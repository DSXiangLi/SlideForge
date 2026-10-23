#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渲染自检：Playwright 1920×1080 逐页检查单个 deck。

用法：python3 skills/html-pptx/scripts/check-render.py <deck>/index.html

检查项（全部硬）：
  1. 零溢出——每个 data-editable 元素的包围盒不得越出所在 1920×1080 画布
     （画布坐标系，容差 2px；装饰件 data-editable-skip 不参与）；
  2. 零重叠——同页 data-editable 元素两两交集面积 ≤16px²（画布坐标）；
  3. 正文字号 ≥18px（画布坐标 = 计算样式 px）——例外：.masthead/.mastfoot
     框架家具（meta 槽位，typography §2 下限 14px）、mono meta 小字（≥14px）、
     K 期标注层（typography §5：mono + 12–13.9px + 低明度——合成色线性亮度
     须退到底色→墨色区间的 ≤65%，全亮小字仍判违规）。
退出码：全过 0，任一失败 1。
"""
import os
import sys

from playwright.sync_api import sync_playwright

MEASURE_JS = r"""(idx) => {
  const slot = document.querySelectorAll('.slide-slot')[idx];
  const slide = slot.querySelector('.slide');
  const scale = parseFloat(document.documentElement.style.getPropertyValue('--slide-scale')) || 1;
  const sr = slide.getBoundingClientRect();
  const toCanvas = (r) => ({
    left: (r.left - sr.left) / scale, top: (r.top - sr.top) / scale,
    right: (r.right - sr.left) / scale, bottom: (r.bottom - sr.top) / scale,
    width: r.width / scale, height: r.height / scale,
  });
  const els = Array.from(slide.querySelectorAll('[data-editable]'));
  function parseColor(c) {
    if (!c) return null;
    let m = /^rgba?\(([^)]+)\)$/.exec(c.trim());
    if (m) {
      const p = m[1].split(',').map((s) => parseFloat(s));
      return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    }
    m = /^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+%?))?\)$/.exec(c.trim());
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
  const items = els.map((el) => {
    const cs = getComputedStyle(el);
    const opacity = parseFloat(cs.opacity);
    const col = parseColor(cs.color);
    let dimT = 1;   // 合成色线性亮度在 底色→墨色 区间中的位置（0=贴底，1=全亮墨色）
    if (col) {
      const a = Math.max(0, Math.min(1, col.a * opacity));
      const comp = { r: col.r * a + bgC.r * (1 - a), g: col.g * a + bgC.g * (1 - a), b: col.b * a + bgC.b * (1 - a) };
      // 亮度位置 t 与底色/墨色极性无关：亮底深墨（分母为负）与暗底浅墨同样成立，
      // 仅当底色与墨色等亮（非法主题）时退化为 1（全亮，不放过小字）。
      dimT = Link !== Lbg ? (lum(comp) - Lbg) / (Link - Lbg) : 1;
    }
    return {
      text: (el.textContent || '').trim().slice(0, 24),
      rect: toCanvas(el.getBoundingClientRect()),
      fontSize: parseFloat(cs.fontSize),
      fontFamily: cs.fontFamily,
      dimT,
      inFurniture: !!el.closest('.masthead,.mastfoot'),
      visible: cs.visibility !== 'hidden' && opacity > 0.02,
    };
  }).filter((it) => it.visible && it.rect.width > 0 && it.rect.height > 0);

  const overflow = [];
  for (const it of items) {
    if (it.rect.left < -2 || it.rect.top < -2 || it.rect.right > 1922 || it.rect.bottom > 1082) {
      overflow.push(it);
    }
  }
  const overlaps = [];
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      const a = items[i].rect, b = items[j].rect;
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 0 && h > 0 && w * h > 16) {
        overlaps.push({ a: items[i].text, b: items[j].text, area: Math.round(w * h) });
      }
    }
  }
  const small = [];
  for (const it of items) {
    if (it.fontSize >= 18) continue;
    const mono = /mono/i.test(it.fontFamily);
    const monoMeta = mono && it.fontSize >= 14;
    // K 期标注层例外（typography §5）：mono + ≥12px + 低明度（dimT ≤0.65）
    const annoLayer = mono && it.fontSize >= 12 && it.dimT <= 0.65;
    if (!it.inFurniture && !monoMeta && !annoLayer) small.push(it);
  }
  return { overflow, overlaps, small, count: items.length, scale };
}"""


def main():
    target = os.path.abspath(sys.argv[1])
    url = 'file://' + target
    failures = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.goto(url)
        page.wait_for_timeout(800)
        n = page.evaluate("document.querySelectorAll('.slide-slot').length")
        print('deck: %s  pages: %d' % (target, n))
        for i in range(n):
            page.evaluate(
                "(i) => document.querySelectorAll('.slide-slot')[i].scrollIntoView({block:'start'})", i)
            page.wait_for_timeout(2600)  # 等入场/运行时动效完成并还原终态
            sid = page.evaluate(
                "(i) => document.querySelectorAll('.slide-slot')[i].querySelector('.slide').dataset.slideId", i)
            r = page.evaluate(MEASURE_JS, i)
            ok = not (r['overflow'] or r['overlaps'] or r['small'])
            print('%s  p%d %-12s editable=%d' % ('PASS' if ok else 'FAIL', i + 1, sid, r['count']))
            for it in r['overflow']:
                print('    溢出: "%s" rect=%s' % (it['text'], {k: round(v, 1) for k, v in it['rect'].items()}))
                failures += 1
            for ov in r['overlaps']:
                print('    重叠: "%s" × "%s" area=%dpx²' % (ov['a'], ov['b'], ov['area']))
                failures += 1
            for it in r['small']:
                print('    小字: "%s" %.1fpx' % (it['text'], it['fontSize']))
                failures += 1
        browser.close()
    print('RESULT:', 'ALL PASS' if failures == 0 else '%d FAILURES' % failures)
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
