"""Tests for database migration system."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import json
import tempfile
import os

from shared.database.migrations import (
    DatabaseMigrationManager,
    MongoMigrator,
    PostgreSQLMigrator,
    ElasticsearchMigrator,
    Migration,
    MigrationError
)


class TestMigration:
    """Test Migration dataclass."""
    
    def test_migration_creation(self):
        """Test creating a migration object."""
        migration = Migration(
            version="1.0.0",
            name="test_migration",
            description="Test migration",
            database_type="mongodb",
            migration_type="schema"
        )
        
        assert migration.version == "1.0.0"
        assert migration.name == "test_migration"
        assert migration.dependencies == []
    
    def test_migration_with_dependencies(self):
        """Test migration with dependencies."""
        migration = Migration(
            version="1.1.0",
            name="dependent_migration",
            description="Migration with dependencies",
            database_type="mongodb",
            migration_type="schema",
            dependencies=["1.0.0"]
        )
        
        assert migration.dependencies == ["1.0.0"]


class TestMongoMigrator:
    """Test MongoDB migrator."""
    
    @pytest.fixture
    def mock_mongodb_manager(self):
        """Create mock MongoDB manager."""
        manager = Mock()
        manager.database = Mock()
        return manager
    
    @pytest.fixture
    def mongo_migrator(self, mock_mongodb_manager):
        """Create MongoDB migrator with mock manager."""
        return MongoMigrator(mock_mongodb_manager)
    
    @pytest.mark.asyncio
    async def test_get_current_version_no_migrations(self, mongo_migrator, mock_mongodb_manager):
        """Test getting current version when no migrations exist."""
        mock_mongodb_manager.database.schema_migrations.find_one = AsyncMock(return_value=None)
        
        version = await mongo_migrator.get_current_version()
        assert version == "0.0.0"
    
    @pytest.mark.asyncio
    async def test_get_current_version_with_migrations(self, mongo_migrator, mock_mongodb_manager):
        """Test getting current version with existing migrations."""
        mock_mongodb_manager.database.schema_migrations.find_one = AsyncMock(
            return_value={"version": "1.2.0"}
        )
        
        version = await mongo_migrator.get_current_version()
        assert version == "1.2.0"
    
    @pytest.mark.asyncio
    async def test_record_migration(self, mongo_migrator, mock_mongodb_manager):
        """Test recording a migration."""
        migration = Migration(
            version="1.0.0",
            name="test_migration",
            description="Test migration",
            database_type="mongodb",
            migration_type="schema"
        )
        
        mock_mongodb_manager.database.schema_migrations.insert_one = AsyncMock()
        
        await mongo_migrator.record_migration(migration)
        
        mock_mongodb_manager.database.schema_migrations.insert_one.assert_called_once()
        call_args = mock_mongodb_manager.database.schema_migrations.insert_one.call_args[0][0]
        assert call_args["version"] == "1.0.0"
        assert call_args["name"] == "test_migration"
    
    def test_compare_versions(self, mongo_migrator):
        """Test version comparison."""
        assert mongo_migrator.compare_versions("1.0.0", "0.9.0") == 1
        assert mongo_migrator.compare_versions("1.0.0", "1.0.0") == 0
        assert mongo_migrator.compare_versions("1.0.0", "1.1.0") == -1
        assert mongo_migrator.compare_versions("1.0.0", "1.0.1") == -1


class TestPostgreSQLMigrator:
    """Test PostgreSQL migrator."""
    
    @pytest.fixture
    def mock_postgresql_manager(self):
        """Create mock PostgreSQL manager."""
        manager = Mock()
        manager.pool = Mock()
        manager.execute = AsyncMock()
        manager.fetchval = AsyncMock()
        return manager
    
    @pytest.fixture
    def postgresql_migrator(self, mock_postgresql_manager):
        """Create PostgreSQL migrator with mock manager."""
        return PostgreSQLMigrator(mock_postgresql_manager)
    
    @pytest.mark.asyncio
    async def test_ensure_migrations_table(self, postgresql_migrator, mock_postgresql_manager):
        """Test ensuring migrations table exists."""
        await postgresql_migrator.ensure_migrations_table()
        
        mock_postgresql_manager.execute.assert_called_once()
        call_args = mock_postgresql_manager.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS schema_migrations" in call_args
    
    @pytest.mark.asyncio
    async def test_get_current_version_no_migrations(self, postgresql_migrator, mock_postgresql_manager):
        """Test getting current version when no migrations exist."""
        mock_postgresql_manager.fetchval.return_value = None
        
        version = await postgresql_migrator.get_current_version()
        assert version == "0.0.0"
    
    @pytest.mark.asyncio
    async def test_record_migration(self, postgresql_migrator, mock_postgresql_manager):
        """Test recording a migration."""
        migration = Migration(
            version="1.0.0",
            name="test_migration",
            description="Test migration",
            database_type="postgresql",
            migration_type="schema"
        )
        
        await postgresql_migrator.record_migration(migration)
        
        # Should call execute twice: once for ensure_migrations_table, once for insert
        assert mock_postgresql_manager.execute.call_count == 2


class TestDatabaseMigrationManager:
    """Test database migration manager."""
    
    @pytest.fixture
    def mock_managers(self):
        """Create mock database managers."""
        mongodb_manager = Mock()
        postgresql_manager = Mock()
        elasticsearch_client = Mock()
        
        return mongodb_manager, postgresql_manager, elasticsearch_client
    
    @pytest.fixture
    def migration_manager(self, mock_managers):
        """Create migration manager with mock managers."""
        mongodb_manager, postgresql_manager, elasticsearch_client = mock_managers
        
        return DatabaseMigrationManager(
            mongodb_manager=mongodb_manager,
            postgresql_manager=postgresql_manager,
            elasticsearch_client=elasticsearch_client
        )
    
    @pytest.mark.asyncio
    async def test_get_migration_status(self, migration_manager):
        """Test getting migration status."""
        # Mock the migrators
        for migrator in migration_manager.migrators.values():
            migrator.get_current_version = AsyncMock(return_value="1.0.0")
            migrator.load_migrations = AsyncMock(return_value=[
                Migration("1.0.0", "test", "test", "mongodb", "schema"),
                Migration("1.1.0", "test2", "test2", "mongodb", "schema")
            ])
        
        status = await migration_manager.get_migration_status()
        
        assert "mongodb" in status
        assert "postgresql" in status
        assert "elasticsearch" in status
        
        for db_status in status.values():
            assert "current_version" in db_status
            assert "latest_version" in db_status
            assert "pending_migrations" in db_status
            assert "up_to_date" in db_status


class TestMigrationFiles:
    """Test migration file loading and validation."""
    
    def test_load_mongodb_migration_file(self):
        """Test loading MongoDB migration file."""
        migration_file = Path("project-dharma/migrations/mongodb/001_initial_schema.json")
        
        if migration_file.exists():
            with open(migration_file, 'r') as f:
                migration_data = json.load(f)
            
            assert "version" in migration_data
            assert "name" in migration_data
            assert "description" in migration_data
            assert "database_type" in migration_data
            assert migration_data["database_type"] == "mongodb"
            assert "operations" in migration_data
            
            # Validate operations structure
            for operation in migration_data["operations"]:
                assert "type" in operation
                if operation["type"] == "create_collection":
                    assert "collection" in operation
                elif operation["type"] == "create_index":
                    assert "collection" in operation
                    assert "index" in operation
    
    def test_load_postgresql_migration_files(self):
        """Test loading PostgreSQL migration files."""
        json_file = Path("project-dharma/migrations/postgresql/001_initial_schema.json")
        sql_file = Path("project-dharma/migrations/postgresql/001_initial_schema.sql")
        
        if json_file.exists():
            with open(json_file, 'r') as f:
                migration_data = json.load(f)
            
            assert "version" in migration_data
            assert "database_type" in migration_data
            assert migration_data["database_type"] == "postgresql"
        
        if sql_file.exists():
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            
            assert "CREATE TABLE" in sql_content
            assert "users" in sql_content
            assert "alerts" in sql_content
    
    def test_load_elasticsearch_migration_file(self):
        """Test loading Elasticsearch migration file."""
        migration_file = Path("project-dharma/migrations/elasticsearch/001_initial_mappings.json")
        
        if migration_file.exists():
            with open(migration_file, 'r') as f:
                migration_data = json.load(f)
            
            assert "version" in migration_data
            assert "database_type" in migration_data
            assert migration_data["database_type"] == "elasticsearch"
            assert "operations" in migration_data
            
            # Validate operations structure
            for operation in migration_data["operations"]:
                assert "type" in operation
                if operation["type"] == "create_index":
                    assert "index" in operation
                    assert "mapping" in operation


if __name__ == "__main__":
    pytest.main([__file__])