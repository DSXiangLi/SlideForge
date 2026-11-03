# E1 孔版印刷

- **id**：e1
- **气质**：大豆油墨 + 荧光专色双辊 + 套色错位，独立出版 zine 的手工印刷感与不完美的生命力
- **适用**：创意/设计/艺术分享、青年文化与亚文化主题、工作坊与社区活动、独立出版、任何"反精致"立场的表达
- **focus**：G3 + G9
- **世界参考**：Riso 孔版印刷与独立出版 zine 文化——大豆油墨专色滚筒、手工装订小志、套色不准的"印刷事故美"、网目调与颗粒噪点
- **unforgettable**：套色错位——同一形状两层油墨错开 2–3px 叠印出的重影色边，一眼 riso；没有错位就是骗子主题
- **分化声明**：与 d3 分化于 L2/L4/L5/L6——d3 是楷体手绘字排、笔触块/虚线圈注/画框双描边母题、不规则有机圆角容器、calm 气质的 draw-line 慢描绘；e1 是粗黑无衬线海报字排、套色错位叠印块/裁剪虚线/网目调母题、微旋转拼贴卡容器、playful 气质的 scale-pop 蹦贴节奏

**本质规范**（从 unforgettable 推理出的骨架硬规则——所有 G1–G9 规范须服从）

| # | 维度 | 规范 | 推理路径 |
|---|---|---|---|
| 1 | 氛围 | 印刷车间的成品——纸有触感，油墨有颗粒，套印有错位 | riso 不是编辑部，是印刷工坊 |
| 2 | 容器 | 微旋转拼贴卡——直角纯色块整体 ±1.5° 旋转，像随手贴上去的纸片 | zine 的页面是贴出来的，不是排版排出来的 |
| 3 | 分隔 | 裁剪虚线（dashed）——剪刀沿线的手工暗示 | 发丝线是杂志词汇，zine 的线是剪刀线 |
| 4 | 层次 | 套色叠印——双色 multiply 叠出第三色调 | 深度来自印刷工艺，不来自阴影 |
| 5 | 版式 | 拼贴散布——内容在拼贴卡上分布，不居中排列 | zine 是拼贴世界，不是编辑部版式 |
| 6 | 入场 | scale-pop 蹦贴上墙——拼贴卡的物理落位感 | 纸片是"贴"上去的，不是"淡入"的 |
| 7 | 底色 | 旧纸面（--paper）+ 全场半调点纹 | 印刷世界的基底是纸和油墨颗粒 |
| 8 | 字色 | 粗黑印纸面——文字永远落在纸上，深色只来自叠印 | 油墨印纸，riso 世界不存在深色容器 |

**骨架硬规则**（生成侧必须遵从）：
- **禁 masthead / mastfoot**——zine 不需要编辑部刊头刊脚，手工装订的小志不需要家具
- **禁 `.reveal` 通用入场**——用 `data-anim="scale-pop"` 替代（拼贴卡蹦贴上墙）
- **禁居中内容带布局**（`display:flex;flex-direction:column;justify-content:center`）——用拼贴散布：内容分布在微旋转的拼贴卡上，卡片位置不对称
- **禁发丝线 hairline**——分隔用裁剪虚线（`.mt-ris-cut`）或套印色面边缘
- **禁 box-shadow**——深度靠套色叠印的 multiply 混色
- **禁 ink/ink-tint 深底容器**——深色只来自套印的视觉后果，不作容器填充

**G1 color**

```css
--paper:#f7f2e6; --paper-tint:#ece5d3;
--ink:#221d16;   --ink-tint:#332c22;
--accent:#FF48B0; --accent-on:#fdfaf3;
--accent-2:#0078BF; --accent-2-on:#f2f8fc;
```

- **accent 预算**：内容页 accent 面积 ≤10%（荧光专色给错位叠印块/网目调块/单强调词——专色油墨是滚筒上一整支，但版面里只准点染）；满屏荧光 accent 是封面/收束特权（riso 海报的整版荧光单色是它的原生形态）；首尾闭环：封面荧光专色满版 + 错位巨标开场 → 收束页同色错位叠印条带呼应（半亮：accent 淡档色块）。
- **多色立场**：双墨辊封闭制——本世界只有两支滚筒（accent 主辊 + accent-2 副辊），禁第三支；分配规则：套色错位叠印块必须双色（主辊 + 副辊错 2–3px，multiply 叠出第三色调——这是 riso 多版印刷的本质），其余装饰件仍归主辊；注意力预算：满版特权只归主辊 accent，副辊永不满版。

**G2 typography**

```css
--font-display:"Helvetica Neue","Arial Black","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"Courier New","SF Mono","JetBrains Mono",monospace;
```

- **字重倾向**：标题 700–900（海报粗黑，拉丁落 Arial Black 档）、正文 400–500——zine 的对比是油墨与纸，不是字重阶梯
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：粗黑恒重立场（不走倒挂——zine 标题越大越要黑，细大标题在厚纸上发飘）：≥77px→800–900；35–76px→700–800；正文 400；14–16px 小字 500–600
- **标题修饰**：标题/关键词后垫套色错位叠印块（G9 `.mt-ris-misreg`），字体本身不加修饰

**G3 texture**

```css
--texture-type: grain;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E"), radial-gradient(circle at 1px 1px, color-mix(in srgb, var(--ink) 8%, transparent) 1px, transparent 1.6px) 0 0 / 4px 4px, radial-gradient(70% 60% at 75% 85%, color-mix(in srgb, var(--accent) 4%, transparent), transparent 65%);
--texture-scope: all;
```

- **立场**：颗粒 = 材质本体——riso 大豆油墨的颗粒感与滚筒上墨不均是这个世界的一部分，全页许可（scope all），正文页也铺，但仍需生成侧逐页 `texture-on` 落码

**G4 shape**

- **圆角**：0–2px（剪纸拼贴以直角为主，zine 没有工业圆角）
- **hairline**：1px dashed color-mix(in srgb, var(--ink) 38%, transparent)——裁剪虚线隐喻（剪刀沿线的 zine 手工感），实线 hairline 只给图表轴
- **阴影**：无投影——"厚度"由套色错位块的双层叠印承担（G9），纸面世界不吃弥散阴影
- **容器造型**：微旋转拼贴卡——直角纯色块（paper-tint / accent 淡档 / **套印色面** `.mt-ris-field`）整体 `transform: rotate(±1.5°)`，像 zine 页面上随手贴上去的纸片；大面积内容区可垫套印色面（双版叠印即容器工艺）；**只有纸面系容器**——ink/ink-tint 深底容器禁止（深色只来自套印的视觉后果）；禁精密直角网格对齐的强迫症排布、禁玻璃拟态、禁描边窗口
- **高密度容器边界**：微旋转拼贴卡面——paper-tint / accent 淡档纸片整体 ±1.5° 旋转上墙，贴上去的纸即边界；需要更强分区时垫套色错位块（G9）而非描边，拼贴世界没有框

**G5 motion**

- **气质**：playful
- **强度上限**：默认
- **锚点偏好**：scale-pop 为签名锚点——拼贴卡/叠印块蹦贴上墙的弹感；封面标题 chars 错落阶梯入场（逐字如逐色滚筒套印）；数据页 rise-in 轻上浮，禁数据端过度编排
- **节奏偏移**：时长档默认；阶梯步长 60–90ms（拼贴逐件上墙的节奏）
- **缓动签名**：覆盖 `--ease-out` 为 cubic-bezier(.3,1.4,.4,1)——轻微过冲回弹，纸片落位的物理感
- **禁用**：typewriter / scramble（打字机是终端词汇）/ blur-in（模糊不属于油墨与纸）
- **fx 许可**：全禁（颗粒与拼贴是材质不是像素仪式，canvas 粒子不属于印刷世界）

**G8 component**

- **亲和**：图文证据（拼贴画页是它的原生形态）、巨字宣言（海报式粗黑巨字 + 错位叠印）、裂屏对开（zine 跨页对撞）
- **禁忌**：禁连续两页网格矩阵——zine 是拼贴不是货架；禁绝对对齐洁癖：相邻拼贴件允许 ±1.5° 微旋转与轻微破格出血；图表须收编进拼贴卡（纸贴图表），禁裸图表直角网格页

**G9 motif**

- **词汇**：套色错位叠印块（`.mt-ris-misreg`：主辊 + 副辊双色版错 2–3px 叠印 + multiply 混色叠出第三色调，垫在标题/关键词后，每页 ≤2 处）/ 套印色面（`.mt-ris-field`：大面积双版套印——色块容器/图版垫底，错位量随面积放大到 4px，双色 multiply 叠出第三色，是 riso 多版印刷的真正主力形态）/ 裁剪虚线（`.mt-ris-cut`：dashed 分隔线，剪刀沿线的手工暗示）/ 网目调点块（`.mt-ris-halftone`：accent 半调点阵，只许页面角落或色块边缘低透明，模拟 riso 挂网） / 全场半调点纸纹层（`.mt-ris-halftone-full`：4px 周期半调点阵铺满版心，16% 透明度，锚定 riso 挂网质感——是全场底纹锚定而非角落装饰）/ 双辊色缎带（`.mt-ris-belt`：accent + accent-2 两色横条 ±22° 旋转扫过，封面/收束专用，呼应双辊套印）/ 荧光戳记（`.mt-ris-stamp`：accent 底 + paper 字 + 粗黑字排 + -3° 旋转，限量/独家/手工编号标记）

```css
/* E1 孔版印刷 · 装饰母题 + 缓动签名 */
:root{--ease-out:cubic-bezier(.3,1.4,.4,1)}
.mt-ris-misreg{position:relative;isolation:isolate}
.mt-ris-misreg::before,.mt-ris-misreg::after{content:"";position:absolute;inset:-.12em -.3em;z-index:-1;mix-blend-mode:multiply}
.mt-ris-misreg::before{background:color-mix(in srgb,var(--accent) 80%,transparent);transform:translate(-2.5px,2px)}
.mt-ris-misreg::after{background:color-mix(in srgb,var(--accent-2) 55%,transparent);transform:translate(2.5px,-2px)}
.mt-ris-field{position:relative;isolation:isolate;background-image:repeating-linear-gradient(45deg,transparent,transparent 20px,color-mix(in srgb,var(--ink) 6%,transparent) 20px,color-mix(in srgb,var(--ink) 6%,transparent) 40px)}
.mt-ris-field::before,.mt-ris-field::after{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;mix-blend-mode:multiply}
.mt-ris-field::before{background:color-mix(in srgb,var(--accent) 75%,transparent);transform:translate(-4px,3px)}
.mt-ris-field::after{inset:8% 6%;background:color-mix(in srgb,var(--accent-2) 55%,transparent);transform:translate(4px,-3px)}
.mt-ris-cut{border:none;border-top:1px dashed color-mix(in srgb,var(--ink) 38%,transparent)}
.mt-ris-halftone{position:absolute;pointer-events:none;background-image:radial-gradient(color-mix(in srgb,var(--accent) 55%,transparent) 1.2px,transparent 1.7px);background-size:9px 9px;opacity:.5}
.mt-ris-halftone-full{position:absolute;inset:0;pointer-events:none;background-image:radial-gradient(color-mix(in srgb,var(--ink) 55%,transparent) 1px,transparent 1.6px);background-size:4px 4px;opacity:.16;z-index:0}
.mt-ris-belt{position:absolute;pointer-events:none;overflow:hidden;opacity:.85}
.mt-ris-belt::before,.mt-ris-belt::after{content:"";position:absolute;height:100%;width:40%;transform:rotate(22deg)}
.mt-ris-belt::before{background:color-mix(in srgb,var(--accent) 70%,transparent);left:-5%}
.mt-ris-belt::after{background:color-mix(in srgb,var(--accent-2) 55%,transparent);right:-5%;transform:rotate(-22deg)}
.mt-ris-stamp{display:inline-block;background:var(--accent);color:var(--paper);font-family:var(--font-mono);font-weight:800;font-size:14px;letter-spacing:.12em;padding:.3em .7em;transform:rotate(-3deg);text-transform:uppercase}
```

- **禁忌**：错位量文字垫 2–3px、色面 4px 烧死——超过即成故障而非工艺；错位块每页 ≤2 处且只垫重点（处处错位即脏污）；套印色面每页 ≤1 面（大面积工艺是主角不是墙纸）；网目调禁铺满版心；**对比度铁律：文字永远落在纸面（paper/paper-tint）上——油墨印纸，riso 世界不存在深色容器**；套印色面上只许压 ≥56px 的粗黑 ink 海报标题（印字于色是海报工艺），正文与标签禁压套印面；禁 ink/ink-tint 深底容器（深色只许来自 multiply 叠印区的视觉后果，不作容器填充）；`.mt-ris-misreg` 是文本载体类母题（加在真实文本上，文本保持可编辑），`.mt-ris-field` 内内容须自带 position 层级，其余母题件一律 `data-editable-skip`

**Variants 配色变体**

#### Riso 蓝

- **气质**：只换墨辊——荧光粉滚筒换成 Riso 蓝，同一台机器同一批纸，冷静清爽——技术社区、独立杂志、音乐与现场文化

```css
--paper:#f7f2e6; --paper-tint:#ece5d3;
--ink:#221d16;   --ink-tint:#332c22;
--accent:#0078BF; --accent-on:#f2f8fc;
--accent-2:#FF48B0; --accent-2-on:#fdfaf3;
```

#### 向日葵黄

- **气质**：只换墨辊——向日葵黄专色，最"印刷车间"的一档，明度高、噪点下最出颗粒——青年文化、市集/展览、轻品牌

```css
--paper:#f7f2e6; --paper-tint:#ece5d3;
--ink:#221d16;   --ink-tint:#332c22;
--accent:#FFB511; --accent-on:#221d16;
--accent-2:#FF48B0; --accent-2-on:#fdfaf3;
```

- **accent 预算**：荧光黄明度饱和双高——错位块/半调块面积再收一半（内容页 ≤5%），满屏黄仅封面；黄底上的文字一律 ink 不用 accent-on；其余同基底口径
