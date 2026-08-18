"""UMAP/t-SNE prep and table score formatting."""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from dss_clustering.pipeline.metrics import series_to_rows
from dss_clustering.pipeline.viz import prepare_viz_matrix


def test_prepare_viz_matrix_compresses_wide_sparse():
    matrix = sp.random(40, 2000, density=0.05, format="csr", random_state=0)
    prepared = prepare_viz_matrix(matrix, max_components=50)
    # TruncatedSVD cannot exceed n_samples - 1.
    assert prepared.shape == (40, 39)
    assert prepared.dtype == np.float64


def test_prepare_viz_matrix_leaves_narrow_matrices():
    matrix = np.eye(8, dtype=np.float64)
    prepared = prepare_viz_matrix(matrix, max_components=50)
    assert prepared.shape == (8, 8)


def test_series_to_rows_formats_scores_to_two_decimals():
    series = pd.Series([1.23456, 0.1], index=["a", "b"])
    rows = series_to_rows(series, kind="top")
    assert rows[0]["score"] == "1.23"
    assert rows[1]["score"] == "0.10"
