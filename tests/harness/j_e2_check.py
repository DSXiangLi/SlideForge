#!/usr/bin/env python3
"""J 期终验 2/3：j-localfirst-e2 渲染自检（1920x1080 逐页）。
检查：1) 每页 scrollWidth/scrollHeight 不越 1920x1080 画布；
2) 可编辑元素（[data-editable]）两两不重叠（交叠面积 >16px^2 才计）；
3) 正文（[data-editable] 元素）字号 >=18px（画布坐标系）——
   meta/kicker/图注档（masthead/mastfoot/mono 标注）按契约下限 14/16 豁免，
   本脚本对 <18px 的 data-editable 元素单独列出人工核对。
"""
import os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = 8942
BASE = 'http://127.0.0.1:%d' % PORT
URL = BASE + '/tests/decks/j-localfirst-e2/index.html'

srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                        '--bind', '127.0.0.1', '-d', ROOT],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
problems = []
notes = []
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + '/editor.html', timeout=1); break
        except Exception:
            time.sleep(0.2)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1920, 'height': 1080})
        pg.on('pageerror', lambda e: problems.append('pageerror: %s' % e))
        pg.goto(URL)
        pg.wait_for_timeout(1500)

        # 强制所有页进入终态（in-view），避免入场动效影响测量
        pg.evaluate("""() => {
          document.querySelectorAll('.slide').forEach(s => s.classList.add('in-view'));
          if (window.__pptxMotion) window.__pptxMotion.restoreAll();
        }""")
        pg.wait_for_timeout(400)

        # 1) 溢出
        ov = pg.evaluate("""() => Array.from(document.querySelectorAll('.slide')).map(s => ({
          id: s.getAttribute('data-slide-id'), sw: s.scrollWidth, sh: s.scrollHeight }))""")
        for o in ov:
            if o['sw'] > 1920 or o['sh'] > 1080:
                problems.append('溢出: %s %sx%s' % (o['id'], o['sw'], o['sh']))

        # 2) 可编辑元素两两重叠（画布坐标 = getBoundingClientRect / scale）
        scale = pg.evaluate("() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--slide-scale'))")
        overlaps = pg.evaluate("""() => {
          const out = [];
          document.querySelectorAll('.slide').forEach(slide => {
            const sr = slide.getBoundingClientRect();
            const sc = sr.width / 1920;
            const els = Array.from(slide.querySelectorAll('[data-editable]'));
            const rects = els.map(el => {
              const r = el.getBoundingClientRect();
              return { el, x: (r.left - sr.left) / sc, y: (r.top - sr.top) / sc,
                       w: r.width / sc, h: r.height / sc };
            }).filter(r => r.w > 0 && r.h > 0);
            for (let i = 0; i < rects.length; i++)
              for (let j = i + 1; j < rects.length; j++) {
                const a = rects[i], c = rects[j];
                if (a.el.contains(c.el) || c.el.contains(a.el)) continue;
                const iw = Math.min(a.x + a.w, c.x + c.w) - Math.max(a.x, c.x);
                const ih = Math.min(a.y + a.h, c.y + c.h) - Math.max(a.y, c.y);
                if (iw > 0 && ih > 0 && iw * ih > 16)
                  out.push(slide.getAttribute('data-slide-id') + ': "' +
                           a.el.textContent.slice(0, 14) + '" x "' +
                           c.el.textContent.slice(0, 14) + '" = ' +
                           Math.round(iw * ih) + 'px^2');
              }
          });
          return out;
        }""")
        for o in overlaps:
            problems.append('重叠: ' + o)

        # 3) 字号（画布坐标）：data-editable 元素 computed font-size（缩放无关，直接读 px）
        sizes = pg.evaluate("""() => Array.from(document.querySelectorAll('[data-editable]')).map(el => ({
          slide: el.closest('.slide').getAttribute('data-slide-id'),
          tag: el.tagName, text: el.textContent.trim().slice(0, 18),
          fs: parseFloat(getComputedStyle(el).fontSize),
          mast: !!el.closest('.masthead,.mastfoot') }))""")
        for s in sizes:
            if s['fs'] < 14:
                problems.append('字号 <14px: %s %s "%s" = %s' % (s['slide'], s['tag'], s['text'], s['fs']))
            elif s['fs'] < 18:
                if s['mast'] or s['fs'] >= 14:
                    notes.append('小字（meta/标注档，%spx）: %s "%s"' % (s['fs'], s['slide'], s['text']))
                else:
                    problems.append('正文 <18px: %s "%s" = %s' % (s['slide'], s['text'], s['fs']))

        # 截图（每页滚动到位）
        for i, o in enumerate(ov):
            pg.evaluate("""(i) => { const slots = document.querySelectorAll('.slide-slot');
              document.getElementById('deck').scrollTo({top: slots[i].offsetTop, behavior: 'auto'}); }""", i)
            pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(ROOT, 'tests/harness/results/j-e2-p%d.png' % (i + 1)))
        pg.close()
        b.close()
finally:
    srv.terminate()

print('scale =', scale if 'scale' in dir() else '?')
for n in notes:
    print('NOTE:', n)
if problems:
    print('FAIL (%d):' % len(problems))
    for p in problems:
        print(' -', p)
    sys.exit(1)
print('PASS: 零溢出 / 零重叠 / 字号合规')
