"""Frozen AnalysisConfig — analysis-space snapshot (spec §7 / §8.10)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnalysisConfig:
    """Immutable configuration that defines the analysis space.

    Deliberately excludes rendering-only fields (colors, 3D method, UMAP/t-SNE,
    table filter text).
    """

    selected_document_ids: tuple[int, ...]
    feature_mode: str  # "lemma" | "morphology"
    morph_columns: tuple[str, ...]
    apply_proper_name_exception: bool
    rescale_mode: str  # "raw" | "tf" | "tfidf"
    svd_enabled: bool
    svd_mode: str  # "constant" | "sweep"
    svd_n_components: int
    svd_sweep_range: tuple[int, int, int] | None  # (min, max, step)
    svd_normalize: bool
    svd_random_state: int
    svd_plateau_min: int
    linkage_method: str  # "ward" | "average"
    distance_metric: str  # "euclidean" | "cosine"
    cut_height: float
    # document_id str → excluded DSS fragment keys (e.g. ["f13"])
    excluded_fragments: dict[str, list[str]] = field(default_factory=dict)
    # Kept proper-name rows become subtype=properName when True.
    collapse_proper_names: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # JSON-friendly: tuples → lists
        d["selected_document_ids"] = list(self.selected_document_ids)
        d["morph_columns"] = list(self.morph_columns)
        if self.svd_sweep_range is not None:
            d["svd_sweep_range"] = list(self.svd_sweep_range)
        d["excluded_fragments"] = {
            str(k): list(v) for k, v in (self.excluded_fragments or {}).items()
        }
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisConfig:
        sweep = data.get("svd_sweep_range")
        raw_excl = data.get("excluded_fragments") or {}
        excluded = {
            str(k): [str(f) for f in (v or [])]
            for k, v in raw_excl.items()
            if v
        }
        return cls(
            selected_document_ids=tuple(int(x) for x in data["selected_document_ids"]),
            feature_mode=str(data["feature_mode"]),
            morph_columns=tuple(str(c) for c in data["morph_columns"]),
            apply_proper_name_exception=bool(data["apply_proper_name_exception"]),
            rescale_mode=str(data["rescale_mode"]),
            svd_enabled=bool(data["svd_enabled"]),
            svd_mode=str(data["svd_mode"]),
            svd_n_components=int(data["svd_n_components"]),
            svd_sweep_range=(
                None
                if sweep is None
                else (int(sweep[0]), int(sweep[1]), int(sweep[2]))
            ),
            svd_normalize=bool(data["svd_normalize"]),
            svd_random_state=int(data["svd_random_state"]),
            svd_plateau_min=int(data["svd_plateau_min"]),
            linkage_method=str(data["linkage_method"]),
            distance_metric=str(data["distance_metric"]),
            cut_height=float(data["cut_height"]),
            excluded_fragments=excluded,
            collapse_proper_names=bool(data.get("collapse_proper_names", True)),
        )
