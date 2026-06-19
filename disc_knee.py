#19.06.26 NZST
import numpy as np, pandas as pd, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

area = pd.read_csv("disc_area_by_threshold.csv")
T = sorted(area.threshold.unique())

out = []
for f, g in area.groupby("file"):
    g = g.sort_values("threshold"); a = g.area_px.values.astype(float)
    r = (a[1:] + 1) / (a[:-1] + 1)                 # relative jump between successive thresholds
    knee = T[int(np.argmax(r))]                    # last threshold before the biggest escape into wood
    row = g.iloc[0]
    out.append([row.tree, row.height_m, f, row.bad, knee])
kdf = pd.DataFrame(out, columns=["tree", "height_m", "file", "bad", "knee_thresh"])
kdf.to_csv("disc_knee.csv", index=False)

os.makedirs("charts", exist_ok=True)
for tree, g in area.groupby("tree"):
    fig, ax = plt.subplots(figsize=(15 / 2.54, 10 / 2.54))
    for f, gg in g.groupby("file"):
        gg = gg.sort_values("threshold")
        ax.plot(gg.threshold, gg.area_px + 1, marker="o", ms=3, label=f"{gg.iloc[0].height_m}m")
    for k in kdf[kdf.tree == tree].knee_thresh:
        ax.axvline(k, color="0.8", lw=0.5)
    ax.set_yscale("log"); ax.set_xlabel("threshold"); ax.set_ylabel("area px (log)")
    ax.set_title(f"{tree} area vs threshold (vlines = per-disc knee)"); ax.legend(fontsize=6, ncol=2)
    fig.tight_layout(); fig.savefig(f"charts/knee_{tree}.png", dpi=200); plt.close(fig)
print(kdf.to_string(index=False))
