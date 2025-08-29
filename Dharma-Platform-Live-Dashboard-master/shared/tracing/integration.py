"""
Integration utilities for distributed tracing across Dharma services
Provides middleware, decorators, and utilities for seamless tracing integration
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps

from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import aiohttp
from kafka import KafkaProducer, KafkaConsumer

from .tracer import get_tracer, DharmaTracer, TracingContext
from .correlation import get_correlation_manager, CorrelationMiddleware, CorrelationContext
from .error_tracker import get_error_tracker, ErrorSeverity, ErrorCategory
from .performance_profiler import get_profiler


class TracingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for distributed tracing"""
    
    def __init__(self, app: ASGIApp, service_name: str):
        super().__init__(app)
        self.service_name = service_name
        self.tracer = get_tracer(service_name)
        self.correlation_manager = get_correlation_manager()
        self.error_tracker = get_error_tracker(service_name)
        self.profiler = get_profiler()
    
    async def dispatch(self, request: Request, call_next):
        # Extract correlation context from headers
        headers = dict(request.headers)
        correlation_context = CorrelationContext.from_headers(headers)
        
        # Set correlation context
        self.correlation_manager.set_correlation_context(correlation_context)
        
        # Start tracing span
        operation_name = f"{request.method} {request.url.path}"
        
        with self.tracer.trace_operation(
            operation_name,
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname,
                "http.target": request.url.path,
                "http.user_agent": request.headers.get("user-agent", ""),
                "http.client_ip": request.client.host if request.client else "",
                "service.name": self.service_name
            },
            kind=self.tracer.tracer.SpanKind.SERVER
        ) as span:
            
            # Profile the request
            with self.profiler.profile_operation(f"http.{operation_name}"):
                start_time = time.time()
                
                try:
                    # Process request
                    response = await call_next(request)
                    
                    # Add response attributes
                    span.set_attribute("http.status_code", response.status_code)
                    span.set_attribute("http.response.size", 
                                     len(response.body) if hasattr(response, 'body') else 0)
                    
                    # Add correlation headers to response
                    correlation_headers = correlation_context.to_headers()
                    for key, value in correlation_headers.items():
                        response.headers[key] = value
                    
                    # Add tracing headers
                    trace_id = self.tracer.get_trace_id()
                    span_id = self.tracer.get_span_id()
                    if trace_id:
                        response.headers["X-Trace-ID"] = trace_id
                    if span_id:
                        response.headers["X-Span-ID"] = span_id
                    
                    return response
                
                except Exception as e:
                    # Track error
                    self.error_tracker.track_error(
                        e,
                        severity=ErrorSeverity.HIGH,
                        category=ErrorCategory.APPLICATION,
                        context={
                            "method": request.method,
                            "url": str(request.url),
                            "user_agent": request.headers.get("user-agent"),
                            "client_ip": request.client.host if request.client else None
                        }
                    )
                    
                    # Add error attributes to span
                    span.set_attribute("http.status_code", 500)
                    span.set_attribute("error", True)
                    
                    raise
                
                finally:
                    # Add timing attributes
                    duration = time.time() - start_time
                    span.set_attribute("http.request.duration", duration)


class TracedHTTPClient:
    """HTTP client with distributed tracing support"""
    
    def __init__(self, service_name: str, base_url: str = None):
        self.service_name = service_name
        self.base_url = base_url
        self.tracer = get_tracer(service_name)
        self.correlation_manager = get_correlation_manager()
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make traced HTTP request"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Prepare full URL
        full_url = url if url.startswith('http') else f"{self.base_url}{url}"
        
        # Get correlation context
        correlation_context = self.correlation_manager.get_correlation_context()
        
        # Add correlation headers
        headers = kwargs.get('headers', {})
        if correlation_context:
            headers.update(correlation_context.to_headers())
        
        # Add tracing headers
        trace_id = self.tracer.get_trace_id()
        span_id = self.tracer.get_span_id()
        if trace_id:
            headers["X-Trace-ID"] = trace_id
        if span_id:
            headers["X-Parent-Span-ID"] = span_id
        
        kwargs['headers'] = headers
        
        # Start tracing span
        operation_name = f"HTTP {method.upper()}"
        
        with self.tracer.trace_operation(
            operation_name,
            attributes={
                "http.method": method.upper(),
                "http.url": full_url,
                "http.client": self.service_name,
                "component": "http-client"
            },
            kind=self.tracer.tracer.SpanKind.CLIENT
        ) as span:
            
            start_time = time.time()
            
            try:
                response = await self.session.request(method, full_url, **kwargs)
                
                # Add response attributes
                span.set_attribute("http.status_code", response.status)
                span.set_attribute("http.response.size", 
                                 int(response.headers.get('content-length', 0)))
                
                return response
            
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                raise
            
            finally:
                duration = time.time() - start_time
                span.set_attribute("http.request.duration", duration)
    
    async def get(self, url: str, **kwargs):
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs):
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs):
        return await self.request('DELETE', url, **kwargs)


class TracedKafkaProducer:
    """Kafka producer with distributed tracing"""
    
    def __init__(self, service_name: str, **kafka_config):
        self.service_name = service_name
        self.tracer = get_tracer(service_name)
        self.correlation_manager = get_correlation_manager()
        self.producer = KafkaProducer(**kafka_config)
    
    def send(self, topic: str, value: Any, key: Any = None, **kwargs):
        """Send message with tracing"""
        # Get correlation context
        correlation_context = self.correlation_manager.get_correlation_context()
        
        # Add tracing headers to message
        headers = kwargs.get('headers', [])
        if correlation_context:
            correlation_headers = correlation_context.to_headers()
            for header_key, header_value in correlation_headers.items():
                headers.append((header_key, header_value.encode('utf-8')))
        
        # Add trace context
        trace_id = self.tracer.get_trace_id()
        span_id = self.tracer.get_span_id()
        if trace_id:
            headers.append(('X-Trace-ID', trace_id.encode('utf-8')))
        if span_id:
            headers.append(('X-Parent-Span-ID', span_id.encode('utf-8')))
        
        kwargs['headers'] = headers
        
        # Start tracing span
        with self.tracer.trace_operation(
            f"kafka.send.{topic}",
            attributes={
                "messaging.system": "kafka",
                "messaging.destination": topic,
                "messaging.operation": "send",
                "messaging.producer": self.service_name
            },
            kind=self.tracer.tracer.SpanKind.PRODUCER
        ) as span:
            
            try:
                future = self.producer.send(topic, value, key, **kwargs)
                
                # Add message attributes
                span.set_attribute("messaging.message.size", len(str(value)))
                if key:
                    span.set_attribute("messaging.kafka.message.key", str(key))
                
                return future
            
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                raise
    
    def close(self):
        """Close producer"""
        self.producer.close()


class TracedKafkaConsumer:
    """Kafka consumer with distributed tracing"""
    
    def __init__(self, service_name: str, topics: list, **kafka_config):
        self.service_name = service_name
        self.topics = topics
        self.tracer = get_tracer(service_name)
        self.correlation_manager = get_correlation_manager()
        self.consumer = KafkaConsumer(*topics, **kafka_config)
    
    def __iter__(self):
        return self
    
    def __next__(self):
        message = next(self.consumer)
        
        # Extract correlation context from headers
        headers = {}
        if message.headers:
            for key, value in message.headers:
                headers[key] = value.decode('utf-8') if isinstance(value, bytes) else value
        
        correlation_context = CorrelationContext.from_headers(headers)
        self.correlation_manager.set_correlation_context(correlation_context)
        
        # Start tracing span
        with self.tracer.trace_operation(
            f"kafka.receive.{message.topic}",
            attributes={
                "messaging.system": "kafka",
                "messaging.destination": message.topic,
                "messaging.operation": "receive",
                "messaging.consumer": self.service_name,
                "messaging.kafka.partition": message.partition,
                "messaging.kafka.offset": message.offset
            },
            kind=self.tracer.tracer.SpanKind.CONSUMER
        ) as span:
            
            # Add message attributes
            span.set_attribute("messaging.message.size", len(message.value))
            if message.key:
                span.set_attribute("messaging.kafka.message.key", message.key.decode('utf-8'))
            
            return message
    
    def close(self):
        """Close consumer"""
        self.consumer.close()


def setup_service_tracing(app: FastAPI, service_name: str, 
                         enable_profiling: bool = True,
                         enable_error_tracking: bool = True):
    """Setup comprehensive tracing for a FastAPI service"""
    
    # Initialize tracing components
    tracer = get_tracer(service_name)
    correlation_manager = get_correlation_manager()
    
    if enable_error_tracking:
        error_tracker = get_error_tracker(service_name)
    
    if enable_profiling:
        profiler = get_profiler()
    
    # Instrument FastAPI
    tracer.instrument_fastapi(app)
    
    # Add correlation middleware
    app.add_middleware(CorrelationMiddleware, correlation_manager, service_name)
    
    # Add tracing middleware
    app.add_middleware(TracingMiddleware, service_name)
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        await correlation_manager.initialize()
        if enable_profiling:
            await profiler.initialize()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        await correlation_manager.close()
        if enable_profiling:
            await profiler.close()
    
    return {
        'tracer': tracer,
        'correlation_manager': correlation_manager,
        'error_tracker': error_tracker if enable_error_tracking else None,
        'profiler': profiler if enable_profiling else None
    }


def trace_database_operation(operation_name: str, db_type: str = "unknown"):
    """Decorator for tracing database operations"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.trace_operation(
                f"db.{operation_name}",
                attributes={
                    "db.system": db_type,
                    "db.operation": operation_name,
                    "component": "database"
                },
                kind=tracer.tracer.SpanKind.CLIENT
            ) as span:
                
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("db.success", True)
                    return result
                
                except Exception as e:
                    span.set_attribute("db.success", False)
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise
                
                finally:
                    duration = time.time() - start_time
                    span.set_attribute("db.duration", duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.trace_operation(
                f"db.{operation_name}",
                attributes={
                    "db.system": db_type,
                    "db.operation": operation_name,
                    "component": "database"
                },
                kind=tracer.tracer.SpanKind.CLIENT
            ) as span:
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("db.success", True)
                    return result
                
                except Exception as e:
                    span.set_attribute("db.success", False)
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise
                
                finally:
                    duration = time.time() - start_time
                    span.set_attribute("db.duration", duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def trace_ai_operation(model_name: str, operation_type: str = "inference"):
    """Decorator for tracing AI/ML operations"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            profiler = get_profiler()
            
            with tracer.trace_operation(
                f"ai.{operation_type}",
                attributes={
                    "ai.model.name": model_name,
                    "ai.operation": operation_type,
                    "component": "ai-ml"
                },
                kind=tracer.tracer.SpanKind.INTERNAL
            ) as span:
                
                with profiler.profile_operation(f"ai.{model_name}.{operation_type}"):
                    start_time = time.time()
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("ai.success", True)
                        
                        # Add result metadata if available
                        if hasattr(result, '__len__'):
                            span.set_attribute("ai.result.size", len(result))
                        
                        return result
                    
                    except Exception as e:
                        span.set_attribute("ai.success", False)
                        span.set_attribute("error", True)
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))
                        raise
                    
                    finally:
                        duration = time.time() - start_time
                        span.set_attribute("ai.duration", duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            profiler = get_profiler()
            
            with tracer.trace_operation(
                f"ai.{operation_type}",
                attributes={
                    "ai.model.name": model_name,
                    "ai.operation": operation_type,
                    "component": "ai-ml"
                },
                kind=tracer.tracer.SpanKind.INTERNAL
            ) as span:
                
                with profiler.profile_operation(f"ai.{model_name}.{operation_type}"):
                    start_time = time.time()
                    
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("ai.success", True)
                        
                        # Add result metadata if available
                        if hasattr(result, '__len__'):
                            span.set_attribute("ai.result.size", len(result))
                        
                        return result
                    
                    except Exception as e:
                        span.set_attribute("ai.success", False)
                        span.set_attribute("error", True)
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))
                        raise
                    
                    finally:
                        duration = time.time() - start_time
                        span.set_attribute("ai.duration", duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Example usage and testing
if __name__ == "__main__":
    from fastapi import FastAPI
    
    app = FastAPI()
    
    # Setup tracing
    tracing_components = setup_service_tracing(app, "test-service")
    
    @app.get("/test")
    @trace_database_operation("test_query", "postgresql")
    async def test_endpoint():
        # Simulate database operation
        await asyncio.sleep(0.1)
        return {"message": "test"}
    
    @app.get("/ai-test")
    @trace_ai_operation("test-model", "sentiment_analysis")
    async def ai_test_endpoint():
        # Simulate AI operation
        await asyncio.sleep(0.2)
        return {"sentiment": "positive", "confidence": 0.95}
    
    print("Tracing integration setup complete")