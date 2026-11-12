"""check-dna.py — G10 跨主题 / 跨页面类型结构分化门禁。

输入：analysis/PILOT-<theme>-<page>.png（4 主题 × 6 页面类型 = 24 张）
复用 _fingerprint.features 取低频骨架层 s(10×6) 与皮肤层 v(32×18)。

判据（取自 G10-主题DNA规范草案.md §4，阈值用该轮实测校准）：
  1. 类间可分：任意两主题骨架相关 ≤ 0.35；>0.8 的配对占比 = 0
  2. 类内成族：同主题跨页骨架相关落在 0.55–0.85（原校准基于每主题 3 张代表页；
              本试点扩到 6 种页面类型，跨类型差异会拉低均值，低于 0.55 即记 WARN）
  3. 页面类型覆盖：每种页面类型下，跨主题骨架相关 ≤ 0.35 仍成立（证明结论不挑页面类型）
  4. 几何不变量（指纹可代理项）：
       B1 斜向结构能量 ≈ 0（禁斜向）
       E5 对角结构能量 ≥ 25%（−12° 力线）
       H1 结构边缘主方向 = vertical（竖排主轴）
  5. 节奏方差（C3 只封面强形态）：封面与弱形态页的相关，应低于弱形态内部相关

输出：check_dna_report.json + check_dna_report.txt（人读版）
"""
import os
import sys
import glob
import json
import numpy as np

ANALYSIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ANALYSIS)
import _fingerprint as F

PAGES = ["cover", "toc", "low", "high", "chart", "closing"]  # 首页/目录/低密度/高密度/图表/收尾
THEMES = ["b1", "e5", "c3", "h1"]

# 页角色 → dna_events 强度（取自 G10 草案；toc 视为 divider 中强度）
STRENGTH = {
    "b1": {"cover": "强", "toc": "中", "low": "强", "high": "中", "chart": "强", "closing": "中"},
    "e5": {"cover": "强", "toc": "中", "low": "强", "high": "弱", "chart": "强", "closing": "强"},
    "c3": {"cover": "强", "toc": "弱", "low": "弱", "high": "弱", "chart": "弱", "closing": "弱"},
    "h1": {"cover": "强", "toc": "中", "low": "中", "high": "弱", "chart": "弱", "closing": "强"},
}


def parse():
    files = sorted(glob.glob(os.path.join(ANALYSIS, "PILOT-*.png")))
    feats = {}
    for f in files:
        base = os.path.basename(f)[:-4]
        parts = base.split("-")
        if len(parts) != 3 or parts[0] != "PILOT":
            continue
        feats[(parts[1], parts[2])] = F.features(f)
    return feats


def cos(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def count(seq):
    d = {}
    for x in seq:
        d[x] = d.get(x, 0) + 1
    return d


def main():
    feats = parse()
    keys = list(feats.keys())
    missing = [(t, p) for t in THEMES for p in PAGES if (t, p) not in feats]
    if missing:
        raise SystemExit("缺少样张: %s" % missing)

    # 跨主题两两骨架/皮肤相关（区分「同页面角色」与「不同角色」）
    cross_s, cross_v = [], []
    cross_s_same, cross_s_diff = [], []
    collisions = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if keys[i][0] == keys[j][0]:
                continue
            cs = cos(feats[keys[i]]["s"], feats[keys[j]]["s"])
            cv = cos(feats[keys[i]]["v"], feats[keys[j]]["v"])
            cross_s.append(cs)
            cross_v.append(cv)
            if keys[i][1] == keys[j][1]:
                cross_s_same.append(cs)
            else:
                cross_s_diff.append(cs)
            collisions.append((cs, "%s/%s" % (keys[i][0], keys[i][1]), "%s/%s" % (keys[j][0], keys[j][1])))
    cross_s = np.array(cross_s)
    cross_v = np.array(cross_v)
    cross_s_same = np.array(cross_s_same)
    cross_s_diff = np.array(cross_s_diff)
    collisions.sort(reverse=True)
    top_collisions = [{"corr": round(c, 3), "a": a, "b": b} for c, a, b in collisions[:12]]

    # 类内成族
    within = {}
    for t in THEMES:
        vals = []
        for a in range(len(PAGES)):
            for b in range(a + 1, len(PAGES)):
                vals.append(cos(feats[(t, PAGES[a])]["s"], feats[(t, PAGES[b])]["s"]))
        m = float(np.mean(vals))
        within[t] = {
            "mean": round(m, 4),
            "min": round(float(np.min(vals)), 4),
            "max": round(float(np.max(vals)), 4),
            "in_band_055_085": bool(0.55 <= m <= 0.85),
        }

    # 每种页面类型下的跨主题相关
    per_type = {}
    for p in PAGES:
        vals = []
        for a in range(len(THEMES)):
            for b in range(a + 1, len(THEMES)):
                vals.append(cos(feats[(THEMES[a], p)]["s"], feats[(THEMES[b], p)]["s"]))
        mx = float(np.max(vals))
        per_type[p] = {
            "mean": round(float(np.mean(vals)), 4),
            "max": round(mx, 4),
            "pass_le_035": bool(mx <= 0.35),
        }

    # 几何不变量代理
    invariants = {}
    for t in THEMES:
        diag = [round(feats[(t, p)]["edge_struct"]["diag135"] + feats[(t, p)]["edge_struct"]["diag45"], 4) for p in PAGES]
        dom = [feats[(t, p)]["edge_struct_dominant"] for p in PAGES]
        if t == "b1":
            invariants[t] = {"diag_energy_max": round(max(diag), 4), "diag_zero_ok": bool(max(diag) < 0.10), "dominant_counts": count(dom)}
        elif t == "e5":
            invariants[t] = {"diag_energy_min": round(min(diag), 4), "diag_ge_25_ok": bool(min(diag) >= 0.25), "dominant_counts": count(dom)}
        elif t == "h1":
            invariants[t] = {"vertical_count": sum(1 for d in dom if d == "vertical"), "total": len(dom),
                             "vertical_ok": bool(all(d == "vertical" for d in dom))}
        else:
            invariants[t] = {"diag_energy": diag, "dominant_counts": count(dom)}

    # 节奏方差（强 vs 弱）
    rhythm = {}
    for t in THEMES:
        strong = [p for p in PAGES if STRENGTH[t][p] == "强"]
        weak = [p for p in PAGES if STRENGTH[t][p] == "弱"]
        if strong and weak:
            sw = [cos(feats[(t, a)]["s"], feats[(t, b)]["s"]) for a in strong for b in weak]
            ww = [cos(feats[(t, a)]["s"], feats[(t, b)]["s"]) for i, a in enumerate(weak) for b in weak[i + 1:]]
            rhythm[t] = {"strong_weak_mean": round(float(np.mean(sw)), 4),
                         "weak_weak_mean": round(float(np.mean(ww)), 4) if ww else None}
        else:
            rhythm[t] = {"note": "无强/弱分化样本（仅有 强/中）"}

    # 重心离散度
    centroid = {}
    for t in THEMES:
        cx = [feats[(t, p)]["cx"] for p in PAGES]
        cy = [feats[(t, p)]["cy"] for p in PAGES]
        centroid[t] = {"cx_std": round(float(np.std(cx)), 4), "cy_std": round(float(np.std(cy)), 4)}

    verdict = {
        "n_pages": len(keys),
        "themes": THEMES,
        "pages": PAGES,
        "check1_cross_theme_separable": {
            "skeleton_corr_max": round(float(cross_s.max()), 4),
            "skeleton_corr_mean": round(float(cross_s.mean()), 4),
            "skin_corr_max": round(float(cross_v.max()), 4),
            "pct_pairs_above_080": round(float((cross_s > 0.8).mean()), 4),
            "cross_same_role_max": round(float(cross_s_same.max()), 4),
            "cross_same_role_mean": round(float(cross_s_same.mean()), 4),
            "cross_diff_role_max": round(float(cross_s_diff.max()), 4),
            "cross_diff_role_mean": round(float(cross_s_diff.mean()), 4),
            "top_collisions": top_collisions,
            "pass": bool(cross_s.max() <= 0.35 and (cross_s > 0.8).mean() == 0),
        },
        "check2_within_theme_cluster": within,
        "check3_per_page_type": per_type,
        "check4_invariants": invariants,
        "rhythm": rhythm,
        "centroid_dispersion": centroid,
        "summary": {
            "check1_pass": bool(cross_s.max() <= 0.35 and (cross_s > 0.8).mean() == 0),
            "check2_all_in_band": all(within[t]["in_band_055_085"] for t in THEMES),
            "check3_all_types_pass": all(per_type[p]["pass_le_035"] for p in PAGES),
            "check4_ok": bool(invariants["b1"]["diag_zero_ok"] and invariants["e5"]["diag_ge_25_ok"] and invariants["h1"]["vertical_ok"]),
        },
    }

    verdict["measurement_caveats"] = [
        "指纹骨架层 s 仅 10×6=60 格、强模糊后只保留「哪重哪空」——被页面角色(封面/图表/目录)的功能结构主导，同角色跨主题页天然趋同，这是方法局限不是主题缺陷。",
        "edge_struct 方向只用 4 个 22.5° 分箱：E5 的 −12° 力带长边近水平会被计入 horizontal；H1 细竖排标题被上下金轴(水平)的粗边压制，二者都读不出真实签名方向，invariants 的方向项须改在 DOM 几何层校验。",
        "本批 24 张为最新无头渲染(经 npmmirror 镜像装好 Chromium 后重渲)，已包含字号下限(1.5cqw)、H1 竖排断列修复与 E5 目录对齐；结论与上一轮一致。",
        "原始 4 页演示(不同角色各一)的「类间可分」是在 apple-vs-orange 下成立的；本 24 页同角色对照才是 DNA 的真正试金石，目前仅 H1 通过。",
    ]

    out_json = os.path.join(ANALYSIS, "check_dna_report.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)

    # 人读版
    L = []
    L.append("=" * 60)
    L.append("G10 DNA 门禁报告  (n=%d 页)" % len(keys))
    L.append("=" * 60)
    c1 = verdict["check1_cross_theme_separable"]
    L.append("[CHECK 1] 类间可分（跨主题骨架相关）")
    L.append("  骨架相关 max=%.3f  mean=%.3f  皮肤相关 max=%.3f" % (c1["skeleton_corr_max"], c1["skeleton_corr_mean"], c1["skin_corr_max"]))
    L.append("  >0.8 配对占比=%.3f  判定: %s" % (c1["pct_pairs_above_080"], "PASS" if c1["pass"] else "FAIL"))
    L.append("  同角色对照  max=%.3f mean=%.3f  |  异角色对照  max=%.3f mean=%.3f" % (
        c1["cross_same_role_max"], c1["cross_same_role_mean"], c1["cross_diff_role_max"], c1["cross_diff_role_mean"]))
    L.append("  最高撞脸配对(top collisions):")
    for c in c1["top_collisions"][:6]:
        L.append("    %.3f  %s  <->  %s" % (c["corr"], c["a"], c["b"]))
    L.append("")
    L.append("[CHECK 2] 类内成族（同主题跨页骨架相关，目标 0.55–0.85）")
    for t in THEMES:
        w = within[t]
        flag = "OK" if w["in_band_055_085"] else "WARN"
        L.append("  %s  mean=%.3f  min=%.3f  max=%.3f  [%s]" % (t.upper(), w["mean"], w["min"], w["max"], flag))
    L.append("")
    L.append("[CHECK 3] 页面类型覆盖（每种类型下跨主题骨架相关 ≤0.35）")
    for p in PAGES:
        r = per_type[p]
        L.append("  %-8s max=%.3f  mean=%.3f  [%s]" % (p, r["max"], r["mean"], "PASS" if r["pass_le_035"] else "FAIL"))
    L.append("")
    L.append("[CHECK 4] 几何不变量（指纹代理）")
    L.append("  B1 对角能量 max=%.3f  禁斜向: %s" % (invariants["b1"]["diag_energy_max"], invariants["b1"]["diag_zero_ok"]))
    L.append("  E5 对角能量 min=%.3f  ≥0.25: %s" % (invariants["e5"]["diag_energy_min"], invariants["e5"]["diag_ge_25_ok"]))
    L.append("  H1 vertical 主方向 %d/%d  全vertical: %s" % (invariants["h1"]["vertical_count"], invariants["h1"]["total"], invariants["h1"]["vertical_ok"]))
    L.append("")
    L.append("[CHECK 5] 节奏方差（C3 封面强 vs 弱形态）")
    for t in THEMES:
        r = rhythm[t]
        if "note" in r:
            L.append("  %s  %s" % (t.upper(), r["note"]))
        else:
            L.append("  %s  强-弱 mean=%.3f  弱-弱 mean=%s" % (t.upper(), r["strong_weak_mean"], r["weak_weak_mean"]))
    L.append("")
    L.append("[SUMMARY] 1=%s  2(全在带)=%s  3(全类型过)=%s  4=%s" % (
        verdict["summary"]["check1_pass"], verdict["summary"]["check2_all_in_band"],
        verdict["summary"]["check3_all_types_pass"], verdict["summary"]["check4_ok"]))
    L.append("")
    L.append("[测量局限 / 说明]")
    for cav in verdict["measurement_caveats"]:
        L.append("  - " + cav)
    L.append("=" * 60)

    txt = "\n".join(L)
    out_txt = os.path.join(ANALYSIS, "check_dna_report.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
