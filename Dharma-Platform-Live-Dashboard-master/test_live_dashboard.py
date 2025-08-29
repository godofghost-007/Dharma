#!/usr/bin/env python3
"""
Test Live Anti-Nationalist Dashboard
"""

import asyncio
from api_config import get_api_config

async def test_youtube_search():
    """Test YouTube search functionality"""
    print("🧪 Testing Live Anti-Nationalist Dashboard")
    print("=" * 50)
    
    # Check API configuration
    config = get_api_config()
    print(f"YouTube API Status: {'✅ Configured' if config.is_youtube_configured() else '❌ Not configured'}")
    
    if not config.is_youtube_configured():
        print("❌ Cannot test without YouTube API key")
        return False
    
    # Test search functionality
    try:
        import aiohttp
        from datetime import datetime, timedelta
        
        async with aiohttp.ClientSession() as session:
            # Test search
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'part': 'snippet',
                'q': 'india news',
                'type': 'video',
                'maxResults': 5,
                'order': 'relevance',
                'publishedAfter': (datetime.now() - timedelta(days=7)).isoformat() + 'Z',
                'key': config.youtube_api_key
            }
            
            print("🔍 Testing YouTube search...")
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    videos = data.get('items', [])
                    
                    print(f"✅ Search successful! Found {len(videos)} videos")
                    
                    if videos:
                        print("\n📺 Sample results:")
                        for i, video in enumerate(videos[:3], 1):
                            title = video['snippet']['title']
                            channel = video['snippet']['channelTitle']
                            print(f"  {i}. {title[:60]}... - {channel}")
                    
                    return True
                else:
                    print(f"❌ Search failed with status: {response.status}")
                    return False
    
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

def main():
    """Main test function"""
    success = asyncio.run(test_youtube_search())
    
    if success:
        print("\n🎉 Live dashboard test successful!")
        print("\n🚀 To launch the dashboard:")
        print("   streamlit run live_anti_nationalist_dashboard.py")
        print("\n🔧 Or launch enhanced dashboard:")
        print("   streamlit run enhanced_real_data_dashboard.py")
    else:
        print("\n❌ Live dashboard test failed!")
        print("💡 Check your YouTube API configuration")

if __name__ == "__main__":
    main()