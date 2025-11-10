"""
Entity Resolution for AI DM Tools.

Provides robust entity lookup that accepts both names and IDs,
with fuzzy matching and context-aware disambiguation.

This implements the architectural principle:
- IDs for backend (stable, unique, efficient)
- Names for presentation (human-readable, AI-friendly)
- This resolver bridges the gap between the two
"""

import logging
from typing import Optional, List
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Resolves entity references (names or IDs) to actual entities.

    Provides fuzzy matching, type filtering, and context-aware
    disambiguation to handle ambiguous references gracefully.

    Usage:
        resolver = EntityResolver(engine)
        entity = resolver.resolve('The Golden Tankard',
                                 expected_type='location',
                                 context_location=player_location)
    """

    def __init__(self, engine: 'StateEngine'):
        """
        Initialize resolver.

        Args:
            engine: StateEngine instance for querying entities
        """
        self.engine = engine

    def resolve(self,
                reference: str,
                expected_type: Optional[str] = None,
                context_location: Optional[str] = None,
                allow_fuzzy: bool = True) -> Optional['Entity']:
        """
        Resolve a name or ID to an entity.

        This is the main entry point for entity resolution. It tries multiple
        strategies in order of specificity:

        1. Exact ID match (fastest, most specific)
        2. Exact name match
        3. Fuzzy name match (if allow_fuzzy=True)

        Each step can be filtered by expected_type and context_location.

        Args:
            reference: Entity name or ID to resolve
            expected_type: Filter by entity type ('npc', 'location', 'item', 'player')
            context_location: Current location ID for disambiguation
            allow_fuzzy: Whether to use fuzzy matching if exact match fails

        Returns:
            Entity if found, None otherwise

        Examples:
            # Exact ID
            resolve('entity_abc123') → Entity

            # Exact name
            resolve('The Golden Tankard', expected_type='location') → Entity

            # Fuzzy match
            resolve('golden tankrd', expected_type='location') → Entity (typo fixed)

            # Context disambiguation (prefer nearby entity)
            resolve('Guard', context_location='entity_tavern') → Guard in tavern
        """
        if not reference:
            return None

        logger.debug(f"Resolving entity reference: '{reference}' "
                    f"(type={expected_type}, context={context_location})")

        # Strategy 1: Try exact ID match first (fast path)
        if reference.startswith('entity_'):
            entity = self.engine.get_entity(reference)
            if entity and entity.is_active():
                # Verify type if specified
                if expected_type and not self._has_type(entity, expected_type):
                    logger.debug(f"  ✗ ID match {entity.name} has wrong type")
                    return None
                logger.debug(f"  ✓ Resolved by ID to: {entity.name}")
                return entity
            logger.debug(f"  ✗ No active entity with ID {reference}")
            return None

        # Strategy 2: Try exact name match
        entity = self._find_by_exact_name(reference, expected_type)
        if entity:
            # If multiple matches, use context to disambiguate
            candidates = self._find_all_by_exact_name(reference, expected_type)
            if len(candidates) > 1 and context_location:
                local = self._filter_by_location(candidates, context_location)
                if local:
                    entity = local[0]
                    logger.debug(f"  ✓ Disambiguated by location to: {entity.name}")
                    return entity
            logger.debug(f"  ✓ Resolved by exact name to: {entity.name}")
            return entity

        # Strategy 3: Try fuzzy match if enabled
        if allow_fuzzy:
            entity = self._find_by_fuzzy_name(reference, expected_type,
                                             context_location)
            if entity:
                logger.debug(f"  ✓ Resolved by fuzzy match to: {entity.name}")
                return entity

        logger.debug(f"  ✗ Could not resolve '{reference}'")
        return None

    def resolve_multiple(self,
                        reference: str,
                        expected_type: Optional[str] = None,
                        context_location: Optional[str] = None) -> List['Entity']:
        """
        Resolve a reference to multiple entities (for disambiguation).

        Returns all entities matching the reference, ordered by relevance.
        Useful when you need to show the user multiple matches.

        Args:
            reference: Entity name or ID
            expected_type: Filter by type
            context_location: Prefer entities in this location

        Returns:
            List of matching entities, ordered by relevance
        """
        # Try exact name first
        candidates = self._find_all_by_exact_name(reference, expected_type)

        # If no exact matches, try fuzzy
        if not candidates:
            candidates = self._find_all_by_fuzzy_name(reference, expected_type)

        # Sort by location context (prefer nearby)
        if context_location:
            # Put entities in context location first
            local = []
            remote = []
            for entity in candidates:
                if self._is_in_location(entity, context_location):
                    local.append(entity)
                else:
                    remote.append(entity)
            candidates = local + remote

        return candidates

    # ========== Internal Helper Methods ==========

    def _has_type(self, entity: 'Entity', expected_type: str) -> bool:
        """Check if entity has the expected type."""
        type_to_component = {
            'npc': 'NPC',
            'player': 'PlayerCharacter',
            'location': 'Location',
            'item': 'Item'
        }
        component = type_to_component.get(expected_type)
        if not component:
            return True  # Unknown type, don't filter

        return self.engine.get_component(entity.id, component) is not None

    def _find_by_exact_name(self,
                           name: str,
                           expected_type: Optional[str] = None) -> Optional['Entity']:
        """Find first entity with exact name match."""
        candidates = self._find_all_by_exact_name(name, expected_type)
        return candidates[0] if candidates else None

    def _find_all_by_exact_name(self,
                               name: str,
                               expected_type: Optional[str] = None) -> List['Entity']:
        """
        Find all entities with exact name match (case-insensitive).

        Note: Uses query_entities() without component filter to ensure
        newly-created entities are visible within the same execution batch.
        Component-filtered queries may have caching issues.
        """
        all_entities = self.engine.query_entities()
        matches = []

        for entity in all_entities:
            if not entity.is_active():
                continue

            # Case-insensitive name comparison
            if entity.name.lower() == name.lower():
                # Filter by type if specified (check component manually)
                if expected_type and not self._has_type(entity, expected_type):
                    continue
                matches.append(entity)

        return matches

    def _find_by_fuzzy_name(self,
                           name: str,
                           expected_type: Optional[str] = None,
                           context_location: Optional[str] = None,
                           threshold: float = 0.6) -> Optional['Entity']:
        """Find entity using fuzzy name matching."""
        candidates = self._find_all_by_fuzzy_name(name, expected_type, threshold)

        if not candidates:
            return None

        # If multiple candidates, prefer those in context location
        if len(candidates) > 1 and context_location:
            local = self._filter_by_location(candidates, context_location)
            if local:
                return local[0]

        return candidates[0]

    def _find_all_by_fuzzy_name(self,
                               name: str,
                               expected_type: Optional[str] = None,
                               threshold: float = 0.6) -> List['Entity']:
        """Find all entities using fuzzy name matching, ranked by similarity."""
        all_entities = self.engine.query_entities()
        scored_matches = []

        for entity in all_entities:
            if not entity.is_active():
                continue

            # Filter by type first (efficiency)
            if expected_type and not self._has_type(entity, expected_type):
                continue

            # Calculate similarity ratio
            ratio = SequenceMatcher(None, name.lower(), entity.name.lower()).ratio()

            if ratio >= threshold:
                scored_matches.append((ratio, entity))

        # Sort by score descending (best matches first)
        scored_matches.sort(key=lambda x: x[0], reverse=True)

        return [entity for _, entity in scored_matches]

    def _filter_by_location(self,
                           entities: List['Entity'],
                           location_id: str) -> List['Entity']:
        """Filter entities to those in the specified location."""
        filtered = []

        for entity in entities:
            if self._is_in_location(entity, location_id):
                filtered.append(entity)

        return filtered

    def _is_in_location(self, entity: 'Entity', location_id: str) -> bool:
        """Check if entity is in the specified location."""
        position = self.engine.get_component(entity.id, 'Position')
        if not position:
            return False

        # Check if positioned at this location
        region = position.data.get('region')

        # Direct match
        if region == location_id:
            return True

        # If region is an entity, check if it's the location
        if region and region.startswith('entity_'):
            # The entity is positioned AT the region entity
            return region == location_id

        return False


__all__ = ['EntityResolver']
