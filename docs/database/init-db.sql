-- PostgreSQL initialization script for Scomp project
-- This script is automatically run when PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema
CREATE SCHEMA IF NOT EXISTS public;

-- Grant privileges to user
GRANT ALL PRIVILEGES ON SCHEMA public TO scrapper;

-- Set search path
SET search_path TO public;

-- Verify connection
SELECT 'PostgreSQL initialized for Scomp' as status;
