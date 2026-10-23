# E12 商务粗野（Business Neo-Brutalism）

- **id**：e12
- **气质**：奶油纸 + 墨黑粗描边 + 策展五色平涂，每个色块拖着一块没对准的纯墨硬影——完整粗野的商务驯化版，有棱角的商务
- **适用**：金融科技、高密度数据汇报、消费/零售、产品与增长叙事、需要"多彩但不戏谑"的商务场合
- **focus**：G1 + G4
- **世界参考**：Neo-Brutalism 网页运动 × 丝网印刷海报传统的**商务驯化演绎**——保留粗墨框、平涂色块、套色错位硬影与贴纸标签，去掉街头/反体制的戏谑，色板策展化、动效去弹跳
- **unforgettable**：纯墨硬偏移投影——每个描边色块/照片卡都拖着一块 `8px 8px 0` 的墨影，像丝网套色没对准，一眼新粗野
- **分化声明**：与 e6 分化于 L1/L4/L5/L6——e12 是奶油纸 + 策展五色板（变体即五色：朱红/钴蓝/松绿/明黄/青碧），e6 是米白纸 + 糖果粉单罐明度阶梯（L1）；e12 母题是描边圆环/实心圆盘/直角色块/爆炸星/贴纸 chip/3px 结构线，e6 是彩纸屑碎形/之字波浪线/圆角粗描边卡（L4）；e12 容器是直角 0 圆角 + 墨色硬投影 + 2.5px 描边平面卡，e6 是 8–16px 圆角 + accent 色硬投影（L5）；e12 动效 professional 短促（wipe-clip/rise-in，禁弹跳回弹），e6 是 playful（scale-pop + magnetic + 回弹缓动）（L6）

**G1 color**

```css
--paper:#FFF6E3; --paper-tint:#F8EAC6;
--ink:#17140E;   --ink-tint:#2C2517;
--accent:#E43D25; --accent-on:#FFF6E3;
```

- **accent 预算**：内容页 accent 面积 ≤10%——accent 给：标题荧光（`.tt-mark`）、焦点色块（带硬投影，单页至多一个）、列表方块引子、图表主系列；满屏 accent 是封面/章节/封底特权（满版色相页 + 墨描边反白字，明黄变体反墨字）；首尾闭环：封面五色方块列 + 爆炸星开场 → 收束页同构五色方块列呼应。
- **多彩纪律**：单页单 accent 纪律不破。本主题的多彩感由**变体即五色**承载（基底朱红 + 钴蓝/松绿/明黄/青碧四变体），deck 级玩法 = 章节级色相轮转（逐章把 `--accent` 换成变体色，`docs/design/theme-e12-neobrutalism.md` §4；该玩法的 `data-hue` 覆盖规则不进 G9 CSS 块，属 deck 级扩展）——禁在单页内混用多个高饱和色。

**G2 typography**

```css
--font-display:"Helvetica Neue","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：极粗标题立场——大字 800 极粗（字重差本身即装饰），正文 400，字重倒挂（细大粗小）在本世界不成立
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：极粗标题立场：≥77px→800；35–76px→700；正文 400；14–16px 小字 500–600
- **标题修饰**：`.tt-mark` accent 荧光标记压题（typography.md §7）+ 标题前 24px accent 描边色块引子（G9 `.mt-nb-block` 的静态档位用法）

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——新粗野是丝网平涂世界，纸纹、颗粒、渐变都是背叛

**G4 shape**

- **圆角**：0——直角是本世界的立场，圆角属于孟菲斯/奶油
- **hairline**：无细线——分隔用 2px 实墨结构线，母题级用 3px（G9 `.mt-nb-line`）
- **阴影**：唯一形态 = 纯墨硬偏移投影 `box-shadow: Npx Npx 0 var(--ink)`（4/5/8/12px 档：小引子 4、贴纸 5、色块圆盘 8、照片卡 12）；墨填色件投影换 `var(--accent)` 防糊；**禁弥散阴影**
- **容器造型**：两档制——**描边平面卡**（2.5px ink 描边 + paper-tint/paper 底，无投影，内容容器默认档）与**焦点卡**（+8px 硬投影，单页至多一个，照片卡/关键数据卡用）；禁圆角、禁渐变、禁玻璃拟态
- **高密度容器边界**：描边平面卡成阵 + 2px 实墨行线即边界——边界义务由描边与结构线承担，cmb-retail-v3 实证（54 页高密度零容量违规）

**G5 motion**

- **气质**：professional
- **强度上限**：默认；节奏偏移：时长档 −1（短促，印章落定感）；阶梯步长 ≤60ms
- **锚点偏好**：wipe-clip（色块与标题的精确揭示）+ rise-in（卡阵逐格落定）+ count-up 给数据英雄页
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / persp-in / blur-in / magnetic（弹跳回弹与柔焦不属于直角平涂世界）
- **fx 许可**：全禁

**G8 component**

- **亲和**：图文证据（描边照片卡，旋转 ≤2°）、数据英雄（巨数 800 + accent 色块引子）、网格矩阵（描边平面卡阵是它的货架）、裂屏对开（墨框分区）
- **禁忌**：禁圆角容器/弥散阴影/玻璃拟态/渐变；不用彩纸屑/之字线（孟菲斯词汇）、不用 Ghost 残影/竖排题字条（杂志系）、不用加号角标/网格点阵（瑞士系）；图表页保持直角 + 3px 折线宽（`--chart-stroke:3px`）

**G9 motif**

- **词汇**：描边圆环（`.mt-nb-ring` 3px 墨描边空心圆，背景构成件）/ 实心圆盘（`.mt-nb-disc` + 8px 硬投影）/ 直角色块（`.mt-nb-block` + 8px 硬投影；墨填色变体 `.mt-nb-block-ink` 投影换 accent）/ 爆炸星（`.mt-nb-star` 十二角 clip-path，**只许仪式页焦点位**，正文页禁用）/ 3px 墨结构线（`.mt-nb-line`）/ 贴纸 chip（`.mt-nb-chip` 2.5px 描边 + accent 底 + 5px 硬投影，文本载体类——文字保持 `data-editable`）

```css
/* E12 商务粗野 · 装饰母题 */
.mt-nb-ring,.mt-nb-disc,.mt-nb-block,.mt-nb-star{position:absolute;pointer-events:none;user-select:none}
.mt-nb-ring{border:3px solid var(--ink);border-radius:50%}
.mt-nb-disc{border:3px solid var(--ink);border-radius:50%;box-shadow:8px 8px 0 var(--ink)}
.mt-nb-block{border:3px solid var(--ink);box-shadow:8px 8px 0 var(--ink)}
.mt-nb-block-ink{position:absolute;pointer-events:none;user-select:none;border:3px solid var(--ink);background:var(--ink);box-shadow:8px 8px 0 var(--accent)}
.mt-nb-star{clip-path:polygon(50% 0,61% 12%,75% 4%,79% 19%,95% 15%,91% 31%,100% 38%,90% 50%,100% 62%,91% 69%,95% 85%,79% 81%,75% 96%,61% 88%,50% 100%,39% 88%,25% 96%,21% 81%,5% 85%,9% 69%,0 62%,10% 50%,0 38%,9% 31%,5% 15%,21% 19%,25% 4%,39% 12%);background:var(--accent)}
.mt-nb-line{display:block;height:3px;background:var(--ink)}
.mt-nb-chip{display:inline-block;border:2.5px solid var(--ink);background:var(--accent);color:var(--accent-on);box-shadow:5px 5px 0 var(--ink);padding:.25em .7em}
```

- **禁忌**：硬投影一律 `var(--ink)`（墨填色件除外，换 accent）；每页母题件 1–3 件；爆炸星只许仪式页；正圆环/圆盘以外禁任何曲线形（波浪/有机形属奶油与孟菲斯）；母题件一律 `data-editable-skip`（`.mt-nb-chip` 文本除外）

**bake_brief**

```json
{
  "visual_direction": "business neo-brutalist poster, screen-print tradition tamed for the boardroom, cream paper, thick black outlines, flat curated color blocks each dragging a hard offset pure-ink shadow like a misregistered second pass, sticker chips, one explosive star on ritual pages, print-shop confidence",
  "palette_rule": "cream paper and near-black ink carry the page; the single curated accent hue appears as title marker highlights, one focal color block with hard ink shadow, list square markers and one chart series; full-bleed accent is cover/divider/closing privilege; never mix a second saturated hue on one page; shadows are always pure ink — accent only when the casting piece itself is ink-filled",
  "typography_bake": "主标题重构词汇：极粗 800 立场（字重差即装饰，不走倒挂）；标题关键词压 accent 荧光标记（marker 笔法——荧光带垫在字下半、纸纹之上）；标题前 24px accent 描边色块引子；断行成直角块；隐喻融字只允许贴纸化——关键词装进描边 chip 徽章（墨框 + accent 底 + 硬影），禁笔画变形",
  "uplift": "升维路径（HTML 做不到的物理维度）：粗墨描边的印刷机压力感——线宽有微妙压力变化与偶发飞白（刻板/丝网的手工证据）；硬偏移投影获得真实光投落感——墨影有物理厚度与一致的投射方向，而非像素复制；纸卡的真实厚度与裁切边缘——卡片像从厚卡纸裁下、切口微毛；丝网色块的微妙不匀——大面积平涂有滚筒上墨的轻微深浅呼吸——HTML 的平面色块在此获得丝网印刷的工艺性，直角立场不变",
  "allowed": "thick black outlines, flat curated color blocks, hard offset pure-ink shadows, sticker chips with accent fill, outlined rings and solid discs, one twelve-point explosive star on ritual pages, 3px ink structural rules, marker-style title highlights, square corners everywhere, mono field labels",
  "avoid": "rounded corners, soft diffuse shadows, gradients, glass morphism, mesh gradients, aurora blobs, photorealism, thin hairline dividers, ghost outline characters, confetti scatter, zigzag lines, serif elegance, centered symmetric template layout, multiple saturated hues on one page, gray drop shadows, 3D bevels",
  "layout_blueprints": {
    "cover": [
      {"position": "top", "count": 1, "labels": ["mono 字段行（deck 名/日期）"]},
      {"position": "center-left", "count": 1, "labels": ["极粗巨字标题（关键词压荧光标记）"]},
      {"position": "single focal point", "count": 1, "labels": ["accent 焦点色块或爆炸星（实色 + 墨硬影）"]},
      {"position": "background edge", "count": 2, "labels": ["描边圆环构成件", "3px 墨结构线"]}
    ],
    "divider": [
      {"position": "left", "count": 1, "labels": ["巨大章节数字（800）+ accent 色块引子"]},
      {"position": "middle", "count": 1, "labels": ["3px 墨结构线横贯"]},
      {"position": "below line", "count": 1, "labels": ["一行章节题"]}
    ],
    "key-message": [
      {"position": "center-left 70%", "count": 1, "labels": ["宣言巨字 + 荧光标记关键词"]},
      {"position": "single focal point", "count": 1, "labels": ["贴纸 chip 焦点（描边 + accent 底 + 硬影）"]},
      {"position": "background", "count": 2, "labels": ["描边圆环/圆盘构成件 ≤2"]}
    ],
    "analysis": [
      {"position": "top", "count": 1, "labels": ["标题 + 3px 墨结构线"]},
      {"position": "main", "count": 1, "labels": ["描边平面卡阵（2.5px 墨框、直角，3–6 格）"]},
      {"position": "inside grid", "count": 1, "labels": ["至多一个焦点卡（8px 墨硬影）"]},
      {"position": "bottom", "count": 1, "labels": ["mono 字段注记/图例"]}
    ]
  },
  "rendering_constraints": [
    "The page must read as a screen-printed business neo-brutalist poster — not a Memphis party flyer, not a generic card template.",
    "Square corners everywhere — rounded corners belong to other worlds.",
    "Exactly one shadow form: hard offset pure ink (accent only under ink-filled pieces); soft or gray shadows are failure.",
    "One accent hue per page; multi-color feeling lives in palette variants, never mixed on one page.",
    "Titles at weight 800; the inverted thin-giant ladder does not exist in this world.",
    "Flat silkscreen ink only: no gradients, no glass, no photorealism.",
    "Explosive star on ritual pages only; motif pieces 1-3 per page.",
    "Cover/divider/key-message pages: at most 5 text elements; analysis pages: 3-6 outlined flat cards with at most one hard-shadow focal card.",
    "Hard shadows may gain physical light-cast thickness, but the offset direction stays constant across the page.",
    "Do not invent logos, watermarks, or brand marks."
  ]
}
```

**Variants 配色变体**

#### 钴蓝

- **气质**：墨框里的钴蓝——冷静理性的机构感，五色板里最商务的一格——金融机构、企业服务、研究发布

```css
--paper:#FFF6E3; --paper-tint:#F8EAC6;
--ink:#17140E;   --ink-tint:#2C2517;
--accent:#2456D6; --accent-on:#FFF6E3;
```

#### 松绿

- **气质**：墨框里的松绿——稳健增长与可持续的联想——ESG、农业食品、健康、长期主义叙事

```css
--paper:#FFF6E3; --paper-tint:#F8EAC6;
--ink:#17140E;   --ink-tint:#2C2517;
--accent:#1F9D64; --accent-on:#FFF6E3;
```

#### 明黄

- **气质**：墨框里的明黄——海报压强最高的一格，街头海报与促销的直给——零售、活动、消费品牌；**accent-on 反墨字**（黄底深字才读得清）

```css
--paper:#FFF6E3; --paper-tint:#F8EAC6;
--ink:#17140E;   --ink-tint:#2C2517;
--accent:#F2B100; --accent-on:#17140E;
```

#### 青碧

- **气质**：墨框里的青碧——清爽现代的科技消费感——互联网产品、出海品牌、生活方式

```css
--paper:#FFF6E3; --paper-tint:#F8EAC6;
--ink:#17140E;   --ink-tint:#2C2517;
--accent:#0E8F8A; --accent-on:#FFF6E3;
```

---

## F 系 · 光与纵深（J 期新增）

F 系是光学轴补完：前 21 个主题全部建立在"线 + 平涂色块"的扁平范式上，F 系把纵深（柔和多层投影）、透明（毛玻璃叠层）、光线（发光体系）、氛围（渐变与暗角）四根新手法轴各自立为主题。A–E 系的"薄"是立场，F 系的"厚"也是立场——两者互不正交借用。设计依据 `docs/design/theme-optical-axes.md`。
