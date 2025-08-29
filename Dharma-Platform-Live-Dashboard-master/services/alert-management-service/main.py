#!/usr/bin/env python3
"""
Alert Management Service
Main entry point for the alert management microservice
"""

import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add shared modules to path
sys.path.append(str(Path(__file__).parent.parent.parent / "shared"))

from app.core.config import AlertManagementConfig
from app.core.alert_manager import AlertManager
from app.notifications.notification_service import NotificationService
from app.api.alert_interface import AlertInterface


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Alert Management Service...")
    
    # Initialize services
    config = AlertManagementConfig()
    alert_manager = AlertManager(config)
    notification_service = NotificationService(config)
    alert_interface = AlertInterface(alert_manager, notification_service)
    
    # Store in app state
    app.state.config = config
    app.state.alert_manager = alert_manager
    app.state.notification_service = notification_service
    app.state.alert_interface = alert_interface
    
    # Start background tasks
    await alert_manager.start()
    await notification_service.start()
    
    logger.info("Alert Management Service started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Alert Management Service...")
    await alert_manager.stop()
    await notification_service.stop()
    logger.info("Alert Management Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Alert Management Service",
    description="Notification and escalation system for Project Dharma",
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
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "alert-management-service",
        "version": "1.0.0"
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    alert_manager = app.state.alert_manager
    notification_service = app.state.notification_service
    
    return {
        "alerts_processed": alert_manager.get_metrics().get("alerts_processed", 0),
        "notifications_sent": notification_service.get_metrics().get("notifications_sent", 0),
        "active_alerts": alert_manager.get_metrics().get("active_alerts", 0)
    }


@app.post("/alerts")
async def create_alert(alert_data: dict):
    """Create a new alert"""
    try:
        alert_interface = app.state.alert_interface
        alert = await alert_interface.create_alert(alert_data)
        return {"alert_id": alert.id, "status": "created"}
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts")
async def get_alerts(limit: int = 100, offset: int = 0):
    """Get alerts with pagination"""
    try:
        alert_interface = app.state.alert_interface
        alerts = await alert_interface.get_alerts(limit=limit, offset=offset)
        return {"alerts": alerts, "total": len(alerts)}
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    try:
        alert_interface = app.state.alert_interface
        await alert_interface.acknowledge_alert(alert_id)
        return {"status": "acknowledged"}
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notifications/send")
async def send_notification(notification_data: dict):
    """Send a notification"""
    try:
        notification_service = app.state.notification_service
        result = await notification_service.send_notification(notification_data)
        return {"status": "sent", "result": result}
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )