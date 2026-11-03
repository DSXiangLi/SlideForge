# D2 柔光暗房

- **id**：d2
- **气质**：暗房安全灯下的琥珀光——影像正在显影液里浮现，安静、有胶片的颗粒时间感
- **适用**：摄影/影像/艺术/品牌故事，氛围叙事，情绪主导的发布
- **focus**：G3 + G9
- **世界参考**：摄影暗房与胶片工艺——安全灯红光、显影液里慢慢显影的相纸、胶片齿孔、放大机投下的光束
- **unforgettable**：显影——一切从黑暗中柔光浮现（blur-in 显影式入场 + accent 辉光托底），胶片齿孔条压住页缘
- **分化声明**：与 c2 分化于 L1/L2/L4/L5/L6——d2 琥珀更亮更橙、c2 暖金暗哑；d2 标题 400–500 偏细 + 斜体强调、c2 标题 500–600 恒重；d2 母题是胶片齿孔/光束角标/显影晕、c2 是标本引线/编号签/叶脉分叉线；d2 容器无框立场只许辉光托底、c2 是 1px 细描边直角图鉴卡；d2 签名动效是 blur-in 显影 + 覆盖缓动为更慢的浮出曲线、c2 是 draw-line 叶脉生长（L3 两者同为 glow/cover，不计入分化——拉开靠的是 L4/L5/L6）
- **material_world**：摄影暗房——安全灯琥珀光下，银盐相纸在显影液中浮现，胶片齿孔记录时间，空气中有药液微粒（HTML 版是这个世界的线框图，bake 版是这个世界的高清照片）
- **anti_lazy**：不要因为是暗色主题就加星空/宇宙元素——暗房不是夜空；不要因为是胶片就加电影院银幕边框——齿孔条只许一条，不许变成画框；不要用高亮度白光——暗房唯一的光源是安全灯，白光会毁了这个主题

**G1 color**

```css
--paper:#14110e; --paper-tint:#211b16;
--ink:#f0e6d8;   --ink-tint:#2c241d;
--accent:#e8a34c; --accent-on:#14110e;
```

- **accent 预算**：内容页 accent 面积 ≤5%（暖金是暗房里的灯，只点一两处：辉光托底、光束角标、关键数字）；满屏 accent 禁止——暗房没有开大灯的时刻；首尾闭环：封面辉光开场 → 收束页同位辉光呼应（可略强）。
- **暗底 token 语义**：`--ink-tint` 是比 `--paper` 更深的暗角色（只用于做旧暗角/沉底层次，**不是次级文字色**）；次级文字一律走 `color-mix(in srgb, var(--ink) X%, transparent)` 明度阶梯。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 400–500 偏细、正文 400——氛围靠辉光而非字重，暗场衬线偏细更空
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：衬线偏细立场：≥77px→400–500；35–76px→400–500；正文 400；14–16px 小字 500
- **标题修饰**：斜体强调（西文/引文用 italic 点睛，中文不全句斜体）

**G3 texture**

```css
--texture-type: glow;
--texture-layer: radial-gradient(120% 90% at 70% 10%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 60%);
--texture-scope: cover;
```

- **立场**：glow——仪式页上方一团琥珀辉光，是放大机投下的光束也是安全灯；正文页纯暗，内容靠自己"显"出来
- **material**：胶片相纸——银盐乳剂面的微颗粒，安全灯琥珀光下的显影液反光
- **light**：安全灯单点光源——琥珀色、低亮度、有方向性，从上方 70° 投射
- **css_recipes**：["film-grain", "light-leak", "aged-fade"]

**G4 shape**

- **圆角**：0–4px（胶片是工业切片，几乎不用圆角）
- **hairline**：少用——暗房里边界靠光不靠线；必要时 1px solid color-mix(in srgb, var(--ink) 22%, transparent)
- **阴影**：无硬阴影；唯一允许的"影"是 accent 低透明辉光托底（`.mt-drk-halo`）
- **容器造型**：无框 + 辉光底——容器不描边、不出卡片、不落厚色块，用显影晕柔光把内容从暗底中"显"出来；禁硬投影、禁满版色块（无框是与 c2 图鉴卡立场相反的 L5 分界——暗房的边界是光不是线）
- **高密度容器边界**：显影晕辉光托底（`.mt-drk-halo`）——暗底上 accent 低透明柔光晕即容器边界，是"面"的光学形态；同页同构叠用、间距恒定，容器边界义务由辉光承担而非描边

**G5 motion**

- **气质**：calm（ambience 型归入沉静：慢速、低强度、只动主角）
- **强度上限**：低
- **锚点偏好**：blur-in 显影式入场为签名——标题与图像如相纸在显影液中浮现；数据页 draw-line 可用但不做主角，count-up 只给真正的 KPI 英雄页
- **节奏偏移**：时长档 +1（显影是慢过程，急不得）
- **缓动签名**：覆盖 `--ease-out` 为 cubic-bezier(.1,.7,.2,1)——更慢更柔的浮出曲线，像影像从药水里长出来
- **禁用**：无（calm 气质本身排除硬切/弹跳/字符噪点类）
- **fx 许可**：starfield、particle-drift（暗场星点与药液浮尘；constellation 连线感太硬，禁）

**G8 component**

- **亲和**：巨字宣言（暗场巨字 + 辉光托底，暗房最正当的仪式感）、裂屏对开（明/暗对撞 = 负片/正片、曝光/遮光）
- **禁忌**：禁密集网格矩阵（暗场堆格子像档案柜，不属于暗房）；数据英雄页保持大留白，图表以 accent 单系列描线为主

**G9 motif**

- **词汇**：胶片齿孔条（`.mt-drk-film`：12px 方孔 repeating 边带，只许页面上缘或下缘横贯一条）/ 光束角标（`.mt-drk-beam`：细长三角光楔从页角射入，accent 低透明，每页至多 1 个、只许仪式页）/ 显影晕（`.mt-drk-halo`：accent 低透明 radial 柔光托底，是无框容器唯一的"边界"）/ 胶片颗粒层（`.mt-drk-grain`：feTurbulence 银盐颗粒满版层，正文页细颗粒 baseFrequency 0.6、opacity 0.04–0.05；仪式页用 `.mt-drk-grain-lg` 粗颗粒 0.9、opacity ≤0.06——配方 film-grain）/ 漏光光斑（`.mt-drk-leak`：琥珀 radial 大光斑 + blur(40px) + screen 混合，只许页面上缘或侧缘被裁切，opacity ≤0.15，每页至多 1 个、只许仪式页——配方 light-leak）/ 做旧色调（`.mt-drk-aged`：暖色 soft-light 罩 + 四角暗角，模拟相纸微微泛黄与边缘曝光不足，只许仪式页——配方 aged-fade）

```css
/* D2 柔光暗房 · 装饰母题 + 缓动签名 */
:root{--ease-out:cubic-bezier(.1,.7,.2,1)}
.mt-drk-film{height:26px;pointer-events:none;background-image:linear-gradient(90deg,color-mix(in srgb,var(--ink) 55%,transparent) 0 12px,transparent 12px 24px);background-size:24px 12px;background-repeat:repeat-x;background-position:0 50%;opacity:.6}
.mt-drk-beam{position:absolute;pointer-events:none;width:200px;height:200px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 20%,transparent),transparent 65%);clip-path:polygon(0 0,100% 0,0 100%)}
.mt-drk-halo{position:relative}
.mt-drk-halo::before{content:"";position:absolute;inset:-12%;pointer-events:none;background:radial-gradient(65% 65% at 50% 60%,color-mix(in srgb,var(--accent) 13%,transparent),transparent 70%)}
.mt-drk-grain{position:absolute;inset:0;pointer-events:none;opacity:.05;background-image:url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22240%22 height=%22240%22%3E%3Cfilter id=%22g%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.6%22 numOctaves=%222%22 stitchTiles=%22stitch%22/%3E%3CfeColorMatrix type=%22saturate%22 values=%220%22/%3E%3C/filter%3E%3Crect width=%22240%22 height=%22240%22 filter=%22url(%23g)%22/%3E%3C/svg%3E")}
.mt-drk-grain-lg{position:absolute;inset:0;pointer-events:none;opacity:.06;background-image:url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22240%22 height=%22240%22%3E%3Cfilter id=%22g%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.9%22 numOctaves=%222%22 stitchTiles=%22stitch%22/%3E%3CfeColorMatrix type=%22saturate%22 values=%220%22/%3E%3C/filter%3E%3Crect width=%22240%22 height=%22240%22 filter=%22url(%23g)%22/%3E%3C/svg%3E")}
.mt-drk-leak{position:absolute;top:-18%;right:-10%;width:52%;aspect-ratio:1;pointer-events:none;background:radial-gradient(50% 50% at 50% 50%,color-mix(in srgb,var(--accent) 55%,transparent),transparent 70%);filter:blur(40px);mix-blend-mode:screen;opacity:.14}
.mt-drk-aged{position:absolute;inset:0;pointer-events:none;mix-blend-mode:soft-light;background:radial-gradient(120% 100% at 50% 42%,color-mix(in srgb,var(--accent) 9%,transparent) 28%,transparent 60%),radial-gradient(135% 115% at 50% 50%,transparent 66%,color-mix(in srgb,var(--ink-tint) 62%,transparent))}
```

- **禁忌**：齿孔条禁竖放、禁多于一组边带；光束角标禁压正文文字；显影晕禁叠在任何描边卡上（无框立场）；颗粒层 opacity 禁超 0.06（颗粒是肌理不是噪点，看得见颗粒的边缘就够）且禁压图表数据区之外的阅读焦点——它铺满全页但必须安静；漏光光斑禁出现在页面中段、禁压标题字面、禁与光束角标同页叠加（一页只许一个光源叙事）；做旧色调只许仪式页，正文页做旧会拖累可读性；母题件一律 `data-editable-skip`

**bake_brief**

```json
{
  "visual_direction": "a photographic darkroom under a single amber safelight — silver-gelatin prints surfacing in developer trays, film perforation strips marking time, liquid particles in the air, everything emerging from darkness through soft amber glow, quiet analogue reverence",
  "palette_rule": "amber is light, not pigment: it appears only as glow, halo, beam and one or two focal accents (≤5% area on content pages); the ground stays deep umber-black, text stays warm ivory; forbid large amber fills, white light sources, cold blue tones, starfield/cosmic imagery, and any hue outside the umber / ivory / amber triad",
  "typography_bake": "主标题重构词汇：显影定格——衬线标题如相纸显影过程中定格在最清晰的一帧，笔画边缘带极轻微显影柔化（不是模糊，是乳剂感）；负片反白——关键词可做负片式反白块（暗字亮底小面积）；齿孔定位——标题区可与一条胶片齿孔边带对齐，字面与齿孔有毫米级前后层次；断行在语义边界，西文/引文 italic 点睛，中文不全句斜体；细衬线大字号（400–500 字重感）靠辉光托底而非加粗",
  "uplift": "升维路径（HTML 做不到的物理维度）：银盐颗粒的物理肌理——不是数字噪点，是乳剂层微晶体在安全灯下的细密反光，暗部颗粒更可见；显影液的光学折射——琥珀光斑边缘带轻微色散，像光穿过液体；相纸的白边与胶片齿孔的物理厚度——纸基微微翘起、齿孔有冲压的凹凸；安全灯的单点方向性——所有明暗过渡都从同一上方光源推理，亮部暖、暗部冷褐；显影晕的纵深——内容从黑暗中浮现时，辉光有前后层次而非平面光圈",
  "material_anchor": "silver-gelatin photographic paper + amber safelight + developer liquid optics + film perforation",
  "viewing_sequence": [
    "第一眼：暗场中一团琥珀辉光和标题剪影——先感到暗房的安静与光",
    "第二眼：发现胶片颗粒纹理、齿孔边带与光斑边缘的色散——材料的物理细节",
    "第三眼：阅读文字，感受暗房的时间感——信息最后抵达，像影像慢慢显影"
  ],
  "anti_lazy": [
    "不要因为是暗色主题就加星空/宇宙元素——暗房不是夜空",
    "不要因为是胶片就加电影院银幕边框——齿孔条只许一条，不许变成画框",
    "不要用高亮度白光——暗房唯一的光源是安全灯，白光会毁了这个主题"
  ],
  "allowed": "film perforation strip (single horizontal band, top or bottom page edge only), amber glow halos lifting content out of darkness, soft light-leak blobs clipped by page edges (single per page, ritual pages only), fine silver grain texture across the whole surface, thin triangular light wedges from page corners, italic Latin quotes, warm ivory serif display type, subtle vignette and aged warm cast on ritual pages, negative-style reversed text blocks in small areas",
  "avoid": "starfields, cosmic or nebula imagery, cinema screen frames, white or cold-blue light, LED/neon glow, hard shadows, bordered cards or boxes, filled color panels, rounded UI components, gradient meshes, photorealistic faces, cluttered collage, high-saturation fills, page header/footer chrome, anything that reads as digital interface rather than photographic process",
  "layout_blueprints": {
    "cover": [
      {"position": "top or bottom edge", "count": 1, "labels": ["胶片齿孔条边带（横贯一条）"]},
      {"position": "upper area", "count": 1, "labels": ["琥珀辉光团（安全灯/放大机光束，标题托底）"]},
      {"position": "center", "count": 1, "labels": ["显影定格主标题（细衬线、辉光托底）"]},
      {"position": "below title", "count": 2, "labels": ["一行副题", "一行小字署名/日期"]},
      {"position": "page edge", "count": 1, "labels": ["漏光光斑（被页缘裁切，至多一个）"]}
    ],
    "divider": [
      {"position": "top or bottom edge", "count": 1, "labels": ["胶片齿孔条边带"]},
      {"position": "center", "count": 1, "labels": ["章节序号或章节题（显影式浮现，辉光托底）"]},
      {"position": "corner", "count": 1, "labels": ["光束角标（细长三角光楔，至多一个）"]},
      {"position": "background", "count": 1, "labels": ["粗颗粒层 + 做旧暖调（仪式页特权）"]}
    ],
    "key-message": [
      {"position": "center 60%", "count": 1, "labels": ["2–8 字核心词巨字（显影定格，琥珀辉光托底）"]},
      {"position": "top", "count": 1, "labels": ["一行 kicker（mono 小字，宽字距）"]},
      {"position": "edge", "count": 1, "labels": ["漏光光斑或光束角标（二选一）"]},
      {"position": "background", "count": 1, "labels": ["颗粒层（全页细密银盐颗粒）"]}
    ],
    "analysis": [
      {"position": "top", "count": 1, "labels": ["标题 + kicker（无辉光托底，正文页纯暗）"]},
      {"position": "center", "count": 1, "labels": ["核心内容区（无框，显影晕柔光分组）"]},
      {"position": "left and right", "count": 2, "labels": ["辅助模块（显影晕边界）", "辅助模块"]},
      {"position": "background", "count": 1, "labels": ["细颗粒层（安静的全页肌理）"]}
    ]
  },
  "rendering_constraints": [
    "The page must read as a photographic darkroom scene, not a generic dark PPT template, not a starfield, not a cinema.",
    "Amber is light: it renders as glow, halo, beam or light-leak with soft falloff — flat amber fills and amber borders are forbidden.",
    "The single light source is the amber safelight above; all shading must be consistent with one directional source, no white or cold fill light.",
    "Silver grain covers the whole surface quietly: visible in shadow areas, never louder than the text; it is emulsion texture, not digital noise.",
    "Exactly one lead light motif per page (halo OR leak OR beam); the rest stay subordinate — never stack all light effects at equal intensity.",
    "The main title must read as a frame frozen mid-development: slightly softened serif strokes with a glow pedestal — plain bold type on flat black is a failure.",
    "No bordered cards or boxes anywhere: content groups are separated by glow halos and spacing only — the darkroom's boundary is light, not line.",
    "Cover/divider/key-message pages: one giant title, one kicker, at most one subtitle plus one small annotation line; forbid 5 or more text modules.",
    "Film perforation appears at most once per page as a single horizontal edge band — never vertical, never a full frame, never a screen bezel.",
    "Chinese strokes must render accurately; title legibility outranks atmosphere — keep the title zone quiet and the glow behind, not over, the type.",
    "Do not invent logos, watermarks, camera icons, or brand marks."
  ]
}
```

**Variants 配色变体**

#### 银盐

- **气质**：黑白银盐相纸的冷调——暖灯关掉，只剩月光白的显影盘，适合建筑/纪实/极简影像

```css
--paper:#14110e; --paper-tint:#211b16;
--ink:#f0e6d8;   --ink-tint:#2c241d;
--accent:#C0C8D0; --accent-on:#14110e;
```

#### 安全灯红

- **气质**：暗房安全灯的忠实采样——红是暗房里唯一被允许的光，氛围最强、使用最克制

```css
--paper:#14110e; --paper-tint:#211b16;
--ink:#f0e6d8;   --ink-tint:#2c241d;
--accent:#C0392B; --accent-on:#f0e6d8;
```

- **accent 预算**：红光下辉光即安全灯本灯，正合世界；但红 accent 面积预算从严——≤5% 不变且永不满屏，正文文字一律保持 ink 不落红
