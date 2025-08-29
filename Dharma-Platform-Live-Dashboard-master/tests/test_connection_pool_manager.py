"""Test connection pool manager functionality."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from shared.database.connection_pool_manager import (
    ConnectionPoolManager, PoolConfiguration, PoolStatus,
    ConnectionStats, ConnectionWrapper, MultiPoolManager
)

# Mark all test functions as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def pool_config():
    """Create test pool configuration."""
    return PoolConfiguration(
        min_size=2,
        max_size=10,
        acquire_timeout=5.0,
        idle_timeout=60.0,
        health_check_interval=10.0,
        enable_monitoring=True,
        enable_auto_scaling=True,
        scale_up_threshold=0.8,
        scale_down_threshold=0.3
    )


@pytest.fixture
def mock_pool():
    """Create mock connection pool."""
    pool = MagicMock()
    pool.acquire = AsyncMock()
    pool.release = MagicMock()
    pool.get_size = MagicMock(return_value=5)
    pool.get_max_size = MagicMock(return_value=10)
    pool.get_min_size = MagicMock(return_value=2)
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_connection():
    """Create mock database connection."""
    conn = MagicMock()
    conn.execute = AsyncMock(return_value="OK")
    conn.fetch = AsyncMock(return_value=[{"id": 1, "name": "test"}])
    conn.fetchrow = AsyncMock(return_value={"id": 1, "name": "test"})
    return conn


class TestConnectionPoolManager:
    """Test connection pool manager."""
    
    async def test_pool_initialization(self, pool_config, mock_pool):
        """Test pool initialization."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        
        async def pool_factory(**kwargs):
            return mock_pool
        
        await pool_manager.initialize_pool(pool_factory)
        
        assert pool_manager.status == PoolStatus.HEALTHY
        assert pool_manager.stats.total_connections == pool_config.min_size
        assert pool_manager.stats.idle_connections == pool_config.min_size
    
    async def test_connection_acquisition(self, pool_config, mock_pool, mock_connection):
        """Test connection acquisition and release."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        pool_manager._pool = mock_pool
        pool_manager.status = PoolStatus.HEALTHY
        
        # Mock pool.acquire to return our mock connection
        mock_pool.acquire.return_value = mock_connection
        
        # Acquire connection
        conn_wrapper = await pool_manager.acquire_connection()
        
        assert isinstance(conn_wrapper, ConnectionWrapper)
        assert pool_manager.stats.active_connections == 1
        assert pool_manager.stats.idle_connections == 0
        
        # Release connection
        pool_manager.release_connection(mock_connection)
        
        assert pool_manager.stats.active_connections == 0
        assert pool_manager.stats.idle_connections == 1
    
    async def test_connection_timeout(self, pool_config, mock_pool):
        """Test connection acquisition timeout."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        pool_manager._pool = mock_pool
        pool_manager.status = PoolStatus.HEALTHY
        
        # Mock pool.acquire to raise timeout
        async def slow_acquire():
            await asyncio.sleep(10)  # Longer than timeout
            return MagicMock()
        
        mock_pool.acquire.side_effect = slow_acquire
        
        with pytest.raises(asyncio.TimeoutError):
            await pool_manager.acquire_connection(timeout=0.1)
        
        assert pool_manager.stats.failed_connections == 1
    
    async def test_query_performance_tracking(self, pool_config, mock_pool, mock_connection):
        """Test query performance tracking."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        pool_manager._pool = mock_pool
        
        # Record successful query
        pool_manager.record_query(0.05, success=True)
        
        assert pool_manager.stats.total_queries == 1
        assert pool_manager.stats.failed_queries == 0
        assert pool_manager.stats.avg_query_time == 0.05
        
        # Record failed query
        pool_manager.record_query(0.1, success=False)
        
        assert pool_manager.stats.total_queries == 2
        assert pool_manager.stats.failed_queries == 1
        assert pool_manager.stats.avg_query_time == 0.05  # Only successful queries affect avg
    
    async def test_pool_statistics(self, pool_config, mock_pool):
        """Test pool statistics generation."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        pool_manager._pool = mock_pool
        pool_manager.status = PoolStatus.HEALTHY
        
        # Set some test data
        pool_manager.stats.active_connections = 3
        pool_manager.stats.total_queries = 100
        pool_manager.stats.failed_queries = 5
        pool_manager.stats.avg_query_time = 0.025
        
        stats = pool_manager.get_statistics()
        
        assert stats["pool_name"] == "test_pool"
        assert stats["status"] == "healthy"
        assert stats["current_state"]["active_connections"] == 3
        assert stats["performance_metrics"]["total_queries"] == 100
        assert stats["performance_metrics"]["query_success_rate"] == 0.95
        assert stats["performance_metrics"]["avg_query_time"] == 0.025
    
    async def test_statistics_reset(self, pool_config):
        """Test statistics reset."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        
        # Set some test data
        pool_manager.stats.total_queries = 100
        pool_manager.stats.failed_queries = 5
        
        # Reset statistics
        pool_manager.reset_statistics()
        
        assert pool_manager.stats.total_queries == 0
        assert pool_manager.stats.failed_queries == 0
        assert isinstance(pool_manager.stats.last_reset, datetime)


class TestConnectionWrapper:
    """Test connection wrapper functionality."""
    
    async def test_connection_wrapper_execute(self, pool_config, mock_connection):
        """Test connection wrapper execute method."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        wrapper = ConnectionWrapper(mock_connection, pool_manager)
        
        result = await wrapper.execute("SELECT 1")
        
        assert result == "OK"
        assert pool_manager.stats.total_queries == 1
        assert pool_manager.stats.failed_queries == 0
        mock_connection.execute.assert_called_once_with("SELECT 1")
    
    async def test_connection_wrapper_fetch(self, pool_config, mock_connection):
        """Test connection wrapper fetch method."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        wrapper = ConnectionWrapper(mock_connection, pool_manager)
        
        result = await wrapper.fetch("SELECT * FROM test")
        
        assert result == [{"id": 1, "name": "test"}]
        assert pool_manager.stats.total_queries == 1
        mock_connection.fetch.assert_called_once_with("SELECT * FROM test")
    
    async def test_connection_wrapper_error_handling(self, pool_config, mock_connection):
        """Test connection wrapper error handling."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        wrapper = ConnectionWrapper(mock_connection, pool_manager)
        
        # Mock execute to raise an exception
        mock_connection.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await wrapper.execute("SELECT 1")
        
        assert pool_manager.stats.total_queries == 1
        assert pool_manager.stats.failed_queries == 1
    
    async def test_connection_wrapper_context_manager(self, pool_config, mock_connection):
        """Test connection wrapper as context manager."""
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        pool_manager.release_connection = MagicMock()
        
        wrapper = ConnectionWrapper(mock_connection, pool_manager)
        
        async with wrapper as conn:
            assert conn == mock_connection
        
        pool_manager.release_connection.assert_called_once_with(mock_connection)


class TestMultiPoolManager:
    """Test multi-pool manager functionality."""
    
    def test_add_and_get_pool(self, pool_config):
        """Test adding and retrieving pools."""
        multi_manager = MultiPoolManager()
        pool_manager = ConnectionPoolManager("test_pool", pool_config)
        
        multi_manager.add_pool("test", pool_manager)
        
        retrieved_pool = multi_manager.get_pool("test")
        assert retrieved_pool == pool_manager
        
        # Test non-existent pool
        assert multi_manager.get_pool("nonexistent") is None
    
    def test_get_all_statistics(self, pool_config):
        """Test getting statistics for all pools."""
        multi_manager = MultiPoolManager()
        
        # Add multiple pools
        pool1 = ConnectionPoolManager("pool1", pool_config)
        pool2 = ConnectionPoolManager("pool2", pool_config)
        
        multi_manager.add_pool("pool1", pool1)
        multi_manager.add_pool("pool2", pool2)
        
        # Mock get_statistics for both pools
        pool1.get_statistics = MagicMock(return_value={"pool_name": "pool1"})
        pool2.get_statistics = MagicMock(return_value={"pool_name": "pool2"})
        
        all_stats = multi_manager.get_all_statistics()
        
        assert "pool1" in all_stats
        assert "pool2" in all_stats
        assert all_stats["pool1"]["pool_name"] == "pool1"
        assert all_stats["pool2"]["pool_name"] == "pool2"
    
    def test_health_summary(self, pool_config):
        """Test health summary generation."""
        multi_manager = MultiPoolManager()
        
        # Create pools with different statuses
        healthy_pool = ConnectionPoolManager("healthy", pool_config)
        healthy_pool.status = PoolStatus.HEALTHY
        healthy_pool._pool = MagicMock()
        healthy_pool._pool.get_size.return_value = 5
        
        warning_pool = ConnectionPoolManager("warning", pool_config)
        warning_pool.status = PoolStatus.WARNING
        warning_pool._pool = MagicMock()
        warning_pool._pool.get_size.return_value = 8
        
        critical_pool = ConnectionPoolManager("critical", pool_config)
        critical_pool.status = PoolStatus.CRITICAL
        critical_pool._pool = MagicMock()
        critical_pool._pool.get_size.return_value = 10
        
        multi_manager.add_pool("healthy", healthy_pool)
        multi_manager.add_pool("warning", warning_pool)
        multi_manager.add_pool("critical", critical_pool)
        
        health_summary = multi_manager.get_health_summary()
        
        assert health_summary["overall_status"] == "critical"  # Worst status
        assert health_summary["total_pools"] == 3
        assert health_summary["healthy_pools"] == 1
        assert health_summary["warning_pools"] == 1
        assert health_summary["critical_pools"] == 1
        assert health_summary["offline_pools"] == 0
    
    async def test_close_all_pools(self, pool_config):
        """Test closing all pools."""
        multi_manager = MultiPoolManager()
        
        # Add pools
        pool1 = ConnectionPoolManager("pool1", pool_config)
        pool2 = ConnectionPoolManager("pool2", pool_config)
        
        pool1.close = AsyncMock()
        pool2.close = AsyncMock()
        
        multi_manager.add_pool("pool1", pool1)
        multi_manager.add_pool("pool2", pool2)
        
        await multi_manager.close_all()
        
        pool1.close.assert_called_once()
        pool2.close.assert_called_once()
        assert len(multi_manager.pools) == 0


class TestPoolConfiguration:
    """Test pool configuration."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = PoolConfiguration()
        
        assert config.min_size == 5
        assert config.max_size == 20
        assert config.acquire_timeout == 30.0
        assert config.enable_monitoring is True
        assert config.enable_auto_scaling is True
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = PoolConfiguration(
            min_size=10,
            max_size=50,
            acquire_timeout=60.0,
            enable_auto_scaling=False
        )
        
        assert config.min_size == 10
        assert config.max_size == 50
        assert config.acquire_timeout == 60.0
        assert config.enable_auto_scaling is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])