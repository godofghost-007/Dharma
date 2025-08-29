"""
Simple tests for Event Bus Service components without external dependencies
"""
import pytest
from datetime import datetime
from unittest.mock import Mock

def test_event_creation():
    """Test basic Event creation"""
    from app.core.event_bus import Event
    
    event = Event(
        event_id="test-123",
        event_type="test_event",
        source_service="test_service",
        timestamp=datetime.now().isoformat(),
        data={"key": "value"}
    )
    
    assert event.event_id == "test-123"
    assert event.event_type == "test_event"
    assert event.source_service == "test_service"
    assert event.data == {"key": "value"}
    
    # Test to_dict method
    event_dict = event.to_dict()
    assert event_dict["event_id"] == "test-123"
    assert event_dict["event_type"] == "test_event"

def test_workflow_status_enum():
    """Test WorkflowStatus enum"""
    from app.monitoring.workflow_monitor import WorkflowStatus
    
    assert WorkflowStatus.RUNNING.value == "running"
    assert WorkflowStatus.COMPLETED.value == "completed"
    assert WorkflowStatus.FAILED.value == "failed"
    assert WorkflowStatus.CANCELLED.value == "cancelled"
    assert WorkflowStatus.TIMEOUT.value == "timeout"

def test_workflow_metrics_creation():
    """Test WorkflowMetrics creation"""
    from app.monitoring.workflow_monitor import WorkflowMetrics, WorkflowStatus
    
    metrics = WorkflowMetrics(
        workflow_id="test_workflow",
        status=WorkflowStatus.RUNNING,
        start_time=datetime.now()
    )
    
    assert metrics.workflow_id == "test_workflow"
    assert metrics.status == WorkflowStatus.RUNNING
    assert metrics.steps_completed == 0
    assert metrics.steps_failed == 0
    assert metrics.error_count == 0
    assert metrics.retry_count == 0

def test_event_bus_initialization():
    """Test EventBus initialization"""
    from app.core.event_bus import EventBus
    
    kafka_config = {
        "bootstrap_servers": ["localhost:9092"]
    }
    
    event_bus = EventBus(kafka_config)
    
    assert event_bus.kafka_config == kafka_config
    assert event_bus.producer is None  # Not initialized yet
    assert event_bus.consumers == {}
    assert event_bus.event_handlers == {}
    assert event_bus.running is False

@pytest.mark.asyncio
async def test_workflow_monitor_initialization():
    """Test WorkflowMonitor initialization"""
    from app.monitoring.workflow_monitor import WorkflowMonitor
    
    mock_client = Mock()
    monitor = WorkflowMonitor(mock_client)
    
    assert monitor.client == mock_client
    assert monitor.active_workflows == {}
    assert monitor.workflow_metrics == {}
    assert monitor.monitoring_active is False

@pytest.mark.asyncio
async def test_workflow_monitor_register_workflow():
    """Test workflow registration"""
    from app.monitoring.workflow_monitor import WorkflowMonitor, WorkflowStatus
    
    mock_client = Mock()
    monitor = WorkflowMonitor(mock_client)
    
    workflow_id = "test_workflow_123"
    await monitor.register_workflow(workflow_id)
    
    assert workflow_id in monitor.active_workflows
    assert workflow_id in monitor.workflow_metrics
    assert monitor.workflow_metrics[workflow_id].status == WorkflowStatus.RUNNING
    assert monitor.workflow_metrics[workflow_id].workflow_id == workflow_id

if __name__ == "__main__":
    pytest.main([__file__])