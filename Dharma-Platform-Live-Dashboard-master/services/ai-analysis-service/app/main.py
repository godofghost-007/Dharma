"""Main FastAPI application for AI Analysis Service."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.model_governance_service import (
    initialize_governance_service, 
    shutdown_governance_service,
    get_governance_service
)
from .analysis.sentiment_analyzer import SentimentAnalyzer
from .analysis.bot_detector import BotDetector
from .analysis.campaign_detector import CampaignDetector
from .models.requests import (
    SentimentRequest, BotDetectionRequest, CampaignDetectionRequest,
    SentimentAnalysisResponse, BotDetectionResponse, CampaignDetectionResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
sentiment_analyzer: Optional[SentimentAnalyzer] = None
bot_detector: Optional[BotDetector] = None
campaign_detector: Optional[CampaignDetector] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI Analysis Service...")
    
    try:
        # Initialize governance service
        await initialize_governance_service()
        
        # Initialize AI components
        global sentiment_analyzer, bot_detector, campaign_detector
        
        sentiment_analyzer = SentimentAnalyzer()
        await sentiment_analyzer.initialize()
        
        bot_detector = BotDetector()
        await bot_detector.initialize()
        
        campaign_detector = CampaignDetector()
        await campaign_detector.initialize()
        
        logger.info("AI Analysis Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start AI Analysis Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Analysis Service...")
    
    try:
        await shutdown_governance_service()
        logger.info("AI Analysis Service shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Project Dharma - AI Analysis Service",
    description="AI-powered analysis service for sentiment analysis, bot detection, and campaign detection",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check all components
        health_status = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "components": {}
        }
        
        if sentiment_analyzer:
            sentiment_health = await sentiment_analyzer.health_check()
            health_status["components"]["sentiment_analyzer"] = sentiment_health
        
        if bot_detector:
            bot_health = await bot_detector.health_check()
            health_status["components"]["bot_detector"] = bot_health
        
        if campaign_detector:
            campaign_health = await campaign_detector.health_check()
            health_status["components"]["campaign_detector"] = campaign_health
        
        # Check if any component is unhealthy
        unhealthy_components = [
            name for name, status in health_status["components"].items()
            if status.get("status") != "healthy"
        ]
        
        if unhealthy_components:
            health_status["status"] = "degraded"
            health_status["unhealthy_components"] = unhealthy_components
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
        )


# Sentiment Analysis Endpoints
@app.post("/api/v1/analyze/sentiment", response_model=SentimentAnalysisResponse)
async def analyze_sentiment(
    request: SentimentRequest,
    background_tasks: BackgroundTasks
):
    """Analyze sentiment of text content."""
    try:
        if not sentiment_analyzer:
            raise HTTPException(status_code=503, detail="Sentiment analyzer not available")
        
        # Get model version from governance service
        governance_service = get_governance_service()
        from .core.model_registry import ModelType
        
        model_version = await governance_service.get_model_for_inference(
            ModelType.SENTIMENT_ANALYSIS,
            request.request_id
        )
        
        # Perform sentiment analysis
        result = await sentiment_analyzer.analyze_sentiment(
            text=request.text,
            language=request.language,
            translate=request.translate
        )
        
        # Record inference result for governance
        if model_version:
            background_tasks.add_task(
                governance_service.record_inference_result,
                model_version=model_version,
                input_data={"text": request.text, "language": request.language},
                prediction=result.sentiment.value,
                confidence=result.confidence,
                latency_ms=result.processing_time_ms,
                request_id=request.request_id
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze/sentiment/batch", response_model=List[SentimentAnalysisResponse])
async def analyze_sentiment_batch(
    texts: List[str],
    language: Optional[str] = None,
    translate: bool = True
):
    """Analyze sentiment for multiple texts."""
    try:
        if not sentiment_analyzer:
            raise HTTPException(status_code=503, detail="Sentiment analyzer not available")
        
        if len(texts) > settings.max_batch_size:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size {len(texts)} exceeds maximum {settings.max_batch_size}"
            )
        
        results = await sentiment_analyzer.batch_analyze_sentiment(
            texts=texts,
            language=language,
            translate=translate
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error in batch sentiment analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Bot Detection Endpoints
@app.post("/api/v1/analyze/bot-detection", response_model=BotDetectionResponse)
async def analyze_bot_behavior(
    request: BotDetectionRequest,
    background_tasks: BackgroundTasks
):
    """Analyze user behavior for bot indicators."""
    try:
        if not bot_detector:
            raise HTTPException(status_code=503, detail="Bot detector not available")
        
        # Get model version from governance service
        governance_service = get_governance_service()
        from .core.model_registry import ModelType
        
        model_version = await governance_service.get_model_for_inference(
            ModelType.BOT_DETECTION,
            request.request_id
        )
        
        # Perform bot detection analysis
        result = await bot_detector.analyze_user_behavior(
            user_id=request.user_id,
            platform=request.platform,
            user_data=request.user_data,
            include_network_analysis=request.include_network_analysis
        )
        
        # Record inference result for governance
        if model_version:
            background_tasks.add_task(
                governance_service.record_inference_result,
                model_version=model_version,
                input_data={"user_id": request.user_id, "platform": request.platform},
                prediction=result.bot_probability,
                confidence=result.confidence,
                latency_ms=result.processing_time_ms,
                request_id=request.request_id
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bot detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze/coordinated-behavior")
async def analyze_coordinated_behavior(
    user_group: List[Dict[str, Any]],
    time_window_hours: float = 24.0
):
    """Analyze coordinated behavior among a group of users."""
    try:
        if not bot_detector:
            raise HTTPException(status_code=503, detail="Bot detector not available")
        
        if len(user_group) > settings.max_coordination_group_size:
            raise HTTPException(
                status_code=400,
                detail=f"Group size {len(user_group)} exceeds maximum {settings.max_coordination_group_size}"
            )
        
        result = await bot_detector.detect_coordinated_behavior(
            user_group=user_group,
            time_window_hours=time_window_hours
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in coordinated behavior analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Campaign Detection Endpoints
@app.post("/api/v1/analyze/campaign-detection", response_model=CampaignDetectionResponse)
async def detect_campaigns(
    request: CampaignDetectionRequest,
    background_tasks: BackgroundTasks
):
    """Detect coordinated campaigns from posts data."""
    try:
        if not campaign_detector:
            raise HTTPException(status_code=503, detail="Campaign detector not available")
        
        # Get model version from governance service
        governance_service = get_governance_service()
        from .core.model_registry import ModelType
        
        model_version = await governance_service.get_model_for_inference(
            ModelType.CAMPAIGN_DETECTION,
            request.request_id
        )
        
        # Perform campaign detection
        result = await campaign_detector.detect_campaigns(
            posts_data=request.posts_data,
            time_window_hours=request.time_window_hours,
            min_coordination_score=request.min_coordination_score
        )
        
        # Record inference result for governance
        if model_version:
            background_tasks.add_task(
                governance_service.record_inference_result,
                model_version=model_version,
                input_data={"posts_count": len(request.posts_data)},
                prediction=result.coordination_score,
                confidence=result.coordination_score,  # Use coordination score as confidence
                latency_ms=result.processing_time_ms,
                request_id=request.request_id
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in campaign detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Model Information Endpoints
@app.get("/api/v1/models/info")
async def get_models_info():
    """Get information about all loaded models."""
    try:
        models_info = {}
        
        if sentiment_analyzer:
            models_info["sentiment_analyzer"] = sentiment_analyzer.get_model_info()
        
        if bot_detector:
            models_info["bot_detector"] = bot_detector.get_model_info()
        
        if campaign_detector:
            models_info["campaign_detector"] = campaign_detector.get_model_info()
        
        return models_info
        
    except Exception as e:
        logger.error(f"Error getting models info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Include governance API routes
from .api.governance import router as governance_router
app.include_router(governance_router, prefix="/api/v1/governance", tags=["governance"])


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": asyncio.get_event_loop().time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": asyncio.get_event_loop().time()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )