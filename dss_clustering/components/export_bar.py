"""Small export control strips for tables and plots."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.help import tip_button
from dss_clustering.export.plotly_client import export_plot_script
from dss_clustering.states.plot_state import (
    PANEL_SINGLE,
    _EXPORT_STEM,
    plot_root_id,
)


def table_export_bar(source: str, kind: str) -> rx.Component:
    """CSV / Excel / PDF buttons for one feature table panel."""
    from dss_clustering.states.export_state import ExportState

    return rx.hstack(
        rx.text("Export", size="1", color="gray"),
        tip_button(
            "CSV",
            "Download this table as CSV",
            size="1",
            variant="soft",
            on_click=ExportState.export_feature_table(source, kind, "csv"),
        ),
        tip_button(
            "Excel",
            "Download this table as Excel",
            size="1",
            variant="soft",
            on_click=ExportState.export_feature_table(source, kind, "excel"),
        ),
        tip_button(
            "PDF",
            "Download this table as PDF",
            size="1",
            variant="soft",
            on_click=ExportState.export_feature_table(source, kind, "pdf"),
        ),
        spacing="2",
        align="center",
        flex_wrap="wrap",
    )


def plot_export_bar(*, kind: str, panel: str | None = None) -> rx.Component:
    """PNG / PDF buttons that capture the on-screen Plotly view in the browser."""
    if kind == "plot":
        target = panel or PANEL_SINGLE
        root_id = plot_root_id(target)
        stem = _EXPORT_STEM.get(target, "plot")
    else:
        root_id = plot_root_id("dendrogram")
        stem = "dendrogram"
    return rx.hstack(
        rx.text("Export", size="1", color="gray"),
        tip_button(
            "PNG",
            "Download the current on-screen view as PNG",
            size="1",
            variant="soft",
            on_click=rx.call_script(export_plot_script(root_id, "png", stem)),
        ),
        tip_button(
            "PDF",
            "Download the current on-screen view as PDF",
            size="1",
            variant="soft",
            on_click=rx.call_script(export_plot_script(root_id, "pdf", stem)),
        ),
        spacing="2",
        align="center",
    )
