"""
MicroMind Plugin Manager
========================

Manages the lifecycle of MicroMind plugins: discovery, loading, activation,
and unloading.  Each plugin is described by metadata (name, version,
permissions, compatibility, entrypoint) and runs in an isolated context so
that a crash in one plugin does not bring down the core.

Design principles:
  * Core does NOT depend on LLM, Internet, GUI, heavy database, cloud, or GPU.
  * Plugins are optional extensions; the core is fully functional without them.
  * Plugin crashes are contained – a failing plugin is disabled, not fatal.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
import traceback
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plugin metadata
# ---------------------------------------------------------------------------


class PluginState(str, Enum):
    """Lifecycle states for a plugin."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    CRASHED = "crashed"


@dataclass(frozen=True)
class PluginMetadata:
    """
    Immutable metadata describing a plugin.

    Attributes
    ----------
    name:
        Unique plugin identifier (e.g. ``"speech_recognition"``).
    version:
        Semver version string (e.g. ``"1.2.0"``).
    permissions:
        List of permission strings the plugin requires (e.g.
        ``["filesystem.read", "network.http"]``).
    compatibility:
        List of MicroMind core versions this plugin is compatible with
        (e.g. ``[">=1.0.0,<2.0.0"]``).
    entrypoint:
        Dotted path to the plugin's entry function or class
        (e.g. ``"my_plugin:activate"``).
    description:
        Human-readable description of the plugin.
    author:
        Plugin author name or organisation.
    """

    name: str
    version: str
    permissions: List[str] = field(default_factory=list)
    compatibility: List[str] = field(default_factory=list)
    entrypoint: str = ""
    description: str = ""
    author: str = ""


# ---------------------------------------------------------------------------
# Plugin protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Plugin(Protocol):
    """Protocol that all plugins must satisfy."""

    def activate(self) -> None:
        """Called when the plugin is activated."""
        ...

    def deactivate(self) -> None:
        """Called when the plugin is deactivated."""
        ...


# ---------------------------------------------------------------------------
# Plugin wrapper (crash isolation)
# ---------------------------------------------------------------------------


@dataclass
class PluginWrapper:
    """
    Wraps a loaded plugin with its metadata and runtime state.

    All public methods delegate to the underlying plugin inside a
    try/except block so that exceptions are caught and the plugin is
    marked as ``CRASHED`` rather than propagating to the core.
    """

    metadata: PluginMetadata
    instance: Optional[Plugin] = None
    state: PluginState = PluginState.DISCOVERED
    error: Optional[str] = None

    def activate(self) -> bool:
        """
        Activate the wrapped plugin.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if the plugin crashed.
        """
        if self.instance is None:
            self.state = PluginState.CRASHED
            self.error = "Plugin instance is None"
            return False
        try:
            self.instance.activate()
            self.state = PluginState.ACTIVE
            self.error = None
            return True
        except Exception as exc:
            self.state = PluginState.CRASHED
            self.error = f"{type(exc).__name__}: {exc}"
            logger.error(
                "Plugin %s crashed during activate: %s",
                self.metadata.name,
                self.error,
            )
            return False

    def deactivate(self) -> bool:
        """
        Deactivate the wrapped plugin.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if the plugin crashed.
        """
        if self.instance is None:
            return True
        try:
            self.instance.deactivate()
            self.state = PluginState.DISABLED
            self.error = None
            return True
        except Exception as exc:
            self.state = PluginState.CRASHED
            self.error = f"{type(exc).__name__}: {exc}"
            logger.error(
                "Plugin %s crashed during deactivate: %s",
                self.metadata.name,
                self.error,
            )
            return False


# ---------------------------------------------------------------------------
# Plugin manager
# ---------------------------------------------------------------------------


class PluginManager:
    """
    Discovers, loads, activates, and unloads plugins.

    Parameters
    ----------
    plugin_dirs:
        Directories to search for plugin modules.
    auto_activate:
        If ``True`` (default), plugins are activated immediately after
        successful loading.
    """

    def __init__(
        self,
        plugin_dirs: Optional[List[Path]] = None,
        auto_activate: bool = True,
    ) -> None:
        self._plugin_dirs: List[Path] = list(plugin_dirs or [])
        self._auto_activate: bool = auto_activate
        self._plugins: Dict[str, PluginWrapper] = {}

    # -- discovery ---------------------------------------------------------

    def discover(self) -> List[PluginMetadata]:
        """
        Scan plugin directories and return metadata for all discovered plugins.

        Discovery looks for Python files containing a ``METADATA`` attribute
        of type :class:`PluginMetadata`.
        """
        discovered: List[PluginMetadata] = []
        for directory in self._plugin_dirs:
            if not directory.is_dir():
                continue
            for py_file in directory.glob("*.py"):
                try:
                    metadata = self._extract_metadata(py_file)
                    if metadata is not None:
                        discovered.append(metadata)
                except Exception as exc:
                    logger.warning(
                        "Failed to extract metadata from %s: %s", py_file, exc
                    )
        return discovered

    def _extract_metadata(self, py_file: Path) -> Optional[PluginMetadata]:
        """Extract :class:`PluginMetadata` from a Python file."""
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        metadata = getattr(module, "METADATA", None)
        if isinstance(metadata, PluginMetadata):
            return metadata
        return None

    # -- loading -----------------------------------------------------------

    def load(self, metadata: PluginMetadata) -> bool:
        """
        Load a plugin described by *metadata*.

        Returns
        -------
        bool
            ``True`` if the plugin was loaded (and optionally activated)
            successfully.
        """
        if metadata.name in self._plugins:
            logger.warning("Plugin %s is already loaded", metadata.name)
            return False

        wrapper = PluginWrapper(metadata=metadata)
        try:
            instance = self._load_entrypoint(metadata.entrypoint)
            wrapper.instance = instance
            wrapper.state = PluginState.LOADED
            self._plugins[metadata.name] = wrapper

            if self._auto_activate:
                return wrapper.activate()
            return True
        except Exception as exc:
            wrapper.state = PluginState.CRASHED
            wrapper.error = f"{type(exc).__name__}: {exc}"
            logger.error(
                "Failed to load plugin %s: %s\n%s",
                metadata.name,
                wrapper.error,
                traceback.format_exc(),
            )
            return False

    def _load_entrypoint(self, entrypoint: str) -> Plugin:
        """Load and return the plugin instance from *entrypoint*."""
        if not entrypoint:
            raise ValueError("Plugin entrypoint is empty")
        module_path, _, attr_name = entrypoint.partition(":")
        if not module_path or not attr_name:
            raise ValueError(
                f"Invalid entrypoint format: {entrypoint!r} (expected 'module:attr')"
            )
        module = importlib.import_module(module_path)
        factory: Callable[[], Plugin] = getattr(module, attr_name)
        return factory()

    # -- unloading ---------------------------------------------------------

    def unload(self, name: str) -> bool:
        """
        Unload the plugin identified by *name*.

        Returns
        -------
        bool
            ``True`` if the plugin was found and deactivated successfully.
        """
        wrapper = self._plugins.get(name)
        if wrapper is None:
            logger.warning("Plugin %s is not loaded", name)
            return False
        success = wrapper.deactivate()
        if success:
            del self._plugins[name]
        return success

    def unload_all(self) -> None:
        """Unload all active plugins."""
        for name in list(self._plugins.keys()):
            self.unload(name)

    # -- queries -----------------------------------------------------------

    def get(self, name: str) -> Optional[PluginWrapper]:
        """Return the :class:`PluginWrapper` for *name*, or ``None``."""
        return self._plugins.get(name)

    def list_plugins(self) -> List[PluginWrapper]:
        """Return a list of all loaded plugin wrappers."""
        return list(self._plugins.values())

    def list_active(self) -> List[PluginWrapper]:
        """Return a list of all active plugin wrappers."""
        return [w for w in self._plugins.values() if w.state == PluginState.ACTIVE]

    # -- context manager ---------------------------------------------------

    def __enter__(self) -> "PluginManager":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.unload_all()
