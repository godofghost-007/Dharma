"""
Compliance Reporter

Generates comprehensive compliance reports for various regulations
and standards including GDPR, data retention, and security compliance.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import logging
from pymongo import MongoClient
import asyncpg
from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)


class ComplianceRegulation(Enum):
    """Supported compliance regulations"""
    GDPR = "gdpr"
    CCPA = "ccpa"
    PIPEDA = "pipeda"
    DATA_RETENTION = "data_retention"
    SECURITY_STANDARDS = "security_standards"
    AUDIT_REQUIREMENTS = "audit_requirements"


class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNDER_REVIEW = "under_review"


@dataclass
class ComplianceIssue:
    """Individual compliance issue"""
    regulation: ComplianceRegulation
    severity: str  # high, medium, low
    description: str
    affected_records: int
    recommendation: str
    deadline: Optional[datetime] = None


@dataclass
class ComplianceReport:
    """Comprehensive compliance report"""
    regulation: ComplianceRegulation
    status: ComplianceStatus
    score: float
    issues: List[ComplianceIssue]
    recommendations: List[str]
    generated_at: datetime
    report_period: Dict[str, datetime]


class ComplianceReporter:
    """
    Comprehensive compliance reporting system for data governance
    """
    
    def __init__(self, mongodb_client: MongoClient,
                 postgresql_pool: asyncpg.Pool,
                 elasticsearch_client: AsyncElasticsearch):
        self.mongodb = mongodb_client
        self.postgresql = postgresql_pool
        self.elasticsearch = elasticsearch_client
        
    async def generate_comprehensive_report(self, 
                                          start_date: datetime,
                                          end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive compliance report for all regulations"""
        try:
            reports = {}
            
            # Generate reports for each regulation
            for regulation in ComplianceRegulation:
                report = await self.generate_regulation_report(
                    regulation, start_date, end_date
                )
                reports[regulation.value] = report
            
            # Calculate overall compliance score
            overall_score = sum(r.score for r in reports.values()) / len(reports)
            
            # Aggregate all issues
            all_issues = []
            for report in reports.values():
                all_issues.extend(report.issues)
            
            # Sort issues by severity
            high_priority_issues = [i for i in all_issues if i.severity == "high"]
            medium_priority_issues = [i for i in all_issues if i.severity == "medium"]
            low_priority_issues = [i for i in all_issues if i.severity == "low"]
            
            return {
                'summary': {
                    'overall_score': overall_score,
                    'overall_status': self._determine_overall_status(overall_score),
                    'total_issues': len(all_issues),
                    'high_priority_issues': len(high_priority_issues),
                    'medium_priority_issues': len(medium_priority_issues),
                    'low_priority_issues': len(low_priority_issues),
                    'report_period': {
                        'start_date': start_date,
                        'end_date': end_date
                    },
                    'generated_at': datetime.utcnow()
                },
                'regulation_reports': {
                    reg.value: {
                        'status': report.status.value,
                        'score': report.score,
                        'issues_count': len(report.issues),
                        'recommendations_count': len(report.recommendations)
                    }
                    for reg, report in reports.items()
                },
                'priority_issues': {
                    'high': [self._serialize_issue(i) for i in high_priority_issues[:10]],
                    'medium': [self._serialize_issue(i) for i in medium_priority_issues[:10]],
                    'low': [self._serialize_issue(i) for i in low_priority_issues[:10]]
                },
                'detailed_reports': {
                    reg.value: self._serialize_report(report)
                    for reg, report in reports.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive compliance report: {e}")
            raise
    
    async def generate_regulation_report(self, 
                                       regulation: ComplianceRegulation,
                                       start_date: datetime,
                                       end_date: datetime) -> ComplianceReport:
        """Generate compliance report for a specific regulation"""
        if regulation == ComplianceRegulation.GDPR:
            return await self._generate_gdpr_report(start_date, end_date)
        elif regulation == ComplianceRegulation.DATA_RETENTION:
            return await self._generate_retention_report(start_date, end_date)
        elif regulation == ComplianceRegulation.SECURITY_STANDARDS:
            return await self._generate_security_report(start_date, end_date)
        elif regulation == ComplianceRegulation.AUDIT_REQUIREMENTS:
            return await self._generate_audit_report(start_date, end_date)
        else:
            # Default implementation for other regulations
            return await self._generate_default_report(regulation, start_date, end_date)
    
    async def _generate_gdpr_report(self, start_date: datetime, 
                                  end_date: datetime) -> ComplianceReport:
        """Generate GDPR compliance report"""
        db = self.mongodb.dharma_platform
        issues = []
        
        # Check for unclassified personal data
        unclassified_personal = await db.posts.count_documents({
            '$and': [
                {'content': {'$regex': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'}},
                {'_classification': {'$exists': False}},
                {'created_at': {'$gte': start_date, '$lte': end_date}}
            ]
        })
        
        if unclassified_personal > 0:
            issues.append(ComplianceIssue(
                regulation=ComplianceRegulation.GDPR,
                severity="high",
                description=f"{unclassified_personal} documents contain potential personal data but are not classified",
                affected_records=unclassified_personal,
                recommendation="Implement automated data classification for all incoming data",
                deadline=datetime.utcnow() + timedelta(days=30)
            ))
        
        # Check for data without consent tracking
        no_consent = await db.posts.count_documents({
            '$and': [
                {'_classification.data_types': 'personal_identifiable'},
                {'consent_status': {'$exists': False}},
                {'created_at': {'$gte': start_date, '$lte': end_date}}
            ]
        })
        
        if no_consent > 0:
            issues.append(ComplianceIssue(
                regulation=ComplianceRegulation.GDPR,
                severity="high",
                description=f"{no_consent} personal data records lack consent tracking",
                affected_records=no_consent,
                recommendation="Implement consent management system for all personal data"
            ))
        
        # Check for data without retention policies
        no_retention = await db.posts.count_documents({
            '$and': [
                {'_classification.sensitivity_level': {'$in': ['confidential', 'restricted']}},
                {'_retention_policy': {'$exists': False}},
                {'created_at': {'$gte': start_date, '$lte': end_date}}
            ]
        })
        
        if no_retention > 0:
            issues.append(ComplianceIssue(
                regulation=ComplianceRegulation.GDPR,
                severity="medium",
                description=f"{no_retention} sensitive records lack retention policies",
                affected_records=no_retention,
                recommendation="Apply appropriate retention policies to all sensitive data"
            ))
        
        # Check for data subject rights implementation
        async with self.postgresql.acquire() as conn:
            # Check if data subject rights tables exist
            rights_tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name IN ('data_subject_requests', 'consent_records')
            """)
            
            if len(rights_tables) < 2:
                issues.append(ComplianceIssue(
                    regulation=ComplianceRegulation.GDPR,
                    severity="high",
                    description="Data subject rights infrastructure not implemented",
                    affected_records=0,
                    recommendation="Implement data subject rights management system (access, rectification, erasure, portability)"
                ))
        
        # Calculate compliance score
        total_personal_data = await db.posts.count_documents({
            '_classification.data_types': 'personal_identifiable',
            'created_at': {'$gte': start_date, '$lte': end_date}
        })
        
        if total_personal_data > 0:
            compliant_records = total_personal_data - sum(i.affected_records for i in issues)
            score = max(0, (compliant_records / total_personal_data) * 100)
        else:
            score = 100  # No personal data = compliant
        
        recommendations = [
            "Implement comprehensive data classification system",
            "Deploy consent management platform",
            "Establish data subject rights procedures",
            "Conduct regular GDPR compliance audits",
            "Train staff on GDPR requirements"
        ]
        
        return ComplianceReport(
            regulation=ComplianceRegulation.GDPR,
            status=self._determine_status_from_score(score),
            score=score,
            issues=issues,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            report_period={'start_date': start_date, 'end_date': end_date}
        )
    
    async def _generate_retention_report(self, start_date: datetime, 
                                       end_date: datetime) -> ComplianceReport:
        """Generate data retention compliance report"""
        db = self.mongodb.dharma_platform
        issues = []
        
        # Check for data exceeding retention periods
        cutoff_dates = {
            'posts': datetime.utcnow() - timedelta(days=365),  # 1 year
            'analysis_results': datetime.utcnow() - timedelta(days=180),  # 6 months
            'system_logs': datetime.utcnow() - timedelta(days=90)  # 3 months
        }
        
        for collection_name, cutoff_date in cutoff_dates.items():
            if collection_name in ['posts', 'analysis_results']:
                collection = db[collection_name]
                overdue_count = await collection.count_documents({
                    'created_at': {'$lt': cutoff_date}
                })
                
                if overdue_count > 0:
                    issues.append(ComplianceIssue(
                        regulation=ComplianceRegulation.DATA_RETENTION,
                        severity="medium",
                        description=f"{overdue_count} {collection_name} records exceed retention period",
                        affected_records=overdue_count,
                        recommendation=f"Execute retention policy for {collection_name} collection"
                    ))
        
        # Check retention policy coverage
        total_records = await db.posts.count_documents({})
        records_with_policy = await db.posts.count_documents({
            '_retention_policy': {'$exists': True}
        })
        
        if total_records > 0:
            coverage = (records_with_policy / total_records) * 100
            if coverage < 90:
                issues.append(ComplianceIssue(
                    regulation=ComplianceRegulation.DATA_RETENTION,
                    severity="high",
                    description=f"Only {coverage:.1f}% of records have retention policies",
                    affected_records=total_records - records_with_policy,
                    recommendation="Apply retention policies to all data collections"
                ))
        
        # Calculate score based on policy coverage and overdue records
        if total_records > 0:
            overdue_records = sum(i.affected_records for i in issues if "exceed retention" in i.description)
            score = max(0, ((total_records - overdue_records) / total_records) * 100)
        else:
            score = 100
        
        recommendations = [
            "Implement automated retention policy enforcement",
            "Regular monitoring of retention compliance",
            "Establish clear retention schedules for all data types",
            "Implement secure data disposal procedures"
        ]
        
        return ComplianceReport(
            regulation=ComplianceRegulation.DATA_RETENTION,
            status=self._determine_status_from_score(score),
            score=score,
            issues=issues,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            report_period={'start_date': start_date, 'end_date': end_date}
        )
    
    async def _generate_security_report(self, start_date: datetime, 
                                      end_date: datetime) -> ComplianceReport:
        """Generate security compliance report"""
        db = self.mongodb.dharma_platform
        issues = []
        
        # Check for unencrypted sensitive data
        sensitive_unencrypted = await db.posts.count_documents({
            '$and': [
                {'_classification.sensitivity_level': 'restricted'},
                {'_encrypted': {'$ne': True}},
                {'created_at': {'$gte': start_date, '$lte': end_date}}
            ]
        })
        
        if sensitive_unencrypted > 0:
            issues.append(ComplianceIssue(
                regulation=ComplianceRegulation.SECURITY_STANDARDS,
                severity="high",
                description=f"{sensitive_unencrypted} restricted documents are not encrypted",
                affected_records=sensitive_unencrypted,
                recommendation="Encrypt all restricted and confidential data at rest"
            ))
        
        # Check audit logging coverage
        async with self.postgresql.acquire() as conn:
            total_user_actions = await conn.fetchval("""
                SELECT COUNT(*) FROM audit_logs 
                WHERE timestamp >= $1 AND timestamp <= $2
            """, start_date, end_date)
            
            if total_user_actions == 0:
                issues.append(ComplianceIssue(
                    regulation=ComplianceRegulation.SECURITY_STANDARDS,
                    severity="high",
                    description="No audit logs found for the reporting period",
                    affected_records=0,
                    recommendation="Ensure comprehensive audit logging is enabled"
                ))
        
        # Check access control implementation
        users_without_roles = await db.users.count_documents({
            'role': {'$exists': False}
        })
        
        if users_without_roles > 0:
            issues.append(ComplianceIssue(
                regulation=ComplianceRegulation.SECURITY_STANDARDS,
                severity="medium",
                description=f"{users_without_roles} users lack proper role assignments",
                affected_records=users_without_roles,
                recommendation="Implement role-based access control for all users"
            ))
        
        # Calculate security score
        total_sensitive = await db.posts.count_documents({
            '_classification.sensitivity_level': {'$in': ['confidential', 'restricted']},
            'created_at': {'$gte': start_date, '$lte': end_date}
        })
        
        if total_sensitive > 0:
            secure_records = total_sensitive - sensitive_unencrypted
            score = (secure_records / total_sensitive) * 100
        else:
            score = 100
        
        recommendations = [
            "Implement end-to-end encryption for sensitive data",
            "Deploy comprehensive audit logging",
            "Establish role-based access controls",
            "Regular security assessments and penetration testing",
            "Implement multi-factor authentication"
        ]
        
        return ComplianceReport(
            regulation=ComplianceRegulation.SECURITY_STANDARDS,
            status=self._determine_status_from_score(score),
            score=score,
            issues=issues,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            report_period={'start_date': start_date, 'end_date': end_date}
        )
    
    async def _generate_audit_report(self, start_date: datetime, 
                                   end_date: datetime) -> ComplianceReport:
        """Generate audit requirements compliance report"""
        issues = []
        
        async with self.postgresql.acquire() as conn:
            # Check audit log completeness
            audit_gaps = await conn.fetch("""
                SELECT DATE(timestamp) as audit_date, COUNT(*) as log_count
                FROM audit_logs 
                WHERE timestamp >= $1 AND timestamp <= $2
                GROUP BY DATE(timestamp)
                HAVING COUNT(*) < 10  -- Minimum expected daily logs
            """, start_date, end_date)
            
            if audit_gaps:
                issues.append(ComplianceIssue(
                    regulation=ComplianceRegulation.AUDIT_REQUIREMENTS,
                    severity="medium",
                    description=f"Audit logging gaps detected on {len(audit_gaps)} days",
                    affected_records=len(audit_gaps),
                    recommendation="Investigate and resolve audit logging gaps"
                ))
            
            # Check for critical actions without audit trails
            critical_actions = await conn.fetchval("""
                SELECT COUNT(*) FROM audit_logs 
                WHERE action IN ('DELETE', 'MODIFY_SENSITIVE', 'ACCESS_RESTRICTED')
                AND timestamp >= $1 AND timestamp <= $2
            """, start_date, end_date)
            
            if critical_actions == 0:
                issues.append(ComplianceIssue(
                    regulation=ComplianceRegulation.AUDIT_REQUIREMENTS,
                    severity="high",
                    description="No critical actions logged during reporting period",
                    affected_records=0,
                    recommendation="Verify audit logging for critical operations"
                ))
        
        # Calculate audit score
        expected_days = (end_date - start_date).days
        days_with_gaps = len(audit_gaps) if 'audit_gaps' in locals() else 0
        score = max(0, ((expected_days - days_with_gaps) / expected_days) * 100) if expected_days > 0 else 100
        
        recommendations = [
            "Implement comprehensive audit trail coverage",
            "Regular audit log integrity checks",
            "Establish audit log retention policies",
            "Monitor audit system availability"
        ]
        
        return ComplianceReport(
            regulation=ComplianceRegulation.AUDIT_REQUIREMENTS,
            status=self._determine_status_from_score(score),
            score=score,
            issues=issues,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            report_period={'start_date': start_date, 'end_date': end_date}
        )
    
    async def _generate_default_report(self, regulation: ComplianceRegulation,
                                     start_date: datetime, 
                                     end_date: datetime) -> ComplianceReport:
        """Generate default compliance report for unsupported regulations"""
        return ComplianceReport(
            regulation=regulation,
            status=ComplianceStatus.UNDER_REVIEW,
            score=0.0,
            issues=[],
            recommendations=[f"Implement compliance checking for {regulation.value}"],
            generated_at=datetime.utcnow(),
            report_period={'start_date': start_date, 'end_date': end_date}
        )
    
    def _determine_status_from_score(self, score: float) -> ComplianceStatus:
        """Determine compliance status from score"""
        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 80:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            return ComplianceStatus.NON_COMPLIANT
    
    def _determine_overall_status(self, overall_score: float) -> str:
        """Determine overall compliance status"""
        if overall_score >= 95:
            return "compliant"
        elif overall_score >= 80:
            return "partially_compliant"
        else:
            return "non_compliant"
    
    def _serialize_issue(self, issue: ComplianceIssue) -> Dict[str, Any]:
        """Serialize compliance issue for JSON output"""
        return {
            'regulation': issue.regulation.value,
            'severity': issue.severity,
            'description': issue.description,
            'affected_records': issue.affected_records,
            'recommendation': issue.recommendation,
            'deadline': issue.deadline.isoformat() if issue.deadline else None
        }
    
    def _serialize_report(self, report: ComplianceReport) -> Dict[str, Any]:
        """Serialize compliance report for JSON output"""
        return {
            'regulation': report.regulation.value,
            'status': report.status.value,
            'score': report.score,
            'issues': [self._serialize_issue(issue) for issue in report.issues],
            'recommendations': report.recommendations,
            'generated_at': report.generated_at.isoformat(),
            'report_period': {
                'start_date': report.report_period['start_date'].isoformat(),
                'end_date': report.report_period['end_date'].isoformat()
            }
        }
    
    async def export_compliance_report(self, report_data: Dict[str, Any], 
                                     format_type: str = "json") -> str:
        """Export compliance report in specified format"""
        if format_type.lower() == "json":
            return json.dumps(report_data, indent=2, default=str)
        elif format_type.lower() == "csv":
            # Implement CSV export if needed
            pass
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    async def schedule_compliance_monitoring(self, 
                                           regulations: List[ComplianceRegulation],
                                           check_interval: timedelta = timedelta(days=1)):
        """Schedule regular compliance monitoring"""
        logger.info(f"Starting compliance monitoring for {len(regulations)} regulations")
        
        while True:
            try:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=7)  # Weekly reports
                
                for regulation in regulations:
                    report = await self.generate_regulation_report(
                        regulation, start_date, end_date
                    )
                    
                    # Log compliance status
                    logger.info(f"{regulation.value} compliance: {report.status.value} (score: {report.score:.1f})")
                    
                    # Alert on non-compliance
                    if report.status == ComplianceStatus.NON_COMPLIANT:
                        logger.warning(f"Non-compliance detected for {regulation.value}")
                        # Could trigger alerts here
                
                await asyncio.sleep(check_interval.total_seconds())
                
            except Exception as e:
                logger.error(f"Error in compliance monitoring: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error