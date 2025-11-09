"""
Prompt Templates and Formatting for AI DM.

Handles conversion of game state context into LLM-ready prompts
and conversation history formatting.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Default system prompt path
DEFAULT_SYSTEM_PROMPT_PATH = Path(__file__).parent / 'prompts' / 'dm_system.txt'


def load_system_prompt(prompt_path: str = None) -> str:
    """
    Load system prompt from file.

    Args:
        prompt_path: Path to prompt file (uses default if not provided)

    Returns:
        System prompt text

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    if prompt_path is None:
        prompt_path = DEFAULT_SYSTEM_PROMPT_PATH
    else:
        prompt_path = Path(prompt_path)

    if not prompt_path.exists():
        logger.error(f"System prompt not found at: {prompt_path}")
        raise FileNotFoundError(f"System prompt file not found: {prompt_path}")

    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()

    logger.info(f"Loaded system prompt from {prompt_path} ({len(prompt)} characters)")
    return prompt


def build_context_prompt(ai_context: Dict[str, Any]) -> str:
    """
    Convert AI context dict into formatted prompt section.

    Takes the output of engine.generate_ai_context() and formats it
    into a human-readable prompt that provides game state information.

    Args:
        ai_context: Context dict from AIContextBuilder

    Returns:
        Formatted context prompt

    Example:
        >>> context = engine.generate_ai_context('entity_123')
        >>> prompt = build_context_prompt(context)
        >>> print(prompt)
        ## Character: Theron
        Class: Wizard, Level 5
        Race: Human, Alignment: Neutral Good
        ...
    """
    prompt_parts = []

    # === Character Info ===
    character = ai_context.get('character', {})
    if character:
        prompt_parts.append("## Character Information")
        prompt_parts.append(f"**Name:** {character.get('name', 'Unknown')}")

        if 'description' in character:
            prompt_parts.append(f"**Description:** {character['description']}")

        # Class and Level
        char_class = character.get('class', 'unknown').title()
        level = character.get('level', 1)
        prompt_parts.append(f"**Class:** {char_class}, Level {level}")

        # Race and Alignment
        race = character.get('race', 'unknown').title()
        alignment = character.get('alignment', 'unknown').replace('_', ' ').title()
        prompt_parts.append(f"**Race:** {race}, **Alignment:** {alignment}")

        # Attributes
        if 'attributes' in character:
            attrs = character['attributes']
            mods = character.get('modifiers', {})
            attr_line = []
            for attr in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                score = attrs.get(attr, 10)
                mod = mods.get(attr, 0)
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
                attr_line.append(f"{attr[:3].upper()} {score} ({mod_str})")
            prompt_parts.append(f"**Attributes:** {' | '.join(attr_line)}")

        # HP
        if 'hp' in character:
            hp = character['hp']
            current = hp.get('current', 0)
            max_hp = hp.get('max', 0)
            hp_percent = (current / max_hp * 100) if max_hp > 0 else 0
            status = "healthy" if hp_percent > 75 else "wounded" if hp_percent > 25 else "critical"
            prompt_parts.append(f"**HP:** {current}/{max_hp} ({status})")

        # Skills
        if 'skills' in character:
            skills = character['skills']
            prof_bonus = skills.get('proficiency_bonus', 2)
            proficient = skills.get('proficient_skills', [])
            if proficient:
                prompt_parts.append(f"**Proficient Skills (+{prof_bonus}):** {', '.join(proficient)}")

        # Magic
        if 'magic' in character:
            magic = character['magic']
            spell_ability = magic.get('spellcasting_ability', 'intelligence').upper()
            slots = magic.get('available_spell_slots', {})
            if slots:
                slot_str = ', '.join([f"Level {lvl}: {count}" for lvl, count in slots.items()])
                prompt_parts.append(f"**Spellcasting ({spell_ability}):** {slot_str} slots available")
                prompt_parts.append(f"**Known Spells:** {magic.get('known_spells_count', 0)}, "
                                  f"**Prepared:** {magic.get('prepared_spells_count', 0)}, "
                                  f"**Cantrips:** {magic.get('cantrips_count', 0)}")

        prompt_parts.append("")  # Blank line

    # === Location ===
    location = ai_context.get('location', {})
    if location:
        prompt_parts.append("## Current Location")
        region = location.get('region', 'Unknown')
        prompt_parts.append(f"**Region:** {region}")

        # Nearby entities - show full details so AI knows what exists
        nearby = location.get('nearby_entities', [])
        if nearby:
            npcs = [e for e in nearby if e.get('type') == 'npc']
            players = [e for e in nearby if e.get('type') == 'player']
            items = [e for e in nearby if e.get('type') == 'item']

            if npcs:
                prompt_parts.append(f"**Nearby NPCs ({len(npcs)}):**")
                for npc in npcs:
                    desc_parts = [f"  • **{npc['name']}**"]
                    if npc.get('race'):
                        desc_parts.append(f"({npc['race']}")
                        if npc.get('occupation'):
                            desc_parts[-1] += f" {npc['occupation']}"
                        desc_parts[-1] += ")"
                    elif npc.get('occupation'):
                        desc_parts.append(f"({npc['occupation']})")
                    if npc.get('description'):
                        desc_parts.append(f"- {npc['description']}")
                    prompt_parts.append(' '.join(desc_parts))

            if players:
                player_list = ', '.join([p['name'] for p in players])
                prompt_parts.append(f"**Other Players:** {player_list}")

            if items:
                prompt_parts.append(f"**Nearby Items ({len(items)}):**")
                for item in items:
                    desc = f"  • **{item['name']}**"
                    if item.get('description'):
                        desc += f" - {item['description']}"
                    prompt_parts.append(desc)

        prompt_parts.append("")  # Blank line

    # === Inventory ===
    inventory = ai_context.get('inventory', [])
    if inventory:
        prompt_parts.append("## Inventory")

        # Calculate total gold/wealth
        total_gold = 0
        for item in inventory:
            value = item.get('value', 0)
            quantity = item.get('quantity', 1)
            if item.get('type') == 'currency' or 'gold' in item.get('name', '').lower():
                total_gold += value * quantity
            else:
                # Count item value as sellable wealth
                pass

        # Show gold prominently
        if total_gold > 0:
            prompt_parts.append(f"**💰 Gold:** {total_gold} gp")
        else:
            prompt_parts.append(f"**💰 Gold:** 0 gp (no money!)")

        equipped = [item for item in inventory if item.get('equipped')]
        carried = [item for item in inventory if not item.get('equipped')]

        if equipped:
            equipped_items = []
            for item in equipped:
                name = item['name']
                value = item.get('value', 0)
                qty = item.get('quantity', 1)
                if qty > 1:
                    equipped_items.append(f"{name} x{qty} ({value}gp ea)")
                elif value > 0:
                    equipped_items.append(f"{name} ({value}gp)")
                else:
                    equipped_items.append(name)
            prompt_parts.append(f"**Equipped:** {', '.join(equipped_items)}")

        if carried:
            carried_items = []
            for item in carried[:10]:  # Show top 10
                name = item['name']
                value = item.get('value', 0)
                qty = item.get('quantity', 1)
                item_type = item.get('type', 'misc')

                # Skip currency items (already counted in gold)
                if item_type == 'currency' or 'gold' in name.lower():
                    continue

                if qty > 1:
                    carried_items.append(f"{name} x{qty} ({value}gp ea)")
                elif value > 0:
                    carried_items.append(f"{name} ({value}gp)")
                else:
                    carried_items.append(name)

            more = len(carried) - 10
            if carried_items:
                carried_str = ', '.join(carried_items)
                if more > 0:
                    carried_str += f", and {more} more items"
                prompt_parts.append(f"**Carried:** {carried_str}")

        prompt_parts.append("")  # Blank line

    # === Recent Events ===
    recent_events = ai_context.get('recent_events', [])
    if recent_events and len(recent_events) > 0:
        prompt_parts.append("## Recent Events")
        for event in recent_events[-3:]:  # Last 3 events
            summary = event.get('summary', 'Unknown event')
            prompt_parts.append(f"- {summary}")
        prompt_parts.append("")  # Blank line

    # === Game System (Registries) ===
    game_system = ai_context.get('game_system', {})
    if game_system:
        prompt_parts.append("## Game System")
        prompt_parts.append("Available options in this game world:")
        prompt_parts.append("")

        for registry_name, items in game_system.items():
            if items:
                # Format registry name nicely (e.g., "skill_types" -> "Skill Types")
                display_name = registry_name.replace('_', ' ').title()
                prompt_parts.append(f"**{display_name}:**")

                # Show items in a compact list
                item_list = ', '.join([f"{item['key']}" for item in items])
                prompt_parts.append(f"  {item_list}")
                prompt_parts.append("")  # Blank line between registries

    return "\n".join(prompt_parts)


def build_message_history(messages: List[Dict], limit: int = 10, player_message: str = None) -> List[Dict[str, str]]:
    """
    Convert conversation messages to LLM format.

    Formats message history from database into the format expected
    by LLM APIs (role + content).

    Args:
        messages: List of message dicts from conversation history
        limit: Maximum number of messages to include (default: 10)
        player_message: Optional current player message to append

    Returns:
        List of formatted messages for LLM

    Example:
        >>> messages = context['conversation']
        >>> llm_messages = build_message_history(messages, player_message="I search the room")
        >>> print(llm_messages)
        [
            {'role': 'assistant', 'content': 'You find a hidden door...'},
            {'role': 'user', 'content': 'I search the room'}
        ]
    """
    llm_messages = []

    for msg in messages[-limit:]:  # Last N messages
        # Map speaker to LLM role
        speaker = msg.get('speaker', 'unknown')
        if speaker == 'player':
            role = 'user'
        elif speaker == 'dm':
            role = 'assistant'
        else:
            # System messages are skipped (or could be included as user)
            continue

        content = msg.get('message', '')
        if content:
            llm_messages.append({
                'role': role,
                'content': content
            })

    # Add current player message if provided
    if player_message:
        llm_messages.append({
            'role': 'user',
            'content': player_message
        })

    logger.debug(f"Built {len(llm_messages)} messages for LLM context")
    return llm_messages


def build_full_prompt(
    ai_context: Dict[str, Any],
    system_prompt: str = None,
    include_tool_docs: bool = True
) -> str:
    """
    Build complete system prompt with context.

    Combines the DM system prompt with current game state context and
    dynamically generated tool documentation.

    Args:
        ai_context: Context from engine.generate_ai_context()
        system_prompt: System prompt text (loads from file if not provided)
        include_tool_docs: Whether to include dynamic tool documentation (default: True)

    Returns:
        Complete system prompt with context

    Example:
        >>> context = engine.generate_ai_context(entity_id)
        >>> full_prompt = build_full_prompt(context)
        >>> # Use with LLM
        >>> response = llm.generate_response(
        ...     messages=conversation,
        ...     system=full_prompt
        ... )
    """
    if system_prompt is None:
        system_prompt = load_system_prompt()

    context_prompt = build_context_prompt(ai_context)

    # Build prompt sections
    prompt_sections = [system_prompt]

    # Add dynamic tool documentation if requested
    if include_tool_docs:
        try:
            from .tools import generate_tool_documentation
            tool_docs = generate_tool_documentation()
            prompt_sections.append(f"---\n\n{tool_docs}")
        except ImportError:
            logger.warning("Could not import tool documentation generator")

    # Add current game state
    prompt_sections.append(f"---\n\n# Current Game State\n\n{context_prompt}")

    full_prompt = "\n\n".join(prompt_sections)

    logger.debug(f"Built full prompt: {len(full_prompt)} characters")
    return full_prompt


__all__ = [
    'load_system_prompt',
    'build_context_prompt',
    'build_message_history',
    'build_full_prompt'
]
