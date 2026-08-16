"""Global busy flag so long computations can block the UI."""

from __future__ import annotations

import reflex as rx


class BusyState(rx.State):
    """Reference-counted busy indicator shared by every long pipeline step."""

    depth: int = 0
    message: str = "Working…"

    @rx.var(cache=True)
    def is_busy(self) -> bool:
        return self.depth > 0

    def begin(self, message: str = "Working…") -> None:
        """Enter a busy section. Safe to nest across chained events."""
        self.depth += 1
        self.message = message

    def end(self) -> None:
        """Leave a busy section."""
        self.depth = max(0, self.depth - 1)

    @rx.event
    def release(self):
        """Leave a busy section from a chained event.

        A handler that hands work off to follow-up events queues this last, so
        the overlay stays up for the whole chain instead of blinking between
        steps.
        """
        self.end()

    @rx.event
    def clear(self):
        """Escape hatch if a handler crashed before releasing the flag."""
        self.depth = 0
