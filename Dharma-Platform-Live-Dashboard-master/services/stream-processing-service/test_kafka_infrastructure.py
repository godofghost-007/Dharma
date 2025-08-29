"""
Test Kafka streaming infrastructure
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.core.kafka_config import KafkaStreamConfig, KafkaTopicManager
from app.core.stream_processor import StreamProcessor, StreamTopology
from app.core.kafka_clients import EnhancedKafkaProducer, EnhancedKafkaConsumer, KafkaHealthChecker


class TestKafkaStreamConfig:
    """Test Kafka stream configuration"""
    
    def test_kafka_config_initialization(self):
        """Test Kafka configuration initialization"""
        config = KafkaStreamConfig()
        
        assert config.bootstrap_servers == "localhost:29092"
        assert config.topic_prefix == "dharma"
        assert config.num_partitions == 3
        assert config.replication_factor == 1
        
        # Test producer config
        producer_config = config.producer_config
        assert producer_config["bootstrap_servers"] == "localhost:29092"
        assert producer_config["acks"] == "all"
        assert producer_config["retries"] == 3
        
        # Test consumer config
        consumer_config = config.consumer_config
        assert consumer_config["bootstrap_servers"] == "localhost:29092"
        assert consumer_config["group_id"] == "dharma-stream-processors"
        assert consumer_config["auto_offset_reset"] == "earliest"


class TestKafkaTopicManager:
    """Test Kafka topic management"""
    
    def test_topic_manager_initialization(self):
        """Test topic manager initialization"""
        config = KafkaStreamConfig()
        
        with patch('app.core.kafka_config.KafkaAdminClient') as mock_admin:
            topic_manager = KafkaTopicManager(config)
        
        # Check that all required topics are defined
        expected_topics = [
            "raw_twitter", "raw_youtube", "raw_web", "raw_telegram",
            "sentiment_analysis", "bot_detection", "campaign_detection",
            "analysis_results", "alerts", "campaigns",
            "dead_letter_queue", "retry_queue"
        ]
        
        for topic in expected_topics:
            assert topic in topic_manager.topics
            assert topic_manager.topics[topic].startswith("dharma.")
    
    def test_partition_configuration(self):
        """Test partition configuration for different topic types"""
        config = KafkaStreamConfig()
        
        with patch('app.core.kafka_config.KafkaAdminClient') as mock_admin:
            topic_manager = KafkaTopicManager(config)
        
        # High throughput topics should have more partitions
        high_throughput_partitions = topic_manager._get_partitions_for_topic("raw_twitter")
        normal_partitions = topic_manager._get_partitions_for_topic("alerts")
        
        assert high_throughput_partitions > normal_partitions
        assert high_throughput_partitions == config.num_partitions * 2
        assert normal_partitions == config.num_partitions
    
    def test_topic_configuration(self):
        """Test topic-specific configuration"""
        config = KafkaStreamConfig()
        
        with patch('app.core.kafka_config.KafkaAdminClient') as mock_admin:
            topic_manager = KafkaTopicManager(config)
        
        # Test raw data topic config
        raw_config = topic_manager._get_topic_config("raw_twitter")
        assert raw_config["retention.ms"] == "259200000"  # 3 days
        
        # Test DLQ config
        dlq_config = topic_manager._get_topic_config("dead_letter_queue")
        assert dlq_config["retention.ms"] == "2592000000"  # 30 days
        
        # Test default config
        default_config = topic_manager._get_topic_config("analysis_results")
        assert default_config["retention.ms"] == "604800000"  # 7 days


class TestStreamProcessor:
    """Test stream processor functionality"""
    
    @pytest.fixture
    def mock_kafka_config(self):
        """Mock Kafka configuration"""
        config = Mock(spec=KafkaStreamConfig)
        config.bootstrap_servers = "localhost:29092"
        config.consumer_group_id = "test-group"
        config.producer_config = {"bootstrap_servers": "localhost:29092"}
        config.consumer_config = {"bootstrap_servers": "localhost:29092", "group_id": "test-group"}
        return config
    
    @pytest.fixture
    def mock_topic_manager(self):
        """Mock topic manager"""
        topic_manager = Mock(spec=KafkaTopicManager)
        topic_manager.topics = {
            "raw_twitter": "dharma.raw.twitter",
            "sentiment_analysis": "dharma.analysis.sentiment",
            "analysis_results": "dharma.results.analysis",
            "dead_letter_queue": "dharma.errors.dlq"
        }
        topic_manager.create_topics = AsyncMock(return_value=True)
        return topic_manager
    
    @pytest.mark.asyncio
    async def test_stream_processor_initialization(self, mock_kafka_config):
        """Test stream processor initialization"""
        with patch('app.core.stream_processor.KafkaTopicManager') as mock_tm_class:
            mock_tm_class.return_value = Mock()
            mock_tm_class.return_value.create_topics = AsyncMock(return_value=True)
            
            processor = StreamProcessor(mock_kafka_config)
            
            # Mock Kafka clients to avoid actual connections
            with patch.object(processor, '_initialize_kafka_clients'):
                await processor.initialize()
            
            assert processor.config == mock_kafka_config
            assert processor.processing_handlers == {}
            assert not processor.running
    
    @pytest.mark.asyncio
    async def test_handler_registration(self, mock_kafka_config):
        """Test handler registration"""
        with patch('app.core.kafka_config.KafkaAdminClient') as mock_admin:
            processor = StreamProcessor(mock_kafka_config)
        
        async def test_handler(data, context):
            return {"processed": True}
        
        processor.register_handler("test_topic", test_handler)
        
        assert "test_topic" in processor.processing_handlers
        assert processor.processing_handlers["test_topic"] == test_handler
    
    @pytest.mark.asyncio
    async def test_message_processing(self, mock_kafka_config, mock_topic_manager):
        """Test message processing logic"""
        with patch('app.core.kafka_config.KafkaAdminClient') as mock_admin:
            processor = StreamProcessor(mock_kafka_config)
        processor.topic_manager = mock_topic_manager
        
        # Mock producer
        processor.producer = Mock()
        processor.producer.send = Mock()
        
        # Register test handler
        async def test_handler(data, context):
            return {"result": "processed", "input": data}
        
        processor.register_handler("dharma.raw.twitter", test_handler)
        
        # Create mock message
        mock_message = Mock()
        mock_message.topic = "dharma.raw.twitter"
        mock_message.partition = 0
        mock_message.offset = 123
        mock_message.value = {"content": "test message"}
        
        # Process message
        await processor._process_message(mock_message)
        
        # Verify handler was called and result was routed
        # (This would require more detailed mocking of the routing logic)


class TestStreamTopology:
    """Test stream topology building"""
    
    @pytest.fixture
    def mock_stream_processor(self):
        """Mock stream processor"""
        processor = Mock(spec=StreamProcessor)
        processor.topic_manager = Mock()
        processor.topic_manager.topics = {
            "raw_twitter": "dharma.raw.twitter",
            "raw_youtube": "dharma.raw.youtube",
            "raw_web": "dharma.raw.web",
            "raw_telegram": "dharma.raw.telegram",
            "sentiment_analysis": "dharma.analysis.sentiment",
            "bot_detection": "dharma.analysis.bot_detection",
            "campaign_detection": "dharma.analysis.campaign_detection",
            "analysis_results": "dharma.results.analysis",
            "alerts": "dharma.results.alerts"
        }
        processor.register_handler = Mock()
        return processor
    
    def test_topology_building(self, mock_stream_processor):
        """Test stream topology building"""
        topology = StreamTopology(mock_stream_processor)
        topology.build_topology()
        
        # Verify handlers were registered for all topic types
        expected_calls = len(mock_stream_processor.topic_manager.topics)
        assert mock_stream_processor.register_handler.call_count >= 8  # At least 8 handlers
    
    @pytest.mark.asyncio
    async def test_data_preprocessing(self, mock_stream_processor):
        """Test data preprocessing handlers"""
        topology = StreamTopology(mock_stream_processor)
        
        # Test Twitter data preprocessing
        twitter_data = {
            "id": "123456789",
            "text": "Test tweet content",
            "user_id": "user123",
            "created_at": "2024-01-01T12:00:00Z",
            "public_metrics": {
                "like_count": 10,
                "retweet_count": 5,
                "reply_count": 2
            }
        }
        
        result = await topology._preprocess_twitter_data(twitter_data, {})
        
        assert result["platform"] == "twitter"
        assert result["content"] == "Test tweet content"
        assert result["post_id"] == "123456789"
        assert result["user_id"] == "user123"
        assert result["metrics"]["likes"] == 10
        assert result["metrics"]["retweets"] == 5
        assert result["metrics"]["replies"] == 2
    
    @pytest.mark.asyncio
    async def test_youtube_preprocessing(self, mock_stream_processor):
        """Test YouTube data preprocessing"""
        topology = StreamTopology(mock_stream_processor)
        
        youtube_data = {
            "id": "comment123",
            "snippet": {
                "textDisplay": "Great video!",
                "authorChannelId": {"value": "channel123"},
                "publishedAt": "2024-01-01T12:00:00Z",
                "likeCount": 5
            }
        }
        
        result = await topology._preprocess_youtube_data(youtube_data, {})
        
        assert result["platform"] == "youtube"
        assert result["content"] == "Great video!"
        assert result["post_id"] == "comment123"
        assert result["user_id"] == "channel123"
        assert result["metrics"]["likes"] == 5


class TestEnhancedKafkaClients:
    """Test enhanced Kafka clients"""
    
    @pytest.fixture
    def mock_kafka_config(self):
        """Mock Kafka configuration"""
        config = Mock(spec=KafkaStreamConfig)
        config.producer_config = {"bootstrap_servers": "localhost:29092"}
        config.consumer_config = {"bootstrap_servers": "localhost:29092", "group_id": "test"}
        return config
    
    def test_enhanced_producer_initialization(self, mock_kafka_config):
        """Test enhanced producer initialization"""
        with patch('app.core.kafka_clients.KafkaProducer') as mock_producer_class:
            producer = EnhancedKafkaProducer(mock_kafka_config)
            
            assert producer.config == mock_kafka_config
            assert producer.metrics["messages_sent"] == 0
            assert producer.metrics["messages_failed"] == 0
            mock_producer_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enhanced_producer_send_message(self, mock_kafka_config):
        """Test enhanced producer message sending"""
        with patch('app.core.kafka_clients.KafkaProducer') as mock_producer_class:
            mock_producer = Mock()
            mock_future = Mock()
            mock_metadata = Mock()
            mock_metadata.partition = 0
            mock_metadata.offset = 123
            mock_future.get.return_value = mock_metadata
            mock_producer.send.return_value = mock_future
            mock_producer_class.return_value = mock_producer
            
            producer = EnhancedKafkaProducer(mock_kafka_config)
            
            result = await producer.send_message("test_topic", {"test": "data"})
            
            assert result is True
            assert producer.metrics["messages_sent"] == 1
            mock_producer.send.assert_called_once()
    
    def test_enhanced_consumer_initialization(self, mock_kafka_config):
        """Test enhanced consumer initialization"""
        topics = ["topic1", "topic2"]
        
        with patch('app.core.kafka_clients.KafkaConsumer') as mock_consumer_class:
            consumer = EnhancedKafkaConsumer(mock_kafka_config, topics)
            
            assert consumer.config == mock_kafka_config
            assert consumer.topics == topics
            assert consumer.metrics["messages_consumed"] == 0
            mock_consumer_class.assert_called_once()


class TestKafkaHealthChecker:
    """Test Kafka health checker"""
    
    @pytest.fixture
    def mock_kafka_config(self):
        """Mock Kafka configuration"""
        config = Mock(spec=KafkaStreamConfig)
        config.bootstrap_servers = "localhost:29092"
        config.topic_prefix = "dharma"
        return config
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_kafka_config):
        """Test successful health check"""
        with patch('app.core.kafka_clients.KafkaProducer') as mock_producer_class, \
             patch('app.core.kafka_clients.KafkaConsumer') as mock_consumer_class:
            
            # Mock successful producer
            mock_producer = Mock()
            mock_future = Mock()
            mock_future.get.return_value = Mock()
            mock_producer.send.return_value = mock_future
            mock_producer_class.return_value = mock_producer
            
            # Mock successful consumer
            mock_consumer = Mock()
            mock_consumer_class.return_value = mock_consumer
            
            health_checker = KafkaHealthChecker(mock_kafka_config)
            result = await health_checker.check_kafka_health()
            
            assert result["kafka_available"] is True
            assert result["producer_working"] is True
            assert result["consumer_working"] is True
            assert result["topics_accessible"] is True
            assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_kafka_config):
        """Test health check failure"""
        with patch('app.core.kafka_clients.KafkaProducer') as mock_producer_class:
            mock_producer_class.side_effect = Exception("Connection failed")
            
            health_checker = KafkaHealthChecker(mock_kafka_config)
            result = await health_checker.check_kafka_health()
            
            assert result["kafka_available"] is False
            assert result["producer_working"] is False
            assert result["consumer_working"] is False
            assert result["topics_accessible"] is False
            assert "Connection failed" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])