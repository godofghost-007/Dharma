"""Simple migration runner for API Gateway users table."""

import asyncio
import asyncpg
import os
from pathlib import Path

async def run_postgresql_migration():
    """Run PostgreSQL migration for users table."""
    
    # Database connection string
    db_url = os.getenv("DB_POSTGRESQL_URL", "postgresql://postgres:postgres@localhost:5432/dharma")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("Connected to PostgreSQL database")
        
        # Read migration file
        migration_file = Path(__file__).parent.parent.parent / "migrations" / "postgresql" / "007_api_gateway_users.sql"
        
        if not migration_file.exists():
            print(f"Migration file not found: {migration_file}")
            return False
        
        # Read and execute migration
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("Executing migration...")
        await conn.execute(migration_sql)
        print("Migration completed successfully!")
        
        # Verify tables were created
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'token_blacklist')
        """)
        
        print(f"Created tables: {[row['table_name'] for row in tables]}")
        
        # Check if users were inserted
        user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"Users in database: {user_count}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_postgresql_migration())
    exit(0 if success else 1)