"""Public landing (Home) tab."""

from __future__ import annotations

import reflex as rx

from dss_clustering.states.nav_state import NavState
from dss_clustering.styles import ACCENT, BORDER, BRAND_NAME, BRAND_TAGLINE


def _capability(title: str, body: str) -> rx.Component:
    return rx.vstack(
        rx.text(title, size="3", weight="bold"),
        rx.text(body, size="2", color="gray"),
        spacing="1",
        align="start",
        padding="1rem",
        border=BORDER,
        border_radius="md",
        width="100%",
    )


def landing_page() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.heading(BRAND_NAME, size="9", weight="bold"),
            rx.text(BRAND_TAGLINE, size="4", color="gray", max_width="40rem"),
            rx.hstack(
                rx.button(
                    "Start analysis",
                    size="3",
                    color_scheme=ACCENT,
                    on_click=NavState.start_analysis,
                ),
                spacing="3",
                flex_wrap="wrap",
            ),
            spacing="4",
            align="start",
            padding_y="2rem",
            width="100%",
        ),
        rx.grid(
            _capability(
                "Compare corpora",
                "Select Mikra, Mishna, and DSS books, then build feature tables that contrast any two groups.",
            ),
            _capability(
                "Cluster style",
                "Reduce the matrix with SVD, explore a 3D map, and cut a dendrogram into shared stylistic neighborhoods.",
            ),
            _capability(
                "Save and export",
                "Keep manual book groups under your Google account and export plots or tables with clear branding.",
            ),
            columns=rx.breakpoints(initial="1", md="3"),
            spacing="4",
            width="100%",
        ),
        spacing="6",
        width="100%",
        align="start",
    )
