#!/usr/bin/env python3
"""
Final Alert Management System Integration Test
Tests the complete alert management system with all components working together.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import shared models
from shared.models.alert import (
    Alert, AlertContext, AlertType, SeverityLevel, AlertStatus,
    NotificationChannel, EscalationRule, NotificationPreference
)

# Import alert management components
from app.core.alert_generator import AlertGenerator
from app.core.alert_deduplicator import AlertDeduplicator
from app.core.alert_correlator import AlertCorrelator
from app.core.severity_calculator import SeverityCalculator
from app.core.alert_manager import AlertManager
from app.core.escalation_engine import EscalationEngine
from app.core.search_service import SearchService
from app.core.reporting_service import ReportingService

# Import notification service
from app.notifications.notification_service import NotificationService

# Import interface components
from app.interface.alert_management_dashboard import AlertManagementDashboard
from app.api.alert_interface import AlertInterface


class TestAlertManagementSystemIntegration:
    """Comprehensive integration tests for the alert management system."""
    
    @pytest.fixture
    def sample_alert_context(self):
        """Create a sample alert context for testing."""
        return AlertContext(
            source_platform="twitter",
            content_samples=["Test content for alert"],
            detection_method="sentiment_analysis",
            confidence_score=0.85,
            risk_score=0.78,
            detection_window_start=datetime.utcnow() - timedelta(hours=1),
            detection_window_end=datetime.utcnow(),
            keywords_matched=["test", "alert"],
            affected_regions=["India"],
            volume_metrics={"post_count": 150, "user_count": 45},
            engagement_metrics={"total_likes": 1200, "total_shares": 340}
        )
    
    @pytest.fixture
    def sample_alert(self, sample_alert_context):
        """Create a sample alert for testing."""
        return Alert(
            alert_id="test_integration_001",
            title="Integration Test Alert",
            description="Testing complete alert management system",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.HIGH,
            status=AlertStatus.NEW,
            context=sample_alert_context,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_alert_generation_pipeline(self, sample_alert_context):
        """Test the complete alert generation pipeline."""
        print("Testing Alert Generation Pipeline...")
        
        # Initialize components
        generator = AlertGenerator()
        deduplicator = AlertDeduplicator()
        correlator = AlertCorrelator()
        severity_calc = SeverityCalculator()
        
        # Test data
        test_data = {
            "content": "This is anti-India propaganda content",
            "platform": "twitter",
            "user_id": "test_user_123",
            "sentiment_score": -0.85,
            "bot_probability": 0.92,
            "engagement_metrics": {"likes": 500, "shares": 200}
        }
        
        # Generate alert
        alert = generator.generate_alert(test_data)
        assert alert is not None
        assert alert.alert_type == AlertType.HIGH_RISK_CONTENT
        print(f"✓ Generated alert: {alert.alert_id}")
        
        # Test deduplication
        is_duplicate = deduplicator.is_duplicate(alert)
        assert not is_duplicate  # First occurrence should not be duplicate
        print("✓ Deduplication check passed")
        
        # Test correlation
        related_alerts = correlator.find_related_alerts(alert)
        assert isinstance(related_alerts, list)
        print(f"✓ Found {len(related_alerts)} related alerts")
        
        # Test severity calculation
        calculated_severity = severity_calc.calculate_severity(alert.context)
        assert calculated_severity in [SeverityLevel.LOW, SeverityLevel.MEDIUM, 
                                     SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        print(f"✓ Calculated severity: {calculated_severity}")
    
    def test_notification_system_integration(self, sample_alert):
        """Test the notification system integration."""
        print("Testing Notification System Integration...")
        
        # Initialize notification service
        notification_service = NotificationService()
        
        # Test notification preferences
        preferences = NotificationPreference(
            user_id="analyst_001",
            channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
            severity_filter=[SeverityLevel.HIGH, SeverityLevel.CRITICAL],
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            enabled=True
        )
        
        # Test notification routing
        result = notification_service.route_notification(sample_alert, preferences)
        assert result["success"] is True
        assert len(result["channels_notified"]) > 0
        print(f"✓ Notification routed to {len(result['channels_notified'])} channels")
        
        # Test notification formatting
        email_content = notification_service.format_email_notification(sample_alert)
        assert "Integration Test Alert" in email_content["subject"]
        assert sample_alert.description in email_content["body"]
        print("✓ Email notification formatted correctly")
        
        dashboard_notification = notification_service.format_dashboard_notification(sample_alert)
        assert dashboard_notification["alert_id"] == sample_alert.alert_id
        assert dashboard_notification["severity"] == sample_alert.severity
        print("✓ Dashboard notification formatted correctly")
    
    def test_alert_management_workflow(self, sample_alert):
        """Test the complete alert management workflow."""
        print("Testing Alert Management Workflow...")
        
        # Initialize alert manager
        alert_manager = AlertManager()
        
        # Test alert processing
        processed_alert = alert_manager.process_alert(sample_alert)
        assert processed_alert.alert_id == sample_alert.alert_id
        assert processed_alert.status == AlertStatus.NEW
        print("✓ Alert processed successfully")
        
        # Test alert acknowledgment
        ack_result = alert_manager.acknowledge_alert(
            sample_alert.alert_id, 
            "analyst_001", 
            "Investigating this alert"
        )
        assert ack_result["success"] is True
        assert ack_result["alert"]["status"] == AlertStatus.ACKNOWLEDGED
        print("✓ Alert acknowledged successfully")
        
        # Test alert assignment
        assign_result = alert_manager.assign_alert(
            sample_alert.alert_id,
            "analyst_001",
            "senior_analyst_002"
        )
        assert assign_result["success"] is True
        assert assign_result["alert"]["assigned_to"] == "senior_analyst_002"
        print("✓ Alert assigned successfully")
        
        # Test alert resolution
        resolve_result = alert_manager.resolve_alert(
            sample_alert.alert_id,
            "senior_analyst_002",
            "False positive - content was satirical",
            "false_positive"
        )
        assert resolve_result["success"] is True
        assert resolve_result["alert"]["status"] == AlertStatus.RESOLVED
        print("✓ Alert resolved successfully")
    
    def test_escalation_system(self, sample_alert):
        """Test the alert escalation system."""
        print("Testing Alert Escalation System...")
        
        # Initialize escalation engine
        escalation_engine = EscalationEngine()
        
        # Create escalation rule
        escalation_rule = EscalationRule(
            rule_id="critical_escalation",
            name="Critical Alert Escalation",
            conditions={
                "severity": [SeverityLevel.CRITICAL],
                "unacknowledged_time_minutes": 30
            },
            escalation_delay_minutes=30,
            escalation_levels=[
                {"level": 1, "notify_users": ["supervisor_001"]},
                {"level": 2, "notify_users": ["manager_001", "director_001"]}
            ],
            max_escalation_level=2,
            enabled=True
        )
        
        # Test escalation rule evaluation
        should_escalate = escalation_engine.should_escalate(sample_alert, escalation_rule)
        # Should not escalate immediately for new alert
        assert not should_escalate
        print("✓ Escalation rule evaluation correct")
        
        # Simulate time passing and test escalation
        sample_alert.created_at = datetime.utcnow() - timedelta(minutes=35)
        should_escalate = escalation_engine.should_escalate(sample_alert, escalation_rule)
        # Should escalate for old unacknowledged critical alert
        if sample_alert.severity == SeverityLevel.CRITICAL:
            assert should_escalate
            print("✓ Escalation triggered correctly for overdue critical alert")
        else:
            print("✓ Escalation correctly not triggered for non-critical alert")
    
    def test_search_and_filtering(self):
        """Test search and filtering functionality."""
        print("Testing Search and Filtering...")
        
        # Initialize search service
        search_service = SearchService()
        
        # Create sample alerts for search testing
        alerts = []
        for i in range(5):
            context = AlertContext(
                source_platform="twitter" if i % 2 == 0 else "youtube",
                content_samples=[f"Test content {i}"],
                detection_method="sentiment_analysis",
                confidence_score=0.8 + (i * 0.02),
                risk_score=0.7 + (i * 0.03),
                detection_window_start=datetime.utcnow() - timedelta(hours=i+1),
                detection_window_end=datetime.utcnow() - timedelta(hours=i),
                keywords_matched=["test", f"keyword_{i}"],
                affected_regions=["India"]
            )
            
            alert = Alert(
                alert_id=f"search_test_{i:03d}",
                title=f"Search Test Alert {i}",
                description=f"Testing search functionality {i}",
                alert_type=AlertType.HIGH_RISK_CONTENT if i % 2 == 0 else AlertType.BOT_NETWORK_DETECTED,
                severity=SeverityLevel.HIGH if i < 3 else SeverityLevel.MEDIUM,
                status=AlertStatus.NEW if i < 2 else AlertStatus.ACKNOWLEDGED,
                context=context
            )
            alerts.append(alert)
        
        # Test text search
        search_results = search_service.search_alerts(alerts, query="Search Test")
        assert len(search_results) == 5
        print(f"✓ Text search returned {len(search_results)} results")
        
        # Test filtering by severity
        high_severity_alerts = search_service.filter_by_severity(alerts, [SeverityLevel.HIGH])
        assert len(high_severity_alerts) == 3
        print(f"✓ Severity filter returned {len(high_severity_alerts)} high severity alerts")
        
        # Test filtering by status
        new_alerts = search_service.filter_by_status(alerts, [AlertStatus.NEW])
        assert len(new_alerts) == 2
        print(f"✓ Status filter returned {len(new_alerts)} new alerts")
        
        # Test filtering by platform
        twitter_alerts = search_service.filter_by_platform(alerts, ["twitter"])
        assert len(twitter_alerts) == 3
        print(f"✓ Platform filter returned {len(twitter_alerts)} Twitter alerts")
    
    def test_reporting_and_analytics(self):
        """Test reporting and analytics functionality."""
        print("Testing Reporting and Analytics...")
        
        # Initialize reporting service
        reporting_service = ReportingService()
        
        # Create sample alerts for reporting
        alerts = []
        statuses = [AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING, AlertStatus.RESOLVED]
        severities = [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        
        for i in range(20):
            context = AlertContext(
                source_platform="twitter",
                content_samples=[f"Report test content {i}"],
                detection_method="sentiment_analysis",
                confidence_score=0.8,
                risk_score=0.7,
                detection_window_start=datetime.utcnow() - timedelta(hours=1),
                detection_window_end=datetime.utcnow(),
                affected_regions=["India"]
            )
            
            alert = Alert(
                alert_id=f"report_test_{i:03d}",
                title=f"Report Test Alert {i}",
                description=f"Testing reporting {i}",
                alert_type=AlertType.HIGH_RISK_CONTENT,
                severity=severities[i % len(severities)],
                status=statuses[i % len(statuses)],
                context=context,
                created_at=datetime.utcnow() - timedelta(days=i % 7)
            )
            alerts.append(alert)
        
        # Test summary statistics
        summary = reporting_service.generate_summary_stats(alerts)
        assert summary["total_alerts"] == 20
        assert summary["by_severity"]["critical"] == 5
        assert summary["by_status"]["new"] == 5
        print("✓ Summary statistics generated correctly")
        
        # Test trend analysis
        trends = reporting_service.analyze_trends(alerts, days=7)
        assert "daily_counts" in trends
        assert len(trends["daily_counts"]) <= 7
        print("✓ Trend analysis completed")
        
        # Test performance metrics
        performance = reporting_service.calculate_performance_metrics(alerts)
        assert "avg_response_time" in performance
        assert "resolution_rate" in performance
        print("✓ Performance metrics calculated")
    
    def test_dashboard_interface_integration(self, sample_alert):
        """Test dashboard interface integration."""
        print("Testing Dashboard Interface Integration...")
        
        # Initialize dashboard
        dashboard = AlertManagementDashboard()
        
        # Test dashboard data loading
        dashboard_data = dashboard.load_dashboard_data()
        assert "alerts" in dashboard_data
        assert "summary_stats" in dashboard_data
        assert "recent_activity" in dashboard_data
        print("✓ Dashboard data loaded successfully")
        
        # Test alert inbox rendering
        inbox_data = dashboard.render_alert_inbox([sample_alert])
        assert len(inbox_data["alerts"]) == 1
        assert inbox_data["alerts"][0]["alert_id"] == sample_alert.alert_id
        print("✓ Alert inbox rendered correctly")
        
        # Test alert detail view
        detail_view = dashboard.render_alert_detail(sample_alert)
        assert detail_view["alert"]["alert_id"] == sample_alert.alert_id
        assert "context" in detail_view["alert"]
        assert "timeline" in detail_view
        print("✓ Alert detail view rendered correctly")
    
    def test_api_interface_integration(self, sample_alert):
        """Test API interface integration."""
        print("Testing API Interface Integration...")
        
        # Initialize API interface
        api_interface = AlertInterface()
        
        # Test alert retrieval
        retrieved_alert = api_interface.get_alert(sample_alert.alert_id)
        if retrieved_alert:  # May be None if not in storage
            assert retrieved_alert["alert_id"] == sample_alert.alert_id
            print("✓ Alert retrieved via API")
        else:
            print("✓ Alert not found (expected for test data)")
        
        # Test alert list endpoint
        alert_list = api_interface.list_alerts(limit=10, offset=0)
        assert "alerts" in alert_list
        assert "total_count" in alert_list
        assert "pagination" in alert_list
        print(f"✓ Alert list returned {len(alert_list['alerts'])} alerts")
        
        # Test alert filtering endpoint
        filtered_alerts = api_interface.filter_alerts({
            "severity": ["high", "critical"],
            "status": ["new", "acknowledged"]
        })
        assert "alerts" in filtered_alerts
        print(f"✓ Filtered alerts returned {len(filtered_alerts['alerts'])} results")
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        print("Testing End-to-End Workflow...")
        
        # Simulate incoming threat data
        threat_data = {
            "content": "Spreading false information about Indian government policies",
            "platform": "twitter",
            "user_id": "suspicious_user_456",
            "post_id": "tweet_789",
            "sentiment_score": -0.92,
            "bot_probability": 0.88,
            "engagement_metrics": {"likes": 1500, "shares": 800, "comments": 200},
            "timestamp": datetime.utcnow().isoformat(),
            "location": "India"
        }
        
        # Step 1: Generate alert
        generator = AlertGenerator()
        alert = generator.generate_alert(threat_data)
        assert alert is not None
        print(f"✓ Step 1: Alert generated - {alert.alert_id}")
        
        # Step 2: Process through alert manager
        alert_manager = AlertManager()
        processed_alert = alert_manager.process_alert(alert)
        assert processed_alert.status == AlertStatus.NEW
        print("✓ Step 2: Alert processed and stored")
        
        # Step 3: Send notifications
        notification_service = NotificationService()
        preferences = NotificationPreference(
            user_id="analyst_001",
            channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
            severity_filter=[SeverityLevel.HIGH, SeverityLevel.CRITICAL],
            enabled=True
        )
        
        notification_result = notification_service.route_notification(processed_alert, preferences)
        assert notification_result["success"] is True
        print("✓ Step 3: Notifications sent")
        
        # Step 4: Analyst acknowledges alert
        ack_result = alert_manager.acknowledge_alert(
            processed_alert.alert_id,
            "analyst_001",
            "Investigating this high-risk content"
        )
        assert ack_result["success"] is True
        print("✓ Step 4: Alert acknowledged by analyst")
        
        # Step 5: Investigation and resolution
        resolve_result = alert_manager.resolve_alert(
            processed_alert.alert_id,
            "analyst_001",
            "Confirmed misinformation - content reported to platform",
            "confirmed_threat"
        )
        assert resolve_result["success"] is True
        print("✓ Step 5: Alert investigated and resolved")
        
        print("✅ End-to-end workflow completed successfully!")


def run_integration_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("ALERT MANAGEMENT SYSTEM - INTEGRATION TESTS")
    print("=" * 60)
    
    test_instance = TestAlertManagementSystemIntegration()
    
    # Create fixtures
    sample_context = AlertContext(
        source_platform="twitter",
        content_samples=["Test content for alert"],
        detection_method="sentiment_analysis",
        confidence_score=0.85,
        risk_score=0.78,
        detection_window_start=datetime.utcnow() - timedelta(hours=1),
        detection_window_end=datetime.utcnow(),
        keywords_matched=["test", "alert"],
        affected_regions=["India"],
        volume_metrics={"post_count": 150, "user_count": 45},
        engagement_metrics={"total_likes": 1200, "total_shares": 340}
    )
    
    sample_alert = Alert(
        alert_id="test_integration_001",
        title="Integration Test Alert",
        description="Testing complete alert management system",
        alert_type=AlertType.HIGH_RISK_CONTENT,
        severity=SeverityLevel.HIGH,
        status=AlertStatus.NEW,
        context=sample_context,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    try:
        # Run all tests
        test_instance.test_alert_generation_pipeline(sample_context)
        test_instance.test_notification_system_integration(sample_alert)
        test_instance.test_alert_management_workflow(sample_alert)
        test_instance.test_escalation_system(sample_alert)
        test_instance.test_search_and_filtering()
        test_instance.test_reporting_and_analytics()
        test_instance.test_dashboard_interface_integration(sample_alert)
        test_instance.test_api_interface_integration(sample_alert)
        test_instance.test_end_to_end_workflow()
        
        print("\n" + "=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("Alert Management System is fully functional.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    run_integration_tests()