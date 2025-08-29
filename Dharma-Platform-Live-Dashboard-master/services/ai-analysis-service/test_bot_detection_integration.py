"""Integration test demonstrating comprehensive bot detection capabilities."""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.analysis.bot_detector import BotDetector
from app.analysis.bot_model_trainer import BotModelTrainer


async def demonstrate_bot_detection_pipeline():
    """Demonstrate the complete bot detection pipeline."""
    print("🤖 Bot Detection System Integration Test")
    print("=" * 50)
    
    # Initialize components
    print("\n1. Initializing Bot Detection System...")
    detector = BotDetector()
    await detector.initialize()
    print("✓ Bot detector initialized")
    
    trainer = BotModelTrainer()
    print("✓ Model trainer initialized")
    
    # Generate and train improved models
    print("\n2. Training Enhanced Models...")
    print("Generating synthetic training data...")
    training_data, labels = await trainer.generate_synthetic_training_data(
        num_samples=500,
        bot_ratio=0.3
    )
    
    print(f"Generated {len(training_data)} training samples")
    print(f"- Human samples: {len(labels) - sum(labels)}")
    print(f"- Bot samples: {sum(labels)}")
    
    print("Training models...")
    training_results = await trainer.train_models(
        training_data=training_data,
        labels=labels,
        validation_split=0.2,
        use_cross_validation=False
    )
    
    print("✓ Models trained successfully")
    print(f"- Validation Accuracy: {training_results['classifier']['validation_accuracy']:.3f}")
    print(f"- Validation AUC: {training_results['classifier']['validation_auc']:.3f}")
    
    # Reload detector with new models
    detector = BotDetector()
    await detector.initialize()
    
    # Test scenarios
    print("\n3. Testing Bot Detection Scenarios...")
    
    # Scenario 1: Legitimate human user
    print("\n📱 Scenario 1: Legitimate Human User")
    human_user = create_human_user_data()
    result = await detector.analyze_user_behavior(
        user_id=human_user['user_id'],
        platform=human_user['platform'],
        user_data=human_user,
        include_network_analysis=True
    )
    
    print(f"User: {human_user['user_id']}")
    print(f"Bot Probability: {result.bot_probability:.3f}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Risk Indicators: {result.risk_indicators}")
    print(f"Classification: {'🤖 BOT' if result.bot_probability > 0.7 else '👤 HUMAN'}")
    
    # Scenario 2: Obvious bot account
    print("\n🤖 Scenario 2: Obvious Bot Account")
    bot_user = create_bot_user_data()
    result = await detector.analyze_user_behavior(
        user_id=bot_user['user_id'],
        platform=bot_user['platform'],
        user_data=bot_user,
        include_network_analysis=True
    )
    
    print(f"User: {bot_user['user_id']}")
    print(f"Bot Probability: {result.bot_probability:.3f}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Risk Indicators: {result.risk_indicators}")
    print(f"Classification: {'🤖 BOT' if result.bot_probability > 0.7 else '👤 HUMAN'}")
    
    # Scenario 3: Sophisticated bot (harder to detect)
    print("\n🎭 Scenario 3: Sophisticated Bot")
    sophisticated_bot = create_sophisticated_bot_data()
    result = await detector.analyze_user_behavior(
        user_id=sophisticated_bot['user_id'],
        platform=sophisticated_bot['platform'],
        user_data=sophisticated_bot,
        include_network_analysis=True
    )
    
    print(f"User: {sophisticated_bot['user_id']}")
    print(f"Bot Probability: {result.bot_probability:.3f}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Risk Indicators: {result.risk_indicators}")
    print(f"Classification: {'🤖 BOT' if result.bot_probability > 0.7 else '👤 HUMAN'}")
    
    # Scenario 4: Coordinated bot network
    print("\n🕸️ Scenario 4: Coordinated Bot Network")
    bot_network = create_coordinated_bot_network()
    
    coordination_result = await detector.detect_coordinated_behavior(
        user_group=bot_network,
        time_window_hours=24.0
    )
    
    print(f"Network Size: {len(bot_network)} accounts")
    print(f"Coordination Detected: {coordination_result['coordination_detected']}")
    print(f"Coordination Score: {coordination_result['coordination_score']:.3f}")
    print(f"Patterns Detected: {coordination_result.get('patterns_detected', [])}")
    
    # Analyze each bot in the network
    print("\nIndividual Bot Analysis:")
    for i, bot_data in enumerate(bot_network[:3]):  # Analyze first 3
        result = await detector.analyze_user_behavior(
            user_id=bot_data['user_id'],
            platform=bot_data['platform'],
            user_data=bot_data,
            include_network_analysis=False  # Skip network analysis for speed
        )
        print(f"  Bot {i+1}: {result.bot_probability:.3f} probability, {len(result.risk_indicators)} risk indicators")
    
    # Feature importance analysis
    print("\n4. Feature Importance Analysis...")
    model_info = detector.get_model_info()
    
    # Get top features from the trained model
    if 'feature_importance' in training_results['classifier']:
        top_features = training_results['classifier']['top_features'][:10]
        print("\nTop 10 Most Important Features for Bot Detection:")
        for i, (feature, importance) in enumerate(top_features, 1):
            print(f"  {i:2d}. {feature:<30} {importance:.4f}")
    
    # Performance metrics
    print("\n5. Performance Metrics...")
    print(f"Total Analyses Performed: {model_info['total_analyses']}")
    print(f"Average Processing Time: {model_info['average_processing_time_ms']:.1f}ms")
    print(f"Model Version: {model_info['model_version']}")
    
    # System health check
    print("\n6. System Health Check...")
    health = await detector.health_check()
    print(f"System Status: {health['status'].upper()}")
    print(f"All Components Loaded: {all(health[key] for key in ['classifier_loaded', 'scaler_loaded', 'anomaly_detector_loaded'])}")
    
    print("\n" + "=" * 50)
    print("✅ Bot Detection Integration Test Completed Successfully!")
    print("\nKey Capabilities Demonstrated:")
    print("• Behavioral feature extraction (temporal, content, network, behavioral)")
    print("• Machine learning model training with synthetic data")
    print("• Individual bot probability scoring")
    print("• Coordinated behavior detection")
    print("• Risk indicator identification")
    print("• Feature importance analysis")
    print("• Performance monitoring")
    print("• System health checking")


def create_human_user_data():
    """Create realistic human user data."""
    base_time = datetime.now()
    
    return {
        'user_id': 'human_journalist_sarah',
        'platform': 'twitter',
        'followers_count': 2500,
        'following_count': 800,
        'posts_count': 1200,
        'account_created': (base_time - timedelta(days=800)).isoformat() + 'Z',
        'avg_posts_per_day': 3.2,
        'duplicate_content_ratio': 0.05,
        'avg_content_length': 180.0,
        'hashtag_usage_frequency': 0.4,
        'mention_usage_frequency': 0.3,
        'avg_likes_per_post': 25.0,
        'avg_shares_per_post': 8.0,
        'engagement_consistency': 0.6,
        'mutual_connections_ratio': 0.35,
        'network_clustering_coefficient': 0.25,
        'posts': [
            {
                'content': 'Interesting developments in the tech industry today. What are your thoughts on the new AI regulations? #TechPolicy #AI',
                'timestamp': (base_time - timedelta(hours=2)).isoformat() + 'Z',
                'hashtags': ['TechPolicy', 'AI'],
                'mentions': [],
                'metrics': {'likes': 45, 'shares': 12, 'comments': 8}
            },
            {
                'content': 'Thanks @colleague for sharing that insightful article on climate change. Really makes you think about our future.',
                'timestamp': (base_time - timedelta(hours=8)).isoformat() + 'Z',
                'hashtags': [],
                'mentions': ['colleague'],
                'metrics': {'likes': 18, 'shares': 3, 'comments': 5}
            },
            {
                'content': 'Coffee break thoughts: Why do we always rush through life? Sometimes it\'s good to just pause and appreciate the moment ☕',
                'timestamp': (base_time - timedelta(hours=24)).isoformat() + 'Z',
                'hashtags': [],
                'mentions': [],
                'metrics': {'likes': 32, 'shares': 2, 'comments': 12}
            },
            {
                'content': 'Working on a story about local community gardens. Amazing how much impact these small initiatives can have! 🌱',
                'timestamp': (base_time - timedelta(hours=36)).isoformat() + 'Z',
                'hashtags': [],
                'mentions': [],
                'metrics': {'likes': 28, 'shares': 6, 'comments': 4}
            }
        ]
    }


def create_bot_user_data():
    """Create obvious bot user data."""
    base_time = datetime.now()
    
    return {
        'user_id': 'promo_bot_deals123',
        'platform': 'twitter',
        'followers_count': 45,
        'following_count': 3500,
        'posts_count': 2800,
        'account_created': (base_time - timedelta(days=30)).isoformat() + 'Z',
        'avg_posts_per_day': 45.0,
        'duplicate_content_ratio': 0.85,
        'avg_content_length': 95.0,
        'hashtag_usage_frequency': 0.95,
        'mention_usage_frequency': 0.8,
        'avg_likes_per_post': 1.2,
        'avg_shares_per_post': 0.3,
        'engagement_consistency': 0.98,
        'mutual_connections_ratio': 0.02,
        'network_clustering_coefficient': 0.85,
        'posts': [
            {
                'content': 'AMAZING DEALS HERE! 50% OFF EVERYTHING! CLICK NOW! #deals #sale #discount #shopping',
                'timestamp': (base_time - timedelta(minutes=30)).isoformat() + 'Z',
                'hashtags': ['deals', 'sale', 'discount', 'shopping'],
                'mentions': [],
                'metrics': {'likes': 1, 'shares': 0, 'comments': 0}
            },
            {
                'content': 'AMAZING DEALS HERE! 50% OFF EVERYTHING! CLICK NOW! #deals #sale #discount #shopping',
                'timestamp': (base_time - timedelta(minutes=60)).isoformat() + 'Z',
                'hashtags': ['deals', 'sale', 'discount', 'shopping'],
                'mentions': [],
                'metrics': {'likes': 2, 'shares': 1, 'comments': 0}
            },
            {
                'content': 'LIMITED TIME OFFER! BEST PRICES GUARANTEED! #deals #sale #discount #shopping',
                'timestamp': (base_time - timedelta(minutes=90)).isoformat() + 'Z',
                'hashtags': ['deals', 'sale', 'discount', 'shopping'],
                'mentions': [],
                'metrics': {'likes': 1, 'shares': 0, 'comments': 0}
            },
            {
                'content': 'AMAZING DEALS HERE! 50% OFF EVERYTHING! CLICK NOW! #deals #sale #discount #shopping',
                'timestamp': (base_time - timedelta(minutes=120)).isoformat() + 'Z',
                'hashtags': ['deals', 'sale', 'discount', 'shopping'],
                'mentions': [],
                'metrics': {'likes': 1, 'shares': 0, 'comments': 0}
            }
        ]
    }


def create_sophisticated_bot_data():
    """Create sophisticated bot that's harder to detect."""
    base_time = datetime.now()
    
    return {
        'user_id': 'news_aggregator_pro',
        'platform': 'twitter',
        'followers_count': 1200,
        'following_count': 400,
        'posts_count': 800,
        'account_created': (base_time - timedelta(days=120)).isoformat() + 'Z',
        'avg_posts_per_day': 12.0,
        'duplicate_content_ratio': 0.3,
        'avg_content_length': 140.0,
        'hashtag_usage_frequency': 0.7,
        'mention_usage_frequency': 0.4,
        'avg_likes_per_post': 8.0,
        'avg_shares_per_post': 3.0,
        'engagement_consistency': 0.85,
        'mutual_connections_ratio': 0.15,
        'network_clustering_coefficient': 0.6,
        'posts': [
            {
                'content': 'Breaking: New study reveals impact of social media on mental health. Researchers call for more regulation. #MentalHealth #SocialMedia',
                'timestamp': (base_time - timedelta(hours=1)).isoformat() + 'Z',
                'hashtags': ['MentalHealth', 'SocialMedia'],
                'mentions': [],
                'metrics': {'likes': 12, 'shares': 4, 'comments': 2}
            },
            {
                'content': 'Market update: Tech stocks continue to rise amid AI boom. Investors remain optimistic about future growth. #TechStocks #AI',
                'timestamp': (base_time - timedelta(hours=3)).isoformat() + 'Z',
                'hashtags': ['TechStocks', 'AI'],
                'mentions': [],
                'metrics': {'likes': 8, 'shares': 2, 'comments': 1}
            },
            {
                'content': 'Weather alert: Heavy rainfall expected in northern regions. Residents advised to take precautions. #Weather #Safety',
                'timestamp': (base_time - timedelta(hours=5)).isoformat() + 'Z',
                'hashtags': ['Weather', 'Safety'],
                'mentions': [],
                'metrics': {'likes': 6, 'shares': 3, 'comments': 0}
            },
            {
                'content': 'Sports update: Championship finals set for this weekend. Tickets selling fast for the highly anticipated match. #Sports #Championship',
                'timestamp': (base_time - timedelta(hours=7)).isoformat() + 'Z',
                'hashtags': ['Sports', 'Championship'],
                'mentions': [],
                'metrics': {'likes': 10, 'shares': 2, 'comments': 1}
            }
        ]
    }


def create_coordinated_bot_network():
    """Create a network of coordinated bots."""
    base_time = datetime.now()
    bot_network = []
    
    # Common characteristics for coordinated bots
    common_content = [
        "Support our cause! Join the movement for change! #Movement #Change #Action",
        "This is important! Everyone needs to see this! Share now! #Important #Share #Viral",
        "Breaking news that mainstream media won't tell you! #Truth #News #Alternative",
        "Stand up for what's right! Time to take action! #StandUp #Action #Rights"
    ]
    
    for i in range(5):
        bot_data = {
            'user_id': f'activist_bot_{i+1}',
            'platform': 'twitter',
            'followers_count': 150 + (i * 20),
            'following_count': 2000 + (i * 100),
            'posts_count': 400 + (i * 50),
            'account_created': (base_time - timedelta(days=45 + i)).isoformat() + 'Z',
            'avg_posts_per_day': 20.0 + (i * 2),
            'duplicate_content_ratio': 0.7 + (i * 0.05),
            'avg_content_length': 120.0 + (i * 10),
            'hashtag_usage_frequency': 0.8 + (i * 0.02),
            'mention_usage_frequency': 0.6 + (i * 0.05),
            'avg_likes_per_post': 3.0 + (i * 0.5),
            'avg_shares_per_post': 1.0 + (i * 0.2),
            'engagement_consistency': 0.9 + (i * 0.01),
            'mutual_connections_ratio': 0.05 + (i * 0.01),
            'network_clustering_coefficient': 0.8 + (i * 0.02),
            'posts': []
        }
        
        # Create similar posts with slight variations
        for j, content in enumerate(common_content):
            post_time = base_time - timedelta(hours=j*2 + i*0.5)  # Slightly staggered timing
            bot_data['posts'].append({
                'content': content,
                'timestamp': post_time.isoformat() + 'Z',
                'hashtags': ['Movement', 'Change', 'Action'] if j == 0 else ['Important', 'Share', 'Viral'] if j == 1 else ['Truth', 'News', 'Alternative'] if j == 2 else ['StandUp', 'Action', 'Rights'],
                'mentions': [],
                'metrics': {'likes': 2 + i, 'shares': 1, 'comments': 0}
            })
        
        bot_network.append(bot_data)
    
    return bot_network


if __name__ == '__main__':
    asyncio.run(demonstrate_bot_detection_pipeline())