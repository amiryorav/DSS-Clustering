"""Count-matrix construction and rescaling (spec §8.3–8.4)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfTransformer

from dss_clustering.pipeline.signatures import (
    build_signatures_vectorized,
    filter_experiment_rows,
)

RESCALE_MODES = ("raw", "tf", "tfidf")


def build_count_matrix(
    df: pd.DataFrame,
    selected_columns: list[str],
    *,
    ignore_proper_names: bool = False,
    document_ids: list[int] | None = None,
) -> tuple[sp.csr_matrix, list[int], list[str], int]:
    """Build book × signature count matrix from lemma rows.

    Returns ``(matrix, document_ids, signatures, n_source_rows)`` where
    ``n_source_rows`` is the row count after proper-name filtering.
    """
    if not selected_columns:
        raise ValueError("No feature columns selected")
    if "document_id" not in df.columns:
        raise ValueError("DataFrame must include document_id")

    filtered = filter_experiment_rows(df, ignore_proper_names=ignore_proper_names)
    n_source = len(filtered)
    if n_source == 0:
        doc_ids = list(document_ids) if document_ids else []
        empty = sp.csr_matrix((len(doc_ids), 0), dtype=np.float64)
        return empty, doc_ids, [], 0

    sig = build_signatures_vectorized(filtered, selected_columns)

    if document_ids is not None:
        doc_cat = pd.Categorical(filtered["document_id"], categories=document_ids)
    else:
        doc_cat = pd.Categorical(filtered["document_id"])
    sig_cat = pd.Categorical(sig)

    # Drop rows whose document_id was not in the requested categories
    valid = doc_cat.codes >= 0
    if not bool(np.all(valid)):
        doc_codes = doc_cat.codes[valid]
        sig_codes = sig_cat.codes[valid]
        ones = np.ones(int(valid.sum()), dtype=np.float64)
    else:
        doc_codes = doc_cat.codes
        sig_codes = sig_cat.codes
        ones = np.ones(n_source, dtype=np.float64)

    mat = sp.coo_matrix(
        (ones, (doc_codes, sig_codes)),
        shape=(len(doc_cat.categories), len(sig_cat.categories)),
    ).tocsr()
    return mat, list(doc_cat.categories), list(sig_cat.categories), n_source


def rescale_matrix(count_matrix: sp.spmatrix, mode: str) -> sp.csr_matrix:
    """Weight raw counts: raw | tf | tfidf (spec §8.4)."""
    if mode not in RESCALE_MODES:
        raise ValueError(f"Unknown rescale mode: {mode!r}")
    matrix = count_matrix.tocsr()
    if mode == "raw":
        return matrix
    if matrix.shape[0] == 0 or matrix.shape[1] == 0:
        return matrix
    return TfidfTransformer(use_idf=(mode == "tfidf")).fit_transform(matrix)
