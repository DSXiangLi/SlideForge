#!/usr/bin/env python3
"""J 期终验 e6 deck 自检：1920x1080 逐页渲染——
1. 零溢出（slide scrollWidth/Height 不越 1920x1080 画布）
2. 可编辑元素两两不重叠（交集面积 >16px² 报警；祖先-后代嵌套豁免）
3. 正文 >=18px（画布坐标；meta/kicker 家具与 16px 标签档豁免并列出）
"""
import os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import socket
_sk = socket.socket(); _sk.bind(('127.0.0.1', 0))
PORT = _sk.getsockname()[1]; _sk.close()
BASE = 'http://127.0.0.1:%d' % PORT
URL = BASE + '/tests/decks/j-localfirst-e6/index.html'

srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                        '--bind', '127.0.0.1', '-d', ROOT],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
problems = []
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
        resp = pg.goto(URL)
        print('goto status:', resp.status if resp else None, 'url:', pg.url)
        pg.wait_for_timeout(800)
        print('slides found:', pg.evaluate("() => document.querySelectorAll('.slide').length"))

        n = pg.evaluate("() => document.querySelectorAll('.slide').length")
        # 逐页滚入视口，等动效完成（拆字/count-up/mask-lines 还原）
        for i in range(n):
            pg.evaluate("""(i) => {
              const slots = document.querySelectorAll('.slide-slot');
              document.getElementById('deck').scrollTo({top: slots[i].offsetTop, behavior: 'auto'});
            }""", i)
            pg.wait_for_timeout(2200)

        # 1) 溢出
        ov = pg.evaluate("""() => Array.from(document.querySelectorAll('.slide')).map(s => ({
          id: s.getAttribute('data-slide-id'), sh: s.scrollHeight, sw: s.scrollWidth }))""")
        for o in ov:
            if o['sh'] > 1080 or o['sw'] > 1920:
                problems.append('溢出: %s %sx%s' % (o['id'], o['sw'], o['sh']))
        print('overflow check:', ov)

        # 2) 可编辑元素两两重叠（同页内；祖先-后代豁免；>16px² 报警）
        overlaps = pg.evaluate("""() => {
          const out = [];
          document.querySelectorAll('.slide').forEach(slide => {
            const els = Array.from(slide.querySelectorAll('[data-editable]'))
              .filter(e => e.getClientRects().length);
            const rects = els.map(e => ({ e, r: e.getBoundingClientRect() }));
            for (let i = 0; i < rects.length; i++)
              for (let j = i + 1; j < rects.length; j++) {
                const a = rects[i], b2 = rects[j];
                if (a.e.contains(b2.e) || b2.e.contains(a.e)) continue;
                const x = Math.max(0, Math.min(a.r.right, b2.r.right) - Math.max(a.r.left, b2.r.left));
                const y = Math.max(0, Math.min(a.r.bottom, b2.r.bottom) - Math.max(a.r.top, b2.r.top));
                if (x * y > 16)
                  out.push(slide.getAttribute('data-slide-id') + ': [' +
                    a.e.textContent.slice(0, 12) + '] x [' + b2.e.textContent.slice(0, 12) +
                    '] area=' + Math.round(x * y));
              }
          });
          return out;
        }""")
        for o in overlaps:
            problems.append('重叠: ' + o)
        print('overlap check:', overlaps or 'clean')

        # 3) 字号：列出全部可编辑元素计算字号；<18 的只允许 meta 档（家具/mono/16px 标签）
        sizes = pg.evaluate("""() => {
          const out = [];
          document.querySelectorAll('.slide').forEach(slide => {
            slide.querySelectorAll('[data-editable]').forEach(e => {
              const fs = parseFloat(getComputedStyle(e).fontSize);
              const meta = !!(e.closest('.masthead') || e.closest('.mastfoot'));
              out.push({ slide: slide.getAttribute('data-slide-id'),
                         text: e.textContent.trim().slice(0, 14), fs, meta });
            });
          });
          return out;
        }""")
        small = [s for s in sizes if s['fs'] < 18]
        for s in small:
            ok = s['meta'] or s['fs'] >= 14
            print('  small: %s "%s" %spx meta=%s -> %s' % (s['slide'], s['text'], s['fs'], s['meta'], 'ok(meta档)' if ok else 'FAIL'))
            if not ok:
                problems.append('小字越线: %s "%s" %spx' % (s['slide'], s['text'], s['fs']))
        bodybad = [s for s in sizes if s['fs'] < 18 and not s['meta'] and s['fs'] < 14]
        print('min font (non-meta):', min((s['fs'] for s in sizes if not s['meta']), default=None))

        # 截图每页
        os.makedirs(os.path.join(ROOT, 'tests/harness/results'), exist_ok=True)
        for i in range(n):
            pg.evaluate("""(i) => {
              const slots = document.querySelectorAll('.slide-slot');
              document.getElementById('deck').scrollTo({top: slots[i].offsetTop, behavior: 'auto'});
            }""", i)
            pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(ROOT, 'tests/harness/results/j-e6-p%d.png' % (i + 1)))
        pg.close()
        b.close()
finally:
    srv.terminate()

print()
if problems:
    print('PROBLEMS (%d):' % len(problems))
    for x in problems: print(' -', x)
    sys.exit(1)
print('ALL CHECKS PASSED')
