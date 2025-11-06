"""
Web interface for Arcane Arsenal.

Flask app with separate client (player) and host (DM) interfaces.
- /client: Player interface for character management
- /host: DM interface for full state management
"""

from flask import Flask, jsonify, request, redirect, url_for
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.state_engine import StateEngine
from src.web.blueprints import client_bp, host_bp


def create_app(world_path: str) -> Flask:
    """
    Create Flask app for viewing a world.

    Args:
        world_path: Path to world directory

    Returns:
        Configured Flask app with client and host blueprints
    """
    app = Flask(__name__)
    app.config['WORLD_PATH'] = world_path
    app.config['SECRET_KEY'] = os.urandom(24)  # For flash messages

    # Register blueprints
    app.register_blueprint(client_bp)
    app.register_blueprint(host_bp)

    # Root route - redirect to client
    @app.route('/')
    def index():
        """Redirect to client interface."""
        return redirect(url_for('client.index'))

    # ========== API Endpoints ==========

    @app.route('/api/entities')
    def api_entities():
        """JSON API: List all entities."""
        engine = StateEngine(app.config['WORLD_PATH'])
        entities = engine.list_entities()
        return jsonify([e.to_dict() for e in entities])

    @app.route('/api/entity/<entity_id>')
    def api_entity(entity_id: str):
        """JSON API: Get entity details."""
        engine = StateEngine(app.config['WORLD_PATH'])
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
        engine = StateEngine(app.config['WORLD_PATH'])
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
        engine = StateEngine(app.config['WORLD_PATH'])
        return jsonify({
            'components': engine.storage.get_component_types(),
            'relationships': engine.storage.get_relationship_types(),
            'events': engine.storage.get_event_types()
        })

    return app


def main():
    """Run development server."""
    import argparse

    parser = argparse.ArgumentParser(description='Arcane Arsenal Web Interface')
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

    print(f"\nArcane Arsenal Web Interface")
    print(f"World: {args.world_path}")
    print(f"")
    print(f"  Client (Player): http://{args.host}:{args.port}/client")
    print(f"  Host (DM):       http://{args.host}:{args.port}/host")
    print(f"")
    print(f"Press Ctrl+C to stop\n")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
