#19.06.26 NZST
import numpy as np, pandas as pd, os, gc
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import binary_opening, binary_closing, label

UPLOADS = "images"
REF_FILE = "23717.tif"
THRESH = [10, 20, 30, 40, 50]
COL = {10: "red", 20: "orange", 30: "yellow", 40: "lime", 50: "cyan"}

man = pd.read_csv("disc_manifest.csv", dtype={"file": str})
marks = pd.read_csv("disc_marks.csv")
df = man.merge(marks, on="file")
df = df[df["file"].apply(lambda f: os.path.exists(os.path.join(UPLOADS, f)))].sort_values(["tree", "height_m"])

def load(f): return np.array(Image.open(os.path.join(UPLOADS, f)).convert("RGB")).astype(np.float32)

def geom(arr, px, py):
    R_, B_ = arr[:, :, 0], arr[:, :, 2]; wood = (R_ - B_) > 40
    Rr = (wood.sum() / np.pi) ** 0.5
    H, W = arr.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((yy - py) ** 2 + (xx - px) ** 2)
    return Rr, wood & (d < 0.95 * Rr), xx, yy

ref = load(REF_FILE); r = marks.loc[marks.file == REF_FILE].iloc[0]
Rr0, i0, x0, _ = geom(ref, r.pith_x, r.pith_y)
S0 = ref.max(2) - ref.min(2); L0 = ref.mean(2); seed0 = i0 & (x0 > r.pith_x + 0.08 * Rr0)
sc = S0 - 0.6 * L0; sc[ref[:, :, 0] < ref[:, :, 1]] = -999
REF = np.median(ref[seed0 & (sc > np.percentile(sc[seed0], 99))], 0)

os.makedirs("charts", exist_ok=True)
for _, row in df.iterrows():
    arr = load(row.file); px, py = row.pith_x, row.pith_y
    Rr, interior, xx, yy = geom(arr, px, py)
    seed = interior & (xx > px + 0.08 * Rr)
    dist = np.sqrt(((arr - REF) ** 2).sum(2))

    fig, ax = plt.subplots(figsize=(15 / 2.54, 15 / 2.54))
    ax.imshow(arr.astype(np.uint8))
    for T in THRESH:
        m = binary_opening((dist < T) & interior, iterations=2)
        lab, n = label(m); sub = lab[seed]; sub = sub[sub > 0]
        if len(sub) == 0:
            continue
        sel = binary_closing(lab == np.bincount(sub).argmax(), iterations=3) & interior
        ax.contour(sel.astype(float), levels=[0.5], colors=[COL[T]], linewidths=2.0 if T == 10 else 1.0)
    ax.plot(px, py, "w+", ms=10, mew=2)
    rr = 1.15 * Rr
    ax.set_xlim(px - rr, px + rr); ax.set_ylim(py + rr, py - rr)
    ax.set_title(f"{row.tree}  {row.height_m} m  {row.file}  flip={row.flip} bad={row.bad}")
    h = [plt.Line2D([], [], color=COL[T], lw=2 if T == 10 else 1, label=f"T{T}") for T in THRESH]
    ax.legend(handles=h, fontsize=7, loc="upper right")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(f"charts/overlay_{row.tree}_{row.height_m}_{row.file}.png", dpi=200); plt.close(fig)
    del arr, dist, interior, xx, yy, seed; gc.collect()
