"""Cache monitoring and analytics."""

import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog
from ..database.redis import RedisManager

logger = structlog.get_logger(__name__)


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    hit_rate: float = 0.0
    memory_usage: int = 0
    key_count: int = 0
    expired_keys: int = 0


@dataclass
class CacheKeyMetrics:
    """Metrics for individual cache keys."""
    key: str
    hits: int = 0
    misses: int = 0
    last_accessed: Optional[datetime] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    size_bytes: int = 0
    ttl_remaining: Optional[int] = None


class CacheMonitor:
    """Monitors cache performance and provides analytics."""
    
    def __init__(self, redis_manager: RedisManager, namespace: str = "dharma"):
        self.redis = redis_manager
        self.namespace = namespace
        self.metrics_key = f"{namespace}:cache_metrics"
        self.key_metrics_prefix = f"{namespace}:key_metrics"
        
    async def record_hit(self, key: str, response_time: float = 0.0):
        """Record cache hit."""
        await self._update_global_metrics("hits", 1)
        await self._update_global_metrics("total_requests", 1)
        await self._update_response_time(response_time)
        await self._update_key_metrics(key, "hits", 1)
        
    async def record_miss(self, key: str, response_time: float = 0.0):
        """Record cache miss."""
        await self._update_global_metrics("misses", 1)
        await self._update_global_metrics("total_requests", 1)
        await self._update_response_time(response_time)
        await self._update_key_metrics(key, "misses", 1)
        
    async def record_set(self, key: str, size_bytes: int = 0):
        """Record cache set operation."""
        await self._update_global_metrics("sets", 1)
        await self._update_key_metrics(key, "size_bytes", size_bytes)
        
    async def record_delete(self, key: str):
        """Record cache delete operation."""
        await self._update_global_metrics("deletes", 1)
        
    async def record_eviction(self, key: str):
        """Record cache eviction."""
        await self._update_global_metrics("evictions", 1)
        
    async def record_error(self, operation: str, error: str):
        """Record cache error."""
        await self._update_global_metrics("errors", 1)
        logger.error("Cache operation error", operation=operation, error=error)
        
    async def _update_global_metrics(self, metric: str, value: int):
        """Update global cache metrics."""
        try:
            await self.redis.incr(f"{self.metrics_key}:{metric}", value)
        except Exception as e:
            logger.error("Failed to update global metrics", metric=metric, error=str(e))
            
    async def _update_response_time(self, response_time: float):
        """Update average response time."""
        try:
            # Use exponential moving average
            current_avg = await self.redis.get(f"{self.metrics_key}:avg_response_time") or 0.0
            current_avg = float(current_avg)
            
            # EMA with alpha = 0.1
            new_avg = 0.1 * response_time + 0.9 * current_avg
            await self.redis.set(f"{self.metrics_key}:avg_response_time", new_avg)
            
        except Exception as e:
            logger.error("Failed to update response time", error=str(e))
            
    async def _update_key_metrics(self, key: str, metric: str, value: Any):
        """Update metrics for specific key."""
        try:
            key_metrics_key = f"{self.key_metrics_prefix}:{key}"
            
            if metric in ["hits", "misses"]:
                await self.redis.incr(f"{key_metrics_key}:{metric}", value)
                # Update last accessed time
                await self.redis.set(
                    f"{key_metrics_key}:last_accessed", 
                    datetime.utcnow().isoformat()
                )
            else:
                await self.redis.set(f"{key_metrics_key}:{metric}", value)
                
        except Exception as e:
            logger.error("Failed to update key metrics", key=key, metric=metric, error=str(e))
            
    async def get_global_metrics(self) -> CacheMetrics:
        """Get global cache metrics."""
        try:
            metrics = CacheMetrics()
            
            # Get all metric values
            metric_keys = [
                "hits", "misses", "sets", "deletes", 
                "evictions", "errors", "total_requests", "avg_response_time"
            ]
            
            for metric in metric_keys:
                value = await self.redis.get(f"{self.metrics_key}:{metric}")
                if value is not None:
                    if metric == "avg_response_time":
                        setattr(metrics, metric, float(value))
                    else:
                        setattr(metrics, metric, int(value))
            
            # Calculate hit rate
            if metrics.total_requests > 0:
                metrics.hit_rate = metrics.hits / metrics.total_requests
            
            # Get memory usage and key count from Redis INFO
            info = await self.redis.client.info("memory")
            metrics.memory_usage = info.get("used_memory", 0)
            
            info = await self.redis.client.info("keyspace")
            db_info = info.get("db0", {})
            if isinstance(db_info, dict):
                metrics.key_count = db_info.get("keys", 0)
                metrics.expired_keys = db_info.get("expires", 0)
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get global metrics", error=str(e))
            return CacheMetrics()
            
    async def get_key_metrics(self, key: str) -> CacheKeyMetrics:
        """Get metrics for specific key."""
        try:
            key_metrics_key = f"{self.key_metrics_prefix}:{key}"
            metrics = CacheKeyMetrics(key=key)
            
            # Get key-specific metrics
            hits = await self.redis.get(f"{key_metrics_key}:hits")
            misses = await self.redis.get(f"{key_metrics_key}:misses")
            size_bytes = await self.redis.get(f"{key_metrics_key}:size_bytes")
            last_accessed = await self.redis.get(f"{key_metrics_key}:last_accessed")
            
            if hits is not None:
                metrics.hits = int(hits)
            if misses is not None:
                metrics.misses = int(misses)
            if size_bytes is not None:
                metrics.size_bytes = int(size_bytes)
            if last_accessed:
                try:
                    metrics.last_accessed = datetime.fromisoformat(last_accessed)
                except ValueError:
                    pass
            
            # Get TTL for the actual cache key
            cache_key = f"{self.namespace}:cache:{key}"
            ttl = await self.redis.client.ttl(cache_key)
            if ttl > 0:
                metrics.ttl_remaining = ttl
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get key metrics", key=key, error=str(e))
            return CacheKeyMetrics(key=key)
            
    async def get_top_keys(self, limit: int = 10, sort_by: str = "hits") -> List[CacheKeyMetrics]:
        """Get top cache keys by specified metric."""
        try:
            # Get all key metrics keys
            pattern = f"{self.key_metrics_prefix}:*:{sort_by}"
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
            
            # Get values and sort
            key_values = []
            for key in keys:
                value = await self.redis.get(key)
                if value is not None:
                    # Extract original key name
                    original_key = key.replace(f"{self.key_metrics_prefix}:", "").replace(f":{sort_by}", "")
                    key_values.append((original_key, int(value)))
            
            # Sort by value descending
            key_values.sort(key=lambda x: x[1], reverse=True)
            
            # Get full metrics for top keys
            top_keys = []
            for key_name, _ in key_values[:limit]:
                metrics = await self.get_key_metrics(key_name)
                top_keys.append(metrics)
            
            return top_keys
            
        except Exception as e:
            logger.error("Failed to get top keys", sort_by=sort_by, error=str(e))
            return []
            
    async def get_cache_health(self) -> Dict[str, Any]:
        """Get overall cache health status."""
        try:
            metrics = await self.get_global_metrics()
            
            # Calculate health indicators
            health_score = 100.0
            issues = []
            
            # Hit rate health (good > 80%, warning > 60%, critical < 60%)
            if metrics.hit_rate < 0.6:
                health_score -= 30
                issues.append(f"Low hit rate: {metrics.hit_rate:.2%}")
            elif metrics.hit_rate < 0.8:
                health_score -= 15
                issues.append(f"Moderate hit rate: {metrics.hit_rate:.2%}")
            
            # Error rate health
            if metrics.total_requests > 0:
                error_rate = metrics.errors / metrics.total_requests
                if error_rate > 0.05:  # > 5% error rate
                    health_score -= 25
                    issues.append(f"High error rate: {error_rate:.2%}")
                elif error_rate > 0.01:  # > 1% error rate
                    health_score -= 10
                    issues.append(f"Moderate error rate: {error_rate:.2%}")
            
            # Response time health (good < 10ms, warning < 50ms, critical > 50ms)
            if metrics.avg_response_time > 50:
                health_score -= 20
                issues.append(f"High response time: {metrics.avg_response_time:.2f}ms")
            elif metrics.avg_response_time > 10:
                health_score -= 10
                issues.append(f"Moderate response time: {metrics.avg_response_time:.2f}ms")
            
            # Memory usage health (warning > 80%, critical > 95%)
            try:
                info = await self.redis.client.info("memory")
                max_memory = info.get("maxmemory", 0)
                if max_memory > 0:
                    memory_usage_pct = metrics.memory_usage / max_memory
                    if memory_usage_pct > 0.95:
                        health_score -= 25
                        issues.append(f"Critical memory usage: {memory_usage_pct:.1%}")
                    elif memory_usage_pct > 0.8:
                        health_score -= 15
                        issues.append(f"High memory usage: {memory_usage_pct:.1%}")
            except Exception:
                pass
            
            # Determine health status
            if health_score >= 90:
                status = "healthy"
            elif health_score >= 70:
                status = "warning"
            else:
                status = "critical"
            
            return {
                "status": status,
                "health_score": max(0, health_score),
                "issues": issues,
                "metrics": asdict(metrics),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get cache health", error=str(e))
            return {
                "status": "error",
                "health_score": 0,
                "issues": [f"Health check failed: {str(e)}"],
                "metrics": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def reset_metrics(self):
        """Reset all cache metrics."""
        try:
            # Delete global metrics
            pattern = f"{self.metrics_key}:*"
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
                await self.redis.delete(*keys)
            
            # Delete key metrics
            pattern = f"{self.key_metrics_prefix}:*"
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
                await self.redis.delete(*keys)
            
            logger.info("Cache metrics reset")
            
        except Exception as e:
            logger.error("Failed to reset metrics", error=str(e))
            
    async def export_metrics(self, start_time: Optional[datetime] = None, 
                           end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Export cache metrics for analysis."""
        try:
            global_metrics = await self.get_global_metrics()
            top_keys = await self.get_top_keys(limit=50)
            health = await self.get_cache_health()
            
            return {
                "export_time": datetime.utcnow().isoformat(),
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None
                },
                "global_metrics": asdict(global_metrics),
                "top_keys": [asdict(key_metrics) for key_metrics in top_keys],
                "health": health
            }
            
        except Exception as e:
            logger.error("Failed to export metrics", error=str(e))
            return {
                "export_time": datetime.utcnow().isoformat(),
                "error": str(e)
            }