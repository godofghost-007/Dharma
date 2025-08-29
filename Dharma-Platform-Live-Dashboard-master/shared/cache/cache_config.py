"""Cache configuration and setup utilities."""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import structlog
from ..database.redis import RedisManager
from .cache_manager import CacheManager
from .cache_policies import CachePolicies
from .invalidation_handler import CacheInvalidationHandler
from .monitoring import CacheMonitor
from .cluster_manager import RedisClusterManager

logger = structlog.get_logger(__name__)


class CacheMode(Enum):
    """Cache deployment modes."""
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"


@dataclass
class CacheConfig:
    """Cache system configuration."""
    mode: CacheMode = CacheMode.STANDALONE
    redis_url: str = "redis://localhost:6379"
    max_connections: int = 20
    namespace: str = "dharma"
    
    # Cluster configuration
    cluster_nodes: Optional[List[Dict[str, Any]]] = None
    
    # Sentinel configuration
    sentinel_hosts: Optional[List[Dict[str, str]]] = None
    sentinel_service_name: str = "mymaster"
    
    # Performance settings
    connection_pool_size: int = 20
    socket_keepalive: bool = True
    health_check_interval: int = 30
    
    # Cache behavior
    default_ttl: int = 3600
    max_memory_policy: str = "allkeys-lru"
    enable_compression: bool = False
    compression_threshold: int = 1024
    
    # Monitoring
    enable_monitoring: bool = True
    metrics_retention_days: int = 7
    
    # Security
    password: Optional[str] = None
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None


class CacheSystemBuilder:
    """Builder for cache system components."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_manager: Optional[RedisManager] = None
        self.cache_manager: Optional[CacheManager] = None
        self.cache_policies: Optional[CachePolicies] = None
        self.invalidation_handler: Optional[CacheInvalidationHandler] = None
        self.cache_monitor: Optional[CacheMonitor] = None
        self.cluster_manager: Optional[RedisClusterManager] = None
    
    async def build_redis_manager(self) -> RedisManager:
        """Build and configure Redis manager."""
        if self.redis_manager:
            return self.redis_manager
        
        cluster_mode = self.config.mode == CacheMode.CLUSTER
        
        self.redis_manager = RedisManager(
            redis_url=self.config.redis_url,
            max_connections=self.config.max_connections,
            cluster_mode=cluster_mode,
            cluster_nodes=self.config.cluster_nodes
        )
        
        await self.redis_manager.connect()
        logger.info("Redis manager initialized", mode=self.config.mode.value)
        
        return self.redis_manager
    
    async def build_cache_manager(self) -> CacheManager:
        """Build and configure cache manager."""
        if self.cache_manager:
            return self.cache_manager
        
        if not self.redis_manager:
            await self.build_redis_manager()
        
        self.cache_manager = CacheManager(
            redis_manager=self.redis_manager,
            namespace=self.config.namespace
        )
        
        logger.info("Cache manager initialized")
        return self.cache_manager
    
    def build_cache_policies(self) -> CachePolicies:
        """Build and configure cache policies."""
        if self.cache_policies:
            return self.cache_policies
        
        self.cache_policies = CachePolicies()
        logger.info("Cache policies initialized")
        
        return self.cache_policies
    
    async def build_invalidation_handler(self) -> CacheInvalidationHandler:
        """Build and configure invalidation handler."""
        if self.invalidation_handler:
            return self.invalidation_handler
        
        if not self.cache_manager:
            await self.build_cache_manager()
        
        if not self.cache_policies:
            self.build_cache_policies()
        
        self.invalidation_handler = CacheInvalidationHandler(
            cache_manager=self.cache_manager,
            cache_policies=self.cache_policies
        )
        
        logger.info("Invalidation handler initialized")
        return self.invalidation_handler
    
    async def build_cache_monitor(self) -> CacheMonitor:
        """Build and configure cache monitor."""
        if self.cache_monitor:
            return self.cache_monitor
        
        if not self.redis_manager:
            await self.build_redis_manager()
        
        self.cache_monitor = CacheMonitor(
            redis_manager=self.redis_manager,
            namespace=self.config.namespace
        )
        
        logger.info("Cache monitor initialized")
        return self.cache_monitor
    
    async def build_cluster_manager(self) -> Optional[RedisClusterManager]:
        """Build and configure cluster manager (cluster mode only)."""
        if self.config.mode != CacheMode.CLUSTER:
            return None
        
        if self.cluster_manager:
            return self.cluster_manager
        
        if not self.redis_manager:
            await self.build_redis_manager()
        
        self.cluster_manager = RedisClusterManager(
            redis_manager=self.redis_manager
        )
        
        logger.info("Cluster manager initialized")
        return self.cluster_manager
    
    async def build_complete_system(self) -> Dict[str, Any]:
        """Build complete cache system with all components."""
        components = {}
        
        # Core components
        components["redis_manager"] = await self.build_redis_manager()
        components["cache_manager"] = await self.build_cache_manager()
        components["cache_policies"] = self.build_cache_policies()
        components["invalidation_handler"] = await self.build_invalidation_handler()
        
        # Optional components
        if self.config.enable_monitoring:
            components["cache_monitor"] = await self.build_cache_monitor()
        
        if self.config.mode == CacheMode.CLUSTER:
            components["cluster_manager"] = await self.build_cluster_manager()
        
        logger.info("Complete cache system initialized", 
                   components=list(components.keys()))
        
        return components


def create_cache_config_from_env() -> CacheConfig:
    """Create cache configuration from environment variables."""
    config = CacheConfig()
    
    # Basic configuration
    config.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    config.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
    config.namespace = os.getenv("CACHE_NAMESPACE", "dharma")
    
    # Mode configuration
    mode_str = os.getenv("REDIS_MODE", "standalone").lower()
    if mode_str == "cluster":
        config.mode = CacheMode.CLUSTER
        
        # Parse cluster nodes from environment
        cluster_nodes_str = os.getenv("REDIS_CLUSTER_NODES", "")
        if cluster_nodes_str:
            nodes = []
            for node_str in cluster_nodes_str.split(","):
                host, port = node_str.strip().split(":")
                nodes.append({"host": host, "port": int(port)})
            config.cluster_nodes = nodes
    
    elif mode_str == "sentinel":
        config.mode = CacheMode.SENTINEL
        config.sentinel_service_name = os.getenv("REDIS_SENTINEL_SERVICE", "mymaster")
        
        # Parse sentinel hosts
        sentinel_hosts_str = os.getenv("REDIS_SENTINEL_HOSTS", "")
        if sentinel_hosts_str:
            hosts = []
            for host_str in sentinel_hosts_str.split(","):
                host, port = host_str.strip().split(":")
                hosts.append({"host": host, "port": port})
            config.sentinel_hosts = hosts
    
    # Performance settings
    config.default_ttl = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
    config.health_check_interval = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
    
    # Monitoring
    config.enable_monitoring = os.getenv("CACHE_ENABLE_MONITORING", "true").lower() == "true"
    config.metrics_retention_days = int(os.getenv("CACHE_METRICS_RETENTION_DAYS", "7"))
    
    # Security
    config.password = os.getenv("REDIS_PASSWORD")
    config.ssl_enabled = os.getenv("REDIS_SSL_ENABLED", "false").lower() == "true"
    config.ssl_cert_path = os.getenv("REDIS_SSL_CERT_PATH")
    config.ssl_key_path = os.getenv("REDIS_SSL_KEY_PATH")
    
    return config


async def initialize_cache_system(config: Optional[CacheConfig] = None) -> Dict[str, Any]:
    """Initialize complete cache system."""
    if config is None:
        config = create_cache_config_from_env()
    
    builder = CacheSystemBuilder(config)
    return await builder.build_complete_system()


class CacheHealthChecker:
    """Health checker for cache system."""
    
    def __init__(self, cache_system: Dict[str, Any]):
        self.cache_system = cache_system
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "overall_status": "healthy",
            "components": {},
            "issues": []
        }
        
        # Check Redis connection
        redis_manager = self.cache_system.get("redis_manager")
        if redis_manager:
            redis_healthy = await redis_manager.health_check()
            health_status["components"]["redis"] = {
                "status": "healthy" if redis_healthy else "unhealthy",
                "connected": redis_healthy
            }
            
            if not redis_healthy:
                health_status["overall_status"] = "unhealthy"
                health_status["issues"].append("Redis connection failed")
        
        # Check cluster health (if applicable)
        cluster_manager = self.cache_system.get("cluster_manager")
        if cluster_manager:
            cluster_health = await cluster_manager.check_cluster_health()
            health_status["components"]["cluster"] = {
                "status": cluster_health.overall_health,
                "cluster_state": cluster_health.cluster_state,
                "nodes_health": cluster_health.nodes_health
            }
            
            if cluster_health.overall_health != "healthy":
                health_status["overall_status"] = "degraded"
                health_status["issues"].append(f"Cluster health: {cluster_health.overall_health}")
        
        # Check cache performance
        cache_monitor = self.cache_system.get("cache_monitor")
        if cache_monitor:
            cache_health = await cache_monitor.get_cache_health()
            health_status["components"]["cache"] = cache_health
            
            if cache_health["status"] != "healthy":
                health_status["overall_status"] = "degraded"
                health_status["issues"].extend(cache_health.get("issues", []))
        
        return health_status


# Utility functions for common cache operations
async def warm_up_cache(cache_manager: CacheManager, warm_up_data: Dict[str, Any]) -> None:
    """Warm up cache with initial data."""
    logger.info("Starting cache warm-up", keys_count=len(warm_up_data))
    
    for key, value in warm_up_data.items():
        try:
            await cache_manager.set(key, value, ttl=3600)
        except Exception as e:
            logger.error("Failed to warm up cache key", key=key, error=str(e))
    
    logger.info("Cache warm-up completed")


async def clear_cache_namespace(cache_manager: CacheManager, namespace: str) -> int:
    """Clear all cache entries in a specific namespace."""
    logger.warning("Clearing cache namespace", namespace=namespace)
    
    try:
        cleared_count = await cache_manager.clear_namespace()
        logger.info("Cache namespace cleared", namespace=namespace, cleared=cleared_count)
        return cleared_count
    except Exception as e:
        logger.error("Failed to clear cache namespace", namespace=namespace, error=str(e))
        return 0