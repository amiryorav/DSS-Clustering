"""Manual cluster selection by clicking 3D / dendrogram leaves (spec §8.9)."""

from __future__ import annotations

import reflex as rx

from dss_clustering.pipeline.metrics import (
    COMPARE_ALL_OTHER,
    COMPARE_CORPUS,
    COMPARE_EXISTING_CLUSTER,
    TOP_N,
    active_frame,
    build_phase_rows,
    cosine_distance_embedding,
    cosine_distance_frame,
    diff_features,
    nn_consistency_for_group,
    resolve_comparison,
    shared_features,
    ward_merge_height,
)
from dss_clustering.pipeline.runtime import get_bundle, get_dendrogram, get_embedding
from dss_clustering.repository import delete_manual_cluster, list_manual_clusters, save_manual_cluster
from dss_clustering.states.data_state import (
    CORPUS_LABELS,
    CORPUS_ORDER,
    DataState,
)
from dss_clustering.states.dendrogram_state import DendrogramState
from dss_clustering.states.feature_state import FeatureState
from dss_clustering.states.rescale_state import RescaleState


class ManualClusterState(rx.State):
    """Click-to-select books and compare against a chosen reference group."""

    picking: bool = False
    picked_document_ids: list[int] = []
    comparison_scope_type: str = COMPARE_CORPUS
    comparison_scope_value: str = "mikra"
    saved_name: str = ""
    # Saved groups for the current user, loaded from `manual_clusters`.
    saved_groups: list[dict] = []
    # Guest groups: kept in this browser session only, never written to the DB.
    session_groups: list[dict] = []
    session_seq: int = 0
    comparison_options_rows: list[dict] = [
        {"value": corpus, "label": CORPUS_LABELS.get(corpus, corpus)}
        for corpus in CORPUS_ORDER
    ]
    comparison_member_rows: list[dict] = []

    has_results: bool = False
    consistency: str = ""
    top_rows: list[dict] = []
    distinctive_rows: list[dict] = []
    gap_rows: list[dict] = []
    status_message: str = (
        "Start selecting, then click books on the 3D plot or dendrogram."
    )

    def _token(self) -> str:
        return self.router.session.client_token

    @rx.var(cache=True)
    def n_picked(self) -> int:
        return len(self.picked_document_ids)

    @rx.var(cache=True)
    def group_rows(self) -> list[dict]:
        """Session groups first, then anything stored on the account."""
        return [*self.session_groups, *self.saved_groups]

    def all_groups(self) -> list[dict]:
        """Both kinds of group, for whoever needs to resolve ids to books."""
        return [*self.session_groups, *self.saved_groups]

    @rx.var(cache=True)
    async def picked_chip_rows(self) -> list[dict]:
        """Chips show the book name, falling back to the id if it is unknown."""
        data = await self.get_state(DataState)
        rows = []
        for document_id in self.picked_document_ids:
            key = str(document_id)
            rows.append(
                {
                    "id": document_id,
                    "label": data.document_books.get(key)
                    or data.document_labels.get(key, key),
                }
            )
        return rows

    @rx.event
    def start_picking(self):
        self.picking = True
        self.picked_document_ids = []
        self.has_results = False
        self.consistency = ""
        self.top_rows = []
        self.distinctive_rows = []
        self.gap_rows = []
        self.comparison_member_rows = []
        self.status_message = "Picking — click books on the 3D plot or dendrogram."

    @rx.event
    def clear_picked(self):
        self.picked_document_ids = []
        self.has_results = False
        self.consistency = ""
        self.top_rows = []
        self.distinctive_rows = []
        self.gap_rows = []
        self.comparison_member_rows = []
        self.status_message = "Selection cleared."

    @rx.event
    async def set_comparison_scope_type(self, value: str | list[str]):
        v = value[0] if isinstance(value, list) else value
        if v in (COMPARE_CORPUS, COMPARE_ALL_OTHER, COMPARE_EXISTING_CLUSTER):
            self.comparison_scope_type = v
            await self._refresh_comparison_options()

    @rx.event
    def set_comparison_scope_value(self, value: str | list[str]):
        v = value[0] if isinstance(value, list) else value
        self.comparison_scope_value = str(v)

    @rx.event
    async def refresh_comparison_options(self):
        await self._refresh_comparison_options()

    async def _refresh_comparison_options(self):
        if self.comparison_scope_type == COMPARE_ALL_OTHER:
            self.comparison_options_rows = []
            self.comparison_scope_value = ""
            return
        data = await self.get_state(DataState)
        if self.comparison_scope_type == COMPARE_CORPUS:
            present = {
                data.document_corpus.get(str(document_id), "")
                for document_id in data.selected_document_ids
            }
            options = [
                {"value": corpus, "label": CORPUS_LABELS.get(corpus, corpus)}
                for corpus in CORPUS_ORDER
                if corpus in present
            ]
        else:
            dendro = await self.get_state(DendrogramState)
            cluster_ids = sorted({int(value) for value in dendro.cluster_of.values()})
            options = [
                {"value": str(cluster_id), "label": f"Cluster {cluster_id}"}
                for cluster_id in cluster_ids
            ]
        self.comparison_options_rows = options
        valid = {option["value"] for option in options}
        if self.comparison_scope_value not in valid:
            self.comparison_scope_value = options[0]["value"] if options else ""

    @rx.event
    def set_saved_name(self, value: str):
        self.saved_name = value

    @rx.event
    def toggle_document(self, document_id: int):
        """Add/remove a book while picking (called from plot/dendrogram clicks)."""
        if not self.picking:
            # Direct plot selection starts a fresh group on the first click.
            self.picking = True
            self.picked_document_ids = []
            self.has_results = False
            self.consistency = ""
            self.top_rows = []
            self.distinctive_rows = []
            self.gap_rows = []
            self.comparison_member_rows = []
        if document_id in self.picked_document_ids:
            self.picked_document_ids = [
                i for i in self.picked_document_ids if i != document_id
            ]
        else:
            self.picked_document_ids = [*self.picked_document_ids, document_id]
        self.status_message = (
            f"Picked {len(self.picked_document_ids)} book(s)."
            if self.picked_document_ids
            else "Picking — click books on the 3D plot or dendrogram."
        )

    @rx.var(cache=True)
    async def pickable_books(self) -> list[dict]:
        """Books in the current analysis selection, for list-based picking."""
        data = await self.get_state(DataState)
        rows = []
        picked = set(self.picked_document_ids)
        for i in data.selected_document_ids:
            key = str(i)
            rows.append(
                {
                    "id": i,
                    "label": data.document_books.get(key)
                    or data.document_labels.get(key, key),
                    "picked": i in picked,
                }
            )
        return rows

    @rx.event
    async def done_picking(self):
        self.picking = False
        if len(self.picked_document_ids) < 1:
            self.has_results = False
            self.status_message = "No books picked."
            return

        data = await self.get_state(DataState)
        rescale = await self.get_state(RescaleState)
        dendro = await self.get_state(DendrogramState)
        token = self._token()

        bundle = get_bundle(token)
        emb = get_embedding(token)
        dendro_bundle = get_dendrogram(token)
        if bundle is None or not rescale.applied:
            self.has_results = False
            self.comparison_member_rows = []
            self.status_message = "Need an active (rescaled) matrix first."
            return

        document_corpus = {
            int(k): v for k, v in data.document_corpus.items()
        }
        cluster_of = {int(k): int(v) for k, v in dendro.cluster_of.items()}
        comparison = resolve_comparison(
            self.comparison_scope_type,
            self.comparison_scope_value,
            self.picked_document_ids,
            selected_document_ids=list(data.selected_document_ids),
            document_corpus=document_corpus,
            cluster_of=cluster_of,
        )
        if not comparison:
            self.has_results = False
            self.comparison_member_rows = []
            self.status_message = "Comparison group is empty — adjust the scope."
            return
        self.comparison_member_rows = [
            {
                "id": document_id,
                "label": data.document_books.get(str(document_id))
                or data.document_labels.get(str(document_id), str(document_id)),
            }
            for document_id in comparison
        ]

        try:
            frame = active_frame(bundle, rescale.mode)
            top = shared_features(frame, self.picked_document_ids, n=TOP_N)
            distinctive, gap = diff_features(
                frame, self.picked_document_ids, comparison, n=TOP_N
            )
            rows = build_phase_rows(top, distinctive, gap)

            consistency = "—"
            if emb is not None and dendro_bundle is not None:
                active_dist = cosine_distance_frame(frame)
                svd_cos = cosine_distance_embedding(
                    emb.embedding, list(emb.document_ids)
                )
                ward_dist = ward_merge_height(
                    dendro_bundle.Z, list(dendro_bundle.document_ids)
                )
                consistency = nn_consistency_for_group(
                    self.picked_document_ids,
                    active_dist=active_dist,
                    svd_cosine_dist=svd_cos,
                    ward_dist=ward_dist,
                )

            self.top_rows = rows["top"]
            self.distinctive_rows = rows["distinctive"]
            self.gap_rows = rows["gap"]
            self.consistency = consistency
            self.has_results = True
            self.status_message = (
                f"Compared {len(self.picked_document_ids)} books vs "
                f"{len(comparison)} reference books — consistency {consistency}."
            )
        except Exception as exc:  # noqa: BLE001
            self.has_results = False
            self.status_message = f"Manual compare failed: {exc}"

    def _save_session_group(self, name: str, feature_mode: str) -> None:
        """Keep a guest's group in state, replacing any earlier one by name."""
        self.session_seq += 1
        ids = [int(i) for i in self.picked_document_ids]
        group = {
            # Negative ids keep session groups distinguishable from DB rows.
            "id": -self.session_seq,
            "name": name,
            "document_ids": ids,
            "n_books": len(ids),
            "feature_mode": feature_mode,
            "comparison_scope_type": self.comparison_scope_type,
            "comparison_scope_value": self.comparison_scope_value,
            "created_at": "this session",
            "scope": "session",
        }
        self.session_groups = [
            *[g for g in self.session_groups if g["name"] != name],
            group,
        ]
        self.status_message = (
            f"Saved '{name}' ({len(ids)} books) for this visit. "
            "Sign in if you want it kept for next time."
        )

    async def _owner_user_id(self) -> int:
        """Saved groups belong to the signed-in account only."""
        from dss_clustering.states.auth_state import AuthState

        auth = await self.get_state(AuthState)
        return int(auth.current_user_id) if auth.current_user_id else 0

    async def reload_saved_groups(self) -> None:
        """Refresh the saved-cluster list for the signed-in / local user."""
        user_id = await self._owner_user_id()
        if not user_id:
            self.saved_groups = []
            return
        try:
            self.saved_groups = self._tag_account(list_manual_clusters(user_id))
        except Exception as exc:  # noqa: BLE001
            self.saved_groups = []
            self.status_message = f"Could not load saved clusters: {exc}"

    @staticmethod
    def _tag_account(rows: list[dict]) -> list[dict]:
        return [{**row, "scope": "account"} for row in rows]

    @rx.event(background=True)
    async def load_saved_groups(self):
        """Background so page mount does not block Start analysis."""
        async with self:
            await self.reload_saved_groups()

    @rx.event
    async def save_group(self):
        name = self.saved_name.strip()
        if not name:
            self.status_message = "Enter a name before saving."
            return
        if not self.picked_document_ids:
            self.status_message = "Nothing to save — pick books first."
            return

        feature = await self.get_state(FeatureState)

        user_id = await self._owner_user_id()
        if not user_id:
            self._save_session_group(name, feature.mode)
            return

        try:
            save_manual_cluster(
                user_id,
                name=name,
                document_ids=list(self.picked_document_ids),
                feature_mode=feature.mode,
                comparison_scope_type=self.comparison_scope_type,
                comparison_scope_value=self.comparison_scope_value,
            )
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Save failed: {exc}"
            return

        self.saved_groups = self._tag_account(list_manual_clusters(user_id))
        self.status_message = (
            f"Saved '{name}' ({len(self.picked_document_ids)} books) to your account."
        )

    @rx.event
    async def delete_group(self, group_id: int):
        gid = int(group_id)
        if gid < 0:
            self.session_groups = [
                g for g in self.session_groups if g["id"] != gid
            ]
            self.status_message = "Removed this visit's group."
            return
        user_id = await self._owner_user_id()
        if not user_id:
            return
        try:
            delete_manual_cluster(user_id, gid)
            self.saved_groups = self._tag_account(list_manual_clusters(user_id))
            self.status_message = "Deleted saved cluster."
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Delete failed: {exc}"

    @rx.event
    def load_group(self, group_id: int):
        match = next(
            (g for g in self.all_groups() if g["id"] == group_id), None
        )
        if match is None:
            return
        self.picked_document_ids = list(match["document_ids"])
        self.comparison_scope_type = match.get(
            "comparison_scope_type", COMPARE_CORPUS
        )
        self.comparison_scope_value = match.get("comparison_scope_value", "mikra")
        self.saved_name = match["name"]
        self.picking = False
        self.has_results = False
        self.status_message = (
            f"Loaded '{match['name']}' ({len(self.picked_document_ids)} books). "
            "Click Done to recompute."
        )
