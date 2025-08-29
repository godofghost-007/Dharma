"""Service routing and circuit breaker implementation."""

import asyncio
from typing import Dict, Any, Optional
from enum import Enum
import httpx
from fastapi import HTTPException, status, Request
import structlog
from datetime import datetime, timedelta

from ..core.config import settings

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for service calls."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and \
               datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        
        # HALF_OPEN state
        return True
    
    def record_success(self):
        """Record successful request."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


class ServiceRouter:
    """Routes requests to appropriate microservices."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.service_urls = {
            "data-collection": settings.service_data_collection_url,
            "ai-analysis": settings.service_ai_analysis_url,
            "alert-management": settings.service_alert_management_url,
            "dashboard": settings.service_dashboard_url,
        }
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]
    
    def get_service_from_path(self, path: str) -> Optional[str]:
        """Determine target service from request path."""
        path_parts = path.strip("/").split("/")
        
        if len(path_parts) < 2:
            return None
        
        # API versioning: /api/v1/service/...
        if path_parts[0] == "api" and path_parts[1].startswith("v"):
            if len(path_parts) < 3:
                return None
            service_path = path_parts[2]
        else:
            service_path = path_parts[0]
        
        # Map path segments to services
        service_mapping = {
            "collect": "data-collection",
            "data": "data-collection",
            "analyze": "ai-analysis",
            "ai": "ai-analysis",
            "sentiment": "ai-analysis",
            "bot": "ai-analysis",
            "campaign": "ai-analysis",
            "alerts": "alert-management",
            "notifications": "alert-management",
            "dashboard": "dashboard",
            "reports": "dashboard",
            "analytics": "dashboard"
        }
        
        return service_mapping.get(service_path)
    
    async def route_request(
        self,
        request: Request,
        service_name: str,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Route request to target service with circuit breaker."""
        
        circuit_breaker = self.get_circuit_breaker(service_name)
        
        if not circuit_breaker.can_execute():
            logger.warning(
                "Circuit breaker open for service",
                service=service_name,
                state=circuit_breaker.state.value
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} is temporarily unavailable"
            )
        
        service_url = self.service_urls.get(service_name)
        if not service_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service {service_name} not found"
            )
        
        # Construct target URL
        target_url = f"{service_url.rstrip('/')}/{path.lstrip('/')}"
        
        try:
            # Prepare request
            request_kwargs = {
                "method": method,
                "url": target_url,
                "headers": headers,
                "params": params
            }
            
            if body:
                request_kwargs["content"] = body
            
            # Make request
            logger.info(
                "Routing request to service",
                service=service_name,
                method=method,
                path=path,
                target_url=target_url
            )
            
            response = await self.client.request(**request_kwargs)
            
            # Record success
            circuit_breaker.record_success()
            
            # Return response data
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.content,
                "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
            }
            
        except httpx.TimeoutException:
            circuit_breaker.record_failure()
            logger.error("Service request timeout", service=service_name, path=path)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Service {service_name} request timeout"
            )
        
        except httpx.ConnectError:
            circuit_breaker.record_failure()
            logger.error("Service connection error", service=service_name, path=path)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} is unavailable"
            )
        
        except Exception as e:
            circuit_breaker.record_failure()
            logger.error("Service request error", service=service_name, path=path, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error communicating with service {service_name}"
            )
    
    async def health_check_service(self, service_name: str) -> bool:
        """Check if service is healthy."""
        service_url = self.service_urls.get(service_name)
        if not service_url:
            return False
        
        try:
            health_url = f"{service_url.rstrip('/')}/health"
            response = await self.client.get(
                health_url,
                timeout=settings.service_health_check_timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning("Service health check failed", service=service_name, error=str(e))
            return False
    
    async def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services."""
        status_info = {}
        
        for service_name in self.service_urls.keys():
            circuit_breaker = self.get_circuit_breaker(service_name)
            is_healthy = await self.health_check_service(service_name)
            
            status_info[service_name] = {
                "healthy": is_healthy,
                "circuit_breaker_state": circuit_breaker.state.value,
                "failure_count": circuit_breaker.failure_count,
                "last_failure": circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None
            }
        
        return status_info
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global service router instance
service_router = ServiceRouter()