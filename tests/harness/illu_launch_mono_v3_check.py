#!/usr/bin/env python3
"""launch-mono-v3 插画 pass 回归：含图页（09 设计 / 11 界面）渲染校验——
图片加载成功、容器构图尺寸不变、全 deck 无溢出。"""
import subprocess, sys, time, urllib.request, os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = 8933
BASE = 'http://127.0.0.1:%d' % PORT

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
        pg = b.new_page(viewport={'width': 1440, 'height': 900})
        pg.on('pageerror', lambda e: problems.append('pageerror: %s' % e))
        pg.goto('%s/tests/decks/launch-mono-v3/index.html' % BASE)
        pg.wait_for_timeout(1500)

        # 1. 两个槽位：加载成功 + src 已换 png + 构图尺寸不变
        imgs = pg.evaluate("""() => Array.from(document.querySelectorAll('img[data-image-slot]')).map(im => ({
          slot: im.getAttribute('data-image-slot'),
          state: im.getAttribute('data-image-state'),
          src: im.getAttribute('src'),
          naturalW: im.naturalWidth, naturalH: im.naturalHeight,
          complete: im.complete,
          w: im.offsetWidth, h: im.offsetHeight }))""")
        expect = {'device-halo-1x1': (1050, 1080), 'interface-panel-1x1': (1080, 1080)}
        for it in imgs:
            print('slot:', it)
            if it['state'] != 'generated':
                problems.append('%s state=%s' % (it['slot'], it['state']))
            if not it['src'].endswith('.png'):
                problems.append('%s src 未换 png：%s' % (it['slot'], it['src']))
            if not it['complete'] or it['naturalW'] == 0:
                problems.append('%s 图片未加载' % it['slot'])
            ew, eh = expect[it['slot']]
            if (it['w'], it['h']) != (ew, eh):
                problems.append('%s 构图尺寸变化：%sx%s（期望 %sx%s）' % (it['slot'], it['w'], it['h'], ew, eh))
        if len(imgs) != 2:
            problems.append('槽位数量=%d（期望 2）' % len(imgs))

        # 2. 全 deck 逐页溢出检查
        ov = pg.evaluate("""() => Array.from(document.querySelectorAll('.slide')).map(s => ({
          id: s.getAttribute('data-slide-id'), sh: s.scrollHeight, sw: s.scrollWidth }))""")
        for o in ov:
            if o['sh'] > 1080 or o['sw'] > 1920:
                problems.append('页面溢出：%s %sx%s' % (o['id'], o['sw'], o['sh']))
        print('slides checked:', len(ov))

        # 3. 含图页截图留证
        for sid, name in [('feature-design', 'p09-design'), ('feature-interface', 'p11-interface')]:
            pg.evaluate("""(sid) => document.querySelector('[data-slide-id="%s"]').scrollIntoView()""" % sid)
            pg.wait_for_timeout(900)
            pg.screenshot(path=os.path.join(ROOT, 'tests/harness/results/illu-%s.png' % name))
        pg.close()
        b.close()
finally:
    srv.terminate()

if problems:
    print('\nFAIL:')
    for x in problems:
        print(' -', x)
    sys.exit(1)
print('\nPASS: launch-mono-v3 插画页渲染零问题')
