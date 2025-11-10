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
from src.core.event_bus import Event
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
        # Collect ALL form data generically - web layer doesn't know about module fields
        form_data = dict(request.form)

        # Extract only core fields needed by the engine itself
        name = form_data.get('name')
        description = form_data.get('description', '')

        if not name:
            flash('Character name is required', 'error')
            return redirect(url_for('client.character_builder'))

        # Handle starting scenario selection (core concern for Position component)
        scenario_type = form_data.get('scenario_type', 'default')
        region = 'The Realm'  # Default

        if scenario_type == 'join_players':
            target_player = form_data.get('join_player_id')
            if target_player:
                target_entity = engine.get_entity(target_player)
                if target_entity:
                    target_pos = engine.get_component(target_player, 'Position')
                    if target_pos:
                        region = target_pos.data.get('region', 'The Realm')
        elif scenario_type == 'prewritten':
            scenario_key = form_data.get('prewritten_scenario', 'default')
            scenario_regions = {
                'tavern': 'The Golden Tankard',
                'city_gates': 'Gates of Waterdeep',
                'forest': 'Whispering Woods',
                'dungeon_entrance': 'The Shadowed Crypt Entrance',
                'roadside': 'The King\'s Road',
                'default': 'The Realm'
            }
            region = scenario_regions.get(scenario_key, 'The Realm')

        # Create character entity
        result = engine.create_entity(name)
        if not result.success:
            flash(f'Error creating character: {result.error}', 'error')
            return redirect(url_for('client.character_builder'))

        entity_id = result.data['id']

        try:
            # Add core components
            engine.add_component(entity_id, 'Identity', {
                'description': description or "A new character"
            })

            engine.add_component(entity_id, 'Position', {
                'x': 0, 'y': 0, 'z': 0,
                'region': region
            })

            engine.add_component(entity_id, 'PlayerCharacter', {})

            # Publish character creation event with ALL form data
            # Modules subscribe to this event and parse what they need
            # Web layer doesn't know what fields modules care about
            engine.event_bus.publish(Event.create(
                event_type='character.form_submitted',
                entity_id=entity_id,
                data=form_data  # Pass ALL form data to modules
            ))

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
        owner = engine.get_registry_owner('races')
        if owner:
            races_registry = engine.create_registry('races', owner)
            races = races_registry.get_all()
        else:
            races = []
    except Exception as e:
        logger.warning(f"Failed to load races registry: {e}")
        races = []

    try:
        owner = engine.get_registry_owner('classes')
        if owner:
            classes_registry = engine.create_registry('classes', owner)
            classes = classes_registry.get_all()
        else:
            classes = []
    except Exception as e:
        logger.warning(f"Failed to load classes registry: {e}")
        classes = []

    try:
        owner = engine.get_registry_owner('alignments')
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
    # Note: PositionSystem is a core utility, so direct import is acceptable
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

# Note: Item usage endpoint moved to items module API
# See src/modules/items/api.py - POST /api/item/use
