"""Cache policies and TTL management."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class CachePolicy(Enum):
    """Cache policy types."""
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    CACHE_ASIDE = "cache_aside"
    REFRESH_AHEAD = "refresh_ahead"


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    TTL = "ttl"
    EVENT_BASED = "event_based"
    TAG_BASED = "tag_based"
    PATTERN_BASED = "pattern_based"


@dataclass
class CachePolicyConfig:
    """Cache policy configuration."""
    name: str
    ttl: Optional[int] = None
    policy: CachePolicy = CachePolicy.CACHE_ASIDE
    invalidation_strategy: InvalidationStrategy = InvalidationStrategy.TTL
    invalidation_events: List[str] = None
    tags: List[str] = None
    max_size: Optional[int] = None
    refresh_threshold: float = 0.8  # Refresh when 80% of TTL elapsed


class CachePolicies:
    """Manages cache policies and TTL configurations."""
    
    def __init__(self):
        self.policies: Dict[str, CachePolicyConfig] = {}
        self._setup_default_policies()
    
    def _setup_default_policies(self):
        """Setup default cache policies for different data types."""
        
        # User profiles - medium TTL, invalidate on profile updates
        self.policies["user_profiles"] = CachePolicyConfig(
            name="user_profiles",
            ttl=3600,  # 1 hour
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            invalidation_events=["user_profile_updated", "user_deleted"],
            tags=["user_data"]
        )
        
        # Sentiment analysis results - long TTL, invalidate on model updates
        self.policies["sentiment_results"] = CachePolicyConfig(
            name="sentiment_results",
            ttl=86400,  # 24 hours
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            invalidation_events=["sentiment_model_updated"],
            tags=["ai_analysis", "sentiment"]
        )
        
        # Bot detection results - medium TTL, invalidate on model updates
        self.policies["bot_detection"] = CachePolicyConfig(
            name="bot_detection",
            ttl=7200,  # 2 hours
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            invalidation_events=["bot_model_updated"],
            tags=["ai_analysis", "bot_detection"]
        )
        
        # Campaign data - short TTL, invalidate on campaign updates
        self.policies["campaign_data"] = CachePolicyConfig(
            name="campaign_data",
            ttl=1800,  # 30 minutes
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            invalidation_events=["campaign_updated", "campaign_deleted"],
            tags=["campaign_analysis"]
        )
        
        # Dashboard metrics - very short TTL, high refresh rate
        self.policies["dashboard_metrics"] = CachePolicyConfig(
            name="dashboard_metrics",
            ttl=300,  # 5 minutes
            invalidation_strategy=InvalidationStrategy.TTL,
            tags=["dashboard", "metrics"]
        )
        
        # API responses - short TTL, pattern-based invalidation
        self.policies["api_responses"] = CachePolicyConfig(
            name="api_responses",
            ttl=600,  # 10 minutes
            invalidation_strategy=InvalidationStrategy.PATTERN_BASED,
            tags=["api_cache"]
        )
        
        # Database query results - medium TTL, tag-based invalidation
        self.policies["db_queries"] = CachePolicyConfig(
            name="db_queries",
            ttl=1800,  # 30 minutes
            invalidation_strategy=InvalidationStrategy.TAG_BASED,
            tags=["database", "queries"]
        )
        
        # Session data - long TTL, event-based invalidation
        self.policies["session_data"] = CachePolicyConfig(
            name="session_data",
            ttl=7200,  # 2 hours
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            invalidation_events=["user_logout", "session_expired"],
            tags=["session"]
        )
        
        # Static content - very long TTL, manual invalidation
        self.policies["static_content"] = CachePolicyConfig(
            name="static_content",
            ttl=604800,  # 1 week
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            invalidation_events=["content_updated"],
            tags=["static"]
        )
        
        # Real-time data - very short TTL
        self.policies["realtime_data"] = CachePolicyConfig(
            name="realtime_data",
            ttl=60,  # 1 minute
            invalidation_strategy=InvalidationStrategy.TTL,
            tags=["realtime"]
        )
    
    def get_policy(self, policy_name: str) -> Optional[CachePolicyConfig]:
        """Get cache policy by name."""
        return self.policies.get(policy_name)
    
    def add_policy(self, policy: CachePolicyConfig):
        """Add or update cache policy."""
        self.policies[policy.name] = policy
        logger.info("Cache policy added", name=policy.name)
    
    def remove_policy(self, policy_name: str) -> bool:
        """Remove cache policy."""
        if policy_name in self.policies:
            del self.policies[policy_name]
            logger.info("Cache policy removed", name=policy_name)
            return True
        return False
    
    def get_ttl_for_key(self, key: str, policy_name: Optional[str] = None) -> Optional[int]:
        """Get TTL for cache key based on policy."""
        if policy_name:
            policy = self.get_policy(policy_name)
            if policy:
                return policy.ttl
        
        # Try to infer policy from key pattern
        for policy_name, policy in self.policies.items():
            if policy_name in key:
                return policy.ttl
        
        # Default TTL
        return 3600  # 1 hour
    
    def get_tags_for_key(self, key: str, policy_name: Optional[str] = None) -> List[str]:
        """Get tags for cache key based on policy."""
        if policy_name:
            policy = self.get_policy(policy_name)
            if policy and policy.tags:
                return policy.tags
        
        # Try to infer policy from key pattern
        for policy_name, policy in self.policies.items():
            if policy_name in key and policy.tags:
                return policy.tags
        
        return []
    
    def should_refresh_ahead(self, key: str, policy_name: Optional[str] = None, 
                           elapsed_time: int = 0, ttl: int = 0) -> bool:
        """Check if cache entry should be refreshed ahead of expiration."""
        if policy_name:
            policy = self.get_policy(policy_name)
            if policy and policy.policy == CachePolicy.REFRESH_AHEAD:
                threshold = ttl * policy.refresh_threshold
                return elapsed_time >= threshold
        
        return False
    
    def get_invalidation_events(self, policy_name: str) -> List[str]:
        """Get invalidation events for policy."""
        policy = self.get_policy(policy_name)
        if policy and policy.invalidation_events:
            return policy.invalidation_events
        return []
    
    def get_policies_by_event(self, event: str) -> List[str]:
        """Get policy names that should be invalidated by event."""
        matching_policies = []
        
        for policy_name, policy in self.policies.items():
            if (policy.invalidation_events and 
                event in policy.invalidation_events):
                matching_policies.append(policy_name)
        
        return matching_policies
    
    def get_policies_by_tag(self, tag: str) -> List[str]:
        """Get policy names that have the specified tag."""
        matching_policies = []
        
        for policy_name, policy in self.policies.items():
            if policy.tags and tag in policy.tags:
                matching_policies.append(policy_name)
        
        return matching_policies
    
    def list_policies(self) -> Dict[str, Dict[str, Any]]:
        """List all cache policies."""
        return {
            name: {
                "ttl": policy.ttl,
                "policy": policy.policy.value,
                "invalidation_strategy": policy.invalidation_strategy.value,
                "invalidation_events": policy.invalidation_events or [],
                "tags": policy.tags or [],
                "refresh_threshold": policy.refresh_threshold
            }
            for name, policy in self.policies.items()
        }