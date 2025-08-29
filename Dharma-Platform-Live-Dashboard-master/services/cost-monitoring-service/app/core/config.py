"""
Configuration for Cost Monitoring Service
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseSettings, Field

class CostMonitoringConfig(BaseSettings):
    """Configuration settings for cost monitoring service"""
    
    # Database settings
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    postgresql_url: str = Field(default="postgresql://user:password@localhost:5432/dharma", env="POSTGRESQL_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Cloud provider settings
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    
    gcp_project_id: Optional[str] = Field(default=None, env="GCP_PROJECT_ID")
    gcp_credentials_path: Optional[str] = Field(default=None, env="GCP_CREDENTIALS_PATH")
    
    azure_subscription_id: Optional[str] = Field(default=None, env="AZURE_SUBSCRIPTION_ID")
    azure_tenant_id: Optional[str] = Field(default=None, env="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, env="AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = Field(default=None, env="AZURE_CLIENT_SECRET")
    
    # Budget settings
    default_monthly_budget: float = Field(default=10000.0, env="DEFAULT_MONTHLY_BUDGET")
    budget_alert_thresholds: List[float] = Field(default=[0.5, 0.8, 0.9, 1.0])
    
    # Cost tracking settings
    cost_collection_interval: int = Field(default=3600, env="COST_COLLECTION_INTERVAL")  # seconds
    cost_retention_days: int = Field(default=365, env="COST_RETENTION_DAYS")
    
    # Optimization settings
    optimization_analysis_interval: int = Field(default=21600, env="OPTIMIZATION_ANALYSIS_INTERVAL")  # 6 hours
    min_savings_threshold: float = Field(default=50.0, env="MIN_SAVINGS_THRESHOLD")  # minimum monthly savings to recommend
    
    # Autoscaling settings
    autoscaling_enabled: bool = Field(default=True, env="AUTOSCALING_ENABLED")
    cost_performance_ratio_threshold: float = Field(default=0.8, env="COST_PERFORMANCE_RATIO_THRESHOLD")
    
    # Component mapping for cost attribution
    component_tags: Dict[str, str] = Field(default={
        "data-collection": "dharma-data-collection",
        "ai-analysis": "dharma-ai-analysis", 
        "alert-management": "dharma-alert-management",
        "api-gateway": "dharma-api-gateway",
        "dashboard": "dharma-dashboard",
        "stream-processing": "dharma-stream-processing",
        "event-bus": "dharma-event-bus",
        "cost-monitoring": "dharma-cost-monitoring",
        "database": "dharma-database",
        "cache": "dharma-cache",
        "monitoring": "dharma-monitoring"
    })
    
    # Alert settings
    alert_webhook_url: Optional[str] = Field(default=None, env="ALERT_WEBHOOK_URL")
    alert_email_recipients: List[str] = Field(default=["admin@dharma.gov"], env="ALERT_EMAIL_RECIPIENTS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Service-specific cost thresholds
SERVICE_COST_THRESHOLDS = {
    "data-collection": {
        "daily_threshold": 100.0,
        "monthly_threshold": 2000.0,
        "cpu_cost_per_hour": 0.05,
        "memory_cost_per_gb_hour": 0.01
    },
    "ai-analysis": {
        "daily_threshold": 200.0,
        "monthly_threshold": 4000.0,
        "gpu_cost_per_hour": 2.50,
        "inference_cost_per_request": 0.001
    },
    "database": {
        "daily_threshold": 150.0,
        "monthly_threshold": 3000.0,
        "storage_cost_per_gb_month": 0.10,
        "iops_cost_per_operation": 0.0001
    },
    "cache": {
        "daily_threshold": 50.0,
        "monthly_threshold": 1000.0,
        "memory_cost_per_gb_hour": 0.02
    }
}

# Cost optimization rules
OPTIMIZATION_RULES = {
    "idle_resources": {
        "cpu_utilization_threshold": 5.0,  # %
        "memory_utilization_threshold": 10.0,  # %
        "idle_duration_threshold": 3600  # seconds
    },
    "oversized_instances": {
        "cpu_utilization_threshold": 80.0,  # %
        "memory_utilization_threshold": 80.0,  # %
        "sustained_duration": 86400  # 24 hours
    },
    "storage_optimization": {
        "unused_storage_threshold": 30.0,  # %
        "old_snapshot_days": 30,
        "infrequent_access_days": 90
    }
}