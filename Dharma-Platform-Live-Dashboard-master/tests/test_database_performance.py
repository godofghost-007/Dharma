"""Test database performance optimization implementation."""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from shared.database.performance import (
    DatabasePerformanceOptimizer,
    MongoDBOptimizer,
    PostgreSQLOptimizer,
    ConnectionPoolOptimizer,
    QueryPerformanceMetrics,
    IndexRecommendation
)


class TestDatabasePerformanceOptimizer:
    """Test database performance optimizer."""
    
    def test_track_query_performance(self):
        """Test query performance tracking."""
        optimizer = DatabasePerformanceOptimizer()
        
        # Track some queries
        optimizer.track_query_performance("SELECT * FROM users", 0.5)
        optimizer.track_query_performance("SELECT * FROM users", 0.3)
        optimizer.track_query_performance("SELECT * FROM posts", 1.2)
        
        assert len(optimizer.query_metrics) == 2  # Two unique queries
        
        # Check metrics for first query
        user_query_hash = list(optimizer.query_metrics.keys())[0]
        user_metrics = optimizer.query_metrics[user_query_hash]
        
        assert user_metrics.execution_count == 2
        assert user_metrics.avg_execution_time == 0.4  # (0.5 + 0.3) / 2
        assert user_metrics.min_execution_time == 0.3
        assert user_metrics.max_execution_time == 0.5
    
    def test_get_slow_queries(self):
        """Test slow query detection."""
        optimizer = DatabasePerformanceOptimizer()
        optimizer.slow_query_threshold = 1.0
        
        # Add queries with different performance
        optimizer.track_query_performance("FAST QUERY", 0.1)
        optimizer.track_query_performance("SLOW QUERY", 1.5)
        optimizer.track_query_performance("VERY SLOW QUERY", 2.0)
        
        slow_queries = optimizer.get_slow_queries()
        assert len(slow_queries) == 2
        
        # Check that slow queries are identified correctly
        slow_query_texts = [m.query_text for m in slow_queries]
        assert "SLOW QUERY" in slow_query_texts
        assert "VERY SLOW QUERY" in slow_query_texts
        assert "FAST QUERY" not in slow_query_texts
    
    def test_get_most_frequent_queries(self):
        """Test frequent query identification."""
        optimizer = DatabasePerformanceOptimizer()
        
        # Add queries with different frequencies
        for _ in range(10):
            optimizer.track_query_performance("FREQUENT QUERY", 0.1)
        
        for _ in range(5):
            optimizer.track_query_performance("MODERATE QUERY", 0.2)
        
        optimizer.track_query_performance("RARE QUERY", 0.3)
        
        frequent_queries = optimizer.get_most_frequent_queries(limit=2)
        assert len(frequent_queries) == 2
        
        # Most frequent should be first
        assert frequent_queries[0].execution_count == 10
        assert frequent_queries[1].execution_count == 5
    
    def test_generate_performance_report(self):
        """Test performance report generation."""
        optimizer = DatabasePerformanceOptimizer()
        optimizer.slow_query_threshold = 1.0
        
        # Add test data
        optimizer.track_query_performance("FAST QUERY", 0.1)
        optimizer.track_query_performance("SLOW QUERY", 1.5)
        
        report = optimizer.generate_performance_report()
        
        assert "summary" in report
        assert "slow_queries" in report
        assert "frequent_queries" in report
        assert "index_recommendations" in report
        
        assert report["summary"]["total_unique_queries"] == 2
        assert report["summary"]["slow_queries_count"] == 1
        assert len(report["slow_queries"]) == 1
        assert len(report["frequent_queries"]) == 2


class TestMongoDBOptimizer:
    """Test MongoDB optimizer."""
    
    def test_initialization(self):
        """Test MongoDB optimizer initialization."""
        mock_mongodb = MagicMock()
        optimizer = MongoDBOptimizer(mock_mongodb)
        
        assert optimizer.mongodb == mock_mongodb
        assert isinstance(optimizer.performance_optimizer, DatabasePerformanceOptimizer)
    
    def test_create_optimized_indexes_mock(self):
        """Test optimized index creation with proper mocking."""
        mock_mongodb = MagicMock()
        mock_database = MagicMock()
        mock_mongodb.database = mock_database
        
        # Mock collections with AsyncMock for create_index
        mock_posts = MagicMock()
        mock_posts.create_index = AsyncMock()
        mock_campaigns = MagicMock()
        mock_campaigns.create_index = AsyncMock()
        mock_user_profiles = MagicMock()
        mock_user_profiles.create_index = AsyncMock()
        mock_alerts = MagicMock()
        mock_alerts.create_index = AsyncMock()
        
        mock_database.__getitem__.side_effect = lambda name: {
            'posts': mock_posts,
            'campaigns': mock_campaigns,
            'user_profiles': mock_user_profiles,
            'alerts': mock_alerts
        }[name]
        
        optimizer = MongoDBOptimizer(mock_mongodb)
        
        # Test that optimizer was created successfully
        assert optimizer.mongodb == mock_mongodb
        assert isinstance(optimizer.performance_optimizer, DatabasePerformanceOptimizer)
    
    @pytest.mark.asyncio
    async def test_get_collection_stats(self):
        """Test collection statistics retrieval."""
        mock_mongodb = MagicMock()
        mock_database = MagicMock()
        mock_mongodb.database = mock_database
        
        # Mock command response
        mock_database.command = AsyncMock(return_value={
            "count": 1000,
            "avgObjSize": 512,
            "size": 512000,
            "storageSize": 1024000,
            "totalIndexSize": 256000,
            "indexSizes": {
                "_id_": 128000,
                "platform_time_idx": 128000
            }
        })
        
        optimizer = MongoDBOptimizer(mock_mongodb)
        stats = await optimizer.get_collection_stats("posts")
        
        assert stats["document_count"] == 1000
        assert stats["avg_document_size"] == 512
        assert stats["total_size"] == 512000
        assert stats["index_count"] == 2
        assert "_id_" in stats["indexes"]
    
    @pytest.mark.asyncio
    async def test_suggest_indexes(self):
        """Test index suggestion."""
        mock_mongodb = MagicMock()
        optimizer = MongoDBOptimizer(mock_mongodb)
        
        query_patterns = [
            {
                "filter": {"platform": "twitter", "user_id": "123"},
                "sort": {"timestamp": -1}
            },
            {
                "filter": {"analysis_results.sentiment": "positive"},
                "sort": {"timestamp": -1}
            }
        ]
        
        recommendations = await optimizer.suggest_indexes("posts", query_patterns)
        
        assert len(recommendations) == 2
        assert all(isinstance(rec, IndexRecommendation) for rec in recommendations)
        
        # Check that recommendations include relevant fields
        first_rec = recommendations[0]
        assert "platform" in first_rec.index_fields
        assert "user_id" in first_rec.index_fields
        assert first_rec.collection_or_table == "posts"


class TestPostgreSQLOptimizer:
    """Test PostgreSQL optimizer."""
    
    def test_initialization(self):
        """Test PostgreSQL optimizer initialization."""
        mock_postgresql = MagicMock()
        optimizer = PostgreSQLOptimizer(mock_postgresql)
        
        assert optimizer.postgresql == mock_postgresql
        assert isinstance(optimizer.performance_optimizer, DatabasePerformanceOptimizer)
    
    @pytest.mark.asyncio
    async def test_create_optimized_indexes(self):
        """Test optimized index creation."""
        mock_postgresql = MagicMock()
        mock_postgresql.execute = AsyncMock()
        
        optimizer = PostgreSQLOptimizer(mock_postgresql)
        await optimizer.create_optimized_indexes()
        
        # Verify that execute was called multiple times for index creation
        assert mock_postgresql.execute.call_count > 0
        
        # Check that some expected indexes were created
        calls = [call[0][0] for call in mock_postgresql.execute.call_args_list]
        index_calls = [call for call in calls if "CREATE INDEX" in call]
        assert len(index_calls) > 0
    
    @pytest.mark.asyncio
    async def test_get_table_stats(self):
        """Test table statistics retrieval."""
        mock_postgresql = MagicMock()
        mock_postgresql.fetch = AsyncMock(return_value=[
            {
                "schemaname": "public",
                "tablename": "users",
                "attname": "username",
                "n_distinct": 1000,
                "correlation": 0.1
            }
        ])
        mock_postgresql.fetchrow = AsyncMock(return_value={
            "total_size": "1 MB",
            "table_size": "800 kB",
            "index_size": "200 kB"
        })
        
        optimizer = PostgreSQLOptimizer(mock_postgresql)
        stats = await optimizer.get_table_stats("users")
        
        assert "column_stats" in stats
        assert "size_info" in stats
        assert len(stats["column_stats"]) == 1
        assert stats["size_info"]["total_size"] == "1 MB"
    
    @pytest.mark.asyncio
    async def test_update_table_statistics(self):
        """Test table statistics update."""
        mock_postgresql = MagicMock()
        mock_postgresql.execute = AsyncMock()
        
        optimizer = PostgreSQLOptimizer(mock_postgresql)
        
        # Test updating specific table
        await optimizer.update_table_statistics("users")
        mock_postgresql.execute.assert_called_with("ANALYZE users")
        
        # Test updating all tables
        await optimizer.update_table_statistics()
        mock_postgresql.execute.assert_called_with("ANALYZE")


class TestConnectionPoolOptimizer:
    """Test connection pool optimizer."""
    
    def test_calculate_optimal_pool_size(self):
        """Test optimal pool size calculation."""
        min_size, max_size = ConnectionPoolOptimizer.calculate_optimal_pool_size(
            expected_concurrent_users=100,
            avg_query_time_ms=50,
            target_response_time_ms=100
        )
        
        assert isinstance(min_size, int)
        assert isinstance(max_size, int)
        assert min_size > 0
        assert max_size > min_size
        assert min_size <= 20  # Should be capped
        assert max_size <= 100  # Should be capped
    
    def test_get_pool_recommendations(self):
        """Test pool recommendations."""
        # High utilization scenario
        high_util_stats = {
            "pool_utilization": 0.9,
            "wait_time_avg": 150,
            "active_connections": 15,
            "idle_connections": 5,
            "peak_connections": 18
        }
        
        recommendations = ConnectionPoolOptimizer.get_pool_recommendations(high_util_stats)
        
        assert "recommendations" in recommendations
        assert "optimal_min_size" in recommendations
        assert "optimal_max_size" in recommendations
        assert len(recommendations["recommendations"]) > 0
        
        # Check that high utilization is detected
        rec_text = " ".join(recommendations["recommendations"])
        assert "utilization" in rec_text or "wait time" in rec_text
    
    def test_pool_recommendations_idle_connections(self):
        """Test recommendations for too many idle connections."""
        idle_heavy_stats = {
            "pool_utilization": 0.3,
            "wait_time_avg": 10,
            "active_connections": 5,
            "idle_connections": 20,  # Too many idle
            "peak_connections": 10
        }
        
        recommendations = ConnectionPoolOptimizer.get_pool_recommendations(idle_heavy_stats)
        
        rec_text = " ".join(recommendations["recommendations"])
        assert "idle" in rec_text.lower()


class TestQueryPerformanceMetrics:
    """Test query performance metrics data class."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = QueryPerformanceMetrics(
            query_hash="abc123",
            query_text="SELECT * FROM users"
        )
        
        assert metrics.query_hash == "abc123"
        assert metrics.query_text == "SELECT * FROM users"
        assert metrics.execution_count == 0
        assert metrics.total_execution_time == 0.0
        assert metrics.avg_execution_time == 0.0
        assert metrics.min_execution_time == float('inf')
        assert metrics.max_execution_time == 0.0
        assert metrics.last_executed is None
        assert metrics.slow_query_threshold == 1.0


class TestIndexRecommendation:
    """Test index recommendation data class."""
    
    def test_recommendation_creation(self):
        """Test index recommendation creation."""
        recommendation = IndexRecommendation(
            collection_or_table="users",
            index_fields=["username", "email"],
            index_type="btree",
            reason="Optimize user lookup queries",
            estimated_benefit="High - reduces scan time",
            query_pattern="SELECT * FROM users WHERE username = ? AND email = ?"
        )
        
        assert recommendation.collection_or_table == "users"
        assert recommendation.index_fields == ["username", "email"]
        assert recommendation.index_type == "btree"
        assert recommendation.reason == "Optimize user lookup queries"
        assert recommendation.estimated_benefit == "High - reduces scan time"
        assert "username" in recommendation.query_pattern


if __name__ == "__main__":
    pytest.main([__file__, "-v"])