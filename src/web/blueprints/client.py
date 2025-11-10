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
from src.core.module_loader import ModuleLoader
from src.web.form_builder import FormBuilder

logger = logging.getLogger(__name__)

# Create blueprint
client_bp = Blueprint('client', __name__, url_prefix='/client', template_folder='../templates/client')

# Cache for initialized modules per world
_world_modules_cache = {}


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


def get_generic_fantasy_module():
    """
    Get the generic_fantasy module for the current world (if loaded).

    Returns:
        GenericFantasyModule instance or None if not loaded
    """
    world_name = session.get('world_name')
    if not world_name:
        return None

    # Check if modules are already loaded for this world
    if world_name not in _world_modules_cache:
        # Load and initialize modules
        world_path = session.get('world_path')
        engine = get_engine()

        logger.info(f"Loading modules for world: {world_name}")
        loader = ModuleLoader(world_path)
        modules = loader.load_modules(strategy='config')

        # Initialize each module with the cached engine
        for module in modules:
            try:
                module.initialize(engine)
            except Exception as e:
                logger.warning(f"Failed to initialize module {module.name}: {e}")

        # Cache the loaded modules for this world
        _world_modules_cache[world_name] = modules
        logger.info(f"✓ Modules loaded and cached for world: {world_name}")

    # Get modules from cache
    modules = _world_modules_cache[world_name]

    # Find generic_fantasy module
    for module in modules:
        if module.name == 'generic_fantasy':
            return module

    return None


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
            # Add core components (these are core_components module, always available)
            engine.add_component(entity_id, 'Identity', {
                'description': description or f"A {race} {char_class}" if (race or char_class) else "A new character"
            })

            engine.add_component(entity_id, 'Position', {
                'x': 0, 'y': 0, 'z': 0,
                'region': region
            })

            engine.add_component(entity_id, 'PlayerCharacter', {})

            # Add fantasy-specific components via module (if module loaded and fields provided)
            # This delegates to the module instead of directly manipulating module components
            if has_attributes or race or char_class or alignment:
                fantasy_module = get_generic_fantasy_module()
                if fantasy_module:
                    result = fantasy_module.add_fantasy_components(
                        engine, entity_id,
                        race=race,
                        character_class=char_class,
                        alignment=alignment,
                        strength=strength,
                        dexterity=dexterity,
                        constitution=constitution,
                        intelligence=intelligence,
                        wisdom=wisdom,
                        charisma=charisma
                    )
                    if not result.success:
                        raise ValueError(result.error)
                else:
                    logger.warning("Fantasy fields provided but generic_fantasy module not loaded")

            # Generate AI intro if requested
            # Note: AI intro generation is handled by ai_dm module
            # For now, we skip auto-generation during character creation
            # Players can trigger intro generation from the character sheet
            # This simplifies the flow and moves AI logic to the ai_dm module
            if scenario_type == 'ai_generated':
                # Create empty Conversation component so AI intro can be generated later
                engine.add_component(entity_id, 'Conversation', {
                    'message_ids': []
                })
                flash('Character created! Visit your character sheet to generate an AI introduction.', 'info')

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
