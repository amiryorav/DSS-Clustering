"""Session-only AnalysisConfig presets (spec §8.10, local-only)."""

from __future__ import annotations

from datetime import datetime, timezone

import reflex as rx

from dss_clustering.pipeline.config import AnalysisConfig
from dss_clustering.states.busy_state import BusyState
from dss_clustering.states.data_state import DataState
from dss_clustering.states.dendrogram_state import DendrogramState
from dss_clustering.states.feature_state import (
    MODE_LEMMA,
    MODE_MORPHOLOGY,
    FeatureState,
)
from dss_clustering.states.rescale_state import RescaleState
from dss_clustering.states.svd_state import SVDState
from dss_clustering.states.vectorize_state import VectorizeState


class SavedConfigState(rx.State):
    """Save / load named AnalysisConfig snapshots for this browser session."""

    presets: list[dict] = []
    preset_name: str = ""
    status_message: str = ""
    _next_id: int = 1

    @rx.event
    def set_preset_name(self, value: str):
        self.preset_name = value

    @rx.event
    async def save(self):
        name = self.preset_name.strip()
        if not name:
            self.status_message = "Enter a name for this configuration."
            return
        config = await self._snapshot()
        entry = {
            "id": self._next_id,
            "name": name,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "config": config.to_dict(),
        }
        self._next_id += 1
        self.presets = [*self.presets, entry]
        self.status_message = f"Saved configuration '{name}' for this session."

    @rx.event
    async def load(self, preset_id: int):
        match = next((p for p in self.presets if p["id"] == preset_id), None)
        if match is None:
            self.status_message = "Preset not found."
            return
        config = AnalysisConfig.from_dict(match["config"])
        self.status_message = f"Loading '{match['name']}'…"
        # Applying a preset reruns the whole pipeline, so block the UI up front
        # and let the last chained step release it.
        busy = await self.get_state(BusyState)
        busy.begin(f"Loading preset '{match['name']}'…")
        yield
        yield SavedConfigState.apply_config(config.to_dict())
        yield BusyState.release

    @rx.event
    async def apply_config(self, config_dict: dict):
        """Push AnalysisConfig fields into step states and recompute."""
        config = AnalysisConfig.from_dict(config_dict)

        data = await self.get_state(DataState)
        features = await self.get_state(FeatureState)
        rescale = await self.get_state(RescaleState)
        svd = await self.get_state(SVDState)
        dendro = await self.get_state(DendrogramState)

        data.selected_document_ids = list(config.selected_document_ids)

        if config.feature_mode in (MODE_LEMMA, MODE_MORPHOLOGY):
            features.mode = config.feature_mode
        features.selected_morph_columns = [
            c for c in features.morph_columns if c in set(config.morph_columns)
        ] or list(config.morph_columns)
        # Spec field name; project maps it to ignore_proper_names.
        features.ignore_proper_names = bool(config.apply_proper_name_exception)

        rescale.mode = config.rescale_mode

        svd.enabled = bool(config.svd_enabled)
        svd.mode = config.svd_mode
        svd.n_components = int(config.svd_n_components)
        if config.svd_sweep_range is not None:
            svd.sweep_min, svd.sweep_max, svd.sweep_step = config.svd_sweep_range
        svd.normalize = bool(config.svd_normalize)
        svd.random_state = int(config.svd_random_state)
        svd.plateau_min = int(config.svd_plateau_min)

        dendro.linkage_method = config.linkage_method
        dendro.distance_metric = config.distance_metric
        dendro.cut_height = float(config.cut_height)

        self.status_message = (
            f"Applied config ({len(config.selected_document_ids)} books) — rebuilding."
        )
        return VectorizeState.build_matrix

    async def _snapshot(self) -> AnalysisConfig:
        data = await self.get_state(DataState)
        features = await self.get_state(FeatureState)
        rescale = await self.get_state(RescaleState)
        svd = await self.get_state(SVDState)
        dendro = await self.get_state(DendrogramState)

        morph = (
            tuple(features.selected_morph_columns)
            if features.mode == MODE_MORPHOLOGY
            else tuple(features.morph_columns)
        )
        return AnalysisConfig(
            selected_document_ids=tuple(data.selected_document_ids),
            feature_mode=features.mode,
            morph_columns=morph,
            apply_proper_name_exception=bool(features.ignore_proper_names),
            rescale_mode=rescale.mode,
            svd_enabled=bool(svd.enabled),
            svd_mode=svd.mode,
            svd_n_components=int(svd.n_components),
            svd_sweep_range=(
                int(svd.sweep_min),
                int(svd.sweep_max),
                int(svd.sweep_step),
            ),
            svd_normalize=bool(svd.normalize),
            svd_random_state=int(svd.random_state),
            svd_plateau_min=int(svd.plateau_min),
            linkage_method=dendro.linkage_method,
            distance_metric=dendro.distance_metric,
            cut_height=float(dendro.cut_height),
        )
