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


def generate_intro_for_character(engine, entity_id):
    """
    Generate AI intro for a character.

    Args:
        engine: StateEngine instance
        entity_id: ID of the character entity

    Returns:
        dict with keys: success, message_id, intro_text, starting_location_id, error
    """
    import json
    from .llm_client import get_llm_client, LLMError
    from .prompts import build_full_prompt
    from .response_parser import parse_dm_response
    from .tools import get_tool_definitions, execute_tool
    from src.core.config import get_config

    try:
        # Verify entity exists
        entity = engine.get_entity(entity_id)
        if not entity:
            return {'success': False, 'error': f'Entity {entity_id} not found'}

        # Create Conversation component if missing
        conversation = engine.get_component(entity_id, 'Conversation')
        if not conversation:
            result = engine.add_component(entity_id, 'Conversation', {
                'message_ids': []
            })
            if not result.success:
                return {'success': False, 'error': f'Failed to create conversation: {result.error}'}

        # Build context and generate intro
        ai_context = engine.generate_ai_context(entity_id)
        full_system_prompt = build_full_prompt(ai_context)

        intro_prompt = (
            "This is the very beginning of the adventure. "
            "Create an engaging, UNIQUE opening scene that introduces the character to their starting location. "
            "Set the mood, describe the environment, and present an initial situation that draws them in. "
            "\n\n"
            "IMPORTANT - CREATE VARIETY:\n"
            "- Avoid generic taverns unless the character's class/background specifically suggests it\n"
            "- Consider diverse starting locations: festivals, caravans, wilderness camps, merchant shops, "
            "noble courts, guild halls, temples, city gates, docks, markets, ruins, etc.\n"
            "- Create NPCs with distinct, memorable names and personalities (avoid common fantasy names)\n"
            "- Match the starting scenario to the character's class and background when possible\n"
            "- Add unexpected twists or unique situations that immediately engage the player\n"
            "\n"
            "CRITICAL - ITEM OWNERSHIP:\n"
            "- The player's inventory is EMPTY at the start (check the Inventory section)\n"
            "- You CAN give the player starting items if appropriate for their character/backstory\n"
            "- BUT you MUST use transfer_item to actually give them ownership first\n"
            "- Two valid approaches:\n"
            "  1. **Starting gear**: create_item owned by player's name → player starts with it\n"
            "  2. **Environmental items**: create_item owned by location → mention it's there → "
            "let player choose to interact via action buttons\n"
            "- NEVER write narrative about player using an item without first checking/transferring ownership\n"
            "- Example GOOD (starting gear): create_item 'Traveling Cloak' owned by 'Sam' → "
            "'Your traveling cloak...'\n"
            "- Example GOOD (environment): create_item 'Journal' owned by 'The Library' → "
            "'A weathered journal lies on the table'\n"
            "- Example BAD: create_item 'Journal' owned by location → 'You pick up and read the journal' "
            "(FAILS - need transfer_item first!)\n"
            "\n"
            "Use your available tools to create NPCs, locations, and items as needed to make the world come alive. "
            "Remember: no meta-gaming, just vivid narrative."
        )

        config = get_config()
        llm = get_llm_client(config)
        tools = get_tool_definitions()

        # Convert tools to Anthropic format
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            })

        # Accumulate response and execute tools
        full_response = ""
        tool_uses = []
        current_tool = None
        tool_input_json = ""

        logger.info("=== Starting AI intro generation ===")
        logger.info(f"Entity: {entity_id}")
        logger.info(f"Tools available: {len(anthropic_tools)}")

        # First turn: Let Claude use tools
        llm_messages = [{'role': 'user', 'content': intro_prompt}]

        for chunk in llm.generate_response_stream(
            messages=llm_messages,
            system=full_system_prompt,
            max_tokens=config.ai_max_tokens,
            temperature=config.ai_temperature,
            tools=anthropic_tools if anthropic_tools else None
        ):
            if chunk['type'] == 'text':
                full_response += chunk['content']
            elif chunk['type'] == 'tool_use_start':
                # Save previous tool if exists
                if current_tool and tool_input_json:
                    try:
                        tool_uses.append({
                            'id': current_tool['id'],
                            'name': current_tool['name'],
                            'input': json.loads(tool_input_json)
                        })
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse tool input for {current_tool['name']}")

                current_tool = {
                    'id': chunk['tool_use_id'],
                    'name': chunk['tool_name']
                }
                tool_input_json = ""
                logger.info(f"Tool use START: {chunk['tool_name']} (id: {chunk['tool_use_id']})")
            elif chunk['type'] == 'tool_input_delta':
                tool_input_json += chunk['partial_json']

        # Save last tool
        if current_tool and tool_input_json:
            try:
                tool_uses.append({
                    'id': current_tool['id'],
                    'name': current_tool['name'],
                    'input': json.loads(tool_input_json)
                })
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse final tool input: {e}")

        logger.info(f"=== First turn complete: {len(tool_uses)} tools, {len(full_response)} chars text ===")

        # Execute all tools
        tool_results = []
        if tool_uses:
            logger.info(f"=== Executing {len(tool_uses)} tools ===")
            for tool_use in tool_uses:
                logger.info(f"Executing: {tool_use['name']}")
                result = execute_tool(
                    tool_use['name'],
                    tool_use['input'],
                    engine,
                    entity_id
                )
                tool_results.append({
                    'tool_use_id': tool_use['id'],
                    'result': result
                })
                logger.info(f"  Result: {result['success']} - {result['message']}")

            # Second turn: Give Claude the tool results and ask for narrative
            logger.info("=== Second turn: Asking Claude for narrative ===")

            # Build tool result content
            tool_result_content = []
            for tr in tool_results:
                result_text = tr['result']['message']
                tool_result_content.append({
                    'type': 'tool_result',
                    'tool_use_id': tr['tool_use_id'],
                    'content': result_text
                })

            # Add assistant message with tool uses
            llm_messages.append({
                'role': 'assistant',
                'content': [{'type': 'tool_use', 'id': tu['id'], 'name': tu['name'], 'input': tu['input']} for tu in tool_uses]
            })

            # Add user message with tool results
            llm_messages.append({
                'role': 'user',
                'content': tool_result_content
            })

            # Get narrative response
            full_response = ""
            for chunk in llm.generate_response_stream(
                messages=llm_messages,
                system=full_system_prompt,
                max_tokens=config.ai_max_tokens,
                temperature=config.ai_temperature,
                tools=None  # No tools in second turn
            ):
                if chunk['type'] == 'text':
                    full_response += chunk['content']

            logger.info(f"=== Second turn complete: {len(full_response)} chars narrative ===")

        logger.info(f"=== Final response: {full_response[:300]}... ===")

        intro_text, intro_actions = parse_dm_response(full_response)
        logger.info(f"=== Parsed intro ===")
        logger.info(f"Intro text length: {len(intro_text)} chars")
        logger.info(f"Intro actions: {intro_actions}")

        # Create intro message entity
        dm_msg_result = engine.create_entity("DM intro message")
        if not dm_msg_result.success:
            return {'success': False, 'error': 'Failed to create intro message entity'}

        dm_msg_id = dm_msg_result.data['id']

        engine.add_component(dm_msg_id, 'ChatMessage', {
            'speaker': 'dm',
            'speaker_name': 'Dungeon Master',
            'message': intro_text,
            'timestamp': datetime.utcnow().isoformat(),
            'suggested_actions': intro_actions
        })

        # Add to conversation
        conversation = engine.get_component(entity_id, 'Conversation')
        message_ids = conversation.data.get('message_ids', []) if conversation else []
        message_ids.append(dm_msg_id)
        engine.update_component(entity_id, 'Conversation', {
            'message_ids': message_ids
        })

        logger.info(f"Generated AI intro for character {entity_id}")

        # Entity-based positioning: Move player to created location if any
        location_entities = engine.query_entities(['Location'])
        starting_location_id = None
        if location_entities:
            # Get the first (most recent) location
            starting_location = location_entities[0]
            logger.info(f"Found starting location: {starting_location.name} ({starting_location.id})")

            # Update player's Position to be AT this location (entity-based)
            position = engine.get_component(entity_id, 'Position')
            if position:
                engine.update_component(entity_id, 'Position', {
                    **position.data,
                    'region': starting_location.id  # Entity reference!
                })
                starting_location_id = starting_location.id
                logger.info(f"  → Moved player to location entity: {starting_location.id}")
        else:
            logger.warning("No location entities found after AI intro - player remains in named region")

        return {
            'success': True,
            'message_id': dm_msg_id,
            'intro_text': intro_text,
            'starting_location_id': starting_location_id
        }

    except LLMError as e:
        logger.error(f"LLM error during intro generation: {e}", exc_info=True)
        return {'success': False, 'error': f'AI service error: {str(e)}'}

    except Exception as e:
        logger.error(f"Failed to generate AI intro: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


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


@ai_dm_bp.route('/api/dm/message_stream', methods=['POST'])
def send_dm_message_stream():
    """
    Send a message to the DM and stream the response.

    Uses Server-Sent Events (SSE) to stream the AI response as it's generated.

    Request JSON:
        {
            "entity_id": "player_entity_123",
            "message": "I want to search the room"
        }

    Streams:
        data: {"type": "token", "content": "You"}
        data: {"type": "token", "content": " search"}
        data: {"type": "token", "content": " the"}
        ...
        data: {"type": "done", "message_id": "msg_456", "suggested_actions": [...]}
    """
    import json
    from flask import Response, stream_with_context

    def generate():
        try:
            ensure_modules_loaded()
            engine = get_engine()

            data = request.get_json()
            entity_id = data.get('entity_id')
            message = data.get('message')
            skip_player_message = data.get('skip_player_message', False)  # New flag

            if not entity_id or not message:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Missing required fields'})}\n\n"
                return

            # Get or create Conversation component
            conversation = engine.get_component(entity_id, 'Conversation')
            if not conversation:
                result = engine.add_component(entity_id, 'Conversation', {
                    'message_ids': [],
                    'active': True
                })
                if not result.success:
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Failed to create conversation'})}\n\n"
                    return
                conversation = engine.get_component(entity_id, 'Conversation')

            # Get message_ids from conversation (needed for both paths)
            message_ids = conversation.data.get('message_ids', [])

            # Create player message entity (unless skip_player_message is true)
            if not skip_player_message:
                entity = engine.get_entity(entity_id)
                player_name = entity.name if entity else "Player"

                player_msg_result = engine.create_entity(f"Player message from {player_name}")

                if not player_msg_result.success:
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Failed to create message entity'})}\n\n"
                    return

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
                message_ids.append(player_msg_id)

                engine.update_component(entity_id, 'Conversation', {
                    'message_ids': message_ids,
                    'last_message_time': timestamp
                })

            # Generate DM response using streaming LLM with tools
            try:
                from .llm_client import get_llm_client, LLMError
                from .prompts import build_full_prompt, build_message_history
                from .response_parser import parse_dm_response, get_fallback_actions
                from .tools import get_tool_definitions, execute_tool
                from src.core.config import get_config

                logger.info(f"Generating streaming AI response for entity {entity_id}")
                ai_context = engine.generate_ai_context(entity_id)

                # Get conversation history
                conversation_messages = []
                # If we created a player message, exclude it from history (it'll be added via player_message param)
                # If we skipped creating it, include all messages
                msg_list = message_ids[:-1] if not skip_player_message else message_ids
                for msg_id in msg_list:
                    msg_entity = engine.get_entity(msg_id)
                    if msg_entity and msg_entity.is_active():
                        msg_comp = engine.get_component(msg_id, 'ChatMessage')
                        if msg_comp:
                            conversation_messages.append(msg_comp.data)

                # Build prompts
                full_system_prompt = build_full_prompt(ai_context)
                llm_messages = build_message_history(conversation_messages, player_message=message)

                # Get LLM client and tool definitions
                config = get_config()
                llm = get_llm_client(config)
                tools = get_tool_definitions()

                # Convert tools to Anthropic format
                anthropic_tools = []
                for tool in tools:
                    anthropic_tools.append({
                        "name": tool["name"],
                        "description": tool["description"],
                        "input_schema": tool["input_schema"]
                    })

                # Accumulate full response and tool uses (TWO-TURN PATTERN)
                full_response = ""
                def ends_with_partial_tag(text: str) -> int:
                    """
                    Check if text ends with a partial <actions> or </actions> tag.
                    Returns the length of the partial tag if found, 0 otherwise.
                    """
                    tags = ['<actions>', '</actions>']
                    max_partial_len = 0
                    for tag in tags:
                        # Check all prefixes of the tag (e.g., '<', '<a', '<ac', etc.)
                        for i in range(1, len(tag)):
                            prefix = tag[:i]
                            if text.endswith(prefix):
                                max_partial_len = max(max_partial_len, len(prefix))
                    return max_partial_len

                current_tool = None
                tool_input_json = ""
                tool_uses = []
                in_actions_block = False  # Track if we're inside <actions> tags
                buffer = ""  # Buffer to detect tags split across chunks

                # TURN 1: Let AI use tools (accumulate, don't execute yet)
                for chunk in llm.generate_response_stream(
                    messages=llm_messages,
                    system=full_system_prompt,
                    max_tokens=config.ai_max_tokens,
                    temperature=config.ai_temperature,
                    tools=anthropic_tools if anthropic_tools else None
                ):
                    if chunk['type'] == 'text':
                        # Accumulate text from first turn (usually empty when tools used)
                        content = chunk['content']
                        full_response += content

                        # Combine buffer with new content to detect tags across boundaries
                        combined = buffer + content

                        # Filter out <actions> block from streaming
                        # Handle case where entire block is in combined content
                        if '<actions>' in combined and '</actions>' in combined:
                            # Complete actions block - remove it entirely
                            before = combined.split('<actions>')[0]
                            after = combined.split('</actions>')[-1]
                            filtered = before + after
                            if filtered.strip():
                                yield f"data: {json.dumps({'type': 'token', 'content': filtered})}\n\n"
                            buffer = ""
                        elif '<actions>' in combined:
                            # Opening tag - start filtering
                            in_actions_block = True
                            before_actions = combined.split('<actions>')[0]
                            if before_actions:
                                yield f"data: {json.dumps({'type': 'token', 'content': before_actions})}\n\n"
                            buffer = ""
                        elif '</actions>' in combined:
                            # Closing tag - stop filtering
                            in_actions_block = False
                            after_actions = combined.split('</actions>')[-1]
                            if after_actions:
                                yield f"data: {json.dumps({'type': 'token', 'content': after_actions})}\n\n"
                            buffer = ""
                        elif not in_actions_block:
                            # Normal content - check if combined ends with partial tag
                            holdback_len = ends_with_partial_tag(combined)

                            # Stream everything except potential partial tag
                            if len(combined) > holdback_len:
                                to_stream = combined[:len(combined) - holdback_len]
                                if to_stream:
                                    yield f"data: {json.dumps({'type': 'token', 'content': to_stream})}\n\n"

                            # Keep potential partial tag in buffer
                            buffer = combined[-holdback_len:] if holdback_len > 0 else ""
                        else:
                            # Inside actions block, skip streaming
                            buffer = ""

                    elif chunk['type'] == 'tool_use_start':
                        # Save previous tool if exists
                        if current_tool and tool_input_json:
                            try:
                                tool_uses.append({
                                    'id': current_tool['id'],
                                    'name': current_tool['name'],
                                    'input': json.loads(tool_input_json)
                                })
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse tool input for {current_tool['name']}")

                        # Start new tool
                        current_tool = {
                            'id': chunk['tool_use_id'],
                            'name': chunk['tool_name']
                        }
                        tool_input_json = ""
                        # Notify frontend
                        yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': chunk['tool_name']})}\n\n"
                        logger.info(f"AI using tool: {chunk['tool_name']}")

                    elif chunk['type'] == 'tool_input_delta':
                        # Accumulate tool input JSON
                        tool_input_json += chunk['partial_json']

                # Flush any remaining buffer content at end of Turn 1
                if buffer and not in_actions_block:
                    yield f"data: {json.dumps({'type': 'token', 'content': buffer})}\n\n"

                # Save last tool
                if current_tool and tool_input_json:
                    try:
                        tool_uses.append({
                            'id': current_tool['id'],
                            'name': current_tool['name'],
                            'input': json.loads(tool_input_json)
                        })
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse final tool input: {e}")

                # Execute all tools if any were used
                if tool_uses:
                    logger.info(f"Executing {len(tool_uses)} tools...")
                    tool_results = []
                    for tool_use in tool_uses:
                        try:
                            logger.info(f"Executing tool {tool_use['name']} with input: {tool_use['input']}")

                            result = execute_tool(
                                tool_use['name'],
                                tool_use['input'],
                                engine,
                                entity_id
                            )

                            tool_results.append({
                                'tool_use_id': tool_use['id'],
                                'result': result
                            })

                            # Notify frontend
                            yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': tool_use['name'], 'result': result})}\n\n"

                        except Exception as e:
                            logger.error(f"Tool execution failed: {e}")
                            yield f"data: {json.dumps({'type': 'error', 'error': f'Tool execution failed: {str(e)}'})}\n\n"

                    # TURN 2: Give AI the tool results and get narrative
                    logger.info("Second turn: Asking AI for narrative based on tool results...")

                    # Build tool result content for second turn
                    tool_result_content = []
                    for tr in tool_results:
                        result_text = tr['result']['message']
                        tool_result_content.append({
                            'type': 'tool_result',
                            'tool_use_id': tr['tool_use_id'],
                            'content': result_text
                        })

                    # Add assistant message with tool uses
                    llm_messages.append({
                        'role': 'assistant',
                        'content': [{'type': 'tool_use', 'id': tu['id'], 'name': tu['name'], 'input': tu['input']} for tu in tool_uses]
                    })

                    # Add user message with tool results
                    llm_messages.append({
                        'role': 'user',
                        'content': tool_result_content
                    })

                    # Get narrative response (stream it!)
                    full_response = ""
                    in_actions_block = False  # Reset for second turn
                    buffer = ""  # Reset buffer for second turn
                    for chunk in llm.generate_response_stream(
                        messages=llm_messages,
                        system=full_system_prompt,
                        max_tokens=config.ai_max_tokens,
                        temperature=config.ai_temperature,
                        tools=None  # No tools in second turn
                    ):
                        if chunk['type'] == 'text':
                            content = chunk['content']
                            full_response += content

                            # Combine buffer with new content to detect tags across boundaries
                            combined = buffer + content

                            # Filter out <actions> block from streaming
                            # Handle case where entire block is in combined content
                            if '<actions>' in combined and '</actions>' in combined:
                                # Complete actions block - remove it entirely
                                before = combined.split('<actions>')[0]
                                after = combined.split('</actions>')[-1]
                                filtered = before + after
                                if filtered.strip():
                                    yield f"data: {json.dumps({'type': 'token', 'content': filtered})}\n\n"
                                buffer = ""
                            elif '<actions>' in combined:
                                # Opening tag - start filtering
                                in_actions_block = True
                                before_actions = combined.split('<actions>')[0]
                                if before_actions:
                                    yield f"data: {json.dumps({'type': 'token', 'content': before_actions})}\n\n"
                                buffer = ""
                            elif '</actions>' in combined:
                                # Closing tag - stop filtering
                                in_actions_block = False
                                after_actions = combined.split('</actions>')[-1]
                                if after_actions:
                                    yield f"data: {json.dumps({'type': 'token', 'content': after_actions})}\n\n"
                                buffer = ""
                            elif not in_actions_block:
                                # Normal content - check if combined ends with partial tag
                                holdback_len = ends_with_partial_tag(combined)

                                # Stream everything except potential partial tag
                                if len(combined) > holdback_len:
                                    to_stream = combined[:len(combined) - holdback_len]
                                    if to_stream:
                                        yield f"data: {json.dumps({'type': 'token', 'content': to_stream})}\n\n"

                                # Keep potential partial tag in buffer
                                buffer = combined[-holdback_len:] if holdback_len > 0 else ""
                            else:
                                # Inside actions block, skip streaming
                                buffer = ""

                    # Flush any remaining buffer content at end of Turn 2
                    if buffer and not in_actions_block:
                        yield f"data: {json.dumps({'type': 'token', 'content': buffer})}\n\n"

                logger.debug(f"Streaming complete. Full response length: {len(full_response)} chars")
                logger.debug(f"Response preview: {full_response[:200]}...")

                # Parse complete response for actions
                logger.info("Parsing AI response for narrative and actions...")
                narrative, suggested_actions = parse_dm_response(full_response)
                logger.info(f"Parse complete: {len(narrative)} chars narrative, {len(suggested_actions)} actions")

                # Create DM message entity
                logger.debug("Creating DM message entity...")
                dm_msg_result = engine.create_entity("DM response")
                logger.debug(f"Entity creation result: success={dm_msg_result.success}")
                if dm_msg_result.success:
                    dm_msg_id = dm_msg_result.data['id']
                    dm_timestamp = datetime.utcnow().isoformat()
                    logger.debug(f"Created DM message entity: {dm_msg_id}")

                    logger.debug("Adding ChatMessage component...")
                    engine.add_component(dm_msg_id, 'ChatMessage', {
                        'speaker': 'dm',
                        'speaker_name': 'Dungeon Master',
                        'message': narrative,
                        'timestamp': dm_timestamp,
                        'suggested_actions': suggested_actions
                    })
                    logger.debug("ChatMessage component added")

                    # Add to conversation
                    logger.debug(f"Updating conversation with {len(message_ids) + 1} total messages")
                    message_ids.append(dm_msg_id)
                    engine.update_component(entity_id, 'Conversation', {
                        'message_ids': message_ids
                    })
                    logger.debug("Conversation updated")

                    # Send completion event with actions
                    logger.info(f"Sending 'done' event with {len(suggested_actions)} actions")
                    yield f"data: {json.dumps({'type': 'done', 'message_id': dm_msg_id, 'suggested_actions': suggested_actions})}\n\n"
                    logger.info("✓ AI response complete and sent to client")
                else:
                    logger.error("Failed to create DM message entity!")
                    logger.error(f"Entity creation error: {dm_msg_result.error if hasattr(dm_msg_result, 'error') else 'Unknown error'}")
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Failed to save DM response'})}\n\n"

            except LLMError as e:
                logger.error(f"LLM error during streaming: {e}")
                fallback_actions = get_fallback_actions()
                yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'fallback_actions': fallback_actions})}\n\n"

            except Exception as e:
                logger.error(f"Error during streaming response: {e}", exc_info=True)
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        except GeneratorExit:
            logger.warning("⚠️  Generator exit detected - client may have closed connection prematurely")
            raise

        except Exception as e:
            logger.error(f"Error in stream generator: {e}", exc_info=True)
            logger.error(f"Error type: {type(e).__name__}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


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


@ai_dm_bp.route('/api/dm/generate_intro', methods=['POST'])
def api_generate_intro():
    """
    Generate AI intro for a new character.

    Request JSON:
        {
            "entity_id": "character_123"
        }

    Returns:
        {
            "success": true,
            "message_id": "dm_msg_456",
            "intro_text": "The intro narrative...",
            "starting_location_id": "location_789"
        }
    """
    try:
        ensure_modules_loaded()
        engine = get_engine()

        data = request.get_json()
        entity_id = data.get('entity_id')

        if not entity_id:
            return jsonify({
                'success': False,
                'error': 'Missing required field: entity_id'
            }), 400

        # Use the shared intro generation function
        result = generate_intro_for_character(engine, entity_id)

        if not result['success']:
            status_code = 404 if 'not found' in result.get('error', '').lower() else 500
            return jsonify(result), status_code

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in generate_intro endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
                roll_msg = engine.create_entity(f"Roll: {label}")

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
            # Generic custom action - convert to a message to the DM
            action_name = action_data.get('action', 'unknown')

            # Create a user message describing the action
            conversation = engine.get_component(entity_id, 'Conversation')
            if conversation:
                # Convert action name to readable text
                action_text = action_name.replace('_', ' ').title()
                message_text = f"I want to {action_text.lower()}"

                logger.info(f"Custom action '{action_name}' converted to message: {message_text}")

                # Get entity name for the message
                entity = engine.get_entity(entity_id)
                player_name = entity.name if entity else "Player"

                # Create player message entity
                player_msg_result = engine.create_entity(f"Player message from {player_name}")
                if player_msg_result.success:
                    player_msg_id = player_msg_result.data['id']

                    engine.add_component(player_msg_id, 'ChatMessage', {
                        'speaker': 'player',
                        'speaker_name': player_name,
                        'message': message_text,
                        'timestamp': datetime.utcnow().isoformat()
                    })

                    message_ids = conversation.data.get('message_ids', [])
                    message_ids.append(player_msg_id)
                    engine.update_component(entity_id, 'Conversation', {
                        'message_ids': message_ids
                    })

            result_data = {
                'type': 'custom',
                'action': action_name,
                'message': message_text,
                'trigger_ai_response': True  # Signal frontend to trigger AI response
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
