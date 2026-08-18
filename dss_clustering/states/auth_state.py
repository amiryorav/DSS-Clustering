"""Google sign-in and ownership of saved manual clusters."""

from __future__ import annotations

import asyncio
import logging
import os

import reflex as rx
from reflex_google_auth import GoogleAuthState

from dss_clustering.repository import claim_or_create_google_user, get_user_profile
from dss_clustering.session import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    issue_session,
    read_session,
)
from dss_clustering.states.user_state import UserState

logger = logging.getLogger(__name__)

# Google only serves its sign-in button to origins registered on the OAuth client,
# so a developer machine that is not registered cannot reach the wizard at all.
# Setting DSS_DEV_SIGNIN=1 opens a local-only door into a dedicated user row.
DEV_SUBJECT = "dev-local-signin"


def dev_signin_requested(value: str | None) -> bool:
    """Whether ``DSS_DEV_SIGNIN`` explicitly opts into the local-only door."""
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


DEV_SIGNIN_ENABLED = dev_signin_requested(os.environ.get("DSS_DEV_SIGNIN"))


class AuthState(GoogleAuthState):
    """Maps a verified Google identity onto the local ``users`` table."""

    current_user_id: int = 0
    signed_in_email: str = ""
    signed_in_name: str = ""
    auth_message: str = ""
    # Last checkpoint reached by the sign-in chain, surfaced in the gate so a
    # stalled login says which step failed instead of silently staying closed.
    auth_stage: str = "idle"
    dev_signed_in: bool = False
    # Our own session, signed server-side. Google's credential expires in about
    # an hour with no refresh token, so gating on it logged people out mid-run.
    session_token: str = rx.Cookie(
        "",
        name=SESSION_COOKIE_NAME,
        max_age=SESSION_MAX_AGE_SECONDS,
        same_site="lax",
    )

    @rx.var(cache=True)
    def is_authenticated(self) -> bool:
        # ``current_user_id`` is only ever set after Google verification or a
        # valid signed cookie, so it is the session on its own.
        return bool(self.current_user_id)

    @rx.var(cache=True)
    def has_client_id(self) -> bool:
        return bool(self.client_id)

    @rx.var(cache=True)
    def dev_signin_available(self) -> bool:
        return DEV_SIGNIN_ENABLED

    @rx.var(cache=True)
    def page_origin(self) -> str:
        """Origin Google validates the button against.

        Opening the app by any other spelling of the same server — 127.0.0.1,
        0.0.0.0, or a second port — is a different origin to Google and gets a 403
        even when localhost itself is authorized.
        """
        return self.router.url.origin

    @rx.var(cache=True)
    def client_id_tail(self) -> str:
        """Last chunk of the client id, enough to compare against the console."""
        head = self.client_id.split(".")[0]
        return head[-12:] if head else "(none)"

    @rx.event
    async def on_success(self, response: dict):
        # ``GoogleAuthState.on_success`` is an EventHandler object, not a plain
        # coroutine, so ``super().on_success(...)`` builds an EventSpec that cannot
        # be awaited. Reach through to the wrapped function instead.
        self.auth_stage = "google returned a credential"
        logger.warning("auth: google callback keys=%s", sorted(response))
        await GoogleAuthState.on_success.fn(self, response)
        return AuthState.sync_user

    @rx.event
    async def sync_user(self):
        """Create or claim a DB user after Google login (or clear on logout)."""
        if not self.token_is_valid:
            self.current_user_id = 0
            self.signed_in_email = ""
            self.signed_in_name = ""
            self.auth_stage = "token rejected (expired or failed verification)"
            logger.warning("auth: token_is_valid=False, aborting sync")
            return

        info = self.tokeninfo or {}
        google_sub = str(info.get("sub") or "").strip()
        if not google_sub:
            self.auth_message = "Google token is missing a subject id."
            self.auth_stage = "token has no subject id"
            logger.warning("auth: token missing sub")
            return

        local = await self.get_state(UserState)
        local_key = (local.owner_key or "").strip()
        try:
            user_id = claim_or_create_google_user(
                google_sub=google_sub,
                email=str(info.get("email") or "") or None,
                display_name=str(info.get("name") or "") or None,
                local_key=local_key or None,
            )
        except Exception as exc:  # noqa: BLE001
            self.auth_message = f"Could not link Google account: {exc}"
            self.auth_stage = "database link failed"
            logger.exception("auth: claim_or_create_google_user failed")
            return

        self.current_user_id = user_id
        self.signed_in_email = str(info.get("email") or "")
        self.signed_in_name = str(info.get("name") or "")
        self.auth_message = ""
        self.auth_stage = "signed in"
        self.session_token = issue_session(user_id)
        local.user_id = user_id
        logger.warning("auth: linked user_id=%s email=%s", user_id, self.signed_in_email)

        return AuthState.load_user_data

    @rx.event
    async def dev_sign_in(self):
        """Enter the wizard as a local development user, bypassing Google."""
        if not DEV_SIGNIN_ENABLED:
            self.auth_message = "Local sign-in is disabled."
            return

        local = await self.get_state(UserState)
        try:
            user_id = claim_or_create_google_user(
                google_sub=DEV_SUBJECT,
                email="dev@localhost",
                display_name="Local developer",
                local_key=(local.owner_key or "").strip() or None,
            )
        except Exception as exc:  # noqa: BLE001
            self.auth_message = f"Could not create the local user: {exc}"
            self.auth_stage = "local sign-in failed"
            logger.exception("auth: dev sign-in failed")
            return

        self.dev_signed_in = True
        self.current_user_id = user_id
        self.signed_in_email = "dev@localhost"
        self.signed_in_name = "Local developer"
        self.auth_message = ""
        self.auth_stage = "signed in (local development)"
        self.session_token = issue_session(user_id)
        local.user_id = user_id

        return AuthState.load_user_data

    @rx.event
    async def load_user_data(self):
        """Pull the account's saved work in one place after any sign-in path."""
        from dss_clustering.states.manual_cluster_state import ManualClusterState
        from dss_clustering.states.saved_config_state import SavedConfigState

        return [ManualClusterState.load_saved_groups, SavedConfigState.load_presets]

    @rx.event
    async def logout_user(self):
        self.logout()
        self.dev_signed_in = False
        self.current_user_id = 0
        self.signed_in_email = ""
        self.signed_in_name = ""
        self.auth_message = ""
        self.auth_stage = "idle"
        self.session_token = ""
        local = await self.get_state(UserState)
        local.user_id = 0

    @rx.event
    async def restore_session(self):
        """Re-open a session from the signed cookie, without Google."""
        user_id = read_session(self.session_token)
        if not user_id:
            return

        profile = await asyncio.to_thread(get_user_profile, user_id)
        if profile is None:
            # The row is gone (or this is a different database), so the token
            # cannot be honoured; drop it instead of half-restoring.
            logger.warning("auth: session cookie for unknown user_id=%s", user_id)
            self.session_token = ""
            return

        self.current_user_id = user_id
        self.signed_in_email = profile["email"]
        self.signed_in_name = profile["display_name"]
        self.auth_stage = "signed in (restored session)"
        local = await self.get_state(UserState)
        local.user_id = user_id
        logger.warning("auth: restored session from cookie for user_id=%s", user_id)
        return AuthState.load_user_data

    @rx.event
    async def ensure_synced(self):
        """Restore the session on page load: Google token first, then cookie."""
        if self.current_user_id:
            return
        if self.token_is_valid:
            return AuthState.sync_user
        return AuthState.restore_session
