#!/usr/bin/env python3
"""
Migration: Rename item component types to PascalCase

Changes:
- item → Item
- equippable → Equippable
- consumable → Consumable

Usage:
    python migrations/001_rename_item_components.py /path/to/world
"""

import sys
import os
import sqlite3
from pathlib import Path


def migrate_world(world_path: str) -> None:
    """
    Migrate a world database to use PascalCase component type names.

    Args:
        world_path: Path to world directory containing world.db
    """
    db_path = os.path.join(world_path, 'world.db')

    if not os.path.exists(db_path):
        print(f"Error: No world database found at {db_path}")
        sys.exit(1)

    print(f"Migrating world: {world_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Start transaction
    cursor.execute("BEGIN TRANSACTION")

    try:
        # 1. Update component_types table
        print("  Updating component_types table...")

        renames = [
            ('item', 'Item'),
            ('equippable', 'Equippable'),
            ('consumable', 'Consumable')
        ]

        for old_name, new_name in renames:
            cursor.execute(
                "UPDATE component_types SET type = ? WHERE type = ?",
                (new_name, old_name)
            )
            affected = cursor.rowcount
            if affected > 0:
                print(f"    Renamed {old_name} → {new_name} in component_types")

        # 2. Update components table
        print("  Updating components table...")

        for old_name, new_name in renames:
            cursor.execute(
                "UPDATE components SET component_type = ? WHERE component_type = ?",
                (new_name, old_name)
            )
            affected = cursor.rowcount
            if affected > 0:
                print(f"    Updated {affected} component(s) from {old_name} → {new_name}")

        # Commit transaction
        conn.commit()
        print("✓ Migration completed successfully")

    except Exception as e:
        # Rollback on error
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        sys.exit(1)

    finally:
        conn.close()


def main():
    """Main entry point for migration script."""
    if len(sys.argv) != 2:
        print("Usage: python migrations/001_rename_item_components.py /path/to/world")
        sys.exit(1)

    world_path = sys.argv[1]

    if not os.path.isdir(world_path):
        print(f"Error: {world_path} is not a directory")
        sys.exit(1)

    # Confirm migration
    print("This will rename item component types in the world database.")
    print("Changes:")
    print("  - item → Item")
    print("  - equippable → Equippable")
    print("  - consumable → Consumable")
    print()

    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Migration cancelled")
        sys.exit(0)

    migrate_world(world_path)


if __name__ == '__main__':
    main()
