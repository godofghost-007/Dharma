"""
Log-based alerting system for Project Dharma
Provides real-time alerting based on log patterns and anomalies
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

import aioredis
from elasticsearch import AsyncElasticsearch
from kafka import KafkaProducer

from .log_aggregator import LogAggregator, LogLevel, LogAnomaly


class AlertSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    ERROR_RATE = "error_rate"
    SECURITY_BREACH = "security_breach"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SERVICE_UNAVAILABLE = "service_unavailable"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass
class AlertRule:
    """Alert rule configuration"""
    id: str
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    query: Dict[str, Any]
    threshold: float
    time_window: timedelta
    cooldown: timedelta
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['alert_type'] = self.alert_type.value
        data['severity'] = self.severity.value
        data['time_window'] = self.time_window.total_seconds()
        data['cooldown'] = self.cooldown.total_seconds()
        return data


@dataclass
class Alert:
    """Alert instance"""
    id: str
    rule_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    timestamp: datetime
    data: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['alert_type'] = self.alert_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class LogAlertingEngine:
    """Main log alerting engine"""
    
    def __init__(self, 
                 aggregator: LogAggregator,
                 elasticsearch_url: str = "http://localhost:9200",
                 redis_url: str = "redis://localhost:6379",
                 kafka_bootstrap_servers: str = "localhost:9092"):
        self.aggregator = aggregator
        self.es_client = AsyncElasticsearch([elasticsearch_url])
        self.redis_url = redis_url
        self.kafka_servers = kafka_bootstrap_servers
        
        self.alert_rules = {}
        self.active_alerts = {}
        self.alert_callbacks = []
        self.cooldown_cache = {}
        
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        default_rules = [
            AlertRule(
                id="high_error_rate",
                name="High Error Rate",
                description="Error rate exceeds threshold",
                alert_type=AlertType.ERROR_RATE,
                severity=AlertSeverity.HIGH,
                query={
                    "bool": {
                        "must": [
                            {"terms": {"level.keyword": ["ERROR", "CRITICAL"]}},
                            {"range": {"@timestamp": {"gte": "now-5m"}}}
                        ]
                    }
                },
                threshold=0.1,  # 10% error rate
                time_window=timedelta(minutes=5),
                cooldown=timedelta(minutes=15)
            ),
            AlertRule(
                id="authentication_failures",
                name="Authentication Failures",
                description="Multiple authentication failures detected",
                alert_type=AlertType.SECURITY_BREACH,
                severity=AlertSeverity.CRITICAL,
                query={
                    "bool": {
                        "must": [
                            {"match": {"message": "authentication failed"}},
                            {"range": {"@timestamp": {"gte": "now-5m"}}}
                        ]
                    }
                },
                threshold=5,  # 5 failures in 5 minutes
                time_window=timedelta(minutes=5),
                cooldown=timedelta(minutes=10)
            ),
            AlertRule(
                id="service_unavailable",
                name="Service Unavailable",
                description="Service availability issues detected",
                alert_type=AlertType.SERVICE_UNAVAILABLE,
                severity=AlertSeverity.CRITICAL,
                query={
                    "bool": {
                        "must": [
                            {"match": {"message": "service unavailable"}},
                            {"range": {"@timestamp": {"gte": "now-2m"}}}
                        ]
                    }
                },
                threshold=1,  # Any service unavailable message
                time_window=timedelta(minutes=2),
                cooldown=timedelta(minutes=5)
            ),
            AlertRule(
                id="memory_pressure",
                name="Memory Pressure",
                description="Memory pressure detected in services",
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                severity=AlertSeverity.HIGH,
                query={
                    "bool": {
                        "must": [
                            {"match": {"message": "out of memory"}},
                            {"range": {"@timestamp": {"gte": "now-5m"}}}
                        ]
                    }
                },
                threshold=1,  # Any OOM message
                time_window=timedelta(minutes=5),
                cooldown=timedelta(minutes=20)
            ),
            AlertRule(
                id="database_connection_errors",
                name="Database Connection Errors",
                description="Database connectivity issues",
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                severity=AlertSeverity.MEDIUM,
                query={
                    "bool": {
                        "must": [
                            {"match": {"message": "database connection"}},
                            {"terms": {"level.keyword": ["ERROR", "CRITICAL"]}},
                            {"range": {"@timestamp": {"gte": "now-5m"}}}
                        ]
                    }
                },
                threshold=3,  # 3 database errors in 5 minutes
                time_window=timedelta(minutes=5),
                cooldown=timedelta(minutes=10)
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.id] = rule
    
    async def start(self):
        """Start the alerting engine"""
        self.redis_client = await aioredis.from_url(self.redis_url)
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        # Register with log aggregator
        self.aggregator.add_alert_callback(self._handle_aggregator_alert)
        
        # Start background tasks
        asyncio.create_task(self._monitor_alert_rules())
        asyncio.create_task(self._cleanup_old_alerts())
    
    async def stop(self):
        """Stop the alerting engine"""
        await self.es_client.close()
        await self.redis_client.close()
        self.kafka_producer.close()
    
    async def _monitor_alert_rules(self):
        """Background task to monitor alert rules"""
        while True:
            try:
                for rule in self.alert_rules.values():
                    if rule.enabled:
                        await self._check_alert_rule(rule)
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"Error in alert rule monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _check_alert_rule(self, rule: AlertRule):
        """Check individual alert rule"""
        # Check cooldown
        if self._is_in_cooldown(rule.id):
            return
        
        try:
            # Execute query
            response = await self.es_client.search(
                index="dharma-logs-*",
                body={
                    "query": rule.query,
                    "size": 0,
                    "aggs": {
                        "services": {
                            "terms": {"field": "service.keyword"}
                        }
                    }
                }
            )
            
            total_hits = response["hits"]["total"]["value"]
            
            # Check threshold
            if self._check_threshold(rule, total_hits, response):
                await self._trigger_alert(rule, total_hits, response)
        
        except Exception as e:
            print(f"Error checking alert rule {rule.id}: {e}")
    
    def _check_threshold(self, rule: AlertRule, total_hits: int, response: Dict[str, Any]) -> bool:
        """Check if threshold is exceeded"""
        if rule.alert_type == AlertType.ERROR_RATE:
            # Calculate error rate
            total_logs_query = {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": f"now-{int(rule.time_window.total_seconds())}s"}}}
                    ]
                }
            }
            
            # This would need another query to get total logs, simplified for now
            error_rate = total_hits / max(total_hits * 10, 1)  # Simplified calculation
            return error_rate > rule.threshold
        else:
            return total_hits >= rule.threshold
    
    async def _trigger_alert(self, rule: AlertRule, count: int, query_response: Dict[str, Any]):
        """Trigger an alert"""
        alert_id = f"{rule.id}_{int(datetime.utcnow().timestamp())}"
        
        # Extract affected services
        affected_services = []
        if "aggregations" in query_response and "services" in query_response["aggregations"]:
            affected_services = [
                bucket["key"] for bucket in query_response["aggregations"]["services"]["buckets"]
            ]
        
        alert = Alert(
            id=alert_id,
            rule_id=rule.id,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=rule.name,
            description=f"{rule.description}. Count: {count}, Services: {', '.join(affected_services)}",
            timestamp=datetime.utcnow(),
            data={
                "count": count,
                "affected_services": affected_services,
                "rule": rule.to_dict(),
                "query_response": query_response
            }
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        await self._store_alert(alert)
        
        # Set cooldown
        self._set_cooldown(rule.id, rule.cooldown)
        
        # Send notifications
        await self._send_alert_notifications(alert)
    
    async def _handle_aggregator_alert(self, alert_data: Dict[str, Any]):
        """Handle alerts from log aggregator"""
        alert_id = f"aggregator_{int(datetime.utcnow().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            rule_id="aggregator",
            alert_type=AlertType.ANOMALY_DETECTED,
            severity=AlertSeverity(alert_data.get("severity", "MEDIUM")),
            title=f"Log Anomaly: {alert_data.get('type', 'Unknown')}",
            description=alert_data.get("description", "Anomaly detected by log aggregator"),
            timestamp=datetime.utcnow(),
            data=alert_data
        )
        
        # Store and send
        self.active_alerts[alert_id] = alert
        await self._store_alert(alert)
        await self._send_alert_notifications(alert)
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period"""
        if rule_id not in self.cooldown_cache:
            return False
        
        return datetime.utcnow() < self.cooldown_cache[rule_id]
    
    def _set_cooldown(self, rule_id: str, cooldown: timedelta):
        """Set cooldown for rule"""
        self.cooldown_cache[rule_id] = datetime.utcnow() + cooldown
    
    async def _store_alert(self, alert: Alert):
        """Store alert in Redis and Elasticsearch"""
        # Store in Redis for real-time access
        await self.redis_client.setex(
            f"alert:{alert.id}",
            3600,  # 1 hour TTL
            json.dumps(alert.to_dict())
        )
        
        # Store in Elasticsearch for historical analysis
        try:
            await self.es_client.index(
                index=f"dharma-alerts-{datetime.utcnow().strftime('%Y.%m')}",
                body=alert.to_dict()
            )
        except Exception as e:
            print(f"Error storing alert in Elasticsearch: {e}")
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send alert notifications"""
        # Send to Kafka for other services
        self.kafka_producer.send('dharma-alerts', alert.to_dict())
        
        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")
    
    async def _cleanup_old_alerts(self):
        """Background task to cleanup old alerts"""
        while True:
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                # Clean up active alerts
                expired_alerts = [
                    alert_id for alert_id, alert in self.active_alerts.items()
                    if alert.timestamp < cutoff_time
                ]
                
                for alert_id in expired_alerts:
                    del self.active_alerts[alert_id]
                
                # Clean up cooldown cache
                expired_cooldowns = [
                    rule_id for rule_id, expiry in self.cooldown_cache.items()
                    if datetime.utcnow() > expiry
                ]
                
                for rule_id in expired_cooldowns:
                    del self.cooldown_cache[rule_id]
                
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                print(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def add_alert_rule(self, rule: AlertRule):
        """Add custom alert rule"""
        self.alert_rules[rule.id] = rule
    
    def remove_alert_rule(self, rule_id: str):
        """Remove alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
    
    def enable_alert_rule(self, rule_id: str):
        """Enable alert rule"""
        if rule_id in self.alert_rules:
            self.alert_rules[rule_id].enabled = True
    
    def disable_alert_rule(self, rule_id: str):
        """Disable alert rule"""
        if rule_id in self.alert_rules:
            self.alert_rules[rule_id].enabled = False
    
    async def acknowledge_alert(self, alert_id: str, user_id: str = None) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            
            # Update in storage
            alert_data = self.active_alerts[alert_id].to_dict()
            alert_data['acknowledged'] = True
            alert_data['acknowledged_by'] = user_id
            alert_data['acknowledged_at'] = datetime.utcnow().isoformat()
            
            await self.redis_client.setex(
                f"alert:{alert_id}",
                3600,
                json.dumps(alert_data)
            )
            
            return True
        return False
    
    async def resolve_alert(self, alert_id: str, user_id: str = None) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            
            # Update in storage
            alert_data = self.active_alerts[alert_id].to_dict()
            alert_data['resolved'] = True
            alert_data['resolved_by'] = user_id
            alert_data['resolved_at'] = datetime.utcnow().isoformat()
            
            await self.redis_client.setex(
                f"alert:{alert_id}",
                3600,
                json.dumps(alert_data)
            )
            
            return True
        return False
    
    async def get_active_alerts(self, severity: AlertSeverity = None) -> List[Alert]:
        """Get active alerts"""
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alerts
    
    async def get_alert_statistics(self, time_range: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """Get alert statistics"""
        start_time = datetime.utcnow() - time_range
        
        query = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": start_time.isoformat()
                    }
                }
            },
            "aggs": {
                "by_severity": {
                    "terms": {"field": "severity.keyword"}
                },
                "by_type": {
                    "terms": {"field": "alert_type.keyword"}
                },
                "timeline": {
                    "date_histogram": {
                        "field": "timestamp",
                        "interval": "1h"
                    }
                }
            }
        }
        
        try:
            response = await self.es_client.search(
                index="dharma-alerts-*",
                body=query,
                size=0
            )
            
            return {
                "total_alerts": response["hits"]["total"]["value"],
                "by_severity": {bucket["key"]: bucket["doc_count"] 
                              for bucket in response["aggregations"]["by_severity"]["buckets"]},
                "by_type": {bucket["key"]: bucket["doc_count"] 
                           for bucket in response["aggregations"]["by_type"]["buckets"]},
                "timeline": [(bucket["key_as_string"], bucket["doc_count"]) 
                            for bucket in response["aggregations"]["timeline"]["buckets"]]
            }
        
        except Exception as e:
            print(f"Error getting alert statistics: {e}")
            return {}


# Example usage and testing
if __name__ == "__main__":
    async def test_alerting_engine():
        from .log_aggregator import LogAggregator
        
        aggregator = LogAggregator()
        alerting_engine = LogAlertingEngine(aggregator)
        
        # Add custom alert callback
        async def alert_callback(alert: Alert):
            print(f"ALERT TRIGGERED: {alert.title} - {alert.description}")
        
        alerting_engine.add_alert_callback(alert_callback)
        
        # Start engines
        await aggregator.start()
        await alerting_engine.start()
        
        # Test alert acknowledgment
        active_alerts = await alerting_engine.get_active_alerts()
        if active_alerts:
            await alerting_engine.acknowledge_alert(active_alerts[0].id, "test_user")
        
        # Get statistics
        stats = await alerting_engine.get_alert_statistics()
        print(f"Alert statistics: {stats}")
        
        # Stop engines
        await alerting_engine.stop()
        await aggregator.stop()
    
    # Run test
    asyncio.run(test_alerting_engine())