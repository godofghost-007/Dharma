"""
Comprehensive tests for audit logging system
Tests all components of the audit logging implementation
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json
import uuid

from shared.security.audit_logger import (
    AuditLogger, AuditEvent, AuditEventType, AuditSeverity,
    DataLineageTracker, ComplianceChecker, audit_action, audit_session
)
from shared.security.data_access_monitor import (
    DataAccessMonitor, DataAccessEvent, AccessPattern, AccessPatternAnalyzer,
    monitor_data_access
)
from shared.security.compliance_reporter import (
    ComplianceReporter, ComplianceRule, ComplianceFramework, ComplianceStatus,
    ComplianceRuleEngine, ComplianceCheckResult
)
from shared.security.compliance_alerting import (
    ComplianceAlertingSystem, ComplianceAlert, AlertSeverity, AlertChannel,
    AlertRule, AlertThrottler, AlertDeliveryService
)
from shared.database.postgresql import PostgreSQLManager
from shared.database.mongodb import MongoDBManager


class TestAuditLogger:
    """Test audit logging functionality"""
    
    @pytest.fixture
    async def audit_logger(self):
        """Create audit logger for testing"""
        postgresql_mock = Mock(spec=PostgreSQLManager)
        postgresql_mock.execute_query = AsyncMock()
        postgresql_mock.fetch_all = AsyncMock()
        postgresql_mock.fetch_one = AsyncMock()
        
        mongodb_mock = Mock(spec=MongoDBManager)
        mongodb_mock.insert_document = AsyncMock()
        mongodb_mock.find_document = AsyncMock()
        
        logger = AuditLogger(postgresql_mock, mongodb_mock)
        return logger
    
    @pytest.mark.asyncio
    async def test_log_user_action(self, audit_logger):
        """Test logging user actions"""
        await audit_logger.log_user_action(
            user_id="user123",
            action="login",
            resource_type="authentication",
            details={"method": "password"},
            session_id="session123",
            ip_address="192.168.1.1"
        )
        
        # Verify PostgreSQL call
        audit_logger.postgresql.execute_query.assert_called()
        
        # Verify MongoDB call
        audit_logger.mongodb.insert_document.assert_called()
    
    @pytest.mark.asyncio
    async def test_log_data_access(self, audit_logger):
        """Test logging data access events"""
        await audit_logger.log_data_access(
            user_id="user123",
            resource_type="posts",
            resource_id="post456",
            action="read",
            data_classification="confidential",
            details={"query": "SELECT * FROM posts WHERE id = 456"}
        )
        
        # Verify calls were made
        audit_logger.postgresql.execute_query.assert_called()
        audit_logger.mongodb.insert_document.assert_called()
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, audit_logger):
        """Test logging security events"""
        await audit_logger.log_security_event(
            event_type="failed_login_attempt",
            severity=AuditSeverity.HIGH,
            details={"attempts": 5, "user": "admin"},
            user_id="user123",
            ip_address="192.168.1.100"
        )
        
        # Verify calls were made
        audit_logger.postgresql.execute_query.assert_called()
        audit_logger.mongodb.insert_document.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_audit_trail(self, audit_logger):
        """Test retrieving audit trail"""
        # Mock return data
        audit_logger.postgresql.fetch_all.return_value = [
            {
                "event_id": "event123",
                "user_id": "user123",
                "action": "login",
                "timestamp": datetime.now(timezone.utc)
            }
        ]
        
        result = await audit_logger.get_audit_trail(
            user_id="user123",
            start_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        assert len(result) == 1
        assert result[0]["user_id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, audit_logger):
        """Test generating compliance reports"""
        # Mock return data
        audit_logger.postgresql.fetch_all.return_value = [
            {"event_type": "user_action", "severity": "low", "count": 100, "violations": 0}
        ]
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        report = await audit_logger.generate_compliance_report(start_date, end_date)
        
        assert "report_period" in report
        assert "statistics" in report
        assert "generated_at" in report


class TestDataLineageTracker:
    """Test data lineage tracking"""
    
    @pytest.fixture
    def lineage_tracker(self):
        """Create lineage tracker for testing"""
        mongodb_mock = Mock(spec=MongoDBManager)
        mongodb_mock.insert_document = AsyncMock()
        mongodb_mock.find_document = AsyncMock()
        
        return DataLineageTracker(mongodb_mock)
    
    @pytest.mark.asyncio
    async def test_track_data_creation(self, lineage_tracker):
        """Test tracking data creation"""
        lineage_id = await lineage_tracker.track_data_creation(
            data_id="data123",
            source="twitter_api",
            metadata={"platform": "twitter", "type": "tweet"}
        )
        
        assert lineage_id is not None
        lineage_tracker.mongodb.insert_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_data_transformation(self, lineage_tracker):
        """Test tracking data transformation"""
        # Mock parent lineage
        lineage_tracker.mongodb.find_document.return_value = {
            "lineage_id": "parent123",
            "transformations": ["sentiment_analysis"]
        }
        
        lineage_id = await lineage_tracker.track_data_transformation(
            source_data_id="data123",
            target_data_id="processed456",
            transformation="bot_detection",
            metadata={"model": "bot_detector_v1"}
        )
        
        assert lineage_id is not None
        lineage_tracker.mongodb.insert_document.assert_called()


class TestComplianceChecker:
    """Test compliance checking functionality"""
    
    @pytest.fixture
    def compliance_checker(self):
        """Create compliance checker for testing"""
        audit_logger_mock = Mock()
        audit_logger_mock.log_event = AsyncMock()
        
        return ComplianceChecker(audit_logger_mock)
    
    @pytest.mark.asyncio
    async def test_check_compliance_data_retention(self, compliance_checker):
        """Test data retention compliance check"""
        event = AuditEvent(
            event_id="event123",
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.LOW,
            timestamp=datetime.now(timezone.utc),
            user_id="user123",
            session_id=None,
            ip_address=None,
            user_agent=None,
            resource_type="personal_data",
            resource_id="data123",
            action="access",
            details={},
            outcome="success",
            risk_score=0.1,
            compliance_tags=[],
            data_classification="personal",
            retention_period=300  # Less than required 365 days
        )
        
        violations = await compliance_checker.check_compliance(event)
        
        assert len(violations) > 0
        assert "retention period too short" in violations[0].lower()
    
    @pytest.mark.asyncio
    async def test_check_compliance_admin_action(self, compliance_checker):
        """Test admin action compliance check"""
        event = AuditEvent(
            event_id="event123",
            event_type=AuditEventType.ADMIN_ACTION,
            severity=AuditSeverity.HIGH,
            timestamp=datetime.now(timezone.utc),
            user_id="admin123",
            session_id=None,
            ip_address=None,
            user_agent=None,
            resource_type="system",
            resource_id="config",
            action="modify_config",
            details={},  # No approval
            outcome="success",
            risk_score=0.5,
            compliance_tags=[],
            data_classification="restricted",
            retention_period=365
        )
        
        violations = await compliance_checker.check_compliance(event)
        
        assert len(violations) > 0
        assert "requires approval" in violations[0].lower()


class TestDataAccessMonitor:
    """Test data access monitoring"""
    
    @pytest.fixture
    async def data_access_monitor(self):
        """Create data access monitor for testing"""
        postgresql_mock = Mock(spec=PostgreSQLManager)
        postgresql_mock.execute_query = AsyncMock()
        postgresql_mock.fetch_all = AsyncMock()
        postgresql_mock.fetch_one = AsyncMock()
        
        mongodb_mock = Mock(spec=MongoDBManager)
        mongodb_mock.insert_document = AsyncMock()
        
        audit_logger_mock = Mock()
        audit_logger_mock.log_data_access = AsyncMock()
        audit_logger_mock.log_security_event = AsyncMock()
        
        monitor = DataAccessMonitor(postgresql_mock, mongodb_mock, audit_logger_mock)
        return monitor
    
    @pytest.mark.asyncio
    async def test_log_data_access_normal(self, data_access_monitor):
        """Test logging normal data access"""
        access_event = DataAccessEvent(
            access_id="access123",
            user_id="user123",
            resource_type="posts",
            resource_id="post456",
            operation="read",
            timestamp=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            session_id="session123",
            data_classification="internal",
            access_method="api",
            query_details={"limit": 10},
            result_count=10,
            data_size_bytes=1024,
            access_duration_ms=150.0,
            success=True,
            error_message=None
        )
        
        await data_access_monitor.log_data_access(access_event)
        
        # Verify calls were made
        data_access_monitor.postgresql.execute_query.assert_called()
        data_access_monitor.mongodb.insert_document.assert_called()
        data_access_monitor.audit_logger.log_data_access.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_access_summary(self, data_access_monitor):
        """Test getting access summary"""
        # Mock return data
        data_access_monitor.postgresql.fetch_one.return_value = {
            "total_accesses": 100,
            "unique_users": 10,
            "resource_types_accessed": 5,
            "avg_risk_score": 0.2,
            "successful_accesses": 95,
            "failed_accesses": 5
        }
        
        data_access_monitor.postgresql.fetch_all.return_value = [
            {"pattern": "normal", "count": 90},
            {"pattern": "suspicious", "count": 10}
        ]
        
        summary = await data_access_monitor.get_access_summary(
            user_id="user123",
            start_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        assert "statistics" in summary
        assert "pattern_distribution" in summary
        assert summary["statistics"]["total_accesses"] == 100


class TestAccessPatternAnalyzer:
    """Test access pattern analysis"""
    
    @pytest.fixture
    def pattern_analyzer(self):
        """Create pattern analyzer for testing"""
        postgresql_mock = Mock(spec=PostgreSQLManager)
        postgresql_mock.fetch_all = AsyncMock()
        postgresql_mock.fetch_one = AsyncMock()
        
        return AccessPatternAnalyzer(postgresql_mock)
    
    @pytest.mark.asyncio
    async def test_analyze_bulk_access_pattern(self, pattern_analyzer):
        """Test bulk access pattern detection"""
        # Mock baseline data
        pattern_analyzer.postgresql.fetch_one.return_value = {
            "avg_result_count": 50
        }
        
        access_event = DataAccessEvent(
            access_id="access123",
            user_id="user123",
            resource_type="posts",
            resource_id="bulk_query",
            operation="read",
            timestamp=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent=None,
            session_id="session123",
            data_classification="internal",
            access_method="api",
            query_details={},
            result_count=1000,  # Much higher than baseline
            data_size_bytes=1024000,
            access_duration_ms=5000.0,
            success=True,
            error_message=None
        )
        
        patterns = await pattern_analyzer.analyze_access_pattern(access_event)
        
        assert AccessPattern.BULK_ACCESS in patterns


class TestComplianceRuleEngine:
    """Test compliance rule engine"""
    
    @pytest.fixture
    def rule_engine(self):
        """Create rule engine for testing"""
        postgresql_mock = Mock(spec=PostgreSQLManager)
        postgresql_mock.fetch_one = AsyncMock()
        
        return ComplianceRuleEngine(postgresql_mock)
    
    @pytest.mark.asyncio
    async def test_execute_compliance_check_data_retention(self, rule_engine):
        """Test data retention compliance check"""
        # Mock query result showing violations
        rule_engine.postgresql.fetch_one.return_value = {
            "violation_count": 5
        }
        
        result = await rule_engine.execute_compliance_check("DR001")
        
        assert result.rule_id == "DR001"
        assert result.status == ComplianceStatus.NON_COMPLIANT
        assert len(result.violations) > 0
    
    @pytest.mark.asyncio
    async def test_execute_compliance_check_access_control(self, rule_engine):
        """Test access control compliance check"""
        # Mock query result showing no violations
        rule_engine.postgresql.fetch_one.return_value = {
            "unidentified_access": 0,
            "total_privileged_access": 10
        }
        
        result = await rule_engine.execute_compliance_check("AC001")
        
        assert result.rule_id == "AC001"
        assert result.status == ComplianceStatus.COMPLIANT
        assert len(result.violations) == 0
    
    def test_add_custom_rule(self, rule_engine):
        """Test adding custom compliance rule"""
        custom_rule = ComplianceRule(
            rule_id="CUSTOM001",
            framework=ComplianceFramework.CUSTOM,
            category="custom_category",
            title="Custom Rule",
            description="Custom compliance rule for testing",
            requirement="Custom requirement",
            severity="medium",
            automated_check=True,
            check_query="SELECT COUNT(*) as count FROM test_table",
            remediation_steps=["Fix the issue"],
            evidence_required=["test_evidence"]
        )
        
        rule_engine.add_custom_rule(custom_rule)
        
        assert "CUSTOM001" in rule_engine.rules
        assert rule_engine.rules["CUSTOM001"].title == "Custom Rule"


class TestComplianceReporter:
    """Test compliance reporting"""
    
    @pytest.fixture
    async def compliance_reporter(self):
        """Create compliance reporter for testing"""
        postgresql_mock = Mock(spec=PostgreSQLManager)
        postgresql_mock.execute_query = AsyncMock()
        postgresql_mock.fetch_all = AsyncMock()
        postgresql_mock.fetch_one = AsyncMock()
        
        mongodb_mock = Mock(spec=MongoDBManager)
        
        audit_logger_mock = Mock()
        audit_logger_mock.generate_compliance_report = AsyncMock(return_value={
            "statistics": [],
            "top_users": [],
            "compliance_violations": []
        })
        
        data_access_monitor_mock = Mock()
        data_access_monitor_mock.get_access_summary = AsyncMock(return_value={
            "statistics": {},
            "pattern_distribution": []
        })
        
        reporter = ComplianceReporter(
            postgresql_mock, mongodb_mock, 
            audit_logger_mock, data_access_monitor_mock
        )
        return reporter
    
    @pytest.mark.asyncio
    async def test_run_compliance_assessment(self, compliance_reporter):
        """Test running compliance assessment"""
        # Mock rule engine methods
        with patch.object(compliance_reporter.rule_engine, 'get_all_rules') as mock_get_rules:
            with patch.object(compliance_reporter.rule_engine, 'execute_compliance_check') as mock_execute:
                # Setup mocks
                mock_get_rules.return_value = [
                    compliance_reporter.rule_engine.rules["DR001"],
                    compliance_reporter.rule_engine.rules["AC001"]
                ]
                
                mock_execute.return_value = ComplianceCheckResult(
                    check_id="check123",
                    rule_id="DR001",
                    status=ComplianceStatus.COMPLIANT,
                    timestamp=datetime.now(timezone.utc),
                    details={},
                    evidence=[],
                    violations=[],
                    remediation_required=False,
                    risk_level="low"
                )
                
                assessment = await compliance_reporter.run_compliance_assessment()
                
                assert "assessment_id" in assessment
                assert "overall_status" in assessment
                assert "total_checks" in assessment
                assert assessment["total_checks"] == 2
    
    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, compliance_reporter):
        """Test generating compliance report"""
        # Mock database returns
        compliance_reporter.postgresql.fetch_all.return_value = [
            {
                "check_id": "check123",
                "rule_id": "DR001",
                "status": "compliant",
                "risk_level": "low",
                "violations": []
            }
        ]
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        report = await compliance_reporter.generate_compliance_report(
            ComplianceFramework.GDPR, start_date, end_date
        )
        
        assert "report_id" in report
        assert "framework" in report
        assert "executive_summary" in report
        assert "detailed_findings" in report
        assert report["framework"] == "gdpr"


class TestComplianceAlertingSystem:
    """Test compliance alerting system"""
    
    @pytest.fixture
    async def alerting_system(self):
        """Create alerting system for testing"""
        postgresql_mock = Mock(spec=PostgreSQLManager)
        postgresql_mock.execute_query = AsyncMock()
        postgresql_mock.fetch_all = AsyncMock()
        postgresql_mock.fetch_one = AsyncMock()
        
        audit_logger_mock = Mock()
        audit_logger_mock.log_security_event = AsyncMock()
        audit_logger_mock.log_user_action = AsyncMock()
        
        compliance_reporter_mock = Mock()
        compliance_reporter_mock.rule_engine = Mock()
        compliance_reporter_mock.rule_engine.rules = {}
        
        system = ComplianceAlertingSystem(
            postgresql_mock, audit_logger_mock, compliance_reporter_mock
        )
        return system
    
    @pytest.mark.asyncio
    async def test_process_compliance_check_result_critical(self, alerting_system):
        """Test processing critical compliance violation"""
        check_result = {
            "rule_id": "AC001",
            "status": "non_compliant",
            "risk_level": "critical",
            "violations": ["Unidentified privileged access"],
            "details": {"unidentified_access": 5}
        }
        
        with patch.object(alerting_system, '_deliver_alert') as mock_deliver:
            with patch.object(alerting_system, '_store_alert') as mock_store:
                await alerting_system.process_compliance_check_result(check_result)
                
                # Should generate alert for critical violation
                mock_deliver.assert_called()
                mock_store.assert_called()
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, alerting_system):
        """Test acknowledging an alert"""
        # Mock successful update
        alerting_system.postgresql.execute_query.return_value = True
        
        result = await alerting_system.acknowledge_alert("alert123", "user123")
        
        assert result is True
        alerting_system.audit_logger.log_user_action.assert_called()
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, alerting_system):
        """Test resolving an alert"""
        # Mock successful update
        alerting_system.postgresql.execute_query.return_value = True
        
        result = await alerting_system.resolve_alert(
            "alert123", "user123", "Issue fixed"
        )
        
        assert result is True
        alerting_system.audit_logger.log_user_action.assert_called()


class TestAlertThrottler:
    """Test alert throttling functionality"""
    
    def test_should_send_alert_first_time(self):
        """Test sending alert for the first time"""
        throttler = AlertThrottler()
        
        result = throttler.should_send_alert("test_alert", 60)
        
        assert result is True
    
    def test_should_not_send_alert_within_throttle_period(self):
        """Test not sending alert within throttle period"""
        throttler = AlertThrottler()
        
        # First alert should be sent
        result1 = throttler.should_send_alert("test_alert", 60)
        assert result1 is True
        
        # Second alert within throttle period should not be sent
        result2 = throttler.should_send_alert("test_alert", 60)
        assert result2 is False
    
    def test_reset_throttle(self):
        """Test resetting throttle"""
        throttler = AlertThrottler()
        
        # Send first alert
        throttler.should_send_alert("test_alert", 60)
        
        # Reset throttle
        throttler.reset_throttle("test_alert")
        
        # Should be able to send alert again
        result = throttler.should_send_alert("test_alert", 60)
        assert result is True


class TestAlertDeliveryService:
    """Test alert delivery service"""
    
    @pytest.fixture
    def delivery_service(self):
        """Create delivery service for testing"""
        return AlertDeliveryService()
    
    @pytest.mark.asyncio
    async def test_deliver_alert_multiple_channels(self, delivery_service):
        """Test delivering alert through multiple channels"""
        alert = ComplianceAlert(
            alert_id="alert123",
            alert_type="CRITICAL_VIOLATION",
            severity=AlertSeverity.CRITICAL,
            title="Critical Compliance Violation",
            description="Test violation",
            compliance_rule_id="AC001",
            framework=ComplianceFramework.ISO27001,
            violation_details={},
            affected_resources=[],
            remediation_steps=["Fix issue"],
            escalation_required=True,
            timestamp=datetime.now(timezone.utc),
            expires_at=None
        )
        
        channels = [AlertChannel.EMAIL, AlertChannel.DASHBOARD]
        
        results = await delivery_service.deliver_alert(alert, channels)
        
        assert len(results) == 2
        assert "email" in results
        assert "dashboard" in results
        assert results["email"]["success"] is True
        assert results["dashboard"]["success"] is True


class TestAuditDecorators:
    """Test audit decorators and context managers"""
    
    @pytest.mark.asyncio
    async def test_audit_action_decorator_success(self):
        """Test audit action decorator on successful function"""
        
        @audit_action("test_action", "test_resource")
        async def test_function(value):
            return value * 2
        
        # Mock audit logger
        with patch('shared.security.audit_logger.PostgreSQLManager') as mock_pg:
            with patch('shared.security.audit_logger.MongoDBManager') as mock_mongo:
                mock_audit_logger = Mock()
                mock_audit_logger.log_user_action = AsyncMock()
                
                result = await test_function(
                    5,
                    audit_logger=mock_audit_logger,
                    audit_user_id="user123",
                    audit_session_id="session123"
                )
                
                assert result == 10
                mock_audit_logger.log_user_action.assert_called()
    
    @pytest.mark.asyncio
    async def test_audit_action_decorator_failure(self):
        """Test audit action decorator on failed function"""
        
        @audit_action("test_action", "test_resource")
        async def failing_function():
            raise ValueError("Test error")
        
        # Mock audit logger
        mock_audit_logger = Mock()
        mock_audit_logger.log_user_action = AsyncMock()
        
        with pytest.raises(ValueError):
            await failing_function(
                audit_logger=mock_audit_logger,
                audit_user_id="user123"
            )
        
        # Should log failure
        mock_audit_logger.log_user_action.assert_called()
        call_args = mock_audit_logger.log_user_action.call_args
        assert call_args[1]["outcome"] == "failure"
    
    @pytest.mark.asyncio
    async def test_monitor_data_access_decorator(self):
        """Test data access monitoring decorator"""
        
        @monitor_data_access("posts", "read", "internal")
        async def get_posts():
            return [{"id": 1, "title": "Test Post"}]
        
        # Mock monitor
        mock_monitor = Mock()
        mock_monitor.log_data_access = AsyncMock()
        
        result = await get_posts(
            data_access_monitor=mock_monitor,
            monitor_user_id="user123",
            monitor_session_id="session123",
            resource_id="posts_table"
        )
        
        assert len(result) == 1
        mock_monitor.log_data_access.assert_called()


# Integration test
class TestAuditLoggingIntegration:
    """Integration tests for the complete audit logging system"""
    
    @pytest.mark.asyncio
    async def test_complete_audit_workflow(self):
        """Test complete audit logging workflow"""
        # This would be a more comprehensive integration test
        # that tests the entire flow from data access to compliance reporting
        
        # Mock all dependencies
        postgresql_mock = Mock(spec=PostgreSQLManager)
        postgresql_mock.execute_query = AsyncMock()
        postgresql_mock.fetch_all = AsyncMock(return_value=[])
        postgresql_mock.fetch_one = AsyncMock(return_value={})
        
        mongodb_mock = Mock(spec=MongoDBManager)
        mongodb_mock.insert_document = AsyncMock()
        mongodb_mock.find_document = AsyncMock(return_value={})
        
        # Create audit logger
        audit_logger = AuditLogger(postgresql_mock, mongodb_mock)
        
        # Create data access monitor
        data_access_monitor = DataAccessMonitor(
            postgresql_mock, mongodb_mock, audit_logger
        )
        
        # Create compliance reporter
        compliance_reporter = ComplianceReporter(
            postgresql_mock, mongodb_mock, 
            audit_logger, data_access_monitor
        )
        
        # Create alerting system
        alerting_system = ComplianceAlertingSystem(
            postgresql_mock, audit_logger, compliance_reporter
        )
        
        # Simulate data access event
        access_event = DataAccessEvent(
            access_id="access123",
            user_id="user123",
            resource_type="confidential_data",
            resource_id="data456",
            operation="read",
            timestamp=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent="TestAgent",
            session_id="session123",
            data_classification="confidential",
            access_method="api",
            query_details={"sensitive": True},
            result_count=1000,  # Large access
            data_size_bytes=1024000,
            access_duration_ms=5000.0,
            success=True,
            error_message=None
        )
        
        # Log the access event
        await data_access_monitor.log_data_access(access_event)
        
        # Verify audit logging was called
        audit_logger.postgresql.execute_query.assert_called()
        audit_logger.mongodb.insert_document.assert_called()
        
        # This integration test demonstrates how all components work together
        # In a real scenario, this would trigger compliance checks and potentially alerts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])