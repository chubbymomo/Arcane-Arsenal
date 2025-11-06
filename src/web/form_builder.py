"""
Form Builder - Schema-aware form generation for component types.

Generates HTML forms from component schemas and UI metadata, supporting:
- Registry-based dropdowns
- Proper HTML5 input types with validation
- Field grouping and ordering
- Help text and labels
"""

from typing import Dict, Any, Optional, List
from markupsafe import Markup, escape


class FormBuilder:
    """
    Builds HTML forms from component schemas and UI metadata.

    Usage:
        builder = FormBuilder(engine)
        html = builder.build_form('Attributes', {'str': 10, 'dex': 14})
    """

    def __init__(self, engine):
        """
        Initialize form builder with state engine for registry lookups.

        Args:
            engine: StateEngine instance
        """
        self.engine = engine

    def build_form(self, component_type: str, current_data: Optional[Dict[str, Any]] = None) -> Markup:
        """
        Build HTML form for a component type.

        Args:
            component_type: Component type name (e.g., 'Attributes')
            current_data: Current component data (for editing)

        Returns:
            Markup-safe HTML string
        """
        current_data = current_data or {}

        # Get component definition
        comp_def = self._get_component_definition(component_type)
        if not comp_def:
            return self._fallback_json_form(component_type, current_data)

        # Get UI metadata
        ui_metadata = comp_def.get_ui_metadata()
        if not ui_metadata:
            return self._fallback_json_form(component_type, current_data)

        # Get schema for field info
        schema = comp_def.get_schema()
        properties = schema.get('properties', {})
        required_fields = set(schema.get('required', []))

        # Group fields by group metadata
        grouped_fields = self._group_fields(ui_metadata, properties, required_fields, current_data)

        # Build HTML
        html_parts = []
        for group_name, fields in grouped_fields.items():
            if group_name:
                html_parts.append(f'<div class="form-group-section">')
                html_parts.append(f'<h4 class="form-group-title">{escape(group_name)}</h4>')

            for field_data in fields:
                html_parts.append(self._render_field(field_data))

            if group_name:
                html_parts.append('</div>')

        return Markup(''.join(html_parts))

    def build_display(self, component_type: str, data: Dict[str, Any]) -> Markup:
        """
        Build read-only display for a component.

        Args:
            component_type: Component type name
            data: Component data to display

        Returns:
            Markup-safe HTML string
        """
        comp_def = self._get_component_definition(component_type)
        if not comp_def:
            return self._fallback_json_display(data)

        ui_metadata = comp_def.get_ui_metadata()
        if not ui_metadata:
            return self._fallback_json_display(data)

        schema = comp_def.get_schema()
        properties = schema.get('properties', {})
        required_fields = set(schema.get('required', []))

        grouped_fields = self._group_fields(ui_metadata, properties, required_fields, data)

        html_parts = []
        for group_name, fields in grouped_fields.items():
            if group_name:
                html_parts.append(f'<div class="component-display-group">')
                html_parts.append(f'<h4>{escape(group_name)}</h4>')

            html_parts.append('<dl class="component-data">')
            for field_data in fields:
                html_parts.append(self._render_display_field(field_data))
            html_parts.append('</dl>')

            if group_name:
                html_parts.append('</div>')

        return Markup(''.join(html_parts))

    def _get_component_definition(self, component_type: str):
        """Get component definition from engine."""
        return self.engine.component_validators.get(component_type)

    def _group_fields(self, ui_metadata: Dict, properties: Dict, required: set, data: Dict) -> Dict[str, List[Dict]]:
        """Group fields by their group metadata and sort by order."""
        groups = {}

        for field_name, field_ui in ui_metadata.items():
            group_name = field_ui.get('group', '')
            order = field_ui.get('order', 999)

            field_data = {
                'name': field_name,
                'ui': field_ui,
                'schema': properties.get(field_name, {}),
                'required': field_name in required,
                'value': data.get(field_name),
                'order': order
            }

            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(field_data)

        # Sort fields within each group by order
        for group in groups.values():
            group.sort(key=lambda f: f['order'])

        # Sort groups: empty string group first, then alphabetically
        sorted_groups = {}
        if '' in groups:
            sorted_groups[''] = groups.pop('')
        for key in sorted(groups.keys()):
            sorted_groups[key] = groups[key]

        return sorted_groups

    def _render_field(self, field_data: Dict) -> str:
        """Render a single form field."""
        field_name = field_data['name']
        ui = field_data['ui']
        value = field_data['value']
        required = field_data['required']

        widget = ui.get('widget', 'text')
        label = escape(ui.get('label', field_name.replace('_', ' ').title()))
        help_text = ui.get('help_text', '')

        html = [f'<div class="form-group">']
        html.append(f'<label for="{escape(field_name)}">{label}')
        if required:
            html.append(' <span class="required">*</span>')
        html.append('</label>')

        if widget == 'number':
            html.append(self._render_number_input(field_name, value, ui))
        elif widget == 'select':
            html.append(self._render_select_input(field_name, value, ui))
        elif widget == 'textarea':
            html.append(self._render_textarea(field_name, value, ui))
        elif widget == 'checkbox':
            html.append(self._render_checkbox(field_name, value, ui))
        elif widget == 'range':
            html.append(self._render_range_input(field_name, value, ui))
        elif widget == 'multi-select':
            html.append(self._render_multiselect(field_name, value, ui))
        else:  # text
            html.append(self._render_text_input(field_name, value, ui))

        if help_text:
            html.append(f'<small class="form-text">{escape(help_text)}</small>')

        html.append('</div>')
        return ''.join(html)

    def _render_number_input(self, name: str, value: Any, ui: Dict) -> str:
        """Render number input field."""
        attrs = [
            f'type="number"',
            f'id="{escape(name)}"',
            f'name="{escape(name)}"',
            f'class="form-control"'
        ]

        if value is not None:
            attrs.append(f'value="{escape(str(value))}"')
        if 'min' in ui:
            attrs.append(f'min="{ui["min"]}"')
        if 'max' in ui:
            attrs.append(f'max="{ui["max"]}"')
        if 'step' in ui:
            attrs.append(f'step="{ui["step"]}"')
        if 'placeholder' in ui:
            attrs.append(f'placeholder="{escape(ui["placeholder"])}"')

        return f'<input {" ".join(attrs)}>'

    def _render_text_input(self, name: str, value: Any, ui: Dict) -> str:
        """Render text input field."""
        attrs = [
            f'type="text"',
            f'id="{escape(name)}"',
            f'name="{escape(name)}"',
            f'class="form-control"'
        ]

        if value is not None:
            attrs.append(f'value="{escape(str(value))}"')
        if 'placeholder' in ui:
            attrs.append(f'placeholder="{escape(ui["placeholder"])}"')

        return f'<input {" ".join(attrs)}>'

    def _render_textarea(self, name: str, value: Any, ui: Dict) -> str:
        """Render textarea field."""
        attrs = [
            f'id="{escape(name)}"',
            f'name="{escape(name)}"',
            f'class="form-control"',
            'rows="4"'
        ]

        if 'placeholder' in ui:
            attrs.append(f'placeholder="{escape(ui["placeholder"])}"')

        content = escape(str(value)) if value is not None else ''
        return f'<textarea {" ".join(attrs)}>{content}</textarea>'

    def _render_checkbox(self, name: str, value: Any, ui: Dict) -> str:
        """Render checkbox field."""
        checked = 'checked' if value else ''
        return f'''
            <div class="form-check">
                <input type="checkbox"
                       id="{escape(name)}"
                       name="{escape(name)}"
                       class="form-check-input"
                       {checked}>
            </div>
        '''

    def _render_range_input(self, name: str, value: Any, ui: Dict) -> str:
        """Render range slider field."""
        attrs = [
            f'type="range"',
            f'id="{escape(name)}"',
            f'name="{escape(name)}"',
            f'class="form-range"'
        ]

        if value is not None:
            attrs.append(f'value="{escape(str(value))}"')
        if 'min' in ui:
            attrs.append(f'min="{ui["min"]}"')
        if 'max' in ui:
            attrs.append(f'max="{ui["max"]}"')
        if 'step' in ui:
            attrs.append(f'step="{ui["step"]}"')

        current_val = value if value is not None else ui.get('min', 0)
        return f'<input {" ".join(attrs)}><span class="range-value">{current_val}</span>'

    def _render_select_input(self, name: str, value: Any, ui: Dict) -> str:
        """Render select dropdown field."""
        registry_name = ui.get('registry')
        if not registry_name:
            return f'<p class="text-danger">Error: select widget requires registry name</p>'

        # Get registry values
        try:
            registry = self.engine.create_registry(registry_name, 'generic_fantasy')
            options = registry.get_all()
        except:
            return f'<p class="text-danger">Error: registry "{escape(registry_name)}" not found</p>'

        html = [f'<select id="{escape(name)}" name="{escape(name)}" class="form-control">']
        html.append('<option value="">-- Select --</option>')

        for opt in options:
            selected = 'selected' if value == opt['key'] else ''
            html.append(f'<option value="{escape(opt["key"])}" {selected}>{escape(opt["description"])}</option>')

        html.append('</select>')
        return ''.join(html)

    def _render_multiselect(self, name: str, value: Any, ui: Dict) -> str:
        """Render multi-select checkboxes."""
        registry_name = ui.get('registry')
        if not registry_name:
            return f'<p class="text-danger">Error: multi-select widget requires registry name</p>'

        try:
            registry = self.engine.create_registry(registry_name, 'generic_fantasy')
            options = registry.get_all()
        except:
            return f'<p class="text-danger">Error: registry "{escape(registry_name)}" not found</p>'

        value_list = value if isinstance(value, list) else []

        html = ['<div class="multi-select-group">']
        for opt in options:
            checked = 'checked' if opt['key'] in value_list else ''
            html.append(f'''
                <div class="form-check">
                    <input type="checkbox"
                           id="{escape(name)}_{escape(opt['key'])}"
                           name="{escape(name)}"
                           value="{escape(opt['key'])}"
                           class="form-check-input"
                           {checked}>
                    <label class="form-check-label" for="{escape(name)}_{escape(opt['key'])}">
                        {escape(opt['description'])}
                    </label>
                </div>
            ''')
        html.append('</div>')
        return ''.join(html)

    def _render_display_field(self, field_data: Dict) -> str:
        """Render a single field for read-only display."""
        field_name = field_data['name']
        ui = field_data['ui']
        value = field_data['value']

        label = escape(ui.get('label', field_name.replace('_', ' ').title()))

        # Format value based on type
        if value is None:
            display_value = '<em>Not set</em>'
        elif isinstance(value, bool):
            display_value = '✓ Yes' if value else '✗ No'
        elif isinstance(value, list):
            display_value = ', '.join(str(v) for v in value) if value else '<em>None</em>'
        elif isinstance(value, dict):
            display_value = '<pre>' + escape(str(value)) + '</pre>'
        else:
            display_value = escape(str(value))

        return f'<dt>{label}</dt><dd>{display_value}</dd>'

    def _fallback_json_form(self, component_type: str, data: Dict) -> Markup:
        """Fallback to JSON textarea when no UI metadata available."""
        import json
        json_value = json.dumps(data, indent=2) if data else '{}'
        return Markup(f'''
            <div class="form-group">
                <label for="component_data">Component Data (JSON)</label>
                <textarea id="component_data" name="component_data" class="form-control" rows="10">{escape(json_value)}</textarea>
                <small class="form-text">Enter component data as JSON. No UI metadata defined for {escape(component_type)}.</small>
            </div>
        ''')

    def _fallback_json_display(self, data: Dict) -> Markup:
        """Fallback to JSON display when no UI metadata available."""
        import json
        json_value = json.dumps(data, indent=2)
        return Markup(f'<pre class="component-data-json">{escape(json_value)}</pre>')

    # ========== Character Sheet Specific Methods ==========

    def categorize_component(self, component_type: str, component_data: Dict[str, Any]) -> str:
        """
        Categorize a component for character sheet layout.

        Categories:
        - CORE: Essential stats (Attributes, Health, CharacterDetails)
        - COMBAT: Combat-related (Weapons, Armor, Attack bonuses)
        - SKILLS: Skills and proficiencies
        - RESOURCES: Spell slots, Ki points, etc.
        - INVENTORY: Items, equipment
        - INFO: Background, notes, description
        - MISC: Everything else

        Args:
            component_type: Name of component type
            component_data: Component data

        Returns:
            Category string
        """
        # Core types - essential stats and attributes
        core_types = {'Attributes', 'CharacterDetails', 'health', 'Health'}
        if component_type in core_types:
            return 'CORE'

        # Combat types - weapons, armor, attack bonuses
        combat_types = {'weapon', 'armor', 'Weapon', 'Armor', 'WeaponComponent', 'ArmorComponent'}
        if component_type in combat_types:
            return 'COMBAT'

        # Skills and proficiencies
        if 'skill' in component_type.lower() or 'proficiency' in component_type.lower():
            return 'SKILLS'

        # Resources - spell slots, ki points, etc.
        if any(keyword in component_type.lower() for keyword in ['spell', 'magic', 'ki', 'resource']):
            return 'RESOURCES'

        # Inventory
        if 'inventory' in component_type.lower() or 'item' in component_type.lower():
            return 'INVENTORY'

        # Info - background, notes, etc.
        if any(keyword in component_type.lower() for keyword in ['background', 'note', 'description', 'story']):
            return 'INFO'

        # Field-based detection
        if isinstance(component_data, dict):
            # Has damage_dice or attack_bonus? → COMBAT
            if any(key in component_data for key in ['damage_dice', 'attack_bonus', 'armor_class', 'ac']):
                return 'COMBAT'

            # Has proficiency or bonus to skills? → SKILLS
            if any(key in component_data for key in ['proficiency', 'skill_bonus']):
                return 'SKILLS'

            # Has slots or uses? → RESOURCES
            if any(key in component_data for key in ['slots', 'uses', 'charges']):
                return 'RESOURCES'

        return 'MISC'

    def build_character_sheet_display(self, component_type: str, data: Dict[str, Any], entity_id: str) -> Markup:
        """
        Build character sheet display with dice rolling support.

        Uses component-specific renderers for known types (Attributes, Weapons, etc.),
        falls back to generic display for unknown types.

        Args:
            component_type: Component type name
            data: Component data
            entity_id: Entity ID for dice rolling

        Returns:
            Markup-safe HTML string
        """
        # Check for component-specific renderer
        if component_type == 'Attributes':
            return self._render_attributes_sheet(data, entity_id)
        elif component_type in ['Weapon', 'WeaponComponent'] or 'weapon' in component_type.lower():
            return self._render_weapon_sheet(data, entity_id)
        elif component_type in ['Armor', 'ArmorComponent'] or 'armor' in component_type.lower():
            return self._render_armor_sheet(data, entity_id)
        elif component_type in ['Health', 'health']:
            return self._render_health_sheet(data, entity_id)
        else:
            # Use generic display with dice button detection
            return self._render_generic_sheet(component_type, data, entity_id)

    def _render_attributes_sheet(self, data: Dict[str, Any], entity_id: str) -> Markup:
        """Render Attributes component with ability checks."""
        from src.modules.generic_fantasy.attributes import AttributesComponent

        html = ['<div class="attributes-grid">']

        # Define attribute order
        attributes = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        labels = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

        for attr, label in zip(attributes, labels):
            score = data.get(attr, 10)
            modifier = AttributesComponent.calculate_modifier(score)
            mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)

            html.append(f'''
                <div class="attribute-card">
                    <div class="attribute-label">{label}</div>
                    <div class="attribute-score">{score}</div>
                    <div class="attribute-modifier">{mod_str}</div>
                    <button class="btn-roll-dice"
                            data-entity-id="{escape(entity_id)}"
                            data-notation="1d20{mod_str}"
                            data-roll-type="ability_check"
                            data-label="{label} Check">
                        🎲 Roll
                    </button>
                </div>
            ''')

        html.append('</div>')
        return Markup(''.join(html))

    def _render_weapon_sheet(self, data: Dict[str, Any], entity_id: str) -> Markup:
        """Render Weapon component with attack/damage rolls."""
        name = data.get('name', 'Weapon')
        damage_dice = data.get('damage_dice', '1d6')
        damage_type = data.get('damage_type', 'slashing')
        attack_bonus = data.get('attack_bonus', 0)
        bonus_str = f"+{attack_bonus}" if attack_bonus >= 0 else str(attack_bonus)

        html = [f'''
            <div class="weapon-card">
                <div class="weapon-name">{escape(name)}</div>
                <div class="weapon-stats">
                    <div class="weapon-stat">
                        <span class="stat-label">Attack:</span>
                        <span class="stat-value">1d20{bonus_str}</span>
                        <button class="btn-roll-dice"
                                data-entity-id="{escape(entity_id)}"
                                data-notation="1d20{bonus_str}"
                                data-roll-type="attack"
                                data-label="{escape(name)} Attack">
                            🎲
                        </button>
                    </div>
                    <div class="weapon-stat">
                        <span class="stat-label">Damage:</span>
                        <span class="stat-value">{escape(damage_dice)} {escape(damage_type)}</span>
                        <button class="btn-roll-dice"
                                data-entity-id="{escape(entity_id)}"
                                data-notation="{escape(damage_dice)}"
                                data-roll-type="damage"
                                data-label="{escape(name)} Damage">
                            🎲
                        </button>
                    </div>
                </div>
            </div>
        ''']

        return Markup(''.join(html))

    def _render_armor_sheet(self, data: Dict[str, Any], entity_id: str) -> Markup:
        """Render Armor component."""
        armor_type = data.get('armor_type', 'none')
        ac_bonus = data.get('ac_bonus', 0)

        html = [f'''
            <div class="armor-display">
                <div class="armor-stat">
                    <span class="stat-label">Type:</span>
                    <span class="stat-value">{escape(armor_type).title()}</span>
                </div>
                <div class="armor-stat">
                    <span class="stat-label">AC Bonus:</span>
                    <span class="stat-value">+{ac_bonus}</span>
                </div>
            </div>
        ''']

        return Markup(''.join(html))

    def _render_health_sheet(self, data: Dict[str, Any], entity_id: str) -> Markup:
        """Render Health component with HP bar."""
        current_hp = data.get('current_hp', 0)
        max_hp = data.get('max_hp', 1)
        temp_hp = data.get('temp_hp', 0)

        percentage = min(100, (current_hp / max_hp * 100)) if max_hp > 0 else 0

        # Color based on HP percentage
        if percentage > 50:
            bar_color = '#4caf50'
        elif percentage > 25:
            bar_color = '#ff9800'
        else:
            bar_color = '#f44336'

        html = [f'''
            <div class="health-display">
                <div class="hp-bar-container">
                    <div class="hp-bar" style="width: {percentage}%; background-color: {bar_color};"></div>
                    <div class="hp-text">{current_hp} / {max_hp} HP</div>
                </div>
                {f'<div class="temp-hp">Temp HP: {temp_hp}</div>' if temp_hp > 0 else ''}
            </div>
        ''']

        return Markup(''.join(html))

    def _render_generic_sheet(self, component_type: str, data: Dict[str, Any], entity_id: str) -> Markup:
        """Render generic component with automatic dice button detection."""
        comp_def = self._get_component_definition(component_type)
        if not comp_def:
            return self._fallback_json_display(data)

        ui_metadata = comp_def.get_ui_metadata()
        if not ui_metadata:
            return self._fallback_json_display(data)

        schema = comp_def.get_schema()
        properties = schema.get('properties', {})
        required_fields = set(schema.get('required', []))

        grouped_fields = self._group_fields(ui_metadata, properties, required_fields, data)

        html_parts = []
        for group_name, fields in grouped_fields.items():
            if group_name:
                html_parts.append(f'<div class="component-display-group">')
                html_parts.append(f'<h4>{escape(group_name)}</h4>')

            html_parts.append('<dl class="component-data">')
            for field_data in fields:
                html_parts.append(self._render_display_field_with_dice(field_data, entity_id))
            html_parts.append('</dl>')

            if group_name:
                html_parts.append('</div>')

        return Markup(''.join(html_parts))

    def _render_display_field_with_dice(self, field_data: Dict, entity_id: str) -> str:
        """Render display field with dice button if value looks like dice notation."""
        field_name = field_data['name']
        ui = field_data['ui']
        value = field_data['value']

        label = escape(ui.get('label', field_name.replace('_', ' ').title()))

        # Format value
        if value is None:
            display_value = '<em>Not set</em>'
        elif isinstance(value, bool):
            display_value = '✓ Yes' if value else '✗ No'
        elif isinstance(value, list):
            display_value = ', '.join(str(v) for v in value) if value else '<em>None</em>'
        elif isinstance(value, dict):
            display_value = '<pre>' + escape(str(value)) + '</pre>'
        else:
            display_value = escape(str(value))

            # Check if value looks like dice notation
            if self._is_dice_notation(str(value)):
                display_value += f'''
                    <button class="btn-roll-dice inline"
                            data-entity-id="{escape(entity_id)}"
                            data-notation="{escape(str(value))}"
                            data-roll-type="custom"
                            data-label="{label}">
                        🎲
                    </button>
                '''

        return f'<dt>{label}</dt><dd>{display_value}</dd>'

    def _is_dice_notation(self, value: str) -> bool:
        """Check if a string looks like dice notation (e.g., 1d20, 3d6+5)."""
        import re
        # Basic pattern: one or more NdN patterns
        pattern = r'\d+d\d+'
        return bool(re.search(pattern, value.lower()))
