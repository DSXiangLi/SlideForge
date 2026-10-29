#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
editor.html 端到端验收（嵌入模式 postMessage 协议）

用法：python3 tests/harness/run_e2e.py
产物：tests/harness/results/（diff、截图、report.json）
退出码：全部 PASS 为 0，任一 FAIL 为 1。

环境事实（Chromium 145 headless 实测）：
- http://127.0.0.1 是安全上下文，iframe 内 showOpenFilePicker/showSaveFilePicker
  均为 function；修复前嵌入态保存会误入 FSAA 路径被静默吞掉（见报告 Bug-1）。
- headless 使用 overlay 滚动条（clientWidth 不含滚动条）。
"""
import difflib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVE = '/tmp/pptx-e2e'
PORT = 8925
BASE = 'http://127.0.0.1:%d' % PORT
RESULTS = os.path.join(ROOT, 'tests/harness/results')

DECKS = ['tech-ikb', 'culture-kraft', 'launch-mono', 'art-botanical', 'density-low', 'density-high', 'infographic-b2', 'charts-a3', 'motion-d2', 'motion-v5', 'infographic-d1', 'tech-ikb-v2', 'culture-kraft-v2', 'launch-mono-v2', 'components-gallery', 'tech-ikb-v3', 'culture-kraft-v3', 'launch-mono-v3', 'j-localfirst-a1', 'j-localfirst-e2', 'j-localfirst-e6', 'smartforge-c1', 'smartforge-e8', 'bake-mix', 'cmb-retail']
VIEW_W, VIEW_H = 1440, 900          # harness 视口

RESULTS_LIST = []

def report(tid, name, ok, evidence=''):
    RESULTS_LIST.append({'id': tid, 'name': name, 'ok': bool(ok), 'evidence': evidence})
    print('%s  %-28s %s' % ('PASS' if ok else 'FAIL', tid + ' ' + name, ('— ' + evidence) if evidence else ''))

def read_deck(deck):
    with open(os.path.join(ROOT, 'tests/decks', deck, 'index.html'), encoding='utf-8') as f:
        return f.read()

# ---------- 环境 ----------

def setup_serve():
    os.makedirs(SERVE, exist_ok=True)
    for name, target in [('editor.html', os.path.join(ROOT, 'editor.html')),
                         ('decks', os.path.join(ROOT, 'tests/decks'))]:
        dst = os.path.join(SERVE, name)
        if os.path.islink(dst):
            os.remove(dst)
        elif os.path.exists(dst):
            shutil.rmtree(dst)
        os.symlink(target, dst)
    shutil.copy(os.path.join(ROOT, 'tests/harness/harness.html'), os.path.join(SERVE, 'harness.html'))
    os.makedirs(RESULTS, exist_ok=True)

def point_assets(deck):
    link = os.path.join(SERVE, 'assets')
    if os.path.islink(link):
        os.remove(link)
    os.symlink(os.path.join(SERVE, 'decks', deck, 'assets'), link)

def unpoint_assets():
    link = os.path.join(SERVE, 'assets')
    if os.path.islink(link):
        os.remove(link)

# ---------- 浏览器辅助 ----------

def fresh_page(browser, width=VIEW_W, height=VIEW_H):
    """每个测试独立 context：隔离 HTTP 缓存与脏状态。"""
    ctx = browser.new_context(viewport={'width': width, 'height': height})
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: print('[pageerror]', e))
    return ctx, pg

def wait_editor_ready(page):
    page.wait_for_function("""() => {
      const w = document.getElementById('ed').contentWindow;
      return w && w.state !== undefined && w.document.getElementById('btnSave');
    }""", timeout=8000)

def editor_frame(page):
    for f in page.frames:
        if f.url.endswith('/editor.html'):
            return f
    raise RuntimeError('editor frame not found')

def deck_frame(page):
    ef = editor_frame(page)
    if ef.child_frames:
        return ef.child_frames[0]
    raise RuntimeError('deck frame not found')

def load_deck(page, html, name, assets_url=None):
    page.evaluate('([h, n, a]) => window.loadDeck(h, n, a)', [html, name, assets_url])
    page.wait_for_function("""() => {
      const w = document.getElementById('ed').contentWindow;
      return w && w.state && w.state.loaded === true && w.registry.length > 0 &&
             w.frame && w.frame.contentDocument &&
             w.frame.contentDocument.querySelectorAll('.slide').length > 0;
    }""", timeout=10000)
    page.wait_for_timeout(400)   # fit() / rAF 稳定

def save_and_capture(page):
    n0 = page.evaluate('window.saveCount()')
    page.frame_locator('#ed').locator('#btnSave').click()
    page.wait_for_function('(n) => window.saveCount() > n', arg=n0, timeout=8000)
    return page.evaluate('window.lastSave().html')

def deck_loc(page, sel):
    return page.frame_locator('#ed').frame_locator('#deckFrame').locator(sel)

def dirty_events(page):
    return page.evaluate('window.dirtyEvents()')

# ---------- 往返 diff 白名单（§5.4 + 实测的一次性解析/序列化规范化） ----------

BOOLEAN_ATTRS = ['data-editable', 'data-editable-image', 'data-editable-skip', 'data-anim', 'data-ig-item', 'data-rotate', 'data-rotate-item', 'hidden']
SVG_VOID = 'circle|ellipse|line|path|polygon|polyline|rect|stop|use'

def _canon_style(m):
    """style 属性规范化（skeleton v2：框架 JS 给 [data-anim] setProperty('--i') 会触发
    CSSOM 整体重序列化该属性——冒号后空格、0.x 前导零、追加 --i、末尾分号）。
    双侧规范化后比较：剥离 --i，声明按 'name:value' 紧排。
    v3 补充（CSSOM 等价简写展开，均双向一致）：flex 简写展开（flex:1 == 1 1 0%、
    flex:none == 0 0 auto）、零值单位（0 == 0px == 0%）、盒简写去重（56px 56px == 56px）、
    函数参数逗号后空格、属性值内单引号被 outerHTML 转义为 &quot;。"""
    decls = []
    raw = m.group(1).replace('&quot;', "'")   # 先还原实体再按 ; 切分（&quot; 自身含分号）
    for d in raw.split(';'):
        d = d.strip()
        if not d or ':' not in d:
            continue
        name, val = d.split(':', 1)
        name = name.strip()
        if name == '--i':
            continue
        val = ' '.join(val.split())
        val = re.sub(r'(?<![\d.])0\.(\d)', r'.\1', val)   # 0.55 -> .55
        val = re.sub(r',\s+', ',', val)                    # repeat(3, 1fr) -> repeat(3,1fr)
        val = re.sub(r'\b0(?:px|%)(?![\w%])', '0', val)    # 0px/0% -> 0（\b 对 % 不成立，用后环视）
        if name == 'flex':
            val = re.sub(r'^(\S+) 1 0$', r'\1', val)       # flex:1 == flex:1 1 0(%)
            if val == '0 0 auto':
                val = 'none'                               # flex:none == 0 0 auto
        if name in ('padding', 'margin'):
            parts = val.split(' ')
            if len(parts) == 4 and parts[0] == parts[2] and parts[1] == parts[3]:
                parts = parts[:2]
            if len(parts) == 2 and parts[0] == parts[1]:
                parts = parts[:1]
            val = ' '.join(parts)
        decls.append('%s:%s' % (name, val))
    return 'style="' + ';'.join(decls) + '"'

def whitelist_norm(t):
    """白名单：布尔属性 ="" 化；chrome 页码重置；HTML parser 对 <head> 前空白的丢弃；
    SVG 自闭合写法展开；</body></html> 周边空白被 parser 移位的规范化；
    skeleton v2 运行时残留（<html> 的 js class、style 属性 CSSOM 重序列化）。"""
    for a in BOOLEAN_ATTRS:
        t = t.replace(' %s=""' % a, ' ' + a)
    t = re.sub(r'(<div class="deck-chrome" id="chrome">)[^<]*(</div>)', r'\1@@\2', t)
    t = t.replace('>\n<head>', '><head>')
    t = t.replace(' class="js"', '')
    t = re.sub(r'<(%s)((?:"[^"]*"|[^">])*?)\s*/>' % SVG_VOID, r'<\1\2></\1>', t)
    t = re.sub(r'style="([^"]*)"', _canon_style, t)
    t = re.sub(r'\s*</body>\s*</html>\s*$', '</body></html>', t)
    return t

def framework_blocks(t):
    style = re.search(r'<style>(.*?)</style>', t, re.S)
    script = re.search(r'<script>(.*?)</script>', t, re.S)
    return (style.group(1) if style else None, script.group(1) if script else None)

def write_diff(a, b, fname):
    diff = list(difflib.unified_diff(a.splitlines(), b.splitlines(),
                                     fromfile='original', tofile='saved', lineterm=''))
    with open(os.path.join(RESULTS, fname), 'w', encoding='utf-8') as f:
        f.write('\n'.join(diff))
    return len(diff)

# ---------- 测试 1：往返幂等（§10.3 / §10.6） ----------

def test_roundtrip(browser, deck):
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')

        saved1 = save_and_capture(page)
        with open(os.path.join(RESULTS, deck + '.roundtrip1.html'), 'w', encoding='utf-8') as f:
            f.write(saved1)

        if src == saved1:
            cls = '零 diff'
        elif whitelist_norm(src) == whitelist_norm(saved1):
            cls = '仅白名单差异'
        else:
            cls = None

        load_deck(page, saved1, deck + '/index.html')
        saved2 = save_and_capture(page)
        idem2 = (saved1 == saved2)

        ndiff = write_diff(src, saved1, deck + '.roundtrip1.diff')

        fs1, fj1 = framework_blocks(src)
        fs2, fj2 = framework_blocks(saved1)
        framework_ok = (fs1 == fs2 and fj1 == fj2)

        no_dirty = (dirty_events(page) == [])

        ok = (cls is not None) and idem2 and framework_ok and no_dirty
        ev = '首趟 %s（diff %d 行）；第二趟%s；框架层%s；脏事件%s' % (
            cls or '存在非白名单差异', ndiff,
            '逐字节相等' if idem2 else '不相等',
            '逐字节一致' if framework_ok else '被改动',
            dirty_events(page) or '无')
        report('T1-' + deck, '往返幂等', ok, ev)
    finally:
        ctx.close()

# ---------- 测试 2/3 的产物净化检查 ----------

def assert_clean_output(deck, saved, extra_checks):
    """§5.4 五条：检查运行时/编辑态残留。注意 --slide-scale、in-view 字样
    合法存在于框架 CSS/JS 文本中，必须查属性位而非全文子串。"""
    problems = []
    if re.search(r'<html[^>]*\sstyle\s*=', saved):
        problems.append('<html> 残留 style（--slide-scale 未归位）')
    if re.search(r'class="[^"]*\bin-view\b', saved):
        problems.append('class 残留 in-view')
    for bad in ['contenteditable', 'ed-selected', 'ed-hover', 'ed-editing', 'data-editor-injected']:
        if bad in saved:
            problems.append('残留 ' + bad)
    if re.search(r'src="[^"]*\?v=', saved):
        problems.append('img src 残留 ?v=')
    m = re.search(r'<div class="deck-chrome" id="chrome">([^<]*)</div>', saved)
    src = read_deck(deck)
    n_slides = len(re.findall(r'data-slide-id="', src))
    if not m or m.group(1) != '1 / %d' % n_slides:
        problems.append('chrome 页码=%s，期望 1 / %d' % (m.group(1) if m else None, n_slides))
    if saved.count('data-slide-id="') != n_slides:
        problems.append('data-slide-id 数量变化')
    for label, cond in extra_checks:
        if not cond:
            problems.append(label)
    return problems

# ---------- 测试 2：编辑端到端（§10.2 文字部分） ----------

def test_edit_tech_ikb(browser):
    deck = 'tech-ikb'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')

        # --- 2a. 单行文字：两段手势 + Ctrl+Enter 确认 ---
        h1 = deck_loc(page, '[data-slide-id="cover"] h1[data-editable]')
        h1.scroll_into_view_if_needed()
        h1.click()
        cls_after_1 = h1.get_attribute('class') or ''
        ce_after_1 = h1.get_attribute('contenteditable')
        first_strike_ok = ('ed-selected' in cls_after_1) and (ce_after_1 is None)
        h1.click()
        ce_after_2 = h1.get_attribute('contenteditable')
        ws_during_edit = deck_frame(page).evaluate(
            '''() => getComputedStyle(document.querySelector('[data-slide-id="cover"] h1[data-editable]')).whiteSpace''')
        page.keyboard.type('微服务三年：架构演进实录')
        page.keyboard.press('Control+Enter')
        ce_after_commit = h1.get_attribute('contenteditable')
        cls_after_commit = h1.get_attribute('class') or ''
        ok1 = (first_strike_ok and ce_after_2 == 'plaintext-only'
               and ce_after_commit is None and 'ed-selected' in cls_after_commit
               and ws_during_edit == 'pre-wrap')

        # --- 2b. 多行编辑：Enter 换行，点击另一元素确认 ---
        h2 = deck_loc(page, '[data-slide-id="monolith-origin"] h2[data-editable]')
        h2.scroll_into_view_if_needed()
        h2.click(); h2.click()
        page.keyboard.type('单体不是错误')
        page.keyboard.press('Enter')
        page.keyboard.type('是那个阶段最对的选择')
        h1.click()   # 点击另一可编辑元素 → 提交 h2
        page.wait_for_timeout(200)
        h2_html = deck_frame(page).evaluate(
            '''() => document.querySelector('[data-slide-id="monolith-origin"] h2[data-editable]').innerHTML''')
        multiline_is_br = '单体不是错误<br>是那个阶段最对的选择' in h2_html
        multiline_is_raw_nl = '单体不是错误\n是那个阶段最对的选择' in h2_html

        dev = dirty_events(page)

        # --- 2c. 保存并检验产物 ---
        saved = save_and_capture(page)
        with open(os.path.join(RESULTS, deck + '.edited.html'), 'w', encoding='utf-8') as f:
            f.write(saved)
        problems = assert_clean_output(deck, saved, [
            ('单行修改未生效', '微服务三年：架构演进实录' in saved),
            ('多行修改未生效', '单体不是错误' in saved and '是那个阶段最对的选择' in saved),
            ('多行未以 <br> 持久化（重开丢换行）', '单体不是错误<br>是那个阶段最对的选择' in saved),
        ])
        dev2 = dirty_events(page)
        dirty_seq_ok = (dev == [True] and dev2 == [True, False])
        if not dirty_seq_ok:
            problems.append('脏事件序列异常 %r -> %r' % (dev, dev2))

        ev = '两段手势%s（首击 class=%r ce=%r；二击 ce=%r white-space=%s） | 多行提交后 innerHTML=%s | 产物：%s | 脏事件 %s' % (
            '正确' if ok1 else '异常', cls_after_1, ce_after_1, ce_after_2, ws_during_edit,
            '<br>（正确）' if multiline_is_br else ('原始 \\n（换行将丢失）' if multiline_is_raw_nl else '其他: ' + h2_html),
            '干净' if not problems else '；'.join(problems), dev2)
        report('T2-tech-ikb', '编辑端到端', ok1 and multiline_is_br and not problems, ev)
    finally:
        ctx.close()

def test_edit_culture_kraft(browser):
    deck = 'culture-kraft'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')

        sel = '[data-slide-id="key-terms"] h3[data-editable]'
        h3 = deck_loc(page, sel + ':has-text("礼治秩序")')
        h3.scroll_into_view_if_needed()
        page.wait_for_timeout(300)

        # 首击不得改变布局（§5.1 防截断释放）。用 offsetWidth/Height（布局整数，
        # 不受滚动位置影响；bounding_box 是视口坐标且亚像素，会被 scroll-snap 微调干扰）
        size_js = '''() => {
          const e = [...document.querySelectorAll('%s')].find(x => x.textContent.includes('礼治秩序'));
          return [e.offsetWidth, e.offsetHeight];
        }''' % sel
        box0 = deck_frame(page).evaluate(size_js)
        h3.click()
        box1 = deck_frame(page).evaluate(size_js)
        layout_stable = (box0 == box1) and (h3.get_attribute('contenteditable') is None)

        # 二击进入编辑，输入加长文本
        h3.click()
        ce = h3.get_attribute('contenteditable')
        page.keyboard.type('礼治秩序与现代社会的治理逻辑')
        # 真实失焦路径：点击编辑器 iframe 之外（宿主页面区域）
        page.locator('#outside').click()
        page.wait_for_timeout(300)
        committed = h3.get_attribute('contenteditable') is None

        saved = save_and_capture(page)
        with open(os.path.join(RESULTS, deck + '.edited.html'), 'w', encoding='utf-8') as f:
            f.write(saved)
        problems = assert_clean_output(deck, saved, [
            ('窄文本框加长文本未生效', '礼治秩序与现代社会的治理逻辑</h3>' in saved),
        ])
        ev = '首击布局%s（offset %s -> %s）；二击 ce=%r；点击编辑器外失焦提交%s；产物%s' % (
            '稳定' if layout_stable else '发生变化', box0, box1, ce,
            '成功' if committed else '失败（ce 仍在）',
            '干净' if not problems else '；'.join(problems))
        report('T2-culture-kraft', '窄文本框加长编辑',
               layout_stable and ce == 'plaintext-only' and committed and not problems, ev)
    finally:
        ctx.close()

# ---------- 测试 3：Esc 取消（§5.1） ----------

def test_esc_cancel(browser):
    deck = 'culture-kraft'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')

        h2 = deck_loc(page, '[data-slide-id="key-terms"] h2[data-editable]')
        h2.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        orig = h2.inner_text()
        h2.click(); h2.click()
        page.keyboard.type('这段文字应当被Esc取消掉')
        page.keyboard.press('Escape')
        page.wait_for_timeout(200)
        after = h2.inner_text()
        dirty = editor_frame(page).evaluate('window.state.dirty')
        dev = dirty_events(page)
        saved = save_and_capture(page)
        junk_in_save = '这段文字应当被Esc取消掉' in saved

        ok = (after == orig) and (dirty is False) and (dev == []) and (not junk_in_save)
        report('T3-esc', 'Esc 取消还原', ok,
               '还原%s；dirty=%s；脏事件=%r；保存产物%s' % (
                   '一致' if after == orig else '不一致(%r vs %r)' % (orig, after),
                   dirty, dev, '无残留' if not junk_in_save else '含已取消文本'))
    finally:
        ctx.close()

# ---------- 测试 4：渲染一致性（§10.1） ----------
#
# 判定口径：§10.1 要求"无文字重叠、无错位、无异常空白"——即布局一致。
# 实测发现：Chromium 对 iframe 内文档的合成路径与顶层文档不同，fixed 定位的
# 小字号 chrome 文本会出现亚像素抗锯齿差异（裸 iframe、无任何编辑层注入的
# 对照组差异完全相同，325 通道像素 / 356 万，bbox 仅覆盖 chrome 页码）。
# 因此验收标准 = 布局指标（slide 位置尺寸）逐页精确一致 + 像素差在抗锯齿量级内。

PIXEL_TOLERANCE_RATIO = 0.002   # 抗锯齿容差：差异通道像素 ≤ 总量 0.2%

RECT_JS = """() => Array.from(document.querySelectorAll('.slide-slot')).map(s => {
  const r = s.getBoundingClientRect();
  return [Math.round(r.x*1000), Math.round(r.y*1000), Math.round(r.width*1000), Math.round(r.height*1000)];
})"""

def wait_images(frame):
    frame.wait_for_function(
        '() => Array.from(document.images).every(i => i.complete)',
        timeout=8000)

def pixel_diff(png_a, png_b):
    ia, ib = Image.open(io.BytesIO(png_a)), Image.open(io.BytesIO(png_b))
    if ia.size != ib.size:
        return None, 1, '尺寸不同 %s vs %s' % (ia.size, ib.size)
    diff = ImageChops.difference(ia.convert('RGB'), ib.convert('RGB'))
    total = ia.size[0] * ia.size[1] * 3
    bbox = diff.getbbox()
    if bbox is None:
        return 0, total, '逐像素一致'
    hist = diff.histogram()
    nonzero = total - hist[0] - hist[256] - hist[512]
    return nonzero, total, '差异通道像素 %d / %d（%.4f%%，bbox %s）' % (
        nonzero, total, nonzero * 100.0 / total, bbox)

def test_render(browser, deck):
    point_assets(deck)
    src = read_deck(deck)
    # 编辑器侧：测量 deck iframe 实际视口（headless 下 stage 宽度有 1px 取整差，须实测）
    ctx, page = fresh_page(browser)
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')
        w, h = deck_frame(page).evaluate(
            '[document.documentElement.clientWidth, document.documentElement.clientHeight]')
        wait_images(deck_frame(page))
        page.wait_for_timeout(1500)
        shot_editor = page.frame_locator('#ed').locator('#deckFrame').screenshot()
        rects_editor = deck_frame(page).evaluate(RECT_JS)
    finally:
        ctx.close()
    # 直开侧：视口精确等于编辑器内 deck iframe 视口
    ctx2, d = fresh_page(browser, w, h)
    try:
        d.goto('%s/decks/%s/index.html' % (BASE, deck))
        wait_images(d)
        d.wait_for_timeout(1500)
        shot_direct = d.screenshot()
        d.wait_for_timeout(400)
        stable = (d.screenshot() == shot_direct)
        rects_direct = d.evaluate(RECT_JS)
    finally:
        ctx2.close()

    open(os.path.join(RESULTS, deck + '.direct.png'), 'wb').write(shot_direct)
    open(os.path.join(RESULTS, deck + '.editor.png'), 'wb').write(shot_editor)

    layout_equal = (rects_direct == rects_editor)
    n, total, desc = pixel_diff(shot_direct, shot_editor)
    pixel_ok = (n is not None) and (n <= total * PIXEL_TOLERANCE_RATIO)
    ok = stable and layout_equal and pixel_ok
    report('T4-' + deck, '渲染一致性', ok,
           '视口 %dx%d；布局指标%s；直开截图稳定性=%s；像素 %s（抗锯齿容差内=%s）' % (
               w, h, '逐页一致' if layout_equal else '不一致！', '稳定' if stable else '不稳定',
               desc, pixel_ok))

# ---------- 测试 5：srcdoc base URL 与 assets 相对路径（§8 assetsUrl） ----------

def test_assets_base(browser):
    deck = 'tech-ikb'
    unpoint_assets()   # 模拟 editor.html 与 deck 不同目录
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    try:
        # (a) 不传 assetsUrl：相对路径按 editor.html 所在目录解析 → 图坏（已知限制，
        #     独立模式下无解——FSAA 文件句柄不暴露路径；嵌入模式宿主应传 assetsUrl）
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')
        page.wait_for_timeout(800)
        imgs = deck_frame(page).evaluate(
            '() => Array.from(document.images).map(i => ({src: i.src, ok: i.complete && i.naturalWidth > 0}))')
        broken = [i for i in imgs if not i['ok']]
        limitation_confirmed = len(broken) == len(imgs) and len(imgs) > 0

        # (b) 传 assetsUrl：图片应正常加载；且注入的 <base> 不得进入保存产物
        load_deck(page, src, deck + '/index.html',
                  '%s/decks/%s/' % (BASE, deck))
        wait_images(deck_frame(page))
        imgs2 = deck_frame(page).evaluate(
            '() => Array.from(document.images).map(i => i.complete && i.naturalWidth > 0)')
        assets_url_ok = bool(imgs2) and all(imgs2)
        saved = save_and_capture(page)
        base_leaked = '<base' in saved

        ok = assets_url_ok and not base_leaked
        report('T5-assets-base', 'assets 路径与 assetsUrl', ok,
               '无 assetsUrl 时 %d/%d 图加载失败（%s，宿主须传 assetsUrl）；'
               '传 assetsUrl 后 %d/%d 图正常；保存产物%s <base>' % (
                   len(broken), len(imgs),
                   '限制确认' if limitation_confirmed else '与预期不符',
                   sum(1 for x in imgs2 if x), len(imgs2),
                   '不含' if not base_leaked else '泄漏'))
    finally:
        ctx.close()
        point_assets(deck)

# ---------- 测试 6：独立模式非修复路径（saveDeck 改动不影响 standalone） ----------

def test_standalone(browser):
    """saveDeck 的嵌入分支改动不得影响独立模式：embedded=false 时
    不得向 parent postMessage；编辑与脏状态逻辑保持原样。
    （FSAA 直写路径 headless 无法交互验证，按任务约定不测。）"""
    deck = 'tech-ikb'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    try:
        page.goto(BASE + '/editor.html')   # 顶层打开 → 独立模式
        page.wait_for_function('() => window.state && window.state.embedded === false')
        page.evaluate('''() => {
          window.__msgs = [];
          window.addEventListener('message', m => window.__msgs.push(m.data));
        }''')
        page.evaluate('(h) => window.openHtml(h, "tech-ikb/index.html", null)', src)
        page.wait_for_function(
            '() => window.state.loaded && window.registry.length > 0 && '
            'window.frame.contentDocument.querySelectorAll(".slide").length > 0')
        page.wait_for_timeout(400)

        # 独立模式下编辑正常工作
        h1 = page.frame_locator('#deckFrame').locator('[data-slide-id="cover"] h1[data-editable]')
        h1.click(); h1.click()
        page.keyboard.type('独立模式编辑验证')
        page.keyboard.press('Control+Enter')
        dirty = page.evaluate('window.state.dirty')
        # 点保存：embedded=false → 绝不走 postMessage（FSAA 直写 headless 不可交互，可能挂起/静默中止）
        page.locator('#btnSave').click()
        page.wait_for_timeout(1200)
        msgs = page.evaluate('window.__msgs')
        no_post = not any(m and isinstance(m, dict) and m.get('type') == 'pptx-html:save' for m in msgs)
        no_throw = True   # 有未捕获异常会触发 pageerror 打印

        report('T6-standalone', '独立模式非修复路径', dirty is True and no_post and no_throw,
               '编辑后 dirty=%s；保存未向 parent postMessage=%s（收到 %d 条消息）' % (dirty, no_post, len(msgs)))
    finally:
        ctx.close()

# ---------- 测试 7/8：批注（§11.7 / §11.8） ----------

RESOLVER_JS = """([slide, path]) => {
  const slideEl = document.querySelector('.slide[data-slide-id="' + slide + '"]');
  if (!slideEl) return null;
  let cur = slideEl;
  for (const part of path.split('>')){
    const m = /^([a-z0-9]+)\\.(\\d+)$/.exec(part);
    if (!m) return null;
    const child = cur.children[+m[2]];
    if (!child || child.tagName.toLowerCase() !== m[1]) return null;
    cur = child;
  }
  return cur.hasAttribute('data-editable-image')
    ? (cur.getAttribute('src') || '').split('?')[0]
    : (cur.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 40);
}"""

def deck_client_rects(page, selectors):
    """deck iframe 内元素的 client 坐标 rect 列表。"""
    return deck_frame(page).evaluate("""(sels) => sels.map(s => {
      const el = document.querySelector(s);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {x: r.x, y: r.y, w: r.width, h: r.height};
    })""", selectors)

def to_page_rects(page, client_rects):
    box = page.frame_locator('#ed').locator('#deckFrame').bounding_box()
    return [{'x': box['x'] + r['x'], 'y': box['y'] + r['y'],
             'w': r['w'], 'h': r['h']} for r in client_rects]

def union_rect(rects, pad=6):
    x0 = min(r['x'] for r in rects) - pad
    y0 = min(r['y'] for r in rects) - pad
    x1 = max(r['x'] + r['w'] for r in rects) + pad
    y1 = max(r['y'] + r['h'] for r in rects) + pad
    return (x0, y0, x1, y1)

def marquee_drag(page, rect):
    x0, y0, x1, y1 = rect
    page.mouse.move(x0, y0)
    page.mouse.down()
    page.mouse.move(x1, y1, steps=8)
    page.mouse.up()

def anno_mask_open(page):
    return editor_frame(page).evaluate(
        "document.getElementById('annoMask').classList.contains('show')")

def test_annotation_e2e(browser):
    """§11.7：跨两文本框+一图框选 → 弹窗清单 → 剔除误选 → 提交 →
    导出 JSON 三层引用回验 → 保存产物无批注痕迹 → 删除。"""
    deck = 'tech-ikb'
    point_assets(deck)
    src = read_deck(deck)
    ctx = browser.new_context(viewport={'width': VIEW_W, 'height': VIEW_H},
                              permissions=['clipboard-read', 'clipboard-write'])
    page = ctx.new_page()
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')

        # 切到批注模式
        page.frame_locator('#ed').locator('#viewSeg button[data-view="annotate"]').click()
        if editor_frame(page).evaluate('window.mode') != 'annotate':
            problems.append('模式切换失败')

        # 滚动到 slide 2（monolith-origin）
        deck_frame(page).evaluate("""() => {
          const deck = document.querySelector('.deck');
          const slot = document.querySelectorAll('.slide-slot')[1];
          deck.scrollTop = slot.offsetTop;
        }""")
        page.wait_for_timeout(400)

        # 框选 h2 + p×2 + img 的并集
        client_rects = deck_frame(page).evaluate("""() => {
          const els = [
            document.querySelector('[data-slide-id="monolith-origin"] h2[data-editable]'),
            ...document.querySelectorAll('[data-slide-id="monolith-origin"] p[data-editable]'),
            document.querySelector('[data-slide-id="monolith-origin"] img[data-editable-image]')
          ];
          return els.map(el => { const r = el.getBoundingClientRect();
            return {x: r.x, y: r.y, w: r.width, h: r.height}; });
        }""")
        page_rects = to_page_rects(page, client_rects)
        marquee_drag(page, union_rect(page_rects))
        page.wait_for_timeout(400)

        # 弹窗应打开，4 行命中
        if not anno_mask_open(page):
            problems.append('框选后弹窗未打开')
            report('T7-annotation', '批注端到端', False, '；'.join(problems))
            return
        rows = page.frame_locator('#ed').locator('.anno-hit-row')
        n_rows = rows.count()
        if n_rows != 4:
            problems.append('命中行数=%d，期望 4' % n_rows)
        row_text = page.frame_locator('#ed').locator('#annoHits').inner_text()
        for expect in ['monolith-origin', '<h2>', '<p>', '<img>', '单体不是错误', 'diagram-monolith.svg']:
            if expect not in row_text:
                problems.append('弹窗清单缺少 %r' % expect)

        # 空批注禁止提交
        submit = page.frame_locator('#ed').locator('#annoSubmit')
        if not submit.is_disabled():
            problems.append('空批注时提交按钮未置灰')

        # 剔除一个误选（第 3 行：第二个 p）
        rows.nth(2).locator('input[type=checkbox]').click()
        page.frame_locator('#ed').locator('#annoText').fill('这三处的口径需要更新为最新数据')
        if submit.is_disabled():
            problems.append('填写批注后提交按钮仍置灰')
        submit.click()
        page.wait_for_timeout(300)

        # 提交后：清单 1 条、3 个角标（编号 1）、未导出提示
        df = deck_frame(page)
        n_badges = df.evaluate("document.querySelectorAll('.anno-badge').length")
        badge_texts = df.evaluate("Array.from(document.querySelectorAll('.anno-badge')).map(b => b.textContent)")
        n_hits = df.evaluate("document.querySelectorAll('.anno-hit').length")
        if n_badges != 3 or badge_texts != ['1', '1', '1']:
            problems.append('角标异常：%d 个，编号 %r' % (n_badges, badge_texts))
        if n_hits != 3:
            problems.append('高亮元素数=%d，期望 3' % n_hits)
        # 角标反缩放补偿（§10.2-1）：computed font-size ≈ 13 / scale
        scale = df.evaluate("parseFloat(document.documentElement.style.getPropertyValue('--slide-scale'))")
        fs = df.evaluate("parseFloat(getComputedStyle(document.querySelector('.anno-badge')).fontSize)")
        if abs(fs - 13 / scale) > 0.6:
            problems.append('角标未反缩放：font-size=%.2f，期望 %.2f' % (fs, 13 / scale))
        unexp = editor_frame(page).evaluate("document.getElementById('annoUnexp').textContent")
        if unexp != '未导出':
            problems.append('未导出提示缺失：%r' % unexp)
        if editor_frame(page).evaluate('window.state.dirty') is not False:
            problems.append('批注置脏了！')
        if dirty_events(page) != []:
            problems.append('批注触发了脏事件：%r' % dirty_events(page))

        # 点击清单项定位：deck 滚动到 slide 2 + 闪烁 class
        page.frame_locator('#ed').locator('.anno-item .txt').click()
        page.wait_for_timeout(200)
        st = df.evaluate("document.querySelector('.deck').scrollTop")
        n_flash = df.evaluate("document.querySelectorAll('.anno-flash').length")
        if not (st > 100 and n_flash == 3):
            problems.append('定位/闪烁异常：scrollTop=%s，flash=%d' % (st, n_flash))

        # 导出：postMessage payload + 剪贴板文本
        n_msg0 = page.evaluate(
            "window.__inbox.filter(m => m && m.type === 'pptx-html:annotations').length")
        page.frame_locator('#ed').locator('#btnSendAnno').click()
        page.wait_for_function(
            '(n) => window.__inbox.filter(m => m && m.type === "pptx-html:annotations").length > n',
            arg=n_msg0, timeout=5000)
        payload = page.evaluate(
            "window.__inbox.filter(m => m && m.type === 'pptx-html:annotations').slice(-1)[0].payload")
        clip = page.evaluate('navigator.clipboard.readText()')
        if '请按以下批注修改' not in clip or '批注 1（页 monolith-origin，3 个元素）' not in clip:
            problems.append('剪贴板自然语言指令格式不符')
        unexp2 = editor_frame(page).evaluate("document.getElementById('annoUnexp').textContent")
        if unexp2 != '':
            problems.append('导出后未清空"未导出"提示')

        # 三层引用回验（§10.3 / §11.7）：slide+path 在原文件中定位，excerpt 一致
        if payload.get('kind') != 'annotation' or len(payload.get('annotations', [])) != 1:
            problems.append('payload 结构异常')
        else:
            anno = payload['annotations'][0]
            if anno['id'] != 'anno-1' or len(anno['targets']) != 3:
                problems.append('批注条目异常：id=%s targets=%d' % (anno.get('id'), len(anno.get('targets', []))))
            ctx2, dp = fresh_page(browser, 1280, 720)
            try:
                dp.goto('%s/decks/%s/index.html' % (BASE, deck))
                dp.wait_for_timeout(600)
                for t in anno['targets']:
                    got = dp.evaluate(RESOLVER_JS, [t['slide'], t['path']])
                    if got is None:
                        problems.append('原文件定位失败：%s / %s' % (t['slide'], t['path']))
                    elif got != t['excerpt']:
                        problems.append('excerpt 不符：%s → %r vs %r' % (t['path'], got, t['excerpt']))
            finally:
                ctx2.close()

        # 保存产物无批注痕迹（§11.7）：且无实质 diff（全程未改正文）
        saved = save_and_capture(page)
        for bad in ['anno-badge', 'anno-hit', 'anno-marquee', 'annoFlash', 'anno-dragging']:
            if bad in saved:
                problems.append('保存产物残留 %s' % bad)
        if whitelist_norm(src) != whitelist_norm(saved):
            problems.append('批注流程导致正文 diff')

        # 删除批注：角标/高亮清除
        page.frame_locator('#ed').locator('.anno-item .del').click()
        page.wait_for_timeout(200)
        left = df.evaluate("document.querySelectorAll('.anno-badge,.anno-hit').length")
        n_items = page.frame_locator('#ed').locator('.anno-item').count()
        if left != 0 or n_items != 0:
            problems.append('删除后残留：badge/hit=%d，清单项=%d' % (left, n_items))

        # 同元素多条批注 → 角标堆叠（§10.2-1）：h2 先入批注 2，再入批注 3
        page_rects2 = to_page_rects(page, deck_client_rects(page, [
            '[data-slide-id="monolith-origin"] h2[data-editable]']))
        r2 = page_rects2[0]
        for i in (2, 3):
            marquee_drag(page, (r2['x'] - 20, r2['y'] - 20, r2['x'] + r2['w'] + 20, r2['y'] + r2['h'] + 20))
            page.wait_for_timeout(300)
            page.frame_locator('#ed').locator('#annoText').fill('堆叠测试批注 %d' % i)
            page.frame_locator('#ed').locator('#annoSubmit').click()
            page.wait_for_timeout(200)
        h2_badges = df.evaluate("""() => {
          const h2 = document.querySelector('[data-slide-id="monolith-origin"] h2[data-editable]');
          const slide = h2.closest('.slide');
          return Array.from(slide.querySelectorAll('.anno-badge'))
            .filter(b => b.__forEl === h2).map(b => b.textContent);
        }""")
        if h2_badges != ['2', '3']:
            problems.append('同元素多条批注角标未堆叠：%r' % h2_badges)
        else:
            # 堆叠角标 left 应错开
            lefts = df.evaluate("""() => {
              const h2 = document.querySelector('[data-slide-id="monolith-origin"] h2[data-editable]');
              const slide = h2.closest('.slide');
              return Array.from(slide.querySelectorAll('.anno-badge'))
                .filter(b => b.__forEl === h2).map(b => b.style.left);
            }""")
            if len(set(lefts)) != 2:
                problems.append('堆叠角标位置未错开：%r' % lefts)
        if page.frame_locator('#ed').locator('.anno-item').count() != 2:
            problems.append('批注清单条数异常')

        report('T7-annotation', '批注端到端', not problems,
               '；'.join(problems) if problems else
               '4 命中剔除 1 → 3 目标（h2+p+img）；角标反缩放补偿正确；三层引用原文件回验一致；'
               '保存产物零痕迹；同元素多批注角标堆叠正确')
    finally:
        ctx.close()

def test_annotation_edges(browser):
    """§11.8：零命中不弹窗；空批注不可提交；Esc 取消框选无残留；批注模式禁用文字手势。"""
    deck = 'tech-ikb'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')
        page.frame_locator('#ed').locator('#viewSeg button[data-view="annotate"]').click()

        # 批注模式下文字两段手势禁用（§5.0）
        h1 = deck_loc(page, '[data-slide-id="cover"] h1[data-editable]')
        h1.click(); h1.click()
        page.wait_for_timeout(200)
        if h1.get_attribute('contenteditable') is not None or 'ed-selected' in (h1.get_attribute('class') or ''):
            problems.append('批注模式下文字手势未禁用')

        # 零命中：deck 顶部 12px 间距带（slide 未开始处）
        box = page.frame_locator('#ed').locator('#deckFrame').bounding_box()
        marquee_drag(page, (box['x'] + 600, box['y'] + 2, box['x'] + 800, box['y'] + 8))
        page.wait_for_timeout(400)
        if anno_mask_open(page):
            problems.append('零命中弹窗了')

        # Esc 取消框选：在 slide 1 内容上拖拽，中途中断
        rects = to_page_rects(page, deck_client_rects(page, ['[data-slide-id="cover"] h1[data-editable]']))
        r = rects[0]
        page.mouse.move(r['x'] - 30, r['y'] - 30)
        page.mouse.down()
        page.mouse.move(r['x'] + r['w'] + 30, r['y'] + r['h'] + 30, steps=5)
        if deck_frame(page).evaluate("document.querySelectorAll('.anno-marquee').length") != 1:
            problems.append('框选中选框节点缺失')
        # 真实浏览器中 mousedown 会把焦点带入 iframe；合成输入不会，显式聚焦模拟
        deck_frame(page).evaluate('window.focus()')
        page.keyboard.press('Escape')
        page.wait_for_timeout(150)
        page.mouse.up()
        page.wait_for_timeout(300)
        if anno_mask_open(page):
            problems.append('Esc 取消后弹窗了')
        if deck_frame(page).evaluate("document.querySelectorAll('.anno-marquee,.anno-badge,.anno-hit').length") != 0:
            problems.append('Esc 取消后有注入残留')

        # 弹窗取消：不留痕
        marquee_drag(page, (r['x'] - 30, r['y'] - 30, r['x'] + r['w'] + 30, r['y'] + r['h'] + 30))
        page.wait_for_timeout(400)
        if not anno_mask_open(page):
            problems.append('有效框选未弹窗')
        else:
            # 纯空白批注禁止提交
            page.frame_locator('#ed').locator('#annoText').fill('   ')
            if not page.frame_locator('#ed').locator('#annoSubmit').is_disabled():
                problems.append('纯空白批注未禁止提交')
            page.frame_locator('#ed').locator('#annoCancel').click()
            page.wait_for_timeout(200)
            if deck_frame(page).evaluate("document.querySelectorAll('.anno-badge,.anno-hit').length") != 0:
                problems.append('弹窗取消后角标/高亮未清除')
            if page.frame_locator('#ed').locator('.anno-item').count() != 0:
                problems.append('弹窗取消后批注清单非空')

        # 全程不置脏
        if editor_frame(page).evaluate('window.state.dirty') is not False or dirty_events(page) != []:
            problems.append('批注流程置脏')

        # 切回文字编辑模式：手势恢复
        page.frame_locator('#ed').locator('#viewSeg button[data-view="edit"]').click()
        h1.click(); h1.click()
        if h1.get_attribute('contenteditable') != 'plaintext-only':
            problems.append('切回文字编辑模式后手势未恢复')
        else:
            page.keyboard.press('Escape')   # 还原，不留修改

        report('T8-annotation-edges', '批注边界', not problems,
               '；'.join(problems) if problems else '零命中静默；Esc 取消无残留；空批注置灰；取消不留痕；模式互斥正确；全程不置脏')
    finally:
        ctx.close()

# ---------- 测试 9：面板意图导出（§7.3，主题单源化联动回归） ----------

def test_panel_export(browser):
    """打开面板 → 选主题 B1 + 变体柠檬黄 + 密度 high → 导出指令；断言文本含主题、
    变体与密度条目；主题卡数与 sync-themes.mjs 注入的 JSON 一致（G 期起为 9 个
    七层重主题 + 变体，不硬编码数量）。"""
    deck = 'tech-ikb'
    point_assets(deck)
    src = read_deck(deck)
    ctx = browser.new_context(viewport={'width': VIEW_W, 'height': VIEW_H},
                              permissions=['clipboard-read', 'clipboard-write'])
    page = ctx.new_page()
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')
        page.frame_locator('#ed').locator('#btnPanel').click()
        n_cards = page.frame_locator('#ed').locator('.theme-card').count()
        ed_frame = next(f for f in page.frames if f.name == 'ed')
        expected = ed_frame.evaluate('PANEL_DATA.questions[0].options.length')
        if n_cards != expected:
            problems.append('主题卡片数=%d，期望 %d（PANEL_DATA 注入值）' % (n_cards, expected))
        n_groups = page.frame_locator('#ed').locator('.theme-group').count()
        if n_groups < 3:
            problems.append('主题分组数=%d，期望 ≥3（focus 分组展示）' % n_groups)
        page.frame_locator('#ed').locator('.theme-card[data-id="b1"]').click()
        # G 期：点击 B1 卡的第一个变体色点（柠檬黄）——选中变体即选中主题
        page.frame_locator('#ed').locator('.theme-card[data-id="b1"] .variants i').first.click()
        page.frame_locator('#ed').locator('#densityOpts .opt[data-id="high"]').click()
        page.frame_locator('#ed').locator('#btnExport').click()
        page.wait_for_timeout(400)
        clip = page.evaluate('navigator.clipboard.readText()')
        for expect in ['B1', '瑞士国际主义', '变体：柠檬黄', '#FFD500',
                       'SLOT: theme tokens', 'SLOT: theme css',
                       '内容密度', '高密度', 'design-intent']:
            if expect not in clip:
                problems.append('导出指令缺少 %r' % expect)
        report('T9-panel-export', '面板意图导出', not problems,
               '；'.join(problems) if problems else
               '%d 张主题卡渲染（与注入 JSON 一致）；变体切换与双 SLOT 导出口径生效' % n_cards)
    finally:
        ctx.close()

# ---------- 测试 10：文字样式编辑持久化（v1.6 §1 / editor-v2.md §4） ----------

def test_style_editing(browser):
    """选中文字元素 → 样式控件组出现 → 改四属性即时生效且置脏 →
    保存 → 重载断言 inline style 仍在；图片元素选中时控件组隐藏；
    字号低于 18px 警告不禁止。"""
    deck = 'tech-ikb'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')
        ef = editor_frame(page)
        ed = page.frame_locator('#ed')
        bar_shown = "() => document.getElementById('styleBar').classList.contains('show')"

        if ef.evaluate(bar_shown):
            problems.append('未选中时样式控件组未隐藏')

        # 选中封面 h1 → 控件组出现，字号回填为画布坐标（computed 不受 transform 影响）
        h1 = deck_loc(page, '[data-slide-id="cover"] h1[data-editable]')
        h1.click()
        page.wait_for_timeout(200)
        if not ef.evaluate(bar_shown):
            problems.append('选中文字元素后样式控件组未出现')
        fs0 = ef.evaluate("document.getElementById('stSize').value")
        if fs0 != '128':
            problems.append('字号回填=%s，期望 128（画布坐标）' % fs0)

        # 字号 < 18：警告但不禁止
        ed.locator('#stSize').fill('12')
        ed.locator('#stSize').press('Enter')
        page.wait_for_timeout(150)
        warn = ef.evaluate("!document.getElementById('stSizeWarn').hidden")
        fs12 = deck_frame(page).evaluate(
            "document.querySelector('[data-slide-id=\"cover\"] h1[data-editable]').style.fontSize")
        if not warn or fs12 != '12px':
            problems.append('18px 下限警告/应用异常：warn=%s fs=%r' % (warn, fs12))
        ed.locator('#stSize').fill('72')
        ed.locator('#stSize').press('Enter')
        page.wait_for_timeout(150)

        # 字体写 var() 引用（换主题跟随）；色板写 var()；自定义色写字面量；对齐按钮
        ed.locator('#stFont').select_option('var(--font-body)')
        ed.locator('#stSwatches .st-swatch[data-token="--accent"]').click()
        ed.locator('#stAlign button[data-align="center"]').click()
        page.wait_for_timeout(150)
        ef.evaluate("""() => {
          const c = document.getElementById('stColor');
          c.value = '#ff0000';
          c.dispatchEvent(new Event('input', { bubbles: true }));
        }""")
        page.wait_for_timeout(150)
        applied = deck_frame(page).evaluate("""() => {
          const el = document.querySelector('[data-slide-id="cover"] h1[data-editable]');
          return {ff: el.style.getPropertyValue('font-family'), fs: el.style.fontSize,
                  color: el.style.getPropertyValue('color'), ta: el.style.textAlign};
        }""")
        # CSSOM 会把 #ff0000 规范化为 rgb(255, 0, 0)，两种写法都算对
        color_ok = applied['color'] in ('#ff0000', 'rgb(255, 0, 0)')
        if not (applied['ff'] == 'var(--font-body)' and applied['fs'] == '72px'
                and color_ok and applied['ta'] == 'center'):
            problems.append('iframe 内联样式不符：%r' % applied)
        if ef.evaluate('window.state.dirty') is not True:
            problems.append('样式修改未置脏')

        # 图片元素选中：样式控件组隐藏，"替换图片"按钮逻辑不变
        img = deck_loc(page, '[data-slide-id="monolith-origin"] img[data-editable-image]')
        img.scroll_into_view_if_needed()
        img.click()
        page.wait_for_timeout(200)
        if ef.evaluate(bar_shown):
            problems.append('选中图片时样式控件组未隐藏')
        if ef.evaluate("document.getElementById('btnReplaceImg').disabled"):
            problems.append('选中图片后替换按钮应可用')

        # 保存 → 重载 → inline style 持久化（白名单四属性随序列化保留）
        saved = save_and_capture(page)
        load_deck(page, saved, deck + '/index.html')
        attr = deck_frame(page).evaluate(
            "document.querySelector('[data-slide-id=\"cover\"] h1[data-editable]').getAttribute('style')")
        for label, cond in [
            ('字号未持久化', '72px' in attr),
            ('字体未持久化', 'var(--font-body)' in attr),
            ('字色未持久化', 'rgb(255, 0, 0)' in attr or '#ff0000' in attr),
            ('对齐未持久化', 'center' in attr),
            ('白名单外属性混入', 'background' not in attr),
        ]:
            if not cond:
                problems.append('%s：style=%r' % (label, attr))
        # 重载后选中同一元素：字体下拉应回显 var(--font-body)
        deck_loc(page, '[data-slide-id="cover"] h1[data-editable]').click()
        page.wait_for_timeout(200)
        fv = ef.evaluate("document.getElementById('stFont').value")
        if fv != 'var(--font-body)':
            problems.append('重载后字体下拉回显=%r' % fv)

        report('T10-style', '文字样式编辑持久化', not problems,
               '；'.join(problems) if problems else
               '四属性即时生效+置脏；<18px 警告不禁止；图片选中隐藏控件组；保存重载后 inline style 完整回显')
    finally:
        ctx.close()

# ---------- 测试 11：目录侧栏（v1.6 §2） ----------

def test_toc_nav(browser):
    """嵌入态默认收起 → 按钮展开 → N 页渲染 N 卡 → 懒渲染滚到底全部出图 →
    点击第 3 卡 iframe 滚到第 3 页且卡片高亮、页码同步 → 克隆体无 id、动效终态。"""
    deck = 'tech-ikb'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')
        ef = editor_frame(page)
        ed = page.frame_locator('#ed')
        n_slides = src.count('data-slide-id="')

        if ef.evaluate("document.getElementById('toc').classList.contains('open')"):
            problems.append('嵌入态侧栏应默认收起')
        ed.locator('#btnToc').click()
        page.wait_for_timeout(300)
        if not ef.evaluate("document.getElementById('toc').classList.contains('open')"):
            problems.append('目录按钮未展开侧栏')
        n_cards = ed.locator('.toc-card').count()
        if n_cards != n_slides:
            problems.append('缩略卡片数=%d，期望 %d' % (n_cards, n_slides))

        rendered_js = ("Array.from(document.querySelectorAll('.toc-thumb'))"
                       ".filter(t => t.shadowRoot && t.shadowRoot.querySelector('.slide')).length")
        page.wait_for_timeout(400)
        first_rendered = ef.evaluate(rendered_js)
        if first_rendered < 1:
            problems.append('侧栏展开后无可视缩略图渲染')
        # 懒渲染：滚动到底触发 IntersectionObserver
        ef.evaluate("document.getElementById('tocList').scrollTop = 999999")
        page.wait_for_timeout(600)
        rendered = ef.evaluate(rendered_js)
        if rendered != n_slides:
            problems.append('滚到底后渲染缩略图=%d，期望 %d' % (rendered, n_slides))
        if ef.evaluate("!!document.querySelector('.toc-thumb').shadowRoot.querySelector('[id]')"):
            problems.append('克隆体残留 id（页面出现重复 id）')
        op = ef.evaluate("""() => {
          const t = document.querySelector('.toc-thumb');
          const r = t.shadowRoot.querySelector('.reveal,[data-anim]');
          return r ? getComputedStyle(r).opacity : 'none';
        }""")
        if op != '1':
            problems.append('克隆动效未强制终态 opacity=%r' % op)

        # 点击第 3 张卡 → iframe 滚到第 3 页 + 高亮 + 页码同步
        ef.evaluate("document.getElementById('tocList').scrollTop = 0")
        page.wait_for_timeout(300)
        ed.locator('.toc-card').nth(2).click()
        page.wait_for_timeout(500)
        df = deck_frame(page)
        st = df.evaluate("document.querySelector('.deck').scrollTop")
        exp = df.evaluate("document.querySelectorAll('.slide-slot')[2].offsetTop")
        if abs(st - exp) > 4:
            problems.append('点击导航滚动位置=%s，期望 %s' % (st, exp))
        cur = ef.evaluate("Array.from(document.querySelectorAll('.toc-card'))"
                          ".findIndex(c => c.classList.contains('cur'))")
        if cur != 2:
            problems.append('高亮卡片=%d，期望 2' % cur)
        sb = ef.evaluate("document.getElementById('sbPage').textContent")
        if '第 3 /' not in sb:
            problems.append('页码未同步：%r' % sb)

        # 编辑后对应卡片失效重克隆（导航件按需刷新，不实时同步）
        h1 = deck_loc(page, '[data-slide-id="cover"] h1[data-editable]')
        h1.click(); h1.click()
        page.keyboard.type('侧栏失效验证')
        page.keyboard.press('Control+Enter')
        page.wait_for_timeout(300)
        thumb_text = ef.evaluate("""() => {
          const cards = Array.from(document.querySelectorAll('.toc-card'));
          const t = cards[0].querySelector('.toc-thumb');
          return t.shadowRoot ? t.shadowRoot.textContent : '';
        }""")
        if '侧栏失效验证' not in thumb_text:
            problems.append('编辑后封面卡片未重克隆')

        report('T11-toc', '目录侧栏导航', not problems,
               '；'.join(problems) if problems else
               '嵌入默认收起；%d 卡懒渲染齐全；点击导航+高亮+页码同步；克隆无 id、动效终态；编辑后失效重克隆' % n_slides)
    finally:
        ctx.close()

# ---------- 测试 12：Bridge v2 手动 daemon、版本与回滚 ----------

GIT_PORT = PORT + 2


def bridge_request(base, path, body=None, bearer=None, origin=None):
    headers = {}
    data = None
    if bearer:
        headers['Authorization'] = 'Bearer ' + bearer
        if body is None:
            headers['Sec-Fetch-Site'] = 'same-origin'
    if origin is not None:
        headers['Origin'] = origin
    if body is not None:
        data = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + path, data=data, headers=headers,
                                 method='POST' if body is not None else 'GET')
    try:
        response = urllib.request.urlopen(req, timeout=10)
        return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode('utf-8'))


def start_manual_bridge(workdir):
    proc = subprocess.Popen([
        sys.executable, os.path.join(ROOT, 'tools/edit.py'), workdir,
        '--deck', 'index.html', '--port', str(GIT_PORT), '--no-browser'],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    discovery_path = os.path.join(workdir, '.pptx-html', 'serve.json')
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if os.path.isfile(discovery_path):
            discovery = json.loads(open(discovery_path, encoding='utf-8').read())
            code, boot = bridge_request(discovery['origin'], '/api/bridge/bootstrap',
                                        {'mode': 'deck', 'path': 'index.html'},
                                        discovery['management_token'])
            if code == 200:
                return proc, discovery, boot['url']
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    if proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=5)
    raise RuntimeError('手动 Bridge daemon 未就绪')


def stop_manual_bridge(proc, discovery):
    if proc is None:
        return
    if proc.poll() is None and discovery:
        bridge_request(discovery['origin'], '/api/bridge/stop', {'reason': 'cli-stop'},
                       discovery['management_token'])
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=5)


def copy_git_fixture(workdir):
    shutil.copy(os.path.join(ROOT, 'tests/decks/tech-ikb/index.html'),
                os.path.join(workdir, 'index.html'))
    shutil.copytree(os.path.join(ROOT, 'tests/decks/tech-ikb/assets'),
                    os.path.join(workdir, 'assets'))


def test_git_versions(browser):
    """Bridge v2 手动入口回归：bootstrap/browser bearer、CAS receipt、专用
    refs/snapshot 与历史 UI；所有 Git 与 deck 写入只发生在临时目录。"""
    problems = []
    tmp = tempfile.mkdtemp(prefix='pptx-e2e-git-')
    probe_dir = os.path.join(tmp, 'probe')
    flow_dir = os.path.join(tmp, 'flow')
    os.makedirs(probe_dir)
    os.makedirs(flow_dir)
    probe_srv = flow_srv = None
    probe_discovery = flow_discovery = None
    try:
        # (a) 无后端仍保留静态编辑器降级。
        ctx0, page0 = fresh_page(browser)
        try:
            page0.goto(BASE + '/editor.html')
            page0.wait_for_function('() => window.state !== undefined')
            page0.wait_for_timeout(800)
            hb = page0.evaluate("""({
              dis: document.getElementById('btnHistory').disabled,
              title: document.getElementById('btnHistory').title,
              backend: window.state.backend })""")
            if not (hb['dis'] and hb['backend'] is None and 'tools/edit.py' in hb['title']):
                problems.append('无后端时历史按钮状态异常：%r' % hb)
        finally:
            ctx0.close()

        # (b) 安全与非 Git 首存确认使用独立临时 daemon，避免失败尝试影响主流程版本数。
        copy_git_fixture(probe_dir)
        probe_srv, probe_discovery, probe_boot = start_manual_bridge(probe_dir)
        probe_base = probe_discovery['origin']
        probe_ctx, probe_page = fresh_page(browser)
        try:
            probe_page.goto(probe_boot)
            probe_page.wait_for_function(
                '() => window.bridge && bridge.enabled && bridge.sessionId && bridge.token && '
                'window.state && state.loaded && window.registry.length > 0', timeout=10000)
            auth = probe_page.evaluate('({sid:bridge.sessionId,token:bridge.token,rev:bridge.loadedRevision})')
            src = open(os.path.join(probe_dir, 'index.html'), encoding='utf-8').read()
            valid = {'session_id': auth['sid'], 'path': 'index.html', 'html': src,
                     'base_revision': auth['rev']}

            code, body = bridge_request(probe_base, '/api/save', valid, origin=probe_base)
            if code not in (401, 403):
                problems.append('未鉴权写请求响应=%d %r，期望拒绝' % (code, body))

            for bad in ['../evil.html', '/etc/passwd', 'a/../../evil.html']:
                request = dict(valid)
                request['path'] = bad
                code, body = bridge_request(probe_base, '/api/save', request,
                                            auth['token'], probe_base)
                if code != 403 or body.get('error', {}).get('code') != 'PATH_DENIED':
                    problems.append('合法鉴权后的穿越路径 %r 响应异常：%d %r' %
                                    (bad, code, body))

            code, body = bridge_request(probe_base, '/api/save', valid,
                                        auth['token'], probe_base)
            if code != 409 or body.get('error', {}).get('code') != 'GIT_INIT_REQUIRED':
                problems.append('非 Git 首存未要求显式 init：%d %r' % (code, body))
            if not os.path.isfile(os.path.join(probe_dir, 'index.html')) or \
                    open(os.path.join(probe_dir, 'index.html'), encoding='utf-8').read() != src:
                problems.append('拒绝非 Git 首存时改写了目标文件')
        finally:
            probe_ctx.close()
            stop_manual_bridge(probe_srv, probe_discovery)
            probe_srv = None

        # (c) 主流程必须由真实手动 daemon 的 bootstrap URL 进入，不再使用 ?deck= 直开。
        copy_git_fixture(flow_dir)
        flow_srv, flow_discovery, flow_boot = start_manual_bridge(flow_dir)
        base = flow_discovery['origin']
        ctx, page = fresh_page(browser)
        try:
            page.goto(flow_boot)
            page.wait_for_function(
                '() => window.bridge && bridge.enabled && bridge.sessionId && bridge.token && '
                'window.state && state.loaded && window.registry.length > 0', timeout=10000)
            page.wait_for_timeout(400)
            bridge_state = page.evaluate("""({sid:bridge.sessionId,token:bridge.token,
              rev:bridge.loadedRevision,gitReady:bridge.capabilities.git_ready,
              hash:location.hash,historyDisabled:document.getElementById('btnHistory').disabled})""")
            if bridge_state['hash']:
                problems.append('bootstrap bearer 未从地址 fragment 清除')
            if bridge_state['gitReady'] or bridge_state['historyDisabled']:
                problems.append('bootstrap 后端/历史状态异常：%r' % bridge_state)

            def edit_h1(text):
                page.frame_locator('#deckFrame').locator('body').click(position={'x': 8, 'y': 6})
                page.wait_for_timeout(150)
                h1 = page.frame_locator('#deckFrame').locator(
                    '[data-slide-id="cover"] h1[data-editable]')
                h1.click(); h1.click()
                page.keyboard.type(text)
                page.keyboard.press('Control+Enter')

            def save_ui(confirm_init=False):
                with page.expect_response(
                        lambda r: r.url == base + '/api/save' and r.request.method == 'POST',
                        timeout=10000) as response_info:
                    page.locator('#btnSave').click()
                    if confirm_init:
                        page.locator('#confirmMask.show #confirmOk').click()
                result = response_info.value.json()
                page.wait_for_function('() => window.state.dirty === false', timeout=10000)
                return result

            edit_h1('版本一标题')
            save1 = save_ui(confirm_init=True)
            if not (save1.get('receipt_id') and save1.get('snapshot_id') and save1.get('gitReady')):
                problems.append('UI 首存缺少 Bridge v2 receipt/snapshot：%r' % save1)
            if subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=flow_dir,
                              capture_output=True).returncode == 0:
                problems.append('Bridge 首存不应创建或移动用户 HEAD')
            if os.path.exists(os.path.join(flow_dir, '.git', 'index')):
                problems.append('Bridge 首存不应创建用户真实 index')

            # 建立并暂存用户自己的状态；后续保存和回滚必须保持 HEAD/index 字节不变。
            open(os.path.join(flow_dir, 'owner.txt'), 'w', encoding='utf-8').write('owner\n')
            subprocess.run(['git', 'add', 'owner.txt'], cwd=flow_dir, check=True)
            subprocess.run(['git', '-c', 'user.name=T12 Owner', '-c',
                            'user.email=t12@example.invalid', 'commit', '-m', 'owner head'],
                           cwd=flow_dir, check=True, capture_output=True)
            open(os.path.join(flow_dir, 'staged.txt'), 'w', encoding='utf-8').write('staged\n')
            subprocess.run(['git', 'add', 'staged.txt'], cwd=flow_dir, check=True)
            head_before = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=flow_dir).strip()
            index_before = open(os.path.join(flow_dir, '.git', 'index'), 'rb').read()

            edit_h1('版本二标题')
            save2 = save_ui()
            if not save2.get('receipt_id') or save2.get('receipt_id') == save1.get('receipt_id'):
                problems.append('UI 第二次保存未产生独立 receipt：%r' % save2)
            head_after = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=flow_dir).strip()
            index_after = open(os.path.join(flow_dir, '.git', 'index'), 'rb').read()
            if head_after != head_before or index_after != index_before:
                problems.append('Bridge 保存修改了用户 HEAD 或真实 index')

            sid = bridge_state['sid']
            token = bridge_state['token']
            code, versions = bridge_request(
                base, '/api/versions?session_id=%s&path=index.html' % sid, bearer=token)
            vlist = versions.get('versions', []) if code == 200 else []
            save_versions = [v for v in vlist if v.get('message') == 'save']
            snapshot_ids = {v.get('snapshot_id') for v in save_versions}
            if code != 200 or len(save_versions) != 2:
                problems.append('Bridge v2 版本列表异常：%d %r' % (code, versions))
            if not {save1.get('snapshot_id'), save2.get('snapshot_id')} <= snapshot_ids:
                problems.append('两次 UI 保存 receipt 对应版本不可枚举：%r' % vlist)

            # (d) 保留浏览器未保存字节为 draft，再通过历史 UI + revision CAS 回滚首版。
            edit_h1('外部未保存字节')
            page.locator('#btnHistory').click()
            try:
                page.wait_for_selector('.ver-item', timeout=5000)
            except Exception:
                pass
            history_error = page.locator('#histList .ver-empty').all_text_contents()
            if not history_error:
                legacy = page.evaluate("""() => {
                  renderVersions([{hash:'abcdef1234567890',message:'legacy',time:'old'}]);
                  const row=document.querySelector('.ver-item');
                  return row && row.dataset.versionId;
                }""")
                if legacy != 'abcdef1234567890':
                    problems.append('旧 versions hash schema 未安全回退：%r' % legacy)
                page.evaluate('() => loadVersions()')
            target = save1['snapshot_id']
            row = page.locator('.ver-item[data-version-id="%s"]' % target)
            rolled = None
            if history_error or row.count() != 1:
                problems.append('历史 UI 未使用 snapshot_id 枚举 Bridge v2 版本：errors=%r rows=%d' %
                                (history_error, page.locator('.ver-item').count()))
                # 继续验证服务端回滚、draft 与专用 ref，不让 UI 单点失败遮蔽其余断言。
                page.evaluate('() => bridgePersistDraft(true)')
                code, rolled = bridge_request(base, '/api/rollback', {
                    'session_id': sid, 'path': 'index.html', 'hash': target,
                    'base_revision': save2['revision']}, token, base)
                if code != 200:
                    problems.append('合法 browser bearer 的 CAS 回滚失败：%d %r' % (code, rolled))
            else:
                with page.expect_response(
                        lambda r: r.url == base + '/api/rollback' and r.request.method == 'POST',
                        timeout=10000) as rollback_info:
                    row.locator('.ver-rollback').click()
                    page.locator('#confirmMask.show #confirmOk').click()
                rolled = rollback_info.value.json()
                page.wait_for_function("""() => {
                  const d=window.frame && window.frame.contentDocument;
                  const h=d && d.querySelector('[data-slide-id="cover"] h1');
                  return !!(window.state.loaded && h && h.textContent.includes('版本一标题'));
                }""", timeout=10000)
            if not rolled or not rolled.get('receipt_id') or rolled.get('revision') != save1.get('revision'):
                problems.append('回滚 receipt/revision 异常：%r' % rolled)

            disk = open(os.path.join(flow_dir, 'index.html'), encoding='utf-8').read()
            if '版本一标题' not in disk or '版本二标题' in disk or '外部未保存字节' in disk:
                problems.append('回滚后目标未恢复首存版本')
            code, drafts = bridge_request(
                base, '/api/bridge/drafts?session_id=%s' % sid, bearer=token)
            if code != 200 or not drafts.get('items'):
                problems.append('回滚前未保护浏览器未保存 draft：%d %r' % (code, drafts))
            else:
                draft_id = drafts['items'][0]['id']
                code, draft = bridge_request(base, '/api/bridge/draft?id=' + draft_id,
                                             bearer=token)
                if code != 200 or '外部未保存字节' not in draft.get('html', ''):
                    problems.append('pre-rollback draft 未保留外部未保存字节：%d %r' %
                                    (code, draft))

            code, after_versions = bridge_request(
                base, '/api/versions?session_id=%s&path=index.html' % sid, bearer=token)
            messages = [v.get('message') for v in after_versions.get('versions', [])]
            if code != 200 or 'pre-rollback' not in messages or 'rollback' not in messages:
                problems.append('回滚未保留 pre-rollback/rollback 快照版本：%r' % after_versions)
            if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=flow_dir).strip() != head_before or \
                    open(os.path.join(flow_dir, '.git', 'index'), 'rb').read() != index_before:
                problems.append('Bridge 回滚修改了用户 HEAD 或真实 index')
        finally:
            ctx.close()

        report('T12-git', 'Bridge v2 版本与回滚', not problems,
               '；'.join(problems) if problems else
               '无后端降级；未鉴权/穿越拒绝；显式 init；bootstrap UI 双保存 receipt；'
               '专用 ref 不污染 HEAD/index；CAS 回滚保留 draft 与 pre-rollback 快照；历史 UI 可用')
    finally:
        stop_manual_bridge(flow_srv, flow_discovery)
        stop_manual_bridge(probe_srv, probe_discovery)
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- 测试 13：skeleton v3 运行时动效（迭代 C / motion-system.md） ----------

def goto_slide(page, i):
    page.evaluate("""(i) => {
      const deck = document.querySelector('.deck');
      deck.scrollTop = document.querySelectorAll('.slide-slot')[i].offsetTop;
    }""", i)

def test_motion_v3(browser):
    """(a) 入场拆字 spans → 完成后还原纯文本节点（无残留）；(b) count-up 精确还原
    终值（含 data-from 分支）；(c) draw-line 描边归零；(d) fill-bar 到终态；
    (e) 质感槽位 --texture-scope:cover（封面有质感层、普通页没有）；
    (f) reduced-motion：引擎不启动、全文完整可读。"""
    deck = 'motion-d2'
    problems = []
    ctx, page = fresh_page(browser)
    try:
        page.goto('%s/decks/%s/index.html' % (BASE, deck))

        # (a) chars：入场即拆字（spans 出现）→ 完成后还原
        page.wait_for_selector('[data-slide-id="cover"] [data-anim="chars"] .sp-unit', timeout=5000)
        page.wait_for_timeout(2400)
        st = page.evaluate("""() => {
          const h1 = document.querySelector('[data-slide-id="cover"] [data-anim="chars"]');
          return { spans: document.querySelectorAll('.sp-unit').length,
                   text: h1.textContent, kids: h1.childNodes.length,
                   isText: h1.childNodes[0] && h1.childNodes[0].nodeType === 3,
                   cls: h1.className };
        }""")
        if st['spans'] != 0:
            problems.append('chars 完成后残留 sp-unit ×%d' % st['spans'])
        if not (st['text'] == '柔光暗房' and st['kids'] == 1 and st['isText']):
            problems.append('chars 未还原为纯文本节点：%r kids=%d' % (st['text'], st['kids']))
        if 'split-anim' in st['cls']:
            problems.append('split-anim class 未清除')

        # (a2) words：空白以文本节点保留，还原后文本精确
        goto_slide(page, 1)
        page.wait_for_selector('[data-slide-id="chapter-words"] [data-anim="words"] .sp-unit', timeout=5000)
        page.wait_for_timeout(2400)
        w = page.evaluate("""() => {
          const h2 = document.querySelector('[data-slide-id="chapter-words"] [data-anim="words"]');
          return { text: h2.textContent, spans: h2.querySelectorAll('.sp-unit').length,
                   kids: h2.childNodes.length };
        }""")
        if not (w['text'] == 'From darkness to light' and w['spans'] == 0 and w['kids'] == 1):
            problems.append('words 还原异常：%r spans=%d kids=%d' % (w['text'], w['spans'], w['kids']))

        # (b) count-up：进行中是滚动值，结束后精确还原终值文本
        goto_slide(page, 2)
        page.wait_for_timeout(300)
        mid = page.evaluate("""() => {
          const els = document.querySelectorAll('[data-slide-id="metrics"] [data-anim="count-up"]');
          return Array.from(els).map(e => e.textContent);
        }""")
        page.wait_for_timeout(2200)
        fin = page.evaluate("""() => {
          const els = document.querySelectorAll('[data-slide-id="metrics"] [data-anim="count-up"]');
          return Array.from(els).map(e => ({ t: e.textContent,
            kids: e.childNodes.length, spans: e.querySelectorAll('.sp-unit').length }));
        }""")
        if mid[0] == '87.5%' or mid[1] == '128':
            problems.append('count-up 未见滚动中间态：%r' % mid)
        if not (fin[0]['t'] == '87.5%' and fin[1]['t'] == '128'):
            problems.append('count-up 终值未精确还原：%r' % [f['t'] for f in fin])
        if any(f['kids'] != 1 or f['spans'] != 0 for f in fin):
            problems.append('count-up 结束态非纯文本：%r' % fin)

        # (c) draw-line：加载时藏线（dasharray 就位），入场后归零
        goto_slide(page, 3)
        page.wait_for_timeout(1600)
        dl = page.evaluate("""() => {
          const p = document.querySelector('[data-slide-id="flow"] [data-anim="draw-line"]');
          return { arr: p.style.strokeDasharray, off: p.style.strokeDashoffset };
        }""")
        if not dl['arr'] or dl['off'] != '0':
            problems.append('draw-line 描边未就位/未归零：%r' % dl)

        # (d) fill-bar：终态 transform none、opacity 1
        goto_slide(page, 4)
        page.wait_for_timeout(1500)
        fb = page.evaluate("""() => {
          const b = document.querySelector('[data-slide-id="bars"] [data-anim="fill-bar"]');
          const cs = getComputedStyle(b);
          return { tf: cs.transform, op: cs.opacity };
        }""")
        if not (fb['tf'] == 'none' and fb['op'] == '1'):
            problems.append('fill-bar 终态异常：%r' % fb)

        # (e) 质感槽位：scope=cover → 封面/章节页有质感层，普通页没有
        tx = page.evaluate("""() => ({
          cover: getComputedStyle(document.querySelector('[data-slide-id="cover"]'), '::before').backgroundImage,
          plain: getComputedStyle(document.querySelector('[data-slide-id="metrics"]'), '::before').backgroundImage,
          htmlCls: document.documentElement.className })""")
        if 'radial-gradient' not in tx['cover']:
            problems.append('封面质感层缺失：%r' % tx['cover'][:80])
        if tx['plain'] != 'none':
            problems.append('普通页不应有质感层（scope=cover）：%r' % tx['plain'][:80])
        if 'texture-cover' not in tx['htmlCls']:
            problems.append('html 缺少 texture-cover class：%r' % tx['htmlCls'])
    finally:
        ctx.close()

    # (f) reduced-motion：引擎不启动，全文完整可读
    ctx3 = browser.new_context(viewport={'width': VIEW_W, 'height': VIEW_H},
                               reduced_motion='reduce')
    pg = ctx3.new_page()
    pg.on('pageerror', lambda e: print('[pageerror]', e))
    try:
        pg.goto('%s/decks/%s/index.html' % (BASE, deck))
        pg.wait_for_timeout(800)
        rm = pg.evaluate("""() => {
          const h1 = document.querySelector('[data-slide-id="cover"] [data-anim="chars"]');
          const cu = document.querySelector('[data-slide-id="metrics"] [data-anim="count-up"]');
          const p = document.querySelector('[data-slide-id="flow"] [data-anim="draw-line"]');
          return { spans: document.querySelectorAll('.sp-unit').length,
                   h1: h1.textContent, h1op: getComputedStyle(h1).opacity,
                   cu: cu.textContent, cuop: getComputedStyle(cu).opacity,
                   dash: p.style.strokeDasharray };
        }""")
        if rm['spans'] != 0:
            problems.append('reduced-motion 下出现拆字 span ×%d' % rm['spans'])
        if rm['h1'] != '柔光暗房' or rm['h1op'] != '1':
            problems.append('reduced-motion 下标题不可读：%r op=%s' % (rm['h1'], rm['h1op']))
        if rm['cu'] != '87.5%' or rm['cuop'] != '1':
            problems.append('reduced-motion 下 count-up 非终值：%r op=%s' % (rm['cu'], rm['cuop']))
        if rm['dash'] != '':
            problems.append('reduced-motion 下 draw-line 被藏线：%r' % rm['dash'])
    finally:
        ctx3.close()

    report('T13-motion-v3', '骨架 v3 运行时动效', not problems,
           '；'.join(problems) if problems else
           'chars/words 拆字后还原纯文本；count-up 终值精确（含 data-from）；draw-line 归零；fill-bar 终态；'
           '质感层仅封面页；reduced-motion 全文可读零拆字')

# ---------- 测试 14：编辑拆字元素（契约 v3：编辑前强制还原 + 保存净化） ----------

def test_edit_chars_v3(browser):
    """动画进行中两段手势进入编辑 → 元素先强制还原为纯文本 → 编辑 →
    保存产物：无拆字 span、无 split-anim、无 draw-line 运行时 style、
    html 无运行时 class、data-from 保留 → 重载再保存逐字节幂等。"""
    deck = 'motion-d2'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')   # 加载即触发封面 chars 拆字动画

        # 动画进行中：两段手势进入编辑
        h1 = deck_loc(page, '[data-slide-id="cover"] h1[data-editable]')
        h1.click()
        h1.click()
        ce = h1.get_attribute('contenteditable')
        st = deck_frame(page).evaluate("""() => {
          const h1 = document.querySelector('[data-slide-id="cover"] h1[data-editable]');
          return { spans: h1.querySelectorAll('.sp-unit').length, text: h1.textContent };
        }""")
        if ce != 'plaintext-only':
            problems.append('未进入编辑态 ce=%r' % ce)
        if st['spans'] != 0 or st['text'] != '柔光暗房':
            problems.append('进入编辑前未强制还原：spans=%d text=%r' % (st['spans'], st['text']))
        page.keyboard.type('柔光实验室')
        page.keyboard.press('Control+Enter')

        saved = save_and_capture(page)
        with open(os.path.join(RESULTS, deck + '.edited.html'), 'w', encoding='utf-8') as f:
            f.write(saved)
        problems += assert_clean_output(deck, saved, [
            ('编辑未生效', '柔光实验室' in saved),
            ('拆字 span 进入产物', '<span class="sp-unit"' not in saved),
            ('split-anim class 进入产物', 'class="split-anim"' not in saved),
            ('draw-line 运行时 style 进入产物',
             not re.search(r'style="[^"]*stroke-dash', saved)),
            ('html 残留运行时 class', not re.search(r'<html[^>]*\sclass=', saved)),
            ('data-from 丢失', 'data-from="12"' in saved),
        ])

        # 重载 → 再保存：逐字节幂等且无 span 污染
        load_deck(page, saved, deck + '/index.html')
        saved2 = save_and_capture(page)
        if saved2 != saved:
            problems.append('重载再保存不幂等')
        if '<span class="sp-unit"' in saved2:
            problems.append('重载保存产物出现拆字 span')

        report('T14-edit-chars', '编辑拆字元素（v3 契约）', not problems,
               '；'.join(problems) if problems else
               '动画中点击进入编辑已强制还原纯文本；产物零 span/style/class 污染；重载幂等')
    finally:
        ctx.close()


# ---------- 测试 19：skeleton v5 动效词汇库 8 族（迭代 F4 / visual-depth.md §三） ----------

def test_motion_v5(browser):
    """(a) enter 族终态（blur-in/scale-pop/wipe-clip/rise-in/persp-in 归位）；
    (b) text 族：mask-lines 行结构终态 + typewriter 中间态截获与精确还原 +
        scramble 精确还原 + gradient-flow 循环在跑；
    (c) data 族：fill-bar-y 终态、ring dashoffset==100-val（纯 CSS）；
    (d) link 族：dash-flow / flow-dot 循环动画在跑；
    (e) scroll 族：read-progress 随滚动 scaleX 0→1、scrub-draw dashoffset 随滚动
        变化、parallax transform 随滚动变化、sticky 槽位就位（cover/stack）；
    (f) ptr 族：程序化 pointermove → slide 写 --mx/--my、tilt 写 --rx/--ry、
        magnetic 写 --mgx；__pptxMotion.freeze() 后变量清空且不再写入；
    (g) reduced-motion：全静态可读（引擎与 tracker 不启动、循环动画全停）。"""
    deck = 'motion-v5'
    problems = []
    ctx, page = fresh_page(browser)
    try:
        page.goto('%s/decks/%s/index.html' % (BASE, deck))
        v = page.evaluate("document.querySelector('meta[name=skeleton-version]').content")
        if v != '5.1':
            problems.append('skeleton-version=%r，期望 5.1（v5.1 patch）' % v)

        # (a) enter 族终态
        goto_slide(page, 1)
        page.wait_for_timeout(2200)
        en = page.evaluate("""() => ({
          blur: getComputedStyle(document.querySelector('[data-anim="blur-in"]')).filter,
          wipe: getComputedStyle(document.querySelector('[data-anim="wipe-clip"]')).clipPath,
          pop: getComputedStyle(document.querySelector('[data-anim="scale-pop"]')).transform,
          persp: getComputedStyle(document.querySelector('[data-anim="persp-in"]')).transform,
          rise: getComputedStyle(document.querySelector('[data-slide-id="enter-lab"] [data-anim="rise-in"]')).transform,
          op: getComputedStyle(document.querySelector('[data-anim="blur-in"]')).opacity })""")
        if en['blur'] not in ('none', 'blur(0px)', 'blur(0)'):
            problems.append('blur-in 终态 filter=%r' % en['blur'])
        if not (en['wipe'] in ('none', 'inset(0px)')):
            problems.append('wipe-clip 终态 clip-path=%r' % en['wipe'])
        for k in ('pop', 'persp', 'rise'):
            if en[k] != 'none':
                problems.append('%s 终态 transform=%r' % (k, en[k]))
        if en['op'] != '1':
            problems.append('enter 族终态 opacity=%r' % en['op'])

        # (b) text 族
        goto_slide(page, 2)
        page.wait_for_timeout(320)   # typewriter 中间态截获
        mid = page.evaluate("""() => ({
          tw: document.querySelector('[data-anim="typewriter"]').textContent,
          live: document.querySelector('[data-anim="typewriter"]').classList.contains('tw-live') })""")
        page.wait_for_timeout(2600)
        tx = page.evaluate("""() => {
          const ml = document.querySelector('[data-anim="mask-lines"]');
          const inners = Array.from(ml.querySelectorAll('.ml-inner'));
          const tw = document.querySelector('[data-anim="typewriter"]');
          const sc = document.querySelector('[data-anim="scramble"]');
          const gf = document.querySelector('[data-slide-id="text-lab"] [data-anim="gradient-flow"]');
          return { mlText: ml.textContent, spans: ml.querySelectorAll('.sp-unit').length,
                   innerTf: inners.map(i => getComputedStyle(i).transform),
                   tw: tw.textContent, twLive: tw.classList.contains('tw-live'),
                   sc: sc.textContent,
                   gfAnim: getComputedStyle(gf).animationName,
                   gfFill: getComputedStyle(gf).webkitTextFillColor };
        }""")
        if not (0 < len(mid['tw']) < 40 and mid['live']):
            problems.append('typewriter 中间态异常：%r' % mid)
        if tx['mlText'] != '逐行遮罩显影，行与行之间有先后。' or tx['spans'] != 0:
            problems.append('mask-lines 文本/结构异常：%r spans=%d' % (tx['mlText'], tx['spans']))
        if any(t != 'none' for t in tx['innerTf']):
            problems.append('mask-lines 行终态未归位：%r' % tx['innerTf'])
        if tx['tw'] != '$ render --family=text --mode=typewriter' or tx['twLive']:
            problems.append('typewriter 还原异常：%r live=%s' % (tx['tw'], tx['twLive']))
        if tx['sc'] != 'SIGNAL-LOCKED-0942':
            problems.append('scramble 还原异常：%r' % tx['sc'])
        if tx['gfAnim'] != 'gradient-flow':
            problems.append('gradient-flow 动画未运行：%r' % tx['gfAnim'])
        if tx['gfFill'] != 'rgba(0, 0, 0, 0)':
            problems.append('gradient-flow 未走透明填充：%r' % tx['gfFill'])

        # (c) data 族
        goto_slide(page, 3)
        page.wait_for_timeout(2400)
        da = page.evaluate("""() => ({
          bars: Array.from(document.querySelectorAll('[data-anim="fill-bar-y"]'))
                     .map(b => getComputedStyle(b).transform),
          ring: parseFloat(getComputedStyle(document.querySelector('[data-anim="ring"]')).strokeDashoffset.replace(/[^0-9.]/g, '')) })""")
        if any(t != 'none' for t in da['bars']):
            problems.append('fill-bar-y 终态异常：%r' % da['bars'])
        if abs(da['ring'] - 28) > 1:
            problems.append('ring 终态 dashoffset=%s，期望 28（100-72）' % da['ring'])

        # (d) link 族
        goto_slide(page, 4)
        page.wait_for_timeout(400)
        li = page.evaluate("""() => ({
          dash: getComputedStyle(document.querySelector('.dash-flow')).animationName,
          dot: getComputedStyle(document.querySelector('.flow-dot')).animationName,
          dotOp: getComputedStyle(document.querySelector('.flow-dot')).opacity })""")
        if li['dash'] != 'dash-flow':
            problems.append('dash-flow 动画未运行：%r' % li['dash'])
        if li['dot'] != 'flow-dot' or li['dotOp'] != '1':
            problems.append('flow-dot 异常：%r op=%s' % (li['dot'], li['dotOp']))

        # (e) scroll 族（滚动驱动断言；先关 scroll-snap 防止吸附把两个采样位并到一起）
        page.evaluate("document.querySelector('.deck').style.scrollSnapType = 'none'")
        page.evaluate("document.querySelector('.deck').scrollTop = 0")
        page.wait_for_timeout(500)
        sc0 = page.evaluate(
            "getComputedStyle(document.querySelector('.read-progress')).transform")
        page.evaluate("""() => {
          const deck = document.querySelector('.deck');
          deck.scrollTop = deck.scrollHeight - deck.clientHeight;
        }""")
        page.wait_for_timeout(600)
        sc1 = page.evaluate("""() => {
          const m = getComputedStyle(document.querySelector('.read-progress')).transform;
          return { m, display: getComputedStyle(document.querySelector('.read-progress')).display };
        }""")
        def scalex(m):
            mm = re.match(r'matrix\(([\d.e-]+)', m or '')
            return float(mm.group(1)) if mm else None
        sx0, sx1 = scalex(sc0), scalex(sc1['m'])
        if sc1['display'] != 'block' or sx0 is None or sx1 is None or not (sx0 < 0.05 and sx1 > 0.95):
            problems.append('read-progress 滚动驱动异常：top=%r bottom=%r' % (sc0, sc1))

        # scrub-draw：两个滚动位置的 dashoffset 不同且都在 [0,100]
        page.evaluate("""() => {
          const deck = document.querySelector('.deck');
          deck.scrollTop = document.querySelectorAll('.slide-slot')[5].offsetTop - deck.clientHeight * 0.5;
        }""")
        page.wait_for_timeout(500)
        sd_mid = page.evaluate("parseFloat(getComputedStyle(document.querySelector('[data-scroll=\\'scrub-draw\\']')).strokeDashoffset.replace(/[^0-9.]/g, ''))")
        goto_slide(page, 5)
        page.wait_for_timeout(600)
        sd_in = page.evaluate("parseFloat(getComputedStyle(document.querySelector('[data-scroll=\\'scrub-draw\\']')).strokeDashoffset.replace(/[^0-9.]/g, ''))")
        if not (0 <= sd_mid <= 100 and 0 <= sd_in <= 100):
            problems.append('scrub-draw dashoffset 越界：%s / %s' % (sd_mid, sd_in))
        if abs(sd_mid - sd_in) < 5:
            problems.append('scrub-draw 未随滚动变化：%s vs %s' % (sd_mid, sd_in))

        # parallax：两个滚动位置 transform 不同
        plx0 = page.evaluate("getComputedStyle(document.querySelector('[data-scroll=\\'parallax\\']')).transform")
        page.evaluate("document.querySelector('.deck').scrollTop += 200")
        page.wait_for_timeout(500)
        plx1 = page.evaluate("getComputedStyle(document.querySelector('[data-scroll=\\'parallax\\']')).transform")
        if plx0 == plx1:
            problems.append('scroll-parallax 未随滚动变化：%r' % plx0)

        # sticky 页间效果就位
        sticky = page.evaluate("""() => ({
          cover: getComputedStyle(document.querySelector('.slide-slot[data-scroll="cover"]')).position,
          stack: getComputedStyle(document.querySelector('.slide-slot[data-scroll="stack"]')).position })""")
        if sticky['cover'] != 'sticky' or sticky['stack'] != 'sticky':
            problems.append('sticky 槽位异常：%r' % sticky)

        # (f) ptr 族：程序化指针模拟
        goto_slide(page, 6)
        page.wait_for_timeout(500)
        box = page.evaluate("""() => {
          const r = document.querySelector('[data-ptr="tilt"]').getBoundingClientRect();
          return { x: r.x, y: r.y, w: r.width, h: r.height };
        }""")
        page.mouse.move(box['x'] + box['w'] * 0.25, box['y'] + box['h'] * 0.3, steps=4)
        page.wait_for_timeout(300)
        pt = page.evaluate("""() => {
          const slide = document.querySelector('[data-slide-id="ptr-lab"]');
          const tilt = document.querySelector('[data-ptr="tilt"]');
          const mag = document.querySelector('[data-ptr="magnetic"]');
          return { mx: slide.style.getPropertyValue('--mx'), myr: slide.style.getPropertyValue('--myr'),
                   rx: tilt.style.getPropertyValue('--rx'), ry: tilt.style.getPropertyValue('--ry') };
        }""")
        magc = page.evaluate("""() => {
          const r = document.querySelector('[data-ptr="magnetic"]').getBoundingClientRect();
          return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }""")
        page.mouse.move(magc['x'], magc['y'], steps=3)
        page.wait_for_timeout(300)
        pt['mgx'] = page.evaluate("document.querySelector('[data-ptr=\\'magnetic\\']').style.getPropertyValue('--mgx')")
        if not pt['mx'] or not pt['myr']:
            problems.append('slide 级 pointer 变量未写入：%r' % pt)
        if not pt['rx'] or not pt['ry']:
            problems.append('tilt 变量未写入：%r' % pt)
        if not pt['mgx']:
            problems.append('magnetic 变量未写入：%r' % pt)

        # freeze：变量清空且指针不再驱动
        page.evaluate('window.__pptxMotion.freeze()')
        fz = page.evaluate("""() => {
          const slide = document.querySelector('[data-slide-id="ptr-lab"]');
          const tilt = document.querySelector('[data-ptr="tilt"]');
          return { mx: slide.style.getPropertyValue('--mx'), rx: tilt.style.getPropertyValue('--rx') };
        }""")
        page.mouse.move(box['x'] + box['w'] * 0.7, box['y'] + box['h'] * 0.6, steps=3)
        page.wait_for_timeout(300)
        fz2 = page.evaluate("""() => ({
          mx: document.querySelector('[data-slide-id="ptr-lab"]').style.getPropertyValue('--mx'),
          rx: document.querySelector('[data-ptr="tilt"]').style.getPropertyValue('--rx') })""")
        if fz['mx'] or fz['rx'] or fz2['mx'] or fz2['rx']:
            problems.append('freeze 后变量未清空/仍写入：%r -> %r' % (fz, fz2))
    finally:
        ctx.close()

    # (g) reduced-motion：全静态可读
    ctx3 = browser.new_context(viewport={'width': VIEW_W, 'height': VIEW_H},
                               reduced_motion='reduce')
    pg = ctx3.new_page()
    pg.on('pageerror', lambda e: print('[pageerror]', e))
    try:
        pg.goto('%s/decks/%s/index.html' % (BASE, deck))
        pg.wait_for_timeout(900)
        rm = pg.evaluate("""() => ({
          h1: document.querySelector('[data-slide-id="cover"] [data-anim="chars"]').textContent,
          spans: document.querySelectorAll('.sp-unit').length,
          tw: document.querySelector('[data-anim="typewriter"]').textContent,
          sc: document.querySelector('[data-anim="scramble"]').textContent,
          mlTf: getComputedStyle(document.querySelector('.ml-inner')).transform,
          dash: getComputedStyle(document.querySelector('.dash-flow')).animationName,
          blob: getComputedStyle(document.querySelector('.amb-gradient-blob')).animationName,
          sweep: getComputedStyle(document.querySelector('.light-sweep'), '::after').animationName,
          rp: getComputedStyle(document.querySelector('.read-progress')).display,
          ring: parseFloat(getComputedStyle(document.querySelector('[data-anim="ring"]')).strokeDashoffset.replace(/[^0-9.]/g, '')) })""")
        if rm['h1'] != '终端即诗' or rm['spans'] != 0:
            problems.append('RM 下封面标题异常：%r spans=%d' % (rm['h1'], rm['spans']))
        if rm['tw'] != '$ render --family=text --mode=typewriter':
            problems.append('RM 下 typewriter 非全文：%r' % rm['tw'])
        if rm['sc'] != 'SIGNAL-LOCKED-0942':
            problems.append('RM 下 scramble 非全文：%r' % rm['sc'])
        if rm['mlTf'] != 'none':
            problems.append('RM 下 mask-lines 未归位：%r' % rm['mlTf'])
        if rm['dash'] != 'none' or rm['blob'] != 'none' or rm['sweep'] != 'none':
            problems.append('RM 下循环动画未停：%r' % rm)
        if rm['rp'] != 'none':
            problems.append('RM 下 read-progress 未隐藏：%r' % rm['rp'])
        if abs(rm['ring'] - 28) > 1:
            problems.append('RM 下 ring 非终态：%s' % rm['ring'])
        tb = pg.evaluate("""() => {
          const r = document.querySelector('[data-ptr="tilt"]').getBoundingClientRect();
          return { x: r.x, y: r.y };
        }""")
        pg.mouse.move(tb['x'] + 30, tb['y'] + 30, steps=3)
        pg.wait_for_timeout(300)
        rmv = pg.evaluate("""() => ({
          mx: document.querySelector('[data-slide-id="ptr-lab"]').style.getPropertyValue('--mx'),
          rx: document.querySelector('[data-ptr="tilt"]').style.getPropertyValue('--rx') })""")
        if rmv['mx'] or rmv['rx']:
            problems.append('RM 下 tracker 仍在写变量：%r' % rmv)
    finally:
        ctx3.close()

    report('T19-motion-v5', '骨架 v5 动效 8 族', not problems,
           '；'.join(problems) if problems else
           'enter/text/data/link 族终态与精确还原全过；scroll 族滚动驱动断言全过（read-progress/scrub-draw/parallax/sticky）；'
           'ptr 族程序化指针写入与 freeze 清空全过；reduced-motion 全静态可读')


def test_edit_motion_v5(browser):
    """F4 编辑侧（契约 v6）：编辑器加载即冻结交互层；编辑 mask-lines 行叶子与
    gradient-flow（编辑态还原本色）；手工注入 pointer 运行时变量后保存——
    净化清单移除全部 v5 运行时残留、保留产物结构（.ml-line/--val/--pin-i/
    pathLength）；重载再保存逐字节幂等。"""
    deck = 'motion-v5'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')

        # 编辑态冻结交互动效层（契约 v6）：注入样式已生效
        fz = deck_frame(page).evaluate("""() => ({
          rp: getComputedStyle(document.querySelector('.read-progress')).display,
          spot: getComputedStyle(document.querySelector('.spotlight')).display })""")
        if fz['rp'] != 'none' or fz['spot'] != 'none':
            problems.append('编辑态未冻结 spotlight/read-progress：%r' % fz)

        # 手工注入 v5 运行时残留（等价于 tracker 写过一轮）
        deck_frame(page).evaluate("""() => {
          const slide = document.querySelector('[data-slide-id="ptr-lab"]');
          slide.style.setProperty('--mx', '50%'); slide.style.setProperty('--my', '30%');
          slide.style.setProperty('--mxr', '0.1'); slide.style.setProperty('--myr', '-0.2');
          const tilt = document.querySelector('[data-ptr="tilt"]');
          tilt.style.setProperty('--rx', '3deg'); tilt.style.setProperty('--ry', '-2deg');
          const mag = document.querySelector('[data-ptr="magnetic"]');
          mag.style.setProperty('--mgx', '8px'); mag.style.setProperty('--mgy', '-6px');
        }""")

        # 编辑 mask-lines 行叶子（产物结构必须保留）
        line = deck_loc(page, '[data-slide-id="text-lab"] .ml-inner[data-editable]:has-text("行与行之间")')
        line.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        line.click(); line.click()
        ce = line.get_attribute('contenteditable')
        if ce != 'plaintext-only':
            problems.append('mask-lines 行叶子未进入编辑态 ce=%r' % ce)
        page.keyboard.type('每行都有自己的时刻。')
        page.keyboard.press('Control+Enter')

        # gradient-flow：编辑态强制还原本色（契约 v6 透明填充条款）
        gf = deck_loc(page, '[data-slide-id="text-lab"] [data-anim="gradient-flow"]')
        gf.scroll_into_view_if_needed()
        gf.click(); gf.click()
        fill = deck_frame(page).evaluate(
            "getComputedStyle(document.querySelector('[data-slide-id=\"text-lab\"] [data-anim=\"gradient-flow\"]')).webkitTextFillColor")
        if fill == 'rgba(0, 0, 0, 0)':
            problems.append('gradient-flow 编辑态未还原本色：%r' % fill)
        page.keyboard.press('Escape')   # 不留修改

        saved = save_and_capture(page)
        with open(os.path.join(RESULTS, deck + '.edited.html'), 'w', encoding='utf-8') as f:
            f.write(saved)
        problems += assert_clean_output(deck, saved, [
            ('mask-lines 行编辑未生效', '每行都有自己的时刻。' in saved),
            ('mask-lines 产物结构丢失', 'class="ml-line"' in saved and 'class="ml-inner"' in saved),
            ('pointer 运行时变量残留（--mx 等）',
             not re.search(r'style="[^"]*--m[xyr]', saved)),
            ('tilt/magnetic 运行时变量残留（--rx/--ry/--mgx/--mgy）',
             not re.search(r'style="[^"]*--(rx|ry|mgx|mgy)', saved)),
            ('--i 阶梯序号残留', not re.search(r'style="[^"]*--i\s*:', saved)),
            ('tw-live class 残留', re.search(r'class="[^"]*tw-live', saved) is None),
            ('--val 产物内容被误删', re.search(r'--val\s*:\s*72', saved) is not None),
            ('--pin-i 产物内容被误删', re.search(r'--pin-i\s*:\s*0', saved) is not None),
            ('--depth 产物内容被误删', re.search(r'--depth\s*:\s*\.35', saved) is not None),
            ('--flow-path 产物内容被误删', '--flow-path' in saved),
            ('pathLength 被误删',
             len(re.findall(r'<(?:circle|path)[^>]*\bpathLength="100"', saved)) == 2),
            ('拆字 span 进入产物', '<span class="sp-unit"' not in saved),
        ])

        load_deck(page, saved, deck + '/index.html')
        saved2 = save_and_capture(page)
        if saved2 != saved:
            problems.append('重载再保存不幂等')

        report('T20-edit-motion-v5', '编辑 v5 动效 deck（契约 v6）', not problems,
               '；'.join(problems) if problems else
               '编辑态交互层冻结；mask-lines 行叶子可编辑且结构保留；gradient-flow 编辑态还原本色；'
               'pointer 变量/tw-live/--i 全净化、产物内容（--val/--pin-i/--depth/--flow-path/pathLength）全保留；重载幂等')
    finally:
        ctx.close()


# ---------- 测试 21：skeleton v5.1 canvas FX 仪式层（迭代 F5 / visual-depth.md §四） ----------

def test_fx_v51(browser):
    """(a) 视口内启动：封面 constellation 入视口即配位图尺寸（width 属性就位）
       且逐帧推进（两次像素快照不同）；从未入视口的 closing ascii-field 连
       width 属性都没有（零残留）；(b) 滚到 closing：ascii-field 启动并推进；
       (c) 离屏停帧：滚走后 closing 快照冻结（封面槽位是 data-scroll="cover"
       的 sticky 钉住页，几何上始终在视口内——离屏停帧用普通槽位的 closing
       验证）；(d) freeze()：全部停帧 + 清屏 + 摘除 width/height，fxFrozen 后
       回滚到封面也不再重启；(e) reduced-motion：零 canvas 活动；
       (f) 编辑器路径：加载即冻结（canvas 从未配尺寸），序列化产物 canvas 无
       width/height、往返幂等（全量往返另由 T1-motion-v5 覆盖）。"""
    deck = 'motion-v5'
    problems = []
    CV = "document.querySelector('[data-slide-id=\"%s\"] canvas[data-fx]')"
    ctx, page = fresh_page(browser)
    try:
        page.goto('%s/decks/%s/index.html' % (BASE, deck))
        page.wait_for_timeout(900)

        # (a) 封面 constellation 启动
        cov = page.evaluate("""() => { const c = %s;
          return { hasW: c.hasAttribute('width'), w: c.width, h: c.height }; }""" % CV % 'cover')
        if not cov['hasW'] or cov['w'] < 100:
            problems.append('封面 fx 未配位图尺寸：%r' % cov)
        page.evaluate("window.__snap = %s.toDataURL()" % CV % 'cover')
        page.wait_for_timeout(500)
        if page.evaluate("window.__snap === %s.toDataURL()" % CV % 'cover'):
            problems.append('封面 fx 画面未逐帧推进')

        # 从未入视口的 closing：零残留
        if page.evaluate("%s.hasAttribute('width')" % CV % 'closing'):
            problems.append('未入视口的 closing fx 已有 width 属性（应零初始化）')

        # (b) closing ascii-field 启动
        goto_slide(page, 9)
        page.wait_for_timeout(900)
        clo = page.evaluate("""() => { const c = %s;
          return { hasW: c.hasAttribute('width'), w: c.width }; }""" % CV % 'closing')
        if not clo['hasW']:
            problems.append('closing fx 入视口未启动：%r' % clo)
        page.evaluate("window.__snap3 = %s.toDataURL()" % CV % 'closing')
        page.wait_for_timeout(500)
        if page.evaluate("window.__snap3 === %s.toDataURL()" % CV % 'closing'):
            problems.append('closing fx 画面未逐帧推进')

        # (c) 离屏停帧：滚回普通内容页后 closing 完全离屏 → 停帧
        goto_slide(page, 3)
        page.wait_for_timeout(600)
        page.evaluate("window.__snap2 = %s.toDataURL()" % CV % 'closing')
        page.wait_for_timeout(500)
        if page.evaluate("window.__snap2 !== %s.toDataURL()" % CV % 'closing'):
            problems.append('离屏后 closing fx 仍在绘制（未停帧）')

        # (d) freeze：停帧 + 清屏 + 摘除 width/height，且不再重启
        page.evaluate('window.__pptxMotion.freeze()')
        page.wait_for_timeout(400)
        fz = page.evaluate("""() => Array.from(document.querySelectorAll('canvas[data-fx]'))
          .map(c => ({ w: c.hasAttribute('width'), h: c.hasAttribute('height'),
                       blank: c.toDataURL().length }))""")
        if any(f['w'] or f['h'] for f in fz):
            problems.append('freeze 后 canvas 残留 width/height：%r' % fz)
        goto_slide(page, 0)
        page.wait_for_timeout(600)
        if page.evaluate("%s.hasAttribute('width')" % CV % 'cover'):
            problems.append('freeze 后回滚封面 fx 被重启')
    finally:
        ctx.close()

    # (e) reduced-motion：零 canvas 活动
    ctx3 = browser.new_context(viewport={'width': VIEW_W, 'height': VIEW_H},
                               reduced_motion='reduce')
    pg = ctx3.new_page()
    pg.on('pageerror', lambda e: print('[pageerror]', e))
    try:
        pg.goto('%s/decks/%s/index.html' % (BASE, deck))
        pg.wait_for_timeout(900)
        rm = pg.evaluate("""() => Array.from(document.querySelectorAll('canvas[data-fx]'))
          .map(c => c.hasAttribute('width'))""")
        if any(rm):
            problems.append('reduced-motion 下 fx 被初始化：%r' % rm)
        goto_slide(pg, 9)
        pg.wait_for_timeout(600)
        rm2 = pg.evaluate("""() => Array.from(document.querySelectorAll('canvas[data-fx]'))
          .map(c => c.hasAttribute('width'))""")
        if any(rm2):
            problems.append('reduced-motion 滚动后 fx 被初始化：%r' % rm2)
    finally:
        ctx3.close()

    # (f) 编辑器路径：加载即冻结，序列化产物 canvas 无 width/height
    point_assets(deck)
    src = read_deck(deck)
    ctx4, page4 = fresh_page(browser)
    try:
        page4.goto(BASE + '/harness.html')
        wait_editor_ready(page4)
        load_deck(page4, src, deck + '/index.html')
        ed = deck_frame(page4).evaluate("""() => Array.from(document.querySelectorAll('canvas[data-fx]'))
          .map(c => c.hasAttribute('width'))""")
        if any(ed):
            problems.append('编辑器内 fx 未被冻结：%r' % ed)
        saved = save_and_capture(page4)
        if re.search(r'<canvas[^>]*\s(?:width|height)=', saved):
            problems.append('保存产物 canvas 残留 width/height')
        n_fx = len(re.findall(r'<canvas data-fx="(?:constellation|starfield|particle-drift|ascii-field)"', saved))
        if n_fx != 2:
            problems.append('保存产物 fx 实例数异常：%d' % n_fx)
        load_deck(page4, saved, deck + '/index.html')
        saved2 = save_and_capture(page4)
        if saved2 != saved:
            problems.append('fx deck 编辑器往返不幂等')
    finally:
        ctx4.close()

    report('T21-fx-v51', 'canvas FX 仪式层（F5）', not problems,
           '；'.join(problems) if problems else
           '视口内启动/离屏停帧/回屏续播全过；未入视口零初始化；freeze 停帧+摘除尺寸且不重启；'
           'reduced-motion 零 canvas 活动；编辑器加载即冻结、产物无 width/height、往返幂等')


# ---------- 测试 15：信息图系统 v2 组件标记合规（迭代 D / infographic-system.md） ----------

# components.md §1 合法项数区间 + §3 适配矩阵白名单（✓/△ 均算允许，✗ 禁止）的镜像。
# v2 → v3（F2）：新增构图谱系（§11）与容器规格（§12）均为叙述/纪律层，未改族、骨架、
# 皮肤与项数区间，故本镜像表语义不变。新增族/骨架/皮肤时两端必须同步——这是
# "适配矩阵静态可验"的落点。
IG_RANGES = {
    'list-row': (3, 5), 'list-grid': (4, 6), 'list-zigzag': (3, 6),
    'list-waterfall': (3, 5), 'list-pyramid': (3, 5),
    'sequence-steps': (3, 5), 'sequence-timeline': (3, 5), 'sequence-stairs': (3, 5),
    'sequence-funnel': (3, 6), 'sequence-snake': (5, 8),
    'compare-binary-cols': (2, 2), 'compare-quadrant': (4, 4),
    'compare-swot': (4, 4), 'compare-vs-overlay': (2, 2),
    'hierarchy-concentric': (2, 4),
    'relation-flow': (3, 6), 'relation-network': (4, 8), 'relation-circle-loop': (3, 5),
}
IG_ALLOWED = {   # 族 × 皮肤白名单（chart 族不参与矩阵，跳过）
    'list': {'bare', 'card', 'badge', 'ribbon', 'stat', 'icon-line'},
    'sequence': {'bare', 'card', 'badge', 'ribbon', 'stat', 'icon-line'},
    'compare': {'bare', 'card', 'badge', 'ribbon', 'stat', 'icon-line'},
    'hierarchy': {'bare', 'card', 'badge', 'icon-line'},
    'relation': {'bare', 'card', 'badge', 'icon-line'},
}

def test_infographic_v2(browser):
    """infographic-d1（skeleton v3，5 结构族 × 4 皮肤 + 嵌套 chart + 标注修饰件）：
    (a) 族×皮肤组合在白名单内、项数 ∈ 合法区间（binary 恰好 2 项等硬断言）；
    (b) 每个 Item 含可编辑文字；容器不带 data-editable；装饰元素 skip；
    (c) 嵌套 chart 小图按图表分层（几何 skip、标签/数值 editable）；
    (d) 标注修饰件：旗标文字 editable、引线 skip；
    (e) 编辑 Item 文字 → 保存 → 辅助标记保留、产物净化 → 重载再保存逐字节幂等。"""
    deck = 'infographic-d1'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')
        df = deck_frame(page)

        # (a)+(b) 结构族根：项数区间、白名单、Item 可编辑文字、容器不带 data-editable
        roots = df.evaluate("""() => Array.from(document.querySelectorAll('[data-ig]')).map(r => ({
          ig: r.getAttribute('data-ig'), skin: r.getAttribute('data-ig-skin'),
          items: r.querySelectorAll(':scope [data-ig-item]').length,
          rootEditable: r.hasAttribute('data-editable'),
          itemsNoText: Array.from(r.querySelectorAll(':scope [data-ig-item]'))
            .filter(i => !i.querySelector('[data-editable]')).length,
          nested: !!r.querySelector('[data-ig]') }))""")
        n_struct = 0
        for r in roots:
            if r['ig'].startswith('chart-'):
                if r['skin'] is not None:
                    problems.append('chart 族不参与皮肤矩阵，不应带 data-ig-skin：%r' % r['ig'])
                continue
            n_struct += 1
            fam = r['ig'].split('-')[0]
            if r['skin'] not in IG_ALLOWED.get(fam, set()):
                problems.append('族×皮肤禁止组合：%s × %s' % (r['ig'], r['skin']))
            lo, hi = IG_RANGES.get(r['ig'], (None, None))
            if lo is None:
                problems.append('未知骨架（IG_RANGES 未收录）：%s' % r['ig'])
            elif not (lo <= r['items'] <= hi):
                problems.append('%s 项数=%d，超出区间 [%d,%d]' % (r['ig'], r['items'], lo, hi))
            if r['rootEditable']:
                problems.append('%s 容器误标 data-editable' % r['ig'])
            if r['itemsNoText']:
                problems.append('%s 有 %d 个 Item 不含可编辑文字' % (r['ig'], r['itemsNoText']))
        if n_struct != 5:
            problems.append('结构族主体数=%d，期望 5（list/sequence/compare/hierarchy/relation）' % n_struct)
        nested_roots = [r['ig'] for r in roots if r['nested']]
        if nested_roots != ['sequence-steps']:
            problems.append('嵌套位置异常：%r（期望仅 sequence-steps 内嵌 chart）' % nested_roots)

        # (c) 嵌套 chart：几何 skip、标签/数值 editable
        nest = df.evaluate("""() => {
          const c = document.querySelector('[data-ig="chart-progress"]');
          if (!c) return null;
          return { inItem: !!c.closest('[data-ig-item]'),
                   skips: c.querySelectorAll('[data-editable-skip]').length,
                   edits: c.querySelectorAll('[data-editable]').length,
                   fills: c.querySelectorAll('[data-anim="fill-bar"]').length };
        }""")
        if not nest or not nest['inItem']:
            problems.append('嵌套 chart 不在 Item 内：%r' % nest)
        elif not (nest['skips'] == 2 and nest['edits'] == 4 and nest['fills'] == 2):
            problems.append('嵌套 chart 分层异常：%r（期望 skip=2 轨道、editable=2 标签+2 数值、fill-bar=2）' % nest)

        # (d) 标注修饰件：旗标文字 editable、引线（draw-line 在 skip 容器内）
        anno = df.evaluate("""() => {
          const slide = document.querySelector('[data-slide-id="member-loop"]');
          const flag = Array.from(slide.querySelectorAll('[data-editable]'))
            .find(e => e.textContent.includes('会员贡献营收'));
          const path = slide.querySelector('path[data-anim="draw-line"]');
          return { flag: !!flag,
                   lead: !!(path && path.closest('[data-editable-skip]')) };
        }""")
        if not anno['flag']:
            problems.append('标注旗标文字不可编辑')
        if not anno['lead']:
            problems.append('标注引线未标 data-editable-skip')

        # (b2) 结构装饰抽查：steps 连接线、VS 徽章、同心圆环、闭环箭头
        deco = df.evaluate("""() => ({
          stepsLine: !!document.querySelector('[data-slide-id="launch-pipeline"] [data-ig] > [data-editable-skip]'),
          vs: !!document.querySelector('[data-slide-id="channel-compare"] [data-ig] > [data-editable-skip]'),
          rings: document.querySelectorAll('[data-slide-id="brand-system"] [data-ig] > [data-editable-skip]').length,
          arrows: document.querySelectorAll('[data-slide-id="member-loop"] [data-ig] > [data-editable-skip]').length,
          stylize: document.querySelectorAll('[data-stylize]').length })""")
        if not (deco['stepsLine'] and deco['vs']):
            problems.append('steps 连接线 / VS 徽章未标 skip：%r' % deco)
        if deco['rings'] != 3 or deco['arrows'] != 5:
            problems.append('同心圆环/闭环箭头装饰标记数异常：%r' % deco)
        if deco['stylize'] != 0:
            problems.append('D1 为 flat 质感主题，不应出现 data-stylize：%d' % deco['stylize'])

        # (e) 编辑 Item 文字 → 保存 → 标记保留 + 净化 → 重载幂等
        title = deck_loc(page, '[data-slide-id="launch-pipeline"] [data-ig-item] p[data-editable]:has-text("杯测校准")')
        title.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        title.click(); title.click()
        page.keyboard.type('杯测校准与定版')
        page.keyboard.press('Control+Enter')
        saved = save_and_capture(page)
        with open(os.path.join(RESULTS, deck + '.edited.html'), 'w', encoding='utf-8') as f:
            f.write(saved)
        problems += assert_clean_output(deck, saved, [
            ('Item 文字编辑未生效', '杯测校准与定版' in saved),
            ('data-ig 辅助标记丢失', saved.count('data-ig="') == 6 and saved.count('data-ig-item') == 18),
            ('嵌套 fill-bar 丢失', ('width:92%' in saved or 'width: 92%' in saved) and 'data-anim="fill-bar"' in saved),
            ('标注旗标丢失', '会员贡献营收 63%' in saved),
        ])
        load_deck(page, saved, deck + '/index.html')
        saved2 = save_and_capture(page)
        if saved2 != saved:
            problems.append('重载再保存不幂等')

        report('T15-infographic-v2', '信息图 v2 标记合规', not problems,
               '；'.join(problems) if problems else
               '5 族 × 4 皮肤白名单通过；binary=2 等项数硬断言通过；Item 文字可编辑、装饰 skip、'
               '嵌套 chart 分层正确；标注文字 editable / 引线 skip；编辑往返幂等且标记保留')
    finally:
        ctx.close()


# ---------- 测试 18：组件画廊 F2+F3（components.md v3 §11/§12 + charts.md v2 + gallery/） ----------

# F3 新增图表类型的 chart 族根（data-ig="chart-*"）覆盖清单——charts.md v2 扩展九 +
# 存量 chart-progress（p13 嵌套实例）。新增图表类型时两端必须同步。
CHART_IGS = {'chart-progress', 'chart-stacked', 'chart-grouped', 'chart-area',
             'chart-waterfall', 'chart-scatter', 'chart-radar', 'chart-slope',
             'chart-funnel', 'chart-heatmap'}

def test_gallery_f2(browser):
    """gallery/index.html（skeleton v4，61 页，多主题 sampler + 29 主题样张 + §13 六型容器 + v7.2 文字呈现/装饰线页组）：
    (a) 零溢出：每页全部 [data-editable] 元素矩形落在画布内（±2px）；
    (b) 零重叠：同页可编辑元素两两矩形不相交（>16px² 才算，排除祖先包含）；
    (c) data-ig 根：族×皮肤 ∈ 白名单、项数 ∈ 区间（复用 T15 镜像表，chart- 前缀跳过）；
    (d) 覆盖断言：6 结构族 × 6 皮肤全部出现；
    (e) 谱系节奏纪律（components.md §11）：mastfoot 声明抽取，无连续 3 页同谱系；
    (f) F3 图表页：chart 族根覆盖 10 类（CHART_IGS）；每根几何 skip + 标签/标注 editable；
        几何抽验——瀑布图累计水位衔接（首末柱贴基线、逐段连续、终点==起点+ΣΔ）、
        雷达图顶点半径 ∝ 数据值、斜率图端点 y == 数据线性映射（data-geo/data-vals
        是画廊自带的测量钩子，编辑契约之外、序列化原样保留）。
    测量在 1920×1080 视口 + reduced-motion 下进行（动效零位移，布局即终态）。"""
    deck = 'components-gallery'
    src = read_deck(deck)
    problems = []
    ctx = browser.new_context(viewport={'width': 1920, 'height': 1080},
                              reduced_motion='reduce')
    page = ctx.new_page()
    page.on('pageerror', lambda e: print('[pageerror]', e))
    try:
        page.goto('%s/decks/%s/index.html' % (BASE, deck))
        page.wait_for_timeout(800)
        # content-visibility:auto 下远屏页不排版——先强制全部排版本再测量（仅测量页，不保存）
        page.evaluate("""() => document.querySelectorAll('.slide-slot')
          .forEach(s => s.style.contentVisibility = 'visible')""")
        page.wait_for_timeout(400)

        # (a)+(b) 逐页溢出 / 重叠
        geo = page.evaluate("""() => {
          const out = [];
          document.querySelectorAll('.slide').forEach(slide => {
            const sr = slide.getBoundingClientRect();
            const els = Array.from(slide.querySelectorAll('[data-editable]'));
            const rs = els.map(el => ({ el, r: el.getBoundingClientRect() }));
            rs.forEach(({el, r}) => {
              if (r.left < sr.left - 2 || r.top < sr.top - 2 ||
                  r.right > sr.right + 2 || r.bottom > sr.bottom + 2)
                out.push(slide.dataset.slideId + ' 溢出: ' + el.tagName + ' "' +
                  (el.textContent || '').trim().slice(0, 16) + '"');
            });
            for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) {
              const a = rs[i], b = rs[j];
              if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
              const ix = Math.max(0, Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left));
              const iy = Math.max(0, Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top));
              if (ix * iy > 16)
                out.push(slide.dataset.slideId + ' 重叠: "' +
                  (a.el.textContent || '').trim().slice(0, 12) + '" × "' +
                  (b.el.textContent || '').trim().slice(0, 12) + '"');
            }
          });
          return out;
        }""")
        problems += geo

        # (c) data-ig 根校验（镜像 T15 口径）
        roots = page.evaluate("""() => Array.from(document.querySelectorAll('[data-ig]')).map(r => ({
          ig: r.getAttribute('data-ig'), skin: r.getAttribute('data-ig-skin'),
          items: r.querySelectorAll(':scope [data-ig-item]').length,
          rootEditable: r.hasAttribute('data-editable'),
          edits: r.querySelectorAll('[data-editable]').length,
          skips: r.querySelectorAll('[data-editable-skip]').length,
          itemsNoText: Array.from(r.querySelectorAll(':scope [data-ig-item]'))
            .filter(i => !i.querySelector('[data-editable]')).length }))""")
        fams, skins = set(), set()
        n_struct = 0
        chart_igs = set()
        for r in roots:
            if r['ig'].startswith('chart-'):
                if r['skin'] is not None:
                    problems.append('chart 族不应带 data-ig-skin：%r' % r['ig'])
                chart_igs.add(r['ig'])
                # (f) 图表根分层：几何 skip + 标签/标注 editable 都必须存在
                if r['skips'] < 1:
                    problems.append('%s 缺几何 skip 层' % r['ig'])
                if r['edits'] < 3:
                    problems.append('%s 可编辑标签/标注不足（%d 个）' % (r['ig'], r['edits']))
                continue
            n_struct += 1
            fam = r['ig'].split('-')[0]
            fams.add(fam); skins.add(r['skin'])
            if r['skin'] not in IG_ALLOWED.get(fam, set()):
                problems.append('族×皮肤禁止组合：%s × %s' % (r['ig'], r['skin']))
            lo, hi = IG_RANGES.get(r['ig'], (None, None))
            if lo is None:
                problems.append('未知骨架（IG_RANGES 未收录）：%s' % r['ig'])
            elif not (lo <= r['items'] <= hi):
                problems.append('%s 项数=%d，超出区间 [%d,%d]' % (r['ig'], r['items'], lo, hi))
            if r['rootEditable']:
                problems.append('%s 容器误标 data-editable' % r['ig'])
            if r['itemsNoText']:
                problems.append('%s 有 %d 个 Item 不含可编辑文字' % (r['ig'], r['itemsNoText']))
        if n_struct != 13:
            problems.append('结构族主体数=%d，期望 13' % n_struct)
        if chart_igs != CHART_IGS:
            problems.append('图表根覆盖异常：缺 %r / 多 %r' % (CHART_IGS - chart_igs, chart_igs - CHART_IGS))

        # (d) 6 族 × 6 皮肤全覆盖
        if fams != {'list', 'sequence', 'compare', 'hierarchy', 'relation'}:
            problems.append('结构族覆盖不全：%r' % fams)
        if skins != {'bare', 'card', 'badge', 'ribbon', 'stat', 'icon-line'}:
            problems.append('皮肤覆盖不全：%r' % skins)

        # (e) 谱系节奏：封面=宣言，guide=说明页跳过，其余取 mastfoot 右槽"谱系：X"
        lineages = page.evaluate("""() => Array.from(document.querySelectorAll('.slide')).map(s => {
          if (s.dataset.slideId === 'cover') return '宣言';
          const spans = s.querySelectorAll('.mastfoot span');
          if (!spans.length) return null;
          const m = /谱系：(\\S+)/.exec(spans[spans.length - 1].textContent);
          if (!m) return null;
          const g = m[1].split('·')[0].trim();
          return g === '—' || g === '—（说明页）' ? null : g;
        })""")
        for i in range(len(lineages) - 2):
            trio = lineages[i:i + 3]
            if trio[0] and trio[0] == trio[1] == trio[2]:
                problems.append('连续 3 页同谱系：%r（页 %d-%d）' % (trio[0], i + 1, i + 3))
        seen = set(g for g in lineages if g)
        if seen != {'宣言', '数据英雄', '网格矩阵', '轴与节点', '图文证据', '裂屏对开'}:
            problems.append('谱系覆盖异常：%r' % seen)

        # (f) F3 几何抽验：瀑布 / 雷达 / 斜率
        wf = page.evaluate("""() => Array.from(document.querySelectorAll(
          '[data-slide-id="profit-waterfall"] [data-geo="wf-bar"]'))
          .map(b => ({ bottom: parseFloat(b.style.bottom), height: parseFloat(b.style.height) }))""")
        if len(wf) != 7:
            problems.append('瀑布图柱数=%d，期望 7' % len(wf))
        else:
            FLOOR = 56.0
            if wf[0]['bottom'] != FLOOR or wf[6]['bottom'] != FLOOR:
                problems.append('瀑布图首末柱未贴基线：%r / %r' % (wf[0], wf[6]))
            # 累计水位链：level = 前柱的"接力水位"（前柱升→柱顶，降→柱底）；
            # 本柱升则底接水位、降则顶接水位，接不上即断裂
            level = wf[0]['bottom'] + wf[0]['height']
            for i in range(1, 6):
                rise = abs(wf[i]['bottom'] - level)
                fall = abs(wf[i]['bottom'] + wf[i]['height'] - level)
                if min(rise, fall) > 1:
                    problems.append('瀑布图第 %d 段累计水位断裂：bottom=%s h=%s 水位=%s' % (
                        i + 1, wf[i]['bottom'], wf[i]['height'], level))
                level = (wf[i]['bottom'] + wf[i]['height']) if rise <= fall else wf[i]['bottom']
            if abs(level - (FLOOR + wf[6]['height'])) > 1:
                problems.append('瀑布图终点柱高与累计不符：水位 %s vs 终点柱 %r' % (level, wf[6]))

        radar = page.evaluate("""() => {
          const p = document.querySelector('[data-slide-id="radar-stack"] polygon[data-geo="radar-series"]');
          if (!p) return null;
          return { pts: p.getAttribute('points'), vals: p.getAttribute('data-vals'),
                   cx: +p.getAttribute('data-cx'), cy: +p.getAttribute('data-cy'), r: +p.getAttribute('data-r') };
        }""")
        if not radar:
            problems.append('雷达图测量钩子缺失')
        else:
            pts = [tuple(map(float, xy.split(','))) for xy in radar['pts'].split()]
            vals = [float(v) for v in radar['vals'].split(',')]
            if len(pts) != 6 or len(vals) != 6:
                problems.append('雷达图顶点/数值数不符：%d vs %d' % (len(pts), len(vals)))
            else:
                for i, ((x, y), v) in enumerate(zip(pts, vals)):
                    dist = math.hypot(x - radar['cx'], y - radar['cy'])
                    if abs(dist - v / 100 * radar['r']) > 1.5:
                        problems.append('雷达顶点 %d 半径 %.1f ≠ 值 %.0f 映射 %.1f' % (
                            i, dist, v, v / 100 * radar['r']))
                    ang = math.atan2(y - radar['cy'], x - radar['cx'])
                    want = -math.pi / 2 + i * math.pi / 3
                    diff = (ang - want + math.pi) % (2 * math.pi) - math.pi  # 角度归一到 [-π,π]
                    if abs(diff) > 0.02:
                        problems.append('雷达顶点 %d 角度偏差 %.3f rad' % (i, diff))

        slope = page.evaluate("""() => Array.from(document.querySelectorAll(
          '[data-slide-id="slope-cities"] line[data-geo="slope-line"]'))
          .map(l => ({ y1: +l.getAttribute('y1'), y2: +l.getAttribute('y2'),
                       v1: +l.getAttribute('data-v1'), v2: +l.getAttribute('data-v2') }))""")
        if len(slope) != 5:
            problems.append('斜率图线数=%d，期望 5' % len(slope))
        else:
            for i, s in enumerate(slope):
                w1, w2 = 600 * (1 - s['v1'] / 30), 600 * (1 - s['v2'] / 30)
                if abs(s['y1'] - w1) > 0.6 or abs(s['y2'] - w2) > 0.6:
                    problems.append('斜率线 %d 端点不映射数据：(%s,%s) vs (%s,%s)' % (
                        i, s['y1'], s['y2'], w1, w2))

        report('T18-gallery-f2', '组件画廊 F2+F3', not problems,
               '；'.join(problems) if problems else
               '61 页零溢出零重叠；13 族根 + 10 图表根白名单/分层全过；6 族 × 6 皮肤全覆盖；6 谱系无连续 3 页同谱系；'
               '瀑布水位/雷达顶点/斜率端点几何抽验通过')
    finally:
        ctx.close()


# ---------- 测试 16：图片槽位契约静态校验器（迭代 E / 契约 v5） ----------

CHECK_IMAGES = os.path.join(ROOT, 'skills/html-pptx/scripts/check-images.mjs')

def run_check_images(*args):
    return subprocess.run(['node', CHECK_IMAGES, *args], capture_output=True, text=True)

def test_check_images():
    """(a) 合规 deck（charts-a3 + culture-kraft，v5 三属性齐全）通过且无警告；
    (b) 存量无槽位 deck（tech-ikb）警告但退出码 0；
    (c) 插画模式（--mode illustration）下 placeholder 残留 → 报错且非零退出；
    (d) 幂等：重跑结果逐字节一致；
    (e) G7 分辨率下限：bake-mix 合规通过；页面级槽位 1280×720（<2560×1440）报错；
    页内槽位短边 <640px 报错（负例均在临时副本上，fixture 不动）；
     (f) G7 适用范围（2026-10-21 裁决）：同一张 512×288 小图，state=uploaded → 降级为告警
    且 rc=0（真实素材原样保留，放大它等于伪造来源），state=generated → 仍报错（生成侧纪律没被放开）。"""
    problems = []
    ok_decks = [os.path.join(ROOT, 'tests/decks', d, 'index.html') for d in ('charts-a3', 'culture-kraft')]
    r1 = run_check_images(*ok_decks)
    if r1.returncode != 0 or 'WARN' in (r1.stdout + r1.stderr):
        problems.append('合规 deck 未零警告通过：rc=%d %s%s' % (r1.returncode, r1.stdout, r1.stderr))
    r2 = run_check_images(os.path.join(ROOT, 'tests/decks/tech-ikb/index.html'))
    if r2.returncode != 0 or r2.stderr.count('缺 data-image-slot') != 2:
        problems.append('存量 deck 警告路径异常：rc=%d stderr=%s' % (r2.returncode, r2.stderr.strip()[:200]))
    r3 = run_check_images(ok_decks[0], '--mode', 'illustration')
    if r3.returncode == 0 or 'placeholder 状态槽位' not in r3.stderr:
        problems.append('插画模式反降级未报错：rc=%d %s' % (r3.returncode, r3.stderr.strip()[:200]))
    r1b = run_check_images(*ok_decks)
    if (r1b.returncode, r1b.stdout, r1b.stderr) != (r1.returncode, r1.stdout, r1.stderr):
        problems.append('重跑结果不一致（非幂等）')
    # (e) G7 绝对分辨率下限：合规基线 + 两类负例（临时副本，不改 fixture）
    bake_src = os.path.join(ROOT, 'tests/decks/bake-mix')
    r4 = run_check_images(os.path.join(bake_src, 'index.html'))
    if r4.returncode != 0 or 'WARN' in (r4.stdout + r4.stderr):
        problems.append('bake-mix（2560×1440 页面级 + 1280×720 页内）未零警告通过：rc=%d %s%s'
                        % (r4.returncode, r4.stdout, r4.stderr))
    with tempfile.TemporaryDirectory(prefix='check-images-floor-') as tmp:
        import shutil as _sh
        deck_dir = os.path.join(tmp, 'bake-mix')
        _sh.copytree(bake_src, deck_dir)
        deck_html = os.path.join(deck_dir, 'index.html')
        # 页面级槽位低于 2560×1440 → 报错
        Image.new('RGB', (1280, 720), (128, 128, 128)).save(
            os.path.join(deck_dir, 'assets', 'page-ch-baked.png'))
        r5 = run_check_images(deck_html)
        if r5.returncode == 0 or '页面级槽位素材分辨率不足' not in r5.stderr:
            problems.append('页面级分辨率下限未报错：rc=%d %s' % (r5.returncode, r5.stderr.strip()[:200]))
        # 页面级合规 + 页内槽位短边 <640px → 报错
        Image.new('RGB', (2560, 1440), (128, 128, 128)).save(
            os.path.join(deck_dir, 'assets', 'page-ch-baked.png'))
        Image.new('RGB', (512, 288), (128, 128, 128)).save(
            os.path.join(deck_dir, 'assets', 'now-illustration.png'))
        r6 = run_check_images(deck_html)
        if r6.returncode == 0 or '页内槽位素材分辨率不足' not in r6.stderr:
            problems.append('页内分辨率下限未报错：rc=%d %s' % (r6.returncode, r6.stderr.strip()[:200]))
        # 页内槽位短边 ≥640px → 恢复通过
        Image.new('RGB', (1280, 720), (128, 128, 128)).save(
            os.path.join(deck_dir, 'assets', 'now-illustration.png'))
        r7 = run_check_images(deck_html)
        if r7.returncode != 0:
            problems.append('页内 1280×720 合规图未通过：rc=%d %s' % (r7.returncode, r7.stderr.strip()[:200]))
        # (f) G7 适用范围（2026-10-21 裁决，docs/design/g7-resolution-floor-scope.md）：
        #     uploaded 真实素材不达标 → 告警且 rc=0；同尺寸但 generated → 仍报错。
        Image.new('RGB', (512, 288), (128, 128, 128)).save(os.path.join(deck_dir, 'assets', 'now-illustration.png'))
        slot_marker = 'data-image-slot="now-illustration-16x9"'

        def set_slot_state(html_text, state_value):
            """按槽位定位 img 标签再改 state——不假设属性顺序（外层正则无分组，取 group(0)）。"""
            def patch(match):
                return re.sub(r'(data-image-state=")[a-z]+(")', r'\g<1>' + state_value + r'\g<2>', match.group(0), count=1)
            return re.sub(r'<img[^>]*' + re.escape(slot_marker) + r'[^>]*>', patch, html_text, count=1)

        with open(deck_html, encoding='utf-8') as fh:
            html_text = fh.read()
        probe = set_slot_state(html_text, 'uploaded')
        if probe == html_text or 'data-image-state="uploaded"' not in probe:
            problems.append('适用范围断言无法改写 fixture 的 now-illustration 图位（测试自身需修）')
        else:
            for state_value, expect_error in (('uploaded', False), ('generated', True)):
                with open(deck_html, 'w', encoding='utf-8') as fh:
                    fh.write(set_slot_state(html_text, state_value))
                r8 = run_check_images(deck_html)
                if expect_error:
                    if r8.returncode == 0 or '页内槽位素材分辨率不足' not in r8.stderr:
                        problems.append('generated 小图被豁免误放行：rc=%d %s' % (r8.returncode, r8.stderr.strip()[:200]))
                else:
                    if r8.returncode != 0 or 'uploaded 真实素材' not in r8.stderr:
                        problems.append('uploaded 小图未按裁决降级为告警：rc=%d %s' % (r8.returncode, r8.stderr.strip()[:200]))
            with open(deck_html, 'w', encoding='utf-8') as fh:
                fh.write(html_text)
    report('T16-check-images', '槽位契约静态校验器', not problems,
           '；'.join(problems) if problems else
           '合规 deck 零警告通过；存量 deck 2 警告 rc=0；插画模式 placeholder 残留 rc=1；重跑幂等；'
           'G7 分辨率下限：页面级 <2560×1440 报错、页内短边 <640px 报错、合规图通过；'
           'G7 适用范围：uploaded 小图告警不阻断、generated 小图仍报错')

# ---------- 测试 23：页级 content-hash（三形态 M1 / tri-form-architecture.md §4.3） ----------

def test_hash_check():
    """l_hash_check.py 作为子进程纳入回归：提取幂等 / 编辑翻转 /
    编辑器 Web Crypto 端与 extractor 端 hash 双端一致 / 产物每页 12 位 hex。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/l_hash_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T23-hash', '页级 content-hash（M1）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 24：页面烙入模式（三形态 M2 / page-render-mode.md §6） ----------

def test_bake_check():
    """m_bake_check.py 作为子进程纳入回归（沿用 T23 加 l_hash_check 的约定）：
    契约 v7 三要素静态校验 / 源层保留与回退 / 指令编译合规（Text 段精确子串）/
    编辑器源层跳过与保存幂等 / hash 翻转 / 混合 deck 渲染与章节跳转回归 /
    失败回退演练。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/m_bake_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T24-bake', '页面烙入模式（M2）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 25：HTML→PPTX 导出管线（三形态 M3 / pptx-export-svg.md §6） ----------

def test_export_pptx():
    """n_fidelity_check.py 作为子进程纳入回归（沿用 T23/T24 约定）：
    全流程出口与耗时 / postflight 结构复核 / 保真阈值（平均 diff<2%、单页<5%）/
    manifest schema / stale 检出 / 降级演练（屏蔽 pdftocairo、屏蔽截图）/
    单向纪律 / 门禁演练（伪造漂移基线阻断）。
    命名偏差：设计文档称 m_fidelity_check.py，m_ 已被 m_bake_check 占用，用 n_。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/n_fidelity_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T25-export', 'HTML→PPTX 导出管线（M3）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 26：编辑器 v3 三态工作台与翻转对比（三形态 M4 / editor-tri-view.md §7） ----------

def test_tri_view_check():
    """o_tri_view_check.py 作为子进程纳入回归（沿用 T23–T25 约定）：
    HTTP 通道 manifest 读取 / 对比默认落定并排 + 无产物页黑面 / 背面三态
    （就绪 SVG / 黑面空态 / 过期水印）/ stale 闭环（改字保存→水印→重跑导出→
    水印消失）/ 烙入页源层编辑 / 导出面板四页与载体保真分 / 嵌入态
    export-intent 消息 / 降级引导 / 翻面与 reduced-motion。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/o_tri_view_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T26-tri-view', '编辑器 v3 三态工作台（M4）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 27：可编辑 PPTX 导出 C1（子技能 C / pptx-export-editable.md §7） ----------

def test_editable_check():
    """p_editable_check.py 作为子进程纳入回归（沿用 T23–T26 约定）：
    文本逐字（extractor 文本 ⊆ slide XML）/ 几何抽验 ≤2% / wrap=square +
    框宽=渲染宽度 / 字号 px→pt 映射 / CJK run 双 typeface a:ea / 烙入页满幅
    p:pic / 单向纪律 / native_text_ratio=1.0（fixture bake-mix + smartforge-c1）。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/p_editable_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T27-editable', '可编辑 PPTX 导出 C1+C2（子技能 C）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 28：生成侧容量门禁（C5a / 0924_editable_overlap_fix.md §七） ----------

def test_capacity_check():
    """q_capacity_check.py 作为子进程纳入回归（沿用 T23–T27 约定）：
    正例 bake-mix 0 违规 / 负例合成超限容器被抓（水平+垂直+净距三规则）/ 幂等。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/q_capacity_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T28-capacity', '生成侧容量门禁（C5a）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 29：编辑器↔Agent bridge v2（P0–P2 自动组） ----------

def test_bridge_check():
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/r_bridge_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T29-bridge', '编辑器↔Agent bridge v2（P0–P2）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 30：生图色彩一致性后置校验与评审 rubric（imagegen v2 G2/G3） ----------

def test_harmony_check():
    """w_harmony_check.py 作为子进程纳入回归（沿用 T23–T29 约定）：
    三图判定（纯 token 全过 / 纯无关色 A+B / 烙入页豁免只触发 A）/
    告警不阻断与 ≥50% 双触发阻断 / --strict 升级 / ledger 写入与不强行创建 /
    幂等 / CIEDE2000 自检 / adapter --rubric-json 透传。
    命名偏差：设计文档称 r_harmony_check.py，r–v 已被既有子检查占用，用 w_。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/w_harmony_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T30-harmony', '生图色彩一致性与评审 rubric（imagegen v2 G2/G3）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 31：需求脑暴页（Step 0.5 / briefing.md；含 imagegen v2 G1 烙入三态） ----------

def test_brief_check():
    """k_brief_check.py 作为子进程纳入回归（沿用 T23–T30 约定）：覆盖层懒渲染 /
    缺省标注 / 叙事弧条件显示 / 简报文本与 JSON 输出 / 三态提交路由文案 /
    抽屉状态隔离 / 烙入策略三态与 bake_intent 缺省展开（G1）。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/k_brief_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T31-brief', '需求脑暴页（含 G1 烙入三态）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 35：动态脑暴（briefing v2 P1 / brief-dynamic-brainstorming.md §11） ----------

def test_dynamic_brief_check():
    """y_dynamic_brief_check.py 作为子进程纳入回归（沿用 T23–T31 约定）：
    open_editor(brief_options=...) 注入全链路 + 浏览器动态渲染三态 / schema 拒收
    原值不变 / 无参回落静态问卷 / 覆盖语义（带参替换、不带参保持）/ 嵌入态入站
    pptx-html:brief-options 注入与非法回落 / 动态作答提交 design-brief JSON 键结构
    与静态提交 diff 为空（仅多可选 extras）。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/y_dynamic_brief_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T35-dynamic-brief', '动态脑暴（briefing v2 P1）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))

# ---------- 测试 17：图片上传置 state=uploaded（迭代 E / 契约 v5） ----------

def test_image_upload_state(browser):
    """headless 无法驱动 FSAA 系统弹窗：stub showOpenFilePicker/showDirectoryPicker
    后调用真实 replaceImage（同名覆盖分支）——上传成功后 img 置
    data-image-state="uploaded"（slot/intent 保留）、置脏，保存产物持久化且 ?v= 剥离。"""
    deck = 'culture-kraft'
    point_assets(deck)
    src = read_deck(deck)
    ctx, page = fresh_page(browser)
    problems = []
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html')
        ef = editor_frame(page)
        ef.evaluate("""() => {
          window.showOpenFilePicker = async () => [{
            name: 'village-fields.svg',
            getFile: async () => new File(
              ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3"></svg>'],
              'village-fields.svg', { type: 'image/svg+xml' })
          }];
          window.showDirectoryPicker = async () => ({
            requestPermission: async () => 'granted',
            getFileHandle: async () => ({ createWritable: async () => (
              { write: async () => {}, close: async () => {} }) })
          });
        }""")
        r = ef.evaluate("""async () => {
          const img = document.getElementById('deckFrame').contentDocument
            .querySelector('[data-slide-id="the-land"] img[data-editable-image]');
          await window.replaceImage(img);
          return { state: img.getAttribute('data-image-state'),
                   slot: img.getAttribute('data-image-slot'),
                   intent: img.getAttribute('data-image-intent'),
                   src: img.getAttribute('src'),
                   dirty: window.state.dirty };
        }""")
        if r['state'] != 'uploaded':
            problems.append('上传后 state=%r，期望 uploaded' % r['state'])
        if r['slot'] != 'village-fields-4x3' or '田野' not in (r['intent'] or ''):
            problems.append('slot/intent 未保留：%r' % r)
        if not (r['src'] or '').startswith('assets/village-fields.svg?v='):
            problems.append('同名覆盖分支 src 异常：%r' % r['src'])
        if r['dirty'] is not True:
            problems.append('上传未置脏')
        saved = save_and_capture(page)
        for label, cond in [
            ('state=uploaded 未持久化', 'data-image-state="uploaded"' in saved),
            ('slot 未持久化', 'data-image-slot="village-fields-4x3"' in saved),
            ('intent 未持久化', 'data-image-intent="层叠田野与远山的乡土意象' in saved),
            ('src 残留 ?v=', 'village-fields.svg?v=' not in saved),
        ]:
            if not cond:
                problems.append(label)
        report('T17-upload-state', '图片上传 state 翻转', not problems,
               '；'.join(problems) if problems else
               'stub FSAA 走真实 replaceImage：state→uploaded、slot/intent 保留、置脏、保存产物持久化（?v= 已剥离）')
    finally:
        ctx.close()


# ---------- 测试 22：章节跳转与 v7 动效（K 期 / skeleton v7 / 契约 v6.3） ----------

def test_nav_v7(browser):
    """smartforge-c1（高密度验收 deck，skeleton v7）：
    (a) 数字键直跳第 N 章（data-chapter 注册序）；(b) 封面 nav-link 点击平滑跳转；
    (c) End 键到末页；(d) 编辑器态 nav-link 点击被拦截、不跳转（契约 v6.3）；
    (e) data-rotate 轮转 in-view 启动、freeze 清空 .active；
    (f) 保存产物：mend-bar 的 --from/--val 保留、.active 无残留、nav-link 与
    data-chapter 原样保留。"""
    deck = 'smartforge-c1'
    src = read_deck(deck)
    problems = []
    ctx, page = fresh_page(browser)
    try:
        # —— 直开 deck（无编辑器，验骨架行为） ——
        page.goto('%s/decks/%s/index.html' % (BASE, deck))
        page.wait_for_timeout(900)
        nav = page.evaluate("""() => {
          const deck = document.getElementById('deck');
          const slots = [...document.querySelectorAll('.slide-slot')];
          const ch = slots.filter(s => s.querySelector('.slide[data-chapter]'));
          return { nCh: ch.length, nSlots: slots.length,
                   tops: ch.map(s => s.offsetTop),
                   links: document.querySelectorAll('a.nav-link[href^="#"]').length };
        }""")
        if nav['nCh'] < 3:
            problems.append('data-chapter 章节数=%d（<3）' % nav['nCh'])
        if nav['links'] < nav['nCh']:
            problems.append('封面 nav-link 数=%d < 章节数=%d' % (nav['links'], nav['nCh']))

        # (a) 数字键 2 → 第 2 章
        page.evaluate("window.dispatchEvent(new KeyboardEvent('keydown',{key:'2'}))")
        page.wait_for_timeout(1300)
        top = page.evaluate("document.getElementById('deck').scrollTop")
        if nav['nCh'] >= 2 and abs(top - nav['tops'][1]) > 60:
            problems.append('数字键 2 未跳到第 2 章：scrollTop=%d 期望≈%d' % (top, nav['tops'][1]))

        # (b) nav-link 点击跳转（点击第一个目录链接）
        page.evaluate("window.dispatchEvent(new KeyboardEvent('keydown',{key:'0'}))")
        page.wait_for_timeout(1100)
        href = page.evaluate("document.querySelector('a.nav-link').getAttribute('href')")
        page.evaluate("document.querySelector('a.nav-link').click()")
        page.wait_for_timeout(1300)
        top = page.evaluate("document.getElementById('deck').scrollTop")
        tgt = page.evaluate(
            "(() => { const t = document.getElementById('%s');"
            " const s = t && t.closest('.slide-slot'); return s ? s.offsetTop : -1; })()"
            % href.lstrip('#'))
        if tgt < 0 or abs(top - tgt) > 60:
            problems.append('nav-link 点击未跳转：scrollTop=%d 目标=%d' % (top, tgt))

        # (c) End → 末页（scrollTop 会被夹到 scrollHeight - clientHeight，末页 slot
        # 比视口矮时到不了 offsetTop——与最大滚动位置比较）
        page.evaluate("window.dispatchEvent(new KeyboardEvent('keydown',{key:'End'}))")
        page.wait_for_timeout(1300)
        last = page.evaluate("""() => { const d = document.getElementById('deck');
          const s = [...document.querySelectorAll('.slide-slot')];
          return { top: d.scrollTop,
                   expect: Math.min(s[s.length-1].offsetTop, d.scrollHeight - d.clientHeight) }; }""")
        if abs(last['top'] - last['expect']) > 60:
            problems.append('End 未到末页：%d vs %d' % (last['top'], last['expect']))

        # (e) data-rotate：滚到含 data-rotate 的页 → .active 出现；freeze → 清空
        rot_top = page.evaluate("""() => { const r = document.querySelector('[data-rotate]');
          if (!r) return -1;
          return r.closest('.slide-slot').offsetTop; }""")
        if rot_top < 0:
            problems.append('未找到 data-rotate 容器')
        else:
            page.evaluate("document.getElementById('deck').scrollTo({top:%d,behavior:'auto'})" % rot_top)
            page.wait_for_timeout(3200)
            n_active = page.evaluate("document.querySelectorAll('[data-rotate-item].active').length")
            if n_active != 1:
                problems.append('data-rotate 轮转后 active 数=%d（期望 1）' % n_active)
            page.evaluate("window.__pptxMotion.freeze()")
            n_active = page.evaluate("document.querySelectorAll('[data-rotate-item].active').length")
            if n_active != 0:
                problems.append('freeze 后 active 残留 %d 个' % n_active)

        # mend-bar：入视口页存在 mend-bar 且终态 accent（冻结后静态终态）
        mb = page.evaluate("""() => { const b = document.querySelector('[data-anim="mend-bar"]');
          if (!b) return null;
          return { from: b.style.getPropertyValue('--from'), val: b.style.getPropertyValue('--val') }; }""")
        if not mb or not mb['from'] or not mb['val']:
            problems.append('mend-bar 缺失或 --from/--val 不全：%r' % mb)
        page.close()

        # —— 编辑器路径：nav-link 拦截 + 保存净化 ——
        ctx2, page2 = fresh_page(browser)
        try:
            page2.goto(BASE + '/harness.html')
            wait_editor_ready(page2)
            load_deck(page2, src, deck + '/index.html')
            df = deck_frame(page2)
            df.evaluate("document.getElementById('deck').scrollTo({top:0,behavior:'auto'})")
            page2.wait_for_timeout(300)
            # (d) 编辑态点击 nav-link：不跳转
            df.evaluate("document.querySelector('a.nav-link').click()")
            page2.wait_for_timeout(600)
            top = df.evaluate("document.getElementById('deck').scrollTop")
            if top > 60:
                problems.append('编辑态 nav-link 点击未拦截：scrollTop=%d' % top)
            # (f) 保存产物
            html = save_and_capture(page2)
            for keep in ['data-chapter=', 'nav-link', '--from:']:
                if keep not in html:
                    problems.append('保存产物丢失 %s' % keep)
            import re as _re
            for m in _re.finditer(r'data-rotate-item[^>]*class="([^"]*)"', html):
                if 'active' in m.group(1).split():
                    problems.append('保存产物残留 .active：%s' % m.group(1))
                    break
            page2.close()
        finally:
            ctx2.close()
        report('T22-nav-v7', '章节跳转与 v7 动效（skeleton v7）', not problems,
               '；'.join(problems) if problems else
               '数字键/nav-link/End 三通道跳转全过；编辑态拦截生效；rotate 轮转+freeze 清空；mend-bar 参数与净化口径正确')
    finally:
        ctx.close()


# ---------- 测试 32：生图入口三态与嵌入协议补全（imagegen v2 P2 G5 / editor v3.7） ----------

def test_imagegen_entries(browser):
    """(a) 嵌入态：顶栏「整页重绘」「自动补图」可见、bridge bar 不显示；点击发
    pptx-html:bake-intent {slideIds} 与 pptx-html:illustrate-intent {slots}；
    （注：v3.9.9 起生图入口只保留页头这一对，桥栏那一对已删除——断言不再读 `btnBridgeBake`）
    (b) 入站 pptx-html:assets-changed {files}：命中 img src 加 ?v= 热刷新且不置脏；
    (c) 独立（裸静态）态：按钮可见，点击走复制指令文本路径（stub copyText 取证，
    不依赖系统剪贴板）。"""
    deck = 'culture-kraft'
    point_assets(deck)
    src = read_deck(deck)
    problems = []
    ctx, page = fresh_page(browser)
    try:
        page.goto(BASE + '/harness.html')
        wait_editor_ready(page)
        load_deck(page, src, deck + '/index.html', '%s/decks/%s/' % (BASE, deck))
        ef = editor_frame(page)
        vis = ef.evaluate("""() => ({
          bake: !document.getElementById('btnBake').hidden,
          ill: !document.getElementById('btnIllustrate').hidden,
          bridgeBar: document.getElementById('bridgeBar').classList.contains('show'),
          slide: triPages[curSlideIdx].slideId })""")
        if not (vis['bake'] and vis['ill']):
            problems.append('嵌入态顶栏生图按钮不可见：%r' % vis)
        if vis['bridgeBar']:
            problems.append('嵌入态 bridge bar 不应显示')
        n0 = page.evaluate('window.__inbox.length')
        ef.evaluate("document.getElementById('btnIllustrate').click()")
        page.wait_for_function('(n) => window.__inbox.length > n', arg=n0, timeout=5000)
        ill = page.evaluate("window.__inbox.filter(m => m && m.type === 'pptx-html:illustrate-intent')")
        if not ill or ill[-1].get('slots') != ['village-fields-4x3']:
            problems.append('illustrate-intent 消息异常：%r' % ill)
        ef.evaluate("document.getElementById('btnBake').click()")
        page.wait_for_function(
            "() => window.__inbox.some(m => m && m.type === 'pptx-html:bake-intent')", timeout=5000)
        bake = page.evaluate("window.__inbox.filter(m => m && m.type === 'pptx-html:bake-intent')")
        if bake[-1].get('slideIds') != [vis['slide']]:
            problems.append('bake-intent 消息异常：%r（期望当前页 %s）' % (bake, vis['slide']))
        # (b) 入站 assets-changed：热刷新命中资产，不置脏
        before = deck_frame(page).evaluate(
            "document.querySelector('[data-image-slot=\"village-fields-4x3\"]').getAttribute('src')")
        page.evaluate("""document.getElementById('ed').contentWindow.postMessage(
          {type:'pptx-html:assets-changed', files:['assets/village-fields.svg']}, '*')""")
        page.wait_for_function("""() => { const w = document.getElementById('ed').contentWindow;
          const img = w.frame.contentDocument.querySelector('[data-image-slot="village-fields-4x3"]');
          return img.getAttribute('src').indexOf('?v=') > 0; }""", timeout=5000)
        after = deck_frame(page).evaluate(
            "document.querySelector('[data-image-slot=\"village-fields-4x3\"]').getAttribute('src')")
        dirty = ef.evaluate('window.state.dirty')
        if before != 'assets/village-fields.svg' or not after.startswith('assets/village-fields.svg?v='):
            problems.append('assets-changed 热刷新异常：%r -> %r' % (before, after))
        if dirty is not False:
            problems.append('assets-changed 不应置脏：%r' % dirty)
    finally:
        ctx.close()
    # (c) 独立（裸静态）态：按钮可见 + 复制指令文本路径
    ctx, page = fresh_page(browser)
    try:
        page.goto(BASE + '/editor.html')
        page.wait_for_function('() => window.state && window.state.embedded === false')
        page.evaluate('(h) => window.openHtml(h, "culture-kraft/index.html", null)', src)
        page.wait_for_function(
            '() => window.state.loaded && window.registry.length > 0 && '
            'window.frame.contentDocument.querySelectorAll(".slide").length > 0')
        page.evaluate("""() => { window.__copied = null;
          window.copyText = async t => { window.__copied = t; return true; }; }""")
        vis2 = page.evaluate("""() => ({
          bake: !document.getElementById('btnBake').hidden,
          ill: !document.getElementById('btnIllustrate').hidden })""")
        if not (vis2['bake'] and vis2['ill']):
            problems.append('独立态生图按钮不可见：%r' % vis2)
        page.evaluate("document.getElementById('btnIllustrate').click()")
        page.wait_for_function('() => window.__copied !== null', timeout=5000)
        copied1 = page.evaluate('window.__copied')
        page.evaluate("window.__copied = null; document.getElementById('btnBake').click()")
        page.wait_for_function('() => window.__copied !== null', timeout=5000)
        copied2 = page.evaluate('window.__copied')
        if '补上配图' not in (copied1 or ''):
            problems.append('独立态自动补图未复制指令文本：%r' % copied1)
        if '整页重画' not in (copied2 or ''):
            problems.append('独立态整页重绘未复制指令文本：%r' % copied2)
    finally:
        ctx.close()
    report('T32-imagegen-entries', '生图入口三态与嵌入协议补全（G5）', not problems,
           '；'.join(problems) if problems else
           '嵌入态按钮可见且 bridge bar 隐藏；点击发 bake-intent{slideIds}/illustrate-intent{slots}；'
           'assets-changed 热刷新 ?v= 且不置脏；独立态按钮可见并复制指令文本')

# ---------- 测试 33：--imagegen 本地插画通道（imagegen v2 P2 G6；打桩 provider，零费用） ----------

def test_local_imagegen():
    """x_local_imagegen_check.py 作为子进程纳入回归（沿用 T23–T31 约定）：
    intent 落库 → 本地 worker 执行（adapter 打桩生图 → 槽位 state 推进 generated
    → 四闸 + harmony 告警口径）→ 发布；无 placeholder 空转成功；未启用 403；
    CLI 缺 provider 配置 exit 2；config.json 供给路径。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/x_local_imagegen_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T33-local-imagegen', '--imagegen 本地插画通道（G6，打桩）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))


# ---------- 测试 36：MCP Apps 轨 A（宿主模拟器 + View 第四态） ----------

def test_mcp_apps_check():
    """aa_mcp_apps_check.py 作为子进程纳入回归（沿用 T23–T35 约定）：
    build_view_html 产出自包含 View（≤2MB、含门面）→ 宿主模拟器（sandbox 两臂）驱动
    真 editor.html + 真 daemon：ui/initialize 握手、attach→status→read_deck、deck 可读、
    save_deck（CAS + 目标文件落盘 + 无 data: URI 泄漏）、服务端草稿、便条、两阶段拆卸；
    另一臂复刻"只有 allow-scripts"的宿主沙箱，断言**如实降级**（可见不可编辑），
    不把"渲染成功"写成"编辑可用"。"""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests/harness/aa_mcp_apps_check.py')],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    report('T36-mcp-apps', 'MCP Apps 轨 A（View 第四态 + 宿主模拟器）', r.returncode == 0,
           '子进程退出码 %d：%s%s' % (r.returncode, tail,
                                      ('\n' + r.stdout + r.stderr) if r.returncode else ''))


# ---------- 测试 34：主题验收 deck（theme-proving，8 多色主题 × 8 页型 = 64 页） ----------

def _hue_families(path, min_px=150):
    """色相族计数（纯 PIL）：缩到 480×270 后逐像素统计。
    有色像素 = max(r,g,b)−min(r,g,b) ≥ 46（饱和度 ≳0.18，排除纸面/墨色/灰阶）
    且 max ≥ 60（排除深墨）；色相 30° 一区分 12 族；一族 ≥150 缩图像素
    （≈全幅 2,400px²，约一页 0.12%）计为"存在"。返回存在的族索引列表。"""
    im = Image.open(path).convert('RGB').resize((480, 270))
    px = im.load()
    bins = [0] * 12
    for yy in range(270):
        for xx in range(480):
            r, g, b = px[xx, yy]
            mx, mn = max(r, g, b), min(r, g, b)
            d = mx - mn
            if d < 46 or mx < 60:
                continue
            if mx == r:
                h = (60.0 * ((g - b) / d)) % 360
            elif mx == g:
                h = 60.0 * ((b - r) / d) + 120
            else:
                h = 60.0 * ((r - g) / d) + 240
            bins[int(h // 30) % 12] += 1
    return [i for i, c in enumerate(bins) if c >= min_px]

def test_theme_proving(browser):
    """theme-proving/index.html（skeleton v7.6，64 页 = 8 多色主题 e1/e4/e6/g1/g2/g3/g4/g5
    × 8 页型 cover/toc/low/high/ig1/ig2/chart1/chart2；多色主题/升级主题入库验收 deck）：
    (a) 结构断言：按 data-slide-id 前缀分主题组，每组恰好 8 页且 data-ptype 覆盖
        {cover,toc,low,high,ig1,ig2,chart1,chart2}；每组非 chart 的 [data-ig] 根 ≥2
        且结构族不同；chart 根 ≥2 且类型不同；
    (b) 逐页溢出/重叠测量（T18 同口径）：data-editable 矩形落画布 ±2px、
        两两不交 >16px²（排除祖先包含）；
    (c) 多色实证（像素级）：e1-cover（套印色面双版 multiply）/ e4-cover（三原色基本形）/
        e6-ig1（palette 四色徽章）/ g2-cover（两色荧光高亮带）截图走色相族计数；
        g5-cover（三色旬刊：胭脂与酒红同色相靠明度分家）改走 ΔRGB≤45 token 近邻计数，
        三色各 ≥150 缩图像素。截图落 tests/harness/results/T34-*.png。
    测量在 1920×1080 视口 + reduced-motion 下进行（动效零位移，布局即终态）。"""
    deck = 'theme-proving'
    problems = []
    ctx = browser.new_context(viewport={'width': 1920, 'height': 1080},
                              reduced_motion='reduce')
    page = ctx.new_page()
    page.on('pageerror', lambda e: print('[pageerror]', e))
    try:
        page.goto('%s/decks/%s/index.html' % (BASE, deck))
        page.wait_for_timeout(800)
        # content-visibility:auto 下远屏页不排版——先强制全部排版本再测量（仅测量页，不保存）
        page.evaluate("""() => document.querySelectorAll('.slide-slot')
          .forEach(s => s.style.contentVisibility = 'visible')""")
        page.wait_for_timeout(400)

        # (a) 结构断言：主题分组 / 页型覆盖 / data-ig 族与图表类型
        structure = page.evaluate("""() => Array.from(document.querySelectorAll('.slide')).map(s => ({
          id: s.dataset.slideId, ptype: s.dataset.ptype || '',
          igs: Array.from(s.querySelectorAll('[data-ig]')).map(r => r.getAttribute('data-ig')) }))""")
        WANT_PTYPES = {'cover', 'toc', 'low', 'high', 'ig1', 'ig2', 'chart1', 'chart2'}
        groups = {}
        for s in structure:
            theme = s['id'].split('-')[0]
            groups.setdefault(theme, []).append(s)
        if set(groups) != {'e1', 'e4', 'e6', 'g1', 'g2', 'g3', 'g4', 'g5'}:
            problems.append('主题分组异常：%r' % sorted(groups))
        for theme, pages in sorted(groups.items()):
            if len(pages) != 8:
                problems.append('%s 页数=%d，期望 8' % (theme, len(pages)))
            ptypes = set(p['ptype'] for p in pages)
            if ptypes != WANT_PTYPES:
                problems.append('%s 页型覆盖异常：缺 %r / 多 %r' % (theme, WANT_PTYPES - ptypes, ptypes - WANT_PTYPES))
            ig_struct, ig_chart = [], []
            for p in pages:
                for ig in p['igs']:
                    (ig_chart if ig.startswith('chart-') else ig_struct).append(ig)
            struct_fams = set(i.split('-')[0] for i in ig_struct)
            if len(ig_struct) < 2 or len(struct_fams) < 2:
                problems.append('%s 非图表信息图根不足或同族：%r' % (theme, ig_struct))
            if len(ig_chart) < 2 or len(set(ig_chart)) < 2:
                problems.append('%s 图表根不足或同类型：%r' % (theme, ig_chart))

        # (b) 逐页溢出 / 重叠（T18 同口径）
        geo = page.evaluate("""() => {
          const out = [];
          document.querySelectorAll('.slide').forEach(slide => {
            const sr = slide.getBoundingClientRect();
            const els = Array.from(slide.querySelectorAll('[data-editable]'));
            const rs = els.map(el => ({ el, r: el.getBoundingClientRect() }));
            rs.forEach(({el, r}) => {
              if (r.left < sr.left - 2 || r.top < sr.top - 2 ||
                  r.right > sr.right + 2 || r.bottom > sr.bottom + 2)
                out.push(slide.dataset.slideId + ' 溢出: ' + el.tagName + ' "' +
                  (el.textContent || '').trim().slice(0, 16) + '"');
            });
            for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) {
              const a = rs[i], b = rs[j];
              if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
              const ix = Math.max(0, Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left));
              const iy = Math.max(0, Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top));
              if (ix * iy > 16)
                out.push(slide.dataset.slideId + ' 重叠: "' +
                  (a.el.textContent || '').trim().slice(0, 12) + '" × "' +
                  (b.el.textContent || '').trim().slice(0, 12) + '"');
            }
          });
          return out;
        }""")
        problems += geo

        # (c) 多色实证：四页截图 + 色相族计数；g5-cover 三色近邻计数
        hue_pages = [('e1-cover', '粉满版×蓝错位层'), ('e4-cover', '三原色基本形'),
                     ('e6-ig1', 'palette 四色徽章'), ('g2-cover', '两色荧光高亮带')]
        hue_evidence = []
        for sid, what in hue_pages:
            path = os.path.join(RESULTS, 'T34-%s.png' % sid)
            loc = page.locator('[data-slide-id="%s"]' % sid)
            loc.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            loc.screenshot(path=path)
            fams = _hue_families(path)
            hue_evidence.append('%s=%d族%r' % (sid, len(fams), fams))
            if len(fams) < 2:
                problems.append('%s（%s）色相族=%d <2：%r' % (sid, what, len(fams), fams))
        # g5-cover（三色旬刊）：胭脂与酒红同色相（≈345°）靠明度分家，色相族法会漏判——
        # 改用 ΔRGB≤45 的 token 近邻计数（480×270 缩图，每色 ≥150 缩图像素 ≈ 全幅 2,400px²）
        g5_path = os.path.join(RESULTS, 'T34-g5-cover.png')
        loc = page.locator('[data-slide-id="g5-cover"]')
        loc.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        loc.screenshot(path=g5_path)
        g5im = Image.open(g5_path).convert('RGB').resize((480, 270))
        g5px = g5im.load()
        g5cnt = dict.fromkeys(['胭脂', '黄油', '酒红'], 0)
        for yy in range(270):
            for xx in range(480):
                r, g, b = g5px[xx, yy]
                for name, (tr, tg, tb) in [('胭脂', (242, 182, 198)), ('黄油', (242, 216, 106)), ('酒红', (122, 31, 53))]:
                    if (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2 <= 45 * 45:
                        g5cnt[name] += 1
                        break
        hue_evidence.append('g5-cover=%r' % g5cnt)
        for name, cnt in g5cnt.items():
            if cnt < 150:
                problems.append('g5-cover 缺%s色域：近邻像素 %d <150' % (name, cnt))

        report('T34-theme-proving', '主题验收 deck（8 主题 × 8 页型）', not problems,
               '；'.join(problems) if problems else
               '64 页结构/溢出/重叠全过；8 组页型与信息图族/图表类型覆盖齐；多色实证：' + '，'.join(hue_evidence))
    finally:
        ctx.close()


def main():
    setup_serve()
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                            '--bind', '127.0.0.1', '-d', SERVE],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                import urllib.request
                urllib.request.urlopen(BASE + '/harness.html', timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            print('Chromium', browser.version)
            ctx0, page = fresh_page(browser)
            page.goto(BASE + '/harness.html')
            wait_editor_ready(page)
            env = editor_frame(page).evaluate(
                '({fsaa: window.state.fsaa, embedded: window.state.embedded})')
            print('editor 环境探测: fsaa=%s embedded=%s' % (env['fsaa'], env['embedded']))
            ctx0.close()

            for deck in DECKS:
                test_roundtrip(browser, deck)
            test_edit_tech_ikb(browser)
            test_edit_culture_kraft(browser)
            test_esc_cancel(browser)
            for deck in ['tech-ikb', 'culture-kraft']:
                test_render(browser, deck)
            test_assets_base(browser)
            test_standalone(browser)
            test_annotation_e2e(browser)
            test_annotation_edges(browser)
            test_panel_export(browser)
            test_style_editing(browser)
            test_toc_nav(browser)
            test_git_versions(browser)
            test_motion_v3(browser)
            test_edit_chars_v3(browser)
            test_motion_v5(browser)
            test_edit_motion_v5(browser)
            test_fx_v51(browser)
            test_nav_v7(browser)
            test_infographic_v2(browser)
            test_gallery_f2(browser)
            test_check_images()
            test_image_upload_state(browser)
            test_hash_check()
            test_bake_check()
            test_export_pptx()
            test_tri_view_check()
            test_editable_check()
            test_capacity_check()
            test_bridge_check()
            test_harmony_check()
            test_brief_check()
            test_dynamic_brief_check()
            test_imagegen_entries(browser)
            test_local_imagegen()
            test_mcp_apps_check()
            test_theme_proving(browser)

            browser.close()
    finally:
        srv.terminate()

    with open(os.path.join(RESULTS, 'report.json'), 'w', encoding='utf-8') as f:
        json.dump(RESULTS_LIST, f, ensure_ascii=False, indent=2)
    nfail = sum(1 for r in RESULTS_LIST if not r['ok'])
    print('\n==== 汇总：%d 项，%d PASS，%d FAIL ====' % (len(RESULTS_LIST), len(RESULTS_LIST) - nfail, nfail))
    sys.exit(1 if nfail else 0)

if __name__ == '__main__':
    main()
