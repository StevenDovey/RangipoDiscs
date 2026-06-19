#19.06.26 NZST
import numpy as np, pandas as pd, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

THRESH = list(range(10, 101, 10))
METRICS = [("dist_pith_mm", "dist pith (mm)"), ("dist_edge_mm", "dist edge area (mm)"),
           ("arc_deg", "arc (deg)"), ("arc_len_mm", "arc length (mm)"),
           ("max_thick_mm", "max thickness (mm)"), ("area_mm2", "area t10 (mm2)"),
           ("r_area_mm", "radius area (mm)"), ("r_bearing_mm", "radius bearing (mm)"),
           ("dist_edge_bearing_mm", "dist edge bearing (mm)")]

area = pd.read_csv("disc_area_by_threshold.csv")
met = pd.read_csv("disc_threshold10_metrics.csv")

aw = area.pivot_table(index=["tree", "height_m", "file"], columns="threshold", values="area_mm2").reset_index()
aw = aw.rename(columns={T: f"area_t{T}_mm2" for T in THRESH})
wide = met.merge(aw, on=["tree", "height_m", "file"]).sort_values(["tree", "height_m"])
wide.to_csv("disc_wide.csv", index=False)

os.makedirs("charts", exist_ok=True)
for tree, g in wide.groupby("tree"):
    g = g.sort_values("height_m")

    fig, ax = plt.subplots(figsize=(15 / 2.54, 10 / 2.54))
    for T in THRESH:
        ax.plot(g["height_m"], g[f"area_t{T}_mm2"], marker="o", label=str(T))
    ax.set_xlabel("height (m)"); ax.set_ylabel("area (mm2)"); ax.set_title(f"{tree} area vs height")
    ax.legend(title="threshold", fontsize=6, ncol=2)
    fig.tight_layout(); fig.savefig(f"charts/{tree}_area.png", dpi=300); plt.close(fig)

    fig, axes = plt.subplots(3, 3, figsize=(15 / 2.54, 15 / 2.54))
    for ax, (c, lab) in zip(axes.ravel(), METRICS):
        ax.plot(g["height_m"], g[c], marker="o")
        ax.set_title(lab, fontsize=7); ax.set_xlabel("height (m)", fontsize=6); ax.tick_params(labelsize=6)
    fig.suptitle(f"{tree} metrics vs height", fontsize=9)
    fig.tight_layout(); fig.savefig(f"charts/{tree}_metrics.png", dpi=300); plt.close(fig)
