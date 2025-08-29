"""Unit tests for alert management components."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import alert management components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services/alert-management-service'))

from app.core.alert_generator import AlertGenerator, AlertRule, AlertRateLimiter
from app.core.alert_deduplicator import AlertDeduplicator
from app.core.alert_correlator import AlertCorrelator
from app.core.severity_calculator import SeverityCalculator
from app.notifications.notification_service import NotificationService
from shared.models.alert import (
    Alert, AlertCreate, AlertType, SeverityLevel, AlertContext,
    AlertStatus, NotificationChannel, EscalationLevel
)


class TestAlertRule:
    """Test alert rule functionality."""
    
    def test_alert_rule_creation(self):
        """Test alert rule creation."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "risk_score", "operator": "gte", "value": 0.7},
            severity_base=SeverityLevel.HIGH
        )
        
        assert rule.rule_id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.alert_type == AlertType.HIGH_RISK_CONTENT
        assert rule.severity_base == SeverityLevel.HIGH
        assert rule.enabled == True
        assert rule.trigger_count == 0
    
    def test_simple_condition_evaluation(self):
        """Test simple condition evaluation."""
        rule = AlertRule(
            rule_id="simple_rule",
            name="Simple Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "risk_score", "operator": "gte", "value": 0.7}
        )
        
        # Test data that should trigger the rule
        data = {"risk_score": 0.8}
        assert rule.evaluate(data) == True
        
        # Test data that should not trigger the rule
        data = {"risk_score": 0.5}
        assert rule.evaluate(data) == False
    
    def test_complex_condition_evaluation(self):
        """Test complex condition evaluation with AND/OR logic."""
        rule = AlertRule(
            rule_id="complex_rule",
            name="Complex Rule",
            alert_type=AlertType.BOT_NETWORK_DETECTED,
            conditions={
                "and": [
                    {"field": "bot_probability", "operator": "gte", "value": 0.8},
                    {"or": [
                        {"field": "network_size", "operator": "gte", "value": 5},
                        {"field": "coordination_score", "operator": "gte", "value": 0.9}
                    ]}
                ]
            }
        )
        
        # Test data that should trigger (high bot probability + large network)
        data = {"bot_probability": 0.85, "network_size": 6, "coordination_score": 0.5}
        assert rule.evaluate(data) == True
        
        # Test data that should trigger (high bot probability + high coordination)
        data = {"bot_probability": 0.85, "network_size": 2, "coordination_score": 0.95}
        assert rule.evaluate(data) == True
        
        # Test data that should not trigger (low bot probability)
        data = {"bot_probability": 0.5, "network_size": 10, "coordination_score": 0.95}
        assert rule.evaluate(data) == False
    
    def test_nested_field_evaluation(self):
        """Test evaluation of nested fields using dot notation."""
        rule = AlertRule(
            rule_id="nested_rule",
            name="Nested Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "analysis.sentiment.confidence", "operator": "gte", "value": 0.8}
        )
        
        # Test nested data structure
        data = {
            "analysis": {
                "sentiment": {
                    "confidence": 0.9
                }
            }
        }
        assert rule.evaluate(data) == True
        
        # Test missing nested field
        data = {"analysis": {"other_field": "value"}}
        assert rule.evaluate(data) == False
    
    def test_string_operations(self):
        """Test string-based condition operations."""
        rule = AlertRule(
            rule_id="string_rule",
            name="String Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "content", "operator": "contains", "value": "terrorist"}
        )
        
        # Test content that contains the keyword
        data = {"content": "This terrorist attack is terrible"}
        assert rule.evaluate(data) == True
        
        # Test content that doesn't contain the keyword
        data = {"content": "This is normal content"}
        assert rule.evaluate(data) == False
    
    def test_disabled_rule(self):
        """Test that disabled rules don't trigger."""
        rule = AlertRule(
            rule_id="disabled_rule",
            name="Disabled Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "risk_score", "operator": "gte", "value": 0.1},
            enabled=False
        )
        
        # Even with matching data, disabled rule should not trigger
        data = {"risk_score": 0.9}
        assert rule.evaluate(data) == False


class TestAlertGenerator:
    """Test alert generator functionality."""
    
    @pytest.fixture
    def alert_generator(self):
        """Create alert generator with mocked dependencies."""
        generator = AlertGenerator()
        generator.deduplicator = Mock(spec=AlertDeduplicator)
        generator.correlator = Mock(spec=AlertCorrelator)
        generator.severity_calculator = Mock(spec=SeverityCalculator)
        generator.rate_limiter = Mock(spec=AlertRateLimiter)
        
        # Mock async methods
        generator.deduplicator.is_duplicate = AsyncMock(return_value=False)
        generator.correlator.find_correlations = AsyncMock(return_value=[])
        generator.severity_calculator.calculate_severity = AsyncMock(return_value=SeverityLevel.HIGH)
        generator.rate_limiter.can_generate_alert = AsyncMock(return_value=True)
        
        return generator
    
    @pytest.mark.asyncio
    async def test_process_data_single_rule(self, alert_generator):
        """Test processing data with a single matching rule."""
        # Add a test rule
        alert_generator.add_rule(AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "risk_score", "operator": "gte", "value": 0.7}
        ))
        
        # Test data that should trigger the rule
        data = {
            "risk_score": 0.8,
            "content": "Test content",
            "platform": "twitter",
            "user_id": "user123",
            "analysis": {"confidence_score": 0.9}
        }
        
        alerts = await alert_generator.process_data(data)
        
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HIGH_RISK_CONTENT
        assert alerts[0].severity == SeverityLevel.HIGH
        assert "Test Rule" in alerts[0].description
    
    @pytest.mark.asyncio
    async def test_process_data_multiple_rules(self, alert_generator):
        """Test processing data with multiple matching rules."""
        # Add multiple test rules
        alert_generator.add_rule(AlertRule(
            rule_id="rule1",
            name="Rule 1",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "risk_score", "operator": "gte", "value": 0.7}
        ))
        
        alert_generator.add_rule(AlertRule(
            rule_id="rule2",
            name="Rule 2",
            alert_type=AlertType.SENTIMENT_ANOMALY,
            conditions={"field": "anomaly_score", "operator": "gte", "value": 0.8}
        ))
        
        # Test data that should trigger both rules
        data = {
            "risk_score": 0.8,
            "anomaly_score": 0.9,
            "content": "Test content",
            "analysis": {"confidence_score": 0.9}
        }
        
        alerts = await alert_generator.process_data(data)
        
        assert len(alerts) == 2
        alert_types = [alert.alert_type for alert in alerts]
        assert AlertType.HIGH_RISK_CONTENT in alert_types
        assert AlertType.SENTIMENT_ANOMALY in alert_types
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, alert_generator):
        """Test alert generation rate limiting."""
        # Mock rate limiter to deny generation
        alert_generator.rate_limiter.can_generate_alert = AsyncMock(return_value=False)
        
        # Add a test rule
        alert_generator.add_rule(AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "risk_score", "operator": "gte", "value": 0.7}
        ))
        
        # Test data that would normally trigger
        data = {"risk_score": 0.8}
        
        alerts = await alert_generator.process_data(data)
        
        # Should return empty list due to rate limiting
        assert len(alerts) == 0
    
    @pytest.mark.asyncio
    async def test_deduplication(self, alert_generator):
        """Test alert deduplication."""
        # Mock deduplicator to indicate duplicate
        alert_generator.deduplicator.is_duplicate = AsyncMock(return_value=True)
        
        # Add a test rule
        alert_generator.add_rule(AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "risk_score", "operator": "gte", "value": 0.7}
        ))
        
        # Test data that would normally trigger
        data = {"risk_score": 0.8, "analysis": {"confidence_score": 0.9}}
        
        alerts = await alert_generator.process_data(data)
        
        # Should return empty list due to deduplication
        assert len(alerts) == 0
    
    def test_alert_id_generation(self, alert_generator):
        """Test alert ID generation."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={}
        )
        
        data = {"user_id": "user123", "campaign_id": "camp456"}
        
        alert_id = alert_generator._generate_alert_id(rule, data)
        
        assert alert_id.startswith("alert_test_rule_")
        assert len(alert_id) > len("alert_test_rule_")
    
    def test_alert_title_generation(self, alert_generator):
        """Test alert title generation."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={}
        )
        
        data = {"platform": "twitter"}
        
        title = alert_generator._generate_alert_title(rule, data)
        
        assert "High-Risk Content Detected" in title
        assert "twitter" in title
    
    def test_alert_description_generation(self, alert_generator):
        """Test alert description generation."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={}
        )
        
        data = {
            "platform": "twitter",
            "content": "Test content for description",
            "analysis": {"confidence_score": 0.85, "risk_score": 0.75},
            "metrics": {"post_count": 10, "engagement_rate": 0.05}
        }
        
        description = alert_generator._generate_alert_description(rule, data)
        
        assert "Test Rule" in description
        assert "Confidence: 0.85" in description
        assert "Risk Score: 0.75" in description
        assert "Platform: twitter" in description
        assert "Posts: 10" in description
    
    def test_alert_tags_generation(self, alert_generator):
        """Test alert tags generation."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={}
        )
        
        data = {
            "platform": "twitter",
            "analysis": {"sentiment": "Anti-India"},
            "location": {"country": "India"}
        }
        
        tags = alert_generator._generate_alert_tags(rule, data)
        
        assert "high_risk_content" in tags
        assert "test_rule" in tags
        assert "platform:twitter" in tags
        assert "sentiment:Anti-India" in tags
        assert "country:India" in tags
    
    @pytest.mark.asyncio
    async def test_get_rule_statistics(self, alert_generator):
        """Test getting rule statistics."""
        # Add a test rule and simulate some triggers
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "risk_score", "operator": "gte", "value": 0.7}
        )
        rule.trigger_count = 5
        rule.last_triggered = datetime.utcnow()
        
        alert_generator.add_rule(rule)
        
        stats = await alert_generator.get_rule_statistics()
        
        assert "test_rule" in stats
        assert stats["test_rule"]["name"] == "Test Rule"
        assert stats["test_rule"]["trigger_count"] == 5
        assert stats["test_rule"]["enabled"] == True


class TestAlertRateLimiter:
    """Test alert rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing."""
        limiter = AlertRateLimiter()
        limiter.max_alerts_per_hour = 10  # Set low limit for testing
        return limiter
    
    @pytest.mark.asyncio
    async def test_can_generate_alert_within_limit(self, rate_limiter):
        """Test alert generation within rate limit."""
        # Should be able to generate alerts initially
        for i in range(5):
            assert await rate_limiter.can_generate_alert() == True
            await rate_limiter.record_alert()
    
    @pytest.mark.asyncio
    async def test_can_generate_alert_exceeds_limit(self, rate_limiter):
        """Test alert generation when exceeding rate limit."""
        # Generate alerts up to the limit
        for i in range(10):
            await rate_limiter.record_alert()
        
        # Should not be able to generate more alerts
        assert await rate_limiter.can_generate_alert() == False
    
    @pytest.mark.asyncio
    async def test_rate_limit_by_type(self, rate_limiter):
        """Test rate limiting by alert type."""
        # Generate alerts for specific type
        for i in range(5):
            await rate_limiter.record_alert("high_risk_content")
        
        # Should still be able to generate global alerts
        assert await rate_limiter.can_generate_alert() == True
        
        # Should be limited for the specific type if we had type-specific limits
        # (This would require implementing type-specific limits in the actual class)


class TestNotificationService:
    """Test notification service functionality."""
    
    @pytest.fixture
    def notification_service(self):
        """Create notification service with mocked providers."""
        service = NotificationService()
        
        # Mock notification providers
        service.email_provider = Mock()
        service.sms_provider = Mock()
        service.webhook_provider = Mock()
        service.dashboard_provider = Mock()
        
        # Mock async methods
        service.email_provider.send_notification = AsyncMock(return_value=True)
        service.sms_provider.send_notification = AsyncMock(return_value=True)
        service.webhook_provider.send_notification = AsyncMock(return_value=True)
        service.dashboard_provider.send_notification = AsyncMock(return_value=True)
        
        return service
    
    @pytest.fixture
    def sample_alert(self):
        """Create sample alert for testing."""
        context = AlertContext(
            detection_method="test_method",
            confidence_score=0.9,
            risk_score=0.8,
            detection_window_start=datetime.utcnow() - timedelta(hours=1),
            detection_window_end=datetime.utcnow()
        )
        
        return Alert(
            alert_id="test_alert_001",
            title="Test Alert",
            description="This is a test alert",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.HIGH,
            context=context
        )
    
    @pytest.mark.asyncio
    async def test_send_notification_email(self, notification_service, sample_alert):
        """Test sending email notification."""
        result = await notification_service.send_notification(
            sample_alert,
            [NotificationChannel.EMAIL],
            ["test@example.com"]
        )
        
        assert result == True
        notification_service.email_provider.send_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_sms(self, notification_service, sample_alert):
        """Test sending SMS notification."""
        result = await notification_service.send_notification(
            sample_alert,
            [NotificationChannel.SMS],
            ["+1234567890"]
        )
        
        assert result == True
        notification_service.sms_provider.send_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_multiple_channels(self, notification_service, sample_alert):
        """Test sending notification to multiple channels."""
        channels = [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.DASHBOARD]
        recipients = ["test@example.com", "+1234567890", "dashboard"]
        
        result = await notification_service.send_notification(
            sample_alert,
            channels,
            recipients
        )
        
        assert result == True
        notification_service.email_provider.send_notification.assert_called_once()
        notification_service.sms_provider.send_notification.assert_called_once()
        notification_service.dashboard_provider.send_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_notification_failure_handling(self, notification_service, sample_alert):
        """Test handling of notification failures."""
        # Mock email provider to fail
        notification_service.email_provider.send_notification = AsyncMock(return_value=False)
        
        result = await notification_service.send_notification(
            sample_alert,
            [NotificationChannel.EMAIL],
            ["test@example.com"]
        )
        
        # Should handle failure gracefully
        assert result == False


class TestAlertIntegration:
    """Test integration between alert management components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_alert_processing(self):
        """Test complete alert processing pipeline."""
        # Create alert generator with real dependencies
        generator = AlertGenerator()
        
        # Mock external dependencies
        generator.deduplicator.is_duplicate = AsyncMock(return_value=False)
        generator.correlator.find_correlations = AsyncMock(return_value=[])
        generator.severity_calculator.calculate_severity = AsyncMock(return_value=SeverityLevel.HIGH)
        generator.rate_limiter.can_generate_alert = AsyncMock(return_value=True)
        
        # Test data that should trigger default rules
        data = {
            "analysis": {
                "sentiment": "Anti-India",
                "confidence_score": 0.85,
                "risk_score": 0.75
            },
            "platform": "twitter",
            "user_id": "suspicious_user",
            "content": "This is anti-India content for testing"
        }
        
        # Process data
        alerts = await generator.process_data(data)
        
        # Should generate at least one alert
        assert len(alerts) > 0
        
        # Verify alert properties
        alert = alerts[0]
        assert alert.alert_type == AlertType.HIGH_RISK_CONTENT
        assert alert.severity == SeverityLevel.HIGH
        assert alert.status == AlertStatus.NEW
        assert "Anti-India" in alert.description
    
    @pytest.mark.asyncio
    async def test_alert_lifecycle_methods(self):
        """Test alert lifecycle methods (acknowledge, assign, resolve, escalate)."""
        # Create test alert
        context = AlertContext(
            detection_method="test_method",
            confidence_score=0.9,
            risk_score=0.8,
            detection_window_start=datetime.utcnow() - timedelta(hours=1),
            detection_window_end=datetime.utcnow()
        )
        
        alert = Alert(
            alert_id="lifecycle_test_001",
            title="Lifecycle Test Alert",
            description="Testing alert lifecycle methods",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            severity=SeverityLevel.HIGH,
            context=context
        )
        
        # Test acknowledge
        alert.acknowledge("analyst1", "Reviewing the alert")
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "analyst1"
        assert alert.acknowledged_at is not None
        assert alert.response_time_minutes is not None
        assert len(alert.actions) == 1
        
        # Test assign
        alert.assign("analyst2", "supervisor1")
        assert alert.assigned_to == "analyst2"
        assert alert.assigned_at is not None
        assert len(alert.actions) == 2
        
        # Test resolve
        alert.resolve("analyst2", "False positive - resolved")
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_by == "analyst2"
        assert alert.resolved_at is not None
        assert alert.resolution_time_minutes is not None
        assert len(alert.actions) == 3
        
        # Test escalate (on a new alert)
        alert2 = Alert(
            alert_id="escalation_test_001",
            title="Escalation Test Alert",
            description="Testing alert escalation",
            alert_type=AlertType.COORDINATED_CAMPAIGN,
            severity=SeverityLevel.CRITICAL,
            context=context
        )
        
        alert2.escalate("supervisor1", EscalationLevel.LEVEL_3, "Needs management attention")
        assert alert2.status == AlertStatus.ESCALATED
        assert alert2.escalation_level == EscalationLevel.LEVEL_3
        assert alert2.escalated_by == "supervisor1"
        assert alert2.escalated_at is not None
        assert len(alert2.actions) == 1