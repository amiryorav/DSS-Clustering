"""Google sign-in and ownership of saved manual clusters."""

from __future__ import annotations

import reflex as rx
from reflex_google_auth import GoogleAuthState

from dss_clustering.repository import claim_or_create_google_user
from dss_clustering.states.user_state import UserState


class AuthState(GoogleAuthState):
    """Maps a verified Google identity onto the local ``users`` table."""

    current_user_id: int = 0
    signed_in_email: str = ""
    signed_in_name: str = ""
    auth_message: str = ""

    @rx.var(cache=True)
    def is_authenticated(self) -> bool:
        return bool(self.token_is_valid and self.current_user_id)

    @rx.var(cache=True)
    def has_client_id(self) -> bool:
        return bool(self.client_id)

    @rx.event
    async def on_success(self, response: dict):
        await super().on_success(response)
        return AuthState.sync_user

    @rx.event
    async def sync_user(self):
        """Create or claim a DB user after Google login (or clear on logout)."""
        if not self.token_is_valid:
            self.current_user_id = 0
            self.signed_in_email = ""
            self.signed_in_name = ""
            return

        info = self.tokeninfo or {}
        google_sub = str(info.get("sub") or "").strip()
        if not google_sub:
            self.auth_message = "Google token is missing a subject id."
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
            return

        self.current_user_id = user_id
        self.signed_in_email = str(info.get("email") or "")
        self.signed_in_name = str(info.get("name") or "")
        self.auth_message = ""
        local.user_id = user_id

        from dss_clustering.states.manual_cluster_state import ManualClusterState

        return ManualClusterState.load_saved_groups

    @rx.event
    async def logout_user(self):
        self.logout()
        self.current_user_id = 0
        self.signed_in_email = ""
        self.signed_in_name = ""
        self.auth_message = ""
        local = await self.get_state(UserState)
        local.user_id = 0

    @rx.event
    async def ensure_synced(self):
        """Re-link DB user if a valid Google token is already in local storage."""
        if self.token_is_valid and not self.current_user_id:
            return AuthState.sync_user
