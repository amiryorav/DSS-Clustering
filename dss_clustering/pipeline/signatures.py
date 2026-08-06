"""Signature construction for lemma / morphology feature modes (spec §8.2–8.3).

Proper-name handling (project rule, superseding the original collapse-to-
``subtype=properName`` exception): when ``ignore_proper_names`` is set, every
row with ``subtype == "properName"`` is dropped from the experiment entirely
before signatures / counts are built.
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


def row_signature(
    values: dict[str, Any],
    selected_columns: list[str],
) -> str:
    """Reference per-row signature rule.

    Faster paths (vectorized / SQL) must match this exactly. Proper-name rows
    must already have been filtered out when ignore-proper-name is on.
    """
    parts = [
        f"{col}={values[col]}"
        for col in selected_columns
        if pd.notna(values.get(col)) and str(values.get(col)) not in MISSING_STRINGS
    ]
    return "|".join(parts) if parts else "EMPTY"


def build_signatures_vectorized(
    df: pd.DataFrame,
    selected_columns: list[str],
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
    return (
        parts_df.stack(future_stack=True)
        .dropna()
        .groupby(level=0)
        .agg("|".join)
        .reindex(df.index)
        .fillna("EMPTY")
    )
