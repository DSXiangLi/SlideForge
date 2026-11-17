/* phase6-batch1-v2 / build.js  (Step 4a rev6: claim + full 标杆页)
 *
 * v2 rev6 修复（标题不换行 + F1 对齐）：
 *  - E6: --t-display 132→120px（按容器内宽 1022px 调字号，不换行）
 *  - E6 full: 恢复 white-space:nowrap，容器高度 300→200 回调
 *  - F1 full: KPI chip 和 caption 合并到同一 flex 容器（flex:1 等宽），不再 chip 自适应+caption 固定 320px
 *  - 审计新增：标题紧贴检测（>97% 容器内宽告警）+ 同组等宽检测（同 y 同字号宽度差 >30px 告警）
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const DIR = path.join(__dirname);
const THEMES = {
  e6: 'color/e6/theme.md', g2: 'color/g2/theme.md',
  e7: 'texture/e7/theme.md', f1: 'light/f1/theme.md'
};
const LABEL = { e6: 'E6 孟菲斯', g2: 'G2 腮红荧光笔', e7: 'E7 浮世绘', f1: 'F1 浮光玻璃' };
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const pos = (x, y, w, h) => `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px`;

/* ---------------- 唯一内容对象 D ---------------- */
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
const foot = (id, role) => `<div class="mastfoot"><span>${esc(D.footL)}</span><span>${LABEL[id]} · ${role}</span><span>—</span></div>`;
const note = (y = 1000) => `<div class="t-meta note" style="position:absolute;left:${M}px;top:${y}px">${esc(D.note)}</div>`;
const kicker = (y = 96) => `<div class="t-meta" style="position:absolute;left:${M}px;top:${y}px;letter-spacing:.1em">${esc(D.kicker)}</div>`;

/* =================== E6 几何拼贴构图 ===================
 * 设计原理执行：
 *  - KPI 三块同宽同高（每块 540×240），焦点用 accent 填充区分
 *  - 正文容器宽度够容下文字（820px 宽 × 280px 高可容 ~120 字 body 28px）
 *  - 低密度页(claim)：大色面 + 圆形 + 之字带做视觉填充，不空
 *  - 高密度页(full)：信息块 ≤6，留白率 ≥20%
 */
function E6(role) {
  const h = [];
  const conf = [[1680, 120, 'dot'], [1760, 420, 'tri'], [120, 980, 'ring'], [1840, 900, 'dot'], [1440, 80, 'tri'], [200, 260, 'dot']].map(([x, y, t], i) =>
    `<i class="mt-mem-${t} ${['', 'mt-mem-c2', 'mt-mem-c3', 'mt-mem-c4'][i % 4]}" style="left:${x}px;top:${y}px"></i>`).join('');
  h.push(`<div class="bg-layer"><div class="mt-mem-confetti">${conf}</div></div>`);
  h.push(kicker());

  const block = (x, y, w, hh, inner, o = {}) => {
    const { focus = false, fill = false, accent = false, idx = 0, ink = false } = o;
    const pal = `var(--palette-${(idx % 4) + 1})`;
    const palOn = `var(--palette-${(idx % 4) + 1}-on)`;
    const bg = ink ? 'var(--ink)' : (focus ? 'var(--accent)' : (fill ? pal : (accent ? pal : 'var(--paper)')));
    const color = ink ? 'var(--paper)' : (focus ? 'var(--accent-on)' : (fill || accent ? palOn : 'var(--ink)'));
    return `<div class="mt-mem-block ${focus ? 'mt-mem-block--focus' : ''} ${ink ? 'mt-mem-block--ink' : ''}" style="${pos(x, y, w, hh)};background:${bg};color:${color}">${inner}</div>`;
  };

  if (role === 'claim') {
    // 低密度：主张句在大色面上 + 说明在相邻色面 + 底部 KPI 三块同尺寸
    // 大色面（palette-1 粉）承载主张
    h.push(block(M, 220, 1080, 340,
      `<div class="t-display" style="font-weight:800;line-height:1.05">${esc(D.claim)}</div>` +
      `<div class="t-body" style="margin-top:20px">${esc(D.claimNote)}</div>`,
      { fill: true, idx: 0 }));
    // 相邻小色面（accent 黄）承载 creed
    h.push(block(1240, 220, 560, 340,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;margin-bottom:12px">CREED</div>` +
      `<div class="t-caption" style="line-height:1.6">${esc(D.creed[0])}</div>` +
      `<div class="t-caption" style="line-height:1.6;margin-top:10px">${esc(D.creed[1])}</div>`,
      { accent: true, idx: 1 }));
    // 圆形装饰（视觉填充）
    h.push(`<div class="mt-mem-circle" style="${pos(1360, 600, 160, 160)};background:var(--palette-3)"></div>`);
    // 之字带做过渡
    h.push(`<div class="mt-mem-bar" style="${pos(M, 600, CW, 12)}"></div>`);
    // KPI 三块同宽同高（各 540×240），焦点用 accent 填充
    const KW = 540, KH = 240, KY = 650, KG = 30;
    D.kpis.forEach((k, i) => {
      const x = M + i * (KW + KG);
      h.push(block(x, KY, KW, KH,
        `<div class="t-heading" style="font-weight:800;line-height:1.1">${esc(k.num)}</div>` +
        `<div class="t-meta" style="margin-top:10px;line-height:1.35">${esc(k.cap)}</div>` +
        (k.tag ? `<div class="t-meta" style="margin-top:8px;font-weight:600;color:var(--accent-on)">${esc(k.tag)}</div>` : ''),
        { focus: i === 0, fill: i > 0, idx: i }));
    });
  } else if (role === 'full') {
    // 高密度：标题大色面 + 正文两块 + KPI 三块同尺寸
    // rev6: 标题不换行——按容器调字号（--t-display 132→120px 适配 1080 容器内宽 1022px）
    h.push(block(M, 140, 1080, 200,
      `<div class="t-display" style="font-weight:800;white-space:nowrap;line-height:1.05">${ttl}</div>`,
      { fill: true, idx: 0 }));
    h.push(block(1240, 140, 560, 200,
      `<div class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em">山禾集 · 2026</div>`,
      { accent: true, idx: 1 }));
    // 正文两块等宽等高（820×300）
    h.push(block(M, 380, 820, 300, `<div class="t-body">${esc(D.p1)}</div>`, { idx: 1 }));
    h.push(block(980, 380, 820, 300, `<div class="t-body">${esc(D.p2)}</div>`, { idx: 2 }));
    // KPI 三块同宽同高
    const KW = 540, KH = 200, KY = 720, KG = 30;
    D.kpis.forEach((k, i) => {
      const x = M + i * (KW + KG);
      h.push(block(x, KY, KW, KH,
        `<div class="t-heading" style="font-weight:800;line-height:1.1">${esc(k.num)}</div>` +
        `<div class="t-meta" style="margin-top:8px;line-height:1.35">${esc(k.cap)}</div>`,
        { focus: i === 0, fill: i > 0, idx: i }));
    });
    // 底部 creed
    h.push(`<div style="${pos(M, 950, CW, 26)}">${D.creed.map(c => `<span class="t-caption" style="display:inline-block;margin-right:34px">${esc(c)}</span>`).join('')}</div>`);
  }
  h.push(note(990));
  h.push(foot('e6', role));
  return h.join('\n');
}

/* =================== G2 单栏流式 + 便签浮层 ===================
 * 设计原理执行：
 *  - 便签同宽（340px）
 *  - full 页减少信息块数：不把 creed 单独放底部，融入便签
 *  - claim 页视觉填充：大标题 + 高亮 + 便签组 + 底部 creed 行
 */
function G2(role) {
  const h = [];
  // rev5: 重心修复——正文区 1280→1140，便签从 1460→1300 靠近正文，宽度 340→400
  const X_TEXT = 120, W_TEXT = 1140, X_NOTE = 1300, W_NOTE = 400;
  h.push(`<div class="bg-layer"></div>`);
  h.push(kicker());

  const note_ = (y, inner, cls = '') => `<div class="mt-hl-note ${cls}" style="position:absolute;left:${X_NOTE}px;top:${y}px;width:${W_NOTE}px;min-height:60px">${inner}</div>`;
  const hl = (s) => { const i = s.indexOf('，'); return i < 0 ? `<span class="mt-hl-mark">${esc(s)}</span>` : `<span class="mt-hl-mark">${esc(s.slice(0, i + 1))}</span>${esc(s.slice(i + 1))}`; };

  if (role === 'claim') {
    // 低密度：大标题 + 说明 + 左下 creed 色块 + 右便签组
    // rev5 重心修复：左侧加 KPI 大数字块平衡右侧便签视觉重量
    h.push(`<div class="t-display" style="position:absolute;left:${X_TEXT}px;top:180px;width:${W_TEXT}px;font-weight:700;line-height:1.0;font-size:max(var(--t-display),96px)"><span class="mt-hl-mark" style="--hl-c:var(--accent)">${esc(D.claim)}</span></div>`);
    h.push(`<div class="t-body" style="position:absolute;left:${X_TEXT}px;top:380px;width:760px;line-height:1.7">${hl(D.claimNote)}</div>`);
    // 左下区域：creed 色块（accent 背景，增加视觉重量平衡右侧便签）
    h.push(`<div style="position:absolute;left:${X_TEXT}px;top:540px;width:560px;padding:24px 32px;border-left:4px solid var(--accent);background:var(--paper-tint)">${D.creed.map((c, i) => `<div class="t-caption" style="${i > 0 ? 'margin-top:10px' : ''};line-height:1.6">${esc(c)}</div>`).join('')}</div>`);
    // 左下 KPI 大数字块（与右侧便签呼应，平衡视觉重量）
    h.push(`<div style="position:absolute;left:720px;top:540px;width:420px;padding:24px 32px;background:color-mix(in srgb,var(--accent) 12%,var(--paper))"><div class="t-heading" style="font-weight:700">${esc(D.kpis[0].num)}</div><div class="t-meta" style="margin-top:4px;line-height:1.35">${esc(D.kpis[0].cap)}</div></div>`);
    // mono 标注行
    h.push(`<div class="t-meta" style="position:absolute;left:${X_TEXT}px;top:800px;width:760px;letter-spacing:.06em;color:color-mix(in srgb,var(--ink) 50%,transparent);font-family:var(--font-mono)">— 山禾集 · 2026 年度经营情况汇报</div>`);
    // 便签组（2 枚 KPI 同宽，分布在右侧 y=180~680）
    h.push(note_(180, `<div class="t-caption" style="font-weight:600">关键指标</div><div class="t-meta" style="margin-top:4px;line-height:1.35">行业前列</div>`, 'mt-hl-note--alt'));
    h.push(note_(340, `<div class="t-heading" style="font-weight:700">${esc(D.kpis[1].num)}</div><div class="t-meta" style="margin-top:4px;line-height:1.35">${esc(D.kpis[1].cap)}</div>`, 'mt-hl-note--hl3'));
    h.push(note_(540, `<div class="t-heading" style="font-weight:700">${esc(D.kpis[2].num)}</div><div class="t-meta" style="margin-top:4px;line-height:1.35">${esc(D.kpis[2].cap)}</div>`, 'mt-hl-note--hl4'));
    // 胶带装饰
    h.push(`<div class="mt-hl-tape" style="position:absolute;left:1220px;top:160px;width:88px;height:24px"></div>`);
  } else if (role === 'full') {
    // 高密度：大标题 + 两段正文 + 便签组
    h.push(`<div class="t-display" style="position:absolute;left:${X_TEXT}px;top:180px;width:${W_TEXT}px;font-weight:700;white-space:nowrap;line-height:1.05"><span class="mt-hl-mark" style="--hl-c:var(--accent)">${ttl}</span></div>`);
    h.push(`<div class="t-body" style="position:absolute;left:${X_TEXT}px;top:340px;width:${W_TEXT}px;line-height:1.7">${hl(D.p1)}</div>`);
    h.push(`<div class="t-body" style="position:absolute;left:${X_TEXT}px;top:540px;width:${W_TEXT}px;line-height:1.7">${esc(D.p2)}</div>`);
    // 便签组（同宽）
    h.push(note_(180, `<div class="t-caption" style="font-weight:600">标题</div><div class="t-meta" style="margin-top:4px;line-height:1.35">关键词高亮</div>`, 'mt-hl-note--alt'));
    h.push(note_(360, `<div class="t-caption" style="font-weight:600">上游直采</div><div class="t-meta" style="margin-top:4px;line-height:1.35">全资子公司山禾供应链</div>`, 'mt-hl-note--hl2'));
    h.push(note_(560, `<div class="t-heading" style="font-weight:700">${esc(D.kpis[0].num)}</div><div class="t-meta" style="margin-top:4px;line-height:1.35">${esc(D.kpis[0].cap)}</div>`, 'mt-hl-note--hl3'));
    h.push(note_(720, `<div class="t-heading" style="font-weight:700">${esc(D.kpis[1].num)}</div><div class="t-meta" style="margin-top:4px;line-height:1.35">${esc(D.kpis[1].cap)}</div>`, 'mt-hl-note--hl4'));
    h.push(note_(880, `<div class="t-heading" style="font-weight:700">${esc(D.kpis[2].num)}</div><div class="t-meta" style="margin-top:4px;line-height:1.35">${esc(D.kpis[2].cap)}</div>`, 'mt-hl-note--alt'));
    // 底部 creed 行（上移 950→930 避免与 note y=990 重叠）
    h.push(`<div style="position:absolute;left:${X_TEXT}px;top:930px;width:${W_TEXT}px">${D.creed.map(c => `<span class="t-caption" style="display:inline-block;margin-right:30px">${esc(c)}</span>`).join('')}</div>`);
  }
  h.push(note(990));
  h.push(foot('g2', role));
  return h.join('\n');
}

/* =================== E7 日式不对称三分法 ===================
 * 设计原理执行：
 *  - claim 页：正文宽度限制在前景面左侧（≤400px），不与前景面重叠
 *  - full 页：前景面内文字分行控制，KPI 横排不溢出
 *  - 低密度页(claim)：远山+云霞+印章做视觉填充
 *  - 高密度页(full)：正文在前景面上方，前景面承载标题+KPI
 */
function E7(role) {
  const h = [];
  const seal = (x, y, s = 96) => `<span class="mt-uki-seal" style="${pos(x, y, s, s)}">茶</span>`;
  const band = (y, cls) => `<div class="mt-uki-band ${cls}" style="${pos(0, y, 1920, 12)}"></div>`;
  const farMtn = (x, y, w, h2) => `<div style="${pos(x, y, w, h2)};background:color-mix(in srgb,var(--ink) 13%,transparent);clip-path:polygon(0 100%, 45% 10%, 100% 100%)"></div>`;
  h.push(`<div class="bg-layer"></div>`);
  h.push(kicker());

  if (role === 'claim') {
    // 低密度：远山+云霞做余白填充，前景面右下
    h.push(farMtn(120, 120, 400, 160));
    h.push(band(300, 'mt-uki-cloud'));
    // 余白左上：说明（宽度 380→420 避免换行溢出，高度 80→100 容下两行 body）
    h.push(`<div class="t-body" style="${pos(140, 340, 420, 100)};line-height:1.7">${esc(D.claimNote)}</div>`);
    // 前景深墨面居右下（560 起 → 右边缘 1800，宽 1240）
    h.push(`<div class="mt-uki-plate mt-uki-plate--first" style="${pos(560, 380, 1240, 420)};display:flex;flex-direction:column;justify-content:center;padding:40px 50px">
      <div class="t-display" style="font-weight:700;line-height:1.05">${esc(D.claim)}</div>
      <div style="margin-top:30px">${D.kpis.map((k, i) => `<span style="display:inline-block;margin-right:30px;vertical-align:top"><span class="t-heading" style="font-weight:700">${esc(k.num)}</span><div class="t-meta" style="margin-top:4px;max-width:300px;line-height:1.35">${esc(k.cap)}</div></span>`).join('')}</div>
    </div>`);
    h.push(seal(1740, 96));
    // 余白底部：creed（高度 60→120 容下三行 caption 18px × 1.6 lh）
    h.push(`<div style="${pos(140, 840, 420, 120)};line-height:1.6">${D.creed.map(c => `<div class="t-caption">${esc(c)}</div>`).join('')}</div>`);
  } else if (role === 'full') {
    // 高密度：正文在上方，前景面在下承载标题+KPI
    h.push(farMtn(120, 120, 380, 150));
    h.push(band(300, 'mt-uki-cloud'));
    h.push(`<div class="t-body" style="${pos(140, 340, 1640, 160)};line-height:1.7">${esc(D.p1)}</div>`);
    h.push(`<div class="t-body" style="${pos(140, 520, 1640, 160)};line-height:1.7">${esc(D.p2)}</div>`);
    // 前景深墨面居下满宽
    h.push(`<div class="mt-uki-plate mt-uki-plate--first" style="${pos(120, 720, 1680, 240)};display:flex;flex-direction:column;justify-content:center;padding:24px 50px">
      <div class="t-display" style="font-weight:700;white-space:nowrap;line-height:1.05">${ttl}</div>
      <div style="margin-top:14px">${D.kpis.map((k, i) => `<span style="display:inline-block;margin-right:30px;vertical-align:top"><span class="t-heading" style="font-weight:700">${esc(k.num)}</span><span class="t-meta" style="margin-left:8px">${esc(k.cap)}</span></span>`).join('')}</div>
    </div>`);
    h.push(seal(1740, 96));
  }
  h.push(note(990));
  h.push(foot('e7', role));
  return h.join('\n');
}

/* =================== F1 中心聚焦单玻璃 ===================
 * 设计原理执行：
 *  - 所有玻璃容器 border-radius 统一 24px（G9 CSS 已改，不再用 999px 胶囊）
 *  - 玻璃内文字容量控制：full 页正文精简，不把两段长文全塞进玻璃
 *  - claim 页：玻璃居中，三块 KPI chip 同尺寸（不是三个不同大小）
 *  - 高密度页：玻璃够大，内部纵向流不溢出
 *  - rev4 九宫格修复：玻璃从 1080→1440px 宽（两侧空白 420→240px），光斑加大加密
 */
function F1(role) {
  const h = [];
  const GX = 240, GW = 1440;
  const panel = (y, hh, inner) =>
    `<div class="mt-gls-depth" style="${pos(GX, y, GW, hh)};display:flex;flex-direction:column;justify-content:center;padding:40px 80px">${inner}</div>`;
  // 光斑加大：从 620→760px，4 个角各一个，构图填充两侧空白
  const blobs = `<div class="bg-layer">
    <div class="mt-gls-blob" style="${pos(-60, 20, 760, 760)}"></div>
    <div class="mt-gls-blob" style="${pos(1220, 20, 760, 760)}"></div>
    <div class="mt-gls-blob" style="${pos(-60, 520, 760, 760)}"></div>
    <div class="mt-gls-blob" style="${pos(1220, 520, 760, 760)}"></div>
  </div>`;
  h.push(blobs);
  h.push(kicker());

  if (role === 'claim') {
    // 低密度：单块大玻璃居中，主张句 + KPI 三 chip 同尺寸 + creed
    h.push(panel(200, 660,
      `<div class="t-display" style="font-weight:400;line-height:1.05;color:var(--accent);text-align:center">${esc(D.claim)}</div>` +
      `<div class="t-body" style="margin-top:20px;text-align:center;line-height:1.7">${esc(D.claimNote)}</div>` +
      `<div style="margin-top:30px;display:flex;justify-content:center;gap:24px">${D.kpis.map((k, i) =>
        `<span class="mt-gls-chip" style="display:inline-flex;flex-direction:column;align-items:center;width:300px;padding:24px 20px">
          <span class="t-heading" style="font-weight:500">${esc(k.num)}</span>
          <span class="t-meta" style="margin-top:8px;text-align:center;line-height:1.35">${esc(k.cap)}</span>
        </span>`).join('')}</div>` +
      `<div style="margin-top:20px;text-align:center">${D.creed.map(c => `<span class="t-meta" style="display:inline-block;margin-right:24px">${esc(c)}</span>`).join('')}</div>`));
  } else if (role === 'full') {
    // 高密度：大玻璃居中，标题 + KPI chip 行 + 两段正文 + creed
    // rev6: KPI chip 和 caption 用同一 flex 容器等宽对齐（不再 chip 自适应 + caption 固定 320px）
    const p1Short = D.p1.slice(0, 80) + '……';
    const p2Short = D.p2.slice(0, 80) + '……';
    // KPI 行：chip + caption 一体化，每个 KPI 占 1/3 等宽
    const kpiRow = `<div style="margin-top:18px;display:flex;justify-content:center;gap:20px">${D.kpis.map((k, i) =>
      `<div style="flex:1;max-width:380px;text-align:center">
        <div class="mt-gls-chip-n" style="display:inline-flex;align-items:center;padding:.3em 1.2em">
          <span class="t-heading" style="font-weight:500">${esc(k.num)}</span>
        </div>
        <div class="t-meta" style="margin-top:8px;line-height:1.35">${esc(k.cap)}</div>
      </div>`).join('')}</div>`;
    h.push(panel(140, 820,
      `<div class="t-display" style="font-weight:400;white-space:nowrap;line-height:1.05;color:var(--accent);text-align:center">${ttl}</div>` +
      kpiRow +
      `<div class="t-body" style="margin-top:24px;line-height:1.7">${esc(p1Short)}</div>` +
      `<div class="t-body" style="margin-top:12px;line-height:1.7">${esc(p2Short)}</div>` +
      `<div style="margin-top:16px;text-align:center">${D.creed.map(c => `<span class="t-meta" style="display:inline-block;margin-right:22px">${esc(c)}</span>`).join('')}</div>`));
  }
  h.push(note(960));
  h.push(foot('f1', role));
  return h.join('\n');
}

/* ---------------- 组装 8 页 ---------------- */
const RENDER = { e6: E6, g2: G2, e7: E7, f1: F1 };
const IDS = ['e6', 'g2', 'e7', 'f1'];
const cases = [];
IDS.forEach(id => {
  cases.push({ id, role: 'claim' });
  cases.push({ id, role: 'full' });
});

const slides = cases.map(c => `<section class="slide ${c.id}" id="s-${c.id}-${c.role}" ` +
  `data-theme="${c.id}" data-role="${c.role}" style='${TOK[c.id]};font-family:var(--font-body)'>\n` +
  RENDER[c.id](c.role) + `\n</section>`);

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Phase6 Batch1 v2 · Step 4a rev6 · 标杆页</title>
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
  font-size:max(var(--t-meta),14px);line-height:1.4;letter-spacing:.04em;opacity:.6}
.e6 .t-display,.e6 .t-heading,.e6 .t-subhead{font-family:var(--font-display)}
.g2 .t-display,.g2 .t-heading{font-family:var(--font-display)}
.e7 .t-display,.e7 .t-heading,.e7 .t-subhead{font-family:var(--font-display)}
.f1 .t-display,.f1 .t-heading{font-family:var(--font-display)}
.e6 .mt-mem-block{z-index:2}
.g2 .mt-hl-note{z-index:2}
.e7 .mt-uki-plate{z-index:2}
.f1 .mt-gls-depth{z-index:2}
${ROLE_CSS}
${Object.values(MOTIF).join('\n')}
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">Phase 6 · 批次 1 v2 · Step 4a rev6 · 标杆页（claim + full）</div>
  <div class="sub">同一份「山禾集 1.1」内容 × 4 套新 G10 构图程序 × 8 页。<br>
  rev6：E6 标题按容器调字号不换行 + F1 KPI chip/caption flex 等宽对齐 + 审计加紧贴/等宽检测。<br>
  E6 几何拼贴 · G2 单栏流式+便签 · E7 日式不对称 · F1 中心聚焦单玻璃。</div>
${cases.map((c, i) => `  <div class="slot"><div class="cap"><span>${LABEL[c.id]} · ${c.role}</span><b>${String(i + 1).padStart(2, '0')} / 08</b></div>
  ${slides[i]}
  </div>`).join('\n')}
</div>
</body>
</html>`;

fs.writeFileSync(path.join(DIR, 'sampler.html'), html, 'utf8');
console.log('written sampler.html', Buffer.byteLength(html), 'bytes,', cases.length, 'pages');
