"""MongoDB connection manager and utilities."""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import structlog

logger = structlog.get_logger(__name__)


class MongoDBManager:
    """MongoDB connection manager with connection pooling."""
    
    def __init__(self, connection_string: str, database_name: str):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(
                self.connection_string,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                waitQueueTimeoutMS=5000,
                serverSelectionTimeoutMS=5000,
            )
            
            # Test connection
            await self.client.admin.command('ping')
            self.database = self.client[self.database_name]
            self._connected = True
            
            logger.info("Connected to MongoDB", database=self.database_name)
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")
    
    async def health_check(self) -> bool:
        """Check MongoDB connection health."""
        try:
            if not self._connected or not self.client:
                return False
            
            await self.client.admin.command('ping')
            return True
            
        except Exception as e:
            logger.error("MongoDB health check failed", error=str(e))
            return False
    
    async def create_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        # Posts collection indexes
        posts = self.database.posts
        await posts.create_index([("platform", 1), ("timestamp", -1)])
        await posts.create_index([("user_id", 1), ("timestamp", -1)])
        await posts.create_index([("analysis_results.sentiment", 1), ("timestamp", -1)])
        await posts.create_index([("analysis_results.risk_score", -1)])
        await posts.create_index([("content", "text")])
        await posts.create_index([("geolocation.coordinates", "2dsphere")])
        
        # Campaigns collection indexes
        campaigns = self.database.campaigns
        await campaigns.create_index([("status", 1), ("detection_date", -1)])
        await campaigns.create_index([("coordination_score", -1)])
        await campaigns.create_index([("participants", 1)])
        
        # User profiles collection indexes
        user_profiles = self.database.user_profiles
        await user_profiles.create_index([("platform", 1), ("user_id", 1)], unique=True)
        await user_profiles.create_index([("bot_probability", -1)])
        await user_profiles.create_index([("username", 1)])
        
        logger.info("MongoDB indexes created successfully")
    
    async def insert_post(self, post_data: Dict[str, Any]) -> str:
        """Insert a new post document."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        result = await self.database.posts.insert_one(post_data)
        return str(result.inserted_id)
    
    async def find_posts(
        self, 
        filter_query: Dict[str, Any], 
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Find posts matching the filter criteria."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        cursor = self.database.posts.find(filter_query).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def update_post_analysis(
        self, 
        post_id: str, 
        analysis_results: Dict[str, Any]
    ) -> bool:
        """Update post with analysis results."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        result = await self.database.posts.update_one(
            {"_id": post_id},
            {"$set": {"analysis_results": analysis_results}}
        )
        return result.modified_count > 0
    
    async def insert_campaign(self, campaign_data: Dict[str, Any]) -> str:
        """Insert a new campaign document."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        result = await self.database.campaigns.insert_one(campaign_data)
        return str(result.inserted_id)
    
    async def get_active_campaigns(self) -> List[Dict[str, Any]]:
        """Get all active campaigns."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        cursor = self.database.campaigns.find({"status": "active"})
        return await cursor.to_list(length=None)
    
    async def insert_user_profile(self, user_data: Dict[str, Any]) -> str:
        """Insert or update a user profile."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        # Use upsert to handle existing users
        result = await self.database.user_profiles.replace_one(
            {"platform": user_data["platform"], "user_id": user_data["user_id"]},
            user_data,
            upsert=True
        )
        
        if result.upserted_id:
            return str(result.upserted_id)
        else:
            # Find the existing document
            existing = await self.database.user_profiles.find_one(
                {"platform": user_data["platform"], "user_id": user_data["user_id"]}
            )
            return str(existing["_id"]) if existing else ""
    
    async def get_user_profile(self, platform: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by platform and user ID."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        return await self.database.user_profiles.find_one(
            {"platform": platform, "user_id": user_id}
        )
    
    async def update_user_bot_probability(self, platform: str, user_id: str, bot_probability: float) -> bool:
        """Update user's bot probability score."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        result = await self.database.user_profiles.update_one(
            {"platform": platform, "user_id": user_id},
            {"$set": {"bot_probability": bot_probability, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    async def find_posts_by_sentiment(
        self, 
        sentiment: str, 
        limit: int = 100,
        skip: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Find posts by sentiment with optional date filtering."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        filter_query = {"analysis_results.sentiment": sentiment}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            filter_query["timestamp"] = date_filter
        
        cursor = self.database.posts.find(filter_query).skip(skip).limit(limit).sort("timestamp", -1)
        return await cursor.to_list(length=limit)
    
    async def find_high_risk_posts(
        self, 
        risk_threshold: float = 0.7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find posts with high risk scores."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        cursor = self.database.posts.find(
            {"analysis_results.risk_score": {"$gte": risk_threshold}}
        ).sort("analysis_results.risk_score", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_posts_by_user(
        self, 
        user_id: str, 
        platform: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get posts by specific user."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        cursor = self.database.posts.find(
            {"user_id": user_id, "platform": platform}
        ).sort("timestamp", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def aggregate_sentiment_trends(
        self, 
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """Aggregate sentiment trends over time."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_date, "$lte": end_date},
                    "analysis_results.sentiment": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d" if interval == "1d" else "%Y-%m-%d %H:00:00",
                                "date": "$timestamp"
                            }
                        },
                        "sentiment": "$analysis_results.sentiment"
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.date": 1}
            }
        ]
        
        cursor = self.database.posts.aggregate(pipeline)
        return await cursor.to_list(length=None)
    
    async def get_campaign_participants(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get detailed information about campaign participants."""
        if not self.database:
            raise RuntimeError("Database not connected")
        
        campaign = await self.database.campaigns.find_one({"_id": campaign_id})
        if not campaign or "participants" not in campaign:
            return []
        
        # Get user profiles for all participants
        cursor = self.database.user_profiles.find(
            {"_id": {"$in": campaign["participants"]}}
        )
        return await cursor.to_list(length=None)