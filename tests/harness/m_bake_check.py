#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三形态 M2 验收：页面烙入模式（docs/design/page-render-mode.md §6）。

用法：python3 tests/harness/m_bake_check.py

fixture：tests/decks/bake-mix/（skeleton v7.3，4 页混合 deck——封面目录 +
两页普通 HTML 章节页 + 一页整页烙入页 ch-baked）。

检查项（全部硬断言）：
  ① 契约 v7 三要素静态校验：data-render-mode="baked" / 页面级槽位
     page-baked-16x9 三属性 / .baked-source hidden 源层；check-images 扩展
     对合规页零错误、对缺 render-mode 的负例报错；
  ② 源层保留：extract-manifest 对烙入页提取的 texts 与源层 data-editable
     逐字一致（querySelectorAll 天然含 hidden 子树）；模拟回退（摘除 img 与
     render-mode、解 hidden）后 check-render 通过且文本提取不变；
  ③ 指令合规：compile-bake-prompts.py 编译产物七节齐全，Text 段每行是
     manifest 该页文本的精确子串，Global Style 含 manifest token 具体色值，
     重跑幂等；
  ④ 编辑器行为：harness.html 驱动 editor.html 加载混合 deck——注册表无
     .baked-source 内元素（整页 img 仍在）、保存产物源层字节保留、重载再
     保存幂等、产物每页 hash 与 extractor 重算双端一致；
  ⑤ hash 翻转：文件级改烙入页源层文字 → 该页 hash 翻转、其余页不变；
  ⑥ 混合 deck 回归：check-render / k_nav_check 通过；骨架运行时跳过
     源层（.baked-source 内无 .sp-unit、无 --i 注入），普通页动效照常；
  ⑦ 失败回退演练：placeholder 残留的页面级槽位在 --mode illustration 下
     报错；诚实回退（摘除 img/render-mode、解 hidden）后渲染与校验全过；
  ⑧ 图片入场动效（契约 v8 / imagegen v2 G4）：白名单静态校验；渲染实测
     （未入视口 opacity 0 → 入视口到终态，图片可见）；导出 freeze 同款
     序列后两图呈终态、过导出 visible() 门槛、截图非空白；仓库骨架 v7.5
     合成页实测整图时长 ≤0.8s、零延迟。
退出码：全过 0，任一失败 1。
"""
import importlib.util
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
EXTRACTOR = os.path.join(ROOT, 'skills/html-pptx/scripts/extract-manifest.py')
EXPORT_PPTX = os.path.join(ROOT, 'skills/html-pptx/scripts/export-pptx.py')
COMPILER = os.path.join(ROOT, 'skills/html-pptx/scripts/compile-bake-prompts.py')
CHECK_IMAGES = os.path.join(ROOT, 'skills/html-pptx/scripts/check-images.mjs')
J_RENDER = os.path.join(ROOT, 'skills/html-pptx/scripts/check-render.py')
K_NAV = os.path.join(ROOT, 'tests/harness/k_nav_check.py')
FIXTURE = os.path.join(ROOT, 'tests/decks/bake-mix')
BAKED_ID = 'ch-baked'
PORT = 8933
BASE = 'http://127.0.0.1:%d' % PORT
HASH_RE = re.compile(r'^[0-9a-f]{12}$')

FAILURES = []


def check(label, cond, detail=''):
    print('%s  %s%s' % ('PASS' if cond else 'FAIL', label,
                        (' — ' + detail) if (detail and not cond) else ''))
    if not cond:
        FAILURES.append(label)


def run_extractor(deck_html, out=None):
    cmd = [sys.executable, EXTRACTOR, deck_html]
    if out:
        cmd += ['--out', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('extractor 失败：%s%s' % (r.stdout, r.stderr))
    if out:
        with open(out, encoding='utf-8') as f:
            return json.load(f)
    return json.loads(r.stdout)


def hashes_of(manifest):
    return {p['slide_id']: p['content_hash'] for p in manifest['pages']}


def run_py(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True)


BOOLEAN_ATTRS = ['data-editable', 'data-editable-image', 'data-editable-skip',
                 'data-anim', 'data-ig-item', 'data-rotate', 'data-rotate-item', 'hidden']


def source_block(html):
    """提取 .baked-source 源层块（布尔属性 ="" 化规范化后比较，同 run_e2e 白名单口径）。"""
    i = html.find('<div class="baked-source"')
    if i < 0:
        return None
    j = html.index('</div>', i) + len('</div>')
    block = html[i:j]
    for a in BOOLEAN_ATTRS:
        block = block.replace(' %s=""' % a, ' ' + a)
    return block


def main():
    tmp = tempfile.mkdtemp(prefix='pptx-bake-check-')
    serve = os.path.join(tmp, 'serve')
    os.makedirs(serve)
    deck_dir = os.path.join(tmp, 'deck')
    shutil.copytree(FIXTURE, deck_dir)
    deck_html = os.path.join(deck_dir, 'index.html')
    os.symlink(os.path.join(ROOT, 'editor.html'), os.path.join(serve, 'editor.html'))
    shutil.copy(os.path.join(ROOT, 'tests/harness/harness.html'),
                os.path.join(serve, 'harness.html'))
    with open(deck_html, encoding='utf-8') as f:
        src = f.read()

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
                urllib.request.urlopen(BASE + '/harness.html', timeout=1)
                up = True
                break
            except Exception:
                time.sleep(0.2)
        if not up:
            raise RuntimeError('静态服务 10s 内未就绪')

        # ---------- ① 契约 v7 三要素静态校验 ----------
        sec_m = re.search(r'<section\b[^>]*\bdata-slide-id="%s"[^>]*>' % BAKED_ID, src)
        check('①a 烙入页 section 存在', sec_m is not None)
        sec_tag = sec_m.group(0)
        check('①b data-render-mode="baked"', 'data-render-mode="baked"' in sec_tag)
        check('①c 烙入页 data-content-hash 合法（12 位 hex）',
              bool(re.search(r'\bdata-content-hash="[0-9a-f]{12}"', sec_tag)))
        img_m = re.search(r'<img\b[^>]*\bdata-image-slot="page-baked-16x9"[^>]*>', src)
        check('①d 页面级槽位 img 存在且三属性齐备',
              img_m is not None and all(k in img_m.group(0) for k in
                  ('data-editable-image', 'data-image-intent=', 'data-image-state="generated"',
                   'src="assets/')))
        check('①e .baked-source hidden 源层存在',
              '<div class="baked-source" hidden>' in src)
        other_secs = [t for t in re.findall(r'<section\b[^>]*\bdata-slide-id="(?!%s)' % BAKED_ID + r'[^"]+"[^>]*>', src)]
        check('①f 其余页无 data-render-mode（缺省 html）', len(other_secs) == 3)
        r = subprocess.run(['node', CHECK_IMAGES, deck_html], capture_output=True, text=True)
        check('①g check-images 默认模式零错误', r.returncode == 0, r.stderr.strip()[:200])
        r = subprocess.run(['node', CHECK_IMAGES, deck_html, '--mode', 'illustration'],
                           capture_output=True, text=True)
        check('①h check-images 插画模式零错误（generated 页级槽位）', r.returncode == 0,
              r.stderr.strip()[:200])
        # 负例：摘除 render-mode → 结构校验报错
        neg_dir = os.path.join(tmp, 'neg')
        shutil.copytree(deck_dir, neg_dir)
        neg_html = os.path.join(neg_dir, 'index.html')
        with open(neg_html, 'w', encoding='utf-8') as f:
            f.write(src.replace(' data-render-mode="baked"', ''))
        r = subprocess.run(['node', CHECK_IMAGES, neg_html], capture_output=True, text=True)
        check('①i 负例：缺 render-mode 的页面级槽位报错',
              r.returncode != 0 and 'data-render-mode' in r.stderr, r.stderr.strip()[:200])

        # ---------- ② 源层保留 ----------
        m1 = run_extractor(deck_html)
        baked = next(p for p in m1['pages'] if p['slide_id'] == BAKED_ID)
        check('②a manifest 中烙入页 render_mode=baked', baked['render_mode'] == 'baked')
        src_texts = re.findall(r'data-editable[^>]*>([^<]+)<', source_block(src) or '')
        src_texts = [re.sub(r'\s+', ' ', t).strip() for t in src_texts if t.strip()]
        mf_texts = [t['content'] for t in baked['texts'] if t['content']]
        check('②b 烙入页 manifest texts 与源层逐字一致（%d 条）' % len(mf_texts),
              mf_texts == src_texts, 'manifest=%r vs 源层=%r' % (mf_texts, src_texts))
        # 模拟回退：摘除 img 与 render-mode、解 hidden → 完整回退为 HTML 页
        rev_dir = os.path.join(tmp, 'reverted')
        shutil.copytree(deck_dir, rev_dir)
        rev_html = os.path.join(rev_dir, 'index.html')
        reverted = src.replace(' data-render-mode="baked"', '')
        reverted = re.sub(r'\n\s*<img\b[^>]*\bdata-image-slot="page-baked-16x9"[^>]*>', '', reverted)
        reverted = reverted.replace('<div class="baked-source" hidden>', '<div class="baked-source">')
        with open(rev_html, 'w', encoding='utf-8') as f:
            f.write(reverted)
        r = run_py(J_RENDER, rev_html)
        check('②c 回退后 check-render 通过', r.returncode == 0,
              (r.stdout + r.stderr).strip()[-300:])
        m_rev = run_extractor(rev_html)
        rev_baked = next(p for p in m_rev['pages'] if p['slide_id'] == BAKED_ID)
        check('②d 回退页文本提取与烙入态一致',
              [t['content'] for t in rev_baked['texts']] == [t['content'] for t in baked['texts']])
        check('②e 回退页 render_mode 回落 html', rev_baked['render_mode'] == 'html')

        # ---------- ③ 指令合规 ----------
        manifest_path = os.path.join(tmp, 'manifest.json')
        run_extractor(deck_html, out=manifest_path)
        plan_path = os.path.join(tmp, 'plan.json')
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump({
                'goal': '面向技术团队的混合形态演示 deck',
                'style': '深蓝夜空科技感，发光网格线，冷峻克制',
                'pages': {BAKED_ID: {'layout': '仪式页构图：标题巨字位于上三分之一留白区'}},
            }, f, ensure_ascii=False)
        prompts_dir = os.path.join(tmp, 'prompts')
        r = run_py(COMPILER, manifest_path, '--pages', BAKED_ID,
                   '--plan', plan_path, '--anchor', 'cover.png', '--out-dir', prompts_dir)
        check('③a 编译器运行成功', r.returncode == 0, r.stderr.strip()[:200])
        prompt_file = os.path.join(prompts_dir, BAKED_ID + '.md')
        prompt_text = ''
        if os.path.isfile(prompt_file):
            with open(prompt_file, encoding='utf-8') as f:
                prompt_text = f.read()
        check('③b 指令文件存在', bool(prompt_text))
        for sec in ('## Canvas', '## Deck Goal', '## Global Style', '## Style Anchor',
                    '## Text', '## Layout', '## Constraints'):
            check('③c 七节齐全：%s' % sec, sec in prompt_text)
        text_m = re.search(r'## Text\n(.*?)## Layout', prompt_text, re.S)
        text_sec = text_m.group(1) if text_m else ''
        missing = [c for c in mf_texts if c not in text_sec]
        check('③d Text 段每行是 manifest 文本的精确子串（%d 条）' % len(mf_texts),
              not missing and bool(mf_texts), '缺失=%r' % missing)
        tokens = (m1.get('theme') or {}).get('tokens') or {}
        gs_m = re.search(r'## Global Style\n(.*?)## Style Anchor', prompt_text, re.S)
        gs_sec = gs_m.group(1) if gs_m else ''
        missing_tok = ['%s: %s' % (k, v) for k, v in tokens.items()
                       if '%s: %s' % (k, v) not in gs_sec]
        check('③e Global Style 含 manifest token 具体色值', not missing_tok and bool(tokens),
              '缺失=%r' % missing_tok)
        prompts_dir2 = os.path.join(tmp, 'prompts2')
        r = run_py(COMPILER, manifest_path, '--pages', BAKED_ID,
                   '--plan', plan_path, '--anchor', 'cover.png', '--out-dir', prompts_dir2)
        with open(os.path.join(prompts_dir2, BAKED_ID + '.md'), encoding='utf-8') as f:
            prompt_text2 = f.read()
        check('③f 编译幂等（重跑字节一致）', r.returncode == 0 and prompt_text2 == prompt_text)
        r = run_py(COMPILER, manifest_path, '--pages', 'no-such-page',
                   '--plan', plan_path, '--out-dir', os.path.join(tmp, 'prompts3'))
        check('③g 负例：选定页不在 manifest 中非零退出', r.returncode != 0)
        # ③h restructure 分支（v5）：plan 页带 restructure:true → 布局重构授权段出现、
        #    一般构图授权行被替代；缺省（③ 主流程）两者相反
        plan_rs = os.path.join(tmp, 'plan-restructure.json')
        with open(plan_rs, 'w', encoding='utf-8') as f:
            json.dump({'goal': '重构分支测试',
                       'pages': {BAKED_ID: {'layout': '平铺文本页', 'restructure': True}}},
                      f, ensure_ascii=False)
        r = run_py(COMPILER, manifest_path, '--pages', BAKED_ID,
                   '--plan', plan_rs, '--out-dir', os.path.join(tmp, 'prompts-rs'))
        rs_text = ''
        rs_path = os.path.join(tmp, 'prompts-rs', BAKED_ID + '.md')
        if r.returncode == 0 and os.path.isfile(rs_path):
            with open(rs_path, encoding='utf-8') as f:
                rs_text = f.read()
        check('③h restructure:true → 重构授权段出现且替代一般构图授权',
              '布局重构授权' in rs_text and '构图授权：蓝图只约束' not in rs_text)
        check('③i 缺省（无 restructure）→ 无重构授权段、一般构图授权在位',
              '布局重构授权' not in prompt_text and '构图授权：蓝图只约束' not in prompt_text)
        # ③j decorate 分支（v5）：装饰升维授权段出现、一般授权被替代
        plan_dc = os.path.join(tmp, 'plan-decorate.json')
        with open(plan_dc, 'w', encoding='utf-8') as f:
            json.dump({'goal': '装饰分支测试',
                       'pages': {BAKED_ID: {'layout': '高密度页', 'decorate': True}}},
                      f, ensure_ascii=False)
        r = run_py(COMPILER, manifest_path, '--pages', BAKED_ID,
                   '--plan', plan_dc, '--out-dir', os.path.join(tmp, 'prompts-dc'))
        dc_text = ''
        dc_path = os.path.join(tmp, 'prompts-dc', BAKED_ID + '.md')
        if r.returncode == 0 and os.path.isfile(dc_path):
            with open(dc_path, encoding='utf-8') as f:
                dc_text = f.read()
        check('③j decorate:true → 装饰升维授权段出现且替代一般构图授权',
              '装饰升维授权' in dc_text and '构图授权：蓝图只约束' not in dc_text
              and '布局重构授权' not in dc_text)
        check('③k 缺省（无 decorate）→ 无装饰升维授权段', '装饰升维授权' not in prompt_text)

        # ---------- ④ 编辑器行为（harness.html 驱动） ----------
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = ctx.new_page()
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto(BASE + '/harness.html')
            page.wait_for_function("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w && w.state !== undefined && w.document.getElementById('btnSave');
            }""", timeout=8000)
            page.evaluate('([h, n]) => window.loadDeck(h, n)', [src, 'bake-mix/index.html'])
            page.wait_for_function("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w && w.state && w.state.loaded === true && w.registry.length > 0 &&
                     w.frame && w.frame.contentDocument &&
                     w.frame.contentDocument.querySelectorAll('.slide').length > 0;
            }""", timeout=10000)
            page.wait_for_timeout(400)

            reg = page.evaluate("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w.registry.map(r => ({
                slide: r.slideId, kind: r.kind,
                inBaked: !!r.el.closest('.baked-source'),
                slot: r.el.getAttribute && r.el.getAttribute('data-image-slot') }));
            }""")
            in_baked = [r for r in reg if r['inBaked']]
            check('④a 注册表无 .baked-source 内元素（源层文字不进编辑扫描）',
                  not in_baked, '误注册=%r' % in_baked)
            page_imgs = [r for r in reg if r.get('slot') == 'page-baked-16x9']
            check('④b 烙入页整页 img 在注册表内（换图/页级批注可用）', len(page_imgs) == 1)
            n_expected = 19   # cover 5 + ch-now 7（含插画槽位 img）+ ch-end 6 + 整页 img 1
            check('④c 注册表条目数=%d（源层 3 条被排除）' % n_expected,
                  len(reg) == n_expected, '实际=%d' % len(reg))

            # 保存 → 源层字节保留；重载再保存幂等
            n0 = page.evaluate('window.saveCount()')
            page.frame_locator('#ed').locator('#btnSave').click()
            page.wait_for_function('(n) => window.saveCount() > n', arg=n0, timeout=8000)
            saved = page.evaluate('window.lastSave().html')
            check('④d 保存产物源层字节保留', source_block(saved) == source_block(src))
            check('④e 保存产物保留 data-render-mode="baked" 与页面级槽位',
                  'data-render-mode="baked"' in saved and 'page-baked-16x9' in saved)
            page.evaluate('([h, n]) => window.loadDeck(h, n)', [saved, 'bake-mix/index.html'])
            page.wait_for_function("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w && w.state && w.state.loaded === true && w.registry.length > 0;
            }""", timeout=10000)
            page.wait_for_timeout(400)
            n1 = page.evaluate('window.saveCount()')
            page.frame_locator('#ed').locator('#btnSave').click()
            page.wait_for_function('(n) => window.saveCount() > n', arg=n1, timeout=8000)
            saved2 = page.evaluate('window.lastSave().html')
            check('④f 重载再保存幂等', saved2 == saved)
            ctx.close()
            browser.close()

        # 双端一致：保存产物每页 hash 属性 == extractor 重算
        saved_path = os.path.join(tmp, 'saved.html')
        with open(saved_path, 'w', encoding='utf-8') as f:
            f.write(saved)
        m_saved = run_extractor(saved_path)
        re_hashes = hashes_of(m_saved)
        sv = {}
        for mm in re.finditer(r'<section\b[^>]*\bdata-slide-id="([^"]+)"[^>]*>', saved):
            hm = re.search(r'\bdata-content-hash="([^"]*)"', mm.group(0))
            sv[mm.group(1)] = hm.group(1) if hm else None
        mism = [sid for sid in sv if sv[sid] != re_hashes.get(sid)]
        check('④g 双端一致：产物每页 hash == extractor 重算（含烙入页）',
              not mism and all(v and HASH_RE.match(v) for v in sv.values()),
              '不一致页=%r' % mism)

        # ---------- ⑤ 文件级改源层文字 → hash 翻转 ----------
        base_hashes = hashes_of(m1)
        old, new = '>整页烙入示例</h1>', '>整页烙入示例改</h1>'
        assert src.count(old) == 1, 'fixture 假设失效'
        edited_path = os.path.join(tmp, 'edited.html')
        with open(edited_path, 'w', encoding='utf-8') as f:
            f.write(src.replace(old, new))
        m2 = run_extractor(edited_path)
        edited_hashes = hashes_of(m2)
        flipped = [sid for sid in base_hashes if base_hashes[sid] != edited_hashes.get(sid)]
        check('⑤ 改源层文字：恰好烙入页 hash 翻转、其余 3 页不变',
              flipped == [BAKED_ID], '翻转页=%r' % flipped)

        # ---------- ⑥ 混合 deck 回归 ----------
        r = run_py(J_RENDER, deck_html)
        check('⑥a 混合 deck 过 check-render', r.returncode == 0,
              (r.stdout + r.stderr).strip()[-300:])
        r = run_py(K_NAV, deck_html)
        check('⑥b 混合 deck 过 k_nav_check（章节跳转不受 v7.3 影响）', r.returncode == 0,
              (r.stdout + r.stderr).strip()[-300:])
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto('file://' + deck_html)
            page.wait_for_timeout(600)
            n_slots = page.evaluate("document.querySelectorAll('.slide-slot').length")
            for i in range(n_slots):
                page.evaluate("(i) => document.querySelectorAll('.slide-slot')[i]"
                              ".scrollIntoView({block:'start'})", i)
                page.wait_for_timeout(200)
            page.wait_for_timeout(2600)
            rt = page.evaluate("""() => ({
              srcSpans: document.querySelectorAll('.baked-source .sp-unit').length,
              srcI: Array.from(document.querySelectorAll('.baked-source [data-anim]'))
                         .filter(e => e.style.getPropertyValue('--i') !== '').length,
              srcHidden: getComputedStyle(document.querySelector('.baked-source')).display,
              liveSpans: document.querySelectorAll('.slide:not([data-render-mode="baked"]) .sp-unit').length,
              coverText: document.querySelector('[data-slide-id="cover"] h1').textContent,
              nowText: document.querySelector('[data-slide-id="ch-now"] h2').textContent })""")
            check('⑥c 骨架运行时跳过源层：无 .sp-unit、无 --i 注入、源层保持 hidden',
                  rt['srcSpans'] == 0 and rt['srcI'] == 0 and rt['srcHidden'] == 'none',
                  repr(rt))
            check('⑥d 普通页拆字动效照常执行并还原',
                  rt['liveSpans'] == 0 and rt['coverText'] == '混合形态演示'
                  and rt['nowText'] == '现状：内容仍在 HTML 层', repr(rt))
            browser.close()

        # ---------- ⑦ 失败回退演练 ----------
        ph_dir = os.path.join(tmp, 'placeholder')
        shutil.copytree(deck_dir, ph_dir)
        ph_html = os.path.join(ph_dir, 'index.html')
        with open(ph_html, 'w', encoding='utf-8') as f:
            f.write(src.replace('data-image-state="generated"', 'data-image-state="placeholder"'))
        r = subprocess.run(['node', CHECK_IMAGES, ph_html, '--mode', 'illustration'],
                           capture_output=True, text=True)
        check('⑦a 模拟生图失败：placeholder 页级槽位在插画模式下报错',
              r.returncode != 0 and 'placeholder' in r.stderr, r.stderr.strip()[:200])
        r = subprocess.run(['node', CHECK_IMAGES, rev_html], capture_output=True, text=True)
        check('⑦b 诚实回退页（HTML 形态）默认模式校验通过', r.returncode == 0,
              r.stderr.strip()[:200])

        # ---------- ⑧ 图片入场动效（契约 v8 / imagegen v2 G4 / skeleton v7.5） ----------
        IMG_ANIM_WHITELIST = {'', 'rise-in', 'scale-pop', 'wipe-clip'}   # '' = 裸 data-anim（fade）
        # ⑧a 静态：skeleton 版本与整图时长帽；fixture 两张图的 data-anim 均在白名单
        with open(os.path.join(ROOT, 'skills/html-pptx/assets/skeleton.html'), encoding='utf-8') as f:
            skel = f.read()
        skel_ver_m = re.search(r'<meta name="skeleton-version" content="([\d.]+)">', skel)
        skel_ver = float(skel_ver_m.group(1)) if skel_ver_m else 0.0
        # 时长帽规则 v7.5 引入，后续版本沿用——断言版本下限而非钉死版本号
        check('⑧a skeleton ≥v7.5（实测 %s）+ 烙入整图时长帽规则在位'
              % (skel_ver_m.group(1) if skel_ver_m else '无 meta'),
              skel_ver >= 7.5
              and 'img[data-image-slot^="page-baked-"][data-anim]' in skel)
        baked_img_m = re.search(r'<img\b[^>]*\bdata-image-slot="page-baked-16x9"[^>]*>', src)
        slot_img_m = re.search(r'<img\b[^>]*\bdata-image-slot="now-illustration-16x9"[^>]*>', src)
        def anim_of(m):
            am = re.search(r'\bdata-anim(?:="([^"]*)")?', m.group(0)) if m else None
            return am.group(1) if (am and am.group(1) is not None) else ('' if am else None)
        baked_anim, slot_anim = anim_of(baked_img_m), anim_of(slot_img_m)
        check('⑧b 烙入整图与插画槽位 img 均携带白名单 enter 动效（%r / %r）' % (baked_anim, slot_anim),
              baked_anim in IMG_ANIM_WHITELIST and slot_anim in IMG_ANIM_WHITELIST
              and baked_anim is not None and slot_anim is not None)

        # ⑧c 渲染实测（fixture 骨架 v7.3：enter 族纯 CSS 过渡对 img 通用）：
        #    未入视口 opacity:0 → 入视口过渡到终态（渲染校验中图片可见）
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto('file://' + deck_html)
            page.wait_for_timeout(700)
            BIMG = '[data-slide-id="ch-baked"] > img[data-editable-image]'
            SIMG = '[data-slide-id="ch-now"] img[data-editable-image]'
            ini = page.evaluate("""([b, s]) => ({
              b: getComputedStyle(document.querySelector(b)).opacity,
              s: getComputedStyle(document.querySelector(s)).opacity })""" , [BIMG, SIMG])
            check('⑧c-a 未入视口时两张图处于入场初始态（opacity 0）',
                  ini['b'] == '0' and ini['s'] == '0', repr(ini))
            page.evaluate("(i) => document.querySelectorAll('.slide-slot')[i]"
                          ".scrollIntoView({block:'start'})", 1)
            page.wait_for_timeout(1400)
            mid = page.evaluate("""(s) => { const cs = getComputedStyle(document.querySelector(s));
              return { op: cs.opacity, tf: cs.transform }; }""", SIMG)
            check('⑧c-b 插画槽位 img 入视口后到终态（opacity 1 / transform none）',
                  mid['op'] == '1' and mid['tf'] == 'none', repr(mid))
            page.evaluate("(i) => document.querySelectorAll('.slide-slot')[i]"
                          ".scrollIntoView({block:'start'})", 2)
            page.wait_for_timeout(1700)
            fin = page.evaluate("""(b) => { const cs = getComputedStyle(document.querySelector(b));
              return { op: cs.opacity, tf: cs.transform, cp: cs.clipPath }; }""", BIMG)
            check('⑧c-c 烙入整图 wipe-clip 到终态（opacity 1 / clip-path 全揭示）',
                  fin['op'] == '1' and fin['tf'] == 'none'
                  and fin['cp'] in ('none', 'inset(0px)'), repr(fin))

            # ⑧d freeze 终态实测：导出同款序列（export-pptx.py FREEZE_JS +
            #    export-pptx-editable.py 的终态强制样式注入）后，两图呈终态且
            #    满足导出快照的 visible() 门槛（opacity>0.02、有包围盒）
            spec = importlib.util.spec_from_file_location('export_pptx_mod', EXPORT_PPTX)
            exmod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(exmod)
            page2 = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page2.on('pageerror', lambda e: print('[pageerror]', e))
            page2.goto('file://' + deck_html)
            page2.wait_for_timeout(800)
            page2.evaluate(exmod.FREEZE_JS)
            page2.add_style_tag(content=(
                ".js .reveal,.js [data-anim]{opacity:1 !important;transform:none !important;"
                "transition:none !important;filter:none !important;clip-path:none !important}"
                ".js .split-anim .sp-unit{opacity:1 !important;transform:none !important;"
                "transition:none !important}"
                "*{animation:none !important;transition:none !important}"))   # 与 export-pptx-editable.py 注入逐字一致
            page2.wait_for_timeout(300)
            fz = page2.evaluate("""([b, s]) => [b, s].map(sel => { const el = document.querySelector(sel);
              const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
              return { op: cs.opacity, tf: cs.transform, cp: cs.clipPath,
                       vis: cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0.02
                            && r.width > 0 && r.height > 0,
                       loaded: el.complete && el.naturalWidth > 0 }; })""", [BIMG, SIMG])
            check('⑧d-a freeze+终态注入后两图 opacity 1 / transform none / clip-path none',
                  all(x['op'] == '1' and x['tf'] == 'none' and x['cp'] == 'none' for x in fz),
                  repr(fz))
            check('⑧d-b 两图过导出快照 visible() 门槛且位图已加载', all(x['vis'] and x['loaded'] for x in fz),
                  repr(fz))
            shot_b = page2.locator(BIMG).screenshot()
            shot_s = page2.locator(SIMG).screenshot()
            from PIL import Image, ImageStat
            import io as _io
            def img_stats(buf):
                im = Image.open(_io.BytesIO(buf)).convert('L')
                return ImageStat.Stat(im).stddev[0]
            std_b, std_s = img_stats(shot_b), img_stats(shot_s)
            check('⑧d-c freeze 后两图截图非空白（灰度标准差 %.1f / %.1f）' % (std_b, std_s),
                  std_b > 5 and std_s > 5)
            browser.close()

        # ⑧e 骨架 v7.5 整图时长帽实测：以仓库当前骨架合成一页烙入 deck，
        #    wipe-clip（原 .9s）作用于 page-baked img 时被压到 ≤0.8s、零延迟
        anim_dir = os.path.join(tmp, 'anim-cap')
        os.makedirs(anim_dir)
        os.symlink(os.path.join(FIXTURE, 'assets'), os.path.join(anim_dir, 'assets'))
        with open(os.path.join(ROOT, 'skills/html-pptx/assets/skeleton.html'), encoding='utf-8') as f:
            skel_doc = f.read()
        baked_slide = ('<div class="slide-slot"><section class="slide" data-slide-id="cap-baked" '
                       'data-render-mode="baked"><img data-editable-image '
                       'data-image-slot="page-baked-16x9" data-image-intent="时长帽合成页" '
                       'data-image-state="generated" src="assets/page-ch-baked.png" alt="cap" '
                       'data-anim="wipe-clip" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">'
                       '<div class="baked-source" hidden><h1 data-editable>时长帽</h1></div>'
                       '</section></div>')
        anchor = '\n</div>\n\n<!-- SLOT: 页码初始文本'
        assert anchor in skel_doc, '骨架 slides 槽位锚点失效'
        skel_doc = skel_doc.replace(anchor, '\n  ' + baked_slide + anchor)
        cap_html = os.path.join(anim_dir, 'index.html')
        with open(cap_html, 'w', encoding='utf-8') as f:
            f.write(skel_doc)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto('file://' + cap_html)
            page.wait_for_timeout(700)
            cap = page.evaluate("""() => { const img = document.querySelector(
              '[data-slide-id="cap-baked"] > img'); const cs = getComputedStyle(img);
              return { ver: document.querySelector('meta[name=skeleton-version]').content,
                       dur: cs.transitionDuration, delay: cs.transitionDelay }; }""")
            durs = [float(x) for x in re.findall(r'([\d.]+)s', cap['dur'])]
            delays = [float(x) for x in re.findall(r'([\d.]+)s', cap['delay'])]
            check('⑧e skeleton ≥v7.5 烙入整图动效 ≤0.8s 且零延迟（ver=%s dur=%s delay=%s）'
                  % (cap['ver'], cap['dur'], cap['delay']),
                  float(cap['ver']) >= 7.5 and durs and max(durs) <= 0.8
                  and (not delays or max(delays) == 0.0))
            page.evaluate("document.querySelectorAll('.slide-slot')[2]"
                          ".scrollIntoView({block:'start'})")
            page.wait_for_timeout(1500)
            cap2 = page.evaluate("""() => { const cs = getComputedStyle(document.querySelector(
              '[data-slide-id="cap-baked"] > img')); return { op: cs.opacity, cp: cs.clipPath }; }""")
            check('⑧f v7.5 骨架下烙入整图入视口到终态（图片可见）',
                  cap2['op'] == '1' and cap2['cp'] in ('none', 'inset(0px)'), repr(cap2))
            browser.close()
    finally:
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)

    print('RESULT:', 'ALL PASS' if not FAILURES else '%d FAILURES: %s' % (len(FAILURES), FAILURES))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())
