#!/usr/bin/env python3
"""Database migration CLI tool for Project Dharma."""

import asyncio
import argparse
import sys
from pathlib import Path
import json
from typing import Optional, List

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.migrations import DatabaseMigrationManager
from shared.database.mongodb import MongoDBManager
from shared.database.postgresql import PostgreSQLManager
from shared.config.settings import get_settings
import structlog

logger = structlog.get_logger(__name__)


async def create_database_managers():
    """Create database manager instances."""
    settings = get_settings()
    
    # MongoDB manager
    mongodb_manager = MongoDBManager(
        connection_string=settings.MONGODB_URL,
        database_name=settings.MONGODB_DATABASE
    )
    await mongodb_manager.connect()
    
    # PostgreSQL manager
    postgresql_manager = PostgreSQLManager(
        connection_string=settings.POSTGRESQL_URL
    )
    await postgresql_manager.connect()
    
    # Elasticsearch client (if available)
    elasticsearch_client = None
    try:
        from elasticsearch import AsyncElasticsearch
        elasticsearch_client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
    except ImportError:
        logger.warning("Elasticsearch client not available")
    
    return mongodb_manager, postgresql_manager, elasticsearch_client


async def run_migrations(target_version: str = "latest", database_types: Optional[List[str]] = None):
    """Run database migrations."""
    try:
        mongodb_manager, postgresql_manager, elasticsearch_client = await create_database_managers()
        
        migration_manager = DatabaseMigrationManager(
            mongodb_manager=mongodb_manager,
            postgresql_manager=postgresql_manager,
            elasticsearch_client=elasticsearch_client
        )
        
        print(f"Running migrations to version: {target_version}")
        if database_types:
            print(f"Database types: {', '.join(database_types)}")
        
        results = await migration_manager.run_migrations(target_version, database_types)
        
        print("\nMigration Results:")
        print("=" * 50)
        
        for db_type, result in results.items():
            print(f"\n{db_type.upper()}:")
            print(f"  Status: {result['status']}")
            
            if result['status'] == 'success':
                print(f"  Current Version: {result.get('current_version', 'N/A')}")
                print(f"  Target Version: {result.get('target_version', 'N/A')}")
                
                migrations_applied = result.get('migrations_applied', [])
                if migrations_applied:
                    print(f"  Migrations Applied: {', '.join(migrations_applied)}")
                else:
                    print("  No migrations applied (already up to date)")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        # Cleanup
        await mongodb_manager.disconnect()
        await postgresql_manager.disconnect()
        if elasticsearch_client:
            await elasticsearch_client.close()
        
        return all(r['status'] == 'success' for r in results.values())
        
    except Exception as e:
        logger.error("Migration failed", error=str(e))
        print(f"Migration failed: {e}")
        return False


async def rollback_migrations(target_version: str, database_types: Optional[List[str]] = None):
    """Rollback database migrations."""
    try:
        mongodb_manager, postgresql_manager, elasticsearch_client = await create_database_managers()
        
        migration_manager = DatabaseMigrationManager(
            mongodb_manager=mongodb_manager,
            postgresql_manager=postgresql_manager,
            elasticsearch_client=elasticsearch_client
        )
        
        print(f"Rolling back to version: {target_version}")
        if database_types:
            print(f"Database types: {', '.join(database_types)}")
        
        results = await migration_manager.rollback_to_version(target_version, database_types)
        
        print("\nRollback Results:")
        print("=" * 50)
        
        for db_type, result in results.items():
            print(f"\n{db_type.upper()}:")
            print(f"  Status: {result['status']}")
            
            if result['status'] == 'success':
                print(f"  Current Version: {result.get('current_version', 'N/A')}")
                print(f"  Target Version: {result.get('target_version', 'N/A')}")
                
                migrations_rolled_back = result.get('migrations_rolled_back', [])
                if migrations_rolled_back:
                    print(f"  Migrations Rolled Back: {', '.join(migrations_rolled_back)}")
                else:
                    print("  No migrations rolled back")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        # Cleanup
        await mongodb_manager.disconnect()
        await postgresql_manager.disconnect()
        if elasticsearch_client:
            await elasticsearch_client.close()
        
        return all(r['status'] == 'success' for r in results.values())
        
    except Exception as e:
        logger.error("Rollback failed", error=str(e))
        print(f"Rollback failed: {e}")
        return False


async def show_migration_status(database_types: Optional[List[str]] = None):
    """Show current migration status."""
    try:
        mongodb_manager, postgresql_manager, elasticsearch_client = await create_database_managers()
        
        migration_manager = DatabaseMigrationManager(
            mongodb_manager=mongodb_manager,
            postgresql_manager=postgresql_manager,
            elasticsearch_client=elasticsearch_client
        )
        
        status = await migration_manager.get_migration_status()
        
        print("Migration Status:")
        print("=" * 50)
        
        for db_type, db_status in status.items():
            if database_types and db_type not in database_types:
                continue
                
            print(f"\n{db_type.upper()}:")
            
            if 'error' in db_status:
                print(f"  Error: {db_status['error']}")
            else:
                print(f"  Current Version: {db_status['current_version']}")
                print(f"  Latest Version: {db_status['latest_version']}")
                print(f"  Pending Migrations: {db_status['pending_migrations']}")
                print(f"  Up to Date: {'Yes' if db_status['up_to_date'] else 'No'}")
        
        # Cleanup
        await mongodb_manager.disconnect()
        await postgresql_manager.disconnect()
        if elasticsearch_client:
            await elasticsearch_client.close()
        
    except Exception as e:
        logger.error("Status check failed", error=str(e))
        print(f"Status check failed: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Database migration tool for Project Dharma")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run database migrations')
    migrate_parser.add_argument(
        '--version', 
        default='latest', 
        help='Target version (default: latest)'
    )
    migrate_parser.add_argument(
        '--databases', 
        nargs='+', 
        choices=['mongodb', 'postgresql', 'elasticsearch'],
        help='Specific databases to migrate (default: all)'
    )
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback database migrations')
    rollback_parser.add_argument(
        'version', 
        help='Target version to rollback to'
    )
    rollback_parser.add_argument(
        '--databases', 
        nargs='+', 
        choices=['mongodb', 'postgresql', 'elasticsearch'],
        help='Specific databases to rollback (default: all)'
    )
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')
    status_parser.add_argument(
        '--databases', 
        nargs='+', 
        choices=['mongodb', 'postgresql', 'elasticsearch'],
        help='Specific databases to check (default: all)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Run the appropriate command
    if args.command == 'migrate':
        success = asyncio.run(run_migrations(args.version, args.databases))
        sys.exit(0 if success else 1)
    
    elif args.command == 'rollback':
        success = asyncio.run(rollback_migrations(args.version, args.databases))
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        asyncio.run(show_migration_status(args.databases))


if __name__ == '__main__':
    main()