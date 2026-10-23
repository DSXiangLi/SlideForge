#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
防线 A 最小落地：字体子集化（docs/design/pptx-export-svg.md §4.2）。

用法：
  python3 scripts/subset-fonts.py <deck/index.html> \
      --font "Noto Sans SC=/path/to/NotoSansSC.ttf" [--font "Family=path" ...]
      [--inject] [--out-dir <deck>/fonts]

行为：
  1. 子进程跑 extract-manifest.py 取全 deck 真实用字（渲染后提取，含编辑器
     改过的最新文本——比静态解析 HTML 可靠）；
  2. 每个 --font 映射按用字集子集化 → fonts/<family-slug>.woff2
     （本环境无 brotli 时诚实降级为 .ttf 并在 stderr 声明——woff2 需要
     fontTools[woff] 即 brotli 压缩支持）；
  3. 输出可粘贴进骨架 SLOT: fonts 的 @font-face CSS 块（stdout）；
     --inject 时直接写入 deck 的 fonts SLOT 标记区间
     （__FONTS_SLOT_BEGIN__ … __FONTS_SLOT_END__ 注释标记区间，骨架 v7.4 起）。
     注入是幂等的：区间内容整体替换。

注意：字体的许可合规（OFL 等可再分发许可）是选字时的责任，脚本不审查。
退出码：成功 0，任一失败 1。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
EXTRACT_MANIFEST = os.path.join(ROOT, 'skills/html-pptx/scripts/extract-manifest.py')

SLOT_BEGIN = '/*__FONTS_SLOT_BEGIN__*/'
SLOT_END = '/*__FONTS_SLOT_END__*/'


def log(msg):
    print('[subset-fonts] %s' % msg, file=sys.stderr)


def deck_charset(deck_html):
    """全 deck 真实用字集（渲染后提取）。"""
    work = tempfile.mkdtemp(prefix='pptx-subset-')
    try:
        out = os.path.join(work, 'm.json')
        r = subprocess.run([sys.executable, EXTRACT_MANIFEST, deck_html, '--out', out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit('manifest 提取失败：%s%s' % (r.stdout, r.stderr))
        with open(out, encoding='utf-8') as f:
            manifest = json.load(f)
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    text = ''.join(t.get('content') or ''
                   for p in manifest['pages'] for t in p.get('texts', []))
    # alt 文本也是用户可见内容的语义备份，一并纳入（图片槽位 intent 不进——
    # 它是给生图的说明，不渲染）
    charset = ''.join(sorted({c for c in text if not c.isspace()}))
    log('全 deck 用字 %d 个（%d 页）' % (len(charset), len(manifest['pages'])))
    return charset


def slugify(family):
    return re.sub(r'[^a-z0-9]+', '-', family.lower()).strip('-')


def subset_one(family, font_path, charset, out_dir, fmt_choice='auto'):
    """子集化单个字体，返回 (输出文件名, 字重, 格式, 字节数)。
    fmt_choice：auto（有 brotli 出 woff2，否则 ttf）/ woff2 / ttf。
    ttf 是 pptx fntdata 字体内嵌的唯一形态（C3）；woff2 仅供 HTML 侧使用。"""
    from fontTools import subset
    from fontTools.ttLib import TTFont

    if not os.path.isfile(font_path):
        raise SystemExit('字体文件不存在：%s' % font_path)
    try:
        font = TTFont(font_path)
    except Exception:
        # .ttc 集合：取 0 号字体并声明
        from fontTools.ttLib import TTCollection
        coll = TTCollection(font_path)
        font = coll.fonts[0]
        log('%s 是 TTC 集合（%d 款）——取 0 号字体' % (font_path, len(coll.fonts)))
    weight = font['OS/2'].usWeightClass if 'OS/2' in font else 400

    has_brotli = True
    try:
        import brotli  # noqa: F401
    except ImportError:
        has_brotli = False
    if fmt_choice == 'woff2' and not has_brotli:
        raise SystemExit('--format woff2 需要 brotli（pip install brotli）')
    if fmt_choice == 'ttf' or (fmt_choice == 'auto' and not has_brotli):
        flavor, ext, fmt = None, '.ttf', 'truetype'
        if fmt_choice == 'auto':
            log('未安装 brotli——%s 降级输出 .ttf（woff2 需 pip install brotli）' % family)
    else:
        flavor, ext, fmt = 'woff2', '.woff2', 'woff2'

    opts = subset.Options()
    opts.flavor = flavor
    opts.layout_features = ['*']      # 保留排版特性（kern/liga 等）
    opts.hinting = True
    opts.desubroutinize = False

    sub = subset.Subsetter(options=opts)
    sub.populate(text=charset)
    sub.subset(font)
    if flavor:
        font.flavor = flavor

    os.makedirs(out_dir, exist_ok=True)
    name = slugify(family) + ext
    out_path = os.path.join(out_dir, name)
    font.save(out_path)
    font.close()
    size = os.path.getsize(out_path)
    log('%s：%d 字 → %s（%.1f KB，字重 %d，%s）' % (family, len(charset), name, size / 1024, weight, fmt))
    return name, weight, fmt, size


def font_face_block(entries, out_dir, deck_dir):
    """entries: [(family, filename, weight, fmt)]。src 用相对 deck 根的路径。"""
    lines = []
    for family, filename, weight, fmt in entries:
        rel = os.path.relpath(os.path.join(out_dir, filename), deck_dir)
        rel = rel.replace(os.sep, '/')
        lines.append(
            "@font-face{font-family:'%s';src:url('%s') format('%s');"
            "font-weight:%d;font-display:swap}" % (family, rel, fmt, weight))
    return '\n'.join(lines)


def inject(deck_html, block):
    """把 @font-face 块写入骨架 fonts SLOT 标记区间（幂等整体替换）。"""
    with open(deck_html, encoding='utf-8') as f:
        text = f.read()
    if SLOT_BEGIN not in text or SLOT_END not in text:
        raise SystemExit('deck 无 fonts SLOT 标记（骨架 v7.4 起才有）——'
                         '请手工把 @font-face 块贴入 SLOT: fonts')
    pat = re.compile(re.escape(SLOT_BEGIN) + r'.*?' + re.escape(SLOT_END), re.S)
    new = pat.sub(SLOT_BEGIN + '\n' + block + '\n' + SLOT_END, text, count=1)
    with open(deck_html, 'w', encoding='utf-8') as f:
        f.write(new)
    log('已注入 fonts SLOT：%s' % deck_html)


def main():
    ap = argparse.ArgumentParser(description='字体子集化（防线 A）')
    ap.add_argument('deck', help='deck 的 index.html 路径')
    ap.add_argument('--font', action='append', required=True, metavar='Family=path',
                    help='字体映射，可多个：--font "Noto Sans SC=/path/NotoSansSC.ttf"')
    ap.add_argument('--out-dir', help='子集输出目录（缺省 <deck>/fonts）')
    ap.add_argument('--inject', action='store_true',
                    help='把 @font-face 块写入 deck 的 fonts SLOT 标记区间')
    ap.add_argument('--format', choices=['auto', 'woff2', 'ttf'], default='auto',
                    help='子集形态：auto（缺省，有 brotli 出 woff2 否则 ttf）；'
                         'ttf 是 pptx 字体内嵌（fntdata）的唯一形态')
    args = ap.parse_args()

    deck_html = os.path.abspath(args.deck)
    deck_dir = os.path.dirname(deck_html)
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(deck_dir, 'fonts')

    mappings = []
    for spec in args.font:
        if '=' not in spec:
            raise SystemExit('--font 格式应为 "Family Name=/path/to/font.ttf"，实为：%s' % spec)
        family, path = spec.split('=', 1)
        mappings.append((family.strip(), os.path.abspath(path.strip())))

    charset = deck_charset(deck_html)
    entries = []
    for family, path in mappings:
        name, weight, fmt, _ = subset_one(family, path, charset, out_dir, args.format)
        entries.append((family, name, weight, fmt))

    block = font_face_block(entries, out_dir, deck_dir)
    print(block)
    if args.inject:
        inject(deck_html, block)
    return 0


if __name__ == '__main__':
    sys.exit(main())
