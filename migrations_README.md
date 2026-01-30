# FastMigrate Multi-Tenant Migrations

Quick reference for database migrations in FINXPLORER.

## 🚀 Quick Commands

```bash
# Check migration status
python fastmigrate_multi.py status

# Apply all pending migrations
python fastmigrate_multi.py migrate

# Preview migrations (dry-run)
python fastmigrate_multi.py migrate --dry-run

# Rollback last migration
python fastmigrate_multi.py rollback

# Rollback to specific version
python fastmigrate_multi.py rollback --to 5
```

## 📁 Directory Structure

```
migrations/
├── host/              # Host database migrations
│   ├── 001_add_subscription_support.sql
│   └── 002_*.sql
│
├── tenant/            # Tenant database migrations
│   ├── 001_example_add_tags_to_transactions.sql
│   └── 002_*.sql
│
└── both/              # Both host and tenant (rare)
    └── 001_*.sql
```

## 📝 Creating a New Migration

### 1. Choose Scope

- **host/** - Only affects main database (users, tenants, subscriptions)
- **tenant/** - Affects all tenant databases (transactions, budgets, connections)
- **both/** - Affects both (rare - use carefully!)

### 2. Create File

File naming: `{version}_{description}.sql`

Example: `migrations/host/002_add_email_verification.sql`

### 3. Write Migration

```sql
-- Migration: 002_add_email_verification
-- Version: 002
-- Description: Add email verification to users
-- Author: your.name@finxplorer.com
-- Date: 2025-12-13
-- Scope: host

-- ==================== UP ====================
-- Applied when migrating forward

ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_user_email_verification 
ON "user"(email_verified);

-- ==================== DOWN ====================
-- Applied when rolling back

DROP INDEX IF EXISTS idx_user_email_verification;
ALTER TABLE "user" DROP COLUMN IF EXISTS email_verified;
```

### 4. Test Migration

```bash
# Preview
python fastmigrate_multi.py migrate --dry-run

# Apply
python fastmigrate_multi.py migrate

# Test rollback
python fastmigrate_multi.py rollback --dry-run
python fastmigrate_multi.py rollback

# Re-apply
python fastmigrate_multi.py migrate
```

## ✅ Best Practices

1. **Always include DOWN section** - Every migration must be reversible
2. **Use idempotent SQL** - Use `IF EXISTS` / `IF NOT EXISTS`
3. **Test rollback** - Before production, test that rollback works
4. **Never edit applied migrations** - Create new migration instead
5. **Keep migrations small** - One logical change per migration
6. **Use descriptive names** - Clear, specific descriptions

## 🔍 Version Tracking

Each database tracks applied migrations in `_migration_versions` table:

```sql
-- View migration history
SELECT version, name, direction, applied_at 
FROM _migration_versions 
ORDER BY applied_at DESC;

-- Check current version
SELECT MAX(version) FROM _migration_versions WHERE direction = 'up';
```

## 🎯 Common Patterns

### Adding a Column

```sql
-- UP
ALTER TABLE table_name 
ADD COLUMN IF NOT EXISTS column_name VARCHAR(255) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_table_column 
ON table_name(column_name);

-- DOWN
DROP INDEX IF EXISTS idx_table_column;
ALTER TABLE table_name DROP COLUMN IF EXISTS column_name;
```

### Creating a Table

```sql
-- UP
CREATE TABLE IF NOT EXISTS new_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_new_table_name ON new_table(name);

-- DOWN
DROP TABLE IF EXISTS new_table CASCADE;
```

### Modifying Data

```sql
-- UP
UPDATE table_name SET status = 'active' WHERE status IS NULL;

-- DOWN
UPDATE table_name SET status = NULL WHERE status = 'active';
```

## 🆘 Troubleshooting

### Migration fails with "column already exists"
- Add `IF NOT EXISTS` to your ALTER TABLE statement
- Or check if migration was partially applied

### Can't find tenant databases
- Verify `.env` has correct database credentials
- Check tenant records exist in host database

### Rollback fails
- Check DOWN section is correct
- Verify objects exist before dropping
- Use `IF EXISTS` clauses

### Version mismatch across databases
```bash
# Check status to see which databases are behind
python fastmigrate_multi.py status

# Apply migrations to bring all up to date
python fastmigrate_multi.py migrate
```

## 📚 Full Documentation

See `docs/MIGRATION_SYSTEM.md` for complete documentation including:
- Detailed command reference
- Workflow examples
- Advanced topics
- CI/CD integration

## 🔗 Related Files

- `fastmigrate_multi.py` - Migration runner script
- `docs/MIGRATION_SYSTEM.md` - Complete documentation
- `services/tenant/tenant_db_service.py` - Tenant database service
- `.env` - Database configuration

---

**Need Help?** Check `docs/MIGRATION_SYSTEM.md` or contact the dev team.
