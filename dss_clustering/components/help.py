"""Reusable (?) help button, panel, and control hints."""

from __future__ import annotations

import reflex as rx

from dss_clustering.help_content import help_entry
from dss_clustering.states.help_state import HelpState
from dss_clustering.states.nav_state import NavState


def help_button(key: str) -> rx.Component:
    """Small ghost button that toggles a short inline tip."""
    entry = help_entry(key)
    return rx.icon_button(
        "circle-help",
        on_click=HelpState.toggle(key),
        size="1",
        variant="ghost",
        aria_label=f"Help: {entry['title']}",
        title=entry["summary"],
    )


def help_panel(key: str) -> rx.Component:
    """Short callout shown while ``key`` is in HelpState.open_keys."""
    entry = help_entry(key)
    return rx.cond(
        HelpState.open_keys.contains(key),
        rx.callout.root(
            rx.callout.icon(rx.icon("info")),
            # A plain vstack keeps the block content out of Callout.Text's <p>.
            rx.vstack(
                rx.text(entry["title"], weight="bold", size="2"),
                rx.text(entry["summary"], size="2"),
                rx.link(
                    "More in Help",
                    size="1",
                    on_click=NavState.go_help,
                ),
                spacing="1",
                align="start",
            ),
            color_scheme="teal",
            width="100%",
        ),
    )


def control_hint(text: str) -> rx.Component:
    """One-line hint under a primary control."""
    return rx.text(text, size="1", color="gray")


def step_header(title: str, help_key: str) -> rx.Component:
    """Step title row with an inline (?) toggle."""
    return rx.hstack(
        rx.heading(title, size="6"),
        help_button(help_key),
        spacing="2",
        align="center",
    )
