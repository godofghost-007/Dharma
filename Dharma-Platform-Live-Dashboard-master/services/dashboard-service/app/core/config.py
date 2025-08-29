"""
Dashboard Service Configuration
"""

import os
from typing import Optional, List
from dataclasses import dataclass, field

@dataclass
class DashboardConfig:
    """Dashboard service configuration"""
    
    # API Gateway
    api_gateway_url: str = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    
    # Database connections (for direct access if needed)
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    postgresql_url: str = os.getenv("POSTGRESQL_URL", "postgresql://postgres:password@localhost:5432/dharma_platform")
    elasticsearch_url: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Dashboard settings
    refresh_interval: int = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "30"))  # seconds
    max_chart_points: int = int(os.getenv("MAX_CHART_POINTS", "1000"))
    
    # Real-time updates
    websocket_url: str = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/ws")
    
    # Export settings
    export_max_records: int = int(os.getenv("EXPORT_MAX_RECORDS", "10000"))
    
    # Internationalization
    default_language: str = os.getenv("DEFAULT_LANGUAGE", "en")
    supported_languages: List[str] = field(default_factory=lambda: ["en", "hi", "bn", "ta", "ur"])
    
    # Accessibility
    high_contrast_mode: bool = os.getenv("HIGH_CONTRAST_MODE", "false").lower() == "true"
    large_font_mode: bool = os.getenv("LARGE_FONT_MODE", "false").lower() == "true"