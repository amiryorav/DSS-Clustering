"""UI for data tables step (spec §8.8)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.feature_grid import feature_grid
from dss_clustering.components.help import tip_button
from dss_clustering.components.manual_cluster_step import manual_cluster_step
from dss_clustering.pipeline.metrics import (
    SCOPE_BOOK,
    SCOPE_CLUSTER,
    SCOPE_CORPUS,
    SCOPE_MANUAL,
)
from dss_clustering.states.export_state import ExportState
from dss_clustering.states.manual_cluster_state import ManualClusterState
from dss_clustering.states.table_state import TableState
from dss_clustering.styles import ACCENT


def _scope_option(opt: dict) -> rx.Component:
    return rx.select.item(opt["label"], value=opt["value"])


def _member_badge(row: dict) -> rx.Component:
    return rx.badge(
        row["label"],
        title="Document " + row["id"].to(str),
        variant="soft",
        size="1",
    )


def _side_picker(
    *,
    caption: str,
    kind,
    value,
    options,
    on_kind_change,
    on_value_change,
    color: str,
) -> rx.Component:
    return rx.hstack(
        rx.badge(caption, color_scheme=color, size="2", variant="solid"),
        rx.segmented_control.root(
            rx.segmented_control.item("Corpus", value=SCOPE_CORPUS),
            rx.segmented_control.item("Cluster", value=SCOPE_CLUSTER),
            rx.segmented_control.item("Manual group", value=SCOPE_MANUAL),
            rx.segmented_control.item("Book", value=SCOPE_BOOK),
            value=kind,
            on_change=on_kind_change,
            size="1",
        ),
        rx.select.root(
            rx.select.trigger(placeholder="Choose…"),
            rx.select.content(rx.foreach(options, _scope_option)),
            value=value,
            on_change=on_value_change,
            size="2",
        ),
        spacing="3",
        flex_wrap="wrap",
        align="center",
        width="100%",
    )


def _member_panel(title, rows, color: str) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.badge(title, color_scheme=color, variant="soft", size="2"),
            rx.text(rows.length().to(str) + " books", size="1", color="gray"),
            spacing="2",
            align="center",
        ),
        rx.cond(
            rows.length() > 0,
            rx.hstack(
                rx.foreach(rows, _member_badge),
                spacing="2",
                flex_wrap="wrap",
            ),
            rx.text("No books in this group.", size="1", color="gray"),
        ),
        width="100%",
        spacing="2",
        align="start",
        border="1px solid var(--gray-a6)",
        border_radius="md",
        padding="0.75rem",
    )


def tables_step() -> rx.Component:
    """Top / distinctive / gap tables for a subject-reference comparison."""
    return rx.vstack(
        rx.cond(
            ManualClusterState.show_builder,
            rx.vstack(
                rx.hstack(
                    rx.heading("Create our own groups", size="4", weight="bold"),
                    tip_button(
                        "Hide",
                        "Hide the group creator",
                        on_click=ManualClusterState.close_builder,
                        size="2",
                        variant="ghost",
                    ),
                    width="100%",
                    align="center",
                    justify="between",
                ),
                manual_cluster_step(),
                width="100%",
                spacing="3",
                align="start",
                border="1px solid var(--gray-a6)",
                border_radius="md",
                padding="0.75rem",
            ),
            tip_button(
                "Create our own groups",
                "Pick books into a named group to use as either side below",
                on_click=ManualClusterState.open_builder,
                size="2",
                variant="soft",
                color_scheme=ACCENT,
            ),
        ),
        rx.vstack(
            _side_picker(
                caption=TableState.x_display_label,
                kind=TableState.x_kind,
                value=TableState.x_value,
                options=TableState.x_options,
                on_kind_change=TableState.set_x_kind,
                on_value_change=TableState.set_x_value,
                color="indigo",
            ),
            _side_picker(
                caption=TableState.y_display_label,
                kind=TableState.y_kind,
                value=TableState.y_value,
                options=TableState.y_options,
                on_kind_change=TableState.set_y_kind,
                on_value_change=TableState.set_y_value,
                color="gray",
            ),
            rx.hstack(
                rx.button(
                    "Compare",
                    on_click=TableState.recompute,
                    size="2",
                ),
                rx.button(
                    "Swap subject / reference",
                    on_click=TableState.swap_sides,
                    size="2",
                    variant="soft",
                ),
                rx.input(
                    placeholder="Filter signatures…",
                    value=TableState.filter_text,
                    on_change=TableState.set_filter_text,
                    size="2",
                    max_width="16rem",
                ),
                spacing="3",
                flex_wrap="wrap",
                align="center",
            ),
            width="100%",
            spacing="3",
            align="start",
            border="1px solid var(--gray-a6)",
            border_radius="md",
            padding="0.75rem",
        ),
        rx.hstack(
            rx.badge(
                "Stability: " + TableState.stability_pct_label,
                variant="soft",
                color_scheme="green",
            ),
            rx.cond(
                TableState.show_purity,
                rx.badge(
                    "Purity of "
                    + TableState.x_display_label
                    + ": "
                    + TableState.purity_verdict
                    + " ("
                    + TableState.purity_score.to(str)
                    + ")",
                    variant="soft",
                ),
            ),
            rx.cond(
                TableState.show_consistency,
                rx.badge(
                    "Consistency of "
                    + TableState.x_display_label
                    + ": "
                    + TableState.consistency_label,
                    variant="soft",
                    color_scheme="blue",
                ),
            ),
            spacing="3",
            flex_wrap="wrap",
        ),
        rx.grid(
            _member_panel(
                TableState.x_display_label, TableState.x_member_rows, "indigo"
            ),
            _member_panel(
                TableState.y_display_label, TableState.y_member_rows, "gray"
            ),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="3",
            width="100%",
        ),
        rx.text(TableState.status_message, size="2", color="gray"),
        rx.text(ExportState.status_message, size="2", color="gray"),
        rx.cond(
            TableState.has_tables,
            rx.grid(
                feature_grid(
                    grid_id="tables-top",
                    title="Top features",
                    subtitle=TableState.top_subtitle,
                    rows=TableState.filtered_top_rows,
                    help_key="top_features",
                    export_source="tables",
                    export_kind="top",
                ),
                feature_grid(
                    grid_id="tables-distinctive",
                    title="Distinctive features",
                    subtitle=TableState.distinctive_subtitle,
                    rows=TableState.filtered_distinctive_rows,
                    help_key="distinctive_features",
                    export_source="tables",
                    export_kind="distinctive",
                ),
                feature_grid(
                    grid_id="tables-gap",
                    title="Gap features",
                    subtitle=TableState.gap_subtitle,
                    rows=TableState.filtered_gap_rows,
                    help_key="gap_features",
                    export_source="tables",
                    export_kind="gap",
                ),
                columns=rx.breakpoints(initial="1", md="3"),
                spacing="4",
                width="100%",
            ),
        ),
        spacing="4",
        width="100%",
        align="start",
    )
