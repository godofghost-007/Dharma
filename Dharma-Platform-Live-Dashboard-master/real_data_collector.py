#!/usr/bin/env python3
"""
Real Data Collector for Dharma Platform
Collects real social media data from various platforms
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
import hashlib
import re
from api_config import get_api_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SocialMediaPost:
    """Data class for social media posts"""
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

class RealDataCollector:
    """Collects real data from social media platforms"""
    
    def __init__(self):
        self.db_path = "dharma_real_data.db"
        self.setup_database()
        
        # API clients
        self.twitter_client = None
        self.youtube_client = None
        
        # Search terms for India-related content
        self.search_terms = [
            "India", "भारत", "Bharat", "Indian", "Modi", "Delhi", "Mumbai",
            "Kashmir", "Pakistan", "China", "BJP", "Congress", "Hindu", "Muslim",
            "Bollywood", "cricket India", "Indian economy", "Make in India",
            "Digital India", "Atmanirbhar", "JAI HIND", "anti-India", "pro-India"
        ]
        
        # Initialize API clients
        self.initialize_apis()
    
    def setup_database(self):
        """Setup SQLite database for storing real data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create posts table
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
                language TEXT,
                location TEXT,
                hashtags TEXT,
                mentions TEXT,
                media_urls TEXT,
                sentiment TEXT,
                bot_probability REAL,
                risk_score REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                post_id TEXT PRIMARY KEY,
                sentiment TEXT,
                confidence REAL,
                bot_probability REAL,
                risk_score REAL,
                propaganda_techniques TEXT,
                language_detected TEXT,
                analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database setup complete")
    
    def initialize_apis(self):
        """Initialize API clients with credentials"""
        try:
            config = get_api_config()
            
            # Twitter API v2 setup
            if config.is_twitter_configured():
                self.twitter_client = tweepy.Client(bearer_token=config.twitter_bearer_token)
                logger.info("✅ Twitter API client initialized")
            else:
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
            self.youtube_api_key = None
    
    async def collect_twitter_data(self, max_results: int = 100) -> List[SocialMediaPost]:
        """Collect real data from Twitter"""
        posts = []
        
        if not self.twitter_client:
            logger.warning("Twitter client not available")
            return posts
        
        try:
            for search_term in self.search_terms[:3]:  # Limit to avoid rate limits
                try:
                    # Search for recent tweets
                    tweets = tweepy.Paginator(
                        self.twitter_client.search_recent_tweets,
                        query=f"{search_term} -is:retweet lang:en OR lang:hi",
                        tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang', 'geo'],
                        user_fields=['username'],
                        expansions=['author_id'],
                        max_results=min(max_results // len(self.search_terms), 100)
                    ).flatten(limit=max_results // len(self.search_terms))
                    
                    for tweet in tweets:
                        try:
                            # Get author info
                            author_username = "unknown"
                            if hasattr(tweet, 'includes') and 'users' in tweet.includes:
                                for user in tweet.includes['users']:
                                    if user.id == tweet.author_id:
                                        author_username = user.username
                                        break
                            
                            # Extract hashtags and mentions
                            hashtags = re.findall(r'#\w+', tweet.text)
                            mentions = re.findall(r'@\w+', tweet.text)
                            
                            # Create post object
                            post = SocialMediaPost(
                                id=f"twitter_{tweet.id}",
                                platform="Twitter",
                                content=tweet.text,
                                author_id=str(tweet.author_id),
                                author_username=author_username,
                                timestamp=tweet.created_at,
                                url=f"https://twitter.com/{author_username}/status/{tweet.id}",
                                engagement={
                                    'likes': tweet.public_metrics.get('like_count', 0),
                                    'shares': tweet.public_metrics.get('retweet_count', 0),
                                    'comments': tweet.public_metrics.get('reply_count', 0)
                                },
                                language=tweet.lang or 'unknown',
                                hashtags=hashtags,
                                mentions=mentions
                            )
                            
                            posts.append(post)
                            
                        except Exception as e:
                            logger.error(f"Error processing tweet {tweet.id}: {e}")
                            continue
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error searching for '{search_term}': {e}")
                    continue
            
            logger.info(f"Collected {len(posts)} Twitter posts")
            
        except Exception as e:
            logger.error(f"Error collecting Twitter data: {e}")
        
        return posts
    
    async def collect_youtube_data(self, max_results: int = 50) -> List[SocialMediaPost]:
        """Collect real data from YouTube"""
        posts = []
        
        youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        if not youtube_api_key:
            logger.warning("YouTube API key not available")
            return posts
        
        try:
            async with aiohttp.ClientSession() as session:
                for search_term in self.search_terms[:2]:  # Limit searches
                    try:
                        # Search for videos
                        search_url = "https://www.googleapis.com/youtube/v3/search"
                        params = {
                            'part': 'snippet',
                            'q': search_term,
                            'type': 'video',
                            'maxResults': min(max_results // len(self.search_terms), 25),
                            'order': 'relevance',
                            'publishedAfter': (datetime.now() - timedelta(days=7)).isoformat() + 'Z',
                            'key': youtube_api_key
                        }
                        
                        async with session.get(search_url, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                for item in data.get('items', []):
                                    try:
                                        snippet = item['snippet']
                                        video_id = item['id']['videoId']
                                        
                                        # Get video statistics
                                        stats_url = "https://www.googleapis.com/youtube/v3/videos"
                                        stats_params = {
                                            'part': 'statistics',
                                            'id': video_id,
                                            'key': youtube_api_key
                                        }
                                        
                                        engagement = {'likes': 0, 'shares': 0, 'comments': 0}
                                        async with session.get(stats_url, params=stats_params) as stats_response:
                                            if stats_response.status == 200:
                                                stats_data = await stats_response.json()
                                                if stats_data.get('items'):
                                                    stats = stats_data['items'][0]['statistics']
                                                    engagement = {
                                                        'likes': int(stats.get('likeCount', 0)),
                                                        'shares': 0,  # YouTube doesn't provide share count
                                                        'comments': int(stats.get('commentCount', 0))
                                                    }
                                        
                                        # Create post object
                                        post = SocialMediaPost(
                                            id=f"youtube_{video_id}",
                                            platform="YouTube",
                                            content=f"{snippet['title']} - {snippet['description'][:200]}...",
                                            author_id=snippet['channelId'],
                                            author_username=snippet['channelTitle'],
                                            timestamp=datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00')),
                                            url=f"https://www.youtube.com/watch?v={video_id}",
                                            engagement=engagement,
                                            language='unknown'
                                        )
                                        
                                        posts.append(post)
                                        
                                    except Exception as e:
                                        logger.error(f"Error processing YouTube video: {e}")
                                        continue
                            
                            # Rate limiting
                            await asyncio.sleep(1)
                            
                    except Exception as e:
                        logger.error(f"Error searching YouTube for '{search_term}': {e}")
                        continue
            
            logger.info(f"Collected {len(posts)} YouTube posts")
            
        except Exception as e:
            logger.error(f"Error collecting YouTube data: {e}")
        
        return posts
    
    async def collect_reddit_data(self, max_results: int = 50) -> List[SocialMediaPost]:
        """Collect real data from Reddit using public API"""
        posts = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Search India-related subreddits
                subreddits = ['india', 'IndiaSpeaks', 'indianews', 'bollywood', 'cricket']
                
                for subreddit in subreddits:
                    try:
                        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                        params = {'limit': max_results // len(subreddits)}
                        
                        headers = {'User-Agent': 'DharmaPlatform/1.0'}
                        
                        async with session.get(url, params=params, headers=headers) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                for item in data['data']['children']:
                                    try:
                                        post_data = item['data']
                                        
                                        # Skip removed or deleted posts
                                        if post_data.get('removed_by_category') or post_data.get('selftext') == '[deleted]':
                                            continue
                                        
                                        # Create post object
                                        post = SocialMediaPost(
                                            id=f"reddit_{post_data['id']}",
                                            platform="Reddit",
                                            content=f"{post_data['title']} - {post_data.get('selftext', '')[:200]}",
                                            author_id=post_data['author'],
                                            author_username=post_data['author'],
                                            timestamp=datetime.fromtimestamp(post_data['created_utc']),
                                            url=f"https://reddit.com{post_data['permalink']}",
                                            engagement={
                                                'likes': post_data.get('ups', 0),
                                                'shares': 0,
                                                'comments': post_data.get('num_comments', 0)
                                            },
                                            language='en'
                                        )
                                        
                                        posts.append(post)
                                        
                                    except Exception as e:
                                        logger.error(f"Error processing Reddit post: {e}")
                                        continue
                        
                        # Rate limiting
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error collecting from r/{subreddit}: {e}")
                        continue
            
            logger.info(f"Collected {len(posts)} Reddit posts")
            
        except Exception as e:
            logger.error(f"Error collecting Reddit data: {e}")
        
        return posts
    
    def save_posts_to_db(self, posts: List[SocialMediaPost]):
        """Save posts to database"""
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
                        engagement_comments, language, location, hashtags, mentions, media_urls
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post.id, post.platform, post.content, post.author_id,
                    post.author_username, post.timestamp, post.url,
                    post.engagement.get('likes', 0), post.engagement.get('shares', 0),
                    post.engagement.get('comments', 0), post.language, post.location,
                    json.dumps(post.hashtags) if post.hashtags else None,
                    json.dumps(post.mentions) if post.mentions else None,
                    json.dumps(post.media_urls) if post.media_urls else None
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving post {post.id}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {saved_count} posts to database")
    
    def get_posts_from_db(self, limit: int = 100, platform: str = None) -> List[Dict[str, Any]]:
        """Get posts from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT p.*, a.sentiment, a.bot_probability, a.risk_score
            FROM posts p
            LEFT JOIN analysis_results a ON p.id = a.post_id
            WHERE p.timestamp > datetime('now', '-7 days')
        '''
        params = []
        
        if platform:
            query += ' AND p.platform = ?'
            params.append(platform)
        
        query += ' ORDER BY p.timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to dictionaries
        columns = [description[0] for description in cursor.description]
        posts = []
        
        for row in rows:
            post_dict = dict(zip(columns, row))
            
            # Parse JSON fields
            if post_dict['hashtags']:
                post_dict['hashtags'] = json.loads(post_dict['hashtags'])
            if post_dict['mentions']:
                post_dict['mentions'] = json.loads(post_dict['mentions'])
            if post_dict['media_urls']:
                post_dict['media_urls'] = json.loads(post_dict['media_urls'])
            
            # Add engagement dict
            post_dict['engagement'] = {
                'likes': post_dict['engagement_likes'] or 0,
                'shares': post_dict['engagement_shares'] or 0,
                'comments': post_dict['engagement_comments'] or 0
            }
            
            posts.append(post_dict)
        
        conn.close()
        return posts
    
    async def collect_all_data(self, max_results_per_platform: int = 100):
        """Collect data from all available platforms"""
        logger.info("Starting real data collection...")
        
        all_posts = []
        
        # Collect from Twitter
        twitter_posts = await self.collect_twitter_data(max_results_per_platform)
        all_posts.extend(twitter_posts)
        
        # Collect from YouTube
        youtube_posts = await self.collect_youtube_data(max_results_per_platform)
        all_posts.extend(youtube_posts)
        
        # Collect from Reddit
        reddit_posts = await self.collect_reddit_data(max_results_per_platform)
        all_posts.extend(reddit_posts)
        
        # Save to database
        self.save_posts_to_db(all_posts)
        
        logger.info(f"Total collected: {len(all_posts)} posts")
        return all_posts

# Async function to run data collection
async def collect_real_data():
    """Main function to collect real data"""
    collector = RealDataCollector()
    await collector.collect_all_data()
    return collector.get_posts_from_db()

if __name__ == "__main__":
    # Run data collection
    asyncio.run(collect_real_data())