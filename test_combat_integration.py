#!/usr/bin/env python3
"""
Integration test for the combat system.
Tests the full combat flow including character creation, combat start, attacks, and combat end.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.state_engine import StateEngine
from src.modules.ai_dm.tools import get_tool_handler

def test_combat_integration():
    """Test full combat flow."""
    print("=" * 60)
    print("COMBAT SYSTEM INTEGRATION TEST")
    print("=" * 60)

    # Initialize engine with all modules
    print("\n1. Initializing StateEngine...")
    engine = StateEngine()

    # Load modules
    from src.modules.core_components import CoreComponentsModule
    from src.modules.generic_combat import GenericCombatModule
    from src.modules.generic_fantasy import GenericFantasyModule
    from src.modules.rng import RNGModule
    from src.modules.ai_dm import AIDMModule

    engine.load_module(CoreComponentsModule())
    engine.load_module(RNGModule())
    engine.load_module(GenericCombatModule())
    engine.load_module(GenericFantasyModule())
    engine.load_module(AIDMModule())

    print(f"✓ Loaded {len(engine._modules)} modules")

    # Create player character
    print("\n2. Creating player character...")
    player = engine.create_entity("Thorin Ironshield")

    # Add fantasy components
    engine.add_component(player.id, 'Attributes', {
        'strength': 16,
        'dexterity': 12,
        'constitution': 14,
        'intelligence': 10,
        'wisdom': 11,
        'charisma': 8
    })

    engine.add_component(player.id, 'CharacterDetails', {
        'race': 'dwarf',
        'character_class': 'fighter',
        'level': 3,
        'alignment': 'lawful_good'
    })

    engine.add_component(player.id, 'Health', {
        'current_hp': 28,
        'max_hp': 28
    })

    engine.add_component(player.id, 'Armor', {
        'armor_class': 16,
        'armor_type': 'medium'
    })

    engine.add_component(player.id, 'Weapon', {
        'damage_dice': '1d8+3',
        'damage_type': 'slashing',
        'attack_bonus': 5
    })

    print(f"✓ Created player: {player.name}")
    print(f"  - Level 3 Dwarf Fighter")
    print(f"  - HP: 28/28, AC: 16")
    print(f"  - STR: 16 (+3), DEX: 12 (+1)")

    # Create enemy
    print("\n3. Creating enemy NPC...")
    goblin = engine.create_entity("Goblin Scout")

    engine.add_component(goblin.id, 'NPC', {
        'race': 'goblin',
        'occupation': 'scout',
        'disposition': 'hostile'
    })

    engine.add_component(goblin.id, 'Attributes', {
        'strength': 8,
        'dexterity': 14,
        'constitution': 10,
        'intelligence': 10,
        'wisdom': 8,
        'charisma': 8
    })

    engine.add_component(goblin.id, 'Health', {
        'current_hp': 7,
        'max_hp': 7
    })

    engine.add_component(goblin.id, 'Armor', {
        'armor_class': 13,
        'armor_type': 'light'
    })

    engine.add_component(goblin.id, 'Weapon', {
        'damage_dice': '1d4+2',
        'damage_type': 'piercing',
        'attack_bonus': 4
    })

    print(f"✓ Created enemy: {goblin.name}")
    print(f"  - HP: 7/7, AC: 13")
    print(f"  - DEX: 14 (+2)")

    # Test 1: Start Combat
    print("\n4. Starting combat...")
    start_combat_handler = get_tool_handler('start_combat')
    result = start_combat_handler(engine, player.id, {
        'participant_names': ['Thorin Ironshield', 'Goblin Scout'],
        'description': 'The goblin leaps from the shadows!'
    })

    if result['success']:
        print("✓ Combat started successfully")
        print(f"  Initiative order:")
        for i, combatant in enumerate(result['data']['initiative_order'], 1):
            print(f"    {i}. {combatant['name']} (Initiative: {combatant['initiative']})")
    else:
        print(f"❌ Failed to start combat: {result['message']}")
        return False

    # Test 2: Resolve Attack (Player attacks Goblin)
    print("\n5. Player attacks goblin...")
    resolve_attack_handler = get_tool_handler('resolve_attack')
    result = resolve_attack_handler(engine, player.id, {
        'attacker_name': 'Thorin Ironshield',
        'target_name': 'Goblin Scout',
        'attack_type': 'melee',
        'damage_type': 'slashing'
    })

    if result['success']:
        print(f"✓ {result['message']}")
        data = result['data']
        print(f"  Attack roll: {data['attack_roll']} vs AC {data['target_ac']}")
        if data['hit']:
            print(f"  Damage: {data['damage_dealt']} {data['damage_type']}")

        # Check goblin health
        goblin_health = engine.get_component(goblin.id, 'Health')
        print(f"  Goblin HP: {goblin_health.data['current_hp']}/{goblin_health.data['max_hp']}")
    else:
        print(f"❌ Attack failed: {result['message']}")
        return False

    # Test 3: Apply Condition
    print("\n6. Applying poisoned condition to goblin...")
    apply_condition_handler = get_tool_handler('apply_condition')
    result = apply_condition_handler(engine, player.id, {
        'target_name': 'Goblin Scout',
        'condition_name': 'Poisoned',
        'condition_description': 'Has disadvantage on attack rolls and ability checks',
        'duration_type': 'rounds',
        'duration_remaining': 3
    })

    if result['success']:
        print(f"✓ {result['message']}")
    else:
        print(f"❌ Failed to apply condition: {result['message']}")

    # Test 4: End Turn
    print("\n7. Ending player's turn...")
    end_turn_handler = get_tool_handler('end_turn')
    result = end_turn_handler(engine, player.id, {
        'entity_name': 'Thorin Ironshield'
    })

    if result['success']:
        print(f"✓ Turn ended")
        print(f"  Next: {result['data']['next_combatant']}")
        print(f"  Round: {result['data']['round']}")
    else:
        print(f"❌ Failed to end turn: {result['message']}")

    # Test 5: Goblin attacks back (if still alive)
    goblin_health = engine.get_component(goblin.id, 'Health')
    if goblin_health.data['current_hp'] > 0:
        print("\n8. Goblin counter-attacks...")
        result = resolve_attack_handler(engine, player.id, {
            'attacker_name': 'Goblin Scout',
            'target_name': 'Thorin Ironshield',
            'attack_type': 'melee',
            'disadvantage': True  # Because poisoned
        })

        if result['success']:
            print(f"✓ {result['message']}")
            data = result['data']
            print(f"  Attack roll: {data['attack_roll']} vs AC {data['target_ac']}")
            if data['hit']:
                print(f"  Damage: {data['damage_dealt']} {data['damage_type']}")

            # Check player health
            player_health = engine.get_component(player.id, 'Health')
            print(f"  Player HP: {player_health.data['current_hp']}/{player_health.data['max_hp']}")
    else:
        print("\n8. Goblin is defeated, skipping its turn")

    # Test 6: End Combat
    print("\n9. Ending combat...")
    end_combat_handler = get_tool_handler('end_combat')
    result = end_combat_handler(engine, player.id, {
        'outcome': 'Player victorious'
    })

    if result['success']:
        print(f"✓ {result['message']}")
    else:
        print(f"❌ Failed to end combat: {result['message']}")

    # Verify combat cleanup
    print("\n10. Verifying combat cleanup...")
    player_init = engine.get_component(player.id, 'Initiative')
    goblin_init = engine.get_component(goblin.id, 'Initiative')

    if player_init is None and goblin_init is None:
        print("✓ Initiative components removed")
    else:
        print("⚠ Initiative components still present")

    print("\n" + "=" * 60)
    print("COMBAT INTEGRATION TEST COMPLETE")
    print("=" * 60)

    return True


if __name__ == '__main__':
    try:
        success = test_combat_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
