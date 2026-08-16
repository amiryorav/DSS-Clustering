"""Shared color palettes for identity and cluster colors."""

COLOR_PALETTE = (
    "#E53935",
    "#D81B60",
    "#8E24AA",
    "#5E35B1",
    "#3949AB",
    "#1E88E5",
    "#039BE5",
    "#00ACC1",
    "#00897B",
    "#43A047",
    "#7CB342",
    "#C0CA33",
    "#FDD835",
    "#FFB300",
    "#FB8C00",
    "#F4511E",
    "#6D4C41",
    "#757575",
    "#546E7A",
    "#212121",
)

# Cluster colors are read side by side, so neighbouring ids must not share a
# hue family. The identity palette above is a smooth Material ramp, which made
# consecutive clusters look nearly identical.
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
