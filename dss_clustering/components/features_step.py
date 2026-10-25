"""UI for the Features pipeline step."""

from __future__ import annotations

import reflex as rx

from dss_clustering.states.feature_state import FeatureState


def _morph_column_row(item: dict) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=item["selected"],
            on_change=lambda _: FeatureState.toggle_morph_column(item["column"]),
        ),
        rx.text(item["column"], weight="medium", font_family="monospace"),
        width="100%",
        align="center",
        spacing="2",
        padding_y="0.15rem",
    )


def _active_columns() -> rx.Component:
    return rx.hstack(
        rx.text("Active columns:", weight="bold", size="2"),
        rx.cond(
            FeatureState.is_ready,
            rx.flex(
                rx.foreach(
                    FeatureState.active_columns,
                    lambda col: rx.badge(col, variant="outline", size="1"),
                ),
                gap="2",
                flex_wrap="wrap",
            ),
            rx.badge("none selected", color_scheme="red", size="1"),
        ),
        spacing="2",
        align="center",
        flex_wrap="wrap",
    )


def _morphology_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Morphological attributes", weight="bold", size="2"),
            rx.spacer(),
            rx.button(
                "Select all",
                size="1",
                variant="soft",
                on_click=FeatureState.select_all_morph_columns,
            ),
            rx.button(
                "Clear",
                size="1",
                variant="soft",
                on_click=FeatureState.clear_morph_columns,
            ),
            width="100%",
            align="center",
        ),
        rx.vstack(
            rx.foreach(FeatureState.morph_options, _morph_column_row),
            width="100%",
            spacing="0",
            border="1px solid var(--gray-a6)",
            border_radius="md",
            padding="0.75rem",
        ),
        width="100%",
        spacing="3",
        align="start",
    )


def _ignore_proper_names_toggle() -> rx.Component:
    return rx.hstack(
        rx.switch(
            checked=FeatureState.ignore_proper_names,
            on_change=FeatureState.set_ignore_proper_names,
        ),
        rx.vstack(
            rx.text("Ignore proper-name", weight="medium", size="2"),
            rx.text(
                "When checked, subtype=properName rows are dropped from the experiment.",
                size="1",
                color="gray",
            ),
            spacing="0",
            align="start",
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def _collapse_proper_names_toggle() -> rx.Component:
    return rx.vstack(
        rx.text(
            "Collapse proper names into one feature",
            weight="medium",
            size="2",
        ),
        rx.segmented_control.root(
            rx.segmented_control.item("Yes", value="yes"),
            rx.segmented_control.item("No", value="no"),
            value=FeatureState.collapse_proper_names_value,
            on_change=FeatureState.set_collapse_proper_names,
            size="1",
        ),
        rx.text(
            "Yes maps every subtype=properName row to the single feature "
            "subtype=properName. No keeps the other selected grammar "
            "attributes on those rows.",
            size="1",
            color="gray",
        ),
        spacing="2",
        align="start",
        width="100%",
    )


def features_advanced() -> rx.Component:
    """Under-the-hood: morphology column picks, proper names, active columns."""
    from dss_clustering.components.section import under_hood

    return under_hood(
        rx.cond(
            FeatureState.is_morphology,
            _morphology_panel(),
        ),
        rx.cond(
            FeatureState.show_ignore_proper_names,
            _ignore_proper_names_toggle(),
        ),
        rx.cond(
            FeatureState.show_collapse_proper_names,
            _collapse_proper_names_toggle(),
        ),
        _active_columns(),
    )


def features_step() -> rx.Component:
    """Features step: words vs grammar."""
    return rx.vstack(
        rx.segmented_control.root(
            rx.segmented_control.item("Words", value="lemma"),
            rx.segmented_control.item("Grammar", value="morphology"),
            value=FeatureState.mode,
            on_change=FeatureState.set_mode,
            size="2",
        ),
        rx.text(FeatureState.status_message, size="2", color="gray"),
        spacing="4",
        width="100%",
        align="start",
    )
