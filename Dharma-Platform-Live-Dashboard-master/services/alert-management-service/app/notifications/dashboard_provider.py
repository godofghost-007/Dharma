"""Dashboard notification provider using WebSockets for real-time notifications."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Set, Optional, List
import websockets
from websockets.server import WebSocketServerProtocol

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.models.alert import Alert, NotificationChannel, SeverityLevel
from ..core.config import config
from .notification_service import NotificationProvider, NotificationRecord, NotificationStatus

logger = logging.getLogger(__name__)


class DashboardProvider(NotificationProvider):
    """Dashboard notification provider with WebSocket support."""
    
    def __init__(self):
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.user_sessions: Dict[str, Set[WebSocketServerProtocol]] = {}
        self.notification_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # WebSocket server
        self.websocket_server = None
        self.server_port = getattr(config, 'websocket_port', 8765)
        
        # Start WebSocket server
        asyncio.create_task(self._start_websocket_server())
    
    def get_channel(self) -> NotificationChannel:
        """Get the notification channel this provider handles."""
        return NotificationChannel.DASHBOARD
    
    async def validate_recipient(self, recipient: str) -> bool:
        """Validate dashboard recipient (user ID or 'dashboard')."""
        # Dashboard notifications can be sent to specific users or broadcast
        return isinstance(recipient, str) and len(recipient) > 0
    
    async def send_notification(
        self,
        alert: Alert,
        recipient: str,
        template_data: Dict[str, Any]
    ) -> NotificationRecord:
        """Send dashboard notification via WebSocket."""
        notification_id = f"dashboard_{alert.alert_id}_{recipient}"
        record = NotificationRecord(
            notification_id=notification_id,
            alert_id=alert.alert_id,
            channel=NotificationChannel.DASHBOARD,
            recipient=recipient
        )
        
        try:
            # Prepare notification payload
            notification_payload = self._prepare_dashboard_notification(alert, template_data)
            
            # Send to specific user or broadcast
            if recipient == "dashboard" or recipient == "broadcast":
                # Broadcast to all connected clients
                sent_count = await self._broadcast_notification(notification_payload)
                record.metadata["broadcast_count"] = sent_count
            else:
                # Send to specific user
                sent_count = await self._send_to_user(recipient, notification_payload)
                record.metadata["user_sessions"] = sent_count
            
            # Add to notification history
            await self._add_to_history(notification_payload)
            
            record.mark_sent()
            logger.info(f"Dashboard notification sent: {notification_id}")
            
        except Exception as e:
            error_msg = f"Dashboard notification error: {str(e)}"
            record.mark_failed(error_msg)
            logger.error(f"Failed to send dashboard notification: {error_msg}")
        
        return record
    
    def _prepare_dashboard_notification(self, alert: Alert, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare dashboard notification payload."""
        return {
            "type": "alert_notification",
            "timestamp": datetime.utcnow().isoformat(),
            "alert": {
                "id": alert.alert_id,
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity.value,
                "alert_type": alert.alert_type.value,
                "status": alert.status.value,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                "platform": alert.context.source_platform,
                "confidence_score": alert.context.confidence_score,
                "risk_score": alert.context.risk_score,
                "affected_regions": alert.context.affected_regions,
                "tags": alert.tags
            },
            "ui": {
                "notification_title": template_data.get("notification_title", alert.title),
                "notification_message": template_data.get("notification_message", alert.description),
                "action_url": template_data.get("action_url", f"/alerts/{alert.alert_id}"),
                "severity_color": self._get_severity_color(alert.severity),
                "icon": self._get_severity_icon(alert.severity),
                "auto_dismiss": alert.severity not in [SeverityLevel.HIGH, SeverityLevel.CRITICAL],
                "dismiss_timeout": 10000 if alert.severity == SeverityLevel.LOW else 30000
            }
        }
    
    def _get_severity_color(self, severity: SeverityLevel) -> str:
        """Get color for severity level."""
        colors = {
            SeverityLevel.CRITICAL: "#dc3545",  # Red
            SeverityLevel.HIGH: "#fd7e14",      # Orange
            SeverityLevel.MEDIUM: "#ffc107",    # Yellow
            SeverityLevel.LOW: "#28a745"        # Green
        }
        return colors.get(severity, "#6c757d")
    
    def _get_severity_icon(self, severity: SeverityLevel) -> str:
        """Get icon for severity level."""
        icons = {
            SeverityLevel.CRITICAL: "alert-triangle",
            SeverityLevel.HIGH: "alert-circle",
            SeverityLevel.MEDIUM: "info",
            SeverityLevel.LOW: "check-circle"
        }
        return icons.get(severity, "bell")
    
    async def _broadcast_notification(self, payload: Dict[str, Any]) -> int:
        """Broadcast notification to all connected clients."""
        if not self.connected_clients:
            return 0
        
        message = json.dumps(payload)
        sent_count = 0
        
        # Create a copy of the set to avoid modification during iteration
        clients_copy = self.connected_clients.copy()
        
        for client in clients_copy:
            try:
                await client.send(message)
                sent_count += 1
            except websockets.exceptions.ConnectionClosed:
                # Remove disconnected client
                self.connected_clients.discard(client)
            except Exception as e:
                logger.error(f"Error sending to WebSocket client: {e}")
        
        return sent_count
    
    async def _send_to_user(self, user_id: str, payload: Dict[str, Any]) -> int:
        """Send notification to specific user sessions."""
        user_sessions = self.user_sessions.get(user_id, set())
        if not user_sessions:
            return 0
        
        message = json.dumps(payload)
        sent_count = 0
        
        # Create a copy to avoid modification during iteration
        sessions_copy = user_sessions.copy()
        
        for session in sessions_copy:
            try:
                await session.send(message)
                sent_count += 1
            except websockets.exceptions.ConnectionClosed:
                # Remove disconnected session
                user_sessions.discard(session)
                self.connected_clients.discard(session)
            except Exception as e:
                logger.error(f"Error sending to user {user_id} session: {e}")
        
        # Clean up empty user session sets
        if not user_sessions:
            self.user_sessions.pop(user_id, None)
        
        return sent_count
    
    async def _add_to_history(self, notification: Dict[str, Any]):
        """Add notification to history."""
        self.notification_history.append(notification)
        
        # Limit history size
        if len(self.notification_history) > self.max_history_size:
            self.notification_history.pop(0)
    
    async def _start_websocket_server(self):
        """Start WebSocket server for dashboard notifications."""
        try:
            self.websocket_server = await websockets.serve(
                self._handle_websocket_connection,
                "0.0.0.0",
                self.server_port
            )
            logger.info(f"Dashboard WebSocket server started on port {self.server_port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def _handle_websocket_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection."""
        logger.info(f"New WebSocket connection from {websocket.remote_address}")
        
        # Add to connected clients
        self.connected_clients.add(websocket)
        
        try:
            # Send connection acknowledgment
            await websocket.send(json.dumps({
                "type": "connection_ack",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to Project Dharma dashboard notifications"
            }))
            
            # Handle incoming messages
            async for message in websocket:
                await self._handle_websocket_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            # Clean up connection
            self.connected_clients.discard(websocket)
            
            # Remove from user sessions
            for user_id, sessions in list(self.user_sessions.items()):
                sessions.discard(websocket)
                if not sessions:
                    del self.user_sessions[user_id]
    
    async def _handle_websocket_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "authenticate":
                # Associate websocket with user
                user_id = data.get("user_id")
                if user_id:
                    if user_id not in self.user_sessions:
                        self.user_sessions[user_id] = set()
                    self.user_sessions[user_id].add(websocket)
                    
                    await websocket.send(json.dumps({
                        "type": "auth_success",
                        "user_id": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
                    # Send recent notifications
                    await self._send_recent_notifications(websocket)
            
            elif message_type == "ping":
                # Respond to ping
                await websocket.send(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            elif message_type == "get_history":
                # Send notification history
                await self._send_notification_history(websocket, data.get("limit", 50))
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received from {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def _send_recent_notifications(self, websocket: WebSocketServerProtocol):
        """Send recent notifications to newly connected client."""
        recent_notifications = self.notification_history[-10:]  # Last 10 notifications
        
        for notification in recent_notifications:
            try:
                await websocket.send(json.dumps(notification))
            except Exception as e:
                logger.error(f"Error sending recent notification: {e}")
                break
    
    async def _send_notification_history(self, websocket: WebSocketServerProtocol, limit: int):
        """Send notification history to client."""
        history = self.notification_history[-limit:] if limit > 0 else self.notification_history
        
        response = {
            "type": "notification_history",
            "timestamp": datetime.utcnow().isoformat(),
            "notifications": history,
            "total_count": len(self.notification_history)
        }
        
        try:
            await websocket.send(json.dumps(response))
        except Exception as e:
            logger.error(f"Error sending notification history: {e}")
    
    async def send_system_notification(self, message: str, notification_type: str = "info"):
        """Send system notification to all connected clients."""
        payload = {
            "type": "system_notification",
            "timestamp": datetime.utcnow().isoformat(),
            "notification_type": notification_type,
            "message": message,
            "ui": {
                "icon": "info" if notification_type == "info" else "alert-triangle",
                "auto_dismiss": True,
                "dismiss_timeout": 5000
            }
        }
        
        await self._broadcast_notification(payload)
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self.connected_clients),
            "authenticated_users": len(self.user_sessions),
            "notification_history_size": len(self.notification_history),
            "server_port": self.server_port,
            "server_running": self.websocket_server is not None
        }
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get dashboard provider statistics."""
        return await self.get_connection_stats()
    
    async def close(self):
        """Close WebSocket server and connections."""
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        # Close all client connections
        for client in self.connected_clients.copy():
            await client.close()


class DashboardNotificationManager:
    """Manages dashboard-specific notification features."""
    
    def __init__(self, dashboard_provider: DashboardProvider):
        self.provider = dashboard_provider
        self.notification_filters: Dict[str, Dict[str, Any]] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
    
    async def set_user_notification_filter(self, user_id: str, filters: Dict[str, Any]):
        """Set notification filters for a user."""
        self.notification_filters[user_id] = filters
    
    async def should_send_to_user(self, user_id: str, alert: Alert) -> bool:
        """Check if notification should be sent to user based on filters."""
        filters = self.notification_filters.get(user_id, {})
        
        # Check severity filter
        min_severity = filters.get("min_severity")
        if min_severity:
            severity_levels = ["low", "medium", "high", "critical"]
            if severity_levels.index(alert.severity.value) < severity_levels.index(min_severity):
                return False
        
        # Check alert type filter
        allowed_types = filters.get("alert_types")
        if allowed_types and alert.alert_type.value not in allowed_types:
            return False
        
        # Check platform filter
        allowed_platforms = filters.get("platforms")
        if allowed_platforms and alert.context.source_platform not in allowed_platforms:
            return False
        
        return True
    
    async def send_bulk_notification(self, alerts: List[Alert], message: str):
        """Send bulk notification for multiple alerts."""
        payload = {
            "type": "bulk_alert_notification",
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "alert_count": len(alerts),
            "alerts": [
                {
                    "id": alert.alert_id,
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None
                }
                for alert in alerts[:10]  # Limit to first 10 alerts
            ],
            "ui": {
                "icon": "layers",
                "auto_dismiss": False,
                "action_url": "/alerts"
            }
        }
        
        await self.provider._broadcast_notification(payload)