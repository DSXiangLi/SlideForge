#!/usr/bin/env python3
"""j-localfirst-e2 几何抽验：P5 节点框位置 vs SVG 连线端点；重叠检查阳性对照。"""
import os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = 8943
BASE = 'http://127.0.0.1:%d' % PORT

srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                        '--bind', '127.0.0.1', '-d', ROOT],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + '/editor.html', timeout=1); break
        except Exception:
            time.sleep(0.2)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1920, 'height': 1080})
        pg.goto(BASE + '/tests/decks/j-localfirst-e2/index.html')
        pg.wait_for_timeout(1200)
        pg.evaluate("() => { document.querySelectorAll('.slide').forEach(s => s.classList.add('in-view')); }")
        pg.wait_for_timeout(300)
        g = pg.evaluate("""() => {
          const slide = document.querySelector('[data-slide-id="sync-flow"]');
          const wrap = slide.querySelector('[data-ig="sequence-snake"]');
          const sr = slide.getBoundingClientRect();
          const sc = sr.width / 1920;
          const wr = wrap.getBoundingClientRect();
          const boxes = Array.from(wrap.querySelectorAll('[data-ig-item]')).map(el => {
            const r = el.getBoundingClientRect();
            return { x: (r.left - sr.left)/sc, y: (r.top - sr.top)/sc, w: r.width/sc, h: r.height/sc };
          });
          return { wrap: { x: (wr.left - sr.left)/sc, y: (wr.top - sr.top)/sc, w: wr.width/sc, h: wr.height/sc }, boxes };
        }""")
        print('snake 容器:', g['wrap'])
        # DOM 序 01..06；行2 视觉反转。连线端点期望（相对 snake 容器原点）：
        # 行1 框缘 x: 130-430 / 690-990 / 1250-1550；行1 中心 y=46；行2 中心 y=238（按 288 视图高 + none 拉伸）
        for i, bx in enumerate(g['boxes']):
            rel_y1 = bx['y'] - g['wrap']['y']
            print('节点%02d: 相对容器 x=%.0f..%.0f y=%.0f..%.0f 中心y=%.1f' % (
                i+1, bx['x']-g['wrap']['x'], bx['x']-g['wrap']['x']+bx['w'],
                rel_y1, rel_y1+bx['h'], rel_y1+bx['h']/2))
        # 阳性对照：临时让两个元素重叠，确认检查能抓到
        pg.evaluate("""() => { const a = document.querySelector('[data-slide-id="compare"] [data-ig-item] p:nth-of-type(2)');
          a.style.position='absolute'; a.style.top='0'; a.style.left='0'; }""")
        ov = pg.evaluate("""() => {
          const out = [];
          const slide = document.querySelector('[data-slide-id="compare"]');
          const sr = slide.getBoundingClientRect(); const sc = sr.width/1920;
          const els = Array.from(slide.querySelectorAll('[data-editable]'));
          const rects = els.map(el => { const r = el.getBoundingClientRect();
            return { el, x:(r.left-sr.left)/sc, y:(r.top-sr.top)/sc, w:r.width/sc, h:r.height/sc }; });
          for (let i=0;i<rects.length;i++) for (let j=i+1;j<rects.length;j++){
            const a=rects[i], c=rects[j];
            if (a.el.contains(c.el) || c.el.contains(a.el)) continue;
            const iw=Math.min(a.x+a.w,c.x+c.w)-Math.max(a.x,c.x);
            const ih=Math.min(a.y+a.h,c.y+c.h)-Math.max(a.y,c.y);
            if (iw>0 && ih>0 && iw*ih>16) out.push(iw*ih|0);
          }
          return out;
        }""")
        print('阳性对照（应非空）:', ov)
        b.close()
finally:
    srv.terminate()
