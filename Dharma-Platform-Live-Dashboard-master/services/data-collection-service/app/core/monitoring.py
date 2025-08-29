"""
Monitoring and logging for data collection pipeline
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
from contextlib import asynccontextmanager

from app.core.config import get_settings
from shared.database.redis import RedisManager
from shared.models.post import Platform

logger = structlog.get_logger()


class MetricType(str, Enum):
    """Types of metrics to collect"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Metric data structure"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'labels': self.labels,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    labels: Dict[str, str]
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'alert_id': self.alert_id,
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'labels': self.labels,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class MetricsCollector:
    """Collects and stores metrics for monitoring"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        self.metrics_buffer: List[Metric] = []
        self.buffer_size = 100
        self.flush_interval = 30  # seconds
        self.last_flush = time.time()
    
    async def record_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Record a counter metric"""
        await self._record_metric(name, value, MetricType.COUNTER, labels or {})
    
    async def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a gauge metric"""
        await self._record_metric(name, value, MetricType.GAUGE, labels or {})
    
    async def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric"""
        await self._record_metric(name, value, MetricType.HISTOGRAM, labels or {})
    
    async def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """Record a timer metric"""
        await self._record_metric(name, duration, MetricType.TIMER, labels or {})
    
    async def _record_metric(self, name: str, value: float, metric_type: MetricType, labels: Dict[str, str]):
        """Record a metric in the buffer"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels,
            timestamp=datetime.utcnow()
        )
        
        self.metrics_buffer.append(metric)
        
        # Flush buffer if needed
        if (len(self.metrics_buffer) >= self.buffer_size or 
            time.time() - self.last_flush >= self.flush_interval):
            await self._flush_metrics()
    
    async def _flush_metrics(self):
        """Flush metrics buffer to Redis"""
        if not self.metrics_buffer:
            return
        
        try:
            # Store metrics in Redis with time-based keys
            current_time = datetime.utcnow()
            metrics_key = f"metrics:{current_time.strftime('%Y-%m-%d:%H:%M')}"
            
            metrics_data = [metric.to_dict() for metric in self.metrics_buffer]
            
            # Store as JSON list
            await self.redis.lpush(metrics_key, *[json.dumps(metric) for metric in metrics_data])
            
            # Set TTL for metrics (7 days)
            await self.redis.expire(metrics_key, 86400 * 7)
            
            logger.debug("Flushed metrics to Redis", count=len(self.metrics_buffer))
            
            # Clear buffer
            self.metrics_buffer.clear()
            self.last_flush = time.time()
            
        except Exception as e:
            logger.error("Failed to flush metrics", error=str(e))
    
    async def get_metrics(self, name_pattern: str = "*", 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Retrieve metrics from Redis"""
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(hours=1)
            if not end_time:
                end_time = datetime.utcnow()
            
            metrics = []
            
            # Generate time range keys
            current = start_time.replace(second=0, microsecond=0)
            while current <= end_time:
                metrics_key = f"metrics:{current.strftime('%Y-%m-%d:%H:%M')}"
                
                # Get metrics for this time period
                metric_strings = await self.redis.lrange(metrics_key, 0, -1)
                
                for metric_str in metric_strings:
                    try:
                        metric_data = json.loads(metric_str)
                        
                        # Filter by name pattern if specified
                        if name_pattern != "*" and name_pattern not in metric_data['name']:
                            continue
                        
                        metrics.append(metric_data)
                    except json.JSONDecodeError:
                        continue
                
                current += timedelta(minutes=1)
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to retrieve metrics", error=str(e))
            return []
    
    @asynccontextmanager
    async def timer_context(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            await self.record_timer(name, duration, labels or {})


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        self.alert_rules: List[Callable] = []
        self.active_alerts: Dict[str, Alert] = {}
    
    async def create_alert(self, level: AlertLevel, title: str, message: str, 
                          labels: Dict[str, str] = None) -> str:
        """Create a new alert"""
        import uuid
        
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            alert_id=alert_id,
            level=level,
            title=title,
            message=message,
            labels=labels or {},
            timestamp=datetime.utcnow()
        )
        
        # Store alert
        await self._store_alert(alert)
        self.active_alerts[alert_id] = alert
        
        logger.warning("Alert created", 
                      alert_id=alert_id, 
                      level=level.value, 
                      title=title)
        
        return alert_id
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                
                await self._store_alert(alert)
                del self.active_alerts[alert_id]
                
                logger.info("Alert resolved", alert_id=alert_id)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
            return False
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    async def add_alert_rule(self, rule_func: Callable):
        """Add an alert rule function"""
        self.alert_rules.append(rule_func)
    
    async def check_alert_rules(self, metrics: List[Dict[str, Any]]):
        """Check all alert rules against current metrics"""
        for rule_func in self.alert_rules:
            try:
                await rule_func(metrics, self)
            except Exception as e:
                logger.error("Error in alert rule", rule=rule_func.__name__, error=str(e))
    
    async def _store_alert(self, alert: Alert):
        """Store alert in Redis"""
        try:
            alert_key = f"alert:{alert.alert_id}"
            await self.redis.setex(alert_key, 86400 * 30, json.dumps(alert.to_dict()))  # 30 day TTL
            
            # Add to alerts index
            alerts_index_key = "alerts:index"
            await self.redis.zadd(alerts_index_key, {alert.alert_id: alert.timestamp.timestamp()})
            
        except Exception as e:
            logger.error("Failed to store alert", alert_id=alert.alert_id, error=str(e))


class DataCollectionMonitor:
    """Main monitoring system for data collection pipeline"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis = RedisManager()
        self.metrics_collector = MetricsCollector(self.redis)
        self.alert_manager = AlertManager(self.redis)
        self.monitoring_active = False
    
    async def initialize(self):
        """Initialize monitoring system"""
        try:
            await self.redis.connect()
            await self._setup_default_alert_rules()
            logger.info("Data collection monitoring initialized")
        except Exception as e:
            logger.error("Failed to initialize monitoring", error=str(e))
            raise
    
    async def start_monitoring(self):
        """Start monitoring loop"""
        self.monitoring_active = True
        
        # Start background tasks
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._metrics_flush_loop())
        
        logger.info("Data collection monitoring started")
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logger.info("Data collection monitoring stopped")
    
    async def record_collection_event(self, platform: Platform, event_type: str, 
                                    success: bool = True, duration: Optional[float] = None,
                                    additional_labels: Dict[str, str] = None):
        """Record a data collection event"""
        labels = {
            'platform': platform.value,
            'event_type': event_type,
            'status': 'success' if success else 'failure'
        }
        
        if additional_labels:
            labels.update(additional_labels)
        
        # Record counter
        await self.metrics_collector.record_counter('data_collection_events_total', 1.0, labels)
        
        # Record duration if provided
        if duration is not None:
            await self.metrics_collector.record_timer('data_collection_duration_seconds', duration, labels)
    
    async def record_processing_metrics(self, platform: Platform, processed_count: int, 
                                      failed_count: int, duplicate_count: int):
        """Record data processing metrics"""
        labels = {'platform': platform.value}
        
        await self.metrics_collector.record_counter('data_processed_total', processed_count, labels)
        await self.metrics_collector.record_counter('data_failed_total', failed_count, labels)
        await self.metrics_collector.record_counter('data_duplicates_total', duplicate_count, labels)
    
    async def record_kafka_metrics(self, topic: str, success: bool, latency: float):
        """Record Kafka producer metrics"""
        labels = {
            'topic': topic,
            'status': 'success' if success else 'failure'
        }
        
        await self.metrics_collector.record_counter('kafka_messages_total', 1.0, labels)
        await self.metrics_collector.record_timer('kafka_send_duration_seconds', latency, labels)
    
    async def record_database_metrics(self, operation: str, database: str, success: bool, duration: float):
        """Record database operation metrics"""
        labels = {
            'operation': operation,
            'database': database,
            'status': 'success' if success else 'failure'
        }
        
        await self.metrics_collector.record_counter('database_operations_total', 1.0, labels)
        await self.metrics_collector.record_timer('database_operation_duration_seconds', duration, labels)
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            # Get recent metrics
            recent_metrics = await self.metrics_collector.get_metrics(
                start_time=datetime.utcnow() - timedelta(minutes=5)
            )
            
            # Get active alerts
            active_alerts = await self.alert_manager.get_active_alerts()
            
            # Calculate health score
            health_score = await self._calculate_health_score(recent_metrics, active_alerts)
            
            return {
                'health_score': health_score,
                'status': 'healthy' if health_score > 0.8 else 'degraded' if health_score > 0.5 else 'unhealthy',
                'active_alerts_count': len(active_alerts),
                'critical_alerts_count': len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
                'last_updated': datetime.utcnow().isoformat(),
                'metrics_count': len(recent_metrics)
            }
            
        except Exception as e:
            logger.error("Failed to get system health", error=str(e))
            return {
                'health_score': 0.0,
                'status': 'unknown',
                'error': str(e),
                'last_updated': datetime.utcnow().isoformat()
            }
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Get recent metrics
                metrics = await self.metrics_collector.get_metrics(
                    start_time=datetime.utcnow() - timedelta(minutes=1)
                )
                
                # Check alert rules
                await self.alert_manager.check_alert_rules(metrics)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("Error in monitoring loop", error=str(e))
                await asyncio.sleep(60)
    
    async def _metrics_flush_loop(self):
        """Periodic metrics flush loop"""
        while self.monitoring_active:
            try:
                await self.metrics_collector._flush_metrics()
                await asyncio.sleep(30)  # Flush every 30 seconds
            except Exception as e:
                logger.error("Error in metrics flush loop", error=str(e))
                await asyncio.sleep(30)
    
    async def _setup_default_alert_rules(self):
        """Setup default alert rules"""
        
        async def high_error_rate_rule(metrics: List[Dict[str, Any]], alert_manager: AlertManager):
            """Alert on high error rate"""
            error_count = sum(1 for m in metrics if m['name'] == 'data_collection_events_total' 
                            and m['labels'].get('status') == 'failure')
            total_count = sum(1 for m in metrics if m['name'] == 'data_collection_events_total')
            
            if total_count > 10 and error_count / total_count > 0.1:  # 10% error rate
                await alert_manager.create_alert(
                    AlertLevel.WARNING,
                    "High Error Rate Detected",
                    f"Error rate: {error_count/total_count*100:.1f}% ({error_count}/{total_count})",
                    {'rule': 'high_error_rate'}
                )
        
        async def kafka_connection_issues_rule(metrics: List[Dict[str, Any]], alert_manager: AlertManager):
            """Alert on Kafka connection issues"""
            kafka_failures = sum(1 for m in metrics if m['name'] == 'kafka_messages_total' 
                               and m['labels'].get('status') == 'failure')
            
            if kafka_failures > 5:
                await alert_manager.create_alert(
                    AlertLevel.ERROR,
                    "Kafka Connection Issues",
                    f"Multiple Kafka send failures detected: {kafka_failures}",
                    {'rule': 'kafka_connection_issues'}
                )
        
        async def no_data_collection_rule(metrics: List[Dict[str, Any]], alert_manager: AlertManager):
            """Alert when no data collection events in last 5 minutes"""
            collection_events = [m for m in metrics if m['name'] == 'data_collection_events_total']
            
            if not collection_events:
                await alert_manager.create_alert(
                    AlertLevel.WARNING,
                    "No Data Collection Activity",
                    "No data collection events detected in the last 5 minutes",
                    {'rule': 'no_data_collection'}
                )
        
        # Add alert rules
        await self.alert_manager.add_alert_rule(high_error_rate_rule)
        await self.alert_manager.add_alert_rule(kafka_connection_issues_rule)
        await self.alert_manager.add_alert_rule(no_data_collection_rule)
    
    async def _calculate_health_score(self, metrics: List[Dict[str, Any]], alerts: List[Alert]) -> float:
        """Calculate system health score (0.0 to 1.0)"""
        score = 1.0
        
        # Deduct for active alerts
        for alert in alerts:
            if alert.level == AlertLevel.CRITICAL:
                score -= 0.3
            elif alert.level == AlertLevel.ERROR:
                score -= 0.2
            elif alert.level == AlertLevel.WARNING:
                score -= 0.1
        
        # Deduct for high error rates
        error_metrics = [m for m in metrics if 'failure' in m.get('labels', {}).get('status', '')]
        total_metrics = [m for m in metrics if 'data_collection_events_total' in m['name']]
        
        if total_metrics:
            error_rate = len(error_metrics) / len(total_metrics)
            score -= error_rate * 0.5
        
        return max(0.0, min(1.0, score))
    
    async def cleanup(self):
        """Cleanup monitoring resources"""
        try:
            await self.stop_monitoring()
            await self.metrics_collector._flush_metrics()
            await self.redis.disconnect()
            logger.info("Data collection monitoring cleaned up")
        except Exception as e:
            logger.error("Error during monitoring cleanup", error=str(e))


# Global monitoring instance
_monitor_instance = None


async def get_monitor() -> DataCollectionMonitor:
    """Get or create global monitoring instance"""
    global _monitor_instance
    
    if _monitor_instance is None:
        _monitor_instance = DataCollectionMonitor()
        await _monitor_instance.initialize()
    
    return _monitor_instance