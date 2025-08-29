"""
Distributed tracing system for Project Dharma using OpenTelemetry
Provides request tracing, performance monitoring, and error tracking
"""

import os
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass
import asyncio
import threading
from contextvars import ContextVar

from opentelemetry import trace, baggage, context
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes


# Context variables for correlation
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


@dataclass
class TraceConfig:
    """Tracing configuration"""
    service_name: str
    service_version: str = "1.0.0"
    environment: str = "development"
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    otlp_endpoint: str = "http://localhost:4317"
    sample_rate: float = 1.0
    enable_console_export: bool = False
    enable_auto_instrumentation: bool = True


class DharmaTracer:
    """Main tracer class for Dharma platform"""
    
    def __init__(self, config: TraceConfig):
        self.config = config
        self.tracer_provider = None
        self.tracer = None
        self._setup_tracing()
    
    def _setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        # Create resource
        resource = Resource.create({
            "service.name": self.config.service_name,
            "service.version": self.config.service_version,
            "deployment.environment": self.config.environment,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python"
        })
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self.tracer_provider)
        
        # Setup exporters
        self._setup_exporters()
        
        # Setup propagators
        self._setup_propagators()
        
        # Get tracer
        self.tracer = trace.get_tracer(__name__)
        
        # Setup auto-instrumentation
        if self.config.enable_auto_instrumentation:
            self._setup_auto_instrumentation()
    
    def _setup_exporters(self):
        """Setup trace exporters"""
        # Jaeger exporter
        jaeger_exporter = JaegerExporter(
            endpoint=self.config.jaeger_endpoint,
        )
        self.tracer_provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )
        
        # OTLP exporter (for other backends like Grafana Tempo)
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config.otlp_endpoint,
                insecure=True
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
        except Exception as e:
            print(f"Failed to setup OTLP exporter: {e}")
        
        # Console exporter for debugging
        if self.config.enable_console_export:
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
    
    def _setup_propagators(self):
        """Setup trace propagators"""
        # Use composite propagator for multiple formats
        propagator = CompositeHTTPPropagator([
            JaegerPropagator(),
            B3MultiFormat()
        ])
        set_global_textmap(propagator)
    
    def _setup_auto_instrumentation(self):
        """Setup automatic instrumentation"""
        try:
            # HTTP libraries
            RequestsInstrumentor().instrument()
            URLLib3Instrumentor().instrument()
            
            # Database libraries
            AsyncPGInstrumentor().instrument()
            PymongoInstrumentor().instrument()
            
            # Cache libraries
            RedisInstrumentor().instrument()
            
            # Search libraries
            ElasticsearchInstrumentor().instrument()
            
            # Message queue libraries
            KafkaInstrumentor().instrument()
            
        except Exception as e:
            print(f"Failed to setup auto-instrumentation: {e}")
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application"""
        FastAPIInstrumentor.instrument_app(app)
    
    def start_span(self, name: str, kind: trace.SpanKind = trace.SpanKind.INTERNAL, 
                   attributes: Dict[str, Any] = None) -> trace.Span:
        """Start a new span"""
        span = self.tracer.start_span(name, kind=kind, attributes=attributes or {})
        
        # Add correlation IDs if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            span.set_attribute("correlation.id", correlation_id)
        
        user_id = user_id_var.get()
        if user_id:
            span.set_attribute("user.id", user_id)
        
        request_id = request_id_var.get()
        if request_id:
            span.set_attribute("request.id", request_id)
        
        return span
    
    @contextmanager
    def trace_operation(self, operation_name: str, 
                       attributes: Dict[str, Any] = None,
                       kind: trace.SpanKind = trace.SpanKind.INTERNAL):
        """Context manager for tracing operations"""
        span = self.start_span(operation_name, kind=kind, attributes=attributes)
        
        try:
            with trace.use_span(span):
                yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            span.end()
    
    def trace_function(self, operation_name: str = None, 
                      attributes: Dict[str, Any] = None,
                      kind: trace.SpanKind = trace.SpanKind.INTERNAL):
        """Decorator for tracing functions"""
        def decorator(func):
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.trace_operation(span_name, attributes, kind) as span:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("function.result.success", True)
                        return result
                    except Exception as e:
                        span.set_attribute("function.result.success", False)
                        span.set_attribute("function.error.type", type(e).__name__)
                        raise
                    finally:
                        duration = time.time() - start_time
                        span.set_attribute("function.duration", duration)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.trace_operation(span_name, attributes, kind) as span:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("function.result.success", True)
                        return result
                    except Exception as e:
                        span.set_attribute("function.result.success", False)
                        span.set_attribute("function.error.type", type(e).__name__)
                        raise
                    finally:
                        duration = time.time() - start_time
                        span.set_attribute("function.duration", duration)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def add_baggage(self, key: str, value: str):
        """Add baggage to current context"""
        ctx = baggage.set_baggage(key, value)
        context.attach(ctx)
    
    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage from current context"""
        return baggage.get_baggage(key)
    
    def get_current_span(self) -> Optional[trace.Span]:
        """Get current active span"""
        return trace.get_current_span()
    
    def get_trace_id(self) -> Optional[str]:
        """Get current trace ID"""
        span = self.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, '032x')
        return None
    
    def get_span_id(self) -> Optional[str]:
        """Get current span ID"""
        span = self.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, '016x')
        return None


class ErrorTracker:
    """Error tracking and reporting system"""
    
    def __init__(self, tracer: DharmaTracer):
        self.tracer = tracer
        self.error_handlers = []
    
    def track_error(self, error: Exception, 
                   context: Dict[str, Any] = None,
                   severity: str = "error"):
        """Track an error with context"""
        span = self.tracer.get_current_span()
        
        if span:
            # Record exception in span
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
            
            # Add error attributes
            span.set_attribute("error.type", type(error).__name__)
            span.set_attribute("error.message", str(error))
            span.set_attribute("error.severity", severity)
            
            if context:
                for key, value in context.items():
                    span.set_attribute(f"error.context.{key}", str(value))
        
        # Call error handlers
        error_data = {
            "error": error,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity,
            "context": context or {},
            "trace_id": self.tracer.get_trace_id(),
            "span_id": self.tracer.get_span_id(),
            "timestamp": time.time()
        }
        
        for handler in self.error_handlers:
            try:
                handler(error_data)
            except Exception as e:
                print(f"Error in error handler: {e}")
    
    def add_error_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add error handler"""
        self.error_handlers.append(handler)
    
    def track_exception_decorator(self, severity: str = "error"):
        """Decorator for automatic exception tracking"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    self.track_error(e, severity=severity)
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.track_error(e, severity=severity)
                    raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator


class PerformanceProfiler:
    """Performance profiling and bottleneck identification"""
    
    def __init__(self, tracer: DharmaTracer):
        self.tracer = tracer
        self.performance_data = []
        self.thresholds = {
            "slow_operation": 1.0,  # 1 second
            "very_slow_operation": 5.0,  # 5 seconds
            "critical_operation": 10.0  # 10 seconds
        }
    
    def profile_operation(self, operation_name: str, 
                         threshold: float = None):
        """Decorator for profiling operations"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                
                with self.tracer.trace_operation(
                    f"profile.{operation_name}",
                    attributes={"profiling.enabled": True}
                ) as span:
                    try:
                        result = await func(*args, **kwargs)
                        duration = time.time() - start_time
                        
                        # Add performance attributes
                        span.set_attribute("performance.duration", duration)
                        span.set_attribute("performance.operation", operation_name)
                        
                        # Check thresholds
                        self._check_performance_thresholds(span, duration, threshold)
                        
                        # Store performance data
                        self._store_performance_data(operation_name, duration, True)
                        
                        return result
                    
                    except Exception as e:
                        duration = time.time() - start_time
                        span.set_attribute("performance.duration", duration)
                        span.set_attribute("performance.error", True)
                        
                        self._store_performance_data(operation_name, duration, False)
                        raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                
                with self.tracer.trace_operation(
                    f"profile.{operation_name}",
                    attributes={"profiling.enabled": True}
                ) as span:
                    try:
                        result = func(*args, **kwargs)
                        duration = time.time() - start_time
                        
                        # Add performance attributes
                        span.set_attribute("performance.duration", duration)
                        span.set_attribute("performance.operation", operation_name)
                        
                        # Check thresholds
                        self._check_performance_thresholds(span, duration, threshold)
                        
                        # Store performance data
                        self._store_performance_data(operation_name, duration, True)
                        
                        return result
                    
                    except Exception as e:
                        duration = time.time() - start_time
                        span.set_attribute("performance.duration", duration)
                        span.set_attribute("performance.error", True)
                        
                        self._store_performance_data(operation_name, duration, False)
                        raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def _check_performance_thresholds(self, span: trace.Span, duration: float, custom_threshold: float = None):
        """Check performance against thresholds"""
        threshold = custom_threshold or self.thresholds["slow_operation"]
        
        if duration > self.thresholds["critical_operation"]:
            span.set_attribute("performance.level", "critical")
            span.add_event("Critical performance threshold exceeded")
        elif duration > self.thresholds["very_slow_operation"]:
            span.set_attribute("performance.level", "very_slow")
            span.add_event("Very slow performance threshold exceeded")
        elif duration > threshold:
            span.set_attribute("performance.level", "slow")
            span.add_event("Slow performance threshold exceeded")
        else:
            span.set_attribute("performance.level", "normal")
    
    def _store_performance_data(self, operation: str, duration: float, success: bool):
        """Store performance data for analysis"""
        data = {
            "operation": operation,
            "duration": duration,
            "success": success,
            "timestamp": time.time(),
            "trace_id": self.tracer.get_trace_id()
        }
        
        self.performance_data.append(data)
        
        # Keep only recent data (last 1000 operations)
        if len(self.performance_data) > 1000:
            self.performance_data = self.performance_data[-1000:]
    
    def get_performance_summary(self, operation: str = None) -> Dict[str, Any]:
        """Get performance summary"""
        data = self.performance_data
        if operation:
            data = [d for d in data if d["operation"] == operation]
        
        if not data:
            return {}
        
        durations = [d["duration"] for d in data]
        success_count = sum(1 for d in data if d["success"])
        
        return {
            "operation": operation or "all",
            "total_calls": len(data),
            "success_rate": success_count / len(data),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "p95_duration": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
            "slow_calls": sum(1 for d in durations if d > self.thresholds["slow_operation"]),
            "very_slow_calls": sum(1 for d in durations if d > self.thresholds["very_slow_operation"]),
            "critical_calls": sum(1 for d in durations if d > self.thresholds["critical_operation"])
        }


class TracingContext:
    """Context manager for tracing with correlation IDs"""
    
    def __init__(self, correlation_id: str = None, user_id: str = None, request_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.request_id = request_id or str(uuid.uuid4())
        
        self.correlation_token = None
        self.user_token = None
        self.request_token = None
    
    def __enter__(self):
        self.correlation_token = correlation_id_var.set(self.correlation_id)
        if self.user_id:
            self.user_token = user_id_var.set(self.user_id)
        self.request_token = request_id_var.set(self.request_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        correlation_id_var.reset(self.correlation_token)
        if self.user_token:
            user_id_var.reset(self.user_token)
        request_id_var.reset(self.request_token)


# Global tracer instance
_tracer_instance = None
_error_tracker = None
_profiler = None

def get_tracer(service_name: str = None, config: TraceConfig = None) -> DharmaTracer:
    """Get global tracer instance"""
    global _tracer_instance
    
    if _tracer_instance is None:
        if config is None:
            service_name = service_name or os.getenv('SERVICE_NAME', 'dharma-service')
            config = TraceConfig(
                service_name=service_name,
                service_version=os.getenv('SERVICE_VERSION', '1.0.0'),
                environment=os.getenv('ENVIRONMENT', 'development'),
                jaeger_endpoint=os.getenv('JAEGER_ENDPOINT', 'http://localhost:14268/api/traces'),
                otlp_endpoint=os.getenv('OTLP_ENDPOINT', 'http://localhost:4317')
            )
        _tracer_instance = DharmaTracer(config)
    
    return _tracer_instance

def get_error_tracker(service_name: str = None) -> ErrorTracker:
    """Get error tracker instance"""
    global _error_tracker
    
    if _error_tracker is None:
        tracer = get_tracer(service_name)
        _error_tracker = ErrorTracker(tracer)
    
    return _error_tracker

def get_profiler(service_name: str = None) -> PerformanceProfiler:
    """Get performance profiler instance"""
    global _profiler
    
    if _profiler is None:
        tracer = get_tracer(service_name)
        _profiler = PerformanceProfiler(tracer)
    
    return _profiler


# Example usage and testing
if __name__ == "__main__":
    # Initialize tracer
    config = TraceConfig(
        service_name="test-service",
        enable_console_export=True
    )
    tracer = get_tracer(config=config)
    error_tracker = get_error_tracker()
    profiler = get_profiler()
    
    # Test tracing
    with TracingContext(user_id="test_user"):
        with tracer.trace_operation("test_operation") as span:
            span.set_attribute("test.attribute", "test_value")
            span.add_event("Test event")
            
            # Test error tracking
            try:
                raise ValueError("Test error")
            except Exception as e:
                error_tracker.track_error(e, {"context": "test"})
    
    # Test function decoration
    @tracer.trace_function("decorated_function")
    @profiler.profile_operation("test_profile")
    def test_function():
        time.sleep(0.1)
        return "test_result"
    
    result = test_function()
    print(f"Function result: {result}")
    
    # Get performance summary
    summary = profiler.get_performance_summary("test_profile")
    print(f"Performance summary: {summary}")
    
    print("Tracing test completed")