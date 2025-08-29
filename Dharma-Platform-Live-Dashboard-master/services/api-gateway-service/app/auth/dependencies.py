"""Authentication dependencies for FastAPI."""

from typing import List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from .service import auth_service
from .models import CurrentUser
from ..rbac.models import Permission
from ..rbac.service import rbac_service

logger = structlog.get_logger()

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """Get current authenticated user."""
    try:
        token = credentials.credentials
        user = await auth_service.get_current_user(token)
        return user
    except Exception as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permissions(required_permissions: List[str]):
    """Dependency factory for permission-based access control."""
    
    async def permission_checker(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user)
    ):
        """Check if user has required permissions."""
        user_permissions = set(current_user.permissions)
        required_perms = set(required_permissions)
        
        # Admin role has all permissions
        if current_user.role == "admin":
            # Log successful access
            await rbac_service.log_audit_event(
                user_id=current_user.id,
                action="access_granted",
                resource_type="endpoint",
                resource_id=request.url.path,
                details={"reason": "admin_role", "required_permissions": required_permissions},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=True
            )
            return current_user
        
        # Check if user has all required permissions
        if not required_perms.issubset(user_permissions):
            missing_perms = required_perms - user_permissions
            
            # Log access denied
            await rbac_service.log_audit_event(
                user_id=current_user.id,
                action="access_denied",
                resource_type="endpoint",
                resource_id=request.url.path,
                details={
                    "reason": "insufficient_permissions",
                    "required_permissions": required_permissions,
                    "user_permissions": list(user_permissions),
                    "missing_permissions": list(missing_perms)
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=False
            )
            
            logger.warning(
                "Access denied: insufficient permissions",
                user=current_user.username,
                required=list(required_perms),
                missing=list(missing_perms)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Missing: {', '.join(missing_perms)}"
            )
        
        # Log successful access
        await rbac_service.log_audit_event(
            user_id=current_user.id,
            action="access_granted",
            resource_type="endpoint",
            resource_id=request.url.path,
            details={"required_permissions": required_permissions},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        return current_user
    
    return permission_checker


def require_role(required_roles: List[str]):
    """Dependency factory for role-based access control."""
    
    async def role_checker(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user)
    ):
        """Check if user has required role."""
        if current_user.role not in required_roles:
            # Log access denied
            await rbac_service.log_audit_event(
                user_id=current_user.id,
                action="access_denied",
                resource_type="endpoint",
                resource_id=request.url.path,
                details={
                    "reason": "insufficient_role",
                    "user_role": current_user.role,
                    "required_roles": required_roles
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=False
            )
            
            logger.warning(
                "Access denied: insufficient role",
                user=current_user.username,
                user_role=current_user.role,
                required_roles=required_roles
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        
        # Log successful access
        await rbac_service.log_audit_event(
            user_id=current_user.id,
            action="access_granted",
            resource_type="endpoint",
            resource_id=request.url.path,
            details={"required_roles": required_roles, "user_role": current_user.role},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        return current_user
    
    return role_checker


# Common permission dependencies
require_admin = require_role(["admin"])
require_supervisor_or_admin = require_role(["supervisor", "admin"])
require_analyst_or_above = require_role(["analyst", "supervisor", "admin"])

# Permission-based dependencies
require_user_management = require_permissions(["users:write"])
require_alert_management = require_permissions(["alerts:write"])
require_campaign_management = require_permissions(["campaigns:write"])
require_analytics_access = require_permissions(["analytics:read"])