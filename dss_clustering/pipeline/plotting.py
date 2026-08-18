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
    height: int = 780,
    uirevision: str = "plot-camera",
    marker_size: int = 6,
) -> go.Figure:
    """Identity- or cluster-colored 3D scatter of books (spec §8.6)."""
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
                # A list per point avoids Plotly's typed-array encoding, which
                # Reflex does not consistently deserialize in click payloads.
                customdata=[[int(document_id)] for document_id in document_ids],
                marker={
                    "size": marker_size,
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
        height=height,
        # Keep the user's camera stable when unrelated Reflex state updates
        # cause react-plotly.js to receive the figure again. The zoom/rotate
        # buttons bump this value, which is what lets a programmatic camera
        # override the camera the user last dragged to.
        uirevision=uirevision,
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
        clickmode="event",
    )
    return fig


def make_sweep_chart(
    results: list[dict],
) -> go.Figure:
    """Plot SVD sweep cophenetic correlation and variance vs dimension count."""
    ns = [r["n"] for r in results]
    ccs = [r["cc"] for r in results]
    vars_ = [r["var_exp"] for r in results]
    selected_n = next((r["n"] for r in results if r.get("selected")), None)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ns,
            y=ccs,
            mode="lines+markers",
            name="Cophenetic",
            marker={"size": 8},
            customdata=ns,
            hovertemplate="dims=%{x}<br>cc=%{y:.4f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ns,
            y=vars_,
            mode="lines+markers",
            name="Variance",
            yaxis="y2",
            marker={"size": 8, "symbol": "diamond"},
            customdata=ns,
            hovertemplate="dims=%{x}<br>var=%{y:.4f}<extra></extra>",
        )
    )
    if selected_n is not None:
        fig.add_vline(
            x=selected_n,
            line_dash="dash",
            line_color="#22c55e",
            annotation_text=f"selected {selected_n}",
            annotation_position="top",
        )
    fig.update_layout(
        margin={"l": 40, "r": 40, "t": 30, "b": 40},
        height=280,
        xaxis={"title": "SVD dimensions"},
        yaxis={"title": "Cophenetic correlation", "side": "left"},
        yaxis2={
            "title": "Variance explained",
            "overlaying": "y",
            "side": "right",
            "range": [0, 1.05],
        },
        legend={"orientation": "h", "y": 1.12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#c8c8c8"},
        clickmode="event+select",
    )
    return fig
