"""Database connection and operations."""

import asyncpg
import redis.asyncio as redis
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import structlog

from .config import settings

logger = structlog.get_logger()


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize database connections."""
        try:
            # Initialize PostgreSQL connection pool
            self.pg_pool = await asyncpg.create_pool(
                settings.db_postgresql_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("PostgreSQL connection pool initialized")
            
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                settings.db_redis_url,
                decode_responses=True,
                max_connections=20
            )
            await self.redis_client.ping()
            logger.info("Redis connection initialized")
            
        except Exception as e:
            logger.error("Failed to initialize database connections", error=str(e))
            raise
    
    async def close(self):
        """Close database connections."""
        if self.pg_pool:
            await self.pg_pool.close()
            logger.info("PostgreSQL connection pool closed")
        
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    @asynccontextmanager
    async def get_pg_connection(self):
        """Get PostgreSQL connection from pool."""
        if not self.pg_pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        async with self.pg_pool.acquire() as connection:
            yield connection
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis client."""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        return self.redis_client


class UserRepository:
    """Repository for user-related database operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        async with self.db.get_pg_connection() as conn:
            query = """
                SELECT id, username, email, hashed_password, role, is_active, 
                       full_name, department, permissions, last_login, created_at
                FROM users 
                WHERE username = $1 AND is_active = true
            """
            row = await conn.fetchrow(query, username)
            return dict(row) if row else None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        async with self.db.get_pg_connection() as conn:
            query = """
                SELECT id, username, email, role, is_active, full_name, 
                       department, permissions, last_login, created_at
                FROM users 
                WHERE id = $1 AND is_active = true
            """
            row = await conn.fetchrow(query, user_id)
            return dict(row) if row else None
    
    async def create_user(self, user_data: Dict[str, Any]) -> int:
        """Create new user."""
        async with self.db.get_pg_connection() as conn:
            query = """
                INSERT INTO users (username, email, hashed_password, role, full_name, 
                                 department, permissions, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            user_id = await conn.fetchval(
                query,
                user_data["username"],
                user_data["email"],
                user_data["hashed_password"],
                user_data["role"],
                user_data.get("full_name"),
                user_data.get("department"),
                user_data.get("permissions", []),
                user_data.get("is_active", True)
            )
            return user_id
    
    async def update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        async with self.db.get_pg_connection() as conn:
            query = """
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP, login_count = login_count + 1
                WHERE id = $1
            """
            await conn.execute(query, user_id)
    
    async def get_user_permissions(self, user_id: int) -> List[str]:
        """Get user permissions including role-based permissions."""
        async with self.db.get_pg_connection() as conn:
            query = """
                SELECT role, permissions 
                FROM users 
                WHERE id = $1 AND is_active = true
            """
            row = await conn.fetchrow(query, user_id)
            if not row:
                return []
            
            # Base permissions by role
            role_permissions = {
                "admin": [
                    "users:read", "users:write", "users:delete",
                    "alerts:read", "alerts:write", "alerts:delete",
                    "campaigns:read", "campaigns:write", "campaigns:delete",
                    "analytics:read", "analytics:write",
                    "system:admin"
                ],
                "supervisor": [
                    "users:read", "users:write",
                    "alerts:read", "alerts:write",
                    "campaigns:read", "campaigns:write",
                    "analytics:read", "analytics:write"
                ],
                "analyst": [
                    "alerts:read", "alerts:write",
                    "campaigns:read", "campaigns:write",
                    "analytics:read"
                ],
                "viewer": [
                    "alerts:read",
                    "campaigns:read",
                    "analytics:read"
                ]
            }
            
            base_permissions = role_permissions.get(row["role"], [])
            additional_permissions = row["permissions"] or []
            
            return list(set(base_permissions + additional_permissions))


# Global database manager instance
db_manager = DatabaseManager()