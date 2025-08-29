"""
Comprehensive health check system for Project Dharma
Provides health monitoring for all services and dependencies
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import aiohttp
import aioredis
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient
from elasticsearch import AsyncElasticsearch
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result data structure"""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['timestamp'] = self.timestamp.isoformat()
        return result


class HealthChecker:
    """Base health checker class"""
    
    def __init__(self, name: str, timeout: float = 5.0):
        self.name = name
        self.timeout = timeout
        self.last_check: Optional[HealthCheckResult] = None
    
    async def check_health(self) -> HealthCheckResult:
        """Perform health check - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def _timed_check(self, check_func: Callable) -> HealthCheckResult:
        """Execute health check with timing"""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(check_func(), timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                result.response_time_ms = response_time
                return result
            else:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Health check passed",
                    timestamp=datetime.utcnow(),
                    response_time_ms=response_time,
                    details=result if isinstance(result, dict) else None
                )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                timestamp=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000
            )
        
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000,
                details={"error_type": type(e).__name__, "error_message": str(e)}
            )


class DatabaseHealthChecker(HealthChecker):
    """Health checker for database connections"""
    
    def __init__(self, name: str, connection_string: str, db_type: str):
        super().__init__(name)
        self.connection_string = connection_string
        self.db_type = db_type.lower()
    
    async def check_health(self) -> HealthCheckResult:
        """Check database health"""
        return await self._timed_check(self._check_database)
    
    async def _check_database(self) -> Dict[str, Any]:
        """Perform database-specific health check"""
        if self.db_type == "postgresql":
            return await self._check_postgresql()
        elif self.db_type == "mongodb":
            return await self._check_mongodb()
        elif self.db_type == "redis":
            return await self._check_redis()
        elif self.db_type == "elasticsearch":
            return await self._check_elasticsearch()
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    async def _check_postgresql(self) -> Dict[str, Any]:
        """Check PostgreSQL health"""
        conn = await asyncpg.connect(self.connection_string)
        try:
            # Test basic connectivity
            result = await conn.fetchval("SELECT 1")
            
            # Get database stats
            stats = await conn.fetchrow("""
                SELECT 
                    count(*) as active_connections,
                    pg_database_size(current_database()) as db_size
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            
            return {
                "connection_test": result == 1,
                "active_connections": stats["active_connections"],
                "database_size_bytes": stats["db_size"]
            }
        finally:
            await conn.close()
    
    async def _check_mongodb(self) -> Dict[str, Any]:
        """Check MongoDB health"""
        client = AsyncIOMotorClient(self.connection_string)
        try:
            # Test basic connectivity
            await client.admin.command("ping")
            
            # Get server status
            status = await client.admin.command("serverStatus")
            
            return {
                "connection_test": True,
                "version": status.get("version"),
                "uptime_seconds": status.get("uptime"),
                "connections": status.get("connections", {})
            }
        finally:
            client.close()
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis health"""
        redis = aioredis.from_url(self.connection_string)
        try:
            # Test basic connectivity
            pong = await redis.ping()
            
            # Get Redis info
            info = await redis.info()
            
            return {
                "connection_test": pong,
                "version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human")
            }
        finally:
            await redis.close()
    
    async def _check_elasticsearch(self) -> Dict[str, Any]:
        """Check Elasticsearch health"""
        es = AsyncElasticsearch([self.connection_string])
        try:
            # Test basic connectivity
            health = await es.cluster.health()
            
            # Get cluster stats
            stats = await es.cluster.stats()
            
            return {
                "cluster_status": health.get("status"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_primary_shards": health.get("active_primary_shards"),
                "active_shards": health.get("active_shards"),
                "indices_count": stats.get("indices", {}).get("count", 0)
            }
        finally:
            await es.close()


class HTTPServiceHealthChecker(HealthChecker):
    """Health checker for HTTP services"""
    
    def __init__(self, name: str, url: str, expected_status: int = 200):
        super().__init__(name)
        self.url = url
        self.expected_status = expected_status
    
    async def check_health(self) -> HealthCheckResult:
        """Check HTTP service health"""
        return await self._timed_check(self._check_http_service)
    
    async def _check_http_service(self) -> Dict[str, Any]:
        """Perform HTTP health check"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                return {
                    "status_code": response.status,
                    "expected_status": self.expected_status,
                    "status_match": response.status == self.expected_status,
                    "headers": dict(response.headers),
                    "content_length": response.headers.get("content-length")
                }


class KafkaHealthChecker(HealthChecker):
    """Health checker for Kafka"""
    
    def __init__(self, name: str, bootstrap_servers: List[str]):
        super().__init__(name)
        self.bootstrap_servers = bootstrap_servers
    
    async def check_health(self) -> HealthCheckResult:
        """Check Kafka health"""
        return await self._timed_check(self._check_kafka)
    
    async def _check_kafka(self) -> Dict[str, Any]:
        """Perform Kafka health check"""
        try:
            # Test producer connectivity
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                request_timeout_ms=5000,
                api_version=(0, 10, 1)
            )
            
            # Get cluster metadata
            metadata = producer.list_topics()
            
            producer.close()
            
            return {
                "connection_test": True,
                "topics_count": len(metadata),
                "topics": list(metadata)[:10]  # Limit to first 10 topics
            }
        
        except KafkaError as e:
            raise Exception(f"Kafka connection failed: {str(e)}")


class SystemResourceHealthChecker(HealthChecker):
    """Health checker for system resources"""
    
    def __init__(self, name: str = "system_resources"):
        super().__init__(name)
    
    async def check_health(self) -> HealthCheckResult:
        """Check system resource health"""
        return await self._timed_check(self._check_system_resources)
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            warnings = []
            
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                warnings.append(f"High CPU usage: {cpu_percent}%")
            elif cpu_percent > 70:
                status = HealthStatus.DEGRADED
                warnings.append(f"Elevated CPU usage: {cpu_percent}%")
            
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                warnings.append(f"High memory usage: {memory.percent}%")
            elif memory.percent > 70:
                status = HealthStatus.DEGRADED
                warnings.append(f"Elevated memory usage: {memory.percent}%")
            
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 90:
                status = HealthStatus.UNHEALTHY
                warnings.append(f"High disk usage: {disk_percent:.1f}%")
            elif disk_percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append(f"Elevated disk usage: {disk_percent:.1f}%")
            
            return {
                "status": status,
                "warnings": warnings,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk_percent,
                "disk_free_gb": disk.free / (1024**3),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv
            }
        
        except ImportError:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "psutil not available for system monitoring"
            }


class CompositeHealthChecker:
    """Composite health checker that manages multiple health checkers"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.checkers: Dict[str, HealthChecker] = {}
        self.check_interval = 30  # seconds
        self.running = False
        self._check_task: Optional[asyncio.Task] = None
        self.last_results: Dict[str, HealthCheckResult] = {}
    
    def add_checker(self, checker: HealthChecker):
        """Add a health checker"""
        self.checkers[checker.name] = checker
        logger.info(f"Added health checker: {checker.name}")
    
    def remove_checker(self, name: str):
        """Remove a health checker"""
        if name in self.checkers:
            del self.checkers[name]
            if name in self.last_results:
                del self.last_results[name]
            logger.info(f"Removed health checker: {name}")
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks"""
        results = {}
        
        # Run all checks concurrently
        tasks = {
            name: asyncio.create_task(checker.check_health())
            for name, checker in self.checkers.items()
        }
        
        # Wait for all checks to complete
        for name, task in tasks.items():
            try:
                result = await task
                results[name] = result
                self.last_results[name] = result
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check error: {str(e)}",
                    timestamp=datetime.utcnow(),
                    response_time_ms=0
                )
        
        return results
    
    async def get_overall_health(self) -> HealthCheckResult:
        """Get overall service health"""
        if not self.last_results:
            await self.check_all()
        
        # Determine overall status
        statuses = [result.status for result in self.last_results.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
            message = "One or more components are unhealthy"
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
            message = "One or more components are degraded"
        elif HealthStatus.UNKNOWN in statuses:
            overall_status = HealthStatus.UNKNOWN
            message = "One or more components have unknown status"
        else:
            overall_status = HealthStatus.HEALTHY
            message = "All components are healthy"
        
        # Calculate average response time
        avg_response_time = sum(
            result.response_time_ms for result in self.last_results.values()
        ) / len(self.last_results) if self.last_results else 0
        
        return HealthCheckResult(
            component=self.service_name,
            status=overall_status,
            message=message,
            timestamp=datetime.utcnow(),
            response_time_ms=avg_response_time,
            details={
                "component_count": len(self.last_results),
                "healthy_count": sum(1 for r in self.last_results.values() if r.status == HealthStatus.HEALTHY),
                "degraded_count": sum(1 for r in self.last_results.values() if r.status == HealthStatus.DEGRADED),
                "unhealthy_count": sum(1 for r in self.last_results.values() if r.status == HealthStatus.UNHEALTHY),
                "components": {name: result.to_dict() for name, result in self.last_results.items()}
            }
        )
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.running:
            return
        
        self.running = True
        self._check_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started health monitoring for {self.service_name}")
    
    async def stop_monitoring(self):
        """Stop continuous health monitoring"""
        if not self.running:
            return
        
        self.running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Stopped health monitoring for {self.service_name}")
    
    async def _monitoring_loop(self):
        """Continuous monitoring loop"""
        while self.running:
            try:
                await self.check_all()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)  # Short delay before retry


# Global health checker instance
_health_checker: Optional[CompositeHealthChecker] = None


def get_health_checker(service_name: str = "dharma-service") -> CompositeHealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = CompositeHealthChecker(service_name)
    return _health_checker


def setup_default_health_checks(service_name: str, config: Dict[str, Any]) -> CompositeHealthChecker:
    """Setup default health checks based on configuration"""
    health_checker = get_health_checker(service_name)
    
    # System resources
    health_checker.add_checker(SystemResourceHealthChecker())
    
    # Database health checks
    if "postgresql" in config:
        health_checker.add_checker(
            DatabaseHealthChecker(
                "postgresql",
                config["postgresql"]["connection_string"],
                "postgresql"
            )
        )
    
    if "mongodb" in config:
        health_checker.add_checker(
            DatabaseHealthChecker(
                "mongodb",
                config["mongodb"]["connection_string"],
                "mongodb"
            )
        )
    
    if "redis" in config:
        health_checker.add_checker(
            DatabaseHealthChecker(
                "redis",
                config["redis"]["connection_string"],
                "redis"
            )
        )
    
    if "elasticsearch" in config:
        health_checker.add_checker(
            DatabaseHealthChecker(
                "elasticsearch",
                config["elasticsearch"]["connection_string"],
                "elasticsearch"
            )
        )
    
    # Kafka health check
    if "kafka" in config:
        health_checker.add_checker(
            KafkaHealthChecker(
                "kafka",
                config["kafka"]["bootstrap_servers"]
            )
        )
    
    # External service health checks
    if "external_services" in config:
        for service_name, service_config in config["external_services"].items():
            health_checker.add_checker(
                HTTPServiceHealthChecker(
                    service_name,
                    service_config["health_url"],
                    service_config.get("expected_status", 200)
                )
            )
    
    return health_checker