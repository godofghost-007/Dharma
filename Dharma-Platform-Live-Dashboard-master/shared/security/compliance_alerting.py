"""
Automated Compliance Alerting System for Project Dharma
Monitors compliance status and generates real-time alerts for violations
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid

from .audit_logger import AuditLogger, AuditEventType, AuditSeverity
from .compliance_reporter import ComplianceReporter, ComplianceStatus, ComplianceFramework
from ..database.postgresql import PostgreSQLManager
from ..logging.structured_logger import StructuredLogger


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"
    SYSLOG = "syslog"


@dataclass
class ComplianceAlert:
    """Compliance alert structure"""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    title: str
    description: str
    compliance_rule_id: str
    framework: ComplianceFramework
    violation_details: Dict[str, Any]
    affected_resources: List[str]
    remediation_steps: List[str]
    escalation_required: bool
    timestamp: datetime
    expires_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "compliance_rule_id": self.compliance_rule_id,
            "framework": self.framework.value,
            "violation_details": self.violation_details,
            "affected_resources": self.affected_resources,
            "remediation_steps": self.remediation_steps,
            "escalation_required": self.escalation_required,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    condition: str  # SQL condition or Python expression
    severity: AlertSeverity
    channels: List[AlertChannel]
    throttle_minutes: int
    escalation_minutes: Optional[int]
    auto_resolve: bool
    enabled: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "severity": self.severity.value,
            "channels": [c.value for c in self.channels],
            "throttle_minutes": self.throttle_minutes,
            "escalation_minutes": self.escalation_minutes,
            "auto_resolve": self.auto_resolve,
            "enabled": self.enabled
        }


class AlertThrottler:
    """Manages alert throttling to prevent spam"""
    
    def __init__(self):
        self.alert_history = {}
        self.logger = StructuredLogger(__name__)
    
    def should_send_alert(self, alert_type: str, throttle_minutes: int) -> bool:
        """Check if alert should be sent based on throttling rules"""
        now = datetime.now(timezone.utc)
        last_sent = self.alert_history.get(alert_type)
        
        if not last_sent:
            self.alert_history[alert_type] = now
            return True
        
        time_since_last = (now - last_sent).total_seconds() / 60
        
        if time_since_last >= throttle_minutes:
            self.alert_history[alert_type] = now
            return True
        
        return False
    
    def reset_throttle(self, alert_type: str):
        """Reset throttle for specific alert type"""
        if alert_type in self.alert_history:
            del self.alert_history[alert_type]


class AlertDeliveryService:
    """Handles alert delivery through various channels"""
    
    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.delivery_handlers = {
            AlertChannel.EMAIL: self._send_email_alert,
            AlertChannel.SMS: self._send_sms_alert,
            AlertChannel.SLACK: self._send_slack_alert,
            AlertChannel.WEBHOOK: self._send_webhook_alert,
            AlertChannel.DASHBOARD: self._send_dashboard_alert,
            AlertChannel.SYSLOG: self._send_syslog_alert
        }
    
    async def deliver_alert(self, alert: ComplianceAlert, channels: List[AlertChannel]):
        """Deliver alert through specified channels"""
        delivery_results = {}
        
        for channel in channels:
            try:
                handler = self.delivery_handlers.get(channel)
                if handler:
                    result = await handler(alert)
                    delivery_results[channel.value] = {"success": True, "result": result}
                else:
                    delivery_results[channel.value] = {"success": False, "error": "No handler configured"}
            
            except Exception as e:
                self.logger.error(f"Failed to deliver alert via {channel.value}: {e}")
                delivery_results[channel.value] = {"success": False, "error": str(e)}
        
        return delivery_results
    
    async def _send_email_alert(self, alert: ComplianceAlert) -> Dict[str, Any]:
        """Send alert via email"""
        # This would integrate with an email service like SendGrid, SES, etc.
        email_content = {
            "to": ["compliance@company.com", "security@company.com"],
            "subject": f"[{alert.severity.value.upper()}] Compliance Alert: {alert.title}",
            "body": self._format_email_body(alert),
            "html": self._format_email_html(alert)
        }
        
        # Simulate email sending
        self.logger.info(f"Email alert sent: {alert.alert_id}")
        return {"message_id": str(uuid.uuid4()), "status": "sent"}
    
    async def _send_sms_alert(self, alert: ComplianceAlert) -> Dict[str, Any]:
        """Send alert via SMS"""
        # This would integrate with Twilio, AWS SNS, etc.
        sms_content = {
            "to": ["+1234567890"],  # Compliance team phone numbers
            "message": f"COMPLIANCE ALERT [{alert.severity.value.upper()}]: {alert.title}. "
                      f"Rule: {alert.compliance_rule_id}. Check dashboard for details."
        }
        
        # Simulate SMS sending
        self.logger.info(f"SMS alert sent: {alert.alert_id}")
        return {"message_id": str(uuid.uuid4()), "status": "sent"}
    
    async def _send_slack_alert(self, alert: ComplianceAlert) -> Dict[str, Any]:
        """Send alert via Slack"""
        # This would integrate with Slack API
        slack_message = {
            "channel": "#compliance-alerts",
            "text": f"🚨 Compliance Alert: {alert.title}",
            "attachments": [
                {
                    "color": self._get_slack_color(alert.severity),
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                        {"title": "Rule ID", "value": alert.compliance_rule_id, "short": True},
                        {"title": "Framework", "value": alert.framework.value.upper(), "short": True},
                        {"title": "Description", "value": alert.description, "short": False}
                    ],
                    "footer": f"Alert ID: {alert.alert_id}",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        # Simulate Slack sending
        self.logger.info(f"Slack alert sent: {alert.alert_id}")
        return {"message_ts": str(int(alert.timestamp.timestamp())), "status": "sent"}
    
    async def _send_webhook_alert(self, alert: ComplianceAlert) -> Dict[str, Any]:
        """Send alert via webhook"""
        # This would send HTTP POST to configured webhook URLs
        webhook_payload = {
            "event_type": "compliance_alert",
            "alert": alert.to_dict(),
            "timestamp": alert.timestamp.isoformat()
        }
        
        # Simulate webhook sending
        self.logger.info(f"Webhook alert sent: {alert.alert_id}")
        return {"webhook_id": str(uuid.uuid4()), "status": "sent"}
    
    async def _send_dashboard_alert(self, alert: ComplianceAlert) -> Dict[str, Any]:
        """Send alert to dashboard (real-time notification)"""
        # This would push to WebSocket connections or message queue
        dashboard_notification = {
            "type": "compliance_alert",
            "data": alert.to_dict(),
            "timestamp": alert.timestamp.isoformat()
        }
        
        # Simulate dashboard notification
        self.logger.info(f"Dashboard alert sent: {alert.alert_id}")
        return {"notification_id": str(uuid.uuid4()), "status": "sent"}
    
    async def _send_syslog_alert(self, alert: ComplianceAlert) -> Dict[str, Any]:
        """Send alert to syslog"""
        # This would send to syslog daemon
        syslog_message = (
            f"COMPLIANCE_ALERT severity={alert.severity.value} "
            f"rule_id={alert.compliance_rule_id} "
            f"framework={alert.framework.value} "
            f"title=\"{alert.title}\" "
            f"alert_id={alert.alert_id}"
        )
        
        # Simulate syslog sending
        self.logger.info(f"Syslog alert sent: {alert.alert_id}")
        return {"syslog_id": str(uuid.uuid4()), "status": "sent"}
    
    def _format_email_body(self, alert: ComplianceAlert) -> str:
        """Format alert as plain text email"""
        return f"""
Compliance Alert: {alert.title}

Severity: {alert.severity.value.upper()}
Rule ID: {alert.compliance_rule_id}
Framework: {alert.framework.value.upper()}
Timestamp: {alert.timestamp.isoformat()}

Description:
{alert.description}

Violation Details:
{json.dumps(alert.violation_details, indent=2)}

Affected Resources:
{', '.join(alert.affected_resources) if alert.affected_resources else 'None specified'}

Remediation Steps:
{chr(10).join(f"- {step}" for step in alert.remediation_steps)}

Alert ID: {alert.alert_id}
        """
    
    def _format_email_html(self, alert: ComplianceAlert) -> str:
        """Format alert as HTML email"""
        color = {"info": "#17a2b8", "warning": "#ffc107", "critical": "#dc3545", "emergency": "#6f42c1"}[alert.severity.value]
        
        return f"""
        <html>
        <body>
            <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h2 style="color: {color};">🚨 Compliance Alert: {alert.title}</h2>
                
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Severity:</strong></td><td>{alert.severity.value.upper()}</td></tr>
                    <tr><td><strong>Rule ID:</strong></td><td>{alert.compliance_rule_id}</td></tr>
                    <tr><td><strong>Framework:</strong></td><td>{alert.framework.value.upper()}</td></tr>
                    <tr><td><strong>Timestamp:</strong></td><td>{alert.timestamp.isoformat()}</td></tr>
                </table>
                
                <h3>Description</h3>
                <p>{alert.description}</p>
                
                <h3>Remediation Steps</h3>
                <ul>
                    {''.join(f"<li>{step}</li>" for step in alert.remediation_steps)}
                </ul>
                
                <p><small>Alert ID: {alert.alert_id}</small></p>
            </div>
        </body>
        </html>
        """
    
    def _get_slack_color(self, severity: AlertSeverity) -> str:
        """Get Slack attachment color for severity"""
        colors = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.EMERGENCY: "#6f42c1"
        }
        return colors.get(severity, "good")


class ComplianceAlertingSystem:
    """Main compliance alerting system"""
    
    def __init__(self, postgresql_manager: PostgreSQLManager,
                 audit_logger: AuditLogger,
                 compliance_reporter: ComplianceReporter):
        self.postgresql = postgresql_manager
        self.audit_logger = audit_logger
        self.compliance_reporter = compliance_reporter
        self.throttler = AlertThrottler()
        self.delivery_service = AlertDeliveryService()
        self.logger = StructuredLogger(__name__)
        self.alert_rules = {}
        self.active_alerts = {}
        self._setup_alerting_tables()
        self._load_default_alert_rules()
    
    async def _setup_alerting_tables(self):
        """Setup alerting tables"""
        create_tables = """
        CREATE TABLE IF NOT EXISTS compliance_alerts (
            id SERIAL PRIMARY KEY,
            alert_id VARCHAR(255) UNIQUE NOT NULL,
            alert_type VARCHAR(100) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            compliance_rule_id VARCHAR(100) NOT NULL,
            framework VARCHAR(50) NOT NULL,
            violation_details JSONB,
            affected_resources TEXT[],
            remediation_steps TEXT[],
            escalation_required BOOLEAN NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            acknowledged_by VARCHAR(255),
            acknowledged_at TIMESTAMP WITH TIME ZONE,
            resolved_by VARCHAR(255),
            resolved_at TIMESTAMP WITH TIME ZONE,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS alert_deliveries (
            id SERIAL PRIMARY KEY,
            alert_id VARCHAR(255) NOT NULL,
            channel VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            delivery_details JSONB,
            delivered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (alert_id) REFERENCES compliance_alerts(alert_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_compliance_alerts_status ON compliance_alerts(status);
        CREATE INDEX IF NOT EXISTS idx_compliance_alerts_severity ON compliance_alerts(severity);
        CREATE INDEX IF NOT EXISTS idx_compliance_alerts_rule ON compliance_alerts(compliance_rule_id);
        """
        
        await self.postgresql.execute_query(create_tables)
    
    def _load_default_alert_rules(self):
        """Load default alert rules"""
        default_rules = [
            AlertRule(
                rule_id="CRITICAL_VIOLATION",
                name="Critical Compliance Violation",
                description="Alert for critical compliance violations requiring immediate attention",
                condition="severity = 'critical' AND status = 'non_compliant'",
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.SMS, AlertChannel.SLACK, AlertChannel.DASHBOARD],
                throttle_minutes=5,
                escalation_minutes=30,
                auto_resolve=False,
                enabled=True
            ),
            
            AlertRule(
                rule_id="DATA_RETENTION_VIOLATION",
                name="Data Retention Policy Violation",
                description="Alert when data retention policies are violated",
                condition="rule_id = 'DR001' AND status = 'non_compliant'",
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.EMAIL, AlertChannel.DASHBOARD],
                throttle_minutes=60,
                escalation_minutes=None,
                auto_resolve=True,
                enabled=True
            ),
            
            AlertRule(
                rule_id="PRIVILEGED_ACCESS_VIOLATION",
                name="Privileged Access Violation",
                description="Alert for unmonitored privileged access attempts",
                condition="rule_id = 'AC001' AND status = 'non_compliant'",
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.SMS, AlertChannel.DASHBOARD],
                throttle_minutes=15,
                escalation_minutes=60,
                auto_resolve=False,
                enabled=True
            ),
            
            AlertRule(
                rule_id="BULK_DATA_ACCESS",
                name="Suspicious Bulk Data Access",
                description="Alert for potential data exfiltration attempts",
                condition="access_patterns @> '[\"data_exfiltration\"]'",
                severity=AlertSeverity.EMERGENCY,
                channels=[AlertChannel.EMAIL, AlertChannel.SMS, AlertChannel.SLACK, AlertChannel.WEBHOOK],
                throttle_minutes=0,  # No throttling for emergency alerts
                escalation_minutes=15,
                auto_resolve=False,
                enabled=True
            ),
            
            AlertRule(
                rule_id="COMPLIANCE_DEGRADATION",
                name="Compliance Score Degradation",
                description="Alert when overall compliance score drops significantly",
                condition="compliance_percentage < 80",
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.EMAIL, AlertChannel.DASHBOARD],
                throttle_minutes=240,  # 4 hours
                escalation_minutes=None,
                auto_resolve=True,
                enabled=True
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
    
    async def process_compliance_check_result(self, check_result: Dict[str, Any]):
        """Process compliance check result and generate alerts if needed"""
        try:
            # Check each alert rule
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Evaluate rule condition
                if await self._evaluate_alert_condition(rule, check_result):
                    # Check throttling
                    if self.throttler.should_send_alert(rule_id, rule.throttle_minutes):
                        # Generate alert
                        alert = await self._create_compliance_alert(rule, check_result)
                        
                        # Deliver alert
                        await self._deliver_alert(alert, rule.channels)
                        
                        # Store alert
                        await self._store_alert(alert)
                        
                        # Track active alert
                        self.active_alerts[alert.alert_id] = alert
        
        except Exception as e:
            self.logger.error(f"Error processing compliance check result: {e}")
    
    async def _evaluate_alert_condition(self, rule: AlertRule, check_result: Dict[str, Any]) -> bool:
        """Evaluate if alert condition is met"""
        try:
            # Simple condition evaluation (in production, use a proper expression evaluator)
            condition = rule.condition
            
            # Replace placeholders with actual values
            for key, value in check_result.items():
                if isinstance(value, str):
                    condition = condition.replace(key, f"'{value}'")
                else:
                    condition = condition.replace(key, str(value))
            
            # For safety, only allow specific conditions (in production, use sandboxed evaluation)
            if "severity = 'critical'" in rule.condition and check_result.get("risk_level") == "critical":
                return check_result.get("status") == "non_compliant"
            
            if "rule_id = 'DR001'" in rule.condition and check_result.get("rule_id") == "DR001":
                return check_result.get("status") == "non_compliant"
            
            if "rule_id = 'AC001'" in rule.condition and check_result.get("rule_id") == "AC001":
                return check_result.get("status") == "non_compliant"
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating alert condition: {e}")
            return False
    
    async def _create_compliance_alert(self, rule: AlertRule, check_result: Dict[str, Any]) -> ComplianceAlert:
        """Create compliance alert from rule and check result"""
        alert_id = str(uuid.uuid4())
        
        # Determine framework from check result
        framework = ComplianceFramework.CUSTOM
        if check_result.get("rule_id", "").startswith("DR"):
            framework = ComplianceFramework.GDPR
        elif check_result.get("rule_id", "").startswith("AC"):
            framework = ComplianceFramework.ISO27001
        
        # Extract affected resources
        affected_resources = []
        if "resource_id" in check_result:
            affected_resources.append(check_result["resource_id"])
        
        # Get remediation steps from compliance rule
        compliance_rule = self.compliance_reporter.rule_engine.rules.get(check_result.get("rule_id"))
        remediation_steps = compliance_rule.remediation_steps if compliance_rule else ["Review and remediate violation"]
        
        alert = ComplianceAlert(
            alert_id=alert_id,
            alert_type=rule.rule_id,
            severity=rule.severity,
            title=f"{rule.name}: {check_result.get('rule_id', 'Unknown Rule')}",
            description=f"{rule.description}. Violation detected in compliance check.",
            compliance_rule_id=check_result.get("rule_id", "unknown"),
            framework=framework,
            violation_details=check_result.get("details", {}),
            affected_resources=affected_resources,
            remediation_steps=remediation_steps,
            escalation_required=rule.escalation_minutes is not None,
            timestamp=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24) if rule.auto_resolve else None
        )
        
        return alert
    
    async def _deliver_alert(self, alert: ComplianceAlert, channels: List[AlertChannel]):
        """Deliver alert through specified channels"""
        delivery_results = await self.delivery_service.deliver_alert(alert, channels)
        
        # Store delivery results
        for channel, result in delivery_results.items():
            await self._store_alert_delivery(alert.alert_id, channel, result)
        
        # Log alert generation
        await self.audit_logger.log_security_event(
            event_type="compliance_alert_generated",
            severity=AuditSeverity.MEDIUM,
            details={
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity.value,
                "compliance_rule_id": alert.compliance_rule_id,
                "delivery_channels": [c.value for c in channels],
                "delivery_results": delivery_results
            }
        )
    
    async def _store_alert(self, alert: ComplianceAlert):
        """Store alert in database"""
        query = """
        INSERT INTO compliance_alerts (
            alert_id, alert_type, severity, title, description,
            compliance_rule_id, framework, violation_details,
            affected_resources, remediation_steps, escalation_required,
            timestamp, expires_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """
        
        await self.postgresql.execute_query(
            query,
            alert.alert_id, alert.alert_type, alert.severity.value,
            alert.title, alert.description, alert.compliance_rule_id,
            alert.framework.value, json.dumps(alert.violation_details),
            alert.affected_resources, alert.remediation_steps,
            alert.escalation_required, alert.timestamp, alert.expires_at
        )
    
    async def _store_alert_delivery(self, alert_id: str, channel: str, result: Dict[str, Any]):
        """Store alert delivery result"""
        query = """
        INSERT INTO alert_deliveries (alert_id, channel, status, delivery_details)
        VALUES ($1, $2, $3, $4)
        """
        
        status = "success" if result.get("success", False) else "failed"
        
        await self.postgresql.execute_query(
            query, alert_id, channel, status, json.dumps(result)
        )
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        query = """
        UPDATE compliance_alerts 
        SET status = 'acknowledged', acknowledged_by = $2, acknowledged_at = $3
        WHERE alert_id = $1 AND status = 'active'
        """
        
        result = await self.postgresql.execute_query(
            query, alert_id, acknowledged_by, datetime.now(timezone.utc)
        )
        
        if result:
            # Remove from active alerts
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
            
            # Log acknowledgment
            await self.audit_logger.log_user_action(
                user_id=acknowledged_by,
                action="acknowledge_compliance_alert",
                resource_type="compliance_alert",
                resource_id=alert_id,
                details={"alert_id": alert_id}
            )
            
            return True
        
        return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: str = None) -> bool:
        """Resolve an alert"""
        query = """
        UPDATE compliance_alerts 
        SET status = 'resolved', resolved_by = $2, resolved_at = $3
        WHERE alert_id = $1 AND status IN ('active', 'acknowledged')
        """
        
        result = await self.postgresql.execute_query(
            query, alert_id, resolved_by, datetime.now(timezone.utc)
        )
        
        if result:
            # Remove from active alerts
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
            
            # Log resolution
            await self.audit_logger.log_user_action(
                user_id=resolved_by,
                action="resolve_compliance_alert",
                resource_type="compliance_alert",
                resource_id=alert_id,
                details={
                    "alert_id": alert_id,
                    "resolution_notes": resolution_notes
                }
            )
            
            return True
        
        return False
    
    async def get_active_alerts(self, severity: AlertSeverity = None) -> List[Dict[str, Any]]:
        """Get active compliance alerts"""
        conditions = ["status = 'active'"]
        params = []
        
        if severity:
            conditions.append("severity = $1")
            params.append(severity.value)
        
        query = f"""
        SELECT * FROM compliance_alerts 
        WHERE {' AND '.join(conditions)}
        ORDER BY timestamp DESC
        """
        
        alerts = await self.postgresql.fetch_all(query, *params)
        return [dict(alert) for alert in alerts]
    
    async def get_alert_statistics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get alert statistics for reporting"""
        stats_query = """
        SELECT 
            severity,
            status,
            COUNT(*) as count
        FROM compliance_alerts 
        WHERE timestamp BETWEEN $1 AND $2
        GROUP BY severity, status
        ORDER BY severity, status
        """
        
        stats = await self.postgresql.fetch_all(stats_query, start_date, end_date)
        
        # Get delivery statistics
        delivery_query = """
        SELECT 
            ad.channel,
            ad.status,
            COUNT(*) as count
        FROM alert_deliveries ad
        JOIN compliance_alerts ca ON ad.alert_id = ca.alert_id
        WHERE ca.timestamp BETWEEN $1 AND $2
        GROUP BY ad.channel, ad.status
        ORDER BY ad.channel, ad.status
        """
        
        delivery_stats = await self.postgresql.fetch_all(delivery_query, start_date, end_date)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "alert_statistics": [dict(row) for row in stats],
            "delivery_statistics": [dict(row) for row in delivery_stats],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def start_monitoring(self):
        """Start continuous compliance monitoring"""
        self.logger.info("Starting compliance alerting system")
        
        while True:
            try:
                # Check for expired alerts that should auto-resolve
                await self._auto_resolve_expired_alerts()
                
                # Check for alerts requiring escalation
                await self._check_escalation_required()
                
                # Clean up old resolved alerts (older than 90 days)
                await self._cleanup_old_alerts()
                
                # Wait 5 minutes before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in compliance monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _auto_resolve_expired_alerts(self):
        """Auto-resolve expired alerts"""
        query = """
        UPDATE compliance_alerts 
        SET status = 'auto_resolved', resolved_at = NOW()
        WHERE status = 'active' 
        AND expires_at IS NOT NULL 
        AND expires_at <= NOW()
        RETURNING alert_id
        """
        
        resolved_alerts = await self.postgresql.fetch_all(query)
        
        for alert in resolved_alerts:
            alert_id = alert['alert_id']
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
            
            self.logger.info(f"Auto-resolved expired alert: {alert_id}")
    
    async def _check_escalation_required(self):
        """Check for alerts requiring escalation"""
        query = """
        SELECT alert_id, alert_type, severity, timestamp
        FROM compliance_alerts 
        WHERE status = 'active' 
        AND escalation_required = true
        AND timestamp <= NOW() - INTERVAL '30 minutes'
        """
        
        escalation_alerts = await self.postgresql.fetch_all(query)
        
        for alert in escalation_alerts:
            await self._escalate_alert(dict(alert))
    
    async def _escalate_alert(self, alert: Dict[str, Any]):
        """Escalate an alert"""
        # Create escalation alert
        escalation_alert = ComplianceAlert(
            alert_id=str(uuid.uuid4()),
            alert_type="ESCALATION",
            severity=AlertSeverity.EMERGENCY,
            title=f"ESCALATION: {alert['alert_type']}",
            description=f"Alert {alert['alert_id']} requires immediate attention - no response received",
            compliance_rule_id=alert.get('compliance_rule_id', 'unknown'),
            framework=ComplianceFramework.CUSTOM,
            violation_details={"original_alert_id": alert['alert_id']},
            affected_resources=[],
            remediation_steps=["Immediate management review required"],
            escalation_required=False,
            timestamp=datetime.now(timezone.utc),
            expires_at=None
        )
        
        # Send to escalation channels (management, security team)
        escalation_channels = [AlertChannel.EMAIL, AlertChannel.SMS]
        await self._deliver_alert(escalation_alert, escalation_channels)
        await self._store_alert(escalation_alert)
        
        self.logger.warning(f"Escalated alert: {alert['alert_id']}")
    
    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        cleanup_date = datetime.now(timezone.utc) - timedelta(days=90)
        
        query = """
        DELETE FROM compliance_alerts 
        WHERE status IN ('resolved', 'auto_resolved') 
        AND resolved_at <= $1
        """
        
        result = await self.postgresql.execute_query(query, cleanup_date)
        
        if result:
            self.logger.info(f"Cleaned up old compliance alerts before {cleanup_date}")