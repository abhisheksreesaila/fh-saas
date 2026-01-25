#!/usr/bin/env python3
"""
Clean Database Files Script (Python version)
Removes SQLite database files and related artifacts from the fh-saas project
"""

import os
import glob
import sys
from pathlib import Path

def find_db_files(base_path="."):
    """Find all database files in the project."""
    patterns = [
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "*.db-shm",
        "*.db-wal",
        "*.db-journal"
    ]
    
    search_paths = [".", "nbs", "_proc"]
    exclude_dirs = {".git", "node_modules", "dist", "build", ".venv", "venv"}
    
    found_files = []
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            continue
            
        for pattern in patterns:
            path_pattern = os.path.join(search_path, "**", pattern)
            for file_path in glob.glob(path_pattern, recursive=True):
                # Skip excluded directories
                path_parts = Path(file_path).parts
                if not any(excluded in path_parts for excluded in exclude_dirs):
                    found_files.append(file_path)
    
    return found_files

def main():
    print("🧹 Cleaning Database Files...")
    
    # Find database files
    db_files = find_db_files()
    
    if not db_files:
        print("✅ No database files found to clean.")
        return 0
    
    # Display files
    print(f"\nFound {len(db_files)} database file(s):")
    for file_path in db_files:
        rel_path = os.path.relpath(file_path)
        print(f"  - {rel_path}")
    
    # Confirm deletion
    print("\n⚠️  This will permanently delete these files.")
    try:
        confirmation = input("Continue? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n❌ Cancelled.")
        return 1
    
    if confirmation not in ('y', 'yes'):
        print("❌ Cancelled.")
        return 1
    
    # Remove files
    print("\n🗑️  Removing files...")
    removed_count = 0
    
    for file_path in db_files:
        try:
            os.remove(file_path)
            rel_path = os.path.relpath(file_path)
            print(f"  ✓ Removed: {rel_path}")
            removed_count += 1
        except Exception as e:
            print(f"  ✗ Failed to remove: {file_path} - {e}")
    
    print(f"\n✅ Cleanup complete! Removed {removed_count} file(s).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
