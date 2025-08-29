# Event Bus Service

Handles cross-service communication and workflow orchestration.

## Features

- Event-driven architecture with Kafka
- Workflow orchestration with Temporal
- Message routing and transformation
- Dead letter queue handling

## Topics

- `data.collected` - New data ingested
- `analysis.completed` - Analysis results ready
- `campaign.detected` - New campaign identified
- `alert.triggered` - Alert generated