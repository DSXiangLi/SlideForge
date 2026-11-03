# G4 靛墨黄页

- **id**：g4
- **气质**：暖纸 + 靛蓝墨 + 太阳黄出血——双年展海报的高长调张力，黄与靛的互补对撞
- **适用**：设计提案、建筑与艺术、文化机构年报、展览开幕、创意作品集
- **focus**：G1 + G8
- **世界参考**：威尼斯双年展海报与画廊图录——互补色对撞、出血版式、展览编号系统
- **unforgettable**：黄底出血版——整页太阳黄 + 靛蓝巨字（互补对撞的全亮页），与纸底靛墨页交替翻页即节奏
- **分化声明**：与 b1 分化于 L1/L4/L5/L7——b1 灰白底 + 克莱因蓝单点 + 网格矩阵纪律；g4 暖纸底 + 靛蓝全墨化 + 太阳黄出血面料 + 黄/靛裂屏对撞构图亲和 + 展览编号签母题

**本质规范**（从 unforgettable 推理出的骨架硬规则——所有 G1–G9 规范须服从）

| # | 维度 | 规范 | 推理路径 |
|---|---|---|---|
| 1 | 氛围 | 威尼斯双年展海报——互补色对撞的展览印刷物 | 双年展不是编辑部，是展览现场 |
| 2 | 容器 | 黄底色面 + 靛蓝结构线框——容器即色面，出血是合法的 | 海报的容器是色面不是描边卡，色面可顶到页缘 |
| 3 | 分隔 | 1.5px solid var(--ink) 结构线——不是 1px hairline | 发丝线是杂志词汇，海报的线是承重结构线 |
| 4 | 层次 | 色面出血对比——黄底与靛墨交替翻页即节奏 | 纵深靠互补色对撞，不靠投影 |
| 5 | 版式 | 海报式不对称出血——不是居中内容带 | 海报是出血的，不是居中的 |
| 6 | 入场 | wipe-clip 硬揭示——色面滑入如印版落纸 | 海报是印版落纸的物理感，不是通用淡入 |
| 7 | 底色 | 暖纸底 + 太阳黄出血面交替——黄是面料不是装饰 | 黄底是海报的本体，满版黄出血是常态页型 |
| 8 | 字色 | 靛蓝全文字色——黄底上也是靛字 | 靛蓝是唯一文字色，黄是底面不是字色 |

**骨架硬规则**（生成侧必须遵从）：
- **禁 masthead / mastfoot**——海报不需要编辑部刊头刊脚
- **禁 `.reveal` 通用入场（非标题元素）**——标题已用 wipe-clip 是对的；非标题元素的 `.reveal` 须替换为 `data-anim="wipe-clip"` 或 `data-anim="rise-in"`
- **禁居中内容带布局**（`display:flex;flex-direction:column;justify-content:center`）——用海报式不对称出血：色面承载内容，不对称排布
- **禁发丝线 hairline**——分隔用 1.5px solid var(--ink) 结构线或色面边缘
- **禁 box-shadow**——纵深靠色面出血对比

**G1 color**

```css
--paper:#E9E5DB; --paper-tint:#DDD8CB;
--ink:#1B2566;   --ink-tint:#2A3374;
--accent:#F1EE2E; --accent-on:#1B2566;
--accent-2:#E26B4A; --accent-2-on:#FAF1E2;
```

- **accent 预算**：黄是面料不是针线——**满版黄出血页是常态页型**（不是封面特权），与纸底靛墨页交替构成翻页节奏；靛蓝是唯一文字色（黄底上也是靛字）；余烬橙（accent-2）单点纪律：只给"本页最重要的那一件"（一个数字/一条标注/一枚签），内容页 ≤2%；首尾闭环：黄底靛标开场 → 收束页黄底 + 展览编号呼应。
- **多色立场**：互补双色封闭对（太阳黄 × 靛蓝，60°/235° 高长调）+ 余烬橙单点——禁第四彩色；分配规则：黄=底面/出血块/色带，靛=全部文字与结构线，橙=单点注意力；双主角纪律：黄与靛同页面积必分主客（8:2 或 2:8），五五对撞禁止（裂屏对开除外——那里对撞即内容）。

**G2 typography**

```css
--font-display:"Helvetica Neue","Arial Black","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 700–900（海报粗黑，拉丁可落 Arial Black）、正文 400——双年展的粗字排
- **字号对比**：主标题:正文 ≥8:1（低密度）；巨字特档 10:1（海报页）；高密度 ≥5:1
- **字重映射**：海报恒重立场：≥77px→800–900；35–76px→700；正文 400；14–16px 小字 500–600
- **标题修饰**：拉丁标题全大写 + 宽字距（海报字排）；展览编号前缀（G9）
- **metric_fallback**：display→Helvetica Neue/Arial Black；body→Helvetica Neue/PingFang SC；mono→SF Mono/Menlo

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——海报是平网印刷，肌理在纸色本身（暖纸灰），不另加纹理

**G4 shape**

- **圆角**：0
- **hairline**：1.5px solid var(--ink)——靛蓝结构线，黄底上同样成立
- **阴影**：无
- **容器造型**：三色块卡（纸档 / 黄面 accent / 靛面 ink 反白）——容器即色面，出血是合法的（色面可顶到页缘）；禁描边卡、禁圆角、禁玻璃
- **高密度容器边界**：纸档面 + 靛结构线分区；黄面只给焦点区（单焦点纪律在黄面料上的形态）

**G5 motion**

- **气质**：dramatic
- **强度上限**：默认
- **锚点偏好**：wipe-clip 硬揭示（色面滑入如印版落纸）；巨字 chars 逐字落版；count-up 只给 KPI
- **节奏偏移**：时长档 −1（利落）
- **缓动签名**：默认三 token，不覆盖
- **禁用**：blur-in / scale-pop（柔焦与弹跳都不是海报）
- **fx 许可**：全禁

**G8 component**

- **亲和**：裂屏对开（黄/靛对撞是它的原生形态）、巨字宣言（海报巨字）、网格矩阵（展览墙格子）
- **禁忌**：禁轴与节点的细线流程（海报不画流程图）；图表多系列走靛墨（ink）明度阶梯（`color-mix(in srgb, var(--ink) X%, var(--paper))` 逐页 section 内联），太阳黄只作唯一焦点系列；不用 Ghost 残影字（杂志系词汇）

**G9 motif**

- **词汇**：展览编号签（`.mt-bie-num`——mono 大字号靛蓝描边空心数字，页角或版缘，双年展的展位编号感）/ 黄楔出血块（`.mt-bie-wedge`——页缘太阳黄矩块，出血结构件）/ 双色对撞带（`.mt-bie-band`——黄 + 靛上下双色横带，页缘收束）

```css
/* G4 靛墨黄页 · 装饰母题 */
.mt-bie-num{font-family:var(--font-mono);font-weight:700;line-height:1;color:transparent;-webkit-text-stroke:1.5px var(--ink);pointer-events:none}
.mt-bie-wedge{position:absolute;background:var(--accent);pointer-events:none}
.mt-bie-band{display:block;height:14px;background:linear-gradient(180deg,var(--accent) 50%,var(--ink) 50%)}
```

- **禁忌**：编号签每页至多一枚且只作页码/展位号语义；黄楔每页至多一条且必须出血（浮在版心即杂耍）；对撞带只许页缘横贯；母题件一律 `data-editable-skip`（`.mt-bie-num` 为文本载体类母题，数字可编辑）

**Variants 配色变体**

#### 夜场靛蓝

- **气质**：靛蓝满铺底 + 黄墨——海报的夜场版，适合晚间活动、开幕酒会、音乐现场

```css
--paper:#1B2566; --paper-tint:#2A3374;
--ink:#E9E5DB;   --ink-tint:#3A4485;
--accent:#F1EE2E; --accent-on:#1B2566;
--accent-2:#E26B4A; --accent-2-on:#FAF1E2;
```

#### 白立方

- **气质**：白墙画廊底——最克制的一档，黄只在出血块与焦点，适合机构年报、学术出版

```css
--paper:#FAFAF7; --paper-tint:#EFEFEA;
--ink:#1B2566;   --ink-tint:#2A3374;
--accent:#F1EE2E; --accent-on:#1B2566;
--accent-2:#E26B4A; --accent-2-on:#FAF1E2;
```
