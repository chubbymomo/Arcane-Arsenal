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


def multi_turn_streaming_handler(
    llm_messages,
    system_prompt,
    llm_client,
    engine,
    entity_id,
    tools,
    config,
    max_turns=10,
    stream_to_client=False
):
    """
    Unified multi-turn streaming handler for AI DM interactions.

    Handles the complete interaction loop:
    - Streams text and filters <actions> tags
    - Collects tool use requests
    - Executes tools and feeds results back
    - Continues until AI provides final narrative

    Args:
        llm_messages: Initial message history for the LLM
        system_prompt: System prompt for the LLM
        llm_client: LLM client instance
        engine: StateEngine instance
        entity_id: ID of the character entity
        tools: Tool definitions for the LLM
        config: Configuration object with AI settings
        max_turns: Maximum number of turns (default 10)
        stream_to_client: If True, yields SSE events for frontend streaming

    Yields:
        If stream_to_client=True: SSE event strings (data: {...}\n\n)

    Returns:
        dict with keys:
            - full_response: Complete text response from AI
            - narrative: Parsed narrative text (without <actions> tags)
            - suggested_actions: List of suggested action dicts
            - tool_uses_count: Total number of tools used across all turns
    """
    import json
    from .tools import execute_tool
    from .response_parser import parse_dm_response

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

    full_response = ""
    total_tool_uses = 0
    turn_number = 1

    while turn_number <= max_turns:
        logger.info(f"=== Turn {turn_number}: Waiting for AI response ===")

        # Reset for this turn
        in_actions_block = False
        buffer = ""
        current_tool = None
        tool_input_json = ""
        tool_uses = []

        for chunk in llm_client.generate_response_stream(
            messages=llm_messages,
            system=system_prompt,
            max_tokens=config.ai_max_tokens,
            temperature=config.ai_temperature if turn_number == 1 else config.ai_temperature,
            tools=tools if tools else None
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
                    if filtered.strip() and stream_to_client:
                        yield f"data: {json.dumps({'type': 'token', 'content': filtered})}\n\n"
                    buffer = ""
                elif '<actions>' in combined:
                    # Opening tag - start filtering
                    in_actions_block = True
                    before_actions = combined.split('<actions>')[0]
                    if before_actions and stream_to_client:
                        yield f"data: {json.dumps({'type': 'token', 'content': before_actions})}\n\n"
                    buffer = ""
                elif '</actions>' in combined:
                    # Closing tag - stop filtering
                    in_actions_block = False
                    after_actions = combined.split('</actions>')[-1]
                    if after_actions and stream_to_client:
                        yield f"data: {json.dumps({'type': 'token', 'content': after_actions})}\n\n"
                    buffer = ""
                elif not in_actions_block:
                    # Normal content - check if combined ends with partial tag
                    holdback_len = ends_with_partial_tag(combined)

                    # Stream everything except potential partial tag
                    if len(combined) > holdback_len:
                        to_stream = combined[:len(combined) - holdback_len]
                        if to_stream and stream_to_client:
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

                # Notify frontend if streaming
                if stream_to_client:
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': chunk['tool_name']})}\n\n"
                logger.info(f"Turn {turn_number} - AI using tool: {chunk['tool_name']}")

            elif chunk['type'] == 'tool_input_delta':
                # Accumulate tool input JSON
                tool_input_json += chunk['partial_json']

        # Flush any remaining buffer content
        if buffer and not in_actions_block and stream_to_client:
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

        total_tool_uses += len(tool_uses)
        logger.info(f"=== Turn {turn_number} complete: {len(tool_uses)} tools, {len(full_response)} chars text ===")

        # If no tools used, we have the final narrative
        if not tool_uses:
            break

        # Execute tools for next turn
        logger.info(f"Executing {len(tool_uses)} tools...")
        tool_results = []
        for tool_use in tool_uses:
            logger.info(f"Executing: {tool_use['name']}")
            try:
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
                if stream_to_client:
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': tool_use['name'], 'success': result['success']})}\n\n"
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                if stream_to_client:
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Tool execution failed: {str(e)}'})}\n\n"

        # Prepare next turn with tool results
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

        turn_number += 1

    logger.debug(f"Streaming complete. Full response length: {len(full_response)} chars")
    logger.debug(f"Response preview: {full_response[:200]}...")

    # Parse complete response for actions
    logger.info("Parsing AI response for narrative and actions...")
    narrative, suggested_actions = parse_dm_response(full_response)
    logger.info(f"Parse complete: {len(narrative)} chars narrative, {len(suggested_actions)} actions")

    result = {
        'full_response': full_response,
        'narrative': narrative,
        'suggested_actions': suggested_actions,
        'tool_uses_count': total_tool_uses
    }

    # Always yield the final result as the last event
    # Callers can identify it by checking for the 'narrative' key
    yield result


def generate_intro_for_character(engine, entity_id, scenario_suggestion=None):
    """
    Generate AI intro for a character.

    Args:
        engine: StateEngine instance
        entity_id: ID of the character entity
        scenario_suggestion: Optional user suggestion for the scenario

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

        # Build intro prompt with optional user suggestion
        intro_prompt = (
            "Create a compelling, ORIGINAL opening scene for this character's adventure. "
            "Be creative and unexpected - avoid clichés and make each intro memorable and distinct.\n"
            "\n"
        )

        # Add user suggestion if provided
        if scenario_suggestion:
            intro_prompt += (
                f"USER'S SCENARIO SUGGESTION:\n"
                f"{scenario_suggestion}\n"
                "\n"
                "IMPORTANT: Incorporate the user's suggestion into your opening scene. Use their ideas as "
                "inspiration while expanding on them with your own creative details. Make sure the final "
                "scenario aligns with what they requested while still being engaging and well-crafted.\n"
                "\n"
            )

        intro_prompt += (
            "VARIETY IS ESSENTIAL:\n"
            "- Choose starting locations that fit the character: festivals, wilderness, ships, workshops, "
            "courts, temples, markets, ruins, or anywhere interesting\n"
            "- Skip generic taverns unless they truly fit\n"
            "- Give NPCs distinctive personalities and avoid overused fantasy names\n"
            "- Create unique situations with hooks that immediately engage\n"
            "- Match tone and setting to character class/background\n"
            "\n"
            "LOCATION HIERARCHY (CRITICAL):\n"
            "- Build location hierarchies: Create parent locations (regions, areas) FIRST\n"
            "- Example: create_location(name='The Shadowfen Marshes', location_type='region', region='wilderness') FIRST\n"
            "- Then: create_location(name='Ancient Temple', parent_location_name='The Shadowfen Marshes')\n"
            "- NEVER use region names that aren't created location entities\n"
            "- Use parent_location_name to establish proper containment hierarchies\n"
            "\n"
            "SPATIAL POSITIONING (CRITICAL):\n"
            "- Position player in LEAF locations (specific rooms/areas), NEVER in parent containers\n"
            "- If you create sub-locations within a parent, position player in one of the CHILDREN\n"
            "- WRONG: Create parent 'Sunken Archives' with child 'North Passage', position player in parent\n"
            "- RIGHT: Create 'Sunken Archives', create 'Main Hall' as child, create 'North Passage' as child, position in 'Main Hall'\n"
            "- Think: player is in a ROOM within a BUILDING, not 'in the building' generally\n"
            "\n"
            "ITEM OWNERSHIP (Important):\n"
            "- Player starts with EMPTY inventory - you can give them starting gear if appropriate\n"
            "- To give starting gear: create_item with player's name as owner\n"
            "- For environment items: create_item with location as owner, describe it, let player interact\n"
            "- Rule: Only narrate player using items they actually own (check inventory or use transfer_item)\n"
            "\n"
            "Use tools to create NPCs, locations, and items. Be vivid and immersive - no meta-gaming."
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

        logger.info("=== Starting AI intro generation ===")
        logger.info(f"Entity: {entity_id}")
        logger.info(f"Tools available: {len(anthropic_tools)}")

        # Initial message for intro generation
        llm_messages = [{'role': 'user', 'content': intro_prompt}]

        # Use the unified multi-turn streaming handler
        # Note: stream_to_client=False since intro generation doesn't stream to frontend
        # The handler is a generator, so we consume it to get the final result
        result = None
        for event in multi_turn_streaming_handler(
            llm_messages=llm_messages,
            system_prompt=full_system_prompt,
            llm_client=llm,
            engine=engine,
            entity_id=entity_id,
            tools=anthropic_tools,
            config=config,
            max_turns=10,
            stream_to_client=False
        ):
            result = event  # The final event is the result dict

        intro_text = result['narrative']
        intro_actions = result['suggested_actions']

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

        # Check if player was already positioned by AI during intro generation
        # If move_player_to_location was used, respect that choice - don't override!
        position = engine.get_component(entity_id, 'Position')
        current_region = position.data.get('region') if position else None

        # Check if current position is already a valid location entity
        starting_location_id = None
        if current_region and current_region.startswith('entity_'):
            # Player is already positioned at a location entity - check if it's valid
            location_comp = engine.get_component(current_region, 'Location')
            if location_comp:
                # Player was already positioned correctly by AI tools
                starting_location_id = current_region
                logger.info(f"Player already positioned at location {current_region} by AI - keeping this position")
            else:
                # Position references an entity that's not a location - need to fix
                logger.warning(f"Player position references non-location entity {current_region} - will reposition")
                current_region = None

        # Only reposition if player wasn't already positioned at a valid location
        if not starting_location_id:
            location_entities = engine.query_entities(['Location'])
            if location_entities:
                # Get the first location as fallback
                starting_location = location_entities[0]
                logger.info(f"Found fallback location: {starting_location.name} ({starting_location.id})")

                # Update player's Position to be AT this location (entity-based)
                if position:
                    engine.update_component(entity_id, 'Position', {
                        **position.data,
                        'region': starting_location.id  # Entity reference!
                    })
                    starting_location_id = starting_location.id
                    logger.info(f"  → Moved player to fallback location entity: {starting_location.id}")
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

                # Use the unified multi-turn streaming handler
                # stream_to_client=True enables SSE streaming to the frontend
                for event in multi_turn_streaming_handler(
                    llm_messages=llm_messages,
                    system_prompt=full_system_prompt,
                    llm_client=llm,
                    engine=engine,
                    entity_id=entity_id,
                    tools=anthropic_tools,
                    config=config,
                    max_turns=10,
                    stream_to_client=True
                ):
                    # If this is the final result (returned at the end), extract it
                    if isinstance(event, dict) and 'narrative' in event:
                        # This is the return value from the handler
                        narrative = event['narrative']
                        suggested_actions = event['suggested_actions']
                        break
                    else:
                        # This is a streaming event - yield it to the client
                        yield event

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
