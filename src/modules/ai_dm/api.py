"""
AI DM Module API Blueprint.

Provides REST API endpoints and pages for DM chat and interaction:
- GET  /dm/chat/:id              - DM chat page (HTML)
- POST /api/dm/message          - Send message to DM
- GET  /api/dm/chat_display/:id - Get rendered chat HTML
- POST /api/dm/execute_action   - Execute suggested action
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session, current_app, render_template, redirect, url_for, flash
from src.core.module_loader import ModuleLoader

logger = logging.getLogger(__name__)

# Create blueprint for AI DM module API
# Note: We use both /dm (for pages) and /api/dm (for API endpoints)
ai_dm_bp = Blueprint('ai_dm', __name__, template_folder='templates')

# Cache for initialized modules per world
_world_modules_cache = {}


def get_engine():
    """Get the cached StateEngine for the current world."""
    world_name = session.get('world_name')
    if not world_name:
        raise ValueError('No world selected')

    engine = current_app.engine_instances.get(world_name)
    if not engine:
        raise ValueError(f'StateEngine not initialized for world: {world_name}')

    return engine


def ensure_modules_loaded():
    """Ensure modules are loaded for the current world."""
    world_name = session.get('world_name')
    if not world_name:
        return

    if world_name not in _world_modules_cache:
        world_path = session.get('world_path')
        engine = get_engine()

        logger.info(f"Loading modules for AI DM in world: {world_name}")
        loader = ModuleLoader(world_path)
        modules = loader.load_modules(strategy='config')

        for module in modules:
            try:
                module.initialize(engine)
            except Exception as e:
                logger.warning(f"Failed to initialize module {module.name}: {e}")

        _world_modules_cache[world_name] = modules
        logger.info(f"✓ Modules loaded for AI DM: {world_name}")


# ========== Page Routes ==========

@ai_dm_bp.route('/dm/chat/<entity_id>')
def dm_chat_page(entity_id: str):
    """
    DM Chat page for a character.

    Displays the full chat interface in a dedicated page instead of
    cluttering the character sheet.
    """
    try:
        world_name = session.get('world_name')
        if not world_name:
            flash('No world selected', 'error')
            return redirect(url_for('index'))

        ensure_modules_loaded()
        engine = get_engine()

        # Get entity
        entity = engine.get_entity(entity_id)
        if not entity:
            flash('Character not found', 'error')
            return redirect(url_for('client.index'))

        # Get or create DMDisplay component
        dm_display = engine.get_component(entity_id, 'DMDisplay')
        if not dm_display:
            engine.add_component(entity_id, 'DMDisplay', {
                'show_suggested_actions': True,
                'show_timestamps': True,
                'max_visible_messages': 20,
                'auto_scroll': True
            })
            dm_display = engine.get_component(entity_id, 'DMDisplay')

        # Get or create Conversation component
        conversation = engine.get_component(entity_id, 'Conversation')
        if not conversation:
            engine.add_component(entity_id, 'Conversation', {
                'message_ids': [],
                'active': True
            })
            conversation = engine.get_component(entity_id, 'Conversation')

        # Get conversation messages
        messages = []
        if conversation:
            message_ids = conversation.data.get('message_ids', [])
            for msg_id in message_ids:
                msg_entity = engine.get_entity(msg_id)
                if msg_entity and msg_entity.is_active():
                    msg_comp = engine.get_component(msg_id, 'ChatMessage')
                    if msg_comp:
                        messages.append({
                            'id': msg_id,
                            'data': msg_comp.data
                        })

        return render_template(
            'dm_chat.html',
            entity=entity,
            messages=messages,
            dm_display_data=dm_display.data if dm_display else {}
        )

    except Exception as e:
        logger.error(f"Error loading DM chat page: {e}", exc_info=True)
        flash(f'Error loading DM chat: {str(e)}', 'error')
        return redirect(url_for('client.index'))


# ========== API Routes ==========

@ai_dm_bp.route('/api/dm/message', methods=['POST'])
def api_send_message():
    """
    Send a message to the DM.

    Request JSON:
        {
            "entity_id": "player_entity_123",
            "message": "I want to search the room"
        }

    Returns:
        {
            "success": true,
            "message_id": "msg_456",
            "dm_response": {
                "message": "You search the dusty chamber...",
                "suggested_actions": [...]
            }
        }
    """
    try:
        ensure_modules_loaded()
        engine = get_engine()

        data = request.get_json()
        entity_id = data.get('entity_id')
        message = data.get('message')

        if not entity_id or not message:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: entity_id, message'
            }), 400

        # Get or create Conversation component
        conversation = engine.get_component(entity_id, 'Conversation')
        if not conversation:
            result = engine.add_component(entity_id, 'Conversation', {
                'message_ids': [],
                'active': True
            })
            if not result.success:
                return jsonify({
                    'success': False,
                    'error': f'Failed to create conversation: {result.error}'
                }), 500
            conversation = engine.get_component(entity_id, 'Conversation')

        # Create player message entity
        entity = engine.get_entity(entity_id)
        player_name = entity.name if entity else "Player"

        player_msg_result = engine.create_entity(
            f"Player message from {player_name}",
            entity_type='message'
        )

        if not player_msg_result.success:
            return jsonify({
                'success': False,
                'error': f'Failed to create message entity: {player_msg_result.error}'
            }), 500

        player_msg_id = player_msg_result.data['id']

        # Add ChatMessage component to player message
        timestamp = datetime.utcnow().isoformat()
        engine.add_component(player_msg_id, 'ChatMessage', {
            'speaker': 'player',
            'speaker_name': player_name,
            'message': message,
            'timestamp': timestamp
        })

        # Add message to conversation history
        message_ids = conversation.data.get('message_ids', [])
        message_ids.append(player_msg_id)

        engine.update_component(entity_id, 'Conversation', {
            'message_ids': message_ids,
            'last_message_time': timestamp
        })

        # Generate DM response (for now, placeholder - will add AI later)
        dm_response_text = f"I see you said: '{message}'. (AI response coming soon!)"
        dm_suggested_actions = [
            {
                'label': '🎲 Roll Perception',
                'action_type': 'roll_dice',
                'action_data': {'dice': '1d20+0', 'label': 'Perception Check'}
            },
            {
                'label': '⚔️ Draw Weapon',
                'action_type': 'custom',
                'action_data': {'action': 'ready_weapon'}
            }
        ]

        # Create DM message entity
        dm_msg_result = engine.create_entity(
            "DM response",
            entity_type='message'
        )

        if dm_msg_result.success:
            dm_msg_id = dm_msg_result.data['id']

            engine.add_component(dm_msg_id, 'ChatMessage', {
                'speaker': 'dm',
                'speaker_name': 'Dungeon Master',
                'message': dm_response_text,
                'timestamp': datetime.utcnow().isoformat(),
                'suggested_actions': dm_suggested_actions
            })

            # Add DM message to conversation
            message_ids.append(dm_msg_id)
            engine.update_component(entity_id, 'Conversation', {
                'message_ids': message_ids,
                'last_message_time': datetime.utcnow().isoformat()
            })

            return jsonify({
                'success': True,
                'message_id': player_msg_id,
                'dm_response': {
                    'message_id': dm_msg_id,
                    'message': dm_response_text,
                    'suggested_actions': dm_suggested_actions
                }
            })
        else:
            # Player message sent but DM response failed
            return jsonify({
                'success': True,
                'message_id': player_msg_id,
                'dm_response': None
            })

    except Exception as e:
        logger.error(f"Error sending DM message: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_dm_bp.route('/api/dm/chat_display/<entity_id>')
def api_chat_display(entity_id: str):
    """
    Get rendered chat display HTML for an entity.

    Returns just the DM chat HTML without reloading the page.
    """
    try:
        ensure_modules_loaded()
        engine = get_engine()

        # Get entity
        entity = engine.get_entity(entity_id)
        if not entity:
            return '<p>Error: Entity not found</p>', 404

        # Get DMDisplay component
        dm_display = engine.get_component(entity_id, 'DMDisplay')
        if not dm_display:
            return '<p>No DM display component found</p>', 404

        # Get component definition
        comp_def = engine.component_validators.get('DMDisplay')
        if not comp_def:
            return '<p>Error: DMDisplay component definition not found</p>', 500

        # Render the chat display
        html = comp_def.get_character_sheet_renderer(
            dm_display.data,
            engine,
            entity_id
        )

        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    except Exception as e:
        logger.error(f"Error rendering DM chat for entity {entity_id}: {e}", exc_info=True)
        return f'<p>Error: {str(e)}</p>', 500


@ai_dm_bp.route('/api/dm/execute_action', methods=['POST'])
def api_execute_action():
    """
    Execute a suggested action from the DM.

    Request JSON:
        {
            "entity_id": "player_123",
            "action_type": "roll_dice",
            "action_data": {"dice": "1d20+5", "label": "Perception"}
        }

    Returns:
        {
            "success": true,
            "result": {...},
            "reload_sheet": false
        }
    """
    try:
        ensure_modules_loaded()
        engine = get_engine()

        data = request.get_json()
        entity_id = data.get('entity_id')
        action_type = data.get('action_type')
        action_data = data.get('action_data', {})

        if not entity_id or not action_type:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: entity_id, action_type'
            }), 400

        reload_sheet = False

        # Handle different action types
        if action_type == 'roll_dice':
            # Trigger dice roll via WebSocket (if RNG module available)
            dice = action_data.get('dice', '1d20')
            label = action_data.get('label', 'Custom Roll')

            # Create a system message about the roll
            conversation = engine.get_component(entity_id, 'Conversation')
            if conversation:
                roll_msg = engine.create_entity(
                    f"Roll: {label}",
                    entity_type='message'
                )

                if roll_msg.success:
                    engine.add_component(roll_msg.data['id'], 'ChatMessage', {
                        'speaker': 'system',
                        'speaker_name': 'System',
                        'message': f"🎲 Rolling {dice} for {label}...",
                        'timestamp': datetime.utcnow().isoformat()
                    })

                    message_ids = conversation.data.get('message_ids', [])
                    message_ids.append(roll_msg.data['id'])
                    engine.update_component(entity_id, 'Conversation', {
                        'message_ids': message_ids
                    })

            result_data = {
                'type': 'roll_dice',
                'dice': dice,
                'label': label
            }

        elif action_type == 'custom':
            # Generic custom action
            action_name = action_data.get('action', 'unknown')

            result_data = {
                'type': 'custom',
                'action': action_name
            }

        else:
            return jsonify({
                'success': False,
                'error': f'Unknown action type: {action_type}'
            }), 400

        return jsonify({
            'success': True,
            'result': result_data,
            'reload_sheet': reload_sheet
        })

    except Exception as e:
        logger.error(f"Error executing action: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


__all__ = ['ai_dm_bp']
