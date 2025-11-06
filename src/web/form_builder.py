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
