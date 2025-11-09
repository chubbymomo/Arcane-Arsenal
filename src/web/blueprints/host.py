"""
Host Blueprint - DM/Host interface for state management.

Provides full CRUD operations for entities, components, and relationships.
Intended for game masters to manage world state.
"""

from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, current_app, session
import json as json_module
from functools import wraps

from src.core.state_engine import StateEngine
from src.web.form_builder import FormBuilder

# Create blueprint
host_bp = Blueprint('host', __name__, url_prefix='/host', template_folder='../templates/host')


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

@host_bp.route('/')
@require_world
def index():
    """Dashboard overview."""
    engine = get_engine()

    # Get stats
    all_entities = engine.list_entities()
    entity_count = len(all_entities)
    player_count = len(engine.query_entities(['PlayerCharacter']))
    component_types = engine.storage.get_component_types()
    component_type_count = len(component_types)

    # Get recent events
    events = engine.get_events(limit=10)
    event_data = []
    for event in events:
        entity_name = None
        if event.entity_id:
            entity = engine.get_entity(event.entity_id)
            if entity:
                entity_name = entity.name
        event_data.append({
            'event': event,
            'event_type': event.event_type,
            'entity_name': entity_name
        })

    # Get loaded modules info
    from src.core.module_loader import ModuleLoader
    loader = ModuleLoader()
    loader.world_path = engine.world_path
    loaded_modules = loader.load_modules('config')
    module_info = []
    for mod in loaded_modules:
        module_info.append({
            'name': mod.name,
            'display_name': mod.display_name,
            'version': mod.version,
            'description': mod.description,
            'is_core': mod.is_core
        })

    return render_template(
        'dashboard.html',
        entity_count=entity_count,
        player_count=player_count,
        component_type_count=component_type_count,
        event_count=len(events),
        recent_events=event_data[:5],  # Show only 5 most recent
        modules=module_info
    )

@host_bp.route('/entities')
@require_world
def entities():
    """List all entities."""
    engine = get_engine()
    entities = engine.list_entities()

    # Prepare entity data with component list
    entity_data = []
    for entity in entities:
        components = engine.get_entity_components(entity.id)

        entity_data.append({
            'entity': entity,
            'components': list(components.keys())
        })

    # Get registered types for forms
    component_types = engine.storage.get_component_types()
    relationship_types = engine.storage.get_relationship_types()

    return render_template(
        'entities.html',
        entities=entity_data,
        component_types=component_types,
        relationship_types=relationship_types
    )


@host_bp.route('/entity/<entity_id>')
@require_world
def entity_detail(entity_id: str):
    """Show entity details with all components and relationships."""
    engine = get_engine()
    entity = engine.get_entity(entity_id)

    if not entity:
        return "Entity not found", 404

    # Get components
    components = engine.get_entity_components(entity_id)

    # Get relationships
    relationships = engine.get_relationships(entity_id)

    # Organize relationships
    outgoing = []
    incoming = []
    for rel in relationships:
        if rel.from_entity == entity_id:
            to_entity = engine.get_entity(rel.to_entity)
            outgoing.append({
                'rel': rel,
                'other': to_entity
            })
        else:
            from_entity = engine.get_entity(rel.from_entity)
            incoming.append({
                'rel': rel,
                'other': from_entity
            })

    # Get recent events for this entity
    events = engine.get_events(entity_id=entity_id, limit=10)

    # Get registered types for forms
    component_types = engine.storage.get_component_types()
    relationship_types = engine.storage.get_relationship_types()
    all_entities = engine.list_entities()

    # Create FormBuilder instance
    form_builder = FormBuilder(engine)

    return render_template(
        'entity.html',
        entity=entity,
        components=components,
        outgoing=outgoing,
        incoming=incoming,
        events=events,
        component_types=component_types,
        relationship_types=relationship_types,
        all_entities=all_entities,
        engine=engine,
        form_builder=form_builder
    )


@host_bp.route('/events')
@require_world
def events():
    """Show recent events."""
    engine = get_engine()
    limit = request.args.get('limit', 50, type=int)
    event_type = request.args.get('type', None)

    events = engine.get_events(event_type=event_type, limit=limit)

    # Get entity names for events
    event_data = []
    for event in events:
        entity_name = None
        if event.entity_id:
            entity = engine.get_entity(event.entity_id)
            if entity:
                entity_name = entity.name

        event_data.append({
            'event': event,
            'entity_name': entity_name
        })

    # Get available event types for filter
    event_types = list(set(e.event_type for e in events))

    return render_template(
        'events.html',
        events=event_data,
        event_types=event_types,
        current_type=event_type,
        limit=limit
    )


# ========== POST Endpoints for State Modification ==========

@host_bp.route('/entity/create', methods=['POST'])
@require_world
def create_entity():
    """Create a new entity."""
    engine = get_engine()
    name = request.form.get('name')

    if not name:
        flash('Entity name is required', 'error')
        # Redirect back to referring page or dashboard
        return redirect(request.referrer or url_for('host.index'))

    result = engine.create_entity(name)

    if result.success:
        flash(f'Entity "{name}" created successfully', 'success')
        return redirect(url_for('host.entity_detail', entity_id=result.data['id']))
    else:
        flash(f'Error creating entity: {result.error}', 'error')
        return redirect(request.referrer or url_for('host.index'))


@host_bp.route('/entity/<entity_id>/update', methods=['POST'])
@require_world
def update_entity(entity_id: str):
    """Update an entity's name."""
    engine = get_engine()
    name = request.form.get('name')

    if not name:
        flash('Entity name is required', 'error')
        return redirect(url_for('host.entity_detail', entity_id=entity_id))

    result = engine.update_entity(entity_id, name)

    if result.success:
        flash(f'Entity updated to "{name}"', 'success')
    else:
        flash(f'Error updating entity: {result.error}', 'error')

    return redirect(url_for('host.entity_detail', entity_id=entity_id))


@host_bp.route('/entity/<entity_id>/delete', methods=['POST'])
@require_world
def delete_entity(entity_id: str):
    """Delete an entity."""
    engine = get_engine()
    entity = engine.get_entity(entity_id)

    if not entity:
        flash('Entity not found', 'error')
        return redirect(url_for('host.index'))

    result = engine.delete_entity(entity_id)

    if result.success:
        flash(f'Entity "{entity.name}" deleted successfully', 'success')
        return redirect(url_for('host.entities'))
    else:
        flash(f'Error deleting entity: {result.error}', 'error')
        return redirect(url_for('host.entity_detail', entity_id=entity_id))


@host_bp.route('/entity/<entity_id>/component/add', methods=['POST'])
@require_world
def add_component(entity_id: str):
    """Add a component to an entity."""
    engine = get_engine()
    component_type = request.form.get('component_type')
    component_data = request.form.get('component_data')

    if not component_type or not component_data:
        flash('Component type and data are required', 'error')
        return redirect(url_for('host.entity_detail', entity_id=entity_id))

    try:
        data = json_module.loads(component_data)
    except json_module.JSONDecodeError as e:
        flash(f'Invalid JSON: {e}', 'error')
        return redirect(url_for('host.entity_detail', entity_id=entity_id))

    result = engine.add_component(entity_id, component_type, data)

    if result.success:
        flash(f'Component "{component_type}" added successfully', 'success')
    else:
        flash(f'Error adding component: {result.error}', 'error')

    return redirect(url_for('host.entity_detail', entity_id=entity_id))


@host_bp.route('/entity/<entity_id>/component/<component_type>/update', methods=['POST'])
@require_world
def update_component(entity_id: str, component_type: str):
    """Update a component."""
    engine = get_engine()
    component_data = request.form.get('component_data')

    if not component_data:
        flash('Component data is required', 'error')
        return redirect(url_for('host.entity_detail', entity_id=entity_id))

    try:
        data = json_module.loads(component_data)
    except json_module.JSONDecodeError as e:
        flash(f'Invalid JSON: {e}', 'error')
        return redirect(url_for('host.entity_detail', entity_id=entity_id))

    result = engine.update_component(entity_id, component_type, data)

    if result.success:
        flash(f'Component "{component_type}" updated successfully', 'success')
    else:
        flash(f'Error updating component: {result.error}', 'error')

    return redirect(url_for('host.entity_detail', entity_id=entity_id))


@host_bp.route('/entity/<entity_id>/component/<component_type>/delete', methods=['POST'])
@require_world
def delete_component(entity_id: str, component_type: str):
    """Delete a component."""
    engine = get_engine()
    result = engine.remove_component(entity_id, component_type)

    if result.success:
        flash(f'Component "{component_type}" removed successfully', 'success')
    else:
        flash(f'Error removing component: {result.error}', 'error')

    return redirect(url_for('host.entity_detail', entity_id=entity_id))


@host_bp.route('/relationship/create', methods=['POST'])
@require_world
def create_relationship():
    """Create a relationship between entities."""
    engine = get_engine()
    from_entity = request.form.get('from_entity')
    to_entity = request.form.get('to_entity')
    relationship_type = request.form.get('relationship_type')
    metadata = request.form.get('metadata', '{}')

    if not all([from_entity, to_entity, relationship_type]):
        flash('From entity, to entity, and relationship type are required', 'error')
        return redirect(request.referrer or url_for('host.index'))

    try:
        metadata_dict = json_module.loads(metadata) if metadata.strip() else {}
    except json_module.JSONDecodeError as e:
        flash(f'Invalid metadata JSON: {e}', 'error')
        return redirect(url_for('host.entity_detail', entity_id=from_entity))

    result = engine.create_relationship(from_entity, to_entity, relationship_type, metadata_dict)

    if result.success:
        flash('Relationship created successfully', 'success')
    else:
        flash(f'Error creating relationship: {result.error}', 'error')

    return redirect(url_for('host.entity_detail', entity_id=from_entity))


@host_bp.route('/relationship/<relationship_id>/delete', methods=['POST'])
@require_world
def delete_relationship(relationship_id: str):
    """Delete a relationship."""
    engine = get_engine()

    # Get relationship to find source entity for redirect
    relationship = engine.storage.get_relationship(relationship_id)
    if not relationship:
        flash('Relationship not found', 'error')
        return redirect(url_for('host.index'))

    from_entity_id = relationship.from_entity
    result = engine.delete_relationship(relationship_id)

    if result.success:
        flash('Relationship deleted successfully', 'success')
    else:
        flash(f'Error deleting relationship: {result.error}', 'error')

    return redirect(url_for('host.entity_detail', entity_id=from_entity_id))
