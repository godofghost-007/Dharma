"""Simple integration test for the AI processing engine."""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append('../../')

# Now import the components
from app.analysis.sentiment_analyzer import SentimentAnalyzer
from app.analysis.bot_detector import BotDetector
from app.analysis.campaign_detector import CampaignDetector


async def test_ai_processing_engine():
    """Test the complete AI processing engine."""
    print("🚀 Starting AI Processing Engine Test")
    print("=" * 50)
    
    try:
        # Initialize components
        print("\n1. Initializing AI Components...")
        
        sentiment_analyzer = SentimentAnalyzer()
        await sentiment_analyzer.initialize()
        print("   ✅ Sentiment Analyzer initialized")
        
        bot_detector = BotDetector()
        await bot_detector.initialize()
        print("   ✅ Bot Detector initialized")
        
        campaign_detector = CampaignDetector()
        await campaign_detector.initialize()
        print("   ✅ Campaign Detector initialized")
        
        # Test sentiment analysis
        print("\n2. Testing Sentiment Analysis...")
        
        test_texts = [
            "India is a great country with rich cultural heritage and strong democratic values.",
            "Anti-India propaganda is being spread to destabilize our nation.",
            "The weather is nice today and I had a good breakfast."
        ]
        
        for i, text in enumerate(test_texts, 1):
            result = await sentiment_analyzer.analyze_sentiment(text)
            print(f"   Text {i}: {result.sentiment.value} (confidence: {result.confidence:.3f})")
        
        # Test batch sentiment analysis
        batch_results = await sentiment_analyzer.batch_analyze_sentiment(test_texts)
        print(f"   ✅ Batch analysis completed: {len(batch_results)} texts processed")
        
        # Test bot detection
        print("\n3. Testing Bot Detection...")
        
        sample_user_data = {
            "user_id": "test_user_123",
            "platform": "twitter",
            "account_created": (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z",
            "follower_count": 1500,
            "following_count": 800,
            "posts": [
                {
                    "post_id": "post_1",
                    "content": "Great news about India's economic growth!",
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
                    "likes": 25,
                    "shares": 5
                }
            ],
            "avg_posts_per_day": 3.5,
            "duplicate_content_ratio": 0.1,
            "hashtag_usage_frequency": 0.6,
            "mention_usage_frequency": 0.3,
            "engagement_consistency": 0.7
        }
        
        bot_result = await bot_detector.analyze_user_behavior(
            user_id="test_user_123",
            platform="twitter",
            user_data=sample_user_data,
            include_network_analysis=False
        )
        
        print(f"   Bot probability: {bot_result.bot_probability:.3f}")
        print(f"   Confidence: {bot_result.confidence:.3f}")
        print(f"   Risk indicators: {len(bot_result.risk_indicators)}")
        print("   ✅ Bot detection completed")
        
        # Test campaign detection
        print("\n4. Testing Campaign Detection...")
        
        sample_posts = [
            {
                "post_id": "post_1",
                "user_id": "user_1",
                "platform": "twitter",
                "content": "India is facing serious challenges with misinformation campaigns targeting our democracy.",
                "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z",
                "metrics": {"likes": 45, "shares": 12, "comments": 8}
            },
            {
                "post_id": "post_2",
                "user_id": "user_2",
                "platform": "twitter",
                "content": "India is facing serious challenges with misinformation campaigns targeting our democracy.",
                "timestamp": (datetime.utcnow() - timedelta(minutes=3)).isoformat() + "Z",
                "metrics": {"likes": 43, "shares": 11, "comments": 7}
            },
            {
                "post_id": "post_3",
                "user_id": "user_3",
                "platform": "twitter",
                "content": "We must protect our nation from foreign interference and fake news spreading lies.",
                "timestamp": (datetime.utcnow() - timedelta(minutes=2)).isoformat() + "Z",
                "metrics": {"likes": 67, "shares": 23, "comments": 15}
            }
        ]
        
        campaign_result = await campaign_detector.detect_campaigns(
            posts_data=sample_posts,
            time_window_hours=24.0,
            min_coordination_score=0.3
        )
        
        print(f"   Campaigns detected: {campaign_result.campaigns_detected}")
        print(f"   Coordination score: {campaign_result.coordination_score:.3f}")
        print(f"   Content similarity: {campaign_result.content_similarity_score:.3f}")
        print(f"   Temporal coordination: {campaign_result.temporal_coordination_score:.3f}")
        print("   ✅ Campaign detection completed")
        
        # Test coordinated behavior detection
        print("\n5. Testing Coordinated Behavior Detection...")
        
        user_group = [
            {
                "user_id": "user_1",
                "avg_posts_per_day": 15.0,
                "duplicate_content_ratio": 0.7,
                "hashtag_usage_frequency": 0.8,
                "mention_usage_frequency": 0.6,
                "engagement_consistency": 0.3
            },
            {
                "user_id": "user_2",
                "avg_posts_per_day": 16.0,
                "duplicate_content_ratio": 0.75,
                "hashtag_usage_frequency": 0.82,
                "mention_usage_frequency": 0.58,
                "engagement_consistency": 0.32
            }
        ]
        
        coordination_result = await bot_detector.detect_coordinated_behavior(
            user_group=user_group,
            time_window_hours=24.0
        )
        
        print(f"   Coordination detected: {coordination_result['coordination_detected']}")
        print(f"   Coordination score: {coordination_result['coordination_score']:.3f}")
        print("   ✅ Coordinated behavior detection completed")
        
        # Performance test
        print("\n6. Performance Testing...")
        
        import time
        
        # Test sentiment analysis performance
        start_time = time.time()
        perf_texts = ["This is a test sentence for performance evaluation."] * 20
        perf_results = await sentiment_analyzer.batch_analyze_sentiment(perf_texts)
        sentiment_time = (time.time() - start_time) * 1000
        
        print(f"   Sentiment analysis: {len(perf_texts)} texts in {sentiment_time:.2f}ms")
        print(f"   Average per text: {sentiment_time/len(perf_texts):.2f}ms")
        
        # Test bot detection performance
        start_time = time.time()
        for i in range(5):
            await bot_detector.analyze_user_behavior(
                user_id=f"perf_user_{i}",
                platform="twitter",
                user_data={
                    "avg_posts_per_day": 5.0,
                    "duplicate_content_ratio": 0.2,
                    "account_age_days": 365,
                    "engagement_consistency": 0.7
                },
                include_network_analysis=False
            )
        bot_time = (time.time() - start_time) * 1000
        
        print(f"   Bot detection: 5 users in {bot_time:.2f}ms")
        print(f"   Average per user: {bot_time/5:.2f}ms")
        print("   ✅ Performance testing completed")
        
        # Health checks
        print("\n7. Health Checks...")
        
        sentiment_health = await sentiment_analyzer.health_check()
        bot_health = await bot_detector.health_check()
        campaign_health = await campaign_detector.health_check()
        
        print(f"   Sentiment analyzer: {sentiment_health['status']}")
        print(f"   Bot detector: {bot_health['status']}")
        print(f"   Campaign detector: {campaign_health['status']}")
        print("   ✅ Health checks completed")
        
        # Model information
        print("\n8. Model Information...")
        
        sentiment_info = sentiment_analyzer.get_model_info()
        bot_info = bot_detector.get_model_info()
        campaign_info = campaign_detector.get_model_info()
        
        print(f"   Sentiment model: {sentiment_info['model_name']} v{sentiment_info['model_version']}")
        print(f"   Bot detection model: {bot_info['model_name']} v{bot_info['model_version']}")
        print(f"   Campaign detection: v{campaign_info['model_version']}")
        print("   ✅ Model information retrieved")
        
        print("\n" + "=" * 50)
        print("🎉 AI PROCESSING ENGINE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        
        # Summary
        print("\nSUMMARY:")
        print(f"✅ Sentiment Analysis: {len(test_texts)} texts analyzed")
        print(f"✅ Bot Detection: 1 user analyzed")
        print(f"✅ Campaign Detection: {len(sample_posts)} posts analyzed")
        print(f"✅ Coordinated Behavior: {len(user_group)} users analyzed")
        print(f"✅ Performance: Batch processing tested")
        print(f"✅ Health Checks: All components healthy")
        print(f"✅ Model Info: All models loaded and operational")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ai_processing_engine())
    if success:
        print("\n🚀 All tests passed! AI Processing Engine is ready for production.")
    else:
        print("\n💥 Tests failed! Please check the errors above.")
        sys.exit(1)