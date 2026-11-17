# E2 蓝图

- **id**：e2
- **气质**：硫酸纸深蓝底 + 白线 + 尺寸标注，工程制图的精确、复写感与"可施工"的权威
- **适用**：工程/建筑/制造、技术方案与架构汇报、基础设施、产品规格书、流程严谨的交付文档
- **focus**：G3 + G9
- **世界参考**：建筑工程蓝图（cyanotype 氰版晒图）——硫酸纸蓝底白线、双向箭头尺寸标注、右下角图框标题栏、绘图网格纸
- **unforgettable**：尺寸标注线——双向箭头 dimension line 加两端延伸线，把图与尺寸缝在一起，一眼工程制图
- **分化声明**：与 b1 分化于 L1/L3/L4/L5——b1 是纸白底高亮色的 flat 平色世界，母题是加号角标/网格点阵/色块编号，容器是直角纯色块；e2 是深蓝底白线世界，制图网格纸质感全页铺底（paper/all vs flat/cover），母题是尺寸标注线/双线图框/图框标题栏，容器是 1px 双线图框

**G1 color**

```css
--paper:#14304a; --paper-tint:#1b3d5c;
--ink:#f2f6f9;   --ink-tint:#0f2438;
--accent:#35C8E8; --accent-on:#0e2a3f;
```

- **accent 预算**：内容页 accent 面积 ≤5%（亮青是蓝图上最亮的那支笔——只给尺寸线箭头、图签、关键数字标注）；满屏 accent 禁止——蓝图的世界里满版只有蓝底，没有满版青色；首尾闭环：封面白线巨标 + 亮青图签开场 → 收束页同位亮青标注/图签呼应。

**G2 typography**

```css
--font-display:"Helvetica Neue","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 500–600 恒重 + 拉丁大写字距拉开（工程字一手写体制图字体），正文 400；图注/图号/尺寸一律 mono
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：工程字恒重立场（不走倒挂——蓝图上一套字管到底，层级靠字号与线宽不靠字重）：标题 600；副标/区块标 500–600；正文 400；标注/图号 mono 400–500；14–16px 小字 500
- **标题修饰**：拉丁标题全大写 + letter-spacing 拉开；图签编号 mono 前缀（"DWG-A1 / SCALE 1:50" 式，见 G9 `.mt-bp-tag`）

**G3 texture**

```css
--texture-type: paper;
--texture-layer: repeating-linear-gradient(0deg, color-mix(in srgb, var(--ink) 5%, transparent) 0 1px, transparent 1px 7px), repeating-linear-gradient(90deg, color-mix(in srgb, var(--ink) 5%, transparent) 0 1px, transparent 1px 7px), repeating-linear-gradient(0deg, color-mix(in srgb, var(--ink) 12%, transparent) 0 1px, transparent 1px 35px), repeating-linear-gradient(90deg, color-mix(in srgb, var(--ink) 12%, transparent) 0 1px, transparent 1px 35px);
--texture-scope: all;
```

- **立场**：制图网格纸 = 材质本体——蓝图全部画在网格纸上（7px 细格 + 35px 主格双向细白线），全页许可（scope all），正文页也铺，但仍需生成侧逐页 `texture-on` 落码

**G4 shape**

- **圆角**：0（图框一律直角，制图没有圆角）
- **hairline**：1px solid color-mix(in srgb, var(--ink) 45%, transparent)——白线即墨线；线在这个主题里是制图工具：尺寸线、延伸线、图框线、剖面线
- **阴影**：无
- **容器造型**：1px 双线图框容器——外框 + 内缩 5px 第二道细线（`.mt-bp-frame` 落码），右下角钉图框标题栏（`.mt-bp-tag`：图号/比例/日期 mono 小字）；禁圆角卡、禁阴影、禁玻璃拟态、禁满版色块卡
- **高密度容器边界**：双线图框（`.mt-bp-frame`）成阵即边界——图纸世界的容器生来带框；图框标题栏钉右下角，框与框同距同构，禁图框套图框（G9 禁忌同口径）

**G5 motion**

- **气质**：professional
- **强度上限**：默认
- **锚点偏好**：draw-line 为签名锚点——尺寸线/图框/折线图像被绘图笔逐段画出；标题入场 wipe-clip 精确揭示（制图的对齐感）；数字以 mono 直排 + 标注线呈现，count-up 只给真正的规格英雄页
- **节奏偏移**：时长档默认（制图是精确不是迟缓，也不是抢）；阶梯步长 ≤60ms
- **缓动签名**：默认三 token，不覆盖（精确感由 draw-line 的描绘节奏承担）
- **禁用**：scale-pop / persp-in（弹跳与透视翻转不属于图板）
- **fx 许可**：全禁（蓝图是纸面世界，无像素仪式）

**G8 component**

- **亲和**：轴与节点（流程图/系统图 = 工程图的原生形态，节点即构件）、数据英雄（规格大数字 + 标注线）、网格矩阵（器件明细表/参数表）
- **禁忌**：禁手绘/有机形态（撕边、笔触、晕染都不是制图）；裂屏对开慎用——图框是完整单页，禁把图框劈开；不用加号角标/网格点阵（瑞士系词汇）——本主题的角部词汇是延伸线与图框角

**G9 motif**

- **词汇**：尺寸标注线（`.mt-bp-dim`：双向箭头 hairline + 居中 mono 尺寸注记，两端可带延伸线——工程制图词汇，与 c2 的标本引线 `.mt-bot-lead` 不同源：那是渐隐装饰引线，这是双向箭头的度量工具）/ 双线图框（`.mt-bp-frame`：外 1px + 内缩 5px 细线，图纸边框）/ 图框标题栏（`.mt-bp-tag`：钉在图框右下角的 mono 分格小签——图号/比例/日期，每页至多一个）

```css
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
```

- **禁忌**：尺寸线只标真实结构（容器/图/关键间距），禁无对象空挂——标注是度量不是装饰；标题栏只许右下角、每页至多一个；双线图框禁嵌套（图框套图框即图纸事故）；母题件一律 `data-editable-skip`

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：尺寸标注线和双线图框是签名结构件，形状由 CSS 承担（data-editable-skip），其内部承载的文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，页面回到「标题 + 两段正文 + 横排三格 KPI」，制图网格纸底纹、尺寸标注线、双线图框阵列、图框标题栏全部消失，元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 可施工的权威——蓝图不是展示，是施工依据；每条线都在度量，每个框都是图纸。

page_composition:
  skeleton: 双线图框阵列（图框成阵即分区，全页铺制图网格纸）
  grid: {margin: 96, gutter: 32}
  balance: {anchor: 主图框(主信息区), counterweight: 标注线/标题栏(右下角)}
  whitespace_ratio: "≥30%"
  flow: "图框承载信息 → 标注线缝合图与尺寸 → 标题栏钉右下角做图签"
signature_operator: 把每条信息编译成一个双线图框或一组尺寸标注——
  核心信息装进双线图框（外 1px + 内缩 5px 第二道细线），图框成阵即分区；
  标题在图框内或跨图框，拉丁全大写宽字距，恒重 600（不走倒挂）；
  数字以 mono 直排 + 标注线呈现（双向箭头 hairline + 居中 mono 尺寸注记），count-up 只给规格英雄页；
  三项数字重排为图框阵列中的标注行（key:value 式），非横排等宽三格；
  图框标题栏（mono 分格小签：图号/比例/日期）钉在右下角，每页至多一个；
  制图网格纸（7px 细格 + 35px 主格双向白线）全页铺底，正文页也铺。
silhouette: 图框阵列构图；矩形双线框成阵；水平/垂直主轴（制图网格）；重心均匀分布；暗蓝底白线。
info_grammar:
  cover:    满版蓝底 + 白线巨标 + 亮青图签（封面特权），制图网格全页铺
  toc:      3–5 个双线图框阵列排列，当前章节用亮青标注线标记
  claim:    主张句在主图框内，标注线指向关键数据点，标题栏钉右下
  analysis: 2–4 个同构双线图框成阵（同 gap 同 padding），每框承载一段信息
  data:     三项数字 → 图框内 mono key:value 标注行，主数字用亮青标注线强调
  closing:  蓝底 + 亮青图签呼应封面，制图网格最后一次铺满
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 104px  # 工程字恒重 600 承载图框压强；与正文 3.7:1
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读；accent 亮青面积 ≤5%（只给标注线箭头/图签/关键数字）
  floor_note: body/heading/subhead/caption/meta 不覆盖，继承骨架 28/64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 双线图框 ≥2 个/页（外 1px + 内缩 5px 细线），图框成阵即分区
  - 尺寸标注线只标真实结构（容器/图/关键间距），禁无对象空挂
  - 图框标题栏每页至多一个、只钉右下角
  - 制图网格纸全页铺底（scope: all），7px 细格 + 35px 主格双向白线
  - 全栈等宽倾向：标注/图号/尺寸一律 mono，标题/正文 sans-serif 恒重 600
  - 横排等权三格容器数 = 0
  - 禁圆角、禁阴影、禁满版色块卡——图框是直角中空双线框
forbidden_defaults: [横向等权三格 KPI, 卡片墙成阵, 居中 hero, 弥散软影, 渐变色块, 玻璃拟态, 圆角卡, 满版色块, hairline 发丝线（本主题的线是 1px 制图线不是装饰线）]
dna_events: {cover: 强, claim: 中, analysis: 中, data: 强, toc: 中, closing: 中}
```

---

**Variants 配色变体**

#### 反相蓝图

- **气质**：蓝线白底的晒图反相——从硫酸纸回到绘图板，更亮更文档化，适合打印交付与正式评审

```css
--paper:#f4f7f9; --paper-tint:#e5ecf1;
--ink:#14304a;   --ink-tint:#27455e;
--accent:#0E7D99; --accent-on:#f4f7f9;
```

#### 黑板粉笔

- **气质**：深灰黑板 + 白粉笔线 + 粉笔黄标注——制图前的推演现场，适合方案推演、教学、头脑风暴复盘

```css
--paper:#232a30; --paper-tint:#2d353c;
--ink:#e9edf0;   --ink-tint:#161b1f;
--accent:#E3C85C; --accent-on:#232a30;
--texture-type: grain;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.06'/%3E%3C/svg%3E"), repeating-linear-gradient(0deg, color-mix(in srgb, var(--ink) 6%, transparent) 0 1px, transparent 1px 7px), repeating-linear-gradient(90deg, color-mix(in srgb, var(--ink) 6%, transparent) 0 1px, transparent 1px 7px);
```

- **accent 预算**：粉笔黄是黑板上唯一的彩色粉笔——标注纪律不变（≤5%），粉笔尘颗粒感强于基底网格；其余同基底口径
