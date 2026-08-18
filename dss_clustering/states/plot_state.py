"""3D plot step: SVD / UMAP / t-SNE scatter (spec §8.6)."""

from __future__ import annotations

import math

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

# One camera pad per rendered scene: the big single plot plus the 2×2 comparison.
PANEL_SINGLE = "single"
PANEL_SVD_A = "svd_a"
PANEL_SVD_B = "svd_b"
PANEL_UMAP = "umap"
PANEL_TSNE = "tsne"
GRID_PANELS = (PANEL_SVD_A, PANEL_SVD_B, PANEL_UMAP, PANEL_TSNE)
ALL_PANELS = (PANEL_SINGLE, *GRID_PANELS)

# Plotly's default eye (1.25, 1.25, 1.25) in spherical terms.
DEFAULT_AZIMUTH = 45.0
DEFAULT_ELEVATION = 35.0
DEFAULT_DISTANCE = 2.17
ROTATE_STEP_DEGREES = 15.0
ZOOM_FACTOR = 1.25
MIN_DISTANCE = 0.5
MAX_DISTANCE = 8.0
GRID_PANEL_HEIGHT = 420

_FIGURE_ATTR = {
    PANEL_SINGLE: "figure",
    PANEL_SVD_A: "figure_svd_a",
    PANEL_SVD_B: "figure_svd_b",
    PANEL_UMAP: "figure_umap",
    PANEL_TSNE: "figure_tsne",
}

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
    # Zero-based SVD component indices, matching the axis labels ("Dim 0" …).
    dim_x: int = 1
    dim_y: int = 2
    dim_z: int = 3
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

    # 2×2 comparison grid: SVD 0-1-2, SVD 1-2-3, UMAP, t-SNE.
    show_grid: bool = False
    has_grid: bool = False
    figure_svd_a: Figure = Figure()
    figure_svd_b: Figure = Figure()
    figure_umap: Figure = Figure()
    figure_tsne: Figure = Figure()
    grid_title_svd_a: str = "SVD dims 0,1,2"
    grid_title_svd_b: str = "SVD dims 1,2,3"
    grid_title_umap: str = "UMAP"
    grid_title_tsne: str = "t-SNE"
    # Backend-only projection cache. UI-only changes (labels, colours, hidden
    # books) can redraw all four panels without fitting UMAP/t-SNE again.
    _grid_sources: dict = {}
    _grid_notes: list[str] = []

    # Button-driven camera per panel, in degrees / eye distance.
    panel_azimuth: dict[str, float] = {p: DEFAULT_AZIMUTH for p in ALL_PANELS}
    panel_elevation: dict[str, float] = {p: DEFAULT_ELEVATION for p in ALL_PANELS}
    panel_distance: dict[str, float] = {p: DEFAULT_DISTANCE for p in ALL_PANELS}
    # Bumped on every camera button press so Plotly stops preserving the
    # dragged camera and accepts the one we send.
    panel_revision: dict[str, int] = {p: 0 for p in ALL_PANELS}

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
            return PlotState.refresh_visible_plots

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
            return PlotState.refresh_visible_plots

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
        return PlotState.refresh_visible_plots

    @rx.event
    def show_all_books(self):
        self.hidden_document_ids = []
        return PlotState.refresh_visible_plots

    @rx.event
    def show_matching_books(self):
        matched = {str(b["id"]) for b in self.filtered_plot_books}
        self.hidden_document_ids = [
            k for k in self.hidden_document_ids if k not in matched
        ]
        return PlotState.refresh_visible_plots

    @rx.event
    def hide_matching_books(self):
        matched = {str(b["id"]) for b in self.filtered_plot_books}
        self.hidden_document_ids = sorted(set(self.hidden_document_ids) | matched)
        return PlotState.refresh_visible_plots

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
        return PlotState.refresh_visible_plots

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

        return [PlotState.refresh_visible_plots, DendrogramState.refresh_colors]

    @rx.event
    async def refresh_visible_plots(self):
        """Apply display-only controls to whichever plot layout is visible."""
        if self.show_grid and self._grid_sources:
            await self._render_grid()
        else:
            await self._recompute()

    # ---------- camera pads ----------

    def _uirevision(self, panel: str) -> str:
        return f"{panel}-{int(self.panel_revision.get(panel, 0))}"

    def _camera_for(self, panel: str) -> dict:
        """Spherical pad angles → a Plotly gl3d camera eye."""
        azimuth = math.radians(float(self.panel_azimuth.get(panel, DEFAULT_AZIMUTH)))
        elevation = math.radians(
            float(self.panel_elevation.get(panel, DEFAULT_ELEVATION))
        )
        distance = float(self.panel_distance.get(panel, DEFAULT_DISTANCE))
        return {
            "eye": {
                "x": distance * math.cos(elevation) * math.cos(azimuth),
                "y": distance * math.cos(elevation) * math.sin(azimuth),
                "z": distance * math.sin(elevation),
            }
        }

    def _apply_panel_camera(self, panel: str):
        """Push the pad camera into that panel's figure.

        A copy is assigned rather than mutating in place so Reflex sees the var
        as changed and ships the new layout to the browser.
        """
        attr = _FIGURE_ATTR.get(panel)
        if attr is None:
            return
        current = getattr(self, attr, None)
        if current is None:
            return
        self.panel_revision = {
            **self.panel_revision,
            panel: int(self.panel_revision.get(panel, 0)) + 1,
        }
        updated = Figure(current)
        updated.update_layout(
            scene_camera=self._camera_for(panel),
            uirevision=self._uirevision(panel),
        )
        if panel == PANEL_SINGLE:
            # Keep exports in step with what the buttons are showing.
            self.camera = self._camera_for(panel)
        setattr(self, attr, updated)

    @rx.event
    def rotate_panel(self, panel: str, delta_azimuth: float, delta_elevation: float):
        if panel not in ALL_PANELS:
            return
        azimuth = float(self.panel_azimuth.get(panel, DEFAULT_AZIMUTH))
        elevation = float(self.panel_elevation.get(panel, DEFAULT_ELEVATION))
        self.panel_azimuth = {
            **self.panel_azimuth,
            panel: (azimuth + float(delta_azimuth)) % 360.0,
        }
        # Stop just short of the poles, where the gl3d camera flips over.
        self.panel_elevation = {
            **self.panel_elevation,
            panel: max(-89.0, min(89.0, elevation + float(delta_elevation))),
        }
        self._apply_panel_camera(panel)

    @rx.event
    def zoom_panel(self, panel: str, factor: float):
        if panel not in ALL_PANELS:
            return
        distance = float(self.panel_distance.get(panel, DEFAULT_DISTANCE))
        scaled = distance / float(factor) if factor else distance
        self.panel_distance = {
            **self.panel_distance,
            panel: max(MIN_DISTANCE, min(MAX_DISTANCE, scaled)),
        }
        self._apply_panel_camera(panel)

    @rx.event
    def reset_panel_view(self, panel: str):
        if panel not in ALL_PANELS:
            return
        self.panel_azimuth = {**self.panel_azimuth, panel: DEFAULT_AZIMUTH}
        self.panel_elevation = {**self.panel_elevation, panel: DEFAULT_ELEVATION}
        self.panel_distance = {**self.panel_distance, panel: DEFAULT_DISTANCE}
        if panel == PANEL_SINGLE:
            self.camera = {}
        self._apply_panel_camera(panel)

    # ---------- 2×2 comparison grid ----------

    @rx.event
    async def toggle_grid(self):
        """Show or hide the four side-by-side projections."""
        if self.show_grid:
            self.show_grid = False
            return
        self.show_grid = True
        if self._grid_sources:
            await self._render_grid()
            return
        return PlotState.build_grid

    @rx.event
    async def build_grid(self):
        """Paint the overlay first — UMAP and t-SNE are both fitted here."""
        busy = await self.get_state(BusyState)
        busy.begin("Fitting the four comparison views…")
        self.is_fitting_viz = True
        return rx.call_script(
            WAIT_FOR_BUSY_PAINT,
            callback=PlotState.run_grid_build,
        )

    @rx.event(background=True)
    async def run_grid_build(self, _painted: bool = True):
        try:
            async with self:
                await self._build_grid()
        finally:
            async with self:
                self.is_fitting_viz = False
                busy = await self.get_state(BusyState)
                busy.end()

    async def _build_grid(self):
        svd = await self.get_state(SVDState)
        rescale = await self.get_state(RescaleState)
        data = await self.get_state(DataState)
        token = self.router.session.client_token

        emb = get_embedding(token)
        if not svd.has_embedding or emb is None:
            self.has_grid = False
            self.status_message = "Run SVD before building the comparison grid."
            return

        X = emb.embedding
        n_dims = int(X.shape[1])
        svd_ids = list(emb.document_ids)

        def svd_panel(start: int) -> tuple:
            idx = [min(start + offset, n_dims - 1) for offset in range(3)]
            titles = (f"Dim {idx[0]}", f"Dim {idx[1]}", f"Dim {idx[2]}")
            return X[:, idx], titles, "SVD dims " + ",".join(str(i) for i in idx)

        panels: list[tuple[str, object, tuple, str, list[int]]] = []
        coords_a, titles_a, label_a = svd_panel(0)
        panels.append((PANEL_SVD_A, coords_a, titles_a, label_a, svd_ids))
        coords_b, titles_b, label_b = svd_panel(1)
        panels.append((PANEL_SVD_B, coords_b, titles_b, label_b, svd_ids))

        notes: list[str] = []
        bundle = get_bundle(token)
        if bundle is not None and rescale.applied:
            matrix = bundle.rescaled(rescale.mode)
            viz_ids = list(bundle.document_ids)
            try:
                panels.append(
                    (
                        PANEL_UMAP,
                        fit_umap(
                            matrix,
                            n_neighbors=self.umap_n_neighbors,
                            min_dist=self.umap_min_dist,
                            n_components=3,
                        ),
                        ("UMAP-1", "UMAP-2", "UMAP-3"),
                        "UMAP",
                        viz_ids,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                notes.append(f"UMAP failed: {exc}")
            try:
                panels.append(
                    (
                        PANEL_TSNE,
                        fit_tsne(
                            matrix,
                            perplexity=self.tsne_perplexity,
                            n_components=3,
                        ),
                        ("t-SNE-1", "t-SNE-2", "t-SNE-3"),
                        "t-SNE",
                        viz_ids,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                notes.append(f"t-SNE failed: {exc}")
        else:
            notes.append("Apply Rescale to include UMAP and t-SNE.")

        self._grid_sources = {
            panel: {
                "coords": coords,
                "titles": titles,
                "label": label,
                "doc_ids": doc_ids,
            }
            for panel, coords, titles, label, doc_ids in panels
        }
        self._grid_notes = notes
        await self._render_grid()

    async def _render_grid(self):
        """Redraw cached projections with current labels, colours and visibility."""
        data = await self.get_state(DataState)
        cluster_of, cluster_color = await self._cluster_colors()
        use_cluster = self.color_mode == COLOR_CLUSTER and bool(cluster_of)
        show_labels = self.label_mode == LABEL_SHORT
        built = 0

        # Clear panels missing from the cache (for example, a failed UMAP fit).
        for panel in GRID_PANELS:
            if panel not in self._grid_sources:
                setattr(self, _FIGURE_ATTR[panel], Figure())

        for panel, source in self._grid_sources.items():
            coords = source["coords"]
            titles = source["titles"]
            label = source["label"]
            doc_ids = source["doc_ids"]
            series = self._point_series(
                coords,
                doc_ids,
                data=data,
                cluster_of=cluster_of,
                cluster_color=cluster_color,
                use_cluster=use_cluster,
            )
            if not series["visible_ids"]:
                continue
            figure = make_3d_scatter(
                series["xs"],
                series["ys"],
                series["zs"],
                labels=series["labels"],
                hover_labels=series["hovers"],
                colors=series["colors"],
                document_ids=series["visible_ids"],
                axis_titles=titles,
                show_labels=show_labels,
                height=GRID_PANEL_HEIGHT,
                uirevision=self._uirevision(panel),
                marker_size=4,
            )
            figure.update_layout(scene_camera=self._camera_for(panel))
            setattr(self, _FIGURE_ATTR[panel], figure)
            setattr(self, f"grid_title_{panel}", label)
            built += 1
            if panel == PANEL_SVD_A:
                self.plot_books = series["book_rows"]
                self.visible_document_ids = series["visible_ids"]

        self.has_grid = built > 0
        summary = f"Comparison grid: {built} view(s)."
        self.status_message = (
            " ".join([summary, *self._grid_notes]) if self._grid_notes else summary
        )

    async def _cluster_colors(self) -> tuple[dict, dict]:
        """Current dendrogram cut colors, or empty when there is no tree."""
        try:
            from dss_clustering.states.dendrogram_state import DendrogramState

            dendro = await self.get_state(DendrogramState)
            if dendro.has_tree:
                return dict(dendro.cluster_of), dict(dendro.cluster_color)
        except Exception:  # noqa: BLE001
            pass
        return {}, {}

    def _point_series(
        self,
        coords,
        doc_ids: list[int],
        *,
        data: DataState,
        cluster_of: dict,
        cluster_color: dict,
        use_cluster: bool,
    ) -> dict:
        """Per-point arrays for one projection, honouring hidden books."""
        hidden = set(self.hidden_document_ids)
        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        labels: list[str] = []
        hovers: list[str] = []
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
                color = cluster_color.get(str(cluster_of[key]), identity)
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
            labels.append(short)
            hovers.append(full)
            colors.append(color)
            visible_ids.append(doc_id)

        book_rows.sort(key=lambda row: str(row["short"]).lower())
        return {
            "xs": xs,
            "ys": ys,
            "zs": zs,
            "labels": labels,
            "hovers": hovers,
            "colors": colors,
            "visible_ids": visible_ids,
            "book_rows": book_rows,
        }

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

        cluster_of, cluster_color = await self._cluster_colors()

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

        show_labels = self.label_mode == LABEL_SHORT
        use_cluster = self.color_mode == COLOR_CLUSTER and bool(cluster_of)
        series = self._point_series(
            coords,
            doc_ids,
            data=data,
            cluster_of=cluster_of,
            cluster_color=cluster_color,
            use_cluster=use_cluster,
        )
        xs = series["xs"]
        ys = series["ys"]
        zs = series["zs"]
        point_labels = series["labels"]
        hover_labels = series["hovers"]
        colors = series["colors"]
        visible_ids = series["visible_ids"]

        self.plot_books = series["book_rows"]
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
                uirevision=self._uirevision(PANEL_SINGLE),
            )
            if self.camera:
                figure.update_layout(scene_camera=self.camera)
            else:
                figure.update_layout(scene_camera=self._camera_for(PANEL_SINGLE))
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
