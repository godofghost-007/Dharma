#!/usr/bin/env python3
"""
Demo script for Redis caching system with intelligent invalidation.
This script demonstrates the enhanced Redis caching capabilities including:
- Cache-aside pattern implementation
- Intelligent invalidation strategies
- Cache hit/miss monitoring and analytics
- TTL policies and cache management
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

from shared.cache.cache_config import CacheConfig, CacheMode, initialize_cache_system
from shared.cache.cache_policies import CachePolicyConfig, CachePolicy, InvalidationStrategy


async def demo_basic_cache_operations(cache_system: Dict[str, Any]):
    """Demonstrate basic cache operations."""
    print("\n=== Basic Cache Operations Demo ===")
    
    cache_manager = cache_system["cache_manager"]
    cache_monitor = cache_system.get("cache_monitor")
    
    # Set some test data
    test_data = {
        "user:123:profile": {
            "user_id": "123",
            "name": "John Doe",
            "email": "john@example.com",
            "last_login": datetime.utcnow().isoformat()
        },
        "post:456:content": {
            "post_id": "456",
            "content": "This is a test post about AI and social media monitoring",
            "platform": "twitter",
            "sentiment": "neutral",
            "timestamp": datetime.utcnow().isoformat()
        },
        "campaign:789:analysis": {
            "campaign_id": "789",
            "name": "Test Campaign",
            "participants": 150,
            "coordination_score": 0.75,
            "status": "active"
        }
    }
    
    print("Setting cache entries...")
    for key, value in test_data.items():
        success = await cache_manager.set(key, value, ttl=3600, tags=["demo", "test"])
        print(f"  ✓ Set {key}: {success}")
        
        if cache_monitor:
            await cache_monitor.record_set(key, len(json.dumps(value)))
    
    print("\nRetrieving cache entries...")
    for key in test_data.keys():
        start_time = time.time()
        value = await cache_manager.get(key)
        response_time = (time.time() - start_time) * 1000
        
        if value:
            print(f"  ✓ Got {key}: {type(value).__name__} ({response_time:.2f}ms)")
            if cache_monitor:
                await cache_monitor.record_hit(key, response_time)
        else:
            print(f"  ✗ Miss {key}")
            if cache_monitor:
                await cache_monitor.record_miss(key, response_time)
    
    # Test cache miss
    print("\nTesting cache miss...")
    start_time = time.time()
    missing_value = await cache_manager.get("nonexistent:key", default="not_found")
    response_time = (time.time() - start_time) * 1000
    print(f"  Missing key result: {missing_value} ({response_time:.2f}ms)")
    
    if cache_monitor:
        await cache_monitor.record_miss("nonexistent:key", response_time)


async def demo_cache_aside_pattern(cache_system: Dict[str, Any]):
    """Demonstrate cache-aside pattern."""
    print("\n=== Cache-Aside Pattern Demo ===")
    
    cache_manager = cache_system["cache_manager"]
    
    # Simulate database fetch function
    async def fetch_user_from_db(user_id: str):
        print(f"    📊 Fetching user {user_id} from database...")
        await asyncio.sleep(0.1)  # Simulate DB latency
        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "created_at": datetime.utcnow().isoformat()
        }
    
    user_id = "999"
    cache_key = f"user:{user_id}:profile"
    
    print(f"First request for user {user_id} (cache miss expected)...")
    start_time = time.time()
    
    user_data = await cache_manager.cache_aside_get(
        cache_key,
        lambda: fetch_user_from_db(user_id),
        ttl=1800,
        tags=["user_data", "profiles"]
    )
    
    first_request_time = (time.time() - start_time) * 1000
    print(f"  ✓ Got user data: {user_data['name']} ({first_request_time:.2f}ms)")
    
    print(f"\nSecond request for user {user_id} (cache hit expected)...")
    start_time = time.time()
    
    cached_user_data = await cache_manager.cache_aside_get(
        cache_key,
        lambda: fetch_user_from_db(user_id),
        ttl=1800,
        tags=["user_data", "profiles"]
    )
    
    second_request_time = (time.time() - start_time) * 1000
    print(f"  ✓ Got cached user data: {cached_user_data['name']} ({second_request_time:.2f}ms)")
    
    print(f"\nPerformance improvement: {first_request_time / second_request_time:.1f}x faster")


async def demo_cache_invalidation(cache_system: Dict[str, Any]):
    """Demonstrate cache invalidation strategies."""
    print("\n=== Cache Invalidation Demo ===")
    
    cache_manager = cache_system["cache_manager"]
    invalidation_handler = cache_system["invalidation_handler"]
    
    # Set up test data with different tags
    test_keys = {
        "user:100:profile": {"name": "Alice", "role": "admin"},
        "user:101:profile": {"name": "Bob", "role": "user"},
        "sentiment:post:200": {"sentiment": "positive", "confidence": 0.9},
        "sentiment:post:201": {"sentiment": "negative", "confidence": 0.8},
        "campaign:300:data": {"name": "Campaign A", "status": "active"}
    }
    
    print("Setting up test data...")
    for key, value in test_keys.items():
        if "user" in key:
            tags = ["user_data", "profiles"]
        elif "sentiment" in key:
            tags = ["ai_analysis", "sentiment"]
        elif "campaign" in key:
            tags = ["campaign_analysis"]
        else:
            tags = ["general"]
        
        await cache_manager.set(key, value, ttl=3600, tags=tags)
        print(f"  ✓ Set {key} with tags: {tags}")
    
    # Test pattern-based invalidation
    print("\nTesting pattern-based invalidation...")
    deleted_count = await cache_manager.invalidate_by_pattern("user:*")
    print(f"  ✓ Deleted {deleted_count} user entries")
    
    # Verify user entries are gone
    user_data = await cache_manager.get("user:100:profile")
    print(f"  User 100 profile after invalidation: {user_data}")
    
    # Test tag-based invalidation
    print("\nTesting tag-based invalidation...")
    deleted_count = await cache_manager.invalidate_by_tags(["sentiment"])
    print(f"  ✓ Deleted {deleted_count} sentiment entries")
    
    # Verify sentiment entries are gone
    sentiment_data = await cache_manager.get("sentiment:post:200")
    print(f"  Sentiment post 200 after invalidation: {sentiment_data}")
    
    # Test event-based invalidation
    print("\nTesting event-based invalidation...")
    await invalidation_handler.handle_event("campaign_updated", {"campaign_id": "300"})
    print("  ✓ Triggered campaign update event")
    
    # Campaign data should be invalidated
    campaign_data = await cache_manager.get("campaign:300:data")
    print(f"  Campaign 300 data after event: {campaign_data}")


async def demo_cache_policies(cache_system: Dict[str, Any]):
    """Demonstrate cache policies and TTL management."""
    print("\n=== Cache Policies Demo ===")
    
    cache_policies = cache_system["cache_policies"]
    cache_manager = cache_system["cache_manager"]
    
    # Show default policies
    print("Default cache policies:")
    policies = cache_policies.list_policies()
    for name, policy in policies.items():
        print(f"  • {name}: TTL={policy['ttl']}s, Strategy={policy['invalidation_strategy']}")
    
    # Add custom policy
    custom_policy = CachePolicyConfig(
        name="api_responses",
        ttl=300,  # 5 minutes
        policy=CachePolicy.CACHE_ASIDE,
        invalidation_strategy=InvalidationStrategy.TTL,
        tags=["api", "responses"]
    )
    
    cache_policies.add_policy(custom_policy)
    print(f"\n✓ Added custom policy: {custom_policy.name}")
    
    # Use policy for caching
    api_response_data = {
        "endpoint": "/api/v1/dashboard/metrics",
        "data": {"active_alerts": 5, "processed_posts": 1250},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    policy = cache_policies.get_policy("api_responses")
    await cache_manager.set(
        "api:dashboard:metrics",
        api_response_data,
        ttl=policy.ttl,
        tags=policy.tags
    )
    
    print(f"  ✓ Cached API response with {policy.ttl}s TTL")
    
    # Test TTL determination
    ttl = cache_policies.get_ttl_for_key("user_profiles:123")
    print(f"  TTL for user profile key: {ttl}s")
    
    ttl = cache_policies.get_ttl_for_key("unknown_key_type")
    print(f"  TTL for unknown key type: {ttl}s (default)")


async def demo_cache_monitoring(cache_system: Dict[str, Any]):
    """Demonstrate cache monitoring and analytics."""
    print("\n=== Cache Monitoring Demo ===")
    
    cache_monitor = cache_system.get("cache_monitor")
    if not cache_monitor:
        print("  Cache monitoring not enabled")
        return
    
    # Get global metrics
    print("Global cache metrics:")
    metrics = await cache_monitor.get_global_metrics()
    print(f"  • Hit rate: {metrics.hit_rate:.2%}")
    print(f"  • Total requests: {metrics.total_requests}")
    print(f"  • Hits: {metrics.hits}")
    print(f"  • Misses: {metrics.misses}")
    print(f"  • Sets: {metrics.sets}")
    print(f"  • Average response time: {metrics.avg_response_time:.2f}ms")
    print(f"  • Memory usage: {metrics.memory_usage:,} bytes")
    print(f"  • Key count: {metrics.key_count}")
    
    # Get cache health
    print("\nCache health assessment:")
    health = await cache_monitor.get_cache_health()
    print(f"  • Status: {health['status']}")
    print(f"  • Health score: {health['health_score']:.1f}/100")
    
    if health['issues']:
        print("  • Issues:")
        for issue in health['issues']:
            print(f"    - {issue}")
    else:
        print("  • No issues detected")
    
    # Export metrics
    print("\nExporting metrics...")
    export_data = await cache_monitor.export_metrics()
    print(f"  ✓ Exported metrics at {export_data['export_time']}")


async def demo_cluster_operations(cache_system: Dict[str, Any]):
    """Demonstrate Redis cluster operations (if available)."""
    print("\n=== Redis Cluster Operations Demo ===")
    
    cluster_manager = cache_system.get("cluster_manager")
    if not cluster_manager:
        print("  Cluster mode not enabled - skipping cluster demo")
        return
    
    # Get cluster topology
    print("Cluster topology:")
    topology = await cluster_manager.get_cluster_topology()
    for node_id, node in topology.items():
        print(f"  • Node {node_id}: {node.host}:{node.port} ({node.role})")
    
    # Check cluster health
    print("\nCluster health:")
    health = await cluster_manager.check_cluster_health()
    print(f"  • Cluster state: {health.cluster_state}")
    print(f"  • Overall health: {health.overall_health}")
    print(f"  • Slots assigned: {health.cluster_slots_assigned}/16384")
    print(f"  • Known nodes: {health.cluster_known_nodes}")
    
    # Get cluster stats
    print("\nCluster statistics:")
    stats = await cluster_manager.get_cluster_stats()
    print(f"  • Total nodes: {stats.get('total_nodes', 0)}")
    print(f"  • Master nodes: {stats.get('master_nodes', 0)}")
    print(f"  • Slave nodes: {stats.get('slave_nodes', 0)}")
    print(f"  • Slots coverage: {stats.get('slots_coverage', 0):.1f}%")


async def main():
    """Main demo function."""
    print("🚀 Redis Caching System Demo")
    print("=" * 50)
    
    # Create cache configuration
    config = CacheConfig(
        mode=CacheMode.STANDALONE,  # Change to CLUSTER for cluster demo
        redis_url="redis://localhost:6379",
        max_connections=10,
        namespace="demo",
        enable_monitoring=True
    )
    
    print(f"Configuration:")
    print(f"  • Mode: {config.mode.value}")
    print(f"  • Redis URL: {config.redis_url}")
    print(f"  • Namespace: {config.namespace}")
    print(f"  • Monitoring: {config.enable_monitoring}")
    
    try:
        # Initialize cache system
        print("\n🔧 Initializing cache system...")
        cache_system = await initialize_cache_system(config)
        print("  ✓ Cache system initialized successfully")
        
        # Run demos
        await demo_basic_cache_operations(cache_system)
        await demo_cache_aside_pattern(cache_system)
        await demo_cache_invalidation(cache_system)
        await demo_cache_policies(cache_system)
        await demo_cache_monitoring(cache_system)
        await demo_cluster_operations(cache_system)
        
        print("\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if 'cache_system' in locals():
            redis_manager = cache_system.get("redis_manager")
            if redis_manager:
                await redis_manager.disconnect()
                print("\n🔌 Disconnected from Redis")


if __name__ == "__main__":
    asyncio.run(main())