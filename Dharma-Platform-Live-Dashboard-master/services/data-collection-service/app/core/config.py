"""
Configuration settings for the data collection service
"""
from functools import lru_cache
from typing import Optional, Dict, Any
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field


class TwitterCredentials(BaseSettings):
    """Twitter API credentials"""
    bearer_token: str = Field(..., env="TWITTER_BEARER_TOKEN")
    api_key: str = Field(..., env="TWITTER_API_KEY")
    api_secret: str = Field(..., env="TWITTER_API_SECRET")
    access_token: str = Field(..., env="TWITTER_ACCESS_TOKEN")
    access_token_secret: str = Field(..., env="TWITTER_ACCESS_TOKEN_SECRET")
    
    def validate_credentials(self) -> bool:
        """Validate that all required credentials are present and non-empty"""
        required_fields = [
            self.bearer_token, self.api_key, self.api_secret, 
            self.access_token, self.access_token_secret
        ]
        return all(field and field.strip() for field in required_fields)
    
    def get_auth_config(self) -> dict:
        """Get authentication configuration for tweepy client"""
        return {
            "bearer_token": self.bearer_token,
            "consumer_key": self.api_key,
            "consumer_secret": self.api_secret,
            "access_token": self.access_token,
            "access_token_secret": self.access_token_secret
        }


class TelegramCredentials(BaseSettings):
    """Telegram API credentials"""
    api_id: int = Field(..., env="TELEGRAM_API_ID")
    api_hash: str = Field(..., env="TELEGRAM_API_HASH")
    phone_number: str = Field(..., env="TELEGRAM_PHONE_NUMBER")


class KafkaConfig(BaseSettings):
    """Kafka configuration"""
    bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    topic_prefix: str = Field(default="dharma", env="KAFKA_TOPIC_PREFIX")
    
    @property
    def producer_config(self) -> Dict[str, Any]:
        return {
            "bootstrap_servers": self.bootstrap_servers.split(","),
            "value_serializer": lambda x: x.encode('utf-8') if isinstance(x, str) else x
        }


class Settings(BaseSettings):
    """Main application settings"""
    # API Keys
    youtube_api_key: str = Field(..., env="YOUTUBE_API_KEY")
    
    # Database
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Rate limiting
    default_rate_limit: int = Field(default=100, env="DEFAULT_RATE_LIMIT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Nested configurations - will be loaded on demand
    twitter_credentials: Optional[TwitterCredentials] = None
    telegram_credentials: Optional[TelegramCredentials] = None
    kafka_config: Optional[KafkaConfig] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize nested configs only if environment variables are available
        try:
            self.twitter_credentials = TwitterCredentials()
        except:
            self.twitter_credentials = None
        
        try:
            self.telegram_credentials = TelegramCredentials()
        except:
            self.telegram_credentials = None
        
        try:
            self.kafka_config = KafkaConfig()
        except:
            self.kafka_config = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()