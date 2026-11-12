# -*- coding: utf-8 -*-
"""
字号与排版修复（稳健版）：
1) 通用可读下限：任何 font-size:Xcqw 且 X<1.5 的统一提升到 1.5cqw（7.2px），
   正文/说明/轴标不再出现 4.6–8px 的不可读字号；标题/数字层级(>=2cqw)不动。
2) 竖排断列修复（H1）：cover 主标题 7cqw->6cqw 并加高至 78cqh（6字单列可容）；
   low 主标题 4.6->5.2cqw 并加高；closing 主标题加高至 80cqh（7字单列保险）。
3) E5 目录：序号列对齐（去掉 i*1.6 错位），行距收紧避免与红色力带相撞；
   目录页红色力带下移 64->72cqh。
仅放大/改结构，绝不缩小；regex 正确解析 .95 / 1.1 等写法。
"""
import re, os

SRC = os.path.join(os.path.dirname(__file__), "dna-pilot.html")
text = open(SRC, encoding="utf-8").read()

# ---- 1) 通用下限 1.5cqw ----
fs_re = re.compile(r"font-size:(\d*\.\d+|\d+)cqw")
def floor(m):
    v = float(m.group(1))
    if v < 1.5:
        return "font-size:1.5cqw"
    return m.group(0)
before = len(fs_re.findall(text))
out = fs_re.sub(floor, text)
after = len(fs_re.findall(out))
print("[1] font-size<cqw 下限 1.5cqw：扫描 %d 处，已提升 %d 处" % (before, before - sum(1 for _ in fs_re.finditer(out))))

# ---- 2) 竖排断列 / 结构修复（精确字符串） ----
STRUCT = [
  # H1 cover 竖排主标题
  ('right:8cqw;top:30cqh;writing-mode:vertical-rl;font-size:7cqw;font-weight:700;color:var(--ink);letter-spacing:.1em;height:60cqh">${D.title}',
   'right:8cqw;top:22cqh;writing-mode:vertical-rl;font-size:6cqw;font-weight:700;color:var(--ink);letter-spacing:.1em;height:78cqh">${D.title}'),
  # H1 low 竖排主标题
  ('right:8cqw;top:20cqh;writing-mode:vertical-rl;font-size:4.6cqw;font-weight:700;color:var(--ink);height:76cqh;white-space:pre-line;line-height:1.15">${D.claim.head}',
   'right:8cqw;top:18cqh;writing-mode:vertical-rl;font-size:5.2cqw;font-weight:700;color:var(--ink);height:80cqh;white-space:pre-line;line-height:1.15">${D.claim.head}'),
  # H1 closing 竖排主标题（加高保险）
  ('font-size:5cqw;font-weight:700;color:var(--ink);height:72cqh;white-space:pre-line;line-height:1.2">${D.closing.head}',
   'font-size:5cqw;font-weight:700;color:var(--ink);height:80cqh;white-space:pre-line;line-height:1.2">${D.closing.head}'),
  # E5 chrome 目录页力带下移
  ("top:${pg==='toc'?64:42}cqh", "top:${pg==='toc'?72:42}cqh"),
  # E5 toc 序号列对齐 + 行距
  ("const x=4+i*1.6, y=20+i*11;", "const x=4, y=16+i*9.6;"),
]
for old, new in STRUCT:
    n = out.count(old)
    out = out.replace(old, new)
    print("[2] %-2s  %s" % (n, old[:50]))

open(SRC, "w", encoding="utf-8").write(out)
print("\n写入完成。")
