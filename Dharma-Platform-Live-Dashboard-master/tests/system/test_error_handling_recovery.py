"""
Error handling and recovery scenario tests
Tests system resilience and recovery capabilities
"""

import pytest
import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
import aiohttp
import asyncpg
import motor.motor_asyncio
import redis.asyncio as redis
from unittest.mock import patch, MagicMock


class ErrorScenarioConfig:
    """Configuration for error scenario testing"""
    
    # Service endpoints
    SERVICES = {
        "api_gateway": "http://localhost:8000",
        "data_collection": "http://localhost:8001", 
        "ai_analysis": "http://localhost:8002",
        "alert_management": "http://localhost:8003"
    }
    
    # Recovery timeouts
    SERVICE_RECOVERY_TIMEOUT = 30  # seconds
    DATABASE_RECOVERY_TIMEOUT = 15  # seconds
    CIRCUIT_BREAKER_TIMEOUT = 10   # seconds


@pytest.fixture
async def error_test_clients():
    """Initialize clients for error testing"""
    clients = {
        'http': aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)),
        'mongodb': motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/dharma_test"),
        'postgresql': await asyncpg.connect("postgresql://postgres:password@localhost:5432/dharma_test"),
        'redis': redis.from_url("redis://localhost:6379/0")
    }
    
    yield clients
    
    # Cleanup
    await clients['http'].close()
    clients['mongodb'].close()
    await clients['postgresql'].close()
    await clients['redis'].close()


class TestServiceFailureRecovery:
    """Test service failure and recovery scenarios"""
    
    async def test_ai_service_failure_graceful_degradation(self, error_test_clients):
        """Test system behavior when AI analysis service fails"""
        
        # First verify AI service is working
        test_content = "Test content for analysis"
        
        try:
            async with error_test_clients['http'].post(
                f"{ErrorScenarioConfig.SERVICES['ai_analysis']}/api/v1/analyze/sentiment",
                json={"content": test_content, "language": "en"},
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                initial_status = response.status
        except Exception:
            initial_status = 500
        
        # Simulate AI service failure by overwhelming it
        failure_tasks = []
        for i in range(50):  # Send many requests to cause overload
            task = error_test_clients['http'].post(
                f"{ErrorScenarioConfig.SERVICES['ai_analysis']}/api/v1/analyze/sentiment",
                json={"content": f"Overload test {i}" * 1000, "language": "en"},  # Large content
                headers={"Authorization": "Bearer test_token"}
            )
            failure_tasks.append(task)
        
        # Execute overload requests
        overload_results = await asyncio.gather(*failure_tasks, return_exceptions=True)
        
        # Test that data collection still works (graceful degradation)
        collection_request = {
            "platform": "twitter",
            "content": "Test post during AI service failure",
            "user_id": "test_user_failure",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        async with error_test_clients['http'].post(
            f"{ErrorScenarioConfig.SERVICES['data_collection']}/api/v1/ingest",
            json=collection_request,
            headers={"Authorization": "Bearer test_token"}
        ) as response:
            collection_status = response.status
        
        # Data collection should still work even if AI analysis fails
        assert collection_status in [200, 202], "Data collection failed during AI service overload"
        
        # Test that API gateway health check still works
        async with error_test_clients['http'].get(
            f"{ErrorScenarioConfig.SERVICES['api_gateway']}/health"
        ) as response:
            gateway_status = response.status
        
        assert gateway_status == 200, "API gateway health check failed"
        
        # Wait for AI service recovery
        recovery_start = time.time()
        ai_recovered = False
        
        while (time.time() - recovery_start) < ErrorScenarioConfig.SERVICE_RECOVERY_TIMEOUT:
            try:
                async with error_test_clients['http'].post(
                    f"{ErrorScenarioConfig.SERVICES['ai_analysis']}/api/v1/analyze/sentiment",
                    json={"content": "Recovery test", "language": "en"},
                    headers={"Authorization": "Bearer test_token"}
                ) as response:
                    if response.status == 200:
                        ai_recovered = True
                        break
            except Exception:
                pass
            
            await asyncio.sleep(2)
        
        recovery_time = time.time() - recovery_start
        
        return {
            "initial_ai_status": initial_status,
            "collection_during_failure": collection_status,
            "gateway_health_during_failure": gateway_status,
            "ai_recovered": ai_recovered,
            "recovery_time": recovery_time,
            "overload_requests": len(failure_tasks)
        }
    
    async def test_database_connection_failure_recovery(self, error_test_clients):
        """Test database connection failure and recovery"""
        
        # Test MongoDB connection recovery
        try:
            # Simulate connection issue by closing and reconnecting
            error_test_clients['mongodb'].close()
            
            # Try to perform operation (should fail initially)
            db = error_test_clients['mongodb'].dharma_test
            
            # Reconnect
            error_test_clients['mongodb'] = motor.motor_asyncio.AsyncIOMotorClient(
                "mongodb://localhost:27017/dharma_test"
            )
            db = error_test_clients['mongodb'].dharma_test
            
            # Test that connection works after reconnection
            test_doc = {"test": "recovery", "timestamp": datetime.utcnow()}
            result = await db.test_recovery.insert_one(test_doc)
            
            mongo_recovery = result.inserted_id is not None
            
        except Exception as e:
            mongo_recovery = False
            print(f"MongoDB recovery test failed: {e}")
        
        # Test Redis connection recovery
        try:
            # Close Redis connection
            await error_test_clients['redis'].close()
            
            # Reconnect
            error_test_clients['redis'] = redis.from_url("redis://localhost:6379/0")
            
            # Test Redis operations
            await error_test_clients['redis'].set("recovery_test", "success")
            value = await error_test_clients['redis'].get("recovery_test")
            
            redis_recovery = value.decode() == "success"
            
        except Exception as e:
            redis_recovery = False
            print(f"Redis recovery test failed: {e}")
        
        # Test PostgreSQL connection recovery
        try:
            # Close PostgreSQL connection
            await error_test_clients['postgresql'].close()
            
            # Reconnect
            error_test_clients['postgresql'] = await asyncpg.connect(
                "postgresql://postgres:password@localhost:5432/dharma_test"
            )
            
            # Test PostgreSQL operations
            result = await error_test_clients['postgresql'].fetchval(
                "SELECT 'recovery_success' as test"
            )
            
            pg_recovery = result == "recovery_success"
            
        except Exception as e:
            pg_recovery = False
            print(f"PostgreSQL recovery test failed: {e}")
        
        return {
            "mongodb_recovery": mongo_recovery,
            "redis_recovery": redis_recovery,
            "postgresql_recovery": pg_recovery,
            "all_databases_recovered": mongo_recovery and redis_recovery and pg_recovery
        }
    
    async def test_circuit_breaker_behavior(self, error_test_clients):
        """Test circuit breaker pattern for failing services"""
        
        # Simulate repeated failures to trigger circuit breaker
        failure_count = 0
        success_count = 0
        
        # Send requests that should trigger circuit breaker
        for i in range(20):
            try:
                async with error_test_clients['http'].post(
                    f"{ErrorScenarioConfig.SERVICES['ai_analysis']}/api/v1/nonexistent_endpoint",
                    json={"test": "data"},
                    headers={"Authorization": "Bearer test_token"}
                ) as response:
                    if response.status >= 500:
                        failure_count += 1
                    else:
                        success_count += 1
            except Exception:
                failure_count += 1
            
            await asyncio.sleep(0.1)
        
        # After failures, test if circuit breaker prevents further requests
        circuit_breaker_active = failure_count > success_count
        
        # Wait for circuit breaker to potentially reset
        await asyncio.sleep(ErrorScenarioConfig.CIRCUIT_BREAKER_TIMEOUT)
        
        # Test if service becomes available again
        try:
            async with error_test_clients['http'].get(
                f"{ErrorScenarioConfig.SERVICES['ai_analysis']}/health"
            ) as response:
                service_recovered = response.status == 200
        except Exception:
            service_recovered = False
        
        return {
            "failure_count": failure_count,
            "success_count": success_count,
            "circuit_breaker_triggered": circuit_breaker_active,
            "service_recovered_after_timeout": service_recovered
        }


class TestDataValidationAndErrorHandling:
    """Test data validation and error handling for invalid inputs"""
    
    async def test_invalid_data_submission_handling(self, error_test_clients):
        """Test system handling of invalid data submissions"""
        
        invalid_test_cases = [
            # Missing required fields
            {
                "name": "missing_platform",
                "data": {"content": "test", "user_id": "user1"},
                "expected_status": [400, 422]
            },
            # Invalid data types
            {
                "name": "invalid_timestamp",
                "data": {
                    "platform": "twitter",
                    "content": "test",
                    "user_id": "user1",
                    "timestamp": "invalid_date"
                },
                "expected_status": [400, 422]
            },
            # Oversized content
            {
                "name": "oversized_content",
                "data": {
                    "platform": "twitter",
                    "content": "x" * 10000,  # Very large content
                    "user_id": "user1",
                    "timestamp": datetime.utcnow().isoformat()
                },
                "expected_status": [400, 413, 422]
            },
            # SQL injection attempt
            {
                "name": "sql_injection",
                "data": {
                    "platform": "twitter",
                    "content": "'; DROP TABLE posts; --",
                    "user_id": "user1",
                    "timestamp": datetime.utcnow().isoformat()
                },
                "expected_status": [200, 202, 400]  # Should be sanitized, not cause error
            },
            # XSS attempt
            {
                "name": "xss_attempt",
                "data": {
                    "platform": "twitter",
                    "content": "<script>alert('xss')</script>",
                    "user_id": "user1",
                    "timestamp": datetime.utcnow().isoformat()
                },
                "expected_status": [200, 202, 400]  # Should be sanitized
            }
        ]
        
        validation_results = {}
        
        for test_case in invalid_test_cases:
            try:
                async with error_test_clients['http'].post(
                    f"{ErrorScenarioConfig.SERVICES['data_collection']}/api/v1/ingest",
                    json=test_case["data"],
                    headers={"Authorization": "Bearer test_token"}
                ) as response:
                    actual_status = response.status
                    response_data = await response.text()
                    
                    validation_results[test_case["name"]] = {
                        "status": actual_status,
                        "expected_statuses": test_case["expected_status"],
                        "handled_correctly": actual_status in test_case["expected_status"],
                        "response_length": len(response_data)
                    }
            
            except Exception as e:
                validation_results[test_case["name"]] = {
                    "status": "exception",
                    "error": str(e),
                    "handled_correctly": False
                }
        
        # Verify all invalid inputs were handled correctly
        correctly_handled = sum(1 for result in validation_results.values() 
                              if result.get("handled_correctly", False))
        
        assert correctly_handled >= len(invalid_test_cases) * 0.8, \
            f"Only {correctly_handled}/{len(invalid_test_cases)} invalid inputs handled correctly"
        
        return validation_results
    
    async def test_malformed_api_requests(self, error_test_clients):
        """Test handling of malformed API requests"""
        
        malformed_requests = [
            # Invalid JSON
            {
                "name": "invalid_json",
                "endpoint": "/api/v1/analyze/sentiment",
                "data": "invalid json content",
                "content_type": "application/json"
            },
            # Missing content-type
            {
                "name": "missing_content_type",
                "endpoint": "/api/v1/analyze/sentiment",
                "data": '{"content": "test"}',
                "content_type": None
            },
            # Wrong content-type
            {
                "name": "wrong_content_type",
                "endpoint": "/api/v1/analyze/sentiment",
                "data": '{"content": "test"}',
                "content_type": "text/plain"
            },
            # Oversized request
            {
                "name": "oversized_request",
                "endpoint": "/api/v1/analyze/sentiment",
                "data": '{"content": "' + "x" * 100000 + '"}',
                "content_type": "application/json"
            }
        ]
        
        malformed_results = {}
        
        for request in malformed_requests:
            try:
                headers = {"Authorization": "Bearer test_token"}
                if request["content_type"]:
                    headers["Content-Type"] = request["content_type"]
                
                async with error_test_clients['http'].post(
                    f"{ErrorScenarioConfig.SERVICES['ai_analysis']}{request['endpoint']}",
                    data=request["data"],
                    headers=headers
                ) as response:
                    malformed_results[request["name"]] = {
                        "status": response.status,
                        "handled_gracefully": 400 <= response.status < 500,
                        "response_time": response.headers.get("X-Response-Time", "unknown")
                    }
            
            except Exception as e:
                malformed_results[request["name"]] = {
                    "status": "exception",
                    "error": str(e),
                    "handled_gracefully": "timeout" not in str(e).lower()
                }
        
        # Verify malformed requests are handled gracefully
        gracefully_handled = sum(1 for result in malformed_results.values() 
                               if result.get("handled_gracefully", False))
        
        assert gracefully_handled >= len(malformed_requests) * 0.9, \
            f"Only {gracefully_handled}/{len(malformed_requests)} malformed requests handled gracefully"
        
        return malformed_results


class TestConcurrencyAndRaceConditions:
    """Test system behavior under concurrent access and potential race conditions"""
    
    async def test_concurrent_data_ingestion(self, error_test_clients):
        """Test concurrent data ingestion for race conditions"""
        
        # Generate concurrent posts with potential conflicts
        concurrent_posts = []
        for i in range(50):
            post = {
                "platform": "twitter",
                "content": f"Concurrent test post {i}",
                "user_id": f"concurrent_user_{i % 10}",  # Some users post multiple times
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"concurrent_test": True, "batch": i // 10}
            }
            concurrent_posts.append(post)
        
        # Submit all posts concurrently
        ingestion_tasks = []
        for post in concurrent_posts:
            task = error_test_clients['http'].post(
                f"{ErrorScenarioConfig.SERVICES['data_collection']}/api/v1/ingest",
                json=post,
                headers={"Authorization": "Bearer test_token"}
            )
            ingestion_tasks.append(task)
        
        # Execute all ingestion requests
        start_time = time.time()
        results = await asyncio.gather(*ingestion_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        successful_ingestions = sum(1 for r in results if not isinstance(r, Exception))
        failed_ingestions = len(results) - successful_ingestions
        total_time = end_time - start_time
        
        # Verify data consistency in database
        await asyncio.sleep(2)  # Allow time for processing
        
        db = error_test_clients['mongodb'].dharma_test
        stored_posts = await db.posts.find(
            {"metadata.concurrent_test": True}
        ).to_list(length=None)
        
        # Check for duplicate posts (race condition indicator)
        content_counts = {}
        for post in stored_posts:
            content = post['content']
            content_counts[content] = content_counts.get(content, 0) + 1
        
        duplicates = sum(1 for count in content_counts.values() if count > 1)
        
        return {
            "total_posts": len(concurrent_posts),
            "successful_ingestions": successful_ingestions,
            "failed_ingestions": failed_ingestions,
            "stored_posts": len(stored_posts),
            "duplicate_posts": duplicates,
            "total_time": total_time,
            "race_conditions_detected": duplicates > 0
        }
    
    async def test_concurrent_analysis_requests(self, error_test_clients):
        """Test concurrent analysis requests for resource conflicts"""
        
        # Generate concurrent analysis requests
        analysis_requests = [
            {"content": f"Analysis test content {i}", "language": "en"}
            for i in range(30)
        ]
        
        # Submit analysis requests concurrently
        analysis_tasks = []
        for request in analysis_requests:
            task = error_test_clients['http'].post(
                f"{ErrorScenarioConfig.SERVICES['ai_analysis']}/api/v1/analyze/sentiment",
                json=request,
                headers={"Authorization": "Bearer test_token"}
            )
            analysis_tasks.append(task)
        
        # Execute all analysis requests
        start_time = time.time()
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results for consistency
        successful_analyses = []
        failed_analyses = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_analyses.append({"index": i, "error": str(result)})
            else:
                try:
                    if hasattr(result, 'status') and result.status == 200:
                        response_data = await result.json()
                        successful_analyses.append(response_data)
                    else:
                        failed_analyses.append({"index": i, "status": getattr(result, 'status', 'unknown')})
                except Exception as e:
                    failed_analyses.append({"index": i, "error": str(e)})
        
        # Check for consistency in analysis results
        sentiment_consistency = True
        if len(successful_analyses) > 1:
            # Check if similar content gets similar results
            first_result = successful_analyses[0]
            for result in successful_analyses[1:]:
                if abs(result.get('confidence', 0) - first_result.get('confidence', 0)) > 0.5:
                    sentiment_consistency = False
                    break
        
        total_time = end_time - start_time
        
        return {
            "total_requests": len(analysis_requests),
            "successful_analyses": len(successful_analyses),
            "failed_analyses": len(failed_analyses),
            "total_time": total_time,
            "avg_response_time": total_time / len(analysis_requests),
            "sentiment_consistency": sentiment_consistency
        }


class TestMemoryLeaksAndResourceCleanup:
    """Test for memory leaks and proper resource cleanup"""
    
    async def test_memory_usage_over_time(self, error_test_clients):
        """Test memory usage doesn't grow indefinitely"""
        
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform many operations to test for memory leaks
        operations_count = 100
        
        for i in range(operations_count):
            # Data ingestion
            post_data = {
                "platform": "twitter",
                "content": f"Memory test post {i} with some content to analyze",
                "user_id": f"memory_user_{i}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                async with error_test_clients['http'].post(
                    f"{ErrorScenarioConfig.SERVICES['data_collection']}/api/v1/ingest",
                    json=post_data,
                    headers={"Authorization": "Bearer test_token"}
                ) as response:
                    pass
            except Exception:
                pass
            
            # Analysis request
            try:
                async with error_test_clients['http'].post(
                    f"{ErrorScenarioConfig.SERVICES['ai_analysis']}/api/v1/analyze/sentiment",
                    json={"content": post_data["content"], "language": "en"},
                    headers={"Authorization": "Bearer test_token"}
                ) as response:
                    pass
            except Exception:
                pass
            
            # Periodic memory check
            if i % 20 == 0:
                gc.collect()  # Force garbage collection
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be reasonable
                if memory_growth > 500:  # 500MB growth threshold
                    print(f"Warning: Memory growth of {memory_growth:.1f}MB detected at operation {i}")
        
        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable for the number of operations
        memory_per_operation = total_memory_growth / operations_count
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "total_growth_mb": total_memory_growth,
            "memory_per_operation_kb": memory_per_operation * 1024,
            "operations_count": operations_count,
            "memory_leak_detected": total_memory_growth > 200  # 200MB threshold
        }


@pytest.mark.asyncio
async def test_error_handling_recovery_suite():
    """Run complete error handling and recovery test suite"""
    
    print("Starting error handling and recovery tests...")
    
    # Run error handling tests
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    asyncio.run(test_error_handling_recovery_suite())