"""Parse DSS fragment locators from ``lemma_rows.verse_id``.

Examples::

    "6Q18 f13:2"     → fragment key "f13"
    "4Q394 f8iii:6"  → "f8iii"
    "CD 1:1"         → None (no fragment token)
    "Gen. 1:1"       → None
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Mapping, Sequence

import reflex as rx
from sqlalchemy import and_, not_, or_
from sqlmodel import func, select

from dss_clustering.models import LemmaRow

# ``{scroll} f{label}:{line}`` — label may include letters (e.g. f8iii).
FRAG_RE = re.compile(
    r"^(?P<scroll>\S+)\s+(?P<frag>f[^:\s]+):(?P<line>\S+)\s*$"
)

# Cheap SQL probe: DSS fragment locators contain " f" then a fragment token and ":".
FRAG_VERSE_LIKE = "% f%:%"


def fragment_key(verse_id: str | None) -> str | None:
    """Return the fragment token (e.g. ``f13``) or ``None`` if not a fragment locator."""
    if not verse_id:
        return None
    match = FRAG_RE.match(verse_id.strip())
    if not match:
        return None
    return match.group("frag")


def document_ids_with_fragments(
    document_ids: Sequence[int],
    *,
    row_type: str,
) -> set[int]:
    """Ids among ``document_ids`` that have at least one fragment-pattern verse."""
    if not document_ids:
        return set()
    with rx.session() as session:
        rows = session.exec(
            select(LemmaRow.document_id)
            .where(LemmaRow.document_id.in_(list(document_ids)))
            .where(LemmaRow.row_type == row_type)
            .where(LemmaRow.verse_id.is_not(None))
            .where(LemmaRow.verse_id.like(FRAG_VERSE_LIKE))
            .distinct()
        ).all()
    return {int(doc_id) for doc_id in rows}


def list_fragments_for_document(
    document_id: int,
    *,
    row_type: str,
    book: str = "",
) -> list[dict]:
    """Lazy-load fragment rows for one scroll: ``{key, label, n_entries}``."""
    with rx.session() as session:
        rows = session.exec(
            select(LemmaRow.verse_id, func.count(LemmaRow.id))
            .where(LemmaRow.document_id == int(document_id))
            .where(LemmaRow.row_type == row_type)
            .where(LemmaRow.verse_id.is_not(None))
            .group_by(LemmaRow.verse_id)
        ).all()

    counts: dict[str, int] = defaultdict(int)
    for verse_id, n in rows:
        key = fragment_key(verse_id)
        if key is None:
            continue
        counts[key] += int(n)

    prefix = f"{book} " if book else ""
    return [
        {
            "key": key,
            "label": f"{prefix}{key}".strip(),
            "n_entries": counts[key],
        }
        for key in sorted(counts, key=_fragment_sort_key)
    ]


def _fragment_sort_key(key: str) -> tuple:
    """Sort ``f13`` before ``f130``; fall back to string."""
    m = re.match(r"^f(\d+)(.*)$", key, re.IGNORECASE)
    if m:
        return (0, int(m.group(1)), m.group(2))
    return (1, 0, key)


def exclusion_sql_filter(
    excluded_fragments: Mapping[int, Sequence[str]] | Mapping[str, Sequence[str]],
    *,
    document_books: Mapping[str, str] | None = None,
):
    """SQLAlchemy clause that drops rows belonging to excluded fragments.

    ``verse_id`` looks like ``{book} {frag}:{line}``. We match
    ``LIKE '{book} {frag}:%'`` when the book siglum is known, else
    ``LIKE '% {frag}:%'`` scoped to that ``document_id``.
    """
    clauses = []
    for raw_doc_id, frags in excluded_fragments.items():
        doc_id = int(raw_doc_id)
        book = ""
        if document_books is not None:
            book = (document_books.get(str(doc_id)) or "").strip()
        for frag in frags:
            frag = str(frag).strip()
            if not frag:
                continue
            if book:
                pattern = f"{book} {frag}:%"
            else:
                pattern = f"% {frag}:%"
            clauses.append(
                and_(
                    LemmaRow.document_id == doc_id,
                    LemmaRow.verse_id.is_not(None),
                    LemmaRow.verse_id.like(pattern),
                )
            )
    if not clauses:
        return None
    return not_(or_(*clauses))
