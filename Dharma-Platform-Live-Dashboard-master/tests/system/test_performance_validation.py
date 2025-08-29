"""
Performance validation tests for system requirements
Validates performance requirements under realistic load conditions
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
import aiohttp
import psutil
import asyncpg
import motor.motor_asyncio
import redis.asyncio as redis
from concurrent.futures import ThreadPoolExecutor


class PerformanceTestConfig:
    """Performance test configuration and thresholds"""
    
    # Performance thresholds from requirements
    DAILY_POST_PROCESSING = 100000  # Requirement 9.1
    SENTIMENT_ANALYSIS_TIME = 5.0   # Requirement 9.2 - seconds
    DASHBOARD_LOAD_TIME = 2.0       # Requirement 9.3 - seconds
    ANALYTICS_QUERY_TIME = 10.0     # Requirement 9.4 - seconds
    API_THROUGHPUT = 1000           # Requirement 9.5 - requests per minute
    SYSTEM_UPTIME = 99.9            # Requirement 9.5 - percentage
    
    # Load test parameters
    CONCURRENT_USERS = 50
    TEST_DURATION = 300  # 5 minutes
    RAMP_UP_TIME = 60    # 1 minute


@pytest.fixture
async def performance_clients():
    """Initialize clients for performance testing"""
    clients = {
        'http_pool': [aiohttp.ClientSession() for _ in range(10)],
        'mongodb': motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/dharma_test"),
        'postgresql': await asyncpg.create_pool("postgresql://postgres:password@localhost:5432/dharma_test"),
        'redis': redis.ConnectionPool.from_url("redis://localhost:6379/0")
    }
    
    yield clients
    
    # Cleanup
    for session in clients['http_pool']:
        await session.close()
    clients['mongodb'].close()
    await clients['postgresql'].close()
    clients['redis'].disconnect()


class TestDailyProcessingCapacity:
    """Test system capacity for daily processing requirements"""
    
    async def test_100k_posts_per_day_capacity(self, performance_clients):
        """Test system can handle 100,000+ posts per day (Requirement 9.1)"""
        
        # Calculate required throughput: 100k posts / 24 hours = ~1.16 posts/second
        required_throughput = 100000 / (24 * 3600)  # posts per second
        test_duration = 60  # Test for 1 minute
        target_posts = int(required_throughput * test_duration * 1.2)  # 20% buffer
        
        print(f"Testing processing capacity: {target_posts} posts in {test_duration} seconds")
        
        # Generate test posts
        test_posts = [
            {
                "platform": "twitter",
                "content": f"Performance test post {i} with sentiment analysis content",
                "user_id": f"perf_user_{i % 1000}",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"performance_test": True}
            }
            for i in range(target_posts)
        ]
        
        # Submit posts in batches
        batch_size = 100
        start_time = time.time()
        successful_submissions = 0
        
        for i in range(0, len(test_posts), batch_size):
            batch = test_posts[i:i + batch_size]
            
            # Submit batch concurrently
            tasks = []
            for post in batch:
                client = performance_clients['http_pool'][i % len(performance_clients['http_pool'])]
                task = client.post(
                    "http://localhost:8001/api/v1/ingest",
                    json=post,
                    headers={"Authorization": "Bearer test_token"}
                )
                tasks.append(task)
            
            try:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                successful_submissions += sum(1 for r in responses if not isinstance(r, Exception))
            except Exception as e:
                print(f"Batch submission error: {e}")
        
        end_time = time.time()
        actual_duration = end_time - start_time
        actual_throughput = successful_submissions / actual_duration
        
        print(f"Processed {successful_submissions} posts in {actual_duration:.2f} seconds")
        print(f"Actual throughput: {actual_throughput:.2f} posts/second")
        print(f"Required throughput: {required_throughput:.2f} posts/second")
        
        assert actual_throughput >= required_throughput, \
            f"Throughput {actual_throughput:.2f} below requirement {required_throughput:.2f}"
        
        return {
            "posts_processed": successful_submissions,
            "duration": actual_duration,
            "throughput": actual_throughput,
            "requirement_met": actual_throughput >= required_throughput
        }


class TestRealTimePerformance:
    """Test real-time processing performance requirements"""
    
    async def test_sentiment_analysis_latency(self, performance_clients):
        """Test sentiment analysis completes within 5 seconds (Requirement 9.2)"""
        
        test_texts = [
            "This is a positive message about India's progress and development",
            "Neutral content discussing various political topics without bias",
            "Critical content that might be classified as anti-India sentiment",
            "Mixed sentiment content with both positive and negative elements",
            "Complex multilingual content requiring translation and analysis"
        ]
        
        latencies = []
        
        for text in test_texts * 20:  # Test 100 analyses
            start_time = time.time()
            
            client = performance_clients['http_pool'][0]
            async with client.post(
                "http://localhost:8002/api/v1/analyze/sentiment",
                json={"content": text, "language": "auto"},
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    end_time = time.time()
                    latency = end_time - start_time
                    latencies.append(latency)
                    
                    # Verify analysis quality
                    assert 'sentiment' in result
                    assert 'confidence' in result
                    assert 0 <= result['confidence'] <= 1
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        max_latency = max(latencies)
        
        print(f"Sentiment Analysis Performance:")
        print(f"  Average latency: {avg_latency:.3f}s")
        print(f"  95th percentile: {p95_latency:.3f}s")
        print(f"  Maximum latency: {max_latency:.3f}s")
        print(f"  Requirement: {PerformanceTestConfig.SENTIMENT_ANALYSIS_TIME}s")
        
        assert avg_latency <= PerformanceTestConfig.SENTIMENT_ANALYSIS_TIME, \
            f"Average latency {avg_latency:.3f}s exceeds requirement {PerformanceTestConfig.SENTIMENT_ANALYSIS_TIME}s"
        
        assert p95_latency <= PerformanceTestConfig.SENTIMENT_ANALYSIS_TIME * 1.5, \
            f"95th percentile latency {p95_latency:.3f}s exceeds threshold"
        
        return {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "max_latency": max_latency,
            "total_analyses": len(latencies)
        }
    
    async def test_dashboard_load_performance(self, performance_clients):
        """Test dashboard loads within 2 seconds (Requirement 9.3)"""
        
        dashboard_endpoints = [
            "/api/v1/dashboard/overview",
            "/api/v1/dashboard/alerts",
            "/api/v1/dashboard/campaigns",
            "/api/v1/dashboard/analytics",
            "/api/v1/dashboard/metrics"
        ]
        
        load_times = []
        
        for endpoint in dashboard_endpoints * 10:  # Test each endpoint 10 times
            start_time = time.time()
            
            client = performance_clients['http_pool'][0]
            async with client.get(
                f"http://localhost:8000{endpoint}",
                headers={"Authorization": "Bearer test_token"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    end_time = time.time()
                    load_time = end_time - start_time
                    load_times.append(load_time)
                    
                    # Verify response contains expected data
                    assert isinstance(data, dict)
                    assert len(data) > 0
        
        avg_load_time = statistics.mean(load_times)
        p95_load_time = statistics.quantiles(load_times, n=20)[18]
        max_load_time = max(load_times)
        
        print(f"Dashboard Load Performance:")
        print(f"  Average load time: {avg_load_time:.3f}s")
        print(f"  95th percentile: {p95_load_time:.3f}s")
        print(f"  Maximum load time: {max_load_time:.3f}s")
        print(f"  Requirement: {PerformanceTestConfig.DASHBOARD_LOAD_TIME}s")
        
        assert avg_load_time <= PerformanceTestConfig.DASHBOARD_LOAD_TIME, \
            f"Average load time {avg_load_time:.3f}s exceeds requirement"
        
        return {
            "avg_load_time": avg_load_time,
            "p95_load_time": p95_load_time,
            "max_load_time": max_load_time,
            "endpoints_tested": len(dashboard_endpoints)
        }


class TestDatabasePerformance:
    """Test database query performance requirements"""
    
    async def test_analytics_query_performance(self, performance_clients):
        """Test complex analytics queries complete within 10 seconds (Requirement 9.4)"""
        
        # Test MongoDB aggregation queries
        db = performance_clients['mongodb'].dharma_test
        
        complex_queries = [
            # Sentiment trend analysis
            [
                {"$match": {"timestamp": {"$gte": datetime.utcnow() - timedelta(days=7)}}},
                {"$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "sentiment": "$analysis_results.sentiment"
                    },
                    "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$analysis_results.confidence"}
                }},
                {"$sort": {"_id.date": 1}}
            ],
            # Platform activity analysis
            [
                {"$match": {"timestamp": {"$gte": datetime.utcnow() - timedelta(days=1)}}},
                {"$group": {
                    "_id": "$platform",
                    "post_count": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"},
                    "avg_engagement": {"$avg": {"$add": ["$metrics.likes", "$metrics.shares"]}}
                }},
                {"$addFields": {"unique_user_count": {"$size": "$unique_users"}}},
                {"$project": {"unique_users": 0}}
            ],
            # Bot detection analysis
            [
                {"$match": {"analysis_results.bot_probability": {"$gte": 0.7}}},
                {"$group": {
                    "_id": "$user_id",
                    "post_count": {"$sum": 1},
                    "avg_bot_probability": {"$avg": "$analysis_results.bot_probability"},
                    "platforms": {"$addToSet": "$platform"}
                }},
                {"$match": {"post_count": {"$gte": 5}}},
                {"$sort": {"avg_bot_probability": -1}}
            ]
        ]
        
        mongo_times = []
        
        for query in complex_queries:
            start_time = time.time()
            results = await db.posts.aggregate(query).to_list(length=1000)
            end_time = time.time()
            query_time = end_time - start_time
            mongo_times.append(query_time)
            
            print(f"MongoDB query completed in {query_time:.3f}s, returned {len(results)} results")
        
        # Test PostgreSQL analytical queries
        async with performance_clients['postgresql'].acquire() as conn:
            pg_queries = [
                # Alert response time analysis
                """
                SELECT 
                    severity,
                    COUNT(*) as total_alerts,
                    AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at))) as avg_response_time,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (acknowledged_at - created_at))) as p95_response_time
                FROM alerts 
                WHERE created_at >= NOW() - INTERVAL '30 days'
                AND acknowledged_at IS NOT NULL
                GROUP BY severity
                ORDER BY avg_response_time DESC
                """,
                # User activity analysis
                """
                SELECT 
                    u.role,
                    COUNT(DISTINCT al.id) as alerts_handled,
                    AVG(EXTRACT(EPOCH FROM (al.resolved_at - al.acknowledged_at))) as avg_resolution_time,
                    COUNT(DISTINCT DATE(al.created_at)) as active_days
                FROM users u
                LEFT JOIN alerts al ON u.id = al.assigned_to
                WHERE al.created_at >= NOW() - INTERVAL '30 days'
                GROUP BY u.role
                ORDER BY alerts_handled DESC
                """,
                # System performance metrics
                """
                WITH daily_stats AS (
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as daily_alerts,
                        COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_alerts,
                        AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at))) as avg_response_time
                    FROM alerts
                    WHERE created_at >= NOW() - INTERVAL '90 days'
                    GROUP BY DATE(created_at)
                )
                SELECT 
                    date,
                    daily_alerts,
                    critical_alerts,
                    avg_response_time,
                    LAG(daily_alerts) OVER (ORDER BY date) as prev_day_alerts,
                    (daily_alerts - LAG(daily_alerts) OVER (ORDER BY date)) * 100.0 / 
                        NULLIF(LAG(daily_alerts) OVER (ORDER BY date), 0) as growth_rate
                FROM daily_stats
                ORDER BY date DESC
                LIMIT 30
                """
            ]
            
            pg_times = []
            
            for query in pg_queries:
                start_time = time.time()
                results = await conn.fetch(query)
                end_time = time.time()
                query_time = end_time - start_time
                pg_times.append(query_time)
                
                print(f"PostgreSQL query completed in {query_time:.3f}s, returned {len(results)} results")
        
        # Verify performance requirements
        all_query_times = mongo_times + pg_times
        max_query_time = max(all_query_times)
        avg_query_time = statistics.mean(all_query_times)
        
        print(f"Database Query Performance:")
        print(f"  Average query time: {avg_query_time:.3f}s")
        print(f"  Maximum query time: {max_query_time:.3f}s")
        print(f"  Requirement: {PerformanceTestConfig.ANALYTICS_QUERY_TIME}s")
        
        assert max_query_time <= PerformanceTestConfig.ANALYTICS_QUERY_TIME, \
            f"Query time {max_query_time:.3f}s exceeds requirement {PerformanceTestConfig.ANALYTICS_QUERY_TIME}s"
        
        return {
            "mongodb_queries": len(complex_queries),
            "postgresql_queries": len(pg_queries),
            "avg_query_time": avg_query_time,
            "max_query_time": max_query_time,
            "all_query_times": all_query_times
        }


class TestAPIThroughput:
    """Test API throughput requirements"""
    
    async def test_api_requests_per_minute(self, performance_clients):
        """Test system handles 1000+ requests per minute (Requirement 9.5)"""
        
        target_rpm = PerformanceTestConfig.API_THROUGHPUT
        test_duration = 60  # 1 minute
        
        # API endpoints to test
        endpoints = [
            ("GET", "/api/v1/dashboard/overview"),
            ("POST", "/api/v1/analyze/sentiment", {"content": "Test content", "language": "en"}),
            ("GET", "/api/v1/alerts"),
            ("GET", "/api/v1/campaigns"),
            ("POST", "/api/v1/search", {"query": "test", "filters": {}})
        ]
        
        # Distribute requests across endpoints
        requests_per_endpoint = target_rpm // len(endpoints)
        
        async def make_request(client, method, endpoint, data=None):
            """Make a single API request"""
            try:
                if method == "GET":
                    async with client.get(
                        f"http://localhost:8000{endpoint}",
                        headers={"Authorization": "Bearer test_token"}
                    ) as response:
                        return response.status
                else:
                    async with client.post(
                        f"http://localhost:8000{endpoint}",
                        json=data,
                        headers={"Authorization": "Bearer test_token"}
                    ) as response:
                        return response.status
            except Exception as e:
                return f"Error: {e}"
        
        # Generate request tasks
        all_tasks = []
        for method, endpoint, *data in endpoints:
            request_data = data[0] if data else None
            
            for _ in range(requests_per_endpoint):
                client = performance_clients['http_pool'][len(all_tasks) % len(performance_clients['http_pool'])]
                task = make_request(client, method, endpoint, request_data)
                all_tasks.append(task)
        
        # Execute all requests and measure time
        start_time = time.time()
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        end_time = time.time()
        
        actual_duration = end_time - start_time
        successful_requests = sum(1 for r in results if isinstance(r, int) and 200 <= r < 300)
        actual_rpm = (successful_requests / actual_duration) * 60
        
        print(f"API Throughput Performance:")
        print(f"  Total requests: {len(all_tasks)}")
        print(f"  Successful requests: {successful_requests}")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  Actual RPM: {actual_rpm:.2f}")
        print(f"  Target RPM: {target_rpm}")
        
        success_rate = (successful_requests / len(all_tasks)) * 100
        
        assert actual_rpm >= target_rpm * 0.9, \
            f"Throughput {actual_rpm:.2f} RPM below 90% of target {target_rpm} RPM"
        
        assert success_rate >= 95, \
            f"Success rate {success_rate:.1f}% below 95% threshold"
        
        return {
            "total_requests": len(all_tasks),
            "successful_requests": successful_requests,
            "actual_rpm": actual_rpm,
            "success_rate": success_rate,
            "duration": actual_duration
        }


class TestSystemResourceUsage:
    """Test system resource usage under load"""
    
    async def test_resource_utilization_under_load(self, performance_clients):
        """Test system resource usage during peak load"""
        
        # Monitor system resources during load test
        def get_system_metrics():
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            }
        
        # Baseline metrics
        baseline_metrics = get_system_metrics()
        
        # Generate sustained load
        load_tasks = []
        for i in range(100):  # 100 concurrent operations
            client = performance_clients['http_pool'][i % len(performance_clients['http_pool'])]
            
            # Mix of operations
            if i % 3 == 0:
                # Data ingestion
                task = client.post(
                    "http://localhost:8001/api/v1/ingest",
                    json={
                        "platform": "twitter",
                        "content": f"Load test content {i}",
                        "user_id": f"load_user_{i}",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
            elif i % 3 == 1:
                # Analysis request
                task = client.post(
                    "http://localhost:8002/api/v1/analyze/sentiment",
                    json={"content": f"Analysis content {i}", "language": "en"},
                    headers={"Authorization": "Bearer test_token"}
                )
            else:
                # Dashboard request
                task = client.get(
                    "http://localhost:8000/api/v1/dashboard/overview",
                    headers={"Authorization": "Bearer test_token"}
                )
            
            load_tasks.append(task)
        
        # Execute load and monitor resources
        start_time = time.time()
        
        # Start resource monitoring
        resource_samples = []
        
        async def monitor_resources():
            while time.time() - start_time < 30:  # Monitor for 30 seconds
                metrics = get_system_metrics()
                metrics['timestamp'] = time.time() - start_time
                resource_samples.append(metrics)
                await asyncio.sleep(1)
        
        # Run load and monitoring concurrently
        monitor_task = asyncio.create_task(monitor_resources())
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        await monitor_task
        
        # Analyze resource usage
        if resource_samples:
            avg_cpu = statistics.mean([s['cpu_percent'] for s in resource_samples])
            max_cpu = max([s['cpu_percent'] for s in resource_samples])
            avg_memory = statistics.mean([s['memory_percent'] for s in resource_samples])
            max_memory = max([s['memory_percent'] for s in resource_samples])
        else:
            avg_cpu = max_cpu = avg_memory = max_memory = 0
        
        successful_operations = sum(1 for r in load_results if not isinstance(r, Exception))
        
        print(f"Resource Utilization Under Load:")
        print(f"  Successful operations: {successful_operations}/{len(load_tasks)}")
        print(f"  Average CPU: {avg_cpu:.1f}%")
        print(f"  Peak CPU: {max_cpu:.1f}%")
        print(f"  Average Memory: {avg_memory:.1f}%")
        print(f"  Peak Memory: {max_memory:.1f}%")
        
        # Resource usage should be reasonable
        assert max_cpu < 90, f"Peak CPU usage {max_cpu:.1f}% too high"
        assert max_memory < 85, f"Peak memory usage {max_memory:.1f}% too high"
        
        return {
            "successful_operations": successful_operations,
            "total_operations": len(load_tasks),
            "avg_cpu": avg_cpu,
            "max_cpu": max_cpu,
            "avg_memory": avg_memory,
            "max_memory": max_memory,
            "resource_samples": len(resource_samples)
        }


@pytest.mark.asyncio
async def test_performance_validation_suite():
    """Run complete performance validation test suite"""
    
    print("Starting performance validation tests...")
    
    # Run performance tests
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-k", "test_"
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    asyncio.run(test_performance_validation_suite())