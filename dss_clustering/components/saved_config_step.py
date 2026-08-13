"""UI for session AnalysisConfig presets (spec §8.10, local-only)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.help import help_button, help_panel
from dss_clustering.states.saved_config_state import SavedConfigState


def _preset_row(preset: dict) -> rx.Component:
    return rx.hstack(
        rx.text(preset["name"], weight="medium"),
        rx.text(preset["created_at"], size="1", color="gray"),
        rx.spacer(),
        rx.button(
            "Load",
            size="1",
            variant="soft",
            on_click=SavedConfigState.load(preset["id"]),
        ),
        width="100%",
        align="center",
        spacing="3",
    )


def saved_config_step() -> rx.Component:
    """Save / load named pipeline configurations for this session."""
    return rx.vstack(
        rx.hstack(
            rx.heading("Analysis presets", size="5"),
            help_button("presets"),
            spacing="2",
            align="center",
        ),
        help_panel("presets"),
        rx.text(
            "Save the current Data→Dendrogram controls as a named preset for "
            "this browser session (not persisted to the database).",
            color="gray",
            size="2",
        ),
        rx.hstack(
            rx.input(
                placeholder="Preset name…",
                value=SavedConfigState.preset_name,
                on_change=SavedConfigState.set_preset_name,
                size="2",
                max_width="16rem",
                width="100%",
            ),
            rx.button(
                "Save configuration",
                on_click=SavedConfigState.save,
                size="2",
            ),
            spacing="3",
            align="center",
            flex_wrap="wrap",
        ),
        rx.cond(
            SavedConfigState.presets.length() > 0,
            rx.vstack(
                rx.foreach(SavedConfigState.presets, _preset_row),
                width="100%",
                spacing="2",
            ),
            rx.text("No saved presets yet.", size="2", color="gray"),
        ),
        rx.text(SavedConfigState.status_message, size="2", color="gray"),
        spacing="3",
        width="100%",
        align="start",
    )
