"""
Knowledge base and documentation management for teams
"""

import logging
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import json
import re

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """Types of knowledge base documents"""
    GUIDE = "guide"
    PROCEDURE = "procedure"
    TEMPLATE = "template"
    REFERENCE = "reference"
    FAQ = "faq"
    BEST_PRACTICE = "best_practice"
    LESSON_LEARNED = "lesson_learned"
    ANALYSIS_REPORT = "analysis_report"
    INVESTIGATION_NOTES = "investigation_notes"

class DocumentStatus(Enum):
    """Document lifecycle status"""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"

class AccessLevel(Enum):
    """Document access levels"""
    PUBLIC = "public"
    TEAM = "team"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"

@dataclass
class DocumentVersion:
    """Document version information"""
    version_id: str
    version_number: str
    content: str
    created_by: str
    created_at: datetime
    change_summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentComment:
    """Comment on a document"""
    comment_id: str
    document_id: str
    user_id: str
    content: str
    created_at: datetime
    parent_comment_id: Optional[str] = None
    resolved: bool = False

@dataclass
class KnowledgeDocument:
    """Knowledge base document"""
    document_id: str
    title: str
    content: str
    document_type: DocumentType
    
    # Authorship and ownership
    created_by: str
    created_at: datetime
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    # Status and access
    status: DocumentStatus = DocumentStatus.DRAFT
    access_level: AccessLevel = AccessLevel.TEAM
    
    # Organization
    category: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    keywords: Set[str] = field(default_factory=set)
    
    # Versioning
    version: str = "1.0"
    versions: List[DocumentVersion] = field(default_factory=list)
    
    # Collaboration
    contributors: Set[str] = field(default_factory=set)
    reviewers: Set[str] = field(default_factory=set)
    comments: List[DocumentComment] = field(default_factory=list)
    
    # Metadata
    workspace_id: Optional[str] = None
    related_documents: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Usage tracking
    view_count: int = 0
    last_viewed: Optional[datetime] = None
    
    # Approval workflow
    approval_required: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

class KnowledgeBase:
    """Knowledge base management system"""
    
    def __init__(self, storage_backend=None, search_engine=None):
        """Initialize knowledge base"""
        self.storage_backend = storage_backend
        self.search_engine = search_engine
        self.documents: Dict[str, KnowledgeDocument] = {}
        self.categories: Dict[str, Set[str]] = {}  # category -> document_ids
        self.user_documents: Dict[str, Set[str]] = {}  # user_id -> document_ids
        self.workspace_documents: Dict[str, Set[str]] = {}  # workspace_id -> document_ids
    
    async def create_document(
        self,
        title: str,
        content: str,
        document_type: DocumentType,
        created_by: str,
        workspace_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        access_level: AccessLevel = AccessLevel.TEAM,
        approval_required: bool = False
    ) -> KnowledgeDocument:
        """Create a new knowledge document"""
        
        document_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Extract keywords from content
        keywords = self._extract_keywords(content)
        
        # Create initial version
        initial_version = DocumentVersion(
            version_id=str(uuid.uuid4()),
            version_number="1.0",
            content=content,
            created_by=created_by,
            created_at=now,
            change_summary="Initial version"
        )
        
        document = KnowledgeDocument(
            document_id=document_id,
            title=title,
            content=content,
            document_type=document_type,
            created_by=created_by,
            created_at=now,
            status=DocumentStatus.DRAFT,
            access_level=access_level,
            category=category,
            tags=tags or set(),
            keywords=keywords,
            versions=[initial_version],
            workspace_id=workspace_id,
            approval_required=approval_required
        )
        
        # Store document
        self.documents[document_id] = document
        
        # Update indexes
        if created_by not in self.user_documents:
            self.user_documents[created_by] = set()
        self.user_documents[created_by].add(document_id)
        
        if category:
            if category not in self.categories:
                self.categories[category] = set()
            self.categories[category].add(document_id)
        
        if workspace_id:
            if workspace_id not in self.workspace_documents:
                self.workspace_documents[workspace_id] = set()
            self.workspace_documents[workspace_id].add(document_id)
        
        # Index for search
        if self.search_engine:
            await self.search_engine.index_document(document)
        
        # Persist to storage
        if self.storage_backend:
            await self.storage_backend.save_document(document)
        
        logger.info(f"Created document {document_id}: {title}")
        return document
    
    async def update_document(
        self,
        document_id: str,
        user_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        category: Optional[str] = None,
        change_summary: str = "Updated document"
    ) -> bool:
        """Update document content"""
        
        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Check permissions
        if not await self._check_document_permission(document, user_id, 'write'):
            raise PermissionError("Insufficient permissions to update document")
        
        now = datetime.utcnow()
        version_updated = False
        
        # Update content and create new version if changed
        if content and content != document.content:
            new_version = DocumentVersion(
                version_id=str(uuid.uuid4()),
                version_number=self._increment_version(document.version),
                content=content,
                created_by=user_id,
                created_at=now,
                change_summary=change_summary
            )
            
            document.versions.append(new_version)
            document.content = content
            document.version = new_version.version_number
            document.keywords = self._extract_keywords(content)
            version_updated = True
        
        # Update metadata
        if title:
            document.title = title
        
        if tags is not None:
            document.tags = tags
        
        if category and category != document.category:
            # Remove from old category
            if document.category and document.category in self.categories:
                self.categories[document.category].discard(document_id)
            
            # Add to new category
            if category not in self.categories:
                self.categories[category] = set()
            self.categories[category].add(document_id)
            document.category = category
        
        document.updated_by = user_id
        document.updated_at = now
        
        # Add contributor
        document.contributors.add(user_id)
        
        # Update search index
        if self.search_engine and version_updated:
            await self.search_engine.update_document(document)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_document(document)
        
        return True
    
    async def add_comment(
        self,
        document_id: str,
        user_id: str,
        content: str,
        parent_comment_id: Optional[str] = None
    ) -> str:
        """Add comment to document"""
        
        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Check permissions
        if not await self._check_document_permission(document, user_id, 'read'):
            raise PermissionError("Insufficient permissions to comment")
        
        comment_id = str(uuid.uuid4())
        comment = DocumentComment(
            comment_id=comment_id,
            document_id=document_id,
            user_id=user_id,
            content=content,
            created_at=datetime.utcnow(),
            parent_comment_id=parent_comment_id
        )
        
        document.comments.append(comment)
        document.updated_at = datetime.utcnow()
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_document(document)
        
        return comment_id
    
    async def submit_for_review(
        self,
        document_id: str,
        user_id: str,
        reviewers: List[str]
    ) -> bool:
        """Submit document for review"""
        
        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Check permissions
        if not await self._check_document_permission(document, user_id, 'write'):
            raise PermissionError("Insufficient permissions to submit for review")
        
        if document.status != DocumentStatus.DRAFT:
            raise ValueError("Only draft documents can be submitted for review")
        
        document.status = DocumentStatus.REVIEW
        document.reviewers = set(reviewers)
        document.updated_at = datetime.utcnow()
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_document(document)
        
        return True
    
    async def approve_document(
        self,
        document_id: str,
        approver_id: str,
        publish: bool = True
    ) -> bool:
        """Approve document"""
        
        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Check if user is authorized to approve
        if approver_id not in document.reviewers and document.created_by != approver_id:
            raise PermissionError("Not authorized to approve this document")
        
        document.status = DocumentStatus.APPROVED
        document.approved_by = approver_id
        document.approved_at = datetime.utcnow()
        document.updated_at = datetime.utcnow()
        
        if publish:
            document.status = DocumentStatus.PUBLISHED
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_document(document)
        
        return True
    
    async def search_documents(
        self,
        user_id: str,
        query: str,
        document_types: Optional[List[DocumentType]] = None,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        limit: int = 50
    ) -> List[KnowledgeDocument]:
        """Search documents"""
        
        # Use search engine if available
        if self.search_engine:
            return await self.search_engine.search_documents(
                query, document_types, categories, tags, workspace_id, limit
            )
        
        # Fallback to basic search
        matching_documents = []
        query_lower = query.lower()
        
        for document in self.documents.values():
            # Check permissions
            if not await self._check_document_permission(document, user_id, 'read'):
                continue
            
            # Filter by workspace
            if workspace_id and document.workspace_id != workspace_id:
                continue
            
            # Filter by type
            if document_types and document.document_type not in document_types:
                continue
            
            # Filter by category
            if categories and document.category not in categories:
                continue
            
            # Filter by tags
            if tags and not any(tag in document.tags for tag in tags):
                continue
            
            # Search in content
            if self._matches_document_query(document, query_lower):
                matching_documents.append(document)
            
            if len(matching_documents) >= limit:
                break
        
        # Sort by relevance (view count and update time)
        matching_documents.sort(
            key=lambda d: (d.view_count, d.updated_at or d.created_at),
            reverse=True
        )
        
        return matching_documents
    
    async def get_document(
        self,
        document_id: str,
        user_id: str,
        track_view: bool = True
    ) -> Optional[KnowledgeDocument]:
        """Get document by ID"""
        
        document = self.documents.get(document_id)
        if not document:
            return None
        
        # Check permissions
        if not await self._check_document_permission(document, user_id, 'read'):
            return None
        
        # Track view
        if track_view:
            document.view_count += 1
            document.last_viewed = datetime.utcnow()
            
            if self.storage_backend:
                await self.storage_backend.update_document_stats(document_id, document.view_count)
        
        return document
    
    async def get_user_documents(
        self,
        user_id: str,
        document_types: Optional[List[DocumentType]] = None,
        status_filter: Optional[List[DocumentStatus]] = None
    ) -> List[KnowledgeDocument]:
        """Get documents created by user"""
        
        document_ids = self.user_documents.get(user_id, set())
        documents = []
        
        for document_id in document_ids:
            document = self.documents.get(document_id)
            if not document:
                continue
            
            # Filter by type
            if document_types and document.document_type not in document_types:
                continue
            
            # Filter by status
            if status_filter and document.status not in status_filter:
                continue
            
            documents.append(document)
        
        # Sort by update time
        documents.sort(key=lambda d: d.updated_at or d.created_at, reverse=True)
        return documents
    
    async def get_workspace_documents(
        self,
        workspace_id: str,
        user_id: str,
        category: Optional[str] = None
    ) -> List[KnowledgeDocument]:
        """Get documents in workspace"""
        
        document_ids = self.workspace_documents.get(workspace_id, set())
        documents = []
        
        for document_id in document_ids:
            document = self.documents.get(document_id)
            if not document:
                continue
            
            # Check permissions
            if not await self._check_document_permission(document, user_id, 'read'):
                continue
            
            # Filter by category
            if category and document.category != category:
                continue
            
            documents.append(document)
        
        # Sort by update time
        documents.sort(key=lambda d: d.updated_at or d.created_at, reverse=True)
        return documents
    
    async def create_template(
        self,
        title: str,
        content: str,
        created_by: str,
        template_type: str,
        workspace_id: Optional[str] = None,
        tags: Optional[Set[str]] = None
    ) -> KnowledgeDocument:
        """Create a reusable template"""
        
        template_tags = tags or set()
        template_tags.add(f"template:{template_type}")
        
        return await self.create_document(
            title=title,
            content=content,
            document_type=DocumentType.TEMPLATE,
            created_by=created_by,
            workspace_id=workspace_id,
            category="templates",
            tags=template_tags,
            access_level=AccessLevel.TEAM
        )
    
    async def get_templates(
        self,
        user_id: str,
        template_type: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> List[KnowledgeDocument]:
        """Get available templates"""
        
        templates = []
        
        for document in self.documents.values():
            if document.document_type != DocumentType.TEMPLATE:
                continue
            
            # Check permissions
            if not await self._check_document_permission(document, user_id, 'read'):
                continue
            
            # Filter by workspace
            if workspace_id and document.workspace_id != workspace_id:
                continue
            
            # Filter by template type
            if template_type:
                template_tag = f"template:{template_type}"
                if template_tag not in document.tags:
                    continue
            
            templates.append(document)
        
        # Sort by usage (view count)
        templates.sort(key=lambda t: t.view_count, reverse=True)
        return templates
    
    async def _check_document_permission(
        self,
        document: KnowledgeDocument,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if user has permission for document"""
        
        # Document creator has full permissions
        if document.created_by == user_id:
            return True
        
        # Contributors can read and write
        if user_id in document.contributors:
            return permission in ['read', 'write']
        
        # Reviewers can read
        if user_id in document.reviewers:
            return permission == 'read'
        
        # Check access level
        if document.access_level == AccessLevel.PUBLIC:
            return permission == 'read'
        elif document.access_level == AccessLevel.TEAM:
            # For team access, check if user is in same workspace
            # This would need workspace manager integration
            return permission == 'read'
        
        return False
    
    def _extract_keywords(self, content: str) -> Set[str]:
        """Extract keywords from document content"""
        
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Filter out common words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        
        keywords = set()
        for word in words:
            if len(word) > 3 and word not in stop_words:
                keywords.add(word)
        
        return keywords
    
    def _matches_document_query(self, document: KnowledgeDocument, query: str) -> bool:
        """Check if document matches search query"""
        
        # Search in title
        if query in document.title.lower():
            return True
        
        # Search in content
        if query in document.content.lower():
            return True
        
        # Search in tags
        for tag in document.tags:
            if query in tag.lower():
                return True
        
        # Search in keywords
        for keyword in document.keywords:
            if query in keyword.lower():
                return True
        
        return False
    
    def _increment_version(self, current_version: str) -> str:
        """Increment version number"""
        
        try:
            parts = current_version.split('.')
            if len(parts) == 2:
                major, minor = int(parts[0]), int(parts[1])
                return f"{major}.{minor + 1}"
            else:
                return f"{current_version}.1"
        except:
            return "1.1"
    
    def get_knowledge_base_stats(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        
        documents = self.documents.values()
        
        # Filter by workspace if specified
        if workspace_id:
            documents = [d for d in documents if d.workspace_id == workspace_id]
        
        total_documents = len(documents)
        
        # Count by type
        type_counts = {}
        for document in documents:
            doc_type = document.document_type.value
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        # Count by status
        status_counts = {}
        for document in documents:
            status = document.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by category
        category_counts = {}
        for document in documents:
            if document.category:
                category_counts[document.category] = category_counts.get(document.category, 0) + 1
        
        # Calculate total views
        total_views = sum(d.view_count for d in documents)
        
        # Most viewed documents
        most_viewed = sorted(documents, key=lambda d: d.view_count, reverse=True)[:5]
        
        return {
            'total_documents': total_documents,
            'documents_by_type': type_counts,
            'documents_by_status': status_counts,
            'documents_by_category': category_counts,
            'total_views': total_views,
            'most_viewed_documents': [
                {'id': d.document_id, 'title': d.title, 'views': d.view_count}
                for d in most_viewed
            ],
            'unique_contributors': len(set(d.created_by for d in documents)),
            'templates_count': type_counts.get('template', 0)
        }

class DocumentationManager:
    """Manages documentation workflows and processes"""
    
    def __init__(self, knowledge_base: KnowledgeBase, team_coordinator=None):
        """Initialize documentation manager"""
        self.knowledge_base = knowledge_base
        self.team_coordinator = team_coordinator
        self.documentation_workflows: Dict[str, Dict[str, Any]] = {}
    
    async def create_documentation_workflow(
        self,
        workflow_name: str,
        document_types: List[DocumentType],
        required_reviewers: int,
        approval_required: bool,
        created_by: str,
        workspace_id: Optional[str] = None
    ) -> str:
        """Create documentation workflow"""
        
        workflow_id = str(uuid.uuid4())
        
        workflow = {
            'workflow_id': workflow_id,
            'name': workflow_name,
            'document_types': [dt.value for dt in document_types],
            'required_reviewers': required_reviewers,
            'approval_required': approval_required,
            'created_by': created_by,
            'created_at': datetime.utcnow().isoformat(),
            'workspace_id': workspace_id,
            'active': True
        }
        
        self.documentation_workflows[workflow_id] = workflow
        
        logger.info(f"Created documentation workflow {workflow_id}: {workflow_name}")
        return workflow_id
    
    async def generate_analysis_report(
        self,
        analysis_data: Dict[str, Any],
        created_by: str,
        workspace_id: Optional[str] = None,
        template_id: Optional[str] = None
    ) -> KnowledgeDocument:
        """Generate analysis report from data"""
        
        # Use template if provided
        content = ""
        if template_id:
            template = await self.knowledge_base.get_document(template_id, created_by)
            if template:
                content = template.content
        
        # Generate report content
        if not content:
            content = self._generate_default_report_content(analysis_data)
        else:
            content = self._populate_template_content(content, analysis_data)
        
        # Create document
        title = f"Analysis Report - {analysis_data.get('title', 'Untitled')} - {datetime.utcnow().strftime('%Y-%m-%d')}"
        
        return await self.knowledge_base.create_document(
            title=title,
            content=content,
            document_type=DocumentType.ANALYSIS_REPORT,
            created_by=created_by,
            workspace_id=workspace_id,
            category="reports",
            tags={'analysis', 'report', 'generated'},
            approval_required=True
        )
    
    async def create_investigation_notes(
        self,
        case_id: str,
        findings: str,
        evidence_summary: str,
        created_by: str,
        workspace_id: Optional[str] = None
    ) -> KnowledgeDocument:
        """Create investigation notes document"""
        
        content = f"""# Investigation Notes - Case {case_id}

## Summary
Investigation notes for case {case_id}

## Findings
{findings}

## Evidence Summary
{evidence_summary}

## Created
- Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
- Analyst: {created_by}
- Case ID: {case_id}
"""
        
        title = f"Investigation Notes - Case {case_id}"
        
        return await self.knowledge_base.create_document(
            title=title,
            content=content,
            document_type=DocumentType.INVESTIGATION_NOTES,
            created_by=created_by,
            workspace_id=workspace_id,
            category="investigations",
            tags={'investigation', 'case', case_id},
            access_level=AccessLevel.RESTRICTED
        )
    
    def _generate_default_report_content(self, analysis_data: Dict[str, Any]) -> str:
        """Generate default report content"""
        
        return f"""# Analysis Report

## Executive Summary
{analysis_data.get('summary', 'Analysis summary not provided')}

## Methodology
{analysis_data.get('methodology', 'Methodology not specified')}

## Key Findings
{analysis_data.get('findings', 'Findings not provided')}

## Data Analysis
{analysis_data.get('analysis', 'Analysis details not provided')}

## Recommendations
{analysis_data.get('recommendations', 'No recommendations provided')}

## Appendix
- Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
- Data Sources: {', '.join(analysis_data.get('sources', []))}
"""
    
    def _populate_template_content(self, template_content: str, data: Dict[str, Any]) -> str:
        """Populate template with analysis data"""
        
        # Simple template variable replacement
        content = template_content
        
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in content:
                content = content.replace(placeholder, str(value))
        
        # Add timestamp
        content = content.replace("{timestamp}", datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        
        return content