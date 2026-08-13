"""Hebrew stylometry explorer — pipeline through help + export (Phases 5–6)."""

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
from dss_clustering.models import Document, LemmaRow  # noqa: F401
from dss_clustering.states.data_state import DataState


def index() -> rx.Component:
    # rx.container caps content at its Radix inner max-width (880px), which the
    # wide dendrogram needs to escape.
    return rx.box(
        rx.vstack(
            rx.heading("Hebrew Stylometry Explorer", size="8"),
            rx.text(
                "Interactive lexical and morphological comparison of Mikra, Mishna, and DSS.",
                color="gray",
            ),
            rx.divider(),
            saved_config_step(),
            rx.divider(),
            data_step(),
            rx.divider(),
            features_step(),
            rx.divider(),
            vectorize_step(),
            rx.divider(),
            rescale_step(),
            rx.divider(),
            svd_step(),
            rx.divider(),
            plot_step(),
            rx.divider(),
            dendrogram_step(),
            rx.divider(),
            manual_cluster_step(),
            rx.divider(),
            tables_step(),
            spacing="5",
            padding_y="2em",
            width="100%",
            align="start",
        ),
        width="100%",
        max_width="100%",
        padding_x="1.5rem",
        on_mount=DataState.load_documents,
    )


app = rx.App()
app.add_page(index, title="Hebrew Stylometry Explorer")
