"""Unified database manager for coordinating all database connections."""

from typing import Optional, Dict, Any
import asyncio
import structlog

from .mongodb import MongoDBManager
from .postgresql import PostgreSQLManager
from .redis import RedisManager
from .elasticsearch import ElasticsearchManager
from ..config.settings import Settings

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Unified database manager that coordinates all database connections."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Initialize database managers
        self.mongodb: Optional[MongoDBManager] = None
        self.postgresql: Optional[PostgreSQLManager] = None
        self.redis: Optional[RedisManager] = None
        self.elasticsearch: Optional[ElasticsearchManager] = None
        
        self._connected = False
    
    async def connect_all(self) -> None:
        """Connect to all configured databases."""
        connection_tasks = []
        
        # MongoDB connection
        if self.settings.database.mongodb_url:
            self.mongodb = MongoDBManager(
                self.settings.database.mongodb_url,
                self.settings.database.mongodb_database
            )
            connection_tasks.append(self._connect_mongodb())
        
        # PostgreSQL connection
        if self.settings.database.postgresql_url:
            self.postgresql = PostgreSQLManager(
                self.settings.database.postgresql_url
            )
            connection_tasks.append(self._connect_postgresql())
        
        # Redis connection
        if self.settings.redis.url:
            self.redis = RedisManager(
                self.settings.redis.url,
                self.settings.redis.max_connections
            )
            connection_tasks.append(self._connect_redis())
        
        # Elasticsearch connection
        if self.settings.database.elasticsearch_url:
            self.elasticsearch = ElasticsearchManager(
                self.settings.database.elasticsearch_url,
                self.settings.database.elasticsearch_index_prefix
            )
            connection_tasks.append(self._connect_elasticsearch())
        
        # Connect to all databases concurrently
        if connection_tasks:
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Check for connection failures
            failed_connections = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_connections.append(str(result))
            
            if failed_connections:
                logger.error("Some database connections failed", failures=failed_connections)
                # Don't raise exception - allow partial connectivity
            
            self._connected = True
            logger.info("Database manager initialized", 
                       mongodb=self.mongodb is not None,
                       postgresql=self.postgresql is not None,
                       redis=self.redis is not None,
                       elasticsearch=self.elasticsearch is not None)
    
    async def _connect_mongodb(self) -> None:
        """Connect to MongoDB."""
        if self.mongodb:
            await self.mongodb.connect()
            await self.mongodb.create_indexes()
    
    async def _connect_postgresql(self) -> None:
        """Connect to PostgreSQL."""
        if self.postgresql:
            await self.postgresql.connect()
    
    async def _connect_redis(self) -> None:
        """Connect to Redis."""
        if self.redis:
            await self.redis.connect()
    
    async def _connect_elasticsearch(self) -> None:
        """Connect to Elasticsearch."""
        if self.elasticsearch:
            await self.elasticsearch.connect()
            await self.elasticsearch.create_default_indexes()
    
    async def disconnect_all(self) -> None:
        """Disconnect from all databases."""
        disconnection_tasks = []
        
        if self.mongodb:
            disconnection_tasks.append(self.mongodb.disconnect())
        
        if self.postgresql:
            disconnection_tasks.append(self.postgresql.disconnect())
        
        if self.redis:
            disconnection_tasks.append(self.redis.disconnect())
        
        if self.elasticsearch:
            disconnection_tasks.append(self.elasticsearch.disconnect())
        
        if disconnection_tasks:
            await asyncio.gather(*disconnection_tasks, return_exceptions=True)
        
        self._connected = False
        logger.info("Disconnected from all databases")
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all database connections."""
        health_status = {}
        
        if self.mongodb:
            health_status["mongodb"] = await self.mongodb.health_check()
        
        if self.postgresql:
            health_status["postgresql"] = await self.postgresql.health_check()
        
        if self.redis:
            health_status["redis"] = await self.redis.health_check()
        
        if self.elasticsearch:
            health_status["elasticsearch"] = await self.elasticsearch.health_check()
        
        return health_status
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """Get information about database connections."""
        info = {
            "connected": self._connected,
            "databases": {}
        }
        
        if self.mongodb:
            info["databases"]["mongodb"] = {
                "connected": self.mongodb._connected,
                "database": self.mongodb.database_name
            }
        
        if self.postgresql:
            info["databases"]["postgresql"] = {
                "connected": self.postgresql._connected,
                "pool_size": self.postgresql.pool.get_size() if self.postgresql.pool else 0
            }
        
        if self.redis:
            info["databases"]["redis"] = {
                "connected": self.redis._connected,
                "max_connections": self.redis.max_connections
            }
        
        if self.elasticsearch:
            info["databases"]["elasticsearch"] = {
                "connected": self.elasticsearch._connected,
                "index_prefix": self.elasticsearch.index_prefix
            }
        
        return info
    
    def get_mongodb(self) -> MongoDBManager:
        """Get MongoDB manager instance."""
        if not self.mongodb:
            raise RuntimeError("MongoDB not configured")
        return self.mongodb
    
    def get_postgresql(self) -> PostgreSQLManager:
        """Get PostgreSQL manager instance."""
        if not self.postgresql:
            raise RuntimeError("PostgreSQL not configured")
        return self.postgresql
    
    def get_redis(self) -> RedisManager:
        """Get Redis manager instance."""
        if not self.redis:
            raise RuntimeError("Redis not configured")
        return self.redis
    
    def get_elasticsearch(self) -> ElasticsearchManager:
        """Get Elasticsearch manager instance."""
        if not self.elasticsearch:
            raise RuntimeError("Elasticsearch not configured")
        return self.elasticsearch


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_database_manager(settings: Optional[Settings] = None) -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        if settings is None:
            settings = Settings()
        
        _db_manager = DatabaseManager(settings)
        await _db_manager.connect_all()
    
    return _db_manager


async def close_database_manager() -> None:
    """Close the global database manager instance."""
    global _db_manager
    
    if _db_manager:
        await _db_manager.disconnect_all()
        _db_manager = None