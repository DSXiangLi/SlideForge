# G2 腮红荧光笔

- **id**：g2
- **气质**：腮红粉底 + 墨色手账字 + 四支荧光笔——划重点划出来的设计，亲切而有系统
- **适用**：教育与知识付费、读书笔记、活动回顾、年轻消费品牌、社群运营
- **focus**：G1 + G9
- **世界参考**：课堂笔记 × 音乐节手册——粉彩纸上，荧光笔标注系统是唯一的色彩语言
- **unforgettable**：荧光高亮带——关键词底部一条半透明荧光色带（半截渐变），四支笔分工明确
- **分化声明**：与 d1 分化于 L1/L4/L5/L6——d1 奶油底 + 焦糖 accent + 贴纸徽章/扇贝花边 + 大圆角弥散软影卡；g2 腮红粉底 + 四色荧光标注（只进标注层不进容器面）+ 手账纸胶带母题 + 微旋转便签卡

**本质规范**（从 unforgettable 推理出的骨架硬规则——所有 G1–G9 规范须服从）

| # | 维度 | 规范 | 推理路径 |
|---|---|---|---|
| 1 | 氛围 | 课堂笔记 × 音乐节手册——粉彩纸上，荧光笔标注系统是唯一的色彩语言 | 手账不是编辑部，是课桌上的笔记本 |
| 2 | 容器 | 便签卡——1px 描边 + 微旋转（±0.8°）贴上墙 | 手账的卡片是随手贴的便签，不是精密排版的色面 |
| 3 | 分隔 | 1px dashed 铅笔虚线——不是 solid hairline | 手账的线是铅笔画的虚线，不是印刷实线 |
| 4 | 层次 | 荧光带覆盖文字（z-index 层叠）——无弥散影 | 深度来自荧光笔的标注层叠，不来自投影 |
| 5 | 版式 | 手账散布贴卡——不是居中内容带 | 手账是贴出来的，不是排版排出来的 |
| 6 | 入场 | scale-pop 便签贴上墙——卡片的物理落位感 | 便签是"贴"上去的，不是"淡入"的 |
| 7 | 底色 | 腮红粉底——粉彩纸本身已是氛围 | 粉底是手账纸的本体，不需要额外纹理 |
| 8 | 字色 | 墨色手账字印粉底 + 荧光色只进标注层 | 荧光笔只标注不写字，文字永远是墨色 |

**骨架硬规则**（生成侧必须遵从）：
- **禁 masthead / mastfoot**——手账不需要编辑部刊头刊脚
- **禁 `.reveal` 通用入场**——用 `data-anim="scale-pop"` 替代（便签贴上墙）
- **禁居中内容带布局**（`display:flex;flex-direction:column;justify-content:center`）——用手账散布：内容分布在微旋转的便签卡上，卡片位置不对称
- **禁 solid hairline**——分隔用 1px dashed 铅笔虚线（`1px dashed color-mix(in srgb, var(--ink) 30%, transparent)`），实线只给图表轴
- **禁 box-shadow**——便签卡用 1px 细描边 + 微旋转贴上墙，深度靠层叠不靠投影

**G1 color**

```css
--paper:#F5E1E3; --paper-tint:#EFD3D8;
--ink:#1B1518;   --ink-tint:#3A2A30;
--accent:#C2447C; --accent-on:#FFF5F8;
--hl-1:#FBB24D; --hl-1-on:#3A2607;
--hl-2:#C44EE0; --hl-2-on:#FFFFFF;
--hl-3:#74D2F0; --hl-3-on:#0D2C44;
--hl-4:#BCEE54; --hl-4-on:#234D12;
```

- **accent 预算**：内容页 accent ≤8%（覆盆子红只给主标题关键词与唯一焦点卡）；荧光笔色不计入面积预算但计入**标注预算**（见多色立场）；满屏 accent 仅封面/收束；首尾闭环：封面粉底 + accent 巨标 + 四色高亮带开场 → 收束页同位高亮呼应。
- **多色立场**：四支荧光笔封闭制（hl-1 橙 / hl-2 紫 / hl-3 青 / hl-4 绿，禁第五支）；分配规则：**荧光色只以标注形态存在**（高亮带/圈注/胶带），禁做容器面、禁大面积填充、禁正文文字色；每支笔预配对 on-color（AA 纪律，配对即契约）；每页荧光标注 ≤4 处且同页 ≤2 色；容器与结构只用 paper/paper-tint/accent/ink。

**G2 typography**

```css
--font-display:"Yuanti SC","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 600–700（圆体的亲切恒重）、正文 400
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：圆体恒重立场：≥77px→600–700；35–76px→600；正文 400；14–16px 小字 500–600
- **标题修饰**：关键词垫荧光高亮带（G9 `.mt-hl-mark`），字体本身不加修饰
- **metric_fallback**：display→Yuanti SC/PingFang SC；body→PingFang SC/Noto Sans SC；mono→SF Mono/Menlo

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——手账纸是干净的，粉底本身已是氛围

**G4 shape**

- **圆角**：8–12px（便签的友好圆角，不到玻璃卡的连续曲面）
- **hairline**：1px dashed color-mix(in srgb, var(--ink) 30%, transparent)——铅笔虚线感
- **阴影**：无弥散影——便签卡用 1px color-mix(in srgb, var(--ink) 15%, transparent) 细描边 + 微旋转（±0.8°）贴上墙
- **容器造型**：便签卡（paper-tint 面 + 细描边 + 微旋转）；禁玻璃、禁硬偏移影（那是粗野系）
- **高密度容器边界**：便签卡成阵（旋转角全页统一方向，乱中有序）；分区用铅笔虚线

**G5 motion**

- **气质**：playful
- **强度上限**：默认
- **锚点偏好**：scale-pop 便签贴上墙；文字 rise-in；count-up 只给 KPI
- **节奏偏移**：不偏移
- **缓动签名**：默认三 token，不覆盖
- **禁用**：typewriter / scramble / flicker-in（通电词汇不属于手账）
- **fx 许可**：全禁

**G8 component**

- **亲和**：网格矩阵（便签墙）、图文证据（照片 + 胶带 + 手写注）、list 族徽章行
- **禁忌**：禁裂屏对撞（手账没有对峙）；禁暗底；图表收编进便签卡，系列色可用 hl 序列但须压回低饱和（color-mix 50% paper）

**G9 motif**

- **词汇**：荧光高亮带（`.mt-hl-mark`——半截渐变色带垫关键词，色随 `--hl-c`，四色各一档变体类）/ 荧光圈注（`.mt-hl-circle`——椭圆荧光描边圈住短语，像随手画的圈）/ 纸胶带（`.mt-hl-tape`——半透明胶带条贴便签顶角，固定感）

```css
/* G2 腮红荧光笔 · 装饰母题 */
.mt-hl-mark{background:linear-gradient(180deg,transparent 58%,color-mix(in srgb,var(--hl-c,var(--hl-1)) 60%,transparent) 58%,color-mix(in srgb,var(--hl-c,var(--hl-1)) 60%,transparent) 92%,transparent 92%);padding:0 .08em}
.mt-hl-mark--2{--hl-c:var(--hl-2)}
.mt-hl-mark--3{--hl-c:var(--hl-3)}
.mt-hl-mark--4{--hl-c:var(--hl-4)}
.mt-hl-circle{border:2.5px solid color-mix(in srgb,var(--hl-c,var(--hl-1)) 80%,transparent);border-radius:50%;padding:.1em .3em;transform:rotate(-1.5deg)}
.mt-hl-tape{position:absolute;width:88px;height:24px;background:color-mix(in srgb,var(--hl-c,var(--hl-1)) 45%,transparent);transform:rotate(-4deg);pointer-events:none}
```

- **禁忌**：高亮带每处只标 1–3 词（标整段等于没划）；圈注每页 ≤1 处；胶带只贴便签顶角；`.mt-hl-mark`/`.mt-hl-circle` 是文本载体类母题（加在真实文本上，文本保持可编辑），其余母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 薄荷笔记

- **气质**：薄荷纸底——更清爽的学习感，适合读书笔记、课程大纲、知识管理

```css
--paper:#E3F2EC; --paper-tint:#D2E8DE;
--ink:#15201B;   --ink-tint:#2C3A33;
--accent:#2E7D5B; --accent-on:#F0FAF5;
```

#### 海盐笔记

- **气质**：海盐蓝纸底——最安静的一档，适合技术笔记、文档团队、远程协作场景

```css
--paper:#E4EEF7; --paper-tint:#D4E2F0;
--ink:#14202E;   --ink-tint:#2A3848;
--accent:#3A6EA5; --accent-on:#F2F8FD;
```
