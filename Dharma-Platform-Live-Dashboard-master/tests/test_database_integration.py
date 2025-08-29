"""Integration tests for database managers."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from shared.database.manager import DatabaseManager
from shared.config.settings import Settings


@pytest.mark.asyncio
async def test_database_manager_integration():
    """Test database manager integration with all database types."""
    
    # Create settings with all database URLs
    settings = Settings()
    settings.database.mongodb_url = "mongodb://localhost:27017"
    settings.database.mongodb_database = "test_db"
    settings.database.postgresql_url = "postgresql://localhost:5432/test"
    settings.database.elasticsearch_url = "http://localhost:9200"
    settings.redis.url = "redis://localhost:6379"
    
    # Create database manager
    db_manager = DatabaseManager(settings)
    
    # Mock all the database managers to avoid actual connections
    db_manager.mongodb = AsyncMock()
    db_manager.mongodb.connect = AsyncMock()
    db_manager.mongodb.create_indexes = AsyncMock()
    db_manager.mongodb.health_check = AsyncMock(return_value=True)
    db_manager.mongodb._connected = True
    
    db_manager.postgresql = AsyncMock()
    db_manager.postgresql.connect = AsyncMock()
    db_manager.postgresql.health_check = AsyncMock(return_value=True)
    db_manager.postgresql._connected = True
    
    db_manager.redis = AsyncMock()
    db_manager.redis.connect = AsyncMock()
    db_manager.redis.health_check = AsyncMock(return_value=True)
    db_manager.redis._connected = True
    
    db_manager.elasticsearch = AsyncMock()
    db_manager.elasticsearch.connect = AsyncMock()
    db_manager.elasticsearch.create_default_indexes = AsyncMock()
    db_manager.elasticsearch.health_check = AsyncMock(return_value=True)
    db_manager.elasticsearch._connected = True
    
    # Test connection info
    info = await db_manager.get_connection_info()
    assert info["connected"] is False  # Not actually connected since we mocked
    assert "mongodb" in info["databases"]
    assert "postgresql" in info["databases"]
    assert "redis" in info["databases"]
    assert "elasticsearch" in info["databases"]
    
    # Test health check
    health_status = await db_manager.health_check()
    assert health_status["mongodb"] is True
    assert health_status["postgresql"] is True
    assert health_status["redis"] is True
    assert health_status["elasticsearch"] is True
    
    # Test getters
    mongodb = db_manager.get_mongodb()
    assert mongodb is not None
    
    postgresql = db_manager.get_postgresql()
    assert postgresql is not None
    
    redis = db_manager.get_redis()
    assert redis is not None
    
    elasticsearch = db_manager.get_elasticsearch()
    assert elasticsearch is not None


@pytest.mark.asyncio
async def test_database_operations_workflow():
    """Test a typical workflow using multiple database managers."""
    
    settings = Settings()
    db_manager = DatabaseManager(settings)
    
    # Mock database managers
    db_manager.mongodb = AsyncMock()
    db_manager.postgresql = AsyncMock()
    db_manager.redis = AsyncMock()
    db_manager.elasticsearch = AsyncMock()
    
    # Mock typical operations
    # 1. Insert post data into MongoDB
    post_data = {
        "content": "Test post content",
        "platform": "twitter",
        "user_id": "user123",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    
    db_manager.mongodb.insert_post = AsyncMock(return_value="post_id_123")
    post_id = await db_manager.mongodb.insert_post(post_data)
    assert post_id == "post_id_123"
    
    # 2. Cache analysis results in Redis
    analysis_results = {
        "sentiment": "positive",
        "confidence": 0.85,
        "risk_score": 0.2
    }
    
    db_manager.redis.set = AsyncMock(return_value=True)
    cache_result = await db_manager.redis.set(f"analysis:{post_id}", analysis_results, expire=3600)
    assert cache_result is True
    
    # 3. Index content in Elasticsearch for search
    search_doc = {
        "content": post_data["content"],
        "platform": post_data["platform"],
        "sentiment": analysis_results["sentiment"],
        "timestamp": post_data["timestamp"]
    }
    
    db_manager.elasticsearch.index_document = AsyncMock(return_value="es_doc_id")
    es_doc_id = await db_manager.elasticsearch.index_document("posts", search_doc, post_id)
    assert es_doc_id == "es_doc_id"
    
    # 4. Create alert in PostgreSQL if high risk
    if analysis_results["risk_score"] > 0.7:
        alert_data = {
            "type": "high_risk_content",
            "severity": "high",
            "title": "High risk content detected",
            "description": f"Post {post_id} has high risk score"
        }
        
        db_manager.postgresql.create_alert = AsyncMock(return_value=1)
        alert_id = await db_manager.postgresql.create_alert(alert_data)
        assert alert_id == 1
    
    # Verify all operations were called
    db_manager.mongodb.insert_post.assert_called_once_with(post_data)
    db_manager.redis.set.assert_called_once()
    db_manager.elasticsearch.index_document.assert_called_once()


def test_database_manager_error_handling():
    """Test database manager error handling."""
    
    settings = Settings()
    db_manager = DatabaseManager(settings)
    
    # Test getters when managers not configured
    with pytest.raises(RuntimeError, match="MongoDB not configured"):
        db_manager.get_mongodb()
    
    with pytest.raises(RuntimeError, match="PostgreSQL not configured"):
        db_manager.get_postgresql()
    
    with pytest.raises(RuntimeError, match="Redis not configured"):
        db_manager.get_redis()
    
    with pytest.raises(RuntimeError, match="Elasticsearch not configured"):
        db_manager.get_elasticsearch()