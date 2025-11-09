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

        characters.append({
            'entity': entity,
            'description': identity.get('description', 'No description'),
            'has_position': True,  # Always true due to query filter
            'region': position.get('region', 'Unknown')
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
        needs_ai_intro = False

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
            # AI will generate a custom starting scenario
            region = 'The Realm'  # Placeholder - AI will describe the real location
            needs_ai_intro = True
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

            # Add PlayerCharacter component with AI intro flag
            engine.add_component(entity_id, 'PlayerCharacter', {
                'needs_ai_intro': needs_ai_intro
            })

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
