"""
Event Bus Service - Main application
"""
import asyncio
import logging
import signal
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from .core.event_bus import EventBus
from .workflows.orchestrator import WorkflowOrchestrator
from .monitoring.workflow_monitor import WorkflowMonitor, ErrorRecoveryManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
event_bus = None
orchestrator = None
monitor = None
recovery_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global event_bus, orchestrator, monitor, recovery_manager
    
    # Startup
    logger.info("Starting Event Bus Service...")
    
    # Initialize Kafka configuration
    kafka_config = {
        "bootstrap_servers": ["localhost:9092"]
    }
    
    # Initialize services
    event_bus = EventBus(kafka_config)
    await event_bus.initialize()
    
    orchestrator = WorkflowOrchestrator("localhost:7233")
    await orchestrator.initialize()
    
    monitor = WorkflowMonitor(orchestrator.client)
    await monitor.start_monitoring()
    
    recovery_manager = ErrorRecoveryManager(monitor, orchestrator)
    
    # Register event handlers
    await setup_event_handlers()
    
    logger.info("Event Bus Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Event Bus Service...")
    
    if monitor:
        await monitor.stop_monitoring()
    
    if event_bus:
        await event_bus.shutdown()
    
    logger.info("Event Bus Service shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Event Bus Service",
    description="Handles cross-service communication and workflow orchestration",
    version="1.0.0",
    lifespan=lifespan
)

async def setup_event_handlers():
    """Setup event handlers for different topics"""
    
    # Data collection events
    await event_bus.subscribe_to_events(
        topics=["data.collected"],
        group_id="data_processing_group",
        handler=handle_data_collected
    )
    
    # Analysis completion events
    await event_bus.subscribe_to_events(
        topics=["analysis.completed"],
        group_id="analysis_processing_group", 
        handler=handle_analysis_completed
    )
    
    # Campaign detection events
    await event_bus.subscribe_to_events(
        topics=["campaign.detected"],
        group_id="campaign_processing_group",
        handler=handle_campaign_detected
    )

async def handle_data_collected(topic: str, event):
    """Handle data collection events"""
    logger.info(f"Handling data collected event: {event.event_id}")
    
    try:
        # Start data processing workflow
        workflow_id = await orchestrator.start_data_processing_workflow(
            data_source=event.data.get("source", "unknown"),
            parameters=event.data.get("parameters", {})
        )
        
        # Register workflow for monitoring
        await monitor.register_workflow(workflow_id)
        
        logger.info(f"Started data processing workflow: {workflow_id}")
        
    except Exception as e:
        logger.error(f"Failed to handle data collected event: {e}")

async def handle_analysis_completed(topic: str, event):
    """Handle analysis completion events"""
    logger.info(f"Handling analysis completed event: {event.event_id}")
    
    # Publish downstream event for alert generation
    await event_bus.publish_event(
        topic="alerts.check",
        event_type="analysis_ready",
        data=event.data,
        source_service="event_bus",
        correlation_id=event.correlation_id
    )

async def handle_campaign_detected(topic: str, event):
    """Handle campaign detection events"""
    logger.info(f"Handling campaign detected event: {event.event_id}")
    
    # Publish high-priority alert event
    await event_bus.publish_event(
        topic="alerts.urgent",
        event_type="campaign_detected",
        data={
            "campaign_id": event.data.get("campaign_id"),
            "severity": "high",
            "detection_time": event.timestamp
        },
        source_service="event_bus",
        correlation_id=event.correlation_id
    )

# API Endpoints
@app.post("/api/v1/events/publish")
async def publish_event(event_data: Dict[str, Any]):
    """Publish event to event bus"""
    try:
        event_id = await event_bus.publish_event(
            topic=event_data["topic"],
            event_type=event_data["event_type"],
            data=event_data["data"],
            source_service=event_data.get("source_service", "api"),
            correlation_id=event_data.get("correlation_id")
        )
        
        return {"event_id": event_id, "status": "published"}
        
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/workflows/start")
async def start_workflow(workflow_request: Dict[str, Any]):
    """Start a new workflow"""
    try:
        workflow_type = workflow_request.get("type")
        parameters = workflow_request.get("parameters", {})
        
        if workflow_type == "data_processing":
            workflow_id = await orchestrator.start_data_processing_workflow(
                data_source=parameters.get("data_source", "unknown"),
                parameters=parameters
            )
        elif workflow_type == "model_retraining":
            workflow_id = await orchestrator.start_model_retraining_workflow(
                model_type=parameters.get("model_type", "sentiment"),
                training_data=parameters.get("training_data", {})
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown workflow type: {workflow_type}")
        
        # Register for monitoring
        await monitor.register_workflow(workflow_id)
        
        return {"workflow_id": workflow_id, "status": "started"}
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    try:
        status = await orchestrator.get_workflow_status(workflow_id)
        metrics = await monitor.get_workflow_metrics(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": status,
            "metrics": metrics.__dict__ if metrics else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow"""
    try:
        await orchestrator.cancel_workflow(workflow_id, "User requested cancellation")
        return {"workflow_id": workflow_id, "status": "cancelled"}
        
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows/active")
async def get_active_workflows():
    """Get list of active workflows"""
    try:
        active_workflows = await monitor.get_active_workflows()
        return {"active_workflows": active_workflows}
        
    except Exception as e:
        logger.error(f"Failed to get active workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics/workflows")
async def get_workflow_metrics():
    """Get metrics for all workflows"""
    try:
        metrics = await monitor.get_all_metrics()
        
        # Convert metrics to serializable format
        serializable_metrics = {}
        for workflow_id, metric in metrics.items():
            serializable_metrics[workflow_id] = {
                "workflow_id": metric.workflow_id,
                "status": metric.status.value,
                "start_time": metric.start_time.isoformat(),
                "end_time": metric.end_time.isoformat() if metric.end_time else None,
                "duration": str(metric.duration) if metric.duration else None,
                "steps_completed": metric.steps_completed,
                "steps_failed": metric.steps_failed,
                "error_count": metric.error_count,
                "retry_count": metric.retry_count
            }
        
        return {"metrics": serializable_metrics}
        
    except Exception as e:
        logger.error(f"Failed to get workflow metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "event-bus-service",
        "timestamp": asyncio.get_event_loop().time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)