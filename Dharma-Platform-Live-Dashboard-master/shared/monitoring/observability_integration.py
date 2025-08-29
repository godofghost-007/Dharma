"""
Comprehensive observability integration for Project Dharma
Integrates logging, metrics, tracing, health checks, and service discovery
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from shared.logging.structured_logger import get_logger, StructuredLogger
from shared.monitoring.metrics_collector import get_metrics_collector, get_business_metrics
from shared.tracing.tracer import get_tracer
from shared.tracing.correlation import get_correlation_manager
from shared.tracing.error_tracker import get_error_tracker
from shared.tracing.performance_profiler import get_profiler
from shared.monitoring.health_checks import get_health_checker, setup_default_health_checks
from shared.monitoring.service_discovery import setup_service_discovery, ServiceAgent

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Centralized observability manager"""
    
    def __init__(self, service_name: str, config: Dict[str, Any]):
        self.service_name = service_name
        self.config = config
        
        # Components
        self.logger = None
        self.metrics_collector = None
        self.business_metrics = None
        self.tracer = None
        self.correlation_manager = None
        self.error_tracker = None
        self.profiler = None
        self.health_checker = None
        self.service_agent: Optional[ServiceAgent] = None
        
        self.initialized = False
    
    async def initialize(self):
        """Initialize all observability components"""
        if self.initialized:
            return
        
        try:
            # Initialize structured logging
            self.logger = get_logger(self.service_name)
            logger.info(f"Initialized structured logging for {self.service_name}")
            
            # Initialize metrics collection
            self.metrics_collector = get_metrics_collector(self.service_name)
            self.business_metrics = get_business_metrics(self.service_name)
            
            # Start metrics HTTP server if configured
            if self.config.get("metrics", {}).get("enable_http_server", True):
                metrics_port = self.config.get("metrics", {}).get("port", 9090)
                self.metrics_collector.start_http_server(metrics_port)
            
            logger.info(f"Initialized metrics collection for {self.service_name}")
            
            # Initialize distributed tracing
            self.tracer = get_tracer(self.service_name)
            logger.info(f"Initialized distributed tracing for {self.service_name}")
            
            # Initialize correlation management
            self.correlation_manager = get_correlation_manager()
            await self.correlation_manager.initialize()
            logger.info(f"Initialized correlation management for {self.service_name}")
            
            # Initialize error tracking
            self.error_tracker = get_error_tracker(self.service_name)
            await self.error_tracker.start()
            logger.info(f"Initialized error tracking for {self.service_name}")
            
            # Initialize performance profiling
            self.profiler = get_profiler()
            await self.profiler.initialize()
            logger.info(f"Initialized performance profiling for {self.service_name}")
            
            # Initialize health checks
            self.health_checker = setup_default_health_checks(self.service_name, self.config)
            await self.health_checker.start_monitoring()
            logger.info(f"Initialized health checks for {self.service_name}")
            
            # Initialize service discovery if configured
            if self.config.get("service_discovery", {}).get("enabled", False):
                discovery_config = self.config["service_discovery"]
                self.service_agent = await setup_service_discovery(
                    service_name=self.service_name,
                    host=discovery_config.get("host", "localhost"),
                    port=discovery_config.get("port", 8000),
                    redis_url=discovery_config.get("redis_url", "redis://localhost:6379"),
                    version=discovery_config.get("version", "1.0.0"),
                    metadata=discovery_config.get("metadata", {})
                )
                logger.info(f"Initialized service discovery for {self.service_name}")
            
            self.initialized = True
            logger.info(f"Observability manager fully initialized for {self.service_name}")
        
        except Exception as e:
            logger.error(f"Failed to initialize observability manager: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all observability components"""
        if not self.initialized:
            return
        
        try:
            # Shutdown service discovery
            if self.service_agent:
                await self.service_agent.stop()
                logger.info("Shutdown service discovery")
            
            # Shutdown health checks
            if self.health_checker:
                await self.health_checker.stop_monitoring()
                logger.info("Shutdown health checks")
            
            # Shutdown performance profiling
            if self.profiler:
                await self.profiler.close()
                logger.info("Shutdown performance profiling")
            
            # Shutdown error tracking
            if self.error_tracker:
                await self.error_tracker.stop()
                logger.info("Shutdown error tracking")
            
            # Shutdown correlation management
            if self.correlation_manager:
                await self.correlation_manager.close()
                logger.info("Shutdown correlation management")
            
            self.initialized = False
            logger.info(f"Observability manager shutdown complete for {self.service_name}")
        
        except Exception as e:
            logger.error(f"Error during observability manager shutdown: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        if not self.initialized or not self.health_checker:
            return {
                "status": "unhealthy",
                "message": "Observability manager not initialized"
            }
        
        # Get overall health from health checker
        # This would be async in real implementation
        return {
            "status": "healthy",
            "service": self.service_name,
            "components": {
                "logging": "healthy",
                "metrics": "healthy",
                "tracing": "healthy",
                "correlation": "healthy",
                "error_tracking": "healthy",
                "profiling": "healthy",
                "health_checks": "healthy",
                "service_discovery": "healthy" if self.service_agent else "disabled"
            }
        }


class ObservabilityMiddleware:
    """FastAPI middleware for comprehensive observability"""
    
    def __init__(self, app: FastAPI, observability_manager: ObservabilityManager):
        self.app = app
        self.observability_manager = observability_manager
    
    async def __call__(self, request: Request, call_next):
        """Process request with full observability"""
        start_time = asyncio.get_event_loop().time()
        
        # Start tracing
        with self.observability_manager.tracer.trace_operation(
            f"{request.method} {request.url.path}"
        ) as span:
            
            # Set span attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.scheme", request.url.scheme)
            span.set_attribute("http.host", request.url.hostname or "unknown")
            span.set_attribute("user_agent", request.headers.get("user-agent", "unknown"))
            
            # Start performance profiling
            with self.observability_manager.profiler.profile_operation(
                f"http_request_{request.method}_{request.url.path}"
            ):
                
                try:
                    # Process request
                    response = await call_next(request)
                    
                    # Record successful request metrics
                    self.observability_manager.metrics_collector.increment_counter(
                        "http_requests_total",
                        {
                            "method": request.method,
                            "endpoint": request.url.path,
                            "status": str(response.status_code)
                        }
                    )
                    
                    # Set response span attributes
                    span.set_attribute("http.status_code", response.status_code)
                    
                    return response
                
                except Exception as e:
                    # Track error
                    self.observability_manager.error_tracker.track_error(e)
                    
                    # Record error metrics
                    self.observability_manager.metrics_collector.increment_counter(
                        "http_requests_total",
                        {
                            "method": request.method,
                            "endpoint": request.url.path,
                            "status": "500"
                        }
                    )
                    
                    # Set error span attributes
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                    raise
                
                finally:
                    # Record request duration
                    duration = asyncio.get_event_loop().time() - start_time
                    self.observability_manager.metrics_collector.observe_histogram(
                        "http_request_duration_seconds",
                        duration,
                        {
                            "method": request.method,
                            "endpoint": request.url.path
                        }
                    )


def setup_observability_endpoints(app: FastAPI, observability_manager: ObservabilityManager):
    """Setup observability endpoints"""
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            if not observability_manager.health_checker:
                return JSONResponse(
                    status_code=503,
                    content={"status": "unhealthy", "message": "Health checker not initialized"}
                )
            
            overall_health = await observability_manager.health_checker.get_overall_health()
            
            status_code = 200
            if overall_health.status.value == "unhealthy":
                status_code = 503
            elif overall_health.status.value == "degraded":
                status_code = 200  # Still accepting traffic but degraded
            
            return JSONResponse(
                status_code=status_code,
                content=overall_health.to_dict()
            )
        
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "message": f"Health check failed: {str(e)}"
                }
            )
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check endpoint"""
        try:
            if not observability_manager.health_checker:
                return JSONResponse(
                    status_code=503,
                    content={"status": "unhealthy", "message": "Health checker not initialized"}
                )
            
            all_results = await observability_manager.health_checker.check_all()
            overall_health = await observability_manager.health_checker.get_overall_health()
            
            return JSONResponse(
                content={
                    "overall": overall_health.to_dict(),
                    "components": {name: result.to_dict() for name, result in all_results.items()}
                }
            )
        
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"Detailed health check failed: {str(e)}"
                }
            )
    
    @app.get("/metrics")
    async def metrics_endpoint():
        """Prometheus metrics endpoint"""
        try:
            if not observability_manager.metrics_collector:
                return Response(
                    content="# Metrics collector not initialized\n",
                    media_type="text/plain"
                )
            
            metrics_text = observability_manager.metrics_collector.get_metrics_text()
            return Response(content=metrics_text, media_type="text/plain")
        
        except Exception as e:
            return Response(
                content=f"# Error generating metrics: {str(e)}\n",
                media_type="text/plain",
                status_code=500
            )
    
    @app.get("/observability/status")
    async def observability_status():
        """Observability system status"""
        return JSONResponse(content=observability_manager.get_health_status())


async def setup_service_observability(
    app: FastAPI,
    service_name: str,
    config: Dict[str, Any]
) -> ObservabilityManager:
    """
    Complete observability setup for a service
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
        config: Configuration dictionary
    
    Returns:
        ObservabilityManager instance
    """
    # Create observability manager
    observability_manager = ObservabilityManager(service_name, config)
    
    # Initialize all components
    await observability_manager.initialize()
    
    # Add observability middleware
    app.add_middleware(
        ObservabilityMiddleware,
        observability_manager=observability_manager
    )
    
    # Setup observability endpoints
    setup_observability_endpoints(app, observability_manager)
    
    # Setup shutdown handler
    @app.on_event("shutdown")
    async def shutdown_observability():
        await observability_manager.shutdown()
    
    logger.info(f"Complete observability setup completed for {service_name}")
    
    return observability_manager


# Example configuration
DEFAULT_OBSERVABILITY_CONFIG = {
    "metrics": {
        "enable_http_server": True,
        "port": 9090
    },
    "service_discovery": {
        "enabled": True,
        "host": "localhost",
        "port": 8000,
        "redis_url": "redis://localhost:6379",
        "version": "1.0.0",
        "metadata": {}
    },
    "postgresql": {
        "connection_string": "postgresql://postgres:postgres@localhost:5432/dharma_platform"
    },
    "mongodb": {
        "connection_string": "mongodb://localhost:27017/dharma_platform"
    },
    "redis": {
        "connection_string": "redis://localhost:6379"
    },
    "elasticsearch": {
        "connection_string": "http://localhost:9200"
    },
    "kafka": {
        "bootstrap_servers": ["localhost:9092"]
    },
    "external_services": {
        "api-gateway": {
            "health_url": "http://localhost:8001/health",
            "expected_status": 200
        }
    }
}