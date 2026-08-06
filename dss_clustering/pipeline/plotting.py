"""Plotly figure builders for visualization steps."""

from __future__ import annotations

import plotly.graph_objects as go


def make_3d_scatter(
    xs: list[float],
    ys: list[float],
    zs: list[float],
    *,
    labels: list[str],
    hover_labels: list[str],
    colors: list[str],
    document_ids: list[int],
    axis_titles: tuple[str, str, str],
    show_labels: bool,
) -> go.Figure:
    """Identity-colored 3D scatter of books (spec §8.6, SVD mode)."""
    mode = "markers+text" if show_labels else "markers"
    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode=mode,
                text=labels,
                hovertext=hover_labels,
                textposition="top center",
                customdata=document_ids,
                marker={
                    "size": 6,
                    "color": colors,
                    "opacity": 0.9,
                    "line": {"width": 1, "color": "#222"},
                },
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    "x=%{x:.3f}<br>y=%{y:.3f}<br>z=%{z:.3f}"
                    "<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        height=520,
        scene={
            "xaxis_title": axis_titles[0],
            "yaxis_title": axis_titles[1],
            "zaxis_title": axis_titles[2],
            "aspectmode": "cube",
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#c8c8c8"},
        showlegend=False,
    )
    return fig
