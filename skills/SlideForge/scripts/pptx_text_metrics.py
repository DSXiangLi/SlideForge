#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
候选字体集文本度量引擎（子技能 C · F2/F4′ 共用）。

认证与布局的核心思想：**不再假设单一字体**——在声明的候选字体集合上逐项取
最坏值（宽度取最大、自然行高取最大），认证结论在集合内是数学保证。

候选解析优先级（每个声明族名）：
  1. 内嵌字体文件（pptx fntdata 拆出 / fonts/ 目录 TTF）——真实度量；
  2. fc-match 解析到的本机文件（注意：这是替换字体，仅作近似——报告标注）；
  3. ppt-master font_advances.json 宽度表（MIT，仅拉丁族；
     source/ppt-master/.../drawingml/font_advances.json）；
  4. 保守上界：CJK/全角标点 1.0em、拉丁数字 0.65em、半角标点 0.60em——
     宁可宽不可窄。

字形分类：CJK（汉字/平片假名/全角标点/谚文）与拉丁。粗体乘 1.03 合成加粗因子。
自然行高系数 = (hhea.ascent − descent + lineGap) / unitsPerEm（文件候选实测；
表/上界候选取保守值 1.50）。

直接运行本文件执行内置自测。
"""
import json
import os
import subprocess

from fontTools.ttLib import TTFont

_ADVANCES_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', '..', 'source/ppt-master/skills/ppt-master/scripts/svg_to_pptx/drawingml/font_advances.json')
# 注意：source/ 是参考资源目录，运行时存在才用；不存在则跳过表候选

FULLWIDTH_RANGES = ((0x3000, 0x303F), (0xFF00, 0xFFEF), (0x2018, 0x201D))  # 全角标点/引号

# OOXML 排版引擎（PowerPoint/LO 同款）在 CJK↔拉丁/数字边界自动插入间距——
# 0929 受控实验复测（tests/harness/results/diag-c5/spacing/）：pdftotext -bbox
# 逐词坐标显示 LO 每边界净增 ≈0.237em（14pt/18pt 两组字号、双向边界、单/双
# typeface 四种条件一致），与 Word/PPT 文献值 1/4em 吻合；取 0.25em 保守上界。
# 0928 的 1.04em 系单行反推（未分解多边界），为过度保守值——它制造幻行
# （est 行数虚增）导致 cmb-retail 13 页修复环振荡降级，0929 依实验校正。
MIXED_BOUNDARY_EM = 0.25


def mixed_boundaries(text):
    """CJK/全角 与 拉丁/半角 的相邻对数（OOXML 自动间距的作用点数）。
    空白相邻对不计——空格本身已是分隔，实测 LO 在空格两侧无附加间距
    （0929 受控实验 diag-c5/spacing/）。"""
    n = 0
    for a, b in zip(text, text[1:]):
        if a.isspace() or b.isspace():
            continue
        if _cls(a) != _cls(b):
            n += 1
    return n


def tokenize_mixed(text):
    """OOXML wrap 的 token 流：CJK/全角逐字可断；拉丁/数字按词（空格为界）；
    空格独立成 token。返回 [(text, kind)]，kind ∈ ('cjk', 'word', 'space')。"""
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            tokens.append((ch, 'space'))
            i += 1
            continue
        if _cls(ch) == 'latin':
            j = i
            while j < len(text) and _cls(text[j]) == 'latin' \
                    and not text[j].isspace():
                j += 1
            tokens.append((text[i:j], 'word'))
            i = j
        else:
            tokens.append((ch, 'cjk'))
            i += 1
    return tokens


def greedy_wrap_lines(cands, runs, net_w, scale=1.0):
    """OOXML wrap=square 贪心换行估算（候选集最坏值，无容量折扣——0929 实验：
    真实引擎按 advance 精确换行，压实密度 99.4%+，模型与 LO 逐字吻合）。
    runs: [{'text','sz','latin','ea','spc','bold'}]（长度单位自洽即可：px/pt）。
    断行规则：CJK 逐字可断；拉丁词整体不断（超净宽硬断——PPT 行为）；空格可断；
    混排边界在拼接处 +MIXED_BOUNDARY_EM×两侧最大字号（空格相邻不计）。
    返回 (行数, 最宽行墨水宽)。"""
    toks = []
    for r in runs:
        sz = (r.get('sz') or 18.0) * scale
        for tok, kind in tokenize_mixed(r.get('text') or ''):
            toks.append((tok, kind, sz, r))
    lines = 1
    cur = 0.0
    max_w = 0.0
    prev_cls = None
    prev_sz = 0.0
    for tok, kind, sz, r in toks:
        if not tok:
            continue
        w = cands.width_px_for(tok, sz, r.get('latin'), r.get('ea'),
                               r.get('spc') or 0.0, bool(r.get('bold')),
                               with_boundary=False)
        boundary = 0.0
        if prev_cls not in (None, 'space') and kind != 'space':
            tcls = 'latin' if kind == 'word' else 'cjk'
            if prev_cls != tcls:
                boundary = MIXED_BOUNDARY_EM * max(prev_sz, sz)
        need = cur + boundary + w
        if prev_cls is not None and need > net_w and net_w > 0:
            max_w = max(max_w, cur)          # 完结行墨水宽
            lines += 1                       # 断行：token 整体下行
            cur = w
            # 长词硬断：PPT 对超宽拉丁词直接断字符
            while cur > net_w:
                max_w = max(max_w, net_w)
                lines += 1
                cur -= net_w
        else:
            cur = need
        prev_cls = 'space' if kind == 'space' else ('latin' if kind == 'word' else 'cjk')
        prev_sz = sz
    max_w = max(max_w, cur)
    return lines, max_w

CJK_RANGES = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF),
              (0x3040, 0x30FF), (0x1100, 0x11FF), (0xAC00, 0xD7AF))


def _cls(ch):
    """字符类别：'cjk'（CJK+全角标点，1em 全宽）或 'latin'。"""
    cp = ord(ch)
    for a, b in CJK_RANGES + FULLWIDTH_RANGES:
        if a <= cp <= b:
            return 'cjk'
    return 'latin'


class _FileCand:
    kind = 'file'

    def __init__(self, path, note=''):
        self.path = path
        self.note = note
        try:
            font = TTFont(path)
        except Exception:
            from fontTools.ttLib import TTCollection
            font = TTCollection(path).fonts[0]
        self.font = font
        self.upm = font['head'].unitsPerEm
        h = font['hhea']
        self._natural = (h.ascent - h.descent + h.lineGap) / self.upm
        # 墨迹高度用 OS/2 typo 度量（sTypo* 是设计墨迹口径；hhea 的
        # ascent/descent 是行距储备，当墨迹用会把留白误报成碰撞——
        # Noto CJK hhea=1.48 vs typo=1.0 实测）
        if 'OS/2' in font and hasattr(font['OS/2'], 'sTypoAscender'):
            self._em = (font['OS/2'].sTypoAscender - font['OS/2'].sTypoDescender) / self.upm
        else:
            self._em = (h.ascent - h.descent) / self.upm
        self.cmap = font.getBestCmap() or {}
        self.hmtx = font['hmtx']
        self._wcache = {}

    def char_em(self, ch, bold):
        cp = ord(ch)
        if cp in self.cmap:
            gname = self.cmap[cp]
            w = self.hmtx[gname][0] / self.upm
        else:
            # 缺字形：CJK 按 1em（.notdef 通常全宽框），拉丁 0.60em 上界
            w = 1.0 if _cls(ch) == 'cjk' else 0.60
        return w * (1.03 if bold else 1.0)

    def natural(self):
        return self._natural

    def em(self):
        return self._em

    def close(self):
        self.font.close()


class _TableCand:
    """ppt-master font_advances.json 宽度表（拉丁族；CJK 恒 1em 上界）。"""
    kind = 'table'

    def __init__(self, family_key, advances, note=''):
        self.family_key = family_key
        self.adv = advances
        self.note = note

    def char_em(self, ch, bold):
        if _cls(ch) == 'cjk':
            w = 1.0
        else:
            w = self.adv.get(ch, 0.65)   # 表外拉丁字符取上界
        return w * (1.03 if bold else 1.0)

    def natural(self):
        return 1.50    # 表无行高度量 → 保守上界

    def em(self):
        return 1.17    # 典型拉丁 em 比例上界

    def close(self):
        pass


class _BoundsCand:
    """无文件无表 → 保守上界。"""
    kind = 'bounds'

    def __init__(self, note=''):
        self.note = note

    def char_em(self, ch, bold):
        w = 1.0 if _cls(ch) == 'cjk' else 0.65
        return w * (1.03 if bold else 1.0)

    def natural(self):
        return 1.50

    def em(self):
        return 1.17

    def close(self):
        pass


def _fc_match(family):
    try:
        r = subprocess.run(['fc-match', '-f', '%{file}', family],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    path = r.stdout.strip()
    if not os.path.isfile(path) or not path.lower().endswith(('.ttf', '.ttc', '.otf')):
        return None
    return path


class CandidateSet:
    """候选字体集【按声明族名分轨】：run 只会以它声明的 typeface（或匹配内嵌件）
    渲染——全局最坏会把别的轨的高字体（如 Noto Mono 1.17）误摊到正文轨。
    逐字分流：CJK/全角字符走 ea 轨、拉丁走 latin 轨（CJK 字体的拉丁字形同源，
    ea 轨内嵌件同时覆盖拉丁）。声明族名解析不到 → 该名保守上界轨。"""

    def __init__(self):
        self.by_name = {}        # name.lower() → cand
        self.embeds = []         # 内嵌文件 cand（真实度量）
        self.notes = []
        self._bounds = _BoundsCand(note='保守上界')

    @classmethod
    def build(cls, declared_names, embed_files=(), extra_names=('Microsoft YaHei', 'SimSun')):
        cs = cls()
        seen_paths = set()
        for fp in embed_files or ():
            if os.path.isfile(fp) and fp not in seen_paths:
                seen_paths.add(fp)
                cs.embeds.append(_FileCand(fp, note='内嵌/本地字体文件'))
        adv = None
        if os.path.isfile(_ADVANCES_JSON):
            try:
                adv = json.load(open(_ADVANCES_JSON)).get('families', {})
            except (OSError, json.JSONDecodeError):
                adv = None
        for name in list(dict.fromkeys(list(declared_names or ()) + list(extra_names))):
            key = name.lower()
            if key in cs.by_name:
                continue
            fp = _fc_match(name)
            if fp:
                if fp in seen_paths:
                    # 同文件已入集（内嵌或他族名解析至此）——共享同一度量源
                    hit = (next((c for c in cs.embeds if c.path == fp), None)
                           or next((c for c in cs.by_name.values()
                                    if getattr(c, 'path', None) == fp), None))
                    cs.by_name[key] = hit if hit is not None else _FileCand(fp, note='fc-match 替换近似（%s）' % name)
                else:
                    seen_paths.add(fp)
                    cs.by_name[key] = _FileCand(fp, note='fc-match 替换近似（%s）' % name)
            elif adv and key in adv:
                styles = adv[key]
                reg = styles.get('regular') or next(iter(styles.values()))
                cs.by_name[key] = _TableCand(key, reg['advances'],
                                             note='font_advances 表（%s）' % name)
            else:
                cs.by_name[key] = _BoundsCand(note='保守上界（%s）' % name)
                cs.notes.append('候选 %s 无文件无表 → 保守上界' % name)
        return cs

    def _cand(self, name):
        if not name:
            return self._bounds
        c = self.by_name.get(name.lower())
        if c is not None:
            return c
        # 内嵌件族名匹配（run 声明族名 == 内嵌注册名）
        for e in self.embeds:
            fam = (e.font['name'].getDebugName(16) or e.font['name'].getDebugName(1) or '')
            if fam.lower() == name.lower():
                return e
        return self._bounds

    def width_px_for(self, text, sz_px, latin, ea, spc_px=0.0, bold=False,
                     with_boundary=True):
        """逐字分流度量 + 混排边界项：CJK/全角走 ea 轨，其余走 latin 轨；
        每个 CJK↔拉丁相邻对 +MIXED_BOUNDARY_EM（OOXML 自动间距）。"""
        cl, ce = self._cand(latin), self._cand(ea)
        wl = sum(cl.char_em(ch, bold) for ch in text if _cls(ch) == 'latin')
        we = sum(ce.char_em(ch, bold) for ch in text if _cls(ch) != 'latin')
        boundary = mixed_boundaries(text) * MIXED_BOUNDARY_EM if with_boundary else 0.0
        return (wl + we + boundary) * sz_px + spc_px * max(0, len(text))

    def width_pt_for(self, text, sz_pt, latin, ea, spc_pt=0.0, bold=False,
                     with_boundary=True):
        return self.width_px_for(text, sz_pt * 2, latin, ea, spc_pt * 2, bold,
                                 with_boundary) / 2

    # 全局口径（布局期尚无逐 run 族名时的栈级近似）
    def width_px(self, text, sz_px, spc_px=0.0, bold=False, latin=None, ea=None):
        return self.width_px_for(text, sz_px, latin, ea, spc_px, bold)

    def _factors_for(self, latin, ea):
        cl, ce = self._cand(latin), self._cand(ea)
        return max(cl.natural(), ce.natural()), max(cl.em(), ce.em())

    def natural_factor(self, latin=None, ea=None):
        return self._factors_for(latin, ea)[0]

    def em_factor(self, latin=None, ea=None):
        return self._factors_for(latin, ea)[1]

    def close(self):
        for c in list(self.by_name.values()) + self.embeds:
            c.close()

    def describe(self):
        return sorted({'%s（%s）' % (c.kind, c.note)
                       for c in list(self.by_name.values()) + self.embeds})


def _self_test():
    cs = CandidateSet.build(['Microsoft YaHei', 'SimSun', 'Arial'])
    # 逐字分流：CJK 走 ea（SimSun/雅黑轨），拉丁走 latin（Arial 轨）
    w = cs.width_px_for('产品提供者', 20, latin='Arial', ea='SimSun')
    assert abs(w - 100) < 1.0, 'CJK 5 字 @20px 应=100px（1em），实测 %.1f' % w
    w2 = cs.width_px_for('“产品提供者”', 20, latin='Arial', ea='SimSun')
    assert abs(w2 - 140) < 1.0, '全角引号应全宽：%.1f' % w2
    assert cs.natural_factor(ea='SimSun') >= 1.14
    latin = cs.width_px_for('SMART', 20, latin='Arial', ea='SimSun')
    assert 30 < latin < 100, '拉丁宽度异常：%.1f' % latin
    # 混排边界：'10年' = 1 个边界（0|年）→ +1em
    assert mixed_boundaries('10年') == 1
    assert mixed_boundaries('2026年Q1：示例') == 3   # 6|年、6|Q、1|：
    mixed = cs.width_px_for('10年', 20, latin='Arial', ea='SimSun')
    # 绝对值核验：数字 2×0.556em×20 + 年 1em×20 + 边界 0.25em×20×1边界 ≈ 47.2px
    # （0929 校正：边界项实测 0.237em 取 0.25em，见 MIXED_BOUNDARY_EM 注释）
    assert abs(mixed - 47.2) < 2.0, '混排串宽度应为 advance+0.25em 边界≈47px：%.1f' % mixed
    # 纯 CJK 串无边界项
    assert mixed_boundaries('产品提供者') == 0
    print('候选描述:', cs.describe())
    cs.close()
    print('自测通过')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(_self_test())
