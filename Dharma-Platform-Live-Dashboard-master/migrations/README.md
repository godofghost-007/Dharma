# Database Migration System

This directory contains the database migration system for Project Dharma, supporting MongoDB, PostgreSQL, and Elasticsearch migrations with versioning and rollback capabilities.

## Directory Structure

```
migrations/
├── mongodb/           # MongoDB migrations
├── postgresql/        # PostgreSQL migrations
├── elasticsearch/     # Elasticsearch migrations
└── README.md         # This file
```

## Migration File Format

### MongoDB Migrations

MongoDB migrations are defined in JSON files with the following structure:

```json
{
  "version": "1.0.0",
  "name": "migration_name",
  "description": "Description of what this migration does",
  "database_type": "mongodb",
  "migration_type": "schema",
  "operations": [
    {
      "type": "create_collection",
      "collection": "collection_name",
      "options": {
        "validator": { ... }
      }
    },
    {
      "type": "create_index",
      "collection": "collection_name",
      "index": [["field", 1]],
      "options": {"name": "index_name"}
    }
  ]
}
```

Supported MongoDB operations:
- `create_collection`: Create a new collection with optional validation
- `create_index`: Create an index on a collection
- `drop_index`: Drop an index
- `add_field`: Add a field to documents
- `remove_field`: Remove a field from documents
- `rename_field`: Rename a field
- `update_documents`: Update documents with custom queries

### PostgreSQL Migrations

PostgreSQL migrations consist of two files:
1. A JSON metadata file (e.g., `001_migration.json`)
2. A SQL file with the actual migration (e.g., `001_migration.sql`)

JSON metadata file:
```json
{
  "version": "1.0.0",
  "name": "migration_name",
  "description": "Description of what this migration does",
  "database_type": "postgresql",
  "migration_type": "schema"
}
```

SQL file contains standard SQL DDL statements:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL
);

CREATE INDEX idx_users_username ON users(username);
```

### Elasticsearch Migrations

Elasticsearch migrations are defined in JSON files:

```json
{
  "version": "1.0.0",
  "name": "migration_name",
  "description": "Description of what this migration does",
  "database_type": "elasticsearch",
  "migration_type": "schema",
  "operations": [
    {
      "type": "create_index",
      "index": "index_name",
      "mapping": { ... },
      "settings": { ... }
    }
  ]
}
```

Supported Elasticsearch operations:
- `create_index`: Create a new index with mappings and settings
- `delete_index`: Delete an index
- `update_mapping`: Update index mapping
- `create_alias`: Create an index alias
- `reindex`: Reindex data from one index to another

## Using the Migration System

### Command Line Interface

The migration system includes a CLI tool at `scripts/migrate.py`:

```bash
# Run all pending migrations
python scripts/migrate.py migrate

# Run migrations to a specific version
python scripts/migrate.py migrate --version 1.2.0

# Run migrations for specific databases only
python scripts/migrate.py migrate --databases mongodb postgresql

# Check migration status
python scripts/migrate.py status

# Rollback to a specific version
python scripts/migrate.py rollback 1.0.0

# Rollback specific databases
python scripts/migrate.py rollback 1.0.0 --databases mongodb
```

### Programmatic Usage

```python
from shared.database.migrations import DatabaseMigrationManager
from shared.database.mongodb import MongoDBManager
from shared.database.postgresql import PostgreSQLManager

# Create database managers
mongodb_manager = MongoDBManager(connection_string, database_name)
postgresql_manager = PostgreSQLManager(connection_string)

# Create migration manager
migration_manager = DatabaseMigrationManager(
    mongodb_manager=mongodb_manager,
    postgresql_manager=postgresql_manager
)

# Run migrations
results = await migration_manager.run_migrations("latest")

# Check status
status = await migration_manager.get_migration_status()
```

## Version Numbering

Migrations use semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes that require manual intervention
- **MINOR**: New features or schema additions
- **PATCH**: Bug fixes or minor adjustments

Examples:
- `1.0.0`: Initial schema
- `1.1.0`: Add new collections/tables
- `1.1.1`: Fix index or constraint
- `2.0.0`: Breaking schema changes

## Creating New Migrations

### 1. Determine Version Number

Look at existing migrations and increment appropriately:
```bash
ls migrations/mongodb/
# 001_initial_schema.json (1.0.0)
# Next migration should be 002_add_user_profiles.json (1.1.0)
```

### 2. Create Migration Files

For MongoDB:
```bash
# Create JSON file
touch migrations/mongodb/002_add_user_profiles.json
```

For PostgreSQL:
```bash
# Create both JSON and SQL files
touch migrations/postgresql/002_add_user_roles.json
touch migrations/postgresql/002_add_user_roles.sql
```

### 3. Define Migration Content

Follow the format examples above and include:
- Clear version number
- Descriptive name and description
- All necessary operations
- Proper error handling considerations

### 4. Test Migration

```bash
# Test on development environment
python scripts/migrate.py migrate --version 1.1.0

# Verify results
python scripts/migrate.py status

# Test rollback
python scripts/migrate.py rollback 1.0.0
```

## Best Practices

### 1. Migration Safety
- Always test migrations on development/staging first
- Create rollback scripts for complex migrations
- Use transactions where possible (PostgreSQL)
- Backup data before running migrations in production

### 2. Schema Design
- Make migrations idempotent when possible
- Use `IF NOT EXISTS` for CREATE operations
- Consider data migration impact on large datasets
- Plan for zero-downtime deployments

### 3. Version Control
- Never modify existing migration files
- Create new migrations for schema changes
- Use descriptive names and comments
- Document breaking changes clearly

### 4. Dependencies
- List migration dependencies explicitly
- Ensure proper ordering of operations
- Consider cross-database dependencies

## Rollback Strategy

### Automatic Rollback
The system supports automatic rollback for failed migrations:
```python
try:
    await migrator.execute_migration(migration)
    await migrator.record_migration(migration)
except Exception as e:
    await migrator.rollback_migration(migration)
    raise
```

### Manual Rollback
Create rollback files for complex migrations:
```
migrations/mongodb/002_add_user_profiles.json
migrations/mongodb/002_add_user_profiles_rollback.json
```

### Rollback Limitations
- Some operations cannot be automatically rolled back
- Data loss may occur during rollback
- Always backup before major migrations

## Monitoring and Logging

The migration system provides comprehensive logging:
- Migration execution status
- Performance metrics
- Error details and stack traces
- Rollback operations

Logs are structured using `structlog` for easy parsing and monitoring.

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify database connection strings
   - Check network connectivity
   - Ensure proper credentials

2. **Version Conflicts**
   - Check for duplicate version numbers
   - Verify migration file format
   - Review dependency chains

3. **Schema Validation Errors**
   - Validate JSON syntax
   - Check MongoDB validators
   - Verify PostgreSQL constraints

4. **Performance Issues**
   - Monitor migration execution time
   - Consider batch processing for large datasets
   - Use appropriate indexes

### Recovery Procedures

1. **Failed Migration Recovery**
   ```bash
   # Check current status
   python scripts/migrate.py status
   
   # Rollback to last known good version
   python scripts/migrate.py rollback <version>
   
   # Fix migration file and retry
   python scripts/migrate.py migrate
   ```

2. **Inconsistent State Recovery**
   - Manually verify database state
   - Update migration tracking tables if needed
   - Re-run specific migrations if safe

## Security Considerations

- Store database credentials securely
- Use least-privilege database accounts
- Audit migration execution
- Encrypt sensitive migration data
- Review migration files for security issues

## Performance Optimization

- Create indexes after bulk data operations
- Use batch operations for large datasets
- Monitor resource usage during migrations
- Schedule migrations during low-traffic periods
- Consider read replicas for zero-downtime migrations