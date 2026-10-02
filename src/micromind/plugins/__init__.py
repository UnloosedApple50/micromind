"""
MicroMind Plugins Package
=========================

Optional plugin system.  The core never imports this package directly.
"""

from .manager import (
    Plugin,
    PluginManager,
    PluginMetadata,
    PluginState,
    PluginWrapper,
)

__all__ = [
    "Plugin",
    "PluginManager",
    "PluginMetadata",
    "PluginState",
    "PluginWrapper",
]
