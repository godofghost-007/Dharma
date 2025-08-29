"""Test async processing and concurrency implementation."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from shared.async_processing.async_manager import AsyncManager, AsyncConfig
from shared.async_processing.task_queue import TaskQueue, BackgroundTaskManager, TaskStatus
from shared.async_processing.concurrency_limiter import (
    ConcurrencyLimiter, 
    TokenBucketRateLimiter, 
    RateLimitConfig
)
from shared.async_processing.worker_pool import WorkerPool, WorkerStatus


class TestAsyncManager:
    """Test async manager functionality."""
    
    def test_async_manager_initialization(self):
        """Test async manager initialization."""
        config = AsyncConfig(max_workers=5, timeout=60.0)
        manager = AsyncManager(config)
        
        assert manager.config.max_workers == 5
        assert manager.config.timeout == 60.0
        assert manager.thread_executor is not None
        assert manager.process_executor is not None
    
    @pytest.mark.asyncio
    async def test_run_in_thread(self):
        """Test running sync function in thread."""
        manager = AsyncManager()
        
        def sync_function(x, y):
            return x + y
        
        result = await manager.run_in_thread(sync_function, 5, 10)
        assert result == 15
    
    @pytest.mark.asyncio
    async def test_run_with_retry(self):
        """Test retry functionality."""
        manager = AsyncManager()
        
        call_count = 0
        
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await manager.run_with_retry(
            failing_function,
            max_attempts=3,
            delay=0.1
        )
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_gather_with_concurrency_limit(self):
        """Test concurrent execution with limits."""
        manager = AsyncManager()
        
        async def test_coro(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        coroutines = [test_coro(i) for i in range(5)]
        results = await manager.gather_with_concurrency_limit(
            *coroutines,
            limit=2
        )
        
        assert results == [0, 2, 4, 6, 8]
    
    @pytest.mark.asyncio
    async def test_run_parallel_batches(self):
        """Test parallel batch processing."""
        manager = AsyncManager()
        
        async def process_item(item):
            return item * 2
        
        items = list(range(10))
        results = await manager.run_parallel_batches(
            items,
            process_item,
            batch_size=3,
            max_concurrent_batches=2
        )
        
        assert len(results) == 10
        assert results == [i * 2 for i in range(10)]
    
    @pytest.mark.asyncio
    async def test_background_task_management(self):
        """Test background task creation and management."""
        manager = AsyncManager()
        
        async def background_work():
            await asyncio.sleep(0.1)
            return "completed"
        
        task = manager.create_background_task(background_work(), name="test_task")
        
        assert "test_task" in manager.get_running_tasks()
        
        result = await manager.wait_for_task("test_task")
        assert result == "completed"
        
        assert "test_task" not in manager.get_running_tasks()
        assert "test_task" in manager.get_task_results()
    
    def test_to_async_decorator(self):
        """Test sync to async conversion decorator."""
        manager = AsyncManager()
        
        def sync_function(x):
            return x * 2
        
        async_function = manager.to_async(sync_function)
        
        # Test that it returns a coroutine function
        assert asyncio.iscoroutinefunction(async_function)
    
    def test_batch_processor_decorator(self):
        """Test batch processor decorator."""
        manager = AsyncManager()
        
        @manager.batch_processor(batch_size=2, max_concurrent_batches=1)
        async def process_item(item):
            return item * 2
        
        # Test that decorator returns a function
        assert callable(process_item)


class TestTaskQueue:
    """Test task queue functionality."""
    
    def test_task_queue_initialization(self):
        """Test task queue initialization."""
        queue = TaskQueue("test_queue", max_size=50)
        
        assert queue.name == "test_queue"
        assert queue.max_size == 50
        assert len(queue._registered_tasks) == 0
    
    def test_task_registration(self):
        """Test task registration."""
        queue = TaskQueue()
        
        def test_task(x, y):
            return x + y
        
        queue.register_task("add_task", test_task)
        
        assert "add_task" in queue._registered_tasks
        assert queue._registered_tasks["add_task"] == test_task
    
    def test_task_decorator(self):
        """Test task decorator."""
        queue = TaskQueue()
        
        @queue.task("multiply_task")
        def multiply(x, y):
            return x * y
        
        assert "multiply_task" in queue._registered_tasks
        assert queue._registered_tasks["multiply_task"] == multiply
    
    @pytest.mark.asyncio
    async def test_task_enqueue_and_result(self):
        """Test task enqueueing and result retrieval."""
        queue = TaskQueue()
        
        @queue.task("test_task")
        def simple_task(value):
            return value * 2
        
        # Enqueue task
        task_id = await queue.enqueue("test_task", 5)
        
        assert task_id in queue._results
        assert queue._results[task_id].status == TaskStatus.PENDING
    
    def test_queue_stats(self):
        """Test queue statistics."""
        queue = TaskQueue("test_queue")
        
        @queue.task("dummy_task")
        def dummy():
            pass
        
        stats = queue.get_queue_stats()
        
        assert stats["queue_name"] == "test_queue"
        assert stats["total_tasks"] == 0
        assert stats["running_tasks"] == 0
        assert "dummy_task" in stats["registered_tasks"]


class TestBackgroundTaskManager:
    """Test background task manager."""
    
    def test_task_manager_initialization(self):
        """Test task manager initialization."""
        manager = BackgroundTaskManager()
        
        assert len(manager._queues) == 0
        assert manager._default_queue == "default"
    
    def test_queue_creation(self):
        """Test queue creation."""
        manager = BackgroundTaskManager()
        
        queue = manager.create_queue("test_queue", max_size=100)
        
        assert queue.name == "test_queue"
        assert queue.max_size == 100
        assert "test_queue" in manager._queues
    
    def test_get_default_queue(self):
        """Test getting default queue."""
        manager = BackgroundTaskManager()
        
        # Should auto-create default queue
        queue = manager.get_queue()
        
        assert queue.name == "default"
        assert "default" in manager._queues
    
    def test_task_decorator_with_manager(self):
        """Test task decorator with manager."""
        manager = BackgroundTaskManager()
        
        # Create custom queue first
        manager.create_queue("custom")
        
        @manager.task("test_task", queue="custom")
        def test_function():
            return "test"
        
        # Should use custom queue
        assert "custom" in manager._queues
        
        custom_queue = manager.get_queue("custom")
        assert "test_task" in custom_queue._registered_tasks


class TestConcurrencyLimiter:
    """Test concurrency limiter."""
    
    def test_concurrency_limiter_initialization(self):
        """Test concurrency limiter initialization."""
        limiter = ConcurrencyLimiter(max_concurrent=5)
        
        assert limiter.max_concurrent == 5
        assert limiter._active_count == 0
        assert limiter._total_requests == 0
    
    @pytest.mark.asyncio
    async def test_concurrency_limiting(self):
        """Test concurrency limiting functionality."""
        limiter = ConcurrencyLimiter(max_concurrent=2)
        
        active_count = 0
        max_active = 0
        
        async def test_operation():
            nonlocal active_count, max_active
            
            async with limiter:
                active_count += 1
                max_active = max(max_active, active_count)
                await asyncio.sleep(0.1)
                active_count -= 1
        
        # Start 5 concurrent operations
        tasks = [test_operation() for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Should never exceed max_concurrent
        assert max_active <= 2
        
        stats = limiter.get_stats()
        assert stats["total_requests"] == 5
        assert stats["completed_requests"] == 5
    
    def test_limiter_resize(self):
        """Test limiter resizing."""
        limiter = ConcurrencyLimiter(max_concurrent=5)
        
        limiter.resize(10)
        assert limiter.max_concurrent == 10
        
        with pytest.raises(ValueError):
            limiter.resize(0)


class TestTokenBucketRateLimiter:
    """Test token bucket rate limiter."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        config = RateLimitConfig(requests_per_second=10.0, burst_size=20)
        limiter = TokenBucketRateLimiter(config)
        
        assert limiter.config.requests_per_second == 10.0
        assert limiter.config.burst_size == 20
        assert limiter.tokens == 20.0
    
    @pytest.mark.asyncio
    async def test_token_acquisition(self):
        """Test token acquisition."""
        config = RateLimitConfig(requests_per_second=10.0, burst_size=5)
        limiter = TokenBucketRateLimiter(config)
        
        # Should be able to acquire up to burst_size tokens immediately
        for _ in range(5):
            assert await limiter.acquire() is True
        
        # Next acquisition should fail (no tokens left)
        assert await limiter.acquire() is False
    
    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test token refill over time."""
        config = RateLimitConfig(requests_per_second=100.0, burst_size=1)
        limiter = TokenBucketRateLimiter(config)
        
        # Use up the token
        assert await limiter.acquire() is True
        assert await limiter.acquire() is False
        
        # Wait for refill (at 100 rps, should refill quickly)
        await asyncio.sleep(0.02)  # 20ms should be enough for 1 token at 100 rps
        
        assert await limiter.acquire() is True
    
    def test_rate_limiter_stats(self):
        """Test rate limiter statistics."""
        config = RateLimitConfig(requests_per_second=10.0, burst_size=5)
        limiter = TokenBucketRateLimiter(config)
        
        stats = limiter.get_stats()
        
        assert stats["requests_per_second"] == 10.0
        assert stats["burst_size"] == 5
        assert stats["current_tokens"] == 5.0
        assert stats["requests_count"] == 0
        assert stats["rejected_count"] == 0


class TestWorkerPool:
    """Test worker pool functionality."""
    
    def test_worker_pool_initialization(self):
        """Test worker pool initialization."""
        def dummy_processor(task):
            return task
        
        pool = WorkerPool(dummy_processor, pool_size=3, queue_size=10)
        
        assert pool.pool_size == 3
        assert pool.queue_size == 10
        assert pool.task_processor == dummy_processor
        assert len(pool.workers) == 0
    
    @pytest.mark.asyncio
    async def test_worker_pool_start_stop(self):
        """Test worker pool start and stop."""
        def dummy_processor(task):
            return task
        
        pool = WorkerPool(dummy_processor, pool_size=2)
        
        await pool.start()
        
        assert len(pool.workers) == 2
        assert len(pool.worker_tasks) == 2
        assert pool.is_running() is True
        
        await pool.shutdown(timeout=1.0)
        
        assert pool.is_running() is False
    
    @pytest.mark.asyncio
    async def test_task_submission_and_processing(self):
        """Test task submission and processing."""
        processed_tasks = []
        
        def task_processor(task):
            processed_tasks.append(task * 2)
        
        pool = WorkerPool(task_processor, pool_size=2)
        await pool.start()
        
        # Submit tasks
        tasks = [1, 2, 3, 4, 5]
        submitted = await pool.submit_tasks(tasks)
        
        assert submitted == 5
        
        # Wait for processing
        await pool.wait_for_completion(timeout=2.0)
        
        # Check results
        assert len(processed_tasks) == 5
        assert set(processed_tasks) == {2, 4, 6, 8, 10}
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_pool_resize(self):
        """Test worker pool resizing."""
        def dummy_processor(task):
            pass
        
        pool = WorkerPool(dummy_processor, pool_size=2)
        await pool.start()
        
        assert len(pool.workers) == 2
        
        # Resize up
        await pool.resize_pool(4)
        assert len(pool.workers) == 4
        assert pool.pool_size == 4
        
        # Resize down
        await pool.resize_pool(1)
        assert len(pool.workers) == 1
        assert pool.pool_size == 1
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_pool_stats(self):
        """Test worker pool statistics."""
        def dummy_processor(task):
            time.sleep(0.1)  # Simulate work
        
        pool = WorkerPool(dummy_processor, pool_size=2)
        await pool.start()
        
        stats = await pool.get_stats()
        
        assert stats.total_workers == 2
        assert stats.idle_workers == 2
        assert stats.busy_workers == 0
        assert stats.queue_size == 0
        
        await pool.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])