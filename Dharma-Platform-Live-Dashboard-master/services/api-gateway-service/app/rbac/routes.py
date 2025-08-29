"""RBAC management routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
import structlog

from ..auth.dependencies import get_current_user, require_admin, require_supervisor_or_admin
from ..auth.models import CurrentUser
from .models import (
    Role, Permission, RoleUpdateRequest, PermissionUpdateRequest,
    AuditLogEntry, PermissionCheck, PermissionResult
)
from .service import rbac_service

logger = structlog.get_logger()
router = APIRouter(prefix="/rbac", tags=["Role-Based Access Control"])


@router.get("/roles", response_model=List[dict])
async def get_all_roles(current_user: CurrentUser = Depends(require_supervisor_or_admin)):
    """Get all available roles and their permissions."""
    try:
        roles = await rbac_service.get_all_roles()
        logger.info("Roles retrieved", requested_by=current_user.username)
        return roles
    except Exception as e:
        logger.error("Failed to get roles", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve roles"
        )


@router.get("/permissions", response_model=List[str])
async def get_all_permissions(current_user: CurrentUser = Depends(require_supervisor_or_admin)):
    """Get all available permissions."""
    try:
        permissions = [perm.value for perm in Permission]
        logger.info("Permissions retrieved", requested_by=current_user.username)
        return permissions
    except Exception as e:
        logger.error("Failed to get permissions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permissions"
        )


@router.get("/users/{user_id}/permissions", response_model=List[str])
async def get_user_permissions(
    user_id: int,
    current_user: CurrentUser = Depends(require_supervisor_or_admin)
):
    """Get permissions for a specific user."""
    try:
        permissions = await rbac_service.get_user_permissions(user_id)
        logger.info("User permissions retrieved", user_id=user_id, requested_by=current_user.username)
        return permissions
    except Exception as e:
        logger.error("Failed to get user permissions", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user permissions"
        )


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: RoleUpdateRequest,
    current_user: CurrentUser = Depends(require_admin)
):
    """Update user role (admin only)."""
    try:
        success = await rbac_service.update_user_role(
            user_id=user_id,
            new_role=role_update.new_role,
            updated_by=current_user.id,
            reason=role_update.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user role"
            )
        
        logger.info(
            "User role updated",
            user_id=user_id,
            new_role=role_update.new_role.value,
            updated_by=current_user.username
        )
        
        return {"message": "User role updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update user role", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/users/{user_id}/permissions")
async def update_user_permissions(
    user_id: int,
    permission_update: PermissionUpdateRequest,
    current_user: CurrentUser = Depends(require_admin)
):
    """Update user additional permissions (admin only)."""
    try:
        success = await rbac_service.update_user_permissions(
            user_id=user_id,
            additional_permissions=permission_update.permissions,
            updated_by=current_user.id,
            reason=permission_update.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user permissions"
            )
        
        logger.info(
            "User permissions updated",
            user_id=user_id,
            permissions=[p.value for p in permission_update.permissions],
            updated_by=current_user.username
        )
        
        return {"message": "User permissions updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update user permissions", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/check-permission", response_model=PermissionResult)
async def check_permission(
    permission_check: PermissionCheck,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Check if current user has specific permission."""
    try:
        # Only allow users to check their own permissions unless they're admin/supervisor
        if (permission_check.user_id != current_user.id and 
            current_user.role not in ["admin", "supervisor"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only check your own permissions"
            )
        
        # For checking other users, use the target user's info
        if permission_check.user_id != current_user.id:
            # This would require getting the target user's info from database
            # For now, we'll just check the current user's permissions
            pass
        
        result = await rbac_service.check_permission(
            user=current_user,
            required_permission=permission_check.permission,
            resource_id=permission_check.resource_id,
            context=permission_check.context
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check permission", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/audit-logs", response_model=List[AuditLogEntry])
async def get_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(require_supervisor_or_admin)
):
    """Get audit logs (supervisor/admin only)."""
    try:
        # Limit regular supervisors to their own audit logs
        if current_user.role == "supervisor" and user_id is None:
            user_id = current_user.id
        
        logs = await rbac_service.get_audit_logs(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            limit=min(limit, 1000),  # Cap at 1000
            offset=offset
        )
        
        logger.info(
            "Audit logs retrieved",
            requested_by=current_user.username,
            filters={"user_id": user_id, "action": action, "resource_type": resource_type}
        )
        
        return logs
        
    except Exception as e:
        logger.error("Failed to get audit logs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )


@router.get("/my-permissions", response_model=List[str])
async def get_my_permissions(current_user: CurrentUser = Depends(get_current_user)):
    """Get current user's permissions."""
    return current_user.permissions


@router.get("/my-role", response_model=dict)
async def get_my_role(current_user: CurrentUser = Depends(get_current_user)):
    """Get current user's role information."""
    try:
        role_permissions = await rbac_service.get_role_permissions(Role(current_user.role))
        
        return {
            "role": current_user.role,
            "permissions": current_user.permissions,
            "role_permissions": [perm.value for perm in role_permissions],
            "additional_permissions": list(
                set(current_user.permissions) - 
                set(perm.value for perm in role_permissions)
            )
        }
        
    except Exception as e:
        logger.error("Failed to get role info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve role information"
        )