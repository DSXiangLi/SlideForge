/* phase6-batch3 / build.js
 *
 * 4 套主题 × 4 页型（cover/claim/analysis/data）= 16 页基线
 * G4 靛墨黄页 · G5 三色旬刊 · E2 蓝图 · E3 装饰艺术
 * 每套按 G10 signature_operator 重编译 DOM（不是换 token 换皮）
 *
 * v2（根因修复后）：
 * - 移除所有 inline line-height 覆盖（typography.md §6 硬规则）
 * - 容器 padding 按 components.md §12 硬规则 9 分档
 * - display 标题加 white-space:nowrap（typography.md §1 硬规则）
 * - 同组并列容器用 flex/grid 对齐（components.md §13 硬规则 5）
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const DIR = path.join(__dirname);
const THEMES = {
  g4: 'color/g4/theme.md',
  g5: 'color/g5/theme.md',
  e2: 'line/e2/theme.md',
  e3: 'space/e3/theme.md'
};
const LABEL = {
  g4: 'G4 靛墨黄页', g5: 'G5 三色旬刊',
  e2: 'E2 蓝图', e3: 'E3 装饰艺术'
};
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const pos = (x, y, w, h) => `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px`;

/* ---------------- 唯一内容对象 D（沿用批次 1 v2） ---------------- */
const D = {
  kicker: '1.1 · 整体特色及优势',
  title: '一杯好茶  山野作答',
  subtitle: '山禾集 · 经营情况汇报 · 2026',
  p1: '山禾集深耕新式茶饮行业，同时通过全资子公司山禾供应链管理有限公司协同布局上游茶园直采业务。通过多年不懈努力，山禾集秉持"当季鲜茶，日常相伴"的经营理念，建立起从茶园到门店的全链路品控流程，持续为消费者创造价值，赢得了广大茶饮爱好者的喜爱。',
  p2: '近年来山禾集门店网络稳步扩张，行业排名持续提升。2019年，山禾集全国门店总数突破八千家，跻身行业头部梯队。截至2026年6月30日，山禾集全国门店总数8,637家（含直营门店1,653家，子公司山禾供应链合作门店432家），其中标准门店8,428家，位于行业前列；城市旗舰店总数361家。成立以来累计为超过6.8亿会员用户售出茶饮2.8亿杯。',
  kpis: [
    { num: '8,637家', cap: '山禾集全国门店总数', tag: '行业前列' },
    { num: '2.8亿杯', cap: '累计售出茶饮' },
    { num: '361家', cap: '城市旗舰店总数' }
  ],
  creed: [
    '经营理念：当季鲜茶，日常相伴。',
    '使命：为大众提供新鲜、健康、平价的日常茶饮。',
    '愿景：成为持续领先的新式茶饮品牌。'
  ],
  claim: '从茶园到门店',
  claimNote: '一杯好茶的答案，写在每一片叶子的来路上。',
  note: '* 注：山禾集为虚构演示品牌，文中数据均为虚构，仅用于主题样式对比展示。',
  footL: '山禾集 · 经营情况汇报'
};
const ttl = esc(D.title).replace(/ /g, '&nbsp;');

/* ---------------- 从 theme.md 提取 token 与母题 CSS ---------------- */
function cssBlocks(txt) { return [...txt.matchAll(/```css\r?\n([\s\S]*?)```/g)].map(m => m[1]); }
function sectionAfter(txt, name) {
  const i = txt.indexOf('**' + name);
  if (i < 0) throw new Error('缺段 ' + name);
  return txt.slice(i);
}
const TOK = {}, MOTIF = {}, TTYPE = {};
for (const [id, rel] of Object.entries(THEMES)) {
  const t = fs.readFileSync(path.join(ROOT, 'skills/SlideForge/references/themes', rel), 'utf8').replace(/\r\n/g, '\n');
  const g1 = cssBlocks(sectionAfter(t, 'G1 color'))[0];
  const g2 = cssBlocks(sectionAfter(t, 'G2 typography'))[0];
  const g9 = cssBlocks(sectionAfter(t, 'G9 motif')).find(b => b.includes('.mt-'));
  if (!g1 || !g2 || !g9) throw new Error(id + ': token/CSS 提取失败');
  const root = (g9.match(/:root\{([^}]*)\}/) || [, ''])[1];
  TOK[id] = [g1.replace(/\s*\n\s*/g, ' '), g2.replace(/\s*\n\s*/g, ' '), root].filter(Boolean).join(';');
  MOTIF[id] = g9;
  // 提取 G3 texture
  const g3 = cssBlocks(sectionAfter(t, 'G3 texture'))[0];
  TTYPE[id] = g3 || '';
}

/* ---------------- 骨架 v7.6 角色类 ---------------- */
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

const M = 120, G = 40, CW = 1680;
const note = (y = 1000) => `<div class="t-meta note" style="position:absolute;left:${M}px;top:${y}px">${esc(D.note)}</div>`;
const kicker = (y = 96) => `<div class="t-meta" style="position:absolute;left:${M}px;top:${y}px;letter-spacing:.1em">${esc(D.kicker)}</div>`;
const foot = (id, role) => `<div class="mastfoot"><span>${esc(D.footL)}</span><span>${LABEL[id]} · ${role}</span><span>—</span></div>`;

/* =================== G4 海报式不对称出血 ===================
 * signature_operator: 出血色面 + 靛蓝结构线 + 展览编号签
 * - cover: 满版黄出血 + 靛蓝巨字反白 + 编号签
 * - claim: 裂屏对开（黄/靛上下对撞）
 * - analysis: 靛蓝线框分区在纸底上
 * - data: 靛蓝线框 + 黄面焦点
 */
function G4(role) {
  const h = [];
  // 展览编号签
  const num = (x, y, n) => `<div class="mt-bie-num" style="${pos(x, y, 120, 120)};font-size:var(--t-display);display:flex;align-items:center;justify-content:center" data-editable-skip>${n}</div>`;
  // 黄楔出血块
  const wedge = (x, y, w, h2) => `<div class="mt-bie-wedge" style="${pos(x, y, w, h2)}" data-editable-skip></div>`;
  // 双色对撞带
  const band = (y) => `<div class="mt-bie-band" style="position:absolute;left:0;right:0;top:${y}px;height:14px" data-editable-skip></div>`;

  if (role === 'cover') {
    // 满版黄出血 + 靛蓝巨字反白
    h.push(`<div class="bg-layer" style="background:var(--accent)" data-editable-skip></div>`);
    h.push(`<div class="t-meta" style="${pos(M, 96, 400, 30)};color:var(--accent-on);opacity:.9;letter-spacing:.1em">${esc(D.kicker)}</div>`);
    h.push(`<div class="t-meta" style="${pos(820, 96, 400, 30)};color:var(--accent-on);opacity:.9;letter-spacing:.1em;text-align:center">${esc(D.subtitle)}</div>`);
    h.push(`<div class="t-meta" style="${pos(1500, 96, 300, 30)};color:var(--accent-on);opacity:.9;font-family:var(--font-mono);letter-spacing:.14em">EXHIBITION · 2026</div>`);
    h.push(`<div class="t-display" style="${pos(M, 360, CW, 220)};font-weight:900;color:var(--accent-on);font-size:max(var(--t-display),128px);white-space:nowrap">${ttl}</div>`);
    h.push(`<div class="t-subhead" style="${pos(M, 600, 800, 48)};color:var(--accent-on);font-weight:700;letter-spacing:.04em">${esc(D.subtitle)}</div>`);
    h.push(num(1740, 900, '01'));
    h.push(band(880));
    h.push(`<div class="t-caption" style="${pos(M, 920, 800, 30)};color:var(--accent-on);opacity:.9">${esc(D.creed[0])}</div>`);
  } else if (role === 'claim') {
    // 裂屏对开：上半黄面 + 下半靛蓝面
    h.push(`<div class="bg-layer" data-editable-skip>
      <div style="${pos(0, 0, 1920, 480)};background:var(--accent)"></div>
      <div style="${pos(0, 480, 1920, 600)};background:var(--paper)"></div>
    </div>`);
    h.push(kicker(60));
    // 上半：黄面上的主张句
    h.push(`<div class="t-display" style="${pos(M, 160, CW, 180)};font-weight:900;color:var(--accent-on);font-size:max(var(--t-display),128px);white-space:nowrap">${esc(D.claim)}</div>`);
    h.push(`<div class="t-body" style="${pos(M, 350, 1000, 80)};color:var(--accent-on)">${esc(D.claimNote)}</div>`);
    // 下半：纸底上的说明 + KPI
    h.push(`<div style="${pos(M, 540, 1000, 2)};background:var(--ink);height:1.5px" data-editable-skip></div>`);
    h.push(`<div class="t-body" style="${pos(M, 570, 760, 200)}">${esc(D.p1.slice(0, 80))}……</div>`);
    // KPI：靛蓝线框纵向排列（padding ≥28px for heading 档，容器高度需容纳 heading+meta）
    D.kpis.forEach((k, i) => {
      const y = 490 + i * 175;
      const isFocus = i === 0;
      h.push(`<div style="${pos(1100, y, 560, 170)};border:1.5px solid var(--ink);padding:28px 32px;${isFocus ? 'background:var(--accent)' : 'background:var(--paper-tint)'}">
        <div class="t-heading" style="font-weight:800;${isFocus ? 'color:var(--accent-on)' : ''}">${esc(k.num)}</div>
        <div class="t-meta" style="margin-top:6px;${isFocus ? 'color:var(--accent-on)' : ''}">${esc(k.cap)}</div>
      </div>`);
    });
    h.push(num(1740, 900, '02'));
    h.push(band(500));
  } else if (role === 'analysis') {
    // 靛蓝线框分区在纸底上
    h.push(kicker());
    h.push(`<div class="t-display" style="${pos(M, 180, CW, 140)};font-weight:900;white-space:nowrap">${ttl}</div>`);
    h.push(wedge(1740, 180, 120, 120));
    // 3 个靛蓝线框分区，至多一个黄面焦点
    const blocks = [
      { x: M, y: 360, w: 520, h: 300, focus: false, text: D.p1.slice(0, 80) + '……' },
      { x: 700, y: 360, w: 520, h: 300, focus: true, text: D.creed[0] + ' ' + D.creed[1] },
      { x: 1280, y: 360, w: 520, h: 300, focus: false, text: D.p2.slice(0, 80) + '……' }
    ];
    blocks.forEach(b => {
      h.push(`<div style="${pos(b.x, b.y, b.w, b.h)};border:1.5px solid var(--ink);padding:24px 28px;${b.focus ? 'background:var(--accent);color:var(--accent-on)' : 'background:var(--paper)'}">
        <div class="t-body">${esc(b.text)}</div>
      </div>`);
    });
    // 底部 creed 行
    h.push(`<div style="${pos(M, 720, 1080, 30)}">${D.creed.map(c => `<span class="t-caption" style="display:inline-block;margin-right:34px">${esc(c)}</span>`).join('')}</div>`);
    // 底部 KPI 行：靛蓝线框（padding ≥28px for heading 档）
    D.kpis.forEach((k, i) => {
      const x = M + i * 550;
      h.push(`<div style="${pos(x, 790, 510, 140)};border:1.5px solid var(--ink);padding:28px 32px;${i === 0 ? 'background:var(--accent);color:var(--accent-on)' : ''}">
        <div class="t-heading" style="font-weight:800">${esc(k.num)}</div>
        <div class="t-meta" style="margin-top:6px">${esc(k.cap)}</div>
      </div>`);
    });
    h.push(num(1740, 950, '03'));
    h.push(note(990));
  } else if (role === 'data') {
    // 靛蓝线框 + 黄面焦点
    h.push(kicker());
    h.push(`<div class="t-display" style="${pos(M, 180, CW, 140)};font-weight:900;white-space:nowrap">数据宣言</div>`);
    h.push(wedge(1740, 180, 120, 120));
    // 主 KPI：大黄面焦点（display 内容 → padding ≥ 40px）
    h.push(`<div style="${pos(M, 340, 1080, 520)};background:var(--accent);padding:44px 56px;overflow:visible">
      <div class="t-meta" style="color:var(--accent-on);letter-spacing:.12em;font-family:var(--font-mono);margin-bottom:16px">KEY METRIC</div>
      <div class="t-display" style="font-weight:900;color:var(--accent-on);font-size:max(var(--t-display),128px);white-space:nowrap;overflow:visible;height:170px">${esc(D.kpis[0].num)}</div>
      <div class="t-subhead" style="color:var(--accent-on);margin-top:16px;font-weight:700">${esc(D.kpis[0].cap)}</div>
      <div class="t-meta" style="color:var(--accent-on);margin-top:8px;opacity:.8">${esc(D.kpis[0].tag)}</div>
    </div>`);
    // 辅助 KPI：靛蓝线框纵向（padding ≥28px for heading 档）
    D.kpis.slice(1).forEach((k, i) => {
      const y = 380 + i * 210;
      h.push(`<div style="${pos(1240, y, 560, 190)};border:1.5px solid var(--ink);padding:28px 32px;background:var(--paper-tint)">
        <div class="t-heading" style="font-weight:800">${esc(k.num)}</div>
        <div class="t-meta" style="margin-top:8px">${esc(k.cap)}</div>
      </div>`);
    });
    h.push(`<div class="t-body" style="${pos(M, 880, 1080, 120)}">${esc(D.p2.slice(0, 100))}……</div>`);
    h.push(num(1740, 900, '04'));
    h.push(note(1010));
  }
  h.push(foot('g4', role));
  return h.join('\n');
}

/* =================== G5 三色反转配对面 ===================
 * signature_operator: 三色反转面 + 色面跳跃分区 + 刊号签/三色带
 * - cover: 满屏暗夜蓝底 + 苔绿巨标 + 大刊号签
 * - claim: 裂屏对开（暗夜蓝/苔绿对撞）
 * - analysis: 三色反转面分区
 * - data: 三色反转面并置数字
 */
function G5(role) {
  const h = [];
  // 三色带
  const triBand = (y) => `<div class="mt-tri-band" style="position:absolute;left:0;right:0;top:${y}px" data-editable-skip></div>`;
  // 刊号签
  const tag = (x, y, txt, cls = 'mt-tri-tag') => `<span class="${cls}" style="position:absolute;left:${x}px;top:${y}px" data-editable-skip>${esc(txt)}</span>`;

  if (role === 'cover') {
    // 满屏暗夜蓝底 + 苔绿巨标
    h.push(`<div class="bg-layer" style="background:var(--ink)" data-editable-skip></div>`);
    h.push(tag(M, 96, 'VOL.07 / NO.128'));
    h.push(`<div class="t-display" style="${pos(M, 320, CW, 220)};font-weight:700;color:var(--accent);font-size:max(var(--t-display),112px);white-space:nowrap">${ttl}</div>`);
    h.push(`<div class="t-subhead" style="${pos(M, 560, 800, 48)};color:var(--paper);font-weight:500">${esc(D.subtitle)}</div>`);
    h.push(triBand(640));
    h.push(`<div class="t-caption" style="${pos(M, 700, 800, 30)};color:var(--accent);opacity:.9">${esc(D.creed[0])}</div>`);
    h.push(`<div class="mt-tri-pill-lg" style="position:absolute;left:${M}px;top:800px" data-editable-skip>2026</div>`);
  } else if (role === 'claim') {
    // 裂屏对开：左暗夜蓝底 + 右苔绿底
    h.push(`<div class="bg-layer" data-editable-skip>
      <div style="${pos(0, 0, 960, 1080)};background:var(--ink)"></div>
      <div style="${pos(960, 0, 960, 1080)};background:var(--accent)"></div>
    </div>`);
    h.push(tag(M, 80, 'VOL.07 / NO.128'));
    // 左侧：暗夜蓝底苔绿字——主张句
    h.push(`<div class="t-display" style="${pos(M, 220, 760, 180)};font-weight:700;color:var(--accent);font-size:max(var(--t-display),112px);white-space:nowrap">${esc(D.claim)}</div>`);
    h.push(`<div class="t-body" style="${pos(M, 420, 760, 120)};color:var(--accent);opacity:.9">${esc(D.claimNote)}</div>`);
    // 右侧：苔绿底暗夜蓝字——说明 + KPI
    h.push(`<div class="t-body" style="${pos(1020, 220, 760, 200)};color:var(--ink)">${esc(D.p1.slice(0, 100))}……</div>`);
    // KPI 容器（heading 档 padding ≥ 28px，容器高度需容纳 heading+meta）
    D.kpis.forEach((k, i) => {
      const y = 420 + i * 175;
      h.push(`<div style="${pos(1020, y, 760, 170)};background:var(--paper);color:var(--ink);padding:28px 32px">
        <div class="t-heading" style="font-weight:600">${esc(k.num)}</div>
        <div class="t-meta" style="margin-top:6px">${esc(k.cap)}</div>
      </div>`);
    });
    h.push(triBand(1000));
  } else if (role === 'analysis') {
    // 三色反转面分区
    h.push(kicker());
    h.push(`<div class="t-display" style="${pos(M, 180, CW, 140)};font-weight:700;white-space:nowrap">${ttl}</div>`);
    h.push(tag(1500, 96, 'NO.128'));
    // 3 块三色反转面（赭石底/苔绿底/暗夜蓝底 轮转）
    const blocks = [
      { x: M, y: 360, w: 520, h: 320, bg: 'var(--paper)', fg: 'var(--ink)', text: D.p1.slice(0, 80) + '……' },
      { x: 700, y: 360, w: 520, h: 320, bg: 'var(--accent)', fg: 'var(--ink)', text: D.creed[0] + ' ' + D.creed[1] },
      { x: 1280, y: 360, w: 520, h: 320, bg: 'var(--ink)', fg: 'var(--accent)', text: D.p2.slice(0, 80) + '……' }
    ];
    blocks.forEach(b => {
      h.push(`<div style="${pos(b.x, b.y, b.w, b.h)};background:${b.bg};color:${b.fg};padding:24px 28px">
        <div class="t-body">${esc(b.text)}</div>
      </div>`);
    });
    // 底部 creed 行
    h.push(`<div style="${pos(M, 730, 1080, 30)}">${D.creed.map(c => `<span class="t-caption" style="display:inline-block;margin-right:30px">${esc(c)}</span>`).join('')}</div>`);
    // 底部 KPI：用 flex 布局对齐，不逐个绝对定位（§13 硬规则 5）
    h.push(`<div style="position:absolute;left:1240px;top:730px;width:560px;display:flex;flex-direction:column;gap:12px">
      ${D.kpis.map(k => `<div class="t-meta" style="color:var(--ink)">${esc(k.num)} — ${esc(k.cap)}</div>`).join('')}
    </div>`);
    h.push(triBand(960));
    h.push(note(980));
  } else if (role === 'data') {
    // 三色反转面并置数字
    h.push(kicker());
    h.push(`<div class="t-display" style="${pos(M, 180, CW, 140)};font-weight:700;white-space:nowrap">数据宣言</div>`);
    h.push(tag(1500, 96, 'NO.128'));
    // 3 块三色反转面并置（暗夜蓝底/苔绿底/赭石底）
    const KW = 520, KH = 400, KY = 360, KG = 30;
    const colors = [
      { bg: 'var(--ink)', fg: 'var(--accent)' },
      { bg: 'var(--accent)', fg: 'var(--ink)' },
      { bg: 'var(--paper)', fg: 'var(--ink)' }
    ];
    D.kpis.forEach((k, i) => {
      const x = M + i * (520 + 30);
      const c = colors[i];
      h.push(`<div style="${pos(x, KY, 520, KH)};background:${c.bg};color:${c.fg};padding:36px 40px;display:flex;flex-direction:column;justify-content:center">
        <div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;margin-bottom:16px;opacity:.7">METRIC ${String(i + 1).padStart(2, '0')}</div>
        <div class="t-heading" style="font-weight:600;font-size:max(var(--t-heading),48px);white-space:nowrap">${esc(k.num)}</div>
        <div class="t-body" style="margin-top:14px">${esc(k.cap)}</div>
      </div>`);
    });
    h.push(`<div class="t-body" style="${pos(M, 800, CW, 120)}">${esc(D.p2.slice(0, 120))}……</div>`);
    h.push(triBand(940));
    h.push(note(960));
  }
  h.push(foot('g5', role));
  return h.join('\n');
}

/* =================== E2 双线图框阵列 + 尺寸标注 ===================
 * signature_operator: 双线图框 + 尺寸标注线 + 制图网格纸
 * - cover: 满版蓝底 + 白线巨标 + 亮青图签
 * - claim: 主图框 + 标注线指向关键数据
 * - analysis: 2-4 同构双线图框成阵
 * - data: 图框内 mono key:value 标注行
 */
function E2(role) {
  const h = [];
  // 制图网格纸（全页铺底）
  const grid = () => `<div class="bg-layer" data-editable-skip></div>`;
  // 图框标题栏
  const titleBar = (x, y, w, items) => {
    const spans = items.map(it => `<span>${esc(it)}</span>`).join('');
    return `<div class="mt-bp-tag" style="${pos(x, y, w, 'auto')}" data-editable-skip>${spans}</div>`;
  };
  // 尺寸标注线
  const dim = (x, y, w, label) => `<div class="mt-bp-dim" style="position:absolute;left:${x}px;top:${y}px;width:${w}px" data-editable-skip><i></i>${esc(label)}<i></i></div>`;
  // 双线图框（默认 padding 24px 28px for body 级内容；display 级用 frameD）
  const frame = (x, y, w, h2, inner, pad) => `<div class="mt-bp-frame" style="${pos(x, y, w, h2)};padding:${pad || '24px 28px'};overflow:visible">${inner}</div>`;

  if (role === 'cover') {
    h.push(grid());
    h.push(`<div class="t-meta" style="${pos(M, 80, 400, 30)};font-family:var(--font-mono);letter-spacing:.14em;color:var(--accent)">DWG-A1 · SCALE 1:50</div>`);
    h.push(`<div class="t-display" style="${pos(M, 300, CW, 220)};font-weight:600;white-space:nowrap;font-size:max(var(--t-display),104px)">${ttl}</div>`);
    h.push(`<div class="t-subhead" style="${pos(M, 540, 800, 48)};font-weight:500;letter-spacing:.04em">${esc(D.subtitle)}</div>`);
    h.push(dim(M, 620, 800, 'W = 1920px'));
    h.push(titleBar(1480, 920, 320, ['DWG-A1', '1:50', '2026']));
    h.push(`<div class="t-caption" style="${pos(M, 700, 800, 30)};font-family:var(--font-mono);opacity:.9">${esc(D.creed[0])}</div>`);
  } else if (role === 'claim') {
    h.push(grid());
    h.push(`<div class="t-meta" style="${pos(M, 80, 400, 30)};font-family:var(--font-mono);letter-spacing:.14em;color:var(--accent)">DWG-A2 · CLAIM</div>`);
    // 主图框（含 display 级文字 → padding ≥ 40px）
    h.push(frame(M, 160, 1080, 360,
      `<div class="t-display" style="font-weight:600;font-size:max(var(--t-display),88px);white-space:nowrap">${esc(D.claim)}</div>` +
      `<div class="t-body" style="margin-top:20px">${esc(D.claimNote)}</div>`,
      '40px 44px'));
    h.push(dim(M, 540, 1080, '1080px'));
    // 右侧图框：KPI 标注（body 级 → padding ≥ 20px）
    h.push(frame(1240, 160, 560, 360,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;color:var(--accent);margin-bottom:16px">STAT --BRIEF</div>` +
      D.kpis.map(k => `<div class="t-body" style="font-family:var(--font-mono)"><span style="color:var(--accent)">${esc(k.num)}</span> ${esc(k.cap)}</div>`).join(''),
      '24px 28px'));
    h.push(dim(1240, 540, 560, '560px'));
    // 底部说明（body 级 → padding ≥ 20px）
    h.push(frame(M, 580, 1680, 200, `<div class="t-body">${esc(D.p1.slice(0, 120))}……</div>`, '24px 28px'));
    h.push(titleBar(1480, 960, 320, ['DWG-A2', '1:100', '2026']));
  } else if (role === 'analysis') {
    h.push(grid());
    h.push(`<div class="t-meta" style="${pos(M, 80, 400, 30)};font-family:var(--font-mono);letter-spacing:.14em;color:var(--accent)">DWG-A3 · ANALYSIS</div>`);
    h.push(`<div class="t-display" style="${pos(M, 160, CW, 120)};font-weight:600;white-space:nowrap">${ttl}</div>`);
    // 3 个同构双线图框成阵（body 级 → padding ≥ 20px）
    const FW = 520, FH = 320, FY = 320, FG = 30;
    const texts = [D.p1.slice(0, 60) + '……', D.creed[0] + ' ' + D.creed[1], D.p2.slice(0, 60) + '……'];
    texts.forEach((txt, i) => {
      const x = M + i * (FW + FG);
      h.push(frame(x, FY, FW, FH,
        `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;color:var(--accent);margin-bottom:12px">SECTION ${String(i + 1).padStart(2, '0')}</div>` +
        `<div class="t-body">${esc(txt)}</div>`));
    });
    h.push(dim(M, 660, 1680, '3 × 520 + 2 × 30 = 1620px'));
    // 底部 KPI 图框（caption 级 → padding ≥ 16px）
    D.kpis.forEach((k, i) => {
      const x = M + i * (FW + FG);
      h.push(frame(x, 700, FW, 160,
        `<div class="t-meta" style="font-family:var(--font-mono);color:var(--accent)">${esc(k.num)}</div>` +
        `<div class="t-caption" style="margin-top:6px">${esc(k.cap)}</div>`));
    });
    h.push(titleBar(1480, 960, 320, ['DWG-A3', '1:200', '2026']));
    h.push(note(980));
  } else if (role === 'data') {
    h.push(grid());
    h.push(`<div class="t-meta" style="${pos(M, 80, 400, 30)};font-family:var(--font-mono);letter-spacing:.14em;color:var(--accent)">DWG-A4 · DATA</div>`);
    h.push(`<div class="t-display" style="${pos(M, 160, CW, 120)};font-weight:600;white-space:nowrap">数据宣言</div>`);
    // 主 KPI 图框（大）（含 display 级 → padding ≥ 40px）
    h.push(frame(M, 320, 1080, 400,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;color:var(--accent);margin-bottom:16px">KEY METRIC</div>` +
      `<div class="t-display" style="font-weight:600;font-size:max(var(--t-display),88px);white-space:nowrap">${esc(D.kpis[0].num)}</div>` +
      `<div class="t-subhead" style="margin-top:14px;font-weight:500">${esc(D.kpis[0].cap)}</div>` +
      `<div class="t-meta" style="margin-top:8px;font-family:var(--font-mono);color:var(--accent)">${esc(D.kpis[0].tag)}</div>`,
      '40px 44px'));
    h.push(dim(M, 740, 1080, '1080px'));
    // 辅助 KPI 图框（caption 级 → padding ≥ 16px）
    D.kpis.slice(1).forEach((k, i) => {
      const y = 320 + i * 200;
      h.push(frame(1240, y, 560, 170,
        `<div class="t-meta" style="font-family:var(--font-mono);color:var(--accent)">${esc(k.num)}</div>` +
        `<div class="t-caption" style="margin-top:6px">${esc(k.cap)}</div>`));
    });
    h.push(dim(1240, 740, 560, '560px'));
    // 底部说明（body 级 → padding ≥ 20px）
    h.push(frame(M, 760, 1680, 140, `<div class="t-body">${esc(D.p2.slice(0, 100))}……</div>`));
    h.push(titleBar(1480, 960, 320, ['DWG-A4', '1:50', '2026']));
  }
  h.push(foot('e2', role));
  return h.join('\n');
}

/* =================== E3 中轴对称金线放射 ===================
 * signature_operator: 双线金框对称阵列 + 扇形 sunburst + 菱形分隔
 * - cover: 双线金框整页内框 + 页顶 sunburst + 中轴标题
 * - claim: 中轴金框 + 两侧金线翼卫 + 菱形引出
 * - analysis: 中轴对称双栏
 * - data: 对称双栏镜像模块
 */
function E3(role) {
  const h = [];
  // 菱形分隔
  const divider = (y) => `<div class="mt-deco-divider" style="position:absolute;left:50%;top:${y}px;transform:translateX(-50%);width:300px" data-editable-skip><span class="mt-deco-rhombus"></span></div>`;
  // 双线金框（默认 padding 28px 36px for body/heading 级；display 级用 goldFrameD）
  const goldFrame = (x, y, w, h2, inner, pad) => `<div class="mt-deco-frame" style="${pos(x, y, w, h2)};padding:${pad || '28px 36px'};overflow:visible">${inner}</div>`;
  // sunburst
  const sun = (y) => `<div class="mt-deco-sun" style="position:absolute;left:50%;top:${y}px;transform:translateX(-50%);opacity:.35" data-editable-skip></div>`;

  if (role === 'cover') {
    // 双线金框整页内框
    h.push(`<div class="mt-deco-frame" style="position:absolute;left:2%;top:2%;right:2%;bottom:2%;pointer-events:none" data-editable-skip></div>`);
    h.push(sun(60));
    h.push(divider(280));
    // kicker
    h.push(`<div class="t-meta" style="position:absolute;left:50%;top:330px;transform:translateX(-50%);letter-spacing:.3em;text-transform:uppercase;font-family:var(--font-mono);color:var(--accent)">${esc(D.kicker)}</div>`);
    h.push(divider(380));
    // 中轴标题（nowrap + 按容器调字号）
    h.push(`<div class="t-display" style="position:absolute;left:50%;top:430px;transform:translateX(-50%);font-weight:700;text-align:center;white-space:nowrap;font-size:max(var(--t-display),96px)">${ttl}</div>`);
    h.push(divider(620));
    // 副标题
    h.push(`<div class="t-subhead" style="position:absolute;left:50%;top:660px;transform:translateX(-50%);text-align:center;font-weight:500">${esc(D.subtitle)}</div>`);
    h.push(`<div class="t-caption" style="position:absolute;left:50%;top:740px;transform:translateX(-50%);text-align:center;opacity:.9">${esc(D.creed[0])}</div>`);
    // 左右对称装饰：金线竖条 + 日期（上移到顶部填充空白格）
    h.push(`<div style="position:absolute;left:120px;top:80px;width:1px;height:200px;background:color-mix(in srgb,var(--accent) 50%,transparent)" data-editable-skip></div>`);
    h.push(`<div class="t-meta" style="position:absolute;left:80px;top:300px;width:100px;text-align:center;font-family:var(--font-mono);color:var(--accent);letter-spacing:.14em;writing-mode:vertical-rl">2026</div>`);
    h.push(`<div style="position:absolute;right:120px;top:80px;width:1px;height:200px;background:color-mix(in srgb,var(--accent) 50%,transparent)" data-editable-skip></div>`);
    h.push(`<div class="t-meta" style="position:absolute;right:80px;top:300px;width:100px;text-align:center;font-family:var(--font-mono);color:var(--accent);letter-spacing:.14em;writing-mode:vertical-rl">EXHIBITION</div>`);
  } else if (role === 'claim') {
    h.push(sun(40));
    h.push(divider(200));
    // 中轴金框装主张句（display 级 → padding ≥ 40px）
    h.push(goldFrame(460, 250, 1000, 300,
      `<div class="t-display" style="font-weight:700;text-align:center;font-size:max(var(--t-display),112px);white-space:nowrap">${esc(D.claim)}</div>` +
      `<div class="t-body" style="margin-top:16px;text-align:center">${esc(D.claimNote)}</div>`,
      '44px 48px'));
    h.push(divider(580));
    // 两侧对称说明（body 级 → padding ≥ 20px）
    h.push(goldFrame(M, 640, 760, 260,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;color:var(--accent);margin-bottom:12px">CONTEXT</div>` +
      `<div class="t-body">${esc(D.p1.slice(0, 60))}……</div>`));
    h.push(goldFrame(1040, 640, 760, 260,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;color:var(--accent);margin-bottom:12px">CREED</div>` +
      `<div class="t-body">${esc(D.creed[0])} ${esc(D.creed[1])}</div>`));
    h.push(divider(890));
    // 底部 KPI 对称排列（heading 级 → 无边框纯文字，不受 padding 下限约束）
    D.kpis.forEach((k, i) => {
      const x = 460 + i * 360;
      h.push(`<div style="position:absolute;left:${x}px;top:920px;width:280px;text-align:center">
        <div class="t-heading" style="font-weight:700">${esc(k.num)}</div>
        <div class="t-meta" style="margin-top:6px;opacity:.8">${esc(k.cap)}</div>
      </div>`);
    });
  } else if (role === 'analysis') {
    h.push(divider(120));
    h.push(`<div class="t-display" style="position:absolute;left:50%;top:160px;transform:translateX(-50%);font-weight:700;text-align:center;white-space:nowrap">${ttl}</div>`);
    h.push(divider(300));
    // 中轴对称双栏（body 级 → padding ≥ 20px）
    h.push(goldFrame(M, 350, 760, 360,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;color:var(--accent);margin-bottom:12px">SECTION A</div>` +
      `<div class="t-body">${esc(D.p1.slice(0, 100))}……</div>` +
      `<div class="t-caption" style="margin-top:16px;opacity:.9">${esc(D.creed[0])}</div>`));
    h.push(goldFrame(1040, 350, 760, 360,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;color:var(--accent);margin-bottom:12px">SECTION B</div>` +
      `<div class="t-body">${esc(D.p2.slice(0, 100))}……</div>` +
      `<div class="t-caption" style="margin-top:16px;opacity:.9">${esc(D.creed[1])}</div>`));
    h.push(divider(740));
    // 底部对称 KPI（纯文字无容器，不受 padding 下限约束）
    D.kpis.forEach((k, i) => {
      const x = 460 + i * 360;
      h.push(`<div style="position:absolute;left:${x}px;top:780px;width:280px;text-align:center">
        <div class="t-heading" style="font-weight:700">${esc(k.num)}</div>
        <div class="t-meta" style="margin-top:6px;opacity:.8">${esc(k.cap)}</div>
      </div>`);
    });
    h.push(note(960));
  } else if (role === 'data') {
    h.push(sun(40));
    // 左右对称金线竖条填充顶部
    h.push(`<div style="position:absolute;left:120px;top:80px;width:1px;height:180px;background:color-mix(in srgb,var(--accent) 50%,transparent)" data-editable-skip></div>`);
    h.push(`<div class="t-meta" style="position:absolute;left:80px;top:280px;width:100px;text-align:center;font-family:var(--font-mono);color:var(--accent);letter-spacing:.14em;writing-mode:vertical-rl">DATA</div>`);
    h.push(`<div style="position:absolute;right:120px;top:80px;width:1px;height:180px;background:color-mix(in srgb,var(--accent) 50%,transparent)" data-editable-skip></div>`);
    h.push(`<div class="t-meta" style="position:absolute;right:80px;top:280px;width:100px;text-align:center;font-family:var(--font-mono);color:var(--accent);letter-spacing:.14em;writing-mode:vertical-rl">REPORT</div>`);
    h.push(divider(140));
    h.push(`<div class="t-display" style="position:absolute;left:50%;top:180px;transform:translateX(-50%);font-weight:700;text-align:center;white-space:nowrap">数据宣言</div>`);
    h.push(divider(320));
    // 中轴主 KPI 金框（display 级 → padding ≥ 40px）
    h.push(goldFrame(560, 360, 800, 300,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;color:var(--accent);margin-bottom:12px;text-align:center">KEY METRIC</div>` +
      `<div class="t-display" style="font-weight:700;text-align:center;font-size:max(var(--t-display),112px);white-space:nowrap">${esc(D.kpis[0].num)}</div>` +
      `<div class="t-subhead" style="margin-top:14px;text-align:center;font-weight:500">${esc(D.kpis[0].cap)}</div>`,
      '44px 48px'));
    h.push(divider(690));
    // 两侧对称辅助 KPI 金框（heading 级 → padding ≥ 28px）
    h.push(goldFrame(M, 740, 520, 160,
      `<div class="t-heading" style="font-weight:700;text-align:center">${esc(D.kpis[1].num)}</div>` +
      `<div class="t-meta" style="margin-top:6px;text-align:center;opacity:.9">${esc(D.kpis[1].cap)}</div>`));
    h.push(goldFrame(1280, 740, 520, 160,
      `<div class="t-heading" style="font-weight:700;text-align:center">${esc(D.kpis[2].num)}</div>` +
      `<div class="t-meta" style="margin-top:6px;text-align:center;opacity:.9">${esc(D.kpis[2].cap)}</div>`));
    h.push(note(940));
  }
  h.push(foot('e3', role));
  return h.join('\n');
}

/* ---------------- 组装 16 页 ---------------- */
const RENDER = { g4: G4, g5: G5, e2: E2, e3: E3 };
const IDS = ['g4', 'g5', 'e2', 'e3'];
const ROLES = ['cover', 'claim', 'analysis', 'data'];
const cases = [];
IDS.forEach(id => {
  ROLES.forEach(role => {
    cases.push({ id, role });
  });
});

const slides = cases.map(c => `<section class="slide ${c.id}" id="s-${c.id}-${c.role}" ` +
  `data-theme="${c.id}" data-role="${c.role}" style='${TOK[c.id]};font-family:var(--font-body)'>\n` +
  RENDER[c.id](c.role) + `\n</section>`);

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Phase6 Batch3 · Step 4 · 标杆页</title>
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
  font-size:max(var(--t-meta),14px);letter-spacing:.04em;opacity:.6}
.g4 .t-display,.g4 .t-heading,.g4 .t-subhead{font-family:var(--font-display)}
.g5 .t-display,.g5 .t-heading,.g5 .t-subhead{font-family:var(--font-display)}
.e2 .t-display,.e2 .t-heading,.e2 .t-subhead{font-family:var(--font-display)}
.e3 .t-display,.e3 .t-heading,.e3 .t-subhead{font-family:var(--font-display)}
.g4 .mt-bie-wedge,.g4 .mt-bie-num,.g4 .mt-bie-band{z-index:2}
.g5 .mt-tri-band,.g5 .mt-tri-tag,.g5 .mt-tri-pill-lg{z-index:2}
.e2 .mt-bp-frame,.e2 .mt-bp-tag,.e2 .mt-bp-dim{z-index:2}
.e3 .mt-deco-sun,.e3 .mt-deco-frame,.e3 .mt-deco-divider,.e3 .mt-deco-rhombus{z-index:2}
${ROLE_CSS}
${Object.values(MOTIF).join('\n')}
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">Phase 6 · 批次 3 · Step 4 · 标杆页（cover + claim + analysis + data）</div>
  <div class="sub">同一份「山禾集 1.1」内容 × 4 套新 G10 构图程序 × 16 页。<br>
  G4 海报式不对称出血 · G5 三色反转配对面 · E2 双线图框阵列+标注线 · E3 中轴对称金线放射。</div>
${cases.map((c, i) => `  <div class="slot"><div class="cap"><span>${LABEL[c.id]} · ${c.role}</span><b>${String(i + 1).padStart(2, '0')} / 16</b></div>
  ${slides[i]}
  </div>`).join('\n')}
</div>
</body>
</html>`;

fs.writeFileSync(path.join(DIR, 'sampler.html'), html, 'utf8');
console.log('written sampler.html', Buffer.byteLength(html), 'bytes,', cases.length, 'pages');
