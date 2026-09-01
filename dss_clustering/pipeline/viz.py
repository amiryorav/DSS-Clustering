"""Visualization-only embeddings: PCA, UMAP, and t-SNE (spec §8.6).

These never feed the dendrogram, tables, or purity metrics — only the 3D plot.

UMAP/t-SNE on a wide count matrix (thousands of features) is prohibitively slow,
so both paths first compress to a modest dense subspace with TruncatedSVD —
the usual practice for text-like sparse data — then embed that.

PCA is mean-centered on the original weighted matrix (densified; sklearn PCA
does not accept sparse input). That is the contrast with the SVD panel:
uncentered Truncated SVD of the analysis embedding.
"""

from __future__ import annotations

import os

# Must land before umap-learn imports Numba. JIT compile + thread pools on the
# 1 GB Cloud VM is what made Compare-4-views hang after PCA.
os.environ.setdefault("NUMBA_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

import numpy as np
import scipy.sparse as sp
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.manifold import TSNE

DEFAULT_RANDOM_STATE = 42
# Enough structure for a 3D viz without spending minutes on the full feature space.
VIZ_SVD_COMPONENTS = 50
# UMAP is optional decoration; never block t-SNE on it.
UMAP_FIT_TIMEOUT_SEC = 90.0
# Pure-Python UMAP (JIT off) is slow; 50 epochs is enough for a 3D sketch.
UMAP_N_EPOCHS = 50


def prepare_viz_matrix(
    matrix: sp.spmatrix | np.ndarray,
    *,
    max_components: int = VIZ_SVD_COMPONENTS,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> np.ndarray:
    """Dense, low-dimensional input for UMAP / t-SNE."""
    n_samples, n_features = matrix.shape
    if n_samples < 2:
        dense = matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix)
        return np.asarray(dense, dtype=np.float64)

    target = min(int(max_components), n_samples - 1, n_features)
    if target < 2 or n_features <= int(max_components):
        dense = matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix)
        return np.asarray(dense, dtype=np.float64)

    reducer = TruncatedSVD(n_components=target, random_state=random_state)
    return np.asarray(reducer.fit_transform(matrix), dtype=np.float64)


def fit_pca(
    matrix: sp.spmatrix | np.ndarray,
    *,
    n_components: int = 3,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> np.ndarray:
    """Mean-centered PCA of the original weighted matrix (not SVD-precompressed)."""
    n_samples, n_features = matrix.shape
    if n_samples < 2:
        raise ValueError("PCA needs at least 2 books.")
    # sklearn.decomposition.PCA densifies anyway; do it once, on the original.
    dense = matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix)
    dense = np.asarray(dense, dtype=np.float64)
    target = min(int(n_components), n_samples - 1, n_features)
    if target < 1:
        raise ValueError("PCA needs at least 1 usable component.")
    coords = PCA(n_components=target, random_state=random_state).fit_transform(
        dense
    )
    if coords.shape[1] < int(n_components):
        pad = np.zeros(
            (coords.shape[0], int(n_components) - coords.shape[1]),
            dtype=np.float64,
        )
        coords = np.hstack([coords, pad])
    return np.asarray(coords, dtype=np.float64)


def umap_from_prepared(
    prepared: np.ndarray,
    *,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    n_components: int = 3,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> np.ndarray:
    """UMAP on an already-compressed dense matrix (the Cloud-safe path)."""
    try:
        import umap
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "umap-learn is required for UMAP plots. "
            "Install with: pip install umap-learn"
        ) from exc

    n_samples = prepared.shape[0]
    if n_samples < 3:
        raise ValueError("UMAP needs at least 3 books.")
    nn = max(2, min(int(n_neighbors), n_samples - 1))
    # random init + single thread: spectral layout and Numba parallel have
    # hung the Cloud worker indefinitely. n_epochs is capped so a JIT-less
    # Python path still finishes on ~200 points.
    reducer = umap.UMAP(
        n_neighbors=nn,
        min_dist=float(min_dist),
        n_components=int(n_components),
        random_state=random_state,
        metric="euclidean",
        n_epochs=UMAP_N_EPOCHS,
        n_jobs=1,
        low_memory=True,
        init="random",
        verbose=False,
    )
    return np.asarray(reducer.fit_transform(prepared), dtype=np.float64)


def fit_umap(
    matrix: sp.spmatrix | np.ndarray,
    *,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    n_components: int = 3,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> np.ndarray:
    """Fit UMAP on a SVD-compressed view of the rescaled count matrix."""
    n_samples = matrix.shape[0]
    if n_samples < 3:
        raise ValueError("UMAP needs at least 3 books.")
    prepared = prepare_viz_matrix(matrix, random_state=random_state)
    return umap_from_prepared(
        prepared,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        n_components=n_components,
        random_state=random_state,
    )


def fit_tsne(
    matrix: sp.spmatrix | np.ndarray,
    *,
    perplexity: float = 30.0,
    n_components: int = 3,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> np.ndarray:
    """Fit t-SNE on a SVD-compressed view of the rescaled count matrix."""
    n_samples = matrix.shape[0]
    if n_samples < 4:
        raise ValueError("t-SNE needs at least 4 books.")
    prepared = prepare_viz_matrix(matrix, random_state=random_state)
    perp = min(float(perplexity), max(5.0, (n_samples - 1) / 3.0))
    reducer = TSNE(
        n_components=int(n_components),
        perplexity=perp,
        random_state=random_state,
        init="pca",
        learning_rate="auto",
        max_iter=400,
    )
    return np.asarray(reducer.fit_transform(prepared), dtype=np.float64)


def viz_params_key(
    method: str,
    *,
    n_neighbors: int,
    min_dist: float,
    perplexity: float,
    rescale_mode: str,
) -> str:
    if method == "umap":
        return f"umap|nn={n_neighbors}|md={min_dist:.4f}|r={rescale_mode}|svd={VIZ_SVD_COMPONENTS}"
    if method == "tsne":
        return f"tsne|p={perplexity:.2f}|r={rescale_mode}|svd={VIZ_SVD_COMPONENTS}"
    if method == "pca":
        return f"pca|r={rescale_mode}"
    return f"{method}|r={rescale_mode}"
