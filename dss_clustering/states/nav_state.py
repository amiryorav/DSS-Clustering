"""Top-level navigation for the single-page brochure layout.

The old step-by-step wizard is gone: the whole analysis lives on one scrolling
page (``TAB_HOME``), and Help stays a separate tab. ``scroll_to`` smoothly jumps
to a section anchor so buttons like "Run the analysis" can move the viewport.
"""

from __future__ import annotations

import reflex as rx

TAB_HOME = "home"
TAB_HELP = "help"

# Section anchors on the one-page layout, in reading order.
ANCHOR_TEXTS = "texts"
ANCHOR_COMPARE = "compare"
ANCHOR_RUN = "run"
ANCHOR_MAP = "map"
ANCHOR_TREE = "tree"
ANCHOR_GROUPS = "groups"
ANCHOR_NUMBERS = "numbers"
ANCHOR_SAVE = "save"


class NavState(rx.State):
    """Home (the one-page analysis) vs Help, plus smooth-scroll to a section."""

    main_tab: str = TAB_HOME

    @rx.event
    def set_main_tab(self, tab: str):
        if tab in (TAB_HOME, TAB_HELP):
            self.main_tab = tab

    @rx.event
    def go_home(self):
        self.main_tab = TAB_HOME

    @rx.event
    def go_help(self):
        self.main_tab = TAB_HELP

    @rx.event
    def scroll_to(self, anchor: str):
        """Jump to a section, switching back to the main page first if needed."""
        self.main_tab = TAB_HOME
        return rx.call_script(
            f"""
            requestAnimationFrame(() => {{
              const el = document.getElementById({anchor!r});
              if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }});
            """
        )
