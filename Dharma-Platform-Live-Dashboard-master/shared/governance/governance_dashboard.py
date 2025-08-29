"""
Data Governance Dashboard

Provides comprehensive dashboard and reporting capabilities for data governance,
including retention status, classification metrics, and compliance tracking.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from pymongo import MongoClient
import asyncpg
from elasticsearch import AsyncElasticsearch

from .retention_manager import RetentionManager, RetentionJob
from .data_classifier import DataClassifier, ClassificationResult, SensitivityLevel
from .data_anonymizer import DataAnonymizer

logger = logging.getLogger(__name__)


@dataclass
class GovernanceMetrics:
    """Data governance metrics"""
    total_documents: int
    classified_documents: int
    anonymized_documents: int
    retention_policies_active: int
    compliance_score: float
    last_updated: datetime


@dataclass
class ComplianceStatus:
    """Compliance status information"""
    regulation: str
    status: str
    last_audit: datetime
    issues_count: int
    recommendations: List[str]


class GovernanceDashboard:
    """
    Comprehensive data governance dashboard and reporting system
    """
    
    def __init__(self, mongodb_client: MongoClient,
                 postgresql_pool: asyncpg.Pool,
                 elasticsearch_client: AsyncElasticsearch,
                 retention_manager: RetentionManager,
                 data_classifier: DataClassifier):
        self.mongodb = mongodb_client
        self.postgresql = postgresql_pool
        self.elasticsearch = elasticsearch_client
        self.retention_manager = retention_manager
        self.data_classifier = data_classifier
        
    async def get_governance_overview(self) -> Dict[str, Any]:
        """Get comprehensive governance overview"""
        try:
            # Get basic metrics
            metrics = await self._calculate_governance_metrics()
            
            # Get retention status
            retention_status = self.retention_manager.get_retention_status()
            
            # Get classification statistics
            classification_stats = await self._get_classification_statistics()
            
            # Get compliance status
            compliance_status = await self._get_compliance_status()
            
            # Get recent activities
            recent_activities = await self._get_recent_activities()
            
            return {
                'overview': {
                    'total_documents': metrics.total_documents,
                    'classified_documents': metrics.classified_documents,
                    'anonymized_documents': metrics.anonymized_documents,
                    'compliance_score': metrics.compliance_score,
                    'last_updated': metrics.last_updated
                },
                'retention': retention_status,
                'classification': classification_stats,
                'compliance': compliance_status,
                'recent_activities': recent_activities
            }
            
        except Exception as e:
            logger.error(f"Error generating governance overview: {e}")
            raise
    
    async def _calculate_governance_metrics(self) -> GovernanceMetrics:
        """Calculate core governance metrics"""
        db = self.mongodb.dharma_platform
        
        # Count total documents across collections
        total_docs = 0
        collections = ['posts', 'users', 'campaigns', 'analysis_results']
        
        for collection_name in collections:
            collection = db[collection_name]
            count = await collection.count_documents({})
            total_docs += count
        
        # Count classified documents
        classified_docs = await db.posts.count_documents({
            '_classification': {'$exists': True}
        })
        
        # Count anonymized documents
        anonymized_docs = await db.posts.count_documents({
            '_anonymization_audit': {'$exists': True}
        })
        
        # Calculate compliance score
        compliance_score = await self._calculate_compliance_score()
        
        return GovernanceMetrics(
            total_documents=total_docs,
            classified_documents=classified_docs,
            anonymized_documents=anonymized_docs,
            retention_policies_active=len([p for p in self.retention_manager.policies if p.enabled]),
            compliance_score=compliance_score,
            last_updated=datetime.utcnow()
        )
    
    async def _get_classification_statistics(self) -> Dict[str, Any]:
        """Get data classification statistics"""
        db = self.mongodb.dharma_platform
        
        # Aggregate classification results
        pipeline = [
            {'$match': {'_classification': {'$exists': True}}},
            {'$group': {
                '_id': '$_classification.sensitivity_level',
                'count': {'$sum': 1}
            }}
        ]
        
        sensitivity_distribution = {}
        async for result in db.posts.aggregate(pipeline):
            sensitivity_distribution[result['_id']] = result['count']
        
        # Get data type distribution
        pipeline = [
            {'$match': {'_classification.data_types': {'$exists': True}}},
            {'$unwind': '$_classification.data_types'},
            {'$group': {
                '_id': '$_classification.data_types',
                'count': {'$sum': 1}
            }}
        ]
        
        data_type_distribution = {}
        async for result in db.posts.aggregate(pipeline):
            data_type_distribution[result['_id']] = result['count']
        
        # Calculate average confidence
        pipeline = [
            {'$match': {'_classification.confidence_score': {'$exists': True}}},
            {'$group': {
                '_id': None,
                'avg_confidence': {'$avg': '$_classification.confidence_score'},
                'total_classified': {'$sum': 1}
            }}
        ]
        
        confidence_stats = await db.posts.aggregate(pipeline).to_list(1)
        avg_confidence = confidence_stats[0]['avg_confidence'] if confidence_stats else 0.0
        
        return {
            'sensitivity_distribution': sensitivity_distribution,
            'data_type_distribution': data_type_distribution,
            'average_confidence': avg_confidence,
            'classification_coverage': (
                sum(sensitivity_distribution.values()) / 
                await db.posts.count_documents({}) * 100
                if await db.posts.count_documents({}) > 0 else 0
            )
        }
    
    async def _get_compliance_status(self) -> List[ComplianceStatus]:
        """Get compliance status for various regulations"""
        compliance_statuses = []
        
        # GDPR Compliance
        gdpr_status = await self._check_gdpr_compliance()
        compliance_statuses.append(gdpr_status)
        
        # Data Retention Compliance
        retention_status = await self._check_retention_compliance()
        compliance_statuses.append(retention_status)
        
        # Security Compliance
        security_status = await self._check_security_compliance()
        compliance_statuses.append(security_status)
        
        return compliance_statuses
    
    async def _check_gdpr_compliance(self) -> ComplianceStatus:
        """Check GDPR compliance status"""
        db = self.mongodb.dharma_platform
        issues = []
        
        # Check for unclassified personal data
        unclassified_personal = await db.posts.count_documents({
            '$and': [
                {'content': {'$regex': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'}},
                {'_classification': {'$exists': False}}
            ]
        })
        
        if unclassified_personal > 0:
            issues.append(f"{unclassified_personal} documents with potential personal data not classified")
        
        # Check for data without retention policies
        no_retention = await db.posts.count_documents({
            '_retention_policy': {'$exists': False}
        })
        
        if no_retention > 0:
            issues.append(f"{no_retention} documents without retention policies")
        
        recommendations = []
        if issues:
            recommendations.extend([
                "Implement automated data classification",
                "Apply retention policies to all personal data",
                "Conduct regular data audits"
            ])
        
        return ComplianceStatus(
            regulation="GDPR",
            status="compliant" if not issues else "non_compliant",
            last_audit=datetime.utcnow() - timedelta(days=30),
            issues_count=len(issues),
            recommendations=recommendations
        )
    
    async def _check_retention_compliance(self) -> ComplianceStatus:
        """Check data retention compliance"""
        retention_status = self.retention_manager.get_retention_status()
        issues = []
        
        if retention_status['failed_jobs'] > 0:
            issues.append(f"{retention_status['failed_jobs']} retention jobs failed")
        
        if retention_status['active_policies'] == 0:
            issues.append("No active retention policies configured")
        
        recommendations = []
        if issues:
            recommendations.extend([
                "Review and fix failed retention jobs",
                "Ensure all data types have retention policies",
                "Monitor retention job execution regularly"
            ])
        
        return ComplianceStatus(
            regulation="Data Retention",
            status="compliant" if not issues else "non_compliant",
            last_audit=datetime.utcnow(),
            issues_count=len(issues),
            recommendations=recommendations
        )
    
    async def _check_security_compliance(self) -> ComplianceStatus:
        """Check security compliance status"""
        db = self.mongodb.dharma_platform
        issues = []
        
        # Check for unencrypted sensitive data
        sensitive_unencrypted = await db.posts.count_documents({
            '$and': [
                {'_classification.sensitivity_level': 'restricted'},
                {'_encrypted': {'$ne': True}}
            ]
        })
        
        if sensitive_unencrypted > 0:
            issues.append(f"{sensitive_unencrypted} sensitive documents not encrypted")
        
        recommendations = []
        if issues:
            recommendations.extend([
                "Encrypt all sensitive data at rest",
                "Implement access controls for restricted data",
                "Enable comprehensive audit logging"
            ])
        
        return ComplianceStatus(
            regulation="Security",
            status="compliant" if not issues else "non_compliant",
            last_audit=datetime.utcnow() - timedelta(days=7),
            issues_count=len(issues),
            recommendations=recommendations
        )
    
    async def _calculate_compliance_score(self) -> float:
        """Calculate overall compliance score"""
        compliance_statuses = await self._get_compliance_status()
        
        if not compliance_statuses:
            return 0.0
        
        compliant_count = len([s for s in compliance_statuses if s.status == "compliant"])
        return (compliant_count / len(compliance_statuses)) * 100
    
    async def _get_recent_activities(self) -> List[Dict[str, Any]]:
        """Get recent governance activities"""
        activities = []
        
        # Recent retention jobs
        recent_jobs = [j for j in self.retention_manager.jobs 
                      if j.scheduled_time > datetime.utcnow() - timedelta(days=7)]
        
        for job in recent_jobs[-10:]:  # Last 10 jobs
            activities.append({
                'type': 'retention_job',
                'description': f"Retention policy '{job.policy_name}' executed",
                'timestamp': job.scheduled_time,
                'status': job.status,
                'details': {
                    'records_processed': job.records_processed,
                    'records_affected': job.records_affected
                }
            })
        
        # Recent classification activities (simulated)
        db = self.mongodb.dharma_platform
        recent_classifications = await db.posts.find({
            '_classification.classification_timestamp': {
                '$gte': datetime.utcnow() - timedelta(days=7)
            }
        }).limit(5).to_list(5)
        
        for doc in recent_classifications:
            classification = doc.get('_classification', {})
            activities.append({
                'type': 'classification',
                'description': f"Document classified as {classification.get('sensitivity_level', 'unknown')}",
                'timestamp': classification.get('classification_timestamp', datetime.utcnow()),
                'status': 'completed',
                'details': {
                    'confidence_score': classification.get('confidence_score', 0),
                    'data_types': classification.get('data_types', [])
                }
            })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:20]  # Return last 20 activities
    
    async def generate_governance_report(self, start_date: datetime, 
                                       end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive governance report for a date range"""
        try:
            # Get overview for the period
            overview = await self.get_governance_overview()
            
            # Get retention activities in the period
            retention_activities = [
                job for job in self.retention_manager.jobs
                if start_date <= job.scheduled_time <= end_date
            ]
            
            # Calculate period statistics
            period_stats = {
                'retention_jobs_executed': len(retention_activities),
                'successful_jobs': len([j for j in retention_activities if j.status == 'completed']),
                'failed_jobs': len([j for j in retention_activities if j.status == 'failed']),
                'total_records_processed': sum(j.records_processed for j in retention_activities),
                'total_records_affected': sum(j.records_affected for j in retention_activities)
            }
            
            # Get compliance trends
            compliance_trends = await self._get_compliance_trends(start_date, end_date)
            
            return {
                'report_period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'generated_at': datetime.utcnow()
                },
                'overview': overview,
                'period_statistics': period_stats,
                'compliance_trends': compliance_trends,
                'retention_activities': [
                    {
                        'policy_name': job.policy_name,
                        'scheduled_time': job.scheduled_time,
                        'status': job.status,
                        'records_processed': job.records_processed,
                        'records_affected': job.records_affected,
                        'error_message': job.error_message
                    }
                    for job in retention_activities
                ],
                'recommendations': await self._generate_governance_recommendations()
            }
            
        except Exception as e:
            logger.error(f"Error generating governance report: {e}")
            raise
    
    async def _get_compliance_trends(self, start_date: datetime, 
                                   end_date: datetime) -> Dict[str, Any]:
        """Get compliance trends over time"""
        # This would typically query historical compliance data
        # For now, return current status as baseline
        current_compliance = await self._get_compliance_status()
        
        return {
            'current_score': await self._calculate_compliance_score(),
            'trend': 'stable',  # Would be calculated from historical data
            'regulations': {
                status.regulation: {
                    'status': status.status,
                    'issues_count': status.issues_count
                }
                for status in current_compliance
            }
        }
    
    async def _generate_governance_recommendations(self) -> List[str]:
        """Generate governance recommendations based on current state"""
        recommendations = []
        
        # Get current metrics
        metrics = await self._calculate_governance_metrics()
        classification_stats = await self._get_classification_statistics()
        
        # Classification coverage recommendations
        if classification_stats['classification_coverage'] < 80:
            recommendations.append(
                "Increase data classification coverage - currently at "
                f"{classification_stats['classification_coverage']:.1f}%"
            )
        
        # Confidence score recommendations
        if classification_stats['average_confidence'] < 0.7:
            recommendations.append(
                "Review and improve classification rules - average confidence is "
                f"{classification_stats['average_confidence']:.2f}"
            )
        
        # Retention policy recommendations
        retention_status = self.retention_manager.get_retention_status()
        if retention_status['failed_jobs'] > 0:
            recommendations.append(
                f"Address {retention_status['failed_jobs']} failed retention jobs"
            )
        
        # Compliance recommendations
        compliance_statuses = await self._get_compliance_status()
        non_compliant = [s for s in compliance_statuses if s.status != "compliant"]
        if non_compliant:
            recommendations.append(
                f"Address compliance issues in: {', '.join([s.regulation for s in non_compliant])}"
            )
        
        return recommendations
    
    async def get_data_lineage(self, document_id: str) -> Dict[str, Any]:
        """Get data lineage information for a specific document"""
        db = self.mongodb.dharma_platform
        
        # Find the document
        document = await db.posts.find_one({'_id': document_id})
        if not document:
            return {'error': 'Document not found'}
        
        lineage = {
            'document_id': document_id,
            'created_at': document.get('created_at'),
            'source_platform': document.get('platform'),
            'processing_history': [],
            'current_status': {
                'classified': '_classification' in document,
                'anonymized': '_anonymization_audit' in document,
                'retention_policy': document.get('_retention_policy')
            }
        }
        
        # Add classification history
        if '_classification' in document:
            classification = document['_classification']
            lineage['processing_history'].append({
                'action': 'classification',
                'timestamp': classification.get('classification_timestamp'),
                'result': {
                    'sensitivity_level': classification.get('sensitivity_level'),
                    'confidence_score': classification.get('confidence_score')
                }
            })
        
        # Add anonymization history
        if '_anonymization_audit' in document:
            anonymization = document['_anonymization_audit']
            lineage['processing_history'].append({
                'action': 'anonymization',
                'timestamp': anonymization.get('anonymized_at'),
                'result': {
                    'fields_processed': anonymization.get('fields_processed', [])
                }
            })
        
        return lineage