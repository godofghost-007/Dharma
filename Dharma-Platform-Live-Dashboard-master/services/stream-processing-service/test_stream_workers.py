"""
Test stream processing workers and monitoring
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.workers.worker_pool import (
    WorkerMetrics, WorkerPoolConfig, StreamWorker, WorkerPool, 
    LoadBalancer, AutoScaler, HealthMonitor
)
from app.workers.dead_letter_queue import (
    DeadLetterQueueHandler, FailedMessage, RetryConfig, RetryStrategy
)
from app.monitoring.pipeline_monitor import (
    PipelineMonitor, HealthStatus, HealthCheck, PipelineMetrics
)


class TestWorkerMetrics:
    """Test worker metrics functionality"""
    
    def test_worker_metrics_initialization(self):
        """Test worker metrics initialization"""
        metrics = WorkerMetrics(worker_id="test_worker")
        
        assert metrics.worker_id == "test_worker"
        assert metrics.tasks_processed == 0
        assert metrics.tasks_failed == 0
        assert metrics.total_processing_time == 0.0
        assert metrics.current_load == 0
        assert metrics.max_concurrent_tasks == 10
    
    def test_average_processing_time_calculation(self):
        """Test average processing time calculation"""
        metrics = WorkerMetrics(worker_id="test_worker")
        
        # No tasks processed
        assert metrics.average_processing_time == 0.0
        
        # With tasks processed
        metrics.tasks_processed = 10
        metrics.total_processing_time = 50.0
        assert metrics.average_processing_time == 5.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = WorkerMetrics(worker_id="test_worker")
        
        # No tasks
        assert metrics.success_rate == 1.0
        
        # With tasks
        metrics.tasks_processed = 8
        metrics.tasks_failed = 2
        assert metrics.success_rate == 0.8
    
    def test_overload_detection(self):
        """Test worker overload detection"""
        metrics = WorkerMetrics(worker_id="test_worker")
        
        # Not overloaded
        metrics.current_load = 5
        assert not metrics.is_overloaded
        
        # Overloaded
        metrics.current_load = 10
        assert metrics.is_overloaded


class TestStreamWorker:
    """Test individual stream worker"""
    
    @pytest.fixture
    def mock_handler(self):
        """Mock processing handler"""
        async def handler(data):
            await asyncio.sleep(0.01)  # Simulate processing
            return {"processed": True, "data": data}
        return handler
    
    @pytest.fixture
    def worker_config(self):
        """Worker pool configuration"""
        return WorkerPoolConfig(
            min_workers=1,
            max_workers=5,
            target_queue_size=10,
            worker_timeout=5
        )
    
    def test_stream_worker_initialization(self, mock_handler, worker_config):
        """Test stream worker initialization"""
        worker = StreamWorker("test_worker", mock_handler, worker_config)
        
        assert worker.worker_id == "test_worker"
        assert worker.handler == mock_handler
        assert worker.config == worker_config
        assert not worker.running
        assert worker.task_queue.maxsize == worker_config.target_queue_size
    
    @pytest.mark.asyncio
    async def test_worker_task_processing(self, mock_handler, worker_config):
        """Test worker task processing"""
        worker = StreamWorker("test_worker", mock_handler, worker_config)
        
        # Add a task
        test_data = {"test": "data"}
        success = await worker.add_task(test_data)
        assert success
        
        # Process the task manually (simulate processing loop)
        task_data = await worker.task_queue.get()
        await worker._process_task(task_data)
        
        # Check metrics
        assert worker.metrics.tasks_processed == 1
        assert worker.metrics.tasks_failed == 0
        assert worker.metrics.total_processing_time > 0
    
    @pytest.mark.asyncio
    async def test_worker_queue_full_handling(self, mock_handler, worker_config):
        """Test worker behavior when queue is full"""
        # Create worker with small queue
        config = WorkerPoolConfig(target_queue_size=2)
        worker = StreamWorker("test_worker", mock_handler, config)
        
        # Fill the queue
        assert await worker.add_task({"task": 1})
        assert await worker.add_task({"task": 2})
        
        # Queue should be full now
        assert not await worker.add_task({"task": 3})
    
    def test_worker_health_status(self, mock_handler, worker_config):
        """Test worker health status reporting"""
        worker = StreamWorker("test_worker", mock_handler, worker_config)
        
        health = worker.get_health_status()
        
        assert health["worker_id"] == "test_worker"
        assert health["running"] == False
        assert health["queue_size"] == 0
        assert health["current_load"] == 0
        assert health["tasks_processed"] == 0
        assert health["success_rate"] == 1.0


class TestWorkerPool:
    """Test worker pool functionality"""
    
    @pytest.fixture
    def mock_handler(self):
        """Mock processing handler"""
        async def handler(data):
            await asyncio.sleep(0.01)
            return {"processed": True}
        return handler
    
    @pytest.fixture
    def pool_config(self):
        """Worker pool configuration"""
        return WorkerPoolConfig(
            min_workers=2,
            max_workers=5,
            auto_scaling_enabled=False  # Disable for testing
        )
    
    @pytest.mark.asyncio
    async def test_worker_pool_initialization(self, mock_handler, pool_config):
        """Test worker pool initialization"""
        pool = WorkerPool(mock_handler, pool_config)
        
        assert pool.handler == mock_handler
        assert pool.config == pool_config
        assert not pool.running
        assert len(pool.workers) == 0
    
    @pytest.mark.asyncio
    async def test_worker_pool_start_stop(self, mock_handler, pool_config):
        """Test worker pool start and stop"""
        pool = WorkerPool(mock_handler, pool_config)
        
        # Start pool
        await pool.start()
        
        assert pool.running
        assert len(pool.workers) == pool_config.min_workers
        
        # Stop pool
        await pool.stop()
        
        assert not pool.running
        assert len(pool.workers) == 0
    
    @pytest.mark.asyncio
    async def test_task_submission(self, mock_handler, pool_config):
        """Test task submission to worker pool"""
        pool = WorkerPool(mock_handler, pool_config)
        await pool.start()
        
        try:
            # Submit task
            success = await pool.submit_task({"test": "data"})
            assert success
            
            # Wait a bit for processing
            await asyncio.sleep(0.1)
            
            # Check metrics
            metrics = pool.get_pool_metrics()
            assert metrics["active_workers"] == pool_config.min_workers
            
        finally:
            await pool.stop()


class TestLoadBalancer:
    """Test load balancer functionality"""
    
    def test_load_balancer_worker_selection(self):
        """Test worker selection logic"""
        balancer = LoadBalancer()
        
        # Create mock workers
        workers = {}
        for i in range(3):
            worker = Mock()
            worker.metrics = Mock()
            worker.metrics.is_overloaded = False
            worker.metrics.current_load = i
            worker.running = True
            workers[f"worker_{i}"] = worker
        
        # Select worker (should use round-robin)
        selected = balancer.select_worker(workers)
        assert selected in workers
        
        # Select again (should be different due to round-robin)
        selected2 = balancer.select_worker(workers)
        assert selected2 in workers
    
    def test_load_balancer_overloaded_workers(self):
        """Test load balancer with overloaded workers"""
        balancer = LoadBalancer()
        
        # Create workers where some are overloaded
        workers = {}
        for i in range(3):
            worker = Mock()
            worker.metrics = Mock()
            worker.metrics.is_overloaded = (i < 2)  # First two are overloaded
            worker.metrics.current_load = i * 5
            worker.running = True
            workers[f"worker_{i}"] = worker
        
        # Should select the non-overloaded worker
        selected = balancer.select_worker(workers)
        assert selected == "worker_2"


class TestDeadLetterQueue:
    """Test dead letter queue functionality"""
    
    @pytest.fixture
    def mock_kafka_config(self):
        """Mock Kafka configuration"""
        config = Mock()
        config.topic_prefix = "test"
        config.bootstrap_servers = "localhost:9092"
        return config
    
    @pytest.fixture
    def retry_config(self):
        """Retry configuration"""
        return RetryConfig(
            max_retries=3,
            initial_delay=60,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
    
    def test_failed_message_creation(self):
        """Test failed message creation"""
        message = FailedMessage(
            message_id="test_123",
            original_topic="test.topic",
            original_partition=0,
            original_offset=100,
            original_data={"test": "data"},
            error_message="Processing failed",
            failure_timestamp=datetime.utcnow()
        )
        
        assert message.message_id == "test_123"
        assert message.original_topic == "test.topic"
        assert message.retry_count == 0
        assert message.next_retry_time is None
    
    def test_failed_message_serialization(self):
        """Test failed message serialization"""
        timestamp = datetime.utcnow()
        message = FailedMessage(
            message_id="test_123",
            original_topic="test.topic",
            original_partition=0,
            original_offset=100,
            original_data={"test": "data"},
            error_message="Processing failed",
            failure_timestamp=timestamp
        )
        
        # Convert to dict and back
        data = message.to_dict()
        restored = FailedMessage.from_dict(data)
        
        assert restored.message_id == message.message_id
        assert restored.original_topic == message.original_topic
        assert restored.failure_timestamp == message.failure_timestamp
    
    @patch('app.workers.dead_letter_queue.EnhancedKafkaProducer')
    def test_dlq_handler_initialization(self, mock_producer, mock_kafka_config, retry_config):
        """Test DLQ handler initialization"""
        handler = DeadLetterQueueHandler(mock_kafka_config, retry_config)
        
        assert handler.kafka_config == mock_kafka_config
        assert handler.retry_config == retry_config
        assert handler.dlq_topic == "test.errors.dlq"
        assert handler.retry_topic == "test.errors.retry"
        assert not handler.running
    
    def test_retry_delay_calculation(self, mock_kafka_config, retry_config):
        """Test retry delay calculation"""
        with patch('app.workers.dead_letter_queue.EnhancedKafkaProducer'):
            handler = DeadLetterQueueHandler(mock_kafka_config, retry_config)
            
            # Test exponential backoff
            assert handler._calculate_retry_delay(0) == 60  # Initial delay
            assert handler._calculate_retry_delay(1) == 120  # 60 * 2
            assert handler._calculate_retry_delay(2) == 240  # 60 * 4
            
            # Test max delay cap
            retry_config.max_delay = 100
            assert handler._calculate_retry_delay(10) == 100  # Capped at max


class TestPipelineMonitor:
    """Test pipeline monitoring"""
    
    def test_pipeline_monitor_initialization(self):
        """Test pipeline monitor initialization"""
        monitor = PipelineMonitor(check_interval=10)
        
        assert monitor.check_interval == 10
        assert not monitor.running
        assert len(monitor.health_checks) == 0
        assert monitor.metrics.messages_processed == 0
    
    def test_health_check_creation(self):
        """Test health check creation"""
        check = HealthCheck(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good",
            timestamp=datetime.utcnow(),
            response_time_ms=100.0
        )
        
        assert check.name == "test_check"
        assert check.status == HealthStatus.HEALTHY
        assert check.message == "All good"
        assert check.response_time_ms == 100.0
    
    @pytest.mark.asyncio
    async def test_health_status_aggregation(self):
        """Test health status aggregation"""
        monitor = PipelineMonitor()
        
        # Add some health checks
        monitor.health_checks["service1"] = HealthCheck(
            name="service1",
            status=HealthStatus.HEALTHY,
            message="OK",
            timestamp=datetime.utcnow()
        )
        
        monitor.health_checks["service2"] = HealthCheck(
            name="service2",
            status=HealthStatus.WARNING,
            message="Slow",
            timestamp=datetime.utcnow()
        )
        
        status = monitor.get_health_status()
        
        # Overall status should be WARNING (worst of HEALTHY and WARNING)
        assert status["overall_status"] == HealthStatus.WARNING.value
        assert len(status["checks"]) == 2
    
    def test_metrics_collection(self):
        """Test metrics collection"""
        monitor = PipelineMonitor()
        
        # Update metrics
        monitor.metrics.messages_processed = 1000
        monitor.metrics.messages_failed = 50
        monitor.metrics.last_updated = datetime.utcnow()
        
        metrics = monitor.get_metrics()
        
        assert metrics["messages_processed"] == 1000
        assert metrics["messages_failed"] == 50
        assert metrics["last_updated"] is not None
    
    def test_alert_threshold_updates(self):
        """Test alert threshold updates"""
        monitor = PipelineMonitor()
        
        original_threshold = monitor.alert_thresholds["error_rate_warning"]
        
        # Update thresholds
        new_thresholds = {"error_rate_warning": 0.10}
        monitor.update_thresholds(new_thresholds)
        
        assert monitor.alert_thresholds["error_rate_warning"] == 0.10
        assert monitor.alert_thresholds["error_rate_warning"] != original_threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])