#!/usr/bin/env python3
"""
Simple test to verify notification service implementation.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

try:
    from shared.models.alert import Alert, AlertType, SeverityLevel, AlertStatus, AlertContext, NotificationChannel
    from app.notifications.notification_service import NotificationService
    print("✓ Successfully imported notification service components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_notification_service():
    """Test the notification service implementation."""
    print("🧪 Testing Multi-Channel Notification Service Implementation")
    print("=" * 60)
    
    try:
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
        
        print("\n🎉 Basic notification service test passed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_notification_service())
    sys.exit(0 if success else 1)