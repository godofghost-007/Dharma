"""
Integration tests for workflow client
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import aiohttp

@pytest.mark.asyncio
async def test_workflow_client_initialization():
    """Test WorkflowClient initialization"""
    from app.orchestration.workflow_client import WorkflowClient
    
    client = WorkflowClient("http://localhost:8005")
    
    assert client.event_bus_url == "http://localhost:8005"
    assert client.session is None  # Not initialized yet

@pytest.mark.asyncio
async def test_workflow_client_session_management():
    """Test session initialization and shutdown"""
    from app.orchestration.workflow_client import WorkflowClient
    
    client = WorkflowClient("http://localhost:8005")
    
    # Initialize
    await client.initialize()
    assert client.session is not None
    assert isinstance(client.session, aiohttp.ClientSession)
    
    # Shutdown
    await client.shutdown()

@pytest.mark.asyncio
async def test_publish_event_success():
    """Test successful event publishing"""
    from app.orchestration.workflow_client import WorkflowClient
    
    client = WorkflowClient("http://localhost:8005")
    
    # Mock the session and response
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"event_id": "test-event-123"}
    
    mock_session.post.return_value.__aenter__.return_value = mock_response
    client.session = mock_session
    
    # Test event publishing
    event_id = await client.publish_event(
        topic="test.topic",
        event_type="test_event",
        data={"key": "value"},
        correlation_id="corr-123"
    )
    
    assert event_id == "test-event-123"
    mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_start_workflow_success():
    """Test successful workflow start"""
    from app.orchestration.workflow_client import WorkflowClient
    
    client = WorkflowClient("http://localhost:8005")
    
    # Mock the session and response
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"workflow_id": "workflow-123"}
    
    mock_session.post.return_value.__aenter__.return_value = mock_response
    client.session = mock_session
    
    # Test workflow start
    workflow_id = await client.start_workflow(
        workflow_type="data_processing",
        parameters={"source": "twitter"}
    )
    
    assert workflow_id == "workflow-123"
    mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_get_workflow_status_success():
    """Test successful workflow status retrieval"""
    from app.orchestration.workflow_client import WorkflowClient
    
    client = WorkflowClient("http://localhost:8005")
    
    # Mock the session and response
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "workflow_id": "workflow-123",
        "status": "running"
    }
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    client.session = mock_session
    
    # Test status retrieval
    status = await client.get_workflow_status("workflow-123")
    
    assert status["workflow_id"] == "workflow-123"
    assert status["status"] == "running"
    mock_session.get.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_workflow_success():
    """Test successful workflow cancellation"""
    from app.orchestration.workflow_client import WorkflowClient
    
    client = WorkflowClient("http://localhost:8005")
    
    # Mock the session and response
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    
    mock_session.post.return_value.__aenter__.return_value = mock_response
    client.session = mock_session
    
    # Test workflow cancellation
    success = await client.cancel_workflow("workflow-123")
    
    assert success is True
    mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in workflow client"""
    from app.orchestration.workflow_client import WorkflowClient
    
    client = WorkflowClient("http://localhost:8005")
    
    # Mock the session to raise an exception
    mock_session = AsyncMock()
    mock_session.post.side_effect = Exception("Connection error")
    client.session = mock_session
    
    # Test that exceptions are properly raised
    with pytest.raises(Exception, match="Connection error"):
        await client.publish_event(
            topic="test.topic",
            event_type="test_event",
            data={"key": "value"}
        )

if __name__ == "__main__":
    pytest.main([__file__])