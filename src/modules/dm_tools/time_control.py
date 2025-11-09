"""
Time and turn management for DM tools.

Provides an interface for combat modules to register turn handlers,
allowing different combat systems to implement their own timing mechanics.
"""

from typing import Protocol, Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class TurnHandler(Protocol):
    """
    Interface for modules to handle turn advancement.

    Combat modules implement this protocol to provide their own
    turn mechanics (initiative, simultaneous actions, etc.).
    """

    def can_handle(self, engine, scene_id: str) -> bool:
        """
        Check if this handler manages time for this scene.

        Args:
            engine: StateEngine instance
            scene_id: Entity ID of the scene/encounter

        Returns:
            True if this handler should manage turn advancement
        """
        ...

    def advance_turn(self, engine, scene_id: str) -> Dict[str, Any]:
        """
        Advance one turn/round.

        Args:
            engine: StateEngine instance
            scene_id: Entity ID of the scene/encounter

        Returns:
            Dict with information about what happened:
            {
                'actor_id': str,      # Who's acting now
                'round': int,         # Current round number
                'system': str,        # Combat system name
                'ended': bool         # Whether combat ended
            }
        """
        ...

    def get_current_actor(self, engine, scene_id: str) -> Optional[str]:
        """
        Get entity ID of who's acting right now.

        Args:
            engine: StateEngine instance
            scene_id: Entity ID of the scene/encounter

        Returns:
            Entity ID of current actor, or None
        """
        ...

    def end_sequence(self, engine, scene_id: str):
        """
        End combat/encounter and clean up.

        Args:
            engine: StateEngine instance
            scene_id: Entity ID of the scene/encounter
        """
        ...


# Global registry of turn handlers
_turn_handlers: List[TurnHandler] = []


def register_turn_handler(handler: TurnHandler):
    """
    Register a turn handler for a combat system.

    Combat modules call this during initialization to register
    their turn management implementation.

    Args:
        handler: TurnHandler implementation
    """
    _turn_handlers.append(handler)
    logger.info(f"Registered turn handler: {handler.__class__.__name__}")


def advance_time(engine, scene_id: str) -> Dict[str, Any]:
    """
    Advance time in the game.

    DM interface to move time forward. Delegates to registered
    combat handlers if combat is active, otherwise advances narrative time.

    Args:
        engine: StateEngine instance
        scene_id: Entity ID of the current scene/encounter

    Returns:
        Dict with information about what happened
    """
    # Check each registered handler
    for handler in _turn_handlers:
        if handler.can_handle(engine, scene_id):
            logger.debug(f"Delegating to {handler.__class__.__name__}")
            return handler.advance_turn(engine, scene_id)

    # No combat active - advance narrative time
    return advance_narrative(engine, scene_id)


def get_current_actor(engine, scene_id: str) -> Optional[str]:
    """
    Get who's currently acting.

    Args:
        engine: StateEngine instance
        scene_id: Entity ID of the current scene

    Returns:
        Entity ID of current actor, or None if narrative mode
    """
    for handler in _turn_handlers:
        if handler.can_handle(engine, scene_id):
            return handler.get_current_actor(engine, scene_id)

    return None


def advance_narrative(engine, scene_id: str) -> Dict[str, Any]:
    """
    Advance narrative time (non-combat).

    Default time advancement when no combat system is active.
    Just progresses the story forward.

    Args:
        engine: StateEngine instance
        scene_id: Entity ID of current scene

    Returns:
        Dict with narrative advancement info
    """
    logger.debug("Advancing narrative time")
    return {
        'mode': 'narrative',
        'message': 'Time passes...'
    }


def clear_handlers():
    """Clear all registered turn handlers. Useful for testing."""
    global _turn_handlers
    _turn_handlers = []
