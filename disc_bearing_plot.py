#20.06.26 NZST
import numpy as np, pandas as pd, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

m = pd.read_csv("disc_threshold10_metrics.csv")
trees = sorted(m.tree.astype(str).unique())
cols = 4; rws = int(np.ceil(len(trees) / cols))
fig, axes = plt.subplots(rws, cols, figsize=(20 / 2.54, 5 * rws / 2.54), squeeze=False, sharex=True)
for ax, t in zip(axes.ravel(), trees):
    g = m[m.tree.astype(str) == t].sort_values("height_m")
    s = g.dropna(subset=["bearing_deg"])
    ax.plot(s.bearing_deg, s.height_m, "-", color="0.7", lw=0.6, zorder=1)
    ax.scatter(s.bearing_deg, s.height_m, s=np.clip(s.area_mm2, 3, 300), c=s.height_m,
               cmap="viridis", edgecolor="k", lw=0.3, zorder=2)
    ax.set_title(t, fontsize=8); ax.set_xlim(0, 360); ax.set_xticks([0, 90, 180, 270, 360])
    ax.tick_params(labelsize=6); ax.grid(alpha=0.3)
for ax in axes.ravel()[len(trees):]:
    ax.axis("off")
fig.supxlabel("damage arc bearing (deg, flip-corrected)", fontsize=8)
fig.supylabel("height (m)", fontsize=8)
fig.suptitle("Damage bearing vs height per tree (point size proportional to area_mm2)", fontsize=9)
fig.tight_layout()
fig.savefig("charts/bearing_vs_height.png", dpi=200); plt.close(fig)
