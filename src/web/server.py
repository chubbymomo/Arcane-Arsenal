"""
Web viewer for Arcane Arsenal.

Simple Flask app to browse world state in a web browser.
Provides read-only viewing of entities, components, relationships, and events.
"""

from flask import Flask, render_template, jsonify, request
import sys
import os
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

        return render_template('index.html', entities=entity_data)

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

        return render_template(
            'entity.html',
            entity=entity,
            components=components,
            outgoing=outgoing,
            incoming=incoming,
            events=events
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
