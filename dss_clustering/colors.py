"""Shared color palettes and point-color resolution."""

# Book-picker swatches. Neighbouring hues are spaced so adjacent chips and
# nearby plot points stay distinguishable (the old Material ramp was not).
COLOR_PALETTE = (
    "#D62728",  # red
    "#1414F5",  # royal blue
    "#1BBB1B",  # green
    "#29A9E0",  # sky
    "#E755CA",  # magenta
    "#CEA609",  # gold
    "#252E7E",  # indigo
    "#257E52",  # forest
    "#7E5225",  # brown
    "#8F1445",  # wine
    "#8155E7",  # violet
    "#DF14F5",  # fuchsia
    "#1485F5",  # azure
    "#6A8F14",  # olive
    "#F78C45",  # orange
    "#F5146E",  # rose
    "#1BBBBB",  # teal
    "#255B7E",  # steel
    "#D37369",  # salmon
    "#D3A969",  # tan
)

# Cluster colors are read side by side, so neighbouring ids must not share a
# hue family.
CLUSTER_PALETTE = (
    "#1F77B4",  # blue
    "#E31A1C",  # red
    "#33A02C",  # green
    "#FF7F00",  # orange
    "#6A3D9A",  # purple
    "#00CED1",  # turquoise
    "#B15928",  # brown
    "#F781BF",  # pink
    "#A6CEE3",  # light blue
    "#FDBF6F",  # light orange
    "#B2DF8A",  # light green
    "#CAB2D6",  # light purple
    "#8C564B",  # clay
    "#17BECF",  # cyan
    "#BCBD22",  # olive
    "#7F7F7F",  # gray
    "#FF9896",  # salmon
    "#9467BD",  # violet
    "#2CA02C",  # forest
    "#D62728",  # brick
)


def resolve_book_color(
    *,
    corpus_default: str,
    identity_override: str | None = None,
    cluster_color: str | None = None,
    cluster_override: str | None = None,
    use_cluster: bool = False,
) -> str:
    """Color for one book on the 3D plot.

    Identity mode uses a per-book override, else the corpus default.
    Cluster mode uses the dendrogram cut, then a per-book override on top.
    """
    if use_cluster:
        if cluster_override:
            return cluster_override
        if cluster_color:
            return cluster_color
    return identity_override or corpus_default
