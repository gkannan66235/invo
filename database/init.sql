-- Initialize GST Service Center Database
-- This script sets up the database with required extensions and initial configuration

-- Enable UUID extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search performance
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create database user if not exists (handled by environment variables)
-- POSTGRES_USER and POSTGRES_PASSWORD are set in Dockerfile

-- Set timezone to Indian Standard Time
SET timezone = 'Asia/Kolkata';

-- Create schema for application tables
CREATE SCHEMA IF NOT EXISTS gst_app;

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON SCHEMA gst_app TO gst_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gst_app TO gst_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gst_app TO gst_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA gst_app GRANT ALL ON TABLES TO gst_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA gst_app GRANT ALL ON SEQUENCES TO gst_user;

-- Create indexes for performance optimization (will be created by SQLAlchemy migrations)
-- This is just a placeholder for any custom database setup