"""UMAP/t-SNE prep and table score formatting."""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from dss_clustering.pipeline.metrics import series_to_rows
from dss_clustering.pipeline.viz import fit_pca, prepare_viz_matrix


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


def test_fit_pca_three_components_from_sparse():
    rng = np.random.default_rng(0)
    dense = rng.normal(size=(20, 50))
    coords = fit_pca(sp.csr_matrix(dense), n_components=3)
    assert coords.shape == (20, 3)
    assert coords.dtype == np.float64


def test_fit_pca_matches_sklearn_on_original_matrix():
    """PCA must not TruncatedSVD-compress first (UMAP/t-SNE still do)."""
    from sklearn.decomposition import PCA

    rng = np.random.default_rng(0)
    dense = rng.normal(size=(15, 200))
    expected = PCA(n_components=3, random_state=42).fit_transform(dense)
    coords = fit_pca(sp.csr_matrix(dense), n_components=3)
    assert np.allclose(coords, expected)


def test_fit_pca_pads_when_fewer_than_three_components():
    coords = fit_pca(np.array([[1.0, 0.0], [0.0, 1.0]]), n_components=3)
    assert coords.shape == (2, 3)
    assert np.allclose(coords[:, 2], 0.0)


def test_series_to_rows_formats_scores_to_two_decimals():
    series = pd.Series([1.23456, 0.1], index=["a", "b"])
    rows = series_to_rows(series, kind="top")
    assert rows[0]["score"] == "1.23"
    assert rows[1]["score"] == "0.10"
