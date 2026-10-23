#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPTX 字体映射表与 CSS font-family → latin/ea 双 typeface 解析（三形态子技能 C）。

出处：字体四表（EA_FONTS / FONT_FALLBACK_WIN / GENERIC_FONT_MAP /
PPT_SAFE_FONTS）与 parse_font_family 的 latin/ea 双 typeface 策略抽取仿写自
ppt-master v6.6.0（MIT License, Copyright (c) 2025-2026 Hugo He）
  source/ppt-master/skills/ppt-master/scripts/svg_to_pptx/drawingml/utils.py
（EA_FONTS≈L60 / FONT_FALLBACK_WIN≈L97 / GENERIC_FONT_MAP≈L152 /
PPT_SAFE_FONTS≈L173 / parse_font_family≈L3234）。
按 MIT 许可复制并保留出处；本文件不 import ppt-master 任何模块。

策略要点（与 ppt-master 一致）：
- 优先 Windows 可用字体（PPTX 主要在 Windows/Office 打开）；macOS/Linux
  专有字体经 FONT_FALLBACK_WIN 映射；
- 第一个具名 Latin 字体进 latin，第一个具名 CJK 字体进 ea；只有 CJK 字体
  时 latin 复用 ea（PowerPoint 对 CJK 文本会走 ea typeface）；
- 通用族（sans-serif 等）只在先于一切具名字体出现时才填 latin；
- ea 永远落到 CJK 能力字体：栈内无 CJK 字体时按 deck 语言选系统回退
  （zh→Microsoft YaHei/SimSun、zh-hant→Microsoft JhengHei、ja→Yu Gothic、
  ko→Malgun Gothic），latin 为衬线时 EA 回退取衬线 CJK（SimSun 系）。

直接运行本文件执行内置单元自测（含 CJK → ea typeface 断言）。
"""
# ---------------------------------------------------------------------------
# 已知东亚字体（ppt-master utils.py L60，MIT）
EA_FONTS = {
    'PingFang SC', 'PingFang TC', 'PingFang HK',
    'Microsoft YaHei', 'Microsoft JhengHei',
    'SimSun', 'SimHei', 'FangSong', 'KaiTi', 'STKaiti',
    'STHeiti', 'STSong', 'STFangsong', 'STXihei', 'STZhongsong',
    'Hiragino Sans', 'Hiragino Sans GB', 'Hiragino Mincho ProN',
    'Hiragino Kaku Gothic ProN', 'Hiragino Kaku Gothic Pro',
    'Hiragino Mincho Pro',
    'Noto Sans SC', 'Noto Sans TC', 'Noto Serif SC', 'Noto Serif TC',
    'Noto Sans CJK SC', 'Noto Serif CJK SC',
    'Noto Sans JP', 'Noto Serif JP', 'Noto Sans CJK JP',
    'Source Han Sans SC', 'Source Han Sans TC',
    'Source Han Serif SC', 'Source Han Serif TC',
    'Source Han Sans JP', 'Source Han Serif JP',
    'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
    'YouYuan', 'LiSu', 'HuaWenKaiTi',
    'Heiti TC', 'Kaiti TC', 'Songti SC', 'Songti TC',
    # Windows 10/11 + Office 默认/常见简中
    'DengXian', 'DengXian Light', 'DengXian Bold', 'Microsoft YaHei UI',
    # Office 华文/方正标题字（非全机预装）
    'STXingkai', 'STLiti', 'STXinwei', 'STHupo', 'STCaiyun',
    'FZShuTi', 'FZYaoti',
    # 常见繁中（Office）
    'DFKai-SB', 'MingLiU', 'PMingLiU', 'MingLiU_HKSCS',
    'MingLiU-ExtB', 'PMingLiU-ExtB',
    'Microsoft JhengHei UI',
    # 日文（Windows 可用）
    'Yu Gothic', 'Yu Gothic UI', 'Yu Mincho',
    'Meiryo', 'Meiryo UI', 'メイリオ',
    'MS Gothic', 'MS Mincho', 'MS PGothic', 'MS PMincho', 'MS UI Gothic',
    # 韩文
    'Malgun Gothic', 'Gulim', 'Dotum', 'Batang',
    'Noto Sans KR', 'Noto Serif KR',
}
SYSTEM_FONTS = {'system-ui', '-apple-system', 'BlinkMacSystemFont'}

# macOS/Linux 专有字体 → Windows 等价（ppt-master utils.py L97，MIT）
FONT_FALLBACK_WIN = {
    '微软雅黑': 'Microsoft YaHei',
    'PingFang SC': 'Microsoft YaHei',
    'PingFang TC': 'Microsoft JhengHei',
    'PingFang HK': 'Microsoft JhengHei',
    'Heiti TC': 'Microsoft JhengHei',
    'Kaiti TC': 'DFKai-SB',
    'Hiragino Sans': 'Microsoft YaHei',
    'Hiragino Sans GB': 'Microsoft YaHei',
    'Hiragino Mincho ProN': 'SimSun',
    'STHeiti': 'SimHei',
    'STSong': 'SimSun',
    'STKaiti': 'KaiTi',
    'STFangsong': 'FangSong',
    'STXihei': 'Microsoft YaHei',
    'STZhongsong': 'SimSun',
    'Songti SC': 'SimSun',
    'Songti TC': 'PMingLiU',
    'Noto Sans SC': 'Microsoft YaHei',
    'Noto Sans CJK SC': 'Microsoft YaHei',
    'Noto Sans TC': 'Microsoft JhengHei',
    'Noto Serif SC': 'SimSun',
    'Noto Serif CJK SC': 'SimSun',
    'Noto Serif TC': 'PMingLiU',
    'メイリオ': 'Meiryo',
    'Source Han Sans SC': 'Microsoft YaHei',
    'Source Han Sans TC': 'Microsoft JhengHei',
    'Source Han Serif SC': 'SimSun',
    'Source Han Serif TC': 'PMingLiU',
    'Source Han Sans JP': 'Noto Sans JP',
    'Source Han Serif JP': 'Noto Serif JP',
    'WenQuanYi Micro Hei': 'Microsoft YaHei',
    'WenQuanYi Zen Hei': 'Microsoft YaHei',
    # Latin（macOS / Linux / Web → Windows）
    'SF Pro': 'Segoe UI',
    'SF Pro Display': 'Segoe UI',
    'SF Pro Text': 'Segoe UI',
    'SF Mono': 'Consolas',
    'Menlo': 'Consolas',
    'Monaco': 'Consolas',
    'Helvetica Neue': 'Arial',
    'Helvetica': 'Arial',
    'Roboto': 'Segoe UI',
    'Ubuntu': 'Segoe UI',
    'Liberation Sans': 'Arial',
    'Liberation Serif': 'Times New Roman',
    'Liberation Mono': 'Consolas',
    'DejaVu Sans': 'Segoe UI',
    'DejaVu Serif': 'Times New Roman',
    'DejaVu Sans Mono': 'Consolas',
}

# 通用族 → Windows 具体字体（ppt-master utils.py L152，MIT）
GENERIC_FONT_MAP = {
    'monospace': 'Consolas',
    'sans-serif': 'Segoe UI',
    'serif': 'Times New Roman',
}

# Office/OS 预装安全字体（小写；ppt-master utils.py L173，MIT）——
# 落在表外的 typeface 需要自定义安装，导出报告据此告警
PPT_SAFE_FONTS = frozenset({
    'microsoft yahei', 'simhei', 'simsun', 'kaiti', 'fangsong',
    'dengxian',
    'microsoft jhenghei', 'microsoft jhenghei ui', 'pmingliu', 'mingliu',
    'mingliu_hkscs', 'dfkai-sb',
    'pingfang sc', 'heiti sc', 'songti sc', 'stsong',
    'pingfang tc', 'pingfang hk', 'heiti tc', 'songti tc', 'kaiti tc',
    'yu gothic', 'yu gothic ui', 'yu mincho',
    'meiryo', 'meiryo ui',
    'ms gothic', 'ms mincho', 'ms pgothic', 'ms pmincho', 'ms ui gothic',
    'malgun gothic', 'gulim', 'dotum', 'batang',
    'nirmala ui', 'mangal', 'kokila', 'aparajita', 'utsaah',
    'leelawadee ui', 'leelawadee', 'cordia new', 'angsana new', 'browallia new',
    'david', 'miriam', 'frank ruehl', 'gisha', 'levenim mt', 'narkisim', 'aharoni',
    'arial', 'arial black', 'calibri', 'segoe ui', 'verdana',
    'helvetica', 'helvetica neue', 'tahoma', 'trebuchet ms',
    'times new roman', 'times', 'georgia', 'cambria', 'cambria math', 'palatino',
    'garamond', 'book antiqua',
    'consolas', 'courier new', 'menlo', 'monaco',
    'impact',
})

_FONT_CANONICAL_NAMES = {
    name.casefold(): name
    for name in EA_FONTS | SYSTEM_FONTS | FONT_FALLBACK_WIN.keys() | GENERIC_FONT_MAP.keys()
}

# latin 为衬线且无 EA 指定时，EA 回退取衬线 CJK（SimSun 而非雅黑）
_SERIF_LATIN = {
    'Times New Roman', 'Georgia', 'Garamond', 'Palatino', 'Palatino Linotype',
    'Book Antiqua', 'Cambria', 'SimSun', 'Liberation Serif', 'DejaVu Serif',
}

# 语言 → EA 系统回退（无衬线, 衬线）（ppt-master utils.py L3205，MIT）
_EA_DEFAULTS_BY_LANGUAGE = (
    (('ja',), ('Yu Gothic', 'Yu Mincho')),
    (('ko',), ('Malgun Gothic', 'Batang')),
    (('zh-hant', 'zh-tw', 'zh-hk', 'zh-mo'), ('Microsoft JhengHei', 'PMingLiU')),
)
# macOS 日文字体 → Windows 日文面孔（不落到中文面孔）
_JA_FONT_FALLBACK_WIN = {
    'Hiragino Sans': 'Yu Gothic',
    'Hiragino Kaku Gothic ProN': 'Yu Gothic',
    'Hiragino Kaku Gothic Pro': 'Yu Gothic',
    'Hiragino Mincho ProN': 'Yu Mincho',
    'Hiragino Mincho Pro': 'Yu Mincho',
}


def _language_is(language, prefix):
    """BCP-47 标签等于或以某子标签前缀开头。"""
    tag = (language or '').lower()
    return tag == prefix or tag.startswith(prefix + '-')


def _ea_default(language, serif):
    """deck 语言对应的 Windows EA 回退面孔。"""
    for prefixes, faces in _EA_DEFAULTS_BY_LANGUAGE:
        if any(_language_is(language, p) for p in prefixes):
            return faces[1] if serif else faces[0]
    return 'SimSun' if serif else 'Microsoft YaHei'


def parse_font_family(font_family_str, language=None):
    """CSS font-family 字符串 → {'latin', 'ea'} typeface 对（仿写 ppt-master）。

    language 为 deck 的 BCP-47 主语言（如 'zh-CN'），栈内无 CJK 字体时决定
    EA 回退（日文永不错落中文面孔）。
    """
    is_japanese = _language_is(language, 'ja')
    if not font_family_str:
        return {'latin': 'Segoe UI', 'ea': _ea_default(language, False)}

    fonts = [f.strip().strip("'\"") for f in font_family_str.split(',')]
    latin_font = None
    ea_font = None

    for font in fonts:
        font = _FONT_CANONICAL_NAMES.get(font.casefold(), font)
        if font in SYSTEM_FONTS:
            continue
        if font in GENERIC_FONT_MAP:
            # 通用族只在先于一切具名字体时填 latin：具名 CJK 之后的
            # sans-serif 不得把该 run 的拉丁字形拽到别的面孔
            if latin_font is None and ea_font is None:
                latin_font = GENERIC_FONT_MAP[font]
            continue

        win_font = (
            _JA_FONT_FALLBACK_WIN.get(font) if is_japanese else None
        ) or FONT_FALLBACK_WIN.get(font, font)
        if font in EA_FONTS or win_font in EA_FONTS:
            ea_font = ea_font or win_font
        else:
            latin_font = latin_font or win_font

    # 只有 CJK 面孔时 latin 复用之（PowerPoint 对 CJK 文本走 ea typeface）
    if not latin_font and ea_font:
        latin_font = ea_font

    final_latin = latin_font or 'Segoe UI'

    # ea 永远是 CJK 能力字体
    if not ea_font:
        ea_font = _ea_default(language, final_latin in _SERIF_LATIN)

    return {'latin': final_latin, 'ea': ea_font}


def unsafe_exported_font_faces(font_family_str, language=None):
    """解析结果中不在 PPT 安全字体表内的 typeface（需自定义安装，报告告警用）。"""
    return {
        role: family
        for role, family in parse_font_family(font_family_str, language).items()
        if family.strip().lower() not in PPT_SAFE_FONTS
    }


# ---------------------------------------------------------------------------
def _self_test():
    """内置单元自测（python3 pptx_font_maps.py 直接运行）。"""
    cases = [
        # (font-family 栈, language, 期望 latin, 期望 ea)
        # CJK 栈：PingFang → Windows 雅黑；latin 复用 ea（无具名 latin）
        ('"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif', 'zh-CN',
         'Microsoft YaHei', 'Microsoft YaHei'),
        # B1 瑞士栈：Helvetica Neue→Arial 进 latin，PingFang→雅黑进 ea
        ('"Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif', 'zh-CN',
         'Arial', 'Microsoft YaHei'),
        # A1 衬线栈：Songti SC→SimSun；body PingFang→雅黑
        ('"Songti SC","Noto Serif SC","STSong",serif', 'zh-CN',
         'SimSun', 'SimSun'),
        # mono 栈：SF Mono→Consolas；无 CJK → EA 系统回退（Consolas 非衬线 → 雅黑）
        ('"SF Mono","JetBrains Mono","Menlo",monospace', 'zh-CN',
         'Consolas', 'Microsoft YaHei'),
        # 纯拉丁栈 + zh：ea 回退雅黑
        ('"Helvetica Neue",Arial,sans-serif', 'zh-CN', 'Arial', 'Microsoft YaHei'),
        # 纯拉丁衬线栈：ea 回退 SimSun（衬线 CJK）
        ('Georgia,serif', 'zh-CN', 'Georgia', 'SimSun'),
        # 日文 deck：无 CJK 字体 → Yu Gothic；Hiragana → Yu Gothic（不落中文）
        ('"Hiragino Sans","Helvetica Neue",sans-serif', 'ja', 'Arial', 'Yu Gothic'),
        ('"Helvetica Neue",sans-serif', 'ja', 'Arial', 'Yu Gothic'),
        # 繁中 deck
        ('"Helvetica Neue",sans-serif', 'zh-TW', 'Arial', 'Microsoft JhengHei'),
        # 空栈
        ('', 'zh-CN', 'Segoe UI', 'Microsoft YaHei'),
        # 具名 CJK 之后的通用族不得抢占 latin
        ('"PingFang SC",sans-serif', 'zh-CN', 'Microsoft YaHei', 'Microsoft YaHei'),
    ]
    fails = []
    for stack, lang, want_latin, want_ea in cases:
        got = parse_font_family(stack, lang)
        if got['latin'] != want_latin or got['ea'] != want_ea:
            fails.append('栈=%r lang=%s → %r，期望 latin=%r ea=%r'
                         % (stack, lang, got, want_latin, want_ea))
    # 安全字体告警路径
    unsafe = unsafe_exported_font_faces('"LXGW WenKai","PingFang SC",sans-serif', 'zh-CN')
    assert unsafe.get('latin') == 'LXGW WenKai', '自定义字体应被告警：%r' % unsafe
    assert unsafe_exported_font_faces('"PingFang SC",sans-serif', 'zh-CN') == {}, \
        '雅黑在安全表内不应告警'
    for f in fails:
        print('FAIL', f)
    print('自测：%d/%d 通过' % (len(cases) - len(fails), len(cases)))
    return 0 if not fails else 1


if __name__ == '__main__':
    import sys
    sys.exit(_self_test())
