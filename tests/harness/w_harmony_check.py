#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""imagegen v2 G2/G3 验收：生图色彩一致性后置校验 + 评审 rubric 落账
（docs/design/imagegen-v2.md §3-G2/G3）。

用法：python3 tests/harness/w_harmony_check.py

命名偏差：设计文档称 r_harmony_check.py，r/s/t/u/v 已被 bridge/imagegen
既有子检查占用（r_bridge/s_bridge_scale/t_imagegen/u_bridge_stability/
v_bridge_host），顺延用 w_。

fixture：tests/decks/harmony-fixture/（3 页合成 deck；assets 由同目录
gen-assets.py 纯 stdlib 生成——tokens.png 纯 token 色应全过、foreign.png
纯品红族无关色应触发 A+B、mixed.png 挂在烙入页 50% accent+50% 品红应只
触发 A，借它同时验证满幅烙入页的 --paper/--ink 豁免）。全程合成图，不
依赖付费生图与网络（仅复用项目既有 Playwright Chromium 渲染通道）。

检查项（全部硬断言）：
  ① 基础运行：exit 0，报告 3 图、6 个可解析 token；
  ② p-token 无告警，主色板全部 ΔE00=0 精确锚定；
  ③ p-foreign 同时触发 A+B（无锚率 100%，缺 --accent/--paper/--ink），
     退出码仍 0（单图告警不阻断）；
  ④ p-mixed（满幅烙入）只触发 A——缺 --paper/--ink 因豁免不计入 B；
  ⑤ ledger 缺省时只出报告、不强行创建；
  ⑥ 预置 ledger：harmony 结论按 outputs[].file 写入对应条目，无关条目
     与其余字段不染指；
  ⑦ 阻断逻辑：构造 2/3 图双触发（≥50%）→ 退出码 1；
  ⑧ --strict：任何告警升级为阻断 → 退出码 1；
  ⑨ 幂等：同输入连跑两次，报告 JSON 逐字节一致；
  ⑩ 色彩数学自检：CIEDE2000 已知 Lab 对（Sharma 测试数据）≈2.0425、
     同色 ΔE=0；
  ⑪ adapter --rubric-json 透传（G3）：stub provider 成功生图后 ledger
     条目携带逐字 rubric；无效 rubric JSON → 非零退出 invalid_rubric。
退出码：全过 0，任一失败 1。
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARMONY = os.path.join(ROOT, 'skills/html-pptx/scripts/check-image-harmony.py')
ADAPTER = os.path.join(ROOT, 'skills/html-pptx/scripts/imagegen-adapter.py')
FIXTURE = os.path.join(ROOT, 'tests/decks/harmony-fixture')

FAILURES = []


def check(label, cond, detail=''):
    print('%s  %s%s' % ('PASS' if cond else 'FAIL', label,
                        (' — ' + detail) if (detail and not cond) else ''))
    if not cond:
        FAILURES.append(label)


def run_harmony(deck_html, *extra):
    return subprocess.run([sys.executable, HARMONY, deck_html, *extra],
                          capture_output=True, text=True)


STUB_PROVIDER = '''#!/usr/bin/env python3
# 打桩 provider：按 adapter 契约把纯色 PNG 写进 --output-dir，不产生任何费用。
import argparse, os, struct, zlib
p = argparse.ArgumentParser()
p.add_argument('--mode'); p.add_argument('--prompt-file')
p.add_argument('--output-dir', required=True)
p.add_argument('--quality'); p.add_argument('--format', default='png')
p.add_argument('--moderation'); p.add_argument('--background')
p.add_argument('--n', type=int, default=1); p.add_argument('--name', required=True)
p.add_argument('--size'); p.add_argument('--aspect-ratio'); p.add_argument('--resolution')
p.add_argument('--reference-image', action='append', default=[])
p.add_argument('--advance-model', action='store_true')
a = p.parse_args()
w, h = (int(v) for v in (a.size or '16x9').split('x'))

def chunk(typ, data):
    return (struct.pack('>I', len(data)) + typ + data +
            struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF))

raw = (b'\\x00' + b'\\x80\\x80\\x80' * w) * h
ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
blob = (b'\\x89PNG\\r\\n\\x1a\\n' + chunk(b'IHDR', ihdr) +
        chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
names = [a.name + '.png'] if a.n == 1 else ['%s_%d.png' % (a.name, i) for i in range(a.n)]
for n in names:
    with open(os.path.join(a.output_dir, n), 'wb') as f:
        f.write(blob)
'''


def main():
    tmp = tempfile.mkdtemp(prefix='pptx-harmony-check-')
    try:
        deck_dir = os.path.join(tmp, 'deck')
        shutil.copytree(FIXTURE, deck_dir)
        deck_html = os.path.join(deck_dir, 'index.html')
        ledger_path = os.path.join(deck_dir, 'imagegen-ledger.json')

        # ---------- ①②③④ 基础运行与三图判定 ----------
        r = run_harmony(deck_html)
        check('① 基础运行 exit 0（仅告警不阻断）', r.returncode == 0,
              (r.stdout + r.stderr).strip()[-300:])
        report = None
        if r.returncode == 0:
            report = json.loads(r.stdout)
            check('①b 报告覆盖 3 图、6 个 token',
                  report['summary']['total'] == 3 and len(report['tokens']) == 6,
                  repr(report['summary']))
            by_slide = {i['slide_id']: i for i in report['images']}
            token_img = by_slide.get('p-token', {})
            check('② p-token 无告警且主色全部 ΔE00=0 精确锚定',
                  token_img.get('warn') is False and
                  bool(token_img.get('palette')) and
                  all(c['delta_e'] == 0 for c in token_img['palette']),
                  repr(token_img.get('palette')))
            foreign = by_slide.get('p-foreign', {})
            check('③ p-foreign 同时触发 A+B（无锚率 100%，缺三个呼应）',
                  foreign.get('metric_a', {}).get('triggered') is True and
                  foreign.get('metric_a', {}).get('unanchored_share') == 1.0 and
                  foreign.get('metric_b', {}).get('triggered') is True and
                  sorted(foreign.get('metric_b', {}).get('missing_echo', [])) ==
                  ['--accent', '--ink', '--paper'] and
                  report['summary']['both_a_and_b'] == 1 and
                  report['summary']['blocked'] is False,
                  repr({k: foreign.get(k) for k in ('metric_a', 'metric_b')}))
            mixed = by_slide.get('p-mixed', {})
            check('④ p-mixed（满幅烙入）只触发 A：--paper/--ink 豁免生效',
                  mixed.get('metric_a', {}).get('triggered') is True and
                  mixed.get('metric_b', {}).get('triggered') is False and
                  mixed.get('full_bleed') is True,
                  repr({k: mixed.get(k) for k in ('metric_a', 'metric_b')}))

        # ---------- ⑤ ledger 缺省不创建 ----------
        check('⑤ ledger 缺省时只出报告、不强行创建',
              not os.path.exists(ledger_path))

        # ---------- ⑥ 预置 ledger 的写入/更新 ----------
        entry_ok = {
            'timestamp': '2026-10-06T00:00:00+00:00', 'status': 'success',
            'error_code': None,
            'provider': {'script': 'stub.py', 'sha256': '0' * 64},
            'request': {'name': 'foreign'}, 'billing': {'amount': 'unknown', 'currency': 'unknown'},
            'outputs': [{'file': 'foreign.png', 'media_type': 'png', 'width': 160,
                         'height': 90, 'bytes': 1, 'sha256': '0' * 64}],
        }
        entry_other = {
            'timestamp': '2026-10-05T00:00:00+00:00', 'status': 'failed',
            'error_code': 'provider_failed', 'provider': {'script': 'stub.py', 'sha256': '1' * 64},
            'request': {'name': 'gone'}, 'billing': {'amount': 'unknown', 'currency': 'unknown'},
            'outputs': [{'file': 'gone.png', 'media_type': 'png', 'width': 1,
                         'height': 1, 'bytes': 1, 'sha256': '1' * 64}],
        }
        with open(ledger_path, 'w', encoding='utf-8') as f:
            json.dump([entry_ok, entry_other], f, ensure_ascii=False)
        r = run_harmony(deck_html)
        with open(ledger_path, encoding='utf-8') as f:
            ledger = json.load(f)
        harmony = (ledger[0]['outputs'][0].get('harmony') or {})
        check('⑥ ledger 对应条目写入 harmony 结论（warn+A+B）',
              r.returncode == 0 and
              harmony.get('warn') is True and harmony.get('metric_a') is True and
              harmony.get('metric_b') is True,
              repr(harmony))
        untouched = dict(entry_other)
        check('⑥b 无关条目与其余字段不染指',
              ledger[1] == untouched and
              all(k in ledger[0] for k in entry_ok),
              repr(ledger[1]))

        # ---------- ⑦ 阻断：≥50% 图双触发 → exit 1 ----------
        blk_dir = os.path.join(tmp, 'blocked')
        shutil.copytree(FIXTURE, blk_dir)
        blk_html = os.path.join(blk_dir, 'index.html')
        with open(blk_html, encoding='utf-8') as f:
            blk_src = f.read()
        assert blk_src.count('assets/tokens.png') == 1
        with open(blk_html, 'w', encoding='utf-8') as f:
            f.write(blk_src.replace('assets/tokens.png', 'assets/foreign.png'))
        r = run_harmony(blk_html)
        blk_report = json.loads(r.stdout) if r.stdout.strip().startswith('{') else {}
        check('⑦ 2/3 图双触发（≥50%）→ 阻断 exit 1',
              r.returncode == 1 and blk_report.get('summary', {}).get('blocked') is True and
              blk_report.get('summary', {}).get('both_a_and_b') == 2,
              'rc=%d %s' % (r.returncode, repr(blk_report.get('summary'))))

        # ---------- ⑧ --strict 升级阻断 ----------
        r = run_harmony(deck_html, '--strict')
        check('⑧ --strict：存在告警即阻断 exit 1', r.returncode == 1,
              'rc=%d' % r.returncode)

        # ---------- ⑨ 幂等 ----------
        r1 = run_harmony(deck_html)
        r2 = run_harmony(deck_html)
        check('⑨ 幂等：连跑两次报告逐字节一致',
              r1.returncode == r2.returncode and r1.stdout == r2.stdout)

        # ---------- ⑩ 色彩数学自检 ----------
        spec = importlib.util.spec_from_file_location('check_image_harmony', HARMONY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        d = mod.delta_e_2000((50, 2.6772, -79.7751), (50, 0.0, -82.7485))
        check('⑩ CIEDE2000 已知 Lab 对 ≈2.0425（Sharma 测试数据）',
              abs(d - 2.0425) < 0.001, 'ΔE=%.4f' % d)
        lab = mod.srgb_to_lab((0xB4, 0x23, 0x2A))
        check('⑩b 同色 ΔE00=0 / Lab 转换自洽',
              mod.delta_e_2000(lab, lab) == 0.0)

        # ---------- ⑪ adapter --rubric-json 透传（G3） ----------
        provider = os.path.join(tmp, 'stub_provider.py')
        with open(provider, 'w', encoding='utf-8') as f:
            f.write(STUB_PROVIDER)
        rubric = {
            'rubric_version': 1,
            'dimensions': {
                'text_exact': {'score': 1, 'reason': '标题逐字正确'},
                'layout': {'score': 1, 'reason': '巨字谱系'},
                'color': {'score': 1, 'reason': 'harmony 无告警'},
                'style': {'score': 0, 'reason': '出现照片质感'},
                'no_forbidden': {'score': 1, 'reason': '无水印页码'},
            },
            'decision': 'reject', 'note': '风格不匹配，重 roll',
        }
        rubric_path = os.path.join(tmp, 'rubric.json')
        with open(rubric_path, 'w', encoding='utf-8') as f:
            json.dump(rubric, f, ensure_ascii=False)
        gen_deck = os.path.join(tmp, 'gen-deck')
        os.makedirs(gen_deck)
        r = subprocess.run([sys.executable, ADAPTER, gen_deck,
                            '--provider-script', provider,
                            '--prompt', 'rubric 透传测试', '--name', 'hero',
                            '--expected-size', '16x9', '--size', '16x9',
                            '--rubric-json', rubric_path],
                           capture_output=True, text=True)
        gen_ledger = []
        glp = os.path.join(gen_deck, 'imagegen-ledger.json')
        if os.path.isfile(glp):
            with open(glp, encoding='utf-8') as f:
                gen_ledger = json.load(f)
        check('⑪ adapter --rubric-json 逐字透传进 ledger 条目',
              r.returncode == 0 and gen_ledger and
              gen_ledger[-1].get('rubric') == rubric and
              gen_ledger[-1].get('status') == 'success',
              'rc=%d %s%s' % (r.returncode, r.stderr.strip()[-200:], repr(gen_ledger[-1:])[:300]))
        bad_rubric = os.path.join(tmp, 'bad-rubric.json')
        with open(bad_rubric, 'w', encoding='utf-8') as f:
            f.write('{not json')
        r = subprocess.run([sys.executable, ADAPTER, gen_deck,
                            '--provider-script', provider,
                            '--prompt', 'bad rubric', '--name', 'hero2',
                            '--expected-size', '16x9', '--size', '16x9',
                            '--rubric-json', bad_rubric],
                           capture_output=True, text=True)
        check('⑪b 无效 rubric JSON → 非零退出 invalid_rubric（不触发 provider 计费）',
              r.returncode != 0 and 'invalid_rubric' in r.stderr,
              'rc=%d %s' % (r.returncode, r.stderr.strip()[-200:]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('RESULT:', 'ALL PASS' if not FAILURES else '%d FAILURES: %s' % (len(FAILURES), FAILURES))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())
