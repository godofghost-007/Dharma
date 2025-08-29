"""
Tests for Event Bus Service
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.core.event_bus import EventBus, Event
from app.workflows.orchestrator import WorkflowOrchestrator, WorkflowDefinition, WorkflowStep
from app.monitoring.workflow_monitor import WorkflowMonitor, WorkflowStatus, WorkflowMetrics

@pytest.fixture
def kafka_config():
    return {
        "bootstrap_servers": ["localhost:9092"]
    }

@pytest.fixture
def mock_kafka_producer():
    with patch('app.core.event_bus.KafkaProducer') as mock:
        producer = Mock()
        producer.send.return_value.get.return_value = Mock(topic="test", partition=0, offset=1)
        mock.return_value = producer
        yield producer

@pytest.fixture
def mock_kafka_consumer():
    with patch('app.core.event_bus.KafkaConsumer') as mock:
        consumer = Mock()
        consumer.poll.return_value = {}
        mock.return_value = consumer
        yield consumer

@pytest.fixture
def event_bus(kafka_config, mock_kafka_producer):
    return EventBus(kafka_config)

@pytest.fixture
def sample_event():
    return Event(
        event_id="test-event-123",
        event_type="test_event",
        source_service="test_service",
        timestamp=datetime.utcnow().isoformat(),
        data={"key": "value"},
        correlation_id="corr-123"
    )

class TestEventBus:
    """Test Event Bus functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize_event_bus(self, event_bus, mock_kafka_producer):
        """Test event bus initialization"""
        await event_bus.initialize()
        
        assert event_bus.producer is not None
        mock_kafka_producer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus, mock_kafka_producer):
        """Test event publishing"""
        await event_bus.initialize()
        
        event_id = await event_bus.publish_event(
            topic="test_topic",
            event_type="test_event",
            data={"test": "data"},
            source_service="test_service"
        )
        
        assert event_id is not None
        mock_kafka_producer.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_subscribe_to_events(self, event_bus, mock_kafka_consumer):
        """Test event subscription"""
        handler = AsyncMock()
        
        await event_bus.subscribe_to_events(
            topics=["test_topic"],
            group_id="test_group",
            handler=handler
        )
        
        assert "test_group" in event_bus.consumers
        assert "test_group" in event_bus.event_handlers
        mock_kafka_consumer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_event_processing_error_handling(self, event_bus):
        """Test error handling in event processing"""
        error = Exception("Test error")
        message = Mock()
        message.value = {"test": "data"}
        message.topic = "test_topic"
        message.partition = 0
        message.offset = 1
        
        with patch.object(event_bus, 'publish_event') as mock_publish:
            await event_bus._handle_event_processing_error(error, message, "test_group")
            
            mock_publish.assert_called_once()
            call_args = mock_publish.call_args
            assert call_args[1]["topic"] == "events.dead_letter"
            assert call_args[1]["event_type"] == "event_processing_error"

class TestWorkflowOrchestrator:
    """Test Workflow Orchestrator functionality"""
    
    @pytest.fixture
    def mock_temporal_client(self):
        with patch('app.workflows.orchestrator.Client') as mock:
            client = AsyncMock()
            mock.connect.return_value = client
            yield client
    
    @pytest.fixture
    def orchestrator(self, mock_temporal_client):
        return WorkflowOrchestrator("localhost:7233")
    
    @pytest.mark.asyncio
    async def test_initialize_orchestrator(self, orchestrator, mock_temporal_client):
        """Test orchestrator initialization"""
        await orchestrator.initialize()
        
        assert orchestrator.client is not None
    
    @pytest.mark.asyncio
    async def test_register_workflow(self, orchestrator):
        """Test workflow registration"""
        workflow_def = WorkflowDefinition(
            workflow_id="test_workflow",
            name="Test Workflow",
            description="Test workflow description",
            steps=[
                WorkflowStep(
                    step_id="step1",
                    service="test_service",
                    action="test_action",
                    parameters={"param": "value"}
                )
            ]
        )
        
        await orchestrator.register_workflow(workflow_def)
        
        assert "test_workflow" in orchestrator.workflows
        assert orchestrator.workflows["test_workflow"] == workflow_def
    
    @pytest.mark.asyncio
    async def test_start_data_processing_workflow(self, orchestrator, mock_temporal_client):
        """Test starting data processing workflow"""
        await orchestrator.initialize()
        
        # Mock workflow handle
        handle = Mock()
        handle.id = "workflow_123"
        mock_temporal_client.start_workflow.return_value = handle
        
        workflow_id = await orchestrator.start_data_processing_workflow(
            data_source="twitter",
            parameters={"keywords": ["test"]}
        )
        
        assert workflow_id == "workflow_123"
        mock_temporal_client.start_workflow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(self, orchestrator, mock_temporal_client):
        """Test getting workflow status"""
        await orchestrator.initialize()
        
        # Mock workflow handle and description
        handle = Mock()
        description = Mock()
        description.status = "WORKFLOW_EXECUTION_STATUS_RUNNING"
        description.start_time = datetime.utcnow()
        description.execution_time = timedelta(minutes=5)
        description.close_time = None
        
        handle.describe.return_value = description
        mock_temporal_client.get_workflow_handle.return_value = handle
        
        status = await orchestrator.get_workflow_status("test_workflow")
        
        assert status["workflow_id"] == "test_workflow"
        assert status["status"] == "WORKFLOW_EXECUTION_STATUS_RUNNING"

class TestWorkflowMonitor:
    """Test Workflow Monitor functionality"""
    
    @pytest.fixture
    def mock_temporal_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def monitor(self, mock_temporal_client):
        return WorkflowMonitor(mock_temporal_client)
    
    @pytest.mark.asyncio
    async def test_register_workflow(self, monitor):
        """Test workflow registration for monitoring"""
        workflow_id = "test_workflow_123"
        
        await monitor.register_workflow(workflow_id)
        
        assert workflow_id in monitor.active_workflows
        assert workflow_id in monitor.workflow_metrics
        assert monitor.workflow_metrics[workflow_id].status == WorkflowStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_workflow_health_check(self, monitor, mock_temporal_client):
        """Test workflow health checking"""
        workflow_id = "test_workflow_123"
        await monitor.register_workflow(workflow_id)
        
        # Mock workflow handle and description
        handle = Mock()
        description = Mock()
        description.status = "WORKFLOW_EXECUTION_STATUS_COMPLETED"
        description.close_time = datetime.utcnow()
        
        handle.describe.return_value = description
        mock_temporal_client.get_workflow_handle.return_value = handle
        
        await monitor._check_workflow_health(workflow_id)
        
        # Workflow should be removed from active monitoring after completion
        assert workflow_id not in monitor.active_workflows
    
    @pytest.mark.asyncio
    async def test_stuck_workflow_detection(self, monitor):
        """Test detection of stuck workflows"""
        workflow_id = "stuck_workflow_123"
        
        # Register workflow with old timestamp
        await monitor.register_workflow(workflow_id)
        monitor.active_workflows[workflow_id]["registered_at"] = datetime.utcnow() - timedelta(hours=3)
        
        is_stuck = await monitor._is_workflow_stuck(workflow_id)
        
        assert is_stuck is True
    
    @pytest.mark.asyncio
    async def test_get_workflow_metrics(self, monitor):
        """Test getting workflow metrics"""
        workflow_id = "test_workflow_123"
        await monitor.register_workflow(workflow_id)
        
        metrics = await monitor.get_workflow_metrics(workflow_id)
        
        assert metrics is not None
        assert metrics.workflow_id == workflow_id
        assert metrics.status == WorkflowStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_get_active_workflows(self, monitor):
        """Test getting active workflows list"""
        workflow_ids = ["workflow_1", "workflow_2", "workflow_3"]
        
        for workflow_id in workflow_ids:
            await monitor.register_workflow(workflow_id)
        
        active_workflows = await monitor.get_active_workflows()
        
        assert len(active_workflows) == 3
        assert all(wid in active_workflows for wid in workflow_ids)

if __name__ == "__main__":
    pytest.main([__file__])