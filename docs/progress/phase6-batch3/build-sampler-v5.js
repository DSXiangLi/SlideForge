/* phase6-batch3 / build-sampler-v5.js
 * 保留原版骨架框架层（padding/mastfoot/reveal/G9母题 CSS）+ 山禾集内容
 * 布局按当前技能 theme.md 的 G10 info_grammar.claim 契约重构
 *
 * G10 契约摘要：
 * G4 claim: 裂屏对开（黄/靛对撞），主张句在黄面上反白，说明在靛面上
 * G4 data:  靛蓝线框内纵向或错落排列，主数字独占黄面焦点
 * G5 claim: 裂屏对开（暗夜蓝/苔绿对撞），主张句在暗夜蓝底苔绿字上
 * G5 data:  三色反转面并置排列，主数字独占暗夜蓝底面
 * E2 claim: 主张句在主图框内，标注线指向关键数据点，标题栏钉右下
 * E2 data:  图框内 mono key:value 标注行，主数字用亮青标注线强调
 * E3 claim: 中轴金框装主张句 + 两侧金线翼卫 + 底部菱形引出说明
 * E3 data:  对称双栏镜像模块，主数字在中轴金框内
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
const galleryStyleBlock = galleryHTML.substring(gStyleStart, gStyleEnd + 8);

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

// ===== 3. G10 契约驱动的 4 主题 slide HTML =====
// 保留原版骨架框架层：.slide 的 padding:var(--slide-pad) 即 96px 120px
// .reveal 入场动效类、footer 用原版内联定位（与原版 sampler 一致）

// --- G4 靛墨黄页 ---
// G10 claim: 裂屏对开（黄/靛对撞），主张句在黄面上反白，说明在靛面上
// G10 data: 靛蓝线框内纵向或错落排列，主数字独占黄面焦点
// G10 invariants: 出血色面 ≥1；1.5px solid var(--ink) 结构线；横排等权三格容器数 = 0
// G10 forbidden: 横向等权三格 KPI, 居中 hero
// 保留原版 G9 母题：黄楔右缘出血、展览编号签、对撞带
const slideG4 = `  <div class="slide-slot">
    <section class="slide" data-slide-id="theme-g4" style="font-family:var(--font-body);--paper:#E9E5DB;--paper-tint:#DDD8CB;--ink:#1B2566;--ink-tint:#2A3374;--accent:#F1EE2E;--accent-on:#1B2566;--accent-2:#E26B4A;--accent-2-on:#FAF1E2;--font-display:'Helvetica Neue','Arial Black','PingFang SC','Noto Sans SC',sans-serif;--font-body:'Helvetica Neue','PingFang SC','Noto Sans SC',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:flat;--texture-layer:none;--texture-scope:cover;padding:0">
      <!-- G9 母题：黄楔出血 + 编号签 + 对撞带（原版位置保留） -->
      <div class="mt-bie-wedge" data-editable-skip style="right:0;top:0;bottom:0;width:380px"></div>
      <span class="mt-bie-num" data-editable style="position:absolute;right:64px;bottom:120px;font-size:160px">28</span>
      <span class="mt-bie-band" data-editable-skip style="position:absolute;left:0;right:0;bottom:0"></span>

      <!-- G10 claim: 裂屏对开——左靛蓝面（说明）+ 右黄面（主张句反白） -->
      <!-- 左侧靛蓝面（说明在靛面上） -->
      <div style="position:absolute;left:0;top:0;width:960px;height:100%;background:var(--ink);color:var(--paper);padding:80px 60px 80px 120px;display:flex;flex-direction:column;justify-content:center">
        <p data-editable class="reveal" style="font-family:var(--font-mono);font-size:16px;font-weight:600;letter-spacing:.14em;opacity:.7">${C.eyebrow}</p>
        <div class="reveal" style="--d:.12s;margin-top:24px;max-width:720px">
          <p data-editable style="font-size:18px;line-height:1.8">${C.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.8">${C.body2}</p>
        </div>
        <div class="reveal" style="--d:.24s;margin-top:28px;max-width:720px;border-top:1.5px solid var(--accent);padding-top:16px">
          ${C.values.map((v,i)=>`<p data-editable style="${i>0?'margin-top:8px;':''}font-size:19px;line-height:1.7">${v}</p>`).join('\n          ')}
        </div>
      </div>

      <!-- 右侧黄面（主张句在黄面上反白） -->
      <div style="position:absolute;right:0;top:0;width:960px;height:100%;background:var(--accent);color:var(--accent-on);padding:80px 80px 80px 60px;display:flex;flex-direction:column;justify-content:center">
        <h1 data-editable data-anim="wipe-clip" style="font-family:var(--font-display);font-size:92px;line-height:1.1;font-weight:900;letter-spacing:.02em">${C.title}</h1>

        <!-- G10 data: 靛蓝线框内纵向错落排列，主数字独占黄面焦点（余烬橙单点） -->
        <div class="reveal" style="--d:.16s;margin-top:36px;display:flex;flex-direction:column;gap:0;max-width:780px">
          <div style="border:2px solid var(--ink);padding:20px 28px;background:var(--accent)">
            <p data-editable style="font-family:var(--font-mono);font-size:52px;font-weight:800;line-height:1.1;color:var(--accent-2)">${C.kpi1Num}<span style="font-size:26px">${C.kpi1Unit}</span></p>
            <p data-editable style="margin-top:6px;font-size:16px;line-height:1.5;opacity:.85">${C.kpi1Label}</p>
            <p data-editable style="margin-top:4px;font-family:var(--font-mono);font-size:14px;font-weight:600;color:var(--accent-2)">${C.kpi1Tag}</p>
          </div>
          <div style="display:flex;gap:0">
            <div style="flex:1;border:2px solid var(--ink);border-top:none;border-right:none;padding:20px 28px;background:var(--accent)">
              <p data-editable style="font-family:var(--font-mono);font-size:42px;font-weight:800;line-height:1.1">${C.kpi2Num}<span style="font-size:22px">${C.kpi2Unit}</span></p>
              <p data-editable style="margin-top:6px;font-size:15px;line-height:1.5;opacity:.85">${C.kpi2Label}</p>
            </div>
            <div style="flex:1;border:2px solid var(--ink);border-top:none;padding:20px 28px;background:var(--accent)">
              <p data-editable style="font-family:var(--font-mono);font-size:42px;font-weight:800;line-height:1.1">${C.kpi3Num}<span style="font-size:22px">${C.kpi3Unit}</span></p>
              <p data-editable style="margin-top:6px;font-size:15px;line-height:1.5;opacity:.85">${C.kpi3Label}</p>
            </div>
          </div>
        </div>
        <p data-editable class="reveal" style="--d:.32s;margin-top:16px;font-family:var(--font-mono);font-size:13px;opacity:.55">${C.footnote}</p>
      </div>

      <!-- 页脚（原版 mastfoot 样式） -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.65;z-index:10">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>G4 · 靛墨黄页 · 太阳黄</span>
        <span data-editable>28 / 29</span>
      </div>
    </section>
  </div>`;

// --- G5 三色旬刊 ---
// G10 claim: 裂屏对开（暗夜蓝/苔绿对撞），主张句在暗夜蓝底苔绿字上
// G10 data: 三色反转面并置排列，主数字独占暗夜蓝底面
// G10 invariants: 三色反转面 ≥2；三色带每页至多一条；横排等权三格容器数 = 0
// G10 forbidden: 横向等权三格 KPI, 黑/白/灰文字
// 保留原版 G9 母题：刊号签、三色带
const slideG5 = `  <div class="slide-slot">
    <section class="slide" data-slide-id="theme-g5" style="font-family:var(--font-body);--paper:#E4C9A8;--paper-tint:#8BAE6F;--ink:#1A2B3D;--ink-tint:#121E2D;--accent:#8BAE6F;--accent-on:#1A2B3D;--font-display:'Didot','Bodoni MT','Songti SC','Noto Serif SC',serif;--font-body:'Songti SC','Noto Serif SC','STSong',serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:flat;--texture-layer:none;--texture-scope:cover;padding:0">
      <!-- G9 母题：三色带 + 刊号签（原版位置保留） -->
      <span class="mt-tri-band" data-editable-skip style="position:absolute;left:0;right:0;bottom:0;z-index:5"></span>
      <div style="position:absolute;left:120px;top:64px;z-index:10"><span class="mt-tri-tag" data-editable>VOL.03 / NO.29</span></div>

      <!-- G10 claim: 裂屏对开——左暗夜蓝面（主张句苔绿字）+ 右苔绿面（说明暗夜蓝字） -->
      <!-- 左侧暗夜蓝面（主张句在暗夜蓝底苔绿字上） -->
      <div style="position:absolute;left:0;top:0;width:1000px;height:100%;background:var(--ink);color:var(--accent);padding:120px 80px 80px 120px;display:flex;flex-direction:column;justify-content:center">
        <p data-editable class="reveal" style="font-family:var(--font-mono);font-size:16px;font-weight:500;letter-spacing:.14em;opacity:.7">${C.eyebrow}</p>
        <h1 data-anim="mask-lines" style="margin-top:22px;font-family:var(--font-display);font-size:84px;line-height:1.2;font-weight:600"><span class="ml-line"><span class="ml-inner" data-editable>${C.title}</span></span></h1>
        <!-- G10 invariants: 三色反转面 ≥2——暗夜蓝底苔绿字框 -->
        <div class="mt-tri-frame reveal" style="--d:.14s;margin-top:28px;max-width:760px;padding:24px 36px">
          <p data-editable style="font-size:18px;line-height:1.85;color:var(--paper)">${C.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.85;color:var(--paper)">${C.body2}</p>
        </div>
      </div>

      <!-- 右侧苔绿面（说明在苔绿底暗夜蓝字上——反转配对） -->
      <div style="position:absolute;right:0;top:0;width:920px;height:100%;background:var(--accent);color:var(--accent-on);padding:120px 120px 80px 60px;display:flex;flex-direction:column;justify-content:center">
        <!-- G10 data: 三色反转面并置排列，主数字独占暗夜蓝底面 -->
        <div class="reveal" style="--d:.2s;display:flex;flex-direction:column;gap:14px;max-width:680px">
          <!-- 主数字：暗夜蓝底苔绿字（独占暗夜蓝底面——单焦点） -->
          <div style="background:var(--ink);color:var(--accent);padding:22px 32px">
            <p data-editable style="font-family:var(--font-display);font-size:48px;font-weight:600;line-height:1.2">${C.kpi1Num}<span style="font-size:24px">${C.kpi1Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:17px;line-height:1.55;color:var(--paper)">${C.kpi1Label}</p>
            <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:14px;font-weight:600">${C.kpi1Tag}</p>
          </div>
          <!-- 赭石底暗夜蓝字（第三色轮转） -->
          <div style="background:var(--paper);color:var(--ink);padding:22px 32px">
            <p data-editable style="font-family:var(--font-display);font-size:42px;font-weight:600;line-height:1.2">${C.kpi2Num}<span style="font-size:22px">${C.kpi2Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:17px;line-height:1.55">${C.kpi2Label}</p>
          </div>
          <!-- 苔绿底暗夜蓝字（与右栏面同色——反转配对中的同色续） -->
          <div style="background:var(--paper);color:var(--ink);padding:22px 32px">
            <p data-editable style="font-family:var(--font-display);font-size:42px;font-weight:600;line-height:1.2">${C.kpi3Num}<span style="font-size:22px">${C.kpi3Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:17px;line-height:1.55">${C.kpi3Label}</p>
          </div>
        </div>
        <div class="reveal" style="--d:.3s;margin-top:20px;max-width:680px">
          ${C.values.map((v,i)=>`<p data-editable style="${i>0?'margin-top:6px;':''}font-size:19px;line-height:1.7">${v}</p>`).join('\n          ')}
        </div>
        <p data-editable class="reveal" style="--d:.38s;margin-top:10px;font-family:var(--font-mono);font-size:13px;opacity:.6">${C.footnote}</p>
      </div>

      <!-- 页脚 -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.65;z-index:10">
        <span data-editable style="color:var(--accent)">山禾集 · 经营情况汇报</span>
        <span data-editable style="color:var(--ink)">G5 · 三色旬刊 · 赭石</span>
        <span data-editable style="color:var(--accent)">29 / 29</span>
      </div>
    </section>
  </div>`;

// --- E2 蓝图 ---
// G10 claim: 主张句在主图框内，标注线指向关键数据点，标题栏钉右下
// G10 data: 图框内 mono key:value 标注行，主数字用亮青标注线强调
// G10 invariants: 双线图框 ≥2；图框标题栏每页至多一个钉右下；制图网格全页铺；横排等权三格容器数 = 0
// G10 forbidden: 横向等权三格 KPI, 满版色块, 圆角卡
// 保留原版 G9 母题：双线图框、图框标题栏、尺寸标注线
const slideE2 = `  <div class="slide-slot">
    <section class="slide texture-on" data-slide-id="theme-e2" style="font-family:var(--font-body);--paper:#14304a;--paper-tint:#1b3d5c;--ink:#f2f6f9;--ink-tint:#0f2438;--accent:#35C8E8;--accent-on:#0e2a3f;--font-display:'Helvetica Neue','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-body:'Helvetica Neue','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:paper;--texture-layer:repeating-linear-gradient(0deg,color-mix(in srgb,var(--ink) 5%,transparent) 0 1px,transparent 1px 7px),repeating-linear-gradient(90deg,color-mix(in srgb,var(--ink) 5%,transparent) 0 1px,transparent 1px 7px),repeating-linear-gradient(0deg,color-mix(in srgb,var(--ink) 12%,transparent) 0 1px,transparent 1px 35px),repeating-linear-gradient(90deg,color-mix(in srgb,var(--ink) 12%,transparent) 0 1px,transparent 1px 35px);--texture-scope:all">
      <!-- G9 母题：整页双线图框内框 + 图框标题栏（原版位置保留） -->
      <div class="mt-bp-frame" data-editable-skip style="position:absolute;inset:48px 60px">
        <div class="mt-bp-tag"><span>FIG. 1-1</span><span>SCALE 1:1</span><span>2026.06</span></div>
      </div>

      <div style="position:relative;height:100%;display:flex;flex-direction:column;justify-content:center;padding:96px 120px">
        <p data-editable class="reveal" style="font-family:var(--font-mono);font-size:15px;letter-spacing:.3em;color:var(--accent)">${C.eyebrow}</p>

        <!-- G10 claim: 主张句在主图框内 -->
        <div class="mt-bp-frame reveal" style="--d:.1s;margin-top:22px;max-width:1300px;padding:28px 40px">
          <h1 data-editable data-anim="wipe-clip" style="font-size:88px;line-height:1.25;font-weight:600;letter-spacing:.04em">${C.title}</h1>
        </div>

        <!-- 双线图框装正文（图框成阵即分区） -->
        <div class="mt-bp-frame reveal" style="--d:.16s;margin-top:20px;max-width:1300px;padding:24px 36px">
          <p data-editable style="font-size:18px;line-height:1.8;opacity:.88">${C.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.8;opacity:.88">${C.body2}</p>
        </div>

        <!-- G10 data: 图框内 mono key:value 标注行，主数字用亮青标注线强调（非横排等权三格） -->
        <div class="reveal" style="--d:.24s;margin-top:24px;display:flex;gap:0;max-width:1300px">
          <!-- 主数字图框（亮青标注线强调） -->
          <div class="mt-bp-frame" style="flex:0 0 520px;padding:24px 32px">
            <div class="mt-bp-dim" data-editable-skip style="margin-bottom:12px"><i></i><span style="color:var(--accent)">KEY METRIC</span><i></i></div>
            <p data-editable style="font-family:var(--font-mono);font-size:50px;font-weight:600;line-height:1.15;color:var(--accent)">${C.kpi1Num}<span style="font-size:24px">${C.kpi1Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.8">${C.kpi1Label}</p>
            <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:14px;color:var(--accent)">${C.kpi1Tag}</p>
          </div>
          <!-- 辅助数字图框 -->
          <div class="mt-bp-frame" style="flex:0 0 380px;margin-left:-1px;padding:24px 32px">
            <p data-editable style="font-family:var(--font-mono);font-size:14px;letter-spacing:.12em;opacity:.6">SPEC.02</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-mono);font-size:42px;font-weight:600;line-height:1.15">${C.kpi2Num}<span style="font-size:20px">${C.kpi2Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.8">${C.kpi2Label}</p>
          </div>
          <div class="mt-bp-frame" style="flex:0 0 340px;margin-left:-1px;padding:24px 32px">
            <p data-editable style="font-family:var(--font-mono);font-size:14px;letter-spacing:.12em;opacity:.6">SPEC.03</p>
            <p data-editable style="margin-top:8px;font-family:var(--font-mono);font-size:42px;font-weight:600;line-height:1.15">${C.kpi3Num}<span style="font-size:20px">${C.kpi3Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.8">${C.kpi3Label}</p>
          </div>
        </div>

        <!-- 标注线（G9 signature） -->
        <div class="mt-bp-dim reveal" data-editable-skip style="--d:.3s;margin-top:18px;max-width:1300px"><i></i><span data-editable style="font-size:14px">单位：亿元人民币 · 截至 2026.6.3</span><i></i></div>

        <!-- 价值观 -->
        <div class="reveal" style="--d:.36s;margin-top:18px;max-width:1300px">
          ${C.values.map((v,i)=>`<p data-editable style="${i>0?'margin-top:6px;':''}border-top:1px solid color-mix(in srgb,var(--ink) 45%,transparent);padding:8px 0;font-size:19px">${v}</p>`).join('\n          ')}
        </div>
        <p data-editable class="reveal" style="--d:.42s;margin-top:12px;font-family:var(--font-mono);font-size:14px;opacity:.55">${C.footnote}</p>
      </div>

      <!-- 页脚（原版样式） -->
      <div style="position:absolute;left:120px;right:120px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.7">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E2 · 蓝图 · 经典蓝图</span>
        <span data-editable>11 / 29</span>
      </div>
    </section>
  </div>`;

// --- E3 装饰艺术 ---
// G10 claim: 中轴金框装主张句 + 两侧金线翼卫 + 底部菱形引出说明
// G10 data: 对称双栏镜像模块，主数字在中轴金框内
// G10 invariants: 中轴对称；双线金框 ≥1；菱形分隔只许中轴对称位；横排等权三格容器数 = 0
// G10 forbidden: 横向等权三格 KPI, 居中 hero（裸居中文字无金框）, 斜线/对角, 大面积金块
// 保留原版 G9 母题：扇形放射、双线金框、菱形分隔
const slideE3 = `  <div class="slide-slot">
    <section class="slide" data-slide-id="theme-e3" style="font-family:var(--font-body);--paper:#111110;--paper-tint:#1b1b18;--ink:#f0e9d6;--ink-tint:#0a0a09;--accent:#c9a227;--accent-on:#111110;--font-display:'Songti SC','Noto Serif SC','STSong',serif;--font-body:'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;--font-mono:'SF Mono','JetBrains Mono','Menlo',monospace;--texture-type:flat;--texture-layer:none;--texture-scope:cover">
      <!-- G9 母题：扇形放射 + 双线金框整页内框（原版位置保留） -->
      <div class="mt-deco-sun" data-editable-skip style="position:absolute;left:50%;top:0;transform:translateX(-50%)"></div>
      <div class="mt-deco-frame" data-editable-skip style="position:absolute;inset:56px 72px;pointer-events:none"></div>

      <div style="position:relative;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:96px 120px">
        <p data-editable class="reveal" style="font-family:var(--font-mono);font-size:15px;font-weight:500;letter-spacing:.34em;color:var(--accent)">${C.eyebrow}</p>
        <div class="mt-deco-divider reveal" data-editable-skip style="--d:.08s;margin-top:20px"><span class="mt-deco-rhombus"></span></div>

        <!-- G10 claim: 中轴金框装主张句 + 两侧金线翼卫 -->
        <div class="reveal" style="--d:.14s;margin-top:20px;display:flex;align-items:center;gap:0;max-width:1400px">
          <div style="flex:1;height:1px;background:color-mix(in srgb,var(--accent) 65%,transparent)"></div>
          <div class="mt-deco-frame" style="padding:24px 56px;text-align:center;flex:0 0 auto">
            <h1 data-anim="mask-lines" style="font-family:var(--font-display);font-size:72px;line-height:1.3;font-weight:600;letter-spacing:.06em;white-space:nowrap"><span class="ml-line"><span class="ml-inner" data-editable>${C.title}</span></span></h1>
          </div>
          <div style="flex:1;height:1px;background:color-mix(in srgb,var(--accent) 65%,transparent)"></div>
        </div>

        <div class="reveal" style="--d:.2s;margin-top:20px;max-width:1100px">
          <p data-editable style="font-size:18px;line-height:1.85;opacity:.85">${C.body1}</p>
          <p data-editable style="margin-top:10px;font-size:18px;line-height:1.85;opacity:.85">${C.body2}</p>
        </div>

        <!-- G10 data: 对称双栏镜像模块，主数字在中轴金框内 -->
        <div class="reveal" style="--d:.28s;margin-top:24px;display:flex;justify-content:center;align-items:stretch">
          <div style="padding:0 40px;text-align:center">
            <p data-editable style="font-family:var(--font-display);font-size:46px;font-weight:600;line-height:1.15">${C.kpi2Num}<span style="font-size:22px">${C.kpi2Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.75;max-width:300px">${C.kpi2Label}</p>
          </div>
          <div class="mt-deco-frame" style="padding:18px 44px;text-align:center">
            <p data-editable style="font-family:var(--font-display);font-size:52px;font-weight:600;line-height:1.15;color:var(--accent)">${C.kpi1Num}<span style="font-size:24px">${C.kpi1Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.75;max-width:320px">${C.kpi1Label}</p>
            <p data-editable style="margin-top:6px;font-family:var(--font-mono);font-size:13px;color:var(--accent)">${C.kpi1Tag}</p>
          </div>
          <div style="padding:0 40px;text-align:center">
            <p data-editable style="font-family:var(--font-display);font-size:46px;font-weight:600;line-height:1.15">${C.kpi3Num}<span style="font-size:22px">${C.kpi3Unit}</span></p>
            <p data-editable style="margin-top:8px;font-size:16px;line-height:1.55;opacity:.75;max-width:300px">${C.kpi3Label}</p>
          </div>
        </div>

        <!-- G10 claim: 底部菱形引出说明 -->
        <div class="mt-deco-divider reveal" data-editable-skip style="--d:.34s;margin-top:22px"><span class="mt-deco-rhombus"></span></div>
        <div class="reveal" style="--d:.4s;margin-top:14px;max-width:900px">
          ${C.values.map((v,i)=>`<p data-editable style="${i>0?'margin-top:6px;':''}font-size:19px;line-height:1.8">${v}</p>`).join('\n          ')}
        </div>
        <p data-editable class="reveal" style="--d:.46s;margin-top:12px;font-family:var(--font-mono);font-size:14px;opacity:.5">${C.footnote}</p>
      </div>

      <!-- 页脚（原版样式） -->
      <div style="position:absolute;left:160px;right:160px;bottom:30px;display:flex;justify-content:space-between;align-items:baseline;gap:2em;font-family:var(--font-mono);font-size:14px;opacity:.65">
        <span data-editable>山禾集 · 经营情况汇报</span>
        <span data-editable>E3 · 装饰艺术 · 墨黑金</span>
        <span data-editable>12 / 29</span>
      </div>
    </section>
  </div>`;

// ===== 4. 组装 HTML =====
const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920">
<title>Theme Sampler v5 · G10 契约布局 + 山禾集内容</title>
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
.split-anim .sp-unit{opacity:1!important;transform:none!important}
.amb-pulse,.amb-drift,.amb-glow{animation:none!important}
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
console.log('  Content: 山禾集业务汇报 (claim page)');
console.log('  Layout: G10 info_grammar.claim 契约驱动');
console.log('  Framework: gallery 骨架框架 CSS（padding/mastfoot/reveal/G9母题）');
console.log('  G5 colors: 赭石#E4C9A8 / 苔绿#8BAE6F / 暗夜蓝#1A2B3D');
