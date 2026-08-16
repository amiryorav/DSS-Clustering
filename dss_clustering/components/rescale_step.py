"""UI for the Rescale pipeline step."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.help import help_button, help_panel, step_header
from dss_clustering.states.rescale_state import RescaleState


def rescale_step() -> rx.Component:
    """Rescale: raw / TF / TF-IDF weighting of the count matrix."""
    return rx.vstack(
        step_header("Rescale", "rescale"),
        help_panel("rescale"),
        rx.text(
            "Choose how raw signature counts are weighted. "
            "This becomes the active matrix for SVD, tables, and metrics.",
            color="gray",
        ),
        rx.segmented_control.root(
            rx.segmented_control.item("Raw", value="raw"),
            rx.segmented_control.item("TF", value="tf"),
            rx.segmented_control.item("TF-IDF", value="tfidf"),
            value=RescaleState.mode,
            on_change=RescaleState.set_mode,
        ),
        rx.hstack(
            help_button("tf_tfidf"),
            rx.text("What TF / TF-IDF mean", size="1", color="gray"),
            spacing="1",
            align="center",
        ),
        help_panel("tf_tfidf"),
        rx.hstack(
            rx.button(
                "Apply",
                on_click=RescaleState.apply,
                size="2",
                variant="soft",
            ),
            rx.cond(
                RescaleState.applied,
                rx.badge("active", color_scheme="green"),
            ),
            spacing="3",
            align="center",
        ),
        rx.text(RescaleState.status_message, size="2", color="gray"),
        spacing="4",
        width="100%",
        align="start",
    )
