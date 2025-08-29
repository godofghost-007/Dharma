"""Database migration system with versioning support."""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import structlog
from dataclasses import dataclass

from .mongodb import MongoDBManager
from .redis import RedisManager

try:
    from .postgresql import PostgreSQLManager
except ImportError:
    PostgreSQLManager = None

logger = structlog.get_logger(__name__)


@dataclass
class Migration:
    """Represents a database migration."""
    version: str
    name: str
    description: str
    database_type: str
    migration_type: str
    file_path: Optional[str] = None
    rollback_path: Optional[str] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class MigrationError(Exception):
    """Exception raised when migration fails."""
    pass


class BaseMigrator(ABC):
    """Base class for database migrators."""
    
    def __init__(self, database_manager):
        self.db_manager = database_manager
        self.migrations_dir = Path("migrations")
        self.applied_migrations: List[str] = []
    
    @abstractmethod
    async def get_current_version(self) -> str:
        """Get current database schema version."""
        pass
    
    @abstractmethod
    async def record_migration(self, migration: Migration) -> None:
        """Record applied migration in database."""
        pass
    
    @abstractmethod
    async def execute_migration(self, migration: Migration) -> None:
        """Execute a single migration."""
        pass
    
    @abstractmethod
    async def rollback_migration(self, migration: Migration) -> None:
        """Rollback a migration."""
        pass
    
    async def get_pending_migrations(self, current_version: str, target_version: str) -> List[Migration]:
        """Get list of pending migrations between versions."""
        all_migrations = await self.load_migrations()
        
        # Filter migrations based on version range
        pending = []
        for migration in all_migrations:
            if (self.compare_versions(migration.version, current_version) > 0 and
                self.compare_versions(migration.version, target_version) <= 0):
                pending.append(migration)
        
        # Sort by version
        pending.sort(key=lambda m: m.version)
        return pending
    
    async def load_migrations(self) -> List[Migration]:
        """Load all available migrations from files."""
        migrations = []
        migration_files = list(self.migrations_dir.glob(f"{self.db_type}/*.json"))
        
        for file_path in sorted(migration_files):
            with open(file_path, 'r') as f:
                migration_data = json.load(f)
                migration = Migration(**migration_data, file_path=str(file_path))
                migrations.append(migration)
        
        return migrations
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Pad shorter version with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        return 0


class MongoMigrator(BaseMigrator):
    """MongoDB migration manager."""
    
    def __init__(self, mongodb_manager: MongoDBManager):
        super().__init__(mongodb_manager)
        self.db_type = "mongodb"
    
    async def get_current_version(self) -> str:
        """Get current MongoDB schema version."""
        if not self.db_manager.database:
            raise RuntimeError("Database not connected")
        
        version_doc = await self.db_manager.database.schema_migrations.find_one(
            {}, sort=[("version", -1)]
        )
        return version_doc["version"] if version_doc else "0.0.0"
    
    async def record_migration(self, migration: Migration) -> None:
        """Record applied migration in MongoDB."""
        if not self.db_manager.database:
            raise RuntimeError("Database not connected")
        
        migration_record = {
            "version": migration.version,
            "name": migration.name,
            "description": migration.description,
            "migration_type": migration.migration_type,
            "applied_at": datetime.utcnow(),
            "checksum": self._calculate_checksum(migration)
        }
        
        await self.db_manager.database.schema_migrations.insert_one(migration_record)
        logger.info("Recorded MongoDB migration", version=migration.version)
    
    async def execute_migration(self, migration: Migration) -> None:
        """Execute MongoDB migration."""
        if not self.db_manager.database:
            raise RuntimeError("Database not connected")
        
        logger.info("Executing MongoDB migration", version=migration.version, name=migration.name)
        
        if migration.file_path:
            # Load migration from file
            with open(migration.file_path, 'r') as f:
                migration_data = json.load(f)
                operations = migration_data.get("operations", [])
        else:
            operations = []
        
        for operation in operations:
            await self._execute_operation(operation)
    
    async def _execute_operation(self, operation: Dict[str, Any]) -> None:
        """Execute a single MongoDB operation."""
        op_type = operation["type"]
        collection_name = operation["collection"]
        collection = self.db_manager.database[collection_name]
        
        if op_type == "create_collection":
            await self.db_manager.database.create_collection(
                collection_name, 
                **operation.get("options", {})
            )
        
        elif op_type == "create_index":
            index_spec = operation["index"]
            options = operation.get("options", {})
            await collection.create_index(index_spec, **options)
        
        elif op_type == "drop_index":
            index_name = operation["index_name"]
            await collection.drop_index(index_name)
        
        elif op_type == "add_field":
            filter_query = operation.get("filter", {})
            field_name = operation["field"]
            default_value = operation["default_value"]
            
            await collection.update_many(
                {**filter_query, field_name: {"$exists": False}},
                {"$set": {field_name: default_value}}
            )
        
        elif op_type == "remove_field":
            filter_query = operation.get("filter", {})
            field_name = operation["field"]
            
            await collection.update_many(
                filter_query,
                {"$unset": {field_name: ""}}
            )
        
        elif op_type == "rename_field":
            filter_query = operation.get("filter", {})
            old_field = operation["old_field"]
            new_field = operation["new_field"]
            
            await collection.update_many(
                filter_query,
                {"$rename": {old_field: new_field}}
            )
        
        elif op_type == "update_documents":
            filter_query = operation["filter"]
            update_query = operation["update"]
            
            await collection.update_many(filter_query, update_query)
        
        else:
            raise MigrationError(f"Unknown MongoDB operation type: {op_type}")
    
    async def rollback_migration(self, migration: Migration) -> None:
        """Rollback MongoDB migration."""
        if migration.rollback_path and os.path.exists(migration.rollback_path):
            with open(migration.rollback_path, 'r') as f:
                rollback_data = json.load(f)
                operations = rollback_data.get("operations", [])
            
            for operation in operations:
                await self._execute_operation(operation)
        
        # Remove migration record
        if self.db_manager.database:
            await self.db_manager.database.schema_migrations.delete_one(
                {"version": migration.version}
            )
    
    def _calculate_checksum(self, migration: Migration) -> str:
        """Calculate checksum for migration integrity."""
        import hashlib
        content = f"{migration.version}{migration.name}{migration.description}"
        return hashlib.md5(content.encode()).hexdigest()


class PostgreSQLMigrator(BaseMigrator):
    """PostgreSQL migration manager using Flyway-like approach."""
    
    def __init__(self, postgresql_manager: PostgreSQLManager):
        super().__init__(postgresql_manager)
        self.db_type = "postgresql"
    
    async def ensure_migrations_table(self) -> None:
        """Ensure schema_migrations table exists."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            migration_type VARCHAR(50) NOT NULL,
            checksum VARCHAR(32) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            execution_time_ms INTEGER
        );
        """
        await self.db_manager.execute(create_table_sql)
    
    async def get_current_version(self) -> str:
        """Get current PostgreSQL schema version."""
        await self.ensure_migrations_table()
        
        result = await self.db_manager.fetchval(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        )
        return result if result else "0.0.0"
    
    async def record_migration(self, migration: Migration) -> None:
        """Record applied migration in PostgreSQL."""
        await self.ensure_migrations_table()
        
        await self.db_manager.execute(
            """
            INSERT INTO schema_migrations (version, name, description, migration_type, checksum)
            VALUES ($1, $2, $3, $4, $5)
            """,
            migration.version,
            migration.name,
            migration.description,
            migration.migration_type,
            self._calculate_checksum(migration)
        )
        logger.info("Recorded PostgreSQL migration", version=migration.version)
    
    async def execute_migration(self, migration: Migration) -> None:
        """Execute PostgreSQL migration."""
        logger.info("Executing PostgreSQL migration", version=migration.version, name=migration.name)
        
        if migration.file_path:
            # Execute SQL file
            sql_file_path = migration.file_path.replace('.json', '.sql')
            if os.path.exists(sql_file_path):
                with open(sql_file_path, 'r') as f:
                    sql_content = f.read()
                
                # Split by semicolon and execute each statement
                statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                
                async with self.db_manager.pool.acquire() as conn:
                    async with conn.transaction():
                        for statement in statements:
                            await conn.execute(statement)
    
    async def rollback_migration(self, migration: Migration) -> None:
        """Rollback PostgreSQL migration."""
        if migration.rollback_path and os.path.exists(migration.rollback_path):
            with open(migration.rollback_path, 'r') as f:
                sql_content = f.read()
            
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            async with self.db_manager.pool.acquire() as conn:
                async with conn.transaction():
                    for statement in statements:
                        await conn.execute(statement)
        
        # Remove migration record
        await self.db_manager.execute(
            "DELETE FROM schema_migrations WHERE version = $1",
            migration.version
        )
    
    def _calculate_checksum(self, migration: Migration) -> str:
        """Calculate checksum for migration integrity."""
        import hashlib
        content = f"{migration.version}{migration.name}{migration.description}"
        return hashlib.md5(content.encode()).hexdigest()


class ElasticsearchMigrator(BaseMigrator):
    """Elasticsearch index migration manager."""
    
    def __init__(self, elasticsearch_client):
        super().__init__(elasticsearch_client)
        self.db_type = "elasticsearch"
        self.es_client = elasticsearch_client
    
    async def get_current_version(self) -> str:
        """Get current Elasticsearch schema version."""
        try:
            # Check if migrations index exists
            if not await self.es_client.indices.exists(index="schema_migrations"):
                return "0.0.0"
            
            # Get latest migration
            response = await self.es_client.search(
                index="schema_migrations",
                body={
                    "query": {"match_all": {}},
                    "sort": [{"version": {"order": "desc"}}],
                    "size": 1
                }
            )
            
            if response["hits"]["total"]["value"] > 0:
                return response["hits"]["hits"][0]["_source"]["version"]
            
            return "0.0.0"
            
        except Exception as e:
            logger.error("Failed to get Elasticsearch version", error=str(e))
            return "0.0.0"
    
    async def record_migration(self, migration: Migration) -> None:
        """Record applied migration in Elasticsearch."""
        # Ensure migrations index exists
        if not await self.es_client.indices.exists(index="schema_migrations"):
            await self.es_client.indices.create(
                index="schema_migrations",
                body={
                    "mappings": {
                        "properties": {
                            "version": {"type": "keyword"},
                            "name": {"type": "text"},
                            "description": {"type": "text"},
                            "migration_type": {"type": "keyword"},
                            "applied_at": {"type": "date"},
                            "checksum": {"type": "keyword"}
                        }
                    }
                }
            )
        
        migration_record = {
            "version": migration.version,
            "name": migration.name,
            "description": migration.description,
            "migration_type": migration.migration_type,
            "applied_at": datetime.utcnow().isoformat(),
            "checksum": self._calculate_checksum(migration)
        }
        
        await self.es_client.index(
            index="schema_migrations",
            id=migration.version,
            body=migration_record
        )
        logger.info("Recorded Elasticsearch migration", version=migration.version)
    
    async def execute_migration(self, migration: Migration) -> None:
        """Execute Elasticsearch migration."""
        logger.info("Executing Elasticsearch migration", version=migration.version, name=migration.name)
        
        if migration.file_path:
            with open(migration.file_path, 'r') as f:
                migration_data = json.load(f)
                operations = migration_data.get("operations", [])
        else:
            operations = []
        
        for operation in operations:
            await self._execute_operation(operation)
    
    async def _execute_operation(self, operation: Dict[str, Any]) -> None:
        """Execute a single Elasticsearch operation."""
        op_type = operation["type"]
        
        if op_type == "create_index":
            index_name = operation["index"]
            mapping = operation.get("mapping", {})
            settings = operation.get("settings", {})
            
            body = {}
            if mapping:
                body["mappings"] = mapping
            if settings:
                body["settings"] = settings
            
            await self.es_client.indices.create(index=index_name, body=body)
        
        elif op_type == "delete_index":
            index_name = operation["index"]
            await self.es_client.indices.delete(index=index_name)
        
        elif op_type == "update_mapping":
            index_name = operation["index"]
            mapping = operation["mapping"]
            
            await self.es_client.indices.put_mapping(
                index=index_name,
                body=mapping
            )
        
        elif op_type == "create_alias":
            alias_name = operation["alias"]
            index_name = operation["index"]
            
            await self.es_client.indices.put_alias(
                index=index_name,
                name=alias_name
            )
        
        elif op_type == "reindex":
            source_index = operation["source"]
            dest_index = operation["destination"]
            
            await self.es_client.reindex(
                body={
                    "source": {"index": source_index},
                    "dest": {"index": dest_index}
                }
            )
        
        else:
            raise MigrationError(f"Unknown Elasticsearch operation type: {op_type}")
    
    async def rollback_migration(self, migration: Migration) -> None:
        """Rollback Elasticsearch migration."""
        if migration.rollback_path and os.path.exists(migration.rollback_path):
            with open(migration.rollback_path, 'r') as f:
                rollback_data = json.load(f)
                operations = rollback_data.get("operations", [])
            
            for operation in operations:
                await self._execute_operation(operation)
        
        # Remove migration record
        await self.es_client.delete(index="schema_migrations", id=migration.version)
    
    def _calculate_checksum(self, migration: Migration) -> str:
        """Calculate checksum for migration integrity."""
        import hashlib
        content = f"{migration.version}{migration.name}{migration.description}"
        return hashlib.md5(content.encode()).hexdigest()


class DatabaseMigrationManager:
    """Manages database schema migrations across different databases."""
    
    def __init__(
        self,
        mongodb_manager: Optional[MongoDBManager] = None,
        postgresql_manager: Optional[PostgreSQLManager] = None,
        elasticsearch_client: Optional[Any] = None
    ):
        self.migrators = {}
        
        if mongodb_manager:
            self.migrators["mongodb"] = MongoMigrator(mongodb_manager)
        
        if postgresql_manager and PostgreSQLManager:
            self.migrators["postgresql"] = PostgreSQLMigrator(postgresql_manager)
        
        if elasticsearch_client:
            self.migrators["elasticsearch"] = ElasticsearchMigrator(elasticsearch_client)
    
    async def run_migrations(self, target_version: str = "latest", database_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run migrations across specified databases."""
        if database_types is None:
            database_types = list(self.migrators.keys())
        
        migration_results = {}
        
        for db_type in database_types:
            if db_type not in self.migrators:
                logger.warning(f"No migrator available for {db_type}")
                continue
            
            try:
                migrator = self.migrators[db_type]
                current_version = await migrator.get_current_version()
                
                if target_version == "latest":
                    # Get the highest version available
                    all_migrations = await migrator.load_migrations()
                    if all_migrations:
                        target_version = max(m.version for m in all_migrations)
                    else:
                        target_version = current_version
                
                pending_migrations = await migrator.get_pending_migrations(current_version, target_version)
                
                migration_results[db_type] = {
                    "current_version": current_version,
                    "target_version": target_version,
                    "migrations_applied": [],
                    "status": "success"
                }
                
                for migration in pending_migrations:
                    try:
                        await migrator.execute_migration(migration)
                        await migrator.record_migration(migration)
                        migration_results[db_type]["migrations_applied"].append(migration.version)
                        
                    except Exception as e:
                        logger.error(f"Migration {migration.version} failed for {db_type}", error=str(e))
                        migration_results[db_type]["status"] = "failed"
                        migration_results[db_type]["error"] = str(e)
                        
                        # Attempt rollback
                        try:
                            await migrator.rollback_migration(migration)
                            logger.info(f"Rolled back migration {migration.version} for {db_type}")
                        except Exception as rollback_error:
                            logger.error(f"Rollback failed for {migration.version} on {db_type}", error=str(rollback_error))
                        
                        break
                
            except Exception as e:
                logger.error(f"Migration process failed for {db_type}", error=str(e))
                migration_results[db_type] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return migration_results
    
    async def rollback_to_version(self, target_version: str, database_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Rollback to a specific version."""
        if database_types is None:
            database_types = list(self.migrators.keys())
        
        rollback_results = {}
        
        for db_type in database_types:
            if db_type not in self.migrators:
                continue
            
            try:
                migrator = self.migrators[db_type]
                current_version = await migrator.get_current_version()
                
                # Get migrations to rollback (in reverse order)
                all_migrations = await migrator.load_migrations()
                migrations_to_rollback = [
                    m for m in all_migrations
                    if migrator.compare_versions(m.version, target_version) > 0 and
                       migrator.compare_versions(m.version, current_version) <= 0
                ]
                migrations_to_rollback.sort(key=lambda m: m.version, reverse=True)
                
                rollback_results[db_type] = {
                    "current_version": current_version,
                    "target_version": target_version,
                    "migrations_rolled_back": [],
                    "status": "success"
                }
                
                for migration in migrations_to_rollback:
                    try:
                        await migrator.rollback_migration(migration)
                        rollback_results[db_type]["migrations_rolled_back"].append(migration.version)
                        
                    except Exception as e:
                        logger.error(f"Rollback of {migration.version} failed for {db_type}", error=str(e))
                        rollback_results[db_type]["status"] = "failed"
                        rollback_results[db_type]["error"] = str(e)
                        break
                
            except Exception as e:
                logger.error(f"Rollback process failed for {db_type}", error=str(e))
                rollback_results[db_type] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return rollback_results
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status for all databases."""
        status = {}
        
        for db_type, migrator in self.migrators.items():
            try:
                current_version = await migrator.get_current_version()
                all_migrations = await migrator.load_migrations()
                
                if all_migrations:
                    latest_version = max(m.version for m in all_migrations)
                    pending_count = len([
                        m for m in all_migrations
                        if migrator.compare_versions(m.version, current_version) > 0
                    ])
                else:
                    latest_version = "0.0.0"
                    pending_count = 0
                
                status[db_type] = {
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "pending_migrations": pending_count,
                    "up_to_date": current_version == latest_version
                }
                
            except Exception as e:
                status[db_type] = {
                    "error": str(e),
                    "status": "error"
                }
        
        return status