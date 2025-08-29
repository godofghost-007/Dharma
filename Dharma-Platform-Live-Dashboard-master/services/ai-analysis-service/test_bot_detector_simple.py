"""Simple test for bot detection system."""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.analysis.bot_detector import BotDetector
from app.analysis.bot_model_trainer import BotModelTrainer


async def test_bot_detector_basic():
    """Basic test of bot detector functionality."""
    print("Testing bot detector initialization...")
    
    # Initialize bot detector
    detector = BotDetector()
    await detector.initialize()
    
    print("✓ Bot detector initialized successfully")
    
    # Test with sample human data
    human_data = {
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
            }
        ]
    }
    
    print("Testing human user analysis...")
    result = await detector.analyze_user_behavior(
        user_id='human_user_123',
        platform='twitter',
        user_data=human_data,
        include_network_analysis=True
    )
    
    print(f"✓ Human analysis completed:")
    print(f"  - Bot probability: {result.bot_probability:.3f}")
    print(f"  - Confidence: {result.confidence:.3f}")
    print(f"  - Risk indicators: {len(result.risk_indicators)}")
    print(f"  - Processing time: {result.processing_time_ms:.1f}ms")
    
    # Test with sample bot data
    bot_data = {
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
            }
        ]
    }
    
    print("\nTesting bot user analysis...")
    result = await detector.analyze_user_behavior(
        user_id='bot_user_456',
        platform='twitter',
        user_data=bot_data,
        include_network_analysis=True
    )
    
    print(f"✓ Bot analysis completed:")
    print(f"  - Bot probability: {result.bot_probability:.3f}")
    print(f"  - Confidence: {result.confidence:.3f}")
    print(f"  - Risk indicators: {len(result.risk_indicators)}")
    print(f"  - Processing time: {result.processing_time_ms:.1f}ms")
    
    # Test coordinated behavior detection
    print("\nTesting coordinated behavior detection...")
    bot_group = [bot_data.copy() for _ in range(3)]
    for i, bot in enumerate(bot_group):
        bot['user_id'] = f'bot_user_{i}'
    
    coordination_result = await detector.detect_coordinated_behavior(
        user_group=bot_group,
        time_window_hours=24.0
    )
    
    print(f"✓ Coordination analysis completed:")
    print(f"  - Coordination detected: {coordination_result['coordination_detected']}")
    print(f"  - Coordination score: {coordination_result['coordination_score']:.3f}")
    print(f"  - Patterns detected: {coordination_result.get('patterns_detected', [])}")
    
    # Test health check
    print("\nTesting health check...")
    health = await detector.health_check()
    print(f"✓ Health check: {health['status']}")
    
    # Test model info
    print("\nTesting model info...")
    model_info = detector.get_model_info()
    print(f"✓ Model info retrieved:")
    print(f"  - Model version: {model_info['model_version']}")
    print(f"  - Total analyses: {model_info['total_analyses']}")
    print(f"  - Feature extractors: {len(model_info['feature_extractors'])}")
    
    print("\n🎉 All bot detector tests passed!")


async def test_model_trainer():
    """Test the model trainer functionality."""
    print("\nTesting model trainer...")
    
    trainer = BotModelTrainer()
    
    # Generate synthetic training data
    print("Generating synthetic training data...")
    training_data, labels = await trainer.generate_synthetic_training_data(
        num_samples=100,
        bot_ratio=0.3
    )
    
    print(f"✓ Generated {len(training_data)} samples ({sum(labels)} bots, {len(labels) - sum(labels)} humans)")
    
    # Verify data structure
    sample = training_data[0]
    print(f"✓ Sample has {len(sample)} features")
    
    # Test feature extraction
    print("Testing feature extraction...")
    feature_matrix = await trainer._prepare_feature_matrix(training_data)
    print(f"✓ Feature matrix shape: {feature_matrix.shape}")
    
    print("\n🎉 Model trainer tests passed!")


async def main():
    """Run all tests."""
    print("🚀 Starting bot detection system tests...\n")
    
    try:
        await test_bot_detector_basic()
        await test_model_trainer()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)