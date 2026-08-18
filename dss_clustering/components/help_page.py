"""Dedicated Help tab: how-to walkthrough plus searchable reference."""

from __future__ import annotations

import reflex as rx

from dss_clustering.help_content import HELP_GROUPS, help_catalog_rows
from dss_clustering.site_content import (
    HOW_TO_STEPS,
    HOW_TO_SUMMARY,
    HOW_TO_TITLE,
)
from dss_clustering.styles import ACCENT, BORDER


class HelpPageState(rx.State):
    """Client-side filter for the Help catalog."""

    query: str = ""

    @rx.event
    def set_query(self, value: str):
        self.query = value

    @rx.var(cache=True)
    def filtered_rows(self) -> list[dict]:
        rows = help_catalog_rows()
        q = self.query.strip().lower()
        if not q:
            return rows
        return [
            row
            for row in rows
            if q in str(row["title"]).lower()
            or q in str(row["summary"]).lower()
            or q in str(row["body"]).lower()
            or q in str(row["group"]).lower()
        ]


def _how_to_step(index: int, title: str, body: str) -> rx.Component:
    return rx.hstack(
        rx.badge(str(index), variant="soft", color_scheme=ACCENT, size="2"),
        rx.vstack(
            rx.text(title, weight="bold", size="3"),
            rx.text(body, size="2", color="gray"),
            spacing="1",
            align="start",
            width="100%",
        ),
        spacing="3",
        align="start",
        width="100%",
        padding="0.85rem",
        border=BORDER,
        border_radius="md",
    )


def _how_to_section() -> rx.Component:
    return rx.vstack(
        rx.heading(HOW_TO_TITLE, size="7", weight="bold"),
        rx.text(HOW_TO_SUMMARY, size="2", color="gray", max_width="44rem"),
        rx.vstack(
            *[
                _how_to_step(i, step["title"], step["body"])
                for i, step in enumerate(HOW_TO_STEPS, start=1)
            ],
            spacing="2",
            width="100%",
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def _help_item(row: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.badge(row["group"], variant="soft", size="1"),
                rx.text(row["title"], weight="bold", size="3"),
                spacing="2",
                align="center",
            ),
            rx.text(row["summary"], size="2", color="gray"),
            rx.text(row["body"], size="2"),
            spacing="2",
            align="start",
            width="100%",
        ),
        width="100%",
        padding="1rem",
        border=BORDER,
        border_radius="md",
    )


def help_page() -> rx.Component:
    return rx.vstack(
        _how_to_section(),
        rx.divider(),
        rx.heading("Reference", size="6", weight="bold"),
        rx.text(
            "Short tips appear next to controls in Analysis. This catalog keeps "
            "the fuller explanations in one place.",
            color="gray",
        ),
        rx.input(
            placeholder="Search help…",
            value=HelpPageState.query,
            on_change=HelpPageState.set_query,
            width="100%",
            max_width="28rem",
        ),
        rx.hstack(
            *[rx.badge(group, variant="outline", size="1") for group in HELP_GROUPS],
            spacing="2",
            flex_wrap="wrap",
        ),
        rx.vstack(
            rx.foreach(HelpPageState.filtered_rows, _help_item),
            spacing="3",
            width="100%",
        ),
        spacing="5",
        width="100%",
        align="start",
    )
