"""UI for the Data pipeline step."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.help import tip_button
from dss_clustering.states.data_state import DataState


def _document_row(doc: dict) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=doc["selected"],
            on_change=lambda _: DataState.toggle_document(doc["id"]),
        ),
        rx.text(doc["label"], weight="medium"),
        rx.spacer(),
        rx.text(doc["n_entries"], size="2", color="gray"),
        rx.text("valid rows", size="2", color="gray"),
        width="100%",
        padding_y="0.2rem",
        align="center",
        spacing="2",
    )


def _corpus_section(corpus: str) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.checkbox(
                checked=DataState.corpus_all_selected[corpus],
                on_change=lambda _: DataState.toggle_corpus_visible(corpus),
            ),
            rx.heading(DataState.corpus_labels[corpus], size="4"),
            spacing="2",
            align="center",
        ),
        rx.vstack(
            rx.foreach(DataState.filtered_documents[corpus], _document_row),
            width="100%",
            spacing="0",
            max_height="18rem",
            overflow_y="auto",
            border="1px solid var(--gray-a6)",
            border_radius="md",
            padding="0.75rem",
        ),
        width="100%",
        spacing="2",
        align="start",
    )


def data_advanced() -> rx.Component:
    """Under-the-hood: the minimum-valid-rows threshold and a catalog reload."""
    from dss_clustering.components.section import under_hood

    return under_hood(
        rx.hstack(
            rx.text("Minimum valid rows per book", size="2", white_space="nowrap"),
            rx.input(
                type="number",
                value=DataState.min_entries_per_book.to(str),
                on_change=DataState.set_min_entries,
                width="6rem",
            ),
            tip_button(
                "Reload catalog",
                "Reload the book catalog from the database",
                on_click=DataState.load_documents,
                loading=DataState.is_loading,
                size="2",
                variant="soft",
            ),
            spacing="3",
            align="center",
            flex_wrap="wrap",
        ),
        rx.text(DataState.status_message, size="2", color="gray"),
    )


def data_step() -> rx.Component:
    """Data step panel: search and book selection."""
    return rx.vstack(
        rx.hstack(
            rx.input(
                placeholder="Search books...",
                value=DataState.search_text,
                on_change=DataState.set_search_text,
                max_width="18rem",
                width="100%",
            ),
            tip_button(
                "Select all visible",
                "Select every book currently shown (after search)",
                on_click=DataState.select_all_visible,
                variant="soft",
            ),
            tip_button(
                "Clear selection",
                "Deselect all books",
                on_click=DataState.clear_selection,
                variant="soft",
            ),
            spacing="3",
            flex_wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.cond(
            DataState.is_loading,
            rx.hstack(
                rx.spinner(size="2"),
                rx.text("Loading book catalog…", size="2", color="gray"),
                spacing="2",
                align="center",
            ),
        ),
        rx.hstack(
            rx.text("Selected:", weight="bold"),
            rx.text(DataState.selected_count),
            spacing="2",
        ),
        rx.vstack(
            rx.foreach(DataState.visible_corpora, _corpus_section),
            width="100%",
            spacing="5",
            align="start",
        ),
        spacing="4",
        width="100%",
        align="start",
    )
