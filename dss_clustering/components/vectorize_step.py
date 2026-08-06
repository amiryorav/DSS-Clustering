"""UI for the Vectorize pipeline step."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.busy import busy_banner
from dss_clustering.states.vectorize_state import VectorizeState


def _stat_chip(label: str, value) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color="gray"),
        rx.text(value, weight="bold", size="4"),
        spacing="0",
        align="start",
        min_width="7rem",
    )


def vectorize_step() -> rx.Component:
    """Vectorize: automatic count-matrix build with status only."""
    return rx.vstack(
        rx.heading("3. Vectorize", size="6"),
        rx.text(
            "Build the book × signature count matrix from the selected books "
            "and feature columns. This step has no parameters.",
            color="gray",
        ),
        busy_banner(VectorizeState.is_running, VectorizeState.progress_message),
        rx.hstack(
            rx.button(
                "Build count matrix",
                on_click=VectorizeState.build_matrix,
                loading=VectorizeState.is_running,
                size="2",
                disabled=VectorizeState.is_running,
            ),
            rx.cond(
                VectorizeState.has_matrix,
                rx.cond(
                    VectorizeState.is_stale,
                    rx.badge("stale — rebuild needed", color_scheme="amber"),
                    rx.badge("up to date", color_scheme="green"),
                ),
            ),
            spacing="3",
            align="center",
            flex_wrap="wrap",
        ),
        rx.text(VectorizeState.status_message, size="2", color="gray"),
        rx.cond(
            VectorizeState.has_matrix,
            rx.vstack(
                rx.hstack(
                    _stat_chip("Books", VectorizeState.n_documents),
                    _stat_chip("Signatures", VectorizeState.n_signatures),
                    _stat_chip("Source rows", VectorizeState.n_source_rows),
                    _stat_chip("Non-zeros", VectorizeState.n_nnz),
                    _stat_chip("Density", VectorizeState.nnz_pct_label),
                    spacing="5",
                    flex_wrap="wrap",
                ),
                rx.text(
                    VectorizeState.built_summary,
                    size="2",
                    color="gray",
                ),
                width="100%",
                spacing="2",
                border="1px solid var(--gray-a6)",
                border_radius="md",
                padding="0.75rem",
            ),
        ),
        spacing="4",
        width="100%",
        align="start",
    )
