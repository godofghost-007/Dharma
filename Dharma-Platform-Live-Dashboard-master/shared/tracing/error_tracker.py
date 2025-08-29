"""
Advanced error tracking and reporting system for Project Dharma
Provides comprehensive error collection, analysis, and alerting
"""

import json
import time
import traceback
import sys
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import threading
from collections import defaultdict, Counter
import hashlib

try:
    import aioredis
except ImportError:
    aioredis = None

try:
    from elasticsearch import AsyncElasticsearch
except ImportError:
    AsyncElasticsearch = None

try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS_LOGIC = "business_logic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DATA = "data"
    INTEGRATION = "integration"


@dataclass
class ErrorContext:
    """Error context information"""
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ErrorEvent:
    """Error event data structure"""
    id: str
    timestamp: datetime
    service: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    stack_trace: str
    context: ErrorContext
    fingerprint: str
    count: int = 1
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    resolved: bool = False
    tags: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['severity'] = self.severity.value
        data['category'] = self.category.value
        if self.first_seen:
            data['first_seen'] = self.first_seen.isoformat()
        if self.last_seen:
            data['last_seen'] = self.last_seen.isoformat()
        return data


class ErrorAggregator:
    """Aggregates similar errors to reduce noise"""
    
    def __init__(self, time_window: timedelta = timedelta(minutes=5)):
        self.time_window = time_window
        self.error_groups = defaultdict(list)
        self.fingerprint_cache = {}
    
    def generate_fingerprint(self, error_type: str, error_message: str, 
                           stack_trace: str, service: str) -> str:
        """Generate fingerprint for error grouping"""
        # Extract relevant parts of stack trace (ignore line numbers)
        stack_lines = stack_trace.split('\n')
        relevant_lines = []
        
        for line in stack_lines:
            if 'File "' in line and 'line' in line:
                # Extract file path and function name, ignore line numbers
                parts = line.split(', ')
                if len(parts) >= 2:
                    file_part = parts[0].replace('File "', '').replace('"', '')
                    func_part = parts[1] if 'in ' in parts[1] else ''
                    relevant_lines.append(f"{file_part}:{func_part}")
        
        # Create fingerprint from error type, message pattern, and stack trace
        message_pattern = self._extract_message_pattern(error_message)
        fingerprint_data = f"{service}:{error_type}:{message_pattern}:{'|'.join(relevant_lines[:5])}"
        
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def _extract_message_pattern(self, message: str) -> str:
        """Extract pattern from error message by removing variable parts"""
        import re
        
        # Replace common variable patterns
        patterns = [
            (r'\d+', 'N'),  # Numbers
            (r"'[^']*'", "'STRING'"),  # Single quoted strings
            (r'"[^"]*"', '"STRING"'),  # Double quoted strings
            (r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', 'UUID'),  # UUIDs
            (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'IP'),  # IP addresses
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL'),  # Email addresses
        ]
        
        pattern = message
        for regex, replacement in patterns:
            pattern = re.sub(regex, replacement, pattern)
        
        return pattern
    
    def should_aggregate(self, error_event: ErrorEvent) -> bool:
        """Check if error should be aggregated with existing group"""
        fingerprint = error_event.fingerprint
        
        if fingerprint not in self.error_groups:
            return False
        
        # Check if there's a recent error with same fingerprint
        recent_errors = [
            e for e in self.error_groups[fingerprint]
            if error_event.timestamp - e.timestamp < self.time_window
        ]
        
        return len(recent_errors) > 0
    
    def add_error(self, error_event: ErrorEvent) -> bool:
        """Add error to aggregation groups. Returns True if aggregated, False if new."""
        fingerprint = error_event.fingerprint
        
        if self.should_aggregate(error_event):
            # Update existing error group
            existing_errors = self.error_groups[fingerprint]
            if existing_errors:
                latest_error = existing_errors[-1]
                latest_error.count += 1
                latest_error.last_seen = error_event.timestamp
                return True
        
        # Add as new error
        error_event.first_seen = error_event.timestamp
        error_event.last_seen = error_event.timestamp
        self.error_groups[fingerprint].append(error_event)
        return False
    
    def cleanup_old_errors(self):
        """Clean up old error groups"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        for fingerprint in list(self.error_groups.keys()):
            self.error_groups[fingerprint] = [
                e for e in self.error_groups[fingerprint]
                if e.timestamp > cutoff_time
            ]
            
            if not self.error_groups[fingerprint]:
                del self.error_groups[fingerprint]


class AdvancedErrorTracker:
    """Advanced error tracking system"""
    
    def __init__(self, 
                 service_name: str,
                 elasticsearch_url: str = "http://localhost:9200",
                 redis_url: str = "redis://localhost:6379",
                 kafka_bootstrap_servers: str = "localhost:9092"):
        self.service_name = service_name
        self.es_client = AsyncElasticsearch([elasticsearch_url])
        self.redis_url = redis_url
        self.kafka_servers = kafka_bootstrap_servers
        
        self.aggregator = ErrorAggregator()
        self.error_handlers = []
        self.alert_rules = []
        
        # Error statistics
        self.error_stats = defaultdict(Counter)
        self.running = False
        
        self._setup_default_alert_rules()
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules"""
        self.alert_rules = [
            {
                "name": "high_error_rate",
                "condition": lambda stats: stats.get("error_rate_5m", 0) > 0.1,
                "severity": ErrorSeverity.HIGH,
                "message": "High error rate detected"
            },
            {
                "name": "critical_error",
                "condition": lambda error: error.severity == ErrorSeverity.CRITICAL,
                "severity": ErrorSeverity.CRITICAL,
                "message": "Critical error occurred"
            },
            {
                "name": "new_error_type",
                "condition": lambda error: error.fingerprint not in self.aggregator.fingerprint_cache,
                "severity": ErrorSeverity.MEDIUM,
                "message": "New error type detected"
            }
        ]
    
    async def start(self):
        """Start error tracking system"""
        self.redis_client = await aioredis.from_url(self.redis_url)
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._cleanup_task())
        asyncio.create_task(self._stats_calculation_task())
    
    async def stop(self):
        """Stop error tracking system"""
        self.running = False
        await self.es_client.close()
        await self.redis_client.close()
        self.kafka_producer.close()
    
    def track_error(self, 
                   error: Exception,
                   severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                   category: ErrorCategory = ErrorCategory.APPLICATION,
                   context: ErrorContext = None,
                   tags: Dict[str, str] = None) -> ErrorEvent:
        """Track an error event"""
        
        # Extract error information
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        # Generate fingerprint
        fingerprint = self.aggregator.generate_fingerprint(
            error_type, error_message, stack_trace, self.service_name
        )
        
        # Create error event
        error_event = ErrorEvent(
            id=f"{self.service_name}_{int(time.time() * 1000)}_{fingerprint[:8]}",
            timestamp=datetime.utcnow(),
            service=self.service_name,
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            category=category,
            stack_trace=stack_trace,
            context=context or ErrorContext(),
            fingerprint=fingerprint,
            tags=tags or {}
        )
        
        # Check if should be aggregated
        is_aggregated = self.aggregator.add_error(error_event)
        
        # Store error
        asyncio.create_task(self._store_error(error_event, is_aggregated))
        
        # Update statistics
        self._update_stats(error_event)
        
        # Check alert rules
        self._check_alert_rules(error_event)
        
        return error_event
    
    async def _store_error(self, error_event: ErrorEvent, is_aggregated: bool):
        """Store error in storage systems"""
        try:
            # Store in Elasticsearch
            await self.es_client.index(
                index=f"dharma-errors-{datetime.utcnow().strftime('%Y.%m')}",
                body=error_event.to_dict()
            )
            
            # Store in Redis for real-time access
            await self.redis_client.setex(
                f"error:{error_event.id}",
                3600,  # 1 hour TTL
                json.dumps(error_event.to_dict())
            )
            
            # Send to Kafka for real-time processing
            if not is_aggregated:  # Only send new errors to avoid spam
                self.kafka_producer.send('dharma-errors', error_event.to_dict())
            
        except Exception as e:
            print(f"Failed to store error: {e}")
    
    def _update_stats(self, error_event: ErrorEvent):
        """Update error statistics"""
        now = datetime.utcnow()
        minute_key = now.strftime('%Y%m%d%H%M')
        
        self.error_stats[minute_key]['total'] += 1
        self.error_stats[minute_key][error_event.severity.value] += 1
        self.error_stats[minute_key][error_event.category.value] += 1
        self.error_stats[minute_key][error_event.error_type] += 1
    
    def _check_alert_rules(self, error_event: ErrorEvent):
        """Check error against alert rules"""
        for rule in self.alert_rules:
            try:
                if rule["condition"](error_event):
                    self._trigger_alert(rule, error_event)
            except Exception as e:
                print(f"Error checking alert rule {rule['name']}: {e}")
    
    def _trigger_alert(self, rule: Dict[str, Any], error_event: ErrorEvent):
        """Trigger alert for error"""
        alert_data = {
            "rule_name": rule["name"],
            "severity": rule["severity"].value,
            "message": rule["message"],
            "error_event": error_event.to_dict(),
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send alert to handlers
        for handler in self.error_handlers:
            try:
                handler(alert_data)
            except Exception as e:
                print(f"Error in alert handler: {e}")
    
    async def _cleanup_task(self):
        """Background task for cleanup"""
        while self.running:
            try:
                self.aggregator.cleanup_old_errors()
                
                # Clean up old stats
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                cutoff_key = cutoff_time.strftime('%Y%m%d%H%M')
                
                for key in list(self.error_stats.keys()):
                    if key < cutoff_key:
                        del self.error_stats[key]
                
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                print(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    async def _stats_calculation_task(self):
        """Background task for calculating error statistics"""
        while self.running:
            try:
                # Calculate error rates
                now = datetime.utcnow()
                
                # 5-minute error rate
                error_count_5m = sum(
                    self.error_stats.get((now - timedelta(minutes=i)).strftime('%Y%m%d%H%M'), Counter())['total']
                    for i in range(5)
                )
                
                # This is simplified - in reality you'd need total request count
                # For now, assume error rate based on error count threshold
                error_rate_5m = min(error_count_5m / 100.0, 1.0)  # Simplified calculation
                
                # Store calculated stats
                stats = {
                    "error_count_5m": error_count_5m,
                    "error_rate_5m": error_rate_5m,
                    "timestamp": now.isoformat()
                }
                
                # Check alert rules based on stats
                for rule in self.alert_rules:
                    if rule["name"] == "high_error_rate" and rule["condition"](stats):
                        alert_data = {
                            "rule_name": rule["name"],
                            "severity": rule["severity"].value,
                            "message": f"{rule['message']}: {error_rate_5m:.2%}",
                            "stats": stats,
                            "service": self.service_name,
                            "timestamp": now.isoformat()
                        }
                        
                        for handler in self.error_handlers:
                            try:
                                handler(alert_data)
                            except Exception as e:
                                print(f"Error in stats alert handler: {e}")
                
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                print(f"Error in stats calculation task: {e}")
                await asyncio.sleep(60)
    
    def add_error_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add error alert handler"""
        self.error_handlers.append(handler)
    
    def add_alert_rule(self, rule: Dict[str, Any]):
        """Add custom alert rule"""
        self.alert_rules.append(rule)
    
    async def get_error_summary(self, time_range: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get error summary for time range"""
        start_time = datetime.utcnow() - time_range
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"service.keyword": self.service_name}},
                        {"range": {"timestamp": {"gte": start_time.isoformat()}}}
                    ]
                }
            },
            "aggs": {
                "by_severity": {
                    "terms": {"field": "severity.keyword"}
                },
                "by_category": {
                    "terms": {"field": "category.keyword"}
                },
                "by_error_type": {
                    "terms": {"field": "error_type.keyword"}
                },
                "timeline": {
                    "date_histogram": {
                        "field": "timestamp",
                        "interval": "5m"
                    }
                }
            }
        }
        
        try:
            response = await self.es_client.search(
                index="dharma-errors-*",
                body=query,
                size=0
            )
            
            return {
                "total_errors": response["hits"]["total"]["value"],
                "by_severity": {bucket["key"]: bucket["doc_count"] 
                              for bucket in response["aggregations"]["by_severity"]["buckets"]},
                "by_category": {bucket["key"]: bucket["doc_count"] 
                               for bucket in response["aggregations"]["by_category"]["buckets"]},
                "by_error_type": {bucket["key"]: bucket["doc_count"] 
                                 for bucket in response["aggregations"]["by_error_type"]["buckets"]},
                "timeline": [(bucket["key_as_string"], bucket["doc_count"]) 
                            for bucket in response["aggregations"]["timeline"]["buckets"]]
            }
        
        except Exception as e:
            print(f"Error getting error summary: {e}")
            return {}
    
    async def get_error_details(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed error information"""
        try:
            # Try Redis first
            error_data = await self.redis_client.get(f"error:{error_id}")
            if error_data:
                return json.loads(error_data)
            
            # Fall back to Elasticsearch
            response = await self.es_client.search(
                index="dharma-errors-*",
                body={
                    "query": {"term": {"id.keyword": error_id}},
                    "size": 1
                }
            )
            
            if response["hits"]["hits"]:
                return response["hits"]["hits"][0]["_source"]
            
            return None
        
        except Exception as e:
            print(f"Error getting error details: {e}")
            return None


def error_tracking_decorator(tracker: AdvancedErrorTracker,
                           severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                           category: ErrorCategory = ErrorCategory.APPLICATION,
                           tags: Dict[str, str] = None):
    """Decorator for automatic error tracking"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    request_id=getattr(args[0], 'request_id', None) if args else None
                )
                tracker.track_error(e, severity, category, context, tags)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    request_id=getattr(args[0], 'request_id', None) if args else None
                )
                tracker.track_error(e, severity, category, context, tags)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Example usage and testing
if __name__ == "__main__":
    async def test_error_tracker():
        tracker = AdvancedErrorTracker("test-service")
        
        # Add error handler
        def error_handler(alert_data):
            print(f"ERROR ALERT: {alert_data}")
        
        tracker.add_error_handler(error_handler)
        
        # Start tracker
        await tracker.start()
        
        # Test error tracking
        try:
            raise ValueError("Test error message")
        except Exception as e:
            context = ErrorContext(
                user_id="test_user",
                request_id="test_request_123",
                url="/api/test"
            )
            tracker.track_error(e, ErrorSeverity.HIGH, ErrorCategory.APPLICATION, context)
        
        # Test duplicate error (should be aggregated)
        try:
            raise ValueError("Test error message")
        except Exception as e:
            tracker.track_error(e, ErrorSeverity.HIGH, ErrorCategory.APPLICATION)
        
        # Wait a bit for processing
        await asyncio.sleep(2)
        
        # Get error summary
        summary = await tracker.get_error_summary()
        print(f"Error summary: {summary}")
        
        # Stop tracker
        await tracker.stop()
    
    # Run test
    asyncio.run(test_error_tracker())