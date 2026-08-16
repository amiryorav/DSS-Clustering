"""Vectorize step: build book × signature count matrix (spec §8.3)."""

from __future__ import annotations

import hashlib
import json

import reflex as rx

from dss_clustering.pipeline.aggregate import (
    count_matrix_from_groups,
    signature_count_query,
)
from dss_clustering.pipeline.runtime import MatrixBundle, clear_bundle, put_bundle
from dss_clustering.states.busy_state import BusyState
from dss_clustering.states.data_state import VALID_ROW_TYPE, DataState
from dss_clustering.states.feature_state import FeatureState


def _fingerprint(
    document_ids: list[int],
    feature_mode: str,
    active_columns: list[str],
    ignore_proper_names: bool,
) -> str:
    payload = {
        "docs": sorted(document_ids),
        "mode": feature_mode,
        "cols": list(active_columns),
        "ignore": bool(ignore_proper_names),
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class VectorizeState(rx.State):
    """Automatic count-matrix build with status summary (no feature controls)."""

    is_running: bool = False
    has_matrix: bool = False
    is_stale: bool = True
    status_message: str = "Select books and features, then build the count matrix."
    progress_message: str = ""

    n_documents: int = 0
    n_signatures: int = 0
    n_source_rows: int = 0
    n_nnz: int = 0
    nnz_pct: float = 0.0
    nnz_pct_label: str = "—"
    built_fingerprint: str = ""
    built_summary: str = ""

    def _client_token(self) -> str:
        return self.router.session.client_token

    @rx.var(cache=True)
    def max_svd_components(self) -> int:
        """SVD ceiling for the built matrix — usually the book count minus one."""
        if not self.has_matrix:
            return 0
        return max(0, min(self.n_documents, self.n_signatures) - 1)

    @rx.event
    async def refresh_stale(self):
        data = await self.get_state(DataState)
        features = await self.get_state(FeatureState)
        if not data.selected_document_ids or not features.is_ready:
            self.is_stale = True
            return
        fp = _fingerprint(
            data.selected_document_ids,
            features.mode,
            list(features.active_columns),
            bool(features.should_ignore_proper_names),
        )
        self.is_stale = (not self.has_matrix) or (fp != self.built_fingerprint)

    @rx.event(background=True)
    async def build_matrix(self):
        async with self:
            data = await self.get_state(DataState)
            features = await self.get_state(FeatureState)
            doc_ids = list(data.selected_document_ids)
            active_columns = list(features.active_columns)
            feature_mode = features.mode
            ignore = bool(features.should_ignore_proper_names)
            token = self._client_token()

            if not doc_ids:
                self.status_message = (
                    "Select at least one book in Data before vectorizing."
                )
                self.has_matrix = False
                self.is_stale = True
                return
            if not active_columns:
                self.status_message = (
                    "Select feature columns in Features before vectorizing."
                )
                self.has_matrix = False
                self.is_stale = True
                return

            busy = await self.get_state(BusyState)
            busy.begin("Building the count matrix…")
            self.is_running = True
            self.progress_message = (
                f"Aggregating signature counts for {len(doc_ids)} books…"
            )
            self.status_message = self.progress_message

        try:
            # Grouping in the database keeps memory proportional to the matrix's
            # non-zero count instead of the corpus row count.
            with rx.session() as session:
                groups = session.exec(
                    signature_count_query(
                        doc_ids,
                        active_columns,
                        row_type=VALID_ROW_TYPE,
                        ignore_proper_names=ignore,
                    )
                ).all()

            async with self:
                self.progress_message = (
                    f"Assembling matrix from {len(groups):,} signature groups…"
                )
                self.status_message = self.progress_message

            if not groups:
                async with self:
                    clear_bundle(token)
                    self.has_matrix = False
                    self.is_stale = True
                    self.n_documents = 0
                    self.n_signatures = 0
                    self.n_source_rows = 0
                    self.n_nnz = 0
                    self.nnz_pct = 0.0
                    self.nnz_pct_label = "—"
                    self.built_fingerprint = ""
                    self.built_summary = ""
                    self.status_message = (
                        "No valid lemma rows found for the selected books."
                    )
                    self.progress_message = ""
                    self.is_running = False
                    (await self.get_state(BusyState)).end()
                return

            matrix, out_doc_ids, signatures, n_source = count_matrix_from_groups(
                groups, doc_ids
            )
            del groups
            fp = _fingerprint(doc_ids, feature_mode, active_columns, ignore)
            put_bundle(
                token,
                MatrixBundle(
                    count_matrix=matrix,
                    document_ids=out_doc_ids,
                    signatures=signatures,
                    n_source_rows=n_source,
                    fingerprint=fp,
                    feature_mode=feature_mode,
                    active_columns=tuple(active_columns),
                    ignore_proper_names=ignore,
                ),
            )

            cols = ", ".join(active_columns)
            async with self:
                self.has_matrix = True
                self.is_stale = False
                self.n_documents = int(matrix.shape[0])
                self.n_signatures = int(matrix.shape[1])
                self.n_source_rows = int(n_source)
                self.n_nnz = int(matrix.nnz)
                total_cells = self.n_documents * self.n_signatures
                self.nnz_pct = (
                    round(100.0 * self.n_nnz / total_cells, 2) if total_cells else 0.0
                )
                self.nnz_pct_label = f"{self.nnz_pct:.2f}%"
                self.built_fingerprint = fp
                self.built_summary = (
                    f"{feature_mode} · {cols}"
                    + (" · ignore proper-name" if ignore else "")
                )
                self.status_message = (
                    f"Built {self.n_documents} × {self.n_signatures} count matrix "
                    f"from {self.n_source_rows:,} valid rows "
                    f"({self.n_nnz:,} non-zeros, {self.nnz_pct_label})."
                )
                self.progress_message = ""
                self.is_running = False
                from dss_clustering.states.rescale_state import RescaleState

                # Release last so the overlay stays up for the whole
                # rescale → SVD → dendrogram chain.
                return [RescaleState.apply, BusyState.release]
        except Exception as exc:  # noqa: BLE001 — surfaced in UI
            async with self:
                clear_bundle(token)
                self.has_matrix = False
                self.is_stale = True
                self.status_message = f"Vectorize failed: {exc}"
                self.progress_message = ""
                self.is_running = False
                (await self.get_state(BusyState)).end()
