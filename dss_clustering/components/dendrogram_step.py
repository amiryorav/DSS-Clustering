"""UI for the dendrogram pipeline step (spec §8.7)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.export_bar import plot_export_bar
from dss_clustering.pipeline.dendrogram import (
    LINKAGE_AVERAGE,
    LINKAGE_WARD,
    METRIC_COSINE,
    METRIC_EUCLIDEAN,
)
from dss_clustering.states.dendrogram_state import DendrogramState
from dss_clustering.states.export_state import ExportState
from dss_clustering.states.plot_state import plot_root_id


def dendrogram_advanced() -> rx.Component:
    """Under-the-hood: linkage, distance metric, refit, and Ward artifacts."""
    from dss_clustering.components.section import under_hood

    return under_hood(
        rx.hstack(
            rx.segmented_control.root(
                rx.segmented_control.item("Ward", value=LINKAGE_WARD),
                rx.segmented_control.item("Average", value=LINKAGE_AVERAGE),
                value=DendrogramState.linkage_method,
                on_change=DendrogramState.set_linkage,
            ),
            rx.segmented_control.root(
                rx.segmented_control.item("Euclidean", value=METRIC_EUCLIDEAN),
                rx.segmented_control.item("Cosine", value=METRIC_COSINE),
                value=DendrogramState.distance_metric,
                on_change=DendrogramState.set_metric,
                disabled=DendrogramState.metric_locked,
            ),
            rx.button(
                "Refit tree",
                on_click=DendrogramState.refit,
                loading=DendrogramState.is_running,
                size="2",
                variant="soft",
            ),
            spacing="4",
            flex_wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.cond(
            DendrogramState.linkage_method == LINKAGE_WARD,
            rx.vstack(
                rx.checkbox(
                    "Mark Ward artifacts as gray italic leaves",
                    checked=DendrogramState.mark_ward_artifacts,
                    on_change=DendrogramState.set_mark_ward_artifacts,
                    size="2",
                ),
                rx.cond(
                    DendrogramState.mark_ward_artifacts,
                    rx.text(
                        "Gray italic leaf = Ward artifact (top-5 three-view "
                        "overlap < 20%).",
                        color="gray",
                        size="1",
                    ),
                ),
                spacing="1",
                align="start",
            ),
        ),
    )


def dendrogram_step() -> rx.Component:
    """Hierarchical clustering tree with live cut-height."""
    return rx.vstack(
        rx.cond(
            DendrogramState.has_tree,
            rx.vstack(
                rx.hstack(
                    rx.text("Cut height", size="2", white_space="nowrap"),
                    rx.input(
                        type="number",
                        value=DendrogramState.cut_height.to(str),
                        on_change=DendrogramState.set_cut_height,
                        min=0,
                        max=DendrogramState.max_height,
                        step=0.001,
                        width="8rem",
                    ),
                    rx.text(
                        "0 – " + DendrogramState.max_height.to(str),
                        size="1",
                        color="gray",
                        white_space="nowrap",
                    ),
                    align="center",
                    spacing="3",
                    flex_wrap="wrap",
                ),
                rx.hstack(
                    rx.badge(
                        DendrogramState.n_clusters.to(str) + " clusters",
                        variant="soft",
                    ),
                    rx.badge(
                        DendrogramState.n_documents.to(str) + " books",
                        variant="soft",
                    ),
                    spacing="2",
                ),
                width="100%",
                spacing="2",
            ),
        ),
        rx.text(DendrogramState.status_message, size="2", color="gray"),
        rx.text(ExportState.status_message, size="2", color="gray"),
        rx.cond(
            DendrogramState.has_tree,
            rx.vstack(
                plot_export_bar(kind="dendrogram"),
                rx.box(
                    rx.box(
                        rx.plotly(
                            data=DendrogramState.figure,
                            on_click=DendrogramState.on_leaf_click,
                            width="100%",
                        ),
                        width="100%",
                        min_width=DendrogramState.figure_min_width,
                    ),
                    id=plot_root_id("dendrogram"),
                    width="100%",
                    border="1px solid var(--gray-a6)",
                    border_radius="md",
                    padding="0.5rem",
                    overflow_x="auto",
                    overflow_y="hidden",
                ),
                width="100%",
                spacing="2",
                align="start",
            ),
        ),
        spacing="4",
        width="100%",
        align="start",
    )
