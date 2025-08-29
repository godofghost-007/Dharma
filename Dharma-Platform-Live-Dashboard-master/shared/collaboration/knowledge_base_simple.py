"""
Simple knowledge base for testing
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

class DocumentType(Enum):
    """Types of knowledge base documents"""
    GUIDE = "guide"
    TEMPLATE = "template"
    BEST_PRACTICE = "best_practice"
    ANALYSIS_REPORT = "analysis_report"
    INVESTIGATION_NOTES = "investigation_notes"

class DocumentStatus(Enum):
    """Document lifecycle status"""
    DRAFT = "draft"
    PUBLISHED = "published"

class AccessLevel(Enum):
    """Document access levels"""
    PUBLIC = "public"
    TEAM = "team"

@dataclass
class KnowledgeDocument:
    """Simple knowledge document"""
    document_id: str
    title: str
    content: str
    document_type: DocumentType
    created_by: str
    created_at: datetime
    status: DocumentStatus = DocumentStatus.DRAFT
    access_level: AccessLevel = AccessLevel.TEAM
    tags: Set[str] = field(default_factory=set)
    view_count: int = 0

class KnowledgeBase:
    """Simple knowledge base"""
    
    def __init__(self):
        self.documents: Dict[str, KnowledgeDocument] = {}
    
    async def create_document(
        self,
        title: str,
        content: str,
        document_type: DocumentType,
        created_by: str,
        **kwargs
    ) -> KnowledgeDocument:
        """Create a document"""
        document_id = str(uuid.uuid4())
        
        document = KnowledgeDocument(
            document_id=document_id,
            title=title,
            content=content,
            document_type=document_type,
            created_by=created_by,
            created_at=datetime.utcnow(),
            tags=kwargs.get('tags', set())
        )
        
        self.documents[document_id] = document
        return document
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[KnowledgeDocument]:
        """Get a document"""
        return self.documents.get(document_id)
    
    async def search_documents(self, user_id: str, query: str, **kwargs) -> List[KnowledgeDocument]:
        """Search documents"""
        results = []
        query_lower = query.lower()
        
        for doc in self.documents.values():
            if query_lower in doc.title.lower() or query_lower in doc.content.lower():
                results.append(doc)
        
        return results
    
    async def create_template(self, title: str, content: str, created_by: str, template_type: str, **kwargs) -> KnowledgeDocument:
        """Create a template"""
        return await self.create_document(
            title=title,
            content=content,
            document_type=DocumentType.TEMPLATE,
            created_by=created_by,
            tags={f"template:{template_type}"}
        )
    
    async def get_templates(self, user_id: str, **kwargs) -> List[KnowledgeDocument]:
        """Get templates"""
        return [doc for doc in self.documents.values() if doc.document_type == DocumentType.TEMPLATE]
    
    async def add_comment(self, document_id: str, user_id: str, content: str, **kwargs) -> str:
        """Add comment to document"""
        return str(uuid.uuid4())
    
    async def update_document(self, document_id: str, user_id: str, **kwargs) -> bool:
        """Update document"""
        return True
    
    def get_knowledge_base_stats(self, **kwargs) -> Dict[str, Any]:
        """Get stats"""
        return {
            'total_documents': len(self.documents),
            'documents_by_type': {},
            'total_views': sum(d.view_count for d in self.documents.values())
        }

class DocumentationManager:
    """Simple documentation manager"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base
    
    async def create_documentation_workflow(self, workflow_name: str, **kwargs) -> str:
        """Create workflow"""
        return str(uuid.uuid4())
    
    async def generate_analysis_report(self, analysis_data: Dict[str, Any], created_by: str, **kwargs) -> KnowledgeDocument:
        """Generate report"""
        title = f"Analysis Report - {analysis_data.get('title', 'Untitled')}"
        content = f"# {title}\n\n{analysis_data.get('summary', 'No summary')}"
        
        return await self.knowledge_base.create_document(
            title=title,
            content=content,
            document_type=DocumentType.ANALYSIS_REPORT,
            created_by=created_by
        )
    
    async def create_investigation_notes(self, case_id: str, findings: str, evidence_summary: str, created_by: str, **kwargs) -> KnowledgeDocument:
        """Create investigation notes"""
        title = f"Investigation Notes - Case {case_id}"
        content = f"# {title}\n\n## Findings\n{findings}\n\n## Evidence\n{evidence_summary}"
        
        return await self.knowledge_base.create_document(
            title=title,
            content=content,
            document_type=DocumentType.INVESTIGATION_NOTES,
            created_by=created_by
        )