# -*- coding: utf-8 -*-
"""E5/H1 toc+low font-harmony patch: coherent 3-tier scale (number~3 / title~2.2 / body~1.8)."""
import io, sys

P = r"C:/Users/lixiang/Desktop/SlideForge/analysis/dna-pilot.html"
t = io.open(P, encoding="utf-8").read()

EDITS = [
    # --- E5 toc: header 1.6->1.7; number 3.4->3; title 2->2.4; desc 1.5->1.8 (+opacity); clear wedge; fill page ---
    ('font-size:1.6cqw;font-weight:900;letter-spacing:.2em;color:var(--ink)">目录 / INDEX',
     'font-size:1.7cqw;font-weight:900;letter-spacing:.2em;color:var(--ink)">目录 / INDEX'),
    ('const x=4, y=16+i*9.6;', 'const x=5, y=18+i*10;'),
    ('top:${y}cqh;font-size:3.4cqw;font-weight:900;color:var(--accent)',
     'top:${y}cqh;font-size:3cqw;font-weight:900;color:var(--accent)'),
    ('left:${x+11}cqw;top:${y+0.3}cqh;font-size:2cqw;font-weight:800',
     'left:${x+12}cqw;top:${y+0.3}cqh;font-size:2.4cqw;font-weight:800'),
    ('left:${x+11}cqw;top:${y+5}cqh;font-size:1.5cqw;color:var(--ink);opacity:.75',
     'left:${x+12}cqw;top:${y+5.4}cqh;font-size:1.8cqw;color:var(--ink);opacity:.85'),
    # --- E5 low: note 1.5->1.8, widen to keep one line ---
    ('right:6cqw;top:8cqh;width:34cqw;font-size:1.5cqw;font-weight:700;color:var(--ink);text-align:right;line-height:1.4',
     'right:6cqw;top:8cqh;width:38cqw;font-size:1.8cqw;font-weight:700;color:var(--ink);text-align:right;line-height:1.5'),
    # --- H1 toc: header 1.5->1.6; number 3.2->2.9; title 1.7->2.1; desc 1.5->1.8 opacity .8; rules match content ---
    ('font-size:1.5cqw;letter-spacing:.2em;color:var(--accent-2)">展卷 · 目录',
     'font-size:1.6cqw;letter-spacing:.2em;color:var(--accent-2)">展卷 · 目录'),
    ('const x=x0[i];const y=18;', 'const x=x0[i];const y=20;'),
    ('width:14cqw;height:60cqh;border-left:1px solid', 'width:14cqw;height:50cqh;border-left:1px solid'),
    ('font-size:3.2cqw;color:var(--accent-2)', 'font-size:2.9cqw;color:var(--accent-2)'),
    ('font-size:1.7cqw;font-weight:700;color:var(--ink);margin-top:.6cqh">${it.t}',
     'font-size:2.1cqw;font-weight:700;color:var(--ink);margin-top:.6cqh">${it.t}'),
    ('font-size:1.5cqw;color:var(--ink);opacity:.65;margin-top:1cqh;line-height:1.5">${it.d}',
     'font-size:1.8cqw;color:var(--ink);opacity:.8;margin-top:1.2cqh;line-height:1.55">${it.d}'),
    # --- H1 low: note & stat caption 1.5->1.8, lift opacity ---
    ('left:6cqw;top:20cqh;width:30cqw;font-size:1.5cqw;color:var(--ink);opacity:.75;line-height:1.6',
     'left:6cqw;top:20cqh;width:32cqw;font-size:1.8cqw;color:var(--ink);opacity:.85;line-height:1.6'),
    ('left:6cqw;top:62cqh;font-size:1.5cqw;color:var(--ink);opacity:.6;line-height:1.5;width:30cqw',
     'left:6cqw;top:62cqh;font-size:1.8cqw;color:var(--ink);opacity:.8;line-height:1.5;width:30cqw'),
]

applied, missed = 0, []
for old, new in EDITS:
    n = t.count(old)
    if n == 1:
        t = t.replace(old, new); applied += 1
    else:
        missed.append((n, old[:70]))

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
with io.open(r"C:/Users/lixiang/Desktop/SlideForge/analysis/_patch_out.txt", "w", encoding="utf-8") as f:
    f.write("APPLIED %d / %d\n" % (applied, len(EDITS)))
    for n, frag in missed:
        f.write("MISS(count=%d): %s\n" % (n, frag))
print("done")
