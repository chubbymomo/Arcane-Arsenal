"""
AI DM components for managing conversations and suggested actions.

Provides components for:
- ChatMessage: Individual messages in the conversation
- Conversation: Chat history and context tracking
- DMDisplay: UI component for displaying the chat interface
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
        """Conversation tracking is internal."""
        return {
            "visible": False,
            "category": "misc"
        }


class DMDisplayComponent(ComponentTypeDefinition):
    """
    DM chat display component for character sheets.

    Provides the UI for interacting with the AI DM.
    Shows conversation history, suggested actions, and message input.
    """

    type = "DMDisplay"
    description = "AI DM chat interface on character sheet"
    schema_version = "1.0.0"
    module = "ai_dm"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "show_suggested_actions": {
                    "type": "boolean",
                    "description": "Display suggested action buttons",
                    "default": True
                },
                "show_timestamps": {
                    "type": "boolean",
                    "description": "Show message timestamps",
                    "default": True
                },
                "max_visible_messages": {
                    "type": "integer",
                    "description": "Maximum messages to show before scrolling",
                    "minimum": 5,
                    "maximum": 100,
                    "default": 20
                },
                "auto_scroll": {
                    "type": "boolean",
                    "description": "Auto-scroll to latest message",
                    "default": True
                }
            },
            "required": []
        }

    def get_default_data(self) -> Dict[str, Any]:
        return {
            "show_suggested_actions": True,
            "show_timestamps": True,
            "max_visible_messages": 20,
            "auto_scroll": True
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """DM Display should not appear on character sheet - it has its own page."""
        return {
            "visible": False,
            "category": "info",
            "priority": 0,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer for DM chat interface."""
        from markupsafe import escape

        if not engine or not entity_id:
            return '<p>DM interface not available</p>'

        # Get conversation component to load messages
        conversation = engine.get_component(entity_id, 'Conversation')
        messages = []

        if conversation:
            message_ids = conversation.data.get('message_ids', [])
            max_messages = data.get('max_visible_messages', 20)
            recent_ids = message_ids[-max_messages:]  # Get most recent messages

            for msg_id in recent_ids:
                msg_entity = engine.get_entity(msg_id)
                if msg_entity and msg_entity.is_active():
                    msg_comp = engine.get_component(msg_id, 'ChatMessage')
                    if msg_comp:
                        messages.append({
                            'id': msg_id,
                            'data': msg_comp.data
                        })

        # Build HTML
        html = [f'<div id="dm-chat-{escape(entity_id)}" class="dm-chat-container">']

        # Chat messages
        html.append('<div class="dm-messages" id="dm-messages-{}" style="max-height: 400px; overflow-y: auto; margin-bottom: 1rem; padding: 0.5rem; background: linear-gradient(145deg, #1a1520, #211528); border: 1px solid #3d2b4d; border-radius: 8px;">'.format(escape(entity_id)))

        if messages:
            for msg in messages:
                msg_data = msg['data']
                speaker = msg_data.get('speaker', 'unknown')
                speaker_name = msg_data.get('speaker_name', speaker.title())
                message = msg_data.get('message', '')
                timestamp = msg_data.get('timestamp', '')
                suggested_actions = msg_data.get('suggested_actions', [])

                # Different styling based on speaker
                if speaker == 'dm':
                    speaker_color = '#d4af37'  # Gold
                    bg_color = 'rgba(212, 175, 55, 0.1)'
                elif speaker == 'player':
                    speaker_color = '#4a9eff'  # Blue
                    bg_color = 'rgba(74, 158, 255, 0.1)'
                else:  # system
                    speaker_color = '#9b59b6'  # Purple
                    bg_color = 'rgba(155, 89, 182, 0.1)'

                html.append(f'''
                    <div class="dm-message" style="margin-bottom: 0.75rem; padding: 0.75rem; background: {bg_color}; border-left: 3px solid {speaker_color}; border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                            <strong style="color: {speaker_color}; font-family: 'Cinzel', serif;">{escape(speaker_name)}</strong>
                ''')

                if data.get('show_timestamps') and timestamp:
                    html.append(f'<span style="font-size: 0.8rem; color: #6a5a7a;">{escape(timestamp.split("T")[1].split(".")[0] if "T" in timestamp else timestamp)}</span>')

                html.append('</div>')
                html.append(f'<div style="color: #f0e6d6; line-height: 1.5;">{escape(message)}</div>')

                # Suggested actions
                if data.get('show_suggested_actions') and suggested_actions:
                    html.append('<div style="margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.5rem;">')
                    for action in suggested_actions:
                        label = action.get('label', 'Action')
                        action_type = action.get('action_type', 'custom')
                        action_data = action.get('action_data', {})

                        html.append(f'''
                            <button class="dm-suggested-action"
                                    style="padding: 0.4rem 0.75rem; background: linear-gradient(135deg, #d4af37, #b8942b); color: #1a1520; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; font-family: 'Cinzel', serif; transition: all 0.2s;"
                                    onmouseover="this.style.background='linear-gradient(135deg, #ffd700, #d4af37)'"
                                    onmouseout="this.style.background='linear-gradient(135deg, #d4af37, #b8942b)'"
                                    onclick="executeSuggestedAction('{escape(entity_id)}', '{escape(action_type)}', {escape(str(action_data).replace("'", '"'))})">
                                {escape(label)}
                            </button>
                        ''')
                    html.append('</div>')

                html.append('</div>')
        else:
            html.append('<p style="color: #6a5a7a; font-style: italic; text-align: center; padding: 2rem;">No messages yet. Say hello to the DM!</p>')

        html.append('</div>')

        # Message input
        html.append(f'''
            <div class="dm-input-container" style="display: flex; gap: 0.5rem;">
                <input type="text"
                       id="dm-input-{escape(entity_id)}"
                       placeholder="Speak with the DM..."
                       style="flex: 1; padding: 0.75rem; background: #211528; border: 1px solid #3d2b4d; border-radius: 6px; color: #f0e6d6; font-family: inherit;"
                       onkeypress="if(event.key==='Enter') sendDMMessage('{escape(entity_id)}')">
                <button onclick="sendDMMessage('{escape(entity_id)}')"
                        style="padding: 0.75rem 1.5rem; background: linear-gradient(135deg, #d4af37, #b8942b); color: #1a1520; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-family: 'Cinzel', serif; transition: all 0.2s;"
                        onmouseover="this.style.background='linear-gradient(135deg, #ffd700, #d4af37)'"
                        onmouseout="this.style.background='linear-gradient(135deg, #d4af37, #b8942b)'">
                    Send
                </button>
            </div>
        ''')

        html.append('</div>')

        # JavaScript for chat interactions
        html.append('''
            <script>
            function sendDMMessage(entityId) {
                const input = document.getElementById('dm-input-' + entityId);
                const message = input.value.trim();

                if (!message) return;

                fetch('/api/dm/message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        entity_id: entityId,
                        message: message
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        input.value = '';
                        reloadDMChat(entityId);
                    } else {
                        alert('Failed to send message: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    console.error('DM message error:', error);
                    alert('Failed to send message');
                });
            }

            function reloadDMChat(entityId) {
                fetch('/api/dm/chat_display/' + entityId)
                .then(response => response.text())
                .then(html => {
                    const container = document.getElementById('dm-chat-' + entityId);
                    if (container) {
                        container.outerHTML = html;

                        // Auto-scroll to bottom
                        const messagesDiv = document.getElementById('dm-messages-' + entityId);
                        if (messagesDiv) {
                            messagesDiv.scrollTop = messagesDiv.scrollHeight;
                        }
                    }
                })
                .catch(error => {
                    console.error('Failed to reload DM chat:', error);
                });
            }

            function executeSuggestedAction(entityId, actionType, actionData) {
                fetch('/api/dm/execute_action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        entity_id: entityId,
                        action_type: actionType,
                        action_data: actionData
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        reloadDMChat(entityId);
                        // Reload character sheet if needed
                        if (data.reload_sheet) {
                            location.reload();
                        }
                    } else {
                        alert('Action failed: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    console.error('Action execution error:', error);
                    alert('Failed to execute action');
                });
            }

            // Auto-scroll on load
            document.addEventListener('DOMContentLoaded', function() {
                const messagesDiv = document.getElementById('dm-messages-' + '{{ entity_id }}');
                if (messagesDiv) {
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            });
            </script>
        ''')

        return ''.join(html)


__all__ = [
    'ChatMessageComponent',
    'ConversationComponent',
    'DMDisplayComponent'
]
