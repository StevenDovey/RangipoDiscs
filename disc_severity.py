#20.06.26 NZST
# Locked severity = stain area at threshold 10 (the dark stain core): escape-free,
# avoids base heartwood, and peaks at the physically-expected mid-stem height.
# Integration over the band was rejected (it drags in threshold escape and basal
# heartwood). Per-disc severity is zeroed for bad / branch discs. Builds a
# regression-ready per-tree table keyed by plot/treeno.
import numpy as np, pandas as pd

area = pd.read_csv("disc_area_by_threshold.csv")
man = pd.read_csv("disc_manifest.csv", dtype={"file": str})[["file", "plot", "treeno"]]
branch = pd.read_csv("disc_marks.csv")[["file", "branch"]]

d = area[area.threshold == 10][["tree", "height_m", "file", "bad", "area_mm2"]].rename(columns={"area_mm2": "sev_mm2"})
d = d.merge(branch, on="file")
d.loc[(d.bad == 1) | (d.branch == 1), "sev_mm2"] = 0.0
d.to_csv("disc_severity_by_disc.csv", index=False)

rows = []
for tree, g in d.merge(man, on="file").groupby("tree"):
    g = g.sort_values("height_m"); s = g.sev_mm2.values; h = g.height_m.values
    rows.append([tree, g["plot"].iloc[0], g["treeno"].iloc[0], len(g), h.min(), h.max(),
                 round(s.max(), 1), round(float(h[s.argmax()]), 2), round(float(np.trapezoid(s, h)), 1)])
pd.DataFrame(rows, columns=["tree", "plot", "treeno", "n_disc", "h_min", "h_max",
    "peak_sev_mm2", "peak_height_m", "stem_integral_mm2m"]
    ).to_csv("disc_tree_severity.csv", index=False)
