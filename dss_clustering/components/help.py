"""Reusable (?) help button and panel (spec §5.3)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.help_content import HELP_CONTENT
from dss_clustering.states.help_state import HelpState


def help_button(key: str) -> rx.Component:
    """Small ghost button that toggles a help panel."""
    return rx.icon_button(
        "circle-help",
        on_click=HelpState.toggle(key),
        size="1",
        variant="ghost",
        aria_label=f"Help: {HELP_CONTENT.get(key, {}).get('title', key)}",
        title=HELP_CONTENT.get(key, {}).get("title", key),
    )


def help_panel(key: str) -> rx.Component:
    """Callout shown while ``key`` is in HelpState.open_keys."""
    entry = HELP_CONTENT.get(
        key,
        {"title": key, "body": "No help text is defined for this topic yet."},
    )
    return rx.cond(
        HelpState.open_keys.contains(key),
        rx.callout(
            rx.vstack(
                rx.text(entry["title"], weight="bold", size="2"),
                rx.text(entry["body"], size="2"),
                spacing="1",
                align="start",
            ),
            icon="info",
            color_scheme="blue",
            width="100%",
        ),
    )


def step_header(title: str, help_key: str) -> rx.Component:
    """Step title row with an inline (?) toggle."""
    return rx.hstack(
        rx.heading(title, size="6"),
        help_button(help_key),
        spacing="2",
        align="center",
    )
