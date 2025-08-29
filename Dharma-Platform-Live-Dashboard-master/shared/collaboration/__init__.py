"""
Collaboration and team features for analyst teams
"""

from .workspace_manager import WorkspaceManager, SharedWorkspace
from .annotation_service import AnnotationService, CollaborativeAnnotation
from .case_manager import CaseManager, InvestigationCase
from .team_coordinator import TeamCoordinator, WorkflowManager

# Import knowledge base components separately to avoid circular imports
try:
    from .knowledge_base import KnowledgeBase, DocumentationManager
except ImportError:
    # Fallback if there are import issues
    KnowledgeBase = None
    DocumentationManager = None

__all__ = [
    'WorkspaceManager',
    'SharedWorkspace',
    'AnnotationService', 
    'CollaborativeAnnotation',
    'CaseManager',
    'InvestigationCase',
    'TeamCoordinator',
    'WorkflowManager',
    'KnowledgeBase',
    'DocumentationManager'
]