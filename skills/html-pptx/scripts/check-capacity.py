#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成侧容量门禁（三形态 C5a + C5c 两闸对齐）：HTML deck 交付时就是
"PPT 度量装得下、几何摆得开"的。

用法：python3 scripts/check-capacity.py <deck/index.html> [--json out.json]

与既有闸的分工：check-render 管浏览器口径破版（溢出/重叠/字号档）；
本闸管 PPT 口径容量 + 几何；certify-pptx 管产物数学正确——本闸第二层
（预认证）与 certify 共用同一规则实现（certify_elements）：快照经
plan_fonts/apply_layout 定型后构造与 build_pptx 同构的 SlideElements
模型，跑 R1/R2/R3/R4/R4b/R4c 全规则。生成侧过闸 ⇒ 导出认证第一轮
即净，修复环零介入，页级降级零发生。

两层检查：
  层 A 容量视图（生成语言、指名容器）：
    1. 水平：HTML 单行叶的 PPT 不换行总宽 > 容器净宽；
    2. 垂直：容器内文本叶按 PPT 口径贪心换行（逐字 advance + 混排边界
       +1em/对 + CJK 随处可断 + 拉丁词界）的行簇墨水总高 > 容器净高；
    3. 净距：文本叶渲染盒距容器边框 <4px。
  层 B 预认证（certify 同数学、指名元素）：逐叶框模型——换行宽度 =
  叶框净宽（渲染宽 ×1.02，单行 wrap=none 框宽 = 最坏墨水 ×1.08/1.15）、
  逐渲染行 est_lines（0.97 容量折扣）、lnSpc 校准、基线补偿，墨水盒
  两两相碰/形状骑缝/压字/净距全量预演。

贪心换行是估算不是渲染——口径取保守上界（宁可多算一行：行宽距净宽 ≤2px
即断行）。输出逐页违规清单（文本前 12 字 + 需求值 vs 可用值）。
非零退出 = 有超限。幂等。
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    'export_pptx_editable', os.path.join(HERE, 'export-pptx-editable.py'))
_edx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_edx)   # 复用 RenderSession/parse_font_family/fc_match

_spec2 = importlib.util.spec_from_file_location(
    'pptx_text_metrics', os.path.join(HERE, 'pptx_text_metrics.py'))
_metrics = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(_metrics)

parse_font_family = _edx.parse_font_family

MARGIN_PX = 4.0          # 净距硬要求
EDGE_PX = 2.0            # 换行保守余量：行宽距净宽 ≤2px 即断行

# 快照 JS：容器（形状启发式同 L2）+ 文本叶（含父链容器归属）
SNAPSHOT_JS = r"""
() => {
  const out = {pages: []};
  function transparent(c){
    if (!c || c === 'transparent') return true;
    const m = /^rgba\(([^)]+)\)$/.exec(c.trim());
    return !!m && parseFloat(m[1].split(',')[3]) === 0;
  }
  function visible(el){
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) <= 0.02) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  function isContainer(el){
    if (!visible(el)) return false;
    const cs = getComputedStyle(el);
    const bg = !transparent(cs.backgroundColor);
    let border = false;
    for (const side of ['Top', 'Right', 'Bottom', 'Left']){
      const st = cs['border' + side + 'Style'];
      if (st && st !== 'none' && st !== 'hidden'
          && parseFloat(cs['border' + side + 'Width']) > 0
          && !transparent(cs['border' + side + 'Color'])) border = true;
    }
    const radius = parseFloat(cs.borderTopLeftRadius) || 0;
    return bg || border || radius > 0;
  }
  const slides = Array.from(document.querySelectorAll('section.slide'));
  for (const slide of slides){
    const scale = parseFloat(document.documentElement.style.getPropertyValue('--slide-scale')) || 1;
    const sr = slide.getBoundingClientRect();
    const cv = (r) => ({left: (r.left - sr.left) / scale, top: (r.top - sr.top) / scale,
                        width: r.width / scale, height: r.height / scale});
    const page = {slide_id: slide.getAttribute('data-slide-id') || '', containers: [], leaves: []};
    const containerIdx = new Map();
    Array.from(slide.querySelectorAll('*')).forEach(el => {
      if (el.closest('.baked-source')) return;
      if (el.hasAttribute('data-editable') || el.closest('svg')) return;
      if (isContainer(el)){
        const cs = getComputedStyle(el);
        containerIdx.set(el, page.containers.length);
        page.containers.push({
          rect: cv(el.getBoundingClientRect()),
          pad: {l: parseFloat(cs.paddingLeft) || 0, r: parseFloat(cs.paddingRight) || 0,
                t: parseFloat(cs.paddingTop) || 0, b: parseFloat(cs.paddingBottom) || 0},
          hint: (el.className || '').toString().split(' ')[0] || el.tagName.toLowerCase(),
        });
      }
    });
    Array.from(slide.querySelectorAll('[data-editable]')).forEach(el => {
      if (el.closest('.baked-source') || !visible(el)) return;
      const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (!text) return;
      // 父链最近的容器
      let ci = -1;
      let n = el.parentElement;
      while (n && n !== slide){
        if (containerIdx.has(n)){ ci = containerIdx.get(n); break; }
        n = n.parentElement;
      }
      const cs = getComputedStyle(el);
      page.leaves.push({
        text, rect: cv(el.getBoundingClientRect()),
        fontFamily: cs.fontFamily, fontSizePx: parseFloat(cs.fontSize),
        bold: parseInt(cs.fontWeight, 10) >= 600,
        lineHeightPx: parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2,
        letterSpacingPx: cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing) || 0,
        container: ci,
      });
    });
    out.pages.push(page);
  }
  return out;
}
"""


def tokenize(text):
    """贪心换行 token 流：CJK/全角逐字可断；拉丁数字按词（空格为界），
    超长词可硬断（PPT wrap 行为）。返回 [(text, is_latin_word)]。"""
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == ' ':
            tokens.append((' ', False))
            i += 1
            continue
        if _metrics._cls(ch) == 'latin':
            j = i
            while j < len(text) and _metrics._cls(text[j]) == 'latin' and text[j] != ' ':
                j += 1
            tokens.append((text[i:j], True))
            i = j
        else:
            tokens.append((ch, False))
            i += 1
    return tokens


def greedy_wrap(text, net_w, sz_px, cands, latin, ea, spc_px=0.0, bold=False):
    """PPT 口径贪心换行模拟（保守上界：行宽距净宽 ≤2px 即断行）。
    返回行数。混排边界项在 token 拼接处计入。"""
    tokens = tokenize(text)
    lines = 1
    cur = 0.0
    prev_cls = None
    for tok, is_word in tokens:
        if not tok:
            continue
        w = cands.width_px_for(tok, sz_px, latin, ea, spc_px, bold, with_boundary=False)
        # 拼接边界（含跨 token）
        first_cls = _metrics._cls(tok[0])
        boundary = 0.0
        if prev_cls is not None and prev_cls != first_cls:
            boundary = _metrics.MIXED_BOUNDARY_EM * sz_px
        need = cur + boundary + w
        if prev_cls is not None and need > net_w - EDGE_PX:
            # 断行；超长单词硬断（按剩余宽度能塞多少塞多少的保守上界：直接整词新行）
            lines += 1
            cur = w
        else:
            cur = need
        prev_cls = _metrics._cls(tok[-1])
        # 单词超整行宽 → 硬断多行
        while cur > net_w - EDGE_PX:
            lines += 1
            cur = cur - net_w   # 近似：折入下一行继续
    return lines


RULE_LABELS_B = {                            # 层 B：certify 规则 → 生成侧中文标签
    'R1-h-overflow': '水平超限·PPT', 'R2-v-overflow': '垂直超限·PPT',
    'R3-line-crash': '行内叠字', 'R4-ink-collision': '文本相碰',
    'R4-shape-covers-text': '形状压字', 'R4b-margin-tight': '净距·PPT',
    'R4c-edge-straddle': '骑缝',
}
LAYER_A_RULES = ('水平超限', '垂直超限', '净距')


def check_deck(deck_html):
    """返回 {'pages': [...], 'violations': [...], 'containers_over': n}。"""
    work = tempfile.mkdtemp(prefix='pptx-capacity-')
    try:
        with _edx.RenderSession(deck_html) as sess:
            snap = sess.page.evaluate(SNAPSHOT_JS)          # 层 A：容器视图
            snap_b, deck_lang = sess.snapshot()             # 层 B：导出同构快照
        # 候选字体集（与导出同口径：三栈映射名 + deck fonts/ 内嵌 + 雅黑/宋体默认）
        declared = []
        for role in ('display', 'body', 'mono'):
            st = (snap_b.get('fontStacks') or {}).get(role)
            if st:
                f = parse_font_family(st, deck_lang)
                declared += [f['latin'], f['ea']]
        for pg in snap['pages']:                    # 层 A 叶的族名也并入声明
            for lf in pg['leaves']:
                f = parse_font_family(lf['fontFamily'], None)
                declared += [f['latin'], f['ea']]
        deck_dir = os.path.dirname(os.path.abspath(deck_html))
        fonts_dir = os.path.join(deck_dir, 'fonts')
        embeds = [os.path.join(fonts_dir, f) for f in sorted(os.listdir(fonts_dir))
                  if f.lower().endswith(('.ttf', '.otf'))] if os.path.isdir(fonts_dir) else []
        cands = _metrics.CandidateSet.build(sorted(set(declared)), embeds)

        violations = []
        for pg in snap['pages']:
            sid = pg['slide_id']
            # 页级容器（无归属文本叶）
            page_container = {'rect': {'left': 0, 'top': 0, 'width': 1920, 'height': 1080},
                              'pad': {'l': 0, 'r': 0, 't': 0, 'b': 0}, 'hint': 'page'}
            containers = pg['containers'] + [page_container]
            for ci, cont in enumerate(containers):
                r = cont['rect']
                pad = cont['pad']
                net_l = r['left'] + pad['l']
                net_t = r['top'] + pad['t']
                net_w = r['width'] - pad['l'] - pad['r']
                net_h = r['height'] - pad['t'] - pad['b']
                leaves = [lf for lf in pg['leaves']
                          if (lf['container'] if ci < len(pg['containers']) else -1) == ci
                          or (ci == len(pg['containers']) and lf['container'] == -1)]
                if not leaves:
                    continue
                # 行簇模型：并排叶不叠高度——按 y 带聚类，带内取最大墨水高，
                # 带间取真实间距（横向并排的叶共享纵向空间）
                row_bands = []
                for lf in sorted(leaves, key=lambda l: l['rect']['top']):
                    f = parse_font_family(lf['fontFamily'], None)
                    sz = lf['fontSizePx']
                    n_lines = greedy_wrap(lf['text'], net_w, sz, cands, f['latin'], f['ea'],
                                          lf['letterSpacingPx'], lf['bold'])
                    nat = cands.natural_factor(f['latin'], f['ea'])
                    ink_h = n_lines * nat * sz
                    lf['_ink_h'] = ink_h
                    placed = False
                    for band in row_bands:
                        if abs(band['top'] - lf['rect']['top']) <= max(ink_h, band['ink']) * 0.4:
                            band['ink'] = max(band['ink'], ink_h)
                            band['leaves'].append(lf)
                            placed = True
                            break
                    if not placed:
                        row_bands.append({'top': lf['rect']['top'], 'ink': ink_h,
                                          'bottom': lf['rect']['top'] + lf['rect']['height'],
                                          'leaves': [lf]})
                total_ink = 0.0
                prev_bottom = None
                for band in row_bands:
                    if prev_bottom is not None:
                        total_ink += max(0.0, band['top'] - prev_bottom)
                    total_ink += band['ink']
                    prev_bottom = band['top'] + band['ink']
                for lf in leaves:
                    # 水平：HTML 单行展示的叶，PPT 不换行总宽 > 净宽 →
                    # PPT 里会换行/溢出（多行叶的宽度问题归垂直规则管）
                    full_w = cands.width_px_for(lf['text'], sz, f['latin'], f['ea'],
                                                lf['letterSpacingPx'], lf['bold'])
                    nat1 = cands.natural_factor(f['latin'], f['ea'])
                    visually_single = lf['rect']['height'] <= nat1 * sz * 1.6
                    if visually_single and full_w > net_w:
                        violations.append({'page': sid, 'container': cont['hint'],
                                           'rule': '水平超限', 'text': lf['text'][:12],
                                           'need_px': round(full_w, 1),
                                           'avail_px': round(net_w, 1)})
                    # 净距（叶完全在容器内时）
                    lr = lf['rect']
                    inside = (lr['left'] >= net_l - 0.5 and lr['top'] >= net_t - 0.5
                              and lr['left'] + lr['width'] <= net_l + net_w + 0.5
                              and lr['top'] + lr['height'] <= net_t + net_h + 0.5)
                    furniture = bool(lf['rect'] and cont['hint'] in ('masthead', 'mastfoot'))
                    if inside and ci < len(pg['containers']) and not furniture:
                        # 净距从容器边框量——padding 本来就是净距的组成部分
                        gaps = [lr['left'] - r['left'], lr['top'] - r['top'],
                                r['left'] + r['width'] - (lr['left'] + lr['width']),
                                r['top'] + r['height'] - (lr['top'] + lr['height'])]
                        if min(gaps) < MARGIN_PX:
                            violations.append({'page': sid, 'container': cont['hint'],
                                               'rule': '净距', 'text': lf['text'][:12],
                                               'need_px': MARGIN_PX,
                                               'avail_px': round(min(gaps), 1)})
                # 垂直：PPT 墨水总高 vs 净高（刊头家具豁免——页缘空白吸收，
                # 文字越界无处可碰；与净距豁免同口径）
                furniture = cont['hint'] in ('masthead', 'mastfoot')
                if total_ink > net_h and ci < len(pg['containers']) and not furniture:
                    violations.append({'page': sid, 'container': cont['hint'],
                                       'rule': '垂直超限',
                                       'text': '%d 叶' % len(leaves),
                                       'need_px': round(total_ink, 1),
                                       'avail_px': round(net_h, 1)})
        containers_over = len({(v['page'], v['container']) for v in violations
                               if v['rule'] == '垂直超限'})

        # ---- 层 B：几何预认证（certify 同数学——快照经布局定型后构造
        # build_pptx 同构模型，跑 R1/R2/R3/R4/R4b/R4c 全规则）----
        fplan = {'cands': cands, 'margin_mode': 'normal', 'notes': [], 'embeds': []}
        _edx.apply_layout(snap_b, fplan)
        for pi, pg in enumerate(snap_b['pages'], 1):
            se = _edx.slide_elements_from_snap(pg, deck_lang)
            for v in _edx._certify_mod.certify_elements([se], cands):
                rec = {'page': pg['slide_id'], 'container': '预认证',
                       'rule': RULE_LABELS_B.get(v['rule'], v['rule']),
                       'text': (v.get('text') or '')[:12]}
                if v['rule'] == 'R1-h-overflow':
                    rec['need_px'] = round(v['ink_w_pt'] * 2, 1)
                    rec['avail_px'] = round(v['net_w_pt'] * 2, 1)
                elif v['rule'] == 'R2-v-overflow':
                    rec['need_px'] = round(v['need_h_pt'] * 2, 1)
                    rec['avail_px'] = round(v['box_h_pt'] * 2, 1)
                elif v['rule'] == 'R3-line-crash':
                    rec['need_px'] = round(v['natural_pt'] * 2, 1)
                    rec['avail_px'] = round(v['lnSpc_pt'] * 2, 1)
                elif v['rule'] == 'R4b-margin-tight':
                    rec['need_px'] = MARGIN_PX
                    rec['avail_px'] = round(v['min_gap_px'], 1)
                else:                       # R4 相碰/压字/骑缝：报相交面积与对象
                    rec['need_px'] = round(v.get('inter_pt2', 0), 1)
                    rec['avail_px'] = 0
                rec['el'] = v.get('el', '')
                violations.append(rec)
        cands.close()
        return {'pages': len(snap['pages']), 'violations': violations,
                'containers_over': containers_over}
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description='生成侧容量门禁（PPT 度量口径）')
    ap.add_argument('deck', help='deck 的 index.html 路径')
    ap.add_argument('--json', help='违规清单 JSON 输出路径')
    args = ap.parse_args()
    rep = check_deck(args.deck)
    for v in rep['violations']:
        line = ('超限  %-24s %-14s %-10s 需求 %.1fpx vs 可用 %.1fpx  %r'
                % (v['page'], v['container'], v['rule'],
                   v['need_px'], v['avail_px'], v['text']))
        if v.get('el'):
            line += '  ⟨%s⟩' % v['el']
        print(line)
    n_a = len([v for v in rep['violations'] if v['rule'] in LAYER_A_RULES])
    n_b = len(rep['violations']) - n_a
    print('容量认证：%s——%d 页，违规 %d 项（容量视图 %d / 预认证 %d），需重排容器 %d 个'
          % ('PASS' if not rep['violations'] else 'FAIL',
             rep['pages'], len(rep['violations']), n_a, n_b, rep['containers_over']))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print('清单已写入：%s' % args.json, file=sys.stderr)
    return 0 if not rep['violations'] else 1


if __name__ == '__main__':
    sys.exit(main())
