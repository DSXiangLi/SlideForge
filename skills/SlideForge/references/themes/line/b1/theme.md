# B1 瑞士国际主义

- **id**：b1
- **气质**：最经典的瑞士配色，绝不出错
- **适用**：通用场合、商业发布、AI/科技、设计领域
- **focus**：G1 + G9
- **世界参考**：1960 年代瑞士国际主义海报（Müller-Brockmann 网格体系）+ 瑞士铁路 signage 的加号与网格纪律
- **unforgettable**：加号角标 + 网格点阵——页面四角的细十字与版心网格，一眼瑞士
- **分化声明**：与 a1 分化于 L1/L2/L4/L5/L6——accent 是独立高亮色（非 ink）、无衬线倒挂字重、母题是加号/点阵/色块编号而非 Ghost 字、容器是直角色块而非无卡片、动效锐利短促而非慢显影

**G1 color**

```css
--paper:#fafaf8; --paper-tint:#f0f0ee;
--ink:#0a0a0a;   --ink-tint:#1a1a1a;
--accent:#002FA7; --accent-on:#ffffff;
```

- **高亮纪律**：accent 单页至多出现在一个视觉重心上
- **accent 预算**：内容页 accent 面积 ≤10%（与高亮纪律同口径）；满屏 accent 是封面/收束特权（归藏式 IKB 满版蓝 + 反白巨字）。首尾闭环：满版 IKB 封面（全亮）开场 → 收束页半亮呼应（IKB 通栏条带，或蓝底降明度 + 纸白文字）。

**G2 typography**

```css
--font-display:"Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：越大越细（大标题 200–300），越小越粗（正文/标签 500–700）
- **字号对比**：主标题:正文 ≥8:1（瑞士立场，巨字双约束 `min(Xvw, Yvh)` 限高）；高密度 ≥5:1
- **字重映射**：归藏倒挂阶梯：≥154px（≥8vw）→200；77–153px→200–300；35–76px→300–400；17–34px→400–500；14–16px→500–600；同页小字字重 ≥ 大字
- **标题修饰**：无
- **metric_fallback**：display→Helvetica Neue/Arial/Liberation Sans；body→PingFang SC/Noto Sans SC；mono→SF Mono/Menlo/DejaVu Sans Mono

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——瑞士版面靠纸白、网格与 hairline 建立秩序，任何纹理都是噪声

**G4 shape**

- **圆角**：0
- **hairline**：1px solid color-mix(in srgb, var(--ink) 18%, transparent)，配网格使用
- **阴影**：无
- **容器造型**：直角纯色块（四档明度照 §12）；编号用 accent 实心方块白字（单焦点纪律内）；描边框 1px hairline，给纸档锚点容器与图表区
- **高密度容器边界**：灰档 paper-tint 平涂色块面为主力——瑞士的容器是色块不是框；需要框的锚点容器走纸档 + 1px hairline，面与框同页不混（§12/§13 隔离纪律）

**G5 motion**

- **气质**：professional
- **强度上限**：默认
- **锚点偏好**：wipe-clip 精确揭示（标题/色块）+ count-up（数据页）——瑞士的动效是"对齐到网格的精确位移"，不是显影
- **节奏偏移**：时长档 −1（短促）；阶梯步长 ≤60ms
- **缓动签名**：覆盖 `--ease-out` 为更锐利的 cubic-bezier(.2,.9,.25,1)——快出急停
- **禁用**：blur-in / persp-in / mask-lines（模糊与柔缓不属于网格纪律）
- **fx 许可**：仅 ascii-field（归藏 IKB 封面字符呼吸场的正当先例；粒子类禁）

**G8 component**

- **亲和**：网格矩阵、数据英雄（图表/数字）、裂屏对开（双色对撞）
- **禁忌**：不用 Ghost 残影字（那是杂志系词汇）；轴与节点的时间轴必须严格水平或垂直，禁斜线引导

**G9 motif**

- **词汇**：加号角标（页面四角或内容区角上的细十字，14px，低透明，每页 ≤4 个）/ 网格点阵（封面或收束页背景，24px 点距）/ 色块编号（accent 实心方块 + 反白 mono 编号，替代圆点列表）

```css
/* B1 瑞士国际主义 · 装饰母题 + 缓动签名 */
:root{--ease-out:cubic-bezier(.2,.9,.25,1)}
.mt-cross{position:absolute;width:14px;height:14px;pointer-events:none;opacity:.55}
.mt-cross::before,.mt-cross::after{content:"";position:absolute;background:var(--ink)}
.mt-cross::before{left:50%;top:0;bottom:0;width:1px;margin-left:-.5px}
.mt-cross::after{top:50%;left:0;right:0;height:1px;margin-top:-.5px}
.mt-grid-dots{position:absolute;inset:0;pointer-events:none;background-image:radial-gradient(color-mix(in srgb,var(--ink) 18%,transparent) 1px,transparent 1.5px);background-size:24px 24px}
.mt-swatch{display:inline-flex;align-items:center;justify-content:center;min-width:2.2em;height:2.2em;background:var(--accent);color:var(--accent-on);font-family:var(--font-mono);font-weight:600}
```

- **禁忌**：加号只许四角与内容区角点，禁撒在页面中部；网格点阵只许仪式页；母题件一律 `data-editable-skip`

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约；`signature_operator` 必须通过 DOM 结构测试——删掉它，页面的元素数量 / 分组 / 顺序 / 位置会变，否则退回重写。
- **灵魂承载**：签名形状升级为信息容器（网格线作坐标、色块编号装数据）；形状由 CSS 承担（`data-editable-skip`），其内部承载文字仍是 `data-editable` 叶子节点——文字始终留在 DOM，不牺牲可编辑性，也不需整页生图。

```yaml
doctrine: 客观、去个人化；信息即形式，网格是理性秩序的可见化。
signature_operator: 把整页压进 12 栏网格（栏界以 hairline 可见化），标题跨栏语义断行并倒挂字重，
  其余信息沿栏吸附；把横向等权 KPI 重排成右侧纵向数据脊，只给一个数字一次 accent 面积事件。
silhouette: 横竖双轴；矩形分区；重心左上象限；右上 ≥25% 主动负空间。
info_grammar:
  cover:    ≤4 文本元素；满版 IKB + 反白发丝巨字
  claim:    左 7 栏巨字（200 字重、语义断行）+ 右 5 栏数据脊
  analysis: 3–6 块灰档平涂模块严格对格，至多一个 accent 焦点块
  data:     三项数字 → 纵向脊（非横排等权三格），仅一项用 accent 实色块承载
type_scale:            # 三级层级（480px 预览基准，单位 cqw）；任何文本不得低于 floor
  floor:   1.5         # ≈7.2px，唯一硬下限（真实 deck ~2.7x 后 ≈19px）
  display: 12.0        # 网格巨字（封面倒挂字重）；与标题拉开 ≥5 倍
  heading: 2.2         # 栏内小标题
  body:    1.8         # 说明 / 轴标 / 注脚（opacity ≥ .8，禁灰化弱读）
  rule: 标题:正文 ≈ 1.2–1.5:1，巨字:正文 ≥ 8:1（低密度）；禁层级倒挂与灰化弱读
invariants:
  - 主轴 ∈ {0°, 90°}，斜向结构件面积 = 0
  - 最大字号 / 最小字号 ≥ 8（低密度档）
  - 墨水重心 x ≤ 0.45
  - accent 实色面积 3–10%，且单页仅一处
  - 最大留白矩形位于右上，面积 ≥ 25%
forbidden_defaults: [三格等权 KPI, 居中 hero, 通栏长正文行 >70cqw, 卡片墙, 任何渐变]
dna_events: {cover: 强, claim: 强, analysis: 中, data: 强, divider: 中, closing: 中}
```

**bake_brief**

```json
{
  "visual_direction": "1960s Swiss International Style poster, Mueller-Brockmann grid discipline, hairline-thin giant grotesque type on warm white paper, crosshair registration marks, one International Klein Blue accent block, typographic poster as precision instrument, exhibition-print craft",
  "palette_rule": "warm white paper field and near-black ink carry the page; one accent hue under single-focus discipline — at most one visual center per page, full-bleed accent field is cover/closing privilege only; no second accent hue, no gradients, no color casts over the paper white",
  "typography_bake": "主标题重构词汇：倒挂字重即签名——巨字 200–300 细如发丝、同页小字 500–700 不弱于大字；字号对比 ≥8:1 即构图主体；基线与字距吸附不可见网格，网格对齐本身即装饰；断行按语义单元左对齐成块；隐喻融字只允许负空间网格化（字身骨架与网格线对位），禁笔画变形；拉丁小标签全大写宽字距",
  "uplift": "升维路径（HTML 做不到的物理维度）：高克重海报纸的物质性——纸面纤维微起伏与平整冷白；油墨的物理厚度——巨字发丝笔划边缘的着墨锐度、实地色块的微凸墨层；丝网印刷的工艺感——色块边缘绝对平直、单层专色的纯粹墨膜；纸面在展厅顶光下的极轻微明暗（纸张张力反光，不是渐变滤镜）——HTML 的扁平色块在此获得印刷工艺的物质性，而非立体化",
  "allowed": "hairline-thin giant grotesque type, strict invisible-grid alignment, crosshair registration marks at corners (at most four), dot grid on ritual pages, one solid accent square with reversed-out mono numbering, flat gray-step color blocks, precise hairlines, generous negative space, left-aligned semantic line-break blocks",
  "avoid": "gradients, shadows, rounded corners, 3D effects, texture overlays, ghost outline characters, serif type, ornamental decoration, icon rows, emoji, mesh gradients, aurora blobs, photorealism, diagonal or skewed composition, centered symmetric poster layout, multiple accent hues, cheap corporate template feel",
  "layout_blueprints": {
    "cover": [
      {"position": "top-left", "count": 1, "labels": ["mono 小字 meta 行（deck 名/日期）"]},
      {"position": "left, lower half", "count": 1, "labels": ["发丝级巨字主标题（倒挂字重、网格对齐、语义断行）"]},
      {"position": "single focal point", "count": 1, "labels": ["accent 实色方块焦点（可含反白 mono 编号）"]},
      {"position": "corners", "count": 4, "labels": ["加号角标（≤4，低透明）"]},
      {"position": "background", "count": 1, "labels": ["可选网格点阵（仪式页）"]}
    ],
    "divider": [
      {"position": "left", "count": 1, "labels": ["巨大章节序号（发丝字重 200）"]},
      {"position": "number block", "count": 1, "labels": ["accent 色块编号（反白 mono）"]},
      {"position": "below", "count": 2, "labels": ["一道 hairline", "一行章节题"]}
    ],
    "key-message": [
      {"position": "mid-left 70%", "count": 1, "labels": ["宣言句发丝巨字（语义断行块）"]},
      {"position": "single focal point", "count": 1, "labels": ["accent 焦点件（方块/编号）"]},
      {"position": "corners", "count": 2, "labels": ["加号角标"]},
      {"position": "bottom-left", "count": 1, "labels": ["可选一行 mono 小注"]}
    ],
    "analysis": [
      {"position": "top", "count": 1, "labels": ["标题 + hairline"]},
      {"position": "main grid", "count": 1, "labels": ["灰档平涂色块模块严格对格（3–6 件）"]},
      {"position": "inside grid", "count": 1, "labels": ["至多一个 accent 焦点模块"]},
      {"position": "side or bottom", "count": 1, "labels": ["mono 小注/图例编号"]}
    ]
  },
  "rendering_constraints": [
    "The page must read as a Swiss International Style exhibition poster, not a default corporate deck template.",
    "The inverted weight ladder is the signature: giant type hairline-thin (200-300), small type bolder — never reversed.",
    "Single accent focus per page; full-bleed accent only on cover/closing.",
    "Every element aligns to an invisible grid; arbitrary placement is failure.",
    "Flat print ink only: no gradients, no shadows, no 3D, no texture overlays beyond paper substance.",
    "Titles are left-aligned semantic line-break blocks; centered symmetric poster composition is forbidden.",
    "No ghost outline characters, no serif display type, no ornamental motifs — those belong to other themes.",
    "Cover/divider/key-message pages: at most 4 text elements; analysis pages: 3-6 grid-aligned flat blocks.",
    "Crosshair marks at most four, corners only; dot grid on ritual pages only.",
    "Do not invent logos, watermarks, or brand marks."
  ]
}
```

**Variants 配色变体**

#### 柠檬黄

- **气质**：浅色高亮，活力直接——年轻、运动、零售、消费品

```css
--paper:#fafaf8; --paper-tint:#f0f0ee;
--ink:#0a0a0a;   --ink-tint:#1a1a1a;
--accent:#FFD500; --accent-on:#0a0a0a;
```

#### 柠檬绿

- **气质**：荧光感高亮，适合屏幕与投影——生态、可持续、健康、新兴科技、Z 世代品牌

```css
--paper:#fafaf8; --paper-tint:#f0f0ee;
--ink:#0a0a0a;   --ink-tint:#1a1a1a;
--accent:#C5E803; --accent-on:#0a0a0a;
```

- **accent 预算**：荧光绿满版仅封面，投影场景慎用；其余同基底口径

#### 安全橙

- **气质**：工业感高亮，警告/转折/重点专用——工业、运动、技术发布会的"警告/转折/重点"页

```css
--paper:#fafaf8; --paper-tint:#f0f0ee;
--ink:#0a0a0a;   --ink-tint:#1a1a1a;
--accent:#FF6B35; --accent-on:#ffffff;
```

- **accent 预算**：**不满屏**——满版橙过于刺眼，封面/收束的特权形态是橙色通栏条带（高度 ≤20%）；首尾闭环为同位条带呼应

---

## C 系 · 深色与个性（源自 frontend-slides）

C 系补充暗色与强个性方向。暗色主题中 `.slide.dark` 变体的角色反转：默认页即暗页。
