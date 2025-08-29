"""Task queue and background task management using Celery-like patterns."""

import asyncio
import json
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskConfig:
    """Task configuration."""
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    timeout: Optional[float] = 300.0
    priority: int = 0
    expires: Optional[datetime] = None


class TaskQueue:
    """Async task queue implementation."""
    
    def __init__(self, name: str = "default", max_size: int = 1000):
        self.name = name
        self.max_size = max_size
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._results: Dict[str, TaskResult] = {}
        self._registered_tasks: Dict[str, Callable] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._workers: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
    
    def register_task(self, name: str, func: Callable):
        """Register a task function."""
        self._registered_tasks[name] = func
        logger.debug("Task registered", task_name=name, queue=self.name)
    
    def task(self, name: Optional[str] = None, **task_config):
        """Decorator to register a task function."""
        def decorator(func: Callable) -> Callable:
            task_name = name or func.__name__
            self.register_task(task_name, func)
            
            # Add task configuration as function attribute
            func._task_config = TaskConfig(**task_config)
            
            return func
        
        return decorator
    
    async def enqueue(
        self, 
        task_name: str, 
        *args, 
        task_id: Optional[str] = None,
        config: Optional[TaskConfig] = None,
        **kwargs
    ) -> str:
        """Enqueue a task for execution."""
        if task_name not in self._registered_tasks:
            raise ValueError(f"Task '{task_name}' not registered")
        
        task_id = task_id or str(uuid.uuid4())
        config = config or TaskConfig()
        
        # Check if task has expired
        if config.expires and datetime.utcnow() > config.expires:
            logger.warning("Task expired before enqueue", 
                         task_id=task_id, 
                         task_name=task_name)
            return task_id
        
        task_data = {
            "task_id": task_id,
            "task_name": task_name,
            "args": args,
            "kwargs": kwargs,
            "config": asdict(config),
            "enqueued_at": datetime.utcnow().isoformat()
        }
        
        # Initialize task result
        self._results[task_id] = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            max_retries=config.max_retries
        )
        
        try:
            await self._queue.put(task_data)
            logger.debug("Task enqueued", 
                        task_id=task_id, 
                        task_name=task_name,
                        queue_size=self._queue.qsize())
            
        except asyncio.QueueFull:
            logger.error("Queue full, cannot enqueue task", 
                        task_id=task_id, 
                        task_name=task_name)
            self._results[task_id].status = TaskStatus.FAILURE
            self._results[task_id].error = "Queue full"
            raise
        
        return task_id
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """Get task result, waiting if necessary."""
        if task_id not in self._results:
            raise ValueError(f"Task '{task_id}' not found")
        
        start_time = time.time()
        
        while True:
            result = self._results[task_id]
            
            if result.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED]:
                return result
            
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"Task '{task_id}' result timeout")
            
            await asyncio.sleep(0.1)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        if task_id not in self._results:
            return False
        
        result = self._results[task_id]
        
        if result.status == TaskStatus.PENDING:
            result.status = TaskStatus.CANCELLED
            logger.info("Pending task cancelled", task_id=task_id)
            return True
        
        if result.status == TaskStatus.RUNNING and task_id in self._running_tasks:
            running_task = self._running_tasks[task_id]
            running_task.cancel()
            result.status = TaskStatus.CANCELLED
            logger.info("Running task cancelled", task_id=task_id)
            return True
        
        return False
    
    async def start_workers(self, worker_count: int = 3):
        """Start worker tasks to process the queue."""
        for i in range(worker_count):
            worker = asyncio.create_task(
                self._worker_loop(f"worker-{i}"),
                name=f"{self.name}-worker-{i}"
            )
            self._workers.append(worker)
        
        logger.info("Workers started", 
                   queue=self.name, 
                   worker_count=worker_count)
    
    async def stop_workers(self):
        """Stop all worker tasks."""
        self._shutdown_event.set()
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
        
        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        logger.info("Workers stopped", queue=self.name)
    
    async def _worker_loop(self, worker_name: str):
        """Worker loop to process tasks from the queue."""
        logger.debug("Worker started", worker=worker_name, queue=self.name)
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Get task with timeout to allow periodic shutdown checks
                    task_data = await asyncio.wait_for(
                        self._queue.get(), 
                        timeout=1.0
                    )
                    
                    await self._execute_task(task_data, worker_name)
                    
                except asyncio.TimeoutError:
                    # No task available, continue loop
                    continue
                except Exception as e:
                    logger.error("Worker error", 
                               worker=worker_name, 
                               error=str(e))
                    
        except asyncio.CancelledError:
            logger.debug("Worker cancelled", worker=worker_name)
        
        logger.debug("Worker stopped", worker=worker_name, queue=self.name)
    
    async def _execute_task(self, task_data: Dict[str, Any], worker_name: str):
        """Execute a single task."""
        task_id = task_data["task_id"]
        task_name = task_data["task_name"]
        args = task_data["args"]
        kwargs = task_data["kwargs"]
        config = TaskConfig(**task_data["config"])
        
        result = self._results[task_id]
        result.status = TaskStatus.RUNNING
        result.started_at = datetime.utcnow()
        
        logger.debug("Task execution started", 
                    task_id=task_id, 
                    task_name=task_name,
                    worker=worker_name)
        
        try:
            # Check if task has expired
            if config.expires and datetime.utcnow() > config.expires:
                raise Exception("Task expired")
            
            # Get the task function
            task_func = self._registered_tasks[task_name]
            
            # Create execution task with timeout
            execution_task = asyncio.create_task(
                self._run_task_function(task_func, *args, **kwargs)
            )
            
            self._running_tasks[task_id] = execution_task
            
            try:
                if config.timeout:
                    task_result = await asyncio.wait_for(
                        execution_task, 
                        timeout=config.timeout
                    )
                else:
                    task_result = await execution_task
                
                # Task completed successfully
                result.status = TaskStatus.SUCCESS
                result.result = task_result
                result.completed_at = datetime.utcnow()
                result.execution_time = (
                    result.completed_at - result.started_at
                ).total_seconds()
                
                logger.debug("Task execution completed", 
                           task_id=task_id, 
                           execution_time=result.execution_time)
                
            except asyncio.TimeoutError:
                execution_task.cancel()
                raise Exception(f"Task timeout after {config.timeout} seconds")
            
            finally:
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]
        
        except asyncio.CancelledError:
            result.status = TaskStatus.CANCELLED
            result.completed_at = datetime.utcnow()
            logger.info("Task cancelled during execution", task_id=task_id)
        
        except Exception as e:
            error_msg = str(e)
            result.error = error_msg
            result.completed_at = datetime.utcnow()
            
            # Handle retries
            if result.retry_count < config.max_retries:
                result.retry_count += 1
                result.status = TaskStatus.RETRY
                
                # Calculate retry delay with backoff
                retry_delay = config.retry_delay * (config.retry_backoff ** (result.retry_count - 1))
                
                logger.warning("Task failed, scheduling retry", 
                             task_id=task_id,
                             retry_count=result.retry_count,
                             max_retries=config.max_retries,
                             retry_delay=retry_delay,
                             error=error_msg)
                
                # Re-enqueue task after delay
                asyncio.create_task(self._retry_task(task_data, retry_delay))
            else:
                result.status = TaskStatus.FAILURE
                logger.error("Task failed after max retries", 
                           task_id=task_id,
                           max_retries=config.max_retries,
                           error=error_msg)
    
    async def _run_task_function(self, func: Callable, *args, **kwargs) -> Any:
        """Run task function, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)
    
    async def _retry_task(self, task_data: Dict[str, Any], delay: float):
        """Retry a failed task after delay."""
        await asyncio.sleep(delay)
        
        # Reset task status to pending
        task_id = task_data["task_id"]
        if task_id in self._results:
            self._results[task_id].status = TaskStatus.PENDING
            await self._queue.put(task_data)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        status_counts = {}
        for result in self._results.values():
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "queue_name": self.name,
            "queue_size": self._queue.qsize(),
            "max_size": self.max_size,
            "total_tasks": len(self._results),
            "running_tasks": len(self._running_tasks),
            "worker_count": len(self._workers),
            "status_counts": status_counts,
            "registered_tasks": list(self._registered_tasks.keys())
        }


class BackgroundTaskManager:
    """Manages multiple task queues and provides Celery-like interface."""
    
    def __init__(self):
        self._queues: Dict[str, TaskQueue] = {}
        self._default_queue = "default"
    
    def create_queue(self, name: str, max_size: int = 1000) -> TaskQueue:
        """Create a new task queue."""
        if name in self._queues:
            raise ValueError(f"Queue '{name}' already exists")
        
        queue = TaskQueue(name, max_size)
        self._queues[name] = queue
        
        logger.info("Task queue created", queue_name=name, max_size=max_size)
        return queue
    
    def get_queue(self, name: str = None) -> TaskQueue:
        """Get a task queue by name."""
        queue_name = name or self._default_queue
        
        if queue_name not in self._queues:
            # Auto-create default queue
            if queue_name == self._default_queue:
                return self.create_queue(queue_name)
            else:
                raise ValueError(f"Queue '{queue_name}' not found")
        
        return self._queues[queue_name]
    
    def task(self, name: Optional[str] = None, queue: str = None, **config):
        """Decorator to register a task."""
        target_queue = self.get_queue(queue)
        return target_queue.task(name, **config)
    
    async def delay(
        self, 
        task_name: str, 
        *args, 
        queue: str = None,
        **kwargs
    ) -> str:
        """Execute task asynchronously (Celery-like interface)."""
        target_queue = self.get_queue(queue)
        return await target_queue.enqueue(task_name, *args, **kwargs)
    
    async def apply_async(
        self, 
        task_name: str, 
        args: tuple = (), 
        kwargs: dict = None,
        queue: str = None,
        **options
    ) -> str:
        """Execute task asynchronously with options."""
        target_queue = self.get_queue(queue)
        kwargs = kwargs or {}
        
        config = TaskConfig(**options)
        return await target_queue.enqueue(
            task_name, 
            *args, 
            config=config,
            **kwargs
        )
    
    async def start_all_workers(self, workers_per_queue: int = 3):
        """Start workers for all queues."""
        for queue in self._queues.values():
            await queue.start_workers(workers_per_queue)
        
        logger.info("All workers started", 
                   queue_count=len(self._queues),
                   workers_per_queue=workers_per_queue)
    
    async def stop_all_workers(self):
        """Stop workers for all queues."""
        for queue in self._queues.values():
            await queue.stop_workers()
        
        logger.info("All workers stopped")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all queues."""
        return {
            queue_name: queue.get_queue_stats()
            for queue_name, queue in self._queues.items()
        }