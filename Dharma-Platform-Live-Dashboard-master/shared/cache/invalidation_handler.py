"""Cache invalidation event handlers."""

import json
from typing import Dict, List, Callable, Any
from datetime import datetime
import structlog
from .cache_manager import CacheManager
from .cache_policies import CachePolicies

logger = structlog.get_logger(__name__)


class CacheInvalidationHandler:
    """Handles cache invalidation events and strategies."""
    
    def __init__(self, cache_manager: CacheManager, cache_policies: CachePolicies):
        self.cache_manager = cache_manager
        self.cache_policies = cache_policies
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default invalidation handlers."""
        
        # User-related invalidations
        self.register_handler("user_profile_updated", self._handle_user_profile_update)
        self.register_handler("user_deleted", self._handle_user_deletion)
        self.register_handler("user_logout", self._handle_user_logout)
        
        # AI model updates
        self.register_handler("sentiment_model_updated", self._handle_sentiment_model_update)
        self.register_handler("bot_model_updated", self._handle_bot_model_update)
        self.register_handler("campaign_model_updated", self._handle_campaign_model_update)
        
        # Campaign updates
        self.register_handler("campaign_updated", self._handle_campaign_update)
        self.register_handler("campaign_deleted", self._handle_campaign_deletion)
        
        # Data updates
        self.register_handler("post_analyzed", self._handle_post_analysis)
        self.register_handler("alert_created", self._handle_alert_creation)
        
        # System events
        self.register_handler("database_updated", self._handle_database_update)
        self.register_handler("content_updated", self._handle_content_update)
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        self._event_handlers[event_type].append(handler)
        logger.debug("Invalidation handler registered", event_type=event_type)
    
    async def handle_event(self, event_type: str, data: Dict[str, Any]):
        """Handle cache invalidation event."""
        logger.info("Processing cache invalidation event", 
                   event_type=event_type, data=data)
        
        handlers = self._event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error("Invalidation handler failed", 
                           event_type=event_type, handler=handler.__name__, error=str(e))
        
        # Publish event for other instances
        await self._publish_invalidation_event(event_type, data)
    
    async def _publish_invalidation_event(self, event_type: str, data: Dict):
        """Publish invalidation event to Redis."""
        event_data = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "cache_invalidation_handler"
        }
        
        await self.cache_manager.redis.publish(
            f"cache_invalidation:{event_type}", 
            event_data
        )
    
    # Default event handlers
    
    async def _handle_user_profile_update(self, data: Dict):
        """Handle user profile update event."""
        user_id = data.get("user_id")
        if not user_id:
            return
        
        # Invalidate user-specific caches
        patterns = [
            f"user:{user_id}*",
            f"profile:{user_id}*",
            f"dashboard:user:{user_id}*",
            f"session:{user_id}*"
        ]
        
        for pattern in patterns:
            await self.cache_manager.invalidate_by_pattern(pattern)
        
        logger.info("User profile cache invalidated", user_id=user_id)
    
    async def _handle_user_deletion(self, data: Dict):
        """Handle user deletion event."""
        user_id = data.get("user_id")
        if not user_id:
            return
        
        # Invalidate all user-related caches
        patterns = [
            f"user:{user_id}*",
            f"profile:{user_id}*",
            f"dashboard:user:{user_id}*",
            f"session:{user_id}*",
            f"auth:{user_id}*"
        ]
        
        for pattern in patterns:
            await self.cache_manager.invalidate_by_pattern(pattern)
        
        logger.info("User deletion cache invalidated", user_id=user_id)
    
    async def _handle_user_logout(self, data: Dict):
        """Handle user logout event."""
        user_id = data.get("user_id")
        session_id = data.get("session_id")
        
        if user_id:
            await self.cache_manager.invalidate_by_pattern(f"session:{user_id}*")
        
        if session_id:
            await self.cache_manager.delete(f"session:{session_id}")
        
        logger.info("User logout cache invalidated", user_id=user_id, session_id=session_id)
    
    async def _handle_sentiment_model_update(self, data: Dict):
        """Handle sentiment model update event."""
        model_version = data.get("model_version")
        
        # Invalidate all sentiment analysis results
        await self.cache_manager.invalidate_by_tags(["sentiment", "ai_analysis"])
        
        # Invalidate dashboard metrics that depend on sentiment
        await self.cache_manager.invalidate_by_pattern("dashboard:sentiment*")
        await self.cache_manager.invalidate_by_pattern("metrics:sentiment*")
        
        logger.info("Sentiment model cache invalidated", model_version=model_version)
    
    async def _handle_bot_model_update(self, data: Dict):
        """Handle bot detection model update event."""
        model_version = data.get("model_version")
        
        # Invalidate all bot detection results
        await self.cache_manager.invalidate_by_tags(["bot_detection", "ai_analysis"])
        
        # Invalidate related dashboard metrics
        await self.cache_manager.invalidate_by_pattern("dashboard:bot*")
        await self.cache_manager.invalidate_by_pattern("metrics:bot*")
        
        logger.info("Bot model cache invalidated", model_version=model_version)
    
    async def _handle_campaign_model_update(self, data: Dict):
        """Handle campaign detection model update event."""
        model_version = data.get("model_version")
        
        # Invalidate all campaign analysis results
        await self.cache_manager.invalidate_by_tags(["campaign_analysis", "ai_analysis"])
        
        # Invalidate campaign dashboards
        await self.cache_manager.invalidate_by_pattern("dashboard:campaign*")
        await self.cache_manager.invalidate_by_pattern("campaign:*")
        
        logger.info("Campaign model cache invalidated", model_version=model_version)
    
    async def _handle_campaign_update(self, data: Dict):
        """Handle campaign update event."""
        campaign_id = data.get("campaign_id")
        if not campaign_id:
            return
        
        # Invalidate campaign-specific caches
        patterns = [
            f"campaign:{campaign_id}*",
            f"dashboard:campaign:{campaign_id}*",
            f"analysis:campaign:{campaign_id}*"
        ]
        
        for pattern in patterns:
            await self.cache_manager.invalidate_by_pattern(pattern)
        
        # Invalidate campaign list caches
        await self.cache_manager.invalidate_by_pattern("campaigns:list*")
        
        logger.info("Campaign cache invalidated", campaign_id=campaign_id)
    
    async def _handle_campaign_deletion(self, data: Dict):
        """Handle campaign deletion event."""
        campaign_id = data.get("campaign_id")
        if not campaign_id:
            return
        
        # Invalidate all campaign-related caches
        patterns = [
            f"campaign:{campaign_id}*",
            f"dashboard:campaign:{campaign_id}*",
            f"analysis:campaign:{campaign_id}*",
            f"network:campaign:{campaign_id}*"
        ]
        
        for pattern in patterns:
            await self.cache_manager.invalidate_by_pattern(pattern)
        
        # Invalidate campaign lists
        await self.cache_manager.invalidate_by_pattern("campaigns:*")
        
        logger.info("Campaign deletion cache invalidated", campaign_id=campaign_id)
    
    async def _handle_post_analysis(self, data: Dict):
        """Handle post analysis completion event."""
        post_id = data.get("post_id")
        platform = data.get("platform")
        
        if post_id:
            # Invalidate post-specific caches
            await self.cache_manager.invalidate_by_pattern(f"post:{post_id}*")
            await self.cache_manager.invalidate_by_pattern(f"analysis:post:{post_id}*")
        
        if platform:
            # Invalidate platform metrics
            await self.cache_manager.invalidate_by_pattern(f"metrics:platform:{platform}*")
        
        # Invalidate dashboard metrics
        await self.cache_manager.invalidate_by_tags(["dashboard", "metrics"])
        
        logger.info("Post analysis cache invalidated", post_id=post_id, platform=platform)
    
    async def _handle_alert_creation(self, data: Dict):
        """Handle alert creation event."""
        alert_id = data.get("alert_id")
        severity = data.get("severity")
        
        # Invalidate alert-related caches
        await self.cache_manager.invalidate_by_pattern("alerts:*")
        await self.cache_manager.invalidate_by_pattern("dashboard:alerts*")
        
        if severity:
            await self.cache_manager.invalidate_by_pattern(f"alerts:severity:{severity}*")
        
        logger.info("Alert creation cache invalidated", alert_id=alert_id, severity=severity)
    
    async def _handle_database_update(self, data: Dict):
        """Handle database update event."""
        table = data.get("table")
        operation = data.get("operation")
        
        if table:
            # Invalidate table-specific caches
            await self.cache_manager.invalidate_by_pattern(f"db:{table}*")
            await self.cache_manager.invalidate_by_tags([f"table_{table}"])
        
        # Invalidate general database caches
        await self.cache_manager.invalidate_by_tags(["database", "queries"])
        
        logger.info("Database update cache invalidated", table=table, operation=operation)
    
    async def _handle_content_update(self, data: Dict):
        """Handle content update event."""
        content_type = data.get("content_type")
        content_id = data.get("content_id")
        
        if content_id:
            await self.cache_manager.invalidate_by_pattern(f"content:{content_id}*")
        
        if content_type:
            await self.cache_manager.invalidate_by_pattern(f"content:type:{content_type}*")
        
        # Invalidate static content caches
        await self.cache_manager.invalidate_by_tags(["static", "content"])
        
        logger.info("Content update cache invalidated", 
                   content_type=content_type, content_id=content_id)
    
    async def setup_event_listeners(self):
        """Setup Redis pub/sub listeners for cache invalidation events."""
        try:
            # Subscribe to all cache invalidation events
            pubsub = await self.cache_manager.redis.subscribe("cache_invalidation:*")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        channel = message["channel"]
                        event_type = channel.split(":")[-1]
                        data = json.loads(message["data"])
                        
                        await self.handle_event(event_type, data.get("data", {}))
                        
                    except Exception as e:
                        logger.error("Failed to process invalidation event", 
                                   message=message, error=str(e))
        
        except Exception as e:
            logger.error("Failed to setup cache invalidation listeners", error=str(e))