"""Dendrogram step: hierarchical clustering on the SVD embedding (spec §8.7)."""

from __future__ import annotations

import reflex as rx
from plotly.graph_objects import Figure

from dss_clustering.pipeline.dendrogram import (
    LINKAGE_AVERAGE,
    LINKAGE_WARD,
    METRIC_COSINE,
    METRIC_EUCLIDEAN,
    cluster_palette,
    clusters_as_dict,
    cut_clusters,
    default_cut_height,
    figure_min_width,
    fit_linkage,
    make_dendrogram_figure,
    max_cut_height,
)
from dss_clustering.pipeline.runtime import (
    DendrogramBundle,
    clear_dendrogram,
    get_dendrogram,
    get_embedding,
    put_dendrogram,
)
from dss_clustering.pipeline.metrics import (
    ward_artifact_document_ids as find_ward_artifact_document_ids,
)
from dss_clustering.states.busy_state import BusyState
from dss_clustering.states.data_state import FALLBACK_COLOR, DataState
from dss_clustering.states.svd_state import SVDState


class DendrogramState(rx.State):
    """Ward / average dendrogram with live cut-height reclustering."""

    linkage_method: str = LINKAGE_WARD
    distance_metric: str = METRIC_EUCLIDEAN
    cut_height: float = 1.0
    # Slider position while dragging; only committed on release.
    cut_height_draft: float = 1.0
    max_height: float = 1.0

    is_running: bool = False
    has_tree: bool = False
    n_clusters: int = 0
    n_documents: int = 0
    ward_artifact_document_ids: list[int] = []
    leaf_document_ids: list[int] = []
    leaf_trace_index: int = -1
    # Only morphological.py marked Ward artifacts; lemma.py never did, and in
    # lemma space the criterion flags ~25% of books. FeatureState.set_mode flips
    # this with the mode.
    mark_ward_artifacts: bool = False
    # document_id str → cluster id
    cluster_of: dict[str, int] = {}
    # cluster id str → color
    cluster_color: dict[str, str] = {}
    status_message: str = "Run SVD to build the dendrogram."
    figure: Figure = Figure()
    # CSS min-width so leaf labels stay legible; the box scrolls past it.
    figure_min_width: str = "100%"

    def _token(self) -> str:
        return self.router.session.client_token

    @rx.var(cache=True)
    def metric_locked(self) -> bool:
        return self.linkage_method == LINKAGE_WARD

    @rx.event
    def set_linkage(self, method: str | list[str]):
        value = method[0] if isinstance(method, list) else method
        if value not in (LINKAGE_WARD, LINKAGE_AVERAGE):
            return
        self.linkage_method = value
        if value == LINKAGE_WARD:
            self.distance_metric = METRIC_EUCLIDEAN
        return DendrogramState.refit

    @rx.event
    def set_mark_ward_artifacts(self, value: bool):
        self.mark_ward_artifacts = bool(value)
        return DendrogramState.refit

    @rx.event
    def set_metric(self, metric: str | list[str]):
        if self.linkage_method == LINKAGE_WARD:
            self.distance_metric = METRIC_EUCLIDEAN
            return
        value = metric[0] if isinstance(metric, list) else metric
        if value in (METRIC_EUCLIDEAN, METRIC_COSINE):
            self.distance_metric = value
            return DendrogramState.refit

    def _clamp_height(
        self, value: list[float | int] | float | int | str
    ) -> float | None:
        raw = value[0] if isinstance(value, list) else value
        try:
            h = float(raw)
        except (TypeError, ValueError):
            return None
        return max(0.0, min(h, self.max_height))

    @rx.event
    def set_cut_height_draft(self, value: list[float | int] | float | int | str):
        """Track the thumb while dragging without touching the clustering."""
        h = self._clamp_height(value)
        if h is not None:
            self.cut_height_draft = h

    @rx.event
    def set_cut_height(self, value: list[float | int] | float | int | str):
        """Slider release: cut-height only recolors (no Z refit)."""
        h = self._clamp_height(value)
        if h is None:
            return
        self.cut_height_draft = h
        if h == self.cut_height:
            return
        self.cut_height = h
        return DendrogramState.recolor

    @rx.event
    async def refit(self):
        """Fit linkage from the current SVD embedding and draw the tree."""
        svd = await self.get_state(SVDState)
        data = await self.get_state(DataState)
        token = self._token()

        if not svd.has_embedding:
            clear_dendrogram(token)
            self.has_tree = False
            self.figure = Figure()
            self.cluster_of = {}
            self.cluster_color = {}
            self.n_clusters = 0
            self.n_documents = 0
            self.ward_artifact_document_ids = []
            self.status_message = "Run SVD to build the dendrogram."
            return

        emb = get_embedding(token) or get_embedding(svd.router.session.client_token)
        if emb is None:
            clear_dendrogram(token)
            self.has_tree = False
            self.figure = Figure()
            self.status_message = "Embedding not found — re-run SVD."
            return

        if emb.embedding.shape[0] < 2:
            clear_dendrogram(token)
            self.has_tree = False
            self.figure = Figure()
            self.status_message = "Need at least 2 books for a dendrogram."
            return

        busy = await self.get_state(BusyState)
        busy.begin("Fitting hierarchical clustering…")
        self.is_running = True
        self.status_message = "Fitting hierarchical clustering…"
        # Flush before the blocking scipy call so the overlay is already up.
        yield

        try:
            method = self.linkage_method
            metric = (
                METRIC_EUCLIDEAN
                if method == LINKAGE_WARD
                else self.distance_metric
            )
            Z = fit_linkage(emb.embedding, method=method, metric=metric)
            self.ward_artifact_document_ids = (
                sorted(
                    find_ward_artifact_document_ids(
                        emb.embedding,
                        Z,
                        list(emb.document_ids),
                    )
                )
                if method == LINKAGE_WARD and self.mark_ward_artifacts
                else []
            )
            put_dendrogram(
                token,
                DendrogramBundle(
                    Z=Z,
                    document_ids=list(emb.document_ids),
                    linkage_method=method,
                    distance_metric=metric,
                    fingerprint=emb.fingerprint,
                ),
            )
            self.max_height = max_cut_height(Z)
            # Keep prior cut if still in range; otherwise pick a default.
            if self.cut_height <= 0 or self.cut_height > self.max_height:
                self.cut_height = default_cut_height(Z)
            else:
                self.cut_height = min(self.cut_height, self.max_height)
            self.cut_height_draft = self.cut_height

            self.has_tree = True
            self.n_documents = len(emb.document_ids)
            self.is_running = False
            yield DendrogramState.recolor
            yield BusyState.release
        except Exception as exc:  # noqa: BLE001
            clear_dendrogram(token)
            self.has_tree = False
            self.figure = Figure()
            self.cluster_of = {}
            self.cluster_color = {}
            self.n_clusters = 0
            self.ward_artifact_document_ids = []
            self.status_message = f"Dendrogram failed: {exc}"
            self.is_running = False
            busy.end()

    @rx.event
    def on_leaf_click(self, event_data):
        """Toggle the clicked leaf into the manual cluster selection."""
        from dss_clustering.pipeline.clicks import (
            extract_clicked_curve_number,
            extract_clicked_document_id,
            extract_clicked_point_number,
        )
        from dss_clustering.states.manual_cluster_state import ManualClusterState

        doc_id = extract_clicked_document_id(event_data)
        if doc_id is None:
            curve_number = extract_clicked_curve_number(event_data)
            point_number = extract_clicked_point_number(event_data)
            if (
                curve_number == self.leaf_trace_index
                and point_number is not None
                and 0 <= point_number < len(self.leaf_document_ids)
            ):
                doc_id = self.leaf_document_ids[point_number]
        if doc_id is None:
            return
        return ManualClusterState.toggle_document(doc_id)

    @rx.event
    async def recolor(self):
        """Apply cut height via fcluster and redraw — does not refit Z."""
        busy = await self.get_state(BusyState)
        busy.begin("Recomputing clusters…")
        yield

        try:
            drawn = await self._redraw()
        except Exception:
            busy.end()
            raise
        if not drawn:
            busy.end()
            return

        from dss_clustering.states.plot_state import PlotState
        from dss_clustering.states.table_state import TableState

        yield PlotState.refresh_visible_plots
        yield TableState.recompute
        yield BusyState.release

    @rx.event
    async def refresh_colors(self):
        """A book's identity color changed on the 3D plot — redraw the leaves.

        Skips the plot recompute: the caller already redraws the 3D plot.
        """
        if not self.has_tree:
            return
        await self._redraw()

    async def _redraw(self) -> bool:
        """Cut, color and draw the tree from the stored linkage. True on success."""
        data = await self.get_state(DataState)
        token = self._token()
        bundle = get_dendrogram(token)
        if bundle is None:
            self.has_tree = False
            self.figure = Figure()
            self.status_message = "No dendrogram tree — run SVD / refit."
            return False

        Z = bundle.Z
        doc_ids = list(bundle.document_ids)
        cluster_ids = cut_clusters(Z, self.cut_height)
        unique = sorted({int(c) for c in cluster_ids})
        palette = cluster_palette(len(unique))
        color_by_cluster = {
            cid: palette[i] for i, cid in enumerate(unique)
        }

        leaf_labels: list[str] = []
        leaf_colors: list[str] = []
        for doc_id in doc_ids:
            key = str(doc_id)
            short = data.document_books.get(key) or data.document_labels.get(
                key, key
            )
            leaf_labels.append(short)
            corpus = data.document_corpus.get(key, "")
            leaf_colors.append(
                data.document_color_override.get(key)
                or data.corpus_default_color.get(corpus, FALLBACK_COLOR)
            )

        try:
            self.figure = make_dendrogram_figure(
                Z,
                document_ids=doc_ids,
                leaf_labels=leaf_labels,
                leaf_identity_colors=leaf_colors,
                cluster_ids=cluster_ids,
                cluster_colors=color_by_cluster,
                cut_height=self.cut_height,
                ward_artifact_document_ids=set(self.ward_artifact_document_ids),
            )
            leaf_customdata = self.figure.data[-1].customdata
            self.leaf_document_ids = [
                int(row[0]) for row in leaf_customdata
            ]
            self.leaf_trace_index = len(self.figure.data) - 1
            self.figure_min_width = f"{figure_min_width(len(doc_ids))}px"
            self.cluster_of = clusters_as_dict(doc_ids, cluster_ids)
            self.cluster_color = {
                str(cid): color for cid, color in color_by_cluster.items()
            }
            self.n_clusters = len(unique)
            self.n_documents = len(doc_ids)
            self.has_tree = True
            artifact_note = (
                f"; {len(self.ward_artifact_document_ids)} gray-italic Ward artifacts"
                if bundle.linkage_method == LINKAGE_WARD and self.mark_ward_artifacts
                else ""
            )
            self.status_message = (
                f"{bundle.linkage_method}/{bundle.distance_metric} dendrogram — "
                f"{self.n_clusters} clusters at cut {self.cut_height:.3f} "
                f"({self.n_documents} books{artifact_note})."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self.has_tree = False
            self.figure = Figure()
            self.status_message = f"Dendrogram draw failed: {exc}"
            return False
