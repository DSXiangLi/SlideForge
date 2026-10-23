#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPTX 版式数学认证器（子技能 C · F4′——修 R4 门禁双盲）。

写入后读结构化 XML 做纯计算认证（不渲染）——视觉 QA 在重叠/边距场景不可信赖
（0928 二次诊断实证：LO 回验对字体未生效与文本重叠双盲）。

用法：
  python3 scripts/certify-pptx.py <deck.pptx> [--fonts-dir <dir>] [--json out.json]
  python3 scripts/certify-pptx.py --self-test

四条认证规则（候选字体集上取最坏值，集合内数学保证）：
  R1 逐行墨水宽：Σ(字形 advance×字号×fontScale + spc) ≤ 框内净宽
     （wrap=none 硬要求；wrap=square 估算重排行数喂给 R2）；
  R2 逐块墨水高：Σ(段落估算行数 × lnSpc_eff) + 上下内边距 ≤ 框高；
  R3 行内不叠字：lnSpc_eff ≥ 候选集最坏自然行高 × 字号（逐段）；
  R4 页内墨水盒两两相交 = 0：墨水盒 = 框 left/top + Σ行 lnSpc_eff（高）×
     各行最坏墨水宽+左右内边距（宽）——余量区伸入空白不算冲突；
     文字-文字严格；文字-背景形状按 z 序在下豁免；位图（pic）豁免；
  R4b 文字墨水被形状完全包含时，与容器四边净距 ≥4px（2pt）；
  R4c 文字墨水与下层形状**部分相交（骑缝/压边线）**即违规——骑缝是
     "修复环挪位把文本挪到卡片缝上"的漏洞位（0928 四次诊断实锤）。

lnSpc 口径：spcPct 按候选字体各自自然行高换算取最坏；spcPts 为绝对磅值；
无 lnSpc = 单倍（自然行高）。fontScale（normAutofit）乘进字号。

退出码：全过 0；任一违规 1。--json 落结构化违规清单。
"""
import argparse
import json
import os
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    'pptx_text_metrics', os.path.join(HERE, 'pptx_text_metrics.py'))
_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_metrics)

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
EMU_PT = 12700.0
PT_PER_PX = 0.5
MARGIN_PT = 2.0          # 4px 画布 = 2pt
TOL_PT = 0.75            # 取整/换算容差


def _pt(emu):
    return int(emu) / EMU_PT


class SlideElements:
    def __init__(self):
        self.texts = []    # {name,x,y,w,h,wrap,lIns..,paras,fontScale,z,first}
        self.shapes = []   # {name,x,y,w,h,z}
        self.z = 0

    def walk(self, node, dx=0.0, dy=0.0, sx=1.0, sy=1.0):
        for child in node:
            tag = child.tag.rsplit('}', 1)[-1]
            if tag == 'grpSp':
                self._group(child, dx, dy, sx, sy)
            elif tag == 'sp':
                self._sp(child, dx, dy, sx, sy)
            # pic/graphicFrame：位图豁免，不参与

    def _group(self, grp, dx, dy, sx, sy):
        xfrm = grp.find('.//a:xfrm', NS)
        if xfrm is None:
            return
        off, ext = xfrm.find('a:off', NS), xfrm.find('a:ext', NS)
        choff, chext = xfrm.find('a:chOff', NS), xfrm.find('a:chExt', NS)
        if off is None or ext is None or choff is None or chext is None:
            return
        nsx = _pt(ext.get('cx')) / max(_pt(chext.get('cx')), 1e-6)
        nsy = _pt(ext.get('cy')) / max(_pt(chext.get('cy')), 1e-6)
        ndx = _pt(off.get('x')) - _pt(choff.get('x')) * nsx
        ndy = _pt(off.get('y')) - _pt(choff.get('y')) * nsy
        for child in grp:
            tag = child.tag.rsplit('}', 1)[-1]
            if tag == 'grpSp':
                self._group(child, ndx, ndy, nsx, nsy)
            elif tag == 'sp':
                self._sp(child, ndx, ndy, nsx, nsy)

    def _sp(self, sp, dx, dy, sx, sy):
        xfrm = sp.find('.//a:xfrm', NS)
        if xfrm is None:
            return
        off, ext = xfrm.find('a:off', NS), xfrm.find('a:ext', NS)
        if off is None or ext is None:
            return
        x = dx + _pt(off.get('x')) * sx
        y = dy + _pt(off.get('y')) * sy
        w = _pt(ext.get('cx')) * sx
        h = _pt(ext.get('cy')) * sy
        nv = sp.find('.//p:cNvPr', NS)
        name = nv.get('name') if nv is not None else ''
        self.z += 1
        txts = sp.findall('.//a:t', NS)
        if not txts:
            # 圆形/环形（roundRect adj≥0.45 且近等边）：文字居中压环边是设计
            # 常态（d1 同心圆/圆环徽章实测），R4c 豁免
            geom = sp.find('.//a:prstGeom', NS)
            roundish = False
            if geom is not None and geom.get('prst') == 'roundRect':
                adj = geom.find('.//a:gd', NS)
                if adj is not None and adj.get('fmla', '').startswith('val'):
                    try:
                        roundish = float(adj.get('fmla').split()[1]) >= 0.45 * 100000                             and abs(w - h) <= max(w, h) * 0.08
                    except (ValueError, IndexError):
                        pass
            self.shapes.append({'name': name, 'x': x, 'y': y, 'w': w, 'h': h,
                                'z': self.z, 'roundish': roundish})
            return
        body = sp.find('.//a:bodyPr', NS)
        wrap = body.get('wrap') if body is not None else None
        font_scale = 1.0
        na = body.find('a:normAutofit', NS) if body is not None else None
        if na is not None and na.get('fontScale'):
            font_scale = int(na.get('fontScale')) / 100000.0
        insets = {k: (int(body.get(k)) / EMU_PT if body is not None and body.get(k)
                      else (91440 / EMU_PT if k in ('lIns', 'rIns') else 45720 / EMU_PT))
                  for k in ('lIns', 'rIns', 'tIns', 'bIns')}
        paras = []
        for para in sp.findall('.//a:p', NS):
            ln = para.find('.//a:pPr/a:lnSpc', NS)
            lnspc = None
            if ln is not None:
                pct = ln.find('a:spcPct', NS)
                pts = ln.find('a:spcPts', NS)
                if pct is not None:
                    lnspc = ('pct', int(pct.get('val')) / 100000.0)
                elif pts is not None:
                    lnspc = ('pts', int(pts.get('val')) / 100.0)
            runs = []
            for r in para.findall('a:r', NS):
                t = r.find('a:t', NS)
                rpr = r.find('a:rPr', NS)
                lat = rpr.find('a:latin', NS) if rpr is not None else None
                eaf = rpr.find('a:ea', NS) if rpr is not None else None
                runs.append({
                    'text': t.text or '' if t is not None else '',
                    'sz': (int(rpr.get('sz')) / 100.0) if rpr is not None and rpr.get('sz') else 18.0,
                    'spc': (int(rpr.get('spc')) / 100.0) if rpr is not None and rpr.get('spc') else 0.0,
                    'bold': rpr is not None and rpr.get('b') == '1',
                    'latin': lat.get('typeface') if lat is not None else None,
                    'ea': eaf.get('typeface') if eaf is not None else None,
                })
            paras.append({'lnspc': lnspc, 'runs': runs})
        self.texts.append({'name': name, 'x': x, 'y': y, 'w': w, 'h': h, 'wrap': wrap,
                           'insets': insets, 'paras': paras, 'fontScale': font_scale,
                           'z': self.z,
                           'first': ''.join(r['text'] for p in paras for r in p['runs'])[:12]})


def certify_elements(pages, cands):
    """对 SlideElements 列表（页序）跑全部认证规则——certify(pptx) 的
    XML 路径与 check-capacity 的 HTML 快照路径共用同一数学的落点。"""
    violations = []
    for pi, se in enumerate(pages, 1):
        violations += _certify_slide(pi, se, cands)
    return violations


def certify(pptx_path, fonts_dir=None, extra_names=('Microsoft YaHei', 'SimSun')):
    """返回 {'ok': bool, 'violations': [...], 'candidates': [...], 'pages': N}。"""
    work = tempfile.mkdtemp(prefix='pptx-certify-')
    embed_files = []
    try:
        z = zipfile.ZipFile(pptx_path)
        # 内嵌字体拆出（真实度量）
        for n in z.namelist():
            if n.startswith('ppt/fonts/') and n.endswith('.fntdata'):
                fp = os.path.join(work, os.path.basename(n) + '.ttf')
                with open(fp, 'wb') as f:
                    f.write(z.read(n))
                embed_files.append(fp)
        if fonts_dir and os.path.isdir(fonts_dir):
            embed_files += [os.path.join(fonts_dir, f) for f in sorted(os.listdir(fonts_dir))
                            if f.lower().endswith(('.ttf', '.otf'))]
        # 声明族名
        declared = set()
        slide_names = sorted([n for n in z.namelist()
                              if re.match(r'ppt/slides/slide\d+\.xml$', n)],
                             key=lambda n: int(re.search(r'(\d+)', n).group(1)))
        for n in slide_names:
            declared.update(re.findall(r'<a:(?:latin|ea) typeface="([^"]+)"',
                                       z.read(n).decode('utf-8')))
        cands = _metrics.CandidateSet.build(sorted(declared), embed_files,
                                            extra_names=extra_names)
        violations = []
        pages = []
        for pi, n in enumerate(slide_names, 1):
            root = ET.fromstring(z.read(n))
            se = SlideElements()
            se.walk(root.find('.//p:cSld/p:spTree', NS))
            pages.append(se)
        violations = certify_elements(pages, cands)
        cands.close()
        return {'ok': not violations, 'violations': violations,
                'candidates': cands.describe(), 'pages': len(slide_names)}
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def _certify_slide(pi, se, cands):
    v = []
    boxes = []   # (kind, idx, inkbox)
    for ti, t in enumerate(se.texts):
        net_w = t['w'] - t['insets']['lIns'] - t['insets']['rIns']
        need_h = t['insets']['tIns'] + t['insets']['bIns']
        ink_w_max = 0.0
        ln_first = None       # 首段 lnSpc_eff
        ln_last = None        # 末段 lnSpc_eff
        sz_max = 0.0
        n_lines_total = 0
        for para in t['paras']:
            ln_worst = 0.0
            nat_worst = 0.0
            ink_w = 0.0
            sz_max_para = max((run['sz'] for run in para['runs']), default=0.0)
            for run in para['runs']:
                sz = run['sz'] * t['fontScale']
                ink_w += cands.width_pt_for(run['text'], sz, run['latin'], run['ea'],
                                            run['spc'], run['bold'], with_boundary=False)
                nat_worst = max(nat_worst,
                                cands.natural_factor(run['latin'], run['ea']) * sz)
            # OOXML 混排自动间距：边界按段落全文计一次（覆盖跨 run 边界），
            # 磅值随最大字号（保守）
            ink_w += _metrics.mixed_boundaries(
                ''.join(r['text'] for r in para['runs'])) * _metrics.MIXED_BOUNDARY_EM \
                * sz_max_para * t['fontScale']
            # lnSpc_eff 逐候选取最坏
            kind_val = para['lnspc']
            if kind_val is None:
                ln_worst = nat_worst
            elif kind_val[0] == 'pct':
                ln_worst = kind_val[1] * nat_worst
            else:
                ln_worst = kind_val[1]
            # R3 行内不叠字
            if ln_worst + 0.05 < nat_worst:
                v.append({'page': pi, 'el': t['name'], 'text': t['first'], 'rule': 'R3-line-crash',
                          'lnSpc_pt': round(ln_worst, 2), 'natural_pt': round(nat_worst, 2)})
            if t['wrap'] == 'none':
                # R1 单行水平溢出硬要求
                if ink_w > net_w + TOL_PT:
                    v.append({'page': pi, 'el': t['name'], 'text': t['first'],
                              'rule': 'R1-h-overflow', 'ink_w_pt': round(ink_w, 1),
                              'net_w_pt': round(net_w, 1)})
                est_lines = 1
                line_w = ink_w
            else:
                # 逻辑段贪心换行（与导出布局/生成侧门禁同一函数：逐 run 分词、
                # CJK 逐字可断、拉丁词界、混排边界 +0.25em，无容量折扣——
                # 0929 受控实验：模型与 LO 逐字吻合，真实引擎按 advance 精确
                # 换行。逐渲染行 a:p 已改为逻辑段 a:p，Chromium 紧凑断行不再
                # 锁死 PPT 重排）
                est_lines, line_w = _metrics.greedy_wrap_lines(
                    cands, [{'text': r['text'], 'sz': r['sz'], 'latin': r['latin'],
                             'ea': r['ea'], 'spc': r['spc'], 'bold': r['bold']}
                            for r in para['runs']], net_w, scale=t['fontScale'])
            need_h += est_lines * ln_worst
            n_lines_total += est_lines
            ln_last = ln_worst
            if ln_first is None:
                ln_first = ln_worst
            ink_w_max = max(ink_w_max, min(line_w, net_w) if t['wrap'] != 'none' else ink_w)
        # R2 垂直溢出
        if need_h > t['h'] + TOL_PT:
            v.append({'page': pi, 'el': t['name'], 'text': t['first'], 'rule': 'R2-v-overflow',
                      'need_h_pt': round(need_h, 1), 'box_h_pt': round(t['h'], 1)})
        # 墨水盒（F1 口径，修正：末行只占墨迹 em 高而非整自然行高——
        # 单行/标签的 lineGap 是排版储备不是墨迹，否则把留白误报成碰撞）
        sz_max = 0.0
        em_worst = 0.0
        for para in t['paras']:
            for r in para['runs']:
                sz_max = max(sz_max, r['sz'])
                em_worst = max(em_worst, cands.em_factor(r['latin'], r['ea']))
        em_h = em_worst * sz_max * t['fontScale']
        ink_h = (need_h - (ln_last or 0)) + em_h if n_lines_total else need_h
        boxes.append(('text', ti, {'l': t['x'], 't': t['y'],
                                   'r': t['x'] + min(ink_w_max + t['insets']['lIns']
                                                     + t['insets']['rIns'], t['w']),
                                   'b': t['y'] + ink_h}))
    for si, sh in enumerate(se.shapes):
        boxes.append(('shape', si, {'l': sh['x'], 't': sh['y'],
                                    'r': sh['x'] + sh['w'], 'b': sh['y'] + sh['h']}))
    # R4 相交（文字-文字严格；z 序在下的形状豁免；文字压在上层形状上 = 违规）
    text_boxes = {i: b for k, i, b in boxes if k == 'text'}
    for i in text_boxes:
        for j in text_boxes:
            if j <= i:
                continue
            inter = _inter(text_boxes[i], text_boxes[j])
            if inter > 0.5:
                v.append({'page': pi, 'el': se.texts[i]['name'] + ' × ' + se.texts[j]['name'],
                          'text': se.texts[i]['first'] + '‖' + se.texts[j]['first'],
                          'rule': 'R4-ink-collision', 'inter_pt2': round(inter, 1)})
        # 形状在文字之上且相碰 → 压字违规
    for si, sh in enumerate(se.shapes):
        for ti, tb in text_boxes.items():
            if sh['z'] > se.texts[ti]['z']:
                inter = _inter({'l': sh['x'], 't': sh['y'], 'r': sh['x'] + sh['w'],
                                'b': sh['y'] + sh['h']}, tb)
                if inter > 0.5:
                    v.append({'page': pi, 'el': sh['name'] + ' 压 ' + se.texts[ti]['name'],
                              'text': se.texts[ti]['first'], 'rule': 'R4-shape-covers-text',
                              'inter_pt2': round(inter, 1),
                              'shape_box': [round(sh['x'], 1), round(sh['y'], 1),
                                            round(sh['w'], 1), round(sh['h'], 1)]})
    # R4b/R4c 文字墨水 vs 一切下层形状的边缘关系：
    #   完全包含 → 四边净距 ≥4px（R4b）；
    #   部分相交（骑缝/压边线）→ 违规（R4c，规则漏洞修补——此前只查包含）；
    #   全页背景底（覆盖 ≥95% 页面积）只走包含分支，不产生骑缝误报
    page_area = 960.0 * 540.0
    for ti, tb in text_boxes.items():
        t = se.texts[ti]
        for sh in se.shapes:
            if sh['z'] >= t['z']:
                continue
            sbox = {'l': sh['x'], 't': sh['y'], 'r': sh['x'] + sh['w'], 'b': sh['y'] + sh['h']}
            inter = _inter(tb, sbox)
            if inter <= 0.5:
                continue
            if sh.get('roundish'):
                continue   # 环/圆形豁免 R4c（文字居中压环边是设计常态）
            if sh['w'] * sh['h'] >= page_area * 0.95:
                inside = True   # 全页背景底必然包含
            else:
                inside = (sbox['l'] - 0.5 <= tb['l'] and sbox['t'] - 0.5 <= tb['t']
                          and sbox['r'] + 0.5 >= tb['r'] and sbox['b'] + 0.5 >= tb['b'])
            if inside:
                gaps = [tb['l'] - sbox['l'], tb['t'] - sbox['t'],
                        sbox['r'] - tb['r'], sbox['b'] - tb['b']]
                if min(gaps) < MARGIN_PT - 0.05:
                    v.append({'page': pi, 'el': t['name'], 'text': t['first'],
                              'rule': 'R4b-margin-tight',
                              'min_gap_px': round(min(gaps) / PT_PER_PX, 1)})
            else:
                v.append({'page': pi, 'el': t['name'], 'text': t['first'],
                          'rule': 'R4c-edge-straddle',
                          'inter_pt2': round(inter, 1),
                          'shape_box': [round(sh['x'], 1), round(sh['y'], 1),
                                        round(sh['w'], 1), round(sh['h'], 1)]})
    return v


def _inter(a, b):
    w = min(a['r'], b['r']) - max(a['l'], b['l'])
    h = min(a['b'], b['b']) - max(a['t'], b['t'])
    return max(0.0, w) * max(0.0, h)


def main():
    ap = argparse.ArgumentParser(description='PPTX 版式数学认证器（F4′）')
    ap.add_argument('pptx', nargs='?', help='deck.pptx 路径')
    ap.add_argument('--fonts-dir', help='额外候选字体目录（deck fonts/）')
    ap.add_argument('--json', help='结构化违规清单输出路径')
    args = ap.parse_args()
    if not args.pptx:
        ap.error('缺 pptx 路径')
    rep = certify(args.pptx, args.fonts_dir)
    for v in rep['violations']:
        print('VIOLATION  p%-3d %-22s %-18s %s'
              % (v['page'], v['el'], v['rule'],
                 {k: v[k] for k in v if k not in ('page', 'el', 'rule', 'text')}))
    print('认证：%s——%d 页，违规 %d 项；候选：%s'
          % ('PASS' if rep['ok'] else 'FAIL', rep['pages'], len(rep['violations']),
             '、'.join(rep['candidates'])))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
