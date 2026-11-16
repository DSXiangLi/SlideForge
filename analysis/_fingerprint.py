"""低频结构指纹：把幻灯片去掉颜色，只看墨水分布形状。

用途：验证「30 个主题 = 同一副骨架的 30 张皮」。
指标：
  - z-vector: 32x18 灰度下采样后 z-score 化的结构向量
  - pairwise corr: 两两余弦相似度（= 去亮度后的结构相关性）
  - centroid: 墨水质量重心（归一化）
  - edge: Sobel 近似梯度主方向（横 / 纵 / 45 / 135）
  - dark_ratio, accent-free contrast
并输出所有样张灰度叠加的「平均脸」。
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # 仓库根，随机器迁移
SAMPLE = os.path.join(ROOT, "assets", "theme-sampler")
ANALYSIS = os.path.join(ROOT, "analysis")

W, H = 320, 180
VW, VH = 32, 18


def features(path):
    im = Image.open(path).convert("L")
    orig = im.size
    a = np.asarray(im.resize((W, H), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    # 极性归一：暗底页反相，让「墨水=内容」方向一致，否则亮/暗主题的结构相关会假性变负
    polarity = "dark" if float((a < 0.35).mean()) > 0.5 else "light"
    if polarity == "dark":
        a = 1.0 - a
    ink = 1.0 - a

    # 墨水重心（扣除背景亮度基线，避免整页暗底主导）
    base = np.percentile(ink, 12)
    rel = np.clip(ink - base, 0, None)
    ys, xs = np.mgrid[0:H, 0:W]
    tot = float(rel.sum()) + 1e-6
    cx = float((rel * xs).sum() / tot / W)
    cy = float((rel * ys).sum() / tot / H)

    # 梯度主方向（按梯度幅值加权，四方向占比）
    gy, gx = np.gradient(a)
    ang = (np.degrees(np.arctan2(gy, gx)) + 180.0) % 180.0
    mag = np.hypot(gx, gy)
    d0 = np.minimum(ang, 180.0 - ang)                 # 距 0°(水平线)
    d90 = np.abs(ang - 90.0)                          # 距 90°(垂直线)
    d45 = np.abs(ang - 45.0)
    d135 = np.abs(ang - 135.0)
    weights = np.array([
        float(mag[d0 < 22.5].sum()),
        float(mag[d45 < 22.5].sum()),
        float(mag[d90 < 22.5].sum()),
        float(mag[d135 < 22.5].sum()),
    ])
    weights = weights / (weights.sum() + 1e-6)
    # 梯度方向垂直于边缘：ang≈0 是竖直边缘，ang≈90 是水平边缘
    labels = ["vertical", "diag135", "horizontal", "diag45"]

    # 结构层边缘：强模糊抹掉文字笔画，只留大面积色块/结构件的边界方向
    ab = np.asarray(
        Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)),
        dtype=np.float32,
    ) / 255.0
    gyb, gxb = np.gradient(ab)
    angb = (np.degrees(np.arctan2(gyb, gxb)) + 180.0) % 180.0
    magb = np.hypot(gxb, gyb)
    wb = np.array([
        float(magb[np.minimum(angb, 180.0 - angb) < 22.5].sum()),
        float(magb[np.abs(angb - 45.0) < 22.5].sum()),
        float(magb[np.abs(angb - 90.0) < 22.5].sum()),
        float(magb[np.abs(angb - 135.0) < 22.5].sum()),
    ])
    wb = wb / (wb.sum() + 1e-6)

    # 皮肤层 v：32x18 精细结构（保留文字笔画、装饰、纹理），z-score 去掉底色差
    v = np.asarray(
        Image.fromarray((a * 255).astype(np.uint8)).resize((VW, VH), Image.Resampling.BOX),
        dtype=np.float32,
    ).ravel()
    v = (v - v.mean()) / (v.std() + 1e-6)

    # 骨架层 s：强模糊抹掉笔画后再降到 10x6 块密度，只留「哪里重、哪里空」
    blurred = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=10))
    s = np.asarray(blurred.resize((10, 6), Image.Resampling.BOX), dtype=np.float32).ravel()
    s = (s - s.mean()) / (s.std() + 1e-6)

    return {
        "file": os.path.basename(path),
        "orig": list(orig),
        "polarity": polarity,
        "cx": round(cx, 4),
        "cy": round(cy, 4),
        "dark_ratio": round(float((a < 0.35).mean()), 4),
        "edge": {labels[i]: round(float(weights[i]), 4) for i in range(4)},
        "edge_dominant": labels[int(weights.argmax())],
        "edge_anisotropy": round(float(weights.max()), 4),
        "edge_struct": {labels[i]: round(float(wb[i]), 4) for i in range(4)},
        "edge_struct_dominant": labels[int(wb.argmax())],
        "edge_struct_anisotropy": round(float(wb.max()), 4),
        "v": v,
        "s": s,
        "gray": a,
    }


def corr(x, y):
    return float(np.dot(x, y) / (len(x)))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "sampler"
    if mode == "sampler":
        paths = sorted(glob.glob(os.path.join(SAMPLE, "*.png")))
        out_json = os.path.join(ANALYSIS, "_fingerprint.json")
    else:
        paths = sorted(glob.glob(os.path.join(ANALYSIS, "DNA-0*.png")))
        out_json = os.path.join(ANALYSIS, "_fingerprint-demo.json")

    fs = [features(p) for p in paths]
    n = len(fs)
    mat = np.zeros((n, n), dtype=np.float32)
    mat_s = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        for j in range(n):
            mat[i, j] = corr(fs[i]["v"], fs[j]["v"])
            mat_s[i, j] = corr(fs[i]["s"], fs[j]["s"])
    off = mat[~np.eye(n, dtype=bool)]
    off_s = mat_s[~np.eye(n, dtype=bool)]

    # 平均脸：所有灰度图等权叠加
    avg = np.mean(np.stack([f["gray"] for f in fs]), axis=0)
    face = Image.fromarray(np.clip(avg * 255, 0, 255).astype(np.uint8)).resize(
        (960, 540), Image.Resampling.LANCZOS
    )
    face_path = os.path.join(ANALYSIS, "DNA-平均脸.png" if mode == "sampler" else "DNA-演示平均脸.png")
    face.save(face_path)

    vs = np.stack([f["v"] for f in fs])
    mean_v = vs.mean(axis=0)
    mean_v = mean_v / (np.linalg.norm(mean_v) / np.sqrt(len(mean_v)) + 1e-6)
    to_mean = [round(corr(f["v"], mean_v), 4) for f in fs]

    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((round(float(mat[i, j]), 4), fs[i]["file"], fs[j]["file"]))
    pairs.sort(reverse=True)

    cxs = [f["cx"] for f in fs]
    cys = [f["cy"] for f in fs]
    result = {
        "mode": mode,
        "count": n,
        "pairwise_corr": {
            "mean": round(float(off.mean()), 4),
            "median": round(float(np.median(off)), 4),
            "min": round(float(off.min()), 4),
            "max": round(float(off.max()), 4),
            "pct_above_090": round(float((off > 0.90).mean()), 4),
            "pct_above_080": round(float((off > 0.80).mean()), 4),
        },
        "skeleton_corr": {
            "mean": round(float(off_s.mean()), 4),
            "median": round(float(np.median(off_s)), 4),
            "min": round(float(off_s.min()), 4),
            "max": round(float(off_s.max()), 4),
            "pct_above_090": round(float((off_s > 0.90).mean()), 4),
            "pct_above_080": round(float((off_s > 0.80).mean()), 4),
        },
        "to_mean_face": {
            "mean": round(float(np.mean(to_mean)), 4),
            "min": round(float(np.min(to_mean)), 4),
            "max": round(float(np.max(to_mean)), 4),
        },
        "centroid": {
            "cx_mean": round(float(np.mean(cxs)), 4),
            "cx_std": round(float(np.std(cxs)), 4),
            "cy_mean": round(float(np.mean(cys)), 4),
            "cy_std": round(float(np.std(cys)), 4),
        },
        "edge_dominant_counts": {
            k: sum(1 for f in fs if f["edge_dominant"] == k)
            for k in ["vertical", "diag135", "horizontal", "diag45"]
        },
        "edge_struct_dominant_counts": {
            k: sum(1 for f in fs if f["edge_struct_dominant"] == k)
            for k in ["vertical", "diag135", "horizontal", "diag45"]
        },
        "top_similar_pairs": pairs[:8],
        "per_image": [
            {
                "file": f["file"],
                "polarity": f["polarity"],
                "cx": f["cx"],
                "cy": f["cy"],
                "dark_ratio": f["dark_ratio"],
                "edge_dominant": f["edge_dominant"],
                "edge_anisotropy": f["edge_anisotropy"],
                "sim_to_mean": to_mean[i],
            }
            for i, f in enumerate(fs)
        ],
        "matrix_labels": [f["file"] for f in fs],
        "matrix": [[round(float(x), 3) for x in row] for row in mat],
    }
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print("MODE", mode, "N", n)
    print("PAIRWISE_SKIN", json.dumps(result["pairwise_corr"], ensure_ascii=False))
    print("PAIRWISE_SKELETON", json.dumps(result["skeleton_corr"], ensure_ascii=False))
    print("TO_MEAN_FACE", json.dumps(result["to_mean_face"], ensure_ascii=False))
    print("CENTROID", json.dumps(result["centroid"], ensure_ascii=False))
    print("EDGE_DOMINANT", json.dumps(result["edge_dominant_counts"], ensure_ascii=False))
    print("EDGE_STRUCT_DOMINANT", json.dumps(result["edge_struct_dominant_counts"], ensure_ascii=False))
    print("EDGE_STRUCT_PER_IMAGE", json.dumps(
        [(f["file"], f["edge_struct_dominant"], f["edge_struct_anisotropy"]) for f in fs], ensure_ascii=False))
    print("TOP_SIMILAR", json.dumps(result["top_similar_pairs"][:5], ensure_ascii=False))
    print("FACE", face_path)


if __name__ == "__main__":
    main()
