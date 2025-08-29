"""Simple test for Redis caching system implementation."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from shared.cache.cache_policies import CachePolicies, CachePolicyConfig, CachePolicy
from shared.cache.cache_manager import CacheStats


class TestCachePolicies:
    """Test cache policies functionality."""
    
    def test_default_policies_loaded(self):
        """Test that default policies are loaded."""
        cache_policies = CachePolicies()
        assert "user_profiles" in cache_policies.policies
        assert "sentiment_results" in cache_policies.policies
        assert "dashboard_metrics" in cache_policies.policies
        assert "bot_detection" in cache_policies.policies
        assert "campaign_data" in cache_policies.policies
    
    def test_get_policy(self):
        """Test getting cache policy."""
        cache_policies = CachePolicies()
        policy = cache_policies.get_policy("user_profiles")
        assert policy is not None
        assert policy.ttl == 3600
        assert "user_data" in policy.tags
    
    def test_add_custom_policy(self):
        """Test adding custom cache policy."""
        cache_policies = CachePolicies()
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
        assert "custom" in retrieved_policy.tags
    
    def test_get_ttl_for_key(self):
        """Test TTL determination for keys."""
        cache_policies = CachePolicies()
        ttl = cache_policies.get_ttl_for_key("user_profiles:123")
        assert ttl == 3600  # user_profiles policy TTL
        
        ttl = cache_policies.get_ttl_for_key("unknown_key")
        assert ttl == 3600  # default TTL
    
    def test_get_policies_by_event(self):
        """Test getting policies by invalidation event."""
        cache_policies = CachePolicies()
        policies = cache_policies.get_policies_by_event("user_profile_updated")
        assert "user_profiles" in policies
    
    def test_get_policies_by_tag(self):
        """Test getting policies by tag."""
        cache_policies = CachePolicies()
        policies = cache_policies.get_policies_by_tag("ai_analysis")
        assert "sentiment_results" in policies
        assert "bot_detection" in policies
    
    def test_list_policies(self):
        """Test listing all policies."""
        cache_policies = CachePolicies()
        policies_list = cache_policies.list_policies()
        
        assert isinstance(policies_list, dict)
        assert "user_profiles" in policies_list
        assert "ttl" in policies_list["user_profiles"]
        assert "tags" in policies_list["user_profiles"]


class TestCacheStats:
    """Test cache statistics functionality."""
    
    def test_cache_stats_initialization(self):
        """Test cache stats initialization."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.evictions == 0
        assert stats.hit_rate == 0.0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats()
        stats.hits = 80
        stats.misses = 20
        
        assert stats.hit_rate == 0.8  # 80 / (80 + 20)
    
    def test_hit_rate_with_no_requests(self):
        """Test hit rate when no requests made."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0


class TestCacheManagerBasics:
    """Test basic cache manager functionality without async."""
    
    def test_make_cache_key(self):
        """Test cache key creation."""
        from shared.cache.cache_manager import CacheManager
        
        # Mock redis manager
        redis_manager = MagicMock()
        cache_manager = CacheManager(redis_manager, namespace="test")
        
        # Test make_cache_key
        key = cache_manager.make_cache_key("user", "123", "profile")
        assert key == "user:123:profile"
    
    def test_hash_key(self):
        """Test hash-based key creation."""
        from shared.cache.cache_manager import CacheManager
        
        # Mock redis manager
        redis_manager = MagicMock()
        cache_manager = CacheManager(redis_manager, namespace="test")
        
        # Test hash_key
        hash_key = cache_manager.hash_key({"user_id": 123, "action": "login"})
        assert len(hash_key) == 32  # MD5 hash length
        
        # Same input should produce same hash
        hash_key2 = cache_manager.hash_key({"user_id": 123, "action": "login"})
        assert hash_key == hash_key2
    
    def test_namespaced_keys(self):
        """Test namespaced key creation."""
        from shared.cache.cache_manager import CacheManager
        
        redis_manager = MagicMock()
        cache_manager = CacheManager(redis_manager, namespace="test")
        
        cache_key = cache_manager._make_key("user:123")
        assert cache_key == "test:cache:user:123"
        
        meta_key = cache_manager._make_metadata_key("user:123")
        assert meta_key == "test:meta:user:123"
        
        tag_key = cache_manager._make_tag_key("user_data")
        assert tag_key == "test:tag:user_data"


class TestCacheIntegration:
    """Test cache system integration."""
    
    def test_policies_integration(self):
        """Test that policies work with cache manager."""
        cache_policies = CachePolicies()
        
        # Test getting policy for sentiment analysis
        policy = cache_policies.get_policy("sentiment_results")
        assert policy is not None
        assert policy.ttl == 86400  # 24 hours
        assert "sentiment" in policy.tags
        assert "ai_analysis" in policy.tags
        
        # Test invalidation events
        events = cache_policies.get_invalidation_events("sentiment_results")
        assert "sentiment_model_updated" in events
    
    def test_cache_key_patterns(self):
        """Test cache key patterns match policies."""
        cache_policies = CachePolicies()
        
        # Test TTL inference from key patterns
        ttl = cache_policies.get_ttl_for_key("sentiment_results:post:123")
        assert ttl == 86400  # Should match sentiment_results policy
        
        ttl = cache_policies.get_ttl_for_key("dashboard_metrics:overview")
        assert ttl == 300  # Should match dashboard_metrics policy
    
    def test_tag_based_invalidation_mapping(self):
        """Test tag-based invalidation mapping."""
        cache_policies = CachePolicies()
        
        # Test getting policies by AI analysis tag
        ai_policies = cache_policies.get_policies_by_tag("ai_analysis")
        assert "sentiment_results" in ai_policies
        assert "bot_detection" in ai_policies
        
        # Test getting policies by dashboard tag
        dashboard_policies = cache_policies.get_policies_by_tag("dashboard")
        assert "dashboard_metrics" in dashboard_policies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])