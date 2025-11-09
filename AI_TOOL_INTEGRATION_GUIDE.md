# AI Tool Integration - Completion Guide

This document explains how to complete the streaming integration with AI tools.

## What's Already Done ✅

1. **Tool System** (`src/modules/ai_dm/tools.py`)
   - 10 comprehensive tools defined
   - Modular registry system (modules can add custom tools)
   - `execute_tool()` function that runs tool handlers
   - All core tools registered on module import

2. **LLM Client Updates** (`src/modules/ai_dm/llm_client.py`)
   - `AnthropicProvider.generate_response_stream()` now yields dicts
   - Handles tool use events from Claude API
   - Returns `{'type': 'text'}` or `{'type': 'tool_use_start'}` etc.

3. **Bug Fixes** (`src/modules/ai_dm/prompts.py`)
   - `build_message_history()` accepts `player_message` parameter

## What Needs Implementation 🚧

### 1. Update Streaming Endpoint (`src/modules/ai_dm/api.py`)

The `/api/dm/message_stream` endpoint needs major changes to handle the tool use loop:

**Current Flow:**
```
Player message → AI streams text → Done
```

**New Flow:**
```
Player message
  ↓
AI thinks (streams text)
  ↓
AI calls tool (e.g., create_npc)
  ↓
Tool executes (create NPC entity)
  ↓
Tool result fed back to AI
  ↓
AI continues thinking with result
  ↓
AI streams final response
  ↓
Done
```

**Implementation Steps:**

```python
from src.modules.ai_dm.tools import get_tool_definitions, execute_tool

@ai_dm_bp.route('/api/dm/message_stream', methods=['POST'])
def send_dm_message_stream():
    import json
    from flask import Response, stream_with_context

    def generate():
        # ... existing setup code ...

        # Get tool definitions
        tools = get_tool_definitions()

        # Convert tools to Anthropic format
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            })

        # Stream with tools
        full_response = ""
        tool_uses = []  # Track tool calls
        current_tool = None
        tool_input_json = ""

        for chunk in llm.generate_response_stream(
            messages=llm_messages,
            system=full_system_prompt,
            max_tokens=config.ai_max_tokens,
            temperature=config.ai_temperature,
            tools=anthropic_tools  # Pass tools to LLM!
        ):
            if chunk['type'] == 'text':
                # Stream text to user
                full_response += chunk['content']
                yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"

            elif chunk['type'] == 'tool_use_start':
                # AI wants to use a tool
                current_tool = {
                    'id': chunk['tool_use_id'],
                    'name': chunk['tool_name'],
                    'input': ''
                }
                tool_input_json = ""

                # Notify frontend
                yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': chunk['tool_name']})}\n\n"

            elif chunk['type'] == 'tool_input_delta':
                # Accumulate tool input JSON
                tool_input_json += chunk['partial_json']

        # After stream ends, execute any tool calls
        if tool_input_json:
            try:
                tool_input = json.loads(tool_input_json)

                # Execute the tool
                result = execute_tool(
                    current_tool['name'],
                    tool_input,
                    engine,
                    entity_id
                )

                # Notify frontend
                yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': current_tool['name'], 'result': result})}\n\n"

                # If AI used tools, we need to continue the conversation
                # Add tool result to message history and call AI again
                if result['success']:
                    # This would require another streaming loop
                    # For now, we'll just include the result in the response
                    full_response += f"\n\n[Tool: {current_tool['name']} - {result['message']}]"

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool input: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': 'Tool input parsing failed'})}\n\n"

        # Parse final response and send done event
        narrative, suggested_actions = parse_dm_response(full_response)

        # ... existing message saving code ...

        yield f"data: {json.dumps({'type': 'done', 'message_id': dm_msg_id, 'suggested_actions': suggested_actions})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
```

**Note:** The above is simplified. For full multi-turn tool use, you need to:
1. Detect when stream ends with tool use
2. Add tool results as new messages
3. Call LLM again with updated history
4. Continue streaming the follow-up response

### 2. Update Frontend (`src/modules/ai_dm/templates/dm_chat.html`)

The frontend needs to handle new event types:

```javascript
function sendDMMessage() {
    // ... existing code ...

    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6));

            if (data.type === 'token') {
                // Existing text streaming code
            }
            else if (data.type === 'tool_start') {
                // Show tool execution indicator
                const toolDiv = document.createElement('div');
                toolDiv.className = 'tool-execution';
                toolDiv.innerHTML = `🔧 Using tool: ${data.tool_name}...`;
                messagesDiv.appendChild(toolDiv);
            }
            else if (data.type === 'tool_result') {
                // Show tool result
                const resultDiv = document.createElement('div');
                resultDiv.className = 'tool-result';
                resultDiv.innerHTML = `✓ ${data.result.message}`;
                messagesDiv.appendChild(resultDiv);
            }
            else if (data.type === 'done') {
                // Existing done handling
            }
        }
    }
}
```

### 3. Update System Prompt (`src/modules/ai_dm/prompts/dm_system.txt`)

Add a section teaching the AI about tools:

```markdown
## Available Tools

You have access to powerful tools that let you interact with the game world:

**Entity Creation:**
- `create_npc`: When an NPC first appears, create them as a real entity with personality
- `create_location`: When entering a new area, create it as a trackable location
- `create_item`: When describing items, create them so players can interact with them

**Game State:**
- `query_entities`: Check if an NPC/location/item already exists before creating duplicates
- `move_player_to_location`: When the player travels, update their location
- `roll_dice`: When actions have uncertain outcomes, roll dice (e.g., "1d20+5" against DC 15)

**NPC Interaction:**
- `update_npc_disposition`: Change how NPCs feel based on player actions

**Inventory:**
- `give_item_to_player`: Add items to their inventory when found/purchased/gifted

**Combat/Health:**
- `deal_damage`: Apply damage from attacks, traps, hazards
- `heal_player`: Restore HP from potions, spells, rest

**When to Use Tools:**

1. **Create entities for important things:**
   - NPCs the player talks to → create_npc
   - New locations they enter → create_location
   - Items they might take → create_item

2. **Query before creating:**
   - Use query_entities to check if "Innkeeper Tom" already exists
   - Prevents duplicate NPCs with same name

3. **Roll for uncertainty:**
   - Player searches room → roll_dice with Perception
   - Player sneaks past guards → roll_dice with Stealth
   - Include DC (difficulty) so I know if they succeed

4. **Track consequences:**
   - Player angers the duke → update_npc_disposition to 'hostile'
   - Player defeats bandits → give_item_to_player for loot
   - Player falls from cliff → deal_damage

**Example:**

Player: "I want to talk to the innkeeper"

You think:
1. Does the innkeeper exist? → query_entities for "innkeeper"
2. No results → create_npc: "Tom the Innkeeper", friendly, in tavern
3. Now describe the interaction naturally

Response: "The portly innkeeper wipes down the bar as you approach..."

**Remember:**
- Use tools BEFORE narrating the outcome
- Tools create the real game world - use them liberally
- Dice rolls happen automatically - you see the result
- Keep narration natural - don't mention "I'm creating an NPC"
```

### 4. Add Tool Execution Feedback

In `src/modules/ai_dm/tools.py`, enhance logging:

```python
def execute_tool(tool_name: str, tool_input: Dict[str, Any], engine, player_entity_id: str) -> Dict[str, Any]:
    logger.info(f"🔧 AI using tool: {tool_name}")
    logger.debug(f"   Input: {tool_input}")

    result = # ... execute tool ...

    if result['success']:
        logger.info(f"✓ Tool {tool_name} succeeded: {result['message']}")
    else:
        logger.warning(f"✗ Tool {tool_name} failed: {result['message']}")

    return result
```

## Testing

1. **Test basic streaming** (should already work):
   ```
   You: "Hello"
   AI: "Greetings, traveler!" (streams in)
   ```

2. **Test tool use**:
   ```
   You: "I enter a tavern"
   AI: [creates location] "You push open the heavy oak door..."
   ```

3. **Test NPC creation**:
   ```
   You: "I talk to the bartender"
   AI: [queries for bartender] [creates NPC] "The grizzled bartender looks up..."
   ```

4. **Test dice rolls**:
   ```
   You: "I search the room"
   AI: [rolls 1d20+2 Perception vs DC 12] "You notice a loose floorboard..."
   ```

## Module Extension Example

Any module can add custom tools:

```python
# src/modules/magic/spell_tools.py
from src.modules.ai_dm.tools import register_tool

def cast_spell_handler(engine, player_id, tool_input):
    spell_name = tool_input['spell_name']
    target = tool_input.get('target')

    # Get player's spell component
    magic = engine.get_component(player_id, 'Magic')
    if not magic:
        return {'success': False, 'message': 'You cannot cast spells'}

    # Check if spell is known
    known_spells = magic.data.get('known_spells', [])
    if spell_name not in known_spells:
        return {'success': False, 'message': f'You do not know {spell_name}'}

    # Deduct spell slot, apply effects, etc.
    # ...

    return {
        'success': True,
        'message': f'Cast {spell_name}!',
        'data': {'spell': spell_name, 'target': target}
    }

# Register the tool
register_tool({
    'name': 'cast_spell',
    'description': 'Cast a magical spell from your spell list',
    'input_schema': {
        'type': 'object',
        'properties': {
            'spell_name': {
                'type': 'string',
                'description': 'Name of the spell to cast (e.g., "Fireball", "Cure Wounds")'
            },
            'target': {
                'type': 'string',
                'description': 'Target of the spell (optional)'
            }
        },
        'required': ['spell_name']
    }
}, cast_spell_handler)
```

Then just import it in your module's `__init__.py` and it will be available to the AI!

## Summary

The tool system is fully built and modular. What remains is:
1. Updating the streaming endpoint to handle tool events
2. Updating frontend to show tool execution
3. Adding tool instructions to system prompt

This will make the AI DM truly integrated with your game world!
