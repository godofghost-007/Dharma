#!/usr/bin/env python3
"""
Test script for collaboration and team features
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from shared.collaboration.workspace_manager import WorkspaceManager, SharedWorkspace, WorkspaceType, AccessLevel
from shared.collaboration.annotation_service import AnnotationService, AnnotationType, AnnotationStatus
from shared.collaboration.case_manager import CaseManager, CaseType, CaseStatus, CasePriority
from shared.collaboration.team_coordinator import TeamCoordinator, WorkflowManager, NotificationType
from shared.collaboration.knowledge_base_simple import KnowledgeBase, DocumentType, DocumentStatus, DocumentationManager

async def test_workspace_management():
    """Test shared workspace functionality"""
    print("Testing Workspace Management...")
    
    workspace_manager = WorkspaceManager()
    
    # Create workspace
    workspace = await workspace_manager.create_workspace(
        name="Disinformation Investigation",
        description="Workspace for tracking disinformation campaigns",
        workspace_type=WorkspaceType.INVESTIGATION,
        owner_id="analyst1",
        owner_username="Alice Analyst",
        owner_email="alice@dharma.gov"
    )
    
    print(f"✓ Created workspace: {workspace.name}")
    
    # Add team members
    await workspace_manager.add_member(
        workspace_id=workspace.workspace_id,
        user_id="analyst2",
        username="Bob Researcher",
        email="bob@dharma.gov",
        access_level=AccessLevel.EDITOR,
        added_by="analyst1"
    )
    
    await workspace_manager.add_member(
        workspace_id=workspace.workspace_id,
        user_id="analyst3",
        username="Carol Investigator",
        email="carol@dharma.gov",
        access_level=AccessLevel.VIEWER,
        added_by="analyst1"
    )
    
    print(f"✓ Added {len(workspace.members)} members to workspace")
    
    # Update workspace content
    await workspace_manager.update_workspace_content(
        workspace_id=workspace.workspace_id,
        user_id="analyst2",
        content_updates={
            "investigation_status": "active",
            "priority_level": "high",
            "target_platforms": ["twitter", "youtube", "telegram"]
        }
    )
    
    print("✓ Updated workspace content")
    
    # Get user workspaces
    user_workspaces = await workspace_manager.get_user_workspaces("analyst1")
    print(f"✓ Retrieved {len(user_workspaces)} workspaces for user")
    
    # Create template
    template_id = await workspace_manager.create_template(
        workspace_id=workspace.workspace_id,
        template_name="Disinformation Investigation Template",
        template_description="Standard template for disinformation investigations",
        created_by="analyst1"
    )
    
    print(f"✓ Created template: {template_id}")
    
    return workspace_manager, workspace.workspace_id

async def test_annotation_service():
    """Test collaborative annotation functionality"""
    print("\nTesting Annotation Service...")
    
    annotation_service = AnnotationService()
    
    # Create annotations
    annotation1 = await annotation_service.create_annotation(
        content_id="post_12345",
        workspace_id="workspace_1",
        annotation_type=AnnotationType.THREAT_LEVEL,
        value="high",
        created_by="analyst1"
    )
    
    annotation2 = await annotation_service.create_annotation(
        content_id="post_12345",
        workspace_id="workspace_1",
        annotation_type=AnnotationType.COMMENT,
        value="This post shows clear signs of coordinated behavior",
        created_by="analyst2"
    )
    
    print(f"✓ Created {len([annotation1, annotation2])} annotations")
    
    # Add reply
    reply = await annotation_service.add_reply(
        parent_annotation_id=annotation2.annotation_id,
        reply_content="I agree, the timing patterns are suspicious",
        user_id="analyst3"
    )
    
    print("✓ Added reply to annotation")
    
    # Vote on annotation
    await annotation_service.vote_on_annotation(
        annotation_id=annotation1.annotation_id,
        user_id="analyst2",
        vote="agree"
    )
    
    await annotation_service.vote_on_annotation(
        annotation_id=annotation1.annotation_id,
        user_id="analyst3",
        vote="agree"
    )
    
    print("✓ Added votes to annotation")
    
    # Get content annotations
    content_annotations = await annotation_service.get_content_annotations(
        content_id="post_12345",
        user_id="analyst1"
    )
    
    print(f"✓ Retrieved {len(content_annotations)} annotations for content")
    
    # Search annotations
    search_results = await annotation_service.search_annotations(
        workspace_id="workspace_1",
        user_id="analyst1",
        query="coordinated"
    )
    
    print(f"✓ Found {len(search_results)} annotations matching search")
    
    return annotation_service

async def test_case_management():
    """Test investigation case management"""
    print("\nTesting Case Management...")
    
    case_manager = CaseManager()
    
    # Create investigation case
    case = await case_manager.create_case(
        title="Coordinated Bot Network Investigation",
        description="Investigation into suspected bot network spreading disinformation",
        case_type=CaseType.BOT_NETWORK,
        priority=CasePriority.HIGH,
        created_by="analyst1",
        workspace_id="workspace_1",
        due_date=datetime.utcnow() + timedelta(days=7),
        tags={"bots", "disinformation", "urgent"}
    )
    
    print(f"✓ Created case: {case.title}")
    
    # Assign case
    await case_manager.assign_case(
        case_id=case.case_id,
        assigned_to="analyst2",
        assigned_by="analyst1",
        role="lead",
        notes="Lead analyst for bot detection"
    )
    
    await case_manager.assign_case(
        case_id=case.case_id,
        assigned_to="analyst3",
        assigned_by="analyst1",
        role="analyst",
        notes="Supporting analyst for data collection"
    )
    
    print(f"✓ Assigned case to {len(case.assignments)} analysts")
    
    # Add evidence
    evidence_id = await case_manager.add_evidence(
        case_id=case.case_id,
        evidence_type="user_profile",
        source_id="user_98765",
        description="Suspicious user profile with automated posting patterns",
        collected_by="analyst3",
        metadata={"bot_score": 0.92, "creation_date": "2024-01-15"},
        tags={"bot", "suspicious"}
    )
    
    print(f"✓ Added evidence: {evidence_id}")
    
    # Update case status
    await case_manager.update_case_status(
        case_id=case.case_id,
        new_status=CaseStatus.IN_PROGRESS,
        user_id="analyst2",
        notes="Started analysis of collected data"
    )
    
    print("✓ Updated case status")
    
    # Update findings
    await case_manager.update_case_findings(
        case_id=case.case_id,
        findings="Identified network of 50+ bot accounts with coordinated posting behavior",
        recommendations="Recommend platform notification and continued monitoring",
        confidence_score=0.88,
        updated_by="analyst2"
    )
    
    print("✓ Updated case findings")
    
    # Get user cases
    user_cases = await case_manager.get_user_cases("analyst1")
    print(f"✓ Retrieved {len(user_cases)} cases for user")
    
    return case_manager, case.case_id

async def test_team_coordination():
    """Test team coordination and notifications"""
    print("\nTesting Team Coordination...")
    
    team_coordinator = TeamCoordinator()
    
    # Create team
    team_id = await team_coordinator.create_team(
        team_name="Disinformation Analysis Team",
        team_description="Team focused on disinformation detection and analysis",
        created_by="analyst1",
        initial_members=["analyst1", "analyst2", "analyst3"]
    )
    
    print(f"✓ Created team: {team_id}")
    
    # Send notifications
    notification_id = await team_coordinator.send_notification(
        recipient_id="analyst2",
        notification_type=NotificationType.TASK_ASSIGNED,
        title="New Analysis Task",
        message="You have been assigned a new bot detection task",
        sender_id="analyst1",
        priority="high"
    )
    
    print(f"✓ Sent notification: {notification_id}")
    
    # Broadcast to team
    broadcast_ids = await team_coordinator.broadcast_to_team(
        team_id=team_id,
        notification_type=NotificationType.WORKFLOW_STARTED,
        title="Investigation Workflow Started",
        message="New disinformation investigation workflow has been initiated",
        sender_id="analyst1"
    )
    
    print(f"✓ Broadcast to team: {len(broadcast_ids)} notifications sent")
    
    # Mention user
    mention_id = await team_coordinator.mention_user(
        mentioned_user_id="analyst3",
        mentioning_user_id="analyst2",
        context="Please review the bot detection results",
        context_url="/workspace/analysis/bot-detection"
    )
    
    print(f"✓ Sent mention: {mention_id}")
    
    # Get user notifications
    notifications = await team_coordinator.get_user_notifications("analyst2")
    print(f"✓ Retrieved {len(notifications)} notifications for user")
    
    return team_coordinator, team_id

async def test_workflow_management():
    """Test workflow management"""
    print("\nTesting Workflow Management...")
    
    team_coordinator = TeamCoordinator()
    workflow_manager = WorkflowManager(team_coordinator)
    
    # Create workflow
    workflow = await workflow_manager.create_workflow(
        name="Bot Network Investigation Workflow",
        description="Standard workflow for investigating bot networks",
        created_by="analyst1",
        team_members=["analyst1", "analyst2", "analyst3"],
        deadline=datetime.utcnow() + timedelta(days=5)
    )
    
    print(f"✓ Created workflow: {workflow.name}")
    
    # Add tasks
    task1_id = await workflow_manager.add_task(
        workflow_id=workflow.workflow_id,
        task_name="Data Collection",
        task_description="Collect suspicious user profiles and posts",
        assigned_to="analyst3",
        estimated_hours=4.0
    )
    
    task2_id = await workflow_manager.add_task(
        workflow_id=workflow.workflow_id,
        task_name="Bot Analysis",
        task_description="Analyze collected data for bot indicators",
        assigned_to="analyst2",
        depends_on=[task1_id],
        estimated_hours=6.0
    )
    
    task3_id = await workflow_manager.add_task(
        workflow_id=workflow.workflow_id,
        task_name="Report Generation",
        task_description="Generate investigation report",
        assigned_to="analyst1",
        depends_on=[task2_id],
        estimated_hours=2.0
    )
    
    print(f"✓ Added {len([task1_id, task2_id, task3_id])} tasks to workflow")
    
    # Start workflow
    await workflow_manager.start_workflow(workflow.workflow_id, "analyst1")
    print("✓ Started workflow")
    
    # Complete first task
    await workflow_manager.complete_task(
        workflow_id=workflow.workflow_id,
        task_id=task1_id,
        completed_by="analyst3",
        result="Collected 150 suspicious profiles"
    )
    
    print("✓ Completed first task")
    
    return workflow_manager, workflow.workflow_id

async def test_knowledge_base():
    """Test knowledge base functionality"""
    print("\nTesting Knowledge Base...")
    
    knowledge_base = KnowledgeBase()
    
    # Create documents
    guide = await knowledge_base.create_document(
        title="Bot Detection Best Practices",
        content="""# Bot Detection Best Practices

## Overview
This guide outlines best practices for detecting automated accounts.

## Key Indicators
1. Posting frequency patterns
2. Content similarity
3. Account creation timing
4. Network connections

## Analysis Steps
1. Collect account metadata
2. Analyze posting patterns
3. Check content similarity
4. Map network connections
5. Calculate bot probability score
""",
        document_type=DocumentType.BEST_PRACTICE,
        created_by="analyst1",
        category="guides",
        tags={"bot-detection", "best-practices", "analysis"}
    )
    
    template = await knowledge_base.create_template(
        title="Investigation Report Template",
        content="""# Investigation Report - {case_title}

## Executive Summary
{executive_summary}

## Methodology
{methodology}

## Key Findings
{key_findings}

## Evidence Summary
{evidence_summary}

## Recommendations
{recommendations}

## Conclusion
{conclusion}

---
Generated: {timestamp}
Analyst: {analyst_name}
""",
        created_by="analyst1",
        template_type="investigation_report",
        tags={"template", "investigation", "report"}
    )
    
    print(f"✓ Created documents: guide and template")
    
    # Add comments
    comment_id = await knowledge_base.add_comment(
        document_id=guide.document_id,
        user_id="analyst2",
        content="Great guide! Should we add a section on temporal analysis?"
    )
    
    print(f"✓ Added comment: {comment_id}")
    
    # Update document
    await knowledge_base.update_document(
        document_id=guide.document_id,
        user_id="analyst1",
        content=guide.content + "\n\n## Temporal Analysis\n5. Analyze posting time patterns\n6. Check for coordinated timing",
        change_summary="Added temporal analysis section"
    )
    
    print("✓ Updated document")
    
    # Search documents
    search_results = await knowledge_base.search_documents(
        user_id="analyst1",
        query="bot detection",
        document_types=[DocumentType.BEST_PRACTICE, DocumentType.GUIDE]
    )
    
    print(f"✓ Found {len(search_results)} documents in search")
    
    # Get templates
    templates = await knowledge_base.get_templates(
        user_id="analyst1",
        template_type="investigation_report"
    )
    
    print(f"✓ Retrieved {len(templates)} templates")
    
    return knowledge_base, guide.document_id, template.document_id

async def test_documentation_manager():
    """Test documentation management"""
    print("\nTesting Documentation Manager...")
    
    knowledge_base = KnowledgeBase()
    doc_manager = DocumentationManager(knowledge_base)
    
    # Create documentation workflow
    workflow_id = await doc_manager.create_documentation_workflow(
        workflow_name="Investigation Documentation Process",
        document_types=[DocumentType.ANALYSIS_REPORT, DocumentType.INVESTIGATION_NOTES],
        required_reviewers=2,
        approval_required=True,
        created_by="analyst1"
    )
    
    print(f"✓ Created documentation workflow: {workflow_id}")
    
    # Generate analysis report
    analysis_data = {
        "title": "Bot Network Analysis",
        "summary": "Analysis of coordinated bot network spreading disinformation",
        "methodology": "Behavioral analysis and network mapping",
        "findings": "Identified 75 bot accounts with coordinated behavior",
        "recommendations": "Platform notification and continued monitoring",
        "sources": ["Twitter API", "Manual Analysis", "Network Analysis"]
    }
    
    report = await doc_manager.generate_analysis_report(
        analysis_data=analysis_data,
        created_by="analyst2",
        workspace_id="workspace_1"
    )
    
    print(f"✓ Generated analysis report: {report.title}")
    
    # Create investigation notes
    notes = await doc_manager.create_investigation_notes(
        case_id="case_12345",
        findings="Bot network shows clear coordination patterns",
        evidence_summary="150 suspicious accounts, 500+ coordinated posts",
        created_by="analyst3",
        workspace_id="workspace_1"
    )
    
    print(f"✓ Created investigation notes: {notes.title}")
    
    return doc_manager, report.document_id, notes.document_id

async def test_integration():
    """Test integration between collaboration components"""
    print("\nTesting Integration...")
    
    # Create integrated workflow
    workspace_manager = WorkspaceManager()
    annotation_service = AnnotationService(workspace_manager=workspace_manager)
    case_manager = CaseManager(workspace_manager=workspace_manager)
    team_coordinator = TeamCoordinator()
    knowledge_base = KnowledgeBase()
    
    # Create workspace
    workspace = await workspace_manager.create_workspace(
        name="Integrated Investigation Workspace",
        description="Full-featured investigation workspace",
        workspace_type=WorkspaceType.INVESTIGATION,
        owner_id="lead_analyst",
        owner_username="Lead Analyst",
        owner_email="lead@dharma.gov"
    )
    
    # Add team members
    await workspace_manager.add_member(
        workspace_id=workspace.workspace_id,
        user_id="analyst_a",
        username="Analyst A",
        email="a@dharma.gov",
        access_level=AccessLevel.EDITOR,
        added_by="lead_analyst"
    )
    
    # Create case in workspace
    case = await case_manager.create_case(
        title="Integrated Investigation Case",
        description="Test case for integrated workflow",
        case_type=CaseType.COORDINATED_CAMPAIGN,
        priority=CasePriority.HIGH,
        created_by="lead_analyst",
        workspace_id=workspace.workspace_id
    )
    
    # Add annotations to content
    annotation = await annotation_service.create_annotation(
        content_id="content_123",
        workspace_id=workspace.workspace_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        value="disinformation",
        created_by="analyst_a"
    )
    
    # Create knowledge document
    doc = await knowledge_base.create_document(
        title="Investigation Findings",
        content="Detailed findings from the integrated investigation",
        document_type=DocumentType.INVESTIGATION_NOTES,
        created_by="lead_analyst",
        workspace_id=workspace.workspace_id
    )
    
    print("✓ Created integrated workflow with workspace, case, annotations, and documentation")
    
    return {
        'workspace_id': workspace.workspace_id,
        'case_id': case.case_id,
        'annotation_id': annotation.annotation_id,
        'document_id': doc.document_id
    }

async def main():
    """Run all collaboration feature tests"""
    print("🚀 Testing Project Dharma Collaboration Features\n")
    
    try:
        # Test individual components
        workspace_manager, workspace_id = await test_workspace_management()
        annotation_service = await test_annotation_service()
        case_manager, case_id = await test_case_management()
        team_coordinator, team_id = await test_team_coordination()
        workflow_manager, workflow_id = await test_workflow_management()
        knowledge_base, guide_id, template_id = await test_knowledge_base()
        doc_manager, report_id, notes_id = await test_documentation_manager()
        
        # Test integration
        integration_results = await test_integration()
        
        print("\n📊 Test Summary:")
        print("✅ Workspace Management - PASSED")
        print("✅ Annotation Service - PASSED")
        print("✅ Case Management - PASSED")
        print("✅ Team Coordination - PASSED")
        print("✅ Workflow Management - PASSED")
        print("✅ Knowledge Base - PASSED")
        print("✅ Documentation Manager - PASSED")
        print("✅ Integration Tests - PASSED")
        
        print("\n🎉 All collaboration features are working correctly!")
        
        # Print statistics
        print("\n📈 Statistics:")
        workspace_stats = workspace_manager.get_workspace_stats()
        print(f"Workspaces: {workspace_stats['total_workspaces']} total, {workspace_stats['active_workspaces']} active")
        
        annotation_stats = annotation_service.get_annotation_stats()
        print(f"Annotations: {annotation_stats['total_annotations']} total, {annotation_stats['unique_annotators']} contributors")
        
        case_analytics = await case_manager.get_case_analytics()
        print(f"Cases: {case_analytics['total_cases']} total, {case_analytics['active_cases']} active")
        
        team_stats = team_coordinator.get_team_stats()
        print(f"Teams: {team_stats['total_teams']} total, {team_stats['total_members']} members")
        
        workflow_stats = workflow_manager.get_workflow_stats()
        print(f"Workflows: {workflow_stats['total_workflows']} total, {workflow_stats['active_workflows']} active")
        
        kb_stats = knowledge_base.get_knowledge_base_stats()
        print(f"Knowledge Base: {kb_stats['total_documents']} documents, {kb_stats['total_views']} views")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)