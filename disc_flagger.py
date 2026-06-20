#19.06.26 NZST
# Interactive disc flagger: step through discs and toggle flip / bad / branch,
# saving to disc_marks.csv. Run locally (needs a GUI backend), not headless.
#   keys:  f=flip   b=bad   r=branch   left/right=prev/next   s=save   q=quit
# flip is shown applied so you can confirm the 180 rotation.
import numpy as np, pandas as pd, os
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import binary_opening, binary_closing, label

UPLOADS = "images"
REF_FILE = "23717.tif"
THRESH = [10, 20, 30, 40, 50]
COL = {10: "red", 20: "orange", 30: "yellow", 40: "lime", 50: "cyan"}

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
    return Rr, wood & (d < 0.95 * Rr), wood, xx

def build_ref(marks):
    ref = load(REF_FILE); r = marks.loc[marks.file == REF_FILE].iloc[0]
    Rr0, i0, _, x0 = geom(ref, r.pith_x, r.pith_y)
    S0 = ref.max(2) - ref.min(2); L0 = ref.mean(2); seed0 = i0 & (x0 > r.pith_x + 0.08 * Rr0)
    sc = S0 - 0.6 * L0; sc[ref[:, :, 0] < ref[:, :, 1]] = -999
    return np.median(ref[seed0 & (sc > np.percentile(sc[seed0], 99))], 0)

man = pd.read_csv("disc_manifest.csv", dtype={"file": str})
marks = pd.read_csv("disc_marks.csv")
if "branch" not in marks:
    marks["branch"] = 0
REF = build_ref(marks)
files = [f for f in man.file if os.path.exists(os.path.join(UPLOADS, f))]
state = {"i": 0, "cache": None}

def compute(f):
    arr = load(f); r = marks.loc[marks.file == f].iloc[0]
    Rr, interior, wood, xx = geom(arr, r.pith_x, r.pith_y)
    dist = np.sqrt(((arr - REF) ** 2).sum(2))
    masks = [(T, binary_closing(binary_opening((dist < T) & interior, iterations=2), iterations=3) & interior) for T in THRESH]
    yw, xw = np.where(wood)
    return {"f": f, "arr": arr.astype(np.uint8), "px": r.pith_x, "py": r.pith_y, "masks": masks,
            "bbox": (xw.min(), xw.max(), yw.min(), yw.max())}

fig, ax = plt.subplots(figsize=(9, 9))

def draw():
    f = files[state["i"]]
    if state["cache"] is None or state["cache"]["f"] != f:
        state["cache"] = compute(f)
    c = state["cache"]; r = marks.loc[marks.file == f].iloc[0]; flip = int(r.flip)
    arr, px, py, masks = c["arr"], c["px"], c["py"], c["masks"]; x0, x1, y0, y1 = c["bbox"]
    H, W = arr.shape[:2]
    if flip:
        arr = arr[::-1, ::-1]; px = W - 1 - px; py = H - 1 - py
        masks = [(T, m[::-1, ::-1]) for T, m in masks]
        x0, x1, y0, y1 = W - 1 - x1, W - 1 - x0, H - 1 - y1, H - 1 - y0
    ax.clear(); ax.imshow(arr)
    for T, m in masks:
        ax.contour(m.astype(float), levels=[0.5], colors=[COL[T]], linewidths=2 if T == 10 else 1)
    ax.plot(px, py, "w+", ms=12, mew=2)
    mg = 0.05 * (x1 - x0); ax.set_xlim(x0 - mg, x1 + mg); ax.set_ylim(y1 + mg, y0 - mg)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"[{state['i']+1}/{len(files)}] {f}  flip={flip} bad={int(r.bad)} branch={int(r.branch)}\n"
                 "f=flip  b=bad  r=branch   < >=nav   s=save   q=quit", fontsize=9)
    fig.canvas.draw_idle()

def toggle(col):
    i = marks.index[marks.file == files[state["i"]]][0]
    marks.at[i, col] = 1 - int(marks.at[i, col]); draw()

def on_key(e):
    if e.key in ("right", "down", "n", " "):
        state["i"] = (state["i"] + 1) % len(files); draw()
    elif e.key in ("left", "up", "p"):
        state["i"] = (state["i"] - 1) % len(files); draw()
    elif e.key == "f": toggle("flip")
    elif e.key == "b": toggle("bad")
    elif e.key == "r": toggle("branch")
    elif e.key == "s": marks.to_csv("disc_marks.csv", index=False); print("saved disc_marks.csv")
    elif e.key == "q": plt.close(fig)

fig.canvas.mpl_connect("key_press_event", on_key)
draw(); plt.show()
