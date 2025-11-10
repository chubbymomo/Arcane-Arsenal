"""
Equipment System for managing item ownership and equipment.

Provides high-level operations for equipping, unequipping, and querying items.
All operations use generic StateEngine methods - no special cases.
"""

from typing import List, Dict, Any, Optional
from src.core.result import Result


class EquipmentSystem:
    """
    System for managing equipment relationships.

    This is a pure ECS system - it operates on components and relationships
    using only generic StateEngine operations. No special-case logic in the engine.

    Usage:
        system = EquipmentSystem(engine)
        result = system.equip_item(character_id, sword_id)
        equipped = system.get_equipped_items(character_id)
    """

    def __init__(self, engine):
        """
        Initialize equipment system.

        Args:
            engine: StateEngine instance
        """
        self.engine = engine

    def equip_item(self, character_id: str, item_id: str) -> Result:
        """
        Equip an item to a character.

        Validates:
        - Item has Equippable component
        - Character owns the item
        - Character meets requirements (strength, level)
        - Slot is not occupied (unequips existing item if needed)

        Args:
            character_id: Entity ID of character
            item_id: Entity ID of item to equip

        Returns:
            Result with success/error status
        """
        # 1. Validate item has Equippable component
        equippable = self.engine.get_component(item_id, 'Equippable')
        if not equippable:
            return Result.fail("Item is not equippable", "ITEM_NOT_EQUIPPABLE")

        slot = equippable.data['slot']
        two_handed = equippable.data.get('two_handed', False)

        # 2. Validate character owns the item
        owns_relationships = self.engine.get_relationships(
            character_id,
            rel_type='owns',
            direction='from'
        )
        owns_item = any(rel.to_entity == item_id for rel in owns_relationships)
        if not owns_item:
            return Result.fail("Character does not own this item", "NOT_OWNED")

        # 3. Check requirements (optional - only if components exist)
        required_strength = equippable.data.get('required_strength')
        if required_strength:
            attributes = self.engine.get_component(character_id, 'Attributes')
            if attributes and attributes.data.get('strength', 0) < required_strength:
                return Result.fail(
                    f"Requires {required_strength} strength",
                    "INSUFFICIENT_STRENGTH"
                )

        required_level = equippable.data.get('required_level')
        if required_level:
            char_details = self.engine.get_component(character_id, 'CharacterDetails')
            if char_details and char_details.data.get('level', 1) < required_level:
                return Result.fail(
                    f"Requires level {required_level}",
                    "INSUFFICIENT_LEVEL"
                )

        # 4. Unequip any items in the same slot
        equipped_rels = self.engine.get_relationships(
            character_id,
            rel_type='equipped',
            direction='from'
        )

        for rel in equipped_rels:
            other_equippable = self.engine.get_component(rel.to_entity, 'Equippable')
            if other_equippable:
                other_slot = other_equippable.data['slot']
                # Unequip if same slot, or if two-handed weapon conflicts
                if other_slot == slot:
                    self.engine.delete_relationship(rel.id)
                elif two_handed and other_slot in ['main_hand', 'off_hand']:
                    self.engine.delete_relationship(rel.id)
                elif slot in ['main_hand', 'off_hand'] and other_equippable.data.get('two_handed'):
                    self.engine.delete_relationship(rel.id)

        # 5. Create equipped relationship
        result = self.engine.create_relationship(
            from_id=character_id,
            to_id=item_id,
            rel_type='equipped'
        )

        if result.success:
            return Result.ok({
                'character_id': character_id,
                'item_id': item_id,
                'slot': slot
            })
        else:
            return result

    def unequip_item(self, character_id: str, item_id: str) -> Result:
        """
        Unequip an item from a character.

        Args:
            character_id: Entity ID of character
            item_id: Entity ID of item to unequip

        Returns:
            Result with success/error status
        """
        # Find equipped relationship
        equipped_rels = self.engine.get_relationships(
            character_id,
            rel_type='equipped',
            direction='from'
        )

        for rel in equipped_rels:
            if rel.to_entity == item_id:
                result = self.engine.delete_relationship(rel.id)
                if result.success:
                    return Result.ok({
                        'character_id': character_id,
                        'item_id': item_id
                    })
                else:
                    return result

        return Result.fail("Item is not equipped", "NOT_EQUIPPED")

    def get_equipped_items(self, character_id: str) -> List[Dict[str, Any]]:
        """
        Get all equipped items for a character.

        Args:
            character_id: Entity ID of character

        Returns:
            List of dicts with item entity and components:
            [
                {
                    'entity': Entity,
                    'slot': str,
                    'components': {...}
                },
                ...
            ]
        """
        equipped_rels = self.engine.get_relationships(
            character_id,
            rel_type='equipped',
            direction='from'
        )

        items = []
        for rel in equipped_rels:
            entity = self.engine.get_entity(rel.to_entity)
            if entity and entity.is_active():
                components = self.engine.get_entity_components(rel.to_entity)
                equippable = components.get('Equippable', {})
                items.append({
                    'entity': entity,
                    'slot': equippable.get('slot', 'unknown'),
                    'components': components
                })

        return items

    def get_inventory(self, character_id: str) -> List[Dict[str, Any]]:
        """
        Get all owned items for a character (inventory).

        Args:
            character_id: Entity ID of character

        Returns:
            List of dicts with item entity and components:
            [
                {
                    'entity': Entity,
                    'equipped': bool,
                    'components': {...}
                },
                ...
            ]
        """
        owns_rels = self.engine.get_relationships(
            character_id,
            rel_type='owns',
            direction='from'
        )

        # Get equipped item IDs for marking
        equipped_rels = self.engine.get_relationships(
            character_id,
            rel_type='equipped',
            direction='from'
        )
        equipped_ids = {rel.to_entity for rel in equipped_rels}

        items = []
        for rel in owns_rels:
            entity = self.engine.get_entity(rel.to_entity)
            if entity and entity.is_active():
                components = self.engine.get_entity_components(rel.to_entity)
                items.append({
                    'entity': entity,
                    'equipped': rel.to_entity in equipped_ids,
                    'components': components
                })

        return items

    def get_item_in_slot(self, character_id: str, slot: str) -> Optional[Dict[str, Any]]:
        """
        Get the item equipped in a specific slot.

        Args:
            character_id: Entity ID of character
            slot: Equipment slot name

        Returns:
            Dict with item info or None if slot is empty:
            {
                'entity': Entity,
                'components': {...}
            }
        """
        equipped_items = self.get_equipped_items(character_id)

        for item in equipped_items:
            if item['slot'] == slot:
                return item

        return None

    def transfer_item(self, from_id: str, to_id: str, item_id: str) -> Result:
        """
        Transfer ownership of an item from one entity to another.

        Automatically unequips the item if it was equipped.

        Args:
            from_id: Current owner entity ID
            to_id: New owner entity ID
            item_id: Item entity ID

        Returns:
            Result with success/error status
        """
        # 1. Verify current ownership
        owns_rels = self.engine.get_relationships(
            from_id,
            rel_type='owns',
            direction='from'
        )

        owns_rel = None
        for rel in owns_rels:
            if rel.to_entity == item_id:
                owns_rel = rel
                break

        if not owns_rel:
            return Result.fail("Entity does not own this item", "NOT_OWNED")

        # 2. Unequip if equipped
        self.unequip_item(from_id, item_id)

        # 3. Delete old ownership
        result = self.engine.delete_relationship(owns_rel.id)
        if not result.success:
            return result

        # 4. Create new ownership
        result = self.engine.create_relationship(
            from_id=to_id,
            to_id=item_id,
            rel_type='owns'
        )

        if not result.success:
            return result

        # 5. Update Position to reflect new physical location
        # Items have Position components that track where they physically are
        position_result = self.engine.update_component(item_id, 'Position', {
            'region': to_id  # Item is now physically where the new owner is
        })
        if not position_result.success:
            # Log warning but don't fail - position update is not critical
            # (Some old items might not have Position yet)
            pass

        return Result.ok({
            'from': from_id,
            'to': to_id,
            'item_id': item_id
        })


__all__ = ['EquipmentSystem']
