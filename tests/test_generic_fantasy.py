"""
Tests for Generic Fantasy module.

Validates attributes, character details, skills, and other fantasy components.
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


class TestAttributesComponent:
    """Test Attributes component functionality."""

    def test_attributes_component_registration(self, temp_world):
        """Test that Attributes component registers correctly."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        # Check that Attributes component is registered
        component_types = engine.storage.get_component_types()
        attr_types = [ct for ct in component_types if ct['type'] == 'Attributes']

        assert len(attr_types) == 1
        assert attr_types[0]['module'] == 'generic_fantasy'
        assert attr_types[0]['description'] == "Core ability scores (STR, DEX, CON, INT, WIS, CHA)"

    def test_attributes_valid_creation(self, temp_world):
        """Test creating an entity with valid attributes."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        # Create entity
        result = engine.create_entity("Test Character")
        assert result.success
        entity_id = result.data['id']

        # Add attributes
        result = engine.add_component(entity_id, "Attributes", {
            "strength": 16,
            "dexterity": 14,
            "constitution": 15,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 8
        })

        assert result.success

    def test_attributes_validation_min_max(self, temp_world):
        """Test that attributes validate minimum and maximum values."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        result = engine.create_entity("Test Character")
        entity_id = result.data['id']

        # Test value too low
        result = engine.add_component(entity_id, "Attributes", {
            "strength": 0,  # Below minimum
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10
        })

        assert not result.success
        # Check for validation error (either JSON schema or custom validation)
        assert "minimum" in result.error.lower() or "must be between" in result.error.lower()

    def test_attributes_required_fields(self, temp_world):
        """Test that all attribute fields are required."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        result = engine.create_entity("Test Character")
        entity_id = result.data['id']

        # Missing charisma
        result = engine.add_component(entity_id, "Attributes", {
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10
            # Missing charisma
        })

        assert not result.success

    def test_attributes_ui_metadata(self, temp_world):
        """Test that Attributes component provides UI metadata."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        # Get component definition from component validators
        comp_def = engine.component_validators.get('Attributes')
        assert comp_def is not None

        # Get UI metadata
        ui_metadata = comp_def.get_ui_metadata()

        # Check that all attributes have UI metadata
        for attr in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            assert attr in ui_metadata
            assert 'label' in ui_metadata[attr]
            assert 'widget' in ui_metadata[attr]
            assert ui_metadata[attr]['widget'] == 'number'
            assert 'min' in ui_metadata[attr]
            assert 'max' in ui_metadata[attr]
            assert 'group' in ui_metadata[attr]

    def test_attributes_modifier_calculation(self, temp_world):
        """Test the static modifier calculation method."""
        from src.modules.generic_fantasy.attributes import AttributesComponent

        # Standard scores and modifiers
        assert AttributesComponent.calculate_modifier(1) == -5
        assert AttributesComponent.calculate_modifier(8) == -1
        assert AttributesComponent.calculate_modifier(10) == 0
        assert AttributesComponent.calculate_modifier(12) == 1
        assert AttributesComponent.calculate_modifier(16) == 3
        assert AttributesComponent.calculate_modifier(20) == 5
        assert AttributesComponent.calculate_modifier(30) == 10


class TestGenericFantasyRegistries:
    """Test that registries are created correctly."""

    def test_races_registry(self, temp_world):
        """Test that races registry is populated."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        # Get races registry
        races = engine.create_registry('races', 'generic_fantasy')
        all_races = races.get_all()

        # Should have at least 6 races
        assert len(all_races) >= 6

        # Check that human exists
        human = next((r for r in all_races if r['key'] == 'human'), None)
        assert human is not None
        assert 'Human' in human['description']

    def test_classes_registry(self, temp_world):
        """Test that classes registry is populated."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        classes = engine.create_registry('classes', 'generic_fantasy')
        all_classes = classes.get_all()

        # Should have at least 8 classes
        assert len(all_classes) >= 8

        # Check that fighter exists
        fighter = next((c for c in all_classes if c['key'] == 'fighter'), None)
        assert fighter is not None
        assert 'Fighter' in fighter['description']

    def test_skills_registry(self, temp_world):
        """Test that skills registry is populated."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        skills = engine.create_registry('skill_types', 'generic_fantasy')
        all_skills = skills.get_all()

        # Should have 18 skills
        assert len(all_skills) >= 18

        # Check a few key skills
        athletics = next((s for s in all_skills if s['key'] == 'athletics'), None)
        assert athletics is not None
        assert athletics['metadata']['ability'] == 'strength'

        stealth = next((s for s in all_skills if s['key'] == 'stealth'), None)
        assert stealth is not None
        assert stealth['metadata']['ability'] == 'dexterity'

    def test_alignments_registry(self, temp_world):
        """Test that alignments registry is populated."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        alignments = engine.create_registry('alignments', 'generic_fantasy')
        all_alignments = alignments.get_all()

        # Should have 9 alignments
        assert len(all_alignments) == 9

        # Check that lawful good exists
        lg = next((a for a in all_alignments if a['key'] == 'lawful_good'), None)
        assert lg is not None
        assert 'Lawful Good' in lg['description']


class TestModuleDependencies:
    """Test module dependency resolution."""

    def test_generic_fantasy_dependencies(self, temp_world):
        """Test that generic_fantasy correctly loads with dependencies."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['generic_fantasy']
        )

        # Get loaded modules from component types
        component_types = engine.storage.get_component_types()
        loaded_modules = {ct['module'] for ct in component_types}

        # Should have loaded: core_components, fantasy_combat, rng, generic_fantasy
        assert 'core_components' in loaded_modules
        assert 'fantasy_combat' in loaded_modules
        assert 'rng' in loaded_modules
        assert 'generic_fantasy' in loaded_modules
