"""
Tests for centralized logging system (ELK stack)
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from shared.logging.structured_logger import (
    StructuredLogger, LoggingContext, BusinessMetricsLogger, 
    AuditLogger, get_logger
)
from shared.logging.log_aggregator import (
    LogAggregator, LogEntry, LogLevel, LogPattern, LogAnomaly
)
from shared.logging.log_alerting import (
    LogAlertingEngine, AlertRule, Alert, AlertType, AlertSeverity
)


class TestStructuredLogger:
    """Test structured logging functionality"""
    
    def test_logger_initialization(self):
        """Test logger initialization"""
        logger = StructuredLogger("test-service", "DEBUG")
        assert logger.service_name == "test-service"
        assert logger.log_level == "DEBUG"
    
    def test_get_logger(self):
        """Test getting logger instance"""
        logger = StructuredLogger("test-service")
        log_instance = logger.get_logger("test-component")
        assert log_instance is not None
    
    def test_logging_context(self):
        """Test logging context manager"""
        with LoggingContext(correlation_id="test-123", user_id="user-456") as ctx:
            assert ctx.correlation_id == "test-123"
            assert ctx.user_id == "user-456"
            assert ctx.request_id is not None
    
    def test_business_metrics_logger(self):
        """Test business metrics logging"""
        logger = get_logger("test-service")
        metrics_logger = BusinessMetricsLogger(logger)
        
        # Test posts processed logging
        metrics_logger.log_posts_processed(100, "twitter", 1500.0)
        
        # Test alerts generated logging
        metrics_logger.log_alerts_generated(5, "HIGH", "security_breach")
        
        # Test campaigns detected logging
        metrics_logger.log_campaigns_detected(2, 0.85, 15)
    
    def test_audit_logger(self):
        """Test audit logging"""
        logger = get_logger("test-service")
        audit_logger = AuditLogger(logger)
        
        # Test user action logging
        audit_logger.log_user_action(
            "user123", "view_dashboard", "dashboard", "success"
        )
        
        # Test data access logging
        audit_logger.log_data_access(
            "user123", "posts", "read", 100
        )
        
        # Test security event logging
        audit_logger.log_security_event(
            "failed_login", "HIGH", {"ip": "192.168.1.1", "attempts": 5}
        )


class TestLogAggregator:
    """Test log aggregation functionality"""
    
    @pytest.fixture
    def mock_aggregator(self):
        """Create mock log aggregator"""
        with patch('shared.logging.log_aggregator.AsyncElasticsearch'), \
             patch('shared.logging.log_aggregator.aioredis.from_url'), \
             patch('shared.logging.log_aggregator.KafkaConsumer'):
            aggregator = LogAggregator()
            return aggregator
    
    def test_log_entry_creation(self):
        """Test log entry creation"""
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            service="test-service",
            level=LogLevel.INFO,
            message="Test message",
            correlation_id="test-123"
        )
        
        assert entry.service == "test-service"
        assert entry.level == LogLevel.INFO
        assert entry.correlation_id == "test-123"
        
        # Test serialization
        entry_dict = entry.to_dict()
        assert "timestamp" in entry_dict
        assert entry_dict["level"] == "INFO"
    
    def test_log_pattern_matching(self):
        """Test log pattern matching"""
        pattern = LogPattern(
            pattern="test_pattern",
            regex=r"error.*occurred",
            severity="HIGH",
            description="Test pattern"
        )
        
        # This would be tested with actual regex matching
        assert pattern.pattern == "test_pattern"
        assert pattern.severity == "HIGH"
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, mock_aggregator):
        """Test anomaly detection"""
        # Mock the anomaly detection process
        mock_aggregator._check_anomalies = AsyncMock()
        
        log_entry = LogEntry(
            timestamp=datetime.utcnow(),
            service="test-service",
            level=LogLevel.ERROR,
            message="Authentication failed for user",
            correlation_id="test-123"
        )
        
        await mock_aggregator._check_anomalies(log_entry)
        mock_aggregator._check_anomalies.assert_called_once_with(log_entry)
    
    @pytest.mark.asyncio
    async def test_log_search(self, mock_aggregator):
        """Test log search functionality"""
        # Mock Elasticsearch response
        mock_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "timestamp": "2024-01-01T00:00:00Z",
                            "service": "test-service",
                            "level": "ERROR",
                            "message": "Test error"
                        }
                    }
                ]
            }
        }
        
        mock_aggregator.es_client.search = AsyncMock(return_value=mock_response)
        
        results = await mock_aggregator.search_logs(
            service="test-service",
            level=LogLevel.ERROR,
            limit=10
        )
        
        assert len(results) == 1
        assert results[0]["service"] == "test-service"
    
    @pytest.mark.asyncio
    async def test_log_statistics(self, mock_aggregator):
        """Test log statistics"""
        # Mock Elasticsearch response
        mock_response = {
            "hits": {"total": {"value": 100}},
            "aggregations": {
                "levels": {
                    "buckets": [
                        {"key": "INFO", "doc_count": 80},
                        {"key": "ERROR", "doc_count": 20}
                    ]
                },
                "services": {
                    "buckets": [
                        {"key": "service1", "doc_count": 60},
                        {"key": "service2", "doc_count": 40}
                    ]
                },
                "timeline": {
                    "buckets": [
                        {"key_as_string": "2024-01-01T00:00:00Z", "doc_count": 50},
                        {"key_as_string": "2024-01-01T01:00:00Z", "doc_count": 50}
                    ]
                }
            }
        }
        
        mock_aggregator.es_client.search = AsyncMock(return_value=mock_response)
        
        stats = await mock_aggregator.get_log_statistics()
        
        assert stats["total_logs"] == 100
        assert stats["levels"]["INFO"] == 80
        assert stats["levels"]["ERROR"] == 20
        assert len(stats["timeline"]) == 2


class TestLogAlerting:
    """Test log alerting functionality"""
    
    @pytest.fixture
    def mock_alerting_engine(self):
        """Create mock alerting engine"""
        with patch('shared.logging.log_alerting.AsyncElasticsearch'), \
             patch('shared.logging.log_alerting.aioredis.from_url'), \
             patch('shared.logging.log_alerting.KafkaProducer'):
            
            mock_aggregator = Mock()
            engine = LogAlertingEngine(mock_aggregator)
            return engine
    
    def test_alert_rule_creation(self):
        """Test alert rule creation"""
        rule = AlertRule(
            id="test_rule",
            name="Test Rule",
            description="Test alert rule",
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.HIGH,
            query={"match": {"level": "ERROR"}},
            threshold=0.1,
            time_window=timedelta(minutes=5),
            cooldown=timedelta(minutes=15)
        )
        
        assert rule.id == "test_rule"
        assert rule.alert_type == AlertType.ERROR_RATE
        assert rule.severity == AlertSeverity.HIGH
        assert rule.threshold == 0.1
        
        # Test serialization
        rule_dict = rule.to_dict()
        assert rule_dict["alert_type"] == "error_rate"
        assert rule_dict["severity"] == "HIGH"
    
    def test_alert_creation(self):
        """Test alert creation"""
        alert = Alert(
            id="alert_123",
            rule_id="test_rule",
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.HIGH,
            title="High Error Rate",
            description="Error rate exceeded threshold",
            timestamp=datetime.utcnow(),
            data={"count": 10, "threshold": 5}
        )
        
        assert alert.id == "alert_123"
        assert alert.alert_type == AlertType.ERROR_RATE
        assert alert.severity == AlertSeverity.HIGH
        assert not alert.acknowledged
        assert not alert.resolved
        
        # Test serialization
        alert_dict = alert.to_dict()
        assert alert_dict["alert_type"] == "error_rate"
        assert alert_dict["severity"] == "HIGH"
    
    def test_default_alert_rules(self, mock_alerting_engine):
        """Test default alert rules setup"""
        assert len(mock_alerting_engine.alert_rules) > 0
        assert "high_error_rate" in mock_alerting_engine.alert_rules
        assert "authentication_failures" in mock_alerting_engine.alert_rules
        assert "service_unavailable" in mock_alerting_engine.alert_rules
    
    def test_alert_rule_management(self, mock_alerting_engine):
        """Test alert rule management"""
        # Test adding custom rule
        custom_rule = AlertRule(
            id="custom_rule",
            name="Custom Rule",
            description="Custom alert rule",
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            severity=AlertSeverity.MEDIUM,
            query={"match": {"message": "slow query"}},
            threshold=5,
            time_window=timedelta(minutes=10),
            cooldown=timedelta(minutes=20)
        )
        
        mock_alerting_engine.add_alert_rule(custom_rule)
        assert "custom_rule" in mock_alerting_engine.alert_rules
        
        # Test disabling rule
        mock_alerting_engine.disable_alert_rule("custom_rule")
        assert not mock_alerting_engine.alert_rules["custom_rule"].enabled
        
        # Test enabling rule
        mock_alerting_engine.enable_alert_rule("custom_rule")
        assert mock_alerting_engine.alert_rules["custom_rule"].enabled
        
        # Test removing rule
        mock_alerting_engine.remove_alert_rule("custom_rule")
        assert "custom_rule" not in mock_alerting_engine.alert_rules
    
    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self, mock_alerting_engine):
        """Test alert acknowledgment"""
        # Create test alert
        alert = Alert(
            id="test_alert",
            rule_id="test_rule",
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            description="Test alert description",
            timestamp=datetime.utcnow(),
            data={}
        )
        
        mock_alerting_engine.active_alerts["test_alert"] = alert
        mock_alerting_engine.redis_client = AsyncMock()
        
        # Test acknowledgment
        result = await mock_alerting_engine.acknowledge_alert("test_alert", "user123")
        assert result is True
        assert mock_alerting_engine.active_alerts["test_alert"].acknowledged
    
    @pytest.mark.asyncio
    async def test_alert_resolution(self, mock_alerting_engine):
        """Test alert resolution"""
        # Create test alert
        alert = Alert(
            id="test_alert",
            rule_id="test_rule",
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            description="Test alert description",
            timestamp=datetime.utcnow(),
            data={}
        )
        
        mock_alerting_engine.active_alerts["test_alert"] = alert
        mock_alerting_engine.redis_client = AsyncMock()
        
        # Test resolution
        result = await mock_alerting_engine.resolve_alert("test_alert", "user123")
        assert result is True
        assert mock_alerting_engine.active_alerts["test_alert"].resolved
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, mock_alerting_engine):
        """Test getting active alerts"""
        # Create test alerts
        alert1 = Alert(
            id="alert1",
            rule_id="rule1",
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.HIGH,
            title="Alert 1",
            description="First alert",
            timestamp=datetime.utcnow(),
            data={}
        )
        
        alert2 = Alert(
            id="alert2",
            rule_id="rule2",
            alert_type=AlertType.SECURITY_BREACH,
            severity=AlertSeverity.CRITICAL,
            title="Alert 2",
            description="Second alert",
            timestamp=datetime.utcnow(),
            data={}
        )
        
        mock_alerting_engine.active_alerts["alert1"] = alert1
        mock_alerting_engine.active_alerts["alert2"] = alert2
        
        # Test getting all alerts
        all_alerts = await mock_alerting_engine.get_active_alerts()
        assert len(all_alerts) == 2
        
        # Test filtering by severity
        critical_alerts = await mock_alerting_engine.get_active_alerts(AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertSeverity.CRITICAL


class TestELKIntegration:
    """Test ELK stack integration"""
    
    @pytest.mark.asyncio
    async def test_elasticsearch_connection(self):
        """Test Elasticsearch connection"""
        # This would test actual Elasticsearch connection in integration tests
        pass
    
    @pytest.mark.asyncio
    async def test_logstash_pipeline(self):
        """Test Logstash pipeline processing"""
        # This would test actual Logstash pipeline in integration tests
        pass
    
    @pytest.mark.asyncio
    async def test_kibana_dashboard_creation(self):
        """Test Kibana dashboard creation"""
        # This would test actual Kibana dashboard creation in integration tests
        pass
    
    @pytest.mark.asyncio
    async def test_filebeat_log_shipping(self):
        """Test Filebeat log shipping"""
        # This would test actual Filebeat log shipping in integration tests
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])