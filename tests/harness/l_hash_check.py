#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三形态 M1 验收：页级 content-hash（tri-form-architecture.md §4.3 / §7）。

用法：python3 tests/harness/l_hash_check.py

检查项（全部硬断言）：
  ① 幂等——对 fixture deck 连续两次提取，除 extracted_at 外字节一致；
  ② 编辑翻转——拷贝 deck 改一处 data-editable 文本后重提取：该页 hash 翻转、
     其余页 hash 不变；
  ③ 双端一致【M1 核心】——驱动 editor.html（嵌入模式）加载 fixture、就地改一处
     文字并保存（postMessage 捕获产物），对保存产物跑 extract-manifest.py：
     产物中每页 data-content-hash 属性值必须等于 extractor 重算值
     （证明编辑器 Web Crypto 端与 extractor 端算法同构）；且编辑页 hash 相对
     原 deck 翻转、他页不变（编辑器路径下复核②）；
  ④ 保存产物全 deck 每页都有合法 data-content-hash（12 位 hex）。
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
EXTRACTOR = os.path.join(ROOT, 'skills/html-pptx/scripts/extract-manifest.py')
FIXTURE = os.path.join(ROOT, 'tests/decks/tech-ikb-v3')   # 含动效/图片的中等 deck
PORT = 8932
BASE = 'http://127.0.0.1:%d' % PORT
HASH_RE = re.compile(r'^[0-9a-f]{12}$')

FAILURES = []


def check(label, cond, detail=''):
    print('%s  %s%s' % ('PASS' if cond else 'FAIL', label,
                        (' — ' + detail) if (detail and not cond) else ''))
    if not cond:
        FAILURES.append(label)


def run_extractor(deck_html):
    """跑 extract-manifest.py，返回（manifest dict，stdout 去 extracted_at 的规范化文本）。"""
    r = subprocess.run([sys.executable, EXTRACTOR, deck_html],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('extractor 失败：%s%s' % (r.stdout, r.stderr))
    manifest = json.loads(r.stdout)
    canon = dict(manifest)
    canon['deck'] = dict(manifest['deck'])
    canon['deck'].pop('extracted_at', None)
    canon_text = json.dumps(canon, ensure_ascii=False, sort_keys=True)
    return manifest, canon_text


def hashes_of(manifest):
    return {p['slide_id']: p['content_hash'] for p in manifest['pages']}


def saved_hashes(html):
    """从保存产物中逐页取 data-slide-id → data-content-hash（同一 <section> 标签内）。"""
    out = {}
    for m in re.finditer(r'<section\b[^>]*\bdata-slide-id="([^"]+)"[^>]*>', html):
        hm = re.search(r'\bdata-content-hash="([^"]*)"', m.group(0))
        out[m.group(1)] = hm.group(1) if hm else None
    return out


def main():
    tmp = tempfile.mkdtemp(prefix='pptx-hash-check-')
    serve = os.path.join(tmp, 'serve')
    os.makedirs(serve)
    # 工作副本（extractor 幂等/编辑翻转用，不动 tests/decks 原件）
    deck_dir = os.path.join(tmp, 'deck')
    shutil.copytree(FIXTURE, deck_dir)
    deck_html = os.path.join(deck_dir, 'index.html')
    # 嵌入模式 harness：editor.html + harness.html
    os.symlink(os.path.join(ROOT, 'editor.html'), os.path.join(serve, 'editor.html'))
    shutil.copy(os.path.join(ROOT, 'tests/harness/harness.html'),
                os.path.join(serve, 'harness.html'))

    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                            '--bind', '127.0.0.1', '-d', serve],
                           stdout=open(os.path.join(tmp, 'srv.log'), 'w'),
                           stderr=subprocess.STDOUT)
    try:
        up = False
        for _ in range(50):
            if srv.poll() is not None:
                raise RuntimeError('静态服务启动失败（端口 %d 被占用？），日志：\n%s'
                                   % (PORT, open(os.path.join(tmp, 'srv.log')).read()))
            try:
                urllib.request.urlopen(BASE + '/harness.html', timeout=1)
                up = True
                break
            except Exception:
                time.sleep(0.2)
        if not up:
            raise RuntimeError('静态服务 10s 内未就绪')

        # ---------- ① 幂等 ----------
        m1, c1 = run_extractor(deck_html)
        m2, c2 = run_extractor(deck_html)
        check('① 提取幂等（除 extracted_at）', c1 == c2)
        n_pages = len(m1['pages'])
        check('①b 页数 >0', n_pages > 0, 'pages=%d' % n_pages)
        base_hashes = hashes_of(m1)
        check('①c 每页 hash 为 12 位 hex',
              all(HASH_RE.match(h or '') for h in base_hashes.values()),
              repr(base_hashes))

        # ---------- ② 编辑翻转（文件级：改字 → 重提取对比） ----------
        with open(deck_html, encoding='utf-8') as f:
            src = f.read()
        old, new = '>从单体到微服务的三年</h1>', '>从单体到微服务的四年</h1>'
        assert src.count(old) == 1, 'fixture 假设失效：%r 出现 %d 次' % (old, src.count(old))
        edited_html_path = os.path.join(tmp, 'deck-edited.html')
        with open(edited_html_path, 'w', encoding='utf-8') as f:
            f.write(src.replace(old, new))
        m3, _ = run_extractor(edited_html_path)
        edited_hashes = hashes_of(m3)
        flipped = [sid for sid in base_hashes if base_hashes[sid] != edited_hashes.get(sid)]
        check('② 编辑翻转：恰好封面页 hash 翻转、其余 %d 页不变' % (n_pages - 1),
              flipped == ['cover'], '翻转页=%r' % flipped)

        # ---------- ③ 双端一致（编辑器保存产物 vs extractor 重算） ----------
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
            page.evaluate('([h, n]) => window.loadDeck(h, n)', [src, 'tech-ikb-v3/index.html'])
            page.wait_for_function("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w && w.state && w.state.loaded === true && w.registry.length > 0 &&
                     w.frame && w.frame.contentDocument &&
                     w.frame.contentDocument.querySelectorAll('.slide').length > 0;
            }""", timeout=10000)
            page.wait_for_timeout(400)

            # 就地改封面标题（两段手势 + Ctrl+Enter 确认，与 run_e2e T2 同打法）
            h1 = page.frame_locator('#ed').frame_locator('#deckFrame').locator(
                '[data-slide-id="cover"] h1[data-editable]')
            h1.click(); h1.click()
            page.keyboard.type('从单体到微服务的四年')
            page.keyboard.press('Control+Enter')

            n0 = page.evaluate('window.saveCount()')
            page.frame_locator('#ed').locator('#btnSave').click()
            page.wait_for_function('(n) => window.saveCount() > n', arg=n0, timeout=8000)
            saved = page.evaluate('window.lastSave().html')
            ctx.close()
            browser.close()

        saved_path = os.path.join(tmp, 'saved.html')
        with open(saved_path, 'w', encoding='utf-8') as f:
            f.write(saved)

        # ④ 保存产物每页都有合法 hash
        sv = saved_hashes(saved)
        check('④ 产物每页 data-content-hash 合法（%d/%d 页，12 位 hex）'
              % (sum(1 for v in sv.values() if v and HASH_RE.match(v)), n_pages),
              len(sv) == n_pages and all(v and HASH_RE.match(v) for v in sv.values()),
              repr(sv))

        # ③ 对保存产物跑 extractor：重算值 == 产物属性值
        m4, _ = run_extractor(saved_path)
        re_hashes = hashes_of(m4)
        mism = [sid for sid in sv if sv[sid] != re_hashes.get(sid)]
        check('③ 双端一致：产物属性 == extractor 重算（%d 页）' % n_pages,
              not mism, '不一致页=%r' % mism)

        # 编辑器路径下复核②：编辑页翻转、他页与原 deck 一致
        flipped2 = [sid for sid in base_hashes if base_hashes[sid] != re_hashes.get(sid)]
        check('③b 编辑器编辑翻转：恰好封面页翻转、其余不变',
              flipped2 == ['cover'], '翻转页=%r' % flipped2)
    finally:
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)

    print('RESULT:', 'ALL PASS' if not FAILURES else '%d FAILURES: %s' % (len(FAILURES), FAILURES))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())
