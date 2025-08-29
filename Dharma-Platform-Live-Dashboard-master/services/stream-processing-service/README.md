# Stream Processing Service

Real-time data processing service for Project Dharma.

## Features

- Kafka stream processing for real-time data
- Parallel processing workers for AI analysis
- Load balancing and auto-scaling
- Dead letter queues for failed processing

## API Endpoints

- `GET /health` - Health check
- `GET /metrics` - Processing metrics
- `POST /process` - Manual processing trigger

## Configuration

Set environment variables:
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka connection
- `KAFKA_TOPIC_PREFIX` - Topic prefix
- `KAFKA_CONSUMER_GROUP` - Consumer group name

## Usage

```bash
# Start service
python main.py

# Or with Docker
docker build -t stream-processing-service .
docker run -p 8002:8002 stream-processing-service
```