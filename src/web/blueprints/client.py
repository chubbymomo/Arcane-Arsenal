"""
Client Blueprint - Player interface for character management.

Provides character selection, creation, and viewing for players.
Eventually will include action interface and gameplay features.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
import json as json_module
from functools import wraps

from src.core.state_engine import StateEngine
from src.web.form_builder import FormBuilder

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
    """Get StateEngine instance for current world from session."""
    world_path = session.get('world_path')
    return StateEngine(world_path)


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
    """Character creation form."""
    engine = get_engine()

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        region = request.form.get('region', 'The Realm')

        if not name or not description:
            flash('Character name and description are required', 'error')
            return redirect(url_for('client.character_create'))

        # Create character entity
        result = engine.create_entity(name)

        if not result.success:
            flash(f'Error creating character: {result.error}', 'error')
            return redirect(url_for('client.character_create'))

        entity_id = result.data['id']

        # Add Identity component
        identity_result = engine.add_component(entity_id, 'Identity', {
            'description': description
        })

        if not identity_result.success:
            flash(f'Error adding identity: {identity_result.error}', 'error')
            engine.delete_entity(entity_id)  # Clean up
            return redirect(url_for('client.character_create'))

        # Add Position component (default to 0, 0, 0 in specified region)
        position_result = engine.add_component(entity_id, 'Position', {
            'x': 0,
            'y': 0,
            'z': 0,
            'region': region
        })

        if not position_result.success:
            flash(f'Error adding position: {position_result.error}', 'error')
            engine.delete_entity(entity_id)  # Clean up
            return redirect(url_for('client.character_create'))

        # Add PlayerCharacter component (marks this as a player character)
        player_result = engine.add_component(entity_id, 'PlayerCharacter', {})

        if not player_result.success:
            flash(f'Error marking as player character: {player_result.error}', 'error')
            engine.delete_entity(entity_id)  # Clean up
            return redirect(url_for('client.character_create'))

        flash(f'Character "{name}" created successfully!', 'success')
        return redirect(url_for('client.character_sheet', entity_id=entity_id))

    # GET request - show form
    # Get available regions for dropdown
    positioned_entities = engine.query_entities(['Position'])
    regions = set(['The Realm'])  # Default starting region

    for entity in positioned_entities:
        pos = engine.get_component(entity.id, 'Position')
        if pos and pos.data.get('region'):
            region = pos.data['region']
            if not region.startswith('entity_'):
                regions.add(region)

    return render_template(
        'character_create.html',
        regions=sorted(list(regions))
    )


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
        region = request.form.get('region', 'The Realm')

        # Fantasy-specific fields
        race = request.form.get('race')
        char_class = request.form.get('class')
        alignment = request.form.get('alignment')

        # Attributes
        strength = request.form.get('strength', type=int)
        dexterity = request.form.get('dexterity', type=int)
        constitution = request.form.get('constitution', type=int)
        intelligence = request.form.get('intelligence', type=int)
        wisdom = request.form.get('wisdom', type=int)
        charisma = request.form.get('charisma', type=int)

        if not name:
            flash('Character name is required', 'error')
            return redirect(url_for('client.character_builder'))

        # Validate attributes
        attrs = [strength, dexterity, constitution, intelligence, wisdom, charisma]
        if any(attr is None or attr < 1 or attr > 20 for attr in attrs):
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

            # Add PlayerCharacter component
            engine.add_component(entity_id, 'PlayerCharacter', {})

            # Add Attributes component
            engine.add_component(entity_id, 'Attributes', {
                'strength': strength,
                'dexterity': dexterity,
                'constitution': constitution,
                'intelligence': intelligence,
                'wisdom': wisdom,
                'charisma': charisma
            })

            # Add CharacterDetails if provided
            if race or char_class or alignment:
                char_details = {}
                if race:
                    char_details['race'] = race
                if char_class:
                    char_details['class'] = char_class
                if alignment:
                    char_details['alignment'] = alignment

                # Note: CharacterDetails component not implemented yet,
                # so this will fail gracefully
                # engine.add_component(entity_id, 'CharacterDetails', char_details)

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
        races_registry = engine.create_registry('races', 'generic_fantasy')
        races = races_registry.get_all()
    except:
        races = []

    try:
        classes_registry = engine.create_registry('classes', 'generic_fantasy')
        classes = classes_registry.get_all()
    except:
        classes = []

    try:
        alignments_registry = engine.create_registry('alignments', 'generic_fantasy')
        alignments = alignments_registry.get_all()
    except:
        alignments = []

    # Get available regions
    positioned_entities = engine.query_entities(['Position'])
    regions = set(['The Realm'])

    for entity in positioned_entities:
        pos = engine.get_component(entity.id, 'Position')
        if pos and pos.data.get('region'):
            region_name = pos.data['region']
            if not region_name.startswith('entity_'):
                regions.add(region_name)

    return render_template(
        'character_builder.html',
        races=races,
        classes=classes,
        alignments=alignments,
        regions=sorted(list(regions)),
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
            nearby_entities = position_system.get_entities_in_region(region)
            # Filter out the character itself
            nearby_entities = [e for e in nearby_entities if e.id != entity_id]
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
