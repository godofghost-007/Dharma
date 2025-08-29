"""
Web-based Alert Management Interface using FastAPI and HTML templates.

This module provides a comprehensive web interface for alert management
with server-side rendering and AJAX interactions.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json

from shared.models.alert import (
    Alert, AlertSummary, AlertType, SeverityLevel, AlertStatus, EscalationLevel
)
from ..core.alert_manager import AlertManager
from ..core.search_service import AlertSearchService
from ..core.reporting_service import ReportingService
from ..core.escalation_engine import EscalationEngine


class AlertWebInterface:
    """Web-based alert management interface."""
    
    def __init__(self):
        self.app = FastAPI(title="Alert Management Interface")
        self.templates = Jinja2Templates(directory="templates")
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # Initialize services
        self.alert_manager = AlertManager()
        self.search_service = AlertSearchService()
        self.reporting_service = ReportingService()
        self.escalation_engine = EscalationEngine()
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all web interface routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Main dashboard home page."""
            # Get summary statistics
            stats = await self._get_dashboard_stats()
            
            return self.templates.TemplateResponse(
                "dashboard.html",
                {
                    "request": request,
                    "stats": stats,
                    "page_title": "Alert Management Dashboard"
                }
            )
        
        @self.app.get("/inbox", response_class=HTMLResponse)
        async def alert_inbox(
            request: Request,
            status: Optional[List[str]] = Query(None),
            severity: Optional[List[str]] = Query(None),
            alert_type: Optional[List[str]] = Query(None),
            assigned_to: Optional[str] = Query(None),
            page: int = Query(1, ge=1),
            limit: int = Query(25, ge=1, le=100)
        ):
            """Alert inbox page with filtering."""
            
            # Build filters
            filters = {}
            if status:
                filters['statuses'] = status
            if severity:
                filters['severities'] = severity
            if alert_type:
                filters['alert_types'] = alert_type
            if assigned_to:
                filters['assigned_to'] = assigned_to
            
            # Get alerts
            skip = (page - 1) * limit
            alerts = await self.alert_manager.get_alerts(
                filters=filters,
                skip=skip,
                limit=limit
            )
            
            # Get total count for pagination
            total_count = await self._get_filtered_alert_count(filters)
            total_pages = (total_count + limit - 1) // limit
            
            return self.templates.TemplateResponse(
                "inbox.html",
                {
                    "request": request,
                    "alerts": alerts,
                    "filters": filters,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit
                    },
                    "alert_types": [t.value for t in AlertType],
                    "severities": [s.value for s in SeverityLevel],
                    "statuses": [s.value for s in AlertStatus],
                    "page_title": "Alert Inbox"
                }
            )
        
        @self.app.get("/alert/{alert_id}", response_class=HTMLResponse)
        async def alert_details(request: Request, alert_id: str):
            """Alert details page."""
            alert = await self.alert_manager.get_alert_by_id(alert_id)
            
            if not alert:
                raise HTTPException(status_code=404, detail="Alert not found")
            
            # Get related alerts (mock implementation)
            related_alerts = await self._get_related_alerts(alert_id)
            
            # Get escalation history
            escalation_history = await self._get_escalation_history(alert_id)
            
            return self.templates.TemplateResponse(
                "alert_details.html",
                {
                    "request": request,
                    "alert": alert,
                    "related_alerts": related_alerts,
                    "escalation_history": escalation_history,
                    "page_title": f"Alert {alert_id[:8]}..."
                }
            )
        
        @self.app.get("/search", response_class=HTMLResponse)
        async def search_page(request: Request):
            """Advanced search page."""
            return self.templates.TemplateResponse(
                "search.html",
                {
                    "request": request,
                    "alert_types": [t.value for t in AlertType],
                    "severities": [s.value for s in SeverityLevel],
                    "statuses": [s.value for s in AlertStatus],
                    "escalation_levels": [l.value for l in EscalationLevel],
                    "page_title": "Advanced Search"
                }
            )
        
        @self.app.post("/search", response_class=HTMLResponse)
        async def perform_search(
            request: Request,
            query: str = Form(""),
            alert_types: Optional[List[str]] = Form(None),
            severities: Optional[List[str]] = Form(None),
            statuses: Optional[List[str]] = Form(None),
            platforms: Optional[List[str]] = Form(None),
            risk_score_min: float = Form(0.0),
            risk_score_max: float = Form(1.0),
            date_from: Optional[str] = Form(None),
            date_to: Optional[str] = Form(None)
        ):
            """Perform advanced search."""
            
            # Build search parameters
            search_params = {
                "query": query,
                "alert_types": alert_types,
                "severities": severities,
                "statuses": statuses,
                "platforms": platforms,
                "min_risk_score": risk_score_min,
                "max_risk_score": risk_score_max
            }
            
            # Add date filters if provided
            if date_from:
                search_params["created_after"] = datetime.fromisoformat(date_from)
            if date_to:
                search_params["created_before"] = datetime.fromisoformat(date_to)
            
            # Perform search
            if query or any([alert_types, severities, statuses, platforms]):
                results = await self.search_service.advanced_search(search_params)
            else:
                results = {"alerts": [], "total_hits": 0, "facets": {}}
            
            return self.templates.TemplateResponse(
                "search_results.html",
                {
                    "request": request,
                    "results": results,
                    "search_params": search_params,
                    "page_title": "Search Results"
                }
            )
        
        @self.app.get("/analytics", response_class=HTMLResponse)
        async def analytics_dashboard(
            request: Request,
            period: int = Query(30, ge=1, le=365)
        ):
            """Analytics dashboard page."""
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period)
            
            # Get analytics data
            stats = await self.reporting_service.get_alert_statistics(start_date, end_date)
            trends = await self.reporting_service.get_alert_trends(start_date, end_date)
            performance = await self.reporting_service.get_performance_metrics(start_date, end_date)
            
            return self.templates.TemplateResponse(
                "analytics.html",
                {
                    "request": request,
                    "stats": stats,
                    "trends": trends,
                    "performance": performance,
                    "period": period,
                    "page_title": "Analytics Dashboard"
                }
            )
        
        @self.app.get("/escalation", response_class=HTMLResponse)
        async def escalation_management(request: Request):
            """Escalation management page."""
            
            # Get escalation rules
            rules = await self.escalation_engine.get_escalation_rules()
            
            # Get recent escalations
            recent_escalations = await self._get_recent_escalations()
            
            return self.templates.TemplateResponse(
                "escalation.html",
                {
                    "request": request,
                    "rules": rules,
                    "recent_escalations": recent_escalations,
                    "alert_types": [t.value for t in AlertType],
                    "severities": [s.value for s in SeverityLevel],
                    "escalation_levels": [l.value for l in EscalationLevel],
                    "page_title": "Escalation Management"
                }
            )
        
        @self.app.get("/bulk-operations", response_class=HTMLResponse)
        async def bulk_operations_page(request: Request):
            """Bulk operations page."""
            
            # Get alerts available for bulk operations
            alerts = await self._get_bulk_operation_alerts()
            
            return self.templates.TemplateResponse(
                "bulk_operations.html",
                {
                    "request": request,
                    "alerts": alerts,
                    "page_title": "Bulk Operations"
                }
            )
        
        # API endpoints for AJAX operations
        @self.app.post("/api/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert_api(
            alert_id: str,
            user_id: str = Form(...),
            notes: Optional[str] = Form(None)
        ):
            """API endpoint to acknowledge an alert."""
            try:
                success = await self.alert_manager.acknowledge_alert(
                    alert_id=alert_id,
                    user_id=user_id,
                    notes=notes
                )
                
                if success:
                    return {"success": True, "message": "Alert acknowledged successfully"}
                else:
                    return {"success": False, "message": "Failed to acknowledge alert"}
                    
            except Exception as e:
                return {"success": False, "message": str(e)}
        
        @self.app.post("/api/alerts/{alert_id}/assign")
        async def assign_alert_api(
            alert_id: str,
            assigned_to: str = Form(...),
            assigned_by: str = Form(...),
            notes: Optional[str] = Form(None)
        ):
            """API endpoint to assign an alert."""
            try:
                success = await self.alert_manager.assign_alert(
                    alert_id=alert_id,
                    assigned_to=assigned_to,
                    assigned_by=assigned_by,
                    notes=notes
                )
                
                if success:
                    return {"success": True, "message": f"Alert assigned to {assigned_to}"}
                else:
                    return {"success": False, "message": "Failed to assign alert"}
                    
            except Exception as e:
                return {"success": False, "message": str(e)}
        
        @self.app.post("/api/alerts/{alert_id}/resolve")
        async def resolve_alert_api(
            alert_id: str,
            resolved_by: str = Form(...),
            resolution_type: str = Form(...),
            resolution_notes: str = Form(...)
        ):
            """API endpoint to resolve an alert."""
            try:
                success = await self.alert_manager.resolve_alert(
                    alert_id=alert_id,
                    resolved_by=resolved_by,
                    resolution_notes=resolution_notes,
                    resolution_type=resolution_type
                )
                
                if success:
                    return {"success": True, "message": "Alert resolved successfully"}
                else:
                    return {"success": False, "message": "Failed to resolve alert"}
                    
            except Exception as e:
                return {"success": False, "message": str(e)}
        
        @self.app.post("/api/alerts/{alert_id}/escalate")
        async def escalate_alert_api(
            alert_id: str,
            escalated_by: str = Form(...),
            escalation_level: str = Form(...),
            reason: str = Form(...),
            notes: Optional[str] = Form(None)
        ):
            """API endpoint to escalate an alert."""
            try:
                success = await self.escalation_engine.escalate_alert(
                    alert_id=alert_id,
                    escalated_by=escalated_by,
                    new_level=EscalationLevel(escalation_level),
                    reason=reason,
                    notes=notes
                )
                
                if success:
                    return {"success": True, "message": f"Alert escalated to {escalation_level}"}
                else:
                    return {"success": False, "message": "Failed to escalate alert"}
                    
            except Exception as e:
                return {"success": False, "message": str(e)}
        
        @self.app.post("/api/bulk-operations")
        async def bulk_operations_api(
            operation: str = Form(...),
            alert_ids: str = Form(...),  # JSON string of alert IDs
            user_id: str = Form(...),
            parameters: str = Form("{}")  # JSON string of parameters
        ):
            """API endpoint for bulk operations."""
            try:
                alert_id_list = json.loads(alert_ids)
                params = json.loads(parameters)
                
                results = await self.alert_manager.bulk_operation(
                    alert_ids=alert_id_list,
                    operation=operation,
                    user_id=user_id,
                    parameters=params
                )
                
                return {
                    "success": True,
                    "message": f"Bulk {operation} completed",
                    "results": results
                }
                
            except Exception as e:
                return {"success": False, "message": str(e)}
        
        @self.app.get("/api/search/suggestions")
        async def search_suggestions_api(query: str = Query(...)):
            """API endpoint for search suggestions."""
            try:
                suggestions = await self.search_service.get_search_suggestions(query)
                return {"suggestions": suggestions}
                
            except Exception as e:
                return {"suggestions": []}
        
        @self.app.get("/api/alerts/stats")
        async def alert_stats_api():
            """API endpoint for alert statistics."""
            try:
                stats = await self._get_dashboard_stats()
                return stats
                
            except Exception as e:
                return {"error": str(e)}
        
        @self.app.post("/api/escalation/rules")
        async def create_escalation_rule_api(
            alert_type: str = Form(...),
            severity: str = Form(...),
            escalation_delay_minutes: int = Form(...),
            escalation_level: str = Form(...),
            max_unacknowledged_time: int = Form(...),
            max_investigation_time: int = Form(...),
            configured_by: str = Form(...)
        ):
            """API endpoint to create escalation rule."""
            try:
                config = {
                    "alert_type": alert_type,
                    "severity": severity,
                    "escalation_delay_minutes": escalation_delay_minutes,
                    "escalation_level": escalation_level,
                    "max_unacknowledged_time": max_unacknowledged_time,
                    "max_investigation_time": max_investigation_time
                }
                
                success = await self.escalation_engine.configure_auto_escalation(
                    config=config,
                    configured_by=configured_by
                )
                
                if success:
                    return {"success": True, "message": "Escalation rule created successfully"}
                else:
                    return {"success": False, "message": "Failed to create escalation rule"}
                    
            except Exception as e:
                return {"success": False, "message": str(e)}
    
    async def _get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        # Mock implementation - replace with actual database queries
        return {
            "total_alerts": 156,
            "active_alerts": 47,
            "critical_alerts": 8,
            "high_alerts": 23,
            "medium_alerts": 45,
            "low_alerts": 80,
            "new_alerts": 12,
            "acknowledged_alerts": 25,
            "investigating_alerts": 10,
            "resolved_alerts": 109,
            "overdue_alerts": 3,
            "avg_response_time": 18.5,
            "avg_resolution_time": 142.3
        }
    
    async def _get_filtered_alert_count(self, filters: Dict) -> int:
        """Get count of alerts matching filters."""
        # Mock implementation
        return 47
    
    async def _get_related_alerts(self, alert_id: str) -> List[Dict]:
        """Get alerts related to the given alert."""
        # Mock implementation
        return [
            {
                "alert_id": "related_001",
                "title": "Related Alert 1",
                "similarity_score": 0.85
            },
            {
                "alert_id": "related_002", 
                "title": "Related Alert 2",
                "similarity_score": 0.72
            }
        ]
    
    async def _get_escalation_history(self, alert_id: str) -> List[Dict]:
        """Get escalation history for an alert."""
        # Mock implementation
        return [
            {
                "escalated_by": "system",
                "from_level": "level_1",
                "to_level": "level_2",
                "reason": "No acknowledgment within SLA",
                "timestamp": datetime.now() - timedelta(hours=2)
            }
        ]
    
    async def _get_recent_escalations(self) -> List[Dict]:
        """Get recent escalations."""
        # Mock implementation
        return [
            {
                "alert_id": "alert_001",
                "escalated_by": "analyst_1",
                "escalation_level": "level_2",
                "reason": "Requires supervisor attention",
                "timestamp": datetime.now() - timedelta(minutes=30)
            },
            {
                "alert_id": "alert_002",
                "escalated_by": "system",
                "escalation_level": "level_3",
                "reason": "Critical severity auto-escalation",
                "timestamp": datetime.now() - timedelta(hours=1)
            }
        ]
    
    async def _get_bulk_operation_alerts(self) -> List[Dict]:
        """Get alerts available for bulk operations."""
        # Mock implementation
        return [
            {
                "alert_id": "bulk_001",
                "title": "High Risk Content Alert",
                "severity": "high",
                "status": "new",
                "created_at": datetime.now() - timedelta(hours=2)
            },
            {
                "alert_id": "bulk_002",
                "title": "Bot Network Detection",
                "severity": "medium",
                "status": "acknowledged",
                "created_at": datetime.now() - timedelta(hours=4)
            }
        ]


# Create the FastAPI app instance
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    interface = AlertWebInterface()
    return interface.app


# For running with uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)