"""End-to-end workflow integration tests."""

import pytest
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx
from unittest.mock import Mock, AsyncMock, patch

# Import workflow components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services'))

from models.post import Post, PostCreate, Platform, SentimentType
from models.user import SocialMediaUser, UserRole
from models.alert import Alert, AlertType, SeverityLevel, AlertStatus
from models.campaign import Campaign, CampaignType


@pytest.mark.e2e
class TestDataIngestionWorkflow:
    """Test complete data ingestion workflow."""
    
    @pytest.fixture(scope="class")
    async def workflow_clients(self):
        """Set up clients for workflow testing."""
        clients = {
            "data_collection": httpx.AsyncClient(
                base_url=os.getenv("TEST_DATA_COLLECTION_URL", "http://localhost:8001"),
                timeout=60
            ),
            "ai_analysis": httpx.AsyncClient(
                base_url=os.getenv("TEST_AI_ANALYSIS_URL", "http://localhost:8002"),
                timeout=60
            ),
            "alert_management": httpx.AsyncClient(
                base_url=os.getenv("TEST_ALERT_MANAGEMENT_URL", "http://localhost:8003"),
                timeout=60
            )
        }
        
        yield clients
        
        for client in clients.values():
            await client.aclose()
    
    @pytest.mark.asyncio
    async def test_social_media_post_processing_workflow(self, workflow_clients):
        """Test complete workflow for processing social media posts."""
        # Step 1: Simulate data collection
        post_data = {
            "platform": "twitter",
            "post_id": f"e2e_test_post_{datetime.utcnow().timestamp()}",
            "user_id": "e2e_test_user_001",
            "content": "India should be destroyed by terrorists. This is anti-national propaganda spreading hate.",
            "timestamp": datetime.utcnow().isoformat(),
            "hashtags": ["anti-india", "terrorism", "propaganda"],
            "mentions": ["@suspicious_account"],
            "metrics": {
                "likes": 150,
                "shares": 75,
                "comments": 30,
                "views": 2000
            },
            "geolocation": {
                "country": "Pakistan",
                "region": "Punjab",
                "coordinates": [74.3587, 31.5204]
            }
        }
        
        # Step 2: Submit for AI analysis
        analysis_request = {
            "text": post_data["content"],
            "language": "en",
            "metadata": {
                "platform": post_data["platform"],
                "user_id": post_data["user_id"],
                "post_id": post_data["post_id"],
                "timestamp": post_data["timestamp"]
            }
        }
        
        sentiment_response = await workflow_clients["ai_analysis"].post(
            "/analyze/sentiment",
            json=analysis_request
        )
        
        if sentiment_response.status_code == 200:
            sentiment_result = sentiment_response.json()
            
            # Verify analysis results
            assert "sentiment" in sentiment_result
            assert "confidence" in sentiment_result
            assert "risk_score" in sentiment_result
            
            # Step 3: Check if alert should be generated
            if (sentiment_result.get("sentiment") == "anti_india" and 
                sentiment_result.get("risk_score", 0) > 0.7):
                
                # Step 4: Generate alert
                alert_data = {
                    "alert_id": f"e2e_alert_{datetime.utcnow().timestamp()}",
                    "title": "High-Risk Anti-India Content Detected",
                    "description": f"Suspicious content detected: {post_data['content'][:100]}...",
                    "alert_type": "high_risk_content",
                    "severity": "high",
                    "context": {
                        "detection_method": "sentiment_analysis",
                        "confidence_score": sentiment_result.get("confidence", 0),
                        "risk_score": sentiment_result.get("risk_score", 0),
                        "detection_window_start": datetime.utcnow().isoformat(),
                        "detection_window_end": datetime.utcnow().isoformat(),
                        "source_platform": post_data["platform"],
                        "source_user_ids": [post_data["user_id"]],
                        "source_post_ids": [post_data["post_id"]],
                        "content_samples": [post_data["content"]],
                        "keywords_matched": ["terrorists", "destroyed", "anti-national"],
                        "hashtags_involved": post_data["hashtags"],
                        "origin_country": post_data["geolocation"]["country"],
                        "volume_metrics": {
                            "likes": post_data["metrics"]["likes"],
                            "shares": post_data["metrics"]["shares"],
                            "engagement_rate": (post_data["metrics"]["likes"] + 
                                              post_data["metrics"]["shares"]) / post_data["metrics"]["views"]
                        }
                    }
                }
                
                alert_response = await workflow_clients["alert_management"].post(
                    "/alerts",
                    json=alert_data
                )
                
                if alert_response.status_code in [200, 201]:
                    created_alert = alert_response.json()
                    
                    # Step 5: Verify alert was created and can be retrieved
                    get_alert_response = await workflow_clients["alert_management"].get(
                        f"/alerts/{alert_data['alert_id']}"
                    )
                    
                    if get_alert_response.status_code == 200:
                        retrieved_alert = get_alert_response.json()
                        assert retrieved_alert["alert_id"] == alert_data["alert_id"]
                        assert retrieved_alert["severity"] == "high"
                        assert retrieved_alert["status"] == "new"
                        
                        # Step 6: Test alert workflow (acknowledge, investigate, resolve)
                        await self._test_alert_lifecycle(workflow_clients, alert_data["alert_id"])
    
    async def _test_alert_lifecycle(self, clients, alert_id):
        """Test complete alert lifecycle."""
        # Acknowledge alert
        acknowledge_data = {
            "status": "acknowledged",
            "acknowledged_by": "e2e_test_analyst",
            "notes": "Alert acknowledged for investigation"
        }
        
        ack_response = await clients["alert_management"].patch(
            f"/alerts/{alert_id}",
            json=acknowledge_data
        )
        
        if ack_response.status_code == 200:
            # Assign alert
            assign_data = {
                "assigned_to": "senior_analyst_001",
                "assigned_by": "supervisor_001"
            }
            
            assign_response = await clients["alert_management"].patch(
                f"/alerts/{alert_id}/assign",
                json=assign_data
            )
            
            # Resolve alert
            resolve_data = {
                "status": "resolved",
                "resolved_by": "senior_analyst_001",
                "resolution": "Confirmed as coordinated disinformation campaign. Users flagged for monitoring.",
                "actions_taken": [
                    "Added users to monitoring list",
                    "Reported to platform for content review",
                    "Updated threat intelligence database"
                ]
            }
            
            resolve_response = await clients["alert_management"].patch(
                f"/alerts/{alert_id}/resolve",
                json=resolve_data
            )
    
    @pytest.mark.asyncio
    async def test_bot_detection_workflow(self, workflow_clients):
        """Test bot detection and network analysis workflow."""
        # Step 1: Simulate suspicious user behavior data
        suspicious_users = []
        
        for i in range(5):  # Create a network of suspicious accounts
            user_data = {
                "user_id": f"e2e_bot_user_{i:03d}",
                "platform": "twitter",
                "user_data": {
                    "profile": {
                        "username": f"bot_account_{i:03d}",
                        "display_name": f"Bot Account {i}",
                        "followers_count": 10000 + (i * 1000),
                        "following_count": 50,  # Suspicious ratio
                        "posts_count": 5000,
                        "account_created": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                        "is_verified": False,
                        "bio": "Patriotic Indian citizen"  # Generic bio
                    },
                    "posts": [
                        {
                            "timestamp": (datetime.utcnow() - timedelta(minutes=j*5)).isoformat(),
                            "content": f"India is great! Jai Hind! #{j}" if j % 2 == 0 else f"Pakistan zindabad! #{j}"
                        }
                        for j in range(50)  # High posting frequency
                    ],
                    "behavioral_features": {
                        "avg_posts_per_day": 80.0,  # Very high
                        "posting_time_variance": 0.1,  # Very regular
                        "weekend_activity_ratio": 1.0,  # No difference
                        "duplicate_content_ratio": 0.9,  # Very high duplication
                        "avg_content_length": 50.0,
                        "hashtag_usage_frequency": 0.8,
                        "mention_usage_frequency": 0.1,
                        "avg_likes_per_post": 5.0,  # Low engagement
                        "avg_shares_per_post": 1.0,
                        "engagement_consistency": 0.1,  # Very low
                        "follower_following_ratio": 200.0,  # Suspicious ratio
                        "mutual_connections_ratio": 0.8,  # High coordination
                        "network_clustering_coefficient": 0.9,  # Highly connected
                        "account_age_days": 30,
                        "activity_burst_frequency": 0.8
                    }
                }
            }
            suspicious_users.append(user_data)
        
        # Step 2: Analyze each user for bot behavior
        bot_results = []
        
        for user_data in suspicious_users:
            bot_response = await workflow_clients["ai_analysis"].post(
                "/analyze/bot-detection",
                json=user_data
            )
            
            if bot_response.status_code == 200:
                bot_result = bot_response.json()
                bot_result["user_id"] = user_data["user_id"]
                bot_results.append(bot_result)
        
        # Step 3: Analyze for coordinated behavior
        if len(bot_results) >= 3:
            coordination_data = {
                "user_group": suspicious_users,
                "time_window_hours": 24.0,
                "analysis_type": "coordination"
            }
            
            coordination_response = await workflow_clients["ai_analysis"].post(
                "/analyze/coordination",
                json=coordination_data
            )
            
            if coordination_response.status_code == 200:
                coordination_result = coordination_response.json()
                
                # Step 4: Generate bot network alert if coordination detected
                if coordination_result.get("coordination_detected", False):
                    network_alert_data = {
                        "alert_id": f"e2e_bot_network_{datetime.utcnow().timestamp()}",
                        "title": "Coordinated Bot Network Detected",
                        "description": f"Network of {len(suspicious_users)} suspicious accounts showing coordinated behavior",
                        "alert_type": "bot_network_detected",
                        "severity": "critical",
                        "context": {
                            "detection_method": "bot_network_analysis",
                            "confidence_score": coordination_result.get("coordination_score", 0),
                            "risk_score": 0.95,
                            "detection_window_start": datetime.utcnow().isoformat(),
                            "detection_window_end": datetime.utcnow().isoformat(),
                            "source_platform": "twitter",
                            "source_user_ids": [user["user_id"] for user in suspicious_users],
                            "volume_metrics": {
                                "network_size": len(suspicious_users),
                                "coordination_score": coordination_result.get("coordination_score", 0),
                                "avg_bot_probability": sum(r.get("bot_probability", 0) for r in bot_results) / len(bot_results)
                            },
                            "patterns_detected": coordination_result.get("patterns_detected", [])
                        }
                    }
                    
                    network_alert_response = await workflow_clients["alert_management"].post(
                        "/alerts",
                        json=network_alert_data
                    )
                    
                    if network_alert_response.status_code in [200, 201]:
                        # Verify network alert was created
                        created_alert = network_alert_response.json()
                        assert created_alert["alert_type"] == "bot_network_detected"
                        assert created_alert["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_campaign_detection_workflow(self, workflow_clients):
        """Test campaign detection and analysis workflow."""
        # Step 1: Simulate coordinated campaign data
        campaign_posts = []
        base_content_templates = [
            "India's economy is failing because of {reason}",
            "The government is hiding the truth about {topic}",
            "Citizens should protest against {issue}",
            "International community condemns India for {action}"
        ]
        
        reasons = ["corruption", "poor policies", "international pressure"]
        topics = ["economic crisis", "social unrest", "military failures"]
        issues = ["rising prices", "unemployment", "infrastructure"]
        actions = ["human rights violations", "environmental damage", "trade disputes"]
        
        # Generate coordinated posts
        for i in range(20):
            template_idx = i % len(base_content_templates)
            template = base_content_templates[template_idx]
            
            if "{reason}" in template:
                content = template.format(reason=reasons[i % len(reasons)])
            elif "{topic}" in template:
                content = template.format(topic=topics[i % len(topics)])
            elif "{issue}" in template:
                content = template.format(issue=issues[i % len(issues)])
            elif "{action}" in template:
                content = template.format(action=actions[i % len(actions)])
            else:
                content = template
            
            post = {
                "post_id": f"e2e_campaign_post_{i:03d}",
                "user_id": f"campaign_user_{i % 5}",  # 5 users posting similar content
                "platform": "twitter",
                "content": content,
                "timestamp": (datetime.utcnow() - timedelta(minutes=i*10)).isoformat(),
                "hashtags": ["IndiaFailing", "TruthRevealed", "ProtestNow"],
                "metrics": {
                    "likes": 100 + (i * 10),
                    "shares": 50 + (i * 5),
                    "comments": 20 + (i * 2)
                }
            }
            campaign_posts.append(post)
        
        # Step 2: Analyze posts for campaign patterns
        campaign_analysis_data = {
            "posts": campaign_posts,
            "time_window_hours": 24.0,
            "similarity_threshold": 0.7,
            "coordination_threshold": 0.8
        }
        
        campaign_response = await workflow_clients["ai_analysis"].post(
            "/analyze/campaign",
            json=campaign_analysis_data
        )
        
        if campaign_response.status_code == 200:
            campaign_result = campaign_response.json()
            
            # Step 3: Generate campaign alert if detected
            if campaign_result.get("campaign_detected", False):
                campaign_alert_data = {
                    "alert_id": f"e2e_campaign_{datetime.utcnow().timestamp()}",
                    "title": "Coordinated Disinformation Campaign Detected",
                    "description": f"Coordinated campaign involving {len(set(p['user_id'] for p in campaign_posts))} users and {len(campaign_posts)} posts",
                    "alert_type": "coordinated_campaign",
                    "severity": "high",
                    "context": {
                        "detection_method": "campaign_analysis",
                        "confidence_score": campaign_result.get("coordination_score", 0),
                        "risk_score": campaign_result.get("impact_score", 0),
                        "detection_window_start": min(p["timestamp"] for p in campaign_posts),
                        "detection_window_end": max(p["timestamp"] for p in campaign_posts),
                        "source_platform": "twitter",
                        "source_user_ids": list(set(p["user_id"] for p in campaign_posts)),
                        "source_post_ids": [p["post_id"] for p in campaign_posts],
                        "content_samples": [p["content"] for p in campaign_posts[:5]],
                        "hashtags_involved": ["IndiaFailing", "TruthRevealed", "ProtestNow"],
                        "volume_metrics": {
                            "total_posts": len(campaign_posts),
                            "unique_users": len(set(p["user_id"] for p in campaign_posts)),
                            "total_engagement": sum(p["metrics"]["likes"] + p["metrics"]["shares"] for p in campaign_posts),
                            "coordination_score": campaign_result.get("coordination_score", 0)
                        },
                        "patterns_detected": campaign_result.get("patterns", [])
                    }
                }
                
                campaign_alert_response = await workflow_clients["alert_management"].post(
                    "/alerts",
                    json=campaign_alert_data
                )
                
                if campaign_alert_response.status_code in [200, 201]:
                    created_alert = campaign_alert_response.json()
                    assert created_alert["alert_type"] == "coordinated_campaign"
                    assert created_alert["severity"] == "high"


@pytest.mark.e2e
class TestMultiLanguageWorkflow:
    """Test multi-language content processing workflow."""
    
    @pytest.fixture(scope="class")
    async def ml_clients(self):
        """Set up clients for multi-language testing."""
        clients = {
            "ai_analysis": httpx.AsyncClient(
                base_url=os.getenv("TEST_AI_ANALYSIS_URL", "http://localhost:8002"),
                timeout=60
            ),
            "alert_management": httpx.AsyncClient(
                base_url=os.getenv("TEST_ALERT_MANAGEMENT_URL", "http://localhost:8003"),
                timeout=60
            )
        }
        
        yield clients
        
        for client in clients.values():
            await client.aclose()
    
    @pytest.mark.asyncio
    async def test_hindi_content_processing(self, ml_clients):
        """Test processing of Hindi content."""
        hindi_content = {
            "text": "भारत को नष्ट करना चाहिए। यह देश बुरा है और इसे खत्म होना चाहिए।",  # Anti-India content in Hindi
            "language": "hi",
            "metadata": {
                "platform": "twitter",
                "user_id": "hindi_test_user",
                "original_language": "hi"
            }
        }
        
        # Analyze Hindi content
        response = await ml_clients["ai_analysis"].post(
            "/analyze/sentiment",
            json=hindi_content
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Verify analysis includes translation
            assert "sentiment" in result
            assert "translated_text" in result or "language_detected" in result
            
            # If high risk, should generate alert
            if result.get("risk_score", 0) > 0.7:
                await self._create_multilingual_alert(ml_clients, hindi_content, result, "Hindi")
    
    @pytest.mark.asyncio
    async def test_bengali_content_processing(self, ml_clients):
        """Test processing of Bengali content."""
        bengali_content = {
            "text": "ভারত একটি খারাপ দেশ এবং এটি ধ্বংস হওয়া উচিত।",  # Anti-India content in Bengali
            "language": "bn",
            "metadata": {
                "platform": "twitter",
                "user_id": "bengali_test_user",
                "original_language": "bn"
            }
        }
        
        response = await ml_clients["ai_analysis"].post(
            "/analyze/sentiment",
            json=bengali_content
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("risk_score", 0) > 0.7:
                await self._create_multilingual_alert(ml_clients, bengali_content, result, "Bengali")
    
    @pytest.mark.asyncio
    async def test_urdu_content_processing(self, ml_clients):
        """Test processing of Urdu content."""
        urdu_content = {
            "text": "ہندوستان کو تباہ کر دینا چاہیے۔ یہ ملک برا ہے۔",  # Anti-India content in Urdu
            "language": "ur",
            "metadata": {
                "platform": "twitter",
                "user_id": "urdu_test_user",
                "original_language": "ur"
            }
        }
        
        response = await ml_clients["ai_analysis"].post(
            "/analyze/sentiment",
            json=urdu_content
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("risk_score", 0) > 0.7:
                await self._create_multilingual_alert(ml_clients, urdu_content, result, "Urdu")
    
    async def _create_multilingual_alert(self, clients, content, analysis_result, language):
        """Create alert for multilingual content."""
        alert_data = {
            "alert_id": f"e2e_multilang_{language.lower()}_{datetime.utcnow().timestamp()}",
            "title": f"High-Risk {language} Content Detected",
            "description": f"Anti-India content detected in {language}: {content['text'][:50]}...",
            "alert_type": "high_risk_content",
            "severity": "high",
            "context": {
                "detection_method": "multilingual_sentiment_analysis",
                "confidence_score": analysis_result.get("confidence", 0),
                "risk_score": analysis_result.get("risk_score", 0),
                "detection_window_start": datetime.utcnow().isoformat(),
                "detection_window_end": datetime.utcnow().isoformat(),
                "source_platform": content["metadata"]["platform"],
                "source_user_ids": [content["metadata"]["user_id"]],
                "content_samples": [content["text"]],
                "original_language": language.lower(),
                "translated_text": analysis_result.get("translated_text"),
                "translation_confidence": analysis_result.get("translation_confidence")
            }
        }
        
        response = await clients["alert_management"].post("/alerts", json=alert_data)
        
        if response.status_code in [200, 201]:
            created_alert = response.json()
            assert created_alert["alert_type"] == "high_risk_content"


@pytest.mark.e2e
class TestPerformanceWorkflow:
    """Test system performance under load."""
    
    @pytest.fixture(scope="class")
    async def perf_clients(self):
        """Set up clients for performance testing."""
        clients = {
            "ai_analysis": httpx.AsyncClient(
                base_url=os.getenv("TEST_AI_ANALYSIS_URL", "http://localhost:8002"),
                timeout=120  # Longer timeout for performance tests
            )
        }
        
        yield clients
        
        for client in clients.values():
            await client.aclose()
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_performance(self, perf_clients):
        """Test performance with concurrent analysis requests."""
        # Generate test content
        test_contents = [
            f"This is test content number {i} for performance testing. India is great!"
            for i in range(50)
        ]
        
        # Create analysis tasks
        async def analyze_content(content, client):
            start_time = datetime.utcnow()
            
            response = await client.post(
                "/analyze/sentiment",
                json={"text": content, "language": "en"}
            )
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            return {
                "status_code": response.status_code,
                "processing_time": processing_time,
                "success": response.status_code == 200
            }
        
        # Execute concurrent requests
        tasks = [
            analyze_content(content, perf_clients["ai_analysis"])
            for content in test_contents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze performance results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_requests = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
        
        if successful_requests:
            avg_processing_time = sum(r["processing_time"] for r in successful_requests) / len(successful_requests)
            max_processing_time = max(r["processing_time"] for r in successful_requests)
            
            # Performance assertions
            assert len(successful_requests) >= len(test_contents) * 0.8  # At least 80% success rate
            assert avg_processing_time < 5.0  # Average response time under 5 seconds
            assert max_processing_time < 10.0  # Max response time under 10 seconds
            
            print(f"Performance Results:")
            print(f"  Successful requests: {len(successful_requests)}/{len(test_contents)}")
            print(f"  Average processing time: {avg_processing_time:.2f}s")
            print(f"  Max processing time: {max_processing_time:.2f}s")
            print(f"  Failed requests: {len(failed_requests)}")


if __name__ == "__main__":
    # Run end-to-end tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])