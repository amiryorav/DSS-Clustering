"""Sweep sizing rules for the SVD step."""

from __future__ import annotations

import numpy as np

from dss_clustering.pipeline.svd import max_svd_components, run_svd_sweep


def _sweep(rows: int, cols: int, **kwargs) -> list[int]:
    matrix = np.random.default_rng(0).random((rows, cols))
    _, _, _, sweep_rows = run_svd_sweep(matrix, normalize=True, **kwargs)
    return [int(r["n"]) for r in sweep_rows]


def test_sweep_covers_the_ceiling_when_range_is_too_wide():
    """A range wider than the matrix must still probe the largest usable size."""
    assert max_svd_components(12, 50) == 11
    sizes = _sweep(12, 50, sweep_min=3, sweep_max=50, sweep_step=3, plateau_min=6)
    assert sizes == [3, 6, 9, 11]


def test_sweep_keeps_requested_grid_when_it_fits():
    sizes = _sweep(40, 60, sweep_min=5, sweep_max=15, sweep_step=5, plateau_min=5)
    assert sizes == [5, 10, 15]


def test_sweep_falls_back_to_ceiling_when_minimum_is_too_high():
    sizes = _sweep(8, 30, sweep_min=20, sweep_max=40, sweep_step=10, plateau_min=20)
    assert sizes == [max_svd_components(8, 30)]
