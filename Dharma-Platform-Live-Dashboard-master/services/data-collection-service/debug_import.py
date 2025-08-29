#!/usr/bin/env python3
import sys
import traceback

# Add project root to path
sys.path.insert(0, '../..')

try:
    print("Testing imports...")
    
    # Test shared models
    from shared.models.post import Platform
    print("✓ Platform import OK")
    
    # Test config
    from app.core.config import get_settings
    print("✓ Config import OK")
    
    # Test kafka producer
    from app.core.kafka_producer import KafkaDataProducer
    print("✓ KafkaDataProducer import OK")
    
    # Test database managers
    from shared.database.mongodb import MongoDBManager
    print("✓ MongoDBManager import OK")
    
    from shared.database.redis import RedisManager
    print("✓ RedisManager import OK")
    
    # Test data pipeline
    print("Importing data pipeline...")
    import app.core.data_pipeline as dp
    print(f"Module contents: {dir(dp)}")
    
    # Try to execute the module manually to see what happens
    print("Executing data_pipeline.py manually...")
    with open('app/core/data_pipeline.py', 'r') as f:
        code = f.read()
    
    # Execute in a new namespace
    namespace = {}
    try:
        exec(code, namespace)
        print(f"Executed namespace contents: {[k for k in namespace.keys() if not k.startswith('__')]}")
    except Exception as e:
        print(f"Error during execution: {e}")
        traceback.print_exc()
    
    # Try to import the class directly
    from app.core.data_pipeline import DataIngestionPipeline
    print("✓ DataIngestionPipeline import OK")
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()