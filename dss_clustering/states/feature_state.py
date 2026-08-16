"""Features step: lemma vs morphology analytical basis (spec §8.2)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.pipeline.signatures import MORPH_COLUMNS

MODE_LEMMA = "lemma"
MODE_MORPHOLOGY = "morphology"


class FeatureState(rx.State):
    """Choose lemma or morphology features for the rest of the pipeline."""

    mode: str = MODE_LEMMA
    morph_columns: list[str] = list(MORPH_COLUMNS)
    # Default to all morph attrs so morphology mode is usable immediately.
    selected_morph_columns: list[str] = list(MORPH_COLUMNS)
    # When True, rows with subtype=properName are excluded from the experiment;
    # off by default so they collapse to subtype=properName like morphological.py.
    ignore_proper_names: bool = False

    @staticmethod
    def _invalidate_matrix():
        """Any feature change makes the built count matrix stale."""
        from dss_clustering.states.vectorize_state import VectorizeState

        return VectorizeState.refresh_stale

    @rx.event
    async def set_mode(self, mode: str | list[str]):
        # SegmentedControl may pass a single value or a list.
        value = mode[0] if isinstance(mode, list) else mode
        if value in (MODE_LEMMA, MODE_MORPHOLOGY):
            self.mode = value
            # Match the two originals: lemma plateau >=70, morphology >=50,
            # and Ward-artifact leaf marking only in morphology.
            from dss_clustering.states.data_state import DataState
            from dss_clustering.states.dendrogram_state import DendrogramState
            from dss_clustering.states.svd_state import SVDState

            svd = await self.get_state(SVDState)
            svd.plateau_min = 70 if value == MODE_LEMMA else 50
            dendro = await self.get_state(DendrogramState)
            dendro.mark_ward_artifacts = value == MODE_MORPHOLOGY
            return [DataState.load_documents, self._invalidate_matrix()]

    @rx.event
    def toggle_morph_column(self, column: str):
        if column not in self.morph_columns:
            return
        if column in self.selected_morph_columns:
            self.selected_morph_columns = [
                c for c in self.selected_morph_columns if c != column
            ]
        else:
            # Keep stable morph_columns order
            selected = set(self.selected_morph_columns) | {column}
            self.selected_morph_columns = [
                c for c in self.morph_columns if c in selected
            ]
        return self._invalidate_matrix()

    @rx.event
    def select_all_morph_columns(self):
        self.selected_morph_columns = list(self.morph_columns)
        return self._invalidate_matrix()

    @rx.event
    def clear_morph_columns(self):
        self.selected_morph_columns = []
        return self._invalidate_matrix()

    @rx.event
    def set_ignore_proper_names(self, value: bool):
        self.ignore_proper_names = value
        return self._invalidate_matrix()

    @rx.var(cache=True)
    def active_columns(self) -> list[str]:
        if self.mode == MODE_LEMMA:
            return ["clean_lemma"]
        return list(self.selected_morph_columns)

    @rx.var(cache=True)
    def is_morphology(self) -> bool:
        return self.mode == MODE_MORPHOLOGY

    @rx.var(cache=True)
    def show_ignore_proper_names(self) -> bool:
        """Toggle is relevant only when subtype is an active morph attribute."""
        return (
            self.mode == MODE_MORPHOLOGY
            and "subtype" in self.selected_morph_columns
        )

    @rx.var(cache=True)
    def should_ignore_proper_names(self) -> bool:
        """Effective filter used by Vectorize and later steps."""
        return self.show_ignore_proper_names and self.ignore_proper_names

    @rx.var(cache=True)
    def is_ready(self) -> bool:
        return len(self.active_columns) > 0

    @rx.var(cache=True)
    def status_message(self) -> str:
        if self.mode == MODE_LEMMA:
            return "Lemma mode: each occurrence signs as clean_lemma=…"
        if not self.selected_morph_columns:
            return "Select at least one morphological attribute."
        cols = ", ".join(self.selected_morph_columns)
        if self.show_ignore_proper_names:
            ignore_note = (
                " Proper-name rows are excluded."
                if self.ignore_proper_names
                else " Proper-name rows collapse to subtype=properName."
            )
            return f"Morphology mode using {cols}.{ignore_note}"
        return f"Morphology mode using {cols}."

    @rx.var(cache=True)
    def morph_options(self) -> list[dict]:
        selected = set(self.selected_morph_columns)
        return [
            {"column": col, "selected": col in selected}
            for col in self.morph_columns
        ]
