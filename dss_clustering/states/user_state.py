"""Current-user identity for owning saved manual clusters.

Google sign-in is not wired up yet, so the "user" is a random key kept in the
browser's local storage and mapped to a row in ``users``. When Google auth
lands, ``users.google_sub`` can be filled in for the same row.
"""

from __future__ import annotations

from uuid import uuid4

import reflex as rx

from dss_clustering.repository import get_or_create_local_user


class UserState(rx.State):
    """Resolves the numeric user id used to scope saved manual clusters."""

    owner_key: str = rx.LocalStorage("", name="dss_owner_key")
    user_id: int = 0
    identity_error: str = ""

    async def ensure_user_id(self) -> int:
        """Return the user id, creating the local identity on first use."""
        if self.user_id:
            return self.user_id
        key = (self.owner_key or "").strip()
        if not key:
            key = uuid4().hex
            self.owner_key = key
        try:
            self.user_id = get_or_create_local_user(key)
            self.identity_error = ""
        except Exception as exc:  # noqa: BLE001
            self.user_id = 0
            self.identity_error = str(exc)
        return self.user_id

    @rx.event
    async def load_identity(self):
        await self.ensure_user_id()
