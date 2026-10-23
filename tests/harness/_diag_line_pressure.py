#!/usr/bin/env python3
"""诊断 2（scratch）：cmb-retail 逐文本叶逐渲染行的 PPT 换行压力分布。
判定每行 ink_w / (render_w×1.02×0.97) 比值——>1 即导出侧幻行（est 2 行）。
同时给单行叶的墨水宽×1.08/1.15 与邻居横向间隙关系。
用法：python3 tests/harness/_diag_line_pressure.py"""
import importlib.util
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECK = os.path.join(ROOT, 'tests/decks/cmb-retail/index.html')

spec = importlib.util.spec_from_file_location(
    'epx_editable', os.path.join(ROOT, 'skills/html-pptx/scripts/export-pptx-editable.py'))
mod = importlib.util.module_from_spec(spec)
sys.modules['epx_editable'] = mod
spec.loader.exec_module(mod)

DEGRADED = {'research-team', 'wealth-upgrade', 'allocation-solution', 'qdii-mrf',
            'research-overview', 'index-team', 'quant-team', 'equity-team',
            'fixed-income-team', 'fof-team', 'intl-team', 'regional-model',
            'org-structure'}

import tempfile
work = tempfile.mkdtemp(prefix='diag-pressure-')
with mod.RenderSession(DECK) as sess:
    snap, deck_lang = sess.snapshot()
deck_dir = os.path.dirname(DECK)
fplan = mod.plan_fonts(snap, deck_lang, deck_dir, work, False)
cands = fplan['cands']
mod.apply_layout(snap, fplan)

print('lang=%s' % deck_lang)
for pg in snap['pages']:
    sid = pg['slide_id']
    mark = '★' if sid in DEGRADED else ' '
    hot = []
    for it in pg['items']:
        if it['kind'] != 'text':
            continue
        st = it['style']
        mf = mod.parse_font_family(st['fontFamily'], None)
        fs = st['fontSizePx']
        lines = it.get('lines') or []
        if len(lines) <= 1:
            text = ''.join(r['text'] for l in lines for r in l['runs'])
            ink_w = cands.width_px_for(text, fs, mf['latin'], mf['ea'],
                                       st.get('letterSpacingPx', 0))
            ratio = ink_w / max(it['rect']['width'], 1)
            if ratio > 0.90:
                hot.append(('单行', ratio, text[:14], it['rect']['width'], ink_w))
        else:
            w = it['rect']['width'] * 1.02 * 0.97
            for li, line in enumerate(lines):
                lw = cands.width_px_for(''.join(r['text'] for r in line['runs']),
                                        fs, mf['latin'], mf['ea'])
                ratio = lw / max(w, 1)
                if ratio > 0.95:
                    hot.append(('行%d' % (li + 1), ratio,
                                ''.join(r['text'] for r in line['runs'])[:14],
                                it['rect']['width'], lw))
    if hot and (sid in DEGRADED):
        print('%s %s: %d 行 >0.95' % (mark, sid, len(hot)))
        for tag, ratio, txt, rw, lw in sorted(hot, key=lambda h: -h[1])[:8]:
            print('     %s ratio=%.3f 渲染宽 %.0f 墨水 %.0f  %r' % (tag, ratio, rw, lw, txt))

# 全 deck 统计
tot = over = 0
for pg in snap['pages']:
    for it in pg['items']:
        if it['kind'] != 'text':
            continue
        st = it['style']
        mf = mod.parse_font_family(st['fontFamily'], None)
        fs = st['fontSizePx']
        lines = it.get('lines') or []
        if len(lines) <= 1:
            continue
        w = it['rect']['width'] * 1.02 * 0.97
        for line in lines:
            lw = cands.width_px_for(''.join(r['text'] for r in line['runs']),
                                    fs, mf['latin'], mf['ea'])
            tot += 1
            if lw > w:
                over += 1
print('多行叶逐行统计：%d 行，幻行（>0.9894 净宽）%d 行' % (tot, over))
