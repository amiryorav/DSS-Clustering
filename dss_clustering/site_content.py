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
    "contrasts without rewriting notebook code for every trial. Analysis "
    "requires Google sign-in so manual book groups can be saved under your "
    "account."
)

HOW_TO_TITLE = "How to use this site"

HOW_TO_SUMMARY = (
    "A typical path from sign-in through tables. Short tips also sit next "
    "to each Analysis control; this page is the end-to-end walkthrough."
)

# Ordered steps for the Help overview. Keep labels aligned with the wizard rail.
HOW_TO_STEPS: list[dict[str, str]] = [
    {
        "title": "Open Analysis and sign in",
        "body": (
            "Use Start analysis or the Analysis tab. Sign in with Google when "
            "asked so saved manual groups stay attached to your account."
        ),
    },
    {
        "title": "Optional: load a preset",
        "body": (
            "On Presets, restore a named snapshot of earlier controls for this "
            "browser session, or continue with the defaults."
        ),
    },
    {
        "title": "Select books",
        "body": (
            "On Data, choose which Mikra, Mishna, and DSS documents enter the "
            "experiment. Later steps only see this selection."
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
            "raw, TF, or TF-IDF on Rescale. Rebuild Vectorize after book or "
            "feature changes."
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
