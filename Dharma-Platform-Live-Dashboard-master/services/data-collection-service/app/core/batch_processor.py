"""
Batch processing service for historical data ingestion
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import structlog

from app.core.data_pipeline import DataIngestionPipeline, ProcessingStatus, ProcessingMetrics
from app.core.config import get_settings
from shared.models.post import Platform
from shared.database.redis import RedisManager

logger = structlog.get_logger()


class BatchJobStatus(str, Enum):
    """Batch job status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Batch processing job definition"""
    job_id: str
    platform: Platform
    data_source: str  # file path, API endpoint, etc.
    collection_id: str
    parameters: Dict[str, Any]
    status: BatchJobStatus = BatchJobStatus.QUEUED
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Optional[ProcessingMetrics] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class BatchDataLoader:
    """Loads data from various sources for batch processing"""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def load_from_file(self, file_path: str, platform: Platform) -> AsyncGenerator[Dict[str, Any], None]:
        """Load data from JSON file"""
        try:
            import aiofiles
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
            data = json.loads(content)
            
            # Handle different file formats
            if isinstance(data, list):
                for item in data:
                    yield item
            elif isinstance(data, dict):
                # Handle paginated API responses
                if 'data' in data and isinstance(data['data'], list):
                    for item in data['data']:
                        yield item
                else:
                    yield data
                    
        except Exception as e:
            logger.error("Failed to load data from file", file_path=file_path, error=str(e))
            raise
    
    async def load_from_api_export(self, api_data: Dict[str, Any], platform: Platform) -> AsyncGenerator[Dict[str, Any], None]:
        """Load data from API export format"""
        try:
            if platform == Platform.TWITTER:
                yield from self._process_twitter_export(api_data)
            elif platform == Platform.YOUTUBE:
                yield from self._process_youtube_export(api_data)
            elif platform == Platform.TELEGRAM:
                yield from self._process_telegram_export(api_data)
            else:
                # Generic processing
                if isinstance(api_data, list):
                    for item in api_data:
                        yield item
                else:
                    yield api_data
                    
        except Exception as e:
            logger.error("Failed to load data from API export", platform=platform, error=str(e))
            raise
    
    def _process_twitter_export(self, data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process Twitter API export format"""
        # Handle Twitter API v2 response format
        if 'data' in data:
            for tweet in data['data']:
                # Transform to our internal format
                processed_tweet = {
                    'post_id': tweet['id'],
                    'content': tweet['text'],
                    'timestamp': tweet['created_at'],
                    'user_id': tweet['author_id'],
                    'metrics': {
                        'likes': tweet.get('public_metrics', {}).get('like_count', 0),
                        'shares': tweet.get('public_metrics', {}).get('retweet_count', 0),
                        'comments': tweet.get('public_metrics', {}).get('reply_count', 0),
                        'views': tweet.get('public_metrics', {}).get('impression_count', 0)
                    }
                }
                
                # Add additional fields if available
                if 'entities' in tweet:
                    processed_tweet['entities'] = tweet['entities']
                
                if 'geo' in tweet:
                    processed_tweet['geolocation'] = tweet['geo']
                
                yield processed_tweet
    
    def _process_youtube_export(self, data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process YouTube API export format"""
        if 'items' in data:
            for item in data['items']:
                if item['kind'] == 'youtube#video':
                    processed_video = {
                        'post_id': item['id'],
                        'content': item['snippet']['title'] + '\n' + item['snippet']['description'],
                        'timestamp': item['snippet']['publishedAt'],
                        'user_id': item['snippet']['channelId'],
                        'metrics': {
                            'views': item.get('statistics', {}).get('viewCount', 0),
                            'likes': item.get('statistics', {}).get('likeCount', 0),
                            'comments': item.get('statistics', {}).get('commentCount', 0)
                        }
                    }
                    yield processed_video
                elif item['kind'] == 'youtube#comment':
                    processed_comment = {
                        'post_id': item['id'],
                        'content': item['snippet']['textDisplay'],
                        'timestamp': item['snippet']['publishedAt'],
                        'user_id': item['snippet']['authorChannelId']['value'],
                        'thread_id': item['snippet']['videoId'],
                        'metrics': {
                            'likes': item['snippet']['likeCount'],
                            'shares': 0,
                            'comments': 0
                        }
                    }
                    yield processed_comment
    
    def _process_telegram_export(self, data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process Telegram export format"""
        if 'messages' in data:
            for message in data['messages']:
                processed_message = {
                    'post_id': str(message['id']),
                    'content': message.get('text', ''),
                    'timestamp': message['date'],
                    'user_id': str(message.get('from_id', 'unknown')),
                    'thread_id': str(message.get('chat_id', '')),
                    'metrics': {
                        'likes': 0,
                        'shares': message.get('forwards', 0),
                        'comments': 0,
                        'views': message.get('views', 0)
                    }
                }
                
                # Handle media
                if 'media' in message:
                    processed_message['media_urls'] = [message['media']]
                
                yield processed_message


class BatchProcessor:
    """Handles batch processing of historical data"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis = RedisManager()
        self.data_loader = BatchDataLoader()
        self.pipeline = None
        self.active_jobs: Dict[str, BatchJob] = {}
        self.max_concurrent_jobs = 3
    
    async def initialize(self):
        """Initialize batch processor"""
        try:
            await self.redis.connect()
            self.pipeline = DataIngestionPipeline()
            await self.pipeline.initialize()
            logger.info("Batch processor initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize batch processor", error=str(e))
            raise
    
    async def submit_batch_job(self, platform: Platform, data_source: str, 
                             collection_id: str, parameters: Dict[str, Any] = None) -> str:
        """Submit a new batch processing job"""
        import uuid
        
        job_id = str(uuid.uuid4())
        
        job = BatchJob(
            job_id=job_id,
            platform=platform,
            data_source=data_source,
            collection_id=collection_id,
            parameters=parameters or {}
        )
        
        # Store job in Redis
        await self._store_job(job)
        
        # Queue job for processing
        await self._queue_job(job)
        
        logger.info("Batch job submitted", job_id=job_id, platform=platform, data_source=data_source)
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get status of a batch job"""
        try:
            job_key = f"batch_job:{job_id}"
            job_data = await self.redis.get(job_key)
            
            if job_data:
                job_dict = json.loads(job_data)
                return BatchJob(**job_dict)
            else:
                return None
                
        except Exception as e:
            logger.error("Failed to get job status", job_id=job_id, error=str(e))
            return None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a batch job"""
        try:
            job = await self.get_job_status(job_id)
            if not job:
                return False
            
            if job.status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED, BatchJobStatus.CANCELLED]:
                return False
            
            job.status = BatchJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            
            await self._store_job(job)
            
            # Remove from active jobs if running
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            logger.info("Batch job cancelled", job_id=job_id)
            return True
            
        except Exception as e:
            logger.error("Failed to cancel job", job_id=job_id, error=str(e))
            return False
    
    async def process_jobs(self):
        """Main job processing loop"""
        logger.info("Starting batch job processor")
        
        while True:
            try:
                # Check for queued jobs
                if len(self.active_jobs) < self.max_concurrent_jobs:
                    queued_jobs = await self._get_queued_jobs()
                    
                    for job in queued_jobs:
                        if len(self.active_jobs) >= self.max_concurrent_jobs:
                            break
                        
                        # Start processing job
                        asyncio.create_task(self._process_job(job))
                
                # Clean up completed jobs
                completed_jobs = [job_id for job_id, job in self.active_jobs.items() 
                                if job.status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED, BatchJobStatus.CANCELLED]]
                
                for job_id in completed_jobs:
                    del self.active_jobs[job_id]
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error("Error in job processing loop", error=str(e))
                await asyncio.sleep(10)
    
    async def _process_job(self, job: BatchJob):
        """Process a single batch job"""
        try:
            logger.info("Starting batch job processing", job_id=job.job_id, platform=job.platform)
            
            # Update job status
            job.status = BatchJobStatus.RUNNING
            job.started_at = datetime.utcnow()
            self.active_jobs[job.job_id] = job
            await self._store_job(job)
            
            # Load data from source
            data_items = []
            async for item in self._load_job_data(job):
                data_items.append(item)
            
            if not data_items:
                raise ValueError("No data items found in source")
            
            # Process data through pipeline
            metrics = await self.pipeline.process_batch_data(
                job.platform, data_items, job.collection_id
            )
            
            # Update job completion
            job.status = BatchJobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.metrics = metrics
            await self._store_job(job)
            
            logger.info("Batch job completed successfully", 
                       job_id=job.job_id, 
                       processed_items=metrics.processed_items,
                       success_rate=metrics.success_rate)
            
        except Exception as e:
            logger.error("Batch job failed", job_id=job.job_id, error=str(e))
            
            job.status = BatchJobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            await self._store_job(job)
    
    async def _load_job_data(self, job: BatchJob) -> AsyncGenerator[Dict[str, Any], None]:
        """Load data for a batch job"""
        data_source = job.data_source
        
        if data_source.startswith('file://'):
            file_path = data_source[7:]  # Remove 'file://' prefix
            async for item in self.data_loader.load_from_file(file_path, job.platform):
                yield item
        elif data_source.startswith('api://'):
            # Handle API data source
            api_data = job.parameters.get('api_data', {})
            async for item in self.data_loader.load_from_api_export(api_data, job.platform):
                yield item
        else:
            raise ValueError(f"Unsupported data source format: {data_source}")
    
    async def _store_job(self, job: BatchJob):
        """Store job in Redis"""
        try:
            job_key = f"batch_job:{job.job_id}"
            job_data = {
                'job_id': job.job_id,
                'platform': job.platform.value,
                'data_source': job.data_source,
                'collection_id': job.collection_id,
                'parameters': job.parameters,
                'status': job.status.value,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'error_message': job.error_message,
                'metrics': job.metrics.__dict__ if job.metrics else None
            }
            
            await self.redis.setex(job_key, 86400 * 7, json.dumps(job_data))  # 7 day TTL
            
        except Exception as e:
            logger.error("Failed to store job", job_id=job.job_id, error=str(e))
    
    async def _queue_job(self, job: BatchJob):
        """Add job to processing queue"""
        try:
            queue_key = "batch_job_queue"
            await self.redis.lpush(queue_key, job.job_id)
            
        except Exception as e:
            logger.error("Failed to queue job", job_id=job.job_id, error=str(e))
    
    async def _get_queued_jobs(self) -> List[BatchJob]:
        """Get queued jobs for processing"""
        try:
            queue_key = "batch_job_queue"
            job_ids = await self.redis.lrange(queue_key, 0, self.max_concurrent_jobs - len(self.active_jobs) - 1)
            
            jobs = []
            for job_id in job_ids:
                job = await self.get_job_status(job_id.decode() if isinstance(job_id, bytes) else job_id)
                if job and job.status == BatchJobStatus.QUEUED:
                    jobs.append(job)
                    # Remove from queue
                    await self.redis.lrem(queue_key, 1, job_id)
            
            return jobs
            
        except Exception as e:
            logger.error("Failed to get queued jobs", error=str(e))
            return []
    
    async def cleanup(self):
        """Cleanup batch processor resources"""
        try:
            if self.pipeline:
                await self.pipeline.cleanup()
            await self.redis.disconnect()
            logger.info("Batch processor cleaned up successfully")
        except Exception as e:
            logger.error("Error during batch processor cleanup", error=str(e))


# Global batch processor instance
_batch_processor_instance = None


async def get_batch_processor() -> BatchProcessor:
    """Get or create global batch processor instance"""
    global _batch_processor_instance
    
    if _batch_processor_instance is None:
        _batch_processor_instance = BatchProcessor()
        await _batch_processor_instance.initialize()
    
    return _batch_processor_instance