"""
Telegram data collector using Telethon
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat, User
import structlog

from app.core.config import TelegramCredentials
from app.models.requests import TelegramCollectionRequest
from app.core.kafka_producer import KafkaDataProducer

logger = structlog.get_logger()


class TelegramCollector:
    """Telegram data collector using Telethon"""
    
    def __init__(self, credentials: TelegramCredentials):
        self.credentials = credentials
        self.client = None
        self.active_collections = {}
    
    async def _initialize_client(self):
        """Initialize Telegram client with authentication"""
        if self.client and self.client.is_connected():
            return
        
        try:
            self.client = TelegramClient(
                'dharma_session',
                self.credentials.api_id,
                self.credentials.api_hash
            )
            
            await self.client.start(phone=self.credentials.phone_number)
            
            if not await self.client.is_user_authorized():
                logger.error("Telegram client not authorized")
                raise Exception("Telegram authentication failed")
            
            logger.info("Telegram client initialized successfully")
            
        except SessionPasswordNeededError:
            logger.error("Two-factor authentication required for Telegram")
            raise Exception("2FA required - please configure in settings")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            raise
    
    async def start_collection(self, request: TelegramCollectionRequest,
                             kafka_producer: KafkaDataProducer):
        """Start Telegram data collection"""
        try:
            await self._initialize_client()
            
            logger.info(f"Starting Telegram collection for {len(request.channels)} channels")
            
            # Collect historical messages if requested
            if request.historical_days and request.historical_days > 0:
                await self._collect_historical_messages(request, kafka_producer)
            
            # Start real-time monitoring
            await self._start_real_time_monitoring(request, kafka_producer)
            
        except Exception as e:
            logger.error("Failed to start Telegram collection", error=str(e))
            raise
    
    async def _collect_historical_messages(self, request: TelegramCollectionRequest,
                                         kafka_producer: KafkaDataProducer):
        """Collect historical messages from channels"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=request.historical_days)
            
            for channel_username in request.channels:
                try:
                    # Get channel entity
                    channel = await self.client.get_entity(channel_username)
                    
                    logger.info(f"Collecting historical messages from {channel_username}")
                    
                    message_count = 0
                    async for message in self.client.iter_messages(
                        channel,
                        offset_date=cutoff_date,
                        limit=request.max_results or 1000
                    ):
                        try:
                            # Process message
                            message_data = await self._process_message(message, channel)
                            message_data['collection_type'] = 'historical'
                            
                            # Send to Kafka
                            await kafka_producer.send_data("telegram", message_data, request.collection_id)
                            
                            message_count += 1
                            
                            if message_count % 100 == 0:
                                logger.info(f"Collected {message_count} messages from {channel_username}")
                            
                            # Respect rate limits
                            await asyncio.sleep(0.1)
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            continue
                    
                    logger.info(f"Completed historical collection for {channel_username}: {message_count} messages")
                    
                except FloodWaitError as e:
                    logger.warning(f"Rate limited for {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logger.error(f"Failed to collect from channel {channel_username}: {e}")
                    continue
                    
        except Exception as e:
            logger.error("Failed to collect historical messages", error=str(e))
            raise
    
    async def _start_real_time_monitoring(self, request: TelegramCollectionRequest,
                                        kafka_producer: KafkaDataProducer):
        """Start real-time message monitoring"""
        try:
            # Get channel entities
            channels = []
            for channel_username in request.channels:
                try:
                    channel = await self.client.get_entity(channel_username)
                    channels.append(channel)
                except Exception as e:
                    logger.error(f"Failed to get channel {channel_username}: {e}")
                    continue
            
            if not channels:
                logger.warning("No valid channels found for monitoring")
                return
            
            logger.info(f"Starting real-time monitoring for {len(channels)} channels")
            
            # Store collection info
            self.active_collections[request.collection_id] = {
                'channels': channels,
                'kafka_producer': kafka_producer,
                'include_media': request.include_media,
                'start_time': datetime.utcnow()
            }
            
            # Set up event handler
            @self.client.on(events.NewMessage(chats=channels))
            async def handle_new_message(event):
                try:
                    message_data = await self._process_message(event.message, event.chat)
                    message_data['collection_type'] = 'real_time'
                    
                    await kafka_producer.send_data("telegram", message_data, request.collection_id)
                    
                    logger.debug(f"Processed real-time message from {event.chat.username or event.chat.title}")
                    
                except Exception as e:
                    logger.error(f"Error processing real-time message: {e}")
            
            # Keep monitoring (in production, this would be managed differently)
            logger.info("Real-time Telegram monitoring started")
            
        except Exception as e:
            logger.error("Failed to start real-time monitoring", error=str(e))
            raise
    
    async def _process_message(self, message, chat) -> Dict[str, Any]:
        """Process Telegram message into standardized format"""
        try:
            # Basic message data
            message_data = {
                "id": message.id,
                "text": message.text or "",
                "date": message.date.isoformat() if message.date else None,
                "chat_id": chat.id,
                "chat_title": getattr(chat, 'title', ''),
                "chat_username": getattr(chat, 'username', ''),
                "chat_type": self._get_chat_type(chat),
                "message_type": "text",
                "collected_at": datetime.utcnow().isoformat()
            }
            
            # Sender information
            if message.sender:
                sender_data = await self._process_sender(message.sender)
                message_data.update(sender_data)
            
            # Media information
            if message.media:
                media_data = await self._process_media(message.media)
                message_data.update(media_data)
            
            # Forward information
            if message.forward:
                forward_data = self._process_forward_info(message.forward)
                message_data['forward_info'] = forward_data
            
            # Reply information
            if message.reply_to:
                message_data['reply_to_message_id'] = message.reply_to.reply_to_msg_id
            
            # Message statistics
            message_data['views'] = getattr(message, 'views', 0)
            message_data['edit_date'] = message.edit_date.isoformat() if message.edit_date else None
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "id": getattr(message, 'id', 0),
                "text": "",
                "error": str(e),
                "collected_at": datetime.utcnow().isoformat()
            }
    
    async def _process_sender(self, sender) -> Dict[str, Any]:
        """Process sender information"""
        sender_data = {
            "sender_id": sender.id,
            "sender_type": "user" if isinstance(sender, User) else "channel"
        }
        
        if isinstance(sender, User):
            sender_data.update({
                "sender_username": getattr(sender, 'username', ''),
                "sender_first_name": getattr(sender, 'first_name', ''),
                "sender_last_name": getattr(sender, 'last_name', ''),
                "sender_phone": getattr(sender, 'phone', ''),
                "sender_is_bot": getattr(sender, 'bot', False),
                "sender_is_verified": getattr(sender, 'verified', False)
            })
        elif isinstance(sender, (Channel, Chat)):
            sender_data.update({
                "sender_title": getattr(sender, 'title', ''),
                "sender_username": getattr(sender, 'username', ''),
                "sender_is_verified": getattr(sender, 'verified', False)
            })
        
        return sender_data
    
    async def _process_media(self, media) -> Dict[str, Any]:
        """Process media information"""
        media_data = {
            "has_media": True,
            "media_type": type(media).__name__
        }
        
        # Add specific media information based on type
        if hasattr(media, 'photo'):
            media_data['message_type'] = 'photo'
        elif hasattr(media, 'document'):
            media_data['message_type'] = 'document'
            if hasattr(media.document, 'mime_type'):
                media_data['mime_type'] = media.document.mime_type
        elif hasattr(media, 'webpage'):
            media_data['message_type'] = 'webpage'
            if hasattr(media.webpage, 'url'):
                media_data['webpage_url'] = media.webpage.url
        
        return media_data
    
    def _process_forward_info(self, forward) -> Dict[str, Any]:
        """Process forward information"""
        forward_data = {
            "is_forwarded": True,
            "forward_date": forward.date.isoformat() if forward.date else None
        }
        
        if forward.from_id:
            forward_data['forward_from_id'] = forward.from_id.user_id if hasattr(forward.from_id, 'user_id') else str(forward.from_id)
        
        if forward.from_name:
            forward_data['forward_from_name'] = forward.from_name
        
        if forward.channel_post:
            forward_data['forward_channel_post'] = forward.channel_post
        
        return forward_data
    
    def _get_chat_type(self, chat) -> str:
        """Determine chat type"""
        if isinstance(chat, User):
            return "private"
        elif isinstance(chat, Chat):
            return "group"
        elif isinstance(chat, Channel):
            if getattr(chat, 'megagroup', False):
                return "supergroup"
            else:
                return "channel"
        else:
            return "unknown"
    
    async def get_channel_info(self, channel_username: str) -> Dict[str, Any]:
        """Get detailed channel information"""
        try:
            await self._initialize_client()
            
            channel = await self.client.get_entity(channel_username)
            
            channel_info = {
                "id": channel.id,
                "title": getattr(channel, 'title', ''),
                "username": getattr(channel, 'username', ''),
                "description": getattr(channel, 'about', ''),
                "participants_count": getattr(channel, 'participants_count', 0),
                "is_verified": getattr(channel, 'verified', False),
                "is_restricted": getattr(channel, 'restricted', False),
                "is_scam": getattr(channel, 'scam', False),
                "is_fake": getattr(channel, 'fake', False),
                "creation_date": channel.date.isoformat() if hasattr(channel, 'date') and channel.date else None,
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            return channel_info
            
        except Exception as e:
            logger.error(f"Failed to get channel info for {channel_username}: {e}")
            return {}
    
    async def get_channel_participants(self, channel_username: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get channel participants for analysis"""
        try:
            await self._initialize_client()
            
            channel = await self.client.get_entity(channel_username)
            participants = []
            
            async for user in self.client.iter_participants(channel, limit=limit):
                participant_data = {
                    "id": user.id,
                    "username": getattr(user, 'username', ''),
                    "first_name": getattr(user, 'first_name', ''),
                    "last_name": getattr(user, 'last_name', ''),
                    "phone": getattr(user, 'phone', ''),
                    "is_bot": getattr(user, 'bot', False),
                    "is_verified": getattr(user, 'verified', False),
                    "is_restricted": getattr(user, 'restricted', False),
                    "is_scam": getattr(user, 'scam', False),
                    "is_fake": getattr(user, 'fake', False),
                    "collected_at": datetime.utcnow().isoformat()
                }
                participants.append(participant_data)
            
            return participants
            
        except Exception as e:
            logger.error(f"Failed to get participants for {channel_username}: {e}")
            return []
    
    async def stop_collection(self, collection_id: str):
        """Stop active collection"""
        if collection_id in self.active_collections:
            # Remove event handlers and cleanup
            collection_info = self.active_collections[collection_id]
            
            # In a real implementation, you'd remove specific event handlers
            # For now, we'll just remove from active collections
            del self.active_collections[collection_id]
            
            logger.info(f"Stopped Telegram collection: {collection_id}")
    
    async def close(self):
        """Close Telegram client"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info("Telegram client disconnected")