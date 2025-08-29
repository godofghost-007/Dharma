"""Pytest configuration and fixtures for unit tests."""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, MagicMock
import numpy as np

# Test fixtures for data models
@pytest.fixture
def sample_post_data():
    """Sample post data for testing."""
    return {
        "platform": "twitter",
        "post_id": "1234567890",
        "user_id": "user123",
        "content": "This is a sample tweet for testing purposes #test",
        "timestamp": datetime.utcnow(),
        "hashtags": ["test"],
        "mentions": ["@example"],
        "metrics": {
            "likes": 10,
            "shares": 5,
            "comments": 2,
            "views": 100
        }
    }

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "platform": "twitter",
        "user_id": "user123",
        "profile": {
            "username": "testuser",
            "display_name": "Test User",
            "bio": "This is a test user account",
            "followers_count": 1000,
            "following_count": 500,
            "posts_count": 250,
            "account_created": datetime.utcnow() - timedelta(days=365),
            "is_verified": False,
            "is_private": False
        }
    }

@pytest.fixture
def sample_campaign_data():
    """Sample campaign data for testing."""
    return {
        "campaign_id": "campaign123",
        "name": "Test Campaign",
        "description": "A test disinformation campaign",
        "detection_date": datetime.utcnow(),
        "coordination_score": 0.8,
        "participant_count": 15,
        "content_samples": ["Sample content 1", "Sample content 2"],
        "impact_metrics": {
            "reach": 10000,
            "engagement": 500,
            "virality_score": 0.7
        }
    }

@pytest.fixture
def sample_alert_data():
    """Sample alert data for testing."""
    return {
        "alert_id": "alert123",
        "title": "Test Alert",
        "description": "This is a test alert",
        "alert_type": "high_risk_content",
        "severity": "high",
        "platform": "twitter",
        "user_id": "user123",
        "post_id": "post123",
        "analysis": {
            "sentiment": "Anti-India",
            "confidence_score": 0.85,
            "risk_score": 0.75
        }
    }

# Mock fixtures for external dependencies
@pytest.fixture
def mock_nlp_service():
    """Mock NLP service for testing."""
    mock = AsyncMock()
    mock.analyze_text.return_value = Mock(
        success=True,
        language_detection=Mock(language="en", confidence=0.95),
        sentiment=Mock(sentiment="neutral", confidence=0.8),
        translation=Mock(translated_text="Translated text", quality_score=0.9),
        processing_time=0.1
    )
    mock.batch_analyze.return_value = [mock.analyze_text.return_value]
    mock.health_check.return_value = {"overall": "healthy"}
    mock.get_service_stats.return_value = {"total_requests": 100}
    return mock

@pytest.fixture
def mock_database():
    """Mock database for testing."""
    mock = AsyncMock()
    mock.get_user_by_username.return_value = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "$2b$12$test_hash",
        "role": "analyst",
        "is_active": True
    }
    mock.get_user_by_id.return_value = mock.get_user_by_username.return_value
    mock.get_user_permissions.return_value = ["read", "write"]
    mock.create_user.return_value = 1
    mock.update_last_login.return_value = None
    return mock

@pytest.fixture
def mock_security_manager():
    """Mock security manager for testing."""
    mock = Mock()
    mock.verify_password.return_value = True
    mock.get_password_hash.return_value = "$2b$12$test_hash"
    mock.create_token_pair.return_value = Mock(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="bearer",
        expires_in=3600
    )
    mock.verify_token.return_value = Mock(
        user_id=1,
        username="testuser",
        role="analyst"
    )
    return mock

@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing."""
    mock = AsyncMock()
    mock.send.return_value = Mock(topic="test", partition=0, offset=1)
    return mock

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = False
    return mock

# Behavioral features fixture for bot detection
@pytest.fixture
def sample_behavioral_features():
    """Sample behavioral features for bot detection testing."""
    return {
        "avg_posts_per_day": 5.0,
        "posting_time_variance": 0.5,
        "weekend_activity_ratio": 0.3,
        "duplicate_content_ratio": 0.1,
        "avg_content_length": 120.0,
        "hashtag_usage_frequency": 0.2,
        "mention_usage_frequency": 0.1,
        "avg_likes_per_post": 15.0,
        "avg_shares_per_post": 3.0,
        "engagement_consistency": 0.7,
        "follower_following_ratio": 2.0,
        "mutual_connections_ratio": 0.4,
        "network_clustering_coefficient": 0.3,
        "account_age_days": 365,
        "activity_burst_frequency": 0.1
    }

# ML model fixtures
@pytest.fixture
def mock_ml_models():
    """Mock ML models for testing."""
    classifier = Mock()
    classifier.predict_proba.return_value = np.array([[0.3, 0.7]])  # Bot probability 0.7
    
    scaler = Mock()
    scaler.transform.return_value = np.array([[0.1, 0.2, 0.3]])
    
    anomaly_detector = Mock()
    anomaly_detector.decision_function.return_value = np.array([-0.2])
    
    return {
        "classifier": classifier,
        "scaler": scaler,
        "anomaly_detector": anomaly_detector
    }

# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Async test helper
@pytest.fixture
def async_test():
    """Helper for running async tests."""
    def _async_test(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return _async_test

# Additional fixtures for alert management testing
@pytest.fixture
def sample_alert_context():
    """Sample alert context for testing."""
    return {
        "detection_method": "sentiment_analysis",
        "confidence_score": 0.85,
        "risk_score": 0.75,
        "detection_window_start": datetime.utcnow() - timedelta(hours=1),
        "detection_window_end": datetime.utcnow(),
        "source_platform": "twitter",
        "source_user_ids": ["user123"],
        "source_post_ids": ["post456"],
        "keywords_matched": ["anti-india", "terrorist"],
        "content_samples": ["Sample suspicious content"]
    }

@pytest.fixture
def sample_notification_data():
    """Sample notification data for testing."""
    return {
        "recipient": "analyst@example.com",
        "subject": "Test Alert Notification",
        "message": "This is a test alert notification",
        "alert_id": "test_alert_001",
        "severity": "high",
        "timestamp": datetime.utcnow()
    }

# Authentication fixtures
@pytest.fixture
def sample_user_credentials():
    """Sample user credentials for testing."""
    return {
        "username": "testuser",
        "password": "SecurePass123",
        "email": "testuser@example.com",
        "role": "analyst",
        "full_name": "Test User",
        "department": "Intelligence Analysis"
    }

@pytest.fixture
def sample_jwt_payload():
    """Sample JWT payload for testing."""
    return {
        "sub": "testuser",
        "user_id": 1,
        "role": "analyst",
        "permissions": ["read", "write", "analyze"],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "type": "access"
    }

# Mock external services
@pytest.fixture
def mock_email_service():
    """Mock email service for testing."""
    mock = AsyncMock()
    mock.send_email.return_value = {"success": True, "message_id": "test_msg_123"}
    mock.validate_email.return_value = True
    return mock

@pytest.fixture
def mock_sms_service():
    """Mock SMS service for testing."""
    mock = AsyncMock()
    mock.send_sms.return_value = {"success": True, "message_id": "sms_123"}
    mock.validate_phone.return_value = True
    return mock

# Database fixtures
@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    mock = AsyncMock()
    mock.fetchrow.return_value = None
    mock.fetch.return_value = []
    mock.fetchval.return_value = None
    mock.execute.return_value = None
    return mock

@pytest.fixture
def sample_database_user():
    """Sample database user record for testing."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "testuser@example.com",
        "hashed_password": "$2b$12$test_hash_value",
        "role": "analyst",
        "full_name": "Test User",
        "department": "Intelligence",
        "is_active": True,
        "created_at": datetime.utcnow() - timedelta(days=30),
        "last_login": datetime.utcnow() - timedelta(hours=2),
        "login_count": 15,
        "failed_login_attempts": 0
    }