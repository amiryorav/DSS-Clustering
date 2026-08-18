"""Database access for users and their saved manual clusters."""

from __future__ import annotations

from datetime import datetime, timezone

import reflex as rx
from sqlmodel import select

from dss_clustering.models import AnalysisPreset, ManualCluster, User


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


def claim_or_create_google_user(
    *,
    google_sub: str,
    email: str | None = None,
    display_name: str | None = None,
    local_key: str | None = None,
) -> int:
    """Upsert a Google identity, preferring to claim the current local user row.

    If ``google_sub`` already exists, that row wins. Otherwise, if ``local_key``
    points at a user without a Google subject, that row is claimed so saved
    manual clusters stay attached. Otherwise a new user row is created.
    """
    sub = google_sub.strip()
    if not sub:
        raise ValueError("google_sub is required.")
    key = (local_key or "").strip() or None
    now = _utcnow()
    with rx.session() as session:
        by_sub = session.exec(select(User).where(User.google_sub == sub)).first()
        if by_sub is not None:
            by_sub.email = email or by_sub.email
            by_sub.display_name = display_name or by_sub.display_name
            by_sub.last_seen_at = now
            session.add(by_sub)
            session.commit()
            session.refresh(by_sub)
            return int(by_sub.id or 0)

        local = None
        if key:
            local = session.exec(select(User).where(User.local_key == key)).first()
        if local is not None and not local.google_sub:
            local.google_sub = sub
            local.email = email or local.email
            local.display_name = display_name or local.display_name
            local.last_seen_at = now
            session.add(local)
            session.commit()
            session.refresh(local)
            return int(local.id or 0)

        user = User(
            google_sub=sub,
            local_key=key if local is None else None,
            email=email,
            display_name=display_name,
            created_at=now,
            last_seen_at=now,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return int(user.id or 0)


def get_user_profile(user_id: int) -> dict | None:
    """Email / name for a user id, used when restoring a session cookie."""
    if not user_id:
        return None
    with rx.session() as session:
        user = session.get(User, int(user_id))
        if user is None:
            return None
        return {
            "id": int(user.id or 0),
            "email": user.email or "",
            "display_name": user.display_name or "",
            "google_sub": user.google_sub or "",
        }


def preset_to_dict(preset: AnalysisPreset) -> dict:
    return {
        "id": int(preset.id or 0),
        "name": preset.name,
        "config": dict(preset.config or {}),
        "created_at": _fmt(preset.created_at),
    }


def list_analysis_presets(user_id: int) -> list[dict]:
    if not user_id:
        return []
    with rx.session() as session:
        rows = session.exec(
            select(AnalysisPreset)
            .where(AnalysisPreset.user_id == user_id)
            .order_by(AnalysisPreset.name)
        ).all()
        return [preset_to_dict(row) for row in rows]


def save_analysis_preset(user_id: int, *, name: str, config: dict) -> dict:
    """Insert or overwrite the user's preset with this name."""
    if not user_id:
        raise ValueError("No user id available for saving.")
    with rx.session() as session:
        preset = session.exec(
            select(AnalysisPreset)
            .where(AnalysisPreset.user_id == user_id)
            .where(AnalysisPreset.name == name)
        ).first()
        if preset is None:
            preset = AnalysisPreset(user_id=user_id, name=name)
        preset.config = dict(config)
        preset.updated_at = _utcnow()
        session.add(preset)
        session.commit()
        session.refresh(preset)
        return preset_to_dict(preset)


def delete_analysis_preset(user_id: int, preset_id: int) -> bool:
    if not user_id:
        return False
    with rx.session() as session:
        preset = session.exec(
            select(AnalysisPreset)
            .where(AnalysisPreset.user_id == user_id)
            .where(AnalysisPreset.id == preset_id)
        ).first()
        if preset is None:
            return False
        session.delete(preset)
        session.commit()
        return True


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
