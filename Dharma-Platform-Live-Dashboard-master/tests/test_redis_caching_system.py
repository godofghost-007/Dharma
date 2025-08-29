"""Test Redis caching system implementation."""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from shared.database.redis import RedisManager
from shared.cache.cache_manager import CacheManager, CacheStats
from shared.cache.cache_policies import CachePolicies, CachePolicyConfig, CachePolicy
from shared.cache.invalidation_handler import CacheInvalidationHandler
from shared.cache.monitoring import CacheMonitor, CacheMetrics


@pytest.fixture
async def redis_manager():
    """Create mock Redis manager."""
    manager = MagicMock(spec=RedisManager)
    manager.client = AsyncMock()
    
    # Mock Redis operations
    manager.get = AsyncMock(return_value=None)
    manager.set = AsyncMock(return_value=True)
    manager.delete = AsyncMock(return_value=1)
    manager.exists = AsyncMock(return_value=False)
    manager.expire = AsyncMock(return_value=True)
    manager.incr = AsyncMock(return_value=1)
    manager.publish = AsyncMock(return_value=1)
    manager.subscribe = AsyncMock()
    
    # Mock Redis client operations
    manager.client.scan = AsyncMock(return_value=(0, []))
    manager.client.lrem = AsyncMock(return_value=1)
    manager.client.llen = AsyncMock(return_value=0)
    manager.client.lrange = AsyncMock(return_value=[])
    manager.client.ttl = AsyncMock(return_value=-1)
    manager.client.info = AsyncMock(return_value={
        "used_memory": 1024000,
        "maxmemory": 1073741824,
        "db0": {"keys": 100, "expires": 50}
    })
    
    return manager


@pytest.fixture
def cache_policies():
    """Create cache policies instance."""
    return CachePolicies()


@pytest.fixture
async def cache_manager(redis_manager):
    """Create cache manager instance."""
    return CacheManager(redis_manager, namespace="test")


@pytest.fixture
async def cache_monitor(redis_manager):
    """Create cache monitor instance."""
    return CacheMonitor(redis_manager, namespace="test")


@pytest.fixture
async def invalidation_handler(cache_manager, cache_policies):
    """Create invalidation handler instance."""
    return CacheInvalidationHandler(cache_manager, cache_policies)


class TestCacheManager:
    """Test cache manager functionality."""
    
    async def test_cache_set_and_get(self, cache_manager, redis_manager):
        """Test basic cache set and get operations."""
        # Mock successful set
        redis_manager.set.return_value = True
        
        # Test set
        result = await cache_manager.set("test_key", "test_value", ttl=3600)
        assert result is True
        
        # Verify Redis calls
        redis_manager.set.assert_called()
        
        # Mock get
        redis_manager.get.side_effect = ["test_value", None]  # value, then metadata
        
        # Test get
        value = await cache_manager.get("test_key")
        assert value == "test_value"
    
    async def test_cache_miss(self, cache_manager, redis_manager):
        """Test cache miss behavior."""
        redis_manager.get.return_value = None
        
        value = await cache_manager.get("nonexistent_key", default="default_value")
        assert value == "default_value"
        assert cache_manager.stats.misses == 1
    
    async def test_cache_with_tags(self, cache_manager, redis_manager):
        """Test cache operations with tags."""
        redis_manager.set.return_value = True
        redis_manager.lpush = AsyncMock(return_value=1)
        
        # Set cache with tags
        result = await cache_manager.set(
            "tagged_key", 
            "tagged_value", 
            ttl=3600, 
            tags=["tag1", "tag2"]
        )
        assert result is True
        
        # Verify tag operations
        redis_manager.lpush.assert_called()
    
    async def test_cache_invalidation_by_pattern(self, cache_manager, redis_manager):
        """Test pattern-based cache invalidation."""
        # Mock scan results
        redis_manager.client.scan.return_value = (0, [
            "test:cache:pattern:key1",
            "test:cache:pattern:key2"
        ])
        
        # Mock delete operations
        cache_manager.delete = AsyncMock(return_value=True)
        
        deleted_count = await cache_manager.invalidate_by_pattern("pattern:*")
        assert deleted_count == 2
    
    async def test_cache_invalidation_by_tags(self, cache_manager, redis_manager):
        """Test tag-based cache invalidation."""
        # Mock tag key operations
        redis_manager.client.llen.return_value = 2
        redis_manager.client.lrange.return_value = ["key1", "key2"]
        
        # Mock delete operations
        cache_manager.delete = AsyncMock(return_value=True)
        
        deleted_count = await cache_manager.invalidate_by_tags(["tag1"])
        assert deleted_count == 2
    
    async def test_cache_aside_pattern(self, cache_manager, redis_manager):
        """Test cache-aside pattern implementation."""
        # Mock cache miss
        redis_manager.get.return_value = None
        
        # Mock fetch function
        async def fetch_data():
            return "fetched_data"
        
        # Mock successful set
        cache_manager.set = AsyncMock(return_value=True)
        
        value = await cache_manager.cache_aside_get(
            "cache_aside_key",
            fetch_data,
            ttl=3600
        )
        
        assert value == "fetched_data"
        cache_manager.set.assert_called_once()
    
    async def test_cache_key_utilities(self, cache_manager):
        """Test cache key utility functions."""
        # Test make_cache_key
        key = cache_manager.make_cache_key("user", "123", "profile")
        assert key == "user:123:profile"
        
        # Test hash_key
        hash_key = cache_manager.hash_key({"user_id": 123, "action": "login"})
        assert len(hash_key) == 32  # MD5 hash length


class TestCachePolicies:
    """Test cache policies functionality."""
    
    def test_default_policies_loaded(self, cache_policies):
        """Test that default policies are loaded."""
        assert "user_profiles" in cache_policies.policies
        assert "sentiment_results" in cache_policies.policies
        assert "dashboard_metrics" in cache_policies.policies
    
    def test_get_policy(self, cache_policies):
        """Test getting cache policy."""
        policy = cache_policies.get_policy("user_profiles")
        assert policy is not None
        assert policy.ttl == 3600
        assert "user_data" in policy.tags
    
    def test_add_custom_policy(self, cache_policies):
        """Test adding custom cache policy."""
        custom_policy = CachePolicyConfig(
            name="custom_policy",
            ttl=7200,
            policy=CachePolicy.CACHE_ASIDE,
            tags=["custom"]
        )
        
        cache_policies.add_policy(custom_policy)
        
        retrieved_policy = cache_policies.get_policy("custom_policy")
        assert retrieved_policy is not None
        assert retrieved_policy.ttl == 7200
    
    def test_get_ttl_for_key(self, cache_policies):
        """Test TTL determination for keys."""
        ttl = cache_policies.get_ttl_for_key("user_profiles:123")
        assert ttl == 3600  # user_profiles policy TTL
        
        ttl = cache_policies.get_ttl_for_key("unknown_key")
        assert ttl == 3600  # default TTL
    
    def test_get_policies_by_event(self, cache_policies):
        """Test getting policies by invalidation event."""
        policies = cache_policies.get_policies_by_event("user_profile_updated")
        assert "user_profiles" in policies
    
    def test_get_policies_by_tag(self, cache_policies):
        """Test getting policies by tag."""
        policies = cache_policies.get_policies_by_tag("ai_analysis")
        assert "sentiment_results" in policies
        assert "bot_detection" in policies


class TestCacheInvalidationHandler:
    """Test cache invalidation handler."""
    
    async def test_user_profile_update_handler(self, invalidation_handler, cache_manager):
        """Test user profile update invalidation."""
        cache_manager.invalidate_by_pattern = AsyncMock(return_value=5)
        
        await invalidation_handler._handle_user_profile_update({"user_id": "123"})
        
        # Should invalidate multiple patterns
        assert cache_manager.invalidate_by_pattern.call_count >= 1
    
    async def test_model_update_handler(self, invalidation_handler, cache_manager):
        """Test AI model update invalidation."""
        cache_manager.invalidate_by_tags = AsyncMock(return_value=10)
        cache_manager.invalidate_by_pattern = AsyncMock(return_value=5)
        
        await invalidation_handler._handle_sentiment_model_update({
            "model_version": "v2.0"
        })
        
        cache_manager.invalidate_by_tags.assert_called_with(["sentiment", "ai_analysis"])
    
    async def test_campaign_update_handler(self, invalidation_handler, cache_manager):
        """Test campaign update invalidation."""
        cache_manager.invalidate_by_pattern = AsyncMock(return_value=3)
        
        await invalidation_handler._handle_campaign_update({"campaign_id": "camp_123"})
        
        # Should invalidate campaign-specific patterns
        assert cache_manager.invalidate_by_pattern.call_count >= 1
    
    async def test_event_registration_and_handling(self, invalidation_handler):
        """Test event handler registration and execution."""
        # Register custom handler
        handler_called = False
        
        async def custom_handler(data):
            nonlocal handler_called
            handler_called = True
        
        invalidation_handler.register_handler("custom_event", custom_handler)
        
        # Trigger event
        await invalidation_handler.handle_event("custom_event", {"test": "data"})
        
        assert handler_called is True


class TestCacheMonitor:
    """Test cache monitoring functionality."""
    
    async def test_record_metrics(self, cache_monitor, redis_manager):
        """Test recording cache metrics."""
        redis_manager.incr = AsyncMock(return_value=1)
        redis_manager.set = AsyncMock(return_value=True)
        
        await cache_monitor.record_hit("test_key", response_time=5.0)
        await cache_monitor.record_miss("test_key", response_time=10.0)
        await cache_monitor.record_set("test_key", size_bytes=1024)
        
        # Verify metrics were recorded
        assert redis_manager.incr.call_count >= 3
    
    async def test_get_global_metrics(self, cache_monitor, redis_manager):
        """Test getting global cache metrics."""
        # Mock metric values
        redis_manager.get.side_effect = [
            "100",  # hits
            "20",   # misses
            "80",   # sets
            "5",    # deletes
            "2",    # evictions
            "1",    # errors
            "120",  # total_requests
            "7.5"   # avg_response_time
        ]
        
        metrics = await cache_monitor.get_global_metrics()
        
        assert metrics.hits == 100
        assert metrics.misses == 20
        assert metrics.hit_rate == 100 / 120  # hits / total_requests
        assert metrics.avg_response_time == 7.5
    
    async def test_get_cache_health(self, cache_monitor, redis_manager):
        """Test cache health assessment."""
        # Mock good metrics
        redis_manager.get.side_effect = [
            "900",  # hits
            "100",  # misses
            "800",  # sets
            "50",   # deletes
            "10",   # evictions
            "5",    # errors
            "1000", # total_requests
            "8.0"   # avg_response_time
        ]
        
        health = await cache_monitor.get_cache_health()
        
        assert health["status"] in ["healthy", "warning", "critical"]
        assert "health_score" in health
        assert "issues" in health
        assert "metrics" in health
    
    async def test_export_metrics(self, cache_monitor):
        """Test metrics export functionality."""
        # Mock methods
        cache_monitor.get_global_metrics = AsyncMock(return_value=CacheMetrics())
        cache_monitor.get_top_keys = AsyncMock(return_value=[])
        cache_monitor.get_cache_health = AsyncMock(return_value={"status": "healthy"})
        
        export_data = await cache_monitor.export_metrics()
        
        assert "export_time" in export_data
        assert "global_metrics" in export_data
        assert "top_keys" in export_data
        assert "health" in export_data


class TestIntegration:
    """Integration tests for the caching system."""
    
    async def test_full_cache_workflow(self, cache_manager, cache_policies, 
                                     invalidation_handler, redis_manager):
        """Test complete cache workflow."""
        # Setup mocks
        redis_manager.set.return_value = True
        redis_manager.get.side_effect = [None, None]  # Cache miss
        
        # 1. Set cache with policy
        policy = cache_policies.get_policy("user_profiles")
        result = await cache_manager.set(
            "user:123:profile",
            {"name": "John Doe", "email": "john@example.com"},
            ttl=policy.ttl,
            tags=policy.tags
        )
        assert result is True
        
        # 2. Trigger invalidation event
        cache_manager.invalidate_by_pattern = AsyncMock(return_value=1)
        await invalidation_handler.handle_event("user_profile_updated", {"user_id": "123"})
        
        # Verify invalidation was called
        cache_manager.invalidate_by_pattern.assert_called()
    
    async def test_cache_aside_with_policies(self, cache_manager, cache_policies, redis_manager):
        """Test cache-aside pattern with policies."""
        # Mock cache miss
        redis_manager.get.return_value = None
        cache_manager.set = AsyncMock(return_value=True)
        
        # Mock data fetch
        async def fetch_user_profile():
            return {"user_id": "123", "name": "John Doe"}
        
        # Get policy
        policy = cache_policies.get_policy("user_profiles")
        
        # Use cache-aside pattern
        data = await cache_manager.cache_aside_get(
            "user:123:profile",
            fetch_user_profile,
            ttl=policy.ttl,
            tags=policy.tags
        )
        
        assert data["user_id"] == "123"
        cache_manager.set.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])