"""
Workflow client for stream processing service
"""
import asyncio
import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class WorkflowClient:
    """Client for interacting with event bus workflow orchestration"""
    
    def __init__(self, event_bus_url: str = "http://localhost:8005"):
        self.event_bus_url = event_bus_url
        self.session = None
        
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        
    async def shutdown(self):
        """Shutdown HTTP session"""
        if self.session:
            await self.session.close()
    
    async def publish_event(self, topic: str, event_type: str, data: Dict[str, Any], 
                          correlation_id: Optional[str] = None) -> str:
        """Publish event to event bus"""
        if not self.session:
            raise RuntimeError("Workflow client not initialized")
            
        event_data = {
            "topic": topic,
            "event_type": event_type,
            "data": data,
            "source_service": "stream_processing",
            "correlation_id": correlation_id
        }
        
        try:
            async with self.session.post(
                f"{self.event_bus_url}/api/v1/events/publish",
                json=event_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Published event {event_type} to {topic}: {result['event_id']}")
                    return result["event_id"]
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to publish event: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error publishing event to {topic}: {e}")
            raise
    
    async def start_workflow(self, workflow_type: str, parameters: Dict[str, Any]) -> str:
        """Start a new workflow"""
        if not self.session:
            raise RuntimeError("Workflow client not initialized")
            
        workflow_request = {
            "type": workflow_type,
            "parameters": parameters
        }
        
        try:
            async with self.session.post(
                f"{self.event_bus_url}/api/v1/workflows/start",
                json=workflow_request
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Started workflow {workflow_type}: {result['workflow_id']}")
                    return result["workflow_id"]
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to start workflow: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error starting workflow {workflow_type}: {e}")
            raise
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status"""
        if not self.session:
            raise RuntimeError("Workflow client not initialized")
            
        try:
            async with self.session.get(
                f"{self.event_bus_url}/api/v1/workflows/{workflow_id}/status"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get workflow status: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting workflow status for {workflow_id}: {e}")
            raise
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        if not self.session:
            raise RuntimeError("Workflow client not initialized")
            
        try:
            async with self.session.post(
                f"{self.event_bus_url}/api/v1/workflows/{workflow_id}/cancel"
            ) as response:
                if response.status == 200:
                    logger.info(f"Cancelled workflow: {workflow_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to cancel workflow: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error cancelling workflow {workflow_id}: {e}")
            return False