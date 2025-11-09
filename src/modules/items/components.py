"""
Item components for the Items module.

Provides components for creating item entities:
- Item: Basic item properties (weight, value, rarity)
- Equippable: Marks entity as equippable (slot, requirements)
- Consumable: Marks entity as consumable (charges, effects)
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class ItemComponent(ComponentTypeDefinition):
    """
    Basic item component for physical objects.

    Stores common item properties like weight, value, rarity, and description.
    Items are entities that can be owned, carried, and potentially equipped.
    """

    type = "Item"
    description = "Basic item properties"
    schema_version = "1.0.0"
    module = "items"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "weight": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Weight in pounds"
                },
                "value": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Value in gold pieces"
                },
                "rarity": {
                    "type": "string",
                    "description": "Item rarity"
                },
                "stackable": {
                    "type": "boolean",
                    "default": False,
                    "description": "Can multiple instances stack"
                },
                "quantity": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                    "description": "Number of items in stack"
                }
            },
            "required": ["weight", "value"]
        }

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """Validate rarity against registry if provided."""
        rarity = data.get('rarity')
        if rarity:
            registry = engine.create_registry('item_rarities', self.module)
            registry.validate(rarity, 'rarity')
        return True

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "weight": {
                "label": "Weight (lbs)",
                "widget": "number",
                "order": 0,
                "min": 0,
                "step": 0.1,
                "help_text": "Weight in pounds"
            },
            "value": {
                "label": "Value (gp)",
                "widget": "number",
                "order": 1,
                "min": 0,
                "step": 0.01,
                "help_text": "Value in gold pieces"
            },
            "rarity": {
                "label": "Rarity",
                "widget": "select",
                "order": 2,
                "registry": "item_rarities",
                "help_text": "Item rarity tier"
            },
            "stackable": {
                "label": "Stackable",
                "widget": "checkbox",
                "order": 3,
                "help_text": "Can multiple instances stack together"
            },
            "quantity": {
                "label": "Quantity",
                "widget": "number",
                "order": 4,
                "min": 1,
                "help_text": "Number of items in this stack"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Items don't appear directly on character sheets (they're entities)."""
        return {
            "visible": False,
            "category": "inventory",
            "priority": 100
        }


class EquippableComponent(ComponentTypeDefinition):
    """
    Equippable component marks an item entity as equippable.

    Defines which equipment slot the item occupies and any requirements
    for equipping it (e.g., minimum strength).
    """

    type = "Equippable"
    description = "Marks item as equippable gear"
    schema_version = "1.0.0"
    module = "items"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "slot": {
                    "type": "string",
                    "description": "Equipment slot this item occupies"
                },
                "two_handed": {
                    "type": "boolean",
                    "default": False,
                    "description": "Requires both hands (occupies main_hand and off_hand)"
                },
                "required_strength": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Minimum strength to equip"
                },
                "required_level": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Minimum character level to equip"
                }
            },
            "required": ["slot"]
        }

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """Validate slot against equipment_slots registry."""
        slot = data.get('slot')
        if not slot:
            raise ValueError("slot is required for equippable items")

        # Validate against equipment_slots registry
        registry = engine.create_registry('equipment_slots', self.module)
        registry.validate(slot, 'slot')

        return True

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "slot": {
                "label": "Equipment Slot",
                "widget": "select",
                "order": 0,
                "registry": "equipment_slots",
                "help_text": "Which slot this item occupies when equipped"
            },
            "two_handed": {
                "label": "Two-Handed",
                "widget": "checkbox",
                "order": 1,
                "help_text": "Requires both hands to use"
            },
            "required_strength": {
                "label": "Required Strength",
                "widget": "number",
                "order": 2,
                "min": 0,
                "help_text": "Minimum strength score to equip"
            },
            "required_level": {
                "label": "Required Level",
                "widget": "number",
                "order": 3,
                "min": 1,
                "help_text": "Minimum character level to equip"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Equippable info doesn't appear directly on character sheets."""
        return {
            "visible": False,
            "category": "equipment",
            "priority": 100
        }


class ConsumableComponent(ComponentTypeDefinition):
    """
    Consumable component for items that can be used up.

    Examples: potions, scrolls, food, ammunition.
    Tracks charges/uses and describes the effect.
    """

    type = "Consumable"
    description = "Consumable item with limited uses"
    schema_version = "1.0.0"
    module = "items"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "charges": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Remaining uses/charges"
                },
                "max_charges": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum charges when full"
                },
                "effect_description": {
                    "type": "string",
                    "description": "Description of what happens when consumed"
                },
                "rechargeable": {
                    "type": "boolean",
                    "default": False,
                    "description": "Can this item be recharged"
                }
            },
            "required": ["charges", "max_charges", "effect_description"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "charges": {
                "label": "Current Charges",
                "widget": "number",
                "order": 0,
                "min": 0,
                "help_text": "Remaining uses"
            },
            "max_charges": {
                "label": "Max Charges",
                "widget": "number",
                "order": 1,
                "min": 1,
                "help_text": "Maximum charges"
            },
            "effect_description": {
                "label": "Effect",
                "widget": "textarea",
                "order": 2,
                "help_text": "What happens when this item is used"
            },
            "rechargeable": {
                "label": "Rechargeable",
                "widget": "checkbox",
                "order": 3,
                "help_text": "Can this item be recharged"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Consumable info doesn't appear directly on character sheets."""
        return {
            "visible": False,
            "category": "inventory",
            "priority": 100
        }


class InventoryDisplayComponent(ComponentTypeDefinition):
    """
    Inventory display component for character sheets.

    Provides UI for viewing owned and equipped items.
    This component has no meaningful data - it's purely a UI container that
    displays items from 'owns' and 'equipped' relationships.
    """

    type = "InventoryDisplay"
    description = "Displays inventory and equipped items on character sheet"
    schema_version = "1.0.0"
    module = "items"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "show_weight": {
                    "type": "boolean",
                    "description": "Display total weight carried",
                    "default": True
                },
                "show_value": {
                    "type": "boolean",
                    "description": "Display total value of inventory",
                    "default": True
                }
            },
            "required": []
        }

    def get_default_data(self) -> Dict[str, Any]:
        return {
            "show_weight": True,
            "show_value": True
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Inventory appears in the INVENTORY category (right column)."""
        return {
            "visible": True,
            "category": "inventory",
            "priority": 1,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer for inventory and equipment display."""
        from markupsafe import escape

        if not engine or not entity_id:
            return '<p>No inventory data available</p>'

        # Get owned and equipped items via relationships
        relationships = engine.get_relationships(entity_id)
        owned_items = []
        equipped_items = {}

        for rel in relationships:
            if rel.from_entity == entity_id:
                if rel.relationship_type == 'owns':
                    item_entity = engine.get_entity(rel.to_entity)
                    if item_entity and item_entity.is_active():
                        owned_items.append(item_entity)
                elif rel.relationship_type == 'equipped':
                    item_entity = engine.get_entity(rel.to_entity)
                    if item_entity and item_entity.is_active():
                        equippable = engine.get_component(item_entity.id, 'Equippable')
                        if equippable:
                            slot = equippable.data.get('slot', 'unknown')
                            equipped_items[slot] = item_entity

        # Calculate total weight and value
        total_weight = 0
        total_value = 0

        for item in owned_items:
            item_comp = engine.get_component(item.id, 'Item')
            if item_comp:
                total_weight += item_comp.data.get('weight', 0) * item_comp.data.get('quantity', 1)
                total_value += item_comp.data.get('value', 0) * item_comp.data.get('quantity', 1)

        # Build HTML
        html = ['<div class="inventory-display">']

        # Equipment section
        html.append('<div class="equipment-section" style="margin-bottom: 1rem;">')
        html.append('<h4 style="font-weight: bold; margin-bottom: 0.5rem;">⚔️ Equipped</h4>')

        if equipped_items:
            html.append('<div class="equipment-slots" style="display: grid; gap: 0.5rem;">')
            for slot, item in equipped_items.items():
                item_comp = engine.get_component(item.id, 'Item')
                if item_comp:
                    rarity = item_comp.data.get('rarity', 'common')
                    html.append(f'''
                        <div class="equipped-item" style="padding: 0.75rem; background: linear-gradient(145deg, #211528, #2d1b3d); border: 1px solid #3d2b4d; border-radius: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;">
                                <div style="flex: 1;">
                                    <strong style="color: #d4af37; font-family: 'Cinzel', serif;">{escape(item.name)}</strong>
                                    <div style="font-size: 0.85rem; color: #a99b8a;">
                                        {escape(slot.replace('_', ' ').title())}
                                        {' • ' + escape(rarity).upper() if rarity else ''}
                                    </div>
                                </div>
                                <button class="btn-unequip"
                                        style="padding: 0.5rem 1rem; background: linear-gradient(135deg, #c0392b, #a82820); color: #ffffff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; transition: all 0.2s;"
                                        onmouseover="this.style.background='linear-gradient(135deg, #d43f2f, #c0392b)'; this.style.transform='translateY(-1px)'"
                                        onmouseout="this.style.background='linear-gradient(135deg, #c0392b, #a82820)'; this.style.transform='translateY(0)'"
                                        onclick="unequipItem('{escape(entity_id)}', '{escape(item.id)}')">
                                    Unequip
                                </button>
                            </div>
                        </div>
                    ''')
            html.append('</div>')
        else:
            html.append('<p style="color: #6a5a7a; font-style: italic;">No items equipped</p>')

        html.append('</div>')

        # Inventory section
        html.append('<div class="inventory-section">')
        html.append('<h4 style="font-weight: bold; margin-bottom: 0.5rem;">🎒 Inventory</h4>')

        # Stats
        if data.get('show_weight') or data.get('show_value'):
            html.append('<div style="display: flex; gap: 1rem; margin-bottom: 0.5rem; font-size: 0.9rem; color: #a99b8a;">')
            if data.get('show_weight'):
                html.append(f'<span style="color: #d4af37;">⚖️ {total_weight:.1f} lbs</span>')
            if data.get('show_value'):
                html.append(f'<span style="color: #d4af37;">💰 {total_value:.2f} gp</span>')
            html.append('</div>')

        if owned_items:
            unequipped_items = [item for item in owned_items if item.id not in [e.id for e in equipped_items.values()]]

            html.append('<div class="inventory-items" style="max-height: 300px; overflow-y: auto; display: grid; gap: 0.5rem;">')
            for item in unequipped_items:
                item_comp = engine.get_component(item.id, 'Item')
                equippable = engine.get_component(item.id, 'Equippable')
                consumable = engine.get_component(item.id, 'Consumable')

                if item_comp:
                    quantity = item_comp.data.get('quantity', 1)
                    weight = item_comp.data.get('weight', 0)
                    value = item_comp.data.get('value', 0)
                    rarity = item_comp.data.get('rarity', 'common')

                    # Build buttons separately to avoid f-string nesting issues
                    buttons_html = ''
                    if equippable:
                        buttons_html += f'<button class="btn-equip" style="padding: 0.4rem 0.75rem; background: linear-gradient(135deg, #d4af37, #b8942b); color: #1a1520; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; transition: all 0.2s; font-family: \'Cinzel\', serif;" onmouseover="this.style.background=\'linear-gradient(135deg, #ffd700, #d4af37)\'; this.style.transform=\'translateY(-1px)\'" onmouseout="this.style.background=\'linear-gradient(135deg, #d4af37, #b8942b)\'; this.style.transform=\'translateY(0)\'" onclick="equipItem(\'{escape(entity_id)}\', \'{escape(item.id)}\')">Equip</button>'
                    if consumable:
                        charges = consumable.data.get('charges', 0)
                        buttons_html += f'<button class="btn-use" style="padding: 0.4rem 0.75rem; background: linear-gradient(135deg, #4a4a4a, #353535); color: #f0e6d6; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; transition: all 0.2s;" onmouseover="this.style.background=\'linear-gradient(135deg, #5a5a5a, #454545)\'" onmouseout="this.style.background=\'linear-gradient(135deg, #4a4a4a, #353535)\'" onclick="useItem(\'{escape(entity_id)}\', \'{escape(item.id)}\')">Use ({charges})</button>'

                    # Build item stats line
                    stats_parts = []
                    if rarity:
                        stats_parts.append(escape(rarity))
                    if weight:
                        stats_parts.append(f'{weight:.1f} lbs')
                    if value:
                        stats_parts.append(f'{value:.2f} gp')
                    stats_line = ' • '.join(stats_parts) if stats_parts else ''

                    # Build consumable effect line
                    effect_line = ''
                    if consumable:
                        effect_desc = consumable.data.get('effect_description', '')
                        if effect_desc:
                            effect_line = f'<div style="font-size: 0.85rem; color: #9b59b6; margin-top: 0.25rem; font-style: italic;">{escape(effect_desc)}</div>'

                    html.append(f'''
                        <div class="inventory-item" style="padding: 0.75rem; background: linear-gradient(145deg, #211528, #2d1b3d); border: 1px solid #3d2b4d; border-radius: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem;">
                                <div style="flex: 1;">
                                    <strong style="color: #f0e6d6; font-family: 'Cinzel', serif;">{escape(item.name)}</strong>
                                    {f' <span style="color: #a99b8a;">x{quantity}</span>' if quantity > 1 else ''}
                                    <div style="font-size: 0.85rem; color: #a99b8a; margin-top: 0.25rem;">
                                        {stats_line}
                                    </div>
                                    {effect_line}
                                </div>
                                <div style="display: flex; gap: 0.5rem; flex-shrink: 0;">
                                    {buttons_html}
                                </div>
                            </div>
                        </div>
                    ''')
            html.append('</div>')
        else:
            html.append('<p style="color: #6a5a7a; font-style: italic;">No items in inventory</p>')

        html.append('</div>')
        html.append('</div>')

        # JavaScript for item interactions
        html.append('''
            <script>
            function equipItem(entityId, itemId) {
                fetch(`/client/api/entities/${entityId}/equip`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ item_id: itemId })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Failed to equip item: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    console.error('Equip error:', error);
                    alert('Failed to equip item');
                });
            }

            function unequipItem(entityId, itemId) {
                fetch(`/client/api/entities/${entityId}/unequip`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ item_id: itemId })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Failed to unequip item: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    console.error('Unequip error:', error);
                    alert('Failed to unequip item');
                });
            }

            function useItem(entityId, itemId) {
                fetch(`/client/api/entities/${entityId}/use_item`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ item_id: itemId })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message || 'Item used successfully');
                        location.reload();
                    } else {
                        alert('Failed to use item: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    console.error('Use item error:', error);
                    alert('Failed to use item');
                });
            }
            </script>
        ''')

        return ''.join(html)


__all__ = [
    'ItemComponent',
    'EquippableComponent',
    'ConsumableComponent',
    'InventoryDisplayComponent'
]
