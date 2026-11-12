# -*- coding: utf-8 -*-
"""
H1 竖排标题最终修复：实测回退字体的竖排字距 ≈ 1.4 x font-size（渲染证实 1em 假设不成立）。
按  chars_fit = height / (font*1.4)  重算三处竖排标题，保证单列不断行。
同时给 C3 目录加大字号/行距，填补终端窗口下部的空腔。
"""
import os
SRC = os.path.join(os.path.dirname(__file__), "dna-pilot.html")
out = open(SRC, encoding="utf-8").read()

FIX = [
  # cover：7字，height 90cqh=243px -> font <= 243/(7*1.4)=24.8px，取 4.8cqw(23px)=225px，留 18px 余量
  ('right:8cqw;top:22cqh;writing-mode:vertical-rl;font-size:6cqw;font-weight:700;color:var(--ink);letter-spacing:.1em;height:78cqh">${D.title}',
   'right:8cqw;top:6cqh;writing-mode:vertical-rl;font-size:4.8cqw;font-weight:700;color:var(--ink);letter-spacing:.02em;height:90cqh">${D.title}'),
  # low：首行 8 字(含逗号)，height 86cqh=232px -> font <= 232/11.2=20.7px，取 4.1cqw(19.7px)=220px
  ('right:8cqw;top:18cqh;writing-mode:vertical-rl;font-size:5.2cqw;font-weight:700;color:var(--ink);height:80cqh;white-space:pre-line;line-height:1.15">${D.claim.head}',
   'right:8cqw;top:12cqh;writing-mode:vertical-rl;font-size:4.1cqw;font-weight:700;color:var(--ink);height:86cqh;white-space:pre-line;line-height:1.15">${D.claim.head}'),
  # closing：次行 7 字，height 84cqh=227px -> font <= 227/9.8=23.1px，取 4.6cqw(22px)=216px
  ('right:10cqw;top:22cqh;writing-mode:vertical-rl;font-size:5cqw;font-weight:700;color:var(--ink);height:80cqh;white-space:pre-line;line-height:1.2">${D.closing.head}',
   'right:10cqw;top:14cqh;writing-mode:vertical-rl;font-size:4.6cqw;font-weight:700;color:var(--ink);height:84cqh;white-space:pre-line;line-height:1.2">${D.closing.head}'),
  # C3 目录：放大条目并增加行距，填满终端窗口
  ("toc(){let items=D.toc.map((it,i)=>",
   'toc(){let items=\'<div style="font-size:2cqw;line-height:2.2;margin-top:1cqh">\'+D.toc.map((it,i)=>'),
  ("</span></div>`).join(\"\");",
   "</span></div>`).join(\"\")+'</div>';"),
]
for old, new in FIX:
    n = out.count(old)
    out = out.replace(old, new)
    print("%d  %s" % (n, old[:46]))

open(SRC, "w", encoding="utf-8").write(out)
print("done")
