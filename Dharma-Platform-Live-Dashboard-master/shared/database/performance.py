"""Database performance optimization utilities."""

import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class QueryPerformanceMetrics:
    """Query performance metrics."""
    query_hash: str
    query_text: str
    execution_count: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    last_executed: Optional[datetime] = None
    slow_query_threshold: float = 1.0  # seconds


@dataclass
class IndexRecommendation:
    """Database index recommendation."""
    collection_or_table: str
    index_fields: List[str]
    index_type: str  # "btree", "text", "2dsphere", etc.
    reason: str
    estimated_benefit: str
    query_pattern: str


class DatabasePerformanceOptimizer:
    """Database performance optimization and monitoring."""
    
    def __init__(self):
        self.query_metrics: Dict[str, QueryPerformanceMetrics] = {}
        self.slow_query_threshold = 1.0  # seconds
        self.index_recommendations: List[IndexRecommendation] = []
    
    def track_query_performance(self, query_text: str, execution_time: float):
        """Track query performance metrics."""
        import hashlib
        query_hash = hashlib.md5(query_text.encode()).hexdigest()
        
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryPerformanceMetrics(
                query_hash=query_hash,
                query_text=query_text
            )
        
        metrics = self.query_metrics[query_hash]
        metrics.execution_count += 1
        metrics.total_execution_time += execution_time
        metrics.avg_execution_time = metrics.total_execution_time / metrics.execution_count
        metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
        metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
        metrics.last_executed = datetime.utcnow()
        
        # Log slow queries
        if execution_time > self.slow_query_threshold:
            logger.warning("Slow query detected", 
                         query_hash=query_hash,
                         execution_time=execution_time,
                         query_text=query_text[:200])
    
    def get_slow_queries(self, threshold: Optional[float] = None) -> List[QueryPerformanceMetrics]:
        """Get queries that exceed the slow query threshold."""
        threshold = threshold or self.slow_query_threshold
        return [
            metrics for metrics in self.query_metrics.values()
            if metrics.avg_execution_time > threshold
        ]
    
    def get_most_frequent_queries(self, limit: int = 10) -> List[QueryPerformanceMetrics]:
        """Get most frequently executed queries."""
        return sorted(
            self.query_metrics.values(),
            key=lambda x: x.execution_count,
            reverse=True
        )[:limit]
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        total_queries = len(self.query_metrics)
        slow_queries = self.get_slow_queries()
        frequent_queries = self.get_most_frequent_queries()
        
        return {
            "summary": {
                "total_unique_queries": total_queries,
                "slow_queries_count": len(slow_queries),
                "slow_query_threshold": self.slow_query_threshold,
                "total_executions": sum(m.execution_count for m in self.query_metrics.values()),
                "avg_execution_time": sum(m.avg_execution_time for m in self.query_metrics.values()) / total_queries if total_queries > 0 else 0
            },
            "slow_queries": [
                {
                    "query_hash": m.query_hash,
                    "query_text": m.query_text[:200],
                    "avg_execution_time": m.avg_execution_time,
                    "execution_count": m.execution_count,
                    "max_execution_time": m.max_execution_time
                }
                for m in slow_queries[:10]
            ],
            "frequent_queries": [
                {
                    "query_hash": m.query_hash,
                    "query_text": m.query_text[:200],
                    "execution_count": m.execution_count,
                    "avg_execution_time": m.avg_execution_time
                }
                for m in frequent_queries
            ],
            "index_recommendations": [
                {
                    "collection_or_table": rec.collection_or_table,
                    "index_fields": rec.index_fields,
                    "index_type": rec.index_type,
                    "reason": rec.reason,
                    "estimated_benefit": rec.estimated_benefit
                }
                for rec in self.index_recommendations
            ]
        }


class MongoDBOptimizer:
    """MongoDB-specific performance optimization."""
    
    def __init__(self, mongodb_manager):
        self.mongodb = mongodb_manager
        self.performance_optimizer = DatabasePerformanceOptimizer()
    
    async def create_optimized_indexes(self):
        """Create optimized indexes for MongoDB collections."""
        if not self.mongodb.database:
            raise RuntimeError("Database not connected")
        
        logger.info("Creating optimized MongoDB indexes")
        
        # Posts collection - optimized for common query patterns
        posts = self.mongodb.database.posts
        
        # Compound indexes for common filtering patterns
        await posts.create_index([
            ("platform", 1), 
            ("timestamp", -1), 
            ("analysis_results.sentiment", 1)
        ], name="platform_time_sentiment_idx")
        
        await posts.create_index([
            ("user_id", 1), 
            ("platform", 1), 
            ("timestamp", -1)
        ], name="user_platform_time_idx")
        
        await posts.create_index([
            ("analysis_results.risk_score", -1),
            ("timestamp", -1)
        ], name="risk_score_time_idx")
        
        await posts.create_index([
            ("analysis_results.bot_probability", -1),
            ("platform", 1)
        ], name="bot_probability_platform_idx")
        
        # Geospatial index for location-based queries
        await posts.create_index([
            ("geolocation.coordinates", "2dsphere")
        ], name="geolocation_idx")
        
        # Text index for content search
        await posts.create_index([
            ("content", "text"),
            ("analysis_results.keywords", "text")
        ], name="content_search_idx")
        
        # Campaigns collection indexes
        campaigns = self.mongodb.database.campaigns
        
        await campaigns.create_index([
            ("status", 1),
            ("coordination_score", -1),
            ("detection_date", -1)
        ], name="status_score_date_idx")
        
        await campaigns.create_index([
            ("participants", 1)
        ], name="participants_idx")
        
        await campaigns.create_index([
            ("impact_metrics.reach", -1),
            ("status", 1)
        ], name="reach_status_idx")
        
        # User profiles collection indexes
        user_profiles = self.mongodb.database.user_profiles
        
        await user_profiles.create_index([
            ("platform", 1), 
            ("user_id", 1)
        ], unique=True, name="platform_user_unique_idx")
        
        await user_profiles.create_index([
            ("bot_probability", -1),
            ("platform", 1)
        ], name="bot_probability_platform_idx")
        
        await user_profiles.create_index([
            ("behavioral_features.posting_frequency", -1),
            ("platform", 1)
        ], name="posting_frequency_platform_idx")
        
        # Alerts collection indexes (if using MongoDB for alerts)
        alerts = self.mongodb.database.alerts
        
        await alerts.create_index([
            ("severity", 1),
            ("status", 1),
            ("created_at", -1)
        ], name="severity_status_date_idx")
        
        await alerts.create_index([
            ("assigned_to", 1),
            ("status", 1)
        ], name="assigned_status_idx")
        
        logger.info("MongoDB indexes created successfully")
    
    async def analyze_query_performance(self, collection_name: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query performance using MongoDB explain."""
        if not self.mongodb.database:
            raise RuntimeError("Database not connected")
        
        collection = self.mongodb.database[collection_name]
        
        # Get query execution stats
        explain_result = await collection.find(query).explain()
        
        execution_stats = explain_result.get("executionStats", {})
        
        return {
            "total_docs_examined": execution_stats.get("totalDocsExamined", 0),
            "total_docs_returned": execution_stats.get("totalDocsReturned", 0),
            "execution_time_millis": execution_stats.get("executionTimeMillis", 0),
            "index_used": execution_stats.get("indexUsed", False),
            "winning_plan": explain_result.get("queryPlanner", {}).get("winningPlan", {}),
            "rejected_plans": explain_result.get("queryPlanner", {}).get("rejectedPlans", [])
        }
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self.mongodb.database:
            raise RuntimeError("Database not connected")
        
        stats = await self.mongodb.database.command("collStats", collection_name)
        
        return {
            "document_count": stats.get("count", 0),
            "avg_document_size": stats.get("avgObjSize", 0),
            "total_size": stats.get("size", 0),
            "storage_size": stats.get("storageSize", 0),
            "total_index_size": stats.get("totalIndexSize", 0),
            "index_count": len(stats.get("indexSizes", {})),
            "indexes": list(stats.get("indexSizes", {}).keys())
        }
    
    async def suggest_indexes(self, collection_name: str, query_patterns: List[Dict[str, Any]]) -> List[IndexRecommendation]:
        """Suggest indexes based on query patterns."""
        recommendations = []
        
        for pattern in query_patterns:
            # Analyze query pattern and suggest indexes
            filter_fields = list(pattern.get("filter", {}).keys())
            sort_fields = list(pattern.get("sort", {}).keys())
            
            if filter_fields:
                # Suggest compound index for filter + sort
                index_fields = filter_fields + sort_fields
                recommendations.append(IndexRecommendation(
                    collection_or_table=collection_name,
                    index_fields=index_fields,
                    index_type="btree",
                    reason=f"Optimize filtering on {', '.join(filter_fields)} with sorting on {', '.join(sort_fields)}",
                    estimated_benefit="High - reduces document scanning",
                    query_pattern=str(pattern)
                ))
        
        return recommendations


class PostgreSQLOptimizer:
    """PostgreSQL-specific performance optimization."""
    
    def __init__(self, postgresql_manager):
        self.postgresql = postgresql_manager
        self.performance_optimizer = DatabasePerformanceOptimizer()
    
    async def create_optimized_indexes(self):
        """Create optimized indexes for PostgreSQL tables."""
        if not self.postgresql.pool:
            raise RuntimeError("Database not connected")
        
        logger.info("Creating optimized PostgreSQL indexes")
        
        # Users table indexes
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username_lower 
            ON users (LOWER(username))
        """)
        
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_lower 
            ON users (LOWER(email))
        """)
        
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role_active 
            ON users (role) WHERE active = true
        """)
        
        # Alerts table indexes
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_status_severity_date 
            ON alerts (status, severity, created_at DESC)
        """)
        
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_assigned_status 
            ON alerts (assigned_to, status) WHERE assigned_to IS NOT NULL
        """)
        
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_type_date 
            ON alerts (type, created_at DESC)
        """)
        
        # Partial index for unresolved alerts
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_unresolved 
            ON alerts (created_at DESC) WHERE status IN ('new', 'acknowledged')
        """)
        
        # Audit logs table indexes
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_user_timestamp 
            ON audit_logs (user_id, timestamp DESC)
        """)
        
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_action_timestamp 
            ON audit_logs (action, timestamp DESC)
        """)
        
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_resource 
            ON audit_logs (resource_type, resource_id) WHERE resource_type IS NOT NULL
        """)
        
        # GIN index for JSONB columns
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_metadata_gin 
            ON alerts USING GIN (metadata) WHERE metadata IS NOT NULL
        """)
        
        await self.postgresql.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_details_gin 
            ON audit_logs USING GIN (details) WHERE details IS NOT NULL
        """)
        
        logger.info("PostgreSQL indexes created successfully")
    
    async def analyze_query_performance(self, query: str, params: List[Any] = None) -> Dict[str, Any]:
        """Analyze query performance using EXPLAIN ANALYZE."""
        if not self.postgresql.pool:
            raise RuntimeError("Database not connected")
        
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
        
        async with self.postgresql.pool.acquire() as conn:
            result = await conn.fetchval(explain_query, *(params or []))
        
        plan = result[0] if result else {}
        execution_time = plan.get("Execution Time", 0)
        planning_time = plan.get("Planning Time", 0)
        
        return {
            "execution_time_ms": execution_time,
            "planning_time_ms": planning_time,
            "total_time_ms": execution_time + planning_time,
            "plan": plan.get("Plan", {}),
            "triggers": plan.get("Triggers", [])
        }
    
    async def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics."""
        query = """
            SELECT 
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation,
                most_common_vals,
                most_common_freqs
            FROM pg_stats 
            WHERE tablename = $1
        """
        
        stats = await self.postgresql.fetch(query, table_name)
        
        # Get table size information
        size_query = """
            SELECT 
                pg_size_pretty(pg_total_relation_size($1)) as total_size,
                pg_size_pretty(pg_relation_size($1)) as table_size,
                pg_size_pretty(pg_total_relation_size($1) - pg_relation_size($1)) as index_size
        """
        
        size_info = await self.postgresql.fetchrow(size_query, table_name)
        
        return {
            "column_stats": stats,
            "size_info": size_info
        }
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow queries from pg_stat_statements if available."""
        query = """
            SELECT 
                query,
                calls,
                total_time,
                mean_time,
                rows,
                100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
            FROM pg_stat_statements 
            ORDER BY mean_time DESC 
            LIMIT $1
        """
        
        try:
            return await self.postgresql.fetch(query, limit)
        except Exception as e:
            logger.warning("pg_stat_statements not available", error=str(e))
            return []
    
    async def update_table_statistics(self, table_name: Optional[str] = None):
        """Update table statistics for query planner."""
        if table_name:
            await self.postgresql.execute(f"ANALYZE {table_name}")
            logger.info("Updated statistics for table", table=table_name)
        else:
            await self.postgresql.execute("ANALYZE")
            logger.info("Updated statistics for all tables")
    
    async def suggest_indexes(self, table_name: str, query_patterns: List[str]) -> List[IndexRecommendation]:
        """Suggest indexes based on query patterns."""
        recommendations = []
        
        # This is a simplified version - in practice, you'd analyze actual query plans
        for query in query_patterns:
            if "WHERE" in query.upper():
                # Extract WHERE conditions (simplified)
                where_part = query.upper().split("WHERE")[1].split("ORDER BY")[0] if "ORDER BY" in query.upper() else query.upper().split("WHERE")[1]
                
                # Simple pattern matching for common conditions
                if "=" in where_part:
                    # Suggest index on equality conditions
                    recommendations.append(IndexRecommendation(
                        collection_or_table=table_name,
                        index_fields=["extracted_field"],  # Would need proper parsing
                        index_type="btree",
                        reason="Optimize equality filtering",
                        estimated_benefit="Medium - faster lookups",
                        query_pattern=query
                    ))
        
        return recommendations


class ConnectionPoolOptimizer:
    """Connection pool optimization utilities."""
    
    @staticmethod
    def calculate_optimal_pool_size(
        expected_concurrent_users: int,
        avg_query_time_ms: float,
        target_response_time_ms: float = 100
    ) -> Tuple[int, int]:
        """Calculate optimal connection pool size."""
        
        # Calculate connections needed based on Little's Law
        # Connections = (Arrival Rate * Service Time)
        arrival_rate = expected_concurrent_users / 1000  # requests per ms
        service_time = avg_query_time_ms
        
        base_connections = int(arrival_rate * service_time * 2)  # 2x safety factor
        
        # Ensure minimum and maximum bounds
        min_connections = max(5, base_connections // 4)
        max_connections = max(min_connections * 2, base_connections)
        
        # Cap at reasonable limits
        min_connections = min(min_connections, 20)
        max_connections = min(max_connections, 100)
        
        return min_connections, max_connections
    
    @staticmethod
    def get_pool_recommendations(current_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Get connection pool optimization recommendations."""
        recommendations = []
        
        # Analyze pool utilization
        if current_stats.get("pool_utilization", 0) > 0.8:
            recommendations.append("Consider increasing max pool size - high utilization detected")
        
        if current_stats.get("wait_time_avg", 0) > 100:  # ms
            recommendations.append("High wait times detected - increase pool size or optimize queries")
        
        if current_stats.get("idle_connections", 0) > current_stats.get("active_connections", 0) * 2:
            recommendations.append("Many idle connections - consider reducing min pool size")
        
        return {
            "recommendations": recommendations,
            "optimal_min_size": max(5, current_stats.get("active_connections", 10)),
            "optimal_max_size": min(50, current_stats.get("peak_connections", 20) * 2)
        }