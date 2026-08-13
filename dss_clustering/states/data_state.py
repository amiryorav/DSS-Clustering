"""Data step: choose books/scrolls for analysis."""

from __future__ import annotations

from collections import defaultdict

import reflex as rx
from sqlmodel import func, select

from dss_clustering.models import Document, LemmaRow

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
    # corpus -> [{id, book, label, n_entries}, ...] straight from the DB
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

    min_entries_per_book: int = 100
    search_text: str = ""
    status_message: str = ""
    is_loading: bool = False

    # ---------- events ----------

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
        else:
            self.selected_document_ids = [*self.selected_document_ids, document_id]

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
        else:
            self.selected_document_ids = sorted(selected | set(ids))

    @rx.event
    def select_all_visible(self):
        ids = [
            doc["id"]
            for docs in self._filtered_raw().values()
            for doc in docs
        ]
        self.selected_document_ids = sorted(set(self.selected_document_ids) | set(ids))

    @rx.event
    def clear_selection(self):
        self.selected_document_ids = []

    @rx.event
    async def load_documents(self):
        """Load documents eligible under the current original-script rules."""
        self.is_loading = True
        self.status_message = "Loading documents..."
        try:
            # lemma.py applies the >=100 threshold after removing blank lemmas;
            # morphological.py applies it to all NNN rows.
            from dss_clustering.states.feature_state import FeatureState, MODE_LEMMA

            features = await self.get_state(FeatureState)
            lemma_mode = features.mode == MODE_LEMMA

            with rx.session() as session:
                statement = (
                    select(
                        Document.id,
                        Document.book,
                        Document.corpus,
                        Document.display_name,
                        func.count(LemmaRow.id),
                    )
                    .join(LemmaRow, LemmaRow.document_id == Document.id)
                    .where(LemmaRow.row_type == VALID_ROW_TYPE)
                )
                if lemma_mode:
                    cleaned_lemma = func.trim(LemmaRow.clean_lemma)
                    statement = (
                        statement.where(LemmaRow.clean_lemma.is_not(None))
                        .where(cleaned_lemma != "")
                        .where(func.lower(cleaned_lemma) != "nan")
                    )
                rows = session.exec(
                    statement.group_by(
                        Document.id,
                        Document.book,
                        Document.corpus,
                        Document.display_name,
                    ).order_by(Document.corpus, Document.book)
                ).all()

            by_corpus: dict[str, list[dict]] = defaultdict(list)
            labels: dict[str, str] = {}
            books: dict[str, str] = {}
            corpus_of: dict[str, str] = {}

            for doc_id, book, corpus, display_name, n in rows:
                if n < self.min_entries_per_book:
                    continue
                label = (display_name or "").strip() or book
                by_corpus[corpus].append(
                    {
                        "id": doc_id,
                        "book": book,
                        "label": label,
                        "n_entries": int(n),
                    }
                )
                labels[str(doc_id)] = label
                books[str(doc_id)] = book
                corpus_of[str(doc_id)] = corpus

            for docs in by_corpus.values():
                docs.sort(key=lambda d: d["label"].lower())

            ordered = [c for c in CORPUS_ORDER if c in by_corpus]
            ordered += sorted(c for c in by_corpus if c not in CORPUS_ORDER)

            self.corpora = ordered
            self.documents_by_corpus = dict(by_corpus)
            self.document_labels = labels
            self.document_books = books
            self.document_corpus = corpus_of

            eligible = set(labels)
            self.selected_document_ids = [
                i for i in self.selected_document_ids if str(i) in eligible
            ]

            total = sum(len(v) for v in by_corpus.values())
            self.status_message = (
                f"Loaded {total} books/scrolls "
                f"(min {'non-empty lemma' if lemma_mode else 'valid'} rows "
                f">= {self.min_entries_per_book})."
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            self.status_message = f"Failed to load documents: {exc}"
        finally:
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

    # ---------- computed vars ----------

    @rx.var(cache=True)
    def filtered_documents(self) -> dict[str, list[dict]]:
        """Search-filtered documents enriched with selection state."""
        selected = set(self.selected_document_ids)
        out: dict[str, list[dict]] = {}
        for corpus, docs in self._filtered_raw().items():
            out[corpus] = [{**doc, "selected": doc["id"] in selected} for doc in docs]
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
