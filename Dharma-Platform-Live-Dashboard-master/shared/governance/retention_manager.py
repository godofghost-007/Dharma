"""
Automated Data Retention and Deletion Manager

Implements automated data retention policies with configurable rules
for different data types and compliance requirements.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
import logging
from pymongo import MongoClient
import asyncpg
from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)


class RetentionAction(Enum):
    """Available retention actions"""
    DELETE = "delete"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"
    COMPRESS = "compress"


class DataCategory(Enum):
    """Data categories for retention policies"""
    SOCIAL_MEDIA_POSTS = "social_media_posts"
    USER_PROFILES = "user_profiles"
    ANALYSIS_RESULTS = "analysis_results"
    AUDIT_LOGS = "audit_logs"
    SYSTEM_LOGS = "system_logs"
    ALERTS = "alerts"
    CAMPAIGNS = "campaigns"


@dataclass
class RetentionPolicy:
    """Configuration for data retention policy"""
    name: str
    data_category: DataCategory
    retention_period: timedelta
    action: RetentionAction
    conditions: Optional[Dict[str, Any]] = None
    archive_location: Optional[str] = None
    enabled: bool = True
    priority: int = 1


@dataclass
class RetentionJob:
    """Retention job execution details"""
    policy_name: str
    scheduled_time: datetime
    status: str
    records_processed: int = 0
    records_affected: int = 0
    error_message: Optional[str] = None


class RetentionManager:
    """
    Automated data retention and deletion manager
    """
    
    def __init__(self, mongodb_client: MongoClient, 
                 postgresql_pool: asyncpg.Pool,
                 elasticsearch_client: AsyncElasticsearch):
        self.mongodb = mongodb_client
        self.postgresql = postgresql_pool
        self.elasticsearch = elasticsearch_client
        self.policies: List[RetentionPolicy] = []
        self.jobs: List[RetentionJob] = []
        self.running = False
        
    def add_policy(self, policy: RetentionPolicy):
        """Add a retention policy"""
        self.policies.append(policy)
        logger.info(f"Added retention policy: {policy.name}")
    
    def remove_policy(self, policy_name: str):
        """Remove a retention policy"""
        self.policies = [p for p in self.policies if p.name != policy_name]
        logger.info(f"Removed retention policy: {policy_name}")
    
    async def start_scheduler(self, check_interval: timedelta = timedelta(hours=1)):
        """Start the retention policy scheduler"""
        self.running = True
        logger.info("Starting retention policy scheduler")
        
        while self.running:
            try:
                await self._execute_retention_policies()
                await asyncio.sleep(check_interval.total_seconds())
            except Exception as e:
                logger.error(f"Error in retention scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def stop_scheduler(self):
        """Stop the retention policy scheduler"""
        self.running = False
        logger.info("Stopping retention policy scheduler")
    
    async def _execute_retention_policies(self):
        """Execute all enabled retention policies"""
        for policy in self.policies:
            if not policy.enabled:
                continue
                
            try:
                job = RetentionJob(
                    policy_name=policy.name,
                    scheduled_time=datetime.utcnow(),
                    status="running"
                )
                
                await self._execute_policy(policy, job)
                job.status = "completed"
                
            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                logger.error(f"Error executing retention policy {policy.name}: {e}")
            
            finally:
                self.jobs.append(job)
                # Keep only last 100 jobs
                if len(self.jobs) > 100:
                    self.jobs = self.jobs[-100:]
    
    async def _execute_policy(self, policy: RetentionPolicy, job: RetentionJob):
        """Execute a specific retention policy"""
        cutoff_date = datetime.utcnow() - policy.retention_period
        
        if policy.data_category == DataCategory.SOCIAL_MEDIA_POSTS:
            await self._process_social_media_posts(policy, cutoff_date, job)
        elif policy.data_category == DataCategory.USER_PROFILES:
            await self._process_user_profiles(policy, cutoff_date, job)
        elif policy.data_category == DataCategory.ANALYSIS_RESULTS:
            await self._process_analysis_results(policy, cutoff_date, job)
        elif policy.data_category == DataCategory.AUDIT_LOGS:
            await self._process_audit_logs(policy, cutoff_date, job)
        elif policy.data_category == DataCategory.SYSTEM_LOGS:
            await self._process_system_logs(policy, cutoff_date, job)
        elif policy.data_category == DataCategory.ALERTS:
            await self._process_alerts(policy, cutoff_date, job)
        elif policy.data_category == DataCategory.CAMPAIGNS:
            await self._process_campaigns(policy, cutoff_date, job)
    
    async def _process_social_media_posts(self, policy: RetentionPolicy, 
                                        cutoff_date: datetime, job: RetentionJob):
        """Process social media posts retention"""
        db = self.mongodb.dharma_platform
        collection = db.posts
        
        # Build query with conditions
        query = {"created_at": {"$lt": cutoff_date}}
        if policy.conditions:
            query.update(policy.conditions)
        
        # Count records to be processed
        job.records_processed = await collection.count_documents(query)
        
        if policy.action == RetentionAction.DELETE:
            result = await collection.delete_many(query)
            job.records_affected = result.deleted_count
            
        elif policy.action == RetentionAction.ARCHIVE:
            # Move to archive collection
            archive_collection = db.posts_archive
            documents = await collection.find(query).to_list(None)
            if documents:
                await archive_collection.insert_many(documents)
                result = await collection.delete_many(query)
                job.records_affected = result.deleted_count
                
        elif policy.action == RetentionAction.ANONYMIZE:
            from .data_anonymizer import DataAnonymizer, AnonymizationConfig, AnonymizationRule, AnonymizationMethod
            
            # Configure anonymization for posts
            config = AnonymizationConfig(
                rules=[
                    AnonymizationRule("user_id", AnonymizationMethod.PSEUDONYMIZATION),
                    AnonymizationRule("content", AnonymizationMethod.REDACTION, "[CONTENT_REDACTED]")
                ]
            )
            anonymizer = DataAnonymizer(config)
            
            documents = await collection.find(query).to_list(None)
            for doc in documents:
                anonymized = await anonymizer.anonymize_document(doc)
                await collection.replace_one({"_id": doc["_id"]}, anonymized)
            
            job.records_affected = len(documents)
        
        logger.info(f"Processed {job.records_affected} social media posts for policy {policy.name}")
    
    async def _process_user_profiles(self, policy: RetentionPolicy, 
                                   cutoff_date: datetime, job: RetentionJob):
        """Process user profiles retention"""
        db = self.mongodb.dharma_platform
        collection = db.users
        
        query = {"last_activity": {"$lt": cutoff_date}}
        if policy.conditions:
            query.update(policy.conditions)
        
        job.records_processed = await collection.count_documents(query)
        
        if policy.action == RetentionAction.ANONYMIZE:
            from .data_anonymizer import DataAnonymizer, AnonymizationConfig, AnonymizationRule, AnonymizationMethod
            
            config = AnonymizationConfig(
                rules=[
                    AnonymizationRule("username", AnonymizationMethod.PSEUDONYMIZATION),
                    AnonymizationRule("email", AnonymizationMethod.REDACTION, "[EMAIL_REDACTED]"),
                    AnonymizationRule("profile_data", AnonymizationMethod.SUPPRESSION)
                ]
            )
            anonymizer = DataAnonymizer(config)
            
            documents = await collection.find(query).to_list(None)
            for doc in documents:
                anonymized = await anonymizer.anonymize_document(doc)
                await collection.replace_one({"_id": doc["_id"]}, anonymized)
            
            job.records_affected = len(documents)
        
        logger.info(f"Processed {job.records_affected} user profiles for policy {policy.name}")
    
    async def _process_analysis_results(self, policy: RetentionPolicy, 
                                      cutoff_date: datetime, job: RetentionJob):
        """Process analysis results retention"""
        db = self.mongodb.dharma_platform
        collection = db.analysis_results
        
        query = {"created_at": {"$lt": cutoff_date}}
        if policy.conditions:
            query.update(policy.conditions)
        
        job.records_processed = await collection.count_documents(query)
        
        if policy.action == RetentionAction.DELETE:
            result = await collection.delete_many(query)
            job.records_affected = result.deleted_count
        elif policy.action == RetentionAction.COMPRESS:
            # Compress old analysis results by removing detailed data
            documents = await collection.find(query).to_list(None)
            for doc in documents:
                # Keep only summary data
                compressed = {
                    "_id": doc["_id"],
                    "post_id": doc.get("post_id"),
                    "sentiment": doc.get("sentiment"),
                    "confidence": doc.get("confidence"),
                    "created_at": doc.get("created_at"),
                    "compressed": True
                }
                await collection.replace_one({"_id": doc["_id"]}, compressed)
            
            job.records_affected = len(documents)
        
        logger.info(f"Processed {job.records_affected} analysis results for policy {policy.name}")
    
    async def _process_audit_logs(self, policy: RetentionPolicy, 
                                cutoff_date: datetime, job: RetentionJob):
        """Process audit logs retention"""
        async with self.postgresql.acquire() as conn:
            query = """
                SELECT COUNT(*) FROM audit_logs 
                WHERE timestamp < $1
            """
            if policy.conditions:
                # Add additional conditions if needed
                pass
            
            job.records_processed = await conn.fetchval(query, cutoff_date)
            
            if policy.action == RetentionAction.ARCHIVE:
                # Move to archive table
                await conn.execute("""
                    INSERT INTO audit_logs_archive 
                    SELECT * FROM audit_logs WHERE timestamp < $1
                """, cutoff_date)
                
                result = await conn.execute("""
                    DELETE FROM audit_logs WHERE timestamp < $1
                """, cutoff_date)
                
                job.records_affected = int(result.split()[-1])
            
            elif policy.action == RetentionAction.DELETE:
                result = await conn.execute("""
                    DELETE FROM audit_logs WHERE timestamp < $1
                """, cutoff_date)
                
                job.records_affected = int(result.split()[-1])
        
        logger.info(f"Processed {job.records_affected} audit logs for policy {policy.name}")
    
    async def _process_system_logs(self, policy: RetentionPolicy, 
                                 cutoff_date: datetime, job: RetentionJob):
        """Process system logs retention in Elasticsearch"""
        # Query Elasticsearch for old logs
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "lt": cutoff_date.isoformat()
                    }
                }
            }
        }
        
        if policy.conditions:
            # Add additional conditions
            if "bool" not in query["query"]:
                query["query"] = {"bool": {"must": [query["query"]]}}
            
            for key, value in policy.conditions.items():
                query["query"]["bool"]["must"].append({
                    "term": {key: value}
                })
        
        # Count documents
        count_result = await self.elasticsearch.count(
            index="dharma-logs-*",
            body=query
        )
        job.records_processed = count_result["count"]
        
        if policy.action == RetentionAction.DELETE:
            # Delete old logs
            delete_result = await self.elasticsearch.delete_by_query(
                index="dharma-logs-*",
                body=query
            )
            job.records_affected = delete_result["deleted"]
        
        logger.info(f"Processed {job.records_affected} system logs for policy {policy.name}")
    
    async def _process_alerts(self, policy: RetentionPolicy, 
                            cutoff_date: datetime, job: RetentionJob):
        """Process alerts retention"""
        async with self.postgresql.acquire() as conn:
            query = """
                SELECT COUNT(*) FROM alerts 
                WHERE created_at < $1 AND status = 'resolved'
            """
            
            job.records_processed = await conn.fetchval(query, cutoff_date)
            
            if policy.action == RetentionAction.ARCHIVE:
                await conn.execute("""
                    INSERT INTO alerts_archive 
                    SELECT * FROM alerts 
                    WHERE created_at < $1 AND status = 'resolved'
                """, cutoff_date)
                
                result = await conn.execute("""
                    DELETE FROM alerts 
                    WHERE created_at < $1 AND status = 'resolved'
                """, cutoff_date)
                
                job.records_affected = int(result.split()[-1])
        
        logger.info(f"Processed {job.records_affected} alerts for policy {policy.name}")
    
    async def _process_campaigns(self, policy: RetentionPolicy, 
                               cutoff_date: datetime, job: RetentionJob):
        """Process campaigns retention"""
        db = self.mongodb.dharma_platform
        collection = db.campaigns
        
        query = {
            "detection_date": {"$lt": cutoff_date},
            "status": "resolved"
        }
        if policy.conditions:
            query.update(policy.conditions)
        
        job.records_processed = await collection.count_documents(query)
        
        if policy.action == RetentionAction.ARCHIVE:
            archive_collection = db.campaigns_archive
            documents = await collection.find(query).to_list(None)
            if documents:
                await archive_collection.insert_many(documents)
                result = await collection.delete_many(query)
                job.records_affected = result.deleted_count
        
        logger.info(f"Processed {job.records_affected} campaigns for policy {policy.name}")
    
    def get_retention_status(self) -> Dict[str, Any]:
        """Get current retention status and statistics"""
        active_policies = [p for p in self.policies if p.enabled]
        recent_jobs = [j for j in self.jobs if j.scheduled_time > datetime.utcnow() - timedelta(days=7)]
        
        return {
            "total_policies": len(self.policies),
            "active_policies": len(active_policies),
            "recent_jobs": len(recent_jobs),
            "successful_jobs": len([j for j in recent_jobs if j.status == "completed"]),
            "failed_jobs": len([j for j in recent_jobs if j.status == "failed"]),
            "total_records_processed": sum(j.records_processed for j in recent_jobs),
            "total_records_affected": sum(j.records_affected for j in recent_jobs),
            "last_execution": max([j.scheduled_time for j in recent_jobs]) if recent_jobs else None
        }
    
    def create_default_policies(self) -> List[RetentionPolicy]:
        """Create default retention policies for common data types"""
        default_policies = [
            RetentionPolicy(
                name="social_media_posts_1_year",
                data_category=DataCategory.SOCIAL_MEDIA_POSTS,
                retention_period=timedelta(days=365),
                action=RetentionAction.ARCHIVE,
                conditions={"platform": {"$in": ["twitter", "youtube"]}}
            ),
            RetentionPolicy(
                name="inactive_user_profiles_2_years",
                data_category=DataCategory.USER_PROFILES,
                retention_period=timedelta(days=730),
                action=RetentionAction.ANONYMIZE,
                conditions={"status": "inactive"}
            ),
            RetentionPolicy(
                name="analysis_results_6_months",
                data_category=DataCategory.ANALYSIS_RESULTS,
                retention_period=timedelta(days=180),
                action=RetentionAction.COMPRESS
            ),
            RetentionPolicy(
                name="audit_logs_7_years",
                data_category=DataCategory.AUDIT_LOGS,
                retention_period=timedelta(days=2555),  # 7 years
                action=RetentionAction.ARCHIVE
            ),
            RetentionPolicy(
                name="system_logs_90_days",
                data_category=DataCategory.SYSTEM_LOGS,
                retention_period=timedelta(days=90),
                action=RetentionAction.DELETE
            ),
            RetentionPolicy(
                name="resolved_alerts_1_year",
                data_category=DataCategory.ALERTS,
                retention_period=timedelta(days=365),
                action=RetentionAction.ARCHIVE,
                conditions={"status": "resolved"}
            ),
            RetentionPolicy(
                name="resolved_campaigns_2_years",
                data_category=DataCategory.CAMPAIGNS,
                retention_period=timedelta(days=730),
                action=RetentionAction.ARCHIVE,
                conditions={"status": "resolved"}
            )
        ]
        
        for policy in default_policies:
            self.add_policy(policy)
        
        return default_policies