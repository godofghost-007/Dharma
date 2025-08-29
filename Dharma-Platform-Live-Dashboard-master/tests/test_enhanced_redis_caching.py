"""Test enhanced Redis caching system with cluster support."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from shared.cache.cache_config import (
    CacheConfig, CacheMode, CacheSystemBuilder, 
    create_cache_config_from_env, initialize_cache_system,
    CacheHealthChecker
)
from shared.cache.cluster_manager import RedisClusterManager, ClusterNode, ClusterHealth
from shared.database.redis import RedisManager


@pytest.fixture
def standalone_config():
    """Create standalone cache configuration."""
    return CacheConfig(
        mode=CacheMode.STANDALONE,
        redis_url="redis://localhost:6379",
        max_connections=10,
        namespace="test"
    )


@pytest.fixture
def cluster_config():
    """Create cluster cache configuration."""
    return CacheConfig(
        mode=CacheMode.CLUSTER,
        redis_url="redis://localhost:6379",
        max_connections=20,
        namespace="test",
        cluster_nodes=[
            {"host": "localhost", "port": 7001},
            {"host": "localhost", "port": 7002},
            {"host": "localhost", "port": 7003}
        ]
    )


@pytest.fixture
async def mock_redis_manager():
    """Create mock Redis manager."""
    manager = MagicMock(spec=RedisManager)
    manager.cluster_mode = False
    manager.connect = AsyncMock()
    manager.health_check = AsyncMock(return_value=True)
    manager.get_cluster_info = AsyncMock(return_value=None)
    manager.get_node_info = AsyncMock(return_value={
        "redis_version": "7.2.0",
        "connected_clients": 5,
        "used_memory": 1024000
    })
    return manager


@pytest.fixture
async def mock_cluster_redis_manager():
    """Create mock Redis cluster manager."""
    manager = MagicMock(spec=RedisManager)
    manager.cluster_mode = True
    manager.connect = AsyncMock()
    manager.health_check = AsyncMock(return_value=True)
    manager.get_cluster_info = AsyncMock(return_value={
        "cluster_info": {
            "cluster_state": "ok",
            "cluster_slots_assigned": 16384,
            "cluster_slots_ok": 16384,
            "cluster_known_nodes": 6,
            "cluster_size": 3
        },
        "cluster_nodes": {
            "node1": {
                "host": "localhost",
                "port": 7001,
                "role": "master",
                "flags": ["master", "connected"],
                "slots": [(0, 5460)]
            },
            "node2": {
                "host": "localhost",
                "port": 7002,
                "role": "master",
                "flags": ["master", "connected"],
                "slots": [(5461, 10922)]
            },
            "node3": {
                "host": "localhost",
                "port": 7003,
                "role": "master",
                "flags": ["master", "connected"],
                "slots": [(10923, 16383)]
            }
        }
    })
    return manager


class TestCacheConfig:
    """Test cache configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CacheConfig()
        
        assert config.mode == CacheMode.STANDALONE
        assert config.redis_url == "redis://localhost:6379"
        assert config.max_connections == 20
        assert config.namespace == "dharma"
        assert config.default_ttl == 3600
        assert config.enable_monitoring is True
    
    def test_cluster_config(self, cluster_config):
        """Test cluster configuration."""
        assert cluster_config.mode == CacheMode.CLUSTER
        assert len(cluster_config.cluster_nodes) == 3
        assert cluster_config.cluster_nodes[0]["host"] == "localhost"
        assert cluster_config.cluster_nodes[0]["port"] == 7001
    
    @patch.dict('os.environ', {
        'REDIS_URL': 'redis://test:6379',
        'REDIS_MODE': 'cluster',
        'REDIS_CLUSTER_NODES': 'node1:7001,node2:7002,node3:7003',
        'CACHE_NAMESPACE': 'test_env',
        'CACHE_DEFAULT_TTL': '7200'
    })
    def test_config_from_env(self):
        """Test configuration from environment variables."""
        config = create_cache_config_from_env()
        
        assert config.redis_url == "redis://test:6379"
        assert config.mode == CacheMode.CLUSTER
        assert config.namespace == "test_env"
        assert config.default_ttl == 7200
        assert len(config.cluster_nodes) == 3
        assert config.cluster_nodes[0]["host"] == "node1"
        assert config.cluster_nodes[0]["port"] == 7001


class TestCacheSystemBuilder:
    """Test cache system builder."""
    
    async def test_build_standalone_system(self, standalone_config):
        """Test building standalone cache system."""
        with patch('shared.database.redis.RedisManager') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.connect = AsyncMock()
            mock_redis_class.return_value = mock_redis
            
            builder = CacheSystemBuilder(standalone_config)
            redis_manager = await builder.build_redis_manager()
            
            assert redis_manager is not None
            mock_redis.connect.assert_called_once()
    
    async def test_build_cluster_system(self, cluster_config):
        """Test building cluster cache system."""
        with patch('shared.database.redis.RedisManager') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.connect = AsyncMock()
            mock_redis_class.return_value = mock_redis
            
            builder = CacheSystemBuilder(cluster_config)
            components = await builder.build_complete_system()
            
            assert "redis_manager" in components
            assert "cache_manager" in components
            assert "cache_policies" in components
            assert "invalidation_handler" in components
            assert "cluster_manager" in components
    
    async def test_build_with_monitoring_disabled(self, standalone_config):
        """Test building system with monitoring disabled."""
        standalone_config.enable_monitoring = False
        
        with patch('shared.database.redis.RedisManager') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.connect = AsyncMock()
            mock_redis_class.return_value = mock_redis
            
            builder = CacheSystemBuilder(standalone_config)
            components = await builder.build_complete_system()
            
            assert "cache_monitor" not in components
            assert "cluster_manager" not in components


class TestRedisClusterManager:
    """Test Redis cluster manager."""
    
    async def test_get_cluster_topology(self, mock_cluster_redis_manager):
        """Test getting cluster topology."""
        cluster_manager = RedisClusterManager(mock_cluster_redis_manager)
        
        topology = await cluster_manager.get_cluster_topology()
        
        assert len(topology) == 3
        assert "node1" in topology
        assert topology["node1"].role == "master"
        assert topology["node1"].host == "localhost"
        assert topology["node1"].port == 7001
    
    async def test_check_cluster_health(self, mock_cluster_redis_manager):
        """Test cluster health check."""
        cluster_manager = RedisClusterManager(mock_cluster_redis_manager)
        
        health = await cluster_manager.check_cluster_health()
        
        assert health.cluster_state == "ok"
        assert health.cluster_slots_ok == 16384
        assert health.overall_health == "healthy"
        assert len(health.nodes_health) == 3
    
    async def test_get_master_nodes(self, mock_cluster_redis_manager):
        """Test getting master nodes."""
        cluster_manager = RedisClusterManager(mock_cluster_redis_manager)
        
        masters = await cluster_manager.get_master_nodes()
        
        assert len(masters) == 3
        for master in masters:
            assert master.role == "master"
    
    async def test_calculate_slot_for_key(self, mock_cluster_redis_manager):
        """Test slot calculation for keys."""
        cluster_manager = RedisClusterManager(mock_cluster_redis_manager)
        
        # Mock crc16 calculation
        with patch('crc16.crc16xmodem', return_value=12345):
            slot = await cluster_manager.calculate_slot_for_key("test_key")
            assert slot == 12345 % 16384
    
    async def test_get_key_distribution(self, mock_cluster_redis_manager):
        """Test key distribution across nodes."""
        cluster_manager = RedisClusterManager(mock_cluster_redis_manager)
        
        # Mock slot calculations and node lookups
        with patch.object(cluster_manager, 'calculate_slot_for_key') as mock_calc_slot, \
             patch.object(cluster_manager, 'get_node_by_slot') as mock_get_node:
            
            mock_calc_slot.side_effect = [100, 6000, 12000]
            mock_get_node.side_effect = [
                ClusterNode("node1", "localhost", 7001, "master"),
                ClusterNode("node2", "localhost", 7002, "master"),
                ClusterNode("node3", "localhost", 7003, "master")
            ]
            
            distribution = await cluster_manager.get_key_distribution(
                ["key1", "key2", "key3"]
            )
            
            assert len(distribution) == 3
            assert "localhost:7001" in distribution
            assert "localhost:7002" in distribution
            assert "localhost:7003" in distribution
    
    async def test_cluster_stats(self, mock_cluster_redis_manager):
        """Test getting cluster statistics."""
        cluster_manager = RedisClusterManager(mock_cluster_redis_manager)
        
        stats = await cluster_manager.get_cluster_stats()
        
        assert "cluster_health" in stats
        assert "total_nodes" in stats
        assert "master_nodes" in stats
        assert "slave_nodes" in stats
        assert "slots_coverage" in stats


class TestCacheHealthChecker:
    """Test cache health checker."""
    
    async def test_health_check_healthy_system(self, mock_redis_manager):
        """Test health check for healthy system."""
        cache_system = {
            "redis_manager": mock_redis_manager,
            "cache_monitor": MagicMock()
        }
        
        # Mock healthy responses
        cache_system["cache_monitor"].get_cache_health = AsyncMock(return_value={
            "status": "healthy",
            "health_score": 95,
            "issues": []
        })
        
        health_checker = CacheHealthChecker(cache_system)
        health = await health_checker.check_health()
        
        assert health["overall_status"] == "healthy"
        assert len(health["issues"]) == 0
        assert "redis" in health["components"]
        assert health["components"]["redis"]["status"] == "healthy"
    
    async def test_health_check_unhealthy_redis(self, mock_redis_manager):
        """Test health check with unhealthy Redis."""
        mock_redis_manager.health_check = AsyncMock(return_value=False)
        
        cache_system = {"redis_manager": mock_redis_manager}
        
        health_checker = CacheHealthChecker(cache_system)
        health = await health_checker.check_health()
        
        assert health["overall_status"] == "unhealthy"
        assert "Redis connection failed" in health["issues"]
        assert health["components"]["redis"]["status"] == "unhealthy"
    
    async def test_health_check_with_cluster(self, mock_cluster_redis_manager):
        """Test health check with cluster."""
        cluster_manager = MagicMock()
        cluster_manager.check_cluster_health = AsyncMock(return_value=ClusterHealth(
            cluster_state="ok",
            cluster_slots_assigned=16384,
            cluster_slots_ok=16384,
            cluster_slots_pfail=0,
            cluster_slots_fail=0,
            cluster_known_nodes=6,
            cluster_size=3,
            nodes_health={"node1": True, "node2": True, "node3": True},
            overall_health="healthy"
        ))
        
        cache_system = {
            "redis_manager": mock_cluster_redis_manager,
            "cluster_manager": cluster_manager
        }
        
        health_checker = CacheHealthChecker(cache_system)
        health = await health_checker.check_health()
        
        assert health["overall_status"] == "healthy"
        assert "cluster" in health["components"]
        assert health["components"]["cluster"]["status"] == "healthy"


class TestIntegration:
    """Integration tests for enhanced caching system."""
    
    async def test_complete_system_initialization(self, standalone_config):
        """Test complete system initialization."""
        with patch('shared.database.redis.RedisManager') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.connect = AsyncMock()
            mock_redis_class.return_value = mock_redis
            
            cache_system = await initialize_cache_system(standalone_config)
            
            assert "redis_manager" in cache_system
            assert "cache_manager" in cache_system
            assert "cache_policies" in cache_system
            assert "invalidation_handler" in cache_system
    
    async def test_cluster_system_initialization(self, cluster_config):
        """Test cluster system initialization."""
        with patch('shared.database.redis.RedisManager') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.connect = AsyncMock()
            mock_redis_class.return_value = mock_redis
            
            cache_system = await initialize_cache_system(cluster_config)
            
            assert "cluster_manager" in cache_system
            
            # Test cluster-specific operations
            cluster_manager = cache_system["cluster_manager"]
            assert cluster_manager is not None
    
    async def test_cache_operations_with_monitoring(self, standalone_config):
        """Test cache operations with monitoring enabled."""
        with patch('shared.database.redis.RedisManager') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.connect = AsyncMock()
            mock_redis.get = AsyncMock(return_value="test_value")
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis_class.return_value = mock_redis
            
            cache_system = await initialize_cache_system(standalone_config)
            cache_manager = cache_system["cache_manager"]
            cache_monitor = cache_system["cache_monitor"]
            
            # Perform cache operations
            await cache_manager.set("test_key", "test_value", ttl=3600)
            value = await cache_manager.get("test_key")
            
            assert value == "test_value"
            
            # Check monitoring
            assert cache_monitor is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])