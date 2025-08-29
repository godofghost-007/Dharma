#!/usr/bin/env python3
"""
Minimal test of data pipeline classes
"""
import sys
sys.path.insert(0, '../..')

print("Testing minimal pipeline...")

# Test basic imports first
try:
    from datetime import datetime
    print("✓ datetime import OK")
    
    from typing import Dict, Any, List
    print("✓ typing import OK")
    
    from enum import Enum
    print("✓ enum import OK")
    
    from dataclasses import dataclass
    print("✓ dataclasses import OK")
    
    import structlog
    print("✓ structlog import OK")
    
    from pydantic import ValidationError
    print("✓ pydantic ValidationError import OK")
    
    from shared.models.post import Platform
    print("✓ Platform import OK")
    
    # Now test the problematic imports
    from app.core.kafka_producer import KafkaDataProducer
    print("✓ KafkaDataProducer import OK")
    
    from app.core.config import get_settings
    print("✓ get_settings import OK")
    
    from shared.database.mongodb import MongoDBManager
    print("✓ MongoDBManager import OK")
    
    from shared.database.redis import RedisManager
    print("✓ RedisManager import OK")
    
    print("All imports successful! Now testing class definition...")
    
    # Define a minimal version of the class
    class TestDataIngestionPipeline:
        """Test version of DataIngestionPipeline"""
        
        def __init__(self):
            print("TestDataIngestionPipeline initialized")
    
    # Test instantiation
    pipeline = TestDataIngestionPipeline()
    print("✓ Test pipeline created successfully")
    
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()