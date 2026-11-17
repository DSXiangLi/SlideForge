/* phase6-batch3 / build-sampler-g10.js
 * 用 G10 composition_program 重新构建 4 主题 theme-sampler
 * 使用原 sampler 的山禾集文字内容，但布局完全按 G10 契约
 * 选择 claim（主张页）作为展示页型——最能集中展示主题 DNA
 */
const fs = require('fs');
const path = require('path');

const DIR = __dirname;

// 读取骨架 CSS
const skeleton = fs.readFileSync(path.resolve(DIR, '../../..', 'skills/SlideForge/assets/skeleton.html'), 'utf8');
const styleStart = skeleton.indexOf('<style>');
const styleEnd = skeleton.indexOf('</style>');
const skeletonCSS = skeleton.substring(styleStart + 7, styleEnd);

// G9 motif CSS（4 主题）
const g9CSS = `
/* G4 靛墨黄页 · 装饰母题 */
.mt-bie-num{font-family:var(--font-mono);font-weight:700;line-height:1;color:transparent;-webkit-text-stroke:1.5px var(--ink);pointer-events:none}
.mt-bie-wedge{position:absolute;background:var(--accent);pointer-events:none}
.mt-bie-band{display:block;height:14px;background:linear-gradient(180deg,var(--accent) 50%,var(--ink) 50%)}

/* G5 三色旬刊 · 装饰母题 */
.mt-tri-band{display:block;height:12px;background:linear-gradient(90deg,var(--paper) 0 33.3%,var(--accent) 33.3% 66.6%,var(--ink) 66.6%)}
.mt-tri-tag{font-family:var(--font-mono);font-size:14px;letter-spacing:.18em;color:var(--ink);border:1.5px solid var(--ink);padding:.25em .8em;display:inline-block}
.mt-tri-frame{border:1.5px solid var(--ink);outline:1px solid var(--ink);outline-offset:5px}
.mt-tri-rule{display:flex;align-items:center;gap:16px}
.mt-tri-rule::before,.mt-tri-rule::after{content:"";flex:1;height:4px;background:var(--ink)}
.mt-tri-pill-sm{font-family:var(--font-mono);font-size:16px;letter-spacing:.14em;color:var(--ink);border:1.5px solid var(--ink);padding:.2em .6em;display:inline-block}

/* E2 蓝图 · 装饰母题 */
.mt-bp-frame{position:relative;border:1px solid color-mix(in srgb,var(--ink) 55%,transparent)}
.mt-bp-frame::before{content:"";position:absolute;inset:5px;border:1px solid color-mix(in srgb,var(--ink) 32%,transparent);pointer-events:none}
.mt-bp-tag{position:absolute;right:-1px;bottom:-1px;display:flex;font-family:var(--font-mono);font-size:14px;letter-spacing:.14em;color:color-mix(in srgb,var(--ink) 82%,transparent);border:1px solid color-mix(in srgb,var(--ink) 55%,transparent);background:var(--paper)}
.mt-bp-tag>span{padding:.35em .9em;border-left:1px solid color-mix(in srgb,var(--ink) 32%,transparent)}
.mt-bp-tag>span:first-child{border-left:none}
.mt-bp-dim{display:flex;align-items:center;gap:.8em;font-family:var(--font-mono);font-size:14px;letter-spacing:.12em;color:color-mix(in srgb,var(--ink) 75%,transparent)}
.mt-bp-dim i{flex:1;position:relative;height:1px;font-style:normal;background:color-mix(in srgb,var(--ink) 55%,transparent)}
.mt-bp-dim i::before,.mt-bp-dim i::after{content:"";position:absolute;top:-3px;width:0;height:0;border:3.5px solid transparent}
.mt-bp-dim i::before{left:0;border-right:6px solid color-mix(in srgb,var(--ink) 55%,transparent)}
.mt-bp-dim i::after{right:0;border-left:6px solid color-mix(in srgb,var(--ink) 55%,transparent)}

/* E3 装饰艺术 · 装饰母题 */
.mt-deco-sun{width:min(56vw,480px);height:calc(min(56vw,480px)/2);border-radius:999px 999px 0 0;overflow:hidden;pointer-events:none;background:repeating-conic-gradient(from -90deg at 50% 100%,color-mix(in srgb,var(--accent) 60%,transparent) 0deg 1.5deg,transparent 1.5deg 9deg)}
.mt-deco-frame{border:1px solid color-mix(in srgb,var(--accent) 70%,transparent);outline:1px solid color-mix(in srgb,var(--accent) 70%,transparent);outline-offset:5px}
.mt-deco-divider{display:flex;align-items:center;justify-content:center;gap:14px;pointer-events:none}
.mt-deco-divider::before,.mt-deco-divider::after{content:"";width:72px;height:1px;background:color-mix(in srgb,var(--accent) 65%,transparent)}
.mt-deco-rhombus{display:inline-block;width:8px;height:8px;background:var(--accent);transform:rotate(45deg)}
`;

// ===== 共享文字内容（山禾集） =====
const CONTENT = {
  eyebrow: '1.1 · 整体特色及优势',
  title: '一杯好茶  山野作答',
  body1: '山禾集深耕新式茶饮行业，同时通过全资子公司山禾供应链管理有限公司协同布局上游茶园直采业务。通过多年不懈努力，山禾集秉持"当季鲜茶，日常相伴"的经营理念，建立起从茶园到门店的全链路品控流程，持续为消费者创造价值，赢得了广大茶饮爱好者的喜爱。',
  body2: '近年来山禾集门店网络稳步扩张，行业排名持续提升。2019年，山禾集全国门店总数突破八千家，跻身行业头部梯队。截至2026年6月30日，山禾集全国门店总数8,637家（含直营门店1,653家，子公司山禾供应链合作门店432家），其中标准门店8,428家，位于行业前列；城市旗舰店总数361家。成立以来累计为超过6.8亿会员用户售出茶饮2.8亿杯。',
  kpi1Num: '8,637',
  kpi1Unit: '家',
  kpi1Label: '山禾集（含直营和子公司山禾供应链）全国门店总数',
  kpi1Tag: '行业前列',
  kpi2Num: '2.8',
  kpi2Unit: '亿杯',
  kpi2Label: '成立以来累计为超过6.8亿会员用户售出茶饮',
  kpi3Num: '361',
  kpi3Unit: '家',
  kpi3Label: '城市旗舰店总数',
  values: [
    '经营理念：当季鲜茶，日常相伴。',
    '使命：为大众提供新鲜、健康、平价的日常茶饮。',
    '愿景：成为持续领先的新式茶饮品牌。'
  ],
  footnote: '* 注：山禾集为虚构演示品牌，文中数据均为虚构，仅用于主题样式对比展示。'
};

// ===== G4 靛墨黄页 — G10: 海报式不对称出血，裂屏对开 =====
const slideG4 = `
  <!-- G4 靛墨黄页 · G10 海报式不对称出血：裂屏对开（黄/靛对撞）+ 出血黄楔 + 展览编号签 + 主数字独占黄面 -->
  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-g4" style="--paper:#E9E5DB;--paper-tint:#DDD8CB;--ink:#1B2566;--ink-tint:#2A3374;--accent:#F1EE2E;--accent-on:#1B2566;--accent-2:#E26B4A;--accent-2-on:#FAF1E2;--font-display:'Helvetica Neue','Arial Black','PingFang SC','Noto Sans SC',sans-serif;--font-body:'Helvetica Neue','PingFang SC','Noto Sans SC',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:flat;--texture-layer:none;--texture-scope:cover;padding:0">
      <!-- 出血黄楔（右上方出血块，G10 signature_operator） -->
      <div class="mt-bie-wedge" data-editable-skip style="right:0;top:0;width:420px;height:560px"></div>
      <!-- 展览编号签（G9，页角页码语义） -->
      <span class="mt-bie-num" data-editable style="position:absolute;right:48px;top:380px;font-size:120px">28</span>
      <!-- 底部对撞带 -->
      <span class="mt-bie-band" data-editable-skip style="position:absolute;left:0;right:0;bottom:0"></span>

      <!-- 左侧纸底靛墨区（辅助信息） -->
      <div style="position:absolute;left:0;top:0;width:1100px;height:100%;padding:80px 60px 80px 120px;display:flex;flex-direction:column;justify-content:center">
        <p data-editable style="font-family:var(--font-mono);font-size:16px;font-weight:600;letter-spacing:.14em;opacity:.7">${CONTENT.eyebrow}</p>
        <h1 data-editable data-anim="wipe-clip" style="margin-top:24px;font-family:var(--font-display);font-size:96px;line-height:1.1;font-weight:900;letter-spacing:.02em">${CONTENT.title}</h1>
        <div style="margin-top:28px;max-width:880px;border-left:3px solid var(--ink);padding-left:24px">
          <p data-editable style="font-size:18px;line-height:1.8">${CONTENT.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.8">${CONTENT.body2}</p>
        </div>
        <!-- 三项数字：靛蓝线框内纵向错落排列（非横排等宽三格），主数字用余烬橙单点 -->
        <div style="margin-top:32px;display:flex;gap:0;max-width:880px">
          <div style="flex:0 0 300px;border:1.5px solid var(--ink);padding:20px 24px">
            <p data-editable style="font-family:var(--font-mono);font-size:42px;font-weight:800;line-height:1.1;color:var(--accent-2)">${CONTENT.kpi1Num}<span style="font-size:22px">${CONTENT.kpi1Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:15px;line-height:1.5;opacity:.85">${CONTENT.kpi1Label}</p>
            <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:13px;font-weight:600;color:var(--accent-2)">${CONTENT.kpi1Tag}</p>
          </div>
          <div style="flex:0 0 240px;border:1.5px solid var(--ink);border-left:none;padding:20px 24px">
            <p data-editable style="font-family:var(--font-mono);font-size:36px;font-weight:800;line-height:1.1">${CONTENT.kpi2Num}<span style="font-size:18px">${CONTENT.kpi2Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:15px;line-height:1.5;opacity:.85">${CONTENT.kpi2Label}</p>
          </div>
          <div style="flex:0 0 200px;border:1.5px solid var(--ink);border-left:none;padding:20px 24px">
            <p data-editable style="font-family:var(--font-mono);font-size:36px;font-weight:800;line-height:1.1">${CONTENT.kpi3Num}<span style="font-size:18px">${CONTENT.kpi3Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:15px;line-height:1.5;opacity:.85">${CONTENT.kpi3Label}</p>
          </div>
        </div>
      </div>

      <!-- 右侧黄面区（核心信息——裂屏对开的黄面） -->
      <div style="position:absolute;right:0;top:0;width:820px;height:100%;background:var(--accent);color:var(--accent-on);padding:80px 60px 80px 60px;display:flex;flex-direction:column;justify-content:flex-end">
        <div style="margin-bottom:80px">
          <p data-editable style="font-family:var(--font-mono);font-size:14px;font-weight:600;letter-spacing:.14em;opacity:.7">CORE VALUES</p>
          <div style="margin-top:20px">
            ${CONTENT.values.map((v, i) => `<p data-editable style="${i > 0 ? 'margin-top:16px;' : ''}font-size:22px;line-height:1.5;font-weight:700">${v}</p>`).join('\n            ')}
          </div>
        </div>
      </div>

      <!-- 底部页码条 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.65">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>G4 · 靛墨黄页 · 太阳黄</span>
        <span data-editable>28 / 29</span>
      </div>
      <p data-editable style="position:absolute;left:120px;bottom:54px;font-family:var(--font-mono);font-size:13px;opacity:.5">${CONTENT.footnote}</p>
    </section>
  </div>`;

// ===== G5 三色旬刊 — G10: 三色反转配对面，刊号签 + 三色带 =====
const slideG5 = `
  <!-- G5 三色旬刊 · G10 三色反转配对面：刊号签页眉 + 双线刊框 + 三色反转面KPI（主数字独占暗夜蓝底）+ 三色带收束 -->
  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-g5" style="--paper:#E4C9A8;--paper-tint:#8BAE6F;--ink:#1A2B3D;--ink-tint:#121E2D;--accent:#8BAE6F;--accent-on:#1A2B3D;--font-display:'Didot','Bodoni MT','Songti SC','Noto Serif SC',serif;--font-body:'Songti SC','Noto Serif SC','STSong',serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:flat;--texture-layer:none;--texture-scope:cover">
      <!-- 三色带（页底收束，G9 signature） -->
      <span class="mt-tri-band" data-editable-skip style="position:absolute;left:0;right:0;bottom:0"></span>

      <!-- 刊号签（页眉，G9 signature） -->
      <div style="position:absolute;left:120px;top:64px"><span class="mt-tri-tag" data-editable>VOL.03 / NO.29</span></div>

      <div style="position:relative;height:100%;display:flex;flex-direction:column;justify-content:center;padding:120px 120px 80px">
        <p data-editable style="font-family:var(--font-mono);font-size:16px;font-weight:500;letter-spacing:.14em;opacity:.7">${CONTENT.eyebrow}</p>
        <h1 data-anim="mask-lines" style="margin-top:22px;font-family:var(--font-display);font-size:88px;line-height:1.25;font-weight:600"><span class="ml-line"><span class="ml-inner" data-editable>${CONTENT.title}</span></span></h1>

        <!-- 双线刊框装正文 -->
        <div class="mt-tri-frame" style="margin-top:28px;max-width:1360px;padding:28px 40px">
          <p data-editable style="font-size:18px;line-height:1.85">${CONTENT.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.85">${CONTENT.body2}</p>
        </div>

        <!-- 三色反转面 KPI（非横排等宽三格——三块色面宽度不等、底字互反） -->
        <div style="margin-top:28px;display:flex;max-width:1360px">
          <!-- 焦点：暗夜蓝底苔绿字（主数字独占暗夜蓝底面） -->
          <div style="width:520px;background:var(--ink);color:var(--accent);padding:28px 36px">
            <p data-editable style="font-family:var(--font-display);font-size:48px;font-weight:600;line-height:1.2">${CONTENT.kpi1Num}<span style="font-size:24px">${CONTENT.kpi1Unit}</span></p>
            <p data-editable style="margin-top:10px;font-size:18px;line-height:1.6;color:var(--paper)">${CONTENT.kpi1Label}</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-mono);font-size:14px;font-weight:600">${CONTENT.kpi1Tag}</p>
          </div>
          <!-- 苔绿底暗夜蓝字（反转配对） -->
          <div style="width:420px;background:var(--accent);color:var(--accent-on);padding:28px 36px">
            <p data-editable style="font-family:var(--font-display);font-size:42px;font-weight:600;line-height:1.2">${CONTENT.kpi2Num}<span style="font-size:20px">${CONTENT.kpi2Unit}</span></p>
            <p data-editable style="margin-top:10px;font-size:18px;line-height:1.6">${CONTENT.kpi2Label}</p>
          </div>
          <!-- 赭石底暗夜蓝字（第三色轮转） -->
          <div style="width:420px;background:var(--paper);color:var(--ink);padding:28px 36px;border:1.5px solid var(--ink)">
            <p data-editable style="font-family:var(--font-display);font-size:42px;font-weight:600;line-height:1.2">${CONTENT.kpi3Num}<span style="font-size:20px">${CONTENT.kpi3Unit}</span></p>
            <p data-editable style="margin-top:10px;font-size:18px;line-height:1.6">${CONTENT.kpi3Label}</p>
          </div>
        </div>

        <!-- 价值观（三色带分隔上方） -->
        <div style="margin-top:24px;max-width:1360px">
          ${CONTENT.values.map((v, i) => `<p data-editable style="${i > 0 ? 'margin-top:8px;' : ''}font-size:20px;line-height:1.75">${v}</p>`).join('\n          ')}
        </div>
        <p data-editable style="margin-top:14px;font-family:var(--font-mono);font-size:14px;opacity:.65">${CONTENT.footnote}</p>
      </div>

      <!-- 底部页码条 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.65">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>G5 · 三色旬刊 · 赭石</span>
        <span data-editable>29 / 29</span>
      </div>
    </section>
  </div>`;

// ===== E2 蓝图 — G10: 双线图框阵列，标注线，图框标题栏 =====
const slideE2 = `
  <!-- E2 蓝图 · G10 双线图框阵列：制图网格纸底 + 双线图框装信息 + 标注线指向数字 + 图框标题栏 -->
  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-e2" style="--paper:#14304a;--paper-tint:#1b3d5c;--ink:#f2f6f9;--ink-tint:#0f2438;--accent:#35C8E8;--accent-on:#0e2a3f;--font-display:'Helvetica Neue','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-body:'Helvetica Neue','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:paper;--texture-layer:repeating-linear-gradient(0deg,color-mix(in srgb,var(--ink) 5%,transparent) 0 1px,transparent 1px 7px),repeating-linear-gradient(90deg,color-mix(in srgb,var(--ink) 5%,transparent) 0 1px,transparent 1px 7px),repeating-linear-gradient(0deg,color-mix(in srgb,var(--ink) 12%,transparent) 0 1px,transparent 1px 35px),repeating-linear-gradient(90deg,color-mix(in srgb,var(--ink) 12%,transparent) 0 1px,transparent 1px 35px);--texture-scope:all">
      <!-- 整页双线图框内框 -->
      <div class="mt-bp-frame" data-editable-skip style="position:absolute;inset:48px 60px"></div>
      <!-- 图框标题栏（右下角，G9 signature） -->
      <div class="mt-bp-tag" data-editable-skip style="position:absolute;right:59px;bottom:59px">
        <span>FIG. 1-1</span><span>SCALE 1:1</span><span>2026.06</span>
      </div>

      <div style="position:relative;height:100%;display:flex;flex-direction:column;justify-content:center;padding:96px 120px">
        <p data-editable style="font-family:var(--font-mono);font-size:15px;letter-spacing:.3em;color:var(--accent)">${CONTENT.eyebrow}</p>
        <h1 data-editable data-anim="wipe-clip" style="margin-top:22px;font-size:88px;line-height:1.25;font-weight:600;letter-spacing:.04em">${CONTENT.title}</h1>

        <!-- 双线图框装正文（图框成阵即分区） -->
        <div class="mt-bp-frame" style="margin-top:24px;max-width:1300px;padding:24px 36px">
          <p data-editable style="font-size:18px;line-height:1.8;opacity:.88">${CONTENT.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.8;opacity:.88">${CONTENT.body2}</p>
        </div>

        <!-- 三项数字：图框内 mono key:value 标注行（非横排等宽三格） -->
        <div style="margin-top:24px;display:flex;gap:0;max-width:1300px">
          <!-- 主数字图框（亮青标注线强调） -->
          <div class="mt-bp-frame" style="flex:0 0 480px;padding:24px 32px">
            <div class="mt-bp-dim" data-editable-skip style="margin-bottom:12px"><i></i><span style="color:var(--accent)">KEY METRIC</span><i></i></div>
            <p data-editable style="font-family:var(--font-mono);font-size:48px;font-weight:600;line-height:1.15;color:var(--accent)">${CONTENT.kpi1Num}<span style="font-size:22px">${CONTENT.kpi1Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.8">${CONTENT.kpi1Label}</p>
            <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:14px;color:var(--accent)">${CONTENT.kpi1Tag}</p>
          </div>
          <!-- 辅助数字图框 1 -->
          <div class="mt-bp-frame" style="flex:0 0 380px;margin-left:-1px;padding:24px 32px">
            <p data-editable style="font-family:var(--font-mono);font-size:14px;letter-spacing:.12em;opacity:.6">SPEC.02</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-mono);font-size:40px;font-weight:600;line-height:1.15">${CONTENT.kpi2Num}<span style="font-size:18px">${CONTENT.kpi2Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.8">${CONTENT.kpi2Label}</p>
          </div>
          <!-- 辅助数字图框 2 -->
          <div class="mt-bp-frame" style="flex:0 0 320px;margin-left:-1px;padding:24px 32px">
            <p data-editable style="font-family:var(--font-mono);font-size:14px;letter-spacing:.12em;opacity:.6">SPEC.03</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-mono);font-size:40px;font-weight:600;line-height:1.15">${CONTENT.kpi3Num}<span style="font-size:18px">${CONTENT.kpi3Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.8">${CONTENT.kpi3Label}</p>
          </div>
        </div>

        <!-- 标注线（尺寸标注，G9 signature） -->
        <div class="mt-bp-dim reveal" data-editable-skip style="margin-top:18px;max-width:1300px"><i></i><span data-editable style="font-size:14px">单位：亿元人民币 · 截至 2026.6.3</span><i></i></div>

        <!-- 价值观 -->
        <div style="margin-top:20px;max-width:1300px">
          ${CONTENT.values.map((v, i) => `<p data-editable style="${i > 0 ? 'margin-top:8px;' : ''}border-top:1px solid color-mix(in srgb,var(--ink) 45%,transparent);padding:8px 0;font-size:19px">${v}</p>`).join('\n          ')}
        </div>
        <p data-editable style="margin-top:14px;font-family:var(--font-mono);font-size:14px;opacity:.55">${CONTENT.footnote}</p>
      </div>

      <!-- 底部页码条 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.7">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E2 · 蓝图 · 经典蓝图</span>
        <span data-editable>11 / 29</span>
      </div>
    </section>
  </div>`;

// ===== E3 装饰艺术 — G10: 中轴对称，双线金框，菱形分隔，对称双栏 =====
const slideE3 = `
  <!-- E3 装饰艺术 · G10 中轴对称：扇形放射 + 双线金框整页内框 + 中轴标题 + 菱形分隔 + 对称双栏数字 -->
  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-e3" style="--paper:#111110;--paper-tint:#1b1b18;--ink:#f0e9d6;--ink-tint:#0a0a09;--accent:#c9a227;--accent-on:#111110;--font-display:'Songti SC','Noto Serif SC','STSong',serif;--font-body:'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:flat;--texture-layer:none;--texture-scope:cover">
      <!-- 扇形放射 sunburst（页顶，G9 signature） -->
      <div class="mt-deco-sun" data-editable-skip style="position:absolute;left:50%;top:0;transform:translateX(-50%)"></div>
      <!-- 双线金框整页内框 -->
      <div class="mt-deco-frame" data-editable-skip style="position:absolute;inset:56px 72px;pointer-events:none"></div>

      <div style="position:relative;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:96px 120px">
        <p data-editable style="font-family:var(--font-mono);font-size:15px;font-weight:500;letter-spacing:.34em;color:var(--accent)">${CONTENT.eyebrow}</p>
        <!-- 菱形分隔 -->
        <div class="mt-deco-divider" data-editable-skip style="margin-top:20px"><span class="mt-deco-rhombus"></span></div>

        <h1 data-anim="mask-lines" style="margin-top:20px;font-family:var(--font-display);font-size:84px;line-height:1.3;font-weight:600;letter-spacing:.06em"><span class="ml-line"><span class="ml-inner" data-editable>${CONTENT.title}</span></span></h1>

        <div style="margin-top:22px;max-width:1100px">
          <p data-editable style="font-size:18px;line-height:1.85;opacity:.85">${CONTENT.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.85;opacity:.85">${CONTENT.body2}</p>
        </div>

        <!-- 三项数字：对称双栏镜像模块（主数字在中轴金框内） -->
        <div style="margin-top:28px;display:flex;justify-content:center;align-items:stretch">
          <!-- 左栏 -->
          <div style="padding:0 40px;text-align:center">
            <p data-editable style="font-family:var(--font-display);font-size:46px;font-weight:600;line-height:1.15">${CONTENT.kpi2Num}<span style="font-size:20px">${CONTENT.kpi2Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.75;max-width:300px">${CONTENT.kpi2Label}</p>
          </div>
          <!-- 中轴金框（主数字） -->
          <div class="mt-deco-frame" style="padding:20px 48px;text-align:center">
            <p data-editable style="font-family:var(--font-display);font-size:52px;font-weight:600;line-height:1.15;color:var(--accent)">${CONTENT.kpi1Num}<span style="font-size:22px">${CONTENT.kpi1Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.75;max-width:320px">${CONTENT.kpi1Label}</p>
            <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:13px;color:var(--accent)">${CONTENT.kpi1Tag}</p>
          </div>
          <!-- 右栏 -->
          <div style="padding:0 40px;text-align:center">
            <p data-editable style="font-family:var(--font-display);font-size:46px;font-weight:600;line-height:1.15">${CONTENT.kpi3Num}<span style="font-size:20px">${CONTENT.kpi3Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.75;max-width:300px">${CONTENT.kpi3Label}</p>
          </div>
        </div>

        <!-- 菱形分隔 -->
        <div class="mt-deco-divider" data-editable-skip style="margin-top:24px"><span class="mt-deco-rhombus"></span></div>

        <!-- 价值观 -->
        <div style="margin-top:18px">
          ${CONTENT.values.map((v, i) => `<p data-editable style="${i > 0 ? 'margin-top:6px;' : ''}font-size:19px;line-height:1.8">${v}</p>`).join('\n          ')}
        </div>
        <p data-editable style="margin-top:14px;font-family:var(--font-mono);font-size:14px;opacity:.5">${CONTENT.footnote}</p>
      </div>

      <!-- 底部页码条 -->
      <div style="position:absolute;left:160px;right:160px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.65">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E3 · 装饰艺术 · 墨黑金</span>
        <span data-editable>12 / 29</span>
      </div>
    </section>
  </div>`;

// ===== 组装 HTML =====
const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920">
<title>Theme Sampler G10 · E2 / E3 / G4 / G5</title>
<style>
${skeletonCSS}

${g9CSS}

/* sampler 页面基础 */
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:#222;font-family:sans-serif}
.deck{display:flex;flex-direction:column;align-items:center;padding:24px 0}
.slide-slot{width:1920px;height:1080px;margin:12px 0;position:relative}
.slide{width:1920px;height:1080px;position:relative;overflow:hidden;transform:none;background:var(--paper);color:var(--ink);padding:96px 120px}
/* 确保不缩放——sampler 直接 1:1 渲染 */
.slide-slot{width:1920px;height:1080px;overflow:hidden}
/* 动效终态——截静态图 */
.reveal{opacity:1!important;transform:none!important}
[data-anim="wipe-clip"]{clip-path:inset(0 0 0 0)!important}
[data-anim="mask-lines"] .ml-inner{transform:none!important}
</style>
</head>
<body>
<div class="deck" id="deck">
${slideE2}
${slideE3}
${slideG4}
${slideG5}
</div>
<script>(function(){document.documentElement.classList.add("js");document.querySelectorAll(".slide").forEach(function(s){s.classList.add("in-view")});})();</script>
</body>
</html>`;

fs.writeFileSync(path.join(DIR, 'theme-sampler-4.html'), html);
console.log('Generated theme-sampler-4.html (' + html.length + ' chars)');
