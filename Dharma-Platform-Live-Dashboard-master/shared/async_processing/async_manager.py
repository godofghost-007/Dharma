"""Async processing manager for converting sync operations to async."""

import asyncio
import functools
import concurrent.futures
from typing import Any, Callable, Optional, Dict, List, Union
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AsyncConfig:
    """Configuration for async operations."""
    max_workers: int = 10
    thread_pool_size: int = 5
    process_pool_size: int = 2
    timeout: Optional[float] = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0


class AsyncManager:
    """Manages async operations and converts sync functions to async."""
    
    def __init__(self, config: Optional[AsyncConfig] = None):
        self.config = config or AsyncConfig()
        self.thread_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.thread_pool_size
        )
        self.process_executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=self.config.process_pool_size
        )
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_results: Dict[str, Any] = {}
    
    async def run_in_thread(
        self, 
        func: Callable, 
        *args, 
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """Run a synchronous function in a thread pool."""
        timeout = timeout or self.config.timeout
        
        try:
            loop = asyncio.get_event_loop()
            partial_func = functools.partial(func, *args, **kwargs)
            
            result = await asyncio.wait_for(
                loop.run_in_executor(self.thread_executor, partial_func),
                timeout=timeout
            )
            
            logger.debug("Thread execution completed", 
                        function=func.__name__, 
                        args_count=len(args))
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Thread execution timed out", 
                        function=func.__name__, 
                        timeout=timeout)
            raise
        except Exception as e:
            logger.error("Thread execution failed", 
                        function=func.__name__, 
                        error=str(e))
            raise
    
    async def run_in_process(
        self, 
        func: Callable, 
        *args, 
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """Run a CPU-intensive function in a process pool."""
        timeout = timeout or self.config.timeout
        
        try:
            loop = asyncio.get_event_loop()
            partial_func = functools.partial(func, *args, **kwargs)
            
            result = await asyncio.wait_for(
                loop.run_in_executor(self.process_executor, partial_func),
                timeout=timeout
            )
            
            logger.debug("Process execution completed", 
                        function=func.__name__, 
                        args_count=len(args))
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Process execution timed out", 
                        function=func.__name__, 
                        timeout=timeout)
            raise
        except Exception as e:
            logger.error("Process execution failed", 
                        function=func.__name__, 
                        error=str(e))
            raise
    
    async def run_with_retry(
        self, 
        coro_func: Callable,
        *args,
        max_attempts: Optional[int] = None,
        delay: Optional[float] = None,
        backoff_factor: float = 2.0,
        **kwargs
    ) -> Any:
        """Run an async function with retry logic."""
        max_attempts = max_attempts or self.config.retry_attempts
        delay = delay or self.config.retry_delay
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                result = await coro_func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info("Retry succeeded", 
                               function=coro_func.__name__, 
                               attempt=attempt + 1)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < max_attempts - 1:
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning("Retry attempt failed, retrying", 
                                 function=coro_func.__name__,
                                 attempt=attempt + 1,
                                 max_attempts=max_attempts,
                                 wait_time=wait_time,
                                 error=str(e))
                    
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("All retry attempts failed", 
                               function=coro_func.__name__,
                               max_attempts=max_attempts,
                               error=str(e))
        
        raise last_exception
    
    async def gather_with_concurrency_limit(
        self,
        *coroutines,
        limit: int = 10,
        return_exceptions: bool = False
    ) -> List[Any]:
        """Run multiple coroutines with concurrency limit."""
        semaphore = asyncio.Semaphore(limit)
        
        async def limited_coro(coro):
            async with semaphore:
                return await coro
        
        limited_coroutines = [limited_coro(coro) for coro in coroutines]
        
        return await asyncio.gather(
            *limited_coroutines, 
            return_exceptions=return_exceptions
        )
    
    async def run_parallel_batches(
        self,
        items: List[Any],
        async_func: Callable,
        batch_size: int = 10,
        max_concurrent_batches: int = 3
    ) -> List[Any]:
        """Process items in parallel batches."""
        results = []
        
        # Split items into batches
        batches = [
            items[i:i + batch_size] 
            for i in range(0, len(items), batch_size)
        ]
        
        # Process batches with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        async def process_batch(batch):
            async with semaphore:
                batch_results = []
                for item in batch:
                    try:
                        result = await async_func(item)
                        batch_results.append(result)
                    except Exception as e:
                        logger.error("Batch item processing failed", 
                                   item=str(item)[:100], 
                                   error=str(e))
                        batch_results.append(None)
                return batch_results
        
        batch_tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Flatten results
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error("Batch processing failed", error=str(batch_result))
                continue
            results.extend(batch_result)
        
        logger.info("Parallel batch processing completed", 
                   total_items=len(items),
                   batch_count=len(batches),
                   results_count=len(results))
        
        return results
    
    def create_background_task(
        self, 
        coro, 
        name: Optional[str] = None,
        callback: Optional[Callable] = None
    ) -> asyncio.Task:
        """Create a background task with optional callback."""
        task_name = name or f"task_{len(self._running_tasks)}"
        
        async def task_wrapper():
            try:
                result = await coro
                self._task_results[task_name] = result
                
                if callback:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(result)
                        else:
                            callback(result)
                    except Exception as e:
                        logger.error("Task callback failed", 
                                   task_name=task_name, 
                                   error=str(e))
                
                logger.debug("Background task completed", task_name=task_name)
                return result
                
            except Exception as e:
                logger.error("Background task failed", 
                           task_name=task_name, 
                           error=str(e))
                raise
            finally:
                # Clean up task reference
                if task_name in self._running_tasks:
                    del self._running_tasks[task_name]
        
        task = asyncio.create_task(task_wrapper(), name=task_name)
        self._running_tasks[task_name] = task
        
        return task
    
    async def wait_for_task(self, task_name: str, timeout: Optional[float] = None) -> Any:
        """Wait for a specific background task to complete."""
        if task_name not in self._running_tasks:
            # Check if task already completed
            if task_name in self._task_results:
                return self._task_results[task_name]
            raise ValueError(f"Task '{task_name}' not found")
        
        task = self._running_tasks[task_name]
        
        try:
            if timeout:
                result = await asyncio.wait_for(task, timeout=timeout)
            else:
                result = await task
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Task wait timed out", task_name=task_name, timeout=timeout)
            raise
    
    async def cancel_task(self, task_name: str) -> bool:
        """Cancel a background task."""
        if task_name not in self._running_tasks:
            return False
        
        task = self._running_tasks[task_name]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        del self._running_tasks[task_name]
        logger.info("Task cancelled", task_name=task_name)
        
        return True
    
    async def cancel_all_tasks(self):
        """Cancel all running background tasks."""
        tasks_to_cancel = list(self._running_tasks.values())
        
        for task in tasks_to_cancel:
            task.cancel()
        
        # Wait for all tasks to be cancelled
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        
        self._running_tasks.clear()
        logger.info("All background tasks cancelled", count=len(tasks_to_cancel))
    
    def get_running_tasks(self) -> Dict[str, asyncio.Task]:
        """Get currently running tasks."""
        return self._running_tasks.copy()
    
    def get_task_results(self) -> Dict[str, Any]:
        """Get completed task results."""
        return self._task_results.copy()
    
    async def shutdown(self):
        """Shutdown the async manager and clean up resources."""
        # Cancel all running tasks
        await self.cancel_all_tasks()
        
        # Shutdown executors
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        
        logger.info("AsyncManager shutdown completed")
    
    def to_async(self, func: Callable, use_process: bool = False) -> Callable:
        """Decorator to convert sync function to async."""
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if use_process:
                return await self.run_in_process(func, *args, **kwargs)
            else:
                return await self.run_in_thread(func, *args, **kwargs)
        
        return async_wrapper
    
    def batch_processor(
        self, 
        batch_size: int = 10,
        max_concurrent_batches: int = 3
    ) -> Callable:
        """Decorator for batch processing functions."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def batch_wrapper(items: List[Any]) -> List[Any]:
                return await self.run_parallel_batches(
                    items, 
                    func, 
                    batch_size=batch_size,
                    max_concurrent_batches=max_concurrent_batches
                )
            
            return batch_wrapper
        
        return decorator