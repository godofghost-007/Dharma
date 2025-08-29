"""Alert correlation and grouping logic."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict

from shared.models.alert import Alert, AlertType, AlertContext

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class AlertCorrelation:
    """Represents a correlation between alerts."""
    primary_alert_id: str
    related_alert_ids: List[str]
    correlation_type: str
    correlation_score: float
    correlation_reason: str


@dataclass
class CorrelationRule:
    """Rule for correlating alerts."""
    name: str
    alert_types: List[AlertType]
    correlation_function: str
    threshold: float
    time_window_minutes: int
    max_group_size: int = 10


class AlertCorrelator:
    """Handles alert correlation and grouping."""
    
    def __init__(self):
        self.correlation_threshold = config.alert_correlation_threshold
        self.correlation_rules = self._initialize_correlation_rules()
        self.correlation_cache: Dict[str, List[AlertCorrelation]] = {}
    
    def _initialize_correlation_rules(self) -> List[CorrelationRule]:
        """Initialize correlation rules."""
        return [
            # Same platform and user correlation
            CorrelationRule(
                name="same_user_platform",
                alert_types=[AlertType.HIGH_RISK_CONTENT, AlertType.BOT_NETWORK_DETECTED],
                correlation_function="user_platform_correlation",
                threshold=0.9,
                time_window_minutes=60
            ),
            
            # Campaign-related correlation
            CorrelationRule(
                name="campaign_related",
                alert_types=[AlertType.COORDINATED_CAMPAIGN, AlertType.BOT_NETWORK_DETECTED],
                correlation_function="campaign_correlation",
                threshold=0.8,
                time_window_minutes=120
            ),
            
            # Content similarity correlation
            CorrelationRule(
                name="content_similarity",
                alert_types=[AlertType.HIGH_RISK_CONTENT, AlertType.VIRAL_MISINFORMATION],
                correlation_function="content_similarity_correlation",
                threshold=0.7,
                time_window_minutes=30
            ),
            
            # Geographic correlation
            CorrelationRule(
                name="geographic_correlation",
                alert_types=[AlertType.SENTIMENT_ANOMALY, AlertType.VOLUME_SPIKE],
                correlation_function="geographic_correlation",
                threshold=0.8,
                time_window_minutes=90
            ),
            
            # Temporal pattern correlation
            CorrelationRule(
                name="temporal_pattern",
                alert_types=[AlertType.VOLUME_SPIKE, AlertType.COORDINATED_CAMPAIGN],
                correlation_function="temporal_correlation",
                threshold=0.75,
                time_window_minutes=45
            )
        ]
    
    async def find_correlations(self, alerts: List[Alert]) -> List[AlertCorrelation]:
        """Find correlations among a list of alerts."""
        if len(alerts) < 2:
            return []
        
        correlations = []
        
        try:
            # Apply each correlation rule
            for rule in self.correlation_rules:
                rule_correlations = await self._apply_correlation_rule(rule, alerts)
                correlations.extend(rule_correlations)
            
            # Merge overlapping correlations
            merged_correlations = self._merge_correlations(correlations)
            
            return merged_correlations
            
        except Exception as e:
            logger.error(f"Error finding correlations: {e}")
            return []
    
    async def _apply_correlation_rule(
        self, 
        rule: CorrelationRule, 
        alerts: List[Alert]
    ) -> List[AlertCorrelation]:
        """Apply a specific correlation rule to alerts."""
        correlations = []
        
        # Filter alerts by type and time window
        relevant_alerts = self._filter_alerts_for_rule(rule, alerts)
        
        if len(relevant_alerts) < 2:
            return correlations
        
        # Apply correlation function
        if rule.correlation_function == "user_platform_correlation":
            correlations = await self._user_platform_correlation(rule, relevant_alerts)
        elif rule.correlation_function == "campaign_correlation":
            correlations = await self._campaign_correlation(rule, relevant_alerts)
        elif rule.correlation_function == "content_similarity_correlation":
            correlations = await self._content_similarity_correlation(rule, relevant_alerts)
        elif rule.correlation_function == "geographic_correlation":
            correlations = await self._geographic_correlation(rule, relevant_alerts)
        elif rule.correlation_function == "temporal_correlation":
            correlations = await self._temporal_correlation(rule, relevant_alerts)
        
        return correlations
    
    def _filter_alerts_for_rule(self, rule: CorrelationRule, alerts: List[Alert]) -> List[Alert]:
        """Filter alerts relevant to a correlation rule."""
        relevant_alerts = []
        
        for alert in alerts:
            # Check alert type
            if alert.alert_type in rule.alert_types:
                relevant_alerts.append(alert)
        
        # Sort by creation time
        relevant_alerts.sort(key=lambda a: a.created_at or datetime.utcnow())
        
        return relevant_alerts
    
    async def _user_platform_correlation(
        self, 
        rule: CorrelationRule, 
        alerts: List[Alert]
    ) -> List[AlertCorrelation]:
        """Correlate alerts by user and platform."""
        correlations = []
        
        # Group alerts by user and platform
        user_platform_groups = defaultdict(list)
        
        for alert in alerts:
            context = alert.context
            if context.source_user_ids and context.source_platform:
                for user_id in context.source_user_ids:
                    key = f"{user_id}:{context.source_platform}"
                    user_platform_groups[key].append(alert)
        
        # Create correlations for groups with multiple alerts
        for key, group_alerts in user_platform_groups.items():
            if len(group_alerts) >= 2:
                # Sort by creation time
                group_alerts.sort(key=lambda a: a.created_at or datetime.utcnow())
                
                primary_alert = group_alerts[0]
                related_alerts = group_alerts[1:]
                
                correlation = AlertCorrelation(
                    primary_alert_id=primary_alert.alert_id,
                    related_alert_ids=[a.alert_id for a in related_alerts],
                    correlation_type="user_platform",
                    correlation_score=0.95,  # High confidence for exact matches
                    correlation_reason=f"Same user and platform: {key}"
                )
                correlations.append(correlation)
        
        return correlations
    
    async def _campaign_correlation(
        self, 
        rule: CorrelationRule, 
        alerts: List[Alert]
    ) -> List[AlertCorrelation]:
        """Correlate alerts by campaign."""
        correlations = []
        
        # Group alerts by campaign
        campaign_groups = defaultdict(list)
        
        for alert in alerts:
            context = alert.context
            if context.source_campaign_id:
                campaign_groups[context.source_campaign_id].append(alert)
        
        # Create correlations for campaign groups
        for campaign_id, group_alerts in campaign_groups.items():
            if len(group_alerts) >= 2:
                group_alerts.sort(key=lambda a: a.created_at or datetime.utcnow())
                
                primary_alert = group_alerts[0]
                related_alerts = group_alerts[1:]
                
                correlation = AlertCorrelation(
                    primary_alert_id=primary_alert.alert_id,
                    related_alert_ids=[a.alert_id for a in related_alerts],
                    correlation_type="campaign",
                    correlation_score=0.9,
                    correlation_reason=f"Same campaign: {campaign_id}"
                )
                correlations.append(correlation)
        
        return correlations
    
    async def _content_similarity_correlation(
        self, 
        rule: CorrelationRule, 
        alerts: List[Alert]
    ) -> List[AlertCorrelation]:
        """Correlate alerts by content similarity."""
        correlations = []
        
        # Compare content similarity between alerts
        for i, alert1 in enumerate(alerts):
            related_alerts = []
            
            for j, alert2 in enumerate(alerts[i+1:], i+1):
                similarity = self._calculate_content_similarity(alert1, alert2)
                
                if similarity >= rule.threshold:
                    related_alerts.append(alert2)
            
            if related_alerts:
                correlation = AlertCorrelation(
                    primary_alert_id=alert1.alert_id,
                    related_alert_ids=[a.alert_id for a in related_alerts],
                    correlation_type="content_similarity",
                    correlation_score=similarity,
                    correlation_reason=f"Similar content (similarity: {similarity:.2f})"
                )
                correlations.append(correlation)
        
        return correlations
    
    async def _geographic_correlation(
        self, 
        rule: CorrelationRule, 
        alerts: List[Alert]
    ) -> List[AlertCorrelation]:
        """Correlate alerts by geographic proximity."""
        correlations = []
        
        # Group alerts by country/region
        geo_groups = defaultdict(list)
        
        for alert in alerts:
            context = alert.context
            
            # Group by country
            if context.origin_country:
                geo_groups[f"country:{context.origin_country}"].append(alert)
            
            # Group by regions
            for region in context.affected_regions:
                geo_groups[f"region:{region}"].append(alert)
        
        # Create correlations for geographic groups
        for geo_key, group_alerts in geo_groups.items():
            if len(group_alerts) >= 2:
                group_alerts.sort(key=lambda a: a.created_at or datetime.utcnow())
                
                primary_alert = group_alerts[0]
                related_alerts = group_alerts[1:]
                
                correlation = AlertCorrelation(
                    primary_alert_id=primary_alert.alert_id,
                    related_alert_ids=[a.alert_id for a in related_alerts],
                    correlation_type="geographic",
                    correlation_score=0.85,
                    correlation_reason=f"Same geographic area: {geo_key}"
                )
                correlations.append(correlation)
        
        return correlations
    
    async def _temporal_correlation(
        self, 
        rule: CorrelationRule, 
        alerts: List[Alert]
    ) -> List[AlertCorrelation]:
        """Correlate alerts by temporal patterns."""
        correlations = []
        
        # Group alerts by time windows
        time_window = timedelta(minutes=rule.time_window_minutes)
        time_groups = []
        
        for alert in alerts:
            alert_time = alert.created_at or datetime.utcnow()
            
            # Find existing group within time window
            added_to_group = False
            for group in time_groups:
                group_start = min(a.created_at or datetime.utcnow() for a in group)
                group_end = max(a.created_at or datetime.utcnow() for a in group)
                
                if (alert_time >= group_start - time_window and 
                    alert_time <= group_end + time_window):
                    group.append(alert)
                    added_to_group = True
                    break
            
            if not added_to_group:
                time_groups.append([alert])
        
        # Create correlations for temporal groups
        for group_alerts in time_groups:
            if len(group_alerts) >= 2:
                group_alerts.sort(key=lambda a: a.created_at or datetime.utcnow())
                
                primary_alert = group_alerts[0]
                related_alerts = group_alerts[1:]
                
                time_span = (
                    (group_alerts[-1].created_at or datetime.utcnow()) - 
                    (group_alerts[0].created_at or datetime.utcnow())
                ).total_seconds() / 60
                
                correlation = AlertCorrelation(
                    primary_alert_id=primary_alert.alert_id,
                    related_alert_ids=[a.alert_id for a in related_alerts],
                    correlation_type="temporal",
                    correlation_score=0.8,
                    correlation_reason=f"Temporal cluster ({time_span:.1f} minutes span)"
                )
                correlations.append(correlation)
        
        return correlations
    
    def _calculate_content_similarity(self, alert1: Alert, alert2: Alert) -> float:
        """Calculate content similarity between two alerts."""
        context1 = alert1.context
        context2 = alert2.context
        
        # Compare content samples
        content1 = " ".join(context1.content_samples) if context1.content_samples else ""
        content2 = " ".join(context2.content_samples) if context2.content_samples else ""
        
        if not content1 or not content2:
            return 0.0
        
        # Simple token-based similarity
        tokens1 = set(content1.lower().split())
        tokens2 = set(content2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # Boost similarity if keywords match
        keywords1 = set(context1.keywords_matched) if context1.keywords_matched else set()
        keywords2 = set(context2.keywords_matched) if context2.keywords_matched else set()
        
        keyword_overlap = len(keywords1.intersection(keywords2))
        if keyword_overlap > 0:
            jaccard_similarity += 0.1 * keyword_overlap
        
        # Boost similarity if hashtags match
        hashtags1 = set(context1.hashtags_involved) if context1.hashtags_involved else set()
        hashtags2 = set(context2.hashtags_involved) if context2.hashtags_involved else set()
        
        hashtag_overlap = len(hashtags1.intersection(hashtags2))
        if hashtag_overlap > 0:
            jaccard_similarity += 0.1 * hashtag_overlap
        
        return min(jaccard_similarity, 1.0)
    
    def _merge_correlations(self, correlations: List[AlertCorrelation]) -> List[AlertCorrelation]:
        """Merge overlapping correlations."""
        if not correlations:
            return []
        
        # Group correlations by primary alert
        primary_groups = defaultdict(list)
        for correlation in correlations:
            primary_groups[correlation.primary_alert_id].append(correlation)
        
        merged = []
        
        for primary_id, group_correlations in primary_groups.items():
            if len(group_correlations) == 1:
                merged.append(group_correlations[0])
            else:
                # Merge multiple correlations for same primary alert
                all_related = set()
                correlation_types = []
                reasons = []
                max_score = 0.0
                
                for corr in group_correlations:
                    all_related.update(corr.related_alert_ids)
                    correlation_types.append(corr.correlation_type)
                    reasons.append(corr.correlation_reason)
                    max_score = max(max_score, corr.correlation_score)
                
                merged_correlation = AlertCorrelation(
                    primary_alert_id=primary_id,
                    related_alert_ids=list(all_related),
                    correlation_type=",".join(set(correlation_types)),
                    correlation_score=max_score,
                    correlation_reason="; ".join(reasons)
                )
                merged.append(merged_correlation)
        
        return merged
    
    async def get_correlation_stats(self) -> Dict:
        """Get correlation statistics."""
        total_correlations = len(self.correlation_cache)
        
        # Count by correlation type
        type_counts = defaultdict(int)
        for correlations in self.correlation_cache.values():
            for correlation in correlations:
                type_counts[correlation.correlation_type] += 1
        
        return {
            "total_correlations": total_correlations,
            "by_type": dict(type_counts),
            "correlation_threshold": self.correlation_threshold,
            "active_rules": len(self.correlation_rules)
        }