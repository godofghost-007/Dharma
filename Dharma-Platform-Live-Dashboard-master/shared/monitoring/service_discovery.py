"""
Service discovery system for Project Dharma
Provides service registration, discovery, and load balancing
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import aioredis
import aiohttp
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """Service instance information"""
    service_name: str
    instance_id: str
    host: str
    port: int
    protocol: str = "http"
    version: str = "1.0.0"
    status: ServiceStatus = ServiceStatus.HEALTHY
    metadata: Dict[str, Any] = None
    health_check_url: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    registration_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.registration_time is None:
            self.registration_time = datetime.utcnow()
        if self.health_check_url is None:
            self.health_check_url = f"{self.protocol}://{self.host}:{self.port}/health"
    
    @property
    def base_url(self) -> str:
        """Get base URL for the service instance"""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if service instance is healthy"""
        if self.status != ServiceStatus.HEALTHY:
            return False
        
        if self.last_heartbeat is None:
            return False
        
        # Consider unhealthy if no heartbeat in last 60 seconds
        return datetime.utcnow() - self.last_heartbeat < timedelta(seconds=60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        if self.last_heartbeat:
            result['last_heartbeat'] = self.last_heartbeat.isoformat()
        if self.registration_time:
            result['registration_time'] = self.registration_time.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceInstance':
        """Create instance from dictionary"""
        if 'status' in data:
            data['status'] = ServiceStatus(data['status'])
        if 'last_heartbeat' in data and data['last_heartbeat']:
            data['last_heartbeat'] = datetime.fromisoformat(data['last_heartbeat'])
        if 'registration_time' in data and data['registration_time']:
            data['registration_time'] = datetime.fromisoformat(data['registration_time'])
        return cls(**data)


class LoadBalancingStrategy(Enum):
    """Load balancing strategy enumeration"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"


class ServiceRegistry:
    """Service registry for managing service instances"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.services: Dict[str, Dict[str, ServiceInstance]] = {}
        self.heartbeat_interval = 30  # seconds
        self.cleanup_interval = 60  # seconds
        self.running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the service registry"""
        self.redis_client = aioredis.from_url(self.redis_url)
        await self._load_services_from_redis()
        logger.info("Service registry initialized")
    
    async def close(self):
        """Close the service registry"""
        if self.running:
            await self.stop()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Service registry closed")
    
    async def register_service(self, service: ServiceInstance) -> bool:
        """Register a service instance"""
        try:
            # Store in memory
            if service.service_name not in self.services:
                self.services[service.service_name] = {}
            
            service.registration_time = datetime.utcnow()
            service.last_heartbeat = datetime.utcnow()
            self.services[service.service_name][service.instance_id] = service
            
            # Store in Redis
            await self._store_service_in_redis(service)
            
            logger.info(f"Registered service: {service.service_name}/{service.instance_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register service {service.service_name}/{service.instance_id}: {e}")
            return False
    
    async def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance"""
        try:
            # Remove from memory
            if service_name in self.services and instance_id in self.services[service_name]:
                del self.services[service_name][instance_id]
                
                if not self.services[service_name]:
                    del self.services[service_name]
            
            # Remove from Redis
            await self._remove_service_from_redis(service_name, instance_id)
            
            logger.info(f"Deregistered service: {service_name}/{instance_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to deregister service {service_name}/{instance_id}: {e}")
            return False
    
    async def update_service_status(self, service_name: str, instance_id: str, status: ServiceStatus) -> bool:
        """Update service instance status"""
        try:
            if service_name in self.services and instance_id in self.services[service_name]:
                service = self.services[service_name][instance_id]
                service.status = status
                service.last_heartbeat = datetime.utcnow()
                
                # Update in Redis
                await self._store_service_in_redis(service)
                
                logger.debug(f"Updated service status: {service_name}/{instance_id} -> {status.value}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to update service status {service_name}/{instance_id}: {e}")
            return False
    
    async def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Send heartbeat for a service instance"""
        return await self.update_service_status(service_name, instance_id, ServiceStatus.HEALTHY)
    
    def get_service_instances(self, service_name: str, healthy_only: bool = True) -> List[ServiceInstance]:
        """Get all instances of a service"""
        if service_name not in self.services:
            return []
        
        instances = list(self.services[service_name].values())
        
        if healthy_only:
            instances = [instance for instance in instances if instance.is_healthy]
        
        return instances
    
    def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services"""
        result = {}
        for service_name, instances in self.services.items():
            result[service_name] = list(instances.values())
        return result
    
    async def discover_service(self, service_name: str, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN) -> Optional[ServiceInstance]:
        """Discover a service instance using load balancing"""
        instances = self.get_service_instances(service_name, healthy_only=True)
        
        if not instances:
            return None
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(service_name, instances)
        elif strategy == LoadBalancingStrategy.RANDOM:
            return self._random_select(instances)
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(instances)
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(instances)
        else:
            return instances[0]  # Default to first instance
    
    def _round_robin_select(self, service_name: str, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round-robin load balancing"""
        # Simple round-robin based on instance count
        if not hasattr(self, '_round_robin_counters'):
            self._round_robin_counters = {}
        
        if service_name not in self._round_robin_counters:
            self._round_robin_counters[service_name] = 0
        
        index = self._round_robin_counters[service_name] % len(instances)
        self._round_robin_counters[service_name] += 1
        
        return instances[index]
    
    def _random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Random load balancing"""
        import random
        return random.choice(instances)
    
    def _least_connections_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Least connections load balancing (simplified)"""
        # For now, just return the first instance
        # In a real implementation, you'd track active connections
        return instances[0]
    
    def _weighted_round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted round-robin load balancing"""
        # For now, treat all instances equally
        # In a real implementation, you'd use weights from metadata
        return self._round_robin_select("weighted", instances)
    
    async def start(self):
        """Start background tasks"""
        if self.running:
            return
        
        self.running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Service registry background tasks started")
    
    async def stop(self):
        """Stop background tasks"""
        if not self.running:
            return
        
        self.running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Service registry background tasks stopped")
    
    async def _cleanup_loop(self):
        """Background task to cleanup stale services"""
        while self.running:
            try:
                await self._cleanup_stale_services()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_stale_services(self):
        """Remove stale service instances"""
        current_time = datetime.utcnow()
        stale_threshold = timedelta(seconds=120)  # 2 minutes
        
        services_to_remove = []
        
        for service_name, instances in self.services.items():
            instances_to_remove = []
            
            for instance_id, instance in instances.items():
                if (instance.last_heartbeat and 
                    current_time - instance.last_heartbeat > stale_threshold):
                    instances_to_remove.append(instance_id)
            
            for instance_id in instances_to_remove:
                await self.deregister_service(service_name, instance_id)
                logger.info(f"Removed stale service: {service_name}/{instance_id}")
    
    async def _store_service_in_redis(self, service: ServiceInstance):
        """Store service instance in Redis"""
        if not self.redis_client:
            return
        
        key = f"services:{service.service_name}:{service.instance_id}"
        value = json.dumps(service.to_dict())
        
        await self.redis_client.set(key, value, ex=300)  # 5 minute expiry
    
    async def _remove_service_from_redis(self, service_name: str, instance_id: str):
        """Remove service instance from Redis"""
        if not self.redis_client:
            return
        
        key = f"services:{service_name}:{instance_id}"
        await self.redis_client.delete(key)
    
    async def _load_services_from_redis(self):
        """Load services from Redis on startup"""
        if not self.redis_client:
            return
        
        try:
            keys = await self.redis_client.keys("services:*")
            
            for key in keys:
                value = await self.redis_client.get(key)
                if value:
                    service_data = json.loads(value)
                    service = ServiceInstance.from_dict(service_data)
                    
                    if service.service_name not in self.services:
                        self.services[service.service_name] = {}
                    
                    self.services[service.service_name][service.instance_id] = service
            
            logger.info(f"Loaded {len(keys)} services from Redis")
        
        except Exception as e:
            logger.error(f"Failed to load services from Redis: {e}")


class ServiceClient:
    """HTTP client with service discovery integration"""
    
    def __init__(self, service_registry: ServiceRegistry, timeout: float = 30.0):
        self.service_registry = service_registry
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def request(self, method: str, service_name: str, path: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request to a service using service discovery"""
        instance = await self.service_registry.discover_service(service_name)
        
        if not instance:
            raise Exception(f"No healthy instances found for service: {service_name}")
        
        url = urljoin(instance.base_url, path)
        
        if not self.session:
            raise Exception("ServiceClient not initialized. Use as async context manager.")
        
        return await self.session.request(method, url, **kwargs)
    
    async def get(self, service_name: str, path: str, **kwargs) -> aiohttp.ClientResponse:
        """GET request to service"""
        return await self.request("GET", service_name, path, **kwargs)
    
    async def post(self, service_name: str, path: str, **kwargs) -> aiohttp.ClientResponse:
        """POST request to service"""
        return await self.request("POST", service_name, path, **kwargs)
    
    async def put(self, service_name: str, path: str, **kwargs) -> aiohttp.ClientResponse:
        """PUT request to service"""
        return await self.request("PUT", service_name, path, **kwargs)
    
    async def delete(self, service_name: str, path: str, **kwargs) -> aiohttp.ClientResponse:
        """DELETE request to service"""
        return await self.request("DELETE", service_name, path, **kwargs)


class ServiceAgent:
    """Service agent for automatic registration and heartbeat"""
    
    def __init__(self, service_registry: ServiceRegistry, service_instance: ServiceInstance):
        self.service_registry = service_registry
        self.service_instance = service_instance
        self.running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self.heartbeat_interval = 30  # seconds
    
    async def start(self):
        """Start the service agent"""
        if self.running:
            return
        
        # Register the service
        success = await self.service_registry.register_service(self.service_instance)
        if not success:
            raise Exception(f"Failed to register service: {self.service_instance.service_name}")
        
        # Start heartbeat
        self.running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"Service agent started for {self.service_instance.service_name}/{self.service_instance.instance_id}")
    
    async def stop(self):
        """Stop the service agent"""
        if not self.running:
            return
        
        self.running = False
        
        # Stop heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Deregister the service
        await self.service_registry.deregister_service(
            self.service_instance.service_name,
            self.service_instance.instance_id
        )
        
        logger.info(f"Service agent stopped for {self.service_instance.service_name}/{self.service_instance.instance_id}")
    
    async def _heartbeat_loop(self):
        """Background heartbeat loop"""
        while self.running:
            try:
                await self.service_registry.heartbeat(
                    self.service_instance.service_name,
                    self.service_instance.instance_id
                )
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None


def get_service_registry(redis_url: str = "redis://localhost:6379") -> ServiceRegistry:
    """Get global service registry instance"""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry(redis_url)
    return _service_registry


async def setup_service_discovery(service_name: str, host: str, port: int, 
                                 redis_url: str = "redis://localhost:6379",
                                 **kwargs) -> ServiceAgent:
    """Setup service discovery for a service"""
    # Create service registry
    registry = get_service_registry(redis_url)
    await registry.initialize()
    await registry.start()
    
    # Create service instance
    instance = ServiceInstance(
        service_name=service_name,
        instance_id=f"{service_name}-{host}-{port}",
        host=host,
        port=port,
        **kwargs
    )
    
    # Create and start service agent
    agent = ServiceAgent(registry, instance)
    await agent.start()
    
    return agent