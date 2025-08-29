"""Tests for database managers."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from shared.database.redis import RedisManager
from shared.database.mongodb import MongoDBManager
from shared.database.postgresql import PostgreSQLManager
from shared.database.elasticsearch import ElasticsearchManager
from shared.database.manager import DatabaseManager
from shared.config.settings import Settings


class TestRedisManager:
    """Test cases for Redis manager."""
    
    @pytest.mark.asyncio
    async def test_redis_manager_connection(self):
        """Test Redis manager connection."""
        manager = RedisManager("redis://localhost:6379")
        
        # Mock the Redis client
        manager.client = AsyncMock()
        manager.client.ping = AsyncMock(return_value=True)
        manager._connected = True
        
        # Test health check
        health = await manager.health_check()
        assert health is True
        
        # Test set/get operations
        await manager.set("test_key", "test_value")
        manager.client.set.assert_called_once()
        
        manager.client.get = AsyncMock(return_value="test_value")
        value = await manager.get("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_redis_manager_json_operations(self):
        """Test Redis manager JSON serialization."""
        manager = RedisManager("redis://localhost:6379")
        manager.client = AsyncMock()
        manager._connected = True
        
        # Test JSON serialization
        test_data = {"key": "value", "number": 42}
        await manager.set("json_key", test_data)
        
        # Verify JSON was serialized
        call_args = manager.client.set.call_args
        assert '"key": "value"' in call_args[0][1]
        assert '"number": 42' in call_args[0][1]
    
    def test_redis_manager_initialization(self):
        """Test Redis manager initialization."""
        manager = RedisManager("redis://localhost:6379", max_connections=50)
        assert manager.redis_url == "redis://localhost:6379"
        assert manager.max_connections == 50
        assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_redis_list_operations(self):
        """Test Redis list operations."""
        manager = RedisManager("redis://localhost:6379")
        manager.client = AsyncMock()
        manager._connected = True
        
        # Test lpush
        manager.client.lpush = AsyncMock(return_value=1)
        result = await manager.lpush("test_list", "item1", "item2")
        assert result == 1
        
        # Test rpop
        manager.client.rpop = AsyncMock(return_value="item1")
        item = await manager.rpop("test_list")
        assert item == "item1"


class TestMongoDBManager:
    """Test cases for MongoDB manager."""
    
    def test_mongodb_manager_initialization(self):
        """Test MongoDB manager initialization."""
        manager = MongoDBManager("mongodb://localhost:27017", "test_db")
        assert manager.connection_string == "mongodb://localhost:27017"
        assert manager.database_name == "test_db"
        assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_mongodb_health_check(self):
        """Test MongoDB health check."""
        manager = MongoDBManager("mongodb://localhost:27017", "test_db")
        manager.client = AsyncMock()
        manager.client.admin.command = AsyncMock(return_value={"ok": 1})
        manager._connected = True
        
        health = await manager.health_check()
        assert health is True
    
    @pytest.mark.asyncio
    async def test_mongodb_post_operations(self):
        """Test MongoDB post operations."""
        manager = MongoDBManager("mongodb://localhost:27017", "test_db")
        manager.database = AsyncMock()
        manager.database.posts.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
        
        post_data = {
            "content": "Test post",
            "platform": "twitter",
            "user_id": "user123"
        }
        
        result = await manager.insert_post(post_data)
        assert result == "test_id"
    
    @pytest.mark.asyncio
    async def test_mongodb_user_profile_operations(self):
        """Test MongoDB user profile operations."""
        manager = MongoDBManager("mongodb://localhost:27017", "test_db")
        manager.database = AsyncMock()
        
        # Test insert user profile
        manager.database.user_profiles.replace_one = AsyncMock(
            return_value=MagicMock(upserted_id="user_profile_id")
        )
        
        user_data = {
            "platform": "twitter",
            "user_id": "user123",
            "username": "testuser"
        }
        
        result = await manager.insert_user_profile(user_data)
        assert result == "user_profile_id"
        
        # Test get user profile
        manager.database.user_profiles.find_one = AsyncMock(return_value=user_data)
        profile = await manager.get_user_profile("twitter", "user123")
        assert profile == user_data


class TestPostgreSQLManager:
    """Test cases for PostgreSQL manager."""
    
    def test_postgresql_manager_initialization(self):
        """Test PostgreSQL manager initialization."""
        manager = PostgreSQLManager("postgresql://localhost:5432/test")
        assert manager.connection_string == "postgresql://localhost:5432/test"
        assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_postgresql_health_check(self):
        """Test PostgreSQL health check."""
        manager = PostgreSQLManager("postgresql://localhost:5432/test")
        
        # Test when not connected
        health = await manager.health_check()
        assert health is False
        
        # Test when connected but no pool
        manager._connected = True
        health = await manager.health_check()
        assert health is False
    
    @pytest.mark.asyncio
    async def test_postgresql_user_operations(self):
        """Test PostgreSQL user operations."""
        manager = PostgreSQLManager("postgresql://localhost:5432/test")
        manager.pool = AsyncMock()
        
        # Mock fetchval for create_user
        manager.fetchval = AsyncMock(return_value=1)
        
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "role": "analyst",
            "password_hash": "hashed_password"
        }
        
        user_id = await manager.create_user(user_data)
        assert user_id == 1
        
        # Mock fetchrow for get_user_by_id
        manager.fetchrow = AsyncMock(return_value=user_data)
        user = await manager.get_user_by_id(1)
        assert user == user_data
    
    @pytest.mark.asyncio
    async def test_postgresql_alert_operations(self):
        """Test PostgreSQL alert operations."""
        manager = PostgreSQLManager("postgresql://localhost:5432/test")
        manager.fetchval = AsyncMock(return_value=1)
        manager.execute = AsyncMock()
        
        alert_data = {
            "type": "high_risk_content",
            "severity": "high",
            "title": "Test Alert",
            "description": "Test alert description"
        }
        
        alert_id = await manager.create_alert(alert_data)
        assert alert_id == 1
        
        # Test acknowledge alert
        result = await manager.acknowledge_alert(1, 1)
        assert result is True


class TestElasticsearchManager:
    """Test cases for Elasticsearch manager."""
    
    def test_elasticsearch_manager_initialization(self):
        """Test Elasticsearch manager initialization."""
        manager = ElasticsearchManager("http://localhost:9200", "test")
        assert manager.elasticsearch_url == "http://localhost:9200"
        assert manager.index_prefix == "test"
        assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_elasticsearch_health_check(self):
        """Test Elasticsearch health check."""
        manager = ElasticsearchManager("http://localhost:9200", "test")
        manager.client = AsyncMock()
        manager.client.cluster.health = AsyncMock(return_value={"status": "green"})
        manager._connected = True
        
        health = await manager.health_check()
        assert health is True
    
    @pytest.mark.asyncio
    async def test_elasticsearch_index_operations(self):
        """Test Elasticsearch index operations."""
        manager = ElasticsearchManager("http://localhost:9200", "test")
        manager.client = AsyncMock()
        
        # Test create index
        manager.client.indices.create = AsyncMock()
        mapping = {"properties": {"content": {"type": "text"}}}
        
        result = await manager.create_index("posts", mapping)
        assert result is True
        
        # Test index document
        manager.client.index = AsyncMock(return_value={"_id": "doc123"})
        document = {"content": "Test document"}
        
        doc_id = await manager.index_document("posts", document)
        assert doc_id == "doc123"
    
    @pytest.mark.asyncio
    async def test_elasticsearch_search_operations(self):
        """Test Elasticsearch search operations."""
        manager = ElasticsearchManager("http://localhost:9200", "test")
        manager.client = AsyncMock()
        
        # Mock search response
        search_response = {
            "hits": {
                "hits": [
                    {"_source": {"content": "Test document 1"}},
                    {"_source": {"content": "Test document 2"}}
                ],
                "total": {"value": 2}
            }
        }
        manager.client.search = AsyncMock(return_value=search_response)
        
        query = {"match": {"content": "test"}}
        result = await manager.search("posts", query)
        
        assert result == search_response
        assert len(result["hits"]["hits"]) == 2


class TestDatabaseManager:
    """Test cases for unified database manager."""
    
    def test_database_manager_initialization(self):
        """Test database manager initialization."""
        settings = Settings()
        manager = DatabaseManager(settings)
        
        assert manager.settings == settings
        assert manager.mongodb is None
        assert manager.postgresql is None
        assert manager.redis is None
        assert manager.elasticsearch is None
        assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_database_manager_health_check(self):
        """Test database manager health check."""
        settings = Settings()
        manager = DatabaseManager(settings)
        
        # Mock individual managers
        manager.mongodb = AsyncMock()
        manager.mongodb.health_check = AsyncMock(return_value=True)
        
        manager.postgresql = AsyncMock()
        manager.postgresql.health_check = AsyncMock(return_value=True)
        
        manager.redis = AsyncMock()
        manager.redis.health_check = AsyncMock(return_value=True)
        
        manager.elasticsearch = AsyncMock()
        manager.elasticsearch.health_check = AsyncMock(return_value=True)
        
        health_status = await manager.health_check()
        
        assert health_status["mongodb"] is True
        assert health_status["postgresql"] is True
        assert health_status["redis"] is True
        assert health_status["elasticsearch"] is True
    
    def test_database_manager_getters(self):
        """Test database manager getter methods."""
        settings = Settings()
        manager = DatabaseManager(settings)
        
        # Test exception when managers not configured
        with pytest.raises(RuntimeError, match="MongoDB not configured"):
            manager.get_mongodb()
        
        with pytest.raises(RuntimeError, match="PostgreSQL not configured"):
            manager.get_postgresql()
        
        with pytest.raises(RuntimeError, match="Redis not configured"):
            manager.get_redis()
        
        with pytest.raises(RuntimeError, match="Elasticsearch not configured"):
            manager.get_elasticsearch()
        
        # Test successful getters
        manager.mongodb = MagicMock()
        manager.postgresql = MagicMock()
        manager.redis = MagicMock()
        manager.elasticsearch = MagicMock()
        
        assert manager.get_mongodb() == manager.mongodb
        assert manager.get_postgresql() == manager.postgresql
        assert manager.get_redis() == manager.redis
        assert manager.get_elasticsearch() == manager.elasticsearch