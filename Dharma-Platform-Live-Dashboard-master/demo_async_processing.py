#!/usr/bin/env python3
"""
Demo script for async processing and concurrency system.
This script demonstrates the advanced async processing capabilities including:
- Async manager for converting sync operations to async
- Task queue with background processing
- Worker pools with auto-scaling
- Load balancing and service management
- Connection pooling and resource management
"""

import asyncio
import time
import random
from datetime import datetime
from typing import List, Dict, Any

from shared.async_processing.async_manager import AsyncManager, AsyncConfig
from shared.async_processing.task_queue import BackgroundTaskManager, TaskConfig
from shared.async_processing.worker_pool import DynamicWorkerPool
from shared.async_processing.load_balancer import (
    LoadBalancer, LoadBalancingStrategy, ServiceEndpoint, AutoScaler
)
from shared.async_processing.connection_pool import ConnectionPoolManager, PoolConfig


async def demo_async_manager():
    """Demonstrate async manager capabilities."""
    print("\n=== Async Manager Demo ===")
    
    config = AsyncConfig(
        max_workers=5,
        thread_pool_size=3,
        process_pool_size=2,
        timeout=10.0,
        retry_attempts=3
    )
    
    async_manager = AsyncManager(config)
    
    # Demo 1: Convert sync function to async
    def cpu_intensive_task(n: int) -> int:
        """Simulate CPU-intensive work."""
        result = 0
        for i in range(n):
            result += i * i
        return result
    
    print("Running CPU-intensive task in process pool...")
    start_time = time.time()
    result = await async_manager.run_in_process(cpu_intensive_task, 100000)
    execution_time = time.time() - start_time
    print(f"  ✓ Result: {result}, Time: {execution_time:.3f}s")
    
    # Demo 2: Run with retry logic
    async def flaky_operation():
        """Simulate unreliable operation."""
        if random.random() < 0.7:  # 70% chance of failure
            raise Exception("Random failure")
        return "Success!"
    
    print("\nRunning flaky operation with retry...")
    try:
        result = await async_manager.run_with_retry(
            flaky_operation,
            max_attempts=5,
            delay=0.5
        )
        print(f"  ✓ Result: {result}")
    except Exception as e:
        print(f"  ✗ Failed after retries: {e}")
    
    # Demo 3: Parallel batch processing
    async def process_item(item: int) -> int:
        """Process a single item."""
        await asyncio.sleep(0.1)  # Simulate work
        return item * 2
    
    print("\nRunning parallel batch processing...")
    items = list(range(20))
    start_time = time.time()
    results = await async_manager.run_parallel_batches(
        items,
        process_item,
        batch_size=5,
        max_concurrent_batches=3
    )
    execution_time = time.time() - start_time
    print(f"  ✓ Processed {len(items)} items in {execution_time:.3f}s")
    print(f"  ✓ Results: {results[:10]}...")  # Show first 10 results
    
    # Demo 4: Background tasks
    async def background_work():
        """Background task."""
        await asyncio.sleep(2)
        return "Background task completed"
    
    print("\nStarting background task...")
    task = async_manager.create_background_task(
        background_work(),
        name="demo_background_task"
    )
    
    print("  ✓ Background task started, continuing with other work...")
    await asyncio.sleep(1)
    print("  ✓ Doing other work while background task runs...")
    
    # Wait for background task
    result = await async_manager.wait_for_task("demo_background_task")
    print(f"  ✓ Background task result: {result}")
    
    # Cleanup
    await async_manager.shutdown()


async def demo_task_queue():
    """Demonstrate task queue and background processing."""
    print("\n=== Task Queue Demo ===")
    
    task_manager = BackgroundTaskManager()
    
    # Register tasks
    @task_manager.task("data_processing", max_retries=2, timeout=5.0)
    async def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data asynchronously."""
        await asyncio.sleep(0.5)  # Simulate processing
        
        # Simulate occasional failures
        if random.random() < 0.2:
            raise Exception("Processing failed")
        
        return {
            "processed_data": data,
            "processed_at": datetime.utcnow().isoformat(),
            "processing_time": 0.5
        }
    
    @task_manager.task("send_notification", queue="notifications")
    def send_notification(message: str, recipient: str) -> str:
        """Send notification (sync function)."""
        time.sleep(0.2)  # Simulate network call
        return f"Notification sent to {recipient}: {message}"
    
    # Create queues and start workers
    data_queue = task_manager.get_queue("default")
    notification_queue = task_manager.create_queue("notifications", max_size=50)
    
    await task_manager.start_all_workers(workers_per_queue=2)
    
    # Submit tasks
    print("Submitting data processing tasks...")
    task_ids = []
    for i in range(10):
        task_id = await task_manager.delay(
            "data_processing",
            {"id": i, "value": f"data_{i}"}
        )
        task_ids.append(task_id)
    
    print("Submitting notification tasks...")
    notification_ids = []
    for i in range(5):
        task_id = await task_manager.delay(
            "send_notification",
            f"Message {i}",
            f"user_{i}@example.com",
            queue="notifications"
        )
        notification_ids.append(task_id)
    
    # Wait for some tasks to complete
    print("Waiting for tasks to complete...")
    await asyncio.sleep(3)
    
    # Check results
    completed_tasks = 0
    failed_tasks = 0
    
    for task_id in task_ids[:5]:  # Check first 5 tasks
        try:
            result = await data_queue.get_result(task_id, timeout=1.0)
            if result.status.value == "success":
                completed_tasks += 1
                print(f"  ✓ Task {task_id[:8]} completed successfully")
            else:
                failed_tasks += 1
                print(f"  ✗ Task {task_id[:8]} failed: {result.error}")
        except asyncio.TimeoutError:
            print(f"  ⏳ Task {task_id[:8]} still running")
    
    # Show queue statistics
    stats = task_manager.get_all_stats()
    print(f"\nQueue Statistics:")
    for queue_name, queue_stats in stats.items():
        print(f"  {queue_name}: {queue_stats['total_tasks']} total, "
              f"{queue_stats['running_tasks']} running, "
              f"{queue_stats['queue_size']} queued")
    
    # Cleanup
    await task_manager.stop_all_workers()


async def demo_worker_pool():
    """Demonstrate dynamic worker pool."""
    print("\n=== Dynamic Worker Pool Demo ===")
    
    # Task processor function
    async def process_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task with variable processing time."""
        processing_time = task_data.get("processing_time", 0.5)
        await asyncio.sleep(processing_time)
        
        # Simulate occasional failures
        if random.random() < 0.1:
            raise Exception("Task processing failed")
        
        return {
            "task_id": task_data["id"],
            "result": f"Processed task {task_data['id']}",
            "processing_time": processing_time
        }
    
    # Create dynamic worker pool
    worker_pool = DynamicWorkerPool(
        task_processor=process_task,
        min_workers=2,
        max_workers=8,
        queue_size=50,
        scale_up_threshold=0.8,
        scale_down_threshold=0.2,
        adjustment_interval=5.0  # Faster scaling for demo
    )
    
    await worker_pool.start()
    
    # Submit initial batch of tasks
    print("Submitting initial batch of tasks...")
    initial_tasks = [
        {"id": i, "processing_time": random.uniform(0.1, 1.0)}
        for i in range(10)
    ]
    
    submitted = await worker_pool.submit_tasks(initial_tasks)
    print(f"  ✓ Submitted {submitted} tasks")
    
    # Monitor pool stats
    for i in range(6):  # Monitor for 30 seconds
        await asyncio.sleep(5)
        
        stats = await worker_pool.get_stats()
        print(f"\nPool Stats (t={i*5}s):")
        print(f"  Workers: {stats.total_workers} total, "
              f"{stats.busy_workers} busy, {stats.idle_workers} idle")
        print(f"  Tasks: {stats.total_tasks_completed} completed, "
              f"{stats.total_tasks_failed} failed")
        print(f"  Queue: {stats.queue_size} pending")
        print(f"  Utilization: {stats.avg_pool_utilization:.1%}")
        
        # Add more tasks to trigger scaling
        if i == 2:
            print("  Adding high-load batch...")
            high_load_tasks = [
                {"id": f"hl_{j}", "processing_time": 2.0}
                for j in range(15)
            ]
            await worker_pool.submit_tasks(high_load_tasks)
    
    # Wait for completion
    print("\nWaiting for all tasks to complete...")
    await worker_pool.wait_for_completion(timeout=30)
    
    # Final stats
    final_stats = await worker_pool.get_stats()
    print(f"\nFinal Stats:")
    print(f"  Total tasks completed: {final_stats.total_tasks_completed}")
    print(f"  Total tasks failed: {final_stats.total_tasks_failed}")
    print(f"  Success rate: {(final_stats.total_tasks_completed / (final_stats.total_tasks_completed + final_stats.total_tasks_failed)):.1%}")
    
    # Cleanup
    await worker_pool.shutdown(timeout=10)


async def demo_load_balancer():
    """Demonstrate load balancing."""
    print("\n=== Load Balancer Demo ===")
    
    # Create load balancer
    load_balancer = LoadBalancer(
        strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
        health_check_interval=5.0
    )
    
    # Add service endpoints
    endpoints = [
        ServiceEndpoint("service-1", "localhost", 8001, weight=1),
        ServiceEndpoint("service-2", "localhost", 8002, weight=2),
        ServiceEndpoint("service-3", "localhost", 8003, weight=1),
    ]
    
    for endpoint in endpoints:
        load_balancer.add_endpoint(endpoint)
    
    # Start health checks
    await load_balancer.start_health_checks()
    
    # Simulate requests
    print("Simulating load-balanced requests...")
    
    async def simulate_request(endpoint: ServiceEndpoint) -> str:
        """Simulate a request to an endpoint."""
        # Simulate variable response times
        response_time = random.uniform(0.1, 0.5)
        await asyncio.sleep(response_time)
        
        # Simulate occasional failures
        if random.random() < 0.05:
            raise Exception("Service unavailable")
        
        return f"Response from {endpoint.id}"
    
    # Execute requests
    successful_requests = 0
    failed_requests = 0
    
    for i in range(20):
        endpoint = load_balancer.get_next_endpoint()
        if not endpoint:
            print(f"  ✗ Request {i}: No healthy endpoints")
            failed_requests += 1
            continue
        
        start_time = time.time()
        await load_balancer.record_request_start(endpoint.id)
        
        try:
            result = await simulate_request(endpoint)
            response_time = (time.time() - start_time) * 1000
            await load_balancer.record_request_end(endpoint.id, response_time, True)
            
            print(f"  ✓ Request {i}: {result} ({response_time:.1f}ms)")
            successful_requests += 1
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            await load_balancer.record_request_end(endpoint.id, response_time, False)
            
            print(f"  ✗ Request {i}: Failed - {e} ({response_time:.1f}ms)")
            failed_requests += 1
        
        await asyncio.sleep(0.1)  # Brief pause between requests
    
    # Show load balancer stats
    stats = load_balancer.get_stats()
    print(f"\nLoad Balancer Stats:")
    print(f"  Strategy: {stats['strategy']}")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Average response time: {stats['avg_response_time']:.1f}ms")
    print(f"  Healthy endpoints: {stats['healthy_endpoints']}/{stats['total_endpoints']}")
    
    print(f"\nEndpoint Details:")
    for endpoint_id, metrics in stats['endpoint_metrics'].items():
        print(f"  {endpoint_id}: {metrics['health_status']}, "
              f"{metrics['total_requests']} requests, "
              f"{metrics['success_rate']:.1%} success rate, "
              f"{metrics['avg_response_time']:.1f}ms avg")
    
    # Cleanup
    await load_balancer.stop_health_checks()


async def demo_connection_pool():
    """Demonstrate connection pooling."""
    print("\n=== Connection Pool Demo ===")
    
    # Mock connection factory
    async def create_mock_connection():
        """Create a mock database connection."""
        await asyncio.sleep(0.1)  # Simulate connection time
        
        class MockConnection:
            def __init__(self):
                self.id = random.randint(1000, 9999)
                self.queries_executed = 0
            
            async def execute(self, query: str):
                await asyncio.sleep(0.05)  # Simulate query time
                self.queries_executed += 1
                return f"Query result from connection {self.id}"
            
            async def close(self):
                await asyncio.sleep(0.01)
        
        return MockConnection()
    
    # Create connection pool
    pool_config = PoolConfig(
        min_size=3,
        max_size=10,
        max_idle_time=30.0,
        connection_timeout=5.0,
        health_check_interval=10.0
    )
    
    pool = ConnectionPoolManager(create_mock_connection, pool_config)
    await pool.initialize()
    
    # Execute queries using the pool
    print("Executing queries using connection pool...")
    
    async def execute_query(query: str) -> str:
        """Execute a query using the connection pool."""
        async with pool.acquire() as conn:
            return await conn.execute(query)
    
    # Simulate concurrent queries
    tasks = []
    for i in range(15):
        task = asyncio.create_task(
            execute_query(f"SELECT * FROM table_{i}")
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_queries = sum(1 for r in results if not isinstance(r, Exception))
    print(f"  ✓ Executed {successful_queries}/{len(tasks)} queries successfully")
    
    # Show pool statistics
    stats = pool.get_stats()
    print(f"\nConnection Pool Stats:")
    print(f"  Total connections: {stats.total_connections}")
    print(f"  Active connections: {stats.active_connections}")
    print(f"  Idle connections: {stats.idle_connections}")
    print(f"  Failed connections: {stats.failed_connections}")
    print(f"  Total requests: {stats.total_requests}")
    print(f"  Success rate: {(stats.successful_requests / stats.total_requests):.1%}")
    print(f"  Average response time: {stats.avg_response_time:.3f}s")
    print(f"  Pool utilization: {stats.pool_utilization:.1%}")
    
    # Cleanup
    await pool.shutdown()


async def main():
    """Main demo function."""
    print("🚀 Async Processing and Concurrency Demo")
    print("=" * 60)
    
    try:
        # Run all demos
        await demo_async_manager()
        await demo_task_queue()
        await demo_worker_pool()
        await demo_load_balancer()
        await demo_connection_pool()
        
        print("\n" + "=" * 60)
        print("✅ All async processing demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())