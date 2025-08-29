"""
Tests for workflow types and basic functionality
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
    from app.monitoring.workflow_types import WorkflowStatus
    
    assert WorkflowStatus.RUNNING.value == "running"
    assert WorkflowStatus.COMPLETED.value == "completed"
    assert WorkflowStatus.FAILED.value == "failed"
    assert WorkflowStatus.CANCELLED.value == "cancelled"
    assert WorkflowStatus.TIMEOUT.value == "timeout"

def test_workflow_metrics_creation():
    """Test WorkflowMetrics creation"""
    from app.monitoring.workflow_types import WorkflowMetrics, WorkflowStatus
    
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

def test_config_loading():
    """Test configuration loading"""
    from app.core.config import EventBusConfig, get_kafka_config, get_temporal_config
    
    config = EventBusConfig()
    
    assert config.service_name == "event-bus-service"
    assert config.service_port == 8005
    assert config.kafka_bootstrap_servers == ["localhost:9092"]
    assert config.temporal_host == "localhost:7233"
    
    kafka_config = get_kafka_config()
    assert "bootstrap_servers" in kafka_config
    assert "producer_config" in kafka_config
    assert "consumer_config" in kafka_config
    
    temporal_config = get_temporal_config()
    assert "host" in temporal_config
    assert "namespace" in temporal_config
    assert "task_queue" in temporal_config

if __name__ == "__main__":
    pytest.main([__file__])