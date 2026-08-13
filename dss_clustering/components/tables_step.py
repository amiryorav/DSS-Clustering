"""UI for data tables step (spec §8.8)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.feature_grid import feature_grid
from dss_clustering.components.help import help_button, help_panel, step_header
from dss_clustering.pipeline.metrics import (
    SCOPE_BOOK,
    SCOPE_CLUSTER,
    SCOPE_CORPUS,
    SCOPE_MANUAL,
)
from dss_clustering.states.export_state import ExportState
from dss_clustering.states.table_state import TableState


def _scope_option(opt: dict) -> rx.Component:
    return rx.select.item(opt["label"], value=opt["value"])


def _member_badge(row: dict) -> rx.Component:
    return rx.badge(
        row["label"],
        title="Document " + row["id"].to(str),
        variant="soft",
        size="1",
    )


def tables_step() -> rx.Component:
    """Top / distinctive / gap tables with purity and stability metrics."""
    return rx.vstack(
        step_header("9. Data tables", "tables"),
        help_panel("tables"),
        rx.text(
            "Top, distinctive, and gap features for any corpus, dendrogram "
            "cluster, saved manual cluster, or book. "
            "Corpus-wide stability is shown once above the tables; purity appears "
            "in book scope and consistency in cluster scope.",
            color="gray",
        ),
        rx.hstack(
            help_button("consistency_score"),
            rx.text("Consistency / purity", size="1", color="gray"),
            spacing="1",
            align="center",
        ),
        help_panel("consistency_score"),
        rx.hstack(
            rx.segmented_control.root(
                rx.segmented_control.item("Corpus", value=SCOPE_CORPUS),
                rx.segmented_control.item("Cluster", value=SCOPE_CLUSTER),
                rx.segmented_control.item("Manual cluster", value=SCOPE_MANUAL),
                rx.segmented_control.item("Book", value=SCOPE_BOOK),
                value=TableState.scope,
                on_change=TableState.set_scope,
            ),
            rx.select.root(
                rx.select.trigger(placeholder="Scope value…"),
                rx.select.content(
                    rx.foreach(TableState.scope_options_rows, _scope_option),
                ),
                value=TableState.scope_value,
                on_change=TableState.set_scope_value,
                size="2",
            ),
            rx.input(
                placeholder="Filter signatures…",
                value=TableState.filter_text,
                on_change=TableState.set_filter_text,
                size="2",
                max_width="16rem",
            ),
            rx.button(
                "Refresh",
                on_click=TableState.recompute,
                size="2",
                variant="soft",
            ),
            spacing="3",
            flex_wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.hstack(
            rx.badge(
                "Stability: " + TableState.stability_pct_label,
                variant="soft",
                color_scheme="green",
            ),
            rx.cond(
                TableState.scope == SCOPE_BOOK,
                rx.badge(
                    "Purity: "
                    + TableState.purity_verdict
                    + " ("
                    + TableState.purity_score.to(str)
                    + ")",
                    variant="soft",
                ),
            ),
            rx.cond(
                (TableState.scope == SCOPE_CLUSTER)
                | (TableState.scope == SCOPE_MANUAL),
                rx.badge(
                    "Consistency: " + TableState.consistency_label,
                    variant="soft",
                    color_scheme="blue",
                ),
            ),
            spacing="3",
            flex_wrap="wrap",
        ),
        rx.cond(
            ((TableState.scope == SCOPE_CLUSTER) | (TableState.scope == SCOPE_MANUAL))
            & (TableState.group_member_rows.length() > 0),
            rx.vstack(
                rx.text(
                    "Books in this group ("
                    + TableState.group_member_rows.length().to(str)
                    + ")",
                    size="2",
                    weight="bold",
                ),
                rx.hstack(
                    rx.foreach(TableState.group_member_rows, _member_badge),
                    spacing="2",
                    flex_wrap="wrap",
                ),
                width="100%",
                spacing="2",
                border="1px solid var(--gray-a6)",
                border_radius="md",
                padding="0.75rem",
            ),
        ),
        rx.text(TableState.status_message, size="2", color="gray"),
        rx.text(ExportState.status_message, size="2", color="gray"),
        rx.cond(
            TableState.has_tables,
            rx.grid(
                feature_grid(
                    grid_id="tables-top",
                    title="Top features",
                    rows=TableState.filtered_top_rows,
                    help_key="top_features",
                    export_source="tables",
                    export_kind="top",
                ),
                feature_grid(
                    grid_id="tables-distinctive",
                    title="Distinctive features",
                    rows=TableState.filtered_distinctive_rows,
                    help_key="distinctive_features",
                    export_source="tables",
                    export_kind="distinctive",
                ),
                feature_grid(
                    grid_id="tables-gap",
                    title="Gap features",
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
