"""Multi-channel notification service for alert delivery."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from enum import Enum

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.models.alert import Alert, NotificationChannel, SeverityLevel
from shared.models.user import SystemUser

from ..core.config import config

logger = logging.getLogger(__name__)


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"


class NotificationRecord:
    """Record of a notification attempt."""
    
    def __init__(
        self,
        notification_id: str,
        alert_id: str,
        channel: NotificationChannel,
        recipient: str,
        status: NotificationStatus = NotificationStatus.PENDING,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.notification_id = notification_id
        self.alert_id = alert_id
        self.channel = channel
        self.recipient = recipient
        self.status = status
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.sent_at: Optional[datetime] = None
        self.delivered_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.retry_count = 0
        self.max_retries = 3
    
    def mark_sent(self):
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()
    
    def mark_delivered(self):
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str):
        """Mark notification as failed."""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
    
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        self.status = NotificationStatus.RETRY


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""
    
    @abstractmethod
    async def send_notification(
        self,
        alert: Alert,
        recipient: str,
        template_data: Dict[str, Any]
    ) -> NotificationRecord:
        """Send notification through this provider."""
        pass
    
    @abstractmethod
    def get_channel(self) -> NotificationChannel:
        """Get the notification channel this provider handles."""
        pass
    
    @abstractmethod
    async def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient format for this channel."""
        pass


class NotificationService:
    """Main notification service orchestrator."""
    
    def __init__(self):
        self.providers: Dict[NotificationChannel, NotificationProvider] = {}
        self.notification_records: Dict[str, NotificationRecord] = {}
        self.template_engine = NotificationTemplateEngine()
        self.delivery_queue = asyncio.Queue()
        self.retry_queue = asyncio.Queue()
        
        # Initialize providers
        self._initialize_providers()
        
        # Start background workers
        self._start_workers()
    
    def _initialize_providers(self):
        """Initialize notification providers."""
        from .sms_provider import SMSProvider
        from .email_provider import EmailProvider
        from .webhook_provider import WebhookProvider
        from .dashboard_provider import DashboardProvider
        
        # Initialize providers
        self.providers[NotificationChannel.SMS] = SMSProvider()
        self.providers[NotificationChannel.EMAIL] = EmailProvider()
        self.providers[NotificationChannel.WEBHOOK] = WebhookProvider()
        self.providers[NotificationChannel.DASHBOARD] = DashboardProvider()
    
    def _start_workers(self):
        """Start background workers."""
        asyncio.create_task(self._delivery_worker())
        asyncio.create_task(self._retry_worker())
    
    async def send_alert_notifications(
        self,
        alert: Alert,
        recipients: List[Dict[str, Any]]
    ) -> List[NotificationRecord]:
        """Send notifications for an alert to multiple recipients."""
        notification_records = []
        
        try:
            for recipient_info in recipients:
                recipient = recipient_info.get("recipient")
                channels = recipient_info.get("channels", [])
                
                for channel in channels:
                    if channel in self.providers:
                        # Create notification record
                        notification_id = self._generate_notification_id(alert.alert_id, channel, recipient)
                        record = NotificationRecord(
                            notification_id=notification_id,
                            alert_id=alert.alert_id,
                            channel=channel,
                            recipient=recipient
                        )
                        
                        # Queue for delivery
                        await self.delivery_queue.put((alert, record))
                        notification_records.append(record)
                        self.notification_records[notification_id] = record
            
            # Update alert with notification records
            alert.notifications_sent.extend([
                {
                    "notification_id": record.notification_id,
                    "channel": record.channel.value,
                    "recipient": record.recipient,
                    "status": record.status.value,
                    "created_at": record.created_at.isoformat()
                }
                for record in notification_records
            ])
            
            return notification_records
            
        except Exception as e:
            logger.error(f"Error sending alert notifications: {e}")
            return []
    
    async def _delivery_worker(self):
        """Background worker for processing notification deliveries."""
        while True:
            try:
                alert, record = await self.delivery_queue.get()
                await self._process_notification(alert, record)
                self.delivery_queue.task_done()
            except Exception as e:
                logger.error(f"Error in delivery worker: {e}")
                await asyncio.sleep(1)
    
    async def _retry_worker(self):
        """Background worker for processing notification retries."""
        while True:
            try:
                alert, record = await self.retry_queue.get()
                
                if record.can_retry():
                    record.increment_retry()
                    await asyncio.sleep(2 ** record.retry_count)  # Exponential backoff
                    await self._process_notification(alert, record)
                else:
                    record.mark_failed("Max retries exceeded")
                    logger.warning(f"Notification {record.notification_id} failed after max retries")
                
                self.retry_queue.task_done()
            except Exception as e:
                logger.error(f"Error in retry worker: {e}")
                await asyncio.sleep(1)
    
    async def _process_notification(self, alert: Alert, record: NotificationRecord):
        """Process a single notification."""
        try:
            provider = self.providers[record.channel]
            
            # Validate recipient
            if not await provider.validate_recipient(record.recipient):
                record.mark_failed("Invalid recipient format")
                return
            
            # Generate template data
            template_data = await self.template_engine.generate_template_data(alert, record.channel)
            
            # Send notification
            result = await provider.send_notification(alert, record.recipient, template_data)
            
            if result.status == NotificationStatus.SENT:
                record.mark_sent()
                logger.info(f"Notification {record.notification_id} sent successfully")
            else:
                record.mark_failed(result.error_message or "Unknown error")
                
                # Queue for retry if possible
                if record.can_retry():
                    await self.retry_queue.put((alert, record))
            
        except Exception as e:
            logger.error(f"Error processing notification {record.notification_id}: {e}")
            record.mark_failed(str(e))
            
            # Queue for retry if possible
            if record.can_retry():
                await self.retry_queue.put((alert, record))
    
    def _generate_notification_id(self, alert_id: str, channel: NotificationChannel, recipient: str) -> str:
        """Generate unique notification ID."""
        import hashlib
        
        data = f"{alert_id}_{channel.value}_{recipient}_{datetime.utcnow().isoformat()}"
        hash_digest = hashlib.md5(data.encode()).hexdigest()[:8]
        return f"notif_{hash_digest}"
    
    async def get_notification_status(self, notification_id: str) -> Optional[NotificationRecord]:
        """Get notification status."""
        return self.notification_records.get(notification_id)
    
    async def get_alert_notifications(self, alert_id: str) -> List[NotificationRecord]:
        """Get all notifications for an alert."""
        return [
            record for record in self.notification_records.values()
            if record.alert_id == alert_id
        ]
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        total_notifications = len(self.notification_records)
        
        # Count by status
        status_counts = {}
        for status in NotificationStatus:
            status_counts[status.value] = sum(
                1 for record in self.notification_records.values()
                if record.status == status
            )
        
        # Count by channel
        channel_counts = {}
        for channel in NotificationChannel:
            channel_counts[channel.value] = sum(
                1 for record in self.notification_records.values()
                if record.channel == channel
            )
        
        # Calculate success rate
        sent_count = status_counts.get(NotificationStatus.SENT.value, 0)
        delivered_count = status_counts.get(NotificationStatus.DELIVERED.value, 0)
        success_rate = (sent_count + delivered_count) / total_notifications if total_notifications > 0 else 0
        
        return {
            "total_notifications": total_notifications,
            "by_status": status_counts,
            "by_channel": channel_counts,
            "success_rate": success_rate,
            "queue_sizes": {
                "delivery": self.delivery_queue.qsize(),
                "retry": self.retry_queue.qsize()
            }
        }


class NotificationTemplateEngine:
    """Template engine for generating notification content."""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load notification templates."""
        return {
            NotificationChannel.SMS.value: {
                "critical": "🚨 CRITICAL ALERT: {title}. {description}. View: {dashboard_url}",
                "high": "⚠️ HIGH ALERT: {title}. {description}. View: {dashboard_url}",
                "medium": "📢 ALERT: {title}. View: {dashboard_url}",
                "low": "ℹ️ {title}. View: {dashboard_url}"
            },
            NotificationChannel.EMAIL.value: {
                "subject": "Project Dharma Alert: {title}",
                "html_template": "alert_email.html",
                "text_template": "alert_email.txt"
            },
            NotificationChannel.DASHBOARD.value: {
                "title": "{title}",
                "message": "{description}",
                "action_url": "/alerts/{alert_id}"
            },
            NotificationChannel.WEBHOOK.value: {
                "payload_template": "webhook_payload.json"
            }
        }
    
    async def generate_template_data(
        self,
        alert: Alert,
        channel: NotificationChannel
    ) -> Dict[str, Any]:
        """Generate template data for an alert and channel."""
        base_data = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity,
            "alert_type": alert.alert_type,
            "created_at": alert.created_at.isoformat() if alert.created_at else "",
            "dashboard_url": f"{config.dashboard_base_url}/alerts/{alert.alert_id}",
            "platform": alert.context.source_platform or "Unknown",
            "confidence_score": alert.context.confidence_score,
            "risk_score": alert.context.risk_score
        }
        
        # Add channel-specific data
        if channel == NotificationChannel.SMS:
            template_key = alert.severity
            template = self.templates[channel.value].get(template_key, self.templates[channel.value]["medium"])
            base_data["sms_message"] = template.format(**base_data)
        
        elif channel == NotificationChannel.EMAIL:
            base_data["subject"] = self.templates[channel.value]["subject"].format(**base_data)
            base_data["content_samples"] = alert.context.content_samples[:3]  # Limit samples
            base_data["keywords"] = ", ".join(alert.context.keywords_matched[:10])  # Limit keywords
            base_data["affected_regions"] = ", ".join(alert.context.affected_regions)
        
        elif channel == NotificationChannel.DASHBOARD:
            base_data["notification_title"] = self.templates[channel.value]["title"].format(**base_data)
            base_data["notification_message"] = self.templates[channel.value]["message"].format(**base_data)
            base_data["action_url"] = self.templates[channel.value]["action_url"].format(**base_data)
        
        elif channel == NotificationChannel.WEBHOOK:
            base_data["webhook_payload"] = {
                "event": "alert_created",
                "alert": {
                    "id": alert.alert_id,
                    "title": alert.title,
                    "description": alert.description,
                    "severity": alert.severity,
                    "type": alert.alert_type,
                    "created_at": base_data["created_at"],
                    "context": {
                        "platform": alert.context.source_platform,
                        "confidence": alert.context.confidence_score,
                        "risk_score": alert.context.risk_score,
                        "affected_regions": alert.context.affected_regions
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return base_data


class NotificationPreferenceManager:
    """Manages user notification preferences."""
    
    def __init__(self):
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
    
    async def get_recipients_for_alert(self, alert: Alert) -> List[Dict[str, Any]]:
        """Get recipients for an alert based on preferences."""
        recipients = []
        
        # For now, use default recipients based on severity
        # In production, this would query user preferences from database
        
        if alert.severity == SeverityLevel.CRITICAL:
            recipients.extend([
                {
                    "recipient": "+1234567890",  # Emergency contact
                    "channels": [NotificationChannel.SMS, NotificationChannel.EMAIL]
                },
                {
                    "recipient": "admin@dharma.gov",
                    "channels": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD]
                }
            ])
        
        elif alert.severity == SeverityLevel.HIGH:
            recipients.extend([
                {
                    "recipient": "analyst@dharma.gov",
                    "channels": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD]
                }
            ])
        
        else:
            recipients.extend([
                {
                    "recipient": "dashboard",
                    "channels": [NotificationChannel.DASHBOARD]
                }
            ])
        
        # Add webhook notifications for all alerts
        recipients.append({
            "recipient": "https://external-system.gov/webhooks/alerts",
            "channels": [NotificationChannel.WEBHOOK]
        })
        
        return recipients
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ):
        """Update user notification preferences."""
        self.user_preferences[user_id] = preferences
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user notification preferences."""
        return self.user_preferences.get(user_id, {
            "channels": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
            "severity_threshold": SeverityLevel.MEDIUM,
            "quiet_hours": {"start": "22:00", "end": "08:00"},
            "timezone": "Asia/Kolkata"
        })