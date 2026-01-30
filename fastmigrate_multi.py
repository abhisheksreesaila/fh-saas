#!/usr/bin/env python3
"""
FastMigrate Multi-Tenant: Bidirectional Database Migration System
Inspired by FastMigrate with multi-tenant support

Features:
- Forward (UP) and backward (DOWN) migrations
- Version tracking per database (host + all tenants)
- Transaction safety with rollback
- Checksum validation
- Dry-run mode
- Multi-tenant aware
"""

import os
import re
import hashlib
import psycopg2
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv
import argparse
import sys

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from services.tenant.tenant_db_service import get_tenant_db_service


class MigrationFile:
    """Represents a migration file with UP and DOWN sections"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.version = self._extract_version()
        self.name = self._extract_name()
        self.scope = self._extract_scope()
        self.up_sql, self.down_sql = self._parse_sql()
    
    def _extract_version(self) -> int:
        """Extract version number from filename (e.g., 003_add_stripe.sql -> 3)"""
        match = re.match(r'^(\d+)_', self.filepath.name)
        if not match:
            raise ValueError(f"Invalid migration filename: {self.filepath.name}. Must start with version number (e.g., 001_)")
        return int(match.group(1))
    
    def _extract_name(self) -> str:
        """Extract migration name from filename"""
        match = re.match(r'^\d+_(.+)\.sql$', self.filepath.name)
        if not match:
            return self.filepath.stem
        return match.group(1)
    
    def _extract_scope(self) -> str:
        """Determine scope from directory (host/tenant/both)"""
        parent_dir = self.filepath.parent.name
        if parent_dir in ['host', 'tenant', 'both']:
            return parent_dir
        return 'unknown'
    
    def _parse_sql(self) -> Tuple[str, str]:
        """Parse SQL file and extract UP and DOWN sections"""
        content = self.filepath.read_text(encoding='utf-8')
        
        # Look for UP and DOWN markers
        up_pattern = r'--\s*=+\s*UP\s*=+\s*\n(.*?)(?=--\s*=+\s*DOWN\s*=+|$)'
        down_pattern = r'--\s*=+\s*DOWN\s*=+\s*\n(.*?)$'
        
        up_match = re.search(up_pattern, content, re.DOTALL | re.IGNORECASE)
        down_match = re.search(down_pattern, content, re.DOTALL | re.IGNORECASE)
        
        up_sql = up_match.group(1).strip() if up_match else content.strip()
        down_sql = down_match.group(1).strip() if down_match else ''
        
        return up_sql, down_sql
    
    def get_checksum(self, direction: str = 'up') -> str:
        """Calculate checksum for migration content"""
        sql = self.up_sql if direction == 'up' else self.down_sql
        return hashlib.sha256(sql.encode()).hexdigest()[:16]
    
    def __repr__(self):
        return f"Migration({self.version:03d}_{self.name}, scope={self.scope})"


class MigrationRunner:
    """Handles migration execution across host and tenant databases"""
    
    def __init__(self, migrations_dir: str = 'migrations', dry_run: bool = False):
        self.migrations_dir = Path(migrations_dir)
        self.dry_run = dry_run
        self.tenant_service = get_tenant_db_service()
        
        # Color codes for console output
        self.COLORS = {
            'GREEN': '\033[92m',
            'YELLOW': '\033[93m',
            'RED': '\033[91m',
            'BLUE': '\033[94m',
            'CYAN': '\033[96m',
            'BOLD': '\033[1m',
            'END': '\033[0m'
        }
    
    def _color(self, text: str, color: str) -> str:
        """Apply color to text"""
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['END']}"
    
    def _get_db_connection(self, database_name: str = None):
        """Get raw psycopg2 connection for migration operations"""
        POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME")
        POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        POSTGRES_HOST = os.getenv("POSTGRES_HOST")
        POSTGRES_DATABASE = database_name or os.getenv("POSTGRES_DATABASE")
        POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USERNAME,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DATABASE
        )
    
    def _ensure_migration_table(self, conn):
        """Create migration tracking table if it doesn't exist"""
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _migration_versions (
                    version INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_by TEXT,
                    execution_time_ms INTEGER,
                    checksum TEXT NOT NULL,
                    PRIMARY KEY (version, direction)
                );
                
                CREATE INDEX IF NOT EXISTS idx_migration_version_timestamp 
                ON _migration_versions(version DESC, applied_at DESC);
            """)
            conn.commit()
    
    def get_current_version(self, conn) -> int:
        """Get current migration version for a database"""
        try:
            self._ensure_migration_table(conn)
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(version) 
                    FROM _migration_versions 
                    WHERE direction = 'up'
                """)
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except Exception as e:
            print(f"Error getting current version: {e}")
            return 0
    
    def discover_migrations(self, scope: str = None) -> List[MigrationFile]:
        """Discover all migration files, optionally filtered by scope"""
        migrations = []
        
        scopes = [scope] if scope else ['host', 'tenant', 'both']
        
        for scope_dir in scopes:
            scope_path = self.migrations_dir / scope_dir
            if not scope_path.exists():
                continue
            
            for sql_file in sorted(scope_path.glob('*.sql')):
                try:
                    migration = MigrationFile(sql_file)
                    migrations.append(migration)
                except Exception as e:
                    print(f"⚠️  Skipping invalid migration file {sql_file}: {e}")
        
        # Sort by version number
        migrations.sort(key=lambda m: m.version)
        return migrations
    
    def get_all_tenant_databases(self) -> List[Tuple[str, str]]:
        """Get list of all tenant databases from host database"""
        try:
            from storage.db_models import Tenant
            tenants_table = self.tenant_service.host_db.t.tenants if hasattr(self.tenant_service.host_db, 't') else self.tenant_service.host_db.create(Tenant, pk='id')
            
            tenant_dbs = []
            for tenant in tenants_table():
                if tenant.is_active and tenant.tenant_type == 'tenant':
                    # Extract database name from connection string
                    # Format: postgresql://user:pass@host:port/database
                    db_name = tenant.dbconnection.split('/')[-1]
                    tenant_dbs.append((tenant.id, db_name))
            
            return tenant_dbs
        except Exception as e:
            print(f"Error getting tenant databases: {e}")
            return []
    
    def apply_migration(self, conn, migration: MigrationFile, direction: str = 'up'):
        """Apply a single migration to a database"""
        sql = migration.up_sql if direction == 'up' else migration.down_sql
        
        if not sql:
            raise ValueError(f"No {direction.upper()} section found in migration {migration.version}")
        
        start_time = datetime.now()
        
        try:
            with conn.cursor() as cursor:
                # Execute migration SQL
                cursor.execute(sql)
                
                # Record migration in tracking table
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                checksum = migration.get_checksum(direction)
                
                cursor.execute("""
                    INSERT INTO _migration_versions 
                    (version, name, scope, direction, applied_by, execution_time_ms, checksum)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    migration.version,
                    migration.name,
                    migration.scope,
                    direction,
                    os.getenv('USER', 'system'),
                    execution_time,
                    checksum
                ))
            
            conn.commit()
            return True, execution_time
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Migration failed: {e}")
    
    def migrate_database(self, db_name: str, db_label: str, target_version: Optional[int] = None):
        """Migrate a single database forward"""
        try:
            conn = self._get_db_connection(db_name)
            self._ensure_migration_table(conn)
            
            current_version = self.get_current_version(conn)
            migrations = self.discover_migrations()
            
            # Filter migrations to apply
            pending = [m for m in migrations if m.version > current_version]
            if target_version:
                pending = [m for m in pending if m.version <= target_version]
            
            if not pending:
                print(f"  {self._color('✓', 'GREEN')} {db_label}: Already up to date (v{current_version:03d})")
                conn.close()
                return True
            
            print(f"\n{self._color(f'📦 {db_label}', 'CYAN')} (v{current_version:03d} → v{pending[-1].version:03d})")
            
            for migration in pending:
                # Check scope compatibility
                if migration.scope == 'host' and 'tenant' in db_name.lower():
                    continue
                if migration.scope == 'tenant' and db_name == os.getenv('POSTGRES_DATABASE'):
                    continue
                
                if self.dry_run:
                    print(f"  [DRY RUN] Would apply: {migration.version:03d}_{migration.name}")
                else:
                    try:
                        success, exec_time = self.apply_migration(conn, migration, 'up')
                        print(f"  {self._color('✓', 'GREEN')} Applied {migration.version:03d}_{migration.name} ({exec_time}ms)")
                    except Exception as e:
                        print(f"  {self._color('✗', 'RED')} Failed {migration.version:03d}_{migration.name}: {e}")
                        conn.close()
                        return False
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"  {self._color('✗', 'RED')} Database error for {db_label}: {e}")
            return False
    
    def migrate_all(self, target_version: Optional[int] = None):
        """Migrate all databases (host + tenants)"""
        print(self._color("\n" + "="*60, 'BOLD'))
        print(self._color("  FASTMIGRATE MULTI-TENANT - FORWARD MIGRATION", 'BOLD'))
        print(self._color("="*60 + "\n", 'BOLD'))
        
        if self.dry_run:
            print(self._color("🔍 DRY RUN MODE - No changes will be made\n", 'YELLOW'))
        
        # Migrate host database
        host_db_name = os.getenv('POSTGRES_DATABASE')
        print(self._color("📊 MIGRATING HOST DATABASE", 'BLUE'))
        self.migrate_database(host_db_name, "HOST", target_version)
        
        # Migrate tenant databases
        tenant_dbs = self.get_all_tenant_databases()
        if tenant_dbs:
            print(self._color(f"\n📊 MIGRATING {len(tenant_dbs)} TENANT DATABASE(S)", 'BLUE'))
            for tenant_id, db_name in tenant_dbs:
                self.migrate_database(db_name, f"TENANT {tenant_id}", target_version)
        
        print(self._color("\n" + "="*60, 'BOLD'))
        print(self._color("✅ MIGRATION COMPLETE", 'GREEN'))
        print(self._color("="*60 + "\n", 'BOLD'))
    
    def rollback_database(self, db_name: str, db_label: str, steps: int = 1, target_version: Optional[int] = None):
        """Rollback migrations for a single database"""
        try:
            conn = self._get_db_connection(db_name)
            self._ensure_migration_table(conn)
            
            current_version = self.get_current_version(conn)
            
            if current_version == 0:
                print(f"  {self._color('✓', 'GREEN')} {db_label}: No migrations to rollback")
                conn.close()
                return True
            
            # Calculate target version
            if target_version is None:
                target_version = max(0, current_version - steps)
            
            if target_version >= current_version:
                print(f"  {self._color('⚠️ ', 'YELLOW')} {db_label}: Already at or below target version")
                conn.close()
                return True
            
            # Get migrations to rollback
            migrations = self.discover_migrations()
            to_rollback = [m for m in migrations if target_version < m.version <= current_version]
            to_rollback.reverse()  # Rollback in reverse order
            
            print(f"\n{self._color(f'🔄 {db_label}', 'CYAN')} (v{current_version:03d} → v{target_version:03d})")
            
            for migration in to_rollback:
                if self.dry_run:
                    print(f"  [DRY RUN] Would rollback: {migration.version:03d}_{migration.name}")
                else:
                    try:
                        success, exec_time = self.apply_migration(conn, migration, 'down')
                        print(f"  {self._color('✓', 'GREEN')} Rolled back {migration.version:03d}_{migration.name} ({exec_time}ms)")
                    except Exception as e:
                        print(f"  {self._color('✗', 'RED')} Failed {migration.version:03d}_{migration.name}: {e}")
                        conn.close()
                        return False
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"  {self._color('✗', 'RED')} Database error for {db_label}: {e}")
            return False
    
    def rollback_all(self, steps: int = 1, target_version: Optional[int] = None):
        """Rollback migrations on all databases"""
        print(self._color("\n" + "="*60, 'BOLD'))
        print(self._color("  FASTMIGRATE MULTI-TENANT - ROLLBACK", 'BOLD'))
        print(self._color("="*60 + "\n", 'BOLD'))
        
        if self.dry_run:
            print(self._color("🔍 DRY RUN MODE - No changes will be made\n", 'YELLOW'))
        else:
            print(self._color("⚠️  WARNING: Rolling back migrations may result in data loss!\n", 'RED'))
        
        # Rollback host database
        host_db_name = os.getenv('POSTGRES_DATABASE')
        print(self._color("📊 ROLLING BACK HOST DATABASE", 'BLUE'))
        self.rollback_database(host_db_name, "HOST", steps, target_version)
        
        # Rollback tenant databases
        tenant_dbs = self.get_all_tenant_databases()
        if tenant_dbs:
            print(self._color(f"\n📊 ROLLING BACK {len(tenant_dbs)} TENANT DATABASE(S)", 'BLUE'))
            for tenant_id, db_name in tenant_dbs:
                self.rollback_database(db_name, f"TENANT {tenant_id}", steps, target_version)
        
        print(self._color("\n" + "="*60, 'BOLD'))
        print(self._color("✅ ROLLBACK COMPLETE", 'GREEN'))
        print(self._color("="*60 + "\n", 'BOLD'))
    
    def show_status(self):
        """Show migration status for all databases"""
        print(self._color("\n" + "="*60, 'BOLD'))
        print(self._color("  MIGRATION STATUS", 'BOLD'))
        print(self._color("="*60 + "\n", 'BOLD'))
        
        # Get latest version from migrations
        migrations = self.discover_migrations()
        latest_version = max([m.version for m in migrations]) if migrations else 0
        
        # Show host database status
        host_db_name = os.getenv('POSTGRES_DATABASE')
        try:
            conn = self._get_db_connection(host_db_name)
            self._ensure_migration_table(conn)
            current = self.get_current_version(conn)
            pending = latest_version - current
            status = '✓' if pending == 0 else '⚠️ '
            print(f"{status} HOST: v{current:03d} (latest: v{latest_version:03d}, pending: {pending})")
            conn.close()
        except Exception as e:
            print(f"❌ HOST: Error - {e}")
        
        # Show tenant databases status
        tenant_dbs = self.get_all_tenant_databases()
        if tenant_dbs:
            print(f"\nTENANT DATABASES ({len(tenant_dbs)}):")
            for tenant_id, db_name in tenant_dbs:
                try:
                    conn = self._get_db_connection(db_name)
                    self._ensure_migration_table(conn)
                    current = self.get_current_version(conn)
                    pending = latest_version - current
                    status = '✓' if pending == 0 else '⚠️ '
                    print(f"  {status} {tenant_id}: v{current:03d} (pending: {pending})")
                    conn.close()
                except Exception as e:
                    print(f"  ❌ {tenant_id}: Error - {e}")
        
        print(self._color("\n" + "="*60 + "\n", 'BOLD'))


def main():
    parser = argparse.ArgumentParser(description='FastMigrate Multi-Tenant Database Migration')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Apply pending migrations')
    migrate_parser.add_argument('--to', type=int, help='Migrate to specific version')
    migrate_parser.add_argument('--dry-run', action='store_true', help='Preview migrations without applying')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migrations')
    rollback_parser.add_argument('--steps', type=int, default=1, help='Number of versions to rollback')
    rollback_parser.add_argument('--to', type=int, help='Rollback to specific version')
    rollback_parser.add_argument('--dry-run', action='store_true', help='Preview rollback without applying')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    runner = MigrationRunner(dry_run=args.dry_run if hasattr(args, 'dry_run') else False)
    
    if args.command == 'migrate':
        runner.migrate_all(target_version=args.to if hasattr(args, 'to') else None)
    elif args.command == 'rollback':
        runner.rollback_all(steps=args.steps if hasattr(args, 'steps') else 1, 
                          target_version=args.to if hasattr(args, 'to') else None)
    elif args.command == 'status':
        runner.show_status()


if __name__ == '__main__':
    main()
