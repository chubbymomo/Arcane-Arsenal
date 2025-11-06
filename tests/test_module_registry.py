"""
Tests for generic module registry system.

Tests the ModuleRegistry class and storage methods that allow modules
to create custom registries without modifying core schema.
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


class TestModuleRegistry:
    """Test generic module registry functionality."""

    def test_create_registry(self, temp_world):
        """Test creating a registry via StateEngine."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        # Create a registry
        magic_registry = engine.create_registry('magic_schools', 'magic')

        # Verify it's a ModuleRegistry instance
        from src.modules.base import ModuleRegistry
        assert isinstance(magic_registry, ModuleRegistry)
        assert magic_registry.registry_name == 'magic_schools'
        assert magic_registry.module_name == 'magic'

    def test_register_values(self, temp_world):
        """Test registering values in a registry."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        # Create registry and register values
        magic_registry = engine.create_registry('magic_schools', 'magic')
        magic_registry.register('evocation', 'Evocation magic', {'category': 'arcane'})
        magic_registry.register('necromancy', 'Necromancy magic', {'category': 'dark'})
        magic_registry.register('conjuration', 'Conjuration magic', {'category': 'arcane'})

        # Get all values
        values = magic_registry.get_all()
        assert len(values) == 3

        # Check structure
        evocation = next(v for v in values if v['key'] == 'evocation')
        assert evocation['description'] == 'Evocation magic'
        assert evocation['module'] == 'magic'
        assert evocation['metadata']['category'] == 'arcane'

    def test_get_keys(self, temp_world):
        """Test getting all keys from a registry."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        damage_registry = engine.create_registry('damage_types', 'combat')
        damage_registry.register('fire', 'Fire damage')
        damage_registry.register('cold', 'Cold damage')
        damage_registry.register('slashing', 'Slashing damage')

        keys = damage_registry.get_keys()
        assert sorted(keys) == ['cold', 'fire', 'slashing']

    def test_is_valid(self, temp_world):
        """Test checking if a key is valid."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        armor_registry = engine.create_registry('armor_types', 'equipment')
        armor_registry.register('light', 'Light armor')
        armor_registry.register('medium', 'Medium armor')
        armor_registry.register('heavy', 'Heavy armor')

        # Valid keys
        assert armor_registry.is_valid('light')
        assert armor_registry.is_valid('medium')
        assert armor_registry.is_valid('heavy')

        # Invalid keys
        assert not armor_registry.is_valid('super_heavy')
        assert not armor_registry.is_valid('Light')  # Case sensitive
        assert not armor_registry.is_valid('')

    def test_validate(self, temp_world):
        """Test validate() method raises on invalid keys."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        damage_registry = engine.create_registry('damage_types', 'combat')
        damage_registry.register('fire', 'Fire damage')
        damage_registry.register('cold', 'Cold damage')

        # Valid key - should not raise
        damage_registry.validate('fire')
        damage_registry.validate('cold')

        # Invalid key - should raise
        with pytest.raises(ValueError) as exc_info:
            damage_registry.validate('poison')

        error_message = str(exc_info.value)
        assert 'Invalid damage_types' in error_message
        assert 'poison' in error_message
        assert 'cold, fire' in error_message  # Shows valid options
        assert '/api/registries/damage_types' in error_message  # Shows API endpoint

    def test_validate_with_context(self, temp_world):
        """Test validate() with error context."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        school_registry = engine.create_registry('magic_schools', 'magic')
        school_registry.register('evocation', 'Evocation magic')

        # Invalid with context
        with pytest.raises(ValueError) as exc_info:
            school_registry.validate('illusion', 'spell school field')

        error_message = str(exc_info.value)
        assert 'spell school field' in error_message

    def test_multiple_registries(self, temp_world):
        """Test creating multiple independent registries."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        # Create multiple registries
        magic_registry = engine.create_registry('magic_schools', 'magic')
        damage_registry = engine.create_registry('damage_types', 'combat')
        armor_registry = engine.create_registry('armor_types', 'equipment')

        # Register values
        magic_registry.register('evocation', 'Evocation magic')
        damage_registry.register('fire', 'Fire damage')
        armor_registry.register('light', 'Light armor')

        # Verify independence
        assert magic_registry.get_keys() == ['evocation']
        assert damage_registry.get_keys() == ['fire']
        assert armor_registry.get_keys() == ['light']

        # Verify storage has all registries
        registry_names = engine.storage.get_registry_names()
        assert sorted(registry_names) == ['armor_types', 'damage_types', 'magic_schools']

    def test_registry_replace_value(self, temp_world):
        """Test that registering same key replaces the value."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        registry = engine.create_registry('test_registry', 'test')

        # Register initial value
        registry.register('key1', 'Original description')
        assert len(registry.get_all()) == 1
        assert registry.get_all()[0]['description'] == 'Original description'

        # Replace with new value
        registry.register('key1', 'Updated description', {'new_field': 'value'})
        assert len(registry.get_all()) == 1  # Still only one entry
        updated = registry.get_all()[0]
        assert updated['description'] == 'Updated description'
        assert updated['metadata']['new_field'] == 'value'

    def test_storage_methods_directly(self, temp_world):
        """Test storage methods for generic registries directly."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        # Register values directly via storage
        engine.storage.register_in_registry(
            registry_name='test_registry',
            key='value1',
            description='Test value 1',
            module='test_module',
            metadata={'category': 'test'}
        )

        engine.storage.register_in_registry(
            registry_name='test_registry',
            key='value2',
            description='Test value 2',
            module='test_module',
            metadata={'category': 'test'}
        )

        # Get values
        values = engine.storage.get_registry_values('test_registry')
        assert len(values) == 2

        # Get registry names
        names = engine.storage.get_registry_names()
        assert 'test_registry' in names

    def test_empty_registry(self, temp_world):
        """Test querying an empty registry."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        # Create registry but don't register anything
        registry = engine.create_registry('empty_registry', 'test')

        # Should return empty lists
        assert registry.get_all() == []
        assert registry.get_keys() == []

        # Should not appear in registry names (no values registered)
        names = engine.storage.get_registry_names()
        assert 'empty_registry' not in names

    def test_metadata_optional(self, temp_world):
        """Test that metadata is optional when registering values."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=[]
        )

        registry = engine.create_registry('test_registry', 'test')

        # Register without metadata
        registry.register('key1', 'Description without metadata')

        # Register with metadata
        registry.register('key2', 'Description with metadata', {'extra': 'data'})

        values = registry.get_all()
        assert len(values) == 2

        # First entry should have None or empty metadata
        key1 = next(v for v in values if v['key'] == 'key1')
        assert key1['metadata'] is None

        # Second entry should have metadata
        key2 = next(v for v in values if v['key'] == 'key2')
        assert key2['metadata'] == {'extra': 'data'}
