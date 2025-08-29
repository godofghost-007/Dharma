"""
Data ingestion pipeline for streaming and batch processing
"""
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import structlog
from pydantic import ValidationError

from app.core.kafka_producer import KafkaDataProducer
from app.core.config import get_settings
from shared.models.post import Post, PostCreate, Platform
from shared.database.mongodb import MongoDBManager
from shared.database.redis import RedisManager

logger = structlog.get_logger()


class ProcessingStatus(str, Enum):
    """Data processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ProcessingMetrics:
    """Metrics for data processing operations"""
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    duplicate_items: int = 0
    validation_errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def processing_time(self) -> Optional[timedelta]:
        """Calculate total processing time"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class DataValidator:
    """Validates and preprocesses collected data"""
    
    def __init__(self):
        self.settings = get_settings()
        self.required_fields = {
            Platform.TWITTER: ["post_id", "user_id", "content", "timestamp"],
            Platform.YOUTUBE: ["post_id", "user_id", "content", "timestamp"],
            Platform.TELEGRAM: ["post_id", "user_id", "content", "timestamp"],
            Platform.WEB: ["post_id", "content", "timestamp"]
        }
    
    async def validate_post_data(self, platform: Platform, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and preprocess post data"""
        try:
            # Check required fields
            required = self.required_fields.get(platform, [])
            missing_fields = [field for field in required if field not in data]
            
            if missing_fields:
                raise ValidationError(f"Missing required fields: {missing_fields}")
            
            # Preprocess data
            processed_data = await self._preprocess_data(platform, data)
            
            # Validate using Pydantic model
            post_create = PostCreate(platform=platform, **processed_data)
            
            return post_create.dict()
            
        except ValidationError as e:
            logger.error("Data validation failed", platform=platform, error=str(e), data=data)
            raise
        except Exception as e:
            logger.error("Unexpected validation error", platform=platform, error=str(e))
            raise ValidationError(f"Validation error: {str(e)}")
    
    async def _preprocess_data(self, platform: Platform, data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess data based on platform"""
        processed = data.copy()
        
        # Ensure timestamp is datetime
        if "timestamp" in processed:
            if isinstance(processed["timestamp"], str):
                processed["timestamp"] = datetime.fromisoformat(processed["timestamp"].replace('Z', '+00:00'))
        
        # Clean content
        if "content" in processed:
            processed["content"] = self._clean_content(processed["content"])
        
        # Extract hashtags and mentions
        if "content" in processed:
            processed["hashtags"] = self._extract_hashtags(processed["content"])
            processed["mentions"] = self._extract_mentions(processed["content"])
        
        # Platform-specific preprocessing
        if platform == Platform.TWITTER:
            processed = await self._preprocess_twitter_data(processed)
        elif platform == Platform.YOUTUBE:
            processed = await self._preprocess_youtube_data(processed)
        elif platform == Platform.TELEGRAM:
            processed = await self._preprocess_telegram_data(processed)
        elif platform == Platform.WEB:
            processed = await self._preprocess_web_data(processed)
        
        return processed
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = " ".join(content.split())
        
        # Remove null bytes
        content = content.replace('\x00', '')
        
        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000]
        
        return content.strip()
    
    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from content"""
        import re
        hashtags = re.findall(r'#\w+', content)
        return [tag.lower() for tag in hashtags]
    
    def _extract_mentions(self, content: str) -> List[str]:
        """Extract mentions from content"""
        import re
        mentions = re.findall(r'@\w+', content)
        return [mention.lower() for mention in mentions]
    
    async def _preprocess_twitter_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Twitter-specific preprocessing"""
        # Handle retweets
        if data.get("content", "").startswith("RT @"):
            data["is_repost"] = True
        
        # Extract media URLs from entities
        if "entities" in data and "media" in data["entities"]:
            data["media_urls"] = [media["url"] for media in data["entities"]["media"]]
        
        return data
    
    async def _preprocess_youtube_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """YouTube-specific preprocessing"""
        # Handle video comments vs video descriptions
        if "video_id" in data:
            data["thread_id"] = data["video_id"]
        
        return data
    
    async def _preprocess_telegram_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Telegram-specific preprocessing"""
        # Handle channel vs group messages
        if "chat_id" in data:
            data["thread_id"] = str(data["chat_id"])
        
        return data
    
    async def _preprocess_web_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Web scraping data preprocessing"""
        # Generate user_id for web content if not present
        if "user_id" not in data:
            data["user_id"] = f"web_{hashlib.md5(data.get('url', '').encode()).hexdigest()[:8]}"
        
        return data


class DuplicateDetector:
    """Detects and handles duplicate content"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        self.duplicate_ttl = 86400 * 7  # 7 days
    
    async def is_duplicate(self, platform: Platform, post_id: str, content: str) -> bool:
        """Check if content is duplicate"""
        # Create content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check by post_id first
        post_key = f"post:{platform}:{post_id}"
        if await self.redis.exists(post_key):
            return True
        
        # Check by content hash
        content_key = f"content_hash:{content_hash}"
        if await self.redis.exists(content_key):
            return True
        
        # Store for future duplicate detection
        await self.redis.setex(post_key, self.duplicate_ttl, "1")
        await self.redis.setex(content_key, self.duplicate_ttl, "1")
        
        return False
    
    async def mark_as_processed(self, platform: Platform, post_id: str, content: str):
        """Mark content as processed"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        post_key = f"post:{platform}:{post_id}"
        content_key = f"content_hash:{content_hash}"
        
        await self.redis.setex(post_key, self.duplicate_ttl, "1")
        await self.redis.setex(content_key, self.duplicate_ttl, "1")


class DataIngestionPipeline:
    """Main data ingestion pipeline for streaming and batch processing"""
    
    def __init__(self):
        self.settings = get_settings()
        self.kafka_producer = KafkaDataProducer(self.settings.kafka_config)
        self.mongodb = MongoDBManager()
        self.redis = RedisManager()
        self.validator = DataValidator()
        self.duplicate_detector = DuplicateDetector(self.redis)
        self.processing_metrics = ProcessingMetrics()
    
    async def initialize(self):
        """Initialize pipeline components"""
        try:
            await self.mongodb.connect()
            await self.redis.connect()
            logger.info("Data ingestion pipeline initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize data ingestion pipeline", error=str(e))
            raise
    
    async def process_streaming_data(self, platform: Platform, data: Dict[str, Any], 
                                   collection_id: str) -> bool:
        """Process single item from streaming data"""
        try:
            # Validate and preprocess data
            validated_data = await self.validator.validate_post_data(platform, data)
            
            # Check for duplicates
            if await self.duplicate_detector.is_duplicate(
                platform, validated_data["post_id"], validated_data["content"]
            ):
                logger.debug("Duplicate content detected, skipping", 
                           platform=platform, post_id=validated_data["post_id"])
                return False
            
            # Send to Kafka for real-time processing
            success = await self.kafka_producer.send_data(
                platform.value, validated_data, collection_id
            )
            
            if success:
                # Store in MongoDB for persistence
                await self._store_post_data(validated_data)
                
                # Mark as processed
                await self.duplicate_detector.mark_as_processed(
                    platform, validated_data["post_id"], validated_data["content"]
                )
                
                logger.info("Successfully processed streaming data", 
                          platform=platform, post_id=validated_data["post_id"])
                return True
            else:
                logger.error("Failed to send data to Kafka", 
                           platform=platform, post_id=validated_data["post_id"])
                return False
                
        except ValidationError as e:
            logger.error("Data validation failed in streaming pipeline", 
                        platform=platform, error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error in streaming pipeline", 
                        platform=platform, error=str(e))
            return False
    
    async def process_batch_data(self, platform: Platform, data_batch: List[Dict[str, Any]], 
                               collection_id: str) -> ProcessingMetrics:
        """Process batch of historical data"""
        metrics = ProcessingMetrics(
            total_items=len(data_batch),
            start_time=datetime.utcnow()
        )
        
        logger.info("Starting batch processing", 
                   platform=platform, batch_size=len(data_batch))
        
        # Process in chunks to avoid memory issues
        chunk_size = 100
        for i in range(0, len(data_batch), chunk_size):
            chunk = data_batch[i:i + chunk_size]
            await self._process_batch_chunk(platform, chunk, collection_id, metrics)
        
        metrics.end_time = datetime.utcnow()
        
        logger.info("Batch processing completed", 
                   platform=platform,
                   total_items=metrics.total_items,
                   processed_items=metrics.processed_items,
                   failed_items=metrics.failed_items,
                   duplicate_items=metrics.duplicate_items,
                   success_rate=metrics.success_rate,
                   processing_time=metrics.processing_time)
        
        return metrics
    
    async def _process_batch_chunk(self, platform: Platform, chunk: List[Dict[str, Any]], 
                                 collection_id: str, metrics: ProcessingMetrics):
        """Process a chunk of batch data"""
        tasks = []
        
        for item in chunk:
            task = self._process_batch_item(platform, item, collection_id, metrics)
            tasks.append(task)
        
        # Process chunk concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_batch_item(self, platform: Platform, data: Dict[str, Any], 
                                collection_id: str, metrics: ProcessingMetrics):
        """Process single item in batch"""
        try:
            # Validate and preprocess data
            validated_data = await self.validator.validate_post_data(platform, data)
            
            # Check for duplicates
            if await self.duplicate_detector.is_duplicate(
                platform, validated_data["post_id"], validated_data["content"]
            ):
                metrics.duplicate_items += 1
                return
            
            # Send to Kafka
            success = await self.kafka_producer.send_data(
                platform.value, validated_data, collection_id
            )
            
            if success:
                # Store in MongoDB
                await self._store_post_data(validated_data)
                
                # Mark as processed
                await self.duplicate_detector.mark_as_processed(
                    platform, validated_data["post_id"], validated_data["content"]
                )
                
                metrics.processed_items += 1
            else:
                metrics.failed_items += 1
                
        except ValidationError:
            metrics.validation_errors += 1
        except Exception as e:
            logger.error("Error processing batch item", platform=platform, error=str(e))
            metrics.failed_items += 1
    
    async def _store_post_data(self, validated_data: Dict[str, Any]):
        """Store validated post data in MongoDB"""
        try:
            # Add processing metadata
            validated_data["processing_metadata"] = {
                "ingested_at": datetime.utcnow(),
                "pipeline_version": "1.0.0",
                "status": ProcessingStatus.COMPLETED
            }
            
            # Insert into MongoDB
            await self.mongodb.insert_document("posts", validated_data)
            
        except Exception as e:
            logger.error("Failed to store post data in MongoDB", error=str(e))
            raise
    
    async def get_processing_status(self, collection_id: str) -> Dict[str, Any]:
        """Get processing status for a collection"""
        try:
            # Get status from Redis
            status_key = f"processing_status:{collection_id}"
            status_data = await self.redis.get(status_key)
            
            if status_data:
                return json.loads(status_data)
            else:
                return {"status": "not_found", "collection_id": collection_id}
                
        except Exception as e:
            logger.error("Failed to get processing status", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def update_processing_status(self, collection_id: str, status: ProcessingStatus, 
                                     metrics: Optional[ProcessingMetrics] = None):
        """Update processing status in Redis"""
        try:
            status_data = {
                "collection_id": collection_id,
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if metrics:
                status_data["metrics"] = {
                    "total_items": metrics.total_items,
                    "processed_items": metrics.processed_items,
                    "failed_items": metrics.failed_items,
                    "duplicate_items": metrics.duplicate_items,
                    "validation_errors": metrics.validation_errors,
                    "success_rate": metrics.success_rate,
                    "processing_time": str(metrics.processing_time) if metrics.processing_time else None
                }
            
            status_key = f"processing_status:{collection_id}"
            await self.redis.setex(status_key, 86400, json.dumps(status_data))  # 24 hour TTL
            
        except Exception as e:
            logger.error("Failed to update processing status", error=str(e))
    
    async def cleanup(self):
        """Cleanup pipeline resources"""
        try:
            await self.kafka_producer.close()
            await self.mongodb.disconnect()
            await self.redis.disconnect()
            logger.info("Data ingestion pipeline cleaned up successfully")
        except Exception as e:
            logger.error("Error during pipeline cleanup", error=str(e))


# Global pipeline instance
_pipeline_instance = None


async def get_pipeline() -> DataIngestionPipeline:
    """Get or create global pipeline instance"""
    global _pipeline_instance
    
    if _pipeline_instance is None:
        _pipeline_instance = DataIngestionPipeline()
        await _pipeline_instance.initialize()
    
    return _pipeline_instance