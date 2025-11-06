# Database Migrations

This directory contains migration scripts for updating world databases to new schema versions.

## When to Use Migrations

Migrations are needed when:
- Component type names change
- Relationship type names change
- Database schema changes (new tables, columns)
- Data format changes that affect existing worlds

## Running Migrations

Each migration is a standalone Python script that can be run directly:

```bash
python migrations/001_rename_item_components.py /path/to/world
```

**Important:**
- Always backup your world before running migrations
- Migrations are transactional - they will rollback on error
- Migrations should be idempotent (safe to run multiple times)

## Available Migrations

### 001_rename_item_components.py

**Purpose:** Rename item component types to follow PascalCase naming convention

**Changes:**
- `item` → `Item`
- `equippable` → `Equippable`
- `consumable` → `Consumable`

**Required for:** Worlds created before Sprint 1 Priority 2 fixes

**Usage:**
```bash
python migrations/001_rename_item_components.py /path/to/world
```

## Creating New Migrations

When creating a new migration:

1. **Naming:** Use format `NNN_description.py` (e.g., `002_add_spell_system.py`)
2. **Documentation:** Include docstring explaining what the migration does
3. **Transactions:** Wrap all changes in a transaction with rollback on error
4. **Logging:** Print clear progress messages
5. **Confirmation:** Ask for user confirmation before making changes
6. **Idempotency:** Make migrations safe to run multiple times
7. **Testing:** Test on a copy of a real world database

### Migration Template

```python
#!/usr/bin/env python3
"""
Migration: Brief description

Changes:
- List of changes

Usage:
    python migrations/NNN_migration_name.py /path/to/world
"""

import sys
import os
import sqlite3

def migrate_world(world_path: str) -> None:
    db_path = os.path.join(world_path, 'world.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("BEGIN TRANSACTION")

    try:
        # Make changes here

        conn.commit()
        print("✓ Migration completed")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        sys.exit(1)

    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python migrations/NNN_migration_name.py /path/to/world")
        sys.exit(1)

    migrate_world(sys.argv[1])
```

## Migration Best Practices

1. **Backup First:** Always backup worlds before migrating
2. **Test Thoroughly:** Test on development worlds before production
3. **Document Changes:** Update this README when adding migrations
4. **Version Control:** Commit migrations with the code changes they support
5. **Backward Compatibility:** Consider if old code needs to work during migration
6. **Error Handling:** Provide clear error messages and rollback on failure
7. **Progress Reporting:** Show what the migration is doing
