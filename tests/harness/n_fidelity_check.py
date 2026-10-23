#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三形态 M3 验收：HTML→PPTX 导出管线（docs/design/pptx-export-svg.md §6）。

用法：python3 tests/harness/n_fidelity_check.py

fixture：tests/decks/bake-mix/ 的临时副本（4 页混合 deck——3 HTML 页 +
1 烙入页，覆盖烙入直通分支）。脚本全程只动临时副本，fixture 只读。

命名偏差说明：设计文档 pptx-export-svg.md §6 称本检查为 m_fidelity_check.py；
m_ 前缀已被 m_bake_check.py（M2）占用，本脚本用 n_ 前缀，经 run_e2e T25 纳入回归。

检查项（全部硬断言）：
  ① 全流程：export-pptx.py 跑通临时副本，出口 0，耗时 < 120s；
  ② postflight 复核：python-pptx 重开 deck.pptx 页数=4；zip 结构
     4 PNG + 3 SVG + [Content_Types] svg Default；manifest 载体分布
     = 3 svg + 1 baked（烙入页 ch-baked 直通）；
  ③ 保真阈值：全 deck 平均 diff < 2%（fidelity_avg > 98）、单页 diff < 5%
     （fidelity > 95）；烙入页直通不参与 diff（fidelity=null）；
  ④ export/manifest.json schema：每页 carrier/fidelity/export_hash 齐备，
     顶层含导出时间/转换器版本/门禁结果；
  ⑤ stale 检出：改 deck 一字 → --check-stale 非零退出且指名该页；
     未改动时 --check-stale 出口 0；
  ⑥ 降级演练：PATH 屏蔽 pdftocairo → png-fallback 生效且逐页列明降级原因；
     PPTX_EXPORT_DISABLE_SCREENSHOT=1 模拟截图设施不可用 → 非零退出且
     不产 export/ 半成品；
  ⑦ 单向纪律：导出前后 index.html 字节一致（sha256）；
  ⑧ 门禁演练：伪造漂移基线（.manifest-baseline.json 篡改 line_count）→
     防线 C2 阻断、非零退出、逐元素列出页与文本。
退出码：全过 0，任一失败 1。
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORTER = os.path.join(ROOT, 'skills/html-pptx/scripts/export-pptx.py')
EXTRACTOR = os.path.join(ROOT, 'skills/html-pptx/scripts/extract-manifest.py')
FIXTURE = os.path.join(ROOT, 'tests/decks/bake-mix')
BAKED_ID = 'ch-baked'
HASH_RE = re.compile(r'^[0-9a-f]{12}$')

FAILURES = []


def check(label, cond, detail=''):
    print('%s  %s%s' % ('PASS' if cond else 'FAIL', label,
                        (' — ' + detail) if (detail and not cond) else ''))
    if not cond:
        FAILURES.append(label)


def run_export(deck_html, *extra, env=None):
    return subprocess.run([sys.executable, EXPORTER, deck_html, *extra],
                          capture_output=True, text=True, env=env)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fresh_deck(tmp, name):
    d = os.path.join(tmp, name)
    # 派生产物不随 fixture 拷贝（export/ 由本测试现跑现验；prompts/ 是烙入工作区），
    # 否则 fixture 目录里残留的 export/deck.pptx 会让预备导出被"重导需 --force"拒绝。
    shutil.copytree(FIXTURE, d, ignore=shutil.ignore_patterns('export', 'prompts'))
    return os.path.join(d, 'index.html')


def main():
    tmp = tempfile.mkdtemp(prefix='pptx-export-check-')
    try:
        # ---------- ⓪ SVG 引用安全契约 ----------
        spec = importlib.util.spec_from_file_location('export_pptx_under_test', EXPORTER)
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        png = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+'
               'A8AAQUBAScY42YAAAAASUVORK5CYII=')
        padding = '<!--' + ('x' * 520) + '-->'

        def svg_result(name, body):
            path = os.path.join(tmp, name)
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">'
                        + padding + body + '</svg>')
            return exporter.svg_sanity(path)

        check('⓪a pdftocairo PNG/JPEG data URI 是已内联资源',
              svg_result('inline.svg', '<image href="data:image/png;base64,' + png
                         + '"/><image href="data:image/jpeg;base64,/9j/2Q=="/>') is None)
        check('⓪b 纯矢量 fragment 引用不受影响',
              svg_result('fragment.svg', '<defs><path id="p" d="M0 0"/></defs><use href="#p"/><rect style="fill:url(#p)"/>') is None)
        bad_refs = {
            'https': 'https://example.com/a.png',
            'local': 'local.png',
            'active-data': 'data:image/svg+xml;base64,PHN2Zy8+',
            'malformed-data': 'data:image/png;base64,not-base64',
            'mime-spoof': 'data:image/png;base64,/9j/2Q==',
        }
        rejected = {name: svg_result(name + '.svg', '<image href="' + ref + '"/>')
                    for name, ref in bad_refs.items()}
        rejected['css-external'] = svg_result(
            'css-external.svg', '<rect style="fill:url(https://example.com/a.png)"/>')
        check('⓪c 外链、本地路径、主动/畸形/伪装 data URI 继续拒绝',
              all(rejected.values()), repr(rejected))

        # ---------- ① 全流程 + ⑦ 单向纪律 ----------
        deck = fresh_deck(tmp, 'main')
        before = sha256(deck)
        t0 = time.time()
        r = run_export(deck)
        dt = time.time() - t0
        check('①a 全流程出口 0（耗时 %.1fs）' % dt, r.returncode == 0,
              (r.stdout + r.stderr).strip()[-400:])
        check('①b 全流程耗时 < 120s', dt < 120, '%.1fs' % dt)
        check('⑦ 单向纪律：导出前后 index.html 字节一致', sha256(deck) == before)

        export_dir = os.path.join(os.path.dirname(deck), 'export')
        pptx = os.path.join(export_dir, 'deck-vector.pptx')   # 保真轨（C3 定名）
        mf_path = os.path.join(export_dir, 'manifest.json')
        check('①c 双轨产物齐备（deck.pptx 可编辑 + deck-vector.pptx + deck.pdf + manifest.json）',
              os.path.isfile(pptx) and os.path.isfile(mf_path)
              and os.path.isfile(os.path.join(export_dir, 'deck.pptx'))
              and os.path.isfile(os.path.join(export_dir, 'deck.pdf')))
        with open(os.path.join(export_dir, 'deck.pdf'), 'rb') as f:
            pdf_bytes = f.read()
        check('①d deck.pdf 直出：4 页 MediaBox', pdf_bytes.count(b'/MediaBox') == 4)

        # ---------- ② postflight 复核 ----------
        from pptx import Presentation
        prs = Presentation(pptx)
        check('②a pptx 重开页数=4', len(list(prs.slides)) == 4)
        with zipfile.ZipFile(pptx) as z:
            names = z.namelist()
            n_png = len([n for n in names if n.startswith('ppt/media/') and n.endswith('.png')])
            n_svg = len([n for n in names if n.startswith('ppt/media/') and n.endswith('.svg')])
            ct = z.read('[Content_Types].xml').decode('utf-8')
        check('②b media 结构 4 PNG + 3 SVG', n_png == 4 and n_svg == 3,
              'png=%d svg=%d' % (n_png, n_svg))
        check('②c [Content_Types] 含 svg Default', 'Extension="svg"' in ct)
        with open(mf_path, encoding='utf-8') as f:
            mf = json.load(f)
        carriers = {p['slide_id']: p.get('carrier') for p in mf['pages']}
        check('②d 烙入页载体=baked、HTML 页载体=svg',
              carriers.get(BAKED_ID) == 'baked'
              and all(c == 'svg' for sid, c in carriers.items() if sid != BAKED_ID),
              repr(carriers))
        tracks = mf.get('export', {}).get('tracks', {})
        check('②e tracks schema：双轨 ok + 可编辑轨指标齐备',
              tracks.get('vector', {}).get('ok') is True
              and tracks.get('editable', {}).get('ok') is True
              and tracks['editable'].get('native_text_ratio') == 1.0
              and 'fonts_embedded' in tracks['editable'])

        # ---------- ③ 保真阈值 ----------
        fids = {p['slide_id']: p.get('fidelity') for p in mf['pages']}
        html_fids = [v for sid, v in fids.items() if sid != BAKED_ID]
        avg = mf.get('export', {}).get('fidelity_avg')
        check('③a 烙入页 fidelity=null（直通不参与 diff）', fids.get(BAKED_ID) is None)
        check('③b 全 deck 平均 diff < 2%%（fidelity_avg=%s）' % avg,
              avg is not None and avg > 98)
        check('③c 单页 diff < 5%%（逐页 fidelity=%s）' % fids,
              all(v is not None and v > 95 for v in html_fids))
        check('③d 差异热区产出（page-NN.diff.png ×3）',
              sum(1 for n in os.listdir(export_dir) if n.endswith('.diff.png')) == 3)

        # ---------- ④ manifest schema ----------
        ok_schema = True
        for p in mf['pages']:
            if p.get('carrier') not in ('svg', 'png-fallback', 'baked'):
                ok_schema = False
            if not HASH_RE.match(p.get('export_hash') or ''):
                ok_schema = False
            if p.get('carrier') == 'baked':
                if p.get('fidelity') is not None:
                    ok_schema = False
            elif not isinstance(p.get('fidelity'), (int, float)):
                ok_schema = False
            if not isinstance(p.get('uncovered_glyphs'), list):
                ok_schema = False
        exp = mf.get('export', {})
        check('④a 每页 carrier/fidelity/export_hash/uncovered_glyphs 齐备', ok_schema)
        check('④b 顶层含 exported_at/converter/gate',
              bool(exp.get('exported_at')) and bool(exp.get('converter')) and bool(exp.get('gate')))
        check('④c M1 提取态字段保留（theme/pages[].texts/content_hash）',
              bool(mf.get('theme')) and all(p.get('texts') is not None and p.get('content_hash')
                                            for p in mf['pages']))

        # ---------- ⑤ stale 检出 ----------
        r = run_export(deck, '--check-stale')
        check('⑤a 未改动时 --check-stale 出口 0', r.returncode == 0, r.stderr.strip()[:200])
        with open(deck, encoding='utf-8') as f:
            src = f.read()
        old, new = '>现状：内容仍在 HTML 层<', '>现状：内容仍然在 HTML 层<'
        assert src.count(old) == 1, 'fixture 假设失效'
        with open(deck, 'w', encoding='utf-8') as f:
            f.write(src.replace(old, new))
        r = run_export(deck, '--check-stale')
        check('⑤b 改一字 → stale 检出非零退出且指名 ch-now',
              r.returncode != 0 and 'ch-now' in (r.stdout + r.stderr),
              (r.stdout + r.stderr).strip()[:200])
        with open(deck, 'w', encoding='utf-8') as f:
            f.write(src)  # 还原，单向纪律后续不再用本副本

        # ---------- ⑥ 降级演练 ----------
        empty_bin = os.path.join(tmp, 'empty-bin')
        os.makedirs(empty_bin)
        env_no_cairo = dict(os.environ, PATH=empty_bin)
        deck_b = fresh_deck(tmp, 'degrade')
        r = run_export(deck_b, env=env_no_cairo)
        ok_deg = False
        if r.returncode == 0:
            with open(os.path.join(os.path.dirname(deck_b), 'export', 'manifest.json'),
                      encoding='utf-8') as f:
                mf_b = json.load(f)
            cb = {p['slide_id']: (p.get('carrier'), p.get('degraded_reason'))
                  for p in mf_b['pages']}
            ok_deg = (cb.get(BAKED_ID, ('',))[0] == 'baked'
                      and all(v[0] == 'png-fallback' and v[1]
                              for sid, v in cb.items() if sid != BAKED_ID))
        check('⑥a 屏蔽 pdftocairo → png-fallback 生效且逐页列明降级原因', ok_deg,
              'rc=%d %s' % (r.returncode, (r.stdout + r.stderr).strip()[-300:]))
        deck_c = fresh_deck(tmp, 'noshot')
        env_no_shot = dict(os.environ, PPTX_EXPORT_DISABLE_SCREENSHOT='1')
        r = run_export(deck_c, env=env_no_shot)
        exp_c = os.path.join(os.path.dirname(deck_c), 'export')
        check('⑥b 截图设施不可用 → 保真轨失败非零退出、无 deck-vector.pptx；'
              '可编辑轨（bake-mix 无烙图需求）不被阻断',
              r.returncode != 0
              and not os.path.exists(os.path.join(exp_c, 'deck-vector.pptx'))
              and os.path.exists(os.path.join(exp_c, 'deck.pptx')),
              'rc=%d' % r.returncode)

        # ---------- ⑧ 门禁演练（伪造漂移基线） ----------
        deck_d = fresh_deck(tmp, 'gate')
        work_m = os.path.join(tmp, 'baseline.json')
        r = subprocess.run([sys.executable, EXTRACTOR, deck_d, '--out', work_m],
                           capture_output=True, text=True)
        check('⑧a 基线提取成功', r.returncode == 0, r.stderr.strip()[:200])
        with open(work_m, encoding='utf-8') as f:
            base = json.load(f)
        victim = None
        for p in base['pages']:
            for t in p.get('texts', []):
                if t.get('content') and t.get('line_count'):
                    victim = (p['slide_id'], t['content'])
                    t['line_count'] = t['line_count'] + 1  # 伪造字体漂移
                    break
            if victim:
                break
        with open(os.path.join(os.path.dirname(deck_d), '.manifest-baseline.json'),
                  'w', encoding='utf-8') as f:
            json.dump(base, f, ensure_ascii=False)
        r = run_export(deck_d)
        check('⑧b 伪造漂移基线 → 防线 C2 阻断并非零退出',
              r.returncode != 0 and '防线 C2 阻断' in (r.stdout + r.stderr),
              (r.stdout + r.stderr).strip()[-300:])
        check('⑧c 阻断报告逐元素列出页与文本',
              victim is not None and victim[0] in (r.stdout + r.stderr)
              and victim[1][:12] in (r.stdout + r.stderr))
        exp_d = os.path.join(os.path.dirname(deck_d), 'export')
        check('⑧d 门禁阻断不产 export/ 半成品（可编辑轨已撤下）',
              not os.path.exists(exp_d) or not os.listdir(exp_d))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('RESULT:', 'ALL PASS' if not FAILURES else '%d FAILURES: %s' % (len(FAILURES), FAILURES))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())
