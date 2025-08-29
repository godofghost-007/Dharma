"""
Compliance Reporting System for Project Dharma
Generates comprehensive compliance reports and automated compliance checking
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid
from pathlib import Path

from .audit_logger import AuditLogger, AuditEventType, AuditSeverity
from .data_access_monitor import DataAccessMonitor
from ..database.postgresql import PostgreSQLManager
from ..database.mongodb import MongoDBManager
from ..logging.structured_logger import StructuredLogger


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    GDPR = "gdpr"
    SOX = "sox"
    HIPAA = "hipaa"
    ISO27001 = "iso27001"
    NIST = "nist"
    CUSTOM = "custom"


class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNDER_REVIEW = "under_review"
    REMEDIATION_REQUIRED = "remediation_required"


@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    rule_id: str
    framework: ComplianceFramework
    category: str
    title: str
    description: str
    requirement: str
    severity: str
    automated_check: bool
    check_query: Optional[str]
    remediation_steps: List[str]
    evidence_required: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "framework": self.framework.value,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "requirement": self.requirement,
            "severity": self.severity,
            "automated_check": self.automated_check,
            "check_query": self.check_query,
            "remediation_steps": self.remediation_steps,
            "evidence_required": self.evidence_required
        }


@dataclass
class ComplianceCheckResult:
    """Result of compliance check"""
    check_id: str
    rule_id: str
    status: ComplianceStatus
    timestamp: datetime
    details: Dict[str, Any]
    evidence: List[str]
    violations: List[str]
    remediation_required: bool
    risk_level: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "rule_id": self.rule_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "evidence": self.evidence,
            "violations": self.violations,
            "remediation_required": self.remediation_required,
            "risk_level": self.risk_level
        }


class ComplianceRuleEngine:
    """Engine for managing and executing compliance rules"""
    
    def __init__(self, postgresql_manager: PostgreSQLManager):
        self.postgresql = postgresql_manager
        self.logger = StructuredLogger(__name__)
        self.rules = {}
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default compliance rules"""
        default_rules = [
            # Data Retention Rules
            ComplianceRule(
                rule_id="DR001",
                framework=ComplianceFramework.GDPR,
                category="data_retention",
                title="Personal Data Retention Limit",
                description="Personal data must not be retained longer than necessary",
                requirement="Personal data retention must not exceed 365 days without explicit consent",
                severity="high",
                automated_check=True,
                check_query="""
                SELECT COUNT(*) as violation_count
                FROM audit_logs 
                WHERE data_classification = 'personal' 
                AND timestamp < NOW() - INTERVAL '365 days'
                """,
                remediation_steps=[
                    "Identify personal data older than 365 days",
                    "Verify if extended retention is legally justified",
                    "Anonymize or delete data if no legal basis exists"
                ],
                evidence_required=["retention_policy", "legal_basis_documentation"]
            ),
            
            # Access Control Rules
            ComplianceRule(
                rule_id="AC001",
                framework=ComplianceFramework.ISO27001,
                category="access_control",
                title="Privileged Access Monitoring",
                description="All privileged access must be monitored and logged",
                requirement="100% of privileged access attempts must be logged with user identification",
                severity="critical",
                automated_check=True,
                check_query="""
                SELECT 
                    COUNT(CASE WHEN user_id IS NULL THEN 1 END) as unidentified_access,
                    COUNT(*) as total_privileged_access
                FROM audit_logs 
                WHERE event_type = 'admin_action' 
                AND timestamp >= NOW() - INTERVAL '24 hours'
                """,
                remediation_steps=[
                    "Review unidentified privileged access attempts",
                    "Ensure all admin accounts have proper identification",
                    "Implement mandatory authentication for privileged operations"
                ],
                evidence_required=["access_logs", "user_authentication_records"]
            ),
            
            # Data Encryption Rules
            ComplianceRule(
                rule_id="DE001",
                framework=ComplianceFramework.NIST,
                category="data_encryption",
                title="Sensitive Data Encryption",
                description="All sensitive data must be encrypted at rest and in transit",
                requirement="Confidential and restricted data must use AES-256 encryption",
                severity="critical",
                automated_check=False,  # Requires manual verification
                check_query=None,
                remediation_steps=[
                    "Identify unencrypted sensitive data",
                    "Implement AES-256 encryption for data at rest",
                    "Ensure TLS 1.3 for data in transit",
                    "Update encryption key management procedures"
                ],
                evidence_required=["encryption_certificates", "key_management_policy"]
            ),
            
            # Audit Trail Rules
            ComplianceRule(
                rule_id="AT001",
                framework=ComplianceFramework.SOX,
                category="audit_trail",
                title="Complete Audit Trail",
                description="All system activities must maintain complete audit trails",
                requirement="Audit logs must capture user, timestamp, action, and outcome for all operations",
                severity="high",
                automated_check=True,
                check_query="""
                SELECT COUNT(*) as incomplete_logs
                FROM audit_logs 
                WHERE (user_id IS NULL OR action IS NULL OR outcome IS NULL)
                AND timestamp >= NOW() - INTERVAL '7 days'
                """,
                remediation_steps=[
                    "Review incomplete audit log entries",
                    "Update logging configuration to capture all required fields",
                    "Implement mandatory field validation for audit logs"
                ],
                evidence_required=["audit_log_samples", "logging_configuration"]
            ),
            
            # Data Access Rules
            ComplianceRule(
                rule_id="DA001",
                framework=ComplianceFramework.GDPR,
                category="data_access",
                title="Data Access Justification",
                description="Access to personal data must have documented business justification",
                requirement="All access to personal/confidential data must include access justification",
                severity="medium",
                automated_check=True,
                check_query="""
                SELECT COUNT(*) as unjustified_access
                FROM data_access_log 
                WHERE data_classification IN ('personal', 'confidential')
                AND (query_details->>'justification' IS NULL OR query_details->>'justification' = '')
                AND timestamp >= NOW() - INTERVAL '7 days'
                """,
                remediation_steps=[
                    "Implement mandatory justification fields for sensitive data access",
                    "Train users on proper access justification procedures",
                    "Review and approve access to sensitive data"
                ],
                evidence_required=["access_justification_records", "user_training_records"]
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
    
    async def execute_compliance_check(self, rule_id: str) -> ComplianceCheckResult:
        """Execute a specific compliance check"""
        rule = self.rules.get(rule_id)
        if not rule:
            raise ValueError(f"Unknown compliance rule: {rule_id}")
        
        check_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        if rule.automated_check and rule.check_query:
            # Execute automated check
            try:
                result = await self.postgresql.fetch_one(rule.check_query)
                status, violations = self._evaluate_check_result(rule, result)
                
                return ComplianceCheckResult(
                    check_id=check_id,
                    rule_id=rule_id,
                    status=status,
                    timestamp=timestamp,
                    details=dict(result) if result else {},
                    evidence=[],
                    violations=violations,
                    remediation_required=status != ComplianceStatus.COMPLIANT,
                    risk_level=rule.severity
                )
                
            except Exception as e:
                self.logger.error(f"Failed to execute compliance check {rule_id}: {e}")
                return ComplianceCheckResult(
                    check_id=check_id,
                    rule_id=rule_id,
                    status=ComplianceStatus.UNDER_REVIEW,
                    timestamp=timestamp,
                    details={"error": str(e)},
                    evidence=[],
                    violations=[f"Check execution failed: {e}"],
                    remediation_required=True,
                    risk_level="high"
                )
        else:
            # Manual check required
            return ComplianceCheckResult(
                check_id=check_id,
                rule_id=rule_id,
                status=ComplianceStatus.UNDER_REVIEW,
                timestamp=timestamp,
                details={"manual_check_required": True},
                evidence=[],
                violations=[],
                remediation_required=False,
                risk_level=rule.severity
            )
    
    def _evaluate_check_result(self, rule: ComplianceRule, 
                             result: Dict[str, Any]) -> Tuple[ComplianceStatus, List[str]]:
        """Evaluate check result against rule criteria"""
        violations = []
        
        if rule.rule_id == "DR001":  # Data retention check
            violation_count = result.get("violation_count", 0)
            if violation_count > 0:
                violations.append(f"{violation_count} records exceed retention period")
                return ComplianceStatus.NON_COMPLIANT, violations
        
        elif rule.rule_id == "AC001":  # Access control check
            unidentified = result.get("unidentified_access", 0)
            total = result.get("total_privileged_access", 0)
            if unidentified > 0:
                violations.append(f"{unidentified} out of {total} privileged access attempts lack user identification")
                return ComplianceStatus.NON_COMPLIANT, violations
        
        elif rule.rule_id == "AT001":  # Audit trail check
            incomplete = result.get("incomplete_logs", 0)
            if incomplete > 0:
                violations.append(f"{incomplete} audit log entries are incomplete")
                return ComplianceStatus.PARTIALLY_COMPLIANT, violations
        
        elif rule.rule_id == "DA001":  # Data access check
            unjustified = result.get("unjustified_access", 0)
            if unjustified > 0:
                violations.append(f"{unjustified} sensitive data access attempts lack justification")
                return ComplianceStatus.PARTIALLY_COMPLIANT, violations
        
        return ComplianceStatus.COMPLIANT, violations
    
    async def get_all_rules(self, framework: ComplianceFramework = None) -> List[ComplianceRule]:
        """Get all compliance rules, optionally filtered by framework"""
        if framework:
            return [rule for rule in self.rules.values() if rule.framework == framework]
        return list(self.rules.values())
    
    def add_custom_rule(self, rule: ComplianceRule):
        """Add custom compliance rule"""
        self.rules[rule.rule_id] = rule


class ComplianceReporter:
    """Main compliance reporting system"""
    
    def __init__(self, postgresql_manager: PostgreSQLManager,
                 mongodb_manager: MongoDBManager,
                 audit_logger: AuditLogger,
                 data_access_monitor: DataAccessMonitor):
        self.postgresql = postgresql_manager
        self.mongodb = mongodb_manager
        self.audit_logger = audit_logger
        self.data_access_monitor = data_access_monitor
        self.rule_engine = ComplianceRuleEngine(postgresql_manager)
        self.logger = StructuredLogger(__name__)
        self._setup_compliance_tables()
    
    async def _setup_compliance_tables(self):
        """Setup compliance reporting tables"""
        create_tables = """
        CREATE TABLE IF NOT EXISTS compliance_checks (
            id SERIAL PRIMARY KEY,
            check_id VARCHAR(255) UNIQUE NOT NULL,
            rule_id VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            details JSONB,
            evidence TEXT[],
            violations TEXT[],
            remediation_required BOOLEAN NOT NULL,
            risk_level VARCHAR(20) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS compliance_reports (
            id SERIAL PRIMARY KEY,
            report_id VARCHAR(255) UNIQUE NOT NULL,
            framework VARCHAR(50) NOT NULL,
            report_type VARCHAR(50) NOT NULL,
            start_date TIMESTAMP WITH TIME ZONE NOT NULL,
            end_date TIMESTAMP WITH TIME ZONE NOT NULL,
            overall_status VARCHAR(50) NOT NULL,
            total_checks INTEGER NOT NULL,
            compliant_checks INTEGER NOT NULL,
            non_compliant_checks INTEGER NOT NULL,
            report_data JSONB NOT NULL,
            generated_by VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_compliance_checks_rule ON compliance_checks(rule_id);
        CREATE INDEX IF NOT EXISTS idx_compliance_checks_status ON compliance_checks(status);
        CREATE INDEX IF NOT EXISTS idx_compliance_reports_framework ON compliance_reports(framework);
        """
        
        await self.postgresql.execute_query(create_tables)
    
    async def run_compliance_assessment(self, framework: ComplianceFramework = None) -> Dict[str, Any]:
        """Run comprehensive compliance assessment"""
        assessment_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        # Get rules to check
        rules = await self.rule_engine.get_all_rules(framework)
        
        # Execute all compliance checks
        check_results = []
        for rule in rules:
            try:
                result = await self.rule_engine.execute_compliance_check(rule.rule_id)
                check_results.append(result)
                
                # Store check result
                await self._store_compliance_check(result)
                
            except Exception as e:
                self.logger.error(f"Failed compliance check for rule {rule.rule_id}: {e}")
        
        # Calculate overall compliance status
        overall_status = self._calculate_overall_status(check_results)
        
        # Generate assessment report
        assessment_report = {
            "assessment_id": assessment_id,
            "timestamp": timestamp.isoformat(),
            "framework": framework.value if framework else "all",
            "overall_status": overall_status.value,
            "total_checks": len(check_results),
            "compliant_checks": len([r for r in check_results if r.status == ComplianceStatus.COMPLIANT]),
            "non_compliant_checks": len([r for r in check_results if r.status == ComplianceStatus.NON_COMPLIANT]),
            "partially_compliant_checks": len([r for r in check_results if r.status == ComplianceStatus.PARTIALLY_COMPLIANT]),
            "under_review_checks": len([r for r in check_results if r.status == ComplianceStatus.UNDER_REVIEW]),
            "check_results": [result.to_dict() for result in check_results],
            "recommendations": self._generate_recommendations(check_results)
        }
        
        # Log compliance assessment
        await self.audit_logger.log_event(
            event_type=AuditEventType.COMPLIANCE_EVENT,
            severity=AuditSeverity.MEDIUM,
            details={
                "assessment_id": assessment_id,
                "framework": framework.value if framework else "all",
                "overall_status": overall_status.value,
                "total_checks": len(check_results)
            }
        )
        
        return assessment_report
    
    async def _store_compliance_check(self, result: ComplianceCheckResult):
        """Store compliance check result"""
        query = """
        INSERT INTO compliance_checks (
            check_id, rule_id, status, timestamp, details, evidence,
            violations, remediation_required, risk_level
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        await self.postgresql.execute_query(
            query,
            result.check_id, result.rule_id, result.status.value,
            result.timestamp, json.dumps(result.details),
            result.evidence, result.violations,
            result.remediation_required, result.risk_level
        )
    
    def _calculate_overall_status(self, check_results: List[ComplianceCheckResult]) -> ComplianceStatus:
        """Calculate overall compliance status"""
        if not check_results:
            return ComplianceStatus.UNDER_REVIEW
        
        status_counts = {}
        for result in check_results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
        
        total_checks = len(check_results)
        compliant_count = status_counts.get(ComplianceStatus.COMPLIANT, 0)
        non_compliant_count = status_counts.get(ComplianceStatus.NON_COMPLIANT, 0)
        
        # If any critical violations, overall is non-compliant
        if non_compliant_count > 0:
            return ComplianceStatus.NON_COMPLIANT
        
        # If all checks are compliant
        if compliant_count == total_checks:
            return ComplianceStatus.COMPLIANT
        
        # Otherwise partially compliant
        return ComplianceStatus.PARTIALLY_COMPLIANT
    
    def _generate_recommendations(self, check_results: List[ComplianceCheckResult]) -> List[Dict[str, Any]]:
        """Generate compliance recommendations"""
        recommendations = []
        
        # Group violations by severity
        high_risk_violations = [r for r in check_results if r.risk_level == "critical" and r.violations]
        medium_risk_violations = [r for r in check_results if r.risk_level == "high" and r.violations]
        
        if high_risk_violations:
            recommendations.append({
                "priority": "critical",
                "title": "Address Critical Compliance Violations",
                "description": f"Found {len(high_risk_violations)} critical compliance violations requiring immediate attention",
                "actions": [
                    "Review all critical violations immediately",
                    "Implement emergency remediation procedures",
                    "Notify compliance officer and management"
                ]
            })
        
        if medium_risk_violations:
            recommendations.append({
                "priority": "high",
                "title": "Remediate High-Risk Compliance Issues",
                "description": f"Found {len(medium_risk_violations)} high-risk compliance issues",
                "actions": [
                    "Create remediation plan for high-risk issues",
                    "Assign responsible parties for each violation",
                    "Set target completion dates"
                ]
            })
        
        # Add general recommendations
        recommendations.append({
            "priority": "medium",
            "title": "Implement Continuous Compliance Monitoring",
            "description": "Establish automated compliance monitoring and alerting",
            "actions": [
                "Schedule regular compliance assessments",
                "Set up automated compliance alerts",
                "Train staff on compliance procedures"
            ]
        })
        
        return recommendations
    
    async def generate_compliance_report(self, framework: ComplianceFramework,
                                       start_date: datetime, end_date: datetime,
                                       report_type: str = "standard") -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        report_id = str(uuid.uuid4())
        
        # Get compliance check history
        checks_query = """
        SELECT * FROM compliance_checks 
        WHERE timestamp BETWEEN $1 AND $2
        ORDER BY timestamp DESC
        """
        
        checks = await self.postgresql.fetch_all(checks_query, start_date, end_date)
        
        # Get audit statistics
        audit_stats = await self.audit_logger.generate_compliance_report(start_date, end_date)
        
        # Get data access statistics
        access_stats = await self.data_access_monitor.get_access_summary(
            start_date=start_date, end_date=end_date
        )
        
        # Calculate compliance metrics
        total_checks = len(checks)
        compliant_checks = len([c for c in checks if c['status'] == 'compliant'])
        non_compliant_checks = len([c for c in checks if c['status'] == 'non_compliant'])
        
        compliance_percentage = (compliant_checks / total_checks * 100) if total_checks > 0 else 0
        
        # Generate report
        report = {
            "report_id": report_id,
            "framework": framework.value,
            "report_type": report_type,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "executive_summary": {
                "overall_compliance_percentage": round(compliance_percentage, 2),
                "total_compliance_checks": total_checks,
                "compliant_checks": compliant_checks,
                "non_compliant_checks": non_compliant_checks,
                "critical_violations": len([c for c in checks if c['risk_level'] == 'critical' and c['violations']]),
                "remediation_items": len([c for c in checks if c['remediation_required']])
            },
            "detailed_findings": {
                "compliance_checks": [dict(check) for check in checks],
                "audit_statistics": audit_stats,
                "data_access_statistics": access_stats
            },
            "risk_assessment": self._generate_risk_assessment(checks),
            "recommendations": self._generate_detailed_recommendations(checks),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": "automated_compliance_system"
        }
        
        # Store report
        await self._store_compliance_report(report)
        
        return report
    
    def _generate_risk_assessment(self, checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate risk assessment from compliance checks"""
        risk_levels = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for check in checks:
            if check['violations']:
                risk_level = check['risk_level']
                risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
        
        total_risks = sum(risk_levels.values())
        overall_risk = "low"
        
        if risk_levels["critical"] > 0:
            overall_risk = "critical"
        elif risk_levels["high"] > 0:
            overall_risk = "high"
        elif risk_levels["medium"] > 0:
            overall_risk = "medium"
        
        return {
            "overall_risk_level": overall_risk,
            "risk_distribution": risk_levels,
            "total_risk_items": total_risks,
            "risk_score": self._calculate_risk_score(risk_levels)
        }
    
    def _calculate_risk_score(self, risk_levels: Dict[str, int]) -> float:
        """Calculate numerical risk score"""
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        
        total_score = sum(count * weights[level] for level, count in risk_levels.items())
        max_possible = 100  # Arbitrary maximum for normalization
        
        return min(100.0, (total_score / max_possible) * 100)
    
    def _generate_detailed_recommendations(self, checks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate detailed recommendations based on compliance checks"""
        recommendations = []
        
        # Group checks by rule and status
        rule_violations = {}
        for check in checks:
            if check['violations']:
                rule_id = check['rule_id']
                if rule_id not in rule_violations:
                    rule_violations[rule_id] = []
                rule_violations[rule_id].append(check)
        
        # Generate specific recommendations for each violated rule
        for rule_id, violations in rule_violations.items():
            rule = self.rule_engine.rules.get(rule_id)
            if rule:
                recommendations.append({
                    "rule_id": rule_id,
                    "title": f"Address {rule.title} Violations",
                    "category": rule.category,
                    "severity": rule.severity,
                    "violation_count": len(violations),
                    "description": rule.description,
                    "remediation_steps": rule.remediation_steps,
                    "evidence_required": rule.evidence_required
                })
        
        return recommendations
    
    async def _store_compliance_report(self, report: Dict[str, Any]):
        """Store compliance report"""
        query = """
        INSERT INTO compliance_reports (
            report_id, framework, report_type, start_date, end_date,
            overall_status, total_checks, compliant_checks, non_compliant_checks,
            report_data, generated_by
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """
        
        exec_summary = report["executive_summary"]
        overall_status = "compliant" if exec_summary["non_compliant_checks"] == 0 else "non_compliant"
        
        await self.postgresql.execute_query(
            query,
            report["report_id"], report["framework"], report["report_type"],
            datetime.fromisoformat(report["period"]["start_date"]),
            datetime.fromisoformat(report["period"]["end_date"]),
            overall_status, exec_summary["total_compliance_checks"],
            exec_summary["compliant_checks"], exec_summary["non_compliant_checks"],
            json.dumps(report), report["generated_by"]
        )
    
    async def schedule_automated_compliance_checks(self):
        """Schedule automated compliance checks"""
        # This would integrate with a task scheduler like Celery or APScheduler
        # For now, we'll create a simple implementation
        
        self.logger.info("Starting automated compliance monitoring")
        
        while True:
            try:
                # Run daily compliance assessment
                assessment = await self.run_compliance_assessment()
                
                # Check for critical violations
                critical_violations = [
                    result for result in assessment["check_results"]
                    if result["status"] == "non_compliant" and result["risk_level"] == "critical"
                ]
                
                if critical_violations:
                    # Generate critical compliance alert
                    await self.audit_logger.log_security_event(
                        event_type="critical_compliance_violation",
                        severity=AuditSeverity.CRITICAL,
                        details={
                            "assessment_id": assessment["assessment_id"],
                            "critical_violations": len(critical_violations),
                            "violation_details": critical_violations
                        }
                    )
                
                # Wait 24 hours before next check
                await asyncio.sleep(24 * 60 * 60)
                
            except Exception as e:
                self.logger.error(f"Error in automated compliance check: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour before retry
    
    async def get_compliance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for compliance dashboard"""
        # Get recent compliance status
        recent_checks_query = """
        SELECT 
            status,
            COUNT(*) as count,
            risk_level
        FROM compliance_checks 
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY status, risk_level
        ORDER BY count DESC
        """
        
        recent_checks = await self.postgresql.fetch_all(recent_checks_query)
        
        # Get compliance trends
        trends_query = """
        SELECT 
            DATE(timestamp) as check_date,
            COUNT(*) as total_checks,
            SUM(CASE WHEN status = 'compliant' THEN 1 ELSE 0 END) as compliant_count
        FROM compliance_checks 
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(timestamp)
        ORDER BY check_date
        """
        
        trends = await self.postgresql.fetch_all(trends_query)
        
        # Get top violations
        violations_query = """
        SELECT 
            rule_id,
            COUNT(*) as violation_count,
            MAX(timestamp) as last_violation
        FROM compliance_checks 
        WHERE violations IS NOT NULL AND array_length(violations, 1) > 0
        AND timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY rule_id
        ORDER BY violation_count DESC
        LIMIT 10
        """
        
        violations = await self.postgresql.fetch_all(violations_query)
        
        return {
            "recent_compliance_status": [dict(row) for row in recent_checks],
            "compliance_trends": [dict(row) for row in trends],
            "top_violations": [dict(row) for row in violations],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }