"""Guards for Cloud-light catalog counts and plot defaults."""

from __future__ import annotations

import inspect

from dss_clustering.export.plotly_client import export_plot_script
from dss_clustering.models import Document
from dss_clustering.states.data_state import DataState
from dss_clustering.states.plot_state import (
    DEFAULT_SVD_DIMS,
    LABEL_HIDDEN,
    METHOD_SVD,
    PlotState,
    select_svd_plot_dims,
)


def test_document_model_has_precomputed_counts():
    assert hasattr(Document, "n_nnn")
    assert hasattr(Document, "n_lemma")


def test_catalog_fetch_does_not_group_lemma_rows():
    src = inspect.getsource(DataState._fetch_document_rows)
    assert "group_by" not in src
    assert "n_nnn" in src
    assert "n_lemma" in src


def test_plot_defaults_hide_labels():
    fields = PlotState.get_fields()
    assert fields["label_mode"].default == LABEL_HIDDEN
    assert fields["show_grid"].default is False
    assert fields["method"].default == METHOD_SVD


def test_svd_plot_skips_first_component():
    assert DEFAULT_SVD_DIMS == (1, 2, 3)
    fields = PlotState.get_fields()
    assert fields["dim_x"].default == 1
    assert fields["dim_y"].default == 2
    assert fields["dim_z"].default == 3

    cols, titles, note, labels = select_svd_plot_dims(10, *DEFAULT_SVD_DIMS)
    assert cols == [1, 2, 3]
    assert 0 not in cols
    assert labels == (1, 2, 3)
    assert titles == ("Dim 1", "Dim 2", "Dim 3")
    assert note == "SVD dims 1,2,3"

    clamped, _, clamped_note, _ = select_svd_plot_dims(10, 0, 1, 2)
    assert clamped == [1, 1, 2]
    assert 0 not in clamped
    assert clamped_note == "SVD dims 1,1,2"


def test_export_plot_script_stays_in_the_browser():
    script = export_plot_script("plot-panel-single", "png", "plot")
    assert "dssExportPlotly" in script
    assert "Plotly.toImage" in script
    assert "plot-panel-single" in script
    assert "themedFigure" in script
    assert "pageIsDark" in script
    assert "#ffffff" in script
