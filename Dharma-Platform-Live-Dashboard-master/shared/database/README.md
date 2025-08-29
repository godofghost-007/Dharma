# Database Connection Utilities

This module provides comprehensive database connection utilities and ORM-like functionality for Project Dharma. It supports MongoDB, PostgreSQL, Redis, and Elasticsearch with connection pooling, error handling, and health monitoring.

## Features

- **Connection Pooling**: Efficient connection management for all databases
- **Health Monitoring**: Built-in health checks and monitoring
- **Error Handling**: Robust error handling with proper logging
- **ORM-like Operations**: High-level methods for common database operations
- **Unified Management**: Single interface to manage all database connections
- **Async Support**: Full async/await support for non-blocking operations

## Supported Databases

### MongoDB
- Document storage for posts, campaigns, and user profiles
- Automatic indexing for optimal performance
- Aggregation pipelines for analytics
- Connection pooling with Motor (async PyMongo)

### PostgreSQL
- Relational data for users, alerts, and audit logs
- Connection pooling with asyncpg
- Transaction support
- Advanced querying and reporting

### Redis
- Caching and session management
- Pub/sub messaging
- Rate limiting support
- JSON serialization/deserialization

### Elasticsearch
- Full-text search capabilities
- Document indexing and retrieval
- Aggregations and analytics
- Custom mappings and settings

## Quick Start

### Basic Usage

```python
import asyncio
from shared.database import get_database_manager
from shared.config.settings import Settings

async def main():
    # Initialize database manager
    settings = Settings()
    db_manager = await get_database_manager(settings)
    
    # Check health
    health = await db_manager.health_check()
    print(f"Database health: {health}")
    
    # Use individual databases
    mongodb = db_manager.get_mongodb()
    postgresql = db_manager.get_postgresql()
    redis = db_manager.get_redis()
    elasticsearch = db_manager.get_elasticsearch()
    
    # Perform operations...
    
    # Cleanup
    await db_manager.disconnect_all()

asyncio.run(main())
```

### Configuration

Configure database connections using environment variables or settings:

```python
from shared.config.settings import Settings

settings = Settings()
settings.database.mongodb_url = "mongodb://localhost:27017"
settings.database.mongodb_database = "dharma_platform"
settings.database.postgresql_url = "postgresql://localhost:5432/dharma"
settings.database.elasticsearch_url = "http://localhost:9200"
settings.redis.url = "redis://localhost:6379"
```

## Database Managers

### MongoDBManager

```python
# Insert post
post_data = {
    "content": "Sample post",
    "platform": "twitter",
    "user_id": "user123"
}
post_id = await mongodb.insert_post(post_data)

# Find posts by sentiment
posts = await mongodb.find_posts_by_sentiment("positive", limit=10)

# Insert user profile
user_data = {
    "platform": "twitter",
    "user_id": "user123",
    "username": "testuser"
}
await mongodb.insert_user_profile(user_data)

# Aggregate sentiment trends
trends = await mongodb.aggregate_sentiment_trends(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31)
)
```

### PostgreSQLManager

```python
# Create user
user_data = {
    "username": "analyst",
    "email": "analyst@example.com",
    "role": "analyst"
}
user_id = await postgresql.create_user(user_data)

# Create alert
alert_data = {
    "type": "high_risk_content",
    "severity": "high",
    "title": "Suspicious Activity",
    "description": "Multiple coordinated posts detected"
}
alert_id = await postgresql.create_alert(alert_data)

# Get alerts with filtering
alerts = await postgresql.get_alerts(
    status="new",
    severity="high",
    limit=50
)

# Log user action
await postgresql.log_user_action(
    user_id=1,
    action="acknowledge_alert",
    resource_type="alert",
    resource_id="123"
)
```

### RedisManager

```python
# Cache data
await redis.set("key", {"data": "value"}, expire=3600)

# Get cached data
data = await redis.get("key")

# List operations
await redis.lpush("queue", "item1", "item2")
item = await redis.rpop("queue")

# Pub/sub messaging
await redis.publish("channel", {"event": "new_alert"})

# Rate limiting
count = await redis.incr("rate_limit:user123")
await redis.expire("rate_limit:user123", 3600)
```

### ElasticsearchManager

```python
# Index document
document = {
    "content": "Sample content",
    "platform": "twitter",
    "sentiment": "positive"
}
doc_id = await elasticsearch.index_document("posts", document)

# Search documents
query = {
    "match": {
        "content": "sample"
    }
}
results = await elasticsearch.search("posts", query)

# Aggregations
agg_query = {
    "sentiment_dist": {
        "terms": {
            "field": "sentiment"
        }
    }
}
agg_results = await elasticsearch.aggregate("posts", agg_query)

# Bulk operations
documents = [
    {"content": "Post 1", "sentiment": "positive"},
    {"content": "Post 2", "sentiment": "negative"}
]
await elasticsearch.bulk_index("posts", documents)
```

## Error Handling

All database managers include comprehensive error handling:

```python
try:
    await mongodb.insert_post(post_data)
except Exception as e:
    logger.error("Failed to insert post", error=str(e))
    # Handle error appropriately
```

## Health Monitoring

Monitor database health:

```python
# Check individual database health
mongodb_healthy = await mongodb.health_check()

# Check all databases
health_status = await db_manager.health_check()
for db_name, is_healthy in health_status.items():
    print(f"{db_name}: {'✓' if is_healthy else '✗'}")
```

## Connection Management

The unified database manager handles connection lifecycle:

```python
# Automatic connection on first use
db_manager = await get_database_manager(settings)

# Manual connection management
await db_manager.connect_all()
await db_manager.disconnect_all()

# Global cleanup
await close_database_manager()
```

## Testing

The module includes comprehensive unit tests:

```bash
# Run database manager tests
python -m pytest tests/test_database_managers.py -v

# Run integration tests
python -m pytest tests/test_database_integration.py -v

# Run all database tests
python -m pytest tests/test_database_*.py -v
```

## Examples

See `examples/database_usage_example.py` for a complete demonstration of all database operations.

## Requirements

- Python 3.8+
- motor (MongoDB async driver)
- asyncpg (PostgreSQL async driver)
- redis (Redis client)
- elasticsearch (Elasticsearch client)
- structlog (Structured logging)
- pydantic (Settings management)

## Environment Variables

Configure databases using environment variables:

```bash
# MongoDB
DB_MONGODB_URL=mongodb://localhost:27017
DB_MONGODB_DATABASE=dharma_platform

# PostgreSQL
DB_POSTGRESQL_URL=postgresql://localhost:5432/dharma
DB_POSTGRESQL_POOL_SIZE=10

# Elasticsearch
DB_ELASTICSEARCH_URL=http://localhost:9200
DB_ELASTICSEARCH_INDEX_PREFIX=dharma

# Redis
REDIS_URL=redis://localhost:6379
REDIS_MAX_CONNECTIONS=20
```

## Performance Considerations

- **Connection Pooling**: All managers use connection pooling for optimal performance
- **Indexing**: MongoDB and Elasticsearch indexes are created automatically
- **Caching**: Use Redis for frequently accessed data
- **Batch Operations**: Use bulk operations for large datasets
- **Health Checks**: Regular health monitoring prevents connection issues

## Security

- **Connection Security**: Use TLS/SSL for production connections
- **Authentication**: Configure proper authentication for all databases
- **Input Validation**: All inputs are validated before database operations
- **Audit Logging**: PostgreSQL manager includes comprehensive audit logging
- **Error Handling**: Sensitive information is not exposed in error messages