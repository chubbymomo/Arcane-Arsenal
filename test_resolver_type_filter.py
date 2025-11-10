#!/usr/bin/env python3
"""
Test to diagnose EntityResolver type filtering issue.
Simulates the exact scenario: create location in Tool 1, resolve it in Tool 2.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Set up logging to see DEBUG/INFO messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from core.state_engine import StateEngine
from modules.ai_dm.entity_resolver import EntityResolver

def test_type_filtering():
    """Test if type filtering works correctly on newly created entities."""

    print("\n" + "="*80)
    print("TEST: EntityResolver Type Filtering After Entity Creation")
    print("="*80 + "\n")

    # Create in-memory database with autocommit
    print("Step 1: Initializing StateEngine with autocommit mode...")
    engine = StateEngine(':memory:')

    # Load core components module
    from modules.core_components import CoreComponentsModule
    module = CoreComponentsModule()
    module.initialize(engine)
    print("  ✓ StateEngine initialized\n")

    # SIMULATE TOOL 1: Create location
    print("Step 2: TOOL 1 - Creating location 'The Crescent Library'")
    print("-" * 80)

    result = engine.create_entity("The Crescent Library")
    location_id = result.entity.id
    print(f"  ✓ Created entity: {location_id}")

    # Add Identity component
    engine.add_component(location_id, 'Identity', {
        'description': 'A test library'
    })
    print(f"  ✓ Added Identity component")

    # Add Location component
    engine.add_component(location_id, 'Location', {
        'location_type': 'library',
        'features': [],
        'visited': False,
        'parent_location': None,
        'connected_locations': []
    })
    print(f"  ✓ Added Location component")

    # Add Position component
    engine.add_component(location_id, 'Position', {
        'region': 'Meridian City'
    })
    print(f"  ✓ Added Position component")
    print()

    # Verify the entity was created correctly
    print("Step 3: Verifying entity was created correctly")
    print("-" * 80)
    entity = engine.get_entity(location_id)
    print(f"  Entity exists: {entity is not None}")
    print(f"  Entity name: {entity.name}")
    print(f"  Entity ID: {entity.id}")

    # Check components
    components = engine.get_entity_components(location_id)
    print(f"  Components: {list(components.keys())}")

    # Specifically check for Location component
    location_comp = engine.get_component(location_id, 'Location')
    print(f"  Has Location component: {location_comp is not None}")
    if location_comp:
        print(f"    → Location data: {location_comp.data}")
    print()

    # SIMULATE TOOL 2: Try to resolve the location WITH type filter
    print("Step 4: TOOL 2 - Resolving 'The Crescent Library' WITH type filter")
    print("-" * 80)
    print("  Calling: resolver.resolve('The Crescent Library', expected_type='location')")
    print()

    resolver = EntityResolver(engine)
    resolved_with_type = resolver.resolve('The Crescent Library', expected_type='location')

    if resolved_with_type:
        print(f"  ✓ SUCCESS: Found {resolved_with_type.name} ({resolved_with_type.id})")
    else:
        print(f"  ✗ FAILED: Could not resolve with type filter")
    print()

    # SIMULATE TOOL 3: Try to resolve the location WITHOUT type filter
    print("Step 5: TOOL 3 - Resolving 'The Crescent Library' WITHOUT type filter")
    print("-" * 80)
    print("  Calling: resolver.resolve('The Crescent Library')")
    print()

    resolved_without_type = resolver.resolve('The Crescent Library')

    if resolved_without_type:
        print(f"  ✓ SUCCESS: Found {resolved_without_type.name} ({resolved_without_type.id})")
    else:
        print(f"  ✗ FAILED: Could not resolve without type filter")
    print()

    # Check what query_entities returns
    print("Step 6: Checking what query_entities() returns")
    print("-" * 80)
    all_entities = engine.query_entities()
    print(f"  Total entities: {len(all_entities)}")
    for e in all_entities:
        if not e.is_active():
            continue
        print(f"    - {e.name} (id: {e.id})")
        comps = engine.get_entity_components(e.id)
        print(f"      Components: {list(comps.keys())}")
    print()

    # Final summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"  Entity created: ✓")
    print(f"  Location component added: ✓")
    print(f"  Resolve WITH type filter: {'✓ PASS' if resolved_with_type else '✗ FAIL'}")
    print(f"  Resolve WITHOUT type filter: {'✓ PASS' if resolved_without_type else '✗ FAIL'}")
    print()

    if not resolved_with_type and resolved_without_type:
        print("❌ BUG CONFIRMED: Type filtering is broken!")
        print("   Entity exists, has Location component, but type filter fails.")
        return False
    elif resolved_with_type:
        print("✓ No bug found - type filtering works correctly")
        return True
    else:
        print("❌ Neither method worked - entity not visible at all")
        return False

if __name__ == '__main__':
    success = test_type_filtering()
    sys.exit(0 if success else 1)
