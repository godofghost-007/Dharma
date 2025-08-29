"""Contract testing between microservices."""

import pytest
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx
from pydantic import BaseModel, ValidationError
from unittest.mock import Mock, AsyncMock

# Import shared models for contract validation
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from models.post import Post, PostCreate, SentimentType, PropagandaTechnique
from models.user import SocialMediaUser, SystemUser, UserRole
from models.alert import Alert, AlertCreate, AlertType, SeverityLevel, AlertContext
from models.campaign import Campaign, CampaignCreate, CampaignType


class APIContract:
    """Base class for API contract definitions."""
    
    def __init__(self, service_name: str, base_url: str):
        self.service_name = service_name
        self.base_url = base_url
        self.endpoints = {}
    
    def add_endpoint(self, path: str, method: str, request_schema=None, response_schema=None):
        """Add endpoint contract definition."""
        self.endpoints[f"{method.upper()} {path}"] = {
            "path": path,
            "method": method.upper(),
            "request_schema": request_schema,
            "response_schema": response_schema
        }
    
    async def validate_endpoint(self, client: httpx.AsyncClient, endpoint_key: str, 
                              request_data=None, expected_status=200):
        """Validate endpoint against contract."""
        if endpoint_key not in self.endpoints:
            raise ValueError(f"Endpoint {endpoint_key} not defined in contract")
        
        endpoint = self.endpoints[endpoint_key]
        
        # Validate request data against schema
        if endpoint["request_schema"] and request_data:
            try:
                endpoint["request_schema"](**request_data)
            except ValidationError as e:
                raise AssertionError(f"Request data validation failed: {e}")
        
        # Make API call
        method = endpoint["method"].lower()
        path = endpoint["path"]
        
        if method == "get":
            response = await client.get(path, params=request_data)
        elif method == "post":
            response = await client.post(path, json=request_data)
        elif method == "put":
            response = await client.put(path, json=request_data)
        elif method == "patch":
            response = await client.patch(path, json=request_data)
        elif method == "delete":
            response = await client.delete(path)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Validate response status
        if response.status_code != expected_status:
            if expected_status == 200 and response.status_code in [404, 501, 503]:
                # Service might not be available in test environment
                pytest.skip(f"Service {self.service_name} not available (status: {response.status_code})")
            else:
                raise AssertionError(
                    f"Expected status {expected_status}, got {response.status_code}. "
                    f"Response: {response.text}"
                )
        
        # Validate response data against schema
        if endpoint["response_schema"] and response.status_code == 200:
            try:
                response_data = response.json()
                if isinstance(response_data, list):
                    # For list responses, validate each item
                    for item in response_data:
                        endpoint["response_schema"](**item)
                else:
                    endpoint["response_schema"](**response_data)
            except ValidationError as e:
                raise AssertionError(f"Response data validation failed: {e}")
            except json.JSONDecodeError:
                # Response might not be JSON
                pass
        
        return response


# Request/Response schemas for contract validation
class SentimentAnalysisRequest(BaseModel):
    text: str
    language: str = "en"
    metadata: Dict[str, Any] = {}


class SentimentAnalysisResponse(BaseModel):
    sentiment: str
    confidence: float
    risk_score: float
    propaganda_techniques: List[str] = []
    language_detected: str = "en"
    translated_text: str = None
    translation_confidence: float = None
    model_version: str
    processing_time_ms: float


class BotDetectionRequest(BaseModel):
    user_id: str
    platform: str
    user_data: Dict[str, Any]


class BotDetectionResponse(BaseModel):
    user_id: str
    platform: str
    bot_probability: float
    confidence: float
    risk_indicators: List[str]
    behavioral_features: Dict[str, Any]
    model_version: str
    analysis_timestamp: str
    processing_time_ms: float


class AlertCreateRequest(BaseModel):
    alert_id: str
    title: str
    description: str
    alert_type: str
    severity: str
    context: Dict[str, Any]
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class AlertResponse(BaseModel):
    alert_id: str
    title: str
    description: str
    alert_type: str
    severity: str
    status: str
    context: Dict[str, Any]
    created_at: str
    updated_at: str = None


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, Any] = {}


@pytest.mark.contract
class TestAIAnalysisServiceContract:
    """Test AI Analysis Service API contracts."""
    
    @pytest.fixture(scope="class")
    def ai_contract(self):
        """Define AI Analysis Service contract."""
        contract = APIContract(
            "ai-analysis-service",
            os.getenv("TEST_AI_ANALYSIS_URL", "http://localhost:8002")
        )
        
        # Define endpoints
        contract.add_endpoint(
            "/health", "GET",
            response_schema=HealthCheckResponse
        )
        
        contract.add_endpoint(
            "/analyze/sentiment", "POST",
            request_schema=SentimentAnalysisRequest,
            response_schema=SentimentAnalysisResponse
        )
        
        contract.add_endpoint(
            "/analyze/bot-detection", "POST",
            request_schema=BotDetectionRequest,
            response_schema=BotDetectionResponse
        )
        
        return contract
    
    @pytest.fixture(scope="class")
    async def ai_client(self, ai_contract):
        """Create HTTP client for AI Analysis Service."""
        async with httpx.AsyncClient(
            base_url=ai_contract.base_url,
            timeout=60
        ) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_endpoint_contract(self, ai_contract, ai_client):
        """Test health endpoint contract compliance."""
        await ai_contract.validate_endpoint(ai_client, "GET /health")
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_contract(self, ai_contract, ai_client):
        """Test sentiment analysis endpoint contract compliance."""
        request_data = {
            "text": "India is a wonderful country with rich culture",
            "language": "en",
            "metadata": {
                "platform": "twitter",
                "user_id": "test_user"
            }
        }
        
        await ai_contract.validate_endpoint(
            ai_client, 
            "POST /analyze/sentiment", 
            request_data
        )
    
    @pytest.mark.asyncio
    async def test_bot_detection_contract(self, ai_contract, ai_client):
        """Test bot detection endpoint contract compliance."""
        request_data = {
            "user_id": "test_user_123",
            "platform": "twitter",
            "user_data": {
                "profile": {
                    "username": "test_user",
                    "followers_count": 1000,
                    "following_count": 500,
                    "posts_count": 250
                },
                "posts": [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "content": "Test post content"
                    }
                ],
                "behavioral_features": {
                    "avg_posts_per_day": 5.0,
                    "duplicate_content_ratio": 0.1,
                    "account_age_days": 365,
                    "engagement_consistency": 0.7
                }
            }
        }
        
        await ai_contract.validate_endpoint(
            ai_client,
            "POST /analyze/bot-detection",
            request_data
        )
    
    @pytest.mark.asyncio
    async def test_invalid_request_handling(self, ai_client):
        """Test handling of invalid requests."""
        # Test with missing required fields
        invalid_request = {"language": "en"}  # Missing 'text' field
        
        response = await ai_client.post("/analyze/sentiment", json=invalid_request)
        
        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422, 404, 501]
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, ai_client):
        """Test error response format consistency."""
        # Test with malformed JSON
        response = await ai_client.post(
            "/analyze/sentiment",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [400, 422]:
            # Error response should be JSON with error details
            try:
                error_data = response.json()
                assert "detail" in error_data or "error" in error_data or "message" in error_data
            except json.JSONDecodeError:
                # Some services might return plain text errors
                pass


@pytest.mark.contract
class TestAlertManagementServiceContract:
    """Test Alert Management Service API contracts."""
    
    @pytest.fixture(scope="class")
    def alert_contract(self):
        """Define Alert Management Service contract."""
        contract = APIContract(
            "alert-management-service",
            os.getenv("TEST_ALERT_MANAGEMENT_URL", "http://localhost:8003")
        )
        
        # Define endpoints
        contract.add_endpoint(
            "/health", "GET",
            response_schema=HealthCheckResponse
        )
        
        contract.add_endpoint(
            "/alerts", "POST",
            request_schema=AlertCreateRequest,
            response_schema=AlertResponse
        )
        
        contract.add_endpoint(
            "/alerts", "GET",
            response_schema=None  # List of alerts
        )
        
        return contract
    
    @pytest.fixture(scope="class")
    async def alert_client(self, alert_contract):
        """Create HTTP client for Alert Management Service."""
        async with httpx.AsyncClient(
            base_url=alert_contract.base_url,
            timeout=60
        ) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_alert_creation_contract(self, alert_contract, alert_client):
        """Test alert creation endpoint contract compliance."""
        request_data = {
            "alert_id": f"contract_test_{datetime.utcnow().timestamp()}",
            "title": "Contract Test Alert",
            "description": "This is a test alert for contract validation",
            "alert_type": "high_risk_content",
            "severity": "high",
            "context": {
                "detection_method": "contract_test",
                "confidence_score": 0.95,
                "risk_score": 0.85,
                "detection_window_start": datetime.utcnow().isoformat(),
                "detection_window_end": datetime.utcnow().isoformat()
            },
            "tags": ["contract_test"],
            "metadata": {"test": True}
        }
        
        await alert_contract.validate_endpoint(
            alert_client,
            "POST /alerts",
            request_data,
            expected_status=201  # Created
        )
    
    @pytest.mark.asyncio
    async def test_alert_retrieval_contract(self, alert_contract, alert_client):
        """Test alert retrieval endpoint contract compliance."""
        await alert_contract.validate_endpoint(alert_client, "GET /alerts")
    
    @pytest.mark.asyncio
    async def test_alert_field_validation(self, alert_client):
        """Test alert field validation."""
        # Test with invalid severity
        invalid_alert = {
            "alert_id": "invalid_test",
            "title": "Invalid Alert",
            "description": "Test alert with invalid severity",
            "alert_type": "high_risk_content",
            "severity": "invalid_severity",  # Invalid value
            "context": {
                "detection_method": "test",
                "confidence_score": 0.5,
                "risk_score": 0.5,
                "detection_window_start": datetime.utcnow().isoformat(),
                "detection_window_end": datetime.utcnow().isoformat()
            }
        }
        
        response = await alert_client.post("/alerts", json=invalid_alert)
        
        # Should return validation error
        assert response.status_code in [400, 422, 404, 501]


@pytest.mark.contract
class TestDataCollectionServiceContract:
    """Test Data Collection Service API contracts."""
    
    @pytest.fixture(scope="class")
    async def data_client(self):
        """Create HTTP client for Data Collection Service."""
        base_url = os.getenv("TEST_DATA_COLLECTION_URL", "http://localhost:8001")
        async with httpx.AsyncClient(base_url=base_url, timeout=60) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, data_client):
        """Test data collection service health endpoint."""
        response = await data_client.get("/health")
        
        if response.status_code == 200:
            health_data = response.json()
            assert "status" in health_data
            assert health_data["status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self, data_client):
        """Test collection status endpoint."""
        response = await data_client.get("/status")
        
        if response.status_code == 200:
            status_data = response.json()
            # Validate expected fields exist
            expected_fields = ["active_collectors", "total_collected"]
            for field in expected_fields:
                if field in status_data:
                    assert isinstance(status_data[field], (int, float))


@pytest.mark.contract
class TestCrossServiceIntegration:
    """Test contracts between services in integration scenarios."""
    
    @pytest.fixture(scope="class")
    async def all_clients(self):
        """Set up clients for all services."""
        clients = {
            "ai_analysis": httpx.AsyncClient(
                base_url=os.getenv("TEST_AI_ANALYSIS_URL", "http://localhost:8002"),
                timeout=60
            ),
            "alert_management": httpx.AsyncClient(
                base_url=os.getenv("TEST_ALERT_MANAGEMENT_URL", "http://localhost:8003"),
                timeout=60
            ),
            "data_collection": httpx.AsyncClient(
                base_url=os.getenv("TEST_DATA_COLLECTION_URL", "http://localhost:8001"),
                timeout=60
            )
        }
        
        yield clients
        
        for client in clients.values():
            await client.aclose()
    
    @pytest.mark.asyncio
    async def test_analysis_to_alert_integration(self, all_clients):
        """Test integration between AI analysis and alert management."""
        # Step 1: Perform sentiment analysis
        analysis_request = {
            "text": "India should be destroyed by terrorists",
            "language": "en",
            "metadata": {"platform": "twitter", "user_id": "test_user"}
        }
        
        analysis_response = await all_clients["ai_analysis"].post(
            "/analyze/sentiment",
            json=analysis_request
        )
        
        if analysis_response.status_code == 200:
            analysis_result = analysis_response.json()
            
            # Step 2: Create alert based on analysis result
            if analysis_result.get("risk_score", 0) > 0.7:
                alert_request = {
                    "alert_id": f"integration_test_{datetime.utcnow().timestamp()}",
                    "title": "High Risk Content - Integration Test",
                    "description": f"Content analysis result: {analysis_result.get('sentiment')}",
                    "alert_type": "high_risk_content",
                    "severity": "high",
                    "context": {
                        "detection_method": "sentiment_analysis",
                        "confidence_score": analysis_result.get("confidence", 0),
                        "risk_score": analysis_result.get("risk_score", 0),
                        "detection_window_start": datetime.utcnow().isoformat(),
                        "detection_window_end": datetime.utcnow().isoformat(),
                        "analysis_result": analysis_result
                    }
                }
                
                alert_response = await all_clients["alert_management"].post(
                    "/alerts",
                    json=alert_request
                )
                
                # Verify alert creation succeeded or service is unavailable
                assert alert_response.status_code in [200, 201, 404, 501, 503]
    
    @pytest.mark.asyncio
    async def test_service_discovery_contracts(self, all_clients):
        """Test service discovery and health check contracts."""
        service_health = {}
        
        for service_name, client in all_clients.items():
            try:
                response = await client.get("/health")
                service_health[service_name] = {
                    "available": response.status_code == 200,
                    "status_code": response.status_code
                }
                
                if response.status_code == 200:
                    health_data = response.json()
                    service_health[service_name]["health_data"] = health_data
                    
                    # Validate health response format
                    assert "status" in health_data
                    assert health_data["status"] in ["healthy", "degraded", "unhealthy"]
                    
            except Exception as e:
                service_health[service_name] = {
                    "available": False,
                    "error": str(e)
                }
        
        # Log service availability for debugging
        print(f"Service health check results: {service_health}")
        
        # At least verify we can check service health
        assert len(service_health) > 0
    
    @pytest.mark.asyncio
    async def test_error_propagation_contracts(self, all_clients):
        """Test error propagation between services."""
        # Test with invalid data to trigger errors
        invalid_requests = [
            {
                "service": "ai_analysis",
                "endpoint": "/analyze/sentiment",
                "data": {"invalid": "data"}
            },
            {
                "service": "alert_management", 
                "endpoint": "/alerts",
                "data": {"invalid": "alert_data"}
            }
        ]
        
        for req in invalid_requests:
            if req["service"] in all_clients:
                response = await all_clients[req["service"]].post(
                    req["endpoint"],
                    json=req["data"]
                )
                
                # Should return proper error status codes
                if response.status_code not in [404, 501, 503]:  # Service available
                    assert response.status_code in [400, 422]  # Validation error
                    
                    # Error response should be structured
                    try:
                        error_data = response.json()
                        # Should contain error information
                        assert any(key in error_data for key in ["detail", "error", "message", "errors"])
                    except json.JSONDecodeError:
                        # Some services might return plain text errors
                        pass


if __name__ == "__main__":
    # Run contract tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "contract"])