#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三形态 HTML→PPTX 导出（双轨编排入口，docs/design/pptx-export-editable.md §5）。

用法：
  python3 scripts/export-pptx.py <deck/index.html> [--force] [--track both|editable|vector]
  python3 scripts/export-pptx.py <deck/index.html> --check-stale

双轨（C3 起）：
  - **可编辑轨（主交付）**：export/deck.pptx——文本/形状/图表原生可编辑
    （export-pptx-editable.py，import 复用非 subprocess）；
  - **保真轨**：export/deck-vector.pptx（转曲 SVG 矢量）+ export/deck.pdf
    （printToPDF 顺带直出）+ page-NN.svg/png/diff.png——视觉封存、打印、
    跨机零漂移。
  任一轨的基础设施失败不阻断另一轨（报告逐轨声明成败，退出码 1）；
  防线 C 门禁阻断属 deck 级问题——两轨都不产出，已产出的可编辑轨撤下。
  manifest.json 顶层字段向后兼容（编辑器 v3 在读），新增 export.tracks
  字段逐轨声明。

保真轨管线（参数经 tests/harness/results/spike-m3/REPORT.md 实测固化）：
  ① 防线 C 门禁【不过不产 PDF】：
     C1 渲染校验——子进程跑同目录 check-render.py（零溢出/零重叠/
        字号档），任一页 FAIL 即阻断；
     C2 排版漂移对比——现场提取 manifest，与基线快照逐叶对比：内容逐字一致
        的叶子，line_count 变化或 advance_width 漂移 >3% 即判定字体替换已
        改变排版，逐页逐元素列出并阻断。内容不一致的叶子视为合法编辑，
        不参与漂移判定。基线来源按优先级：上一次 export/manifest.json →
        deck 内 .manifest-baseline.json → 无基线时诚实降级（只做 C1，报告
        声明"无基线，漂移检测未生效"），本次快照写入 export/manifest.json
        供下次对比。
  ② printToPDF：freeze 动效后 Chromium 打印——运行时注入
     @page{size:13.333in 7.5in} 与 gradient-flow 还原本色样式（pdftocairo
     无法转换 background-clip:text，见 spike 报告坑 3），scale=2/3
     （骨架固定 1920px 画布 ↔ 13.333″=1280px 的换算常数），
     prefer_css_page_size + print_background。验证页数与逐页尺寸
     13.333″×7.5″。
  ③ pdf→svg：pdftocairo -svg 逐页 -f N -l N（不带页码会把全部页叠印进
     单个 SVG，spike 坑 1）；sanity check：viewBox 16:9、非空、零 <text>
     元素（文字必须已转曲）、零外部引用。
  ④ PNG 副本：最终 SVG 用 Chromium 光栅化（1280×720 视口 + dsf=1.5 →
     1920×1080；大视口直接截图会因 SVG 固有尺寸居中留白边，spike 坑 4）。
     烙入页（render_mode=baked）跳过 ②③④，assets/page-<id>.png 直通。
  ⑤ python-pptx 组装：13.333″×7.5″ 演示文稿，每页满幅 PNG；svg 页追加
     svgBlip 双写（a:blip r:embed→PNG，a:extLst asvg:svgBlip→SVG，
     ext uri {96DAC541-7B7A-43D3-8B79-37D633B846F1}）；保存后 zip 手术补
     [Content_Types].xml 的 svg Default（python-pptx 不序列化未知 content
     type，spike 坑 5）。
  ⑥ 降级链【硬规则】：pdftocairo 不可用或某页转换/sanity 失败 → 该页以
     3840×2160 高分辨率截图单独成页（carrier=png-fallback，报告列明降级
     原因）；截图设施也不可用 → 非零退出、不产半成品。
  ⑦ postflight：全部产物先写临时目录，重开包校验（python-pptx 重开、
     页数一致、media/rels/content-types 与报告逐页一致）全过才覆盖
     export/ 主产物。
  ⑧ 保真分 + 热区：每页 HTML freeze 截图 vs export/page-NN.png 像素 diff
     （max 通道差 >24 计差异像素，spike 口径），fidelity=100-diff_pct，
     产出 page-NN.diff.png 差异热力图；烙入页直通不参与 diff
     （fidelity=null）。
  ⑨ export/manifest.json（交付态）：M1 提取态全量 + 每页合并
     {carrier, fidelity, export_hash, uncovered_glyphs, degraded_reason?}
     + 顶层导出时间/转换器版本/门禁结果。
  ⑩ 单向纪律【硬规则】：导出全程对 index.html 只读——前后 sha256 比对，
     变化即非零退出。

--check-stale：重提取当前页级 hash，与 export/manifest.json 的 export_hash
  逐页比对；任何页不一致（含缺失）列出并非零退出——指纹过期检出。

环境变量 PPTX_EXPORT_DISABLE_SCREENSHOT=1：测试钩子，模拟截图设施不可用
（harness 降级演练用），首次需要截图即失败退出。

依赖：python3 stdlib + playwright + python-pptx + pillow（harness 既有依赖）
     + fontTools（仅 uncovered_glyphs 检测，无 fonts/ 时不触发）。
退出码：成功 0；门禁阻断 / 漂移阻断 / 转换与截图双失败 / 单向纪律违反 /
       postflight 失败 / stale 检出 均为 1。
"""
import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
J_RENDER_CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check-render.py')
EXTRACT_MANIFEST = os.path.join(ROOT, 'skills/html-pptx/scripts/extract-manifest.py')

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5
PDF_SCALE = 2 / 3            # 1920px 画布 → 1280px（13.333″）的换算常数
DIFF_W, DIFF_H = 1280, 720   # 保真 diff 统一分辨率
DIFF_THRESH = 24             # max 通道绝对差阈值（抗锯齿噪声之上）
DRIFT_WIDTH_TOL = 0.03       # 防线 C：advance_width 漂移容忍 3%

# 打印前注入（运行时，不落盘）：页尺寸钉死 13.333×7.5 + 流光字还原本色
PRINT_INJECT_CSS = (
    "@media print{"
    "@page{size:13.333in 7.5in;margin:0 !important}"
    "[data-anim='gradient-flow']{background:none !important;"
    "-webkit-text-fill-color:currentColor !important}"
    "}"
)

SVG_BLIP_EXT_URI = '{96DAC541-7B7A-43D3-8B79-37D633B846F1}'
NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_ASVG = 'http://schemas.microsoft.com/office/drawing/2016/SVG/main'


class ExportError(Exception):
    """管线级失败：打印信息并以退出码 1 终止。"""


class GateBlocked(ExportError):
    """防线 C 门禁阻断（deck 级质量门禁）——双轨编排下两轨都不产出：
    烙入坏版式到哪条轨都是坏的，门禁失败不属于"单轨基础设施失败"。"""


def _load_editable():
    """惰性加载可编辑轨模块（避免与 export-pptx-editable.py 顶层互导死循环）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'export_pptx_editable', os.path.join(HERE, 'export-pptx-editable.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def log(msg):
    print('[export-pptx] %s' % msg, file=sys.stderr)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def run_py(script, *args, env=None):
    return subprocess.run([sys.executable, script, *args],
                          capture_output=True, text=True, env=env)


# ---------------------------------------------------------------- 防线 C

def gate_render(deck_html):
    """C1：子进程重跑 check-render 口径（零溢出/零重叠/字号档）。"""
    log('防线 C1：渲染校验（check-render 口径）…')
    r = run_py(J_RENDER_CHECK, deck_html)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    if r.returncode != 0:
        raise GateBlocked('防线 C1 阻断：渲染校验未过——%s\n%s' % (tail, r.stdout))
    log('防线 C1 通过：%s' % tail)


def extract_manifest(deck_html, out_path):
    r = run_py(EXTRACT_MANIFEST, deck_html, '--out', out_path)
    if r.returncode != 0:
        raise ExportError('manifest 提取失败：%s%s' % (r.stdout, r.stderr))
    with open(out_path, encoding='utf-8') as f:
        return json.load(f)


def load_baseline(deck_dir):
    """漂移基线，按优先级：上一次 export/manifest.json → deck/.manifest-baseline.json。"""
    p1 = os.path.join(deck_dir, 'export', 'manifest.json')
    p2 = os.path.join(deck_dir, '.manifest-baseline.json')
    for path, src in ((p1, 'export/manifest.json（上次导出快照）'),
                      (p2, '.manifest-baseline.json（生成侧落盘基线）')):
        if os.path.isfile(path):
            try:
                with open(path, encoding='utf-8') as f:
                    return json.load(f), src
            except (OSError, json.JSONDecodeError) as e:
                log('基线 %s 读取失败（%s），尝试下一来源' % (path, e))
    return None, None


def gate_drift(manifest, baseline, baseline_src):
    """C2：排版漂移对比。内容逐字一致的叶子比 line_count / advance_width；
    内容不一致的叶子是合法编辑，不参与漂移判定。"""
    if baseline is None:
        log('防线 C2：无基线，漂移检测未生效（本次快照将写入 export/manifest.json）')
        return {'status': 'no-baseline', 'baseline': None, 'violations': []}
    base_pages = {p['slide_id']: p for p in baseline.get('pages', [])}
    violations = []
    compared = 0
    for page in manifest['pages']:
        bp = base_pages.get(page['slide_id'])
        if not bp:
            continue
        base_texts = [t for t in bp.get('texts', []) if t.get('content')]
        cur_texts = [t for t in page.get('texts', []) if t.get('content')]
        for bt in base_texts:
            # 同一内容可能多次出现：逐次消耗匹配，避免重复比对同一基线叶
            hit = None
            for ct in cur_texts:
                if ct.get('_consumed'):
                    continue
                if ct['content'] == bt['content']:
                    hit = ct
                    break
            if hit is None:
                continue  # 内容被编辑/删除——合法变更，非字体漂移
            hit['_consumed'] = True
            compared += 1
            bw = float(bt.get('advance_width') or 0)
            cw = float(hit.get('advance_width') or 0)
            width_drift = abs(cw - bw) / bw if bw > 0 else (0 if cw == 0 else 1)
            if hit.get('line_count') != bt.get('line_count') or width_drift > DRIFT_WIDTH_TOL:
                violations.append({
                    'slide_id': page['slide_id'],
                    'text': bt['content'][:24],
                    'baseline': {'line_count': bt.get('line_count'), 'advance_width': bw},
                    'current': {'line_count': hit.get('line_count'), 'advance_width': cw},
                })
    for page in manifest['pages']:
        for t in page.get('texts', []):
            t.pop('_consumed', None)
    if violations:
        lines = ['防线 C2 阻断：排版漂移（字体替换已改变排版），逐元素明细：']
        for v in violations:
            lines.append('  页 %s 文本 "%s…"：快照 行数=%s 宽=%.1f → 实测 行数=%s 宽=%.1f'
                         % (v['slide_id'], v['text'],
                            v['baseline']['line_count'], v['baseline']['advance_width'],
                            v['current']['line_count'], v['current']['advance_width']))
        lines.append('修复路径：安装主题字体 / 跑 subset-fonts.py 防线 A 子集化 / 调整容器')
        raise GateBlocked('\n'.join(lines))
    log('防线 C2 通过：基线=%s，比对叶子 %d 片，零漂移' % (baseline_src, compared))
    return {'status': 'pass', 'baseline': baseline_src, 'compared_leaves': compared,
            'violations': []}


# ---------------------------------------------------------------- 渲染与打印

FREEZE_JS = """async () => {
  const slides = Array.from(document.querySelectorAll('.slide-slot'));
  for (const s of slides) {
    s.scrollIntoView({block: 'start', behavior: 'instant'});
    await new Promise(r => setTimeout(r, 250));
  }
  slides[0] && slides[0].scrollIntoView({block: 'start', behavior: 'instant'});
  await new Promise(r => setTimeout(r, 600));
  const m = window.__pptxMotion;
  if (m) {
    if (typeof m.freeze === 'function') m.freeze();        // v5+ 才有 freeze
    if (typeof m.restoreAll === 'function') m.restoreAll();
  }
}"""


def screenshots_disabled():
    return os.environ.get('PPTX_EXPORT_DISABLE_SCREENSHOT') == '1'


def render_deck(deck_html, work):
    """一次渲染会话：freeze 后的逐页截图（真值 + 降级高分辨率源）+ printToPDF。
    返回 (truth_shots[N], pdf_path)。dsf=2 → 截图原生 3840×2160。"""
    if screenshots_disabled():
        raise ExportError('截图设施不可用（PPTX_EXPORT_DISABLE_SCREENSHOT=1）——'
                          '降级链穷尽，不产半成品')
    pdf_path = os.path.join(work, 'deck.pdf')
    truth = []
    url = 'file://' + os.path.abspath(deck_html)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1080},
                                device_scale_factor=2)
        page.goto(url)
        page.wait_for_timeout(1000)
        page.evaluate(FREEZE_JS)
        slides = page.query_selector_all('section.slide')
        for i, s in enumerate(slides, 1):
            p = os.path.join(work, 'truth-%02d.png' % i)
            s.screenshot(path=p)
            truth.append(p)
        # printToPDF（spike 固化参数）
        page.add_style_tag(content=PRINT_INJECT_CSS)
        page.pdf(path=pdf_path, prefer_css_page_size=True, print_background=True,
                 display_header_footer=False, scale=PDF_SCALE)
        browser.close()
    return truth, pdf_path


def verify_pdf(pdf_path, expect_pages):
    """stdlib 级 PDF 校验：页数与逐页 MediaBox = 13.333″×7.5″（960×540pt）。"""
    with open(pdf_path, 'rb') as f:
        data = f.read()
    boxes = re.findall(rb'/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]', data)
    if not boxes:
        raise ExportError('PDF 校验失败：读不到 MediaBox')
    bad = []
    for b in boxes:
        w = (float(b[2]) - float(b[0])) / 72.0
        h = (float(b[3]) - float(b[1])) / 72.0
        if abs(w - SLIDE_W_IN) > 0.01 or abs(h - SLIDE_H_IN) > 0.01:
            bad.append('%.4f″×%.4f″' % (w, h))
    if len(boxes) != expect_pages:
        raise ExportError('PDF 页数不符：期望 %d，实测 MediaBox %d 个' % (expect_pages, len(boxes)))
    if bad:
        raise ExportError('PDF 页尺寸不符（期望 13.333″×7.5″）：%s' % bad)
    log('PDF 校验通过：%d 页，逐页 13.333″×7.5″' % len(boxes))


# ---------------------------------------------------------------- pdf→svg

def pdftocairo_version():
    try:
        r = subprocess.run(['pdftocairo', '-v'], capture_output=True, text=True)
        return (r.stderr or r.stdout).strip().splitlines()[0]
    except OSError:
        return None


def pdf_to_svg(pdf_path, page_no, out_path):
    """逐页转换（必须 -f N -l N：不带页码会把全部页叠印进单个 SVG）。
    返回 None 成功，否则返回失败原因字符串。"""
    r = subprocess.run(['pdftocairo', '-svg', '-f', str(page_no), '-l', str(page_no),
                        pdf_path, out_path], capture_output=True, text=True)
    if r.returncode != 0:
        return 'pdftocairo 退出码 %d：%s' % (r.returncode, (r.stderr or '').strip()[:200])
    return svg_sanity(out_path)


def valid_inline_raster_data_uri(value):
    match = re.fullmatch(r'data:image/(png|jpeg);base64,([A-Za-z0-9+/]*={0,2})',
                         value.strip(), re.I)
    if not match:
        return False
    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError):
        return False
    mime = match.group(1).lower()
    return (mime == 'png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (
        mime == 'jpeg' and raw.startswith(b'\xff\xd8\xff'))


def svg_sanity(path):
    """sanity check：viewBox 16:9、非空、零 <text>、零外部引用。"""
    try:
        with open(path, encoding='utf-8') as f:
            s = f.read()
    except OSError as e:
        return 'SVG 读取失败：%s' % e
    if len(s) < 500:
        return 'SVG 过小（%d 字节），疑似空页' % len(s)
    try:
        root = ET.fromstring(s)
    except ET.ParseError as e:
        return 'SVG XML 非法：%s' % e
    view_box = root.attrib.get('viewBox', '').split()
    if len(view_box) != 4:
        return 'SVG 缺 viewBox'
    try:
        w, h = float(view_box[2]), float(view_box[3])
    except ValueError:
        return 'SVG viewBox 非数字：%s' % root.attrib.get('viewBox')
    if h <= 0 or abs(w / h - 16 / 9) > 0.01:
        return 'viewBox 比例非 16:9：%s×%s' % (w, h)
    if any(element.tag.rsplit('}', 1)[-1].lower() == 'text' for element in root.iter()):
        return 'SVG 含 <text> 元素——文字未转曲，违反管线核心约定'
    external = []
    for element in root.iter():
        for name, value in element.attrib.items():
            local = name.rsplit('}', 1)[-1].lower()
            reference = value.strip()
            if local in {'href', 'src'} and reference and not reference.startswith('#'):
                if not valid_inline_raster_data_uri(reference):
                    external.append(reference)
    external.extend(reference.strip(" '\"") for reference in re.findall(
        r'url\(([^)]+)\)', s, re.I) if not reference.strip(" '\"").startswith('#'))
    if external:
        return 'SVG 含外部或非法内联引用：%s' % external[:3]
    if '@font-face' in s:
        return 'SVG 含 @font-face（字体应已转曲）'
    return None


def rasterize_svg(svg_paths, out_dir, suffix='.png'):
    """SVG → 1920×1080 PNG（1280×720 视口 + dsf=1.5；SVG 按固有尺寸渲染，
    大视口截图会居中留白边——spike 坑 4）。返回 {page_key: png_path}。"""
    if screenshots_disabled():
        raise ExportError('截图设施不可用（PPTX_EXPORT_DISABLE_SCREENSHOT=1）——'
                          '降级链穷尽，不产半成品')
    out = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': DIFF_W, 'height': DIFF_H},
                                device_scale_factor=1.5)
        for key, svg in svg_paths.items():
            page.goto('file://' + os.path.abspath(svg))
            page.wait_for_timeout(300)
            p = os.path.join(out_dir, key + suffix)
            page.screenshot(path=p)
            out[key] = p
        browser.close()
    return out


# ---------------------------------------------------------------- 保真分

def diff_pair(img_a, img_b):
    """spike 口径：双图统一到 1280×720，max(R,G,B) 通道绝对差 >24 计差异像素。
    返回 (diff_pct, mean_abs)。纯 PIL（ImageChops 逐通道 lighter 取 max）。"""
    from PIL import Image, ImageChops, ImageStat
    a = Image.open(img_a).convert('RGB').resize((DIFF_W, DIFF_H), Image.LANCZOS)
    b = Image.open(img_b).convert('RGB').resize((DIFF_W, DIFF_H), Image.LANCZOS)
    diff = ImageChops.difference(a, b)
    r, g, bl = diff.split()
    dmax = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    over = dmax.point(lambda v: 255 if v > DIFF_THRESH else 0)
    hist = over.histogram()
    diff_pct = hist[255] / (DIFF_W * DIFF_H) * 100
    mean_abs = ImageStat.Stat(dmax).mean[0]
    return diff_pct, mean_abs, dmax


def save_heatmap(dmax, out_path):
    """差异热力图：差异像素染红（强度∝差值），一致区淡绿。"""
    from PIL import Image
    red = dmax.point(lambda v: min(255, v * 4))
    green = dmax.point(lambda v: 200 if v <= DIFF_THRESH else 0)
    Image.merge('RGB', (red, green, Image.new('L', dmax.size, 0))).save(out_path)


# ---------------------------------------------------------------- 字体覆盖（防线 A 配套）

def uncovered_glyphs(manifest, deck_dir):
    """deck/fonts/*.woff2（或 .ttf）子集覆盖检测：全 deck 用字集 vs 子集覆盖集。
    无 fonts/ → 空数组 + 注明缺失。返回 (per_page{slide_id: [...]}, all_chars, note)。"""
    fonts_dir = os.path.join(deck_dir, 'fonts')
    files = []
    if os.path.isdir(fonts_dir):
        files = [os.path.join(fonts_dir, f) for f in sorted(os.listdir(fonts_dir))
                 if f.lower().endswith(('.woff2', '.ttf', '.otf'))]
    if not files:
        return {p['slide_id']: [] for p in manifest['pages']}, [], \
            'deck 无 fonts/ 子集——字形覆盖检测未生效（防线 A 未启用）'
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return {p['slide_id']: [] for p in manifest['pages']}, [], \
            'fontTools 不可用——字形覆盖检测未生效'
    covered = set()
    for fp in files:
        try:
            with TTFont(fp) as font:
                cmap = font.getBestCmap()
                if cmap:
                    covered.update(cmap.keys())
        except Exception as e:  # 单个字体损坏不拖死导出，记入说明
            log('字体 %s 解析失败（%s），不计入覆盖集' % (fp, e))
    def uncover(text):
        return sorted({c for c in text if not c.isspace() and ord(c) not in covered})
    per_page = {}
    all_missing = set()
    for p in manifest['pages']:
        text = ''.join(t.get('content') or '' for t in p.get('texts', []))
        miss = uncover(text)
        per_page[p['slide_id']] = miss
        all_missing.update(miss)
    note = 'fonts/ 子集覆盖检测完成（%d 个字体文件）' % len(files)
    if all_missing:
        note += '；发现 %d 个未覆盖字形——fonts stale，需重跑 subset-fonts.py' % len(all_missing)
    return per_page, sorted(all_missing), note


# ---------------------------------------------------------------- pptx 组装

def build_pptx(pages_plan, out_path):
    """pages_plan: [{png, svg|None}]。满幅 PNG + svgBlip 双写（有 svg 的页）。"""
    from pptx import Presentation
    from pptx.util import Inches
    from pptx.opc.package import Part
    from pptx.opc.packuri import PackURI
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from lxml import etree

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)
    blank = prs.slide_layouts[6]
    n_svg = 0
    for i, plan in enumerate(pages_plan, 1):
        slide = prs.slides.add_slide(blank)
        pic = slide.shapes.add_picture(plan['png'], 0, 0,
                                       width=prs.slide_width, height=prs.slide_height)
        if not plan.get('svg'):
            continue
        with open(plan['svg'], 'rb') as f:
            blob = f.read()
        svg_part = PackURI('/ppt/media/page-%02d.svg' % i)
        part = Part(svg_part, 'image/svg+xml', prs.part.package, blob)
        svg_rid = slide.part.relate_to(part, RT.IMAGE)
        blip = pic._pic.blipFill.blip
        ext_lst = blip.find('{%s}extLst' % NS_A)
        if ext_lst is None:
            ext_lst = etree.SubElement(blip, '{%s}extLst' % NS_A)
        ext = etree.SubElement(ext_lst, '{%s}ext' % NS_A)
        ext.set('uri', SVG_BLIP_EXT_URI)
        svg_blip = etree.SubElement(ext, '{%s}svgBlip' % NS_ASVG)
        svg_blip.set('{%s}embed' % NS_R, svg_rid)
        n_svg += 1
    prs.save(out_path)
    if n_svg:
        patch_content_types(out_path)
    return n_svg


def patch_content_types(pptx_path):
    """python-pptx 不序列化未知 content type——zip 手术补 svg Default
    （缺失时 Office 判包损坏，spike 坑 5）。"""
    tmp = pptx_path + '.tmp'
    with zipfile.ZipFile(pptx_path) as zin, \
            zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == '[Content_Types].xml':
                s = data.decode('utf-8')
                if 'Extension="svg"' not in s:
                    s = s.replace('</Types>',
                                  '<Default Extension="svg" ContentType="image/svg+xml"/>'
                                  '</Types>')
                data = s.encode('utf-8')
            zout.writestr(item, data)
    os.replace(tmp, pptx_path)


def postflight(pptx_path, pages_plan, expect_pages, expect_svg):
    """重开包校验：python-pptx 重开、页数、media/rels/content-types 逐页一致。"""
    from pptx import Presentation
    prs = Presentation(pptx_path)
    if len(list(prs.slides)) != expect_pages:
        raise ExportError('postflight 失败：pptx 重开页数 %d ≠ %d'
                          % (len(list(prs.slides)), expect_pages))
    with zipfile.ZipFile(pptx_path) as z:
        names = z.namelist()
        n_png = len([n for n in names if n.startswith('ppt/media/') and n.endswith('.png')])
        n_svg = len([n for n in names if n.startswith('ppt/media/') and n.endswith('.svg')])
        if n_png != expect_pages:
            raise ExportError('postflight 失败：media PNG %d ≠ 页数 %d' % (n_png, expect_pages))
        if n_svg != expect_svg:
            raise ExportError('postflight 失败：media SVG %d ≠ 报告 %d' % (n_svg, expect_svg))
        if expect_svg:
            ct = z.read('[Content_Types].xml').decode('utf-8')
            if 'Extension="svg"' not in ct:
                raise ExportError('postflight 失败：[Content_Types].xml 缺 svg Default')
        for i, plan in enumerate(pages_plan, 1):
            rels = z.read('ppt/slides/_rels/slide%d.xml.rels' % i).decode('utf-8')
            has_svg_rel = '.svg' in rels
            if has_svg_rel != bool(plan.get('svg')):
                raise ExportError('postflight 失败：slide%d rels 与载体报告不一致' % i)
    log('postflight 通过：%d 页、%d SVG、media/rels/content-types 一致'
        % (expect_pages, expect_svg))


# ---------------------------------------------------------------- 主流程

def run_vector(deck_html, deck_dir, export_dir, t0):
    """保真轨全流程（既有 M3 管线，零行为变更；产物改名 deck-vector.pptx +
    顺带直出 deck.pdf）。返回交付态 manifest dict，失败抛 ExportError。"""
    hash_before = sha256_file(deck_html)

    # 防线 C 门禁【不过不产 PDF】
    gate_render(deck_html)
    work = tempfile.mkdtemp(prefix='pptx-export-')
    try:
        manifest = extract_manifest(deck_html, os.path.join(work, 'manifest.json'))
        baseline, baseline_src = load_baseline(deck_dir)
        gate = {'render': 'pass', 'drift': gate_drift(manifest, baseline, baseline_src)}

        n_pages = len(manifest['pages'])
        baked = {}  # page_index(1-based) -> assets png
        for i, p in enumerate(manifest['pages'], 1):
            if p.get('render_mode') == 'baked':
                src = None
                for img in p.get('images', []):
                    if img.get('slot', '').startswith('page-baked'):
                        src = img.get('src')
                        break
                if not src:
                    raise ExportError('烙入页 %s 缺页面级槽位（page-baked-*）' % p['slide_id'])
                ap = os.path.join(deck_dir, src)
                if not os.path.isfile(ap):
                    raise ExportError('烙入页 %s 图片不存在：%s' % (p['slide_id'], src))
                baked[i] = ap

        # 渲染 + 打印（HTML 页；烙入页直通但仍参与页序）
        truth, pdf_path = render_deck(deck_html, work)   # work/deck.pdf 即保真轨直出 PDF
        verify_pdf(pdf_path, n_pages)

        # pdf→svg + 降级链
        conv_version = pdftocairo_version()
        svg_ok = conv_version is not None
        page_key = lambda i: 'page-%02d' % i
        svgs, degraded = {}, {}
        if not svg_ok:
            log('pdftocairo 不可用——全部 HTML 页降级为 png-fallback（3840×2160 截图）')
            for i in range(1, n_pages + 1):
                if i not in baked:
                    degraded[i] = 'pdftocairo 不可用'
        else:
            for i in range(1, n_pages + 1):
                if i in baked:
                    continue
                sp = os.path.join(work, page_key(i) + '.svg')
                err = pdf_to_svg(pdf_path, i, sp)
                if err:
                    degraded[i] = err
                    log('第 %d 页 SVG 转换失败（%s）——降级 png-fallback' % (i, err))
                else:
                    svgs[i] = sp

        # PNG 副本：svg 页由最终 SVG 光栅化（与 pptx 内嵌件同一份矢量源）；
        # 降级页用 3840×2160 真值截图；烙入页 assets 直通
        pngs = {}
        if svgs:
            pngs.update(rasterize_svg({page_key(i): s for i, s in svgs.items()}, work))
        for i in degraded:
            pngs[page_key(i)] = truth[i - 1]  # dsf=2 → 3840×2160 高分辨率截图
        for i, ap in baked.items():
            dst = os.path.join(work, page_key(i) + '.png')
            shutil.copyfile(ap, dst)
            pngs[page_key(i)] = dst

        # 保真分 + 热区（烙入页直通不参与 diff）
        fidelity = {}
        for i in range(1, n_pages + 1):
            key = page_key(i)
            if i in baked:
                fidelity[key] = None
                continue
            diff_pct, mean_abs, dmax = diff_pair(truth[i - 1], pngs[key])
            save_heatmap(dmax, os.path.join(work, key + '.diff.png'))
            fidelity[key] = round(100 - diff_pct, 3)
            log('保真 %s：fidelity=%.3f（diff %.3f%%，mean %.2f）'
                % (key, fidelity[key], diff_pct, mean_abs))

        # 组装 + postflight（先写临时文件，全过才覆盖主产物）
        pages_plan = [{'png': pngs[page_key(i)], 'svg': svgs.get(i)}
                      for i in range(1, n_pages + 1)]
        pptx_path = os.path.join(work, 'deck-vector.pptx')
        n_svg = build_pptx(pages_plan, pptx_path)
        postflight(pptx_path, pages_plan, n_pages, n_svg)

        # export/manifest.json（交付态 = 提取态 + 导出报告）
        per_page_uncov, all_uncov, glyphs_note = uncovered_glyphs(manifest, deck_dir)
        for i, p in enumerate(manifest['pages'], 1):
            key = page_key(i)
            p['carrier'] = 'baked' if i in baked else ('svg' if i in svgs else 'png-fallback')
            p['fidelity'] = fidelity[key]
            p['export_hash'] = p['content_hash']
            p['uncovered_glyphs'] = per_page_uncov.get(p['slide_id'], [])
            if i in degraded:
                p['degraded_reason'] = degraded[i]
        vals = [v for v in fidelity.values() if v is not None]
        manifest['export'] = {
            'exported_at': t0.isoformat(),
            'exporter': 'export-pptx.py (M3+C3 双轨)',
            'converter': {'pdftocairo': conv_version, 'chromium': 'playwright'},
            'gate': gate,
            'pages': n_pages,
            'carriers': {'svg': len(svgs), 'baked': len(baked), 'png-fallback': len(degraded)},
            'fidelity_avg': round(sum(vals) / len(vals), 3) if vals else None,
            'uncovered_glyphs': all_uncov,
            'glyphs_note': glyphs_note,
        }

        # 单向纪律：导出前后 deck 字节一致
        if sha256_file(deck_html) != hash_before:
            raise ExportError('单向纪律违反：导出过程中 index.html 发生变化')

        # 交付态 manifest 落盘（覆盖提取态临时件）
        with open(os.path.join(work, 'manifest.json'), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.write('\n')

        # 落盘 export/（--force 覆盖）；清理上一版的过期产物——keep 按本次
        # 实际产物名构建，并保护可编辑轨产物（deck.pptx / deck.report.json /
        # native/ 原生预览页图目录——可编辑轨持久化的 LO 参考渲染，同属交付产物）
        os.makedirs(export_dir, exist_ok=True)
        keep = {'manifest.json', 'deck.pptx', 'deck.report.json', 'native'}
        for name in os.listdir(work):
            if name in ('manifest.json',):
                continue
            if name.startswith('page-') or name in ('deck-vector.pptx', 'deck.pdf'):
                shutil.move(os.path.join(work, name), os.path.join(export_dir, name))
                keep.add(name)
        for name in list(os.listdir(export_dir)):
            if name not in keep:
                os.remove(os.path.join(export_dir, name))
        shutil.move(os.path.join(work, 'manifest.json'),
                    os.path.join(export_dir, 'manifest.json'))
        log('保真轨完成：%s（%d 页）' % (export_dir, n_pages))
        return manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)


def cmd_export(deck_html, force, track='both'):
    """双轨编排：默认两轨全出——可编辑轨 deck.pptx（主交付）+ 保真轨
    deck-vector.pptx / deck.pdf；任一轨的基础设施失败不阻断另一轨（报告
    逐轨声明成败），防线 C 门禁阻断属 deck 级问题，两轨都不产出。"""
    deck_html = os.path.abspath(deck_html)
    deck_dir = os.path.dirname(deck_html)
    export_dir = os.path.join(deck_dir, 'export')
    if not os.path.isfile(deck_html):
        raise ExportError('deck 不存在：%s' % deck_html)
    if not force and (os.path.isfile(os.path.join(export_dir, 'deck.pptx'))
                      or os.path.isfile(os.path.join(export_dir, 'deck-vector.pptx'))):
        raise ExportError('export/ 已有 pptx 产物——重导请加 --force（旧件作废，单向纪律）')

    t0 = datetime.now(timezone.utc)
    tracks = {}
    gate_blocked = None

    # 保真轨先行：可编辑轨 L5 逐页降级可借 export/ 的 page-NN.svg/png 矢量件
    if track in ('both', 'vector'):
        try:
            manifest = run_vector(deck_html, deck_dir, export_dir, t0)
            exp = manifest['export']
            tracks['vector'] = {'ok': True, 'pptx': 'deck-vector.pptx', 'pdf': 'deck.pdf',
                                'fidelity_avg': exp['fidelity_avg'],
                                'carriers': exp['carriers']}
        except GateBlocked as e:
            gate_blocked = str(e)
            tracks['vector'] = {'ok': False, 'gate': gate_blocked}
        except Exception as e:
            tracks['vector'] = {'ok': False, 'error': str(e)}
            log('保真轨失败（可编辑轨继续）：%s' % e)

    # 可编辑轨（基础设施失败不阻断保真轨成果）
    if track in ('both', 'editable') and not gate_blocked:
        try:
            rep = _load_editable().run_export(deck_html,
                                              os.path.join(export_dir, 'deck.pptx'),
                                              vector_dir=export_dir)
            tracks['editable'] = {
                'ok': True, 'pptx': 'deck.pptx',
                'native_text_ratio': rep['native_text_ratio'],
                'native_infographic_ratio': rep.get('native_infographic_ratio'),
                'rasterized': rep['totals']['raster'],
                'uncovered': sorted({u for p in rep['pages'] for u in p['uncovered']}),
                'fonts_embedded': rep.get('fonts_embedded'),
                'fonts_skipped': rep.get('fonts_skipped'),
                'fonts_note': rep.get('fonts_note'),
                'margin_mode': rep.get('margin_mode'),
                'verify': (rep.get('verify') or {}).get('status'),
                'degraded_pages': (rep.get('verify') or {}).get('degraded_pages'),
            }
        except Exception as e:  # 单轨失败诚实声明，另一轨继续
            tracks['editable'] = {'ok': False, 'error': str(e)}
            log('可编辑轨失败（保真轨成果保留）：%s' % e)

    # 门禁阻断 → 可编辑轨不跑/已产出即撤下（坏版式不交付，门禁语义覆盖双轨）
    if gate_blocked:
        tracks.setdefault('editable', {'ok': False, 'gate': '门禁阻断，可编辑轨未产出'})
    if gate_blocked and os.path.isfile(os.path.join(export_dir, 'deck.pptx')):
        os.remove(os.path.join(export_dir, 'deck.pptx'))
        rep_json = os.path.join(export_dir, 'deck.report.json')
        if os.path.isfile(rep_json):
            os.remove(rep_json)
        tracks['editable'] = {'ok': False, 'gate': '门禁阻断，可编辑轨产物已撤下'}

    # tracks 写回 export/manifest.json（保真轨产出过时；向后兼容：顶层字段不动）
    mf_path = os.path.join(export_dir, 'manifest.json')
    if os.path.isfile(mf_path):
        with open(mf_path, encoding='utf-8') as f:
            mf = json.load(f)
        mf.setdefault('export', {})['tracks'] = tracks
        with open(mf_path, 'w', encoding='utf-8') as f:
            json.dump(mf, f, ensure_ascii=False, indent=2)
            f.write('\n')

    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    ok_all = all(t.get('ok') for t in tracks.values()) if tracks else False
    print(json.dumps({'ok': ok_all, 'export_dir': export_dir, 'tracks': tracks,
                      'elapsed_s': round(dt, 1)}, ensure_ascii=False, indent=2))
    if gate_blocked:
        print(gate_blocked, file=sys.stderr)
    return 0 if ok_all else 1


def cmd_check_stale(deck_html):
    deck_html = os.path.abspath(deck_html)
    deck_dir = os.path.dirname(deck_html)
    mf_path = os.path.join(deck_dir, 'export', 'manifest.json')
    if not os.path.isfile(mf_path):
        print('export/manifest.json 不存在——从未导出，无法做 stale 检测', file=sys.stderr)
        return 1
    with open(mf_path, encoding='utf-8') as f:
        exported = json.load(f)
    work = tempfile.mkdtemp(prefix='pptx-stale-')
    try:
        cur = extract_manifest(deck_html, os.path.join(work, 'm.json'))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    exp_hashes = {p['slide_id']: p.get('export_hash') for p in exported.get('pages', [])}
    stale = []
    for p in cur['pages']:
        eh = exp_hashes.get(p['slide_id'])
        if eh != p['content_hash']:
            stale.append('%s（导出时 %s ≠ 当前 %s）'
                         % (p['slide_id'], eh, p['content_hash']))
    if stale:
        print('指纹过期 %d 页：%s' % (len(stale), '、'.join(stale)), file=sys.stderr)
        return 1
    print('stale 检测通过：%d 页指纹全部与导出时一致' % len(cur['pages']))
    return 0


def main():
    ap = argparse.ArgumentParser(description='HTML→PPTX 导出管线（双轨：可编辑轨 + 保真轨）')
    ap.add_argument('deck', help='deck 的 index.html 路径')
    ap.add_argument('--force', action='store_true',
                    help='覆盖已有 export/ pptx 产物（重导即作废旧件）')
    ap.add_argument('--track', choices=['both', 'editable', 'vector'], default='both',
                    help='导出轨道：both（缺省两轨全出）/ editable（可编辑轨 deck.pptx）'
                         '/ vector（保真轨 deck-vector.pptx + deck.pdf）')
    ap.add_argument('--check-stale', action='store_true',
                    help='只做指纹过期检测：当前页级 hash vs export/manifest.json')
    args = ap.parse_args()
    try:
        if args.check_stale:
            return cmd_check_stale(args.deck)
        return cmd_export(args.deck, args.force, args.track)
    except ExportError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
