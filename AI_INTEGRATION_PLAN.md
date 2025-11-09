# AI Integration Plan for Arcane Arsenal

## Overview
This document outlines the plan for integrating LLM-powered AI Dungeon Master functionality into Arcane Arsenal.

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│  AI DM Module (src/modules/ai_dm/)          │
│  - Flask routes (api.py)                    │
│  - Message handling                         │
│  - Action execution                         │
├─────────────────────────────────────────────┤
│  LLM Client Layer (NEW)                     │
│  - Provider abstraction (Anthropic/OpenAI)  │
│  - Prompt templates                         │
│  - Response parsing                         │
│  - Error handling & retries                 │
├─────────────────────────────────────────────┤
│  Context Generation (NEW)                   │
│  - StateEngine.generate_ai_context()        │
│  - Entity context builder                   │
│  - Conversation memory management           │
│  - Event history formatter                  │
├─────────────────────────────────────────────┤
│  Core Engine (existing)                     │
│  - State management                         │
│  - Event bus                                │
│  - Component queries                        │
└─────────────────────────────────────────────┘
```

## Phase 1: Infrastructure Completion (10/10)

### 1.1 Performance Optimization
**File:** `src/modules/base.py`
**Task:** Add caching to ModuleRegistry
- Cache registry data in memory dict
- O(1) lookups instead of O(n)
- Invalidate cache on register()

### 1.2 Configuration Management
**File:** `src/core/config.py` (NEW)
**Task:** Create centralized config system
- Environment variable loading with python-dotenv
- API key management
- Server configuration
- AI model settings

**File:** `.env.example` (NEW)
```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Server
HOST=0.0.0.0
PORT=5000
DEBUG=False

# Logging
LOG_LEVEL=INFO
LOG_FILE=arcane_arsenal.log

# AI Settings
AI_PROVIDER=anthropic  # anthropic or openai
AI_MODEL=claude-3-5-sonnet-20241022
AI_MAX_TOKENS=4096
AI_TEMPERATURE=0.7
AI_SYSTEM_PROMPT_PATH=prompts/dm_system.txt
```

### 1.3 Error Taxonomy
**File:** `src/core/result.py`
**Task:** Add error code enum
- Standard error types
- Better error handling in API responses

## Phase 2: Context Generation System

### 2.1 Core Context Builder
**File:** `src/core/ai_context.py` (NEW)

```python
class AIContextBuilder:
    """Builds structured context for AI from game state."""

    def __init__(self, engine: StateEngine):
        self.engine = engine

    def build_character_context(self, entity_id: str) -> Dict[str, Any]:
        """Build full context for a character entity."""

    def build_location_context(self, entity_id: str) -> Dict[str, Any]:
        """Build context for character's current location."""

    def build_inventory_context(self, entity_id: str) -> List[Dict]:
        """Build context for character's inventory."""

    def build_conversation_history(self, entity_id: str, limit: int = 10) -> List[Dict]:
        """Build recent conversation history."""

    def build_recent_events(self, entity_id: str, limit: int = 5) -> List[Dict]:
        """Build recent game events."""
```

### 2.2 StateEngine Integration
**File:** `src/core/state_engine.py`
**Task:** Add AI context methods

```python
class StateEngine:
    # ... existing methods ...

    def generate_ai_context(self, entity_id: str, include_history: bool = True) -> Dict[str, Any]:
        """
        Generate comprehensive AI context for an entity.

        Returns structured data including:
        - Character stats and abilities
        - Current location and nearby entities
        - Inventory and equipment
        - Recent conversation history
        - Recent game events
        """
        from .ai_context import AIContextBuilder
        builder = AIContextBuilder(self)

        context = {
            'character': builder.build_character_context(entity_id),
            'location': builder.build_location_context(entity_id),
            'inventory': builder.build_inventory_context(entity_id)
        }

        if include_history:
            context['conversation'] = builder.build_conversation_history(entity_id)
            context['recent_events'] = builder.build_recent_events(entity_id)

        return context
```

## Phase 3: LLM Client Abstraction

### 3.1 Provider Interface
**File:** `src/modules/ai_dm/llm_client.py` (NEW)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.core.config import Config

class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """Generate a response from the LLM."""
        pass

class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation."""

    def __init__(self, api_key: str):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)

    def generate_response(self, messages, system=None, **kwargs):
        response = self.client.messages.create(
            model=kwargs.get('model', 'claude-3-5-sonnet-20241022'),
            max_tokens=kwargs.get('max_tokens', 4096),
            temperature=kwargs.get('temperature', 0.7),
            system=system,
            messages=messages
        )
        return response.content[0].text

class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation."""

    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)

    def generate_response(self, messages, system=None, **kwargs):
        if system:
            messages = [{"role": "system", "content": system}] + messages

        response = self.client.chat.completions.create(
            model=kwargs.get('model', 'gpt-4-turbo-preview'),
            max_tokens=kwargs.get('max_tokens', 4096),
            temperature=kwargs.get('temperature', 0.7'),
            messages=messages
        )
        return response.choices[0].message.content

def get_llm_client(config: Config) -> LLMProvider:
    """Factory function to get configured LLM client."""
    provider = config.ai_provider if hasattr(config, 'ai_provider') else 'anthropic'

    if provider == 'anthropic':
        return AnthropicProvider(config.anthropic_api_key)
    elif provider == 'openai':
        return OpenAIProvider(config.openai_api_key)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")
```

### 3.2 Prompt Templates
**File:** `src/modules/ai_dm/prompts.py` (NEW)

```python
from typing import Dict, Any, List

SYSTEM_PROMPT = """You are an expert Dungeon Master for a fantasy tabletop RPG.

Your role is to:
- Create engaging, immersive narrative descriptions
- Present the player with meaningful choices
- Suggest 2-4 contextual actions the player can take
- Maintain consistency with the game world state
- Follow established fantasy RPG conventions

Guidelines:
- Keep responses concise (2-4 paragraphs max)
- Always suggest actions that match the situation
- Use vivid, evocative language
- Respect player agency - suggest, don't force
- Reference character abilities when relevant

Response Format:
Provide your response as narrative text, followed by a JSON block with suggested actions:

<narrative>
Your engaging story text here...
</narrative>

<actions>
[
  {
    "label": "🎲 Roll Perception",
    "action_type": "roll_dice",
    "action_data": {"dice": "1d20+3", "label": "Perception Check"}
  },
  ...
]
</actions>
"""

def build_context_prompt(ai_context: Dict[str, Any]) -> str:
    """Convert AI context dict into formatted prompt."""

    character = ai_context.get('character', {})
    location = ai_context.get('location', {})

    prompt_parts = []

    # Character info
    if character:
        prompt_parts.append("## Character")
        prompt_parts.append(f"Name: {character.get('name')}")
        prompt_parts.append(f"Class: {character.get('class', 'Unknown')}, Level {character.get('level', 1)}")

        if 'attributes' in character:
            attrs = character['attributes']
            prompt_parts.append(f"Attributes: STR {attrs.get('strength')}, DEX {attrs.get('dexterity')}, ...")

    # Location info
    if location:
        prompt_parts.append(f"\n## Current Location")
        prompt_parts.append(f"{location.get('description', 'Unknown location')}")

        if 'nearby_entities' in location:
            prompt_parts.append(f"Nearby: {', '.join(location['nearby_entities'])}")

    # Inventory
    inventory = ai_context.get('inventory', [])
    if inventory:
        prompt_parts.append(f"\n## Inventory")
        for item in inventory[:5]:  # Top 5 items
            prompt_parts.append(f"- {item.get('name')}")

    return "\n".join(prompt_parts)

def build_message_history(messages: List[Dict]) -> List[Dict[str, str]]:
    """Convert conversation messages to LLM format."""

    llm_messages = []

    for msg in messages[-10:]:  # Last 10 messages
        role = 'user' if msg.get('speaker') == 'player' else 'assistant'
        content = msg.get('message', '')

        llm_messages.append({
            'role': role,
            'content': content
        })

    return llm_messages
```

### 3.3 Response Parser
**File:** `src/modules/ai_dm/response_parser.py` (NEW)

```python
import re
import json
from typing import Dict, List, Tuple, Optional

def parse_dm_response(raw_response: str) -> Tuple[str, List[Dict]]:
    """
    Parse DM response into narrative text and suggested actions.

    Returns:
        (narrative_text, suggested_actions)
    """

    # Extract narrative
    narrative_match = re.search(r'<narrative>(.*?)</narrative>', raw_response, re.DOTALL)
    narrative = narrative_match.group(1).strip() if narrative_match else raw_response

    # Extract actions
    actions_match = re.search(r'<actions>(.*?)</actions>', raw_response, re.DOTALL)
    suggested_actions = []

    if actions_match:
        try:
            suggested_actions = json.loads(actions_match.group(1))
        except json.JSONDecodeError:
            # Fallback to default actions if parsing fails
            suggested_actions = get_fallback_actions()
    else:
        suggested_actions = get_fallback_actions()

    return narrative, suggested_actions

def get_fallback_actions() -> List[Dict]:
    """Default actions if LLM doesn't provide them."""
    return [
        {
            'label': '🔍 Look Around',
            'action_type': 'custom',
            'action_data': {'action': 'look'}
        },
        {
            'label': '💬 Talk',
            'action_type': 'custom',
            'action_data': {'action': 'talk'}
        }
    ]
```

## Phase 4: Integration

### 4.1 Update AI DM API
**File:** `src/modules/ai_dm/api.py`
**Task:** Replace placeholder with real AI

```python
@ai_dm_bp.route('/api/dm/message', methods=['POST'])
def api_send_message():
    # ... existing validation ...

    # NEW: Generate AI context
    ai_context = engine.generate_ai_context(entity_id)

    # NEW: Get conversation history
    conversation = engine.get_component(entity_id, 'Conversation')
    messages = get_conversation_messages(engine, conversation)

    # NEW: Call LLM
    from .llm_client import get_llm_client
    from .prompts import SYSTEM_PROMPT, build_context_prompt, build_message_history
    from .response_parser import parse_dm_response
    from src.core.config import Config

    config = Config()
    llm = get_llm_client(config)

    # Build prompts
    context_prompt = build_context_prompt(ai_context)
    llm_messages = build_message_history(messages)
    llm_messages.append({'role': 'user', 'content': message})

    # Add context as system message
    full_system = f"{SYSTEM_PROMPT}\n\n{context_prompt}"

    # Generate response
    try:
        raw_response = llm.generate_response(
            messages=llm_messages,
            system=full_system,
            max_tokens=config.ai_max_tokens,
            temperature=config.ai_temperature
        )

        dm_response_text, dm_suggested_actions = parse_dm_response(raw_response)

    except Exception as e:
        logger.error(f"LLM error: {e}", exc_info=True)
        dm_response_text = "The DM seems distracted... (AI error)"
        dm_suggested_actions = get_fallback_actions()

    # ... rest of existing code to save message ...
```

## Dependencies to Add

```txt
# Add to requirements.txt
anthropic>=0.25.0
openai>=1.12.0
python-dotenv>=1.0.0
```

## Testing Strategy

1. **Unit Tests**
   - Context builder functions
   - Prompt template generation
   - Response parsing

2. **Integration Tests**
   - Mock LLM responses
   - End-to-end message flow
   - Error handling paths

3. **Manual Testing**
   - Create test character
   - Send messages
   - Verify context accuracy
   - Check suggested actions

## Implementation Order

1. ✅ Fix infrastructure (Registry caching, Config, Errors)
2. 🔨 Context generation system
3. 🔨 LLM client abstraction
4. 🔨 Prompt templates
5. 🔨 Response parsing
6. 🔨 Integrate into api.py
7. 🧪 Testing
8. 📝 Documentation

## Timeline Estimate

- Infrastructure fixes: 30 min
- Context generation: 1-2 hours
- LLM client: 1 hour
- Prompts & parsing: 1 hour
- Integration: 1 hour
- Testing: 1-2 hours

**Total: 5-7 hours** for complete AI DM integration
