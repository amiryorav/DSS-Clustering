"""3D plot step: SVD / UMAP / t-SNE scatter (spec §8.6)."""

from __future__ import annotations

import asyncio
import math
from types import SimpleNamespace

import numpy as np
import reflex as rx
from plotly.graph_objects import Figure

from dss_clustering.colors import resolve_book_color
from dss_clustering.pipeline.plotting import make_3d_scatter
from dss_clustering.pipeline.runtime import (
    VizEmbeddingBundle,
    get_bundle,
    get_embedding,
    get_viz,
    put_viz,
)
from dss_clustering.pipeline.viz import (
    fit_pca,
    fit_tsne,
    fit_umap,
    viz_params_key,
)
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
PANEL_PCA = "pca"
PANEL_SVD_B = "svd_b"
PANEL_UMAP = "umap"
PANEL_TSNE = "tsne"
GRID_PANELS = (PANEL_PCA, PANEL_SVD_B, PANEL_UMAP, PANEL_TSNE)
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
    PANEL_PCA: "figure_pca",
    PANEL_SVD_B: "figure_svd_b",
    PANEL_UMAP: "figure_umap",
    PANEL_TSNE: "figure_tsne",
}

_EXPORT_STEM = {
    PANEL_SINGLE: "plot",
    PANEL_PCA: "plot_pca",
    PANEL_SVD_B: "plot_svd",
    PANEL_UMAP: "plot_umap",
    PANEL_TSNE: "plot_tsne",
}

_READY_ATTR = {
    PANEL_PCA: "grid_ready_pca",
    PANEL_SVD_B: "grid_ready_svd_b",
    PANEL_UMAP: "grid_ready_umap",
    PANEL_TSNE: "grid_ready_tsne",
}


def plot_root_id(panel: str) -> str:
    """DOM id for the wrapper around one Plotly scene."""
    return f"plot-panel-{panel}"


# Wait for two browser paint frames after enabling the blocking overlay before
# asking the backend to begin CPU-heavy dimensionality reduction.
WAIT_FOR_BUSY_PAINT = """
new Promise((resolve) => {
  requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)));
})
"""

# 0-based TruncatedSVD columns. Column 0 is the first component and is skipped:
# it often tracks document length rather than style.
DEFAULT_SVD_DIMS = (1, 2, 3)


def select_svd_plot_dims(
    n_dims: int,
    dim_x: int = DEFAULT_SVD_DIMS[0],
    dim_y: int = DEFAULT_SVD_DIMS[1],
    dim_z: int = DEFAULT_SVD_DIMS[2],
) -> tuple[list[int], tuple[str, str, str], str, tuple[int, int, int]]:
    """Pick 0-based SVD columns. Labels match those indices (never column 0)."""
    n_dims = max(0, int(n_dims))
    if n_dims < 1:
        raise ValueError("Embedding has no dimensions to plot.")
    max_idx = n_dims - 1
    min_idx = 1 if n_dims > 1 else 0

    def _clamp(dim: int) -> int:
        try:
            value = int(dim)
        except (TypeError, ValueError):
            value = min_idx
        return min(max(min_idx, value), max_idx)

    cols = [_clamp(dim_x), _clamp(dim_y), _clamp(dim_z)]
    labels = (cols[0], cols[1], cols[2])
    titles = (f"Dim {labels[0]}", f"Dim {labels[1]}", f"Dim {labels[2]}")
    note = "SVD dims " + ",".join(str(d) for d in labels)
    return cols, titles, note, labels


class PlotState(rx.State):
    """Interactive 3D scatter — SVD (analysis) or UMAP/t-SNE (viz-only)."""

    method: str = METHOD_SVD
    color_mode: str = COLOR_IDENTITY
    # 0-based SVD columns shown on the axes. Defaults skip column 0.
    dim_x: int = DEFAULT_SVD_DIMS[0]
    dim_y: int = DEFAULT_SVD_DIMS[1]
    dim_z: int = DEFAULT_SVD_DIMS[2]
    label_mode: str = LABEL_HIDDEN
    hidden_document_ids: list[str] = []
    visible_document_ids: list[int] = []
    plot_books: list[dict] = []
    book_search: str = ""
    # Last camera applied from the pad (single view). Dragged views live in the DOM.
    camera: dict = {}

    # UMAP / t-SNE hyperparameters
    umap_n_neighbors: int = 15
    umap_min_dist: float = 0.1
    tsne_perplexity: float = 30.0
    is_fitting_viz: bool = False

    figure: Figure = Figure()
    has_figure: bool = False
    status_message: str = "Run SVD to generate the 3D plot."
    max_dim_index: int = 0

    # 2×2 comparison grid: PCA, SVD 1-2-3, UMAP, t-SNE.
    show_grid: bool = False
    has_grid: bool = False
    figure_pca: Figure = Figure()
    figure_svd_b: Figure = Figure()
    figure_umap: Figure = Figure()
    figure_tsne: Figure = Figure()
    grid_title_pca: str = "PCA"
    grid_title_svd_b: str = "SVD dims 1,2,3"
    grid_title_umap: str = "UMAP"
    grid_title_tsne: str = "t-SNE"
    grid_ready_pca: bool = False
    grid_ready_svd_b: bool = False
    grid_ready_umap: bool = False
    grid_ready_tsne: bool = False
    umap_skip_message: str = ""
    pca_skip_message: str = ""
    is_fitting_pca: bool = False
    is_fitting_umap: bool = False
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
            self.dim_x = max(1, int(value))
        except (TypeError, ValueError):
            return
        return PlotState.recompute

    @rx.event
    def set_dim_y(self, value: str):
        try:
            self.dim_y = max(1, int(value))
        except (TypeError, ValueError):
            return
        return PlotState.recompute

    @rx.event
    def set_dim_z(self, value: str):
        try:
            self.dim_z = max(1, int(value))
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

    async def _uses_cluster_colors(self) -> bool:
        if self.color_mode != COLOR_CLUSTER:
            return False
        cluster_of, _ = await self._cluster_colors()
        return bool(cluster_of)

    @rx.event
    async def set_book_color(self, document_id: int, color: str):
        data = await self.get_state(DataState)
        key = str(document_id)
        if await self._uses_cluster_colors():
            data.document_cluster_color_override = {
                **data.document_cluster_color_override,
                key: color,
            }
            return PlotState.refresh_visible_plots
        data.document_color_override = {
            **data.document_color_override,
            key: color,
        }
        return self._identity_color_changed()

    @rx.event
    async def clear_book_color(self, document_id: int):
        data = await self.get_state(DataState)
        key = str(document_id)
        if await self._uses_cluster_colors():
            overrides = dict(data.document_cluster_color_override)
            overrides.pop(key, None)
            data.document_cluster_color_override = overrides
            return PlotState.refresh_visible_plots
        overrides = dict(data.document_color_override)
        overrides.pop(key, None)
        data.document_color_override = overrides
        return self._identity_color_changed()

    @rx.event
    async def clear_all_book_colors(self):
        """Clear every hand-picked color for the active coloring mode."""
        data = await self.get_state(DataState)
        if await self._uses_cluster_colors():
            data.document_cluster_color_override = {}
            return PlotState.refresh_visible_plots
        data.document_color_override = {}
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
        """Paint the overlay first — PCA is cheap; UMAP and t-SNE dominate."""
        busy = await self.get_state(BusyState)
        busy.begin("Fitting SVD and t-SNE…")
        self.is_fitting_viz = True
        return rx.call_script(
            WAIT_FOR_BUSY_PAINT,
            callback=PlotState.run_grid_build,
        )

    @rx.event(background=True)
    async def run_grid_build(self, _painted: bool = True):
        """Fit views off the state lock so the Cloud websocket stays alive."""
        notes: list[str] = []
        overlay_held = True
        want_pca = False
        want_umap = False
        try:
            async with self:
                want_pca = bool(self.grid_ready_pca)
                want_umap = bool(self.grid_ready_umap)
                snapshot = await self._grid_inputs()
                if snapshot is None:
                    return
            overlay_held = await self._fit_grid_from_snapshot(
                snapshot,
                notes,
                fit_pca_panel=want_pca,
                fit_umap_panel=want_umap,
            )
        except Exception as exc:  # noqa: BLE001
            async with self:
                if not any(
                    (
                        self.grid_ready_pca,
                        self.grid_ready_svd_b,
                        self.grid_ready_umap,
                        self.grid_ready_tsne,
                    )
                ):
                    self.has_grid = False
                self.status_message = f"Comparison grid failed: {exc}"
        finally:
            async with self:
                self.is_fitting_viz = False
                if overlay_held:
                    busy = await self.get_state(BusyState)
                    busy.end()

    async def _grid_inputs(self) -> dict | None:
        """Read everything the fits need; caller must hold the state lock."""
        svd = await self.get_state(SVDState)
        rescale = await self.get_state(RescaleState)
        token = self.router.session.client_token
        emb = get_embedding(token)
        if not svd.has_embedding or emb is None:
            self.has_grid = False
            self.status_message = "Run SVD before building the comparison grid."
            return None
        X = np.asarray(emb.embedding, dtype=np.float64)
        n_dims = int(X.shape[1])
        cols, titles, note, _ = select_svd_plot_dims(n_dims, *DEFAULT_SVD_DIMS)
        bundle = get_bundle(token)
        matrix = None
        viz_ids: list[int] = []
        if bundle is not None and rescale.applied:
            matrix = bundle.rescaled(rescale.mode)
            viz_ids = list(bundle.document_ids)
        else:
            self.status_message = "Apply Rescale to include PCA, UMAP, and t-SNE."
        return {
            "svd_coords": X[:, cols],
            "svd_titles": titles,
            "svd_label": note,
            "svd_ids": list(emb.document_ids),
            "matrix": matrix,
            "viz_ids": viz_ids,
            "n_neighbors": self.umap_n_neighbors,
            "min_dist": self.umap_min_dist,
            "perplexity": self.tsne_perplexity,
        }

    def _remember_grid_panel(
        self,
        panel: str,
        coords,
        titles: tuple,
        label: str,
        doc_ids: list[int],
    ) -> None:
        self._grid_sources = {
            **self._grid_sources,
            panel: {
                "coords": coords,
                "titles": titles,
                "label": label,
                "doc_ids": doc_ids,
            },
        }

    async def _fit_grid_from_snapshot(
        self,
        snapshot: dict,
        notes: list[str],
        *,
        fit_pca_panel: bool = False,
        fit_umap_panel: bool = False,
    ) -> bool:
        """Fit SVD + t-SNE by default. PCA/UMAP only when explicitly requested."""
        matrix = snapshot["matrix"]
        viz_ids = snapshot["viz_ids"]
        overlay_held = True
        pca_skip = (
            "PCA is off by default so this Cloud VM stays up. "
            "Click Fit PCA if you want that layout."
        )
        umap_skip = (
            "UMAP is off by default — fitting it can exhaust Cloud RAM. "
            "Click Fit UMAP if you still want that layout."
        )

        async with self:
            keep_pca = self._grid_sources.get(PANEL_PCA) if fit_pca_panel else None
            keep_umap = self._grid_sources.get(PANEL_UMAP) if fit_umap_panel else None
            self._grid_sources = {}
            self.grid_ready_pca = False
            self.grid_ready_svd_b = False
            self.grid_ready_umap = False
            self.grid_ready_tsne = False
            self.pca_skip_message = "" if fit_pca_panel else pca_skip
            self.umap_skip_message = "" if fit_umap_panel else umap_skip
            self._remember_grid_panel(
                PANEL_SVD_B,
                snapshot["svd_coords"],
                snapshot["svd_titles"],
                snapshot["svd_label"],
                snapshot["svd_ids"],
            )
            if keep_pca is not None:
                self._grid_sources = {**self._grid_sources, PANEL_PCA: keep_pca}
            if keep_umap is not None:
                self._grid_sources = {**self._grid_sources, PANEL_UMAP: keep_umap}
            self._grid_notes = list(notes)
            if matrix is not None:
                busy = await self.get_state(BusyState)
                busy.message = "Fitting t-SNE…"
        await self._publish_panels((PANEL_SVD_B,))
        if matrix is None:
            async with self:
                self.pca_skip_message = (
                    "Apply Rescale before fitting PCA, UMAP, or t-SNE."
                )
                self.umap_skip_message = self.pca_skip_message
            return overlay_held

        try:
            tsne_coords = await asyncio.to_thread(
                fit_tsne,
                matrix,
                perplexity=snapshot["perplexity"],
                n_components=3,
            )
        except Exception as exc:  # noqa: BLE001
            notes.append(f"t-SNE failed: {exc}")
            tsne_coords = None
        async with self:
            if tsne_coords is not None:
                self._remember_grid_panel(
                    PANEL_TSNE,
                    tsne_coords,
                    ("t-SNE-1", "t-SNE-2", "t-SNE-3"),
                    "t-SNE",
                    viz_ids,
                )
            self._grid_notes = list(notes)
        await self._publish_panels((PANEL_TSNE,))

        if fit_pca_panel:
            await self._fit_pca_into_grid(snapshot, notes)
        if fit_umap_panel:
            await self._fit_umap_into_grid(snapshot, notes)

        async with self:
            ready_n = sum(
                1 for panel in GRID_PANELS if getattr(self, _READY_ATTR[panel])
            )
            summary = f"Comparison grid: {ready_n} view(s)."
            self.status_message = " ".join([summary, *notes]) if notes else summary
            busy = await self.get_state(BusyState)
            busy.end()
            overlay_held = False
        return overlay_held

    async def _fit_pca_into_grid(self, snapshot: dict, notes: list[str]) -> None:
        matrix = snapshot["matrix"]
        if matrix is None:
            return
        try:
            pca_coords = await asyncio.to_thread(fit_pca, matrix, n_components=3)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"PCA failed: {exc}")
            async with self:
                self.pca_skip_message = f"PCA failed: {exc}"
                self._grid_notes = list(notes)
            return
        async with self:
            self._remember_grid_panel(
                PANEL_PCA,
                pca_coords,
                ("PC1", "PC2", "PC3"),
                "PCA",
                snapshot["viz_ids"],
            )
            self.pca_skip_message = ""
            self._grid_notes = list(notes)
        await self._publish_panels((PANEL_PCA,))

    async def _fit_umap_into_grid(self, snapshot: dict, notes: list[str]) -> None:
        matrix = snapshot["matrix"]
        if matrix is None:
            return
        try:
            umap_coords = await asyncio.to_thread(
                fit_umap,
                matrix,
                n_neighbors=snapshot["n_neighbors"],
                min_dist=snapshot["min_dist"],
                n_components=3,
            )
        except Exception as exc:  # noqa: BLE001
            notes.append(f"UMAP failed: {exc}")
            async with self:
                self.umap_skip_message = f"UMAP failed: {exc}"
                self._grid_notes = list(notes)
            return
        async with self:
            self._remember_grid_panel(
                PANEL_UMAP,
                umap_coords,
                ("UMAP-1", "UMAP-2", "UMAP-3"),
                "UMAP",
                snapshot["viz_ids"],
            )
            self.umap_skip_message = ""
            self._grid_notes = list(notes)
        await self._publish_panels((PANEL_UMAP,))

    @rx.event(background=True)
    async def fit_grid_pca(self):
        """Fit PCA for the comparison grid without the blocking overlay."""
        notes: list[str] = []
        async with self:
            self.is_fitting_pca = True
            self.pca_skip_message = "Fitting PCA…"
            snapshot = await self._grid_inputs()
            if snapshot is None or snapshot["matrix"] is None:
                self.is_fitting_pca = False
                self.pca_skip_message = "Apply Rescale before fitting PCA."
                return
        try:
            await self._fit_pca_into_grid(snapshot, notes)
        finally:
            async with self:
                self.is_fitting_pca = False

    @rx.event(background=True)
    async def fit_grid_umap(self):
        """Fit UMAP for the comparison grid without the blocking overlay."""
        notes: list[str] = []
        async with self:
            self.is_fitting_umap = True
            self.umap_skip_message = "Fitting UMAP…"
            snapshot = await self._grid_inputs()
            if snapshot is None or snapshot["matrix"] is None:
                self.is_fitting_umap = False
                self.umap_skip_message = "Apply Rescale before fitting UMAP."
                return
        try:
            await self._fit_umap_into_grid(snapshot, notes)
        finally:
            async with self:
                self.is_fitting_umap = False

    async def _publish_panels(self, panels: tuple[str, ...]) -> None:
        """Build and assign only the named panels so earlier views are not resent."""
        async with self:
            ctx = await self._grid_render_context()
        ctx["sources"] = {
            panel: ctx["sources"][panel]
            for panel in panels
            if panel in ctx["sources"]
        }
        payload = self._figures_from_context(ctx)
        async with self:
            for panel in panels:
                setattr(
                    self, _READY_ATTR[panel], payload["ready"].get(panel, False)
                )
                if panel in payload["figures"]:
                    setattr(self, _FIGURE_ATTR[panel], payload["figures"][panel])
                    setattr(self, f"grid_title_{panel}", payload["titles"][panel])
            if payload["book_rows"] is not None:
                self.plot_books = payload["book_rows"]
                self.visible_document_ids = payload["visible_ids"]
            ready_n = sum(
                1 for panel in GRID_PANELS if getattr(self, _READY_ATTR[panel])
            )
            self.has_grid = ready_n > 0
            notes = ctx["notes"]
            summary = f"Comparison grid: {ready_n} view(s)."
            self.status_message = (
                " ".join([summary, *notes]) if notes else summary
            )
        await asyncio.sleep(0)

    async def _render_grid(self):
        """Redraw while the caller already holds the state lock."""
        ctx = await self._grid_render_context()
        payload = self._figures_from_context(ctx)
        self._apply_grid_payload(payload)

    async def _grid_render_context(self) -> dict:
        """Snapshot everything figure building needs. Caller must hold the lock."""
        data = await self.get_state(DataState)
        cluster_of, cluster_color = await self._cluster_colors()
        return {
            "sources": dict(self._grid_sources),
            "notes": list(self._grid_notes),
            "color_mode": self.color_mode,
            "label_mode": self.label_mode,
            "hidden": set(self.hidden_document_ids),
            "data": SimpleNamespace(
                document_books=dict(data.document_books),
                document_labels=dict(data.document_labels),
                document_corpus=dict(data.document_corpus),
                document_color_override=dict(data.document_color_override),
                document_cluster_color_override=dict(
                    data.document_cluster_color_override
                ),
                corpus_default_color=dict(data.corpus_default_color),
            ),
            "cluster_of": cluster_of,
            "cluster_color": cluster_color,
            "cameras": {panel: self._camera_for(panel) for panel in GRID_PANELS},
            "uirevisions": {
                panel: self._uirevision(panel) for panel in GRID_PANELS
            },
        }

    def _figures_from_context(self, ctx: dict) -> dict:
        """CPU/Plotly work — safe to run without the state lock."""
        sources = ctx["sources"]
        cluster_of = ctx["cluster_of"]
        use_cluster = ctx["color_mode"] == COLOR_CLUSTER and bool(cluster_of)
        show_labels = ctx["label_mode"] == LABEL_SHORT
        figures: dict = {}
        titles: dict = {}
        book_rows = None
        visible_ids: list[int] = []
        built = 0
        for panel, source in sources.items():
            series = self._point_series(
                source["coords"],
                source["doc_ids"],
                data=ctx["data"],
                cluster_of=cluster_of,
                cluster_color=ctx["cluster_color"],
                use_cluster=use_cluster,
                hidden=ctx["hidden"],
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
                axis_titles=source["titles"],
                show_labels=show_labels,
                height=GRID_PANEL_HEIGHT,
                uirevision=ctx["uirevisions"].get(panel, panel),
                marker_size=4,
            )
            figure.update_layout(scene_camera=ctx["cameras"].get(panel, {}))
            figures[panel] = figure
            titles[panel] = source["label"]
            built += 1
            if panel == PANEL_PCA or (
                panel == PANEL_SVD_B and PANEL_PCA not in sources
            ):
                book_rows = series["book_rows"]
                visible_ids = series["visible_ids"]
        summary = f"Comparison grid: {built} view(s)."
        notes = ctx["notes"]
        return {
            "ready": {panel: panel in sources for panel in GRID_PANELS},
            "figures": figures,
            "titles": titles,
            "built": built,
            "book_rows": book_rows,
            "visible_ids": visible_ids,
            "status": " ".join([summary, *notes]) if notes else summary,
        }

    def _apply_grid_payload(self, payload: dict) -> None:
        """Write prebuilt figures. Caller must hold the state lock."""
        for panel in GRID_PANELS:
            setattr(self, _READY_ATTR[panel], payload["ready"].get(panel, False))
            if panel in payload["figures"]:
                setattr(self, _FIGURE_ATTR[panel], payload["figures"][panel])
                setattr(self, f"grid_title_{panel}", payload["titles"][panel])
        if payload["book_rows"] is not None:
            self.plot_books = payload["book_rows"]
            self.visible_document_ids = payload["visible_ids"]
        self.has_grid = payload["built"] > 0
        self.status_message = payload["status"]

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
        data,
        cluster_of: dict,
        cluster_color: dict,
        use_cluster: bool,
        hidden: set | None = None,
    ) -> dict:
        """Per-point arrays for one projection, honouring hidden books."""
        hidden_ids = set(self.hidden_document_ids) if hidden is None else hidden
        identity_overrides = dict(getattr(data, "document_color_override", {}) or {})
        cluster_overrides = dict(
            getattr(data, "document_cluster_color_override", {}) or {}
        )
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
            assigned_cluster = None
            if use_cluster and key in cluster_of:
                assigned_cluster = cluster_color.get(str(cluster_of[key]))
            color = resolve_book_color(
                corpus_default=data.corpus_default_color.get(corpus, FALLBACK_COLOR),
                identity_override=identity_overrides.get(key),
                cluster_color=assigned_cluster,
                cluster_override=cluster_overrides.get(key),
                use_cluster=use_cluster,
            )
            visible = key not in hidden_ids
            book_rows.append(
                {
                    "id": doc_id,
                    "short": short,
                    "label": full,
                    "corpus": corpus,
                    "color": color,
                    "visible": visible,
                    "has_override": (
                        key in cluster_overrides
                        if use_cluster
                        else key in identity_overrides
                    ),
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

            cols, titles, note, labels = select_svd_plot_dims(
                n_dims, self.dim_x, self.dim_y, self.dim_z
            )
            self.dim_x, self.dim_y, self.dim_z = labels
            coords = X[:, cols]
            return coords, list(emb.document_ids), titles, note

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
