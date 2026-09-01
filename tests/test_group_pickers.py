"""Helpers for comparison book search and manual-group cluster adds."""

from __future__ import annotations

from dss_clustering.states.manual_cluster_state import union_document_ids
from dss_clustering.states.table_state import filter_labeled_options


def test_filter_labeled_options_matches_short_full_and_corpus():
    options = [
        {"value": "1", "label": "Dan", "full": "Daniel", "corpus": "mikra"},
        {"value": "2", "label": "1QS", "full": "Community Rule", "corpus": "dss"},
    ]
    matched = filter_labeled_options(options, "comm", "2")
    assert [row["value"] for row in matched] == ["2"]
    assert matched[0]["selected"] is True
    assert filter_labeled_options(options, "mikra", "1")[0]["value"] == "1"


def test_union_document_ids_appends_only_new_books():
    picked, added = union_document_ids([4, 1], [1, 2, 3])
    assert picked == [4, 1, 2, 3]
    assert added == 2
    again, added_again = union_document_ids(picked, [1, 2, 3])
    assert again == picked
    assert added_again == 0
