"""Smoke tests for metrics helpers used by tables / manual cluster."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage

from dss_clustering.pipeline.dendrogram import make_dendrogram_figure
from dss_clustering.pipeline.metrics import (
    build_phase_rows,
    corpus_wide_stability,
    diff_features,
    nearest_group_by_centroid,
    shared_features,
    ward_artifact_document_ids,
    ward_merge_height,
)


def test_shared_and_diff_features():
    frame = pd.DataFrame(
        {
            "a": [10.0, 9.0, 1.0, 0.0],
            "b": [0.0, 1.0, 8.0, 9.0],
            "c": [5.0, 5.0, 5.0, 5.0],
        },
        index=[1, 2, 3, 4],
    )
    top = shared_features(frame, [1, 2], n=2)
    assert list(top.index)[0] == "a"
    distinctive, gap = diff_features(frame, [1, 2], [3, 4], n=2)
    assert "a" in distinctive.index
    assert "b" in gap.index


def test_ward_merge_height_and_stability_shape():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(6, 4))
    Z = linkage(X, method="ward")
    ids = list(range(10, 16))
    ward = ward_merge_height(Z, ids)
    assert ward.shape == (6, 6)
    # Fake agreement distances: identical neighbor views → stability 1.0
    dist = pd.DataFrame(np.eye(6), index=ids, columns=ids)
    # Make off-diagonal increasing so neighbors are deterministic
    for i, a in enumerate(ids):
        for j, b in enumerate(ids):
            if i != j:
                dist.loc[a, b] = abs(i - j)
    stab = corpus_wide_stability(
        ids,
        ward_dist=dist,
        svd_euclidean_dist=dist,
        svd_cosine_dist=dist,
        k=2,
    )
    assert stab == 1.0


def test_lemma_table_rows_hide_internal_prefix():
    rows = build_phase_rows(
        pd.Series([0.8], index=["clean_lemma=אמר"]),
        pd.Series(dtype=float),
        pd.Series(dtype=float),
    )
    assert rows["top"][0]["signature"] == "אמר"


def test_nearest_group_uses_embedding_centroids():
    embedding = pd.DataFrame(
        [[1.0, 0.0], [0.9, 0.1], [0.8, 0.2], [-1.0, 0.0]],
        index=[1, 2, 3, 4],
    )
    nearest = nearest_group_by_centroid(embedding, [1], [[2, 3], [4]])
    assert nearest == [2, 3]


def test_ward_artifact_ids_follow_three_view_threshold():
    rng = np.random.default_rng(12)
    embedding = rng.normal(size=(8, 4))
    ids = list(range(100, 108))
    Z = linkage(embedding, method="ward")
    flagged = ward_artifact_document_ids(
        embedding,
        Z,
        ids,
        k=5,
        threshold=1.01,
    )
    # Every possible score is <= 1; threshold above 1 flags every leaf.
    assert flagged == set(ids)


def test_ward_artifact_leaf_is_gray_and_italic():
    embedding = np.array([[0.0, 0.0], [1.0, 0.0], [3.0, 0.0]])
    Z = linkage(embedding, method="ward")
    fig = make_dendrogram_figure(
        Z,
        document_ids=[10, 11, 12],
        leaf_labels=["A", "B", "C"],
        leaf_identity_colors=["red", "green", "blue"],
        cluster_ids=np.array([1, 1, 2]),
        cluster_colors={1: "orange", 2: "purple"},
        cut_height=1.5,
        ward_artifact_document_ids={11},
    )
    annotation = next(a for a in fig.layout.annotations if "B" in a.text)
    assert annotation.text == "<i>B</i>"
    assert annotation.font.color == "#808080"
