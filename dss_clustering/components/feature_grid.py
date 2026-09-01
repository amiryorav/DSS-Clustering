"""Shared feature-table renderer for Tables + Manual cluster results.

Uses ``rx.table`` rather than ``reflex-ag-grid``: that package still imports
``reflex.base``, which was removed in Reflex 0.9.x.
"""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.export_bar import table_export_bar
from dss_clustering.components.help import help_button, help_panel


def _feature_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(row["rank"], white_space="nowrap"),
        rx.table.cell(row["signature"], white_space="nowrap"),
        rx.table.cell(row["score"], white_space="nowrap"),
    )


def feature_grid(
    *,
    grid_id: str,
    title: str,
    rows,
    height: str = "640px",
    help_key: str | None = None,
    subtitle=None,
    export_source: str | None = None,
    export_kind: str | None = None,
) -> rx.Component:
    """Scrollable feature table (top / common / distinctive / gap).

    ``title`` stays short and single-line so the three grids in a row line up.
    ``subtitle`` carries the (possibly long) comparison detail in a fixed-height
    box, which keeps every table starting at the same vertical offset even when
    one caption wraps to two lines and another does not.
    Long signatures stay on one line; the box scrolls horizontally and
    vertically so the three side-by-side tables stay the same width.
    """
    title_row = (
        rx.hstack(
            rx.text(title, size="3", weight="bold", white_space="nowrap"),
            help_button(help_key),
            spacing="1",
            align="center",
        )
        if help_key
        else rx.text(title, size="3", weight="bold", white_space="nowrap")
    )
    children: list[rx.Component] = [title_row]
    if subtitle is not None:
        children.append(
            rx.box(
                rx.text(
                    subtitle,
                    size="1",
                    color="gray",
                    style={
                        "display": "-webkit-box",
                        "-webkit-line-clamp": "2",
                        "-webkit-box-orient": "vertical",
                        "overflow": "hidden",
                    },
                ),
                width="100%",
                height="2.4rem",
                overflow="hidden",
            )
        )
    if help_key:
        children.append(help_panel(help_key))
    if export_source and export_kind:
        children.append(table_export_bar(export_source, export_kind))
    children.append(
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("#", white_space="nowrap"),
                        rx.table.column_header_cell(
                            "Signature", white_space="nowrap"
                        ),
                        rx.table.column_header_cell("Score", white_space="nowrap"),
                    ),
                ),
                rx.table.body(rx.foreach(rows, _feature_row)),
                width="max-content",
                min_width="100%",
                variant="surface",
                size="1",
            ),
            width="100%",
            max_height=height,
            overflow_x="auto",
            overflow_y="auto",
            border="1px solid var(--gray-a6)",
            border_radius="md",
            id=grid_id,
        )
    )
    return rx.vstack(
        *children,
        width="100%",
        spacing="2",
        align="start",
    )
