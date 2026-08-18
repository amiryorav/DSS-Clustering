"""Building blocks for the single-page brochure layout.

Each pipeline stage renders as a full-width section: a numbered heading, a
plain-language blurb, the playful controls, and — tucked away in a closed
accordion — the technical knobs most visitors never need.
"""

from __future__ import annotations

import reflex as rx

from dss_clustering.styles import (
    ACCENT,
    BLURB_SIZE,
    HEADING_SIZE,
    MAX_CONTENT,
    MAX_TEXT,
    SURFACE_ALT,
)


def under_hood(*content: rx.Component) -> rx.Component:
    """A closed-by-default accordion holding the technical controls."""
    return rx.accordion.root(
        rx.accordion.item(
            header="Under the hood",
            content=rx.vstack(
                *content,
                spacing="4",
                width="100%",
                align="start",
                padding_top="1rem",
            ),
            value="under-the-hood",
        ),
        type="single",
        collapsible=True,
        variant="ghost",
        width="100%",
    )


def _placeholder(text: str) -> rx.Component:
    return rx.center(
        rx.hstack(
            rx.icon("sparkles", color="var(--gray-8)"),
            rx.text(text, size="4", color="gray"),
            spacing="3",
            align="center",
        ),
        width="100%",
        padding_y="3rem",
        border="1px dashed var(--gray-a6)",
        border_radius="lg",
    )


def page_section(
    anchor: str,
    number: str,
    title: str,
    blurb: str,
    *body: rx.Component,
    ready=None,
    placeholder: str = "",
    advanced: rx.Component | None = None,
    alt: bool = False,
) -> rx.Component:
    """One brochure section.

    ``ready`` optionally gates the body: until the analysis has produced the
    result this section needs, a friendly placeholder shows instead.
    """
    body_stack = rx.vstack(
        *body,
        spacing="5",
        width="100%",
        align="start",
    )
    if ready is not None:
        body_stack = rx.cond(ready, body_stack, _placeholder(placeholder))

    children: list[rx.Component] = [
        rx.hstack(
            rx.badge(
                number,
                color_scheme=ACCENT,
                variant="soft",
                radius="full",
                size="2",
            ),
            rx.heading(title, size=HEADING_SIZE, weight="bold"),
            spacing="3",
            align="center",
        ),
        rx.text(blurb, size=BLURB_SIZE, color="gray", max_width=MAX_TEXT),
        body_stack,
    ]
    if advanced is not None:
        children.append(advanced)

    return rx.box(
        rx.vstack(
            *children,
            spacing="5",
            width="100%",
            max_width=MAX_CONTENT,
            margin_x="auto",
            align="start",
        ),
        id=anchor,
        width="100%",
        padding_y="3.5rem",
        padding_x="1.5rem",
        background=SURFACE_ALT if alt else "transparent",
        # Anchored jumps should clear the sticky header instead of hiding the
        # heading behind it.
        style={"scroll-margin-top": "5rem"},
    )
