#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三形态公共地基 M1：manifest 提取器（docs/design/tri-form-architecture.md §4）。

用法：
  python3 scripts/extract-manifest.py <deck/index.html> [--out manifest.json] [--write-hashes]

行为：
  无头 Chromium 渲染 deck（file:// 直开，1920×1080），先调骨架的
  window.__pptxMotion.freeze() 与 restoreAll()（存在才调）并等待动效静止，
  再逐页提取 texts/images/content_hash（"净化后 DOM"语义，契约 §5.4）。

content-hash 算法【与 editor.html 保存路径双端一致，逐字节同构】：
  对每页构造 canonical string——
    第 1 行 slide_id，第 2 行 render_mode（缺省 "html"）；
    随后按文档序每个 [data-editable] 叶一行：T: + 规范化文本
    （trim + 连续空白折叠为单个空格）；
    随后按文档序每个 img[data-editable-image] 一行：
    I: + slot|intent|state|src；
  全部行以 \\n 连接，UTF-8 编码，SHA-256 取前 12 个 hex 字符。
  canonical string 构造函数 CANONICAL_JS 与 editor.html 内的
  pptxCanonicalString/pptxNormText/pptxContentHash 逐字一致，改动必须两端同步。

--write-hashes：把算出的 hash 写回 deck 文件每个 <section class="slide">
  的 data-content-hash 属性（属性级精准替换，不重序列化文档）。

幂等：同一 deck 连续提取两次，stdout JSON 除 extracted_at 外字节一致。
退出码：成功 0，任一失败 1。
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

# 主题 token 读取清单（themes/index.md G1 六色 + -tint/-on 变体位 + 多色扩展位
# --accent-2/3（含 -on 配对）与旧谱 --accent2/--paper2/--ink2；存在的才进 manifest）
THEME_TOKENS = ['--paper', '--paper-tint', '--paper2',
                '--ink', '--ink-tint', '--ink2',
                '--accent', '--accent-on', '--accent2',
                '--accent-2', '--accent-2-on', '--accent-3', '--accent-3-on']

# canonical string 构造函数【双端一致锚】：editor.html 内有逐字相同的副本。
CANONICAL_JS = r"""
function pptxNormText(s){
  return (s || '').replace(/\s+/g, ' ').trim();
}
function pptxCanonicalString(slide){
  var lines = [];
  lines.push(slide.getAttribute('data-slide-id') || '');
  lines.push(slide.getAttribute('data-render-mode') || 'html');
  Array.prototype.forEach.call(slide.querySelectorAll('[data-editable]'), function(el){
    lines.push('T:' + pptxNormText(el.textContent));
  });
  Array.prototype.forEach.call(slide.querySelectorAll('img[data-editable-image]'), function(img){
    lines.push('I:' + (img.getAttribute('data-image-slot') || '') + '|' +
      (img.getAttribute('data-image-intent') || '') + '|' +
      (img.getAttribute('data-image-state') || '') + '|' +
      (img.getAttribute('src') || ''));
  });
  return lines.join('\n');
}
async function pptxContentHash(slide){
  var buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(pptxCanonicalString(slide)));
  var hex = Array.prototype.map.call(new Uint8Array(buf), function(b){
    return ('0' + b.toString(16)).slice(-2);
  }).join('');
  return hex.slice(0, 12);
}
"""

# 提取主逻辑：role 推导（总览 §4.5 确定优先级）+ 行数/排版宽度快照 + hash。
EXTRACT_JS = r"""
async (tokens) => {
""" + CANONICAL_JS + r"""
  /* 标注层口径（typography §5）：mono 字体 + 12–16px 档 */
  function isAnnotation(el){
    var cs = getComputedStyle(el);
    var fs = parseFloat(cs.fontSize);
    return /mono/i.test(cs.fontFamily) && fs >= 12 && fs < 17;
  }
  /* 真实行数：逐文本节点 Range.getClientRects()，按行盒 top 聚类（1px 容差） */
  function lineCountOf(el){
    var tops = [];
    var tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    var n;
    while ((n = tw.nextNode())){
      if (!n.nodeValue) continue;
      var r = document.createRange();
      r.selectNodeContents(n);
      var rs = r.getClientRects();
      for (var i = 0; i < rs.length; i++){
        if (rs[i].height > 0) tops.push(rs[i].top);
      }
    }
    if (!tops.length) return pptxNormText(el.textContent) ? 1 : 0;
    tops.sort(function(a, b){ return a - b; });
    var count = 1;
    for (var j = 1; j < tops.length; j++){
      if (tops[j] - tops[j - 1] > 1) count++;
    }
    return count;
  }
  var scale = parseFloat(document.documentElement.style.getPropertyValue('--slide-scale')) || 1;
  var rootCs = getComputedStyle(document.documentElement);
  var themeTokens = {};
  tokens.forEach(function(t){
    var v = rootCs.getPropertyValue(t).trim();
    if (v) themeTokens[t] = v;
  });
  var metaTheme = document.querySelector('meta[name="theme-id"]');
  var metaVariant = document.querySelector('meta[name="theme-variant"]');
  var metaSkel = document.querySelector('meta[name="skeleton-version"]');
  var out = {
    deck: {
      title: document.title || '',
      skeleton_version: metaSkel ? metaSkel.content : null,
    },
    theme: {
      id: metaTheme ? metaTheme.content : null,
      variant: metaVariant ? metaVariant.content : null,
      tokens: themeTokens,
    },
    pages: [],
  };
  var slides = Array.from(document.querySelectorAll('section.slide'));
  for (var s = 0; s < slides.length; s++){
    var slide = slides[s];
    var els = Array.from(slide.querySelectorAll('[data-editable]'));
    /* 页内最大字阶（furniture/annotation 之外）→ title；同字阶并列皆 title */
    var maxFs = 0;
    els.forEach(function(el){
      if (el.closest('.masthead,.mastfoot') || isAnnotation(el)) return;
      maxFs = Math.max(maxFs, parseFloat(getComputedStyle(el).fontSize));
    });
    var texts = els.map(function(el){
      var role;
      if (el.closest('.masthead,.mastfoot')) role = 'furniture';
      else if (isAnnotation(el)) role = 'annotation';
      else if (parseFloat(getComputedStyle(el).fontSize) === maxFs) role = 'title';
      else role = 'body';
      return {
        role: role,
        content: pptxNormText(el.textContent),
        line_count: lineCountOf(el),
        advance_width: Math.round(el.getBoundingClientRect().width / scale * 10) / 10,
      };
    });
    var images = Array.from(slide.querySelectorAll('img[data-editable-image]')).map(function(img){
      return {
        slot: img.getAttribute('data-image-slot') || null,
        intent: img.getAttribute('data-image-intent') || null,
        state: img.getAttribute('data-image-state') || null,
        src: img.getAttribute('src') || '',
      };
    });
    out.pages.push({
      slide_id: slide.getAttribute('data-slide-id') || '',
      render_mode: slide.getAttribute('data-render-mode') || 'html',
      chapter: slide.getAttribute('data-chapter') || null,
      texts: texts,
      images: images,
      content_hash: await pptxContentHash(slide),
    });
  }
  return out;
}
"""


def extract(deck_path):
    """渲染 deck 并提取 manifest（extracted_at 由调用方补，便于幂等比较）。"""
    url = 'file://' + os.path.abspath(deck_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.goto(url)
        page.wait_for_timeout(800)
        n = page.evaluate("document.querySelectorAll('.slide-slot').length")
        # 逐页滚入触发入场/运行时动效，再等其完成（对齐 check-render 口径）
        for i in range(n):
            page.evaluate(
                "(i) => document.querySelectorAll('.slide-slot')[i].scrollIntoView({block:'start'})", i)
            page.wait_for_timeout(200)
        page.wait_for_timeout(2600)
        # 净化后 DOM 语义（契约 §5.4）：freeze 交互层 + restoreAll 终值还原
        page.evaluate("""() => {
          var m = window.__pptxMotion;
          if (m){
            if (typeof m.freeze === 'function') m.freeze();        // v5+ 才有 freeze
            if (typeof m.restoreAll === 'function') m.restoreAll();
          }
        }""")
        # content-visibility:auto 下远屏页不排版——强制全部排版再测量行数/宽度
        page.evaluate("""() => document.querySelectorAll('.slide-slot')
          .forEach(s => s.style.contentVisibility = 'visible')""")
        page.wait_for_timeout(400)
        manifest = page.evaluate(EXTRACT_JS, THEME_TOKENS)
        browser.close()
    return manifest


def write_hashes(deck_path, pages):
    """把页级 hash 写回 <section class="slide"> 的 data-content-hash 属性。
    属性级精准替换：只动含 data-slide-id 的那个开始标签，不重序列化文档。"""
    with open(deck_path, encoding='utf-8') as f:
        text = f.read()
    n_written = 0
    for p in pages:
        sid = p['slide_id']
        h = p['content_hash']
        pat = re.compile(r'<section\b[^>]*\bdata-slide-id="%s"[^>]*>' % re.escape(sid))
        m = pat.search(text)
        if not m:
            raise SystemExit('write-hashes 失败：找不到 slide_id=%r 的 <section> 开始标签' % sid)
        tag = m.group(0)
        if re.search(r'\bdata-content-hash="[^"]*"', tag):
            new_tag = re.sub(r'\bdata-content-hash="[^"]*"',
                             'data-content-hash="%s"' % h, tag)
        else:
            new_tag = tag[:-1] + ' data-content-hash="%s">' % h
        text = text[:m.start()] + new_tag + text[m.end():]
        n_written += 1
    with open(deck_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return n_written


def main():
    ap = argparse.ArgumentParser(description='manifest 提取器（三形态 M1）')
    ap.add_argument('deck', help='deck 的 index.html 路径')
    ap.add_argument('--out', help='manifest JSON 输出路径（缺省写 stdout）')
    ap.add_argument('--write-hashes', action='store_true',
                    help='把页级 content-hash 写回 deck 的 data-content-hash 属性')
    args = ap.parse_args()

    deck_path = os.path.abspath(args.deck)
    if not os.path.isfile(deck_path):
        print('deck 不存在：%s' % deck_path, file=sys.stderr)
        return 1

    manifest = extract(deck_path)
    manifest['deck']['extracted_at'] = datetime.now(timezone.utc).isoformat()

    if args.write_hashes:
        n = write_hashes(deck_path, manifest['pages'])
        print('已写回 %d 页 data-content-hash：%s' % (n, deck_path), file=sys.stderr)

    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
        print('manifest 已写入：%s（%d 页）' % (args.out, len(manifest['pages'])), file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
