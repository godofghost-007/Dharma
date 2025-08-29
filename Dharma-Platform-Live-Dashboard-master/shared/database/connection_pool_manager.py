"""Advanced connection pool management and optimization."""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class PoolStatus(Enum):
    """Connection pool status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class ConnectionStats:
    """Connection statistics."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    waiting_connections: int = 0
    failed_connections: int = 0
    peak_connections: int = 0
    avg_connection_time: float = 0.0
    avg_query_time: float = 0.0
    total_queries: int = 0
    failed_queries: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PoolConfiguration:
    """Connection pool configuration."""
    min_size: int = 5
    max_size: int = 20
    acquire_timeout: float = 30.0
    idle_timeout: float = 300.0
    max_lifetime: float = 3600.0
    health_check_interval: float = 60.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_monitoring: bool = True
    enable_auto_scaling: bool = True
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3


class ConnectionPoolManager:
    """Advanced connection pool manager with monitoring and auto-scaling."""
    
    def __init__(self, pool_name: str, config: PoolConfiguration):
        self.pool_name = pool_name
        self.config = config
        self.stats = ConnectionStats()
        self.status = PoolStatus.OFFLINE
        self._pool = None
        self._monitoring_task = None
        self._health_check_task = None
        self._last_scale_action = datetime.utcnow()
        self._scale_cooldown = timedelta(minutes=5)
        
    async def initialize_pool(self, pool_factory: Callable) -> None:
        """Initialize the connection pool."""
        try:
            self._pool = await pool_factory(
                min_size=self.config.min_size,
                max_size=self.config.max_size,
                command_timeout=self.config.acquire_timeout
            )
            
            self.status = PoolStatus.HEALTHY
            self.stats.total_connections = self.config.min_size
            self.stats.idle_connections = self.config.min_size
            
            # Start monitoring tasks
            if self.config.enable_monitoring:
                self._monitoring_task = asyncio.create_task(self._monitor_pool())
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("Connection pool initialized", 
                       pool_name=self.pool_name,
                       min_size=self.config.min_size,
                       max_size=self.config.max_size)
            
        except Exception as e:
            self.status = PoolStatus.OFFLINE
            logger.error("Failed to initialize connection pool", 
                        pool_name=self.pool_name, error=str(e))
            raise
    
    async def acquire_connection(self, timeout: Optional[float] = None):
        """Acquire a connection from the pool with monitoring."""
        if not self._pool:
            raise RuntimeError("Pool not initialized")
        
        timeout = timeout or self.config.acquire_timeout
        start_time = time.time()
        
        try:
            # Update waiting connections count
            self.stats.waiting_connections += 1
            
            connection = await asyncio.wait_for(
                self._pool.acquire(),
                timeout=timeout
            )
            
            # Update statistics
            connection_time = time.time() - start_time
            self.stats.active_connections += 1
            self.stats.idle_connections = max(0, self.stats.idle_connections - 1)
            self.stats.waiting_connections = max(0, self.stats.waiting_connections - 1)
            self.stats.avg_connection_time = (
                (self.stats.avg_connection_time * self.stats.total_queries + connection_time) /
                (self.stats.total_queries + 1)
            )
            
            logger.debug("Connection acquired", 
                        pool_name=self.pool_name,
                        connection_time=connection_time,
                        active_connections=self.stats.active_connections)
            
            return ConnectionWrapper(connection, self)
            
        except asyncio.TimeoutError:
            self.stats.failed_connections += 1
            self.stats.waiting_connections = max(0, self.stats.waiting_connections - 1)
            logger.error("Connection acquisition timeout", 
                        pool_name=self.pool_name, timeout=timeout)
            raise
        except Exception as e:
            self.stats.failed_connections += 1
            self.stats.waiting_connections = max(0, self.stats.waiting_connections - 1)
            logger.error("Connection acquisition failed", 
                        pool_name=self.pool_name, error=str(e))
            raise
    
    def release_connection(self, connection):
        """Release a connection back to the pool."""
        if self._pool:
            self._pool.release(connection)
            self.stats.active_connections = max(0, self.stats.active_connections - 1)
            self.stats.idle_connections += 1
            
            logger.debug("Connection released", 
                        pool_name=self.pool_name,
                        active_connections=self.stats.active_connections)
    
    def record_query(self, execution_time: float, success: bool = True):
        """Record query execution statistics."""
        self.stats.total_queries += 1
        
        if success:
            self.stats.avg_query_time = (
                (self.stats.avg_query_time * (self.stats.total_queries - 1) + execution_time) /
                self.stats.total_queries
            )
        else:
            self.stats.failed_queries += 1
    
    async def _monitor_pool(self):
        """Monitor pool performance and trigger auto-scaling."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if not self._pool:
                    continue
                
                # Update current pool statistics
                current_size = self._pool.get_size()
                max_size = self._pool.get_max_size()
                
                self.stats.total_connections = current_size
                self.stats.peak_connections = max(self.stats.peak_connections, current_size)
                
                # Calculate utilization
                utilization = self.stats.active_connections / current_size if current_size > 0 else 0
                
                # Auto-scaling logic
                if self.config.enable_auto_scaling:
                    await self._auto_scale(utilization, current_size, max_size)
                
                # Update pool status
                self._update_pool_status(utilization)
                
                logger.debug("Pool monitoring update", 
                           pool_name=self.pool_name,
                           utilization=utilization,
                           active=self.stats.active_connections,
                           total=current_size,
                           status=self.status.value)
                
            except Exception as e:
                logger.error("Pool monitoring error", 
                           pool_name=self.pool_name, error=str(e))
    
    async def _auto_scale(self, utilization: float, current_size: int, max_size: int):
        """Auto-scale the connection pool based on utilization."""
        now = datetime.utcnow()
        
        # Check cooldown period
        if now - self._last_scale_action < self._scale_cooldown:
            return
        
        # Scale up if utilization is high
        if (utilization > self.config.scale_up_threshold and 
            current_size < max_size and
            self.stats.waiting_connections > 0):
            
            new_size = min(current_size + 2, max_size)
            await self._resize_pool(new_size)
            self._last_scale_action = now
            
            logger.info("Pool scaled up", 
                       pool_name=self.pool_name,
                       old_size=current_size,
                       new_size=new_size,
                       utilization=utilization)
        
        # Scale down if utilization is low
        elif (utilization < self.config.scale_down_threshold and 
              current_size > self.config.min_size and
              self.stats.waiting_connections == 0):
            
            new_size = max(current_size - 1, self.config.min_size)
            await self._resize_pool(new_size)
            self._last_scale_action = now
            
            logger.info("Pool scaled down", 
                       pool_name=self.pool_name,
                       old_size=current_size,
                       new_size=new_size,
                       utilization=utilization)
    
    async def _resize_pool(self, new_size: int):
        """Resize the connection pool."""
        if self._pool and hasattr(self._pool, 'resize'):
            try:
                await self._pool.resize(new_size)
            except Exception as e:
                logger.error("Pool resize failed", 
                           pool_name=self.pool_name, 
                           new_size=new_size, 
                           error=str(e))
    
    def _update_pool_status(self, utilization: float):
        """Update pool status based on current metrics."""
        if self.stats.failed_connections > self.stats.total_queries * 0.1:
            self.status = PoolStatus.CRITICAL
        elif utilization > 0.9 or self.stats.waiting_connections > 5:
            self.status = PoolStatus.WARNING
        elif self.stats.failed_queries > self.stats.total_queries * 0.05:
            self.status = PoolStatus.WARNING
        else:
            self.status = PoolStatus.HEALTHY
    
    async def _health_check_loop(self):
        """Perform periodic health checks on the pool."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval * 2)
                await self._perform_health_check()
                
            except Exception as e:
                logger.error("Health check error", 
                           pool_name=self.pool_name, error=str(e))
    
    async def _perform_health_check(self):
        """Perform health check on the connection pool."""
        if not self._pool:
            self.status = PoolStatus.OFFLINE
            return
        
        try:
            # Try to acquire and immediately release a connection
            async with self._pool.acquire() as conn:
                # Perform a simple query to test connection health
                if hasattr(conn, 'execute'):
                    await conn.execute('SELECT 1')
                elif hasattr(conn, 'ping'):
                    await conn.ping()
            
            # Health check passed
            if self.status == PoolStatus.OFFLINE:
                self.status = PoolStatus.HEALTHY
                logger.info("Pool health check passed - status restored", 
                           pool_name=self.pool_name)
                
        except Exception as e:
            self.status = PoolStatus.CRITICAL
            logger.error("Pool health check failed", 
                        pool_name=self.pool_name, error=str(e))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics."""
        current_size = self._pool.get_size() if self._pool else 0
        utilization = (self.stats.active_connections / current_size 
                      if current_size > 0 else 0)
        
        return {
            "pool_name": self.pool_name,
            "status": self.status.value,
            "configuration": {
                "min_size": self.config.min_size,
                "max_size": self.config.max_size,
                "acquire_timeout": self.config.acquire_timeout,
                "idle_timeout": self.config.idle_timeout,
                "auto_scaling_enabled": self.config.enable_auto_scaling
            },
            "current_state": {
                "total_connections": current_size,
                "active_connections": self.stats.active_connections,
                "idle_connections": self.stats.idle_connections,
                "waiting_connections": self.stats.waiting_connections,
                "utilization": utilization
            },
            "performance_metrics": {
                "total_queries": self.stats.total_queries,
                "failed_queries": self.stats.failed_queries,
                "query_success_rate": (
                    (self.stats.total_queries - self.stats.failed_queries) / 
                    self.stats.total_queries if self.stats.total_queries > 0 else 0
                ),
                "avg_connection_time": self.stats.avg_connection_time,
                "avg_query_time": self.stats.avg_query_time,
                "peak_connections": self.stats.peak_connections,
                "failed_connections": self.stats.failed_connections
            },
            "last_reset": self.stats.last_reset.isoformat()
        }
    
    def reset_statistics(self):
        """Reset pool statistics."""
        self.stats = ConnectionStats()
        self.stats.last_reset = datetime.utcnow()
        logger.info("Pool statistics reset", pool_name=self.pool_name)
    
    async def close(self):
        """Close the connection pool and cleanup resources."""
        # Cancel monitoring tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close the pool
        if self._pool:
            await self._pool.close()
            self.status = PoolStatus.OFFLINE
            
        logger.info("Connection pool closed", pool_name=self.pool_name)


class ConnectionWrapper:
    """Wrapper for database connections with automatic monitoring."""
    
    def __init__(self, connection, pool_manager: ConnectionPoolManager):
        self.connection = connection
        self.pool_manager = pool_manager
        self._acquired_at = time.time()
    
    async def __aenter__(self):
        return self.connection
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.pool_manager.release_connection(self.connection)
    
    async def execute(self, query: str, *args, **kwargs):
        """Execute query with performance monitoring."""
        start_time = time.time()
        
        try:
            result = await self.connection.execute(query, *args, **kwargs)
            execution_time = time.time() - start_time
            self.pool_manager.record_query(execution_time, success=True)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.pool_manager.record_query(execution_time, success=False)
            raise
    
    async def fetch(self, query: str, *args, **kwargs):
        """Fetch query with performance monitoring."""
        start_time = time.time()
        
        try:
            result = await self.connection.fetch(query, *args, **kwargs)
            execution_time = time.time() - start_time
            self.pool_manager.record_query(execution_time, success=True)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.pool_manager.record_query(execution_time, success=False)
            raise
    
    async def fetchrow(self, query: str, *args, **kwargs):
        """Fetch single row with performance monitoring."""
        start_time = time.time()
        
        try:
            result = await self.connection.fetchrow(query, *args, **kwargs)
            execution_time = time.time() - start_time
            self.pool_manager.record_query(execution_time, success=True)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.pool_manager.record_query(execution_time, success=False)
            raise


class MultiPoolManager:
    """Manager for multiple connection pools."""
    
    def __init__(self):
        self.pools: Dict[str, ConnectionPoolManager] = {}
    
    def add_pool(self, name: str, pool_manager: ConnectionPoolManager):
        """Add a connection pool to the manager."""
        self.pools[name] = pool_manager
        logger.info("Pool added to manager", pool_name=name)
    
    def get_pool(self, name: str) -> Optional[ConnectionPoolManager]:
        """Get a connection pool by name."""
        return self.pools.get(name)
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics for all pools."""
        return {
            name: pool.get_statistics()
            for name, pool in self.pools.items()
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all pools."""
        healthy_pools = sum(1 for pool in self.pools.values() 
                           if pool.status == PoolStatus.HEALTHY)
        warning_pools = sum(1 for pool in self.pools.values() 
                           if pool.status == PoolStatus.WARNING)
        critical_pools = sum(1 for pool in self.pools.values() 
                            if pool.status == PoolStatus.CRITICAL)
        offline_pools = sum(1 for pool in self.pools.values() 
                           if pool.status == PoolStatus.OFFLINE)
        
        overall_status = PoolStatus.HEALTHY
        if critical_pools > 0 or offline_pools > 0:
            overall_status = PoolStatus.CRITICAL
        elif warning_pools > 0:
            overall_status = PoolStatus.WARNING
        
        return {
            "overall_status": overall_status.value,
            "total_pools": len(self.pools),
            "healthy_pools": healthy_pools,
            "warning_pools": warning_pools,
            "critical_pools": critical_pools,
            "offline_pools": offline_pools,
            "pool_details": {
                name: {
                    "status": pool.status.value,
                    "active_connections": pool.stats.active_connections,
                    "total_connections": pool._pool.get_size() if pool._pool else 0
                }
                for name, pool in self.pools.items()
            }
        }
    
    async def close_all(self):
        """Close all connection pools."""
        for name, pool in self.pools.items():
            try:
                await pool.close()
                logger.info("Pool closed", pool_name=name)
            except Exception as e:
                logger.error("Failed to close pool", pool_name=name, error=str(e))
        
        self.pools.clear()
        logger.info("All pools closed")


# Global pool manager instance
pool_manager = MultiPoolManager()


def get_pool_manager() -> MultiPoolManager:
    """Get the global pool manager instance."""
    return pool_manager