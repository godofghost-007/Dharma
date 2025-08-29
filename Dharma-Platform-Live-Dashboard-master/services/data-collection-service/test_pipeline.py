#!/usr/bin/env python3
"""
Test script for data ingestion pipeline
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from app.core.data_pipeline import DataIngestionPipeline, get_pipeline
from app.core.batch_processor import BatchProcessor, get_batch_processor
from app.core.monitoring import DataCollectionMonitor, get_monitor
from shared.models.post import Platform


async def test_streaming_pipeline():
    """Test streaming data processing"""
    print("Testing streaming data pipeline...")
    
    pipeline = await get_pipeline()
    
    # Sample Twitter data
    sample_data = {
        "post_id": "1234567890",
        "user_id": "user123",
        "content": "This is a test tweet about India #test",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "likes": 10,
            "shares": 5,
            "comments": 2
        }
    }
    
    # Process the data
    success = await pipeline.process_streaming_data(
        Platform.TWITTER, 
        sample_data, 
        "test_collection_001"
    )
    
    print(f"Streaming processing result: {success}")
    
    # Check processing status
    status = await pipeline.get_processing_status("test_collection_001")
    print(f"Processing status: {status}")


async def test_batch_processing():
    """Test batch data processing"""
    print("Testing batch data processing...")
    
    batch_processor = await get_batch_processor()
    
    # Sample batch data
    batch_data = [
        {
            "post_id": f"batch_{i}",
            "user_id": f"user_{i}",
            "content": f"Batch test post {i} about India",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {"likes": i, "shares": i//2, "comments": i//3}
        }
        for i in range(1, 11)
    ]
    
    # Create a temporary file for testing
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(batch_data, f)
        temp_file = f.name
    
    try:
        # Submit batch job
        job_id = await batch_processor.submit_batch_job(
            Platform.TWITTER,
            f"file://{temp_file}",
            "test_batch_collection_001"
        )
        
        print(f"Batch job submitted: {job_id}")
        
        # Wait a bit and check status
        await asyncio.sleep(2)
        
        job_status = await batch_processor.get_job_status(job_id)
        if job_status:
            print(f"Job status: {job_status.status}")
            print(f"Metrics: {job_status.metrics}")
        
    finally:
        # Clean up temp file
        os.unlink(temp_file)


async def test_monitoring():
    """Test monitoring system"""
    print("Testing monitoring system...")
    
    monitor = await get_monitor()
    
    # Record some test metrics
    await monitor.record_collection_event(Platform.TWITTER, "test_event", True, 1.5)
    await monitor.record_processing_metrics(Platform.TWITTER, 10, 1, 2)
    await monitor.record_kafka_metrics("test_topic", True, 0.1)
    
    # Get system health
    health = await monitor.get_system_health()
    print(f"System health: {health}")
    
    # Get metrics
    from datetime import timedelta
    metrics = await monitor.metrics_collector.get_metrics(
        start_time=datetime.utcnow() - timedelta(minutes=5)
    )
    print(f"Recent metrics count: {len(metrics)}")
    
    # Get active alerts
    alerts = await monitor.alert_manager.get_active_alerts()
    print(f"Active alerts: {len(alerts)}")


async def test_data_validation():
    """Test data validation"""
    print("Testing data validation...")
    
    pipeline = await get_pipeline()
    
    # Test valid data
    valid_data = {
        "post_id": "valid_123",
        "user_id": "user_valid",
        "content": "Valid test content",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        validated = await pipeline.validator.validate_post_data(Platform.TWITTER, valid_data)
        print("Valid data passed validation ✓")
    except Exception as e:
        print(f"Valid data failed validation: {e}")
    
    # Test invalid data
    invalid_data = {
        "post_id": "",  # Empty post_id should fail
        "content": "Invalid test content"
        # Missing required fields
    }
    
    try:
        validated = await pipeline.validator.validate_post_data(Platform.TWITTER, invalid_data)
        print("Invalid data unexpectedly passed validation ✗")
    except Exception as e:
        print("Invalid data correctly failed validation ✓")


async def main():
    """Run all tests"""
    print("Starting data ingestion pipeline tests...\n")
    
    try:
        await test_data_validation()
        print()
        
        await test_streaming_pipeline()
        print()
        
        await test_batch_processing()
        print()
        
        await test_monitoring()
        print()
        
        print("All tests completed!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            pipeline = await get_pipeline()
            monitor = await get_monitor()
            batch_processor = await get_batch_processor()
            
            await pipeline.cleanup()
            await monitor.cleanup()
            await batch_processor.cleanup()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())