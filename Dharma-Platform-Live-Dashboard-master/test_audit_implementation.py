"""
Test the comprehensive audit logging implementation
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta

from shared.security.audit_logger_simple import (
    AuditLogger, AuditEvent, AuditEventType, AuditSeverity,
    DataLineageTracker, ComplianceChecker, audit_action, audit_session
)


async def test_audit_logger_basic():
    """Test basic audit logger functionality"""
    print("🧪 Testing basic audit logger functionality...")
    
    # Create audit logger
    audit_logger = AuditLogger()
    
    # Test user action logging
    await audit_logger.log_user_action(
        user_id="test_user",
        action="test_action",
        resource_type="test_resource",
        details={"test": "data"}
    )
    
    # Test data access logging
    await audit_logger.log_data_access(
        user_id="test_user",
        resource_type="test_data",
        resource_id="data_123",
        action="read",
        data_classification="internal"
    )
    
    # Test security event logging
    await audit_logger.log_security_event(
        event_type="test_security_event",
        severity=AuditSeverity.MEDIUM,
        details={"test": "security_data"},
        user_id="test_user"
    )
    
    # Verify events were logged
    assert len(audit_logger.events) >= 3
    print(f"✅ Logged {len(audit_logger.events)} events successfully")
    
    # Test audit trail retrieval
    trail = await audit_logger.get_audit_trail(user_id="test_user")
    assert len(trail) >= 3
    print(f"✅ Retrieved {len(trail)} events from audit trail")
    
    return True


async def test_data_lineage_tracker():
    """Test data lineage tracking"""
    print("🧪 Testing data lineage tracker...")
    
    tracker = DataLineageTracker()
    
    # Test data creation tracking
    lineage_id = await tracker.track_data_creation(
        data_id="test_data_123",
        source="test_source",
        metadata={"test": "metadata"}
    )
    
    assert lineage_id is not None
    print(f"✅ Created data lineage: {lineage_id}")
    
    # Test data transformation tracking
    transform_id = await tracker.track_data_transformation(
        source_data_id="test_data_123",
        target_data_id="transformed_data_456",
        transformation="test_transformation",
        metadata={"transform": "metadata"}
    )
    
    assert transform_id is not None
    print(f"✅ Created transformation lineage: {transform_id}")
    
    # Test lineage retrieval
    lineage = await tracker.get_data_lineage("transformed_data_456")
    assert lineage is not None
    print(f"✅ Retrieved lineage data")
    
    return True


async def test_compliance_checker():
    """Test compliance checking"""
    print("🧪 Testing compliance checker...")
    
    audit_logger = AuditLogger()
    checker = ComplianceChecker(audit_logger)
    
    # Create a compliant event
    compliant_event = AuditEvent(
        event_id="compliant_001",
        event_type=AuditEventType.USER_ACTION,
        severity=AuditSeverity.LOW,
        timestamp=datetime.now(timezone.utc),
        user_id="test_user",
        session_id="test_session",
        ip_address="192.168.1.1",
        user_agent=None,
        resource_type="test_resource",
        resource_id="resource_123",
        action="test_action",
        details={"approved_by": "manager"},
        outcome="success",
        risk_score=0.1,
        compliance_tags=[],
        data_classification="internal",
        retention_period=365
    )
    
    violations = await checker.check_compliance(compliant_event)
    assert len(violations) == 0
    print("✅ Compliant event passed compliance check")
    
    # Create a non-compliant event (admin action without approval)
    non_compliant_event = AuditEvent(
        event_id="non_compliant_001",
        event_type=AuditEventType.ADMIN_ACTION,
        severity=AuditSeverity.HIGH,
        timestamp=datetime.now(timezone.utc),
        user_id="admin_user",
        session_id="admin_session",
        ip_address="192.168.1.1",
        user_agent=None,
        resource_type="system_config",
        resource_id="config_123",
        action="modify_config",
        details={},  # No approval
        outcome="success",
        risk_score=0.7,
        compliance_tags=[],
        data_classification="restricted",
        retention_period=365
    )
    
    violations = await checker.check_compliance(non_compliant_event)
    assert len(violations) > 0
    print(f"✅ Non-compliant event detected {len(violations)} violations")
    
    return True


async def test_audit_decorators():
    """Test audit decorators"""
    print("🧪 Testing audit decorators...")
    
    audit_logger = AuditLogger()
    
    @audit_action("test_decorated_action", "test_resource")
    async def test_function(value):
        return value * 2
    
    # Test successful function call
    result = await test_function(
        5,
        audit_logger=audit_logger,
        audit_user_id="test_user",
        audit_session_id="test_session"
    )
    
    assert result == 10
    print("✅ Decorated function executed successfully")
    
    # Test audit session context manager
    async with audit_session(
        audit_logger,
        user_id="test_user",
        session_id="context_session",
        ip_address="192.168.1.1"
    ) as session_logger:
        await session_logger.log_user_action(
            user_id="test_user",
            action="context_action",
            details={"context": "test"}
        )
    
    print("✅ Audit session context manager worked")
    
    return True


async def test_compliance_reporting():
    """Test compliance reporting"""
    print("🧪 Testing compliance reporting...")
    
    audit_logger = AuditLogger()
    
    # Add some test events
    await audit_logger.log_user_action("user1", "action1")
    await audit_logger.log_user_action("user2", "action2")
    await audit_logger.log_data_access("user1", "data", "data1", "read")
    
    # Generate compliance report
    start_date = datetime.now(timezone.utc) - timedelta(hours=1)
    end_date = datetime.now(timezone.utc)
    
    report = await audit_logger.generate_compliance_report(start_date, end_date)
    
    assert "report_period" in report
    assert "statistics" in report
    assert "top_users" in report
    assert "compliance_violations" in report
    
    print("✅ Compliance report generated successfully")
    
    return True


async def run_all_tests():
    """Run all audit logging tests"""
    print("🧪 Starting Comprehensive Audit Logging Tests")
    print("=" * 50)
    
    tests = [
        test_audit_logger_basic,
        test_data_lineage_tracker,
        test_compliance_checker,
        test_audit_decorators,
        test_compliance_reporting
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
                print(f"✅ {test.__name__} PASSED\n")
            else:
                failed += 1
                print(f"❌ {test.__name__} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED: {e}\n")
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Audit logging implementation is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)