#!/usr/bin/env python3
"""
Test Enhanced Data Collection with YouTube API
"""

import asyncio
from api_config import get_api_config
from enhanced_data_collector import EnhancedDataCollector

async def test_collection():
    """Test the enhanced data collection"""
    print("🧪 Testing Enhanced Data Collection")
    print("=" * 40)
    
    # Check API configuration
    config = get_api_config()
    config.print_configuration_status()
    
    # Test enhanced collector
    print("\n🚀 Testing Enhanced Data Collector...")
    collector = EnhancedDataCollector()
    
    # Collect a small sample
    posts = await collector.collect_all_data_enhanced(max_results_per_platform=10)
    
    print(f"\n📊 Collection Results:")
    print(f"Total posts collected: {len(posts)}")
    
    # Show breakdown by platform
    platform_counts = {}
    for post in posts:
        platform_counts[post.platform] = platform_counts.get(post.platform, 0) + 1
    
    for platform, count in platform_counts.items():
        print(f"  {platform}: {count} posts")
    
    # Show sample posts
    if posts:
        print(f"\n📝 Sample Posts:")
        for i, post in enumerate(posts[:3], 1):
            print(f"  {i}. [{post.platform}] {post.content[:100]}...")
            print(f"     Author: {post.author_username}")
            print(f"     Engagement: {post.engagement}")
            print()
    
    return len(posts) > 0

if __name__ == "__main__":
    success = asyncio.run(test_collection())
    
    if success:
        print("✅ Enhanced data collection test successful!")
    else:
        print("❌ Enhanced data collection test failed!")