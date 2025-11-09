"""
DM Tools Module

Provides core functionality for Dungeon Master operations:
- Turn and time management
- Scene control
- Narrative tools

This module serves as the foundation that both ai_dm and player_dm
modules build upon, providing a common interface for DM operations
regardless of whether the DM is AI or human.
"""

from typing import List
from ..base import Module
import logging

logger = logging.getLogger(__name__)


class DMToolsModule(Module):
    """
    DM Tools module for Arcane Arsenal.

    Provides the foundation for DM operations including turn management,
    scene control, and narrative tools. Combat modules register their
    turn handlers with this module.
    """

    name = "dm_tools"
    version = "1.0.0"
    description = "Core DM functionality and time management"
    author = "Arcane Arsenal"

    def dependencies(self) -> List[str]:
        """No dependencies - only needs core (implicit)."""
        return []

    def initialize(self, engine):
        """
        Initialize DM tools.

        Sets up the turn handler registry for combat modules.
        """
        self.engine = engine
        logger.info("DM Tools module initialized")
        logger.info("Turn handler registry ready for combat modules")

    def register_components(self) -> List:
        """
        DM Tools doesn't register components itself.

        It provides infrastructure that other modules use.
        """
        return []

    def register_blueprint(self):
        """No web endpoints - DM tools is infrastructure only."""
        return None


__all__ = ['DMToolsModule']
