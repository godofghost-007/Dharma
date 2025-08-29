"""Core alert management service for handling alert operations."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from shared.models.alert import (
    Alert, AlertCreate, AlertUpdate, AlertSummary, AlertStats,
    AlertType, SeverityLevel, AlertStatus, EscalationLevel, AlertAction
)
from shared.database.manager import DatabaseManager
from ..notifications.notification_service import NotificationService
from .config import AlertConfig


class AlertManager:
    """Manages alert lifecycle operations."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.notification_service = NotificationService()
        self.config = AlertConfig()
        
    async def create_alert(self, alert_data: AlertCreate) -> Alert:
        """Create a new alert."""
        try:
            # Create alert object
            alert = Alert(
                alert_id=alert_data.alert_id or str(uuid4()),
                title=alert_data.title,
                description=alert_data.description,
                alert_type=alert_data.alert_type,
                severity=alert_data.severity,
                context=alert_data.context,
                assigned_to=alert_data.assigned_to,
                tags=alert_data.tags,
                metadata=alert_data.metadata
            )
            
            # Store in database
            await self._store_alert(alert)
            
            # Send initial notifications
            await self._send_alert_notifications(alert)
            
            return alert
            
        except Exception as e:
            raise Exception(f"Failed to create alert: {str(e)}")
    
    async def get_alerts(
        self,
        filters: Optional[Dict] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[AlertSummary]:
        """Get alerts with filtering and pagination."""
        try:
            # Build query based on filters
            query = self._build_alert_query(filters)
            
            # Get alerts from database
            alerts = await self.db_manager.postgresql.fetch_all(
                query="""
                SELECT alert_id, title, alert_type, severity, status, created_at,
                       assigned_to, acknowledged_at, resolved_at, 
                       response_time_minutes, resolution_time_minutes
                FROM alerts 
                WHERE ($1::text IS NULL OR alert_type = ANY($1::text[]))
                  AND ($2::text IS NULL OR severity = ANY($2::text[]))
                  AND ($3::text IS NULL OR status = ANY($3::text[]))
                  AND ($4::text IS NULL OR assigned_to = $4)
                  AND ($5::timestamp IS NULL OR created_at >= $5)
                  AND ($6::timestamp IS NULL OR created_at <= $6)
                ORDER BY {} {}
                LIMIT $7 OFFSET $8
                """.format(sort_by, sort_order.upper()),
                values=[
                    filters.get('alert_types') if filters else None,
                    filters.get('severities') if filters else None,
                    filters.get('statuses') if filters else None,
                    filters.get('assigned_to') if filters else None,
                    filters.get('created_after') if filters else None,
                    filters.get('created_before') if filters else None,
                    limit,
                    skip
                ]
            )
            
            return [AlertSummary(**alert) for alert in alerts]
            
        except Exception as e:
            raise Exception(f"Failed to get alerts: {str(e)}")
    
    async def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get detailed alert by ID."""
        try:
            # Get from PostgreSQL first
            alert_data = await self.db_manager.postgresql.fetch_one(
                query="SELECT * FROM alerts WHERE alert_id = $1",
                values=[alert_id]
            )
            
            if not alert_data:
                return None
            
            # Get additional context from MongoDB
            context_data = await self.db_manager.mongodb.find_one(
                collection="alert_contexts",
                filter={"alert_id": alert_id}
            )
            
            if context_data:
                alert_data['context'] = context_data.get('context', {})
            
            return Alert(**alert_data)
            
        except Exception as e:
            raise Exception(f"Failed to get alert by ID: {str(e)}")
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Acknowledge an alert."""
        try:
            # Get current alert
            alert = await self.get_alert_by_id(alert_id)
            if not alert or alert.status != AlertStatus.NEW:
                return False
            
            # Update alert
            alert.acknowledge(user_id, notes)
            
            # Save to database
            await self._update_alert_in_db(alert)
            
            # Send acknowledgment notification
            await self.notification_service.send_acknowledgment_notification(alert, user_id)
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to acknowledge alert: {str(e)}")
    
    async def assign_alert(
        self,
        alert_id: str,
        assigned_to: str,
        assigned_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """Assign an alert to a user."""
        try:
            # Get current alert
            alert = await self.get_alert_by_id(alert_id)
            if not alert:
                return False
            
            # Update alert
            alert.assign(assigned_to, assigned_by)
            if notes:
                alert.investigation_notes.append(f"Assignment note: {notes}")
            
            # Save to database
            await self._update_alert_in_db(alert)
            
            # Send assignment notification
            await self.notification_service.send_assignment_notification(alert, assigned_to)
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to assign alert: {str(e)}")
    
    async def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution_notes: str,
        resolution_type: str
    ) -> bool:
        """Resolve an alert."""
        try:
            # Get current alert
            alert = await self.get_alert_by_id(alert_id)
            if not alert or alert.status == AlertStatus.RESOLVED:
                return False
            
            # Update alert
            alert.resolve(resolved_by, resolution_notes)
            alert.metadata['resolution_type'] = resolution_type
            
            # Save to database
            await self._update_alert_in_db(alert)
            
            # Send resolution notification
            await self.notification_service.send_resolution_notification(alert, resolved_by)
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to resolve alert: {str(e)}")
    
    async def bulk_operation(
        self,
        alert_ids: List[str],
        operation: str,
        user_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform bulk operations on alerts."""
        try:
            results = {
                "successful": [],
                "failed": [],
                "total": len(alert_ids)
            }
            
            for alert_id in alert_ids:
                try:
                    if operation == "acknowledge":
                        success = await self.acknowledge_alert(
                            alert_id, user_id, parameters.get('notes')
                        )
                    elif operation == "assign":
                        success = await self.assign_alert(
                            alert_id, parameters['assigned_to'], user_id, parameters.get('notes')
                        )
                    elif operation == "resolve":
                        success = await self.resolve_alert(
                            alert_id, user_id, parameters['resolution_notes'], 
                            parameters['resolution_type']
                        )
                    else:
                        success = False
                    
                    if success:
                        results["successful"].append(alert_id)
                    else:
                        results["failed"].append({"alert_id": alert_id, "reason": "Operation failed"})
                        
                except Exception as e:
                    results["failed"].append({"alert_id": alert_id, "reason": str(e)})
            
            return results
            
        except Exception as e:
            raise Exception(f"Failed to perform bulk operation: {str(e)}")
    
    async def _store_alert(self, alert: Alert):
        """Store alert in database."""
        # Store main alert data in PostgreSQL
        await self.db_manager.postgresql.execute(
            query="""
            INSERT INTO alerts (
                alert_id, title, description, alert_type, severity, status,
                assigned_to, escalation_level, tags, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            values=[
                alert.alert_id, alert.title, alert.description,
                alert.alert_type.value, alert.severity.value, alert.status.value,
                alert.assigned_to, alert.escalation_level.value,
                alert.tags, alert.created_at, alert.updated_at
            ]
        )
        
        # Store context in MongoDB
        await self.db_manager.mongodb.insert_one(
            collection="alert_contexts",
            document={
                "alert_id": alert.alert_id,
                "context": alert.context.dict(),
                "metadata": alert.metadata,
                "actions": [action.dict() for action in alert.actions]
            }
        )
    
    async def _update_alert_in_db(self, alert: Alert):
        """Update alert in database."""
        # Update PostgreSQL
        await self.db_manager.postgresql.execute(
            query="""
            UPDATE alerts SET
                title = $2, description = $3, status = $4, severity = $5,
                assigned_to = $6, assigned_at = $7, acknowledged_by = $8,
                acknowledged_at = $9, resolved_by = $10, resolved_at = $11,
                escalation_level = $12, escalated_at = $13, escalated_by = $14,
                response_time_minutes = $15, resolution_time_minutes = $16,
                tags = $17, updated_at = $18
            WHERE alert_id = $1
            """,
            values=[
                alert.alert_id, alert.title, alert.description,
                alert.status.value, alert.severity.value, alert.assigned_to,
                alert.assigned_at, alert.acknowledged_by, alert.acknowledged_at,
                alert.resolved_by, alert.resolved_at, alert.escalation_level.value,
                alert.escalated_at, alert.escalated_by, alert.response_time_minutes,
                alert.resolution_time_minutes, alert.tags, alert.updated_at
            ]
        )
        
        # Update MongoDB
        await self.db_manager.mongodb.update_one(
            collection="alert_contexts",
            filter={"alert_id": alert.alert_id},
            update={
                "$set": {
                    "context": alert.context.dict(),
                    "metadata": alert.metadata,
                    "actions": [action.dict() for action in alert.actions],
                    "investigation_notes": alert.investigation_notes
                }
            }
        )
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send initial alert notifications."""
        await self.notification_service.send_alert_notification(alert)
    
    def _build_alert_query(self, filters: Optional[Dict]) -> str:
        """Build SQL query based on filters."""
        # This is a simplified version - in practice, you'd build dynamic queries
        return "SELECT * FROM alerts"