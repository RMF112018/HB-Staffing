-- Database initialization script for PostgreSQL
-- This script runs when the PostgreSQL container starts for the first time

-- Create database (if not exists)
-- Note: This is handled by POSTGRES_DB environment variable in docker-compose.yml

-- Grant permissions (handled by POSTGRES_USER/POSTGRES_PASSWORD)

-- Create extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Additional database configuration can be added here
-- For example: CREATE INDEX, CREATE VIEW, etc.
