"""
Log aggregation and correlation utilities for Project Dharma
Provides log correlation, anomaly detection, and alerting capabilities
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum

import aioredis
from elasticsearch import AsyncElasticsearch
from kafka import KafkaConsumer, KafkaProducer


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    service: str
    level: LogLevel
    message: str
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        return data


@dataclass
class LogPattern:
    """Log pattern for anomaly detection"""
    pattern: str
    regex: re.Pattern
    severity: str
    description: str
    action: Optional[str] = None


@dataclass
class LogAnomaly:
    """Detected log anomaly"""
    pattern: LogPattern
    entries: List[LogEntry]
    count: int
    time_window: timedelta
    first_occurrence: datetime
    last_occurrence: datetime
    severity: str


class LogAggregator:
    """Aggregates and correlates logs from multiple sources"""
    
    def __init__(self, 
                 elasticsearch_url: str = "http://localhost:9200",
                 redis_url: str = "redis://localhost:6379",
                 kafka_bootstrap_servers: str = "localhost:9092"):
        self.es_client = AsyncElasticsearch([elasticsearch_url])
        self.redis_url = redis_url
        self.kafka_servers = kafka_bootstrap_servers
        
        # In-memory storage for real-time correlation
        self.correlation_cache = defaultdict(list)
        self.anomaly_patterns = []
        self.alert_callbacks = []
        
        # Rate limiting for anomaly detection
        self.anomaly_counts = defaultdict(lambda: deque(maxlen=1000))
        
        self._setup_default_patterns()
    
    def _setup_default_patterns(self):
        """Setup default anomaly detection patterns"""
        patterns = [
            LogPattern(
                pattern="authentication_failure",
                regex=re.compile(r"authentication.*failed|login.*failed|invalid.*credentials", re.IGNORECASE),
                severity="HIGH",
                description="Authentication failure detected",
                action="security_alert"
            ),
            LogPattern(
                pattern="database_error",
                regex=re.compile(r"database.*error|connection.*timeout|query.*failed", re.IGNORECASE),
                severity="MEDIUM",
                description="Database connectivity issues",
                action="infrastructure_alert"
            ),
            LogPattern(
                pattern="high_error_rate",
                regex=re.compile(r"error|exception|failed", re.IGNORECASE),
                severity="MEDIUM",
                description="High error rate detected",
                action="performance_alert"
            ),
            LogPattern(
                pattern="memory_pressure",
                regex=re.compile(r"out.*of.*memory|memory.*exhausted|oom.*killed", re.IGNORECASE),
                severity="HIGH",
                description="Memory pressure detected",
                action="resource_alert"
            ),
            LogPattern(
                pattern="service_unavailable",
                regex=re.compile(r"service.*unavailable|connection.*refused|timeout", re.IGNORECASE),
                severity="HIGH",
                description="Service availability issues",
                action="availability_alert"
            )
        ]
        
        self.anomaly_patterns = patterns
    
    async def start(self):
        """Start the log aggregator"""
        self.redis_client = await aioredis.from_url(self.redis_url)
        
        # Start background tasks
        asyncio.create_task(self._consume_logs())
        asyncio.create_task(self._detect_anomalies())
        asyncio.create_task(self._cleanup_old_data())
    
    async def stop(self):
        """Stop the log aggregator"""
        await self.es_client.close()
        await self.redis_client.close()
    
    async def _consume_logs(self):
        """Consume logs from Kafka"""
        consumer = KafkaConsumer(
            'dharma-logs',
            bootstrap_servers=self.kafka_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='log-aggregator'
        )
        
        for message in consumer:
            try:
                log_data = message.value
                log_entry = self._parse_log_entry(log_data)
                await self._process_log_entry(log_entry)
            except Exception as e:
                print(f"Error processing log message: {e}")
    
    def _parse_log_entry(self, log_data: Dict[str, Any]) -> LogEntry:
        """Parse raw log data into LogEntry"""
        return LogEntry(
            timestamp=datetime.fromisoformat(log_data.get('timestamp', datetime.utcnow().isoformat()).replace('Z', '+00:00')),
            service=log_data.get('service', 'unknown'),
            level=LogLevel(log_data.get('level', 'INFO')),
            message=log_data.get('message', ''),
            correlation_id=log_data.get('correlation_id'),
            user_id=log_data.get('user_id'),
            request_id=log_data.get('request_id'),
            metadata=log_data.get('metadata', {})
        )
    
    async def _process_log_entry(self, log_entry: LogEntry):
        """Process individual log entry"""
        # Store in correlation cache
        if log_entry.correlation_id:
            self.correlation_cache[log_entry.correlation_id].append(log_entry)
        
        # Check for anomalies
        await self._check_anomalies(log_entry)
        
        # Store in Redis for real-time access
        await self._store_in_redis(log_entry)
    
    async def _check_anomalies(self, log_entry: LogEntry):
        """Check log entry against anomaly patterns"""
        for pattern in self.anomaly_patterns:
            if pattern.regex.search(log_entry.message):
                await self._handle_anomaly(pattern, log_entry)
    
    async def _handle_anomaly(self, pattern: LogPattern, log_entry: LogEntry):
        """Handle detected anomaly"""
        now = datetime.utcnow()
        pattern_key = f"{pattern.pattern}:{log_entry.service}"
        
        # Add to anomaly count
        self.anomaly_counts[pattern_key].append(now)
        
        # Check if we should trigger an alert
        recent_count = sum(1 for ts in self.anomaly_counts[pattern_key] 
                          if now - ts < timedelta(minutes=5))
        
        if recent_count >= self._get_threshold(pattern.severity):
            anomaly = LogAnomaly(
                pattern=pattern,
                entries=[log_entry],
                count=recent_count,
                time_window=timedelta(minutes=5),
                first_occurrence=min(self.anomaly_counts[pattern_key]),
                last_occurrence=now,
                severity=pattern.severity
            )
            
            await self._trigger_alert(anomaly)
    
    def _get_threshold(self, severity: str) -> int:
        """Get alert threshold based on severity"""
        thresholds = {
            "LOW": 10,
            "MEDIUM": 5,
            "HIGH": 3,
            "CRITICAL": 1
        }
        return thresholds.get(severity, 5)
    
    async def _trigger_alert(self, anomaly: LogAnomaly):
        """Trigger alert for anomaly"""
        alert_data = {
            "type": "log_anomaly",
            "pattern": anomaly.pattern.pattern,
            "severity": anomaly.severity,
            "count": anomaly.count,
            "description": anomaly.pattern.description,
            "first_occurrence": anomaly.first_occurrence.isoformat(),
            "last_occurrence": anomaly.last_occurrence.isoformat()
        }
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert_data)
            except Exception as e:
                print(f"Error in alert callback: {e}")
    
    async def _store_in_redis(self, log_entry: LogEntry):
        """Store log entry in Redis for real-time access"""
        key = f"logs:{log_entry.service}:{log_entry.timestamp.strftime('%Y%m%d%H')}"
        await self.redis_client.lpush(key, json.dumps(log_entry.to_dict()))
        await self.redis_client.expire(key, 86400)  # Expire after 24 hours
    
    async def _detect_anomalies(self):
        """Background task for anomaly detection"""
        while True:
            try:
                await self._run_anomaly_detection()
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                print(f"Error in anomaly detection: {e}")
                await asyncio.sleep(60)
    
    async def _run_anomaly_detection(self):
        """Run anomaly detection algorithms"""
        # Query recent logs from Elasticsearch
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": "now-5m"
                    }
                }
            },
            "aggs": {
                "error_rate": {
                    "terms": {
                        "field": "service.keyword"
                    },
                    "aggs": {
                        "error_count": {
                            "filter": {
                                "terms": {
                                    "level.keyword": ["ERROR", "CRITICAL"]
                                }
                            }
                        }
                    }
                }
            }
        }
        
        try:
            response = await self.es_client.search(
                index="dharma-logs-*",
                body=query
            )
            
            # Analyze error rates
            for bucket in response['aggregations']['error_rate']['buckets']:
                service = bucket['key']
                total_logs = bucket['doc_count']
                error_logs = bucket['error_count']['doc_count']
                
                if total_logs > 0:
                    error_rate = error_logs / total_logs
                    if error_rate > 0.1:  # 10% error rate threshold
                        await self._create_error_rate_alert(service, error_rate, total_logs)
        
        except Exception as e:
            print(f"Error in anomaly detection query: {e}")
    
    async def _create_error_rate_alert(self, service: str, error_rate: float, total_logs: int):
        """Create alert for high error rate"""
        alert_data = {
            "type": "high_error_rate",
            "service": service,
            "error_rate": error_rate,
            "total_logs": total_logs,
            "severity": "HIGH" if error_rate > 0.2 else "MEDIUM",
            "description": f"High error rate detected in {service}: {error_rate:.2%}"
        }
        
        for callback in self.alert_callbacks:
            try:
                await callback(alert_data)
            except Exception as e:
                print(f"Error in alert callback: {e}")
    
    async def _cleanup_old_data(self):
        """Background task to cleanup old data"""
        while True:
            try:
                # Clean up correlation cache
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                for correlation_id, entries in list(self.correlation_cache.items()):
                    self.correlation_cache[correlation_id] = [
                        entry for entry in entries 
                        if entry.timestamp > cutoff_time
                    ]
                    if not self.correlation_cache[correlation_id]:
                        del self.correlation_cache[correlation_id]
                
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                print(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for anomaly alerts"""
        self.alert_callbacks.append(callback)
    
    def add_anomaly_pattern(self, pattern: LogPattern):
        """Add custom anomaly pattern"""
        self.anomaly_patterns.append(pattern)
    
    async def get_correlated_logs(self, correlation_id: str) -> List[LogEntry]:
        """Get all logs for a correlation ID"""
        return self.correlation_cache.get(correlation_id, [])
    
    async def search_logs(self, 
                         service: str = None,
                         level: LogLevel = None,
                         start_time: datetime = None,
                         end_time: datetime = None,
                         message_pattern: str = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Search logs in Elasticsearch"""
        
        query = {"bool": {"must": []}}
        
        if service:
            query["bool"]["must"].append({"term": {"service.keyword": service}})
        
        if level:
            query["bool"]["must"].append({"term": {"level.keyword": level.value}})
        
        if start_time or end_time:
            time_range = {}
            if start_time:
                time_range["gte"] = start_time.isoformat()
            if end_time:
                time_range["lte"] = end_time.isoformat()
            query["bool"]["must"].append({"range": {"@timestamp": time_range}})
        
        if message_pattern:
            query["bool"]["must"].append({
                "match": {"message": message_pattern}
            })
        
        try:
            response = await self.es_client.search(
                index="dharma-logs-*",
                body={
                    "query": query,
                    "sort": [{"@timestamp": {"order": "desc"}}],
                    "size": limit
                }
            )
            
            return [hit["_source"] for hit in response["hits"]["hits"]]
        
        except Exception as e:
            print(f"Error searching logs: {e}")
            return []
    
    async def get_log_statistics(self, 
                                service: str = None,
                                time_range: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get log statistics"""
        
        start_time = datetime.utcnow() - time_range
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": start_time.isoformat()}}}
                    ]
                }
            },
            "aggs": {
                "levels": {
                    "terms": {"field": "level.keyword"}
                },
                "services": {
                    "terms": {"field": "service.keyword"}
                },
                "timeline": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "interval": "5m"
                    }
                }
            }
        }
        
        if service:
            query["query"]["bool"]["must"].append({"term": {"service.keyword": service}})
        
        try:
            response = await self.es_client.search(
                index="dharma-logs-*",
                body=query,
                size=0
            )
            
            return {
                "total_logs": response["hits"]["total"]["value"],
                "levels": {bucket["key"]: bucket["doc_count"] 
                          for bucket in response["aggregations"]["levels"]["buckets"]},
                "services": {bucket["key"]: bucket["doc_count"] 
                            for bucket in response["aggregations"]["services"]["buckets"]},
                "timeline": [(bucket["key_as_string"], bucket["doc_count"]) 
                            for bucket in response["aggregations"]["timeline"]["buckets"]]
            }
        
        except Exception as e:
            print(f"Error getting log statistics: {e}")
            return {}


class LogCorrelator:
    """Correlates logs across services using correlation IDs"""
    
    def __init__(self, aggregator: LogAggregator):
        self.aggregator = aggregator
    
    async def trace_request(self, correlation_id: str) -> Dict[str, Any]:
        """Trace a request across all services"""
        logs = await self.aggregator.get_correlated_logs(correlation_id)
        
        if not logs:
            return {"correlation_id": correlation_id, "logs": [], "services": [], "timeline": []}
        
        # Sort by timestamp
        logs.sort(key=lambda x: x.timestamp)
        
        # Extract services and timeline
        services = list(set(log.service for log in logs))
        timeline = [(log.timestamp.isoformat(), log.service, log.level.value, log.message) 
                   for log in logs]
        
        # Calculate request duration
        duration = logs[-1].timestamp - logs[0].timestamp
        
        # Identify errors
        errors = [log for log in logs if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
        
        return {
            "correlation_id": correlation_id,
            "duration_ms": duration.total_seconds() * 1000,
            "services": services,
            "total_logs": len(logs),
            "errors": len(errors),
            "timeline": timeline,
            "logs": [log.to_dict() for log in logs]
        }


# Example usage and testing
if __name__ == "__main__":
    async def test_log_aggregator():
        aggregator = LogAggregator()
        
        # Add custom alert callback
        async def alert_callback(alert_data):
            print(f"ALERT: {alert_data}")
        
        aggregator.add_alert_callback(alert_callback)
        
        # Start aggregator
        await aggregator.start()
        
        # Test search
        logs = await aggregator.search_logs(
            service="data-collection-service",
            level=LogLevel.ERROR,
            limit=10
        )
        print(f"Found {len(logs)} error logs")
        
        # Test statistics
        stats = await aggregator.get_log_statistics()
        print(f"Log statistics: {stats}")
        
        # Stop aggregator
        await aggregator.stop()
    
    # Run test
    asyncio.run(test_log_aggregator())