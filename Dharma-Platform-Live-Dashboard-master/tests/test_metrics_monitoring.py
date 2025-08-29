"""
Tests for metrics and monitoring system
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from shared.monitoring.metrics_collector import (
    MetricsCollector, BusinessMetricsCollector, MetricDefinition, 
    MetricType, metrics_middleware, get_metrics_collector, get_business_metrics
)


class TestMetricsCollector:
    """Test metrics collector functionality"""
    
    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization"""
        collector = MetricsCollector("test-service", 9091)
        assert collector.service_name == "test-service"
        assert collector.port == 9091
        assert len(collector.metrics) > 0  # Should have default metrics
    
    def test_metric_registration(self):
        """Test metric registration"""
        collector = MetricsCollector("test-service")
        
        metric_def = MetricDefinition(
            name="test_counter",
            description="Test counter metric",
            metric_type=MetricType.COUNTER,
            labels=["label1", "label2"]
        )
        
        metric = collector.register_metric(metric_def)
        assert metric is not None
        assert "test_counter" in collector.metrics
        
        # Test duplicate registration
        metric2 = collector.register_metric(metric_def)
        assert metric is metric2  # Should return same instance
    
    def test_counter_operations(self):
        """Test counter metric operations"""
        collector = MetricsCollector("test-service")
        
        # Register test counter
        metric_def = MetricDefinition(
            name="test_counter",
            description="Test counter",
            metric_type=MetricType.COUNTER,
            labels=["method"]
        )
        collector.register_metric(metric_def)
        
        # Test increment
        collector.increment_counter("test_counter", {"method": "GET"}, 1)
        collector.increment_counter("test_counter", {"method": "GET"}, 2)
        
        # Verify metric exists
        metric = collector.get_metric("test_counter")
        assert metric is not None
    
    def test_histogram_operations(self):
        """Test histogram metric operations"""
        collector = MetricsCollector("test-service")
        
        # Register test histogram
        metric_def = MetricDefinition(
            name="test_histogram",
            description="Test histogram",
            metric_type=MetricType.HISTOGRAM,
            labels=["endpoint"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0]
        )
        collector.register_metric(metric_def)
        
        # Test observations
        collector.observe_histogram("test_histogram", 0.5, {"endpoint": "/api/test"})
        collector.observe_histogram("test_histogram", 1.2, {"endpoint": "/api/test"})
        
        # Verify metric exists
        metric = collector.get_metric("test_histogram")
        assert metric is not None
    
    def test_gauge_operations(self):
        """Test gauge metric operations"""
        collector = MetricsCollector("test-service")
        
        # Register test gauge
        metric_def = MetricDefinition(
            name="test_gauge",
            description="Test gauge",
            metric_type=MetricType.GAUGE,
            labels=["instance"]
        )
        collector.register_metric(metric_def)
        
        # Test set operations
        collector.set_gauge("test_gauge", 42.0, {"instance": "test-1"})
        collector.set_gauge("test_gauge", 24.0, {"instance": "test-2"})
        
        # Verify metric exists
        metric = collector.get_metric("test_gauge")
        assert metric is not None
    
    def test_metrics_text_output(self):
        """Test metrics text output"""
        collector = MetricsCollector("test-service")
        
        # Add some test metrics
        collector.increment_counter("http_requests_total", {"method": "GET", "endpoint": "/test", "status": "200"})
        collector.set_gauge("process_cpu_usage_percent", 25.5)
        
        # Get metrics text
        metrics_text = collector.get_metrics_text()
        assert isinstance(metrics_text, str)
        assert "http_requests_total" in metrics_text
        assert "process_cpu_usage_percent" in metrics_text
    
    @patch('shared.monitoring.metrics_collector.psutil.Process')
    def test_system_metrics_collection(self, mock_process):
        """Test system metrics collection"""
        # Mock psutil.Process
        mock_proc = Mock()
        mock_proc.cpu_percent.return_value = 25.5
        mock_proc.memory_info.return_value = Mock(rss=1024*1024*100)  # 100MB
        mock_proc.num_threads.return_value = 10
        mock_proc.num_fds.return_value = 50
        mock_process.return_value = mock_proc
        
        collector = MetricsCollector("test-service")
        
        # Manually trigger system metrics collection
        collector._collect_system_metrics()
        
        # Verify system metrics were set
        assert collector.get_metric("process_cpu_usage_percent") is not None
        assert collector.get_metric("process_memory_usage_bytes") is not None
        assert collector.get_metric("process_threads") is not None


class TestBusinessMetricsCollector:
    """Test business metrics collector"""
    
    def test_business_metrics_initialization(self):
        """Test business metrics collector initialization"""
        base_collector = MetricsCollector("test-service")
        business_collector = BusinessMetricsCollector(base_collector)
        
        # Verify business metrics were registered
        assert base_collector.get_metric("posts_processed_total") is not None
        assert base_collector.get_metric("sentiment_analysis_total") is not None
        assert base_collector.get_metric("bots_detected_total") is not None
        assert base_collector.get_metric("campaigns_detected_total") is not None
    
    def test_post_processing_metrics(self):
        """Test post processing metrics recording"""
        base_collector = MetricsCollector("test-service")
        business_collector = BusinessMetricsCollector(base_collector)
        
        # Record post processing
        business_collector.record_post_processed("twitter", "data-collection", 1.5)
        business_collector.record_post_processed("youtube", "data-collection", 2.3)
        
        # Verify metrics were recorded
        posts_metric = base_collector.get_metric("posts_processed_total")
        duration_metric = base_collector.get_metric("posts_processing_duration_seconds")
        assert posts_metric is not None
        assert duration_metric is not None
    
    def test_sentiment_analysis_metrics(self):
        """Test sentiment analysis metrics recording"""
        base_collector = MetricsCollector("test-service")
        business_collector = BusinessMetricsCollector(base_collector)
        
        # Record sentiment analyses
        business_collector.record_sentiment_analysis("pro-india", 0.85)
        business_collector.record_sentiment_analysis("neutral", 0.65)
        business_collector.record_sentiment_analysis("anti-india", 0.92)
        
        # Verify metrics were recorded
        sentiment_metric = base_collector.get_metric("sentiment_analysis_total")
        assert sentiment_metric is not None
    
    def test_bot_detection_metrics(self):
        """Test bot detection metrics recording"""
        base_collector = MetricsCollector("test-service")
        business_collector = BusinessMetricsCollector(base_collector)
        
        # Record bot detections
        business_collector.record_bot_detection("twitter", 0.95)
        business_collector.record_bot_detection("youtube", 0.75)
        
        # Verify metrics were recorded
        bots_metric = base_collector.get_metric("bots_detected_total")
        assert bots_metric is not None
    
    def test_campaign_detection_metrics(self):
        """Test campaign detection metrics recording"""
        base_collector = MetricsCollector("test-service")
        business_collector = BusinessMetricsCollector(base_collector)
        
        # Record campaign detections
        business_collector.record_campaign_detection("disinformation", "high")
        business_collector.record_campaign_detection("bot_network", "critical")
        
        # Verify metrics were recorded
        campaigns_metric = base_collector.get_metric("campaigns_detected_total")
        assert campaigns_metric is not None
    
    def test_alert_metrics(self):
        """Test alert metrics recording"""
        base_collector = MetricsCollector("test-service")
        business_collector = BusinessMetricsCollector(base_collector)
        
        # Record alert generation
        business_collector.record_alert_generated("security_breach", "critical")
        business_collector.record_alert_generated("performance_issue", "warning")
        
        # Update pending alerts
        business_collector.update_pending_alerts(5, "critical")
        business_collector.update_pending_alerts(12, "warning")
        
        # Verify metrics were recorded
        alerts_metric = base_collector.get_metric("alerts_generated_total")
        pending_metric = base_collector.get_metric("alerts_pending_total")
        assert alerts_metric is not None
        assert pending_metric is not None
    
    def test_model_inference_metrics(self):
        """Test model inference metrics recording"""
        base_collector = MetricsCollector("test-service")
        business_collector = BusinessMetricsCollector(base_collector)
        
        # Record model inference
        business_collector.record_model_inference("sentiment_bert", "v1.2", 0.15, 0.92)
        business_collector.record_model_inference("bot_detector", "v2.1", 0.08, 0.88)
        
        # Verify metrics were recorded
        duration_metric = base_collector.get_metric("model_inference_duration_seconds")
        accuracy_metric = base_collector.get_metric("model_accuracy_score")
        assert duration_metric is not None
        assert accuracy_metric is not None


class TestMetricsMiddleware:
    """Test metrics middleware"""
    
    def test_middleware_decorator(self):
        """Test metrics middleware decorator"""
        collector = MetricsCollector("test-service")
        
        @metrics_middleware(collector)
        def test_endpoint(request):
            # Mock response
            response = Mock()
            response.status_code = 200
            return response
        
        # Mock request
        request = Mock()
        request.method = "GET"
        request.url.path = "/api/test"
        
        # Call decorated function
        response = test_endpoint(request)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify metrics were recorded
        requests_metric = collector.get_metric("http_requests_total")
        duration_metric = collector.get_metric("http_request_duration_seconds")
        assert requests_metric is not None
        assert duration_metric is not None
    
    def test_middleware_error_handling(self):
        """Test middleware error handling"""
        collector = MetricsCollector("test-service")
        
        @metrics_middleware(collector)
        def failing_endpoint(request):
            raise ValueError("Test error")
        
        # Mock request
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/fail"
        
        # Call decorated function and expect error
        with pytest.raises(ValueError):
            failing_endpoint(request)
        
        # Verify error metrics were recorded
        requests_metric = collector.get_metric("http_requests_total")
        assert requests_metric is not None


class TestGlobalInstances:
    """Test global metrics instances"""
    
    def test_get_metrics_collector(self):
        """Test getting global metrics collector"""
        collector1 = get_metrics_collector("test-service")
        collector2 = get_metrics_collector("test-service")
        
        # Should return same instance
        assert collector1 is collector2
        assert collector1.service_name == "test-service"
    
    def test_get_business_metrics(self):
        """Test getting global business metrics"""
        business1 = get_business_metrics("test-service")
        business2 = get_business_metrics("test-service")
        
        # Should return same instance
        assert business1 is business2


class TestMetricDefinition:
    """Test metric definition"""
    
    def test_metric_definition_creation(self):
        """Test metric definition creation"""
        metric_def = MetricDefinition(
            name="test_metric",
            description="Test metric description",
            metric_type=MetricType.COUNTER,
            labels=["label1", "label2"]
        )
        
        assert metric_def.name == "test_metric"
        assert metric_def.description == "Test metric description"
        assert metric_def.metric_type == MetricType.COUNTER
        assert metric_def.labels == ["label1", "label2"]
    
    def test_metric_definition_defaults(self):
        """Test metric definition with defaults"""
        metric_def = MetricDefinition(
            name="test_metric",
            description="Test metric",
            metric_type=MetricType.GAUGE
        )
        
        assert metric_def.labels == []
        assert metric_def.buckets is None


class TestPrometheusIntegration:
    """Test Prometheus integration"""
    
    @patch('shared.monitoring.metrics_collector.start_http_server')
    def test_http_server_start(self, mock_start_server):
        """Test starting HTTP server for metrics"""
        collector = MetricsCollector("test-service", 9091)
        collector.start_http_server()
        
        mock_start_server.assert_called_once_with(9091, registry=collector.registry)
    
    def test_prometheus_metrics_format(self):
        """Test Prometheus metrics format"""
        collector = MetricsCollector("test-service")
        
        # Add some metrics
        collector.increment_counter("test_counter", {"label": "value"})
        collector.set_gauge("test_gauge", 42.0)
        
        # Get metrics text
        metrics_text = collector.get_metrics_text()
        
        # Verify Prometheus format
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text
        assert "test_counter" in metrics_text
        assert "test_gauge" in metrics_text


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])