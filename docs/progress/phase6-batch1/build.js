/* phase6-batch1 / build.js
 * 同一份「山禾集 1.1」内容对象 × 4 套 G10 构图程序 × 10 页 = 40 页 sampler。
 *
 * 纪律：
 *  - 唯一内容对象 D；渲染函数只消费、不改写文字（压力变体的长文/极长标题也在 D 里定义）。
 *  - 字号只用骨架 v7.6 的 .t-* 角色类；主题令牌从各自 theme.md 的 G1/G2/G9 css 块**实时提取**，
 *    注入 section 的 inline style，保证与 theme.md 逐字一致。
 *  - G9 母题 CSS 同样从 theme.md 提取，逐字放进 sampler 的 <style>。
 *  - 静态渲染，无任何入场动效。
 */
const fs = require('fs');
const path = require('path');
const ROOT = 'C:/Users/lixiang/Desktop/SlideForge';
const DIR = path.join(ROOT, 'docs/progress/phase6-batch1');
const THEMES = {
  e6: 'color/e6/theme.md', g2: 'color/g2/theme.md',
  e7: 'texture/e7/theme.md', f1: 'light/f1/theme.md'
};
const LABEL = { e6: 'E6 孟菲斯', g2: 'G2 腮红荧光笔', e7: 'E7 浮世绘', f1: 'F1 浮光玻璃' };
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

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
  // 压力集 D2：中文 300+ 字无分段
  longText: '山禾集深耕新式茶饮行业，同时通过全资子公司山禾供应链管理有限公司协同布局上游茶园直采业务。通过多年不懈努力，山禾集秉持“当季鲜茶，日常相伴”的经营理念，建立起从茶园到门店的全链路品控流程，持续为消费者创造价值，赢得了广大茶饮爱好者的喜爱。近年来山禾集门店网络稳步扩张，行业排名持续提升。二〇一九年，山禾集全国门店总数突破八千家，跻身行业头部梯队。截至二〇二六年六月三十日，山禾集全国门店总数八千六百三十七家，其中含直营门店一千六百五十三家、子公司山禾供应链合作门店四百三十二家，标准门店八千四百二十八家，位于行业前列；城市旗舰店总数三百六十一家。成立以来累计为超过六点八亿会员用户售出茶饮二点八亿杯。经营理念是当季鲜茶、日常相伴；使命是为大众提供新鲜、健康、平价的日常茶饮；愿景是成为持续领先的新式茶饮品牌。',
  // 压力集 D3：大数与负数
  bigNums: ['8,637家', '2.8亿杯', '361家', '−12%', '6.8亿'],
  // 压力集 D4：八系列
  series8: [
    { n: '华东', v: 96 }, { n: '华南', v: 82 }, { n: '华北', v: 71 }, { n: '西南', v: 63 },
    { n: '华中', v: 55 }, { n: '东北', v: 42 }, { n: '西北', v: 31 }, { n: '其他', v: 18 }
  ],
  // 压力集 D7：30+ 字极长标题
  longTitle: '从茶园直采到门店现制的全链路品控体系如何持续支撑山禾集的新式茶饮增长叙事',
  singleChar: '茶',
  empty: '—'
};
// 把长文切成 4 段（只切分、不改写）
D.longChunks = [D.longText.slice(0, 105), D.longText.slice(105, 210), D.longText.slice(210, 315), D.longText.slice(315)];
// 把 p1/p2 按语义切成 4 行（只切分、不改写）
D.rows = [D.p1.slice(0, 58), D.p1.slice(58), D.p2.slice(0, 64), D.p2.slice(64, 140)];

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
const box = (content, style, cls = '') => `<div class="${cls}" style="${style}">${content}</div>`;
const text = (cls, s, style) => `<div class="${cls}" style="${style}">${esc(s)}</div>`;
const bars = (arr, x, y, w, color) => arr.map((s, i) =>
  `<div style="${pos(x, y + i * 22, w, 12)};background:color-mix(in srgb,var(--accent) ${Math.max(18, s.v)}%,var(--paper));border:1px solid color-mix(in srgb,var(--ink) 20%,transparent)"></div>` +
  text('t-meta', s.n, `${pos(x + w + 12, y + i * 22 - 3, 120, 20)}`)
).join('');
const foot = (id, role, n) => `<div class="mastfoot"><span>${esc(D.footL)}</span><span>${LABEL[id]} · ${role}</span><span>${n} / 40</span></div>`;
const note = (y = 1000) => text('t-meta', D.note, `${pos(120, y, 1500, 24)}`);
const kicker = (x, y, s = D.kicker) => text('t-meta', s, `${pos(x, y, 600, 24)};letter-spacing:.1em`);

/* =================== E6 之字路径积木 =================== */
function E6(p) {
  const h = [];
  const conf = [[1680, 120], [1760, 420], [120, 980], [1840, 900]].map(([x, y], i) =>
    `<i class="mt-mem-dot ${i % 2 ? 'mt-mem-c2' : ''}" style="left:${x}px;top:${y}px"></i>`).join('');
  h.push(`<div class="bg-layer"><div class="mt-mem-path"></div><div class="mt-mem-confetti">${conf}</div></div>`);
  h.push(kicker(120, 96));
  const block = (x, y, w, hh, inner, focus, idx) => {
    const bg = focus ? 'var(--accent)' : `var(--palette-${(idx % 3) + 2})`;
    const color = focus ? 'var(--accent-on)' : 'var(--ink)';
    return `<div class="mt-mem-block ${focus ? 'mt-mem-block--focus' : ''}" data-block="${idx}" style="${pos(x, y, w, hh)};background:${bg};color:${color}">${inner}</div>`;
  };
  const step = i => `<span class="mt-mem-step"></span>`;
  const R = p.role, V = p.variant;

  if (R === 'cover' || V === 'd7') {
    const ttl = V === 'd7' ? D.longTitle : D.title;
    const cls = V === 'd7' ? 't-heading' : 't-display';
    h.push(block(140, 260, 1600, 460,
      `<div class="${cls}" style="font-weight:800;white-space:pre-line">${esc(ttl.length > 18 ? ttl.slice(0, 16) + '\n' + ttl.slice(16, 32) + (ttl.length > 32 ? '\n' + ttl.slice(32) : '') : ttl)}</div>` +
      text('t-meta', D.subtitle, 'margin-top:26px;font-family:var(--font-mono)'), true, 0));
    h.push(text('t-meta', '之字路径 · 第 01 版', `${pos(120, 800, 600, 24)};font-family:var(--font-mono);letter-spacing:.12em`));
  } else if (V === 'd2') {
    D.longChunks.forEach((s, i) => h.push(block(120 + i * 60, 180 + i * 195, 900 + i * 90, 170,
      text('t-caption', s, 'line-height:1.55'), false, i)));
  } else if (V === 'd4') {
    h.push(block(120, 190, 1660, 700, text('t-heading', '八系列 · 门店分布', 'font-weight:800;margin-bottom:26px') +
      bars(D.series8, 60, 150, 1100), false, 0));
  } else if (R === 'toc') {
    D.toc.forEach((s, i) => h.push(block(140 + i * 330, 700 - i * 115, 330, 165,
      `<div class="t-subhead" style="font-weight:800">${step(i)}${String(i + 1).padStart(2, '0')}</div>` +
      text('t-caption', s, 'margin-top:10px'), false, i)));
  } else if (R === 'claim' || R === 'closing') {
    const main = R === 'claim' ? D.claim : D.closing;
    const sub = R === 'claim' ? D.claimNote : D.closingNote;
    h.push(block(140, 250, 1440, 380,
      text('t-display', main, 'font-weight:800') + text('t-meta', sub, 'margin-top:24px'), true, 0));
    h.push(block(420, 690, 1080, 190, text('t-body', D.creed[0], 'font-weight:600'), false, 1));
  } else if (R === 'analysis') {
    [D.rows[0], D.rows[1], D.p2.slice(0, 100)].forEach((s, i) =>
      h.push(block(140 + i * 150, 200 + i * 250, 760 + i * 140, 220,
        text('t-meta', '版 ' + String(i + 1).padStart(2, '0'), 'font-family:var(--font-mono);margin-bottom:8px') +
        text('t-caption', s, 'line-height:1.55'), false, i)));
  } else if (R === 'data' || V === 'd3') {
    const nums = V === 'd3' ? D.bigNums.slice(0, 3) : D.kpis.map(k => k.num);
    nums.forEach((n, i) => h.push(block(140 + i * 540, 660 - i * 175, 480 + i * 60, 210 + i * 40,
      `<div class="${i === 2 ? 't-display' : 't-heading'}" style="font-weight:800">${esc(n)}</div>` +
      text('t-meta', (D.kpis[i] && D.kpis[i].cap) || '同比变化', 'margin-top:10px'), i === 2, i)));
    h.push(text('t-meta', '结论：三项数字沿之字路径逐级放大，末块为唯一焦点', `${pos(140, 900, 1200, 24)}`));
  }
  h.push(note(1010));
  h.push(foot('e6', R + (V ? '/' + V : ''), p.n));
  return h.join('\n');
}

/* =================== G2 正文层 / 批注层双坐标 =================== */
function G2(p) {
  const h = [];
  const R = p.role, V = p.variant;
  const X_TEXT = 170, X_LEAD = 1210, X_IDX = 1340;
  const lead = (y, i) => `<div class="mt-hl-lead" data-lead="${i}" style="${pos(X_LEAD, y + 20, 120, 5)};--hl-c:var(--hl-${i % 2 + 1})"></div>`;
  const lineNo = (y, i) => `<div class="mt-hl-lineno" style="${pos(100, y, 56, 24)}">${String(i + 1).padStart(2, '0')}</div>`;
  const idx = (y, s, i) => `<div class="mt-hl-index" style="${pos(X_IDX, y - 8, 440, 74)};--hl-c:var(--hl-${i % 2 + 1})">` +
    text('t-caption', s, '') + `</div>`;
  const row = (y, s, tag, i) => lineNo(y, i) + text('t-caption', s, `${pos(X_TEXT, y, 1020, 74)};line-height:1.5`) + lead(y, i) + idx(y, tag, i);
  h.push(`<div class="bg-layer" style="background:repeating-linear-gradient(0deg,transparent 0 87px,color-mix(in srgb,var(--ink) 8%,transparent) 87px 88px)"></div>`);
  h.push(kicker(100, 96));
  h.push(text('t-meta', '笔记正文层', `${pos(X_TEXT, 150, 400, 24)};font-family:var(--font-mono);letter-spacing:.14em`));
  h.push(text('t-meta', '标注索引脊', `${pos(X_IDX, 150, 400, 24)};font-family:var(--font-mono);letter-spacing:.14em`));

  if (R === 'cover' || V === 'd7') {
    const ttl = V === 'd7' ? D.longTitle : D.title;
    h.push(`<div class="t-${V === 'd7' ? 'heading' : 'display'}" style="${pos(120, 280, 1500, 320)};font-weight:700;white-space:pre-line"><span class="mt-hl-mark">${esc(ttl.length > 18 ? ttl.slice(0, 16) + '\n' + ttl.slice(16, 32) + (ttl.length > 32 ? '\n' + ttl.slice(32) : '') : ttl)}</span></div>`);
    h.push(`<div class="mt-hl-tape" style="${pos(1500, 240, 88, 24)}"></div>`);
    h.push(idx(680, V === 'd7' ? '极长标题 · 一次标注' : '唯一焦点 · 一杯好茶', 0));
    h.push(text('t-meta', D.subtitle, `${pos(120, 700, 800, 24)}`));
  } else if (V === 'd2') {
    const chunks = [D.longText.slice(0, 95), D.longText.slice(95, 190), D.longText.slice(190, 285), D.longText.slice(285, 380), D.longText.slice(380)];
    chunks.forEach((s, i) => {
      const y = 210 + i * 140;
      h.push(lineNo(y, i) + text('t-caption', s, `${pos(X_TEXT, y, 1020, 130)};line-height:1.5`) + lead(y, i) + idx(y, '长段落 · 第 ' + (i + 1) + ' 段', i));
    });
  } else if (V === 'd4') {
    h.push(text('t-heading', '八系列 · 门店分布', `${pos(X_TEXT, 210, 900, 70)};font-weight:700`));
    D.series8.forEach((s, i) => {
      const y = 300 + i * 74;
      h.push(lineNo(y, i) + text('t-caption', s.n + ' · ' + s.v + '%', `${pos(X_TEXT, y, 1020, 60)}`) + lead(y, i) + idx(y, '系列 ' + (i + 1), i));
    });
  } else if (R === 'toc') {
    D.toc.forEach((s, i) => h.push(row(230 + i * 130, s, '章节 ' + String(i + 1).padStart(2, '0'), i)));
  } else if (R === 'claim' || R === 'closing') {
    const main = R === 'claim' ? D.claim : D.closing;
    h.push(text('t-display', main, `${pos(X_TEXT, 230, 1020, 150)};font-weight:700`));
    h.push(row(440, R === 'claim' ? D.claimNote : D.closingNote, '主张 · 关键词', 0));
    h.push(row(590, D.creed[0], '经营理念', 1));
    h.push(row(740, D.creed[2], '愿景', 2));
  } else if (R === 'analysis') {
    D.rows.forEach((s, i) => h.push(row(230 + i * 165, s, ['上游直采', '全链路品控', '门店网络', '会员规模'][i], i)));
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

/* =================== E7 横向三层套印 =================== */
function E7(p) {
  const h = [];
  const R = p.role, V = p.variant;
  const plates = [[0, 170, 260], [48, 470, 250], [96, 760, 220]];
  const band = (y, cls) => `<div class="mt-uki-band ${cls}" style="${pos(0, y, 1920, 12)}"></div>`;
  const plate = (i, inner, edition, first) => {
    const [x, y, hh] = plates[i];
    return `<div class="mt-uki-plate ${first ? 'mt-uki-plate--first' : ''}" data-plate="${i + 1}" style="${pos(x, y, 1920 - x, hh)}">${inner}` +
      `<div class="mt-uki-edition t-meta" style="${pos(1920 - x - 180, 18, 140, 40)}">版次 ${esc(edition)}</div></div>`;
  };
  h.push(`<div class="bg-layer"></div>`);
  h.push(kicker(120, 96));
  h.push(`<div class="t-meta" style="${pos(1810, 40, 60, 150)};writing-mode:vertical-rl;letter-spacing:.2em">远景题名</div>`);

  if (R === 'cover' || V === 'd7') {
    const ttl = V === 'd7' ? D.longTitle : D.title;
    h.push(`<div class="mt-uki-plate mt-uki-plate--first" data-plate="1" style="${pos(0, 180, 1920, 620)}">` +
      `<div class="t-${V === 'd7' ? 'heading' : 'display'}" style="${pos(120, 100, 1500, 300)};font-weight:700;white-space:pre-line">${esc(ttl.length > 18 ? ttl.slice(0, 16) + '\n' + ttl.slice(16) : ttl)}</div>` +
      text('t-meta', D.subtitle, `${pos(120, 460, 900, 24)};font-family:var(--font-mono)`) + `</div>`);
    h.push(band(812, 'mt-uki-wave'));
    h.push(`<span class="mt-uki-seal" style="${pos(1700, 860, 104, 104)}">茶</span>`);
  } else if (V === 'd2') {
    D.longChunks.slice(0, 3).forEach((s, i) => h.push(plate(i,
      text('t-caption', s, `${pos(40, 20, 1500, 200)};line-height:1.5`), ['一', '二', '三'][i], i === 0)));
    [0, 1].forEach((_, i) => h.push(band(i === 0 ? 440 : 730, 'mt-uki-cloud')));
  } else if (V === 'd4') {
    h.push(plate(0, text('t-heading', '八系列 · 门店分布', `${pos(40, 20, 900, 80)};font-weight:700`), '一', true));
    h.push(plate(1, bars(D.series8, 40, 16, 1200), '二', false));
    h.push(plate(2, text('t-caption', D.creed[2], `${pos(40, 20, 1200, 80)}`), '三', false));
    [0, 1].forEach((_, i) => h.push(band(i === 0 ? 440 : 730, 'mt-uki-cloud')));
  } else if (R === 'toc') {
    [D.toc.slice(0, 2).join('　/　'), D.toc.slice(2, 4).join('　/　'), D.toc[4]].forEach((s, i) =>
      h.push(plate(i, text('t-subhead', s, `${pos(40, 60, 1500, 120)};font-weight:600`), ['一', '二', '三'][i], i === 0)));
    [0, 1].forEach((_, i) => h.push(band(i === 0 ? 440 : 730, 'mt-uki-cloud')));
  } else if (R === 'claim' || R === 'closing') {
    const main = R === 'claim' ? D.claim : D.closing;
    h.push(plate(0, text('t-display', main, `${pos(40, 40, 1500, 160)};font-weight:700`), '一', true));
    h.push(plate(1, text('t-body', R === 'claim' ? D.claimNote : D.closingNote, `${pos(40, 50, 1400, 120)}`), '二', false));
    h.push(plate(2, text('t-caption', D.creed[0], `${pos(40, 40, 1200, 80)}`), '三', false));
    [0, 1].forEach((_, i) => h.push(band(i === 0 ? 440 : 730, 'mt-uki-cloud')));
  } else if (R === 'analysis') {
    h.push(plate(0, text('t-caption', D.p1.slice(0, 110), `${pos(40, 24, 1500, 180)};line-height:1.5`), '题', true));
    h.push(plate(1, text('t-caption', D.p2.slice(0, 110), `${pos(40, 24, 1500, 180)};line-height:1.5`), '论', false));
    h.push(plate(2, text('t-caption', D.creed.join('　'), `${pos(40, 24, 1500, 140)};line-height:1.5`), '证', false));
    [0, 1].forEach((_, i) => h.push(band(i === 0 ? 440 : 730, 'mt-uki-cloud')));
  } else if (R === 'data' || V === 'd3') {
    const nums = V === 'd3' ? D.bigNums.slice(0, 3) : D.kpis.map(k => k.num);
    nums.forEach((n, i) => h.push(plate(i,
      text('t-heading', n, `${pos(40, 40, 700, 100)};font-weight:700`) +
      text('t-caption', (D.kpis[i] && D.kpis[i].cap) || '同比变化', `${pos(40, 140, 1400, 60)}`),
      ['一', '二', '三'][i], i === 0)));
    [0, 1].forEach((_, i) => h.push(band(i === 0 ? 440 : 730, 'mt-uki-cloud')));
    h.push(`<span class="mt-uki-seal" style="${pos(1740, 900, 96, 96)}">茶</span>`);
  }
  h.push(note(1010));
  h.push(foot('e7', R + (V ? '/' + V : ''), p.n));
  return h.join('\n');
}

/* =================== F1 斜向玻璃深度栈 =================== */
function F1(p) {
  const h = [];
  const R = p.role, V = p.variant;
  const layers = [
    { x: 120, y: 520, w: 1080, h: 420, tx: 160, ty: 560, tw: 980, th: 320, d: 1, a: 88 },
    { x: 620, y: 300, w: 1000, h: 300, tx: 660, ty: 330, tw: 900, th: 170, d: 2, a: 72 },
    { x: 1120, y: 120, w: 760, h: 260, tx: 1160, ty: 150, tw: 680, th: 150, d: 3, a: 56 }
  ];
  const layer = (i, inner) => {
    const L = layers[i];
    return `<div class="mt-gls-depth" data-depth="${L.d}" style="${pos(L.x, L.y, L.w, L.h)};z-index:${4 - L.d};` +
      `background:linear-gradient(155deg,color-mix(in srgb,var(--paper) ${L.a}%,transparent),color-mix(in srgb,var(--paper) ${L.a - 22}%,transparent))">` +
      `<div style="${pos(L.tx - L.x, L.ty - L.y, L.tw, L.th)}">${inner}</div>` +
      `</div>`;
  };
  h.push(`<div class="bg-layer"><div class="mt-gls-blob" style="${pos(80, 60, 620, 620)}"></div><div class="mt-gls-blob" style="${pos(1180, 420, 640, 640)}"></div>` +
    `<div class="mt-gls-axis" data-axis="12" style="${pos(100, 800, 1700, 1)};transform:rotate(-12deg)"></div></div>`);
  h.push(kicker(120, 96));

  if (R === 'cover' || V === 'd7') {
    const ttl = V === 'd7' ? D.longTitle : D.title;
    h.push(`<div class="mt-gls-depth" data-depth="1" style="${pos(120, 250, 1660, 560)};z-index:3;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 88%,transparent),color-mix(in srgb,var(--paper) 66%,transparent))">` +
      `<div class="t-${V === 'd7' ? 'heading' : 'display'}" style="${pos(80, 90, 1480, 320)};font-weight:400;white-space:pre-line">${esc(ttl.length > 18 ? ttl.slice(0, 16) + '\n' + ttl.slice(16) : ttl)}</div>` +
      text('t-meta', D.subtitle, `${pos(80, 440, 800, 24)}`) + `</div>`);
  } else if (V === 'd2') {
    h.push(layer(0, text('t-caption', D.longChunks[0], 'line-height:1.5') + text('t-caption', D.longChunks[1], 'line-height:1.5;margin-top:12px')));
    h.push(layer(1, text('t-caption', D.longChunks[2], 'line-height:1.5')));
    h.push(layer(2, text('t-meta', D.longChunks[3].slice(0, 40), 'line-height:1.5')));
  } else if (V === 'd4') {
    h.push(layer(0, text('t-heading', '八系列 · 门店分布', 'font-weight:400;margin-bottom:18px') + bars(D.series8, 0, 100, 760)));
    h.push(layer(1, text('t-caption', D.p1.slice(0, 70), 'line-height:1.5')));
    h.push(layer(2, text('t-meta', D.footL)));
  } else if (R === 'toc') {
    h.push(layer(0, D.toc.slice(0, 2).map(s => text('t-body', s, 'margin-bottom:14px')).join('')));
    h.push(layer(1, D.toc.slice(2, 4).map(s => text('t-caption', s, 'margin-bottom:8px')).join('')));
    h.push(layer(2, text('t-caption', D.toc[4])));
  } else if (R === 'claim' || R === 'closing') {
    const main = R === 'claim' ? D.claim : D.closing;
    h.push(layer(0, text('t-display', main, 'font-weight:400') + text('t-meta', R === 'claim' ? D.claimNote : D.closingNote, 'margin-top:18px')));
    h.push(layer(1, text('t-body', D.creed[0])));
    h.push(layer(2, text('t-meta', D.creed[2])));
  } else if (R === 'analysis') {
    h.push(layer(0, text('t-caption', D.p1.slice(0, 120), 'line-height:1.5') + text('t-caption', D.p1.slice(120, 200), 'line-height:1.5;margin-top:12px')));
    h.push(layer(1, text('t-caption', D.p2.slice(0, 90), 'line-height:1.5')));
    h.push(layer(2, text('t-meta', D.kicker)));
  } else if (R === 'data' || V === 'd3') {
    const nums = V === 'd3' ? D.bigNums.slice(0, 3) : D.kpis.map(k => k.num);
    h.push(layer(0, text('t-subhead', D.footL, 'font-weight:500') +
      nums.map((n, i) => `<span class="mt-gls-chip-n" style="position:absolute;left:${i * 300}px;top:84px"><span class="t-subhead" style="font-weight:600">${esc(n)}</span></span>`).join('')));
    h.push(layer(1, text('t-caption', D.kpis[0].cap, 'line-height:1.5')));
    h.push(layer(2, text('t-meta', '结论数字 · 深度 3')));
  }
  h.push(note(1010));
  h.push(foot('f1', R + (V ? '/' + V : ''), p.n));
  return h.join('\n');
}

/* ---------------- 组装 40 页 ---------------- */
const RENDER = { e6: E6, g2: G2, e7: E7, f1: F1 };
const ROLES = ['cover', 'toc', 'claim', 'analysis', 'data', 'closing'];
const STRESS = ['d2', 'd3', 'd4', 'd7'];
const IDS = ['e6', 'g2', 'e7', 'f1'];
const cases = [];
IDS.forEach(id => {
  ROLES.forEach(role => cases.push({ id, role, variant: null }));
  STRESS.forEach(variant => cases.push({ id, role: 'stress', variant }));
});
cases.forEach((c, i) => c.n = i + 1);

const slides = cases.map(c => `<section class="slide ${c.id}" id="s-${c.id}-${c.role}${c.variant ? '-' + c.variant : ''}" ` +
  `data-theme="${c.id}" data-role="${c.role}" data-variant="${c.variant || ''}" style='${TOK[c.id]};font-family:var(--font-body)'>\n` +
  RENDER[c.id](c) + `\n</section>`);

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Phase6 Batch1 · 同一内容 × 4 套 G10 构图程序 · 40 页</title>
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
  <div class="hd">Phase 6 · 批次 1 · 同一份「山禾集 1.1」内容 × 4 套 G10 构图程序 × 40 页</div>
  <div class="sub">基线 24 页（4 套 × 6 页型）＋ 压力 16 页（4 套 × 4 变体）。每页按该主题 signature_operator 重新编译 DOM。<br>
  字号只用骨架 v7.6 的 .t-* 角色类；主题令牌与 G9 母题 CSS 逐字提取自各自 theme.md。</div>
${cases.map((c, i) => `  <div class="slot"><div class="cap"><span>${LABEL[c.id]} · ${c.role}${c.variant ? ' / ' + c.variant : ''}</span><b>${String(c.n).padStart(2, '0')} / 40</b></div>
  ${slides[i]}
  </div>`).join('\n')}
</div>
</body>
</html>`;

fs.writeFileSync(path.join(DIR, 'sampler.html'), html, 'utf8');
fs.writeFileSync(path.join(DIR, 'cases.json'), JSON.stringify(cases, null, 2));
console.log('written sampler.html', Buffer.byteLength(html), 'bytes,', cases.length, 'pages');
