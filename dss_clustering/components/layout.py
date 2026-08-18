"""App chrome: header, footer, and page shell."""

from __future__ import annotations

import reflex as rx

from dss_clustering.components.busy import busy_overlay
from dss_clustering.components.google_signin import (
    google_provider,
    google_signin_button,
)
from dss_clustering.states.auth_state import AuthState
from dss_clustering.states.nav_state import (
    TAB_ANALYSIS,
    TAB_HELP,
    TAB_HOME,
    NavState,
)
from dss_clustering.styles import (
    ACCENT,
    BORDER,
    BRAND_NAME,
    CONTACT_EMAIL,
    GITHUB_URL,
    MAX_CONTENT,
    SURFACE,
)


def _nav_tab(label: str, value: str) -> rx.Component:
    active = NavState.main_tab == value
    return rx.button(
        label,
        size="2",
        variant=rx.cond(active, "solid", "soft"),
        color_scheme=rx.cond(active, ACCENT, "gray"),
        on_click=NavState.set_main_tab(value),
    )


def _auth_chip() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        rx.hstack(
            rx.badge(
                AuthState.signed_in_email,
                variant="soft",
                color_scheme=ACCENT,
                max_width="14rem",
                overflow="hidden",
                text_overflow="ellipsis",
            ),
            rx.button(
                "Sign out",
                size="1",
                variant="ghost",
                on_click=AuthState.logout_user,
            ),
            spacing="2",
            align="center",
        ),
        # Sign-in stays in the header for optional account saves; analysis
        # itself no longer requires it.
        rx.cond(
            AuthState.has_client_id,
            google_signin_button(),
            rx.fragment(),
        ),
    )


def app_header() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.heading(BRAND_NAME, size="6", weight="bold"),
                rx.cond(
                    NavState.main_tab == TAB_ANALYSIS,
                    rx.text(NavState.step_progress + " · " + NavState.step_label, size="1", color="gray"),
                ),
                spacing="0",
                align="start",
            ),
            rx.spacer(),
            rx.hstack(
                _nav_tab("Home", TAB_HOME),
                _nav_tab("Analysis", TAB_ANALYSIS),
                _nav_tab("Help", TAB_HELP),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.color_mode.button(size="1", variant="ghost"),
                _auth_chip(),
                spacing="2",
                align="center",
            ),
            width="100%",
            align="center",
            spacing="4",
            flex_wrap="wrap",
        ),
        width="100%",
        padding_y="0.85rem",
        padding_x="1.5rem",
        border_bottom=BORDER,
        background=SURFACE,
        position="sticky",
        top="0",
        z_index="20",
    )


def app_footer() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.button(
                    "About",
                    size="1",
                    variant="ghost",
                    on_click=NavState.go_home,
                ),
                rx.text("·", size="2", color="gray"),
                rx.button(
                    "How to use",
                    size="1",
                    variant="ghost",
                    on_click=NavState.go_help,
                ),
                spacing="1",
                align="center",
                justify="center",
                width="100%",
            ),
            rx.hstack(
                rx.text("Amir Yorav", size="2", weight="medium"),
                rx.text("·", size="2", color="gray"),
                rx.link(CONTACT_EMAIL, href=f"mailto:{CONTACT_EMAIL}", size="2"),
                rx.text("·", size="2", color="gray"),
                rx.link("GitHub", href=GITHUB_URL, is_external=True, size="2"),
                spacing="2",
                align="center",
                flex_wrap="wrap",
                justify="center",
                width="100%",
            ),
            spacing="2",
            width="100%",
            align="center",
        ),
        width="100%",
        padding_y="1.25rem",
        padding_x="1.5rem",
        border_top=BORDER,
        margin_top="auto",
    )


def page_shell(body: rx.Component) -> rx.Component:
    return google_provider(_page_body(body))


def _page_body(body: rx.Component) -> rx.Component:
    return rx.vstack(
        busy_overlay(),
        app_header(),
        rx.box(
            body,
            width="100%",
            max_width=MAX_CONTENT,
            margin_x="auto",
            padding_x="1.5rem",
            padding_y="1.5rem",
            flex="1",
        ),
        app_footer(),
        width="100%",
        min_height="100vh",
        spacing="0",
        align="stretch",
        background=SURFACE,
    )
