"""Shared Plotly click parsing for 3D plot and dendrogram leaves."""

from __future__ import annotations

from typing import Any


def extract_clicked_point(event_data: Any) -> dict | None:
    """Normalize Reflex Plotly's extracted point list and raw Plotly payloads."""
    if isinstance(event_data, (list, tuple)):
        return event_data[0] if event_data and isinstance(event_data[0], dict) else None
    if isinstance(event_data, dict):
        points = event_data.get("points")
        if isinstance(points, (list, tuple)) and points:
            return points[0] if isinstance(points[0], dict) else None
    points = getattr(event_data, "points", None)
    if isinstance(points, (list, tuple)) and points:
        return points[0] if isinstance(points[0], dict) else None
    return None


def extract_clicked_point_number(event_data: Any) -> int | None:
    """Return Plotly's pointNumber/pointIndex from a Reflex click payload."""
    point = extract_clicked_point(event_data)
    if point is None:
        return None
    value = point.get("pointNumber", point.get("pointIndex"))
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def extract_clicked_curve_number(event_data: Any) -> int | None:
    """Return the clicked trace index from a Reflex click payload."""
    point = extract_clicked_point(event_data)
    if point is None:
        return None
    try:
        value = point.get("curveNumber")
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def extract_clicked_document_id(event_data: Any) -> int | None:
    """Return the document_id from a Plotly click event, or None.

    Expects ``customdata`` to be either a bare int (3D scatter) or a
    ``[document_id, cluster_id]`` pair (dendrogram leaf markers).
    """
    try:
        point = extract_clicked_point(event_data)
        if point is None:
            return None
        custom = point.get("customdata")
        if custom is None:
            return None
        # Dendrogram: [doc_id, cluster_id]; 3D: bare int (or length-1 list).
        # Plotly may also deliver typed/binary customdata as a mapping {"0": id, ...}.
        if isinstance(custom, dict):
            if 0 in custom or "0" in custom:
                return int(custom.get(0, custom.get("0")))
            return None
        if isinstance(custom, (list, tuple)):
            if not custom:
                return None
            first = custom[0]
            if isinstance(first, dict) and (0 in first or "0" in first):
                return int(first.get(0, first.get("0")))
            return int(first)
        return int(custom)
    except (TypeError, ValueError, IndexError, KeyError):
        return None
