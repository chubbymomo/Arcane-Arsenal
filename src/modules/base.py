"""
Module system base classes for Arcane Arsenal.

Provides the interfaces that modules must implement to register component types,
relationship types, and event types with the core engine.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ComponentTypeDefinition(ABC):
    """
    Defines a component type with validation.

    Subclasses define the type, description, schema, and validation logic
    for a specific component type.

    Attributes:
        type: Unique name for this component type
        description: Human-readable description
        schema_version: Version of the schema (semver)
        module: Which module provides this type
    """

    type: str
    description: str
    schema_version: str
    module: str

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Return JSON Schema for validation.

        Returns:
            JSON Schema dict defining the structure of component data

        Example:
            {
                "type": "object",
                "properties": {
                    "hp": {"type": "number"},
                    "max_hp": {"type": "number"}
                },
                "required": ["hp", "max_hp"]
            }
        """
        pass

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate component data against schema.

        Args:
            data: Component data to validate

        Returns:
            True if valid

        Raises:
            jsonschema.ValidationError: If validation fails
        """
        import jsonschema
        jsonschema.validate(data, self.get_schema())
        return True


class RelationshipTypeDefinition(ABC):
    """
    Defines a relationship type with validation.

    Subclasses define the type, description, and validation logic
    for a specific relationship type.

    Attributes:
        type: Unique name for this relationship type
        description: Human-readable description
        module: Which module provides this type
    """

    type: str
    description: str
    module: str

    def validate_from_entity(self, entity: 'Entity') -> bool:
        """
        Override to validate from_entity has required components.

        Args:
            entity: Source entity

        Returns:
            True if entity can be source of this relationship

        Example:
            For 'equipped_by', validate that from_entity has Equipment component
        """
        return True

    def validate_to_entity(self, entity: 'Entity') -> bool:
        """
        Override to validate to_entity has required components.

        Args:
            entity: Target entity

        Returns:
            True if entity can be target of this relationship

        Example:
            For 'located_at', validate that to_entity has Position component
        """
        return True


class EventTypeDefinition:
    """
    Defines an event type.

    Simple container for event type metadata.

    Attributes:
        type: Unique name for this event type
        description: Human-readable description
        module: Which module provides this type
        data_schema: Optional JSON Schema for event.data
    """

    def __init__(self, type: str, description: str, module: str,
                 data_schema: Dict[str, Any] = None):
        """
        Initialize event type definition.

        Args:
            type: Event type name
            description: Human-readable description
            module: Which module provides this
            data_schema: Optional JSON Schema for event data
        """
        self.type = type
        self.description = description
        self.module = module
        self.data_schema = data_schema or {}


class RollTypeDefinition:
    """
    Defines a valid roll type for the RNG system.

    Roll types are enumerated values that modules can register to define
    what kinds of rolls are valid. This prevents AI from generating invalid
    roll type strings and provides a clear contract.

    Attributes:
        type: Unique identifier for this roll type (e.g., 'attack', 'skill_check')
        description: Human-readable description
        module: Which module provides this type
        category: Optional grouping (e.g., 'combat', 'skill', 'saving_throw')

    Examples:
        RollTypeDefinition('attack', 'Attack roll to hit a target', 'rng', 'combat')
        RollTypeDefinition('stealth_check', 'Stealth skill check', 'skills', 'skill')
    """

    def __init__(self, type: str, description: str, module: str,
                 category: str = None):
        """
        Initialize roll type definition.

        Args:
            type: Roll type identifier (e.g., 'attack', 'damage')
            description: Human-readable description
            module: Which module provides this
            category: Optional category for grouping
        """
        self.type = type
        self.description = description
        self.module = module
        self.category = category or 'general'


class Module(ABC):
    """
    Base class for all modules.

    Modules extend the core engine with new component types, relationship types,
    and game-specific logic.

    To create a module:
    1. Subclass Module
    2. Implement name and version properties
    3. Implement register_* methods to provide types
    4. Optional: implement dependencies() to specify required modules
    5. Optional: implement initialize() for setup
    6. Optional: implement on_event() to react to events
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Module name (e.g., 'core_components')"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Module version (semver, e.g., '1.0.0')"""
        pass

    @property
    def display_name(self) -> str:
        """
        Human-readable display name for this module.

        Override to provide a more descriptive name for UIs.
        Defaults to the module name.
        """
        return self.name.replace('_', ' ').title()

    @property
    def description(self) -> str:
        """
        Description of what this module provides.

        Override to provide detailed information about the module.
        """
        return f"{self.display_name} module"

    @property
    def is_core(self) -> bool:
        """
        Whether this is a core module that cannot be disabled.

        Core modules are required for basic functionality and are
        automatically included in all worlds.
        """
        return False

    def dependencies(self) -> List[str]:
        """
        Return list of module names that this module depends on.

        Dependencies will be loaded before this module, and users cannot
        enable this module without also enabling its dependencies.

        Returns:
            List of module names (e.g., ['core_components', 'stats'])

        Example:
            def dependencies(self) -> List[str]:
                return ['core_components', 'stats']
        """
        return []

    def initialize(self, engine: 'StateEngine') -> None:
        """
        Called when module is loaded.

        Override to perform initialization tasks like:
        - Creating default entities
        - Setting up event listeners
        - Loading configuration

        Args:
            engine: StateEngine instance
        """
        pass

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """
        Return component types this module provides.

        Returns:
            List of ComponentTypeDefinition instances

        Example:
            return [HealthComponent(), InventoryComponent()]
        """
        return []

    def register_relationship_types(self) -> List[RelationshipTypeDefinition]:
        """
        Return relationship types this module provides.

        Returns:
            List of RelationshipTypeDefinition instances

        Example:
            return [EquippedByRelationship(), ContainsRelationship()]
        """
        return []

    def register_event_types(self) -> List[EventTypeDefinition]:
        """
        Return event types this module provides.

        Returns:
            List of EventTypeDefinition instances

        Example:
            return [
                EventTypeDefinition('item.used', 'Item was used', 'inventory'),
                EventTypeDefinition('damage.taken', 'Entity took damage', 'combat')
            ]
        """
        return []

    def register_roll_types(self) -> List[RollTypeDefinition]:
        """
        Return roll types this module provides.

        Roll types define valid values for roll_type in the RNG system.
        This prevents AI from generating invalid roll type strings.

        Returns:
            List of RollTypeDefinition instances

        Example:
            return [
                RollTypeDefinition('attack', 'Attack roll to hit', 'combat', 'combat'),
                RollTypeDefinition('damage', 'Damage roll', 'combat', 'combat'),
                RollTypeDefinition('stealth_check', 'Stealth skill check', 'skills', 'skill')
            ]
        """
        return []

    def on_event(self, event: 'Event') -> None:
        """
        Optional: React to events.

        Override to implement game logic that responds to state changes.

        Args:
            event: Event that occurred

        Example:
            if event.event_type == 'component.updated':
                # Check if HP dropped to 0
                # Emit character.died event
        """
        pass
