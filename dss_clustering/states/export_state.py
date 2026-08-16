"""Per-panel table/plot export (spec §8.11, localhost — no activity DB)."""

from __future__ import annotations

from copy import deepcopy

import reflex as rx
from plotly.graph_objects import Figure

from dss_clustering.export.writers import (
    write_count_matrix_csv,
    write_plot_image,
    write_table,
)


class ExportState(rx.State):
    """Generate downloadable files for the current table or plot view."""

    status_message: str = ""

    @rx.event
    async def export_count_matrix(self):
        """Download the current unscaled book × signature matrix as CSV."""
        from dss_clustering.pipeline.runtime import get_bundle
        from dss_clustering.states.data_state import DataState

        bundle = get_bundle(self.router.session.client_token)
        if bundle is None:
            self.status_message = "Build the count matrix before exporting it."
            return
        data_state = await self.get_state(DataState)
        labels = {
            int(document_id): data_state.document_books.get(str(document_id))
            or data_state.document_labels.get(str(document_id), str(document_id))
            for document_id in bundle.document_ids
        }
        signatures = (
            [
                signature.removeprefix("clean_lemma=")
                for signature in bundle.signatures
            ]
            if bundle.feature_mode == "lemma"
            else bundle.signatures
        )
        try:
            data, filename, mime = write_count_matrix_csv(
                bundle.count_matrix,
                bundle.document_ids,
                signatures,
                f"raw_count_matrix_{bundle.feature_mode}",
                document_labels=labels,
            )
            self.status_message = f"Downloading {filename}"
            return rx.download(data=data, filename=filename, mime_type=mime)
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Count-matrix export failed: {exc}"

    @rx.event
    async def export_feature_table(self, source: str, kind: str, fmt: str):
        rows, stem, title = await self._resolve_feature_rows(source, kind)
        if not rows:
            self.status_message = f"Nothing to export for {kind}."
            return
        try:
            data, filename, mime = write_table(rows, fmt, stem, title=title)
            self.status_message = f"Downloading {filename}"
            return rx.download(data=data, filename=filename, mime_type=mime)
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Export failed: {exc}"

    @rx.event
    async def export_plot(self, fmt: str):
        from dss_clustering.states.plot_state import PlotState

        plot = await self.get_state(PlotState)
        if not plot.has_figure:
            self.status_message = "No 3D plot to export."
            return
        figure = deepcopy(plot.figure)
        if plot.camera:
            figure.update_layout(scene_camera=plot.camera)
        return self._download_figure(figure, f"plot_{plot.method}", fmt)

    @rx.event
    async def export_dendrogram(self, fmt: str):
        from dss_clustering.pipeline.dendrogram import figure_min_width
        from dss_clustering.states.dendrogram_state import DendrogramState

        dendro = await self.get_state(DendrogramState)
        if not dendro.has_tree:
            self.status_message = "No dendrogram to export."
            return
        # The interactive chart scrolls horizontally, but a static export does
        # not. Give each leaf the same horizontal room it receives on screen.
        width = max(1600, figure_min_width(dendro.n_documents))
        height = max(900, int(dendro.figure.layout.height or 800))
        download = self._download_figure(
            dendro.figure, "dendrogram", fmt, width=width, height=height
        )
        # The browser download is sufficient feedback; avoid leaving a noisy
        # timestamped "Downloading …" line under the chart.
        if not self.status_message.startswith("Plot export failed:"):
            self.status_message = ""
        return download

    def _download_figure(
        self,
        fig: Figure,
        stem: str,
        fmt: str,
        *,
        width: int = 1200,
        height: int = 800,
    ):
        try:
            data, filename, mime = write_plot_image(
                fig, stem, fmt, width=width, height=height
            )
            self.status_message = f"Downloading {filename}"
            return rx.download(data=data, filename=filename, mime_type=mime)
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Plot export failed: {exc}"

    async def _resolve_feature_rows(
        self, source: str, kind: str
    ) -> tuple[list[dict], str, str]:
        titles = {
            "top": "Top features",
            "distinctive": "Distinctive features",
            "gap": "Gap features",
        }
        title = titles.get(kind, kind)
        if source == "tables":
            from dss_clustering.states.table_state import TableState

            table = await self.get_state(TableState)
            mapping = {
                "top": table.filtered_top_rows,
                "distinctive": table.filtered_distinctive_rows,
                "gap": table.filtered_gap_rows,
            }
            rows = list(mapping.get(kind, []))
            stem = f"tables_{kind}_{table.export_slug}"
            return rows, stem, title
        if source == "manual":
            from dss_clustering.states.manual_cluster_state import ManualClusterState

            manual = await self.get_state(ManualClusterState)
            mapping = {
                "top": manual.top_rows,
                "distinctive": manual.distinctive_rows,
                "gap": manual.gap_rows,
            }
            rows = list(mapping.get(kind, []))
            stem = f"manual_{kind}"
            return rows, stem, title
        return [], kind, title
