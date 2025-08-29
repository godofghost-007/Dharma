"""Configuration for Alert Management Service."""

import os
from typing import List, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings


class AlertConfig(BaseSettings):
    """Alert management service configuration."""
    
    # Service configuration
    service_name: str = "alert-management-service"
    service_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # API configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8006, env="PORT")
    
    # Database connections
    mongodb_url: str = Field(env="MONGODB_URL", default="mongodb://localhost:27017")
    mongodb_database: str = Field(env="MONGODB_DATABASE", default="dharma_platform")
    
    postgresql_url: str = Field(env="POSTGRESQL_URL", default="postgresql://user:password@localhost:5432/dharma")
    
    redis_url: str = Field(env="REDIS_URL", default="redis://localhost:6379")
    
    # Kafka configuration
    kafka_bootstrap_servers: str = Field(env="KAFKA_BOOTSTRAP_SERVERS", default="localhost:9092")
    kafka_alert_topic: str = Field(env="KAFKA_ALERT_TOPIC", default="alerts")
    kafka_notification_topic: str = Field(env="KAFKA_NOTIFICATION_TOPIC", default="notifications")
    
    # Notification service configuration
    twilio_account_sid: str = Field(env="TWILIO_ACCOUNT_SID", default="")
    twilio_auth_token: str = Field(env="TWILIO_AUTH_TOKEN", default="")
    twilio_phone_number: str = Field(env="TWILIO_PHONE_NUMBER", default="")
    
    smtp_server: str = Field(env="SMTP_SERVER", default="localhost")
    smtp_port: int = Field(env="SMTP_PORT", default=587)
    smtp_username: str = Field(env="SMTP_USERNAME", default="")
    smtp_password: str = Field(env="SMTP_PASSWORD", default="")
    smtp_from_email: str = Field(env="SMTP_FROM_EMAIL", default="alerts@dharma.gov")
    
    # WebSocket configuration
    websocket_port: int = Field(env="WEBSOCKET_PORT", default=8765)
    websocket_host: str = Field(env="WEBSOCKET_HOST", default="0.0.0.0")
    
    # Dashboard configuration
    dashboard_base_url: str = Field(env="DASHBOARD_BASE_URL", default="https://dharma.gov")
    
    # Webhook configuration
    webhook_signing_secret: str = Field(env="WEBHOOK_SIGNING_SECRET", default="")
    webhook_allowed_domains: List[str] = Field(env="WEBHOOK_ALLOWED_DOMAINS", default=[])
    webhook_timeout_seconds: int = Field(env="WEBHOOK_TIMEOUT_SECONDS", default=30)
    webhook_max_retries: int = Field(env="WEBHOOK_MAX_RETRIES", default=3)
    
    # Alert generation configuration
    alert_deduplication_window_minutes: int = Field(default=30, env="ALERT_DEDUPLICATION_WINDOW")
    alert_correlation_threshold: float = Field(default=0.8, env="ALERT_CORRELATION_THRESHOLD")
    max_alerts_per_hour: int = Field(default=100, env="MAX_ALERTS_PER_HOUR")
    
    # Severity scoring weights
    severity_weights: Dict[str, float] = {
        "confidence_score": 0.3,
        "risk_score": 0.4,
        "volume_impact": 0.2,
        "temporal_urgency": 0.1
    }
    
    # Alert type configurations
    alert_type_configs: Dict[str, Dict[str, Any]] = {
        "high_risk_content": {
            "min_confidence": 0.7,
            "min_risk_score": 0.6,
            "auto_escalate": True,
            "escalation_delay_minutes": 15
        },
        "bot_network_detected": {
            "min_confidence": 0.8,
            "min_risk_score": 0.7,
            "auto_escalate": True,
            "escalation_delay_minutes": 30
        },
        "coordinated_campaign": {
            "min_confidence": 0.75,
            "min_risk_score": 0.8,
            "auto_escalate": True,
            "escalation_delay_minutes": 10
        },
        "viral_misinformation": {
            "min_confidence": 0.6,
            "min_risk_score": 0.9,
            "auto_escalate": True,
            "escalation_delay_minutes": 5
        }
    }
    
    # Escalation rules
    escalation_rules: List[Dict[str, Any]] = [
        {
            "severity": "critical",
            "max_unacknowledged_minutes": 15,
            "max_investigation_minutes": 60,
            "escalation_levels": ["level_2", "level_3", "level_4"]
        },
        {
            "severity": "high",
            "max_unacknowledged_minutes": 30,
            "max_investigation_minutes": 120,
            "escalation_levels": ["level_2", "level_3"]
        },
        {
            "severity": "medium",
            "max_unacknowledged_minutes": 60,
            "max_investigation_minutes": 240,
            "escalation_levels": ["level_2"]
        }
    ]
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False


# Global configuration instance
config = AlertConfig()