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
    "Everything lives on one page — scroll from top to bottom. Short tips sit "
    "next to individual controls; this is the end-to-end walkthrough."
)

# Ordered steps for the Help overview. Keep aligned with the one-page sections.
HOW_TO_STEPS: list[dict[str, str]] = [
    {
        "title": "1 · Choose your texts",
        "body": (
            "Every eligible book starts selected. Search and untick anything "
            "you want to leave out. Guests can run everything without signing "
            "in; sign in only to save settings and hand-picked groups."
        ),
    },
    {
        "title": "2 · Words or grammar",
        "body": (
            "Compare the texts by the words they use, or by their grammar. "
            "Words is a good starting point; deeper feature choices live under "
            "'Under the hood'."
        ),
    },
    {
        "title": "3 · Run the analysis",
        "body": (
            "One button counts the features, weights them, and reduces the "
            "numbers behind the scenes. The weighting and dimensionality "
            "controls are tucked under the hood if you want them."
        ),
    },
    {
        "title": "4 · The 3D map",
        "body": (
            "Every book is a dot; books that use language similarly sit close "
            "together. Rotate and zoom with the buttons, or compare four "
            "projections side by side."
        ),
    },
    {
        "title": "5 · The dendrogram",
        "body": (
            "The same closeness drawn as a tree. Slide the cut line to split "
            "the books into more or fewer clusters."
        ),
    },
    {
        "title": "6 · Your own groups",
        "body": (
            "Click books on the map to gather them into a group, then see what "
            "makes that group stand out. Groups you name are usable in the "
            "comparison tables straight away; they last for your visit, and "
            "signing in keeps them for next time."
        ),
    },
    {
        "title": "7 · The numbers",
        "body": (
            "Compare any two groups — a book, a family from the tree, one of "
            "your groups, or a whole corpus — and read which features set them "
            "apart. Export plots and tables anytime."
        ),
    },
]
