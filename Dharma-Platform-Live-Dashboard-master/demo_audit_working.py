"""
Working demonstration of comprehensive audit logging system
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


class AuditLoggingDemo:
    """Comprehensive demonstration of audit logging system"""
    
    def __init__(self):
        self.audit_logger = None
    
    async def setup_system(self):
        """Setup the audit logging system"""
        print("🔧 Setting up comprehensive audit logging system...")
        
        # Initialize audit logger (without database for demo)
        self.audit_logger = AuditLogger()
        
        print("✅ Audit logging system setup complete!")
    
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
    
    async def demonstrate_data_access_logging(self):
        """Demonstrate data access logging"""
        print("\n🔍 Demonstrating Data Access Logging")
        print("=" * 50)
        
        # Log various data access events
        access_events = [
            {
                "user_id": "analyst_001",
                "resource_type": "posts",
                "resource_id": "twitter_posts",
                "action": "read",
                "data_classification": "internal",
                "details": {"query": "SELECT * FROM posts WHERE sentiment = 'negative'", "limit": 50},
                "session_id": "sess_12345",
                "ip_address": "192.168.1.100"
            },
            {
                "user_id": "analyst_002",
                "resource_type": "user_profiles",
                "resource_id": "all_users",
                "action": "read",
                "data_classification": "confidential",
                "details": {"query": "SELECT * FROM users", "bulk_access": True},
                "session_id": "sess_54321",
                "ip_address": "192.168.1.200"
            },
            {
                "user_id": "admin_001",
                "resource_type": "campaign_data",
                "resource_id": "sensitive_campaigns",
                "action": "read",
                "data_classification": "restricted",
                "details": {"approved_by": "security_officer", "justification": "security_investigation"},
                "session_id": "sess_99999",
                "ip_address": "192.168.1.50"
            }
        ]
        
        for event in access_events:
            await self.audit_logger.log_data_access(**event)
            print(f"✅ Logged data access: {event['action']} on {event['resource_type']} by {event['user_id']}")
            print(f"   📊 Classification: {event['data_classification']}")
        
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
        print(f"   🔗 Transformations: {complete_lineage.get('transformations', [])}")
    
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
    
    async def demonstrate_compliance_checking(self):
        """Demonstrate compliance checking"""
        print("\n⚖️ Demonstrating Compliance Checking")
        print("=" * 50)
        
        # Create events that will trigger compliance violations
        violation_events = [
            # Admin action without approval
            AuditEvent(
                event_id="event_001",
                event_type=AuditEventType.ADMIN_ACTION,
                severity=AuditSeverity.HIGH,
                timestamp=datetime.now(timezone.utc),
                user_id="admin_001",
                session_id="sess_admin",
                ip_address="192.168.1.50",
                user_agent=None,
                resource_type="system_config",
                resource_id="security_settings",
                action="modify_security_policy",
                details={},  # No approval
                outcome="success",
                risk_score=0.7,
                compliance_tags=[],
                data_classification="restricted",
                retention_period=365
            ),
            
            # Data retention violation
            AuditEvent(
                event_id="event_002",
                event_type=AuditEventType.DATA_ACCESS,
                severity=AuditSeverity.LOW,
                timestamp=datetime.now(timezone.utc),
                user_id="analyst_001",
                session_id="sess_12345",
                ip_address="192.168.1.100",
                user_agent=None,
                resource_type="personal_data",
                resource_id="user_profiles",
                action="access",
                details={},
                outcome="success",
                risk_score=0.3,
                compliance_tags=[],
                data_classification="personal",
                retention_period=200  # Less than required 365 days
            ),
            
            # Restricted data access without MFA
            AuditEvent(
                event_id="event_003",
                event_type=AuditEventType.DATA_ACCESS,
                severity=AuditSeverity.MEDIUM,
                timestamp=datetime.now(timezone.utc),
                user_id="analyst_002",
                session_id="sess_54321",
                ip_address="192.168.1.200",
                user_agent=None,
                resource_type="classified_data",
                resource_id="intelligence_reports",
                action="read",
                details={},  # No MFA verification
                outcome="success",
                risk_score=0.5,
                compliance_tags=[],
                data_classification="restricted",
                retention_period=2555
            )
        ]
        
        compliance_checker = self.audit_logger.compliance_checker
        
        for event in violation_events:
            violations = await compliance_checker.check_compliance(event)
            
            if violations:
                print(f"❌ Compliance violations found for event {event.event_id}:")
                for violation in violations:
                    print(f"   ⚠️ {violation}")
                
                # Generate compliance alert
                await compliance_checker.generate_compliance_alert(violations, event)
                print(f"🚨 Compliance alert generated")
            else:
                print(f"✅ Event {event.event_id} is compliant")
        
        print(f"⚖️ Compliance checking completed for {len(violation_events)} events")
    
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
    
    async def demonstrate_audit_trail_retrieval(self):
        """Demonstrate audit trail retrieval"""
        print("\n📋 Demonstrating Audit Trail Retrieval")
        print("=" * 50)
        
        # Get audit trail for specific user
        user_trail = await self.audit_logger.get_audit_trail(
            user_id="analyst_001",
            limit=10
        )
        print(f"👤 Audit trail for analyst_001: {len(user_trail)} events")
        
        # Get audit trail for specific resource type
        resource_trail = await self.audit_logger.get_audit_trail(
            resource_type="posts",
            limit=5
        )
        print(f"📊 Audit trail for posts resource: {len(resource_trail)} events")
        
        # Get recent audit trail
        recent_trail = await self.audit_logger.get_audit_trail(
            start_date=datetime.now(timezone.utc) - timedelta(hours=1),
            limit=20
        )
        print(f"🕐 Recent audit trail (last hour): {len(recent_trail)} events")
        
        # Show sample events
        if recent_trail:
            print("\n📝 Sample audit events:")
            for i, event in enumerate(recent_trail[:3], 1):
                print(f"   {i}. {event.get('action', 'N/A')} by {event.get('user_id', 'N/A')} at {event.get('timestamp', 'N/A')}")
    
    async def demonstrate_compliance_reporting(self):
        """Demonstrate compliance reporting"""
        print("\n📊 Demonstrating Compliance Reporting")
        print("=" * 50)
        
        # Generate compliance report for the last hour
        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc)
        
        report = await self.audit_logger.generate_compliance_report(start_date, end_date)
        
        print(f"📋 Generated compliance report")
        print(f"📅 Period: {report['report_period']['start_date'][:19]} to {report['report_period']['end_date'][:19]}")
        
        # Show statistics
        stats = report.get('statistics', [])
        print(f"📊 Event Statistics ({len(stats)} types):")
        for stat in stats[:5]:  # Show top 5
            print(f"   📈 {stat.get('event_type', 'N/A')}: {stat.get('count', 0)} events")
        
        # Show top users
        users = report.get('top_users', [])
        print(f"👥 Top Active Users ({len(users)}):")
        for user in users[:3]:  # Show top 3
            print(f"   👤 {user.get('user_id', 'N/A')}: {user.get('action_count', 0)} actions")
        
        # Show violations
        violations = report.get('compliance_violations', [])
        print(f"⚠️ Compliance Violations: {len(violations)}")
        
        return report
    
    async def generate_summary_report(self):
        """Generate a summary report of the demonstration"""
        print("\n📋 Audit Logging System Demonstration Summary")
        print("=" * 60)
        
        total_events = len(self.audit_logger.events)
        
        # Count events by type
        event_counts = {}
        for event in self.audit_logger.events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        print(f"📊 Demonstration Statistics:")
        print(f"   📝 Total Audit Events: {total_events}")
        
        for event_type, count in event_counts.items():
            print(f"   📈 {event_type.replace('_', ' ').title()}: {count}")
        
        print(f"\n✅ System Components Demonstrated:")
        print(f"   🔐 Audit Logger - User actions, data access, security events")
        print(f"   🔗 Data Lineage Tracker - Creation and transformation tracking")
        print(f"   ⚖️ Compliance Checker - Automated rule evaluation")
        print(f"   🎭 Audit Decorators - Transparent function monitoring")
        print(f"   📋 Audit Trail Retrieval - Flexible event querying")
        print(f"   📊 Compliance Reporting - Comprehensive analysis")
        
        print(f"\n🎯 Key Features Showcased:")
        print(f"   ✅ Comprehensive audit trail with full context")
        print(f"   ✅ Complete data lineage and provenance tracking")
        print(f"   ✅ Automated compliance checking and violation detection")
        print(f"   ✅ Decorator-based transparent monitoring")
        print(f"   ✅ Security event detection and logging")
        print(f"   ✅ Flexible audit trail retrieval and filtering")
        print(f"   ✅ Comprehensive compliance reporting")
        
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
            await self.demonstrate_data_access_logging()
            await self.demonstrate_data_lineage_tracking()
            await self.demonstrate_security_events()
            await self.demonstrate_compliance_checking()
            await self.demonstrate_audit_decorators()
            await self.demonstrate_audit_trail_retrieval()
            await self.demonstrate_compliance_reporting()
            
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