"""
Tests for health check system
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from shared.monitoring.health_checks import (
    HealthChecker, HealthStatus, HealthCheckResult,
    DatabaseHealthChecker, HTTPServiceHealthChecker, KafkaHealthChecker,
    SystemResourceHealthChecker, CompositeHealthChecker,
    get_health_checker, setup_default_health_checks
)


class TestHealthCheckResult:
    """Test health check result data structure"""
    
    def test_health_check_result_creation(self):
        """Test health check result creation"""
        result = HealthCheckResult(
            component="test-component",
            status=HealthStatus.HEALTHY,
            message="All good",
            timestamp=datetime.utcnow(),
            response_time_ms=150.5
        )
        
        assert result.component == "test-component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.response_time_ms == 150.5
    
    def test_health_check_result_to_dict(self):
        """Test health check result serialization"""
        timestamp = datetime.utcnow()
        result = HealthCheckResult(
            component="test-component",
            status=HealthStatus.DEGRADED,
            message="Slow response",
            timestamp=timestamp,
            response_time_ms=2500.0,
            details={"cpu_usage": 85.0}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["component"] == "test-component"
        assert result_dict["status"] == "degraded"
        assert result_dict["message"] == "Slow response"
        assert result_dict["timestamp"] == timestamp.isoformat()
        assert result_dict["response_time_ms"] == 2500.0
        assert result_dict["details"]["cpu_usage"] == 85.0


class TestHealthChecker:
    """Test base health checker functionality"""
    
    class MockHealthChecker(HealthChecker):
        """Mock health checker for testing"""
        
        def __init__(self, name: str, should_fail: bool = False, timeout_test: bool = False):
            super().__init__(name, timeout=1.0)
            self.should_fail = should_fail
            self.timeout_test = timeout_test
        
        async def check_health(self) -> HealthCheckResult:
            return await self._timed_check(self._mock_check)
        
        async def _mock_check(self):
            if self.timeout_test:
                await asyncio.sleep(2.0)  # Longer than timeout
            
            if self.should_fail:
                raise Exception("Mock health check failure")
            
            return {"status": "ok", "test": True}
    
    @pytest.mark.asyncio
    async def test_successful_health_check(self):
        """Test successful health check"""
        checker = self.MockHealthChecker("test-checker")
        result = await checker.check_health()
        
        assert result.component == "test-checker"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Health check passed"
        assert result.response_time_ms > 0
        assert result.details["test"] is True
    
    @pytest.mark.asyncio
    async def test_failed_health_check(self):
        """Test failed health check"""
        checker = self.MockHealthChecker("test-checker", should_fail=True)
        result = await checker.check_health()
        
        assert result.component == "test-checker"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Mock health check failure" in result.message
        assert result.response_time_ms > 0
        assert result.details["error_type"] == "Exception"
    
    @pytest.mark.asyncio
    async def test_timeout_health_check(self):
        """Test health check timeout"""
        checker = self.MockHealthChecker("test-checker", timeout_test=True)
        result = await checker.check_health()
        
        assert result.component == "test-checker"
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message
        assert result.response_time_ms >= 1000  # At least 1 second


class TestDatabaseHealthChecker:
    """Test database health checker"""
    
    @pytest.mark.asyncio
    async def test_postgresql_health_check(self):
        """Test PostgreSQL health check"""
        with patch('asyncpg.connect') as mock_connect:
            # Mock connection
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1
            mock_conn.fetchrow.return_value = {
                "active_connections": 5,
                "db_size": 1024 * 1024 * 100  # 100MB
            }
            mock_connect.return_value = mock_conn
            
            checker = DatabaseHealthChecker(
                "postgresql",
                "postgresql://test:test@localhost:5432/test",
                "postgresql"
            )
            
            result = await checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.details["connection_test"] is True
            assert result.details["active_connections"] == 5
            mock_conn.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mongodb_health_check(self):
        """Test MongoDB health check"""
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client_class:
            # Mock client
            mock_client = Mock()
            mock_admin = Mock()
            mock_admin.command = AsyncMock()
            mock_admin.command.side_effect = [
                None,  # ping response
                {  # serverStatus response
                    "version": "4.4.0",
                    "uptime": 3600,
                    "connections": {"current": 10, "available": 990}
                }
            ]
            mock_client.admin = mock_admin
            mock_client_class.return_value = mock_client
            
            checker = DatabaseHealthChecker(
                "mongodb",
                "mongodb://localhost:27017/test",
                "mongodb"
            )
            
            result = await checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.details["connection_test"] is True
            assert result.details["version"] == "4.4.0"
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_health_check(self):
        """Test Redis health check"""
        with patch('aioredis.from_url') as mock_from_url:
            # Mock Redis client
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {
                "redis_version": "6.2.0",
                "uptime_in_seconds": 7200,
                "connected_clients": 5,
                "used_memory": 1024 * 1024,
                "used_memory_human": "1.00M"
            }
            mock_from_url.return_value = mock_redis
            
            checker = DatabaseHealthChecker(
                "redis",
                "redis://localhost:6379",
                "redis"
            )
            
            result = await checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.details["connection_test"] is True
            assert result.details["version"] == "6.2.0"
            mock_redis.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_elasticsearch_health_check(self):
        """Test Elasticsearch health check"""
        with patch('elasticsearch.AsyncElasticsearch') as mock_es_class:
            # Mock Elasticsearch client
            mock_es = AsyncMock()
            mock_es.cluster.health.return_value = {
                "status": "green",
                "number_of_nodes": 3,
                "active_primary_shards": 10,
                "active_shards": 20
            }
            mock_es.cluster.stats.return_value = {
                "indices": {"count": 5}
            }
            mock_es_class.return_value = mock_es
            
            checker = DatabaseHealthChecker(
                "elasticsearch",
                "http://localhost:9200",
                "elasticsearch"
            )
            
            result = await checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.details["cluster_status"] == "green"
            assert result.details["number_of_nodes"] == 3
            mock_es.close.assert_called_once()


class TestHTTPServiceHealthChecker:
    """Test HTTP service health checker"""
    
    @pytest.mark.asyncio
    async def test_successful_http_check(self):
        """Test successful HTTP health check"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Mock HTTP response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"content-length": "100"}
            
            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            checker = HTTPServiceHealthChecker(
                "test-service",
                "http://localhost:8000/health"
            )
            
            result = await checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.details["status_code"] == 200
            assert result.details["status_match"] is True
    
    @pytest.mark.asyncio
    async def test_failed_http_check(self):
        """Test failed HTTP health check"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Mock HTTP response with error status
            mock_response = AsyncMock()
            mock_response.status = 503
            mock_response.headers = {}
            
            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            checker = HTTPServiceHealthChecker(
                "test-service",
                "http://localhost:8000/health",
                expected_status=200
            )
            
            result = await checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY  # Still healthy, just status mismatch
            assert result.details["status_code"] == 503
            assert result.details["status_match"] is False


class TestSystemResourceHealthChecker:
    """Test system resource health checker"""
    
    @pytest.mark.asyncio
    async def test_system_resources_healthy(self):
        """Test healthy system resources"""
        with patch('psutil.cpu_percent', return_value=25.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_io_counters') as mock_network:
            
            # Mock system stats
            mock_memory.return_value = Mock(
                percent=30.0,
                available=8 * 1024**3  # 8GB
            )
            mock_disk.return_value = Mock(
                total=100 * 1024**3,  # 100GB
                used=20 * 1024**3,    # 20GB
                free=80 * 1024**3     # 80GB
            )
            mock_network.return_value = Mock(
                bytes_sent=1024**3,
                bytes_recv=2 * 1024**3
            )
            
            checker = SystemResourceHealthChecker()
            result = await checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.details["status"] == HealthStatus.HEALTHY
            assert result.details["cpu_percent"] == 25.0
            assert result.details["memory_percent"] == 30.0
            assert len(result.details["warnings"]) == 0
    
    @pytest.mark.asyncio
    async def test_system_resources_degraded(self):
        """Test degraded system resources"""
        with patch('psutil.cpu_percent', return_value=75.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_io_counters') as mock_network:
            
            # Mock system stats - elevated usage
            mock_memory.return_value = Mock(
                percent=75.0,
                available=2 * 1024**3  # 2GB
            )
            mock_disk.return_value = Mock(
                total=100 * 1024**3,  # 100GB
                used=85 * 1024**3,    # 85GB
                free=15 * 1024**3     # 15GB
            )
            mock_network.return_value = Mock(
                bytes_sent=1024**3,
                bytes_recv=2 * 1024**3
            )
            
            checker = SystemResourceHealthChecker()
            result = await checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY  # Still returns healthy from _timed_check
            assert result.details["status"] == HealthStatus.DEGRADED
            assert result.details["cpu_percent"] == 75.0
            assert result.details["memory_percent"] == 75.0
            assert len(result.details["warnings"]) > 0


class TestCompositeHealthChecker:
    """Test composite health checker"""
    
    @pytest.fixture
    def mock_checkers(self):
        """Create mock health checkers"""
        checker1 = Mock(spec=HealthChecker)
        checker1.name = "checker1"
        checker1.check_health = AsyncMock(return_value=HealthCheckResult(
            component="checker1",
            status=HealthStatus.HEALTHY,
            message="OK",
            timestamp=datetime.utcnow(),
            response_time_ms=100.0
        ))
        
        checker2 = Mock(spec=HealthChecker)
        checker2.name = "checker2"
        checker2.check_health = AsyncMock(return_value=HealthCheckResult(
            component="checker2",
            status=HealthStatus.DEGRADED,
            message="Slow",
            timestamp=datetime.utcnow(),
            response_time_ms=500.0
        ))
        
        return [checker1, checker2]
    
    def test_composite_checker_initialization(self):
        """Test composite health checker initialization"""
        checker = CompositeHealthChecker("test-service")
        
        assert checker.service_name == "test-service"
        assert len(checker.checkers) == 0
        assert checker.check_interval == 30
        assert not checker.running
    
    def test_add_remove_checkers(self, mock_checkers):
        """Test adding and removing checkers"""
        composite = CompositeHealthChecker("test-service")
        
        # Add checkers
        for checker in mock_checkers:
            composite.add_checker(checker)
        
        assert len(composite.checkers) == 2
        assert "checker1" in composite.checkers
        assert "checker2" in composite.checkers
        
        # Remove checker
        composite.remove_checker("checker1")
        
        assert len(composite.checkers) == 1
        assert "checker1" not in composite.checkers
        assert "checker2" in composite.checkers
    
    @pytest.mark.asyncio
    async def test_check_all(self, mock_checkers):
        """Test running all health checks"""
        composite = CompositeHealthChecker("test-service")
        
        for checker in mock_checkers:
            composite.add_checker(checker)
        
        results = await composite.check_all()
        
        assert len(results) == 2
        assert "checker1" in results
        assert "checker2" in results
        assert results["checker1"].status == HealthStatus.HEALTHY
        assert results["checker2"].status == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_overall_health(self, mock_checkers):
        """Test overall health calculation"""
        composite = CompositeHealthChecker("test-service")
        
        for checker in mock_checkers:
            composite.add_checker(checker)
        
        # Run checks first
        await composite.check_all()
        
        # Get overall health
        overall = await composite.get_overall_health()
        
        assert overall.component == "test-service"
        assert overall.status == HealthStatus.DEGRADED  # Degraded because one checker is degraded
        assert overall.details["component_count"] == 2
        assert overall.details["healthy_count"] == 1
        assert overall.details["degraded_count"] == 1
        assert overall.details["unhealthy_count"] == 0


class TestGlobalFunctions:
    """Test global health check functions"""
    
    def test_get_health_checker(self):
        """Test getting global health checker"""
        checker1 = get_health_checker("test-service")
        checker2 = get_health_checker("test-service")
        
        # Should return same instance
        assert checker1 is checker2
        assert checker1.service_name == "test-service"
    
    def test_setup_default_health_checks(self):
        """Test setting up default health checks"""
        config = {
            "postgresql": {
                "connection_string": "postgresql://test:test@localhost:5432/test"
            },
            "redis": {
                "connection_string": "redis://localhost:6379"
            },
            "kafka": {
                "bootstrap_servers": ["localhost:9092"]
            },
            "external_services": {
                "api-gateway": {
                    "health_url": "http://localhost:8001/health",
                    "expected_status": 200
                }
            }
        }
        
        health_checker = setup_default_health_checks("test-service", config)
        
        # Should have system resources + configured services
        assert len(health_checker.checkers) >= 5  # system + postgresql + redis + kafka + api-gateway
        assert "system_resources" in health_checker.checkers
        assert "postgresql" in health_checker.checkers
        assert "redis" in health_checker.checkers
        assert "kafka" in health_checker.checkers
        assert "api-gateway" in health_checker.checkers


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])