"""Configuration and fixtures for performance tests."""

import pytest
import asyncio
import httpx
import os
import time
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """Performance test metrics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    start_time: datetime
    end_time: datetime
    duration: float


@dataclass
class LoadTestConfig:
    """Load test configuration."""
    concurrent_users: int = 10
    requests_per_user: int = 100
    ramp_up_time: int = 30  # seconds
    test_duration: int = 300  # seconds
    base_url: str = "http://localhost:8000"
    timeout: int = 30


@pytest.fixture(scope="session")
def load_test_config():
    """Load test configuration from environment variables."""
    return LoadTestConfig(
        concurrent_users=int(os.getenv("LOAD_TEST_USERS", "10")),
        requests_per_user=int(os.getenv("LOAD_TEST_REQUESTS", "100")),
        ramp_up_time=int(os.getenv("LOAD_TEST_RAMP_UP", "30")),
        test_duration=int(os.getenv("LOAD_TEST_DURATION", "300")),
        base_url=os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8000"),
        timeout=int(os.getenv("LOAD_TEST_TIMEOUT", "30"))
    )


@pytest.fixture(scope="session")
async def performance_clients():
    """Create HTTP clients for performance testing."""
    clients = {
        "api_gateway": httpx.AsyncClient(
            base_url=os.getenv("TEST_API_GATEWAY_URL", "http://localhost:8000"),
            timeout=60,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        ),
        "data_collection": httpx.AsyncClient(
            base_url=os.getenv("TEST_DATA_COLLECTION_URL", "http://localhost:8001"),
            timeout=60,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        ),
        "ai_analysis": httpx.AsyncClient(
            base_url=os.getenv("TEST_AI_ANALYSIS_URL", "http://localhost:8002"),
            timeout=120,  # AI analysis may take longer
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        ),
        "alert_management": httpx.AsyncClient(
            base_url=os.getenv("TEST_ALERT_MANAGEMENT_URL", "http://localhost:8003"),
            timeout=60,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        ),
        "dashboard": httpx.AsyncClient(
            base_url=os.getenv("TEST_DASHBOARD_URL", "http://localhost:8004"),
            timeout=60,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    }
    
    yield clients
    
    # Cleanup
    for client in clients.values():
        await client.aclose()


@pytest.fixture
def sample_test_data():
    """Generate sample test data for performance tests."""
    return {
        "posts": [
            {
                "platform": "twitter",
                "post_id": f"perf_test_post_{i:06d}",
                "user_id": f"perf_test_user_{i % 100:03d}",
                "content": f"This is performance test post number {i}. Testing system load and response times.",
                "timestamp": datetime.utcnow().isoformat(),
                "hashtags": [f"test{i}", "performance", "load"],
                "metrics": {
                    "likes": i * 2,
                    "shares": i,
                    "comments": i // 2,
                    "views": i * 10
                }
            }
            for i in range(1000)
        ],
        "users": [
            {
                "user_id": f"perf_test_user_{i:03d}",
                "platform": "twitter",
                "profile": {
                    "username": f"perfuser{i:03d}",
                    "display_name": f"Performance User {i}",
                    "followers_count": 1000 + i,
                    "following_count": 500 + i,
                    "posts_count": 100 + i,
                    "is_verified": i % 10 == 0
                },
                "behavioral_features": {
                    "avg_posts_per_day": 5.0 + (i % 10),
                    "posting_time_variance": 0.5,
                    "weekend_activity_ratio": 0.3,
                    "duplicate_content_ratio": 0.1 + (i % 5) * 0.1,
                    "avg_content_length": 120.0,
                    "hashtag_usage_frequency": 0.2,
                    "mention_usage_frequency": 0.1,
                    "avg_likes_per_post": 15.0,
                    "avg_shares_per_post": 3.0,
                    "engagement_consistency": 0.7,
                    "follower_following_ratio": 2.0,
                    "mutual_connections_ratio": 0.4,
                    "network_clustering_coefficient": 0.3,
                    "account_age_days": 365 + i,
                    "activity_burst_frequency": 0.1
                }
            }
            for i in range(100)
        ],
        "analysis_requests": [
            {
                "text": f"Performance test content {i}. India is a great country with rich culture and history.",
                "language": "en",
                "metadata": {
                    "test_id": f"perf_test_{i:06d}",
                    "batch_id": f"batch_{i // 100:03d}"
                }
            }
            for i in range(1000)
        ]
    }


class PerformanceTestHelper:
    """Helper class for performance testing utilities."""
    
    @staticmethod
    def calculate_metrics(response_times: List[float], start_time: datetime, end_time: datetime) -> PerformanceMetrics:
        """Calculate performance metrics from response times."""
        if not response_times:
            return PerformanceMetrics(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                requests_per_second=0.0,
                error_rate=1.0,
                start_time=start_time,
                end_time=end_time,
                duration=0.0
            )
        
        response_times.sort()
        total_requests = len(response_times)
        duration = (end_time - start_time).total_seconds()
        
        return PerformanceMetrics(
            total_requests=total_requests,
            successful_requests=total_requests,
            failed_requests=0,
            avg_response_time=sum(response_times) / total_requests,
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p95_response_time=response_times[int(total_requests * 0.95)],
            p99_response_time=response_times[int(total_requests * 0.99)],
            requests_per_second=total_requests / duration if duration > 0 else 0,
            error_rate=0.0,
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )
    
    @staticmethod
    async def run_concurrent_requests(client: httpx.AsyncClient, requests: List[Dict[str, Any]], 
                                    endpoint: str, method: str = "POST") -> List[Dict[str, Any]]:
        """Run concurrent HTTP requests and measure performance."""
        async def make_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
            start_time = time.time()
            
            try:
                if method.upper() == "POST":
                    response = await client.post(endpoint, json=request_data)
                elif method.upper() == "GET":
                    response = await client.get(endpoint, params=request_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                end_time = time.time()
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "response_size": len(response.content) if response.content else 0,
                    "request_data": request_data
                }
            
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "error": str(e),
                    "response_time": end_time - start_time,
                    "request_data": request_data
                }
        
        # Execute all requests concurrently
        tasks = [make_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "response_time": 0.0
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    @staticmethod
    def print_performance_report(metrics: PerformanceMetrics, test_name: str = "Performance Test"):
        """Print a formatted performance report."""
        print(f"\n{'='*60}")
        print(f"{test_name} - Performance Report")
        print(f"{'='*60}")
        print(f"Test Duration: {metrics.duration:.2f} seconds")
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful Requests: {metrics.successful_requests}")
        print(f"Failed Requests: {metrics.failed_requests}")
        print(f"Error Rate: {metrics.error_rate:.2%}")
        print(f"Requests per Second: {metrics.requests_per_second:.2f}")
        print(f"\nResponse Time Statistics:")
        print(f"  Average: {metrics.avg_response_time:.3f}s")
        print(f"  Minimum: {metrics.min_response_time:.3f}s")
        print(f"  Maximum: {metrics.max_response_time:.3f}s")
        print(f"  95th Percentile: {metrics.p95_response_time:.3f}s")
        print(f"  99th Percentile: {metrics.p99_response_time:.3f}s")
        print(f"{'='*60}\n")


@pytest.fixture
def performance_helper():
    """Provide performance testing helper utilities."""
    return PerformanceTestHelper()


# Performance test markers
def pytest_configure(config):
    """Configure pytest markers for performance tests."""
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "load: mark test as load test")
    config.addinivalue_line("markers", "stress: mark test as stress test")
    config.addinivalue_line("markers", "spike: mark test as spike test")
    config.addinivalue_line("markers", "endurance: mark test as endurance test")


# Skip performance tests by default unless explicitly requested
def pytest_collection_modifyitems(config, items):
    """Skip performance tests unless explicitly requested."""
    if not config.getoption("--run-performance"):
        skip_performance = pytest.mark.skip(reason="Performance tests skipped (use --run-performance to run)")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_performance)


def pytest_addoption(parser):
    """Add command line options for performance tests."""
    parser.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="Run performance tests"
    )
    parser.addoption(
        "--performance-users",
        action="store",
        default="10",
        help="Number of concurrent users for load tests"
    )
    parser.addoption(
        "--performance-duration",
        action="store",
        default="60",
        help="Duration of performance tests in seconds"
    )