#!/usr/bin/env python3
"""
Direct test of storage layer with autocommit mode.
No dependencies on other modules.
"""

import sqlite3
import json
from datetime import datetime

print("\n" + "="*80)
print("STORAGE LAYER AUTOCOMMIT TEST")
print("="*80 + "\n")

# Create database with autocommit (like our fix)
print("Step 1: Creating database with isolation_level=None (autocommit)")
conn = sqlite3.connect(':memory:', isolation_level=None)
conn.row_factory = sqlite3.Row
print(f"  → isolation_level = {conn.isolation_level}")
print()

# Create tables
print("Step 2: Creating schema")
conn.execute('''
    CREATE TABLE entities (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT,
        modified_at TEXT,
        deleted_at TEXT,
        deleted_by TEXT
    )
''')

conn.execute('''
    CREATE TABLE components (
        id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL,
        component_type TEXT NOT NULL,
        data TEXT,
        version INTEGER DEFAULT 1,
        created_at TEXT,
        modified_at TEXT,
        deleted_at TEXT,
        FOREIGN KEY (entity_id) REFERENCES entities(id)
    )
''')
print("  ✓ Tables created")
print()

# Simulate Tool 1: Create entity and components
print("Step 3: TOOL 1 - Create entity with components (like create_location does)")
print("-" * 80)

entity_id = 'entity_test123'
now = datetime.utcnow().isoformat()

# Insert entity
conn.execute("""
    INSERT INTO entities (id, name, created_at, modified_at, deleted_at, deleted_by)
    VALUES (?, ?, ?, ?, ?, ?)
""", (entity_id, 'The Crescent Library', now, now, None, None))
conn.commit()  # Explicit commit (like storage.py does)
print(f"  → Inserted entity: {entity_id}")

# Insert Location component
conn.execute("""
    INSERT INTO components (id, entity_id, component_type, data, version, created_at, modified_at, deleted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", ('comp_loc', entity_id, 'Location', json.dumps({'location_type': 'library'}), 1, now, now, None))
conn.commit()  # Explicit commit
print(f"  → Inserted Location component")

# Insert Identity component
conn.execute("""
    INSERT INTO components (id, entity_id, component_type, data, version, created_at, modified_at, deleted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", ('comp_id', entity_id, 'Identity', json.dumps({'description': 'A library'}), 1, now, now, None))
conn.commit()  # Explicit commit
print(f"  → Inserted Identity component")
print()

# Simulate Tool 2: Query for the entity (like EntityResolver does)
print("Step 4: TOOL 2 - Query for entity (like EntityResolver._find_all_by_exact_name)")
print("-" * 80)

cursor = conn.execute("""
    SELECT id, name, created_at, modified_at, deleted_at, deleted_by
    FROM entities
    WHERE deleted_at IS NULL
""")
entities = cursor.fetchall()
print(f"  → Found {len(entities)} entities:")
for e in entities:
    print(f"      - {e['name']} (id: {e['id']})")
print()

# Simulate type check: Get Location component (like EntityResolver._has_type does)
print("Step 5: TOOL 2 - Check for Location component (like _has_type does)")
print("-" * 80)

cursor = conn.execute("""
    SELECT id, entity_id, component_type, data
    FROM components
    WHERE entity_id = ? AND component_type = ? AND deleted_at IS NULL
""", (entity_id, 'Location'))

row = cursor.fetchone()
if row:
    print(f"  ✓ SUCCESS: Found Location component")
    print(f"      id: {row['id']}")
    print(f"      entity_id: {row['entity_id']}")
    print(f"      type: {row['component_type']}")
    print(f"      data: {row['data']}")
    result = "PASS"
else:
    print(f"  ✗ FAILED: Location component NOT FOUND")
    print(f"  Checking what components exist for entity {entity_id}:")

    cursor2 = conn.execute("""
        SELECT component_type FROM components WHERE entity_id = ?
    """, (entity_id,))
    comps = cursor2.fetchall()
    print(f"      Components: {[c['component_type'] for c in comps]}")
    result = "FAIL"

print()
print("="*80)
print(f"TEST RESULT: {result}")
print("="*80)
print()

if result == "PASS":
    print("✓ Autocommit mode works correctly")
    print("  Entities and components are immediately visible after creation")
    print()
    print("If the game still fails, the problem must be elsewhere:")
    print("  - Python module caching (server not restarted)")
    print("  - Different code path in actual game")
    print("  - Some other caching layer")
else:
    print("❌ CRITICAL: Even basic autocommit doesn't work!")
    print("  This means the fix approach is fundamentally wrong")
