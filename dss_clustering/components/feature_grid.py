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
        rx.table.cell(row["rank"]),
        rx.table.cell(row["signature"]),
        rx.table.cell(row["score"]),
    )


def feature_grid(
    *,
    grid_id: str,
    title: str,
    rows,
    height: str = "280px",
    help_key: str | None = None,
    export_source: str | None = None,
    export_kind: str | None = None,
) -> rx.Component:
    """Scrollable feature table (top / distinctive / gap)."""
    title_row = (
        rx.hstack(
            rx.text(title, size="3", weight="bold"),
            help_button(help_key),
            spacing="1",
            align="center",
        )
        if help_key
        else rx.text(title, size="3", weight="bold")
    )
    children: list[rx.Component] = [title_row]
    if help_key:
        children.append(help_panel(help_key))
    if export_source and export_kind:
        children.append(table_export_bar(export_source, export_kind))
    children.append(
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("#"),
                        rx.table.column_header_cell("Signature"),
                        rx.table.column_header_cell("Score"),
                    ),
                ),
                rx.table.body(rx.foreach(rows, _feature_row)),
                width="100%",
                variant="surface",
                size="1",
            ),
            width="100%",
            max_height=height,
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
