"""
Shared workspace management for analyst teams
"""

import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)

class WorkspaceType(Enum):
    """Types of shared workspaces"""
    INVESTIGATION = "investigation"
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    TRAINING = "training"
    TEMPLATE = "template"

class AccessLevel(Enum):
    """Access levels for workspace members"""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    GUEST = "guest"

@dataclass
class WorkspaceMember:
    """Workspace member information"""
    user_id: str
    username: str
    email: str
    access_level: AccessLevel
    joined_at: datetime
    last_active: Optional[datetime] = None
    permissions: Set[str] = field(default_factory=set)

@dataclass
class WorkspaceSettings:
    """Workspace configuration settings"""
    auto_save_interval: int = 300  # seconds
    max_concurrent_editors: int = 10
    enable_real_time_sync: bool = True
    enable_version_history: bool = True
    retention_days: int = 90
    notification_settings: Dict[str, bool] = field(default_factory=lambda: {
        'member_joined': True,
        'content_updated': True,
        'comment_added': True,
        'status_changed': True
    })

@dataclass
class SharedWorkspace:
    """Shared workspace for collaborative analysis"""
    workspace_id: str
    name: str
    description: str
    workspace_type: WorkspaceType
    owner_id: str
    created_at: datetime
    updated_at: datetime
    
    # Members and access control
    members: Dict[str, WorkspaceMember] = field(default_factory=dict)
    settings: WorkspaceSettings = field(default_factory=WorkspaceSettings)
    
    # Content and state
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    # Status tracking
    is_active: bool = True
    is_archived: bool = False
    last_activity: Optional[datetime] = None

class WorkspaceManager:
    """Manages shared workspaces for analyst teams"""
    
    def __init__(self, storage_backend=None):
        """Initialize workspace manager"""
        self.storage_backend = storage_backend
        self.workspaces: Dict[str, SharedWorkspace] = {}
        self.user_workspaces: Dict[str, Set[str]] = {}  # user_id -> workspace_ids
        
        # Permission definitions
        self.permissions = {
            AccessLevel.OWNER: {
                'read', 'write', 'delete', 'manage_members', 'manage_settings',
                'archive', 'export', 'share', 'create_templates'
            },
            AccessLevel.ADMIN: {
                'read', 'write', 'manage_members', 'manage_settings',
                'export', 'share'
            },
            AccessLevel.EDITOR: {
                'read', 'write', 'export', 'comment'
            },
            AccessLevel.VIEWER: {
                'read', 'comment'
            },
            AccessLevel.GUEST: {
                'read'
            }
        }
    
    async def create_workspace(
        self,
        name: str,
        description: str,
        workspace_type: WorkspaceType,
        owner_id: str,
        owner_username: str,
        owner_email: str,
        template_id: Optional[str] = None
    ) -> SharedWorkspace:
        """Create a new shared workspace"""
        
        workspace_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create owner member
        owner_member = WorkspaceMember(
            user_id=owner_id,
            username=owner_username,
            email=owner_email,
            access_level=AccessLevel.OWNER,
            joined_at=now,
            last_active=now,
            permissions=self.permissions[AccessLevel.OWNER]
        )
        
        # Initialize workspace
        workspace = SharedWorkspace(
            workspace_id=workspace_id,
            name=name,
            description=description,
            workspace_type=workspace_type,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
            members={owner_id: owner_member},
            last_activity=now
        )
        
        # Apply template if specified
        if template_id:
            await self._apply_template(workspace, template_id)
        
        # Store workspace
        self.workspaces[workspace_id] = workspace
        
        # Update user workspace mapping
        if owner_id not in self.user_workspaces:
            self.user_workspaces[owner_id] = set()
        self.user_workspaces[owner_id].add(workspace_id)
        
        # Persist to storage
        if self.storage_backend:
            await self.storage_backend.save_workspace(workspace)
        
        logger.info(f"Created workspace {workspace_id}: {name}")
        return workspace
    
    async def add_member(
        self,
        workspace_id: str,
        user_id: str,
        username: str,
        email: str,
        access_level: AccessLevel,
        added_by: str
    ) -> bool:
        """Add a member to workspace"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        # Check permissions
        if not await self._check_permission(workspace_id, added_by, 'manage_members'):
            raise PermissionError("Insufficient permissions to add members")
        
        # Check if user already exists
        if user_id in workspace.members:
            logger.warning(f"User {user_id} already in workspace {workspace_id}")
            return False
        
        # Create member
        member = WorkspaceMember(
            user_id=user_id,
            username=username,
            email=email,
            access_level=access_level,
            joined_at=datetime.utcnow(),
            permissions=self.permissions[access_level]
        )
        
        # Add to workspace
        workspace.members[user_id] = member
        workspace.updated_at = datetime.utcnow()
        workspace.last_activity = datetime.utcnow()
        
        # Update user workspace mapping
        if user_id not in self.user_workspaces:
            self.user_workspaces[user_id] = set()
        self.user_workspaces[user_id].add(workspace_id)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_workspace(workspace)
        
        logger.info(f"Added user {user_id} to workspace {workspace_id}")
        return True
    
    async def remove_member(
        self,
        workspace_id: str,
        user_id: str,
        removed_by: str
    ) -> bool:
        """Remove a member from workspace"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        # Check permissions
        if not await self._check_permission(workspace_id, removed_by, 'manage_members'):
            raise PermissionError("Insufficient permissions to remove members")
        
        # Cannot remove owner
        if user_id == workspace.owner_id:
            raise ValueError("Cannot remove workspace owner")
        
        # Remove member
        if user_id in workspace.members:
            del workspace.members[user_id]
            workspace.updated_at = datetime.utcnow()
            
            # Update user workspace mapping
            if user_id in self.user_workspaces:
                self.user_workspaces[user_id].discard(workspace_id)
            
            # Persist changes
            if self.storage_backend:
                await self.storage_backend.save_workspace(workspace)
            
            logger.info(f"Removed user {user_id} from workspace {workspace_id}")
            return True
        
        return False
    
    async def update_member_access(
        self,
        workspace_id: str,
        user_id: str,
        new_access_level: AccessLevel,
        updated_by: str
    ) -> bool:
        """Update member access level"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        # Check permissions
        if not await self._check_permission(workspace_id, updated_by, 'manage_members'):
            raise PermissionError("Insufficient permissions to update member access")
        
        # Cannot change owner access
        if user_id == workspace.owner_id:
            raise ValueError("Cannot change owner access level")
        
        # Update member
        if user_id in workspace.members:
            member = workspace.members[user_id]
            member.access_level = new_access_level
            member.permissions = self.permissions[new_access_level]
            workspace.updated_at = datetime.utcnow()
            
            # Persist changes
            if self.storage_backend:
                await self.storage_backend.save_workspace(workspace)
            
            logger.info(f"Updated access for user {user_id} in workspace {workspace_id}")
            return True
        
        return False
    
    async def get_user_workspaces(
        self,
        user_id: str,
        workspace_type: Optional[WorkspaceType] = None,
        include_archived: bool = False
    ) -> List[SharedWorkspace]:
        """Get workspaces for a user"""
        
        workspace_ids = self.user_workspaces.get(user_id, set())
        workspaces = []
        
        for workspace_id in workspace_ids:
            workspace = self.workspaces.get(workspace_id)
            if not workspace:
                continue
            
            # Filter by type
            if workspace_type and workspace.workspace_type != workspace_type:
                continue
            
            # Filter archived
            if not include_archived and workspace.is_archived:
                continue
            
            workspaces.append(workspace)
        
        # Sort by last activity
        workspaces.sort(key=lambda w: w.last_activity or w.created_at, reverse=True)
        return workspaces
    
    async def get_workspace(self, workspace_id: str, user_id: str) -> Optional[SharedWorkspace]:
        """Get workspace if user has access"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            return None
        
        # Check if user is member
        if user_id not in workspace.members:
            return None
        
        return workspace
    
    async def update_workspace_content(
        self,
        workspace_id: str,
        user_id: str,
        content_updates: Dict[str, Any]
    ) -> bool:
        """Update workspace content"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        # Check permissions
        if not await self._check_permission(workspace_id, user_id, 'write'):
            raise PermissionError("Insufficient permissions to update content")
        
        # Update content
        workspace.content.update(content_updates)
        workspace.updated_at = datetime.utcnow()
        workspace.last_activity = datetime.utcnow()
        
        # Update member last active
        if user_id in workspace.members:
            workspace.members[user_id].last_active = datetime.utcnow()
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_workspace(workspace)
        
        return True
    
    async def create_template(
        self,
        workspace_id: str,
        template_name: str,
        template_description: str,
        created_by: str
    ) -> str:
        """Create a template from existing workspace"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        # Check permissions
        if not await self._check_permission(workspace_id, created_by, 'create_templates'):
            raise PermissionError("Insufficient permissions to create templates")
        
        # Create template workspace
        template = await self.create_workspace(
            name=template_name,
            description=template_description,
            workspace_type=WorkspaceType.TEMPLATE,
            owner_id=created_by,
            owner_username=workspace.members[created_by].username,
            owner_email=workspace.members[created_by].email
        )
        
        # Copy content (excluding member-specific data)
        template.content = workspace.content.copy()
        template.settings = workspace.settings
        template.tags = workspace.tags.copy()
        
        # Mark as template
        template.metadata['is_template'] = True
        template.metadata['source_workspace'] = workspace_id
        
        # Persist template
        if self.storage_backend:
            await self.storage_backend.save_workspace(template)
        
        logger.info(f"Created template {template.workspace_id} from workspace {workspace_id}")
        return template.workspace_id
    
    async def archive_workspace(
        self,
        workspace_id: str,
        archived_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """Archive a workspace"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        # Check permissions
        if not await self._check_permission(workspace_id, archived_by, 'archive'):
            raise PermissionError("Insufficient permissions to archive workspace")
        
        # Archive workspace
        workspace.is_archived = True
        workspace.is_active = False
        workspace.updated_at = datetime.utcnow()
        workspace.metadata['archived_by'] = archived_by
        workspace.metadata['archived_at'] = datetime.utcnow().isoformat()
        if reason:
            workspace.metadata['archive_reason'] = reason
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_workspace(workspace)
        
        logger.info(f"Archived workspace {workspace_id}")
        return True
    
    async def get_workspace_activity(
        self,
        workspace_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent activity in workspace"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        # Check permissions
        if not await self._check_permission(workspace_id, user_id, 'read'):
            raise PermissionError("Insufficient permissions to view activity")
        
        # Get activity from storage backend
        if self.storage_backend:
            return await self.storage_backend.get_workspace_activity(workspace_id, limit)
        
        return []
    
    async def _check_permission(
        self,
        workspace_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if user has permission in workspace"""
        
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            return False
        
        member = workspace.members.get(user_id)
        if not member:
            return False
        
        return permission in member.permissions
    
    async def _apply_template(self, workspace: SharedWorkspace, template_id: str):
        """Apply template to workspace"""
        
        template = self.workspaces.get(template_id)
        if not template or template.workspace_type != WorkspaceType.TEMPLATE:
            logger.warning(f"Template {template_id} not found or invalid")
            return
        
        # Copy template content
        workspace.content = template.content.copy()
        workspace.settings = template.settings
        workspace.tags = template.tags.copy()
        
        # Add template metadata
        workspace.metadata['template_id'] = template_id
        workspace.metadata['template_applied_at'] = datetime.utcnow().isoformat()
    
    def get_workspace_stats(self) -> Dict[str, Any]:
        """Get workspace statistics"""
        
        total_workspaces = len(self.workspaces)
        active_workspaces = sum(1 for w in self.workspaces.values() if w.is_active)
        archived_workspaces = sum(1 for w in self.workspaces.values() if w.is_archived)
        
        # Count by type
        type_counts = {}
        for workspace in self.workspaces.values():
            workspace_type = workspace.workspace_type.value
            type_counts[workspace_type] = type_counts.get(workspace_type, 0) + 1
        
        # Total members across all workspaces
        total_members = sum(len(w.members) for w in self.workspaces.values())
        
        return {
            'total_workspaces': total_workspaces,
            'active_workspaces': active_workspaces,
            'archived_workspaces': archived_workspaces,
            'workspaces_by_type': type_counts,
            'total_members': total_members,
            'unique_users': len(self.user_workspaces)
        }