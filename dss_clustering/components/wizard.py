"""Analysis wizard: one pipeline step at a time."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.data_step import data_step
from dss_clustering.components.dendrogram_step import dendrogram_step
from dss_clustering.components.features_step import features_step
from dss_clustering.components.google_signin import google_signin_button
from dss_clustering.components.manual_cluster_step import manual_cluster_step
from dss_clustering.components.plot_step import plot_step
from dss_clustering.components.rescale_step import rescale_step
from dss_clustering.components.saved_config_step import saved_config_step
from dss_clustering.components.svd_step import svd_step
from dss_clustering.components.tables_step import tables_step
from dss_clustering.components.vectorize_step import vectorize_step
from dss_clustering.states.auth_state import AuthState
from dss_clustering.states.nav_state import ANALYSIS_STEPS, NavState
from dss_clustering.states.vectorize_state import VectorizeState
from dss_clustering.styles import ACCENT, BORDER

STEP_VECTORIZE = next(
    i for i, step in enumerate(ANALYSIS_STEPS) if step["id"] == "vectorize"
)


def _step_rail_item(index: int, label: str) -> rx.Component:
    active = NavState.analysis_step == index
    return rx.button(
        label,
        size="1",
        variant=rx.cond(active, "solid", "soft"),
        color_scheme=rx.cond(active, ACCENT, "gray"),
        on_click=NavState.set_analysis_step(index),
        disabled=VectorizeState.is_stale & (index > STEP_VECTORIZE),
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
        rx.button(
            "Back",
            size="2",
            variant="soft",
            disabled=NavState.can_go_back == False,
            on_click=NavState.prev_step,
        ),
        rx.spacer(),
        rx.text(NavState.step_progress, size="2", color="gray"),
        rx.spacer(),
        rx.button(
            "Next",
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
        position="sticky",
        bottom="0",
        background="var(--gray-1)",
        z_index="10",
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


def _sign_in_gate() -> rx.Component:
    return rx.vstack(
        rx.heading("Sign in to analyze", size="7"),
        rx.text(
            "The analysis wizard saves manual groups under your Google account. "
            "Home and Help stay available without signing in.",
            color="gray",
            max_width="36rem",
        ),
        rx.cond(
            AuthState.has_client_id,
            rx.vstack(
                google_signin_button(),
                rx.text(
                    "After Google completes, your session links automatically.",
                    size="1",
                    color="gray",
                ),
                spacing="3",
                align="start",
            ),
            rx.callout(
                "Add GOOGLE_CLIENT_ID to your environment (see .env.example), "
                "restart the app, then use Sign in with Google.",
                icon="triangle-alert",
                color_scheme="amber",
                width="100%",
            ),
        ),
        rx.cond(
            AuthState.auth_message != "",
            rx.text(AuthState.auth_message, size="2", color="red"),
        ),
        rx.text(
            "Sign-in status: "
            + AuthState.auth_stage
            + " · token valid: "
            + rx.cond(AuthState.token_is_valid, "yes", "no")
            + " · linked user: "
            + AuthState.current_user_id.to(str),
            size="1",
            color="gray",
        ),
        rx.text(
            "This page's origin is "
            + AuthState.page_origin
            + " (client …"
            + AuthState.client_id_tail
            + "). Google rejects sign-in unless this exact origin is an "
            + "Authorized JavaScript origin on that client.",
            size="1",
            color="gray",
        ),
        rx.cond(
            AuthState.dev_signin_available,
            rx.vstack(
                rx.divider(),
                rx.text(
                    "Development mode: continue without Google to work on the "
                    "pipeline while this origin is unregistered.",
                    size="1",
                    color="gray",
                ),
                rx.button(
                    "Continue as local developer",
                    size="2",
                    variant="soft",
                    on_click=AuthState.dev_sign_in,
                ),
                spacing="2",
                align="start",
                width="100%",
            ),
        ),
        spacing="4",
        align="start",
        padding_y="2rem",
        width="100%",
    )


def analysis_wizard() -> rx.Component:
    body = rx.vstack(
        _step_rail(),
        rx.box(_step_body(), width="100%", padding_y="1rem"),
        _wizard_footer(),
        width="100%",
        spacing="3",
        align="start",
    )
    # When Google is configured, Analysis requires sign-in. Without a client
    # id (local smoke), keep the previous local-key ownership path.
    return rx.cond(
        AuthState.has_client_id,
        rx.cond(AuthState.is_authenticated, body, _sign_in_gate()),
        body,
    )
