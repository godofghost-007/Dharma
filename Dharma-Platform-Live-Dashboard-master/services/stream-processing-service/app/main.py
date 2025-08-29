"""
Stream Processing Service - Main application
"""
import asyncio
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import structlog

from app.core.kafka_config import KafkaStreamConfig, KafkaTopicManager
from app.core.stream_processor import StreamProcessor, StreamTopology
from app.core.kafka_clients import KafkaHealthChecker
from app.orchestration.workflow_client import WorkflowClient

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global variables for service components
stream_processor = None
stream_topology = None
kafka_config = None
processing_task = None
workflow_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global stream_processor, stream_topology, kafka_config, processing_task, workflow_client
    
    try:
        # Initialize Kafka configuration
        kafka_config = KafkaStreamConfig()
        logger.info("Initializing stream processing service")
        
        # Initialize workflow client
        import os
        event_bus_url = os.getenv("EVENT_BUS_URL", "http://localhost:8005")
        workflow_client = WorkflowClient(event_bus_url)
        await workflow_client.initialize()
        
        # Initialize stream processor
        stream_processor = StreamProcessor(kafka_config)
        await stream_processor.initialize()
        
        # Build stream topology
        stream_topology = StreamTopology(stream_processor)
        stream_topology.build_topology()
        
        # Start stream processing in background
        topics_to_process = [
            kafka_config.topic_prefix + ".raw.twitter",
            kafka_config.topic_prefix + ".raw.youtube",
            kafka_config.topic_prefix + ".raw.web",
            kafka_config.topic_prefix + ".raw.telegram",
            kafka_config.topic_prefix + ".analysis.sentiment",
            kafka_config.topic_prefix + ".analysis.bot_detection",
            kafka_config.topic_prefix + ".analysis.campaign_detection"
        ]
        
        processing_task = asyncio.create_task(
            stream_processor.start_processing(topics_to_process)
        )
        
        logger.info("Stream processing service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start stream processing service", error=str(e))
        raise
    finally:
        # Cleanup
        logger.info("Shutting down stream processing service")
        
        if processing_task:
            processing_task.cancel()
            try:
                await processing_task
            except asyncio.CancelledError:
                pass
        
        if stream_processor:
            await stream_processor.stop_processing()
        
        if workflow_client:
            await workflow_client.shutdown()
        
        logger.info("Stream processing service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Stream Processing Service",
    description="Real-time data processing pipeline for Project Dharma",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if not kafka_config:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Check Kafka health
        health_checker = KafkaHealthChecker(kafka_config)
        kafka_health = await health_checker.check_kafka_health()
        
        # Check stream processor status
        processor_status = {
            "initialized": stream_processor is not None,
            "running": stream_processor.running if stream_processor else False
        }
        
        health_status = {
            "status": "healthy" if kafka_health["kafka_available"] and processor_status["running"] else "unhealthy",
            "kafka": kafka_health,
            "processor": processor_status,
            "topics": list(stream_processor.topic_manager.topics.values()) if stream_processor else []
        }
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


@app.get("/metrics")
async def get_metrics():
    """Get processing metrics"""
    try:
        if not stream_processor:
            raise HTTPException(status_code=503, detail="Stream processor not initialized")
        
        # Get metrics from producer and consumer
        metrics = {
            "service_status": "running" if stream_processor.running else "stopped",
            "registered_handlers": len(stream_processor.processing_handlers),
            "topics": list(stream_processor.topic_manager.topics.values())
        }
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topics")
async def list_topics():
    """List all configured topics"""
    try:
        if not stream_processor:
            raise HTTPException(status_code=503, detail="Stream processor not initialized")
        
        return {
            "topics": stream_processor.topic_manager.topics,
            "total_count": len(stream_processor.topic_manager.topics)
        }
        
    except Exception as e:
        logger.error("Failed to list topics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/topics/create")
async def create_topics():
    """Create all required Kafka topics"""
    try:
        if not stream_processor:
            raise HTTPException(status_code=503, detail="Stream processor not initialized")
        
        success = await stream_processor.topic_manager.create_topics()
        
        if success:
            return {"message": "Topics created successfully", "topics": stream_processor.topic_manager.topics}
        else:
            raise HTTPException(status_code=500, detail="Failed to create topics")
            
    except Exception as e:
        logger.error("Failed to create topics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/processing/start")
async def start_processing():
    """Start stream processing (if stopped)"""
    try:
        if not stream_processor:
            raise HTTPException(status_code=503, detail="Stream processor not initialized")
        
        if stream_processor.running:
            return {"message": "Stream processing already running"}
        
        # This would require implementing a restart mechanism
        return {"message": "Stream processing restart not implemented yet"}
        
    except Exception as e:
        logger.error("Failed to start processing", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/processing/stop")
async def stop_processing():
    """Stop stream processing"""
    try:
        if not stream_processor:
            raise HTTPException(status_code=503, detail="Stream processor not initialized")
        
        if not stream_processor.running:
            return {"message": "Stream processing already stopped"}
        
        await stream_processor.stop_processing()
        return {"message": "Stream processing stopped"}
        
    except Exception as e:
        logger.error("Failed to stop processing", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal", signal=signum)
    # The lifespan context manager will handle cleanup


if __name__ == "__main__":
    import uvicorn
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_config=None  # Use structlog configuration
    )


@app.post("/workflows/trigger")
async def trigger_workflow(workflow_request: dict):
    """Trigger a workflow via event bus"""
    try:
        if not workflow_client:
            raise HTTPException(status_code=503, detail="Workflow client not initialized")
        
        workflow_type = workflow_request.get("type")
        parameters = workflow_request.get("parameters", {})
        
        if workflow_type == "data_processing":
            # Publish data collection event to trigger workflow
            event_id = await workflow_client.publish_event(
                topic="data.collected",
                event_type="data_collection_completed",
                data={
                    "source": parameters.get("source", "manual"),
                    "parameters": parameters
                }
            )
            
            return {
                "message": "Data processing workflow triggered",
                "event_id": event_id
            }
            
        elif workflow_type == "model_retraining":
            # Start model retraining workflow directly
            workflow_id = await workflow_client.start_workflow(
                workflow_type="model_retraining",
                parameters=parameters
            )
            
            return {
                "message": "Model retraining workflow started",
                "workflow_id": workflow_id
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown workflow type: {workflow_type}")
            
    except Exception as e:
        logger.error("Failed to trigger workflow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get workflow status via event bus"""
    try:
        if not workflow_client:
            raise HTTPException(status_code=503, detail="Workflow client not initialized")
        
        status = await workflow_client.get_workflow_status(workflow_id)
        return status
        
    except Exception as e:
        logger.error("Failed to get workflow status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """Cancel workflow via event bus"""
    try:
        if not workflow_client:
            raise HTTPException(status_code=503, detail="Workflow client not initialized")
        
        success = await workflow_client.cancel_workflow(workflow_id)
        
        if success:
            return {"message": f"Workflow {workflow_id} cancelled successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to cancel workflow")
            
    except Exception as e:
        logger.error("Failed to cancel workflow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/events/publish")
async def publish_event(event_request: dict):
    """Publish event to event bus"""
    try:
        if not workflow_client:
            raise HTTPException(status_code=503, detail="Workflow client not initialized")
        
        event_id = await workflow_client.publish_event(
            topic=event_request["topic"],
            event_type=event_request["event_type"],
            data=event_request["data"],
            correlation_id=event_request.get("correlation_id")
        )
        
        return {
            "message": "Event published successfully",
            "event_id": event_id
        }
        
    except Exception as e:
        logger.error("Failed to publish event", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))