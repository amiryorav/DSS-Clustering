"""SVD step: constant or sweep TruncatedSVD (spec §8.5)."""

from __future__ import annotations

import numpy as np
import reflex as rx
from plotly.graph_objects import Figure

from dss_clustering.pipeline.plotting import make_sweep_chart
from dss_clustering.pipeline.runtime import (
    EmbeddingBundle,
    clear_embedding,
    get_bundle,
    put_embedding,
)
from dss_clustering.pipeline.svd import (
    DEFAULT_RANDOM_STATE,
    max_svd_components,
    run_svd,
    run_svd_sweep,
)
from dss_clustering.states.rescale_state import RescaleState
from dss_clustering.states.vectorize_state import VectorizeState

MODE_CONSTANT = "constant"
MODE_SWEEP = "sweep"


class SVDState(rx.State):
    """SVD controls: constant size or sweep-to-best."""

    enabled: bool = True
    mode: str = MODE_CONSTANT
    n_components: int = 120
    sweep_min: int = 10
    sweep_max: int = 200
    sweep_step: int = 10
    # lemma.py default; FeatureState switches this to 50 in morphology mode.
    plateau_min: int = 70
    normalize: bool = True
    # Fixed internally for reproducibility — not exposed in the UI.
    random_state: int = DEFAULT_RANDOM_STATE

    is_running: bool = False
    has_embedding: bool = False
    n_components_used: int = 0
    variance_explained: float = 0.0
    density_pct: float = 0.0
    density_label: str = "—"
    n_documents: int = 0
    status_message: str = "Build and rescale a matrix, then run SVD."
    progress_message: str = ""
    sweep_results: list[dict] = []
    sweep_figure: Figure = Figure()
    has_sweep_figure: bool = False

    def _token(self) -> str:
        return self.router.session.client_token

    @rx.event
    def set_enabled(self, value: bool):
        self.enabled = value

    @rx.event
    def set_mode(self, mode: str | list[str]):
        value = mode[0] if isinstance(mode, list) else mode
        if value in (MODE_CONSTANT, MODE_SWEEP):
            self.mode = value

    @rx.event
    def set_n_components(self, value: str):
        try:
            n = int(value)
        except (TypeError, ValueError):
            return
        self.n_components = max(1, n)

    @rx.event
    def set_sweep_min(self, value: str):
        try:
            self.sweep_min = max(1, int(value))
        except (TypeError, ValueError):
            return

    @rx.event
    def set_sweep_max(self, value: str):
        try:
            self.sweep_max = max(1, int(value))
        except (TypeError, ValueError):
            return

    @rx.event
    def set_sweep_step(self, value: str):
        try:
            self.sweep_step = max(1, int(value))
        except (TypeError, ValueError):
            return

    @rx.event
    def set_plateau_min(self, value: str):
        try:
            self.plateau_min = max(1, int(value))
        except (TypeError, ValueError):
            return

    @rx.event
    def set_normalize(self, value: bool):
        self.normalize = value

    @rx.var(cache=True)
    def is_sweep(self) -> bool:
        return self.mode == MODE_SWEEP

    def _update_sweep_figure(self):
        if self.sweep_results:
            self.sweep_figure = make_sweep_chart(list(self.sweep_results))
            self.has_sweep_figure = True
        else:
            self.sweep_figure = Figure()
            self.has_sweep_figure = False

    @rx.event
    def select_sweep_dims(self, n: int):
        """Pick a sweep size as the new constant n_components (user re-runs SVD)."""
        try:
            dims = int(n)
        except (TypeError, ValueError):
            return
        if dims < 1:
            return
        self.n_components = dims
        self.mode = MODE_CONSTANT
        # Mark selected row in the table/chart for feedback
        self.sweep_results = [
            {**row, "selected": int(row["n"]) == dims} for row in self.sweep_results
        ]
        self._update_sweep_figure()
        self.status_message = (
            f"Selected {dims} dims from the sweep chart — "
            f"switched to Constant. Click Run SVD to apply."
        )

    @rx.event
    def on_sweep_click(self, event_data):
        """Plotly click: use the clicked point's x (dims) as constant size."""
        try:
            points = event_data.get("points") if isinstance(event_data, dict) else None
            if not points:
                # Reflex may pass a typed object
                points = getattr(event_data, "points", None)
            if not points:
                return
            point = points[0]
            if isinstance(point, dict):
                x = point.get("x")
            else:
                x = getattr(point, "x", None)
            if x is None:
                return
            return SVDState.select_sweep_dims(int(round(float(x))))
        except Exception:  # noqa: BLE001
            return

    @rx.event(background=True)
    async def run(self):
        async with self:
            vectorize = await self.get_state(VectorizeState)
            rescale = await self.get_state(RescaleState)
            token = self._token()

            if not vectorize.has_matrix or vectorize.is_stale:
                self.has_embedding = False
                clear_embedding(token)
                self.status_message = (
                    "Count matrix missing or stale — rebuild Vectorize."
                )
                return
            if not rescale.applied:
                self.has_embedding = False
                clear_embedding(token)
                self.status_message = "Apply Rescale before running SVD."
                return

            bundle = get_bundle(token) or get_bundle(
                vectorize.router.session.client_token
            )
            if bundle is None:
                self.has_embedding = False
                self.status_message = (
                    "Count matrix not found in server memory — rebuild."
                )
                return

            enabled = self.enabled
            mode = self.mode
            n_components = self.n_components
            sweep_min = self.sweep_min
            sweep_max = self.sweep_max
            sweep_step = self.sweep_step
            plateau_min = self.plateau_min
            normalize = self.normalize
            random_state = self.random_state
            rescale_mode = rescale.mode

            self.is_running = True
            self.progress_message = (
                "Sweeping SVD sizes…" if mode == MODE_SWEEP and enabled else "Running SVD…"
            )
            self.status_message = self.progress_message

        try:
            matrix = bundle.rescaled(rescale_mode)
            max_n = max_svd_components(*matrix.shape)
            sweep_rows: list[dict] = []

            if not enabled:
                embedding, n_used, var_exp = run_svd(
                    matrix,
                    enabled=False,
                    n_components=n_components,
                    normalize=normalize,
                    random_state=random_state,
                )
            elif mode == MODE_SWEEP:
                embedding, n_used, var_exp, sweep_rows = run_svd_sweep(
                    matrix,
                    sweep_min=sweep_min,
                    sweep_max=sweep_max,
                    sweep_step=sweep_step,
                    plateau_min=plateau_min,
                    normalize=normalize,
                    random_state=random_state,
                )
            else:
                embedding, n_used, var_exp = run_svd(
                    matrix,
                    enabled=True,
                    n_components=n_components,
                    normalize=normalize,
                    random_state=random_state,
                )

            put_embedding(
                token,
                EmbeddingBundle(
                    embedding=embedding,
                    document_ids=list(bundle.document_ids),
                    n_components_used=n_used,
                    variance_explained=var_exp,
                    svd_enabled=enabled,
                    rescale_mode=rescale_mode,
                    fingerprint=bundle.fingerprint,
                ),
            )

            async with self:
                self.has_embedding = True
                self.n_components_used = n_used
                self.variance_explained = round(var_exp, 4)
                self.density_pct = (
                    round(100.0 * np.count_nonzero(embedding) / embedding.size, 2)
                    if embedding.size
                    else 0.0
                )
                self.density_label = f"{self.density_pct:.2f}%"
                self.n_documents = int(embedding.shape[0])
                self.sweep_results = sweep_rows
                self._update_sweep_figure()

                if not enabled:
                    self.status_message = (
                        f"SVD disabled — using rescaled matrix "
                        f"{self.n_documents} × {n_used} as the embedding; "
                        f"density {self.density_label}."
                    )
                elif mode == MODE_SWEEP:
                    self.status_message = (
                        f"Sweep picked {n_used} dims "
                        f"(plateau ≥ {plateau_min}; max available {max_n}); "
                        f"variance explained {self.variance_explained:.1%}; "
                        f"density {self.density_label}."
                    )
                else:
                    note = ""
                    if n_used < n_components:
                        note = f" (clamped from {n_components}; max {max_n})"
                    self.status_message = (
                        f"SVD embedding {self.n_documents} × {n_used}{note}; "
                        f"variance explained {self.variance_explained:.1%}; "
                        f"density {self.density_label}."
                    )

                self.progress_message = ""
                self.is_running = False
                from dss_clustering.states.dendrogram_state import DendrogramState
                from dss_clustering.states.plot_state import PlotState

                return [PlotState.recompute, DendrogramState.refit]
        except Exception as exc:  # noqa: BLE001
            async with self:
                clear_embedding(token)
                self.has_embedding = False
                self.n_components_used = 0
                self.variance_explained = 0.0
                self.density_pct = 0.0
                self.density_label = "—"
                self.n_documents = 0
                self.sweep_results = []
                self.sweep_figure = Figure()
                self.has_sweep_figure = False
                self.status_message = f"SVD failed: {exc}"
                self.progress_message = ""
                self.is_running = False
