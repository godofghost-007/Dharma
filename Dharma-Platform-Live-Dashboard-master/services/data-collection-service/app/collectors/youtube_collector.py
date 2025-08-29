"""
YouTube data collector with API v3 integration
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import structlog

from app.models.requests import YouTubeCollectionRequest
from app.core.kafka_producer import KafkaDataProducer

logger = structlog.get_logger()


class QuotaManager:
    """Manages YouTube API quota usage"""
    
    def __init__(self, daily_limit: int = 10000):
        self.daily_limit = daily_limit
        self.used_quota = 0
        self.reset_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # API operation costs (approximate)
        self.operation_costs = {
            'search': 100,
            'videos': 1,
            'commentThreads': 1,
            'channels': 1
        }
    
    def check_quota(self, operation: str, count: int = 1) -> bool:
        """Check if operation would exceed quota"""
        # Reset quota if new day
        if datetime.utcnow() >= self.reset_time:
            self.used_quota = 0
            self.reset_time += timedelta(days=1)
        
        cost = self.operation_costs.get(operation, 1) * count
        return (self.used_quota + cost) <= self.daily_limit
    
    def consume_quota(self, operation: str, count: int = 1):
        """Consume quota for operation"""
        cost = self.operation_costs.get(operation, 1) * count
        self.used_quota += cost
        logger.info(f"Quota consumed: {cost}, Total used: {self.used_quota}/{self.daily_limit}")


class YouTubeCollector:
    """YouTube data collector with API v3 integration"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.quota_manager = QuotaManager(daily_limit=10000)
    
    async def start_collection(self, request: YouTubeCollectionRequest, 
                             kafka_producer: KafkaDataProducer):
        """Start YouTube data collection"""
        try:
            logger.info(f"Starting YouTube collection for query: {request.query}")
            
            # Search for videos
            videos = await self._search_videos(request)
            
            collected_count = 0
            for video in videos:
                # Send video data
                await kafka_producer.send_data("youtube", video, request.collection_id)
                collected_count += 1
                
                # Collect comments if requested
                if request.include_comments:
                    comments = await self._get_video_comments(
                        video['id'], 
                        request.max_comments_per_video
                    )
                    
                    for comment in comments:
                        comment['video_id'] = video['id']
                        comment['content_type'] = 'comment'
                        await kafka_producer.send_data("youtube", comment, request.collection_id)
                
                if collected_count % 10 == 0:
                    logger.info(f"Processed {collected_count} videos")
            
            logger.info(f"YouTube collection completed. Total videos: {collected_count}")
            
        except Exception as e:
            logger.error("Failed to collect YouTube data", error=str(e))
            raise
    
    async def _search_videos(self, request: YouTubeCollectionRequest) -> List[Dict[str, Any]]:
        """Search for videos with keyword filtering"""
        try:
            if not self.quota_manager.check_quota('search'):
                raise Exception("YouTube API quota exceeded")
            
            # Build search parameters
            search_params = {
                'part': 'snippet',
                'q': request.query,
                'type': 'video',
                'maxResults': min(50, request.max_results or 50),
                'order': 'relevance'
            }
            
            # Add filters
            if request.video_duration != 'any':
                search_params['videoDuration'] = request.video_duration
            
            if request.upload_date != 'any':
                if request.upload_date == 'hour':
                    published_after = datetime.utcnow() - timedelta(hours=1)
                elif request.upload_date == 'today':
                    published_after = datetime.utcnow() - timedelta(days=1)
                elif request.upload_date == 'week':
                    published_after = datetime.utcnow() - timedelta(weeks=1)
                elif request.upload_date == 'month':
                    published_after = datetime.utcnow() - timedelta(days=30)
                elif request.upload_date == 'year':
                    published_after = datetime.utcnow() - timedelta(days=365)
                
                search_params['publishedAfter'] = published_after.isoformat() + 'Z'
            
            # Execute search
            search_response = self.youtube.search().list(**search_params).execute()
            self.quota_manager.consume_quota('search')
            
            video_ids = [item['id']['videoId'] for item in search_response['items']]
            
            # Get detailed video information
            videos_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails,status',
                id=','.join(video_ids)
            ).execute()
            self.quota_manager.consume_quota('videos', len(video_ids))
            
            videos = []
            for video in videos_response['items']:
                video_data = self._process_video_data(video)
                videos.append(video_data)
            
            return videos
            
        except HttpError as e:
            logger.error("YouTube API error during search", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to search YouTube videos", error=str(e))
            raise
    
    async def _get_video_comments(self, video_id: str, max_comments: int) -> List[Dict[str, Any]]:
        """Extract comment threads for video analysis"""
        try:
            if not self.quota_manager.check_quota('commentThreads'):
                logger.warning("Quota limit reached, skipping comments")
                return []
            
            comments = []
            next_page_token = None
            
            while len(comments) < max_comments:
                request_params = {
                    'part': 'snippet,replies',
                    'videoId': video_id,
                    'maxResults': min(100, max_comments - len(comments)),
                    'order': 'relevance'
                }
                
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                try:
                    response = self.youtube.commentThreads().list(**request_params).execute()
                    self.quota_manager.consume_quota('commentThreads')
                    
                    for item in response['items']:
                        # Top-level comment
                        comment_data = self._process_comment_data(item['snippet']['topLevelComment'])
                        comments.append(comment_data)
                        
                        # Replies if any
                        if 'replies' in item:
                            for reply in item['replies']['comments']:
                                reply_data = self._process_comment_data(reply)
                                reply_data['is_reply'] = True
                                reply_data['parent_comment_id'] = comment_data['id']
                                comments.append(reply_data)
                    
                    next_page_token = response.get('nextPageToken')
                    if not next_page_token:
                        break
                        
                except HttpError as e:
                    if e.resp.status == 403:
                        logger.warning(f"Comments disabled for video: {video_id}")
                        break
                    else:
                        raise
            
            return comments[:max_comments]
            
        except Exception as e:
            logger.error("Failed to get video comments", video_id=video_id, error=str(e))
            return [] 
   
    def _process_video_data(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """Process video data into standardized format"""
        snippet = video['snippet']
        statistics = video.get('statistics', {})
        content_details = video.get('contentDetails', {})
        
        return {
            "id": video['id'],
            "title": snippet.get('title', ''),
            "description": snippet.get('description', ''),
            "channel_id": snippet.get('channelId', ''),
            "channel_title": snippet.get('channelTitle', ''),
            "published_at": snippet.get('publishedAt', ''),
            "thumbnails": snippet.get('thumbnails', {}),
            "tags": snippet.get('tags', []),
            "category_id": snippet.get('categoryId', ''),
            "default_language": snippet.get('defaultLanguage', ''),
            "default_audio_language": snippet.get('defaultAudioLanguage', ''),
            "duration": content_details.get('duration', ''),
            "dimension": content_details.get('dimension', ''),
            "definition": content_details.get('definition', ''),
            "caption": content_details.get('caption', ''),
            "licensed_content": content_details.get('licensedContent', False),
            "view_count": int(statistics.get('viewCount', 0)),
            "like_count": int(statistics.get('likeCount', 0)),
            "dislike_count": int(statistics.get('dislikeCount', 0)),
            "favorite_count": int(statistics.get('favoriteCount', 0)),
            "comment_count": int(statistics.get('commentCount', 0)),
            "content_type": "video",
            "collected_at": datetime.utcnow().isoformat()
        }
    
    def _process_comment_data(self, comment: Dict[str, Any]) -> Dict[str, Any]:
        """Process comment data into standardized format"""
        snippet = comment['snippet']
        
        return {
            "id": comment['id'],
            "text": snippet.get('textDisplay', ''),
            "text_original": snippet.get('textOriginal', ''),
            "author_display_name": snippet.get('authorDisplayName', ''),
            "author_profile_image_url": snippet.get('authorProfileImageUrl', ''),
            "author_channel_url": snippet.get('authorChannelUrl', ''),
            "author_channel_id": snippet.get('authorChannelId', {}).get('value', ''),
            "can_rate": snippet.get('canRate', False),
            "total_reply_count": snippet.get('totalReplyCount', 0),
            "like_count": snippet.get('likeCount', 0),
            "moderation_status": snippet.get('moderationStatus', ''),
            "published_at": snippet.get('publishedAt', ''),
            "updated_at": snippet.get('updatedAt', ''),
            "parent_id": snippet.get('parentId', ''),
            "is_reply": False,
            "content_type": "comment",
            "collected_at": datetime.utcnow().isoformat()
        }
    
    async def analyze_channel(self, channel_id: str) -> Dict[str, Any]:
        """Analyze channel information and subscriber patterns"""
        try:
            if not self.quota_manager.check_quota('channels'):
                raise Exception("YouTube API quota exceeded")
            
            # Get channel details
            channel_response = self.youtube.channels().list(
                part='snippet,statistics,contentDetails,status,brandingSettings',
                id=channel_id
            ).execute()
            self.quota_manager.consume_quota('channels')
            
            if not channel_response['items']:
                return {}
            
            channel = channel_response['items'][0]
            snippet = channel['snippet']
            statistics = channel.get('statistics', {})
            
            channel_analysis = {
                "id": channel['id'],
                "title": snippet.get('title', ''),
                "description": snippet.get('description', ''),
                "custom_url": snippet.get('customUrl', ''),
                "published_at": snippet.get('publishedAt', ''),
                "thumbnails": snippet.get('thumbnails', {}),
                "default_language": snippet.get('defaultLanguage', ''),
                "country": snippet.get('country', ''),
                "view_count": int(statistics.get('viewCount', 0)),
                "subscriber_count": int(statistics.get('subscriberCount', 0)),
                "hidden_subscriber_count": statistics.get('hiddenSubscriberCount', False),
                "video_count": int(statistics.get('videoCount', 0)),
                "uploads_playlist_id": channel.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads', ''),
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            return channel_analysis
            
        except HttpError as e:
            logger.error("YouTube API error during channel analysis", error=str(e))
            return {}
        except Exception as e:
            logger.error("Failed to analyze YouTube channel", error=str(e))
            return {}
    
    async def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Get recent videos from a channel"""
        try:
            # Get uploads playlist ID
            channel_analysis = await self.analyze_channel(channel_id)
            uploads_playlist_id = channel_analysis.get('uploads_playlist_id')
            
            if not uploads_playlist_id:
                return []
            
            # Get videos from uploads playlist
            playlist_response = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=min(50, max_results)
            ).execute()
            
            video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_response['items']]
            
            # Get detailed video information
            videos_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()
            
            videos = []
            for video in videos_response['items']:
                video_data = self._process_video_data(video)
                videos.append(video_data)
            
            return videos
            
        except Exception as e:
            logger.error("Failed to get channel videos", error=str(e))
            return []