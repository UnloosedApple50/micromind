"""
MicroMind Legacy GUI Adapter
============================

A lightweight, low-resource GUI adapter that provides a simple text-based
interface with keyboard support.  It is designed for environments where a
full graphical toolkit is unavailable or undesirable (headless servers,
embedded systems, low-power devices).

Features:
  * Low resource usage – no heavy animations or rendering.
  * Simple interface – text menus and prompts.
  * Keyboard support – arrow-key navigation and shortcut keys.
  * Headless mode – automatically falls back to a non-interactive mode when
    no GUI terminal is available.

Design principles:
  * Core does NOT depend on LLM, Internet, GUI, heavy database, cloud, or GPU.
  * This module is optional; the core never imports it directly.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class MenuItem:
    """A single menu entry."""

    key: str
    label: str
    action: Optional[Callable[[], None]] = None
    shortcut: Optional[str] = None


@dataclass
class Menu:
    """A titled menu containing one or more :class:`MenuItem` entries."""

    title: str
    items: List[MenuItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Legacy GUI adapter
# ---------------------------------------------------------------------------


class LegacyGUI:
    """
    Lightweight GUI adapter with keyboard support and headless fallback.

    Parameters
    ----------
    headless:
        Force headless mode (no interactive prompts).  When ``None`` the
        adapter auto-detects whether ``stdin`` is a TTY.
    input_func:
        Callable used to read user input.  Defaults to :func:`input`.
        Injectable for testing.
    output_func:
        Callable used to write output.  Defaults to ``print``.
        Injectable for testing.
    """

    def __init__(
        self,
        headless: Optional[bool] = None,
        input_func: Optional[Callable[[str], str]] = None,
        output_func: Optional[Callable[[str], None]] = None,
    ) -> None:
        if headless is None:
            headless = not sys.stdin.isatty()
        self._headless: bool = headless
        self._input: Callable[[str], str] = input_func or input
        self._output: Callable[[str], None] = output_func or print
        self._running: bool = False

    # -- public API --------------------------------------------------------

    @property
    def headless(self) -> bool:
        """Whether the adapter is running in headless (non-interactive) mode."""
        return self._headless

    def display_menu(self, menu: Menu) -> Optional[str]:
        """
        Display *menu* and return the selected item's key.

        In headless mode the menu is printed but no input is read; the
        method returns ``None`` immediately.
        """
        self._output(f"\n=== {menu.title} ===")
        for item in menu.items:
            shortcut_hint = f" [{item.shortcut}]" if item.shortcut else ""
            self._output(f"  {item.key}) {item.label}{shortcut_hint}")

        if self._headless:
            self._output("(headless mode – no input)")
            return None

        valid_keys = {item.key for item in menu.items}
        while True:
            try:
                choice = self._input("Select: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return None
            if choice in valid_keys:
                return choice
            self._output(f"Invalid choice.  Valid options: {', '.join(sorted(valid_keys))}")

    def run_menu(self, menu: Menu) -> None:
        """
        Display *menu* and execute the selected item's action.

        In headless mode this method is a no-op.
        """
        key = self.display_menu(menu)
        if key is None:
            return
        for item in menu.items:
            if item.key == key:
                if item.action is not None:
                    item.action()
                return

    def prompt(self, text: str, default: Optional[str] = None) -> Optional[str]:
        """
        Prompt the user for a line of text.

        Returns *default* when running in headless mode.
        """
        if self._headless:
            return default
        suffix = f" [{default}]" if default is not None else ""
        try:
            value = self._input(f"{text}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            return default
        return value if value else default

    def confirm(self, text: str, default: bool = False) -> bool:
        """
        Ask the user a yes/no question.

        Returns *default* when running in headless mode.
        """
        if self._headless:
            return default
        suffix = " [Y/n]" if default else " [y/N]"
        try:
            value = self._input(f"{text}{suffix}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return default
        if not value:
            return default
        return value in ("y", "yes")

    def display_text(self, text: str) -> None:
        """Display a block of text to the user."""
        self._output(text)

    def clear_screen(self) -> None:
        """Clear the terminal screen (best-effort, no-op in headless mode)."""
        if not self._headless:
            os.system("cls" if os.name == "nt" else "clear")

    def run_interactive(self, main_menu: Menu) -> None:
        """
        Run an interactive menu loop until the user quits.

        In headless mode this method returns immediately.
        """
        if self._headless:
            return
        self._running = True
        while self._running:
            key = self.display_menu(main_menu)
            if key is None:
                break
            for item in main_menu.items:
                if item.key == key:
                    if item.action is not None:
                        item.action()
                    break

    def stop(self) -> None:
        """Signal the interactive loop to stop."""
        self._running = False


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def create_gui(headless: Optional[bool] = None) -> LegacyGUI:
    """
    Create a :class:`LegacyGUI` instance.

    Parameters
    ----------
    headless:
        Force headless mode.  When ``None`` the adapter auto-detects.
    """
    return LegacyGUI(headless=headless)
