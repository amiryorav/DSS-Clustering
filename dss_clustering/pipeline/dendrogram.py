"""Hierarchical clustering dendrogram (spec §8.7).

SciPy computes the tree; Plotly draws it so leaves can later receive clicks
(Phase 3). Cut-height reclustering uses ``fcluster`` without refitting ``Z``.
"""

from __future__ import annotations

from html import escape

import numpy as np
import plotly.graph_objects as go
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage

from dss_clustering.colors import COLOR_PALETTE

LINKAGE_WARD = "ward"
LINKAGE_AVERAGE = "average"
METRIC_EUCLIDEAN = "euclidean"
METRIC_COSINE = "cosine"

# Links that span multiple cut-clusters stay muted.
MIXED_LINK_COLOR = "#6b7280"

DEFAULT_LABEL_FONT_SIZE = 13
# Horizontal room each leaf needs so rotated labels do not collide.
PX_PER_LEAF = 15


def figure_min_width(n_leaves: int) -> int:
    """Width the tree needs for legible leaf labels; container scrolls past it."""
    return max(320, n_leaves * PX_PER_LEAF + 80)


def cluster_palette(n: int) -> list[str]:
    """Stable repeating palette for cluster ids 1..n."""
    if n <= 0:
        return []
    return [COLOR_PALETTE[i % len(COLOR_PALETTE)] for i in range(n)]


def fit_linkage(
    embedding: np.ndarray,
    *,
    method: str,
    metric: str,
) -> np.ndarray:
    """Fit hierarchical clustering on the analysis-space embedding."""
    if embedding.ndim != 2 or embedding.shape[0] < 2:
        raise ValueError("Need at least 2 books for a dendrogram.")
    method = method if method in (LINKAGE_WARD, LINKAGE_AVERAGE) else LINKAGE_WARD
    if method == LINKAGE_WARD:
        metric = METRIC_EUCLIDEAN
    elif metric not in (METRIC_EUCLIDEAN, METRIC_COSINE):
        metric = METRIC_EUCLIDEAN
    return linkage(
        embedding,
        method=method,
        metric=metric,
        optimal_ordering=True,
    )


def cut_clusters(Z: np.ndarray, cut_height: float) -> np.ndarray:
    """Assign each observation a cluster id at the given distance cut."""
    if Z.size == 0:
        return np.array([], dtype=int)
    t = float(cut_height)
    max_h = float(Z[:, 2].max()) if Z.shape[0] else 0.0
    if max_h <= 0:
        return np.ones(Z.shape[0] + 1, dtype=int)
    t = min(max(t, 0.0), max_h)
    # Cutting at (or above) the root merge yields one cluster; nudge slightly down.
    if t >= max_h:
        t = max_h * (1.0 - 1e-9) if max_h > 0 else 0.0
    return fcluster(Z, t=t, criterion="distance")


def default_cut_height(Z: np.ndarray) -> float:
    """Match the original scripts' default cut between merges 8 and 9."""
    if Z.size == 0:
        return 0.0
    if Z.shape[0] >= 9:
        return float((Z[-8, 2] + Z[-9, 2]) / 2.0)
    # Small interactive selections do not have nine merges.
    return float(Z[:, 2].max()) * 0.7


def max_cut_height(Z: np.ndarray) -> float:
    if Z.size == 0:
        return 1.0
    return float(max(Z[:, 2].max(), 1e-9))


def make_dendrogram_figure(
    Z: np.ndarray,
    *,
    document_ids: list[int],
    leaf_labels: list[str],
    leaf_identity_colors: list[str],
    cluster_ids: np.ndarray,
    cluster_colors: dict[int, str],
    cut_height: float,
    ward_artifact_document_ids: set[int] | None = None,
    label_font_size: int = DEFAULT_LABEL_FONT_SIZE,
) -> go.Figure:
    """Draw SciPy dendrogram geometry as Plotly traces (spec §8.7)."""
    n = len(document_ids)
    if n < 2 or Z.shape[0] != n - 1:
        raise ValueError("Linkage matrix does not match document count.")

    labels = [str(x) for x in leaf_labels]
    R = dendrogram(Z, no_plot=True, labels=labels)
    leaves: list[int] = list(R["leaves"])
    obs_to_x = {obs: 5.0 + 10.0 * pos for pos, obs in enumerate(leaves)}

    traces: list = []
    x_max = 10.0 * n
    traces.append(
        go.Scatter(
            x=[0, x_max],
            y=[cut_height, cut_height],
            mode="lines",
            line={"color": "#f59e0b", "width": 2, "dash": "dash"},
            hoverinfo="skip",
            showlegend=False,
            name="cut",
        )
    )

    for xs, ys in zip(R["icoord"], R["dcoord"]):
        x0, x1 = min(xs), max(xs)
        spanned = [
            obs
            for obs, xpos in obs_to_x.items()
            if x0 - 1e-6 <= xpos <= x1 + 1e-6
        ]
        if not spanned:
            color = MIXED_LINK_COLOR
        else:
            ids = {int(cluster_ids[o]) for o in spanned}
            if len(ids) == 1:
                cid = next(iter(ids))
                color = cluster_colors.get(cid, MIXED_LINK_COLOR)
            else:
                color = MIXED_LINK_COLOR
        traces.append(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": color, "width": 2},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    leaf_x = [obs_to_x[i] for i in leaves]
    leaf_y = [0.0] * n
    leaf_text = [labels[i] for i in leaves]
    leaf_colors = [leaf_identity_colors[i] for i in leaves]
    leaf_docs = [document_ids[i] for i in leaves]
    leaf_clusters = [int(cluster_ids[i]) for i in leaves]
    artifact_ids = ward_artifact_document_ids or set()
    leaf_is_artifact = [doc_id in artifact_ids for doc_id in leaf_docs]

    traces.append(
        go.Scatter(
            x=leaf_x,
            y=leaf_y,
            mode="markers",
            text=leaf_text,
            marker={
                "size": 10,
                "color": leaf_colors,
                "line": {"width": 1, "color": "#222"},
            },
            customdata=[[int(d), int(c)] for d, c in zip(leaf_docs, leaf_clusters)],
            hovertemplate=(
                "<b>%{text}</b><br>cluster=%{customdata[1]}<extra></extra>"
            ),
            showlegend=False,
            name="leaves",
        )
    )

    # Rotated per-leaf annotations: Scatter text cannot be angled, and tick
    # labels cannot carry a per-book identity color.
    annotations = []
    for x, text, color, is_artifact in zip(
        leaf_x, leaf_text, leaf_colors, leaf_is_artifact
    ):
        annotations.append(
            {
            "x": x,
            "y": 0.0,
            "text": f"<i>{escape(text)}</i>" if is_artifact else escape(text),
            "showarrow": False,
            "textangle": -90,
            "xanchor": "center",
            "yanchor": "top",
            "yshift": -10,
            "font": {
                "size": max(9, label_font_size - 2) if is_artifact else label_font_size,
                "color": "#808080" if is_artifact else color,
            },
        }
        )

    longest = max((len(t) for t in leaf_text), default=0)
    bottom_margin = min(280, 60 + int(longest * label_font_size * 0.62))

    fig = go.Figure(data=traces)
    fig.update_layout(
        margin={"l": 60, "r": 30, "t": 30, "b": bottom_margin},
        height=520 + bottom_margin,
        annotations=annotations,
        xaxis={
            "showticklabels": False,
            "showgrid": False,
            "zeroline": False,
            "range": [0, x_max],
            "fixedrange": True,
        },
        yaxis={
            "title": {"text": "Distance", "font": {"size": 14}},
            "showgrid": True,
            "gridcolor": "#333",
            "zeroline": False,
            "range": [0, max_cut_height(Z) * 1.05],
            "tickfont": {"size": 12},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#c8c8c8"},
        showlegend=False,
        autosize=True,
        clickmode="event",
    )
    return fig


def clusters_as_dict(
    document_ids: list[int],
    cluster_ids: np.ndarray,
) -> dict[str, int]:
    """JSON-friendly document_id → cluster_id map."""
    return {str(doc_id): int(cid) for doc_id, cid in zip(document_ids, cluster_ids)}
