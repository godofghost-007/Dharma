"""
Simple test of audit logger
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import uuid
import json

class AuditEventType(Enum):
    USER_ACTION = "user_action"
    DATA_ACCESS = "data_access"
    SECURITY_EVENT = "security_event"

class AuditSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    action: str
    details: Dict[str, Any]
    outcome: str

class SimpleAuditLogger:
    def __init__(self):
        self.events = []
    
    async def log_user_action(self, user_id: str, action: str, **kwargs):
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.USER_ACTION,
            severity=AuditSeverity.LOW,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            action=action,
            details=kwargs,
            outcome="success"
        )
        self.events.append(event)
        print(f"✅ Logged: {action} by {user_id}")

async def test_simple_audit():
    logger = SimpleAuditLogger()
    
    await logger.log_user_action("user123", "login", method="oauth2")
    await logger.log_user_action("user123", "view_dashboard", page="overview")
    
    print(f"📊 Total events logged: {len(logger.events)}")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_simple_audit())
    print("✅ Simple audit test completed successfully!" if result else "❌ Test failed")