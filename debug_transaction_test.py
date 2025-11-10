#!/usr/bin/env python3
"""
Debug script to understand SQLite transaction behavior.
"""

import sqlite3
import os

print("\n" + "="*80)
print("DEBUGGING SQLITE TRANSACTION BEHAVIOR")
print("="*80 + "\n")

# Test 1: Default isolation mode
print("TEST 1: Default isolation mode (DEFERRED)")
print("-" * 80)
conn1_default = sqlite3.connect(':memory:')
print(f"isolation_level = {conn1_default.isolation_level}")

conn1_default.execute('CREATE TABLE test (id INTEGER, name TEXT)')
conn1_default.execute('INSERT INTO test VALUES (1, "Item1")')
print("Inserted Item1 (no explicit commit)")

# Open second connection to same database
# (In memory this won't work, but the concept is the same)
cursor = conn1_default.execute('SELECT * FROM test')
rows = cursor.fetchall()
print(f"Query result: {rows}")
print()

# Test 2: Autocommit mode
print("TEST 2: Autocommit mode (isolation_level=None)")
print("-" * 80)
conn2_auto = sqlite3.connect(':memory:', isolation_level=None)
print(f"isolation_level = {conn2_auto.isolation_level}")

conn2_auto.execute('CREATE TABLE test (id INTEGER, name TEXT)')
conn2_auto.execute('INSERT INTO test VALUES (1, "Item1")')
print("Inserted Item1 (autocommit)")

cursor = conn2_auto.execute('SELECT * FROM test')
rows = cursor.fetchall()
print(f"Query result: {rows}")
print()

# Test 3: Explicit commit with default mode
print("TEST 3: Default mode with explicit commit")
print("-" * 80)
conn3 = sqlite3.connect(':memory:')
print(f"isolation_level = {conn3.isolation_level}")

conn3.execute('CREATE TABLE test (id INTEGER, name TEXT)')
conn3.execute('INSERT INTO test VALUES (1, "Item1")')
print("Inserted Item1")
conn3.commit()
print("Called commit()")

cursor = conn3.execute('SELECT * FROM test')
rows = cursor.fetchall()
print(f"Query result: {rows}")
print()

# Test 4: Multiple operations with autocommit
print("TEST 4: Multiple sequential operations with autocommit")
print("-" * 80)
conn4 = sqlite3.connect(':memory:', isolation_level=None)
print(f"isolation_level = {conn4.isolation_level}")

conn4.execute('CREATE TABLE entities (id TEXT PRIMARY KEY, name TEXT)')
conn4.execute('CREATE TABLE components (id TEXT, entity_id TEXT, type TEXT, data TEXT)')

# Simulate Tool 1
conn4.execute("INSERT INTO entities VALUES ('entity_1', 'Location1')")
conn4.execute("INSERT INTO components VALUES ('comp_1', 'entity_1', 'Location', '{}')")
print("Tool 1: Created Location1")

# Simulate Tool 2 query (like EntityResolver does)
cursor = conn4.execute("SELECT id, name FROM entities WHERE name = 'Location1'")
row = cursor.fetchone()
if row:
    print(f"Tool 2: Found entity: {row}")

    # Check for Location component
    cursor2 = conn4.execute("SELECT * FROM components WHERE entity_id = ? AND type = 'Location'", (row[0],))
    comp = cursor2.fetchone()
    if comp:
        print(f"Tool 2: Found Location component: {comp}")
    else:
        print("Tool 2: NO Location component found!")
else:
    print("Tool 2: Entity NOT FOUND!")

print()

# Test 5: The actual issue - calling commit() in autocommit mode
print("TEST 5: Calling commit() in autocommit mode")
print("-" * 80)
conn5 = sqlite3.connect(':memory:', isolation_level=None)
print(f"isolation_level = {conn5.isolation_level}")

conn5.execute('CREATE TABLE test (id INTEGER, name TEXT)')
conn5.execute('INSERT INTO test VALUES (1, "Item1")')
print("Inserted Item1")

try:
    conn5.commit()
    print("Called commit() - NO ERROR")
except Exception as e:
    print(f"Called commit() - ERROR: {e}")

cursor = conn5.execute('SELECT * FROM test')
rows = cursor.fetchall()
print(f"Query result: {rows}")
print()

print("="*80)
print("SUMMARY")
print("="*80)
print("""
In autocommit mode (isolation_level=None):
- Each statement commits immediately
- Calling commit() is a no-op (no error)
- Data should be visible to subsequent queries

If EntityResolver still can't find entities, the problem is NOT transactions.
It must be something else in the query logic or entity creation.
""")
