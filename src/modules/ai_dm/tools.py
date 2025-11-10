"""
AI DM Tools - Functions the AI can call to interact with the game world.

These tools give the AI the ability to create entities, query game state,
and modify the world in structured ways beyond just narrative text.

This module also provides a registry system so other modules can register
their own tools (e.g., spell casting, crafting, etc.).
"""

import logging
from typing import Dict, Any, List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


def _format_error(message: str) -> str:
    """Format an error message in red for display."""
    return f'<span style="color: #ff4444; font-weight: bold;">❌ {message}</span>'


def _format_success(message: str) -> str:
    """Format a success message in green for display."""
    return f'<span style="color: #44ff44;">✅ {message}</span>'


# Tool registry - modules can add their own tools here
_tool_registry: Dict[str, Callable] = {}
_tool_definitions: List[Dict[str, Any]] = []


def register_tool(definition: Dict[str, Any], handler: Callable):
    """
    Register a new tool that the AI can use.

    Args:
        definition: Tool definition dict with name, description, input_schema
        handler: Function that takes (engine, player_entity_id, tool_input) and returns result dict

    Example:
        def cast_spell_handler(engine, player_id, tool_input):
            spell_name = tool_input['spell_name']
            # ... cast the spell ...
            return {'success': True, 'message': f'Cast {spell_name}!'}

        register_tool({
            'name': 'cast_spell',
            'description': 'Cast a magical spell',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'spell_name': {'type': 'string', 'description': 'Name of the spell'}
                },
                'required': ['spell_name']
            }
        }, cast_spell_handler)
    """
    tool_name = definition['name']
    _tool_registry[tool_name] = handler
    _tool_definitions.append(definition)
    logger.info(f"Registered tool: {tool_name}")


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get all registered tool definitions for the LLM."""
    return _tool_definitions.copy()


def get_tool_handler(tool_name: str) -> Callable:
    """Get the handler function for a tool."""
    return _tool_registry.get(tool_name)


def generate_tool_documentation() -> str:
    """
    Generate human-readable documentation for all registered tools.

    This creates formatted documentation from the tool registry that can be
    included in the AI's context, so tools are self-documenting.

    Returns:
        Formatted markdown documentation of all available tools
    """
    if not _tool_definitions:
        return "No tools currently available."

    doc_parts = ["## Available Tools\n"]
    doc_parts.append("You have access to the following tools to interact with the game world:\n")

    for tool in _tool_definitions:
        name = tool['name']
        description = tool['description']
        schema = tool['input_schema']

        # Tool header
        doc_parts.append(f"\n### `{name}`")
        doc_parts.append(f"{description}\n")

        # Parameters
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        if properties:
            doc_parts.append("**Parameters:**")
            for param_name, param_info in properties.items():
                param_desc = param_info.get('description', 'No description')
                param_type = param_info.get('type', 'any')
                req_marker = " *(required)*" if param_name in required else " *(optional)*"
                doc_parts.append(f"- `{param_name}` ({param_type}){req_marker}: {param_desc}")
            doc_parts.append("")  # Blank line

    return "\n".join(doc_parts)


# Core tool definitions for LLM function calling
_CORE_TOOL_DEFINITIONS = [
    {
        "name": "create_npc",
        "description": "Create a new NPC (non-player character) in the game world. Use this when an NPC first appears in the story. NPCs can have classes and levels for mechanical depth (e.g., wizard innkeeper, cleric healer).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The NPC's name (e.g., 'Blacksmith Gorn', 'Mysterious Hooded Figure')"
                },
                "description": {
                    "type": "string",
                    "description": "Physical description and notable features"
                },
                "race": {
                    "type": "string",
                    "description": "The NPC's race (e.g., 'human', 'elf', 'dwarf', 'orc') - use values from Game System races list"
                },
                "occupation": {
                    "type": "string",
                    "description": "The NPC's occupation or role (e.g., 'blacksmith', 'guard', 'merchant', 'wizard')"
                },
                "npc_class": {
                    "type": "string",
                    "description": "Optional: NPC's class for mechanical abilities (e.g., 'wizard', 'cleric', 'fighter') - use values from Game System classes list. Omit for non-combatant NPCs."
                },
                "level": {
                    "type": "integer",
                    "description": "Optional: NPC's level if they have a class (default: 1). Determines their capabilities."
                },
                "disposition": {
                    "type": "string",
                    "description": "Initial attitude toward the player ('friendly', 'neutral', 'hostile', 'fearful')"
                },
                "location_name": {
                    "type": "string",
                    "description": "REQUIRED: Name of the location where the NPC is. MUST match an existing location entity created with create_location. Query first to check if location exists!"
                }
            },
            "required": ["name", "description", "disposition", "location_name"]
        }
    },
    {
        "name": "create_location",
        "description": "Create a new location in the game world. Use this when the player enters a new area that should be tracked.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The location's name (e.g., 'The Rusty Tankard Tavern', 'Ancient Crypt')"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the location"
                },
                "region": {
                    "type": "string",
                    "description": "The broader region this location is in (e.g., 'The Borderlands', 'Shadowmere Valley', 'The Iron Coast'). Create a unique, evocative region name - do NOT use generic names like 'The Realm'."
                },
                "location_type": {
                    "type": "string",
                    "description": "Type of location (e.g., 'tavern', 'dungeon', 'shop', 'wilderness', 'building')"
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Notable features (e.g., ['fireplace', 'bar', 'stage'])"
                }
            },
            "required": ["name", "description", "region", "location_type"]
        }
    },
    {
        "name": "create_item",
        "description": "Create a new item that can be interacted with or acquired. Use this for loot, quest items, or notable objects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The item's name (e.g., 'Rusty Longsword', 'Ancient Tome')"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the item"
                },
                "item_type": {
                    "type": "string",
                    "description": "Type of item (e.g., 'weapon', 'armor', 'consumable', 'quest_item', 'treasure')"
                },
                "location": {
                    "type": "string",
                    "description": "Where the item currently is (location name or 'player_inventory' if given to player)"
                },
                "value": {
                    "type": "integer",
                    "description": "Gold piece value of the item"
                }
            },
            "required": ["name", "description", "item_type"]
        }
    },
    {
        "name": "roll_dice",
        "description": "Roll dice to determine outcomes. Use this when the player attempts something with uncertain results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dice_notation": {
                    "type": "string",
                    "description": "Dice to roll in standard notation (e.g., '1d20', '2d6+3', '1d20+5')"
                },
                "skill": {
                    "type": "string",
                    "description": "Skill being tested (e.g., 'perception', 'stealth', 'persuasion')"
                },
                "difficulty": {
                    "type": "integer",
                    "description": "DC (Difficulty Class) for the check (typically 5-30)"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this roll is being made (e.g., 'Attempting to pick the lock')"
                }
            },
            "required": ["dice_notation", "reason"]
        }
    },
    {
        "name": "move_player_to_location",
        "description": "Move the player character to a different location. Use this when they travel or enter a new area.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location_name": {
                    "type": "string",
                    "description": "Name of the location to move to (must exist or be created first)"
                },
                "region": {
                    "type": "string",
                    "description": "The region name if moving to a new region"
                }
            },
            "required": ["location_name"]
        }
    },
    {
        "name": "query_entities",
        "description": "Search for existing entities in the game world. Use this to check if an NPC, location, or item already exists before creating a duplicate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Type of entity to search for ('npc', 'location', 'item', 'player')"
                },
                "name_pattern": {
                    "type": "string",
                    "description": "Name or partial name to search for (case-insensitive)"
                },
                "location": {
                    "type": "string",
                    "description": "Filter by location (optional)"
                }
            },
            "required": ["entity_type"]
        }
    },
    {
        "name": "update_npc_disposition",
        "description": "Change how an NPC feels about the player based on their actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "npc_name": {
                    "type": "string",
                    "description": "Name of the NPC"
                },
                "new_disposition": {
                    "type": "string",
                    "description": "New disposition ('friendly', 'neutral', 'hostile', 'fearful', 'admiring')"
                },
                "reason": {
                    "type": "string",
                    "description": "Why the disposition changed"
                }
            },
            "required": ["npc_name", "new_disposition", "reason"]
        }
    },
    {
        "name": "give_item_to_player",
        "description": "Add an item to the player's inventory. The item must exist (create it first if needed).",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "Name of the item to give"
                },
                "quantity": {
                    "type": "integer",
                    "description": "How many to give (default 1)"
                }
            },
            "required": ["item_name"]
        }
    },
    {
        "name": "remove_item",
        "description": "Remove an item from the player's inventory. Use this when items are consumed, dropped, destroyed, or given away.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "Name of the item to remove"
                },
                "quantity": {
                    "type": "integer",
                    "description": "How many to remove (default: all)"
                },
                "reason": {
                    "type": "string",
                    "description": "Why the item was removed (e.g., 'consumed potion', 'dropped in river', 'given to guard')"
                }
            },
            "required": ["item_name", "reason"]
        }
    },
    {
        "name": "deal_damage",
        "description": "Apply damage to the player character. Use this when they take damage from combat, traps, or hazards.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "Amount of damage to deal"
                },
                "damage_type": {
                    "type": "string",
                    "description": "Type of damage ('slashing', 'piercing', 'bludgeoning', 'fire', 'cold', 'poison', etc.)"
                },
                "source": {
                    "type": "string",
                    "description": "What caused the damage (e.g., 'goblin sword', 'falling rocks', 'poison trap')"
                }
            },
            "required": ["amount", "source"]
        }
    },
    {
        "name": "heal_player",
        "description": "Restore hit points to the player character.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "Amount of HP to restore"
                },
                "source": {
                    "type": "string",
                    "description": "What caused the healing (e.g., 'healing potion', 'rest', 'divine blessing')"
                }
            },
            "required": ["amount", "source"]
        }
    },
    {
        "name": "long_rest",
        "description": "The player takes a long rest (8+ hours). Restores HP to max, recovers all spell slots, and resets daily abilities. Use when player sleeps at an inn, camps overnight, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Where the rest occurred (e.g., 'inn room', 'forest camp', 'cave')"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_entity_details",
        "description": "Get complete details about an entity including all its components. Use this to inspect an entity's current state before modifying it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Name of the entity to inspect"
                },
                "entity_type": {
                    "type": "string",
                    "description": "Type of entity ('npc', 'location', 'item', 'player') to narrow search"
                }
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "update_component",
        "description": "Update a component's data on any entity. Use this to modify NPC stats, location features, item properties, etc. Get entity details first to see current values.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Name of the entity to update"
                },
                "component_type": {
                    "type": "string",
                    "description": "Component to update (e.g., 'Identity', 'NPC', 'Location', 'Item', 'Health')"
                },
                "updates": {
                    "type": "object",
                    "description": "Fields to update with new values (e.g., {'race': 'elf', 'occupation': 'mage'})"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this update is being made (for narrative context)"
                }
            },
            "required": ["entity_name", "component_type", "updates", "reason"]
        }
    },
    {
        "name": "add_component",
        "description": "Add a new component to an existing entity. Use this to give an NPC combat stats, add health tracking to an entity, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Name of the entity"
                },
                "component_type": {
                    "type": "string",
                    "description": "Component type to add (e.g., 'Health', 'CharacterDetails', 'Magic')"
                },
                "component_data": {
                    "type": "object",
                    "description": "Initial data for the component (schema depends on component type)"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this component is being added"
                }
            },
            "required": ["entity_name", "component_type", "component_data", "reason"]
        }
    },
    {
        "name": "remove_component",
        "description": "Remove a component from an entity. Use carefully - this removes capabilities (e.g., removing Health makes entity not trackable in combat).",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Name of the entity"
                },
                "component_type": {
                    "type": "string",
                    "description": "Component type to remove"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this component is being removed"
                }
            },
            "required": ["entity_name", "component_type", "reason"]
        }
    },
    {
        "name": "add_relationship",
        "description": "Create a relationship between two entities. Use this to establish connections like ownership, location, allegiance, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_entity_name": {
                    "type": "string",
                    "description": "Name of the source entity"
                },
                "to_entity_name": {
                    "type": "string",
                    "description": "Name of the target entity"
                },
                "relationship_type": {
                    "type": "string",
                    "description": "Type of relationship (e.g., 'owns', 'located_at', 'ally_of', 'enemy_of', 'knows')"
                },
                "relationship_data": {
                    "type": "object",
                    "description": "Optional data for the relationship (depends on relationship type)"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this relationship is being created"
                }
            },
            "required": ["from_entity_name", "to_entity_name", "relationship_type", "reason"]
        }
    },
    {
        "name": "remove_relationship",
        "description": "Remove a relationship between two entities. Use when relationships end (ownership transfer, allegiance breaks, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_entity_name": {
                    "type": "string",
                    "description": "Name of the source entity"
                },
                "to_entity_name": {
                    "type": "string",
                    "description": "Name of the target entity"
                },
                "relationship_type": {
                    "type": "string",
                    "description": "Type of relationship to remove"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this relationship is being removed"
                }
            },
            "required": ["from_entity_name", "to_entity_name", "relationship_type", "reason"]
        }
    },
    {
        "name": "query_relationships",
        "description": "Query relationships for an entity. Use to find what/who an entity is connected to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Name of the entity to query relationships for"
                },
                "relationship_type": {
                    "type": "string",
                    "description": "Optional: Filter by specific relationship type"
                },
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "description": "Direction of relationships to query (default: both)"
                }
            },
            "required": ["entity_name"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: Dict[str, Any], engine, player_entity_id: str) -> Dict[str, Any]:
    """
    Execute a tool call from the AI.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Parameters for the tool
        engine: Game engine instance
        player_entity_id: ID of the player character entity

    Returns:
        Result dict with 'success', 'message', and optional 'data' fields
    """
    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

    try:
        handler = get_tool_handler(tool_name)
        if not handler:
            return {
                "success": False,
                "message": f"Unknown tool: {tool_name}"
            }

        # All handlers follow the standard signature
        return handler(engine, player_entity_id, tool_input)

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Tool execution failed: {str(e)}"
        }


def _create_npc(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Create an NPC entity."""
    name = tool_input["name"]
    description = tool_input["description"]
    disposition = tool_input.get("disposition", "neutral")
    race = tool_input.get("race", "human")
    occupation = tool_input.get("occupation", "commoner")
    npc_class = tool_input.get("npc_class")  # Optional class
    level = tool_input.get("level", 1)  # Default level 1
    location = tool_input.get("location")

    # Create entity
    result = engine.create_entity(name)
    if not result.success:
        return {"success": False, "message": f"Failed to create NPC: {result.error}"}

    npc_id = result.data['id']

    # Add Identity component (description only)
    identity_data = {
        'description': description
    }
    result = engine.add_component(npc_id, 'Identity', identity_data)
    if not result.success:
        logger.error(f"  ✗ Failed to add Identity: {result.error}")
        return {"success": False, "message": _format_error(f"Failed to add Identity component: {result.error}")}
    logger.info(f"  → Added Identity: desc={description[:50]}...")

    # Add CharacterDetails if class is provided (enables mechanics like spells, skills)
    if npc_class:
        char_details = {
            'character_class': npc_class,
            'level': level,
            'race': race  # Also in CharacterDetails for module compatibility
        }
        result = engine.add_component(npc_id, 'CharacterDetails', char_details)
        if not result.success:
            logger.error(f"  ✗ Failed to add CharacterDetails: {result.error}")
        else:
            logger.info(f"  → Added CharacterDetails: class={npc_class}, level={level}")
        # Note: This will trigger auto-add of Magic/Skills components via events if applicable

    # Add NPC component (includes race and occupation)
    result = engine.add_component(npc_id, 'NPC', {
        'race': race,
        'occupation': occupation,
        'disposition': disposition,
        'dialogue_state': 'initial',
        'met_player': False
    })
    if not result.success:
        logger.error(f"  ✗ Failed to add NPC component: {result.error}")
        return {"success": False, "message": _format_error(f"Failed to add NPC component: {result.error}")}
    logger.info(f"  → Added NPC component: race={race}, occupation={occupation}, disposition={disposition}")

    # Add Position component - entity-based hierarchical positioning
    location_name = tool_input.get("location_name")
    if location_name:
        # Query for location entity by name (entity-based positioning)
        location_entities = engine.query_entities(['Location'])
        location_entity = None
        for loc in location_entities:
            if loc.name.lower() == location_name.lower():
                location_entity = loc
                break

        if location_entity:
            # Position NPC AT the location entity (using entity ID)
            position_data = {
                'region': location_entity.id  # Entity reference! NPC is IN this location
            }
            result = engine.add_component(npc_id, 'Position', position_data)
            if not result.success:
                logger.error(f"  ✗ Failed to add Position: {result.error}")
            else:
                logger.info(f"  → Added Position: region={location_entity.id} ({location_entity.name})")
        else:
            logger.warning(f"  ⚠ Location '{location_name}' not found! NPC created without position.")
            # Fall back to player's location
            player_position = engine.get_component(player_entity_id, 'Position')
            if player_position:
                position_data = {'region': player_position.data.get('region')}
                result = engine.add_component(npc_id, 'Position', position_data)
                if not result.success:
                    logger.error(f"  ✗ Failed to add fallback Position: {result.error}")
                else:
                    logger.info(f"  → Fallback: Added Position at player's location: region={position_data['region']}")
    else:
        logger.warning(f"  ⚠ No location_name provided for NPC {name}")

    logger.info(f"Created NPC: {name} ({npc_id})")
    return {
        "success": True,
        "message": f"Created NPC '{name}' with {disposition} disposition",
        "data": {"entity_id": npc_id, "name": name}
    }


def _create_location(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a location entity with entity-based hierarchical positioning.

    Locations are entities that other entities can be positioned within.
    They need both Location (marker) and Position (where they are) components.
    """
    name = tool_input["name"]
    description = tool_input["description"]
    location_type = tool_input["location_type"]
    region = tool_input["region"]  # Now required - AI must provide creative region name
    features = tool_input.get("features", [])

    # Create entity
    result = engine.create_entity(name)
    if not result.success:
        return {"success": False, "message": f"Failed to create location: {result.error}"}

    location_id = result.data['id']
    logger.info(f"Creating location: {name} ({location_id})")

    # Add Identity component
    engine.add_component(location_id, 'Identity', {
        'description': description
    })
    logger.info(f"  → Added Identity: desc={description[:50]}...")

    # Add Location component (marker with metadata)
    engine.add_component(location_id, 'Location', {
        'location_type': location_type,
        'features': features,
        'visited': False
    })
    logger.info(f"  → Added Location component: type={location_type}, features={len(features)}")

    # Add Position component (WHERE the location is - in a broader region)
    # This allows hierarchical positioning - locations can be in regions or in other locations
    engine.add_component(location_id, 'Position', {
        'region': region  # Named region string for top-level locations
    })
    logger.info(f"  → Added Position: region={region}")

    logger.info(f"Created Location: {name} ({location_id}) in {region}")
    return {
        "success": True,
        "message": f"Created location '{name}' in {region}",
        "data": {"entity_id": location_id, "name": name, "region": region}
    }


def _create_item(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Create an item entity."""
    name = tool_input["name"]
    description = tool_input["description"]
    item_type = tool_input["item_type"]
    location = tool_input.get("location")
    value = tool_input.get("value", 0)

    # IMPORTANT: Check if item already exists (search by name)
    # This prevents duplicate items when an item exists but lacks the Item component
    all_entities = engine.get_all_entities()
    existing_item = None
    for entity in all_entities:
        if entity.is_active() and entity.name.lower() == name.lower():
            existing_item = entity
            break

    if existing_item:
        # Item already exists! Check if it has the Item component
        item_comp = engine.get_component(existing_item.id, 'Item')
        if item_comp:
            # Item exists and has proper component - return it instead of creating duplicate
            logger.info(f"Item '{name}' already exists ({existing_item.id}), returning existing item")
            return {
                "success": True,
                "message": f"Found existing {item_type} '{name}' (ID: {existing_item.id})",
                "data": {"entity_id": existing_item.id, "name": name, "existing": True}
            }
        else:
            # Item exists but missing Item component - fix it!
            logger.warning(f"Item '{name}' exists ({existing_item.id}) but missing Item component, adding it now")
            engine.add_component(existing_item.id, 'Item', {
                'item_type': item_type,
                'value': value,
                'quantity': 1
            })

            # Update Identity if provided description is different/better
            identity = engine.get_component(existing_item.id, 'Identity')
            if identity and description:
                current_desc = identity.data.get('description', '')
                if not current_desc or len(description) > len(current_desc):
                    engine.update_component(existing_item.id, 'Identity', {'description': description})
                    logger.info(f"  → Updated description for existing item")

            # Update Position if location specified
            if location:
                locations = engine.query_entities(['Location'])
                location_entity = next((e for e in locations if e.name.lower() == location.lower()), None)
                if location_entity:
                    pos = engine.get_component(existing_item.id, 'Position')
                    if not pos:
                        engine.add_component(existing_item.id, 'Position', {'region': location_entity.id})
                        logger.info(f"  → Added Position to existing item at location: {location}")

            return {
                "success": True,
                "message": f"Fixed existing {item_type} '{name}' by adding missing Item component",
                "data": {"entity_id": existing_item.id, "name": name, "fixed": True}
            }

    # Create new entity (no existing item found)
    result = engine.create_entity(name)
    if not result.success:
        return {"success": False, "message": f"Failed to create item: {result.error}"}

    item_id = result.data['id']

    # Add Identity component
    engine.add_component(item_id, 'Identity', {
        'description': description
    })

    # Add Item component
    engine.add_component(item_id, 'Item', {
        'item_type': item_type,
        'value': value,
        'quantity': 1
    })

    # Add Position if location specified (use entity-based positioning)
    if location:
        # Find location entity by name
        locations = engine.query_entities(['Location'])
        location_entity = next((e for e in locations if e.name.lower() == location.lower()), None)

        if location_entity:
            # Position item AT the location (entity-based positioning)
            engine.add_component(item_id, 'Position', {
                'region': location_entity.id  # Entity ID, not string!
            })
            logger.info(f"  → Positioned item at location: {location} ({location_entity.id})")
        else:
            # Fallback: location name as string (legacy)
            engine.add_component(item_id, 'Position', {
                'region': location
            })
            logger.warning(f"  → Location '{location}' not found as entity, using string region")

    logger.info(f"Created Item: {name} ({item_id})")
    return {
        "success": True,
        "message": f"Created {item_type} '{name}'",
        "data": {"entity_id": item_id, "name": name}
    }


def _roll_dice(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Roll dice using the RNG module's event-driven system.

    This integrates with the RNG module so rolls are saved to roll history
    and displayed in the player's character sheet.
    """
    dice_notation = tool_input["dice_notation"]
    reason = tool_input["reason"]
    skill = tool_input.get("skill")
    difficulty = tool_input.get("difficulty")

    # Determine roll type based on skill or default to skill_check
    roll_type = "skill_check"
    if skill:
        # Map common skills to roll types if needed
        # For now, everything is a skill_check
        roll_type = "skill_check"

    # Subscribe to roll.completed BEFORE publishing roll.initiated
    # (Events are processed synchronously, so we need to subscribe first)
    result_data = {}
    def capture_result(event):
        if event.entity_id == player_entity_id:
            result_data.update(event.data)

    # Subscribe FIRST (before publishing event)
    engine.event_bus.subscribe('roll.completed', capture_result)

    # Now publish roll.initiated event - RNG module will process it synchronously
    from src.core.event_bus import Event

    roll_event = Event.create(
        event_type='roll.initiated',
        entity_id=player_entity_id,
        actor_id=player_entity_id,
        data={
            'entity_id': player_entity_id,
            'notation': dice_notation,
            'roll_type': roll_type,
            'purpose': reason
        }
    )

    engine.event_bus.publish(roll_event)

    # Event is processed synchronously, result_data should be populated immediately
    # Unsubscribe right away
    engine.event_bus.unsubscribe('roll.completed', capture_result)

    if not result_data:
        # Fallback: event system didn't work, log error
        logger.error(f"Roll event did not complete for {dice_notation}")
        return {
            "success": False,
            "message": _format_error("Roll system error - check logs")
        }

    # Extract result data
    total = result_data.get('total', 0)
    breakdown = result_data.get('breakdown', '')
    critical_success = result_data.get('critical_success', False)
    critical_failure = result_data.get('critical_failure', False)

    # Determine success if DC provided
    success_result = None
    if difficulty:
        success_result = total >= difficulty

    # Build result message
    result_msg = f"Rolled {dice_notation}: {breakdown}"

    if difficulty:
        if success_result:
            result_msg += f" (DC {difficulty}: SUCCESS ✓)"
        else:
            result_msg += f" (DC {difficulty}: FAILURE ✗)"

    if critical_success:
        result_msg += " 🎯 CRITICAL SUCCESS!"
    elif critical_failure:
        result_msg += " 💥 CRITICAL FAILURE!"

    logger.info(f"Dice roll via RNG module: {result_msg} - Reason: {reason}")

    return {
        "success": True,
        "message": result_msg,
        "data": {
            "total": total,
            "breakdown": breakdown,
            "difficulty": difficulty,
            "success": success_result,
            "skill": skill,
            "reason": reason,
            "critical_success": critical_success,
            "critical_failure": critical_failure
        }
    }


def _move_player_to_location(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Move the player to a new location using entity-based positioning."""
    location_name = tool_input["location_name"]
    region = tool_input.get("region")  # Legacy fallback

    position = engine.get_component(player_entity_id, 'Position')
    if not position:
        return {"success": False, "message": _format_error("Player has no Position component")}

    # Find location entity by name (entity-based positioning)
    locations = engine.query_entities(['Location'])
    location_entity = next((e for e in locations if e.name.lower() == location_name.lower()), None)

    if location_entity:
        # Entity-based positioning: set region to location entity ID
        engine.update_component(player_entity_id, 'Position', {
            'region': location_entity.id  # Entity reference!
        })
        logger.info(f"Moved player to location entity: {location_name} ({location_entity.id})")
        return {
            "success": True,
            "message": f"Moved to {location_name}",
            "data": {"location": location_name, "location_id": location_entity.id}
        }
    elif region:
        # Fallback: Use region string (legacy or for abstract regions)
        engine.update_component(player_entity_id, 'Position', {
            'region': region
        })
        logger.info(f"Moved player to region: {region}")
        return {
            "success": True,
            "message": f"Moved to {region}",
            "data": {"region": region}
        }
    else:
        # Location not found and no region specified
        nearby_locations = [loc.name for loc in locations[:5]]
        error_msg = f"Location '{location_name}' not found"
        if nearby_locations:
            error_msg += f". Available locations: {', '.join(nearby_locations)}"
        return {"success": False, "message": _format_error(error_msg)}


def _query_entities(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Query for entities in the game world."""
    entity_type = tool_input["entity_type"]
    name_pattern = tool_input.get("name_pattern", "").lower()
    location = tool_input.get("location")

    # Query entities by component type
    component_map = {
        "npc": "NPC",
        "location": "Location",
        "item": "Item",
        "player": "PlayerCharacter"
    }

    component_type = component_map.get(entity_type)
    if not component_type:
        return {"success": False, "message": _format_error(f"Unknown entity type: {entity_type}")}

    entities = engine.query_entities([component_type])
    results = []

    # Find location entity ID if location filter specified
    location_id = None
    if location:
        locations = engine.query_entities(['Location'])
        location_entity = next((e for e in locations if e.name.lower() == location.lower()), None)
        if location_entity:
            location_id = location_entity.id
        else:
            # Location not found - return empty results
            return {
                "success": True,
                "message": f"Found 0 {entity_type}(s) (location '{location}' not found)",
                "data": {"entities": []}
            }

    for entity in entities:
        if name_pattern and name_pattern not in entity.name.lower():
            continue

        if location_id:
            # Use entity-based positioning: check if region matches location entity ID
            pos = engine.get_component(entity.id, 'Position')
            if not pos or pos.data.get('region') != location_id:
                continue

        identity = engine.get_component(entity.id, 'Identity')
        results.append({
            "id": entity.id,
            "name": entity.name,
            "description": identity.data.get('description') if identity else None
        })

    # FALLBACK: If searching by name pattern and no results, search ALL entities by name
    # This helps find entities that exist but don't have the proper component (e.g., items without Item component)
    if name_pattern and len(results) == 0:
        logger.info(f"No {entity_type}s found with proper component, searching all entities by name pattern: '{name_pattern}'")
        all_entities = engine.get_all_entities()

        for entity in all_entities:
            if not entity.is_active():
                continue
            if name_pattern not in entity.name.lower():
                continue

            # Check location filter if specified
            if location_id:
                pos = engine.get_component(entity.id, 'Position')
                if not pos or pos.data.get('region') != location_id:
                    continue

            # Add to results with a warning flag
            identity = engine.get_component(entity.id, 'Identity')
            results.append({
                "id": entity.id,
                "name": entity.name,
                "description": identity.data.get('description') if identity else None,
                "warning": f"Entity found but missing {component_type} component"
            })

        if results:
            logger.warning(f"Found {len(results)} entities by name without proper {component_type} component: {[r['name'] for r in results]}")

    return {
        "success": True,
        "message": f"Found {len(results)} {entity_type}(s)",
        "data": {"entities": results}
    }


def _update_npc_disposition(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Update an NPC's disposition toward the player."""
    npc_name = tool_input["npc_name"]
    new_disposition = tool_input["new_disposition"]
    reason = tool_input["reason"]

    # Find the NPC
    npcs = engine.query_entities(['NPC'])
    npc = next((e for e in npcs if e.name.lower() == npc_name.lower()), None)

    if not npc:
        # Get player's current location to suggest nearby NPCs
        player_position = engine.get_component(player_entity_id, 'Position')
        player_region = player_position.data.get('region') if player_position else None

        # Find NPCs at the same location (nearby)
        nearby_npcs = []
        if player_region:
            for npc_entity in npcs:
                npc_pos = engine.get_component(npc_entity.id, 'Position')
                if npc_pos and npc_pos.data.get('region') == player_region:
                    nearby_npcs.append(npc_entity.name)

        error_msg = f"NPC '{npc_name}' not found"
        if nearby_npcs:
            error_msg += f". Nearby NPCs: {', '.join(nearby_npcs[:5])}"

        return {"success": False, "message": _format_error(error_msg)}

    # Update disposition
    engine.update_component(npc.id, 'NPC', {'disposition': new_disposition})

    logger.info(f"Updated {npc_name} disposition to {new_disposition}: {reason}")
    return {
        "success": True,
        "message": f"{npc_name} is now {new_disposition} (Reason: {reason})",
        "data": {"npc_id": npc.id, "disposition": new_disposition}
    }


def _give_item_to_player(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Give an item to the player."""
    item_name = tool_input["item_name"]
    quantity = tool_input.get("quantity", 1)

    # Find the item
    items = engine.query_entities(['Item'])
    item = next((e for e in items if e.name.lower() == item_name.lower()), None)

    if not item:
        # Get player's current location to check for nearby items
        player_position = engine.get_component(player_entity_id, 'Position')
        player_region = player_position.data.get('region') if player_position else None

        # Find items at the same location (nearby)
        nearby_items = []
        if player_region:
            for item_entity in items:
                item_pos = engine.get_component(item_entity.id, 'Position')
                if item_pos and item_pos.data.get('region') == player_region:
                    nearby_items.append(item_entity.name)

        error_msg = f"Item '{item_name}' not found"
        if nearby_items:
            error_msg += f". Did you mean: {', '.join(nearby_items[:5])}?"
        else:
            error_msg += " (create it first or check the name)"

        return {"success": False, "message": _format_error(error_msg)}

    # Use items module's ownership system (create 'owns' relationship)
    # First check if ownership relationship already exists
    owns_rels = engine.get_relationships(player_entity_id, rel_type='owns', direction='from')
    already_owns = any(rel.to_entity == item.id for rel in owns_rels)

    if not already_owns:
        # Create ownership relationship
        result = engine.create_relationship(
            from_id=player_entity_id,
            to_id=item.id,
            rel_type='owns'
        )
        if not result.success:
            return {"success": False, "message": _format_error(f"Failed to give item: {result.error}")}

    # Update quantity if specified
    if quantity > 1:
        engine.update_component(item.id, 'Item', {'quantity': quantity})

    logger.info(f"Gave {quantity}x {item_name} to player")
    return {
        "success": True,
        "message": f"Gave {quantity}x {item_name} to player",
        "data": {"item_id": item.id, "quantity": quantity}
    }


def _remove_item(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Remove an item from the player's inventory."""
    item_name = tool_input["item_name"]
    quantity = tool_input.get("quantity")
    reason = tool_input["reason"]

    # Find the item in player's inventory
    items = engine.query_entities(['Item'])
    item = next((e for e in items if e.name.lower() == item_name.lower()), None)

    if not item:
        return {"success": False, "message": _format_error(f"Item '{item_name}' not found")}

    # Check if player owns this item (using items module's ownership system)
    owns_rels = engine.get_relationships(player_entity_id, rel_type='owns', direction='from')
    owns_item = any(rel.to_entity == item.id for rel in owns_rels)

    if not owns_item:
        return {"success": False, "message": _format_error(f"'{item_name}' is not in your inventory")}

    # Get current quantity
    item_comp = engine.get_component(item.id, 'Item')
    current_quantity = item_comp.data.get('quantity', 1) if item_comp else 1

    # Determine how many to remove
    if quantity is None:
        quantity = current_quantity  # Remove all
    else:
        quantity = min(quantity, current_quantity)  # Can't remove more than we have

    if quantity >= current_quantity:
        # Remove entire item entity
        engine.delete_entity(item.id)
        logger.info(f"Removed all {current_quantity}x {item_name} from player ({reason})")
        return {
            "success": True,
            "message": f"Removed {item_name} ({reason})",
            "data": {"item_id": item.id, "quantity": current_quantity, "reason": reason}
        }
    else:
        # Reduce quantity
        new_quantity = current_quantity - quantity
        engine.update_component(item.id, 'Item', {'quantity': new_quantity})
        logger.info(f"Reduced {item_name} from {current_quantity} to {new_quantity} ({reason})")
        return {
            "success": True,
            "message": f"Removed {quantity}x {item_name} ({reason})",
            "data": {"item_id": item.id, "quantity": quantity, "remaining": new_quantity, "reason": reason}
        }


def _deal_damage(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Deal damage to the player."""
    amount = tool_input["amount"]
    damage_type = tool_input.get("damage_type", "untyped")
    source = tool_input["source"]

    # Get player's health component
    health = engine.get_component(player_entity_id, 'Health')
    if not health:
        return {"success": False, "message": "Player has no Health component"}

    current_hp = health.data.get('current', 0)
    max_hp = health.data.get('max', 1)
    new_hp = max(0, current_hp - amount)

    engine.update_component(player_entity_id, 'Health', {'current': new_hp})

    logger.info(f"Dealt {amount} {damage_type} damage to player from {source} ({new_hp}/{max_hp} HP)")
    return {
        "success": True,
        "message": f"Took {amount} {damage_type} damage from {source} ({new_hp}/{max_hp} HP remaining)",
        "data": {"damage": amount, "new_hp": new_hp, "max_hp": max_hp}
    }


def _heal_player(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Heal the player."""
    amount = tool_input["amount"]
    source = tool_input["source"]

    # Get player's health component
    health = engine.get_component(player_entity_id, 'Health')
    if not health:
        return {"success": False, "message": "Player has no Health component"}

    current_hp = health.data.get('current', 0)
    max_hp = health.data.get('max', 1)
    new_hp = min(max_hp, current_hp + amount)

    engine.update_component(player_entity_id, 'Health', {'current': new_hp})

    logger.info(f"Healed player {amount} HP from {source} ({new_hp}/{max_hp} HP)")
    return {
        "success": True,
        "message": f"Restored {amount} HP from {source} ({new_hp}/{max_hp} HP)",
        "data": {"healing": amount, "new_hp": new_hp, "max_hp": max_hp}
    }


def _long_rest(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Player takes a long rest - restore all resources."""
    location = tool_input["location"]

    recovery_log = []

    # Restore HP to max
    health = engine.get_component(player_entity_id, 'Health')
    if health:
        max_hp = health.data.get('max', 1)
        current_hp = health.data.get('current', 0)
        if current_hp < max_hp:
            engine.update_component(player_entity_id, 'Health', {'current': max_hp})
            hp_restored = max_hp - current_hp
            recovery_log.append(f"Restored {hp_restored} HP to maximum ({max_hp})")
            logger.info(f"Long rest: Restored HP to {max_hp}")

    # Restore spell slots to max
    magic = engine.get_component(player_entity_id, 'Magic')
    if magic:
        max_slots = magic.data.get('max_spell_slots', {})
        if max_slots:
            engine.update_component(player_entity_id, 'Magic', {
                'available_spell_slots': max_slots.copy()
            })
            total_slots = sum(max_slots.values())
            recovery_log.append(f"Recovered all {total_slots} spell slots")
            logger.info(f"Long rest: Restored {total_slots} spell slots")

    # Could also restore other daily resources here (rage uses, ki points, etc.)
    # For now, just HP and spell slots

    if not recovery_log:
        recovery_log.append("Rested peacefully")

    message = f"After a long rest at {location}: {', '.join(recovery_log)}"
    logger.info(f"Player long rest at {location}")

    return {
        "success": True,
        "message": message,
        "data": {"location": location, "recovery": recovery_log}
    }


def _get_entity_details(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Get complete details about an entity including all components."""
    entity_name = tool_input["entity_name"]
    entity_type = tool_input.get("entity_type")

    # Find the entity
    entities = []
    if entity_type:
        component_map = {"npc": "NPC", "location": "Location", "item": "Item", "player": "PlayerCharacter"}
        component = component_map.get(entity_type)
        if component:
            entities = engine.query_entities([component])
    else:
        # Search all entity types
        entities = engine.query_entities(['NPC']) + engine.query_entities(['Location']) + \
                   engine.query_entities(['Item']) + engine.query_entities(['PlayerCharacter'])

    entity = next((e for e in entities if e.name.lower() == entity_name.lower()), None)
    if not entity:
        return {"success": False, "message": _format_error(f"Entity '{entity_name}' not found")}

    # Get all components
    components = engine.get_entity_components(entity.id)
    component_summary = {}
    for comp_type, comp_data in components.items():
        component_summary[comp_type] = comp_data

    logger.info(f"Retrieved details for entity {entity_name} ({entity.id}): {len(components)} components")
    return {
        "success": True,
        "message": f"Found {entity_name} with {len(components)} components",
        "data": {
            "entity_id": entity.id,
            "name": entity.name,
            "components": component_summary
        }
    }


def _update_component(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Update a component on an entity."""
    entity_name = tool_input["entity_name"]
    component_type = tool_input["component_type"]
    updates = tool_input["updates"]
    reason = tool_input["reason"]

    # Find the entity (search all types)
    entities = engine.query_entities(['NPC']) + engine.query_entities(['Location']) + \
               engine.query_entities(['Item']) + engine.query_entities(['PlayerCharacter'])
    entity = next((e for e in entities if e.name.lower() == entity_name.lower()), None)

    if not entity:
        return {"success": False, "message": _format_error(f"Entity '{entity_name}' not found")}

    # Check if component exists
    component = engine.get_component(entity.id, component_type)
    if not component:
        return {"success": False, "message": _format_error(f"Entity '{entity_name}' does not have a {component_type} component")}

    # Update the component
    result = engine.update_component(entity.id, component_type, updates)
    if not result.success:
        logger.error(f"Failed to update {component_type} on {entity_name}: {result.error}")
        return {"success": False, "message": _format_error(f"Failed to update component: {result.error}")}

    logger.info(f"Updated {component_type} on {entity_name} ({entity.id}): {updates} - {reason}")
    return {
        "success": True,
        "message": f"Updated {entity_name}'s {component_type} component: {reason}",
        "data": {"entity_id": entity.id, "component_type": component_type, "updates": updates}
    }


def _add_component(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Add a component to an entity."""
    entity_name = tool_input["entity_name"]
    component_type = tool_input["component_type"]
    component_data = tool_input["component_data"]
    reason = tool_input["reason"]

    # Find the entity
    entities = engine.query_entities(['NPC']) + engine.query_entities(['Location']) + \
               engine.query_entities(['Item']) + engine.query_entities(['PlayerCharacter'])
    entity = next((e for e in entities if e.name.lower() == entity_name.lower()), None)

    if not entity:
        return {"success": False, "message": _format_error(f"Entity '{entity_name}' not found")}

    # Check if component already exists
    existing = engine.get_component(entity.id, component_type)
    if existing:
        return {"success": False, "message": _format_error(f"Entity '{entity_name}' already has a {component_type} component. Use update_component instead.")}

    # Add the component
    result = engine.add_component(entity.id, component_type, component_data)
    if not result.success:
        logger.error(f"Failed to add {component_type} to {entity_name}: {result.error}")
        return {"success": False, "message": _format_error(f"Failed to add component: {result.error}")}

    logger.info(f"Added {component_type} to {entity_name} ({entity.id}): {component_data} - {reason}")
    return {
        "success": True,
        "message": f"Added {component_type} component to {entity_name}: {reason}",
        "data": {"entity_id": entity.id, "component_type": component_type, "data": component_data}
    }


def _remove_component(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Remove a component from an entity."""
    entity_name = tool_input["entity_name"]
    component_type = tool_input["component_type"]
    reason = tool_input["reason"]

    # Find the entity
    entities = engine.query_entities(['NPC']) + engine.query_entities(['Location']) + \
               engine.query_entities(['Item']) + engine.query_entities(['PlayerCharacter'])
    entity = next((e for e in entities if e.name.lower() == entity_name.lower()), None)

    if not entity:
        return {"success": False, "message": _format_error(f"Entity '{entity_name}' not found")}

    # Check if component exists
    component = engine.get_component(entity.id, component_type)
    if not component:
        return {"success": False, "message": _format_error(f"Entity '{entity_name}' does not have a {component_type} component")}

    # Remove the component
    result = engine.remove_component(entity.id, component_type)
    if not result.success:
        logger.error(f"Failed to remove {component_type} from {entity_name}: {result.error}")
        return {"success": False, "message": _format_error(f"Failed to remove component: {result.error}")}

    logger.info(f"Removed {component_type} from {entity_name} ({entity.id}): {reason}")
    return {
        "success": True,
        "message": f"Removed {component_type} component from {entity_name}: {reason}",
        "data": {"entity_id": entity.id, "component_type": component_type}
    }


def _add_relationship(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Add a relationship between two entities."""
    from_entity_name = tool_input["from_entity_name"]
    to_entity_name = tool_input["to_entity_name"]
    relationship_type = tool_input["relationship_type"]
    relationship_data = tool_input.get("relationship_data", {})
    reason = tool_input["reason"]

    # Find both entities
    all_entities = engine.query_entities(['NPC']) + engine.query_entities(['Location']) + \
                   engine.query_entities(['Item']) + engine.query_entities(['PlayerCharacter'])

    from_entity = next((e for e in all_entities if e.name.lower() == from_entity_name.lower()), None)
    to_entity = next((e for e in all_entities if e.name.lower() == to_entity_name.lower()), None)

    if not from_entity:
        return {"success": False, "message": _format_error(f"Entity '{from_entity_name}' not found")}
    if not to_entity:
        return {"success": False, "message": _format_error(f"Entity '{to_entity_name}' not found")}

    # Add the relationship
    result = engine.add_relationship(from_entity.id, to_entity.id, relationship_type, relationship_data)
    if not result.success:
        logger.error(f"Failed to add relationship {relationship_type} from {from_entity_name} to {to_entity_name}: {result.error}")
        return {"success": False, "message": _format_error(f"Failed to add relationship: {result.error}")}

    logger.info(f"Added relationship {relationship_type}: {from_entity_name} -> {to_entity_name} ({reason})")
    return {
        "success": True,
        "message": _format_success(f"Created {relationship_type} relationship: {from_entity_name} → {to_entity_name} ({reason})"),
        "data": {
            "from_entity_id": from_entity.id,
            "to_entity_id": to_entity.id,
            "relationship_type": relationship_type
        }
    }


def _remove_relationship(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Remove a relationship between two entities."""
    from_entity_name = tool_input["from_entity_name"]
    to_entity_name = tool_input["to_entity_name"]
    relationship_type = tool_input["relationship_type"]
    reason = tool_input["reason"]

    # Find both entities
    all_entities = engine.query_entities(['NPC']) + engine.query_entities(['Location']) + \
                   engine.query_entities(['Item']) + engine.query_entities(['PlayerCharacter'])

    from_entity = next((e for e in all_entities if e.name.lower() == from_entity_name.lower()), None)
    to_entity = next((e for e in all_entities if e.name.lower() == to_entity_name.lower()), None)

    if not from_entity:
        return {"success": False, "message": _format_error(f"Entity '{from_entity_name}' not found")}
    if not to_entity:
        return {"success": False, "message": _format_error(f"Entity '{to_entity_name}' not found")}

    # Remove the relationship
    result = engine.remove_relationship(from_entity.id, to_entity.id, relationship_type)
    if not result.success:
        logger.error(f"Failed to remove relationship {relationship_type} from {from_entity_name} to {to_entity_name}: {result.error}")
        return {"success": False, "message": _format_error(f"Failed to remove relationship: {result.error}")}

    logger.info(f"Removed relationship {relationship_type}: {from_entity_name} -> {to_entity_name} ({reason})")
    return {
        "success": True,
        "message": _format_success(f"Removed {relationship_type} relationship: {from_entity_name} → {to_entity_name} ({reason})"),
        "data": {
            "from_entity_id": from_entity.id,
            "to_entity_id": to_entity.id,
            "relationship_type": relationship_type
        }
    }


def _query_relationships(engine, player_entity_id: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Query relationships for an entity."""
    entity_name = tool_input["entity_name"]
    relationship_type = tool_input.get("relationship_type")
    direction = tool_input.get("direction", "both")

    # Find the entity
    all_entities = engine.query_entities(['NPC']) + engine.query_entities(['Location']) + \
                   engine.query_entities(['Item']) + engine.query_entities(['PlayerCharacter'])
    entity = next((e for e in all_entities if e.name.lower() == entity_name.lower()), None)

    if not entity:
        return {"success": False, "message": _format_error(f"Entity '{entity_name}' not found")}

    relationships = []

    # Query outgoing relationships (from this entity)
    if direction in ["outgoing", "both"]:
        outgoing = engine.get_relationships_from(entity.id, relationship_type)
        for rel in outgoing:
            to_entity = engine.get_entity(rel.to_entity_id)
            if to_entity:
                relationships.append({
                    "direction": "outgoing",
                    "type": rel.relationship_type,
                    "target": to_entity.name,
                    "target_id": to_entity.id,
                    "data": rel.data
                })

    # Query incoming relationships (to this entity)
    if direction in ["incoming", "both"]:
        incoming = engine.get_relationships_to(entity.id, relationship_type)
        for rel in incoming:
            from_entity = engine.get_entity(rel.from_entity_id)
            if from_entity:
                relationships.append({
                    "direction": "incoming",
                    "type": rel.relationship_type,
                    "source": from_entity.name,
                    "source_id": from_entity.id,
                    "data": rel.data
                })

    logger.info(f"Queried relationships for {entity_name}: found {len(relationships)}")

    # Format for display
    if relationships:
        rel_summary = "\n".join([
            f"  • {r['type']} ({r['direction']}): {r.get('target', r.get('source'))}"
            for r in relationships
        ])
        message = f"Found {len(relationships)} relationship(s) for {entity_name}:\n{rel_summary}"
    else:
        message = f"No relationships found for {entity_name}"

    return {
        "success": True,
        "message": message,
        "data": {
            "entity_id": entity.id,
            "entity_name": entity_name,
            "relationships": relationships
        }
    }


# Initialize core tools on module load
def _initialize_core_tools():
    """Register all core DM tools."""
    core_handlers = {
        'create_npc': _create_npc,
        'create_location': _create_location,
        'create_item': _create_item,
        'roll_dice': _roll_dice,
        'move_player_to_location': _move_player_to_location,
        'query_entities': _query_entities,
        'update_npc_disposition': _update_npc_disposition,
        'give_item_to_player': _give_item_to_player,
        'remove_item': _remove_item,
        'deal_damage': _deal_damage,
        'heal_player': _heal_player,
        'long_rest': _long_rest,
        'get_entity_details': _get_entity_details,
        'update_component': _update_component,
        'add_component': _add_component,
        'remove_component': _remove_component,
        'add_relationship': _add_relationship,
        'remove_relationship': _remove_relationship,
        'query_relationships': _query_relationships
    }

    for tool_def in _CORE_TOOL_DEFINITIONS:
        tool_name = tool_def['name']
        handler = core_handlers.get(tool_name)
        if handler:
            register_tool(tool_def, handler)
        else:
            logger.warning(f"No handler found for core tool: {tool_name}")


# Initialize on import
_initialize_core_tools()


__all__ = ['execute_tool', 'register_tool', 'get_tool_definitions', 'get_tool_handler', 'generate_tool_documentation']
