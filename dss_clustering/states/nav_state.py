"""Top-level navigation and analysis wizard step index."""

from __future__ import annotations

import reflex as rx

TAB_HOME = "home"
TAB_ANALYSIS = "analysis"
TAB_HELP = "help"

ANALYSIS_STEPS: list[dict[str, str]] = [
    {"id": "presets", "label": "Presets"},
    {"id": "data", "label": "Data"},
    {"id": "features", "label": "Features"},
    {"id": "vectorize", "label": "Vectorize"},
    {"id": "rescale", "label": "Rescale"},
    {"id": "svd", "label": "SVD"},
    {"id": "plot", "label": "3D plot"},
    {"id": "dendrogram", "label": "Dendrogram"},
    {"id": "manual", "label": "Manual group"},
    {"id": "tables", "label": "Tables"},
]


class NavState(rx.State):
    """Home / Analysis / Help tabs and the analysis wizard cursor."""

    main_tab: str = TAB_HOME
    analysis_step: int = 0

    @rx.var(cache=True)
    def step_label(self) -> str:
        if 0 <= self.analysis_step < len(ANALYSIS_STEPS):
            return ANALYSIS_STEPS[self.analysis_step]["label"]
        return ""

    @rx.var(cache=True)
    def step_progress(self) -> str:
        return f"Step {self.analysis_step + 1} of {len(ANALYSIS_STEPS)}"

    @rx.var(cache=True)
    def can_go_back(self) -> bool:
        return self.analysis_step > 0

    @rx.var(cache=True)
    def can_go_next(self) -> bool:
        return self.analysis_step < len(ANALYSIS_STEPS) - 1

    @rx.event
    def set_main_tab(self, tab: str):
        if tab in (TAB_HOME, TAB_ANALYSIS, TAB_HELP):
            self.main_tab = tab

    @rx.event
    def go_home(self):
        self.main_tab = TAB_HOME

    @rx.event
    def go_help(self):
        self.main_tab = TAB_HELP

    @rx.event
    def start_analysis(self):
        self.main_tab = TAB_ANALYSIS
        self.analysis_step = 0

    @rx.event
    def set_analysis_step(self, index: int):
        self.analysis_step = max(0, min(int(index), len(ANALYSIS_STEPS) - 1))

    @rx.event
    def next_step(self):
        if self.analysis_step < len(ANALYSIS_STEPS) - 1:
            self.analysis_step += 1

    @rx.event
    def prev_step(self):
        if self.analysis_step > 0:
            self.analysis_step -= 1
