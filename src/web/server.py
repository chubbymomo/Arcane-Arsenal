"""
Web interface for Arcane Arsenal.

Flask app to browse and edit world state in a web browser.
Provides full CRUD operations for entities, components, and relationships.
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import sys
import os
import json as json_module
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.state_engine import StateEngine


def create_app(world_path: str) -> Flask:
    """
    Create Flask app for viewing a world.

    Args:
        world_path: Path to world directory

    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    app.config['WORLD_PATH'] = world_path
    app.config['SECRET_KEY'] = os.urandom(24)  # For flash messages

    def get_engine() -> StateEngine:
        """Get StateEngine instance for current world."""
        return StateEngine(app.config['WORLD_PATH'])

    @app.route('/')
    def index():
        """List all entities."""
        engine = get_engine()
        entities = engine.list_entities()

        # Group entities by type based on tags
        entity_data = []
        for entity in entities:
            components = engine.get_entity_components(entity.id)
            tags = []
            if 'Identity' in components:
                tags = components['Identity'].get('tags', [])

            entity_data.append({
                'entity': entity,
                'components': list(components.keys()),
                'tags': tags
            })

        # Get registered types for forms
        component_types = engine.storage.get_component_types()
        relationship_types = engine.storage.get_relationship_types()

        return render_template(
            'index.html',
            entities=entity_data,
            component_types=component_types,
            relationship_types=relationship_types
        )

    @app.route('/entity/<entity_id>')
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

        return render_template(
            'entity.html',
            entity=entity,
            components=components,
            outgoing=outgoing,
            incoming=incoming,
            events=events,
            component_types=component_types,
            relationship_types=relationship_types,
            all_entities=all_entities
        )

    @app.route('/events')
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

    @app.route('/entity/create', methods=['POST'])
    def create_entity():
        """Create a new entity."""
        engine = get_engine()
        name = request.form.get('name')

        if not name:
            flash('Entity name is required', 'error')
            return redirect(url_for('index'))

        result = engine.create_entity(name)

        if result.success:
            flash(f'Entity "{name}" created successfully', 'success')
            return redirect(url_for('entity_detail', entity_id=result.data['id']))
        else:
            flash(f'Error creating entity: {result.error}', 'error')
            return redirect(url_for('index'))

    @app.route('/entity/<entity_id>/delete', methods=['POST'])
    def delete_entity(entity_id: str):
        """Delete an entity."""
        engine = get_engine()
        entity = engine.get_entity(entity_id)

        if not entity:
            flash('Entity not found', 'error')
            return redirect(url_for('index'))

        result = engine.delete_entity(entity_id)

        if result.success:
            flash(f'Entity "{entity.name}" deleted successfully', 'success')
            return redirect(url_for('index'))
        else:
            flash(f'Error deleting entity: {result.error}', 'error')
            return redirect(url_for('entity_detail', entity_id=entity_id))

    @app.route('/entity/<entity_id>/component/add', methods=['POST'])
    def add_component(entity_id: str):
        """Add a component to an entity."""
        engine = get_engine()
        component_type = request.form.get('component_type')
        component_data = request.form.get('component_data')

        if not component_type or not component_data:
            flash('Component type and data are required', 'error')
            return redirect(url_for('entity_detail', entity_id=entity_id))

        try:
            data = json_module.loads(component_data)
        except json_module.JSONDecodeError as e:
            flash(f'Invalid JSON: {e}', 'error')
            return redirect(url_for('entity_detail', entity_id=entity_id))

        result = engine.add_component(entity_id, component_type, data)

        if result.success:
            flash(f'Component "{component_type}" added successfully', 'success')
        else:
            flash(f'Error adding component: {result.error}', 'error')

        return redirect(url_for('entity_detail', entity_id=entity_id))

    @app.route('/entity/<entity_id>/component/<component_type>/update', methods=['POST'])
    def update_component(entity_id: str, component_type: str):
        """Update a component."""
        engine = get_engine()
        component_data = request.form.get('component_data')

        if not component_data:
            flash('Component data is required', 'error')
            return redirect(url_for('entity_detail', entity_id=entity_id))

        try:
            data = json_module.loads(component_data)
        except json_module.JSONDecodeError as e:
            flash(f'Invalid JSON: {e}', 'error')
            return redirect(url_for('entity_detail', entity_id=entity_id))

        result = engine.update_component(entity_id, component_type, data)

        if result.success:
            flash(f'Component "{component_type}" updated successfully', 'success')
        else:
            flash(f'Error updating component: {result.error}', 'error')

        return redirect(url_for('entity_detail', entity_id=entity_id))

    @app.route('/entity/<entity_id>/component/<component_type>/delete', methods=['POST'])
    def delete_component(entity_id: str, component_type: str):
        """Delete a component."""
        engine = get_engine()
        result = engine.remove_component(entity_id, component_type)

        if result.success:
            flash(f'Component "{component_type}" removed successfully', 'success')
        else:
            flash(f'Error removing component: {result.error}', 'error')

        return redirect(url_for('entity_detail', entity_id=entity_id))

    @app.route('/relationship/create', methods=['POST'])
    def create_relationship():
        """Create a relationship between entities."""
        engine = get_engine()
        from_entity = request.form.get('from_entity')
        to_entity = request.form.get('to_entity')
        relationship_type = request.form.get('relationship_type')
        metadata = request.form.get('metadata', '{}')

        if not all([from_entity, to_entity, relationship_type]):
            flash('From entity, to entity, and relationship type are required', 'error')
            return redirect(url_for('index'))

        try:
            metadata_dict = json_module.loads(metadata) if metadata.strip() else {}
        except json_module.JSONDecodeError as e:
            flash(f'Invalid metadata JSON: {e}', 'error')
            return redirect(url_for('entity_detail', entity_id=from_entity))

        result = engine.create_relationship(from_entity, to_entity, relationship_type, metadata_dict)

        if result.success:
            flash('Relationship created successfully', 'success')
        else:
            flash(f'Error creating relationship: {result.error}', 'error')

        return redirect(url_for('entity_detail', entity_id=from_entity))

    @app.route('/relationship/<relationship_id>/delete', methods=['POST'])
    def delete_relationship(relationship_id: str):
        """Delete a relationship."""
        engine = get_engine()

        # Get relationship to find source entity for redirect
        relationship = engine.storage.get_relationship(relationship_id)
        if not relationship:
            flash('Relationship not found', 'error')
            return redirect(url_for('index'))

        from_entity_id = relationship.from_entity
        result = engine.delete_relationship(relationship_id)

        if result.success:
            flash('Relationship deleted successfully', 'success')
        else:
            flash(f'Error deleting relationship: {result.error}', 'error')

        return redirect(url_for('entity_detail', entity_id=from_entity_id))

    # ========== API Endpoints ==========

    @app.route('/api/entities')
    def api_entities():
        """JSON API: List all entities."""
        engine = get_engine()
        entities = engine.list_entities()
        return jsonify([e.to_dict() for e in entities])

    @app.route('/api/entity/<entity_id>')
    def api_entity(entity_id: str):
        """JSON API: Get entity details."""
        engine = get_engine()
        entity = engine.get_entity(entity_id)

        if not entity:
            return jsonify({'error': 'Entity not found'}), 404

        components = engine.get_entity_components(entity_id)
        relationships = engine.get_relationships(entity_id)

        return jsonify({
            'entity': entity.to_dict(),
            'components': components,
            'relationships': [r.to_dict() for r in relationships]
        })

    @app.route('/api/events')
    def api_events():
        """JSON API: Get recent events."""
        engine = get_engine()
        limit = request.args.get('limit', 50, type=int)
        entity_id = request.args.get('entity_id', None)
        event_type = request.args.get('type', None)

        events = engine.get_events(
            entity_id=entity_id,
            event_type=event_type,
            limit=limit
        )

        return jsonify([e.to_dict() for e in events])

    @app.route('/api/types')
    def api_types():
        """JSON API: Get registered types."""
        engine = get_engine()
        return jsonify({
            'components': engine.storage.get_component_types(),
            'relationships': engine.storage.get_relationship_types(),
            'events': engine.storage.get_event_types()
        })

    return app


def main():
    """Run development server."""
    import argparse

    parser = argparse.ArgumentParser(description='Arcane Arsenal Web Viewer')
    parser.add_argument('world_path', help='Path to world directory')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    # Verify world exists
    if not os.path.exists(os.path.join(args.world_path, 'world.db')):
        print(f"Error: World not found at {args.world_path}", file=sys.stderr)
        sys.exit(1)

    app = create_app(args.world_path)

    print(f"\nArcane Arsenal Web Viewer")
    print(f"World: {args.world_path}")
    print(f"URL: http://{args.host}:{args.port}")
    print(f"\nPress Ctrl+C to stop\n")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
