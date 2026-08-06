"""Shared busy / progress callout for long pipeline steps."""

from __future__ import annotations

import reflex as rx


def busy_banner(is_busy, message) -> rx.Component:
    """Prominent in-progress indicator (spinner + message)."""
    return rx.cond(
        is_busy,
        rx.callout(
            rx.hstack(
                rx.spinner(size="3"),
                rx.text(message, weight="medium"),
                spacing="3",
                align="center",
            ),
            color_scheme="blue",
            variant="surface",
            width="100%",
        ),
        rx.fragment(),
    )
