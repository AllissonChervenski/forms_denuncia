-- Initialize database with extensions and settings
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";
-- Set timezone
SET timezone = 'America/Sao_Paulo';

-- Create indexes for better performance (will be created by migrations, but good to have)
-- These are placeholders - actual indexes created by Django migrations