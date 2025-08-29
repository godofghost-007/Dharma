#!/usr/bin/env python3
"""
Example script demonstrating how to use the database connection utilities.

This script shows how to:
1. Initialize database connections
2. Perform basic operations on each database
3. Handle errors and cleanup
"""

import asyncio
import json
from datetime import datetime
from shared.database import (
    DatabaseManager,
    get_database_manager,
    close_database_manager
)
from shared.config.settings import Settings


async def demonstrate_mongodb_operations(db_manager: DatabaseManager):
    """Demonstrate MongoDB operations."""
    print("\n=== MongoDB Operations ===")
    
    try:
        mongodb = db_manager.get_mongodb()
        
        # Insert a sample post
        post_data = {
            "content": "This is a sample social media post for testing",
            "platform": "twitter",
            "user_id": "demo_user_123",
            "timestamp": datetime.utcnow(),
            "metrics": {
                "likes": 42,
                "shares": 15,
                "comments": 8
            },
            "analysis_results": {
                "sentiment": "neutral",
                "confidence": 0.75,
                "risk_score": 0.3
            }
        }
        
        post_id = await mongodb.insert_post(post_data)
        print(f"✓ Inserted post with ID: {post_id}")
        
        # Find posts by sentiment
        neutral_posts = await mongodb.find_posts_by_sentiment("neutral", limit=5)
        print(f"✓ Found {len(neutral_posts)} neutral posts")
        
        # Insert user profile
        user_data = {
            "platform": "twitter",
            "user_id": "demo_user_123",
            "username": "demo_user",
            "follower_count": 1500,
            "following_count": 300,
            "bot_probability": 0.1
        }
        
        user_profile_id = await mongodb.insert_user_profile(user_data)
        print(f"✓ Inserted user profile with ID: {user_profile_id}")
        
    except Exception as e:
        print(f"✗ MongoDB operation failed: {e}")


async def demonstrate_postgresql_operations(db_manager: DatabaseManager):
    """Demonstrate PostgreSQL operations."""
    print("\n=== PostgreSQL Operations ===")
    
    try:
        postgresql = db_manager.get_postgresql()
        
        # Create a user
        user_data = {
            "username": "demo_analyst",
            "email": "demo@example.com",
            "role": "analyst",
            "password_hash": "hashed_password_here"
        }
        
        user_id = await postgresql.create_user(user_data)
        if user_id:
            print(f"✓ Created user with ID: {user_id}")
            
            # Create an alert
            alert_data = {
                "type": "high_risk_content",
                "severity": "medium",
                "title": "Suspicious Activity Detected",
                "description": "Multiple posts from the same user with similar content patterns",
                "metadata": {"user_id": "demo_user_123", "post_count": 5}
            }
            
            alert_id = await postgresql.create_alert(alert_data)
            if alert_id:
                print(f"✓ Created alert with ID: {alert_id}")
                
                # Acknowledge the alert
                acknowledged = await postgresql.acknowledge_alert(alert_id, user_id)
                if acknowledged:
                    print("✓ Alert acknowledged successfully")
                
                # Log user action
                logged = await postgresql.log_user_action(
                    user_id, 
                    "acknowledge_alert", 
                    "alert", 
                    str(alert_id),
                    {"alert_type": alert_data["type"]}
                )
                if logged:
                    print("✓ User action logged successfully")
        
    except Exception as e:
        print(f"✗ PostgreSQL operation failed: {e}")


async def demonstrate_redis_operations(db_manager: DatabaseManager):
    """Demonstrate Redis operations."""
    print("\n=== Redis Operations ===")
    
    try:
        redis = db_manager.get_redis()
        
        # Cache some analysis results
        cache_data = {
            "sentiment": "positive",
            "confidence": 0.92,
            "processed_at": datetime.utcnow().isoformat(),
            "model_version": "v1.2.3"
        }
        
        cached = await redis.set("analysis:demo_post_123", cache_data, expire=3600)
        if cached:
            print("✓ Cached analysis results")
            
            # Retrieve cached data
            retrieved = await redis.get("analysis:demo_post_123")
            if retrieved:
                print(f"✓ Retrieved cached data: {retrieved['sentiment']}")
        
        # Use Redis for rate limiting
        user_key = "rate_limit:demo_user_123"
        current_count = await redis.incr(user_key)
        await redis.expire(user_key, 3600)  # 1 hour window
        
        print(f"✓ User request count: {current_count}")
        
        # Use Redis for pub/sub messaging
        message = {
            "event": "new_alert",
            "alert_id": 123,
            "severity": "high",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        published = await redis.publish("alerts", message)
        print(f"✓ Published message to {published} subscribers")
        
    except Exception as e:
        print(f"✗ Redis operation failed: {e}")


async def demonstrate_elasticsearch_operations(db_manager: DatabaseManager):
    """Demonstrate Elasticsearch operations."""
    print("\n=== Elasticsearch Operations ===")
    
    try:
        elasticsearch = db_manager.get_elasticsearch()
        
        # Index a document for search
        search_doc = {
            "content": "This is a sample post about artificial intelligence and machine learning",
            "platform": "twitter",
            "user_id": "demo_user_123",
            "timestamp": datetime.utcnow().isoformat(),
            "sentiment": "positive",
            "risk_score": 0.2,
            "tags": ["AI", "ML", "technology"]
        }
        
        doc_id = await elasticsearch.index_document("posts", search_doc, "demo_post_456")
        if doc_id:
            print(f"✓ Indexed document with ID: {doc_id}")
            
            # Search for documents
            search_query = {
                "bool": {
                    "must": [
                        {"match": {"content": "artificial intelligence"}},
                        {"term": {"sentiment": "positive"}}
                    ]
                }
            }
            
            search_results = await elasticsearch.search("posts", search_query, size=10)
            hit_count = search_results["hits"]["total"]["value"]
            print(f"✓ Found {hit_count} matching documents")
            
            # Perform aggregation
            agg_query = {
                "sentiment_distribution": {
                    "terms": {
                        "field": "sentiment"
                    }
                }
            }
            
            agg_results = await elasticsearch.aggregate("posts", agg_query)
            if "sentiment_distribution" in agg_results:
                print("✓ Sentiment distribution aggregation completed")
        
    except Exception as e:
        print(f"✗ Elasticsearch operation failed: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 Database Connection Utilities Demo")
    print("=" * 50)
    
    # Initialize settings
    settings = Settings()
    
    # For demo purposes, we'll use default local connection strings
    # In production, these would come from environment variables
    settings.database.mongodb_url = "mongodb://localhost:27017"
    settings.database.mongodb_database = "dharma_demo"
    settings.database.postgresql_url = "postgresql://localhost:5432/dharma_demo"
    settings.database.elasticsearch_url = "http://localhost:9200"
    settings.redis.url = "redis://localhost:6379"
    
    try:
        # Get database manager (this will attempt to connect to all databases)
        print("Initializing database connections...")
        db_manager = await get_database_manager(settings)
        
        # Check health of all connections
        print("\nChecking database health...")
        health_status = await db_manager.health_check()
        
        for db_name, is_healthy in health_status.items():
            status = "✓ Healthy" if is_healthy else "✗ Unhealthy"
            print(f"{db_name.capitalize()}: {status}")
        
        # Get connection info
        print("\nConnection Information:")
        conn_info = await db_manager.get_connection_info()
        print(f"Overall connected: {conn_info['connected']}")
        
        for db_name, db_info in conn_info["databases"].items():
            print(f"{db_name.capitalize()}: Connected = {db_info['connected']}")
        
        # Demonstrate operations for each database
        # Note: These will only work if the respective databases are running
        
        if health_status.get("mongodb", False):
            await demonstrate_mongodb_operations(db_manager)
        else:
            print("\n⚠️  Skipping MongoDB demo - database not available")
        
        if health_status.get("postgresql", False):
            await demonstrate_postgresql_operations(db_manager)
        else:
            print("\n⚠️  Skipping PostgreSQL demo - database not available")
        
        if health_status.get("redis", False):
            await demonstrate_redis_operations(db_manager)
        else:
            print("\n⚠️  Skipping Redis demo - database not available")
        
        if health_status.get("elasticsearch", False):
            await demonstrate_elasticsearch_operations(db_manager)
        else:
            print("\n⚠️  Skipping Elasticsearch demo - database not available")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    finally:
        # Clean up connections
        print("\n🧹 Cleaning up database connections...")
        await close_database_manager()
        print("✓ All connections closed")
    
    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())