# Distributed Tracing System for Project Dharma

This directory contains the comprehensive distributed tracing implementation for Project Dharma, providing request correlation, error tracking, performance profiling, and bottleneck identification across all microservices.

## Overview

The distributed tracing system consists of several integrated components:

- **Distributed Tracing**: OpenTelemetry-based tracing with Jaeger backend
- **Correlation Management**: Request correlation across microservices
- **Error Tracking**: Advanced error collection, aggregation, and alerting
- **Performance Profiling**: Real-time performance monitoring and bottleneck detection
- **Integration Utilities**: Middleware and decorators for seamless integration

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Service A     │    │   Service B     │    │   Service C     │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │  Tracer     │ │    │ │  Tracer     │ │    │ │  Tracer     │ │
│ │  Correlator │ │    │ │  Correlator │ │    │ │  Correlator │ │
│ │  Profiler   │ │    │ │  Profiler   │ │    │ │  Profiler   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────▼───────────────────────┐
         │            Tracing Infrastructure             │
         │                                               │
         │  ┌─────────┐  ┌─────────┐  ┌─────────────┐   │
         │  │ Jaeger  │  │  Redis  │  │Elasticsearch│   │
         │  └─────────┘  └─────────┘  └─────────────┘   │
         └───────────────────────────────────────────────┘
```

## Components

### 1. Distributed Tracer (`tracer.py`)

The main tracing component using OpenTelemetry with Jaeger backend.

**Features:**
- Automatic instrumentation for HTTP, database, and message queue operations
- Custom span creation and management
- Trace and span ID generation
- Context propagation across service boundaries
- Integration with correlation IDs

**Usage:**
```python
from shared.tracing.tracer import get_tracer

tracer = get_tracer("my-service")

# Context manager
with tracer.trace_operation("my_operation") as span:
    span.set_attribute("custom.attribute", "value")
    # Your code here

# Decorator
@tracer.trace_function("my_function")
def my_function():
    return "result"
```

### 2. Correlation Manager (`correlation.py`)

Manages correlation IDs and request context across microservices.

**Features:**
- Automatic correlation ID generation and propagation
- Request chain tracking
- Context storage in Redis
- HTTP header-based propagation
- FastAPI middleware integration

**Usage:**
```python
from shared.tracing.correlation import get_correlation_manager, CorrelationContextManager

manager = get_correlation_manager()

# Context manager
async with CorrelationContextManager(
    manager, 
    user_id="user123",
    service_name="my-service"
) as context:
    # Your code here with correlation context
    pass
```

### 3. Error Tracker (`error_tracker.py`)

Advanced error tracking with aggregation, classification, and alerting.

**Features:**
- Automatic error fingerprinting and aggregation
- Error severity and category classification
- Real-time error rate monitoring
- Alert generation based on configurable rules
- Storage in Elasticsearch with Redis caching

**Usage:**
```python
from shared.tracing.error_tracker import get_error_tracker, ErrorSeverity, ErrorCategory

tracker = get_error_tracker("my-service")

try:
    # Your code here
    pass
except Exception as e:
    tracker.track_error(
        e,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.APPLICATION,
        context={"user_id": "user123"}
    )
```

### 4. Performance Profiler (`performance_profiler.py`)

Real-time performance monitoring with bottleneck identification.

**Features:**
- Operation-level performance profiling
- System resource monitoring (CPU, memory, I/O)
- Bottleneck detection with severity classification
- cProfile integration for detailed function profiling
- Performance trend analysis

**Usage:**
```python
from shared.tracing.performance_profiler import get_profiler

profiler = get_profiler()

# Context manager
with profiler.profile_operation("my_operation", enable_cprofile=True):
    # Your code here
    pass

# Decorator
@profiler.profile_function("my_function")
def my_function():
    return "result"
```

### 5. Integration Utilities (`integration.py`)

Middleware and utilities for seamless integration with FastAPI and other frameworks.

**Features:**
- FastAPI middleware for automatic tracing
- Traced HTTP client for service-to-service calls
- Traced Kafka producer/consumer
- Database and AI operation decorators
- One-line service setup

**Usage:**
```python
from fastapi import FastAPI
from shared.tracing.integration import setup_service_tracing

app = FastAPI()

# One-line setup
components = setup_service_tracing(app, "my-service")

# Manual middleware
from shared.tracing.integration import TracingMiddleware
app.add_middleware(TracingMiddleware, "my-service")
```

### 6. Configuration (`config.py`)

Centralized configuration management for all tracing components.

**Features:**
- Environment-based configuration
- Service-specific settings
- Performance tuning parameters
- Backend configuration (Jaeger, Redis, Elasticsearch)

**Usage:**
```python
from shared.tracing.config import get_tracing_config

config = get_tracing_config("my-service")
```

## Infrastructure Setup

### 1. Start Tracing Infrastructure

```bash
# Start Jaeger and related services
cd project-dharma/infrastructure/tracing
docker-compose -f jaeger-config.yml up -d

# Start monitoring stack (includes Jaeger)
cd project-dharma/infrastructure/monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Environment Variables

Set the following environment variables for your services:

```bash
# Service identification
export SERVICE_NAME="my-service"
export SERVICE_VERSION="1.0.0"
export ENVIRONMENT="development"

# Jaeger configuration
export JAEGER_ENDPOINT="http://localhost:14268/api/traces"
export JAEGER_AGENT_HOST="localhost"
export JAEGER_AGENT_PORT="6831"

# Redis configuration
export CORRELATION_REDIS_URL="redis://localhost:6379"
export ERROR_REDIS_URL="redis://localhost:6379"
export PERFORMANCE_REDIS_URL="redis://localhost:6379"

# Elasticsearch configuration
export ERROR_ELASTICSEARCH_URL="http://localhost:9200"

# Kafka configuration
export ERROR_KAFKA_BOOTSTRAP_SERVERS="localhost:9092"

# Sampling configuration
export SAMPLING_STRATEGY="always_on"
export SAMPLING_RATE="1.0"

# Feature flags
export ENABLE_AUTO_INSTRUMENTATION="true"
export ENABLE_SYSTEM_MONITORING="true"
export ENABLE_CPROFILE="false"
```

## Service Integration

### FastAPI Service Integration

```python
from fastapi import FastAPI
from shared.tracing.integration import setup_service_tracing

app = FastAPI(title="My Service")

# Setup tracing (one line!)
tracing_components = setup_service_tracing(
    app, 
    service_name="my-service",
    enable_profiling=True,
    enable_error_tracking=True
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/process")
async def process_data(data: dict):
    # Automatically traced with correlation IDs
    # Errors automatically tracked
    # Performance automatically profiled
    return {"result": "processed"}
```

### Database Operations

```python
from shared.tracing.integration import trace_database_operation

@trace_database_operation("user_query", "postgresql")
async def get_user(user_id: str):
    # Database operation automatically traced
    return await db.fetch_user(user_id)
```

### AI/ML Operations

```python
from shared.tracing.integration import trace_ai_operation

@trace_ai_operation("sentiment-model", "inference")
async def analyze_sentiment(text: str):
    # AI operation automatically traced and profiled
    return await model.predict(text)
```

### Service-to-Service Calls

```python
from shared.tracing.integration import TracedHTTPClient

async with TracedHTTPClient("my-service", "http://other-service:8000") as client:
    # HTTP calls automatically traced with correlation propagation
    response = await client.post("/api/process", json={"data": "value"})
    return response.json()
```

### Message Queue Operations

```python
from shared.tracing.integration import TracedKafkaProducer, TracedKafkaConsumer

# Producer
producer = TracedKafkaProducer("my-service", bootstrap_servers="localhost:9092")
producer.send("my-topic", {"message": "data"})

# Consumer
consumer = TracedKafkaConsumer("my-service", ["my-topic"], bootstrap_servers="localhost:9092")
for message in consumer:
    # Message processing automatically traced
    process_message(message.value)
```

## Monitoring and Observability

### 1. Jaeger UI

Access the Jaeger UI at `http://localhost:16686` to:
- View distributed traces
- Analyze request flows across services
- Identify performance bottlenecks
- Debug service interactions

### 2. Performance Metrics

```python
from shared.tracing.performance_profiler import get_profiler

profiler = get_profiler()

# Get performance summary
summary = await profiler.get_performance_summary("my_operation")
print(f"Average duration: {summary['duration']['avg']:.2f}s")
print(f"95th percentile: {summary['duration']['p95']:.2f}s")

# Get recent bottlenecks
bottlenecks = await profiler.get_recent_bottlenecks()
for bottleneck in bottlenecks:
    print(f"Bottleneck: {bottleneck['description']}")
```

### 3. Error Tracking

```python
from shared.tracing.error_tracker import get_error_tracker

tracker = get_error_tracker("my-service")

# Get error summary
summary = await tracker.get_error_summary()
print(f"Total errors: {summary['total_errors']}")
print(f"Error rate: {summary['by_severity']}")
```

### 4. Correlation Tracking

```python
from shared.tracing.correlation import get_correlation_manager

manager = get_correlation_manager()

# Get request chain
chain = await manager.get_request_chain("correlation-id-123")
for entry in chain:
    print(f"Service: {entry['service']}, Operation: {entry['operation']}")
```

## Best Practices

### 1. Span Naming

Use consistent, hierarchical span names:
```python
# Good
"http.GET./api/users/{id}"
"db.postgresql.select_user"
"ai.sentiment_model.inference"

# Bad
"get_user"
"database_call"
"ai_stuff"
```

### 2. Attributes

Add meaningful attributes to spans:
```python
span.set_attribute("user.id", user_id)
span.set_attribute("http.status_code", 200)
span.set_attribute("db.rows_affected", 1)
span.set_attribute("ai.model.confidence", 0.95)
```

### 3. Error Handling

Always track errors with appropriate context:
```python
try:
    result = await process_data(data)
except ValidationError as e:
    tracker.track_error(
        e,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.BUSINESS_LOGIC,
        context={"data_type": type(data).__name__}
    )
    raise
```

### 4. Performance Profiling

Profile critical operations:
```python
@profiler.profile_function("critical_operation", enable_cprofile=True)
async def critical_operation():
    # Critical code that needs detailed profiling
    pass
```

### 5. Correlation Context

Always maintain correlation context in async operations:
```python
async def background_task():
    # Get current correlation context
    context = correlation_manager.get_correlation_context()
    
    # Use context in background processing
    if context:
        correlation_manager.set_correlation_context(context)
```

## Troubleshooting

### Common Issues

1. **Missing Traces**: Check Jaeger endpoint configuration and network connectivity
2. **High Memory Usage**: Adjust batch processor settings and memory limits
3. **Performance Impact**: Reduce sampling rate or disable detailed profiling
4. **Redis Connection Issues**: Verify Redis URL and network access
5. **Elasticsearch Errors**: Check Elasticsearch cluster health and permissions

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("shared.tracing").setLevel(logging.DEBUG)
```

### Health Checks

Check component health:
```python
# Check if tracing is working
trace_id = tracer.get_trace_id()
print(f"Current trace ID: {trace_id}")

# Check correlation context
correlation_id = get_correlation_id()
print(f"Current correlation ID: {correlation_id}")
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tracing tests
python -m pytest tests/test_distributed_tracing.py -v

# Run specific test categories
python -m pytest tests/test_distributed_tracing.py::TestDharmaTracer -v
python -m pytest tests/test_distributed_tracing.py::TestCorrelationManager -v
python -m pytest tests/test_distributed_tracing.py::TestErrorTracker -v
python -m pytest tests/test_distributed_tracing.py::TestPerformanceProfiler -v

# Run integration tests
python -m pytest tests/test_distributed_tracing.py::TestDistributedTracingIntegration -v
```

## Performance Considerations

### Sampling

In production, use appropriate sampling rates:
```bash
export SAMPLING_STRATEGY="probabilistic"
export SAMPLING_RATE="0.1"  # 10% sampling
```

### Batch Processing

Tune batch processor settings for your load:
```bash
export BATCH_SPAN_PROCESSOR_MAX_QUEUE_SIZE="4096"
export BATCH_SPAN_PROCESSOR_SCHEDULE_DELAY_MILLIS="2000"
export BATCH_SPAN_PROCESSOR_MAX_EXPORT_BATCH_SIZE="1024"
```

### Memory Management

Set appropriate memory limits:
```bash
export MEMORY_LIMIT_MIB="1024"
```

## Security Considerations

1. **Sensitive Data**: Never include sensitive data in span attributes or logs
2. **Network Security**: Use TLS for production deployments
3. **Access Control**: Secure Jaeger UI and Elasticsearch access
4. **Data Retention**: Configure appropriate data retention policies

## Contributing

When adding new tracing functionality:

1. Follow the existing patterns and interfaces
2. Add comprehensive tests
3. Update documentation
4. Consider performance impact
5. Ensure backward compatibility

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review test cases for usage examples
3. Examine existing service integrations
4. Consult OpenTelemetry documentation for advanced features