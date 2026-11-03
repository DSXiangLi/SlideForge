#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三形态 M2 · 子技能 A：页面烙入生图指令编译器（docs/design/page-render-mode.md §4）。

消费 extract-manifest.py 产出的 manifest.json，为用户逐页选定的烙入页
按七节模板（Canvas / Deck Goal / Global Style / Style Anchor / Text /
Layout / Constraints）确定性拼装生图指令，落盘到 prompts/ 工作区目录。

用法：
  python3 compile-bake-prompts.py <manifest.json> --pages cover,closing \
      --out-dir <deck目录>/prompts \
      [--goal "deck 主题与受众一句话"] [--style "全 deck 统一风格段"] \
      [--plan plan.json] [--anchor cover.png]

输入来源（确定性拼装，禁即兴）：
  - Text 段：100% 逐字来自 manifest 该页 texts[].content（防幻觉硬规则，
    harness 校验精确子串），脚本不增删改任何字符；
  - Global Style：manifest 的 theme（id/variant/tokens 具体色值）自动拼装。
    主题在 theme.md 声明了 **bake_brief**（D1 风格圣经）时，整段结构化
    简报由本脚本原样注入（v2 起）；无简报主题回退为散文（--style/plan）
    + token 色值——向后兼容，24 主题铺量前必须能跑；
  - Deck Goal / Layout：--goal / plan.json 提供（页计划表的呈现方案 +
    叙事角色）。plan.json 形状：
      {"goal": "…", "style": "…", "anchor": "cover.png",
       "pages": {"<slide_id>": {"layout": "本页构图指令", "role": "cover",
                                "restructure": true}}}
    CLI 参数优先于 plan 同名字段。goal 与每个选定页的 layout 为必填。
    role 可省：缺省按 slide id 关键词 → 文本量推断（规则见
    bake-prompts.md §6.1），推断结果写进 Layout 节首行；
    restructure / decorate（v5，可选，互斥——restructure 优先）：
    restructure=true → 布局重构授权段（平铺文本 → 结构化信息图，§6.5）；
    decorate=true → 装饰升维授权段（高密度页内容不动、只升氛围，§6.6）；
    两者都替代一般构图授权行；
  - Style Anchor：内容锚而非临摹目标（v3 升维语义：参考图只对齐文字内容 /
    信息层级 / 色系基调，构图与视觉按简报 uplift 升维）；`--anchor none`
    或 plan.anchor="none" 时整节省略（纯文生图臂）；
  - Constraints：通用五条 + 通用反 AI-slop 清单（v2 起）+ 主题 avoid
    清单（有简报时）。

v3 升维语义（2026-10-07 用户裁决）：烙入 = 内容忠实 + 视觉升维，不是
保真封存——保真需求由保真导出轨（PDF/SVG）承担。参考图是内容锚，
蓝图是信息结构纪律，产物必须在材质/光影/纵深/肌理上超越扁平网页截图。

v4（2026-10-08 用户目检 D 组后）：内容锚措辞收紧为"只提供①文字内容与
信息层级②配色基调，其余一律不参照"；新增「Uplift 升维手段」节（六维
工具箱：光线/质感/插画/布局/容器/字体），回退路径同样携带。

幂等：同一输入重跑，产物字节一致（覆盖写）。退出码：成功 0，任一失败 1。
"""
import argparse
import json
import os
import re
import sys

ROLE_LABEL = {'title': '标题', 'body': '正文', 'annotation': '标注', 'furniture': '家具'}

CANVAS = '16:9 整页幻灯片，2560×1440，无页码无水印'
# 内容锚（v4，用户裁决后收紧）：参考图只提供内容与配色两样东西，其余一律不参照——
# i2i 场景下"匹配锚图"类措辞是最高权重指令，任何含糊都会被读成临摹许可
ANCHOR_LINE = ('附件图 = 该页的 HTML 实现截图。它只提供两样东西：① 文字内容与信息层级；'
               '② 配色基调。除此之外一律不参照——光线、质感、材质、插画、布局、容器形态、'
               '字体表现都必须按本指令重新设计，不得沿用参考图的扁平网页渲染。'
               '若输出与参考图在构图或质感上趋同，视为失败')
# 升维手段（v4）：通用六维工具箱，插在 Global Style 与 Style Anchor 之间；
# 回退路径（主题无 bake_brief）同样保留此节
UPLIFT_LEVERS = [
    '在风格圣经 uplift 方向的指引下，从以下六个维度全面升维，每一维都要可见地超越参考图：',
    '- 光线：定义明确光源（方向/强弱/色温），用明暗过渡与真实投影塑造空间层次；',
    '- 质感：为表面指定具体材质与肌理（按主题 uplift 的名目），禁止默认扁平填充；',
    '- 插画：核心概念图形化/隐喻化表达，画面不停留在文字排版；',
    '- 布局：在角色蓝图的位置/数量/层级纪律内重新构图，主动创造焦点轴与视觉张力；',
    '- 容器：卡片/分隔/框架的形态按主题语言重新设计（描边/投影/材质化），禁止默认矩形平铺；',
    '- 字体：标题按 typography_bake 重构与材质化，成为画面本体而非贴字。',
]
CONSTRAINTS = [
    '中文必须清晰可读，不乱码、不缺字',
    '文字逐字渲染，不得增删改（含标点与数字）',
    '不出血、不裁切内容',
    '不渲染页码与水印',
    '整页即幻灯片本体，不留白边、不加画框',
]
# 通用反 AI-slop 清单（D3）：通用负向约束，与主题无关、与主题 avoid 清单并列
ANTI_SLOP = [
    '禁通用 AI 默认质感：mesh 渐变、aurora 极光斑、悬浮玻璃球、玻璃拟态、紫青霓虹辉光',
    '禁廉价自媒体海报感：促销横幅、爆炸贴、带货大字报、红金节庆套路',
    '禁无设计主张的模板构图（裸居中标题+副题+一行日期的默认海报）；主题气质要求中轴对称时，对称必须由主题母题承载仪式感而非裸摆',
    '禁页眉/页脚/品牌 logo/界面按钮等 chrome——页面即内容本体',
    '禁 emoji、禁图标排排坐、禁默认圆角卡片网格',
    '必须有一个可见的设计主张（字型重构 / 主导隐喻 / 焦点轴），装饰全部去掉后结构仍成立',
]

THEMES_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, 'references', 'themes'))

# 页角色缺省推断（规则文本见 bake-prompts.md §6.1，两处必须同步）
ROLE_KEYWORDS = [
    ('cover', ('cover', 'title', '首页', '封面')),
    ('divider', ('divider', 'section', 'chapter', 'part', 'toc', 'agenda', '目录', '章节')),
    ('closing', ('closing', 'end', 'thanks', 'finale', '封底', '结尾', '致谢')),
]
ROLE_FALLBACK = {'closing': 'key-message'}  # 蓝图缺角色时的回落链，末端 key-message


def fail(msg):
    print('[compile-bake-prompts] ERROR: %s' % msg, file=sys.stderr)
    return 1


def _find_theme_file(theme_id):
    """在 themes/<分类>/<id>/theme.md 中查找主题文件。"""
    if not theme_id:
        return None
    for cat in os.listdir(THEMES_DIR):
        cat_dir = os.path.join(THEMES_DIR, cat)
        if not os.path.isdir(cat_dir) or cat == 'index.md':
            continue
        theme_file = os.path.join(cat_dir, theme_id, 'theme.md')
        if os.path.isfile(theme_file):
            return theme_file
    return None


def load_bake_brief(theme_id):
    """从 themes/<分类>/<id>/theme.md 提取该主题 **bake_brief** 字段组的 json 围栏块。

    返回 dict 或 None（主题无简报 → 回退路径）。块存在但 JSON 非法 /
    主题文件不可读属 authoring bug（sync-themes.mjs Schema 校验负责
    拦截），此处抛出由调用方报错，不静默降级。"""
    if not theme_id:
        return None
    theme_file = _find_theme_file(theme_id)
    if not theme_file:
        return None
    with open(theme_file, encoding='utf-8') as f:
        md = f.read()
    gm = re.search(r'^\*\*bake_brief\*\*\s*$', md, re.M)
    if not gm:
        return None
    fm = re.search(r'```json\s*\n(.*?)```', md[gm.end():], re.S)
    if not fm:
        raise ValueError('主题 %s 声明了 bake_brief 但缺 json 围栏块' % theme_id)
    try:
        return json.loads(fm.group(1))
    except ValueError as e:
        raise ValueError('主题 %s 的 bake_brief JSON 非法：%s' % (theme_id, e))


def infer_role(slide_id, page, plan_role):
    if plan_role:
        return plan_role
    sid = (slide_id or '').lower()
    for role, keywords in ROLE_KEYWORDS:
        if any(k in sid for k in keywords):
            return role
    n = len([t for t in page.get('texts') or [] if (t.get('content') or '').strip()])
    return 'key-message' if n <= 5 else 'analysis'


def pick_blueprint(brief, role):
    """蓝图回落链：显式角色 → ROLE_FALLBACK → key-message → 首个蓝图。"""
    blueprints = (brief or {}).get('layout_blueprints') or {}
    seen = set()
    cur = role
    while cur and cur not in seen:
        if cur in blueprints:
            return cur, blueprints[cur]
        seen.add(cur)
        cur = ROLE_FALLBACK.get(cur, 'key-message' if cur != 'key-message' else None)
    if blueprints:
        first = next(iter(blueprints))
        return first, blueprints[first]
    return None, None


def brief_json(brief):
    # 注入形式 = 单行紧凑 JSON：去缩进/换行使 token 最省，ensure_ascii=False
    # 避免 \uXXXX 转义膨胀；围栏 json 块给模型明确的结构边界。分节 markdown
    # 等价内容约多 30% token，弃。
    return json.dumps(brief, ensure_ascii=False, separators=(',', ':'))


def global_style_lines(manifest, style_text, brief):
    """Global Style 段：风格描述文字（提供时前置）+ theme tokens 逐字拼装
    + 风格圣经注入（主题有 bake_brief 时）。"""
    lines = []
    if style_text:
        lines.append(style_text)
        lines.append('')
    theme = manifest.get('theme') or {}
    if theme.get('id'):
        line = '主题：%s' % theme['id']
        if theme.get('variant'):
            line += '（配色变体：%s）' % theme['variant']
        lines.append(line)
    tokens = theme.get('tokens') or {}
    if tokens:
        lines.append('主题 token 色系（逐字来自 manifest）：')
        for k in sorted(tokens):
            lines.append('- %s: %s' % (k, tokens[k]))
    if brief:
        lines.append('')
        lines.append('风格圣经（bake brief · 结构化生成指令，优先于一切泛化风格猜测；具体色值以上表 token 为准）：')
        lines.append('```json')
        lines.append(brief_json(brief))
        lines.append('```')
    return lines


# 布局重构授权（v5，plan.json 该页 restructure:true 时启用，替代一般构图授权）——
# 适用条件与纪律见 bake-prompts.md §6.5
RESTRUCTURE_LINE = ('布局重构授权：本页 HTML 为平铺直叙的文本呈现。授权你对内容做整体布局重构——'
                    '分析内容的关系类型（流程/对比/层级/循环/矩阵/时间轴——参照 motifs 八类隐喻），'
                    '把段落文本重新组织为结构化信息图呈现（节点、连线、卡片、轴、编号系统均可重新设计）。'
                    '硬约束：全部文字逐字保留、信息层级不变、配色基调不变；'
                    '除此之外版式不受参考图约束，目标是最优视觉表达而非忠实复刻。')

# 装饰升维授权（v5，plan.json 该页 decorate:true 时启用，替代一般构图授权）——
# 高密度内容页专用：内容不动，只升维氛围（纪律见 bake-prompts.md §6.6）
DECORATE_LINE = ('装饰升维授权：本页为高密度内容页。内容区块与全部文字保持原位原样'
                 '（逐字、原布局结构不动）；授权的升维范围：'
                 '① 布局节奏微调（间距/对齐/呼吸感，不重组内容块）；'
                 '② 底部与边缘增加主题插画背景带（低对比、不压文字区、不穿越文字）；'
                 '③ 装饰元素（主题母题的角饰/分隔线/水印级纹理）；'
                 '④ 光线与质感按 uplift 方向作用于背景与容器表面。'
                 '文字区背景必须保持可读的对比度。')


def layout_lines(layout, role, role_source, blueprint_role, blueprint, restructure=False,
                 decorate=False):
    lines = ['页角色：%s（%s）' % (role, role_source)]
    if blueprint:
        lines.append('页角色蓝图（位置 × 数量 × 标签，来自主题风格圣经 %s 角色；候选起点——下文构图描述在其上细化内容，不得推翻角色纪律）：' % blueprint_role)
        lines.append('```json')
        lines.append(json.dumps(blueprint, ensure_ascii=False, separators=(',', ':')))
        lines.append('```')
    if restructure:
        lines.append(RESTRUCTURE_LINE)
    elif decorate:
        lines.append(DECORATE_LINE)
    elif blueprint:
        # 升维授权（v3）：蓝图是信息结构纪律，不是版式复刻纪律
        lines.append('构图授权：蓝图只约束信息的位置 / 数量 / 层级，不构成对构图的复刻要求——'
                     '在蓝图纪律内重新设计画面，材质 / 光影 / 纵深 / 肌理按风格圣经 uplift 方向升维。')
    lines.append(layout)
    return lines


def compile_page(page, goal, style_text, layout, anchor, manifest, brief, role, role_source,
                 restructure=False, decorate=False):
    blueprint_role, blueprint = pick_blueprint(brief, role)
    lines = []
    lines.append('# 生图指令：%s' % page.get('slide_id', ''))
    lines.append('')
    lines.append('## Canvas')
    lines.append(CANVAS)
    lines.append('')
    lines.append('## Deck Goal')
    lines.append(goal)
    lines.append('')
    lines.append('## Global Style')
    lines.extend(global_style_lines(manifest, style_text, brief))
    lines.append('')
    lines.append('## Uplift 升维手段')
    lines.extend(UPLIFT_LEVERS)
    lines.append('')
    if anchor:
        lines.append('## Style Anchor')
        lines.append(ANCHOR_LINE + '（附件文件：%s）' % anchor)
        lines.append('')
    lines.append('## Text')
    lines.append('以下为本页全部文字，逐字摘自 deck manifest。文字必须逐字渲染，不得增删改：')
    for t in page.get('texts') or []:
        content = (t.get('content') or '').strip()
        if not content:
            continue
        if t.get('role') == 'furniture':
            continue  # 家具（页眉/页码）是 chrome，Constraints 明禁渲染，不进文字契约
        label = ROLE_LABEL.get(t.get('role'), '正文')
        lines.append('- [%s] %s' % (label, content))
    if brief:
        # 文字视觉化改造授权（v3）：逐字是内容纪律，不是排版纪律
        lines.append('文字逐字不变，但文字是画面的一部分——标题按风格圣经 typography_bake '
                     '做视觉化改造（重构 / 材质化），不是贴在画面上的字。')
    lines.append('')
    lines.append('## Layout')
    lines.extend(layout_lines(layout, role, role_source, blueprint_role, blueprint,
                              restructure=restructure, decorate=decorate))
    lines.append('')
    lines.append('## Constraints')
    for c in CONSTRAINTS:
        lines.append('- %s' % c)
    for c in ANTI_SLOP:
        lines.append('- %s' % c)
    if brief and brief.get('avoid'):
        lines.append('- 主题禁忌（avoid）：%s' % brief['avoid'])
    lines.append('')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description='页面烙入生图指令编译器（三形态 M2）')
    ap.add_argument('manifest', help='extract-manifest.py 产出的 manifest.json 路径')
    ap.add_argument('--pages', required=True,
                    help='逗号分隔的 slide_id 清单（用户逐页选定的烙入页）')
    ap.add_argument('--out-dir', required=True, help='指令文件输出目录（prompts/ 工作区）')
    ap.add_argument('--goal', help='deck 主题与受众一句话（覆盖 plan.goal）')
    ap.add_argument('--style', help='全 deck 统一风格段（覆盖 plan.style）')
    ap.add_argument('--plan', help='页计划 JSON（goal/style/anchor/各页 layout）')
    ap.add_argument('--anchor', help='风格锚截图文件名（覆盖 plan.anchor，缺省 cover.png；"none" = 无参考图纯文生图臂，Style Anchor 整节省略）')
    args = ap.parse_args()

    try:
        with open(args.manifest, encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception as e:
        return fail('manifest 读取失败：%s（%s）' % (args.manifest, e))

    plan = {}
    if args.plan:
        try:
            with open(args.plan, encoding='utf-8') as f:
                plan = json.load(f)
        except Exception as e:
            return fail('plan 读取失败：%s（%s）' % (args.plan, e))

    goal = args.goal or plan.get('goal')
    style_text = args.style or plan.get('style')
    anchor = args.anchor or plan.get('anchor') or 'cover.png'
    if anchor.strip().lower() in ('none', 'off'):  # 纯文生图臂：无参考图，整节省略
        anchor = None
    plan_pages = plan.get('pages') or {}

    page_ids = [p.strip() for p in args.pages.split(',') if p.strip()]
    if not page_ids:
        return fail('--pages 为空：烙入页由用户逐页选定，必须显式给出')
    if not goal:
        return fail('缺 Deck Goal：经 --goal 或 plan.goal 提供（deck 主题与受众一句话）')

    theme_id = ((manifest.get('theme') or {}).get('id') or '').strip()
    try:
        brief = load_bake_brief(theme_id)
    except (OSError, ValueError) as e:
        return fail('风格圣经加载失败：%s' % e)

    by_id = {p.get('slide_id'): p for p in manifest.get('pages') or []}
    errors = []
    compiled = []
    for pid in page_ids:
        page = by_id.get(pid)
        if not page:
            errors.append('manifest 中不存在页：%s' % pid)
            continue
        plan_page = plan_pages.get(pid) or {}
        layout = plan_page.get('layout')
        if not layout:
            errors.append('页 %s 缺 Layout（plan.pages.%s.layout：页计划表的呈现方案 + 叙事角色）' % (pid, pid))
            continue
        plan_role = plan_page.get('role')
        role = infer_role(pid, page, plan_role)
        role_source = 'plan 显式声明' if plan_role else '缺省推断（bake-prompts.md §6.1）'
        compiled.append((pid, compile_page(page, goal, style_text, layout, anchor,
                                           manifest, brief, role, role_source,
                                           restructure=bool(plan_page.get('restructure')),
                                           decorate=bool(plan_page.get('decorate')))))
    if errors:
        for e in errors:
            print('[compile-bake-prompts] ERROR: %s' % e, file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    for pid, text in compiled:
        path = os.path.join(args.out_dir, '%s.md' % pid)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    print('[compile-bake-prompts] 已编译 %d 页生图指令 → %s（%s）'
          % (len(compiled), args.out_dir, '、'.join(pid for pid, _ in compiled)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
