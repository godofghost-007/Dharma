"""Configuration settings for AI Analysis Service."""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = "ai-analysis-service"
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # API configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8003, env="PORT")
    
    # Database configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Kafka configuration
    kafka_bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group: str = Field(default="ai-analysis-group", env="KAFKA_CONSUMER_GROUP")
    
    # Model configuration
    models_path: str = Field(default="./models", env="MODELS_PATH")
    sentiment_model_name: str = Field(default="dharma-bert-sentiment", env="SENTIMENT_MODEL_NAME")
    bot_detection_model_name: str = Field(default="dharma-bot-detector", env="BOT_DETECTION_MODEL_NAME")
    
    # Processing configuration
    batch_size: int = Field(default=32, env="BATCH_SIZE")
    max_content_length: int = Field(default=512, env="MAX_CONTENT_LENGTH")
    confidence_threshold: float = Field(default=0.7, env="CONFIDENCE_THRESHOLD")
    
    # Translation configuration
    translation_service: str = Field(default="google", env="TRANSLATION_SERVICE")
    supported_languages: List[str] = Field(
        default=["hi", "bn", "ta", "ur", "te", "ml", "kn", "gu", "pa", "or"],
        env="SUPPORTED_LANGUAGES"
    )
    
    # Performance configuration
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    max_batch_size: int = Field(default=100, env="MAX_BATCH_SIZE")
    max_coordination_group_size: int = Field(default=50, env="MAX_COORDINATION_GROUP_SIZE")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()