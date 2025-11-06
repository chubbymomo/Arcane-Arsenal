# Web Editing Guide - Arcane Arsenal

## Overview

The Arcane Arsenal web interface now supports full CRUD operations! You can create, edit, and delete entities, components, and relationships directly from your browser.

## Getting Started

Start the web server:
```bash
python src/web/server.py worlds/my_world
```

Open your browser to: `http://localhost:5000`

## Features

### 1. Create Entities

From the **Entities** page:
1. Click **"+ Create Entity"** button
2. Enter entity name
3. Click **"Create"**
4. You'll be redirected to the new entity's detail page

### 2. Add Components

On any entity detail page:
1. Click **"+ Add Component"** under the Components section
2. Select a component type from the dropdown
3. Enter component data as JSON
4. See helpful examples for Identity and Position components
5. Click **"Add Component"**

**Example - Identity Component:**
```json
{
  "description": "A brave warrior"
}
```

**Example - Position Component (Absolute):**
```json
{
  "x": 100,
  "y": 200,
  "z": 0,
  "region": "overworld"
}
```

**Example - Position Component (Hierarchical):**
```json
{
  "x": 5,
  "y": 3,
  "z": 0,
  "region": "entity_abc123xyz"
}
```

When the `region` field is an entity ID (starts with "entity_"), the position is relative to that parent entity. This enables hierarchical positioning like tables in rooms, items on tables, etc.

### 3. Edit Components

For each component:
1. Click the **"Edit"** button next to the component
2. Modify the JSON data
3. Click **"Save"** or **"Cancel"**

Component data is validated using JSON Schema, so you'll get clear error messages if the data doesn't match the schema.

### 4. Delete Components

For each component:
1. Click the **"Delete"** button
2. Confirm the deletion
3. The component is removed immediately

### 5. Create Relationships

On any entity detail page:
1. Click **"+ Add Relationship"** under the Relationships section
2. Select the target entity from the dropdown
3. Select the relationship type (e.g., `located_at`, `contains`)
4. Optionally add metadata as JSON
5. Click **"Create Relationship"**

**Example Metadata:**
```json
{
  "since": "2024-01-15",
  "trust_level": 8
}
```

### 6. Delete Relationships

For outgoing relationships:
1. Click the **"Delete"** button next to the relationship
2. Confirm the deletion

Note: You can only delete outgoing relationships (where this entity is the source).

### 7. Delete Entities

On any entity detail page:
1. Click the **"Delete Entity"** button in the top right
2. Confirm the deletion
3. You'll be redirected to the entities list

Deleted entities are soft-deleted and can be restored via the CLI if needed.

## Flash Messages

Every action provides immediate feedback:
- **Green success messages** - Operation completed successfully
- **Red error messages** - Something went wrong (with details)

Messages can be dismissed by clicking the × button.

## Keyboard & Navigation

- Forms open/close with smooth animations
- All forms have Cancel buttons to close without saving
- Confirmation dialogs prevent accidental deletions
- Breadcrumb navigation at the top of each page

## Tips

1. **JSON Validation** - Component data must be valid JSON. Use an online JSON validator if you're unsure.

2. **Component Schemas** - Each component type has its own schema:
   - **Identity**: Requires `description` (string)
   - **Position**: All fields optional: `x`, `y`, `z` (numbers), `region` (string)

3. **Relationship Types** - Currently available:
   - **located_at**: Entity is physically at a location
   - **contains**: Container holds another entity

4. **Event Tracking** - All changes are logged as events. Check the Events page to see the complete audit trail.

5. **Soft Deletes** - Deleted entities/components/relationships are marked as deleted but not removed from the database. Use the CLI to restore if needed.

## Error Handling

Common errors and solutions:

**"Invalid JSON"** 
- Check for missing quotes, commas, or brackets
- Use `{"key": "value"}` format, not `{key: value}`

**"Component type X not registered"**
- Only use registered component types: Identity, Position
- Check the Types page to see available types

**"Validation failed"**
- Your data doesn't match the component schema
- For Identity: Must include `description` field
- Check the error message for specific field issues

**"Entity not found"**
- The entity may have been deleted
- Refresh the page to see current state

## Advanced Usage

### Creating Complex Worlds

1. **Create Location Entities**
   ```
   Tavern → Identity + Position
   Forest → Identity + Position  
   Cave → Identity + Position
   ```

2. **Create Character Entities**
   ```
   Hero → Identity + Position
   Villain → Identity + Position
   NPC → Identity + Position
   ```

3. **Create Item Entities**
   ```
   Sword → Identity
   Potion → Identity
   Key → Identity
   ```

4. **Link with Relationships**
   ```
   Hero → located_at → Tavern
   Tavern → contains → Sword
   Hero → contains → Key
   ```

### Hierarchical Positioning for Map Rendering

Position components support hierarchical positioning, perfect for rendering maps with nested spaces.

**Example: Building a Tavern Scene**

1. **Create the Tavern** (absolute position)
   ```json
   Position: {
     "x": 100,
     "y": 200,
     "z": 0,
     "region": "overworld"
   }
   ```

2. **Create a Table** (position relative to tavern)

   First, copy the tavern's entity ID (e.g., `entity_abc123xyz`), then:
   ```json
   Position: {
     "x": 5,
     "y": 3,
     "z": 0,
     "region": "entity_abc123xyz"
   }
   ```

   The table is now 5 units right and 3 units forward from the tavern's origin.

3. **Create a Mug** (position relative to table)

   Copy the table's entity ID, then:
   ```json
   Position: {
     "x": 0.5,
     "y": 0.5,
     "z": 1.2,
     "region": "entity_table_id"
   }
   ```

   The mug sits on the table surface at height 1.2 units.

**How It Works:**
- When `region` is a named area (like "overworld"), position is absolute
- When `region` is an entity ID, position is relative to that parent
- The system automatically calculates world positions for map rendering
- Use the CLI/API to call `engine.get_world_position(entity_id)` to get absolute coordinates

**Use Cases:**
- **World → Building → Room → Furniture → Item**
- **Map → Region → Location → Container → Object**
- **Character → Inventory → Backpack → Pouch → Item**

### Organizing by Components

Entity type is determined by which components it has, not by tags. This prevents AI hallucination through inconsistent categorization.

Query entities by component presence:
```python
# Find all characters (entities with CharacterStats - Phase 2)
characters = engine.query_entities(['CharacterStats'])

# Find all positioned entities
positioned = engine.query_entities(['Position'])

# Find all entities with both Identity and Position
described_and_positioned = engine.query_entities(['Identity', 'Position'])

# Get all entities in a region
entities_in_tavern = engine.get_entities_in_region('entity_tavern_id')

# Calculate world position for rendering
tavern_pos = engine.get_world_position(tavern_id)  # (100, 200, 0)
table_pos = engine.get_world_position(table_id)    # (105, 203, 0)
mug_pos = engine.get_world_position(mug_id)        # (105.5, 203.5, 1.2)
```

In Phase 2, specific component types will be added (CharacterStats, LocationProperties, etc.) to further refine entity types through composition.

## Next Steps

After building your world in the web interface:
- Use the **Events** page to review the complete history
- Use the **CLI** for bulk operations or scripting
- Access via **JSON API** for programmatic integration

## Troubleshooting

**Forms not appearing?**
- Make sure JavaScript is enabled
- Try refreshing the page
- Check browser console for errors

**Changes not saving?**
- Check for validation errors in flash messages
- Ensure you're connected to the database
- Verify world.db file permissions

**Page looks broken?**
- Clear browser cache
- Ensure style.css is loading (check Network tab)
- Try a different browser

## Feedback

This is a powerful interface for managing complex game state. All operations are:
- ✅ Validated against schemas
- ✅ Logged as events  
- ✅ Confirmed before destructive actions
- ✅ Backed by the full Arcane Arsenal engine

Happy world building! 🎮✨
