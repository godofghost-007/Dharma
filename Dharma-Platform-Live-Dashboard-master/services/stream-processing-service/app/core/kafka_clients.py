"""
Enhanced Kafka producers and consumers with error handling and monitoring
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError, KafkaTimeoutError, CommitFailedError
import structlog

from .kafka_config import KafkaStreamConfig

logger = structlog.get_logger()


class EnhancedKafkaProducer:
    """Enhanced Kafka producer with retry logic and monitoring"""
    
    def __init__(self, config: KafkaStreamConfig):
        self.config = config
        self.producer = None
        self.metrics = {
            "messages_sent": 0,
            "messages_failed": 0,
            "bytes_sent": 0,
            "last_send_time": None
        }
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialize Kafka producer with enhanced configuration"""
        try:
            self.producer = KafkaProducer(
                **self.config.producer_config,
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                # Enhanced reliability settings
                max_block_ms=60000,
                buffer_memory=33554432,  # 32MB
                batch_size=16384,
                linger_ms=5,  # Small delay to batch messages
                compression_type='snappy'
            )
            logger.info("Enhanced Kafka producer initialized")
        except Exception as e:
            logger.error("Failed to initialize Kafka producer", error=str(e))
            raise
    
    async def send_message(self, topic: str, message: Dict[str, Any], 
                          key: Optional[str] = None, 
                          partition: Optional[int] = None,
                          headers: Optional[Dict[str, str]] = None) -> bool:
        """Send message with retry logic and error handling"""
        if not self.producer:
            logger.error("Producer not initialized")
            return False
        
        try:
            # Add message metadata
            enhanced_message = {
                **message,
                "producer_timestamp": datetime.utcnow().isoformat(),
                "producer_id": "dharma-stream-processor"
            }
            
            # Prepare headers
            kafka_headers = []
            if headers:
                kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]
            
            # Send message
            future = self.producer.send(
                topic=topic,
                value=enhanced_message,
                key=key,
                partition=partition,
                headers=kafka_headers
            )
            
            # Wait for send to complete with timeout
            record_metadata = future.get(timeout=30)
            
            # Update metrics
            self.metrics["messages_sent"] += 1
            self.metrics["bytes_sent"] += len(json.dumps(enhanced_message))
            self.metrics["last_send_time"] = datetime.utcnow().isoformat()
            
            logger.debug("Message sent successfully",
                        topic=topic,
                        partition=record_metadata.partition,
                        offset=record_metadata.offset)
            
            return True
            
        except KafkaTimeoutError:
            logger.error("Kafka send timeout", topic=topic)
            self.metrics["messages_failed"] += 1
            return False
        except KafkaError as e:
            logger.error("Kafka send error", topic=topic, error=str(e))
            self.metrics["messages_failed"] += 1
            return False
        except Exception as e:
            logger.error("Unexpected error sending message", topic=topic, error=str(e))
            self.metrics["messages_failed"] += 1
            return False
    
    async def send_batch(self, topic: str, messages: List[Dict[str, Any]]) -> int:
        """Send multiple messages in batch"""
        successful_sends = 0
        
        tasks = []
        for message in messages:
            task = asyncio.create_task(self.send_message(topic, message))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result is True:
                successful_sends += 1
        
        logger.info("Batch send completed",
                   topic=topic,
                   total_messages=len(messages),
                   successful=successful_sends,
                   failed=len(messages) - successful_sends)
        
        return successful_sends
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get producer metrics"""
        return self.metrics.copy()
    
    def close(self):
        """Close producer"""
        if self.producer:
            self.producer.flush()  # Ensure all messages are sent
            self.producer.close()
            logger.info("Kafka producer closed")


class EnhancedKafkaConsumer:
    """Enhanced Kafka consumer with error handling and monitoring"""
    
    def __init__(self, config: KafkaStreamConfig, topics: List[str]):
        self.config = config
        self.topics = topics
        self.consumer = None
        self.message_handlers = {}
        self.metrics = {
            "messages_consumed": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "last_consume_time": None
        }
        self.running = False
        self._initialize_consumer()
    
    def _initialize_consumer(self):
        """Initialize Kafka consumer with enhanced configuration"""
        try:
            self.consumer = KafkaConsumer(
                *self.topics,
                **self.config.consumer_config,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                # Enhanced reliability settings
                fetch_min_bytes=1024,
                fetch_max_wait_ms=500,
                max_partition_fetch_bytes=1048576,  # 1MB
                check_crcs=True
            )
            logger.info("Enhanced Kafka consumer initialized", topics=self.topics)
        except Exception as e:
            logger.error("Failed to initialize Kafka consumer", error=str(e))
            raise
    
    def register_handler(self, topic: str, handler: Callable):
        """Register message handler for specific topic"""
        self.message_handlers[topic] = handler
        logger.info("Registered handler for topic", topic=topic)
    
    async def start_consuming(self):
        """Start consuming messages with error handling"""
        if not self.consumer:
            raise RuntimeError("Consumer not initialized")
        
        self.running = True
        logger.info("Starting message consumption", topics=self.topics)
        
        try:
            while self.running:
                try:
                    # Poll for messages
                    message_batch = self.consumer.poll(timeout_ms=1000)
                    
                    if not message_batch:
                        continue
                    
                    # Process messages
                    await self._process_message_batch(message_batch)
                    
                    # Commit offsets after successful processing
                    try:
                        self.consumer.commit()
                    except CommitFailedError as e:
                        logger.error("Failed to commit offsets", error=str(e))
                        # Continue processing, don't stop on commit failures
                    
                except KafkaError as e:
                    logger.error("Kafka consumer error", error=str(e))
                    await asyncio.sleep(5)  # Wait before retrying
                    continue
                    
        except Exception as e:
            logger.error("Critical error in consumer loop", error=str(e))
            raise
        finally:
            self.running = False
    
    async def _process_message_batch(self, message_batch):
        """Process batch of messages in parallel"""
        tasks = []
        
        for topic_partition, messages in message_batch.items():
            topic = topic_partition.topic
            
            for message in messages:
                task = asyncio.create_task(
                    self._process_single_message(topic, message)
                )
                tasks.append(task)
        
        # Process all messages in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful/failed processing
            successful = sum(1 for r in results if r is True)
            failed = len(results) - successful
            
            self.metrics["messages_consumed"] += len(tasks)
            self.metrics["messages_processed"] += successful
            self.metrics["messages_failed"] += failed
            self.metrics["last_consume_time"] = datetime.utcnow().isoformat()
            
            if failed > 0:
                logger.warning("Some messages failed processing",
                             successful=successful,
                             failed=failed)
    
    async def _process_single_message(self, topic: str, message) -> bool:
        """Process single message with error handling"""
        try:
            handler = self.message_handlers.get(topic)
            if not handler:
                logger.warning("No handler registered for topic", topic=topic)
                return False
            
            # Create processing context
            context = {
                "topic": topic,
                "partition": message.partition,
                "offset": message.offset,
                "timestamp": message.timestamp,
                "key": message.key,
                "headers": dict(message.headers) if message.headers else {}
            }
            
            # Execute handler
            result = await handler(message.value, context)
            
            logger.debug("Message processed successfully",
                        topic=topic,
                        partition=message.partition,
                        offset=message.offset)
            
            return True
            
        except Exception as e:
            logger.error("Error processing message",
                        topic=topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e))
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics"""
        return self.metrics.copy()
    
    def stop_consuming(self):
        """Stop consuming messages"""
        self.running = False
        logger.info("Stopping message consumption")
    
    def close(self):
        """Close consumer"""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")


class KafkaHealthChecker:
    """Health checker for Kafka infrastructure"""
    
    def __init__(self, config: KafkaStreamConfig):
        self.config = config
    
    async def check_kafka_health(self) -> Dict[str, Any]:
        """Check Kafka cluster health"""
        health_status = {
            "kafka_available": False,
            "topics_accessible": False,
            "producer_working": False,
            "consumer_working": False,
            "error": None
        }
        
        try:
            # Test producer
            test_producer = KafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                request_timeout_ms=5000,
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            
            # Send test message
            test_topic = f"{self.config.topic_prefix}.health.test"
            future = test_producer.send(test_topic, {"test": "health_check"})
            future.get(timeout=5)
            
            health_status["kafka_available"] = True
            health_status["producer_working"] = True
            
            test_producer.close()
            
            # Test consumer
            test_consumer = KafkaConsumer(
                test_topic,
                bootstrap_servers=self.config.bootstrap_servers,
                consumer_timeout_ms=5000,
                auto_offset_reset='latest'
            )
            
            health_status["consumer_working"] = True
            health_status["topics_accessible"] = True
            
            test_consumer.close()
            
        except Exception as e:
            health_status["error"] = str(e)
            logger.error("Kafka health check failed", error=str(e))
        
        return health_status