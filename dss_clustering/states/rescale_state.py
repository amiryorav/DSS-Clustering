"""Rescale step: raw / tf / tfidf weighting (spec §8.4)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.pipeline.runtime import get_bundle
from dss_clustering.states.vectorize_state import VectorizeState

RESCALE_RAW = "raw"
RESCALE_TF = "tf"
RESCALE_TFIDF = "tfidf"


class RescaleState(rx.State):
    """Choose how raw counts are weighted before SVD and metrics."""

    mode: str = RESCALE_TFIDF
    status_message: str = "Build a count matrix first, then choose a weighting."
    n_nnz: int = 0
    applied: bool = False

    @rx.event
    def set_mode(self, mode: str | list[str]):
        value = mode[0] if isinstance(mode, list) else mode
        if value in (RESCALE_RAW, RESCALE_TF, RESCALE_TFIDF):
            self.mode = value
            return RescaleState.apply

    @rx.event
    async def apply(self):
        vectorize = await self.get_state(VectorizeState)
        if not vectorize.has_matrix or vectorize.is_stale:
            self.applied = False
            self.n_nnz = 0
            self.status_message = (
                "Count matrix missing or stale — rebuild Vectorize first."
            )
            return

        bundle = get_bundle(vectorize.router.session.client_token)
        if bundle is None:
            # Fall back to this state's token (same browser session).
            bundle = get_bundle(self.router.session.client_token)
        if bundle is None:
            self.applied = False
            self.n_nnz = 0
            self.status_message = "Count matrix not found in server memory — rebuild."
            return

        try:
            matrix = bundle.rescaled(self.mode)
            self.n_nnz = int(matrix.nnz)
            self.applied = True
            label = {
                RESCALE_RAW: "raw counts",
                RESCALE_TF: "term frequency (TF)",
                RESCALE_TFIDF: "TF-IDF",
            }[self.mode]
            self.status_message = (
                f"Active matrix: {label} — "
                f"{matrix.shape[0]} × {matrix.shape[1]} "
                f"({self.n_nnz:,} non-zero)."
            )
            from dss_clustering.states.svd_state import SVDState

            return SVDState.run
        except Exception as exc:  # noqa: BLE001
            self.applied = False
            self.n_nnz = 0
            self.status_message = f"Rescale failed: {exc}"
