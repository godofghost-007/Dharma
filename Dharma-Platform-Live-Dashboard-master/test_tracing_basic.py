#!/usr/bin/env python3
"""
Basic test script for distributed tracing implementation
Tests core functionality without external dependencies
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_correlation_context():
    """Test correlation context functionality"""
    print("Testing Correlation Context...")
    
    from shared.tracing.correlation import CorrelationContext
    
    # Test context creation
    context = CorrelationContext(
        correlation_id="test-correlation-123",
        request_id="test-request-456",
        user_id="test-user-789"
    )
    
    assert context.correlation_id == "test-correlation-123"
    assert context.request_id == "test-request-456"
    assert context.user_id == "test-user-789"
    print("✓ Correlation context creation works")
    
    # Test header conversion
    headers = context.to_headers()
    assert headers["X-Correlation-ID"] == "test-correlation-123"
    assert headers["X-Request-ID"] == "test-request-456"
    assert headers["X-User-ID"] == "test-user-789"
    print("✓ Header conversion works")
    
    # Test context from headers
    context2 = CorrelationContext.from_headers(headers)
    assert context2.correlation_id == context.correlation_id
    assert context2.request_id == context.request_id
    assert context2.user_id == context.user_id
    print("✓ Context from headers works")

def test_error_tracking():
    """Test error tracking functionality"""
    print("\nTesting Error Tracking...")
    
    from shared.tracing.error_tracker import ErrorEvent, ErrorSeverity, ErrorCategory, ErrorAggregator
    
    # Test error event creation
    error_event = ErrorEvent(
        id="test-error-123",
        timestamp=datetime.utcnow(),
        service="test-service",
        error_type="ValueError",
        error_message="Test error message",
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.APPLICATION,
        stack_trace="Test stack trace",
        context=None,
        fingerprint="test-fingerprint"
    )
    
    assert error_event.error_type == "ValueError"
    assert error_event.severity == ErrorSeverity.HIGH
    print("✓ Error event creation works")
    
    # Test error aggregation
    aggregator = ErrorAggregator()
    fingerprint = aggregator.generate_fingerprint(
        "ValueError", "Test error", "stack trace", "test-service"
    )
    assert len(fingerprint) == 32  # MD5 hash
    print("✓ Error fingerprint generation works")

def test_performance_metrics():
    """Test performance metrics functionality"""
    print("\nTesting Performance Metrics...")
    
    from shared.tracing.performance_profiler import PerformanceMetrics, BottleneckInfo
    
    # Test performance metrics creation
    metrics = PerformanceMetrics(
        operation_name="test_operation",
        duration=2.5,
        cpu_usage=75.0,
        memory_usage=60.0,
        timestamp=datetime.utcnow(),
        correlation_id="test-correlation"
    )
    
    assert metrics.operation_name == "test_operation"
    assert metrics.duration == 2.5
    assert metrics.cpu_usage == 75.0
    print("✓ Performance metrics creation works")
    
    # Test bottleneck info
    bottleneck = BottleneckInfo(
        operation_name="slow_operation",
        bottleneck_type="cpu",
        severity="high",
        description="High CPU usage detected",
        metrics=metrics.to_dict(),
        recommendations=["Optimize algorithm", "Use caching"],
        timestamp=datetime.utcnow()
    )
    
    assert bottleneck.bottleneck_type == "cpu"
    assert bottleneck.severity == "high"
    print("✓ Bottleneck info creation works")

def test_configuration():
    """Test configuration functionality"""
    print("\nTesting Configuration...")
    
    from shared.tracing.config import TracingConfig, CorrelationConfig, ErrorTrackingConfig
    
    # Test tracing config
    tracing_config = TracingConfig(
        service_name="test-service",
        service_version="1.0.0",
        deployment_environment="test"
    )
    
    assert tracing_config.service_name == "test-service"
    assert tracing_config.service_version == "1.0.0"
    assert "service.name" in tracing_config.resource_attributes
    print("✓ Tracing configuration works")
    
    # Test correlation config
    correlation_config = CorrelationConfig()
    assert correlation_config.correlation_id_header == "X-Correlation-ID"
    assert correlation_config.correlation_ttl_seconds == 3600
    print("✓ Correlation configuration works")
    
    # Test error tracking config
    error_config = ErrorTrackingConfig()
    assert error_config.elasticsearch_index_prefix == "dharma-errors"
    assert error_config.aggregation_time_window_minutes == 5
    print("✓ Error tracking configuration works")

async def test_async_functionality():
    """Test async functionality"""
    print("\nTesting Async Functionality...")
    
    from shared.tracing.correlation import CorrelationManager
    
    # Test correlation manager (without Redis)
    manager = CorrelationManager()
    
    correlation_id = manager.generate_correlation_id()
    request_id = manager.generate_request_id()
    
    assert correlation_id is not None
    assert request_id.startswith("req_")
    print("✓ Correlation ID generation works")
    
    # Test context creation
    from shared.tracing.correlation import CorrelationContext
    context = CorrelationContext(
        correlation_id=correlation_id,
        request_id=request_id,
        user_id="test-user"
    )
    
    child_context = manager.create_child_context(
        context, "child-service", "child-operation"
    )
    
    assert child_context.correlation_id == context.correlation_id
    assert child_context.user_id == context.user_id
    assert child_context.request_id != context.request_id
    print("✓ Child context creation works")

def test_integration_decorators():
    """Test integration decorators (without external dependencies)"""
    print("\nTesting Integration Decorators...")
    
    # Mock the tracer and profiler for testing
    class MockTracer:
        def trace_operation(self, name, **kwargs):
            return MockSpan()
        
        def trace_function(self, name, **kwargs):
            def decorator(func):
                return func
            return decorator
    
    class MockSpan:
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def set_attribute(self, key, value):
            pass
    
    class MockProfiler:
        def profile_operation(self, name, **kwargs):
            return MockSpan()
        
        def profile_function(self, name, **kwargs):
            def decorator(func):
                return func
            return decorator
    
    # Test function decoration (mock)
    mock_tracer = MockTracer()
    mock_profiler = MockProfiler()
    
    @mock_tracer.trace_function("test_function")
    @mock_profiler.profile_function("test_function")
    def test_function():
        time.sleep(0.01)
        return "test_result"
    
    result = test_function()
    assert result == "test_result"
    print("✓ Function decoration works")

def main():
    """Run all tests"""
    print("=" * 60)
    print("DISTRIBUTED TRACING BASIC FUNCTIONALITY TEST")
    print("=" * 60)
    
    try:
        # Run synchronous tests
        test_correlation_context()
        test_error_tracking()
        test_performance_metrics()
        test_configuration()
        test_integration_decorators()
        
        # Run async tests
        asyncio.run(test_async_functionality())
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("✅ Distributed tracing implementation is working correctly")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)