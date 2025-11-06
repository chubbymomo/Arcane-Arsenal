"""
Module loader for Arcane Arsenal.

Discovers and loads modules from the src/modules directory or world configuration.
Supports both automatic discovery and explicit configuration with dependency resolution.
"""

import importlib
import inspect
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
import json
import logging

from ..modules.base import Module

logger = logging.getLogger(__name__)


class ModuleDependencyError(Exception):
    """Raised when module dependencies cannot be satisfied."""
    pass


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
            modules = self._load_modules_with_dependencies(module_names)

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

    def _load_modules_with_dependencies(self, module_names: List[str]) -> List[Module]:
        """
        Load modules with dependency resolution.

        Performs topological sort to ensure dependencies are loaded first.
        Validates that all dependencies are available.

        Args:
            module_names: List of module names to load

        Returns:
            List of Module instances in dependency order

        Raises:
            ModuleDependencyError: If dependencies cannot be satisfied
        """
        # Import all requested modules
        modules_by_name = {}
        for name in module_names:
            module = self._import_module(name)
            if module:
                modules_by_name[name] = module

        # Build dependency graph and validate
        all_modules = {}
        visited = set()

        def collect_dependencies(module: Module):
            """Recursively collect module and its dependencies."""
            if module.name in visited:
                return
            visited.add(module.name)

            # Collect dependencies
            for dep_name in module.dependencies():
                if dep_name not in modules_by_name:
                    # Try to import dependency
                    dep_module = self._import_module(dep_name)
                    if not dep_module:
                        raise ModuleDependencyError(
                            f"Module '{module.name}' requires '{dep_name}' but it could not be loaded"
                        )
                    modules_by_name[dep_name] = dep_module

                # Recursively collect dependency's dependencies
                collect_dependencies(modules_by_name[dep_name])

            all_modules[module.name] = module

        # Collect all modules and dependencies
        for module in modules_by_name.values():
            collect_dependencies(module)

        # Topological sort
        sorted_modules = self._topological_sort(all_modules)

        for module in sorted_modules:
            logger.info(f"Loaded module: {module.name} v{module.version}")

        return sorted_modules

    def _topological_sort(self, modules: Dict[str, Module]) -> List[Module]:
        """
        Sort modules by dependencies using topological sort.

        Args:
            modules: Dict mapping module name to Module instance

        Returns:
            List of modules in dependency order (dependencies first)

        Raises:
            ModuleDependencyError: If circular dependencies detected
        """
        sorted_modules = []
        visited = set()
        temp_mark = set()

        def visit(module: Module):
            if module.name in temp_mark:
                raise ModuleDependencyError(
                    f"Circular dependency detected involving module '{module.name}'"
                )

            if module.name not in visited:
                temp_mark.add(module.name)

                # Visit dependencies first
                for dep_name in module.dependencies():
                    if dep_name in modules:
                        visit(modules[dep_name])

                temp_mark.remove(module.name)
                visited.add(module.name)
                sorted_modules.append(module)

        for module in modules.values():
            if module.name not in visited:
                visit(module)

        return sorted_modules

    def discover_available_modules(self) -> List[Dict[str, Any]]:
        """
        Discover all available modules without loading them.

        Returns:
            List of dicts with module metadata:
            {
                'name': 'core_components',
                'display_name': 'Core Components',
                'version': '1.0.0',
                'description': '...',
                'is_core': True,
                'dependencies': []
            }
        """
        modules_dir = Path(__file__).parent.parent / 'modules'

        if not modules_dir.exists():
            return []

        available = []

        for item in sorted(modules_dir.iterdir()):
            if item.name.startswith('_') or not item.is_dir():
                continue

            module = self._import_module(item.name)
            if module:
                available.append({
                    'name': module.name,
                    'display_name': module.display_name,
                    'version': module.version,
                    'description': module.description,
                    'is_core': module.is_core,
                    'dependencies': module.dependencies()
                })

        return available

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
