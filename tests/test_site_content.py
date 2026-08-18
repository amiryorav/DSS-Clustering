"""Smoke test for About / How-to site copy."""

from __future__ import annotations

from dss_clustering.site_content import (
    ABOUT_BODY,
    ABOUT_SUMMARY,
    ABOUT_TITLE,
    HOW_TO_STEPS,
    HOW_TO_SUMMARY,
    HOW_TO_TITLE,
)


def test_about_copy_is_present():
    assert ABOUT_TITLE.strip()
    assert ABOUT_SUMMARY.strip()
    assert ABOUT_BODY.strip()


def test_how_to_steps_cover_the_pipeline():
    assert HOW_TO_TITLE.strip()
    assert HOW_TO_SUMMARY.strip()
    assert len(HOW_TO_STEPS) >= 6
    for step in HOW_TO_STEPS:
        assert step["title"].strip()
        assert step["body"].strip()
