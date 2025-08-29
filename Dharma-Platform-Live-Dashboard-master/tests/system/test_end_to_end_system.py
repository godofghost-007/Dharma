"""
Comprehensive end-to-end system integration tests
Tests complete workflows from data collection to alerting
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import aiohttp
import asyncpg
import motor.motor_asyncio
import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch

from shared.models.post import Post
from shared.models.alert import Alert
from shared.models.campaign import Campaign
from shared.models.user import User


class SystemTestConfig:
    """Configuration for system tests"""
    
    # Service endpoints
    API_GATEWAY_URL = "http://localhost:8000"
    DATA_COLLECTION_URL = "http://localhost:8001"
    AI_ANALYSIS_URL = "http://localhost:8002"
    ALERT_MANAGEMENT_URL = "http://localhost:8003"
    DASHBOARD_URL = "http://localhost:8501"
    
    # Database connections
    MONGODB_URL = "mongodb://localhost:27017/dharma_test"
    POSTGRESQL_URL = "postgresql://postgres:password@localhost:5432/dharma_test"
    ELASTICSEARCH_URL = "http://localhost:9200"
    REDIS_URL = "redis://localhost:6379/0"
    
    # Test data
    TEST_TIMEOUT = 300  # 5 minutes for complete workflow
    PERFORMANCE_THRESHOLD = 5.0  # seconds for analysis completion


@pytest.fixture
async def system_clients():
    """Initialize all system clients for testing"""
    clients = {}
    
    # HTTP client for API calls
    clients['http'] = aiohttp.ClientSession()
    
    # Database clients
    clients['mongodb'] = motor.motor_asyncio.AsyncIOMotorClient(SystemTestConfig.MONGODB_URL)
    clients['postgresql'] = await asyncpg.connect(SystemTestConfig.POSTGRESQL_URL)
    clients['elasticsearch'] = AsyncElasticsearch([SystemTestConfig.ELASTICSEARCH_URL])
    clients['redis'] = redis.from_url(SystemTestConfig.REDIS_URL)
    
    yield clients
    
    # Cleanup
    await clients['http'].close()
    clients['mongodb'].close()
    await clients['postgresql'].close()
    await clients['elasticsearch'].close()
    await clients['redis'].close()


@pytest.fixture
async def test_user(system_clients):
    """Create test user for authentication"""
    user_data = {
        "username": "test_analyst",
        "email": "test@dharma.gov",
        "password": "test_password_123",
        "role": "analyst"
    }
    
    # Register user
    async with system_clients['http'].post(
        f"{SystemTestConfig.API_GATEWAY_URL}/api/v1/auth/register",
        json=user_data
    ) as response:
        assert response.status == 201
        user = await response.json()
    
    # Login to get token
    async with system_clients['http'].post(
        f"{SystemTestConfig.API_GATEWAY_URL}/api/v1/auth/login",
        json={"username": user_data["username"], "password": user_data["password"]}
    ) as response:
        assert response.status == 200
        auth_data = await response.json()
        user['token'] = auth_data['access_token']
    
    return user


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""
    
    async def test_complete_data_processing_workflow(self, system_clients, test_user):
        """Test complete workflow from data collection to alert generation"""
        
        # Step 1: Submit data collection request
        collection_request = {
            "platform": "twitter",
            "keywords": ["test_disinformation", "anti_india"],
            "max_results": 10,
            "priority": "high"
        }
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        async with system_clients['http'].post(
            f"{SystemTestConfig.DATA_COLLECTION_URL}/api/v1/collect",
            json=collection_request,
            headers=headers
        ) as response:
            assert response.status == 202
            collection_job = await response.json()
            job_id = collection_job['job_id']
        
        # Step 2: Wait for data collection to complete
        collection_complete = False
        start_time = time.time()
        
        while not collection_complete and (time.time() - start_time) < 60:
            async with system_clients['http'].get(
                f"{SystemTestConfig.DATA_COLLECTION_URL}/api/v1/jobs/{job_id}",
                headers=headers
            ) as response:
                job_status = await response.json()
                if job_status['status'] == 'completed':
                    collection_complete = True
                    collected_posts = job_status['results']
                    break
            await asyncio.sleep(2)
        
        assert collection_complete, "Data collection did not complete in time"
        assert len(collected_posts) > 0, "No posts were collected"
        
        # Step 3: Verify data is stored in MongoDB
        db = system_clients['mongodb'].dharma_test
        posts_collection = db.posts
        
        stored_posts = await posts_collection.find(
            {"collection_job_id": job_id}
        ).to_list(length=None)
        
        assert len(stored_posts) == len(collected_posts)
        
        # Step 4: Wait for AI analysis to complete
        analysis_complete = False
        start_time = time.time()
        
        while not analysis_complete and (time.time() - start_time) < SystemTestConfig.PERFORMANCE_THRESHOLD:
            analyzed_posts = await posts_collection.find(
                {
                    "collection_job_id": job_id,
                    "analysis_results.sentiment": {"$exists": True}
                }
            ).to_list(length=None)
            
            if len(analyzed_posts) == len(collected_posts):
                analysis_complete = True
                break
            await asyncio.sleep(1)
        
        assert analysis_complete, "AI analysis did not complete within performance threshold"
        
        # Step 5: Verify analysis results
        for post in analyzed_posts:
            analysis = post['analysis_results']
            assert 'sentiment' in analysis
            assert 'confidence' in analysis
            assert 'bot_probability' in analysis
            assert analysis['confidence'] >= 0.0 and analysis['confidence'] <= 1.0
        
        # Step 6: Check for campaign detection
        campaigns_collection = db.campaigns
        detected_campaigns = await campaigns_collection.find(
            {"related_posts": {"$in": [str(post['_id']) for post in analyzed_posts]}}
        ).to_list(length=None)
        
        # Step 7: Verify alert generation for high-risk content
        high_risk_posts = [
            post for post in analyzed_posts 
            if post['analysis_results'].get('risk_score', 0) > 0.7
        ]
        
        if high_risk_posts:
            # Check PostgreSQL for generated alerts
            alerts_query = """
                SELECT * FROM alerts 
                WHERE created_at >= $1 
                AND status = 'new'
            """
            alerts = await system_clients['postgresql'].fetch(
                alerts_query, 
                datetime.utcnow() - timedelta(minutes=5)
            )
            
            assert len(alerts) > 0, "No alerts generated for high-risk content"
        
        # Step 8: Verify data is searchable in Elasticsearch
        await asyncio.sleep(2)  # Allow time for ES indexing
        
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"collection_job_id": job_id}},
                        {"exists": {"field": "analysis_results.sentiment"}}
                    ]
                }
            }
        }
        
        es_results = await system_clients['elasticsearch'].search(
            index="posts",
            body=search_query
        )
        
        assert es_results['hits']['total']['value'] > 0, "Posts not indexed in Elasticsearch"
        
        # Step 9: Test dashboard API endpoints
        async with system_clients['http'].get(
            f"{SystemTestConfig.API_GATEWAY_URL}/api/v1/dashboard/overview",
            headers=headers
        ) as response:
            assert response.status == 200
            dashboard_data = await response.json()
            assert 'total_posts' in dashboard_data
            assert 'active_alerts' in dashboard_data
        
        return {
            "job_id": job_id,
            "collected_posts": len(collected_posts),
            "analyzed_posts": len(analyzed_posts),
            "detected_campaigns": len(detected_campaigns),
            "generated_alerts": len(alerts) if high_risk_posts else 0
        }
    
    async def test_real_time_processing_workflow(self, system_clients, test_user):
        """Test real-time data processing and alerting"""
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        # Step 1: Start real-time monitoring
        monitor_request = {
            "keywords": ["urgent_test", "critical_alert"],
            "platforms": ["twitter", "youtube"],
            "alert_threshold": 0.8
        }
        
        async with system_clients['http'].post(
            f"{SystemTestConfig.DATA_COLLECTION_URL}/api/v1/monitor/start",
            json=monitor_request,
            headers=headers
        ) as response:
            assert response.status == 200
            monitor_session = await response.json()
            session_id = monitor_session['session_id']
        
        # Step 2: Inject test data to trigger real-time processing
        test_post = {
            "platform": "twitter",
            "content": "This is urgent_test content with anti-India sentiment for testing",
            "user_id": "test_user_123",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"test": True, "session_id": session_id}
        }
        
        async with system_clients['http'].post(
            f"{SystemTestConfig.DATA_COLLECTION_URL}/api/v1/ingest",
            json=test_post,
            headers=headers
        ) as response:
            assert response.status == 202
        
        # Step 3: Wait for real-time processing and alert generation
        alert_generated = False
        start_time = time.time()
        
        while not alert_generated and (time.time() - start_time) < 30:
            alerts_query = """
                SELECT * FROM alerts 
                WHERE created_at >= $1 
                AND title LIKE '%urgent_test%'
            """
            alerts = await system_clients['postgresql'].fetch(
                alerts_query,
                datetime.utcnow() - timedelta(minutes=1)
            )
            
            if alerts:
                alert_generated = True
                break
            await asyncio.sleep(2)
        
        assert alert_generated, "Real-time alert not generated within expected time"
        
        # Step 4: Stop monitoring
        async with system_clients['http'].post(
            f"{SystemTestConfig.DATA_COLLECTION_URL}/api/v1/monitor/stop/{session_id}",
            headers=headers
        ) as response:
            assert response.status == 200
        
        return {"session_id": session_id, "alerts_generated": len(alerts)}
    
    async def test_campaign_detection_workflow(self, system_clients, test_user):
        """Test coordinated campaign detection across multiple posts"""
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        # Step 1: Inject coordinated posts that should trigger campaign detection
        coordinated_posts = [
            {
                "platform": "twitter",
                "content": "Identical coordinated message for campaign test #coordination",
                "user_id": f"bot_user_{i}",
                "timestamp": (datetime.utcnow() + timedelta(seconds=i)).isoformat(),
                "metadata": {"test_campaign": True}
            }
            for i in range(5)
        ]
        
        post_ids = []
        for post in coordinated_posts:
            async with system_clients['http'].post(
                f"{SystemTestConfig.DATA_COLLECTION_URL}/api/v1/ingest",
                json=post,
                headers=headers
            ) as response:
                assert response.status == 202
                result = await response.json()
                post_ids.append(result['post_id'])
        
        # Step 2: Wait for campaign detection
        campaign_detected = False
        start_time = time.time()
        
        while not campaign_detected and (time.time() - start_time) < 60:
            db = system_clients['mongodb'].dharma_test
            campaigns = await db.campaigns.find(
                {"detection_date": {"$gte": datetime.utcnow() - timedelta(minutes=2)}}
            ).to_list(length=None)
            
            for campaign in campaigns:
                if len(campaign.get('participants', [])) >= 3:  # Coordinated behavior threshold
                    campaign_detected = True
                    detected_campaign = campaign
                    break
            
            if campaign_detected:
                break
            await asyncio.sleep(3)
        
        assert campaign_detected, "Campaign detection did not trigger for coordinated posts"
        
        # Step 3: Verify campaign analysis results
        assert detected_campaign['coordination_score'] > 0.5
        assert len(detected_campaign['participants']) >= 3
        assert 'network_graph' in detected_campaign
        
        return {
            "campaign_id": str(detected_campaign['_id']),
            "coordination_score": detected_campaign['coordination_score'],
            "participants": len(detected_campaign['participants'])
        }


class TestPerformanceRequirements:
    """Test system performance under realistic load"""
    
    async def test_concurrent_analysis_performance(self, system_clients, test_user):
        """Test system performance with concurrent analysis requests"""
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        # Generate batch of posts for analysis
        test_posts = [
            {
                "content": f"Test post {i} with various sentiment content for performance testing",
                "platform": "twitter",
                "user_id": f"perf_user_{i}",
                "timestamp": datetime.utcnow().isoformat()
            }
            for i in range(100)
        ]
        
        # Submit all posts concurrently
        start_time = time.time()
        
        tasks = []
        for post in test_posts:
            task = system_clients['http'].post(
                f"{SystemTestConfig.AI_ANALYSIS_URL}/api/v1/analyze/sentiment",
                json=post,
                headers=headers
            )
            tasks.append(task)
        
        # Wait for all analyses to complete
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify performance requirements
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) >= 95, "Less than 95% success rate for concurrent requests"
        assert total_time < 30, f"Batch analysis took {total_time}s, exceeds 30s threshold"
        
        # Verify analysis quality
        for response in successful_responses[:10]:  # Check first 10 responses
            if hasattr(response, 'json'):
                result = await response.json()
                assert 'sentiment' in result
                assert 'confidence' in result
        
        return {
            "total_posts": len(test_posts),
            "successful_analyses": len(successful_responses),
            "total_time": total_time,
            "throughput": len(successful_responses) / total_time
        }
    
    async def test_database_query_performance(self, system_clients):
        """Test database query performance under load"""
        
        # Test MongoDB aggregation performance
        db = system_clients['mongodb'].dharma_test
        
        start_time = time.time()
        
        # Complex aggregation query
        pipeline = [
            {"$match": {"analysis_results.sentiment": {"$exists": True}}},
            {"$group": {
                "_id": "$analysis_results.sentiment",
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$analysis_results.confidence"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        results = await db.posts.aggregate(pipeline).to_list(length=None)
        mongo_time = time.time() - start_time
        
        assert mongo_time < 10, f"MongoDB aggregation took {mongo_time}s, exceeds 10s threshold"
        
        # Test PostgreSQL query performance
        start_time = time.time()
        
        complex_query = """
            SELECT 
                severity,
                COUNT(*) as alert_count,
                AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at))) as avg_response_time
            FROM alerts 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY severity
            ORDER BY alert_count DESC
        """
        
        pg_results = await system_clients['postgresql'].fetch(complex_query)
        pg_time = time.time() - start_time
        
        assert pg_time < 5, f"PostgreSQL query took {pg_time}s, exceeds 5s threshold"
        
        # Test Elasticsearch search performance
        start_time = time.time()
        
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"timestamp": {"gte": "now-1d"}}},
                        {"exists": {"field": "analysis_results.sentiment"}}
                    ]
                }
            },
            "aggs": {
                "sentiment_distribution": {
                    "terms": {"field": "analysis_results.sentiment"}
                },
                "platform_breakdown": {
                    "terms": {"field": "platform"}
                }
            }
        }
        
        es_results = await system_clients['elasticsearch'].search(
            index="posts",
            body=search_query
        )
        es_time = time.time() - start_time
        
        assert es_time < 3, f"Elasticsearch search took {es_time}s, exceeds 3s threshold"
        
        return {
            "mongodb_time": mongo_time,
            "postgresql_time": pg_time,
            "elasticsearch_time": es_time
        }


class TestErrorHandlingAndRecovery:
    """Test system error handling and recovery scenarios"""
    
    async def test_service_failure_recovery(self, system_clients, test_user):
        """Test system behavior when individual services fail"""
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        # Test graceful degradation when AI service is unavailable
        # Simulate by sending request to non-existent endpoint
        try:
            async with system_clients['http'].post(
                f"{SystemTestConfig.AI_ANALYSIS_URL}/api/v1/nonexistent",
                json={"test": "data"},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                pass
        except (aiohttp.ClientError, asyncio.TimeoutError):
            # Expected behavior - service should handle gracefully
            pass
        
        # Verify other services continue to function
        async with system_clients['http'].get(
            f"{SystemTestConfig.API_GATEWAY_URL}/api/v1/health",
            headers=headers
        ) as response:
            assert response.status == 200
            health_data = await response.json()
            assert health_data['status'] == 'healthy'
        
        return {"recovery_test": "passed"}
    
    async def test_database_connection_recovery(self, system_clients):
        """Test database connection recovery after temporary failures"""
        
        # Test Redis connection recovery
        try:
            # Simulate connection issue by using invalid command
            await system_clients['redis'].execute_command("INVALID_COMMAND")
        except Exception:
            # Expected - invalid command should fail
            pass
        
        # Verify Redis connection is still functional
        await system_clients['redis'].set("test_key", "test_value")
        value = await system_clients['redis'].get("test_key")
        assert value.decode() == "test_value"
        
        return {"database_recovery": "passed"}
    
    async def test_data_validation_and_error_handling(self, system_clients, test_user):
        """Test data validation and error handling for invalid inputs"""
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        # Test invalid data submission
        invalid_post = {
            "platform": "invalid_platform",
            "content": "",  # Empty content
            "user_id": None,  # Invalid user_id
            "timestamp": "invalid_timestamp"
        }
        
        async with system_clients['http'].post(
            f"{SystemTestConfig.DATA_COLLECTION_URL}/api/v1/ingest",
            json=invalid_post,
            headers=headers
        ) as response:
            assert response.status == 422  # Validation error
            error_data = await response.json()
            assert 'detail' in error_data
        
        # Test malformed analysis request
        async with system_clients['http'].post(
            f"{SystemTestConfig.AI_ANALYSIS_URL}/api/v1/analyze/sentiment",
            json={"invalid": "data"},
            headers=headers
        ) as response:
            assert response.status in [400, 422]  # Bad request or validation error
        
        return {"validation_test": "passed"}


@pytest.mark.asyncio
async def test_complete_system_integration():
    """Run complete system integration test suite"""
    
    print("Starting comprehensive system integration tests...")
    
    # Initialize test environment
    async with aiohttp.ClientSession() as session:
        # Wait for all services to be ready
        services = [
            SystemTestConfig.API_GATEWAY_URL,
            SystemTestConfig.DATA_COLLECTION_URL,
            SystemTestConfig.AI_ANALYSIS_URL,
            SystemTestConfig.ALERT_MANAGEMENT_URL
        ]
        
        for service_url in services:
            ready = False
            for _ in range(30):  # Wait up to 30 seconds per service
                try:
                    async with session.get(f"{service_url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            ready = True
                            break
                except:
                    pass
                await asyncio.sleep(1)
            
            assert ready, f"Service {service_url} not ready for testing"
    
    print("All services ready. Running integration tests...")
    
    # Run the test suite
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    asyncio.run(test_complete_system_integration())