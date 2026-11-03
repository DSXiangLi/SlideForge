#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生图色彩一致性后置校验（imagegen v2 G2，docs/design/imagegen-v2.md §3-G2）。

对 deck 中所有 data-image-state="generated" 的图（页内插画槽位 + 页面级
烙入槽位 page-baked-*）提取主色板，与 manifest 的 theme tokens 做
CIEDE2000 双向校验：

  指标 A 无锚率：主色中"距全部 token 最近色 ΔE00 > 32"的像素权重占比
      > 40% → 告警（发明新色过多）；
  指标 B 缺席：--accent 在主色板中无 ΔE00 ≤ 24 的呼应色 → 告警；
      非满幅页内槽位还要求 --paper/--ink 有呼应，页面级烙入图（满幅
      baked）豁免 --paper/--ink（背景色被画面覆盖是合法偏离）。

处置：单图触发 A 或 B → 告警不阻断（压暗/叠色等艺术化偏离合法），写入
warn 列表与 ledger；deck 内 ≥50% 的图同时触发 A+B → 退出码 1（阻断，
要求风格段重写后重 roll）。--strict 把任何告警升级为阻断。

色板提取复用项目既有无头浏览器通道（同 check-render/extract-manifest 的
Playwright Chromium）：图片字节以 data URI 注入临时页面，canvas 缩采样
64×36（关闭平滑，保证纯色边界不混色）取回像素；中位切分法（median cut）
取 ≤8 主色与 CIEDE2000 色彩数学在 Python 侧完成——不在纯 Python 里解码
JPEG/PNG。

manifest 来源：--manifest 显式指定 > deck 根 manifest.json > 现场调用
extract-manifest.py 提取（同一渲染通道）。

ledger：deck 根 imagegen-ledger.json 存在时，按 outputs[].file 匹配把
harmony 结论写入对应输出条目（{"warn","metric_a","metric_b",
"unanchored_share","missing_echo"}，原子替换写回，沿用 adapter 口径）；
ledger 不存在则只输出报告，不强行创建。

输出：JSON 报告（默认 stdout，--out 写文件）+ 人类可读摘要（stderr）。
退出码：0 通过或仅告警；1 阻断（≥50% 双触发或 --strict 下有告警）；
2 用法/环境错误。
"""
import argparse
import base64
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

# 阈值（imagegen-v2 §3-G2 初值，真实生图验收后用实测分布校准）
DE_UNANCHORED = 32.0   # 指标 A：主色距全部 token 的最近 ΔE00 上限
DE_ECHO = 24.0         # 指标 B：呼应色判定的 ΔE00 上限
SHARE_UNANCHORED = 0.40  # 指标 A：无锚像素权重占比上限
BLOCK_RATIO = 0.50     # 阻断：同时触发 A+B 的图占比下限
SAMPLE_W, SAMPLE_H = 64, 36
PALETTE_N = 8          # 中位切分主色上限（5–8，颜色少时自然更少）

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTRACTOR = os.path.join(SCRIPT_DIR, 'extract-manifest.py')

# canvas 缩采样：关闭平滑（纯色块边界不混色，合成图断言可精确到 ΔE=0）；
# 透明像素合成到白底（与浏览器默认呈现一致）。
SAMPLE_JS = r"""
async ({dataUrl, w, h}) => {
  const img = new Image();
  await new Promise((res, rej) => {
    img.onload = res;
    img.onerror = () => rej(new Error('image decode failed'));
    img.src = dataUrl;
  });
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(img, 0, 0, w, h);
  return Array.from(ctx.getImageData(0, 0, w, h).data);
}
"""

IMG_RE = re.compile(r'<img\b[^>]*>', re.I)
SECTION_RE = re.compile(r'<section\b[^>]*\bdata-slide-id="([^"]+)"[^>]*>', re.I)
ATTR_RE = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
PAGE_SLOT_RE = re.compile(r'^page-baked-\d+x\d+$')
TOKEN_COLOR_RE = re.compile(
    r'^(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})|rgba?\([^)]*\))\s*$')


# ---------- 色彩数学（sRGB → CIE Lab D65/2° → CIEDE2000，kL=kC=kH=1） ----------

def srgb_to_lab(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    x /= 0.95047  # D65 白点
    z /= 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e_2000(lab1, lab2):
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    cbar = (c1 + c2) / 2.0
    cbar7 = cbar ** 7
    g = 0.5 * (1.0 - math.sqrt(cbar7 / (cbar7 + 25.0 ** 7))) if cbar > 0 else 0.5
    a1p, a2p = a1 * (1 + g), a2 * (1 + g)
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)

    def hp(a, b):
        if a == 0 and b == 0:
            return 0.0
        h = math.degrees(math.atan2(b, a))
        return h + 360.0 if h < 0 else h
    h1p, h2p = hp(a1p, b1), hp(a2p, b2)

    dlp = l2 - l1
    dcp = c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360.0
    else:
        dhp = h2p - h1p + 360.0
    dhp_half = math.radians(dhp) / 2.0
    dhp_ = 2.0 * math.sqrt(c1p * c2p) * math.sin(dhp_half)

    lbarp = (l1 + l2) / 2.0
    cbarp = (c1p + c2p) / 2.0
    if c1p * c2p == 0:
        hbarp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbarp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360:
        hbarp = (h1p + h2p + 360.0) / 2.0
    else:
        hbarp = (h1p + h2p - 360.0) / 2.0

    t = (1.0 - 0.17 * math.cos(math.radians(hbarp - 30))
         + 0.24 * math.cos(math.radians(2 * hbarp))
         + 0.32 * math.cos(math.radians(3 * hbarp + 6))
         - 0.20 * math.cos(math.radians(4 * hbarp - 63)))
    dtheta = 30.0 * math.exp(-(((hbarp - 275.0) / 25.0) ** 2))
    cbarp7 = cbarp ** 7
    rc = 2.0 * math.sqrt(cbarp7 / (cbarp7 + 25.0 ** 7)) if cbarp > 0 else 0.0
    sl = 1.0 + (0.015 * (lbarp - 50.0) ** 2) / math.sqrt(20.0 + (lbarp - 50.0) ** 2)
    sc = 1.0 + 0.045 * cbarp
    sh = 1.0 + 0.015 * cbarp * t
    rt = -math.sin(math.radians(2.0 * dtheta)) * rc
    return math.sqrt((dlp / sl) ** 2 + (dcp / sc) ** 2 +
                     (dhp_ / sh) ** 2 + rt * (dcp / sc) * (dhp_ / sh))


# ---------- 主色板：中位切分法 ----------

def median_cut(pixels, target=PALETTE_N):
    """pixels: [(r,g,b), ...] → [((r,g,b), weight), ...] 按权重降序。

    中位切分出 ≤target 个盒后做两轮最近种子重分配（RGB 空间）——盒跨两个
    纯色簇时均值会产生幻影色，重分配把盒中心吸附回真实簇；最后合并同色项。
    """
    boxes = [list(pixels)]
    while len(boxes) < target:
        cand = None
        for box in boxes:
            if len(box) < 2:
                continue
            if max(max(p[i] for p in box) - min(p[i] for p in box) for i in range(3)) == 0:
                continue
            if cand is None or len(box) > len(cand):
                cand = box
        if cand is None:
            break
        ch = max(range(3), key=lambda i: max(p[i] for p in cand) - min(p[i] for p in cand))
        cand.sort(key=lambda p: p[ch])
        mid = len(cand) // 2
        boxes.remove(cand)
        boxes.append(cand[:mid])
        boxes.append(cand[mid:])

    def centroid(box):
        n = len(box)
        return tuple(round(sum(p[i] for p in box) / n) for i in range(3))

    def assign(centers):
        groups = [[] for _ in centers]
        for p in pixels:  # 平手取先出现的种子，保证确定性
            k = min(range(len(centers)),
                    key=lambda i: sum((p[c] - centers[i][c]) ** 2 for c in range(3)))
            groups[k].append(p)
        return groups

    centers = [centroid(b) for b in boxes]
    for _ in range(3):  # Lloyd 重分配（至多 3 轮，收敛即停）
        groups = assign(centers)
        new_centers = [centroid(g) if g else centers[i] for i, g in enumerate(groups)]
        if new_centers == centers:
            break
        centers = new_centers
    groups = assign(centers)
    merged = {}
    for center, group in zip(centers, groups):
        if group:
            key = centroid(group)
            merged[key] = merged.get(key, 0) + len(group)
    total = sum(merged.values())
    palette = [(rgb, n / total) for rgb, n in merged.items()]
    palette.sort(key=lambda item: -item[1])
    return palette


# ---------- deck 扫描与 manifest ----------

def scan_generated_images(deck_path):
    """扫出 data-image-state="generated" 的 img：slide_id/src/slot/full_bleed。"""
    with open(deck_path, encoding='utf-8') as f:
        html = f.read()
    sections = [(m.start(), m.group(1)) for m in SECTION_RE.finditer(html)]
    images = []
    for m in IMG_RE.finditer(html):
        attrs = dict(ATTR_RE.findall(m.group(0)))
        if attrs.get('data-image-state') != 'generated':
            continue
        slide_id = ''
        for pos, sid in sections:
            if pos < m.start():
                slide_id = sid
            else:
                break
        slot = attrs.get('data-image-slot', '')
        images.append({
            'slide_id': slide_id,
            'src': attrs.get('src', ''),
            'slot': slot or None,
            'full_bleed': bool(PAGE_SLOT_RE.match(slot)),
        })
    return images


def parse_token_color(value):
    """#rgb/#rrggbb/rgb() → (r,g,b)；无法解析返回 None。"""
    v = value.strip()
    m = re.fullmatch(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})', v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    m = re.fullmatch(r'rgba?\(([^)]*)\)', v)
    if m:
        parts = [p.strip() for p in m.group(1).split(',')]
        if len(parts) >= 3:
            try:
                return tuple(max(0, min(255, round(float(p)))) for p in parts[:3])
            except ValueError:
                return None
    return None


def load_manifest(deck_path, manifest_arg):
    if manifest_arg:
        with open(manifest_arg, encoding='utf-8') as f:
            return json.load(f)
    deck_manifest = os.path.join(os.path.dirname(deck_path), 'manifest.json')
    if os.path.isfile(deck_manifest):
        with open(deck_manifest, encoding='utf-8') as f:
            return json.load(f)
    # deck 根无 manifest：现场走 extract-manifest（同一无头浏览器通道）
    with tempfile.TemporaryDirectory(prefix='pptx-harmony-') as tmp:
        out = os.path.join(tmp, 'manifest.json')
        r = subprocess.run([sys.executable, EXTRACTOR, deck_path, '--out', out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit('extract-manifest 失败：%s%s' % (r.stdout, r.stderr))
        with open(out, encoding='utf-8') as f:
            return json.load(f)


# ---------- 浏览器色板提取 ----------

def detect_mime(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if data[:2] == b'\xff\xd8':
        return 'image/jpeg'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


def extract_palettes(deck_dir, images):
    """逐图经无头 Chromium canvas 缩采样 → median cut 主色板。同路径图只采样一次。"""
    from playwright.sync_api import sync_playwright
    cache = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto('about:blank')
        for item in images:
            src = item['src'].split('?')[0].split('#')[0]
            path = os.path.normpath(os.path.join(deck_dir, src))
            if not (path + os.sep).startswith(os.path.normpath(deck_dir) + os.sep):
                item['error'] = 'src 越出 deck 目录'
                continue
            if not os.path.isfile(path):
                item['error'] = '文件不存在'
                continue
            if path in cache:
                item['palette'] = cache[path]
                continue
            with open(path, 'rb') as f:
                data = f.read()
            mime = detect_mime(data)
            if not mime:
                item['error'] = '不可识别的图片格式（仅 PNG/JPEG/WebP）'
                continue
            data_url = 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode('ascii'))
            raw = page.evaluate(SAMPLE_JS, {'dataUrl': data_url, 'w': SAMPLE_W, 'h': SAMPLE_H})
            pixels = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw), 4)]
            cache[path] = median_cut(pixels)
            item['palette'] = cache[path]
        browser.close()
    return images


# ---------- 指标评估 ----------

def evaluate(item, token_labs):
    """token_labs: {token: (lab, rgb)}。就地填写 palette 标注与指标。"""
    palette = item.get('palette') or []
    annotated = []
    for rgb, weight in palette:
        lab = srgb_to_lab(rgb)
        best_token, best_de = None, None
        for token, (tlab, _trgb) in token_labs.items():
            de = delta_e_2000(lab, tlab)
            if best_de is None or de < best_de:
                best_token, best_de = token, de
        annotated.append({
            'rgb': list(rgb),
            'hex': '#%02x%02x%02x' % rgb,
            'weight': round(weight, 4),
            'nearest_token': best_token,
            'delta_e': round(best_de, 2) if best_de is not None else None,
        })
    unanchored = sum(c['weight'] for c in annotated
                     if c['delta_e'] is not None and c['delta_e'] > DE_UNANCHORED)
    metric_a = unanchored > SHARE_UNANCHORED

    # 指标 B 呼应要求：--accent 始终要求；--paper/--ink 仅页内槽位要求
    # （满幅烙入页背景色被画面覆盖是合法偏离，豁免）。
    required = ['--accent'] + ([] if item['full_bleed'] else ['--paper', '--ink'])
    missing = []
    for token in required:
        if token not in token_labs:
            continue
        tlab = token_labs[token][0]
        if not any(delta_e_2000(srgb_to_lab(c['rgb']), tlab) <= DE_ECHO for c in annotated):
            missing.append(token)
    metric_b = bool(missing)

    item['palette'] = annotated
    item['metric_a'] = {'triggered': metric_a, 'unanchored_share': round(unanchored, 4)}
    item['metric_b'] = {'triggered': metric_b, 'missing_echo': missing}
    item['warn'] = metric_a or metric_b
    return item


# ---------- ledger ----------

def update_ledger(deck_dir, images):
    """ledger 存在才更新（不强行创建）：按 outputs[].file 匹配写入 harmony 结论。"""
    ledger_path = os.path.join(deck_dir, 'imagegen-ledger.json')
    if not os.path.isfile(ledger_path) or os.path.islink(ledger_path):
        return False
    with open(ledger_path, encoding='utf-8') as f:
        records = json.load(f)
    if not isinstance(records, list):
        print('[check-image-harmony] WARN: ledger 顶层非数组，跳过写入', file=sys.stderr)
        return False
    by_file = {}
    for item in images:
        if item.get('error'):
            continue
        by_file[os.path.basename(item['src'].split('?')[0])] = item
    changed = False
    for entry in records:
        for out in entry.get('outputs') or []:
            item = by_file.get(out.get('file'))
            if item is None:
                continue
            out['harmony'] = {
                'warn': item['warn'],
                'metric_a': item['metric_a']['triggered'],
                'metric_b': item['metric_b']['triggered'],
                'unanchored_share': item['metric_a']['unanchored_share'],
                'missing_echo': item['metric_b']['missing_echo'],
            }
            changed = True
    if not changed:
        return False
    fd, tmp_name = tempfile.mkstemp(prefix='.imagegen-ledger-', suffix='.json', dir=deck_dir)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, ledger_path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
    return True


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser(description='生图色彩一致性后置校验（imagegen v2 G2）')
    ap.add_argument('deck', help='deck 的 index.html 路径')
    ap.add_argument('--manifest', help='manifest JSON 路径（缺省 deck 根 manifest.json，再没有则现场提取）')
    ap.add_argument('--strict', action='store_true', help='任何告警升级为阻断（退出码 1）')
    ap.add_argument('--out', help='JSON 报告输出路径（缺省写 stdout）')
    args = ap.parse_args()

    deck_path = os.path.abspath(args.deck)
    if not os.path.isfile(deck_path):
        print('[check-image-harmony] ERROR: deck 不存在：%s' % deck_path, file=sys.stderr)
        return 2
    deck_dir = os.path.dirname(deck_path)

    manifest = load_manifest(deck_path, args.manifest)
    raw_tokens = ((manifest.get('theme') or {}).get('tokens')) or {}
    token_labs = {}
    for name, value in raw_tokens.items():
        if not isinstance(value, str) or not TOKEN_COLOR_RE.match(value):
            continue
        rgb = parse_token_color(value)
        if rgb:
            token_labs[name] = (srgb_to_lab(rgb), rgb)
    if not token_labs:
        print('[check-image-harmony] ERROR: manifest 无可解析的 theme token 色值', file=sys.stderr)
        return 2

    images = scan_generated_images(deck_path)
    try:
        images = extract_palettes(deck_dir, images)
    except ImportError:
        print('[check-image-harmony] ERROR: 需要 playwright（项目既有渲染通道）', file=sys.stderr)
        return 2

    checked = []
    for item in images:
        if item.get('error'):
            print('[check-image-harmony] WARN: %s %s 跳过：%s'
                  % (item['slide_id'], item['src'], item['error']), file=sys.stderr)
            continue
        checked.append(evaluate(item, token_labs))

    warned = [i for i in checked if i['warn']]
    both = [i for i in checked
            if i['metric_a']['triggered'] and i['metric_b']['triggered']]
    blocked = bool(checked) and len(both) / len(checked) >= BLOCK_RATIO
    if args.strict and warned:
        blocked = True

    report = {
        'deck': deck_path,
        'thresholds': {
            'de_unanchored': DE_UNANCHORED, 'de_echo': DE_ECHO,
            'unanchored_share': SHARE_UNANCHORED, 'block_ratio': BLOCK_RATIO,
        },
        'tokens': {k: '#%02x%02x%02x' % v[1] for k, v in token_labs.items()},
        'images': checked,
        'summary': {
            'total': len(checked),
            'warned': len(warned),
            'both_a_and_b': len(both),
            'blocked': blocked,
        },
    }
    ledger_updated = update_ledger(deck_dir, images)

    # 人类可读摘要（stderr，stdout 留给 JSON）
    for item in checked:
        tags = []
        if item['metric_a']['triggered']:
            tags.append('A 无锚率 %.0f%%>%.0f%%' % (
                item['metric_a']['unanchored_share'] * 100, SHARE_UNANCHORED * 100))
        if item['metric_b']['triggered']:
            tags.append('B 缺呼应 %s' % '/'.join(item['metric_b']['missing_echo']))
        status = ('WARN(%s)' % '；'.join(tags)) if tags else 'ok'
        print('%s  %-10s %s  %s' % (
            'WARN' if item['warn'] else 'PASS', item['slide_id'], item['src'], status),
            file=sys.stderr)
    print('RESULT: %d 图，%d 告警，%d 双触发；%s%s' % (
        len(checked), len(warned), len(both),
        'BLOCKED' if blocked else 'NOT BLOCKED',
        '；ledger 已更新' if ledger_updated else ''), file=sys.stderr)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    else:
        print(text)
    return 1 if blocked else 0


if __name__ == '__main__':
    sys.exit(main())
