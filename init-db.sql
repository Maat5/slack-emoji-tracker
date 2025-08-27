-- Initialize the database with required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create database if it doesn't exist
-- Note: This requires connecting to a default database first (like 'postgres')
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'slack_emoji_tracker') THEN
        CREATE DATABASE slack_emoji_tracker;
    END IF;
END
$$;

-- Connect to the specific database (this would be done in a separate connection)
-- \c slack_emoji_tracker;

-- Create schema if it doesn't exist
-- CREATE SCHEMA IF NOT EXISTS 'your_schema_name';

-- Set the search path to include the new schema
-- SET search_path TO your_schema_name, public;