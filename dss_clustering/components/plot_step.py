"""UI for the 3D plot pipeline step (spec §8.6)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.colors import COLOR_PALETTE
from dss_clustering.components.export_bar import plot_export_bar
from dss_clustering.components.help import help_button, help_panel, step_header
from dss_clustering.components.plotly_relayout import plotly_relayout
from dss_clustering.states.export_state import ExportState
from dss_clustering.states.plot_state import (
    COLOR_CLUSTER,
    COLOR_IDENTITY,
    LABEL_HIDDEN,
    LABEL_SHORT,
    METHOD_SVD,
    METHOD_TSNE,
    METHOD_UMAP,
    PlotState,
)


def _dim_input(label: str, value, on_change, disabled=False) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="2", white_space="nowrap"),
        rx.input(
            type="number",
            value=value.to(str),
            on_change=on_change,
            width="4.5rem",
            min=0,
            disabled=disabled,
        ),
        spacing="2",
        align="center",
    )


def _num(label: str, value, on_change) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="2", white_space="nowrap"),
        rx.input(
            type="number",
            value=value.to(str),
            on_change=on_change,
            width="5rem",
        ),
        spacing="2",
        align="center",
    )


def _palette_picker(current_color, document_id) -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            rx.button(
                rx.box(
                    width="1.2rem",
                    height="1.2rem",
                    border_radius="sm",
                    background=current_color,
                ),
                aria_label="Choose color",
                title="Change color (redraw only)",
                variant="outline",
                size="1",
                width="2.4rem",
                height="1.7rem",
                padding="0.15rem",
            ),
        ),
        rx.popover.content(
            rx.vstack(
                rx.text("Color (no recalculation)", size="2", weight="bold"),
                rx.grid(
                    *[
                        rx.popover.close(
                            rx.button(
                                aria_label=f"Select {color}",
                                title=color,
                                width="1.5rem",
                                height="1.5rem",
                                min_width="0",
                                padding="0",
                                border_radius="sm",
                                background=color,
                                on_click=PlotState.set_book_color(document_id, color),
                            ),
                        )
                        for color in COLOR_PALETTE
                    ],
                    columns="5",
                    spacing="1",
                ),
                rx.popover.close(
                    rx.button(
                        "Reset to corpus default",
                        size="1",
                        variant="soft",
                        on_click=PlotState.clear_book_color(document_id),
                    ),
                ),
                spacing="2",
                align="start",
            ),
            width="auto",
        ),
    )


def _corpus_toggle_row(row) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=row["all_visible"],
            on_change=lambda _: PlotState.toggle_corpus_visibility(row["corpus"]),
        ),
        rx.text(row["label"], size="2", weight="medium"),
        rx.text(
            row["n_visible"].to(str) + "/" + row["n_total"].to(str),
            size="1",
            color="gray",
        ),
        spacing="2",
        align="center",
    )


def _book_row(book) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=book["visible"],
            on_change=lambda _: PlotState.toggle_book_visibility(book["id"]),
        ),
        rx.box(
            width="0.65rem",
            height="0.65rem",
            border_radius="sm",
            background=book["color"],
            flex_shrink="0",
        ),
        rx.text(book["short"], size="2", weight="medium", min_width="3.5rem"),
        rx.text(
            book["label"],
            size="1",
            color="gray",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
            flex="1",
        ),
        _palette_picker(book["color"], book["id"]),
        spacing="2",
        align="center",
        width="100%",
        opacity=rx.cond(book["visible"], "1", "0.45"),
    )


def plot_step() -> rx.Component:
    """3D scatter with SVD / UMAP / t-SNE, labels, and book controls."""
    return rx.vstack(
        step_header("6. 3D plot", "plot"),
        help_panel("plot"),
        rx.text(
            "SVD uses the analysis embedding (feeds clustering). "
            "UMAP and t-SNE are visualization-only — they do not change the dendrogram. "
            "Cluster coloring follows the current dendrogram cut. "
            "Click any point to start a new manual book group, then keep clicking to toggle books.",
            color="gray",
        ),
        rx.hstack(
            help_button("umap"),
            rx.text("UMAP", size="1", color="gray"),
            help_button("tsne"),
            rx.text("t-SNE", size="1", color="gray"),
            spacing="2",
            align="center",
        ),
        help_panel("umap"),
        help_panel("tsne"),
        rx.hstack(
            rx.segmented_control.root(
                rx.segmented_control.item("SVD", value=METHOD_SVD),
                rx.segmented_control.item("UMAP", value=METHOD_UMAP),
                rx.segmented_control.item("t-SNE", value=METHOD_TSNE),
                value=PlotState.method,
                on_change=PlotState.set_method,
            ),
            rx.segmented_control.root(
                rx.segmented_control.item("Identity", value=COLOR_IDENTITY),
                rx.segmented_control.item(
                    "Dendrogram clusters", value=COLOR_CLUSTER
                ),
                value=PlotState.color_mode,
                on_change=PlotState.set_color_mode,
            ),
            rx.segmented_control.root(
                rx.segmented_control.item("Short labels", value=LABEL_SHORT),
                rx.segmented_control.item("Hide labels", value=LABEL_HIDDEN),
                value=PlotState.label_mode,
                on_change=PlotState.set_label_mode,
            ),
            rx.button(
                "Refresh plot",
                on_click=PlotState.recompute,
                size="2",
                variant="soft",
                loading=PlotState.is_fitting_viz,
            ),
            spacing="4",
            flex_wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.cond(
            PlotState.is_svd_method,
            rx.hstack(
                _dim_input("X dim", PlotState.dim_x, PlotState.set_dim_x),
                _dim_input("Y dim", PlotState.dim_y, PlotState.set_dim_y),
                _dim_input("Z dim", PlotState.dim_z, PlotState.set_dim_z),
                spacing="4",
                flex_wrap="wrap",
                align="center",
            ),
        ),
        rx.cond(
            PlotState.is_umap_method,
            rx.hstack(
                _num("n_neighbors", PlotState.umap_n_neighbors, PlotState.set_umap_n_neighbors),
                _num("min_dist", PlotState.umap_min_dist, PlotState.set_umap_min_dist),
                rx.button(
                    "Fit UMAP",
                    on_click=PlotState.refit_viz,
                    size="2",
                    loading=PlotState.is_fitting_viz,
                ),
                spacing="4",
                flex_wrap="wrap",
                align="center",
            ),
        ),
        rx.cond(
            PlotState.is_tsne_method,
            rx.hstack(
                _num(
                    "perplexity",
                    PlotState.tsne_perplexity,
                    PlotState.set_tsne_perplexity,
                ),
                rx.button(
                    "Fit t-SNE",
                    on_click=PlotState.refit_viz,
                    size="2",
                    loading=PlotState.is_fitting_viz,
                ),
                spacing="4",
                flex_wrap="wrap",
                align="center",
            ),
        ),
        rx.text(PlotState.status_message, size="2", color="gray"),
        rx.cond(
            PlotState.camera_captured,
            rx.badge(
                "Current rotation will be used for PNG/PDF export",
                color_scheme="green",
                variant="soft",
            ),
        ),
        rx.text(ExportState.status_message, size="2", color="gray"),
        rx.cond(
            PlotState.has_figure,
            rx.vstack(
                plot_export_bar(kind="plot"),
                rx.box(
                    plotly_relayout(
                        data=PlotState.figure,
                        on_click=PlotState.on_point_click,
                        on_relayout=PlotState.on_relayout,
                    ),
                    width="100%",
                    border="1px solid var(--gray-a6)",
                    border_radius="md",
                    padding="0.5rem",
                    overflow="hidden",
                ),
                width="100%",
                spacing="2",
                align="start",
            ),
        ),
        rx.cond(
            PlotState.plot_books.length() > 0,
            rx.vstack(
                rx.hstack(
                    rx.foreach(PlotState.plot_corpora, _corpus_toggle_row),
                    spacing="4",
                    flex_wrap="wrap",
                    align="center",
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Books on plot", size="2", weight="bold"),
                    rx.input(
                        placeholder="Search books on plot...",
                        value=PlotState.book_search,
                        on_change=PlotState.set_book_search,
                        size="1",
                        max_width="16rem",
                        width="100%",
                    ),
                    rx.text(
                        PlotState.filtered_plot_books.length().to(str)
                        + " / "
                        + PlotState.plot_books.length().to(str),
                        size="1",
                        color="gray",
                        white_space="nowrap",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Show matching",
                        size="1",
                        variant="soft",
                        on_click=PlotState.show_matching_books,
                    ),
                    rx.button(
                        "Hide matching",
                        size="1",
                        variant="soft",
                        on_click=PlotState.hide_matching_books,
                    ),
                    rx.button(
                        "Show all",
                        size="1",
                        variant="soft",
                        on_click=PlotState.show_all_books,
                    ),
                    width="100%",
                    align="center",
                    spacing="2",
                    flex_wrap="wrap",
                ),
                rx.vstack(
                    rx.foreach(PlotState.filtered_plot_books, _book_row),
                    spacing="1",
                    width="100%",
                    max_height="14rem",
                    overflow_y="auto",
                    border="1px solid var(--gray-a6)",
                    border_radius="md",
                    padding="0.5rem",
                ),
                width="100%",
                spacing="2",
            ),
        ),
        spacing="4",
        width="100%",
        align="start",
    )
