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
- Conversation: Chat history tracking (data only, UI on dedicated page)

Dependencies:
- dm_tools: Provides core DM functionality and time management

Philosophy:
The AI DM is a collaborative storyteller that enhances gameplay without
replacing player agency. It suggests actions but lets players make choices.
"""

import logging
from typing import List, Optional, Any
from ..base import Module, ComponentTypeDefinition
from .components import ChatMessageComponent, ConversationComponent
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
        """AI DM depends on dm_tools for core DM functionality."""
        return ['dm_tools']

    def initialize(self, engine) -> None:
        """
        Initialize AI DM module.

        Sets up event subscriptions and auto-adds Conversation to PlayerCharacter entities.
        """
        self.engine = engine

        # Subscribe to component.added to auto-add Conversation to new PlayerCharacter entities
        engine.event_bus.subscribe('component.added', self.on_component_added)

        # Subscribe to character.form_submitted to handle scenario-specific logic
        # (e.g., generate AI intro if scenario_type is 'ai_generated')
        engine.event_bus.subscribe('character.form_submitted', self.on_character_form_submitted)

        # Auto-add Conversation component to all existing PlayerCharacter entities
        try:
            player_characters = engine.query_entities(['PlayerCharacter'])
            for pc in player_characters:
                # Check if Conversation already exists
                if not engine.get_component(pc.id, 'Conversation'):
                    # Add Conversation component
                    engine.add_component(pc.id, 'Conversation', {
                        'message_ids': [],
                        'active': True
                    })
                    logger.info(f"Added Conversation component to player character {pc.name} ({pc.id})")

        except Exception as e:
            logger.warning(f"Could not auto-add Conversation components: {e}")

    def on_component_added(self, event: Event) -> None:
        """Auto-add Conversation when PlayerCharacter component is added."""
        if not hasattr(self, 'engine'):
            return

        # If PlayerCharacter component was added, add Conversation too
        if event.data.get('component_type') == 'PlayerCharacter':
            entity_id = event.entity_id

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

    def on_character_form_submitted(self, event: Event) -> None:
        """Handle character creation - generate AI intro if scenario_type is 'ai_generated'."""
        if not hasattr(self, 'engine'):
            return

        entity_id = event.entity_id
        scenario_type = event.data.get('scenario_type')

        # Only generate intro for AI-generated scenarios
        if scenario_type != 'ai_generated':
            return

        logger.info(f"Generating AI intro for character {entity_id} (scenario_type={scenario_type})")

        try:
            # Import generate_intro_for_character from api module
            from .api import generate_intro_for_character

            # Generate the intro (runs synchronously)
            result = generate_intro_for_character(self.engine, entity_id)

            if result.get('success'):
                logger.info(f"Successfully generated AI intro for {entity_id}")
            else:
                logger.error(f"Failed to generate AI intro for {entity_id}: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error generating AI intro for {entity_id}: {e}", exc_info=True)

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register ChatMessage and Conversation components."""
        return [
            ChatMessageComponent(),
            ConversationComponent()
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
