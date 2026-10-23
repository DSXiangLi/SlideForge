#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三形态 M4 验收：编辑器 v3 三态工作台与翻转对比（docs/design/editor-tri-view.md §7）。

用法：python3 tests/harness/o_tri_view_check.py

fixture：tests/decks/bake-mix/ 的临时副本（4 页混合 deck——封面目录 + 两页
普通 HTML 章节页 + 一页整页烙入页 ch-baked）+ 现场跑 export-pptx.py 产出
export/（脚本全程只动临时副本，fixture 只读）。

通道说明：规格 §6「无伴随服务照常读相对路径」以 http.server 场景为实际含义；
file:// 下 fetch 被浏览器拦截，编辑器按诚实降级（引导态）处理——本脚本用
http.server 驱动 HTTP 服务态与嵌入态两条通道。

检查项（全部硬断言）：
  ① HTTP 通道：?deck= 载入（v3.0 起不再依赖伴随服务）→ 自动 fetch
     export/manifest.json，页级派生态 4 页齐备、载体映射正确
     （3 svg + 1 baked 直通）；
  ② 对比默认落定：进入对比模式即并排双窗格；无产物页（删掉 page-02.svg
     构造）右窗格黑面空态（含状态文案、无 loading 伪装）；
  ③ 背面三态：就绪（F 翻面 → img 指向 export/page-01.svg）/ 黑面（同②
     的缺产物页，编辑态翻面同组件）/ 过期见④；
  ④ stale 闭环（嵌入态）：改封面一字保存 → 背面「已过期」水印 + 导出面板
     stale 行（与水印同源）→ 写回保存产物并重跑导出（子进程）→ 刷新后
     水印消失、全页 fresh；
  ⑤ 烙入页：注册表无 .baked-source 内元素（v2.7 断言复用）；「源层编辑」
     入口可打开（覆盖层展开）、改源层一字保存 → 烙入图 stale；
  ⑥ 导出面板：页清单四页齐备、载体/保真分渲染（色阶绿）、stale 标注与
     水印同源；嵌入态「重新翻转」发 pptx-html:export-intent（格式校验）；
  ⑦ 降级：删 export/ → 对比/导出页引导态不报错；嵌入态给了 manifest 没给
     exportBaseUrl → 产物页黑面空态（诚实，不伪装）；
  ⑧ 翻面：角标与 F 键触发、front/back 类状态正确；reduced-motion
     （page.emulate_media）下即时切换、无动画态残留。
退出码：全过 0，任一失败 1。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORTER = os.path.join(ROOT, 'skills/html-pptx/scripts/export-pptx.py')
FIXTURE = os.path.join(ROOT, 'tests/decks/bake-mix')
BAKED_ID = 'ch-baked'
PORT = 8934
BASE = 'http://127.0.0.1:%d' % PORT

FAILURES = []


def check(label, cond, detail=''):
    print('%s  %s%s' % ('PASS' if cond else 'FAIL', label,
                        (' - ' + detail) if (detail and not cond) else ''))
    if not cond:
        FAILURES.append(label)


def run_export(deck_html, *extra):
    return subprocess.run([sys.executable, EXPORTER, deck_html, *extra],
                          capture_output=True, text=True)


def ed_eval(page, expr):
    """在嵌入态 harness 的编辑器 iframe 里求值。"""
    return page.evaluate('(expr) => { const w = document.getElementById("ed").contentWindow;'
                         ' return (new Function("w", "return (" + expr + ")"))(w); }', expr)


def wait_tri_ready(page, embedded):
    """等编辑器装载 + export manifest 就绪（triStatus ready）。"""
    if embedded:
        page.wait_for_function("""() => {
          const w = document.getElementById('ed').contentWindow;
          return w && w.state && w.state.loaded === true && w.triStatus === 'ready'
                 && w.triPages && w.triPages.length === 4;
        }""", timeout=15000)
    else:
        page.wait_for_function("""() => {
          return window.state && window.state.loaded === true && window.triStatus === 'ready'
                 && window.triPages && window.triPages.length === 4;
        }""", timeout=15000)


def scroll_deck_to(page, sid, embedded):
    """把 deck 滚动到指定页并等当前页落定。

    视图从 display:none 恢复时 offsetTop 会塌缩/重建，偶发 scroll 事件丢失
    （rAF 时序）；等不到就补发一次合成 scroll 再 wait，最多两轮。"""
    if embedded:
        def drive():
            page.evaluate("""(sid) => {
              const w = document.getElementById('ed').contentWindow;
              const d = w.frame.contentDocument;
              const slide = d.querySelector('section.slide[data-slide-id="' + sid + '"]');
              const slot = slide.closest('.slide-slot') || slide;
              d.querySelector('.deck').scrollTo({ top: slot.offsetTop, behavior: 'auto' });
              d.querySelector('.deck').dispatchEvent(new d.defaultView.Event('scroll'));
            }""", sid)
        cond = """(sid) => {
          const w = document.getElementById('ed').contentWindow;
          return w.triPages[w.curSlideIdx] && w.triPages[w.curSlideIdx].slideId === sid;
        }"""
    else:
        def drive():
            page.evaluate("""(sid) => {
              const d = window.frame.contentDocument;
              const slide = d.querySelector('section.slide[data-slide-id="' + sid + '"]');
              const slot = slide.closest('.slide-slot') || slide;
              d.querySelector('.deck').scrollTo({ top: slot.offsetTop, behavior: 'auto' });
              d.querySelector('.deck').dispatchEvent(new d.defaultView.Event('scroll'));
            }""", sid)
        cond = """(sid) => {
          return window.triPages[window.curSlideIdx]
                 && window.triPages[window.curSlideIdx].slideId === sid;
        }"""
    for _ in range(2):
        drive()
        try:
            page.wait_for_function(cond, arg=sid, timeout=8000)
            return
        except Exception:
            pass
    # 最后一轮不吞异常，保留原始失败语义
    drive()
    page.wait_for_function(cond, arg=sid, timeout=8000)


def main():
    tmp = tempfile.mkdtemp(prefix='pptx-tri-view-')
    serve = os.path.join(tmp, 'serve')
    os.makedirs(serve)
    deck_dir = os.path.join(serve, 'deck')
    # 派生产物不随 fixture 拷贝（export/ 由本测试现跑现验；prompts/ 是烙入工作区），
    # 否则 fixture 目录里残留的 export/deck.pptx 会让预备导出被"重导需 --force"拒绝。
    shutil.copytree(FIXTURE, deck_dir, ignore=shutil.ignore_patterns('export', 'prompts'))
    deck_html = os.path.join(deck_dir, 'index.html')
    os.symlink(os.path.join(ROOT, 'editor.html'), os.path.join(serve, 'editor.html'))
    shutil.copy(os.path.join(ROOT, 'tests/harness/harness.html'),
                os.path.join(serve, 'harness.html'))

    # ---------- 预备：跑导出管线产出 export/；删 page-02.svg 构造无产物页 ----------
    r = run_export(deck_html)
    check('0a 预备：export-pptx.py 跑通（出口 0）', r.returncode == 0,
          (r.stdout + r.stderr).strip()[-300:])
    export_dir = os.path.join(deck_dir, 'export')
    mf_path = os.path.join(export_dir, 'manifest.json')
    if r.returncode != 0:
        print('RESULT: 预备导出失败，后续无法进行')
        return 1
    with open(mf_path, encoding='utf-8') as f:
        mf0 = json.load(f)
    os.remove(os.path.join(export_dir, 'page-02.svg'))   # ch-now 无产物 → 黑面
    # v3.1 原生预览：svg 与 native 页图同为该页产物，模拟"缺失"须一并删除
    _nat2 = os.path.join(export_dir, 'native', 'page-02.png')
    if os.path.isfile(_nat2):
        os.remove(_nat2)

    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                            '--bind', '127.0.0.1', '-d', serve],
                           stdout=open(os.path.join(tmp, 'srv.log'), 'w'),
                           stderr=subprocess.STDOUT)
    try:
        up = False
        for _ in range(50):
            if srv.poll() is not None:
                raise RuntimeError('静态服务启动失败（端口 %d）' % PORT)
            try:
                urllib.request.urlopen(BASE + '/editor.html', timeout=1)
                up = True
                break
            except Exception:
                time.sleep(0.2)
        if not up:
            raise RuntimeError('静态服务 10s 内未就绪')

        with sync_playwright() as pw:
            browser = pw.chromium.launch()

            # ==================== 会话 A：独立 HTTP 服务态 ====================
            ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = ctx.new_page()
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto(BASE + '/editor.html?deck=deck/index.html')
            wait_tri_ready(page, embedded=False)

            # ① HTTP 通道：manifest 自动读取 + 页级派生态
            t1 = page.evaluate("""() => ({
              status: window.triStatus, base: window.triBaseUrl,
              pages: window.triPages.map(p => ({ sid: p.slideId, rm: p.renderMode,
                carrier: p.carrier, stale: p.stale, fid: p.fidelity,
                artifact: p.artifact })) })""")
            check('①a HTTP 通道 manifest 就绪（triStatus=ready）', t1['status'] == 'ready',
                  repr(t1['status']))
            check('①b 产物基址从 ?deck= 推导（deck/export/）',
                  t1['base'] == 'deck/export/', repr(t1['base']))
            carriers = {p['sid']: p['carrier'] for p in t1['pages']}
            check('①c 载体映射 3 svg + 1 baked 直通',
                  carriers == {'cover': 'svg', 'ch-now': 'svg',
                               BAKED_ID: 'baked', 'ch-end': 'svg'}, repr(carriers))
            check('①d 初始全部 fresh 且导出件 URL 成形',
                  all(not p['stale'] for p in t1['pages'])
                  and t1['pages'][0]['artifact'] == 'deck/export/page-01.svg'
                  and t1['pages'][2]['artifact'] == 'deck/assets/page-%s.png' % BAKED_ID,
                  repr([(p['sid'], p['stale'], p['artifact']) for p in t1['pages']]))

            # ② 对比默认落定 = 并排双窗格；无产物页右窗格黑面
            page.click('#viewSeg button[data-view="export"]')
            page.click('#expSubSeg button[data-view="compare"]')
            page.wait_for_timeout(200)
            st2 = page.evaluate("""() => ({
              view: window.view, cmpView: window.cmpView,
              rightShown: !document.getElementById('cmpRight').hidden,
              overlayHidden: document.getElementById('cmpOverlay').hidden,
              cards: document.querySelectorAll('#cmpArtifacts .cmp-art').length })""")
            check('②a 进入对比模式即并排（cmpView=side、右窗格显示、叠层隐藏）',
                  st2['view'] == 'compare' and st2['cmpView'] == 'side'
                  and st2['rightShown'] and st2['overlayHidden'], repr(st2))
            check('②b 右窗格页卡齐备（4 页）', st2['cards'] == 4, repr(st2['cards']))
            # 缺产物页 img onerror → 黑面（异步，等待落定）
            page.wait_for_function("""() => {
              const c = document.querySelector('#cmpArtifacts .cmp-art[data-sid="ch-now"] .tri-face');
              return c && c.dataset.artState === 'black';
            }""", timeout=8000)
            black2 = page.evaluate("""() => {
              const f = document.querySelector('#cmpArtifacts .cmp-art[data-sid="ch-now"] .tri-face');
              const ok = document.querySelector('#cmpArtifacts .cmp-art[data-sid="cover"] .tri-face');
              return { black: f.dataset.artState, text: f.textContent,
                       ready: ok.dataset.artState,
                       img: ok.querySelector('img') ? ok.querySelector('img').src : null };
            }""")
            check('②c 无产物页右窗格黑面（产物缺失文案、无 loading 伪装）',
                  black2['black'] == 'black' and '缺失' in black2['text']
                  and '翻转' in black2['text']
                  and '加载中' not in black2['text'] and 'loading' not in black2['text'].lower(),
                  repr(black2['text']))
            check('②d 有产物页右窗格就绪（img 指向产物：native 优先 / SVG 回落）',
                  black2['ready'] == 'ready' and black2['img']
                  and ('export/native/page-01.png' in black2['img']
                       or 'export/page-01.svg' in black2['img']), repr(black2['img']))

            # 页清单徽标三分量 + 保真分排序（红→绿）
            rows2 = page.evaluate("""() => Array.from(
              document.querySelectorAll('#cmpRows .cmp-row')).map(r => ({
                sid: r.dataset.sid,
                badges: Array.from(r.querySelectorAll('.badge')).map(b => b.textContent) }))""")
            ok_badges = all(len(r['badges']) == 3 for r in rows2) and \
                any('烙入' in r['badges'] for r in rows2) and \
                all(('fresh' in r['badges']) for r in rows2)
            check('②e 页清单徽标三分量（形态/状态/保真分）齐备', ok_badges, repr(rows2))

            # ③a 翻面：就绪态（角标与 F 键两通道）
            page.click('#viewSeg button[data-view="edit"]')
            page.wait_for_timeout(150)
            scroll_deck_to(page, 'cover', embedded=False)
            page.click('#flipBadge')   # 角标触发
            page.wait_for_selector('#flipInner.flipped', timeout=3000)
            back3 = page.evaluate("""() => {
              const f = document.querySelector('#flipBack .tri-face');
              return { state: f && f.dataset.artState,
                       img: f && f.querySelector('img') ? f.querySelector('img').src : null,
                       pe: document.getElementById('deckFrame').style.pointerEvents };
            }""")
            check('③a 翻面就绪：背面 img 渲染产物（native 优先 / SVG 回落；角标触发，iframe 指针禁用）',
                  back3['state'] == 'ready' and back3['img']
                  and ('export/native/page-01.png' in back3['img']
                       or 'export/page-01.svg' in back3['img']) and back3['pe'] == 'none',
                  repr(back3))
            page.click('#flipBadge')   # 翻回
            page.wait_for_function("""() =>
              !document.getElementById('flipInner').classList.contains('flipped')""",
              timeout=3000)
            page.wait_for_timeout(900)   # 动画结束（兜底 800ms）恢复指针事件
            pe3 = page.evaluate("document.getElementById('deckFrame').style.pointerEvents")
            check('③b 翻回正面后 iframe 指针事件恢复', pe3 == '', repr(pe3))
            # F 键触发
            page.keyboard.press('f')
            page.wait_for_selector('#flipInner.flipped', timeout=3000)
            page.keyboard.press('f')
            page.wait_for_function("""() =>
              !document.getElementById('flipInner').classList.contains('flipped')""",
              timeout=3000)
            check('③c F 键翻面/翻回正常', True)

            # ③d 编辑态黑面（缺产物页 ch-now 翻面）
            scroll_deck_to(page, 'ch-now', embedded=False)
            page.keyboard.press('f')
            page.wait_for_function("""() => {
              const f = document.querySelector('#flipBack .tri-face');
              return f && f.dataset.artState === 'black';
            }""", timeout=8000)
            blk3 = page.evaluate("document.querySelector('#flipBack .tri-face').textContent")
            check('③d 编辑态黑面：页码 + 状态一行小字、无假进度条',
                  'ch-now' in blk3 and '翻转' in blk3
                  and '加载中' not in blk3 and '%' not in blk3, repr(blk3))
            page.keyboard.press('f')
            page.wait_for_function("""() =>
              !document.getElementById('flipInner').classList.contains('flipped')""",
              timeout=3000)

            # ⑧ reduced-motion：即时切换、无动画态残留
            page.emulate_media(reduced_motion='reduce')
            dur8 = page.evaluate(
                "getComputedStyle(document.getElementById('flipInner')).transitionDuration")
            page.keyboard.press('f')
            page.wait_for_timeout(100)
            rm8 = page.evaluate("""() => ({
              flipped: document.getElementById('flipInner').classList.contains('flipped'),
              backVisible: !!document.querySelector('#flipBack .tri-face') })""")
            page.keyboard.press('f')
            page.wait_for_timeout(100)
            rm8b = page.evaluate(
                "document.getElementById('flipInner').classList.contains('flipped')")
            check('⑧ reduced-motion 即时切换（transition=0s，无动画态残留）',
                  dur8 == '0s' and rm8['flipped'] and rm8['backVisible'] and not rm8b,
                  repr({'dur': dur8, 'rm': rm8, 'back': rm8b}))
            page.emulate_media(reduced_motion='no-preference')

            # ⑥a 导出面板（独立 HTTP 态）
            page.click('#viewSeg button[data-view="export"]')
            page.wait_for_selector('#exportView:not([hidden])', timeout=3000)
            exp6 = page.evaluate("""() => ({
              rows: Array.from(document.querySelectorAll('#expRows .exp-row')).map(r => ({
                sid: r.dataset.sid, stale: r.classList.contains('stale'),
                carrier: r.children[3].textContent,
                fid: r.children[4].textContent.trim(),
                fidGreen: !!r.children[4].querySelector('.f-green') })),
              pptxUrl: document.getElementById('btnDlPptx').dataset.url,
              guideHidden: document.getElementById('expGuide').hidden })""")
            check('⑥a 导出面板四页齐备、载体/保真分渲染（3 绿 + 烙入直通）',
                  len(exp6['rows']) == 4
                  and [r['carrier'] for r in exp6['rows']] == ['SVG', 'SVG', '烙入直通', 'SVG']
                  and sum(1 for r in exp6['rows'] if r['fidGreen']) == 3
                  and exp6['rows'][2]['fid'] == '直通',
                  repr(exp6['rows']))
            check('⑥b 初始无 stale 行；deck.pptx 直链成形；引导态隐藏',
                  all(not r['stale'] for r in exp6['rows'])
                  and exp6['pptxUrl'] == 'deck/export/deck.pptx' and exp6['guideHidden'],
                  repr({'pptx': exp6['pptxUrl'], 'guide': exp6['guideHidden']}))

            # 滑动分割 + 差异热区
            page.click('#viewSeg button[data-view="export"]')
            page.click('#expSubSeg button[data-view="compare"]')
            page.click('#cmpViewSeg button[data-cmp="swipe"]')
            page.wait_for_selector('#cmpOverlay:not([hidden])', timeout=3000)
            page.wait_for_function("""() => {
              const i = document.getElementById('cmpOlImg');
              return i && (i.src.indexOf('export/native/page-01.png') >= 0
                           || i.src.indexOf('export/page-01.svg') >= 0);
            }""", timeout=8000)
            clip0 = page.evaluate(
                "document.getElementById('cmpOlHolder').style.clipPath")
            # 拖拽分割线：把手中心向右 80px
            hb = page.evaluate("""() => {
              const r = document.getElementById('cmpHandle').getBoundingClientRect();
              return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
            }""")
            page.mouse.move(hb['x'], hb['y'])
            page.mouse.down()
            page.mouse.move(hb['x'] + 80, hb['y'], steps=4)
            page.mouse.up()
            clip1 = page.evaluate(
                "document.getElementById('cmpOlHolder').style.clipPath")
            check('⑥c 滑动分割：导出件叠加 + 拖拽分割线 clip 变化',
                  clip0.startswith('inset(') and clip1.startswith('inset(') and clip0 != clip1,
                  repr((clip0, clip1)))
            page.click('#cmpViewSeg button[data-cmp="diff"]')
            page.wait_for_function("""() => {
              const i = document.getElementById('cmpOlImg');
              return i && i.src.indexOf('export/page-01.diff.png') >= 0;
            }""", timeout=8000)
            check('⑥d 差异热区：叠加 page-01.diff.png（管线资产，编辑器只消费）', True)
            page.click('#cmpViewSeg button[data-cmp="side"]')
            ctx.close()

            # ==================== 会话 A2：降级（删 export/） ====================
            off_dir = os.path.join(deck_dir, 'export_off')
            os.rename(export_dir, off_dir)
            ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = ctx.new_page()
            a2_errors = []
            page.on('pageerror', lambda e: a2_errors.append(str(e)))
            page.goto(BASE + '/editor.html?deck=deck/index.html')
            page.wait_for_function("""() => window.state && window.state.loaded === true
                && window.triStatus !== 'idle' && window.triStatus !== 'loading'""",
                timeout=15000)
            page.click('#viewSeg button[data-view="export"]')
            page.click('#expSubSeg button[data-view="compare"]')
            page.wait_for_timeout(200)
            dg = page.evaluate("""() => ({
              status: window.triStatus,
              black: Array.from(document.querySelectorAll('#cmpArtifacts .tri-face'))
                          .map(f => f.dataset.artState),
              note: (document.querySelector('.cmp-art-note') || {}).textContent || '' })""")
            check('⑦a 删 export/ 后对比页全黑面 + 引导文案、不报错',
                  dg['status'] == 'none' and len(dg['black']) == 4
                  and all(b == 'black' for b in dg['black'])
                  and 'export-pptx.py' in dg['note'] and not a2_errors,
                  repr({'status': dg['status'], 'black': dg['black'], 'err': a2_errors}))
            page.click('#viewSeg button[data-view="export"]')
            page.wait_for_timeout(150)
            dg2 = page.evaluate("""() => ({
              guide: document.getElementById('expGuide').textContent,
              guideShown: !document.getElementById('expGuide').hidden,
              tableHidden: document.getElementById('expTable').hidden })""")
            check('⑦b 导出面板引导态（技能运行说明）、表格隐藏、不报错',
                  dg2['guideShown'] and dg2['tableHidden']
                  and 'export-pptx.py' in dg2['guide']
                  and not a2_errors, repr(dg2['guide'][:120]))
            ctx.close()
            os.rename(off_dir, export_dir)   # 还原供会话 B 使用

            # ==================== 会话 B：嵌入态（harness.html） ====================
            with open(deck_html, encoding='utf-8') as f:
                deck_src = f.read()
            ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = ctx.new_page()
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto(BASE + '/harness.html')
            page.wait_for_function("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w && w.state !== undefined && w.document.getElementById('btnSave');
            }""", timeout=8000)

            # ⑦c 给了 manifest 没给 baseUrl → 产物页黑面空态
            page.evaluate('([h, n, m]) => window.loadDeck(h, n, null, m, null)',
                          [deck_src, 'deck/index.html', mf0])
            wait_tri_ready(page, embedded=True)
            page.evaluate("""() => document.getElementById('ed').contentWindow.setFlip(true)""")
            b0 = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              const f = w.document.querySelector('#flipBack .tri-face');
              return { state: f && f.dataset.artState, text: f ? f.textContent : '',
                       hasManifest: !!w.triManifest, base: w.triBaseUrl };
            }""")
            check('⑦c 嵌入态：有 manifest 无 exportBaseUrl → 黑面空态（诚实，不伪装）',
                  b0['hasManifest'] and b0['base'] is None
                  and b0['state'] == 'black' and 'exportBaseUrl' in b0['text'],
                  repr(b0))

            # 正式嵌入装载：exportBaseUrl → manifest 经 HTTP fetch
            page.evaluate('([h, n, a, b]) => window.loadDeck(h, n, a, null, b)',
                          [deck_src, 'deck/index.html', BASE + '/deck/', BASE + '/deck/export/'])
            wait_tri_ready(page, embedded=True)
            b1 = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              return { injected: w.triInjected, pages: w.triPages.length,
                       artifact: w.triPages[0].artifact };
            }""")
            check('⑦d 嵌入态 exportBaseUrl → manifest 经 HTTP fetch 就绪、产物 URL 成形',
                  b1['injected'] is False and b1['pages'] == 4
                  and b1['artifact'] == BASE + '/deck/export/page-01.svg', repr(b1))

            # ⑤a 烙入页：注册表无源层元素（v2.7 断言复用）
            reg5 = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w.registry.filter(r => r.el.closest('.baked-source')).length;
            }""")
            check('⑤a 烙入页注册表无 .baked-source 内元素', reg5 == 0, repr(reg5))

            # ④a stale 闭环第一步：改封面一字保存 → 水印 + 导出面板 stale 行
            h1 = page.frame_locator('#ed').frame_locator('#deckFrame').locator(
                '[data-slide-id="cover"] h1[data-editable]')
            h1.click(); h1.click()
            page.keyboard.type('混合形态演示改')
            page.keyboard.press('Control+Enter')
            n0 = page.evaluate('window.saveCount()')
            page.frame_locator('#ed').locator('#btnSave').click()
            page.wait_for_function('(n) => window.saveCount() > n', arg=n0, timeout=8000)
            st4 = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              return { stale: w.triPages.map(p => ({ sid: p.slideId, stale: p.stale })),
                       liveHash: w.frame.contentDocument
                         .querySelector('[data-slide-id="cover"]')
                         .getAttribute('data-content-hash') };
            }""")
            stale_pages = [p['sid'] for p in st4['stale'] if p['stale']]
            check('④a 改字保存后恰好封面 stale（hash 已写回 live DOM，与导出记录不符）',
                  stale_pages == ['cover']
                  and st4['liveHash'] != mf0['pages'][0]['export_hash'],
                  repr(st4))
            scroll_deck_to(page, 'cover', embedded=True)
            page.evaluate("() => document.getElementById('ed').contentWindow.setFlip(true)")
            wm4 = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              const f = w.document.querySelector('#flipBack .tri-face');
              return { state: f && f.dataset.artState,
                       wm: f ? (f.querySelector('.tri-stale') || {}).textContent || '' : '' };
            }""")
            check('④b 过期态：产物照常显示 + 「已过期」水印',
                  wm4['state'] == 'stale' and '已过期' in wm4['wm'], repr(wm4))
            page.evaluate("() => document.getElementById('ed').contentWindow.setFlip(false)")

            # ⑥e 导出面板 stale 标注与水印同源 + export-intent 消息
            page.evaluate("() => document.getElementById('ed').contentWindow.setView('export')")
            row6 = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              const r = w.document.querySelector('.exp-row[data-sid="cover"]');
              return { stale: r.classList.contains('stale'),
                       badge: (r.querySelector('.b-stale') || {}).textContent || '',
                       hint: (r.querySelector('.exp-hint') || {}).textContent || '' };
            }""")
            check('⑥e 导出面板 stale 行与水印同源 + 「请让 AI 重新翻转本页」引导',
                  row6['stale'] and row6['badge'] == 'stale'
                  and '请让 AI 重新翻转本页' in row6['hint'], repr(row6))
            page.frame_locator('#ed').locator(
                '.exp-row[data-sid="cover"] .btn-reflip').click()
            page.wait_for_timeout(200)
            intents = page.evaluate('window.exportIntents()')
            check('⑥f 嵌入态「重新翻转」发 export-intent（只发消息不执行）',
                  len(intents) >= 1 and intents[-1].get('type') == 'pptx-html:export-intent'
                  and intents[-1].get('action') == 're-export'
                  and intents[-1].get('slideIds') == ['cover'], repr(intents))

            # ⑤b 源层编辑：打开覆盖层 → 改源层一字 → 保存 → 烙入图 stale
            page.evaluate("() => document.getElementById('ed').contentWindow.setView('edit')")
            scroll_deck_to(page, BAKED_ID, embedded=True)
            b5a = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              return { btnShown: !w.document.getElementById('btnSrcEdit').hidden };
            }""")
            check('⑤b 烙入页正面出现「源层编辑」入口', b5a['btnShown'], repr(b5a))
            page.frame_locator('#ed').locator('#btnSrcEdit').click()
            b5c = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              const d = w.frame.contentDocument;
              const src = d.querySelector('.baked-source');
              return { open: !!w.srcEdit, cls: src.classList.contains('ed-src-open'),
                       display: w.frame.contentWindow.getComputedStyle(src).display };
            }""")
            check('⑤c 源层编辑打开：覆盖层展开（ed-src-open，display 覆盖 hidden）',
                  b5c['open'] and b5c['cls'] and b5c['display'] != 'none', repr(b5c))
            sh1 = page.frame_locator('#ed').frame_locator('#deckFrame').locator(
                '.baked-source h1[data-editable]')
            sh1.click(); sh1.click()
            page.keyboard.type('整页烙入示例改')
            page.keyboard.press('Control+Enter')
            page.frame_locator('#ed').locator('#btnSrcEditClose').click()
            b5d = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              const d = w.frame.contentDocument;
              const src = d.querySelector('.baked-source');
              return { closed: !w.srcEdit,
                       display: w.frame.contentWindow.getComputedStyle(src).display,
                       text: src.querySelector('h1').textContent };
            }""")
            check('⑤d 退出源层：hidden 原状恢复、编辑已写回源层 DOM',
                  b5d['closed'] and b5d['display'] == 'none'
                  and b5d['text'] == '整页烙入示例改', repr(b5d))
            n1 = page.evaluate('window.saveCount()')
            page.frame_locator('#ed').locator('#btnSave').click()
            page.wait_for_function('(n) => window.saveCount() > n', arg=n1, timeout=8000)
            saved = page.evaluate('window.lastSave().html')
            b5e = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w.triPages.map(p => ({ sid: p.slideId, stale: p.stale }));
            }""")
            stale5 = sorted(p['sid'] for p in b5e if p['stale'])
            check('⑤e 源层编辑保存 → 烙入图 stale（且保存产物含新文字）',
                  stale5 == [BAKED_ID, 'cover'] and '整页烙入示例改' in saved,
                  repr(stale5))

            # ④c stale 闭环第二步：写回保存产物 → 重跑导出 → 刷新 → 水印消失
            with open(deck_html, 'w', encoding='utf-8') as f:
                f.write(saved)
            r2 = run_export(deck_html, '--force')
            check('④c 重跑导出（--force）出口 0', r2.returncode == 0,
                  (r2.stdout + r2.stderr).strip()[-300:])
            page.evaluate("() => document.getElementById('ed').contentWindow.setView('export')")
            page.frame_locator('#ed').locator('#btnExpRefresh').click()
            page.wait_for_function("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w.triManifest && w.triManifest.export
                     && w.triPages.every(p => !p.stale);
            }""", timeout=15000)
            # 隐藏态的 deck 不派发 scroll 事件（curSlideIdx 不更新），先回编辑态再滚动
            page.evaluate("() => document.getElementById('ed').contentWindow.setView('edit')")
            scroll_deck_to(page, 'cover', embedded=True)
            page.evaluate("() => document.getElementById('ed').contentWindow.setFlip(true)")
            wm4b = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              const f = w.document.querySelector('#flipBack .tri-face');
              return { state: f && f.dataset.artState,
                       wm: !!(f && f.querySelector('.tri-stale')) };
            }""")
            check('④d 闭环：重翻转 + 刷新后水印消失（就绪态）',
                  wm4b['state'] == 'ready' and not wm4b['wm'], repr(wm4b))
            # 烙入页背面 = 烙入图本身，回归就绪
            page.evaluate("() => document.getElementById('ed').contentWindow.setFlip(false)")
            scroll_deck_to(page, BAKED_ID, embedded=True)
            page.evaluate("() => document.getElementById('ed').contentWindow.setFlip(true)")
            wm4c = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              const f = w.document.querySelector('#flipBack .tri-face');
              const img = f && f.querySelector('img');
              return { state: f && f.dataset.artState, src: img ? img.src : null };
            }""")
            check('④e 烙入页背面 = 烙入图本身（assets/page-ch-baked.png），就绪',
                  wm4c['state'] == 'ready' and wm4c['src']
                  and ('assets/page-%s.png' % BAKED_ID) in wm4c['src'], repr(wm4c))
            ctx.close()
            browser.close()
    finally:
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)

    print('RESULT:', 'ALL PASS' if not FAILURES else '%d FAILURES: %s' % (len(FAILURES), FAILURES))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())
