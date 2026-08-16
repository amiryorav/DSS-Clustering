"""Static in-app help copy (spec §5.3).

Content is documentation, not computed data — one dictionary, no DB.
"""

from __future__ import annotations

HELP_CONTENT: dict[str, dict[str, str]] = {
    # ----- per-step -----
    "presets": {
        "title": "Analysis presets",
        "body": (
            "Snapshot the current Data→Dendrogram controls under a name for "
            "this browser session. Loading a preset restores those controls "
            "and rebuilds the pipeline. Presets are not written to the "
            "database while the app runs localhost-only."
        ),
    },
    "data": {
        "title": "Data selection",
        "body": (
            "Choose which books and scrolls enter the experiment. Only "
            "row_type = NNN rows count toward eligibility; in lemma mode, "
            "blank clean_lemma rows are excluded before the minimum-entries "
            "check, matching the original lemma pipeline. Identity colors "
            "are edited on the 3D plot."
        ),
    },
    "features": {
        "title": "Lemma vs morphology",
        "body": (
            "Lemma mode signs each occurrence as its clean lemma. Morphology "
            "mode joins the selected grammatical attributes into one "
            "signature string (e.g. pos=Verb|gender=M|number=S). When "
            "proper-name rows are kept, they collapse to the atomic "
            "signature subtype=properName; the ignore toggle drops them "
            "from the experiment entirely."
        ),
    },
    "vectorize": {
        "title": "Count matrix",
        "body": (
            "Each selected occurrence becomes one signature, then signatures "
            "are counted per book into a book × signature matrix. This is "
            "the shared starting point for rescale, SVD, tables, and "
            "metrics. Rebuild after changing books or feature columns."
        ),
    },
    "rescale": {
        "title": "Active matrix weighting",
        "body": (
            "Raw keeps occurrence counts. TF length-normalizes within each "
            "book. TF-IDF down-weights signatures that appear in many books "
            "(the default, matching the original notebooks). The chosen "
            "weighting is the active matrix for SVD, tables, and purity / "
            "consistency views."
        ),
    },
    "svd": {
        "title": "What SVD is doing here",
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
    },
    "plot": {
        "title": "3D plot modes",
        "body": (
            "SVD mode shows three axes of the analysis embedding that also "
            "feeds the dendrogram and tables. UMAP and t-SNE are "
            "visualization-only fits on the active matrix: they never "
            "change clustering, feature tables, or purity / consistency. "
            "Dendrogram-cluster coloring uses the current cut and the same "
            "palette as the tree. Rotating the plot also updates the camera "
            "used by PNG and PDF exports. "
            "Clicking a point starts a fresh manual group when picking is "
            "inactive, then toggles that book in the group."
        ),
    },
    "dendrogram": {
        "title": "Hierarchical clustering",
        "body": (
            "Built from the SVD analysis embedding. Ward linkage locks "
            "distance to Euclidean; average linkage may use Euclidean or "
            "cosine. Releasing the cut-height slider recolors clusters "
            "without refitting the tree. When Ward-artifact marking is on, gray "
            "italic leaves have less than 20% overlap across top-5 Ward, "
            "SVD-Euclidean, and SVD-cosine neighbors. The original enabled "
            "this for morphology only: lemma features flag roughly a quarter "
            "of the corpus versus about a tenth for morphology, so the mode "
            "switch turns it on for morphology and off for lemma. The count "
            "also grows with the number of SVD components. "
            "Leaf clicks feed the manual cluster tool when picking is active."
        ),
    },
    "manual_cluster": {
        "title": "Manual cluster tool",
        "body": (
            "Start selecting, then click books on the 3D plot or dendrogram. "
            "Done compares the picked set against a reference group "
            "(corpus, all other selected books, or an existing auto "
            "cluster) using the same top / distinctive / gap definitions "
            "as the tables step. Named groups are saved for this session "
            "only."
        ),
    },
    "tables": {
        "title": "Feature tables and metrics",
        "body": (
            "Top, distinctive, and gap features for a corpus, cluster, or "
            "book scope. Corpus-wide stability is shown once above the "
            "tables; purity appears in book scope and consistency in "
            "cluster scope. See the glossary entries for each table and "
            "for consistency / purity."
        ),
    },
    # ----- glossary -----
    "cophenetic_correlation": {
        "title": "Cophenetic correlation",
        "body": (
            "How faithfully a Ward/Euclidean dendrogram's merge heights "
            "reflect the actual pairwise distances between books in a given "
            "embedding. Used here only to pick SVD dimensionality — not as "
            "evidence of corpus separation, cluster validity, or "
            "historical/linguistic significance."
        ),
    },
    "top_features": {
        "title": "Top features",
        "body": (
            "The features this group of books uses most, in absolute terms "
            "— no comparison to anything else."
        ),
    },
    "distinctive_features": {
        "title": "Distinctive features",
        "body": (
            "Features especially characteristic of this group relative to "
            "the comparison group — not just common here, but notably more "
            "common here than there. High usage alone doesn't make a "
            "feature distinctive; a large gap between the two groups does."
        ),
    },
    "gap_features": {
        "title": "Gap features",
        "body": (
            "Features the nearest comparable group (or a book's top SVD "
            "neighbors) uses heavily that this group barely uses — what "
            "this group is conspicuously missing relative to that "
            "neighbor set, matching the original notebook reports."
        ),
    },
    "consistency_score": {
        "title": "Consistency / purity scores",
        "body": (
            "Three related numbers appear around the tables: corpus purity "
            "(does this book's neighborhood match its own corpus?), cluster "
            "consistency (do this cluster's other members actually show up "
            "as neighbors?), and an overall stability check across distance "
            "views. Exact definitions follow the research formulas "
            "(neighbor k = 10 for purity, k = 5 for consistency / "
            "stability)."
        ),
    },
    "ward": {
        "title": "Ward linkage",
        "body": (
            "Merges clusters to minimize increase in within-cluster "
            "variance. Only well-defined for Euclidean distance — the UI "
            "locks the metric accordingly. SVD sweep scoring always uses "
            "Ward + Euclidean regardless of the dendrogram linkage you "
            "choose for display."
        ),
    },
    "average_link": {
        "title": "Average linkage",
        "body": (
            "Merges clusters by average pairwise distance. Unlike Ward, it "
            "may use Euclidean or cosine distance. Changing linkage here "
            "regroups books in the tree; it does not change how many SVD "
            "dimensions were selected."
        ),
    },
    "tf_tfidf": {
        "title": "TF and TF-IDF",
        "body": (
            "TF scales each book's signature counts by that book's total. "
            "TF-IDF further multiplies by an inverse-document-frequency "
            "weight so signatures shared by many books contribute less. "
            "Both use scikit-learn's TfidfTransformer defaults."
        ),
    },
    "umap": {
        "title": "UMAP (visualization only)",
        "body": (
            "A nonlinear 3D layout of the active matrix for exploration. "
            "It does not feed the dendrogram, tables, or metrics. "
            "n_neighbors and min_dist trade local versus global structure "
            "in the drawing."
        ),
    },
    "tsne": {
        "title": "t-SNE (visualization only)",
        "body": (
            "Another stochastic 3D layout of the active matrix. Perplexity "
            "controls the effective neighborhood size. Like UMAP, it never "
            "invalidates analysis-space results."
        ),
    },
}


def help_entry(key: str) -> dict[str, str]:
    """Return a help entry, or a safe fallback for unknown keys."""
    return HELP_CONTENT.get(
        key,
        {
            "title": key,
            "body": "No help text is defined for this topic yet.",
        },
    )
