"""Alert generation engine with severity classification and rule-based triggering."""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from uuid import uuid4

from shared.models.alert import (
    Alert, AlertCreate, AlertType, SeverityLevel, AlertContext,
    EscalationLevel, AlertStatus
)
from shared.models.post import Post
from shared.models.campaign import Campaign
from shared.models.user import User

from .config import config
from .alert_deduplicator import AlertDeduplicator
from .alert_correlator import AlertCorrelator
from .severity_calculator import SeverityCalculator

logger = logging.getLogger(__name__)


class AlertRule:
    """Represents a rule for generating alerts."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        alert_type: AlertType,
        conditions: Dict[str, Any],
        severity_base: SeverityLevel = SeverityLevel.MEDIUM,
        enabled: bool = True
    ):
        self.rule_id = rule_id
        self.name = name
        self.alert_type = alert_type
        self.conditions = conditions
        self.severity_base = severity_base
        self.enabled = enabled
        self.last_triggered = None
        self.trigger_count = 0
    
    def evaluate(self, data: Dict[str, Any]) -> bool:
        """Evaluate if the rule conditions are met."""
        if not self.enabled:
            return False
        
        try:
            return self._evaluate_conditions(self.conditions, data)
        except Exception as e:
            logger.error(f"Error evaluating rule {self.rule_id}: {e}")
            return False
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Recursively evaluate rule conditions."""
        if "and" in conditions:
            return all(self._evaluate_conditions(cond, data) for cond in conditions["and"])
        
        if "or" in conditions:
            return any(self._evaluate_conditions(cond, data) for cond in conditions["or"])
        
        if "not" in conditions:
            return not self._evaluate_conditions(conditions["not"], data)
        
        # Evaluate individual condition
        field = conditions.get("field")
        operator = conditions.get("operator")
        value = conditions.get("value")
        
        if not all([field, operator, value is not None]):
            return False
        
        data_value = self._get_nested_value(data, field)
        
        if operator == "eq":
            return data_value == value
        elif operator == "ne":
            return data_value != value
        elif operator == "gt":
            return data_value > value
        elif operator == "gte":
            return data_value >= value
        elif operator == "lt":
            return data_value < value
        elif operator == "lte":
            return data_value <= value
        elif operator == "in":
            return data_value in value
        elif operator == "contains":
            return value in str(data_value).lower()
        elif operator == "regex":
            import re
            return bool(re.search(value, str(data_value), re.IGNORECASE))
        
        return False
    
    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested value from data using dot notation."""
        keys = field.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value


class AlertGenerator:
    """Main alert generation engine."""
    
    def __init__(self):
        self.deduplicator = AlertDeduplicator()
        self.correlator = AlertCorrelator()
        self.severity_calculator = SeverityCalculator()
        self.rules: Dict[str, AlertRule] = {}
        self.alert_cache: Dict[str, Alert] = {}
        self.rate_limiter = AlertRateLimiter()
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default alert rules."""
        
        # High-risk content rule
        self.add_rule(AlertRule(
            rule_id="high_risk_content",
            name="High Risk Content Detection",
            alert_type=AlertType.HIGH_RISK_CONTENT,
            conditions={
                "and": [
                    {"field": "analysis.sentiment", "operator": "eq", "value": "Anti-India"},
                    {"field": "analysis.confidence_score", "operator": "gte", "value": 0.7},
                    {"field": "analysis.risk_score", "operator": "gte", "value": 0.6}
                ]
            },
            severity_base=SeverityLevel.HIGH
        ))
        
        # Bot network detection rule
        self.add_rule(AlertRule(
            rule_id="bot_network",
            name="Bot Network Detection",
            alert_type=AlertType.BOT_NETWORK_DETECTED,
            conditions={
                "and": [
                    {"field": "bot_analysis.bot_probability", "operator": "gte", "value": 0.8},
                    {"field": "bot_analysis.network_size", "operator": "gte", "value": 5},
                    {"field": "bot_analysis.coordination_score", "operator": "gte", "value": 0.7}
                ]
            },
            severity_base=SeverityLevel.HIGH
        ))
        
        # Coordinated campaign rule
        self.add_rule(AlertRule(
            rule_id="coordinated_campaign",
            name="Coordinated Campaign Detection",
            alert_type=AlertType.COORDINATED_CAMPAIGN,
            conditions={
                "and": [
                    {"field": "campaign.coordination_score", "operator": "gte", "value": 0.75},
                    {"field": "campaign.participant_count", "operator": "gte", "value": 10},
                    {"field": "campaign.impact_metrics.reach", "operator": "gte", "value": 1000}
                ]
            },
            severity_base=SeverityLevel.HIGH
        ))
        
        # Viral misinformation rule
        self.add_rule(AlertRule(
            rule_id="viral_misinformation",
            name="Viral Misinformation Detection",
            alert_type=AlertType.VIRAL_MISINFORMATION,
            conditions={
                "and": [
                    {"field": "analysis.sentiment", "operator": "eq", "value": "Anti-India"},
                    {"field": "metrics.viral_score", "operator": "gte", "value": 0.8},
                    {"field": "metrics.engagement_rate", "operator": "gte", "value": 0.1}
                ]
            },
            severity_base=SeverityLevel.CRITICAL
        ))
        
        # Volume spike rule
        self.add_rule(AlertRule(
            rule_id="volume_spike",
            name="Volume Spike Detection",
            alert_type=AlertType.VOLUME_SPIKE,
            conditions={
                "and": [
                    {"field": "volume_metrics.spike_ratio", "operator": "gte", "value": 3.0},
                    {"field": "volume_metrics.post_count", "operator": "gte", "value": 100}
                ]
            },
            severity_base=SeverityLevel.MEDIUM
        ))
        
        # Sentiment anomaly rule
        self.add_rule(AlertRule(
            rule_id="sentiment_anomaly",
            name="Sentiment Anomaly Detection",
            alert_type=AlertType.SENTIMENT_ANOMALY,
            conditions={
                "and": [
                    {"field": "sentiment_metrics.anomaly_score", "operator": "gte", "value": 0.7},
                    {"field": "sentiment_metrics.deviation", "operator": "gte", "value": 2.0}
                ]
            },
            severity_base=SeverityLevel.MEDIUM
        ))
    
    def add_rule(self, rule: AlertRule):
        """Add a new alert rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name} ({rule.rule_id})")
    
    def remove_rule(self, rule_id: str):
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
    
    def enable_rule(self, rule_id: str):
        """Enable an alert rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            logger.info(f"Enabled alert rule: {rule_id}")
    
    def disable_rule(self, rule_id: str):
        """Disable an alert rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            logger.info(f"Disabled alert rule: {rule_id}")
    
    async def process_data(self, data: Dict[str, Any]) -> List[Alert]:
        """Process incoming data and generate alerts."""
        alerts = []
        
        try:
            # Check rate limiting
            if not await self.rate_limiter.can_generate_alert():
                logger.warning("Alert generation rate limit exceeded")
                return alerts
            
            # Evaluate all rules
            triggered_rules = []
            for rule in self.rules.values():
                if rule.evaluate(data):
                    triggered_rules.append(rule)
            
            # Generate alerts for triggered rules
            for rule in triggered_rules:
                alert = await self._generate_alert(rule, data)
                if alert:
                    alerts.append(alert)
            
            # Process correlations and deduplication
            alerts = await self._process_alert_correlations(alerts)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error processing data for alerts: {e}")
            return []
    
    async def _generate_alert(self, rule: AlertRule, data: Dict[str, Any]) -> Optional[Alert]:
        """Generate an alert from a triggered rule."""
        try:
            # Create alert context
            context = self._create_alert_context(rule, data)
            
            # Calculate severity
            severity = await self.severity_calculator.calculate_severity(
                rule.severity_base,
                context,
                data
            )
            
            # Generate alert ID
            alert_id = self._generate_alert_id(rule, data)
            
            # Check for deduplication
            if await self.deduplicator.is_duplicate(alert_id, context):
                logger.debug(f"Alert {alert_id} is duplicate, skipping")
                return None
            
            # Create alert
            alert_create = AlertCreate(
                alert_id=alert_id,
                title=self._generate_alert_title(rule, data),
                description=self._generate_alert_description(rule, data),
                alert_type=rule.alert_type,
                severity=severity,
                context=context,
                tags=self._generate_alert_tags(rule, data)
            )
            
            alert = Alert(**alert_create.dict())
            
            # Update rule statistics
            rule.last_triggered = datetime.utcnow()
            rule.trigger_count += 1
            
            # Cache alert
            self.alert_cache[alert_id] = alert
            
            logger.info(f"Generated alert: {alert_id} ({rule.name})")
            return alert
            
        except Exception as e:
            logger.error(f"Error generating alert for rule {rule.rule_id}: {e}")
            return None
    
    def _create_alert_context(self, rule: AlertRule, data: Dict[str, Any]) -> AlertContext:
        """Create alert context from rule and data."""
        now = datetime.utcnow()
        
        context = AlertContext(
            detection_method=rule.name,
            confidence_score=data.get("analysis", {}).get("confidence_score", 0.0),
            risk_score=data.get("analysis", {}).get("risk_score", 0.0),
            detection_window_start=now - timedelta(minutes=30),
            detection_window_end=now
        )
        
        # Extract platform information
        if "platform" in data:
            context.source_platform = data["platform"]
        
        # Extract user and post IDs
        if "user_id" in data:
            context.source_user_ids = [data["user_id"]]
        if "post_id" in data:
            context.source_post_ids = [data["post_id"]]
        if "campaign_id" in data:
            context.source_campaign_id = data["campaign_id"]
        
        # Extract content samples
        if "content" in data:
            context.content_samples = [data["content"][:500]]  # Limit length
        
        # Extract keywords and hashtags
        if "keywords" in data:
            context.keywords_matched = data["keywords"]
        if "hashtags" in data:
            context.hashtags_involved = data["hashtags"]
        
        # Extract geographic information
        if "location" in data:
            location = data["location"]
            if "country" in location:
                context.origin_country = location["country"]
            if "regions" in location:
                context.affected_regions = location["regions"]
        
        # Extract metrics
        if "metrics" in data:
            metrics = data["metrics"]
            context.volume_metrics = {
                k: v for k, v in metrics.items() 
                if k.startswith("volume_") or k in ["post_count", "user_count", "spike_ratio"]
            }
            context.engagement_metrics = {
                k: v for k, v in metrics.items()
                if k.startswith("engagement_") or k in ["likes", "shares", "comments", "views"]
            }
        
        return context
    
    def _generate_alert_id(self, rule: AlertRule, data: Dict[str, Any]) -> str:
        """Generate unique alert ID."""
        # Create hash from rule ID, timestamp, and key data elements
        hash_input = f"{rule.rule_id}_{datetime.utcnow().strftime('%Y%m%d_%H')}"
        
        # Add key identifiers to make ID more specific
        if "user_id" in data:
            hash_input += f"_{data['user_id']}"
        if "campaign_id" in data:
            hash_input += f"_{data['campaign_id']}"
        
        hash_digest = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"alert_{rule.rule_id}_{hash_digest}"
    
    def _generate_alert_title(self, rule: AlertRule, data: Dict[str, Any]) -> str:
        """Generate alert title."""
        base_titles = {
            AlertType.HIGH_RISK_CONTENT: "High-Risk Content Detected",
            AlertType.BOT_NETWORK_DETECTED: "Bot Network Activity Detected",
            AlertType.COORDINATED_CAMPAIGN: "Coordinated Campaign Identified",
            AlertType.VIRAL_MISINFORMATION: "Viral Misinformation Spreading",
            AlertType.VOLUME_SPIKE: "Unusual Volume Spike Detected",
            AlertType.SENTIMENT_ANOMALY: "Sentiment Anomaly Detected"
        }
        
        title = base_titles.get(rule.alert_type, "Alert Triggered")
        
        # Add context-specific information
        if "platform" in data:
            title += f" on {data['platform']}"
        
        if "campaign" in data and "name" in data["campaign"]:
            title += f" - {data['campaign']['name']}"
        
        return title
    
    def _generate_alert_description(self, rule: AlertRule, data: Dict[str, Any]) -> str:
        """Generate alert description."""
        description_parts = [f"Alert triggered by rule: {rule.name}"]
        
        # Add confidence and risk scores
        analysis = data.get("analysis", {})
        if "confidence_score" in analysis:
            description_parts.append(f"Confidence: {analysis['confidence_score']:.2f}")
        if "risk_score" in analysis:
            description_parts.append(f"Risk Score: {analysis['risk_score']:.2f}")
        
        # Add platform and content information
        if "platform" in data:
            description_parts.append(f"Platform: {data['platform']}")
        
        if "content" in data:
            content_preview = data["content"][:200] + "..." if len(data["content"]) > 200 else data["content"]
            description_parts.append(f"Content: {content_preview}")
        
        # Add metrics information
        if "metrics" in data:
            metrics = data["metrics"]
            if "post_count" in metrics:
                description_parts.append(f"Posts: {metrics['post_count']}")
            if "user_count" in metrics:
                description_parts.append(f"Users: {metrics['user_count']}")
            if "engagement_rate" in metrics:
                description_parts.append(f"Engagement Rate: {metrics['engagement_rate']:.2f}")
        
        return " | ".join(description_parts)
    
    def _generate_alert_tags(self, rule: AlertRule, data: Dict[str, Any]) -> List[str]:
        """Generate alert tags."""
        tags = [rule.alert_type.value, rule.rule_id]
        
        if "platform" in data:
            tags.append(f"platform:{data['platform']}")
        
        if "analysis" in data and "sentiment" in data["analysis"]:
            tags.append(f"sentiment:{data['analysis']['sentiment']}")
        
        if "location" in data and "country" in data["location"]:
            tags.append(f"country:{data['location']['country']}")
        
        return tags
    
    async def _process_alert_correlations(self, alerts: List[Alert]) -> List[Alert]:
        """Process alert correlations and grouping."""
        if len(alerts) <= 1:
            return alerts
        
        # Find correlations
        correlations = await self.correlator.find_correlations(alerts)
        
        # Group correlated alerts
        processed_alerts = []
        processed_ids = set()
        
        for correlation in correlations:
            if correlation.primary_alert_id not in processed_ids:
                primary_alert = next(
                    (a for a in alerts if a.alert_id == correlation.primary_alert_id),
                    None
                )
                if primary_alert:
                    # Add related alert IDs
                    primary_alert.related_alerts = correlation.related_alert_ids
                    processed_alerts.append(primary_alert)
                    processed_ids.update([correlation.primary_alert_id] + correlation.related_alert_ids)
        
        # Add non-correlated alerts
        for alert in alerts:
            if alert.alert_id not in processed_ids:
                processed_alerts.append(alert)
        
        return processed_alerts
    
    async def get_rule_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all rules."""
        stats = {}
        
        for rule_id, rule in self.rules.items():
            stats[rule_id] = {
                "name": rule.name,
                "alert_type": rule.alert_type.value,
                "enabled": rule.enabled,
                "trigger_count": rule.trigger_count,
                "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None
            }
        
        return stats


class AlertRateLimiter:
    """Rate limiter for alert generation."""
    
    def __init__(self):
        self.alert_counts: Dict[str, List[datetime]] = {}
        self.max_alerts_per_hour = config.max_alerts_per_hour
    
    async def can_generate_alert(self, alert_type: Optional[str] = None) -> bool:
        """Check if alert can be generated within rate limits."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old entries
        key = alert_type or "global"
        if key in self.alert_counts:
            self.alert_counts[key] = [
                timestamp for timestamp in self.alert_counts[key]
                if timestamp > hour_ago
            ]
        else:
            self.alert_counts[key] = []
        
        # Check rate limit
        return len(self.alert_counts[key]) < self.max_alerts_per_hour
    
    async def record_alert(self, alert_type: Optional[str] = None):
        """Record that an alert was generated."""
        key = alert_type or "global"
        if key not in self.alert_counts:
            self.alert_counts[key] = []
        
        self.alert_counts[key].append(datetime.utcnow())