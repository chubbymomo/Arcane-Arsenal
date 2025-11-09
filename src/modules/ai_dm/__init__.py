"""
AI Dungeon Master Module for Arcane Arsenal.

Provides an AI-powered DM that can:
- Engage in natural conversation with players
- Suggest contextual actions
- Respond to player choices
- Generate narrative content
- Track conversation history

Components:
- ChatMessage: Individual messages in the conversation
- Conversation: Chat history tracking
- DMDisplay: UI component for the chat interface

Philosophy:
The AI DM is a collaborative storyteller that enhances gameplay without
replacing player agency. It suggests actions but lets players make choices.
"""

import logging
from typing import List, Optional, Any
from ..base import Module, ComponentTypeDefinition
from .components import ChatMessageComponent, ConversationComponent, DMDisplayComponent
from src.core.event_bus import Event

logger = logging.getLogger(__name__)


class AIDMModule(Module):
    """
    AI Dungeon Master module for interactive storytelling.

    Provides conversational AI interface for players to interact with
    the game world through natural language and suggested actions.
    """

    def __init__(self):
        """Initialize AI DM module."""
        pass

    @property
    def name(self) -> str:
        return "ai_dm"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "AI Dungeon Master"

    @property
    def description(self) -> str:
        return "Conversational AI Dungeon Master with suggested actions and chat interface"

    def dependencies(self) -> List[str]:
        """AI DM depends on core_components."""
        return ['core_components']

    def initialize(self, engine) -> None:
        """
        Initialize AI DM module.

        Sets up event subscriptions and auto-adds DMDisplay to PlayerCharacter entities.
        """
        self.engine = engine

        # Subscribe to component.added to auto-add DMDisplay to new PlayerCharacter entities
        engine.event_bus.subscribe('component.added', self.on_component_added)

        # Auto-add DMDisplay component to all existing PlayerCharacter entities
        try:
            player_characters = engine.query_entities(['PlayerCharacter'])
            for pc in player_characters:
                # Check if DMDisplay already exists
                if not engine.get_component(pc.id, 'DMDisplay'):
                    # Add DMDisplay component with default settings
                    engine.add_component(pc.id, 'DMDisplay', {
                        'show_suggested_actions': True,
                        'show_timestamps': True,
                        'max_visible_messages': 20,
                        'auto_scroll': True
                    })
                    logger.info(f"Added DMDisplay component to player character {pc.name} ({pc.id})")

                # Also add Conversation component if missing
                if not engine.get_component(pc.id, 'Conversation'):
                    engine.add_component(pc.id, 'Conversation', {
                        'message_ids': [],
                        'active': True
                    })
                    logger.info(f"Added Conversation component to player character {pc.name} ({pc.id})")

        except Exception as e:
            logger.warning(f"Could not auto-add AI DM components: {e}")

    def on_component_added(self, event: Event) -> None:
        """Auto-add DMDisplay and Conversation when PlayerCharacter component is added."""
        if not hasattr(self, 'engine'):
            return

        # If PlayerCharacter component was added, add DMDisplay and Conversation too
        if event.data.get('component_type') == 'PlayerCharacter':
            entity_id = event.entity_id

            # Add DMDisplay if missing
            if not self.engine.get_component(entity_id, 'DMDisplay'):
                try:
                    self.engine.add_component(entity_id, 'DMDisplay', {
                        'show_suggested_actions': True,
                        'show_timestamps': True,
                        'max_visible_messages': 20,
                        'auto_scroll': True
                    })
                    logger.info(f"Auto-added DMDisplay component to new player character {entity_id}")
                except Exception as e:
                    logger.warning(f"Could not auto-add DMDisplay to {entity_id}: {e}")

            # Add Conversation if missing
            if not self.engine.get_component(entity_id, 'Conversation'):
                try:
                    self.engine.add_component(entity_id, 'Conversation', {
                        'message_ids': [],
                        'active': True
                    })
                    logger.info(f"Auto-added Conversation component to new player character {entity_id}")
                except Exception as e:
                    logger.warning(f"Could not auto-add Conversation to {entity_id}: {e}")

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register ChatMessage, Conversation, and DMDisplay components."""
        return [
            ChatMessageComponent(),
            ConversationComponent(),
            DMDisplayComponent()
        ]

    def register_blueprint(self) -> Optional[Any]:
        """
        Register Flask blueprint for AI DM API endpoints.

        Provides REST API endpoints for DM chat and interaction:
        - POST /api/dm/message          - Send message to DM
        - GET  /api/dm/chat_display/:id - Get chat HTML
        - POST /api/dm/execute_action   - Execute suggested action
        """
        from .api import ai_dm_bp
        return ai_dm_bp


__all__ = [
    'AIDMModule',
    'ChatMessageComponent',
    'ConversationComponent',
    'DMDisplayComponent'
]
