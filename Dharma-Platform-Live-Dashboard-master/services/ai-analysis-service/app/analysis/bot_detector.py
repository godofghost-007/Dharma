"""Bot detection system using behavioral analysis and machine learning."""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import joblib
import networkx as nx

from ..core.config import settings
from ..models.requests import BotDetectionResponse


logger = logging.getLogger(__name__)


class BotDetector:
    """Advanced bot detection using behavioral analysis and machine learning."""
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize the bot detector.
        
        Args:
            model_path: Path to the trained model. If None, uses default from settings.
        """
        self.model_path = model_path or settings.bot_detection_model_name
        self.model_version = "1.0.0"
        
        # ML components
        self.classifier = None
        self.scaler = None
        self.anomaly_detector = None
        
        # Feature extractors
        self.feature_extractors = {}
        
        # Performance tracking
        self.total_analyses = 0
        self.total_processing_time = 0.0
        
        # Bot detection thresholds
        self.bot_threshold = 0.7
        self.anomaly_threshold = -0.5
        
        # Risk indicators
        self.risk_indicators = {
            'high_risk': [
                'extremely_high_posting_frequency',
                'identical_content_repetition',
                'suspicious_account_age',
                'abnormal_engagement_patterns',
                'coordinated_behavior_detected'
            ],
            'medium_risk': [
                'high_posting_frequency',
                'low_content_diversity',
                'unusual_activity_patterns',
                'suspicious_network_connections',
                'automated_response_patterns'
            ]
        }
    
    async def initialize(self) -> None:
        """Initialize the bot detection system."""
        try:
            logger.info("Initializing bot detector")
            
            # Load or create models
            await self._load_or_create_models()
            
            # Initialize feature extractors
            await self._initialize_feature_extractors()
            
            logger.info("Bot detector initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot detector: {e}")
            raise
    
    async def _load_or_create_models(self) -> None:
        """Load existing models or create new ones."""
        try:
            # Try to load existing models
            try:
                self.classifier = joblib.load(f"{self.model_path}/bot_classifier.pkl")
                self.scaler = joblib.load(f"{self.model_path}/feature_scaler.pkl")
                self.anomaly_detector = joblib.load(f"{self.model_path}/anomaly_detector.pkl")
                logger.info("Loaded existing bot detection models")
                
            except FileNotFoundError:
                # Create new models if none exist
                logger.info("Creating new bot detection models")
                await self._create_default_models()
                
        except Exception as e:
            logger.error(f"Error loading/creating models: {e}")
            raise
    
    async def _create_default_models(self) -> None:
        """Create default models for bot detection."""
        try:
            # Create Random Forest classifier
            self.classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            
            # Create feature scaler
            self.scaler = StandardScaler()
            
            # Create anomaly detector
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            
            # Train with synthetic data for demo purposes
            # In production, this would use real labeled data
            await self._train_with_synthetic_data()
            
        except Exception as e:
            logger.error(f"Error creating default models: {e}")
            raise
    
    async def _train_with_synthetic_data(self) -> None:
        """Train models with synthetic data for demonstration."""
        try:
            # Generate synthetic training data
            n_samples = 1000
            n_features = 15
            
            # Create synthetic features
            np.random.seed(42)
            
            # Human users (70% of data)
            human_features = np.random.normal(0, 1, (int(n_samples * 0.7), n_features))
            human_labels = np.zeros(int(n_samples * 0.7))
            
            # Bot users (30% of data) - with different patterns
            bot_features = np.random.normal(2, 1.5, (int(n_samples * 0.3), n_features))
            bot_labels = np.ones(int(n_samples * 0.3))
            
            # Combine data
            X = np.vstack([human_features, bot_features])
            y = np.hstack([human_labels, bot_labels])
            
            # Fit scaler
            X_scaled = self.scaler.fit_transform(X)
            
            # Train classifier
            self.classifier.fit(X_scaled, y)
            
            # Train anomaly detector
            self.anomaly_detector.fit(X_scaled)
            
            logger.info("Models trained with synthetic data")
            
        except Exception as e:
            logger.error(f"Error training with synthetic data: {e}")
            raise
    
    async def _initialize_feature_extractors(self) -> None:
        """Initialize feature extraction components."""
        try:
            self.feature_extractors = {
                'temporal': TemporalFeatureExtractor(),
                'content': ContentFeatureExtractor(),
                'network': NetworkFeatureExtractor(),
                'behavioral': BehavioralFeatureExtractor()
            }
            
            logger.info("Feature extractors initialized")
            
        except Exception as e:
            logger.error(f"Error initializing feature extractors: {e}")
            raise
    
    async def analyze_user_behavior(
        self,
        user_id: str,
        platform: str,
        user_data: Dict[str, Any],
        include_network_analysis: bool = True
    ) -> BotDetectionResponse:
        """Analyze user behavior for bot indicators.
        
        Args:
            user_id: User ID to analyze
            platform: Platform name
            user_data: User profile and activity data
            include_network_analysis: Whether to include network analysis
            
        Returns:
            BotDetectionResponse with analysis results
        """
        start_time = time.time()
        
        try:
            # Extract behavioral features
            features = await self._extract_behavioral_features(user_data, include_network_analysis)
            
            # Predict bot probability
            bot_probability, confidence = await self._predict_bot_probability(features)
            
            # Detect risk indicators
            risk_indicators = await self._detect_risk_indicators(features, user_data)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Update performance tracking
            self.total_analyses += 1
            self.total_processing_time += processing_time
            
            return BotDetectionResponse(
                user_id=user_id,
                platform=platform,
                bot_probability=bot_probability,
                confidence=confidence,
                risk_indicators=risk_indicators,
                behavioral_features=features,
                model_version=self.model_version,
                analysis_timestamp=datetime.utcnow(),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error analyzing user behavior: {e}")
            raise
    
    async def _extract_behavioral_features(
        self,
        user_data: Dict[str, Any],
        include_network_analysis: bool
    ) -> Dict[str, Any]:
        """Extract behavioral features from user data.
        
        Args:
            user_data: User profile and activity data
            include_network_analysis: Whether to include network analysis
            
        Returns:
            Dictionary of extracted features
        """
        try:
            features = {}
            
            # Extract temporal features
            temporal_features = await self.feature_extractors['temporal'].extract(user_data)
            features.update(temporal_features)
            
            # Extract content features
            content_features = await self.feature_extractors['content'].extract(user_data)
            features.update(content_features)
            
            # Extract behavioral features
            behavioral_features = await self.feature_extractors['behavioral'].extract(user_data)
            features.update(behavioral_features)
            
            # Extract network features if requested
            if include_network_analysis:
                network_features = await self.feature_extractors['network'].extract(user_data)
                features.update(network_features)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting behavioral features: {e}")
            return {}
    
    async def _predict_bot_probability(
        self,
        features: Dict[str, Any]
    ) -> Tuple[float, float]:
        """Predict bot probability using machine learning models.
        
        Args:
            features: Extracted behavioral features
            
        Returns:
            Tuple of (bot_probability, confidence)
        """
        try:
            # Convert features to array
            feature_array = self._features_to_array(features)
            
            if feature_array is None or len(feature_array) == 0:
                return 0.5, 0.1  # Default values if no features
            
            # Scale features
            feature_array_scaled = self.scaler.transform([feature_array])
            
            # Get bot probability from classifier
            bot_probabilities = self.classifier.predict_proba(feature_array_scaled)[0]
            bot_probability = bot_probabilities[1] if len(bot_probabilities) > 1 else 0.5
            
            # Get anomaly score
            anomaly_score = self.anomaly_detector.decision_function(feature_array_scaled)[0]
            
            # Combine scores for final probability
            # Anomaly score contributes to bot probability
            if anomaly_score < self.anomaly_threshold:
                bot_probability = min(1.0, bot_probability + 0.2)
            
            # Calculate confidence based on prediction certainty
            confidence = abs(bot_probability - 0.5) * 2  # Convert to 0-1 scale
            confidence = min(0.95, max(0.1, confidence))  # Clamp to reasonable range
            
            return float(bot_probability), float(confidence)
            
        except Exception as e:
            logger.error(f"Error predicting bot probability: {e}")
            return 0.5, 0.1
    
    def _features_to_array(self, features: Dict[str, Any]) -> Optional[np.ndarray]:
        """Convert feature dictionary to numpy array.
        
        Args:
            features: Feature dictionary
            
        Returns:
            Numpy array of feature values
        """
        try:
            # Define expected feature order
            expected_features = [
                'avg_posts_per_day',
                'posting_time_variance',
                'weekend_activity_ratio',
                'duplicate_content_ratio',
                'avg_content_length',
                'hashtag_usage_frequency',
                'mention_usage_frequency',
                'avg_likes_per_post',
                'avg_shares_per_post',
                'engagement_consistency',
                'follower_following_ratio',
                'mutual_connections_ratio',
                'network_clustering_coefficient',
                'account_age_days',
                'activity_burst_frequency'
            ]
            
            # Extract values in expected order
            feature_values = []
            for feature_name in expected_features:
                value = features.get(feature_name, 0.0)
                # Handle potential None values
                if value is None:
                    value = 0.0
                feature_values.append(float(value))
            
            return np.array(feature_values)
            
        except Exception as e:
            logger.error(f"Error converting features to array: {e}")
            return None
    
    async def _detect_risk_indicators(
        self,
        features: Dict[str, Any],
        user_data: Dict[str, Any]
    ) -> List[str]:
        """Detect risk indicators based on features and user data.
        
        Args:
            features: Extracted behavioral features
            user_data: Original user data
            
        Returns:
            List of detected risk indicators
        """
        try:
            risk_indicators = []
            
            # Check posting frequency
            avg_posts_per_day = features.get('avg_posts_per_day', 0)
            if avg_posts_per_day > 50:
                risk_indicators.append('extremely_high_posting_frequency')
            elif avg_posts_per_day > 20:
                risk_indicators.append('high_posting_frequency')
            
            # Check content diversity
            duplicate_ratio = features.get('duplicate_content_ratio', 0)
            if duplicate_ratio > 0.8:
                risk_indicators.append('identical_content_repetition')
            elif duplicate_ratio > 0.5:
                risk_indicators.append('low_content_diversity')
            
            # Check account age
            account_age_days = features.get('account_age_days', 0)
            if account_age_days < 30:
                risk_indicators.append('suspicious_account_age')
            
            # Check engagement patterns
            engagement_consistency = features.get('engagement_consistency', 0)
            if engagement_consistency < 0.2:
                risk_indicators.append('abnormal_engagement_patterns')
            elif engagement_consistency < 0.4:
                risk_indicators.append('unusual_activity_patterns')
            
            # Check network patterns
            clustering_coefficient = features.get('network_clustering_coefficient', 0)
            if clustering_coefficient > 0.8:
                risk_indicators.append('coordinated_behavior_detected')
            elif clustering_coefficient > 0.6:
                risk_indicators.append('suspicious_network_connections')
            
            # Check temporal patterns
            time_variance = features.get('posting_time_variance', 0)
            if time_variance < 0.1:
                risk_indicators.append('automated_response_patterns')
            
            return risk_indicators
            
        except Exception as e:
            logger.error(f"Error detecting risk indicators: {e}")
            return []
    
    async def detect_coordinated_behavior(
        self,
        user_group: List[Dict[str, Any]],
        time_window_hours: float = 24.0
    ) -> Dict[str, Any]:
        """Detect coordinated behavior among a group of users.
        
        Args:
            user_group: List of user data dictionaries
            time_window_hours: Time window for coordination analysis
            
        Returns:
            Coordination analysis results
        """
        try:
            if len(user_group) < 2:
                return {"coordination_detected": False, "coordination_score": 0.0}
            
            # Extract features for all users
            user_features = []
            for user_data in user_group:
                features = await self._extract_behavioral_features(user_data, True)
                user_features.append(features)
            
            # Analyze coordination patterns
            coordination_score = await self._calculate_coordination_score(user_features)
            
            # Detect specific coordination patterns
            patterns = await self._detect_coordination_patterns(user_group, time_window_hours)
            
            return {
                "coordination_detected": coordination_score > 0.6,
                "coordination_score": coordination_score,
                "patterns_detected": patterns,
                "user_count": len(user_group),
                "analysis_timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error detecting coordinated behavior: {e}")
            return {"coordination_detected": False, "error": str(e)}
    
    async def _calculate_coordination_score(
        self,
        user_features: List[Dict[str, Any]]
    ) -> float:
        """Calculate coordination score based on user features similarity.
        
        Args:
            user_features: List of user feature dictionaries
            
        Returns:
            Coordination score between 0.0 and 1.0
        """
        try:
            if len(user_features) < 2:
                return 0.0
            
            # Convert features to arrays
            feature_arrays = []
            for features in user_features:
                feature_array = self._features_to_array(features)
                if feature_array is not None:
                    feature_arrays.append(feature_array)
            
            if len(feature_arrays) < 2:
                return 0.0
            
            # Calculate pairwise similarities
            similarities = []
            for i in range(len(feature_arrays)):
                for j in range(i + 1, len(feature_arrays)):
                    # Calculate cosine similarity
                    similarity = np.dot(feature_arrays[i], feature_arrays[j]) / (
                        np.linalg.norm(feature_arrays[i]) * np.linalg.norm(feature_arrays[j])
                    )
                    similarities.append(similarity)
            
            # Return average similarity as coordination score
            return float(np.mean(similarities)) if similarities else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating coordination score: {e}")
            return 0.0
    
    async def _detect_coordination_patterns(
        self,
        user_group: List[Dict[str, Any]],
        time_window_hours: float
    ) -> List[str]:
        """Detect specific coordination patterns.
        
        Args:
            user_group: List of user data
            time_window_hours: Time window for analysis
            
        Returns:
            List of detected coordination patterns
        """
        try:
            patterns = []
            
            # Check for synchronized posting
            if await self._detect_synchronized_posting(user_group, time_window_hours):
                patterns.append("synchronized_posting")
            
            # Check for content amplification
            if await self._detect_content_amplification(user_group):
                patterns.append("content_amplification")
            
            # Check for similar behavioral patterns
            if await self._detect_similar_behavior_patterns(user_group):
                patterns.append("similar_behavior_patterns")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting coordination patterns: {e}")
            return []
    
    async def _detect_synchronized_posting(
        self,
        user_group: List[Dict[str, Any]],
        time_window_hours: float
    ) -> bool:
        """Detect synchronized posting patterns.
        
        Args:
            user_group: List of user data
            time_window_hours: Time window for synchronization
            
        Returns:
            True if synchronized posting is detected
        """
        try:
            # This is a simplified implementation
            # In production, this would analyze actual posting timestamps
            
            # Check if users have similar posting frequencies
            posting_frequencies = []
            for user_data in user_group:
                freq = user_data.get('avg_posts_per_day', 0)
                posting_frequencies.append(freq)
            
            if len(posting_frequencies) < 2:
                return False
            
            # Calculate coefficient of variation
            mean_freq = np.mean(posting_frequencies)
            std_freq = np.std(posting_frequencies)
            
            if mean_freq == 0:
                return False
            
            cv = std_freq / mean_freq
            
            # Low coefficient of variation indicates similar posting patterns
            return cv < 0.3
            
        except Exception as e:
            logger.error(f"Error detecting synchronized posting: {e}")
            return False
    
    async def _detect_content_amplification(self, user_group: List[Dict[str, Any]]) -> bool:
        """Detect content amplification patterns.
        
        Args:
            user_group: List of user data
            
        Returns:
            True if content amplification is detected
        """
        try:
            # Check for high duplicate content ratios across users
            duplicate_ratios = []
            for user_data in user_group:
                ratio = user_data.get('duplicate_content_ratio', 0)
                duplicate_ratios.append(ratio)
            
            if not duplicate_ratios:
                return False
            
            # High average duplicate ratio indicates amplification
            avg_duplicate_ratio = np.mean(duplicate_ratios)
            return avg_duplicate_ratio > 0.6
            
        except Exception as e:
            logger.error(f"Error detecting content amplification: {e}")
            return False
    
    async def _detect_similar_behavior_patterns(self, user_group: List[Dict[str, Any]]) -> bool:
        """Detect similar behavioral patterns across users.
        
        Args:
            user_group: List of user data
            
        Returns:
            True if similar behavior patterns are detected
        """
        try:
            # Extract key behavioral metrics
            behavior_metrics = []
            for user_data in user_group:
                metrics = [
                    user_data.get('avg_posts_per_day', 0),
                    user_data.get('hashtag_usage_frequency', 0),
                    user_data.get('mention_usage_frequency', 0),
                    user_data.get('engagement_consistency', 0)
                ]
                behavior_metrics.append(metrics)
            
            if len(behavior_metrics) < 2:
                return False
            
            # Calculate pairwise correlations
            correlations = []
            for i in range(len(behavior_metrics)):
                for j in range(i + 1, len(behavior_metrics)):
                    correlation = np.corrcoef(behavior_metrics[i], behavior_metrics[j])[0, 1]
                    if not np.isnan(correlation):
                        correlations.append(correlation)
            
            if not correlations:
                return False
            
            # High average correlation indicates similar behavior
            avg_correlation = np.mean(correlations)
            return avg_correlation > 0.7
            
        except Exception as e:
            logger.error(f"Error detecting similar behavior patterns: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and performance metrics.
        
        Returns:
            Dictionary with model information
        """
        avg_processing_time = (
            self.total_processing_time / self.total_analyses
            if self.total_analyses > 0 else 0.0
        )
        
        return {
            "model_name": self.model_path,
            "model_version": self.model_version,
            "total_analyses": self.total_analyses,
            "average_processing_time_ms": avg_processing_time,
            "bot_threshold": self.bot_threshold,
            "anomaly_threshold": self.anomaly_threshold,
            "classifier_type": type(self.classifier).__name__ if self.classifier else None,
            "feature_extractors": list(self.feature_extractors.keys())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the bot detector.
        
        Returns:
            Health check results
        """
        try:
            # Test with sample data
            test_user_data = {
                'avg_posts_per_day': 5.0,
                'duplicate_content_ratio': 0.2,
                'account_age_days': 365,
                'engagement_consistency': 0.7
            }
            
            result = await self.analyze_user_behavior(
                "test_user", "test_platform", test_user_data, False
            )
            
            return {
                "status": "healthy",
                "classifier_loaded": self.classifier is not None,
                "scaler_loaded": self.scaler is not None,
                "anomaly_detector_loaded": self.anomaly_detector is not None,
                "feature_extractors_loaded": len(self.feature_extractors) > 0,
                "test_analysis_successful": result is not None
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "classifier_loaded": self.classifier is not None,
                "scaler_loaded": self.scaler is not None
            }


# Feature extractor classes
class TemporalFeatureExtractor:
    """Extract temporal behavioral features for automation detection."""
    
    def __init__(self):
        """Initialize temporal feature extractor."""
        self.time_bins = 24  # Hours in a day
        self.day_bins = 7    # Days in a week
    
    async def extract(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract comprehensive temporal features from user data."""
        try:
            features = {}
            
            # Get post timestamps
            posts = user_data.get('posts', [])
            timestamps = []
            
            for post in posts:
                if isinstance(post, dict) and 'timestamp' in post:
                    timestamp = post['timestamp']
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamps.append(timestamp)
            
            if not timestamps:
                return self._get_default_temporal_features(user_data)
            
            # Basic posting frequency
            if len(timestamps) > 1:
                time_span = (max(timestamps) - min(timestamps)).total_seconds() / 86400  # days
                features['avg_posts_per_day'] = len(timestamps) / max(time_span, 1)
            else:
                features['avg_posts_per_day'] = user_data.get('avg_posts_per_day', 0.0)
            
            # Temporal pattern analysis
            features.update(await self._analyze_posting_patterns(timestamps))
            features.update(await self._analyze_automation_indicators(timestamps))
            features.update(await self._analyze_activity_bursts(timestamps))
            
            # Account age
            account_created = user_data.get('account_created')
            if account_created:
                if isinstance(account_created, str):
                    account_created = datetime.fromisoformat(account_created.replace('Z', '+00:00'))
                # Make datetime.utcnow() timezone-aware for comparison
                now = datetime.utcnow().replace(tzinfo=account_created.tzinfo)
                account_age = (now - account_created).days
                features['account_age_days'] = float(max(account_age, 0))
            else:
                features['account_age_days'] = 365.0  # Default to 1 year
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting temporal features: {e}")
            return self._get_default_temporal_features(user_data)
    
    def _get_default_temporal_features(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Get default temporal features when post data is unavailable."""
        return {
            'avg_posts_per_day': user_data.get('avg_posts_per_day', 0.0),
            'posting_time_variance': 0.5,
            'weekend_activity_ratio': 0.3,
            'activity_burst_frequency': 0.1,
            'hourly_posting_entropy': 0.8,
            'daily_posting_entropy': 0.9,
            'inter_post_time_variance': 0.5,
            'night_posting_ratio': 0.2,
            'regular_interval_score': 0.1,
            'account_age_days': 365.0
        }
    
    async def _analyze_posting_patterns(self, timestamps: List[datetime]) -> Dict[str, float]:
        """Analyze posting time patterns for bot indicators."""
        if len(timestamps) < 2:
            return {
                'posting_time_variance': 0.5,
                'weekend_activity_ratio': 0.3,
                'hourly_posting_entropy': 0.8,
                'daily_posting_entropy': 0.9,
                'night_posting_ratio': 0.2
            }
        
        # Extract hours and days
        hours = [ts.hour for ts in timestamps]
        days = [ts.weekday() for ts in timestamps]  # 0=Monday, 6=Sunday
        
        # Calculate hourly distribution entropy
        hour_counts = np.bincount(hours, minlength=24)
        hour_probs = hour_counts / len(timestamps)
        hourly_entropy = -np.sum(hour_probs * np.log2(hour_probs + 1e-10))
        hourly_posting_entropy = hourly_entropy / np.log2(24)  # Normalize
        
        # Calculate daily distribution entropy
        day_counts = np.bincount(days, minlength=7)
        day_probs = day_counts / len(timestamps)
        daily_entropy = -np.sum(day_probs * np.log2(day_probs + 1e-10))
        daily_posting_entropy = daily_entropy / np.log2(7)  # Normalize
        
        # Weekend vs weekday activity
        weekend_posts = sum(1 for day in days if day >= 5)  # Saturday=5, Sunday=6
        weekend_activity_ratio = weekend_posts / len(timestamps)
        
        # Night posting (11 PM to 6 AM)
        night_posts = sum(1 for hour in hours if hour >= 23 or hour <= 6)
        night_posting_ratio = night_posts / len(timestamps)
        
        # Time variance
        hour_variance = np.var(hours) / 144  # Normalize by max variance (12^2)
        
        return {
            'posting_time_variance': float(hour_variance),
            'weekend_activity_ratio': float(weekend_activity_ratio),
            'hourly_posting_entropy': float(hourly_posting_entropy),
            'daily_posting_entropy': float(daily_posting_entropy),
            'night_posting_ratio': float(night_posting_ratio)
        }
    
    async def _analyze_automation_indicators(self, timestamps: List[datetime]) -> Dict[str, float]:
        """Analyze indicators of automated posting behavior."""
        if len(timestamps) < 3:
            return {
                'inter_post_time_variance': 0.5,
                'regular_interval_score': 0.1
            }
        
        # Calculate inter-post time intervals
        sorted_timestamps = sorted(timestamps)
        intervals = []
        for i in range(1, len(sorted_timestamps)):
            interval = (sorted_timestamps[i] - sorted_timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        # Inter-post time variance (low variance indicates automation)
        if len(intervals) > 1:
            interval_variance = np.var(intervals)
            max_variance = np.var([0, 86400 * 7])  # Week variance as reference
            inter_post_time_variance = min(interval_variance / max_variance, 1.0)
        else:
            inter_post_time_variance = 0.5
        
        # Regular interval detection
        regular_interval_score = await self._detect_regular_intervals(intervals)
        
        return {
            'inter_post_time_variance': float(inter_post_time_variance),
            'regular_interval_score': float(regular_interval_score)
        }
    
    async def _detect_regular_intervals(self, intervals: List[float]) -> float:
        """Detect if posting follows regular intervals (automation indicator)."""
        if len(intervals) < 5:
            return 0.1
        
        # Common automation intervals (in seconds)
        common_intervals = [
            60,      # 1 minute
            300,     # 5 minutes
            600,     # 10 minutes
            1800,    # 30 minutes
            3600,    # 1 hour
            7200,    # 2 hours
            21600,   # 6 hours
            43200,   # 12 hours
            86400    # 24 hours
        ]
        
        max_score = 0.0
        for target_interval in common_intervals:
            # Check how many intervals are close to this target
            close_intervals = sum(
                1 for interval in intervals 
                if abs(interval - target_interval) < target_interval * 0.1
            )
            score = close_intervals / len(intervals)
            max_score = max(max_score, score)
        
        return max_score
    
    async def _analyze_activity_bursts(self, timestamps: List[datetime]) -> Dict[str, float]:
        """Analyze activity burst patterns."""
        if len(timestamps) < 5:
            return {'activity_burst_frequency': 0.1}
        
        # Group timestamps by hour
        sorted_timestamps = sorted(timestamps)
        hourly_groups = {}
        
        for ts in sorted_timestamps:
            hour_key = ts.replace(minute=0, second=0, microsecond=0)
            if hour_key not in hourly_groups:
                hourly_groups[hour_key] = 0
            hourly_groups[hour_key] += 1
        
        # Calculate burst frequency (hours with unusually high activity)
        post_counts = list(hourly_groups.values())
        if len(post_counts) > 1:
            mean_posts = np.mean(post_counts)
            std_posts = np.std(post_counts)
            
            if std_posts > 0:
                # Count hours with activity > mean + 2*std
                burst_threshold = mean_posts + 2 * std_posts
                burst_hours = sum(1 for count in post_counts if count > burst_threshold)
                activity_burst_frequency = burst_hours / len(hourly_groups)
            else:
                activity_burst_frequency = 0.0
        else:
            activity_burst_frequency = 0.1
        
        return {'activity_burst_frequency': float(activity_burst_frequency)}


class ContentFeatureExtractor:
    """Extract content-based behavioral features for bot detection."""
    
    def __init__(self):
        """Initialize content feature extractor."""
        self.min_similarity_threshold = 0.8
        self.content_hash_cache = {}
    
    async def extract(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract comprehensive content features from user data."""
        try:
            features = {}
            
            # Get posts content
            posts = user_data.get('posts', [])
            if not posts:
                return self._get_default_content_features(user_data)
            
            # Extract content texts
            contents = []
            for post in posts:
                if isinstance(post, dict) and 'content' in post:
                    content = post['content']
                    if content and isinstance(content, str):
                        contents.append(content.strip())
            
            if not contents:
                return self._get_default_content_features(user_data)
            
            # Analyze content patterns
            features.update(await self._analyze_content_diversity(contents))
            features.update(await self._analyze_content_structure(contents))
            features.update(await self._analyze_linguistic_patterns(contents))
            features.update(await self._analyze_hashtag_mention_patterns(posts))
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting content features: {e}")
            return self._get_default_content_features(user_data)
    
    def _get_default_content_features(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Get default content features when post data is unavailable."""
        return {
            'duplicate_content_ratio': user_data.get('duplicate_content_ratio', 0.0),
            'avg_content_length': user_data.get('avg_content_length', 100.0),
            'hashtag_usage_frequency': user_data.get('hashtag_usage_frequency', 0.2),
            'mention_usage_frequency': user_data.get('mention_usage_frequency', 0.1),
            'content_length_variance': 0.5,
            'unique_word_ratio': 0.7,
            'repetitive_phrase_score': 0.1,
            'url_sharing_frequency': 0.2,
            'emoji_usage_frequency': 0.3,
            'caps_lock_frequency': 0.1
        }
    
    async def _analyze_content_diversity(self, contents: List[str]) -> Dict[str, float]:
        """Analyze content diversity and duplication patterns."""
        if len(contents) < 2:
            return {
                'duplicate_content_ratio': 0.0,
                'unique_word_ratio': 0.7,
                'repetitive_phrase_score': 0.1
            }
        
        # Calculate exact duplicates
        content_counts = {}
        for content in contents:
            normalized = content.lower().strip()
            content_counts[normalized] = content_counts.get(normalized, 0) + 1
        
        duplicate_count = sum(count - 1 for count in content_counts.values() if count > 1)
        duplicate_content_ratio = duplicate_count / len(contents)
        
        # Calculate unique word ratio
        all_words = set()
        total_words = 0
        
        for content in contents:
            words = content.lower().split()
            all_words.update(words)
            total_words += len(words)
        
        unique_word_ratio = len(all_words) / max(total_words, 1)
        
        # Detect repetitive phrases
        repetitive_phrase_score = await self._detect_repetitive_phrases(contents)
        
        return {
            'duplicate_content_ratio': float(duplicate_content_ratio),
            'unique_word_ratio': float(min(unique_word_ratio, 1.0)),
            'repetitive_phrase_score': float(repetitive_phrase_score)
        }
    
    async def _detect_repetitive_phrases(self, contents: List[str]) -> float:
        """Detect repetitive phrases across content."""
        if len(contents) < 3:
            return 0.1
        
        # Extract 3-word phrases
        phrase_counts = {}
        total_phrases = 0
        
        for content in contents:
            words = content.lower().split()
            for i in range(len(words) - 2):
                phrase = ' '.join(words[i:i+3])
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
                total_phrases += 1
        
        if total_phrases == 0:
            return 0.1
        
        # Calculate repetition score
        repeated_phrases = sum(count - 1 for count in phrase_counts.values() if count > 1)
        repetitive_score = repeated_phrases / total_phrases
        
        return min(repetitive_score, 1.0)
    
    async def _analyze_content_structure(self, contents: List[str]) -> Dict[str, float]:
        """Analyze structural patterns in content."""
        if not contents:
            return {
                'avg_content_length': 100.0,
                'content_length_variance': 0.5,
                'url_sharing_frequency': 0.2,
                'caps_lock_frequency': 0.1
            }
        
        # Content length analysis
        lengths = [len(content) for content in contents]
        avg_content_length = np.mean(lengths)
        length_variance = np.var(lengths) / (avg_content_length ** 2) if avg_content_length > 0 else 0
        
        # URL sharing frequency
        url_count = sum(1 for content in contents if 'http' in content.lower())
        url_sharing_frequency = url_count / len(contents)
        
        # Caps lock usage (potential spam indicator)
        caps_posts = sum(1 for content in contents if self._has_excessive_caps(content))
        caps_lock_frequency = caps_posts / len(contents)
        
        return {
            'avg_content_length': float(avg_content_length),
            'content_length_variance': float(min(length_variance, 1.0)),
            'url_sharing_frequency': float(url_sharing_frequency),
            'caps_lock_frequency': float(caps_lock_frequency)
        }
    
    def _has_excessive_caps(self, content: str) -> bool:
        """Check if content has excessive capital letters."""
        if len(content) < 10:
            return False
        
        caps_count = sum(1 for c in content if c.isupper())
        caps_ratio = caps_count / len(content)
        return caps_ratio > 0.3  # More than 30% caps
    
    async def _analyze_linguistic_patterns(self, contents: List[str]) -> Dict[str, float]:
        """Analyze linguistic patterns that may indicate automation."""
        if not contents:
            return {'emoji_usage_frequency': 0.3}
        
        # Emoji usage frequency
        emoji_posts = 0
        for content in contents:
            # Simple emoji detection (Unicode ranges)
            if any(ord(char) > 127 for char in content):
                # More sophisticated emoji detection could be added
                emoji_posts += 1
        
        emoji_usage_frequency = emoji_posts / len(contents)
        
        return {
            'emoji_usage_frequency': float(emoji_usage_frequency)
        }
    
    async def _analyze_hashtag_mention_patterns(self, posts: List[Dict]) -> Dict[str, float]:
        """Analyze hashtag and mention usage patterns."""
        if not posts:
            return {
                'hashtag_usage_frequency': 0.2,
                'mention_usage_frequency': 0.1
            }
        
        hashtag_posts = 0
        mention_posts = 0
        
        for post in posts:
            if isinstance(post, dict):
                # Check hashtags
                hashtags = post.get('hashtags', [])
                if hashtags and len(hashtags) > 0:
                    hashtag_posts += 1
                
                # Check mentions
                mentions = post.get('mentions', [])
                if mentions and len(mentions) > 0:
                    mention_posts += 1
                
                # Also check content for # and @ symbols
                content = post.get('content', '')
                if isinstance(content, str):
                    if '#' in content:
                        hashtag_posts += 1
                    if '@' in content:
                        mention_posts += 1
        
        hashtag_usage_frequency = hashtag_posts / len(posts)
        mention_usage_frequency = mention_posts / len(posts)
        
        return {
            'hashtag_usage_frequency': float(min(hashtag_usage_frequency, 1.0)),
            'mention_usage_frequency': float(min(mention_usage_frequency, 1.0))
        }


class NetworkFeatureExtractor:
    """Extract network-based behavioral features for coordinated behavior detection."""
    
    def __init__(self):
        """Initialize network feature extractor."""
        self.graph_cache = {}
        self.connection_cache = {}
    
    async def extract(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract comprehensive network features from user data."""
        try:
            features = {}
            
            # Basic network metrics
            features.update(await self._analyze_basic_network_metrics(user_data))
            
            # Connection patterns
            features.update(await self._analyze_connection_patterns(user_data))
            
            # Interaction patterns
            features.update(await self._analyze_interaction_patterns(user_data))
            
            # Suspicious network indicators
            features.update(await self._analyze_suspicious_patterns(user_data))
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting network features: {e}")
            return self._get_default_network_features(user_data)
    
    def _get_default_network_features(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Get default network features when data is unavailable."""
        followers_count = user_data.get('followers_count', 0)
        following_count = user_data.get('following_count', 0)
        
        return {
            'follower_following_ratio': float(followers_count / max(following_count, 1)),
            'mutual_connections_ratio': user_data.get('mutual_connections_ratio', 0.1),
            'network_clustering_coefficient': user_data.get('network_clustering_coefficient', 0.2),
            'interaction_diversity_score': 0.5,
            'reciprocal_connection_ratio': 0.3,
            'suspicious_connection_ratio': 0.1,
            'new_account_connection_ratio': 0.2,
            'bot_connection_ratio': 0.05
        }
    
    async def _analyze_basic_network_metrics(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze basic network structure metrics."""
        followers_count = user_data.get('followers_count', 0)
        following_count = user_data.get('following_count', 0)
        posts_count = user_data.get('posts_count', 0)
        
        # Follower-following ratio (bots often have unusual ratios)
        if following_count > 0:
            follower_following_ratio = followers_count / following_count
        else:
            follower_following_ratio = followers_count
        
        # Normalize extreme ratios
        follower_following_ratio = min(follower_following_ratio, 100.0)
        
        return {
            'follower_following_ratio': float(follower_following_ratio)
        }
    
    async def _analyze_connection_patterns(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze connection patterns for bot indicators."""
        # Get connection data
        connections = user_data.get('connections', [])
        connected_users = user_data.get('connected_users', [])
        
        if not connections and not connected_users:
            return {
                'mutual_connections_ratio': 0.1,
                'reciprocal_connection_ratio': 0.3,
                'network_clustering_coefficient': 0.2
            }
        
        # Analyze mutual connections
        mutual_connections_ratio = await self._calculate_mutual_connections_ratio(user_data)
        
        # Analyze reciprocal connections
        reciprocal_connection_ratio = await self._calculate_reciprocal_ratio(user_data)
        
        # Calculate clustering coefficient
        clustering_coefficient = await self._calculate_clustering_coefficient(user_data)
        
        return {
            'mutual_connections_ratio': float(mutual_connections_ratio),
            'reciprocal_connection_ratio': float(reciprocal_connection_ratio),
            'network_clustering_coefficient': float(clustering_coefficient)
        }
    
    async def _calculate_mutual_connections_ratio(self, user_data: Dict[str, Any]) -> float:
        """Calculate ratio of mutual connections."""
        # This would typically require access to the full network graph
        # For now, use provided data or estimate
        mutual_ratio = user_data.get('mutual_connections_ratio')
        if mutual_ratio is not None:
            return mutual_ratio
        
        # Estimate based on follower/following patterns
        followers_count = user_data.get('followers_count', 0)
        following_count = user_data.get('following_count', 0)
        
        if followers_count == 0 or following_count == 0:
            return 0.0
        
        # Simple heuristic: smaller accounts tend to have higher mutual ratios
        total_connections = followers_count + following_count
        if total_connections < 100:
            return 0.3  # Higher mutual ratio for small accounts
        elif total_connections < 1000:
            return 0.2
        else:
            return 0.1  # Lower mutual ratio for large accounts
    
    async def _calculate_reciprocal_ratio(self, user_data: Dict[str, Any]) -> float:
        """Calculate ratio of reciprocal connections (mutual follows)."""
        followers_count = user_data.get('followers_count', 0)
        following_count = user_data.get('following_count', 0)
        
        if followers_count == 0 or following_count == 0:
            return 0.0
        
        # Estimate reciprocal ratio based on account characteristics
        # Bots often have low reciprocal ratios
        min_connections = min(followers_count, following_count)
        max_connections = max(followers_count, following_count)
        
        if max_connections == 0:
            return 0.0
        
        # Heuristic: reciprocal ratio inversely related to imbalance
        balance_ratio = min_connections / max_connections
        return balance_ratio * 0.5  # Scale to reasonable range
    
    async def _calculate_clustering_coefficient(self, user_data: Dict[str, Any]) -> float:
        """Calculate network clustering coefficient."""
        # This would require full network graph analysis
        # For now, use provided data or estimate
        clustering = user_data.get('network_clustering_coefficient')
        if clustering is not None:
            return clustering
        
        # Estimate based on account characteristics
        followers_count = user_data.get('followers_count', 0)
        following_count = user_data.get('following_count', 0)
        
        # Bots in coordinated networks often have high clustering
        if followers_count < 100 and following_count < 100:
            return 0.4  # Higher clustering for small accounts
        elif followers_count > 10000 or following_count > 10000:
            return 0.1  # Lower clustering for large accounts
        else:
            return 0.2  # Medium clustering
    
    async def _analyze_interaction_patterns(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze interaction patterns for bot indicators."""
        posts = user_data.get('posts', [])
        
        if not posts:
            return {'interaction_diversity_score': 0.5}
        
        # Analyze interaction diversity
        interaction_targets = set()
        total_interactions = 0
        
        for post in posts:
            if isinstance(post, dict):
                # Count mentions as interactions
                mentions = post.get('mentions', [])
                for mention in mentions:
                    interaction_targets.add(mention)
                    total_interactions += 1
                
                # Count replies as interactions
                if post.get('parent_post_id'):
                    total_interactions += 1
        
        # Calculate diversity score
        if total_interactions > 0:
            interaction_diversity_score = len(interaction_targets) / total_interactions
        else:
            interaction_diversity_score = 0.5
        
        return {
            'interaction_diversity_score': float(min(interaction_diversity_score, 1.0))
        }
    
    async def _analyze_suspicious_patterns(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze patterns that indicate suspicious network behavior."""
        # Get connection metadata
        suspicious_connections = user_data.get('suspicious_connections', [])
        connected_users = user_data.get('connected_users', [])
        
        total_connections = len(connected_users) if connected_users else 1
        
        # Suspicious connection ratio
        suspicious_connection_ratio = len(suspicious_connections) / total_connections
        
        # Estimate new account connections (bots often connect to new accounts)
        new_account_connection_ratio = await self._estimate_new_account_connections(user_data)
        
        # Estimate bot connections (bots often connect to other bots)
        bot_connection_ratio = await self._estimate_bot_connections(user_data)
        
        return {
            'suspicious_connection_ratio': float(suspicious_connection_ratio),
            'new_account_connection_ratio': float(new_account_connection_ratio),
            'bot_connection_ratio': float(bot_connection_ratio)
        }
    
    async def _estimate_new_account_connections(self, user_data: Dict[str, Any]) -> float:
        """Estimate ratio of connections to new accounts."""
        # This would require analyzing connected accounts' creation dates
        # For now, provide reasonable estimates based on account characteristics
        
        account_age_days = user_data.get('account_age_days', 365)
        
        # Newer accounts tend to connect more with other new accounts
        if account_age_days < 30:
            return 0.4  # High ratio for very new accounts
        elif account_age_days < 180:
            return 0.2  # Medium ratio for somewhat new accounts
        else:
            return 0.1  # Low ratio for established accounts
    
    async def _estimate_bot_connections(self, user_data: Dict[str, Any]) -> float:
        """Estimate ratio of connections to other bots."""
        # This would require bot detection results for connected accounts
        # For now, provide conservative estimates
        
        followers_count = user_data.get('followers_count', 0)
        following_count = user_data.get('following_count', 0)
        
        # Accounts with unusual follower patterns may connect to more bots
        if followers_count == 0 and following_count > 100:
            return 0.15  # Higher bot connection ratio
        elif followers_count > 10000 and following_count < 100:
            return 0.02  # Lower bot connection ratio
        else:
            return 0.05  # Default estimate


class BehavioralFeatureExtractor:
    """Extract general behavioral features for bot detection."""
    
    def __init__(self):
        """Initialize behavioral feature extractor."""
        self.engagement_cache = {}
    
    async def extract(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract comprehensive behavioral features from user data."""
        try:
            features = {}
            
            # Engagement pattern analysis
            features.update(await self._analyze_engagement_patterns(user_data))
            
            # Response behavior analysis
            features.update(await self._analyze_response_behavior(user_data))
            
            # Activity consistency analysis
            features.update(await self._analyze_activity_consistency(user_data))
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting behavioral features: {e}")
            return self._get_default_behavioral_features(user_data)
    
    def _get_default_behavioral_features(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Get default behavioral features when data is unavailable."""
        return {
            'avg_likes_per_post': user_data.get('avg_likes_per_post', 5.0),
            'avg_shares_per_post': user_data.get('avg_shares_per_post', 1.0),
            'engagement_consistency': user_data.get('engagement_consistency', 0.5),
            'response_time_variance': 0.5,
            'engagement_rate_variance': 0.3,
            'activity_consistency_score': 0.6,
            'human_interaction_ratio': 0.7
        }
    
    async def _analyze_engagement_patterns(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze engagement patterns for bot indicators."""
        posts = user_data.get('posts', [])
        
        if not posts:
            return {
                'avg_likes_per_post': user_data.get('avg_likes_per_post', 5.0),
                'avg_shares_per_post': user_data.get('avg_shares_per_post', 1.0),
                'engagement_consistency': user_data.get('engagement_consistency', 0.5),
                'engagement_rate_variance': 0.3
            }
        
        # Extract engagement metrics
        likes_counts = []
        shares_counts = []
        comments_counts = []
        
        for post in posts:
            if isinstance(post, dict) and 'metrics' in post:
                metrics = post['metrics']
                if isinstance(metrics, dict):
                    likes_counts.append(metrics.get('likes', 0))
                    shares_counts.append(metrics.get('shares', 0))
                    comments_counts.append(metrics.get('comments', 0))
        
        if not likes_counts:
            return self._get_default_behavioral_features(user_data)
        
        # Calculate averages
        avg_likes_per_post = np.mean(likes_counts)
        avg_shares_per_post = np.mean(shares_counts)
        avg_comments_per_post = np.mean(comments_counts)
        
        # Calculate engagement consistency
        engagement_consistency = await self._calculate_engagement_consistency(
            likes_counts, shares_counts, comments_counts
        )
        
        # Calculate engagement rate variance
        total_engagement = [l + s + c for l, s, c in zip(likes_counts, shares_counts, comments_counts)]
        if len(total_engagement) > 1:
            engagement_variance = np.var(total_engagement)
            mean_engagement = np.mean(total_engagement)
            engagement_rate_variance = engagement_variance / (mean_engagement ** 2) if mean_engagement > 0 else 0
        else:
            engagement_rate_variance = 0.3
        
        return {
            'avg_likes_per_post': float(avg_likes_per_post),
            'avg_shares_per_post': float(avg_shares_per_post),
            'engagement_consistency': float(engagement_consistency),
            'engagement_rate_variance': float(min(engagement_rate_variance, 1.0))
        }
    
    async def _calculate_engagement_consistency(
        self, 
        likes: List[int], 
        shares: List[int], 
        comments: List[int]
    ) -> float:
        """Calculate consistency of engagement patterns."""
        if len(likes) < 2:
            return 0.5
        
        # Calculate coefficient of variation for each engagement type
        def cv(values):
            mean_val = np.mean(values)
            if mean_val == 0:
                return 0
            return np.std(values) / mean_val
        
        likes_cv = cv(likes)
        shares_cv = cv(shares)
        comments_cv = cv(comments)
        
        # Average coefficient of variation (lower = more consistent)
        avg_cv = np.mean([likes_cv, shares_cv, comments_cv])
        
        # Convert to consistency score (higher = more consistent)
        # Bots often have very consistent or very inconsistent engagement
        consistency_score = 1.0 / (1.0 + avg_cv)
        
        return min(consistency_score, 1.0)
    
    async def _analyze_response_behavior(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze response behavior patterns."""
        posts = user_data.get('posts', [])
        
        if not posts:
            return {
                'response_time_variance': 0.5,
                'human_interaction_ratio': 0.7
            }
        
        # Analyze response times (if available)
        response_times = []
        human_interactions = 0
        total_interactions = 0
        
        for post in posts:
            if isinstance(post, dict):
                # Check if this is a response to another post
                if post.get('parent_post_id'):
                    total_interactions += 1
                    
                    # Check for human-like interaction patterns
                    content = post.get('content', '')
                    if self._is_human_like_response(content):
                        human_interactions += 1
                
                # Extract response time if available
                response_time = post.get('response_time_seconds')
                if response_time is not None:
                    response_times.append(response_time)
        
        # Calculate response time variance
        if len(response_times) > 1:
            response_time_variance = np.var(response_times) / (np.mean(response_times) ** 2)
            response_time_variance = min(response_time_variance, 1.0)
        else:
            response_time_variance = 0.5
        
        # Calculate human interaction ratio
        if total_interactions > 0:
            human_interaction_ratio = human_interactions / total_interactions
        else:
            human_interaction_ratio = 0.7  # Default assumption
        
        return {
            'response_time_variance': float(response_time_variance),
            'human_interaction_ratio': float(human_interaction_ratio)
        }
    
    def _is_human_like_response(self, content: str) -> bool:
        """Check if response content appears human-like."""
        if not content or len(content.strip()) < 3:
            return False
        
        # Human-like indicators
        human_indicators = [
            len(content.split()) > 3,  # More than 3 words
            '?' in content,  # Questions
            '!' in content,  # Exclamations
            any(word in content.lower() for word in ['thanks', 'thank', 'please', 'sorry', 'yes', 'no']),
            not content.isupper(),  # Not all caps
            len(set(content.lower().split())) > 2  # Diverse vocabulary
        ]
        
        # Consider it human-like if it meets at least 2 criteria
        return sum(human_indicators) >= 2
    
    async def _analyze_activity_consistency(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze overall activity consistency patterns."""
        posts = user_data.get('posts', [])
        
        if len(posts) < 5:
            return {'activity_consistency_score': 0.6}
        
        # Analyze posting frequency consistency over time
        timestamps = []
        for post in posts:
            if isinstance(post, dict) and 'timestamp' in post:
                timestamp = post['timestamp']
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamps.append(timestamp)
        
        if len(timestamps) < 5:
            return {'activity_consistency_score': 0.6}
        
        # Calculate daily activity consistency
        daily_activity = {}
        for ts in timestamps:
            date_key = ts.date()
            daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
        
        if len(daily_activity) < 2:
            return {'activity_consistency_score': 0.6}
        
        # Calculate coefficient of variation for daily activity
        daily_counts = list(daily_activity.values())
        mean_daily = np.mean(daily_counts)
        std_daily = np.std(daily_counts)
        
        if mean_daily > 0:
            cv_daily = std_daily / mean_daily
            # Convert to consistency score (lower CV = higher consistency)
            activity_consistency_score = 1.0 / (1.0 + cv_daily)
        else:
            activity_consistency_score = 0.6
        
        return {
            'activity_consistency_score': float(min(activity_consistency_score, 1.0))
        }