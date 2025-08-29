# Multi-Channel Notification Service

The Multi-Channel Notification Service is a comprehensive system for delivering alert notifications through multiple channels including SMS, Email, Webhooks, and Dashboard real-time notifications.

## Features

### 🔔 SMS Notifications (Twilio)
- **Provider**: Twilio API integration
- **Features**:
  - E.164 phone number validation
  - Message length optimization (160 character limit)
  - Delivery status tracking
  - Rate limiting to prevent spam
  - Exponential backoff retry logic
  - Template-based message formatting

### 📧 Email Notifications
- **Provider**: SMTP with HTML templates
- **Features**:
  - HTML and plain text email support
  - Rich email templates with severity-based styling
  - Email address validation
  - Priority headers for high-severity alerts
  - Content samples and metrics inclusion
  - Responsive email design

### 🔗 Webhook Notifications
- **Provider**: HTTP/HTTPS webhooks
- **Features**:
  - JSON payload delivery to external systems
  - Retry logic with exponential backoff
  - Security headers and HMAC signatures
  - Domain allowlist support
  - Dead letter queue for failed deliveries
  - Comprehensive error tracking

### 📊 Dashboard Real-time Notifications
- **Provider**: WebSocket connections
- **Features**:
  - Real-time browser notifications
  - User-specific and broadcast messaging
  - Connection management and cleanup
  - Notification history and replay
  - Auto-dismiss based on severity
  - WebSocket heartbeat and reconnection

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 NotificationService                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ SMS Provider│  │Email Provider│  │Webhook Prov.│  ...    │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │Delivery Queue│  │Retry Queue  │  │Template Eng.│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

```bash
# Twilio SMS Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# SMTP Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=alerts@dharma.gov

# WebSocket Configuration
WEBSOCKET_PORT=8765
WEBSOCKET_HOST=0.0.0.0

# Dashboard Configuration
DASHBOARD_BASE_URL=https://dharma.gov

# Webhook Configuration
WEBHOOK_SIGNING_SECRET=your_secret_key
WEBHOOK_ALLOWED_DOMAINS=["trusted-domain.gov", "partner-system.org"]
WEBHOOK_TIMEOUT_SECONDS=30
WEBHOOK_MAX_RETRIES=3
```

## Usage

### Basic Usage

```python
from app.notifications.notification_service import NotificationService
from shared.models.alert import Alert, NotificationChannel

# Initialize service
service = NotificationService()

# Define recipients
recipients = [
    {
        "recipient": "+1234567890",
        "channels": [NotificationChannel.SMS]
    },
    {
        "recipient": "admin@dharma.gov",
        "channels": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD]
    },
    {
        "recipient": "https://external-system.gov/webhooks/alerts",
        "channels": [NotificationChannel.WEBHOOK]
    }
]

# Send notifications
records = await service.send_alert_notifications(alert, recipients)

# Check status
for record in records:
    print(f"Notification {record.notification_id}: {record.status}")
```

### Multi-Channel Notifications

```python
# Send to multiple channels for same recipient
recipients = [
    {
        "recipient": "admin@dharma.gov",
        "channels": [
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.DASHBOARD
        ]
    }
]

records = await service.send_alert_notifications(alert, recipients)
```

### Notification Preferences

```python
from app.notifications.notification_service import NotificationPreferenceManager

preference_manager = NotificationPreferenceManager()

# Set user preferences
preferences = {
    "channels": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
    "severity_threshold": SeverityLevel.MEDIUM,
    "quiet_hours": {"start": "22:00", "end": "08:00"},
    "timezone": "Asia/Kolkata"
}

await preference_manager.update_user_preferences("user123", preferences)

# Get recipients based on alert and preferences
recipients = await preference_manager.get_recipients_for_alert(alert)
```

## Templates

### SMS Templates

SMS messages are automatically formatted based on severity:

- **Critical**: 🚨 CRITICAL: {title} - {platform} - Confidence: {confidence_score:.0%} - {dashboard_url}
- **High**: ⚠️ HIGH: {title} - {platform} - {dashboard_url}
- **Medium**: 📢 MEDIUM: {title} - {dashboard_url}
- **Low**: ℹ️ {title} - {dashboard_url}

### Email Templates

Email templates support both HTML and plain text formats with:
- Severity-based color coding
- Rich content including samples and metrics
- Responsive design for mobile devices
- Call-to-action buttons

### Webhook Payloads

```json
{
  "event": "alert.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "source": "project-dharma",
  "version": "1.0",
  "alert": {
    "id": "alert_123",
    "title": "High Risk Content Detected",
    "severity": "high",
    "type": "high_risk_content",
    "context": {
      "platform": "twitter",
      "confidence_score": 0.85,
      "risk_score": 0.75,
      "affected_regions": ["Delhi", "Mumbai"]
    }
  }
}
```

## Monitoring and Statistics

### Service Statistics

```python
stats = await service.get_notification_stats()
print(f"Total notifications: {stats['total_notifications']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"By status: {stats['by_status']}")
print(f"By channel: {stats['by_channel']}")
```

### Provider Statistics

```python
for channel, provider in service.providers.items():
    stats = await provider.get_provider_stats()
    print(f"{channel.value}: {stats}")
```

## Error Handling and Retry Logic

### Retry Strategy
- **Exponential Backoff**: 2^attempt seconds delay
- **Max Retries**: 3 attempts per notification
- **Dead Letter Queue**: Failed notifications after max retries

### Error Types
- **Validation Errors**: Invalid recipient format
- **Network Errors**: Connection timeouts, DNS failures
- **Service Errors**: Provider API errors (Twilio, SMTP)
- **Rate Limiting**: Provider rate limits exceeded

## Security Features

### Webhook Security
- **HMAC Signatures**: SHA-256 signatures for payload verification
- **Domain Allowlist**: Restrict webhooks to trusted domains
- **Timestamp Validation**: Prevent replay attacks
- **TLS Encryption**: HTTPS-only webhook delivery

### Data Protection
- **PII Handling**: Automatic sanitization of sensitive data
- **Audit Logging**: Complete notification audit trail
- **Access Control**: Role-based notification permissions

## Testing

### Unit Tests
```bash
cd project-dharma/services/alert-management-service
python -m pytest test_notification_service.py -v
```

### Integration Demo
```bash
python demo_notification_service.py
```

### Provider Testing
```python
# Test individual providers
sms_provider = SMSProvider()
result = await sms_provider.send_notification(alert, "+1234567890", template_data)

webhook_provider = WebhookProvider()
test_result = await webhook_provider.send_test_webhook("https://example.com/webhook")
```

## Performance Considerations

### Scalability
- **Async Processing**: Non-blocking notification delivery
- **Queue Management**: Separate delivery and retry queues
- **Connection Pooling**: Efficient resource utilization
- **Background Workers**: Parallel notification processing

### Rate Limiting
- **SMS**: 10 per hour, 50 per day per recipient
- **Email**: Configurable SMTP rate limits
- **Webhooks**: Exponential backoff on failures
- **Dashboard**: Connection-based limits

## Troubleshooting

### Common Issues

1. **SMS Not Sending**
   - Check Twilio credentials
   - Verify phone number format (E.164)
   - Check account balance and limits

2. **Email Delivery Issues**
   - Verify SMTP configuration
   - Check firewall/port access
   - Validate email addresses

3. **Webhook Failures**
   - Check endpoint availability
   - Verify SSL certificates
   - Review webhook logs

4. **Dashboard Notifications**
   - Check WebSocket connection
   - Verify client authentication
   - Monitor connection cleanup

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger("app.notifications").setLevel(logging.DEBUG)
```

Check notification records:
```python
record = await service.get_notification_status("notification_id")
print(f"Status: {record.status}")
print(f"Error: {record.error_message}")
print(f"Metadata: {record.metadata}")
```

## Future Enhancements

- **Push Notifications**: Mobile app integration
- **Slack/Teams**: Chat platform notifications
- **Voice Calls**: Critical alert voice notifications
- **Message Queuing**: Kafka/RabbitMQ integration
- **Analytics**: Advanced notification analytics
- **A/B Testing**: Template effectiveness testing