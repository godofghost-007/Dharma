"""
Workflow monitoring and error recovery
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from temporalio.client import Client

logger = logging.getLogger(__name__)

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

class WorkflowMonitor:
    """Monitors workflow execution and handles error recovery"""
    
    def __init__(self, temporal_client: Client):
        self.client = temporal_client
        self.active_workflows = {}
        self.workflow_metrics = {}
        self.monitoring_active = False
        
    async def start_monitoring(self):
        """Start workflow monitoring"""
        self.monitoring_active = True
        asyncio.create_task(self._monitor_workflows())
        logger.info("Workflow monitoring started")
    
    async def stop_monitoring(self):
        """Stop workflow monitoring"""
        self.monitoring_active = False
        logger.info("Workflow monitoring stopped")
    
    async def register_workflow(self, workflow_id: str):
        """Register workflow for monitoring"""
        self.active_workflows[workflow_id] = {
            "registered_at": datetime.utcnow(),
            "last_check": None,
            "status": WorkflowStatus.RUNNING
        }
        
        self.workflow_metrics[workflow_id] = WorkflowMetrics(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.utcnow()
        )
        
        logger.info(f"Registered workflow for monitoring: {workflow_id}")
    
    async def _monitor_workflows(self):
        """Monitor active workflows"""
        while self.monitoring_active:
            try:
                for workflow_id in list(self.active_workflows.keys()):
                    await self._check_workflow_health(workflow_id)
                
                # Sleep between monitoring cycles
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in workflow monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_workflow_health(self, workflow_id: str):
        """Check individual workflow health"""
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            description = await handle.describe()
            
            # Update workflow status
            current_status = self._map_temporal_status(description.status)
            self.active_workflows[workflow_id]["status"] = current_status
            self.active_workflows[workflow_id]["last_check"] = datetime.utcnow()
            
            # Update metrics
            metrics = self.workflow_metrics[workflow_id]
            metrics.status = current_status
            
            if description.close_time:
                metrics.end_time = description.close_time
                metrics.duration = description.close_time - metrics.start_time
            
            # Handle workflow completion or failure
            if current_status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, 
                                WorkflowStatus.CANCELLED, WorkflowStatus.TIMEOUT]:
                await self._handle_workflow_completion(workflow_id, current_status)
                
            # Check for stuck workflows
            elif await self._is_workflow_stuck(workflow_id):
                await self._handle_stuck_workflow(workflow_id)
                
        except Exception as e:
            logger.error(f"Error checking workflow {workflow_id}: {e}")
            await self._handle_monitoring_error(workflow_id, e)
    
    def _map_temporal_status(self, temporal_status) -> WorkflowStatus:
        """Map Temporal status to our WorkflowStatus enum"""
        status_mapping = {
            "WORKFLOW_EXECUTION_STATUS_RUNNING": WorkflowStatus.RUNNING,
            "WORKFLOW_EXECUTION_STATUS_COMPLETED": WorkflowStatus.COMPLETED,
            "WORKFLOW_EXECUTION_STATUS_FAILED": WorkflowStatus.FAILED,
            "WORKFLOW_EXECUTION_STATUS_CANCELED": WorkflowStatus.CANCELLED,
            "WORKFLOW_EXECUTION_STATUS_TERMINATED": WorkflowStatus.FAILED,
            "WORKFLOW_EXECUTION_STATUS_CONTINUED_AS_NEW": WorkflowStatus.RUNNING,
            "WORKFLOW_EXECUTION_STATUS_TIMED_OUT": WorkflowStatus.TIMEOUT
        }
        return status_mapping.get(str(temporal_status), WorkflowStatus.FAILED)
    
    async def _is_workflow_stuck(self, workflow_id: str) -> bool:
        """Check if workflow appears to be stuck"""
        workflow_info = self.active_workflows[workflow_id]
        
        # Consider workflow stuck if running for more than 2 hours without progress
        if workflow_info["status"] == WorkflowStatus.RUNNING:
            registered_time = workflow_info["registered_at"]
            if datetime.utcnow() - registered_time > timedelta(hours=2):
                return True
        
        return False
    
    async def _handle_workflow_completion(self, workflow_id: str, status: WorkflowStatus):
        """Handle workflow completion"""
        logger.info(f"Workflow {workflow_id} completed with status: {status}")
        
        # Remove from active monitoring
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
        
        # Log final metrics
        metrics = self.workflow_metrics.get(workflow_id)
        if metrics:
            logger.info(f"Workflow {workflow_id} metrics: duration={metrics.duration}, "
                       f"steps_completed={metrics.steps_completed}, "
                       f"steps_failed={metrics.steps_failed}")
    
    async def _handle_stuck_workflow(self, workflow_id: str):
        """Handle stuck workflow"""
        logger.warning(f"Workflow {workflow_id} appears to be stuck")
        
        try:
            # Try to cancel stuck workflow
            handle = self.client.get_workflow_handle(workflow_id)
            await handle.cancel()
            logger.info(f"Cancelled stuck workflow: {workflow_id}")
            
            # Update metrics
            metrics = self.workflow_metrics[workflow_id]
            metrics.status = WorkflowStatus.CANCELLED
            metrics.end_time = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to cancel stuck workflow {workflow_id}: {e}")
    
    async def _handle_monitoring_error(self, workflow_id: str, error: Exception):
        """Handle monitoring errors"""
        logger.error(f"Monitoring error for workflow {workflow_id}: {error}")
        
        # Update error count in metrics
        if workflow_id in self.workflow_metrics:
            self.workflow_metrics[workflow_id].error_count += 1
    
    async def get_workflow_metrics(self, workflow_id: str) -> Optional[WorkflowMetrics]:
        """Get metrics for specific workflow"""
        return self.workflow_metrics.get(workflow_id)
    
    async def get_all_metrics(self) -> Dict[str, WorkflowMetrics]:
        """Get metrics for all workflows"""
        return self.workflow_metrics.copy()
    
    async def get_active_workflows(self) -> List[str]:
        """Get list of active workflow IDs"""
        return list(self.active_workflows.keys())

class ErrorRecoveryManager:
    """Handles workflow error recovery strategies"""
    
    def __init__(self, workflow_monitor: WorkflowMonitor, orchestrator):
        self.monitor = workflow_monitor
        self.orchestrator = orchestrator
        self.recovery_strategies = {}
        
    def register_recovery_strategy(self, workflow_type: str, strategy_func):
        """Register recovery strategy for workflow type"""
        self.recovery_strategies[workflow_type] = strategy_func
        logger.info(f"Registered recovery strategy for {workflow_type}")
    
    async def handle_workflow_failure(self, workflow_id: str, error: Exception):
        """Handle workflow failure with appropriate recovery strategy"""
        logger.info(f"Handling failure for workflow {workflow_id}: {error}")
        
        # Determine workflow type from ID
        workflow_type = self._extract_workflow_type(workflow_id)
        
        # Apply recovery strategy if available
        if workflow_type in self.recovery_strategies:
            try:
                await self.recovery_strategies[workflow_type](workflow_id, error)
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed for {workflow_id}: {recovery_error}")
        else:
            # Default recovery: log and alert
            await self._default_recovery(workflow_id, error)
    
    def _extract_workflow_type(self, workflow_id: str) -> str:
        """Extract workflow type from workflow ID"""
        # Assuming workflow IDs follow pattern: type_source_timestamp
        parts = workflow_id.split('_')
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"
        return "unknown"
    
    async def _default_recovery(self, workflow_id: str, error: Exception):
        """Default recovery strategy"""
        logger.warning(f"No specific recovery strategy for {workflow_id}, using default")
        
        # Log error details
        error_details = {
            "workflow_id": workflow_id,
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "recovery_action": "manual_intervention_required"
        }
        
        # This would typically send an alert to operations team
        logger.error(f"Workflow failure requires manual intervention: {error_details}")
    
    async def retry_failed_workflow(self, workflow_id: str, max_retries: int = 3):
        """Retry failed workflow with exponential backoff"""
        workflow_type = self._extract_workflow_type(workflow_id)
        
        for attempt in range(max_retries):
            try:
                # Wait with exponential backoff
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                
                # Restart workflow (this would need workflow definition)
                logger.info(f"Retrying workflow {workflow_id}, attempt {attempt + 1}")
                
                # This would restart the workflow with original parameters
                # Implementation depends on how workflow definitions are stored
                
                return True
                
            except Exception as e:
                logger.error(f"Retry attempt {attempt + 1} failed for {workflow_id}: {e}")
                
                if attempt == max_retries - 1:
                    logger.error(f"All retry attempts exhausted for {workflow_id}")
                    return False
        
        return False