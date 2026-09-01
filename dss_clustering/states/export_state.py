"""Per-panel table export (spec §8.11, localhost — no activity DB).

Plot PNG/PDF downloads run in the browser via Plotly.toImage so Cloud VMs
do not need Chromium/Kaleido.
"""

from __future__ import annotations

import reflex as rx

from dss_clustering.export.writers import (
    write_count_matrix_csv,
    write_excel_side_by_side,
    write_table,
)


class ExportState(rx.State):
    """Generate downloadable files for the current table view."""

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
    async def export_all_feature_tables(self):
        """Download top, common, distinctive, and gap tables side by side."""
        from dss_clustering.states.table_state import TableState

        table = await self.get_state(TableState)
        blocks = [
            {
                "title": "Top features",
                "subtitle": table.top_subtitle,
                "rows": list(table.filtered_top_rows),
            },
            {
                "title": "Common features",
                "subtitle": table.common_subtitle,
                "rows": list(table.filtered_common_rows),
            },
            {
                "title": "Distinctive",
                "subtitle": table.distinctive_subtitle,
                "rows": list(table.filtered_distinctive_rows),
            },
            {
                "title": "Gap",
                "subtitle": table.gap_subtitle,
                "rows": list(table.filtered_gap_rows),
            },
        ]
        if not any(block["rows"] for block in blocks):
            self.status_message = "Nothing to export — run Compare first."
            return
        try:
            data, filename, mime = write_excel_side_by_side(
                blocks,
                f"tables_all_{table.export_slug}",
            )
            self.status_message = f"Downloading {filename}"
            return rx.download(data=data, filename=filename, mime_type=mime)
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Export failed: {exc}"

    async def _resolve_feature_rows(
        self, source: str, kind: str
    ) -> tuple[list[dict], str, str]:
        titles = {
            "top": "Top features",
            "common": "Common features",
            "distinctive": "Distinctive features",
            "gap": "Gap features",
        }
        title = titles.get(kind, kind)
        if source == "tables":
            from dss_clustering.states.table_state import TableState

            table = await self.get_state(TableState)
            mapping = {
                "top": table.filtered_top_rows,
                "common": table.filtered_common_rows,
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
