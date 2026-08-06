"""3D plot step: SVD scatter (spec §8.6, Phase 1 — SVD mode only)."""

from __future__ import annotations

import reflex as rx
from plotly.graph_objects import Figure

from dss_clustering.pipeline.plotting import make_3d_scatter
from dss_clustering.pipeline.runtime import get_embedding
from dss_clustering.states.data_state import (
    CORPUS_LABELS,
    CORPUS_ORDER,
    FALLBACK_COLOR,
    DataState,
)
from dss_clustering.states.svd_state import SVDState

LABEL_SHORT = "short"
LABEL_HIDDEN = "hidden"


class PlotState(rx.State):
    """Interactive 3D scatter of books from the analysis embedding."""

    method: str = "svd"  # Phase 1: SVD only
    dim_x: int = 0
    dim_y: int = 1
    dim_z: int = 2
    label_mode: str = LABEL_SHORT
    # document_id strings currently hidden on the plot (redraw only)
    hidden_document_ids: list[str] = []
    # Books in the current embedding (for show/hide + color controls)
    plot_books: list[dict] = []
    book_search: str = ""

    figure: Figure | None = None
    has_figure: bool = False
    status_message: str = "Run SVD to generate the 3D plot."
    max_dim_index: int = 0

    @rx.var(cache=True)
    def filtered_plot_books(self) -> list[dict]:
        """Books list filtered by the plot-side search box."""
        q = self.book_search.strip().lower()
        if not q:
            return self.plot_books
        return [
            b
            for b in self.plot_books
            if q in str(b["short"]).lower()
            or q in str(b["label"]).lower()
            or q in str(b.get("corpus", "")).lower()
        ]

    @rx.var(cache=True)
    def plot_corpora(self) -> list[dict]:
        """Per-corpus show/hide summary for books currently on the plot."""
        by_corpus: dict[str, list[dict]] = {}
        for book in self.plot_books:
            corpus = str(book.get("corpus", "")) or "unknown"
            by_corpus.setdefault(corpus, []).append(book)

        ordered = [c for c in CORPUS_ORDER if c in by_corpus]
        ordered += sorted(c for c in by_corpus if c not in CORPUS_ORDER)

        rows: list[dict] = []
        for corpus in ordered:
            books = by_corpus[corpus]
            n_visible = sum(1 for b in books if b["visible"])
            rows.append(
                {
                    "corpus": corpus,
                    "label": CORPUS_LABELS.get(corpus, corpus.title()),
                    "all_visible": n_visible == len(books) and len(books) > 0,
                    "n_visible": n_visible,
                    "n_total": len(books),
                }
            )
        return rows

    @rx.var(cache=True)
    def hidden_count(self) -> int:
        return len(self.hidden_document_ids)

    @rx.event
    def set_book_search(self, value: str):
        self.book_search = value

    @rx.event
    def set_dim_x(self, value: str):
        try:
            self.dim_x = max(0, int(value))
        except (TypeError, ValueError):
            return
        return PlotState.recompute

    @rx.event
    def set_dim_y(self, value: str):
        try:
            self.dim_y = max(0, int(value))
        except (TypeError, ValueError):
            return
        return PlotState.recompute

    @rx.event
    def set_dim_z(self, value: str):
        try:
            self.dim_z = max(0, int(value))
        except (TypeError, ValueError):
            return
        return PlotState.recompute

    @rx.event
    def set_label_mode(self, mode: str | list[str]):
        value = mode[0] if isinstance(mode, list) else mode
        if value in (LABEL_SHORT, LABEL_HIDDEN):
            self.label_mode = value
            return PlotState.recompute

    @rx.event
    def toggle_book_visibility(self, document_id: int):
        key = str(document_id)
        if key in self.hidden_document_ids:
            self.hidden_document_ids = [
                k for k in self.hidden_document_ids if k != key
            ]
        else:
            self.hidden_document_ids = [*self.hidden_document_ids, key]
        return PlotState.recompute

    @rx.event
    def show_all_books(self):
        self.hidden_document_ids = []
        return PlotState.recompute

    @rx.event
    def show_matching_books(self):
        matched = {str(b["id"]) for b in self.filtered_plot_books}
        self.hidden_document_ids = [
            k for k in self.hidden_document_ids if k not in matched
        ]
        return PlotState.recompute

    @rx.event
    def hide_matching_books(self):
        matched = {str(b["id"]) for b in self.filtered_plot_books}
        self.hidden_document_ids = sorted(set(self.hidden_document_ids) | matched)
        return PlotState.recompute

    @rx.event
    def toggle_corpus_visibility(self, corpus: str):
        """Show or hide every book from a corpus on the plot (redraw only)."""
        ids = [
            str(b["id"])
            for b in self.plot_books
            if str(b.get("corpus", "")) == corpus
        ]
        if not ids:
            return
        hidden = set(self.hidden_document_ids)
        if all(i not in hidden for i in ids):
            self.hidden_document_ids = sorted(hidden | set(ids))
        else:
            remove = set(ids)
            self.hidden_document_ids = [
                k for k in self.hidden_document_ids if k not in remove
            ]
        return PlotState.recompute

    @rx.event
    async def set_book_color(self, document_id: int, color: str):
        """Change identity color and redraw — no SVD / matrix recalculation."""
        data = await self.get_state(DataState)
        data.document_color_override = {
            **data.document_color_override,
            str(document_id): color,
        }
        return PlotState.recompute

    @rx.event
    async def clear_book_color(self, document_id: int):
        data = await self.get_state(DataState)
        overrides = dict(data.document_color_override)
        overrides.pop(str(document_id), None)
        data.document_color_override = overrides
        return PlotState.recompute

    @rx.event
    async def recompute(self):
        svd = await self.get_state(SVDState)
        data = await self.get_state(DataState)

        if not svd.has_embedding:
            self.has_figure = False
            self.figure = None
            self.plot_books = []
            self.status_message = "Run SVD to generate the 3D plot."
            return

        emb = get_embedding(self.router.session.client_token)
        if emb is None:
            emb = get_embedding(svd.router.session.client_token)
        if emb is None:
            self.has_figure = False
            self.figure = None
            self.plot_books = []
            self.status_message = "Embedding not found in server memory — re-run SVD."
            return

        X = emb.embedding
        n_dims = int(X.shape[1])
        self.max_dim_index = max(0, n_dims - 1)
        if n_dims < 1:
            self.has_figure = False
            self.figure = None
            self.plot_books = []
            self.status_message = "Embedding has no dimensions to plot."
            return

        def _clamp(i: int) -> int:
            return min(max(0, i), n_dims - 1)

        ix, iy, iz = _clamp(self.dim_x), _clamp(self.dim_y), _clamp(self.dim_z)
        self.dim_x, self.dim_y, self.dim_z = ix, iy, iz

        if X.shape[0] < 1:
            self.has_figure = False
            self.figure = None
            self.plot_books = []
            self.status_message = "No books in the embedding."
            return

        hidden = set(self.hidden_document_ids)
        show_labels = self.label_mode == LABEL_SHORT

        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        point_labels: list[str] = []
        hover_labels: list[str] = []
        colors: list[str] = []
        visible_ids: list[int] = []
        book_rows: list[dict] = []

        for i, doc_id in enumerate(emb.document_ids):
            key = str(doc_id)
            short = data.document_books.get(key) or data.document_labels.get(key, key)
            full = data.document_labels.get(key, short)
            corpus = data.document_corpus.get(key, "")
            color = (
                data.document_color_override.get(key)
                or data.corpus_default_color.get(corpus, FALLBACK_COLOR)
            )
            visible = key not in hidden
            book_rows.append(
                {
                    "id": doc_id,
                    "short": short,
                    "label": full,
                    "corpus": corpus,
                    "color": color,
                    "visible": visible,
                    "has_override": key in data.document_color_override,
                }
            )
            if not visible:
                continue
            xs.append(float(X[i, ix]))
            ys.append(float(X[i, iy]))
            zs.append(float(X[i, iz]))
            point_labels.append(short)
            hover_labels.append(full)
            colors.append(color)
            visible_ids.append(doc_id)

        book_rows.sort(key=lambda r: str(r["short"]).lower())
        self.plot_books = book_rows

        if not visible_ids:
            self.has_figure = False
            self.figure = None
            self.status_message = (
                "All books are hidden — show at least one book to plot."
            )
            return

        try:
            self.figure = make_3d_scatter(
                xs,
                ys,
                zs,
                labels=point_labels,
                hover_labels=hover_labels,
                colors=colors,
                document_ids=visible_ids,
                axis_titles=(f"Dim {ix}", f"Dim {iy}", f"Dim {iz}"),
                show_labels=show_labels,
            )
            self.has_figure = True
            label_note = "short labels" if show_labels else "labels hidden"
            self.status_message = (
                f"SVD scatter of {len(visible_ids)}/"
                f"{len(emb.document_ids)} books "
                f"(dims {ix}, {iy}, {iz} of {n_dims}; {label_note})."
            )
        except Exception as exc:  # noqa: BLE001
            self.has_figure = False
            self.figure = None
            self.status_message = f"Plot failed: {exc}"
