"""Signature construction for lemma / morphology feature modes (spec §8.2–8.3).

Proper-name rows (``subtype == "properName"``) collapse to the atomic signature
``subtype=properName`` when ``collapse_proper_names`` is set, matching the
original morphological notebook. When it is off, those rows keep the other
selected grammar attributes. When ``ignore_proper_names`` is set, the rows
are dropped from the experiment entirely before signatures are built.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

MISSING_STRINGS = {"UNKNOWN", "nan", "None", "none", ""}

MORPH_COLUMNS = (
    "pos",
    "gender",
    "number",
    "person",
    "tense",
    "binyan",
    "state",
    "subtype",
)

PROPER_NAME_SUBTYPE = "properName"
PROPER_NAME_SIGNATURE = f"subtype={PROPER_NAME_SUBTYPE}"


def filter_experiment_rows(
    df: pd.DataFrame,
    *,
    ignore_proper_names: bool,
) -> pd.DataFrame:
    """Drop rows that must not enter the experiment.

    When ``ignore_proper_names`` is True, rows with ``subtype == properName``
    are removed completely (lemma and morphology modes alike).
    """
    if not ignore_proper_names or "subtype" not in df.columns:
        return df
    return df.loc[df["subtype"] != PROPER_NAME_SUBTYPE].copy()


def _is_lemma_only(selected_columns: list[str]) -> bool:
    return list(selected_columns) == ["clean_lemma"]


def row_signature(
    values: dict[str, Any],
    selected_columns: list[str],
    *,
    collapse_proper_names: bool = True,
) -> str:
    """Reference per-row signature rule.

    Faster paths (vectorized / SQL) must match this exactly. Proper-name rows
    must already have been filtered out when ignore-proper-name is on. When
    they are kept and ``collapse_proper_names`` is set, morphology signatures
    collapse to ``subtype=properName``.
    """
    if (
        collapse_proper_names
        and not _is_lemma_only(selected_columns)
        and values.get("subtype") == PROPER_NAME_SUBTYPE
    ):
        return PROPER_NAME_SIGNATURE

    parts = [
        f"{col}={values[col]}"
        for col in selected_columns
        if pd.notna(values.get(col)) and str(values.get(col)) not in MISSING_STRINGS
    ]
    return "|".join(parts) if parts else "EMPTY"


def build_signatures_vectorized(
    df: pd.DataFrame,
    selected_columns: list[str],
    *,
    collapse_proper_names: bool = True,
) -> pd.Series:
    """Vectorized equivalent of :func:`row_signature`."""
    if not selected_columns:
        return pd.Series("EMPTY", index=df.index, dtype=object)

    parts: dict[str, np.ndarray] = {}
    for col in selected_columns:
        series = df[col]
        valid = series.notna() & ~series.astype(str).isin(MISSING_STRINGS)
        parts[col] = np.where(valid, col + "=" + series.astype(str), np.nan)

    parts_df = pd.DataFrame(parts, index=df.index)
    # Drop missing cells before join so EMPTY rows and partial morphs match
    # row_signature (pandas 3 stack keeps NaNs when future_stack=True).
    signatures = (
        parts_df.stack(future_stack=True)
        .dropna()
        .groupby(level=0)
        .agg("|".join)
        .reindex(df.index)
        .fillna("EMPTY")
    )

    if (
        collapse_proper_names
        and not _is_lemma_only(selected_columns)
        and "subtype" in df.columns
    ):
        is_proper = df["subtype"] == PROPER_NAME_SUBTYPE
        signatures = signatures.where(~is_proper, PROPER_NAME_SIGNATURE)

    return signatures
