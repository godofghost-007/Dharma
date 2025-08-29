"""
Simplified comprehensive audit logging system for Project Dharma
Tracks all user actions, data access, and system events for compliance
"""

import json
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager


class AuditEventType(Enum):
    """Types of audit events"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_ACTION = "user_action"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_EVENT = "compliance_event"
    API_ACCESS = "api_access"
    ADMIN_ACTION = "admin_action"
    MODEL_ACCESS = "model_access"
    ALERT_GENERATED = "alert_generated"
    CAMPAIGN_DETECTED = "campaign_detected"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    details: Dict[str, Any]
    outcome: str  # success, failure, partial
    risk_score: Optional[float]
    compliance_tags: List[str]
    data_classification: Optional[str]
    retention_period: Optional[int]  # days
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class DataLineageTracker:
    """Tracks data lineage for compliance"""
    
    def __init__(self, mongodb_manager=None):
        self.mongodb = mongodb_manager
        self.lineage_records = []  # In-memory storage for demo
    
    async def track_data_creation(self, data_id: str, source: str, 
                                metadata: Dict[str, Any]) -> str:
        """Track creation of new data"""
        lineage_id = str(uuid.uuid4())
        
        lineage_record = {
            "lineage_id": lineage_id,
            "data_id": data_id,
            "operation": "create",
            "source": source,
            "timestamp": datetime.utcnow(),
            "metadata": metadata,
            "parent_lineage": None,
            "transformations": []
        }
        
        if self.mongodb:
            await self.mongodb.insert_document("data_lineage", lineage_record)
        else:
            self.lineage_records.append(lineage_record)
        
        return lineage_id
    
    async def track_data_transformation(self, source_data_id: str, 
                                      target_data_id: str, 
                                      transformation: str,
                                      metadata: Dict[str, Any]) -> str:
        """Track data transformation"""
        lineage_id = str(uuid.uuid4())
        
        # Get parent lineage
        parent_lineage = None
        if self.mongodb:
            parent_lineage = await self.mongodb.find_document(
                "data_lineage", 
                {"data_id": source_data_id}
            )
        else:
            for record in self.lineage_records:
                if record["data_id"] == source_data_id:
                    parent_lineage = record
                    break
        
        lineage_record = {
            "lineage_id": lineage_id,
            "data_id": target_data_id,
            "operation": "transform",
            "source": source_data_id,
            "timestamp": datetime.utcnow(),
            "metadata": metadata,
            "parent_lineage": parent_lineage.get("lineage_id") if parent_lineage else None,
            "transformation": transformation,
            "transformations": parent_lineage.get("transformations", []) + [transformation] if parent_lineage else [transformation]
        }
        
        if self.mongodb:
            await self.mongodb.insert_document("data_lineage", lineage_record)
        else:
            self.lineage_records.append(lineage_record)
        
        return lineage_id
    
    async def get_data_lineage(self, data_id: str) -> Dict[str, Any]:
        """Get complete lineage for data"""
        if self.mongodb:
            lineage = await self.mongodb.find_document(
                "data_lineage", 
                {"data_id": data_id}
            )
        else:
            lineage = None
            for record in self.lineage_records:
                if record["data_id"] == data_id:
                    lineage = record
                    break
        
        if not lineage:
            return {}
        
        return lineage


class ComplianceChecker:
    """Automated compliance checking"""
    
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger
        self.compliance_rules = self._load_compliance_rules()
    
    def _load_compliance_rules(self) -> Dict[str, Any]:
        """Load compliance rules configuration"""
        return {
            "data_retention": {
                "personal_data": 365,  # days
                "system_logs": 2555,  # 7 years
                "audit_logs": 2555,   # 7 years
                "analytics_data": 1095  # 3 years
            },
            "access_controls": {
                "admin_actions_require_approval": True,
                "sensitive_data_requires_justification": True,
                "bulk_operations_require_review": True
            },
            "data_classification": {
                "public": {"encryption": False, "access_logging": False},
                "internal": {"encryption": True, "access_logging": True},
                "confidential": {"encryption": True, "access_logging": True, "approval_required": True},
                "restricted": {"encryption": True, "access_logging": True, "approval_required": True, "mfa_required": True}
            }
        }
    
    async def check_compliance(self, event: AuditEvent) -> List[str]:
        """Check event against compliance rules"""
        violations = []
        
        # Check data retention compliance
        if event.resource_type and event.retention_period:
            required_retention = self.compliance_rules["data_retention"].get(
                event.resource_type, 365
            )
            if event.retention_period < required_retention:
                violations.append(f"Data retention period too short: {event.retention_period} < {required_retention}")
        
        # Check access control compliance
        if event.event_type == AuditEventType.ADMIN_ACTION:
            if self.compliance_rules["access_controls"]["admin_actions_require_approval"]:
                if not event.details.get("approved_by"):
                    violations.append("Admin action requires approval")
        
        # Check data classification compliance
        if event.data_classification:
            classification_rules = self.compliance_rules["data_classification"].get(
                event.data_classification, {}
            )
            
            if classification_rules.get("approval_required") and not event.details.get("approved_by"):
                violations.append(f"Access to {event.data_classification} data requires approval")
            
            if classification_rules.get("mfa_required") and not event.details.get("mfa_verified"):
                violations.append(f"Access to {event.data_classification} data requires MFA")
        
        return violations
    
    async def generate_compliance_alert(self, violations: List[str], event: AuditEvent):
        """Generate compliance violation alert"""
        if not violations:
            return
        
        compliance_event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.COMPLIANCE_EVENT,
            severity=AuditSeverity.HIGH,
            timestamp=datetime.now(timezone.utc),
            user_id=event.user_id,
            session_id=event.session_id,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            resource_type="compliance_violation",
            resource_id=event.event_id,
            action="compliance_check",
            details={
                "violations": violations,
                "original_event": event.to_dict()
            },
            outcome="violation_detected",
            risk_score=0.8,
            compliance_tags=["violation", "requires_review"],
            data_classification="restricted",
            retention_period=2555  # 7 years
        )
        
        await self.audit_logger.log_event(compliance_event)


class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(self, postgresql_manager=None, mongodb_manager=None):
        self.postgresql = postgresql_manager
        self.mongodb = mongodb_manager
        self.lineage_tracker = DataLineageTracker(mongodb_manager)
        self.compliance_checker = ComplianceChecker(self)
        self.events = []  # In-memory storage for demo
        
        # Setup tables if database managers are available
        if self.postgresql:
            asyncio.create_task(self._setup_audit_tables())
    
    async def _setup_audit_tables(self):
        """Setup audit tables in PostgreSQL"""
        create_audit_table = """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR(255) UNIQUE NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            user_id VARCHAR(255),
            session_id VARCHAR(255),
            ip_address INET,
            user_agent TEXT,
            resource_type VARCHAR(100),
            resource_id VARCHAR(255),
            action VARCHAR(255) NOT NULL,
            details JSONB,
            outcome VARCHAR(50) NOT NULL,
            risk_score FLOAT,
            compliance_tags TEXT[],
            data_classification VARCHAR(50),
            retention_period INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_compliance ON audit_logs USING GIN(compliance_tags);
        """
        
        try:
            await self.postgresql.execute_query(create_audit_table)
        except Exception as e:
            print(f"Failed to setup audit tables: {e}")
    
    async def log_event(self, event: AuditEvent):
        """Log audit event"""
        try:
            # Check compliance
            violations = await self.compliance_checker.check_compliance(event)
            if violations:
                await self.compliance_checker.generate_compliance_alert(violations, event)
            
            # Store in PostgreSQL for structured queries
            if self.postgresql:
                await self._store_in_postgresql(event)
            
            # Store in MongoDB for flexible document storage
            if self.mongodb:
                await self._store_in_mongodb(event)
            
            # Store in memory for demo
            self.events.append(event)
            
        except Exception as e:
            print(f"Failed to log audit event: {e}")
    
    async def _store_in_postgresql(self, event: AuditEvent):
        """Store audit event in PostgreSQL"""
        query = """
        INSERT INTO audit_logs (
            event_id, event_type, severity, timestamp, user_id, session_id,
            ip_address, user_agent, resource_type, resource_id, action,
            details, outcome, risk_score, compliance_tags, data_classification,
            retention_period
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        """
        
        try:
            await self.postgresql.execute_query(
                query,
                event.event_id, event.event_type.value, event.severity.value,
                event.timestamp, event.user_id, event.session_id,
                event.ip_address, event.user_agent, event.resource_type,
                event.resource_id, event.action, json.dumps(event.details),
                event.outcome, event.risk_score, event.compliance_tags,
                event.data_classification, event.retention_period
            )
        except Exception as e:
            print(f"Failed to store audit event in PostgreSQL: {e}")
    
    async def _store_in_mongodb(self, event: AuditEvent):
        """Store audit event in MongoDB"""
        try:
            await self.mongodb.insert_document("audit_events", event.to_dict())
        except Exception as e:
            print(f"Failed to store audit event in MongoDB: {e}")
    
    async def log_user_action(self, user_id: str, action: str, 
                            resource_type: str = None, resource_id: str = None,
                            details: Dict[str, Any] = None, 
                            session_id: str = None, ip_address: str = None,
                            user_agent: str = None, outcome: str = "success"):
        """Log user action"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.USER_ACTION,
            severity=AuditSeverity.LOW,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            outcome=outcome,
            risk_score=0.1,
            compliance_tags=["user_action"],
            data_classification="internal",
            retention_period=365
        )
        
        await self.log_event(event)
    
    async def log_data_access(self, user_id: str, resource_type: str, 
                            resource_id: str, action: str,
                            data_classification: str = "internal",
                            details: Dict[str, Any] = None,
                            session_id: str = None, ip_address: str = None):
        """Log data access event"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.MEDIUM,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=None,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            outcome="success",
            risk_score=0.3,
            compliance_tags=["data_access", "requires_monitoring"],
            data_classification=data_classification,
            retention_period=2555  # 7 years for compliance
        )
        
        await self.log_event(event)
    
    async def log_security_event(self, event_type: str, severity: AuditSeverity,
                               details: Dict[str, Any], user_id: str = None,
                               ip_address: str = None):
        """Log security event"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.SECURITY_EVENT,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            session_id=None,
            ip_address=ip_address,
            user_agent=None,
            resource_type="security",
            resource_id=None,
            action=event_type,
            details=details,
            outcome="detected",
            risk_score=0.7,
            compliance_tags=["security", "requires_investigation"],
            data_classification="restricted",
            retention_period=2555
        )
        
        await self.log_event(event)
    
    async def get_audit_trail(self, user_id: str = None, 
                            resource_type: str = None,
                            start_date: datetime = None,
                            end_date: datetime = None,
                            limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail with filters"""
        if self.postgresql:
            conditions = []
            params = []
            param_count = 0
            
            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)
            
            if resource_type:
                param_count += 1
                conditions.append(f"resource_type = ${param_count}")
                params.append(resource_type)
            
            if start_date:
                param_count += 1
                conditions.append(f"timestamp >= ${param_count}")
                params.append(start_date)
            
            if end_date:
                param_count += 1
                conditions.append(f"timestamp <= ${param_count}")
                params.append(end_date)
            
            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            
            query = f"""
            SELECT * FROM audit_logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit}
            """
            
            try:
                return await self.postgresql.fetch_all(query, *params)
            except Exception as e:
                print(f"Failed to get audit trail: {e}")
        
        # Fallback to in-memory events
        filtered_events = []
        for event in self.events:
            if user_id and event.user_id != user_id:
                continue
            if resource_type and event.resource_type != resource_type:
                continue
            if start_date and event.timestamp < start_date:
                continue
            if end_date and event.timestamp > end_date:
                continue
            
            filtered_events.append(event.to_dict())
            
            if len(filtered_events) >= limit:
                break
        
        return filtered_events
    
    async def generate_compliance_report(self, start_date: datetime, 
                                       end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report"""
        try:
            if self.postgresql:
                # Get audit statistics from database
                stats_query = """
                SELECT 
                    event_type,
                    severity,
                    COUNT(*) as count,
                    COUNT(CASE WHEN 'violation' = ANY(compliance_tags) THEN 1 END) as violations
                FROM audit_logs 
                WHERE timestamp BETWEEN $1 AND $2
                GROUP BY event_type, severity
                ORDER BY count DESC
                """
                
                stats = await self.postgresql.fetch_all(stats_query, start_date, end_date)
                
                # Get top users by activity
                user_activity_query = """
                SELECT 
                    user_id,
                    COUNT(*) as action_count,
                    COUNT(DISTINCT resource_type) as resource_types_accessed
                FROM audit_logs 
                WHERE timestamp BETWEEN $1 AND $2 AND user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY action_count DESC
                LIMIT 10
                """
                
                user_activity = await self.postgresql.fetch_all(user_activity_query, start_date, end_date)
                
                # Get compliance violations
                violations_query = """
                SELECT 
                    event_id,
                    user_id,
                    action,
                    resource_type,
                    timestamp,
                    details
                FROM audit_logs 
                WHERE timestamp BETWEEN $1 AND $2 
                AND 'violation' = ANY(compliance_tags)
                ORDER BY timestamp DESC
                """
                
                violations = await self.postgresql.fetch_all(violations_query, start_date, end_date)
                
                return {
                    "report_period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "statistics": [dict(row) for row in stats],
                    "top_users": [dict(row) for row in user_activity],
                    "compliance_violations": [dict(row) for row in violations],
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                # Generate report from in-memory events
                filtered_events = [e for e in self.events if start_date <= e.timestamp <= end_date]
                
                # Basic statistics
                event_types = {}
                severities = {}
                users = {}
                violations = []
                
                for event in filtered_events:
                    event_types[event.event_type.value] = event_types.get(event.event_type.value, 0) + 1
                    severities[event.severity.value] = severities.get(event.severity.value, 0) + 1
                    users[event.user_id] = users.get(event.user_id, 0) + 1
                    
                    if "violation" in event.compliance_tags:
                        violations.append(event.to_dict())
                
                return {
                    "report_period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "statistics": [
                        {"event_type": k, "count": v} for k, v in event_types.items()
                    ],
                    "top_users": [
                        {"user_id": k, "action_count": v} for k, v in sorted(users.items(), key=lambda x: x[1], reverse=True)[:10]
                    ],
                    "compliance_violations": violations,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            print(f"Failed to generate compliance report: {e}")
            return {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "statistics": [],
                "top_users": [],
                "compliance_violations": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }


# Audit logging decorator
def audit_action(action: str, resource_type: str = None):
    """Decorator to automatically audit function calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract audit logger from args/kwargs or get from context
            audit_logger = kwargs.pop('audit_logger', None)
            user_id = kwargs.pop('audit_user_id', None)
            session_id = kwargs.pop('audit_session_id', None)
            
            if not audit_logger or not user_id:
                # If no audit logger or user_id provided, just execute function
                return await func(*args, **kwargs)
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful action
                await audit_logger.log_user_action(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    details={
                        "function": func.__name__,
                        "args": str(args)[:500],  # Truncate for storage
                        "kwargs": str({k: v for k, v in kwargs.items() if not k.startswith('audit_')})[:500]
                    },
                    session_id=session_id,
                    outcome="success"
                )
                
                return result
                
            except Exception as e:
                # Log failed action
                await audit_logger.log_user_action(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    details={
                        "function": func.__name__,
                        "error": str(e),
                        "args": str(args)[:500],
                        "kwargs": str({k: v for k, v in kwargs.items() if not k.startswith('audit_')})[:500]
                    },
                    session_id=session_id,
                    outcome="failure"
                )
                raise
        
        return wrapper
    return decorator


# Context manager for audit sessions
@asynccontextmanager
async def audit_session(audit_logger: AuditLogger, user_id: str, 
                       session_id: str, ip_address: str = None):
    """Context manager for audit sessions"""
    # Log session start
    await audit_logger.log_user_action(
        user_id=user_id,
        action="session_start",
        session_id=session_id,
        ip_address=ip_address,
        details={"session_type": "audit_session"}
    )
    
    try:
        yield audit_logger
    finally:
        # Log session end
        await audit_logger.log_user_action(
            user_id=user_id,
            action="session_end",
            session_id=session_id,
            ip_address=ip_address,
            details={"session_type": "audit_session"}
        )