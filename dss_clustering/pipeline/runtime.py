"""Process-local storage for analysis matrices (not synced to the browser)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from dss_clustering.pipeline.matrix import rescale_matrix


@dataclass
class MatrixBundle:
    """Count matrix plus metadata for one Vectorize run."""

    count_matrix: sp.csr_matrix
    document_ids: list[int]
    signatures: list[str]
    n_source_rows: int
    fingerprint: str
    feature_mode: str
    active_columns: tuple[str, ...]
    ignore_proper_names: bool
    _rescaled: dict[str, sp.csr_matrix] = field(default_factory=dict, repr=False)

    @property
    def n_documents(self) -> int:
        return int(self.count_matrix.shape[0])

    @property
    def n_signatures(self) -> int:
        return int(self.count_matrix.shape[1])

    @property
    def n_nnz(self) -> int:
        return int(self.count_matrix.nnz)

    def rescaled(self, mode: str) -> sp.csr_matrix:
        if mode not in self._rescaled:
            self._rescaled[mode] = rescale_matrix(self.count_matrix, mode)
        return self._rescaled[mode]


@dataclass
class EmbeddingBundle:
    """Analysis-space embedding produced by the SVD step."""

    embedding: np.ndarray
    document_ids: list[int]
    n_components_used: int
    variance_explained: float
    svd_enabled: bool
    rescale_mode: str
    fingerprint: str


@dataclass
class DendrogramBundle:
    """Server-side linkage tree for the dendrogram step."""

    Z: np.ndarray
    document_ids: list[int]
    linkage_method: str
    distance_metric: str
    fingerprint: str


@dataclass
class VizEmbeddingBundle:
    """Visualization-only 2D/3D coords (UMAP / t-SNE); never feeds clustering."""

    coords: np.ndarray  # shape (n, 2) or (n, 3)
    document_ids: list[int]
    method: str
    params_key: str
    fingerprint: str


_BUNDLES: dict[str, MatrixBundle] = {}
_EMBEDDINGS: dict[str, EmbeddingBundle] = {}
_DENDROGRAMS: dict[str, DendrogramBundle] = {}
_VIZ: dict[str, VizEmbeddingBundle] = {}


def put_bundle(token: str, bundle: MatrixBundle) -> None:
    _BUNDLES[token] = bundle
    # A new count matrix invalidates analysis + viz caches for this session.
    _EMBEDDINGS.pop(token, None)
    _DENDROGRAMS.pop(token, None)
    _VIZ.pop(token, None)


def get_bundle(token: str) -> MatrixBundle | None:
    return _BUNDLES.get(token)


def clear_bundle(token: str) -> None:
    _BUNDLES.pop(token, None)
    _EMBEDDINGS.pop(token, None)
    _DENDROGRAMS.pop(token, None)
    _VIZ.pop(token, None)


def put_embedding(token: str, bundle: EmbeddingBundle) -> None:
    _EMBEDDINGS[token] = bundle
    # New analysis embedding invalidates the dendrogram tree.
    _DENDROGRAMS.pop(token, None)


def get_embedding(token: str) -> EmbeddingBundle | None:
    return _EMBEDDINGS.get(token)


def clear_embedding(token: str) -> None:
    _EMBEDDINGS.pop(token, None)
    _DENDROGRAMS.pop(token, None)


def put_dendrogram(token: str, bundle: DendrogramBundle) -> None:
    _DENDROGRAMS[token] = bundle


def get_dendrogram(token: str) -> DendrogramBundle | None:
    return _DENDROGRAMS.get(token)


def clear_dendrogram(token: str) -> None:
    _DENDROGRAMS.pop(token, None)


def put_viz(token: str, bundle: VizEmbeddingBundle) -> None:
    _VIZ[token] = bundle


def get_viz(token: str) -> VizEmbeddingBundle | None:
    return _VIZ.get(token)


def clear_viz(token: str) -> None:
    _VIZ.pop(token, None)
