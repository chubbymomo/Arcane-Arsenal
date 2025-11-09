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

        # Check if we need to generate an AI intro (empty conversation + needs_ai_intro flag)
        if len(messages) == 0:
            player_comp = engine.get_component(entity_id, 'PlayerCharacter')
            if player_comp and player_comp.data.get('needs_ai_intro', False):
                # Generate AI opening scene
                try:
                    from .llm_client import get_llm_client, LLMError
                    from .prompts import build_full_prompt
                    from .response_parser import parse_dm_response, get_fallback_actions
                    from src.core.config import get_config
                    from datetime import datetime

                    logger.info(f"Generating AI intro for {entity_id}")

                    # Build context for intro generation
                    ai_context = engine.generate_ai_context(entity_id)
                    full_system_prompt = build_full_prompt(ai_context)

                    # Specific prompt for generating opening scene
                    intro_prompt = (
                        "This is the very beginning of the adventure. "
                        "Create an engaging opening scene that introduces the character to their starting location. "
                        "Set the mood, describe the environment, and present an initial situation that draws them in. "
                        "Remember: no meta-gaming, just vivid narrative."
                    )

                    # Call LLM
                    config = get_config()
                    llm = get_llm_client(config)
                    raw_response = llm.generate_response(
                        messages=[{'role': 'user', 'content': intro_prompt}],
                        system=full_system_prompt,
                        max_tokens=config.ai_max_tokens,
                        temperature=config.ai_temperature
                    )

                    # Parse response
                    intro_text, intro_actions = parse_dm_response(raw_response)

                    # Create DM message entity for intro
                    dm_msg_result = engine.create_entity("DM intro message")
                    if dm_msg_result.success:
                        dm_msg_id = dm_msg_result.data['id']

                        engine.add_component(dm_msg_id, 'ChatMessage', {
                            'speaker': 'dm',
                            'speaker_name': 'Dungeon Master',
                            'message': intro_text,
                            'timestamp': datetime.utcnow().isoformat(),
                            'suggested_actions': intro_actions
                        })

                        # Add to conversation
                        message_ids.append(dm_msg_id)
                        engine.update_component(entity_id, 'Conversation', {
                            'message_ids': message_ids
                        })

                        # Add to messages list for rendering
                        messages.append({
                            'id': dm_msg_id,
                            'data': {
                                'speaker': 'dm',
                                'speaker_name': 'Dungeon Master',
                                'message': intro_text,
                                'timestamp': datetime.utcnow().isoformat(),
                                'suggested_actions': intro_actions
                            }
                        })

                        # Clear the needs_ai_intro flag
                        engine.update_component(entity_id, 'PlayerCharacter', {
                            'needs_ai_intro': False
                        })

                        logger.info(f"AI intro generated successfully for {entity_id}")

                except LLMError as e:
                    logger.error(f"Failed to generate AI intro: {e}")
                    # Continue without intro - user can start conversation manually
                except Exception as e:
                    logger.error(f"Unexpected error generating AI intro: {e}", exc_info=True)

        # Hardcoded UI preferences (no component needed)
        ui_settings = {
            'show_suggested_actions': True,
            'show_timestamps': True
        }

        return render_template(
            'dm_chat.html',
            entity=entity,
            messages=messages,
            ui_settings=ui_settings
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
            f"Player message from {player_name}"
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

        # ========== AI INTEGRATION ==========
        # Generate DM response using LLM

        try:
            from .llm_client import get_llm_client, LLMError
            from .prompts import build_full_prompt, build_message_history
            from .response_parser import parse_dm_response, get_fallback_actions
            from src.core.config import get_config

            # Generate AI context from game state
            logger.info(f"Generating AI context for entity {entity_id}")
            ai_context = engine.generate_ai_context(entity_id)

            # Get conversation history
            conversation_messages = []
            for msg_id in message_ids[:-1]:  # Exclude the message we just added
                msg_entity = engine.get_entity(msg_id)
                if msg_entity and msg_entity.is_active():
                    msg_comp = engine.get_component(msg_id, 'ChatMessage')
                    if msg_comp:
                        conversation_messages.append(msg_comp.data)

            # Build prompts
            logger.info("Building prompts for LLM")
            full_system_prompt = build_full_prompt(ai_context)
            llm_messages = build_message_history(conversation_messages)

            # Add current player message
            llm_messages.append({'role': 'user', 'content': message})

            # Get LLM client and generate response
            logger.info("Calling LLM for DM response")
            config = get_config()
            llm = get_llm_client(config)

            raw_response = llm.generate_response(
                messages=llm_messages,
                system=full_system_prompt,
                max_tokens=config.ai_max_tokens,
                temperature=config.ai_temperature
            )

            # Parse response
            logger.info("Parsing LLM response")
            dm_response_text, dm_suggested_actions = parse_dm_response(raw_response)

            logger.info(f"AI response generated: {len(dm_response_text)} chars, "
                       f"{len(dm_suggested_actions)} actions")

        except LLMError as e:
            logger.error(f"LLM error during DM response: {e}", exc_info=True)
            dm_response_text = "The DM seems distracted for a moment... (AI temporarily unavailable)"
            dm_suggested_actions = get_fallback_actions()

        except Exception as e:
            logger.error(f"Unexpected error during AI response generation: {e}", exc_info=True)
            dm_response_text = "The DM pauses, gathering their thoughts... (An error occurred)"
            dm_suggested_actions = get_fallback_actions()

        # Create DM message entity
        dm_msg_result = engine.create_entity(
            "DM response"
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
    Get rendered chat messages HTML for an entity.

    Returns just the messages HTML fragment for AJAX updates.
    """
    try:
        ensure_modules_loaded()
        engine = get_engine()

        # Get entity
        entity = engine.get_entity(entity_id)
        if not entity:
            return '<p>Error: Entity not found</p>', 404

        # Hardcoded UI settings (no component needed)
        ui_settings = {
            'show_suggested_actions': True,
            'show_timestamps': True
        }

        # Get conversation messages
        conversation = engine.get_component(entity_id, 'Conversation')
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

        # Render messages partial
        return render_template(
            'dm_chat_messages.html',
            entity=entity,
            messages=messages,
            ui_settings=ui_settings
        ), 200, {'Content-Type': 'text/html; charset=utf-8'}

    except Exception as e:
        logger.error(f"Error rendering DM chat messages for entity {entity_id}: {e}", exc_info=True)
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
