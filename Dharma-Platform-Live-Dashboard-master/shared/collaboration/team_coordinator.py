"""
Team coordination and workflow management
"""

import logging
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskStatus(Enum):
    """Individual task status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class NotificationType(Enum):
    """Types of team notifications"""
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    DEADLINE_APPROACHING = "deadline_approaching"
    ESCALATION = "escalation"
    MENTION = "mention"
    COMMENT_ADDED = "comment_added"

@dataclass
class WorkflowTask:
    """Individual task in a workflow"""
    task_id: str
    name: str
    description: str
    assigned_to: Optional[str] = None
    
    # Dependencies and ordering
    depends_on: List[str] = field(default_factory=list)  # Task IDs
    blocks: List[str] = field(default_factory=list)  # Task IDs
    
    # Status and timing
    status: TaskStatus = TaskStatus.NOT_STARTED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    
    # Execution details
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    progress_percentage: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    # Results
    result: Optional[Any] = None
    error_message: Optional[str] = None

@dataclass
class TeamWorkflow:
    """Workflow definition for team coordination"""
    workflow_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime
    
    # Tasks and execution
    tasks: Dict[str, WorkflowTask] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    
    # Team and assignments
    team_members: Set[str] = field(default_factory=set)
    workspace_id: Optional[str] = None
    
    # Scheduling and deadlines
    scheduled_start: Optional[datetime] = None
    deadline: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Configuration
    auto_start: bool = False
    allow_parallel: bool = True
    failure_policy: str = "stop"  # "stop", "continue", "retry"
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

@dataclass
class TeamNotification:
    """Team notification message"""
    notification_id: str
    notification_type: NotificationType
    recipient_id: str
    sender_id: Optional[str]
    
    # Content
    title: str
    message: str
    action_url: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"  # "low", "normal", "high", "urgent"

class TeamCoordinator:
    """Coordinates team activities and communications"""
    
    def __init__(self, storage_backend=None, notification_service=None):
        """Initialize team coordinator"""
        self.storage_backend = storage_backend
        self.notification_service = notification_service
        
        # Team data
        self.teams: Dict[str, Set[str]] = {}  # team_id -> user_ids
        self.user_teams: Dict[str, Set[str]] = {}  # user_id -> team_ids
        
        # Notifications
        self.notifications: Dict[str, TeamNotification] = {}
        self.user_notifications: Dict[str, List[str]] = {}  # user_id -> notification_ids
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
    
    async def create_team(
        self,
        team_name: str,
        team_description: str,
        created_by: str,
        initial_members: Optional[List[str]] = None
    ) -> str:
        """Create a new team"""
        
        team_id = str(uuid.uuid4())
        members = set(initial_members or [])
        members.add(created_by)  # Creator is always a member
        
        self.teams[team_id] = members
        
        # Update user teams mapping
        for user_id in members:
            if user_id not in self.user_teams:
                self.user_teams[user_id] = set()
            self.user_teams[user_id].add(team_id)
        
        # Persist to storage
        if self.storage_backend:
            await self.storage_backend.save_team(team_id, {
                'name': team_name,
                'description': team_description,
                'created_by': created_by,
                'created_at': datetime.utcnow().isoformat(),
                'members': list(members)
            })
        
        logger.info(f"Created team {team_id}: {team_name}")
        return team_id
    
    async def add_team_member(
        self,
        team_id: str,
        user_id: str,
        added_by: str
    ) -> bool:
        """Add member to team"""
        
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
        
        # Check if user is already a member
        if user_id in self.teams[team_id]:
            return False
        
        # Add to team
        self.teams[team_id].add(user_id)
        
        # Update user teams mapping
        if user_id not in self.user_teams:
            self.user_teams[user_id] = set()
        self.user_teams[user_id].add(team_id)
        
        # Send notification
        await self.send_notification(
            recipient_id=user_id,
            notification_type=NotificationType.MENTION,
            title="Added to Team",
            message=f"You have been added to a team by {added_by}",
            sender_id=added_by,
            metadata={'team_id': team_id}
        )
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.update_team_members(team_id, list(self.teams[team_id]))
        
        return True
    
    async def remove_team_member(
        self,
        team_id: str,
        user_id: str,
        removed_by: str
    ) -> bool:
        """Remove member from team"""
        
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
        
        if user_id not in self.teams[team_id]:
            return False
        
        # Remove from team
        self.teams[team_id].discard(user_id)
        
        # Update user teams mapping
        if user_id in self.user_teams:
            self.user_teams[user_id].discard(team_id)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.update_team_members(team_id, list(self.teams[team_id]))
        
        return True
    
    async def send_notification(
        self,
        recipient_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        sender_id: Optional[str] = None,
        action_url: Optional[str] = None,
        priority: str = "normal",
        scheduled_for: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send notification to team member"""
        
        notification_id = str(uuid.uuid4())
        
        notification = TeamNotification(
            notification_id=notification_id,
            notification_type=notification_type,
            recipient_id=recipient_id,
            sender_id=sender_id,
            title=title,
            message=message,
            action_url=action_url,
            priority=priority,
            scheduled_for=scheduled_for,
            metadata=metadata or {}
        )
        
        # Store notification
        self.notifications[notification_id] = notification
        
        # Update user notifications index
        if recipient_id not in self.user_notifications:
            self.user_notifications[recipient_id] = []
        self.user_notifications[recipient_id].append(notification_id)
        
        # Send immediately if not scheduled
        if not scheduled_for or scheduled_for <= datetime.utcnow():
            await self._deliver_notification(notification)
        
        # Persist to storage
        if self.storage_backend:
            await self.storage_backend.save_notification(notification)
        
        return notification_id
    
    async def broadcast_to_team(
        self,
        team_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        sender_id: str,
        exclude_sender: bool = True,
        priority: str = "normal"
    ) -> List[str]:
        """Broadcast notification to all team members"""
        
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
        
        notification_ids = []
        members = self.teams[team_id]
        
        for member_id in members:
            if exclude_sender and member_id == sender_id:
                continue
            
            notification_id = await self.send_notification(
                recipient_id=member_id,
                notification_type=notification_type,
                title=title,
                message=message,
                sender_id=sender_id,
                priority=priority,
                metadata={'team_id': team_id, 'broadcast': True}
            )
            notification_ids.append(notification_id)
        
        return notification_ids
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[TeamNotification]:
        """Get notifications for user"""
        
        notification_ids = self.user_notifications.get(user_id, [])
        notifications = []
        
        for notification_id in notification_ids[-limit:]:  # Get recent notifications
            notification = self.notifications.get(notification_id)
            if not notification:
                continue
            
            # Filter unread if requested
            if unread_only and notification.read_at:
                continue
            
            notifications.append(notification)
        
        # Sort by creation time (newest first)
        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications
    
    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """Mark notification as read"""
        
        notification = self.notifications.get(notification_id)
        if not notification or notification.recipient_id != user_id:
            return False
        
        notification.read_at = datetime.utcnow()
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_notification(notification)
        
        return True
    
    async def schedule_recurring_notification(
        self,
        team_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        sender_id: str,
        interval_hours: int,
        start_time: Optional[datetime] = None
    ) -> str:
        """Schedule recurring notification"""
        
        # This would typically integrate with a job scheduler
        # For now, we'll store the schedule configuration
        
        schedule_id = str(uuid.uuid4())
        schedule_config = {
            'schedule_id': schedule_id,
            'team_id': team_id,
            'notification_type': notification_type.value,
            'title': title,
            'message': message,
            'sender_id': sender_id,
            'interval_hours': interval_hours,
            'start_time': (start_time or datetime.utcnow()).isoformat(),
            'active': True
        }
        
        if self.storage_backend:
            await self.storage_backend.save_notification_schedule(schedule_config)
        
        logger.info(f"Scheduled recurring notification {schedule_id}")
        return schedule_id
    
    async def mention_user(
        self,
        mentioned_user_id: str,
        mentioning_user_id: str,
        context: str,
        context_url: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> str:
        """Send mention notification to user"""
        
        return await self.send_notification(
            recipient_id=mentioned_user_id,
            notification_type=NotificationType.MENTION,
            title="You were mentioned",
            message=f"You were mentioned by {mentioning_user_id}: {context}",
            sender_id=mentioning_user_id,
            action_url=context_url,
            metadata={
                'workspace_id': workspace_id,
                'context': context
            }
        )
    
    async def escalate_issue(
        self,
        issue_description: str,
        escalated_by: str,
        escalated_to: List[str],
        priority: str = "high",
        context_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Escalate issue to team leads or managers"""
        
        notification_ids = []
        
        for recipient_id in escalated_to:
            notification_id = await self.send_notification(
                recipient_id=recipient_id,
                notification_type=NotificationType.ESCALATION,
                title="Issue Escalated",
                message=f"Issue escalated by {escalated_by}: {issue_description}",
                sender_id=escalated_by,
                action_url=context_url,
                priority=priority,
                metadata=metadata or {}
            )
            notification_ids.append(notification_id)
        
        return notification_ids
    
    async def register_event_handler(
        self,
        event_type: str,
        handler: Callable
    ):
        """Register event handler for team coordination"""
        
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
    
    async def emit_event(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Emit event to registered handlers"""
        
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Event handler failed for {event_type}: {e}")
    
    async def _deliver_notification(self, notification: TeamNotification):
        """Deliver notification through configured channels"""
        
        notification.sent_at = datetime.utcnow()
        
        # Use external notification service if available
        if self.notification_service:
            try:
                await self.notification_service.send_notification(
                    recipient_id=notification.recipient_id,
                    title=notification.title,
                    message=notification.message,
                    priority=notification.priority,
                    action_url=notification.action_url
                )
            except Exception as e:
                logger.error(f"Failed to deliver notification {notification.notification_id}: {e}")
        
        # Emit event for other handlers
        await self.emit_event('notification_sent', {
            'notification_id': notification.notification_id,
            'recipient_id': notification.recipient_id,
            'type': notification.notification_type.value
        })
    
    def get_team_stats(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """Get team coordination statistics"""
        
        if team_id:
            teams_to_analyze = {team_id: self.teams[team_id]} if team_id in self.teams else {}
        else:
            teams_to_analyze = self.teams
        
        total_teams = len(teams_to_analyze)
        total_members = sum(len(members) for members in teams_to_analyze.values())
        
        # Notification statistics
        total_notifications = len(self.notifications)
        unread_notifications = sum(
            1 for n in self.notifications.values() 
            if not n.read_at
        )
        
        # Notification types breakdown
        notification_types = {}
        for notification in self.notifications.values():
            ntype = notification.notification_type.value
            notification_types[ntype] = notification_types.get(ntype, 0) + 1
        
        return {
            'total_teams': total_teams,
            'total_members': total_members,
            'average_team_size': total_members / total_teams if total_teams > 0 else 0,
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'notifications_by_type': notification_types
        }

class WorkflowManager:
    """Manages team workflows and task coordination"""
    
    def __init__(self, team_coordinator: TeamCoordinator, storage_backend=None):
        """Initialize workflow manager"""
        self.team_coordinator = team_coordinator
        self.storage_backend = storage_backend
        self.workflows: Dict[str, TeamWorkflow] = {}
        self.active_workflows: Set[str] = set()
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        created_by: str,
        workspace_id: Optional[str] = None,
        team_members: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
        auto_start: bool = False
    ) -> TeamWorkflow:
        """Create a new team workflow"""
        
        workflow_id = str(uuid.uuid4())
        
        workflow = TeamWorkflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=datetime.utcnow(),
            workspace_id=workspace_id,
            team_members=set(team_members or []),
            deadline=deadline,
            auto_start=auto_start
        )
        
        self.workflows[workflow_id] = workflow
        
        # Persist to storage
        if self.storage_backend:
            await self.storage_backend.save_workflow(workflow)
        
        logger.info(f"Created workflow {workflow_id}: {name}")
        return workflow
    
    async def add_task(
        self,
        workflow_id: str,
        task_name: str,
        task_description: str,
        assigned_to: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        due_date: Optional[datetime] = None,
        estimated_hours: Optional[float] = None
    ) -> str:
        """Add task to workflow"""
        
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        task_id = str(uuid.uuid4())
        
        task = WorkflowTask(
            task_id=task_id,
            name=task_name,
            description=task_description,
            assigned_to=assigned_to,
            depends_on=depends_on or [],
            due_date=due_date,
            estimated_hours=estimated_hours
        )
        
        workflow.tasks[task_id] = task
        
        # Send assignment notification
        if assigned_to:
            await self.team_coordinator.send_notification(
                recipient_id=assigned_to,
                notification_type=NotificationType.TASK_ASSIGNED,
                title="Task Assigned",
                message=f"You have been assigned task: {task_name}",
                sender_id=workflow.created_by,
                metadata={'workflow_id': workflow_id, 'task_id': task_id}
            )
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_workflow(workflow)
        
        return task_id
    
    async def start_workflow(self, workflow_id: str, started_by: str) -> bool:
        """Start workflow execution"""
        
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Workflow {workflow_id} is not in pending status")
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.utcnow()
        
        self.active_workflows.add(workflow_id)
        
        # Notify team members individually
        for member_id in workflow.team_members:
            await self.team_coordinator.send_notification(
                recipient_id=member_id,
                notification_type=NotificationType.WORKFLOW_STARTED,
                title="Workflow Started",
                message=f"Workflow '{workflow.name}' has been started",
                sender_id=started_by
            )
        
        # Start eligible tasks
        await self._start_eligible_tasks(workflow)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_workflow(workflow)
        
        return True
    
    async def complete_task(
        self,
        workflow_id: str,
        task_id: str,
        completed_by: str,
        result: Optional[Any] = None
    ) -> bool:
        """Mark task as completed"""
        
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        task = workflow.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.progress_percentage = 100.0
        task.result = result
        
        # Calculate actual hours if task was started
        if task.started_at:
            task.actual_hours = (task.completed_at - task.started_at).total_seconds() / 3600
        
        # Notify task completion
        await self.team_coordinator.send_notification(
            recipient_id=task.assigned_to or workflow.created_by,
            notification_type=NotificationType.TASK_COMPLETED,
            title="Task Completed",
            message=f"Task '{task.name}' has been completed",
            sender_id=completed_by,
            metadata={'workflow_id': workflow_id, 'task_id': task_id}
        )
        
        # Start dependent tasks
        await self._start_eligible_tasks(workflow)
        
        # Check if workflow is complete
        if self._is_workflow_complete(workflow):
            await self._complete_workflow(workflow)
        
        # Persist changes
        if self.storage_backend:
            await self.storage_backend.save_workflow(workflow)
        
        return True
    
    async def _start_eligible_tasks(self, workflow: TeamWorkflow):
        """Start tasks that have all dependencies completed"""
        
        for task in workflow.tasks.values():
            if task.status != TaskStatus.NOT_STARTED:
                continue
            
            # Check if all dependencies are completed
            dependencies_met = all(
                workflow.tasks.get(dep_id, {}).status == TaskStatus.COMPLETED
                for dep_id in task.depends_on
            )
            
            if dependencies_met:
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = datetime.utcnow()
                
                # Notify assigned user
                if task.assigned_to:
                    await self.team_coordinator.send_notification(
                        recipient_id=task.assigned_to,
                        notification_type=NotificationType.TASK_ASSIGNED,
                        title="Task Ready",
                        message=f"Task '{task.name}' is ready to start",
                        metadata={'workflow_id': workflow.workflow_id, 'task_id': task.task_id}
                    )
    
    def _is_workflow_complete(self, workflow: TeamWorkflow) -> bool:
        """Check if all tasks in workflow are completed"""
        
        return all(
            task.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
            for task in workflow.tasks.values()
        )
    
    async def _complete_workflow(self, workflow: TeamWorkflow):
        """Complete workflow and notify team"""
        
        workflow.status = WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.utcnow()
        
        self.active_workflows.discard(workflow.workflow_id)
        
        # Notify team members individually
        for member_id in workflow.team_members:
            await self.team_coordinator.send_notification(
                recipient_id=member_id,
                notification_type=NotificationType.WORKFLOW_COMPLETED,
                title="Workflow Completed",
                message=f"Workflow '{workflow.name}' has been completed",
                sender_id=workflow.created_by
            )
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        
        total_workflows = len(self.workflows)
        active_workflows = len(self.active_workflows)
        
        # Count by status
        status_counts = {}
        for workflow in self.workflows.values():
            status = workflow.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Task statistics
        total_tasks = sum(len(w.tasks) for w in self.workflows.values())
        completed_tasks = sum(
            1 for w in self.workflows.values() 
            for t in w.tasks.values() 
            if t.status == TaskStatus.COMPLETED
        )
        
        return {
            'total_workflows': total_workflows,
            'active_workflows': active_workflows,
            'workflows_by_status': status_counts,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'task_completion_rate': completed_tasks / total_tasks if total_tasks > 0 else 0
        }