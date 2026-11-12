# H1 氤氲手卷

- **id**：h1
- **气质**：雾紫氤氲里徐徐展开的宣纸手卷，宋体厚重、毛笔字飘忽，一点朱砂压住整页
- **适用**：人文与科技对话、思辨型主题、品牌叙事、文化教育、需要柔和仪式感的开场与收束
- **focus**：G3 + G9
- **世界参考**：宋式手卷装帧与题跋传统——宣纸、上下两根金轴、朱砂印、极淡的巨字水印，被一层雾色光晕重新打亮
- **unforgettable**：卷轴上下两根金轴与四角铜轴帽，加角落一枚微微歪斜的朱砂印章，一眼手卷
- **分化声明**：与 c4 分化于 L1/L2/L3/L4/L5/L6——h1 是紫墨雾色多调（c4 纸白墨黑单一绯红）、display 与正文虽同属宋体但西文装饰走斜体衬线且毛笔字入母题（c4 全衬线无书法层）、质感是四团模糊雾斑 aura（c4 是轻纸纹 paper）、母题是金轴/朱砂印/淡墨巨字水印（c4 是题花/首字下沉/引文拉页）、容器是半透明圆角宣纸卡（c4 无卡片、直角栏线）、动效是雾中渐显与墨线描绘（c4 是出版式翻页逐行显影）

**G1 color**

```css
--paper:#faf7f3; --paper-tint:#e8e0e7;
--ink:#241f2b;   --ink-tint:#544b60;
--accent:#9c3b34; --accent-on:#faf7f3;
--accent-2:#8d7aa8; --accent-2-on:#faf7f3;
--accent-3:#6f84a6; --accent-3-on:#faf7f3;
--palette-1:#8d7aa8; --palette-1-on:#faf7f3;
--palette-2:#6f84a6; --palette-2-on:#faf7f3;
--palette-3:#bb93ab; --palette-3-on:#241f2b;
--palette-4:#7f9b93; --palette-4-on:#241f2b;
--hl-1:#c9a86a; --hl-1-on:#241f2b;
```

- **accent 预算**：内容页朱砂面积 ≤5%，只许一枚印章、一处眉批线或一个点睛词；四雾色是背景氤氲，不许以实色块出现（叠加不透明度 ≤30%，落在低彩浊色窗口）；金只许细线、轴杆与标注，不许铺面。满屏朱砂仅封面/收束页特权，本主题更推荐「半幅雾色 + 一枚朱印」。首尾闭环：封面朱印起卷 → 收束页朱印回押。
- **多色立场**：封闭色板禁令——除 G1 声明的四雾色、朱砂、金之外不得引入第五种色相，页面任何渐变只许在这几个 token 之间插值；分配规则——四雾色按固定顺序承担氤氲背景与类目轮转（雾紫→雾蓝→藕粉→青绿），accent-2/3 只作语义锚点（章节编号、题跋标签），朱砂只作单页唯一视觉重心，金只作标注层；注意力色预算——单页高彩度（朱砂）面积 ≤5%、至多一处，雾色合计不透明度 ≤30% 且不构成第二焦点，金 ≤2%。

**G2 typography**

```css
--font-display:"Noto Serif SC","Source Han Serif SC","Songti SC","STSong","SimSun",serif;
--font-body:"Noto Serif SC","Source Han Serif SC","Songti SC","STSong","SimSun",serif;
--font-mono:"Cormorant Garamond",Georgia,"Times New Roman",serif;
```

- **字重倾向**：全宋体，标题 700–900（碑刻式厚重），正文 400–500，西文斜体装饰恒 400；书法层只存在于母题，不承载正文
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：衬线 display 恒重立场（不走倒挂——细宋大字号发虚）：标题 700–900；正文 400–500；14–16px 小字 500–600；西文斜体 kicker 400；同页小字字重不低于大字的相邻档
- **标题修饰**：巨字宣言用实色 + 一笔雾色渐层笔触线；章节编号用 `.tt-outline` 描边书法字；关键词用 `.tt-mark` 淡雾底纹（不用 `.tt-glow`、不用 `.tt-shadow`，亮纸面上发光与错版都发脏）

**G3 texture**

```css
--texture-type: aura;
--texture-layer: radial-gradient(46% 50% at 10% 6%, color-mix(in srgb, var(--accent-2) 30%, transparent), transparent 70%), radial-gradient(40% 44% at 88% 24%, color-mix(in srgb, var(--accent-3) 28%, transparent), transparent 72%), radial-gradient(48% 42% at 18% 94%, color-mix(in srgb, var(--palette-3) 26%, transparent), transparent 70%), radial-gradient(36% 38% at 84% 90%, color-mix(in srgb, var(--palette-4) 22%, transparent), transparent 72%);
--texture-scope: all;
```

- **立场**：氤氲是第一主角——四团低彩雾斑以 multiply 叠在宣纸底上，配一层极淡颗粒（`.mt-scroll-grain`）；雾色是气氛不是信息，绝不允许雾斑盖过文字对比度。正文页需逐页加 `texture-on` 才铺，仪式页自动铺。

**G4 shape**

- **圆角**：16–20px（宣纸软边）；朱砂印章 8px；金轴端帽圆形
- **hairline**：1px solid color-mix(in srgb, var(--ink) 12%, transparent)，用于卡片边界与题跋分隔
- **阴影**：0 24px 70px -24px color-mix(in srgb, var(--ink) 45%, transparent)，柔远投影；禁硬边 offsets、禁多层描边
- **容器造型**：半透明宣纸卡——color-mix(in srgb, var(--paper) 92%, transparent) 底 + 1px hairline + 大圆角 + 柔阴影；卡片顶部可落 3px 雾色渐层色带标示类目；禁直角硬框、禁玻璃拟态、禁霓虹描边、禁撕边与胶带
- **高密度容器边界**：左侧 3px 金色细边（--hl-1）或朱砂左线（--accent）二选一，注记块用朱砂且每页至多一处；容器内 eyebrow / 题 / 体 / 注四层字阶齐备

**G5 motion**

- **气质**：calm
- **强度上限**：默认偏慢——一切比全局默认慢半拍，展卷感；每页主动效 ≤1
- **锚点偏好**：blur-in（雾中显影）为封面首选，裸 data-anim（fadeUp）为题跋与卡片，draw-line（墨线描绘）为分隔线；数字以静态直排为主，不做 count-up
- **节奏偏移**：时长档 +1，阶梯步长 ≥140ms，循环氛围一律不用
- **缓动签名**：主题 CSS 块 `:root{--ease-out:cubic-bezier(.2,.7,.3,1)}`——长尾收束，像笔锋收住
- **禁用**：scale-pop / persp-in / shatter / typewriter / scramble / flicker-in / data-rotate / light-sweep（弹跳、透视、碎字、打字机、通电与持续轮转都与卷轴静气冲突）
- **fx 许可**：全禁——canvas 仪式层不使用，氤氲完全由 CSS 质感层与母题件承担

**G8 component**

- **亲和**：巨字宣言（封面题字）、裂屏对开（卷轴左右展开的两栏）、图文证据（图 + 题跋式注记）、注记块（朱砂眉批）
- **禁忌**：禁网格卡片墙与 KPI 仪表盘；禁终端/信号/蓝图/票据词汇；不用加号角标与网格点阵；禁高饱和多色柱图；连续两页不得同为对开谱系

**G9 motif**

- **词汇**：金轴与铜轴帽（`.mt-scroll-rod` + `.mt-scroll-cap`，卷轴上下缘，每页至多一对）/ 朱砂印章（`.mt-scroll-seal`，微歪 -6°，每页至多一枚，内为毛笔单字）/ 淡墨巨字水印（`.mt-scroll-watermark`，4% 不透明度的毛笔大字，仪式页专用）/ 雾团（`.mt-scroll-mist`，模糊圆斑，只作气氛）/ 颗粒（`.mt-scroll-grain`，满幅极淡噪点）/ 笔触线（`.mt-scroll-brush`，雾色渐层细线）/ 描边章节数字（`.mt-scroll-numeral`，书法字描边）
- **禁忌**：母题件一律 `data-editable-skip`；印章与水印不得承载结论性文字；金轴不得压到正文；不使用加号角标、ASCII 框、题花、首字下沉等他系词汇

```css
/* H1 氤氲手卷 · 装饰母题 */
:root{--ease-out:cubic-bezier(.2,.7,.3,1)}
.mt-scroll-rod{position:absolute;left:0;right:0;height:20px;background:linear-gradient(90deg,var(--hl-1),color-mix(in srgb,var(--hl-1) 45%,var(--paper)),var(--hl-1));box-shadow:0 8px 22px -8px color-mix(in srgb,var(--ink) 45%,transparent)}
.mt-scroll-cap{position:absolute;width:24px;height:24px;border-radius:50%;background:radial-gradient(circle at 35% 30%,color-mix(in srgb,var(--hl-1) 55%,var(--paper)),var(--hl-1) 65%,color-mix(in srgb,var(--hl-1) 55%,var(--ink)))}
.mt-scroll-seal{display:flex;align-items:center;justify-content:center;border:2px solid var(--accent);border-radius:8px;color:var(--accent);font-family:"Ma Shan Zheng","STKaiti","KaiTi",cursive;transform:rotate(-6deg);background:color-mix(in srgb,var(--accent) 5%,transparent)}
.mt-scroll-watermark{position:absolute;font-family:"Ma Shan Zheng","STKaiti","KaiTi",cursive;line-height:1;color:color-mix(in srgb,var(--ink) 4%,transparent);pointer-events:none;user-select:none}
.mt-scroll-mist{position:absolute;border-radius:50%;filter:blur(70px);mix-blend-mode:multiply;pointer-events:none;opacity:.55}
.mt-scroll-grain{position:absolute;inset:0;pointer-events:none;opacity:.05;mix-blend-mode:overlay;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
.mt-scroll-brush{height:2px;background:linear-gradient(90deg,transparent,var(--accent-2),var(--accent-3),var(--hl-1),transparent);opacity:.65}
.mt-scroll-numeral{font-family:"Ma Shan Zheng","STKaiti","KaiTi",cursive;color:transparent;-webkit-text-stroke:1.5px var(--accent-2);opacity:.45;line-height:1}
```

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约；`signature_operator` 必须通过 DOM 结构测试——删掉它，页面的元素数量 / 分组 / 顺序 / 位置会变，否则退回重写。
- **灵魂承载**：签名形状升级为信息容器（上下金轴定界、竖排题字列装论点、朱印装句读）；形状由 CSS 承担（`data-editable-skip`），其内部承载文字仍是 `data-editable` 叶子节点——文字始终留在 DOM，不牺牲可编辑性，也不需整页生图。

```yaml
doctrine: 时间展开与人的题跋；内容是卷轴上层层叠加的观看痕迹。
signature_operator: 以自右向左的展开方向重排信息——上下金轴定界，标题竖排居右，
  其余信息按题跋层级分列向左递推；数字改写成汉数题跋而非 KPI 格，朱印是全篇唯一句读。
silhouette: 纵向主轴 + 上下横轴；重心右上；左侧长留白；雾色只作气氛不占结构。
info_grammar:
  all:      上下金轴 + 四角铜帽定界
  claim:    右侧竖排题字列（≥6cqw）+ 西文副题细列
  analysis: 三列题跋（论点 / 说明 / 数字汉数），自右向左递推
  cover:    展卷强形态：淡墨巨字水印 + 一枚朱印
  closing:  朱印回押，与封面闭环
type_scale:            # 三级层级（480px 预览基准，单位 cqw）；任何文本不得低于 floor
  floor:   1.5         # ≈7.2px，唯一硬下限（真实 deck ~2.7x 后 ≈19px）
  display: 2.9         # 汉数题跋数字（非 KPI 格）；与标题拉开 ≥1.3 倍
  heading: 2.1         # 题跋列小标题
  body:    1.8         # 说明 / 图注（opacity ≥ .8，禁灰化弱读）
  vertical_title: 6.0  # 竖排主标题专属下限（writing-mode:vertical-rl，实测字距 ≈1.4×字号）
  rule: 序号:标题 ≥ 1.3:1 且 标题:正文 ≈ 1.2–1.5:1（禁层级倒挂；竖排标题须整列可容不强制断列）
invariants:
  - 主标题 `writing-mode: vertical-rl` 且字号 ≥6cqw
  - 结构边缘主方向 = vertical
  - 朱砂面积 ≤5% 且单页仅一枚
  - 上下轴存在且各自贯穿全宽
  - 横排等权三格容器数量 = 0
forbidden_defaults: [网格卡片墙, KPI 仪表盘, 水平三栏, 终端/蓝图/票据词汇, 高饱和多色柱图]
dna_events: {cover: 强, claim: 中, divider: 中, analysis: 弱, data: 弱, closing: 强}
```

**Variants 配色变体**

#### 青绿

- **气质**：雾气偏青，草木与书卷气——自然、教育、博物、长期主义叙事
- **accent 预算**：朱砂仍 ≤5%，雾色向青绿一侧轮转，金轴略收暗

```css
--paper:#f7f7f2; --paper-tint:#e2e9e4;
--ink:#1f2b2c;   --ink-tint:#4c5f5d;
--accent:#9c3b34; --accent-on:#f7f7f2;
--accent-2:#5d8a86; --accent-2-on:#f7f7f2;
--accent-3:#6f84a6; --accent-3-on:#f7f7f2;
--palette-1:#5d8a86; --palette-1-on:#f7f7f2;
--palette-2:#6f84a6; --palette-2-on:#f7f7f2;
--palette-3:#a8bfa8; --palette-3-on:#1f2b2c;
--palette-4:#7f9b93; --palette-4-on:#1f2b2c;
--hl-1:#b99a5b; --hl-1-on:#1f2b2c;
```

#### 夜卷

- **气质**：墨底展卷，纸色反白，朱印与金轴在暗处微亮——晚场演讲、影像叙事、收束页
- **accent 预算**：朱砂提亮后仍 ≤5%，四雾色亮度上调以在暗底可见，叠加不透明度下调至 ≤22%

```css
--paper:#241f2b; --paper-tint:#322b3c;
--ink:#f3ede6;   --ink-tint:#cfc4d3;
--accent:#c4625a; --accent-on:#241f2b;
--accent-2:#a996c4; --accent-2-on:#241f2b;
--accent-3:#8fa8cc; --accent-3-on:#241f2b;
--palette-1:#a996c4; --palette-1-on:#241f2b;
--palette-2:#8fa8cc; --palette-2-on:#241f2b;
--palette-3:#d8aec8; --palette-3-on:#241f2b;
--palette-4:#9cc0b6; --palette-4-on:#241f2b;
--hl-1:#e0c384; --hl-1-on:#241f2b;
```
