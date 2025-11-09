"""
AI Context Generation for Arcane Arsenal.

Builds structured context from game state for LLM consumption.
Extracts character stats, location, inventory, conversation history,
and recent events into a format optimized for AI understanding.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AIContextBuilder:
    """
    Builds structured context for AI from game state.

    Queries the StateEngine to extract relevant information about
    a character and their surroundings, formatting it for LLM consumption.
    """

    def __init__(self, engine: 'StateEngine'):
        """
        Initialize context builder.

        Args:
            engine: StateEngine instance for querying game state
        """
        self.engine = engine

    def build_game_system_context(self) -> Dict[str, Any]:
        """
        Build context about the game system (all registered game data).

        Dynamically includes all registries (races, classes, skills, spells, etc.)
        that modules have registered with the engine.

        Returns:
            Dict with game system information from all registries
        """
        context = {}

        try:
            # Get all registry names dynamically
            registry_names = self.engine.storage.get_registry_names()

            # Include ALL registries dynamically
            for registry_name in registry_names:
                try:
                    values = self.engine.storage.get_registry_values(registry_name)
                    # Only include key and description for cleaner AI context
                    context[registry_name] = [
                        {'key': v['key'], 'description': v['description']}
                        for v in values
                        if 'key' in v and 'description' in v
                    ]
                except Exception as e:
                    logger.debug(f"Skipping registry '{registry_name}': {e}")

        except Exception as e:
            logger.warning(f"Error building game system context: {e}")

        return context

    def build_character_context(self, entity_id: str) -> Dict[str, Any]:
        """
        Build comprehensive character context.

        Args:
            entity_id: ID of the character entity

        Returns:
            Dict with character information including:
            - name, description
            - class, level, race
            - attributes (STR, DEX, etc.)
            - hit points
            - skills and proficiencies
            - spellcasting info (if applicable)

        Example:
            {
                'name': 'Theron',
                'description': 'A brave warrior',
                'class': 'wizard',
                'level': 5,
                'race': 'human',
                'attributes': {'strength': 10, 'dexterity': 14, ...},
                'hp': {'current': 28, 'max': 35},
                'skills': {'proficiency_bonus': 3, 'proficient_in': ['arcana', 'history']},
                'magic': {'spellcasting_ability': 'intelligence', 'spell_slots': {...}}
            }
        """
        entity = self.engine.get_entity(entity_id)
        if not entity:
            logger.warning(f"Entity {entity_id} not found for context building")
            return {}

        context = {
            'name': entity.name,
            'id': entity_id
        }

        # Identity (description)
        identity = self.engine.get_component(entity_id, 'Identity')
        if identity:
            context['description'] = identity.data.get('description', '')

        # CharacterDetails (class, level, race)
        char_details = self.engine.get_component(entity_id, 'CharacterDetails')
        if char_details:
            context['class'] = char_details.data.get('character_class', 'unknown')
            context['level'] = char_details.data.get('level', 1)
            context['race'] = char_details.data.get('race', 'unknown')
            context['alignment'] = char_details.data.get('alignment', 'unknown')

        # Attributes (STR, DEX, CON, INT, WIS, CHA)
        attributes = self.engine.get_component(entity_id, 'Attributes')
        if attributes:
            context['attributes'] = {
                'strength': attributes.data.get('strength', 10),
                'dexterity': attributes.data.get('dexterity', 10),
                'constitution': attributes.data.get('constitution', 10),
                'intelligence': attributes.data.get('intelligence', 10),
                'wisdom': attributes.data.get('wisdom', 10),
                'charisma': attributes.data.get('charisma', 10)
            }

            # Calculate modifiers
            context['modifiers'] = {
                attr: (score - 10) // 2
                for attr, score in context['attributes'].items()
            }

        # Health (HP)
        health = self.engine.get_component(entity_id, 'Health')
        if health:
            context['hp'] = {
                'current': health.data.get('current_hp', 0),
                'max': health.data.get('max_hp', 0)
            }

        # Skills
        skills = self.engine.get_component(entity_id, 'Skills')
        if skills:
            context['skills'] = {
                'proficiency_bonus': skills.data.get('proficiency_bonus', 2),
                'proficient_skills': skills.data.get('proficient_skills', []),
                'expertise_skills': skills.data.get('expertise_skills', [])
            }

        # Magic (if spellcaster)
        magic = self.engine.get_component(entity_id, 'Magic')
        if magic:
            spell_slots = magic.data.get('spell_slots', {})
            context['magic'] = {
                'spellcasting_ability': magic.data.get('spellcasting_ability', 'intelligence'),
                'available_spell_slots': {
                    level: slot_data.get('current', 0)
                    for level, slot_data in spell_slots.items()
                },
                'known_spells_count': len(magic.data.get('known_spells', [])),
                'prepared_spells_count': len(magic.data.get('prepared_spells', [])),
                'cantrips_count': len(magic.data.get('cantrips', []))
            }

        return context

    def build_location_context(self, entity_id: str, include_nearby: bool = True) -> Dict[str, Any]:
        """
        Build context for character's current location.

        Args:
            entity_id: ID of the character entity
            include_nearby: Whether to include nearby entities

        Returns:
            Dict with location info:
            - region name
            - coordinates
            - nearby entities (NPCs, items, etc.)

        Example:
            {
                'region': 'The Golden Tankard',
                'coordinates': {'x': 10, 'y': 20, 'z': 0},
                'nearby_entities': [
                    {'name': 'Barkeep', 'type': 'NPC'},
                    {'name': 'Rusty Sword', 'type': 'item'}
                ]
            }
        """
        position = self.engine.get_component(entity_id, 'Position')
        if not position:
            return {}

        context = {
            'region': position.data.get('region', 'Unknown'),
            'coordinates': {
                'x': position.data.get('x', 0),
                'y': position.data.get('y', 0),
                'z': position.data.get('z', 0)
            }
        }

        if include_nearby:
            # Find entities in the same region (entity-based hierarchical positioning)
            nearby = []
            region_ref = position.data.get('region')

            if region_ref:
                # Query all entities with Position component
                entities_with_position = self.engine.query_entities(['Position'])

                # Entity-based positioning: Find entities positioned AT this entity
                # If current entity is a location, find entities with Position.region == entity_id
                is_location = self.engine.get_component(entity_id, 'Location')
                if is_location:
                    # This entity is a location - find entities positioned AT it
                    for entity in entities_with_position:
                        if entity.id == entity_id:
                            continue  # Skip self

                        pos = self.engine.get_component(entity.id, 'Position')
                        # Match on entity ID (entity positioned AT this location)
                        if pos and pos.data.get('region') == entity_id:
                            entity_info = self._build_entity_info(entity)
                            if entity_info:
                                nearby.append(entity_info)
                else:
                    # This entity is not a location - find entities in the same region
                    for entity in entities_with_position:
                        if entity.id == entity_id:
                            continue  # Skip self

                        pos = self.engine.get_component(entity.id, 'Position')
                        # Match on region reference (could be entity ID or string)
                        if pos and pos.data.get('region') == region_ref:
                            entity_info = self._build_entity_info(entity)
                            if entity_info:
                                nearby.append(entity_info)

            context['nearby_entities'] = nearby[:10]  # Limit to 10 nearest

        return context

    def _build_entity_info(self, entity) -> Dict[str, Any]:
        """
        Build entity info dict for nearby entities.

        Args:
            entity: Entity to build info for

        Returns:
            Dict with entity info, or None if entity type is unknown
        """
        entity_type = 'unknown'

        # Determine entity type
        if self.engine.get_component(entity.id, 'PlayerCharacter'):
            entity_type = 'player'
        elif self.engine.get_component(entity.id, 'NPC'):
            entity_type = 'npc'
        elif self.engine.get_component(entity.id, 'Item'):
            entity_type = 'item'
        elif self.engine.get_component(entity.id, 'Location'):
            entity_type = 'location'

        entity_info = {
            'name': entity.name,
            'type': entity_type,
            'id': entity.id
        }

        # Include Identity component for description
        identity = self.engine.get_component(entity.id, 'Identity')
        if identity:
            entity_info['description'] = identity.data.get('description', '')

        # Get race and occupation from NPC component (for NPCs)
        npc = self.engine.get_component(entity.id, 'NPC')
        if npc:
            entity_info['race'] = npc.data.get('race', '')
            entity_info['occupation'] = npc.data.get('occupation', '')

        # Get race from CharacterDetails (for player characters)
        char_details = self.engine.get_component(entity.id, 'CharacterDetails')
        if char_details and not entity_info.get('race'):
            entity_info['race'] = char_details.data.get('race', '')

        return entity_info

    def build_inventory_context(self, entity_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Build inventory context for a character.

        Args:
            entity_id: ID of the character entity
            limit: Maximum number of items to include

        Returns:
            List of item dicts with name, description, equipped status

        Example:
            [
                {
                    'name': 'Longsword +1',
                    'description': 'A finely crafted blade',
                    'equipped': True,
                    'type': 'weapon'
                },
                ...
            ]
        """
        # Find items via 'owns' relationships
        relationships = self.engine.get_relationships(entity_id)

        items = []
        for rel in relationships:
            if rel.relationship_type == 'owns' and rel.from_entity == entity_id:
                item_id = rel.to_entity
                item_entity = self.engine.get_entity(item_id)

                if item_entity:
                    item_data = {
                        'name': item_entity.name,
                        'id': item_id
                    }

                    # Get Identity component for description
                    identity = self.engine.get_component(item_id, 'Identity')
                    if identity:
                        item_data['description'] = identity.data.get('description', '')

                    # Get Item component for type and other details
                    item_comp = self.engine.get_component(item_id, 'Item')
                    if item_comp:
                        item_data['type'] = item_comp.data.get('item_type', 'misc')
                        item_data['value'] = item_comp.data.get('value', 0)
                        item_data['quantity'] = item_comp.data.get('quantity', 1)

                    # Check if equipped
                    equipped_rels = [r for r in relationships
                                    if r.relationship_type == 'equipped' and r.to_entity == item_id]
                    item_data['equipped'] = len(equipped_rels) > 0

                    items.append(item_data)

        return items[:limit]

    def build_conversation_history(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Build recent conversation history.

        Args:
            entity_id: ID of the character entity
            limit: Maximum number of messages to include

        Returns:
            List of message dicts in chronological order

        Example:
            [
                {
                    'speaker': 'player',
                    'speaker_name': 'Theron',
                    'message': 'I search the room',
                    'timestamp': '2024-01-01T12:00:00'
                },
                {
                    'speaker': 'dm',
                    'speaker_name': 'Dungeon Master',
                    'message': 'You find a hidden compartment...',
                    'timestamp': '2024-01-01T12:00:05'
                }
            ]
        """
        conversation = self.engine.get_component(entity_id, 'Conversation')
        if not conversation:
            return []

        message_ids = conversation.data.get('message_ids', [])

        messages = []
        for msg_id in message_ids[-limit:]:  # Last N messages
            msg_entity = self.engine.get_entity(msg_id)
            if msg_entity and msg_entity.is_active():
                msg_comp = self.engine.get_component(msg_id, 'ChatMessage')
                if msg_comp:
                    messages.append({
                        'speaker': msg_comp.data.get('speaker', 'unknown'),
                        'speaker_name': msg_comp.data.get('speaker_name', 'Unknown'),
                        'message': msg_comp.data.get('message', ''),
                        'timestamp': msg_comp.data.get('timestamp', '')
                    })

        return messages

    def build_recent_events(
        self,
        entity_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Build recent game events for context.

        Args:
            entity_id: ID of the character entity
            limit: Maximum number of events to include

        Returns:
            List of event dicts

        Example:
            [
                {
                    'type': 'roll.completed',
                    'timestamp': '2024-01-01T12:00:00',
                    'summary': 'Rolled 1d20+3 for Perception: 16'
                },
                ...
            ]
        """
        events = self.engine.get_events(entity_id=entity_id, limit=limit)

        event_summaries = []
        for event in events:
            summary = {
                'type': event.event_type,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp
            }

            # Create human-readable summary based on event type
            if event.event_type == 'roll.completed':
                data = event.data
                notation = data.get('notation', '?')
                purpose = data.get('purpose', 'Unknown')
                total = data.get('total', 0)
                summary['summary'] = f"Rolled {notation} for {purpose}: {total}"

            elif event.event_type == 'component.added':
                comp_type = event.data.get('component_type', 'Unknown')
                summary['summary'] = f"Added {comp_type} component"

            elif event.event_type == 'component.updated':
                comp_type = event.data.get('component_type', 'Unknown')
                summary['summary'] = f"Updated {comp_type} component"

            else:
                summary['summary'] = f"{event.event_type}"

            event_summaries.append(summary)

        return event_summaries

    def build_full_context(
        self,
        entity_id: str,
        include_history: bool = True,
        include_events: bool = True,
        include_nearby: bool = True
    ) -> Dict[str, Any]:
        """
        Build complete AI context for an entity.

        This is the main method that combines all context pieces into
        a comprehensive picture of the game state.

        Args:
            entity_id: ID of the entity to build context for
            include_history: Include conversation history
            include_events: Include recent game events
            include_nearby: Include nearby entities in location context

        Returns:
            Complete context dict with all available information

        Example:
            {
                'character': {...},
                'location': {...},
                'inventory': [...],
                'conversation': [...],  # if include_history
                'recent_events': [...]  # if include_events
            }
        """
        logger.info(f"Building AI context for entity {entity_id}")

        context = {
            'character': self.build_character_context(entity_id),
            'location': self.build_location_context(entity_id, include_nearby=include_nearby),
            'inventory': self.build_inventory_context(entity_id),
            'game_system': self.build_game_system_context()  # Available races, classes, skills, etc.
        }

        if include_history:
            context['conversation'] = self.build_conversation_history(entity_id)

        if include_events:
            context['recent_events'] = self.build_recent_events(entity_id)

        logger.debug(f"Built context with {len(context['conversation']) if include_history else 0} messages, "
                    f"{len(context['inventory'])} items, "
                    f"{len(context.get('location', {}).get('nearby_entities', []))} nearby entities")

        return context


__all__ = ['AIContextBuilder']
