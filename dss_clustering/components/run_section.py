"""The single "Run the analysis" section.

Merges the old Vectorize, Rescale, and SVD steps. A visitor sees one big
button and a plain-language result line; the weighting choice, SVD controls,
and matrix statistics all live under the hood.
"""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.busy import busy_banner
from dss_clustering.components.section import under_hood
from dss_clustering.states.export_state import ExportState
from dss_clustering.states.rescale_state import RescaleState
from dss_clustering.states.svd_state import MODE_CONSTANT, MODE_SWEEP, SVDState
from dss_clustering.states.vectorize_state import VectorizeState
from dss_clustering.styles import ACCENT, BODY_SIZE


def _num(label: str, value, on_change, disabled=False) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="2", white_space="nowrap"),
        rx.input(
            type="number",
            value=value.to(str),
            on_change=on_change,
            width="5.5rem",
            disabled=disabled,
        ),
        spacing="2",
        align="center",
    )


def _stat_chip(label: str, value) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color="gray"),
        rx.text(value, weight="bold", size="4"),
        spacing="0",
        align="start",
        min_width="7rem",
    )


def run_controls() -> rx.Component:
    """Visible part: one button, a status line, and a friendly result."""
    return rx.vstack(
        busy_banner(VectorizeState.is_running, VectorizeState.progress_message),
        rx.cond(
            VectorizeState.is_stale & VectorizeState.has_matrix,
            rx.callout(
                "Your book or feature choices changed. Run the analysis again "
                "to bring the results below up to date.",
                icon="triangle-alert",
                color_scheme="amber",
                width="100%",
            ),
        ),
        rx.button(
            rx.icon("play", size=20),
            rx.cond(VectorizeState.has_matrix, "Run the analysis again", "Run the analysis"),
            on_click=VectorizeState.build_matrix,
            loading=VectorizeState.is_running,
            disabled=VectorizeState.is_running,
            size="4",
            color_scheme=ACCENT,
        ),
        rx.cond(
            VectorizeState.has_matrix & ~VectorizeState.is_stale,
            rx.text(
                "Ready — compared "
                + VectorizeState.n_documents.to(str)
                + " books using "
                + VectorizeState.n_source_rows.to(str)
                + " word occurrences. Explore the map, tree, and tables below.",
                size=BODY_SIZE,
            ),
            rx.text(VectorizeState.status_message, size=BODY_SIZE, color="gray"),
        ),
        spacing="4",
        width="100%",
        align="start",
        on_mount=VectorizeState.refresh_stale,
    )


def _weighting_control() -> rx.Component:
    return rx.vstack(
        rx.text("How word counts are weighted", weight="bold", size="2"),
        rx.segmented_control.root(
            rx.segmented_control.item("Raw counts", value="raw"),
            rx.segmented_control.item("Term frequency", value="tf"),
            rx.segmented_control.item("TF-IDF", value="tfidf"),
            value=RescaleState.mode,
            on_change=RescaleState.set_mode,
        ),
        rx.text(RescaleState.status_message, size="1", color="gray"),
        spacing="2",
        align="start",
        width="100%",
    )


def _svd_controls() -> rx.Component:
    return rx.vstack(
        rx.text("Dimensionality reduction (SVD)", weight="bold", size="2"),
        rx.hstack(
            rx.hstack(
                rx.switch(
                    checked=SVDState.enabled,
                    on_change=SVDState.set_enabled,
                ),
                rx.text("Enable SVD", size="2"),
                spacing="2",
                align="center",
            ),
            rx.segmented_control.root(
                rx.segmented_control.item("Constant", value=MODE_CONSTANT),
                rx.segmented_control.item("Sweep", value=MODE_SWEEP),
                value=SVDState.mode,
                on_change=SVDState.set_mode,
                disabled=~SVDState.enabled,
            ),
            rx.hstack(
                rx.switch(
                    checked=SVDState.normalize,
                    on_change=SVDState.set_normalize,
                    disabled=~SVDState.enabled,
                ),
                rx.text("L2 normalize", size="2"),
                spacing="2",
                align="center",
            ),
            rx.button(
                "Run SVD",
                on_click=SVDState.run,
                loading=SVDState.is_running,
                size="2",
                variant="soft",
            ),
            spacing="4",
            flex_wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.cond(
            SVDState.enabled,
            rx.cond(
                SVDState.is_sweep,
                rx.hstack(
                    _num("From", SVDState.sweep_min, SVDState.set_sweep_min),
                    _num("To", SVDState.sweep_max, SVDState.set_sweep_max),
                    _num("Step", SVDState.sweep_step, SVDState.set_sweep_step),
                    _num(
                        "Plateau min",
                        SVDState.plateau_min,
                        SVDState.set_plateau_min,
                    ),
                    rx.cond(
                        VectorizeState.max_svd_components > 0,
                        rx.badge(
                            "max "
                            + VectorizeState.max_svd_components.to(str)
                            + " dims",
                            color_scheme=rx.cond(
                                SVDState.sweep_max
                                > VectorizeState.max_svd_components,
                                "amber",
                                "gray",
                            ),
                            variant="soft",
                        ),
                    ),
                    spacing="4",
                    flex_wrap="wrap",
                    align="center",
                    width="100%",
                ),
                _num(
                    "Components",
                    SVDState.n_components,
                    SVDState.set_n_components,
                ),
            ),
        ),
        rx.text(SVDState.status_message, size="1", color="gray"),
        rx.cond(
            SVDState.has_sweep_figure,
            rx.box(
                rx.plotly(
                    data=SVDState.sweep_figure,
                    on_click=SVDState.on_sweep_click,
                ),
                width="100%",
                border="1px solid var(--gray-a6)",
                border_radius="md",
                padding="0.5rem",
                overflow="hidden",
            ),
        ),
        rx.cond(
            SVDState.sweep_results.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Dims"),
                        rx.table.column_header_cell("Variance"),
                        rx.table.column_header_cell("Cophenetic"),
                        rx.table.column_header_cell(""),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        SVDState.sweep_results,
                        lambda row: rx.table.row(
                            rx.table.cell(
                                rx.button(
                                    row["n"],
                                    size="1",
                                    variant="ghost",
                                    on_click=SVDState.select_sweep_dims(row["n"]),
                                ),
                            ),
                            rx.table.cell(row["var_exp"]),
                            rx.table.cell(row["cc"]),
                            rx.table.cell(
                                rx.cond(
                                    row["selected"],
                                    rx.badge("selected", color_scheme="green"),
                                    rx.fragment(),
                                ),
                            ),
                        ),
                    ),
                ),
                width="100%",
                variant="surface",
                size="1",
            ),
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def _matrix_stats() -> rx.Component:
    return rx.cond(
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
            rx.text(VectorizeState.built_summary, size="2", color="gray"),
            rx.button(
                "Export raw matrix CSV",
                on_click=ExportState.export_count_matrix,
                size="2",
                variant="soft",
                disabled=VectorizeState.is_stale,
            ),
            rx.text(ExportState.status_message, size="1", color="gray"),
            width="100%",
            spacing="3",
            border="1px solid var(--gray-a6)",
            border_radius="md",
            padding="0.75rem",
        ),
    )


def run_advanced() -> rx.Component:
    """Under-the-hood: weighting, SVD, and matrix statistics."""
    return under_hood(
        _weighting_control(),
        rx.divider(),
        _svd_controls(),
        rx.divider(),
        _matrix_stats(),
    )
