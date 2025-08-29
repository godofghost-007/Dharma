"""
Workflow monitoring types and enums
"""
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from enum import Enum

class WorkflowStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

@dataclass
class WorkflowMetrics:
    """Workflow execution metrics"""
    workflow_id: str
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[timedelta] = None
    steps_completed: int = 0
    steps_failed: int = 0
    error_count: int = 0
    retry_count: int = 0