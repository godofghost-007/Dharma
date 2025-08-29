"""
Basic tests for Event Bus Service components
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

def test_event_creation():
    """Test basic Event creation"""
    from app.core.event_bus import Event
    
    event = Event(
        event_id="test-123",
        event_type="test_event",
        source_service="test_service",
        timestamp=datetime.utcnow().isoformat(),
        data={"key": "value"}
    )
    
    assert event.event_id == "test-123"
    assert event.event_type == "test_event"
    assert event.source_service == "test_service"
    assert event.data == {"key": "value"}

def test_workflow_step_creation():
    """Test WorkflowStep creation"""
    from app.workflows.orchestrator import WorkflowStep
    
    step = WorkflowStep(
        step_id="test_step",
        service="test_service",
        action="test_action",
        parameters={"param": "value"}
    )
    
    assert step.step_id == "test_step"
    assert step.service == "test_service"
    assert step.action == "test_action"
    assert step.parameters == {"param": "value"}

def test_workflow_definition_creation():
    """Test WorkflowDefinition creation"""
    from app.workflows.orchestrator import WorkflowDefinition, WorkflowStep
    
    steps = [
        WorkflowStep(
            step_id="step1",
            service="service1",
            action="action1",
            parameters={}
        )
    ]
    
    workflow_def = WorkflowDefinition(
        workflow_id="test_workflow",
        name="Test Workflow",
        description="Test description",
        steps=steps
    )
    
    assert workflow_def.workflow_id == "test_workflow"
    assert workflow_def.name == "Test Workflow"
    assert len(workflow_def.steps) == 1

def test_workflow_status_enum():
    """Test WorkflowStatus enum"""
    from app.monitoring.workflow_monitor import WorkflowStatus
    
    assert WorkflowStatus.RUNNING.value == "running"
    assert WorkflowStatus.COMPLETED.value == "completed"
    assert WorkflowStatus.FAILED.value == "failed"

def test_workflow_metrics_creation():
    """Test WorkflowMetrics creation"""
    from app.monitoring.workflow_monitor import WorkflowMetrics, WorkflowStatus
    
    metrics = WorkflowMetrics(
        workflow_id="test_workflow",
        status=WorkflowStatus.RUNNING,
        start_time=datetime.utcnow()
    )
    
    assert metrics.workflow_id == "test_workflow"
    assert metrics.status == WorkflowStatus.RUNNING
    assert metrics.steps_completed == 0
    assert metrics.steps_failed == 0

if __name__ == "__main__":
    pytest.main([__file__])