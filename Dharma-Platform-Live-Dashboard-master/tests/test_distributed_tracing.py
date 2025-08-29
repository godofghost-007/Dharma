"""
Comprehensive tests for distributed tracing implementation
Tests tracing, correlation, error tracking, and performance profiling
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from shared.tracing.tracer import (
    DharmaTracer, TraceConfig, ErrorTracker, PerformanceProfiler,
    get_tracer, get_error_tracker, get_profiler, TracingContext
)
from shared.tracing.correlation import (
    CorrelationManager, CorrelationContext, CorrelationMiddleware,
    get_correlation_manager, get_correlation_id, get_request_id
)
from shared.tracing.error_tracker import (
    AdvancedErrorTracker, ErrorSeverity, ErrorCategory, ErrorEvent
)
from shared.tracing.performance_profiler import (
    AdvancedPerformanceProfiler, PerformanceMetrics, BottleneckInfo
)
from shared.tracing.integration import (
    TracingMiddleware, TracedHTTPClient, TracedKafkaProducer,
    setup_service_tracing, trace_database_operation, trace_ai_operation
)


class TestDharmaTracer:
    """Test distributed tracing functionality"""
    
    def test_tracer_initialization(self):
        """Test tracer initialization with config"""
        config = TraceConfig(
            service_name="test-service",
            service_version="1.0.0",
            environment="test",
            enable_console_export=True
        )
        
        tracer = DharmaTracer(config)
        
        assert tracer.config.service_name == "test-service"
        assert tracer.config.service_version == "1.0.0"
        assert tracer.config.environment == "test"
        assert tracer.tracer is not None
    
    def test_span_creation(self):
        """Test span creation and attributes"""
        tracer = get_tracer("test-service")
        
        with TracingContext(correlation_id="test-correlation", user_id="test-user"):
            span = tracer.start_span("test-operation")
            
            # Check span attributes
            assert span is not None
            
            # Test span attributes
            span.set_attribute("test.attribute", "test_value")
            span.add_event("Test event")
            
            span.end()
    
    def test_trace_operation_context_manager(self):
        """Test trace operation context manager"""
        tracer = get_tracer("test-service")
        
        with tracer.trace_operation("test-operation") as span:
            assert span is not None
            span.set_attribute("operation.type", "test")
    
    def test_trace_function_decorator(self):
        """Test function tracing decorator"""
        tracer = get_tracer("test-service")
        
        @tracer.trace_function("test_function")
        def test_func():
            time.sleep(0.01)
            return "test_result"
        
        result = test_func()
        assert result == "test_result"
    
    @pytest.mark.asyncio
    async def test_async_trace_function_decorator(self):
        """Test async function tracing decorator"""
        tracer = get_tracer("test-service")
        
        @tracer.trace_function("async_test_function")
        async def async_test_func():
            await asyncio.sleep(0.01)
            return "async_test_result"
        
        result = await async_test_func()
        assert result == "async_test_result"
    
    def test_trace_id_generation(self):
        """Test trace ID generation and retrieval"""
        tracer = get_tracer("test-service")
        
        with tracer.trace_operation("test-operation"):
            trace_id = tracer.get_trace_id()
            span_id = tracer.get_span_id()
            
            assert trace_id is not None
            assert span_id is not None
            assert len(trace_id) == 32  # 128-bit trace ID as hex
            assert len(span_id) == 16   # 64-bit span ID as hex


class TestCorrelationManager:
    """Test correlation ID management"""
    
    @pytest.mark.asyncio
    async def test_correlation_manager_initialization(self):
        """Test correlation manager initialization"""
        manager = CorrelationManager()
        await manager.initialize()
        
        assert manager.redis_client is not None
        
        await manager.close()
    
    def test_correlation_id_generation(self):
        """Test correlation ID generation"""
        manager = CorrelationManager()
        
        correlation_id = manager.generate_correlation_id()
        request_id = manager.generate_request_id()
        
        assert correlation_id is not None
        assert request_id is not None
        assert request_id.startswith("req_")
    
    def test_correlation_context_creation(self):
        """Test correlation context creation"""
        context = CorrelationContext(
            correlation_id="test-correlation",
            request_id="test-request",
            user_id="test-user"
        )
        
        assert context.correlation_id == "test-correlation"
        assert context.request_id == "test-request"
        assert context.user_id == "test-user"
    
    def test_correlation_context_headers(self):
        """Test correlation context header conversion"""
        context = CorrelationContext(
            correlation_id="test-correlation",
            request_id="test-request",
            user_id="test-user",
            baggage={"key": "value"}
        )
        
        headers = context.to_headers()
        
        assert headers["X-Correlation-ID"] == "test-correlation"
        assert headers["X-Request-ID"] == "test-request"
        assert headers["X-User-ID"] == "test-user"
        assert "X-Baggage" in headers
    
    def test_correlation_context_from_headers(self):
        """Test correlation context creation from headers"""
        headers = {
            "X-Correlation-ID": "test-correlation",
            "X-Request-ID": "test-request",
            "X-User-ID": "test-user",
            "X-Baggage": '{"key": "value"}'
        }
        
        context = CorrelationContext.from_headers(headers)
        
        assert context.correlation_id == "test-correlation"
        assert context.request_id == "test-request"
        assert context.user_id == "test-user"
        assert context.baggage == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_correlation_data_storage(self):
        """Test correlation data storage and retrieval"""
        manager = CorrelationManager()
        
        # Mock Redis client
        manager.redis_client = AsyncMock()
        manager.redis_client.hgetall.return_value = {
            "test_key": '{"test": "value"}'
        }
        
        context = CorrelationContext(
            correlation_id="test-correlation",
            request_id="test-request"
        )
        
        # Store data
        await manager.store_correlation_data(context, {"test": "value"})
        
        # Verify storage call
        manager.redis_client.hset.assert_called_once()
        manager.redis_client.expire.assert_called_once()
        
        # Get data
        data = await manager.get_correlation_data("test-correlation")
        assert data == {"test_key": {"test": "value"}}


class TestErrorTracker:
    """Test error tracking functionality"""
    
    @pytest.mark.asyncio
    async def test_error_tracker_initialization(self):
        """Test error tracker initialization"""
        tracker = AdvancedErrorTracker("test-service")
        
        # Mock dependencies
        tracker.es_client = AsyncMock()
        tracker.redis_client = AsyncMock()
        tracker.kafka_producer = Mock()
        
        await tracker.start()
        
        assert tracker.running is True
        
        await tracker.stop()
    
    def test_error_event_creation(self):
        """Test error event creation"""
        tracker = AdvancedErrorTracker("test-service")
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            error_event = tracker.track_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.APPLICATION
            )
            
            assert error_event.error_type == "ValueError"
            assert error_event.error_message == "Test error"
            assert error_event.severity == ErrorSeverity.HIGH
            assert error_event.category == ErrorCategory.APPLICATION
            assert error_event.service == "test-service"
    
    def test_error_fingerprint_generation(self):
        """Test error fingerprint generation"""
        tracker = AdvancedErrorTracker("test-service")
        
        fingerprint1 = tracker.aggregator.generate_fingerprint(
            "ValueError", "Test error", "traceback", "test-service"
        )
        fingerprint2 = tracker.aggregator.generate_fingerprint(
            "ValueError", "Test error", "traceback", "test-service"
        )
        
        assert fingerprint1 == fingerprint2
        assert len(fingerprint1) == 32  # MD5 hash length
    
    def test_error_aggregation(self):
        """Test error aggregation"""
        tracker = AdvancedErrorTracker("test-service")
        
        # Create similar errors
        try:
            raise ValueError("Test error")
        except Exception as e:
            error1 = tracker.track_error(e)
            error2 = tracker.track_error(e)
            
            # Second error should be aggregated
            assert error1.fingerprint == error2.fingerprint
    
    @pytest.mark.asyncio
    async def test_error_summary(self):
        """Test error summary generation"""
        tracker = AdvancedErrorTracker("test-service")
        
        # Mock Elasticsearch client
        tracker.es_client = AsyncMock()
        tracker.es_client.search.return_value = {
            "hits": {"total": {"value": 10}},
            "aggregations": {
                "by_severity": {"buckets": [{"key": "high", "doc_count": 5}]},
                "by_category": {"buckets": [{"key": "application", "doc_count": 8}]},
                "by_error_type": {"buckets": [{"key": "ValueError", "doc_count": 3}]},
                "timeline": {"buckets": [{"key_as_string": "2023-01-01T00:00:00", "doc_count": 2}]}
            }
        }
        
        summary = await tracker.get_error_summary()
        
        assert summary["total_errors"] == 10
        assert summary["by_severity"]["high"] == 5
        assert summary["by_category"]["application"] == 8


class TestPerformanceProfiler:
    """Test performance profiling functionality"""
    
    @pytest.mark.asyncio
    async def test_profiler_initialization(self):
        """Test profiler initialization"""
        profiler = AdvancedPerformanceProfiler()
        await profiler.initialize()
        
        assert profiler.system_monitor is not None
        
        await profiler.close()
    
    def test_performance_metrics_creation(self):
        """Test performance metrics creation"""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            duration=1.5,
            cpu_usage=25.0,
            memory_usage=10.0,
            timestamp=datetime.utcnow(),
            correlation_id="test-correlation"
        )
        
        assert metrics.operation_name == "test_operation"
        assert metrics.duration == 1.5
        assert metrics.cpu_usage == 25.0
        assert metrics.correlation_id == "test-correlation"
    
    def test_bottleneck_detection(self):
        """Test bottleneck detection"""
        profiler = AdvancedPerformanceProfiler()
        
        # Create metrics that should trigger bottleneck detection
        slow_metrics = PerformanceMetrics(
            operation_name="slow_operation",
            duration=15.0,  # Above critical threshold
            cpu_usage=95.0,  # Above critical threshold
            memory_usage=90.0,  # Above critical threshold
            timestamp=datetime.utcnow()
        )
        
        bottleneck = profiler._detect_bottleneck(slow_metrics)
        
        assert bottleneck is not None
        assert bottleneck.severity == "critical"
        assert bottleneck.bottleneck_type in ["duration", "cpu", "memory"]
    
    def test_profile_operation_context_manager(self):
        """Test profile operation context manager"""
        profiler = AdvancedPerformanceProfiler()
        
        with profiler.profile_operation("test_operation") as span:
            # Simulate some work
            time.sleep(0.01)
            assert span is not None
    
    def test_profile_function_decorator(self):
        """Test profile function decorator"""
        profiler = AdvancedPerformanceProfiler()
        
        @profiler.profile_function("test_function")
        def test_func():
            time.sleep(0.01)
            return "result"
        
        result = test_func()
        assert result == "result"
        assert len(profiler.performance_data) > 0
    
    @pytest.mark.asyncio
    async def test_performance_summary(self):
        """Test performance summary generation"""
        profiler = AdvancedPerformanceProfiler()
        
        # Mock Redis client
        profiler.redis_client = AsyncMock()
        profiler.redis_client.lrange.return_value = [
            json.dumps({
                "operation_name": "test_op",
                "duration": 1.0,
                "cpu_usage": 20.0,
                "memory_usage": 10.0,
                "timestamp": datetime.utcnow().isoformat()
            })
        ]
        
        summary = await profiler.get_performance_summary("test_op")
        
        assert "total_calls" in summary
        assert "duration" in summary
        assert "avg" in summary["duration"]


class TestTracingIntegration:
    """Test tracing integration utilities"""
    
    @pytest.mark.asyncio
    async def test_traced_http_client(self):
        """Test traced HTTP client"""
        client = TracedHTTPClient("test-service", "http://localhost:8000")
        
        # Mock aiohttp session
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"content-length": "100"}
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.request.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            async with client:
                response = await client.get("/test")
                
                assert response.status == 200
                mock_session.request.assert_called_once()
    
    def test_traced_kafka_producer(self):
        """Test traced Kafka producer"""
        with patch('kafka.KafkaProducer') as mock_producer_class:
            mock_producer = Mock()
            mock_producer_class.return_value = mock_producer
            
            producer = TracedKafkaProducer("test-service")
            
            # Mock future
            mock_future = Mock()
            mock_producer.send.return_value = mock_future
            
            future = producer.send("test-topic", {"message": "test"})
            
            assert future == mock_future
            mock_producer.send.assert_called_once()
    
    def test_database_operation_decorator(self):
        """Test database operation tracing decorator"""
        @trace_database_operation("test_query", "postgresql")
        def test_db_operation():
            time.sleep(0.01)
            return {"result": "success"}
        
        result = test_db_operation()
        assert result == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_ai_operation_decorator(self):
        """Test AI operation tracing decorator"""
        @trace_ai_operation("test-model", "inference")
        async def test_ai_operation():
            await asyncio.sleep(0.01)
            return {"prediction": "positive", "confidence": 0.95}
        
        result = await test_ai_operation()
        assert result == {"prediction": "positive", "confidence": 0.95}
    
    def test_setup_service_tracing(self):
        """Test service tracing setup"""
        from fastapi import FastAPI
        
        app = FastAPI()
        
        components = setup_service_tracing(app, "test-service")
        
        assert "tracer" in components
        assert "correlation_manager" in components
        assert "error_tracker" in components
        assert "profiler" in components
        
        assert components["tracer"] is not None
        assert components["correlation_manager"] is not None


class TestTracingMiddleware:
    """Test tracing middleware functionality"""
    
    @pytest.mark.asyncio
    async def test_tracing_middleware(self):
        """Test tracing middleware request processing"""
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Add tracing middleware
        app.add_middleware(TracingMiddleware, "test-service")
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.url.scheme = "http"
        mock_request.url.hostname = "localhost"
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"
        
        # Mock call_next
        async def mock_call_next(request):
            return JSONResponse({"message": "test"})
        
        middleware = TracingMiddleware(app, "test-service")
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response is not None


@pytest.mark.integration
class TestDistributedTracingIntegration:
    """Integration tests for distributed tracing"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_tracing(self):
        """Test end-to-end distributed tracing"""
        # Initialize components
        tracer = get_tracer("integration-test-service")
        correlation_manager = get_correlation_manager()
        error_tracker = get_error_tracker("integration-test-service")
        profiler = get_profiler()
        
        await correlation_manager.initialize()
        await profiler.initialize()
        
        # Create correlation context
        with TracingContext(
            correlation_id="integration-test-correlation",
            user_id="test-user"
        ):
            # Start tracing operation
            with tracer.trace_operation("integration_test") as span:
                # Add some attributes
                span.set_attribute("test.type", "integration")
                
                # Profile the operation
                with profiler.profile_operation("integration_test_profile"):
                    # Simulate some work
                    await asyncio.sleep(0.1)
                    
                    # Test error tracking
                    try:
                        raise ValueError("Integration test error")
                    except Exception as e:
                        error_tracker.track_error(
                            e,
                            severity=ErrorSeverity.MEDIUM,
                            category=ErrorCategory.APPLICATION
                        )
                
                # Verify correlation IDs are set
                assert get_correlation_id() == "integration-test-correlation"
                assert get_request_id() is not None
                
                # Verify trace IDs are available
                trace_id = tracer.get_trace_id()
                span_id = tracer.get_span_id()
                
                assert trace_id is not None
                assert span_id is not None
        
        # Clean up
        await correlation_manager.close()
        await profiler.close()
    
    @pytest.mark.asyncio
    async def test_cross_service_correlation(self):
        """Test correlation across multiple services"""
        # Service A
        correlation_manager_a = CorrelationManager()
        await correlation_manager_a.initialize()
        
        # Service B
        correlation_manager_b = CorrelationManager()
        await correlation_manager_b.initialize()
        
        # Create context in service A
        context_a = CorrelationContext(
            correlation_id="cross-service-test",
            request_id="service-a-request",
            user_id="test-user"
        )
        
        correlation_manager_a.set_correlation_context(context_a)
        
        # Simulate passing context to service B via headers
        headers = context_a.to_headers()
        context_b = CorrelationContext.from_headers(headers)
        
        # Create child context for service B
        child_context = correlation_manager_b.create_child_context(
            context_b, "service-b", "process_request"
        )
        
        # Verify correlation is maintained
        assert child_context.correlation_id == context_a.correlation_id
        assert child_context.user_id == context_a.user_id
        assert child_context.request_id != context_a.request_id  # New request ID
        assert child_context.parent_span_id == context_a.span_id
        
        # Clean up
        await correlation_manager_a.close()
        await correlation_manager_b.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])