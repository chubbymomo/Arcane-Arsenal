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
            # Only add named regions (not entity IDs)
            # Check if region is an entity by attempting to get it
            if not engine.get_entity(region):
                # Region is a named area, not an entity ID
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

            # Add PlayerCharacter component
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

    # Get available regions
    positioned_entities = engine.query_entities(['Position'])
    regions = set(['The Realm'])

    for entity in positioned_entities:
        pos = engine.get_component(entity.id, 'Position')
        if pos and pos.data.get('region'):
            region_name = pos.data['region']
            # Only add named regions (not entity IDs)
            # Check if region is an entity by attempting to get it
            if not engine.get_entity(region_name):
                # Region is a named area, not an entity ID
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


# ==================== Inventory Management API ====================

@client_bp.route('/api/entities/<entity_id>/equip', methods=['POST'])
@require_world
def equip_item(entity_id):
    """Equip an item on an entity."""
    from flask import request, jsonify

    logger.info(f"[EQUIP] Starting equip request for entity {entity_id}")

    engine = get_engine()
    logger.info(f"[EQUIP] Got engine instance: {engine}")

    data = request.get_json()
    item_id = data.get('item_id')
    logger.info(f"[EQUIP] Request data - entity_id: {entity_id}, item_id: {item_id}")

    if not item_id:
        logger.warning("[EQUIP] No item_id provided in request")
        return jsonify({'success': False, 'error': 'item_id required'}), 400

    # Get the equipment system from the items module
    try:
        items_module = None
        logger.info(f"[EQUIP] Searching for items module among {len(engine.modules)} modules")
        for module in engine.modules:
            logger.debug(f"[EQUIP] Checking module: {module.name}")
            if module.name == 'items':
                items_module = module
                logger.info("[EQUIP] Found items module")
                break

        if not items_module:
            logger.error("[EQUIP] Items module not loaded in engine")
            return jsonify({'success': False, 'error': 'Items module not loaded'}), 400

        equipment_system = items_module.get_equipment_system()
        logger.info(f"[EQUIP] Got equipment system: {equipment_system}")

        # Equip the item
        logger.info(f"[EQUIP] Calling equipment_system.equip_item({entity_id}, {item_id})")
        result = equipment_system.equip_item(entity_id, item_id)
        logger.info(f"[EQUIP] Result: success={result.is_ok()}, error={result.error if not result.is_ok() else 'None'}")

        if result.is_ok():
            logger.info("[EQUIP] Successfully equipped item")
            return jsonify({'success': True, 'message': 'Item equipped successfully'})
        else:
            logger.warning(f"[EQUIP] Failed to equip item: {result.error}")
            return jsonify({'success': False, 'error': result.error}), 400

    except Exception as e:
        logger.error(f"[EQUIP] Exception occurred: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@client_bp.route('/api/entities/<entity_id>/unequip', methods=['POST'])
@require_world
def unequip_item(entity_id):
    """Unequip an item from an entity."""
    from flask import request, jsonify

    logger.info(f"[UNEQUIP] Starting unequip request for entity {entity_id}")

    engine = get_engine()
    logger.info(f"[UNEQUIP] Got engine instance: {engine}")

    data = request.get_json()
    item_id = data.get('item_id')
    logger.info(f"[UNEQUIP] Request data - entity_id: {entity_id}, item_id: {item_id}")

    if not item_id:
        logger.warning("[UNEQUIP] No item_id provided in request")
        return jsonify({'success': False, 'error': 'item_id required'}), 400

    # Get the equipment system from the items module
    try:
        items_module = None
        logger.info(f"[UNEQUIP] Searching for items module among {len(engine.modules)} modules")
        for module in engine.modules:
            if module.name == 'items':
                items_module = module
                logger.info("[UNEQUIP] Found items module")
                break

        if not items_module:
            logger.error("[UNEQUIP] Items module not loaded in engine")
            return jsonify({'success': False, 'error': 'Items module not loaded'}), 400

        equipment_system = items_module.get_equipment_system()
        logger.info(f"[UNEQUIP] Got equipment system: {equipment_system}")

        # Unequip the item
        logger.info(f"[UNEQUIP] Calling equipment_system.unequip_item({entity_id}, {item_id})")
        result = equipment_system.unequip_item(entity_id, item_id)
        logger.info(f"[UNEQUIP] Result: success={result.is_ok()}, error={result.error if not result.is_ok() else 'None'}")

        if result.is_ok():
            logger.info("[UNEQUIP] Successfully unequipped item")
            return jsonify({'success': True, 'message': 'Item unequipped successfully'})
        else:
            logger.warning(f"[UNEQUIP] Failed to unequip item: {result.error}")
            return jsonify({'success': False, 'error': result.error}), 400

    except Exception as e:
        logger.error(f"[UNEQUIP] Exception occurred: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


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
