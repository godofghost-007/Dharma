# Alert Management Service

Manages alert generation, routing, and escalation with multi-channel notifications.

## Features

- Real-time alert generation
- Multi-channel notifications (SMS, email, dashboard)
- Alert deduplication and correlation
- Escalation workflows

## API Endpoints

- `POST /alerts` - Create new alert
- `GET /alerts` - List alerts with filtering
- `PUT /alerts/{id}/acknowledge` - Acknowledge alert
- `POST /alerts/{id}/escalate` - Escalate alert