#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三形态子技能 C · C1 阶段：可编辑 PPTX 导出（原生元素轨，文本 + 简单形状）。

规格：docs/design/pptx-export-editable.md（§2 路线 / §3 元素映射 L1·L2·L6 / §7 验收）。
与保真轨 export-pptx.py 平行、独立可用；双轨编排与字体内嵌是 C3 的事。

用法：
  python3 scripts/export-pptx-editable.py <deck/index.html> [--out <deck>/export/deck-editable.pptx]

路线（渲染真相 × 契约标记）：Playwright 渲染 deck → freeze 动效 → 渲染后
DOM 快照（真实包围盒 / 真实逐行分行 / 真实计算样式，零估算）→ python-pptx
原生组装：

- 坐标换算【关键】：画布 1920×1080 px → 12192000×6858000 EMU，
  1 画布 px = 6350 EMU（不是 96dpi 的 9525）；字号 1px = 0.5pt；
- 页背景 → 满幅 rect 置底；z-order = DOM 序（先加的在底）；
- L1 文本叶 [data-editable] → p:sp txBox：框=渲染 rect；word_wrap=True
  （wrap=square，用户改字按原宽重排不溢出——ppt-master wrap=none 的超越点）
  + auto_size=None；真实逐行分行 → 逐行 a:p；行内 run 结构（bold/italic/
  underline/strike/字号/颜色逐段）；字体 latin+ea 双 typeface
  （pptx_font_maps.parse_font_family，python-pptx 只写 latin，ea 补丁
  rPr <a:ea typeface>）；字重 ≥600→bold；行距→lnSpc spcPts；
  letter-spacing→rPr spc；opacity×颜色 alpha→srgbClr a:alpha；
- L2 简单几何 → prstGeom（rect/roundRect）：有非透明背景 / 可见边框 /
  borderRadius>0 的块（不含 .baked-source、不含 svg 内部、不含文本叶容器
  之外的元素——含文本叶的容器仍取自身盒置底）；单侧边框 → 细条 rect；
  圆角 → roundRect + adjustment；
- L6：img[data-editable-image] → 定位 p:pic；烙入页
  （data-render-mode="baked"）整页 img 满幅直通，页内不再提取；
- 复杂视觉本期不烙图（C2/L5），在报告 uncovered 诚实列出：
  渐变背景 / 滤镜 / canvas FX / 图表 svg / 信息图 data-ig / 文字特效
  （描边/发光/叠印/流光）/ object-fit:cover 比例不符。

纪律（与保真轨同口径）：单向纪律（deck sha256 前后比对）/ postflight
重开包校验 / 临时目录构建、全过才原子落盘 / 出口报告 JSON（每页 shapes
统计 + uncovered 清单 + native_text_ratio）。

退出码：成功 0，任一失败 1。幂等语义同 extract-manifest：报告除
generated_at 外字节一致。
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))

# 复用保真轨的工具函数（浏览器 freeze 序列 / sha256 / 常量），不复制代码
_spec = importlib.util.spec_from_file_location('export_pptx', os.path.join(HERE, 'export-pptx.py'))
_epx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_epx)
sha256_file = _epx.sha256_file
FREEZE_JS = _epx.FREEZE_JS

_spec2 = importlib.util.spec_from_file_location('pptx_font_maps', os.path.join(HERE, 'pptx_font_maps.py'))
_fonts = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(_fonts)
parse_font_family = _fonts.parse_font_family
PPT_SAFE_FONTS = _fonts.PPT_SAFE_FONTS

_spec3 = importlib.util.spec_from_file_location('pptx_text_metrics', os.path.join(HERE, 'pptx_text_metrics.py'))
_metrics = importlib.util.module_from_spec(_spec3)
_spec3.loader.exec_module(_metrics)

_spec4 = importlib.util.spec_from_file_location('certify_pptx', os.path.join(HERE, 'certify-pptx.py'))
_certify_mod = importlib.util.module_from_spec(_spec4)
_spec4.loader.exec_module(_certify_mod)

EMU_PER_PX = 6350            # 12192000 / 1920 = 6858000 / 1080 = 6350 精确
SLIDE_W_EMU = 12192000
SLIDE_H_EMU = 6858000
PX_TO_PT = 0.5               # 1 画布 px = 0.5pt\nPT_PER_PX = 2.0               # 1pt = 2 画布 px


class ExportError(Exception):
    """管线级失败：打印信息并以退出码 1 终止。"""


def log(msg):
    print('[export-editable] %s' % msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# 渲染快照（渲染后 DOM：真实几何 + 真实逐行分行 + 真实计算样式）
SNAPSHOT_JS = r"""
() => {
  const scale = parseFloat(document.documentElement.style.getPropertyValue('--slide-scale')) || 1;
  const rootCs = getComputedStyle(document.documentElement);
  const out = {scale, pages: [], fontStacks: {
    display: rootCs.getPropertyValue('--font-display').trim(),
    body: rootCs.getPropertyValue('--font-body').trim(),
    mono: rootCs.getPropertyValue('--font-mono').trim(),
  }};
  let eidxSeq = 0;
  function tagE(el){ const i = eidxSeq++; el.setAttribute('data-pptx-eidx', String(i)); return i; }

  function inBaked(el){ return !!el.closest('.baked-source'); }
  function visible(el){
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) <= 0.02) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  function norm(s){ return (s || '').replace(/\s+/g, ' ').trim(); }
  /* 画布坐标：相对 .slide 左上角，除以 --slide-scale */
  function toCanvas(slideRect, r){
    return {
      left: (r.left - slideRect.left) / scale, top: (r.top - slideRect.top) / scale,
      width: r.width / scale, height: r.height / scale,
    };
  }
  function transparent(c){
    if (!c || c === 'transparent') return true;
    const m = /^rgba\(([^)]+)\)$/.exec(c.trim());
    return !!m && parseFloat(m[1].split(',')[3]) === 0;
  }

  /* 逐行真实分行：逐字 Range rect 按 top 聚类成行，行内按 (bold/italic/
     underline/strike/字号/颜色) 相邻同款合并成 run；
     附带硬换行标记（<br> 后的行 hard=true）供逻辑段重组 */
  function leafLines(el){
    /* <br> 位置集合（全文字符序号，含无 rect 字符） */
    const hardBreaks = new Set();
    let cursor = 0;
    (function walk(node){
      for (const ch of node.childNodes){
        if (ch.nodeType === 3){ cursor += (ch.nodeValue || '').length; }
        else if (ch.nodeType === 1){
          if (ch.tagName === 'BR') hardBreaks.add(cursor);
          else walk(ch);
        }
      }
    })(el);
    const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const segs = [];
    let n, order = 0, domPos = 0;
    while ((n = tw.nextNode())){
      const txt = n.nodeValue;
      if (!txt) continue;
      const pcs = getComputedStyle(n.parentElement);
      const st = {
        bold: parseInt(pcs.fontWeight, 10) >= 600,
        italic: pcs.fontStyle === 'italic',
        underline: /underline/.test(pcs.textDecorationLine || pcs.textDecoration || ''),
        strike: /line-through/.test(pcs.textDecorationLine || pcs.textDecoration || ''),
        fontSizePx: parseFloat(pcs.fontSize),
        color: pcs.color,
      };
      for (let i = 0; i < txt.length; i++){
        const dp = domPos++;
        const r = document.createRange();
        r.setStart(n, i); r.setEnd(n, i + 1);
        const rects = r.getClientRects();
        if (!rects.length || rects[0].height === 0) continue;
        const rc = rects[0];
        segs.push({top: rc.top, bottom: rc.bottom, left: rc.left, height: rc.height,
                   ch: txt[i], st, order: order++, domPos: dp});
      }
    }
    /* 行聚类=纵向区间相交（含基线）：同行混排小字 top/bottom 皆异但区间
       相交；换行则行盒首尾相接（次行 top ≥ 前行 bottom − 容差）→ 新行。
       行内按 left 视觉序（LTR）重排 */
    segs.sort((a, b) => (a.top - b.top) || (a.left - b.left) || (a.order - b.order));
    const lines = [];
    for (const s of segs){
      let line = null;
      if (lines.length && s.top < lines[lines.length - 1].bottom - 2){
        line = lines[lines.length - 1];
      } else {
        line = {top: s.top, bottom: s.bottom, left: s.left, height: s.height, segs: []};
        lines.push(line);
      }
      line.bottom = Math.max(line.bottom, s.bottom);
      line.height = Math.max(line.height, s.height);
      line.left = Math.min(line.left, s.left);
      line.segs.push(s);
    }
    for (const line of lines){
      line.segs.sort((a, b) => (a.left - b.left) || (a.order - b.order));
      line.hard = hardBreaks.has(Math.min(...line.segs.map(s => s.domPos)));
      line.runs = [];
      for (const s of line.segs){
        const last = line.runs[line.runs.length - 1];
        if (last && last.st === s.st && last.order + 1 === s.order){
          last.text += s.ch; last.order = s.order;
        } else {
          line.runs.push({text: s.ch, st: s.st, order: s.order});
        }
      }
      delete line.segs;
    }
    return lines.map(l => ({
      runs: l.runs.map(r => ({text: r.text, bold: r.st.bold, italic: r.st.italic,
                              underline: r.st.underline, strike: r.st.strike,
                              fontSizePx: r.st.fontSizePx, color: r.st.color})),
      hard: !!l.hard,
    }));
  }

  /* ---------- C2：图表检测（数值文本 × 几何比例双源校验，容差 5%；
     不过校验或结构识别失败 → markRaster 烙图兜底，绝不硬映射） ---------- */
  function numOf(s){
    const m = /(-?\d+(?:\.\d+)?)/.exec((s || '').replace(/,/g, ''));
    return m ? parseFloat(m[1]) : null;
  }
  function unionRect(rs){
    let l = Infinity, t = Infinity, r = -Infinity, b = -Infinity;
    for (const q of rs){ l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); }
    return {left: l, top: t, right: r, bottom: b, width: r - l, height: b - t};
  }
  function median(a){ const s = a.slice().sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; }
  /* 双源不变量：文本值 / 几何长度 比值恒定（±5%）。scale = 隐含轴上限 */
  function ratioCheck(vals){
    const m = median(vals);
    if (!m) return {ok: false, maxDev: 1, scale: 0};
    const dev = Math.max.apply(null, vals.map(v => Math.abs(v - m) / Math.abs(m)));
    return {ok: dev <= 0.05, maxDev: dev, scale: m};
  }

  let rasterSeq = 0;   // 全 deck 烙图序号（python 侧按键取截图文件）
  const slides = Array.from(document.querySelectorAll('section.slide'));
  for (const slide of slides){
    const slideRect = slide.getBoundingClientRect();
    const page = {
      slide_id: slide.getAttribute('data-slide-id') || '',
      render_mode: slide.getAttribute('data-render-mode') || 'html',
      background: getComputedStyle(slide).backgroundColor,
      backgroundImage: getComputedStyle(slide).backgroundImage,
      items: [],
      charts: [],
      uncovered: [],
      igTextTotal: 0,   // data-ig 根内可见文本叶总数（native_infographic_ratio 分母）
    };
    if (page.render_mode === 'baked'){
      const img = slide.querySelector('img[data-editable-image]');
      if (img) page.items.push({kind: 'image', rect: {left: 0, top: 0, width: 1920, height: 1080},
                                src: img.getAttribute('src') || '', full_bleed: true});
      out.pages.push(page);
      continue;
    }
    // 页背景渐变/纹理图：烙整页底（L5）——子元素截图时隐藏，底图置最底
    page.bg_gradient = !!(page.backgroundImage && page.backgroundImage !== 'none');

    /* 信息图根（L4 分组用；嵌套 data-ig 取最外层根） */
    const igRoots = Array.from(slide.querySelectorAll('[data-ig]'));
    function igOf(el){
      let root = null, n = el;
      while (n && n !== slide){
        if (n.hasAttribute && n.hasAttribute('data-ig')) root = n;
        n = n.parentElement;
      }
      return root ? {root: igRoots.indexOf(root), family: root.getAttribute('data-ig')} : null;
    }
    function markChart(els){ els.forEach(e => e.setAttribute('data-pptx-chart', '1')); }
    function markRaster(el, reason){
      el.setAttribute('data-pptx-raster', reason);
      el.setAttribute('data-pptx-raster-idx', String(rasterSeq++));
      return rasterSeq - 1;
    }

    /* —— L5 烙图标记：canvas FX 仪式层 —— */
    Array.from(slide.querySelectorAll('canvas[data-fx]')).forEach(c => markRaster(c, 'canvas-fx'));

    /* —— 条形/进度（H-Bar / Progress）：轨道 + [data-anim=line|fill-bar] 横条，
       同容器 ≥2 行成行结构（标签 | 条 | 值）——*/
    const barGroups = new Map();
    Array.from(slide.querySelectorAll('[data-anim="line"],[data-anim="fill-bar"]')).forEach(b => {
      if (inBaked(b)) return;
      const track = b.parentElement;
      if (!track || !visible(track)) return;
      const tr = track.getBoundingClientRect(), br = b.getBoundingClientRect();
      if (!(tr.width > tr.height * 1.5 && tr.height >= 4 && br.width > 0)) return;
      const c = track.parentElement;
      if (!barGroups.has(c)) barGroups.set(c, []);
      barGroups.get(c).push({track, frac: br.width / tr.width,
                             color: getComputedStyle(b).backgroundColor, rect: tr});
    });
    for (const [container, rows] of barGroups){
      if (rows.length < 2) continue;
      let ok = true;
      const data = rows.map(({track, frac, color, rect}) => {
        const prev = track.previousElementSibling, next = track.nextElementSibling;
        const label = prev ? norm(prev.textContent) : '';
        const raw = next ? norm(next.textContent) : '';
        const val = numOf(raw);
        if (!label || val === null) ok = false;
        return {label, raw, value: val, frac, color, rect, track};
      });
      if (!ok) continue;   // 行结构不符 → 非图表，保持 L2 形状语义
      const chk = ratioCheck(data.map(d => d.value / Math.max(d.frac, 1e-6)));
      if (chk.ok){
        markChart(data.map(d => d.track));
        page.charts.push({
          kind: 'bar',
          recipe: data.every(d => /%$/.test(d.raw)) ? 'progress' : 'hbar',
          frame: toCanvas(slideRect, unionRect(data.map(d => d.rect))),
          categories: data.map(d => d.label),
          series: [{name: '', values: data.map(d => d.value), pointColors: data.map(d => d.color)}],
          axisMax: chk.scale, ig: igOf(container),
          verify: {method: 'value/条长 比值恒定', maxDev: Math.round(chk.maxDev * 1000) / 1000},
        });
      } else {
        markRaster(container, 'chart-verify-fail:bar(maxDev=' + (chk.maxDev * 100).toFixed(1) + '%)');
      }
    }
    /* 条形行的第二种包装形态：每行独立包装 div（label/条/值 横排），
       全部单行组且共祖父时按祖父容器合并重试 */
    if (![...barGroups.values()].some(g => g.length >= 2)){
      const singles = [...barGroups.values()].flat();
      if (singles.length >= 2){
        const gps = new Set(singles.map(r => r.track.parentElement.parentElement));
        if (gps.size === 1){
          const gp = [...gps][0];
          const rows2 = singles.map(({track, frac, color, rect}) => {
            const wrap = track.parentElement;
            const texts = Array.from(wrap.querySelectorAll('[data-editable]'));
            const lab = texts.find(e => numOf(norm(e.textContent)) === null);
            const valEl = texts.find(e => numOf(norm(e.textContent)) !== null);
            return {label: lab ? norm(lab.textContent) : '', raw: valEl ? norm(valEl.textContent) : '',
                    value: valEl ? numOf(norm(valEl.textContent)) : null, frac, color, rect, track};
          });
          if (rows2.every(d => d.label && d.value !== null)){
            const chk = ratioCheck(rows2.map(d => d.value / Math.max(d.frac, 1e-6)));
            if (chk.ok){
              markChart(rows2.map(d => d.track));
              page.charts.push({
                kind: 'bar', recipe: rows2.every(d => /%$/.test(d.raw)) ? 'progress' : 'hbar',
                frame: toCanvas(slideRect, unionRect(rows2.map(d => d.rect))),
                categories: rows2.map(d => d.label),
                series: [{name: '', values: rows2.map(d => d.value), pointColors: rows2.map(d => d.color)}],
                axisMax: chk.scale, ig: igOf(gp),
                verify: {method: 'value/条长 比值恒定(包装行)', maxDev: Math.round(chk.maxDev * 1000) / 1000},
              });
            } else {
              markRaster(gp, 'chart-verify-fail:bar(maxDev=' + (chk.maxDev * 100).toFixed(1) + '%)');
            }
          }
        }
      }
    }

    /* —— 柱状（Column）：calc 高度柱 + 上数值下类目 —— */
    const colGroups = new Map();
    Array.from(slide.querySelectorAll('[data-editable-skip]')).forEach(el => {
      if (inBaked(el) || el.closest('[data-pptx-chart]')) return;
      const st = el.getAttribute('style') || '';
      if (!/height\s*:\s*calc\(/.test(st)) return;
      const cs = getComputedStyle(el);
      if (transparent(cs.backgroundColor) || !visible(el)) return;
      const r = el.getBoundingClientRect();
      if (!(r.height > 8)) return;
      /* 柱通常各裹一层包装 div（值/柱/类目竖排），按祖父容器归组 */
      const c = el.parentElement.parentElement || el.parentElement;
      if (!colGroups.has(c)) colGroups.set(c, []);
      colGroups.get(c).push({el, color: cs.backgroundColor, rect: r});
    });
    for (const [container, rows] of colGroups){
      if (rows.length < 2) continue;
      let ok = true;
      const data = rows.map(({el, color, rect}) => {
        const prev = el.previousElementSibling, next = el.nextElementSibling;
        const val = prev ? numOf(norm(prev.textContent)) : null;
        const cat = next ? norm(next.textContent) : '';
        if (val === null || !cat) ok = false;
        return {cat, value: val, len: rect.height, color, el, rect};
      });
      if (!ok) continue;
      const chk = ratioCheck(data.map(d => d.value / Math.max(d.len, 1e-6)));
      if (chk.ok){
        markChart(data.map(d => d.el));
        page.charts.push({
          kind: 'column', frame: toCanvas(slideRect, unionRect(data.map(d => d.rect))),
          categories: data.map(d => d.cat),
          series: [{name: '', values: data.map(d => d.value), pointColors: data.map(d => d.color)}],
          axisMax: chk.scale, ig: igOf(container),
          verify: {method: 'value/柱高 比值恒定', maxDev: Math.round(chk.maxDev * 1000) / 1000},
        });
      } else {
        markRaster(container, 'chart-verify-fail:column(maxDev=' + (chk.maxDev * 100).toFixed(1) + '%)');
      }
    }

    /* —— 环图（Donut）与折线（Line）：svg 内几何 + 页内文本双源 —— */
    const svgs = Array.from(slide.querySelectorAll('svg')).filter(s => !inBaked(s) && visible(s));
    for (const svg of svgs){
      const circles = Array.from(svg.querySelectorAll('circle[stroke-dasharray]'));
      const arcs = circles.map(c => {
        const da = (c.getAttribute('stroke-dasharray') || '').trim().split(/[\s,]+/).map(parseFloat).filter(x => !isNaN(x));
        if (da.length < 2 || da[0] <= 0) return null;
        return {frac: da[0] / (da[0] + da[1]), color: getComputedStyle(c).stroke,
                sw: parseFloat(c.getAttribute('stroke-width')) || 0, r: parseFloat(c.getAttribute('r')) || 0};
      }).filter(a => a && a.frac > 0.005 && a.r > 0);
      if (arcs.length >= 2){
        const pcts = Array.from(slide.querySelectorAll('[data-editable]'))
          .filter(e => /^\d+(?:\.\d+)?%$/.test(norm(e.textContent)));
        const rows = pcts.map(pe => {
          const row = pe.closest('div') || slide;
          const lab = Array.from(row.querySelectorAll('[data-editable]')).find(e =>
            e !== pe && norm(e.textContent) && !/^[\d.]/.test(norm(e.textContent)) && !/%$/.test(norm(e.textContent)));
          return {label: lab ? norm(lab.textContent) : '', pct: parseFloat(norm(pe.textContent))};
        });
        const okRows = rows.length === arcs.length && rows.every(r => r.label);
        const maxDev = okRows ? Math.max.apply(null, arcs.map((a, i) =>
          Math.abs(a.frac * 100 - rows[i].pct) / Math.max(rows[i].pct, 1))) : 1;
        if (okRows && maxDev <= 0.05){
          markChart([svg]);
          const a0 = arcs[0];
          page.charts.push({
            kind: 'donut', frame: toCanvas(slideRect, svg.getBoundingClientRect()),
            categories: rows.map(r => r.label),
            series: [{name: '', values: rows.map(r => r.pct), pointColors: arcs.map(a => a.color)}],
            holeSize: a0.r > 0 ? Math.round((1 - a0.sw / a0.r) * 100) : 60,
            ig: igOf(svg), verify: {method: '弧长比例 vs 图例百分比', maxDev: Math.round(maxDev * 1000) / 1000},
          });
        } else {
          markRaster(svg, okRows
            ? 'chart-verify-fail:donut(maxDev=' + (maxDev * 100).toFixed(1) + '%)'
            : 'chart-deferred:donut(图例行匹配失败)');
        }
        continue;
      }
      const polys = Array.from(svg.querySelectorAll('polyline'))
        .filter(p => (p.getAttribute('points') || '').trim().split(/\s+/).filter(Boolean).length >= 4);
      if (polys.length >= 1){
        const svgRect = svg.getBoundingClientRect();
        const vb = (svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(parseFloat);
        const gridYs = Array.from(svg.querySelectorAll('line')).map(l => parseFloat(l.getAttribute('y1'))).filter(y => !isNaN(y));
        let done = false;
        if (gridYs.length >= 2 && vb.length === 4 && vb[3] > 0){
          const yPxOf = y => svgRect.top + (y - vb[1]) / vb[3] * svgRect.height;
          /* 轴标签：纵范围与 svg 相交的纯数字文本 */
          const labs = Array.from(slide.querySelectorAll('[data-editable]')).map(e => {
            const t = norm(e.textContent);
            if (!/^-?\d+(?:\.\d+)?$/.test(t)) return null;
            const r = e.getBoundingClientRect();
            const cy = r.top + r.height / 2;
            if (cy < svgRect.top - 20 || cy > svgRect.bottom + 20) return null;
            return {v: parseFloat(t), y: cy};
          }).filter(Boolean);
          const gy = gridYs.map(yPxOf).sort((a, b) => a - b);
          const lv = labs.slice().sort((a, b) => b.v - a.v);   // 值降序 ↔ y 升序
          let fit = null;
          if (lv.length >= 2 && gy.length >= 2){
            const top = lv[0], bot = lv[lv.length - 1];
            const b = (bot.v - top.v) / (gy[gy.length - 1] - gy[0]);
            const a = top.v - b * gy[0];
            const nearest = y => gy.reduce((p, c) => Math.abs(c - y) < Math.abs(p - y) ? c : p);
            const maxRes = Math.max.apply(null, lv.map(L => Math.abs(a + b * nearest(L.y) - L.v)));
            const yMis = lv.some(L => Math.abs(nearest(L.y) - L.y) > 15);
            const span = Math.max(Math.abs(top.v - bot.v), 1e-6);
            if (!yMis) fit = {a, b, maxDev: maxRes / span};
          }
          const nPts = polys[0].getAttribute('points').trim().split(/\s+/).filter(Boolean).length;
          let cats = null;
          let scope = svg.closest('div');
          while (scope && scope !== slide && !cats){
            for (const sib of Array.from(scope.parentElement.children)){
              if (sib === scope || sib.contains(svg)) continue;
              const texts = Array.from(sib.querySelectorAll('[data-editable]'))
                .map(e => norm(e.textContent)).filter(t => t && t.length <= 6);
              if (texts.length === nPts){ cats = texts; break; }
            }
            scope = scope.parentElement;
          }
          const series = polys.map(p => {
            const stroke = getComputedStyle(p).stroke || p.getAttribute('stroke');
            let name = '';
            const sw = Array.from(slide.querySelectorAll('[data-editable-skip]')).find(e =>
              getComputedStyle(e).backgroundColor === stroke && e.parentElement && e.parentElement.querySelector('[data-editable]'));
            if (sw) name = norm(sw.parentElement.querySelector('[data-editable]').textContent);
            const ys = p.getAttribute('points').trim().split(/\s+/).filter(Boolean)
              .map(pair => parseFloat(pair.split(',')[1]));
            return {name, stroke, dash: (p.getAttribute('stroke-dasharray') || '').trim(), ys};
          });
          if (fit && fit.maxDev <= 0.05 && cats && series.every(s => s.ys.length === nPts)){
            markChart([svg]);
            page.charts.push({
              kind: 'line', frame: toCanvas(slideRect, svgRect), categories: cats,
              series: series.map(s => ({
                name: s.name, color: s.stroke, dash: s.dash,
                values: s.ys.map(y => Math.round((fit.a + fit.b * yPxOf(y)) * 100) / 100),
              })),
              ig: igOf(svg), verify: {method: '轴标签 vs 网格线线性拟合', maxDev: Math.round(fit.maxDev * 1000) / 1000},
            });
            done = true;
          } else {
            markRaster(svg, 'chart-deferred:line(' + (!fit ? '轴拟合失败' : !cats ? '类目容器匹配失败' : !series.every(s => s.ys.length === nPts) ? '点数与类目不符' : 'fit 超差') + ')');
            done = true;
          }
        }
        if (!done) markRaster(svg, 'chart-deferred:line(网格线或 viewBox 缺失)');
        continue;
      }
      markRaster(svg, 'svg-unmapped(非图表 svg)');
    }

    const els = Array.from(slide.querySelectorAll('*'));
    for (const el of els){
      /* svg 的后代跳过（几何由图表映射或烙图接管）；svg 自身不跳——
         它可能是烙图项（未识别 svg）或已被 chart 标记 */
      if (inBaked(el)) continue;
      const svgAnc = el.closest('svg');
      if (svgAnc && svgAnc !== el) continue;
      /* 烙图：元素自身被标记 → 以 DOM 位次插入 raster 项；其子树的
         非文本后代跳过（data-editable 文字仍走 L1 原生叠加在烙图上） */
      if (el.hasAttribute('data-pptx-raster')){
        if (visible(el)) page.items.push({kind: 'raster', rect: toCanvas(slideRect, el.getBoundingClientRect()),
                                          reason: el.getAttribute('data-pptx-raster'),
                                          rasterIdx: parseInt(el.getAttribute('data-pptx-raster-idx'), 10),
                                          ig: igOf(el), eidx: tagE(el)});
        continue;
      }
      if (el.closest('[data-pptx-raster]') && !el.hasAttribute('data-editable')) continue;
      if (el.closest('[data-pptx-chart]') && !el.hasAttribute('data-editable')) continue;
      const tag = el.tagName.toLowerCase();
      if (tag === 'script' || tag === 'style' || tag === 'canvas') continue;

      if (tag === 'img' && el.hasAttribute('data-editable-image')){
        if (!visible(el)) continue;
        const r = toCanvas(slideRect, el.getBoundingClientRect());
        const src = el.getAttribute('src') || '';
        /* SVG 图片 python-pptx 无法直接嵌入（PIL 不识别）→ 走 L5 烙图 */
        if (/\.svg($|\?)/i.test(src)){
          const ridx = markRaster(el, 'image-svg');
          page.items.push({kind: 'raster', rect: r, reason: 'image-svg', rasterIdx: ridx,
                           ig: igOf(el), eidx: tagE(el)});
          continue;
        }
        const it = {kind: 'image', rect: r, src,
                    objectFit: getComputedStyle(el).objectFit, ig: igOf(el), eidx: tagE(el)};
        // 构图宽高比与图片固有比例不一致时 cover 语义 pptx 无法直接表达（C1 记 uncovered）
        if (it.objectFit === 'cover' && el.naturalWidth && el.naturalHeight){
          const boxAr = r.width / r.height, imgAr = el.naturalWidth / el.naturalHeight;
          if (Math.abs(boxAr - imgAr) / imgAr > 0.05) it.uncovered = 'object-fit-cover-crop';
        }
        page.items.push(it);
        continue;
      }

      if (el.hasAttribute('data-editable')){
        if (!visible(el) || !norm(el.textContent)) continue;
        const cs = getComputedStyle(el);
        const igInfo = igOf(el);
        if (igInfo) page.igTextTotal += 1;
        const r = toCanvas(slideRect, el.getBoundingClientRect());
        const fx = [];
        if (parseFloat(cs.webkitTextStrokeWidth || '0') > 0) fx.push('text-stroke(tt-outline)');
        if (cs.textShadow && cs.textShadow !== 'none') fx.push('text-shadow(tt-glow/tt-shadow)');
        if ((cs.webkitBackgroundClip || cs.backgroundClip) === 'text') fx.push('gradient-flow-text');
        if (fx.length) page.uncovered.push('text-effect:' + fx.join('+') + '(视觉层 C2，文字本体原生可编辑)');
        const lines = leafLines(el);
        if (((cs.webkitBackgroundClip || cs.backgroundClip) === 'text')
            || (parseFloat(cs.webkitTextStrokeWidth || '0') > 0 && transparent(cs.color))){
          // 流光/渐变字 fill 透明——可编辑轨按页墨色还原本色（可见 > 特效）
          const ink = getComputedStyle(slide).color;
          for (const L of lines) for (const run of L.runs) run.color = ink;
        }
        page.items.push({
          kind: 'text',
          eidx: tagE(el),
          rect: r,
          style: {
            fontFamily: cs.fontFamily,
            fontSizePx: parseFloat(cs.fontSize),
            fontWeight: parseInt(cs.fontWeight, 10),
            fontStyle: cs.fontStyle,
            color: cs.color,
            textAlign: cs.textAlign,
            lineHeightPx: parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2,
            letterSpacingPx: cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing) || 0,
            opacity: parseFloat(cs.opacity),
          },
          lines,
          ig: igInfo,
        });
        continue;
      }

      /* L2 简单几何候选：非透明背景 / 可见边框 / 圆角（装饰与容器底） */
      if (!visible(el)) continue;
      const cs = getComputedStyle(el);
      /* L5 烙图兜底：渐变底 / 滤镜 / 混合模式——原生模型无等价物，
         子树截图嵌入，文字仍走 L1 原生叠加 */
      if ((cs.backgroundImage && cs.backgroundImage !== 'none' && !transparent(cs.backgroundColor))
          || cs.filter !== 'none' || cs.backdropFilter !== 'none' || cs.mixBlendMode !== 'normal'){
        const reason = cs.filter !== 'none' || cs.backdropFilter !== 'none' || cs.mixBlendMode !== 'normal'
          ? 'filter-blend' : 'gradient-bg';
        const ridx = markRaster(el, reason);
        page.items.push({kind: 'raster', rect: toCanvas(slideRect, el.getBoundingClientRect()),
                         reason, rasterIdx: ridx, ig: igOf(el), eidx: tagE(el)});
        continue;
      }
      const bg = transparent(cs.backgroundColor) ? null : cs.backgroundColor;
      const sides = [];
      for (const side of ['Top', 'Right', 'Bottom', 'Left']){
        const st = cs['border' + side + 'Style'];
        const w = parseFloat(cs['border' + side + 'Width']);
        const c = cs['border' + side + 'Color'];
        if (st && st !== 'none' && st !== 'hidden' && w > 0 && !transparent(c))
          sides.push({side: side.toLowerCase(), width: w, color: c});
      }
      const radius = parseFloat(cs.borderTopLeftRadius) || 0;
      if (!bg && !sides.length && radius <= 0) continue;
      // 含文本叶的容器仍取自身盒（置底），但跳过无背景无边框的纯结构容器
      page.items.push({kind: 'shape', rect: toCanvas(slideRect, el.getBoundingClientRect()),
                       bg, borders: sides, radius,
                       opacity: parseFloat(cs.opacity), ig: igOf(el), eidx: tagE(el)});
    }
    // 形状盒裁剪到画布内（出血装饰记 uncovered 并裁剪）
    for (const it of page.items){
      const r = it.rect;
      if (r.left < -2 || r.top < -2 || r.left + r.width > 1922 || r.top + r.height > 1082){
        const nl = Math.max(0, r.left), nt = Math.max(0, r.top);
        const nr = Math.min(1920, r.left + r.width), nb = Math.min(1080, r.top + r.height);
        it.rect = {left: nl, top: nt, width: Math.max(0, nr - nl), height: Math.max(0, nb - nt)};
        if (it.kind !== 'text') page.uncovered.push('bleed-clipped:' + it.kind + '(出血裁剪)');
      }
    }
    page.items = page.items.filter(it => it.rect.width > 0 && it.rect.height > 0);
    out.pages.push(page);
  }
  return out;
}
"""


class RenderSession:
    """渲染会话：加载 deck → freeze → 入场终态注入；供快照/烙图/真值截图
    共用同一浏览器实例，用完 close()。"""

    def __init__(self, deck_html):
        self.url = 'file://' + os.path.abspath(deck_html)
        self._pw = None
        self.browser = None
        self.page = None

    def __enter__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch()
        self.page = self.browser.new_page(viewport={'width': 1920, 'height': 1080})
        self.page.goto(self.url)
        self.page.wait_for_timeout(1000)
        self.page.evaluate(FREEZE_JS)
        # 入场终态强制：freeze 回滚后离屏页 .in-view 摘除会把 reveal/data-anim
        # 过渡回 opacity:0（快照要的是渲染终态，与骨架打印 CSS 同口径）
        self.page.add_style_tag(content=(
            ".js .reveal,.js [data-anim]{opacity:1 !important;transform:none !important;"
            "transition:none !important;filter:none !important;clip-path:none !important}"
            ".js .split-anim .sp-unit{opacity:1 !important;transform:none !important;"
            "transition:none !important}"
            # 循环动画不止帧元素截图永不"稳定"（playwright element is not stable
            # 超时）——快照是静态真相，全面停帧（与骨架打印 CSS 同口径）
            "*{animation:none !important;transition:none !important}"))
        # content-visibility:auto 下远屏页不排版——Range 逐字 rect 全部塌缩成
        # 一条假行（extract-manifest 同款处理：强制全部排版再测量）
        self.page.evaluate("() => document.querySelectorAll('.slide-slot')"
                           ".forEach(s => s.style.contentVisibility = 'visible')")
        self.page.wait_for_timeout(500)
        return self

    def snapshot(self):
        lang = self.page.evaluate("document.documentElement.lang || 'zh-CN'")
        return self.page.evaluate(SNAPSHOT_JS), lang

    def screenshot_el(self, el, path, hide_text=True):
        """元素截图；hide_text 时先隐藏子树 data-editable 文字（文字走 L1 原生
        叠加，避免图内图外双重渲染）。"""
        if hide_text:
            self.page.evaluate("(e) => e.querySelectorAll('[data-editable]').forEach("
                               "t => t.style.visibility = 'hidden')", el)
        el.screenshot(path=path)
        if hide_text:
            self.page.evaluate("(e) => e.querySelectorAll('[data-editable]').forEach("
                               "t => t.style.visibility = '')", el)

    def screenshot_marked(self, work):
        """C2/L5 烙图：全部 data-pptx-raster-idx 标记元素。返回 {idx: path}。"""
        raster_paths = {}
        for el in self.page.query_selector_all('[data-pptx-raster-idx]'):
            idx = int(el.get_attribute('data-pptx-raster-idx'))
            p = os.path.join(work, 'raster-%d.png' % idx)
            self.screenshot_el(el, p)
            raster_paths[idx] = p
        return raster_paths

    def capture_truth(self, work):
        """每页 freeze 真值截图（L5 回验基准 + PNG 降级源）。dsf=1 → 1920×1080。"""
        truth = []
        for i, s in enumerate(self.page.query_selector_all('section.slide'), 1):
            p = os.path.join(work, 'truth-%02d.png' % i)
            s.screenshot(path=p)
            truth.append(p)
        return truth

    def raster_eidx(self, eidx, work, name):
        """按 eidx 定位元素烙图（L4 冲突消解用）。返回路径或 None。"""
        el = self.page.query_selector('[data-pptx-eidx="%d"]' % eidx)
        if el is None:
            return None
        p = os.path.join(work, name)
        self.screenshot_el(el, p)
        return p

    def close(self):
        try:
            if self.browser:
                self.browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    def __exit__(self, *exc):
        self.close()


# ---------------------------------------------------------------------------
# L1 字体随档默认化（防线 A 自动跑）：fc-match 解析栈内族名 → 本机文件
# （fontconfig 即 Chromium 的字体解析真相）→ 子集化 TTF → fntdata 内嵌；
# 族名回写 run 的 latin/ea typeface，内嵌字体真正生效。
def fc_match(family):
    """fc-match 解析族名 → 本机字体文件路径（含 fontconfig 替换——那正是
    本机渲染所用的字体）；无法解析/非字体文件返回 None。"""
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


def _load_subset_mod():
    spec = importlib.util.spec_from_file_location(
        'subset_fonts', os.path.join(HERE, 'subset-fonts.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plan_fonts(snap, deck_lang, deck_dir, work, embed_enabled):
    """L1+F3 字体计划：fc-match 解析三栈 → 子集化 TTF → 以【映射后族名】
    （parse_font_family → 雅黑/宋体系，目标机必有）注册内嵌，run 的
    typeface 保持映射名（WPS 可预测回退，365 吃内嵌增强）。
    返回 {'embeds': [{path, declare, slot}], 'cands': CandidateSet,
          'margin_mode', 'notes'}"""
    plan = {'embeds': [], 'cands': None, 'margin_mode': 'normal', 'notes': []}
    stacks = snap.get('fontStacks') or {}
    subset_mod = _load_subset_mod()

    # 候选字体集（认证/布局共用）：内嵌文件 + 声明族名 + 雅黑/宋体
    declared = []
    for role in ('display', 'body', 'mono'):
        st = stacks.get(role)
        if st:
            f = parse_font_family(st, deck_lang)
            declared += [f['latin'], f['ea']]
    embed_paths = []

    if not embed_enabled:
        plan['margin_mode'] = 'reinforced'
        plan['notes'].append('--no-embed-fonts：字体随档关闭（回退映射 + 余量加强）')
    else:
        deck_fonts = os.path.join(deck_dir, 'fonts')
        deck_ttfs = sorted(f for f in os.listdir(deck_fonts)
                           if f.lower().endswith('.ttf')) if os.path.isdir(deck_fonts) else []
        if deck_ttfs:
            # 生成侧已跑防线 A：直接内嵌既有子集，族名按文件内 nameID（ID16 优先）
            from fontTools.ttLib import TTFont
            for fn in deck_ttfs:
                fp = os.path.join(deck_fonts, fn)
                embed_paths.append(fp)
                font = TTFont(fp)
                fam = (font['name'].getDebugName(16) or font['name'].getDebugName(1)
                       or fn.rsplit('.', 1)[0])
                sub = (font['name'].getDebugName(2) or '').lower()
                w = font['OS/2'].usWeightClass if 'OS/2' in font else 400
                if not font['name'].getDebugName(16) and sub and fam.lower().endswith(' ' + sub):
                    fam = fam[: -len(sub) - 1]
                font.close()
                plan['embeds'].append({'path': fp, 'declare': [fam],
                                       'slot': 'bold' if (w >= 600 or 'bold' in sub) else 'regular'})
            plan['notes'].append('使用 deck fonts/ 既有子集（%d 个 TTF）' % len(deck_ttfs))
        else:
            charset = ''.join(sorted({c for p in snap['pages'] for it in p['items']
                                      if it['kind'] == 'text'
                                      for line in (it.get('lines') or [])
                                      for run in line['runs'] for c in run['text']
                                      if not c.isspace()}))
            fonts_work = os.path.join(work, 'fonts')
            os.makedirs(fonts_work, exist_ok=True)
            for role in ('display', 'body', 'mono'):
                stack = stacks.get(role) or ''
                if not stack:
                    continue
                mapped = parse_font_family(stack, deck_lang)
                resolved = None
                for fam in [f.strip().strip('\'"') for f in stack.split(',') if f.strip()]:
                    if fam.lower() in ('sans-serif', 'serif', 'monospace', 'system-ui',
                                       '-apple-system', 'blinkmacsystemfont'):
                        continue
                    fpath = fc_match(fam)
                    if fpath:
                        resolved = (fam, fpath)
                        break
                if not resolved:
                    plan['margin_mode'] = 'reinforced'
                    plan['notes'].append('%s 栈无本机可解析字体（%s）——回退映射 + 余量加强'
                                         % (role, stack[:60]))
                    continue
                fam, fpath = resolved
                try:
                    name, weight, fmt, _ = subset_mod.subset_one(fam, fpath, charset,
                                                                 fonts_work, 'ttf')
                except SystemExit as e:
                    plan['margin_mode'] = 'reinforced'
                    plan['notes'].append('%s 栈子集化失败（%s）' % (role, e))
                    continue
                sub_path = os.path.join(fonts_work, name)
                # fsType 闸读全量字体（子集原样保留该字段）
                try:
                    from fontTools.ttLib import TTFont
                    full = TTFont(fpath)
                except Exception:
                    from fontTools.ttLib import TTCollection
                    full = TTCollection(fpath).fonts[0]
                fs_type = full['OS/2'].fsType if 'OS/2' in full else None
                is_cjk = 0x4E2D in (full.getBestCmap() or {})
                full.close()
                if fs_type is None or not _fsType_embeddable(fs_type):
                    plan['margin_mode'] = 'reinforced'
                    plan['notes'].append('%s 栈字体 fsType=%s 许可受限不嵌——回退 + 余量加强'
                                         % (role, fs_type))
                    os.remove(sub_path)
                    continue
                slot = 'bold' if weight >= 600 else 'regular'
                # F3：以映射后族名注册内嵌（WPS 回退可预测、365 吃内嵌增强）
                declare = sorted({mapped['ea'], mapped['latin']} if is_cjk
                                 else {mapped['latin']})
                embed_paths.append(sub_path)
                plan['embeds'].append({'path': sub_path, 'declare': declare, 'slot': slot})
                plan['notes'].append('%s 栈：%s → 内嵌声明为 %s（fsType=0x%04x）'
                                     % (role, fam, '/'.join(declare), fs_type))
            if not plan['embeds']:
                plan['margin_mode'] = 'reinforced'
                plan['notes'].append('无可内嵌字体——回退映射 + 余量加强模式')

    plan['cands'] = _metrics.CandidateSet.build(sorted(set(declared)), embed_paths)
    plan['notes'] += ['候选度量源：' + d for d in plan['cands'].describe()]
    return plan


# ---------------------------------------------------------------------------
# L2 行高与基线校准 + L3 松配合：计算每个文本叶的终盒（item['box']）与
# 校准行距（item['lnSpcPt']），写回快照供组装与 L4 扫描消费
def _stack_key(font_family_str):
    return re.sub(r'[\s\'"]', '', font_family_str or '').lower()


def _punct_ratio(text):
    """全角标点（引号/书名号/冒号等）占比——标点密集框宽度余量加大。"""
    if not text:
        return 0.0
    n = sum(1 for ch in text
            if 0x3000 <= ord(ch) <= 0x303F or 0xFF00 <= ord(ch) <= 0xFF0F
            or 0x2018 <= ord(ch) <= 0x201D)
    return n / len(text)


def logical_paras(item):
    """渲染行 → 逻辑段重组（0929 对齐修正）：逐渲染行 a:p 会把 Chromium 的
    紧凑断行（无混排间距）锁死为 PPT 段落边界，迫使 PPT 逐段重断行、
    行数虚增（幻行）。逻辑段 = <br> 硬换行分隔（快照 line.hard 标记），
    段内软换行交还 PPT 贪心重排——与 wrap=square 语义一致、与用户编辑
    行为一致（改字本就该整段重排）。返回 [{'runs': [...]}]。"""
    lines = item.get('lines') or []
    paras = [{'runs': []}]
    for i, line in enumerate(lines):
        if i and line.get('hard'):
            paras.append({'runs': []})
        paras[-1]['runs'] += line['runs']
    return paras


def apply_layout(snap, fplan):
    """F2 行距模型 + F3 宽度预算（候选字体集最坏实测，宁可宽不可窄）：
    - 单行/标题/标签：wrap=none 永不重排；框宽 = 最坏墨水宽 ×1.08
      （全角标点占比 >20% → ×1.15）；框高 = 最坏自然行高单行；基线补偿保留；
    - 多行正文（逻辑段 a:p 模型，0929）：lnSpc 写 spcPct = max(作者行高/最坏
      自然行高,1.03)——行距随字体缩放，机制免疫行内叠字；块高 = Σ各逻辑段
      贪心换行行数（greedy_wrap_lines，与 certify 同一函数）×行距 + 0.5 行
      余量；框宽 = 渲染宽 ×1.02；
    终盒 item['box'] / lnSpcPct / wrap / fontScale 供组装与认证消费。"""
    cands = fplan['cands']
    for pg in snap['pages']:
        for it in pg['items']:
            if it['kind'] != 'text':
                continue
            st = it['style']
            mf = parse_font_family(st['fontFamily'], None)   # F3 分流轨
            nat = cands.natural_factor(mf['latin'], mf['ea'])
            em = cands.em_factor(mf['latin'], mf['ea'])
            r = it['rect']
            lines = it.get('lines') or []
            fs = st['fontSizePx']
            lh = st['lineHeightPx']
            shift = min(max(0.0, (lh - em * fs) / 2), 0.5 * lh)
            it['fontScale'] = 1.0
            if len(lines) <= 1:
                text = ''.join(run['text'] for line in lines for run in line['runs'])
                ink_w = cands.width_px_for(text, fs, mf['latin'], mf['ea'],
                                           st.get('letterSpacingPx', 0))
                margin = 1.15 if _punct_ratio(text) > 0.2 else 1.08
                it['wrap'] = 'none'
                it['lnSpcPct'] = None
                it['box'] = {'left': r['left'], 'top': r['top'] + shift,
                             'width': ink_w * margin,
                             'height': nat * fs}
                it['need_h'] = nat * fs
                it['ink_h'] = em * fs
                it['ink_w'] = ink_w
                it['ink_bottom'] = it['box']['top'] + em * fs
            else:
                w = r['width'] * 1.02
                pct = max(lh / (nat * fs), 1.03)
                need = 0.0
                # 逻辑段贪心换行（与 certify 同一函数）：段内软换行交还 PPT，
                # 不再用 Chromium 逐行切片锁死断行点
                for para in logical_paras(it):
                    pruns = [{'text': seg['text'], 'sz': fs,
                              'latin': mf['latin'], 'ea': mf['ea'],
                              'spc': st.get('letterSpacingPx', 0),
                              'bold': seg.get('bold')}
                             for seg in para['runs']]
                    n_w, _ = _metrics.greedy_wrap_lines(cands, pruns, w)
                    need += n_w * pct * nat * fs
                it['wrap'] = 'square'
                it['lnSpcPct'] = pct
                it['box'] = {'left': r['left'], 'top': r['top'] + shift,
                             'width': w, 'height': need + 0.5 * pct * nat * fs}
                it['need_h'] = need
                # 墨水底 = 框顶 + (行数−1)×行距 + 末行墨迹（与 certify 同口径）
                it['ink_bottom'] = it['box']['top'] + need - pct * nat * fs + em * fs
                it['ink_h'] = need - pct * nat * fs + em * fs
            it['slacked'] = True

# ---------------------------------------------------------------------------
# L5 LO 渲染回验 + 逐页混合降级（出厂门禁；LO 是参考渲染近似裁判）
def lo_verify(pptx_path, truth, work, snap, threshold_catastrophic=40.0,
              text_coverage_min=0.98):
    """L5 出厂门禁（LO 参考渲染）。阈值口径【2026-09-24 证据修订】：
    可编辑轨的校准行距（PPT 自然行高 ≠ 作者 line-height）使 CJK 文本页
    在 LO 下产生 ~6-13% 系统性像素差——这是正确渲染的签名而非破损，
    5% 全页 diff 会误杀全部正常页。改为两指标：
      ① 内容存在性：LO 渲染 PDF 文本层逐页抽提，快照文本叶（规范化）
         覆盖率 < 98% → 降级（文字塌缩/不可见才是真的出厂事故）；
      ② 灾难性像素差：diff > 40% → 降级（整页背景/大图级错误）；
    行级重叠由 L4 静态几何扫描兜底（零残留硬规则）。
    LO 是参考渲染近似裁判，真实 PowerPoint 仍以人工目检为准。"""
    def _norm(t):
        return re.sub(r'\s+', '', t or '')
    if _epx.screenshots_disabled():
        return {'status': 'skipped', 'note': '截图设施不可用（PPTX_EXPORT_DISABLE_SCREENSHOT）'}
    if not shutil.which('soffice'):
        return {'status': 'skipped', 'note': 'LibreOffice 不可用——回验跳过（非阻断）'}
    lo_dir = os.path.join(work, 'lo')
    os.makedirs(lo_dir, exist_ok=True)
    try:
        r = subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', pptx_path,
                            '--outdir', lo_dir],
                           capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.SubprocessError) as e:
        return {'status': 'skipped', 'note': 'LibreOffice 调用失败：%s' % e}
    pdf = os.path.join(lo_dir, os.path.splitext(os.path.basename(pptx_path))[0] + '.pdf')
    if r.returncode != 0 or not os.path.isfile(pdf):
        return {'status': 'skipped', 'note': 'LibreOffice 转换失败：%s' % (r.stderr or '')[:200]}
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    page_diffs = []
    degraded = []
    for i in range(len(doc)):
        if i >= len(truth):
            break
        pg = snap['pages'][i]
        sid = pg['slide_id']
        lo_png = os.path.join(lo_dir, 'lo-%02d.png' % (i + 1))
        doc[i].render(scale=1280 / 960).to_pil().convert('RGB').save(lo_png)
        diff_pct, _, _ = _epx.diff_pair(truth[i], lo_png)
        # 内容存在性：快照文本叶字符多重集 ⊆ LO 文本层（阶数无关——
        # 换行重排/孤儿行不影响；逐字缺失才算内容事故）
        leaves = [_norm(''.join(run['text'] for line in (it.get('lines') or [])
                              for run in line['runs']))
                  for it in pg['items'] if it['kind'] == 'text']
        leaves = [t for t in leaves if t]
        coverage = None
        if leaves and pg.get('render_mode') != 'baked':
            from collections import Counter
            tp = doc[i].get_textpage()
            lo_chars = Counter(_norm(tp.get_text_range(0, tp.count_chars())))
            leaf_chars = Counter(''.join(leaves))
            missing = sum((leaf_chars - lo_chars).values())
            coverage = 1 - missing / max(1, sum(leaf_chars.values()))
        rec = {'slide_id': sid, 'diff_pct': round(diff_pct, 3),
               'text_coverage': None if coverage is None else round(coverage, 4)}
        page_diffs.append(rec)
        if diff_pct > threshold_catastrophic:
            degraded.append({'index': i, 'slide_id': sid, 'reason': 'catastrophic-diff',
                             'diff_pct': round(diff_pct, 3)})
        elif coverage is not None and coverage < text_coverage_min:
            degraded.append({'index': i, 'slide_id': sid, 'reason': 'text-coverage',
                             'text_coverage': round(coverage, 4),
                             'diff_pct': round(diff_pct, 3)})
    return {'status': 'done', 'threshold_catastrophic_pct': threshold_catastrophic,
            'text_coverage_min': text_coverage_min,
            'page_diffs': page_diffs, 'degraded': degraded}



def parse_color(c):
    """返回 (r, g, b, a) 0-255/0-1，无法解析返回 None。"""
    if not c:
        return None
    c = c.strip()
    m = re.match(r'^rgba?\(([^)]+)\)$', c)
    if m:
        parts = [p.strip() for p in m.group(1).split(',')]
        if len(parts) >= 3:
            r, g, b = (max(0, min(255, float(p))) for p in parts[:3])
            a = float(parts[3]) if len(parts) > 3 else 1.0
            return int(round(r)), int(round(g)), int(round(b)), max(0.0, min(1.0, a))
        return None
    m = re.match(r'^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*/\s*([\d.]+%?))?\)$', c)
    if m:
        a = 1.0
        if m.group(4) is not None:
            a = float(m.group(4).rstrip('%')) / (100.0 if m.group(4).endswith('%') else 1.0)
        return (int(round(float(m.group(1)) * 255)),
                int(round(float(m.group(2)) * 255)),
                int(round(float(m.group(3)) * 255)),
                max(0.0, min(1.0, a)))
    return None


def _patch_alpha(srgb_clr_el, alpha):
    """srgbClr 元素追加 <a:alpha>（alpha∈[0,1)，val 千分比）。"""
    if alpha >= 0.999:
        return
    from pptx.oxml.ns import qn
    from lxml import etree
    el = etree.SubElement(srgb_clr_el, qn('a:alpha'))
    el.set('val', str(int(round(alpha * 100000))))


def _solid_fill_rgb(fill_owner, rgb, alpha):
    """python-pptx 写完 rgb 后补 alpha 通道。"""
    fill_owner.solid()
    fill_owner.fore_color.rgb = rgb
    from pptx.oxml.ns import qn
    sp_pr = fill_owner._xPr  # FillFormat 的内部 xml（spPr 或 rPr 等）
    srgb = sp_pr.find('.//' + qn('a:srgbClr'))
    if srgb is not None:
        _patch_alpha(srgb, alpha)


# ---------------------------------------------------------------------------
# 组装（python-pptx 原生元素）
def add_native_chart(shapes, ch, RGBColor, Pt):
    """L3 原生 chart：数据/系列名/类目全部来自 DOM 快照（双源校验已过），
    轴与图例删除（标签由 L1 文本框承担，避免双重渲染）；bar 图首类目在顶。"""
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.oxml.ns import qn
    from lxml import etree

    r = ch['frame']
    cd = CategoryChartData()
    cd.categories = ch['categories']
    for s in ch['series']:
        cd.add_series(s.get('name') or '', tuple(s['values']))
    ctype = {'bar': XL_CHART_TYPE.BAR_CLUSTERED,
             'column': XL_CHART_TYPE.COLUMN_CLUSTERED,
             'line': XL_CHART_TYPE.LINE_MARKERS,
             'donut': XL_CHART_TYPE.DOUGHNUT}[ch['kind']]
    gf = shapes.add_chart(ctype,
                          int(round(r['left'] * EMU_PER_PX)),
                          int(round(r['top'] * EMU_PER_PX)),
                          int(round(r['width'] * EMU_PER_PX)),
                          int(round(r['height'] * EMU_PER_PX)), cd)
    gf.name = 'chart·' + ch['kind'] + ('·' + ch.get('recipe', '') if ch.get('recipe') else '')
    chart = gf.chart
    chart.has_legend = False
    try:
        chart.category_axis.visible = False    # 标签已由 L1 文本承担
        chart.value_axis.visible = False
        if ch.get('axisMax'):
            chart.value_axis.maximum_scale = float(ch['axisMax'])
    except (AttributeError, ValueError):
        pass                                   # donut 无直角坐标轴
    plot = chart.plots[0]
    if ch['kind'] in ('bar', 'column'):
        try:
            plot.gap_width = 40
        except (AttributeError, ValueError):
            pass
    if ch['kind'] == 'bar':                    # pptx 条形图首类目默认在底，翻转到顶
        orient = chart.category_axis._element.find(qn('c:scaling') + '/' + qn('c:orientation'))
        if orient is not None:
            orient.set('val', 'maxMin')
    for si, ser in enumerate(chart.series):
        sd = ch['series'][si]
        if ch['kind'] == 'line':
            col = parse_color(sd.get('color'))
            if col:
                ser.format.line.color.rgb = RGBColor(*col[:3])
                ser.format.line.width = Pt(1.25)
            try:
                ser.smooth = False
            except (AttributeError, ValueError):
                pass
            if sd.get('dash'):
                try:
                    from pptx.enum.dml import MSO_LINE_DASH_STYLE
                    ser.format.line.dash_style = MSO_LINE_DASH_STYLE.DASH
                except (AttributeError, ValueError):
                    pass
        else:
            pcs = sd.get('pointColors') or []
            for pi, pt in enumerate(ser.points):
                col = parse_color(pcs[pi] if pi < len(pcs) else sd.get('color'))
                if col:
                    pt.format.fill.solid()
                    pt.format.fill.fore_color.rgb = RGBColor(*col[:3])
    if ch['kind'] == 'donut':
        # python-pptx 默认已带 firstSliceAng=0/holeSize=50——改写而非追加
        dch = chart._chartSpace.find('.//' + qn('c:doughnutChart'))
        if dch is not None:
            el = dch.find(qn('c:firstSliceAng'))
            if el is None:
                el = etree.SubElement(dch, qn('c:firstSliceAng'))
            el.set('val', '270')               # 12 点位起始（与 rotate(-90) 一致）
            el = dch.find(qn('c:holeSize'))
            if el is None:
                el = etree.SubElement(dch, qn('c:holeSize'))
            el.set('val', str(int(ch.get('holeSize') or 60)))
    # chartSpace / plotArea 无底无框：页面底色透过来，暗页不出白盒
    cs = chart._chartSpace
    chart_el = cs.find(qn('c:chart'))
    sp = etree.Element(qn('c:spPr'))
    etree.SubElement(sp, qn('a:noFill'))
    ln = etree.SubElement(sp, qn('a:ln'))
    etree.SubElement(ln, qn('a:noFill'))
    if chart_el is not None:
        chart_el.addnext(sp)
    pa = cs.find('.//' + qn('c:plotArea'))
    if pa is not None:
        sp2 = etree.SubElement(pa, qn('c:spPr'))
        etree.SubElement(sp2, qn('a:noFill'))
        ln2 = etree.SubElement(sp2, qn('a:ln'))
        etree.SubElement(ln2, qn('a:noFill'))
    return gf


def add_text_item(shapes, item, deck_lang, RGBColor, Pt, PP_ALIGN, fplan=None):
    from pptx.oxml.ns import qn
    from lxml import etree

    r = item.get('box') or item['rect']      # L2/L3 终盒（基线补偿 + 松配合）
    st = item['style']
    tb = shapes.add_textbox(int(round(r['left'] * EMU_PER_PX)),
                                  int(round(r['top'] * EMU_PER_PX)),
                                  int(round(r['width'] * EMU_PER_PX)),
                                  int(round(r['height'] * EMU_PER_PX)))
    tf = tb.text_frame
    # wrap=square 改字按原宽重排不溢出；单行禁折行（L3）
    tf.word_wrap = (item.get('wrap', 'square') != 'none')
    from pptx.enum.text import MSO_AUTO_SIZE
    tf.auto_size = MSO_AUTO_SIZE.NONE        # 无 autofit
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

    fonts = parse_font_family(st['fontFamily'], deck_lang)   # F3：目标机必有字体（内嵌以映射名注册）
    align = {'left': PP_ALIGN.LEFT, 'start': PP_ALIGN.LEFT,
             'center': PP_ALIGN.CENTER, 'right': PP_ALIGN.RIGHT,
             'end': PP_ALIGN.RIGHT, 'justify': PP_ALIGN.JUSTIFY}.get(st['textAlign'], PP_ALIGN.LEFT)

    lines = logical_paras(item) or [{'runs': [{'text': '', 'bold': False, 'italic': False,
                                               'underline': False, 'strike': False,
                                               'fontSizePx': st['fontSizePx'], 'color': st['color']}]}]
    # 逐逻辑段一个 a:p（<br> 硬换行分段；软换行交还 PPT wrap=square 重排）
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        # lnSpc 写 spcPct（F2：行距随字体缩放，机制免疫行内叠字）
        if item.get('lnSpcPct'):
            p.line_spacing = round(item['lnSpcPct'], 4)
        p.space_before = Pt(0)
        p.space_after = Pt(0)
        for seg in line['runs']:
            run = p.add_run()
            run.text = seg['text']
            f = run.font
            f.size = Pt(seg['fontSizePx'] * PX_TO_PT)        # 1px = 0.5pt
            if seg.get('bold'):
                f.bold = True
            if seg.get('italic'):
                f.italic = True
            if seg.get('underline'):
                f.underline = True
            f.name = fonts['latin']                          # 只写 latin
            col = parse_color(seg.get('color') or st['color'])
            alpha = st.get('opacity', 1.0)
            if col:
                f.color.rgb = RGBColor(*col[:3])
                alpha *= col[3]
            rpr = run._r.get_or_add_rPr()
            ea = etree.SubElement(rpr, qn('a:ea'))           # ea 双 typeface 补丁
            ea.set('typeface', fonts['ea'])
            if seg.get('strike'):
                rpr.set('strike', 'sngStrike')
            if st.get('letterSpacingPx'):
                rpr.set('spc', str(int(round(st['letterSpacingPx'] * 50))))  # 1/100pt
            if alpha < 0.999:
                srgb = rpr.find(qn('a:solidFill') + '/' + qn('a:srgbClr'))
                if srgb is not None:
                    _patch_alpha(srgb, alpha)
    # F2 缩字修复痕迹：normAutofit fontScale（PPT/LO 渲染时缩放）
    fs100 = int(round((item.get('fontScale') or 1.0) * 100000))
    if fs100 < 100000:
        body_pr = tb.text_frame._txBody.find(qn('a:bodyPr'))
        for old in body_pr.findall(qn('a:noAutofit')):
            body_pr.remove(old)
        na = etree.SubElement(body_pr, qn('a:normAutofit'))
        na.set('fontScale', str(fs100))
    return tb


def add_shape_item(shapes, item, RGBColor, Pt):
    from pptx.enum.shapes import MSO_SHAPE

    r = item['rect']
    alpha = item.get('opacity', 1.0)
    borders = item.get('borders') or []
    bg = parse_color(item.get('bg'))

    # 单侧（或多侧）细边框且无填充 → 细条 rect（hairline 高频形态）
    if borders and not bg:
        for b in borders:
            x, y, w, h = r['left'], r['top'], r['width'], r['height']
            bw = b['width']
            if b['side'] == 'top':
                box = (x, y, w, bw)
            elif b['side'] == 'bottom':
                box = (x, y + h - bw, w, bw)
            elif b['side'] == 'left':
                box = (x, y, bw, h)
            else:
                box = (x + w - bw, y, bw, h)
            col = parse_color(b['color'])
            bar = shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                         int(round(box[0] * EMU_PER_PX)),
                                         int(round(box[1] * EMU_PER_PX)),
                                         max(1, int(round(box[2] * EMU_PER_PX))),
                                         max(1, int(round(box[3] * EMU_PER_PX))))
            bar.shadow.inherit = False
            if col:
                _solid_fill_rgb(bar.fill, RGBColor(*col[:3]), col[3] * alpha)
            bar.line.fill.background()
        return

    # 四边等宽边框 + 可选填充 → 原生形状
    rounded = (item.get('radius') or 0) > 0
    shp = shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        int(round(r['left'] * EMU_PER_PX)), int(round(r['top'] * EMU_PER_PX)),
        int(round(r['width'] * EMU_PER_PX)), int(round(r['height'] * EMU_PER_PX)))
    shp.shadow.inherit = False
    if rounded:
        adj = min(0.5, item['radius'] / max(1.0, min(r['width'], r['height'])))
        try:
            shp.adjustments[0] = adj
        except (IndexError, ValueError):
            pass
    if bg:
        _solid_fill_rgb(shp.fill, RGBColor(*bg[:3]), bg[3] * alpha)
    else:
        shp.fill.background()
    if len(borders) == 4 and len({(b['width'], b['color']) for b in borders}) == 1:
        col = parse_color(borders[0]['color'])
        if col:
            shp.line.color.rgb = RGBColor(*col[:3])
            shp.line.width = Pt(borders[0]['width'] * PX_TO_PT)
    else:
        shp.line.fill.background()


def slide_elements_from_snap(page, deck_lang):
    """页快照（apply_layout 定型后）→ certify 的 SlideElements 模型。
    与 build_pptx 的发射逐项同构：z 序 = sp 发射序（页底 bg 矩形最先；
    ig 组成员归属组、组占位在首成员位置——与 XML 文档序一致），几何经
    同一 EMU 取整换算，字体族名经同一 parse_font_family 映射，insets=0、
    spc/lnSpcPct/fontScale 与 add_text_item 写入值同口径。
    pic/graphicFrame（图片/烙图/图表）按 certify XML 走查同口径豁免。
    用途：check-capacity 生成侧预认证——两闸共用同一数学的落点。"""
    se = _certify_mod.SlideElements()

    def emit_text(item, n_text):
        r = item.get('box') or item['rect']
        st = item['style']
        fonts = parse_font_family(st['fontFamily'], deck_lang)
        paras = []
        for para in logical_paras(item):
            lnspc = None
            if item.get('lnSpcPct'):
                lnspc = ('pct', round(item['lnSpcPct'], 4))
            runs = []
            for seg in para['runs']:
                runs.append({'text': seg['text'],
                             'sz': int(round(seg.get('fontSizePx', st['fontSizePx'])
                                             * 50)) / 100.0,
                             'spc': int(round((st.get('letterSpacingPx') or 0)
                                              * 50)) / 100.0,
                             'bold': bool(seg.get('bold')),
                             'latin': fonts['latin'], 'ea': fonts['ea']})
            paras.append({'lnspc': lnspc, 'runs': runs})
        if not paras:
            paras = [{'lnspc': None, 'runs': []}]
        lines = item.get('lines') or []
        se.z += 1
        se.texts.append({'name': 't%03d' % n_text,
                         'x': int(round(r['left'] * EMU_PER_PX)) / 12700.0,
                         'y': int(round(r['top'] * EMU_PER_PX)) / 12700.0,
                         'w': int(round(r['width'] * EMU_PER_PX)) / 12700.0,
                         'h': int(round(r['height'] * EMU_PER_PX)) / 12700.0,
                         'wrap': 'none' if item.get('wrap') == 'none' else None,
                         'insets': {'lIns': 0.0, 'rIns': 0.0, 'tIns': 0.0, 'bIns': 0.0},
                         'paras': paras,
                         'fontScale': item.get('fontScale') or 1.0,
                         'z': se.z,
                         'first': ''.join(seg['text'] for line in lines
                                          for seg in line['runs'])[:12]})

    def emit_shape(item):
        r = item['rect']
        borders = item.get('borders') or []
        bg = parse_color(item.get('bg'))
        if borders and not bg:
            for b in borders:               # 单侧细边框 → 细条 rect（同 add_shape_item）
                x, y, w, h = r['left'], r['top'], r['width'], r['height']
                bw = b['width']
                if b['side'] == 'top':
                    box = (x, y, w, bw)
                elif b['side'] == 'bottom':
                    box = (x, y + h - bw, w, bw)
                elif b['side'] == 'left':
                    box = (x, y, bw, h)
                else:
                    box = (x + w - bw, y, bw, h)
                se.z += 1
                se.shapes.append({'name': 's-bar', 'roundish': False, 'z': se.z,
                                  'x': int(round(box[0] * EMU_PER_PX)) / 12700.0,
                                  'y': int(round(box[1] * EMU_PER_PX)) / 12700.0,
                                  'w': max(1, int(round(box[2] * EMU_PER_PX))) / 12700.0,
                                  'h': max(1, int(round(box[3] * EMU_PER_PX))) / 12700.0})
            return
        rounded = (item.get('radius') or 0) > 0
        w = int(round(r['width'] * EMU_PER_PX)) / 12700.0
        h = int(round(r['height'] * EMU_PER_PX)) / 12700.0
        roundish = False
        if rounded:
            adj = min(0.5, item['radius'] / max(1.0, min(r['width'], r['height'])))
            roundish = adj >= 0.45 and abs(w - h) <= max(w, h) * 0.08
        se.z += 1
        se.shapes.append({'name': 's', 'roundish': roundish, 'z': se.z,
                          'x': int(round(r['left'] * EMU_PER_PX)) / 12700.0,
                          'y': int(round(r['top'] * EMU_PER_PX)) / 12700.0,
                          'w': w, 'h': h})

    if page['render_mode'] != 'baked' and parse_color(page.get('background')):
        se.z += 1
        se.shapes.append({'name': 'bg', 'x': 0.0, 'y': 0.0, 'roundish': False,
                          'w': SLIDE_W_EMU / 12700.0, 'h': SLIDE_H_EMU / 12700.0,
                          'z': se.z})
    # 发射序 = XML 文档序：ig 组成员随组，组占位在首成员位置
    group_members = {}
    order = []
    for item in page['items']:
        ig = item.get('ig')
        if ig:
            key = ig['root']
            if key not in group_members:
                group_members[key] = []
                order.append(('group', key))
            group_members[key].append(item)
        else:
            order.append(('item', item))
    n_text = 0
    for kind, payload in order:
        seq = group_members[payload] if kind == 'group' else [payload]
        for item in seq:
            if item['kind'] == 'text':
                emit_text(item, n_text)
                n_text += 1
            elif item['kind'] == 'shape':
                emit_shape(item)
            # image/raster/chart：pic/graphicFrame 豁免（certify 走查同口径）
    return se


def add_svg_blip(slide, pic, svg_path, page_no, package):
    """svgBlip 双写（保真轨同款结构）：a:blip r:embed→PNG，extLst 里
    asvg:svgBlip 指向 SVG 媒体件（老 Office 自动降级 PNG）。"""
    from pptx.opc.package import Part
    from pptx.opc.packuri import PackURI
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.oxml.ns import qn
    from lxml import etree

    with open(svg_path, 'rb') as f:
        blob = f.read()
    part = Part(PackURI('/ppt/media/degraded-%02d.svg' % page_no), 'image/svg+xml',
                package, blob)
    svg_rid = slide.part.relate_to(part, RT.IMAGE)
    blip = pic._pic.blipFill.blip
    ext_lst = blip.find(qn('a:extLst'))
    if ext_lst is None:
        ext_lst = etree.SubElement(blip, qn('a:extLst'))
    ext = etree.SubElement(ext_lst, qn('a:ext'))
    ext.set('uri', '{96DAC541-7B7A-43D3-8B79-37D633B846F1}')
    svg_blip = etree.SubElement(ext, '{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip')
    svg_blip.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed',
                 svg_rid)


def build_pptx(snap, deck_lang, deck_dir, raster_paths, out_path, fplan=None,
               overrides=None):
    """overrides: {page_idx0: {'carrier':'svg'|'png','svg':path?,'png':path}}——
    L5 回验降级页整页替换（保真轨 SVG 载体优先，否则真值 PNG 满幅）。"""
    from pptx import Presentation
    from pptx.util import Emu, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE

    prs = Presentation()
    prs.slide_width = Emu(SLIDE_W_EMU)
    prs.slide_height = Emu(SLIDE_H_EMU)
    blank = prs.slide_layouts[6]
    overrides = overrides or {}
    stats = []
    for pi, page in enumerate(snap['pages']):
        slide = prs.slides.add_slide(blank)
        counts = {'text': 0, 'shape': 0, 'image': 0, 'bg': 0, 'chart': 0, 'raster': 0}
        if pi in overrides:
            ov = overrides[pi]
            pic = slide.shapes.add_picture(ov['png'], 0, 0,
                                           prs.slide_width, prs.slide_height)
            if ov.get('svg') and os.path.isfile(ov['svg']):
                add_svg_blip(slide, pic, ov['svg'], pi + 1, prs.part.package)
            stats.append({'slide_id': page['slide_id'], 'render_mode': page['render_mode'],
                          'counts': counts, 'charts': [], 'rasterized': [],
                          'fixes': page.get('fixes', []),
                          'overlap_resolved': [], 'uncovered': [],
                          'degraded_to': ov['carrier']})
            continue
        rasterized = []
        if page['render_mode'] != 'baked':
            bg = parse_color(page.get('background'))
            if bg:
                rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                              0, 0, prs.slide_width, prs.slide_height)
                rect.shadow.inherit = False
                _solid_fill_rgb(rect.fill, RGBColor(*bg[:3]), bg[3])
                rect.line.fill.background()
                counts['bg'] = 1

        # L3 原生 chart：ig 外的直接落 slide（在文本层之下），ig 内的随组发放
        pending_ig_charts = {}
        for ch in page.get('charts', []):
            if ch.get('ig'):
                pending_ig_charts.setdefault(ch['ig']['root'], []).append(ch)
            else:
                add_native_chart(slide.shapes, ch, RGBColor, Pt)
                counts['chart'] += 1

        # L4 信息图分组：ig 根首次出现时建 grpSp（组名 = slide_id·族名），
        # 组内待发放 chart 一并入组；z-order = DOM 序（先加的在底）
        groups = {}

        def group_for(ig):
            key = ig['root']
            if key not in groups:
                g = slide.shapes.add_group_shape()
                g.name = '%s·%s' % (page['slide_id'], ig['family'])
                groups[key] = g
                for ch in pending_ig_charts.pop(key, []):
                    add_native_chart(g.shapes, ch, RGBColor, Pt)
                    counts['chart'] += 1
            return groups[key]

        for item in page['items']:
            shapes = group_for(item['ig']).shapes if item.get('ig') else slide.shapes
            if item['kind'] == 'text':
                tb = add_text_item(shapes, item, deck_lang, RGBColor, Pt, PP_ALIGN, fplan)
                tb.name = 't%03d' % counts['text']
                counts['text'] += 1
            elif item['kind'] == 'shape':
                shp = add_shape_item(shapes, item, RGBColor, Pt)
                if shp is not None and hasattr(shp, 'name'):
                    shp.name = 's%03d' % counts['shape']
                counts['shape'] += 1
            elif item['kind'] == 'image':
                src = os.path.join(deck_dir, item['src'])
                if not os.path.isfile(src):
                    page['uncovered'].append('image-missing:' + item['src'])
                    continue
                shapes.add_picture(src,
                                   int(round(item['rect']['left'] * EMU_PER_PX)),
                                   int(round(item['rect']['top'] * EMU_PER_PX)),
                                   int(round(item['rect']['width'] * EMU_PER_PX)),
                                   int(round(item['rect']['height'] * EMU_PER_PX)))
                counts['image'] += 1
                if item.get('uncovered'):
                    page['uncovered'].append(item['uncovered'] + ':' + item['src'])
            elif item['kind'] == 'raster':
                path = item.get('rasterFile') or raster_paths.get(item.get('rasterIdx'))
                if not path or not os.path.isfile(path):
                    page['uncovered'].append('raster-missing:' + item.get('reason', '?'))
                    continue
                rr = item.get('box') or item['rect']
                shapes.add_picture(path,
                                   int(round(rr['left'] * EMU_PER_PX)),
                                   int(round(rr['top'] * EMU_PER_PX)),
                                   int(round(rr['width'] * EMU_PER_PX)),
                                   int(round(rr['height'] * EMU_PER_PX)))
                counts['raster'] += 1
                rasterized.append(item.get('reason', '?'))
        # ig 组内只剩 chart 的兜底（组内无其它成员时也要建组发放）
        for key, charts in pending_ig_charts.items():
            family = charts[0]['ig'].get('family', 'ig')
            g = slide.shapes.add_group_shape()
            g.name = '%s·%s' % (page['slide_id'], family)
            for ch in charts:
                add_native_chart(g.shapes, ch, RGBColor, Pt)
                counts['chart'] += 1
        stats.append({'slide_id': page['slide_id'], 'render_mode': page['render_mode'],
                      'counts': counts,
                      'charts': [{'kind': c['kind'], 'recipe': c.get('recipe'),
                                  'categories': len(c['categories']), 'verify': c.get('verify')}
                                 for c in page.get('charts', [])],
                      'rasterized': sorted(set(rasterized)),
                      'fixes': page.get('fixes', []),
                      'overlap_resolved': page.get('overlap_resolved', []),
                      'uncovered': sorted(set(page['uncovered']))})
    prs.save(out_path)
    return stats


def postflight(out_path, expect_pages):
    from pptx import Presentation
    prs = Presentation(out_path)
    slides = list(prs.slides)
    if len(slides) != expect_pages:
        raise ExportError('postflight 失败：pptx 重开页数 %d ≠ %d' % (len(slides), expect_pages))
    for i, s in enumerate(slides, 1):
        if len(s.shapes) == 0:
            raise ExportError('postflight 失败：第 %d 页零形状' % i)
    log('postflight 通过：%d 页' % expect_pages)


# ---------------------------------------------------------------------------
# C3 字体内嵌（pptx fntdata；机制参照 ppt-master pptx_package/builder.py 的
# embedded fonts roundtrip——它服务导入侧，我们主动写入；MIT 许可）
FONT_REL_TYPE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/font'
FONT_CONTENT_TYPE = 'application/x-fontdata'
PML = 'http://schemas.openxmlformats.org/presentationml/2006/main'


def _fsType_embeddable(fs_type):
    """fsType 许可闸【硬规则】：0（installable）/ 0x0004（preview&print）/
    0x0008（editable）才嵌；0x0002（restricted）及其余跳过。"""
    if fs_type == 0:
        return True
    if fs_type & 0x0002:
        return False
    return bool(fs_type & 0x0004 or fs_type & 0x0008)


def embed_fonts(pptx_path, embeds):
    """C3/F3 字体内嵌：embeds=[{'path','declare':[族名…],'slot'}]——
    以映射后族名注册（run 的 typeface 即族名，WPS 回退可预测、365 吃内嵌增强）；
    同一文件多族名共享同一 fntdata part（修孤儿件）。fsType 闸兜底复验。
    返回 {'embedded': [...], 'skipped': [...]} 或 None（无内嵌）。"""
    if not embeds:
        return None
    import zipfile
    result = {'embedded': [], 'skipped': []}
    path2part = {}   # path → part index
    payloads = []
    fam_slots = {}   # 族名 → {slot: part_idx}
    from fontTools.ttLib import TTFont
    for e in embeds:
        fp = e['path']
        try:
            font = TTFont(fp)
        except Exception:
            from fontTools.ttLib import TTCollection
            font = TTCollection(fp).fonts[0]
        fs_type = font['OS/2'].fsType if 'OS/2' in font else None
        font.close()
        if fs_type is None or not _fsType_embeddable(fs_type):
            result['skipped'].append({'file': os.path.basename(fp),
                                      'reason': 'fsType=%s 许可受限，不嵌' % fs_type})
            continue
        if fp not in path2part:
            path2part[fp] = len(payloads)
            with open(fp, 'rb') as f:
                payloads.append(f.read())
        for name in e['declare']:
            fam_slots.setdefault(name, {})[e.get('slot', 'regular')] = path2part[fp]
            result['embedded'].append({'file': os.path.basename(fp), 'family': name,
                                       'slot': e.get('slot', 'regular')})
    if not fam_slots:
        return result

    tmp = pptx_path + '.tmp'
    with zipfile.ZipFile(pptx_path) as zin, \
            zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        pres_xml = zin.read('ppt/presentation.xml').decode('utf-8')
        pres_rels = zin.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
        ct = zin.read('[Content_Types].xml').decode('utf-8')
        for item in zin.infolist():
            if item.filename in ('ppt/presentation.xml', 'ppt/_rels/presentation.xml.rels',
                                 '[Content_Types].xml'):
                continue
            zout.writestr(item, zin.read(item.filename))
        rid_nums = [int(m.group(1)) for m in re.finditer(r'Id="rId(\d+)"', pres_rels)]
        next_rid = max(rid_nums, default=0) + 1
        part_rid = []
        rel_add = []
        for i, payload in enumerate(payloads, 1):
            fname = 'font%d.fntdata' % i
            zout.writestr('ppt/fonts/' + fname, payload)
            rid = 'rId%d' % next_rid
            next_rid += 1
            rel_add.append('<Relationship Id="%s" Type="%s" Target="fonts/%s"/>'
                           % (rid, FONT_REL_TYPE, fname))
            part_rid.append(rid)
        lst = ['<p:embeddedFontLst>']
        for family, slots in fam_slots.items():
            lst.append('<p:embeddedFont><p:font typeface="%s"/>' % family)
            for slot in ('regular', 'bold', 'italic'):
                if slot in slots:
                    lst.append('<p:%s r:id="%s"/>' % (slot, part_rid[slots[slot]]))
            lst.append('</p:embeddedFont>')
        lst.append('</p:embeddedFontLst>')
        block = ''.join(lst)
        m = re.search(r'<p:(defaultTextStyle|extLst)[ >]', pres_xml)
        if m:
            pres_xml = pres_xml[:m.start()] + block + pres_xml[m.start():]
        else:
            pres_xml = pres_xml.replace('</p:presentation>', block + '</p:presentation>')
        if 'embedTrueTypeFonts' not in pres_xml:
            pres_xml = pres_xml.replace('<p:presentation ', '<p:presentation embedTrueTypeFonts="1" ', 1)
        pres_rels = pres_rels.replace('</Relationships>', ''.join(rel_add) + '</Relationships>')
        if 'fntdata' not in ct:
            ct = ct.replace('</Types>', '<Default Extension="fntdata" ContentType="%s"/></Types>'
                            % FONT_CONTENT_TYPE)
        zout.writestr('ppt/presentation.xml', pres_xml.encode('utf-8'))
        zout.writestr('ppt/_rels/presentation.xml.rels', pres_rels.encode('utf-8'))
        zout.writestr('[Content_Types].xml', ct.encode('utf-8'))
    os.replace(tmp, pptx_path)
    log('字体内嵌：%d 族入档（%s）' % (len(fam_slots), '、'.join(sorted(fam_slots))))
    return result


def _apply_cert_fixes(sess, snap, violations, work):
    """认证违规 → 快照模型自动修复（下一轮重建生效）。
    返回 (fixed_count, degrade_pages)。政策【硬规则】：纯文本块永不烙图——
    修复阶梯：挪位 → 缩字（fontScale 下限 0.85）→ 页级降级矢量件；
    烙图仅限装饰/形状/复杂视觉层。
    修复策略（按规则）：
      R1 单行水平溢出 → 放宽框宽到墨水宽×余量（至多 2 次，此后缩字）；
      R2 垂直溢出 → 框高 = 需求高 + 余量（至多 2 次，此后缩字）；
      R3 行内叠字 → lnSpcPct 抬升 +0.03（pct 模型下不该发生，防御性）；
      R4 墨水相碰 → 先纵向挪位（页底余量够）→ 缩字 2% 步进（下限 0.85）→
        页级降级（文本不烙图）；
      R4b 贴边 → 往形状中心方向挪出净距；R4c 骑缝 → 收进卡内或完整挪出；
      R4 形状压字 → 把文字挪到形状之后（z 序修正）。
    """
    degrade_pages = set()
    import math
    fixed = 0
    # 页 → 文本/形状 序列表（与 build 命名 t%03d/s%03d 对表）
    for v in violations:
        pg = snap['pages'][v['page'] - 1]
        texts = [it for it in pg['items'] if it['kind'] == 'text']

        def text_by_name(name):
            m = re.match(r't(\d+)$', name)
            if not m:
                return None
            i = int(m.group(1))
            return texts[i] if i < len(texts) else None

        if v['rule'] == 'R1-h-overflow':
            it = text_by_name(v['el'])
            if it is None:
                continue
            if it.get('_widened', 0) < 2:
                text = ''.join(r['text'] for l in (it.get('lines') or []) for r in l['runs'])
                margin = 1.15 if _punct_ratio(text) > 0.2 else 1.08
                it['box']['width'] = (v['ink_w_pt'] / PX_TO_PT) * margin
                it['_widened'] = it.get('_widened', 0) + 1
            else:
                fs = (it.get('fontScale') or 1.0) - 0.02
                if fs >= 0.90:
                    it['fontScale'] = fs
                else:
                    continue
            pg.setdefault('fixes', []).append({'rule': 'R1', 'text': v['text']})
            fixed += 1
        elif v['rule'] == 'R2-v-overflow':
            it = text_by_name(v['el'])
            if it is None:
                continue
            if it.get('_vfixed', 0) < 2:
                it['box']['height'] = (v['need_h_pt'] / PX_TO_PT) * 1.02 + 2
                it['_vfixed'] = it.get('_vfixed', 0) + 1
            else:
                fs = (it.get('fontScale') or 1.0) - 0.02
                if fs >= 0.90:
                    it['fontScale'] = fs
                else:
                    continue
            pg.setdefault('fixes', []).append({'rule': 'R2', 'text': v['text']})
            fixed += 1
        elif v['rule'] == 'R3-line-crash':
            it = text_by_name(v['el'])
            if it is None:
                continue
            it['lnSpcPct'] = max(it.get('lnSpcPct') or 1.0, 1.03) + 0.03
            pg.setdefault('fixes', []).append({'rule': 'R3', 'text': v['text']})
            fixed += 1
        elif v['rule'] in ('R4-ink-collision', 'R4b-margin-tight', 'R4c-edge-straddle'):
            names = re.findall(r't\d+', v['el'])
            its = [text_by_name(n) for n in names]
            its = [x for x in its if x is not None]
            if not its:
                continue
            # R4c/R4b 边缘问题：直接计算——收进卡内/挪出卡外 + 净距，或卡内装不下
            # 时按比例缩字（一轮收敛）；缩字 <0.85 才进页级降级
            if v['rule'] in ('R4b-margin-tight', 'R4c-edge-straddle') and v.get('shape_box'):
                it = its[0]
                sx, sy, sw, sh = [c * 2 for c in v['shape_box']]   # pt → 画布 px
                bx = it['box']
                M = 4.0
                if v['rule'] == 'R4b-margin-tight':
                    dx = max(0.0, (sx + M) - bx['left']) - max(0.0, (bx['left'] + bx['width']) - (sx + sw - M))
                    dy = max(0.0, (sy + M) - bx['top']) - max(0.0, (bx['top'] + bx['height']) - (sy + sh - M))
                    bx['left'] += dx
                    bx['top'] += dy
                    if it.get('ink_bottom'):
                        it['ink_bottom'] += dy
                    pg.setdefault('fixes', []).append({'rule': v['rule'], 'action': 'nudge-in',
                                                       'text': v['text'][:24]})
                    fixed += 1
                    continue
                # 骑缝：过半在内 → 收进卡内；过半在外 → 挪出；都不下 → 直接算缩字量
                inter_w = min(bx['left'] + bx['width'], sx + sw) - max(bx['left'], sx)
                inter_h = min(bx['top'] + bx['height'], sy + sh) - max(bx['top'], sy)
                inside_ratio = (max(0.0, inter_w) * max(0.0, inter_h)) / max(1.0, bx['width'] * bx['height'])
                ink_h = it.get('ink_h') or bx['height']
                ink_w = it.get('ink_w') or bx['width']
                done = False
                if inside_ratio > 0.5:
                    # 收进卡内：净距 4px；装不下（卡内净高不足）→ 直接缩字到装下
                    avail_h = sh - 2 * M
                    avail_w = sw - 2 * M
                    fs_now = it.get('fontScale') or 1.0
                    need_fs = min(avail_h / max(ink_h, 1), avail_w / max(ink_w, 1)) * fs_now
                    if need_fs >= 1.0:
                        bx['left'] = min(max(bx['left'], sx + M), sx + sw - bx['width'] - M)
                        bx['top'] = min(max(bx['top'], sy + M), sy + sh - bx['height'] - M)
                        done = True
                        action = 'nudge-in'
                    elif need_fs / fs_now >= 0.85:
                        it['fontScale'] = need_fs - 0.005
                        done = True
                        action = 'fontScale-fit'
                else:
                    # 挪出：四方向取最小合法位移
                    cands = []
                    cands.append((abs(bx['top'] + bx['height'] - sy) + M, {'top': sy - bx['height'] - M}))
                    cands.append((abs(sy + sh - bx['top']) + M, {'top': sy + sh + M}))
                    cands.append((abs(bx['left'] + bx['width'] - sx) + M, {'left': sx - bx['width'] - M}))
                    cands.append((abs(sx + sw - bx['left']) + M, {'left': sx + sw + M}))
                    cands = [c for c in cands
                             if 0 <= c[1].get('top', bx['top'])
                             and c[1].get('top', bx['top']) + bx['height'] <= 1080
                             and 0 <= c[1].get('left', bx['left'])]
                    if cands:
                        cands.sort(key=lambda c: c[0])
                        bx.update(cands[0][1])
                        if it.get('ink_bottom') and 'top' in cands[0][1]:
                            it['ink_bottom'] += 0  # top 已变，ink_bottom 随 box 联动即可
                            it['ink_bottom'] = bx['top'] + ink_h
                        done = True
                        action = 'nudge-out'
                if done:
                    pg.setdefault('fixes', []).append({'rule': v['rule'], 'action': action,
                                                       'text': v['text'][:24]})
                    fixed += 1
                    continue
                degrade_pages.add(v['page'] - 1)
                pg.setdefault('fixes', []).append({'rule': v['rule'],
                                                   'action': 'page-degrade-pending',
                                                   'text': v['text'][:24]})
                fixed += 1
                continue
            # 文-文碰撞：先纵向挪位（页底余量够才挪）；不够 → 直接算缩字量
            # （一步收敛，不再 2% 步进磨）；下限 0.85 → 页级降级
            if v['rule'] == 'R4-ink-collision' and len(its) == 2:
                a, bb = sorted(its, key=lambda it: it['box']['top'])
                if a.get('ink_bottom') and a['ink_bottom'] > bb['box']['top']:
                    overlap_px = a['ink_bottom'] - bb['box']['top']
                    need_shift = overlap_px + 1.0
                    if bb['box']['top'] + need_shift + bb['box']['height'] <= 1060:
                        bb['box']['top'] += need_shift
                        if bb.get('ink_bottom'):
                            bb['ink_bottom'] += need_shift
                        pg.setdefault('fixes', []).append(
                            {'rule': v['rule'], 'action': 'shift-down',
                             'text': v['text'][:24], 'shift_px': round(need_shift, 1)})
                        fixed += 1
                        continue
                    # 页底没空间 → 缩字到恰好不碰（一步收敛）
                    ink_h = a.get('ink_h') or a['box']['height']
                    fs_now = a.get('fontScale') or 1.0
                    need_fs = (a['ink_bottom'] - overlap_px - a['box']['top']) / max(ink_h, 1) * fs_now
                    if need_fs >= 0.85:
                        a['fontScale'] = max(need_fs - 0.005, 0.85)
                        if a.get('ink_bottom'):
                            a['ink_bottom'] = a['box']['top'] + ink_h * a['fontScale'] / fs_now
                        pg.setdefault('fixes', []).append(
                            {'rule': v['rule'], 'action': 'fontScale',
                             'text': v['text'][:24], 'scale': round(a['fontScale'], 3)})
                        fixed += 1
                        continue
                    degrade_pages.add(v['page'] - 1)
                    pg.setdefault('fixes', []).append({'rule': v['rule'],
                                                       'action': 'page-degrade-pending',
                                                       'text': v['text'][:24]})
                    fixed += 1
                    continue
            # 非纵向结构（横碰等）：缩字一步
            later = its[-1]
            fs_now = later.get('fontScale') or 1.0
            if fs_now - 0.1 >= 0.85:
                later['fontScale'] = fs_now - 0.1
                if later.get('ink_bottom'):
                    later['ink_bottom'] = later['box']['top'] + \
                        (later.get('ink_h') or later['box']['height']) * later['fontScale'] / fs_now
                pg.setdefault('fixes', []).append({'rule': v['rule'], 'action': 'fontScale',
                                                   'text': v['text'][:24],
                                                   'scale': round(later['fontScale'], 3)})
                fixed += 1
            else:
                degrade_pages.add(v['page'] - 1)
                pg.setdefault('fixes', []).append({'rule': v['rule'],
                                                   'action': 'page-degrade-pending',
                                                   'text': v['text'][:24]})
                fixed += 1
        elif v['rule'] == 'R4-shape-covers-text':
            m = re.search(r'压 (t\d+)$', v['el'])
            it = text_by_name(m.group(1)) if m else None
            if it is None:
                continue
            # z 序修正：文字挪到页内元素尾部（压过形状）
            pg['items'].remove(it)
            pg['items'].append(it)
            pg.setdefault('fixes', []).append({'rule': 'R4', 'action': 'z-bump',
                                               'text': v['text']})
            fixed += 1
    return fixed, sorted(degrade_pages)


def run_export(deck_html, out_path, vector_dir=None, embed_fonts_enabled=True,
               verify=True):
    """可编辑轨全流程（供 CLI 与 export-pptx.py 双轨编排调用）。
    五层加固（0924）：L1 字体随档默认化（fc-match→子集化→fntdata 内嵌，
    失败进余量加强模式）→ L2 行高/基线校准（hhea 实测）→ L3 松配合
    （+1 行/×1.02/单行禁折行）→ L4 几何自净（相交扫描：收余量→烙图，
    零残留）→ L5 LO 回验 + 逐页降级（超标页换保真轨 svgBlip 载体，
    vector_dir 无矢量件时退真值 PNG 满幅）。
    vector_dir：保真轨 export/ 目录（逐页降级借 page-NN.svg/png）。
    返回 report dict；失败抛 ExportError。产物：out_path + 同名 .report.json。"""
    deck_html = os.path.abspath(deck_html)
    deck_dir = os.path.dirname(deck_html)
    if not os.path.isfile(deck_html):
        raise ExportError('deck 不存在：%s' % deck_html)
    out_path = os.path.abspath(out_path)
    report_path = os.path.splitext(out_path)[0] + '.report.json'

    hash_before = sha256_file(deck_html)
    t0 = datetime.now(timezone.utc)
    work = tempfile.mkdtemp(prefix='pptx-editable-')
    try:
        with RenderSession(deck_html) as sess:
            snap, deck_lang = sess.snapshot()
            n_pages = len(snap['pages'])
            raster_paths = sess.screenshot_marked(work)
            truth = sess.capture_truth(work)          # L5 回验基准 + PNG 降级源
            log('快照完成：%d 页（lang=%s，烙图 %d 件）' % (n_pages, deck_lang, len(raster_paths)))
            # 页背景渐变/纹理烙底：slide 全体后代隐藏后截整页底（纯背景），
            # 置 items 最底（z-order 最下），文字/形状/图片仍原生叠加
            slide_els = sess.page.query_selector_all('section.slide')
            for pi, pg in enumerate(snap['pages']):
                if pg.get('bg_gradient') and pg.get('render_mode') != 'baked':
                    el = slide_els[pi]
                    path = os.path.join(work, 'bg-%02d.png' % (pi + 1))
                    sess.page.evaluate("(e) => e.querySelectorAll('*').forEach("
                                       "t => t.style.visibility = 'hidden')", el)
                    el.screenshot(path=path)
                    sess.page.evaluate("(e) => e.querySelectorAll('*').forEach("
                                       "t => t.style.visibility = '')", el)
                    pg['items'].insert(0, {'kind': 'raster', 'rect': {'left': 0, 'top': 0, 'width': 1920, 'height': 1080},
                                           'reason': 'page-gradient-bg', 'rasterFile': path, 'ig': None})
            fplan = plan_fonts(snap, deck_lang, deck_dir, work, embed_fonts_enabled)
            for note in fplan['notes']:
                log('字体：%s' % note)
            apply_layout(snap, fplan)                 # L2 + L3
            # F4′ 认证-修复环（出厂硬门禁【硬规则】）：组装 → certify 纯计算
            # 认证 → 违规自动修复（放宽/缩字/烙图）→ 重认证 → 修不净的页
            # 降级矢量件（双轨同跑借 page-NN.svg，单轨退真值 PNG 满幅）→
            # 全过才继续。测试钩子：PPTX_EXPORT_FORCE_DEGRADE=<slide_id>。
            tmp_pptx = os.path.join(work, 'deck.pptx')
            stats = None
            cert = None
            total_fixes = 0
            overrides = {}
            force_deg = os.environ.get('PPTX_EXPORT_FORCE_DEGRADE')
            if force_deg:
                for i, pg in enumerate(snap['pages']):
                    if pg['slide_id'] == force_deg:
                        overrides[i] = {'carrier': 'png', 'png': truth[i], 'svg': None}
                        log('测试钩子：强制降级 %s' % force_deg)
            cert_rounds = 0
            last_n = None
            stall = 0
            for rnd in range(12):
                cert_rounds = rnd + 1
                stats = build_pptx(snap, deck_lang, deck_dir, raster_paths, tmp_pptx,
                                   fplan, overrides=overrides)
                cert = _certify_mod.certify(tmp_pptx)
                if cert['ok']:
                    break
                cur_n = len(cert['violations'])
                if last_n is not None and cur_n >= last_n:
                    stall += 1
                else:
                    stall = 0
                last_n = cur_n
                n_fix, degs = _apply_cert_fixes(sess, snap, cert['violations'], work)
                total_fixes += n_fix
                # 结构性超容页（修复震荡两轮不降）→ 残留页整体页级降级，
                # 不再用局部位移在卡片缝间振荡
                if stall >= 2 or not n_fix:
                    extra = sorted({v['page'] - 1 for v in cert['violations']
                                    if (v['page'] - 1) not in overrides})
                    for di in extra:
                        if di not in degs:
                            degs.append(di)
                    degs = sorted(set(degs))
                for di in degs:
                    if di not in overrides:
                        png = truth[di]
                        svg = None
                        if vector_dir:
                            cand_svg = os.path.join(vector_dir, 'page-%02d.svg' % (di + 1))
                            cand_png = os.path.join(vector_dir, 'page-%02d.png' % (di + 1))
                            if os.path.isfile(cand_svg) and os.path.isfile(cand_png):
                                svg, png = cand_svg, cand_png
                        overrides[di] = {'carrier': 'svg' if svg else 'png', 'png': png,
                                         'svg': svg}
                        log('文本修不净 → 页降级（政策：文本不烙图）：%s（%s 载体）'
                            % (snap['pages'][di]['slide_id'], 'svgBlip' if svg else 'PNG'))
                if n_fix:
                    continue
                # 修不动 → 页级降级（矢量件优先）
                bad = sorted({v['page'] for v in cert['violations']
                              if (v['page'] - 1) not in overrides})
                if not bad:
                    break
                for pno in bad:
                    i = pno - 1
                    png = truth[i]
                    svg = None
                    if vector_dir:
                        cand_svg = os.path.join(vector_dir, 'page-%02d.svg' % pno)
                        cand_png = os.path.join(vector_dir, 'page-%02d.png' % pno)
                        if os.path.isfile(cand_svg) and os.path.isfile(cand_png):
                            svg, png = cand_svg, cand_png
                    overrides[i] = {'carrier': 'svg' if svg else 'png', 'png': png, 'svg': svg}
                    log('认证修不净 → 页降级：%s（%s 载体）'
                        % (snap['pages'][i]['slide_id'], 'svgBlip' if svg else 'PNG'))
            # 环末兜底：仍有违规 → 残留页全部页级降级 → 重建 → 终认证
            if cert is not None and not cert['ok']:
                for pno in sorted({v['page'] for v in cert['violations']
                                   if (v['page'] - 1) not in overrides}):
                    i = pno - 1
                    png = truth[i]
                    svg = None
                    if vector_dir:
                        cand_svg = os.path.join(vector_dir, 'page-%02d.svg' % pno)
                        cand_png = os.path.join(vector_dir, 'page-%02d.png' % pno)
                        if os.path.isfile(cand_svg) and os.path.isfile(cand_png):
                            svg, png = cand_svg, cand_png
                    overrides[i] = {'carrier': 'svg' if svg else 'png', 'png': png, 'svg': svg}
                    log('环末兜底页降级：%s（%s 载体）'
                        % (snap['pages'][i]['slide_id'], 'svgBlip' if svg else 'PNG'))
                if overrides:
                    stats = build_pptx(snap, deck_lang, deck_dir, raster_paths, tmp_pptx,
                                       fplan, overrides=overrides)
                    cert = _certify_mod.certify(tmp_pptx)
                    cert_rounds += 1
            if cert is None or not cert['ok']:
                raise ExportError('认证修复环未收敛，残留违规 %d 项——不产半成品'
                                  % (len(cert['violations']) if cert else -1))
            degraded_pages = [{'slide_id': snap['pages'][i]['slide_id'],
                               'carrier': overrides[i]['carrier'],
                               'reason': 'forced(测试钩子)' if snap['pages'][i]['slide_id'] == force_deg
                               else 'certify-unfixable'} for i in sorted(overrides)]
            log('认证 PASS：修复 %d 处 / 降级 %d 页 / %d 轮'
                % (total_fixes, len(overrides), cert_rounds))

        fonts_report = embed_fonts(tmp_pptx, fplan['embeds'])
        if any(o.get('svg') for o in overrides.values()):
            _epx.patch_content_types(tmp_pptx)
        postflight(tmp_pptx, n_pages)
        # 内嵌后终认证（包结构变化保守复核）
        cert2 = _certify_mod.certify(tmp_pptx)
        if not cert2['ok']:
            raise ExportError('内嵌后终认证失败 %d 项——不产半成品' % len(cert2['violations']))

        # L5 参考通道（降级为参考读数，不作门禁——门禁已由 F4′ 数学认证承担）
        verify_report = {'status': 'skipped', 'note': '--skip-verify'}
        if verify:
            v = lo_verify(tmp_pptx, truth, work, snap)
            v['role'] = 'reference（视觉 QA 参考口径，非门禁；门禁=数学认证）'
            verify_report = v
            if v.get('status') == 'done':
                diffs = v['page_diffs']
                log('LO 参考渲染：平均 diff %.2f%%，最大 %.2f%%（参考口径，不作门禁）'
                    % (sum(d['diff_pct'] for d in diffs) / max(1, len(diffs)),
                       max((d['diff_pct'] for d in diffs), default=0)))

        if sha256_file(deck_html) != hash_before:
            raise ExportError('单向纪律违反：导出过程中 index.html 发生变化')

        # 覆盖率与字体告警（页级降级页的文字整页随图，不计入分母）
        degraded_ids = {snap['pages'][i]['slide_id'] for i in overrides}
        n_text = sum(s['counts']['text'] for s in stats)
        n_text_leaves = sum(
            len([it for it in p['items'] if it['kind'] == 'text'])
            for p in snap['pages'] if p['slide_id'] not in degraded_ids)
        ig_native = sum(len([it for it in p['items'] if it['kind'] == 'text' and it.get('ig')])
                        for p in snap['pages'] if p['slide_id'] not in degraded_ids)
        ig_total = sum(p.get('igTextTotal', 0) for p in snap['pages']
                       if p['slide_id'] not in degraded_ids)
        unsafe = {}
        for p in snap['pages']:
            for it in p['items']:
                if it['kind'] == 'text':
                    ff = it['style']['fontFamily']
                    for role, family in parse_font_family(ff, deck_lang).items():
                        if family.strip().lower() not in PPT_SAFE_FONTS:
                            unsafe.setdefault(ff, parse_font_family(ff, deck_lang))
        report = {
            'deck': deck_html,
            'generated_at': t0.isoformat(),
            'exporter': 'export-pptx-editable.py (C3)',
            'out': out_path,
            'pages': stats,
            'items': [{'slide_id': p['slide_id'],
                       'items': [{'kind': it['kind'], 'rect': it['rect'],
                                  'box': it.get('box'), 'wrap': it.get('wrap'),
                                  'burned_text': it.get('burned_text'),
                                  'fontSizePx': it['style']['fontSizePx'] if it['kind'] == 'text' else None,
                                  'first_text': (it.get('lines') or [{}])[0].get('runs', [{}])[0].get('text', '')[:40]
                                  if it['kind'] == 'text' else ''}
                                 for it in p['items']]}
                      for p in snap['pages']],
            'totals': {
                'text': n_text,
                'shape': sum(s['counts']['shape'] for s in stats),
                'image': sum(s['counts']['image'] for s in stats),
                'chart': sum(s['counts']['chart'] for s in stats),
                'raster': sum(s['counts']['raster'] for s in stats),
            },
            'native_text_ratio': 1.0 if n_text_leaves == 0 else round(n_text / n_text_leaves, 4),
            'native_infographic_ratio': (1.0 if ig_total == 0
                                         else round(ig_native / ig_total, 4)),
            'fonts_embedded': (fonts_report or {}).get('embedded'),
            'fonts_skipped': (fonts_report or {}).get('skipped'),
            'fonts_note': ('字体未随档——%s' % '；'.join(fplan['notes'])
                           if fonts_report is None else None),
            'margin_mode': fplan['margin_mode'],
            'font_plan': fplan['notes'],
            'verify': verify_report,
            'certify': {'ok': cert['ok'], 'rounds': cert_rounds, 'fixes': total_fixes},
            'degraded_pages': degraded_pages,
            'unsafe_fonts': unsafe,
        }
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        shutil.move(tmp_pptx, out_path)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write('\n')

        # LO 参考渲染页图持久化（编辑器"原生 PPTX 预览"消费；
        # 无 soffice / --skip-verify 时缺省——诚实降级，不伪造）
        lo_dir = os.path.join(work, 'lo')
        if os.path.isdir(lo_dir):
            native_dir = os.path.join(os.path.dirname(out_path), 'native')
            saved = 0
            for fn in sorted(os.listdir(lo_dir)):
                if fn.startswith('lo-') and fn.endswith('.png'):
                    os.makedirs(native_dir, exist_ok=True)
                    shutil.copy(os.path.join(lo_dir, fn),
                                os.path.join(native_dir, 'page-' + fn[3:]))
                    saved += 1
            if saved:
                report['native_preview'] = 'native/page-NN.png（LibreOffice 参考渲染，非真实 PowerPoint）'
                log('原生预览页图已持久化：%s（%d 页，LO 参考渲染）' % (native_dir, saved))

        dt = (datetime.now(timezone.utc) - t0).total_seconds()
        log('导出完成：%s（%d 页，文本 %d 框 / 形状 %d / 图片 %d / 原生图表 %d / 烙图 %d，耗时 %.1fs）'
            % (out_path, n_pages, report['totals']['text'],
               report['totals']['shape'], report['totals']['image'],
               report['totals']['chart'], report['totals']['raster'], dt))
        report['elapsed_s'] = round(dt, 1)
        v = report.get('verify') or {}
        if v.get('status') == 'done':
            log('LO 参考渲染回验完成（参考口径，不作门禁）')
        return report
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description='可编辑 PPTX 导出（三形态子技能 C）')
    ap.add_argument('deck', help='deck 的 index.html 路径')
    ap.add_argument('--out', help='输出 pptx 路径（缺省 <deck>/export/deck-editable.pptx）')
    ap.add_argument('--no-embed-fonts', action='store_true',
                    help='关闭字体随档（L1），回退映射 + 余量加强模式')
    ap.add_argument('--skip-verify', action='store_true',
                    help='关闭 L5 LO 回验（报告标注 verify=skipped）')
    args = ap.parse_args()

    deck_html = os.path.abspath(args.deck)
    if not os.path.isfile(deck_html):
        print('deck 不存在：%s' % deck_html, file=sys.stderr)
        return 1
    out_path = os.path.abspath(args.out) if args.out else \
        os.path.join(os.path.dirname(deck_html), 'export', 'deck-editable.pptx')
    try:
        report = run_export(deck_html, out_path,
                            embed_fonts_enabled=not args.no_embed_fonts,
                            verify=not args.skip_verify)
        print(json.dumps({'ok': True, 'out': out_path,
                          'report': os.path.splitext(out_path)[0] + '.report.json',
                          'pages': len(report['pages']), 'totals': report['totals'],
                          'native_text_ratio': report['native_text_ratio'],
                          'native_infographic_ratio': report['native_infographic_ratio'],
                          'fonts_embedded': report['fonts_embedded'],
                          'elapsed_s': report['elapsed_s']}, ensure_ascii=False, indent=2))
        return 0
    except ExportError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
