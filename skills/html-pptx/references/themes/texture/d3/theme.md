# D3 手绘油彩

- **id**：d3
- **气质**：画纸暖灰 + 赭石一笔，手绘油彩的呼吸感与留白
- **适用**：艺术、文化、展览、人文叙事、创作者作品集、慢内容分享
- **focus**：G2 + G9
- **世界参考**：画室速写本与手工画册——可见笔触的油画小品、铅笔虚线圈注、细双描边的画框装裱
- **unforgettable**：笔触块——不规则有机边缘的色块像一笔抹上去的油彩，垫在标题后面，每页都有"被画出来"的痕迹
- **分化声明**：与 a1 分化于 L2/L3/L4/L5/L6——a1 是编辑部衬线、墨韵 glow、Ghost 残影字、无卡片立场、mask-lines 显影；d3 是楷体手绘字排、纸面晕染全页许可、笔触块与虚线圈注、不规则有机圆角容器、draw-line 慢描绘

**G1 color**

```css
--paper:#e9e5da; --paper-tint:#dcd6c6;
--ink:#33413a;   --ink-tint:#46564d;
--accent:#a05f3c; --accent-on:#f5f1e6;
```

- **accent 预算**：内容页 ≤10%（赭石点缀：笔触块/单强调字）；满屏 accent 仅封面/收束；首尾闭环：封面赭石墨色块→收束页赭石一笔

**G2 typography**

```css
--font-display:"Kaiti SC","STKaiti","Songti SC","Noto Serif SC",serif;
--font-body:"Kaiti SC","STKaiti","Songti SC","Noto Serif SC",serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：400–600，靠字体手绘感不靠字重对比
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：手绘立场——楷体无多档字重，层级靠字号差：标题 400–600；正文 400；14–16px 小字 500–600
- **标题修饰**：手绘衬线字体本身即修饰，不另加

**G3 texture**

```css
--texture-type: paper;
--texture-layer: radial-gradient(80% 60% at 30% 20%, color-mix(in srgb, var(--accent) 5%, transparent), transparent 70%), radial-gradient(70% 80% at 75% 85%, color-mix(in srgb, var(--ink) 4%, transparent), transparent 70%);
--texture-scope: all;
```

- **立场**：画纸晕染 = 材质本体——纸与颜料晕染是这个世界的一部分，正文页也允许铺（scope all），但仍需生成侧逐页 `texture-on` 落码

**G4 shape**

- **圆角**：不规则圆角——微妙非对称 radius（如 `14px 18px 12px 20px`），禁全等圆角的工业感
- **hairline**：不用直线分割，用留白分区；标注职能交给虚线圈注（G9）
- **阴影**：无——纸面世界不吃投影，层次靠色块叠压与晕染
- **容器造型**：不规则圆角 + 极淡纸色底（paper-tint）；禁直角硬卡、禁玻璃拟态、禁描边窗口
- **高密度容器边界**：不规则圆角 paper-tint 淡色面——手绘纸片即边界（面即立场）；装裱语义处可用画框双描边（`.mt-art-frame`）收编图版，但容器默认走面不走框

**G5 motion**

- **气质**：calm
- **强度上限**：低
- **锚点偏好**：draw-line（笔触描绘感——线条像被画出来，是它的签名）；文字入场 rise-in 轻上浮
- **节奏偏移**：时长档 +1（慢半拍，描绘需要的时间）
- **缓动签名**：默认三 token，不覆盖
- **禁用**：无禁用
- **fx 许可**：全禁（手绘材质与数字粒子/字符场冲突）

**G7 illustration**

- **风格**：手绘油画质感插画——可见笔触、低饱和、灰绿/赭石/雾蓝三色体系、大量留白
- **提示词种子**：hand-painted oil illustration, muted sage green / ochre / misty blue palette, visible brushstrokes, generous negative space
- **禁忌**：不用照片级写实、不用高饱和霓虹色、不用矢量扁平风

**G8 component**

- **亲和**：图文证据（画作 + 图注是它的原生形态）、巨字宣言（手绘巨字有画册封面感）
- **禁忌**：禁网格矩阵密集排布（画室的墙不是货架）；数据英雄页慎用，图表须以笔触块或画框装裱收编

**G9 motif**

- **词汇**：笔触块（不规则有机边缘的 accent 淡色块，垫在标题或关键词后，像一笔抹上去的油彩）/ 手绘虚线圈注（dashed 不规则圆角框，像铅笔随手圈出的批注）/ 画框双描边（细双线装裱图片与画作，纸色勾边隔开两道墨线）

```css
/* D3 手绘油彩 · 装饰母题 */
.mt-art-brush{position:relative;isolation:isolate}
.mt-art-brush::before{content:"";position:absolute;inset:-.15em -.35em;z-index:-1;background:color-mix(in srgb,var(--accent) 22%,transparent);border-radius:62% 38% 55% 45%/48% 55% 42% 52%}
.mt-art-circle{border:2px dashed color-mix(in srgb,var(--accent) 65%,transparent);border-radius:58% 42% 50% 50%/52% 48% 55% 45%;padding:.4em .9em}
.mt-art-frame{border:1px solid color-mix(in srgb,var(--ink) 55%,transparent);box-shadow:inset 0 0 0 5px var(--paper),inset 0 0 0 6px color-mix(in srgb,var(--ink) 35%,transparent)}
```

- **禁忌**：笔触块每页 ≤2 处且只垫重点（处处笔触即脏）；虚线圈注禁圈长段落（只圈词/短语）；母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 雾蓝

- **气质**：油画三色体系的重心移向雾蓝——烟雨山水感，冷静诗意，适合东方美学、节气、慢旅行

```css
--paper:#e9e5da; --paper-tint:#dcd6c6;
--ink:#33413a;   --ink-tint:#46564d;
--accent:#5B7A8C; --accent-on:#f5f1e6;
```

#### 灰绿

- **气质**：油画三色体系的重心移向灰绿——苔色入画，植物标本册感，适合自然、植物、生态、茶文化

```css
--paper:#e9e5da; --paper-tint:#dcd6c6;
--ink:#33413a;   --ink-tint:#46564d;
--accent:#6B7F5E; --accent-on:#f5f1e6;
```

---

## E 系 · 世界采样（I 期新增）

E 系是"世界采样法"的第一批成果（构思流程见 handover §5.3）：每个主题从一个真实世界翻译而来——印刷工艺、设计史、东方版画、行业票据、自然系统。
