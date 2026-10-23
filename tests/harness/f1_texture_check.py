#!/usr/bin/env python3
"""F1 最小验证：culture-kraft-v2 换入 A4 新 G3 纸纹 token 后，
质感层生效且无溢出；skeleton v4 家具/配给结构渲染无回归。"""
import subprocess, sys, time, urllib.request, os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = 8931
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

        # --- 1. culture-kraft-v2：A4 纸纹 token 置换 ---
        pg = b.new_page(viewport={'width': 1440, 'height': 900})
        pg.on('pageerror', lambda e: problems.append('pageerror: %s' % e))
        pg.goto('%s/tests/decks/culture-kraft-v2/index.html' % BASE)
        pg.wait_for_timeout(1200)
        tx = pg.evaluate("""() => ({
          cover: getComputedStyle(document.querySelector('.slide.cover-page') || document.querySelector('.slide'), '::before').backgroundImage.slice(0, 60),
          plain: getComputedStyle(document.querySelectorAll('.slide')[2], '::before').backgroundImage.slice(0, 60),
          htmlCls: document.documentElement.className })""")
        if 'svg' not in tx['cover'] and 'gradient' not in tx['cover']:
            problems.append('封面质感层未生效：%r' % tx['cover'])
        if 'svg' not in tx['plain'] and 'gradient' not in tx['plain']:
            problems.append('正文页质感层未生效（scope:all）：%r' % tx['plain'])
        ov = pg.evaluate("""() => Array.from(document.querySelectorAll('.slide')).map(s => ({
          id: s.getAttribute('data-slide-id'), sh: s.scrollHeight, sw: s.scrollWidth }))""")
        for o in ov:
            if o['sh'] > 1080 or o['sw'] > 1920:
                problems.append('页面溢出：%s %sx%s' % (o['id'], o['sw'], o['sh']))
        pg.screenshot(path=os.path.join(ROOT, 'tests/harness/results/f1-texture-a4.png'), full_page=False)
        pg.close()

        # --- 2. skeleton v4 本体：家具渲染 + 配给 CSS 合法 ---
        pg2 = b.new_page(viewport={'width': 1440, 'height': 900})
        pg2.on('pageerror', lambda e: problems.append('skeleton pageerror: %s' % e))
        pg2.goto('%s/skills/html-pptx/assets/skeleton.html' % BASE)
        pg2.wait_for_timeout(1000)
        sk = pg2.evaluate("""() => ({
          ver: document.querySelector('meta[name="skeleton-version"]').content,
          masthead: !!document.querySelector('.masthead'),
          mastfoot: !!document.querySelector('.mastfoot'),
          mhStyle: getComputedStyle(document.querySelector('.masthead')).textTransform,
          mfBorder: getComputedStyle(document.querySelector('.mastfoot')).borderTopWidth,
          coverBg: getComputedStyle(document.querySelector('.slide.cover-page'), '::before').backgroundImage,
          plainBg: getComputedStyle(document.querySelectorAll('.slide')[1], '::before').backgroundImage })""")
        if sk['ver'] != '4': problems.append('骨架版本=%s' % sk['ver'])
        if not (sk['masthead'] and sk['mastfoot']): problems.append('示例页家具缺失')
        if sk['mhStyle'] != 'uppercase': problems.append('家具大写样式未生效：%r' % sk['mhStyle'])
        if sk['mfBorder'] != '1px': problems.append('页脚 hairline 未生效：%r' % sk['mfBorder'])
        if sk['coverBg'] != 'none' or sk['plainBg'] != 'none':
            problems.append('默认主题（无质感 token）质感层应为 none：cover=%r plain=%r' % (sk['coverBg'], sk['plainBg']))
        pg2.close()
        b.close()
finally:
    srv.terminate()

if problems:
    print('FAIL'); [print(' -', p) for p in problems]; sys.exit(1)
print('PASS: A4 纸纹层封面/正文页生效（scope:all），零溢出；skeleton v4 家具样式生效、默认主题质感层为 none')
print('  证据: cover=%r' % tx['cover'])
print('        plain=%r' % tx['plain'])
print('        截图: tests/harness/results/f1-texture-a4.png')
