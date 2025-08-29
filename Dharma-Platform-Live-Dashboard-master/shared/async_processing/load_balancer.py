"""Load balancing and auto-scaling for async processing."""

import asyncio
import time
import statistics
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESPONSE_TIME = "response_time"
    RESOURCE_BASED = "resource_based"


class HealthStatus(Enum):
    """Health status for services."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""
    id: str
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100
    timeout: float = 30.0
    health_check_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceMetrics:
    """Service performance metrics."""
    endpoint_id: str
    active_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_response_time: float = 0.0
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    error_rate: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def load_score(self) -> float:
        """Calculate load score for load balancing."""
        # Combine multiple factors into a single load score
        connection_load = self.active_connections / 100.0  # Normalize to 0-1
        response_time_load = min(self.avg_response_time / 1000.0, 1.0)  # Normalize to 0-1
        error_load = self.error_rate
        resource_load = (self.cpu_usage + self.memory_usage) / 200.0
        
        return (connection_load + response_time_load + error_load + resource_load) / 4.0


class LoadBalancer:
    """Advanced load balancer with multiple strategies."""
    
    def __init__(
        self,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS,
        health_check_interval: float = 30.0,
        health_check_timeout: float = 5.0
    ):
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout
        
        self.endpoints: Dict[str, ServiceEndpoint] = {}
        self.metrics: Dict[str, ServiceMetrics] = {}
        self._round_robin_index = 0
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    def add_endpoint(self, endpoint: ServiceEndpoint):
        """Add a service endpoint."""
        self.endpoints[endpoint.id] = endpoint
        self.metrics[endpoint.id] = ServiceMetrics(endpoint_id=endpoint.id)
        
        logger.info("Endpoint added", 
                   endpoint_id=endpoint.id,
                   host=endpoint.host,
                   port=endpoint.port,
                   weight=endpoint.weight)
    
    def remove_endpoint(self, endpoint_id: str):
        """Remove a service endpoint."""
        if endpoint_id in self.endpoints:
            del self.endpoints[endpoint_id]
            del self.metrics[endpoint_id]
            
            logger.info("Endpoint removed", endpoint_id=endpoint_id)
    
    def get_next_endpoint(self) -> Optional[ServiceEndpoint]:
        """Get the next endpoint based on load balancing strategy."""
        healthy_endpoints = [
            endpoint_id for endpoint_id, metrics in self.metrics.items()
            if metrics.health_status == HealthStatus.HEALTHY
        ]
        
        if not healthy_endpoints:
            # Fallback to degraded endpoints if no healthy ones
            healthy_endpoints = [
                endpoint_id for endpoint_id, metrics in self.metrics.items()
                if metrics.health_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            ]
        
        if not healthy_endpoints:
            logger.warning("No healthy endpoints available")
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.RESPONSE_TIME:
            return self._response_time_selection(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.RESOURCE_BASED:
            return self._resource_based_selection(healthy_endpoints)
        else:
            return self._round_robin_selection(healthy_endpoints)
    
    def _round_robin_selection(self, endpoints: List[str]) -> ServiceEndpoint:
        """Round-robin endpoint selection."""
        endpoint_id = endpoints[self._round_robin_index % len(endpoints)]
        self._round_robin_index += 1
        return self.endpoints[endpoint_id]
    
    def _least_connections_selection(self, endpoints: List[str]) -> ServiceEndpoint:
        """Select endpoint with least active connections."""
        min_connections = float('inf')
        selected_endpoint = None
        
        for endpoint_id in endpoints:
            connections = self.metrics[endpoint_id].active_connections
            if connections < min_connections:
                min_connections = connections
                selected_endpoint = endpoint_id
        
        return self.endpoints[selected_endpoint]
    
    def _weighted_round_robin_selection(self, endpoints: List[str]) -> ServiceEndpoint:
        """Weighted round-robin selection based on endpoint weights."""
        # Create weighted list
        weighted_endpoints = []
        for endpoint_id in endpoints:
            weight = self.endpoints[endpoint_id].weight
            weighted_endpoints.extend([endpoint_id] * weight)
        
        if not weighted_endpoints:
            return self._round_robin_selection(endpoints)
        
        endpoint_id = weighted_endpoints[self._round_robin_index % len(weighted_endpoints)]
        self._round_robin_index += 1
        return self.endpoints[endpoint_id]
    
    def _response_time_selection(self, endpoints: List[str]) -> ServiceEndpoint:
        """Select endpoint with best response time."""
        best_time = float('inf')
        selected_endpoint = None
        
        for endpoint_id in endpoints:
            response_time = self.metrics[endpoint_id].avg_response_time
            if response_time < best_time:
                best_time = response_time
                selected_endpoint = endpoint_id
        
        return self.endpoints[selected_endpoint]
    
    def _resource_based_selection(self, endpoints: List[str]) -> ServiceEndpoint:
        """Select endpoint based on resource utilization."""
        lowest_load = float('inf')
        selected_endpoint = None
        
        for endpoint_id in endpoints:
            load_score = self.metrics[endpoint_id].load_score
            if load_score < lowest_load:
                lowest_load = load_score
                selected_endpoint = endpoint_id
        
        return self.endpoints[selected_endpoint]
    
    async def record_request_start(self, endpoint_id: str):
        """Record the start of a request."""
        if endpoint_id in self.metrics:
            self.metrics[endpoint_id].active_connections += 1
            self.metrics[endpoint_id].total_requests += 1
    
    async def record_request_end(
        self, 
        endpoint_id: str, 
        response_time: float, 
        success: bool = True
    ):
        """Record the end of a request."""
        if endpoint_id not in self.metrics:
            return
        
        metrics = self.metrics[endpoint_id]
        metrics.active_connections = max(0, metrics.active_connections - 1)
        metrics.last_response_time = response_time
        
        # Update average response time using exponential moving average
        alpha = 0.1
        if metrics.avg_response_time == 0:
            metrics.avg_response_time = response_time
        else:
            metrics.avg_response_time = (
                alpha * response_time + (1 - alpha) * metrics.avg_response_time
            )
        
        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
        
        # Update error rate
        metrics.error_rate = metrics.failed_requests / metrics.total_requests
    
    async def start_health_checks(self):
        """Start periodic health checks."""
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Health checks started", interval=self.health_check_interval)
    
    async def stop_health_checks(self):
        """Stop health checks."""
        if self._health_check_task:
            self._shutdown_event.set()
            self._health_check_task.cancel()
            
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health checks stopped")
    
    async def _health_check_loop(self):
        """Periodic health check loop."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check loop error", error=str(e))
    
    async def _perform_health_checks(self):
        """Perform health checks on all endpoints."""
        tasks = []
        
        for endpoint_id, endpoint in self.endpoints.items():
            task = asyncio.create_task(
                self._check_endpoint_health(endpoint_id, endpoint)
            )
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_endpoint_health(self, endpoint_id: str, endpoint: ServiceEndpoint):
        """Check health of a single endpoint."""
        try:
            # Simple TCP connection check
            start_time = time.time()
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(endpoint.host, endpoint.port),
                timeout=self.health_check_timeout
            )
            
            writer.close()
            await writer.wait_closed()
            
            response_time = (time.time() - start_time) * 1000
            
            # Update health status based on response time
            if response_time < 100:
                health_status = HealthStatus.HEALTHY
            elif response_time < 500:
                health_status = HealthStatus.DEGRADED
            else:
                health_status = HealthStatus.UNHEALTHY
            
            self.metrics[endpoint_id].health_status = health_status
            self.metrics[endpoint_id].last_health_check = datetime.utcnow()
            
            logger.debug("Health check completed", 
                        endpoint_id=endpoint_id,
                        status=health_status.value,
                        response_time=response_time)
        
        except Exception as e:
            self.metrics[endpoint_id].health_status = HealthStatus.UNHEALTHY
            self.metrics[endpoint_id].last_health_check = datetime.utcnow()
            
            logger.warning("Health check failed", 
                          endpoint_id=endpoint_id,
                          error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        total_requests = sum(m.total_requests for m in self.metrics.values())
        total_successful = sum(m.successful_requests for m in self.metrics.values())
        total_failed = sum(m.failed_requests for m in self.metrics.values())
        
        healthy_endpoints = sum(
            1 for m in self.metrics.values() 
            if m.health_status == HealthStatus.HEALTHY
        )
        
        avg_response_times = [
            m.avg_response_time for m in self.metrics.values() 
            if m.avg_response_time > 0
        ]
        
        return {
            "strategy": self.strategy.value,
            "total_endpoints": len(self.endpoints),
            "healthy_endpoints": healthy_endpoints,
            "total_requests": total_requests,
            "success_rate": total_successful / total_requests if total_requests > 0 else 0,
            "error_rate": total_failed / total_requests if total_requests > 0 else 0,
            "avg_response_time": statistics.mean(avg_response_times) if avg_response_times else 0,
            "endpoint_metrics": {
                endpoint_id: {
                    "health_status": metrics.health_status.value,
                    "active_connections": metrics.active_connections,
                    "total_requests": metrics.total_requests,
                    "success_rate": metrics.success_rate,
                    "avg_response_time": metrics.avg_response_time,
                    "load_score": metrics.load_score
                }
                for endpoint_id, metrics in self.metrics.items()
            }
        }


class AutoScaler:
    """Auto-scaling system for dynamic resource management."""
    
    def __init__(
        self,
        min_instances: int = 1,
        max_instances: int = 10,
        target_cpu_utilization: float = 70.0,
        target_memory_utilization: float = 80.0,
        scale_up_threshold: float = 80.0,
        scale_down_threshold: float = 30.0,
        cooldown_period: float = 300.0,  # 5 minutes
        evaluation_period: float = 60.0   # 1 minute
    ):
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.target_cpu_utilization = target_cpu_utilization
        self.target_memory_utilization = target_memory_utilization
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown_period = cooldown_period
        self.evaluation_period = evaluation_period
        
        self.current_instances = min_instances
        self.last_scale_action = datetime.utcnow()
        self.metrics_history: List[Dict[str, float]] = []
        self._scaling_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Callbacks for scaling actions
        self.scale_up_callback: Optional[Callable] = None
        self.scale_down_callback: Optional[Callable] = None
    
    def set_scale_callbacks(
        self, 
        scale_up_callback: Callable, 
        scale_down_callback: Callable
    ):
        """Set callbacks for scaling actions."""
        self.scale_up_callback = scale_up_callback
        self.scale_down_callback = scale_down_callback
    
    async def start_auto_scaling(self):
        """Start the auto-scaling loop."""
        self._scaling_task = asyncio.create_task(self._scaling_loop())
        logger.info("Auto-scaling started", 
                   min_instances=self.min_instances,
                   max_instances=self.max_instances)
    
    async def stop_auto_scaling(self):
        """Stop the auto-scaling loop."""
        if self._scaling_task:
            self._shutdown_event.set()
            self._scaling_task.cancel()
            
            try:
                await self._scaling_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Auto-scaling stopped")
    
    async def _scaling_loop(self):
        """Main auto-scaling evaluation loop."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.evaluation_period)
                await self._evaluate_scaling()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Auto-scaling evaluation error", error=str(e))
    
    async def _evaluate_scaling(self):
        """Evaluate whether scaling is needed."""
        now = datetime.utcnow()
        
        # Check cooldown period
        if (now - self.last_scale_action).total_seconds() < self.cooldown_period:
            return
        
        # Get current metrics
        current_metrics = await self._get_current_metrics()
        if not current_metrics:
            return
        
        # Add to history
        self.metrics_history.append(current_metrics)
        
        # Keep only recent history (last 10 minutes)
        cutoff_time = now - timedelta(minutes=10)
        self.metrics_history = [
            m for m in self.metrics_history 
            if m.get('timestamp', now) > cutoff_time
        ]
        
        # Calculate average metrics over evaluation period
        if len(self.metrics_history) < 3:  # Need at least 3 data points
            return
        
        avg_cpu = statistics.mean([m['cpu_utilization'] for m in self.metrics_history])
        avg_memory = statistics.mean([m['memory_utilization'] for m in self.metrics_history])
        avg_response_time = statistics.mean([m['avg_response_time'] for m in self.metrics_history])
        
        # Determine scaling action
        should_scale_up = (
            avg_cpu > self.scale_up_threshold or
            avg_memory > self.scale_up_threshold or
            avg_response_time > 1000  # 1 second response time threshold
        )
        
        should_scale_down = (
            avg_cpu < self.scale_down_threshold and
            avg_memory < self.scale_down_threshold and
            avg_response_time < 200  # 200ms response time threshold
        )
        
        if should_scale_up and self.current_instances < self.max_instances:
            await self._scale_up()
        elif should_scale_down and self.current_instances > self.min_instances:
            await self._scale_down()
    
    async def _get_current_metrics(self) -> Optional[Dict[str, float]]:
        """Get current system metrics."""
        # This would typically integrate with monitoring systems
        # For now, return mock data
        return {
            'timestamp': datetime.utcnow(),
            'cpu_utilization': 50.0,  # Mock data
            'memory_utilization': 60.0,  # Mock data
            'avg_response_time': 150.0,  # Mock data
            'active_connections': 25,  # Mock data
            'request_rate': 100.0  # Mock data
        }
    
    async def _scale_up(self):
        """Scale up the number of instances."""
        new_instance_count = min(self.max_instances, self.current_instances + 1)
        
        if new_instance_count > self.current_instances:
            logger.info("Scaling up", 
                       current=self.current_instances,
                       new=new_instance_count)
            
            if self.scale_up_callback:
                try:
                    await self.scale_up_callback(new_instance_count)
                    self.current_instances = new_instance_count
                    self.last_scale_action = datetime.utcnow()
                except Exception as e:
                    logger.error("Scale up callback failed", error=str(e))
    
    async def _scale_down(self):
        """Scale down the number of instances."""
        new_instance_count = max(self.min_instances, self.current_instances - 1)
        
        if new_instance_count < self.current_instances:
            logger.info("Scaling down", 
                       current=self.current_instances,
                       new=new_instance_count)
            
            if self.scale_down_callback:
                try:
                    await self.scale_down_callback(new_instance_count)
                    self.current_instances = new_instance_count
                    self.last_scale_action = datetime.utcnow()
                except Exception as e:
                    logger.error("Scale down callback failed", error=str(e))
    
    def get_scaling_stats(self) -> Dict[str, Any]:
        """Get auto-scaling statistics."""
        return {
            "current_instances": self.current_instances,
            "min_instances": self.min_instances,
            "max_instances": self.max_instances,
            "last_scale_action": self.last_scale_action.isoformat(),
            "metrics_history_size": len(self.metrics_history),
            "target_cpu_utilization": self.target_cpu_utilization,
            "target_memory_utilization": self.target_memory_utilization,
            "scale_up_threshold": self.scale_up_threshold,
            "scale_down_threshold": self.scale_down_threshold
        }


class LoadBalancedService:
    """Service that combines load balancing and auto-scaling."""
    
    def __init__(
        self,
        service_name: str,
        load_balancer: LoadBalancer,
        auto_scaler: Optional[AutoScaler] = None
    ):
        self.service_name = service_name
        self.load_balancer = load_balancer
        self.auto_scaler = auto_scaler
        
        # Set up auto-scaler callbacks if provided
        if self.auto_scaler:
            self.auto_scaler.set_scale_callbacks(
                self._handle_scale_up,
                self._handle_scale_down
            )
    
    async def start(self):
        """Start the load-balanced service."""
        await self.load_balancer.start_health_checks()
        
        if self.auto_scaler:
            await self.auto_scaler.start_auto_scaling()
        
        logger.info("Load-balanced service started", service_name=self.service_name)
    
    async def stop(self):
        """Stop the load-balanced service."""
        await self.load_balancer.stop_health_checks()
        
        if self.auto_scaler:
            await self.auto_scaler.stop_auto_scaling()
        
        logger.info("Load-balanced service stopped", service_name=self.service_name)
    
    async def execute_request(self, request_func: Callable, *args, **kwargs) -> Any:
        """Execute a request using load balancing."""
        endpoint = self.load_balancer.get_next_endpoint()
        if not endpoint:
            raise RuntimeError("No healthy endpoints available")
        
        start_time = time.time()
        await self.load_balancer.record_request_start(endpoint.id)
        
        try:
            # Execute the request
            result = await request_func(endpoint, *args, **kwargs)
            
            response_time = (time.time() - start_time) * 1000
            await self.load_balancer.record_request_end(
                endpoint.id, response_time, success=True
            )
            
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            await self.load_balancer.record_request_end(
                endpoint.id, response_time, success=False
            )
            raise
    
    async def _handle_scale_up(self, new_instance_count: int):
        """Handle scale up action."""
        # This would typically create new service instances
        logger.info("Handling scale up", 
                   service=self.service_name,
                   new_count=new_instance_count)
        
        # Add logic to create new endpoints
        # For example, start new containers or VMs
    
    async def _handle_scale_down(self, new_instance_count: int):
        """Handle scale down action."""
        # This would typically remove service instances
        logger.info("Handling scale down", 
                   service=self.service_name,
                   new_count=new_instance_count)
        
        # Add logic to remove endpoints
        # For example, stop containers or VMs
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        stats = {
            "service_name": self.service_name,
            "load_balancer": self.load_balancer.get_stats()
        }
        
        if self.auto_scaler:
            stats["auto_scaler"] = self.auto_scaler.get_scaling_stats()
        
        return stats