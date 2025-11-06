"""
Web interface for Arcane Arsenal.

Flask app with separate client (player) and host (DM) interfaces.
- /: World selector landing page
- /client: Player interface for character management
- /host: DM interface for full state management
"""

from flask import Flask, jsonify, request, redirect, url_for, session, render_template, flash
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.state_engine import StateEngine
from src.web.blueprints import client_bp, host_bp


def create_app(worlds_dir: str = 'worlds') -> Flask:
    """
    Create Flask app with world selection support.

    Args:
        worlds_dir: Directory containing world folders (default: 'worlds')

    Returns:
        Configured Flask app with client and host blueprints
    """
    app = Flask(__name__)
    app.config['WORLDS_DIR'] = worlds_dir
    app.config['SECRET_KEY'] = os.urandom(24)  # For sessions and flash messages

    # Register blueprints
    app.register_blueprint(client_bp)
    app.register_blueprint(host_bp)

    # Helper: Get list of available worlds
    def get_available_worlds():
        """Return list of world directories with their metadata."""
        if not os.path.exists(worlds_dir):
            return []

        worlds = []
        for item in os.listdir(worlds_dir):
            world_path = os.path.join(worlds_dir, item)
            db_path = os.path.join(world_path, 'world.db')
            config_path = os.path.join(world_path, 'config.json')

            if os.path.isdir(world_path) and os.path.exists(db_path):
                world_info = {'name': item, 'path': world_path}

                # Try to read world name from config
                if os.path.exists(config_path):
                    try:
                        import json
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            world_info['display_name'] = config.get('world_name', item)
                    except:
                        world_info['display_name'] = item
                else:
                    world_info['display_name'] = item

                worlds.append(world_info)

        return sorted(worlds, key=lambda w: w['name'])

    # Root route - World selector
    @app.route('/')
    def index():
        """World selection landing page."""
        worlds = get_available_worlds()
        current_world = session.get('world_path')

        return render_template('world_selector.html',
                             worlds=worlds,
                             current_world=current_world)

    @app.route('/select_world', methods=['POST'])
    def select_world():
        """Select a world and store in session."""
        world_name = request.form.get('world_name')

        if not world_name:
            flash('Please select a world', 'error')
            return redirect(url_for('index'))

        world_path = os.path.join(worlds_dir, world_name)
        db_path = os.path.join(world_path, 'world.db')

        if not os.path.exists(db_path):
            flash(f'World "{world_name}" not found', 'error')
            return redirect(url_for('index'))

        # Store world in session
        session['world_path'] = world_path
        session['world_name'] = world_name
        flash(f'Loaded world: {world_name}', 'success')

        # Redirect to client interface
        return redirect(url_for('client.index'))

    @app.route('/switch_world')
    def switch_world():
        """Clear world selection and return to selector."""
        session.pop('world_path', None)
        session.pop('world_name', None)
        flash('World unloaded', 'info')
        return redirect(url_for('index'))

    # ========== API Endpoints ==========

    def get_current_world_path():
        """Get current world path from session or return None."""
        return session.get('world_path')

    @app.route('/api/entities')
    def api_entities():
        """JSON API: List all entities."""
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
        entities = engine.list_entities()
        return jsonify([e.to_dict() for e in entities])

    @app.route('/api/entity/<entity_id>')
    def api_entity(entity_id: str):
        """JSON API: Get entity details."""
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
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
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
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
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
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
    parser.add_argument('--worlds-dir', default='worlds', help='Directory containing worlds (default: worlds)')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    # Create worlds directory if it doesn't exist
    if not os.path.exists(args.worlds_dir):
        os.makedirs(args.worlds_dir)
        print(f"Created worlds directory: {args.worlds_dir}")

    app = create_app(args.worlds_dir)

    print(f"\n╔══════════════════════════════════════════════════╗")
    print(f"║     Arcane Arsenal Web Interface                 ║")
    print(f"╚══════════════════════════════════════════════════╝")
    print(f"")
    print(f"  Worlds directory: {args.worlds_dir}")
    print(f"  Server URL:       http://{args.host}:{args.port}")
    print(f"")
    print(f"  1. Open http://{args.host}:{args.port} in your browser")
    print(f"  2. Select a world from the list")
    print(f"  3. Start playing!")
    print(f"")
    print(f"  Press Ctrl+C to stop")
    print(f"")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
