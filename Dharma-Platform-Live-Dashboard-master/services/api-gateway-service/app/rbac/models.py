"""RBAC models for roles and permissions."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class Permission(str, Enum):
    """System permissions."""
    
    # User management
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"
    
    # Alert management
    ALERTS_READ = "alerts:read"
    ALERTS_WRITE = "alerts:write"
    ALERTS_DELETE = "alerts:delete"
    
    # Campaign management
    CAMPAIGNS_READ = "campaigns:read"
    CAMPAIGNS_WRITE = "campaigns:write"
    CAMPAIGNS_DELETE = "campaigns:delete"
    
    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_WRITE = "analytics:write"
    
    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    
    # Data collection
    DATA_COLLECT = "data:collect"
    DATA_READ = "data:read"
    
    # AI analysis
    AI_ANALYZE = "ai:analyze"
    AI_MODELS = "ai:models"


class Role(str, Enum):
    """System roles."""
    
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    ANALYST = "analyst"
    VIEWER = "viewer"


class RolePermissions(BaseModel):
    """Role with its permissions."""
    
    role: Role
    permissions: List[Permission]
    description: str


class UserRole(BaseModel):
    """User role assignment."""
    
    user_id: int
    role: Role
    assigned_by: int
    assigned_at: str
    expires_at: Optional[str] = None


class PermissionCheck(BaseModel):
    """Permission check request."""
    
    user_id: int
    permission: Permission
    resource_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PermissionResult(BaseModel):
    """Permission check result."""
    
    allowed: bool
    reason: str
    user_role: Role
    required_permissions: List[Permission]


class AuditLogEntry(BaseModel):
    """Audit log entry for RBAC actions."""
    
    id: Optional[int] = None
    user_id: int
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[str] = None
    success: bool = True


class RoleUpdateRequest(BaseModel):
    """Request to update user role."""
    
    user_id: int
    new_role: Role
    reason: str


class PermissionUpdateRequest(BaseModel):
    """Request to update user permissions."""
    
    user_id: int
    permissions: List[Permission]
    reason: str


# Default role permissions mapping
DEFAULT_ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.USERS_READ, Permission.USERS_WRITE, Permission.USERS_DELETE,
        Permission.ALERTS_READ, Permission.ALERTS_WRITE, Permission.ALERTS_DELETE,
        Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_WRITE, Permission.CAMPAIGNS_DELETE,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_WRITE,
        Permission.SYSTEM_ADMIN, Permission.SYSTEM_CONFIG,
        Permission.DATA_COLLECT, Permission.DATA_READ,
        Permission.AI_ANALYZE, Permission.AI_MODELS
    ],
    Role.SUPERVISOR: [
        Permission.USERS_READ, Permission.USERS_WRITE,
        Permission.ALERTS_READ, Permission.ALERTS_WRITE,
        Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_WRITE,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_WRITE,
        Permission.DATA_READ,
        Permission.AI_ANALYZE
    ],
    Role.ANALYST: [
        Permission.ALERTS_READ, Permission.ALERTS_WRITE,
        Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_WRITE,
        Permission.ANALYTICS_READ,
        Permission.DATA_READ,
        Permission.AI_ANALYZE
    ],
    Role.VIEWER: [
        Permission.ALERTS_READ,
        Permission.CAMPAIGNS_READ,
        Permission.ANALYTICS_READ,
        Permission.DATA_READ
    ]
}