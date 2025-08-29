#!/usr/bin/env python3
"""
Demo script for multi-channel notification service.
This script demonstrates the functionality of all notification channels.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from shared.models.alert import Alert, AlertType, SeverityLevel, AlertStatus, AlertContext, NotificationChannel
from app.notifications.notification_service import NotificationService, NotificationPreferenceManager
from app.core.config import config


async def create_demo_alert() -> Alert:
    """Create a demo alert for testing."""
    context = AlertContext(
        source_platform="twitter",
        detection_method="sentiment_analysis",
        confidence_score=0.85,
        risk_score=0.75,
        affected_regions=["Delhi", "Mumbai", "Bangalore"],
        keywords_matched=["misinformation", "fake news", "viral"],
        hashtags_involved=["#fakenews", "#viral", "#breaking"],
        content_samples=[
            "This is completely false information being spread...",
            "Don't believe this fake news about...",
            "Coordinated effort to spread misinformation..."
        ],
        detection_window_start=datetime.utcnow() - timedelta(hours=2),
        detection_window_end=datetime.utcnow(),
        volume_metrics={
            "post_count": 250,
            "unique_users": 125,
            "repost_count": 180,
            "engagement_rate": 0.65
        },
        engagement_metrics={
            "total_likes": 1500,
            "total_shares": 800,
            "total_comments": 300,
            "viral_coefficient": 2.3
        }
    )
    
    return Alert(
        alert_id=f"demo_alert_{int(datetime.utcnow().timestamp())}",
        title="High-Risk Coordinated Misinformation Campaign Detected",
        description="Automated detection of coordinated spread of false information across multiple social media accounts with high engagement rates",
        alert_type=AlertType.COORDINATED_CAMPAIGN,
        severity=SeverityLevel.HIGH,
        status=AlertStatus.NEW,
        context=context,
        created_at=datetime.utcnow(),
        tags=["misinformation", "coordinated", "high-engagement", "multi-platform"]
    )


async def demo_sms_notifications(service: NotificationService, alert: Alert):
    """Demo SMS notifications."""
    print("\n🔔 Testing SMS Notifications...")
    
    recipients = [
        {
            "recipient": "+1234567890",  # Demo phone number
            "channels": [NotificationChannel.SMS]
        }
    ]
    
    try:
        records = await service.send_alert_notifications(alert, recipients)
        
        for record in records:
            print(f"  ✓ SMS notification {record.notification_id}")
            print(f"    Status: {record.status.value}")
            print(f"    Recipient: {record.recipient}")
            if record.metadata:
                print(f"    Metadata: {json.dumps(record.metadata, indent=4)}")
    
    except Exception as e:
        print(f"  ✗ SMS notification failed: {e}")


async def demo_email_notifications(service: NotificationService, alert: Alert):
    """Demo email notifications."""
    print("\n📧 Testing Email Notifications...")
    
    recipients = [
        {
            "recipient": "analyst@dharma.gov",
            "channels": [NotificationChannel.EMAIL]
        },
        {
            "recipient": "admin@dharma.gov",
            "channels": [NotificationChannel.EMAIL]
        }
    ]
    
    try:
        records = await service.send_alert_notifications(alert, recipients)
        
        for record in records:
            print(f"  ✓ Email notification {record.notification_id}")
            print(f"    Status: {record.status.value}")
            print(f"    Recipient: {record.recipient}")
            if record.metadata:
                print(f"    Subject: {record.metadata.get('subject', 'N/A')}")
    
    except Exception as e:
        print(f"  ✗ Email notification failed: {e}")


async def demo_webhook_notifications(service: NotificationService, alert: Alert):
    """Demo webhook notifications."""
    print("\n🔗 Testing Webhook Notifications...")
    
    recipients = [
        {
            "recipient": "https://external-system.gov/webhooks/alerts",
            "channels": [NotificationChannel.WEBHOOK]
        },
        {
            "recipient": "https://backup-system.gov/api/alerts",
            "channels": [NotificationChannel.WEBHOOK]
        }
    ]
    
    try:
        records = await service.send_alert_notifications(alert, recipients)
        
        for record in records:
            print(f"  ✓ Webhook notification {record.notification_id}")
            print(f"    Status: {record.status.value}")
            print(f"    URL: {record.recipient}")
            if record.metadata:
                print(f"    Attempts: {record.metadata.get('attempt', 'N/A')}")
                print(f"    Status Code: {record.metadata.get('status_code', 'N/A')}")
    
    except Exception as e:
        print(f"  ✗ Webhook notification failed: {e}")


async def demo_dashboard_notifications(service: NotificationService, alert: Alert):
    """Demo dashboard notifications."""
    print("\n📊 Testing Dashboard Notifications...")
    
    recipients = [
        {
            "recipient": "dashboard",
            "channels": [NotificationChannel.DASHBOARD]
        },
        {
            "recipient": "user_analyst_001",
            "channels": [NotificationChannel.DASHBOARD]
        }
    ]
    
    try:
        records = await service.send_alert_notifications(alert, recipients)
        
        for record in records:
            print(f"  ✓ Dashboard notification {record.notification_id}")
            print(f"    Status: {record.status.value}")
            print(f"    Target: {record.recipient}")
            if record.metadata:
                print(f"    Broadcast Count: {record.metadata.get('broadcast_count', 'N/A')}")
                print(f"    User Sessions: {record.metadata.get('user_sessions', 'N/A')}")
    
    except Exception as e:
        print(f"  ✗ Dashboard notification failed: {e}")


async def demo_multi_channel_notifications(service: NotificationService, alert: Alert):
    """Demo multi-channel notifications for a single recipient."""
    print("\n🌐 Testing Multi-Channel Notifications...")
    
    recipients = [
        {
            "recipient": "admin@dharma.gov",
            "channels": [
                NotificationChannel.EMAIL,
                NotificationChannel.DASHBOARD
            ]
        },
        {
            "recipient": "+1234567890",
            "channels": [
                NotificationChannel.SMS,
                NotificationChannel.DASHBOARD
            ]
        }
    ]
    
    try:
        records = await service.send_alert_notifications(alert, recipients)
        
        print(f"  ✓ Sent {len(records)} notifications across multiple channels")
        
        # Group by recipient
        by_recipient = {}
        for record in records:
            if record.recipient not in by_recipient:
                by_recipient[record.recipient] = []
            by_recipient[record.recipient].append(record)
        
        for recipient, recipient_records in by_recipient.items():
            print(f"    Recipient: {recipient}")
            for record in recipient_records:
                print(f"      - {record.channel.value}: {record.status.value}")
    
    except Exception as e:
        print(f"  ✗ Multi-channel notification failed: {e}")


async def demo_notification_stats(service: NotificationService):
    """Demo notification statistics."""
    print("\n📈 Notification Service Statistics...")
    
    try:
        stats = await service.get_notification_stats()
        
        print(f"  Total Notifications: {stats['total_notifications']}")
        print(f"  Success Rate: {stats['success_rate']:.2%}")
        
        print("  By Status:")
        for status, count in stats['by_status'].items():
            print(f"    {status}: {count}")
        
        print("  By Channel:")
        for channel, count in stats['by_channel'].items():
            print(f"    {channel}: {count}")
        
        print("  Queue Sizes:")
        for queue, size in stats['queue_sizes'].items():
            print(f"    {queue}: {size}")
    
    except Exception as e:
        print(f"  ✗ Failed to get stats: {e}")


async def demo_provider_stats(service: NotificationService):
    """Demo individual provider statistics."""
    print("\n🔧 Provider Statistics...")
    
    for channel, provider in service.providers.items():
        try:
            stats = await provider.get_provider_stats()
            print(f"  {channel.value.upper()} Provider:")
            for key, value in stats.items():
                print(f"    {key}: {value}")
            print()
        except Exception as e:
            print(f"  ✗ Failed to get {channel.value} stats: {e}")


async def demo_notification_preferences():
    """Demo notification preference management."""
    print("\n⚙️  Testing Notification Preferences...")
    
    preference_manager = NotificationPreferenceManager()
    
    # Update user preferences
    user_preferences = {
        "channels": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
        "severity_threshold": SeverityLevel.MEDIUM,
        "quiet_hours": {"start": "22:00", "end": "08:00"},
        "timezone": "Asia/Kolkata",
        "alert_types": ["high_risk_content", "coordinated_campaign"]
    }
    
    await preference_manager.update_user_preferences("demo_user", user_preferences)
    
    # Retrieve preferences
    retrieved_prefs = await preference_manager.get_user_preferences("demo_user")
    print(f"  User Preferences: {json.dumps(retrieved_prefs, indent=2, default=str)}")
    
    # Test alert recipient selection
    demo_alert = await create_demo_alert()
    recipients = await preference_manager.get_recipients_for_alert(demo_alert)
    print(f"  Recipients for alert: {len(recipients)}")
    for recipient in recipients:
        print(f"    {recipient['recipient']}: {[c.value for c in recipient['channels']]}")


async def main():
    """Main demo function."""
    print("🚀 Project Dharma Multi-Channel Notification Service Demo")
    print("=" * 60)
    
    # Create demo alert
    alert = await create_demo_alert()
    print(f"\n📋 Created demo alert: {alert.alert_id}")
    print(f"   Title: {alert.title}")
    print(f"   Severity: {alert.severity.value}")
    print(f"   Type: {alert.alert_type.value}")
    
    # Initialize notification service
    print("\n🔧 Initializing notification service...")
    service = NotificationService()
    
    # Wait a moment for service initialization
    await asyncio.sleep(1)
    
    # Demo each notification channel
    await demo_sms_notifications(service, alert)
    await demo_email_notifications(service, alert)
    await demo_webhook_notifications(service, alert)
    await demo_dashboard_notifications(service, alert)
    
    # Demo multi-channel notifications
    await demo_multi_channel_notifications(service, alert)
    
    # Wait for notifications to process
    print("\n⏳ Waiting for notifications to process...")
    await asyncio.sleep(3)
    
    # Show statistics
    await demo_notification_stats(service)
    await demo_provider_stats(service)
    
    # Demo preferences
    await demo_notification_preferences()
    
    print("\n✅ Demo completed successfully!")
    print("\nNote: Some notifications may show as failed if external services")
    print("(Twilio, SMTP, webhooks) are not properly configured.")


if __name__ == "__main__":
    asyncio.run(main())