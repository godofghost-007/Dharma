"""
Configuration management for distributed tracing system
Provides centralized configuration for all tracing components
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class TracingBackend(Enum):
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    OTLP = "otlp"
    CONSOLE = "console"


class SamplingStrategy(Enum):
    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITED = "rate_limited"
    PARENT_BASED = "parent_based"


@dataclass
class TracingConfig:
    """Main tracing configuration"""
    
    # Service identification
    service_name: str
    service_version: str = "1.0.0"
    service_namespace: str = "dharma"
    deployment_environment: str = "development"
    
    # Tracing backends
    enabled_backends: List[TracingBackend] = field(default_factory=lambda: [TracingBackend.JAEGER])
    
    # Jaeger configuration
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6831
    jaeger_collector_endpoint: str = "http://localhost:14268/api/traces"
    
    # Zipkin configuration
    zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"
    
    # OTLP configuration
    otlp_endpoint: str = "http://localhost:4317"
    otlp_insecure: bool = True
    otlp_headers: Dict[str, str] = field(default_factory=dict)
    
    # Sampling configuration
    sampling_strategy: SamplingStrategy = SamplingStrategy.ALWAYS_ON
    sampling_rate: float = 1.0  # For probabilistic sampling
    sampling_rate_limit: int = 100  # For rate limited sampling
    
    # Resource attributes
    resource_attributes: Dict[str, str] = field(default_factory=dict)
    
    # Instrumentation configuration
    enable_auto_instrumentation: bool = True
    enable_console_export: bool = False
    enable_logging_export: bool = False
    
    # Performance settings
    batch_span_processor_max_queue_size: int = 2048
    batch_span_processor_schedule_delay_millis: int = 5000
    batch_span_processor_export_timeout_millis: int = 30000
    batch_span_processor_max_export_batch_size: int = 512
    
    # Memory settings
    memory_limit_mib: int = 512
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Set default resource attributes
        default_attributes = {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "service.namespace": self.service_namespace,
            "deployment.environment": self.deployment_environment,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python"
        }
        
        # Merge with provided attributes
        self.resource_attributes = {**default_attributes, **self.resource_attributes}


@dataclass
class CorrelationConfig:
    """Correlation ID configuration"""
    
    # Redis configuration for correlation storage
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ssl: bool = False
    
    # Correlation storage settings
    correlation_ttl_seconds: int = 3600  # 1 hour
    request_chain_ttl_seconds: int = 3600  # 1 hour
    max_chain_length: int = 100
    
    # Header names for correlation propagation
    correlation_id_header: str = "X-Correlation-ID"
    request_id_header: str = "X-Request-ID"
    user_id_header: str = "X-User-ID"
    session_id_header: str = "X-Session-ID"
    trace_id_header: str = "X-Trace-ID"
    span_id_header: str = "X-Span-ID"
    baggage_header: str = "X-Baggage"
    
    # Correlation ID generation settings
    correlation_id_length: int = 32
    request_id_prefix: str = "req_"


@dataclass
class ErrorTrackingConfig:
    """Error tracking configuration"""
    
    # Storage backends
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index_prefix: str = "dharma-errors"
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 1
    
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "dharma-errors"
    
    # Error aggregation settings
    aggregation_time_window_minutes: int = 5
    max_error_groups: int = 10000
    error_retention_days: int = 30
    
    # Alert thresholds
    high_error_rate_threshold: float = 0.1  # 10%
    critical_error_rate_threshold: float = 0.25  # 25%
    error_rate_window_minutes: int = 5
    
    # Error classification
    default_severity: str = "medium"
    default_category: str = "application"
    
    # Fingerprint settings
    max_stack_trace_lines: int = 10
    include_line_numbers_in_fingerprint: bool = False


@dataclass
class PerformanceProfilingConfig:
    """Performance profiling configuration"""
    
    # Storage configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 2
    
    # Profiling settings
    enable_cprofile: bool = False
    enable_system_monitoring: bool = True
    system_monitoring_interval_seconds: float = 1.0
    
    # Performance thresholds
    cpu_high_threshold: float = 80.0
    cpu_critical_threshold: float = 95.0
    memory_high_threshold: float = 80.0
    memory_critical_threshold: float = 95.0
    duration_slow_threshold: float = 1.0
    duration_very_slow_threshold: float = 5.0
    duration_critical_threshold: float = 10.0
    
    # Data retention
    max_performance_data_points: int = 10000
    max_bottleneck_records: int = 1000
    performance_data_ttl_seconds: int = 86400  # 24 hours
    
    # Bottleneck detection
    enable_bottleneck_detection: bool = True
    bottleneck_detection_interval_seconds: int = 60
    
    # Profiling data collection
    collect_function_profiles: bool = True
    max_profile_functions: int = 20
    profile_output_max_length: int = 2000


@dataclass
class IntegrationConfig:
    """Integration configuration for various components"""
    
    # HTTP client settings
    http_client_timeout_seconds: int = 30
    http_client_max_retries: int = 3
    http_client_retry_delay_seconds: float = 1.0
    
    # Kafka settings
    kafka_producer_batch_size: int = 16384
    kafka_producer_linger_ms: int = 10
    kafka_producer_compression_type: str = "gzip"
    
    # Database operation settings
    db_operation_timeout_seconds: int = 30
    db_slow_query_threshold_seconds: float = 1.0
    
    # AI/ML operation settings
    ai_operation_timeout_seconds: int = 300
    ai_slow_inference_threshold_seconds: float = 5.0
    
    # Middleware settings
    enable_request_logging: bool = True
    enable_response_logging: bool = False
    log_request_body: bool = False
    log_response_body: bool = False
    max_log_body_size: int = 1024


class ConfigManager:
    """Configuration manager for distributed tracing"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self._tracing_config = None
        self._correlation_config = None
        self._error_tracking_config = None
        self._performance_config = None
        self._integration_config = None
    
    def get_tracing_config(self, service_name: str) -> TracingConfig:
        """Get tracing configuration"""
        if self._tracing_config is None:
            self._tracing_config = self._load_tracing_config(service_name)
        return self._tracing_config
    
    def get_correlation_config(self) -> CorrelationConfig:
        """Get correlation configuration"""
        if self._correlation_config is None:
            self._correlation_config = self._load_correlation_config()
        return self._correlation_config
    
    def get_error_tracking_config(self) -> ErrorTrackingConfig:
        """Get error tracking configuration"""
        if self._error_tracking_config is None:
            self._error_tracking_config = self._load_error_tracking_config()
        return self._error_tracking_config
    
    def get_performance_config(self) -> PerformanceProfilingConfig:
        """Get performance profiling configuration"""
        if self._performance_config is None:
            self._performance_config = self._load_performance_config()
        return self._performance_config
    
    def get_integration_config(self) -> IntegrationConfig:
        """Get integration configuration"""
        if self._integration_config is None:
            self._integration_config = self._load_integration_config()
        return self._integration_config
    
    def _load_tracing_config(self, service_name: str) -> TracingConfig:
        """Load tracing configuration from environment"""
        return TracingConfig(
            service_name=service_name,
            service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
            service_namespace=os.getenv("SERVICE_NAMESPACE", "dharma"),
            deployment_environment=os.getenv("ENVIRONMENT", "development"),
            
            # Jaeger settings
            jaeger_endpoint=os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces"),
            jaeger_agent_host=os.getenv("JAEGER_AGENT_HOST", "localhost"),
            jaeger_agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
            
            # Zipkin settings
            zipkin_endpoint=os.getenv("ZIPKIN_ENDPOINT", "http://localhost:9411/api/v2/spans"),
            
            # OTLP settings
            otlp_endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4317"),
            otlp_insecure=os.getenv("OTLP_INSECURE", "true").lower() == "true",
            
            # Sampling settings
            sampling_strategy=SamplingStrategy(os.getenv("SAMPLING_STRATEGY", "always_on")),
            sampling_rate=float(os.getenv("SAMPLING_RATE", "1.0")),
            
            # Feature flags
            enable_auto_instrumentation=os.getenv("ENABLE_AUTO_INSTRUMENTATION", "true").lower() == "true",
            enable_console_export=os.getenv("ENABLE_CONSOLE_EXPORT", "false").lower() == "true",
            enable_logging_export=os.getenv("ENABLE_LOGGING_EXPORT", "false").lower() == "true",
            
            # Performance settings
            batch_span_processor_max_queue_size=int(os.getenv("BATCH_SPAN_PROCESSOR_MAX_QUEUE_SIZE", "2048")),
            batch_span_processor_schedule_delay_millis=int(os.getenv("BATCH_SPAN_PROCESSOR_SCHEDULE_DELAY_MILLIS", "5000")),
            memory_limit_mib=int(os.getenv("MEMORY_LIMIT_MIB", "512"))
        )
    
    def _load_correlation_config(self) -> CorrelationConfig:
        """Load correlation configuration from environment"""
        return CorrelationConfig(
            redis_url=os.getenv("CORRELATION_REDIS_URL", "redis://localhost:6379"),
            redis_db=int(os.getenv("CORRELATION_REDIS_DB", "0")),
            redis_password=os.getenv("CORRELATION_REDIS_PASSWORD"),
            redis_ssl=os.getenv("CORRELATION_REDIS_SSL", "false").lower() == "true",
            
            correlation_ttl_seconds=int(os.getenv("CORRELATION_TTL_SECONDS", "3600")),
            request_chain_ttl_seconds=int(os.getenv("REQUEST_CHAIN_TTL_SECONDS", "3600")),
            max_chain_length=int(os.getenv("MAX_CHAIN_LENGTH", "100"))
        )
    
    def _load_error_tracking_config(self) -> ErrorTrackingConfig:
        """Load error tracking configuration from environment"""
        return ErrorTrackingConfig(
            elasticsearch_url=os.getenv("ERROR_ELASTICSEARCH_URL", "http://localhost:9200"),
            elasticsearch_index_prefix=os.getenv("ERROR_ELASTICSEARCH_INDEX_PREFIX", "dharma-errors"),
            elasticsearch_username=os.getenv("ERROR_ELASTICSEARCH_USERNAME"),
            elasticsearch_password=os.getenv("ERROR_ELASTICSEARCH_PASSWORD"),
            
            redis_url=os.getenv("ERROR_REDIS_URL", "redis://localhost:6379"),
            redis_db=int(os.getenv("ERROR_REDIS_DB", "1")),
            
            kafka_bootstrap_servers=os.getenv("ERROR_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            kafka_topic=os.getenv("ERROR_KAFKA_TOPIC", "dharma-errors"),
            
            aggregation_time_window_minutes=int(os.getenv("ERROR_AGGREGATION_TIME_WINDOW_MINUTES", "5")),
            high_error_rate_threshold=float(os.getenv("HIGH_ERROR_RATE_THRESHOLD", "0.1")),
            critical_error_rate_threshold=float(os.getenv("CRITICAL_ERROR_RATE_THRESHOLD", "0.25"))
        )
    
    def _load_performance_config(self) -> PerformanceProfilingConfig:
        """Load performance profiling configuration from environment"""
        return PerformanceProfilingConfig(
            redis_url=os.getenv("PERFORMANCE_REDIS_URL", "redis://localhost:6379"),
            redis_db=int(os.getenv("PERFORMANCE_REDIS_DB", "2")),
            
            enable_cprofile=os.getenv("ENABLE_CPROFILE", "false").lower() == "true",
            enable_system_monitoring=os.getenv("ENABLE_SYSTEM_MONITORING", "true").lower() == "true",
            system_monitoring_interval_seconds=float(os.getenv("SYSTEM_MONITORING_INTERVAL_SECONDS", "1.0")),
            
            cpu_high_threshold=float(os.getenv("CPU_HIGH_THRESHOLD", "80.0")),
            cpu_critical_threshold=float(os.getenv("CPU_CRITICAL_THRESHOLD", "95.0")),
            memory_high_threshold=float(os.getenv("MEMORY_HIGH_THRESHOLD", "80.0")),
            memory_critical_threshold=float(os.getenv("MEMORY_CRITICAL_THRESHOLD", "95.0")),
            
            duration_slow_threshold=float(os.getenv("DURATION_SLOW_THRESHOLD", "1.0")),
            duration_very_slow_threshold=float(os.getenv("DURATION_VERY_SLOW_THRESHOLD", "5.0")),
            duration_critical_threshold=float(os.getenv("DURATION_CRITICAL_THRESHOLD", "10.0"))
        )
    
    def _load_integration_config(self) -> IntegrationConfig:
        """Load integration configuration from environment"""
        return IntegrationConfig(
            http_client_timeout_seconds=int(os.getenv("HTTP_CLIENT_TIMEOUT_SECONDS", "30")),
            http_client_max_retries=int(os.getenv("HTTP_CLIENT_MAX_RETRIES", "3")),
            
            kafka_producer_batch_size=int(os.getenv("KAFKA_PRODUCER_BATCH_SIZE", "16384")),
            kafka_producer_linger_ms=int(os.getenv("KAFKA_PRODUCER_LINGER_MS", "10")),
            
            db_operation_timeout_seconds=int(os.getenv("DB_OPERATION_TIMEOUT_SECONDS", "30")),
            db_slow_query_threshold_seconds=float(os.getenv("DB_SLOW_QUERY_THRESHOLD_SECONDS", "1.0")),
            
            ai_operation_timeout_seconds=int(os.getenv("AI_OPERATION_TIMEOUT_SECONDS", "300")),
            ai_slow_inference_threshold_seconds=float(os.getenv("AI_SLOW_INFERENCE_THRESHOLD_SECONDS", "5.0")),
            
            enable_request_logging=os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true",
            enable_response_logging=os.getenv("ENABLE_RESPONSE_LOGGING", "false").lower() == "true",
            log_request_body=os.getenv("LOG_REQUEST_BODY", "false").lower() == "true",
            log_response_body=os.getenv("LOG_RESPONSE_BODY", "false").lower() == "true"
        )


# Global configuration manager instance
_config_manager = None

def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    
    return _config_manager


def get_tracing_config(service_name: str) -> TracingConfig:
    """Get tracing configuration for service"""
    return get_config_manager().get_tracing_config(service_name)


def get_correlation_config() -> CorrelationConfig:
    """Get correlation configuration"""
    return get_config_manager().get_correlation_config()


def get_error_tracking_config() -> ErrorTrackingConfig:
    """Get error tracking configuration"""
    return get_config_manager().get_error_tracking_config()


def get_performance_config() -> PerformanceProfilingConfig:
    """Get performance profiling configuration"""
    return get_config_manager().get_performance_config()


def get_integration_config() -> IntegrationConfig:
    """Get integration configuration"""
    return get_config_manager().get_integration_config()


# Example usage and testing
if __name__ == "__main__":
    # Test configuration loading
    config_manager = get_config_manager()
    
    tracing_config = config_manager.get_tracing_config("test-service")
    print(f"Tracing config: {tracing_config}")
    
    correlation_config = config_manager.get_correlation_config()
    print(f"Correlation config: {correlation_config}")
    
    error_config = config_manager.get_error_tracking_config()
    print(f"Error tracking config: {error_config}")
    
    performance_config = config_manager.get_performance_config()
    print(f"Performance config: {performance_config}")
    
    integration_config = config_manager.get_integration_config()
    print(f"Integration config: {integration_config}")
    
    print("Configuration loading test completed")