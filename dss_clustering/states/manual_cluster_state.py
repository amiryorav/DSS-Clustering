"""Manual group selection by clicking 3D / dendrogram leaves.

This section only builds named book groups. Feature comparisons happen later
in the numbers section, where a group can be either side of an X/Y pair.
"""

from __future__ import annotations

import reflex as rx

from dss_clustering.repository import (
    delete_manual_cluster,
    list_manual_clusters,
    save_manual_cluster,
)
from dss_clustering.states.data_state import DataState
from dss_clustering.states.feature_state import FeatureState


class ManualClusterState(rx.State):
    """Click-to-select books and save them as a reusable group."""

    picking: bool = False
    picked_document_ids: list[int] = []
    saved_name: str = ""
    # Nested under The numbers; closed until the visitor asks for it.
    show_builder: bool = False
    # Saved groups for the current user, loaded from `manual_clusters`.
    saved_groups: list[dict] = []
    # Guest groups: kept in this browser session only, never written to the DB.
    session_groups: list[dict] = []
    session_seq: int = 0
    # Kept empty for older export paths that still look for table rows here.
    top_rows: list[dict] = []
    distinctive_rows: list[dict] = []
    gap_rows: list[dict] = []
    status_message: str = (
        "Start selecting, then click books on the 3D plot or dendrogram."
    )

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
    def open_builder(self):
        self.show_builder = True

    @rx.event
    def close_builder(self):
        self.show_builder = False
        self.picking = False

    @rx.event
    def start_picking(self):
        self.picking = True
        self.picked_document_ids = []
        self.status_message = "Picking — click books on the 3D plot or dendrogram."

    @rx.event
    def clear_picked(self):
        self.picked_document_ids = []
        self.status_message = "Selection cleared."

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
    def done_picking(self):
        """Finish picking — no comparison; save the group for the numbers step."""
        self.picking = False
        n = len(self.picked_document_ids)
        if n < 1:
            self.status_message = "No books picked."
            return
        self.status_message = (
            f"Group ready ({n} books). Name it and save, then use it in "
            "The numbers."
        )

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
            "comparison_scope_type": "",
            "comparison_scope_value": "",
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
                comparison_scope_type="",
                comparison_scope_value="",
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
        self.saved_name = match["name"]
        self.picking = False
        self.status_message = (
            f"Loaded '{match['name']}' ({len(self.picked_document_ids)} books)."
        )
