"""Small export control strips for tables and plots."""

from __future__ import annotations

import reflex as rx

from dss_clustering.states.export_state import ExportState


def table_export_bar(source: str, kind: str) -> rx.Component:
    """CSV / Excel / PDF buttons for one feature table panel."""
    return rx.hstack(
        rx.text("Export", size="1", color="gray"),
        rx.button(
            "CSV",
            size="1",
            variant="soft",
            on_click=ExportState.export_feature_table(source, kind, "csv"),
        ),
        rx.button(
            "Excel",
            size="1",
            variant="soft",
            on_click=ExportState.export_feature_table(source, kind, "excel"),
        ),
        rx.button(
            "PDF",
            size="1",
            variant="soft",
            on_click=ExportState.export_feature_table(source, kind, "pdf"),
        ),
        spacing="2",
        align="center",
        flex_wrap="wrap",
    )


def plot_export_bar(*, kind: str) -> rx.Component:
    """PNG / PDF buttons for a Plotly figure panel."""
    on_png = (
        ExportState.export_plot("png")
        if kind == "plot"
        else ExportState.export_dendrogram("png")
    )
    on_pdf = (
        ExportState.export_plot("pdf")
        if kind == "plot"
        else ExportState.export_dendrogram("pdf")
    )
    return rx.hstack(
        rx.text("Export", size="1", color="gray"),
        rx.button("PNG", size="1", variant="soft", on_click=on_png),
        rx.button("PDF", size="1", variant="soft", on_click=on_pdf),
        spacing="2",
        align="center",
    )
