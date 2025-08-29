"""Main FastAPI application for API Gateway."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import structlog

from app.core.config import settings
from app.core.database import db_manager
from app.auth.routes import router as auth_router
from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser
from app.middleware.rate_limiting import limiter, RateLimitExceeded
from app.routing.service_router import service_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting API Gateway service")
    
    try:
        # Initialize database connections
        await db_manager.initialize()
        logger.info("Database connections initialized")
        
        # Initialize service router
        logger.info("Service router initialized")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down API Gateway service")
        
        # Close database connections
        await db_manager.close()
        
        # Close service router
        await service_router.close()
        
        logger.info("API Gateway service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API Gateway for Project Dharma - Social Media Intelligence Platform",
    docs_url=None,  # We'll create custom docs
    redoc_url=None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Add rate limiting
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded exceptions."""
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )
    response = request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)
    return response


# Include authentication routes
app.include_router(auth_router)

# Include RBAC routes
from app.rbac.routes import router as rbac_router
app.include_router(rbac_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": settings.version
    }


@app.get("/status")
async def system_status(current_user: CurrentUser = Depends(get_current_user)):
    """Get system status (authenticated users only)."""
    service_status = await service_router.get_service_status()
    
    return {
        "gateway": {
            "status": "healthy",
            "version": settings.version
        },
        "services": service_status
    }


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI with authentication."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.app_name} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.version,
        description="""
        # Project Dharma API Gateway
        
        This is the main API gateway for Project Dharma, a comprehensive AI-powered 
        social media monitoring platform designed to detect, analyze, and track 
        coordinated disinformation campaigns.
        
        ## Authentication
        
        Most endpoints require authentication using JWT tokens. To authenticate:
        
        1. Use the `/auth/login` endpoint with your credentials
        2. Include the returned `access_token` in the Authorization header: `Bearer <token>`
        
        ## Rate Limiting
        
        API requests are rate limited based on user role:
        - Admin/Supervisor: 1000 requests/minute
        - Analyst: 500 requests/minute  
        - Viewer: 100 requests/minute
        - Unauthenticated: 100 requests/minute
        
        ## Services
        
        The gateway routes requests to the following microservices:
        - Data Collection Service: `/api/v1/collect/*`, `/api/v1/data/*`
        - AI Analysis Service: `/api/v1/analyze/*`, `/api/v1/ai/*`
        - Alert Management Service: `/api/v1/alerts/*`, `/api/v1/notifications/*`
        - Dashboard Service: `/api/v1/dashboard/*`, `/api/v1/reports/*`
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Add security to all endpoints except auth
    for path, path_item in openapi_schema["paths"].items():
        if not path.startswith("/auth"):
            for operation in path_item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit("100/minute")
async def proxy_to_service(
    request: Request,
    path: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Proxy requests to appropriate microservices."""
    
    # Determine target service
    service_name = service_router.get_service_from_path(path)
    if not service_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Get request details
    method = request.method
    headers = dict(request.headers)
    params = dict(request.query_params)
    
    # Add user context to headers
    headers["X-User-ID"] = str(current_user.id)
    headers["X-User-Role"] = current_user.role
    headers["X-User-Permissions"] = ",".join(current_user.permissions)
    
    # Get request body
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    try:
        # Route request to service
        response_data = await service_router.route_request(
            request=request,
            service_name=service_name,
            path=path,
            method=method,
            headers=headers,
            body=body,
            params=params
        )
        
        # Return response
        if response_data["json"]:
            return JSONResponse(
                content=response_data["json"],
                status_code=response_data["status_code"],
                headers=dict(response_data["headers"])
            )
        else:
            return JSONResponse(
                content={"data": response_data["content"].decode() if response_data["content"] else None},
                status_code=response_data["status_code"],
                headers=dict(response_data["headers"])
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Proxy request error", path=path, service=service_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal gateway error"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None  # Use structlog instead
    )