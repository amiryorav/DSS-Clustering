"""Static About and How-to-use copy for the public pages.

Kept separate from per-control ``help_content`` so the landing and Help
overview stay easy to edit without touching the pipeline tip catalog.
"""

from __future__ import annotations

ABOUT_TITLE = "About this site"

ABOUT_SUMMARY = (
    "An interactive workspace for Hebrew stylometry — comparing how "
    "Biblical, Mishnaic, and Dead Sea Scrolls texts use words and grammar."
)

ABOUT_BODY = (
    "Hebrew Stylometry Explorer turns a large annotated corpus into a "
    "guided experiment: pick books, choose lemma or morphology features, "
    "build a book × signature matrix, reduce and cluster it, then inspect "
    "which features distinguish one group from another. It is meant for "
    "researchers who want to explore stylistic neighborhoods and feature "
    "contrasts without rewriting notebook code for every trial. Guests can "
    "run the full analysis without signing in; Google sign-in is optional "
    "when you want presets or manual book groups saved under your account."
)

HOW_TO_TITLE = "How to use this site"

HOW_TO_SUMMARY = (
    "A typical path from Analysis through tables. Short tips also sit next "
    "to each Analysis control; this page is the end-to-end walkthrough."
)

# Ordered steps for the Help overview. Keep labels aligned with the wizard rail.
HOW_TO_STEPS: list[dict[str, str]] = [
    {
        "title": "Open Analysis (sign-in optional)",
        "body": (
            "Use Start analysis or the Analysis tab. Guests can run the full "
            "pipeline immediately. Sign in with Google only when you want "
            "presets or manual groups saved to your account."
        ),
    },
    {
        "title": "Optional: load a preset",
        "body": (
            "On Presets, restore a named snapshot of controls you saved "
            "earlier (requires sign-in), or continue with the defaults."
        ),
    },
    {
        "title": "Select books",
        "body": (
            "On Data, every eligible book starts selected. Narrow the set if "
            "you only want Mikra, Mishna, or DSS documents in the experiment."
        ),
    },
    {
        "title": "Choose features",
        "body": (
            "Pick lemma signatures or morphology columns, and decide whether "
            "proper-name rows are kept or ignored."
        ),
    },
    {
        "title": "Build and weight the matrix",
        "body": (
            "Run Vectorize to build the book × signature counts, then choose "
            "raw, TF, or TF-IDF on Rescale (TF is the default). Rebuild "
            "Vectorize after book or feature changes."
        ),
    },
    {
        "title": "Optional: SVD",
        "body": (
            "Compress the active matrix for clustering. Sweep mode picks a "
            "dimension count from cophenetic correlation within what the "
            "matrix size allows."
        ),
    },
    {
        "title": "Explore space and clusters",
        "body": (
            "Use the 3D plot for layout, the dendrogram to cut hierarchical "
            "clusters, and Manual group to pick books by hand and save them."
        ),
    },
    {
        "title": "Compare and export",
        "body": (
            "On Tables, compare any two entities (book, cluster, manual group, "
            "or the whole corpus). Export plots and tables when you want a "
            "shareable record."
        ),
    },
]
