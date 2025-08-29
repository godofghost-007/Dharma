"""Connection pool management for async operations."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Callable, AsyncContextManager
from dataclasses import dataclass
from contextlib import asynccontextmanager
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PoolConfig:
    """Connection pool configuration."""
    min_size: int = 5
    max_size: int = 20
    max_idle_time: float = 300.0  # 5 minutes
    connection_timeout: float = 30.0
    health_check_interval: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class ConnectionStats:
    """Connection statistics."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    pool_utilization: float = 0.0


class PooledConnection:
    """Wrapper for pooled connections."""
    
    def __init__(self, connection: Any, pool: 'ConnectionPoolManager'):
        self.connection = connection
        self.pool = pool
        self.created_at = time.time()
        self.last_used = time.time()
        self.is_healthy = True
        self.use_count = 0
    
    async def health_check(self) -> bool:
        """Check if connection is healthy."""
        try:
            if hasattr(self.connection, 'ping'):
                await self.connection.ping()
            elif hasattr(self.connection, 'execute'):
                await self.connection.execute('SELECT 1')
            
            self.is_healthy = True
            return True
            
        except Exception as e:
            logger.warning("Connection health check failed", error=str(e))
            self.is_healthy = False
            return False
    
    def is_expired(self, max_idle_time: float) -> bool:
        """Check if connection has been idle too long."""
        return (time.time() - self.last_used) > max_idle_time
    
    def mark_used(self):
        """Mark connection as recently used."""
        self.last_used = time.time()
        self.use_count += 1


class ConnectionPoolManager:
    """Generic async connection pool manager."""
    
    def __init__(
        self, 
        connection_factory: Callable,
        config: Optional[PoolConfig] = None
    ):
        self.connection_factory = connection_factory
        self.config = config or PoolConfig()
        
        self._pool: List[PooledConnection] = []
        self._pool_lock = asyncio.Lock()
        self._stats = ConnectionStats()
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize the connection pool."""
        async with self._pool_lock:
            # Create minimum number of connections
            for _ in range(self.config.min_size):
                try:
                    conn = await self._create_connection()
                    if conn:
                        self._pool.append(conn)
                except Exception as e:
                    logger.error("Failed to create initial connection", error=str(e))
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Connection pool initialized", 
                   initial_size=len(self._pool),
                   min_size=self.config.min_size,
                   max_size=self.config.max_size)
    
    async def _create_connection(self) -> Optional[PooledConnection]:
        """Create a new connection."""
        try:
            connection = await asyncio.wait_for(
                self.connection_factory(),
                timeout=self.config.connection_timeout
            )
            
            pooled_conn = PooledConnection(connection, self)
            self._stats.total_connections += 1
            
            logger.debug("New connection created")
            return pooled_conn
            
        except Exception as e:
            self._stats.failed_connections += 1
            logger.error("Failed to create connection", error=str(e))
            return None
    
    @asynccontextmanager
    async def acquire(self) -> AsyncContextManager[Any]:
        """Acquire a connection from the pool."""
        start_time = time.time()
        connection = None
        
        try:
            connection = await self._get_connection()
            self._stats.total_requests += 1
            
            yield connection.connection
            
            # Mark as successful
            self._stats.successful_requests += 1
            
        except Exception as e:
            self._stats.failed_requests += 1
            logger.error("Connection operation failed", error=str(e))
            
            # Mark connection as unhealthy if it exists
            if connection:
                connection.is_healthy = False
            
            raise
        
        finally:
            # Update response time stats
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            
            # Return connection to pool
            if connection:
                await self._return_connection(connection)
    
    async def _get_connection(self) -> PooledConnection:
        """Get a connection from the pool."""
        async with self._pool_lock:
            # Try to find a healthy idle connection
            for conn in self._pool:
                if conn.is_healthy and not conn.is_expired(self.config.max_idle_time):
                    conn.mark_used()
                    self._stats.active_connections += 1
                    return conn
            
            # No suitable connection found, create new one if possible
            if len(self._pool) < self.config.max_size:
                new_conn = await self._create_connection()
                if new_conn:
                    self._pool.append(new_conn)
                    new_conn.mark_used()
                    self._stats.active_connections += 1
                    return new_conn
            
            # Pool is full, wait for a connection to become available
            # This is a simplified implementation - in production, you'd want
            # a proper queue with timeout
            await asyncio.sleep(0.1)
            return await self._get_connection()
    
    async def _return_connection(self, connection: PooledConnection):
        """Return a connection to the pool."""
        async with self._pool_lock:
            self._stats.active_connections = max(0, self._stats.active_connections - 1)
            
            # Remove unhealthy connections
            if not connection.is_healthy:
                try:
                    self._pool.remove(connection)
                    await self._close_connection(connection)
                except ValueError:
                    pass  # Connection already removed
    
    async def _close_connection(self, connection: PooledConnection):
        """Close a connection."""
        try:
            if hasattr(connection.connection, 'close'):
                await connection.connection.close()
            elif hasattr(connection.connection, 'disconnect'):
                await connection.connection.disconnect()
            
            logger.debug("Connection closed")
            
        except Exception as e:
            logger.warning("Error closing connection", error=str(e))
    
    async def _health_check_loop(self):
        """Periodic health check for connections."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check loop error", error=str(e))
    
    async def _perform_health_checks(self):
        """Perform health checks on all connections."""
        async with self._pool_lock:
            connections_to_remove = []
            
            for conn in self._pool:
                # Check if connection is expired
                if conn.is_expired(self.config.max_idle_time):
                    connections_to_remove.append(conn)
                    continue
                
                # Perform health check
                if not await conn.health_check():
                    connections_to_remove.append(conn)
            
            # Remove unhealthy/expired connections
            for conn in connections_to_remove:
                try:
                    self._pool.remove(conn)
                    await self._close_connection(conn)
                except ValueError:
                    pass
            
            if connections_to_remove:
                logger.debug("Removed unhealthy connections", 
                           count=len(connections_to_remove))
            
            # Ensure minimum pool size
            while len(self._pool) < self.config.min_size:
                new_conn = await self._create_connection()
                if new_conn:
                    self._pool.append(new_conn)
                else:
                    break  # Failed to create connection
    
    def _update_response_time(self, response_time: float):
        """Update average response time using exponential moving average."""
        alpha = 0.1  # Smoothing factor
        if self._stats.avg_response_time == 0:
            self._stats.avg_response_time = response_time
        else:
            self._stats.avg_response_time = (
                alpha * response_time + 
                (1 - alpha) * self._stats.avg_response_time
            )
    
    def get_stats(self) -> ConnectionStats:
        """Get current pool statistics."""
        self._stats.idle_connections = len(self._pool) - self._stats.active_connections
        self._stats.pool_utilization = (
            self._stats.active_connections / self.config.max_size
            if self.config.max_size > 0 else 0
        )
        
        return self._stats
    
    async def resize_pool(self, new_min_size: int, new_max_size: int):
        """Resize the connection pool."""
        if new_min_size > new_max_size:
            raise ValueError("min_size cannot be greater than max_size")
        
        async with self._pool_lock:
            old_min = self.config.min_size
            old_max = self.config.max_size
            
            self.config.min_size = new_min_size
            self.config.max_size = new_max_size
            
            # If reducing max size, close excess connections
            if new_max_size < len(self._pool):
                connections_to_close = self._pool[new_max_size:]
                self._pool = self._pool[:new_max_size]
                
                for conn in connections_to_close:
                    await self._close_connection(conn)
            
            # If increasing min size, create new connections
            elif new_min_size > len(self._pool):
                needed = new_min_size - len(self._pool)
                for _ in range(needed):
                    new_conn = await self._create_connection()
                    if new_conn:
                        self._pool.append(new_conn)
                    else:
                        break
        
        logger.info("Pool resized", 
                   old_min=old_min, 
                   old_max=old_max,
                   new_min=new_min_size, 
                   new_max=new_max_size,
                   current_size=len(self._pool))
    
    async def drain_pool(self):
        """Drain all connections from the pool."""
        async with self._pool_lock:
            connections_to_close = self._pool.copy()
            self._pool.clear()
            
            for conn in connections_to_close:
                await self._close_connection(conn)
        
        logger.info("Pool drained", closed_connections=len(connections_to_close))
    
    async def shutdown(self):
        """Shutdown the connection pool."""
        # Stop health check task
        if self._health_check_task:
            self._shutdown_event.set()
            self._health_check_task.cancel()
            
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        await self.drain_pool()
        
        logger.info("Connection pool shutdown completed")


class DatabaseConnectionPool(ConnectionPoolManager):
    """Specialized connection pool for database connections."""
    
    def __init__(self, database_manager, config: Optional[PoolConfig] = None):
        self.database_manager = database_manager
        
        async def connection_factory():
            # This would create a new database connection
            # Implementation depends on the specific database manager
            return await database_manager.create_connection()
        
        super().__init__(connection_factory, config)
    
    async def execute_query(self, query: str, *args, **kwargs):
        """Execute a query using a pooled connection."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args, **kwargs)
    
    async def fetch_results(self, query: str, *args, **kwargs):
        """Fetch query results using a pooled connection."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, **kwargs)