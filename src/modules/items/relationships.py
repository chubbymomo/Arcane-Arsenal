"""
Relationship types for the Items module.

Provides relationships for item ownership and equipment:
- owns: Entity owns an item
- equipped: Entity has an item equipped
"""

from ..base import RelationshipTypeDefinition


class OwnsRelationship(RelationshipTypeDefinition):
    """
    Relationship indicating an entity owns an item.

    From entity: Character, NPC, or container
    To entity: Item entity

    Examples:
        Character -> Longsword
        Merchant -> Potion of Healing
        Dragon -> Gold Coins
    """

    type = "owns"
    description = "Entity owns this item"
    module = "items"


class EquippedRelationship(RelationshipTypeDefinition):
    """
    Relationship indicating an entity has an item equipped.

    From entity: Character or NPC with equipment
    To entity: Item entity with Equippable component

    Examples:
        Character -> Longsword (equipped in main_hand)
        Character -> Leather Armor (equipped on body)
        Character -> Ring of Protection (equipped in accessory_1)

    Notes:
        - Items must have Equippable component to be equipped
        - Only one item per slot (enforced by EquipmentSystem)
        - Equipped items must also have 'owns' relationship
    """

    type = "equipped"
    description = "Entity has this item equipped"
    module = "items"


__all__ = [
    'OwnsRelationship',
    'EquippedRelationship'
]
