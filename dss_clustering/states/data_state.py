"""Data step: choose books/scrolls for analysis."""

from __future__ import annotations

import asyncio
from collections import defaultdict

import reflex as rx
from sqlmodel import select

from dss_clustering.models import Document
from dss_clustering.pipeline.fragments import (
    document_ids_with_fragments,
    list_fragments_for_document,
)

# Default identity colors used by the plot step (not edited in Data).
DEFAULT_CORPUS_COLORS = {
    "mikra": "#FFD700",
    "mishna": "#32CD32",
    "dss": "#4169E1",
}

CORPUS_ORDER = ("mikra", "mishna", "dss")
CORPUS_LABELS = {"mikra": "Mikra", "mishna": "Mishna", "dss": "DSS"}
FALLBACK_COLOR = "#888888"

# Only these lemma rows count as analysable occurrences.
VALID_ROW_TYPE = "NNN"


class DataState(rx.State):
    """Book selection (spec 8.1). Plot-area colors live here for redraw only."""

    corpora: list[str] = []
    # corpus -> [{id, book, label, n_entries, has_fragments}, ...]
    documents_by_corpus: dict[str, list[dict]] = {}
    # document_id (as str) -> display label
    document_labels: dict[str, str] = {}
    # document_id (as str) -> short book siglum (e.g. Dan, CD)
    document_books: dict[str, str] = {}
    # document_id (as str) -> corpus
    document_corpus: dict[str, str] = {}

    selected_document_ids: list[int] = []
    corpus_default_color: dict[str, str] = dict(DEFAULT_CORPUS_COLORS)
    # keyed by str(document_id); set from the plot step only
    document_color_override: dict[str, str] = {}
    # per-book overrides while coloring by dendrogram cluster
    document_cluster_color_override: dict[str, str] = {}

    # DSS fragment deselection: document_id str → excluded fragment keys (f13, …)
    excluded_fragments: dict[str, list[str]] = {}
    expanded_document_ids: list[int] = []
    # document_id str → [{key, label, n_entries}, ...] loaded on expand
    fragment_cache: dict[str, list[dict]] = {}

    min_entries_per_book: int = 100
    search_text: str = ""
    status_message: str = ""
    is_loading: bool = False

    # ---------- events ----------

    @staticmethod
    def _invalidate_matrix():
        from dss_clustering.states.vectorize_state import VectorizeState

        return VectorizeState.refresh_stale

    @rx.event
    def set_search_text(self, value: str):
        self.search_text = value

    @rx.event
    def set_min_entries(self, value: str):
        try:
            n = int(value)
        except (TypeError, ValueError):
            return
        self.min_entries_per_book = max(0, n)

    @rx.event
    def toggle_document(self, document_id: int):
        if document_id in self.selected_document_ids:
            self.selected_document_ids = [
                i for i in self.selected_document_ids if i != document_id
            ]
            # Deselecting the scroll clears its fragment exclusions.
            key = str(document_id)
            if key in self.excluded_fragments:
                self.excluded_fragments = {
                    k: v for k, v in self.excluded_fragments.items() if k != key
                }
        else:
            self.selected_document_ids = [*self.selected_document_ids, document_id]
            # Re-selecting a scroll includes all fragments again.
            key = str(document_id)
            if key in self.excluded_fragments:
                self.excluded_fragments = {
                    k: v for k, v in self.excluded_fragments.items() if k != key
                }
        return self._invalidate_matrix()

    @rx.event
    def toggle_corpus_visible(self, corpus: str):
        """Select or deselect all currently visible (search-filtered) books in a corpus."""
        docs = self._filtered_raw().get(corpus, [])
        ids = [doc["id"] for doc in docs]
        if not ids:
            return
        selected = set(self.selected_document_ids)
        if all(i in selected for i in ids):
            remove = set(ids)
            self.selected_document_ids = [
                i for i in self.selected_document_ids if i not in remove
            ]
            remove_keys = {str(i) for i in remove}
            self.excluded_fragments = {
                k: v
                for k, v in self.excluded_fragments.items()
                if k not in remove_keys
            }
        else:
            self.selected_document_ids = sorted(selected | set(ids))
            keep = dict(self.excluded_fragments)
            for i in ids:
                keep.pop(str(i), None)
            self.excluded_fragments = keep
        return self._invalidate_matrix()

    @rx.event
    def select_all_visible(self):
        ids = [
            doc["id"]
            for docs in self._filtered_raw().values()
            for doc in docs
        ]
        self.selected_document_ids = sorted(set(self.selected_document_ids) | set(ids))
        keep = dict(self.excluded_fragments)
        for i in ids:
            keep.pop(str(i), None)
        self.excluded_fragments = keep
        return self._invalidate_matrix()

    @rx.event
    def clear_selection(self):
        self.selected_document_ids = []
        self.excluded_fragments = {}
        return self._invalidate_matrix()

    @rx.event(background=True)
    async def expand_document(self, document_id: int):
        """Open the fragment tree; load children from the DB on first expand."""
        doc_id = int(document_id)
        key = str(doc_id)
        async with self:
            if doc_id not in self.expanded_document_ids:
                self.expanded_document_ids = [*self.expanded_document_ids, doc_id]
            if key in self.fragment_cache:
                return
            book = self.document_books.get(key, "")

        try:
            rows = await asyncio.to_thread(
                list_fragments_for_document,
                doc_id,
                row_type=VALID_ROW_TYPE,
                book=book,
            )
        except Exception as exc:  # noqa: BLE001
            async with self:
                self.status_message = f"Could not load fragments: {exc}"
            return

        async with self:
            self.fragment_cache = {**self.fragment_cache, key: rows}

    @rx.event
    def collapse_document(self, document_id: int):
        doc_id = int(document_id)
        self.expanded_document_ids = [
            i for i in self.expanded_document_ids if i != doc_id
        ]

    @rx.event
    def toggle_expand(self, document_id: int):
        doc_id = int(document_id)
        if doc_id in self.expanded_document_ids:
            return DataState.collapse_document(doc_id)
        return DataState.expand_document(doc_id)

    @rx.event
    def toggle_fragment(self, document_id: int, fragment_key: str):
        """Include/exclude one DSS fragment within a selected scroll."""
        doc_id = int(document_id)
        key = str(doc_id)
        frag = str(fragment_key).strip()
        if not frag:
            return

        excluded = list(self.excluded_fragments.get(key, []))
        cache = self.fragment_cache.get(key, [])
        all_keys = [row["key"] for row in cache]

        if frag in excluded:
            excluded = [f for f in excluded if f != frag]
        else:
            excluded = [*excluded, frag]

        # If every known fragment is excluded, deselect the parent scroll.
        if all_keys and set(all_keys).issubset(set(excluded)):
            self.selected_document_ids = [
                i for i in self.selected_document_ids if i != doc_id
            ]
            self.excluded_fragments = {
                k: v for k, v in self.excluded_fragments.items() if k != key
            }
            return self._invalidate_matrix()

        # Re-including any fragment while the scroll was off selects it again.
        if doc_id not in self.selected_document_ids:
            self.selected_document_ids = [*self.selected_document_ids, doc_id]

        if excluded:
            self.excluded_fragments = {**self.excluded_fragments, key: excluded}
        else:
            self.excluded_fragments = {
                k: v for k, v in self.excluded_fragments.items() if k != key
            }
        return self._invalidate_matrix()

    @staticmethod
    def _fetch_document_rows() -> list[tuple]:
        """Load the catalog from precomputed per-document NNN counts.

        ``n_nnn`` is maintained at ingest and by Alembic backfill so Home
        does not GROUP BY lemma_rows on every mount. Eligibility uses NNN
        rows only; lemma mode still drops blank clean_lemma when counting
        features downstream.
        """
        with rx.session() as session:
            statement = select(
                Document.id,
                Document.book,
                Document.corpus,
                Document.display_name,
                Document.n_nnn,
            ).order_by(Document.corpus, Document.book)
            return list(session.exec(statement).all())

    @rx.event(background=True)
    async def load_documents(self):
        """Load documents eligible under the current original-script rules.

        Runs in the background so Home → Start analysis is not queued behind
        catalog setup. Counts are precomputed on ``documents``.
        """
        async with self:
            min_entries = self.min_entries_per_book
            self.is_loading = True
            self.status_message = "Loading documents..."

        try:
            rows = await asyncio.to_thread(DataState._fetch_document_rows)

            by_corpus: dict[str, list[dict]] = defaultdict(list)
            labels: dict[str, str] = {}
            books: dict[str, str] = {}
            corpus_of: dict[str, str] = {}

            for doc_id, book, corpus, display_name, n in rows:
                if int(n or 0) < min_entries:
                    continue
                label = (display_name or "").strip() or book
                by_corpus[corpus].append(
                    {
                        "id": doc_id,
                        "book": book,
                        "label": label,
                        "n_entries": int(n),
                        "has_fragments": False,
                    }
                )
                labels[str(doc_id)] = label
                books[str(doc_id)] = book
                corpus_of[str(doc_id)] = corpus

            # One cheap probe for DSS scrolls that have fragment locators —
            # still no per-fragment lists until the user expands a row.
            dss_ids = [doc["id"] for doc in by_corpus.get("dss", [])]
            if dss_ids:
                frag_ids = await asyncio.to_thread(
                    document_ids_with_fragments,
                    dss_ids,
                    row_type=VALID_ROW_TYPE,
                )
                for doc in by_corpus.get("dss", []):
                    doc["has_fragments"] = doc["id"] in frag_ids

            for docs in by_corpus.values():
                docs.sort(key=lambda d: d["label"].lower())

            ordered = [c for c in CORPUS_ORDER if c in by_corpus]
            ordered += sorted(c for c in by_corpus if c not in CORPUS_ORDER)
            total = sum(len(v) for v in by_corpus.values())

            async with self:
                self.corpora = ordered
                self.documents_by_corpus = dict(by_corpus)
                self.document_labels = labels
                self.document_books = books
                self.document_corpus = corpus_of
                eligible_ids = [
                    doc["id"]
                    for docs in by_corpus.values()
                    for doc in docs
                ]
                eligible = set(eligible_ids)
                eligible_keys = {str(i) for i in eligible}
                self.fragment_cache = {
                    k: v
                    for k, v in self.fragment_cache.items()
                    if k in eligible_keys
                }
                self.expanded_document_ids = [
                    i for i in self.expanded_document_ids if i in eligible
                ]
                self.excluded_fragments = {
                    k: v
                    for k, v in self.excluded_fragments.items()
                    if k in eligible_keys
                }
                if not self.selected_document_ids:
                    self.selected_document_ids = sorted(eligible_ids)
                else:
                    self.selected_document_ids = [
                        i for i in self.selected_document_ids if i in eligible
                    ]
                self.status_message = (
                    f"Loaded {total} books/scrolls "
                    f"(min NNN rows >= {min_entries})."
                )
                self.is_loading = False
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            async with self:
                self.status_message = f"Failed to load documents: {exc}"
                self.is_loading = False

    # ---------- helpers ----------

    def _filtered_raw(self) -> dict[str, list[dict]]:
        q = self.search_text.strip().lower()
        if not q:
            return self.documents_by_corpus
        out: dict[str, list[dict]] = {}
        for corpus, docs in self.documents_by_corpus.items():
            matched = [
                d
                for d in docs
                if q in d["label"].lower() or q in d["book"].lower()
            ]
            if matched:
                out[corpus] = matched
        return out

    def _fragment_rows_for(self, document_id: int) -> list[dict]:
        key = str(document_id)
        excluded = set(self.excluded_fragments.get(key, []))
        return [
            {**row, "selected": row["key"] not in excluded}
            for row in self.fragment_cache.get(key, [])
        ]

    # ---------- computed vars ----------

    @rx.var(cache=True)
    def filtered_documents(self) -> dict[str, list[dict]]:
        """Search-filtered documents enriched with selection / expand state."""
        selected = set(self.selected_document_ids)
        expanded = set(self.expanded_document_ids)
        out: dict[str, list[dict]] = {}
        for corpus, docs in self._filtered_raw().items():
            enriched = []
            for doc in docs:
                doc_id = doc["id"]
                enriched.append(
                    {
                        **doc,
                        "selected": doc_id in selected,
                        "expanded": doc_id in expanded,
                        "fragments": self._fragment_rows_for(doc_id),
                        "fragments_loading": (
                            doc_id in expanded
                            and str(doc_id) not in self.fragment_cache
                        ),
                    }
                )
            out[corpus] = enriched
        return out

    @rx.var(cache=True)
    def corpus_all_selected(self) -> dict[str, bool]:
        """Whether every search-filtered book in each corpus is selected."""
        selected = set(self.selected_document_ids)
        out: dict[str, bool] = {}
        for corpus, docs in self._filtered_raw().items():
            ids = [doc["id"] for doc in docs]
            out[corpus] = bool(ids) and all(i in selected for i in ids)
        return out

    @rx.var(cache=True)
    def corpus_labels(self) -> dict[str, str]:
        return {c: CORPUS_LABELS.get(c, c.title()) for c in self.corpora}

    @rx.var(cache=True)
    def visible_corpora(self) -> list[str]:
        """Corpora that still have at least one document after filtering."""
        present = self.filtered_documents
        return [c for c in self.corpora if present.get(c)]

    @rx.var(cache=True)
    def selected_count(self) -> int:
        return len(self.selected_document_ids)
