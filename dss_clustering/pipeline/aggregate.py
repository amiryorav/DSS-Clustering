"""Server-side signature aggregation (spec §8.3).

Building the count matrix by loading every lemma row into pandas costs memory
proportional to the corpus (~750k rows for Mikra + Mishna), which exceeds small
deployment instances. Postgres can group the rows into ``(document, signature,
count)`` triples instead, so the transferred volume is exactly the non-zero
count of the resulting matrix.

The SQL signature expression must stay byte-identical to
:func:`dss_clustering.pipeline.signatures.row_signature`.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

import numpy as np
import scipy.sparse as sp
from sqlalchemy import and_, case, func, literal
from sqlmodel import select

from dss_clustering.models import LemmaRow
from dss_clustering.pipeline.signatures import (
    MISSING_STRINGS,
    PROPER_NAME_SIGNATURE,
    PROPER_NAME_SUBTYPE,
)

EMPTY_SIGNATURE = "EMPTY"


def _signature_expression(selected_columns: Sequence[str]):
    """SQL equivalent of ``row_signature`` for the given column order."""
    missing = tuple(MISSING_STRINGS)
    parts = []
    for col in selected_columns:
        column = getattr(LemmaRow, col)
        parts.append(
            case(
                (
                    and_(column.is_not(None), column.notin_(missing)),
                    literal(f"{col}=") + column,
                ),
                else_=None,
            )
        )
    # concat_ws skips NULL parts, matching the Python comprehension's filtering.
    joined = func.concat_ws("|", *parts)
    normal = func.coalesce(func.nullif(joined, ""), EMPTY_SIGNATURE)
    # Lemma mode has no proper-name atomic signature (lemma.py).
    if tuple(selected_columns) == ("clean_lemma",):
        return normal
    # morphological.py: subtype=properName collapses the whole row.
    return case(
        (
            LemmaRow.subtype == PROPER_NAME_SUBTYPE,
            literal(PROPER_NAME_SIGNATURE),
        ),
        else_=normal,
    )


def signature_count_query(
    document_ids: Sequence[int],
    selected_columns: Sequence[str],
    *,
    row_type: str,
    ignore_proper_names: bool,
    excluded_fragments: Mapping[int, Sequence[str]]
    | Mapping[str, Sequence[str]]
    | None = None,
    document_books: Mapping[str, str] | None = None,
):
    """Select ``(document_id, signature, count)`` grouped in the database."""
    if not selected_columns:
        raise ValueError("No feature columns selected")

    signature = _signature_expression(selected_columns)
    query = (
        select(
            LemmaRow.document_id,
            signature.label("signature"),
            func.count().label("n"),
        )
        .where(LemmaRow.document_id.in_(list(document_ids)))
        .where(LemmaRow.row_type == row_type)
    )
    if tuple(selected_columns) == ("clean_lemma",):
        # lemma.py Cell 2 excludes missing/blank/"nan" lemmas before both the
        # minimum-book-size check and count-matrix construction. Without this,
        # _signature_expression maps the 77k blank source rows to "EMPTY".
        cleaned_lemma = func.trim(LemmaRow.clean_lemma)
        query = (
            query.where(LemmaRow.clean_lemma.is_not(None))
            .where(cleaned_lemma != "")
            .where(func.lower(cleaned_lemma) != "nan")
        )
    if ignore_proper_names:
        # NULL subtypes are kept, matching the pandas `!=` comparison.
        query = query.where(LemmaRow.subtype.is_distinct_from(PROPER_NAME_SUBTYPE))
    if excluded_fragments:
        from dss_clustering.pipeline.fragments import exclusion_sql_filter

        clause = exclusion_sql_filter(
            excluded_fragments, document_books=document_books
        )
        if clause is not None:
            query = query.where(clause)
    return query.group_by(LemmaRow.document_id, signature)


def count_matrix_from_groups(
    groups: Iterable[tuple[int, str, int]],
    document_ids: Sequence[int],
) -> tuple[sp.csr_matrix, list[int], list[str], int]:
    """Assemble the sparse count matrix from grouped signature counts.

    Returns ``(matrix, document_ids, signatures, n_source_rows)``.
    """
    doc_ids = list(document_ids)
    doc_index = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    sig_index: dict[str, int] = {}

    rows: list[int] = []
    cols: list[int] = []
    values: list[int] = []
    n_source = 0

    for document_id, signature, count in groups:
        row = doc_index.get(document_id)
        if row is None:
            continue
        col = sig_index.get(signature)
        if col is None:
            col = len(sig_index)
            sig_index[signature] = col
        rows.append(row)
        cols.append(col)
        values.append(int(count))
        n_source += int(count)

    signatures = list(sig_index)
    shape = (len(doc_ids), len(signatures))
    if not values:
        return sp.csr_matrix(shape, dtype=np.float64), doc_ids, signatures, 0

    matrix = sp.coo_matrix(
        (
            np.asarray(values, dtype=np.float64),
            (np.asarray(rows, dtype=np.int32), np.asarray(cols, dtype=np.int32)),
        ),
        shape=shape,
    ).tocsr()
    return matrix, doc_ids, signatures, n_source
