"""Application settings and configuration."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="dharma_platform")
    
    postgresql_url: str = Field(default="postgresql://localhost:5432/dharma")
    postgresql_pool_size: int = Field(default=10)
    
    elasticsearch_url: str = Field(default="http://localhost:9200")
    elasticsearch_index_prefix: str = Field(default="dharma")
    
    class Config:
        env_prefix = "DB_"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    url: str = Field(default="redis://localhost:6379")
    max_connections: int = Field(default=20)
    decode_responses: bool = Field(default=True)
    
    class Config:
        env_prefix = "REDIS_"


class Settings(BaseSettings):
    """Main application settings."""
    
    app_name: str = Field(default="Project Dharma")
    debug: bool = Field(default=False)
    version: str = Field(default="1.0.0")
    
    # Service configuration
    service_name: str = Field(default="unknown")
    service_port: int = Field(default=8000)
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production")
    access_token_expire_minutes: int = Field(default=30)
    
    # External APIs
    twitter_bearer_token: Optional[str] = None
    youtube_api_key: Optional[str] = None
    
    # Database settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"