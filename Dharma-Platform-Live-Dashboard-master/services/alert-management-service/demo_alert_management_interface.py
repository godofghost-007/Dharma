"""
Demonstration script for Alert Management Interface.

This script demonstrates all the key features of the alert management interface
including inbox functionality, search capabilities, acknowledgment, assignment,
resolution tracking, and escalation workflows.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from shared.models.alert import (
    Alert, AlertCreate, AlertSummary, AlertType, SeverityLevel, 
    AlertStatus, EscalationLevel, AlertContext
)
from app.core.alert_manager import AlertManager
from app.core.search_service import AlertSearchService
from app.core.reporting_service import ReportingService
from app.core.escalation_engine import EscalationEngine


class AlertManagementInterfaceDemo:
    """Demonstration of alert management interface capabilities."""
    
    def __init__(self):
        self.alert_manager = AlertManager()
        self.search_service = AlertSearchService()
        self.reporting_service = ReportingService()
        self.escalation_engine = EscalationEngine()
        
        # Demo data
        self.demo_alerts = []
        self.demo_users = ["analyst_1", "analyst_2", "supervisor_1", "admin"]
    
    async def run_demo(self):
        """Run the complete demonstration."""
        print("🚨 Project Dharma - Alert Management Interface Demo")
        print("=" * 60)
        
        try:
            # 1. Setup demo data
            await self.setup_demo_data()
            
            # 2. Demonstrate inbox functionality
            await self.demo_inbox_functionality()
            
            # 3. Demonstrate search capabilities
            await self.demo_search_capabilities()
            
            # 4. Demonstrate alert acknowledgment
            await self.demo_alert_acknowledgment()
            
            # 5. Demonstrate alert assignment
            await self.demo_alert_assignment()
            
            # 6. Demonstrate alert resolution
            await self.demo_alert_resolution()
            
            # 7. Demonstrate escalation workflows
            await self.demo_escalation_workflows()
            
            # 8. Demonstrate bulk operations
            await self.demo_bulk_operations()
            
            # 9. Demonstrate reporting and analytics
            await self.demo_reporting_analytics()
            
            print("\n✅ Alert Management Interface Demo Completed Successfully!")
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {str(e)}")
            raise
    
    async def setup_demo_data(self):
        """Setup demonstration data."""
        print("\n📋 Setting up demo data...")
        
        # Create sample alerts
        alert_configs = [
            {
                "title": "High Risk Anti-India Content Detected",
                "description": "Viral tweet thread spreading anti-India sentiment detected",
                "alert_type": AlertType.HIGH_RISK_CONTENT,
                "severity": SeverityLevel.CRITICAL,
                "context": {
                    "source_platform": "twitter",
                    "content_samples": ["Sample anti-India tweet content"],
                    "risk_score": 0.95,
                    "confidence_score": 0.88,
                    "affected_regions": ["national"],
                    "keywords_matched": ["anti-india", "propaganda"]
                }
            },
            {
                "title": "Coordinated Bot Network Activity",
                "description": "Suspicious coordinated posting pattern detected across multiple accounts",
                "alert_type": AlertType.BOT_NETWORK_DETECTED,
                "severity": SeverityLevel.HIGH,
                "context": {
                    "source_platform": "twitter",
                    "content_samples": ["Coordinated bot messages"],
                    "risk_score": 0.82,
                    "confidence_score": 0.91,
                    "affected_regions": ["north", "west"],
                    "bot_accounts_detected": 45
                }
            },
            {
                "title": "Viral Misinformation Campaign",
                "description": "False information about government policy spreading rapidly",
                "alert_type": AlertType.VIRAL_MISINFORMATION,
                "severity": SeverityLevel.CRITICAL,
                "context": {
                    "source_platform": "youtube",
                    "content_samples": ["Misleading video content"],
                    "risk_score": 0.89,
                    "confidence_score": 0.85,
                    "affected_regions": ["national"],
                    "viral_metrics": {"views": 50000, "shares": 1200}
                }
            },
            {
                "title": "Election Interference Attempt",
                "description": "Coordinated campaign targeting election integrity",
                "alert_type": AlertType.ELECTION_INTERFERENCE,
                "severity": SeverityLevel.CRITICAL,
                "context": {
                    "source_platform": "telegram",
                    "content_samples": ["Election misinformation"],
                    "risk_score": 0.97,
                    "confidence_score": 0.93,
                    "affected_regions": ["national"],
                    "election_related": True
                }
            },
            {
                "title": "Suspicious Account Activity",
                "description": "Multiple accounts showing automated behavior patterns",
                "alert_type": AlertType.BOT_NETWORK_DETECTED,
                "severity": SeverityLevel.MEDIUM,
                "context": {
                    "source_platform": "twitter",
                    "content_samples": ["Automated posting patterns"],
                    "risk_score": 0.67,
                    "confidence_score": 0.79,
                    "affected_regions": ["south"],
                    "bot_probability": 0.85
                }
            }
        ]
        
        # Create alerts
        for i, config in enumerate(alert_configs):
            alert_id = f"demo_alert_{i+1:03d}"
            
            # Create alert context
            context = AlertContext(
                source_platform=config["context"]["source_platform"],
                content_samples=config["context"]["content_samples"],
                risk_score=config["context"]["risk_score"],
                confidence_score=config["context"]["confidence_score"],
                affected_regions=config["context"].get("affected_regions", []),
                keywords_matched=config["context"].get("keywords_matched", [])
            )
            
            # Create alert
            alert = Alert(
                alert_id=alert_id,
                title=config["title"],
                description=config["description"],
                alert_type=config["alert_type"],
                severity=config["severity"],
                status=AlertStatus.NEW,
                context=context,
                created_at=datetime.utcnow() - timedelta(hours=i),
                updated_at=datetime.utcnow() - timedelta(hours=i)
            )
            
            self.demo_alerts.append(alert)
        
        print(f"✅ Created {len(self.demo_alerts)} demo alerts")
    
    async def demo_inbox_functionality(self):
        """Demonstrate inbox functionality with filtering and pagination."""
        print("\n📥 Demonstrating Alert Inbox Functionality")
        print("-" * 40)
        
        # Simulate getting alerts with different filters
        print("1. Getting all active alerts...")
        active_alerts = [alert for alert in self.demo_alerts if alert.status != AlertStatus.RESOLVED]
        print(f"   Found {len(active_alerts)} active alerts")
        
        # Filter by severity
        print("\n2. Filtering by critical severity...")
        critical_alerts = [alert for alert in active_alerts if alert.severity == SeverityLevel.CRITICAL]
        print(f"   Found {len(critical_alerts)} critical alerts:")
        for alert in critical_alerts:
            print(f"   - {alert.alert_id}: {alert.title}")
        
        # Filter by alert type
        print("\n3. Filtering by bot network alerts...")
        bot_alerts = [alert for alert in active_alerts if alert.alert_type == AlertType.BOT_NETWORK_DETECTED]
        print(f"   Found {len(bot_alerts)} bot network alerts:")
        for alert in bot_alerts:
            print(f"   - {alert.alert_id}: {alert.title}")
        
        # Filter by assignment status
        print("\n4. Filtering by assignment status...")
        unassigned_alerts = [alert for alert in active_alerts if not alert.assigned_to]
        print(f"   Found {len(unassigned_alerts)} unassigned alerts")
        
        # Demonstrate pagination
        print("\n5. Demonstrating pagination (page 1, limit 3)...")
        page_1_alerts = active_alerts[:3]
        for i, alert in enumerate(page_1_alerts, 1):
            print(f"   {i}. {alert.alert_id}: {alert.title[:50]}...")
        
        print("✅ Inbox functionality demonstrated")
    
    async def demo_search_capabilities(self):
        """Demonstrate advanced search capabilities."""
        print("\n🔍 Demonstrating Search Capabilities")
        print("-" * 40)
        
        # Text search
        print("1. Text search for 'bot network'...")
        search_results = []
        for alert in self.demo_alerts:
            if "bot" in alert.title.lower() or "network" in alert.title.lower():
                search_results.append(alert)
        
        print(f"   Found {len(search_results)} results:")
        for alert in search_results:
            print(f"   - {alert.alert_id}: {alert.title}")
        
        # Risk score filtering
        print("\n2. Filtering by high risk score (>0.8)...")
        high_risk_alerts = [alert for alert in self.demo_alerts if alert.context.risk_score > 0.8]
        print(f"   Found {len(high_risk_alerts)} high-risk alerts:")
        for alert in high_risk_alerts:
            print(f"   - {alert.alert_id}: Risk {alert.context.risk_score:.2f} - {alert.title}")
        
        # Platform filtering
        print("\n3. Filtering by platform (Twitter)...")
        twitter_alerts = [alert for alert in self.demo_alerts if alert.context.source_platform == "twitter"]
        print(f"   Found {len(twitter_alerts)} Twitter alerts:")
        for alert in twitter_alerts:
            print(f"   - {alert.alert_id}: {alert.title}")
        
        # Combined search
        print("\n4. Combined search: Critical alerts from Twitter with risk > 0.9...")
        combined_results = [
            alert for alert in self.demo_alerts
            if (alert.severity == SeverityLevel.CRITICAL and 
                alert.context.source_platform == "twitter" and 
                alert.context.risk_score > 0.9)
        ]
        print(f"   Found {len(combined_results)} matching alerts:")
        for alert in combined_results:
            print(f"   - {alert.alert_id}: {alert.title}")
        
        # Search suggestions
        print("\n5. Search suggestions for 'bot'...")
        suggestions = ["bot network", "bot detection", "bot activity", "coordinated bots"]
        print(f"   Suggestions: {', '.join(suggestions)}")
        
        print("✅ Search capabilities demonstrated")
    
    async def demo_alert_acknowledgment(self):
        """Demonstrate alert acknowledgment functionality."""
        print("\n✅ Demonstrating Alert Acknowledgment")
        print("-" * 40)
        
        # Select first unacknowledged alert
        target_alert = None
        for alert in self.demo_alerts:
            if alert.status == AlertStatus.NEW:
                target_alert = alert
                break
        
        if target_alert:
            print(f"1. Acknowledging alert: {target_alert.alert_id}")
            print(f"   Title: {target_alert.title}")
            print(f"   Current status: {target_alert.status.value}")
            
            # Simulate acknowledgment
            user_id = "analyst_1"
            notes = "Alert acknowledged for investigation"
            
            # Update alert status
            target_alert.acknowledge(user_id, notes)
            
            print(f"   ✅ Alert acknowledged by {user_id}")
            print(f"   New status: {target_alert.status.value}")
            print(f"   Acknowledged at: {target_alert.acknowledged_at}")
            print(f"   Response time: {target_alert.response_time_minutes} minutes")
            print(f"   Notes: {notes}")
            
            # Show acknowledgment tracking
            print("\n2. Acknowledgment tracking:")
            print(f"   - Acknowledged by: {target_alert.acknowledged_by}")
            print(f"   - Response time: {target_alert.response_time_minutes} minutes")
            print(f"   - Investigation notes: {len(target_alert.investigation_notes)} entries")
        
        print("✅ Alert acknowledgment demonstrated")
    
    async def demo_alert_assignment(self):
        """Demonstrate alert assignment functionality."""
        print("\n👤 Demonstrating Alert Assignment")
        print("-" * 40)
        
        # Select an acknowledged alert for assignment
        target_alert = None
        for alert in self.demo_alerts:
            if alert.status == AlertStatus.ACKNOWLEDGED:
                target_alert = alert
                break
        
        if not target_alert:
            # Use any alert
            target_alert = self.demo_alerts[1]
        
        print(f"1. Assigning alert: {target_alert.alert_id}")
        print(f"   Title: {target_alert.title}")
        print(f"   Current assignment: {target_alert.assigned_to or 'Unassigned'}")
        
        # Simulate assignment
        assigned_to = "analyst_2"
        assigned_by = "supervisor_1"
        assignment_notes = "Assigning to specialist for detailed analysis"
        
        # Update alert assignment
        target_alert.assign(assigned_to, assigned_by)
        target_alert.investigation_notes.append(f"Assignment note: {assignment_notes}")
        
        print(f"   ✅ Alert assigned to {assigned_to} by {assigned_by}")
        print(f"   Assignment time: {target_alert.assigned_at}")
        print(f"   Assignment notes: {assignment_notes}")
        
        # Show assignment history
        print("\n2. Assignment tracking:")
        print(f"   - Assigned to: {target_alert.assigned_to}")
        print(f"   - Assigned by: {assigned_by}")
        print(f"   - Assignment time: {target_alert.assigned_at}")
        
        # Demonstrate reassignment
        print("\n3. Demonstrating reassignment...")
        new_assignee = "supervisor_1"
        target_alert.assign(new_assignee, "admin")
        print(f"   ✅ Alert reassigned to {new_assignee}")
        
        print("✅ Alert assignment demonstrated")
    
    async def demo_alert_resolution(self):
        """Demonstrate alert resolution functionality."""
        print("\n🎯 Demonstrating Alert Resolution")
        print("-" * 40)
        
        # Select an assigned alert for resolution
        target_alert = None
        for alert in self.demo_alerts:
            if alert.assigned_to:
                target_alert = alert
                break
        
        if not target_alert:
            target_alert = self.demo_alerts[2]
        
        print(f"1. Resolving alert: {target_alert.alert_id}")
        print(f"   Title: {target_alert.title}")
        print(f"   Current status: {target_alert.status.value}")
        print(f"   Severity: {target_alert.severity.value}")
        
        # Simulate resolution
        resolved_by = "analyst_2"
        resolution_notes = "Content verified as false positive. AI model needs retraining on this content type."
        resolution_type = "False Positive"
        
        # Update alert resolution
        target_alert.resolve(resolved_by, resolution_notes)
        target_alert.metadata['resolution_type'] = resolution_type
        
        print(f"   ✅ Alert resolved by {resolved_by}")
        print(f"   Resolution type: {resolution_type}")
        print(f"   Resolution time: {target_alert.resolved_at}")
        print(f"   Total resolution time: {target_alert.resolution_time_minutes} minutes")
        print(f"   Resolution notes: {resolution_notes}")
        
        # Show resolution tracking
        print("\n2. Resolution tracking:")
        print(f"   - Resolved by: {target_alert.resolved_by}")
        print(f"   - Resolution type: {target_alert.metadata.get('resolution_type')}")
        print(f"   - Resolution time: {target_alert.resolution_time_minutes} minutes")
        print(f"   - Status: {target_alert.status.value}")
        
        # Show resolution analytics
        print("\n3. Resolution analytics:")
        resolved_alerts = [alert for alert in self.demo_alerts if alert.status == AlertStatus.RESOLVED]
        if resolved_alerts:
            avg_resolution_time = sum(
                alert.resolution_time_minutes for alert in resolved_alerts 
                if alert.resolution_time_minutes
            ) / len(resolved_alerts)
            print(f"   - Total resolved alerts: {len(resolved_alerts)}")
            print(f"   - Average resolution time: {avg_resolution_time:.1f} minutes")
        
        print("✅ Alert resolution demonstrated")
    
    async def demo_escalation_workflows(self):
        """Demonstrate escalation workflows and automation."""
        print("\n⚡ Demonstrating Escalation Workflows")
        print("-" * 40)
        
        # Select a critical alert for escalation
        target_alert = None
        for alert in self.demo_alerts:
            if alert.severity == SeverityLevel.CRITICAL and alert.status != AlertStatus.RESOLVED:
                target_alert = alert
                break
        
        if not target_alert:
            target_alert = self.demo_alerts[0]
        
        print(f"1. Manual escalation of alert: {target_alert.alert_id}")
        print(f"   Title: {target_alert.title}")
        print(f"   Current escalation level: {target_alert.escalation_level.value}")
        print(f"   Severity: {target_alert.severity.value}")
        
        # Simulate manual escalation
        escalated_by = "analyst_1"
        new_level = EscalationLevel.LEVEL_2
        escalation_reason = "Critical alert requires supervisor attention due to national security implications"
        
        # Update alert escalation
        target_alert.escalate(escalated_by, new_level, escalation_reason)
        
        print(f"   ✅ Alert escalated to {new_level.value} by {escalated_by}")
        print(f"   Escalation reason: {escalation_reason}")
        print(f"   Escalation time: {target_alert.escalated_at}")
        
        # Demonstrate escalation rules
        print("\n2. Escalation rules configuration:")
        escalation_rules = [
            {
                "alert_type": "high_risk_content",
                "severity": "critical",
                "max_unacknowledged_time": 30,
                "escalation_level": "level_2"
            },
            {
                "alert_type": "election_interference",
                "severity": "critical",
                "max_unacknowledged_time": 10,
                "escalation_level": "level_4"
            },
            {
                "alert_type": "viral_misinformation",
                "severity": "high",
                "max_unacknowledged_time": 60,
                "escalation_level": "level_2"
            }
        ]
        
        for rule in escalation_rules:
            print(f"   - {rule['alert_type']} ({rule['severity']}): "
                  f"Escalate to {rule['escalation_level']} after {rule['max_unacknowledged_time']} min")
        
        # Simulate auto-escalation
        print("\n3. Auto-escalation simulation:")
        auto_escalation_alert = self.demo_alerts[3]  # Election interference
        if auto_escalation_alert.alert_type == AlertType.ELECTION_INTERFERENCE:
            print(f"   Alert {auto_escalation_alert.alert_id} (Election Interference)")
            print(f"   Created: {auto_escalation_alert.created_at}")
            print(f"   Status: {auto_escalation_alert.status.value}")
            
            # Simulate time passing without acknowledgment
            time_since_creation = 15  # minutes
            if time_since_creation > 10:  # Rule: escalate after 10 minutes
                auto_escalation_alert.escalate("system", EscalationLevel.LEVEL_4, 
                                              "Auto-escalated: No acknowledgment within 10 minutes")
                print(f"   🚨 AUTO-ESCALATED to {EscalationLevel.LEVEL_4.value} (system)")
                print(f"   Reason: No acknowledgment within SLA")
        
        # Show escalation history
        print("\n4. Escalation tracking:")
        escalated_alerts = [alert for alert in self.demo_alerts if alert.escalation_level != EscalationLevel.LEVEL_1]
        print(f"   - Total escalated alerts: {len(escalated_alerts)}")
        for alert in escalated_alerts:
            print(f"   - {alert.alert_id}: {alert.escalation_level.value} "
                  f"(escalated by {alert.escalated_by})")
        
        print("✅ Escalation workflows demonstrated")
    
    async def demo_bulk_operations(self):
        """Demonstrate bulk operations functionality."""
        print("\n⚙️ Demonstrating Bulk Operations")
        print("-" * 40)
        
        # Select multiple alerts for bulk operations
        bulk_alerts = [alert for alert in self.demo_alerts if alert.status == AlertStatus.NEW][:3]
        
        if bulk_alerts:
            print(f"1. Bulk acknowledgment of {len(bulk_alerts)} alerts:")
            for alert in bulk_alerts:
                print(f"   - {alert.alert_id}: {alert.title[:40]}...")
            
            # Simulate bulk acknowledgment
            bulk_user = "supervisor_1"
            bulk_notes = "Bulk acknowledged for team review"
            
            successful_ops = []
            failed_ops = []
            
            for alert in bulk_alerts:
                try:
                    alert.acknowledge(bulk_user, bulk_notes)
                    successful_ops.append(alert.alert_id)
                except Exception as e:
                    failed_ops.append({"alert_id": alert.alert_id, "error": str(e)})
            
            print(f"   ✅ Successfully acknowledged: {len(successful_ops)} alerts")
            print(f"   ❌ Failed: {len(failed_ops)} alerts")
            
            # Bulk assignment
            print(f"\n2. Bulk assignment of {len(successful_ops)} acknowledged alerts:")
            assignee = "analyst_2"
            assignment_notes = "Bulk assigned for investigation"
            
            for alert_id in successful_ops:
                alert = next(a for a in self.demo_alerts if a.alert_id == alert_id)
                alert.assign(assignee, bulk_user)
                print(f"   - {alert_id}: Assigned to {assignee}")
            
            print(f"   ✅ Bulk assignment completed")
            
            # Bulk tagging
            print(f"\n3. Bulk tagging operation:")
            bulk_tags = ["bulk_processed", "team_review", "high_priority"]
            
            for alert_id in successful_ops:
                alert = next(a for a in self.demo_alerts if a.alert_id == alert_id)
                alert.tags.extend(bulk_tags)
                print(f"   - {alert_id}: Added tags {bulk_tags}")
            
            print(f"   ✅ Bulk tagging completed")
            
            # Show bulk operation results
            print(f"\n4. Bulk operation summary:")
            print(f"   - Total alerts processed: {len(bulk_alerts)}")
            print(f"   - Successful operations: {len(successful_ops)}")
            print(f"   - Failed operations: {len(failed_ops)}")
            print(f"   - Success rate: {len(successful_ops)/len(bulk_alerts)*100:.1f}%")
        
        print("✅ Bulk operations demonstrated")
    
    async def demo_reporting_analytics(self):
        """Demonstrate reporting and analytics functionality."""
        print("\n📊 Demonstrating Reporting & Analytics")
        print("-" * 40)
        
        # Alert statistics
        print("1. Alert Statistics (Last 7 days):")
        total_alerts = len(self.demo_alerts)
        new_alerts = len([a for a in self.demo_alerts if a.status == AlertStatus.NEW])
        acknowledged_alerts = len([a for a in self.demo_alerts if a.status == AlertStatus.ACKNOWLEDGED])
        investigating_alerts = len([a for a in self.demo_alerts if a.status == AlertStatus.INVESTIGATING])
        resolved_alerts = len([a for a in self.demo_alerts if a.status == AlertStatus.RESOLVED])
        
        print(f"   - Total alerts: {total_alerts}")
        print(f"   - New alerts: {new_alerts}")
        print(f"   - Acknowledged alerts: {acknowledged_alerts}")
        print(f"   - Investigating alerts: {investigating_alerts}")
        print(f"   - Resolved alerts: {resolved_alerts}")
        
        # Severity distribution
        print("\n2. Severity Distribution:")
        critical_count = len([a for a in self.demo_alerts if a.severity == SeverityLevel.CRITICAL])
        high_count = len([a for a in self.demo_alerts if a.severity == SeverityLevel.HIGH])
        medium_count = len([a for a in self.demo_alerts if a.severity == SeverityLevel.MEDIUM])
        low_count = len([a for a in self.demo_alerts if a.severity == SeverityLevel.LOW])
        
        print(f"   - Critical: {critical_count} ({critical_count/total_alerts*100:.1f}%)")
        print(f"   - High: {high_count} ({high_count/total_alerts*100:.1f}%)")
        print(f"   - Medium: {medium_count} ({medium_count/total_alerts*100:.1f}%)")
        print(f"   - Low: {low_count} ({low_count/total_alerts*100:.1f}%)")
        
        # Alert type distribution
        print("\n3. Alert Type Distribution:")
        type_counts = {}
        for alert in self.demo_alerts:
            alert_type = alert.alert_type.value
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
        
        for alert_type, count in type_counts.items():
            print(f"   - {alert_type.replace('_', ' ').title()}: {count}")
        
        # Performance metrics
        print("\n4. Performance Metrics:")
        response_times = [a.response_time_minutes for a in self.demo_alerts if a.response_time_minutes]
        resolution_times = [a.resolution_time_minutes for a in self.demo_alerts if a.resolution_time_minutes]
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            print(f"   - Average response time: {avg_response_time:.1f} minutes")
            print(f"   - Fastest response: {min(response_times)} minutes")
            print(f"   - Slowest response: {max(response_times)} minutes")
        
        if resolution_times:
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
            print(f"   - Average resolution time: {avg_resolution_time:.1f} minutes")
            print(f"   - Fastest resolution: {min(resolution_times)} minutes")
            print(f"   - Slowest resolution: {max(resolution_times)} minutes")
        
        # Platform analysis
        print("\n5. Platform Analysis:")
        platform_counts = {}
        for alert in self.demo_alerts:
            platform = alert.context.source_platform
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        for platform, count in platform_counts.items():
            print(f"   - {platform.title()}: {count} alerts")
        
        # Risk score analysis
        print("\n6. Risk Score Analysis:")
        risk_scores = [a.context.risk_score for a in self.demo_alerts]
        if risk_scores:
            avg_risk_score = sum(risk_scores) / len(risk_scores)
            high_risk_count = len([score for score in risk_scores if score > 0.8])
            
            print(f"   - Average risk score: {avg_risk_score:.3f}")
            print(f"   - High risk alerts (>0.8): {high_risk_count}")
            print(f"   - Highest risk score: {max(risk_scores):.3f}")
            print(f"   - Lowest risk score: {min(risk_scores):.3f}")
        
        # Escalation analysis
        print("\n7. Escalation Analysis:")
        escalated_count = len([a for a in self.demo_alerts if a.escalation_level != EscalationLevel.LEVEL_1])
        auto_escalated = len([a for a in self.demo_alerts if a.escalated_by == "system"])
        manual_escalated = escalated_count - auto_escalated
        
        print(f"   - Total escalated alerts: {escalated_count}")
        print(f"   - Auto-escalated: {auto_escalated}")
        print(f"   - Manually escalated: {manual_escalated}")
        print(f"   - Escalation rate: {escalated_count/total_alerts*100:.1f}%")
        
        # Export simulation
        print("\n8. Report Export Simulation:")
        export_formats = ["CSV", "JSON", "PDF"]
        for format_type in export_formats:
            print(f"   - {format_type} export: ✅ Available")
        
        print("✅ Reporting and analytics demonstrated")
    
    def print_alert_summary(self, alert: Alert):
        """Print a formatted alert summary."""
        print(f"   Alert ID: {alert.alert_id}")
        print(f"   Title: {alert.title}")
        print(f"   Type: {alert.alert_type.value}")
        print(f"   Severity: {alert.severity.value}")
        print(f"   Status: {alert.status.value}")
        print(f"   Risk Score: {alert.context.risk_score:.3f}")
        print(f"   Created: {alert.created_at}")
        if alert.assigned_to:
            print(f"   Assigned to: {alert.assigned_to}")
        if alert.escalation_level != EscalationLevel.LEVEL_1:
            print(f"   Escalation Level: {alert.escalation_level.value}")


async def main():
    """Run the alert management interface demonstration."""
    demo = AlertManagementInterfaceDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())