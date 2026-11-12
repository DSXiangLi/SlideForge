# -*- coding: utf-8 -*-
"""
静态布局审计：在不依赖浏览器渲染的前提下，解析 dna-pilot.html 的内联样式，
把 cqw/cqh 换算成 480x270 幻灯片的实际像素，定位三类问题：
  1. 字号过小（< 可读下限）的文本
  2. 竖排(writing-mode:vertical-rl)标题因高度/字号约束被强制断列
  3. 文本元素越出 480x270 边界（被 overflow:hidden 裁切）
单位约定（container-type:size, 480x270）：
  1cqw = 4.8px, 1cqh = 2.7px
"""
import re, json, os

SRC = os.path.join(os.path.dirname(__file__), "dna-pilot.html")
W, H = 480, 270
CQW, CQH = 4.8, 2.7

text = open(SRC, encoding="utf-8").read()
lines = text.splitlines()

# 状态机：按方法分桶收集 font-size 与竖排块
methods = {}  # method -> {"fonts":[(val,unit,px)], "vert":[style_str]}
cur = None
vert_blocks = []  # (method, style_str)

method_re = re.compile(r"^  ([a-zA-Z_][\w]*)\(")
fs_re = re.compile(r"font-size:\s*([\d.]+)cq([wh])")
vert_re = re.compile(r"writing-mode:\s*vertical-rl")
style_re = re.compile(r'style="([^"]*)"')

for ln in lines:
    m = method_re.match(ln)
    if m:
        cur = m.group(1)
        methods.setdefault(cur, {"fonts": [], "vert": []})
        continue
    if cur:
        for fm in fs_re.finditer(ln):
            val = float(fm.group(1)); unit = fm.group(2)
            px = val * (CQW if unit == "w" else CQH)
            methods[cur]["fonts"].append((val, unit, round(px, 1)))
        if vert_re.search(ln):
            sm = style_re.search(ln)
            if sm:
                methods[cur]["vert"].append(sm.group(1))
                vert_blocks.append((cur, sm.group(1)))

# ---- 1. 字号过小审计 ----
FLOOR_PX = 9.0  # 480px 宽幻灯片上舒适可读的下限（约 1.875cqw）
print("=" * 64)
print("[审计 1] 字号过小（实际像素 < %.1fpx ≈ %.2fcqw）" % (FLOOR_PX, FLOOR_PX / CQW))
print("=" * 64)
tiny = []
for meth, d in methods.items():
    for val, unit, px in d["fonts"]:
        if px < FLOOR_PX:
            tiny.append((meth, val, unit, px))
tiny.sort(key=lambda x: x[3])
for meth, val, unit, px in tiny:
    print("  %-8s font-size:%.2fcq%s  ->  %.1fpx  太小" % (meth, val, unit, px))
print("  共 %d 处小于可读下限\n" % len(tiny))

# ---- 2. 竖排断列审计 ----
print("=" * 64)
print("[审计 2] 竖排标题断列风险（height 限制每列可容纳字符数）")
print("=" * 64)
# 已知 H1 竖排文本长度（按 \n 拆分后最长一行）
H1_VERT_CONTENT = {
    "cover":   [("当模型开始做梦", 6)],            # 单行 6 字
    "low":     [("模型不生产事实，", 7), ("它生产似真", 5)],
    "closing": [("把想象", 3), ("关进工程的笼子", 7)],
}
def get(style, key):
    m = re.search(r"%s:\s*([\d.]+)cq([wh])" % key, style)
    if not m: return None, None
    v = float(m.group(1)); u = m.group(2)
    return v, (v*CQW if u=="w" else v*CQH)
for meth, style in vert_blocks:
    if meth not in H1_VERT_CONTENT: 
        continue
    fv, fpx = get(style, "font-size")
    hv, hpx = get(style, "height")
    wv, wpx = get(style, "width")
    lh = 1.2  # 竖排默认行高近似
    if fpx and hpx:
        char_adv = fpx * lh
        fit = hpx / char_adv
        print("  %-8s font=%.1fpx height=%.1fpx -> 每列可容 %.1f 字" % (meth, fpx, hpx, fit))
        for s, n in H1_VERT_CONTENT[meth]:
            cols = max(1, -(-n // int(fit) if fit >= 1 else 1))  # 需要列数
            # 更精确：n 字若 > floor(fit) 则断列
            per = int(fit)
            if n > per:
                print("      ✗ “%s”(%d字) 超过每列 %d 字 -> 强制断成 %d 列（视觉错乱）"
                      % (s, n, per, n // per + (1 if n % per else 0)))
            else:
                print("      ✓ “%s”(%d字) 单列可容" % (s, n))
        if wpx:
            print("      width=%.1fpx (限制列数上限 %.1f)" % (wpx, wpx/char_adv))
    print()

# ---- 3. 边界越界审计（位置+尺寸，含插值变量给出范围） ----
print("=" * 64)
print("[审计 3] 文本元素越出 480x270（含出血/裁切风险）")
print("=" * 64)
# 解析所有带 left/top/right/bottom/width/height 的定位元素
pos_re = re.compile(r'(left|right|top|bottom|width|height):\s*([\d.]+)cq([wh])')
overflow = []
for i, ln in enumerate(lines):
    sm = style_re.search(ln)
    if not sm: continue
    style = sm.group(1)
    if "font-size" not in style and "writing-mode" not in style:
        # 仅关心文本/结构件位置，这里全量检查
        pass
    coords = {}
    for pm in pos_re.finditer(style):
        k = pm.group(1); v = float(pm.group(2)); u = pm.group(3)
        coords[k] = v * (CQW if u=="w" else CQH)
    if not coords: continue
    # 计算有效盒（允许 left/right 二选一）
    x0 = coords.get("left")
    if x0 is None and "right" in coords:
        x0 = W - coords["right"] - coords.get("width", 0)
    x1 = x0 + coords["width"] if (x0 is not None and "width" in coords) else None
    y0 = coords.get("top")
    if y0 is None and "bottom" in coords:
        y0 = H - coords["bottom"] - coords.get("height", 0)
    y1 = y0 + coords["height"] if (y0 is not None and "height" in coords) else None
    # 仅报告明显越界（> W/H 的 102%），出血母题件另议
    if x1 is not None and x1 > W * 1.02:
        overflow.append((i+1, style[:60], "x>%.0f" % W, round(x1,1)))
    if y1 is not None and y1 > H * 1.02:
        overflow.append((i+1, style[:60], "y>%.0f" % H, round(y1,1)))
for ln_no, s, kind, val in overflow[:40]:
    print("  L%-4d %s 越界 %s (到 %.1fpx)" % (ln_no, s, kind, val))
if not overflow:
    print("  无明显越界（出血母题件如 E5 对角带/黑楔、H1 雾斑为故意，已 overflow:hidden 裁切）")
print()

# ---- 汇总字号分布 ----
print("=" * 64)
print("[汇总] 各方法字号范围（px）")
print("=" * 64)
for meth in ["cover","toc","low","high","chart","closing","chrome","seal","win"]:
    if meth in methods and methods[meth]["fonts"]:
        px = [p for _,_,p in methods[meth]["fonts"]]
        print("  %-8s min=%.1f  max=%.1f  n=%d" % (meth, min(px), max(px), len(px)))
