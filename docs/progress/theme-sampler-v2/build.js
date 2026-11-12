/* theme-sampler-v2 / build.js  (rev2)
 * 用与 tests/decks/theme-sampler/index.html 完全相同的「一杯好茶」内容对象，
 * 经 4 套已升级主题（B1/C3/E5/H1）各自的 G10 composition_program 重新编译，
 * 产出 4 页 sampler.html。
 *
 * 要点：
 *  - 唯一内容对象 D，四个渲染函数只消费 D，不改写文字（H1 按契约追加汉数题跋，
 *    阿拉伯数字以括注保留，信息集完全一致；其余主题数字原样）。
 *  - 字号只用骨架 v7.6 的 .t-* 角色类，不裸写 font-size；各主题通过 :root
 *    覆盖 --t-* 令牌（与 theme.md G9 css 块逐字一致）。
 *  - G9 母题 CSS 逐字复制自各主题 theme.md；静态渲染，无任何入场动效。
 *  - rev2 修复：禁灰化弱读（正文不降 opacity）；C3 去标题辉光烧死 + KPI 窗口
 *    内溢出，doctrine 改无框 stdout 行；E5 正文避开楔形块与 −12° 力带；
 *    H1 汉数题跋与括注分行，避免拆字。
 */
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, 'sampler.html');

/* ---------------- 单一内容对象（逐字取自原 sampler B1 页） ---------------- */
const D = {
  kicker: '1.1 · 整体特色及优势',
  title: '一杯好茶  山野作答',
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
  note: '* 注：山禾集为虚构演示品牌，文中数据均为虚构，仅用于主题样式对比展示。',
  footL: '山禾集 · 经营情况汇报',
  footTheme: {
    B1: 'B1 · 瑞士国际主义 · 克莱因蓝',
    C3: 'C3 · 终端绿 · 磷光绿',
    E5: 'E5 · 构成主义 · 朱红',
    H1: 'H1 · 氤氲手卷 · 朱砂'
  }
};

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/* ---------------- 骨架 v7.6 角色类（逐字复用） ---------------- */
const ROLE_CSS = `
:root{
  --t-display:96px; --t-heading:64px; --t-subhead:40px; --t-body:28px;
  --t-caption:18px; --t-meta:15px; --t-vertical:96px;
}
.t-display{font-size:max(var(--t-display),64px);line-height:1.15}
.t-heading{font-size:max(var(--t-heading),32px);line-height:1.25}
.t-subhead{font-size:max(var(--t-subhead),24px);line-height:1.3}
.t-body{font-size:max(var(--t-body),18px);line-height:1.6}
.t-caption{font-size:max(var(--t-caption),16px);line-height:1.5}
.t-meta{font-size:max(var(--t-meta),14px);line-height:1.4}
.t-vertical{font-size:max(var(--t-vertical),64px);line-height:1.12;writing-mode:vertical-rl}
`;

/* ---------------- 各主题 G9 母题 CSS（逐字复制 theme.md） ---------------- */
const MOTIF = {
  B1: `
.mt-cross{position:absolute;width:14px;height:14px;pointer-events:none;opacity:.55}
.mt-cross::before,.mt-cross::after{content:"";position:absolute;background:var(--ink)}
.mt-cross::before{left:50%;top:0;bottom:0;width:1px;margin-left:-.5px}
.mt-cross::after{top:50%;left:0;right:0;height:1px;margin-top:-.5px}
.mt-swatch{display:inline-flex;align-items:center;justify-content:center;min-width:2.2em;height:2.2em;background:var(--accent);color:var(--accent-on);font-family:var(--font-mono);font-weight:600}`,
  C3: `
.mt-term-box{position:relative;border:1px solid color-mix(in srgb,var(--accent) 45%,transparent);box-shadow:0 0 28px -2px color-mix(in srgb,var(--accent) 45%,transparent),inset 0 0 16px color-mix(in srgb,var(--accent) 10%,transparent)}
.mt-term-box::before{content:"+";position:absolute;top:-.6em;left:-.35em;color:var(--accent);font-family:var(--font-mono);line-height:1}
.mt-term-box::after{content:"+";position:absolute;bottom:-.6em;right:-.35em;color:var(--accent);font-family:var(--font-mono);line-height:1}
.mt-term-caret{display:inline-block;width:.55em;height:1em;margin-left:.08em;background:var(--accent);vertical-align:-.12em;box-shadow:0 0 12px color-mix(in srgb,var(--accent) 85%,transparent)}
.mt-term-glow{text-shadow:0 0 16px color-mix(in srgb,var(--accent) 75%,transparent),0 0 42px color-mix(in srgb,var(--accent) 35%,transparent)}
.mt-term-prompt::before{content:"$ ";color:var(--accent);font-weight:600}`,
  E5: `
.mt-con-diag{position:absolute;left:-15%;width:130%;height:14vh;pointer-events:none;transform:rotate(-12deg);background:var(--accent)}
.mt-con-diag--print{box-shadow:0 10px 0 color-mix(in srgb,var(--ink) 25%,transparent)}
.mt-con-wedge{position:absolute;pointer-events:none;width:38vmin;height:38vmin;background:var(--accent);clip-path:polygon(0 0,100% 0,0 100%)}
.mt-con-wedge--ink{background:var(--ink)}
.mt-con-bar{display:inline-block;width:1.6em;height:.28em;background:var(--ink)}
.mt-con-bar--accent{background:var(--accent)}`,
  H1: `
.mt-scroll-rod{position:absolute;left:0;right:0;height:20px;background:linear-gradient(90deg,var(--hl-1),color-mix(in srgb,var(--hl-1) 45%,var(--paper)),var(--hl-1));box-shadow:0 8px 22px -8px color-mix(in srgb,var(--ink) 45%,transparent)}
.mt-scroll-seal{display:flex;align-items:center;justify-content:center;border:2px solid var(--accent);border-radius:8px;color:var(--accent);font-family:"Ma Shan Zheng","STKaiti","KaiTi",cursive;transform:rotate(-6deg);background:color-mix(in srgb,var(--accent) 5%,transparent)}
.mt-scroll-mist{position:absolute;border-radius:50%;filter:blur(60px);pointer-events:none}`
};

/* ---------------- 主题 token（G1 色板 + G9 :root 覆盖 + G2 字体栈） ---------------- */
const TOKENS = {
  B1: `--paper:#fafaf8;--paper-tint:#f0f0ee;--ink:#0a0a0a;--ink-tint:#1a1a1a;--accent:#002FA7;--accent-on:#ffffff;--ease-out:cubic-bezier(.2,.9,.25,1);--t-display:176px;--t-body:35px;--font-display:"Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace`,
  C3: `--paper:#0d1117;--paper-tint:#161b22;--ink:#e6edf3;--ink-tint:#1c2128;--accent:#39d353;--accent-on:#0d1117;--t-display:104px;--t-body:35px;--font-display:"SF Mono","JetBrains Mono","Menlo",monospace;--font-body:"SF Mono","JetBrains Mono","Menlo",monospace;--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace`,
  E5: `--paper:#eadfc4;--paper-tint:#ddd0b0;--ink:#171310;--ink-tint:#2b241a;--accent:#9E1B1E;--accent-on:#eadfc4;--ease-out:cubic-bezier(.8,0,.2,1);--t-display:128px;--t-body:35px;--font-display:"Arial Black","PingFang SC","Noto Sans SC",sans-serif;--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace`,
  H1: `--paper:#faf7f3;--paper-tint:#e8e0e7;--ink:#241f2b;--ink-tint:#544b60;--accent:#9c3b34;--accent-on:#faf7f3;--accent-2:#8d7aa8;--accent-3:#6f84a6;--hl-1:#c9a86a;--ease-out:cubic-bezier(.2,.7,.3,1);--t-display:92px;--t-body:35px;--t-vertical:118px;--font-display:"Songti SC","Noto Serif SC","STSong",serif;--font-body:"Songti SC","Noto Serif SC","STSong",serif;--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace`
};

function mastfoot(k) {
  return `<div class="mastfoot"><span>${esc(D.footL)}</span><span>${esc(D.footTheme[k])}</span><span>01 / 04</span></div>`;
}
function note(top, extra) {
  return `<div class="t-meta note" style="top:${top}px;${extra || ''}">${esc(D.note)}</div>`;
}

/* =================== B1 瑞士国际主义 ===================
 * 12 栏网格（栏界 hairline 可见）+ 标题跨栏语义断行倒挂字重；
 * 横向等权 KPI 重排成右侧纵向数据脊，只给一个数字一次 accent 面积事件。
 * rev2: 正文去除 opacity 灰化（theme.md G10 rule 禁「灰化弱读」）。
 */
function B1() {
  let grid = '';
  for (let i = 1; i < 12; i++) {
    grid += `<div style="position:absolute;left:${i * 160}px;top:0;bottom:0;width:1px;background:color-mix(in srgb,var(--ink) 10%,transparent)"></div>`;
  }
  const crosses = [[120, 96], [1800, 96], [120, 984], [1800, 984]]
    .map(([x, y]) => `<span class="mt-cross" style="left:${x}px;top:${y}px"></span>`).join('');
  const spine = D.kpis.map((k, i) => {
    const acc = i === 0
      ? `background:var(--accent);color:var(--accent-on);padding:22px 26px;margin-left:-26px`
      : `color:var(--ink)`;
    return `<div style="margin-bottom:40px">
      <div class="t-heading" style="${acc};font-weight:200;letter-spacing:-.02em">${esc(k.num)}</div>
      <div class="t-caption" style="margin-top:12px;max-width:560px">${esc(k.cap)}</div>
      ${k.tag ? `<div class="t-meta" style="opacity:.6;margin-top:8px;font-family:var(--font-mono);font-weight:600">${esc(k.tag)}</div>` : ''}
    </div>`;
  }).join('');
  const creed = D.creed.map(c => `<div class="t-caption" style="border-top:1px solid color-mix(in srgb,var(--ink) 18%,transparent);padding:11px 0">${esc(c)}</div>`).join('');
  return `
  <div class="bg-layer">${grid}${crosses}</div>
  <div class="kicker" style="left:120px;top:128px;display:flex;align-items:center;gap:20px">
    <span class="mt-swatch t-meta">1.1</span>
    <span class="t-meta" style="font-family:var(--font-mono);letter-spacing:.12em;opacity:.6">${esc(D.kicker)}</span>
  </div>
  <h1 class="t-display" style="position:absolute;left:120px;top:186px;font-weight:200;letter-spacing:-.03em;white-space:pre-line">一杯好茶
山野作答</h1>
  <div style="position:absolute;left:120px;top:612px;width:1010px">
    <p class="t-caption" style="line-height:1.7">${esc(D.p1)}</p>
    <p class="t-caption" style="line-height:1.7;margin-top:12px">${esc(D.p2)}</p>
  </div>
  <div style="position:absolute;left:120px;top:800px;width:1010px">${creed}</div>
  <div style="position:absolute;left:1160px;top:186px;width:640px;border-left:1px solid color-mix(in srgb,var(--ink) 26%,transparent);padding-left:44px">${spine}</div>
  ${note(944)}
  ${mastfoot('B1')}`;
}

/* =================== C3 终端绿 ===================
 * 单向时间流：同构描边窗口 / stdout 行；标题重构成命令行，数字重构成 key:value。
 * rev2: 标题与数字去掉 mt-term-glow（辉光烧死字形违反 G9 禁忌）；
 *       重排窗口高度，KPI 不再溢出；doctrine 改为无框 stdout 行（契约允许）。
 */
function C3() {
  const win = (t, top, h, body) => `<div class="mt-term-box" style="position:absolute;left:120px;top:${top}px;width:1680px;height:${h}px">
    <div class="t-meta" style="position:absolute;left:0;top:0;right:0;height:40px;background:color-mix(in srgb,var(--accent) 13%,transparent);border-bottom:1px solid color-mix(in srgb,var(--accent) 30%,transparent);color:var(--accent);padding:0 22px;display:flex;align-items:center;letter-spacing:.08em">${esc(t)}</div>
    <div style="position:absolute;left:26px;right:26px;top:58px;bottom:16px">${body}</div>
  </div>`;
  const kv = D.kpis.map(k => `<div style="display:flex;align-items:baseline;gap:26px;margin-bottom:8px">
      <span class="t-subhead" style="color:var(--accent);min-width:270px;font-weight:600">${esc(k.num)}</span>
      <span class="t-caption">${esc(k.cap)}</span>${k.tag ? `<span class="t-meta" style="color:var(--accent)">[${esc(k.tag)}]</span>` : ''}
    </div>`).join('');
  const creed = D.creed.map(c => `<div class="t-caption mt-term-prompt" style="margin-bottom:10px">${esc(c)}</div>`).join('');
  const scan = `<div style="position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,color-mix(in srgb,var(--ink) 4%,transparent) 0 1px,transparent 1px 5px)"></div>`;
  return `
  ${scan}
  <div class="t-meta" style="position:absolute;left:120px;top:88px;color:var(--accent);letter-spacing:.16em">SESSION 01 · ${esc(D.footL)}</div>
  <div style="position:absolute;left:120px;top:126px">
    <div class="t-caption mt-term-prompt" style="color:var(--accent)">state --overview --brand=shanheji</div>
    <h1 class="t-display" style="font-weight:600;letter-spacing:-.02em;color:var(--ink);margin-top:10px">${esc(D.title)}<span class="mt-term-caret"></span></h1>
  </div>
  ${win('overview.log · stdout', 290, 226, `<p class="t-caption" style="line-height:1.7">${esc(D.p1)}</p><p class="t-caption" style="line-height:1.7;margin-top:12px">${esc(D.p2)}</p>`)}
  ${win('metrics · key:value', 532, 262, kv)}
  <div style="position:absolute;left:120px;top:810px;width:1680px">${creed}</div>
  ${note(944, 'color:var(--ink);opacity:.45')}
  ${mastfoot('C3')}`;
}

/* =================== E5 构成主义 ===================
 * −12° 力线劈开版面，标题装进带内反白；其余文字沿力线对抗/阶梯错排；
 * 楔形块从页缘楔入。
 * rev2: 依据力带旋转几何重排文字区——p1 置右上（楔形块外），p2 与 creed
 *       置左下（力带左端之外），KPI 置右下（力带右端之下），互不遮挡。
 */
function E5() {
  const creed = D.creed.map((c, i) => `<div class="t-caption" style="font-weight:700;margin-left:${i * 26}px;margin-bottom:6px"><span class="mt-con-bar mt-con-bar--accent" style="margin-right:12px;vertical-align:middle"></span>${esc(c)}</div>`).join('');
  const kpis = D.kpis.map((k, i) => `<div style="margin-bottom:14px;margin-left:${i * 22}px">
      <div class="t-subhead" style="font-weight:900;letter-spacing:-.02em;color:${i === 0 ? 'var(--accent)' : 'var(--ink)'}">${esc(k.num)}</div>
      <div class="t-meta" style="margin-top:4px;max-width:520px;font-weight:700">${esc(k.cap)}</div>
    </div>`).join('');
  return `
  <div class="mt-con-wedge" style="left:-40px;top:-40px;opacity:.92"></div>
  <div class="mt-con-wedge mt-con-wedge--ink" style="right:-30px;bottom:-30px;transform:rotate(180deg);opacity:.10"></div>
  <div class="t-meta" style="position:absolute;left:400px;top:92px;font-weight:900;letter-spacing:.18em;opacity:.7">${esc(D.kicker)}</div>
  <p class="t-caption" style="position:absolute;left:400px;top:132px;width:620px;font-weight:700;line-height:1.65">${esc(D.p1)}</p>
  <div class="mt-con-diag mt-con-diag--print" style="top:300px;height:230px"></div>
  <div style="position:absolute;left:-80px;top:300px;width:2100px;height:230px;transform:rotate(-12deg);display:flex;align-items:center;padding-left:430px">
    <h1 class="t-display" style="font-weight:900;color:var(--paper);letter-spacing:-.02em;white-space:nowrap">${esc(D.title)}</h1>
  </div>
  <p class="t-caption" style="position:absolute;left:150px;top:730px;width:820px;font-weight:700;line-height:1.65">${esc(D.p2)}</p>
  <div style="position:absolute;left:150px;top:856px">${creed}</div>
  <div style="position:absolute;left:1090px;top:600px;width:680px">${kpis}</div>
  ${note(966)}
  ${mastfoot('E5')}`;
}

/* =================== H1 氤氲手卷 ===================
 * 自右向左展开，上下金轴定界，标题竖排居右，其余按题跋层级分列向左递推；
 * 数字改写成汉数题跋，朱印是全篇唯一句读。
 * rev2: 汉数与括注分行避免拆字；题跋二列加宽；正文去灰化。
 */
function H1() {
  const cn = [
    { cn: '八千六百三十七家', ar: '（8,637家）' },
    { cn: '二亿八千万杯', ar: '（2.8亿杯）' },
    { cn: '三百六十一家', ar: '（361家）' }
  ];
  const nums = cn.map((s, i) => `<div style="margin-bottom:20px">
      <div class="t-subhead" style="font-family:'STKaiti','KaiTi',serif;color:var(--accent);font-weight:700;white-space:nowrap">${esc(s.cn)}</div>
      <div class="t-meta" style="color:var(--ink);opacity:.7;margin-top:2px">${esc(s.ar)}</div>
      <div class="t-meta" style="opacity:.68;margin-top:6px">${esc(D.kpis[i].cap)}</div>
    </div>`).join('');
  const creed = D.creed.map(c => `<div class="t-caption" style="line-height:1.7;margin-bottom:8px">${esc(c)}</div>`).join('');
  return `
  <div class="mt-scroll-rod" style="top:0"></div><div class="mt-scroll-rod" style="bottom:0"></div>
  <div class="mt-scroll-mist" style="left:120px;top:120px;width:520px;height:520px;background:color-mix(in srgb,var(--accent-2) 22%,transparent)"></div>
  <div class="mt-scroll-mist" style="right:220px;bottom:100px;width:460px;height:460px;background:color-mix(in srgb,var(--accent-3) 20%,transparent)"></div>
  <h1 class="t-vertical" style="position:absolute;right:120px;top:110px;height:820px;font-weight:700;letter-spacing:.06em;color:var(--ink)">一杯好茶</h1>
  <div class="t-vertical" style="position:absolute;right:270px;top:150px;height:660px;font-size:max(var(--t-subhead),24px);font-weight:400;letter-spacing:.2em;color:var(--ink-tint)">山野作答</div>
  <div class="t-meta" style="position:absolute;right:400px;top:110px;writing-mode:vertical-rl;letter-spacing:.2em;color:var(--accent)">${esc(D.kicker)}</div>
  <div style="position:absolute;left:150px;top:150px;width:340px;height:720px;border-right:1px solid color-mix(in srgb,var(--ink) 16%,transparent);padding-right:34px">
    <div class="t-meta" style="color:var(--accent-2);letter-spacing:.16em;margin-bottom:22px">题跋 · 一</div>
    <p class="t-caption" style="line-height:1.9">${esc(D.p1)}</p>
    <p class="t-caption" style="line-height:1.9;margin-top:18px">${esc(D.p2)}</p>
  </div>
  <div style="position:absolute;left:540px;top:150px;width:390px;height:720px;border-right:1px solid color-mix(in srgb,var(--ink) 16%,transparent);padding-right:34px">
    <div class="t-meta" style="color:var(--accent-2);letter-spacing:.16em;margin-bottom:22px">题跋 · 二 · 数目</div>
    ${nums}
    <div style="margin-top:24px;border-top:1px solid color-mix(in srgb,var(--ink) 18%,transparent);padding-top:18px">${creed}</div>
  </div>
  <div class="mt-scroll-seal t-heading" style="position:absolute;left:1000px;top:800px;width:104px;height:104px">茶</div>
  <div class="t-meta" style="position:absolute;left:150px;top:946px;opacity:.5">${esc(D.note)}</div>
  ${mastfoot('H1')}`;
}

/* ---------------- 组装 ---------------- */
const RENDER = { B1, C3, E5, H1 };
const LABEL = { B1: 'B1 · 瑞士国际主义', C3: 'C3 · 终端绿', E5: 'E5 · 构成主义', H1: 'H1 · 氤氲手卷' };
const ORDER = ['B1', 'C3', 'E5', 'H1'];

const slides = {};
ORDER.forEach((k) => {
  slides[k] = `<section class="slide ${k.toLowerCase()}" id="s-${k.toLowerCase()}" data-theme="${k}" style="${TOKENS[k]};font-family:var(--font-body)">
${RENDER[k]()}
</section>`;
});

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Theme Sampler v2 · 同一内容 × 4 套升级主题</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:#15181e;font-family:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif}
.wrap{padding:30px 0 80px}
.hd{color:#e8ebf0;text-align:center;margin-bottom:8px;font-size:22px;font-weight:600}
.sub{color:#8b93a3;text-align:center;margin-bottom:28px;font-size:13px;line-height:1.7}
.slot{margin:0 auto 26px;display:flex;flex-direction:column;align-items:center}
.cap{width:1920px;color:#9aa3b4;font-size:14px;letter-spacing:.06em;margin-bottom:8px;display:flex;justify-content:space-between}
.cap b{color:#dbe0ea;font-weight:600}
.slide{
  width:1920px;height:1080px;position:relative;overflow:hidden;flex:none;
  background:var(--paper);color:var(--ink);
  -webkit-font-smoothing:antialiased;
}
.slide .bg-layer{position:absolute;inset:0;pointer-events:none}
.slide .kicker{position:absolute}
.slide .note{position:absolute;left:120px;opacity:.5}
.slide .mastfoot{
  position:absolute;left:120px;right:120px;bottom:44px;
  display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid color-mix(in srgb,var(--ink) 22%,transparent);
  padding-top:14px;font-family:var(--font-mono);
  font-size:max(var(--t-meta),14px);line-height:1.4;opacity:.6;letter-spacing:.04em;
}
.b1 h1,.b1 .t-display{font-family:var(--font-display)}
.slide.c3 .t-caption,.slide.c3 .t-meta,.slide.c3 .mastfoot{font-family:var(--font-mono)}
.mt-con-diag{height:230px}
${ROLE_CSS}
${Object.values(MOTIF).join('\n')}
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">Theme Sampler v2 · 同一份「一杯好茶」内容 × 4 套升级主题</div>
  <div class="sub">内容对象逐字取自 tests/decks/theme-sampler/index.html（山禾集 · 1.1 整体特色及优势）。<br>
  每页由该主题 G10 composition_program 的 signature_operator 重新编译：结构改变，不只是换色。字号仅用骨架 v7.6 的 .t-* 角色类。</div>
${ORDER.map(k => `  <div class="slot"><div class="cap"><span>${LABEL[k]}</span><b>同一内容 · G10 重编译</b></div>
  ${slides[k]}
  </div>`).join('\n')}
</div>
</body>
</html>`;

fs.writeFileSync(OUT, html, 'utf8');
console.log('written', OUT, Buffer.byteLength(html), 'bytes');
