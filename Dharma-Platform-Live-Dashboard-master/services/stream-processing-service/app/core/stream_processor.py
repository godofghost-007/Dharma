"""
Core stream processing engine with Kafka Streams topology
"""
import json
import asyncio
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timedelta
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import structlog

from .kafka_config import KafkaStreamConfig, KafkaTopicManager

logger = structlog.get_logger()


class StreamProcessor:
    """Core stream processing engine for real-time data analysis"""
    
    def __init__(self, config: KafkaStreamConfig):
        self.config = config
        self.topic_manager = KafkaTopicManager(config)
        self.consumer = None
        self.producer = None
        self.processing_handlers = {}
        self.running = False
        
    async def initialize(self):
        """Initialize stream processor"""
        # Create topics if they don't exist
        await self.topic_manager.create_topics()
        
        # Initialize Kafka consumer and producer
        self._initialize_kafka_clients()
        
        logger.info("Stream processor initialized successfully")
    
    def _initialize_kafka_clients(self):
        """Initialize Kafka consumer and producer"""
        try:
            self.consumer = KafkaConsumer(
                **self.config.consumer_config,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            self.producer = KafkaProducer(
                **self.config.producer_config,
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8')
            )
            
            logger.info("Kafka clients initialized")
        except Exception as e:
            logger.error("Failed to initialize Kafka clients", error=str(e))
            raise
    
    def register_handler(self, topic: str, handler: Callable):
        """Register processing handler for a topic"""
        self.processing_handlers[topic] = handler
        logger.info("Registered handler for topic", topic=topic)
    
    async def start_processing(self, topics: List[str]):
        """Start stream processing for specified topics"""
        if not self.consumer or not self.producer:
            raise RuntimeError("Stream processor not initialized")
        
        self.consumer.subscribe(topics)
        self.running = True
        
        logger.info("Starting stream processing", topics=topics)
        
        try:
            while self.running:
                # Poll for messages with timeout
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if not message_batch:
                    continue
                
                # Process messages in parallel
                tasks = []
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        task = asyncio.create_task(
                            self._process_message(message)
                        )
                        tasks.append(task)
                
                # Wait for all processing tasks to complete
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Commit offsets after successful processing
                    self.consumer.commit()
                
        except Exception as e:
            logger.error("Error in stream processing", error=str(e))
            raise
        finally:
            self.running = False
    
    async def _process_message(self, message):
        """Process individual message"""
        try:
            topic = message.topic
            data = message.value
            
            # Add processing metadata
            processing_context = {
                "topic": topic,
                "partition": message.partition,
                "offset": message.offset,
                "timestamp": datetime.utcnow().isoformat(),
                "original_data": data
            }
            
            # Find and execute handler
            handler = self.processing_handlers.get(topic)
            if handler:
                result = await handler(data, processing_context)
                
                # Route result to appropriate output topic
                await self._route_result(topic, result, processing_context)
            else:
                logger.warning("No handler registered for topic", topic=topic)
                
        except Exception as e:
            logger.error("Error processing message", error=str(e), topic=message.topic)
            await self._send_to_dead_letter_queue(message, str(e))
    
    async def _route_result(self, input_topic: str, result: Dict[str, Any], context: Dict):
        """Route processing result to appropriate output topic"""
        try:
            output_topic = self._get_output_topic(input_topic)
            
            if output_topic and result:
                # Add routing metadata
                result["processing_metadata"] = context
                
                # Send to output topic
                future = self.producer.send(output_topic, value=result)
                await asyncio.wrap_future(future)
                
                logger.debug("Result routed to output topic", 
                           input_topic=input_topic, 
                           output_topic=output_topic)
                
        except Exception as e:
            logger.error("Error routing result", error=str(e), input_topic=input_topic)
    
    def _get_output_topic(self, input_topic: str) -> Optional[str]:
        """Determine output topic based on input topic"""
        topic_routing = {
            self.topic_manager.topics["raw_twitter"]: self.topic_manager.topics["sentiment_analysis"],
            self.topic_manager.topics["raw_youtube"]: self.topic_manager.topics["sentiment_analysis"],
            self.topic_manager.topics["raw_web"]: self.topic_manager.topics["sentiment_analysis"],
            self.topic_manager.topics["raw_telegram"]: self.topic_manager.topics["sentiment_analysis"],
            self.topic_manager.topics["sentiment_analysis"]: self.topic_manager.topics["analysis_results"],
            self.topic_manager.topics["bot_detection"]: self.topic_manager.topics["analysis_results"],
            self.topic_manager.topics["campaign_detection"]: self.topic_manager.topics["campaigns"]
        }
        
        return topic_routing.get(input_topic)
    
    async def _send_to_dead_letter_queue(self, message, error: str):
        """Send failed message to dead letter queue"""
        try:
            dlq_message = {
                "original_topic": message.topic,
                "original_partition": message.partition,
                "original_offset": message.offset,
                "original_data": message.value,
                "error": error,
                "failed_at": datetime.utcnow().isoformat()
            }
            
            future = self.producer.send(
                self.topic_manager.topics["dead_letter_queue"],
                value=dlq_message
            )
            await asyncio.wrap_future(future)
            
            logger.info("Message sent to dead letter queue", 
                       original_topic=message.topic, 
                       error=error)
                       
        except Exception as e:
            logger.error("Failed to send to dead letter queue", error=str(e))
    
    async def stop_processing(self):
        """Stop stream processing"""
        self.running = False
        
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.close()
        
        logger.info("Stream processor stopped")


class StreamTopology:
    """Defines stream processing topology and data flow"""
    
    def __init__(self, stream_processor: StreamProcessor):
        self.processor = stream_processor
        self.topology_config = {}
    
    def build_topology(self):
        """Build complete stream processing topology"""
        # Register handlers for each processing stage
        self._register_data_ingestion_handlers()
        self._register_analysis_handlers()
        self._register_result_handlers()
        
        logger.info("Stream topology built successfully")
    
    def _register_data_ingestion_handlers(self):
        """Register handlers for raw data ingestion"""
        topics = self.processor.topic_manager.topics
        
        # Raw data preprocessing handlers
        self.processor.register_handler(
            topics["raw_twitter"], 
            self._preprocess_twitter_data
        )
        self.processor.register_handler(
            topics["raw_youtube"], 
            self._preprocess_youtube_data
        )
        self.processor.register_handler(
            topics["raw_web"], 
            self._preprocess_web_data
        )
        self.processor.register_handler(
            topics["raw_telegram"], 
            self._preprocess_telegram_data
        )
    
    def _register_analysis_handlers(self):
        """Register handlers for AI analysis stages"""
        topics = self.processor.topic_manager.topics
        
        # Analysis stage handlers
        self.processor.register_handler(
            topics["sentiment_analysis"],
            self._handle_sentiment_analysis
        )
        self.processor.register_handler(
            topics["bot_detection"],
            self._handle_bot_detection
        )
        self.processor.register_handler(
            topics["campaign_detection"],
            self._handle_campaign_detection
        )
    
    def _register_result_handlers(self):
        """Register handlers for processing results"""
        topics = self.processor.topic_manager.topics
        
        # Result processing handlers
        self.processor.register_handler(
            topics["analysis_results"],
            self._handle_analysis_results
        )
        self.processor.register_handler(
            topics["alerts"],
            self._handle_alerts
        )
    
    async def _preprocess_twitter_data(self, data: Dict, context: Dict) -> Dict:
        """Preprocess Twitter data for analysis"""
        try:
            processed = {
                "platform": "twitter",
                "content": data.get("text", ""),
                "user_id": data.get("user_id"),
                "post_id": data.get("id"),
                "timestamp": data.get("created_at"),
                "metrics": {
                    "likes": data.get("public_metrics", {}).get("like_count", 0),
                    "retweets": data.get("public_metrics", {}).get("retweet_count", 0),
                    "replies": data.get("public_metrics", {}).get("reply_count", 0)
                },
                "raw_data": data
            }
            
            logger.debug("Preprocessed Twitter data", post_id=processed["post_id"])
            return processed
            
        except Exception as e:
            logger.error("Error preprocessing Twitter data", error=str(e))
            return {}
    
    async def _preprocess_youtube_data(self, data: Dict, context: Dict) -> Dict:
        """Preprocess YouTube data for analysis"""
        try:
            processed = {
                "platform": "youtube",
                "content": data.get("snippet", {}).get("textDisplay", ""),
                "user_id": data.get("snippet", {}).get("authorChannelId", {}).get("value"),
                "post_id": data.get("id"),
                "timestamp": data.get("snippet", {}).get("publishedAt"),
                "metrics": {
                    "likes": data.get("snippet", {}).get("likeCount", 0)
                },
                "raw_data": data
            }
            
            logger.debug("Preprocessed YouTube data", post_id=processed["post_id"])
            return processed
            
        except Exception as e:
            logger.error("Error preprocessing YouTube data", error=str(e))
            return {}
    
    async def _preprocess_web_data(self, data: Dict, context: Dict) -> Dict:
        """Preprocess web scraped data for analysis"""
        try:
            processed = {
                "platform": "web",
                "content": data.get("content", ""),
                "url": data.get("url"),
                "title": data.get("title"),
                "timestamp": data.get("published_date"),
                "raw_data": data
            }
            
            logger.debug("Preprocessed web data", url=processed["url"])
            return processed
            
        except Exception as e:
            logger.error("Error preprocessing web data", error=str(e))
            return {}
    
    async def _preprocess_telegram_data(self, data: Dict, context: Dict) -> Dict:
        """Preprocess Telegram data for analysis"""
        try:
            processed = {
                "platform": "telegram",
                "content": data.get("message", ""),
                "user_id": data.get("from_id"),
                "post_id": data.get("id"),
                "timestamp": data.get("date"),
                "channel": data.get("peer_id"),
                "raw_data": data
            }
            
            logger.debug("Preprocessed Telegram data", post_id=processed["post_id"])
            return processed
            
        except Exception as e:
            logger.error("Error preprocessing Telegram data", error=str(e))
            return {}
    
    async def _handle_sentiment_analysis(self, data: Dict, context: Dict) -> Dict:
        """Handle sentiment analysis processing"""
        # This will be implemented when AI analysis service is integrated
        logger.info("Processing sentiment analysis", content_length=len(data.get("content", "")))
        
        # Placeholder for actual sentiment analysis
        return {
            "analysis_type": "sentiment",
            "input_data": data,
            "status": "queued_for_analysis"
        }
    
    async def _handle_bot_detection(self, data: Dict, context: Dict) -> Dict:
        """Handle bot detection processing"""
        logger.info("Processing bot detection", user_id=data.get("user_id"))
        
        # Placeholder for actual bot detection
        return {
            "analysis_type": "bot_detection",
            "input_data": data,
            "status": "queued_for_analysis"
        }
    
    async def _handle_campaign_detection(self, data: Dict, context: Dict) -> Dict:
        """Handle campaign detection processing"""
        logger.info("Processing campaign detection")
        
        # Placeholder for actual campaign detection
        return {
            "analysis_type": "campaign_detection",
            "input_data": data,
            "status": "queued_for_analysis"
        }
    
    async def _handle_analysis_results(self, data: Dict, context: Dict) -> Dict:
        """Handle analysis results processing"""
        logger.info("Processing analysis results", analysis_type=data.get("analysis_type"))
        
        # Store results and trigger alerts if needed
        return {
            "result_type": "analysis_complete",
            "data": data
        }
    
    async def _handle_alerts(self, data: Dict, context: Dict) -> Dict:
        """Handle alert processing"""
        logger.info("Processing alert", alert_type=data.get("type"))
        
        # Route to alert management service
        return {
            "alert_processed": True,
            "data": data
        }