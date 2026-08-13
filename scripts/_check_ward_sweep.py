"""Reproduce the original SVD sweep (n_best) and its Ward-artifact count."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import reflex as rx
from scipy.cluster.hierarchy import cophenet, linkage
from scipy.spatial.distance import pdist
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer

from dss_clustering.pipeline.aggregate import (
    count_matrix_from_groups,
    signature_count_query,
)
from dss_clustering.pipeline.metrics import ward_artifact_document_ids
from dss_clustering.pipeline.signatures import MORPH_COLUMNS

from _check_ward_artifacts import eligible_documents  # noqa: E402

CASES = {"morphology": (list(MORPH_COLUMNS), 50), "lemma": (["clean_lemma"], 70)}


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "morphology"
    columns, plateau_min = CASES[mode]

    import _check_ward_artifacts as chk

    chk.MODE = mode

    doc_ids = eligible_documents()
    with rx.session() as session:
        groups = session.exec(
            signature_count_query(
                doc_ids, columns, row_type="NNN", ignore_proper_names=False
            )
        ).all()
    matrix, ids, _sigs, _n = count_matrix_from_groups(groups, doc_ids)
    tfidf = TfidfTransformer().fit_transform(matrix)
    print(f"mode={mode} books={len(ids)} plateau_min={plateau_min} matrix={matrix.shape}")

    best = None
    for n in range(10, 201, 10):
        if n > min(tfidf.shape) - 1:
            break
        lsa = make_pipeline(
            TruncatedSVD(n_components=n, random_state=42), Normalizer(copy=False)
        )
        X = np.asarray(lsa.fit_transform(tfidf), dtype=np.float64)
        Z = linkage(X, method="ward", metric="euclidean")
        cc, _ = cophenet(Z, pdist(X))
        flagged = len(ward_artifact_document_ids(X, Z, list(ids)))
        eligible = n >= plateau_min
        print(f"  n={n:>4} cc={cc:.4f} flagged={flagged:>4} plateau_ok={eligible}")
        if eligible and (best is None or cc > best[1]):
            best = (n, cc, flagged)

    if best:
        n, cc, flagged = best
        print(f"\nORIGINAL n_best={n} cc={cc:.4f} -> flagged {flagged}/{len(ids)}")


if __name__ == "__main__":
    main()
