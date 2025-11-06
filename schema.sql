-- Arcane Arsenal Database Schema
-- Entity Component System for RPG State Management

-- ============================================================================
-- TYPE REGISTRIES
-- Modules must register component, relationship, and event types before use
-- ============================================================================

CREATE TABLE component_types (
    type TEXT PRIMARY KEY,
    description TEXT,
    schema_version TEXT NOT NULL,
    module TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE relationship_types (
    type TEXT PRIMARY KEY,
    description TEXT,
    module TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE event_types (
    type TEXT PRIMARY KEY,
    description TEXT,
    module TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE roll_types (
    type TEXT PRIMARY KEY,
    description TEXT,
    module TEXT,
    category TEXT,  -- For grouping: 'combat', 'skill', 'saving_throw', etc.
    created_at TIMESTAMP NOT NULL
);

-- ============================================================================
-- CORE DATA TABLES
-- ============================================================================

-- Entities: Minimal container with ID and name
-- All real data lives in components
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    deleted_by TEXT  -- Can be entity_id or 'system'
);

-- Components: All entity data
-- Each component is a typed JSON blob attached to an entity
CREATE TABLE components (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    component_type TEXT NOT NULL,
    data JSON NOT NULL,
    version INTEGER DEFAULT 1,  -- Increments on each update
    created_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (component_type) REFERENCES component_types(type)
);

-- Relationships: Explicit directed connections between entities
-- from_entity -> to_entity with a typed relationship
CREATE TABLE relationships (
    id TEXT PRIMARY KEY,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    FOREIGN KEY (from_entity) REFERENCES entities(id),
    FOREIGN KEY (to_entity) REFERENCES entities(id),
    FOREIGN KEY (relationship_type) REFERENCES relationship_types(type)
);

-- Events: Append-only audit log of all state changes
-- Provides complete history for debugging, undo, and network sync
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    event_type TEXT NOT NULL,
    entity_id TEXT,
    component_id TEXT,
    actor_id TEXT,  -- Who/what caused this event
    data JSON NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (event_type) REFERENCES event_types(type)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Entity indexes (filter active vs deleted)
CREATE INDEX idx_entities_active ON entities(name) WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_deleted ON entities(deleted_at) WHERE deleted_at IS NOT NULL;

-- Component indexes (most common queries)
CREATE INDEX idx_components_entity ON components(entity_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_components_type ON components(component_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_components_entity_type ON components(entity_id, component_type) WHERE deleted_at IS NULL;

-- Relationship indexes (bidirectional queries)
CREATE INDEX idx_relationships_from ON relationships(from_entity, relationship_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_to ON relationships(to_entity, relationship_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_type ON relationships(relationship_type) WHERE deleted_at IS NULL;

-- Event indexes (temporal and entity-based queries)
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_entity ON events(entity_id);
CREATE INDEX idx_events_actor ON events(actor_id);
CREATE INDEX idx_events_type ON events(event_type);

-- ============================================================================
-- FULL-TEXT SEARCH
-- For AI natural language queries across component data
-- ============================================================================

CREATE VIRTUAL TABLE components_fts USING fts5(
    id UNINDEXED,
    entity_id UNINDEXED,
    component_type UNINDEXED,
    data
);

-- Triggers to keep FTS table synchronized with components table

CREATE TRIGGER components_fts_insert AFTER INSERT ON components BEGIN
    INSERT INTO components_fts(rowid, id, entity_id, component_type, data)
    VALUES (new.rowid, new.id, new.entity_id, new.component_type, new.data);
END;

CREATE TRIGGER components_fts_delete AFTER DELETE ON components BEGIN
    DELETE FROM components_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER components_fts_update AFTER UPDATE ON components BEGIN
    DELETE FROM components_fts WHERE rowid = old.rowid;
    INSERT INTO components_fts(rowid, id, entity_id, component_type, data)
    VALUES (new.rowid, new.id, new.entity_id, new.component_type, new.data);
END;

-- ============================================================================
-- SCHEMA VERSION
-- Track schema migrations
-- ============================================================================

CREATE TABLE schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL
);

INSERT INTO schema_version (version, applied_at) VALUES ('1.0.0', CURRENT_TIMESTAMP);
