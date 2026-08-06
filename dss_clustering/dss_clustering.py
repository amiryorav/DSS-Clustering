"""Hebrew stylometry explorer — Phase 1 core pipeline."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.data_step import data_step
from dss_clustering.components.features_step import features_step
from dss_clustering.components.plot_step import plot_step
from dss_clustering.components.rescale_step import rescale_step
from dss_clustering.components.svd_step import svd_step
from dss_clustering.components.vectorize_step import vectorize_step
from dss_clustering.models import Document, LemmaRow  # noqa: F401
from dss_clustering.states.data_state import DataState


def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Hebrew Stylometry Explorer", size="8"),
            rx.text(
                "Interactive lexical and morphological comparison of Mikra, Mishna, and DSS.",
                color="gray",
            ),
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
            spacing="5",
            padding_y="2em",
            width="100%",
            align="start",
        ),
        max_width="1100px",
        on_mount=DataState.load_documents,
    )


app = rx.App()
app.add_page(index, title="Hebrew Stylometry Explorer")
