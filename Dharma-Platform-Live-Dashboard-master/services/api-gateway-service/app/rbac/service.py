"""RBAC service for role and permission management."""

from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

from ..core.database import db_manager
from ..auth.models import CurrentUser
from .models import (
    Role, Permission, PermissionCheck, PermissionResult, 
    AuditLogEntry, DEFAULT_ROLE_PERMISSIONS
)

logger = structlog.get_logger()


class RBACService:
    """Role-based access control service."""
    
    def __init__(self):
        self.db = db_manager
    
    async def check_permission(
        self, 
        user: CurrentUser, 
        required_permission: Permission,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PermissionResult:
        """Check if user has required permission."""
        
        # Admin role has all permissions
        if user.role == Role.ADMIN.value:
            await self.log_audit_event(
                user_id=user.id,
                action="permission_check",
                resource_type="permission",
                resource_id=required_permission.value,
                details={"result": "allowed", "reason": "admin_role"},
                success=True
            )
            return PermissionResult(
                allowed=True,
                reason="Admin role has all permissions",
                user_role=Role.ADMIN,
                required_permissions=[required_permission]
            )
        
        # Check if user has the specific permission
        user_permissions = set(user.permissions)
        has_permission = required_permission.value in user_permissions
        
        result = PermissionResult(
            allowed=has_permission,
            reason="Permission granted" if has_permission else f"Missing permission: {required_permission.value}",
            user_role=Role(user.role),
            required_permissions=[required_permission]
        )
        
        # Log audit event
        await self.log_audit_event(
            user_id=user.id,
            action="permission_check",
            resource_type="permission",
            resource_id=required_permission.value,
            details={
                "result": "allowed" if has_permission else "denied",
                "user_permissions": list(user_permissions),
                "resource_id": resource_id,
                "context": context
            },
            success=has_permission
        )
        
        return result
    
    async def check_multiple_permissions(
        self,
        user: CurrentUser,
        required_permissions: List[Permission],
        require_all: bool = True
    ) -> PermissionResult:
        """Check if user has multiple permissions."""
        
        # Admin role has all permissions
        if user.role == Role.ADMIN.value:
            return PermissionResult(
                allowed=True,
                reason="Admin role has all permissions",
                user_role=Role.ADMIN,
                required_permissions=required_permissions
            )
        
        user_permissions = set(user.permissions)
        required_perms = set(perm.value for perm in required_permissions)
        
        if require_all:
            has_permissions = required_perms.issubset(user_permissions)
            missing_perms = required_perms - user_permissions
            reason = "All permissions granted" if has_permissions else f"Missing permissions: {', '.join(missing_perms)}"
        else:
            has_permissions = bool(required_perms.intersection(user_permissions))
            reason = "At least one permission granted" if has_permissions else "No required permissions found"
        
        # Log audit event
        await self.log_audit_event(
            user_id=user.id,
            action="multiple_permission_check",
            resource_type="permissions",
            details={
                "result": "allowed" if has_permissions else "denied",
                "required_permissions": list(required_perms),
                "user_permissions": list(user_permissions),
                "require_all": require_all
            },
            success=has_permissions
        )
        
        return PermissionResult(
            allowed=has_permissions,
            reason=reason,
            user_role=Role(user.role),
            required_permissions=required_permissions
        )
    
    async def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for a user."""
        async with self.db.get_pg_connection() as conn:
            query = """
                SELECT role, permissions 
                FROM users 
                WHERE id = $1 AND is_active = true
            """
            row = await conn.fetchrow(query, user_id)
            if not row:
                return []
            
            # Get base permissions for role
            role = Role(row["role"])
            base_permissions = DEFAULT_ROLE_PERMISSIONS.get(role, [])
            base_perms = [perm.value for perm in base_permissions]
            
            # Add additional permissions
            additional_permissions = row["permissions"] or []
            
            # Combine and deduplicate
            all_permissions = list(set(base_perms + additional_permissions))
            
            return all_permissions
    
    async def update_user_role(
        self, 
        user_id: int, 
        new_role: Role, 
        updated_by: int,
        reason: str
    ) -> bool:
        """Update user role."""
        try:
            async with self.db.get_pg_connection() as conn:
                # Get current role for audit
                current_role = await conn.fetchval(
                    "SELECT role FROM users WHERE id = $1", user_id
                )
                
                # Update role
                await conn.execute(
                    "UPDATE users SET role = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    new_role.value, user_id
                )
                
                # Log audit event
                await self.log_audit_event(
                    user_id=updated_by,
                    action="role_update",
                    resource_type="user",
                    resource_id=str(user_id),
                    details={
                        "old_role": current_role,
                        "new_role": new_role.value,
                        "reason": reason
                    },
                    success=True
                )
                
                logger.info(
                    "User role updated",
                    user_id=user_id,
                    old_role=current_role,
                    new_role=new_role.value,
                    updated_by=updated_by
                )
                
                return True
                
        except Exception as e:
            logger.error("Failed to update user role", user_id=user_id, error=str(e))
            await self.log_audit_event(
                user_id=updated_by,
                action="role_update",
                resource_type="user",
                resource_id=str(user_id),
                details={"error": str(e), "new_role": new_role.value, "reason": reason},
                success=False
            )
            return False
    
    async def update_user_permissions(
        self,
        user_id: int,
        additional_permissions: List[Permission],
        updated_by: int,
        reason: str
    ) -> bool:
        """Update user's additional permissions."""
        try:
            async with self.db.get_pg_connection() as conn:
                # Get current permissions for audit
                current_perms = await conn.fetchval(
                    "SELECT permissions FROM users WHERE id = $1", user_id
                )
                
                # Update permissions
                new_perms = [perm.value for perm in additional_permissions]
                await conn.execute(
                    "UPDATE users SET permissions = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    new_perms, user_id
                )
                
                # Log audit event
                await self.log_audit_event(
                    user_id=updated_by,
                    action="permissions_update",
                    resource_type="user",
                    resource_id=str(user_id),
                    details={
                        "old_permissions": current_perms or [],
                        "new_permissions": new_perms,
                        "reason": reason
                    },
                    success=True
                )
                
                logger.info(
                    "User permissions updated",
                    user_id=user_id,
                    new_permissions=new_perms,
                    updated_by=updated_by
                )
                
                return True
                
        except Exception as e:
            logger.error("Failed to update user permissions", user_id=user_id, error=str(e))
            await self.log_audit_event(
                user_id=updated_by,
                action="permissions_update",
                resource_type="user",
                resource_id=str(user_id),
                details={"error": str(e), "reason": reason},
                success=False
            )
            return False
    
    async def log_audit_event(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True
    ) -> bool:
        """Log audit event."""
        try:
            async with self.db.get_pg_connection() as conn:
                query = """
                    INSERT INTO audit_logs 
                    (user_id, action, resource_type, resource_id, details, 
                     ip_address, user_agent, success, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
                """
                await conn.execute(
                    query,
                    user_id, action, resource_type, resource_id,
                    details, ip_address, user_agent, success
                )
                return True
                
        except Exception as e:
            logger.error("Failed to log audit event", error=str(e))
            return False
    
    async def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogEntry]:
        """Get audit logs with filtering."""
        try:
            async with self.db.get_pg_connection() as conn:
                conditions = []
                params = []
                param_count = 0
                
                if user_id:
                    param_count += 1
                    conditions.append(f"user_id = ${param_count}")
                    params.append(user_id)
                
                if action:
                    param_count += 1
                    conditions.append(f"action = ${param_count}")
                    params.append(action)
                
                if resource_type:
                    param_count += 1
                    conditions.append(f"resource_type = ${param_count}")
                    params.append(resource_type)
                
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                
                query = f"""
                    SELECT id, user_id, action, resource_type, resource_id, 
                           details, ip_address, user_agent, timestamp, success
                    FROM audit_logs 
                    {where_clause}
                    ORDER BY timestamp DESC 
                    LIMIT ${param_count + 1} OFFSET ${param_count + 2}
                """
                params.extend([limit, offset])
                
                rows = await conn.fetch(query, *params)
                
                return [
                    AuditLogEntry(
                        id=row["id"],
                        user_id=row["user_id"],
                        action=row["action"],
                        resource_type=row["resource_type"],
                        resource_id=row["resource_id"],
                        details=row["details"],
                        ip_address=row["ip_address"],
                        user_agent=row["user_agent"],
                        timestamp=row["timestamp"].isoformat() if hasattr(row["timestamp"], 'isoformat') else str(row["timestamp"]) if row["timestamp"] else None,
                        success=row["success"]
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error("Failed to get audit logs", error=str(e))
            return []
    
    async def get_role_permissions(self, role: Role) -> List[Permission]:
        """Get permissions for a role."""
        return DEFAULT_ROLE_PERMISSIONS.get(role, [])
    
    async def get_all_roles(self) -> List[Dict[str, Any]]:
        """Get all available roles with their permissions."""
        roles = []
        for role, permissions in DEFAULT_ROLE_PERMISSIONS.items():
            roles.append({
                "role": role.value,
                "permissions": [perm.value for perm in permissions],
                "permission_count": len(permissions)
            })
        return roles


# Global RBAC service instance
rbac_service = RBACService()