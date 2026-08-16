"""Database access for users and their saved manual clusters."""

from __future__ import annotations

from datetime import datetime, timezone

import reflex as rx
from sqlmodel import select

from dss_clustering.models import ManualCluster, User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else ""


def cluster_to_dict(cluster: ManualCluster) -> dict:
    """Shape a row for the UI (also the session fallback shape)."""
    document_ids = [int(i) for i in (cluster.document_ids or [])]
    return {
        "id": int(cluster.id or 0),
        "name": cluster.name,
        "document_ids": document_ids,
        "n_books": len(document_ids),
        "feature_mode": cluster.feature_mode or "",
        "comparison_scope_type": cluster.comparison_scope_type or "",
        "comparison_scope_value": cluster.comparison_scope_value or "",
        "created_at": _fmt(cluster.created_at),
    }


def get_or_create_local_user(local_key: str) -> int:
    """Resolve the numeric user id for a browser-local identity."""
    key = local_key.strip()
    if not key:
        return 0
    with rx.session() as session:
        user = session.exec(select(User).where(User.local_key == key)).first()
        if user is None:
            user = User(local_key=key)
            session.add(user)
        else:
            user.last_seen_at = _utcnow()
            session.add(user)
        session.commit()
        session.refresh(user)
        return int(user.id or 0)


def list_manual_clusters(user_id: int) -> list[dict]:
    if not user_id:
        return []
    with rx.session() as session:
        rows = session.exec(
            select(ManualCluster)
            .where(ManualCluster.user_id == user_id)
            .order_by(ManualCluster.name)
        ).all()
        return [cluster_to_dict(row) for row in rows]


def save_manual_cluster(
    user_id: int,
    *,
    name: str,
    document_ids: list[int],
    feature_mode: str = "",
    comparison_scope_type: str = "",
    comparison_scope_value: str = "",
) -> dict:
    """Insert or overwrite the user's cluster with this name."""
    if not user_id:
        raise ValueError("No user id available for saving.")
    ids = [int(i) for i in document_ids]
    with rx.session() as session:
        cluster = session.exec(
            select(ManualCluster)
            .where(ManualCluster.user_id == user_id)
            .where(ManualCluster.name == name)
        ).first()
        if cluster is None:
            cluster = ManualCluster(user_id=user_id, name=name)
        cluster.document_ids = ids
        cluster.feature_mode = feature_mode
        cluster.comparison_scope_type = comparison_scope_type
        cluster.comparison_scope_value = comparison_scope_value
        cluster.updated_at = _utcnow()
        session.add(cluster)
        session.commit()
        session.refresh(cluster)
        return cluster_to_dict(cluster)


def delete_manual_cluster(user_id: int, cluster_id: int) -> bool:
    if not user_id:
        return False
    with rx.session() as session:
        cluster = session.exec(
            select(ManualCluster)
            .where(ManualCluster.user_id == user_id)
            .where(ManualCluster.id == cluster_id)
        ).first()
        if cluster is None:
            return False
        session.delete(cluster)
        session.commit()
        return True
