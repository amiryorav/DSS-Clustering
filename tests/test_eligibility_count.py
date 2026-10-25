"""Words-mode catalog threshold: all NNN rows vs rows that have a lemma."""

from dss_clustering.states.data_state import (
    LEMMA_COUNT_NNN,
    LEMMA_COUNT_WITH_VALUE,
    uses_lemma_row_minimum,
)


def test_grammar_always_counts_nnn_rows():
    assert not uses_lemma_row_minimum(
        feature_mode="morphology",
        lemma_min_count=LEMMA_COUNT_WITH_VALUE,
    )


def test_words_mode_can_require_a_lemma_value():
    assert uses_lemma_row_minimum(
        feature_mode="lemma",
        lemma_min_count=LEMMA_COUNT_WITH_VALUE,
    )
    assert not uses_lemma_row_minimum(
        feature_mode="lemma",
        lemma_min_count=LEMMA_COUNT_NNN,
    )
