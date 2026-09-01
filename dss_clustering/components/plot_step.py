"""UI for the 3D plot pipeline step (spec §8.6)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.colors import COLOR_PALETTE
from dss_clustering.components.export_bar import plot_export_bar
from dss_clustering.components.help import tip_button
from dss_clustering.states.export_state import ExportState
from dss_clustering.states.plot_state import (
    COLOR_CLUSTER,
    COLOR_IDENTITY,
    LABEL_HIDDEN,
    LABEL_SHORT,
    METHOD_SVD,
    METHOD_TSNE,
    METHOD_UMAP,
    PANEL_SINGLE,
    PANEL_PCA,
    PANEL_SVD_B,
    PANEL_TSNE,
    PANEL_UMAP,
    ROTATE_STEP_DEGREES,
    ZOOM_FACTOR,
    PlotState,
    plot_root_id,
)

# Buttons drive the camera, so Plotly's own modebar would only duplicate them.
PLOT_CONFIG = {
    "scrollZoom": True,
    "displaylogo": False,
    "displayModeBar": False,
    "responsive": True,
}
# Four gl3d scenes plus a disappearing overlay: Plotly's responsive
# relayout can freeze the tab. Camera pads still resize the view.
GRID_PLOT_CONFIG = {
    **PLOT_CONFIG,
    "responsive": False,
}


def _pad_icon(icon: str, tip: str, on_click) -> rx.Component:
    return rx.tooltip(
        rx.icon_button(
            rx.icon(icon, size=14),
            size="1",
            variant="soft",
            on_click=on_click,
            aria_label=tip,
        ),
        content=tip,
        side="top",
        side_offset=4,
    )


def _camera_pad(panel: str) -> rx.Component:
    """Zoom / rotate / reset controls for one 3D scene."""
    return rx.hstack(
        _pad_icon("zoom-in", "Zoom in", PlotState.zoom_panel(panel, ZOOM_FACTOR)),
        _pad_icon(
            "zoom-out", "Zoom out", PlotState.zoom_panel(panel, 1 / ZOOM_FACTOR)
        ),
        rx.box(width="0.5rem"),
        _pad_icon(
            "arrow-left",
            "Rotate left",
            PlotState.rotate_panel(panel, -ROTATE_STEP_DEGREES, 0),
        ),
        _pad_icon(
            "arrow-right",
            "Rotate right",
            PlotState.rotate_panel(panel, ROTATE_STEP_DEGREES, 0),
        ),
        _pad_icon(
            "arrow-up",
            "Tilt up",
            PlotState.rotate_panel(panel, 0, ROTATE_STEP_DEGREES),
        ),
        _pad_icon(
            "arrow-down",
            "Tilt down",
            PlotState.rotate_panel(panel, 0, -ROTATE_STEP_DEGREES),
        ),
        rx.box(width="0.5rem"),
        _pad_icon("locate-fixed", "Reset view", PlotState.reset_panel_view(panel)),
        spacing="1",
        align="center",
        flex_wrap="wrap",
    )


def _grid_panel(panel: str, title, figure, ready, empty=None) -> rx.Component:
    fallback = empty or rx.text("Not available", size="2", color="gray")
    return rx.vstack(
        rx.hstack(
            rx.text(title, size="2", weight="bold"),
            rx.spacer(),
            plot_export_bar(kind="plot", panel=panel),
            _camera_pad(panel),
            width="100%",
            align="center",
            flex_wrap="wrap",
        ),
        rx.cond(
            ready,
            rx.box(
                rx.plotly(
                    data=figure,
                    config=GRID_PLOT_CONFIG,
                    on_click=PlotState.on_point_click,
                    width="100%",
                ),
                id=plot_root_id(panel),
                width="100%",
            ),
            rx.center(
                rx.cond(
                    PlotState.is_fitting_viz,
                    rx.spinner(size="2"),
                    fallback,
                ),
                width="100%",
                min_height="420px",
                padding="1rem",
            ),
        ),
        width="100%",
        spacing="2",
        border="1px solid var(--gray-a6)",
        border_radius="md",
        padding="0.5rem",
    )


def _dim_input(label: str, value, on_change, disabled=False) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="2", white_space="nowrap"),
        rx.input(
            type="number",
            value=value.to(str),
            on_change=on_change,
            width="4.5rem",
            min=1,
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
                rx.text("Color", size="2", weight="bold"),
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
                        rx.cond(
                            PlotState.color_mode == COLOR_CLUSTER,
                            "Reset to cluster color",
                            "Reset to corpus default",
                        ),
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


def plot_advanced() -> rx.Component:
    """Under-the-hood: which SVD dims to show and the UMAP / t-SNE knobs."""
    from dss_clustering.components.section import under_hood

    return under_hood(
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
                tip_button(
                    "Fit UMAP",
                    "Compute UMAP (SVD-compressed for speed); may take a few seconds",
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
                tip_button(
                    "Fit t-SNE",
                    "Compute t-SNE (SVD-compressed for speed); may take a few seconds",
                    on_click=PlotState.refit_viz,
                    size="2",
                    loading=PlotState.is_fitting_viz,
                ),
                spacing="4",
                flex_wrap="wrap",
                align="center",
            ),
        ),
    )


def plot_step() -> rx.Component:
    """3D scatter with SVD / UMAP / t-SNE, labels, and book controls."""
    return rx.vstack(
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
            tip_button(
                "Refresh plot",
                "Redraw the 3D scatter with the current settings",
                on_click=PlotState.recompute,
                size="2",
                variant="soft",
                loading=PlotState.is_fitting_viz,
            ),
            tip_button(
                rx.cond(PlotState.show_grid, "Single view", "Compare 4 views"),
                "Show SVD and t-SNE side by side. PCA and UMAP stay off until you click Fit.",
                on_click=PlotState.toggle_grid,
                size="2",
                variant="soft",
                loading=PlotState.is_fitting_viz,
            ),
            spacing="4",
            flex_wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.text(PlotState.status_message, size="2", color="gray"),
        rx.text(ExportState.status_message, size="2", color="gray"),
        rx.cond(
            PlotState.show_grid,
            rx.cond(
                PlotState.has_grid,
                rx.vstack(
                    rx.hstack(
                        tip_button(
                            "Rebuild grid",
                            "Refit SVD and t-SNE. PCA and UMAP are refit only if you already fitted them.",
                            on_click=PlotState.build_grid,
                            size="1",
                            variant="soft",
                            loading=PlotState.is_fitting_viz,
                        ),
                        rx.text(
                            "Colours, labels, and book visibility update all four views automatically.",
                            size="1",
                            color="gray",
                        ),
                        spacing="2",
                        align="center",
                        flex_wrap="wrap",
                    ),
                    rx.grid(
                        _grid_panel(
                            PANEL_PCA,
                            PlotState.grid_title_pca,
                            PlotState.figure_pca,
                            PlotState.grid_ready_pca,
                            empty=rx.vstack(
                                rx.text(
                                    PlotState.pca_skip_message,
                                    size="2",
                                    color="gray",
                                    text_align="center",
                                ),
                                tip_button(
                                    "Fit PCA",
                                    "Compute PCA for this cell (no blocking overlay)",
                                    on_click=PlotState.fit_grid_pca,
                                    size="1",
                                    variant="soft",
                                    loading=PlotState.is_fitting_pca,
                                    disabled=PlotState.is_fitting_viz,
                                ),
                                spacing="3",
                                align="center",
                            ),
                        ),
                        _grid_panel(
                            PANEL_SVD_B,
                            PlotState.grid_title_svd_b,
                            PlotState.figure_svd_b,
                            PlotState.grid_ready_svd_b,
                        ),
                        _grid_panel(
                            PANEL_UMAP,
                            PlotState.grid_title_umap,
                            PlotState.figure_umap,
                            PlotState.grid_ready_umap,
                            empty=rx.vstack(
                                rx.text(
                                    PlotState.umap_skip_message,
                                    size="2",
                                    color="gray",
                                    text_align="center",
                                ),
                                tip_button(
                                    "Fit UMAP",
                                    "Compute UMAP for this cell (heavy; no blocking overlay)",
                                    on_click=PlotState.fit_grid_umap,
                                    size="1",
                                    variant="soft",
                                    loading=PlotState.is_fitting_umap,
                                    disabled=PlotState.is_fitting_viz,
                                ),
                                spacing="3",
                                align="center",
                            ),
                        ),
                        _grid_panel(
                            PANEL_TSNE,
                            PlotState.grid_title_tsne,
                            PlotState.figure_tsne,
                            PlotState.grid_ready_tsne,
                        ),
                        # Radix's md starts at 1024px, which leaves laptops in a
                        # single column; sm (768px) is where two panels still fit.
                        columns=rx.breakpoints(initial="1", sm="2"),
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    spacing="2",
                ),
                rx.vstack(
                    rx.spinner(size="3"),
                    rx.text(
                        PlotState.status_message,
                        size="2",
                        color="gray",
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                    padding="2rem",
                ),
            ),
            rx.cond(
                PlotState.has_figure,
                rx.vstack(
                    rx.hstack(
                        plot_export_bar(kind="plot", panel=PANEL_SINGLE),
                        rx.spacer(),
                        _camera_pad(PANEL_SINGLE),
                        width="100%",
                        max_width="1100px",
                        align="center",
                        flex_wrap="wrap",
                    ),
                    rx.box(
                        rx.plotly(
                            data=PlotState.figure,
                            config=PLOT_CONFIG,
                            on_click=PlotState.on_point_click,
                            width="100%",
                        ),
                        id=plot_root_id(PANEL_SINGLE),
                        width="100%",
                        max_width="1100px",
                        margin_x="auto",
                        border="1px solid var(--gray-a6)",
                        border_radius="md",
                        padding="0.5rem",
                        overflow="hidden",
                    ),
                    width="100%",
                    spacing="2",
                    align="center",
                ),
            ),
        ),
        rx.cond(
            PlotState.plot_books.length() > 0,
            rx.vstack(
                rx.vstack(
                    rx.heading("Book coloring", size="5", weight="bold"),
                    rx.cond(
                        PlotState.color_mode == COLOR_CLUSTER,
                        rx.text(
                            "Cluster colors come from the current dendrogram cut. "
                            "Change any book by hand afterward; Reset restores "
                            "that book's cluster color. Reset colors to default "
                            "clears every hand-picked color.",
                            size="2",
                            color="gray",
                        ),
                        rx.text(
                            "Show or hide whole corpora and individual books, and "
                            "give any book its own color on the map. Reset colors "
                            "to default clears every hand-picked color.",
                            size="2",
                            color="gray",
                        ),
                    ),
                    spacing="1",
                    align="start",
                    width="100%",
                    padding_top="1rem",
                ),
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
                    tip_button(
                        "Show matching",
                        "Make search-matching books visible on the plot",
                        size="1",
                        variant="soft",
                        on_click=PlotState.show_matching_books,
                    ),
                    tip_button(
                        "Hide matching",
                        "Hide search-matching books from the plot",
                        size="1",
                        variant="soft",
                        on_click=PlotState.hide_matching_books,
                    ),
                    tip_button(
                        "Show all",
                        "Show every book on the plot again",
                        size="1",
                        variant="soft",
                        on_click=PlotState.show_all_books,
                    ),
                    tip_button(
                        "Reset colors to default",
                        "Clear every hand-picked color and restore dendrogram cluster or corpus/identity colors.",
                        size="1",
                        variant="soft",
                        on_click=PlotState.clear_all_book_colors,
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
