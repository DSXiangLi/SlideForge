# A1 电子杂志（默认）

- **id**：a1
- **气质**：纯墨黑 + 暖米白，杂志感最强
- **适用**：通用分享、商业发布、任何场景的安全选择
- **focus**：G2 + G9
- **世界参考**：归藏"电子杂志 × 电子墨水"——双色墨水、纸面留白、衬线标题的编辑部排版
- **unforgettable**：Ghost 残影巨字——超大低透明描边字作页面背景层，翻页即杂志封面感
- **分化声明**：与 c4 分化于 L2/L4/L6——a1 正文无衬线、母题是 Ghost 巨字与竖排题字条、锚点动效是 mask-lines 逐行显影；c4 全衬线、母题是题花与首字下沉、锚点是 draw-line

**G1 color**

```css
--paper:#f1efea; --paper-tint:#e8e5de;
--ink:#0a0a0b;   --ink-tint:#18181a;
--accent:#0a0a0b; --accent-on:#f1efea;
```

- **accent 预算**：accent 与 ink 同色——"满屏 accent"体现为暗色反白页（`.slide.dark`），是封面/收束的特权；内容页不追求 accent 面积指标，强调靠字重与字号。首尾闭环：暗色封面（全亮墨色）开场 → 收束页暗色反白呼应（可半亮：ink 底 + paper 细条带）。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 600–700、正文 400；强调靠字重与字号，不靠颜色（accent==ink）
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1——衬线 display 靠字号差建层级
- **字重映射**：衬线恒重立场（不走倒挂——细衬线大字号发虚）：≥77px→600（封面/收束可 700）；35–76px→600；正文 400；14–16px 小字 500–600
- **标题修饰**：无
- **metric_fallback**：display→Songti SC/Noto Serif SC；body→PingFang SC/Noto Sans SC；mono→SF Mono/Menlo

**G3 texture**

```css
--texture-type: glow;
--texture-layer: radial-gradient(75% 55% at 80% 10%, color-mix(in srgb, var(--ink) 6%, transparent), transparent 65%);
--texture-scope: cover;
```

- **立场**：墨韵——仪式页一角淡墨晕染，正文页纯纸面

**G4 shape**

- **圆角**：0
- **hairline**：1px solid color-mix(in srgb, var(--ink) 18%, transparent)，只在层级边界出现
- **阴影**：无
- **容器造型**：无卡片立场——靠留白与 hairline 分区；底色块只用 paper-tint 灰档（灰底低对比，靠空气不靠边界），直角纯色；禁渐变、禁阴影
- **高密度容器边界**：paper-tint 灰档面，无框——亮底纸面上灰档明度差自足（§12"靠空气不靠边界"）；确需框感的锚点容器降纸档 + 1px hairline（§12 纸档允许描边），不给灰档补框

**G5 motion**

- **气质**：editorial
- **强度上限**：默认
- **锚点偏好**：封面/章节 mask-lines 逐行显影或 chars；数据页 draw-line；数字以字号对比直排为主，count-up 只给真正的 KPI 英雄页
- **节奏偏移**：时长档 +1（一切比默认慢半拍，显影感）；阶梯步长 ≥90ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / persp-in（弹跳与透视翻转破坏纸面安静）
- **fx 许可**：仅 ascii-field（字符呼吸场可破格；粒子类禁）

**G8 component**

- **亲和**：巨字宣言、图文证据、轴与节点（时间轴/演进）
- **禁忌**：禁连续两页网格矩阵——杂志节奏靠疏密对比，不靠格子堆叠；不用加号角标与网格点阵（那是瑞士系词汇）

**G9 motif**

- **词汇**：Ghost 残影巨字（页面背景层，与内容相关的单字/关键词，低透明描边，每页至多一个、只作背景不抢焦）/ 竖排题字条（封面与章节页侧缘竖排 mono 拉丁或拼音）/ 墨点角标（5px 实心方点替代图标，标记列表项或编号）

```css
/* A1 电子杂志 · 装饰母题 */
.mt-ghost{position:absolute;z-index:0;pointer-events:none;user-select:none;font-family:var(--font-display);font-weight:600;line-height:1;color:transparent;-webkit-text-stroke:1px color-mix(in srgb,var(--ink) 22%,transparent)}
.mt-vquote{writing-mode:vertical-rl;font-family:var(--font-mono);font-size:13px;letter-spacing:.35em;opacity:.5;pointer-events:none}
.mt-dot{display:inline-block;width:5px;height:5px;background:var(--ink)}
```

- **禁忌**：Ghost 字禁与标题同区抢焦、禁内容页连用超过两页；母题件一律 `data-editable-skip`

**bake_brief**

```json
{
  "visual_direction": "literary magazine spread on warm ivory paper, two-ink printing discipline, oversized serif masthead typography with extreme scale contrast, structural negative space, quiet paper grain, ghost outline display characters as background layer, independent-journal editorial restraint",
  "palette_rule": "two-ink discipline: near-black ink on warm ivory paper only — no third hue, no color accents, no gray-wash photography; emphasis is carried by type size and weight, never by color; dark ink-field pages with paper-colored text are a cover/closing privilege",
  "typography_bake": "主标题重构词汇：衬线巨字即页面本体——极端字号对比（≥8:1）；断行即构图——长标题按语义单元断行、左对齐成块、行距紧凑；Ghost 残影——与内容相关的单字作超大低透明描边背景层、与标题错位相切；半空心描边与实心字混排制造残影层次；竖排题字条——侧缘竖排拉丁/拼音小字作刊名注脚；隐喻融字只允许负空间层次（残影/错位），禁把笔画改造成图形",
  "uplift": "升维路径（HTML 做不到的物理维度）：纸与印刷机的物质性——暖米白纸张的纤维肌理与克重感；油墨压痕——凸版印刷的轻微凹陷、笔划边缘积墨的深浅变化；印刷网点的物理颗粒；纸面受光的微妙明暗（不是渐变滤镜，是纸的起伏反光）；Ghost 残影字如上一页透印（show-through）的物理透墨，与正文字有纸张厚度上的前后层——HTML 的扁平墨色在此获得纸与印刷的物质性",
  "allowed": "oversized serif display type, ghost outline background characters (one per page), vertical mono side inscriptions, small solid square dot markers, thin hairline rules, quiet paper grain, at most one corner ink halo on ritual pages, asymmetric editorial grid, generous empty paper",
  "avoid": "color accents, gradients, shadows, rounded cards, glass morphism, color photography, stock photo collage, icon rows, emoji, ornate borders, drop caps, mesh gradients, aurora blobs, sans-serif display type, dense text walls, social-media poster energy, red seal cliche, centered symmetric poster layout",
  "layout_blueprints": {
    "cover": [
      {"position": "top-left", "count": 1, "labels": ["刊名栏小字块（刊名/期号/日期）"]},
      {"position": "mid-left", "count": 1, "labels": ["衬线巨字主标题（左对齐语义断行块）"]},
      {"position": "right background", "count": 1, "labels": ["Ghost 残影单字（低透明描边）"]},
      {"position": "right edge", "count": 1, "labels": ["竖排题字条"]},
      {"position": "bottom", "count": 2, "labels": ["一行副题", "一行署名小字"]}
    ],
    "divider": [
      {"position": "top-left", "count": 1, "labels": ["章节序号衬线巨字"]},
      {"position": "below number", "count": 2, "labels": ["一行章节题", "一道 hairline"]},
      {"position": "background", "count": 1, "labels": ["章节关键词 Ghost 残影"]}
    ],
    "key-message": [
      {"position": "mid-left 70%", "count": 1, "labels": ["核心句衬线宣言（语义断行块）"]},
      {"position": "background", "count": 1, "labels": ["核心词 Ghost 残影"]},
      {"position": "bottom-left", "count": 1, "labels": ["一行小字注脚"]}
    ],
    "analysis": [
      {"position": "top", "count": 1, "labels": ["标题 + 一道 hairline"]},
      {"position": "main", "count": 1, "labels": ["杂志栏格（2–3 栏、hairline 分隔）"]},
      {"position": "inside columns", "count": 1, "labels": ["一句放大衬线引文（pull quote）"]},
      {"position": "column markers", "count": 1, "labels": ["实心方点列表标"]}
    ]
  },
  "rendering_constraints": [
    "The page must read as a printed literary magazine spread, not a PPT page, not a social-media poster.",
    "Hierarchy is built only from type size, weight and space — never from color.",
    "At most one ghost outline character per page, low opacity, never colliding with title legibility.",
    "Titles are left-aligned semantic line-break blocks; centered symmetric poster composition is forbidden.",
    "Empty paper is structural: at least 40% of the page stays blank.",
    "Flat ink only: no gradients, no shadows, no color photography.",
    "Cover/divider/key-message pages: one title plus at most two small annotation lines; analysis pages: 2–3 columns maximum, separated by hairlines.",
    "CJK serif strokes stay crisp at display sizes; no fake-bold smearing, no outline-only main titles.",
    "Pull quotes use the same serif display face; no second typeface family appears.",
    "Do not invent barcodes, QR codes, logos or seals unless they appear verbatim in the Text section."
  ]
}
```

**Variants 配色变体**

#### 靛蓝瓷

- **气质**：深靛蓝 + 瓷白，冷静理性，像学术期刊——科技/研究/数据分享、工程师文化

```css
--paper:#f1f3f5; --paper-tint:#e4e8ec;
--ink:#0a1f3d;   --ink-tint:#152a4a;
--accent:#0a1f3d; --accent-on:#f1f3f5;
--texture-layer: radial-gradient(85% 60% at 18% 0%, color-mix(in srgb, var(--ink) 5%, transparent), transparent 62%);
```

#### 森林墨

- **气质**：深森林绿 + 象牙，沉稳有呼吸感——自然/可持续/文化/非虚构内容

```css
--paper:#f5f1e8; --paper-tint:#ece7da;
--ink:#1a2e1f;   --ink-tint:#253d2c;
--accent:#1a2e1f; --accent-on:#f5f1e8;
--texture-type: grain;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E"), radial-gradient(70% 60% at 75% 85%, color-mix(in srgb, var(--ink) 5%, transparent), transparent 65%);
```

#### 沙丘

- **气质**：炭灰 + 沙色，克制高级，像建筑设计图册——艺术/设计/创意/时尚

```css
--paper:#f0e6d2; --paper-tint:#e3d7bf;
--ink:#1f1a14;   --ink-tint:#2d2620;
--accent:#1f1a14; --accent-on:#f0e6d2;
--texture-type: grain;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E"), radial-gradient(80% 65% at 70% 90%, color-mix(in srgb, var(--accent) 4%, transparent), transparent 65%);
```

#### 牛皮纸

- **气质**：深棕 + 暖米，像牛皮信封，温暖有年代感——怀旧/人文/阅读/历史/文学分享

```css
--paper:#eedfc7; --paper-tint:#e0d0b6;
--ink:#2a1e13;   --ink-tint:#3a2a1d;
--accent:#2a1e13; --accent-on:#eedfc7;
--texture-type: paper;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.06'/%3E%3C/svg%3E"), repeating-linear-gradient(0deg, color-mix(in srgb, var(--ink) 2%, transparent) 0 1px, transparent 1px 5px), radial-gradient(90% 70% at 30% 15%, color-mix(in srgb, var(--ink) 5%, transparent), transparent 60%);
--texture-scope: all;
```

---

## B 系 · 瑞士国际主义

B 系的灵魂：高级灰白底 + **单一**高饱和高亮色 + 1px 极细分割线（hairline）+ 网格。高亮色是手术刀，点到为止——一旦泛滥就掉档。加号角标与网格点阵是 B 系的专属词汇，其他主题禁用。
