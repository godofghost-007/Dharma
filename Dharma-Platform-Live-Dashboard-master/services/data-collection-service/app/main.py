"""
Data Collection Service - Main FastAPI application with data ingestion pipeline
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.collectors.twitter_collector import TwitterCollector
from app.collectors.youtube_collector import YouTubeCollector
from app.collectors.web_scraper import WebScraper
from app.collectors.telegram_collector import TelegramCollector
from app.core.config import get_settings
from app.core.kafka_producer import KafkaDataProducer
from app.core.data_pipeline import get_pipeline, DataIngestionPipeline
from app.core.batch_processor import get_batch_processor, BatchProcessor
from app.core.monitoring import get_monitor, DataCollectionMonitor
from app.models.requests import (
    TwitterCollectionRequest,
    YouTubeCollectionRequest,
    WebScrapingRequest,
    TelegramCollectionRequest,
    BatchProcessingRequest
)
from shared.models.post import Platform

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

# Global collectors
collectors: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()
    
    # Initialize collectors
    collectors["twitter"] = TwitterCollector(settings.twitter_credentials)
    collectors["youtube"] = YouTubeCollector(settings.youtube_api_key)
    collectors["web_scraper"] = WebScraper()
    collectors["telegram"] = TelegramCollector(settings.telegram_credentials)
    collectors["kafka_producer"] = KafkaDataProducer(settings.kafka_config)
    
    # Initialize pipeline and monitoring
    pipeline = await get_pipeline()
    monitor = await get_monitor()
    batch_processor = await get_batch_processor()
    
    # Start monitoring
    await monitor.start_monitoring()
    
    # Start batch processor
    asyncio.create_task(batch_processor.process_jobs())
    
    logger.info("Data collection service with ingestion pipeline started")
    yield
    
    # Cleanup
    await collectors["kafka_producer"].close()
    await pipeline.cleanup()
    await monitor.cleanup()
    await batch_processor.cleanup()
    logger.info("Data collection service stopped")


app = FastAPI(
    title="Data Collection Service",
    description="Multi-platform data collection service for Project Dharma",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check(monitor: DataCollectionMonitor = Depends(get_monitor)):
    """Health check endpoint with system health metrics"""
    try:
        system_health = await monitor.get_system_health()
        return {
            "status": "healthy",
            "service": "data-collection",
            "system_health": system_health
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "data-collection",
            "error": str(e)
        }


@app.post("/collect/twitter")
async def start_twitter_collection(
    request: TwitterCollectionRequest,
    background_tasks: BackgroundTasks,
    pipeline: DataIngestionPipeline = Depends(get_pipeline),
    monitor: DataCollectionMonitor = Depends(get_monitor)
):
    """Start Twitter data collection with pipeline integration"""
    try:
        import time
        start_time = time.time()
        
        twitter_collector = collectors["twitter"]
        kafka_producer = collectors["kafka_producer"]
        
        # Start collection in background with pipeline integration
        background_tasks.add_task(
            twitter_collector.start_collection,
            request,
            kafka_producer,
            pipeline
        )
        
        duration = time.time() - start_time
        await monitor.record_collection_event(Platform.TWITTER, "collection_start", True, duration)
        
        return {
            "status": "started",
            "collection_type": "twitter",
            "keywords": request.keywords,
            "collection_id": request.collection_id
        }
    except Exception as e:
        await monitor.record_collection_event(Platform.TWITTER, "collection_start", False)
        logger.error("Failed to start Twitter collection", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collect/youtube")
async def start_youtube_collection(
    request: YouTubeCollectionRequest,
    background_tasks: BackgroundTasks
):
    """Start YouTube data collection"""
    try:
        youtube_collector = collectors["youtube"]
        kafka_producer = collectors["kafka_producer"]
        
        background_tasks.add_task(
            youtube_collector.start_collection,
            request,
            kafka_producer
        )
        
        return {
            "status": "started",
            "collection_type": "youtube",
            "query": request.query,
            "collection_id": request.collection_id
        }
    except Exception as e:
        logger.error("Failed to start YouTube collection", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collect/web")
async def start_web_scraping(
    request: WebScrapingRequest,
    background_tasks: BackgroundTasks
):
    """Start web scraping"""
    try:
        web_scraper = collectors["web_scraper"]
        kafka_producer = collectors["kafka_producer"]
        
        background_tasks.add_task(
            web_scraper.start_scraping,
            request,
            kafka_producer
        )
        
        return {
            "status": "started",
            "collection_type": "web_scraping",
            "urls": request.urls,
            "collection_id": request.collection_id
        }
    except Exception as e:
        logger.error("Failed to start web scraping", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collect/telegram")
async def start_telegram_collection(
    request: TelegramCollectionRequest,
    background_tasks: BackgroundTasks
):
    """Start Telegram data collection"""
    try:
        telegram_collector = collectors["telegram"]
        kafka_producer = collectors["kafka_producer"]
        
        background_tasks.add_task(
            telegram_collector.start_collection,
            request,
            kafka_producer
        )
        
        return {
            "status": "started",
            "collection_type": "telegram",
            "channels": request.channels,
            "collection_id": request.collection_id
        }
    except Exception as e:
        logger.error("Failed to start Telegram collection", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_service_status():
    """Get service status and active collections"""
    return {
        "service": "data-collection",
        "status": "running",
        "collectors": {
            "twitter": "available",
            "youtube": "available", 
            "web_scraper": "available",
            "telegram": "available"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Da
ta Pipeline Endpoints
@app.get("/pipeline/status/{collection_id}")
async def get_pipeline_status(collection_id: str, 
                             pipeline: DataIngestionPipeline = Depends(get_pipeline)):
    """Get processing status for a collection"""
    try:
        status = await pipeline.get_processing_status(collection_id)
        return status
    except Exception as e:
        logger.error("Failed to get pipeline status", collection_id=collection_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline/process")
async def process_data_directly(platform: str, data: Dict[str, Any], collection_id: str,
                               pipeline: DataIngestionPipeline = Depends(get_pipeline),
                               monitor: DataCollectionMonitor = Depends(get_monitor)):
    """Process data directly through the pipeline"""
    try:
        platform_enum = Platform(platform.lower())
        
        import time
        start_time = time.time()
        
        success = await pipeline.process_streaming_data(platform_enum, data, collection_id)
        
        duration = time.time() - start_time
        await monitor.record_collection_event(platform_enum, "direct_processing", success, duration)
        
        return {"success": success, "collection_id": collection_id, "platform": platform}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    except Exception as e:
        logger.error("Failed to process data directly", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Batch Processing Endpoints
@app.post("/batch/submit")
async def submit_batch_job(request: BatchProcessingRequest,
                          batch_processor: BatchProcessor = Depends(get_batch_processor)):
    """Submit a batch processing job"""
    try:
        platform_enum = Platform(request.platform.lower())
        
        job_id = await batch_processor.submit_batch_job(
            platform_enum,
            request.data_source,
            request.collection_id,
            request.parameters
        )
        
        return {"job_id": job_id, "status": "submitted"}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {request.platform}")
    except Exception as e:
        logger.error("Failed to submit batch job", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batch/status/{job_id}")
async def get_batch_job_status(job_id: str,
                              batch_processor: BatchProcessor = Depends(get_batch_processor)):
    """Get status of a batch processing job"""
    try:
        job = await batch_processor.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job.job_id,
            "platform": job.platform.value,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "metrics": job.metrics.__dict__ if job.metrics else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get batch job status", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/cancel/{job_id}")
async def cancel_batch_job(job_id: str,
                          batch_processor: BatchProcessor = Depends(get_batch_processor)):
    """Cancel a batch processing job"""
    try:
        success = await batch_processor.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Job cannot be cancelled")
        
        return {"job_id": job_id, "status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel batch job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Monitoring Endpoints
@app.get("/monitoring/metrics")
async def get_metrics(name_pattern: str = "*", hours: int = 1,
                     monitor: DataCollectionMonitor = Depends(get_monitor)):
    """Get system metrics"""
    try:
        from datetime import datetime, timedelta
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        metrics = await monitor.metrics_collector.get_metrics(
            name_pattern=name_pattern,
            start_time=start_time
        )
        
        return {"metrics": metrics, "count": len(metrics)}
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/alerts")
async def get_active_alerts(monitor: DataCollectionMonitor = Depends(get_monitor)):
    """Get active alerts"""
    try:
        alerts = await monitor.alert_manager.get_active_alerts()
        return {
            "alerts": [alert.to_dict() for alert in alerts],
            "count": len(alerts)
        }
    except Exception as e:
        logger.error("Failed to get alerts", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/monitoring/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, monitor: DataCollectionMonitor = Depends(get_monitor)):
    """Resolve an active alert"""
    try:
        success = await monitor.alert_manager.resolve_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already resolved")
        
        return {"alert_id": alert_id, "status": "resolved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))