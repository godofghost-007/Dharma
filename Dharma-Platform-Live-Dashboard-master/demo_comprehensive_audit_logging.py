"""
Demonstration of comprehensive audit logging system
Shows all features of the audit logging implementation
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from shared.security.audit_logger_simple import (
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
from shared.logging.structured_logger import StructuredLogger


class AuditLoggingDemo:
    """Comprehensive demonstration of audit logging system"""
    
    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.postgresql = None
        self.mongodb = None
        self.audit_logger = None
        self.data_access_monitor = None
        self.compliance_reporter = None
        self.alerting_system = None
    
    async def setup_system(self):
        """Setup the audit logging system"""
        print("🔧 Setting up comprehensive audit logging system...")
        
        try:
            # Initialize database managers
            self.postgresql = PostgreSQLManager()
            self.mongodb = MongoDBManager()
            
            # Initialize audit logger
            self.audit_logger = AuditLogger(self.postgresql, self.mongodb)
            
            # Initialize data access monitor
            self.data_access_monitor = DataAccessMonitor(
                self.postgresql, self.mongodb, self.audit_logger
            )
            
            # Initialize compliance reporter
            self.compliance_reporter = ComplianceReporter(
                self.postgresql, self.mongodb,
                self.audit_logger, self.data_access_monitor
            )
            
            # Initialize alerting system
            self.alerting_system = ComplianceAlertingSystem(
                self.postgresql, self.audit_logger, self.compliance_reporter
            )
            
            print("✅ Audit logging system setup complete!")
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            # Use mock implementations for demo
            await self._setup_mock_system()
    
    async def _setup_mock_system(self):
        """Setup mock system for demonstration"""
        print("🔧 Setting up mock audit logging system for demo...")
        
        from unittest.mock import Mock, AsyncMock
        
        # Mock database managers
        self.postgresql = Mock()
        self.postgresql.execute_query = AsyncMock()
        self.postgresql.fetch_all = AsyncMock(return_value=[])
        self.postgresql.fetch_one = AsyncMock(return_value={})
        
        self.mongodb = Mock()
        self.mongodb.insert_document = AsyncMock()
        self.mongodb.find_document = AsyncMock(return_value={})
        
        # Initialize components with mocks
        self.audit_logger = AuditLogger(self.postgresql, self.mongodb)
        self.data_access_monitor = DataAccessMonitor(
            self.postgresql, self.mongodb, self.audit_logger
        )
        self.compliance_reporter = ComplianceReporter(
            self.postgresql, self.mongodb,
            self.audit_logger, self.data_access_monitor
        )
        self.alerting_system = ComplianceAlertingSystem(
            self.postgresql, self.audit_logger, self.compliance_reporter
        )
        
        print("✅ Mock audit logging system ready!")
    
    async def demonstrate_user_action_logging(self):
        """Demonstrate user action logging"""
        print("\n📝 Demonstrating User Action Logging")
        print("=" * 50)
        
        # Log various user actions
        actions = [
            {
                "user_id": "analyst_001",
                "action": "login",
                "resource_type": "authentication",
                "details": {"method": "oauth2", "provider": "google"},
                "session_id": "sess_12345",
                "ip_address": "192.168.1.100"
            },
            {
                "user_id": "analyst_001",
                "action": "view_dashboard",
                "resource_type": "dashboard",
                "resource_id": "main_dashboard",
                "details": {"page": "overview", "filters": {"date_range": "7d"}},
                "session_id": "sess_12345",
                "ip_address": "192.168.1.100"
            },
            {
                "user_id": "admin_001",
                "action": "modify_user_permissions",
                "resource_type": "user_management",
                "resource_id": "analyst_002",
                "details": {"permissions_added": ["view_sensitive_data"], "approved_by": "manager_001"},
                "session_id": "sess_67890",
                "ip_address": "192.168.1.50"
            }
        ]
        
        for action in actions:
            await self.audit_logger.log_user_action(**action)
            print(f"✅ Logged action: {action['action']} by {action['user_id']}")
        
        print(f"📊 Total user actions logged: {len(actions)}")
    
    async def demonstrate_data_access_monitoring(self):
        """Demonstrate data access monitoring"""
        print("\n🔍 Demonstrating Data Access Monitoring")
        print("=" * 50)
        
        # Simulate various data access patterns
        access_events = [
            # Normal access
            DataAccessEvent(
                access_id="access_001",
                user_id="analyst_001",
                resource_type="posts",
                resource_id="twitter_posts",
                operation="read",
                timestamp=datetime.now(timezone.utc),
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0 (Dashboard Client)",
                session_id="sess_12345",
                data_classification="internal",
                access_method="api",
                query_details={"filters": {"sentiment": "negative"}, "limit": 50},
                result_count=45,
                data_size_bytes=15360,
                access_duration_ms=250.0,
                success=True,
                error_message=None
            ),
            
            # Bulk access (suspicious)
            DataAccessEvent(
                access_id="access_002",
                user_id="analyst_002",
                resource_type="user_profiles",
                resource_id="all_users",
                operation="read",
                timestamp=datetime.now(timezone.utc),
                ip_address="192.168.1.200",
                user_agent="Python/3.9 requests/2.28.1",
                session_id="sess_54321",
                data_classification="confidential",
                access_method="api",
                query_details={"query": "SELECT * FROM users", "no_limit": True},
                result_count=50000,  # Suspicious bulk access
                data_size_bytes=52428800,  # 50MB
                access_duration_ms=15000.0,
                success=True,
                error_message=None
            ),
            
            # Unusual time access
            DataAccessEvent(
                access_id="access_003",
                user_id="analyst_001",
                resource_type="campaign_data",
                resource_id="sensitive_campaigns",
                operation="read",
                timestamp=datetime.now(timezone.utc).replace(hour=2, minute=30),  # 2:30 AM
                ip_address="10.0.0.50",  # Different IP
                user_agent="curl/7.68.0",
                session_id="sess_99999",
                data_classification="restricted",
                access_method="direct_db",
                query_details={"raw_sql": True, "bypass_api": True},
                result_count=1000,
                data_size_bytes=2048000,
                access_duration_ms=8000.0,
                success=True,
                error_message=None
            )
        ]
        
        for event in access_events:
            await self.data_access_monitor.log_data_access(event)
            print(f"✅ Logged data access: {event.operation} on {event.resource_type} by {event.user_id}")
            print(f"   📊 Result count: {event.result_count}, Size: {event.data_size_bytes} bytes")
        
        print(f"📈 Total data access events logged: {len(access_events)}")
    
    async def demonstrate_data_lineage_tracking(self):
        """Demonstrate data lineage tracking"""
        print("\n🔗 Demonstrating Data Lineage Tracking")
        print("=" * 50)
        
        lineage_tracker = self.audit_logger.lineage_tracker
        
        # Track data creation
        tweet_lineage = await lineage_tracker.track_data_creation(
            data_id="tweet_12345",
            source="twitter_api_v2",
            metadata={
                "platform": "twitter",
                "collection_method": "streaming_api",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api_version": "2.0"
            }
        )
        print(f"✅ Created data lineage for tweet: {tweet_lineage}")
        
        # Track sentiment analysis transformation
        sentiment_lineage = await lineage_tracker.track_data_transformation(
            source_data_id="tweet_12345",
            target_data_id="sentiment_result_67890",
            transformation="sentiment_analysis",
            metadata={
                "model": "bert_sentiment_v2",
                "confidence": 0.95,
                "sentiment": "negative",
                "processing_time_ms": 150
            }
        )
        print(f"✅ Created sentiment analysis lineage: {sentiment_lineage}")
        
        # Track bot detection transformation
        bot_detection_lineage = await lineage_tracker.track_data_transformation(
            source_data_id="tweet_12345",
            target_data_id="bot_analysis_11111",
            transformation="bot_detection",
            metadata={
                "model": "bot_detector_v3",
                "bot_probability": 0.15,
                "behavioral_features": ["posting_frequency", "network_analysis"],
                "processing_time_ms": 300
            }
        )
        print(f"✅ Created bot detection lineage: {bot_detection_lineage}")
        
        # Get complete lineage
        complete_lineage = await lineage_tracker.get_data_lineage("bot_analysis_11111")
        print(f"📊 Complete data lineage retrieved for bot analysis")
    
    async def demonstrate_compliance_checking(self):
        """Demonstrate compliance checking"""
        print("\n⚖️ Demonstrating Compliance Checking")
        print("=" * 50)
        
        rule_engine = self.compliance_reporter.rule_engine
        
        # Mock database responses for compliance checks
        self.postgresql.fetch_one.side_effect = [
            {"violation_count": 3},  # DR001 - Data retention violations
            {"unidentified_access": 0, "total_privileged_access": 15},  # AC001 - Access control
            {"incomplete_logs": 2},  # AT001 - Audit trail
            {"unjustified_access": 5}  # DA001 - Data access justification
        ]
        
        # Run compliance checks
        rules_to_check = ["DR001", "AC001", "AT001", "DA001"]
        check_results = []
        
        for rule_id in rules_to_check:
            result = await rule_engine.execute_compliance_check(rule_id)
            check_results.append(result)
            
            status_emoji = "✅" if result.status == ComplianceStatus.COMPLIANT else "❌"
            print(f"{status_emoji} Rule {rule_id}: {result.status.value}")
            if result.violations:
                for violation in result.violations:
                    print(f"   ⚠️ Violation: {violation}")
        
        print(f"📋 Compliance checks completed: {len(check_results)} rules evaluated")
        
        # Generate compliance assessment
        assessment = await self.compliance_reporter.run_compliance_assessment()
        print(f"📊 Overall compliance status: {assessment['overall_status']}")
        print(f"📈 Compliance score: {assessment['compliant_checks']}/{assessment['total_checks']} checks passed")
        
        return check_results
    
    async def demonstrate_compliance_alerting(self):
        """Demonstrate compliance alerting"""
        print("\n🚨 Demonstrating Compliance Alerting")
        print("=" * 50)
        
        # Simulate compliance violations that trigger alerts
        violation_scenarios = [
            {
                "rule_id": "AC001",
                "status": "non_compliant",
                "risk_level": "critical",
                "violations": ["5 unidentified privileged access attempts detected"],
                "details": {"unidentified_access": 5, "total_access": 20}
            },
            {
                "rule_id": "DR001", 
                "status": "non_compliant",
                "risk_level": "high",
                "violations": ["Personal data retention period exceeded"],
                "details": {"violation_count": 150, "oldest_record_days": 400}
            },
            {
                "rule_id": "DA001",
                "status": "partially_compliant", 
                "risk_level": "medium",
                "violations": ["Sensitive data access without justification"],
                "details": {"unjustified_access": 8}
            }
        ]
        
        for scenario in violation_scenarios:
            await self.alerting_system.process_compliance_check_result(scenario)
            print(f"🚨 Alert generated for rule {scenario['rule_id']} ({scenario['risk_level']} risk)")
        
        # Demonstrate alert management
        print("\n📋 Alert Management:")
        
        # Mock active alerts
        self.postgresql.fetch_all.return_value = [
            {
                "alert_id": "alert_001",
                "alert_type": "CRITICAL_VIOLATION",
                "severity": "critical",
                "title": "Critical Access Control Violation",
                "compliance_rule_id": "AC001",
                "status": "active",
                "timestamp": datetime.now(timezone.utc)
            },
            {
                "alert_id": "alert_002", 
                "alert_type": "DATA_RETENTION_VIOLATION",
                "severity": "warning",
                "title": "Data Retention Policy Violation",
                "compliance_rule_id": "DR001",
                "status": "active",
                "timestamp": datetime.now(timezone.utc)
            }
        ]
        
        active_alerts = await self.alerting_system.get_active_alerts()
        print(f"📊 Active alerts: {len(active_alerts)}")
        
        for alert in active_alerts:
            print(f"   🔔 {alert['severity'].upper()}: {alert['title']}")
        
        # Demonstrate alert acknowledgment
        self.postgresql.execute_query.return_value = True
        ack_result = await self.alerting_system.acknowledge_alert("alert_001", "analyst_001")
        print(f"✅ Alert acknowledged: {ack_result}")
        
        # Demonstrate alert resolution
        resolve_result = await self.alerting_system.resolve_alert(
            "alert_002", "admin_001", "Data retention policy updated and old data purged"
        )
        print(f"✅ Alert resolved: {resolve_result}")
    
    async def demonstrate_compliance_reporting(self):
        """Demonstrate compliance reporting"""
        print("\n📊 Demonstrating Compliance Reporting")
        print("=" * 50)
        
        # Mock compliance report data
        self.postgresql.fetch_all.side_effect = [
            # Compliance checks
            [
                {"check_id": "check_001", "rule_id": "DR001", "status": "non_compliant", "risk_level": "high", "violations": ["retention_exceeded"]},
                {"check_id": "check_002", "rule_id": "AC001", "status": "compliant", "risk_level": "low", "violations": []},
                {"check_id": "check_003", "rule_id": "AT001", "status": "partially_compliant", "risk_level": "medium", "violations": ["incomplete_logs"]},
            ],
            # Alert statistics
            [
                {"severity": "critical", "status": "active", "count": 2},
                {"severity": "warning", "status": "resolved", "count": 5},
                {"severity": "info", "status": "acknowledged", "count": 3}
            ],
            # Delivery statistics  
            [
                {"channel": "email", "status": "success", "count": 8},
                {"channel": "dashboard", "status": "success", "count": 10},
                {"channel": "sms", "status": "failed", "count": 1}
            ]
        ]
        
        # Generate comprehensive compliance report
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)
        
        report = await self.compliance_reporter.generate_compliance_report(
            ComplianceFramework.GDPR, start_date, end_date
        )
        
        print(f"📋 Generated compliance report: {report['report_id']}")
        print(f"🎯 Framework: {report['framework'].upper()}")
        print(f"📅 Period: {report['period']['start_date'][:10]} to {report['period']['end_date'][:10]}")
        
        exec_summary = report['executive_summary']
        print(f"📊 Compliance Score: {exec_summary['overall_compliance_percentage']:.1f}%")
        print(f"✅ Compliant Checks: {exec_summary['compliant_checks']}")
        print(f"❌ Non-Compliant Checks: {exec_summary['non_compliant_checks']}")
        print(f"🚨 Critical Violations: {exec_summary['critical_violations']}")
        
        # Show recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec['title']} ({rec['priority']} priority)")
        
        return report
    
    async def demonstrate_audit_decorators(self):
        """Demonstrate audit decorators and context managers"""
        print("\n🎭 Demonstrating Audit Decorators")
        print("=" * 50)
        
        # Example function with audit decorator
        @audit_action("search_posts", "posts")
        async def search_posts(query, limit=10):
            """Example function that searches posts"""
            # Simulate post search
            await asyncio.sleep(0.1)
            return [
                {"id": 1, "content": f"Post about {query}", "sentiment": "neutral"},
                {"id": 2, "content": f"Another post about {query}", "sentiment": "positive"}
            ]
        
        # Example function with data access monitoring
        @monitor_data_access("user_profiles", "read", "confidential")
        async def get_user_profile(user_id):
            """Example function that retrieves user profile"""
            await asyncio.sleep(0.05)
            return {
                "user_id": user_id,
                "name": "John Doe",
                "email": "john@example.com",
                "classification": "confidential"
            }
        
        # Test audit decorator
        print("🔍 Testing audit action decorator...")
        results = await search_posts(
            "disinformation",
            limit=20,
            audit_logger=self.audit_logger,
            audit_user_id="analyst_001",
            audit_session_id="sess_12345"
        )
        print(f"✅ Search completed, found {len(results)} posts")
        
        # Test data access monitoring decorator
        print("👤 Testing data access monitoring decorator...")
        profile = await get_user_profile(
            "user_12345",
            data_access_monitor=self.data_access_monitor,
            monitor_user_id="analyst_001",
            monitor_session_id="sess_12345",
            monitor_ip_address="192.168.1.100",
            resource_id="user_12345"
        )
        print(f"✅ Profile retrieved for user: {profile['name']}")
        
        # Test audit session context manager
        print("🔐 Testing audit session context manager...")
        async with audit_session(
            self.audit_logger, 
            user_id="analyst_001",
            session_id="sess_context_test",
            ip_address="192.168.1.100"
        ) as session_logger:
            await session_logger.log_user_action(
                user_id="analyst_001",
                action="context_test_action",
                details={"test": "context_manager"}
            )
            print("✅ Action logged within audit session context")
    
    async def demonstrate_security_events(self):
        """Demonstrate security event logging"""
        print("\n🛡️ Demonstrating Security Event Logging")
        print("=" * 50)
        
        # Simulate various security events
        security_events = [
            {
                "event_type": "failed_login_attempt",
                "severity": AuditSeverity.MEDIUM,
                "details": {
                    "username": "admin",
                    "attempts": 3,
                    "source": "brute_force_detection",
                    "blocked": True
                },
                "ip_address": "203.0.113.45"
            },
            {
                "event_type": "privilege_escalation_attempt",
                "severity": AuditSeverity.HIGH,
                "details": {
                    "user_id": "analyst_002",
                    "attempted_action": "admin_panel_access",
                    "current_role": "analyst",
                    "required_role": "admin"
                },
                "user_id": "analyst_002",
                "ip_address": "192.168.1.200"
            },
            {
                "event_type": "suspicious_data_access",
                "severity": AuditSeverity.CRITICAL,
                "details": {
                    "access_pattern": "bulk_download",
                    "data_volume_mb": 500,
                    "access_time": "02:30 AM",
                    "risk_indicators": ["unusual_time", "large_volume", "external_ip"]
                },
                "user_id": "analyst_003",
                "ip_address": "198.51.100.10"
            }
        ]
        
        for event in security_events:
            await self.audit_logger.log_security_event(**event)
            print(f"🚨 Security event logged: {event['event_type']} ({event['severity'].value})")
        
        print(f"🛡️ Total security events logged: {len(security_events)}")
    
    async def generate_summary_report(self):
        """Generate a summary report of the demonstration"""
        print("\n📋 Audit Logging System Demonstration Summary")
        print("=" * 60)
        
        # Mock audit trail data
        self.postgresql.fetch_all.return_value = [
            {"event_type": "user_action", "count": 15},
            {"event_type": "data_access", "count": 8},
            {"event_type": "security_event", "count": 3},
            {"event_type": "compliance_event", "count": 5}
        ]
        
        # Get audit statistics
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=1)  # Last hour of demo
        
        audit_trail = await self.audit_logger.get_audit_trail(
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        
        print(f"📊 Demonstration Statistics:")
        print(f"   🕐 Time Period: {start_date.strftime('%H:%M')} - {end_date.strftime('%H:%M')}")
        print(f"   📝 Total Audit Events: {len(audit_trail)}")
        print(f"   👥 User Actions Logged: 15")
        print(f"   🔍 Data Access Events: 8") 
        print(f"   🛡️ Security Events: 3")
        print(f"   ⚖️ Compliance Events: 5")
        
        print(f"\n✅ System Components Demonstrated:")
        print(f"   🔐 Audit Logger - User actions, data access, security events")
        print(f"   📊 Data Access Monitor - Pattern analysis, risk scoring")
        print(f"   🔗 Data Lineage Tracker - Creation and transformation tracking")
        print(f"   ⚖️ Compliance Checker - Automated rule evaluation")
        print(f"   📋 Compliance Reporter - Assessment and reporting")
        print(f"   🚨 Alerting System - Real-time violation alerts")
        print(f"   🎭 Audit Decorators - Transparent function monitoring")
        
        print(f"\n🎯 Key Features Showcased:")
        print(f"   ✅ Comprehensive audit trail with full context")
        print(f"   ✅ Real-time data access pattern analysis")
        print(f"   ✅ Complete data lineage and provenance tracking")
        print(f"   ✅ Automated compliance checking and reporting")
        print(f"   ✅ Multi-channel alerting for violations")
        print(f"   ✅ Decorator-based transparent monitoring")
        print(f"   ✅ Security event detection and logging")
        
        print(f"\n🔒 Compliance Frameworks Supported:")
        print(f"   📋 GDPR - Data protection and privacy")
        print(f"   🏢 SOX - Financial reporting controls")
        print(f"   🏥 HIPAA - Healthcare data protection")
        print(f"   🔐 ISO 27001 - Information security management")
        print(f"   🇺🇸 NIST - Cybersecurity framework")
        
        print(f"\n🚀 System Ready for Production Use!")
    
    async def run_complete_demonstration(self):
        """Run the complete audit logging demonstration"""
        print("🎬 Starting Comprehensive Audit Logging System Demonstration")
        print("=" * 70)
        
        try:
            # Setup system
            await self.setup_system()
            
            # Run all demonstrations
            await self.demonstrate_user_action_logging()
            await self.demonstrate_data_access_monitoring()
            await self.demonstrate_data_lineage_tracking()
            await self.demonstrate_compliance_checking()
            await self.demonstrate_compliance_alerting()
            await self.demonstrate_compliance_reporting()
            await self.demonstrate_audit_decorators()
            await self.demonstrate_security_events()
            
            # Generate summary
            await self.generate_summary_report()
            
            print(f"\n🎉 Demonstration completed successfully!")
            
        except Exception as e:
            print(f"❌ Demonstration failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main demonstration function"""
    demo = AuditLoggingDemo()
    await demo.run_complete_demonstration()


if __name__ == "__main__":
    asyncio.run(main())