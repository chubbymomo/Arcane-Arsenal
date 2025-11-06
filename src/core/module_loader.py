"""
Module loader for Arcane Arsenal.

Discovers and loads modules from the src/modules directory or world configuration.
Supports both automatic discovery and explicit configuration.
"""

import importlib
import inspect
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import logging

from ..modules.base import Module

logger = logging.getLogger(__name__)


class ModuleLoader:
    """
    Discovers and loads modules for Arcane Arsenal.

    Supports multiple loading strategies:
    1. Auto-discovery: Scan src/modules/ directory
    2. Configuration: Load from world config file
    3. Manual: Explicitly provided module list
    """

    def __init__(self, world_path: Optional[str] = None):
        """
        Initialize module loader.

        Args:
            world_path: Path to world directory (for config-based loading)
        """
        self.world_path = world_path
        self.loaded_modules: List[Module] = []

    def load_modules(self, strategy: str = 'auto') -> List[Module]:
        """
        Load modules using specified strategy.

        Args:
            strategy: 'auto' (discover), 'config' (from world config), or 'core_only'

        Returns:
            List of loaded Module instances
        """
        if strategy == 'core_only':
            return self._load_core_only()
        elif strategy == 'config' and self.world_path:
            return self._load_from_config()
        elif strategy == 'auto':
            return self._load_with_discovery()
        else:
            logger.warning(f"Unknown strategy '{strategy}', falling back to core_only")
            return self._load_core_only()

    def _load_core_only(self) -> List[Module]:
        """Load only the core components module (safe default)."""
        from ..modules.core_components import CoreComponentsModule
        modules = [CoreComponentsModule()]
        logger.info("Loaded core_components module only")
        return modules

    def _load_from_config(self) -> List[Module]:
        """
        Load modules specified in world configuration.

        Reads world_path/config.json for module list.
        Falls back to core_only if config not found.

        Config format:
        {
            "modules": ["core_components", "elder_scrolls", "dnd_5e"]
        }
        """
        config_path = Path(self.world_path) / 'config.json'

        if not config_path.exists():
            logger.info("No config.json found, loading core only")
            return self._load_core_only()

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            module_names = config.get('modules', ['core_components'])
            modules = []

            for name in module_names:
                module = self._import_module(name)
                if module:
                    modules.append(module)
                    logger.info(f"Loaded module: {name} v{module.version}")

            return modules if modules else self._load_core_only()

        except Exception as e:
            logger.error(f"Error loading config: {e}, falling back to core only")
            return self._load_core_only()

    def _load_with_discovery(self) -> List[Module]:
        """
        Auto-discover modules in src/modules/ directory.

        Scans for directories containing Module subclasses.
        Always loads core_components first, then others alphabetically.
        """
        from ..modules.core_components import CoreComponentsModule

        modules = [CoreComponentsModule()]
        logger.info("Loaded core_components module")

        # Find modules directory
        modules_dir = Path(__file__).parent.parent / 'modules'

        if not modules_dir.exists():
            logger.warning("Modules directory not found")
            return modules

        # Scan for module directories
        for item in sorted(modules_dir.iterdir()):
            # Skip core (already loaded), private dirs, and non-directories
            if item.name == 'core_components' or item.name.startswith('_') or not item.is_dir():
                continue

            module = self._import_module(item.name)
            if module:
                modules.append(module)
                logger.info(f"Discovered and loaded module: {item.name} v{module.version}")

        return modules

    def _import_module(self, module_name: str) -> Optional[Module]:
        """
        Import a module by name and return its Module instance.

        Args:
            module_name: Name of module directory (e.g., 'elder_scrolls')

        Returns:
            Module instance if found, None otherwise
        """
        try:
            # Import the module package
            mod = importlib.import_module(f'..modules.{module_name}', __package__)

            # Find Module subclass
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                # Check if it's a class, subclass of Module, and not Module itself
                if (inspect.isclass(attr) and
                    issubclass(attr, Module) and
                    attr != Module):
                    return attr()

            logger.warning(f"Module '{module_name}' has no Module subclass")
            return None

        except ImportError as e:
            logger.warning(f"Failed to import module '{module_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading module '{module_name}': {e}")
            return None

    def get_module_info(self) -> List[Dict[str, Any]]:
        """
        Get information about loaded modules.

        Returns:
            List of dicts with module metadata
        """
        return [
            {
                'name': mod.name,
                'version': mod.version,
                'component_types': len(mod.register_component_types()),
                'relationship_types': len(mod.register_relationship_types())
            }
            for mod in self.loaded_modules
        ]
