/* phase6-batch4-5 / build-sampler.js
 * 4 套主题 theme-sampler 构建——保留原版骨架框架层 + 山禾集内容 + G10 契约布局
 *
 * G10 契约摘要（claim 页型）：
 * D4 黄铜年代: 刻线框阵承载主张句（框内 condensed 大字 + mono 编号 kicker），红色标注章从框角引出批注，铆钉钉框角
 * E9 地质地层: 剖面切片阵承载主张句（切片内 sans 大字 + 年代标注签引线注），层理色带在页底做层序呼应
 * E8 号外报纸: 超粗黑标题压顶 + 粗细双线分区 + 多栏衬线正文承载主张，斜切引文块做观点提炼
 * E11 票据: 票据容器承载主张句（mono 字段行 LABEL/VALUE 排列），齿孔撕线分主券/副券，副券做摘要存根
 *
 * 所有主题 forbidden_defaults 均含: 横向等权三格 KPI
 * 所有主题 invariants 均含: 横排等权三格容器数 = 0
 */
const fs = require('fs');
const path = require('path');

const DIR = __dirname;

// ===== 1. 提取 gallery 的 <style> 块（含完整骨架框架 CSS + G9 装饰母题） =====
const galleryPath = path.resolve(DIR, '../../..', 'skills/SlideForge/gallery/index.html');
const galleryHTML = fs.readFileSync(galleryPath, 'utf8');
const gStyleStart = galleryHTML.indexOf('<style>');
const gStyleEnd = galleryHTML.indexOf('</style>');
let galleryStyleBlock = galleryHTML.substring(gStyleStart, gStyleEnd + 8);

// D4 mt-brs-* 不在 gallery 中，需要内联追加
const d4MotifCSS = `
/* D4 黄铜年代 · 装饰母题（gallery 未收录，内联补入） */
.mt-brs-rivet{position:absolute;width:8px;height:8px;border-radius:50%;pointer-events:none;background:radial-gradient(circle at 34% 30%,color-mix(in srgb,var(--accent) 42%,var(--ink)),var(--accent) 55%,color-mix(in srgb,var(--accent) 52%,var(--paper)));box-shadow:0 1px 1px color-mix(in srgb,var(--paper) 82%,transparent)}
.mt-brs-engrave{border:2px solid color-mix(in srgb,var(--accent) 72%,transparent);outline:1px solid color-mix(in srgb,var(--accent) 38%,transparent);outline-offset:3px;box-shadow:inset 0 1px 2px color-mix(in srgb,var(--paper) 75%,transparent),inset 0 -1px 0 color-mix(in srgb,var(--accent) 25%,transparent)}
.mt-brs-stamp{display:inline-block;padding:.32em .85em;border:2px solid color-mix(in srgb,var(--accent-2) 85%,transparent);color:var(--accent-2);font-family:var(--font-mono);font-size:12px;letter-spacing:.18em;text-transform:uppercase;transform:rotate(-3deg)}
.mt-brs-grid{position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,color-mix(in srgb,var(--ink) 5%,transparent) 0 1px,transparent 1px 56px),repeating-linear-gradient(90deg,color-mix(in srgb,var(--ink) 5%,transparent) 0 1px,transparent 1px 56px)}
`;

// 在 </style> 前追加 D4 + E1 补充母题 CSS
galleryStyleBlock = galleryStyleBlock.replace('</style>', d4MotifCSS + '\n</style>');

// ===== 2. 山禾集内容（与 assets/theme-sampler/ 截图一致） =====
const C = {
  eyebrow: '1.1 · 整体特色及优势',
  title: '一杯好茶  山野作答',
  body1: '山禾集深耕新式茶饮行业，同时通过全资子公司山禾供应链管理有限公司协同布局上游茶园直采业务。通过多年不懈努力，山禾集秉持\u201c当季鲜茶，日常相伴\u201d的经营理念，建立起从茶园到门店的全链路品控流程，持续为消费者创造价值，赢得了广大茶饮爱好者的喜爱。',
  body2: '近年来山禾集门店网络稳步扩张，行业排名持续提升。2019年，山禾集全国门店总数突破八千家，跻身行业头部梯队。截至2026年6月30日，山禾集全国门店总数8,637家（含直营门店1,653家，子公司山禾供应链合作门店432家），其中标准门店8,428家，位于行业前列；城市旗舰店总数361家。成立以来累计为超过6.8亿会员用户售出茶饮2.8亿杯。',
  kpi1Num: '8,637', kpi1Unit: '家', kpi1Label: '山禾集（含直营和子公司山禾供应链）全国门店总数', kpi1Tag: '行业前列',
  kpi2Num: '2.8', kpi2Unit: '亿杯', kpi2Label: '成立以来累计为超过6.8亿会员用户售出茶饮',
  kpi3Num: '361', kpi3Unit: '家', kpi3Label: '城市旗舰店总数',
  values: [
    '经营理念：当季鲜茶，日常相伴。',
    '使命：为大众提供新鲜、健康、平价的日常茶饮。',
    '愿景：成为持续领先的新式茶饮品牌。'
  ],
  footnote: '* 注：山禾集为虚构演示品牌，文中数据均为虚构，仅用于主题样式对比展示。'
};

// ===== 3. G10 契约驱动的 6 主题 slide HTML =====

// --- D4 黄铜年代 ---
// G10 claim: 刻线框阵承载主张句（框内 condensed 大字 + mono 编号 kicker），红色标注章从框角引出批注，铆钉钉框角
// G10 data: 三项数字 → 刻线框阵内参数条目排列，主数字独占黄铜刻度线框
// G10 invariants: 刻线框 2px solid accent border + 1px outline outline-offset:3px；铆钉只钉框角每容器≤4枚；横排等权三格容器数=0
// G10 forbidden: 横向等权三格 KPI, 卡片墙成阵, 居中 hero, 圆角卡, 弥散软影, 满版黄铜填充, 齿轮/管线 steampunk, 赛博/科幻蓝
// 保留原版 G9 母题：黄铜铆钉、刻线框、红色标注章、疏格蓝图网
const slideD4 = `  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-d4" style="font-family:var(--font-body);--paper:#1c1c1e;--paper-tint:#28282b;--ink:#e8dcc8;--ink-tint:#4a4a50;--accent:#b8860b;--accent-on:#1c1c1e;--accent-2:#c0392b;--accent-2-on:#e8dcc8;--font-display:'Franklin Gothic Medium','Arial Narrow','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-body:'Helvetica Neue','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:grain;--texture-layer:url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='f'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.55 0.75' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23f)' opacity='0.05'/%3E%3C/svg%3E&quot;);--texture-scope:cover">
      <!-- G9 母题：疏格钢板网（仪式页背景） -->
      <div class="mt-brs-grid" data-editable-skip></div>
      <div style="position:relative;height:100%;display:flex;flex-direction:column;justify-content:center;padding:96px 120px">
        <p data-editable class="reveal" style="font-family:var(--font-mono);font-size:16px;font-weight:600;letter-spacing:.18em;color:var(--accent)">${C.eyebrow}</p>

        <!-- G10 claim: 刻线框阵承载主张句 -->
        <div class="mt-brs-engrave reveal" style="--d:.1s;position:relative;margin-top:24px;max-width:1280px;padding:32px 48px">
          <span class="mt-brs-rivet" data-editable-skip style="top:-4px;left:-4px"></span>
          <span class="mt-brs-rivet" data-editable-skip style="top:-4px;right:-4px"></span>
          <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;left:-4px"></span>
          <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;right:-4px"></span>
          <p data-editable style="font-family:var(--font-mono);font-size:14px;font-weight:600;letter-spacing:.14em;color:var(--accent);text-transform:uppercase">EXPO-26 / HALL 1 · OVERVIEW</p>
          <h1 data-editable data-anim="wipe-clip" style="margin-top:14px;font-family:var(--font-display);font-size:108px;line-height:1.1;font-weight:700;letter-spacing:.06em;text-transform:uppercase">${C.title}</h1>
        </div>

        <!-- 红色标注章从框角引出批注 -->
        <div class="reveal" style="--d:.18s;position:relative;margin-top:-8px;margin-left:900px">
          <span class="mt-brs-stamp" data-editable>APPROVED</span>
        </div>

        <!-- 正文段（刻线框承载） -->
        <div class="mt-brs-engrave reveal" style="--d:.22s;position:relative;margin-top:24px;max-width:1280px;padding:24px 36px">
          <span class="mt-brs-rivet" data-editable-skip style="top:-4px;left:-4px"></span>
          <span class="mt-brs-rivet" data-editable-skip style="top:-4px;right:-4px"></span>
          <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;left:-4px"></span>
          <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;right:-4px"></span>
          <p data-editable style="font-size:18px;line-height:1.8">${C.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.8">${C.body2}</p>
        </div>

        <!-- G10 data: 刻线框阵内参数条目（非横排等权三格） -->
        <div class="reveal" style="--d:.3s;margin-top:24px;display:flex;gap:0;max-width:1280px">
          <!-- 主数字独占刻线框 + 黄铜刻度线托底 -->
          <div class="mt-brs-engrave" style="position:relative;flex:0 0 540px;padding:24px 32px;border-bottom:3px solid var(--accent)">
            <span class="mt-brs-rivet" data-editable-skip style="top:-4px;left:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="top:-4px;right:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;left:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;right:-4px"></span>
            <p data-editable style="font-family:var(--font-mono);font-size:14px;font-weight:600;letter-spacing:.14em;color:var(--accent)">SPEC.01 · KEY</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-mono);font-size:52px;font-weight:800;line-height:1.1">${C.kpi1Num}<span style="font-size:26px">${C.kpi1Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.85">${C.kpi1Label}</p>
            <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:14px;font-weight:600;color:var(--accent-2)">${C.kpi1Tag}</p>
          </div>
          <div class="mt-brs-engrave" style="position:relative;flex:0 0 380px;margin-left:-1px;padding:24px 32px">
            <span class="mt-brs-rivet" data-editable-skip style="top:-4px;left:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="top:-4px;right:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;left:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;right:-4px"></span>
            <p data-editable style="font-family:var(--font-mono);font-size:14px;font-weight:600;letter-spacing:.14em;color:var(--accent)">SPEC.02</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-mono);font-size:42px;font-weight:800;line-height:1.1">${C.kpi2Num}<span style="font-size:22px">${C.kpi2Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.85">${C.kpi2Label}</p>
          </div>
          <div class="mt-brs-engrave" style="position:relative;flex:0 0 340px;margin-left:-1px;padding:24px 32px">
            <span class="mt-brs-rivet" data-editable-skip style="top:-4px;left:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="top:-4px;right:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;left:-4px"></span>
            <span class="mt-brs-rivet" data-editable-skip style="bottom:-4px;right:-4px"></span>
            <p data-editable style="font-family:var(--font-mono);font-size:14px;font-weight:600;letter-spacing:.14em;color:var(--accent)">SPEC.03</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-mono);font-size:42px;font-weight:800;line-height:1.1">${C.kpi3Num}<span style="font-size:22px">${C.kpi3Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.85">${C.kpi3Label}</p>
          </div>
        </div>

        <!-- 价值观 -->
        <div class="reveal" style="--d:.38s;margin-top:20px;max-width:1280px">
          ${C.values.map((v,i)=>`<p data-editable style="${i>0?'margin-top:6px;':''}font-family:var(--font-mono);font-size:16px;line-height:1.7;color:var(--accent)">${v}</p>`).join('\n          ')}
        </div>
        <p data-editable class="reveal" style="--d:.44s;margin-top:10px;font-family:var(--font-mono);font-size:13px;opacity:.5">${C.footnote}</p>
      </div>

      <!-- 页脚 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.6">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>D4 · 黄铜年代 · 涂漆钢板</span>
        <span data-editable>13 / 29</span>
      </div>
    </section>
  </div>`;

// --- E9 地质地层 ---
// G10 claim: 剖面切片阵承载主张句（切片内 sans 大字 + 年代标注签引线注），层理色带在页底做层序呼应
// G10 data: 三项数字 → 层理色带上分段标尺排列，主数字独占 accent 淡阶色层段
// G10 invariants: 剖面切片直角薄色层容器；层理色带每页至多一条；横排等权三格容器数=0
// G10 forbidden: 横向等权三格 KPI, 卡片墙成阵, 居中 hero, 圆角卡, 弥散软影, 荧光高亮, 手绘/有机形态
// 保留原版 G9 母题：层理色带、岩芯样本条、等高线圈、年代标注签
const slideE9 = `  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-e9" style="font-family:var(--font-body);--paper:#f0e9d8;--paper-tint:#e3d9c3;--ink:#2c251d;--ink-tint:#413729;--accent:#a85a2a;--accent-on:#f0e9d8;--font-display:'Avenir Next','Helvetica Neue','PingFang SC','Noto Sans SC',sans-serif;--font-body:'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'JetBrains Mono','SF Mono','Menlo',monospace;--texture-type:grain;--texture-layer:url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E&quot;);--texture-scope:all">
      <!-- G9 母题：层理色带（页底） -->
      <div class="mt-geo-strata" data-editable-skip style="height:12%"></div>
      <!-- G9 母题：等高线圈（页角留白装饰） -->
      <div class="mt-geo-contour" data-editable-skip style="right:-80px;top:-60px;width:300px;height:300px"></div>
      <!-- G9 母题：岩芯样本条（年代标尺） -->
      <div class="mt-geo-core" data-editable-skip style="position:absolute;right:140px;top:180px;height:460px"></div>
      <div class="mt-geo-tag" data-editable-skip style="position:absolute;right:190px;top:210px"><span>CORE SH-26 · QUATERNARY</span></div>

      <div style="position:relative;height:100%;display:flex;flex-direction:column;justify-content:flex-start;padding:80px 120px 160px">
        <p data-editable class="reveal mt-geo-tag" style="font-size:14px"><span>${C.eyebrow}</span></p>

        <!-- G10 claim: 剖面切片阵承载主张句 -->
        <div class="reveal" style="--d:.1s;margin-top:20px;display:flex;gap:0;max-width:1240px">
          <div style="flex:0 0 auto;background:color-mix(in srgb,var(--accent) 22%,var(--paper));border-top:2px solid var(--accent);padding:28px 40px;min-width:680px">
            <h1 data-editable data-anim="wipe-clip" style="font-family:var(--font-display);font-size:88px;line-height:1.15;font-weight:700;letter-spacing:.02em">${C.title}</h1>
          </div>
          <div style="flex:0 0 auto;background:var(--paper-tint);border-top:2px solid color-mix(in srgb,var(--ink) 30%,transparent);padding:28px 40px;max-width:520px">
            <p data-editable style="font-size:18px;line-height:1.8">${C.body1}</p>
          </div>
        </div>

        <div class="reveal" style="--d:.18s;margin-top:0;display:flex;gap:0;max-width:1240px">
          <div style="flex:0 0 auto;background:var(--paper-tint);padding:24px 40px;max-width:680px">
            <p data-editable style="font-size:18px;line-height:1.8">${C.body2}</p>
          </div>
          <div style="flex:0 0 auto;background:color-mix(in srgb,var(--accent) 12%,var(--paper));padding:24px 40px;max-width:520px">
            ${C.values.map((v,i)=>`<p data-editable style="${i>0?'margin-top:8px;':''}font-family:var(--font-mono);font-size:15px;line-height:1.7">${v}</p>`).join('\n            ')}
          </div>
        </div>

        <!-- G10 data: 层理色带上分段标尺（非横排等权三格）——在层理色带上方做分段标注 -->
        <div class="reveal" style="--d:.26s;position:absolute;left:120px;right:120px;bottom:140px;display:flex;gap:0">
          <div style="flex:0 0 540px;border-top:2px solid var(--accent);background:color-mix(in srgb,var(--accent) 15%,var(--paper));padding:20px 32px">
            <div class="mt-geo-tag" data-editable-skip style="margin-bottom:8px"><span>LAYER A · KEY</span></div>
            <p data-editable style="font-family:var(--font-mono);font-size:48px;font-weight:700;line-height:1.1;color:var(--accent)">${C.kpi1Num}<span style="font-size:24px">${C.kpi1Unit}</span></p>
            <p data-editable style="margin-top:6px;font-size:15px;line-height:1.55;opacity:.85">${C.kpi1Label}</p>
            <p data-editable style="margin-top:4px;font-family:var(--font-mono);font-size:13px;color:var(--accent)">${C.kpi1Tag}</p>
          </div>
          <div style="flex:0 0 360px;border-top:2px solid color-mix(in srgb,var(--ink) 30%,transparent);background:color-mix(in srgb,var(--ink) 8%,var(--paper));padding:20px 32px;margin-left:-1px">
            <div class="mt-geo-tag" data-editable-skip style="margin-bottom:8px"><span>LAYER B</span></div>
            <p data-editable style="font-family:var(--font-mono);font-size:40px;font-weight:700;line-height:1.1">${C.kpi2Num}<span style="font-size:20px">${C.kpi2Unit}</span></p>
            <p data-editable style="margin-top:6px;font-size:15px;line-height:1.55;opacity:.85">${C.kpi2Label}</p>
          </div>
          <div style="flex:0 0 320px;border-top:2px solid color-mix(in srgb,var(--ink) 30%,transparent);background:color-mix(in srgb,var(--ink) 5%,var(--paper));padding:20px 32px;margin-left:-1px">
            <div class="mt-geo-tag" data-editable-skip style="margin-bottom:8px"><span>LAYER C</span></div>
            <p data-editable style="font-family:var(--font-mono);font-size:40px;font-weight:700;line-height:1.1">${C.kpi3Num}<span style="font-size:20px">${C.kpi3Unit}</span></p>
            <p data-editable style="margin-top:6px;font-size:15px;line-height:1.55;opacity:.85">${C.kpi3Label}</p>
          </div>
        </div>

        <p data-editable class="reveal" style="--d:.36s;position:absolute;left:120px;bottom:96px;font-family:var(--font-mono);font-size:13px;opacity:.5">${C.footnote}</p>
      </div>

      <!-- 页脚 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.6;z-index:10">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E9 · 地质地层 · 赭石</span>
        <span data-editable>14 / 29</span>
      </div>
    </section>
  </div>`;

// --- E10 星图 ---
// G10 claim: 星座连线网承载主张句（节点=要点，连线=关系），斜体星名标注节点，mono 星等注记引出说明
// G10 data: 三项数字 → 星座节点排列，主数字独占最亮星 + accent 辉光 + mono 坐标注记
// G10 invariants: 无框 + 虚线连线结构；每页星座 ≤1 组（3-7 颗星）；横排等权三格容器数=0
// G10 forbidden: 横向等权三格 KPI, 居中 hero, 圆角卡, 弥散软影, 实线实框, 密集网格矩阵, 辉光托底
// 保留原版 G9 母题：星座件（星点+连线）、黄道坐标网格、斜体星名、星等注记
const slideE10 = `  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-e10" style="font-family:var(--font-body);--paper:#0b1426;--paper-tint:#152138;--ink:#dfe7f2;--ink-tint:#1d2c47;--accent:#e8b64c;--accent-on:#0b1426;--font-display:'Songti SC','Noto Serif SC','STSong',serif;--font-body:'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:grain;--texture-layer:url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E&quot;);--texture-scope:cover">
      <!-- G9 母题：黄道坐标网格（仪式页背景） -->
      <div class="mt-star-grid" data-editable-skip></div>

      <!-- G9 母题：星座件——主张句节点 + 连线 -->
      <!-- 星座：5 颗星，连线缝成一组 -->
      <span class="mt-star-dot" data-editable-skip style="left:360px;top:320px"></span>
      <span class="mt-star-dot" data-editable-skip style="left:580px;top:260px"></span>
      <span class="mt-star-dot" data-editable-skip style="left:760px;top:380px"></span>
      <span class="mt-star-dot" data-editable-skip style="left:700px;top:540px"></span>
      <span class="mt-star-dot" data-editable-skip style="left:460px;top:500px"></span>
      <!-- 连线 -->
      <span class="mt-star-link" data-editable-skip style="left:363px;top:323px;width:228px;transform:rotate(-15.5deg)"></span>
      <span class="mt-star-link" data-editable-skip style="left:583px;top:263px;width:206px;transform:rotate(35.8deg)"></span>
      <span class="mt-star-link" data-editable-skip style="left:763px;top:383px;width:171px;transform:rotate(110.6deg)"></span>
      <span class="mt-star-link" data-editable-skip style="left:703px;top:543px;width:249px;transform:rotate(-167.3deg)"></span>

      <!-- 斜体星名标注 -->
      <p class="mt-star-name" data-editable style="position:absolute;left:500px;top:560px;font-size:22px">山禾座</p>
      <p class="mt-star-mag" data-editable style="position:absolute;left:370px;top:288px">MAG 1.0 · RA 01H 22M</p>

      <!-- 数据星座：3 颗星 -->
      <span class="mt-star-dot" data-editable-skip style="left:1140px;top:380px;width:7px;height:7px;box-shadow:0 0 14px color-mix(in srgb,var(--accent) 85%,transparent)"></span>
      <span class="mt-star-dot" data-editable-skip style="left:1380px;top:320px"></span>
      <span class="mt-star-dot" data-editable-skip style="left:1480px;top:480px"></span>
      <span class="mt-star-link" data-editable-skip style="left:1143px;top:383px;width:247px;transform:rotate(-14.2deg)"></span>
      <span class="mt-star-link" data-editable-skip style="left:1383px;top:323px;width:189px;transform:rotate(57.5deg)"></span>

      <div style="position:relative;height:100%;display:flex;flex-direction:column;justify-content:center;padding:96px 120px">
        <p data-editable class="reveal" style="font-family:var(--font-mono);font-size:15px;letter-spacing:.3em;color:var(--accent)">${C.eyebrow}</p>

        <!-- G10 claim: 星座连线网承载主张句 -->
        <div class="reveal" style="--d:.12s;margin-top:24px;max-width:900px;position:relative">
          <h1 data-editable data-anim="wipe-clip" style="font-family:var(--font-display);font-size:96px;line-height:1.2;font-weight:400;letter-spacing:.08em">${C.title}</h1>
          <p class="mt-star-name" data-editable style="margin-top:16px;font-size:20px">主张即星座——信息要点之间的关系比要点本身更重要</p>
        </div>

        <!-- 正文段（无框悬浮） -->
        <div class="reveal" style="--d:.22s;margin-top:32px;max-width:860px">
          <p data-editable style="font-size:18px;line-height:1.85;opacity:.88">${C.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.85;opacity:.88">${C.body2}</p>
        </div>

        <!-- G10 data: 星座节点排列（非横排等权三格）——主数字独占最亮星 -->
        <div class="reveal" style="--d:.32s;margin-top:28px;max-width:900px">
          <p class="mt-star-mag" data-editable style="margin-bottom:12px">DATA · 3 STARS · 1 PRIMARY</p>
          <div style="display:flex;gap:0;align-items:flex-end">
            <div style="flex:0 0 480px;border-left:1px dashed color-mix(in srgb,var(--accent) 55%,transparent);padding:12px 28px">
              <p class="mt-star-mag" data-editable>★ MAG 1.0 · BRIGHT</p>
              <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:48px;font-weight:700;line-height:1.1;color:var(--accent)">${C.kpi1Num}<span style="font-size:24px">${C.kpi1Unit}</span></p>
              <p data-editable style="margin-top:6px;font-size:15px;line-height:1.55;opacity:.8">${C.kpi1Label}</p>
              <p data-editable style="margin-top:4px;font-family:var(--font-mono);font-size:13px;color:var(--accent)">${C.kpi1Tag}</p>
            </div>
            <div style="flex:0 0 280px;border-left:1px dashed color-mix(in srgb,var(--ink) 30%,transparent);padding:12px 28px">
              <p class="mt-star-mag" data-editable>★ MAG 2.1</p>
              <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:40px;font-weight:700;line-height:1.1">${C.kpi2Num}<span style="font-size:20px">${C.kpi2Unit}</span></p>
              <p data-editable style="margin-top:6px;font-size:15px;line-height:1.55;opacity:.8">${C.kpi2Label}</p>
            </div>
            <div style="flex:0 0 240px;border-left:1px dashed color-mix(in srgb,var(--ink) 30%,transparent);padding:12px 28px">
              <p class="mt-star-mag" data-editable>★ MAG 2.8</p>
              <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:40px;font-weight:700;line-height:1.1">${C.kpi3Num}<span style="font-size:20px">${C.kpi3Unit}</span></p>
              <p data-editable style="margin-top:6px;font-size:15px;line-height:1.55;opacity:.8">${C.kpi3Label}</p>
            </div>
          </div>
        </div>

        <div class="reveal" style="--d:.42s;margin-top:18px;max-width:860px">
          ${C.values.map((v,i)=>`<p data-editable style="${i>0?'margin-top:6px;':''}font-family:var(--font-mono);font-size:16px;line-height:1.7;opacity:.7">${v}</p>`).join('\n          ')}
        </div>
        <p data-editable class="reveal" style="--d:.48s;margin-top:10px;font-family:var(--font-mono);font-size:13px;opacity:.45">${C.footnote}</p>
      </div>

      <!-- 页脚 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.6;z-index:10">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E10 · 星图 · 深蓝夜空</span>
        <span data-editable>15 / 29</span>
      </div>
    </section>
  </div>`;

// --- E1 孔版印刷 ---
// G10 claim: 拼贴卡阵承载主张句（卡上粗黑海报字 + 套色错位块垫标题），裁剪虚线分卡，荧光戳记做限量标记
// G10 data: 三项数字 → 拼贴卡阵内错落条目排列，主数字独占套印色面卡 + 荧光戳记
// G10 invariants: 微旋转拼贴卡（直角纯色块 ±1.5° rotate）；禁 masthead/mastfoot；禁 hairline 实线分隔；禁 box-shadow；禁深底容器
// G10 forbidden: 横向等权三格 KPI, 居中 hero, hairline 实线分隔, box-shadow, 精密网格对齐, 圆角卡, 深底容器
// 保留原版 G9 母题：套色错位块、套印色面、裁剪虚线、网目调点块、荧光戳记
// E1 缓动签名覆盖：--ease-out: cubic-bezier(.3,1.4,.4,1)
const slideE1 = `  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-e1" style="--ease-out:cubic-bezier(.3,1.4,.4,1);font-family:var(--font-body);--paper:#f7f2e6;--paper-tint:#ece5d3;--ink:#221d16;--ink-tint:#332c22;--accent:#FF48B0;--accent-on:#fdfaf3;--accent-2:#0078BF;--accent-2-on:#f2f8fc;--font-display:'Helvetica Neue','Arial Black','PingFang SC','Noto Sans SC',sans-serif;--font-body:'Helvetica Neue','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'Courier New','SF Mono','JetBrains Mono',monospace;--texture-type:grain;--texture-layer:url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E&quot;),radial-gradient(circle at 1px 1px,color-mix(in srgb,var(--ink) 8%,transparent) 1px,transparent 1.6px) 0 0/4px 4px,radial-gradient(70% 60% at 75% 85%,color-mix(in srgb,var(--accent) 4%,transparent),transparent 65%);--texture-scope:all">
      <!-- G9 母题：网目调点块（页角装饰） -->
      <div class="mt-ris-halftone" data-editable-skip style="left:80px;bottom:120px;width:200px;height:140px"></div>

      <div style="position:relative;height:100%;padding:80px 100px">
        <p data-editable data-anim="scale-pop" style="font-family:var(--font-mono);font-size:16px;font-weight:600;letter-spacing:.14em;transform:rotate(-1deg)">${C.eyebrow}</p>

        <!-- G10 claim: 拼贴卡阵承载主张句 -->
        <div data-anim="scale-pop" style="margin-top:24px;max-width:1100px;background:var(--paper-tint);padding:36px 44px;transform:rotate(1.2deg);position:relative">
          <span class="mt-ris-misreg" data-editable-skip style="position:absolute;inset:0"></span>
          <h1 data-editable style="font-family:var(--font-display);font-size:112px;line-height:1.05;font-weight:900;letter-spacing:-.01em;position:relative">${C.title}</h1>
        </div>

        <!-- 裁剪虚线分区 -->
        <hr class="mt-ris-cut" data-editable-skip data-anim="scale-pop" style="margin-top:32px;width:90%;transform:rotate(-.5deg)">

        <!-- 正文段（拼贴卡） -->
        <div data-anim="scale-pop" style="margin-top:24px;display:flex;gap:20px;align-items:flex-start">
          <div style="flex:1;background:color-mix(in srgb,var(--accent) 8%,var(--paper));padding:24px 32px;transform:rotate(-1deg)">
            <p data-editable style="font-size:18px;line-height:1.8">${C.body1}</p>
          </div>
          <div style="flex:1;background:color-mix(in srgb,var(--accent-2) 6%,var(--paper));padding:24px 32px;transform:rotate(1.5deg)">
            <p data-editable style="font-size:18px;line-height:1.8">${C.body2}</p>
          </div>
        </div>

        <!-- G10 data: 拼贴卡阵内错落条目（非横排等权三格）——主数字独占套印色面卡 + 荧光戳记 -->
        <div data-anim="scale-pop" style="margin-top:24px;display:flex;gap:16px;align-items:flex-start">
          <!-- 主数字：套印色面卡 -->
          <div class="mt-ris-field" style="flex:0 0 460px;padding:24px 32px;transform:rotate(-1.5deg);position:relative">
            <p data-editable style="font-family:var(--font-mono);font-size:14px;font-weight:800;letter-spacing:.12em;color:var(--accent-on)">EDITION.01 · LIMITED</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-display);font-size:56px;font-weight:900;line-height:1.05;color:var(--accent-on)">${C.kpi1Num}<span style="font-size:28px">${C.kpi1Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:15px;line-height:1.55;color:var(--accent-on);opacity:.9">${C.kpi1Label}</p>
            <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--accent-on)">${C.kpi1Tag}</p>
            <span class="mt-ris-stamp" data-editable style="position:absolute;right:-12px;top:-12px">HAND NO.01</span>
          </div>
          <div style="flex:0 0 320px;background:var(--paper-tint);padding:24px 32px;transform:rotate(1deg)">
            <p data-editable style="font-family:var(--font-mono);font-size:14px;font-weight:600;letter-spacing:.12em">EDITION.02</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-display);font-size:44px;font-weight:900;line-height:1.05">${C.kpi2Num}<span style="font-size:22px">${C.kpi2Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:15px;line-height:1.55;opacity:.85">${C.kpi2Label}</p>
          </div>
          <div style="flex:0 0 280px;background:color-mix(in srgb,var(--accent) 10%,var(--paper));padding:24px 32px;transform:rotate(-1deg)">
            <p data-editable style="font-family:var(--font-mono);font-size:14px;font-weight:600;letter-spacing:.12em">EDITION.03</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-display);font-size:44px;font-weight:900;line-height:1.05">${C.kpi3Num}<span style="font-size:22px">${C.kpi3Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:15px;line-height:1.55;opacity:.85">${C.kpi3Label}</p>
          </div>
        </div>

        <!-- 价值观 -->
        <div data-anim="scale-pop" style="margin-top:20px;display:flex;gap:16px">
          ${C.values.map((v,i)=>`<div style="flex:1;background:${i===0?'color-mix(in srgb,var(--accent-2) 5%,var(--paper))':'var(--paper-tint)'};padding:16px 24px;transform:rotate(${i===0?'0.8':'-0.5'}deg)"><p data-editable style="font-family:var(--font-mono);font-size:15px;font-weight:600;line-height:1.6">${v}</p></div>`).join('\n          ')}
        </div>
        <p data-editable data-anim="scale-pop" style="margin-top:12px;font-family:var(--font-mono);font-size:13px;opacity:.5;transform:rotate(-.5deg)">${C.footnote}</p>
      </div>

      <!-- 页脚（E1 禁 masthead/mastfoot——但 sampler 需要标识，用拼贴卡形式） -->
      <div style="position:absolute;left:100px;right:100px;bottom:24px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:13px;opacity:.6;z-index:10">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E1 · 孔版印刷 · 荧光粉</span>
        <span data-editable>16 / 29</span>
      </div>
    </section>
  </div>`;

// --- E8 号外报纸 ---
// G10 claim: 超粗黑标题压顶 + 粗细双线分区 + 多栏衬线正文承载主张，斜切引文块做观点提炼
// G10 data: 三项数字 → 边栏框内数据条目排列（1px 黑框 + mono），主数字独占头版大数字 + 号外红角标
// G10 invariants: 通栏粗细双线每页 ≤2 条；多栏正文（CSS columns 2-4 栏）是正文原生形态；横排等权三格容器数=0
// G10 forbidden: 横向等权三格 KPI, 卡片墙成阵, 居中 hero, 圆角卡, 弥散软影, 彩色圆角图表卡, 发丝线 hairline
// 保留原版 G9 母题：通栏粗细双线、报头徽标条、三栏文本容器、斜切引文块
const slideE8 = `  <div class="slide-slot">
    <section class="slide" data-slide-id="theme-e8" style="font-family:var(--font-body);--paper:#f4f1ea;--paper-tint:#e8e4da;--ink:#111111;--ink-tint:#232323;--accent:#C8102E;--accent-on:#fdf9f4;--font-display:'Arial Black','Impact','SimHei','PingFang SC','Noto Sans SC',sans-serif;--font-body:'Georgia','Times New Roman','Songti SC','SimSun',serif;--font-mono:'Consolas','Courier New','SF Mono',monospace;--texture-type:paper;--texture-layer:radial-gradient(85% 60% at 15% 8%,color-mix(in srgb,var(--ink) 4%,transparent),transparent 60%);--texture-scope:cover">
      <div style="position:relative;height:100%;padding:72px 120px 60px">
        <!-- 报头徽标条 -->
        <div class="mt-news-mast reveal" data-editable-skip><span>山禾周报</span><span>经营情况汇报 · 2026.09 · NO.01</span></div>

        <!-- G10 claim: 超粗黑标题压顶 -->
        <h1 data-editable data-anim="wipe-clip" class="reveal" style="--d:.08s;margin-top:24px;font-family:var(--font-display);font-size:116px;line-height:1.05;font-weight:900;letter-spacing:-.01em;text-transform:uppercase">${C.title}</h1>

        <!-- 粗细双线分区 -->
        <hr class="mt-news-rule reveal" data-editable-skip style="--d:.14s;margin-top:20px">

        <!-- 多栏衬线正文承载主张 -->
        <div class="reveal" style="--d:.2s;margin-top:20px;display:flex;gap:32px;max-width:1680px">
          <div style="flex:1">
            <p data-editable class="mt-news-cols" style="font-size:17px;line-height:1.85">${C.body1} ${C.body2}</p>
          </div>
          <!-- 边栏框：数据 -->
          <div style="flex:0 0 420px;border:1px solid var(--ink);padding:0">
            <div style="background:var(--ink);color:var(--paper);padding:8px 16px;font-family:var(--font-mono);font-size:12px;font-weight:600;letter-spacing:.18em;text-transform:uppercase">DATA · 关键数据</div>
            <div style="padding:16px 20px">
              <!-- 主数字：头版大数字 + 号外红角标 -->
              <div style="position:relative;border-bottom:1px solid color-mix(in srgb,var(--ink) 25%,transparent);padding-bottom:12px">
                <p data-editable style="font-family:var(--font-display);font-size:52px;font-weight:900;line-height:1.1">${C.kpi1Num}<span style="font-size:26px">${C.kpi1Unit}</span></p>
                <p data-editable style="margin-top:6px;font-size:14px;line-height:1.5;font-family:var(--font-body);opacity:.8">${C.kpi1Label}</p>
                <span style="position:absolute;top:0;right:0;background:var(--accent);color:var(--accent-on);font-family:var(--font-mono);font-size:11px;font-weight:700;padding:2px 8px;letter-spacing:.1em">${C.kpi1Tag}</span>
              </div>
              <div style="margin-top:12px;border-bottom:1px solid color-mix(in srgb,var(--ink) 25%,transparent);padding-bottom:10px">
                <p data-editable style="font-family:var(--font-display);font-size:36px;font-weight:900;line-height:1.1">${C.kpi2Num}<span style="font-size:18px">${C.kpi2Unit}</span></p>
                <p data-editable style="margin-top:4px;font-size:13px;line-height:1.5;font-family:var(--font-body);opacity:.8">${C.kpi2Label}</p>
              </div>
              <div style="margin-top:10px">
                <p data-editable style="font-family:var(--font-display);font-size:36px;font-weight:900;line-height:1.1">${C.kpi3Num}<span style="font-size:18px">${C.kpi3Unit}</span></p>
                <p data-editable style="margin-top:4px;font-size:13px;line-height:1.5;font-family:var(--font-body);opacity:.8">${C.kpi3Label}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 斜切引文块做观点提炼 -->
        <div class="mt-news-pull reveal" data-editable-skip style="--d:.28s;margin-top:24px;max-width:1240px">
          <p data-editable style="font-size:22px">${C.values[0]}</p>
        </div>

        <!-- 价值观续 -->
        <div class="reveal" style="--d:.34s;margin-top:16px;display:flex;gap:32px;max-width:1240px">
          ${C.values.slice(1).map((v,i)=>`<div style="flex:1;border-top:1px solid var(--ink);padding-top:10px"><p data-editable style="font-family:var(--font-body);font-size:17px;line-height:1.7">${v}</p></div>`).join('\n          ')}
        </div>
        <p data-editable class="reveal" style="--d:.4s;margin-top:12px;font-family:var(--font-mono);font-size:13px;opacity:.55">${C.footnote}</p>
      </div>

      <!-- 页脚 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.6">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E8 · 号外报纸 · 纸白</span>
        <span data-editable>17 / 29</span>
      </div>
    </section>
  </div>`;

// --- E11 票据 ---
// G10 claim: 票据容器承载主张句（mono 字段行 LABEL/VALUE 排列），齿孔撕线分主券/副券，副券做摘要存根
// G10 data: 三项数字 → 票根字段行排列（mono LABEL/VALUE 对），主数字独占一行 mono 大字 + accent 头带
// G10 invariants: 票据容器 1px 描边 + 齿孔分隔；齿孔撕线每页至多一条；横排等权三格容器数=0
// G10 forbidden: 横向等权三格 KPI, 卡片墙成阵, 居中 hero, 圆角大卡, 弥散软影, 竖排题字条/Ghost 残影, 圆角弥散卡
// 保留原版 G9 母题：齿孔撕线、条码、票根字段行、副券区
const slideE11 = `  <div class="slide-slot">
    <section class="slide" data-slide-id="theme-e11" style="font-family:var(--font-body);--paper:#FDFCF9;--paper-tint:#F2F0E8;--ink:#1D2129;--ink-tint:#3A3F4A;--accent:#0F4C81;--accent-on:#FDFCF9;--font-display:'Arial Black','Avenir Next Heavy','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-body:'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:flat;--texture-layer:none;--texture-scope:cover">
      <div style="position:relative;height:100%;display:flex;flex-direction:column;padding:0">
        <!-- accent 头带横贯版面上缘 -->
        <div style="background:var(--accent);color:var(--accent-on);padding:12px 120px;display:flex;justify-content:space-between;align-items:baseline;font-family:var(--font-mono);font-size:14px;font-weight:600;letter-spacing:.18em;text-transform:uppercase">
          <span data-editable>SHANHE · BUSINESS REPORT</span>
          <span data-editable>2026.09 · NO.01 · CLAIM</span>
        </div>

        <div style="flex:1;display:flex;padding:32px 120px 0;gap:0">
          <!-- 主券区 -->
          <div style="flex:1;border:1px solid color-mix(in srgb,var(--ink) 30%,transparent);padding:32px 40px;position:relative">
            <p data-editable class="reveal" style="font-family:var(--font-mono);font-size:14px;font-weight:500;letter-spacing:.18em;color:var(--accent)">${C.eyebrow}</p>

            <!-- G10 claim: 票根字段行承载主张句 -->
            <div class="reveal" style="--d:.1s;margin-top:20px;display:flex;gap:48px;align-items:baseline">
              <p class="mt-tix-field" data-editable style="font-size:22px"><small>CLAIM</small><b>${C.title}</b></p>
            </div>

            <h1 data-editable data-anim="wipe-clip" class="reveal" style="--d:.16s;margin-top:16px;font-family:var(--font-display);font-size:96px;line-height:1.05;font-weight:800;letter-spacing:-.01em">${C.title}</h1>

            <!-- 正文段（字段行形式） -->
            <div class="reveal" style="--d:.22s;margin-top:24px;display:grid;grid-template-columns:1fr 1fr;gap:16px 48px">
              <p class="mt-tix-field" data-editable style="font-size:16px"><small>OVERVIEW</small><b style="font-family:var(--font-body);font-weight:400;text-transform:none;letter-spacing:0;font-size:16px;line-height:1.7">${C.body1}</b></p>
              <p class="mt-tix-field" data-editable style="font-size:16px"><small>PROGRESS</small><b style="font-family:var(--font-body);font-weight:400;text-transform:none;letter-spacing:0;font-size:16px;line-height:1.7">${C.body2}</b></p>
            </div>

            <!-- G10 data: 票根字段行排列（非横排等权三格）——主数字独占一行 mono 大字 + accent 头带标记 -->
            <div class="reveal" style="--d:.3s;margin-top:24px;border-top:1px solid color-mix(in srgb,var(--ink) 25%,transparent);padding-top:16px">
              <div style="display:flex;gap:32px;align-items:baseline;border-left:3px solid var(--accent);padding-left:16px;margin-bottom:12px">
                <p class="mt-tix-field" data-editable style="font-size:18px"><small>KEY METRIC · PRIMARY</small><b style="font-size:48px">${C.kpi1Num}</b><span style="font-size:24px;font-weight:700">${C.kpi1Unit}</span></p>
                <p data-editable style="font-size:15px;line-height:1.55;opacity:.8;flex:1">${C.kpi1Label} · <span style="font-family:var(--font-mono);color:var(--accent);font-weight:600">${C.kpi1Tag}</span></p>
              </div>
              <div style="display:flex;gap:32px">
                <div style="flex:1">
                  <p class="mt-tix-field" data-editable style="font-size:16px"><small>SPEC.02</small><b style="font-size:36px">${C.kpi2Num}</b><span style="font-size:18px;font-weight:700">${C.kpi2Unit}</span></p>
                  <p data-editable style="margin-top:4px;font-size:14px;line-height:1.5;opacity:.8">${C.kpi2Label}</p>
                </div>
                <div style="flex:1">
                  <p class="mt-tix-field" data-editable style="font-size:16px"><small>SPEC.03</small><b style="font-size:36px">${C.kpi3Num}</b><span style="font-size:18px;font-weight:700">${C.kpi3Unit}</span></p>
                  <p data-editable style="margin-top:4px;font-size:14px;line-height:1.5;opacity:.8">${C.kpi3Label}</p>
                </div>
              </div>
            </div>

            <!-- 价值观 -->
            <div class="reveal" style="--d:.38s;margin-top:16px;display:flex;gap:24px">
              ${C.values.map((v,i)=>`<p class="mt-tix-field" data-editable style="flex:1;font-size:13px"><small>VALUE.0${i+1}</small><b style="font-family:var(--font-body);font-weight:400;text-transform:none;letter-spacing:0;font-size:14px;line-height:1.6">${v}</b></p>`).join('\n              ')}
            </div>
            <p data-editable class="reveal" style="--d:.44s;margin-top:10px;font-family:var(--font-mono);font-size:12px;opacity:.5">${C.footnote}</p>
          </div>

          <!-- 齿孔撕线 -->
          <div class="mt-tix-perf" data-editable-skip style="width:0;height:auto;border-top:none;border-left:2px dashed color-mix(in srgb,var(--ink) 50%,transparent);margin:32px 0"></div>

          <!-- 副券区（存根/摘要） -->
          <div class="mt-tix-stub" style="flex:0 0 320px;padding:32px 28px;display:flex;flex-direction:column;justify-content:flex-start">
            <p class="mt-tix-field" data-editable style="font-size:14px"><small>STUB · SUMMARY</small></p>
            <p data-editable style="margin-top:12px;font-family:var(--font-display);font-size:28px;font-weight:800;line-height:1.2">${C.title}</p>
            <hr style="margin-top:16px;border:none;border-top:1px solid color-mix(in srgb,var(--ink) 20%,transparent)">
            <p class="mt-tix-field" data-editable style="margin-top:12px;font-size:13px"><small>BUSINESS</small><b style="font-family:var(--font-body);font-weight:400;text-transform:none;letter-spacing:0;font-size:13px;line-height:1.6">山禾集 · 新式茶饮</b></p>
            <p class="mt-tix-field" data-editable style="margin-top:8px;font-size:13px"><small>STORES</small><b>${C.kpi1Num}${C.kpi1Unit}</b></p>
            <p class="mt-tix-field" data-editable style="margin-top:8px;font-size:13px"><small>CUPS</small><b>${C.kpi2Num}${C.kpi2Unit}</b></p>
            <p class="mt-tix-field" data-editable style="margin-top:8px;font-size:13px"><small>FLAGSHIP</small><b>${C.kpi3Num}${C.kpi3Unit}</b></p>
            <p class="mt-tix-field" data-editable style="margin-top:12px;font-size:13px"><small>VALID</small><b>2026.06.30</b></p>
            <div style="flex:1"></div>
            <p class="mt-tix-field" data-editable style="font-size:11px;opacity:.6"><small>CLASS</small><b>THEME / E11</b></p>
          </div>
        </div>

        <!-- 条码页底横贯 -->
        <div style="padding:0 120px 12px">
          <div class="mt-tix-barcode" data-editable-skip style="width:100%"></div>
        </div>
      </div>

      <!-- 页脚 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:13px;opacity:.55;z-index:10">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E11 · 票据 · 航司蓝</span>
        <span data-editable>18 / 29</span>
      </div>
    </section>
  </div>`;

// ===== 4. 组装 HTML =====
const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920">
<title>Theme Sampler · Batch 4-5 · G10 契约布局 + 山禾集内容</title>
${galleryStyleBlock}

/* ===== 截图修复：强制 1:1 渲染 ===== */
:root{--slide-scale:1}
html,body{background:#222;height:auto}
.deck{display:flex!important;flex-direction:column!important;align-items:center!important;height:auto!important;overflow:visible!important;padding:24px 0;scroll-snap-type:none!important}
.slide-slot{width:1920px!important;height:1080px!important;margin:12px 0!important;position:relative;overflow:visible!important;content-visibility:visible!important;scroll-snap-align:none!important}
.slide{width:1920px!important;height:1080px!important;transform:none!important;overflow:hidden}
.reveal{opacity:1!important;transform:none!important}
[data-anim="wipe-clip"]{clip-path:inset(0 0 0 0)!important}
[data-anim="mask-lines"] .ml-inner{transform:none!important}
[data-anim="blur-in"]{filter:none!important}
[data-anim="flicker-in"]{opacity:1!important;animation:none!important}
[data-anim="ring"]{stroke-dashoffset:calc(100 - var(--val,0))!important}
[data-anim="gradient-flow"]{animation:none!important}
[data-anim="typewriter"].tw-live::after{animation:none!important}
[data-anim="scale-pop"]{opacity:1!important;transform:none!important}
.split-anim .sp-unit{opacity:1!important;transform:none!important}
.amb-pulse,.amb-drift,.amb-glow{animation:none!important}
</style>
</head>
<body>
<div class="deck" id="deck">
${slideD4}
${slideE9}
${slideE8}
${slideE11}
</div>
<script>(function(){document.documentElement.classList.add("js");document.querySelectorAll(".slide").forEach(function(s){s.classList.add("in-view")});})();</script>
</body>
</html>`;

fs.writeFileSync(path.join(DIR, 'theme-sampler-6.html'), html);
console.log('Generated theme-sampler-6.html (' + html.length + ' chars)');
console.log('  Content: 山禾集业务汇报 (claim page)');
console.log('  Layout: G10 info_grammar.claim 契约驱动');
console.log('  Framework: gallery 骨架框架 CSS（padding/mastfoot/reveal/G9母题）');
console.log('  Themes: D4 黄铜年代 / E9 地质地层 / E8 号外报纸 / E11 票据');
