-- Migration: Add user profile fields
-- Version: 003

-- UP --
ALTER TABLE users ADD COLUMN first_name TEXT;
ALTER TABLE users ADD COLUMN last_name TEXT;
ALTER TABLE users ADD COLUMN avatar_url TEXT;
ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC';

-- DOWN --
-- Note: SQLite doesn't support DROP COLUMN directly in older versions
-- For SQLite < 3.35.0, this requires table recreation
-- For PostgreSQL or SQLite >= 3.35.0:
ALTER TABLE users DROP COLUMN timezone;
ALTER TABLE users DROP COLUMN avatar_url;
ALTER TABLE users DROP COLUMN last_name;
ALTER TABLE users DROP COLUMN first_name;
