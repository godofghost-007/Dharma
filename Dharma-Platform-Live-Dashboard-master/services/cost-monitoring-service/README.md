# Cost Monitoring Service

Resource optimization and budget tracking service for Project Dharma.

## Features

- Cloud spend tracking per component
- Budget alerts and cost optimization recommendations
- Autoscaling policies for cost-performance balance
- Detailed cost reports and trend analysis

## API Endpoints

- `GET /health` - Health check
- `GET /costs` - Get cost data
- `POST /budgets` - Create budget alert
- `GET /recommendations` - Get optimization recommendations

## Configuration

Set environment variables:
- `AWS_ACCESS_KEY_ID` - AWS credentials (optional)
- `AWS_SECRET_ACCESS_KEY` - AWS credentials (optional)
- `AZURE_SUBSCRIPTION_ID` - Azure subscription (optional)
- `GOOGLE_APPLICATION_CREDENTIALS` - GCP credentials (optional)

## Usage

```bash
# Start service
python main.py

# Or with Docker
docker build -t cost-monitoring-service .
docker run -p 8007:8007 cost-monitoring-service
```