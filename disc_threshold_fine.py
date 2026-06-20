#20.06.26 NZST
# Fine threshold sweep around the eyeballed T10 to test severity stability.
# If area is flat across T5-T15 the choice is robust; if steep, pick the plateau.
import numpy as np, pandas as pd, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import binary_opening, binary_closing, label
from multiprocessing import Pool

UPLOADS = "images"
REF_FILE = "23717.tif"
MM_PER_PX = 0.25
FINE = [5, 7, 9, 10, 11, 13, 15]
WORKERS = 12

def load(f): return np.array(Image.open(os.path.join(UPLOADS, f)).convert("RGB")).astype(np.float32)

def geom(arr, px, py):
    R_, B_ = arr[:, :, 0], arr[:, :, 2]
    lab, n = label(binary_closing((R_ - B_) > 40, iterations=5))
    near = lab[int(py) - 20:int(py) + 20, int(px) - 20:int(px) + 20].ravel(); near = near[near > 0]
    disc = np.bincount(near).argmax() if near.size else np.bincount(lab[lab > 0].ravel()).argmax()
    wood = lab == disc
    Rr = (wood.sum() / np.pi) ** 0.5
    H, W = arr.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((yy - py) ** 2 + (xx - px) ** 2)
    return wood & (d < 0.95 * Rr)

def build_ref(marks):
    ref = load(REF_FILE); r = marks.loc[marks.file == REF_FILE].iloc[0]
    R_, B_ = ref[:, :, 0], ref[:, :, 2]
    lab, n = label(binary_closing((R_ - B_) > 40, iterations=5))
    near = lab[int(r.pith_y) - 20:int(r.pith_y) + 20, int(r.pith_x) - 20:int(r.pith_x) + 20].ravel(); near = near[near > 0]
    wood = lab == np.bincount(near).argmax()
    Rr = (wood.sum() / np.pi) ** 0.5
    H, W = ref.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
    i0 = wood & (np.sqrt((yy - r.pith_y) ** 2 + (xx - r.pith_x) ** 2) < 0.95 * Rr)
    S0 = ref.max(2) - ref.min(2); L0 = ref.mean(2); seed0 = i0 & (xx > r.pith_x + 0.08 * Rr)
    sc = S0 - 0.6 * L0; sc[ref[:, :, 0] < ref[:, :, 1]] = -999
    return np.median(ref[seed0 & (sc > np.percentile(sc[seed0], 99))], 0)

def sweep(args):
    row, REF = args
    arr = load(row["file"]); interior = geom(arr, row["pith_x"], row["pith_y"])
    dist = np.sqrt(((arr - REF) ** 2).sum(2))
    out = []
    for T in FINE:
        m = binary_opening((dist < T) & interior, iterations=2)
        lab, n = label(m); sub = lab[interior]; sub = sub[sub > 0]
        a = 0 if len(sub) == 0 else int((binary_closing(lab == np.bincount(sub).argmax(), iterations=3) & interior).sum())
        out.append([row["tree"], row["height_m"], row["file"], row["bad"], T, round(a * MM_PER_PX ** 2, 1)])
    return out

if __name__ == "__main__":
    man = pd.read_csv("disc_manifest.csv", dtype={"file": str})
    marks = pd.read_csv("disc_marks.csv")
    branch = marks[["file", "branch"]]
    df = man.merge(marks, on="file")
    df = df[df["file"].apply(lambda f: os.path.exists(os.path.join(UPLOADS, f)))]
    REF = build_ref(marks)
    rows = df[["tree", "height_m", "file", "bad", "pith_x", "pith_y"]].to_dict("records")
    with Pool(WORKERS) as p:
        res = p.map(sweep, [(r, REF) for r in rows])
    flat = [r for sub in res for r in sub]
    fine = pd.DataFrame(flat, columns=["tree", "height_m", "file", "bad", "threshold", "area_mm2"]).merge(branch, on="file")
    fine.loc[(fine.bad == 1) | (fine.branch == 1), "area_mm2"] = 0.0
    fine.to_csv("disc_area_fine.csv", index=False)

    # stability: how much peak-disc severity moves across T5-T15, relative to T10
    rows2 = []
    for tree, g in fine.groupby("tree"):
        p10 = g[g.threshold == 10].area_mm2.max()
        p5 = g[g.threshold == 5].area_mm2.max(); p15 = g[g.threshold == 15].area_mm2.max()
        rows2.append([tree, round(p5, 1), round(p10, 1), round(p15, 1),
                      round((p15 - p5) / p10, 2) if p10 > 0 else np.nan])
    pd.DataFrame(rows2, columns=["tree", "peak_T5", "peak_T10", "peak_T15", "rel_span_T5_15"]).to_csv("disc_threshold_stability.csv", index=False)

    os.makedirs("charts", exist_ok=True)
    trees = sorted(fine.tree.astype(str).unique()); cols = 4; rws = int(np.ceil(len(trees) / cols))
    fig, axes = plt.subplots(rws, cols, figsize=(20 / 2.54, 5 * rws / 2.54), squeeze=False, sharex=True)
    for ax, t in zip(axes.ravel(), trees):
        for f, gg in fine[fine.tree.astype(str) == t].groupby("file"):
            gg = gg.sort_values("threshold")
            ax.plot(gg.threshold, gg.area_mm2, marker="o", ms=2, lw=0.7)
        ax.axvline(10, color="k", ls="--", lw=0.6); ax.set_title(t, fontsize=8); ax.tick_params(labelsize=6)
    for ax in axes.ravel()[len(trees):]:
        ax.axis("off")
    fig.supxlabel("threshold (fine)", fontsize=8); fig.supylabel("area mm2", fontsize=8)
    fig.suptitle("Severity vs fine threshold T5-T15 (dashed = T10)", fontsize=9)
    fig.tight_layout(); fig.savefig("charts/threshold_fine.png", dpi=200); plt.close(fig)
