# E8 号外报纸

- **id**：e8
- **气质**：纸白 + 油墨黑 + 号外红，超粗黑标题压顶、通栏粗细双线、多栏小字的新闻冲击力
- **适用**：新闻/资讯/时事评论、数据简报与行业观察、战报式项目汇报、危机通报、复古 editorial 叙事
- **focus**：G2 + G9
- **世界参考**：黑白小报与"号外"传单——报头徽标、通栏粗细分栏线、三栏小字正文、满版超粗黑标题的新闻纸
- **unforgettable**：号外版式——满版超粗黑标题压顶 + 通栏粗细双线 + 多栏小字正文，一张纸撑起的街头新闻冲击
- **分化声明**：与 c4 分化于 L2/L4/L7——c4 是全衬线恒重的书籍排版（宋体标题 + 宋体正文）、母题是题花/首字下沉/引文拉页、禁忌网格矩阵（书页靠栏不靠格）；e8 是 display 极粗无衬线黑体（Arial Black 系）+ body 报宋衬线的报馆字排、母题是通栏粗细双线/报头条/三栏容器、网格矩阵（多栏即网格）是原生亲和

**G1 color**

```css
--paper:#f4f1ea; --paper-tint:#e8e4da;
--ink:#111111;   --ink-tint:#232323;
--accent:#C8102E; --accent-on:#fdf9f4;
```

- **accent 预算**：内容页 accent 面积 ≤5%（号外红只给：报头日期线、单条通栏规则、关键数据角标——报纸一天只有一个头条）；满屏 accent 仅封面"号外"页且宜半版（上半红底反白巨标 + 下半纸白多栏）；首尾闭环：号外红报头开场 → 收束页红色通栏粗细线呼应。

**G2 typography**

```css
--font-display:"Arial Black","Impact","SimHei","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"Georgia","Times New Roman","Songti SC","SimSun",serif;
--font-mono:"Consolas","Courier New","SF Mono",monospace;
```

- **字重倾向**：display 极粗恒重（800–900 黑到底），body 400 衬线小字——冲击力来自字重两极与栏密度，不是中间档
- **字号对比**：主标题:正文 ≥8:1（低密度；号外头条 ≥10:1，封面可冲 12:1）；高密度 ≥5:1
- **字重映射**：极粗黑体立场（不走倒挂——报头越黑越有冲击）：≥77px→800–900；35–76px→800；正文 400；14–16px 栏内小字 400–500；图注/署名 mono 400
- **标题修饰**：拉丁头条全大写；标题下通栏粗细双线（G9 `.mt-news-rule`）

**G3 texture**

```css
--texture-type: paper;
--texture-layer: radial-gradient(85% 60% at 15% 8%, color-mix(in srgb, var(--ink) 4%, transparent), transparent 60%);
--texture-scope: cover;
```

- **立场**：轻新闻纸纹——仪式页纸色微沉一角，阅读页保持干净（报纸的质感在纸色本身与栏密度，不靠叠加层）

**G4 shape**

- **圆角**：0
- **hairline**：通栏粗细双线（3px 粗 + 1px 细）做报头下与栏间分隔，是版面骨架；栏内次级分隔用 1px solid color-mix(in srgb, var(--ink) 25%, transparent)
- **阴影**：无
- **容器造型**：多栏即容器——CSS columns 分栏文本 + column-rule 细栏线分区；图证用 1px 黑框 + 图注栏线；禁圆角卡、禁阴影、禁弥散渐变
- **高密度容器边界**：栏框——1px 墨线框的 boxed sidebar（报纸边栏/资料框是真实存在的版式件），框顶可压通栏粗细双线作栏题；框内小字栏排，框是新闻纸的版式工具不是装饰

**G5 motion**

- **气质**：professional
- **强度上限**：默认
- **锚点偏好**：wipe-clip 硬切揭示为签名锚点（标题/通栏线——报纸的动效是"付印"般的利落）；章节页 mask-lines 头条逐行显影；数字以超大字重直排为主，count-up 只给数据简报英雄页
- **节奏偏移**：时长档 −1（快，付印节奏）；阶梯步长 ≤60ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / blur-in / typewriter / scramble（弹跳、柔焦、打字机都不属于报纸）
- **fx 许可**：全禁（新闻纸无像素仪式）

**G8 component**

- **亲和**：网格矩阵（多栏即网格——栏是它的原生单位，与 c4 的书页立场正好对立）、巨字宣言（号外头条）、数据英雄（头版大数字 + 栏线收编）
- **禁忌**：禁圆角柔和组件与渐变卡片；裂屏对开仅限"号外"封面（上红下纸半版对开）；图表收编为"新闻图表"——1px 黑框 + mono 图注，禁彩色圆角图表卡；不用题花/首字下沉（那是书籍词汇，c4 专属）

**G9 motif**

- **词汇**：通栏粗细双线（`.mt-news-rule`：3px 粗 + 1px 细的 thick-thin rule，报头下与栏间的"印刷规则"，每页 ≤2 条）/ 报头徽标条（`.mt-news-mast`：mono 大写报名 + 日期/期号分列左右，上下细线夹住，只许封面/收束）/ 三栏文本容器（`.mt-news-cols`：CSS columns + column-rule 细栏线，栏数 2–4 烧死）/ 斜切引文块（`.mt-news-pull`：衬线斜体通栏大引文，上粗线 + 下细线夹住）

```css
/* E8 号外报纸 · 装饰母题 */
.mt-news-rule{height:5px;border:none;border-top:3px solid var(--ink);border-bottom:1px solid var(--ink)}
.mt-news-mast{display:flex;align-items:baseline;justify-content:space-between;gap:1.2em;padding:.55em 0;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);font-family:var(--font-mono);font-size:12px;letter-spacing:.26em;text-transform:uppercase}
.mt-news-cols{columns:3;column-gap:2.2em;column-rule:1px solid color-mix(in srgb,var(--ink) 22%,transparent);text-align:justify}
.mt-news-pull{border-top:3px solid var(--ink);border-bottom:1px solid var(--ink);padding:.7em 0;font-family:var(--font-body);font-style:italic;font-size:1.45em;line-height:1.6}
```

- **禁忌**：粗细双线每页 ≤2 条（通栏规则是版面骨架不是撒布）；三栏容器只装真实正文，禁栏内塞卡片；`.mt-news-cols`/`.mt-news-pull` 为文本载体类母题（样式由类承担，文本保持可编辑），其余母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 财经蓝

- **气质**：号外红换藏蓝——从街头号外走进金融版，权威、克制、数据感——财报、行业研报、机构简报

```css
--paper:#f4f1ea; --paper-tint:#e8e4da;
--ink:#111111;   --ink-tint:#232323;
--accent:#1E3A6E; --accent-on:#f4f1ea;
```

#### 泛黄旧报

- **气质**：旧报纸泛黄 + 墨褐标题——档案馆里的合订本，年代感与史料感——历史回顾、编年叙事、纪念专题

```css
--paper:#ece2c6; --paper-tint:#ded2b2;
--ink:#241d14;   --ink-tint:#352a1c;
--accent:#6B4A2F; --accent-on:#f0e8d2;
--texture-layer: radial-gradient(60% 50% at 20% 15%, color-mix(in srgb, var(--accent) 8%, transparent), transparent 60%), radial-gradient(70% 60% at 80% 90%, color-mix(in srgb, var(--ink) 6%, transparent), transparent 65%);
```

- **accent 预算**：墨褐饱和度低，礼仪性使用口径不变（≤5%）；"号外"封面的满版特权改为半版旧化晕染；其余同基底口径
