"""Compare app Ward-artifact flagging against the original notebook algorithm."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import reflex as rx
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import pdist, squareform
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.metrics import pairwise_distances
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer
from sqlmodel import select

from dss_clustering.models import Document
from dss_clustering.pipeline.aggregate import (
    count_matrix_from_groups,
    signature_count_query,
)
from dss_clustering.pipeline.metrics import ward_artifact_document_ids
from dss_clustering.pipeline.signatures import MORPH_COLUMNS

MODE = sys.argv[1] if len(sys.argv) > 1 else "morphology"
COLUMNS = ["clean_lemma"] if MODE == "lemma" else list(MORPH_COLUMNS)
MIN_ROWS = 100
TOP_K = 5
THRESHOLD = 0.2


def eligible_documents() -> list[int]:
    with rx.session() as session:
        rows = session.exec(
            select(Document.id).where(Document.n_nnn >= MIN_ROWS)
        ).all()
    return [int(doc_id) for doc_id in rows]


def original_flagged(embedding: np.ndarray, Z: np.ndarray, ids: list[int]) -> set[int]:
    """Verbatim port of morphological.py Cell 7."""
    n_books = len(ids)
    euclid = pd.DataFrame(
        squareform(pdist(embedding, metric="euclidean")), index=ids, columns=ids
    )
    cos = pd.DataFrame(
        pairwise_distances(embedding, metric="cosine"), index=ids, columns=ids
    )
    merge_height = np.full((n_books, n_books), np.inf)
    np.fill_diagonal(merge_height, 0.0)
    members = {i: [i] for i in range(n_books)}
    for step, (left, right, height, _) in enumerate(Z):
        left, right = int(left), int(right)
        lm = members.get(left, [left])
        rm = members.get(right, [right])
        for i in lm:
            for j in rm:
                merge_height[i, j] = height
                merge_height[j, i] = height
        members[n_books + step] = lm + rm
    merge_df = pd.DataFrame(merge_height, index=ids, columns=ids)

    def top(book, df):
        return set(df.loc[book].drop(index=book).nsmallest(TOP_K).index)

    scores = {}
    for book in ids:
        nd = top(book, merge_df)
        eu = top(book, euclid)
        co = top(book, cos)
        scores[book] = len(nd & eu & co) / TOP_K
    return {b for b, s in scores.items() if s < THRESHOLD}


def flagged_for(doc_ids: list[int], *, drop_proper: bool, n: int):
    with rx.session() as session:
        groups = session.exec(
            signature_count_query(
                doc_ids, COLUMNS, row_type="NNN", ignore_proper_names=drop_proper
            )
        ).all()
    matrix, ids, _signatures, _n_source = count_matrix_from_groups(groups, doc_ids)
    tfidf = TfidfTransformer().fit_transform(matrix)
    n = min(n, min(tfidf.shape) - 1)
    lsa = make_pipeline(
        TruncatedSVD(n_components=n, random_state=42), Normalizer(copy=False)
    )
    X = np.asarray(lsa.fit_transform(tfidf), dtype=np.float64)
    Z = linkage(X, method="ward", metric="euclidean", optimal_ordering=True)
    return original_flagged(X, Z, list(ids)), ward_artifact_document_ids(X, Z, list(ids)), list(ids)


def main() -> None:
    all_ids = eligible_documents()
    print(f"mode={MODE} eligible_books={len(all_ids)}")

    print("\n-- full corpus, n_components sweep, proper names kept (original) --")
    for n in (50, 120, 190):
        orig, app, ids = flagged_for(all_ids, drop_proper=False, n=n)
        print(
            f"n={n:>4} original={len(orig):>4}/{len(ids)} app={len(app):>4}/{len(ids)} "
            f"identical={orig == app}"
        )

    print("\n-- full corpus, n=120, proper-name setting --")
    for drop in (False, True):
        orig, app, ids = flagged_for(all_ids, drop_proper=drop, n=120)
        pct = 100.0 * len(app) / len(ids)
        print(f"ignore_proper_names={drop!s:<5} flagged={len(app):>4}/{len(ids)} ({pct:.1f}%)")

    print("\n-- subset size effect (n=120, proper names kept) --")
    rng = np.random.default_rng(0)
    for size in (10, 20, 40, 80, 160, len(all_ids)):
        if size > len(all_ids):
            continue
        subset = sorted(rng.choice(all_ids, size=size, replace=False).tolist())
        _orig, app, ids = flagged_for(subset, drop_proper=False, n=120)
        pct = 100.0 * len(app) / len(ids)
        print(f"books={size:>4} flagged={len(app):>4}/{len(ids)} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
