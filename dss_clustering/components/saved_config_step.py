"""UI for saved AnalysisConfig presets (spec §8.10)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.google_signin import google_signin_button
from dss_clustering.states.auth_state import AuthState
from dss_clustering.states.saved_config_state import SavedConfigState


def _tip_button(label: str, tip: str, **kwargs) -> rx.Component:
    return rx.tooltip(
        rx.button(label, **kwargs),
        content=tip,
        side="top",
        side_offset=4,
    )


def _preset_row(preset: dict) -> rx.Component:
    """One preset line. Kept narrow so the buttons sit beside the name."""
    return rx.hstack(
        rx.text(
            preset["name"],
            weight="medium",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
        ),
        rx.text(
            preset["created_at"],
            size="1",
            color="gray",
            white_space="nowrap",
        ),
        _tip_button(
            "Load",
            "Restore this preset and rebuild the pipeline",
            size="1",
            variant="soft",
            on_click=SavedConfigState.load(preset["id"]),
        ),
        _tip_button(
            "Delete",
            "Remove this preset from your account",
            size="1",
            variant="ghost",
            color_scheme="red",
            on_click=SavedConfigState.delete(preset["id"]),
        ),
        width="100%",
        align="center",
        spacing="3",
    )


def saved_config_step() -> rx.Component:
    """Save / load named pipeline configurations for the current account."""
    return rx.vstack(
        rx.cond(
            AuthState.is_authenticated,
            rx.vstack(
                rx.hstack(
                    rx.input(
                        placeholder="Preset name…",
                        value=SavedConfigState.preset_name,
                        on_change=SavedConfigState.set_preset_name,
                        size="2",
                        max_width="16rem",
                        width="100%",
                    ),
                    _tip_button(
                        "Save configuration",
                        "Store the current controls under your account",
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
                        max_width="30rem",
                        spacing="2",
                    ),
                    rx.text("No saved presets yet.", size="2", color="gray"),
                ),
                width="100%",
                spacing="3",
                align="start",
            ),
            rx.callout(
                rx.hstack(
                    rx.text(
                        "Working as guest. Sign in to save presets to your account.",
                        size="2",
                    ),
                    rx.cond(AuthState.has_client_id, google_signin_button()),
                    spacing="3",
                    align="center",
                    flex_wrap="wrap",
                ),
                icon="info",
                color_scheme="gray",
                width="100%",
            ),
        ),
        rx.text(SavedConfigState.status_message, size="2", color="gray"),
        spacing="3",
        width="100%",
        align="start",
    )
