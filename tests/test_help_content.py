"""Smoke test for static help content keys used by the UI."""

from __future__ import annotations

from dss_clustering.help_content import HELP_CONTENT, help_entry


REQUIRED_KEYS = {
    "presets",
    "data",
    "features",
    "vectorize",
    "rescale",
    "svd",
    "plot",
    "dendrogram",
    "manual_cluster",
    "tables",
    "cophenetic_correlation",
    "top_features",
    "distinctive_features",
    "gap_features",
    "consistency_score",
    "ward",
    "average_link",
    "tf_tfidf",
    "umap",
    "tsne",
}


def test_help_content_covers_ui_keys():
    missing = REQUIRED_KEYS - set(HELP_CONTENT)
    assert not missing, f"Missing help keys: {sorted(missing)}"
    for key in REQUIRED_KEYS:
        entry = help_entry(key)
        assert entry["title"].strip()
        assert entry["body"].strip()
