"""Data tables: top / distinctive / gap + purity metrics (spec §8.8)."""

from __future__ import annotations

import reflex as rx
import pandas as pd

from dss_clustering.pipeline.metrics import (
    PURITY_K,
    SCOPE_BOOK,
    SCOPE_CLUSTER,
    SCOPE_CORPUS,
    SCOPE_MANUAL,
    STABILITY_K,
    TOP_N,
    active_frame,
    build_phase_rows,
    corpus_purity,
    corpus_wide_stability,
    cosine_distance_embedding,
    cosine_distance_frame,
    diff_features,
    euclidean_distance_frame,
    get_top_neighbors,
    nearest_group_by_centroid,
    nn_consistency_for_cluster,
    nn_consistency_for_group,
    resolve_group,
    shared_features,
    ward_merge_height,
)
from dss_clustering.pipeline.runtime import get_bundle, get_dendrogram, get_embedding
from dss_clustering.states.data_state import CORPUS_LABELS, CORPUS_ORDER, DataState
from dss_clustering.states.dendrogram_state import DendrogramState
from dss_clustering.states.rescale_state import RescaleState


class TableState(rx.State):
    """Interactive top / distinctive / gap tables with purity metrics."""

    scope: str = SCOPE_CORPUS
    scope_value: str = "mikra"
    filter_text: str = ""

    top_rows: list[dict] = []
    distinctive_rows: list[dict] = []
    gap_rows: list[dict] = []
    scope_options_rows: list[dict] = []
    group_member_rows: list[dict] = []

    corpus_wide_stability: float = 0.0
    purity_verdict: str = ""
    purity_score: float = 0.0
    consistency_label: str = ""
    has_tables: bool = False
    status_message: str = "Run SVD / dendrogram to populate tables."

    def _token(self) -> str:
        return self.router.session.client_token

    @rx.event
    def set_scope(self, value: str | list[str]):
        v = value[0] if isinstance(value, list) else value
        if v not in (SCOPE_CORPUS, SCOPE_CLUSTER, SCOPE_BOOK, SCOPE_MANUAL):
            return
        self.scope = v
        return TableState.recompute

    @rx.event
    def set_scope_value(self, value: str | list[str]):
        v = value[0] if isinstance(value, list) else value
        self.scope_value = str(v)
        return TableState.recompute

    @rx.event
    def set_filter_text(self, value: str):
        self.filter_text = value

    @rx.var(cache=True)
    def filtered_top_rows(self) -> list[dict]:
        return self._filter_rows(self.top_rows)

    @rx.var(cache=True)
    def filtered_distinctive_rows(self) -> list[dict]:
        return self._filter_rows(self.distinctive_rows)

    @rx.var(cache=True)
    def filtered_gap_rows(self) -> list[dict]:
        return self._filter_rows(self.gap_rows)

    def _filter_rows(self, rows: list[dict]) -> list[dict]:
        q = self.filter_text.strip().lower()
        if not q:
            return rows
        return [r for r in rows if q in str(r.get("signature", "")).lower()]

    @rx.var(cache=True)
    def stability_pct_label(self) -> str:
        return f"{100.0 * self.corpus_wide_stability:.1f}%"

    async def _build_scope_options(self) -> list[dict]:
        data = await self.get_state(DataState)
        dendro = await self.get_state(DendrogramState)
        if self.scope == SCOPE_CORPUS:
            present = {
                data.document_corpus.get(str(i), "")
                for i in data.selected_document_ids
            }
            return [
                {"value": c, "label": CORPUS_LABELS.get(c, c)}
                for c in CORPUS_ORDER
                if c in present
            ]
        if self.scope == SCOPE_CLUSTER:
            cids = sorted({int(v) for v in dendro.cluster_of.values()})
            return [{"value": str(c), "label": f"Cluster {c}"} for c in cids]
        if self.scope == SCOPE_MANUAL:
            from dss_clustering.states.manual_cluster_state import ManualClusterState

            manual = await self.get_state(ManualClusterState)
            return [
                {
                    "value": str(group["id"]),
                    "label": f"{group['name']} ({group['n_books']} books)",
                }
                for group in manual.saved_groups
            ]
        rows = []
        for i in data.selected_document_ids:
            key = str(i)
            label = data.document_books.get(key) or data.document_labels.get(
                key, key
            )
            rows.append({"value": key, "label": label})
        return sorted(rows, key=lambda r: r["label"].lower())

    @rx.event
    async def recompute(self):
        data = await self.get_state(DataState)
        rescale = await self.get_state(RescaleState)
        dendro = await self.get_state(DendrogramState)
        token = self._token()

        bundle = get_bundle(token)
        emb = get_embedding(token)
        dendro_bundle = get_dendrogram(token)

        if bundle is None or not rescale.applied or emb is None:
            self.has_tables = False
            self.top_rows = []
            self.distinctive_rows = []
            self.gap_rows = []
            self.scope_options_rows = []
            self.group_member_rows = []
            self.corpus_wide_stability = 0.0
            self.purity_verdict = ""
            self.purity_score = 0.0
            self.consistency_label = ""
            self.status_message = "Need rescaled matrix + SVD embedding."
            return

        document_corpus = {int(k): v for k, v in data.document_corpus.items()}
        cluster_of = {int(k): int(v) for k, v in dendro.cluster_of.items()}
        selected = list(data.selected_document_ids)

        options = await self._build_scope_options()
        self.scope_options_rows = options
        values = {o["value"] for o in options}
        if self.scope_value not in values and options:
            self.scope_value = options[0]["value"]

        manual_groups: list[dict] = []
        if self.scope == SCOPE_MANUAL:
            from dss_clustering.states.manual_cluster_state import ManualClusterState

            manual = await self.get_state(ManualClusterState)
            manual_groups = list(manual.saved_groups)
            chosen = next(
                (
                    saved
                    for saved in manual_groups
                    if str(saved["id"]) == self.scope_value
                ),
                None,
            )
            selected_set = set(selected)
            group = (
                [
                    int(document_id)
                    for document_id in chosen["document_ids"]
                    if int(document_id) in selected_set
                ]
                if chosen
                else []
            )
        else:
            group = resolve_group(
                self.scope,
                self.scope_value,
                selected_document_ids=selected,
                document_corpus=document_corpus,
                cluster_of=cluster_of,
            )
        rest = [d for d in selected if d not in set(group)]
        if not group:
            self.has_tables = False
            self.group_member_rows = []
            self.status_message = "Scope group is empty."
            return
        self.group_member_rows = [
            {
                "id": document_id,
                "label": data.document_books.get(str(document_id))
                or data.document_labels.get(str(document_id), str(document_id)),
                "corpus": document_corpus.get(document_id, ""),
            }
            for document_id in group
        ]

        try:
            frame = active_frame(bundle, rescale.mode)
            embedding_frame = pd.DataFrame(
                emb.embedding,
                index=list(emb.document_ids),
            )
            svd_cos = cosine_distance_embedding(
                emb.embedding, list(emb.document_ids)
            )
            top = shared_features(frame, group, n=TOP_N)
            if rest:
                distinctive, _ = diff_features(frame, group, rest, n=TOP_N)
            else:
                distinctive = top.iloc[0:0]

            # Original scripts define "gap" against the nearest comparable
            # group (or a book's top-10 SVD neighbors), not against all rest.
            if self.scope == SCOPE_BOOK:
                gap_reference = get_top_neighbors(
                    group[0], svd_cos, PURITY_K
                )
            elif self.scope == SCOPE_CORPUS:
                corpora = sorted(
                    {document_corpus.get(d, "") for d in selected}
                    - {self.scope_value}
                    - {""}
                )
                gap_reference = nearest_group_by_centroid(
                    embedding_frame,
                    group,
                    [
                        [d for d in selected if document_corpus.get(d) == corpus]
                        for corpus in corpora
                    ],
                )
            elif self.scope == SCOPE_CLUSTER:
                try:
                    current_cluster = int(self.scope_value)
                except (TypeError, ValueError):
                    current_cluster = cluster_of.get(group[0], 0)
                cluster_ids = sorted(set(cluster_of.values()) - {current_cluster})
                gap_reference = nearest_group_by_centroid(
                    embedding_frame,
                    group,
                    [
                        [d for d in selected if cluster_of.get(d) == cluster_id]
                        for cluster_id in cluster_ids
                    ],
                )
            else:
                # A saved manual group is compared with the nearest other
                # saved group. If none exists, use the nearest dendrogram
                # cluster that is not wholly contained in the manual group.
                other_manual_groups = [
                    [
                        int(document_id)
                        for document_id in saved["document_ids"]
                        if int(document_id) in set(selected)
                        and int(document_id) not in set(group)
                    ]
                    for saved in manual_groups
                    if str(saved["id"]) != self.scope_value
                ]
                candidates = [candidate for candidate in other_manual_groups if candidate]
                if not candidates:
                    candidates = [
                        [
                            document_id
                            for document_id in selected
                            if cluster_of.get(document_id) == cluster_id
                            and document_id not in set(group)
                        ]
                        for cluster_id in sorted(set(cluster_of.values()))
                    ]
                gap_reference = nearest_group_by_centroid(
                    embedding_frame,
                    group,
                    [candidate for candidate in candidates if candidate],
                )

            if gap_reference:
                _, gap_delta = diff_features(
                    frame, group, gap_reference, n=TOP_N
                )
                gap = gap_delta.abs()
            else:
                gap = top.iloc[0:0]
            rows = build_phase_rows(top, distinctive, gap)
            self.top_rows = rows["top"]
            self.distinctive_rows = rows["distinctive"]
            self.gap_rows = rows["gap"]

            active_dist = cosine_distance_frame(frame)
            svd_euc = euclidean_distance_frame(
                emb.embedding, list(emb.document_ids)
            )
            if dendro_bundle is not None:
                ward_dist = ward_merge_height(
                    dendro_bundle.Z, list(dendro_bundle.document_ids)
                )
                self.corpus_wide_stability = corpus_wide_stability(
                    list(emb.document_ids),
                    ward_dist=ward_dist,
                    svd_euclidean_dist=svd_euc,
                    svd_cosine_dist=svd_cos,
                    k=STABILITY_K,
                )
            else:
                ward_dist = None
                self.corpus_wide_stability = 0.0

            self.purity_verdict = ""
            self.purity_score = 0.0
            self.consistency_label = ""

            if self.scope == SCOPE_BOOK and group and ward_dist is not None:
                purity = corpus_purity(
                    group[0],
                    document_corpus=document_corpus,
                    active_dist=active_dist,
                    svd_cosine_dist=svd_cos,
                    ward_dist=ward_dist,
                )
                self.purity_verdict = purity["verdict"]
                self.purity_score = float(purity["purity_score"])
            elif self.scope == SCOPE_CLUSTER and group and ward_dist is not None:
                try:
                    cid = int(self.scope_value)
                except (TypeError, ValueError):
                    cid = cluster_of.get(group[0], 0)
                self.consistency_label = nn_consistency_for_cluster(
                    cid,
                    cluster_of,
                    active_dist=active_dist,
                    svd_cosine_dist=svd_cos,
                    ward_dist=ward_dist,
                )
            elif self.scope == SCOPE_MANUAL and group and ward_dist is not None:
                self.consistency_label = nn_consistency_for_group(
                    group,
                    active_dist=active_dist,
                    svd_cosine_dist=svd_cos,
                    ward_dist=ward_dist,
                )

            self.has_tables = True
            self.status_message = (
                f"{self.scope}={self.scope_value}: {len(group)} books, "
                f"top {len(self.top_rows)} features; "
                f"stability {100.0 * self.corpus_wide_stability:.1f}%."
            )
        except Exception as exc:  # noqa: BLE001
            self.has_tables = False
            self.status_message = f"Tables failed: {exc}"
