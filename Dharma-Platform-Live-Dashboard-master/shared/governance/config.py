"""
Data Governance Configuration

Centralized configuration for data governance, retention, and compliance settings.
"""

from typing import Dict, List, Optional, Any
from datetime import timedelta
from dataclasses import dataclass, field
from enum import Enum
import os


class GovernanceMode(Enum):
    """Data governance operation modes"""
    STRICT = "strict"          # Strict compliance enforcement
    BALANCED = "balanced"      # Balance between compliance and usability
    PERMISSIVE = "permissive"  # Minimal compliance enforcement


@dataclass
class AnonymizationSettings:
    """Anonymization configuration settings"""
    enabled: bool = True
    preserve_structure: bool = True
    audit_trail: bool = True
    reversible: bool = False
    default_replacement_text: str = "[REDACTED]"
    pseudonym_salt: str = "dharma_default_salt"
    batch_size: int = 100


@dataclass
class ClassificationSettings:
    """Data classification configuration settings"""
    enabled: bool = True
    auto_classify: bool = True
    confidence_threshold: float = 0.7
    require_manual_review_threshold: float = 0.5
    update_existing_classifications: bool = False
    classification_batch_size: int = 50


@dataclass
class RetentionSettings:
    """Data retention configuration settings"""
    enabled: bool = True
    scheduler_interval: timedelta = timedelta(hours=24)
    default_retention_period: timedelta = timedelta(days=365)
    archive_location: str = "archive"
    max_batch_size: int = 1000
    dry_run_mode: bool = False


@dataclass
class ComplianceSettings:
    """Compliance monitoring configuration settings"""
    enabled: bool = True
    monitoring_interval: timedelta = timedelta(hours=12)
    generate_reports: bool = True
    alert_on_violations: bool = True
    supported_regulations: List[str] = field(default_factory=lambda: [
        "gdpr", "ccpa", "data_retention", "security_standards"
    ])


@dataclass
class DatabaseSettings:
    """Database configuration for governance"""
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "dharma_platform"
    postgresql_uri: str = "postgresql://localhost:5432/dharma"
    elasticsearch_uri: str = "http://localhost:9200"
    redis_uri: str = "redis://localhost:6379"


@dataclass
class SecuritySettings:
    """Security configuration for governance"""
    encryption_enabled: bool = True
    encryption_key_rotation_days: int = 90
    audit_all_access: bool = True
    require_approval_for_sensitive: bool = True
    max_failed_attempts: int = 3
    session_timeout_minutes: int = 30


@dataclass
class NotificationSettings:
    """Notification configuration for governance events"""
    enabled: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    webhook_notifications: bool = True
    notification_channels: Dict[str, str] = field(default_factory=dict)


class GovernanceConfig:
    """
    Centralized configuration manager for data governance system
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.mode = GovernanceMode.BALANCED
        
        # Initialize settings with defaults
        self.anonymization = AnonymizationSettings()
        self.classification = ClassificationSettings()
        self.retention = RetentionSettings()
        self.compliance = ComplianceSettings()
        self.database = DatabaseSettings()
        self.security = SecuritySettings()
        self.notifications = NotificationSettings()
        
        # Load configuration from environment or file
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from environment variables or config file"""
        # Load from environment variables
        self._load_from_environment()
        
        # Load from config file if provided
        if self.config_file and os.path.exists(self.config_file):
            self._load_from_file()
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # Governance mode
        mode_str = os.getenv('DHARMA_GOVERNANCE_MODE', 'balanced').lower()
        if mode_str in [m.value for m in GovernanceMode]:
            self.mode = GovernanceMode(mode_str)
        
        # Anonymization settings
        self.anonymization.enabled = os.getenv('DHARMA_ANONYMIZATION_ENABLED', 'true').lower() == 'true'
        self.anonymization.preserve_structure = os.getenv('DHARMA_PRESERVE_STRUCTURE', 'true').lower() == 'true'
        self.anonymization.audit_trail = os.getenv('DHARMA_AUDIT_TRAIL', 'true').lower() == 'true'
        self.anonymization.pseudonym_salt = os.getenv('DHARMA_PSEUDONYM_SALT', self.anonymization.pseudonym_salt)
        
        # Classification settings
        self.classification.enabled = os.getenv('DHARMA_CLASSIFICATION_ENABLED', 'true').lower() == 'true'
        self.classification.auto_classify = os.getenv('DHARMA_AUTO_CLASSIFY', 'true').lower() == 'true'
        confidence_threshold = os.getenv('DHARMA_CONFIDENCE_THRESHOLD')
        if confidence_threshold:
            self.classification.confidence_threshold = float(confidence_threshold)
        
        # Retention settings
        self.retention.enabled = os.getenv('DHARMA_RETENTION_ENABLED', 'true').lower() == 'true'
        retention_hours = os.getenv('DHARMA_RETENTION_INTERVAL_HOURS')
        if retention_hours:
            self.retention.scheduler_interval = timedelta(hours=int(retention_hours))
        
        # Database settings
        self.database.mongodb_uri = os.getenv('DHARMA_MONGODB_URI', self.database.mongodb_uri)
        self.database.postgresql_uri = os.getenv('DHARMA_POSTGRESQL_URI', self.database.postgresql_uri)
        self.database.elasticsearch_uri = os.getenv('DHARMA_ELASTICSEARCH_URI', self.database.elasticsearch_uri)
        self.database.redis_uri = os.getenv('DHARMA_REDIS_URI', self.database.redis_uri)
        
        # Security settings
        self.security.encryption_enabled = os.getenv('DHARMA_ENCRYPTION_ENABLED', 'true').lower() == 'true'
        self.security.audit_all_access = os.getenv('DHARMA_AUDIT_ALL_ACCESS', 'true').lower() == 'true'
        
        # Notification settings
        self.notifications.enabled = os.getenv('DHARMA_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        self.notifications.email_notifications = os.getenv('DHARMA_EMAIL_NOTIFICATIONS', 'true').lower() == 'true'
    
    def _load_from_file(self):
        """Load configuration from JSON/YAML file"""
        import json
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update settings from file
            if 'anonymization' in config_data:
                self._update_dataclass(self.anonymization, config_data['anonymization'])
            
            if 'classification' in config_data:
                self._update_dataclass(self.classification, config_data['classification'])
            
            if 'retention' in config_data:
                self._update_dataclass(self.retention, config_data['retention'])
            
            if 'compliance' in config_data:
                self._update_dataclass(self.compliance, config_data['compliance'])
            
            if 'database' in config_data:
                self._update_dataclass(self.database, config_data['database'])
            
            if 'security' in config_data:
                self._update_dataclass(self.security, config_data['security'])
            
            if 'notifications' in config_data:
                self._update_dataclass(self.notifications, config_data['notifications'])
                
        except Exception as e:
            print(f"Warning: Could not load config file {self.config_file}: {e}")
    
    def _update_dataclass(self, dataclass_instance, config_dict):
        """Update dataclass instance with values from config dictionary"""
        for key, value in config_dict.items():
            if hasattr(dataclass_instance, key):
                # Handle timedelta conversion
                if key.endswith('_interval') or key.endswith('_period'):
                    if isinstance(value, dict) and 'days' in value:
                        value = timedelta(**value)
                    elif isinstance(value, int):
                        value = timedelta(days=value)
                
                setattr(dataclass_instance, key, value)
    
    def get_mode_specific_settings(self) -> Dict[str, Any]:
        """Get settings adjusted for the current governance mode"""
        settings = {}
        
        if self.mode == GovernanceMode.STRICT:
            settings.update({
                'classification_confidence_threshold': 0.9,
                'require_manual_review': True,
                'audit_all_operations': True,
                'encryption_required': True,
                'retention_enforcement': 'strict'
            })
        elif self.mode == GovernanceMode.BALANCED:
            settings.update({
                'classification_confidence_threshold': 0.7,
                'require_manual_review': False,
                'audit_all_operations': True,
                'encryption_required': True,
                'retention_enforcement': 'balanced'
            })
        elif self.mode == GovernanceMode.PERMISSIVE:
            settings.update({
                'classification_confidence_threshold': 0.5,
                'require_manual_review': False,
                'audit_all_operations': False,
                'encryption_required': False,
                'retention_enforcement': 'permissive'
            })
        
        return settings
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate database URIs
        if not self.database.mongodb_uri:
            issues.append("MongoDB URI is required")
        
        if not self.database.postgresql_uri:
            issues.append("PostgreSQL URI is required")
        
        # Validate thresholds
        if not 0 <= self.classification.confidence_threshold <= 1:
            issues.append("Classification confidence threshold must be between 0 and 1")
        
        if not 0 <= self.classification.require_manual_review_threshold <= 1:
            issues.append("Manual review threshold must be between 0 and 1")
        
        # Validate retention settings
        if self.retention.scheduler_interval.total_seconds() < 3600:
            issues.append("Retention scheduler interval should be at least 1 hour")
        
        # Validate security settings
        if self.security.encryption_key_rotation_days < 30:
            issues.append("Encryption key rotation should be at least 30 days")
        
        return issues
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration as dictionary"""
        return {
            'mode': self.mode.value,
            'anonymization': {
                'enabled': self.anonymization.enabled,
                'preserve_structure': self.anonymization.preserve_structure,
                'audit_trail': self.anonymization.audit_trail,
                'reversible': self.anonymization.reversible,
                'batch_size': self.anonymization.batch_size
            },
            'classification': {
                'enabled': self.classification.enabled,
                'auto_classify': self.classification.auto_classify,
                'confidence_threshold': self.classification.confidence_threshold,
                'require_manual_review_threshold': self.classification.require_manual_review_threshold,
                'batch_size': self.classification.classification_batch_size
            },
            'retention': {
                'enabled': self.retention.enabled,
                'scheduler_interval': {'days': self.retention.scheduler_interval.days},
                'default_retention_period': {'days': self.retention.default_retention_period.days},
                'max_batch_size': self.retention.max_batch_size,
                'dry_run_mode': self.retention.dry_run_mode
            },
            'compliance': {
                'enabled': self.compliance.enabled,
                'monitoring_interval': {'hours': self.compliance.monitoring_interval.total_seconds() // 3600},
                'generate_reports': self.compliance.generate_reports,
                'alert_on_violations': self.compliance.alert_on_violations,
                'supported_regulations': self.compliance.supported_regulations
            },
            'security': {
                'encryption_enabled': self.security.encryption_enabled,
                'audit_all_access': self.security.audit_all_access,
                'require_approval_for_sensitive': self.security.require_approval_for_sensitive,
                'session_timeout_minutes': self.security.session_timeout_minutes
            },
            'notifications': {
                'enabled': self.notifications.enabled,
                'email_notifications': self.notifications.email_notifications,
                'sms_notifications': self.notifications.sms_notifications,
                'webhook_notifications': self.notifications.webhook_notifications
            }
        }
    
    def save_configuration(self, file_path: str):
        """Save current configuration to file"""
        import json
        
        config_data = self.export_configuration()
        
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    @classmethod
    def create_default_config_file(cls, file_path: str):
        """Create a default configuration file"""
        config = cls()
        config.save_configuration(file_path)
    
    def __str__(self) -> str:
        """String representation of configuration"""
        return f"GovernanceConfig(mode={self.mode.value}, " \
               f"anonymization_enabled={self.anonymization.enabled}, " \
               f"classification_enabled={self.classification.enabled}, " \
               f"retention_enabled={self.retention.enabled})"


# Global configuration instance
_config_instance = None


def get_governance_config(config_file: Optional[str] = None) -> GovernanceConfig:
    """Get global governance configuration instance"""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = GovernanceConfig(config_file)
    
    return _config_instance


def set_governance_config(config: GovernanceConfig):
    """Set global governance configuration instance"""
    global _config_instance
    _config_instance = config


# Configuration presets for different environments
DEVELOPMENT_CONFIG = {
    'mode': 'permissive',
    'anonymization': {'enabled': True, 'audit_trail': True},
    'classification': {'enabled': True, 'confidence_threshold': 0.5},
    'retention': {'enabled': False, 'dry_run_mode': True},
    'compliance': {'enabled': True, 'alert_on_violations': False}
}

STAGING_CONFIG = {
    'mode': 'balanced',
    'anonymization': {'enabled': True, 'audit_trail': True},
    'classification': {'enabled': True, 'confidence_threshold': 0.7},
    'retention': {'enabled': True, 'dry_run_mode': True},
    'compliance': {'enabled': True, 'alert_on_violations': True}
}

PRODUCTION_CONFIG = {
    'mode': 'strict',
    'anonymization': {'enabled': True, 'audit_trail': True, 'reversible': False},
    'classification': {'enabled': True, 'confidence_threshold': 0.9},
    'retention': {'enabled': True, 'dry_run_mode': False},
    'compliance': {'enabled': True, 'alert_on_violations': True, 'generate_reports': True},
    'security': {'encryption_enabled': True, 'audit_all_access': True}
}