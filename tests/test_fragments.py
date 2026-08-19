"""Tests for DSS fragment locator parsing and exclusion filters."""

from __future__ import annotations

from dss_clustering.pipeline.fragments import (
    _fragment_sort_key,
    fragment_key,
)


def test_fragment_key_simple():
    assert fragment_key("6Q18 f13:2") == "f13"
    assert fragment_key("6Q18 f14:1") == "f14"


def test_fragment_key_complex_label():
    assert fragment_key("4Q394 f8iii:6") == "f8iii"
    assert fragment_key("4Q176a f1:3") == "f1"


def test_fragment_key_no_fragment():
    assert fragment_key("CD 1:1") is None
    assert fragment_key("Gen. 1:1") is None
    assert fragment_key("Ber. 2:3") is None
    assert fragment_key(None) is None
    assert fragment_key("") is None
    assert fragment_key("   ") is None


def test_fragment_key_strips_whitespace():
    assert fragment_key("  6Q18 f13:2  ") == "f13"


def test_fragment_sort_numeric():
    keys = ["f2", "f10", "f1", "f13"]
    assert sorted(keys, key=_fragment_sort_key) == ["f1", "f2", "f10", "f13"]


def test_exclusion_sql_filter_empty():
    from dss_clustering.pipeline.fragments import exclusion_sql_filter

    assert exclusion_sql_filter({}) is None
    assert exclusion_sql_filter({"1": []}) is None


def test_exclusion_sql_filter_builds_clause():
    from dss_clustering.pipeline.fragments import exclusion_sql_filter

    clause = exclusion_sql_filter(
        {"42": ["f13", "f14"]},
        document_books={"42": "6Q18"},
    )
    assert clause is not None


def test_analysis_config_excluded_fragments_roundtrip():
    from dss_clustering.pipeline.config import AnalysisConfig

    cfg = AnalysisConfig(
        selected_document_ids=(1, 2),
        feature_mode="lemma",
        morph_columns=("pos",),
        apply_proper_name_exception=False,
        rescale_mode="tf",
        svd_enabled=True,
        svd_mode="constant",
        svd_n_components=10,
        svd_sweep_range=None,
        svd_normalize=True,
        svd_random_state=42,
        svd_plateau_min=3,
        linkage_method="ward",
        distance_metric="euclidean",
        cut_height=0.5,
        excluded_fragments={"7": ["f13"]},
    )
    restored = AnalysisConfig.from_dict(cfg.to_dict())
    assert restored.excluded_fragments == {"7": ["f13"]}


def test_analysis_config_missing_excluded_defaults_empty():
    from dss_clustering.pipeline.config import AnalysisConfig

    payload = {
        "selected_document_ids": [1],
        "feature_mode": "lemma",
        "morph_columns": ["pos"],
        "apply_proper_name_exception": False,
        "rescale_mode": "tf",
        "svd_enabled": False,
        "svd_mode": "constant",
        "svd_n_components": 5,
        "svd_sweep_range": None,
        "svd_normalize": False,
        "svd_random_state": 0,
        "svd_plateau_min": 1,
        "linkage_method": "ward",
        "distance_metric": "euclidean",
        "cut_height": 1.0,
    }
    restored = AnalysisConfig.from_dict(payload)
    assert restored.excluded_fragments == {}
