"""
MicroMind GUI Package
=====================

Optional GUI adapters.  The core never imports this package directly.
"""

from .legacy import LegacyGUI, Menu, MenuItem, create_gui

__all__ = [
    "LegacyGUI",
    "Menu",
    "MenuItem",
    "create_gui",
]
