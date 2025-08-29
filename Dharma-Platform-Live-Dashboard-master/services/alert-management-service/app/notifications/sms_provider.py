"""SMS notification provider using Twilio API."""

import logging
import re
from typing import Dict, Any
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.models.alert import Alert, NotificationChannel
from ..core.config import config
from .notification_service import NotificationProvider, NotificationRecord, NotificationStatus

logger = logging.getLogger(__name__)


class SMSProvider(NotificationProvider):
    """SMS notification provider using Twilio."""
    
    def __init__(self):
        self.client = None
        self.from_number = config.twilio_phone_number
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Twilio client."""
        try:
            if config.twilio_account_sid and config.twilio_auth_token:
                self.client = Client(config.twilio_account_sid, config.twilio_auth_token)
                logger.info("Twilio SMS client initialized successfully")
            else:
                logger.warning("Twilio credentials not configured, SMS notifications disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
    
    def get_channel(self) -> NotificationChannel:
        """Get the notification channel this provider handles."""
        return NotificationChannel.SMS
    
    async def validate_recipient(self, recipient: str) -> bool:
        """Validate phone number format."""
        # Basic phone number validation (E.164 format)
        phone_pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(phone_pattern, recipient))
    
    async def send_notification(
        self,
        alert: Alert,
        recipient: str,
        template_data: Dict[str, Any]
    ) -> NotificationRecord:
        """Send SMS notification."""
        notification_id = f"sms_{alert.alert_id}_{recipient.replace('+', '')}"
        record = NotificationRecord(
            notification_id=notification_id,
            alert_id=alert.alert_id,
            channel=NotificationChannel.SMS,
            recipient=recipient
        )
        
        try:
            if not self.client:
                record.mark_failed("Twilio client not initialized")
                return record
            
            if not self.from_number:
                record.mark_failed("Twilio phone number not configured")
                return record
            
            # Get SMS message from template data
            message_body = template_data.get("sms_message", f"Alert: {alert.title}")
            
            # Ensure message is within SMS length limits (160 characters for single SMS)
            if len(message_body) > 160:
                message_body = message_body[:157] + "..."
            
            # Send SMS
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=recipient
            )
            
            # Update record with Twilio message SID
            record.metadata["twilio_sid"] = message.sid
            record.metadata["message_body"] = message_body
            record.mark_sent()
            
            logger.info(f"SMS sent successfully to {recipient}, SID: {message.sid}")
            
        except TwilioException as e:
            error_msg = f"Twilio error: {e.msg}"
            record.mark_failed(error_msg)
            logger.error(f"Failed to send SMS to {recipient}: {error_msg}")
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            record.mark_failed(error_msg)
            logger.error(f"Failed to send SMS to {recipient}: {error_msg}")
        
        return record
    
    async def get_delivery_status(self, twilio_sid: str) -> str:
        """Get delivery status from Twilio."""
        try:
            if not self.client:
                return "unknown"
            
            message = self.client.messages(twilio_sid).fetch()
            return message.status
            
        except Exception as e:
            logger.error(f"Failed to get SMS delivery status for {twilio_sid}: {e}")
            return "unknown"
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get SMS provider statistics."""
        stats = {
            "provider": "twilio",
            "configured": self.client is not None,
            "from_number": self.from_number,
            "client_status": "active" if self.client else "inactive"
        }
        
        try:
            if self.client:
                # Get account info
                account = self.client.api.accounts(config.twilio_account_sid).fetch()
                stats["account_status"] = account.status
                
        except Exception as e:
            logger.error(f"Failed to get Twilio account stats: {e}")
            stats["error"] = str(e)
        
        return stats


class SMSTemplateManager:
    """Manages SMS templates and formatting."""
    
    def __init__(self):
        self.templates = {
            "critical": "🚨 CRITICAL: {title} - {platform} - Confidence: {confidence_score:.0%} - {dashboard_url}",
            "high": "⚠️ HIGH: {title} - {platform} - {dashboard_url}",
            "medium": "📢 MEDIUM: {title} - {dashboard_url}",
            "low": "ℹ️ {title} - {dashboard_url}"
        }
        
        # Emoji mappings for different alert types
        self.alert_type_emojis = {
            "high_risk_content": "🚨",
            "bot_network_detected": "🤖",
            "coordinated_campaign": "🎯",
            "viral_misinformation": "📈",
            "sentiment_anomaly": "📊",
            "volume_spike": "📈",
            "system_health": "⚙️",
            "data_quality": "📋"
        }
    
    def format_sms_message(self, alert: Alert, template_data: Dict[str, Any]) -> str:
        """Format SMS message for alert."""
        # Get appropriate template
        severity = alert.severity
        template = self.templates.get(severity, self.templates["medium"])
        
        # Add alert type emoji
        emoji = self.alert_type_emojis.get(alert.alert_type, "📢")
        
        # Format message
        message = template.format(**template_data)
        
        # Ensure message fits in SMS length
        if len(message) > 160:
            # Truncate and add ellipsis
            message = message[:157] + "..."
        
        return message
    
    def create_urgent_message(self, alert: Alert, dashboard_url: str) -> str:
        """Create urgent SMS message for critical alerts."""
        return f"🚨 URGENT: {alert.title[:50]}... Immediate attention required. {dashboard_url}"
    
    def create_summary_message(self, alert_count: int, dashboard_url: str) -> str:
        """Create summary message for multiple alerts."""
        return f"📊 {alert_count} new alerts require attention. View dashboard: {dashboard_url}"


class SMSRateLimiter:
    """Rate limiter for SMS notifications to prevent spam."""
    
    def __init__(self):
        self.send_history: Dict[str, list] = {}  # recipient -> list of timestamps
        self.max_sms_per_hour = 10
        self.max_sms_per_day = 50
    
    async def can_send_sms(self, recipient: str) -> bool:
        """Check if SMS can be sent to recipient."""
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Get send history for recipient
        history = self.send_history.get(recipient, [])
        
        # Clean old entries
        history = [ts for ts in history if ts > day_ago]
        self.send_history[recipient] = history
        
        # Check hourly limit
        recent_sends = [ts for ts in history if ts > hour_ago]
        if len(recent_sends) >= self.max_sms_per_hour:
            logger.warning(f"SMS hourly rate limit exceeded for {recipient}")
            return False
        
        # Check daily limit
        if len(history) >= self.max_sms_per_day:
            logger.warning(f"SMS daily rate limit exceeded for {recipient}")
            return False
        
        return True
    
    async def record_sms_sent(self, recipient: str):
        """Record that SMS was sent to recipient."""
        from datetime import datetime
        
        if recipient not in self.send_history:
            self.send_history[recipient] = []
        
        self.send_history[recipient].append(datetime.utcnow())
    
    async def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        total_recipients = len(self.send_history)
        
        # Count recent sends
        hourly_sends = 0
        daily_sends = 0
        
        for history in self.send_history.values():
            hourly_sends += len([ts for ts in history if ts > hour_ago])
            daily_sends += len([ts for ts in history if ts > day_ago])
        
        return {
            "total_recipients": total_recipients,
            "hourly_sends": hourly_sends,
            "daily_sends": daily_sends,
            "max_per_hour": self.max_sms_per_hour,
            "max_per_day": self.max_sms_per_day
        }