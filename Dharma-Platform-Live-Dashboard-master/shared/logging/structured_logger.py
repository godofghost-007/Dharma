"""
Structured logging utility for Project Dharma
Provides consistent logging format across all services with correlation IDs and structured data
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from functools import wraps

import structlog
from pythonjsonlogger import jsonlogger


# Context variables for distributed tracing
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class CorrelationIdProcessor:
    """Processor to add correlation ID to log records"""
    
    def __call__(self, logger, method_name, event_dict):
        correlation_id = correlation_id_var.get()
        if correlation_id:
            event_dict['correlation_id'] = correlation_id
        
        user_id = user_id_var.get()
        if user_id:
            event_dict['user_id'] = user_id
            
        request_id = request_id_var.get()
        if request_id:
            event_dict['request_id'] = request_id
            
        return event_dict


class DharmaJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for Dharma platform logs"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add service name from environment or default
        import os
        log_record['service'] = os.getenv('SERVICE_NAME', 'unknown-service')
        
        # Add environment
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')
        
        # Add hostname
        import socket
        log_record['hostname'] = socket.gethostname()
        
        # Ensure level is uppercase
        if 'levelname' in log_record:
            log_record['level'] = log_record['levelname'].upper()
            del log_record['levelname']


class StructuredLogger:
    """Main structured logger class for Dharma platform"""
    
    def __init__(self, service_name: str, log_level: str = "INFO"):
        self.service_name = service_name
        self.log_level = log_level
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup structured logging configuration"""
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                CorrelationIdProcessor(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(DharmaJSONFormatter(
            '%(timestamp)s %(service)s %(level)s %(name)s %(message)s'
        ))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Set service name in environment for formatter
        import os
        os.environ['SERVICE_NAME'] = self.service_name
    
    def get_logger(self, name: str = None) -> structlog.BoundLogger:
        """Get a structured logger instance"""
        logger_name = name or self.service_name
        return structlog.get_logger(logger_name)


class LoggingContext:
    """Context manager for setting logging context variables"""
    
    def __init__(self, correlation_id: str = None, user_id: str = None, request_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.request_id = request_id or str(uuid.uuid4())
        
        self.correlation_token = None
        self.user_token = None
        self.request_token = None
    
    def __enter__(self):
        self.correlation_token = correlation_id_var.set(self.correlation_id)
        if self.user_id:
            self.user_token = user_id_var.set(self.user_id)
        self.request_token = request_id_var.set(self.request_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        correlation_id_var.reset(self.correlation_token)
        if self.user_token:
            user_id_var.reset(self.user_token)
        request_id_var.reset(self.request_token)


def with_logging_context(correlation_id: str = None, user_id: str = None):
    """Decorator to add logging context to functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with LoggingContext(correlation_id=correlation_id, user_id=user_id):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with LoggingContext(correlation_id=correlation_id, user_id=user_id):
                return func(*args, **kwargs)
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    return decorator


class BusinessMetricsLogger:
    """Logger for business metrics and KPIs"""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
    
    def log_posts_processed(self, count: int, platform: str, processing_time_ms: float):
        """Log posts processing metrics"""
        self.logger.info(
            "posts_processed",
            business_metrics={
                "posts_processed": count,
                "platform": platform,
                "processing_time_ms": processing_time_ms
            }
        )
    
    def log_alerts_generated(self, count: int, severity: str, alert_type: str):
        """Log alert generation metrics"""
        self.logger.info(
            "alerts_generated",
            business_metrics={
                "alerts_generated": count,
                "severity": severity,
                "alert_type": alert_type
            }
        )
    
    def log_campaigns_detected(self, count: int, coordination_score: float, participants: int):
        """Log campaign detection metrics"""
        self.logger.info(
            "campaigns_detected",
            business_metrics={
                "campaigns_detected": count,
                "coordination_score": coordination_score,
                "participants": participants
            }
        )
    
    def log_performance_metrics(self, operation: str, duration_ms: float, memory_usage: int = None):
        """Log performance metrics"""
        metrics = {
            "operation": operation,
            "duration_ms": duration_ms
        }
        if memory_usage:
            metrics["memory_usage"] = memory_usage
        
        self.logger.info(
            "performance_metrics",
            performance=metrics
        )


class AuditLogger:
    """Logger for audit events and security-related activities"""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
    
    def log_user_action(self, user_id: str, action: str, resource: str, result: str, details: Dict[str, Any] = None):
        """Log user actions for audit trail"""
        self.logger.info(
            "user_action",
            audit={
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "result": result,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_data_access(self, user_id: str, data_type: str, operation: str, record_count: int):
        """Log data access for compliance"""
        self.logger.info(
            "data_access",
            audit={
                "user_id": user_id,
                "data_type": data_type,
                "operation": operation,
                "record_count": record_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_security_event(self, event_type: str, severity: str, details: Dict[str, Any]):
        """Log security events"""
        self.logger.warning(
            "security_event",
            security={
                "event_type": event_type,
                "severity": severity,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Global logger instance
_logger_instance = None

def get_logger(service_name: str = None, log_level: str = "INFO") -> structlog.BoundLogger:
    """Get global logger instance"""
    global _logger_instance
    
    if _logger_instance is None:
        import os
        service_name = service_name or os.getenv('SERVICE_NAME', 'dharma-service')
        _logger_instance = StructuredLogger(service_name, log_level)
    
    return _logger_instance.get_logger()


def get_business_metrics_logger(service_name: str = None) -> BusinessMetricsLogger:
    """Get business metrics logger"""
    logger = get_logger(service_name)
    return BusinessMetricsLogger(logger)


def get_audit_logger(service_name: str = None) -> AuditLogger:
    """Get audit logger"""
    logger = get_logger(service_name)
    return AuditLogger(logger)


# Example usage and testing
if __name__ == "__main__":
    # Initialize logger
    logger = get_logger("test-service")
    business_logger = get_business_metrics_logger("test-service")
    audit_logger = get_audit_logger("test-service")
    
    # Test basic logging
    logger.info("Service started", version="1.0.0")
    
    # Test with context
    with LoggingContext(user_id="user123"):
        logger.info("Processing user request")
        business_logger.log_posts_processed(100, "twitter", 1500.0)
        audit_logger.log_user_action("user123", "view_dashboard", "dashboard", "success")
    
    # Test error logging
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.error("Error occurred", error=str(e), exc_info=True)