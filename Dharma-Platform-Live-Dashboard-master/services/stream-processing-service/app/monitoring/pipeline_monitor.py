"""
Pipeline monitoring and health checks for stream processing
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    messages_processed: int = 0
    messages_failed: int = 0
    average_processing_time: float = 0.0
    throughput_per_second: float = 0.0
    error_rate: float = 0.0
    queue_depth: int = 0
    active_workers: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_updated: Optional[datetime] = None


class PipelineMonitor:
    """Comprehensive pipeline monitoring system"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.running = False
        self.health_checks: Dict[str, HealthCheck] = {}
        self.metrics = PipelineMetrics()
        self.alert_thresholds = self._get_default_thresholds()
        self.alert_callbacks: List[callable] = []
        
        # Metrics history for trend analysis
        self.metrics_history: List[PipelineMetrics] = []
        self.max_history_size = 1440  # 24 hours of minute-by-minute data
    
    def _get_default_thresholds(self) -> Dict[str, Any]:
        """Get default alert thresholds"""
        return {
            "error_rate_warning": 0.05,  # 5%
            "error_rate_critical": 0.10,  # 10%
            "response_time_warning": 5000,  # 5 seconds
            "response_time_critical": 10000,  # 10 seconds
            "queue_depth_warning": 1000,
            "queue_depth_critical": 5000,
            "cpu_usage_warning": 80.0,  # 80%
            "cpu_usage_critical": 95.0,  # 95%
            "memory_usage_warning": 80.0,  # 80%
            "memory_usage_critical": 95.0,  # 95%
        }
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        self.running = True
        logger.info("Starting pipeline monitoring")
        
        try:
            while self.running:
                await self._run_health_checks()
                await self._collect_metrics()
                await self._check_alerts()
                await self._cleanup_old_data()
                await asyncio.sleep(self.check_interval)
        except Exception as e:
            logger.error("Error in monitoring loop", error=str(e))
        finally:
            self.running = False
            logger.info("Pipeline monitoring stopped")
    
    async def _run_health_checks(self):
        """Run all registered health checks"""
        check_tasks = []
        
        # Kafka connectivity check
        check_tasks.append(self._check_kafka_connectivity())
        
        # Worker pool health check
        check_tasks.append(self._check_worker_pool_health())
        
        # Database connectivity checks
        check_tasks.append(self._check_database_connectivity())
        
        # Memory and CPU checks
        check_tasks.append(self._check_system_resources())
        
        # Run all checks concurrently
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Health check {i} failed", error=str(result))
    
    async def _check_kafka_connectivity(self):
        """Check Kafka broker connectivity"""
        start_time = time.time()
        
        try:
            # This would typically use the actual Kafka health checker
            # For now, simulate the check
            await asyncio.sleep(0.1)  # Simulate network call
            
            response_time = (time.time() - start_time) * 1000
            
            if response_time > self.alert_thresholds["response_time_critical"]:
                status = HealthStatus.CRITICAL
                message = f"Kafka response time too high: {response_time:.2f}ms"
            elif response_time > self.alert_thresholds["response_time_warning"]:
                status = HealthStatus.WARNING
                message = f"Kafka response time elevated: {response_time:.2f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Kafka connectivity normal"
            
            self.health_checks["kafka"] = HealthCheck(
                name="kafka",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time
            )
            
        except Exception as e:
            self.health_checks["kafka"] = HealthCheck(
                name="kafka",
                status=HealthStatus.CRITICAL,
                message=f"Kafka connectivity failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_worker_pool_health(self):
        """Check worker pool health"""
        try:
            # This would integrate with the actual worker pool
            # For now, simulate worker pool metrics
            active_workers = 5  # Simulated
            total_capacity = active_workers * 10
            current_load = 25  # Simulated
            
            utilization = current_load / total_capacity if total_capacity > 0 else 0
            
            if utilization > 0.9:
                status = HealthStatus.CRITICAL
                message = f"Worker pool overloaded: {utilization:.1%} utilization"
            elif utilization > 0.8:
                status = HealthStatus.WARNING
                message = f"Worker pool high utilization: {utilization:.1%}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Worker pool normal: {utilization:.1%} utilization"
            
            self.health_checks["worker_pool"] = HealthCheck(
                name="worker_pool",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                details={
                    "active_workers": active_workers,
                    "current_load": current_load,
                    "utilization": utilization
                }
            )
            
        except Exception as e:
            self.health_checks["worker_pool"] = HealthCheck(
                name="worker_pool",
                status=HealthStatus.CRITICAL,
                message=f"Worker pool check failed: {str(e)}",
                timestamp=datetime.utcnow()
            )
    
    async def _check_database_connectivity(self):
        """Check database connectivity"""
        try:
            # Simulate database connectivity checks
            await asyncio.sleep(0.05)  # Simulate DB call
            
            self.health_checks["database"] = HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connectivity normal",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.health_checks["database"] = HealthCheck(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"Database connectivity failed: {str(e)}",
                timestamp=datetime.utcnow()
            )
    
    async def _check_system_resources(self):
        """Check system resource usage"""
        try:
            # Simulate system resource checks
            # In a real implementation, this would use psutil or similar
            cpu_usage = 45.0  # Simulated
            memory_usage = 60.0  # Simulated
            
            # Check CPU usage
            if cpu_usage > self.alert_thresholds["cpu_usage_critical"]:
                cpu_status = HealthStatus.CRITICAL
            elif cpu_usage > self.alert_thresholds["cpu_usage_warning"]:
                cpu_status = HealthStatus.WARNING
            else:
                cpu_status = HealthStatus.HEALTHY
            
            # Check memory usage
            if memory_usage > self.alert_thresholds["memory_usage_critical"]:
                memory_status = HealthStatus.CRITICAL
            elif memory_usage > self.alert_thresholds["memory_usage_warning"]:
                memory_status = HealthStatus.WARNING
            else:
                memory_status = HealthStatus.HEALTHY
            
            # Overall system status
            overall_status = max(cpu_status, memory_status, key=lambda x: x.value)
            
            self.health_checks["system_resources"] = HealthCheck(
                name="system_resources",
                status=overall_status,
                message=f"CPU: {cpu_usage:.1f}%, Memory: {memory_usage:.1f}%",
                timestamp=datetime.utcnow(),
                details={
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage
                }
            )
            
            # Update metrics
            self.metrics.cpu_usage = cpu_usage
            self.metrics.memory_usage = memory_usage
            
        except Exception as e:
            self.health_checks["system_resources"] = HealthCheck(
                name="system_resources",
                status=HealthStatus.CRITICAL,
                message=f"System resource check failed: {str(e)}",
                timestamp=datetime.utcnow()
            )
    
    async def _collect_metrics(self):
        """Collect pipeline performance metrics"""
        try:
            # This would integrate with actual pipeline components
            # For now, simulate metrics collection
            
            current_time = datetime.utcnow()
            
            # Simulate metrics
            self.metrics.messages_processed += 100  # Simulated increment
            self.metrics.messages_failed += 2  # Simulated increment
            self.metrics.average_processing_time = 150.0  # ms
            self.metrics.throughput_per_second = 50.0
            self.metrics.queue_depth = 150
            self.metrics.active_workers = 5
            self.metrics.last_updated = current_time
            
            # Calculate error rate
            total_messages = self.metrics.messages_processed + self.metrics.messages_failed
            self.metrics.error_rate = self.metrics.messages_failed / total_messages if total_messages > 0 else 0
            
            # Store metrics history
            self.metrics_history.append(self.metrics)
            
            logger.debug("Metrics collected",
                        messages_processed=self.metrics.messages_processed,
                        error_rate=self.metrics.error_rate,
                        throughput=self.metrics.throughput_per_second)
            
        except Exception as e:
            logger.error("Error collecting metrics", error=str(e))
    
    async def _check_alerts(self):
        """Check for alert conditions and trigger notifications"""
        alerts = []
        
        # Check error rate
        if self.metrics.error_rate > self.alert_thresholds["error_rate_critical"]:
            alerts.append({
                "level": "critical",
                "metric": "error_rate",
                "value": self.metrics.error_rate,
                "threshold": self.alert_thresholds["error_rate_critical"],
                "message": f"Critical error rate: {self.metrics.error_rate:.2%}"
            })
        elif self.metrics.error_rate > self.alert_thresholds["error_rate_warning"]:
            alerts.append({
                "level": "warning",
                "metric": "error_rate",
                "value": self.metrics.error_rate,
                "threshold": self.alert_thresholds["error_rate_warning"],
                "message": f"High error rate: {self.metrics.error_rate:.2%}"
            })
        
        # Check queue depth
        if self.metrics.queue_depth > self.alert_thresholds["queue_depth_critical"]:
            alerts.append({
                "level": "critical",
                "metric": "queue_depth",
                "value": self.metrics.queue_depth,
                "threshold": self.alert_thresholds["queue_depth_critical"],
                "message": f"Critical queue depth: {self.metrics.queue_depth}"
            })
        elif self.metrics.queue_depth > self.alert_thresholds["queue_depth_warning"]:
            alerts.append({
                "level": "warning",
                "metric": "queue_depth",
                "value": self.metrics.queue_depth,
                "threshold": self.alert_thresholds["queue_depth_warning"],
                "message": f"High queue depth: {self.metrics.queue_depth}"
            })
        
        # Trigger alerts
        for alert in alerts:
            await self._trigger_alert(alert)
    
    async def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger alert notification"""
        logger.warning("Pipeline alert triggered",
                      level=alert["level"],
                      metric=alert["metric"],
                      message=alert["message"])
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error("Error in alert callback", error=str(e))
    
    async def _cleanup_old_data(self):
        """Clean up old metrics data"""
        if len(self.metrics_history) > self.max_history_size:
            # Keep only the most recent data
            self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        # Clean up old health checks (keep only recent ones)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        for check_name, check in list(self.health_checks.items()):
            if check.timestamp < cutoff_time:
                # Update with unknown status if too old
                self.health_checks[check_name] = HealthCheck(
                    name=check_name,
                    status=HealthStatus.UNKNOWN,
                    message="Check data too old",
                    timestamp=datetime.utcnow()
                )
    
    def register_alert_callback(self, callback: callable):
        """Register callback for alert notifications"""
        self.alert_callbacks.append(callback)
        logger.info("Registered alert callback")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        if not self.health_checks:
            return {
                "overall_status": HealthStatus.UNKNOWN.value,
                "message": "No health checks available",
                "checks": {}
            }
        
        # Determine overall status
        statuses = [check.status for check in self.health_checks.values()]
        
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        elif HealthStatus.UNKNOWN in statuses:
            overall_status = HealthStatus.UNKNOWN
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "overall_status": overall_status.value,
            "message": f"Pipeline status: {overall_status.value}",
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "response_time_ms": check.response_time_ms,
                    "details": check.details
                }
                for name, check in self.health_checks.items()
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current pipeline metrics"""
        return {
            "messages_processed": self.metrics.messages_processed,
            "messages_failed": self.metrics.messages_failed,
            "error_rate": self.metrics.error_rate,
            "average_processing_time": self.metrics.average_processing_time,
            "throughput_per_second": self.metrics.throughput_per_second,
            "queue_depth": self.metrics.queue_depth,
            "active_workers": self.metrics.active_workers,
            "cpu_usage": self.metrics.cpu_usage,
            "memory_usage": self.metrics.memory_usage,
            "last_updated": self.metrics.last_updated.isoformat() if self.metrics.last_updated else None
        }
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_metrics = [
            {
                "timestamp": m.last_updated.isoformat() if m.last_updated else None,
                "messages_processed": m.messages_processed,
                "error_rate": m.error_rate,
                "throughput_per_second": m.throughput_per_second,
                "queue_depth": m.queue_depth,
                "cpu_usage": m.cpu_usage,
                "memory_usage": m.memory_usage
            }
            for m in self.metrics_history
            if m.last_updated and m.last_updated > cutoff_time
        ]
        
        return recent_metrics
    
    def update_thresholds(self, new_thresholds: Dict[str, Any]):
        """Update alert thresholds"""
        self.alert_thresholds.update(new_thresholds)
        logger.info("Updated alert thresholds", thresholds=new_thresholds)
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("Stopping pipeline monitoring")