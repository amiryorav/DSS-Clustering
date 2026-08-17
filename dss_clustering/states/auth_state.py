"""Google sign-in and ownership of saved manual clusters."""

from __future__ import annotations

import logging
import os

import reflex as rx
from reflex_google_auth import GoogleAuthState

from dss_clustering.repository import claim_or_create_google_user
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

    @rx.var(cache=True)
    def is_authenticated(self) -> bool:
        return bool((self.token_is_valid or self.dev_signed_in) and self.current_user_id)

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
        local.user_id = user_id
        logger.warning("auth: linked user_id=%s email=%s", user_id, self.signed_in_email)

        from dss_clustering.states.manual_cluster_state import ManualClusterState

        return ManualClusterState.load_saved_groups

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
        local.user_id = user_id

        from dss_clustering.states.manual_cluster_state import ManualClusterState

        return ManualClusterState.load_saved_groups

    @rx.event
    async def logout_user(self):
        self.logout()
        self.dev_signed_in = False
        self.current_user_id = 0
        self.signed_in_email = ""
        self.signed_in_name = ""
        self.auth_message = ""
        self.auth_stage = "idle"
        local = await self.get_state(UserState)
        local.user_id = 0

    @rx.event
    async def ensure_synced(self):
        """Re-link DB user if a valid Google token is already in local storage."""
        if self.token_is_valid and not self.current_user_id:
            return AuthState.sync_user
