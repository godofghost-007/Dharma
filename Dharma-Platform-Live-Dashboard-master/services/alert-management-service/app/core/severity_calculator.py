"""Severity calculation engine for alerts."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from shared.models.alert import SeverityLevel, AlertContext, AlertType

from .config import config

logger = logging.getLogger(__name__)


class SeverityFactor(Enum):
    """Factors that influence alert severity."""
    CONFIDENCE_SCORE = "confidence_score"
    RISK_SCORE = "risk_score"
    VOLUME_IMPACT = "volume_impact"
    TEMPORAL_URGENCY = "temporal_urgency"
    GEOGRAPHIC_SPREAD = "geographic_spread"
    PLATFORM_REACH = "platform_reach"
    CONTENT_VIRALITY = "content_virality"
    BOT_INVOLVEMENT = "bot_involvement"
    CAMPAIGN_COORDINATION = "campaign_coordination"


class SeverityCalculator:
    """Calculates alert severity based on multiple factors."""
    
    def __init__(self):
        self.weights = config.severity_weights
        self.severity_thresholds = {
            SeverityLevel.LOW: 0.3,
            SeverityLevel.MEDIUM: 0.5,
            SeverityLevel.HIGH: 0.7,
            SeverityLevel.CRITICAL: 0.85
        }
        
        # Alert type specific modifiers
        self.alert_type_modifiers = {
            AlertType.VIRAL_MISINFORMATION: 1.2,
            AlertType.COORDINATED_CAMPAIGN: 1.15,
            AlertType.BOT_NETWORK_DETECTED: 1.1,
            AlertType.HIGH_RISK_CONTENT: 1.0,
            AlertType.ELECTION_INTERFERENCE: 1.3,
            AlertType.SENTIMENT_ANOMALY: 0.9,
            AlertType.VOLUME_SPIKE: 0.8,
            AlertType.SYSTEM_HEALTH: 0.7
        }
    
    async def calculate_severity(
        self,
        base_severity: SeverityLevel,
        context: AlertContext,
        data: Dict[str, Any]
    ) -> SeverityLevel:
        """Calculate final alert severity."""
        try:
            # Calculate severity score
            severity_score = await self._calculate_severity_score(context, data)
            
            # Apply alert type modifier
            alert_type = data.get("alert_type")
            if alert_type and alert_type in self.alert_type_modifiers:
                severity_score *= self.alert_type_modifiers[alert_type]
            
            # Ensure score is within bounds
            severity_score = max(0.0, min(1.0, severity_score))
            
            # Convert score to severity level
            calculated_severity = self._score_to_severity(severity_score)
            
            # Use the higher of base severity or calculated severity
            final_severity = self._max_severity(base_severity, calculated_severity)
            
            logger.debug(
                f"Severity calculation: base={base_severity}, "
                f"calculated={calculated_severity}, final={final_severity}, "
                f"score={severity_score:.3f}"
            )
            
            return final_severity
            
        except Exception as e:
            logger.error(f"Error calculating severity: {e}")
            return base_severity
    
    async def _calculate_severity_score(
        self,
        context: AlertContext,
        data: Dict[str, Any]
    ) -> float:
        """Calculate overall severity score."""
        factors = {}
        
        # Calculate individual factors
        factors[SeverityFactor.CONFIDENCE_SCORE] = self._calculate_confidence_factor(context, data)
        factors[SeverityFactor.RISK_SCORE] = self._calculate_risk_factor(context, data)
        factors[SeverityFactor.VOLUME_IMPACT] = self._calculate_volume_factor(context, data)
        factors[SeverityFactor.TEMPORAL_URGENCY] = self._calculate_temporal_factor(context, data)
        factors[SeverityFactor.GEOGRAPHIC_SPREAD] = self._calculate_geographic_factor(context, data)
        factors[SeverityFactor.PLATFORM_REACH] = self._calculate_platform_factor(context, data)
        factors[SeverityFactor.CONTENT_VIRALITY] = self._calculate_virality_factor(context, data)
        factors[SeverityFactor.BOT_INVOLVEMENT] = self._calculate_bot_factor(context, data)
        factors[SeverityFactor.CAMPAIGN_COORDINATION] = self._calculate_coordination_factor(context, data)
        
        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0
        
        for factor, score in factors.items():
            if score is not None:
                weight = self.weights.get(factor.value, 0.1)  # Default weight
                total_score += score * weight
                total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            return total_score / total_weight
        else:
            return 0.5  # Default middle score
    
    def _calculate_confidence_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate confidence-based severity factor."""
        return context.confidence_score
    
    def _calculate_risk_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate risk-based severity factor."""
        return context.risk_score
    
    def _calculate_volume_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate volume-based severity factor."""
        volume_metrics = context.volume_metrics
        
        if not volume_metrics:
            return None
        
        # Normalize volume metrics
        post_count = volume_metrics.get("post_count", 0)
        user_count = volume_metrics.get("user_count", 0)
        spike_ratio = volume_metrics.get("spike_ratio", 1.0)
        
        # Calculate volume score
        volume_score = 0.0
        
        # Post count factor (logarithmic scaling)
        if post_count > 0:
            import math
            volume_score += min(0.4, math.log10(post_count + 1) / 4.0)
        
        # User count factor
        if user_count > 0:
            import math
            volume_score += min(0.3, math.log10(user_count + 1) / 3.0)
        
        # Spike ratio factor
        if spike_ratio > 1.0:
            volume_score += min(0.3, (spike_ratio - 1.0) / 10.0)
        
        return min(1.0, volume_score)
    
    def _calculate_temporal_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate temporal urgency factor."""
        now = datetime.utcnow()
        
        # Time since detection
        detection_age = (now - context.detection_window_end).total_seconds() / 3600  # hours
        
        # Recent detections are more urgent
        if detection_age < 1:
            return 1.0
        elif detection_age < 6:
            return 0.8
        elif detection_age < 24:
            return 0.6
        else:
            return 0.4
    
    def _calculate_geographic_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate geographic spread factor."""
        if not context.affected_regions:
            return None
        
        # More regions = higher severity
        region_count = len(context.affected_regions)
        
        if region_count >= 5:
            return 1.0
        elif region_count >= 3:
            return 0.8
        elif region_count >= 2:
            return 0.6
        else:
            return 0.4
    
    def _calculate_platform_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate platform reach factor."""
        platform = context.source_platform
        
        if not platform:
            return None
        
        # Platform reach weights
        platform_weights = {
            "twitter": 0.9,
            "facebook": 0.8,
            "youtube": 0.8,
            "instagram": 0.7,
            "tiktok": 0.9,
            "telegram": 0.6,
            "whatsapp": 0.7,
            "web": 0.5
        }
        
        return platform_weights.get(platform.lower(), 0.5)
    
    def _calculate_virality_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate content virality factor."""
        engagement_metrics = context.engagement_metrics
        
        if not engagement_metrics:
            return None
        
        # Calculate engagement score
        likes = engagement_metrics.get("likes", 0)
        shares = engagement_metrics.get("shares", 0)
        comments = engagement_metrics.get("comments", 0)
        views = engagement_metrics.get("views", 0)
        
        # Weighted engagement score
        engagement_score = (
            likes * 1.0 +
            shares * 3.0 +  # Shares are more viral
            comments * 2.0 +
            views * 0.1
        )
        
        # Normalize to 0-1 scale (logarithmic)
        if engagement_score > 0:
            import math
            return min(1.0, math.log10(engagement_score + 1) / 6.0)
        
        return 0.0
    
    def _calculate_bot_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate bot involvement factor."""
        bot_data = data.get("bot_analysis", {})
        
        if not bot_data:
            return None
        
        bot_probability = bot_data.get("bot_probability", 0.0)
        network_size = bot_data.get("network_size", 0)
        
        # Higher bot probability and network size = higher severity
        bot_score = bot_probability
        
        if network_size > 0:
            import math
            network_factor = min(0.3, math.log10(network_size + 1) / 3.0)
            bot_score += network_factor
        
        return min(1.0, bot_score)
    
    def _calculate_coordination_factor(self, context: AlertContext, data: Dict[str, Any]) -> Optional[float]:
        """Calculate campaign coordination factor."""
        campaign_data = data.get("campaign", {})
        
        if not campaign_data:
            return None
        
        coordination_score = campaign_data.get("coordination_score", 0.0)
        participant_count = campaign_data.get("participant_count", 0)
        
        # Base coordination score
        coord_factor = coordination_score
        
        # Boost for larger participant count
        if participant_count > 0:
            import math
            participant_factor = min(0.2, math.log10(participant_count + 1) / 5.0)
            coord_factor += participant_factor
        
        return min(1.0, coord_factor)
    
    def _score_to_severity(self, score: float) -> SeverityLevel:
        """Convert severity score to severity level."""
        if score >= self.severity_thresholds[SeverityLevel.CRITICAL]:
            return SeverityLevel.CRITICAL
        elif score >= self.severity_thresholds[SeverityLevel.HIGH]:
            return SeverityLevel.HIGH
        elif score >= self.severity_thresholds[SeverityLevel.MEDIUM]:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
    
    def _max_severity(self, severity1: SeverityLevel, severity2: SeverityLevel) -> SeverityLevel:
        """Return the higher of two severity levels."""
        severity_order = [
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL
        ]
        
        index1 = severity_order.index(severity1)
        index2 = severity_order.index(severity2)
        
        return severity_order[max(index1, index2)]
    
    async def get_severity_breakdown(
        self,
        context: AlertContext,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get detailed severity calculation breakdown."""
        factors = {}
        
        # Calculate all factors
        factors["confidence_score"] = self._calculate_confidence_factor(context, data)
        factors["risk_score"] = self._calculate_risk_factor(context, data)
        factors["volume_impact"] = self._calculate_volume_factor(context, data)
        factors["temporal_urgency"] = self._calculate_temporal_factor(context, data)
        factors["geographic_spread"] = self._calculate_geographic_factor(context, data)
        factors["platform_reach"] = self._calculate_platform_factor(context, data)
        factors["content_virality"] = self._calculate_virality_factor(context, data)
        factors["bot_involvement"] = self._calculate_bot_factor(context, data)
        factors["campaign_coordination"] = self._calculate_coordination_factor(context, data)
        
        # Calculate weighted contributions
        contributions = {}
        total_score = 0.0
        total_weight = 0.0
        
        for factor_name, score in factors.items():
            if score is not None:
                weight = self.weights.get(factor_name, 0.1)
                contribution = score * weight
                contributions[factor_name] = {
                    "score": score,
                    "weight": weight,
                    "contribution": contribution
                }
                total_score += contribution
                total_weight += weight
        
        final_score = total_score / total_weight if total_weight > 0 else 0.5
        final_severity = self._score_to_severity(final_score)
        
        return {
            "final_score": final_score,
            "final_severity": final_severity.value,
            "factors": contributions,
            "thresholds": {level.value: threshold for level, threshold in self.severity_thresholds.items()}
        }