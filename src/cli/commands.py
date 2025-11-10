#!/usr/bin/env python3
"""
Command-line interface for Arcane Arsenal.

Provides commands for initializing worlds and managing entities, components,
and relationships from the terminal.
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.state_engine import StateEngine
from src.core.result import Result


def cmd_init(args):
    """Initialize a new world."""
    try:
        world_name = args.name or Path(args.world_path).name
        engine = StateEngine.initialize_world(args.world_path, world_name)
        print(f"✓ World '{world_name}' initialized at {args.world_path}")
        print(f"  Database: {args.world_path}/world.db")
        print(f"  System entity created")
        print(f"  Core components registered: Identity, Position")
        print(f"  Core relationships registered: located_at, contains")
    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_entity_create(args):
    """Create a new entity."""
    try:
        engine = StateEngine(args.world_path)
        result = engine.create_entity(args.name)

        if result.success:
            entity = result.data
            print(f"✓ Entity created:")
            print(f"  ID: {entity['id']}")
            print(f"  Name: {entity['name']}")
        else:
            print(f"✗ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_entity_list(args):
    """List all entities."""
    try:
        engine = StateEngine(args.world_path)
        entities = engine.list_entities(include_deleted=args.include_deleted)

        if not entities:
            print("No entities found")
            return

        print(f"Found {len(entities)} entities:\n")
        for entity in entities:
            status = " [DELETED]" if not entity.is_active() else ""
            print(f"  {entity.id:20} {entity.name}{status}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_entity_get(args):
    """Get entity details."""
    try:
        engine = StateEngine(args.world_path)
        entity = engine.get_entity(args.entity_id)

        if not entity:
            print(f"✗ Entity {args.entity_id} not found", file=sys.stderr)
            sys.exit(1)

        print(f"Entity: {entity.name}")
        print(f"  ID: {entity.id}")
        print(f"  Created: {entity.created_at}")
        print(f"  Modified: {entity.modified_at}")
        if not entity.is_active():
            print(f"  Status: DELETED")
            print(f"  Deleted at: {entity.deleted_at}")
            print(f"  Deleted by: {entity.deleted_by}")

        # Get components
        components = engine.get_entity_components(args.entity_id)
        if components:
            print(f"\n  Components:")
            for comp_type, data in components.items():
                print(f"    {comp_type}: {json.dumps(data)}")

        # Get relationships
        relationships = engine.get_relationships(args.entity_id)
        if relationships:
            print(f"\n  Relationships:")
            for rel in relationships:
                direction = "→" if rel.from_entity == args.entity_id else "←"
                other = rel.to_entity if rel.from_entity == args.entity_id else rel.from_entity
                print(f"    {direction} {rel.relationship_type} {other}")
                if rel.metadata:
                    print(f"       Metadata: {json.dumps(rel.metadata)}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_entity_delete(args):
    """Delete an entity."""
    try:
        engine = StateEngine(args.world_path)
        result = engine.delete_entity(args.entity_id)

        if result.success:
            print(f"✓ Entity {args.entity_id} deleted")
        else:
            print(f"✗ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_component_add(args):
    """Add a component to an entity."""
    try:
        engine = StateEngine(args.world_path)

        # Parse JSON data
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

        result = engine.add_component(args.entity_id, args.component_type, data)

        if result.success:
            component = result.data
            print(f"✓ Component added:")
            print(f"  Entity: {args.entity_id}")
            print(f"  Type: {args.component_type}")
            print(f"  Data: {json.dumps(data, indent=2)}")
        else:
            print(f"✗ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_component_list(args):
    """List components of an entity."""
    try:
        engine = StateEngine(args.world_path)
        components = engine.get_entity_components(args.entity_id)

        if not components:
            print(f"Entity {args.entity_id} has no components")
            return

        print(f"Components of {args.entity_id}:\n")
        for comp_type, data in components.items():
            print(f"  {comp_type}:")
            print(f"    {json.dumps(data, indent=4)}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_component_get(args):
    """Get a specific component."""
    try:
        engine = StateEngine(args.world_path)
        component = engine.get_component(args.entity_id, args.component_type)

        if not component:
            print(f"✗ Component {args.component_type} not found on entity {args.entity_id}",
                  file=sys.stderr)
            sys.exit(1)

        print(f"Component: {args.component_type}")
        print(f"  Entity: {args.entity_id}")
        print(f"  Version: {component.version}")
        print(f"  Data:")
        print(f"    {json.dumps(component.data, indent=4)}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_relationship_create(args):
    """Create a relationship between entities."""
    try:
        engine = StateEngine(args.world_path)

        # Parse metadata if provided
        metadata = None
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except json.JSONDecodeError as e:
                print(f"✗ Invalid JSON in metadata: {e}", file=sys.stderr)
                sys.exit(1)

        result = engine.create_relationship(
            args.from_entity,
            args.to_entity,
            args.relationship_type,
            metadata
        )

        if result.success:
            rel = result.data
            print(f"✓ Relationship created:")
            print(f"  {args.from_entity} → {args.relationship_type} → {args.to_entity}")
            if metadata:
                print(f"  Metadata: {json.dumps(metadata)}")
        else:
            print(f"✗ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_relationship_list(args):
    """List relationships for an entity."""
    try:
        engine = StateEngine(args.world_path)
        relationships = engine.get_relationships(
            args.entity_id,
            rel_type=args.type,
            direction=args.direction
        )

        if not relationships:
            print(f"No relationships found for {args.entity_id}")
            return

        print(f"Relationships for {args.entity_id}:\n")
        for rel in relationships:
            if rel.from_entity == args.entity_id:
                print(f"  → {rel.relationship_type} → {rel.to_entity}")
            else:
                print(f"  ← {rel.relationship_type} ← {rel.from_entity}")

            if rel.metadata:
                print(f"     Metadata: {json.dumps(rel.metadata)}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_events(args):
    """View event log."""
    try:
        engine = StateEngine(args.world_path)
        events = engine.get_events(
            entity_id=args.entity,
            event_type=args.type,
            limit=args.limit
        )

        if not events:
            print("No events found")
            return

        print(f"Events (showing {len(events)}):\n")
        for event in events:
            print(f"  [{event.timestamp}] {event.event_type}")
            if event.entity_id:
                print(f"    Entity: {event.entity_id}")
            if event.actor_id:
                print(f"    Actor: {event.actor_id}")
            print(f"    Data: {json.dumps(event.data)}")
            print()
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_types_components(args):
    """List registered component types."""
    try:
        engine = StateEngine(args.world_path)
        types = engine.get_component_types()

        if not types:
            print("No component types registered")
            return

        print("Registered component types:\n")
        for t in types:
            print(f"  {t['type']:20} (v{t['schema_version']:6}) - {t['description']}")
            print(f"    Module: {t['module']}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_types_relationships(args):
    """List registered relationship types."""
    try:
        engine = StateEngine(args.world_path)
        types = engine.get_relationship_types()

        if not types:
            print("No relationship types registered")
            return

        print("Registered relationship types:\n")
        for t in types:
            print(f"  {t['type']:20} - {t['description']}")
            print(f"    Module: {t['module']}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Arcane Arsenal - ECS-based roleplaying state manager'
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # ========== init command ==========
    parser_init = subparsers.add_parser('init', help='Initialize a new world')
    parser_init.add_argument('world_path', help='Path to world directory')
    parser_init.add_argument('--name', help='World name (defaults to directory name)')
    parser_init.set_defaults(func=cmd_init)

    # ========== entity commands ==========
    parser_entity = subparsers.add_parser('entity', help='Entity operations')
    entity_subparsers = parser_entity.add_subparsers(dest='entity_command')

    # entity create
    parser_entity_create = entity_subparsers.add_parser('create', help='Create an entity')
    parser_entity_create.add_argument('world_path', help='Path to world directory')
    parser_entity_create.add_argument('name', help='Entity name')
    parser_entity_create.set_defaults(func=cmd_entity_create)

    # entity list
    parser_entity_list = entity_subparsers.add_parser('list', help='List entities')
    parser_entity_list.add_argument('world_path', help='Path to world directory')
    parser_entity_list.add_argument('--include-deleted', action='store_true',
                                    help='Include soft-deleted entities')
    parser_entity_list.set_defaults(func=cmd_entity_list)

    # entity get
    parser_entity_get = entity_subparsers.add_parser('get', help='Get entity details')
    parser_entity_get.add_argument('world_path', help='Path to world directory')
    parser_entity_get.add_argument('entity_id', help='Entity ID')
    parser_entity_get.set_defaults(func=cmd_entity_get)

    # entity delete
    parser_entity_delete = entity_subparsers.add_parser('delete', help='Delete an entity')
    parser_entity_delete.add_argument('world_path', help='Path to world directory')
    parser_entity_delete.add_argument('entity_id', help='Entity ID')
    parser_entity_delete.set_defaults(func=cmd_entity_delete)

    # ========== component commands ==========
    parser_component = subparsers.add_parser('component', help='Component operations')
    component_subparsers = parser_component.add_subparsers(dest='component_command')

    # component add
    parser_component_add = component_subparsers.add_parser('add', help='Add a component')
    parser_component_add.add_argument('world_path', help='Path to world directory')
    parser_component_add.add_argument('entity_id', help='Entity ID')
    parser_component_add.add_argument('component_type', help='Component type')
    parser_component_add.add_argument('data', help='Component data as JSON')
    parser_component_add.set_defaults(func=cmd_component_add)

    # component list
    parser_component_list = component_subparsers.add_parser('list', help='List components')
    parser_component_list.add_argument('world_path', help='Path to world directory')
    parser_component_list.add_argument('entity_id', help='Entity ID')
    parser_component_list.set_defaults(func=cmd_component_list)

    # component get
    parser_component_get = component_subparsers.add_parser('get', help='Get a component')
    parser_component_get.add_argument('world_path', help='Path to world directory')
    parser_component_get.add_argument('entity_id', help='Entity ID')
    parser_component_get.add_argument('component_type', help='Component type')
    parser_component_get.set_defaults(func=cmd_component_get)

    # ========== relationship commands ==========
    parser_relationship = subparsers.add_parser('relationship', help='Relationship operations')
    relationship_subparsers = parser_relationship.add_subparsers(dest='relationship_command')

    # relationship create
    parser_relationship_create = relationship_subparsers.add_parser('create',
                                                                    help='Create a relationship')
    parser_relationship_create.add_argument('world_path', help='Path to world directory')
    parser_relationship_create.add_argument('from_entity', help='Source entity ID')
    parser_relationship_create.add_argument('to_entity', help='Target entity ID')
    parser_relationship_create.add_argument('relationship_type', help='Relationship type')
    parser_relationship_create.add_argument('--metadata', help='Metadata as JSON')
    parser_relationship_create.set_defaults(func=cmd_relationship_create)

    # relationship list
    parser_relationship_list = relationship_subparsers.add_parser('list',
                                                                  help='List relationships')
    parser_relationship_list.add_argument('world_path', help='Path to world directory')
    parser_relationship_list.add_argument('entity_id', help='Entity ID')
    parser_relationship_list.add_argument('--type', help='Filter by relationship type')
    parser_relationship_list.add_argument('--direction', default='both',
                                         choices=['from', 'to', 'both'],
                                         help='Relationship direction')
    parser_relationship_list.set_defaults(func=cmd_relationship_list)

    # ========== events command ==========
    parser_events = subparsers.add_parser('events', help='View event log')
    parser_events.add_argument('world_path', help='Path to world directory')
    parser_events.add_argument('--entity', help='Filter by entity ID')
    parser_events.add_argument('--type', help='Filter by event type')
    parser_events.add_argument('--limit', type=int, default=20, help='Number of events to show')
    parser_events.set_defaults(func=cmd_events)

    # ========== types commands ==========
    parser_types = subparsers.add_parser('types', help='View registered types')
    types_subparsers = parser_types.add_subparsers(dest='types_command')

    # types components
    parser_types_components = types_subparsers.add_parser('components',
                                                          help='List component types')
    parser_types_components.add_argument('world_path', help='Path to world directory')
    parser_types_components.set_defaults(func=cmd_types_components)

    # types relationships
    parser_types_relationships = types_subparsers.add_parser('relationships',
                                                             help='List relationship types')
    parser_types_relationships.add_argument('world_path', help='Path to world directory')
    parser_types_relationships.set_defaults(func=cmd_types_relationships)

    # Parse and execute
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, 'func'):
        args.func(args)
    else:
        print(f"No subcommand provided for '{args.command}'", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
