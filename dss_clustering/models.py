"""Database models for the Hebrew stylometry corpus (ingest + later app phases)."""

from __future__ import annotations

import reflex as rx
from sqlmodel import Field


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
