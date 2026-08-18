"""Analysis wizard: one pipeline step at a time.

Guests can run the full pipeline. Sign-in is only required to persist presets
and manual groups under an account.
"""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.data_step import data_step
from dss_clustering.components.dendrogram_step import dendrogram_step
from dss_clustering.components.features_step import features_step
from dss_clustering.components.manual_cluster_step import manual_cluster_step
from dss_clustering.components.plot_step import plot_step
from dss_clustering.components.rescale_step import rescale_step
from dss_clustering.components.saved_config_step import saved_config_step
from dss_clustering.components.svd_step import svd_step
from dss_clustering.components.tables_step import tables_step
from dss_clustering.components.vectorize_step import vectorize_step
from dss_clustering.states.nav_state import ANALYSIS_STEPS, NavState
from dss_clustering.states.vectorize_state import VectorizeState
from dss_clustering.styles import ACCENT, BORDER

STEP_VECTORIZE = next(
    i for i, step in enumerate(ANALYSIS_STEPS) if step["id"] == "vectorize"
)


def _tip_button(label: str, tip: str, **kwargs) -> rx.Component:
    return rx.tooltip(
        rx.button(label, **kwargs),
        content=tip,
        side="top",
        side_offset=4,
    )


def _step_rail_item(index: int, label: str) -> rx.Component:
    active = NavState.analysis_step == index
    return rx.tooltip(
        rx.button(
            label,
            size="1",
            variant=rx.cond(active, "solid", "soft"),
            color_scheme=rx.cond(active, ACCENT, "gray"),
            on_click=NavState.set_analysis_step(index),
            disabled=VectorizeState.is_stale & (index > STEP_VECTORIZE),
        ),
        content=f"Go to {label}",
        side="bottom",
        side_offset=4,
    )


def _step_rail() -> rx.Component:
    return rx.hstack(
        *[
            _step_rail_item(i, step["label"])
            for i, step in enumerate(ANALYSIS_STEPS)
        ],
        spacing="2",
        flex_wrap="wrap",
        width="100%",
        padding="0.75rem",
        border=BORDER,
        border_radius="md",
    )


def _wizard_footer() -> rx.Component:
    return rx.hstack(
        _tip_button(
            "Back",
            "Previous analysis step",
            size="2",
            variant="soft",
            disabled=NavState.can_go_back == False,
            on_click=NavState.prev_step,
        ),
        rx.spacer(),
        rx.text(NavState.step_progress, size="2", color="gray"),
        rx.spacer(),
        _tip_button(
            "Next",
            "Next analysis step",
            size="2",
            color_scheme=ACCENT,
            # Leaving Vectorize with a stale matrix would carry old results
            # forward, so the rebuild is mandatory here.
            disabled=(NavState.can_go_next == False)
            | ((NavState.analysis_step == STEP_VECTORIZE) & VectorizeState.is_stale),
            on_click=NavState.next_step,
        ),
        width="100%",
        align="center",
        padding_y="0.75rem",
        border_top=BORDER,
    )


def _step_body() -> rx.Component:
    return rx.match(
        NavState.analysis_step,
        (0, saved_config_step()),
        (1, data_step()),
        (2, features_step()),
        (3, vectorize_step()),
        (4, rescale_step()),
        (5, svd_step()),
        (6, plot_step()),
        (7, dendrogram_step()),
        (8, manual_cluster_step()),
        (9, tables_step()),
        data_step(),
    )


def analysis_wizard() -> rx.Component:
    """Full wizard — guests analyze freely; account saves need sign-in."""
    return rx.vstack(
        _step_rail(),
        rx.box(_step_body(), width="100%", padding_y="1rem"),
        _wizard_footer(),
        width="100%",
        spacing="3",
        align="start",
    )
