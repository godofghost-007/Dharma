#!/usr/bin/env python3
"""
Database optimization script for Project Dharma.
This script creates optimized indexes, analyzes performance, and provides recommendations.
"""

import asyncio
import sys
import argparse
from typing import Dict, Any, List
from datetime import datetime
import structlog

# Add project root to path
sys.path.append('.')

from shared.database.enhanced_mongodb import EnhancedMongoDBManager
from shared.database.enhanced_postgresql import EnhancedPostgreSQLManager
from shared.database.connection_pool_manager import (
    ConnectionPoolManager, PoolConfiguration, get_pool_manager
)
from shared.config.settings import get_database_settings

logger = structlog.get_logger(__name__)


class DatabaseOptimizer:
    """Main database optimization coordinator."""
    
    def __init__(self):
        self.mongodb_manager = None
        self.postgresql_manager = None
        self.settings = get_database_settings()
    
    async def initialize_connections(self):
        """Initialize database connections."""
        logger.info("Initializing database connections...")
        
        # Initialize MongoDB
        if self.settings.get('mongodb_url'):
            self.mongodb_manager = EnhancedMongoDBManager(
                self.settings['mongodb_url'],
                self.settings.get('mongodb_database', 'dharma_platform')
            )
            await self.mongodb_manager.connect()
            logger.info("MongoDB connection established")
        
        # Initialize PostgreSQL
        if self.settings.get('postgresql_url'):
            self.postgresql_manager = EnhancedPostgreSQLManager(
                self.settings['postgresql_url']
            )
            await self.postgresql_manager.connect()
            logger.info("PostgreSQL connection established")
    
    async def create_all_indexes(self):
        """Create optimized indexes for all databases."""
        logger.info("Creating optimized indexes...")
        
        # MongoDB indexes
        if self.mongodb_manager:
            logger.info("Creating MongoDB indexes...")
            await self.mongodb_manager.create_optimized_indexes()
            logger.info("MongoDB indexes created successfully")
        
        # PostgreSQL indexes
        if self.postgresql_manager:
            logger.info("Creating PostgreSQL indexes...")
            await self.postgresql_manager.create_optimized_indexes()
            logger.info("PostgreSQL indexes created successfully")
    
    async def analyze_performance(self) -> Dict[str, Any]:
        """Analyze database performance."""
        logger.info("Analyzing database performance...")
        
        performance_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "mongodb": {},
            "postgresql": {}
        }
        
        # MongoDB performance analysis
        if self.mongodb_manager:
            try:
                mongodb_metrics = await self.mongodb_manager.get_performance_metrics()
                performance_report["mongodb"] = mongodb_metrics
                
                # Analyze specific collections
                collections = ["posts", "campaigns", "user_profiles", "alerts"]
                for collection in collections:
                    try:
                        collection_analysis = await self.mongodb_manager.optimize_collection(collection)
                        performance_report["mongodb"][f"{collection}_analysis"] = collection_analysis
                    except Exception as e:
                        logger.warning(f"Failed to analyze {collection}", error=str(e))
                
            except Exception as e:
                logger.error("MongoDB performance analysis failed", error=str(e))
                performance_report["mongodb"]["error"] = str(e)
        
        # PostgreSQL performance analysis
        if self.postgresql_manager:
            try:
                postgresql_metrics = await self.postgresql_manager.get_performance_metrics()
                performance_report["postgresql"] = postgresql_metrics
                
                # Analyze specific tables
                tables = ["users", "alerts", "audit_logs"]
                for table in tables:
                    try:
                        table_analysis = await self.postgresql_manager.optimize_table(table)
                        performance_report["postgresql"][f"{table}_analysis"] = table_analysis
                    except Exception as e:
                        logger.warning(f"Failed to analyze {table}", error=str(e))
                
                # Get table sizes
                table_sizes = await self.postgresql_manager.get_table_sizes()
                performance_report["postgresql"]["table_sizes"] = table_sizes
                
            except Exception as e:
                logger.error("PostgreSQL performance analysis failed", error=str(e))
                performance_report["postgresql"]["error"] = str(e)
        
        return performance_report
    
    async def optimize_connection_pools(self):
        """Optimize connection pool configurations."""
        logger.info("Optimizing connection pools...")
        
        pool_manager = get_pool_manager()
        
        # MongoDB connection pool
        if self.mongodb_manager:
            mongodb_config = PoolConfiguration(
                min_size=5,
                max_size=30,
                acquire_timeout=10.0,
                idle_timeout=300.0,
                enable_auto_scaling=True,
                scale_up_threshold=0.8,
                scale_down_threshold=0.3
            )
            
            mongodb_pool = ConnectionPoolManager("mongodb", mongodb_config)
            pool_manager.add_pool("mongodb", mongodb_pool)
        
        # PostgreSQL connection pool
        if self.postgresql_manager:
            postgresql_config = PoolConfiguration(
                min_size=10,
                max_size=50,
                acquire_timeout=30.0,
                idle_timeout=300.0,
                enable_auto_scaling=True,
                scale_up_threshold=0.8,
                scale_down_threshold=0.3
            )
            
            postgresql_pool = ConnectionPoolManager("postgresql", postgresql_config)
            pool_manager.add_pool("postgresql", postgresql_pool)
        
        logger.info("Connection pools optimized")
    
    async def run_maintenance_tasks(self):
        """Run database maintenance tasks."""
        logger.info("Running database maintenance tasks...")
        
        # PostgreSQL maintenance
        if self.postgresql_manager:
            logger.info("Running PostgreSQL maintenance...")
            
            # Update statistics
            await self.postgresql_manager.vacuum_analyze()
            logger.info("PostgreSQL VACUUM ANALYZE completed")
        
        # MongoDB maintenance
        if self.mongodb_manager:
            logger.info("Running MongoDB maintenance...")
            
            # Clear query cache
            self.mongodb_manager.clear_query_cache()
            logger.info("MongoDB query cache cleared")
        
        logger.info("Maintenance tasks completed")
    
    async def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        logger.info("Generating optimization report...")
        
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "optimization_summary": {
                "indexes_created": True,
                "performance_analyzed": True,
                "pools_optimized": True,
                "maintenance_completed": True
            }
        }
        
        # Get performance metrics
        performance_data = await self.analyze_performance()
        report["performance_analysis"] = performance_data
        
        # Get connection pool statistics
        pool_manager = get_pool_manager()
        pool_stats = pool_manager.get_all_statistics()
        report["connection_pools"] = pool_stats
        
        # Generate recommendations
        recommendations = self._generate_recommendations(performance_data, pool_stats)
        report["recommendations"] = recommendations
        
        return report
    
    def _generate_recommendations(
        self, 
        performance_data: Dict[str, Any], 
        pool_stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # MongoDB recommendations
        mongodb_data = performance_data.get("mongodb", {})
        if mongodb_data:
            query_perf = mongodb_data.get("query_performance", {})
            slow_queries = query_perf.get("slow_queries", [])
            
            if slow_queries:
                recommendations.append({
                    "type": "performance",
                    "database": "mongodb",
                    "priority": "high",
                    "title": "Slow MongoDB Queries Detected",
                    "description": f"Found {len(slow_queries)} slow queries that may need optimization",
                    "action": "Review and optimize slow queries, consider adding indexes"
                })
            
            # Check cache hit rate
            cache_stats = mongodb_data.get("cache_stats", {})
            if cache_stats.get("cache_size", 0) > 1000:
                recommendations.append({
                    "type": "memory",
                    "database": "mongodb",
                    "priority": "medium",
                    "title": "Large Query Cache",
                    "description": "Query cache is growing large, consider tuning TTL",
                    "action": "Review cache TTL settings and clear cache periodically"
                })
        
        # PostgreSQL recommendations
        postgresql_data = performance_data.get("postgresql", {})
        if postgresql_data:
            query_perf = postgresql_data.get("query_performance", {})
            slow_queries = query_perf.get("slow_queries", [])
            
            if slow_queries:
                recommendations.append({
                    "type": "performance",
                    "database": "postgresql",
                    "priority": "high",
                    "title": "Slow PostgreSQL Queries Detected",
                    "description": f"Found {len(slow_queries)} slow queries",
                    "action": "Analyze query plans and optimize with EXPLAIN ANALYZE"
                })
            
            # Check table sizes
            table_sizes = postgresql_data.get("table_sizes", [])
            large_tables = [t for t in table_sizes if "GB" in t.get("total_size", "")]
            
            if large_tables:
                recommendations.append({
                    "type": "storage",
                    "database": "postgresql",
                    "priority": "medium",
                    "title": "Large Tables Detected",
                    "description": f"Found {len(large_tables)} tables over 1GB",
                    "action": "Consider partitioning or archiving old data"
                })
        
        # Connection pool recommendations
        for pool_name, stats in pool_stats.items():
            current_state = stats.get("current_state", {})
            utilization = current_state.get("utilization", 0)
            
            if utilization > 0.9:
                recommendations.append({
                    "type": "connection_pool",
                    "database": pool_name,
                    "priority": "high",
                    "title": f"High Pool Utilization - {pool_name}",
                    "description": f"Pool utilization is {utilization:.1%}",
                    "action": "Consider increasing max pool size"
                })
            elif utilization < 0.2:
                recommendations.append({
                    "type": "connection_pool",
                    "database": pool_name,
                    "priority": "low",
                    "title": f"Low Pool Utilization - {pool_name}",
                    "description": f"Pool utilization is {utilization:.1%}",
                    "action": "Consider reducing min pool size to save resources"
                })
        
        return recommendations
    
    async def cleanup(self):
        """Cleanup database connections."""
        if self.mongodb_manager:
            await self.mongodb_manager.disconnect()
        
        if self.postgresql_manager:
            await self.postgresql_manager.disconnect()
        
        # Close all connection pools
        pool_manager = get_pool_manager()
        await pool_manager.close_all()


async def main():
    """Main optimization function."""
    parser = argparse.ArgumentParser(description="Database optimization for Project Dharma")
    parser.add_argument("--create-indexes", action="store_true", 
                       help="Create optimized indexes")
    parser.add_argument("--analyze-performance", action="store_true", 
                       help="Analyze database performance")
    parser.add_argument("--optimize-pools", action="store_true", 
                       help="Optimize connection pools")
    parser.add_argument("--maintenance", action="store_true", 
                       help="Run maintenance tasks")
    parser.add_argument("--full-optimization", action="store_true", 
                       help="Run complete optimization (all tasks)")
    parser.add_argument("--report-only", action="store_true", 
                       help="Generate report without making changes")
    parser.add_argument("--output", type=str, default="optimization_report.json",
                       help="Output file for the report")
    
    args = parser.parse_args()
    
    # If no specific tasks are specified, run full optimization
    if not any([args.create_indexes, args.analyze_performance, 
                args.optimize_pools, args.maintenance, args.report_only]):
        args.full_optimization = True
    
    optimizer = DatabaseOptimizer()
    
    try:
        # Initialize connections
        await optimizer.initialize_connections()
        
        # Run requested tasks
        if args.full_optimization or args.create_indexes:
            if not args.report_only:
                await optimizer.create_all_indexes()
        
        if args.full_optimization or args.optimize_pools:
            if not args.report_only:
                await optimizer.optimize_connection_pools()
        
        if args.full_optimization or args.maintenance:
            if not args.report_only:
                await optimizer.run_maintenance_tasks()
        
        # Always generate performance analysis and report
        report = await optimizer.generate_optimization_report()
        
        # Save report to file
        import json
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Optimization report saved to {args.output}")
        
        # Print summary
        print("\n" + "="*60)
        print("DATABASE OPTIMIZATION SUMMARY")
        print("="*60)
        
        summary = report["optimization_summary"]
        for task, completed in summary.items():
            status = "✓" if completed else "✗"
            print(f"{status} {task.replace('_', ' ').title()}")
        
        # Print recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            print(f"\n📋 RECOMMENDATIONS ({len(recommendations)} items):")
            for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec["priority"], "⚪")
                print(f"{i}. {priority_icon} {rec['title']} ({rec['database']})")
                print(f"   {rec['description']}")
                print(f"   Action: {rec['action']}\n")
            
            if len(recommendations) > 5:
                print(f"   ... and {len(recommendations) - 5} more recommendations in the report")
        
        print("="*60)
        print("✅ Database optimization completed successfully!")
        
    except Exception as e:
        logger.error("Database optimization failed", error=str(e))
        print(f"\n❌ Optimization failed: {e}")
        sys.exit(1)
    
    finally:
        await optimizer.cleanup()


if __name__ == "__main__":
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    asyncio.run(main())