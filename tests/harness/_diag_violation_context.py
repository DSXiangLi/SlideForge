#!/usr/bin/env python3
"""诊断 3（scratch）：gate v2 违规的几何上下文详单——每条违规给出双方
px 矩形与文本，供逐页修 deck 定位。
用法：python3 tests/harness/_diag_violation_context.py [deck/index.html]"""
import importlib.util
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'tests/decks/cmb-retail/index.html')

spec = importlib.util.spec_from_file_location(
    'epx_editable', os.path.join(ROOT, 'skills/html-pptx/scripts/export-pptx-editable.py'))
mod = importlib.util.module_from_spec(spec)
sys.modules['epx_editable'] = mod
spec.loader.exec_module(mod)
spec2 = importlib.util.spec_from_file_location(
    'pptx_text_metrics', os.path.join(ROOT, 'skills/html-pptx/scripts/pptx_text_metrics.py'))
metrics = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(metrics)
certmod = mod._certify_mod

import tempfile
work = tempfile.mkdtemp(prefix='diag-ctx-')
with mod.RenderSession(DECK) as sess:
    snap, deck_lang = sess.snapshot()
deck_dir = os.path.dirname(os.path.abspath(DECK))
declared = []
for role in ('display', 'body', 'mono'):
    st = (snap.get('fontStacks') or {}).get(role)
    if st:
        f = mod.parse_font_family(st, deck_lang)
        declared += [f['latin'], f['ea']]
fonts_dir = os.path.join(deck_dir, 'fonts')
embeds = [os.path.join(fonts_dir, f) for f in sorted(os.listdir(fonts_dir))
          if f.lower().endswith(('.ttf', '.otf'))] if os.path.isdir(fonts_dir) else []
cands = metrics.CandidateSet.build(sorted(set(declared)), embeds)
fplan = {'cands': cands, 'margin_mode': 'normal', 'notes': [], 'embeds': []}
mod.apply_layout(snap, fplan)

def px(rect_pt):
    return [round(rect_pt[k] * 2, 1) for k in ('l', 't', 'r', 'b')]

out = []
for pi, pg in enumerate(snap['pages'], 1):
    se = mod.slide_elements_from_snap(pg, deck_lang)
    vs = certmod.certify_elements([se], cands)
    if not vs:
        continue
    print('=== %s (%d) ===' % (pg['slide_id'], len(vs)))
    # 重建墨水盒与形状盒（certify 同公式）
    text_boxes = {}
    for ti, t in enumerate(se.texts):
        net_w = t['w'] - t['insets']['lIns'] - t['insets']['rIns']
        need_h = 0.0
        ink_w_max = 0.0
        ln_last = ln_first = None
        n_lines_total = 0
        for para in t['paras']:
            nat_worst = 0.0
            ink_w = 0.0
            sz_max_para = max((run['sz'] for run in para['runs']), default=0.0)
            for run in para['runs']:
                sz = run['sz'] * t['fontScale']
                ink_w += cands.width_pt_for(run['text'], sz, run['latin'], run['ea'],
                                            run['spc'], run['bold'], with_boundary=False)
                nat_worst = max(nat_worst, cands.natural_factor(run['latin'], run['ea']) * sz)
            ink_w += metrics.mixed_boundaries(''.join(r['text'] for r in para['runs'])) \
                * metrics.MIXED_BOUNDARY_EM * sz_max_para * t['fontScale']
            if para['lnspc'] is None:
                ln_worst = nat_worst
            elif para['lnspc'][0] == 'pct':
                ln_worst = para['lnspc'][1] * nat_worst
            else:
                ln_worst = para['lnspc'][1]
            if t['wrap'] == 'none':
                est = 1
            else:
                est = max(1, int(math.ceil(ink_w / max(net_w * 0.97, 1)))) \
                    if ink_w > net_w * 0.97 else 1
            need_h += est * ln_worst
            n_lines_total += est
            ln_last = ln_worst
            if ln_first is None:
                ln_first = ln_worst
            ink_w_max = max(ink_w_max, min(ink_w, net_w) if t['wrap'] != 'none' else ink_w)
        sz_max = max((r['sz'] for p in t['paras'] for r in p['runs']), default=0.0)
        em_worst = max((cands.em_factor(r['latin'], r['ea'])
                        for p in t['paras'] for r in p['runs']), default=1.0)
        em_h = em_worst * sz_max * t['fontScale']
        ink_h = (need_h - (ln_last or 0)) + em_h if n_lines_total else need_h
        text_boxes[t['name']] = {'l': t['x'], 't': t['y'],
                                 'r': t['x'] + min(ink_w_max + t['insets']['lIns']
                                                   + t['insets']['rIns'], t['w']),
                                 'b': t['y'] + ink_h,
                                 'first': t['first'], 'est': n_lines_total,
                                 'render_lines': len(t['paras']), 'wrap': t['wrap']}
    for v in vs:
        names = [n for n in [v['el'].split(' × ')[0],
                             v['el'].split(' × ')[-1]] if n in text_boxes]
        desc = []
        for n in v['el'].split(' × '):
            n = n.replace('压 ', '').strip()
            if n in text_boxes:
                tb = text_boxes[n]
                desc.append('%s%s px%s est%d/渲%d' % (n, ('『' + tb['first'][:10] + '』'),
                                                      px(tb), tb['est'], tb['render_lines']))
        if 'shape_box' in v:
            sb = v['shape_box']
            desc.append('shape px[%s,%s,%s,%s]' % (sb[0] * 2, sb[1] * 2,
                                                   (sb[0] + sb[2]) * 2, (sb[1] + sb[3]) * 2))
        print('  %-22s %s' % (v['rule'], '  |  '.join(desc) or v['el']))
