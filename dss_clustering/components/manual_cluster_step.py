"""UI for manual cluster selection (spec §8.9)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.feature_grid import feature_grid
from dss_clustering.components.help import help_panel, step_header
from dss_clustering.pipeline.metrics import (
    COMPARE_ALL_OTHER,
    COMPARE_CORPUS,
    COMPARE_EXISTING_CLUSTER,
)
from dss_clustering.states.manual_cluster_state import ManualClusterState


def _picked_chip(row: dict) -> rx.Component:
    return rx.badge(row["label"], variant="soft", size="2")


def _pickable_row(row: dict) -> rx.Component:
    return rx.button(
        row["label"],
        size="1",
        variant=rx.cond(row["picked"], "solid", "outline"),
        on_click=ManualClusterState.toggle_document(row["id"]),
        disabled=ManualClusterState.picking == False,  # noqa: E712
    )


def _saved_group_row(group: dict) -> rx.Component:
    return rx.hstack(
        rx.text(group["name"], weight="medium"),
        rx.text(
            group["n_books"].to(str) + " books",
            size="1",
            color="gray",
        ),
        rx.spacer(),
        rx.button(
            "Load",
            size="1",
            variant="soft",
            on_click=ManualClusterState.load_group(group["id"]),
        ),
        rx.button(
            "Delete",
            size="1",
            variant="soft",
            color_scheme="red",
            on_click=ManualClusterState.delete_group(group["id"]),
        ),
        width="100%",
        align="center",
    )


def _comparison_option(option: dict) -> rx.Component:
    return rx.select.item(option["label"], value=option["value"])


def _comparison_member(row: dict) -> rx.Component:
    return rx.badge(
        row["label"],
        title="Document " + row["id"].to(str),
        variant="soft",
        size="1",
    )


def manual_cluster_step() -> rx.Component:
    """Click-to-select books and compare against a reference group."""
    return rx.vstack(
        step_header("Manual group", "manual_cluster"),
        help_panel("manual_cluster"),
        rx.text(
            "Click a book on the 3D plot to start a new group directly, or use "
            "Start selecting to reset first; then click the 3D plot or dendrogram. "
            "Done runs the same top / distinctive / gap comparison as the "
            "tables step against the chosen reference group.",
            color="gray",
        ),
        rx.hstack(
            rx.button(
                "Start selecting",
                on_click=ManualClusterState.start_picking,
                size="2",
                variant=rx.cond(ManualClusterState.picking, "solid", "soft"),
                color_scheme=rx.cond(ManualClusterState.picking, "orange", "gray"),
            ),
            rx.button(
                "Done",
                on_click=ManualClusterState.done_picking,
                size="2",
                disabled=ManualClusterState.n_picked <= 0,
            ),
            rx.button(
                "Clear",
                on_click=ManualClusterState.clear_picked,
                size="2",
                variant="ghost",
            ),
            rx.badge(
                ManualClusterState.n_picked.to(str) + " picked",
                variant="soft",
            ),
            spacing="3",
            flex_wrap="wrap",
            align="center",
        ),
        rx.hstack(
            rx.text("Compare against", size="2", white_space="nowrap"),
            rx.segmented_control.root(
                rx.segmented_control.item("Corpus", value=COMPARE_CORPUS),
                rx.segmented_control.item("All other", value=COMPARE_ALL_OTHER),
                rx.segmented_control.item(
                    "Cluster", value=COMPARE_EXISTING_CLUSTER
                ),
                value=ManualClusterState.comparison_scope_type,
                on_change=ManualClusterState.set_comparison_scope_type,
            ),
            rx.cond(
                ManualClusterState.comparison_scope_type != COMPARE_ALL_OTHER,
                rx.select.root(
                    rx.select.trigger(placeholder="Choose comparison group…"),
                    rx.select.content(
                        rx.foreach(
                            ManualClusterState.comparison_options_rows,
                            _comparison_option,
                        )
                    ),
                    value=ManualClusterState.comparison_scope_value,
                    on_change=ManualClusterState.set_comparison_scope_value,
                    size="2",
                ),
            ),
            spacing="3",
            flex_wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.cond(
            ManualClusterState.picking,
            rx.vstack(
                rx.text(
                    "Click plot/dendrogram leaves, or toggle books here:",
                    size="2",
                    color="gray",
                ),
                rx.hstack(
                    rx.foreach(ManualClusterState.pickable_books, _pickable_row),
                    spacing="2",
                    flex_wrap="wrap",
                ),
                width="100%",
                spacing="2",
            ),
        ),
        rx.cond(
            ManualClusterState.n_picked > 0,
            rx.hstack(
                rx.foreach(ManualClusterState.picked_chip_rows, _picked_chip),
                spacing="2",
                flex_wrap="wrap",
            ),
        ),
        rx.hstack(
            rx.input(
                placeholder="Group name…",
                value=ManualClusterState.saved_name,
                on_change=ManualClusterState.set_saved_name,
                size="2",
                max_width="14rem",
            ),
            rx.button(
                "Save group",
                on_click=ManualClusterState.save_group,
                size="2",
                variant="soft",
            ),
            spacing="3",
            align="center",
        ),
        rx.vstack(
            rx.hstack(
                rx.text("Your saved groups", size="2", weight="bold"),
                rx.button(
                    "Refresh",
                    size="1",
                    variant="ghost",
                    on_click=ManualClusterState.load_saved_groups,
                ),
                spacing="2",
                align="center",
            ),
            rx.cond(
                ManualClusterState.saved_groups.length() > 0,
                rx.vstack(
                    rx.foreach(ManualClusterState.saved_groups, _saved_group_row),
                    width="100%",
                    spacing="2",
                ),
                rx.text(
                    "No saved groups yet. Saved groups are stored under your "
                    "user id and can be picked as X or Y in the data tables.",
                    size="1",
                    color="gray",
                ),
            ),
            width="100%",
            spacing="2",
            align="start",
        ),
        rx.text(ManualClusterState.status_message, size="2", color="gray"),
        rx.cond(
            ManualClusterState.has_results,
            rx.vstack(
                rx.badge(
                    "Consistency: " + ManualClusterState.consistency,
                    variant="soft",
                    color_scheme="blue",
                ),
                rx.vstack(
                    rx.text(
                        "Books in comparison group ("
                        + ManualClusterState.comparison_member_rows.length().to(str)
                        + ")",
                        size="2",
                        weight="bold",
                    ),
                    rx.hstack(
                        rx.foreach(
                            ManualClusterState.comparison_member_rows,
                            _comparison_member,
                        ),
                        spacing="2",
                        flex_wrap="wrap",
                    ),
                    width="100%",
                    spacing="2",
                ),
                rx.grid(
# Also wire glossary help into manual cluster result grids when present.
                feature_grid(
                    grid_id="manual-top",
                    title="Top features",
                    rows=ManualClusterState.top_rows,
                    help_key="top_features",
                    export_source="manual",
                    export_kind="top",
                ),
                feature_grid(
                    grid_id="manual-distinctive",
                    title="Distinctive features",
                    rows=ManualClusterState.distinctive_rows,
                    help_key="distinctive_features",
                    export_source="manual",
                    export_kind="distinctive",
                ),
                feature_grid(
                    grid_id="manual-gap",
                    title="Gap features",
                    rows=ManualClusterState.gap_rows,
                    help_key="gap_features",
                    export_source="manual",
                    export_kind="gap",
                ),
                    columns=rx.breakpoints(initial="1", md="3"),
                    spacing="4",
                    width="100%",
                ),
                width="100%",
                spacing="3",
            ),
        ),
        spacing="4",
        width="100%",
        align="start",
    )
