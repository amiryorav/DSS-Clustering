"""Property test: vectorized signatures match row-wise row_signature."""

from __future__ import annotations

import pandas as pd

from dss_clustering.pipeline.signatures import (
    build_signatures_vectorized,
    filter_experiment_rows,
    row_signature,
)
from dss_clustering.pipeline.matrix import build_count_matrix


def _rowwise(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return df.apply(lambda r: row_signature(r.to_dict(), cols), axis=1)


def test_lemma_signatures_match():
    df = pd.DataFrame(
        {
            "clean_lemma": ["א", "ב", None, "UNKNOWN", "ג"],
            "subtype": ["common", "common", "common", "common", "properName"],
        }
    )
    cols = ["clean_lemma"]
    filtered = filter_experiment_rows(df, ignore_proper_names=True)
    got = build_signatures_vectorized(filtered, cols)
    expected = _rowwise(filtered, cols)
    pd.testing.assert_series_equal(
        got.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )


def test_morphology_signatures_match():
    df = pd.DataFrame(
        {
            "pos": ["Verb", "Noun", "Verb", None],
            "gender": ["M", "F", "UNKNOWN", "M"],
            "number": ["S", "P", "S", "S"],
            "subtype": ["common", "common", "properName", "common"],
        }
    )
    cols = ["pos", "gender", "number"]
    filtered = filter_experiment_rows(df, ignore_proper_names=True)
    assert len(filtered) == 3  # properName dropped
    got = build_signatures_vectorized(filtered, cols)
    expected = _rowwise(filtered, cols)
    pd.testing.assert_series_equal(
        got.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )


def test_proper_name_rows_collapse_when_included():
    df = pd.DataFrame(
        {
            "pos": ["Verb", "Noun"],
            "gender": ["M", "F"],
            "number": ["S", "P"],
            "subtype": ["properName", "common"],
        }
    )
    cols = ["pos", "gender", "number", "subtype"]
    kept = filter_experiment_rows(df, ignore_proper_names=False)
    got = build_signatures_vectorized(kept, cols)
    expected = _rowwise(kept, cols)
    assert list(got) == ["subtype=properName", "pos=Noun|gender=F|number=P|subtype=common"]
    pd.testing.assert_series_equal(
        got.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )


def test_proper_name_rows_keep_attributes_when_not_collapsed():
    df = pd.DataFrame(
        {
            "pos": ["Verb", "Noun"],
            "gender": ["M", "F"],
            "number": ["S", "P"],
            "subtype": ["properName", "common"],
        }
    )
    cols = ["pos", "gender", "number", "subtype"]
    got = build_signatures_vectorized(df, cols, collapse_proper_names=False)
    expected = df.apply(
        lambda r: row_signature(
            r.to_dict(), cols, collapse_proper_names=False
        ),
        axis=1,
    )
    assert list(got) == [
        "pos=Verb|gender=M|number=S|subtype=properName",
        "pos=Noun|gender=F|number=P|subtype=common",
    ]
    pd.testing.assert_series_equal(
        got.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )


def test_empty_columns_yield_empty_signature():
    df = pd.DataFrame({"pos": ["Verb"], "gender": ["M"]})
    got = build_signatures_vectorized(df, [])
    expected = _rowwise(df, [])
    assert list(got) == list(expected) == ["EMPTY"]


def test_lemma_matrix_drops_blank_and_nan_lemmas():
    df = pd.DataFrame(
        {
            "document_id": [1, 1, 1, 2],
            "clean_lemma": ["א", "", "nan", "ב"],
            "subtype": ["common"] * 4,
        }
    )
    matrix, doc_ids, signatures, n_source = build_count_matrix(
        df,
        ["clean_lemma"],
        document_ids=[1, 2],
    )
    assert doc_ids == [1, 2]
    assert n_source == 2
    assert "EMPTY" not in signatures
    assert matrix.sum() == 2
