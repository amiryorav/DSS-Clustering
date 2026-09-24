"""Static in-app help copy (spec §5.3).

Each entry has a short ``summary`` for inline tips and a longer ``body`` for
the Help tab. Content is documentation, not computed data — no DB.
"""

from __future__ import annotations

HELP_CONTENT: dict[str, dict[str, str]] = {
    # ----- per-step -----
    "presets": {
        "title": "Analysis presets",
        "summary": "Save or reload named analysis controls under your account.",
        "body": (
            "Guests can run the full pipeline without signing in. Sign in to "
            "snapshot the current Data→Dendrogram controls under a name. "
            "Loading a preset restores those controls and rebuilds the "
            "pipeline. Presets are stored under your account alongside saved "
            "manual book groups."
        ),
        "group": "Pipeline",
    },
    "data": {
        "title": "Data selection",
        "summary": "Choose which books and scrolls enter the experiment.",
        "body": (
            "Choose which books and scrolls enter the experiment. The "
            "minimum-entries threshold counts row_type = NNN rows per book "
            "(including rows with blank clean_lemma). Lemma mode still "
            "ignores blank clean_lemma when building word features. "
            "Identity colors are edited on the 3D plot."
        ),
        "group": "Pipeline",
    },
    "features": {
        "title": "Lemma vs morphology",
        "summary": "Pick lemma signatures or grammatical morphology columns.",
        "body": (
            "Lemma mode signs each occurrence as its clean lemma. Morphology "
            "mode joins the selected grammatical attributes into one "
            "signature string (e.g. pos=Verb|gender=M|number=S). When "
            "proper-name rows are kept, they collapse to the atomic "
            "signature subtype=properName; the ignore toggle drops them "
            "from the experiment entirely."
        ),
        "group": "Pipeline",
    },
    "vectorize": {
        "title": "Count matrix",
        "summary": "Build the book × signature count matrix used by later steps.",
        "body": (
            "Each selected occurrence becomes one signature, then signatures "
            "are counted per book into a book × signature matrix. This is "
            "the shared starting point for rescale, SVD, tables, and "
            "metrics. Rebuild after changing books or feature columns."
        ),
        "group": "Pipeline",
    },
    "rescale": {
        "title": "Active matrix weighting",
        "summary": "Choose raw counts, TF, or TF-IDF for the active matrix.",
        "body": (
            "Raw keeps occurrence counts. TF length-normalizes within each "
            "book. TF-IDF down-weights signatures that appear in many books "
            "(the default). The chosen weighting is the active matrix for "
            "SVD, tables, and purity / consistency views."
        ),
        "group": "Pipeline",
    },
    "svd": {
        "title": "What SVD is doing here",
        "summary": "Compress the active matrix into analysis dimensions for clustering.",
        "body": (
            "SVD (used the way LSA uses it) compresses thousands of sparse "
            "feature columns into a handful of composite dimensions that "
            "capture most of the shared variation between books. The sweep "
            "tries many dimension counts and keeps the one whose cophenetic "
            "correlation is highest once past the plateau — see "
            "'Cophenetic correlation'. That score selects dimensionality "
            "only; it isn't evidence that the resulting clusters are "
            "linguistically meaningful on its own."
        ),
        "group": "Pipeline",
    },
    "plot": {
        "title": "3D plot modes",
        "summary": "Explore books in 3D; color by identity or dendrogram clusters.",
        "body": (
            "SVD mode shows dims 1, 2, and 3 of the analysis embedding by "
            "default (skipping the first component, which often tracks size). "
            "Compare 4 views uses the same three SVD axes. "
            "That embedding also feeds the dendrogram and tables. "
            "PCA, UMAP, and t-SNE are "
            "visualization-only fits on the active matrix: they never "
            "change clustering, feature tables, or purity / consistency. "
            "Dendrogram-cluster coloring uses the current cut and the same "
            "palette as the tree. After those cluster colors are applied, you "
            "can still pick a custom color for any book; Reset restores that "
            "book's cluster color, and Reset colors to default clears every "
            "hand-picked color. PNG and PDF capture the current on-screen "
            "view in the browser, including any rotation you applied. "
            "The zoom, rotate, and reset buttons above each scene move its "
            "camera without touching the mouse; each scene keeps its own view. "
            "'Compare 4 views' shows SVD dims 1,2,3 and t-SNE immediately. "
            "PCA and UMAP stay off until you click Fit in those cells, so the "
            "Cloud VM stays up. Colour, label, and visibility changes "
            "update the fitted panels automatically; 'Rebuild grid' only "
            "refits projections. Labels start hidden. "
            "Clicking a point starts a fresh manual group when picking is "
            "inactive, then toggles that book in the group."
        ),
        "group": "Pipeline",
    },
    "dendrogram": {
        "title": "Hierarchical clustering",
        "summary": "Cut the tree to define automatic clusters of books.",
        "body": (
            "Built from the SVD analysis embedding. Ward linkage locks "
            "distance to Euclidean; average linkage may use Euclidean or "
            "cosine. Changing the cut height recolors clusters "
            "without refitting the tree. When Ward-artifact marking is on, gray "
            "italic leaves have less than 20% overlap across top-5 Ward, "
            "SVD-Euclidean, and SVD-cosine neighbors. This is enabled for "
            "morphology only: lemma features flag roughly a quarter of the "
            "corpus versus about a tenth for morphology, so the mode switch "
            "turns it on for morphology and off for lemma. The count also "
            "grows with the number of SVD components. "
            "Leaf clicks feed the manual group tool when picking is active."
        ),
        "group": "Pipeline",
    },
    "manual_cluster": {
        "title": "Manual group tool",
        "summary": "Pick books by hand and save them as a named group.",
        "body": (
            "Start selecting, then click books on the 3D plot or dendrogram, "
            "or add a whole dendrogram cluster from the dropdown. Done finishes "
            "the pick — name the group and save it. Guests keep groups for this "
            "visit; signed-in users store them under their account. Use a saved "
            "group as either side when comparing in The numbers."
        ),
        "group": "Pipeline",
    },
    "tables": {
        "title": "Feature tables and metrics",
        "summary": "Compare group X to group Y and list top, common, distinctive, and gap features.",
        "body": (
            "Choose subject X and reference Y (corpus, dendrogram cluster, "
            "saved manual group, or single book). Book lists are searchable "
            "like the plot colouring list. Books shared by both "
            "sides are removed from Y. Top features are X only; common "
            "features appear in both X and Y. Corpus-wide stability is shown "
            "above the tables; purity appears when X is one book and "
            "consistency when X is a multi-book group."
        ),
        "group": "Pipeline",
    },
    # ----- glossary -----
    "cophenetic_correlation": {
        "title": "Cophenetic correlation",
        "summary": "Scores how well a Ward dendrogram matches distances in an embedding.",
        "body": (
            "How faithfully a Ward/Euclidean dendrogram's merge heights "
            "reflect the actual pairwise distances between books in a given "
            "embedding. Used here only to pick SVD dimensionality — not as "
            "evidence of corpus separation, cluster validity, or "
            "historical/linguistic significance."
        ),
        "group": "Methods",
    },
    "top_features": {
        "title": "Top features",
        "summary": "Features this group uses most, with no comparison.",
        "body": (
            "The features this group of books uses most, in absolute terms "
            "— no comparison to anything else."
        ),
        "group": "Metrics",
    },
    "common_features": {
        "title": "Common features",
        "summary": "Features used in both X and Y, ranked by combined usage.",
        "body": (
            "Signatures that appear in both the subject and the reference "
            "(mean usage greater than zero on each side), ranked by how "
            "common they are across the combined X and Y books. Useful for "
            "seeing what a book or cluster shares with its neighbors, not "
            "what sets them apart."
        ),
        "group": "Metrics",
    },
    "distinctive_features": {
        "title": "Distinctive features",
        "summary": "Features used more in X than in Y.",
        "body": (
            "Features especially characteristic of this group relative to "
            "the comparison group — not just common here, but notably more "
            "common here than there. High usage alone doesn't make a "
            "feature distinctive; a large gap between the two groups does."
        ),
        "group": "Metrics",
    },
    "gap_features": {
        "title": "Gap features",
        "summary": "Features used more in Y than in X.",
        "body": (
            "Features the comparison group uses heavily that this group "
            "barely uses — what X is conspicuously missing relative to Y."
        ),
        "group": "Metrics",
    },
    "consistency_score": {
        "title": "Consistency / purity scores",
        "summary": "Neighborhood checks for a book or group across distance views.",
        "body": (
            "Three related numbers appear around the tables: corpus purity "
            "(does this book's neighborhood match its own corpus?), cluster "
            "consistency (do this cluster's other members actually show up "
            "as neighbors?), and an overall stability check across distance "
            "views. Exact definitions follow the research formulas "
            "(neighbor k = 10 for purity, k = 5 for consistency / "
            "stability)."
        ),
        "group": "Metrics",
    },
    "ward": {
        "title": "Ward linkage",
        "summary": "Merge rule that minimizes within-cluster variance (Euclidean only).",
        "body": (
            "Merges clusters to minimize increase in within-cluster "
            "variance. Only well-defined for Euclidean distance — the UI "
            "locks the metric accordingly. SVD sweep scoring always uses "
            "Ward + Euclidean regardless of the dendrogram linkage you "
            "choose for display."
        ),
        "group": "Methods",
    },
    "average_link": {
        "title": "Average linkage",
        "summary": "Merge by average pairwise distance; allows Euclidean or cosine.",
        "body": (
            "Merges clusters by average pairwise distance. Unlike Ward, it "
            "may use Euclidean or cosine distance. Changing linkage here "
            "regroups books in the tree; it does not change how many SVD "
            "dimensions were selected."
        ),
        "group": "Methods",
    },
    "tf_tfidf": {
        "title": "TF and TF-IDF",
        "summary": "Weight raw counts by book length and (for TF-IDF) document rarity.",
        "body": (
            "TF scales each book's signature counts by that book's total. "
            "TF-IDF further multiplies by an inverse-document-frequency "
            "weight so signatures shared by many books contribute less. "
            "Both use scikit-learn's TfidfTransformer defaults."
        ),
        "group": "Methods",
    },
    "pca": {
        "title": "PCA (visualization only)",
        "summary": "A linear 3D layout of the weighted matrix; analysis results stay unchanged.",
        "body": (
            "Principal Component Analysis of the active weighted count "
            "matrix, mean-centered, showing the first three components. "
            "Unlike UMAP and t-SNE, PCA is not compressed with Truncated SVD "
            "first — it uses the original (densified) matrix. Unlike the SVD "
            "panel — uncentered Truncated SVD of the analysis embedding that "
            "also feeds the tree — PCA is visualization-only. It does not "
            "change clustering, tables, or metrics. The comparison grid "
            "leaves PCA off until you click Fit PCA, so Cloud RAM stays free."
        ),
        "group": "Methods",
    },
    "umap": {
        "title": "UMAP (visualization only)",
        "summary": "A 3D layout for exploration; it does not change analysis results.",
        "body": (
            "A nonlinear 3D layout of the active matrix for exploration. "
            "It does not feed the dendrogram, tables, or metrics. "
            "The fit first compresses the wide count matrix with TruncatedSVD "
            "(50 components). The comparison grid leaves UMAP off until you "
            "click Fit UMAP, because the fit can exhaust the Cloud VM; you can "
            "also choose UMAP in the single-view plot. n_neighbors and min_dist "
            "trade local versus global structure in the drawing."
        ),
        "group": "Methods",
    },
    "tsne": {
        "title": "t-SNE (visualization only)",
        "summary": "Another exploratory 3D layout; analysis results stay unchanged.",
        "body": (
            "Another stochastic 3D layout of the active matrix. Perplexity "
            "controls the effective neighborhood size. Like UMAP, it never "
            "invalidates analysis-space results."
        ),
        "group": "Methods",
    },
}


HELP_GROUPS = ("Pipeline", "Methods", "Metrics")


def help_entry(key: str) -> dict[str, str]:
    """Return a help entry, or a safe fallback for unknown keys."""
    return HELP_CONTENT.get(
        key,
        {
            "title": key,
            "summary": "No short tip is defined for this topic yet.",
            "body": "No help text is defined for this topic yet.",
            "group": "Pipeline",
        },
    )


def help_catalog_rows() -> list[dict[str, str]]:
    """Flat list for the Help tab search / accordion."""
    rows: list[dict[str, str]] = []
    for key, entry in HELP_CONTENT.items():
        rows.append(
            {
                "key": key,
                "title": entry["title"],
                "summary": entry["summary"],
                "body": entry["body"],
                "group": entry.get("group", "Pipeline"),
            }
        )
    return rows
