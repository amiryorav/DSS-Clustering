"""Book-picker palette spacing and plot color resolution."""

from __future__ import annotations

from dss_clustering.colors import COLOR_PALETTE, resolve_book_color


def _hex_rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _srgb_to_lin(channel: int) -> float:
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    r_lin, g_lin, b_lin = _srgb_to_lin(r), _srgb_to_lin(g), _srgb_to_lin(b)
    x = r_lin * 0.4124 + g_lin * 0.3576 + b_lin * 0.1805
    y = r_lin * 0.2126 + g_lin * 0.7152 + b_lin * 0.0722
    z = r_lin * 0.0193 + g_lin * 0.1192 + b_lin * 0.9505
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def _f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)

    fx, fy, fz = _f(x / xn), _f(y / yn), _f(z / zn)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _delta_e(a: str, b: str) -> float:
    lab_a = _rgb_to_lab(*_hex_rgb(a))
    lab_b = _rgb_to_lab(*_hex_rgb(b))
    return sum((x - y) ** 2 for x, y in zip(lab_a, lab_b)) ** 0.5


def test_custom_palette_colors_are_visually_distinct():
    distances = [
        _delta_e(COLOR_PALETTE[i], COLOR_PALETTE[j])
        for i in range(len(COLOR_PALETTE))
        for j in range(i + 1, len(COLOR_PALETTE))
    ]
    # The previous Material ramp had pairs around ΔE 12.
    assert min(distances) > 25
    assert len(COLOR_PALETTE) == 20
    assert len(set(COLOR_PALETTE)) == 20


def test_identity_mode_prefers_override_then_corpus_default():
    assert (
        resolve_book_color(corpus_default="#111111", identity_override="#222222")
        == "#222222"
    )
    assert resolve_book_color(corpus_default="#111111") == "#111111"


def test_cluster_mode_uses_cut_color_until_book_is_overridden():
    assert (
        resolve_book_color(
            corpus_default="#111111",
            identity_override="#222222",
            cluster_color="#333333",
            use_cluster=True,
        )
        == "#333333"
    )
    assert (
        resolve_book_color(
            corpus_default="#111111",
            identity_override="#222222",
            cluster_color="#333333",
            cluster_override="#444444",
            use_cluster=True,
        )
        == "#444444"
    )


def test_cluster_override_does_not_affect_identity_mode():
    assert (
        resolve_book_color(
            corpus_default="#111111",
            identity_override="#222222",
            cluster_color="#333333",
            cluster_override="#444444",
            use_cluster=False,
        )
        == "#222222"
    )


def test_point_series_applies_cluster_override_per_book():
    from types import SimpleNamespace

    import numpy as np

    from dss_clustering.states.plot_state import PlotState

    state = SimpleNamespace(hidden_document_ids=[])
    data = SimpleNamespace(
        document_books={"1": "A", "2": "B"},
        document_labels={"1": "Book A", "2": "Book B"},
        document_corpus={"1": "dss", "2": "dss"},
        document_color_override={"1": "#111111"},
        document_cluster_color_override={"1": "#ABCDEF"},
        corpus_default_color={"dss": "#4169E1"},
    )
    series = PlotState._point_series(
        state,
        np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]),
        [1, 2],
        data=data,
        cluster_of={"1": 1, "2": 1},
        cluster_color={"1": "#E31A1C"},
        use_cluster=True,
    )
    by_id = {row["id"]: row for row in series["book_rows"]}
    assert by_id[1]["color"] == "#ABCDEF"
    assert by_id[1]["has_override"] is True
    assert by_id[2]["color"] == "#E31A1C"
    assert by_id[2]["has_override"] is False
    assert series["colors"] == ["#ABCDEF", "#E31A1C"]


def test_clearing_overrides_restores_cluster_and_identity_defaults():
    from types import SimpleNamespace

    import numpy as np

    from dss_clustering.states.plot_state import PlotState

    state = SimpleNamespace(hidden_document_ids=[])
    data = SimpleNamespace(
        document_books={"1": "A", "2": "B"},
        document_labels={"1": "Book A", "2": "Book B"},
        document_corpus={"1": "dss", "2": "mikra"},
        document_color_override={},
        document_cluster_color_override={},
        corpus_default_color={"dss": "#4169E1", "mikra": "#228B22"},
    )
    cluster = PlotState._point_series(
        state,
        np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]),
        [1, 2],
        data=data,
        cluster_of={"1": 1, "2": 2},
        cluster_color={"1": "#E31A1C", "2": "#1F78B4"},
        use_cluster=True,
    )
    identity = PlotState._point_series(
        state,
        np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]),
        [1, 2],
        data=data,
        cluster_of={"1": 1, "2": 2},
        cluster_color={"1": "#E31A1C", "2": "#1F78B4"},
        use_cluster=False,
    )
    assert [row["color"] for row in cluster["book_rows"]] == ["#E31A1C", "#1F78B4"]
    assert all(row["has_override"] is False for row in cluster["book_rows"])
    assert [row["color"] for row in identity["book_rows"]] == ["#4169E1", "#228B22"]
    assert all(row["has_override"] is False for row in identity["book_rows"])
