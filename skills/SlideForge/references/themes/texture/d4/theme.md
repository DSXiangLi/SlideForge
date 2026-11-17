# D4 黄铜年代 Brass Age

- **id**：d4
- **气质**：涂漆钢板 + 黄铜刻线 + 红色标注——1950s 世博会工业乐观主义，钢铁的时代相信未来
- **适用**：科技发布 / 工程 / 制造 / 基础设施 / 航天 / 工业品牌
- **focus**：G9 + G3
- **世界参考**：1950s 世界博览会展馆海报与太空时代工业设计——涂漆钢板、黄铜铆钉、丝网印刷宣传画
- **unforgettable**：黄铜刻线框——双线黄铜色刻痕边框，内凹刻槽感，每个容器像从钢板上刻出来的
- **分化声明**：与 e2 分化于 L1/L2/L3/L4/L5/L6——d4 暖调黄铜 + 炭灰钢板 + 红色标注三墨世界，e2 冷调青蓝 + 深蓝图纸 + 白线单墨；d4 标题是 condensed grotesk 恒重工业字，e2 是工程手写体大宽字距；d4 质感是钢板漆面微颗粒（grain/cover 仪式页），e2 是制图网格纸全页铺底（paper/all）；d4 母题是黄铜铆钉/刻槽线框/红色标注章/疏格钢板网，e2 是尺寸标注线/双线图框/图框标题栏；d4 容器是黄铜刻线框带内凹刻槽影，e2 是 1px 双线图框无影；d4 动效签名是 wipe-clip 精确揭示 + count-up 工程数据，e2 是 draw-line 绘图笔描绘
- **material_world**：1950s 世界博览会展馆——涂漆钢板墙面上铆着黄铜配件，丝网印刷宣传画盖着微微倾斜的红色批注章（HTML 版是这个世界的线框图，bake 版是这个世界的高清照片）
- **anti_lazy**：不要因为是工业主题就堆齿轮/管线元素——黄铜年代的语言是刻线、铆钉与钢板，不是 steampunk 齿轮墙；不要把黄铜做成金色渐变金属字——黄铜是配件材料（刻线/铆钉/边框），不是滤镜质感；不要滑向赛博/科幻蓝——这是 1950s 的乐观工业，不是未来主义；不要用蓝图纸做底色——那是 E2 蓝图的世界，D4 的底是涂漆钢板

**G1 color**

```css
--paper:#1c1c1e; --paper-tint:#28282b;
--ink:#e8dcc8;   --ink-tint:#4a4a50;
--accent:#b8860b; --accent-on:#1c1c1e;
--accent-2:#c0392b; --accent-2-on:#e8dcc8;
```

- **accent 预算**：黄铜是结构金属不是颜料——内容页 accent 面积 ≤6%（刻线框、铆钉、刻度、关键数字），禁大面积黄铜填充；满屏特权：封面/收束页可用满幅刻线框 + 疏格钢板网仪式背景；首尾闭环：封面黄铜刻线巨框开场 → 收束页同位刻线框（缩小或半隐）呼应。
- **多色立场**：双色墨封闭色板——`--accent` 黄铜（结构：刻线/铆钉/刻度/焦点数字）+ `--accent-2` 标注红（批注：印章/评审标记/警示注记），禁引入第三彩色；分配规则：黄铜承担结构与焦点、红色只承担批注意图（`.mt-brs-stamp` 与评审标注专用），红色面积 ≤3% 且单页至多 2 处；两色永不做大面积色面。
- **暗底 token 语义**：`--ink-tint` 是钢板上的弱刻痕色（比 paper 浅的暖灰），用于次级分隔线/弱化标注，不作正文文字色；正文与标题一律 `--ink`。

**G2 typography**

```css
--font-display:"Franklin Gothic Medium","Arial Narrow","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 600–700 恒重（condensed grotesk 的工业重量感，不走倒挂），正文 400；编号/标注/图签一律 mono
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：工业恒重立场（层级靠字号与刻线结构，不靠字重渐变）：≥77px→700；35–76px→600–700；正文 400；14–16px 小字 500；KPI 数值 ≥700
- **标题修饰**：拉丁标题全大写 + letter-spacing 拉开（.08–.16em，展馆海报字距）；kicker 行 = mono 黄铜色小字 + 项目编号式前缀（"EXPO-58 / HALL 2"式）

**G3 texture**

```css
--texture-type: grain;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='f'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.55 0.75' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23f)' opacity='0.05'/%3E%3C/svg%3E");
--texture-scope: cover;
```

- **立场**：钢板漆面的微颗粒 = 材质本体，但只许仪式页铺底（cover 纪律）——正文页的材料感由刻线框/铆钉/印章承担，钢板面退后保持干净
- **material**：涂漆钢板 + 黄铜铆钉——钢板漆面平整有微弱方向性反光与橘皮微肌理，黄铜件有金属高光
- **light**：展馆顶灯——均匀但有微弱方向性（自上而下），金属面有高光，刻槽有内凹阴影
- **css_recipes**：["engraved-line", "halftone-dots", "aged-fade", "paper-fiber"]

**G4 shape**

- **圆角**：0（钢板与图纸都是直角裁切，圆角不属这个世界）
- **hairline**：1px solid color-mix(in srgb, var(--ink-tint) 65%, transparent)——蓝图弱墨线，用于次级分隔；结构线一律黄铜刻线（G9）
- **阴影**：无弥散影；唯一允许的"影"是刻槽内凹影（engraved-line 配方：inset 深线 + 受光亮边）
- **容器造型**：黄铜刻线框直角容器——`border: 2px solid` 黄铜 + `outline: 1px solid; outline-offset: 3px` 第二道细刻线 + inset 刻槽影（`.mt-brs-engrave` 落码），四角可钉铆钉；禁圆角、禁弥散阴影、禁玻璃拟态、禁满版色块卡
- **高密度容器边界**：黄铜刻线框成阵即边界——框与框同距同构、等大开排，铆钉钉角对齐；禁刻线框套刻线框（内外两层即图纸事故）

**G5 motion**

- **气质**：professional
- **强度上限**：默认
- **锚点偏好**：wipe-clip 精确揭示为签名——标题与刻线框像蓝图沿裁切线展开；count-up 给工程数据/KPI 英雄页；draw-line 可给刻线框与图表描线做副锚点
- **节奏偏移**：时长档默认（工业的精确感：不拖不抢）；阶梯步长 60–90ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / persp-in / blur-in（弹跳、透视翻转与柔焦显影都不属于钢板；blur-in 是 d2 暗房的签名）
- **fx 许可**：全禁（刻线与铆钉已是仪式，canvas 会让它变廉价）

**G8 component**

- **亲和**：网格矩阵（器件明细表/参数表/展馆导览——网格是工程图的原生形态）、轴与节点（工艺流程/系统架构，节点即构件）、数据英雄（规格大数字 + 刻线框 + 铆钉角）
- **禁忌**：禁手绘/有机形态（撕边、晕染、笔触都不是工业）；裂屏对开慎用——钢板是完整单页，禁把刻线框劈开；不用加号角标/网格点阵（瑞士系词汇）与尺寸标注线/图框标题栏（e2 蓝图词汇）——本主题的角部词汇是铆钉与刻线框

**G9 motif**

- **词汇**：黄铜铆钉（`.mt-brs-rivet`：8px 金属球面渐变圆点，钉在刻线框四角或分隔线端点，每容器至多 4 枚）/ 刻线框（`.mt-brs-engrave`：2px 黄铜 border + 1px outline 双刻线 + inset 刻槽影，容器与整页内框两用）/ 红色标注章（`.mt-brs-stamp`：accent-2 红 2px 描边 + rotate(-3deg) 微倾斜 + mono 大写短词，如 "APPROVED"/"REV.B"——文本载体类母题，文字保持可编辑）/ 疏格钢板网（`.mt-brs-grid`：56px 单级疏格 ink 5% 线，只许仪式页背景）

```css
/* D4 黄铜年代 · 装饰母题 */
.mt-brs-rivet{position:absolute;width:8px;height:8px;border-radius:50%;pointer-events:none;background:radial-gradient(circle at 34% 30%,color-mix(in srgb,var(--accent) 42%,var(--ink)),var(--accent) 55%,color-mix(in srgb,var(--accent) 52%,var(--paper)));box-shadow:0 1px 1px color-mix(in srgb,var(--paper) 82%,transparent)}
.mt-brs-engrave{border:2px solid color-mix(in srgb,var(--accent) 72%,transparent);outline:1px solid color-mix(in srgb,var(--accent) 38%,transparent);outline-offset:3px;box-shadow:inset 0 1px 2px color-mix(in srgb,var(--paper) 75%,transparent),inset 0 -1px 0 color-mix(in srgb,var(--accent) 25%,transparent)}
.mt-brs-stamp{display:inline-block;padding:.32em .85em;border:2px solid color-mix(in srgb,var(--accent-2) 85%,transparent);color:var(--accent-2);font-family:var(--font-mono);font-size:12px;letter-spacing:.18em;text-transform:uppercase;transform:rotate(-3deg)}
.mt-brs-grid{position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,color-mix(in srgb,var(--ink) 5%,transparent) 0 1px,transparent 1px 56px),repeating-linear-gradient(90deg,color-mix(in srgb,var(--ink) 5%,transparent) 0 1px,transparent 1px 56px)}
```

- **禁忌**：铆钉只钉刻线框角或线端，禁漂浮散布、每容器 ≤4 枚；刻线框禁嵌套、禁配弥散影；标注章只许 2–4 个拉丁大写短词、每页至多 2 枚、禁压正文（是批注不是标语）；疏格钢板网只许仪式页背景、禁与 e2 式制图细格混用；母题件一律 `data-editable-skip`（`.mt-brs-stamp` 为文本载体例外——样式由类承担，文字保持可编辑）

**bake_brief**

```json
{
  "visual_direction": "1950s World's Fair pavilion poster and space-age industrial optimism — lacquered steel panels, brass rivets and engraved trim, silkscreen exhibition graphics, a slightly tilted red annotation stamp, the earnest confidence of an era that believed in the future",
  "palette_rule": "brass is structural metal, not paint: it appears only as engraved lines, rivets, frames, tick marks and focal numerals (≤6% area); annotation red is a second sealed ink reserved for stamps and review marks only (≤3%, at most two per page); the ground stays dark lacquered steel charcoal, text stays warm ivory; forbid large brass fills, gold gradient metallic type, any third chromatic hue, blueprint navy ground (that is E2 territory), cyber/neon blue, and steampunk brown overload",
  "typography_bake": "主标题重构词汇：展馆招牌字——condensed grotesk 恒重大写拉丁，字距拉开如展馆门楣铸字；刻字感——标题笔画边缘带刀刻的微妙锐利感，像从钢板上凿出而非印出；铜版镶嵌——关键词字可嵌入黄铜刻线框内，字面与框有铆钉固定的前后层次；编号前缀——mono 项目编号式 kicker（EXPO-58 / HALL 2 式）钉在标题上方；断行在语义边界，中文标题保持 condensed 气质的紧凑中宫",
  "uplift": "升维路径（HTML 做不到的物理维度）：涂漆钢板的漆面反光——顶灯下钢板有微弱方向性光泽与漆面橘皮微肌理；黄铜铆钉的球面高光——每颗铆钉有金属的环状反光与铆接阴影；刻线的物理凹槽——刻痕是钢板上的真实凹槽，有槽底暗线与槽缘亮边；红色标注章的印泥质感——章面边缘有印泥的轻微洇散与压力不均，章体微倾斜",
  "material_anchor": "lacquered steel panel + brass rivets and engraved trim + silkscreen poster ink + rubber-stamp red annotation",
  "viewing_sequence": [
    "第一眼：深炭钢板上黄铜刻线框与标题剪影——先感到展馆的工业秩序与黄铜光泽",
    "第二眼：发现铆钉高光、刻槽凹凸、漆面微颗粒与红色批注章——材料的物理细节",
    "第三眼：阅读参数与数据，感受那个年代对工程的笃定——信息如铭牌般可信"
  ],
  "anti_lazy": [
    "不要因为是工业主题就堆齿轮/管线元素——黄铜年代的语言是刻线、铆钉与钢板，不是 steampunk 齿轮墙",
    "不要把黄铜做成金色渐变金属字——黄铜是配件材料（刻线/铆钉/边框），不是滤镜质感",
    "不要滑向赛博/科幻蓝——这是 1950s 的乐观工业，不是未来主义",
    "不要用蓝图纸做底色——那是 E2 蓝图的世界，D4 的底是涂漆钢板"
  ],
  "allowed": "brass engraved double-line frames with inner groove shadow, brass rivets pinned at frame corners, slightly tilted red rubber-stamp annotations (two to four uppercase mono words), coarse steel grid on ritual backgrounds, tick marks and scale rules, condensed grotesque uppercase Latin display type, mono project-number kickers, specification tables and parameter grids, exploded-diagram and section-view compositions, halftone silkscreen tonal patches",
  "avoid": "gears and steampunk clutter, gold gradient metallic type, blueprint navy ground (E2 territory), neon or cyberpunk blue, sci-fi HUD elements, rounded corners, diffuse drop shadows, glass morphism, hand-drawn or organic strokes, torn edges, watercolor, photorealistic machinery close-ups, full-bleed brass fills, red used as structural color, page header/footer chrome",
  "layout_blueprints": {
    "cover": [
      {"position": "page inset edge", "count": 1, "labels": ["黄铜刻线整页内框（2px+1px 双刻线，距页缘约 2.5%）"]},
      {"position": "frame corners", "count": 4, "labels": ["黄铜铆钉四角各一枚"]},
      {"position": "top", "count": 1, "labels": ["mono 黄铜 kicker + 项目编号前缀"]},
      {"position": "center", "count": 1, "labels": ["condensed 大写巨字主标题（刻字感）"]},
      {"position": "below title", "count": 2, "labels": ["一行副题", "一行 mono 小字日期/届次"]},
      {"position": "background", "count": 1, "labels": ["疏格钢板网（仪式页特权）"]}
    ],
    "divider": [
      {"position": "page inset edge", "count": 1, "labels": ["黄铜刻线内框 + 四角铆钉"]},
      {"position": "center", "count": 1, "labels": ["章节序号巨字（mono 或 condensed grotesk 拉丁数字）"]},
      {"position": "below center", "count": 1, "labels": ["章节题 + 黄铜刻度短线"]},
      {"position": "upper right", "count": 1, "labels": ["红色标注章（至多一枚，如 SECTION B）"]}
    ],
    "key-message": [
      {"position": "center 60%", "count": 1, "labels": ["2–8 字核心词或 KPI 巨字（condensed 700，黄铜刻线框或刻度线托底）"]},
      {"position": "top", "count": 1, "labels": ["mono kicker + 编号"]},
      {"position": "frame corners", "count": 4, "labels": ["铆钉（若使用刻线框）"]},
      {"position": "lower third", "count": 1, "labels": ["一行支撑注记（mono 小字）"]}
    ],
    "analysis": [
      {"position": "top", "count": 1, "labels": ["标题 + mono kicker（无仪式背景）"]},
      {"position": "center", "count": 1, "labels": ["核心结构（参数网格/工艺流程轴/分解示意图，黄铜刻线框成阵）"]},
      {"position": "left and right", "count": 2, "labels": ["刻线框辅助模块", "刻线框辅助模块"]},
      {"position": "corner", "count": 1, "labels": ["可选红色标注章或评审注记"]}
    ]
  },
  "rendering_constraints": [
    "The page must read as a 1950s World's Fair pavilion panel or industrial exhibition poster, not a generic corporate deck, not cyberpunk, not steampunk.",
    "Brass stays structural: engraved lines, rivets, frames and tick marks only; flat brass fills and metallic gradient type are forbidden.",
    "Annotation red appears only as rubber-stamp marks or review annotations — never as structural lines, fills, or body text.",
    "Every container reads as engraved from steel: double brass line plus inner groove shadow; bare rectangles and diffuse shadows are a failure.",
    "Exactly one lead metal motif per page (frame OR rivet system OR stamp); rivets pin corners only, never float freely.",
    "The main title must read as cast pavilion lettering: condensed grotesque, uppercase Latin with wide tracking, carved-edge crispness — plain default sans is a failure.",
    "All shading follows one overhead exhibition hall light: subtle directional sheen on lacquer, groove shadows inside engravings, rivet highlights upper-left.",
    "Cover/divider/key-message pages: one giant title, one kicker, at most one subtitle plus one small annotation line; forbid 5 or more text modules.",
    "Analysis pages keep engineering discipline: engraved frames aligned in a grid with equal spacing; no overlapping frames, no tilted containers (the stamp alone may tilt).",
    "Chinese strokes must render accurately; title legibility outranks ornament — keep the title zone clear of grid lines and rivets.",
    "Do not invent logos, hall of fame badges, gears, or QR codes."
  ]
}
```

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：黄铜刻线框（.mt-brs-engrave）和铆钉（.mt-brs-rivet）是签名结构件，形状由 CSS 承担（data-editable-skip），其内部承载的文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，页面回到「标题 + 两段正文 + 横排三格 KPI」，黄铜刻线框、铆钉四角、红色标注章、疏格钢板网全部消失，元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 1950s 世博会的工业乐观主义——钢板上的黄铜刻线是工程的尊严，每条信息都是从钢板上刻出来的精确构件，不是贴上去的便利贴。

page_composition:
  skeleton: 黄铜刻线框成阵——2px+1px 双刻线直角容器在涂漆钢板上等距阵列，四角钉铆钉
  grid: {margin: 96px 120px, gutter: 32px}
  balance: {anchor: 刻线框阵(主信息区), counterweight: 红色标注章(角部批注) / 疏格钢板网(仪式页背景)}
  whitespace_ratio: ">=35%"
  flow: "mono 项目编号 kicker 定锚 → 刻线框承载核心信息（标题/数据/参数）→ 铆钉钉角收边 → 红色标注章做批注 → 底部 mono 小字收束"
signature_operator: 把每条信息编译成一个从钢板上刻出来的构件——
  核心信息装进黄铜刻线框（.mt-brs-engrave：2px 黄铜 border + 1px outline 双刻线 + inset 刻槽影），框四角钉铆钉（.mt-brs-rivet）；
  标题用 condensed grotesk 大写 + 加宽字距 + mono 项目编号 kicker（"EXPO-58 / HALL 2"式）；
  三项数字重排为刻线框阵内的参数条目（非横排等权三格），主数字独占一张刻线框 + 黄铜刻度线托底；
  批注用红色标注章（.mt-brs-stamp：accent-2 红 2px 描边 + rotate(-3deg) 微倾斜 + mono 大写短词），每页至多 2 枚；
  疏格钢板网（.mt-brs-grid）只许仪式页背景；
  涂漆钢板底（--paper #1c1c1e）+ 黄铜 accent（#b8860b）是工业世界的基底。
silhouette: 深炭钢板上黄铜刻线框阵列；直角双刻线矩形块面；重心左上象限（刻线框阵区）；右下标注章或疏格网作平衡。
info_grammar:
  cover:    满版炭灰钢板 + 疏格钢板网仪式背景 + 黄铜刻线整页内框 + 四角铆钉 + condensed 大写巨字标题 + mono kicker
  toc:      3-5 个刻线框排列，当前章节用红色标注章标记
  claim:    刻线框阵承载主张句（框内 condensed 大字 + mono 编号 kicker），红色标注章从框角引出批注，铆钉钉框角
  analysis: 2-4 个同构刻线框在涂漆钢板上，每个承载一段信息，至多一张框用黄铜刻度线焦点
  data:     三项数字 → 刻线框阵内参数条目排列，主数字独占黄铜刻度线框
  closing:  炭灰底 + 刻线框呼应封面（缩小或半隐），标注章最后一次出现
type_scale:            # px@1920x1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 128px  # condensed grotesk 700 大写承载展馆招牌字；与正文 4.6:1
  rule: 标题:正文 >=1.8:1；正文层 opacity = 1，禁灰化弱读；黄铜 accent 面积 <=6%（只做刻线/铆钉/刻度/焦点数字）；标注红 <=3% 且单页至多 2 处
  floor_note: body/heading/subhead/caption/meta 不覆盖，继承骨架 28/64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 刻线框 2px solid accent border + 1px outline outline-offset:3px（双刻线 + 刻槽影），直角，无弥散影
  - 炭灰钢板底（--paper #1c1c1e）+ 黄铜 accent（#b8860b），accent 面积 <=6%；标注红（#c0392b）面积 <=3%
  - 铆钉只钉刻线框四角或线端，每容器至多 4 枚，禁漂浮散布
  - 横排等权三格容器数 = 0
  - 红色标注章每页至多 2 枚，禁压正文（是批注不是标语）
  - 疏格钢板网只许仪式页背景，禁进正文阅读区
forbidden_defaults: [横向等权三格 KPI, 卡片墙成阵, 居中 hero, 圆角卡, 弥散软影, 渐变色块, 玻璃拟态, 满版黄铜填充, 齿轮/管线 steampunk 元素, 赛博/科幻蓝, 蓝图纸底色（E2 领地）]
dna_events: {cover: 强, claim: 中, analysis: 弱, data: 中, toc: 弱, closing: 强}
```

**Variants 配色变体**

#### 锈红

- **气质**：深棕钢板 + 锈红主色——更旧的工业感，厂房档案与重型机械，适合制造/重工/遗产活化叙事

```css
--paper:#241a16; --paper-tint:#30231d;
--ink:#ece0d0;   --ink-tint:#4a3a30;
--accent:#c05a3a; --accent-on:#241a16;
--accent-2:#b8860b; --accent-2-on:#241a16;
```

- **accent 预算**：锈红接管结构色（刻线/铆钉/刻度），黄铜退居标注位（章与注记）——两色角色互换，面积口径不变

#### 橄榄绿

- **气质**：深橄榄装备漆 + 黄铜配件——军事/野外工程感，适合户外装备、能源、基建与防务叙事

```css
--paper:#232a1e; --paper-tint:#2d3725;
--ink:#e6e2d2;   --ink-tint:#3d4632;
--accent:#b8860b; --accent-on:#232a1e;
--accent-2:#c0392b; --accent-2-on:#e6e2d2;
```

- **accent 预算**：黄铜在橄榄底上更接近装备铭牌质感——结构色与面积口径同基底；标注红纪律不变
