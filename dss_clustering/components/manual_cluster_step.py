"""UI for manual group selection — pick and save books, no comparison here."""

from __future__ import annotations

import reflex as rx

from dss_clustering.states.auth_state import AuthState
from dss_clustering.states.manual_cluster_state import ManualClusterState


def _cluster_option(opt: dict) -> rx.Component:
    return rx.select.item(opt["label"], value=opt["value"])


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


def manual_cluster_step() -> rx.Component:
    """Pick books into a named group for later use in The numbers."""
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
                "Finish picking — then name and save the group",
                on_click=ManualClusterState.done_picking,
                size="2",
                disabled=ManualClusterState.n_picked <= 0,
            ),
            _tip_button(
                "Clear",
                "Clear the current pick",
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
        rx.cond(
            ManualClusterState.cluster_add_options.length() > 0,
            rx.hstack(
                rx.text("Add cluster", size="2", color="gray"),
                rx.select.root(
                    rx.select.trigger(placeholder="Dendrogram cluster…"),
                    rx.select.content(
                        rx.foreach(
                            ManualClusterState.cluster_add_options,
                            _cluster_option,
                        )
                    ),
                    value=ManualClusterState.cluster_to_add,
                    on_change=ManualClusterState.set_cluster_to_add,
                    size="2",
                ),
                _tip_button(
                    "Add to group",
                    "Add every book in that dendrogram cluster to the current group",
                    on_click=ManualClusterState.add_dendrogram_cluster,
                    size="2",
                    variant="soft",
                ),
                spacing="2",
                flex_wrap="wrap",
                align="center",
            ),
            rx.text(
                "Build the dendrogram to add a whole cluster at once.",
                size="1",
                color="gray",
            ),
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
                    "Groups you save now last until you close the page. "
                    "Sign in at the top of the page to keep them for next time.",
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
                        "side in The numbers below.",
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
        spacing="4",
        width="100%",
        align="start",
    )
