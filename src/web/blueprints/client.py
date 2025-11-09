"""
Client Blueprint - Player interface for character management.

Provides character selection, creation, and viewing for players.
Eventually will include action interface and gameplay features.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
import json as json_module
from functools import wraps

from src.core.state_engine import StateEngine
from src.web.form_builder import FormBuilder

logger = logging.getLogger(__name__)

# Create blueprint
client_bp = Blueprint('client', __name__, url_prefix='/client', template_folder='../templates/client')


def require_world(f):
    """Decorator to ensure a world is selected before accessing routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'world_path' not in session:
            flash('Please select a world first', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def get_engine() -> StateEngine:
    """Get the cached StateEngine for the current world."""
    world_name = session.get('world_name')
    if not world_name:
        raise ValueError('No world selected')

    engine = current_app.engine_instances.get(world_name)
    if not engine:
        raise ValueError(f'StateEngine not initialized for world: {world_name}')

    return engine


# ========== View Endpoints ==========

@client_bp.route('/')
@require_world
def index():
    """Character selection screen - list all player characters."""
    engine = get_engine()

    # Query for player character entities (entities with PlayerCharacter component)
    # This explicitly filters for player-controlled characters only
    # NPCs, monsters, items, and locations will not appear here
    all_entities = engine.query_entities(['PlayerCharacter'])

    # Prepare character data
    characters = []
    for entity in all_entities:
        components = engine.get_entity_components(entity.id)
        identity = components.get('Identity', {})
        position = components.get('Position', {})
        player_char = components.get('PlayerCharacter', {})

        characters.append({
            'entity': entity,
            'description': identity.get('description', 'No description'),
            'has_position': True,  # Always true due to query filter
            'region': position.get('region', 'Unknown'),
            'needs_ai_intro': player_char.get('needs_ai_intro', False)
        })

    return render_template(
        'character_select.html',
        characters=characters
    )


@client_bp.route('/character/create', methods=['GET', 'POST'])
@require_world
def character_create():
    """Redirect to character builder (legacy route for compatibility)."""
    return redirect(url_for('client.character_builder'))


@client_bp.route('/character/build', methods=['GET', 'POST'])
@require_world
def character_builder():
    """Full character builder with all fantasy components."""
    engine = get_engine()
    form_builder = FormBuilder(engine)

    if request.method == 'POST':
        # Get all form data
        name = request.form.get('name')
        description = request.form.get('description', '')

        # Handle starting scenario selection
        scenario_type = request.form.get('scenario_type', 'default')
        region = 'The Realm'  # Default

        if scenario_type == 'join_players':
            # Join existing players at their location
            target_player = request.form.get('join_player_id')
            if target_player:
                target_entity = engine.get_entity(target_player)
                if target_entity:
                    target_pos = engine.get_component(target_player, 'Position')
                    if target_pos:
                        region = target_pos.data.get('region', 'The Realm')
        elif scenario_type == 'prewritten':
            # Use pre-written starting scenario
            scenario_key = request.form.get('prewritten_scenario', 'default')
            scenario_regions = {
                'tavern': 'The Golden Tankard',
                'city_gates': 'Gates of Waterdeep',
                'forest': 'Whispering Woods',
                'dungeon_entrance': 'The Shadowed Crypt Entrance',
                'roadside': 'The King\'s Road',
                'default': 'The Realm'
            }
            region = scenario_regions.get(scenario_key, 'The Realm')
        elif scenario_type == 'ai_generated':
            # AI will generate a custom starting scenario during character creation
            region = 'The Realm'  # Placeholder - AI will describe the real location
        # else: scenario_type == 'default', region already set to 'The Realm'

        # Fantasy-specific fields (only present if generic_fantasy module loaded)
        race = request.form.get('race')
        char_class = request.form.get('class')
        alignment = request.form.get('alignment')

        # Attributes (only present if generic_fantasy module loaded)
        strength = request.form.get('strength', type=int)
        dexterity = request.form.get('dexterity', type=int)
        constitution = request.form.get('constitution', type=int)
        intelligence = request.form.get('intelligence', type=int)
        wisdom = request.form.get('wisdom', type=int)
        charisma = request.form.get('charisma', type=int)

        if not name:
            flash('Character name is required', 'error')
            return redirect(url_for('client.character_builder'))

        # Validate attributes only if they were provided (module loaded)
        attrs = [strength, dexterity, constitution, intelligence, wisdom, charisma]
        has_attributes = any(attr is not None for attr in attrs)
        if has_attributes and any(attr is None or attr < 1 or attr > 20 for attr in attrs):
            flash('All attributes must be between 1 and 20', 'error')
            return redirect(url_for('client.character_builder'))

        # Create character entity
        result = engine.create_entity(name)
        if not result.success:
            flash(f'Error creating character: {result.error}', 'error')
            return redirect(url_for('client.character_builder'))

        entity_id = result.data['id']

        try:
            # Add Identity component
            engine.add_component(entity_id, 'Identity', {
                'description': description or f"A {race} {char_class}"
            })

            # Add Position component
            engine.add_component(entity_id, 'Position', {
                'x': 0, 'y': 0, 'z': 0,
                'region': region
            })

            # Add PlayerCharacter component (marker - no data needed)
            engine.add_component(entity_id, 'PlayerCharacter', {})

            # Add Attributes component (only if generic_fantasy module loaded)
            if has_attributes:
                engine.add_component(entity_id, 'Attributes', {
                    'strength': strength,
                    'dexterity': dexterity,
                    'constitution': constitution,
                    'intelligence': intelligence,
                    'wisdom': wisdom,
                    'charisma': charisma
                })

            # Add CharacterDetails if provided (triggers auto-add of Magic/Skills via events)
            if race or char_class or alignment:
                char_details = {
                    'level': 1  # Default starting level
                }
                if race:
                    char_details['race'] = race
                if char_class:
                    char_details['character_class'] = char_class
                if alignment:
                    char_details['alignment'] = alignment

                engine.add_component(entity_id, 'CharacterDetails', char_details)

            # Generate AI intro if requested (one-time event during creation)
            if scenario_type == 'ai_generated':
                try:
                    from datetime import datetime
                    import json
                    from src.modules.ai_dm.llm_client import get_llm_client, LLMError
                    from src.modules.ai_dm.prompts import build_full_prompt
                    from src.modules.ai_dm.response_parser import parse_dm_response
                    from src.modules.ai_dm.tools import get_tool_definitions, execute_tool
                    from src.core.config import get_config

                    # Create Conversation component
                    engine.add_component(entity_id, 'Conversation', {
                        'message_ids': []
                    })

                    # Build context and generate intro
                    ai_context = engine.generate_ai_context(entity_id)
                    full_system_prompt = build_full_prompt(ai_context)

                    intro_prompt = (
                        "This is the very beginning of the adventure. "
                        "Create an engaging opening scene that introduces the character to their starting location. "
                        "Set the mood, describe the environment, and present an initial situation that draws them in. "
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
                    tool_uses = []  # Collect all tool uses
                    current_tool = None
                    tool_input_json = ""

                    logger.info("=== Starting AI intro generation ===")
                    logger.info(f"Prompt: {intro_prompt}")
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
                    logger.info(f"Intro text: {intro_text}")
                    logger.info(f"Intro actions: {intro_actions}")

                    # Create intro message entity
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
                        engine.update_component(entity_id, 'Conversation', {
                            'message_ids': [dm_msg_id]
                        })

                        logger.info(f"Generated AI intro for character {entity_id}")

                except Exception as e:
                    logger.error(f"Failed to generate AI intro: {e}")
                    # Non-fatal - character still created, just no intro

            flash(f'Character "{name}" created successfully!', 'success')
            return redirect(url_for('client.character_sheet', entity_id=entity_id))

        except Exception as e:
            # Clean up on error
            engine.delete_entity(entity_id)
            flash(f'Error creating character: {str(e)}', 'error')
            return redirect(url_for('client.character_builder'))

    # GET request - show form
    # Get registries for dropdowns
    try:
        owner = engine.storage.get_registry_owner('races')
        if owner:
            races_registry = engine.create_registry('races', owner)
            races = races_registry.get_all()
        else:
            races = []
    except Exception as e:
        logger.warning(f"Failed to load races registry: {e}")
        races = []

    try:
        owner = engine.storage.get_registry_owner('classes')
        if owner:
            classes_registry = engine.create_registry('classes', owner)
            classes = classes_registry.get_all()
        else:
            classes = []
    except Exception as e:
        logger.warning(f"Failed to load classes registry: {e}")
        classes = []

    try:
        owner = engine.storage.get_registry_owner('alignments')
        if owner:
            alignments_registry = engine.create_registry('alignments', owner)
            alignments = alignments_registry.get_all()
        else:
            alignments = []
    except Exception as e:
        logger.warning(f"Failed to load alignments registry: {e}")
        alignments = []

    # Get existing players for "join players" option
    existing_players = []
    player_entities = engine.query_entities(['PlayerCharacter', 'Position'])
    for player in player_entities:
        pos = engine.get_component(player.id, 'Position')
        if pos:
            existing_players.append({
                'id': player.id,
                'name': player.name,
                'region': pos.data.get('region', 'Unknown')
            })

    # Pre-written starting scenarios
    prewritten_scenarios = [
        {
            'key': 'tavern',
            'name': 'The Golden Tankard',
            'description': 'A bustling tavern filled with adventurers and travelers'
        },
        {
            'key': 'city_gates',
            'name': 'Gates of Waterdeep',
            'description': 'The grand entrance to a magnificent walled city'
        },
        {
            'key': 'forest',
            'name': 'Whispering Woods',
            'description': 'A mysterious forest at the edge of civilization'
        },
        {
            'key': 'dungeon_entrance',
            'name': 'The Shadowed Crypt',
            'description': 'Ancient stone steps leading down into darkness'
        },
        {
            'key': 'roadside',
            'name': 'The King\'s Road',
            'description': 'A well-traveled road between major settlements'
        }
    ]

    return render_template(
        'character_builder.html',
        races=races,
        classes=classes,
        alignments=alignments,
        existing_players=existing_players,
        prewritten_scenarios=prewritten_scenarios,
        form_builder=form_builder
    )


@client_bp.route('/character/<entity_id>')
@require_world
def character_sheet(entity_id: str):
    """View character sheet."""
    engine = get_engine()
    entity = engine.get_entity(entity_id)

    if not entity:
        flash('Character not found', 'error')
        return redirect(url_for('client.index'))

    # Get all components
    components = engine.get_entity_components(entity_id)

    # Get identity and position
    identity = components.get('Identity', {})
    position = components.get('Position', {})

    # Get world position if available
    from src.modules.core_components.systems import PositionSystem
    position_system = PositionSystem(engine)
    world_pos = position_system.get_world_position(entity_id)

    # Get relationships
    relationships = engine.get_relationships(entity_id)

    # Organize relationships (items, locations, etc.)
    located_at = None
    inventory = []
    other_relationships = []

    for rel in relationships:
        if rel.relationship_type == 'located_at' and rel.from_entity == entity_id:
            location_entity = engine.get_entity(rel.to_entity)
            if location_entity:
                located_at = location_entity
        elif rel.relationship_type == 'contains' and rel.from_entity == entity_id:
            item_entity = engine.get_entity(rel.to_entity)
            if item_entity:
                inventory.append(item_entity)
        else:
            other_entity = engine.get_entity(
                rel.to_entity if rel.from_entity == entity_id else rel.from_entity
            )
            if other_entity:
                other_relationships.append({
                    'type': rel.relationship_type,
                    'entity': other_entity,
                    'direction': 'to' if rel.from_entity == entity_id else 'from'
                })

    # Get entities in the same region
    if position:
        region = position.get('region')
        if region:
            nearby_entity_ids = position_system.get_entities_in_region(region)
            # Filter out the character itself and convert to Entity objects
            nearby_entities = []
            for e_id in nearby_entity_ids:
                if e_id != entity_id:
                    nearby_entity = engine.get_entity(e_id)
                    if nearby_entity and nearby_entity.is_active():
                        nearby_entities.append(nearby_entity)
        else:
            nearby_entities = []
    else:
        nearby_entities = []

    # Create FormBuilder for component display
    form_builder = FormBuilder(engine)

    return render_template(
        'character_sheet.html',
        entity=entity,
        identity=identity,
        position=position,
        world_pos=world_pos,
        components=components,
        located_at=located_at,
        inventory=inventory,
        nearby_entities=nearby_entities,
        other_relationships=other_relationships,
        form_builder=form_builder
    )

@client_bp.route('/api/entities/<entity_id>/use_item', methods=['POST'])
def use_item(entity_id):
    """Use a consumable item."""
    from flask import request, jsonify, session, current_app

    world_name = session.get('world_name')
    if not world_name:
        return jsonify({'success': False, 'error': 'No world selected'}), 400

    engine = current_app.engine_instances.get(world_name)
    if not engine:
        return jsonify({'success': False, 'error': 'World engine not found'}), 404

    data = request.get_json()
    item_id = data.get('item_id')

    if not item_id:
        return jsonify({'success': False, 'error': 'item_id required'}), 400

    # Get the item
    item = engine.get_entity(item_id)
    if not item:
        return jsonify({'success': False, 'error': 'Item not found'}), 404

    # Check if item is consumable
    consumable = engine.get_component(item_id, 'Consumable')
    if not consumable:
        return jsonify({'success': False, 'error': 'Item is not consumable'}), 400

    # Check if item has charges
    charges = consumable.data.get('charges', 0)
    if charges <= 0:
        return jsonify({'success': False, 'error': 'Item has no charges remaining'}), 400

    try:
        # Decrease charges
        new_charges = charges - 1
        engine.update_component(item_id, 'Consumable', {
            **consumable.data,
            'charges': new_charges
        })

        # If charges reach 0, delete the item (unless rechargeable)
        if new_charges == 0 and not consumable.data.get('rechargeable', False):
            engine.delete_entity(item_id)
            message = f"Used {item.name}. Item consumed (no charges remaining)."
        else:
            message = f"Used {item.name}. {new_charges} charges remaining."

        # Emit event
        from src.core.event_bus import Event
        engine.event_bus.publish(Event.create(
            event_type='item.used',
            entity_id=entity_id,
            actor_id=entity_id,
            data={
                'item_id': item_id,
                'item_name': item.name,
                'effect': consumable.data.get('effect_description', ''),
                'charges_remaining': new_charges
            }
        ))

        return jsonify({'success': True, 'message': message, 'charges_remaining': new_charges})

    except Exception as e:
        logger.error(f"Error using item: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
