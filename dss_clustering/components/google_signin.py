"""Google sign-in button wired to :class:`AuthState`."""

from __future__ import annotations

import reflex as rx
from reflex_google_auth import google_oauth_provider
from reflex_google_auth.google_auth import GoogleLogin

from dss_clustering.states.auth_state import AuthState


class ThemedGoogleLogin(GoogleLogin):
    """``GoogleLogin`` with the upstream widget's appearance props exposed."""

    # Only single-word props survive: Reflex camel-cases prop names, so a
    # snake_case one like ``logo_alignment`` reaches Google as ``logoAlignment``
    # and is silently ignored.
    theme: rx.Var[str]
    size: rx.Var[str]
    shape: rx.Var[str]
    text: rx.Var[str]


def google_signin_button() -> rx.Component:
    """Sign-in button that reports back to ``AuthState``.

    ``GoogleLogin`` defaults ``on_success`` to ``GoogleAuthState.on_success``, which
    stores the token but never links the local user row. That left
    ``AuthState.current_user_id`` at 0, so the analysis gate stayed closed until the
    next page load ran ``ensure_synced``.
    """
    return google_oauth_provider(
        ThemedGoogleLogin.create(
            on_success=AuthState.on_success,
            # Google renders the button itself, so it cannot pick up our palette;
            # switch variants with the color mode instead.
            theme=rx.color_mode_cond(light="outline", dark="filled_black"),
            size="large",
            shape="pill",
        )
    )
