"""Enhanced MongoDB manager with performance optimization."""

import time
import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import structlog

from .mongodb import MongoDBManager
from .performance import MongoDBOptimizer, DatabasePerformanceOptimizer

logger = structlog.get_logger(__name__)


class EnhancedMongoDBManager(MongoDBManager):
    """Enhanced MongoDB manager with performance monitoring and optimization."""
    
    def __init__(self, connection_string: str, database_name: str):
        super().__init__(connection_string, database_name)
        self.optimizer = None
        self.performance_tracker = DatabasePerformanceOptimizer()
        self._query_cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def connect(self) -> None:
        """Establish connection to MongoDB with optimized settings."""
        try:
            self.client = AsyncIOMotorClient(
                self.connection_string,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                waitQueueTimeoutMS=5000,
                serverSelectionTimeoutMS=5000,
                # Performance optimizations
                readPreference='secondaryPreferred',
                readConcern={'level': 'majority'},
                writeConcern={'w': 'majority', 'j': True},
                retryWrites=True,
                retryReads=True,
                compressors=['zstd', 'zlib', 'snappy']
            )
            
            # Test connection
            await self.client.admin.command('ping')
            self.database = self.client[self.database_name]
            self._connected = True
            
            # Initialize optimizer
            self.optimizer = MongoDBOptimizer(self)
            
            logger.info("Connected to MongoDB with performance optimizations", 
                       database=self.database_name)
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise
    
    async def create_optimized_indexes(self) -> None:
        """Create optimized indexes using the optimizer."""
        if self.optimizer:
            await self.optimizer.create_optimized_indexes()
        else:
            await super().create_indexes()
    
    async def _execute_with_monitoring(
        self, 
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute database operation with performance monitoring."""
        start_time = time.time()
        
        try:
            result = await operation_func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Track performance
            self.performance_tracker.track_query_performance(
                f"{operation_name}:{str(args)[:100]}", 
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
    
    async def find_posts_optimized(
        self, 
        filter_query: Dict[str, Any], 
        limit: int = 100,
        skip: int = 0,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Optimized post finding with caching and performance monitoring."""
        
        # Generate cache key
        cache_key = f"posts:{hash(str(filter_query))}:{limit}:{skip}"
        
        # Check cache first
        if use_cache and cache_key in self._query_cache:
            cache_entry = self._query_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                logger.debug("Cache hit for posts query", cache_key=cache_key)
                return cache_entry['data']
        
        async def find_operation():
            if not self.database:
                raise RuntimeError("Database not connected")
            
            # Use optimized query with proper indexing
            cursor = self.database.posts.find(
                filter_query,
                {
                    # Project only needed fields to reduce network transfer
                    'content': 1,
                    'user_id': 1,
                    'platform': 1,
                    'timestamp': 1,
                    'analysis_results': 1,
                    'metrics': 1
                }
            ).skip(skip).limit(limit)
            
            # Add sorting for consistent results and index usage
            if 'timestamp' not in filter_query:
                cursor = cursor.sort('timestamp', -1)
            
            return await cursor.to_list(length=limit)
        
        result = await self._execute_with_monitoring(
            "find_posts_optimized",
            find_operation
        )
        
        # Cache the result
        if use_cache:
            self._query_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
        
        return result
    
    async def aggregate_with_optimization(
        self,
        collection_name: str,
        pipeline: List[Dict[str, Any]],
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline with optimization."""
        
        cache_key = f"agg:{collection_name}:{hash(str(pipeline))}"
        
        # Check cache
        if use_cache and cache_key in self._query_cache:
            cache_entry = self._query_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['data']
        
        async def aggregate_operation():
            if not self.database:
                raise RuntimeError("Database not connected")
            
            collection = self.database[collection_name]
            
            # Add optimization hints to pipeline
            optimized_pipeline = self._optimize_aggregation_pipeline(pipeline)
            
            cursor = collection.aggregate(optimized_pipeline, allowDiskUse=True)
            return await cursor.to_list(length=None)
        
        result = await self._execute_with_monitoring(
            f"aggregate_{collection_name}",
            aggregate_operation
        )
        
        # Cache result
        if use_cache:
            self._query_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
        
        return result
    
    def _optimize_aggregation_pipeline(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize aggregation pipeline for better performance."""
        optimized = []
        
        for stage in pipeline:
            # Move $match stages as early as possible
            if '$match' in stage:
                optimized.insert(0, stage)
            # Add $limit after $sort to reduce memory usage
            elif '$sort' in stage:
                optimized.append(stage)
                # Add limit if not already present
                if not any('$limit' in s for s in pipeline):
                    optimized.append({'$limit': 10000})  # Reasonable default
            else:
                optimized.append(stage)
        
        return optimized
    
    async def bulk_insert_optimized(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> List[str]:
        """Optimized bulk insert with batching."""
        
        async def bulk_insert_operation():
            if not self.database:
                raise RuntimeError("Database not connected")
            
            collection = self.database[collection_name]
            inserted_ids = []
            
            # Process in batches to avoid memory issues
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Use ordered=False for better performance
                result = await collection.insert_many(batch, ordered=False)
                inserted_ids.extend([str(id) for id in result.inserted_ids])
                
                logger.debug("Bulk insert batch completed", 
                           batch_size=len(batch),
                           total_inserted=len(inserted_ids))
            
            return inserted_ids
        
        return await self._execute_with_monitoring(
            f"bulk_insert_{collection_name}",
            bulk_insert_operation
        )
    
    async def update_many_optimized(
        self,
        collection_name: str,
        filter_query: Dict[str, Any],
        update_doc: Dict[str, Any],
        upsert: bool = False
    ) -> int:
        """Optimized bulk update operation."""
        
        async def update_operation():
            if not self.database:
                raise RuntimeError("Database not connected")
            
            collection = self.database[collection_name]
            
            result = await collection.update_many(
                filter_query,
                update_doc,
                upsert=upsert
            )
            
            return result.modified_count
        
        return await self._execute_with_monitoring(
            f"update_many_{collection_name}",
            update_operation
        )
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        metrics = {
            "query_performance": self.performance_tracker.generate_performance_report(),
            "cache_stats": {
                "cache_size": len(self._query_cache),
                "cache_ttl": self._cache_ttl
            }
        }
        
        # Get MongoDB server stats if available
        try:
            if self.database:
                server_stats = await self.database.command("serverStatus")
                metrics["server_stats"] = {
                    "connections": server_stats.get("connections", {}),
                    "opcounters": server_stats.get("opcounters", {}),
                    "memory": server_stats.get("mem", {}),
                    "network": server_stats.get("network", {})
                }
        except Exception as e:
            logger.warning("Could not retrieve server stats", error=str(e))
        
        return metrics
    
    async def optimize_collection(self, collection_name: str) -> Dict[str, Any]:
        """Optimize specific collection performance."""
        if not self.optimizer:
            return {"error": "Optimizer not initialized"}
        
        # Get collection stats
        stats = await self.optimizer.get_collection_stats(collection_name)
        
        # Analyze common query patterns (simplified)
        query_patterns = [
            {"filter": {"platform": 1}, "sort": {"timestamp": -1}},
            {"filter": {"user_id": 1}, "sort": {"timestamp": -1}},
            {"filter": {"analysis_results.sentiment": 1}, "sort": {"timestamp": -1}}
        ]
        
        # Get index recommendations
        recommendations = await self.optimizer.suggest_indexes(collection_name, query_patterns)
        
        return {
            "collection_stats": stats,
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
    
    async def explain_query(
        self,
        collection_name: str,
        query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Explain query execution plan."""
        if not self.optimizer:
            return {"error": "Optimizer not initialized"}
        
        return await self.optimizer.analyze_query_performance(collection_name, query)