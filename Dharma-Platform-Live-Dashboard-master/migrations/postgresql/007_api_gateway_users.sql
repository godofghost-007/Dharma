-- API Gateway Users Table Migration
-- This migration creates the users table for authentication and authorization

-- Create users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'supervisor', 'analyst', 'viewer')),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    
    -- Profile information
    full_name VARCHAR(255),
    department VARCHAR(100),
    phone_number VARCHAR(20),
    
    -- Permissions
    permissions JSONB DEFAULT '[]'::jsonb,
    
    -- Activity tracking
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    last_failed_login TIMESTAMP,
    
    -- Security
    password_changed_at TIMESTAMP,
    must_change_password BOOLEAN DEFAULT false,
    two_factor_enabled BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: Admin123!)
-- In production, this should be changed immediately
INSERT INTO users (username, email, hashed_password, role, full_name, is_active, is_verified)
VALUES (
    'admin',
    'admin@dharma.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3L3jzjvG4e', -- Admin123!
    'admin',
    'System Administrator',
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Insert sample users for testing
INSERT INTO users (username, email, hashed_password, role, full_name, department, is_active, is_verified)
VALUES 
    (
        'analyst1',
        'analyst1@dharma.local',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3L3jzjvG4e', -- Admin123!
        'analyst',
        'John Analyst',
        'Intelligence Analysis',
        true,
        true
    ),
    (
        'supervisor1',
        'supervisor1@dharma.local',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3L3jzjvG4e', -- Admin123!
        'supervisor',
        'Jane Supervisor',
        'Operations',
        true,
        true
    ),
    (
        'viewer1',
        'viewer1@dharma.local',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3L3jzjvG4e', -- Admin123!
        'viewer',
        'Bob Viewer',
        'Monitoring',
        true,
        true
    )
ON CONFLICT (username) DO NOTHING;

-- Create session blacklist table for token management
CREATE TABLE IF NOT EXISTS token_blacklist (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    blacklisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_hash ON token_blacklist(token_hash);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist(expires_at);

-- Create function to clean expired tokens
CREATE OR REPLACE FUNCTION clean_expired_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM token_blacklist WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions to application user (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dharma_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON users TO dharma_app;
        GRANT USAGE, SELECT ON SEQUENCE users_id_seq TO dharma_app;
        GRANT SELECT, INSERT, DELETE ON token_blacklist TO dharma_app;
        GRANT USAGE, SELECT ON SEQUENCE token_blacklist_id_seq TO dharma_app;
    END IF;
END
$$;