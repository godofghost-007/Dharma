"""
Configuration for Event Bus Service
"""
import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings

class EventBusConfig(BaseSettings):
    """Event Bus Service configuration"""
    
    # Service settings
    service_name: str = "event-bus-service"
    service_port: int = 8005
    debug: bool = False
    
    # Kafka settings
    kafka_bootstrap_servers: List[str] = ["localhost:9092"]
    kafka_producer_acks: str = "all"
    kafka_producer_retries: int = 3
    kafka_producer_retry_backoff_ms: int = 1000
    kafka_consumer_group_id: str = "event-bus-group"
    kafka_consumer_auto_offset_reset: str = "latest"
    
    # Temporal settings
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "dharma-workflows"
    
    # Monitoring settings
    monitoring_interval_seconds: int = 30
    workflow_stuck_threshold_hours: int = 2
    max_workflow_execution_hours: int = 4
    
    # Event topics
    event_topics: Dict[str, str] = {
        "data_collected": "data.collected",
        "analysis_completed": "analysis.completed", 
        "campaign_detected": "campaign.detected",
        "alert_triggered": "alert.triggered",
        "dead_letter": "events.dead_letter",
        "alerts_check": "alerts.check",
        "alerts_urgent": "alerts.urgent"
    }
    
    # Retry policies
    default_retry_attempts: int = 3
    default_retry_backoff_seconds: int = 2
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_prefix = "EVENT_BUS_"
        case_sensitive = False

# Global configuration instance
config = EventBusConfig()

def get_kafka_config() -> Dict[str, Any]:
    """Get Kafka configuration"""
    return {
        "bootstrap_servers": config.kafka_bootstrap_servers,
        "producer_config": {
            "acks": config.kafka_producer_acks,
            "retries": config.kafka_producer_retries,
            "retry_backoff_ms": config.kafka_producer_retry_backoff_ms
        },
        "consumer_config": {
            "group_id": config.kafka_consumer_group_id,
            "auto_offset_reset": config.kafka_consumer_auto_offset_reset
        }
    }

def get_temporal_config() -> Dict[str, Any]:
    """Get Temporal configuration"""
    return {
        "host": config.temporal_host,
        "namespace": config.temporal_namespace,
        "task_queue": config.temporal_task_queue
    }