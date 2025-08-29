"""Alert management interface API endpoints."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from shared.models.alert import (
    Alert, AlertCreate, AlertUpdate, AlertSummary, AlertStats,
    AlertType, SeverityLevel, AlertStatus, EscalationLevel
)
from ..core.alert_manager import AlertManager
from ..core.escalation_engine import EscalationEngine
from ..core.reporting_service import ReportingService
from ..core.search_service import AlertSearchService

router = APIRouter(prefix="/api/v1/alerts", tags=["Alert Management"])


class AlertFilter(BaseModel):
    """Filter parameters for alert queries."""
    
    alert_types: Optional[List[AlertType]] = Field(None, description="Filter by alert types")
    severities: Optional[List[SeverityLevel]] = Field(None, description="Filter by severities")
    statuses: Optional[List[AlertStatus]] = Field(None, description="Filter by statuses")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")
    escalation_level: Optional[EscalationLevel] = Field(None, description="Filter by escalation level")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    search_query: Optional[str] = Field(None, description="Text search query")


class AlertAssignment(BaseModel):
    """Alert assignment request."""
    
    alert_id: str = Field(description="Alert ID to assign")
    assigned_to: str = Field(description="User ID to assign to")
    notes: Optional[str] = Field(None, description="Assignment notes")


class AlertAcknowledgment(BaseModel):
    """Alert acknowledgment request."""
    
    alert_id: str = Field(description="Alert ID to acknowledge")
    notes: Optional[str] = Field(None, description="Acknowledgment notes")


class AlertResolution(BaseModel):
    """Alert resolution request."""
    
    alert_id: str = Field(description="Alert ID to resolve")
    resolution_notes: str = Field(description="Resolution notes")
    resolution_type: str = Field(description="Type of resolution")


class AlertEscalation(BaseModel):
    """Alert escalation request."""
    
    alert_id: str = Field(description="Alert ID to escalate")
    escalation_level: EscalationLevel = Field(description="New escalation level")
    escalation_reason: str = Field(description="Reason for escalation")
    notes: Optional[str] = Field(None, description="Additional notes")


class BulkOperation(BaseModel):
    """Bulk operation request."""
    
    alert_ids: List[str] = Field(description="List of alert IDs")
    operation: str = Field(description="Operation to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")


# Dependency injection
def get_alert_manager() -> AlertManager:
    """Get alert manager instance."""
    return AlertManager()


def get_escalation_engine() -> EscalationEngine:
    """Get escalation engine instance."""
    return EscalationEngine()


def get_reporting_service() -> ReportingService:
    """Get reporting service instance."""
    return ReportingService()


def get_search_service() -> AlertSearchService:
    """Get search service instance."""
    return AlertSearchService()


@router.get("/inbox", response_model=List[AlertSummary])
async def get_alert_inbox(
    skip: int = Query(0, ge=0, description="Number of alerts to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Number of alerts to return"),
    alert_types: Optional[List[AlertType]] = Query(None, description="Filter by alert types"),
    severities: Optional[List[SeverityLevel]] = Query(None, description="Filter by severities"),
    statuses: Optional[List[AlertStatus]] = Query(None, description="Filter by statuses"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date"),
    search_query: Optional[str] = Query(None, description="Text search query"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    alert_manager: AlertManager = Depends(get_alert_manager),
    search_service: AlertSearchService = Depends(get_search_service)
):
    """
    Get alert inbox with filtering and search capabilities.
    
    Supports:
    - Pagination with skip/limit
    - Filtering by type, severity, status, assignment
    - Date range filtering
    - Text search across title and description
    - Sorting by various fields
    """
    try:
        # Build filter object
        filters = AlertFilter(
            alert_types=alert_types,
            severities=severities,
            statuses=statuses,
            assigned_to=assigned_to,
            created_after=created_after,
            created_before=created_before,
            search_query=search_query
        )
        
        # Get filtered alerts
        if search_query:
            alerts = await search_service.search_alerts(
                query=search_query,
                filters=filters,
                skip=skip,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order
            )
        else:
            alerts = await alert_manager.get_alerts(
                filters=filters,
                skip=skip,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order
            )
        
        return alerts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")


@router.get("/{alert_id}", response_model=Alert)
async def get_alert_details(
    alert_id: str = Path(..., description="Alert ID"),
    alert_manager: AlertManager = Depends(get_alert_manager)
):
    """Get detailed information for a specific alert."""
    try:
        alert = await alert_manager.get_alert_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alert: {str(e)}")


@router.post("/acknowledge")
async def acknowledge_alert(
    acknowledgment: AlertAcknowledgment,
    user_id: str = Query(..., description="User ID performing acknowledgment"),
    alert_manager: AlertManager = Depends(get_alert_manager)
):
    """Acknowledge an alert and track response time."""
    try:
        success = await alert_manager.acknowledge_alert(
            alert_id=acknowledgment.alert_id,
            user_id=user_id,
            notes=acknowledgment.notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
        
        return {"message": "Alert acknowledged successfully", "alert_id": acknowledgment.alert_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.post("/assign")
async def assign_alert(
    assignment: AlertAssignment,
    assigned_by: str = Query(..., description="User ID performing assignment"),
    alert_manager: AlertManager = Depends(get_alert_manager)
):
    """Assign an alert to a user."""
    try:
        success = await alert_manager.assign_alert(
            alert_id=assignment.alert_id,
            assigned_to=assignment.assigned_to,
            assigned_by=assigned_by,
            notes=assignment.notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "message": "Alert assigned successfully",
            "alert_id": assignment.alert_id,
            "assigned_to": assignment.assigned_to
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign alert: {str(e)}")


@router.post("/resolve")
async def resolve_alert(
    resolution: AlertResolution,
    resolved_by: str = Query(..., description="User ID performing resolution"),
    alert_manager: AlertManager = Depends(get_alert_manager)
):
    """Resolve an alert and track resolution time."""
    try:
        success = await alert_manager.resolve_alert(
            alert_id=resolution.alert_id,
            resolved_by=resolved_by,
            resolution_notes=resolution.resolution_notes,
            resolution_type=resolution.resolution_type
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already resolved")
        
        return {"message": "Alert resolved successfully", "alert_id": resolution.alert_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")


@router.post("/escalate")
async def escalate_alert(
    escalation: AlertEscalation,
    escalated_by: str = Query(..., description="User ID performing escalation"),
    escalation_engine: EscalationEngine = Depends(get_escalation_engine)
):
    """Escalate an alert to a higher level."""
    try:
        success = await escalation_engine.escalate_alert(
            alert_id=escalation.alert_id,
            escalated_by=escalated_by,
            new_level=escalation.escalation_level,
            reason=escalation.escalation_reason,
            notes=escalation.notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "message": "Alert escalated successfully",
            "alert_id": escalation.alert_id,
            "escalation_level": escalation.escalation_level
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to escalate alert: {str(e)}")


@router.post("/bulk-operations")
async def perform_bulk_operation(
    operation: BulkOperation,
    user_id: str = Query(..., description="User ID performing operation"),
    alert_manager: AlertManager = Depends(get_alert_manager)
):
    """Perform bulk operations on multiple alerts."""
    try:
        results = await alert_manager.bulk_operation(
            alert_ids=operation.alert_ids,
            operation=operation.operation,
            user_id=user_id,
            parameters=operation.parameters
        )
        
        return {
            "message": f"Bulk operation '{operation.operation}' completed",
            "processed": len(operation.alert_ids),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform bulk operation: {str(e)}")


@router.get("/stats/summary", response_model=AlertStats)
async def get_alert_statistics(
    period_days: int = Query(7, ge=1, le=365, description="Period in days"),
    alert_types: Optional[List[AlertType]] = Query(None, description="Filter by alert types"),
    reporting_service: ReportingService = Depends(get_reporting_service)
):
    """Get alert statistics and metrics for a specified period."""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        stats = await reporting_service.get_alert_statistics(
            start_date=start_date,
            end_date=end_date,
            alert_types=alert_types
        )
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


@router.get("/trends/analysis")
async def get_alert_trends(
    period_days: int = Query(30, ge=1, le=365, description="Period in days"),
    granularity: str = Query("daily", regex="^(hourly|daily|weekly)$", description="Trend granularity"),
    reporting_service: ReportingService = Depends(get_reporting_service)
):
    """Get alert trend analysis over time."""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        trends = await reporting_service.get_alert_trends(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )
        
        return trends
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve trends: {str(e)}")


@router.get("/export/report")
async def export_alert_report(
    format: str = Query("csv", regex="^(csv|pdf|json)$", description="Export format"),
    period_days: int = Query(30, ge=1, le=365, description="Period in days"),
    alert_types: Optional[List[AlertType]] = Query(None, description="Filter by alert types"),
    reporting_service: ReportingService = Depends(get_reporting_service)
):
    """Export alert report in specified format."""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        report_data = await reporting_service.export_alert_report(
            start_date=start_date,
            end_date=end_date,
            format=format,
            alert_types=alert_types
        )
        
        if format == "csv":
            return JSONResponse(
                content={"data": report_data},
                headers={"Content-Type": "text/csv"}
            )
        elif format == "pdf":
            return JSONResponse(
                content={"data": report_data},
                headers={"Content-Type": "application/pdf"}
            )
        else:
            return report_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")


@router.get("/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=2, description="Search query"),
    search_service: AlertSearchService = Depends(get_search_service)
):
    """Get search suggestions for alert queries."""
    try:
        suggestions = await search_service.get_search_suggestions(query)
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.post("/workflow/auto-escalation")
async def configure_auto_escalation(
    config: Dict[str, Any],
    user_id: str = Query(..., description="User ID configuring escalation"),
    escalation_engine: EscalationEngine = Depends(get_escalation_engine)
):
    """Configure automatic escalation workflows."""
    try:
        success = await escalation_engine.configure_auto_escalation(
            config=config,
            configured_by=user_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid escalation configuration")
        
        return {"message": "Auto-escalation configured successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure auto-escalation: {str(e)}")