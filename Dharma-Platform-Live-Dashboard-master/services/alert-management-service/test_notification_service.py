"""Tests for multi-channel notification service."""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from shared.models.alert import Alert, AlertType, SeverityLevel, AlertStatus, AlertContext, NotificationChannel
from app.notifications.notification_service import (
    NotificationService, NotificationRecord, NotificationStatus,
    NotificationTemplateEngine, NotificationPreferenceManager
)
from app.notifications.sms_provider import SMSProvider
from app.notifications.email_provider import EmailProvider
from app.notifications.webhook_provider import WebhookProvider
from app.notifications.dashboard_provider import DashboardProvider


@pytest.fixture
def sample_alert():
    """Create a sample alert for testing."""
    context = AlertContext(
        source_platform="twitter",
        detection_method="sentiment_analysis",
        confidence_score=0.85,
        risk_score=0.75,
        affected_regions=["Delhi", "Mumbai"],
        keywords_matched=["misinformation", "fake news"],
        hashtags_involved=["#fakenews", "#viral"],
        content_samples=["This is fake news about...", "Spreading false information..."],
        detection_window_start=datetime.utcnow() - timedelta(hours=1),
        detection_window_end=datetime.utcnow(),
        volume_metrics={"post_count": 150, "unique_users": 75},
        engagement_metrics={"total_likes": 500, "total_shares": 200}
    )
    
    return Alert(
        alert_id="test_alert_001",
        title="High Risk Misinformation Detected",
        description="Coordinated spread of false information detected across multiple accounts",
        alert_type=AlertType.HIGH_RISK_CONTENT,
        severity=SeverityLevel.HIGH,
        status=AlertStatus.NEW,
        context=context,
        created_at=datetime.utcnow(),
        tags=["misinformation", "coordinated"]
    )


@pytest.fixture
def notification_service():
    """Create notification service instance for testing."""
    return NotificationService()


class TestNotificationService:
    """Test cases for NotificationService."""
    
    @pytest.mark.asyncio
    async def test_notification_service_initialization(self, notification_service):
        """Test notification service initializes correctly."""
        assert notification_service is not None
        assert len(notification_service.providers) == 4
        assert NotificationChannel.SMS in notification_service.providers
        assert NotificationChannel.EMAIL in notification_service.providers
        assert NotificationChannel.WEBHOOK in notification_service.providers
        assert NotificationChannel.DASHBOARD in notification_service.providers
    
    @pytest.mark.asyncio
    async def test_send_alert_notifications(self, notification_service, sample_alert):
        """Test sending alert notifications to multiple recipients."""
        recipients = [
            {
                "recipient": "+1234567890",
                "channels": [NotificationChannel.SMS]
            },
            {
                "recipient": "test@example.com",
                "channels": [NotificationChannel.EMAIL]
            }
        ]
        
        # Mock providers
        for provider in notification_service.providers.values():
            provider.send_notification = AsyncMock(return_value=NotificationRecord(
                notification_id="test_notif",
                alert_id=sample_alert.alert_id,
                channel=provider.get_channel(),
                recipient="test_recipient",
                status=NotificationStatus.SENT
            ))
            provider.validate_recipient = AsyncMock(return_value=True)
        
        records = await notification_service.send_alert_notifications(sample_alert, recipients)
        
        assert len(records) == 2
        assert all(isinstance(record, NotificationRecord) for record in records)
    
    @pytest.mark.asyncio
    async def test_notification_record_lifecycle(self):
        """Test notification record status transitions."""
        record = NotificationRecord(
            notification_id="test_001",
            alert_id="alert_001",
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com"
        )
        
        assert record.status == NotificationStatus.PENDING
        
        record.mark_sent()
        assert record.status == NotificationStatus.SENT
        assert record.sent_at is not None
        
        record.mark_delivered()
        assert record.status == NotificationStatus.DELIVERED
        assert record.delivered_at is not None
        
        # Test failure
        record = NotificationRecord(
            notification_id="test_002",
            alert_id="alert_001",
            channel=NotificationChannel.SMS,
            recipient="+1234567890"
        )
        
        record.mark_failed("Test error")
        assert record.status == NotificationStatus.FAILED
        assert record.error_message == "Test error"
    
    @pytest.mark.asyncio
    async def test_notification_retry_logic(self):
        """Test notification retry logic."""
        record = NotificationRecord(
            notification_id="test_retry",
            alert_id="alert_001",
            channel=NotificationChannel.WEBHOOK,
            recipient="https://example.com/webhook"
        )
        
        assert record.can_retry() is True
        assert record.retry_count == 0
        
        record.increment_retry()
        assert record.retry_count == 1
        assert record.status == NotificationStatus.RETRY
        
        # Exhaust retries
        for _ in range(record.max_retries):
            record.increment_retry()
        
        assert record.can_retry() is False


class TestSMSProvider:
    """Test cases for SMS provider."""
    
    @pytest.fixture
    def sms_provider(self):
        """Create SMS provider for testing."""
        with patch('app.notifications.sms_provider.Client') as mock_client:
            provider = SMSProvider()
            provider.client = mock_client
            return provider
    
    @pytest.mark.asyncio
    async def test_validate_phone_number(self, sms_provider):
        """Test phone number validation."""
        # Valid phone numbers
        assert await sms_provider.validate_recipient("+1234567890") is True
        assert await sms_provider.validate_recipient("+919876543210") is True
        
        # Invalid phone numbers
        assert await sms_provider.validate_recipient("1234567890") is False
        assert await sms_provider.validate_recipient("invalid") is False
        assert await sms_provider.validate_recipient("") is False
    
    @pytest.mark.asyncio
    async def test_send_sms_notification(self, sms_provider, sample_alert):
        """Test sending SMS notification."""
        # Mock Twilio client
        mock_message = Mock()
        mock_message.sid = "test_sid_123"
        sms_provider.client.messages.create.return_value = mock_message
        
        template_data = {
            "sms_message": "Test alert message",
            "dashboard_url": "https://dharma.gov/alerts/test"
        }
        
        record = await sms_provider.send_notification(
            sample_alert,
            "+1234567890",
            template_data
        )
        
        assert record.status == NotificationStatus.SENT
        assert record.metadata["twilio_sid"] == "test_sid_123"
        assert record.metadata["message_body"] == "Test alert message"
    
    @pytest.mark.asyncio
    async def test_sms_length_limit(self, sms_provider, sample_alert):
        """Test SMS message length limiting."""
        # Mock Twilio client
        mock_message = Mock()
        mock_message.sid = "test_sid_123"
        sms_provider.client.messages.create.return_value = mock_message
        
        long_message = "A" * 200  # Longer than 160 characters
        template_data = {"sms_message": long_message}
        
        record = await sms_provider.send_notification(
            sample_alert,
            "+1234567890",
            template_data
        )
        
        # Check that message was truncated
        sent_message = record.metadata["message_body"]
        assert len(sent_message) <= 160
        assert sent_message.endswith("...")


class TestEmailProvider:
    """Test cases for Email provider."""
    
    @pytest.fixture
    def email_provider(self):
        """Create email provider for testing."""
        return EmailProvider()
    
    @pytest.mark.asyncio
    async def test_validate_email_address(self, email_provider):
        """Test email address validation."""
        # Valid email addresses
        assert await email_provider.validate_recipient("test@example.com") is True
        assert await email_provider.validate_recipient("user.name@domain.co.in") is True
        
        # Invalid email addresses
        assert await email_provider.validate_recipient("invalid-email") is False
        assert await email_provider.validate_recipient("@domain.com") is False
        assert await email_provider.validate_recipient("user@") is False
        assert await email_provider.validate_recipient("") is False
    
    @pytest.mark.asyncio
    async def test_email_content_generation(self, email_provider, sample_alert):
        """Test email content generation."""
        template_data = {
            "subject": "Test Alert",
            "dashboard_url": "https://dharma.gov/alerts/test"
        }
        
        # Mock SMTP sending
        with patch.object(email_provider, '_send_email', new_callable=AsyncMock):
            record = await email_provider.send_notification(
                sample_alert,
                "test@example.com",
                template_data
            )
            
            assert record.status == NotificationStatus.SENT
            assert record.metadata["subject"] == "Test Alert"
    
    @pytest.mark.asyncio
    async def test_email_template_manager(self):
        """Test email template manager."""
        from app.notifications.email_provider import EmailTemplateManager
        
        template_manager = EmailTemplateManager()
        
        # Create test alert
        context = AlertContext(
            source_platform="twitter",
            confidence_score=0.85,
            risk_score=0.75,
            affected_regions=["Delhi"],
            content_samples=["Test content"]
        )
        
        alert = Alert(
            alert_id="test_001",
            title="Test Alert",
            description="Test description",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.HIGH,
            context=context,
            created_at=datetime.utcnow()
        )
        
        template_data = {"dashboard_url": "https://test.com"}
        
        # Test HTML content generation
        html_content = await template_manager.generate_html_content(alert, template_data)
        assert "Test Alert" in html_content
        assert "Test description" in html_content
        assert "https://test.com" in html_content
        
        # Test text content generation
        text_content = await template_manager.generate_text_content(alert, template_data)
        assert "Test Alert" in text_content
        assert "Test description" in text_content


class TestWebhookProvider:
    """Test cases for Webhook provider."""
    
    @pytest.fixture
    def webhook_provider(self):
        """Create webhook provider for testing."""
        provider = WebhookProvider()
        # Mock the session initialization
        provider.session = AsyncMock()
        return provider
    
    @pytest.mark.asyncio
    async def test_validate_webhook_url(self, webhook_provider):
        """Test webhook URL validation."""
        # Valid URLs
        assert await webhook_provider.validate_recipient("https://example.com/webhook") is True
        assert await webhook_provider.validate_recipient("http://localhost:8080/alerts") is True
        
        # Invalid URLs
        assert await webhook_provider.validate_recipient("invalid-url") is False
        assert await webhook_provider.validate_recipient("ftp://example.com") is False
        assert await webhook_provider.validate_recipient("") is False
    
    @pytest.mark.asyncio
    async def test_webhook_payload_preparation(self, webhook_provider, sample_alert):
        """Test webhook payload preparation."""
        template_data = {"dashboard_url": "https://dharma.gov/alerts/test"}
        
        payload = webhook_provider._prepare_webhook_payload(sample_alert, template_data)
        
        assert payload["event"] == "alert.created"
        assert payload["source"] == "project-dharma"
        assert payload["alert"]["id"] == sample_alert.alert_id
        assert payload["alert"]["title"] == sample_alert.title
        assert payload["alert"]["severity"] == sample_alert.severity.value
        assert payload["alert"]["dashboard_url"] == template_data["dashboard_url"]
    
    @pytest.mark.asyncio
    async def test_webhook_retry_logic(self, webhook_provider, sample_alert):
        """Test webhook retry logic."""
        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.headers = {}
        
        webhook_provider.session.post.return_value.__aenter__.return_value = mock_response
        
        template_data = {"dashboard_url": "https://test.com"}
        
        record = await webhook_provider.send_notification(
            sample_alert,
            "https://example.com/webhook",
            template_data
        )
        
        # Should fail after retries
        assert record.status == NotificationStatus.FAILED
        assert "attempt" in record.metadata
    
    @pytest.mark.asyncio
    async def test_webhook_security_manager(self):
        """Test webhook security manager."""
        from app.notifications.webhook_provider import WebhookSecurityManager
        
        security_manager = WebhookSecurityManager()
        
        # Test signature generation
        payload = "test payload"
        secret = "test_secret"
        signature = security_manager.generate_signature(payload, secret)
        
        assert signature.startswith("sha256=")
        assert len(signature) > 10
        
        # Test domain validation (no restrictions by default)
        assert security_manager.is_domain_allowed("https://example.com") is True
        
        # Test security headers
        test_payload = {"event": "test"}
        headers = security_manager.add_security_headers(test_payload)
        
        assert "X-Dharma-Timestamp" in headers
        assert "X-Dharma-Event" in headers


class TestDashboardProvider:
    """Test cases for Dashboard provider."""
    
    @pytest.fixture
    def dashboard_provider(self):
        """Create dashboard provider for testing."""
        provider = DashboardProvider()
        # Mock WebSocket server startup
        provider._start_websocket_server = AsyncMock()
        return provider
    
    @pytest.mark.asyncio
    async def test_validate_dashboard_recipient(self, dashboard_provider):
        """Test dashboard recipient validation."""
        assert await dashboard_provider.validate_recipient("user123") is True
        assert await dashboard_provider.validate_recipient("dashboard") is True
        assert await dashboard_provider.validate_recipient("") is False
    
    @pytest.mark.asyncio
    async def test_dashboard_notification_preparation(self, dashboard_provider, sample_alert):
        """Test dashboard notification payload preparation."""
        template_data = {
            "notification_title": "Test Alert",
            "notification_message": "Test message",
            "action_url": "/alerts/test"
        }
        
        payload = dashboard_provider._prepare_dashboard_notification(sample_alert, template_data)
        
        assert payload["type"] == "alert_notification"
        assert payload["alert"]["id"] == sample_alert.alert_id
        assert payload["ui"]["notification_title"] == "Test Alert"
        assert payload["ui"]["action_url"] == "/alerts/test"
    
    @pytest.mark.asyncio
    async def test_dashboard_broadcast(self, dashboard_provider):
        """Test dashboard broadcast functionality."""
        # Mock connected clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        
        dashboard_provider.connected_clients.add(mock_client1)
        dashboard_provider.connected_clients.add(mock_client2)
        
        test_payload = {"type": "test", "message": "test broadcast"}
        
        sent_count = await dashboard_provider._broadcast_notification(test_payload)
        
        assert sent_count == 2
        mock_client1.send.assert_called_once()
        mock_client2.send.assert_called_once()


class TestNotificationTemplateEngine:
    """Test cases for NotificationTemplateEngine."""
    
    @pytest.fixture
    def template_engine(self):
        """Create template engine for testing."""
        return NotificationTemplateEngine()
    
    @pytest.mark.asyncio
    async def test_sms_template_generation(self, template_engine, sample_alert):
        """Test SMS template generation."""
        template_data = await template_engine.generate_template_data(
            sample_alert,
            NotificationChannel.SMS
        )
        
        assert "sms_message" in template_data
        assert sample_alert.title in template_data["sms_message"]
        assert "dashboard_url" in template_data
    
    @pytest.mark.asyncio
    async def test_email_template_generation(self, template_engine, sample_alert):
        """Test email template generation."""
        template_data = await template_engine.generate_template_data(
            sample_alert,
            NotificationChannel.EMAIL
        )
        
        assert "subject" in template_data
        assert "content_samples" in template_data
        assert "keywords" in template_data
        assert sample_alert.title in template_data["subject"]
    
    @pytest.mark.asyncio
    async def test_webhook_template_generation(self, template_engine, sample_alert):
        """Test webhook template generation."""
        template_data = await template_engine.generate_template_data(
            sample_alert,
            NotificationChannel.WEBHOOK
        )
        
        assert "webhook_payload" in template_data
        webhook_payload = template_data["webhook_payload"]
        assert webhook_payload["event"] == "alert_created"
        assert webhook_payload["alert"]["id"] == sample_alert.alert_id


class TestNotificationPreferenceManager:
    """Test cases for NotificationPreferenceManager."""
    
    @pytest.fixture
    def preference_manager(self):
        """Create preference manager for testing."""
        return NotificationPreferenceManager()
    
    @pytest.mark.asyncio
    async def test_get_recipients_for_alert(self, preference_manager, sample_alert):
        """Test getting recipients based on alert severity."""
        recipients = await preference_manager.get_recipients_for_alert(sample_alert)
        
        assert len(recipients) > 0
        assert any(NotificationChannel.EMAIL in r["channels"] for r in recipients)
        assert any(NotificationChannel.WEBHOOK in r["channels"] for r in recipients)
    
    @pytest.mark.asyncio
    async def test_user_preferences_management(self, preference_manager):
        """Test user preference management."""
        user_id = "test_user_123"
        preferences = {
            "channels": [NotificationChannel.EMAIL],
            "severity_threshold": SeverityLevel.HIGH,
            "quiet_hours": {"start": "22:00", "end": "08:00"}
        }
        
        await preference_manager.update_user_preferences(user_id, preferences)
        
        retrieved_prefs = await preference_manager.get_user_preferences(user_id)
        assert retrieved_prefs["channels"] == [NotificationChannel.EMAIL]
        assert retrieved_prefs["severity_threshold"] == SeverityLevel.HIGH


@pytest.mark.asyncio
async def test_notification_service_integration(sample_alert):
    """Integration test for the complete notification service."""
    service = NotificationService()
    
    # Mock all providers
    for provider in service.providers.values():
        provider.send_notification = AsyncMock(return_value=NotificationRecord(
            notification_id="test_notif",
            alert_id=sample_alert.alert_id,
            channel=provider.get_channel(),
            recipient="test_recipient",
            status=NotificationStatus.SENT
        ))
        provider.validate_recipient = AsyncMock(return_value=True)
    
    # Test sending notifications
    recipients = [
        {"recipient": "+1234567890", "channels": [NotificationChannel.SMS]},
        {"recipient": "test@example.com", "channels": [NotificationChannel.EMAIL]},
        {"recipient": "https://example.com/webhook", "channels": [NotificationChannel.WEBHOOK]},
        {"recipient": "dashboard", "channels": [NotificationChannel.DASHBOARD]}
    ]
    
    records = await service.send_alert_notifications(sample_alert, recipients)
    
    assert len(records) == 4
    assert all(record.status == NotificationStatus.SENT for record in records)
    
    # Test getting notification stats
    stats = await service.get_notification_stats()
    assert "total_notifications" in stats
    assert "by_status" in stats
    assert "by_channel" in stats
    assert "success_rate" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])