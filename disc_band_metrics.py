#18.06.26 NZST
import numpy as np, pandas as pd, os
from PIL import Image
from scipy.ndimage import binary_opening, binary_closing, label

UPLOADS = "/mnt/user-data/uploads"
MANIFEST = "/mnt/user-data/outputs/disc_manifest.csv"
MARKS = UPLOADS + "/disc_marks.csv"
MM_PER_PX = 0.25                       # 1 mm = 4.0 px on the FULLER rule
THRESHOLDS = list(range(10, 101, 10))
REF_FILE = "23717.tif"

man = pd.read_csv(MANIFEST, dtype={"file": str})
marks = pd.read_csv(MARKS)
df = man.merge(marks, on="file", how="inner")
df = df[df["file"].apply(lambda f: os.path.exists(os.path.join(UPLOADS, f)))].reset_index(drop=True)

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

t10, area = [], []
for _, row in df.iterrows():
    arr = load(row.file); px, py = row.pith_x, row.pith_y
    Rr, interior, xx, yy = geom(arr, px, py)
    seed = interior & (xx > px + 0.08 * Rr)
    dist = np.sqrt(((arr - REF) ** 2).sum(2))
    for T in THRESHOLDS:
        m = binary_opening((dist < T) & interior, iterations=2)
        lab, n = label(m); sub = lab[seed]; sub = sub[sub > 0]
        if len(sub) == 0:
            area.append([row.tree, row.height_m, row.file, row.bad, T, 0, 0.0, 0.0])
            if T == 10: t10.append([row.tree, row.height_m, row.file, row.bad,
                                    np.nan, np.nan, np.nan, np.nan, np.nan, 0, 0.0, 0.0])
            continue
        sel = binary_closing(lab == np.bincount(sub).argmax(), iterations=3) & interior
        apx = int(sel.sum()); frac = apx / interior.sum()
        area.append([row.tree, row.height_m, row.file, row.bad, T,
                     apx, round(apx * MM_PER_PX ** 2, 1), round(frac, 4)])
        if T == 10:
            ys, xs = np.where(sel); rr = np.hypot(xs - px, ys - py); th = np.arctan2(ys - py, xs - px)
            inner = np.percentile(rr, 2); outer = np.percentile(rr, 98)
            thc = np.arctan2(np.sin(th).mean(), np.cos(th).mean()); thr = np.angle(np.exp(1j * (th - thc)))
            dth = np.percentile(thr, 98) - np.percentile(thr, 2)
            bins = np.linspace(thr.min(), thr.max(), 31); bi = np.clip(np.digitize(thr, bins) - 1, 0, 29)
            thick = max((rr[bi == b].max() - rr[bi == b].min()) for b in range(30) if (bi == b).any())
            t10.append([row.tree, row.height_m, row.file, row.bad,
                        round(inner * MM_PER_PX, 1), round((Rr - outer) * MM_PER_PX, 1),
                        round(np.degrees(dth), 1), round(dth * rr.mean() * MM_PER_PX, 1),
                        round(thick * MM_PER_PX, 1), apx, round(apx * MM_PER_PX ** 2, 1), round(frac, 4)])

pd.DataFrame(t10, columns=["tree", "height_m", "file", "bad", "dist_pith_mm", "dist_edge_mm",
    "arc_deg", "arc_len_mm", "max_thick_mm", "area_px", "area_mm2", "area_frac"]
    ).to_csv("/mnt/user-data/outputs/disc_threshold10_metrics.csv", index=False)
pd.DataFrame(area, columns=["tree", "height_m", "file", "bad", "threshold", "area_px", "area_mm2", "area_frac"]
    ).to_csv("/mnt/user-data/outputs/disc_area_by_threshold.csv", index=False)
print("THRESHOLD 10, full geometry:")
print(pd.DataFrame(t10, columns=["tree","height_m","file","bad","dist_pith_mm","dist_edge_mm","arc_deg","arc_len_mm","max_thick_mm","area_px","area_mm2","area_frac"]).to_string(index=False))
print("\nAREA by threshold (px):")
print(pd.DataFrame(area, columns=["tree","height_m","file","bad","threshold","area_px","area_mm2","area_frac"]).pivot_table(index="height_m", columns="threshold", values="area_px").to_string())
