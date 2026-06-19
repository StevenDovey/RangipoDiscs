#19.06.26 NZST
# Self-calibrating variant of disc_band_metrics.py: the resin reference is
# re-centred to each disc's own sapwood (REF_disc = REF + localwood - globalwood),
# so a genotype's baseline wood colour does not bias detection. Thresholds and
# outputs match the absolute version for direct comparison.
import numpy as np, pandas as pd, os
from PIL import Image
from scipy.ndimage import binary_opening, binary_closing, label
from multiprocessing import Pool

UPLOADS = "images"
MANIFEST = "disc_manifest.csv"
MARKS = "disc_marks.csv"
MM_PER_PX = 0.25
THRESHOLDS = list(range(10, 101, 10))
REF_FILE = "23717.tif"
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
    REF = np.median(ref[seed0 & (sc > np.percentile(sc[seed0], 99))], 0)
    return REF, np.median(ref[i0], 0)

def disc_metrics(args):
    row, REF, globalwood = args
    arr = load(row["file"]); px, py = row["pith_x"], row["pith_y"]
    Rr, interior, xx, yy, wood = geom(arr, px, py)
    REF_disc = REF + (np.median(arr[interior], 0) - globalwood)      # re-centre to this disc's wood
    seed = interior & (xx > px + 0.08 * Rr)
    dist = np.sqrt(((arr - REF_disc) ** 2).sum(2))
    area_rows, t10_row = [], None
    for T in THRESHOLDS:
        m = binary_opening((dist < T) & interior, iterations=2)
        lab, n = label(m); sub = lab[seed]; sub = sub[sub > 0]
        if len(sub) == 0:
            area_rows.append([row["tree"], row["height_m"], row["file"], row["bad"], T, 0, 0.0, 0.0])
            if T == 10:
                t10_row = [row["tree"], row["height_m"], row["file"], row["bad"],
                           np.nan, np.nan, np.nan, np.nan, np.nan, 0, 0.0, 0.0,
                           np.nan, np.nan, np.nan]
            continue
        sel = binary_closing(lab == np.bincount(sub).argmax(), iterations=3) & interior
        apx = int(sel.sum()); frac = apx / interior.sum()
        area_rows.append([row["tree"], row["height_m"], row["file"], row["bad"], T,
                          apx, round(apx * MM_PER_PX ** 2, 1), round(frac, 4)])
        if T == 10:
            ys, xs = np.where(sel); rr = np.hypot(xs - px, ys - py); th = np.arctan2(ys - py, xs - px)
            inner = np.percentile(rr, 2); outer = np.percentile(rr, 98)
            thc = np.arctan2(np.sin(th).mean(), np.cos(th).mean()); thr = np.angle(np.exp(1j * (th - thc)))
            dth = np.percentile(thr, 98) - np.percentile(thr, 2)
            bins = np.linspace(thr.min(), thr.max(), 31); bi = np.clip(np.digitize(thr, bins) - 1, 0, 29)
            thick = max((rr[bi == b].max() - rr[bi == b].min()) for b in range(30) if (bi == b).any())
            wy, wx = np.where(wood); wr = np.hypot(wx - px, wy - py)
            wedge = np.abs(np.angle(np.exp(1j * (np.arctan2(wy - py, wx - px) - thc)))) < np.radians(15)
            edge_b = np.percentile(wr[wedge], 98)
            t10_row = [row["tree"], row["height_m"], row["file"], row["bad"],
                       round(inner * MM_PER_PX, 1), round((Rr - outer) * MM_PER_PX, 1),
                       round(np.degrees(dth), 1), round(dth * rr.mean() * MM_PER_PX, 1),
                       round(thick * MM_PER_PX, 1), apx, round(apx * MM_PER_PX ** 2, 1), round(frac, 4),
                       round(Rr * MM_PER_PX, 1), round(edge_b * MM_PER_PX, 1),
                       round((edge_b - outer) * MM_PER_PX, 1)]
    return area_rows, t10_row

if __name__ == "__main__":
    man = pd.read_csv(MANIFEST, dtype={"file": str})
    marks = pd.read_csv(MARKS)
    df = man.merge(marks, on="file", how="inner")
    df = df[df["file"].apply(lambda f: os.path.exists(os.path.join(UPLOADS, f)))].reset_index(drop=True)
    REF, globalwood = build_ref(marks)
    rows = df[["tree", "height_m", "file", "bad", "pith_x", "pith_y"]].to_dict("records")
    with Pool(WORKERS) as p:
        results = p.map(disc_metrics, [(r, REF, globalwood) for r in rows])
    area, t10 = [], []
    for ar, tr in results:
        area += ar
        if tr is not None: t10.append(tr)

    pd.DataFrame(t10, columns=["tree", "height_m", "file", "bad", "dist_pith_mm", "dist_edge_mm",
        "arc_deg", "arc_len_mm", "max_thick_mm", "area_px", "area_mm2", "area_frac",
        "r_area_mm", "r_bearing_mm", "dist_edge_bearing_mm"]
        ).to_csv("disc_threshold10_metrics_relative.csv", index=False)
    pd.DataFrame(area, columns=["tree", "height_m", "file", "bad", "threshold", "area_px", "area_mm2", "area_frac"]
        ).to_csv("disc_area_by_threshold_relative.csv", index=False)
    print(pd.DataFrame(t10, columns=["tree","height_m","file","bad","dist_pith_mm","dist_edge_mm","arc_deg","arc_len_mm","max_thick_mm","area_px","area_mm2","area_frac","r_area_mm","r_bearing_mm","dist_edge_bearing_mm"]).to_string(index=False))
