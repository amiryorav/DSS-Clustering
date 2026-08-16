"""Dedicated Help tab: searchable catalog of longer explanations."""

from __future__ import annotations

import reflex as rx

from dss_clustering.help_content import HELP_GROUPS, help_catalog_rows
from dss_clustering.styles import BORDER


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
        rx.heading("Help", size="8"),
        rx.text(
            "Short tips appear next to controls in Analysis. This page keeps "
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
        spacing="4",
        width="100%",
        align="start",
    )
