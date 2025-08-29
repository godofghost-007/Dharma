"""Test suite for bot detection system."""

import asyncio
import pytest
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app.analysis.bot_detector import (
    BotDetector,
    TemporalFeatureExtractor,
    ContentFeatureExtractor,
    NetworkFeatureExtractor,
    BehavioralFeatureExtractor
)
from app.analysis.bot_model_trainer import BotModelTrainer
from app.models.requests import BotDetectionResponse


class TestBotDetector:
    """Test cases for the BotDetector class."""
    
    @pytest.fixture
    async def bot_detector(self):
        """Create a bot detector instance for testing."""
        detector = BotDetector()
        await detector.initialize()
        return detector
    
    @pytest.fixture
    def sample_human_data(self):
        """Sample data representing a human user."""
        return {
            'user_id': 'human_user_123',
            'platform': 'twitter',
            'followers_count': 500,
            'following_count': 300,
            'posts_count': 150,
            'account_created': '2022-01-15T10:30:00Z',
            'avg_posts_per_day': 2.5,
            'duplicate_content_ratio': 0.1,
            'avg_content_length': 120.0,
            'hashtag_usage_frequency': 0.3,
            'mention_usage_frequency': 0.2,
            'avg_likes_per_post': 8.0,
            'avg_shares_per_post': 2.0,
            'engagement_consistency': 0.6,
            'mutual_connections_ratio': 0.25,
            'network_clustering_coefficient': 0.3,
            'posts': [
                {
                    'content': 'Just had a great coffee this morning! ☕',
                    'timestamp': '2024-01-15T08:30:00Z',
                    'hashtags': [],
                    'mentions': [],
                    'metrics': {'likes': 5, 'shares': 1, 'comments': 2}
                },
                {
                    'content': 'Working on an interesting project today #coding',
                    'timestamp': '2024-01-15T14:20:00Z',
                    'hashtags': ['coding'],
                    'mentions': [],
                    'metrics': {'likes': 12, 'shares': 3, 'comments': 1}
                },
                {
                    'content': 'Thanks @friend for the recommendation!',
                    'timestamp': '2024-01-15T19:45:00Z',
                    'hashtags': [],
                    'mentions': ['friend'],
                    'metrics': {'likes': 8, 'shares': 0, 'comments': 4}
                }
            ]
        }
    
    @pytest.fixture
    def sample_bot_data(self):
        """Sample data representing a bot user."""
        return {
            'user_id': 'bot_user_456',
            'platform': 'twitter',
            'followers_count': 50,
            'following_count': 2000,
            'posts_count': 500,
            'account_created': '2024-01-01T00:00:00Z',
            'avg_posts_per_day': 25.0,
            'duplicate_content_ratio': 0.8,
            'avg_content_length': 80.0,
            'hashtag_usage_frequency': 0.9,
            'mention_usage_frequency': 0.7,
            'avg_likes_per_post': 1.0,
            'avg_shares_per_post': 0.5,
            'engagement_consistency': 0.95,
            'mutual_connections_ratio': 0.05,
            'network_clustering_coefficient': 0.8,
            'posts': [
                {
                    'content': 'Check out this amazing deal! #sale #discount',
                    'timestamp': '2024-01-15T12:00:00Z',
                    'hashtags': ['sale', 'discount'],
                    'mentions': [],
                    'metrics': {'likes': 1, 'shares': 0, 'comments': 0}
                },
                {
                    'content': 'Check out this amazing deal! #sale #discount',
                    'timestamp': '2024-01-15T12:30:00Z',
                    'hashtags': ['sale', 'discount'],
                    'mentions': [],
                    'metrics': {'likes': 1, 'shares': 1, 'comments': 0}
                },
                {
                    'content': 'AMAZING OFFERS HERE! CLICK NOW! #deals',
                    'timestamp': '2024-01-15T13:00:00Z',
                    'hashtags': ['deals'],
                    'mentions': [],
                    'metrics': {'likes': 2, 'shares': 0, 'comments': 0}
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_bot_detector_initialization(self, bot_detector):
        """Test bot detector initialization."""
        assert bot_detector.classifier is not None
        assert bot_detector.scaler is not None
        assert bot_detector.anomaly_detector is not None
        assert len(bot_detector.feature_extractors) == 4
    
    @pytest.mark.asyncio
    async def test_analyze_human_user(self, bot_detector, sample_human_data):
        """Test analysis of human user data."""
        result = await bot_detector.analyze_user_behavior(
            user_id='human_user_123',
            platform='twitter',
            user_data=sample_human_data,
            include_network_analysis=True
        )
        
        assert isinstance(result, BotDetectionResponse)
        assert result.user_id == 'human_user_123'
        assert result.platform == 'twitter'
        assert 0.0 <= result.bot_probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.behavioral_features is not None
        
        # Human users should generally have lower bot probability
        assert result.bot_probability < 0.7  # Reasonable threshold
    
    @pytest.mark.asyncio
    async def test_analyze_bot_user(self, bot_detector, sample_bot_data):
        """Test analysis of bot user data."""
        result = await bot_detector.analyze_user_behavior(
            user_id='bot_user_456',
            platform='twitter',
            user_data=sample_bot_data,
            include_network_analysis=True
        )
        
        assert isinstance(result, BotDetectionResponse)
        assert result.user_id == 'bot_user_456'
        assert result.platform == 'twitter'
        assert 0.0 <= result.bot_probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        
        # Bot users should generally have higher bot probability
        assert result.bot_probability > 0.3  # Reasonable threshold
    
    @pytest.mark.asyncio
    async def test_coordinated_behavior_detection(self, bot_detector, sample_bot_data):
        """Test coordinated behavior detection."""
        # Create multiple similar bot accounts
        bot_group = []
        for i in range(3):
            bot_data = sample_bot_data.copy()
            bot_data['user_id'] = f'bot_user_{i}'
            bot_group.append(bot_data)
        
        result = await bot_detector.detect_coordinated_behavior(
            user_group=bot_group,
            time_window_hours=24.0
        )
        
        assert 'coordination_detected' in result
        assert 'coordination_score' in result
        assert 'patterns_detected' in result
        assert 'user_count' in result
        
        assert result['user_count'] == 3
        assert 0.0 <= result['coordination_score'] <= 1.0
        
        # Similar bot accounts should show coordination
        assert result['coordination_score'] > 0.5
    
    @pytest.mark.asyncio
    async def test_health_check(self, bot_detector):
        """Test bot detector health check."""
        health_result = await bot_detector.health_check()
        
        assert health_result['status'] == 'healthy'
        assert health_result['classifier_loaded'] is True
        assert health_result['scaler_loaded'] is True
        assert health_result['anomaly_detector_loaded'] is True
        assert health_result['test_analysis_successful'] is True
    
    def test_get_model_info(self, bot_detector):
        """Test getting model information."""
        model_info = bot_detector.get_model_info()
        
        assert 'model_name' in model_info
        assert 'model_version' in model_info
        assert 'total_analyses' in model_info
        assert 'classifier_type' in model_info
        assert 'feature_extractors' in model_info
        
        assert len(model_info['feature_extractors']) == 4


class TestTemporalFeatureExtractor:
    """Test cases for temporal feature extraction."""
    
    @pytest.fixture
    def temporal_extractor(self):
        """Create temporal feature extractor."""
        return TemporalFeatureExtractor()
    
    @pytest.fixture
    def sample_posts_with_timestamps(self):
        """Sample posts with varied timestamps."""
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        return [
            {
                'timestamp': base_time.isoformat() + 'Z',
                'content': 'Post 1'
            },
            {
                'timestamp': (base_time + timedelta(hours=2)).isoformat() + 'Z',
                'content': 'Post 2'
            },
            {
                'timestamp': (base_time + timedelta(hours=6)).isoformat() + 'Z',
                'content': 'Post 3'
            },
            {
                'timestamp': (base_time + timedelta(days=1)).isoformat() + 'Z',
                'content': 'Post 4'
            }
        ]
    
    @pytest.mark.asyncio
    async def test_extract_temporal_features(self, temporal_extractor, sample_posts_with_timestamps):
        """Test temporal feature extraction."""
        user_data = {
            'posts': sample_posts_with_timestamps,
            'account_created': '2023-01-15T10:30:00Z'
        }
        
        features = await temporal_extractor.extract(user_data)
        
        # Check that all expected features are present
        expected_features = [
            'avg_posts_per_day',
            'posting_time_variance',
            'weekend_activity_ratio',
            'activity_burst_frequency',
            'hourly_posting_entropy',
            'daily_posting_entropy',
            'inter_post_time_variance',
            'night_posting_ratio',
            'regular_interval_score',
            'account_age_days'
        ]
        
        for feature in expected_features:
            assert feature in features
            assert isinstance(features[feature], (int, float))
            assert features[feature] >= 0  # All features should be non-negative
    
    @pytest.mark.asyncio
    async def test_regular_interval_detection(self, temporal_extractor):
        """Test detection of regular posting intervals."""
        # Create posts with regular 1-hour intervals
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        regular_posts = []
        for i in range(10):
            regular_posts.append({
                'timestamp': (base_time + timedelta(hours=i)).isoformat() + 'Z',
                'content': f'Regular post {i}'
            })
        
        user_data = {'posts': regular_posts}
        features = await temporal_extractor.extract(user_data)
        
        # Regular intervals should be detected
        assert features['regular_interval_score'] > 0.5
    
    @pytest.mark.asyncio
    async def test_empty_posts_handling(self, temporal_extractor):
        """Test handling of empty posts list."""
        user_data = {'posts': []}
        features = await temporal_extractor.extract(user_data)
        
        # Should return default values
        assert 'avg_posts_per_day' in features
        assert features['avg_posts_per_day'] >= 0


class TestContentFeatureExtractor:
    """Test cases for content feature extraction."""
    
    @pytest.fixture
    def content_extractor(self):
        """Create content feature extractor."""
        return ContentFeatureExtractor()
    
    @pytest.fixture
    def duplicate_content_posts(self):
        """Sample posts with duplicate content."""
        return [
            {'content': 'This is a duplicate message'},
            {'content': 'This is a duplicate message'},
            {'content': 'This is a duplicate message'},
            {'content': 'This is a unique message'},
            {'content': 'Another unique message'}
        ]
    
    @pytest.mark.asyncio
    async def test_extract_content_features(self, content_extractor):
        """Test content feature extraction."""
        posts = [
            {
                'content': 'Hello world! This is a test post #testing',
                'hashtags': ['testing'],
                'mentions': []
            },
            {
                'content': 'Another post with @mention and #hashtag',
                'hashtags': ['hashtag'],
                'mentions': ['mention']
            }
        ]
        
        user_data = {'posts': posts}
        features = await content_extractor.extract(user_data)
        
        expected_features = [
            'duplicate_content_ratio',
            'avg_content_length',
            'hashtag_usage_frequency',
            'mention_usage_frequency',
            'content_length_variance',
            'unique_word_ratio',
            'repetitive_phrase_score',
            'url_sharing_frequency',
            'emoji_usage_frequency',
            'caps_lock_frequency'
        ]
        
        for feature in expected_features:
            assert feature in features
            assert isinstance(features[feature], (int, float))
    
    @pytest.mark.asyncio
    async def test_duplicate_content_detection(self, content_extractor, duplicate_content_posts):
        """Test duplicate content detection."""
        user_data = {'posts': duplicate_content_posts}
        features = await content_extractor.extract(user_data)
        
        # Should detect high duplicate ratio (3 out of 5 posts are duplicates)
        assert features['duplicate_content_ratio'] > 0.4
    
    @pytest.mark.asyncio
    async def test_caps_lock_detection(self, content_extractor):
        """Test caps lock detection."""
        posts = [
            {'content': 'THIS IS ALL CAPS CONTENT!!!'},
            {'content': 'This is normal content'},
            {'content': 'ANOTHER CAPS LOCK MESSAGE'}
        ]
        
        user_data = {'posts': posts}
        features = await content_extractor.extract(user_data)
        
        # Should detect caps lock usage
        assert features['caps_lock_frequency'] > 0.5


class TestNetworkFeatureExtractor:
    """Test cases for network feature extraction."""
    
    @pytest.fixture
    def network_extractor(self):
        """Create network feature extractor."""
        return NetworkFeatureExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_network_features(self, network_extractor):
        """Test network feature extraction."""
        user_data = {
            'followers_count': 1000,
            'following_count': 500,
            'connected_users': ['user1', 'user2', 'user3'],
            'suspicious_connections': ['user1']
        }
        
        features = await network_extractor.extract(user_data)
        
        expected_features = [
            'follower_following_ratio',
            'mutual_connections_ratio',
            'network_clustering_coefficient',
            'interaction_diversity_score',
            'reciprocal_connection_ratio',
            'suspicious_connection_ratio',
            'new_account_connection_ratio',
            'bot_connection_ratio'
        ]
        
        for feature in expected_features:
            assert feature in features
            assert isinstance(features[feature], (int, float))
    
    @pytest.mark.asyncio
    async def test_suspicious_connection_ratio(self, network_extractor):
        """Test suspicious connection ratio calculation."""
        user_data = {
            'followers_count': 100,
            'following_count': 100,
            'connected_users': ['user1', 'user2', 'user3', 'user4'],
            'suspicious_connections': ['user1', 'user2']  # 50% suspicious
        }
        
        features = await network_extractor.extract(user_data)
        
        # Should detect high suspicious connection ratio
        assert features['suspicious_connection_ratio'] == 0.5


class TestBehavioralFeatureExtractor:
    """Test cases for behavioral feature extraction."""
    
    @pytest.fixture
    def behavioral_extractor(self):
        """Create behavioral feature extractor."""
        return BehavioralFeatureExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_behavioral_features(self, behavioral_extractor):
        """Test behavioral feature extraction."""
        posts = [
            {
                'metrics': {'likes': 10, 'shares': 2, 'comments': 1},
                'content': 'Thanks for the help!'
            },
            {
                'metrics': {'likes': 8, 'shares': 1, 'comments': 3},
                'content': 'Great question, let me think about it.'
            }
        ]
        
        user_data = {'posts': posts}
        features = await behavioral_extractor.extract(user_data)
        
        expected_features = [
            'avg_likes_per_post',
            'avg_shares_per_post',
            'engagement_consistency',
            'response_time_variance',
            'engagement_rate_variance',
            'activity_consistency_score',
            'human_interaction_ratio'
        ]
        
        for feature in expected_features:
            assert feature in features
            assert isinstance(features[feature], (int, float))
    
    @pytest.mark.asyncio
    async def test_human_interaction_detection(self, behavioral_extractor):
        """Test human interaction detection."""
        posts = [
            {
                'content': 'Thanks for the help!',  # Human-like
                'parent_post_id': 'parent1'
            },
            {
                'content': 'CLICK HERE NOW!!!',  # Bot-like
                'parent_post_id': 'parent2'
            },
            {
                'content': 'Great question, what do you think?',  # Human-like
                'parent_post_id': 'parent3'
            }
        ]
        
        user_data = {'posts': posts}
        features = await behavioral_extractor.extract(user_data)
        
        # Should detect some human interactions
        assert features['human_interaction_ratio'] > 0.5


class TestBotModelTrainer:
    """Test cases for bot model training."""
    
    @pytest.fixture
    def model_trainer(self):
        """Create model trainer."""
        return BotModelTrainer()
    
    @pytest.mark.asyncio
    async def test_generate_synthetic_data(self, model_trainer):
        """Test synthetic data generation."""
        training_data, labels = await model_trainer.generate_synthetic_training_data(
            num_samples=100,
            bot_ratio=0.3
        )
        
        assert len(training_data) == 100
        assert len(labels) == 100
        assert sum(labels) == 30  # 30% bots
        
        # Check that all required features are present
        for sample in training_data:
            for feature_name in model_trainer.feature_names:
                assert feature_name in sample
                assert isinstance(sample[feature_name], (int, float))
    
    @pytest.mark.asyncio
    async def test_model_training(self, model_trainer):
        """Test model training process."""
        # Generate synthetic training data
        training_data, labels = await model_trainer.generate_synthetic_training_data(
            num_samples=200,
            bot_ratio=0.3
        )
        
        # Train models
        results = await model_trainer.train_models(
            training_data=training_data,
            labels=labels,
            validation_split=0.2,
            use_cross_validation=False  # Skip CV for faster testing
        )
        
        assert 'classifier' in results
        assert 'scaler' in results
        assert 'anomaly_detector' in results
        
        # Check classifier results
        classifier_results = results['classifier']
        assert 'validation_accuracy' in classifier_results
        assert 'validation_auc' in classifier_results
        assert 'feature_importance' in classifier_results
        
        # Accuracy should be reasonable for synthetic data
        assert classifier_results['validation_accuracy'] > 0.6
        assert classifier_results['validation_auc'] > 0.6
    
    @pytest.mark.asyncio
    async def test_model_evaluation(self, model_trainer):
        """Test model evaluation."""
        # Generate and train on synthetic data
        training_data, labels = await model_trainer.generate_synthetic_training_data(
            num_samples=150,
            bot_ratio=0.3
        )
        
        await model_trainer.train_models(
            training_data=training_data,
            labels=labels,
            use_cross_validation=False
        )
        
        # Generate test data
        test_data, test_labels = await model_trainer.generate_synthetic_training_data(
            num_samples=50,
            bot_ratio=0.3
        )
        
        # Evaluate models
        evaluation_results = await model_trainer.evaluate_model(test_data, test_labels)
        
        assert 'test_accuracy' in evaluation_results
        assert 'test_auc' in evaluation_results
        assert 'classification_report' in evaluation_results
        
        # Performance should be reasonable
        assert evaluation_results['test_accuracy'] > 0.5
        assert evaluation_results['test_auc'] > 0.5


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])