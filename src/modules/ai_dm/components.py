"""
AI DM components for managing conversations and suggested actions.

Provides components for:
- ChatMessage: Individual messages in the conversation
- Conversation: Chat history and context tracking (data only, no UI)
"""

from typing import Dict, Any
from datetime import datetime
from ..base import ComponentTypeDefinition


class ChatMessageComponent(ComponentTypeDefinition):
    """
    Individual chat message in a conversation.

    Messages can be from players, the DM, or system notifications.
    Each message can include suggested actions that players can click.
    """

    type = "ChatMessage"
    description = "A message in the DM conversation"
    schema_version = "1.0.0"
    module = "ai_dm"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "speaker": {
                    "type": "string",
                    "description": "Who sent the message: 'dm', 'player', or 'system'"
                },
                "speaker_name": {
                    "type": "string",
                    "description": "Display name of the speaker"
                },
                "message": {
                    "type": "string",
                    "description": "The message content"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "When the message was sent"
                },
                "suggested_actions": {
                    "type": "array",
                    "description": "Actions the player can take",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "action_type": {"type": "string"},
                            "action_data": {"type": "object"}
                        },
                        "required": ["label", "action_type"]
                    }
                },
                "context": {
                    "type": "object",
                    "description": "Game state context when message was sent"
                }
            },
            "required": ["speaker", "message", "timestamp"]
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Chat messages don't appear individually on character sheets."""
        return {
            "visible": False,
            "category": "misc"
        }


class ConversationComponent(ComponentTypeDefinition):
    """
    Conversation history component for entities.

    Tracks the ongoing conversation between a player character and the DM.
    Stores message IDs in order and maintains conversation context.

    This is a data-only component - the UI is rendered on the dedicated
    DM chat page, not on the character sheet.
    """

    type = "Conversation"
    description = "DM conversation history"
    schema_version = "1.0.0"
    module = "ai_dm"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "description": "Ordered list of message entity IDs",
                    "items": {"type": "string"}
                },
                "last_message_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Timestamp of most recent message"
                },
                "context_summary": {
                    "type": "string",
                    "description": "Summary of conversation context (for AI)"
                },
                "active": {
                    "type": "boolean",
                    "description": "Is the DM actively engaged with this character",
                    "default": True
                }
            },
            "required": []
        }

    def get_default_data(self) -> Dict[str, Any]:
        return {
            "message_ids": [],
            "active": True
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Conversation tracking is internal - never shown on character sheet."""
        return {
            "visible": False,
            "category": "misc"
        }


__all__ = [
    'ChatMessageComponent',
    'ConversationComponent'
]
