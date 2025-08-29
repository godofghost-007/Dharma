"""Tests for alert generation engine."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.core.alert_generator import AlertGenerator, AlertRule
from app.core.alert_deduplicator import AlertDeduplicator
from app.core.alert_correlator import AlertCorrelator
from app.core.severity_calculator import SeverityCalculator
from shared.models.alert import AlertType, SeverityLevel, AlertContext


@pytest.fixture
def alert_generator():
    """Create alert generator instance."""
    return AlertGenerator()


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return {
        "platform": "twitter",
        "user_id": "user123",
        "post_id": "post456",
        "content": "This is anti-India propaganda content",
        "analysis": {
            "sentiment": "Anti-India",
            "confidence_score": 0.85,
            "risk_score": 0.75
        },
        "metrics": {
            "post_count": 50,
            "user_count": 10,
            "spike_ratio": 2.5,
            "likes": 100,
            "shares": 25,
            "comments": 15,
            "views": 1000
        },
        "location": {
            "country": "India",
            "regions": ["Delhi", "Mumbai"]
        },
        "keywords": ["anti-india", "propaganda"],
        "hashtags": ["#fake", "#news"]
    }


class TestAlertGenerator:
    """Test alert generation functionality."""
    
    @pytest.mark.asyncio
    async def test_process_data_generates_alerts(self, alert_generator, sample_data):
        """Test that processing data generates appropriate alerts."""
        alerts = await alert_generator.process_data(sample_data)
        
        assert len(alerts) > 0
        alert = alerts[0]
        assert alert.alert_type == AlertType.HIGH_RISK_CONTENT
        assert alert.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        assert "anti-India" in alert.description.lower()
    
    @pytest.mark.asyncio
    async def test_rule_evaluation(self, alert_generator, sample_data):
        """Test rule evaluation logic."""
        rule = alert_generator.rules["high_risk_content"]
        
        # Test positive case
        assert rule.evaluate(sample_data) == True
        
        # Test negative case
        negative_data = sample_data.copy()
        negative_data["analysis"]["confidence_score"] = 0.5  # Below threshold
        assert rule.evaluate(negative_data) == False
    
    @pytest.mark.asyncio
    async def test_alert_deduplication(self, alert_generator, sample_data):
        """Test alert deduplication."""
        # Generate first alert
        alerts1 = await alert_generator.process_data(sample_data)
        assert len(alerts1) > 0
        
        # Generate duplicate alert
        alerts2 = await alert_generator.process_data(sample_data)
        
        # Should be deduplicated (empty or same alert ID)
        if alerts2:
            assert alerts2[0].alert_id == alerts1[0].alert_id
    
    @pytest.mark.asyncio
    async def test_severity_calculation(self, alert_generator, sample_data):
        """Test severity calculation."""
        alerts = await alert_generator.process_data(sample_data)
        alert = alerts[0]
        
        # High confidence and risk should result in high severity
        assert alert.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        
        # Test with lower scores
        low_data = sample_data.copy()
        low_data["analysis"]["confidence_score"] = 0.4
        low_data["analysis"]["risk_score"] = 0.3
        
        low_alerts = await alert_generator.process_data(low_data)
        if low_alerts:  # Might not trigger due to low scores
            assert low_alerts[0].severity in [SeverityLevel.LOW, SeverityLevel.MEDIUM]
    
    @pytest.mark.asyncio
    async def test_alert_context_creation(self, alert_generator, sample_data):
        """Test alert context creation."""
        alerts = await alert_generator.process_data(sample_data)
        alert = alerts[0]
        context = alert.context
        
        assert context.source_platform == "twitter"
        assert "user123" in context.source_user_ids
        assert "post456" in context.source_post_ids
        assert context.confidence_score == 0.85
        assert context.risk_score == 0.75
        assert "anti-india" in context.keywords_matched
        assert "#fake" in context.hashtags_involved
    
    def test_add_remove_rules(self, alert_generator):
        """Test adding and removing rules."""
        initial_count = len(alert_generator.rules)
        
        # Add new rule
        new_rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            alert_type=AlertType.SUSPICIOUS_ACTIVITY,
            conditions={"field": "test", "operator": "eq", "value": "test"}
        )
        alert_generator.add_rule(new_rule)
        
        assert len(alert_generator.rules) == initial_count + 1
        assert "test_rule" in alert_generator.rules
        
        # Remove rule
        alert_generator.remove_rule("test_rule")
        assert len(alert_generator.rules) == initial_count
        assert "test_rule" not in alert_generator.rules
    
    def test_enable_disable_rules(self, alert_generator):
        """Test enabling and disabling rules."""
        rule_id = "high_risk_content"
        
        # Disable rule
        alert_generator.disable_rule(rule_id)
        assert alert_generator.rules[rule_id].enabled == False
        
        # Enable rule
        alert_generator.enable_rule(rule_id)
        assert alert_generator.rules[rule_id].enabled == True
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, alert_generator, sample_data):
        """Test alert rate limiting."""
        # Mock rate limiter to return False
        with patch.object(alert_generator.rate_limiter, 'can_generate_alert', return_value=False):
            alerts = await alert_generator.process_data(sample_data)
            assert len(alerts) == 0
    
    @pytest.mark.asyncio
    async def test_rule_statistics(self, alert_generator, sample_data):
        """Test rule statistics tracking."""
        # Generate alert to trigger rule
        await alert_generator.process_data(sample_data)
        
        stats = await alert_generator.get_rule_statistics()
        
        assert "high_risk_content" in stats
        rule_stats = stats["high_risk_content"]
        assert rule_stats["trigger_count"] > 0
        assert rule_stats["last_triggered"] is not None


class TestAlertRule:
    """Test alert rule functionality."""
    
    def test_rule_condition_evaluation(self):
        """Test rule condition evaluation."""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={
                "and": [
                    {"field": "score", "operator": "gte", "value": 0.7},
                    {"field": "type", "operator": "eq", "value": "risk"}
                ]
            }
        )
        
        # Test positive case
        data = {"score": 0.8, "type": "risk"}
        assert rule.evaluate(data) == True
        
        # Test negative case
        data = {"score": 0.6, "type": "risk"}
        assert rule.evaluate(data) == False
    
    def test_nested_field_access(self):
        """Test nested field access in conditions."""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={"field": "analysis.confidence", "operator": "gte", "value": 0.7}
        )
        
        data = {"analysis": {"confidence": 0.8}}
        assert rule.evaluate(data) == True
        
        data = {"analysis": {"confidence": 0.6}}
        assert rule.evaluate(data) == False
    
    def test_complex_conditions(self):
        """Test complex condition logic."""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={
                "or": [
                    {"field": "urgent", "operator": "eq", "value": True},
                    {
                        "and": [
                            {"field": "score", "operator": "gte", "value": 0.8},
                            {"field": "verified", "operator": "eq", "value": True}
                        ]
                    }
                ]
            }
        )
        
        # Test urgent case
        data = {"urgent": True, "score": 0.5, "verified": False}
        assert rule.evaluate(data) == True
        
        # Test high score + verified case
        data = {"urgent": False, "score": 0.9, "verified": True}
        assert rule.evaluate(data) == True
        
        # Test negative case
        data = {"urgent": False, "score": 0.7, "verified": False}
        assert rule.evaluate(data) == False


if __name__ == "__main__":
    pytest.main([__file__])