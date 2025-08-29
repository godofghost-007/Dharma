"""Configuration for API Gateway Service."""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class APIGatewaySettings(BaseSettings):
    """Main API Gateway configuration."""
    
    # Application settings
    app_name: str = Field(default="Project Dharma API Gateway")
    version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # Server configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"])
    cors_methods: List[str] = Field(default=["*"])
    cors_headers: List[str] = Field(default=["*"])
    
    # Security settings
    security_secret_key: str = Field(description="JWT secret key")
    security_algorithm: str = Field(default="HS256", description="JWT algorithm")
    security_access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    security_refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration")
    
    # Rate limiting settings
    rate_limit_default_rate_limit: str = Field(default="100/minute", description="Default rate limit")
    rate_limit_redis_url: str = Field(default="redis://localhost:6379", description="Redis URL for rate limiting")
    rate_limit_admin_rate_limit: str = Field(default="1000/minute")
    rate_limit_analyst_rate_limit: str = Field(default="500/minute")
    rate_limit_viewer_rate_limit: str = Field(default="100/minute")
    
    # Database settings
    db_postgresql_url: str = Field(default="postgresql://localhost:5432/dharma")
    db_redis_url: str = Field(default="redis://localhost:6379")
    
    # Service settings
    service_data_collection_url: str = Field(default="http://data-collection-service:8001")
    service_ai_analysis_url: str = Field(default="http://ai-analysis-service:8002")
    service_alert_management_url: str = Field(default="http://alert-management-service:8003")
    service_dashboard_url: str = Field(default="http://dashboard-service:8004")
    service_health_check_timeout: int = Field(default=5, description="Health check timeout in seconds")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = APIGatewaySettings()