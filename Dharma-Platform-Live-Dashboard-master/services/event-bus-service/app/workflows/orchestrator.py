"""
Workflow orchestration using Temporal
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)

@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    step_id: str
    service: str
    action: str
    parameters: Dict[str, Any]
    depends_on: List[str] = None
    retry_policy: Optional[RetryPolicy] = None
    timeout: Optional[timedelta] = None

@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    max_execution_time: timedelta = timedelta(hours=1)

class WorkflowOrchestrator:
    """Orchestrates complex workflows using Temporal"""
    
    def __init__(self, temporal_host: str = "localhost:7233"):
        self.temporal_host = temporal_host
        self.client = None
        self.worker = None
        self.workflows = {}
        
    async def initialize(self):
        """Initialize Temporal client"""
        try:
            self.client = await Client.connect(self.temporal_host)
            logger.info(f"Connected to Temporal at {self.temporal_host}")
        except Exception as e:
            logger.error(f"Failed to connect to Temporal: {e}")
            raise
    
    async def register_workflow(self, workflow_def: WorkflowDefinition):
        """Register a workflow definition"""
        self.workflows[workflow_def.workflow_id] = workflow_def
        logger.info(f"Registered workflow: {workflow_def.name}")
    
    async def start_data_processing_workflow(self, data_source: str, parameters: Dict[str, Any]) -> str:
        """Start data collection and processing workflow"""
        workflow_id = f"data_processing_{data_source}_{int(datetime.utcnow().timestamp())}"
        
        workflow_def = WorkflowDefinition(
            workflow_id=workflow_id,
            name="Data Processing Pipeline",
            description=f"Complete data processing pipeline for {data_source}",
            steps=[
                WorkflowStep(
                    step_id="collect_data",
                    service="data_collection",
                    action="collect",
                    parameters={"source": data_source, **parameters},
                    timeout=timedelta(minutes=30)
                ),
                WorkflowStep(
                    step_id="analyze_sentiment",
                    service="ai_analysis",
                    action="analyze_sentiment",
                    parameters={"batch_size": 100},
                    depends_on=["collect_data"],
                    timeout=timedelta(minutes=15)
                ),
                WorkflowStep(
                    step_id="detect_bots",
                    service="ai_analysis", 
                    action="detect_bots",
                    parameters={"threshold": 0.7},
                    depends_on=["collect_data"],
                    timeout=timedelta(minutes=20)
                ),
                WorkflowStep(
                    step_id="detect_campaigns",
                    service="campaign_detection",
                    action="detect_campaigns",
                    parameters={"time_window": "1h"},
                    depends_on=["analyze_sentiment", "detect_bots"],
                    timeout=timedelta(minutes=25)
                ),
                WorkflowStep(
                    step_id="generate_alerts",
                    service="alert_management",
                    action="generate_alerts",
                    parameters={"severity_threshold": "medium"},
                    depends_on=["detect_campaigns"],
                    timeout=timedelta(minutes=5)
                )
            ]
        )
        
        await self.register_workflow(workflow_def)
        return await self.execute_workflow(workflow_def)
    
    async def start_model_retraining_workflow(self, model_type: str, training_data: Dict[str, Any]) -> str:
        """Start automated model retraining workflow"""
        workflow_id = f"model_retraining_{model_type}_{int(datetime.utcnow().timestamp())}"
        
        workflow_def = WorkflowDefinition(
            workflow_id=workflow_id,
            name="Model Retraining Pipeline",
            description=f"Automated retraining pipeline for {model_type} model",
            steps=[
                WorkflowStep(
                    step_id="prepare_training_data",
                    service="data_processing",
                    action="prepare_data",
                    parameters={"model_type": model_type, **training_data},
                    timeout=timedelta(hours=1)
                ),
                WorkflowStep(
                    step_id="train_model",
                    service="ml_training",
                    action="train",
                    parameters={"model_type": model_type},
                    depends_on=["prepare_training_data"],
                    timeout=timedelta(hours=4)
                ),
                WorkflowStep(
                    step_id="validate_model",
                    service="ml_validation",
                    action="validate",
                    parameters={"validation_threshold": 0.85},
                    depends_on=["train_model"],
                    timeout=timedelta(minutes=30)
                ),
                WorkflowStep(
                    step_id="deploy_model",
                    service="model_deployment",
                    action="deploy",
                    parameters={"deployment_strategy": "blue_green"},
                    depends_on=["validate_model"],
                    timeout=timedelta(minutes=15)
                ),
                WorkflowStep(
                    step_id="invalidate_caches",
                    service="cache_management",
                    action="invalidate",
                    parameters={"cache_pattern": f"model_{model_type}*"},
                    depends_on=["deploy_model"],
                    timeout=timedelta(minutes=5)
                )
            ]
        )
        
        await self.register_workflow(workflow_def)
        return await self.execute_workflow(workflow_def)
    
    async def execute_workflow(self, workflow_def: WorkflowDefinition) -> str:
        """Execute a workflow using Temporal"""
        if not self.client:
            raise RuntimeError("Temporal client not initialized")
            
        try:
            # Start workflow execution
            handle = await self.client.start_workflow(
                DataProcessingWorkflow.run,
                workflow_def,
                id=workflow_def.workflow_id,
                task_queue="dharma-workflows",
                execution_timeout=workflow_def.max_execution_time
            )
            
            logger.info(f"Started workflow {workflow_def.workflow_id}")
            return handle.id
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_def.workflow_id}: {e}")
            raise
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow execution status"""
        if not self.client:
            raise RuntimeError("Temporal client not initialized")
            
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            result = await handle.describe()
            
            return {
                "workflow_id": workflow_id,
                "status": result.status,
                "start_time": result.start_time,
                "execution_time": result.execution_time,
                "close_time": result.close_time
            }
        except Exception as e:
            logger.error(f"Failed to get workflow status for {workflow_id}: {e}")
            raise
    
    async def cancel_workflow(self, workflow_id: str, reason: str = "User requested"):
        """Cancel a running workflow"""
        if not self.client:
            raise RuntimeError("Temporal client not initialized")
            
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            await handle.cancel()
            logger.info(f"Cancelled workflow {workflow_id}: {reason}")
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            raise

@workflow.defn
class DataProcessingWorkflow:
    """Temporal workflow for data processing pipeline"""
    
    @workflow.run
    async def run(self, workflow_def: WorkflowDefinition) -> Dict[str, Any]:
        """Execute the data processing workflow"""
        results = {}
        completed_steps = set()
        
        # Execute steps based on dependencies
        for step in self._get_execution_order(workflow_def.steps):
            try:
                # Check if dependencies are met
                if step.depends_on:
                    missing_deps = set(step.depends_on) - completed_steps
                    if missing_deps:
                        raise workflow.ApplicationError(f"Missing dependencies: {missing_deps}")
                
                # Execute step
                result = await workflow.execute_activity(
                    execute_workflow_step,
                    step,
                    start_to_close_timeout=step.timeout or timedelta(minutes=10),
                    retry_policy=step.retry_policy or RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(seconds=60),
                        maximum_attempts=3
                    )
                )
                
                results[step.step_id] = result
                completed_steps.add(step.step_id)
                
                logger.info(f"Completed workflow step: {step.step_id}")
                
            except Exception as e:
                logger.error(f"Workflow step {step.step_id} failed: {e}")
                results[step.step_id] = {"error": str(e)}
                raise workflow.ApplicationError(f"Step {step.step_id} failed: {e}")
        
        return {
            "workflow_id": workflow_def.workflow_id,
            "status": "completed",
            "results": results,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    def _get_execution_order(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """Determine execution order based on dependencies"""
        ordered_steps = []
        remaining_steps = steps.copy()
        
        while remaining_steps:
            # Find steps with no unmet dependencies
            ready_steps = []
            for step in remaining_steps:
                if not step.depends_on or all(dep in [s.step_id for s in ordered_steps] for dep in step.depends_on):
                    ready_steps.append(step)
            
            if not ready_steps:
                raise workflow.ApplicationError("Circular dependency detected in workflow steps")
            
            # Add ready steps to execution order
            for step in ready_steps:
                ordered_steps.append(step)
                remaining_steps.remove(step)
        
        return ordered_steps

@activity.defn
async def execute_workflow_step(step: WorkflowStep) -> Dict[str, Any]:
    """Execute individual workflow step"""
    logger.info(f"Executing step {step.step_id} on service {step.service}")
    
    # This would make actual service calls
    # For now, simulate step execution
    await asyncio.sleep(1)  # Simulate processing time
    
    return {
        "step_id": step.step_id,
        "service": step.service,
        "action": step.action,
        "status": "completed",
        "executed_at": datetime.utcnow().isoformat()
    }