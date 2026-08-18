"""Hebrew Stylometry Explorer — wizard shell with Google sign-in."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.help_page import help_page
from dss_clustering.components.layout import page_shell
from dss_clustering.components.one_page import one_page
from dss_clustering.models import (  # noqa: F401
    AnalysisPreset,
    Document,
    LemmaRow,
    ManualCluster,
    User,
)
from dss_clustering.states.auth_state import AuthState
from dss_clustering.states.data_state import DataState
from dss_clustering.states.manual_cluster_state import ManualClusterState
from dss_clustering.states.nav_state import (
    TAB_HELP,
    TAB_HOME,
    NavState,
)
from dss_clustering.states.saved_config_state import SavedConfigState


def _main_body() -> rx.Component:
    return rx.match(
        NavState.main_tab,
        (TAB_HOME, one_page()),
        (TAB_HELP, help_page()),
        one_page(),
    )


def index() -> rx.Component:
    return rx.box(
        page_shell(_main_body()),
        width="100%",
        # Both catalog loads are background events: a foreground
        # ``load_documents`` used to sit on the event queue for ~7s (lemma-row
        # aggregation), so Start analysis appeared to do nothing until it finished.
        on_mount=[
            DataState.load_documents,
            ManualClusterState.load_saved_groups,
            SavedConfigState.load_presets,
            AuthState.ensure_synced,
        ],
    )


app = rx.App()
app.add_page(index, title="Hebrew Stylometry Explorer")
