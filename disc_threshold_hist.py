#19.06.26 NZST
import numpy as np, pandas as pd, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import binary_closing, label
from multiprocessing import Pool

UPLOADS = "images"
REF_FILE = "23717.tif"
BINS = np.arange(0, 200, 2)
WORKERS = 12

def load(f): return np.array(Image.open(os.path.join(UPLOADS, f)).convert("RGB")).astype(np.float32)

def geom(arr, px, py):
    R_, B_ = arr[:, :, 0], arr[:, :, 2]
    lab, n = label(binary_closing((R_ - B_) > 40, iterations=5))
    near = lab[int(py) - 20:int(py) + 20, int(px) - 20:int(px) + 20]
    wood = lab == np.bincount(near[near > 0].ravel()).argmax()
    Rr = (wood.sum() / np.pi) ** 0.5
    H, W = arr.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((yy - py) ** 2 + (xx - px) ** 2)
    return Rr, wood & (d < 0.95 * Rr), xx, yy, wood

def build_ref(marks):
    ref = load(REF_FILE); r = marks.loc[marks.file == REF_FILE].iloc[0]
    Rr0, i0, x0, _, _ = geom(ref, r.pith_x, r.pith_y)
    S0 = ref.max(2) - ref.min(2); L0 = ref.mean(2); seed0 = i0 & (x0 > r.pith_x + 0.08 * Rr0)
    sc = S0 - 0.6 * L0; sc[ref[:, :, 0] < ref[:, :, 1]] = -999
    return np.median(ref[seed0 & (sc > np.percentile(sc[seed0], 99))], 0)

def otsu(v):
    h, e = np.histogram(v, bins=221, range=(0, 442)); p = h / h.sum()
    w = np.cumsum(p); mu = np.cumsum(p * ((e[:-1] + e[1:]) / 2)); muT = mu[-1]
    sb = (muT * w - mu) ** 2 / (w * (1 - w) + 1e-12)
    return float((e[:-1] + e[1:])[np.nanargmax(sb)] / 2)

def disc_hist(args):
    row, REF = args
    arr = load(row["file"]); Rr, interior, xx, yy, wood = geom(arr, row["pith_x"], row["pith_y"])
    v = np.sqrt(((arr - REF) ** 2).sum(2))[interior]
    if v.size == 0:                                          # degenerate disc: bad pith / geom found no interior
        return row, np.nan, np.zeros(len(BINS) - 1, int)
    counts, _ = np.histogram(v, bins=BINS)
    return row, otsu(v), counts

if __name__ == "__main__":
    man = pd.read_csv("disc_manifest.csv", dtype={"file": str})
    marks = pd.read_csv("disc_marks.csv")
    df = man.merge(marks, on="file")
    df = df[df["file"].apply(lambda f: os.path.exists(os.path.join(UPLOADS, f)))].sort_values(["tree", "height_m"])
    REF = build_ref(marks)
    rows = df[["tree", "height_m", "file", "bad", "flip", "pith_x", "pith_y"]].to_dict("records")
    with Pool(WORKERS) as p:
        res = p.map(disc_hist, [(r, REF) for r in rows])

    os.makedirs("charts", exist_ok=True)
    out, by_tree = [], {}
    for row, ot, counts in res:
        out.append([row["tree"], row["height_m"], row["file"], row["bad"], round(ot, 1)])
        by_tree.setdefault(row["tree"], []).append((row, ot, counts))
    pd.DataFrame(out, columns=["tree", "height_m", "file", "bad", "otsu_dist"]).to_csv("disc_otsu_threshold.csv", index=False)

    ctr = (BINS[:-1] + BINS[1:]) / 2
    for tree, items in by_tree.items():
        items.sort(key=lambda t: t[0]["height_m"]); k = len(items); cols = 3; rws = int(np.ceil(k / cols))
        fig, axes = plt.subplots(rws, cols, figsize=(15 / 2.54, 4 * rws / 2.54), squeeze=False)
        for ax, (row, ot, counts) in zip(axes.ravel(), items):
            ax.bar(ctr, counts, width=2, color="0.6")
            ax.axvline(ot, color="green", lw=1.2); ax.axvline(10, color="k", ls="--", lw=0.6); ax.axvline(50, color="k", ls="--", lw=0.6)
            ax.set_yscale("log"); ax.set_title(f"{row['height_m']}m otsu={ot:.0f}", fontsize=6); ax.tick_params(labelsize=5)
        for ax in axes.ravel()[k:]:
            ax.axis("off")
        fig.suptitle(f"{tree} colour-distance histograms (green=Otsu, dashed=10/50)", fontsize=8)
        fig.tight_layout(); fig.savefig(f"charts/hist_{tree}.png", dpi=200); plt.close(fig)
