"""
Twitter/X data collector with API v2 support
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Optional, AsyncGenerator, Dict, Any
import tweepy
import structlog

from app.core.config import TwitterCredentials
from app.models.requests import TwitterCollectionRequest
from app.core.kafka_producer import KafkaDataProducer
from shared.models.post import Platform

logger = structlog.get_logger()


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, requests_per_window: int, window_seconds: int):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests = []
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Remove old requests outside the window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.window_seconds]
        
        if len(self.requests) >= self.requests_per_window:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = self.window_seconds - (now - oldest_request)
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        self.requests.append(now)


class TwitterStreamListener(tweepy.StreamingClient):
    """Custom Twitter stream listener"""
    
    def __init__(self, bearer_token: str, kafka_producer: KafkaDataProducer, 
                 collection_id: str, data_pipeline=None):
        super().__init__(bearer_token)
        self.kafka_producer = kafka_producer
        self.collection_id = collection_id
        self.data_pipeline = data_pipeline
        self.tweet_count = 0
        self.max_tweets = None
        self.start_time = datetime.utcnow()
        self.duration_limit = None
    
    def set_limits(self, max_tweets: Optional[int], duration_minutes: Optional[int]):
        """Set collection limits"""
        self.max_tweets = max_tweets
        if duration_minutes:
            self.duration_limit = self.start_time + timedelta(minutes=duration_minutes)
    
    def on_tweet(self, tweet):
        """Handle incoming tweets"""
        try:
            # Check limits
            if self.max_tweets and self.tweet_count >= self.max_tweets:
                logger.info("Max tweets reached, stopping stream")
                self.disconnect()
                return
            
            if self.duration_limit and datetime.utcnow() > self.duration_limit:
                logger.info("Duration limit reached, stopping stream")
                self.disconnect()
                return
            
            # Process tweet data
            tweet_data = self._process_tweet(tweet)
            
            # Send to data pipeline if available, otherwise use Kafka directly
            if hasattr(self, 'data_pipeline') and self.data_pipeline:
                asyncio.create_task(
                    self.data_pipeline.process_streaming_data(
                        Platform.TWITTER, tweet_data, self.collection_id
                    )
                )
            else:
                # Fallback to direct Kafka
                asyncio.create_task(
                    self.kafka_producer.send_data("twitter", tweet_data, self.collection_id)
                )
            
            self.tweet_count += 1
            
            if self.tweet_count % 100 == 0:
                logger.info(f"Processed {self.tweet_count} tweets")
                
        except Exception as e:
            logger.error("Error processing tweet", error=str(e))
    
    def _process_tweet(self, tweet) -> Dict[str, Any]:
        """Process tweet into standardized format"""
        return {
            "id": tweet.id,
            "text": tweet.text,
            "author_id": tweet.author_id,
            "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
            "public_metrics": getattr(tweet, 'public_metrics', {}),
            "context_annotations": getattr(tweet, 'context_annotations', []),
            "entities": getattr(tweet, 'entities', {}),
            "geo": getattr(tweet, 'geo', {}),
            "lang": getattr(tweet, 'lang', None),
            "possibly_sensitive": getattr(tweet, 'possibly_sensitive', False),
            "referenced_tweets": getattr(tweet, 'referenced_tweets', []),
            "reply_settings": getattr(tweet, 'reply_settings', None),
            "source": getattr(tweet, 'source', None),
            "collected_at": datetime.utcnow().isoformat()
        }
    
    def on_error(self, status_code):
        """Handle stream errors"""
        logger.error(f"Twitter stream error: {status_code}")
        if status_code == 420:
            # Rate limit exceeded
            logger.warning("Rate limit exceeded, backing off")
            return False
        return True


class TwitterCollector:
    """Twitter/X data collector with API v2 support"""
    
    def __init__(self, credentials: TwitterCredentials):
        self.credentials = credentials
        
        # Validate credentials before creating client
        if not credentials.validate_credentials():
            raise ValueError("Invalid Twitter credentials: one or more required fields are missing or empty")
        
        try:
            # Create tweepy client with proper authentication
            auth_config = credentials.get_auth_config()
            self.client = tweepy.Client(
                bearer_token=auth_config["bearer_token"],
                consumer_key=auth_config["consumer_key"],
                consumer_secret=auth_config["consumer_secret"],
                access_token=auth_config["access_token"],
                access_token_secret=auth_config["access_token_secret"],
                wait_on_rate_limit=True
            )
            
            # Validate authentication by making a test API call
            self._validate_authentication()
            
        except Exception as e:
            logger.error("Failed to initialize Twitter client", error=str(e))
            raise ValueError(f"Twitter authentication failed: {str(e)}")
        
        self.rate_limiter = RateLimiter(requests_per_window=300, window_seconds=900)
        self.active_streams = {}
    
    def _validate_authentication(self):
        """Validate Twitter API authentication by making a test call"""
        try:
            # Test authentication with a simple API call
            me = self.client.get_me()
            if me.data:
                logger.info(f"Twitter authentication successful for user: {me.data.username}")
            else:
                raise Exception("Authentication test failed: no user data returned")
        except tweepy.Unauthorized as e:
            logger.error("Twitter authentication failed: Invalid credentials")
            raise ValueError("Twitter authentication failed: Invalid credentials")
        except tweepy.Forbidden as e:
            logger.error("Twitter authentication failed: Access forbidden")
            raise ValueError("Twitter authentication failed: Access forbidden")
        except tweepy.TooManyRequests as e:
            logger.warning("Twitter authentication test hit rate limit, but credentials appear valid")
            # Rate limit on auth test is acceptable - credentials are likely valid
        except Exception as e:
            logger.error("Twitter authentication test failed", error=str(e))
            raise ValueError(f"Twitter authentication test failed: {str(e)}")
    
    async def start_collection(self, request: TwitterCollectionRequest, 
                             kafka_producer: KafkaDataProducer, data_pipeline=None):
        """Start Twitter data collection based on request parameters"""
        try:
            logger.info(f"Starting Twitter collection for request: {request.collection_id}")
            
            if request.stream_mode:
                await self._start_streaming(request, kafka_producer, data_pipeline)
            else:
                await self._start_search_collection(request, kafka_producer, data_pipeline)
                
            # Collect user timelines if specified
            if request.user_timelines:
                await self._collect_user_timelines(request, kafka_producer, data_pipeline)
                
        except tweepy.Unauthorized as e:
            logger.error("Twitter collection failed: Authentication error", error=str(e))
            raise ValueError("Twitter authentication failed. Please check your API credentials.")
        except tweepy.Forbidden as e:
            logger.error("Twitter collection failed: Access forbidden", error=str(e))
            raise ValueError("Twitter access forbidden. Please check your API permissions.")
        except tweepy.TooManyRequests as e:
            logger.error("Twitter collection failed: Rate limit exceeded", error=str(e))
            raise ValueError("Twitter rate limit exceeded. Please try again later.")
        except Exception as e:
            logger.error("Failed to start Twitter collection", error=str(e))
            raise
    
    async def _start_streaming(self, request: TwitterCollectionRequest,
                             kafka_producer: KafkaDataProducer, data_pipeline=None):
        """Start real-time tweet streaming"""
        try:
            # Create stream listener
            stream = TwitterStreamListener(
                self.credentials.bearer_token,
                kafka_producer,
                request.collection_id,
                data_pipeline
            )
            
            stream.set_limits(request.max_results, request.duration_minutes)
            
            # Add rules for keywords
            rules = []
            for keyword in request.keywords:
                rule = tweepy.StreamRule(value=keyword)
                rules.append(rule)
            
            # Delete existing rules and add new ones
            existing_rules = stream.get_rules()
            if existing_rules.data:
                rule_ids = [rule.id for rule in existing_rules.data]
                stream.delete_rules(rule_ids)
            
            stream.add_rules(rules)
            
            # Start streaming
            logger.info(f"Starting Twitter stream for keywords: {request.keywords}")
            stream.filter(
                tweet_fields=['created_at', 'author_id', 'public_metrics', 
                             'context_annotations', 'entities', 'geo', 'lang',
                             'possibly_sensitive', 'referenced_tweets', 
                             'reply_settings', 'source'],
                threaded=True
            )
            
            self.active_streams[request.collection_id] = stream
            
        except Exception as e:
            logger.error("Failed to start Twitter streaming", error=str(e))
            raise 
   
    async def _start_search_collection(self, request: TwitterCollectionRequest,
                                     kafka_producer: KafkaDataProducer):
        """Start search-based tweet collection"""
        try:
            query = " OR ".join(request.keywords)
            if request.languages:
                lang_filter = " OR ".join([f"lang:{lang}" for lang in request.languages])
                query = f"({query}) ({lang_filter})"
            
            if not request.include_retweets:
                query += " -is:retweet"
            
            logger.info(f"Starting Twitter search collection with query: {query}")
            
            # Search for tweets
            tweets = tweepy.Paginator(
                self.client.search_recent_tweets,
                query=query,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 
                             'context_annotations', 'entities', 'geo', 'lang',
                             'possibly_sensitive', 'referenced_tweets', 
                             'reply_settings', 'source'],
                max_results=min(100, request.max_results or 100)
            ).flatten(limit=request.max_results or 1000)
            
            count = 0
            for tweet in tweets:
                await self.rate_limiter.wait_if_needed()
                
                tweet_data = self._process_tweet_data(tweet)
                await kafka_producer.send_data("twitter", tweet_data, request.collection_id)
                
                count += 1
                if count % 100 == 0:
                    logger.info(f"Collected {count} tweets")
            
            logger.info(f"Twitter search collection completed. Total tweets: {count}")
            
        except Exception as e:
            logger.error("Failed to collect tweets via search", error=str(e))
            raise
    
    async def _collect_user_timelines(self, request: TwitterCollectionRequest,
                                    kafka_producer: KafkaDataProducer):
        """Collect user timeline data for behavioral analysis"""
        try:
            for username in request.user_timelines:
                await self.rate_limiter.wait_if_needed()
                
                # Get user by username
                user = self.client.get_user(username=username)
                if not user.data:
                    logger.warning(f"User not found: {username}")
                    continue
                
                user_id = user.data.id
                
                # Get user tweets
                tweets = tweepy.Paginator(
                    self.client.get_users_tweets,
                    id=user_id,
                    tweet_fields=['created_at', 'author_id', 'public_metrics', 
                                 'context_annotations', 'entities', 'geo', 'lang',
                                 'possibly_sensitive', 'referenced_tweets', 
                                 'reply_settings', 'source'],
                    max_results=100
                ).flatten(limit=200)  # Limit per user
                
                count = 0
                for tweet in tweets:
                    tweet_data = self._process_tweet_data(tweet)
                    tweet_data['collection_type'] = 'user_timeline'
                    tweet_data['target_user'] = username
                    
                    await kafka_producer.send_data("twitter", tweet_data, request.collection_id)
                    count += 1
                
                logger.info(f"Collected {count} tweets from user: {username}")
                
        except Exception as e:
            logger.error("Failed to collect user timelines", error=str(e))
            raise
    
    def _process_tweet_data(self, tweet) -> Dict[str, Any]:
        """Process tweet data into standardized format"""
        return {
            "id": tweet.id,
            "text": tweet.text,
            "author_id": tweet.author_id,
            "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
            "public_metrics": getattr(tweet, 'public_metrics', {}),
            "context_annotations": getattr(tweet, 'context_annotations', []),
            "entities": getattr(tweet, 'entities', {}),
            "geo": getattr(tweet, 'geo', {}),
            "lang": getattr(tweet, 'lang', None),
            "possibly_sensitive": getattr(tweet, 'possibly_sensitive', False),
            "referenced_tweets": getattr(tweet, 'referenced_tweets', []),
            "reply_settings": getattr(tweet, 'reply_settings', None),
            "source": getattr(tweet, 'source', None),
            "collected_at": datetime.utcnow().isoformat()
        }
    
    async def stop_collection(self, collection_id: str):
        """Stop active collection"""
        if collection_id in self.active_streams:
            stream = self.active_streams[collection_id]
            stream.disconnect()
            del self.active_streams[collection_id]
            logger.info(f"Stopped Twitter collection: {collection_id}")
    
    async def get_tweet_metrics(self, tweet_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve engagement metrics for specific tweets"""
        try:
            await self.rate_limiter.wait_if_needed()
            
            tweets = self.client.get_tweets(
                ids=tweet_ids,
                tweet_fields=['public_metrics', 'non_public_metrics', 'organic_metrics']
            )
            
            metrics = []
            if tweets.data:
                for tweet in tweets.data:
                    metrics.append({
                        "id": tweet.id,
                        "public_metrics": getattr(tweet, 'public_metrics', {}),
                        "non_public_metrics": getattr(tweet, 'non_public_metrics', {}),
                        "organic_metrics": getattr(tweet, 'organic_metrics', {}),
                        "retrieved_at": datetime.utcnow().isoformat()
                    })
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get tweet metrics", error=str(e))
            return []