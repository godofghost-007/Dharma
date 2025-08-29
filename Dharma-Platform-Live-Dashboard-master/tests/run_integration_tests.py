#!/usr/bin/env python3
"""Integration test runner for Project Dharma."""

import sys
import os
import pytest
import asyncio
import time
from pathlib import Path
import subprocess
import signal
from typing import Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

class ServiceManager:
    """Manages test services for integration testing."""
    
    def __init__(self):
        self.services = {}
        self.docker_compose_file = project_root / "docker-compose.yml"
        self.test_env_file = project_root / ".env.test"
    
    def start_test_services(self) -> bool:
        """Start required services for integration testing."""
        print("Starting test services...")
        
        # Check if Docker is available
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker is not available. Please install Docker to run integration tests.")
            return False
        
        # Start services using docker-compose
        try:
            cmd = [
                "docker-compose",
                "-f", str(self.docker_compose_file),
                "--env-file", str(self.test_env_file) if self.test_env_file.exists() else "/dev/null",
                "up", "-d",
                "postgresql", "mongodb", "redis", "elasticsearch"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Failed to start services: {result.stderr}")
                return False
            
            print("✅ Test services started successfully")
            
            # Wait for services to be ready
            print("Waiting for services to be ready...")
            time.sleep(10)
            
            return self._check_service_health()
            
        except Exception as e:
            print(f"❌ Error starting services: {e}")
            return False
    
    def _check_service_health(self) -> bool:
        """Check if all required services are healthy."""
        services_to_check = [
            ("PostgreSQL", "postgresql://test:test@localhost:5432/test_dharma"),
            ("MongoDB", "mongodb://localhost:27017/test_dharma"),
            ("Redis", "redis://localhost:6379/0"),
            ("Elasticsearch", "http://localhost:9200")
        ]
        
        for service_name, connection_string in services_to_check:
            if not self._check_single_service(service_name, connection_string):
                return False
        
        return True
    
    def _check_single_service(self, service_name: str, connection_string: str) -> bool:
        """Check if a single service is healthy."""
        try:
            if "postgresql" in connection_string:
                import psycopg2
                conn = psycopg2.connect(connection_string)
                conn.close()
            elif "mongodb" in connection_string:
                from pymongo import MongoClient
                client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
                client.server_info()
                client.close()
            elif "redis" in connection_string:
                import redis
                r = redis.from_url(connection_string)
                r.ping()
                r.close()
            elif "elasticsearch" in connection_string:
                import requests
                response = requests.get(connection_string, timeout=5)
                response.raise_for_status()
            
            print(f"✅ {service_name} is healthy")
            return True
            
        except Exception as e:
            print(f"❌ {service_name} health check failed: {e}")
            return False
    
    def stop_test_services(self):
        """Stop test services."""
        print("Stopping test services...")
        
        try:
            cmd = [
                "docker-compose",
                "-f", str(self.docker_compose_file),
                "down"
            ]
            
            subprocess.run(cmd, capture_output=True)
            print("✅ Test services stopped")
            
        except Exception as e:
            print(f"❌ Error stopping services: {e}")


def run_integration_tests(test_category: Optional[str] = None, verbose: bool = True) -> int:
    """Run integration tests with proper setup and teardown."""
    
    service_manager = ServiceManager()
    
    # Setup signal handler for cleanup
    def signal_handler(signum, frame):
        print("\n🛑 Received interrupt signal, cleaning up...")
        service_manager.stop_test_services()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start test services
        if not service_manager.start_test_services():
            print("❌ Failed to start test services")
            return 1
        
        # Configure test arguments
        test_args = [
            str(Path(__file__).parent / "integration"),
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "--asyncio-mode=auto",
            "-x",  # Stop on first failure
        ]
        
        # Add category-specific markers
        if test_category:
            if test_category == "api":
                test_args.extend(["-m", "api"])
            elif test_category == "database":
                test_args.extend(["-m", "database"])
            elif test_category == "e2e":
                test_args.extend(["-m", "e2e"])
            elif test_category == "contract":
                test_args.extend(["-m", "contract"])
            else:
                test_args.extend(["-k", test_category])
        
        # Add coverage if available
        try:
            import pytest_cov
            test_args.extend([
                "--cov=shared",
                "--cov=services",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov_integration",
                "--cov-fail-under=70"
            ])
            print("Running integration tests with coverage...")
        except ImportError:
            print("Running integration tests without coverage...")
        
        # Set test environment variables
        os.environ.update({
            "TESTING": "true",
            "TEST_DATABASE_URL": "postgresql://test:test@localhost:5432/test_dharma",
            "TEST_MONGODB_URL": "mongodb://localhost:27017/test_dharma",
            "TEST_REDIS_URL": "redis://localhost:6379/0",
            "TEST_ELASTICSEARCH_URL": "http://localhost:9200",
            "TEST_API_GATEWAY_URL": "http://localhost:8000",
            "TEST_DATA_COLLECTION_URL": "http://localhost:8001",
            "TEST_AI_ANALYSIS_URL": "http://localhost:8002",
            "TEST_ALERT_MANAGEMENT_URL": "http://localhost:8003",
            "TEST_DASHBOARD_URL": "http://localhost:8004"
        })
        
        print("=" * 60)
        print("Running Project Dharma Integration Tests")
        if test_category:
            print(f"Category: {test_category}")
        print("=" * 60)
        
        # Run tests
        exit_code = pytest.main(test_args)
        
        if exit_code == 0:
            print("\n" + "=" * 60)
            print("✅ All integration tests passed!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ Some integration tests failed!")
            print("=" * 60)
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    
    except Exception as e:
        print(f"\n❌ Error running integration tests: {e}")
        return 1
    
    finally:
        # Cleanup
        service_manager.stop_test_services()


def run_performance_tests() -> int:
    """Run performance and load tests."""
    
    print("=" * 60)
    print("Running Performance and Load Tests")
    print("=" * 60)
    
    test_args = [
        str(Path(__file__).parent / "integration"),
        "-v",
        "--tb=short",
        "-m", "performance or load",
        "--asyncio-mode=auto"
    ]
    
    # Set performance test environment
    os.environ.update({
        "TESTING": "true",
        "PERFORMANCE_TESTING": "true",
        "TEST_LOAD_USERS": "50",
        "TEST_DURATION_SECONDS": "60"
    })
    
    return pytest.main(test_args)


def run_end_to_end_tests() -> int:
    """Run end-to-end workflow tests."""
    
    service_manager = ServiceManager()
    
    try:
        # Start all services for E2E tests
        if not service_manager.start_test_services():
            print("❌ Failed to start services for E2E tests")
            return 1
        
        print("=" * 60)
        print("Running End-to-End Workflow Tests")
        print("=" * 60)
        
        test_args = [
            str(Path(__file__).parent / "integration" / "test_end_to_end_workflows.py"),
            "-v",
            "--tb=short",
            "-m", "e2e",
            "--asyncio-mode=auto"
        ]
        
        return pytest.main(test_args)
        
    finally:
        service_manager.stop_test_services()


def main():
    """Main entry point for integration test runner."""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "performance":
            exit_code = run_performance_tests()
        elif command == "e2e":
            exit_code = run_end_to_end_tests()
        elif command in ["api", "database", "contract"]:
            exit_code = run_integration_tests(test_category=command)
        elif command == "help":
            print("Integration Test Runner Commands:")
            print("  python run_integration_tests.py              # Run all integration tests")
            print("  python run_integration_tests.py api          # Run API integration tests")
            print("  python run_integration_tests.py database     # Run database integration tests")
            print("  python run_integration_tests.py contract     # Run contract tests")
            print("  python run_integration_tests.py e2e          # Run end-to-end tests")
            print("  python run_integration_tests.py performance  # Run performance tests")
            print("  python run_integration_tests.py help         # Show this help")
            return 0
        else:
            print(f"Unknown command: {command}")
            print("Use 'help' to see available commands")
            return 1
    else:
        # Run all integration tests
        exit_code = run_integration_tests()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()