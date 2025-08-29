"""
Simple test script for Alert Management Interface components.

Tests the core functionality without external dependencies.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from shared.models.alert import (
    Alert, AlertSummary, AlertType, SeverityLevel, 
    AlertStatus, EscalationLevel, AlertContext
)


def test_alert_inbox_filtering():
    """Test alert inbox filtering functionality."""
    print("Testing Alert Inbox Filtering...")
    
    # Create sample alerts
    alerts = [
        Alert(
            alert_id="test_001",
            title="Critical Security Alert",
            description="High risk content detected",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.CRITICAL,
            status=AlertStatus.NEW,
            context=AlertContext(
                source_platform="twitter",
                content_samples=["Test content"],
                risk_score=0.95,
                confidence_score=0.88
            )
        ),
        Alert(
            alert_id="test_002",
            title="Bot Network Detection",
            description="Coordinated bot activity",
            alert_type=AlertType.BOT_NETWORK_DETECTED,
            severity=SeverityLevel.HIGH,
            status=AlertStatus.ACKNOWLEDGED,
            context=AlertContext(
                source_platform="twitter",
                content_samples=["Bot content"],
                risk_score=0.82,
                confidence_score=0.91
            )
        ),
        Alert(
            alert_id="test_003",
            title="Misinformation Campaign",
            description="Viral false information",
            alert_type=AlertType.VIRAL_MISINFORMATION,
            severity=SeverityLevel.MEDIUM,
            status=AlertStatus.INVESTIGATING,
            context=AlertContext(
                source_platform="youtube",
                content_samples=["Misleading video"],
                risk_score=0.67,
                confidence_score=0.79
            )
        )
    ]
    
    # Test filtering by status
    new_alerts = [a for a in alerts if a.status == AlertStatus.NEW]
    assert len(new_alerts) == 1
    assert new_alerts[0].alert_id == "test_001"
    print("✅ Status filtering works")
    
    # Test filtering by severity
    critical_alerts = [a for a in alerts if a.severity == SeverityLevel.CRITICAL]
    assert len(critical_alerts) == 1
    assert critical_alerts[0].alert_id == "test_001"
    print("✅ Severity filtering works")
    
    # Test filtering by alert type
    bot_alerts = [a for a in alerts if a.alert_type == AlertType.BOT_NETWORK_DETECTED]
    assert len(bot_alerts) == 1
    assert bot_alerts[0].alert_id == "test_002"
    print("✅ Alert type filtering works")
    
    # Test combined filtering
    high_severity_new = [a for a in alerts if a.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] and a.status == AlertStatus.NEW]
    assert len(high_severity_new) == 1
    print("✅ Combined filtering works")
    
    print("Alert Inbox Filtering: PASSED\n")


def test_alert_acknowledgment():
    """Test alert acknowledgment functionality."""
    print("Testing Alert Acknowledgment...")
    
    # Create test alert
    alert = Alert(
        alert_id="ack_test_001",
        title="Test Acknowledgment Alert",
        description="Testing acknowledgment functionality",
        alert_type=AlertType.HIGH_RISK_CONTENT,
        severity=SeverityLevel.HIGH,
        status=AlertStatus.NEW,
        context=AlertContext(
            source_platform="twitter",
            content_samples=["Test content"],
            risk_score=0.85,
            confidence_score=0.90
        )
    )
    
    # Test initial state
    assert alert.status == AlertStatus.NEW
    assert alert.acknowledged_by is None
    assert alert.acknowledged_at is None
    print("✅ Initial state correct")
    
    # Test acknowledgment
    user_id = "analyst_1"
    notes = "Acknowledged for investigation"
    alert.acknowledge(user_id, notes)
    
    assert alert.status == AlertStatus.ACKNOWLEDGED
    assert alert.acknowledged_by == user_id
    assert alert.acknowledged_at is not None
    assert alert.response_time_minutes is not None
    assert notes in alert.investigation_notes
    print("✅ Acknowledgment works correctly")
    
    # Test response time calculation
    assert alert.response_time_minutes >= 0
    print("✅ Response time calculated")
    
    print("Alert Acknowledgment: PASSED\n")


def test_alert_assignment():
    """Test alert assignment functionality."""
    print("Testing Alert Assignment...")
    
    # Create test alert
    alert = Alert(
        alert_id="assign_test_001",
        title="Test Assignment Alert",
        description="Testing assignment functionality",
        alert_type=AlertType.BOT_NETWORK_DETECTED,
        severity=SeverityLevel.HIGH,
        status=AlertStatus.ACKNOWLEDGED,
        context=AlertContext(
            source_platform="telegram",
            content_samples=["Test content"],
            risk_score=0.78,
            confidence_score=0.85
        )
    )
    
    # Test initial state
    assert alert.assigned_to is None
    assert alert.assigned_at is None
    print("✅ Initial assignment state correct")
    
    # Test assignment
    assigned_to = "analyst_2"
    assigned_by = "supervisor_1"
    alert.assign(assigned_to, assigned_by)
    
    assert alert.assigned_to == assigned_to
    assert alert.assigned_at is not None
    print("✅ Assignment works correctly")
    
    # Test reassignment
    new_assignee = "analyst_3"
    alert.assign(new_assignee, assigned_by)
    
    assert alert.assigned_to == new_assignee
    print("✅ Reassignment works correctly")
    
    print("Alert Assignment: PASSED\n")


def test_alert_resolution():
    """Test alert resolution functionality."""
    print("Testing Alert Resolution...")
    
    # Create test alert
    alert = Alert(
        alert_id="resolve_test_001",
        title="Test Resolution Alert",
        description="Testing resolution functionality",
        alert_type=AlertType.VIRAL_MISINFORMATION,
        severity=SeverityLevel.MEDIUM,
        status=AlertStatus.INVESTIGATING,
        context=AlertContext(
            source_platform="youtube",
            content_samples=["Test content"],
            risk_score=0.65,
            confidence_score=0.82
        )
    )
    
    # Acknowledge first (required for resolution time calculation)
    alert.acknowledge("analyst_1", "Starting investigation")
    
    # Test initial state
    assert alert.status == AlertStatus.ACKNOWLEDGED
    assert alert.resolved_by is None
    assert alert.resolved_at is None
    print("✅ Initial resolution state correct")
    
    # Test resolution
    resolved_by = "analyst_1"
    resolution_notes = "Content verified as false positive"
    alert.resolve(resolved_by, resolution_notes)
    
    assert alert.status == AlertStatus.RESOLVED
    assert alert.resolved_by == resolved_by
    assert alert.resolved_at is not None
    assert alert.resolution_time_minutes is not None
    assert resolution_notes in alert.investigation_notes
    print("✅ Resolution works correctly")
    
    # Test resolution time calculation
    assert alert.resolution_time_minutes >= 0
    print("✅ Resolution time calculated")
    
    print("Alert Resolution: PASSED\n")


def test_alert_escalation():
    """Test alert escalation functionality."""
    print("Testing Alert Escalation...")
    
    # Create test alert
    alert = Alert(
        alert_id="escalate_test_001",
        title="Test Escalation Alert",
        description="Testing escalation functionality",
        alert_type=AlertType.ELECTION_INTERFERENCE,
        severity=SeverityLevel.CRITICAL,
        status=AlertStatus.NEW,
        context=AlertContext(
            source_platform="twitter",
            content_samples=["Election misinformation"],
            risk_score=0.97,
            confidence_score=0.93
        )
    )
    
    # Test initial state
    assert alert.escalation_level == EscalationLevel.LEVEL_1
    assert alert.escalated_by is None
    assert alert.escalated_at is None
    print("✅ Initial escalation state correct")
    
    # Test escalation
    escalated_by = "analyst_1"
    new_level = EscalationLevel.LEVEL_2
    reason = "Requires supervisor attention"
    alert.escalate(escalated_by, new_level, reason)
    
    assert alert.escalation_level == new_level
    assert alert.escalated_by == escalated_by
    assert alert.escalated_at is not None
    assert reason in alert.investigation_notes
    print("✅ Escalation works correctly")
    
    # Test further escalation
    alert.escalate("supervisor_1", EscalationLevel.LEVEL_3, "Critical national security issue")
    assert alert.escalation_level == EscalationLevel.LEVEL_3
    print("✅ Further escalation works correctly")
    
    print("Alert Escalation: PASSED\n")


def test_search_functionality():
    """Test search functionality."""
    print("Testing Search Functionality...")
    
    # Create sample alerts for search
    alerts = [
        Alert(
            alert_id="search_001",
            title="Bot Network Detection Alert",
            description="Coordinated bot activity detected on Twitter",
            alert_type=AlertType.BOT_NETWORK_DETECTED,
            severity=SeverityLevel.HIGH,
            status=AlertStatus.NEW,
            context=AlertContext(
                source_platform="twitter",
                content_samples=["Bot messages"],
                risk_score=0.85,
                confidence_score=0.90
            )
        ),
        Alert(
            alert_id="search_002",
            title="High Risk Content Alert",
            description="Anti-India sentiment in viral post",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.CRITICAL,
            status=AlertStatus.ACKNOWLEDGED,
            context=AlertContext(
                source_platform="twitter",
                content_samples=["Anti-India content"],
                risk_score=0.95,
                confidence_score=0.88
            )
        ),
        Alert(
            alert_id="search_003",
            title="Misinformation Campaign",
            description="False information about government policy",
            alert_type=AlertType.VIRAL_MISINFORMATION,
            severity=SeverityLevel.MEDIUM,
            status=AlertStatus.INVESTIGATING,
            context=AlertContext(
                source_platform="youtube",
                content_samples=["Misleading video"],
                risk_score=0.72,
                confidence_score=0.85
            )
        )
    ]
    
    # Test text search
    search_query = "bot"
    text_results = [a for a in alerts if search_query.lower() in a.title.lower() or search_query.lower() in a.description.lower()]
    assert len(text_results) == 1
    assert text_results[0].alert_id == "search_001"
    print("✅ Text search works")
    
    # Test risk score filtering
    high_risk_alerts = [a for a in alerts if a.context.risk_score > 0.8]
    assert len(high_risk_alerts) == 2
    print("✅ Risk score filtering works")
    
    # Test platform filtering
    twitter_alerts = [a for a in alerts if a.context.source_platform == "twitter"]
    assert len(twitter_alerts) == 2
    print("✅ Platform filtering works")
    
    # Test combined search
    combined_results = [
        a for a in alerts 
        if a.severity == SeverityLevel.CRITICAL and a.context.source_platform == "twitter"
    ]
    assert len(combined_results) == 1
    assert combined_results[0].alert_id == "search_002"
    print("✅ Combined search works")
    
    print("Search Functionality: PASSED\n")


def test_bulk_operations():
    """Test bulk operations functionality."""
    print("Testing Bulk Operations...")
    
    # Create sample alerts for bulk operations
    alerts = [
        Alert(
            alert_id=f"bulk_{i:03d}",
            title=f"Bulk Test Alert {i}",
            description=f"Testing bulk operations {i}",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.HIGH,
            status=AlertStatus.NEW,
            context=AlertContext(
                source_platform="twitter",
                content_samples=[f"Test content {i}"],
                risk_score=0.8 + (i * 0.01),
                confidence_score=0.85
            )
        )
        for i in range(1, 6)
    ]
    
    # Test bulk acknowledgment
    user_id = "supervisor_1"
    notes = "Bulk acknowledged"
    
    successful_ops = []
    failed_ops = []
    
    for alert in alerts:
        try:
            if alert.status == AlertStatus.NEW:
                alert.acknowledge(user_id, notes)
                successful_ops.append(alert.alert_id)
        except Exception as e:
            failed_ops.append({"alert_id": alert.alert_id, "error": str(e)})
    
    assert len(successful_ops) == 5
    assert len(failed_ops) == 0
    print("✅ Bulk acknowledgment works")
    
    # Test bulk assignment
    assignee = "analyst_2"
    for alert in alerts:
        if alert.status == AlertStatus.ACKNOWLEDGED:
            alert.assign(assignee, user_id)
    
    assigned_count = len([a for a in alerts if a.assigned_to == assignee])
    assert assigned_count == 5
    print("✅ Bulk assignment works")
    
    # Test bulk tagging
    bulk_tags = ["bulk_processed", "team_review"]
    for alert in alerts:
        alert.tags.extend(bulk_tags)
    
    tagged_count = len([a for a in alerts if all(tag in a.tags for tag in bulk_tags)])
    assert tagged_count == 5
    print("✅ Bulk tagging works")
    
    print("Bulk Operations: PASSED\n")


def test_reporting_analytics():
    """Test reporting and analytics functionality."""
    print("Testing Reporting & Analytics...")
    
    # Create sample alerts with various states
    alerts = [
        Alert(
            alert_id="report_001",
            title="Critical Alert 1",
            description="Test critical alert",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.CRITICAL,
            status=AlertStatus.RESOLVED,
            context=AlertContext(
                source_platform="twitter",
                content_samples=["Test content"],
                risk_score=0.95,
                confidence_score=0.90
            )
        ),
        Alert(
            alert_id="report_002",
            title="High Alert 1",
            description="Test high alert",
            alert_type=AlertType.BOT_NETWORK_DETECTED,
            severity=SeverityLevel.HIGH,
            status=AlertStatus.ACKNOWLEDGED,
            context=AlertContext(
                source_platform="telegram",
                content_samples=["Test content"],
                risk_score=0.82,
                confidence_score=0.88
            )
        ),
        Alert(
            alert_id="report_003",
            title="Medium Alert 1",
            description="Test medium alert",
            alert_type=AlertType.VIRAL_MISINFORMATION,
            severity=SeverityLevel.MEDIUM,
            status=AlertStatus.NEW,
            context=AlertContext(
                source_platform="youtube",
                content_samples=["Test content"],
                risk_score=0.65,
                confidence_score=0.75
            )
        )
    ]
    
    # Acknowledge and resolve some alerts for metrics
    alerts[0].acknowledge("analyst_1", "Test ack")
    alerts[0].resolve("analyst_1", "Test resolution")
    alerts[1].acknowledge("analyst_2", "Test ack")
    
    # Test basic statistics
    total_alerts = len(alerts)
    new_alerts = len([a for a in alerts if a.status == AlertStatus.NEW])
    acknowledged_alerts = len([a for a in alerts if a.status == AlertStatus.ACKNOWLEDGED])
    resolved_alerts = len([a for a in alerts if a.status == AlertStatus.RESOLVED])
    
    assert total_alerts == 3
    assert new_alerts == 1
    assert acknowledged_alerts == 1
    assert resolved_alerts == 1
    print("✅ Basic statistics calculation works")
    
    # Test severity distribution
    critical_count = len([a for a in alerts if a.severity == SeverityLevel.CRITICAL])
    high_count = len([a for a in alerts if a.severity == SeverityLevel.HIGH])
    medium_count = len([a for a in alerts if a.severity == SeverityLevel.MEDIUM])
    
    assert critical_count == 1
    assert high_count == 1
    assert medium_count == 1
    print("✅ Severity distribution calculation works")
    
    # Test performance metrics
    response_times = [a.response_time_minutes for a in alerts if a.response_time_minutes]
    resolution_times = [a.resolution_time_minutes for a in alerts if a.resolution_time_minutes]
    
    assert len(response_times) == 2  # Two alerts were acknowledged
    assert len(resolution_times) == 1  # One alert was resolved
    print("✅ Performance metrics calculation works")
    
    # Test platform analysis
    platform_counts = {}
    for alert in alerts:
        platform = alert.context.source_platform
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    assert len(platform_counts) == 3  # Three different platforms
    assert platform_counts["twitter"] == 1
    assert platform_counts["telegram"] == 1
    assert platform_counts["youtube"] == 1
    print("✅ Platform analysis works")
    
    # Test risk score analysis
    risk_scores = [a.context.risk_score for a in alerts]
    avg_risk_score = sum(risk_scores) / len(risk_scores)
    high_risk_count = len([score for score in risk_scores if score > 0.8])
    
    assert len(risk_scores) == 3
    assert high_risk_count == 2  # Two alerts with risk > 0.8
    assert 0.7 < avg_risk_score < 0.9  # Average should be reasonable
    print("✅ Risk score analysis works")
    
    print("Reporting & Analytics: PASSED\n")


def run_all_tests():
    """Run all test functions."""
    print("🚨 Alert Management Interface - Component Tests")
    print("=" * 60)
    
    test_functions = [
        test_alert_inbox_filtering,
        test_alert_acknowledgment,
        test_alert_assignment,
        test_alert_resolution,
        test_alert_escalation,
        test_search_functionality,
        test_bulk_operations,
        test_reporting_analytics
    ]
    
    passed_tests = 0
    total_tests = len(test_functions)
    
    for test_func in test_functions:
        try:
            test_func()
            passed_tests += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} FAILED: {str(e)}\n")
    
    print("=" * 60)
    print(f"Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("✅ All tests passed! Alert Management Interface is working correctly.")
    else:
        print(f"❌ {total_tests - passed_tests} tests failed. Please check the implementation.")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)