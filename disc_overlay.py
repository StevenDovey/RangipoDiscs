#19.06.26 NZST
import numpy as np, pandas as pd, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import binary_opening, binary_closing, label
from multiprocessing import Pool

UPLOADS = "images"
REF_FILE = "23717.tif"
MM_PER_PX = 0.25
THRESH = [10, 20, 30, 40, 50]
COL = {10: "red", 20: "orange", 30: "yellow", 40: "lime", 50: "cyan"}
WORKERS = 12

def load(f): return np.array(Image.open(os.path.join(UPLOADS, f)).convert("RGB")).astype(np.float32)

def geom(arr, px, py):
    R_, B_ = arr[:, :, 0], arr[:, :, 2]
    lab, n = label(binary_closing((R_ - B_) > 40, iterations=5))   # close the saw kerf
    near = lab[int(py) - 20:int(py) + 20, int(px) - 20:int(px) + 20]
    wood = lab == np.bincount(near[near > 0].ravel()).argmax()     # disc only, not tan background
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

def render(args):
    row, REF = args
    arr = load(row["file"]); px, py = row["pith_x"], row["pith_y"]
    Rr, interior, xx, yy, wood = geom(arr, px, py)
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
    yw, xw = np.where(wood); x0, x1, y0, y1 = xw.min(), xw.max(), yw.min(), yw.max()
    m = 0.05 * (x1 - x0)
    ax.set_xlim(x0 - m, x1 + m); ax.set_ylim(y1 + m, y0 - m)
    bx, by = x0, y1 + 0.6 * m
    ax.plot([bx, bx + 100 / MM_PER_PX], [by, by], color="white", lw=3)
    ax.text(bx, by - 0.15 * m, "100 mm", color="white", fontsize=8, va="bottom")
    ax.set_title(f"{row['tree']}  {row['height_m']} m  {row['file']}  flip={row['flip']} bad={row['bad']}")
    h = [plt.Line2D([], [], color=COL[T], lw=2 if T == 10 else 1, label=f"T{T}") for T in THRESH]
    ax.legend(handles=h, fontsize=7, loc="upper right")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(f"charts/overlay_{row['tree']}_{row['height_m']}_{row['file']}.png", dpi=200); plt.close(fig)

if __name__ == "__main__":
    man = pd.read_csv("disc_manifest.csv", dtype={"file": str})
    marks = pd.read_csv("disc_marks.csv")
    df = man.merge(marks, on="file")
    df = df[df["file"].apply(lambda f: os.path.exists(os.path.join(UPLOADS, f)))].sort_values(["tree", "height_m"])
    REF = build_ref(marks)
    os.makedirs("charts", exist_ok=True)
    rows = df[["tree", "height_m", "file", "bad", "flip", "pith_x", "pith_y"]].to_dict("records")
    with Pool(WORKERS) as p:
        p.map(render, [(r, REF) for r in rows])
