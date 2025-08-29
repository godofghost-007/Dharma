"""
Data Access Monitoring System for Project Dharma
Monitors and logs all data access patterns for compliance and security
"""

import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid

from .audit_logger import AuditLogger, AuditEvent, AuditEventType, AuditSeverity
from ..database.postgresql import PostgreSQLManager
from ..database.mongodb import MongoDBManager
from ..logging.structured_logger import StructuredLogger


class AccessPattern(Enum):
    """Types of data access patterns"""
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    BULK_ACCESS = "bulk_access"
    UNUSUAL_TIME = "unusual_time"
    UNUSUAL_LOCATION = "unusual_location"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"


@dataclass
class DataAccessEvent:
    """Data access event structure"""
    access_id: str
    user_id: str
    resource_type: str
    resource_id: str
    operation: str  # read, write, delete, update
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    data_classification: str
    access_method: str  # api, direct_db, file_system
    query_details: Optional[Dict[str, Any]]
    result_count: Optional[int]
    data_size_bytes: Optional[int]
    access_duration_ms: Optional[float]
    success: bool
    error_message: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "access_id": self.access_id,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "data_classification": self.data_classification,
            "access_method": self.access_method,
            "query_details": self.query_details,
            "result_count": self.result_count,
            "data_size_bytes": self.data_size_bytes,
            "access_duration_ms": self.access_duration_ms,
            "success": self.success,
            "error_message": self.error_message
        }
        return data


class AccessPatternAnalyzer:
    """Analyzes data access patterns for anomalies"""
    
    def __init__(self, postgresql_manager: PostgreSQLManager):
        self.postgresql = postgresql_manager
        self.logger = StructuredLogger(__name__)
        self.baseline_cache = {}
        self.suspicious_patterns = set()
    
    async def analyze_access_pattern(self, access_event: DataAccessEvent) -> List[AccessPattern]:
        """Analyze access event for suspicious patterns"""
        patterns = []
        
        # Check for bulk access
        if await self._is_bulk_access(access_event):
            patterns.append(AccessPattern.BULK_ACCESS)
        
        # Check for unusual time access
        if await self._is_unusual_time_access(access_event):
            patterns.append(AccessPattern.UNUSUAL_TIME)
        
        # Check for unusual location
        if await self._is_unusual_location_access(access_event):
            patterns.append(AccessPattern.UNUSUAL_LOCATION)
        
        # Check for privilege escalation
        if await self._is_privilege_escalation(access_event):
            patterns.append(AccessPattern.PRIVILEGE_ESCALATION)
        
        # Check for potential data exfiltration
        if await self._is_potential_exfiltration(access_event):
            patterns.append(AccessPattern.DATA_EXFILTRATION)
        
        return patterns if patterns else [AccessPattern.NORMAL]
    
    async def _is_bulk_access(self, access_event: DataAccessEvent) -> bool:
        """Check if access is bulk access"""
        if not access_event.result_count:
            return False
        
        # Get user's typical access patterns
        baseline = await self._get_user_baseline(access_event.user_id, access_event.resource_type)
        avg_result_count = baseline.get("avg_result_count", 100)
        
        # Flag if accessing 10x more than usual or more than 1000 records
        return (access_event.result_count > avg_result_count * 10 or 
                access_event.result_count > 1000)
    
    async def _is_unusual_time_access(self, access_event: DataAccessEvent) -> bool:
        """Check if access is at unusual time"""
        hour = access_event.timestamp.hour
        
        # Get user's typical access hours
        baseline = await self._get_user_baseline(access_event.user_id, "time_patterns")
        typical_hours = baseline.get("typical_hours", set(range(9, 18)))  # Default business hours
        
        # Flag if accessing outside typical hours
        return hour not in typical_hours
    
    async def _is_unusual_location_access(self, access_event: DataAccessEvent) -> bool:
        """Check if access is from unusual location"""
        if not access_event.ip_address:
            return False
        
        # Get user's typical IP ranges/locations
        baseline = await self._get_user_baseline(access_event.user_id, "ip_patterns")
        typical_ips = baseline.get("typical_ip_prefixes", set())
        
        # Simple IP prefix check (in production, use geolocation)
        ip_prefix = ".".join(access_event.ip_address.split(".")[:3])
        return ip_prefix not in typical_ips
    
    async def _is_privilege_escalation(self, access_event: DataAccessEvent) -> bool:
        """Check for privilege escalation attempts"""
        # Check if user is accessing data above their classification level
        user_clearance = await self._get_user_clearance(access_event.user_id)
        data_classification_level = self._get_classification_level(access_event.data_classification)
        user_clearance_level = self._get_classification_level(user_clearance)
        
        return data_classification_level > user_clearance_level
    
    async def _is_potential_exfiltration(self, access_event: DataAccessEvent) -> bool:
        """Check for potential data exfiltration"""
        # Check recent access volume for this user
        recent_access = await self._get_recent_access_volume(
            access_event.user_id, 
            timedelta(hours=1)
        )
        
        # Flag if accessing large amounts of data in short time
        return (recent_access.get("total_records", 0) > 5000 or
                recent_access.get("total_size_mb", 0) > 100)
    
    async def _get_user_baseline(self, user_id: str, pattern_type: str) -> Dict[str, Any]:
        """Get user's baseline access patterns"""
        cache_key = f"{user_id}_{pattern_type}"
        
        if cache_key in self.baseline_cache:
            return self.baseline_cache[cache_key]
        
        # Calculate baseline from historical data (last 30 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
        
        if pattern_type == "time_patterns":
            query = """
            SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count
            FROM data_access_log 
            WHERE user_id = $1 AND timestamp BETWEEN $2 AND $3
            GROUP BY EXTRACT(HOUR FROM timestamp)
            ORDER BY count DESC
            """
            
            results = await self.postgresql.fetch_all(query, user_id, start_date, end_date)
            typical_hours = {int(row['hour']) for row in results if row['count'] > 5}
            baseline = {"typical_hours": typical_hours}
            
        elif pattern_type == "ip_patterns":
            query = """
            SELECT ip_address, COUNT(*) as count
            FROM data_access_log 
            WHERE user_id = $1 AND timestamp BETWEEN $2 AND $3 AND ip_address IS NOT NULL
            GROUP BY ip_address
            ORDER BY count DESC
            LIMIT 10
            """
            
            results = await self.postgresql.fetch_all(query, user_id, start_date, end_date)
            typical_ips = {".".join(row['ip_address'].split(".")[:3]) for row in results}
            baseline = {"typical_ip_prefixes": typical_ips}
            
        else:  # Default resource access patterns
            query = """
            SELECT 
                AVG(result_count) as avg_result_count,
                AVG(data_size_bytes) as avg_data_size,
                AVG(access_duration_ms) as avg_duration
            FROM data_access_log 
            WHERE user_id = $1 AND resource_type = $2 AND timestamp BETWEEN $3 AND $4
            """
            
            result = await self.postgresql.fetch_one(query, user_id, pattern_type, start_date, end_date)
            baseline = {
                "avg_result_count": result['avg_result_count'] or 100,
                "avg_data_size": result['avg_data_size'] or 1024,
                "avg_duration": result['avg_duration'] or 100
            }
        
        self.baseline_cache[cache_key] = baseline
        return baseline
    
    async def _get_user_clearance(self, user_id: str) -> str:
        """Get user's security clearance level"""
        query = """
        SELECT security_clearance FROM users WHERE id = $1
        """
        result = await self.postgresql.fetch_one(query, user_id)
        return result['security_clearance'] if result else "public"
    
    def _get_classification_level(self, classification: str) -> int:
        """Get numeric level for data classification"""
        levels = {
            "public": 0,
            "internal": 1,
            "confidential": 2,
            "restricted": 3
        }
        return levels.get(classification.lower(), 0)
    
    async def _get_recent_access_volume(self, user_id: str, time_window: timedelta) -> Dict[str, Any]:
        """Get recent access volume for user"""
        start_time = datetime.now(timezone.utc) - time_window
        
        query = """
        SELECT 
            COUNT(*) as total_accesses,
            SUM(result_count) as total_records,
            SUM(data_size_bytes) / 1024 / 1024 as total_size_mb
        FROM data_access_log 
        WHERE user_id = $1 AND timestamp >= $2
        """
        
        result = await self.postgresql.fetch_one(query, user_id, start_time)
        return {
            "total_accesses": result['total_accesses'] or 0,
            "total_records": result['total_records'] or 0,
            "total_size_mb": result['total_size_mb'] or 0
        }


class DataAccessMonitor:
    """Main data access monitoring system"""
    
    def __init__(self, postgresql_manager: PostgreSQLManager, 
                 mongodb_manager: MongoDBManager,
                 audit_logger: AuditLogger):
        self.postgresql = postgresql_manager
        self.mongodb = mongodb_manager
        self.audit_logger = audit_logger
        self.pattern_analyzer = AccessPatternAnalyzer(postgresql_manager)
        self.logger = StructuredLogger(__name__)
        self._setup_monitoring_tables()
    
    async def _setup_monitoring_tables(self):
        """Setup data access monitoring tables"""
        create_table = """
        CREATE TABLE IF NOT EXISTS data_access_log (
            id SERIAL PRIMARY KEY,
            access_id VARCHAR(255) UNIQUE NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            resource_type VARCHAR(100) NOT NULL,
            resource_id VARCHAR(255) NOT NULL,
            operation VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            ip_address INET,
            user_agent TEXT,
            session_id VARCHAR(255),
            data_classification VARCHAR(50) NOT NULL,
            access_method VARCHAR(50) NOT NULL,
            query_details JSONB,
            result_count INTEGER,
            data_size_bytes BIGINT,
            access_duration_ms FLOAT,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            access_patterns TEXT[],
            risk_score FLOAT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_data_access_user_time ON data_access_log(user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_data_access_resource ON data_access_log(resource_type, resource_id);
        CREATE INDEX IF NOT EXISTS idx_data_access_patterns ON data_access_log USING GIN(access_patterns);
        CREATE INDEX IF NOT EXISTS idx_data_access_classification ON data_access_log(data_classification);
        """
        
        await self.postgresql.execute_query(create_table)
    
    async def log_data_access(self, access_event: DataAccessEvent):
        """Log and analyze data access event"""
        try:
            # Analyze access patterns
            patterns = await self.pattern_analyzer.analyze_access_pattern(access_event)
            pattern_names = [p.value for p in patterns]
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(patterns, access_event)
            
            # Store in PostgreSQL
            await self._store_access_log(access_event, pattern_names, risk_score)
            
            # Store in MongoDB for flexible queries
            access_doc = access_event.to_dict()
            access_doc.update({
                "access_patterns": pattern_names,
                "risk_score": risk_score,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            })
            await self.mongodb.insert_document("data_access_events", access_doc)
            
            # Generate audit event
            await self._generate_audit_event(access_event, patterns, risk_score)
            
            # Generate alerts for suspicious patterns
            if any(p != AccessPattern.NORMAL for p in patterns):
                await self._generate_security_alert(access_event, patterns, risk_score)
            
        except Exception as e:
            self.logger.error(f"Failed to log data access: {e}", extra={"access_event": access_event.to_dict()})
            raise
    
    async def _store_access_log(self, access_event: DataAccessEvent, 
                              patterns: List[str], risk_score: float):
        """Store access log in PostgreSQL"""
        query = """
        INSERT INTO data_access_log (
            access_id, user_id, resource_type, resource_id, operation,
            timestamp, ip_address, user_agent, session_id, data_classification,
            access_method, query_details, result_count, data_size_bytes,
            access_duration_ms, success, error_message, access_patterns, risk_score
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
        """
        
        await self.postgresql.execute_query(
            query,
            access_event.access_id, access_event.user_id, access_event.resource_type,
            access_event.resource_id, access_event.operation, access_event.timestamp,
            access_event.ip_address, access_event.user_agent, access_event.session_id,
            access_event.data_classification, access_event.access_method,
            json.dumps(access_event.query_details) if access_event.query_details else None,
            access_event.result_count, access_event.data_size_bytes,
            access_event.access_duration_ms, access_event.success,
            access_event.error_message, patterns, risk_score
        )
    
    def _calculate_risk_score(self, patterns: List[AccessPattern], 
                            access_event: DataAccessEvent) -> float:
        """Calculate risk score based on access patterns"""
        base_score = 0.1  # Normal access
        
        pattern_scores = {
            AccessPattern.NORMAL: 0.0,
            AccessPattern.SUSPICIOUS: 0.3,
            AccessPattern.BULK_ACCESS: 0.4,
            AccessPattern.UNUSUAL_TIME: 0.2,
            AccessPattern.UNUSUAL_LOCATION: 0.5,
            AccessPattern.PRIVILEGE_ESCALATION: 0.8,
            AccessPattern.DATA_EXFILTRATION: 0.9
        }
        
        # Calculate maximum pattern score
        max_pattern_score = max([pattern_scores.get(p, 0.0) for p in patterns])
        
        # Adjust based on data classification
        classification_multiplier = {
            "public": 1.0,
            "internal": 1.2,
            "confidential": 1.5,
            "restricted": 2.0
        }
        
        multiplier = classification_multiplier.get(access_event.data_classification.lower(), 1.0)
        
        # Adjust based on access method
        method_multiplier = {
            "api": 1.0,
            "direct_db": 1.3,
            "file_system": 1.5
        }
        
        method_mult = method_multiplier.get(access_event.access_method.lower(), 1.0)
        
        final_score = min(1.0, (base_score + max_pattern_score) * multiplier * method_mult)
        return round(final_score, 3)
    
    async def _generate_audit_event(self, access_event: DataAccessEvent,
                                  patterns: List[AccessPattern], risk_score: float):
        """Generate audit event for data access"""
        severity = AuditSeverity.LOW
        if risk_score > 0.7:
            severity = AuditSeverity.HIGH
        elif risk_score > 0.4:
            severity = AuditSeverity.MEDIUM
        
        await self.audit_logger.log_data_access(
            user_id=access_event.user_id,
            resource_type=access_event.resource_type,
            resource_id=access_event.resource_id,
            action=access_event.operation,
            data_classification=access_event.data_classification,
            details={
                "access_patterns": [p.value for p in patterns],
                "risk_score": risk_score,
                "result_count": access_event.result_count,
                "data_size_bytes": access_event.data_size_bytes,
                "access_duration_ms": access_event.access_duration_ms,
                "access_method": access_event.access_method
            },
            session_id=access_event.session_id,
            ip_address=access_event.ip_address
        )
    
    async def _generate_security_alert(self, access_event: DataAccessEvent,
                                     patterns: List[AccessPattern], risk_score: float):
        """Generate security alert for suspicious access"""
        severity = AuditSeverity.MEDIUM
        if AccessPattern.DATA_EXFILTRATION in patterns or AccessPattern.PRIVILEGE_ESCALATION in patterns:
            severity = AuditSeverity.CRITICAL
        elif risk_score > 0.6:
            severity = AuditSeverity.HIGH
        
        await self.audit_logger.log_security_event(
            event_type="suspicious_data_access",
            severity=severity,
            details={
                "access_id": access_event.access_id,
                "suspicious_patterns": [p.value for p in patterns if p != AccessPattern.NORMAL],
                "risk_score": risk_score,
                "resource_type": access_event.resource_type,
                "resource_id": access_event.resource_id,
                "operation": access_event.operation,
                "result_count": access_event.result_count,
                "data_classification": access_event.data_classification
            },
            user_id=access_event.user_id,
            ip_address=access_event.ip_address
        )
    
    async def get_access_summary(self, user_id: str = None, 
                               start_date: datetime = None,
                               end_date: datetime = None) -> Dict[str, Any]:
        """Get data access summary"""
        conditions = []
        params = []
        param_count = 0
        
        if user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)
        
        if start_date:
            param_count += 1
            conditions.append(f"timestamp >= ${param_count}")
            params.append(start_date)
        
        if end_date:
            param_count += 1
            conditions.append(f"timestamp <= ${param_count}")
            params.append(end_date)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get access statistics
        stats_query = f"""
        SELECT 
            COUNT(*) as total_accesses,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(DISTINCT resource_type) as resource_types_accessed,
            AVG(risk_score) as avg_risk_score,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_accesses,
            SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed_accesses
        FROM data_access_log
        {where_clause}
        """
        
        stats = await self.postgresql.fetch_one(stats_query, *params)
        
        # Get pattern distribution
        pattern_query = f"""
        SELECT 
            unnest(access_patterns) as pattern,
            COUNT(*) as count
        FROM data_access_log
        {where_clause}
        GROUP BY unnest(access_patterns)
        ORDER BY count DESC
        """
        
        patterns = await self.postgresql.fetch_all(pattern_query, *params)
        
        # Get top accessed resources
        resource_query = f"""
        SELECT 
            resource_type,
            resource_id,
            COUNT(*) as access_count,
            AVG(risk_score) as avg_risk_score
        FROM data_access_log
        {where_clause}
        GROUP BY resource_type, resource_id
        ORDER BY access_count DESC
        LIMIT 10
        """
        
        resources = await self.postgresql.fetch_all(resource_query, *params)
        
        return {
            "summary_period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "statistics": dict(stats),
            "pattern_distribution": [dict(row) for row in patterns],
            "top_accessed_resources": [dict(row) for row in resources],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# Decorator for monitoring data access
def monitor_data_access(resource_type: str, operation: str, 
                       data_classification: str = "internal"):
    """Decorator to monitor data access"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract monitoring parameters
            monitor = kwargs.pop('data_access_monitor', None)
            user_id = kwargs.pop('monitor_user_id', None)
            session_id = kwargs.pop('monitor_session_id', None)
            ip_address = kwargs.pop('monitor_ip_address', None)
            
            if not monitor or not user_id:
                # If no monitor provided, just execute function
                return await func(*args, **kwargs)
            
            access_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            
            try:
                result = await func(*args, **kwargs)
                
                # Calculate access metrics
                end_time = datetime.now(timezone.utc)
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                # Create access event
                access_event = DataAccessEvent(
                    access_id=access_id,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=kwargs.get('resource_id', 'unknown'),
                    operation=operation,
                    timestamp=start_time,
                    ip_address=ip_address,
                    user_agent=kwargs.get('user_agent'),
                    session_id=session_id,
                    data_classification=data_classification,
                    access_method="api",
                    query_details={"function": func.__name__},
                    result_count=len(result) if isinstance(result, (list, tuple)) else 1,
                    data_size_bytes=len(str(result).encode('utf-8')),
                    access_duration_ms=duration_ms,
                    success=True,
                    error_message=None
                )
                
                # Log access event
                await monitor.log_data_access(access_event)
                
                return result
                
            except Exception as e:
                # Log failed access
                end_time = datetime.now(timezone.utc)
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                access_event = DataAccessEvent(
                    access_id=access_id,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=kwargs.get('resource_id', 'unknown'),
                    operation=operation,
                    timestamp=start_time,
                    ip_address=ip_address,
                    user_agent=kwargs.get('user_agent'),
                    session_id=session_id,
                    data_classification=data_classification,
                    access_method="api",
                    query_details={"function": func.__name__},
                    result_count=0,
                    data_size_bytes=0,
                    access_duration_ms=duration_ms,
                    success=False,
                    error_message=str(e)
                )
                
                await monitor.log_data_access(access_event)
                raise
        
        return wrapper
    return decorator