"""Integration test for the complete AI processing engine."""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import all AI processing components
from app.analysis.sentiment_analyzer import SentimentAnalyzer
from app.analysis.bot_detector import BotDetector
from app.analysis.campaign_detector import CampaignDetector
from app.core.model_governance_service import ModelGovernanceService
from shared.models.post import SentimentType, PropagandaTechnique


class TestAIProcessingEngine:
    """Test the complete AI processing engine integration."""
    
    @pytest.fixture
    async def sentiment_analyzer(self):
        """Create and initialize sentiment analyzer."""
        analyzer = SentimentAnalyzer()
        await analyzer.initialize()
        return analyzer
    
    @pytest.fixture
    async def bot_detector(self):
        """Create and initialize bot detector."""
        detector = BotDetector()
        await detector.initialize()
        return detector
    
    @pytest.fixture
    async def campaign_detector(self):
        """Create and initialize campaign detector."""
        detector = CampaignDetector()
        await detector.initialize()
        return detector
    
    @pytest.fixture
    async def governance_service(self):
        """Create and initialize governance service."""
        service = ModelGovernanceService()
        await service.start()
        yield service
        await service.stop()
    
    @pytest.fixture
    def sample_posts_data(self) -> List[Dict[str, Any]]:
        """Create sample posts data for testing."""
        base_time = datetime.utcnow()
        
        return [
            {
                "post_id": "post_1",
                "user_id": "user_1",
                "platform": "twitter",
                "content": "India is facing serious challenges with misinformation campaigns targeting our democracy.",
                "timestamp": (base_time - timedelta(minutes=5)).isoformat() + "Z",
                "metrics": {"likes": 45, "shares": 12, "comments": 8}
            },
            {
                "post_id": "post_2",
                "user_id": "user_2",
                "platform": "twitter",
                "content": "India is facing serious challenges with misinformation campaigns targeting our democracy.",
                "timestamp": (base_time - timedelta(minutes=3)).isoformat() + "Z",
                "metrics": {"likes": 43, "shares": 11, "comments": 7}
            },
            {
                "post_id": "post_3",
                "user_id": "user_3",
                "platform": "twitter",
                "content": "We must protect our nation from foreign interference and fake news spreading lies.",
                "timestamp": (base_time - timedelta(minutes=2)).isoformat() + "Z",
                "metrics": {"likes": 67, "shares": 23, "comments": 15}
            },
            {
                "post_id": "post_4",
                "user_id": "user_4",
                "platform": "youtube",
                "content": "Anti-India propaganda is being spread systematically to destabilize our country.",
                "timestamp": (base_time - timedelta(minutes=1)).isoformat() + "Z",
                "metrics": {"likes": 89, "shares": 34, "comments": 21}
            }
        ]
    
    @pytest.fixture
    def sample_user_data(self) -> Dict[str, Any]:
        """Create sample user data for bot detection testing."""
        return {
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
                },
                {
                    "post_id": "post_2",
                    "content": "Proud to be Indian! Our culture is amazing.",
                    "timestamp": (datetime.utcnow() - timedelta(hours=4)).isoformat() + "Z",
                    "likes": 30,
                    "shares": 8
                }
            ],
            "avg_posts_per_day": 3.5,
            "duplicate_content_ratio": 0.1,
            "hashtag_usage_frequency": 0.6,
            "mention_usage_frequency": 0.3,
            "engagement_consistency": 0.7
        }
    
    async def test_sentiment_analysis_integration(self, sentiment_analyzer):
        """Test sentiment analysis functionality."""
        # Test single text analysis
        result = await sentiment_analyzer.analyze_sentiment(
            "India is a great country with rich cultural heritage and strong democratic values."
        )
        
        assert result is not None
        assert result.sentiment in [SentimentType.PRO_INDIA, SentimentType.NEUTRAL, SentimentType.ANTI_INDIA]
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.risk_score <= 1.0
        assert result.processing_time_ms > 0
        assert result.model_version is not None
        
        print(f"Sentiment Analysis Result:")
        print(f"  Sentiment: {result.sentiment.value}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Risk Score: {result.risk_score:.3f}")
        print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
        
        # Test batch analysis
        texts = [
            "India's democracy is under threat from misinformation.",
            "Proud to be Indian! Our nation is strong.",
            "The government policies are helping economic growth."
        ]
        
        batch_results = await sentiment_analyzer.batch_analyze_sentiment(texts)
        
        assert len(batch_results) == len(texts)
        for result in batch_results:
            assert result.sentiment in [SentimentType.PRO_INDIA, SentimentType.NEUTRAL, SentimentType.ANTI_INDIA]
            assert 0.0 <= result.confidence <= 1.0
        
        print(f"\nBatch Analysis Results: {len(batch_results)} texts processed")
    
    async def test_bot_detection_integration(self, bot_detector, sample_user_data):
        """Test bot detection functionality."""
        result = await bot_detector.analyze_user_behavior(
            user_id=sample_user_data["user_id"],
            platform=sample_user_data["platform"],
            user_data=sample_user_data,
            include_network_analysis=True
        )
        
        assert result is not None
        assert result.user_id == sample_user_data["user_id"]
        assert result.platform == sample_user_data["platform"]
        assert 0.0 <= result.bot_probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.risk_indicators, list)
        assert isinstance(result.behavioral_features, dict)
        assert result.processing_time_ms > 0
        
        print(f"\nBot Detection Result:")
        print(f"  User ID: {result.user_id}")
        print(f"  Bot Probability: {result.bot_probability:.3f}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Risk Indicators: {result.risk_indicators}")
        print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
    
    async def test_campaign_detection_integration(self, campaign_detector, sample_posts_data):
        """Test campaign detection functionality."""
        result = await campaign_detector.detect_campaigns(
            posts_data=sample_posts_data,
            time_window_hours=24.0,
            min_coordination_score=0.3
        )
        
        assert result is not None
        assert result.campaigns_detected >= 0
        assert 0.0 <= result.coordination_score <= 1.0
        assert result.participant_count >= 0
        assert 0.0 <= result.content_similarity_score <= 1.0
        assert 0.0 <= result.temporal_coordination_score <= 1.0
        assert result.processing_time_ms > 0
        
        print(f"\nCampaign Detection Result:")
        print(f"  Campaigns Detected: {result.campaigns_detected}")
        print(f"  Coordination Score: {result.coordination_score:.3f}")
        print(f"  Participant Count: {result.participant_count}")
        print(f"  Content Similarity: {result.content_similarity_score:.3f}")
        print(f"  Temporal Coordination: {result.temporal_coordination_score:.3f}")
        print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
    
    async def test_coordinated_behavior_detection(self, bot_detector):
        """Test coordinated behavior detection."""
        # Create sample user group data
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
            },
            {
                "user_id": "user_3",
                "avg_posts_per_day": 14.5,
                "duplicate_content_ratio": 0.72,
                "hashtag_usage_frequency": 0.79,
                "mention_usage_frequency": 0.61,
                "engagement_consistency": 0.29
            }
        ]
        
        result = await bot_detector.detect_coordinated_behavior(
            user_group=user_group,
            time_window_hours=24.0
        )
        
        assert result is not None
        assert "coordination_detected" in result
        assert "coordination_score" in result
        assert isinstance(result["coordination_detected"], bool)
        assert 0.0 <= result["coordination_score"] <= 1.0
        
        print(f"\nCoordinated Behavior Detection:")
        print(f"  Coordination Detected: {result['coordination_detected']}")
        print(f"  Coordination Score: {result['coordination_score']:.3f}")
        print(f"  User Count: {result.get('user_count', 0)}")
    
    async def test_end_to_end_processing_pipeline(
        self, 
        sentiment_analyzer, 
        bot_detector, 
        campaign_detector,
        sample_posts_data,
        sample_user_data
    ):
        """Test complete end-to-end processing pipeline."""
        print("\n" + "="*60)
        print("RUNNING END-TO-END AI PROCESSING PIPELINE TEST")
        print("="*60)
        
        # Step 1: Analyze sentiment for all posts
        print("\n1. SENTIMENT ANALYSIS")
        print("-" * 30)
        
        sentiment_results = []
        for post in sample_posts_data:
            result = await sentiment_analyzer.analyze_sentiment(post["content"])
            sentiment_results.append({
                "post_id": post["post_id"],
                "sentiment": result.sentiment.value,
                "confidence": result.confidence,
                "risk_score": result.risk_score
            })
            print(f"Post {post['post_id']}: {result.sentiment.value} (confidence: {result.confidence:.3f})")
        
        # Step 2: Analyze users for bot behavior
        print("\n2. BOT DETECTION")
        print("-" * 30)
        
        # Create user data for each post author
        bot_results = []
        for post in sample_posts_data:
            user_data = {
                **sample_user_data,
                "user_id": post["user_id"],
                "platform": post["platform"]
            }
            
            result = await bot_detector.analyze_user_behavior(
                user_id=post["user_id"],
                platform=post["platform"],
                user_data=user_data,
                include_network_analysis=False
            )
            
            bot_results.append({
                "user_id": post["user_id"],
                "bot_probability": result.bot_probability,
                "confidence": result.confidence,
                "risk_indicators": result.risk_indicators
            })
            print(f"User {post['user_id']}: Bot probability {result.bot_probability:.3f}")
        
        # Step 3: Detect campaigns
        print("\n3. CAMPAIGN DETECTION")
        print("-" * 30)
        
        campaign_result = await campaign_detector.detect_campaigns(
            posts_data=sample_posts_data,
            time_window_hours=24.0,
            min_coordination_score=0.3
        )
        
        print(f"Campaigns detected: {campaign_result.campaigns_detected}")
        print(f"Overall coordination score: {campaign_result.coordination_score:.3f}")
        
        # Step 4: Generate comprehensive analysis report
        print("\n4. COMPREHENSIVE ANALYSIS REPORT")
        print("-" * 40)
        
        # Calculate aggregate metrics
        high_risk_posts = sum(1 for r in sentiment_results if r["risk_score"] > 0.7)
        suspicious_users = sum(1 for r in bot_results if r["bot_probability"] > 0.7)
        
        report = {
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "posts_analyzed": len(sample_posts_data),
            "users_analyzed": len(set(post["user_id"] for post in sample_posts_data)),
            "sentiment_analysis": {
                "high_risk_posts": high_risk_posts,
                "sentiment_distribution": {
                    sentiment: sum(1 for r in sentiment_results if r["sentiment"] == sentiment)
                    for sentiment in ["PRO_INDIA", "NEUTRAL", "ANTI_INDIA"]
                }
            },
            "bot_detection": {
                "suspicious_users": suspicious_users,
                "average_bot_probability": sum(r["bot_probability"] for r in bot_results) / len(bot_results)
            },
            "campaign_detection": {
                "campaigns_detected": campaign_result.campaigns_detected,
                "coordination_score": campaign_result.coordination_score,
                "content_similarity": campaign_result.content_similarity_score,
                "temporal_coordination": campaign_result.temporal_coordination_score
            }
        }
        
        print(json.dumps(report, indent=2))
        
        # Assertions for end-to-end test
        assert len(sentiment_results) == len(sample_posts_data)
        assert len(bot_results) == len(sample_posts_data)
        assert campaign_result.campaigns_detected >= 0
        assert all(0.0 <= r["confidence"] <= 1.0 for r in sentiment_results)
        assert all(0.0 <= r["bot_probability"] <= 1.0 for r in bot_results)
        
        print("\n✅ END-TO-END PIPELINE TEST COMPLETED SUCCESSFULLY")
        return report
    
    async def test_model_governance_integration(self, governance_service):
        """Test model governance service integration."""
        # Test governance service health
        dashboard_data = await governance_service.get_governance_dashboard()
        
        assert dashboard_data is not None
        assert "models" in dashboard_data
        
        # Test model listing
        from app.core.model_registry import ModelType
        models = await governance_service.list_models()
        
        assert isinstance(models, list)
        
        print(f"\nModel Governance Integration:")
        print(f"  Dashboard data keys: {list(dashboard_data.keys())}")
        print(f"  Registered models: {len(models)}")
    
    async def test_performance_benchmarks(
        self,
        sentiment_analyzer,
        bot_detector,
        campaign_detector
    ):
        """Test performance benchmarks for all components."""
        print("\n" + "="*50)
        print("PERFORMANCE BENCHMARKS")
        print("="*50)
        
        # Sentiment analysis benchmark
        test_texts = [
            "India is a great nation with rich cultural heritage.",
            "The government policies are helping economic development.",
            "We need to protect our democracy from misinformation.",
            "Anti-India propaganda is spreading false narratives.",
            "Proud to be Indian and support our country's progress."
        ] * 10  # 50 texts total
        
        import time
        start_time = time.time()
        sentiment_results = await sentiment_analyzer.batch_analyze_sentiment(test_texts)
        sentiment_time = (time.time() - start_time) * 1000
        
        print(f"\nSentiment Analysis Benchmark:")
        print(f"  Texts processed: {len(test_texts)}")
        print(f"  Total time: {sentiment_time:.2f}ms")
        print(f"  Average per text: {sentiment_time/len(test_texts):.2f}ms")
        
        # Bot detection benchmark
        start_time = time.time()
        for i in range(10):
            await bot_detector.analyze_user_behavior(
                user_id=f"test_user_{i}",
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
        
        print(f"\nBot Detection Benchmark:")
        print(f"  Users analyzed: 10")
        print(f"  Total time: {bot_time:.2f}ms")
        print(f"  Average per user: {bot_time/10:.2f}ms")
        
        # Performance assertions
        assert sentiment_time / len(test_texts) < 1000  # Less than 1 second per text
        assert bot_time / 10 < 2000  # Less than 2 seconds per user analysis
        
        print("\n✅ PERFORMANCE BENCHMARKS PASSED")


# Run the tests
if __name__ == "__main__":
    async def run_tests():
        """Run all integration tests."""
        test_instance = TestAIProcessingEngine()
        
        # Initialize components
        sentiment_analyzer = SentimentAnalyzer()
        await sentiment_analyzer.initialize()
        
        bot_detector = BotDetector()
        await bot_detector.initialize()
        
        campaign_detector = CampaignDetector()
        await campaign_detector.initialize()
        
        governance_service = ModelGovernanceService()
        await governance_service.start()
        
        try:
            # Create test data
            sample_posts = [
                {
                    "post_id": "post_1",
                    "user_id": "user_1",
                    "platform": "twitter",
                    "content": "India is facing serious challenges with misinformation campaigns.",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metrics": {"likes": 45, "shares": 12, "comments": 8}
                },
                {
                    "post_id": "post_2",
                    "user_id": "user_2",
                    "platform": "twitter",
                    "content": "We must protect our nation from foreign interference.",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metrics": {"likes": 67, "shares": 23, "comments": 15}
                }
            ]
            
            sample_user = {
                "user_id": "test_user_123",
                "platform": "twitter",
                "account_created": (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z",
                "avg_posts_per_day": 3.5,
                "duplicate_content_ratio": 0.1,
                "engagement_consistency": 0.7
            }
            
            # Run tests
            print("🚀 Starting AI Processing Engine Integration Tests")
            
            await test_instance.test_sentiment_analysis_integration(sentiment_analyzer)
            await test_instance.test_bot_detection_integration(bot_detector, sample_user)
            await test_instance.test_campaign_detection_integration(campaign_detector, sample_posts)
            await test_instance.test_coordinated_behavior_detection(bot_detector)
            await test_instance.test_model_governance_integration(governance_service)
            await test_instance.test_performance_benchmarks(
                sentiment_analyzer, bot_detector, campaign_detector
            )
            
            # Run end-to-end test
            report = await test_instance.test_end_to_end_processing_pipeline(
                sentiment_analyzer, bot_detector, campaign_detector, sample_posts, sample_user
            )
            
            print("\n🎉 ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
            
        finally:
            await governance_service.stop()
    
    # Run the tests
    asyncio.run(run_tests())