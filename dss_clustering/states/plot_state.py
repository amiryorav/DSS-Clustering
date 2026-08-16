"""3D plot step: SVD / UMAP / t-SNE scatter (spec §8.6)."""

from __future__ import annotations

import reflex as rx
from plotly.graph_objects import Figure

from dss_clustering.pipeline.plotting import make_3d_scatter
from dss_clustering.pipeline.runtime import (
    VizEmbeddingBundle,
    get_bundle,
    get_embedding,
    get_viz,
    put_viz,
)
from dss_clustering.pipeline.viz import fit_tsne, fit_umap, viz_params_key
from dss_clustering.states.busy_state import BusyState
from dss_clustering.states.data_state import (
    CORPUS_LABELS,
    CORPUS_ORDER,
    FALLBACK_COLOR,
    DataState,
)
from dss_clustering.states.rescale_state import RescaleState
from dss_clustering.states.svd_state import SVDState

LABEL_SHORT = "short"
LABEL_HIDDEN = "hidden"
COLOR_IDENTITY = "identity"
COLOR_CLUSTER = "cluster"
METHOD_SVD = "svd"
METHOD_UMAP = "umap"
METHOD_TSNE = "tsne"

# Reads the live gl3d camera from the rendered figure (null before first draw).
CAMERA_SNIPPET = """
(() => {
  const gd = document.querySelector('.js-plotly-plot');
  const cam = gd && gd._fullLayout && gd._fullLayout.scene
    ? gd._fullLayout.scene.camera
    : null;
  return cam ? JSON.parse(JSON.stringify(cam)) : null;
})()
"""

# Wait for two browser paint frames after enabling the blocking overlay before
# asking the backend to begin CPU-heavy dimensionality reduction.
WAIT_FOR_BUSY_PAINT = """
new Promise((resolve) => {
  requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)));
})
"""


class PlotState(rx.State):
    """Interactive 3D scatter — SVD (analysis) or UMAP/t-SNE (viz-only)."""

    method: str = METHOD_SVD
    color_mode: str = COLOR_IDENTITY
    dim_x: int = 0
    dim_y: int = 1
    dim_z: int = 2
    label_mode: str = LABEL_SHORT
    hidden_document_ids: list[str] = []
    visible_document_ids: list[int] = []
    plot_books: list[dict] = []
    book_search: str = ""
    # Browser camera, read on demand so exports match the on-screen view.
    camera: dict = {}
    pending_export_format: str = "png"

    # UMAP / t-SNE hyperparameters
    umap_n_neighbors: int = 15
    umap_min_dist: float = 0.1
    tsne_perplexity: float = 30.0
    is_fitting_viz: bool = False

    figure: Figure = Figure()
    has_figure: bool = False
    status_message: str = "Run SVD to generate the 3D plot."
    max_dim_index: int = 0

    @rx.var(cache=True)
    def is_svd_method(self) -> bool:
        return self.method == METHOD_SVD

    @rx.var(cache=True)
    def is_umap_method(self) -> bool:
        return self.method == METHOD_UMAP

    @rx.var(cache=True)
    def is_tsne_method(self) -> bool:
        return self.method == METHOD_TSNE

    @rx.var(cache=True)
    def filtered_plot_books(self) -> list[dict]:
        q = self.book_search.strip().lower()
        if not q:
            return self.plot_books
        return [
            b
            for b in self.plot_books
            if q in str(b["short"]).lower()
            or q in str(b["label"]).lower()
            or q in str(b.get("corpus", "")).lower()
        ]

    @rx.var(cache=True)
    def plot_corpora(self) -> list[dict]:
        by_corpus: dict[str, list[dict]] = {}
        for book in self.plot_books:
            corpus = str(book.get("corpus", "")) or "unknown"
            by_corpus.setdefault(corpus, []).append(book)

        ordered = [c for c in CORPUS_ORDER if c in by_corpus]
        ordered += sorted(c for c in by_corpus if c not in CORPUS_ORDER)

        rows: list[dict] = []
        for corpus in ordered:
            books = by_corpus[corpus]
            n_visible = sum(1 for b in books if b["visible"])
            rows.append(
                {
                    "corpus": corpus,
                    "label": CORPUS_LABELS.get(corpus, corpus.title()),
                    "all_visible": n_visible == len(books) and len(books) > 0,
                    "n_visible": n_visible,
                    "n_total": len(books),
                }
            )
        return rows

    @rx.var(cache=True)
    def hidden_count(self) -> int:
        return len(self.hidden_document_ids)

    @rx.event
    def set_book_search(self, value: str):
        self.book_search = value

    @rx.event
    def set_method(self, method: str | list[str]):
        value = method[0] if isinstance(method, list) else method
        if value in (METHOD_SVD, METHOD_UMAP, METHOD_TSNE):
            self.method = value
            return (
                PlotState.recompute
                if value == METHOD_SVD
                else PlotState.refit_viz
            )

    @rx.event
    def set_color_mode(self, mode: str | list[str]):
        value = mode[0] if isinstance(mode, list) else mode
        if value in (COLOR_IDENTITY, COLOR_CLUSTER):
            self.color_mode = value
            return PlotState.recompute

    @rx.event
    def set_dim_x(self, value: str):
        try:
            self.dim_x = max(0, int(value))
        except (TypeError, ValueError):
            return
        return PlotState.recompute

    @rx.event
    def set_dim_y(self, value: str):
        try:
            self.dim_y = max(0, int(value))
        except (TypeError, ValueError):
            return
        return PlotState.recompute

    @rx.event
    def set_dim_z(self, value: str):
        try:
            self.dim_z = max(0, int(value))
        except (TypeError, ValueError):
            return
        return PlotState.recompute

    @rx.event
    def set_label_mode(self, mode: str | list[str]):
        value = mode[0] if isinstance(mode, list) else mode
        if value in (LABEL_SHORT, LABEL_HIDDEN):
            self.label_mode = value
            return PlotState.recompute

    @rx.event
    def set_umap_n_neighbors(self, value: str):
        try:
            self.umap_n_neighbors = max(2, int(value))
        except (TypeError, ValueError):
            return

    @rx.event
    def set_umap_min_dist(self, value: str):
        try:
            self.umap_min_dist = max(0.0, float(value))
        except (TypeError, ValueError):
            return

    @rx.event
    def set_tsne_perplexity(self, value: str):
        try:
            self.tsne_perplexity = max(5.0, float(value))
        except (TypeError, ValueError):
            return

    @rx.event
    async def refit_viz(self):
        """Paint the blocking overlay before starting a UMAP/t-SNE fit."""
        busy = await self.get_state(BusyState)
        busy.begin(f"Fitting {self.method.upper()} projection…")
        self.is_fitting_viz = True
        return rx.call_script(
            WAIT_FOR_BUSY_PAINT,
            callback=PlotState.run_viz_refit,
        )

    @rx.event(background=True)
    async def run_viz_refit(self, _painted: bool = True):
        """Fit in the background so the browser can keep rendering the overlay."""
        try:
            async with self:
                await self._recompute()
        finally:
            async with self:
                self.is_fitting_viz = False
                busy = await self.get_state(BusyState)
                busy.end()

    @rx.event
    def on_point_click(self, event_data):
        """Start a new manual group if needed, then toggle the clicked book."""
        from dss_clustering.pipeline.clicks import (
            extract_clicked_document_id,
            extract_clicked_point_number,
        )
        from dss_clustering.states.manual_cluster_state import ManualClusterState

        doc_id = extract_clicked_document_id(event_data)
        if doc_id is None:
            point_number = extract_clicked_point_number(event_data)
            if point_number is not None and 0 <= point_number < len(
                self.visible_document_ids
            ):
                doc_id = self.visible_document_ids[point_number]
        if doc_id is None:
            return
        # Return a normal cross-state event instead of mutating another state
        # through async get_state; the latter can produce an invalid frontend
        # callback after Plotly emits a click.
        return ManualClusterState.toggle_document(doc_id)

    @rx.event
    def export_with_camera(self, fmt: str):
        """Read the live camera out of the browser, then render the export.

        Subscribing to Plotly's relayout events instead would push a state
        update per rotation frame, and each one re-ran ``Plotly.react`` — a full
        gl3d scene rebuild that re-vectorizes every text label and stalls the
        main thread. Asking for the camera once per export keeps interaction on
        the client where it belongs.
        """
        self.pending_export_format = "pdf" if str(fmt).lower() == "pdf" else "png"
        return rx.call_script(
            CAMERA_SNIPPET,
            callback=PlotState.finish_export_with_camera,
        )

    @rx.event
    async def finish_export_with_camera(self, camera):
        """Store the browser camera, then hand off to the export writer."""
        from dss_clustering.states.export_state import ExportState

        if isinstance(camera, dict) and camera:
            self.camera = camera
        return ExportState.export_plot(self.pending_export_format)

    @rx.event
    def toggle_book_visibility(self, document_id: int):
        key = str(document_id)
        if key in self.hidden_document_ids:
            self.hidden_document_ids = [
                k for k in self.hidden_document_ids if k != key
            ]
        else:
            self.hidden_document_ids = [*self.hidden_document_ids, key]
        return PlotState.recompute

    @rx.event
    def show_all_books(self):
        self.hidden_document_ids = []
        return PlotState.recompute

    @rx.event
    def show_matching_books(self):
        matched = {str(b["id"]) for b in self.filtered_plot_books}
        self.hidden_document_ids = [
            k for k in self.hidden_document_ids if k not in matched
        ]
        return PlotState.recompute

    @rx.event
    def hide_matching_books(self):
        matched = {str(b["id"]) for b in self.filtered_plot_books}
        self.hidden_document_ids = sorted(set(self.hidden_document_ids) | matched)
        return PlotState.recompute

    @rx.event
    def toggle_corpus_visibility(self, corpus: str):
        ids = [
            str(b["id"])
            for b in self.plot_books
            if str(b.get("corpus", "")) == corpus
        ]
        if not ids:
            return
        hidden = set(self.hidden_document_ids)
        if all(i not in hidden for i in ids):
            self.hidden_document_ids = sorted(hidden | set(ids))
        else:
            remove = set(ids)
            self.hidden_document_ids = [
                k for k in self.hidden_document_ids if k not in remove
            ]
        return PlotState.recompute

    @rx.event
    async def set_book_color(self, document_id: int, color: str):
        data = await self.get_state(DataState)
        data.document_color_override = {
            **data.document_color_override,
            str(document_id): color,
        }
        return self._identity_color_changed()

    @rx.event
    async def clear_book_color(self, document_id: int):
        data = await self.get_state(DataState)
        overrides = dict(data.document_color_override)
        overrides.pop(str(document_id), None)
        data.document_color_override = overrides
        return self._identity_color_changed()

    def _identity_color_changed(self):
        """Identity colors feed both the 3D plot and the dendrogram leaves."""
        from dss_clustering.states.dendrogram_state import DendrogramState

        return [PlotState.recompute, DendrogramState.refresh_colors]

    async def _coords_and_docs(self, token: str, svd: SVDState, rescale: RescaleState):
        """Return (coords ndarray n×d, document_ids, axis_titles, method_note)."""
        if self.method == METHOD_SVD:
            emb = get_embedding(token) or get_embedding(
                svd.router.session.client_token
            )
            if emb is None:
                return None, None, None, "Embedding not found — re-run SVD."
            X = emb.embedding
            n_dims = int(X.shape[1])
            self.max_dim_index = max(0, n_dims - 1)
            if n_dims < 1:
                return None, None, None, "Embedding has no dimensions to plot."

            def _clamp(i: int) -> int:
                return min(max(0, i), n_dims - 1)

            ix, iy, iz = _clamp(self.dim_x), _clamp(self.dim_y), _clamp(self.dim_z)
            self.dim_x, self.dim_y, self.dim_z = ix, iy, iz
            coords = X[:, [ix, iy, iz]]
            titles = (f"Dim {ix}", f"Dim {iy}", f"Dim {iz}")
            return coords, list(emb.document_ids), titles, f"SVD dims {ix},{iy},{iz}"

        # UMAP / t-SNE from rescaled matrix
        if not rescale.applied:
            return None, None, None, "Apply Rescale before UMAP / t-SNE."
        bundle = get_bundle(token)
        if bundle is None:
            return None, None, None, "Count matrix missing — rebuild Vectorize."

        params_key = viz_params_key(
            self.method,
            n_neighbors=self.umap_n_neighbors,
            min_dist=self.umap_min_dist,
            perplexity=self.tsne_perplexity,
            rescale_mode=rescale.mode,
        )
        cached = get_viz(token)
        if (
            cached is not None
            and cached.method == self.method
            and cached.params_key == params_key
            and cached.fingerprint == bundle.fingerprint
            and list(cached.document_ids) == list(bundle.document_ids)
        ):
            coords = cached.coords
        else:
            self.is_fitting_viz = True
            matrix = bundle.rescaled(rescale.mode)
            if self.method == METHOD_UMAP:
                coords = fit_umap(
                    matrix,
                    n_neighbors=self.umap_n_neighbors,
                    min_dist=self.umap_min_dist,
                    n_components=3,
                )
            else:
                coords = fit_tsne(
                    matrix,
                    perplexity=self.tsne_perplexity,
                    n_components=3,
                )
            put_viz(
                token,
                VizEmbeddingBundle(
                    coords=coords,
                    document_ids=list(bundle.document_ids),
                    method=self.method,
                    params_key=params_key,
                    fingerprint=bundle.fingerprint,
                ),
            )
            self.is_fitting_viz = False

        self.max_dim_index = 2
        self.dim_x, self.dim_y, self.dim_z = 0, 1, 2
        titles = (f"{self.method.upper()}-1", f"{self.method.upper()}-2", f"{self.method.upper()}-3")
        note = (
            f"UMAP (nn={self.umap_n_neighbors}, min_dist={self.umap_min_dist})"
            if self.method == METHOD_UMAP
            else f"t-SNE (perplexity={self.tsne_perplexity})"
        )
        return coords, list(bundle.document_ids), titles, note

    @rx.event
    async def recompute(self):
        # Only UMAP / t-SNE can block long enough to need the overlay.
        if self.method == METHOD_SVD:
            await self._recompute()
            return
        busy = await self.get_state(BusyState)
        busy.begin(f"Fitting {self.method.upper()} projection…")
        yield
        try:
            await self._recompute()
        finally:
            busy.end()

    async def _recompute(self):
        svd = await self.get_state(SVDState)
        rescale = await self.get_state(RescaleState)
        data = await self.get_state(DataState)
        token = self.router.session.client_token

        # Cluster colors (optional)
        cluster_of: dict[str, int] = {}
        cluster_color: dict[str, str] = {}
        try:
            from dss_clustering.states.dendrogram_state import DendrogramState

            dendro = await self.get_state(DendrogramState)
            if dendro.has_tree:
                cluster_of = dict(dendro.cluster_of)
                cluster_color = dict(dendro.cluster_color)
        except Exception:  # noqa: BLE001
            pass

        if self.method == METHOD_SVD and not svd.has_embedding:
            self.has_figure = False
            self.figure = Figure()
            self.plot_books = []
            self.visible_document_ids = []
            self.status_message = "Run SVD to generate the 3D plot."
            return

        try:
            coords, doc_ids, axis_titles, method_note = await self._coords_and_docs(
                token, svd, rescale
            )
        except Exception as exc:  # noqa: BLE001
            self.is_fitting_viz = False
            self.has_figure = False
            self.figure = Figure()
            self.status_message = f"Plot failed: {exc}"
            return

        if coords is None or doc_ids is None:
            self.has_figure = False
            self.figure = Figure()
            self.plot_books = []
            self.visible_document_ids = []
            self.status_message = method_note or "Cannot build plot."
            return

        hidden = set(self.hidden_document_ids)
        show_labels = self.label_mode == LABEL_SHORT
        use_cluster = self.color_mode == COLOR_CLUSTER and bool(cluster_of)

        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        point_labels: list[str] = []
        hover_labels: list[str] = []
        colors: list[str] = []
        visible_ids: list[int] = []
        book_rows: list[dict] = []

        for i, doc_id in enumerate(doc_ids):
            key = str(doc_id)
            short = data.document_books.get(key) or data.document_labels.get(key, key)
            full = data.document_labels.get(key, short)
            corpus = data.document_corpus.get(key, "")
            identity = (
                data.document_color_override.get(key)
                or data.corpus_default_color.get(corpus, FALLBACK_COLOR)
            )
            if use_cluster and key in cluster_of:
                cid = str(cluster_of[key])
                color = cluster_color.get(cid, identity)
            else:
                color = identity
            visible = key not in hidden
            book_rows.append(
                {
                    "id": doc_id,
                    "short": short,
                    "label": full,
                    "corpus": corpus,
                    "color": color,
                    "visible": visible,
                    "has_override": key in data.document_color_override,
                }
            )
            if not visible:
                continue
            xs.append(float(coords[i, 0]))
            ys.append(float(coords[i, 1]))
            zs.append(float(coords[i, 2]) if coords.shape[1] > 2 else 0.0)
            point_labels.append(short)
            hover_labels.append(full)
            colors.append(color)
            visible_ids.append(doc_id)

        book_rows.sort(key=lambda r: str(r["short"]).lower())
        self.plot_books = book_rows
        self.visible_document_ids = visible_ids

        if not visible_ids:
            self.has_figure = False
            self.figure = Figure()
            self.visible_document_ids = []
            self.status_message = (
                "All books are hidden — show at least one book to plot."
            )
            return

        try:
            figure = make_3d_scatter(
                xs,
                ys,
                zs,
                labels=point_labels,
                hover_labels=hover_labels,
                colors=colors,
                document_ids=visible_ids,
                axis_titles=axis_titles or ("X", "Y", "Z"),
                show_labels=show_labels,
            )
            if self.camera:
                figure.update_layout(scene_camera=self.camera)
            self.figure = figure
            self.has_figure = True
            label_note = "short labels" if show_labels else "labels hidden"
            color_note = "cluster colors" if use_cluster else "identity colors"
            self.status_message = (
                f"{method_note}: {len(visible_ids)}/{len(doc_ids)} books "
                f"({label_note}, {color_note})."
            )
        except Exception as exc:  # noqa: BLE001
            self.has_figure = False
            self.figure = Figure()
            self.status_message = f"Plot failed: {exc}"
