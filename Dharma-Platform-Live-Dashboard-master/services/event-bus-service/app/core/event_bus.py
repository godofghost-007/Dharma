"""
Event Bus implementation for cross-service communication
"""
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import logging

logger = logging.getLogger(__name__)

@dataclass
class Event:
    """Event data structure"""
    event_id: str
    event_type: str
    source_service: str
    timestamp: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_service": self.source_service,
            "timestamp": self.timestamp,
            "data": self.data,
            "correlation_id": self.correlation_id
        }

class EventBus:
    """Event-driven communication between services"""
    
    def __init__(self, kafka_config: Dict[str, Any]):
        self.kafka_config = kafka_config
        self.producer = None
        self.consumers = {}
        self.event_handlers = {}
        self.running = False
        
    async def initialize(self):
        """Initialize Kafka producer and consumers"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_config.get('bootstrap_servers', ['localhost:9092']),
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                acks='all',
                retries=3,
                retry_backoff_ms=1000
            )
            logger.info("Event bus producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize event bus producer: {e}")
            raise
    
    async def publish_event(self, topic: str, event_type: str, data: Dict[str, Any], 
                          source_service: str, correlation_id: Optional[str] = None):
        """Publish event to topic"""
        if not self.producer:
            raise RuntimeError("Event bus not initialized")
            
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            source_service=source_service,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
            correlation_id=correlation_id
        )
        
        try:
            future = self.producer.send(topic, value=event.to_dict(), key=event.event_id)
            record_metadata = future.get(timeout=10)
            logger.info(f"Event published to {topic}: {event.event_id}")
            return event.event_id
        except KafkaError as e:
            logger.error(f"Failed to publish event to {topic}: {e}")
            raise 
   
    async def subscribe_to_events(self, topics: List[str], group_id: str, handler: Callable):
        """Subscribe to events and register handler"""
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.kafka_config.get('bootstrap_servers', ['localhost:9092']),
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            self.consumers[group_id] = consumer
            self.event_handlers[group_id] = handler
            
            logger.info(f"Subscribed to topics {topics} with group {group_id}")
            
            # Start consuming in background task
            asyncio.create_task(self._consume_events(consumer, handler, group_id))
            
        except Exception as e:
            logger.error(f"Failed to subscribe to topics {topics}: {e}")
            raise
    
    async def _consume_events(self, consumer: KafkaConsumer, handler: Callable, group_id: str):
        """Consume events from Kafka topics"""
        self.running = True
        
        try:
            while self.running:
                message_batch = consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            event_data = message.value
                            event = Event(**event_data)
                            
                            # Process event with handler
                            await handler(message.topic, event)
                            
                        except Exception as e:
                            logger.error(f"Error processing event from {message.topic}: {e}")
                            await self._handle_event_processing_error(e, message, group_id)
                            
        except Exception as e:
            logger.error(f"Consumer {group_id} error: {e}")
        finally:
            consumer.close()
    
    async def _handle_event_processing_error(self, error: Exception, message, group_id: str):
        """Handle event processing errors"""
        error_event = {
            "error": str(error),
            "original_message": message.value,
            "topic": message.topic,
            "partition": message.partition,
            "offset": message.offset,
            "group_id": group_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to dead letter queue
        await self.publish_event(
            topic="events.dead_letter",
            event_type="event_processing_error",
            data=error_event,
            source_service="event_bus"
        )
    
    async def shutdown(self):
        """Shutdown event bus"""
        self.running = False
        
        if self.producer:
            self.producer.close()
            
        for consumer in self.consumers.values():
            consumer.close()
            
        logger.info("Event bus shutdown complete")