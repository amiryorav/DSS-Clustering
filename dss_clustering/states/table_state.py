"""Data tables: compare one group of books (X) against another (Y) (spec §8.8)."""

from __future__ import annotations

from collections import Counter

import reflex as rx
import pandas as pd

from dss_clustering.pipeline.metrics import (
    CORPUS_ALL,
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
    nn_consistency_for_cluster,
    nn_consistency_for_group,
    resolve_side,
    shared_features,
    ward_merge_height,
)
from dss_clustering.pipeline.runtime import get_bundle, get_dendrogram, get_embedding
from dss_clustering.states.busy_state import BusyState
from dss_clustering.states.data_state import CORPUS_LABELS, CORPUS_ORDER, DataState
from dss_clustering.states.dendrogram_state import DendrogramState
from dss_clustering.states.rescale_state import RescaleState

SIDE_KINDS = (SCOPE_CORPUS, SCOPE_CLUSTER, SCOPE_MANUAL, SCOPE_BOOK)
CORPUS_ALL_LABEL = "Entire corpus (all selected books)"


class TableState(rx.State):
    """Top / distinctive / gap tables for an explicit X-versus-Y comparison."""

    x_kind: str = SCOPE_CORPUS
    x_value: str = "mikra"
    y_kind: str = SCOPE_CORPUS
    y_value: str = CORPUS_ALL
    filter_text: str = ""

    x_options: list[dict] = []
    y_options: list[dict] = []
    x_member_rows: list[dict] = []
    y_member_rows: list[dict] = []
    x_label: str = ""
    y_label: str = ""

    top_rows: list[dict] = []
    distinctive_rows: list[dict] = []
    gap_rows: list[dict] = []

    corpus_wide_stability: float = 0.0
    purity_verdict: str = ""
    purity_score: float = 0.0
    consistency_label: str = ""
    show_purity: bool = False
    show_consistency: bool = False
    has_tables: bool = False
    status_message: str = "Run SVD / dendrogram, then choose a subject and reference."

    def _token(self) -> str:
        return self.router.session.client_token

    @rx.event
    async def set_x_kind(self, value: str | list[str]):
        v = value[0] if isinstance(value, list) else value
        if v not in SIDE_KINDS:
            return
        self.x_kind = v
        self.x_value = ""
        return TableState.recompute

    @rx.event
    async def set_y_kind(self, value: str | list[str]):
        v = value[0] if isinstance(value, list) else value
        if v not in SIDE_KINDS:
            return
        self.y_kind = v
        self.y_value = ""
        return TableState.recompute

    @rx.event
    def set_x_value(self, value: str | list[str]):
        self.x_value = str(value[0] if isinstance(value, list) else value)
        return TableState.recompute

    @rx.event
    def set_y_value(self, value: str | list[str]):
        self.y_value = str(value[0] if isinstance(value, list) else value)
        return TableState.recompute

    @rx.event
    def swap_sides(self):
        self.x_kind, self.y_kind = self.y_kind, self.x_kind
        self.x_value, self.y_value = self.y_value, self.x_value
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

    @rx.var(cache=True)
    def distinctive_subtitle(self) -> str:
        return f"{self.x_display_label} > {self.y_display_label}"

    @rx.var(cache=True)
    def gap_subtitle(self) -> str:
        return f"{self.y_display_label} > {self.x_display_label}"

    @staticmethod
    def _display_side(kind: str, label: str) -> str:
        if kind == SCOPE_CORPUS:
            return (
                "Entire selected corpus"
                if label == CORPUS_ALL_LABEL
                else f"Corpus {label}"
            )
        if kind == SCOPE_CLUSTER:
            return label if label.startswith("Cluster ") else f"Cluster {label}"
        if kind == SCOPE_MANUAL:
            return f"Manual Group {label}"
        if kind == SCOPE_BOOK:
            return f"Book {label}"
        return label

    @rx.var(cache=True)
    def x_display_label(self) -> str:
        return self._display_side(self.x_kind, self.x_label)

    @rx.var(cache=True)
    def y_display_label(self) -> str:
        return self._display_side(self.y_kind, self.y_label)

    @rx.var(cache=True)
    def top_subtitle(self) -> str:
        return f"in {self.x_display_label}"

    @rx.var(cache=True)
    def export_slug(self) -> str:
        return (
            f"{self.x_kind}_{self.x_value}__vs__{self.y_kind}_{self.y_value}"
        )

    async def _manual_groups(self) -> list[dict]:
        from dss_clustering.states.manual_cluster_state import ManualClusterState

        manual = await self.get_state(ManualClusterState)
        await manual.reload_saved_groups()
        return list(manual.saved_groups)

    async def _options_for(self, kind: str, manual_groups: list[dict]) -> list[dict]:
        data = await self.get_state(DataState)
        if kind == SCOPE_CORPUS:
            present = {
                data.document_corpus.get(str(i), "")
                for i in data.selected_document_ids
            }
            rows = [{"value": CORPUS_ALL, "label": CORPUS_ALL_LABEL}]
            rows += [
                {"value": c, "label": CORPUS_LABELS.get(c, c)}
                for c in CORPUS_ORDER
                if c in present
            ]
            return rows
        if kind == SCOPE_CLUSTER:
            dendro = await self.get_state(DendrogramState)
            counts = Counter(int(v) for v in dendro.cluster_of.values())
            return [
                {
                    "value": str(cluster_id),
                    "label": f"Cluster {cluster_id} ({counts[cluster_id]} books)",
                }
                for cluster_id in sorted(counts)
            ]
        if kind == SCOPE_MANUAL:
            return [
                {
                    "value": str(group["id"]),
                    "label": f"{group['name']} ({group['n_books']} books)",
                }
                for group in manual_groups
            ]
        rows = [
            {
                "value": str(i),
                "label": data.document_books.get(str(i))
                or data.document_labels.get(str(i), str(i)),
            }
            for i in data.selected_document_ids
        ]
        return sorted(rows, key=lambda r: r["label"].lower())

    @staticmethod
    def _clamp(value: str, options: list[dict]) -> str:
        values = {o["value"] for o in options}
        if value in values:
            return value
        return options[0]["value"] if options else ""

    @staticmethod
    def _label_for(value: str, options: list[dict], fallback: str) -> str:
        for option in options:
            if option["value"] == value:
                return option["label"]
        return fallback

    @staticmethod
    def _no_options_message(kind: str, side: str) -> str:
        if kind == SCOPE_MANUAL:
            return (
                f"No saved manual groups to use as {side}. Pick books in the "
                "manual group step and save them first."
            )
        if kind == SCOPE_CLUSTER:
            return f"No dendrogram clusters available for {side}."
        return f"No {kind} options available for {side}."

    def _reset_tables(self, message: str):
        self.has_tables = False
        self.top_rows = []
        self.distinctive_rows = []
        self.gap_rows = []
        self.show_purity = False
        self.show_consistency = False
        self.purity_verdict = ""
        self.purity_score = 0.0
        self.consistency_label = ""
        self.status_message = message

    def _member_rows(
        self,
        document_ids: list[int],
        data: DataState,
        document_corpus: dict[int, str],
    ) -> list[dict]:
        return [
            {
                "id": document_id,
                "label": data.document_books.get(str(document_id))
                or data.document_labels.get(str(document_id), str(document_id)),
                "corpus": document_corpus.get(document_id, ""),
            }
            for document_id in document_ids
        ]

    @rx.event
    async def recompute(self):
        busy = await self.get_state(BusyState)
        busy.begin("Computing comparison tables…")
        yield
        try:
            await self._recompute()
        finally:
            busy.end()

    async def _recompute(self):
        data = await self.get_state(DataState)
        rescale = await self.get_state(RescaleState)
        dendro = await self.get_state(DendrogramState)
        token = self._token()

        bundle = get_bundle(token)
        emb = get_embedding(token)
        dendro_bundle = get_dendrogram(token)

        if bundle is None or not rescale.applied or emb is None:
            self.x_options = []
            self.y_options = []
            self.x_member_rows = []
            self.y_member_rows = []
            self.corpus_wide_stability = 0.0
            self._reset_tables("Need rescaled matrix + SVD embedding.")
            return

        manual_groups: list[dict] = []
        if SCOPE_MANUAL in (self.x_kind, self.y_kind):
            manual_groups = await self._manual_groups()

        self.x_options = await self._options_for(self.x_kind, manual_groups)
        self.y_options = await self._options_for(self.y_kind, manual_groups)
        self.x_value = self._clamp(self.x_value, self.x_options)
        self.y_value = self._clamp(self.y_value, self.y_options)
        self.x_label = self._label_for(self.x_value, self.x_options, self.x_kind)
        self.y_label = self._label_for(self.y_value, self.y_options, self.y_kind)

        if not self.x_options:
            self.x_member_rows = []
            self.y_member_rows = []
            self._reset_tables(self._no_options_message(self.x_kind, "the subject"))
            return

        document_corpus = {int(k): v for k, v in data.document_corpus.items()}
        cluster_of = {int(k): int(v) for k, v in dendro.cluster_of.items()}
        selected = list(data.selected_document_ids)
        manual_lookup = {
            str(group["id"]): group["document_ids"] for group in manual_groups
        }

        x_group = resolve_side(
            self.x_kind,
            self.x_value,
            selected_document_ids=selected,
            document_corpus=document_corpus,
            cluster_of=cluster_of,
            manual_groups=manual_lookup,
        )
        y_all = resolve_side(
            self.y_kind,
            self.y_value,
            selected_document_ids=selected,
            document_corpus=document_corpus,
            cluster_of=cluster_of,
            manual_groups=manual_lookup,
        )
        x_set = set(x_group)
        y_group = [d for d in y_all if d not in x_set]
        overlap = len(y_all) - len(y_group)

        self.x_member_rows = self._member_rows(x_group, data, document_corpus)
        self.y_member_rows = self._member_rows(y_group, data, document_corpus)

        if not x_group:
            self._reset_tables(
                f"{self.x_display_label} has no books in the selection."
            )
            return

        try:
            frame = active_frame(bundle, rescale.mode)
            top = shared_features(frame, x_group, n=TOP_N)
            if y_group:
                distinctive, gap_delta = diff_features(
                    frame, x_group, y_group, n=TOP_N
                )
                gap = gap_delta.abs()
            else:
                distinctive = top.iloc[0:0]
                gap = top.iloc[0:0]
            rows = build_phase_rows(top, distinctive, gap)
            self.top_rows = rows["top"]
            self.distinctive_rows = rows["distinctive"]
            self.gap_rows = rows["gap"]

            svd_cos = cosine_distance_embedding(emb.embedding, list(emb.document_ids))
            svd_euc = euclidean_distance_frame(emb.embedding, list(emb.document_ids))
            active_dist = cosine_distance_frame(frame)
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
            self.show_purity = False
            self.show_consistency = False

            if ward_dist is not None:
                if len(x_group) == 1:
                    purity = corpus_purity(
                        x_group[0],
                        document_corpus=document_corpus,
                        active_dist=active_dist,
                        svd_cosine_dist=svd_cos,
                        ward_dist=ward_dist,
                        k=PURITY_K,
                    )
                    self.purity_verdict = purity["verdict"]
                    self.purity_score = float(purity["purity_score"])
                    self.show_purity = True
                elif self.x_kind == SCOPE_CLUSTER:
                    try:
                        cid = int(self.x_value)
                    except (TypeError, ValueError):
                        cid = cluster_of.get(x_group[0], 0)
                    self.consistency_label = nn_consistency_for_cluster(
                        cid,
                        cluster_of,
                        active_dist=active_dist,
                        svd_cosine_dist=svd_cos,
                        ward_dist=ward_dist,
                    )
                    self.show_consistency = True
                else:
                    self.consistency_label = nn_consistency_for_group(
                        x_group,
                        active_dist=active_dist,
                        svd_cosine_dist=svd_cos,
                        ward_dist=ward_dist,
                    )
                    self.show_consistency = True

            self.has_tables = True
            if not y_group:
                reason = (
                    self._no_options_message(self.y_kind, "the reference")
                    if not self.y_options
                    else (
                        "The reference is empty once books shared with the subject "
                        "are removed."
                        if y_all
                        else "The reference has no books in the selection."
                    )
                )
                self.status_message = (
                    f"{self.x_display_label}: {len(x_group)} books. {reason} "
                    "Only the top-feature table is available."
                )
            else:
                overlap_note = (
                    f" ({overlap} shared book(s) excluded from the reference)"
                    if overlap
                    else ""
                )
                self.status_message = (
                    f"{self.x_display_label} ({len(x_group)} books) vs "
                    f"{self.y_display_label} "
                    f"({len(y_group)} books){overlap_note}; "
                    f"stability {100.0 * self.corpus_wide_stability:.1f}%."
                )
        except Exception as exc:  # noqa: BLE001
            self._reset_tables(f"Tables failed: {exc}")
