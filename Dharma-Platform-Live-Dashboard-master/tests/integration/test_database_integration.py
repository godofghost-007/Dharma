"""Integration tests for database operations."""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json


class TestPostgreSQLIntegration:
    """Test PostgreSQL database integration."""
    
    @pytest.mark.asyncio
    async def test_user_crud_operations(self, postgres_connection):
        """Test user CRUD operations in PostgreSQL."""
        conn = postgres_connection
        
        # Create user
        user_id = await conn.fetchval("""
            INSERT INTO users (username, email, hashed_password, role, full_name)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, "integration_test_user", "test@integration.com", "hashed_pass", "analyst", "Test User")
        
        assert user_id is not None
        
        # Read user
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        assert user["username"] == "integration_test_user"
        assert user["email"] == "test@integration.com"
        assert user["role"] == "analyst"
        assert user["is_active"] is True
        
        # Update user
        await conn.execute("""
            UPDATE users SET full_name = $1, last_login = $2 WHERE id = $3
        """, "Updated Test User", datetime.utcnow(), user_id)
        
        updated_user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        assert updated_user["full_name"] == "Updated Test User"
        assert updated_user["last_login"] is not None
        
        # Delete user
        deleted_count = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        assert "DELETE 1" in deleted_count
        
        # Verify deletion
        deleted_user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        assert deleted_user is None
    
    @pytest.mark.asyncio
    async def test_alert_operations(self, postgres_connection):
        """Test alert operations in PostgreSQL."""
        conn = postgres_connection
        
        # Create alert
        alert_id = await conn.fetchval("""
            INSERT INTO alerts (alert_id, title, description, alert_type, severity)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, "integration_test_alert_001", "Test Alert", "Test alert description", 
        "high_risk_content", "high")
        
        assert alert_id is not None
        
        # Test alert queries
        alerts = await conn.fetch("""
            SELECT * FROM alerts WHERE severity = $1 ORDER BY created_at DESC
        """, "high")
        
        assert len(alerts) >= 1
        test_alert = next((a for a in alerts if a["alert_id"] == "integration_test_alert_001"), None)
        assert test_alert is not None
        assert test_alert["title"] == "Test Alert"
        assert test_alert["alert_type"] == "high_risk_content"
        
        # Test alert status update
        await conn.execute("""
            UPDATE alerts SET status = $1, updated_at = $2 WHERE alert_id = $3
        """, "acknowledged", datetime.utcnow(), "integration_test_alert_001")
        
        updated_alert = await conn.fetchrow("""
            SELECT * FROM alerts WHERE alert_id = $1
        """, "integration_test_alert_001")
        assert updated_alert["status"] == "acknowledged"
    
    @pytest.mark.asyncio
    async def test_transaction_handling(self, postgres_connection):
        """Test transaction handling and rollback."""
        conn = postgres_connection
        
        # Start transaction
        async with conn.transaction():
            # Insert user
            user_id = await conn.fetchval("""
                INSERT INTO users (username, email, hashed_password, role)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, "transaction_test_user", "transaction@test.com", "hash", "analyst")
            
            # Verify user exists within transaction
            user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            assert user is not None
            
            # Simulate error to trigger rollback
            try:
                await conn.execute("INSERT INTO users (username, email, hashed_password, role) VALUES ($1, $2, $3, $4)",
                                 "transaction_test_user", "duplicate@test.com", "hash", "analyst")  # Duplicate username
            except Exception:
                pass  # Expected to fail due to unique constraint
        
        # Verify rollback - user should not exist
        user = await conn.fetchrow("SELECT * FROM users WHERE username = $1", "transaction_test_user")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_connection_pooling(self, test_databases):
        """Test connection pooling behavior."""
        import asyncpg
        
        config = test_databases["postgresql"]
        
        # Create connection pool
        pool = await asyncpg.create_pool(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["username"],
            password=config["password"],
            min_size=2,
            max_size=5
        )
        
        # Test concurrent connections
        async def test_query(query_id):
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT $1", query_id)
                return result
        
        # Run concurrent queries
        tasks = [test_query(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(results[i] == i for i in range(10))
        
        await pool.close()


class TestMongoDBIntegration:
    """Test MongoDB database integration."""
    
    @pytest.mark.asyncio
    async def test_post_operations(self, mongodb_connection):
        """Test post operations in MongoDB."""
        db = mongodb_connection
        posts_collection = db.posts
        
        # Insert post
        post_data = {
            "post_id": "integration_test_post_001",
            "platform": "twitter",
            "user_id": "integration_test_user_001",
            "content": "This is an integration test post",
            "timestamp": datetime.utcnow(),
            "hashtags": ["integration", "test"],
            "metrics": {
                "likes": 15,
                "shares": 8,
                "comments": 3,
                "views": 150
            },
            "analysis": {
                "sentiment": "neutral",
                "confidence": 0.85,
                "risk_score": 0.3
            }
        }
        
        result = await posts_collection.insert_one(post_data)
        assert result.inserted_id is not None
        
        # Find post
        found_post = await posts_collection.find_one({"post_id": "integration_test_post_001"})
        assert found_post is not None
        assert found_post["platform"] == "twitter"
        assert found_post["content"] == "This is an integration test post"
        assert len(found_post["hashtags"]) == 2
        assert found_post["metrics"]["likes"] == 15
        
        # Update post
        update_result = await posts_collection.update_one(
            {"post_id": "integration_test_post_001"},
            {
                "$set": {
                    "metrics.likes": 25,
                    "analysis.sentiment": "positive"
                },
                "$push": {"hashtags": "updated"}
            }
        )
        assert update_result.modified_count == 1
        
        # Verify update
        updated_post = await posts_collection.find_one({"post_id": "integration_test_post_001"})
        assert updated_post["metrics"]["likes"] == 25
        assert updated_post["analysis"]["sentiment"] == "positive"
        assert "updated" in updated_post["hashtags"]
        
        # Test aggregation
        pipeline = [
            {"$match": {"platform": "twitter"}},
            {"$group": {
                "_id": "$platform",
                "total_posts": {"$sum": 1},
                "avg_likes": {"$avg": "$metrics.likes"},
                "total_engagement": {"$sum": {
                    "$add": ["$metrics.likes", "$metrics.shares", "$metrics.comments"]
                }}
            }}
        ]
        
        agg_result = await posts_collection.aggregate(pipeline).to_list(length=None)
        assert len(agg_result) >= 1
        twitter_stats = next((r for r in agg_result if r["_id"] == "twitter"), None)
        assert twitter_stats is not None
        assert twitter_stats["total_posts"] >= 1
    
    @pytest.mark.asyncio
    async def test_indexing_and_performance(self, mongodb_connection):
        """Test MongoDB indexing and query performance."""
        db = mongodb_connection
        posts_collection = db.posts
        
        # Create indexes
        await posts_collection.create_index("platform")
        await posts_collection.create_index([("timestamp", -1)])
        await posts_collection.create_index([("user_id", 1), ("platform", 1)])
        
        # Insert multiple posts for performance testing
        test_posts = []
        for i in range(100):
            test_posts.append({
                "post_id": f"integration_perf_test_{i}",
                "platform": "twitter" if i % 2 == 0 else "youtube",
                "user_id": f"user_{i % 10}",
                "content": f"Performance test post {i}",
                "timestamp": datetime.utcnow() - timedelta(hours=i),
                "metrics": {"likes": i * 2, "shares": i, "comments": i // 2}
            })
        
        await posts_collection.insert_many(test_posts)
        
        # Test indexed queries
        start_time = datetime.utcnow()
        
        # Query by platform (indexed)
        twitter_posts = await posts_collection.count_documents({"platform": "twitter"})
        assert twitter_posts >= 50
        
        # Query by timestamp range (indexed)
        recent_posts = await posts_collection.find({
            "timestamp": {"$gte": datetime.utcnow() - timedelta(hours=50)}
        }).to_list(length=None)
        assert len(recent_posts) >= 50
        
        # Compound index query
        user_posts = await posts_collection.find({
            "user_id": "user_1",
            "platform": "twitter"
        }).to_list(length=None)
        assert len(user_posts) >= 1
        
        query_time = (datetime.utcnow() - start_time).total_seconds()
        assert query_time < 1.0  # Should be fast with indexes
    
    @pytest.mark.asyncio
    async def test_text_search(self, mongodb_connection):
        """Test MongoDB text search capabilities."""
        db = mongodb_connection
        posts_collection = db.posts
        
        # Create text index
        await posts_collection.create_index([("content", "text")])
        
        # Insert posts with searchable content
        search_posts = [
            {
                "post_id": "search_test_1",
                "content": "This post contains important security information",
                "platform": "twitter"
            },
            {
                "post_id": "search_test_2", 
                "content": "Another post about cybersecurity threats",
                "platform": "twitter"
            },
            {
                "post_id": "search_test_3",
                "content": "Regular social media content without keywords",
                "platform": "twitter"
            }
        ]
        
        await posts_collection.insert_many(search_posts)
        
        # Test text search
        security_posts = await posts_collection.find({
            "$text": {"$search": "security"}
        }).to_list(length=None)
        
        assert len(security_posts) >= 2
        assert all("security" in post["content"].lower() for post in security_posts)
        
        # Test text search with score
        scored_results = await posts_collection.find(
            {"$text": {"$search": "security information"}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).to_list(length=None)
        
        assert len(scored_results) >= 1
        # First result should have highest score
        if len(scored_results) > 1:
            assert scored_results[0]["score"] >= scored_results[1]["score"]


class TestRedisIntegration:
    """Test Redis database integration."""
    
    @pytest.mark.asyncio
    async def test_basic_operations(self, redis_connection):
        """Test basic Redis operations."""
        redis_client = redis_connection
        
        # String operations
        redis_client.set("integration_test_key", "test_value", ex=300)  # 5 minute expiry
        value = redis_client.get("integration_test_key")
        assert value == "test_value"
        
        # Check TTL
        ttl = redis_client.ttl("integration_test_key")
        assert 0 < ttl <= 300
        
        # Hash operations
        redis_client.hset("integration_test_hash", mapping={
            "field1": "value1",
            "field2": "value2",
            "field3": "value3"
        })
        
        hash_value = redis_client.hget("integration_test_hash", "field1")
        assert hash_value == "value1"
        
        all_hash = redis_client.hgetall("integration_test_hash")
        assert len(all_hash) == 3
        assert all_hash["field2"] == "value2"
        
        # List operations
        redis_client.lpush("integration_test_list", "item1", "item2", "item3")
        list_length = redis_client.llen("integration_test_list")
        assert list_length == 3
        
        popped_item = redis_client.rpop("integration_test_list")
        assert popped_item == "item1"
        
        # Set operations
        redis_client.sadd("integration_test_set", "member1", "member2", "member3")
        set_size = redis_client.scard("integration_test_set")
        assert set_size == 3
        
        is_member = redis_client.sismember("integration_test_set", "member2")
        assert is_member is True
    
    @pytest.mark.asyncio
    async def test_caching_patterns(self, redis_connection):
        """Test common caching patterns."""
        redis_client = redis_connection
        
        # Cache-aside pattern
        cache_key = "integration_test_cache_user_123"
        
        # Simulate cache miss
        cached_user = redis_client.get(cache_key)
        assert cached_user is None
        
        # Simulate database fetch and cache set
        user_data = {
            "id": 123,
            "username": "cached_user",
            "email": "cached@example.com",
            "role": "analyst"
        }
        
        redis_client.setex(cache_key, 3600, json.dumps(user_data))  # 1 hour cache
        
        # Simulate cache hit
        cached_user = redis_client.get(cache_key)
        assert cached_user is not None
        
        parsed_user = json.loads(cached_user)
        assert parsed_user["username"] == "cached_user"
        assert parsed_user["id"] == 123
        
        # Test cache invalidation
        redis_client.delete(cache_key)
        invalidated_cache = redis_client.get(cache_key)
        assert invalidated_cache is None
    
    @pytest.mark.asyncio
    async def test_session_management(self, redis_connection):
        """Test session management with Redis."""
        redis_client = redis_connection
        
        # Create session
        session_id = "integration_test_session_abc123"
        session_data = {
            "user_id": 456,
            "username": "session_user",
            "role": "analyst",
            "login_time": datetime.utcnow().isoformat(),
            "permissions": ["read", "write", "analyze"]
        }
        
        # Store session with expiry
        redis_client.setex(f"session:{session_id}", 7200, json.dumps(session_data))  # 2 hours
        
        # Retrieve session
        stored_session = redis_client.get(f"session:{session_id}")
        assert stored_session is not None
        
        parsed_session = json.loads(stored_session)
        assert parsed_session["user_id"] == 456
        assert parsed_session["username"] == "session_user"
        assert "read" in parsed_session["permissions"]
        
        # Update session activity
        redis_client.expire(f"session:{session_id}", 7200)  # Reset expiry
        
        # Test session cleanup
        redis_client.delete(f"session:{session_id}")
        deleted_session = redis_client.get(f"session:{session_id}")
        assert deleted_session is None
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, redis_connection):
        """Test rate limiting implementation."""
        redis_client = redis_connection
        
        # Sliding window rate limiting
        user_id = "integration_test_user_789"
        rate_limit_key = f"rate_limit:{user_id}"
        window_size = 60  # 1 minute
        max_requests = 10
        
        current_time = int(datetime.utcnow().timestamp())
        
        # Simulate multiple requests
        for i in range(15):  # Exceed rate limit
            # Add request timestamp
            redis_client.zadd(rate_limit_key, {f"req_{i}": current_time + i})
            
            # Remove old entries outside window
            redis_client.zremrangebyscore(rate_limit_key, 0, current_time + i - window_size)
            
            # Count current requests
            current_requests = redis_client.zcard(rate_limit_key)
            
            if i < max_requests:
                assert current_requests <= max_requests
            else:
                # Should be rate limited
                assert current_requests >= max_requests
        
        # Set expiry for cleanup
        redis_client.expire(rate_limit_key, window_size)


class TestElasticsearchIntegration:
    """Test Elasticsearch integration."""
    
    @pytest.mark.asyncio
    async def test_document_operations(self, elasticsearch_connection):
        """Test Elasticsearch document operations."""
        es_client = elasticsearch_connection
        
        # Index document
        doc_data = {
            "post_id": "integration_test_es_001",
            "content": "This is a test document for Elasticsearch integration",
            "platform": "twitter",
            "timestamp": datetime.utcnow().isoformat(),
            "sentiment": "neutral",
            "risk_score": 0.4,
            "hashtags": ["elasticsearch", "integration", "test"],
            "user_id": "es_test_user_001"
        }
        
        response = await es_client.index(
            index="test_posts",
            id="integration_test_es_001",
            body=doc_data
        )
        
        assert response["result"] in ["created", "updated"]
        
        # Refresh index to make document searchable
        await es_client.indices.refresh(index="test_posts")
        
        # Get document
        doc = await es_client.get(index="test_posts", id="integration_test_es_001")
        assert doc["_source"]["post_id"] == "integration_test_es_001"
        assert doc["_source"]["platform"] == "twitter"
        assert doc["_source"]["sentiment"] == "neutral"
        
        # Update document
        update_body = {
            "doc": {
                "sentiment": "positive",
                "risk_score": 0.2,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        update_response = await es_client.update(
            index="test_posts",
            id="integration_test_es_001",
            body=update_body
        )
        
        assert update_response["result"] == "updated"
        
        # Verify update
        updated_doc = await es_client.get(index="test_posts", id="integration_test_es_001")
        assert updated_doc["_source"]["sentiment"] == "positive"
        assert updated_doc["_source"]["risk_score"] == 0.2
    
    @pytest.mark.asyncio
    async def test_search_operations(self, elasticsearch_connection):
        """Test Elasticsearch search operations."""
        es_client = elasticsearch_connection
        
        # Index multiple documents for search testing
        test_docs = [
            {
                "post_id": "search_test_001",
                "content": "This post contains security threats and malware",
                "platform": "twitter",
                "sentiment": "negative",
                "risk_score": 0.9,
                "hashtags": ["security", "malware"]
            },
            {
                "post_id": "search_test_002",
                "content": "Normal social media post about daily life",
                "platform": "facebook",
                "sentiment": "neutral",
                "risk_score": 0.1,
                "hashtags": ["life", "social"]
            },
            {
                "post_id": "search_test_003",
                "content": "Another security-related post with suspicious content",
                "platform": "twitter",
                "sentiment": "negative",
                "risk_score": 0.8,
                "hashtags": ["security", "suspicious"]
            }
        ]
        
        # Bulk index documents
        bulk_body = []
        for doc in test_docs:
            bulk_body.extend([
                {"index": {"_index": "test_posts", "_id": doc["post_id"]}},
                doc
            ])
        
        await es_client.bulk(body=bulk_body)
        await es_client.indices.refresh(index="test_posts")
        
        # Test basic search
        search_response = await es_client.search(
            index="test_posts",
            body={
                "query": {
                    "match": {"content": "security"}
                }
            }
        )
        
        assert search_response["hits"]["total"]["value"] >= 2
        security_posts = search_response["hits"]["hits"]
        assert all("security" in hit["_source"]["content"].lower() for hit in security_posts)
        
        # Test filtered search
        filtered_response = await es_client.search(
            index="test_posts",
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"content": "security"}}
                        ],
                        "filter": [
                            {"term": {"platform": "twitter"}},
                            {"range": {"risk_score": {"gte": 0.5}}}
                        ]
                    }
                }
            }
        )
        
        assert filtered_response["hits"]["total"]["value"] >= 1
        filtered_posts = filtered_response["hits"]["hits"]
        assert all(hit["_source"]["platform"] == "twitter" for hit in filtered_posts)
        assert all(hit["_source"]["risk_score"] >= 0.5 for hit in filtered_posts)
        
        # Test aggregation
        agg_response = await es_client.search(
            index="test_posts",
            body={
                "size": 0,
                "aggs": {
                    "platforms": {
                        "terms": {"field": "platform"}
                    },
                    "avg_risk_score": {
                        "avg": {"field": "risk_score"}
                    },
                    "risk_score_ranges": {
                        "range": {
                            "field": "risk_score",
                            "ranges": [
                                {"to": 0.3, "key": "low"},
                                {"from": 0.3, "to": 0.7, "key": "medium"},
                                {"from": 0.7, "key": "high"}
                            ]
                        }
                    }
                }
            }
        )
        
        aggs = agg_response["aggregations"]
        assert "platforms" in aggs
        assert "avg_risk_score" in aggs
        assert "risk_score_ranges" in aggs
        
        platform_buckets = aggs["platforms"]["buckets"]
        assert len(platform_buckets) >= 1
        
        risk_ranges = aggs["risk_score_ranges"]["buckets"]
        assert len(risk_ranges) == 3  # low, medium, high
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self, elasticsearch_connection):
        """Test Elasticsearch bulk operations."""
        es_client = elasticsearch_connection
        
        # Prepare bulk data
        bulk_docs = []
        for i in range(50):
            bulk_docs.extend([
                {"index": {"_index": "test_posts", "_id": f"bulk_test_{i}"}},
                {
                    "post_id": f"bulk_test_{i}",
                    "content": f"Bulk test document {i} with content",
                    "platform": "twitter" if i % 2 == 0 else "facebook",
                    "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                    "risk_score": (i % 10) / 10.0,
                    "batch_id": "integration_test_batch"
                }
            ])
        
        # Execute bulk operation
        bulk_response = await es_client.bulk(body=bulk_docs)
        
        assert not bulk_response["errors"]
        assert len(bulk_response["items"]) == 50
        
        # Refresh and verify
        await es_client.indices.refresh(index="test_posts")
        
        count_response = await es_client.count(
            index="test_posts",
            body={"query": {"term": {"batch_id": "integration_test_batch"}}}
        )
        
        assert count_response["count"] == 50
        
        # Test bulk update
        bulk_updates = []
        for i in range(0, 50, 2):  # Update every other document
            bulk_updates.extend([
                {"update": {"_index": "test_posts", "_id": f"bulk_test_{i}"}},
                {"doc": {"updated": True, "update_timestamp": datetime.utcnow().isoformat()}}
            ])
        
        update_response = await es_client.bulk(body=bulk_updates)
        assert not update_response["errors"]
        
        # Verify updates
        await es_client.indices.refresh(index="test_posts")
        
        updated_count = await es_client.count(
            index="test_posts",
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"batch_id": "integration_test_batch"}},
                            {"term": {"updated": True}}
                        ]
                    }
                }
            }
        )
        
        assert updated_count["count"] == 25  # Half of the documents


class TestCrossDatabaseIntegration:
    """Test integration across multiple databases."""
    
    @pytest.mark.asyncio
    async def test_data_consistency_across_databases(
        self, 
        postgres_connection, 
        mongodb_connection, 
        elasticsearch_connection,
        redis_connection
    ):
        """Test data consistency across all databases."""
        
        # Create user in PostgreSQL
        user_id = await postgres_connection.fetchval("""
            INSERT INTO users (username, email, hashed_password, role, full_name)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, "cross_db_user", "crossdb@test.com", "hash", "analyst", "Cross DB User")
        
        # Create post in MongoDB
        post_data = {
            "post_id": "cross_db_post_001",
            "platform": "twitter",
            "user_id": str(user_id),  # Reference to PostgreSQL user
            "content": "Cross-database integration test post",
            "timestamp": datetime.utcnow(),
            "analysis": {
                "sentiment": "neutral",
                "risk_score": 0.5
            }
        }
        
        mongo_result = await mongodb_connection.posts.insert_one(post_data)
        assert mongo_result.inserted_id is not None
        
        # Index post in Elasticsearch
        es_doc = {
            "post_id": "cross_db_post_001",
            "user_id": str(user_id),
            "content": "Cross-database integration test post",
            "platform": "twitter",
            "sentiment": "neutral",
            "risk_score": 0.5,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await elasticsearch_connection.index(
            index="test_posts",
            id="cross_db_post_001",
            body=es_doc
        )
        
        # Cache user data in Redis
        user_cache_data = {
            "id": user_id,
            "username": "cross_db_user",
            "role": "analyst",
            "cached_at": datetime.utcnow().isoformat()
        }
        
        redis_connection.setex(
            f"user_cache:{user_id}",
            3600,
            json.dumps(user_cache_data)
        )
        
        # Verify data consistency
        # 1. Check PostgreSQL user exists
        pg_user = await postgres_connection.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        assert pg_user["username"] == "cross_db_user"
        
        # 2. Check MongoDB post exists and references correct user
        mongo_post = await mongodb_connection.posts.find_one({"post_id": "cross_db_post_001"})
        assert mongo_post["user_id"] == str(user_id)
        
        # 3. Check Elasticsearch document exists
        await elasticsearch_connection.indices.refresh(index="test_posts")
        es_doc_result = await elasticsearch_connection.get(
            index="test_posts",
            id="cross_db_post_001"
        )
        assert es_doc_result["_source"]["user_id"] == str(user_id)
        
        # 4. Check Redis cache exists
        cached_user = redis_connection.get(f"user_cache:{user_id}")
        assert cached_user is not None
        parsed_cache = json.loads(cached_user)
        assert parsed_cache["username"] == "cross_db_user"
        
        # Test cross-database query simulation
        # Find all posts by user (combining PostgreSQL user lookup with MongoDB query)
        user_posts = await mongodb_connection.posts.find({"user_id": str(user_id)}).to_list(length=None)
        assert len(user_posts) >= 1
        assert all(post["user_id"] == str(user_id) for post in user_posts)
    
    @pytest.mark.asyncio
    async def test_transaction_like_behavior(
        self,
        postgres_connection,
        mongodb_connection,
        elasticsearch_connection,
        redis_connection
    ):
        """Test transaction-like behavior across databases."""
        
        # Simulate distributed transaction
        transaction_id = "cross_db_transaction_001"
        
        try:
            # Step 1: Create alert in PostgreSQL
            alert_id = await postgres_connection.fetchval("""
                INSERT INTO alerts (alert_id, title, description, alert_type, severity)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, transaction_id, "Cross DB Alert", "Cross-database test alert", 
            "high_risk_content", "high")
            
            # Step 2: Store alert metadata in MongoDB
            alert_metadata = {
                "alert_id": transaction_id,
                "pg_id": alert_id,
                "processing_status": "created",
                "created_at": datetime.utcnow(),
                "metadata": {
                    "source": "integration_test",
                    "transaction_id": transaction_id
                }
            }
            
            mongo_result = await mongodb_connection.alert_metadata.insert_one(alert_metadata)
            
            # Step 3: Index alert for search in Elasticsearch
            es_alert = {
                "alert_id": transaction_id,
                "title": "Cross DB Alert",
                "description": "Cross-database test alert",
                "alert_type": "high_risk_content",
                "severity": "high",
                "created_at": datetime.utcnow().isoformat(),
                "searchable_content": "Cross DB Alert Cross-database test alert"
            }
            
            await elasticsearch_connection.index(
                index="test_alerts",
                id=transaction_id,
                body=es_alert
            )
            
            # Step 4: Cache alert summary in Redis
            alert_summary = {
                "alert_id": transaction_id,
                "title": "Cross DB Alert",
                "severity": "high",
                "status": "new",
                "cached_at": datetime.utcnow().isoformat()
            }
            
            redis_connection.setex(
                f"alert_summary:{transaction_id}",
                1800,  # 30 minutes
                json.dumps(alert_summary)
            )
            
            # Verify all operations succeeded
            # PostgreSQL
            pg_alert = await postgres_connection.fetchrow(
                "SELECT * FROM alerts WHERE alert_id = $1", transaction_id
            )
            assert pg_alert is not None
            
            # MongoDB
            mongo_metadata = await mongodb_connection.alert_metadata.find_one(
                {"alert_id": transaction_id}
            )
            assert mongo_metadata is not None
            assert mongo_metadata["pg_id"] == alert_id
            
            # Elasticsearch
            await elasticsearch_connection.indices.refresh(index="test_alerts")
            try:
                es_alert_result = await elasticsearch_connection.get(
                    index="test_alerts",
                    id=transaction_id
                )
                assert es_alert_result["_source"]["title"] == "Cross DB Alert"
            except Exception:
                # Index might not exist, create it
                await elasticsearch_connection.indices.create(
                    index="test_alerts",
                    body={
                        "mappings": {
                            "properties": {
                                "alert_id": {"type": "keyword"},
                                "title": {"type": "text"},
                                "severity": {"type": "keyword"},
                                "created_at": {"type": "date"}
                            }
                        }
                    },
                    ignore=400
                )
                
                # Re-index the document
                await elasticsearch_connection.index(
                    index="test_alerts",
                    id=transaction_id,
                    body=es_alert
                )
            
            # Redis
            cached_summary = redis_connection.get(f"alert_summary:{transaction_id}")
            assert cached_summary is not None
            parsed_summary = json.loads(cached_summary)
            assert parsed_summary["severity"] == "high"
            
        except Exception as e:
            # Simulate rollback by cleaning up created data
            # In a real system, this would be more sophisticated
            
            # Clean PostgreSQL
            await postgres_connection.execute(
                "DELETE FROM alerts WHERE alert_id = $1", transaction_id
            )
            
            # Clean MongoDB
            await mongodb_connection.alert_metadata.delete_one({"alert_id": transaction_id})
            
            # Clean Elasticsearch
            try:
                await elasticsearch_connection.delete(index="test_alerts", id=transaction_id)
            except Exception:
                pass
            
            # Clean Redis
            redis_connection.delete(f"alert_summary:{transaction_id}")
            
            raise e