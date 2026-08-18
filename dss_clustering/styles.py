"""Shared visual tokens for the app shell."""

from __future__ import annotations

# Light professional theme: slate surfaces, teal accent (not purple/indigo defaults).
ACCENT = "teal"
SURFACE = "var(--gray-1)"
# Faint tint used to visually separate alternating brochure sections.
SURFACE_ALT = "var(--gray-2)"
BORDER = "1px solid var(--gray-a6)"
MAX_CONTENT = "80rem"
# Prose keeps a comfortable line length even though plots use the full width.
MAX_TEXT = "46rem"

# Typography scale for the single-page "brochure" layout. Sections read like a
# magazine: a big heading, a plain-language blurb, then generously sized body.
HEADING_SIZE = "8"
BLURB_SIZE = "4"
BODY_SIZE = "3"
GITHUB_URL = "https://github.com/amiryorav/DSS-Clustering"
CONTACT_EMAIL = "amiryorav@gmail.com"
BRAND_NAME = "Hebrew Stylometry Explorer"
BRAND_TAGLINE = (
    "Interactive lexical and morphological comparison of Mikra, Mishna, and DSS."
)
EXPORT_FOOTER = "Hebrew Stylometry Explorer By Amir Yorav"
