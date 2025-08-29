# Data Ingestion Pipeline

This document describes the data ingestion pipeline implementation for Project Dharma's data collection service.

## Overview

The data ingestion pipeline provides comprehensive data processing capabilities including:

- **Streaming Data Processing**: Real-time processing of social media data
- **Batch Data Processing**: Historical data processing with job management
- **Data Validation**: Comprehensive validation and preprocessing
- **Monitoring & Alerting**: System health monitoring and alerting
- **Duplicate Detection**: Content deduplication using Redis
- **Error Handling**: Robust error handling and retry mechanisms

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Data Pipeline   │───▶│   Kafka Topics  │
│                 │    │                  │    │                 │
│ • Twitter/X     │    │ • Validation     │    │ • Raw Data      │
│ • YouTube       │    │ • Preprocessing  │    │ • Processed     │
│ • Telegram      │    │ • Deduplication  │    │ • Failed        │
│ • Web Scraping  │    │ • Monitoring     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │    MongoDB      │
                       │   (Persistence) │
                       └─────────────────┘
```

## Components

### 1. DataIngestionPipeline

Main pipeline class that orchestrates data processing:

```python
from app.core.data_pipeline import get_pipeline

pipeline = await get_pipeline()

# Process streaming data
success = await pipeline.process_streaming_data(
    Platform.TWITTER, 
    data, 
    collection_id
)

# Process batch data
metrics = await pipeline.process_batch_data(
    Platform.TWITTER, 
    data_batch, 
    collection_id
)
```

### 2. DataValidator

Validates and preprocesses data according to platform-specific rules:

- **Field Validation**: Ensures required fields are present
- **Content Cleaning**: Normalizes and cleans text content
- **Hashtag/Mention Extraction**: Extracts social media entities
- **Platform-specific Processing**: Handles platform differences

### 3. DuplicateDetector

Prevents duplicate content processing using Redis:

- **Content Hashing**: SHA-256 hashing for content deduplication
- **Post ID Tracking**: Tracks processed post IDs
- **TTL Management**: Automatic cleanup of old entries

### 4. BatchProcessor

Handles historical data processing:

```python
from app.core.batch_processor import get_batch_processor

batch_processor = await get_batch_processor()

# Submit batch job
job_id = await batch_processor.submit_batch_job(
    Platform.TWITTER,
    "file:///path/to/data.json",
    collection_id
)

# Check job status
job = await batch_processor.get_job_status(job_id)
```

### 5. DataCollectionMonitor

Comprehensive monitoring and alerting:

```python
from app.core.monitoring import get_monitor

monitor = await get_monitor()

# Record metrics
await monitor.record_collection_event(Platform.TWITTER, "collection_start", True, 1.5)
await monitor.record_processing_metrics(Platform.TWITTER, 100, 5, 10)

# Get system health
health = await monitor.get_system_health()
```

## API Endpoints

### Data Processing

- `POST /pipeline/process` - Process data directly through pipeline
- `GET /pipeline/status/{collection_id}` - Get processing status

### Batch Processing

- `POST /batch/submit` - Submit batch processing job
- `GET /batch/status/{job_id}` - Get batch job status
- `POST /batch/cancel/{job_id}` - Cancel batch job

### Monitoring

- `GET /monitoring/metrics` - Get system metrics
- `GET /monitoring/alerts` - Get active alerts
- `POST /monitoring/alerts/{alert_id}/resolve` - Resolve alert

## Data Flow

### Streaming Data Flow

1. **Data Collection**: Collectors gather data from social media APIs
2. **Pipeline Processing**: Data flows through validation and preprocessing
3. **Duplicate Check**: Redis-based duplicate detection
4. **Kafka Publishing**: Validated data sent to Kafka topics
5. **MongoDB Storage**: Data persisted for analysis
6. **Monitoring**: Metrics and alerts generated

### Batch Data Flow

1. **Job Submission**: Batch job submitted with data source
2. **Data Loading**: Data loaded from file or API export
3. **Chunk Processing**: Data processed in manageable chunks
4. **Pipeline Integration**: Each item processed through main pipeline
5. **Progress Tracking**: Job status and metrics updated
6. **Completion**: Final metrics and status reported

## Configuration

### Environment Variables

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=dharma

# Database Configuration
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379

# Monitoring
LOG_LEVEL=INFO
```

### Pipeline Settings

```python
# Data validation settings
REQUIRED_FIELDS = {
    Platform.TWITTER: ["post_id", "user_id", "content", "timestamp"],
    Platform.YOUTUBE: ["post_id", "user_id", "content", "timestamp"],
    # ...
}

# Processing limits
MAX_CONTENT_LENGTH = 10000
BATCH_CHUNK_SIZE = 100
DUPLICATE_TTL = 86400 * 7  # 7 days
```

## Monitoring & Alerting

### Metrics Collected

- **Collection Events**: Success/failure rates by platform
- **Processing Metrics**: Items processed, failed, duplicated
- **Kafka Metrics**: Message send success/failure, latency
- **Database Metrics**: Operation success/failure, duration
- **System Health**: Overall health score and status

### Default Alert Rules

- **High Error Rate**: >10% failure rate triggers warning
- **Kafka Issues**: Multiple send failures trigger error alert
- **No Activity**: No collection events in 5 minutes triggers warning

### Health Scoring

System health calculated based on:
- Active alerts (critical: -0.3, error: -0.2, warning: -0.1)
- Error rates (high error rate: -0.5)
- Overall score: 0.0 (unhealthy) to 1.0 (healthy)

## Error Handling

### Validation Errors

- **Missing Fields**: ValidationError with specific field names
- **Invalid Content**: Content cleaning and normalization
- **Type Errors**: Automatic type conversion where possible

### Processing Errors

- **Kafka Failures**: Retry with exponential backoff
- **Database Errors**: Transaction rollback and retry
- **Network Issues**: Circuit breaker pattern

### Monitoring Errors

- **Metric Collection**: Buffered metrics with periodic flush
- **Alert Processing**: Error isolation per alert rule
- **Health Checks**: Graceful degradation on component failure

## Performance Optimization

### Streaming Performance

- **Async Processing**: Non-blocking I/O operations
- **Connection Pooling**: Reused database connections
- **Batch Operations**: Grouped database writes
- **Caching**: Redis caching for frequently accessed data

### Batch Performance

- **Chunk Processing**: Large datasets processed in chunks
- **Parallel Processing**: Concurrent processing of chunks
- **Memory Management**: Streaming data loading
- **Progress Tracking**: Efficient status updates

## Testing

Run the test suite:

```bash
cd project-dharma/services/data-collection-service
python test_pipeline.py
```

Test coverage includes:
- Data validation with valid/invalid data
- Streaming data processing
- Batch job submission and processing
- Monitoring metrics and alerts
- Error handling scenarios

## Deployment

### Docker Deployment

```bash
# Build the service
docker build -t dharma-data-collection .

# Run with dependencies
docker-compose up data-collection-service
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-collection-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-collection-service
  template:
    metadata:
      labels:
        app: data-collection-service
    spec:
      containers:
      - name: data-collection
        image: dharma-data-collection:latest
        ports:
        - containerPort: 8000
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka:9092"
        - name: MONGODB_URL
          value: "mongodb://mongodb:27017"
        - name: REDIS_URL
          value: "redis://redis:6379"
```

## Troubleshooting

### Common Issues

1. **Kafka Connection Failures**
   - Check Kafka broker availability
   - Verify network connectivity
   - Review authentication credentials

2. **High Memory Usage**
   - Reduce batch chunk size
   - Check for memory leaks in collectors
   - Monitor Redis memory usage

3. **Validation Errors**
   - Review data format requirements
   - Check platform-specific field mappings
   - Verify timestamp formats

4. **Performance Issues**
   - Monitor database connection pools
   - Check Redis cache hit rates
   - Review Kafka partition distribution

### Debugging

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
```

Monitor system health:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/monitoring/metrics
curl http://localhost:8000/monitoring/alerts
```

## Future Enhancements

- **Stream Processing**: Apache Kafka Streams integration
- **Machine Learning**: Real-time ML model inference
- **Data Quality**: Advanced data quality scoring
- **Multi-tenancy**: Support for multiple organizations
- **Advanced Analytics**: Real-time analytics dashboard