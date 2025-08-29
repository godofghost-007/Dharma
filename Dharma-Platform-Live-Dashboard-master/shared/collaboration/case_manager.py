"""
Case management system for investigation workflows
"""

import logging
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)

class CaseStatus(Enum):
    """Investigation case status"""
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ARCHIVED = "archived"

class CasePriority(Enum):
    """Case priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"

class CaseType(Enum):
    """Types of investigation cases"""
    DISINFORMATION = "disinformation"
    BOT_NETWORK = "bot_network"
    COORDINATED_CAMPAIGN = "coordinated_campaign"
    THREAT_MONITORING = "threat_monitoring"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    CONTENT_VERIFICATION = "content_verification"
    INFLUENCE_OPERATION = "influence_operation"

@dataclass
class CaseEvidence:
    """Evidence item in a case"""
    evidence_id: str
    evidence_type: str  # 'post', 'user', 'network', 'document', 'media'
    source_id: str  # ID of the source item
    description: str
    collected_by: str
    collected_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

@dataclass
class CaseTimeline:
    """Timeline entry for case"""
    entry_id: str
    timestamp: datetime
    event_type: str  # 'created', 'updated', 'assigned', 'evidence_added', 'status_changed'
    description: str
    user_id: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CaseAssignment:
    """Case assignment information"""
    assigned_to: str
    assigned_by: str
    assigned_at: datetime
    role: str  # 'lead', 'analyst', 'reviewer', 'observer'
    notes: Optional[str] = None

@dataclass
class InvestigationCase:
    """Investigation case for tracking analysis workflows"""
    case_id: str
    title: str
    description: str
    case_type: CaseType
    
    # Status and priority
    status: CaseStatus
    priority: CasePriority
    
    # Ownership and assignment
    created_by: str
    created_at: datetime
    updated_at: datetime
    assignments: List[CaseAssignment] = field(default_factory=list)
    
    # Content and evidence
    evidence: List[CaseEvidence] = field(default_factory=list)
    timeline: List[CaseTimeline] = field(default_factory=list)
    
    # Workspace integration
    workspace_id: Optional[str] = None
    related_cases: Set[str] = field(default_factory=set)
    
    # Metadata and classification
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Deadlines and scheduling
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    
    # Results and conclusions
    findings: Optional[str] = None
    recommendations: Optional[str] = None
    confidence_score: Optional[float] = None

class CaseManager:
    """Manages investigation cases and workflows"""
    
    def __init__(self, storage_backend=None, workspace_manager=None):
        """Initialize case manager"""
        self.storage_backend = storage_backend
        self.workspace_manager = workspace_manager
        self.cases: Dict[str, InvestigationCase] = {}
        self.user_cases: Dict[str, Set[str]] = {}  # user_id -> case_ids
        self.workspace_cases: Dict[str, Set[str]] = {}  # workspace_id -> case_ids
    
    async def create_case(
        self,
        title: str,
        description: str,
        case_type: CaseType,
        priority: CasePriority,
        created_by: str,
        workspace_id: Optional[str] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[Set[str]] = None
    ) -> InvestigationCase:
        """Create a new investigation case"""
        
        case_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create initial timeline entry
        timeline_entry = CaseTimeline(
            entry_id=str(uuid.uuid4()),
            timestamp=now,
            event_type='created',
            description=f"Case created: {title}",
            user_id=created_by,
            details={'initial_priority': priority.value, 'initial_type': case_type.value}
        )
        
        case = InvestigationCase(
            case_id=case_id,
            title=title,
            description=description,
            case_type=case_type,
            status=CaseStatus.DRAFT,
            priority=priority,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            workspace_id=workspace_id,
            due_date=due_date,
            tags=tags or set(),
            timeline=[timeline_entry]
        )
        
        # Store case
        self.cases[case_id] = case
        
        # Update indexes
        if created_by not in self.user_cases:
            self.user_cases[created_by] = set()
        self.user_cases[created_by].add(case_id)
        
        if workspace_id:
            if workspace_id not in self.workspace_cases:
                self.workspace_cases[workspace_id] = set()
            self.workspace_cases[workspace_id].add(case_id)
        
        # Persist to storage
        if self.storage_backend:
            await self.storage_backend.save_case(case)
        
        logger.info(f"Created case {case_id}: {title}")
        return case
    
    async def assign_case(
        self,
        case_id: str,
        assigned_to: str,
        assigned_by: str,
        role: str = 'analyst',
        notes: Optional[str] = None
    ) -> bool:
        """Assign case to a user"""
        
        case = self.cases.get(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Check permissions
        if not await self._check_case_permission(case, assigned_by, 'manage'):
            raise PermissionError("Insufficient permissions to assign case")
        
        # Create assignment
        assignment = CaseAssignment(
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow(),
            role=role,
            notes=notes
        )
        
        case.assignments.append(assignment)
        case.updated_at = datetime.utcnow()
        
        # Add timeline entry
        timeline_entry = CaseTimeline(
            entry_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type='assigned',
            description=f"Case assigned to {assigned_to} as {role}",
            user_id=assigned_by,
            details={'assigned_to': assigned_to, 'role': role}
        )
        case.timeline.append(timeline_entry)
        
        # Update user cases index
        if assigned_to not in self.user_cases:
            self.user_cases[assigned_to] = set()
        self.user_cases[assigned_to].add(case_id)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_case(case)
        
        logger.info(f"Assigned case {case_id} to {assigned_to}")
        return True
    
    async def update_case_status(
        self,
        case_id: str,
        new_status: CaseStatus,
        user_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update case status"""
        
        case = self.cases.get(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Check permissions
        if not await self._check_case_permission(case, user_id, 'write'):
            raise PermissionError("Insufficient permissions to update case")
        
        old_status = case.status
        case.status = new_status
        case.updated_at = datetime.utcnow()
        
        # Add timeline entry
        timeline_entry = CaseTimeline(
            entry_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type='status_changed',
            description=f"Status changed from {old_status.value} to {new_status.value}",
            user_id=user_id,
            details={'old_status': old_status.value, 'new_status': new_status.value, 'notes': notes}
        )
        case.timeline.append(timeline_entry)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_case(case)
        
        logger.info(f"Updated case {case_id} status to {new_status.value}")
        return True
    
    async def add_evidence(
        self,
        case_id: str,
        evidence_type: str,
        source_id: str,
        description: str,
        collected_by: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None
    ) -> str:
        """Add evidence to case"""
        
        case = self.cases.get(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Check permissions
        if not await self._check_case_permission(case, collected_by, 'write'):
            raise PermissionError("Insufficient permissions to add evidence")
        
        evidence_id = str(uuid.uuid4())
        evidence = CaseEvidence(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            source_id=source_id,
            description=description,
            collected_by=collected_by,
            collected_at=datetime.utcnow(),
            metadata=metadata or {},
            tags=tags or set()
        )
        
        case.evidence.append(evidence)
        case.updated_at = datetime.utcnow()
        
        # Add timeline entry
        timeline_entry = CaseTimeline(
            entry_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type='evidence_added',
            description=f"Added {evidence_type} evidence: {description}",
            user_id=collected_by,
            details={'evidence_id': evidence_id, 'evidence_type': evidence_type}
        )
        case.timeline.append(timeline_entry)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_case(case)
        
        logger.info(f"Added evidence {evidence_id} to case {case_id}")
        return evidence_id
    
    async def update_case_findings(
        self,
        case_id: str,
        findings: str,
        recommendations: Optional[str],
        confidence_score: Optional[float],
        updated_by: str
    ) -> bool:
        """Update case findings and recommendations"""
        
        case = self.cases.get(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Check permissions
        if not await self._check_case_permission(case, updated_by, 'write'):
            raise PermissionError("Insufficient permissions to update findings")
        
        case.findings = findings
        case.recommendations = recommendations
        case.confidence_score = confidence_score
        case.updated_at = datetime.utcnow()
        
        # Add timeline entry
        timeline_entry = CaseTimeline(
            entry_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type='findings_updated',
            description="Case findings and recommendations updated",
            user_id=updated_by,
            details={'has_recommendations': recommendations is not None, 'confidence_score': confidence_score}
        )
        case.timeline.append(timeline_entry)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_case(case)
        
        return True
    
    async def link_cases(
        self,
        case_id1: str,
        case_id2: str,
        linked_by: str,
        relationship_type: str = 'related'
    ) -> bool:
        """Link two related cases"""
        
        case1 = self.cases.get(case_id1)
        case2 = self.cases.get(case_id2)
        
        if not case1 or not case2:
            raise ValueError("One or both cases not found")
        
        # Check permissions for both cases
        if (not await self._check_case_permission(case1, linked_by, 'write') or
            not await self._check_case_permission(case2, linked_by, 'write')):
            raise PermissionError("Insufficient permissions to link cases")
        
        # Add mutual links
        case1.related_cases.add(case_id2)
        case2.related_cases.add(case_id1)
        
        case1.updated_at = datetime.utcnow()
        case2.updated_at = datetime.utcnow()
        
        # Add timeline entries
        for case, other_id in [(case1, case_id2), (case2, case_id1)]:
            timeline_entry = CaseTimeline(
                entry_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                event_type='case_linked',
                description=f"Linked to case {other_id}",
                user_id=linked_by,
                details={'linked_case': other_id, 'relationship_type': relationship_type}
            )
            case.timeline.append(timeline_entry)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_case(case1)
            await self.storage_backend.save_case(case2)
        
        return True
    
    async def get_user_cases(
        self,
        user_id: str,
        status_filter: Optional[List[CaseStatus]] = None,
        priority_filter: Optional[List[CasePriority]] = None,
        limit: int = 50
    ) -> List[InvestigationCase]:
        """Get cases for a user"""
        
        case_ids = self.user_cases.get(user_id, set())
        cases = []
        
        for case_id in case_ids:
            case = self.cases.get(case_id)
            if not case:
                continue
            
            # Filter by status
            if status_filter and case.status not in status_filter:
                continue
            
            # Filter by priority
            if priority_filter and case.priority not in priority_filter:
                continue
            
            cases.append(case)
        
        # Sort by priority and update time
        priority_order = {CasePriority.URGENT: 5, CasePriority.CRITICAL: 4, 
                         CasePriority.HIGH: 3, CasePriority.MEDIUM: 2, CasePriority.LOW: 1}
        
        cases.sort(key=lambda c: (priority_order[c.priority], c.updated_at), reverse=True)
        return cases[:limit]
    
    async def get_workspace_cases(
        self,
        workspace_id: str,
        user_id: str,
        status_filter: Optional[List[CaseStatus]] = None
    ) -> List[InvestigationCase]:
        """Get cases for a workspace"""
        
        # Verify workspace access
        if self.workspace_manager:
            workspace = await self.workspace_manager.get_workspace(workspace_id, user_id)
            if not workspace:
                raise PermissionError("No access to workspace")
        
        case_ids = self.workspace_cases.get(workspace_id, set())
        cases = []
        
        for case_id in case_ids:
            case = self.cases.get(case_id)
            if not case:
                continue
            
            # Filter by status
            if status_filter and case.status not in status_filter:
                continue
            
            cases.append(case)
        
        # Sort by update time
        cases.sort(key=lambda c: c.updated_at, reverse=True)
        return cases
    
    async def search_cases(
        self,
        user_id: str,
        query: str,
        case_types: Optional[List[CaseType]] = None,
        status_filter: Optional[List[CaseStatus]] = None,
        date_range: Optional[tuple] = None,
        limit: int = 100
    ) -> List[InvestigationCase]:
        """Search cases by content"""
        
        matching_cases = []
        query_lower = query.lower()
        
        # Get user's accessible cases
        user_case_ids = self.user_cases.get(user_id, set())
        
        for case_id in user_case_ids:
            case = self.cases.get(case_id)
            if not case:
                continue
            
            # Filter by type
            if case_types and case.case_type not in case_types:
                continue
            
            # Filter by status
            if status_filter and case.status not in status_filter:
                continue
            
            # Filter by date range
            if date_range:
                start_date, end_date = date_range
                if not (start_date <= case.created_at <= end_date):
                    continue
            
            # Search in case content
            if self._matches_case_query(case, query_lower):
                matching_cases.append(case)
            
            if len(matching_cases) >= limit:
                break
        
        # Sort by relevance (update time for now)
        matching_cases.sort(key=lambda c: c.updated_at, reverse=True)
        return matching_cases
    
    async def get_case_analytics(
        self,
        workspace_id: Optional[str] = None,
        date_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Get case analytics and metrics"""
        
        cases = self.cases.values()
        
        # Filter by workspace
        if workspace_id:
            cases = [c for c in cases if c.workspace_id == workspace_id]
        
        # Filter by date range
        if date_range:
            start_date, end_date = date_range
            cases = [c for c in cases if start_date <= c.created_at <= end_date]
        
        total_cases = len(cases)
        
        # Count by status
        status_counts = {}
        for case in cases:
            status = case.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by priority
        priority_counts = {}
        for case in cases:
            priority = case.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Count by type
        type_counts = {}
        for case in cases:
            case_type = case.case_type.value
            type_counts[case_type] = type_counts.get(case_type, 0) + 1
        
        # Calculate average resolution time for closed cases
        closed_cases = [c for c in cases if c.status == CaseStatus.CLOSED]
        avg_resolution_time = None
        if closed_cases:
            resolution_times = []
            for case in closed_cases:
                # Find closure time from timeline
                for entry in reversed(case.timeline):
                    if entry.event_type == 'status_changed' and entry.details.get('new_status') == 'closed':
                        resolution_time = (entry.timestamp - case.created_at).total_seconds() / 3600  # hours
                        resolution_times.append(resolution_time)
                        break
            
            if resolution_times:
                avg_resolution_time = sum(resolution_times) / len(resolution_times)
        
        return {
            'total_cases': total_cases,
            'cases_by_status': status_counts,
            'cases_by_priority': priority_counts,
            'cases_by_type': type_counts,
            'average_resolution_time_hours': avg_resolution_time,
            'overdue_cases': len([c for c in cases if c.due_date and c.due_date < datetime.utcnow() and c.status not in [CaseStatus.CLOSED, CaseStatus.RESOLVED]]),
            'active_cases': len([c for c in cases if c.status in [CaseStatus.OPEN, CaseStatus.IN_PROGRESS]])
        }
    
    async def _check_case_permission(
        self,
        case: InvestigationCase,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if user has permission for case"""
        
        # Case creator has full permissions
        if case.created_by == user_id:
            return True
        
        # Check if user is assigned to case
        for assignment in case.assignments:
            if assignment.assigned_to == user_id:
                if permission == 'read':
                    return True
                elif permission == 'write' and assignment.role in ['lead', 'analyst']:
                    return True
                elif permission == 'manage' and assignment.role == 'lead':
                    return True
        
        # Check workspace permissions if case is in workspace
        if case.workspace_id and self.workspace_manager:
            return await self.workspace_manager._check_permission(
                case.workspace_id, user_id, permission
            )
        
        return False
    
    def _matches_case_query(self, case: InvestigationCase, query: str) -> bool:
        """Check if case matches search query"""
        
        # Search in title and description
        if query in case.title.lower() or query in case.description.lower():
            return True
        
        # Search in findings and recommendations
        if case.findings and query in case.findings.lower():
            return True
        
        if case.recommendations and query in case.recommendations.lower():
            return True
        
        # Search in tags
        for tag in case.tags:
            if query in tag.lower():
                return True
        
        # Search in evidence descriptions
        for evidence in case.evidence:
            if query in evidence.description.lower():
                return True
        
        return False