#!/usr/bin/env python3
"""
Enhanced Real Data Collector for Dharma Platform
Improved Twitter and YouTube data collection with better error handling
"""

import asyncio
import aiohttp
import tweepy
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
import time
import re
from api_config import get_api_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SocialMediaPost:
    """Enhanced data class for social media posts"""
    id: str
    platform: str
    content: str
    author_id: str
    author_username: str
    timestamp: datetime
    url: str
    engagement: Dict[str, int]
    language: str = "unknown"
    location: Optional[str] = None
    hashtags: List[str] = None
    mentions: List[str] = None
    media_urls: List[str] = None
    verified_author: bool = False
    follower_count: int = 0

class EnhancedDataCollector:
    """Enhanced data collector with improved API handling"""
    
    def __init__(self, db_path: str = "dharma_real_data.db"):
        self.db_path = db_path
        self.setup_database()
        
        # Enhanced search terms for India-related content
        self.india_search_terms = [
            # General India terms
            "India OR भारत OR Bharat",
            "Indian government OR Modi OR BJP",
            "Delhi OR Mumbai OR Bangalore",
            
            # Current affairs
            "India Pakistan OR India China",
            "Kashmir OR Ladakh",
            "Indian economy OR Make in India",
            
            # Cultural terms
            "Bollywood OR Indian cinema",
            "Indian cricket OR Team India",
            "Hindu OR Muslim India",
            
            # Technology and development
            "Digital India OR Startup India",
            "Indian space program OR ISRO",
            "Indian railways OR infrastructure"
        ]
        
        # YouTube channel IDs for Indian news/content
        self.youtube_channels = [
            "UCZiCTpKx-KdTPIcNBQwJV6g",  # ANI News
            "UCR_Q-6KEjlzZbOBlqay8pKw",  # NDTV
            "UCYPvAwZP8pZhSMW8qs7cVCw",  # Times Now
            "UCwqusr8YDwM-3mEYTDeJHzw",  # India Today
            "UCkY_KOeF_vNhJlmgUqHaRbQ"   # Republic World
        ]
        
        # Initialize API clients
        self.initialize_apis()
    
    def setup_database(self):
        """Setup enhanced database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enhanced posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                author_id TEXT,
                author_username TEXT,
                timestamp DATETIME,
                url TEXT,
                engagement_likes INTEGER DEFAULT 0,
                engagement_shares INTEGER DEFAULT 0,
                engagement_comments INTEGER DEFAULT 0,
                engagement_views INTEGER DEFAULT 0,
                language TEXT,
                location TEXT,
                hashtags TEXT,
                mentions TEXT,
                media_urls TEXT,
                verified_author BOOLEAN DEFAULT FALSE,
                follower_count INTEGER DEFAULT 0,
                sentiment TEXT,
                bot_probability REAL,
                risk_score REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Collection statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                search_term TEXT,
                posts_collected INTEGER,
                api_calls_made INTEGER,
                collection_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Enhanced database setup complete")
    
    def initialize_apis(self):
        """Initialize API clients with enhanced error handling"""
        try:
            config = get_api_config()
            
            # Twitter API setup
            if config.is_twitter_configured():
                self.twitter_client = tweepy.Client(
                    bearer_token=config.twitter_bearer_token,
                    wait_on_rate_limit=True  # Automatically handle rate limits
                )
                logger.info("✅ Twitter API client initialized")
            else:
                self.twitter_client = None
                logger.warning("⚠️  Twitter API not configured")
            
            # YouTube API setup
            if config.is_youtube_configured():
                self.youtube_api_key = config.youtube_api_key
                logger.info("✅ YouTube API key configured")
            else:
                self.youtube_api_key = None
                logger.warning("⚠️  YouTube API key not found")
                
        except Exception as e:
            logger.error(f"❌ Error initializing APIs: {e}")
            self.twitter_client = None
            self.youtube_api_key = None
    
    async def collect_youtube_data_enhanced(self, max_results: int = 50) -> List[SocialMediaPost]:
        """Enhanced YouTube data collection"""
        posts = []
        api_calls = 0
        
        if not self.youtube_api_key:
            logger.warning("YouTube API key not available")
            return posts
        
        try:
            async with aiohttp.ClientSession() as session:
                # Search by terms
                for search_term in self.india_search_terms[:2]:
                    try:
                        logger.info(f"🔍 Searching YouTube for: {search_term}")
                        
                        search_url = "https://www.googleapis.com/youtube/v3/search"
                        params = {
                            'part': 'snippet',
                            'q': search_term,
                            'type': 'video',
                            'maxResults': min(max_results // len(self.india_search_terms), 25),
                            'order': 'relevance',
                            'publishedAfter': (datetime.now() - timedelta(days=7)).isoformat() + 'Z',
                            'regionCode': 'IN',  # Focus on India
                            'relevanceLanguage': 'en',
                            'key': self.youtube_api_key
                        }
                        
                        async with session.get(search_url, params=params) as response:
                            api_calls += 1
                            
                            if response.status == 200:
                                data = await response.json()
                                
                                for item in data.get('items', []):
                                    try:
                                        snippet = item['snippet']
                                        video_id = item['id']['videoId']
                                        
                                        # Get detailed video statistics
                                        stats_url = "https://www.googleapis.com/youtube/v3/videos"
                                        stats_params = {
                                            'part': 'statistics,contentDetails',
                                            'id': video_id,
                                            'key': self.youtube_api_key
                                        }
                                        
                                        engagement = {'likes': 0, 'shares': 0, 'comments': 0, 'views': 0}
                                        
                                        async with session.get(stats_url, params=stats_params) as stats_response:
                                            api_calls += 1
                                            
                                            if stats_response.status == 200:
                                                stats_data = await stats_response.json()
                                                if stats_data.get('items'):
                                                    stats = stats_data['items'][0]['statistics']
                                                    engagement = {
                                                        'likes': int(stats.get('likeCount', 0)),
                                                        'shares': 0,  # YouTube doesn't provide share count
                                                        'comments': int(stats.get('commentCount', 0)),
                                                        'views': int(stats.get('viewCount', 0))
                                                    }
                                        
                                        # Extract hashtags from description
                                        description = snippet.get('description', '')
                                        hashtags = re.findall(r'#\w+', description)
                                        
                                        # Create enhanced post object
                                        post = SocialMediaPost(
                                            id=f"youtube_{video_id}",
                                            platform="YouTube",
                                            content=f"{snippet['title']} - {description[:300]}...",
                                            author_id=snippet['channelId'],
                                            author_username=snippet['channelTitle'],
                                            timestamp=datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00')),
                                            url=f"https://www.youtube.com/watch?v={video_id}",
                                            engagement=engagement,
                                            language='unknown',
                                            hashtags=hashtags,
                                            verified_author=False,
                                            follower_count=0
                                        )
                                        
                                        posts.append(post)
                                        
                                    except Exception as e:
                                        logger.error(f"Error processing YouTube video: {e}")
                                        continue
                                
                                # Log collection stats
                                self.log_collection_stats(
                                    platform="YouTube",
                                    search_term=search_term,
                                    posts_collected=len([p for p in posts if search_term.split()[0].lower() in p.content.lower()]),
                                    api_calls_made=2,  # Search + stats
                                    success=True
                                )
                                
                            else:
                                error_msg = f"YouTube API error: {response.status}"
                                logger.error(error_msg)
                                self.log_collection_stats(
                                    platform="YouTube",
                                    search_term=search_term,
                                    posts_collected=0,
                                    api_calls_made=1,
                                    success=False,
                                    error_message=error_msg
                                )
                        
                        # Rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error searching YouTube for '{search_term}': {e}")
                        continue
            
            logger.info(f"✅ Collected {len(posts)} YouTube posts with {api_calls} API calls")
            
        except Exception as e:
            logger.error(f"❌ Error in YouTube data collection: {e}")
        
        return posts
    
    def log_collection_stats(self, platform: str, search_term: str, posts_collected: int, 
                           api_calls_made: int, success: bool, error_message: str = None):
        """Log collection statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO collection_stats (
                    platform, search_term, posts_collected, api_calls_made, 
                    success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (platform, search_term, posts_collected, api_calls_made, success, error_message))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging collection stats: {e}")
    
    def save_posts_to_db_enhanced(self, posts: List[SocialMediaPost]):
        """Save posts with enhanced metadata"""
        if not posts:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        for post in posts:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO posts (
                        id, platform, content, author_id, author_username,
                        timestamp, url, engagement_likes, engagement_shares,
                        engagement_comments, engagement_views, language, location, 
                        hashtags, mentions, media_urls, verified_author, follower_count,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post.id, post.platform, post.content, post.author_id,
                    post.author_username, post.timestamp, post.url,
                    post.engagement.get('likes', 0), post.engagement.get('shares', 0),
                    post.engagement.get('comments', 0), post.engagement.get('views', 0),
                    post.language, post.location,
                    json.dumps(post.hashtags) if post.hashtags else None,
                    json.dumps(post.mentions) if post.mentions else None,
                    json.dumps(post.media_urls) if post.media_urls else None,
                    post.verified_author, post.follower_count,
                    datetime.now()
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving post {post.id}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Saved {saved_count} posts to database")
    
    async def collect_all_data_enhanced(self, max_results_per_platform: int = 100):
        """Enhanced data collection from all platforms"""
        logger.info("🚀 Starting enhanced real data collection...")
        
        all_posts = []
        
        # Collect from YouTube
        logger.info("📺 Collecting YouTube data...")
        youtube_posts = await self.collect_youtube_data_enhanced(max_results_per_platform)
        all_posts.extend(youtube_posts)
        
        # Collect from Reddit (existing implementation)
        logger.info("🔴 Collecting Reddit data...")
        try:
            from real_data_collector import RealDataCollector
            reddit_collector = RealDataCollector()
            reddit_posts_raw = await reddit_collector.collect_reddit_data(max_results_per_platform)
            
            # Convert to enhanced format
            reddit_posts = []
            for post in reddit_posts_raw:
                enhanced_post = SocialMediaPost(
                    id=post.id,
                    platform=post.platform,
                    content=post.content,
                    author_id=post.author_id,
                    author_username=post.author_username,
                    timestamp=post.timestamp,
                    url=post.url,
                    engagement=post.engagement,
                    language=post.language,
                    location=post.location,
                    hashtags=post.hashtags,
                    mentions=post.mentions,
                    media_urls=post.media_urls,
                    verified_author=False,  # Reddit doesn't have verified users
                    follower_count=0  # Reddit doesn't show follower counts
                )
                reddit_posts.append(enhanced_post)
            
            all_posts.extend(reddit_posts)
        except Exception as e:
            logger.error(f"Error collecting Reddit data: {e}")
            reddit_posts = []
        
        # Save to database
        self.save_posts_to_db_enhanced(all_posts)
        
        logger.info(f"🎉 Total collected: {len(all_posts)} posts")
        logger.info(f"   YouTube: {len(youtube_posts)} posts")
        logger.info(f"   Reddit: {len(reddit_posts)} posts")
        
        return all_posts

# Main execution function
async def collect_enhanced_real_data():
    """Main function to collect enhanced real data"""
    collector = EnhancedDataCollector()
    
    # Check API configuration
    config = get_api_config()
    config.print_configuration_status()
    
    # Collect data
    posts = await collector.collect_all_data_enhanced()
    
    return posts

if __name__ == "__main__":
    asyncio.run(collect_enhanced_real_data())