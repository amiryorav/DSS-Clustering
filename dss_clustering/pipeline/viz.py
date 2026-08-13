"""Visualization-only embeddings: UMAP and t-SNE (spec §8.6).

These never feed the dendrogram, tables, or purity metrics — only the 3D plot.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from sklearn.manifold import TSNE

DEFAULT_RANDOM_STATE = 42


def fit_umap(
    matrix: sp.spmatrix | np.ndarray,
    *,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    n_components: int = 3,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> np.ndarray:
    """Fit UMAP on the rescaled count matrix → (n, n_components)."""
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
    nn = max(2, min(int(n_neighbors), n_samples - 1))
    reducer = umap.UMAP(
        n_neighbors=nn,
        min_dist=float(min_dist),
        n_components=int(n_components),
        random_state=random_state,
        metric="euclidean",
    )
    return np.asarray(reducer.fit_transform(matrix), dtype=np.float64)


def fit_tsne(
    matrix: sp.spmatrix | np.ndarray,
    *,
    perplexity: float = 30.0,
    n_components: int = 3,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> np.ndarray:
    """Fit t-SNE on the rescaled count matrix → (n, n_components)."""
    n_samples = matrix.shape[0]
    if n_samples < 4:
        raise ValueError("t-SNE needs at least 4 books.")
    # sklearn requires perplexity < n_samples
    perp = min(float(perplexity), max(5.0, (n_samples - 1) / 3.0))
    dense = matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix)
    reducer = TSNE(
        n_components=int(n_components),
        perplexity=perp,
        random_state=random_state,
        init="pca",
        learning_rate="auto",
    )
    return np.asarray(reducer.fit_transform(dense), dtype=np.float64)


def viz_params_key(
    method: str,
    *,
    n_neighbors: int,
    min_dist: float,
    perplexity: float,
    rescale_mode: str,
) -> str:
    if method == "umap":
        return f"umap|nn={n_neighbors}|md={min_dist:.4f}|r={rescale_mode}"
    if method == "tsne":
        return f"tsne|p={perplexity:.2f}|r={rescale_mode}"
    return f"{method}|r={rescale_mode}"
