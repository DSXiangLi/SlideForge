#!/usr/bin/env python3
"""诊断 4（scratch）：逐文本叶宽度需求报告——每个多行叶 est>渲 时给出
需求渲染宽（max 行墨水/0.9894）与当前渲染宽；单行叶给出墨水宽与渲染宽。
用法：python3 tests/harness/_diag_width_needs.py [slide_id 过滤]"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECK = os.path.join(ROOT, 'tests/decks/cmb-retail/index.html')
ONLY = set(sys.argv[1:])

spec = importlib.util.spec_from_file_location(
    'epx', os.path.join(ROOT, 'skills/html-pptx/scripts/export-pptx-editable.py'))
mod = importlib.util.module_from_spec(spec)
sys.modules['epx'] = mod
spec.loader.exec_module(mod)
spec2 = importlib.util.spec_from_file_location(
    'm', os.path.join(ROOT, 'skills/html-pptx/scripts/pptx_text_metrics.py'))
metrics = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(metrics)

with mod.RenderSession(DECK) as sess:
    snap, lang = sess.snapshot()
declared = []
for role in ('display', 'body', 'mono'):
    st = (snap.get('fontStacks') or {}).get(role)
    if st:
        f = mod.parse_font_family(st, lang)
        declared += [f['latin'], f['ea']]
cands = metrics.CandidateSet.build(sorted(set(declared)), [])

for pg in snap['pages']:
    sid = pg['slide_id']
    if ONLY and sid not in ONLY:
        continue
    rows = []
    for it in pg['items']:
        if it['kind'] != 'text':
            continue
        st = it['style']
        mf = mod.parse_font_family(st['fontFamily'], None)
        fs = st['fontSizePx']
        lines = it.get('lines') or []
        rw = it['rect']['width']
        if len(lines) <= 1:
            text = ''.join(r['text'] for l in lines for r in l['runs'])
            ink = cands.width_px_for(text, fs, mf['latin'], mf['ea'],
                                     st.get('letterSpacingPx', 0))
            if ink > rw * 0.995:
                rows.append(('单行', rw, ink, ink / max(rw, 1), text[:18]))
        else:
            maxink = 0.0
            for line in lines:
                lw = cands.width_px_for(''.join(r['text'] for r in line['runs']),
                                        fs, mf['latin'], mf['ea'])
                maxink = max(maxink, lw)
            thr = rw * 1.02 * 0.97
            if maxink > thr:
                need_w = maxink / 0.9894
                txt = ''.join(r['text'] for l in lines for r in l['runs'])
                rows.append(('多行%d→需%d行' % (len(lines), 0), rw, need_w,
                             need_w / max(rw, 1), txt[:18]))
    if rows:
        print('=== %s ===' % sid)
        for tag, rw, ink, ratio, txt in sorted(rows, key=lambda r: -r[3]):
            print('  %-12s 渲染宽 %6.1f 需求宽 %6.1f (×%.3f)  %r' % (tag, rw, ink, ratio, txt))
