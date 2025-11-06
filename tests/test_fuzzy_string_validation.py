"""
Tests for fuzzy string validation fixes.

Validates that component fields that reference other entities or use
specific formats are properly validated to prevent AI typos and errors.
"""

import pytest
import tempfile
import shutil
from src.core.state_engine import StateEngine


@pytest.fixture
def temp_world():
    """Create a temporary world for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestPositionValidation:
    """Test Position component region field validation."""

    def test_region_entity_id_valid(self, temp_world):
        """Test that valid entity IDs in region field are accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['core_components']
        )

        # Create parent entity (e.g., a tavern) with Position
        result = engine.create_entity("Tavern")
        assert result.success
        tavern_id = result.data['id']

        # Parent needs Position for hierarchical positioning to work
        result = engine.add_component(tavern_id, "Position", {
            "x": 0,
            "y": 0,
            "z": 0,
            "region": "overworld"
        })
        assert result.success

        # Create child entity (e.g., a table)
        result = engine.create_entity("Table")
        assert result.success
        table_id = result.data['id']

        # Add Position with valid entity ID as region
        result = engine.add_component(table_id, "Position", {
            "x": 5,
            "y": 3,
            "z": 0,
            "region": tavern_id  # Valid entity ID
        })

        assert result.success

    def test_region_entity_id_invalid(self, temp_world):
        """Test that invalid entity IDs in region field are rejected."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['core_components']
        )

        # Create entity
        result = engine.create_entity("Table")
        assert result.success
        table_id = result.data['id']

        # Try to add Position with non-existent entity ID as region
        result = engine.add_component(table_id, "Position", {
            "x": 5,
            "y": 3,
            "z": 0,
            "region": "entity_does_not_exist"  # Invalid - entity doesn't exist
        })

        # Should fail validation
        assert not result.success
        assert "does not exist" in result.error

    def test_region_named_area_accepted(self, temp_world):
        """Test that named regions (non-entity strings) are accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['core_components']
        )

        # Create entity
        result = engine.create_entity("Player")
        assert result.success
        player_id = result.data['id']

        # Add Position with named region
        result = engine.add_component(player_id, "Position", {
            "x": 100,
            "y": 200,
            "z": 0,
            "region": "overworld"  # Named region - should be accepted
        })

        assert result.success

        # Try various named regions
        for region_name in ["dungeon_level_1", "tavern_main_room", "inventory"]:
            result = engine.update_component(player_id, "Position", {
                "x": 100,
                "y": 200,
                "z": 0,
                "region": region_name
            })
            assert result.success

    def test_region_optional(self, temp_world):
        """Test that region field is optional."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['core_components']
        )

        # Create entity
        result = engine.create_entity("Item")
        assert result.success
        item_id = result.data['id']

        # Add Position without region
        result = engine.add_component(item_id, "Position", {
            "x": 0,
            "y": 0,
            "z": 0
        })

        assert result.success


class TestWeaponValidation:
    """Test Weapon component damage_dice field validation."""

    def test_damage_dice_valid_simple(self, temp_world):
        """Test that valid simple dice notation is accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Sword")
        assert result.success
        weapon_id = result.data['id']

        # Valid simple dice notations
        valid_notations = ['1d6', '1d8', '2d6', '1d20', '3d10']

        for notation in valid_notations:
            result = engine.add_component(weapon_id, "weapon", {
                "damage_dice": notation,
                "damage_type": "slashing"
            })

            # If component already exists, update it
            if not result.success and "already has" in result.error:
                result = engine.update_component(weapon_id, "weapon", {
                    "damage_dice": notation,
                    "damage_type": "slashing"
                })

            assert result.success, f"Failed for notation: {notation}"

    def test_damage_dice_valid_with_modifiers(self, temp_world):
        """Test that dice notation with modifiers is accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Magic Sword")
        assert result.success
        weapon_id = result.data['id']

        # Valid notations with modifiers
        valid_notations = ['1d8+3', '2d6+5', '1d20-2', '3d4+1']

        for notation in valid_notations:
            result = engine.add_component(weapon_id, "weapon", {
                "damage_dice": notation,
                "damage_type": "slashing"
            })

            if not result.success and "already has" in result.error:
                result = engine.update_component(weapon_id, "weapon", {
                    "damage_dice": notation,
                    "damage_type": "slashing"
                })

            assert result.success, f"Failed for notation: {notation}"

    def test_damage_dice_valid_complex(self, temp_world):
        """Test that complex dice notation is accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Flametongue")
        assert result.success
        weapon_id = result.data['id']

        # Complex notation (physical + fire damage)
        result = engine.add_component(weapon_id, "weapon", {
            "damage_dice": "1d8+2d6",  # 1d8 slashing + 2d6 fire
            "damage_type": "slashing"
        })

        assert result.success

    def test_damage_dice_invalid(self, temp_world):
        """Test that invalid dice notation is rejected."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Broken Weapon")
        assert result.success
        weapon_id = result.data['id']

        # Invalid notations that have no valid dice expression
        invalid_notations = [
            'abc',           # Not a dice notation
            'damage',        # Just a word
            'invalid_dice',  # Not dice notation
            'hello world',   # Random text
            'xyz123',        # Random alphanumeric
        ]

        for notation in invalid_notations:
            result = engine.add_component(weapon_id, "weapon", {
                "damage_dice": notation,
                "damage_type": "slashing"
            })

            # Should fail validation
            assert not result.success, f"Should have failed for: {notation}"
            # Error message should mention either "Invalid damage_dice", "validation", or "No valid dice"
            assert any(keyword in result.error for keyword in ["Invalid damage_dice", "validation", "No valid dice"]), \
                f"Unexpected error message: {result.error}"

    def test_damage_dice_required(self, temp_world):
        """Test that damage_dice is required."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Weapon")
        assert result.success
        weapon_id = result.data['id']

        # Try to add weapon without damage_dice
        result = engine.add_component(weapon_id, "weapon", {
            "damage_type": "slashing"
        })

        # Should fail (required field)
        assert not result.success


class TestArmorTypeValidation:
    """Test Armor component armor_type field validation."""

    def test_armor_type_valid(self, temp_world):
        """Test that valid armor types are accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create armor entity
        result = engine.create_entity("Plate Armor")
        assert result.success
        armor_id = result.data['id']

        # Valid armor types from registry: light, medium, heavy, shield
        valid_types = ['light', 'medium', 'heavy', 'shield']

        for armor_type in valid_types:
            result = engine.add_component(armor_id, "armor", {
                "armor_class": 15,
                "armor_type": armor_type
            })

            # If component already exists, update it
            if not result.success and "already has" in result.error:
                result = engine.update_component(armor_id, "armor", {
                    "armor_class": 15,
                    "armor_type": armor_type
                })

            assert result.success, f"Failed for armor_type: {armor_type}"

    def test_armor_type_invalid(self, temp_world):
        """Test that invalid armor types are rejected."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create armor entity
        result = engine.create_entity("Mystery Armor")
        assert result.success
        armor_id = result.data['id']

        # Invalid armor types
        invalid_types = ['super_heavy', 'cloth', 'leather', 'chainmail', 'invalid']

        for armor_type in invalid_types:
            result = engine.add_component(armor_id, "armor", {
                "armor_class": 15,
                "armor_type": armor_type
            })

            # Should fail validation
            assert not result.success, f"Should have failed for: {armor_type}"
            assert "Invalid armor_type" in result.error

    def test_armor_type_optional(self, temp_world):
        """Test that armor_type is optional."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create armor entity
        result = engine.create_entity("Generic Armor")
        assert result.success
        armor_id = result.data['id']

        # Add armor without armor_type (optional field)
        result = engine.add_component(armor_id, "armor", {
            "armor_class": 12
        })

        assert result.success


class TestDamageTypeValidation:
    """Test Weapon component damage_type field validation."""

    def test_damage_type_valid_physical(self, temp_world):
        """Test that valid physical damage types are accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Sword")
        assert result.success
        weapon_id = result.data['id']

        # Valid physical damage types
        physical_types = ['slashing', 'piercing', 'bludgeoning']

        for damage_type in physical_types:
            result = engine.add_component(weapon_id, "weapon", {
                "damage_dice": "1d8",
                "damage_type": damage_type
            })

            # If component already exists, update it
            if not result.success and "already has" in result.error:
                result = engine.update_component(weapon_id, "weapon", {
                    "damage_dice": "1d8",
                    "damage_type": damage_type
                })

            assert result.success, f"Failed for damage_type: {damage_type}"

    def test_damage_type_valid_elemental(self, temp_world):
        """Test that valid elemental damage types are accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Elemental Weapon")
        assert result.success
        weapon_id = result.data['id']

        # Valid elemental damage types
        elemental_types = ['fire', 'cold', 'lightning', 'thunder']

        for damage_type in elemental_types:
            result = engine.add_component(weapon_id, "weapon", {
                "damage_dice": "2d6",
                "damage_type": damage_type
            })

            if not result.success and "already has" in result.error:
                result = engine.update_component(weapon_id, "weapon", {
                    "damage_dice": "2d6",
                    "damage_type": damage_type
                })

            assert result.success, f"Failed for damage_type: {damage_type}"

    def test_damage_type_valid_magical(self, temp_world):
        """Test that valid magical damage types are accepted."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Magic Weapon")
        assert result.success
        weapon_id = result.data['id']

        # Valid magical damage types
        magical_types = ['acid', 'poison', 'necrotic', 'radiant', 'force', 'psychic']

        for damage_type in magical_types:
            result = engine.add_component(weapon_id, "weapon", {
                "damage_dice": "1d10",
                "damage_type": damage_type
            })

            if not result.success and "already has" in result.error:
                result = engine.update_component(weapon_id, "weapon", {
                    "damage_dice": "1d10",
                    "damage_type": damage_type
                })

            assert result.success, f"Failed for damage_type: {damage_type}"

    def test_damage_type_invalid(self, temp_world):
        """Test that invalid damage types are rejected."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Weird Weapon")
        assert result.success
        weapon_id = result.data['id']

        # Invalid damage types
        invalid_types = ['cutting', 'stabbing', 'magic', 'holy', 'dark', 'energy']

        for damage_type in invalid_types:
            result = engine.add_component(weapon_id, "weapon", {
                "damage_dice": "1d6",
                "damage_type": damage_type
            })

            # Should fail validation
            assert not result.success, f"Should have failed for: {damage_type}"
            assert "Invalid damage_type" in result.error

    def test_damage_type_required(self, temp_world):
        """Test that damage_type is required."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon entity
        result = engine.create_entity("Weapon")
        assert result.success
        weapon_id = result.data['id']

        # Try to add weapon without damage_type (required field)
        result = engine.add_component(weapon_id, "weapon", {
            "damage_dice": "1d8"
        })

        # Should fail (required field)
        assert not result.success


class TestUpdateValidation:
    """Test that validation also applies when updating components."""

    def test_position_update_validation(self, temp_world):
        """Test that updating Position validates region field."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['core_components']
        )

        # Create entity with valid Position
        result = engine.create_entity("Item")
        assert result.success
        item_id = result.data['id']

        result = engine.add_component(item_id, "Position", {
            "x": 0,
            "y": 0,
            "region": "tavern"
        })
        assert result.success

        # Try to update with invalid entity ID
        result = engine.update_component(item_id, "Position", {
            "x": 10,
            "y": 20,
            "region": "entity_invalid_id"
        })

        # Should fail validation
        assert not result.success
        assert "does not exist" in result.error

    def test_weapon_update_validation(self, temp_world):
        """Test that updating Weapon validates damage_dice field."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['fantasy_combat']
        )

        # Create weapon with valid dice
        result = engine.create_entity("Sword")
        assert result.success
        weapon_id = result.data['id']

        result = engine.add_component(weapon_id, "weapon", {
            "damage_dice": "1d8",
            "damage_type": "slashing"
        })
        assert result.success

        # Try to update with invalid notation
        result = engine.update_component(weapon_id, "weapon", {
            "damage_dice": "invalid_dice",
            "damage_type": "slashing"
        })

        # Should fail validation
        assert not result.success
        # Error message should mention either "Invalid damage_dice" or "No valid dice"
        assert any(keyword in result.error for keyword in ["Invalid damage_dice", "No valid dice"]), \
            f"Unexpected error message: {result.error}"
