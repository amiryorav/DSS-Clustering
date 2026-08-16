"""Plotly component that forwards raw relayout data to Reflex events."""

from __future__ import annotations

import reflex as rx
from reflex.components.plotly.plotly import Plotly
from reflex.event import passthrough_event_spec


class PlotlyRelayout(Plotly):
    """Expose camera/zoom changes that the built-in component discards."""

    on_relayout: rx.EventHandler[passthrough_event_spec(dict)]


plotly_relayout = PlotlyRelayout.create
