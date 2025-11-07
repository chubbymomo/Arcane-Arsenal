"""
Module system base classes for Arcane Arsenal.

Provides the interfaces that modules must implement to register component types,
relationship types, and event types with the core engine.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


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

    def validate_with_engine(self, data: Dict[str, Any], engine: 'StateEngine') -> bool:
        """
        Optional: Additional validation against engine state.

        Override this to validate component data against registered types,
        existing entities, or other engine state.

        Args:
            data: Component data to validate
            engine: StateEngine instance for querying registered types

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails with descriptive message

        Example:
            def validate_with_engine(self, data, engine):
                valid_types = {rt['type'] for rt in engine.storage.get_roll_types()}
                if data['roll_type'] not in valid_types:
                    raise ValueError(f"Invalid roll_type. Must be one of: {valid_types}")
                return True
        """
        # Default: no additional validation
        return True

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Optional: Return UI rendering hints for component fields.

        Override this to provide field-level metadata for web UI rendering.
        This enables schema-aware form generation with proper input types,
        labels, help text, and validation constraints.

        Returns:
            Dict mapping field names to UI metadata dictionaries

        Example:
            {
                "strength": {
                    "label": "Strength",
                    "widget": "number",
                    "order": 0,
                    "help_text": "Physical power and muscle",
                    "min": 1,
                    "max": 20,
                    "group": "Attributes"
                },
                "armor_type": {
                    "label": "Armor Type",
                    "widget": "select",
                    "order": 10,
                    "registry": "armor_types",
                    "help_text": "Type of armor worn",
                    "group": "Equipment"
                }
            }

        Widget types:
            - "text": Text input field
            - "textarea": Multi-line text area
            - "number": Number input with step controls
            - "range": Slider control (requires min/max)
            - "select": Dropdown from registry or enum
            - "checkbox": Boolean toggle
            - "multi-select": Multiple selection from registry

        Metadata keys:
            - label (str): Human-readable field label
            - widget (str): UI control type
            - order (int): Display order (lower = first)
            - help_text (str): Description/tooltip text
            - group (str): Grouping for organization (e.g., "Basic", "Advanced", "Combat")
            - registry (str): For select widgets, which registry to query
            - min (int/float): Minimum value for number/range
            - max (int/float): Maximum value for number/range
            - step (int/float): Step increment for number/range
            - placeholder (str): Placeholder text for text inputs
            - required (bool): Whether field is required (inferred from schema if omitted)
        """
        # Default: no UI metadata (will fall back to JSON textarea)
        return {}

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """
        Optional: Declare how this component appears on character sheets.

        Override this to control whether and how this component appears on
        character sheets. The category must be a registered value in the
        'character_sheet_categories' registry.

        Returns:
            Dict with character sheet configuration

        Example:
            {
                "visible": True,              # Should appear on character sheets
                "category": "combat",         # Category (validated against registry)
                "priority": 10,               # Display order within category (lower = higher)
                "display_mode": "full",       # "full", "compact", or "inline"
                "icon": "shield"              # Optional icon identifier
            }

        Configuration keys:
            - visible (bool): Whether to show on character sheets (default: True)
            - category (str): Category key from character_sheet_categories registry
                            (default: "misc")
            - priority (int): Display order within category, lower numbers appear first
                            (default: 100)
            - display_mode (str): How to render the component
                - "full": Complete display with all fields
                - "compact": Condensed view
                - "inline": Single-line display
                (default: "full")
            - icon (str): Optional icon identifier for UI (default: None)

        Notes:
            - Components with visible=False will not appear on character sheets
            - Category must be registered in character_sheet_categories registry
            - Components without this method default to misc category with low priority
        """
        # Default: visible in misc category with low priority
        return {
            "visible": True,
            "category": "misc",
            "priority": 100,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine: 'StateEngine' = None, entity_id: str = None) -> Optional[str]:
        """
        Optional: Provide custom HTML rendering for character sheet display.

        Override this to provide custom HTML rendering logic for how this
        component appears on character sheets. If not overridden or returns None,
        FormBuilder will use generic field-by-field display.

        Args:
            data: Component data to render
            engine: Optional StateEngine instance for querying related entities
            entity_id: Optional entity ID for interactive features (dice rolling, etc.)

        Returns:
            HTML string for rendering, or None to use default rendering

        Example (Attributes component with dice rolling):
            def get_character_sheet_renderer(self, data, engine=None, entity_id=None):
                html = ['<div class="attributes-grid">']
                for attr in ['strength', 'dexterity', 'constitution']:
                    score = data.get(attr, 10)
                    mod = (score - 10) // 2
                    mod_str = f"+{mod}" if mod >= 0 else str(mod)

                    # Dice button if entity_id provided
                    dice_btn = ''
                    if entity_id:
                        dice_btn = f'''
                            <button class="btn-roll-dice"
                                    @click="roll('1d20{mod_str}', entityId, 'ability_check', '{attr.upper()} Check')">
                                🎲 Roll
                            </button>
                        '''

                    html.append(f'''
                        <div class="attribute">
                            <div class="attr-name">{attr.upper()}</div>
                            <div class="attr-score">{score}</div>
                            <div class="attr-mod">{mod_str}</div>
                            {dice_btn}
                        </div>
                    ''')
                html.append('</div>')
                return ''.join(html)

        Notes:
            - Return None to use default FormBuilder rendering
            - HTML should be properly escaped for user-provided data
            - Can use engine to query related entities (e.g., equipped items)
            - Use entity_id for interactive features like dice rolling
            - Component should work with or without engine/entity_id parameters
        """
        # Default: use generic FormBuilder rendering
        return None


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


class ModuleRegistry:
    """
    Generic registry for module-defined enumerated values.

    Provides a convenient interface for modules to create and manage
    custom registries without modifying core schema. Modules can define
    registries for concepts like magic_schools, damage_types, armor_types, etc.

    Example:
        # In a module's initialize() method:
        magic_registry = engine.create_registry('magic_schools', self.name)
        magic_registry.register('evocation', 'Evocation magic', {'category': 'arcane'})
        magic_registry.register('necromancy', 'Necromancy magic', {'category': 'dark'})

        # Query registered values:
        schools = magic_registry.get_all()
        # Returns: [
        #   {'key': 'evocation', 'description': '...', 'module': 'magic', 'metadata': {'category': 'arcane'}},
        #   ...
        # ]

        # Validate against registry:
        if not magic_registry.is_valid('illusion'):
            raise ValueError(f"Invalid school. Must be one of: {magic_registry.get_keys()}")

    Attributes:
        registry_name: Name of this registry (e.g., 'magic_schools')
        module_name: Which module owns this registry
        storage: Storage instance for database access
    """

    def __init__(self, registry_name: str, module_name: str, storage):
        """
        Initialize a module registry.

        Args:
            registry_name: Name of the registry (e.g., 'magic_schools')
            module_name: Which module owns this registry
            storage: Storage instance for database operations
        """
        self.registry_name = registry_name
        self.module_name = module_name
        self.storage = storage

    def register(self, key: str, description: str,
                metadata: Dict[str, Any] = None) -> None:
        """
        Register a value in this registry.

        Args:
            key: Unique key within this registry (e.g., 'evocation')
            description: Human-readable description
            metadata: Optional extra data (e.g., {'category': 'arcane', 'damage_bonus': 2})
        """
        self.storage.register_in_registry(
            registry_name=self.registry_name,
            key=key,
            description=description,
            module=self.module_name,
            metadata=metadata
        )

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all registered values in this registry.

        Returns:
            List of dicts with keys: key, description, module, metadata
        """
        return self.storage.get_registry_values(self.registry_name)

    def get_keys(self) -> List[str]:
        """
        Get all registered keys in this registry.

        Returns:
            List of keys (e.g., ['evocation', 'necromancy', 'conjuration'])
        """
        return [entry['key'] for entry in self.get_all()]

    def is_valid(self, key: str) -> bool:
        """
        Check if a key is registered in this registry.

        Args:
            key: Key to check

        Returns:
            True if key is registered, False otherwise
        """
        return key in self.get_keys()

    def validate(self, key: str, error_context: str = None) -> None:
        """
        Validate that a key exists in this registry, raise ValueError if not.

        Args:
            key: Key to validate
            error_context: Optional context for error message (e.g., 'magic_school field')

        Raises:
            ValueError: If key is not registered
        """
        if not self.is_valid(key):
            context = f" in {error_context}" if error_context else ""
            valid_keys = ', '.join(sorted(self.get_keys()))
            raise ValueError(
                f"Invalid {self.registry_name} '{key}'{context}. "
                f"Must be one of: {valid_keys}. "
                f"Query /api/registries/{self.registry_name} to see all valid values."
            )


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

    def register_web_resources(self) -> Dict[str, Any]:
        """
        Register frontend resources (JavaScript, CSS, Web Components) for this module.

        This allows modules to ship custom UI elements, components, and styling
        that integrate seamlessly with the web interface.

        Returns:
            Dict with keys:
            - scripts: List[str] - Paths to JavaScript files
            - styles: List[str] - Paths to CSS files
            - components: List[str] - Names of Web Components defined by this module

        Example:
            def register_web_resources(self) -> Dict[str, Any]:
                return {
                    'scripts': [
                        '/static/modules/spells/spell-list.js',
                        '/static/modules/spells/spell-effects.js'
                    ],
                    'styles': [
                        '/static/modules/spells/spells.css'
                    ],
                    'components': ['spell-list', 'spell-slot-tracker', 'spell-book']
                }

        File organization:
            src/modules/my_module/
                __init__.py          # Module definition
                components.py        # Component type definitions
                web/
                    my-component.js  # Web Component definition
                    styles.css       # Module-specific styles

            src/web/static/modules/my_module/
                my-component.js      # Symlink or copy of web/my-component.js
                styles.css           # Symlink or copy of web/styles.css

        Web Component template:
            // src/modules/my_module/web/my-component.js
            class MyComponent extends HTMLElement {
                connectedCallback() {
                    const entityId = this.getAttribute('entity-id');
                    this.render();
                }

                render() {
                    this.innerHTML = `
                        <div class="my-component">
                            <!-- Component HTML -->
                        </div>
                    `;
                }
            }
            customElements.define('my-component', MyComponent);

        Notes:
            - Scripts are loaded in order
            - Components should use custom element names with hyphens
            - HTMX attributes work inside Web Components
            - Alpine.js can be used within components
            - Components have access to global socket for WebSocket
        """
        return {
            'scripts': [],
            'styles': [],
            'components': []
        }
