#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
密度量化测量：Playwright 1920×1080 逐页统计单个 deck 的密度指标。

用法：python3 tests/harness/density_measure.py tests/decks/<deck>/index.html

每页报告（画布坐标系）：
  leaves    文本叶节点总数（含装饰 skip 件内的文字）
  editable  其中 data-editable 文本叶数
  anno      标注层文本数——mono + 12–16px + 低明度（线性亮度退到
            底色→墨色区间的 ≤65%，typography §5 标注层纪律）
  micro     ≤13px 微字文本数（demo1 解剖口径）
  mono      mono 字体文本数
  tiers     字号档数（去重取整，括号内为非 skip 文字档数）
  fontsizes 全部字号档明细
退出码恒 0（测量工具，不做达标判定）。
"""
import os
import sys

from playwright.sync_api import sync_playwright

MEASURE_JS = """(idx) => {
  const slot = document.querySelectorAll('.slide-slot')[idx];
  const slide = slot.querySelector('.slide');

  function parseColor(c) {
    if (!c) return null;
    let m = /^rgba?\\(([^)]+)\\)$/.exec(c.trim());
    if (m) {
      const p = m[1].split(',').map((s) => parseFloat(s));
      return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    }
    m = /^color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+%?))?\\)$/.exec(c.trim());
    if (m) {
      let a = 1;
      if (m[4] != null) a = m[4].endsWith('%') ? parseFloat(m[4]) / 100 : parseFloat(m[4]);
      return { r: parseFloat(m[1]) * 255, g: parseFloat(m[2]) * 255, b: parseFloat(m[3]) * 255, a };
    }
    return null;
  }
  function lum(rgb) {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(rgb.r) + 0.7152 * f(rgb.g) + 0.0722 * f(rgb.b);
  }
  const csSlide = getComputedStyle(slide);
  const bgC = parseColor(csSlide.backgroundColor) || { r: 0, g: 0, b: 0, a: 1 };
  const inkC = parseColor(csSlide.color) || { r: 255, g: 255, b: 255, a: 1 };
  const Lbg = lum(bgC), Link = lum(inkC);

  const leaves = [];
  const els = Array.from(slide.querySelectorAll('*'));
  for (const el of els) {
    let hasText = false;
    for (const n of el.childNodes) {
      if (n.nodeType === 3 && n.textContent.trim()) { hasText = true; break; }
    }
    if (!hasText) continue;
    let descText = false;
    for (const d of el.querySelectorAll('*')) {
      for (const n of d.childNodes) {
        if (n.nodeType === 3 && n.textContent.trim()) { descText = true; break; }
      }
      if (descText) break;
    }
    if (descText) continue;   // 非叶：文字还在更深层
    const cs = getComputedStyle(el);
    const opacity = parseFloat(cs.opacity);
    if (cs.visibility === 'hidden' || opacity <= 0.02) continue;
    const col = parseColor(cs.color);
    let t = 1;
    if (col) {
      const a = Math.max(0, Math.min(1, col.a * opacity));
      const comp = { r: col.r * a + bgC.r * (1 - a), g: col.g * a + bgC.g * (1 - a), b: col.b * a + bgC.b * (1 - a) };
      const L = lum(comp);
      // 亮度位置 t 与底色/墨色极性无关（同 check-render.py 修正）
      t = Link !== Lbg ? (L - Lbg) / (Link - Lbg) : 1;
    }
    leaves.push({
      text: (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 28),
      fs: parseFloat(cs.fontSize),
      mono: /mono/i.test(cs.fontFamily),
      t: Math.round(t * 100) / 100,
      editable: el.hasAttribute('data-editable'),
      skip: !!el.closest('[data-editable-skip]'),
      furniture: !!el.closest('.masthead,.mastfoot'),
    });
  }

  const anno = leaves.filter((l) => l.mono && l.fs >= 12 && l.fs <= 16 && l.t <= 0.65);
  const micro = leaves.filter((l) => l.fs <= 13);
  const mono = leaves.filter((l) => l.mono);
  const tiersAll = Array.from(new Set(leaves.map((l) => Math.round(l.fs)))).sort((a, b) => a - b);
  const tiersContent = Array.from(new Set(leaves.filter((l) => !l.skip).map((l) => Math.round(l.fs)))).sort((a, b) => a - b);
  return {
    leaves: leaves.length,
    editable: leaves.filter((l) => l.editable).length,
    anno: anno.length,
    micro: micro.length,
    mono: mono.length,
    tiersAll, tiersContent,
    sample: leaves.filter((l) => l.fs <= 16).slice(0, 6),
  };
}"""


def main():
    target = os.path.abspath(sys.argv[1])
    url = 'file://' + target
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.goto(url)
        page.wait_for_timeout(800)
        n = page.evaluate("document.querySelectorAll('.slide-slot').length")
        print('deck: %s  pages: %d' % (target, n))
        print('%-4s %-12s %6s %8s %5s %6s %5s %6s  %s'
              % ('page', 'slide-id', 'leaves', 'editable', 'anno', 'micro', 'mono', 'tiers', 'font-sizes(content)'))
        for i in range(n):
            page.evaluate(
                "(i) => document.querySelectorAll('.slide-slot')[i].scrollIntoView({block:'start'})", i)
            page.wait_for_timeout(2600)  # 等运行时动效还原终态（拆字/count-up）
            sid = page.evaluate(
                "(i) => document.querySelectorAll('.slide-slot')[i].querySelector('.slide').dataset.slideId", i)
            r = page.evaluate(MEASURE_JS, i)
            print('p%-3d %-12s %6d %8d %5d %6d %5d %4d/%-2d  %s'
                  % (i + 1, sid, r['leaves'], r['editable'], r['anno'], r['micro'], r['mono'],
                     len(r['tiersAll']), len(r['tiersContent']), r['tiersContent']))
        browser.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
