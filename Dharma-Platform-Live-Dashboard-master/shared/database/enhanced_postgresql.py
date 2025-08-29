"""Enhanced PostgreSQL manager with performance optimization."""

import time
import asyncio
from typing import Optional, Dict, Any, List, Union, Tuple, Callable
from datetime import datetime
import asyncpg
from asyncpg import Pool
import structlog

from .postgresql import PostgreSQLManager
from .performance import PostgreSQLOptimizer, DatabasePerformanceOptimizer

logger = structlog.get_logger(__name__)


class EnhancedPostgreSQLManager(PostgreSQLManager):
    """Enhanced PostgreSQL manager with performance monitoring and optimization."""
    
    def __init__(self, connection_string: str):
        super().__init__(connection_string)
        self.optimizer = None
        self.performance_tracker = DatabasePerformanceOptimizer()
        self._prepared_statements = {}
        self._query_cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL with optimized settings."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=10,
                max_size=50,
                command_timeout=60,
                server_settings={
                    'jit': 'off',  # Disable JIT for better performance on small queries
                    'shared_preload_libraries': 'pg_stat_statements',
                    'track_activity_query_size': '2048',
                    'log_min_duration_statement': '1000',  # Log slow queries
                    'log_checkpoints': 'on',
                    'log_connections': 'on',
                    'log_disconnections': 'on',
                    'log_lock_waits': 'on',
                    'deadlock_timeout': '1s',
                    'max_connections': '200',
                    'shared_buffers': '256MB',
                    'effective_cache_size': '1GB',
                    'work_mem': '4MB',
                    'maintenance_work_mem': '64MB'
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            self._connected = True
            
            # Initialize optimizer
            self.optimizer = PostgreSQLOptimizer(self)
            
            logger.info("Connected to PostgreSQL with performance optimizations")
            
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise
    
    async def create_optimized_indexes(self) -> None:
        """Create optimized indexes using the optimizer."""
        if self.optimizer:
            await self.optimizer.create_optimized_indexes()
    
    async def _execute_with_monitoring(
        self, 
        operation_name: str,
        query: str,
        *args,
        fetch_method: str = "execute"
    ) -> Any:
        """Execute database operation with performance monitoring."""
        start_time = time.time()
        
        try:
            if not self.pool:
                raise RuntimeError("Database not connected")
            
            async with self.pool.acquire() as conn:
                if fetch_method == "execute":
                    result = await conn.execute(query, *args)
                elif fetch_method == "fetch":
                    result = await conn.fetch(query, *args)
                    result = [dict(row) for row in result]
                elif fetch_method == "fetchrow":
                    row = await conn.fetchrow(query, *args)
                    result = dict(row) if row else None
                elif fetch_method == "fetchval":
                    result = await conn.fetchval(query, *args)
                else:
                    raise ValueError(f"Unknown fetch method: {fetch_method}")
            
            execution_time = time.time() - start_time
            
            # Track performance
            self.performance_tracker.track_query_performance(
                f"{operation_name}:{query[:100]}", 
                execution_time
            )
            
            logger.debug("Database operation completed", 
                        operation=operation_name,
                        execution_time=execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Database operation failed", 
                        operation=operation_name,
                        execution_time=execution_time,
                        error=str(e))
            raise
    
    async def execute_optimized(self, query: str, *args) -> str:
        """Execute query with performance monitoring."""
        return await self._execute_with_monitoring("execute", query, *args, fetch_method="execute")
    
    async def fetch_optimized(self, query: str, *args, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetch multiple rows with caching and performance monitoring."""
        
        # Generate cache key
        cache_key = f"fetch:{hash(query)}:{hash(str(args))}"
        
        # Check cache first
        if use_cache and cache_key in self._query_cache:
            cache_entry = self._query_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                logger.debug("Cache hit for query", cache_key=cache_key[:50])
                return cache_entry['data']
        
        result = await self._execute_with_monitoring("fetch", query, *args, fetch_method="fetch")
        
        # Cache the result
        if use_cache and result:
            self._query_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
        
        return result
    
    async def fetchrow_optimized(self, query: str, *args, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Fetch single row with caching and performance monitoring."""
        
        cache_key = f"fetchrow:{hash(query)}:{hash(str(args))}"
        
        if use_cache and cache_key in self._query_cache:
            cache_entry = self._query_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['data']
        
        result = await self._execute_with_monitoring("fetchrow", query, *args, fetch_method="fetchrow")
        
        if use_cache:
            self._query_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
        
        return result
    
    async def prepare_statement(self, name: str, query: str) -> None:
        """Prepare a statement for repeated execution."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            await conn.execute(f"PREPARE {name} AS {query}")
        
        self._prepared_statements[name] = query
        logger.debug("Prepared statement", name=name)
    
    async def execute_prepared(self, name: str, *args) -> Any:
        """Execute a prepared statement."""
        if name not in self._prepared_statements:
            raise ValueError(f"Prepared statement '{name}' not found")
        
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        start_time = time.time()
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(f"EXECUTE {name}", *args)
            
            execution_time = time.time() - start_time
            self.performance_tracker.track_query_performance(
                f"prepared_{name}", 
                execution_time
            )
            
            return result
            
        except Exception as e:
            logger.error("Prepared statement execution failed", name=name, error=str(e))
            raise
    
    async def bulk_insert_optimized(
        self,
        table_name: str,
        columns: List[str],
        data: List[Tuple],
        batch_size: int = 1000
    ) -> int:
        """Optimized bulk insert using COPY."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        start_time = time.time()
        total_inserted = 0
        
        try:
            async with self.pool.acquire() as conn:
                # Process in batches
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    
                    # Use COPY for maximum performance
                    result = await conn.copy_records_to_table(
                        table_name,
                        records=batch,
                        columns=columns
                    )
                    
                    total_inserted += len(batch)
                    
                    logger.debug("Bulk insert batch completed", 
                               batch_size=len(batch),
                               total_inserted=total_inserted)
            
            execution_time = time.time() - start_time
            self.performance_tracker.track_query_performance(
                f"bulk_insert_{table_name}", 
                execution_time
            )
            
            return total_inserted
            
        except Exception as e:
            logger.error("Bulk insert failed", table=table_name, error=str(e))
            raise
    
    async def get_alerts_optimized(
        self, 
        status: Optional[str] = None,
        severity: Optional[str] = None,
        assigned_to: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Optimized alert retrieval with proper indexing."""
        
        # Build dynamic query with proper parameter binding
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
        
        if assigned_to:
            param_count += 1
            conditions.append(f"assigned_to = ${param_count}")
            params.append(assigned_to)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        param_count += 1
        limit_param = f"${param_count}"
        params.append(limit)
        
        param_count += 1
        offset_param = f"${param_count}"
        params.append(offset)
        
        # Use index-friendly query
        query = f"""
            SELECT id, type, severity, title, description, status, 
                   created_at, acknowledged_at, resolved_at, assigned_to
            FROM alerts
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """
        
        return await self.fetch_optimized(query, *params, use_cache=use_cache)
    
    async def get_user_activity_optimized(
        self, 
        user_id: Optional[int] = None,
        days: int = 30,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Optimized user activity retrieval."""
        
        if user_id:
            query = """
                SELECT action, resource_type, resource_id, timestamp, details
                FROM audit_logs 
                WHERE user_id = $1 
                  AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                ORDER BY timestamp DESC 
                LIMIT 1000
            """
            params = [user_id, days]
        else:
            query = """
                SELECT u.username, u.role, COUNT(al.id) as action_count,
                       MAX(al.timestamp) as last_activity
                FROM users u
                LEFT JOIN audit_logs al ON u.id = al.user_id 
                    AND al.timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY u.id, u.username, u.role
                ORDER BY action_count DESC
                LIMIT 100
            """
            params = [days]
        
        return await self.fetch_optimized(query, *params, use_cache=use_cache)
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        metrics = {
            "query_performance": self.performance_tracker.generate_performance_report(),
            "cache_stats": {
                "cache_size": len(self._query_cache),
                "cache_ttl": self._cache_ttl,
                "prepared_statements": len(self._prepared_statements)
            }
        }
        
        # Get PostgreSQL-specific stats
        try:
            # Connection pool stats
            if self.pool:
                metrics["pool_stats"] = {
                    "size": self.pool.get_size(),
                    "max_size": self.pool.get_max_size(),
                    "min_size": self.pool.get_min_size()
                }
            
            # Database stats
            db_stats_query = """
                SELECT 
                    numbackends as active_connections,
                    xact_commit as transactions_committed,
                    xact_rollback as transactions_rolled_back,
                    blks_read as blocks_read,
                    blks_hit as blocks_hit,
                    tup_returned as tuples_returned,
                    tup_fetched as tuples_fetched,
                    tup_inserted as tuples_inserted,
                    tup_updated as tuples_updated,
                    tup_deleted as tuples_deleted
                FROM pg_stat_database 
                WHERE datname = current_database()
            """
            
            db_stats = await self.fetchrow_optimized(db_stats_query, use_cache=False)
            if db_stats:
                metrics["database_stats"] = db_stats
            
            # Get slow queries if pg_stat_statements is available
            if self.optimizer:
                slow_queries = await self.optimizer.get_slow_queries(limit=5)
                metrics["slow_queries"] = slow_queries
                
        except Exception as e:
            logger.warning("Could not retrieve database stats", error=str(e))
        
        return metrics
    
    async def optimize_table(self, table_name: str) -> Dict[str, Any]:
        """Optimize specific table performance."""
        if not self.optimizer:
            return {"error": "Optimizer not initialized"}
        
        # Update table statistics
        await self.optimizer.update_table_statistics(table_name)
        
        # Get table stats
        stats = await self.optimizer.get_table_stats(table_name)
        
        # Analyze common queries (simplified)
        common_queries = [
            f"SELECT * FROM {table_name} WHERE id = $1",
            f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT 100"
        ]
        
        # Get recommendations
        recommendations = await self.optimizer.suggest_indexes(table_name, common_queries)
        
        return {
            "table_stats": stats,
            "index_recommendations": [
                {
                    "fields": rec.index_fields,
                    "type": rec.index_type,
                    "reason": rec.reason,
                    "benefit": rec.estimated_benefit
                }
                for rec in recommendations
            ]
        }
    
    def clear_query_cache(self):
        """Clear the query cache."""
        self._query_cache.clear()
        logger.info("Query cache cleared")
    
    async def explain_query(self, query: str, *args) -> Dict[str, Any]:
        """Explain query execution plan."""
        if not self.optimizer:
            return {"error": "Optimizer not initialized"}
        
        return await self.optimizer.analyze_query_performance(query, list(args))
    
    async def vacuum_analyze(self, table_name: Optional[str] = None):
        """Run VACUUM ANALYZE for maintenance."""
        if table_name:
            await self.execute_optimized(f"VACUUM ANALYZE {table_name}")
            logger.info("VACUUM ANALYZE completed for table", table=table_name)
        else:
            await self.execute_optimized("VACUUM ANALYZE")
            logger.info("VACUUM ANALYZE completed for all tables")
    
    async def get_table_sizes(self) -> List[Dict[str, Any]]:
        """Get table sizes for monitoring."""
        query = """
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """
        
        return await self.fetch_optimized(query, use_cache=True)