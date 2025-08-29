"""Rate limiting middleware using slowapi and Redis."""

from typing import Optional
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as redis
import structlog

from ..core.config import settings
from ..auth.dependencies import get_current_user

logger = structlog.get_logger()


def get_user_id_or_ip(request: Request) -> str:
    """Get user ID for authenticated requests, IP for anonymous."""
    try:
        # Try to get user from token if present
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # This is a simplified approach - in production you'd want to
            # properly decode the token to get user info
            token = auth_header.split(" ")[1]
            # For now, use token hash as identifier
            import hashlib
            return f"user:{hashlib.md5(token.encode()).hexdigest()[:8]}"
    except Exception:
        pass
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_rate_limit_for_user(request: Request) -> str:
    """Get rate limit based on user role."""
    try:
        # Try to extract role from request context
        # This would be set by authentication middleware
        user_role = getattr(request.state, 'user_role', None)
        
        if user_role == "admin":
            return settings.rate_limit_admin_rate_limit
        elif user_role == "supervisor":
            return settings.rate_limit_admin_rate_limit  # Same as admin
        elif user_role == "analyst":
            return settings.rate_limit_analyst_rate_limit
        elif user_role == "viewer":
            return settings.rate_limit_viewer_rate_limit
        
    except Exception:
        pass
    
    # Default rate limit for unauthenticated users
    return settings.rate_limit_default_rate_limit


# Create Redis connection for rate limiting
redis_client = redis.from_url(settings.rate_limit_redis_url, decode_responses=True)

# Create limiter instance
limiter = Limiter(
    key_func=get_user_id_or_ip,
    storage_uri=settings.rate_limit_redis_url,
    default_limits=[settings.rate_limit_default_rate_limit]
)


class RateLimitMiddleware:
    """Custom rate limiting middleware with role-based limits."""
    
    def __init__(self):
        self.redis_client = redis_client
    
    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""
        try:
            # Get user identifier
            user_key = get_user_id_or_ip(request)
            
            # Get appropriate rate limit
            rate_limit = get_rate_limit_for_user(request)
            
            # Check rate limit
            if await self.is_rate_limited(user_key, rate_limit):
                logger.warning(
                    "Rate limit exceeded",
                    user_key=user_key,
                    rate_limit=rate_limit,
                    path=request.url.path
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": "60"}
                )
            
            # Process request
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Rate limiting error", error=str(e))
            # Don't block requests if rate limiting fails
            return await call_next(request)
    
    async def is_rate_limited(self, user_key: str, rate_limit: str) -> bool:
        """Check if user is rate limited."""
        try:
            # Parse rate limit (e.g., "100/minute")
            limit_parts = rate_limit.split("/")
            if len(limit_parts) != 2:
                return False
            
            max_requests = int(limit_parts[0])
            time_window = limit_parts[1]
            
            # Convert time window to seconds
            window_seconds = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400
            }.get(time_window, 60)
            
            # Use sliding window rate limiting
            redis_key = f"rate_limit:{user_key}:{time_window}"
            
            # Get current count
            current_count = await self.redis_client.get(redis_key)
            current_count = int(current_count) if current_count else 0
            
            if current_count >= max_requests:
                return True
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds)
            await pipe.execute()
            
            return False
            
        except Exception as e:
            logger.error("Rate limit check error", error=str(e))
            return False


# Global rate limit middleware instance
rate_limit_middleware = RateLimitMiddleware()