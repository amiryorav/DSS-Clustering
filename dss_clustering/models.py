"""Database models for the Hebrew stylometry corpus (ingest + later app phases)."""

from __future__ import annotations

from datetime import datetime, timezone

import reflex as rx
from sqlalchemy import JSON, Column, ForeignKey, Integer, UniqueConstraint
from sqlmodel import Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(rx.Model, table=True):
    """Stable identity for a book/scroll."""

    __tablename__ = "documents"

    book: str = Field(unique=True, index=True)
    corpus: str = Field(index=True)
    # Human-readable label shown in the UI; falls back to `book` when empty.
    display_name: str | None = Field(default=None)


class LemmaRow(rx.Model, table=True):
    """One word/morpheme occurrence from master_dataset.pkl."""

    __tablename__ = "lemma_rows"

    document_id: int = Field(foreign_key="documents.id", index=True)
    text_id: str | None = Field(default=None, index=True)
    verse_id: str | None = Field(default=None)
    form: str | None = Field(default=None)
    lemma: str | None = Field(default=None)
    clean_lemma: str = Field(default="")
    row_type: str = Field(default="", index=True)
    pos: str | None = Field(default=None)
    person: str | None = Field(default=None)
    gender: str | None = Field(default=None)
    number: str | None = Field(default=None)
    tense: str | None = Field(default=None)
    binyan: str | None = Field(default=None)
    state: str | None = Field(default=None)
    mood: str | None = Field(default=None)
    subtype: str | None = Field(default=None)


class User(rx.Model, table=True):
    """Owner of saved manual clusters.

    ``google_sub`` stays empty until Google sign-in is wired up; ``local_key``
    is a per-browser identifier so saved work survives restarts before then.
    """

    __tablename__ = "users"

    google_sub: str | None = Field(default=None, unique=True, index=True)
    local_key: str | None = Field(default=None, unique=True, index=True)
    email: str | None = Field(default=None)
    display_name: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime = Field(default_factory=_utcnow)


class AnalysisPreset(rx.Model, table=True):
    """A named ``AnalysisConfig`` snapshot, owned by a user.

    Presets used to live in server memory for the browser session only, so they
    disappeared on every redeploy and were never tied to the signed-in account.
    """

    __tablename__ = "analysis_presets"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_analysis_presets_user_name"),
    )

    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    name: str = Field(index=True)
    config: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ManualCluster(rx.Model, table=True):
    """A hand-picked group of books, owned by a user."""

    __tablename__ = "manual_clusters"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_manual_clusters_user_name"),
    )

    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    name: str = Field(index=True)
    document_ids: list[int] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    feature_mode: str = Field(default="")
    comparison_scope_type: str = Field(default="")
    comparison_scope_value: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
