"""Visualization-only embeddings: UMAP and t-SNE (spec §8.6).

These never feed the dendrogram, tables, or purity metrics — only the 3D plot.

UMAP/t-SNE on a wide count matrix (thousands of features) is prohibitively slow,
so both paths first compress to a modest dense subspace with TruncatedSVD —
the usual practice for text-like sparse data — then embed that.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import TSNE

DEFAULT_RANDOM_STATE = 42
# Enough structure for a 3D viz without spending minutes on the full feature space.
VIZ_SVD_COMPONENTS = 50


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


def fit_umap(
    matrix: sp.spmatrix | np.ndarray,
    *,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    n_components: int = 3,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> np.ndarray:
    """Fit UMAP on a SVD-compressed view of the rescaled count matrix."""
    try:
        import umap
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "umap-learn is required for UMAP plots. "
            "Install with: pip install umap-learn"
        ) from exc

    n_samples = matrix.shape[0]
    if n_samples < 3:
        raise ValueError("UMAP needs at least 3 books.")
    prepared = prepare_viz_matrix(matrix, random_state=random_state)
    nn = max(2, min(int(n_neighbors), n_samples - 1))
    # Cap epochs on small corpora — full default schedules burn time for little gain.
    n_epochs = 200 if n_samples < 200 else None
    reducer = umap.UMAP(
        n_neighbors=nn,
        min_dist=float(min_dist),
        n_components=int(n_components),
        random_state=random_state,
        metric="euclidean",
        n_epochs=n_epochs,
        verbose=False,
    )
    return np.asarray(reducer.fit_transform(prepared), dtype=np.float64)


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
    # sklearn requires perplexity < n_samples
    perp = min(float(perplexity), max(5.0, (n_samples - 1) / 3.0))
    reducer = TSNE(
        n_components=int(n_components),
        perplexity=perp,
        random_state=random_state,
        init="pca",
        learning_rate="auto",
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
    return f"{method}|r={rescale_mode}"
