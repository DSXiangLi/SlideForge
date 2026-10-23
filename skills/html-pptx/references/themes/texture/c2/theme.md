# C2 暗夜植物园

- **id**：c2
- **气质**：暗夜纸面上浮一层暖金灯光，像翻开一本 19 世纪植物图鉴——沉静、精确、有学术温度
- **适用**：自然/博物/文化/人文类分享，研究型叙事，慢节奏深度内容
- **focus**：G3 + G9
- **世界参考**：19 世纪植物学版画图鉴与标本签——夜观植物园里的标本线描、拉丁学名斜体标注、图鉴编号签条
- **unforgettable**：标本引线标注 + 图鉴编号签——细线引线把标本图与图注缝在一起，mono 小签条像标本柜抽屉上的标签
- **分化声明**：与 d2 分化于 L1/L2/L4/L5/L6——c2 暖金暗哑、d2 琥珀更亮更橙；c2 标题 500–600 恒重、d2 标题 400–500 偏细且带斜体强调；c2 母题是标本引线/编号签/叶脉分叉线、d2 是胶片齿孔/光束角标/显影晕；c2 容器是 1px 细描边直角图鉴卡、d2 无框立场只用辉光托底；c2 签名动效是 draw-line 叶脉生长、d2 是 blur-in 显影浮出配更慢缓动（L3 两者同为 glow/cover，不计入分化——拉开靠的是 L4/L5/L6）

**G1 color**

```css
--paper:#0f0f0f; --paper-tint:#1a1816;
--ink:#e8e4df;   --ink-tint:#2a2724;
--accent:#d4a574; --accent-on:#0f0f0f;
```

- **accent 预算**：内容页 accent 面积 ≤5%（暖金只做点睛：引线端点、编号签方块、关键数字）；满屏 accent 不适用——暗夜仪式感靠辉光不靠满色；首尾闭环：封面右上辉光开场 → 收束页同位辉光呼应（可略强）。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 500–600、正文 400——克制不张扬，图鉴的权威感来自排布而非字重
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：衬线恒重立场（不走倒挂）：≥77px→500–600；35–76px→500–600；正文 400；14–16px 小字 500
- **标题修饰**：无（斜体只属于拉丁学名标注 `.mt-bot-latin`，不进标题）

**G3 texture**

```css
--texture-type: glow;
--texture-layer: radial-gradient(90% 70% at 78% 8%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 60%);
--texture-scope: cover;
```

- **立场**：glow——仪式页右上角一团暖金辉光，如温室夜灯悬在图鉴上方；正文页纯暗夜纸面

**G4 shape**

- **圆角**：0（标本柜的秩序，图鉴卡一律直角）
- **hairline**：1px solid color-mix(in srgb, var(--ink) 30%, transparent)，承担图鉴卡描边与引线——线在这个主题里是标注工具，不是装饰
- **阴影**：无
- **容器造型**：图鉴卡——直角 1px 细描边 + 左上角钉编号签条（`.mt-bot-plate` + `.mt-bot-tag` 落码），卡内按图鉴版式排（图在上、拉丁名与引线注在下）；禁圆角、禁玻璃、禁弥散投影、禁满版色块
- **高密度容器边界**：图鉴卡描边成阵即边界——1px 细描边（hairline 口径 ink 30%）是标本柜抽屉的分格，暗底上描边自立边界无需面；同页卡阵同构，签条钉角位置恒定

**G5 motion**

- **气质**：calm
- **强度上限**：低
- **锚点偏好**：draw-line 为签名锚点——图鉴引线与叶脉描线的生长感，图注页/数据页优先；标题入场用默认阶梯或 rise-in，克制
- **节奏偏移**：时长档 +1（一切比默认慢，夜观的呼吸）；阶梯步长 ≥90ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：无（calm 气质本身排除弹跳与硬切）
- **fx 许可**：仅 particle-drift（夜尘/孢子浮动；starfield 太"天文"、constellation 连线太硬，均不属于植物园）

**G8 component**

- **亲和**：图文证据（标本图 + 引线图注，本主题的原生版式）、轴与节点（分类树/谱系——叶脉分叉与分类学同构）
- **禁忌**：禁裂屏对开大色块对撞（图鉴没有满版撞色）；网格矩阵仅用于标本陈列式多图页，连用不超过两页

**G9 motif**

- **词汇**：标本引线标注（`.mt-bot-lead`：accent 空心圆点 + 1px 渐隐细引线 + mono 小注，把图与图注缝在一起，每页 ≤2 条）/ 图鉴编号签（`.mt-bot-tag`：1px 描边 mono 小签条带 accent 方块点，"No.04 / Pl.XII"，钉在图鉴卡左上角或页面角）/ 拉丁学名斜体（`.mt-bot-latin`：衬线 italic 小注，图鉴的学术签名）/ 叶脉分叉细线（`.mt-bot-vein`：羽状分叉 hairline 条带，只许页面侧缘低透明装饰）

```css
/* C2 暗夜植物园 · 装饰母题 */
.mt-bot-tag{display:inline-flex;align-items:center;gap:.7em;padding:.3em .9em;border:1px solid color-mix(in srgb,var(--ink) 32%,transparent);font-family:var(--font-mono);font-size:12px;letter-spacing:.22em;color:color-mix(in srgb,var(--ink) 78%,transparent)}
.mt-bot-tag::before{content:"";width:4px;height:4px;background:var(--accent)}
.mt-bot-plate{position:relative;border:1px solid color-mix(in srgb,var(--ink) 28%,transparent)}
.mt-bot-plate>.mt-bot-tag{position:absolute;top:-1px;left:-1px;background:var(--paper)}
.mt-bot-lead{display:flex;align-items:center;gap:12px;font-family:var(--font-mono);font-size:12px;letter-spacing:.14em;color:color-mix(in srgb,var(--ink) 60%,transparent)}
.mt-bot-lead::before{content:"";flex:none;width:5px;height:5px;border:1px solid var(--accent);border-radius:50%}
.mt-bot-lead::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,color-mix(in srgb,var(--ink) 38%,transparent),transparent)}
.mt-bot-latin{font-family:var(--font-display);font-style:italic;letter-spacing:.04em;color:color-mix(in srgb,var(--ink) 68%,transparent)}
.mt-bot-vein{position:absolute;pointer-events:none;width:90px;height:100%;opacity:.5;background:repeating-linear-gradient(160deg,transparent 0 26px,color-mix(in srgb,var(--ink) 26%,transparent) 26px 27px),linear-gradient(90deg,transparent calc(50% - .5px),color-mix(in srgb,var(--ink) 26%,transparent) calc(50% - .5px) calc(50% + .5px),transparent calc(50% + .5px))}
```

- **禁忌**：引线与签条是标注工具不是装饰，禁无内容空挂；叶脉线禁横穿正文区、禁与引线同页抢焦；母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 月白

- **气质**：暖金灯熄灭后的银灰月色——更冷、更静，像午夜温室的玻璃顶

```css
--paper:#0f0f0f; --paper-tint:#1a1816;
--ink:#e8e4df;   --ink-tint:#2a2724;
--accent:#C9CDC4; --accent-on:#0f0f0f;
```

#### 苔绿

- **气质**：温室深处的苔痕绿——更潮湿、更幽闭的夜，适合蕨类/森林/生态叙事

```css
--paper:#0f0f0f; --paper-tint:#1a1816;
--ink:#e8e4df;   --ink-tint:#2a2724;
--accent:#8FA07A; --accent-on:#0f0f0f;
```

- **accent 预算**：苔绿明度低，暗底上只做线条与小签点，禁大色块；其余同基底口径
