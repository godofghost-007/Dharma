#!/usr/bin/env python3
"""
Fix Database Schema for Enhanced Data Collector
"""

import sqlite3
import os

def fix_database_schema():
    """Fix the database schema to match enhanced collector"""
    db_path = "dharma_real_data.db"
    
    print("🔧 Fixing database schema...")
    
    # Backup existing database
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup"
        print(f"📋 Creating backup: {backup_path}")
        import shutil
        shutil.copy2(db_path, backup_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add missing columns to posts table
        print("📊 Adding missing columns...")
        
        # Check if columns exist and add them if they don't
        cursor.execute("PRAGMA table_info(posts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'engagement_views' not in columns:
            cursor.execute('ALTER TABLE posts ADD COLUMN engagement_views INTEGER DEFAULT 0')
            print("✅ Added engagement_views column")
        
        if 'verified_author' not in columns:
            cursor.execute('ALTER TABLE posts ADD COLUMN verified_author BOOLEAN DEFAULT FALSE')
            print("✅ Added verified_author column")
        
        if 'follower_count' not in columns:
            cursor.execute('ALTER TABLE posts ADD COLUMN follower_count INTEGER DEFAULT 0')
            print("✅ Added follower_count column")
        
        if 'updated_at' not in columns:
            cursor.execute('ALTER TABLE posts ADD COLUMN updated_at DATETIME')
            print("✅ Added updated_at column")
        
        conn.commit()
        print("✅ Database schema updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database_schema()