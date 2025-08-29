"""Configuration for model governance and lifecycle management."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import timedelta


@dataclass
class ModelGovernanceConfig:
    """Configuration for model governance system."""
    
    # Registry settings
    registry_path: str = "models"
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"
    
    # Performance monitoring settings
    performance_monitoring_enabled: bool = True
    drift_detection_enabled: bool = True
    drift_check_interval_hours: int = 6
    performance_summary_days: int = 7
    
    # A/B testing settings
    ab_testing_enabled: bool = True
    default_traffic_split: float = 0.1
    default_test_duration_hours: int = 24
    minimum_sample_size: int = 1000
    confidence_level: float = 0.95
    auto_promotion_enabled: bool = True
    auto_promotion_improvement_threshold: float = 0.05  # 5% improvement
    
    # Alert thresholds
    accuracy_drop_threshold: float = 0.05  # 5% drop triggers alert
    latency_increase_threshold: float = 2.0  # 2x increase triggers alert
    error_rate_threshold: float = 0.1  # 10% error rate triggers alert
    drift_threshold: float = 0.1
    
    # Model lifecycle settings
    auto_deprecation_enabled: bool = True
    deprecated_model_retention_days: int = 30
    failed_model_cleanup_days: int = 7
    
    # Monitoring intervals
    health_check_interval_minutes: int = 60
    ab_test_analysis_interval_minutes: int = 30
    performance_analysis_interval_hours: int = 2
    
    # Retraining settings
    auto_retraining_enabled: bool = True
    retraining_drift_threshold: float = 0.15
    retraining_performance_threshold: float = 0.1
    
    # Model validation settings
    validation_required: bool = True
    staging_required: bool = True
    production_approval_required: bool = True
    
    # Backup and recovery
    model_backup_enabled: bool = True
    backup_retention_days: int = 90
    
    # Compliance and audit
    audit_logging_enabled: bool = True
    bias_detection_enabled: bool = True
    explainability_required: bool = False
    
    # Resource limits
    max_concurrent_ab_tests: int = 5
    max_models_per_type: int = 10
    max_performance_history_days: int = 30


@dataclass
class ModelTypeConfig:
    """Configuration specific to model types."""
    
    # Model-specific thresholds
    accuracy_threshold: float = 0.8
    precision_threshold: float = 0.75
    recall_threshold: float = 0.75
    f1_threshold: float = 0.75
    
    # Drift detection settings
    feature_importance_threshold: float = 0.1
    statistical_tests: List[str] = None
    
    # Performance requirements
    max_latency_ms: float = 1000.0
    max_memory_mb: float = 512.0
    
    # Validation requirements
    min_validation_samples: int = 1000
    cross_validation_folds: int = 5
    
    def __post_init__(self):
        if self.statistical_tests is None:
            self.statistical_tests = ["ks_test", "chi2_test", "psi"]


# Default configurations for different model types
MODEL_TYPE_CONFIGS = {
    "sentiment_analysis": ModelTypeConfig(
        accuracy_threshold=0.85,
        precision_threshold=0.80,
        recall_threshold=0.80,
        f1_threshold=0.82,
        max_latency_ms=500.0,
        max_memory_mb=256.0
    ),
    "bot_detection": ModelTypeConfig(
        accuracy_threshold=0.90,
        precision_threshold=0.85,
        recall_threshold=0.88,
        f1_threshold=0.86,
        max_latency_ms=1000.0,
        max_memory_mb=512.0
    ),
    "campaign_detection": ModelTypeConfig(
        accuracy_threshold=0.88,
        precision_threshold=0.82,
        recall_threshold=0.85,
        f1_threshold=0.83,
        max_latency_ms=2000.0,
        max_memory_mb=1024.0
    ),
    "language_detection": ModelTypeConfig(
        accuracy_threshold=0.95,
        precision_threshold=0.92,
        recall_threshold=0.92,
        f1_threshold=0.92,
        max_latency_ms=200.0,
        max_memory_mb=128.0
    )
}


@dataclass
class AlertConfig:
    """Configuration for alerting system."""
    
    # Alert channels
    email_enabled: bool = True
    slack_enabled: bool = False
    webhook_enabled: bool = False
    dashboard_enabled: bool = True
    
    # Alert thresholds by severity
    critical_thresholds: Dict[str, float] = None
    high_thresholds: Dict[str, float] = None
    medium_thresholds: Dict[str, float] = None
    low_thresholds: Dict[str, float] = None
    
    # Alert frequency limits
    max_alerts_per_hour: int = 10
    alert_cooldown_minutes: int = 30
    
    # Escalation settings
    escalation_enabled: bool = True
    escalation_delay_minutes: int = 60
    
    def __post_init__(self):
        if self.critical_thresholds is None:
            self.critical_thresholds = {
                "accuracy_drop": 0.10,
                "error_rate": 0.20,
                "latency_increase": 5.0,
                "drift_score": 0.25
            }
        
        if self.high_thresholds is None:
            self.high_thresholds = {
                "accuracy_drop": 0.07,
                "error_rate": 0.15,
                "latency_increase": 3.0,
                "drift_score": 0.20
            }
        
        if self.medium_thresholds is None:
            self.medium_thresholds = {
                "accuracy_drop": 0.05,
                "error_rate": 0.10,
                "latency_increase": 2.0,
                "drift_score": 0.15
            }
        
        if self.low_thresholds is None:
            self.low_thresholds = {
                "accuracy_drop": 0.03,
                "error_rate": 0.05,
                "latency_increase": 1.5,
                "drift_score": 0.10
            }


@dataclass
class ComplianceConfig:
    """Configuration for compliance and governance requirements."""
    
    # Data governance
    data_lineage_tracking: bool = True
    data_retention_days: int = 365
    data_anonymization_required: bool = True
    
    # Model governance
    model_approval_workflow: bool = True
    model_documentation_required: bool = True
    model_testing_required: bool = True
    
    # Bias and fairness
    bias_testing_enabled: bool = True
    fairness_metrics_required: bool = True
    protected_attributes: List[str] = None
    
    # Explainability
    explainability_required: bool = False
    explanation_methods: List[str] = None
    
    # Audit requirements
    audit_trail_retention_days: int = 2555  # 7 years
    change_approval_required: bool = True
    
    def __post_init__(self):
        if self.protected_attributes is None:
            self.protected_attributes = ["gender", "age", "ethnicity", "religion"]
        
        if self.explanation_methods is None:
            self.explanation_methods = ["lime", "shap", "permutation_importance"]


def load_governance_config(config_path: Optional[str] = None) -> ModelGovernanceConfig:
    """Load governance configuration from file or use defaults."""
    import os
    import json
    
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Create config object from loaded data
        return ModelGovernanceConfig(**config_data)
    
    # Return default configuration
    return ModelGovernanceConfig()


def get_model_type_config(model_type: str) -> ModelTypeConfig:
    """Get configuration for specific model type."""
    return MODEL_TYPE_CONFIGS.get(model_type, ModelTypeConfig())


def create_default_config_file(config_path: str):
    """Create default configuration file."""
    import json
    from dataclasses import asdict
    
    config = ModelGovernanceConfig()
    config_dict = asdict(config)
    
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    print(f"Created default configuration file at {config_path}")


if __name__ == "__main__":
    # Create sample configuration file
    create_default_config_file("governance_config.json")
    
    # Test loading configuration
    config = load_governance_config("governance_config.json")
    print(f"Loaded configuration: {config}")
    
    # Test model type configuration
    sentiment_config = get_model_type_config("sentiment_analysis")
    print(f"Sentiment analysis config: {sentiment_config}")