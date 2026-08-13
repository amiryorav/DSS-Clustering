"""UI for the SVD pipeline step (constant or sweep)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.busy import busy_banner
from dss_clustering.components.help import help_button, help_panel, step_header
from dss_clustering.states.svd_state import MODE_CONSTANT, MODE_SWEEP, SVDState


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


def svd_step() -> rx.Component:
    """SVD controls: constant size or sweep-to-best (seed fixed internally)."""
    return rx.vstack(
        step_header("5. SVD", "svd"),
        help_panel("svd"),
        rx.text(
            "Compress the active matrix into analysis-space dimensions used by "
            "the 3D plot, dendrogram, and tables. "
            "Use constant size, or sweep a range and pick the best by "
            "cophenetic correlation (Ward + Euclidean). "
            "Click a point on the sweep chart to set Constant dimensions.",
            color="gray",
        ),
        rx.hstack(
            help_button("cophenetic_correlation"),
            rx.text("Cophenetic correlation", size="1", color="gray"),
            spacing="1",
            align="center",
        ),
        help_panel("cophenetic_correlation"),
        busy_banner(SVDState.is_running, SVDState.progress_message),
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
        rx.text(SVDState.status_message, size="2", color="gray"),
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
            rx.vstack(
                rx.text("Sweep results", size="2", weight="bold"),
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
                width="100%",
                spacing="2",
            ),
        ),
        spacing="4",
        width="100%",
        align="start",
    )
