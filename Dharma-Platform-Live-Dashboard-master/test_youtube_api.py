#!/usr/bin/env python3
"""
Test YouTube API Key
Quick test to verify the YouTube API key is working
"""

import asyncio
import aiohttp
from api_config import get_api_config

async def test_youtube_api():
    """Test YouTube API connection"""
    print("🔍 Testing YouTube API...")
    
    config = get_api_config()
    
    if not config.is_youtube_configured():
        print("❌ YouTube API key not configured")
        return False
    
    print(f"🔑 Using API key: {config.youtube_api_key[:10]}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test with a simple search
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'part': 'snippet',
                'q': 'India news',
                'type': 'video',
                'maxResults': 5,
                'order': 'relevance',
                'regionCode': 'IN',
                'key': config.youtube_api_key
            }
            
            print("📡 Making API request...")
            async with session.get(url, params=params) as response:
                print(f"📊 Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    videos = data.get('items', [])
                    
                    print(f"✅ YouTube API working! Found {len(videos)} videos")
                    
                    if videos:
                        print("\n📺 Sample videos:")
                        for i, video in enumerate(videos[:3], 1):
                            title = video['snippet']['title']
                            channel = video['snippet']['channelTitle']
                            print(f"  {i}. {title[:50]}... - {channel}")
                    
                    return True
                    
                elif response.status == 403:
                    error_data = await response.json()
                    error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                    print(f"❌ API key error: {error_msg}")
                    
                    if 'quota' in error_msg.lower():
                        print("💡 This might be a quota limit issue")
                    elif 'key' in error_msg.lower():
                        print("💡 The API key might be invalid or restricted")
                    
                    return False
                    
                else:
                    print(f"❌ API request failed with status {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text[:200]}...")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing YouTube API: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 YouTube API Test")
    print("=" * 30)
    
    success = await test_youtube_api()
    
    if success:
        print("\n🎉 YouTube API is working correctly!")
        print("✅ You can now collect YouTube data")
    else:
        print("\n⚠️  YouTube API test failed")
        print("💡 Check your API key and quota limits")
        print("🔗 Get API key from: https://console.developers.google.com/")

if __name__ == "__main__":
    asyncio.run(main())