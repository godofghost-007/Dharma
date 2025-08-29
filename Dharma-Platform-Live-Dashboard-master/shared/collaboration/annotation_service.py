"""
Collaborative annotation service for content analysis
"""

import logging
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)

class AnnotationType(Enum):
    """Types of annotations"""
    COMMENT = "comment"
    HIGHLIGHT = "highlight"
    TAG = "tag"
    CLASSIFICATION = "classification"
    LINK = "link"
    THREAT_LEVEL = "threat_level"
    SENTIMENT_OVERRIDE = "sentiment_override"
    BOT_INDICATOR = "bot_indicator"

class AnnotationStatus(Enum):
    """Status of annotations"""
    DRAFT = "draft"
    PUBLISHED = "published"
    RESOLVED = "resolved"
    DISPUTED = "disputed"
    ARCHIVED = "archived"

@dataclass
class AnnotationPosition:
    """Position information for annotations"""
    start_offset: int
    end_offset: int
    selected_text: Optional[str] = None
    context: Optional[str] = None

@dataclass
class AnnotationMetadata:
    """Metadata for annotations"""
    confidence: Optional[float] = None
    source: Optional[str] = None
    model_version: Optional[str] = None
    validation_status: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CollaborativeAnnotation:
    """Collaborative annotation on content"""
    annotation_id: str
    content_id: str  # ID of the content being annotated
    workspace_id: str
    annotation_type: AnnotationType
    value: Any  # The annotation value (text, classification, etc.)
    created_by: str
    created_at: datetime
    
    # Optional fields with defaults
    position: Optional[AnnotationPosition] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    status: AnnotationStatus = AnnotationStatus.DRAFT
    assigned_to: Optional[str] = None
    metadata: AnnotationMetadata = field(default_factory=AnnotationMetadata)
    replies: List[str] = field(default_factory=list)  # Reply annotation IDs
    parent_id: Optional[str] = None  # For threaded discussions
    mentions: Set[str] = field(default_factory=set)  # Mentioned user IDs
    votes: Dict[str, str] = field(default_factory=dict)  # user_id -> vote (agree/disagree)
    consensus_score: float = 0.0

class AnnotationService:
    """Service for managing collaborative annotations"""
    
    def __init__(self, storage_backend=None, workspace_manager=None):
        """Initialize annotation service"""
        self.storage_backend = storage_backend
        self.workspace_manager = workspace_manager
        self.annotations: Dict[str, CollaborativeAnnotation] = {}
        self.content_annotations: Dict[str, List[str]] = {}  # content_id -> annotation_ids
        self.user_annotations: Dict[str, List[str]] = {}  # user_id -> annotation_ids
    
    async def create_annotation(
        self,
        content_id: str,
        workspace_id: str,
        annotation_type: AnnotationType,
        value: Any,
        created_by: str,
        position: Optional[AnnotationPosition] = None,
        metadata: Optional[AnnotationMetadata] = None,
        assigned_to: Optional[str] = None
    ) -> CollaborativeAnnotation:
        """Create a new annotation"""
        
        # Verify workspace access
        if self.workspace_manager:
            workspace = await self.workspace_manager.get_workspace(workspace_id, created_by)
            if not workspace:
                raise PermissionError("No access to workspace")
            
            # Check write permissions
            if not await self.workspace_manager._check_permission(workspace_id, created_by, 'write'):
                raise PermissionError("Insufficient permissions to create annotations")
        
        annotation_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        annotation = CollaborativeAnnotation(
            annotation_id=annotation_id,
            content_id=content_id,
            workspace_id=workspace_id,
            annotation_type=annotation_type,
            value=value,
            position=position,
            created_by=created_by,
            created_at=now,
            assigned_to=assigned_to,
            metadata=metadata or AnnotationMetadata()
        )
        
        # Store annotation
        self.annotations[annotation_id] = annotation
        
        # Update indexes
        if content_id not in self.content_annotations:
            self.content_annotations[content_id] = []
        self.content_annotations[content_id].append(annotation_id)
        
        if created_by not in self.user_annotations:
            self.user_annotations[created_by] = []
        self.user_annotations[created_by].append(annotation_id)
        
        # Persist to storage
        if self.storage_backend:
            await self.storage_backend.save_annotation(annotation)
        
        logger.info(f"Created annotation {annotation_id} on content {content_id}")
        return annotation
    
    async def update_annotation(
        self,
        annotation_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an existing annotation"""
        
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            raise ValueError(f"Annotation {annotation_id} not found")
        
        # Check permissions
        if not await self._check_annotation_permission(annotation, user_id, 'write'):
            raise PermissionError("Insufficient permissions to update annotation")
        
        # Apply updates
        for field, value in updates.items():
            if hasattr(annotation, field):
                setattr(annotation, field, value)
        
        annotation.updated_by = user_id
        annotation.updated_at = datetime.utcnow()
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_annotation(annotation)
        
        logger.info(f"Updated annotation {annotation_id}")
        return True
    
    async def add_reply(
        self,
        parent_annotation_id: str,
        reply_content: str,
        user_id: str,
        annotation_type: AnnotationType = AnnotationType.COMMENT
    ) -> CollaborativeAnnotation:
        """Add a reply to an annotation"""
        
        parent_annotation = self.annotations.get(parent_annotation_id)
        if not parent_annotation:
            raise ValueError(f"Parent annotation {parent_annotation_id} not found")
        
        # Create reply annotation
        reply = await self.create_annotation(
            content_id=parent_annotation.content_id,
            workspace_id=parent_annotation.workspace_id,
            annotation_type=annotation_type,
            value=reply_content,
            created_by=user_id
        )
        
        # Link to parent
        reply.parent_id = parent_annotation_id
        parent_annotation.replies.append(reply.annotation_id)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_annotation(parent_annotation)
            await self.storage_backend.save_annotation(reply)
        
        return reply
    
    async def vote_on_annotation(
        self,
        annotation_id: str,
        user_id: str,
        vote: str  # 'agree' or 'disagree'
    ) -> bool:
        """Vote on an annotation for consensus building"""
        
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            raise ValueError(f"Annotation {annotation_id} not found")
        
        # Check permissions
        if not await self._check_annotation_permission(annotation, user_id, 'read'):
            raise PermissionError("Insufficient permissions to vote")
        
        if vote not in ['agree', 'disagree']:
            raise ValueError("Vote must be 'agree' or 'disagree'")
        
        # Record vote
        annotation.votes[user_id] = vote
        
        # Recalculate consensus score
        annotation.consensus_score = await self._calculate_consensus_score(annotation)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_annotation(annotation)
        
        return True
    
    async def get_content_annotations(
        self,
        content_id: str,
        user_id: str,
        annotation_types: Optional[List[AnnotationType]] = None,
        include_resolved: bool = False
    ) -> List[CollaborativeAnnotation]:
        """Get all annotations for content"""
        
        annotation_ids = self.content_annotations.get(content_id, [])
        annotations = []
        
        for annotation_id in annotation_ids:
            annotation = self.annotations.get(annotation_id)
            if not annotation:
                continue
            
            # Check permissions
            if not await self._check_annotation_permission(annotation, user_id, 'read'):
                continue
            
            # Filter by type
            if annotation_types and annotation.annotation_type not in annotation_types:
                continue
            
            # Filter resolved
            if not include_resolved and annotation.status == AnnotationStatus.RESOLVED:
                continue
            
            annotations.append(annotation)
        
        # Sort by creation time
        annotations.sort(key=lambda a: a.created_at)
        return annotations
    
    async def get_user_annotations(
        self,
        user_id: str,
        workspace_id: Optional[str] = None,
        status_filter: Optional[AnnotationStatus] = None,
        limit: int = 50
    ) -> List[CollaborativeAnnotation]:
        """Get annotations created by user"""
        
        annotation_ids = self.user_annotations.get(user_id, [])
        annotations = []
        
        for annotation_id in annotation_ids[-limit:]:  # Get recent annotations
            annotation = self.annotations.get(annotation_id)
            if not annotation:
                continue
            
            # Filter by workspace
            if workspace_id and annotation.workspace_id != workspace_id:
                continue
            
            # Filter by status
            if status_filter and annotation.status != status_filter:
                continue
            
            annotations.append(annotation)
        
        # Sort by creation time (newest first)
        annotations.sort(key=lambda a: a.created_at, reverse=True)
        return annotations
    
    async def resolve_annotation(
        self,
        annotation_id: str,
        user_id: str,
        resolution_note: Optional[str] = None
    ) -> bool:
        """Resolve an annotation"""
        
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            raise ValueError(f"Annotation {annotation_id} not found")
        
        # Check permissions
        if not await self._check_annotation_permission(annotation, user_id, 'write'):
            raise PermissionError("Insufficient permissions to resolve annotation")
        
        annotation.status = AnnotationStatus.RESOLVED
        annotation.updated_by = user_id
        annotation.updated_at = datetime.utcnow()
        
        if resolution_note:
            annotation.metadata.custom_fields['resolution_note'] = resolution_note
            annotation.metadata.custom_fields['resolved_by'] = user_id
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_annotation(annotation)
        
        return True
    
    async def search_annotations(
        self,
        workspace_id: str,
        user_id: str,
        query: str,
        annotation_types: Optional[List[AnnotationType]] = None,
        date_range: Optional[tuple] = None,
        limit: int = 100
    ) -> List[CollaborativeAnnotation]:
        """Search annotations by content"""
        
        # Verify workspace access
        if self.workspace_manager:
            workspace = await self.workspace_manager.get_workspace(workspace_id, user_id)
            if not workspace:
                raise PermissionError("No access to workspace")
        
        matching_annotations = []
        query_lower = query.lower()
        
        for annotation in self.annotations.values():
            # Filter by workspace
            if annotation.workspace_id != workspace_id:
                continue
            
            # Check permissions
            if not await self._check_annotation_permission(annotation, user_id, 'read'):
                continue
            
            # Filter by type
            if annotation_types and annotation.annotation_type not in annotation_types:
                continue
            
            # Filter by date range
            if date_range:
                start_date, end_date = date_range
                if not (start_date <= annotation.created_at <= end_date):
                    continue
            
            # Search in annotation content
            if self._matches_query(annotation, query_lower):
                matching_annotations.append(annotation)
            
            if len(matching_annotations) >= limit:
                break
        
        # Sort by relevance (creation time for now)
        matching_annotations.sort(key=lambda a: a.created_at, reverse=True)
        return matching_annotations
    
    async def get_annotation_thread(
        self,
        annotation_id: str,
        user_id: str
    ) -> List[CollaborativeAnnotation]:
        """Get full annotation thread (parent + replies)"""
        
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            raise ValueError(f"Annotation {annotation_id} not found")
        
        # Check permissions
        if not await self._check_annotation_permission(annotation, user_id, 'read'):
            raise PermissionError("Insufficient permissions to view annotation")
        
        thread = [annotation]
        
        # Get all replies
        for reply_id in annotation.replies:
            reply = self.annotations.get(reply_id)
            if reply and await self._check_annotation_permission(reply, user_id, 'read'):
                thread.append(reply)
        
        # Sort by creation time
        thread.sort(key=lambda a: a.created_at)
        return thread
    
    async def _check_annotation_permission(
        self,
        annotation: CollaborativeAnnotation,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if user has permission for annotation"""
        
        # Check workspace permissions
        if self.workspace_manager:
            return await self.workspace_manager._check_permission(
                annotation.workspace_id, user_id, permission
            )
        
        # Fallback: owner can do anything, others can read
        if permission == 'write':
            return annotation.created_by == user_id
        else:
            return True
    
    async def _calculate_consensus_score(self, annotation: CollaborativeAnnotation) -> float:
        """Calculate consensus score based on votes"""
        
        if not annotation.votes:
            return 0.0
        
        agree_votes = sum(1 for vote in annotation.votes.values() if vote == 'agree')
        total_votes = len(annotation.votes)
        
        return agree_votes / total_votes
    
    def _matches_query(self, annotation: CollaborativeAnnotation, query: str) -> bool:
        """Check if annotation matches search query"""
        
        # Search in annotation value
        if isinstance(annotation.value, str) and query in annotation.value.lower():
            return True
        
        # Search in selected text
        if (annotation.position and 
            annotation.position.selected_text and 
            query in annotation.position.selected_text.lower()):
            return True
        
        # Search in metadata tags
        if hasattr(annotation.metadata, 'tags'):
            for tag in annotation.metadata.tags:
                if query in tag.lower():
                    return True
        
        return False
    
    def get_annotation_stats(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get annotation statistics"""
        
        annotations = self.annotations.values()
        
        # Filter by workspace if specified
        if workspace_id:
            annotations = [a for a in annotations if a.workspace_id == workspace_id]
        
        total_annotations = len(annotations)
        
        # Count by type
        type_counts = {}
        for annotation in annotations:
            annotation_type = annotation.annotation_type.value
            type_counts[annotation_type] = type_counts.get(annotation_type, 0) + 1
        
        # Count by status
        status_counts = {}
        for annotation in annotations:
            status = annotation.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate average consensus score
        consensus_scores = [a.consensus_score for a in annotations if a.votes]
        avg_consensus = sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0.0
        
        return {
            'total_annotations': total_annotations,
            'annotations_by_type': type_counts,
            'annotations_by_status': status_counts,
            'average_consensus_score': avg_consensus,
            'annotations_with_votes': len(consensus_scores),
            'unique_annotators': len(set(a.created_by for a in annotations))
        }