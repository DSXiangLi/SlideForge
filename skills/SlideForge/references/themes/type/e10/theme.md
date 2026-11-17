# E10 星图

- **id**：e10
- **气质**：深夜蓝天球上，银白星点以金色虚线缝成星座——浩瀚、精确，有观星手册的浪漫
- **适用**：愿景/战略/路线图、关系图谱与生态位叙事、科技与人文交叉主题，晚间发布与沉浸暗场
- **focus**：G9 + G5
- **世界参考**：古典星图与观星手册（Uranometria 以降的天球测绘传统）——深蓝夜空、实星点+虚线连线的星座、黄道坐标网格、星等符号与坐标注记
- **unforgettable**：星座连线——几颗亮星以 1px 虚线缝成星座，旁缀斜体星名与 mono 星等注记；"把内容要点连成星座"是天然的关系隐喻
- **分化声明**：与 d2 分化于 L3/L4/L5/L6/L7——e10 质感是极轻 grain 夜空底噪、d2 是 glow 显影辉光；e10 母题是星座连线/黄道坐标网格/星等注记、d2 是胶片齿孔/光束角标/显影晕；e10 容器是无框 + 虚线连线结构（禁辉光托底）、d2 无框只靠辉光托底；e10 签名动效是 draw-line 连线成星座 + fx 仪式层本命、d2 是 blur-in 显影浮出；e10 构图亲和轴与节点（星座=节点连线）、d2 亲和裂屏对开（L2 同为暗场衬线偏细，拉开靠后五层，全真）

**G1 color**

```css
--paper:#0b1426; --paper-tint:#152138;
--ink:#dfe7f2;   --ink-tint:#1d2c47;
--accent:#e8b64c; --accent-on:#0b1426;
```

- **accent 预算**：内容页 accent 面积 ≤5%（金黄是星光——只给亮星、星座连线、星等注记与关键数字，禁大块铺色）；满屏 accent 禁止（夜空永不天亮，封面仪式感靠星座与 fx 星场而非满色）；首尾闭环：封面主星座开场 → 收束页同一星座再现（或黄道金光带呼应）。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 400–500 偏细、正文 400——深空衬线偏细更透，层级靠字距与排布，不靠字重压强
- **字号对比**：主标题:正文 ≥8:1（低密度；夜空巨字特档 10:1 仅封面宣言页）；高密度 ≥5:1
- **字重映射**：衬线偏细立场：≥77px→400；35–76px→400–500；正文 400；14–16px 小字 500
- **标题修饰**：加宽字距（letter-spacing ≥.08em，星图题铭传统）；标题旁可缀 mono 坐标注记（`.mt-star-mag`）；斜体只属于星名（`.mt-star-name`），不进标题本体

**G3 texture**

```css
--texture-type: grain;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
--texture-scope: cover;
```

- **立场**：极轻颗粒 = 夜空底噪——仪式页深空铺一层微弱颗粒；正文页保持纯净星场（星点交给母题与 fx 仪式层）；与 d2 划界：星图没有显影灯，glow 禁入

**G4 shape**

- **圆角**：0（天球仪的经纬是测绘线，容器不磨圆）
- **hairline**：不用实线分割——分组与引导用 1px dashed color-mix(in srgb, var(--ink) 30%, transparent) 虚线（坐标引线与星座连线同一种语言）
- **阴影**：无；唯一允许的光是星点自身辉光（`.mt-star-dot`），禁对容器施辉光
- **容器造型**：无框 + 虚线连线结构——内容悬浮于星空，分区靠坐标网格与虚线连线；禁实色卡、禁描边实框、禁辉光托底（辉光托底是 d2 暗房词汇，这是两主题 L5 的分界）
- **高密度容器边界**：1px dashed 虚线界框（ink 30% 虚线，hairline 口径）——古典星图的星座界线即此形态，是本世界唯一合法的"框"；虚线即立场，实线实框永禁，界框只圈真实成群的内容（孤星不是星座）

**G5 motion**

- **气质**：calm
- **强度上限**：默认（calm 档内——深空不疾不徐）
- **锚点偏好**：draw-line 为签名锚点——虚线描绘即连线成星座，关系图谱页/路线图页优先；标题入场 rise-in 或默认阶梯；count-up 只给真正的 KPI 英雄数字
- **节奏偏移**：时长档 +1（观星是慢的仪式）；阶梯步长 ≥90ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / scramble（弹跳与字符噪点破坏夜空）
- **fx 许可**：constellation / starfield / particle-drift 全开——本库第一个 fx 本命主题：星座与星空本来就是这个世界（ascii-field 禁——字符场是终端词汇）；fx 仍只许封面/收束仪式页，每页至多 1 个

**G8 component**

- **亲和**：轴与节点（星座 = 节点连线，关系/演进内容的原生形态）、巨字宣言（夜空巨字 + 星场，本主题的封面仪式感）、图文证据（星图 + 星名注记）
- **禁忌**：禁密集网格矩阵（星空不是表格——网格语言只许黄道坐标网格一种）；数据英雄页保持大留白，图表以 accent 单系列描线为主；裂屏对开慎用（天球是整一的）

**G9 motif**

- **词汇**：星座件（`.mt-star-dot` 星点：小圆点 + 十字星芒，自带微弱辉光；`.mt-star-link` 连线：1px dashed 线段，宽度与 rotate 由生成侧按星点间距定位——两个类组合使用，把内容要点缝成星座）/ 黄道坐标网格（`.mt-star-grid`：细经纬直线网格，低透明背景层，只许仪式页与图版区）/ 斜体星名（`.mt-star-name`：衬线 italic 小注，古典星图的签名）/ 星等注记（`.mt-star-mag`：mono 小字标注星等/坐标/编号）

```css
/* E10 星图 · 装饰母题 */
.mt-star-dot{position:absolute;width:5px;height:5px;border-radius:50%;background:var(--ink);box-shadow:0 0 6px color-mix(in srgb,var(--accent) 60%,transparent)}
.mt-star-dot::before,.mt-star-dot::after{content:"";position:absolute;left:50%;top:50%;background:color-mix(in srgb,var(--ink) 80%,transparent)}
.mt-star-dot::before{width:13px;height:1px;transform:translate(-50%,-50%)}
.mt-star-dot::after{width:1px;height:13px;transform:translate(-50%,-50%)}
.mt-star-link{position:absolute;height:0;border-top:1px dashed color-mix(in srgb,var(--accent) 55%,transparent);transform-origin:left center;pointer-events:none}
.mt-star-grid{position:absolute;inset:0;pointer-events:none;opacity:.5;background:repeating-linear-gradient(0deg,transparent 0 47px,color-mix(in srgb,var(--ink) 10%,transparent) 47px 48px),repeating-linear-gradient(90deg,transparent 0 47px,color-mix(in srgb,var(--ink) 10%,transparent) 47px 48px)}
.mt-star-name{font-family:var(--font-display);font-style:italic;letter-spacing:.06em;color:color-mix(in srgb,var(--ink) 75%,transparent)}
.mt-star-mag{font-family:var(--font-mono);font-size:11px;letter-spacing:.22em;color:color-mix(in srgb,var(--ink) 52%,transparent)}
```

- **禁忌**：星座件是关系图式不是撒星——每页星座 ≤1 组（3–7 颗星），星点禁无连线空挂（孤星不是星座）；坐标网格禁进正文阅读区；母题件一律 `data-editable-skip`（`.mt-star-name`/`.mt-star-mag` 承载真实星名/坐标文本时除外——样式由类承担，文本保持可编辑）

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：星座件（.mt-star-dot + .mt-star-link）和黄道坐标网格（.mt-star-grid）是签名结构件，形状由 CSS 承担（data-editable-skip），其内部承载的文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，页面回到「标题 + 两段正文 + 横排三格 KPI」，星座连线、星点、坐标网格、星等注记全部消失，元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 浩瀚与精确并存——夜空不拥挤，几颗亮星以虚线缝成星座就够了；信息要点之间的关系比要点本身更重要。

page_composition:
  skeleton: 星座连线阵——内容悬浮于星空，分区靠虚线连线与坐标网格，无实色卡无实框
  grid: {margin: 96px 120px, gutter: 32px}
  balance: {anchor: 星座连线区(主信息关系网), counterweight: 黄道坐标网格(仪式页背景) / 留白星场}
  whitespace_ratio: ">=45%"
  flow: "mono 坐标注记定锚 → 星点承载核心信息节点 → 虚线连线缝成关系星座 → 斜体星名做学术签名 → 星等注记收束"
signature_operator: 把每条信息编译成夜空中的一颗星——
  核心信息节点装进星点（.mt-star-dot：小圆点 + 十字星芒 + 微弱辉光），3-7 颗星点用虚线连线（.mt-star-link：1px dashed accent）缝成一组星座；
  主张句在星座关系网中，斜体星名（.mt-star-name：衬线 italic 小注）标注节点，mono 星等注记（.mt-star-mag）标注坐标/编号；
  三项数字重排为星座节点（非横排等权三格），主数字独占一颗最亮星 + accent 辉光；
  黄道坐标网格（.mt-star-grid：细经纬直线网格）只许仪式页与图版区低透明背景；
  深蓝夜空底（--paper #0b1426）+ 金黄 accent（#e8b64c）只做星光与连线，禁大块铺色。
silhouette: 深蓝夜空上虚线星座；无框悬浮节点；重心分散（星座分布）；大面积留白星场是主负空间。
info_grammar:
  cover:    满版深蓝夜空 + 黄道坐标网格仪式背景 + 衬线巨字标题 + 主星座开场（3-5 颗星 + 连线）
  toc:      3-5 组星座排列，每组对应一章，当前章节用 accent 辉光标记
  claim:    星座连线网承载主张句（节点 = 要点，连线 = 关系），斜体星名标注节点，mono 星等注记引出说明
  analysis: 2-4 组同构星座在深蓝夜空上，每组承载一段信息，至多一组用 accent 辉光焦点
  data:     三项数字 → 星座节点排列，主数字独占最亮星 + accent 辉光 + mono 坐标注记
  closing:  深蓝夜空 + 封面主星座再现（或黄道金光带呼应），星等注记最后一次出现
type_scale:            # px@1920x1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 104px  # 衬线 400 偏细承载星图题铭；与正文 3.7:1
  rule: 标题:正文 >=1.8:1；正文层 opacity = 1，禁灰化弱读；accent 金黄面积 <=5%（只做星点/连线/星等注记/关键数字）
  floor_note: body/heading/subhead/caption/meta 不覆盖，继承骨架 28/64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 无框 + 虚线连线结构（1px dashed ink 30%），禁实色卡、禁描边实框、禁辉光托底
  - 深蓝底（--paper #0b1426）+ 金黄 accent（#e8b64c），accent 面积 <=5%
  - 每页星座 ≤1 组（3-7 颗星），星点禁无连线空挂（孤星不是星座）
  - 横排等权三格容器数 = 0
  - 坐标网格禁进正文阅读区
  - fx 仪式层（constellation/starfield/particle-drift）只许封面/收束仪式页，每页至多 1 个
forbidden_defaults: [横向等权三格 KPI, 卡片墙成阵, 居中 hero, 圆角卡, 弥散软影, 渐变色块, 玻璃拟态, 满版色块, 实线实框, 密集网格矩阵, 辉光托底]
dna_events: {cover: 强, claim: 中, analysis: 弱, data: 中, toc: 弱, closing: 强}
```

**Variants 配色变体**

#### 星云紫

- **气质**：银河深处的星云紫调——更神秘、更内省，适合 AI/深科技/哲学与宇宙学叙事

```css
--paper:#100c22; --paper-tint:#1a1433;
--ink:#e2dcf2;   --ink-tint:#261d47;
--accent:#9b7fd4; --accent-on:#100c22;
```

#### 极夜蓝白

- **气质**：极夜下的蓝白星光——最冷、最素，接近天文台观测记录纸，适合科研/数据/天文与极地叙事

```css
--paper:#0a111c; --paper-tint:#131e2d;
--ink:#e8eef5;   --ink-tint:#1b2939;
--accent:#cfe0f0; --accent-on:#0a111c;
```

- **accent 预算**：蓝白 accent 与 ink 近色——点状纪律不变，强调靠明度差与连线结构而非色相；其余同基底口径
