"""Shared busy / progress indicators for long pipeline steps."""

from __future__ import annotations

import reflex as rx

from dss_clustering.states.busy_state import BusyState


def busy_overlay() -> rx.Component:
    """Full-screen scrim that shows a wait cursor and swallows every click."""
    return rx.cond(
        BusyState.is_busy,
        rx.box(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text(BusyState.message, weight="medium", size="3"),
                spacing="3",
                align="center",
            ),
            position="fixed",
            top="0",
            left="0",
            width="100vw",
            height="100vh",
            display="flex",
            align_items="center",
            justify_content="center",
            background="var(--color-overlay)",
            backdrop_filter="blur(1px)",
            cursor="wait",
            z_index="9999",
        ),
        rx.fragment(),
    )


def busy_banner(is_busy, message) -> rx.Component:
    """Prominent in-progress indicator (spinner + message).

    Built from a box rather than ``rx.callout``: a callout wraps its children in
    a ``<p>``, and nesting the spinner row inside that trips React's hydration
    check for block content inside a paragraph.
    """
    return rx.cond(
        is_busy,
        rx.box(
            rx.hstack(
                rx.spinner(size="3"),
                rx.text(message, weight="medium", size="2"),
                spacing="3",
                align="center",
            ),
            width="100%",
            padding="0.75rem",
            border_radius="md",
            border="1px solid var(--blue-a6)",
            background="var(--blue-a3)",
            color="var(--blue-11)",
        ),
        rx.fragment(),
    )
