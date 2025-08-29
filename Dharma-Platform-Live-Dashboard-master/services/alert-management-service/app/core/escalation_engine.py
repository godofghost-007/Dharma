"""Alert escalation engine for automated escalation workflows."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from shared.models.alert import (
    Alert, AlertType, SeverityLevel, AlertStatus, EscalationLevel, EscalationRule
)
from shared.database.manager import DatabaseManager
from ..notifications.notification_service import NotificationService
from .config import AlertConfig


class EscalationEngine:
    """Manages alert escalation workflows and automation."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.notification_service = NotificationService()
        self.config = AlertConfig()
        self._escalation_rules: Dict[str, EscalationRule] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    async def initialize(self):
        """Initialize escalation engine with rules from database."""
        try:
            # Load escalation rules from database
            rules = await self.db_manager.postgresql.fetch_all(
                query="""
                SELECT alert_type, severity, escalation_delay_minutes,
                       escalation_level, auto_escalate, max_unacknowledged_time,
                       max_investigation_time
                FROM escalation_rules
                WHERE active = true
                """
            )
            
            for rule_data in rules:
                rule = EscalationRule(**rule_data)
                rule_key = f"{rule.alert_type}_{rule.severity}"
                self._escalation_rules[rule_key] = rule
            
            # Start background escalation monitor
            asyncio.create_task(self._monitor_escalations())
            
        except Exception as e:
            raise Exception(f"Failed to initialize escalation engine: {str(e)}")
    
    async def escalate_alert(
        self,
        alert_id: str,
        escalated_by: str,
        new_level: EscalationLevel,
        reason: str,
        notes: Optional[str] = None
    ) -> bool:
        """Manually escalate an alert."""
        try:
            # Get current alert
            alert_data = await self.db_manager.postgresql.fetch_one(
                query="SELECT * FROM alerts WHERE alert_id = $1",
                values=[alert_id]
            )
            
            if not alert_data:
                return False
            
            alert = Alert(**alert_data)
            
            # Perform escalation
            alert.escalate(escalated_by, new_level, f"{reason}. {notes or ''}")
            
            # Update in database
            await self._update_alert_escalation(alert)
            
            # Send escalation notifications
            await self._send_escalation_notifications(alert, reason)
            
            # Log escalation
            await self._log_escalation(alert_id, escalated_by, new_level, reason, manual=True)
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to escalate alert: {str(e)}")
    
    async def configure_auto_escalation(
        self,
        config: Dict[str, Any],
        configured_by: str
    ) -> bool:
        """Configure automatic escalation rules."""
        try:
            # Validate configuration
            if not self._validate_escalation_config(config):
                return False
            
            # Create or update escalation rule
            rule = EscalationRule(
                alert_type=AlertType(config['alert_type']),
                severity=SeverityLevel(config['severity']),
                escalation_delay_minutes=config['escalation_delay_minutes'],
                escalation_level=EscalationLevel(config['escalation_level']),
                auto_escalate=config.get('auto_escalate', True),
                max_unacknowledged_time=config['max_unacknowledged_time'],
                max_investigation_time=config['max_investigation_time']
            )
            
            # Store in database
            await self.db_manager.postgresql.execute(
                query="""
                INSERT INTO escalation_rules (
                    alert_type, severity, escalation_delay_minutes,
                    escalation_level, auto_escalate, max_unacknowledged_time,
                    max_investigation_time, configured_by, created_at, active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (alert_type, severity) 
                DO UPDATE SET
                    escalation_delay_minutes = EXCLUDED.escalation_delay_minutes,
                    escalation_level = EXCLUDED.escalation_level,
                    auto_escalate = EXCLUDED.auto_escalate,
                    max_unacknowledged_time = EXCLUDED.max_unacknowledged_time,
                    max_investigation_time = EXCLUDED.max_investigation_time,
                    configured_by = EXCLUDED.configured_by,
                    updated_at = CURRENT_TIMESTAMP
                """,
                values=[
                    rule.alert_type.value, rule.severity.value,
                    rule.escalation_delay_minutes, rule.escalation_level.value,
                    rule.auto_escalate, rule.max_unacknowledged_time,
                    rule.max_investigation_time, configured_by,
                    datetime.utcnow(), True
                ]
            )
            
            # Update in-memory rules
            rule_key = f"{rule.alert_type}_{rule.severity}"
            self._escalation_rules[rule_key] = rule
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to configure auto-escalation: {str(e)}")
    
    async def schedule_escalation(self, alert: Alert):
        """Schedule automatic escalation for an alert."""
        try:
            rule_key = f"{alert.alert_type}_{alert.severity}"
            rule = self._escalation_rules.get(rule_key)
            
            if not rule or not rule.auto_escalate:
                return
            
            # Cancel existing escalation task if any
            if alert.alert_id in self._running_tasks:
                self._running_tasks[alert.alert_id].cancel()
            
            # Schedule new escalation task
            delay_seconds = rule.escalation_delay_minutes * 60
            task = asyncio.create_task(
                self._auto_escalate_after_delay(alert.alert_id, delay_seconds, rule)
            )
            self._running_tasks[alert.alert_id] = task
            
        except Exception as e:
            # Log error but don't raise to avoid breaking alert creation
            print(f"Failed to schedule escalation for alert {alert.alert_id}: {str(e)}")
    
    async def cancel_escalation(self, alert_id: str):
        """Cancel scheduled escalation for an alert."""
        if alert_id in self._running_tasks:
            self._running_tasks[alert_id].cancel()
            del self._running_tasks[alert_id]
    
    async def get_escalation_rules(self) -> List[EscalationRule]:
        """Get all active escalation rules."""
        try:
            rules_data = await self.db_manager.postgresql.fetch_all(
                query="""
                SELECT alert_type, severity, escalation_delay_minutes,
                       escalation_level, auto_escalate, max_unacknowledged_time,
                       max_investigation_time
                FROM escalation_rules
                WHERE active = true
                ORDER BY alert_type, severity
                """
            )
            
            return [EscalationRule(**rule_data) for rule_data in rules_data]
            
        except Exception as e:
            raise Exception(f"Failed to get escalation rules: {str(e)}")
    
    async def _monitor_escalations(self):
        """Background task to monitor and trigger escalations."""
        while True:
            try:
                # Check for alerts that need escalation
                alerts_to_escalate = await self._find_alerts_needing_escalation()
                
                for alert_data in alerts_to_escalate:
                    alert = Alert(**alert_data)
                    await self._perform_auto_escalation(alert)
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                print(f"Error in escalation monitor: {str(e)}")
                await asyncio.sleep(60)
    
    async def _find_alerts_needing_escalation(self) -> List[Dict]:
        """Find alerts that need automatic escalation."""
        try:
            # Find unacknowledged alerts past their escalation time
            unacknowledged_alerts = await self.db_manager.postgresql.fetch_all(
                query="""
                SELECT a.*, er.max_unacknowledged_time, er.escalation_level
                FROM alerts a
                JOIN escalation_rules er ON a.alert_type = er.alert_type 
                    AND a.severity = er.severity
                WHERE a.status = 'new'
                  AND er.auto_escalate = true
                  AND a.created_at < NOW() - INTERVAL '1 minute' * er.max_unacknowledged_time
                  AND a.escalation_level < er.escalation_level
                """
            )
            
            # Find investigating alerts past their investigation time
            investigating_alerts = await self.db_manager.postgresql.fetch_all(
                query="""
                SELECT a.*, er.max_investigation_time, er.escalation_level
                FROM alerts a
                JOIN escalation_rules er ON a.alert_type = er.alert_type 
                    AND a.severity = er.severity
                WHERE a.status = 'investigating'
                  AND er.auto_escalate = true
                  AND a.acknowledged_at < NOW() - INTERVAL '1 minute' * er.max_investigation_time
                  AND a.escalation_level < er.escalation_level
                """
            )
            
            return unacknowledged_alerts + investigating_alerts
            
        except Exception as e:
            raise Exception(f"Failed to find alerts needing escalation: {str(e)}")
    
    async def _auto_escalate_after_delay(
        self,
        alert_id: str,
        delay_seconds: int,
        rule: EscalationRule
    ):
        """Auto-escalate alert after specified delay."""
        try:
            await asyncio.sleep(delay_seconds)
            
            # Check if alert still needs escalation
            alert_data = await self.db_manager.postgresql.fetch_one(
                query="SELECT * FROM alerts WHERE alert_id = $1",
                values=[alert_id]
            )
            
            if not alert_data:
                return
            
            alert = Alert(**alert_data)
            
            # Only escalate if still in appropriate status
            if alert.status in [AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING]:
                await self._perform_auto_escalation(alert, rule)
            
        except asyncio.CancelledError:
            # Escalation was cancelled (e.g., alert was resolved)
            pass
        except Exception as e:
            print(f"Error in auto-escalation for alert {alert_id}: {str(e)}")
        finally:
            # Clean up task reference
            if alert_id in self._running_tasks:
                del self._running_tasks[alert_id]
    
    async def _perform_auto_escalation(self, alert: Alert, rule: Optional[EscalationRule] = None):
        """Perform automatic escalation of an alert."""
        try:
            if not rule:
                rule_key = f"{alert.alert_type}_{alert.severity}"
                rule = self._escalation_rules.get(rule_key)
                if not rule:
                    return
            
            # Determine escalation reason
            if alert.status == AlertStatus.NEW:
                reason = f"Auto-escalated: No acknowledgment within {rule.max_unacknowledged_time} minutes"
            else:
                reason = f"Auto-escalated: Investigation time exceeded {rule.max_investigation_time} minutes"
            
            # Perform escalation
            alert.escalate("system", rule.escalation_level, reason)
            
            # Update in database
            await self._update_alert_escalation(alert)
            
            # Send escalation notifications
            await self._send_escalation_notifications(alert, reason)
            
            # Log escalation
            await self._log_escalation(
                alert.alert_id, "system", rule.escalation_level, reason, manual=False
            )
            
        except Exception as e:
            raise Exception(f"Failed to perform auto-escalation: {str(e)}")
    
    async def _update_alert_escalation(self, alert: Alert):
        """Update alert escalation in database."""
        await self.db_manager.postgresql.execute(
            query="""
            UPDATE alerts SET
                status = $2, escalation_level = $3, escalated_at = $4,
                escalated_by = $5, updated_at = $6
            WHERE alert_id = $1
            """,
            values=[
                alert.alert_id, alert.status.value, alert.escalation_level.value,
                alert.escalated_at, alert.escalated_by, alert.updated_at
            ]
        )
    
    async def _send_escalation_notifications(self, alert: Alert, reason: str):
        """Send escalation notifications."""
        await self.notification_service.send_escalation_notification(alert, reason)
    
    async def _log_escalation(
        self,
        alert_id: str,
        escalated_by: str,
        escalation_level: EscalationLevel,
        reason: str,
        manual: bool
    ):
        """Log escalation event."""
        await self.db_manager.postgresql.execute(
            query="""
            INSERT INTO escalation_log (
                alert_id, escalated_by, escalation_level, reason,
                manual_escalation, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            values=[
                alert_id, escalated_by, escalation_level.value,
                reason, manual, datetime.utcnow()
            ]
        )
    
    def _validate_escalation_config(self, config: Dict[str, Any]) -> bool:
        """Validate escalation configuration."""
        required_fields = [
            'alert_type', 'severity', 'escalation_delay_minutes',
            'escalation_level', 'max_unacknowledged_time', 'max_investigation_time'
        ]
        
        for field in required_fields:
            if field not in config:
                return False
        
        # Validate enum values
        try:
            AlertType(config['alert_type'])
            SeverityLevel(config['severity'])
            EscalationLevel(config['escalation_level'])
        except ValueError:
            return False
        
        # Validate time values
        if any(config[field] < 0 for field in [
            'escalation_delay_minutes', 'max_unacknowledged_time', 'max_investigation_time'
        ]):
            return False
        
        return True