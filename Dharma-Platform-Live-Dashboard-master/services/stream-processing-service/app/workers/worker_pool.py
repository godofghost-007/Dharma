"""
Worker pool for parallel stream processing with load balancing and auto-scaling
"""
import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import structlog

logger = structlog.get_logger()


@dataclass
class WorkerMetrics:
    """Metrics for individual worker"""
    worker_id: str
    tasks_processed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    last_activity: Optional[datetime] = None
    current_load: int = 0
    max_concurrent_tasks: int = 10
    
    @property
    def average_processing_time(self) -> float:
        """Calculate average processing time per task"""
        if self.tasks_processed == 0:
            return 0.0
        return self.total_processing_time / self.tasks_processed
    
    @property
    def success_rate(self) -> float:
        """Calculate task success rate"""
        total_tasks = self.tasks_processed + self.tasks_failed
        if total_tasks == 0:
            return 1.0
        return self.tasks_processed / total_tasks
    
    @property
    def is_overloaded(self) -> bool:
        """Check if worker is overloaded"""
        return self.current_load >= self.max_concurrent_tasks


@dataclass
class WorkerPoolConfig:
    """Configuration for worker pool"""
    min_workers: int = 2
    max_workers: int = 10
    target_queue_size: int = 100
    scale_up_threshold: float = 0.8  # Scale up when 80% capacity
    scale_down_threshold: float = 0.3  # Scale down when 30% capacity
    worker_timeout: int = 300  # 5 minutes
    health_check_interval: int = 30  # 30 seconds
    auto_scaling_enabled: bool = True


class StreamWorker:
    """Individual stream processing worker"""
    
    def __init__(self, worker_id: str, handler: Callable, config: WorkerPoolConfig):
        self.worker_id = worker_id
        self.handler = handler
        self.config = config
        self.metrics = WorkerMetrics(worker_id=worker_id)
        self.running = False
        self.task_queue = asyncio.Queue(maxsize=config.target_queue_size)
        self.current_tasks = set()
        
    async def start(self):
        """Start worker processing loop"""
        self.running = True
        logger.info("Starting stream worker", worker_id=self.worker_id)
        
        try:
            while self.running:
                try:
                    # Get task from queue with timeout
                    task_data = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=self.config.worker_timeout
                    )
                    
                    # Process task
                    await self._process_task(task_data)
                    
                except asyncio.TimeoutError:
                    # No tasks received within timeout, continue
                    continue
                except Exception as e:
                    logger.error("Error in worker processing loop", 
                               worker_id=self.worker_id, 
                               error=str(e))
                    await asyncio.sleep(1)  # Brief pause before retrying
                    
        except Exception as e:
            logger.error("Critical error in worker", 
                        worker_id=self.worker_id, 
                        error=str(e))
        finally:
            self.running = False
            logger.info("Stream worker stopped", worker_id=self.worker_id)
    
    async def _process_task(self, task_data: Dict[str, Any]):
        """Process individual task"""
        task_id = f"{self.worker_id}_{int(time.time() * 1000)}"
        start_time = time.time()
        
        try:
            # Track current task
            self.current_tasks.add(task_id)
            self.metrics.current_load = len(self.current_tasks)
            
            # Execute handler
            result = await self.handler(task_data)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics.tasks_processed += 1
            self.metrics.total_processing_time += processing_time
            self.metrics.last_activity = datetime.utcnow()
            
            logger.debug("Task processed successfully",
                        worker_id=self.worker_id,
                        task_id=task_id,
                        processing_time=processing_time)
            
            return result
            
        except Exception as e:
            # Update failure metrics
            self.metrics.tasks_failed += 1
            self.metrics.last_activity = datetime.utcnow()
            
            logger.error("Task processing failed",
                        worker_id=self.worker_id,
                        task_id=task_id,
                        error=str(e))
            
            # Re-raise for dead letter queue handling
            raise
            
        finally:
            # Remove from current tasks
            self.current_tasks.discard(task_id)
            self.metrics.current_load = len(self.current_tasks)
            
            # Mark task as done in queue
            self.task_queue.task_done()
    
    async def add_task(self, task_data: Dict[str, Any]) -> bool:
        """Add task to worker queue"""
        try:
            # Check if worker is overloaded
            if self.metrics.is_overloaded:
                return False
            
            # Add task to queue (non-blocking)
            self.task_queue.put_nowait(task_data)
            return True
            
        except asyncio.QueueFull:
            logger.warning("Worker queue full", worker_id=self.worker_id)
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get worker health status"""
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "queue_size": self.task_queue.qsize(),
            "current_load": self.metrics.current_load,
            "max_concurrent_tasks": self.metrics.max_concurrent_tasks,
            "tasks_processed": self.metrics.tasks_processed,
            "tasks_failed": self.metrics.tasks_failed,
            "success_rate": self.metrics.success_rate,
            "average_processing_time": self.metrics.average_processing_time,
            "last_activity": self.metrics.last_activity.isoformat() if self.metrics.last_activity else None,
            "is_overloaded": self.metrics.is_overloaded
        }
    
    async def stop(self):
        """Stop worker gracefully"""
        self.running = False
        
        # Wait for current tasks to complete
        if self.current_tasks:
            logger.info("Waiting for current tasks to complete", 
                       worker_id=self.worker_id,
                       pending_tasks=len(self.current_tasks))
            
            # Wait up to 30 seconds for tasks to complete
            for _ in range(30):
                if not self.current_tasks:
                    break
                await asyncio.sleep(1)
        
        logger.info("Worker stopped", worker_id=self.worker_id)


class WorkerPool:
    """Pool of stream processing workers with auto-scaling and load balancing"""
    
    def __init__(self, handler: Callable, config: WorkerPoolConfig):
        self.handler = handler
        self.config = config
        self.workers: Dict[str, StreamWorker] = {}
        self.worker_tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self.load_balancer = LoadBalancer()
        self.auto_scaler = AutoScaler(config)
        self.health_monitor = HealthMonitor(config)
        
    async def start(self):
        """Start worker pool"""
        self.running = True
        logger.info("Starting worker pool", 
                   min_workers=self.config.min_workers,
                   max_workers=self.config.max_workers)
        
        # Start initial workers
        for i in range(self.config.min_workers):
            await self._add_worker(f"worker_{i}")
        
        # Start background tasks
        if self.config.auto_scaling_enabled:
            asyncio.create_task(self.auto_scaler.run(self))
        
        asyncio.create_task(self.health_monitor.run(self))
        
        logger.info("Worker pool started", active_workers=len(self.workers))
    
    async def _add_worker(self, worker_id: str) -> bool:
        """Add new worker to pool"""
        if worker_id in self.workers:
            return False
        
        try:
            worker = StreamWorker(worker_id, self.handler, self.config)
            self.workers[worker_id] = worker
            
            # Start worker task
            task = asyncio.create_task(worker.start())
            self.worker_tasks[worker_id] = task
            
            logger.info("Added worker to pool", worker_id=worker_id)
            return True
            
        except Exception as e:
            logger.error("Failed to add worker", worker_id=worker_id, error=str(e))
            return False
    
    async def _remove_worker(self, worker_id: str) -> bool:
        """Remove worker from pool"""
        if worker_id not in self.workers:
            return False
        
        try:
            worker = self.workers[worker_id]
            task = self.worker_tasks[worker_id]
            
            # Stop worker gracefully
            await worker.stop()
            
            # Cancel worker task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Remove from pool
            del self.workers[worker_id]
            del self.worker_tasks[worker_id]
            
            logger.info("Removed worker from pool", worker_id=worker_id)
            return True
            
        except Exception as e:
            logger.error("Failed to remove worker", worker_id=worker_id, error=str(e))
            return False
    
    async def submit_task(self, task_data: Dict[str, Any]) -> bool:
        """Submit task to worker pool with load balancing"""
        if not self.running or not self.workers:
            logger.error("Worker pool not running or no workers available")
            return False
        
        # Select best worker using load balancer
        worker_id = self.load_balancer.select_worker(self.workers)
        
        if not worker_id:
            logger.warning("No available workers for task")
            return False
        
        worker = self.workers[worker_id]
        success = await worker.add_task(task_data)
        
        if not success:
            logger.warning("Failed to add task to worker", worker_id=worker_id)
        
        return success
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pool metrics"""
        total_tasks_processed = sum(w.metrics.tasks_processed for w in self.workers.values())
        total_tasks_failed = sum(w.metrics.tasks_failed for w in self.workers.values())
        total_queue_size = sum(w.task_queue.qsize() for w in self.workers.values())
        total_current_load = sum(w.metrics.current_load for w in self.workers.values())
        
        return {
            "pool_status": "running" if self.running else "stopped",
            "active_workers": len(self.workers),
            "total_tasks_processed": total_tasks_processed,
            "total_tasks_failed": total_tasks_failed,
            "total_queue_size": total_queue_size,
            "total_current_load": total_current_load,
            "average_success_rate": sum(w.metrics.success_rate for w in self.workers.values()) / len(self.workers) if self.workers else 0,
            "workers": [w.get_health_status() for w in self.workers.values()]
        }
    
    async def stop(self):
        """Stop worker pool gracefully"""
        self.running = False
        logger.info("Stopping worker pool")
        
        # Stop all workers
        stop_tasks = []
        for worker in self.workers.values():
            stop_tasks.append(asyncio.create_task(worker.stop()))
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Cancel all worker tasks
        for task in self.worker_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks.values(), return_exceptions=True)
        
        self.workers.clear()
        self.worker_tasks.clear()
        
        logger.info("Worker pool stopped")


class LoadBalancer:
    """Load balancer for distributing tasks across workers"""
    
    def __init__(self):
        self.round_robin_index = 0
    
    def select_worker(self, workers: Dict[str, StreamWorker]) -> Optional[str]:
        """Select best worker for task using load balancing strategy"""
        if not workers:
            return None
        
        # Filter available workers (not overloaded)
        available_workers = {
            worker_id: worker for worker_id, worker in workers.items()
            if not worker.metrics.is_overloaded and worker.running
        }
        
        if not available_workers:
            # All workers overloaded, select least loaded
            return min(workers.keys(), key=lambda w_id: workers[w_id].metrics.current_load)
        
        # Use round-robin among available workers
        worker_ids = list(available_workers.keys())
        selected_id = worker_ids[self.round_robin_index % len(worker_ids)]
        self.round_robin_index += 1
        
        return selected_id


class AutoScaler:
    """Auto-scaler for dynamic worker pool sizing"""
    
    def __init__(self, config: WorkerPoolConfig):
        self.config = config
        self.last_scale_time = datetime.utcnow()
        self.scale_cooldown = timedelta(minutes=2)  # Prevent rapid scaling
    
    async def run(self, worker_pool: WorkerPool):
        """Run auto-scaling loop"""
        while worker_pool.running:
            try:
                await self._evaluate_scaling(worker_pool)
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error("Error in auto-scaler", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _evaluate_scaling(self, worker_pool: WorkerPool):
        """Evaluate if scaling is needed"""
        if not self._can_scale():
            return
        
        metrics = worker_pool.get_pool_metrics()
        current_workers = metrics["active_workers"]
        total_queue_size = metrics["total_queue_size"]
        total_current_load = metrics["total_current_load"]
        
        # Calculate utilization
        max_capacity = current_workers * 10  # Assuming 10 concurrent tasks per worker
        utilization = total_current_load / max_capacity if max_capacity > 0 else 0
        
        # Scale up if utilization is high
        if (utilization > self.config.scale_up_threshold and 
            current_workers < self.config.max_workers):
            
            new_worker_id = f"worker_{current_workers}"
            success = await worker_pool._add_worker(new_worker_id)
            
            if success:
                self.last_scale_time = datetime.utcnow()
                logger.info("Scaled up worker pool", 
                           new_workers=current_workers + 1,
                           utilization=utilization)
        
        # Scale down if utilization is low
        elif (utilization < self.config.scale_down_threshold and 
              current_workers > self.config.min_workers):
            
            # Find least active worker to remove
            least_active_worker = min(
                worker_pool.workers.keys(),
                key=lambda w_id: worker_pool.workers[w_id].metrics.current_load
            )
            
            success = await worker_pool._remove_worker(least_active_worker)
            
            if success:
                self.last_scale_time = datetime.utcnow()
                logger.info("Scaled down worker pool", 
                           new_workers=current_workers - 1,
                           utilization=utilization)
    
    def _can_scale(self) -> bool:
        """Check if scaling is allowed (cooldown period)"""
        return datetime.utcnow() - self.last_scale_time > self.scale_cooldown


class HealthMonitor:
    """Health monitor for worker pool"""
    
    def __init__(self, config: WorkerPoolConfig):
        self.config = config
    
    async def run(self, worker_pool: WorkerPool):
        """Run health monitoring loop"""
        while worker_pool.running:
            try:
                await self._check_worker_health(worker_pool)
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error("Error in health monitor", error=str(e))
                await asyncio.sleep(60)
    
    async def _check_worker_health(self, worker_pool: WorkerPool):
        """Check health of all workers"""
        unhealthy_workers = []
        
        for worker_id, worker in worker_pool.workers.items():
            if not self._is_worker_healthy(worker):
                unhealthy_workers.append(worker_id)
        
        # Restart unhealthy workers
        for worker_id in unhealthy_workers:
            logger.warning("Restarting unhealthy worker", worker_id=worker_id)
            
            # Remove and re-add worker
            await worker_pool._remove_worker(worker_id)
            await worker_pool._add_worker(worker_id)
    
    def _is_worker_healthy(self, worker: StreamWorker) -> bool:
        """Check if worker is healthy"""
        # Worker is unhealthy if:
        # 1. Not running
        # 2. No activity for too long
        # 3. Success rate too low
        
        if not worker.running:
            return False
        
        if worker.metrics.last_activity:
            time_since_activity = datetime.utcnow() - worker.metrics.last_activity
            if time_since_activity > timedelta(minutes=10):  # No activity for 10 minutes
                return False
        
        if worker.metrics.success_rate < 0.5:  # Success rate below 50%
            return False
        
        return True