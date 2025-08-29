"""
Kafka streaming configuration and topic management
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import structlog

logger = structlog.get_logger()


@dataclass
class KafkaStreamConfig:
    """Kafka streaming configuration"""
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    topic_prefix: str = os.getenv("KAFKA_TOPIC_PREFIX", "dharma")
    num_partitions: int = int(os.getenv("KAFKA_NUM_PARTITIONS", "3"))
    replication_factor: int = int(os.getenv("KAFKA_REPLICATION_FACTOR", "1"))
    consumer_group_id: str = os.getenv("KAFKA_CONSUMER_GROUP", "dharma-stream-processors")
    
    @property
    def producer_config(self) -> Dict:
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "acks": "all",
            "retries": 3,
            "retry_backoff_ms": 1000,
            "request_timeout_ms": 30000,
            "max_in_flight_requests_per_connection": 1,
            "enable_idempotence": True
        }
    
    @property
    def consumer_config(self) -> Dict:
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "group_id": self.consumer_group_id,
            "auto_offset_reset": "earliest",
            "enable_auto_commit": False,
            "max_poll_records": 100,
            "session_timeout_ms": 30000,
            "heartbeat_interval_ms": 10000
        }


class KafkaTopicManager:
    """Manages Kafka topics for streaming pipeline"""
    
    def __init__(self, config: KafkaStreamConfig):
        self.config = config
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=config.bootstrap_servers,
            client_id="dharma-topic-manager"
        )
        
        # Define all topics needed for the streaming pipeline
        self.topics = {
            # Raw data ingestion topics
            "raw_twitter": f"{config.topic_prefix}.raw.twitter",
            "raw_youtube": f"{config.topic_prefix}.raw.youtube", 
            "raw_web": f"{config.topic_prefix}.raw.web",
            "raw_telegram": f"{config.topic_prefix}.raw.telegram",
            
            # Processing stage topics
            "sentiment_analysis": f"{config.topic_prefix}.analysis.sentiment",
            "bot_detection": f"{config.topic_prefix}.analysis.bot_detection",
            "campaign_detection": f"{config.topic_prefix}.analysis.campaign_detection",
            
            # Results topics
            "analysis_results": f"{config.topic_prefix}.results.analysis",
            "alerts": f"{config.topic_prefix}.results.alerts",
            "campaigns": f"{config.topic_prefix}.results.campaigns",
            
            # Error handling topics
            "dead_letter_queue": f"{config.topic_prefix}.errors.dlq",
            "retry_queue": f"{config.topic_prefix}.errors.retry"
        }
    
    async def create_topics(self) -> bool:
        """Create all required Kafka topics"""
        topic_list = []
        
        for topic_name, topic_full_name in self.topics.items():
            # Configure partitions based on topic type
            partitions = self._get_partitions_for_topic(topic_name)
            
            topic_list.append(NewTopic(
                name=topic_full_name,
                num_partitions=partitions,
                replication_factor=self.config.replication_factor,
                topic_configs=self._get_topic_config(topic_name)
            ))
        
        try:
            self.admin_client.create_topics(topic_list, validate_only=False)
            logger.info("Successfully created Kafka topics", topics=list(self.topics.values()))
            return True
        except TopicAlreadyExistsError:
            logger.info("Topics already exist, skipping creation")
            return True
        except Exception as e:
            logger.error("Failed to create Kafka topics", error=str(e))
            return False
    
    def _get_partitions_for_topic(self, topic_name: str) -> int:
        """Get optimal partition count for topic type"""
        high_throughput_topics = ["raw_twitter", "raw_youtube", "sentiment_analysis"]
        if topic_name in high_throughput_topics:
            return self.config.num_partitions * 2  # More partitions for high throughput
        return self.config.num_partitions
    
    def _get_topic_config(self, topic_name: str) -> Dict[str, str]:
        """Get topic-specific configuration"""
        base_config = {
            "cleanup.policy": "delete",
            "retention.ms": "604800000",  # 7 days
            "compression.type": "snappy"
        }
        
        # Special configs for different topic types
        if topic_name.startswith("raw_"):
            base_config["retention.ms"] = "259200000"  # 3 days for raw data
        elif topic_name == "dead_letter_queue":
            base_config["retention.ms"] = "2592000000"  # 30 days for errors
        
        return base_config