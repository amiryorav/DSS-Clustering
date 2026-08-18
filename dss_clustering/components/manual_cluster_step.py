"""UI for manual cluster selection (spec §8.9)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.feature_grid import feature_grid
from dss_clustering.components.google_signin import google_signin_button
from dss_clustering.pipeline.metrics import (
    COMPARE_ALL_OTHER,
    COMPARE_CORPUS,
    COMPARE_EXISTING_CLUSTER,
)
from dss_clustering.states.auth_state import AuthState
from dss_clustering.states.manual_cluster_state import ManualClusterState


def _tip_button(label: str, tip: str, **kwargs) -> rx.Component:
    return rx.tooltip(
        rx.button(label, **kwargs),
        content=tip,
        side="top",
        side_offset=4,
    )


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
        rx.cond(
            group["scope"] == "session",
            rx.badge("this visit only", variant="soft", color_scheme="amber", size="1"),
            rx.badge("saved", variant="soft", color_scheme="green", size="1"),
        ),
        rx.spacer(),
        _tip_button(
            "Load",
            "Load this group back into the picker",
            size="1",
            variant="soft",
            on_click=ManualClusterState.load_group(group["id"]),
        ),
        _tip_button(
            "Delete",
            "Remove this group",
            size="1",
            variant="soft",
            color_scheme="red",
            on_click=ManualClusterState.delete_group(group["id"]),
        ),
        width="100%",
        align="center",
        spacing="3",
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
        rx.hstack(
            _tip_button(
                "Start selecting",
                "Clear the current pick and start a new group",
                on_click=ManualClusterState.start_picking,
                size="2",
                variant=rx.cond(ManualClusterState.picking, "solid", "soft"),
                color_scheme=rx.cond(ManualClusterState.picking, "orange", "gray"),
            ),
            _tip_button(
                "Done",
                "Compare the picked books to the reference group",
                on_click=ManualClusterState.done_picking,
                size="2",
                disabled=ManualClusterState.n_picked <= 0,
            ),
            _tip_button(
                "Clear",
                "Clear the current pick without comparing",
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
                    rx.select.trigger(placeholder="Choose group…"),
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
        rx.vstack(
            rx.hstack(
                rx.input(
                    placeholder="Group name…",
                    value=ManualClusterState.saved_name,
                    on_change=ManualClusterState.set_saved_name,
                    size="2",
                    max_width="14rem",
                ),
                _tip_button(
                    "Save group",
                    rx.cond(
                        AuthState.is_authenticated,
                        "Store this book group under your account",
                        "Keep this group for the rest of your visit",
                    ),
                    on_click=ManualClusterState.save_group,
                    size="2",
                    variant="soft",
                ),
                spacing="3",
                align="center",
                flex_wrap="wrap",
            ),
            rx.cond(
                ~AuthState.is_authenticated,
                rx.callout(
                    rx.hstack(
                        rx.text(
                            "Groups you save now last until you close the page. "
                            "Sign in to keep them for next time.",
                            size="2",
                        ),
                        rx.cond(AuthState.has_client_id, google_signin_button()),
                        spacing="3",
                        align="center",
                        flex_wrap="wrap",
                    ),
                    icon="info",
                    color_scheme="gray",
                    width="100%",
                ),
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Your groups", size="2", weight="bold"),
                    rx.cond(
                        AuthState.is_authenticated,
                        _tip_button(
                            "Refresh",
                            "Reload groups from your account",
                            size="1",
                            variant="ghost",
                            on_click=ManualClusterState.load_saved_groups,
                        ),
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.cond(
                    ManualClusterState.group_rows.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            ManualClusterState.group_rows, _saved_group_row
                        ),
                        width="100%",
                        spacing="2",
                    ),
                    rx.text(
                        "No groups yet. Saved groups can be picked as either "
                        "side in the comparison tables below.",
                        size="1",
                        color="gray",
                    ),
                ),
                width="100%",
                spacing="2",
                align="start",
            ),
            width="100%",
            spacing="3",
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
