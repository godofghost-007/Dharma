"""
Kafka producer for streaming collected data
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
import structlog

from app.core.config import KafkaConfig

logger = structlog.get_logger()


class KafkaDataProducer:
    """Kafka producer for streaming collected data to processing pipeline"""
    
    def __init__(self, kafka_config: KafkaConfig):
        self.config = kafka_config
        self.producer = None
        self.topics = {
            "twitter": f"{kafka_config.topic_prefix}.twitter.raw",
            "youtube": f"{kafka_config.topic_prefix}.youtube.raw", 
            "web": f"{kafka_config.topic_prefix}.web.raw",
            "telegram": f"{kafka_config.topic_prefix}.telegram.raw"
        }
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialize Kafka producer with error handling"""
        try:
            self.producer = KafkaProducer(
                **self.config.producer_config,
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                retries=3,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                acks='all'
            )
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Kafka producer", error=str(e))
            raise
    
    async def send_data(self, platform: str, data: Dict[str, Any], collection_id: str):
        """Send collected data to appropriate Kafka topic"""
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return False
        
        topic = self.topics.get(platform)
        if not topic:
            logger.error("Unknown platform", platform=platform)
            return False
        
        # Add metadata
        message = {
            "collection_id": collection_id,
            "platform": platform,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        try:
            # Send message asynchronously
            future = self.producer.send(topic, value=message)
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            
            logger.info(
                "Data sent to Kafka",
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                platform=platform,
                collection_id=collection_id
            )
            return True
            
        except KafkaError as e:
            logger.error("Failed to send data to Kafka", error=str(e), platform=platform)
            return False
        except Exception as e:
            logger.error("Unexpected error sending to Kafka", error=str(e), platform=platform)
            return False
    
    async def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")