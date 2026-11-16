/* phase6-batch1 / build.js
 * 同一份「山禾集 1.1」内容对象 × 4 套 G10 构图程序 × 45 页 sampler（含 F1 双变体 full-b）。
 *
 * 纪律：
 *  - 唯一内容对象 D；渲染函数只消费、不改写文字。
 *  - 字号只用骨架 v7.6 的 .t-* 角色类；主题令牌/G9 母题 CSS 从各自 theme.md 实时提取。
 *  - 页面级构图骨架（composition skeleton）：统一边距 M=120、沟槽 G=40，卡片吸附网格。
 *    E6=模块网格+Z动线 · G2=非对称两栏 · E7=对角线纵深 · F1=对角深度栈(+中心聚焦变体)。
 *  - 静态渲染，无入场动效。
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const DIR = path.join(ROOT, 'docs/progress/phase6-batch1');
const THEMES = {
  e6: 'color/e6/theme.md', g2: 'color/g2/theme.md',
  e7: 'texture/e7/theme.md', f1: 'light/f1/theme.md'
};
const LABEL = { e6: 'E6 孟菲斯', g2: 'G2 腮红荧光笔', e7: 'E7 浮世绘', f1: 'F1 浮光玻璃' };
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/* ---- 页面级构图骨架：统一模数 ---- */
const M = 120;   // 页边距
const G = 40;    // 沟槽
const CW = 1680; // 内容宽 = 1920 - 2*M
// 网格锚点：2 列 {120, 980}×820 · 3 列 {120, 680, 1240}×520 · 4 列 {120, 550, 980, 1410}×390

/* ---------------- 唯一内容对象 D ---------------- */
const D = {
  kicker: '1.1 · 整体特色及优势',
  title: '一杯好茶  山野作答',
  subtitle: '山禾集 · 经营情况汇报 · 2026',
  p1: '山禾集深耕新式茶饮行业，同时通过全资子公司山禾供应链管理有限公司协同布局上游茶园直采业务。通过多年不懈努力，山禾集秉持“当季鲜茶，日常相伴”的经营理念，建立起从茶园到门店的全链路品控流程，持续为消费者创造价值，赢得了广大茶饮爱好者的喜爱。',
  p2: '近年来山禾集门店网络稳步扩张，行业排名持续提升。2019年，山禾集全国门店总数突破八千家，跻身行业头部梯队。截至2026年6月30日，山禾集全国门店总数8,637家（含直营门店1,653家，子公司山禾供应链合作门店432家），其中标准门店8,428家，位于行业前列；城市旗舰店总数361家。成立以来累计为超过6.8亿会员用户售出茶饮2.8亿杯。',
  kpis: [
    { num: '8,637家', cap: '山禾集（含直营和子公司山禾供应链）全国门店总数', tag: '行业前列' },
    { num: '2.8亿杯', cap: '成立以来累计为超过6.8亿会员用户售出茶饮' },
    { num: '361家', cap: '城市旗舰店总数' }
  ],
  creed: [
    '经营理念：当季鲜茶，日常相伴。',
    '使命：为大众提供新鲜、健康、平价的日常茶饮。',
    '愿景：成为持续领先的新式茶饮品牌。'
  ],
  toc: [
    '一 · 整体特色及优势', '二 · 全链路品控流程', '三 · 门店网络与渠道',
    '四 · 会员与产品数据', '五 · 经营理念与展望'
  ],
  claim: '从茶园到门店',
  claimNote: '一杯好茶的答案，写在每一片叶子的来路上。',
  closing: '山野作答 · 未完待续',
  closingNote: '以当季鲜茶，回应日常相伴。',
  note: '* 注：山禾集为虚构演示品牌，文中数据均为虚构，仅用于主题样式对比展示。',
  footL: '山禾集 · 经营情况汇报',
  longText: '山禾集深耕新式茶饮行业，同时通过全资子公司山禾供应链管理有限公司协同布局上游茶园直采业务。通过多年不懈努力，山禾集秉持“当季鲜茶，日常相伴”的经营理念，建立起从茶园到门店的全链路品控流程，持续为消费者创造价值，赢得了广大茶饮爱好者的喜爱。近年来山禾集门店网络稳步扩张，行业排名持续提升。二〇一九年，山禾集全国门店总数突破八千家，跻身行业头部梯队。截至二〇二六年六月三十日，山禾集全国门店总数八千六百三十七家，其中含直营门店一千六百五十三家、子公司山禾供应链合作门店四百三十二家，标准门店八千四百二十八家，位于行业前列；城市旗舰店总数三百六十一家。成立以来累计为超过六点八亿会员用户售出茶饮二点八亿杯。经营理念是当季鲜茶、日常相伴；使命是为大众提供新鲜、健康、平价的日常茶饮；愿景是成为持续领先的新式茶饮品牌。',
  bigNums: ['8,637家', '2.8亿杯', '361家', '−12%', '6.8亿'],
  series8: [
    { n: '华东', v: 96 }, { n: '华南', v: 82 }, { n: '华北', v: 71 }, { n: '西南', v: 63 },
    { n: '华中', v: 55 }, { n: '东北', v: 42 }, { n: '西北', v: 31 }, { n: '其他', v: 18 }
  ],
  longTitle: '从茶园直采到门店现制的全链路品控体系如何持续支撑山禾集的新式茶饮增长叙事',
  singleChar: '茶',
  empty: '—'
};
D.longChunks = [D.longText.slice(0, 105), D.longText.slice(105, 210), D.longText.slice(210, 315), D.longText.slice(315)];
D.rows = [D.p1.slice(0, 58), D.p1.slice(58), D.p2.slice(0, 64), D.p2.slice(64, 140)];
const ttl = esc(D.title).replace(/ /g, '&nbsp;');

/* ---------------- 从 theme.md 提取 token 与母题 CSS ---------------- */
function cssBlocks(txt) { return [...txt.matchAll(/```css\r?\n([\s\S]*?)```/g)].map(m => m[1]); }
function sectionAfter(txt, name) {
  const i = txt.indexOf('**' + name);
  if (i < 0) throw new Error('缺段 ' + name);
  return txt.slice(i);
}
const TOK = {}, MOTIF = {};
for (const [id, rel] of Object.entries(THEMES)) {
  const t = fs.readFileSync(path.join(ROOT, 'skills/SlideForge/references/themes', rel), 'utf8').replace(/\r\n/g, '\n');
  const g1 = cssBlocks(sectionAfter(t, 'G1 color'))[0];
  const g2 = cssBlocks(sectionAfter(t, 'G2 typography'))[0];
  const g9 = cssBlocks(sectionAfter(t, 'G9 motif')).find(b => b.includes('.mt-'));
  if (!g1 || !g2 || !g9) throw new Error(id + ': token/CSS 提取失败');
  const root = (g9.match(/:root\{([^}]*)\}/) || [, ''])[1];
  TOK[id] = [g1.replace(/\s*\n\s*/g, ' '), g2.replace(/\s*\n\s*/g, ' '), root].filter(Boolean).join(';');
  MOTIF[id] = g9;
}

/* ---------------- 骨架 v7.6 角色类（逐字复用） ---------------- */
const ROLE_CSS = `
:root{--t-display:96px;--t-heading:64px;--t-subhead:40px;--t-body:28px;
  --t-caption:18px;--t-meta:15px;--t-vertical:96px}
.t-display{font-size:max(var(--t-display),64px);line-height:1.15}
.t-heading{font-size:max(var(--t-heading),32px);line-height:1.25}
.t-subhead{font-size:max(var(--t-subhead),24px);line-height:1.3}
.t-body{font-size:max(var(--t-body),18px);line-height:1.6}
.t-caption{font-size:max(var(--t-caption),16px);line-height:1.5}
.t-meta{font-size:max(var(--t-meta),14px);line-height:1.4}
.t-vertical{font-size:max(var(--t-vertical),64px);line-height:1.12;writing-mode:vertical-rl}
`;

/* ---------------- 小工具 ---------------- */
const pos = (x, y, w, h) => `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px`;
const text = (cls, s, style) => `<div class="${cls}" style="${style}">${esc(s)}</div>`;
const bars = (arr, x, y, w, color) => arr.map((s, i) =>
  `<div style="${pos(x, y + i * 22, w, 12)};background:color-mix(in srgb,var(--accent) ${Math.max(18, s.v)}%,var(--paper));border:1px solid color-mix(in srgb,var(--ink) 20%,transparent)"></div>` +
  text('t-meta', s.n, `${pos(x + w + 12, y + i * 22 - 3, 120, 20)}`)
).join('');
const foot = (id, role, n) => `<div class="mastfoot"><span>${esc(D.footL)}</span><span>${LABEL[id]} · ${role}</span><span>${n} / 45</span></div>`;
const note = (y = 1000) => text('t-meta', D.note, `${pos(M, y, 1500, 24)}`);
const kicker = (x, y, s = D.kicker) => text('t-meta', s, `${pos(x, y, 600, 24)};letter-spacing:.1em`);

/* =================== E6 模块网格 + Z 动线 ===================
 * 骨架：所有卡片吸附统一网格（边距 120 / 沟槽 40），Z 型动线 = 标题(左上) → 右上装饰
 *       → 正文两栏(中) → 数据三块(下) → 页脚。孟菲斯的「活泼」来自背景之字/彩纸屑
 *       + 描边色 + 唯一焦点，不再来自「卡片乱摆」。 */
function E6(p) {
  const h = [];
  const R = p.role, V = p.variant;
  const conf = [[1680, 120], [1760, 420], [120, 980], [1840, 900]].map(([x, y], i) =>
    `<i class="mt-mem-dot ${i % 2 ? 'mt-mem-c2' : ''}" style="left:${x}px;top:${y}px"></i>`).join('');
  h.push(`<div class="bg-layer"><div class="mt-mem-path"></div><div class="mt-mem-confetti">${conf}</div></div>`);
  h.push(kicker(M, 96));
  const block = (x, y, w, hh, inner, o = {}) => {
    const { focus = false, accent = false, idx = 0 } = o;
    const bg = focus ? 'var(--accent)' : (accent ? 'var(--palette-3)' : 'var(--paper)');
    const color = focus ? 'var(--accent-on)' : 'var(--ink)';
    const border = `2px solid ${(focus || accent) ? 'var(--ink)' : `var(--palette-${(idx % 3) + 2})`}`;
    return `<div class="mt-mem-block ${focus ? 'mt-mem-block--focus' : ''}" data-block="${idx}" style="${pos(x, y, w, hh)};background:${bg};color:${color};border:${border}">${inner}</div>`;
  };
  const step = i => `<span class="mt-mem-step"></span>`;
  const titleBlock = (x, y, w, hh, cls = 't-display', s = D.title) => block(x, y, w, hh,
    `<div class="${cls}" style="font-weight:800;white-space:pre-line">${esc(s.length > 18 ? s.slice(0, 16) + '\n' + s.slice(16, 32) + (s.length > 32 ? '\n' + s.slice(32) : '') : s)}</div>` +
    text('t-meta', D.subtitle, 'margin-top:26px;font-family:var(--font-mono)'), { idx: 0 });

  if (R === 'full') {
    // Z 动线：标题(左上 2/3) → 右上装饰 → 正文两栏 → KPI 三块等宽 → 页脚
    h.push(block(M, 140, 1080, 220, `<div class="t-display" style="font-weight:800;white-space:nowrap;line-height:1.05">${ttl}</div>`, { idx: 0 }));
    h.push(block(1240, 140, 560, 220, text('t-meta', '山禾集 · 主题 01', 'font-family:var(--font-mono);letter-spacing:.12em'), { accent: true, idx: 1 }));
    h.push(block(M, 400, 820, 260, text('t-body', D.p1), { idx: 1 }));
    h.push(block(980, 400, 820, 260, text('t-body', D.p2), { idx: 2 }));
    D.kpis.forEach((k, i) => h.push(block(120 + i * 560, 700, 520, 200,
      `<div class="t-heading" style="font-weight:800;line-height:1.1">${esc(k.num)}${k.tag ? `<span class="t-meta" style="color:var(--accent);margin-left:10px;font-weight:600">${esc(k.tag)}</span>` : ''}</div>` +
      text('t-meta', k.cap, 'margin-top:10px;line-height:1.35'), { focus: i === 0, idx: i })));
    h.push(`<div style="${pos(M, 940, CW, 26)}">${D.creed.map(c => text('t-caption', c, 'display:inline-block;margin-right:34px')).join('')}</div>`);
    h.push(note(980));
    h.push(foot('e6', 'full', p.n));
    return h.join('\n');
  }

  if (R === 'cover' || V === 'd7') {
    h.push(titleBlock(M, 300, 1240, 440, V === 'd7' ? 't-heading' : 't-display', V === 'd7' ? D.longTitle : D.title));
    h.push(block(1400, 300, 400, 440, text('t-meta', '之字路径 · 第 01 版', 'font-family:var(--font-mono);letter-spacing:.12em;writing-mode:vertical-rl'), { accent: true, idx: 1 }));
  } else if (V === 'd2') {
    D.longChunks.forEach((s, i) => h.push(block(120 + (i % 2) * 860, 200 + Math.floor(i / 2) * 340, 820, 300, text('t-body', s), { idx: i })));
  } else if (V === 'd4') {
    h.push(block(M, 160, 680, 120, text('t-heading', '八系列 · 门店分布', 'font-weight:800'), { idx: 0 }));
    h.push(block(M, 320, 1240, 640, bars(D.series8, 40, 40, 1000), { idx: 1 }));
    h.push(block(1400, 320, 400, 640, text('t-meta', '门店结构', 'writing-mode:vertical-rl'), { accent: true, idx: 2 }));
  } else if (R === 'toc') {
    D.toc.slice(0, 3).forEach((s, i) => h.push(block(120 + i * 560, 200, 520, 240,
      `<div class="t-subhead" style="font-weight:800">${step(i)}${String(i + 1).padStart(2, '0')}</div>` + text('t-caption', s, 'margin-top:10px'), { idx: i })));
    D.toc.slice(3).forEach((s, i) => h.push(block(120 + i * 860, 480, 820, 240,
      `<div class="t-subhead" style="font-weight:800">${step(i + 3)}${String(i + 4).padStart(2, '0')}</div>` + text('t-caption', s, 'margin-top:10px'), { idx: i + 3 })));
  } else if (R === 'claim' || R === 'closing') {
    const main = R === 'claim' ? D.claim : D.closing;
    const sub = R === 'claim' ? D.claimNote : D.closingNote;
    h.push(block(M, 260, 1240, 400, text('t-display', main, 'font-weight:800') + text('t-meta', sub, 'margin-top:24px'), { idx: 0 }));
    h.push(block(1400, 260, 400, 400, text('t-meta', R, 'font-family:var(--font-mono);letter-spacing:.12em;writing-mode:vertical-rl'), { accent: true, idx: 1 }));
    h.push(block(M, 700, CW, 180, text('t-body', D.creed[0], 'font-weight:600'), { idx: 2 }));
  } else if (R === 'analysis') {
    [D.rows[0], D.rows[1], D.p2.slice(0, 100)].forEach((s, i) =>
      h.push(block(120 + i * 560, 220, 520, 380,
        text('t-meta', '版 ' + String(i + 1).padStart(2, '0'), 'font-family:var(--font-mono);margin-bottom:12px') + text('t-body', s), { idx: i })));
  } else if (R === 'data' || V === 'd3') {
    const nums = V === 'd3' ? D.bigNums.slice(0, 3) : D.kpis.map(k => k.num);
    nums.forEach((n, i) => h.push(block(120 + i * 560, 260, 520, 360,
      `<div class="${i === 0 ? 't-display' : 't-heading'}" style="font-weight:800;line-height:1.1">${esc(n)}</div>` +
      text('t-meta', (D.kpis[i] && D.kpis[i].cap) || '同比变化', 'margin-top:14px;line-height:1.4'), { focus: i === 0, idx: i })));
    h.push(text('t-meta', '结论：三项数字等宽并置，首项为唯一焦点', `${pos(M, 660, 1200, 24)}`));
  }
  h.push(note(1010));
  h.push(foot('e6', R + (V ? '/' + V : ''), p.n));
  return h.join('\n');
}

/* =================== G2 非对称两栏（正文 : 批注 ≈ 58 : 4 : 38） ===================
 * 骨架：左正文 + 右批注索引脊，栏宽/沟槽/边距统一。行号 120 / 正文 180 / 引线 1180 / 索引 1240。 */
function G2(p) {
  const h = [];
  const R = p.role, V = p.variant;
  const X_LINE = 120, X_TEXT = 180, X_LEAD = 1180, X_IDX = 1240, W_TEXT = 980, W_IDX = 560;
  const lead = (y, i) => `<div class="mt-hl-lead" data-lead="${i}" style="${pos(X_LEAD, y + 20, 40, 5)};--hl-c:var(--hl-${i % 2 + 1})"></div>`;
  const lineNo = (y, i) => `<div class="mt-hl-lineno" style="${pos(X_LINE, y, 48, 24)}">${String(i + 1).padStart(2, '0')}</div>`;
  const idx = (y, s, i) => `<div class="mt-hl-index" style="${pos(X_IDX, y - 8, W_IDX, 74)};--hl-c:var(--hl-${i % 2 + 1})">` +
    text('t-caption', s, '') + `</div>`;
  const row = (y, s, tag, i) => lineNo(y, i) + text('t-body', s, `${pos(X_TEXT, y, W_TEXT, 80)}`) + lead(y, i) + idx(y, tag, i);
  h.push(`<div class="bg-layer" style="background:repeating-linear-gradient(0deg,transparent 0 87px,color-mix(in srgb,var(--ink) 8%,transparent) 87px 88px)"></div>`);
  h.push(kicker(M, 96));
  h.push(text('t-meta', '笔记正文层', `${pos(X_TEXT, 150, 400, 24)};font-family:var(--font-mono);letter-spacing:.14em`));
  h.push(text('t-meta', '标注索引脊', `${pos(X_IDX, 150, 400, 24)};font-family:var(--font-mono);letter-spacing:.14em`));

  if (R === 'full') {
    h.push(`<div class="t-display" style="${pos(M, 180, 1200, 140)};font-weight:700;white-space:nowrap;line-height:1.05"><span class="mt-hl-mark" style="--hl-c:var(--accent)">${ttl}</span></div>`);
    const full = D.p1 + D.p2;
    const rows = [];
    for (let i = 0; i < full.length; i += 40) rows.push(full.slice(i, i + 40));
    rows.forEach((s, i) => {
      const y = 320 + i * 52;
      h.push(lineNo(y, i) + text('t-body', s, `${pos(X_TEXT, y, W_TEXT, 44)};line-height:1.4`) + lead(y, i));
    });
    D.kpis.forEach((k, i) => {
      const y = 320 + i * 100;
      h.push(text('t-heading', k.num, `${pos(X_IDX, y, W_IDX, 80)};font-weight:700`) +
        text('t-meta', k.cap, `${pos(X_IDX, y + 78, W_IDX, 30)};line-height:1.3`));
    });
    D.creed.forEach((c, i) => {
      const y = 640 + i * 56;
      h.push(text('t-caption', c, `${pos(X_IDX, y, W_IDX, 40)};line-height:1.35`));
    });
    h.push(note(1015));
    h.push(foot('g2', 'full', p.n));
    return h.join('\n');
  }

  if (R === 'cover' || V === 'd7') {
    const ttl2 = V === 'd7' ? D.longTitle : D.title;
    h.push(`<div class="t-${V === 'd7' ? 'heading' : 'display'}" style="${pos(M, 300, 1500, 320)};font-weight:700;white-space:pre-line"><span class="mt-hl-mark">${esc(ttl2.length > 18 ? ttl2.slice(0, 16) + '\n' + ttl2.slice(16, 32) + (ttl2.length > 32 ? '\n' + ttl2.slice(32) : '') : ttl2)}</span></div>`);
    h.push(`<div class="mt-hl-tape" style="${pos(1500, 260, 88, 24)}"></div>`);
    h.push(idx(700, V === 'd7' ? '极长标题 · 一次标注' : '唯一焦点 · 一杯好茶', 0));
    h.push(text('t-meta', D.subtitle, `${pos(M, 720, 800, 24)}`));
  } else if (V === 'd2') {
    const chunks = [D.longText.slice(0, 95), D.longText.slice(95, 190), D.longText.slice(190, 285), D.longText.slice(285, 380), D.longText.slice(380)];
    chunks.forEach((s, i) => {
      const y = 220 + i * 140;
      h.push(lineNo(y, i) + text('t-body', s, `${pos(X_TEXT, y, W_TEXT, 130)}`) + lead(y, i) + idx(y, '长段落 · 第 ' + (i + 1) + ' 段', i));
    });
  } else if (V === 'd4') {
    h.push(text('t-heading', '八系列 · 门店分布', `${pos(X_TEXT, 210, 900, 70)};font-weight:700`));
    D.series8.forEach((s, i) => {
      const y = 300 + i * 74;
      h.push(lineNo(y, i) + text('t-caption', s.n + ' · ' + s.v + '%', `${pos(X_TEXT, y, W_TEXT, 60)}`) + lead(y, i) + idx(y, '系列 ' + (i + 1), i));
    });
  } else if (R === 'toc') {
    D.toc.forEach((s, i) => h.push(row(240 + i * 130, s, '章节 ' + String(i + 1).padStart(2, '0'), i)));
  } else if (R === 'claim' || R === 'closing') {
    const main = R === 'claim' ? D.claim : D.closing;
    h.push(text('t-display', main, `${pos(X_TEXT, 240, 1020, 150)};font-weight:700`));
    h.push(row(440, R === 'claim' ? D.claimNote : D.closingNote, '主张 · 关键词', 0));
    h.push(row(590, D.creed[0], '经营理念', 1));
    h.push(row(740, D.creed[2], '愿景', 2));
  } else if (R === 'analysis') {
    D.rows.forEach((s, i) => h.push(row(240 + i * 165, s, ['上游直采', '全链路品控', '门店网络', '会员规模'][i], i)));
  } else if (R === 'data' || V === 'd3') {
    const nums = V === 'd3' ? D.bigNums.slice(0, 3) : D.kpis.map(k => k.num);
    nums.forEach((n, i) => {
      const y = 250 + i * 190;
      h.push(lineNo(y, i) + text('t-caption', (D.kpis[i] && D.kpis[i].cap) || '同比变化 · 负数', `${pos(X_TEXT, y, 900, 80)};line-height:1.5`) +
        lead(y, i) + idx(y, '页边批注 ' + n, i) +
        `<span class="mt-hl-mark" style="${pos(1080, y, 110, 40)};font-family:var(--font-mono)">${esc(n)}</span>`);
    });
  }
  h.push(note(1010));
  h.push(foot('g2', R + (V ? '/' + V : ''), p.n));
  return h.join('\n');
}

/* =================== E7 对角线纵深（前景大物 → 远景） ===================
 * 骨架：弃「三条全宽横带」，改对角线纵深——远景(左上,轻) → 中景(中) → 前景(右下,重)，
 *       上 1/3 留白做「天空」，印章落右上对角平衡。套印错位 = 层左缘轻微错开。 */
function E7(p) {
  const h = [];
  const R = p.role, V = p.variant;
  const band = (y, cls) => `<div class="mt-uki-band ${cls}" style="${pos(0, y, 1920, 12)}"></div>`;
  const plate = (x, y, w, hh, inner, ed, strong) =>
    `<div class="mt-uki-plate ${strong ? 'mt-uki-plate--first' : ''}" data-plate="1" style="${pos(x, y, w, hh)}">${inner}</div>` +
    `<div class="mt-uki-edition t-meta" style="${pos(x + w - 150, y + hh + 6, 150, 24)}">版次 ${esc(ed)}</div>`;
  const seal = (x, y, s = 96) => `<span class="mt-uki-seal" style="${pos(x, y, s, s)}">茶</span>`;
  h.push(`<div class="bg-layer"></div>`);
  h.push(kicker(M, 96));

  if (R === 'full') {
    // 远景(左上,轻) → 中景(中) → 前景(右下,重)；印章右上
    h.push(plate(M, 130, 760, 190, text('t-meta', D.subtitle) + text('t-caption', '远景 · 落款', 'margin-top:14px'), '远', false));
    h.push(plate(400, 320, 1120, 290, text('t-body', D.p1) + text('t-body', D.p2, 'margin-top:8px'), '中', false));
    h.push(plate(720, 620, 1080, 340,
      `<div class="t-display" style="font-weight:700;white-space:nowrap;line-height:1.05">${ttl}</div>` +
      `<div style="margin-top:16px">${D.kpis.map((k, i) => `<span style="display:inline-block;margin-right:28px"><span class="t-heading" style="font-weight:700">${esc(k.num)}</span><div class="t-meta" style="margin-top:6px;max-width:300px">${esc(k.cap)}</div></span>`).join('')}</div>` +
      `<div style="margin-top:14px">${D.creed.map(c => text('t-caption', c, 'display:inline-block;margin-right:24px')).join('')}</div>`,
      '近', true));
    h.push(seal(1740, 96));
    h.push(note(1010));
    h.push(foot('e7', 'full', p.n));
    return h.join('\n');
  }

  if (R === 'cover' || V === 'd7') {
    const ttl2 = V === 'd7' ? D.longTitle : D.title;
    h.push(plate(M, 130, 700, 180, text('t-meta', D.subtitle) + text('t-caption', '远景 · 落款', 'margin-top:12px'), '远', false));
    h.push(plate(480, 460, 1320, 500,
      `<div class="t-${V === 'd7' ? 'heading' : 'display'}" style="font-weight:700;white-space:pre-line">${esc(ttl2.length > 18 ? ttl2.slice(0,16) + '\n' + ttl2.slice(16) : ttl2)}</div>` +
      text('t-meta', D.subtitle, 'margin-top:20px;font-family:var(--font-mono)'), '近', true));
    h.push(seal(1740, 96));
    h.push(band(980, 'mt-uki-wave'));
  } else if (V === 'd2') {
    h.push(plate(M, 130, 720, 200, text('t-body', D.longChunks[0]), '远', false));
    h.push(plate(420, 380, 1160, 280, text('t-body', D.longChunks[1]) + text('t-body', D.longChunks[2], 'margin-top:6px'), '中', false));
    h.push(plate(760, 700, 1040, 280, text('t-body', D.longChunks[3]), '近', true));
  } else if (V === 'd4') {
    h.push(plate(M, 130, 700, 180, text('t-heading', '八系列 · 门店分布', 'font-weight:700'), '远', false));
    h.push(plate(420, 380, 1160, 560, bars(D.series8, 40, 20, 800), '中', false));
    h.push(plate(760, 700, 1040, 240, text('t-caption', D.creed[2], 'line-height:1.5'), '近', true));
  } else if (R === 'toc') {
    h.push(plate(M, 130, 760, 200, text('t-subhead', D.toc.slice(0, 2).join('　/　'), 'font-weight:600;line-height:1.4'), '远', false));
    h.push(plate(400, 340, 1120, 240, text('t-subhead', D.toc.slice(2, 4).join('　/　'), 'font-weight:600;line-height:1.4'), '中', false));
    h.push(plate(720, 600, 1080, 240, text('t-subhead', D.toc[4], 'font-weight:600'), '近', true));
  } else if (R === 'claim') {
    h.push(plate(M, 130, 720, 180, text('t-caption', '主张 · 关键词', 'margin-top:10px'), '远', false));
    h.push(plate(420, 380, 1200, 320, text('t-display', D.claim, 'font-weight:700') + text('t-body', D.claimNote, 'margin-top:16px'), '近', true));
  } else if (R === 'closing') {
    h.push(plate(M, 130, 720, 180, text('t-caption', '远景 · 落款', 'margin-top:10px'), '远', false));
    h.push(plate(480, 420, 1280, 360, text('t-display', D.closing, 'font-weight:700') + text('t-body', D.closingNote, 'margin-top:16px'), '近', true));
    h.push(seal(1740, 96));
  } else if (R === 'analysis') {
    h.push(plate(M, 130, 720, 200, text('t-body', D.p1.slice(0, 110)), '题', false));
    h.push(plate(400, 360, 1160, 280, text('t-body', D.p2.slice(0, 110)), '论', false));
    h.push(plate(760, 680, 1040, 260, text('t-caption', D.creed.join('　'), 'line-height:1.5'), '证', true));
  } else if (R === 'data' || V === 'd3') {
    const nums = V === 'd3' ? D.bigNums.slice(0, 3) : D.kpis.map(k => k.num);
    h.push(plate(M, 130, 720, 200, text('t-caption', (D.kpis[0] && D.kpis[0].cap) || '同比变化', 'line-height:1.5'), '远', false));
    h.push(plate(420, 380, 1160, 280, text('t-heading', nums[1] || '', 'font-weight:700') + text('t-caption', (D.kpis[1] && D.kpis[1].cap) || '', 'margin-top:10px;line-height:1.5'), '中', false));
    h.push(plate(760, 700, 1040, 260, text('t-heading', nums[0] || '', 'font-weight:700') + text('t-caption', (D.kpis[0] && D.kpis[0].cap) || '', 'margin-top:10px;line-height:1.5'), '近', true));
    h.push(seal(1740, 96));
  }
  h.push(note(1010));
  h.push(foot('e7', R + (V ? '/' + V : ''), p.n));
  return h.join('\n');
}

/* =================== F1 浮光玻璃 ===================
 * 骨架（A 对角深度栈）：远景(左上,透) → 中景 → 前景(右下,实)，重心回光学中心。
 * 变体 B（中心聚焦）：单块主玻璃居中，周围大留白 + 柔光斑。 */
function F1(p) {
  const h = [];
  const R = p.role, V = p.variant;
  // A 变体：三层沿左上→右下对角递减
  const layers = [
    { x: 120, y: 110, w: 880, h: 240, tx: 160, ty: 140, tw: 800, th: 170, d: 3, a: 56 },
    { x: 480, y: 370, w: 1040, h: 280, tx: 520, ty: 400, tw: 960, th: 210, d: 2, a: 72 },
    { x: 820, y: 670, w: 980, h: 320, tx: 860, ty: 700, tw: 900, th: 250, d: 1, a: 88 }
  ];
  const layer = (i, inner) => {
    const L = layers[i];
    return `<div class="mt-gls-depth" data-depth="${L.d}" style="${pos(L.x, L.y, L.w, L.h)};z-index:${4 - L.d};` +
      `background:linear-gradient(155deg,color-mix(in srgb,var(--paper) ${L.a}%,transparent),color-mix(in srgb,var(--paper) ${L.a - 22}%,transparent))">` +
      `<div style="${pos(L.tx - L.x, L.ty - L.y, L.tw, L.th)}">${inner}</div></div>`;
  };
  h.push(`<div class="bg-layer"><div class="mt-gls-blob" style="${pos(1180, 60, 620, 620)}"></div><div class="mt-gls-blob" style="${pos(80, 660, 560, 560)}"></div>` +
    `<div class="mt-gls-axis" data-axis="12" style="${pos(100, 800, 1700, 1)};transform:rotate(-12deg)"></div></div>`);
  h.push(kicker(M, 96));

  if (R === 'full' && V === 'b') {
    // 变体 B：中心聚焦——单块主玻璃居中，正文/数据/理念全在其中，四周大留白
    h.push(`<div class="mt-gls-depth" data-depth="1" style="${pos(360, 150, 1200, 700)};z-index:3;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 90%,transparent),color-mix(in srgb,var(--paper) 70%,transparent))">` +
      `<div class="t-display" style="${pos(60, 40, 1080, 110)};font-weight:400;white-space:nowrap;line-height:1.05;color:var(--accent)">${ttl}</div>` +
      `<div style="${pos(60, 165, 1080, 80)}">${D.kpis.map((k, i) => `<span class="mt-gls-chip-n" style="display:inline-flex;margin-right:18px"><span class="t-heading" style="font-weight:500">${esc(k.num)}</span></span>`).join('')}</div>` +
      `<div style="${pos(60, 245, 1080, 70)}">${D.kpis.map((k, i) => text('t-meta', k.cap, `display:inline-block;width:${i === 2 ? 360 : 340}px;margin-right:18px;line-height:1.3`)).join('')}</div>` +
      `<div style="${pos(60, 325, 1080, 280)}">${text('t-body', D.p1) + text('t-body', D.p2, 'margin-top:12px')}</div>` +
      `<div style="${pos(60, 615, 1080, 30)}">${D.creed.map(c => text('t-meta', c, 'display:inline-block;margin-right:22px')).join('')}</div>` + `</div>`);
    h.push(note(900));
    h.push(foot('f1', 'full/b', p.n));
    return h.join('\n');
  }

  if (R === 'full') {
    // 变体 A：对角深度栈（左缘 120→360→720 对角，重心回光学中心）
    h.push(`<div class="mt-gls-depth" data-depth="1" style="${pos(720, 560, 1080, 360)};z-index:3;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 88%,transparent),color-mix(in srgb,var(--paper) 66%,transparent))">` +
      `<div class="t-display" style="${pos(40, 24, 1000, 110)};font-weight:400;white-space:nowrap;line-height:1.05;color:var(--accent)">${ttl}</div>` +
      `<div style="${pos(40, 150, 1000, 80)}">${D.kpis.map((k, i) => `<span class="mt-gls-chip-n" style="display:inline-flex;margin-right:16px"><span class="t-heading" style="font-weight:500">${esc(k.num)}</span></span>`).join('')}</div>` +
      `<div style="${pos(40, 245, 1000, 90)}">${D.kpis.map((k, i) => text('t-meta', k.cap, `display:inline-block;width:${i === 2 ? 320 : 310}px;margin-right:16px;line-height:1.3`)).join('')}</div>` + `</div>`);
    h.push(`<div class="mt-gls-depth" data-depth="2" style="${pos(360, 340, 1200, 220)};z-index:2;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 74%,transparent),color-mix(in srgb,var(--paper) 52%,transparent))">` +
      `<div style="${pos(40, 30, 1120, 160)}">${text('t-body', D.p1)}</div>` + `</div>`);
    h.push(`<div class="mt-gls-depth" data-depth="3" style="${pos(120, 120, 1120, 220)};z-index:1;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 60%,transparent),color-mix(in srgb,var(--paper) 38%,transparent))">` +
      `<div style="${pos(40, 16, 1040, 160)}">${text('t-body', D.p2)}</div>` +
      `<div style="${pos(40, 182, 1040, 30)}">${D.creed.map(c => text('t-meta', c, 'display:inline-block;margin-right:20px')).join('')}</div>` + `</div>`);
    h.push(note(1015));
    h.push(foot('f1', 'full', p.n));
    return h.join('\n');
  }

  if (R === 'cover' || V === 'd7') {
    const ttl2 = V === 'd7' ? D.longTitle : D.title;
    h.push(`<div class="mt-gls-depth" data-depth="1" style="${pos(120, 250, 1660, 560)};z-index:3;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 88%,transparent),color-mix(in srgb,var(--paper) 66%,transparent))">` +
      `<div class="t-${V === 'd7' ? 'heading' : 'display'}" style="${pos(80, 90, 1480, 320)};font-weight:400;white-space:pre-line">${esc(ttl2.length > 18 ? ttl2.slice(0, 16) + '\n' + ttl2.slice(16) : ttl2)}</div>` +
      text('t-meta', D.subtitle, `${pos(80, 440, 800, 24)}`) + `</div>`);
  } else if (V === 'd2') {
    h.push(layer(2, text('t-body', D.longChunks[0]) + text('t-body', D.longChunks[1], 'margin-top:12px')));
    h.push(layer(1, text('t-body', D.longChunks[2])));
    h.push(layer(0, text('t-meta', D.longChunks[3].slice(0, 40), 'line-height:1.5')));
  } else if (V === 'd4') {
    h.push(`<div class="mt-gls-depth" data-depth="1" style="${pos(240, 200, 1440, 620)};z-index:3;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 88%,transparent),color-mix(in srgb,var(--paper) 66%,transparent))">` +
      `<div style="${pos(70, 60, 1300, 90)}">${text('t-heading', '八系列 · 门店分布', 'font-weight:400')}</div>` +
      `<div style="${pos(70, 170, 900, 400)}">${bars(D.series8, 0, 0, 760)}</div>` +
      `<div style="${pos(1050, 180, 300, 380)}">${text('t-body', D.p1.slice(0, 70))}</div>` + `</div>`);
  } else if (R === 'toc') {
    h.push(layer(2, D.toc.slice(0, 2).map(s => text('t-body', s, 'margin-bottom:14px')).join('')));
    h.push(layer(1, D.toc.slice(2, 4).map(s => text('t-caption', s, 'margin-bottom:8px')).join('')));
    h.push(layer(0, text('t-caption', D.toc[4])));
  } else if (R === 'claim' || R === 'closing') {
    const main = R === 'claim' ? D.claim : D.closing;
    const sub = R === 'claim' ? D.claimNote : D.closingNote;
    h.push(`<div class="mt-gls-depth" data-depth="1" style="${pos(240, 250, 1440, 460)};z-index:3;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 88%,transparent),color-mix(in srgb,var(--paper) 66%,transparent))">` +
      `<div style="${pos(70, 90, 1300, 200)}">${text('t-display', main, 'font-weight:400;white-space:nowrap')}</div>` +
      `<div style="${pos(70, 300, 1300, 40)}">${text('t-body', sub)}</div>` +
      `<div style="${pos(70, 360, 1300, 30)}">${D.creed.map(c => text('t-meta', c, 'display:inline-block;margin-right:24px')).join('')}</div>` + `</div>`);
  } else if (R === 'analysis') {
    h.push(layer(2, text('t-body', D.p1.slice(0, 120)) + text('t-body', D.p1.slice(120, 200), 'margin-top:12px')));
    h.push(layer(1, text('t-body', D.p2.slice(0, 90))));
    h.push(layer(0, text('t-meta', D.kicker)));
  } else if (R === 'data' || V === 'd3') {
    const nums = V === 'd3' ? D.bigNums.slice(0, 3) : D.kpis.map(k => k.num);
    h.push(layer(2, text('t-subhead', D.footL, 'font-weight:500') +
      nums.map((n, i) => `<span class="mt-gls-chip-n" style="position:absolute;left:${i * 300}px;top:84px"><span class="t-subhead" style="font-weight:600">${esc(n)}</span></span>`).join('')));
    h.push(layer(1, text('t-caption', D.kpis[0].cap, 'line-height:1.5')));
    h.push(layer(0, text('t-meta', '结论数字 · 深度 3')));
  }
  h.push(note(1010));
  h.push(foot('f1', R + (V ? '/' + V : ''), p.n));
  return h.join('\n');
}

/* ---------------- 组装 45 页 ---------------- */
const RENDER = { e6: E6, g2: G2, e7: E7, f1: F1 };
const ROLES = ['cover', 'toc', 'claim', 'analysis', 'data', 'closing'];
const STRESS = ['d2', 'd3', 'd4', 'd7'];
const IDS = ['e6', 'g2', 'e7', 'f1'];
const cases = [];
IDS.forEach(id => {
  ROLES.forEach(role => cases.push({ id, role, variant: null }));
  cases.push({ id, role: 'full', variant: null });
  STRESS.forEach(variant => cases.push({ id, role: 'stress', variant }));
});
cases.push({ id: 'f1', role: 'full', variant: 'b' });   // F1 变体 B（中心聚焦），供 A/B 择优
cases.forEach((c, i) => c.n = i + 1);

const slides = cases.map(c => `<section class="slide ${c.id}" id="s-${c.id}-${c.role}${c.variant ? '-' + c.variant : ''}" ` +
  `data-theme="${c.id}" data-role="${c.role}" data-variant="${c.variant || ''}" style='${TOK[c.id]};font-family:var(--font-body)'>\n` +
  RENDER[c.id](c) + `\n</section>`);

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Phase6 Batch1 · 同一内容 × 4 套 G10 构图程序 · 45 页</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:#15181e;font-family:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif}
.wrap{padding:30px 0 80px}
.hd{color:#e8ebf0;text-align:center;margin-bottom:8px;font-size:22px;font-weight:600}
.sub{color:#8b93a3;text-align:center;margin-bottom:28px;font-size:13px;line-height:1.7}
.slot{margin:0 auto 26px;display:flex;flex-direction:column;align-items:center}
.cap{width:1920px;color:#9aa3b4;font-size:14px;letter-spacing:.06em;margin-bottom:8px;display:flex;justify-content:space-between}
.cap b{color:#dbe0ea;font-weight:600}
.slide{width:1920px;height:1080px;position:relative;overflow:hidden;flex:none;background:var(--paper);color:var(--ink);-webkit-font-smoothing:antialiased}
.slide .bg-layer{position:absolute;inset:0;pointer-events:none;z-index:0}
.slide .bg-layer > *{z-index:0}
.slide > *:not(.bg-layer){z-index:1}
.slide .note{position:absolute;left:120px}
.slide .mastfoot{position:absolute;left:120px;right:120px;bottom:24px;display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid color-mix(in srgb,var(--ink) 22%,transparent);padding-top:12px;font-family:var(--font-mono);
  font-size:max(var(--t-meta),14px);line-height:1.4;letter-spacing:.04em}
.e6 .t-display,.e6 .t-heading,.e6 .t-subhead{font-family:var(--font-display)}
.g2 .t-display,.g2 .t-heading{font-family:var(--font-display)}
.e7 .t-display,.e7 .t-heading,.e7 .t-subhead{font-family:var(--font-display)}
.f1 .t-display,.f1 .t-heading{font-family:var(--font-display)}
.e6 .mt-mem-block{z-index:2}
.g2 .mt-hl-index,.g2 .mt-hl-lineno{z-index:2}
.e7 .mt-uki-plate{z-index:2}
.f1 .mt-gls-depth{z-index:2}
${ROLE_CSS}
${Object.values(MOTIF).join('\n')}
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">Phase 6 · 批次 1 · 同一份「山禾集 1.1」内容 × 4 套 G10 构图程序 × 45 页</div>
  <div class="sub">基线 24 页（4 套 × 6 页型）＋ 完整内容页 5 页（含 F1 双变体）＋ 压力 16 页。<br>
  页面级构图骨架：E6 模块网格+Z 动线 · G2 非对称两栏 · E7 对角线纵深 · F1 对角深度栈(+中心聚焦变体)。<br>
  字号只用骨架 v7.6 的 .t-* 角色类；主题令牌与 G9 母题 CSS 逐字提取自各自 theme.md。</div>
${cases.map((c, i) => `  <div class="slot"><div class="cap"><span>${LABEL[c.id]} · ${c.role}${c.variant ? ' / ' + c.variant : ''}</span><b>${String(c.n).padStart(2, '0')} / 45</b></div>
  ${slides[i]}
  </div>`).join('\n')}
</div>
</body>
</html>`;

fs.writeFileSync(path.join(DIR, 'sampler.html'), html, 'utf8');
fs.writeFileSync(path.join(DIR, 'cases.json'), JSON.stringify(cases, null, 2));
console.log('written sampler.html', Buffer.byteLength(html), 'bytes,', cases.length, 'pages');
