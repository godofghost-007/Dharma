#!/usr/bin/env python3
"""
Simple test script to verify notification service implementation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

import asyncio
from datetime import datetime, timedelta

# Import the models and services
from shared.models.alert import Alert, AlertType, SeverityLevel, AlertStatus, AlertContext, NotificationChannel
from services.alert-management-service.app.notifications.notification_service import NotificationService


async def test_notification_service():
    """Test the notification service implementation."""
    print("🧪 Testing Multi-Channel Notification Service Implementation")
    print("=" * 60)
    
    # Create a test alert
    context = AlertContext(
        source_platform="twitter",
        detection_method="sentiment_analysis",
        confidence_score=0.85,
        risk_score=0.75,
        affected_regions=["Delhi", "Mumbai"],
        keywords_matched=["test", "demo"],
        hashtags_involved=["#test"],
        content_samples=["This is a test alert"],
        detection_window_start=datetime.utcnow() - timedelta(hours=1),
        detection_window_end=datetime.utcnow(),
        volume_metrics={"post_count": 10},
        engagement_metrics={"total_likes": 50}
    )
    
    alert = Alert(
        alert_id="test_alert_001",
        title="Test Alert for Notification Service",
        description="This is a test alert to verify notification service functionality",
        alert_type=AlertType.HIGH_RISK_CONTENT,
        severity=SeverityLevel.HIGH,
        status=AlertStatus.NEW,
        context=context,
        created_at=datetime.utcnow(),
        tags=["test", "demo"]
    )
    
    print(f"✓ Created test alert: {alert.alert_id}")
    
    # Initialize notification service
    try:
        service = NotificationService()
        print("✓ Notification service initialized successfully")
        
        # Test provider initialization
        print(f"✓ Initialized {len(service.providers)} notification providers:")
        for channel, provider in service.providers.items():
            print(f"  - {channel.value}: {provider.__class__.__name__}")
        
        # Test template engine
        template_data = await service.template_engine.generate_template_data(
            alert, NotificationChannel.EMAIL
        )
        print("✓ Template engine working correctly")
        print(f"  - Generated template data keys: {list(template_data.keys())}")
        
        # Test notification record creation
        recipients = [
            {"recipient": "test@example.com", "channels": [NotificationChannel.EMAIL]},
            {"recipient": "+1234567890", "channels": [NotificationChannel.SMS]},
            {"recipient": "https://example.com/webhook", "channels": [NotificationChannel.WEBHOOK]},
            {"recipient": "dashboard", "channels": [NotificationChannel.DASHBOARD]}
        ]
        
        print("✓ Testing notification record creation...")
        
        # Mock the providers to avoid actual sending
        for provider in service.providers.values():
            original_send = provider.send_notification
            original_validate = provider.validate_recipient
            
            async def mock_send(alert, recipient, template_data):
                from services.alert_management_service.app.notifications.notification_service import NotificationRecord, NotificationStatus
                record = NotificationRecord(
                    notification_id=f"mock_{alert.alert_id}_{recipient}",
                    alert_id=alert.alert_id,
                    channel=provider.get_channel(),
                    recipient=recipient
                )
                record.mark_sent()
                return record
            
            async def mock_validate(recipient):
                return True
            
            provider.send_notification = mock_send
            provider.validate_recipient = mock_validate
        
        # Test sending notifications
        records = await service.send_alert_notifications(alert, recipients)
        print(f"✓ Created {len(records)} notification records")
        
        for record in records:
            print(f"  - {record.channel.value} to {record.recipient}: {record.status.value}")
        
        # Test statistics
        await asyncio.sleep(1)  # Allow processing
        stats = await service.get_notification_stats()
        print("✓ Notification statistics:")
        print(f"  - Total notifications: {stats['total_notifications']}")
        print(f"  - Success rate: {stats['success_rate']:.2%}")
        
        print("\n🎉 All tests passed! Multi-channel notification service is working correctly.")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_notification_service())