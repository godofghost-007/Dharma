#!/usr/bin/env python3
"""
Collaboration Service API
Provides REST API for collaboration features
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.collaboration.workspace_manager import WorkspaceManager, WorkspaceType, AccessLevel
from shared.collaboration.annotation_service import AnnotationService, AnnotationType
from shared.collaboration.case_manager import CaseManager, CaseType, CasePriority
from shared.collaboration.team_coordinator import TeamCoordinator, NotificationType
from shared.collaboration.knowledge_base_simple import KnowledgeBase, DocumentType

app = FastAPI(title="Collaboration Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
workspace_manager = WorkspaceManager()
annotation_service = AnnotationService(workspace_manager=workspace_manager)
case_manager = CaseManager(workspace_manager=workspace_manager)
team_coordinator = TeamCoordinator()
knowledge_base = KnowledgeBase()

# Request models
class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str
    workspace_type: str
    owner_username: str
    owner_email: str

class CreateAnnotationRequest(BaseModel):
    content_id: str
    workspace_id: str
    annotation_type: str
    value: Any

class CreateCaseRequest(BaseModel):
    title: str
    description: str
    case_type: str
    priority: str
    workspace_id: Optional[str] = None

# Workspace endpoints
@app.post("/api/v1/workspaces")
async def create_workspace(request: CreateWorkspaceRequest, user_id: str = "default_user"):
    """Create a new workspace"""
    try:
        workspace = await workspace_manager.create_workspace(
            name=request.name,
            description=request.description,
            workspace_type=WorkspaceType(request.workspace_type),
            owner_id=user_id,
            owner_username=request.owner_username,
            owner_email=request.owner_email
        )
        return {"workspace_id": workspace.workspace_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/workspaces")
async def get_user_workspaces(user_id: str = "default_user"):
    """Get workspaces for user"""
    workspaces = await workspace_manager.get_user_workspaces(user_id)
    return [{"id": w.workspace_id, "name": w.name, "type": w.workspace_type.value} for w in workspaces]

# Annotation endpoints  
@app.post("/api/v1/annotations")
async def create_annotation(request: CreateAnnotationRequest, user_id: str = "default_user"):
    """Create annotation"""
    try:
        annotation = await annotation_service.create_annotation(
            content_id=request.content_id,
            workspace_id=request.workspace_id,
            annotation_type=AnnotationType(request.annotation_type),
            value=request.value,
            created_by=user_id
        )
        return {"annotation_id": annotation.annotation_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/annotations/{content_id}")
async def get_content_annotations(content_id: str, user_id: str = "default_user"):
    """Get annotations for content"""
    annotations = await annotation_service.get_content_annotations(content_id, user_id)
    return [{"id": a.annotation_id, "type": a.annotation_type.value, "value": a.value} for a in annotations]

# Case management endpoints
@app.post("/api/v1/cases")
async def create_case(request: CreateCaseRequest, user_id: str = "default_user"):
    """Create investigation case"""
    try:
        case = await case_manager.create_case(
            title=request.title,
            description=request.description,
            case_type=CaseType(request.case_type),
            priority=CasePriority(request.priority),
            created_by=user_id,
            workspace_id=request.workspace_id
        )
        return {"case_id": case.case_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/cases")
async def get_user_cases(user_id: str = "default_user"):
    """Get cases for user"""
    cases = await case_manager.get_user_cases(user_id)
    return [{"id": c.case_id, "title": c.title, "status": c.status.value} for c in cases]

# Knowledge base endpoints
@app.post("/api/v1/documents")
async def create_document(
    title: str,
    content: str,
    document_type: str,
    user_id: str = "default_user"
):
    """Create knowledge document"""
    try:
        document = await knowledge_base.create_document(
            title=title,
            content=content,
            document_type=DocumentType(document_type),
            created_by=user_id
        )
        return {"document_id": document.document_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/documents/search")
async def search_documents(query: str, user_id: str = "default_user"):
    """Search documents"""
    documents = await knowledge_base.search_documents(user_id, query)
    return [{"id": d.document_id, "title": d.title, "type": d.document_type.value} for d in documents]

# Statistics endpoints
@app.get("/api/v1/stats/workspaces")
async def get_workspace_stats():
    """Get workspace statistics"""
    return workspace_manager.get_workspace_stats()

@app.get("/api/v1/stats/annotations")
async def get_annotation_stats():
    """Get annotation statistics"""
    return annotation_service.get_annotation_stats()

@app.get("/api/v1/stats/cases")
async def get_case_stats():
    """Get case statistics"""
    return await case_manager.get_case_analytics()

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "collaboration"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)