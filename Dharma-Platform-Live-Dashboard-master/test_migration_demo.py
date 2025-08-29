#!/usr/bin/env python3
"""Demo script to test the database migration system."""

import asyncio
import json
from shared.database.migrations import DatabaseMigrationManager, MongoMigrator, Migration
from shared.database.mongodb import MongoDBManager

async def demo_migration_system():
    """Demonstrate the migration system functionality."""
    print("=== Database Migration System Demo ===\n")
    
    # Create a mock MongoDB manager for testing
    class MockMongoDBManager:
        def __init__(self):
            self.database = MockDatabase()
    
    class MockDatabase:
        def __init__(self):
            self.schema_migrations = MockCollection()
            self.posts = MockCollection()
            self.campaigns = MockCollection()
    
    class MockCollection:
        def __init__(self):
            self.data = []
        
        async def find_one(self, query=None, sort=None):
            if not self.data:
                return None
            return self.data[-1] if sort else self.data[0]
        
        async def insert_one(self, document):
            self.data.append(document)
            return type('Result', (), {'inserted_id': 'mock_id'})()
        
        async def create_index(self, index_spec, **options):
            print(f"  Created index: {index_spec} with options: {options}")
        
        async def update_many(self, filter_query, update_query):
            print(f"  Updated documents: filter={filter_query}, update={update_query}")
            return type('Result', (), {'modified_count': 1})()
    
    # Create mock migration manager
    mongodb_manager = MockMongoDBManager()
    migration_manager = DatabaseMigrationManager(mongodb_manager=mongodb_manager)
    
    print("1. Testing MongoDB Migrator")
    mongo_migrator = migration_manager.migrators["mongodb"]
    
    # Test getting current version
    current_version = await mongo_migrator.get_current_version()
    print(f"   Current version: {current_version}")
    
    # Test creating a migration
    test_migration = Migration(
        version="1.0.0",
        name="test_migration",
        description="Test migration for demo",
        database_type="mongodb",
        migration_type="schema"
    )
    
    # Test recording migration
    await mongo_migrator.record_migration(test_migration)
    print(f"   Recorded migration: {test_migration.name}")
    
    # Test version comparison
    print(f"   Version comparison (1.0.0 vs 0.9.0): {mongo_migrator.compare_versions('1.0.0', '0.9.0')}")
    print(f"   Version comparison (1.0.0 vs 1.1.0): {mongo_migrator.compare_versions('1.0.0', '1.1.0')}")
    
    print("\n2. Testing Migration File Loading")
    
    # Test loading actual migration files
    try:
        migrations = await mongo_migrator.load_migrations()
        print(f"   Found {len(migrations)} migration files")
        
        for migration in migrations:
            print(f"   - {migration.version}: {migration.name}")
    except Exception as e:
        print(f"   Error loading migrations: {e}")
    
    print("\n3. Testing Migration Status")
    
    # Test getting migration status
    try:
        status = await migration_manager.get_migration_status()
        print("   Migration Status:")
        for db_type, db_status in status.items():
            print(f"   - {db_type}: {db_status}")
    except Exception as e:
        print(f"   Error getting status: {e}")
    
    print("\n4. Testing Migration Operations")
    
    # Test MongoDB operations
    test_operations = [
        {
            "type": "create_index",
            "collection": "posts",
            "index": [["platform", 1], ["timestamp", -1]],
            "options": {"name": "platform_timestamp_idx"}
        },
        {
            "type": "add_field",
            "collection": "posts",
            "field": "new_field",
            "default_value": "default",
            "filter": {}
        }
    ]
    
    print("   Executing test operations:")
    for operation in test_operations:
        try:
            await mongo_migrator._execute_operation(operation)
            print(f"   ✓ Executed: {operation['type']}")
        except Exception as e:
            print(f"   ✗ Failed: {operation['type']} - {e}")
    
    print("\n=== Demo Complete ===")
    print("\nThe database migration system includes:")
    print("- MongoDB migration support with schema validation")
    print("- PostgreSQL migration support with SQL files")
    print("- Elasticsearch index migration support")
    print("- Version management and rollback capabilities")
    print("- CLI tool for running migrations")
    print("- Comprehensive error handling and logging")

if __name__ == "__main__":
    asyncio.run(demo_migration_system())