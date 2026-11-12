# -*- coding: utf-8 -*-
"""一次性原子化应用 dna-pilot.html 的全部布局修正。"""
import io, sys

P = r"C:\Users\lixiang\Desktop\SlideForge\analysis\dna-pilot.html"
s = io.open(P, encoding="utf-8").read()
n0 = s

REPS = []

# 1. B1 角标：右/下角标改用 right/bottom 定位，避免越界
REPS.append(("""    [[0,0],[100,0],[0,100],[100,100]].forEach(([x,y])=>{
      g+=`<div style="left:${x===0?0:100-1.6}cqw;top:${y===0?0:100-2.6}cqh;width:14px;height:14px;opacity:.5">""",
"""    [[0,0],[100,0],[0,100],[100,100]].forEach(([x,y])=>{
      const px = x===0 ? 'left:0' : 'right:0';
      const py = y===0 ? 'top:0' : 'bottom:0';
      g+=`<div style="${px};${py};width:14px;height:14px;opacity:.5">"""))

# 2. C3 窗体 body 底部单位
REPS.append(("right:.8cqw;bottom:.8cqw;color:var(--ink)", "right:.8cqw;bottom:1cqh;color:var(--ink)"))

# 3. C3 图表基线
REPS.append(("chart(){const max=100,h=52,base=72,x0=6,w=12,gap=2.2;",
             "chart(){const max=100,h=48,base=64,x0=6,w=12,gap=2.2;"))

# 4. C3 图表注释移位（原与 93 相撞）
REPS.append(("<div style=\"position:absolute;left:50cqw;top:${base-50}cqh;font-size:1.1cqw;color:var(--accent)\">↑ ${D.chart.take}</div>",
             "<div style=\"position:absolute;left:1cqw;top:${base+9}cqh;font-size:1.1cqw;color:var(--accent)\">↑ ${D.chart.take}</div>"))

# 5. E5 目录：整体上移避开对角带，序号收小
REPS.append(("""    D.toc.forEach((it,i)=>{const x=4+i*1.6, y=20+i*13;
      s+=`<div style="left:${x}cqw;top:${y}cqh;font-size:4.6cqw;font-weight:900;color:var(--accent)">${it.n}</div>
          <div style="left:${x+12}cqw;top:${y+0.5}cqh;font-size:2.2cqw;font-weight:800;color:var(--ink)">${it.t}</div>
          <div style="left:${x+12}cqw;top:${y+6.4}cqh;font-size:1.2cqw;color:var(--ink);opacity:.75">${it.d}</div>`;});""",
"""    D.toc.forEach((it,i)=>{const x=4+i*1.6, y=12+i*8.8;
      s+=`<div style="left:${x}cqw;top:${y}cqh;font-size:3.4cqw;font-weight:900;color:var(--accent)">${it.n}</div>
          <div style="left:${x+11}cqw;top:${y+0.3}cqh;font-size:2cqw;font-weight:800;color:var(--ink)">${it.t}</div>
          <div style="left:${x+11}cqw;top:${y+5}cqh;font-size:1.15cqw;color:var(--ink);opacity:.75">${it.d}</div>`;});"""))

# 6. E5 low：标题随力线旋转，装进带内反白
REPS.append(("""  low(){return `
    <div style="left:0;top:42cqh;width:100cqw;height:17cqh;background:var(--accent);transform:rotate(-12deg)"></div>
    <div style="left:6cqw;top:40cqh;width:84cqw;font-size:6.4cqw;font-weight:900;color:var(--paper);line-height:1.08;white-space:pre-line;text-transform:none">${D.claim.head}</div>
    <div style="right:6cqw;top:8cqh;width:34cqw;font-size:1.5cqw;font-weight:700;color:var(--ink);text-align:right;line-height:1.4">${D.claim.note}</div>
    <div style="left:6cqw;top:88cqh;font-size:3.6cqw;font-weight:900;color:var(--ink)">${D.claim.stat.num}</div>`;""",
"""  low(){return `
    <div style="left:-12cqw;top:40cqh;width:132cqw;height:22cqh;background:var(--accent);transform:rotate(-12deg)"></div>
    <div style="left:-12cqw;top:40cqh;width:132cqw;height:22cqh;transform:rotate(-12deg);display:flex;align-items:center;padding-left:14cqw">
      <div style="font-size:4.2cqw;font-weight:900;color:var(--paper);white-space:pre-line;line-height:1.12">${D.claim.head}</div></div>
    <div style="right:6cqw;top:8cqh;width:34cqw;font-size:1.5cqw;font-weight:700;color:var(--ink);text-align:right;line-height:1.4">${D.claim.note}</div>
    <div style="left:6cqw;top:88cqh;font-size:3.6cqw;font-weight:900;color:var(--ink)">${D.claim.stat.num}</div>`;"""))

# 7. E5 图表大数字：改右缘对齐防溢出
REPS.append(("s+=`<div style=\"left:${x0+last*step+13}cqw;top:18cqh;width:30cqw;font-size:8cqw;font-weight:900;color:var(--accent);line-height:.9\">${D.chart.series[last].v}</div>",
             "s+=`<div style=\"right:5cqw;top:16cqh;width:26cqw;font-size:8cqw;font-weight:900;color:var(--accent);line-height:.9;text-align:right\">${D.chart.series[last].v}</div>"))

# 8. H1 封面副题：右移避开竖排主标题列
REPS.append(("<div style=\"right:30cqh;top:30cqh;writing-mode:vertical-rl;font-size:1.4cqw;color:var(--ink);opacity:.6;height:60cqh\">${D.subtitle}</div>",
             "<div style=\"right:31cqw;top:28cqh;writing-mode:vertical-rl;font-size:1.3cqw;color:var(--ink);opacity:.6;height:60cqh\">${D.subtitle}</div>"))

# 9. H1 low：竖排主标题按语义断行
REPS.append(("<div style=\"right:8cqw;top:14cqh;writing-mode:vertical-rl;font-size:6.4cqw;font-weight:700;color:var(--ink);height:72cqh\">${D.claim.head.replace(\"\\n\",\"\")}</div>",
             "<div style=\"right:8cqw;top:26cqh;writing-mode:vertical-rl;font-size:5cqw;font-weight:700;color:var(--ink);height:78cqh;white-space:pre-line;line-height:1.15\">${D.claim.head}</div>"))

# 10. H1 closing：竖排标题收字
REPS.append(("<div style=\"right:10cqw;top:24cqh;writing-mode:vertical-rl;font-size:6cqw;font-weight:700;color:var(--ink);height:58cqh;white-space:pre-line\">${D.closing.head}</div>",
             "<div style=\"right:10cqw;top:22cqh;writing-mode:vertical-rl;font-size:5cqw;font-weight:700;color:var(--ink);height:72cqh;white-space:pre-line;line-height:1.2\">${D.closing.head}</div>"))

# 11. H1 closing meta 已在上一轮生效，跳过

fail = 0
for old, new in REPS:
    if old not in s:
        print("MISS:", old[:60].replace("\n", "\\n"))
        fail += 1
    else:
        s = s.replace(old, new, 1)

if fail == 0:
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("APPLIED", len(REPS), "edits; size", len(n0), "->", len(s))
else:
    print("ABORTED — nothing written,", fail, "missed")
