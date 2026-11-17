# E9 地质地层

- **id**：e9
- **气质**：白昼大地剖面——纸米底上铺开赭石层理与等高线，像摊开一张地质调查图：精确、沉稳、有岩石的时间厚度
- **适用**：地质/考古/历史纵深、组织架构与层级、演进与成因类内容，研究型叙事，自然与人文地理
- **focus**：G3 + G9
- **世界参考**：地质调查剖面图与岩芯样本档案——层理条纹、地质年代色标、等高线圈、钻孔取出的岩芯圆柱
- **unforgettable**：层理色带——页面底缘（或侧缘）横贯一条大地色水平层理带，层厚可对应数据比例，是层级/组成内容的天然隐喻（与 references/motifs.md「地层剖面」隐喻同构）
- **分化声明**：与 a1 分化于 L2/L4/L5/L7——e9 是 sans display + mono 标注的科学绘图字排、a1 是衬线杂志字排；e9 母题是层理色带/岩芯样本条/等高线圈、a1 是 Ghost 巨字/竖排题字条；e9 容器是直角薄色层剖面切片、a1 是无卡片立场；e9 构图亲和轴与节点与地层剖面隐喻、a1 亲和巨字宣言（L1 与 a1 沙丘变体同为大地调，但本声明对 a1 基底核验——基底是墨黑双色，四层全真）

**G1 color**

```css
--paper:#f0e9d8; --paper-tint:#e3d9c3;
--ink:#2c251d;   --ink-tint:#413729;
--accent:#a85a2a; --accent-on:#f0e9d8;
```

- **accent 预算**：内容页 accent 面积 ≤10%（赭石只给测绘关键标注：地层界线、岩芯主层段、年代标尺当前段、关键数字；层理色带的大面积色层用 accent/ink 向 paper 的 color-mix 淡阶，不计入预算）；满屏 accent 禁止——大地没有荧光时刻，封面/收束的特权形态是层理色带加高至页底 30%；首尾闭环：封面底部厚层理色带开场 → 收束页同层序薄色带呼应。

**G2 typography**

```css
--font-display:"Avenir Next","Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"JetBrains Mono","SF Mono","Menlo",monospace;
```

- **字重倾向**：标题 600–700、正文 400——科学绘图的权威来自标注体系的清晰，不靠细字的优雅
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：sans 恒重立场（不走倒挂——图签标题要立得住）：≥77px→600–700；35–76px→600；正文 400；14–16px 小字 500–600
- **标题修饰**：无（修饰交给 mono 年代标注与等高线，不进标题）

**G3 texture**

```css
--texture-type: grain;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E");
--texture-scope: all;
```

- **立场**：岩石颗粒 = 材质本体——切片、岩芯、断口全是颗粒，全页许可（scope all）；正文页仍需生成侧逐页 `.texture-on` 落码，强度烧死不得加深（颗粒是岩石，不是沙暴）

**G4 shape**

- **圆角**：0（岩层是切出来的，一刀切齐）
- **hairline**：1px solid color-mix(in srgb, var(--ink) 28%, transparent)，承担地层界线与图廓线——线在这个主题里是测绘工具，不是装饰
- **阴影**：无
- **容器造型**：剖面切片——直角薄色层容器（paper-tint 或 accent color-mix 淡阶的纯色薄层，像从剖面上切下的一片地层），顶缘可压 2px accent 界线作"地表线"；禁圆角、禁阴影、禁玻璃拟态
- **高密度容器边界**：直角薄色层面 + 图廓线收边——切片色层是"面"，1px 图廓 hairline（ink 28%，测绘图廓的本世界形态）给需要框的容器收边；同页面框不混，剖面切片阵为主力

**G5 motion**

- **气质**：calm
- **强度上限**：低
- **锚点偏好**：draw-line 为签名锚点——等高线与地层界线的测绘描绘感，剖面图页/年代轴页优先；标题入场用默认阶梯或 rise-in，克制
- **节奏偏移**：时长档 +1（地质时间的尺度，急不得）；阶梯步长 ≥90ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：无（calm 气质本身排除弹跳与硬切）
- **fx 许可**：全禁（canvas 仪式层是夜空与终端的词汇，白昼大地剖面不点灯）

**G8 component**

- **亲和**：轴与节点（地质年代轴/演进——年代标尺是它的原生形态）、层级与组成内容（层理色带 = 地层剖面隐喻，与 motifs.md 同构）、图文证据（标本/剖面图 + 测绘标注）
- **禁忌**：禁圆角卡片阵与弥散阴影（那是奶油系词汇）；巨字宣言慎用——图鉴版面靠测绘精度建立权威，不靠巨字压场

**G9 motif**

- **词汇**：层理色带（`.mt-geo-strata`：页底或侧缘横贯的大地色水平层理带，色层从 accent/ink/paper-tint 用 color-mix 派生大地阶梯，层厚比例由生成侧按数据调整 gradient 断点）/ 岩芯样本条（`.mt-geo-core`：竖向圆柱感色条 = 年代标尺，分段色对应地质年代，段界比例由生成侧调整）/ 等高线圈（`.mt-geo-contour`：细线同心闭合曲线，低透明背景装饰，只许页角与留白区）/ 年代标注签（`.mt-geo-tag`：mono 小字 + accent 短横引线，标注年代/层位/海拔）

```css
/* E9 地质地层 · 装饰母题 */
.mt-geo-strata{position:absolute;left:0;right:0;bottom:0;height:10%;pointer-events:none;border-top:1px solid color-mix(in srgb,var(--ink) 34%,transparent);background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 28%,var(--paper)) 0 24%,color-mix(in srgb,var(--ink) 14%,var(--paper)) 24% 42%,color-mix(in srgb,var(--accent) 48%,var(--paper)) 42% 55%,var(--paper-tint) 55% 78%,color-mix(in srgb,var(--ink) 30%,var(--paper)) 78%)}
.mt-geo-core{width:20px;border-radius:10px;border:1px solid color-mix(in srgb,var(--ink) 32%,transparent);background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 62%,var(--paper)),color-mix(in srgb,var(--accent) 26%,var(--paper)) 38%,color-mix(in srgb,var(--ink) 18%,var(--paper)) 62%,color-mix(in srgb,var(--ink) 40%,var(--paper)))}
.mt-geo-contour{position:absolute;pointer-events:none;width:340px;height:340px;border-radius:50%;opacity:.5;background:repeating-radial-gradient(circle at 50% 50%,transparent 0 27px,color-mix(in srgb,var(--ink) 20%,transparent) 27px 28px)}
.mt-geo-tag{display:inline-flex;align-items:center;gap:.6em;font-family:var(--font-mono);font-size:12px;letter-spacing:.2em;color:color-mix(in srgb,var(--ink) 66%,transparent)}
.mt-geo-tag::before{content:"";width:14px;height:1px;background:var(--accent)}
```

- **禁忌**：层理色带每页至多一条（页底或侧缘二选一，横放），禁压正文；等高线圈禁横穿正文区、禁与岩芯条同页抢焦；岩芯条只许年代/层级语义处，禁当纯装饰撒布；母题件一律 `data-editable-skip`

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：层理色带（.mt-geo-strata）和岩芯样本条（.mt-geo-core）是签名结构件，形状由 CSS 承担（data-editable-skip），其内部承载的文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，页面回到「标题 + 两段正文 + 横排三格 KPI」，层理色带、岩芯条、等高线圈、年代标注签全部消失，元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 大地剖面即叙事——每条信息是地质调查图上的一个层位或标注，时间是这里的主轴，精确的测绘比花哨的视觉更有说服力。

page_composition:
  skeleton: 剖面切片阵——直角薄色层容器在纸米底上按层序排列，页底横贯层理色带
  grid: {margin: 96px 120px, gutter: 32px}
  balance: {anchor: 剖面切片阵(主信息区), counterweight: 层理色带(页底) / 等高线圈(页角留白)}
  whitespace_ratio: ">=40%"
  flow: "年代标注签定锚 → 剖面切片承载核心信息 → 岩芯样本条做年代标尺 → 等高线圈页角装饰 → 层理色带页底收束"
signature_operator: 把每条信息编译成地质调查图上的一个层位——
  核心信息装进剖面切片（直角薄色层容器：paper-tint 或 accent color-mix 淡阶纯色薄层，顶缘可压 2px accent 界线作"地表线"）；
  主张句在切片内 sans 大字，年代标注签（.mt-geo-tag：mono 小字 + accent 短横引线）标注层位/年代；
  三项数字重排为层理色带上的分段标尺（非横排等权三格），主数字独占一段 accent 淡阶色层；
  岩芯样本条（.mt-geo-core）只许年代/层级语义处，竖向圆柱感色条分段对应地质年代；
  等高线圈（.mt-geo-contour）只许页角与留白区低透明装饰；
  页底或侧缘横贯一条层理色带（.mt-geo-strata），层厚比例由数据调整 gradient 断点。
silhouette: 纸米底上剖面切片阵 + 页底层理色带；直角薄色层矩形块面；重心偏上（切片阵区）；底部色带做大地基座。
info_grammar:
  cover:    满版纸米底 + 底部厚层理色带（页底 30%）+ sans 大字标题 + 年代标注签钉页角
  toc:      3-5 个剖面切片按层序排列，当前章节用 accent 界线标记
  claim:    剖面切片阵承载主张句（切片内 sans 大字 + 年代标注签引线注），层理色带在页底做层序呼应
  analysis: 2-4 个同构剖面切片在纸米底上，每个承载一段信息，至多一张切片用 accent 界线焦点
  data:     三项数字 → 层理色带上分段标尺排列，主数字独占 accent 淡阶色层段
  closing:  纸米底 + 底部薄层理色带呼应封面（色带高度减半），年代标注签最后一次出现
type_scale:            # px@1920x1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 104px  # sans 600-700 承载测绘图签标题；与正文 3.7:1
  rule: 标题:正文 >=1.8:1；正文层 opacity = 1，禁灰化弱读；accent 赭石面积 <=10%（只做界线/标注/关键数字）；层理色带大面积色层用 color-mix 淡阶不计入预算
  floor_note: body/heading/subhead/caption/meta 不覆盖，继承骨架 28/64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 剖面切片直角薄色层容器（paper-tint 或 accent color-mix 淡阶），顶缘可压 2px accent 界线，无阴影
  - 纸米底（--paper #f0e9d8）+ 赭石 accent（#a85a2a），accent 面积 <=10%
  - 层理色带每页至多一条（页底或侧缘二选一），禁压正文
  - 横排等权三格容器数 = 0
  - 等高线圈禁横穿正文区、禁与岩芯条同页抢焦
  - 岩芯条只许年代/层级语义处，禁当纯装饰撒布
forbidden_defaults: [横向等权三格 KPI, 卡片墙成阵, 居中 hero, 圆角卡, 弥散软影, 渐变色块, 玻璃拟态, 满版色块, 荧光高亮, 手绘/有机形态]
dna_events: {cover: 强, claim: 中, analysis: 弱, data: 中, toc: 弱, closing: 强}
```

**Variants 配色变体**

#### 岩灰蓝

- **气质**：灰蓝色调的石灰岩与页岩层——更冷、更克制，像阴天野外的测绘现场，适合工程/基建/数据基础设施叙事

```css
--paper:#eeebdf; --paper-tint:#e1dcc9;
--ink:#2c2b26;   --ink-tint:#403e35;
--accent:#5f7482; --accent-on:#eeebdf;
```

#### 红土

- **气质**：红土高原与氧化铁层——更暖、更荒原，适合考古/文明/迁徙/远征类叙事

```css
--paper:#f2e6d2; --paper-tint:#e5d6ba;
--ink:#2e211a;   --ink-tint:#453024;
--accent:#a63f2a; --accent-on:#f2e6d2;
```

- **accent 预算**：红土红与层理色带同属暖域，色带淡阶与 accent 标注的明度差要拉大（淡阶混色 ≤35%），其余同基底口径
