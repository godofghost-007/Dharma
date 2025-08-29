"""
Cost Monitoring Service - Main Application
Tracks cloud spend, generates budget alerts, and provides cost optimization recommendations
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from app.core.config import CostMonitoringConfig
from app.core.cost_tracker import CostTracker
from app.core.budget_manager import BudgetManager
from app.core.optimization_engine import OptimizationEngine
from app.core.autoscaling_manager import AutoscalingManager
from app.api.routes import cost_router
from app.models.requests import CostAnalysisRequest, BudgetAlertRequest
from app.models.responses import CostReport, OptimizationRecommendation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Cost Monitoring Service",
    description="Cloud cost tracking and optimization service for Project Dharma",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize configuration
config = CostMonitoringConfig()

# Initialize core services
cost_tracker = CostTracker(config)
budget_manager = BudgetManager(config)
optimization_engine = OptimizationEngine(config)
autoscaling_manager = AutoscalingManager(config)

# Include API routes
app.include_router(cost_router, prefix="/api/v1/cost", tags=["cost"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Cost Monitoring Service...")
    
    # Initialize database connections
    await cost_tracker.initialize()
    await budget_manager.initialize()
    
    # Start background tasks
    asyncio.create_task(cost_collection_task())
    asyncio.create_task(budget_monitoring_task())
    asyncio.create_task(optimization_analysis_task())
    
    logger.info("Cost Monitoring Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Cost Monitoring Service...")
    await cost_tracker.cleanup()
    await budget_manager.cleanup()

async def cost_collection_task():
    """Background task to collect cost data from cloud providers"""
    while True:
        try:
            logger.info("Collecting cost data from cloud providers...")
            await cost_tracker.collect_cost_data()
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Error in cost collection task: {e}")
            await asyncio.sleep(300)  # Retry after 5 minutes on error

async def budget_monitoring_task():
    """Background task to monitor budget thresholds"""
    while True:
        try:
            logger.info("Checking budget thresholds...")
            await budget_manager.check_budget_thresholds()
            await asyncio.sleep(1800)  # Run every 30 minutes
        except Exception as e:
            logger.error(f"Error in budget monitoring task: {e}")
            await asyncio.sleep(300)

async def optimization_analysis_task():
    """Background task to analyze cost optimization opportunities"""
    while True:
        try:
            logger.info("Analyzing cost optimization opportunities...")
            await optimization_engine.analyze_optimization_opportunities()
            await asyncio.sleep(21600)  # Run every 6 hours
        except Exception as e:
            logger.error(f"Error in optimization analysis task: {e}")
            await asyncio.sleep(1800)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "cost-monitoring-service"
    }

@app.get("/api/v1/cost/summary")
async def get_cost_summary():
    """Get current cost summary across all components"""
    try:
        summary = await cost_tracker.get_cost_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting cost summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cost summary")

@app.get("/api/v1/cost/reports/daily")
async def get_daily_cost_report(days: int = 30):
    """Get daily cost report for specified number of days"""
    try:
        report = await cost_tracker.get_daily_cost_report(days)
        return report
    except Exception as e:
        logger.error(f"Error generating daily cost report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate daily cost report")

@app.get("/api/v1/optimization/recommendations")
async def get_optimization_recommendations():
    """Get current cost optimization recommendations"""
    try:
        recommendations = await optimization_engine.get_recommendations()
        return recommendations
    except Exception as e:
        logger.error(f"Error getting optimization recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recommendations")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)