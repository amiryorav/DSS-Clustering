"""Click helper for Plotly customdata."""

from __future__ import annotations

from dss_clustering.pipeline.clicks import (
    extract_clicked_document_id,
    extract_clicked_point_number,
)
from dss_clustering.pipeline.plotting import make_3d_scatter


def test_extract_from_3d_bare_id():
    assert extract_clicked_document_id({"points": [{"customdata": 7}]}) == 7


def test_extract_from_dendrogram_pair():
    assert (
        extract_clicked_document_id({"points": [{"customdata": [12, 3]}]}) == 12
    )


def test_extract_missing_points():
    assert extract_clicked_document_id({}) is None
    assert extract_clicked_document_id({"points": []}) is None


def test_extract_reflex_plotly_point_list():
    payload = [{"curveNumber": 0, "pointNumber": 4, "x": 1.0}]
    assert extract_clicked_point_number(payload) == 4


def test_3d_scatter_customdata_is_plain_per_point_list():
    figure = make_3d_scatter(
        [0.0],
        [1.0],
        [2.0],
        labels=["A"],
        hover_labels=["Book A"],
        colors=["#123456"],
        document_ids=[17],
        axis_titles=("x", "y", "z"),
        show_labels=True,
    )

    assert figure.data[0].customdata == ([17],)
