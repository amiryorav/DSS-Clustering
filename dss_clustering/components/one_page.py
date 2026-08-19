"""The single scrolling page: hero plus every analysis section in order.

Replaces the old landing tab and the 10-step wizard. Everything a visitor
needs is on one page, top to bottom, in plain language.
"""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.data_step import data_advanced, data_step
from dss_clustering.components.dendrogram_step import (
    dendrogram_advanced,
    dendrogram_step,
)
from dss_clustering.components.features_step import features_advanced, features_step
from dss_clustering.components.plot_step import plot_advanced, plot_step
from dss_clustering.components.run_section import run_advanced, run_controls
from dss_clustering.components.saved_config_step import saved_config_step
from dss_clustering.components.section import page_section
from dss_clustering.components.tables_step import tables_step
from dss_clustering.components.help import tip_button
from dss_clustering.site_content import ABOUT_BODY, ABOUT_SUMMARY
from dss_clustering.states.dendrogram_state import DendrogramState
from dss_clustering.states.nav_state import ANCHOR_TEXTS, NavState
from dss_clustering.states.plot_state import PlotState
from dss_clustering.styles import ACCENT, BLURB_SIZE, MAX_CONTENT, MAX_TEXT, BRAND_NAME


def _hero() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading(BRAND_NAME, size="9", weight="bold"),
            rx.text(
                ABOUT_SUMMARY,
                size="5",
                color="gray",
                max_width=MAX_TEXT,
            ),
            rx.text(ABOUT_BODY, size=BLURB_SIZE, max_width=MAX_TEXT),
            tip_button(
                "Choose your texts",
                "Scroll down to pick which books to include",
                on_click=NavState.scroll_to(ANCHOR_TEXTS),
                size="4",
                color_scheme=ACCENT,
            ),
            spacing="5",
            align="start",
            width="100%",
            max_width=MAX_CONTENT,
            margin_x="auto",
        ),
        width="100%",
        padding_y="4rem",
        padding_x="1.5rem",
    )


def one_page() -> rx.Component:
    """Hero followed by the seven analysis sections."""
    return rx.vstack(
        _hero(),
        page_section(
            "texts",
            "1",
            "Choose your texts",
            "Every eligible book starts selected. Search and untick anything "
            "you want to leave out of the comparison.",
            data_step(),
            advanced=data_advanced(),
            alt=True,
        ),
        page_section(
            "compare",
            "2",
            "Words or grammar?",
            "Compare the texts by the words they use, or by their grammar.",
            features_step(),
            advanced=features_advanced(),
        ),
        page_section(
            "run",
            "3",
            "Run the analysis",
            "One click builds the whole comparison — counting, weighting, and "
            "reducing the numbers behind the scenes.",
            run_controls(),
            advanced=run_advanced(),
            alt=True,
        ),
        page_section(
            "map",
            "4",
            "The 3D map",
            "Every book is a dot. Books that use language in similar ways sit "
            "close together. Drag to rotate, or use the buttons.",
            plot_step(),
            advanced=plot_advanced(),
            ready=PlotState.has_figure,
            placeholder="Run the analysis above to see the 3D map.",
        ),
        page_section(
            "tree",
            "5",
            "The Tree",
            "The same closeness, drawn as a tree. Slide the cut line to split "
            "the books into more or fewer clusters.",
            dendrogram_step(),
            advanced=dendrogram_advanced(),
            ready=DendrogramState.has_tree,
            placeholder="Run the analysis above to build the tree.",
            alt=True,
        ),
        page_section(
            "numbers",
            "6",
            "The numbers",
            "Compare any two groups side by side and read which words or "
            "grammar features set them apart. You can also create your own "
            "groups to use as either side.",
            tables_step(),
            ready=DendrogramState.has_tree,
            placeholder="Run the analysis above to compare groups.",
        ),
        page_section(
            "save",
            "7",
            "Save & export",
            "Sign in to keep your settings and hand-picked groups for next "
            "time. You can export any plot or table as you go.",
            saved_config_step(),
            alt=True,
        ),
        spacing="0",
        width="100%",
        align="stretch",
    )
