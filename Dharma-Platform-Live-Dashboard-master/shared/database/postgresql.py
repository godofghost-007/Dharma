"""PostgreSQL connection manager and utilities."""

import asyncio
from typing import Optional, Dict, Any, List, Union, Tuple

try:
    import asyncpg
    from asyncpg import Pool
    ASYNCPG_AVAILABLE = True
except ImportError:
    asyncpg = None
    Pool = None
    ASYNCPG_AVAILABLE = False

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class PostgreSQLManager:
    """PostgreSQL connection manager with connection pooling."""
    
    def __init__(self, connection_string: str):
        if not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg is required for PostgreSQL support. Install with: pip install asyncpg")
        
        self.connection_string = connection_string
        self.pool: Optional[Pool] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'jit': 'off'  # Disable JIT for better performance on small queries
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            self._connected = True
            logger.info("Connected to PostgreSQL")
            
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("Disconnected from PostgreSQL")
    
    async def health_check(self) -> bool:
        """Check PostgreSQL connection health."""
        try:
            if not self._connected or not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
            return True
            
        except Exception as e:
            logger.error("PostgreSQL health check failed", error=str(e))
            return False
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch multiple rows as dictionaries."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single row as dictionary."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch single value."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def transaction(self):
        """Get a transaction context manager."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        return self.pool.acquire()
    
    # User management methods
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[int]:
        """Create a new user and return user ID."""
        query = """
            INSERT INTO users (username, email, role, password_hash)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """
        try:
            user_id = await self.fetchval(
                query,
                user_data["username"],
                user_data["email"],
                user_data["role"],
                user_data.get("password_hash", "")
            )
            return user_id
        except Exception as e:
            logger.error("Failed to create user", error=str(e))
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE id = $1"
        return await self.fetchrow(query, user_id)
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        query = "SELECT * FROM users WHERE username = $1"
        return await self.fetchrow(query, username)
    
    async def update_user_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp."""
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1"
        try:
            await self.execute(query, user_id)
            return True
        except Exception as e:
            logger.error("Failed to update user last login", user_id=user_id, error=str(e))
            return False
    
    # Alert management methods
    async def create_alert(self, alert_data: Dict[str, Any]) -> Optional[int]:
        """Create a new alert and return alert ID."""
        query = """
            INSERT INTO alerts (type, severity, title, description, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        try:
            alert_id = await self.fetchval(
                query,
                alert_data["type"],
                alert_data["severity"],
                alert_data["title"],
                alert_data["description"],
                alert_data.get("metadata", {})
            )
            return alert_id
        except Exception as e:
            logger.error("Failed to create alert", error=str(e))
            return None
    
    async def get_alerts(
        self, 
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering."""
        conditions = []
        params = []
        param_count = 0
        
        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)
        
        if severity:
            param_count += 1
            conditions.append(f"severity = ${param_count}")
            params.append(severity)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        param_count += 1
        limit_param = f"${param_count}"
        params.append(limit)
        
        param_count += 1
        offset_param = f"${param_count}"
        params.append(offset)
        
        query = f"""
            SELECT * FROM alerts
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """
        
        return await self.fetch(query, *params)
    
    async def acknowledge_alert(self, alert_id: int, user_id: int) -> bool:
        """Acknowledge an alert."""
        query = """
            UPDATE alerts 
            SET status = 'acknowledged', 
                acknowledged_at = CURRENT_TIMESTAMP,
                assigned_to = $2
            WHERE id = $1
        """
        try:
            await self.execute(query, alert_id, user_id)
            return True
        except Exception as e:
            logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
            return False
    
    async def resolve_alert(self, alert_id: int, user_id: int) -> bool:
        """Resolve an alert."""
        query = """
            UPDATE alerts 
            SET status = 'resolved', 
                resolved_at = CURRENT_TIMESTAMP,
                assigned_to = $2
            WHERE id = $1
        """
        try:
            await self.execute(query, alert_id, user_id)
            return True
        except Exception as e:
            logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
            return False
    
    # Audit logging methods
    async def log_user_action(
        self, 
        user_id: int, 
        action: str, 
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log user action for audit trail."""
        query = """
            INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
            VALUES ($1, $2, $3, $4, $5)
        """
        try:
            await self.execute(query, user_id, action, resource_type, resource_id, details or {})
            return True
        except Exception as e:
            logger.error("Failed to log user action", error=str(e))
            return False
    
    async def get_user_audit_logs(
        self, 
        user_id: int, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get audit logs for a specific user."""
        query = """
            SELECT * FROM audit_logs 
            WHERE user_id = $1 
            ORDER BY timestamp DESC 
            LIMIT $2 OFFSET $3
        """
        return await self.fetch(query, user_id, limit, offset)
    
    # Analytics and reporting methods
    async def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert statistics for the last N days."""
        query = """
            SELECT 
                severity,
                status,
                COUNT(*) as count
            FROM alerts 
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY severity, status
            ORDER BY severity, status
        """
        
        rows = await self.fetch(query, days)
        
        # Organize results into a more usable format
        stats = {
            "total": 0,
            "by_severity": {},
            "by_status": {}
        }
        
        for row in rows:
            stats["total"] += row["count"]
            
            if row["severity"] not in stats["by_severity"]:
                stats["by_severity"][row["severity"]] = 0
            stats["by_severity"][row["severity"]] += row["count"]
            
            if row["status"] not in stats["by_status"]:
                stats["by_status"][row["status"]] = 0
            stats["by_status"][row["status"]] += row["count"]
        
        return stats
    
    async def get_user_activity_summary(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get user activity summary for the last N days."""
        query = """
            SELECT 
                u.username,
                u.role,
                COUNT(al.id) as action_count,
                MAX(al.timestamp) as last_activity
            FROM users u
            LEFT JOIN audit_logs al ON u.id = al.user_id 
                AND al.timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY u.id, u.username, u.role
            ORDER BY action_count DESC
        """
        
        return await self.fetch(query, days)