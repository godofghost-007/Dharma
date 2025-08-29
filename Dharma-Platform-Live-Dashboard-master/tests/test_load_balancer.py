"""Test load balancer functionality."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from shared.async_processing.load_balancer import (
    LoadBalancer, LoadBalancingStrategy, ServiceEndpoint, ServiceMetrics,
    HealthStatus, AutoScaler, LoadBalancedService
)

# Mark all test functions as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_endpoints():
    """Create sample service endpoints."""
    return [
        ServiceEndpoint("service-1", "localhost", 8001, weight=1),
        ServiceEndpoint("service-2", "localhost", 8002, weight=2),
        ServiceEndpoint("service-3", "localhost", 8003, weight=1),
    ]


@pytest.fixture
def load_balancer():
    """Create load balancer instance."""
    return LoadBalancer(
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
        health_check_interval=1.0,
        health_check_timeout=0.5
    )


class TestLoadBalancer:
    """Test load balancer functionality."""
    
    def test_add_remove_endpoints(self, load_balancer, sample_endpoints):
        """Test adding and removing endpoints."""
        # Add endpoints
        for endpoint in sample_endpoints:
            load_balancer.add_endpoint(endpoint)
        
        assert len(load_balancer.endpoints) == 3
        assert len(load_balancer.metrics) == 3
        assert "service-1" in load_balancer.endpoints
        
        # Remove endpoint
        load_balancer.remove_endpoint("service-1")
        
        assert len(load_balancer.endpoints) == 2
        assert len(load_balancer.metrics) == 2
        assert "service-1" not in load_balancer.endpoints
    
    def test_round_robin_selection(self, load_balancer, sample_endpoints):
        """Test round-robin endpoint selection."""
        # Add endpoints and mark as healthy
        for endpoint in sample_endpoints:
            load_balancer.add_endpoint(endpoint)
            load_balancer.metrics[endpoint.id].health_status = HealthStatus.HEALTHY
        
        # Test round-robin selection
        selected_ids = []
        for _ in range(6):  # Two full rounds
            endpoint = load_balancer.get_next_endpoint()
            selected_ids.append(endpoint.id)
        
        # Should cycle through endpoints
        expected_pattern = ["service-1", "service-2", "service-3"] * 2
        assert selected_ids == expected_pattern
    
    def test_least_connections_selection(self, load_balancer, sample_endpoints):
        """Test least connections endpoint selection."""
        load_balancer.strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
        
        # Add endpoints and mark as healthy
        for endpoint in sample_endpoints:
            load_balancer.add_endpoint(endpoint)
            load_balancer.metrics[endpoint.id].health_status = HealthStatus.HEALTHY
        
        # Set different connection counts
        load_balancer.metrics["service-1"].active_connections = 5
        load_balancer.metrics["service-2"].active_connections = 2
        load_balancer.metrics["service-3"].active_connections = 8
        
        # Should select service-2 (least connections)
        endpoint = load_balancer.get_next_endpoint()
        assert endpoint.id == "service-2"
    
    def test_weighted_round_robin_selection(self, load_balancer, sample_endpoints):
        """Test weighted round-robin selection."""
        load_balancer.strategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
        
        # Add endpoints and mark as healthy
        for endpoint in sample_endpoints:
            load_balancer.add_endpoint(endpoint)
            load_balancer.metrics[endpoint.id].health_status = HealthStatus.HEALTHY
        
        # Test weighted selection (service-2 has weight 2)
        selected_ids = []
        for _ in range(8):
            endpoint = load_balancer.get_next_endpoint()
            selected_ids.append(endpoint.id)
        
        # service-2 should appear twice as often due to weight 2
        service_2_count = selected_ids.count("service-2")
        service_1_count = selected_ids.count("service-1")
        service_3_count = selected_ids.count("service-3")
        
        assert service_2_count == 4  # Weight 2 out of total weight 4
        assert service_1_count == 2  # Weight 1 out of total weight 4
        assert service_3_count == 2  # Weight 1 out of total weight 4
    
    def test_response_time_selection(self, load_balancer, sample_endpoints):
        """Test response time-based selection."""
        load_balancer.strategy = LoadBalancingStrategy.RESPONSE_TIME
        
        # Add endpoints and mark as healthy
        for endpoint in sample_endpoints:
            load_balancer.add_endpoint(endpoint)
            load_balancer.metrics[endpoint.id].health_status = HealthStatus.HEALTHY
        
        # Set different response times
        load_balancer.metrics["service-1"].avg_response_time = 150.0
        load_balancer.metrics["service-2"].avg_response_time = 50.0
        load_balancer.metrics["service-3"].avg_response_time = 200.0
        
        # Should select service-2 (best response time)
        endpoint = load_balancer.get_next_endpoint()
        assert endpoint.id == "service-2"
    
    def test_no_healthy_endpoints(self, load_balancer, sample_endpoints):
        """Test behavior when no healthy endpoints are available."""
        # Add endpoints but mark as unhealthy
        for endpoint in sample_endpoints:
            load_balancer.add_endpoint(endpoint)
            load_balancer.metrics[endpoint.id].health_status = HealthStatus.UNHEALTHY
        
        # Should return None when no healthy endpoints
        endpoint = load_balancer.get_next_endpoint()
        assert endpoint is None
    
    def test_degraded_endpoints_fallback(self, load_balancer, sample_endpoints):
        """Test fallback to degraded endpoints when no healthy ones."""
        # Add endpoints with mixed health status
        load_balancer.add_endpoint(sample_endpoints[0])
        load_balancer.add_endpoint(sample_endpoints[1])
        
        load_balancer.metrics["service-1"].health_status = HealthStatus.UNHEALTHY
        load_balancer.metrics["service-2"].health_status = HealthStatus.DEGRADED
        
        # Should select degraded endpoint as fallback
        endpoint = load_balancer.get_next_endpoint()
        assert endpoint.id == "service-2"
    
    async def test_request_recording(self, load_balancer, sample_endpoints):
        """Test request start/end recording."""
        load_balancer.add_endpoint(sample_endpoints[0])
        endpoint_id = sample_endpoints[0].id
        
        # Record request start
        await load_balancer.record_request_start(endpoint_id)
        
        metrics = load_balancer.metrics[endpoint_id]
        assert metrics.active_connections == 1
        assert metrics.total_requests == 1
        
        # Record successful request end
        await load_balancer.record_request_end(endpoint_id, 100.0, success=True)
        
        assert metrics.active_connections == 0
        assert metrics.successful_requests == 1
        assert metrics.avg_response_time == 100.0
        assert metrics.last_response_time == 100.0
        
        # Record failed request
        await load_balancer.record_request_start(endpoint_id)
        await load_balancer.record_request_end(endpoint_id, 200.0, success=False)
        
        assert metrics.failed_requests == 1
        assert metrics.error_rate == 0.5  # 1 failed out of 2 total
    
    async def test_health_check_loop(self, load_balancer, sample_endpoints):
        """Test health check functionality."""
        load_balancer.add_endpoint(sample_endpoints[0])
        
        # Mock the health check method
        with patch.object(load_balancer, '_check_endpoint_health') as mock_check:
            mock_check.return_value = None
            
            # Start health checks
            await load_balancer.start_health_checks()
            
            # Wait for at least one health check
            await asyncio.sleep(1.5)
            
            # Stop health checks
            await load_balancer.stop_health_checks()
            
            # Verify health check was called
            assert mock_check.call_count >= 1
    
    def test_get_stats(self, load_balancer, sample_endpoints):
        """Test statistics generation."""
        # Add endpoints and set some metrics
        for endpoint in sample_endpoints:
            load_balancer.add_endpoint(endpoint)
            metrics = load_balancer.metrics[endpoint.id]
            metrics.health_status = HealthStatus.HEALTHY
            metrics.total_requests = 10
            metrics.successful_requests = 8
            metrics.failed_requests = 2
            metrics.avg_response_time = 150.0
        
        stats = load_balancer.get_stats()
        
        assert stats["strategy"] == "round_robin"
        assert stats["total_endpoints"] == 3
        assert stats["healthy_endpoints"] == 3
        assert stats["total_requests"] == 30  # 10 * 3 endpoints
        assert stats["success_rate"] == 0.8  # 24 successful out of 30 total
        assert stats["error_rate"] == 0.2  # 6 failed out of 30 total
        assert "endpoint_metrics" in stats


class TestAutoScaler:
    """Test auto-scaler functionality."""
    
    def test_auto_scaler_initialization(self):
        """Test auto-scaler initialization."""
        auto_scaler = AutoScaler(
            min_instances=2,
            max_instances=10,
            target_cpu_utilization=70.0,
            scale_up_threshold=80.0,
            scale_down_threshold=30.0
        )
        
        assert auto_scaler.min_instances == 2
        assert auto_scaler.max_instances == 10
        assert auto_scaler.current_instances == 2
        assert auto_scaler.target_cpu_utilization == 70.0
    
    def test_scale_callbacks(self):
        """Test setting scale callbacks."""
        auto_scaler = AutoScaler()
        
        scale_up_called = False
        scale_down_called = False
        
        async def scale_up_callback(new_count):
            nonlocal scale_up_called
            scale_up_called = True
        
        async def scale_down_callback(new_count):
            nonlocal scale_down_called
            scale_down_called = True
        
        auto_scaler.set_scale_callbacks(scale_up_callback, scale_down_callback)
        
        assert auto_scaler.scale_up_callback == scale_up_callback
        assert auto_scaler.scale_down_callback == scale_down_callback
    
    async def test_scaling_loop(self):
        """Test auto-scaling loop."""
        auto_scaler = AutoScaler(
            min_instances=1,
            max_instances=5,
            evaluation_period=0.1,  # Fast evaluation for testing
            cooldown_period=0.1     # Short cooldown for testing
        )
        
        scale_actions = []
        
        async def scale_up_callback(new_count):
            scale_actions.append(("up", new_count))
        
        async def scale_down_callback(new_count):
            scale_actions.append(("down", new_count))
        
        auto_scaler.set_scale_callbacks(scale_up_callback, scale_down_callback)
        
        # Mock metrics to trigger scaling
        with patch.object(auto_scaler, '_get_current_metrics') as mock_metrics:
            # High utilization metrics to trigger scale up
            mock_metrics.return_value = {
                'timestamp': datetime.utcnow(),
                'cpu_utilization': 90.0,  # Above scale_up_threshold
                'memory_utilization': 85.0,
                'avg_response_time': 100.0,
                'active_connections': 50,
                'request_rate': 200.0
            }
            
            await auto_scaler.start_auto_scaling()
            
            # Wait for scaling evaluation
            await asyncio.sleep(0.5)
            
            await auto_scaler.stop_auto_scaling()
            
            # Should have triggered scale up
            assert len(scale_actions) > 0
            assert scale_actions[0][0] == "up"
    
    def test_scaling_stats(self):
        """Test scaling statistics."""
        auto_scaler = AutoScaler(
            min_instances=2,
            max_instances=8,
            current_instances=4
        )
        auto_scaler.current_instances = 4
        
        stats = auto_scaler.get_scaling_stats()
        
        assert stats["current_instances"] == 4
        assert stats["min_instances"] == 2
        assert stats["max_instances"] == 8
        assert "last_scale_action" in stats
        assert "target_cpu_utilization" in stats


class TestLoadBalancedService:
    """Test load-balanced service."""
    
    async def test_service_lifecycle(self, sample_endpoints):
        """Test service start/stop lifecycle."""
        load_balancer = LoadBalancer()
        auto_scaler = AutoScaler()
        
        service = LoadBalancedService("test-service", load_balancer, auto_scaler)
        
        # Mock the start/stop methods
        load_balancer.start_health_checks = AsyncMock()
        load_balancer.stop_health_checks = AsyncMock()
        auto_scaler.start_auto_scaling = AsyncMock()
        auto_scaler.stop_auto_scaling = AsyncMock()
        
        # Test start
        await service.start()
        
        load_balancer.start_health_checks.assert_called_once()
        auto_scaler.start_auto_scaling.assert_called_once()
        
        # Test stop
        await service.stop()
        
        load_balancer.stop_health_checks.assert_called_once()
        auto_scaler.stop_auto_scaling.assert_called_once()
    
    async def test_execute_request(self, sample_endpoints):
        """Test request execution through load balancer."""
        load_balancer = LoadBalancer()
        service = LoadBalancedService("test-service", load_balancer)
        
        # Add healthy endpoint
        endpoint = sample_endpoints[0]
        load_balancer.add_endpoint(endpoint)
        load_balancer.metrics[endpoint.id].health_status = HealthStatus.HEALTHY
        
        # Mock request function
        async def mock_request(endpoint, *args, **kwargs):
            return f"Response from {endpoint.id}"
        
        # Mock load balancer methods
        load_balancer.record_request_start = AsyncMock()
        load_balancer.record_request_end = AsyncMock()
        
        # Execute request
        result = await service.execute_request(mock_request, "test_arg")
        
        assert result == f"Response from {endpoint.id}"
        load_balancer.record_request_start.assert_called_once_with(endpoint.id)
        load_balancer.record_request_end.assert_called_once()
    
    async def test_execute_request_no_endpoints(self):
        """Test request execution with no healthy endpoints."""
        load_balancer = LoadBalancer()
        service = LoadBalancedService("test-service", load_balancer)
        
        async def mock_request(endpoint):
            return "Response"
        
        # Should raise RuntimeError when no endpoints available
        with pytest.raises(RuntimeError, match="No healthy endpoints available"):
            await service.execute_request(mock_request)
    
    def test_get_service_stats(self, sample_endpoints):
        """Test service statistics."""
        load_balancer = LoadBalancer()
        auto_scaler = AutoScaler()
        service = LoadBalancedService("test-service", load_balancer, auto_scaler)
        
        # Mock stats methods
        load_balancer.get_stats = MagicMock(return_value={"test": "data"})
        auto_scaler.get_scaling_stats = MagicMock(return_value={"scaling": "data"})
        
        stats = service.get_service_stats()
        
        assert stats["service_name"] == "test-service"
        assert "load_balancer" in stats
        assert "auto_scaler" in stats
        assert stats["load_balancer"]["test"] == "data"
        assert stats["auto_scaler"]["scaling"] == "data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])