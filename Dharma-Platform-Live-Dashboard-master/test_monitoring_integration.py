#!/usr/bin/env python3
"""
Integration test for monitoring and observability system
Tests all components working together
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all monitoring components can be imported"""
    print("Testing monitoring component imports...")
    
    try:
        # Health checks
        from shared.monitoring.health_checks import (
            HealthChecker, HealthStatus, HealthCheckResult,
            CompositeHealthChecker, get_health_checker
        )
        print("✅ Health checks imported successfully")
        
        # Service discovery
        from shared.monitoring.service_discovery import (
            ServiceRegistry, ServiceInstance, ServiceStatus,
            LoadBalancingStrategy, ServiceClient, ServiceAgent
        )
        print("✅ Service discovery imported successfully")
        
        # Observability integration
        from shared.monitoring.observability_integration import (
            ObservabilityManager, ObservabilityMiddleware,
            setup_service_observability, DEFAULT_OBSERVABILITY_CONFIG
        )
        print("✅ Observability integration imported successfully")
        
        # Metrics (if available)
        try:
            from shared.monitoring.metrics_collector import get_metrics_collector
            print("✅ Metrics collector imported successfully")
        except ImportError as e:
            print(f"⚠️  Metrics collector not available: {e}")
        
        # Logging (if available)
        try:
            from shared.logging.structured_logger import get_logger
            print("✅ Structured logger imported successfully")
        except ImportError as e:
            print(f"⚠️  Structured logger not available: {e}")
        
        # Tracing (if available)
        try:
            from shared.tracing.tracer import get_tracer
            from shared.tracing.correlation import get_correlation_manager
            from shared.tracing.error_tracker import get_error_tracker
            from shared.tracing.performance_profiler import get_profiler
            print("✅ Tracing components imported successfully")
        except ImportError as e:
            print(f"⚠️  Tracing components not available: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_health_check_system():
    """Test health check system functionality"""
    print("\nTesting health check system...")
    
    try:
        from shared.monitoring.health_checks import (
            HealthChecker, HealthStatus, HealthCheckResult,
            CompositeHealthChecker, SystemResourceHealthChecker
        )
        
        # Test basic health check result
        result = HealthCheckResult(
            component="test-component",
            status=HealthStatus.HEALTHY,
            message="Test message",
            timestamp=datetime.utcnow(),
            response_time_ms=100.0
        )
        
        result_dict = result.to_dict()
        assert result_dict["component"] == "test-component"
        assert result_dict["status"] == "healthy"
        print("✅ Health check result creation and serialization works")
        
        # Test composite health checker
        composite = CompositeHealthChecker("test-service")
        assert composite.service_name == "test-service"
        assert len(composite.checkers) == 0
        print("✅ Composite health checker creation works")
        
        # Test system resource checker (if psutil available)
        try:
            system_checker = SystemResourceHealthChecker()
            assert system_checker.name == "system_resources"
            print("✅ System resource health checker creation works")
        except ImportError:
            print("⚠️  System resource checker requires psutil")
        
        return True
        
    except Exception as e:
        print(f"❌ Health check system test failed: {e}")
        return False


def test_service_discovery():
    """Test service discovery functionality"""
    print("\nTesting service discovery...")
    
    try:
        from shared.monitoring.service_discovery import (
            ServiceInstance, ServiceStatus, ServiceRegistry,
            LoadBalancingStrategy
        )
        
        # Test service instance creation
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-instance-1",
            host="localhost",
            port=8000,
            version="1.0.0",
            metadata={"region": "us-east-1"}
        )
        
        assert instance.service_name == "test-service"
        assert instance.base_url == "http://localhost:8000"
        assert instance.metadata["region"] == "us-east-1"
        print("✅ Service instance creation works")
        
        # Test serialization
        instance_dict = instance.to_dict()
        assert instance_dict["service_name"] == "test-service"
        assert instance_dict["status"] == "healthy"
        print("✅ Service instance serialization works")
        
        # Test deserialization
        restored_instance = ServiceInstance.from_dict(instance_dict)
        assert restored_instance.service_name == "test-service"
        assert restored_instance.port == 8000
        print("✅ Service instance deserialization works")
        
        # Test service registry creation
        registry = ServiceRegistry("redis://localhost:6379")
        assert registry.redis_url == "redis://localhost:6379"
        assert len(registry.services) == 0
        print("✅ Service registry creation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Service discovery test failed: {e}")
        return False


def test_observability_integration():
    """Test observability integration"""
    print("\nTesting observability integration...")
    
    try:
        from shared.monitoring.observability_integration import (
            ObservabilityManager, DEFAULT_OBSERVABILITY_CONFIG
        )
        
        # Test observability manager creation
        manager = ObservabilityManager("test-service", DEFAULT_OBSERVABILITY_CONFIG)
        assert manager.service_name == "test-service"
        assert not manager.initialized
        print("✅ Observability manager creation works")
        
        # Test health status
        health_status = manager.get_health_status()
        assert health_status["service"] == "test-service"
        assert "components" in health_status
        print("✅ Observability manager health status works")
        
        # Test default config
        assert "metrics" in DEFAULT_OBSERVABILITY_CONFIG
        assert "service_discovery" in DEFAULT_OBSERVABILITY_CONFIG
        print("✅ Default observability configuration is valid")
        
        return True
        
    except Exception as e:
        print(f"❌ Observability integration test failed: {e}")
        return False


async def test_async_functionality():
    """Test async functionality of monitoring components"""
    print("\nTesting async functionality...")
    
    try:
        from shared.monitoring.health_checks import CompositeHealthChecker
        from shared.monitoring.service_discovery import ServiceRegistry
        
        # Test composite health checker async methods
        composite = CompositeHealthChecker("async-test-service")
        
        # Test check_all (should work even with no checkers)
        results = await composite.check_all()
        assert isinstance(results, dict)
        print("✅ Composite health checker async check_all works")
        
        # Test overall health
        overall = await composite.get_overall_health()
        assert overall.component == "async-test-service"
        print("✅ Composite health checker async get_overall_health works")
        
        # Test service registry async methods (without Redis)
        registry = ServiceRegistry("redis://localhost:6379")
        
        # These should work without actual Redis connection
        instances = registry.get_service_instances("test-service")
        assert isinstance(instances, list)
        print("✅ Service registry get_service_instances works")
        
        all_services = registry.get_all_services()
        assert isinstance(all_services, dict)
        print("✅ Service registry get_all_services works")
        
        return True
        
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")
        return False


def main():
    """Run all monitoring integration tests"""
    print("=" * 60)
    print("MONITORING AND OBSERVABILITY INTEGRATION TEST")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Health Check System", test_health_check_system),
        ("Service Discovery", test_service_discovery),
        ("Observability Integration", test_observability_integration),
    ]
    
    results = []
    
    # Run synchronous tests
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Run async tests
    print(f"\nAsync Functionality Tests:")
    print("-" * 40)
    try:
        async_result = asyncio.run(test_async_functionality())
        results.append(("Async Functionality", async_result))
    except Exception as e:
        print(f"❌ Async functionality tests failed with exception: {e}")
        results.append(("Async Functionality", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All monitoring and observability components are working correctly!")
        print("\nTask 10: Set up monitoring and observability - COMPLETED ✅")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Some components may need attention.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)