"""
Dead Letter Queue (DLQ) handler for failed message processing
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import structlog

from ..core.kafka_clients import EnhancedKafkaProducer, EnhancedKafkaConsumer
from ..core.kafka_config import KafkaStreamConfig

logger = structlog.get_logger()


class RetryStrategy(Enum):
    """Retry strategies for failed messages"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    NO_RETRY = "no_retry"


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    initial_delay: int = 60  # seconds
    max_delay: int = 3600  # 1 hour
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_multiplier: float = 2.0


@dataclass
class FailedMessage:
    """Represents a failed message in DLQ"""
    message_id: str
    original_topic: str
    original_partition: int
    original_offset: int
    original_data: Dict[str, Any]
    error_message: str
    failure_timestamp: datetime
    retry_count: int = 0
    next_retry_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "message_id": self.message_id,
            "original_topic": self.original_topic,
            "original_partition": self.original_partition,
            "original_offset": self.original_offset,
            "original_data": self.original_data,
            "error_message": self.error_message,
            "failure_timestamp": self.failure_timestamp.isoformat(),
            "retry_count": self.retry_count,
            "next_retry_time": self.next_retry_time.isoformat() if self.next_retry_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailedMessage':
        """Create from dictionary"""
        return cls(
            message_id=data["message_id"],
            original_topic=data["original_topic"],
            original_partition=data["original_partition"],
            original_offset=data["original_offset"],
            original_data=data["original_data"],
            error_message=data["error_message"],
            failure_timestamp=datetime.fromisoformat(data["failure_timestamp"]),
            retry_count=data.get("retry_count", 0),
            next_retry_time=datetime.fromisoformat(data["next_retry_time"]) if data.get("next_retry_time") else None
        )


class DeadLetterQueueHandler:
    """Handler for dead letter queue operations"""
    
    def __init__(self, kafka_config: KafkaStreamConfig, retry_config: RetryConfig):
        self.kafka_config = kafka_config
        self.retry_config = retry_config
        self.producer = EnhancedKafkaProducer(kafka_config)
        self.dlq_topic = f"{kafka_config.topic_prefix}.errors.dlq"
        self.retry_topic = f"{kafka_config.topic_prefix}.errors.retry"
        self.running = False
        
        # Message handlers for different error types
        self.error_handlers: Dict[str, Callable] = {}
        
    async def send_to_dlq(self, original_message: Dict[str, Any], error: str, 
                         original_topic: str, partition: int = 0, offset: int = 0):
        """Send failed message to dead letter queue"""
        try:
            failed_message = FailedMessage(
                message_id=f"{original_topic}_{partition}_{offset}_{int(datetime.utcnow().timestamp())}",
                original_topic=original_topic,
                original_partition=partition,
                original_offset=offset,
                original_data=original_message,
                error_message=error,
                failure_timestamp=datetime.utcnow()
            )
            
            # Send to DLQ
            success = await self.producer.send_message(
                topic=self.dlq_topic,
                message=failed_message.to_dict(),
                key=failed_message.message_id
            )
            
            if success:
                logger.info("Message sent to DLQ",
                           message_id=failed_message.message_id,
                           original_topic=original_topic,
                           error=error)
            else:
                logger.error("Failed to send message to DLQ",
                            message_id=failed_message.message_id,
                            original_topic=original_topic)
            
            return success
            
        except Exception as e:
            logger.error("Error sending to DLQ", error=str(e))
            return False
    
    async def send_to_retry_queue(self, failed_message: FailedMessage):
        """Send message to retry queue with calculated delay"""
        try:
            # Calculate next retry time
            delay = self._calculate_retry_delay(failed_message.retry_count)
            failed_message.next_retry_time = datetime.utcnow() + timedelta(seconds=delay)
            failed_message.retry_count += 1
            
            # Send to retry queue
            success = await self.producer.send_message(
                topic=self.retry_topic,
                message=failed_message.to_dict(),
                key=failed_message.message_id
            )
            
            if success:
                logger.info("Message sent to retry queue",
                           message_id=failed_message.message_id,
                           retry_count=failed_message.retry_count,
                           next_retry_time=failed_message.next_retry_time)
            
            return success
            
        except Exception as e:
            logger.error("Error sending to retry queue", 
                        message_id=failed_message.message_id,
                        error=str(e))
            return False
    
    def _calculate_retry_delay(self, retry_count: int) -> int:
        """Calculate retry delay based on strategy"""
        if self.retry_config.strategy == RetryStrategy.NO_RETRY:
            return 0
        elif self.retry_config.strategy == RetryStrategy.FIXED_DELAY:
            return self.retry_config.initial_delay
        elif self.retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.retry_config.initial_delay * (retry_count + 1)
        else:  # EXPONENTIAL_BACKOFF
            delay = self.retry_config.initial_delay * (self.retry_config.backoff_multiplier ** retry_count)
        
        # Cap at max delay
        return min(int(delay), self.retry_config.max_delay)
    
    def register_error_handler(self, error_type: str, handler: Callable):
        """Register handler for specific error types"""
        self.error_handlers[error_type] = handler
        logger.info("Registered error handler", error_type=error_type)
    
    async def start_dlq_processor(self):
        """Start processing messages from DLQ"""
        self.running = True
        logger.info("Starting DLQ processor")
        
        # Create consumer for DLQ
        dlq_consumer = EnhancedKafkaConsumer(self.kafka_config, [self.dlq_topic])
        dlq_consumer.register_handler(self.dlq_topic, self._process_dlq_message)
        
        # Create consumer for retry queue
        retry_consumer = EnhancedKafkaConsumer(self.kafka_config, [self.retry_topic])
        retry_consumer.register_handler(self.retry_topic, self._process_retry_message)
        
        try:
            # Start both consumers
            await asyncio.gather(
                dlq_consumer.start_consuming(),
                retry_consumer.start_consuming()
            )
        except Exception as e:
            logger.error("Error in DLQ processor", error=str(e))
        finally:
            self.running = False
            dlq_consumer.close()
            retry_consumer.close()
    
    async def _process_dlq_message(self, message_data: Dict[str, Any], context: Dict[str, Any]):
        """Process message from DLQ"""
        try:
            failed_message = FailedMessage.from_dict(message_data)
            
            logger.info("Processing DLQ message",
                       message_id=failed_message.message_id,
                       original_topic=failed_message.original_topic,
                       retry_count=failed_message.retry_count)
            
            # Check if we should retry
            if failed_message.retry_count < self.retry_config.max_retries:
                # Send to retry queue
                await self.send_to_retry_queue(failed_message)
            else:
                # Max retries reached, handle permanently failed message
                await self._handle_permanent_failure(failed_message)
            
            return True
            
        except Exception as e:
            logger.error("Error processing DLQ message", error=str(e))
            return False
    
    async def _process_retry_message(self, message_data: Dict[str, Any], context: Dict[str, Any]):
        """Process message from retry queue"""
        try:
            failed_message = FailedMessage.from_dict(message_data)
            
            # Check if it's time to retry
            if failed_message.next_retry_time and datetime.utcnow() < failed_message.next_retry_time:
                # Not time yet, send back to retry queue
                await self.send_to_retry_queue(failed_message)
                return True
            
            logger.info("Retrying failed message",
                       message_id=failed_message.message_id,
                       retry_count=failed_message.retry_count)
            
            # Attempt to reprocess the original message
            success = await self._retry_original_processing(failed_message)
            
            if not success:
                # Retry failed, send back to DLQ
                await self.send_to_dlq(
                    failed_message.original_data,
                    f"Retry {failed_message.retry_count} failed",
                    failed_message.original_topic,
                    failed_message.original_partition,
                    failed_message.original_offset
                )
            
            return success
            
        except Exception as e:
            logger.error("Error processing retry message", error=str(e))
            return False
    
    async def _retry_original_processing(self, failed_message: FailedMessage) -> bool:
        """Attempt to reprocess the original message"""
        try:
            # This would typically involve sending the message back to the original topic
            # or calling the original processing handler
            
            # For now, we'll simulate retry logic
            # In a real implementation, this would integrate with the stream processor
            
            logger.info("Simulating retry of original processing",
                       message_id=failed_message.message_id)
            
            # Simulate processing (replace with actual retry logic)
            await asyncio.sleep(0.1)
            
            # For demonstration, assume 70% success rate on retry
            import random
            success = random.random() > 0.3
            
            if success:
                logger.info("Retry successful", message_id=failed_message.message_id)
            else:
                logger.warning("Retry failed", message_id=failed_message.message_id)
            
            return success
            
        except Exception as e:
            logger.error("Error in retry processing", 
                        message_id=failed_message.message_id,
                        error=str(e))
            return False
    
    async def _handle_permanent_failure(self, failed_message: FailedMessage):
        """Handle permanently failed messages"""
        logger.error("Message permanently failed after max retries",
                    message_id=failed_message.message_id,
                    original_topic=failed_message.original_topic,
                    retry_count=failed_message.retry_count,
                    error=failed_message.error_message)
        
        # Check if there's a specific handler for this error type
        error_type = self._classify_error(failed_message.error_message)
        handler = self.error_handlers.get(error_type)
        
        if handler:
            try:
                await handler(failed_message)
            except Exception as e:
                logger.error("Error in permanent failure handler",
                            message_id=failed_message.message_id,
                            error=str(e))
        
        # Could also send to a permanent failure topic or external system
        # for manual investigation
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error type for routing to appropriate handler"""
        error_lower = error_message.lower()
        
        if "timeout" in error_lower:
            return "timeout"
        elif "connection" in error_lower:
            return "connection"
        elif "authentication" in error_lower or "authorization" in error_lower:
            return "auth"
        elif "validation" in error_lower or "invalid" in error_lower:
            return "validation"
        elif "rate limit" in error_lower:
            return "rate_limit"
        else:
            return "unknown"
    
    async def get_dlq_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        # This would typically query the DLQ topic for statistics
        # For now, return placeholder stats
        
        return {
            "dlq_topic": self.dlq_topic,
            "retry_topic": self.retry_topic,
            "retry_config": {
                "max_retries": self.retry_config.max_retries,
                "initial_delay": self.retry_config.initial_delay,
                "max_delay": self.retry_config.max_delay,
                "strategy": self.retry_config.strategy.value
            },
            "registered_handlers": list(self.error_handlers.keys()),
            "processor_running": self.running
        }
    
    async def stop(self):
        """Stop DLQ processor"""
        self.running = False
        self.producer.close()
        logger.info("DLQ handler stopped")


class DLQMonitor:
    """Monitor for DLQ metrics and alerting"""
    
    def __init__(self, dlq_handler: DeadLetterQueueHandler):
        self.dlq_handler = dlq_handler
        self.metrics = {
            "messages_in_dlq": 0,
            "messages_retried": 0,
            "messages_permanently_failed": 0,
            "retry_success_rate": 0.0
        }
    
    async def start_monitoring(self):
        """Start DLQ monitoring"""
        while self.dlq_handler.running:
            try:
                await self._collect_metrics()
                await self._check_alerts()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error("Error in DLQ monitoring", error=str(e))
                await asyncio.sleep(60)
    
    async def _collect_metrics(self):
        """Collect DLQ metrics"""
        # This would typically query Kafka topics for actual metrics
        # For now, we'll use placeholder logic
        pass
    
    async def _check_alerts(self):
        """Check for DLQ alert conditions"""
        # Alert if DLQ size is growing too large
        if self.metrics["messages_in_dlq"] > 1000:
            logger.warning("DLQ size is large", 
                          messages_in_dlq=self.metrics["messages_in_dlq"])
        
        # Alert if retry success rate is too low
        if self.metrics["retry_success_rate"] < 0.5:
            logger.warning("Low retry success rate",
                          success_rate=self.metrics["retry_success_rate"])
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current DLQ metrics"""
        return self.metrics.copy()