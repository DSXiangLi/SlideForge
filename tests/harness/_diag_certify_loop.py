#!/usr/bin/env python3
"""C5 对齐诊断（scratch，不入回归）：复跑 cmb-retail 可编辑轨认证修复环，
逐轮记录违规的 页×规则 分布，区分修复振荡 vs 结构性不可解。
用法：python3 tests/harness/_diag_certify_loop.py"""
import collections
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECK = os.path.join(ROOT, 'tests/decks/cmb-retail/index.html')
OUT = os.path.join(ROOT, 'tests/harness/results/diag-c5/deck.pptx')
VECTOR_DIR = os.path.join(ROOT, 'tests/decks/cmb-retail/export')

spec = importlib.util.spec_from_file_location(
    'epx_editable', os.path.join(ROOT, 'skills/html-pptx/scripts/export-pptx-editable.py'))
mod = importlib.util.module_from_spec(spec)
sys.modules['epx_editable'] = mod
spec.loader.exec_module(mod)

history = []           # 逐轮 [{'round':n,'violations':[...]}]
orig_certify = mod._certify_mod.certify

def wrapped_certify(pptx_path, *a, **kw):
    cert = orig_certify(pptx_path, *a, **kw)
    history.append({'round': len(history) + 1,
                    'ok': cert['ok'],
                    'violations': [dict(v) for v in cert['violations']]})
    return cert

mod._certify_mod.certify = wrapped_certify

os.makedirs(os.path.dirname(OUT), exist_ok=True)
report = mod.run_export(DECK, OUT, vector_dir=VECTOR_DIR, verify=False)

slide_ids = [p['slide_id'] for p in report['pages']] if 'pages' in report else []
degraded = {p['slide_id'] for p in report.get('degraded_pages', [])}

print('==== 降级页 %d：%s' % (len(degraded), ' '.join(sorted(degraded))))
print('==== 逐轮违规分布（全 deck） ====')
for h in history:
    by_rule = collections.Counter(v['rule'] for v in h['violations'])
    print('round %02d ok=%s n=%d %s' % (h['round'], h['ok'], len(h['violations']), dict(by_rule)))

print('==== 降级页逐轮轨迹 ====')
# page 号 → slide_id：快照页序 = report pages 序
for sid in sorted(degraded):
    print('--- %s ---' % sid)
    for h in history:
        mine = [v for v in h['violations']
                if 0 <= v['page'] - 1 < len(report.get('pages', []))
                and report['pages'][v['page'] - 1].get('slide_id') == sid]
        if mine:
            by_rule = collections.Counter(v['rule'] for v in mine)
            print('  round %02d: %d %s' % (h['round'], len(mine), dict(by_rule)))

# 每降级页最后一轮的违规明细（证据样本）
print('==== 降级页终轮违规样本 ====')
last = history[-1] if history else {'violations': []}
for h in reversed(history):
    if h['violations']:
        last = h
        break
for sid in sorted(degraded):
    mine = [v for v in last['violations']
            if 0 <= v['page'] - 1 < len(report.get('pages', []))
            and report['pages'][v['page'] - 1].get('slide_id') == sid]
    for v in mine[:6]:
        print('  %s | %s | %s | %s | %s'
              % (sid, v['rule'], v.get('el'), (v.get('text') or '')[:24],
                 {k: v[k] for k in v if k not in ('page', 'el', 'rule', 'text')}))

with open(os.path.join(os.path.dirname(OUT), 'loop-history.json'), 'w') as f:
    json.dump({'history': history, 'degraded': sorted(degraded),
               'page_slides': [p.get('slide_id') for p in report.get('pages', [])]},
              f, ensure_ascii=False, indent=1)
print('已落盘 tests/harness/results/diag-c5/loop-history.json')
