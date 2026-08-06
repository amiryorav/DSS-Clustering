"""Truncated SVD for the analysis embedding (spec §8.5)."""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy.cluster.hierarchy import cophenet, linkage
from scipy.spatial.distance import pdist
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer

# Fixed seed for reproducible TruncatedSVD (randomized solver). Not a user control.
DEFAULT_RANDOM_STATE = 42


def max_svd_components(n_samples: int, n_features: int) -> int:
    """Largest valid TruncatedSVD n_components for this matrix shape."""
    return max(0, min(n_samples, n_features) - 1)


def pick_best_within_plateau(
    results: list[dict],
    plateau_min: int,
) -> dict:
    """Choose the sweep entry with best cophenetic correlation past plateau_min."""
    if not results:
        raise ValueError("No SVD sweep results to pick from")
    global_best = max(results, key=lambda r: r["cc"])
    plateau_pool = [r for r in results if r["n"] >= plateau_min]
    return max(plateau_pool, key=lambda r: r["cc"]) if plateau_pool else global_best


def _fit_one(
    matrix: sp.spmatrix | np.ndarray,
    n_components: int,
    *,
    normalize: bool,
    random_state: int,
) -> tuple[np.ndarray, float, float]:
    """Fit one TruncatedSVD size; return embedding, variance_explained, cophenetic cc."""
    svd = TruncatedSVD(n_components=n_components, random_state=random_state)
    steps: list = [svd]
    if normalize:
        steps.append(Normalizer(copy=False))
    embedding = make_pipeline(*steps).fit_transform(matrix)
    var_exp = float(svd.explained_variance_ratio_.sum())
    # Spec §7 / §8.5: sweep scoring is always Ward + Euclidean.
    Z = linkage(embedding, method="ward", metric="euclidean", optimal_ordering=True)
    cc, _ = cophenet(Z, pdist(embedding, metric="euclidean"))
    return np.asarray(embedding, dtype=np.float64), var_exp, float(cc)


def run_svd(
    matrix: sp.spmatrix | np.ndarray,
    *,
    enabled: bool,
    n_components: int,
    normalize: bool,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[np.ndarray, int, float]:
    """Fit constant-size TruncatedSVD (or pass through when disabled).

    Returns ``(embedding, n_used, variance_explained)``.
    """
    n_samples, n_features = matrix.shape
    if n_samples == 0 or n_features == 0:
        return np.zeros((n_samples, 0), dtype=np.float64), 0, 0.0

    if not enabled:
        dense = matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix)
        return dense.astype(np.float64, copy=False), int(dense.shape[1]), 1.0

    max_n = max_svd_components(n_samples, n_features)
    if max_n < 1:
        raise ValueError(
            f"Need at least 2 books and 2 signatures for SVD "
            f"(got {n_samples} × {n_features})."
        )

    n_used = max(1, min(int(n_components), max_n))
    embedding, var_exp, _cc = _fit_one(
        matrix, n_used, normalize=normalize, random_state=random_state
    )
    return embedding, n_used, var_exp


def run_svd_sweep(
    matrix: sp.spmatrix | np.ndarray,
    *,
    sweep_min: int,
    sweep_max: int,
    sweep_step: int,
    plateau_min: int,
    normalize: bool,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[np.ndarray, int, float, list[dict]]:
    """Sweep SVD sizes and pick the best by cophenetic correlation (spec §7).

    Returns ``(embedding, n_used, variance_explained, sweep_rows)`` where
    ``sweep_rows`` are UI-safe dicts ``{n, var_exp, cc}``.
    """
    n_samples, n_features = matrix.shape
    max_n = max_svd_components(n_samples, n_features)
    if max_n < 1:
        raise ValueError(
            f"Need at least 2 books and 2 signatures for SVD "
            f"(got {n_samples} × {n_features})."
        )

    lo = max(1, int(sweep_min))
    hi = max(lo, int(sweep_max))
    step = max(1, int(sweep_step))
    sizes = [n for n in range(lo, hi + 1, step) if n <= max_n]
    if not sizes:
        sizes = [max_n]

    results: list[dict] = []
    for n in sizes:
        embedding, var_exp, cc = _fit_one(
            matrix, n, normalize=normalize, random_state=random_state
        )
        results.append(
            {
                "n": n,
                "var_exp": var_exp,
                "cc": cc,
                "X": embedding,
            }
        )

    best = pick_best_within_plateau(results, int(plateau_min))
    sweep_rows = [
        {
            "n": r["n"],
            "var_exp": round(float(r["var_exp"]), 4),
            "cc": round(float(r["cc"]), 4),
            "selected": r["n"] == best["n"],
        }
        for r in results
    ]
    return best["X"], int(best["n"]), float(best["var_exp"]), sweep_rows
