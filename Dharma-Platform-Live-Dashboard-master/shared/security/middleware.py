"""
Security middleware for FastAPI applications
Provides authentication, validation, and security headers
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from .config import get_security_config

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for FastAPI applications"""
    
    def __init__(self, app, security_config=None):
        """
        Initialize security middleware
        
        Args:
            app: FastAPI application instance
            security_config: Optional security configuration
        """
        super().__init__(app)
        self.security_config = security_config or get_security_config()
        self.rate_limiter = RateLimiter()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware"""
        start_time = time.time()
        
        try:
            # Apply rate limiting
            if not await self.rate_limiter.check_rate_limit(request):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Validate request size
            if hasattr(request, 'body'):
                body = await request.body()
                max_size = self.security_config.config['validation']['max_request_size']
                if len(body) > max_size:
                    raise HTTPException(status_code=413, detail="Request too large")
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            security_headers = self.security_config.get_security_headers()
            for header, value in security_headers.items():
                response.headers[header] = value
            
            # Log request
            process_time = time.time() - start_time
            logger.info(
                f"Request processed: {request.method} {request.url.path} "
                f"- {response.status_code} - {process_time:.3f}s"
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            raise HTTPException(status_code=500, detail="Internal security error")


class APIKeyAuthenticator:
    """API key authentication handler"""
    
    def __init__(self, security_config=None):
        self.security_config = security_config or get_security_config()
        self.api_key_manager = self.security_config.get_api_key_manager()
    
    async def authenticate_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Authenticate API key and return user context
        
        Args:
            api_key: API key to authenticate
            
        Returns:
            Dictionary with authentication result and user context
        """
        try:
            validation_result = self.api_key_manager.validate_api_key(api_key)
            
            if not validation_result['valid']:
                return {
                    'authenticated': False,
                    'reason': validation_result['reason']
                }
            
            return {
                'authenticated': True,
                'service_name': validation_result['service_name'],
                'key_type': validation_result['key_type'],
                'usage_count': validation_result['usage_count']
            }
            
        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return {
                'authenticated': False,
                'reason': 'Authentication error'
            }


class InputValidationMiddleware:
    """Middleware for input validation and sanitization"""
    
    def __init__(self, security_config=None):
        self.security_config = security_config or get_security_config()
        self.input_validator = self.security_config.get_input_validator()
        self.data_sanitizer = self.security_config.get_data_sanitizer()
    
    async def validate_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize request data
        
        Args:
            request_data: Raw request data
            
        Returns:
            Validation results and sanitized data
        """
        return self.security_config.validate_and_sanitize_request(request_data)


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis
        self.window_size = 60  # 1 minute window
        self.max_requests = 1000  # Max requests per window
    
    async def check_rate_limit(self, request: Request) -> bool:
        """
        Check if request is within rate limits
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if within limits, False otherwise
        """
        # Get client identifier
        client_ip = request.client.host
        api_key = request.headers.get('X-API-Key')
        identifier = api_key if api_key else client_ip
        
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > window_start
            ]
        else:
            self.requests[identifier] = []
        
        # Check rate limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True


# FastAPI dependencies
security_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = security_scheme):
    """FastAPI dependency for API key authentication"""
    authenticator = APIKeyAuthenticator()
    
    auth_result = await authenticator.authenticate_api_key(credentials.credentials)
    
    if not auth_result['authenticated']:
        raise HTTPException(
            status_code=401,
            detail=auth_result['reason'],
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return auth_result


async def validate_request_json(request: Request) -> Dict[str, Any]:
    """FastAPI dependency for request validation"""
    try:
        request_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    validator = InputValidationMiddleware()
    validation_result = await validator.validate_request_data(request_data)
    
    if not validation_result['valid']:
        raise HTTPException(
            status_code=400,
            detail={
                'errors': validation_result['errors'],
                'security_warnings': validation_result['security_warnings']
            }
        )
    
    return validation_result['sanitized_data']