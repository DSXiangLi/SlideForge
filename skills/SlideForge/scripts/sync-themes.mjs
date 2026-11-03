#!/usr/bin/env node
/* sync-themes.mjs —— 主题数据多文件同步 + Schema 校验
 *
 * 数据源：<当前技能目录>/references/themes/<分类>/<id>/theme.md（29 套七层
 *         重主题 + 配色变体，Schema 化 G0–G9 字段组，唯一事实源；Schema 规范
 *         见 docs/design/theme-schema.md 与 docs/design/theme-expression-stack.md）
 *         索引文件 themes/index.md 含分类框架与全局规则（不参与解析）。
 * 目标：  editor.html 内 PANEL_DATA.questions[0].options（面板主题卡片，
 *         含变体与 theme_css）+ PANEL_DATA.questions[2].options（动效组，
 *         五层启用矩阵——语义源是 references/motion.md v3 §5，本脚本只做
 *         写入载体，选项变更须先改 motion.md）
 *
 * 解析每套主题文件（# A1 名称 → G0 bullets + **Gx** 字段组 + ```css token
 * 块 + **Variants** 小节的 #### 变体），兼任 schema 校验器，生成带 focus
 * 分组信息的面板卡片 JSON，幂等写回 editor.html 的标记区间：
 *   /*__THEMES_JSON_BEGIN__*\/ ... /*__THEMES_JSON_END__*\/
 *   /*__MOTION_JSON_BEGIN__*\/ ... /*__MOTION_JSON_END__*\/
 *
 * 校验项：
 *   1. 主题数 == 28、id 唯一；
 *   2. G0（id/气质/适用/focus/世界参考/unforgettable/分化声明）、G1（6 色
 *      token 全为合法 hex + accent 预算声明）、G2（3 字体栈 + 字重倾向 +
 *      字号对比 + 字重映射 + 标题修饰）字段齐全；
 *   3. focus 声明的字段组全部显式给出：G3 须非 flat 三 token；G4 须
 *      圆角/hairline/阴影；G9 须词汇 + css 块；
 *   4. G3 立场必填（flat 也要显式写出）：三 token 齐全；
 *      --texture-type ∈ flat/glow/grain/paper/hand-drawn/aura；
 *      --texture-scope ∈ cover/all；flat ⇔ layer 为 none；
 *      layer 不得引用外部图片资产（url() 只允许 data: 内联）；
 *      G3 可选字段 css_recipes 引用的配方名必须存在于
 *      references/compositing.md（材料合成词汇表）；
 *   5. 无主题外 hex（所有色值只允许出现在 ```css 代码块内）；
 *   6. focus 组合 + 核心色两两可区分：focus 组合相同的主题 accent 不得撞车，
 *      且任意两主题的 (paper, ink, accent) 三元组不得完全相同；
 *   7. 变体（G 期两级架构）：每主题基底+变体 ≥3 套配色；变体 css 只许含
 *      六色 token + 可选 --texture-* 三 token（部分覆盖，与基底 G3 合并后
 *      重跑第 4 条同款校验）；变体不得覆盖其他组；
 *   8. G9 主题 CSS 块：选择器白名单（:root / .mt-* 及其伪元素后代）、
 *      禁 @keyframes/@media/@import/@font-face、禁字面 hex、禁外部 url()；
 *      .mt-* 类名全库唯一（跨主题不得重名）；
 *   9. 七层分化门槛（G 期）：任意两主题在 L1=G1 / L2=G2 / L3=G3(type+scope)
 *      / L4=G9 / L5=G4 / L6=G5 / L7=G8 七层中至少 3 层实质分化（规范化
 *      文本比较）；G0 分化声明须指名最近邻且逐层核验为真。
 *  10. bake_brief（D1 风格圣经，生图翻译层，不进面板 JSON）：试点主题
 *      （e3/c3/a1）必填、其余暂可选；存在时校验 JSON 可解析、六个字符串
 *      字段（含 uplift 升维路径）非空、layout_blueprints 含
 *      cover/divider/key-message/analysis 四角色且每个 section 为
 *      {position, count≥1, labels[]}、rendering_constraints ≥8 条、
 *      无字面 hex。
 *
 * 用法：node skills/SlideForge/scripts/sync-themes.mjs
 * 校验失败打印可读错误并以非零退出。零依赖，Node ≥ 20。
 */
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const THEMES_DIR = join(ROOT, 'skills/SlideForge/references/themes');
const EDITOR = join(ROOT, 'editor.html');
const COMPOSITING = join(ROOT, 'skills/SlideForge/references/compositing.md');
const EXPECTED_COUNT = 29;  /* 587621b 删 G3 后 28 套 + D4 黄铜年代（材料合成试点任务 B） */
const COLOR_TOKENS = ['--paper', '--paper-tint', '--ink', '--ink-tint', '--accent', '--accent-on'];
const FONT_TOKENS = ['--font-display', '--font-body', '--font-mono'];
const TEXTURE_TOKENS = ['--texture-type', '--texture-layer', '--texture-scope'];

/* G1 多色扩展（J2 期，docs/design/theme-multi-hue.md）：单色主题零改动；
 * 多色主题可追加 --accent-2/3、--palette-N、--hl-N（各带 -on 配对）与
 * --chart-series-N（显式图表系列，缺省回落 color-mix 推导）。 */
const MULTI_RE = /^--(accent-[23]|palette-\d+|hl-\d+)(-on)?$/;
const CHART_SERIES_RE = /^--chart-series-\d+$/;
function isMultiExtra(k) { return MULTI_RE.test(k) || CHART_SERIES_RE.test(k); }
function checkMultiPairs(id, tokens) {
  for (const k of Object.keys(tokens)) {
    if (COLOR_TOKENS.includes(k) || TEXTURE_TOKENS.includes(k)) continue;
    if (!isMultiExtra(k)) err(`${id}: G1 出现白名单外 token ${k}（多色扩展只许 --accent-2/3、--palette-N、--hl-N 及各自 -on 配对、--chart-series-N）`);
    else if (!/^#[0-9a-fA-F]{6}$/.test(tokens[k])) err(`${id}: G1 ${k} 色值非法：${tokens[k]}`);
  }
  for (const k of Object.keys(tokens)) {
    if (/^--(accent-[23]|palette-\d+|hl-\d+)$/.test(k) && !tokens[k + '-on'])
      err(`${id}: G1 多色 token ${k} 缺少 on-color 配对（${k}-on，AA 纪律）`);
  }
  const palNums = Object.keys(tokens).filter(k => /^--palette-\d+$/.test(k))
    .map(k => +k.replace('--palette-', '')).sort((a, b) => a - b);
  palNums.forEach((n, i) => {
    if (n !== i + 1) err(`${id}: --palette-* 编号须连续（1..N 不断档），实为 ${palNums.join(',')}`);
  });
}

/* bake_brief（D1 风格圣经）：试点主题必填，其余暂可选——24 主题铺量完成后
 * 把 BAKE_BRIEF_REQUIRED 改为全主题（届时校验一视同仁）。 */
const BAKE_BRIEF_REQUIRED = ['e3', 'c3', 'a1', 'b1', 'e12', 'd2', 'd4'];
const BAKE_BRIEF_ROLES = ['cover', 'divider', 'key-message', 'analysis'];
const BAKE_BRIEF_STRING_KEYS = ['visual_direction', 'palette_rule', 'typography_bake', 'uplift', 'allowed', 'avoid'];

/* focus 组 → 面板分组。分组归属规则（theme-schema.md 未规定，本脚本定义）：
 * 按"最差异化优先"取 focus 中的首项——G3 质感 > G9 装饰 > G2 字排 > G4 形态
 * > G1 配色，即非颜色维度优先于颜色（颜色是每套主题的必有维度，不构成区分度）。 */
const GROUP_META = {
  G1: { key: 'color',        short: '配色' },
  G2: { key: 'typography',   short: '字排' },
  G3: { key: 'texture',      short: '质感' },
  G4: { key: 'shape',        short: '形态' },
  G5: { key: 'motion',       short: '动效' },
  G6: { key: 'chart',        short: '图表' },
  G7: { key: 'illustration', short: '插画' },
  G8: { key: 'component',    short: '组件' },
  G9: { key: 'motif',        short: '装饰' }
};
const GROUP_PRIORITY = ['G3', 'G9', 'G2', 'G4', 'G1', 'G5', 'G6', 'G7', 'G8'];

/* 七层表达力栈 ↔ 字段组（L4 装饰母题=G9，L5 容器=G4，L6 动效签名=G5，L7 构图=G8） */
const LAYERS = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7'];

const errors = [];
function err(msg) { errors.push(msg); }
function fail(msg) {
  console.error('[sync-themes] ERROR: ' + msg);
  process.exit(1);
}

/* ---------- 读取 themes/<分类>/<id>/theme.md ---------- */
function findThemeFiles() {
  const files = [];
  for (const cat of readdirSync(THEMES_DIR)) {
    const catDir = join(THEMES_DIR, cat);
    try { if (!statSync(catDir).isDirectory()) continue; } catch { continue; }
    if (cat === 'index.md') continue;
    for (const tid of readdirSync(catDir)) {
      const tidDir = join(catDir, tid);
      try { if (!statSync(tidDir).isDirectory()) continue; } catch { continue; }
      const themeFile = join(tidDir, 'theme.md');
      try { statSync(themeFile); } catch { continue; }
      files.push({ path: themeFile, catDir: cat, tidDir: tid });
    }
  }
  return files;
}

/* 切成主题段：每文件一个主题，首行 # A1 名称 */
const segments = [];
const allMdByFile = {};  // fileId → raw md, for hex check
for (const { path: fpath, catDir, tidDir } of findThemeFiles()) {
  const md = readFileSync(fpath, 'utf8');
  const fileId = `${catDir}/${tidDir}`;
  allMdByFile[fileId] = md;
  const lines = md.split('\n');
  const h = /^#\s+([A-G]\d+)\s+(.+?)\s*$/.exec(lines[0] || '');
  if (!h) { err(`主题文件 ${fileId}/theme.md 首行不是合法标题（# A1 名称 格式）`); continue; }
  segments.push({ hid: h[1], heading: h[2], lines: lines.slice(1), fileId, catDir, tidDir });
}

function parseTheme(seg) {
  const t = { id: seg.hid.toLowerCase(), heading: seg.heading, g0: {}, groups: {}, css: {}, variants: [], catDir: seg.catDir, tidDir: seg.tidDir };
  let group = null;        // 当前 **Gx** 字段组（null = G0 区域）
  let inVariants = false;  // **Variants** 小节模式
  let variant = null;      // 当前 #### 变体
  let inCss = false;
  for (const line of seg.lines) {
    if (line.startsWith('```')) {
      if (!inCss) {
        inCss = true;
        if (inVariants) { if (!variant) err(`${t.id}: Variants 小节内出现不属于任何变体的 css 代码块`); }
        else if (!group) err(`${t.id}: 出现不在任何字段组下的 css 代码块`);
        else t.css[group] = t.css[group] || '';
      } else inCss = false;
      continue;
    }
    if (inCss) {
      if (inVariants) { if (variant) variant.css += line + '\n'; }
      else if (group) t.css[group] += line + '\n';
      continue;
    }
    if (/^\*\*Variants/.test(line)) { inVariants = true; group = null; continue; }
    const vh = /^####\s+(.+?)\s*$/.exec(line);
    if (vh) {
      if (!inVariants) err(`${t.id}: #### 变体标题出现在 **Variants** 小节之外：${vh[1]}`);
      else { variant = { name: vh[1], fields: {}, css: '' }; t.variants.push(variant); }
      continue;
    }
    const g = /^\*\*(G[0-9]|bake_brief)\b/.exec(line);
    if (g) { group = g[1]; inVariants = false; t.groups[group] = t.groups[group] || {}; continue; }
    const b = /^- \*\*(.+?)\*\*[：:]\s*(.*)$/.exec(line.trim());
    if (b) {
      if (inVariants) { if (variant) variant.fields[b[1]] = b[2].trim(); }
      else (group ? t.groups[group] : t.g0)[b[1]] = b[2].trim();
    }
  }
  return t;
}

function parseTokens(css) {
  const tokens = {};
  const re = /(--[\w-]+)\s*:\s*([^;]+);/g;
  let m;
  while ((m = re.exec(css || ''))) tokens[m[1]] = m[2].trim();
  return tokens;
}

const themes = segments.map(parseTheme);

/* ---------- 工具 ---------- */
function checkTexture(id, g3) {
  const TEXTURE_TYPES = ['flat', 'glow', 'grain', 'paper', 'hand-drawn', 'aura'];
  for (const k of TEXTURE_TOKENS)
    if (!g3[k]) err(`${id}: G3 立场必填，缺少 token ${k}`);
  if (g3['--texture-type'] && !TEXTURE_TYPES.includes(g3['--texture-type']))
    err(`${id}: G3 --texture-type 非法：${g3['--texture-type']}（枚举：${TEXTURE_TYPES.join('/')}）`);
  if (g3['--texture-scope'] && !['cover', 'all'].includes(g3['--texture-scope']))
    err(`${id}: G3 --texture-scope 非法：${g3['--texture-scope']}（枚举：cover/all）`);
  if (g3['--texture-type'] === 'flat' && g3['--texture-layer'] && g3['--texture-layer'] !== 'none')
    err(`${id}: G3 --texture-type 为 flat 时 --texture-layer 必须为 none`);
  if (g3['--texture-type'] && g3['--texture-type'] !== 'flat' && g3['--texture-layer'] === 'none')
    err(`${id}: G3 声明了非 flat 质感但 --texture-layer 为 none`);
  if (g3['--texture-layer']) {
    /* 先剥离合法的 data: 内联（含其内部嵌套的 url(%23…)），再查剩余 url() */
    const rest = g3['--texture-layer'].replace(/url\("data:[^"]*"\)/g, '');
    if (/url\(/.test(rest))
      err(`${id}: G3 --texture-layer 引用外部图片资产（纹理一律 CSS 实现，url() 只允许 "data:" 内联）`);
  }
}

/* 材料合成词汇表（compositing.md）：G3 css_recipes 字段的合法配方名来源 */
function loadRecipeNames() {
  let md = '';
  try { md = readFileSync(COMPOSITING, 'utf8'); } catch { return null; }
  const names = new Set();
  for (const m of md.matchAll(/^##\s*配方\s*\d+[：:]\s*([\w-]+)/gm)) names.add(m[1]);
  return names;
}
const RECIPE_NAMES = loadRecipeNames();

function checkCssRecipes(t) {
  const raw = t.groups.G3 && t.groups.G3['css_recipes'];
  if (!raw) return;
  if (!RECIPE_NAMES) { err(`${t.id}: 声明了 css_recipes 但 references/compositing.md 不存在或不可读`); return; }
  let names;
  try { names = JSON.parse(raw.replace(/'/g, '"')); }
  catch { err(`${t.id}: G3 css_recipes 须为 JSON 数组（如 ["film-grain","light-leak"]），实为：${raw.slice(0, 60)}`); return; }
  if (!Array.isArray(names) || !names.length || !names.every(n => typeof n === 'string'))
    { err(`${t.id}: G3 css_recipes 须为非空字符串数组`); return; }
  for (const n of names)
    if (!RECIPE_NAMES.has(n))
      err(`${t.id}: G3 css_recipes 引用不存在的配方「${n}」（合法配方见 references/compositing.md：${[...RECIPE_NAMES].join('/')}）`);
}

function checkBakeBrief(t) {
  const raw = t.css.bake_brief;
  if (!raw || !raw.trim()) { err(`${t.id}: bake_brief 缺失或为空（试点主题必填，见 Schema 表 bake_brief 行）`); return; }
  if (/#[0-9a-fA-F]{3,8}\b/.test(raw))
    err(`${t.id}: bake_brief 出现字面 hex（色彩主权在 G1，简报只写色彩行为规则，色值由 manifest token 注入）`);
  let brief;
  try { brief = JSON.parse(raw); }
  catch (e) { err(`${t.id}: bake_brief JSON 解析失败：${e.message}`); return; }
  for (const k of BAKE_BRIEF_STRING_KEYS)
    if (typeof brief[k] !== 'string' || !brief[k].trim())
      err(`${t.id}: bake_brief.${k} 缺失或为空（须为非空字符串）`);
  const bp = brief.layout_blueprints;
  if (!bp || typeof bp !== 'object' || Array.isArray(bp)) {
    err(`${t.id}: bake_brief.layout_blueprints 必须是对象（页角色 → sections 数组）`);
  } else {
    for (const role of BAKE_BRIEF_ROLES) {
      const sections = bp[role];
      if (!Array.isArray(sections) || !sections.length) {
        err(`${t.id}: bake_brief.layout_blueprints 缺页角色「${role}」`); continue;
      }
      sections.forEach((s, i) => {
        if (!s || typeof s.position !== 'string' || !s.position.trim()
            || !Number.isInteger(s.count) || s.count < 1
            || !Array.isArray(s.labels) || !s.labels.length
            || !s.labels.every(l => typeof l === 'string' && l.trim()))
          err(`${t.id}: bake_brief.layout_blueprints.${role}[${i}] 形状非法（须为 {position: 非空字符串, count: ≥1 整数, labels: 非空字符串数组}）`);
      });
    }
  }
  const rc = brief.rendering_constraints;
  if (!Array.isArray(rc) || rc.length < 8 || !rc.every(c => typeof c === 'string' && c.trim()))
    err(`${t.id}: bake_brief.rendering_constraints 须为 ≥8 条非空字符串（实为 ${Array.isArray(rc) ? rc.length + ' 条' : '非数组'}）`);
}

function stableStringify(obj) {
  return JSON.stringify(Object.keys(obj || {}).sort().map(k => [k, obj[k]]));
}
function norm(s) {
  return String(s || '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s+/g, '').toLowerCase();
}
/* 七层签名：两主题该层签名相同 = 该层不分化 */
function layerSig(t, layer) {
  switch (layer) {
    case 'L1': return norm(t.css.G1);
    case 'L2': return norm((t.css.G2 || '') + stableStringify(t.groups.G2));
    case 'L3': { const g3 = parseTokens(t.css.G3); return norm(g3['--texture-type'] + '|' + g3['--texture-scope']); }
    case 'L4': return norm((t.css.G9 || '') + stableStringify(t.groups.G9));
    case 'L5': return norm(stableStringify(t.groups.G4));
    case 'L6': return norm(stableStringify(t.groups.G5));
    case 'L7': return norm(stableStringify(t.groups.G8));
  }
}

/* ---------- Schema 校验（theme-schema.md §6 + theme-expression-stack.md 机器可验项） ---------- */
if (segments.length !== EXPECTED_COUNT)
  err(`解析出 ${segments.length} 套主题，期望 ${EXPECTED_COUNT}`);

const seenIds = new Set();
const seenMotifClasses = {};  // .mt-* 类名全库唯一
const declarations = [];      // 分化声明，二阶段核验

for (const t of themes) {
  if (seenIds.has(t.id)) err(`主题 id 重复：${t.id}`);
  seenIds.add(t.id);

  /* G0 */
  for (const k of ['id', '气质', '适用', 'focus', '世界参考', 'unforgettable', '分化声明'])
    if (!t.g0[k]) err(`${t.id}: G0 缺少字段「${k}」`);
  if (t.g0.id && t.g0.id !== t.id) err(`${t.id}: G0 id（${t.g0.id}）与标题编号不一致`);
  const focus = (t.g0.focus || '').match(/G[0-9]/g) || [];
  if (focus.length < 1 || focus.length > 2)
    err(`${t.id}: focus 须声明 1–2 个字段组，实为 ${focus.length} 个（${t.g0.focus || '空'}）`);
  if (new Set(focus).size !== focus.length) err(`${t.id}: focus 组重复（${t.g0.focus}）`);

  /* 分化声明：格式 与 <id> 分化于 Lx/Ly/Lz（≥3 层），二阶段逐层核验 */
  {
    const d = t.g0['分化声明'] || '';
    const m = /与\s*([a-gA-G]\d+)\s*分化于\s*([L\d\/、,，\s]+)/.exec(d);
    if (!m) err(`${t.id}: 分化声明格式应为「与 <id> 分化于 Lx/Ly/Lz：说明」，实为：${d.slice(0, 40)}…`);
    else {
      const layers = [...new Set(m[2].match(/L[1-7]/g) || [])];
      if (layers.length < 3) err(`${t.id}: 分化声明须列 ≥3 个分化层，实为 ${layers.length} 个（${layers.join('/')}）`);
      declarations.push({ id: t.id, neighbor: m[1].toLowerCase(), layers });
    }
  }

  /* G1 color（必填：6 色 token + accent 用量预算声明） */
  const g1 = parseTokens(t.css.G1);
  for (const k of COLOR_TOKENS) {
    if (!g1[k]) err(`${t.id}: G1 缺少 token ${k}`);
    else if (!/^#[0-9a-fA-F]{6}$/.test(g1[k])) err(`${t.id}: G1 ${k} 色值非法：${g1[k]}`);
  }
  if (!t.groups.G1 || !t.groups.G1['accent 预算'])
    err(`${t.id}: G1 缺少字段「accent 预算」（内容页面积上限/满屏特权页/首尾闭环）`);
  checkMultiPairs(t.id, g1);
  if (Object.keys(g1).some(k => /^--(accent-[23]|palette-\d+|hl-\d+)$/.test(k))
      && (!t.groups.G1 || !t.groups.G1['多色立场']))
    err(`${t.id}: 声明了多色 token 但 G1 缺「多色立场」字段（封闭色板禁令 + 分配规则 + 注意力色预算，见 docs/design/theme-multi-hue.md §一）`);

  /* G2 typography（必填：3 字体栈 + 四个字排字段） */
  const g2 = parseTokens(t.css.G2);
  for (const k of FONT_TOKENS)
    if (!g2[k]) err(`${t.id}: G2 缺少 token ${k}`);
  for (const k of ['字重倾向', '字号对比', '字重映射', '标题修饰'])
    if (!t.groups.G2 || !t.groups.G2[k]) err(`${t.id}: G2 缺少字段「${k}」`);
  /* metric_fallback（可选，M3 防线 B）：display→…；body→…；mono→… */
  if (t.groups.G2 && t.groups.G2['metric_fallback']) {
    const mf = t.groups.G2['metric_fallback'];
    const entries = mf.split(/[；;]/).map(s => s.trim()).filter(Boolean);
    if (!entries.length) err(`${t.id}: metric_fallback 为空`);
    for (const e of entries) {
      const m = /^(display|body|mono)→(.+)$/.exec(e);
      if (!m) err(`${t.id}: metric_fallback 条目非法：「${e}」（格式 display→字体A/字体B，键 ∈ display/body/mono）`);
      else if (!m[2].trim()) err(`${t.id}: metric_fallback ${m[1]} 的回退栈为空`);
    }
  }

  /* G3 texture（立场必填，flat 也要显式写出） */
  checkTexture(t.id, parseTokens(t.css.G3));
  /* G3 材料规格（可选）：css_recipes 引用 compositing.md 合法配方 */
  checkCssRecipes(t);

  /* G9 motif（装饰母题）：css 块纪律 + 类名全库唯一 */
  if (t.css.G9) {
    const css = t.css.G9;
    const stripped = css.replace(/\/\*[\s\S]*?\*\//g, '');
    if (/@(keyframes|media|import|font-face|supports)/.test(stripped))
      err(`${t.id}: G9 css 禁含 @keyframes/@media/@import/@font-face/@supports（主题块不自带动画定义，可引用骨架已有 keyframes）`);
    if (/#[0-9a-fA-F]{3,8}\b/.test(stripped))
      err(`${t.id}: G9 css 出现字面 hex（色彩主权在 G1，只许 var(--*)/color-mix()）`);
    if (/url\(/.test(stripped.replace(/url\("data:[^"]*"\)/g, '')))
      err(`${t.id}: G9 css 引用外部 url()（只允许 "data:" 内联）`);
    const selRe = /(^|\})([^{}@]+)\{/g;
    let sm;
    while ((sm = selRe.exec(stripped))) {
      for (let sel of sm[2].split(',')) {
        sel = sel.trim();
        if (sel === ':root') continue;
        if (!/^\.mt-[\w-]+/.test(sel))
          err(`${t.id}: G9 css 选择器越界：「${sel}」（白名单：:root / .mt-* 及其伪元素后代）`);
        const cls = /^\.mt-[\w-]+/.exec(sel);
        if (cls) {
          if (seenMotifClasses[cls[0]] && seenMotifClasses[cls[0]] !== t.id)
            err(`${t.id}: 母题类名 ${cls[0]} 与 ${seenMotifClasses[cls[0]]} 重名（.mt-* 全库唯一）`);
          seenMotifClasses[cls[0]] = t.id;
        }
      }
    }
  }

  /* bake_brief（D1 风格圣经）：试点必填、其余存在即校验 */
  if (BAKE_BRIEF_REQUIRED.includes(t.id) || t.css.bake_brief !== undefined)
    checkBakeBrief(t);

  /* focus 组全部显式给出（G1/G2 为必填组，上面已验；此处验可选组的显式性） */
  for (const f of focus) {
    if (f === 'G1' || f === 'G2') continue;
    if (!t.groups[f] && !t.css[f]) { err(`${t.id}: focus 声明了 ${f} 但该字段组未显式给出`); continue; }
    if (f === 'G3') {
      const g3 = parseTokens(t.css.G3);
      for (const k of TEXTURE_TOKENS)
        if (!g3[k]) err(`${t.id}: G3 为 focus，缺少 token ${k}`);
      if (g3['--texture-type'] === 'flat')
        err(`${t.id}: G3 为 focus，--texture-type 不得为缺省值 flat`);
    }
    if (f === 'G4') {
      for (const k of ['圆角', 'hairline', '阴影'])
        if (!t.groups.G4 || !t.groups.G4[k]) err(`${t.id}: G4 为 focus，缺少字段「${k}」`);
    }
    if (f === 'G9') {
      if (!t.css.G9) err(`${t.id}: G9 为 focus，缺少母题 css 块`);
      if (!t.groups.G9 || !t.groups.G9['词汇']) err(`${t.id}: G9 为 focus，缺少字段「词汇」`);
    }
  }

  /* Variants 配色变体（两级架构：基底+变体 ≥3 套配色） */
  if (t.variants.length < 2)
    err(`${t.id}: 配色变体不足——基底+变体须 ≥3 套配色，实为 1+${t.variants.length}`);
  const vnames = new Set();
  for (const v of t.variants) {
    const vid = `${t.id} 变体「${v.name}」`;
    if (vnames.has(v.name)) err(`${vid}: 变体名重复`);
    vnames.add(v.name);
    const vt = parseTokens(v.css);
    for (const k of COLOR_TOKENS) {
      if (!vt[k]) err(`${vid}: 缺少 token ${k}`);
      else if (!/^#[0-9a-fA-F]{6}$/.test(vt[k])) err(`${vid}: ${k} 色值非法：${vt[k]}`);
    }
    for (const k of Object.keys(vt))
      if (!COLOR_TOKENS.includes(k) && !TEXTURE_TOKENS.includes(k) && !isMultiExtra(k))
        err(`${vid}: 变体不得覆盖 ${k}（只许 G1 六色 + 可选 G3 三 token + 多色扩展 token；覆盖其他层它就是另一个主题）`);
    checkMultiPairs(vid, { ...parseTokens(t.css.G1), ...vt });
    if (TEXTURE_TOKENS.some(k => vt[k])) {
      /* G3 部分覆盖：与基底合并后重跑质感校验 */
      checkTexture(vid + '（G3 覆盖合并后）', { ...parseTokens(t.css.G3), ...Object.fromEntries(TEXTURE_TOKENS.filter(k => vt[k]).map(k => [k, vt[k]])) });
    }
  }
}

/* 无主题外 hex：剔除全部 ``` 代码块后，正文中不允许出现 hex 色值（逐文件检查） */
for (const [fileId, fileMd] of Object.entries(allMdByFile)) {
  const prose = fileMd.replace(/```[\s\S]*?```/g, '');
  const lines = prose.split('\n');
  lines.forEach((line, i) => {
    const m = /#[0-9a-fA-F]{6}\b/.exec(line);
    if (m) err(`主题外 hex：${fileId} 第 ${i + 1} 行出现 ${m[0]}（色值只允许出现在 css 代码块内）`);
  });
}

/* focus 组合 + 核心色两两可区分 */
{
  const byFocus = {};
  const seenTriplet = {};
  for (const t of themes) {
    const focus = ((t.g0.focus || '').match(/G[0-9]/g) || []).slice().sort();
    const key = focus.join('+');
    const accent = (parseTokens(t.css.G1)['--accent'] || '').toLowerCase();
    (byFocus[key] = byFocus[key] || []).push({ id: t.id, accent });
    const triplet = COLOR_TOKENS.map(k => (parseTokens(t.css.G1)[k] || '').toLowerCase()).join('|');
    if (!triplet.split('|').some(v => !v) && seenTriplet[triplet])
      err(`${t.id}: 核心色三元组与 ${seenTriplet[triplet]} 完全相同，不可区分`);
    seenTriplet[triplet] = t.id;
  }
  for (const key of Object.keys(byFocus)) {
    const list = byFocus[key];
    const seen = {};
    for (const x of list) {
      if (seen[x.accent])
        err(`${x.id}: 与 ${seen[x.accent]} focus 组合相同（${key}）且 accent 撞车（${x.accent}），不可区分`);
      seen[x.accent] = x.id;
    }
  }
}

/* 七层分化门槛：任意两主题至少 3 层实质分化 */
{
  const byId = Object.fromEntries(themes.map(t => [t.id, t]));
  for (let i = 0; i < themes.length; i++) {
    for (let j = i + 1; j < themes.length; j++) {
      const a = themes[i], b = themes[j];
      const same = LAYERS.filter(L => layerSig(a, L) === layerSig(b, L));
      if (same.length > LAYERS.length - 3)
        err(`${a.id} 与 ${b.id} 分化不足：L1–L7 中 ${same.join('/')} 层相同（≥3 层实质分化为入库门槛；确属同一世界请合并为变体）`);
    }
  }
  /* 分化声明逐层核验为真 */
  for (const d of declarations) {
    const t = byId[d.id], n = byId[d.neighbor];
    if (!n) { err(`${d.id}: 分化声明指名的最近邻 ${d.neighbor} 不存在`); continue; }
    for (const L of d.layers)
      if (layerSig(t, L) === layerSig(n, L))
        err(`${d.id}: 分化声明称与 ${d.neighbor} 分化于 ${L}，但该层签名相同（声明必须为真）`);
  }
}

if (errors.length) {
  console.error('[sync-themes] Schema 校验失败（' + errors.length + ' 项）：');
  for (const e of errors) console.error('  - ' + e);
  process.exit(1);
}

/* ---------- 字段推导 ---------- */
function fontKind(stack) {
  if (/monospace\s*$/.test(stack)) return 'mono';
  if (/sans-serif\s*$/.test(stack)) return 'sans';
  if (/serif\s*$/.test(stack)) return 'serif';
  return null;
}

function visualOf(tokens) {
  return { paper: tokens['--paper'], ink: tokens['--ink'], accent: tokens['--accent'] };
}

function buildOption(t) {
  const label = t.heading.replace(/（默认）\s*$/, '').replace(/（[^）]*）\s*$/, '');
  const focus = (t.g0.focus.match(/G[0-9]/g) || []);
  const primary = GROUP_PRIORITY.find(g => focus.includes(g));
  const tokens = {};
  for (const g of Object.keys(t.css)) {
    if (g === 'G9' || g === 'bake_brief') continue;  // G9 是规则块走 theme_css；bake_brief 是生图简报，不进面板 token
    Object.assign(tokens, parseTokens(t.css[g]));
  }
  const fd = fontKind(tokens['--font-display']);
  const fb = fontKind(tokens['--font-body']);
  if (!fd || !fb) fail(`${t.id}: 字体类型推断失败（display=${fd} body=${fb}）`);

  /* demo 图片列表（目录内的 demo-*.png 文件名，按字母序） */
  let demos = [];
  try {
    const demoDir = join(THEMES_DIR, t.catDir, t.tidDir);
    demos = readdirSync(demoDir)
      .filter(f => /^demo-.*\.png$/.test(f))
      .sort();
  } catch { /* 无 demo 也合法（不阻断） */ }

  return {
    id: t.id,
    label,
    series: t.id[0].toUpperCase(),
    vibe: t.g0['气质'],
    description: t.g0['适用'] + '；' + t.g0['气质'],
    focus,
    focus_label: focus.map(g => GROUP_META[g].short).join(' + '),
    group: GROUP_META[primary].key,
    group_label: GROUP_META[primary].short + '主导',
    visual: { ...visualOf(tokens), font_display: fd, font_body: fb },
    tokens,
    theme_css: t.css.G9 ? t.css.G9.trim() : '',
    demos,
    variants: t.variants.map((v, i) => {
      const vt = parseTokens(v.css);
      return {
        id: t.id + '-v' + (i + 1),
        label: v.name,
        vibe: v.fields['气质'] || '',
        accent_note: v.fields['accent 预算'] || '',
        tokens: vt,
        visual: visualOf(vt)
      };
    })
  };
}

const options = themes.map(buildOption);

/* ---------- 动效组选项（五层启用矩阵，语义源 motion.md v3 §5） ----------
 * 本脚本只是写入载体：改选项必须先改 references/motion.md §5，再同步此处。 */
const MOTION_OPTIONS = [
  { id: 'restrained', label: '克制',
    description: '仅 L1 入场编排：默认阶梯 reveal + 页面节奏配方，无文字特效、无背景氛围、无交互层' },
  { id: 'standard', label: '标准',
    description: 'L1–L4 每层至多一个代表：入场编排 + 一个文字动效（如 chars/mask-lines）+ 一个数据动效（如 count-up/draw-line）+ 一个环境氛围（默认）' },
  { id: 'lush', label: '华丽',
    description: 'L1–L5 五层全开：锚点级文字/数据动效 + 环境光效 + 指针/滚动交互层；注意力预算不放宽（每页主动效仍 ≤1），相邻页锚点 recipe 不重复' }
];

/* ---------- 幂等写回 editor.html ---------- */
function writeMarkedBlock(src, begin, end, options, tag) {
  const bi = src.indexOf(begin);
  const ei = src.indexOf(end);
  if (bi < 0 || ei < 0 || ei < bi) fail(`editor.html 标记区间 ${tag} 缺失或顺序错误`);
  if (src.indexOf(begin, bi + begin.length) >= 0 || src.indexOf(end, ei + end.length) >= 0)
    fail(`editor.html 标记区间 ${tag} 不唯一`);
  const json = JSON.stringify(options, null, 2);
  const block = json.split('\n').map((l, i) => (i === 0 ? 'options: ' + l : '        ' + l)).join('\n');
  return src.slice(0, bi + begin.length) + '\n      ' + block + '\n      ' + src.slice(ei);
}

const BEGIN = '/*__THEMES_JSON_BEGIN__*/';
const END = '/*__THEMES_JSON_END__*/';
const MBEGIN = '/*__MOTION_JSON_BEGIN__*/';
const MEND = '/*__MOTION_JSON_END__*/';

let src = readFileSync(EDITOR, 'utf8');
let next = writeMarkedBlock(src, BEGIN, END, options, 'THEMES_JSON');
next = writeMarkedBlock(next, MBEGIN, MEND, MOTION_OPTIONS, 'MOTION_JSON');

if (next === src) {
  console.log('[sync-themes] editor.html 已是最新（幂等，无改动）');
} else {
  writeFileSync(EDITOR, next);
  console.log(`[sync-themes] 已更新 editor.html：${options.length} 套主题卡片数据（${options.map(o => o.id).join(', ')}）+ ${MOTION_OPTIONS.length} 个动效档选项`);
}
