# phase6-batch1 / fingerprint.py
# 复用 analysis/_fingerprint.py 的 features()，对 40 张新页跑结构指纹：
#   类间可分（跨主题骨架相关）/ 类内成族（同主题跨页相关）/ 主轴方向 / 墨水重心。
# 并与 28 张旧样张口径对照。生成灰度 240×135 盲测缩略图。
import glob, json, os, sys
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
from _fingerprint import features, corr  # noqa: E402

DIR = os.path.join(ROOT, "docs", "progress", "phase6-batch1")
PNGDIR = os.path.join(DIR, "png")
BLINDDIR = os.path.join(DIR, "blind")
os.makedirs(BLINDDIR, exist_ok=True)

paths = sorted(glob.glob(os.path.join(PNGDIR, "*.png")))
fs = [features(p) for p in paths]
# 文件名 e6-cover.png / e6-stress-d2.png → 主题 id
def theme_of(p):
    return os.path.basename(p).split("-")[0]

labels = [os.path.basename(p) for p in paths]
n = len(fs)
M = np.zeros((n, n), dtype=np.float32)
for i in range(n):
    for j in range(n):
        M[i, j] = corr(fs[i]["s"], fs[j]["s"])

# 类间（跨主题）与类内（同主题）——只在基线 24 页上测（压力页是内容形态测试，不参与类间可分）
base_idx = [i for i in range(n) if "-stress-" not in labels[i]]
cross, within = [], []
for a, i in enumerate(base_idx):
    for j in base_idx[a + 1:]:
        if theme_of(paths[i]) != theme_of(paths[j]):
            cross.append(float(M[i, j]))
        else:
            within.append(float(M[i, j]))
cross = np.array(cross) if cross else np.array([0.0])
within = np.array(within) if within else np.array([0.0])

# 每主题的类内相关（跨页）
per_theme_within = {}
for tid in ["e6", "g2", "e7", "f1"]:
    idx = [i for i in range(n) if theme_of(paths[i]) == tid and "-stress-" not in labels[i]]
    vals = [float(M[i][j]) for a, i in enumerate(idx) for j in idx[a + 1:]]
    per_theme_within[tid] = {"count": len(vals), "mean": round(float(np.mean(vals)), 3),
                             "min": round(float(np.min(vals)), 3), "max": round(float(np.max(vals)), 3)} if vals else {}

edge = {}
for i, f in enumerate(fs):
    edge.setdefault(f["edge_struct_dominant"], []).append(labels[i])

cxs = [f["cx"] for f in fs]; cys = [f["cy"] for f in fs]
result = {
    "n": n,
    "cross_theme_skeleton_corr": {
        "mean": round(float(cross.mean()), 4),
        "max": round(float(cross.max()), 4),
        "pct_above_080": round(float((cross > 0.8).mean()), 4),
    },
    "within_theme_skeleton_corr": {
        "mean": round(float(within.mean()), 4),
        "min": round(float(within.min()), 4),
        "max": round(float(within.max()), 4),
    },
    "per_theme_within": per_theme_within,
    "edge_struct_dominant": {k: sorted(v) for k, v in edge.items()},
    "centroid": {"cx_mean": round(float(np.mean(cxs)), 4), "cx_std": round(float(np.std(cxs)), 4),
                 "cy_mean": round(float(np.mean(cys)), 4), "cy_std": round(float(np.std(cys)), 4)},
}
# 旧 28 张对照
old = json.load(open(os.path.join(ROOT, "analysis", "_fingerprint.json"), encoding="utf-8"))
result["baseline_28"] = {
    "skeleton_corr_mean": old["skeleton_corr"]["mean"],
    "skeleton_corr_pct_above_080": old["skeleton_corr"]["pct_above_080"],
    "edge_struct_dominant_counts": old["edge_struct_dominant_counts"],
}

# 盲测缩略（灰度 240×135）
blind_meta = []
for p in paths:
    im = Image.open(p).convert("L").resize((240, 135), Image.Resampling.LANCZOS)
    name = os.path.basename(p).replace(".png", ".thumb.png")
    im.save(os.path.join(BLINDDIR, name))
    blind_meta.append({"thumb": name, "id": os.path.basename(p).replace(".png", "")})

json.dump(result, open(os.path.join(DIR, "fingerprint.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(blind_meta, open(os.path.join(DIR, "blind-meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print("CROSS_THEME", json.dumps(result["cross_theme_skeleton_corr"]))
print("WITHIN_THEME", json.dumps(result["within_theme_skeleton_corr"]))
print("PER_THEME", json.dumps(result["per_theme_within"], ensure_ascii=False))
print("EDGE", json.dumps(result["edge_struct_dominant"], ensure_ascii=False))
print("CENTROID", json.dumps(result["centroid"]))
print("BASELINE_28", json.dumps(result["baseline_28"]))
