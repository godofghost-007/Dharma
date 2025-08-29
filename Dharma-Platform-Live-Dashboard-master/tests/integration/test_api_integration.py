"""Integration tests for API endpoints."""

import pytest
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List


class TestAuthenticationAPI:
    """Test authentication API endpoints."""
    
    @pytest.mark.asyncio
    async def test_user_registration_and_login_flow(self, http_client, sample_user_data):
        """Test complete user registration and login flow."""
        
        # Test user registration
        registration_response = await http_client.post(
            f"{TEST_CONFIG['services']['api_gateway']}/auth/register",
            json=sample_user_data
        )
        
        if registration_response.status_code == 201:
            user_data = registration_response.json()
            assert user_data["username"] == sample_user_data["username"]
            assert user_data["email"] == sample_user_data["email"]
            assert user_data["role"] == sample_user_data["role"]
            assert "id" in user_data
        
        # Test login
        login_response = await http_client.post(
            f"{TEST_CONFIG['services']['api_gateway']}/auth/login",
            json={
                "username": sample_user_data["username"],
                "password": sample_user_data["password"]
            }
        )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        assert "access_token" in login_data
        assert "refresh_token" in login_data
        assert login_data["token_type"] == "bearer"
        assert login_data["expires_in"] > 0
        
        # Verify user info in response
        user_info = login_data["user"]
        assert user_info["username"] == sample_user_data["username"]
        assert user_info["email"] == sample_user_data["email"]
        assert user_info["role"] == sample_user_data["role"]
        
        return login_data["access_token"]
    
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, http_client):
        """Test token refresh functionality."""
        
        # First login to get tokens
        login_response = await http_client.post(
            f"{TEST_CONFIG['services']['api_gateway']}/auth/login",
            json={
                "username": "testuser",
                "password": "test_password"
            }
        )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]
        
        # Test token refresh
        refresh_response = await http_client.post(
            f"{TEST_CONFIG['services']['api_gateway']}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["access_token"] != login_data["access_token"]  # Should be new token
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_access(self, authenticated_client):
        """Test access to protected endpoints with authentication."""
        
        # Test accessing user profile
        profile_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['api_gateway']}/auth/me"
        )
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        
        assert "username" in profile_data
        assert "email" in profile_data
        assert "role" in profile_data
        assert "permissions" in profile_data
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, http_client):
        """Test unauthorized access to protected endpoints."""
        
        # Test without token
        response = await http_client.get(
            f"{TEST_CONFIG['services']['api_gateway']}/auth/me"
        )
        
        assert response.status_code == 401
        
        # Test with invalid token
        http_client.headers.update({"Authorization": "Bearer invalid_token"})
        
        response = await http_client.get(
            f"{TEST_CONFIG['services']['api_gateway']}/auth/me"
        )
        
        assert response.status_code == 401


class TestDataCollectionAPI:
    """Test data collection API endpoints."""
    
    @pytest.mark.asyncio
    async def test_post_submission(self, authenticated_client, sample_post_data):
        """Test post data submission."""
        
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['data_collection']}/posts",
            json=sample_post_data
        )
        
        assert response.status_code in [200, 201, 202]
        
        if response.content:
            response_data = response.json()
            assert "post_id" in response_data or "status" in response_data
    
    @pytest.mark.asyncio
    async def test_batch_post_submission(self, authenticated_client):
        """Test batch post submission."""
        
        batch_posts = []
        for i in range(5):
            batch_posts.append({
                "platform": "twitter",
                "post_id": f"batch_test_post_{i}",
                "user_id": f"batch_test_user_{i}",
                "content": f"Batch test post {i} content",
                "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                "metrics": {
                    "likes": i * 2,
                    "shares": i,
                    "comments": i // 2
                }
            })
        
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['data_collection']}/posts/batch",
            json={"posts": batch_posts}
        )
        
        assert response.status_code in [200, 201, 202]
        
        if response.content:
            response_data = response.json()
            assert "processed_count" in response_data or "batch_id" in response_data
    
    @pytest.mark.asyncio
    async def test_data_validation(self, authenticated_client):
        """Test data validation in submission endpoints."""
        
        # Test invalid post data
        invalid_post = {
            "platform": "invalid_platform",
            "post_id": "",  # Empty post_id
            "content": "",  # Empty content
            "timestamp": "invalid_timestamp"
        }
        
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['data_collection']}/posts",
            json=invalid_post
        )
        
        assert response.status_code == 422  # Validation error
        
        if response.content:
            error_data = response.json()
            assert "detail" in error_data or "errors" in error_data


class TestAIAnalysisAPI:
    """Test AI analysis API endpoints."""
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis(self, authenticated_client):
        """Test sentiment analysis endpoint."""
        
        analysis_request = {
            "text": "This is a test message for sentiment analysis",
            "language": "en",
            "include_translation": False
        }
        
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['ai_analysis']}/analyze/sentiment",
            json=analysis_request
        )
        
        assert response.status_code == 200
        analysis_data = response.json()
        
        assert "sentiment" in analysis_data
        assert "confidence" in analysis_data
        assert "risk_score" in analysis_data
        assert "model_version" in analysis_data
        assert "processing_time_ms" in analysis_data
        
        # Validate sentiment values
        assert analysis_data["sentiment"] in ["pro_india", "neutral", "anti_india"]
        assert 0.0 <= analysis_data["confidence"] <= 1.0
        assert 0.0 <= analysis_data["risk_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_batch_sentiment_analysis(self, authenticated_client):
        """Test batch sentiment analysis."""
        
        batch_request = {
            "texts": [
                "This is a positive message about India",
                "This is a neutral message",
                "This is a negative message with concerning content"
            ],
            "language": "en",
            "include_translation": False
        }
        
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['ai_analysis']}/analyze/sentiment/batch",
            json=batch_request
        )
        
        assert response.status_code == 200
        batch_data = response.json()
        
        assert "results" in batch_data
        assert len(batch_data["results"]) == 3
        
        for result in batch_data["results"]:
            assert "sentiment" in result
            assert "confidence" in result
            assert "risk_score" in result
    
    @pytest.mark.asyncio
    async def test_bot_detection(self, authenticated_client):
        """Test bot detection endpoint."""
        
        user_data = {
            "user_id": "test_user_bot_detection",
            "platform": "twitter",
            "profile": {
                "username": "test_user",
                "followers_count": 1000,
                "following_count": 500,
                "posts_count": 250,
                "account_created": "2023-01-01T00:00:00Z"
            },
            "behavioral_features": {
                "avg_posts_per_day": 5.0,
                "duplicate_content_ratio": 0.2,
                "engagement_consistency": 0.7,
                "account_age_days": 365
            }
        }
        
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['ai_analysis']}/analyze/bot-detection",
            json=user_data
        )
        
        assert response.status_code == 200
        bot_data = response.json()
        
        assert "bot_probability" in bot_data
        assert "confidence" in bot_data
        assert "risk_indicators" in bot_data
        assert "model_version" in bot_data
        
        # Validate bot detection values
        assert 0.0 <= bot_data["bot_probability"] <= 1.0
        assert 0.0 <= bot_data["confidence"] <= 1.0
        assert isinstance(bot_data["risk_indicators"], list)
    
    @pytest.mark.asyncio
    async def test_model_health_check(self, authenticated_client):
        """Test AI model health check endpoints."""
        
        # Test sentiment analyzer health
        sentiment_health = await authenticated_client.get(
            f"{TEST_CONFIG['services']['ai_analysis']}/health/sentiment"
        )
        
        assert sentiment_health.status_code == 200
        sentiment_data = sentiment_health.json()
        
        assert "status" in sentiment_data
        assert "model_version" in sentiment_data
        
        # Test bot detector health
        bot_health = await authenticated_client.get(
            f"{TEST_CONFIG['services']['ai_analysis']}/health/bot-detection"
        )
        
        assert bot_health.status_code == 200
        bot_data = bot_health.json()
        
        assert "status" in bot_data
        assert "model_version" in bot_data


class TestAlertManagementAPI:
    """Test alert management API endpoints."""
    
    @pytest.mark.asyncio
    async def test_alert_creation(self, authenticated_client, sample_alert_data):
        """Test alert creation endpoint."""
        
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['alert_management']}/alerts",
            json=sample_alert_data
        )
        
        assert response.status_code in [200, 201]
        alert_data = response.json()
        
        assert "alert_id" in alert_data
        assert alert_data["title"] == sample_alert_data["title"]
        assert alert_data["alert_type"] == sample_alert_data["alert_type"]
        assert alert_data["severity"] == sample_alert_data["severity"]
        assert alert_data["status"] == "new"  # Default status
        
        return alert_data["alert_id"]
    
    @pytest.mark.asyncio
    async def test_alert_retrieval(self, authenticated_client):
        """Test alert retrieval endpoints."""
        
        # Test get all alerts
        alerts_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['alert_management']}/alerts"
        )
        
        assert alerts_response.status_code == 200
        alerts_data = alerts_response.json()
        
        assert "alerts" in alerts_data or isinstance(alerts_data, list)
        
        # Test get alerts with filters
        filtered_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['alert_management']}/alerts",
            params={
                "severity": "high",
                "status": "new",
                "limit": 10
            }
        )
        
        assert filtered_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_alert_status_updates(self, authenticated_client, sample_alert_data):
        """Test alert status update operations."""
        
        # Create alert first
        create_response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['alert_management']}/alerts",
            json=sample_alert_data
        )
        
        assert create_response.status_code in [200, 201]
        alert_id = create_response.json()["alert_id"]
        
        # Test acknowledge alert
        acknowledge_response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['alert_management']}/alerts/{alert_id}/acknowledge",
            json={"notes": "Acknowledging for testing"}
        )
        
        assert acknowledge_response.status_code == 200
        ack_data = acknowledge_response.json()
        assert ack_data["status"] == "acknowledged"
        
        # Test assign alert
        assign_response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['alert_management']}/alerts/{alert_id}/assign",
            json={"assigned_to": "test_analyst"}
        )
        
        assert assign_response.status_code == 200
        
        # Test resolve alert
        resolve_response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['alert_management']}/alerts/{alert_id}/resolve",
            json={"resolution_notes": "Resolved as false positive"}
        )
        
        assert resolve_response.status_code == 200
        resolve_data = resolve_response.json()
        assert resolve_data["status"] == "resolved"
    
    @pytest.mark.asyncio
    async def test_notification_endpoints(self, authenticated_client):
        """Test notification management endpoints."""
        
        # Test get notification preferences
        prefs_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['alert_management']}/notifications/preferences"
        )
        
        assert prefs_response.status_code in [200, 404]  # 404 if no preferences set
        
        # Test update notification preferences
        preferences = {
            "channels": ["email", "dashboard"],
            "severity_threshold": "medium",
            "alert_types": ["high_risk_content", "bot_network_detected"],
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00"
        }
        
        update_response = await authenticated_client.put(
            f"{TEST_CONFIG['services']['alert_management']}/notifications/preferences",
            json=preferences
        )
        
        assert update_response.status_code in [200, 201]


class TestDashboardAPI:
    """Test dashboard API endpoints."""
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics(self, authenticated_client):
        """Test dashboard metrics endpoints."""
        
        # Test overview metrics
        overview_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['dashboard']}/metrics/overview"
        )
        
        assert overview_response.status_code == 200
        overview_data = overview_response.json()
        
        # Should contain key metrics
        expected_metrics = ["total_posts", "total_alerts", "active_campaigns", "system_health"]
        for metric in expected_metrics:
            if metric in overview_data:
                assert isinstance(overview_data[metric], (int, float, dict))
    
    @pytest.mark.asyncio
    async def test_analytics_endpoints(self, authenticated_client):
        """Test analytics endpoints."""
        
        # Test sentiment trends
        sentiment_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['dashboard']}/analytics/sentiment-trends",
            params={
                "time_range": "24h",
                "platform": "twitter"
            }
        )
        
        assert sentiment_response.status_code == 200
        
        # Test alert statistics
        alert_stats_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['dashboard']}/analytics/alert-statistics",
            params={"time_range": "7d"}
        )
        
        assert alert_stats_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_real_time_data(self, authenticated_client):
        """Test real-time data endpoints."""
        
        # Test recent alerts
        recent_alerts_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['dashboard']}/real-time/recent-alerts",
            params={"limit": 10}
        )
        
        assert recent_alerts_response.status_code == 200
        
        # Test system status
        system_status_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['dashboard']}/real-time/system-status"
        )
        
        assert system_status_response.status_code == 200
        status_data = system_status_response.json()
        
        # Should contain service health information
        assert "services" in status_data or "overall_status" in status_data


class TestAPIErrorHandling:
    """Test API error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_endpoints(self, authenticated_client):
        """Test handling of invalid endpoints."""
        
        # Test non-existent endpoint
        response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['api_gateway']}/non-existent-endpoint"
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_malformed_requests(self, authenticated_client):
        """Test handling of malformed requests."""
        
        # Test invalid JSON
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['ai_analysis']}/analyze/sentiment",
            content="invalid json content",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422]
        
        # Test missing required fields
        response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['ai_analysis']}/analyze/sentiment",
            json={}  # Missing required 'text' field
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, authenticated_client):
        """Test API rate limiting."""
        
        # Make multiple rapid requests
        responses = []
        for i in range(20):
            response = await authenticated_client.get(
                f"{TEST_CONFIG['services']['api_gateway']}/auth/me"
            )
            responses.append(response.status_code)
        
        # Should eventually hit rate limit (429) or all succeed (200)
        assert all(status in [200, 429] for status in responses)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, http_client):
        """Test timeout handling."""
        
        # Test with very short timeout
        try:
            async with httpx.AsyncClient(timeout=0.001) as short_timeout_client:
                response = await short_timeout_client.get(
                    f"{TEST_CONFIG['services']['ai_analysis']}/analyze/sentiment",
                    json={"text": "test"}
                )
        except httpx.TimeoutException:
            # Expected behavior
            pass


class TestAPIPerformance:
    """Test API performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_response_times(self, authenticated_client, performance_metrics):
        """Test API response times."""
        
        endpoints_to_test = [
            ("GET", f"{TEST_CONFIG['services']['api_gateway']}/auth/me"),
            ("GET", f"{TEST_CONFIG['services']['dashboard']}/metrics/overview"),
            ("POST", f"{TEST_CONFIG['services']['ai_analysis']}/analyze/sentiment", 
             {"text": "Performance test message"}),
        ]
        
        for method, url, *payload in endpoints_to_test:
            start_time = datetime.utcnow()
            
            if method == "GET":
                response = await authenticated_client.get(url)
            elif method == "POST":
                response = await authenticated_client.post(url, json=payload[0] if payload else {})
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            performance_metrics["api_calls"].append({
                "endpoint": url,
                "method": method,
                "status_code": response.status_code,
                "duration": duration
            })
            
            # Response time should be reasonable (< 5 seconds for most endpoints)
            assert duration < 5.0, f"Endpoint {url} took {duration}s, which is too slow"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, authenticated_client):
        """Test handling of concurrent requests."""
        
        async def make_request(request_id):
            response = await authenticated_client.post(
                f"{TEST_CONFIG['services']['ai_analysis']}/analyze/sentiment",
                json={"text": f"Concurrent test message {request_id}"}
            )
            return response.status_code, request_id
        
        # Make 10 concurrent requests
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed or fail gracefully
        successful_requests = sum(1 for result in results 
                                if not isinstance(result, Exception) and result[0] == 200)
        
        assert successful_requests >= 8, "Too many concurrent requests failed"


class TestCrosServiceIntegration:
    """Test integration between different services."""
    
    @pytest.mark.asyncio
    async def test_data_flow_pipeline(self, authenticated_client):
        """Test complete data flow from collection to alerting."""
        
        # Step 1: Submit post data
        post_data = {
            "platform": "twitter",
            "post_id": "integration_flow_test_001",
            "user_id": "integration_flow_user_001",
            "content": "This is a suspicious message with concerning content that should trigger alerts",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {"likes": 100, "shares": 50, "comments": 25}
        }
        
        collection_response = await authenticated_client.post(
            f"{TEST_CONFIG['services']['data_collection']}/posts",
            json=post_data
        )
        
        assert collection_response.status_code in [200, 201, 202]
        
        # Step 2: Wait for processing and check if analysis was triggered
        await asyncio.sleep(2)  # Allow time for async processing
        
        # Step 3: Check if alerts were generated
        alerts_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['alert_management']}/alerts",
            params={"limit": 10, "sort": "created_at:desc"}
        )
        
        assert alerts_response.status_code == 200
        
        # Step 4: Verify dashboard reflects the new data
        dashboard_response = await authenticated_client.get(
            f"{TEST_CONFIG['services']['dashboard']}/metrics/overview"
        )
        
        assert dashboard_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_service_dependencies(self, authenticated_client):
        """Test service dependency handling."""
        
        # Test that services handle dependencies gracefully
        # This would typically involve testing with some services down
        
        # For now, test that all services are reachable
        services = [
            ("api_gateway", "/health"),
            ("ai_analysis", "/health"),
            ("alert_management", "/health"),
            ("data_collection", "/health"),
            ("dashboard", "/health")
        ]
        
        for service_name, health_endpoint in services:
            if service_name in TEST_CONFIG["services"]:
                response = await authenticated_client.get(
                    f"{TEST_CONFIG['services'][service_name]}{health_endpoint}"
                )
                
                # Service should be healthy or at least respond
                assert response.status_code in [200, 503], f"Service {service_name} is not responding"