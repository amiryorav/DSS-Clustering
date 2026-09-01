"""Feature tables and purity / consistency / stability metrics (spec §7)."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cophenet
from scipy.spatial.distance import squareform
from sklearn.metrics.pairwise import cosine_distances, euclidean_distances

from dss_clustering.pipeline.runtime import MatrixBundle

# Original lemma.py / morphological.py cluster-comparison tables use 20.
TOP_N = 50
PURITY_K = 10
CONSISTENCY_K = 5
STABILITY_K = 5

SCOPE_CORPUS = "corpus"
SCOPE_CLUSTER = "cluster"
SCOPE_BOOK = "book"
SCOPE_MANUAL = "manual"
# Corpus-scope sentinel meaning "every selected book", not one named corpus.
CORPUS_ALL = "__all__"
COMPARE_CORPUS = "corpus"
COMPARE_ALL_OTHER = "all_other_selected"
COMPARE_EXISTING_CLUSTER = "existing_cluster"


def active_frame(bundle: MatrixBundle, mode: str) -> pd.DataFrame:
    """Dense book × signature DataFrame from the rescaled sparse matrix."""
    matrix = bundle.rescaled(mode)
    dense = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)
    return pd.DataFrame(
        dense,
        index=list(bundle.document_ids),
        columns=list(bundle.signatures),
    )


def shared_features(
    frame: pd.DataFrame,
    group: Iterable[int],
    n: int = TOP_N,
) -> pd.Series:
    """Top features for a group: mean usage, no comparison."""
    ids = [i for i in group if i in frame.index]
    if not ids:
        return pd.Series(dtype=float)
    return frame.loc[ids].mean().nlargest(n)


def common_features(
    frame: pd.DataFrame,
    group_a: Iterable[int],
    group_b: Iterable[int],
    n: int = TOP_N,
) -> pd.Series:
    """Features used in both groups, ranked by mean usage on the union."""
    a = [i for i in group_a if i in frame.index]
    b = [i for i in group_b if i in frame.index]
    if not a or not b:
        return pd.Series(dtype=float)
    a_mean = frame.loc[a].mean()
    b_mean = frame.loc[b].mean()
    both = (a_mean > 0) & (b_mean > 0)
    if not bool(both.any()):
        return pd.Series(dtype=float)
    union_ids = list(dict.fromkeys(a + b))
    return frame.loc[union_ids].mean().loc[both].nlargest(n)


def diff_features(
    frame: pd.DataFrame,
    group_a: Iterable[int],
    group_b: Iterable[int],
    n: int = TOP_N,
) -> tuple[pd.Series, pd.Series]:
    """Distinctive (a>b) and gap (a<b) from a single delta."""
    a = [i for i in group_a if i in frame.index]
    b = [i for i in group_b if i in frame.index]
    if not a or not b:
        empty = pd.Series(dtype=float)
        return empty, empty
    delta = frame.loc[a].mean() - frame.loc[b].mean()
    return delta.nlargest(n), delta.nsmallest(n)


def nearest_group_by_centroid(
    embedding: pd.DataFrame,
    group: Iterable[int],
    candidate_groups: Iterable[Iterable[int]],
) -> list[int]:
    """Return the candidate group nearest to ``group`` by SVD cosine centroid."""
    source_ids = [i for i in group if i in embedding.index]
    if not source_ids:
        return []
    source = embedding.loc[source_ids].mean().to_numpy().reshape(1, -1)
    best_group: list[int] = []
    best_distance = float("inf")
    for candidate in candidate_groups:
        ids = [i for i in candidate if i in embedding.index]
        if not ids:
            continue
        centroid = embedding.loc[ids].mean().to_numpy().reshape(1, -1)
        distance = float(cosine_distances(source, centroid)[0, 0])
        if distance < best_distance:
            best_distance = distance
            best_group = ids
    return best_group


def _display_signature(signature: object) -> str:
    """Human-facing feature label; lemma tables show the lemma itself."""
    text = str(signature)
    prefix = "clean_lemma="
    return text[len(prefix) :] if text.startswith(prefix) else text


def series_to_rows(series: pd.Series, *, kind: str) -> list[dict]:
    """Turn a ranked feature Series into table rows (scores shown to 2 d.p.)."""
    return [
        {
            "rank": i + 1,
            "signature": _display_signature(sig),
            "score": f"{float(val):.2f}",
            "kind": kind,
        }
        for i, (sig, val) in enumerate(series.items())
    ]


def build_phase_rows(
    top: pd.Series,
    distinctive: pd.Series,
    gap: pd.Series,
) -> dict[str, list[dict]]:
    return {
        "top": series_to_rows(top, kind="top"),
        "distinctive": series_to_rows(distinctive, kind="distinctive"),
        "gap": series_to_rows(gap, kind="gap"),
    }


def cosine_distance_frame(frame: pd.DataFrame) -> pd.DataFrame:
    ids = list(frame.index)
    dist = cosine_distances(frame.values)
    return pd.DataFrame(dist, index=ids, columns=ids)


def euclidean_distance_frame(coords: np.ndarray, document_ids: list[int]) -> pd.DataFrame:
    dist = euclidean_distances(coords)
    return pd.DataFrame(dist, index=document_ids, columns=document_ids)


def cosine_distance_embedding(
    coords: np.ndarray, document_ids: list[int]
) -> pd.DataFrame:
    dist = cosine_distances(coords)
    return pd.DataFrame(dist, index=document_ids, columns=document_ids)


def ward_merge_height(Z: np.ndarray, document_ids: list[int]) -> pd.DataFrame:
    """Pairwise cophenetic (merge-height) distances from linkage Z."""
    condensed = cophenet(Z)
    square = squareform(condensed)
    return pd.DataFrame(square, index=document_ids, columns=document_ids)


def get_top_neighbors(book: int, distances: pd.DataFrame, k: int) -> list[int]:
    if book not in distances.index:
        return []
    row = distances.loc[book].drop(index=book, errors="ignore")
    if row.empty:
        return []
    return [int(i) for i in row.nsmallest(k).index.tolist()]


def corpus_purity(
    book: int,
    *,
    document_corpus: dict[int, str],
    active_dist: pd.DataFrame,
    svd_cosine_dist: pd.DataFrame,
    ward_dist: pd.DataFrame,
    k: int = PURITY_K,
) -> dict:
    """Does this book's neighborhood match its own corpus label?"""
    own_corpus = document_corpus.get(book, "")
    views = {
        "active": get_top_neighbors(book, active_dist, k),
        "svd": get_top_neighbors(book, svd_cosine_dist, k),
        "ward": get_top_neighbors(book, ward_dist, k),
    }
    fracs = {
        name: (
            sum(document_corpus.get(b, "") == own_corpus for b in nn) / len(nn)
            if nn
            else 0.0
        )
        for name, nn in views.items()
    }
    hits = sum(f >= 0.5 for f in fracs.values())
    verdict = "Typical" if hits >= 2 else ("Mixed" if hits == 1 else "Outlier")
    return {
        "verdict": verdict,
        "purity_score": float(sum(fracs.values()) / len(fracs)) if fracs else 0.0,
        "fracs": fracs,
    }


def nn_consistency(
    book: int,
    group: Iterable[int],
    *,
    active_dist: pd.DataFrame,
    svd_cosine_dist: pd.DataFrame,
    ward_dist: pd.DataFrame,
    k: int = CONSISTENCY_K,
) -> str:
    """Do this group's other members show up as this book's neighbors?"""
    partners = set(group) - {book}
    views = {
        "active": get_top_neighbors(book, active_dist, k),
        "svd": get_top_neighbors(book, svd_cosine_dist, k),
        "ward": get_top_neighbors(book, ward_dist, k),
    }
    hits = sum(bool(partners & set(nn)) for nn in views.values())
    return "Genuine" if hits >= 2 else ("Partial" if hits == 1 else "Artifact")


def nn_consistency_for_group(
    group: Iterable[int],
    *,
    active_dist: pd.DataFrame,
    svd_cosine_dist: pd.DataFrame,
    ward_dist: pd.DataFrame,
    k: int = CONSISTENCY_K,
) -> str:
    """Majority consistency label across books in the group."""
    members = list(group)
    if len(members) < 2:
        return "Artifact"
    labels = [
        nn_consistency(
            b,
            members,
            active_dist=active_dist,
            svd_cosine_dist=svd_cosine_dist,
            ward_dist=ward_dist,
            k=k,
        )
        for b in members
    ]
    # Prefer Genuine > Partial > Artifact by count.
    order = {"Genuine": 2, "Partial": 1, "Artifact": 0}
    best = max(set(labels), key=lambda lab: (labels.count(lab), order.get(lab, 0)))
    return best


def nn_consistency_for_cluster(
    cluster_id: int,
    cluster_of: dict[int, int],
    *,
    active_dist: pd.DataFrame,
    svd_cosine_dist: pd.DataFrame,
    ward_dist: pd.DataFrame,
    k: int = CONSISTENCY_K,
) -> str:
    members = [doc for doc, cid in cluster_of.items() if cid == cluster_id]
    return nn_consistency_for_group(
        members,
        active_dist=active_dist,
        svd_cosine_dist=svd_cosine_dist,
        ward_dist=ward_dist,
        k=k,
    )


def cross_check_book(
    book: int,
    *,
    ward_dist: pd.DataFrame,
    svd_euclidean_dist: pd.DataFrame,
    svd_cosine_dist: pd.DataFrame,
    k: int = STABILITY_K,
) -> int:
    views = [
        get_top_neighbors(book, ward_dist, k),
        get_top_neighbors(book, svd_euclidean_dist, k),
        get_top_neighbors(book, svd_cosine_dist, k),
    ]
    return len(set(views[0]) & set(views[1]) & set(views[2]))


def corpus_wide_stability(
    document_ids: list[int],
    *,
    ward_dist: pd.DataFrame,
    svd_euclidean_dist: pd.DataFrame,
    svd_cosine_dist: pd.DataFrame,
    k: int = STABILITY_K,
) -> float:
    if not document_ids or k <= 0:
        return 0.0
    total = sum(
        cross_check_book(
            b,
            ward_dist=ward_dist,
            svd_euclidean_dist=svd_euclidean_dist,
            svd_cosine_dist=svd_cosine_dist,
            k=k,
        )
        for b in document_ids
    )
    return float(total) / float(len(document_ids) * k)


def ward_artifact_document_ids(
    embedding: np.ndarray,
    Z: np.ndarray,
    document_ids: list[int],
    *,
    k: int = STABILITY_K,
    threshold: float = 0.2,
) -> set[int]:
    """Books whose Ward neighbors disagree with both SVD distance views.

    This ports the original morphological notebook's leaf-label annotation:
    score = |top-k Ward ∩ Euclidean ∩ cosine| / k; score < 0.2 is flagged.
    """
    if len(document_ids) < 2 or k <= 0:
        return set()
    effective_k = min(int(k), len(document_ids) - 1)
    ward_dist = ward_merge_height(Z, document_ids)
    euclidean_dist = euclidean_distance_frame(embedding, document_ids)
    cosine_dist = cosine_distance_embedding(embedding, document_ids)
    return {
        int(book)
        for book in document_ids
        if (
            cross_check_book(
                book,
                ward_dist=ward_dist,
                svd_euclidean_dist=euclidean_dist,
                svd_cosine_dist=cosine_dist,
                k=effective_k,
            )
            / effective_k
        )
        < float(threshold)
    }


def resolve_group(
    scope: str,
    scope_value: str,
    *,
    selected_document_ids: list[int],
    document_corpus: dict[int, str],
    cluster_of: dict[int, int],
) -> list[int]:
    """Resolve table scope → list of document ids."""
    selected = list(selected_document_ids)
    if scope == SCOPE_CORPUS:
        corpus = scope_value.strip().lower()
        if not corpus:
            return selected
        return [d for d in selected if document_corpus.get(d, "") == corpus]
    if scope == SCOPE_CLUSTER:
        try:
            cid = int(scope_value)
        except (TypeError, ValueError):
            return []
        return [d for d in selected if cluster_of.get(d) == cid]
    if scope == SCOPE_BOOK:
        try:
            doc_id = int(scope_value)
        except (TypeError, ValueError):
            return []
        return [doc_id] if doc_id in selected else []
    return selected


def resolve_side(
    kind: str,
    value: str,
    *,
    selected_document_ids: list[int],
    document_corpus: dict[int, str],
    cluster_of: dict[int, int],
    manual_groups: dict[str, Iterable[int]] | None = None,
) -> list[int]:
    """Resolve one side of an X-vs-Y comparison to a list of document ids.

    ``kind`` is one of the ``SCOPE_*`` constants. A corpus side may use
    :data:`CORPUS_ALL` to mean the whole selection.
    """
    selected = list(selected_document_ids)
    if kind == SCOPE_MANUAL:
        members = (manual_groups or {}).get(str(value), [])
        allowed = set(selected)
        return [int(i) for i in members if int(i) in allowed]
    if kind == SCOPE_CORPUS and str(value) == CORPUS_ALL:
        return selected
    return resolve_group(
        kind,
        str(value),
        selected_document_ids=selected,
        document_corpus=document_corpus,
        cluster_of=cluster_of,
    )


def resolve_comparison(
    scope_type: str,
    scope_value: str,
    picked: Iterable[int],
    *,
    selected_document_ids: list[int],
    document_corpus: dict[int, str],
    cluster_of: dict[int, int],
) -> list[int]:
    """Resolve manual-cluster comparison group (exclude picked members)."""
    picked_set = set(picked)
    selected = list(selected_document_ids)
    if scope_type == COMPARE_CORPUS:
        corpus = scope_value.strip().lower()
        return [
            d
            for d in selected
            if d not in picked_set and document_corpus.get(d, "") == corpus
        ]
    if scope_type == COMPARE_ALL_OTHER:
        return [d for d in selected if d not in picked_set]
    if scope_type == COMPARE_EXISTING_CLUSTER:
        try:
            cid = int(scope_value)
        except (TypeError, ValueError):
            return []
        return [
            d
            for d in selected
            if d not in picked_set and cluster_of.get(d) == cid
        ]
    return [d for d in selected if d not in picked_set]
