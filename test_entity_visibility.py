#!/usr/bin/env python3
"""
Test to reproduce the entity visibility issue.
This simulates what happens during AI tool batch execution.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.state_engine import StateEngine
from modules.ai_dm.entity_resolver import EntityResolver
from modules.ai_dm.tools import execute_tool

def test_immediate_entity_visibility():
    """Test if entities created in one tool are visible to the next."""

    print("\n" + "="*80)
    print("TEST: Entity Visibility in Same-Batch Tool Execution")
    print("="*80 + "\n")

    # Create in-memory database
    engine = StateEngine(':memory:')

    # Load required modules (simplified - just core components needed)
    print("Step 1: Initializing engine...")
    from modules.core_components import CoreComponentsModule
    module = CoreComponentsModule()
    module.initialize(engine)
    print("  ✓ Engine initialized\n")

    # Create a test player entity
    print("Step 2: Creating test player entity...")
    player_result = engine.create_entity("Test Player")
    player_id = player_result.entity.id
    print(f"  ✓ Player created: {player_id}\n")

    # TOOL 1: Create parent location
    print("Step 3: TOOL 1 - Create parent location 'Test City'...")
    tool1_result = execute_tool(
        'create_location',
        {
            'name': 'Test City',
            'description': 'A test city',
            'region': 'Test Region',
            'location_type': 'city'
        },
        engine,
        player_id
    )
    print(f"  Tool 1 Result: {tool1_result['success']} - {tool1_result['message']}")

    # Check what entities exist right after Tool 1
    print("\n  Checking entities in database after Tool 1:")
    all_entities_after_tool1 = engine.query_entities()
    for e in all_entities_after_tool1:
        print(f"    - {e.name} (id: {e.id})")

    # Try to resolve the location we just created
    print("\n  Testing EntityResolver after Tool 1:")
    resolver = EntityResolver(engine)
    resolved = resolver.resolve('Test City', expected_type='location')
    if resolved:
        print(f"    ✓ EntityResolver FOUND: {resolved.name} (id: {resolved.id})")
    else:
        print(f"    ✗ EntityResolver FAILED to find 'Test City'")
        print(f"    DEBUG: Trying without expected_type...")
        resolved_no_type = resolver.resolve('Test City')
        if resolved_no_type:
            print(f"      Found without type filter: {resolved_no_type.name}")
            # Check if it has Location component
            loc_comp = engine.get_component(resolved_no_type.id, 'Location')
            print(f"      Has Location component: {loc_comp is not None}")
        else:
            print(f"      Still not found - entity doesn't exist in query results")

    print("\n" + "-"*80 + "\n")

    # TOOL 2: Create child location with parent reference
    print("Step 4: TOOL 2 - Create child location 'Test Building' with parent 'Test City'...")
    tool2_result = execute_tool(
        'create_location',
        {
            'name': 'Test Building',
            'description': 'A test building',
            'region': 'Test City',
            'location_type': 'building',
            'parent_location_name': 'Test City'
        },
        engine,
        player_id
    )
    print(f"  Tool 2 Result: {tool2_result['success']} - {tool2_result['message']}")

    # Check if parent was resolved
    print("\n  Checking if parent location was resolved:")
    test_building = None
    for e in engine.query_entities(['Location']):
        if e.name == 'Test Building':
            test_building = e
            break

    if test_building:
        loc_comp = engine.get_component(test_building.id, 'Location')
        parent_id = loc_comp.data.get('parent_location')
        if parent_id:
            print(f"    ✓ Parent location was resolved: {parent_id}")
        else:
            print(f"    ✗ Parent location was NOT resolved (parent_location is None)")
    else:
        print(f"    ✗ Could not find 'Test Building' entity")

    print("\n" + "-"*80 + "\n")

    # TOOL 3: Try to move player to the child location
    print("Step 5: TOOL 3 - Move player to 'Test Building'...")
    tool3_result = execute_tool(
        'move_player_to_location',
        {
            'location_name': 'Test Building'
        },
        engine,
        player_id
    )
    print(f"  Tool 3 Result: {tool3_result['success']} - {tool3_result['message']}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")

    # Summary
    print("SUMMARY:")
    print(f"  Tool 1 (create parent): {'PASS' if tool1_result['success'] else 'FAIL'}")
    print(f"  EntityResolver found parent: {'PASS' if resolved else 'FAIL'}")
    print(f"  Tool 2 (create child): {'PASS' if tool2_result['success'] else 'FAIL'}")
    parent_resolved = test_building and engine.get_component(test_building.id, 'Location').data.get('parent_location') is not None
    print(f"  Child linked to parent: {'PASS' if parent_resolved else 'FAIL'}")
    print(f"  Tool 3 (move player): {'PASS' if tool3_result['success'] else 'FAIL'}")

    overall = all([
        tool1_result['success'],
        resolved is not None,
        tool2_result['success'],
        parent_resolved,
        tool3_result['success']
    ])

    print(f"\n  OVERALL: {'✓ ALL TESTS PASSED' if overall else '✗ SOME TESTS FAILED'}")

    return overall

if __name__ == '__main__':
    success = test_immediate_entity_visibility()
    sys.exit(0 if success else 1)
