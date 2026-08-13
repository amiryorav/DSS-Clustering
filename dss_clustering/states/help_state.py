"""Toggle which in-app help panels are open (spec §5.3)."""

from __future__ import annotations

import reflex as rx


class HelpState(rx.State):
    """Tracks open help keys for the current browser session."""

    # Reflex serializes lists reliably; treat as an unordered set of keys.
    open_keys: list[str] = []

    @rx.event
    def toggle(self, key: str):
        if key in self.open_keys:
            self.open_keys = [k for k in self.open_keys if k != key]
        else:
            self.open_keys = [*self.open_keys, key]

    @rx.event
    def close_all(self):
        self.open_keys = []
