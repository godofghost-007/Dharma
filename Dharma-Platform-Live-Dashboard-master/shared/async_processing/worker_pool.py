"""Worker pool for parallel async processing."""

import asyncio
import time
from typing import Any, Callable, List, Optional, Dict, Union
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class WorkerStatus(Enum):
    """Worker status enumeration."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerStats:
    """Worker statistics."""
    worker_id: str
    status: WorkerStatus
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    last_task_time: Optional[float] = None
    created_at: float = 0.0
    error_count: int = 0


@dataclass
class PoolStats:
    """Worker pool statistics."""
    total_workers: int = 0
    idle_workers: int = 0
    busy_workers: int = 0
    stopped_workers: int = 0
    error_workers: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    avg_pool_utilization: float = 0.0
    queue_size: int = 0


class Worker:
    """Individual worker for processing tasks."""
    
    def __init__(self, worker_id: str, task_processor: Callable):
        self.worker_id = worker_id
        self.task_processor = task_processor
        self.status = WorkerStatus.IDLE
        self.stats = WorkerStats(worker_id=worker_id, status=WorkerStatus.IDLE)
        self.stats.created_at = time.time()
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
    
    async def start(self, task_queue: asyncio.Queue):
        """Start the worker to process tasks from the queue."""
        self.status = WorkerStatus.IDLE
        self.stats.status = WorkerStatus.IDLE
        
        logger.debug("Worker started", worker_id=self.worker_id)
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Wait for task with timeout to allow periodic stop checks
                    task_data = await asyncio.wait_for(
                        task_queue.get(),
                        timeout=1.0
                    )
                    
                    await self._process_task(task_data)
                    
                except asyncio.TimeoutError:
                    # No task available, continue loop
                    continue
                except Exception as e:
                    self.stats.error_count += 1
                    self.status = WorkerStatus.ERROR
                    self.stats.status = WorkerStatus.ERROR
                    logger.error("Worker error", 
                               worker_id=self.worker_id, 
                               error=str(e))
                    
                    # Brief pause before continuing
                    await asyncio.sleep(1.0)
                    
                    # Reset to idle if not stopping
                    if not self._stop_event.is_set():
                        self.status = WorkerStatus.IDLE
                        self.stats.status = WorkerStatus.IDLE
        
        except asyncio.CancelledError:
            logger.debug("Worker cancelled", worker_id=self.worker_id)
        
        finally:
            self.status = WorkerStatus.STOPPED
            self.stats.status = WorkerStatus.STOPPED
            logger.debug("Worker stopped", worker_id=self.worker_id)
    
    async def _process_task(self, task_data: Any):
        """Process a single task."""
        self.status = WorkerStatus.BUSY
        self.stats.status = WorkerStatus.BUSY
        
        start_time = time.time()
        
        try:
            # Process the task
            if asyncio.iscoroutinefunction(self.task_processor):
                await self.task_processor(task_data)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.task_processor, task_data)
            
            # Update success stats
            processing_time = time.time() - start_time
            self.stats.tasks_completed += 1
            self.stats.total_processing_time += processing_time
            self.stats.avg_processing_time = (
                self.stats.total_processing_time / self.stats.tasks_completed
            )
            self.stats.last_task_time = processing_time
            
            logger.debug("Task completed", 
                        worker_id=self.worker_id,
                        processing_time=processing_time)
        
        except Exception as e:
            # Update failure stats
            processing_time = time.time() - start_time
            self.stats.tasks_failed += 1
            self.stats.error_count += 1
            
            logger.error("Task processing failed", 
                        worker_id=self.worker_id,
                        processing_time=processing_time,
                        error=str(e))
        
        finally:
            self.status = WorkerStatus.IDLE
            self.stats.status = WorkerStatus.IDLE
    
    async def stop(self):
        """Stop the worker gracefully."""
        self.status = WorkerStatus.STOPPING
        self.stats.status = WorkerStatus.STOPPING
        self._stop_event.set()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    def get_stats(self) -> WorkerStats:
        """Get worker statistics."""
        return self.stats


class WorkerPool:
    """Pool of workers for parallel async processing."""
    
    def __init__(
        self, 
        task_processor: Callable,
        pool_size: int = 5,
        queue_size: int = 100
    ):
        self.task_processor = task_processor
        self.pool_size = pool_size
        self.queue_size = queue_size
        
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self.workers: List[Worker] = []
        self.worker_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._stats_lock = asyncio.Lock()
    
    async def start(self):
        """Start all workers in the pool."""
        # Create workers
        for i in range(self.pool_size):
            worker_id = f"worker-{i}"
            worker = Worker(worker_id, self.task_processor)
            self.workers.append(worker)
            
            # Start worker task
            worker_task = asyncio.create_task(
                worker.start(self.task_queue),
                name=f"worker-task-{i}"
            )
            worker._task = worker_task
            self.worker_tasks.append(worker_task)
        
        logger.info("Worker pool started", 
                   pool_size=self.pool_size,
                   queue_size=self.queue_size)
    
    async def submit_task(self, task_data: Any, timeout: Optional[float] = None) -> bool:
        """Submit a task to the worker pool."""
        try:
            if timeout:
                await asyncio.wait_for(
                    self.task_queue.put(task_data),
                    timeout=timeout
                )
            else:
                await self.task_queue.put(task_data)
            
            logger.debug("Task submitted", queue_size=self.task_queue.qsize())
            return True
            
        except asyncio.TimeoutError:
            logger.warning("Task submission timeout")
            return False
        except asyncio.QueueFull:
            logger.warning("Task queue full")
            return False
    
    async def submit_tasks(
        self, 
        tasks: List[Any], 
        timeout: Optional[float] = None
    ) -> int:
        """Submit multiple tasks to the worker pool."""
        submitted_count = 0
        
        for task_data in tasks:
            if await self.submit_task(task_data, timeout):
                submitted_count += 1
            else:
                break
        
        logger.info("Batch tasks submitted", 
                   submitted=submitted_count,
                   total=len(tasks))
        
        return submitted_count
    
    async def wait_for_completion(self, timeout: Optional[float] = None):
        """Wait for all queued tasks to complete."""
        start_time = time.time()
        
        while not self.task_queue.empty():
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError("Wait for completion timeout")
            
            await asyncio.sleep(0.1)
        
        # Wait a bit more to ensure workers finish current tasks
        await asyncio.sleep(0.5)
        
        logger.info("All tasks completed")
    
    async def resize_pool(self, new_size: int):
        """Resize the worker pool."""
        if new_size <= 0:
            raise ValueError("Pool size must be positive")
        
        current_size = len(self.workers)
        
        if new_size > current_size:
            # Add new workers
            for i in range(current_size, new_size):
                worker_id = f"worker-{i}"
                worker = Worker(worker_id, self.task_processor)
                self.workers.append(worker)
                
                worker_task = asyncio.create_task(
                    worker.start(self.task_queue),
                    name=f"worker-task-{i}"
                )
                worker._task = worker_task
                self.worker_tasks.append(worker_task)
            
            logger.info("Worker pool expanded", 
                       old_size=current_size, 
                       new_size=new_size)
        
        elif new_size < current_size:
            # Remove excess workers
            workers_to_stop = self.workers[new_size:]
            tasks_to_cancel = self.worker_tasks[new_size:]
            
            # Stop workers gracefully
            for worker in workers_to_stop:
                await worker.stop()
            
            # Wait for tasks to complete
            if tasks_to_cancel:
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
            
            # Update lists
            self.workers = self.workers[:new_size]
            self.worker_tasks = self.worker_tasks[:new_size]
            
            logger.info("Worker pool reduced", 
                       old_size=current_size, 
                       new_size=new_size)
        
        self.pool_size = new_size
    
    async def get_stats(self) -> PoolStats:
        """Get worker pool statistics."""
        async with self._stats_lock:
            stats = PoolStats()
            stats.total_workers = len(self.workers)
            stats.queue_size = self.task_queue.qsize()
            
            # Aggregate worker stats
            for worker in self.workers:
                worker_stats = worker.get_stats()
                
                if worker_stats.status == WorkerStatus.IDLE:
                    stats.idle_workers += 1
                elif worker_stats.status == WorkerStatus.BUSY:
                    stats.busy_workers += 1
                elif worker_stats.status == WorkerStatus.STOPPED:
                    stats.stopped_workers += 1
                elif worker_stats.status == WorkerStatus.ERROR:
                    stats.error_workers += 1
                
                stats.total_tasks_completed += worker_stats.tasks_completed
                stats.total_tasks_failed += worker_stats.tasks_failed
            
            # Calculate utilization
            if stats.total_workers > 0:
                stats.avg_pool_utilization = stats.busy_workers / stats.total_workers
            
            return stats
    
    async def get_worker_stats(self) -> List[WorkerStats]:
        """Get individual worker statistics."""
        return [worker.get_stats() for worker in self.workers]
    
    async def shutdown(self, timeout: Optional[float] = None):
        """Shutdown the worker pool gracefully."""
        logger.info("Shutting down worker pool")
        
        # Stop accepting new tasks
        self._shutdown_event.set()
        
        # Wait for current tasks to complete (with timeout)
        try:
            if timeout:
                await asyncio.wait_for(
                    self.wait_for_completion(),
                    timeout=timeout
                )
            else:
                await self.wait_for_completion()
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout, forcing worker termination")
        
        # Stop all workers
        for worker in self.workers:
            await worker.stop()
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.workers.clear()
        self.worker_tasks.clear()
        
        logger.info("Worker pool shutdown completed")
    
    def is_running(self) -> bool:
        """Check if the worker pool is running."""
        return not self._shutdown_event.is_set() and len(self.workers) > 0


class DynamicWorkerPool(WorkerPool):
    """Worker pool that automatically adjusts size based on load."""
    
    def __init__(
        self,
        task_processor: Callable,
        min_workers: int = 2,
        max_workers: int = 10,
        queue_size: int = 100,
        scale_up_threshold: float = 0.8,
        scale_down_threshold: float = 0.2,
        adjustment_interval: float = 30.0
    ):
        super().__init__(task_processor, min_workers, queue_size)
        
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.adjustment_interval = adjustment_interval
        
        self._last_adjustment = time.time()
        self._auto_scale_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the dynamic worker pool."""
        await super().start()
        
        # Start auto-scaling task
        self._auto_scale_task = asyncio.create_task(
            self._auto_scale_loop(),
            name="auto-scale-task"
        )
        
        logger.info("Dynamic worker pool started", 
                   min_workers=self.min_workers,
                   max_workers=self.max_workers)
    
    async def _auto_scale_loop(self):
        """Auto-scaling loop that adjusts pool size based on load."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.adjustment_interval)
                await self._adjust_pool_size()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Auto-scaling error", error=str(e))
    
    async def _adjust_pool_size(self):
        """Adjust pool size based on current load."""
        now = time.time()
        
        if now - self._last_adjustment < self.adjustment_interval:
            return
        
        stats = await self.get_stats()
        
        # Calculate load metrics
        queue_load = self.task_queue.qsize() / self.queue_size
        worker_utilization = stats.avg_pool_utilization
        
        current_size = stats.total_workers
        new_size = current_size
        
        # Scale up if high load
        if (queue_load > self.scale_up_threshold or 
            worker_utilization > self.scale_up_threshold):
            
            if current_size < self.max_workers:
                new_size = min(self.max_workers, current_size + 1)
                logger.info("Scaling up worker pool", 
                           queue_load=queue_load,
                           worker_utilization=worker_utilization,
                           old_size=current_size,
                           new_size=new_size)
        
        # Scale down if low load
        elif (queue_load < self.scale_down_threshold and 
              worker_utilization < self.scale_down_threshold):
            
            if current_size > self.min_workers:
                new_size = max(self.min_workers, current_size - 1)
                logger.info("Scaling down worker pool", 
                           queue_load=queue_load,
                           worker_utilization=worker_utilization,
                           old_size=current_size,
                           new_size=new_size)
        
        # Apply size change
        if new_size != current_size:
            await self.resize_pool(new_size)
            self._last_adjustment = now
    
    async def shutdown(self, timeout: Optional[float] = None):
        """Shutdown the dynamic worker pool."""
        # Stop auto-scaling
        if self._auto_scale_task:
            self._auto_scale_task.cancel()
            try:
                await self._auto_scale_task
            except asyncio.CancelledError:
                pass
        
        await super().shutdown(timeout)