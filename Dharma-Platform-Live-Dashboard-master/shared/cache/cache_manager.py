"""Redis cache manager with intelligent invalidation and cache-aside pattern."""

import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog
from ..database.redis import RedisManager

logger = structlog.get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    hit_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: List[str] = None


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheManager:
    """Advanced Redis cache manager with intelligent invalidation."""
    
    def __init__(self, redis_manager: RedisManager, namespace: str = "dharma"):
        self.redis = redis_manager
        self.namespace = namespace
        self.stats = CacheStats()
        self._invalidation_handlers: Dict[str, List[Callable]] = {}
        
    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self.namespace}:cache:{key}"
    
    def _make_metadata_key(self, key: str) -> str:
        """Create metadata key for cache entry."""
        return f"{self.namespace}:meta:{key}"
    
    def _make_tag_key(self, tag: str) -> str:
        """Create tag key for cache invalidation."""
        return f"{self.namespace}:tag:{tag}"
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with cache-aside pattern."""
        cache_key = self._make_key(key)
        meta_key = self._make_metadata_key(key)
        
        try:
            # Get value and metadata
            value = await self.redis.get(cache_key)
            metadata = await self.redis.get(meta_key)
            
            if value is None:
                self.stats.misses += 1
                logger.debug("Cache miss", key=key)
                return default
            
            # Update access statistics
            if metadata:
                try:
                    meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                    meta_dict['hit_count'] = meta_dict.get('hit_count', 0) + 1
                    meta_dict['last_accessed'] = datetime.utcnow().isoformat()
                    await self.redis.set(meta_key, json.dumps(meta_dict))
                except Exception as e:
                    logger.warning("Failed to update cache metadata", key=key, error=str(e))
            
            self.stats.hits += 1
            logger.debug("Cache hit", key=key)
            return value
            
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            self.stats.misses += 1
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in cache with metadata and tags."""
        cache_key = self._make_key(key)
        meta_key = self._make_metadata_key(key)
        
        try:
            # Create metadata
            now = datetime.utcnow()
            metadata = {
                'created_at': now.isoformat(),
                'expires_at': (now + timedelta(seconds=ttl)).isoformat() if ttl else None,
                'hit_count': 0,
                'tags': tags or []
            }
            
            # Set value and metadata
            success = await self.redis.set(cache_key, value, expire=ttl)
            if success:
                await self.redis.set(meta_key, json.dumps(metadata), expire=ttl)
                
                # Add to tag indexes
                if tags:
                    for tag in tags:
                        tag_key = self._make_tag_key(tag)
                        await self.redis.lpush(tag_key, key)
                        if ttl:
                            await self.redis.expire(tag_key, ttl + 3600)  # Tag expires 1 hour after data
                
                self.stats.sets += 1
                logger.debug("Cache set", key=key, ttl=ttl, tags=tags)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        cache_key = self._make_key(key)
        meta_key = self._make_metadata_key(key)
        
        try:
            # Get metadata to find tags
            metadata = await self.redis.get(meta_key)
            if metadata:
                try:
                    meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                    tags = meta_dict.get('tags', [])
                    
                    # Remove from tag indexes
                    for tag in tags:
                        tag_key = self._make_tag_key(tag)
                        # Remove key from tag list (this is a list operation)
                        await self.redis.client.lrem(tag_key, 0, key)
                        
                except Exception as e:
                    logger.warning("Failed to clean up tag indexes", key=key, error=str(e))
            
            # Delete cache entry and metadata
            deleted = await self.redis.delete(cache_key, meta_key)
            
            if deleted > 0:
                self.stats.deletes += 1
                logger.debug("Cache delete", key=key)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Cache delete failed", key=key, error=str(e))
            return False
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        try:
            # Use Redis SCAN to find matching keys
            cache_pattern = self._make_key(pattern)
            keys = []
            
            cursor = 0
            while True:
                cursor, batch = await self.redis.client.scan(
                    cursor=cursor, 
                    match=cache_pattern, 
                    count=100
                )
                keys.extend(batch)
                if cursor == 0:
                    break
            
            if not keys:
                return 0
            
            # Extract original keys and delete
            original_keys = []
            for cache_key in keys:
                if cache_key.startswith(f"{self.namespace}:cache:"):
                    original_key = cache_key[len(f"{self.namespace}:cache:"):]
                    original_keys.append(original_key)
            
            deleted_count = 0
            for key in original_keys:
                if await self.delete(key):
                    deleted_count += 1
            
            logger.info("Pattern invalidation", pattern=pattern, deleted=deleted_count)
            return deleted_count
            
        except Exception as e:
            logger.error("Pattern invalidation failed", pattern=pattern, error=str(e))
            return 0
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate cache entries by tags."""
        try:
            keys_to_delete = set()
            
            for tag in tags:
                tag_key = self._make_tag_key(tag)
                
                # Get all keys with this tag
                tag_keys = []
                try:
                    # Get all items from the list
                    length = await self.redis.client.llen(tag_key)
                    if length > 0:
                        tag_keys = await self.redis.client.lrange(tag_key, 0, -1)
                except Exception as e:
                    logger.warning("Failed to get tag keys", tag=tag, error=str(e))
                    continue
                
                keys_to_delete.update(tag_keys)
                
                # Clean up tag index
                await self.redis.delete(tag_key)
            
            # Delete all tagged keys
            deleted_count = 0
            for key in keys_to_delete:
                if await self.delete(key):
                    deleted_count += 1
            
            logger.info("Tag invalidation", tags=tags, deleted=deleted_count)
            return deleted_count
            
        except Exception as e:
            logger.error("Tag invalidation failed", tags=tags, error=str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        cache_key = self._make_key(key)
        return await self.redis.exists(cache_key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for cache key."""
        cache_key = self._make_key(key)
        meta_key = self._make_metadata_key(key)
        
        success = await self.redis.expire(cache_key, seconds)
        if success:
            await self.redis.expire(meta_key, seconds)
        
        return success
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats
    
    async def get_cache_info(self, key: str) -> Optional[Dict]:
        """Get cache entry information."""
        meta_key = self._make_metadata_key(key)
        metadata = await self.redis.get(meta_key)
        
        if metadata:
            try:
                return json.loads(metadata) if isinstance(metadata, str) else metadata
            except Exception:
                return None
        
        return None
    
    async def clear_namespace(self) -> int:
        """Clear all cache entries in namespace."""
        try:
            pattern = f"{self.namespace}:*"
            keys = []
            
            cursor = 0
            while True:
                cursor, batch = await self.redis.client.scan(
                    cursor=cursor, 
                    match=pattern, 
                    count=100
                )
                keys.extend(batch)
                if cursor == 0:
                    break
            
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info("Namespace cleared", namespace=self.namespace, deleted=deleted)
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error("Namespace clear failed", namespace=self.namespace, error=str(e))
            return 0
    
    def register_invalidation_handler(self, event_type: str, handler: Callable):
        """Register handler for cache invalidation events."""
        if event_type not in self._invalidation_handlers:
            self._invalidation_handlers[event_type] = []
        
        self._invalidation_handlers[event_type].append(handler)
        logger.debug("Invalidation handler registered", event_type=event_type)
    
    async def trigger_invalidation_event(self, event_type: str, data: Dict):
        """Trigger cache invalidation event."""
        handlers = self._invalidation_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error("Invalidation handler failed", 
                           event_type=event_type, error=str(e))
        
        # Publish event to Redis for other instances
        await self.redis.publish(f"cache_invalidation:{event_type}", data)
    
    async def cache_aside_get(
        self, 
        key: str, 
        fetch_func: Callable,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Any:
        """Cache-aside pattern: get from cache or fetch and cache."""
        # Try cache first
        value = await self.get(key)
        if value is not None:
            return value
        
        # Cache miss - fetch from source
        try:
            value = await fetch_func()
            if value is not None:
                await self.set(key, value, ttl=ttl, tags=tags)
            return value
            
        except Exception as e:
            logger.error("Cache-aside fetch failed", key=key, error=str(e))
            raise
    
    def make_cache_key(self, *parts: str) -> str:
        """Create cache key from parts."""
        key_parts = [str(part) for part in parts]
        return ":".join(key_parts)
    
    def hash_key(self, data: Union[str, Dict, List]) -> str:
        """Create hash-based cache key."""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)
        
        return hashlib.md5(content.encode()).hexdigest()