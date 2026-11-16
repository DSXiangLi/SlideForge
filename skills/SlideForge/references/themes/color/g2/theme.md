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
| 5 | 版式 | 左正文行栏 + 右标注索引脊的双坐标——不是居中内容带，也不是便签散布 | 重点是被划出来的，划痕连回原行才成结构 |
| 6 | 入场 | scale-pop 便签贴上墙——卡片的物理落位感 | 便签是"贴"上去的，不是"淡入"的 |
| 7 | 底色 | 腮红粉底——粉彩纸本身已是氛围 | 粉底是手账纸的本体，不需要额外纹理 |
| 8 | 字色 | 墨色手账字印粉底 + 荧光色只进标注层 | 荧光笔只标注不写字，文字永远是墨色 |

**骨架硬规则**（生成侧必须遵从）：
- **禁 masthead / mastfoot**——手账不需要编辑部刊头刊脚
- **禁 `.reveal` 通用入场**——用 `data-anim="scale-pop"` 替代（便签贴上墙）
- **禁居中内容带布局**（display:flex;flex-direction:column;justify-content:center）——用正文层/批注层双坐标：左侧带行号等距正文行，右侧标注索引脊，水平荧光引线连回原行
- **禁 solid hairline**——分隔用 1px dashed 铅笔虚线（`1px dashed color-mix(in srgb, var(--ink) 30%, transparent)`），实线只给图表轴
- **禁 box-shadow**——便签卡用 1px 细描边 + 微旋转贴上墙，深度靠层叠不靠投影；**禁便签卡成阵**，KPI 作为页边批注贴在对应笔记行外侧（G10 优先）

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
- **高密度容器边界**：正文行栏（左 2/3，行号 + 铅笔虚线等距行）＋ 标注索引脊（右 1/3）；两栏由荧光引线一一连接，禁便签卡成阵

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
:root{--t-display:128px}
/* G2 腮红荧光笔 · 装饰母题 */
.mt-hl-mark{background:linear-gradient(180deg,transparent 58%,color-mix(in srgb,var(--hl-c,var(--hl-1)) 60%,transparent) 58%,color-mix(in srgb,var(--hl-c,var(--hl-1)) 60%,transparent) 92%,transparent 92%);padding:0 .08em}
.mt-hl-mark--2{--hl-c:var(--hl-2)}
.mt-hl-mark--3{--hl-c:var(--hl-3)}
.mt-hl-mark--4{--hl-c:var(--hl-4)}
.mt-hl-circle{border:2.5px solid color-mix(in srgb,var(--hl-c,var(--hl-1)) 80%,transparent);border-radius:50%;padding:.1em .3em;transform:rotate(-1.5deg)}
.mt-hl-tape{position:absolute;width:88px;height:24px;background:color-mix(in srgb,var(--hl-c,var(--hl-1)) 45%,transparent);transform:rotate(-4deg);pointer-events:none}
.mt-hl-lineno{position:absolute;width:56px;text-align:right;color:color-mix(in srgb,var(--ink) 45%,transparent);font-family:var(--font-mono)}
.mt-hl-note{position:absolute;border:1px solid color-mix(in srgb,var(--ink) 15%,transparent);border-radius:10px;background:var(--paper-tint);padding:14px 20px;transform:rotate(.6deg)}
.mt-hl-note--alt{transform:rotate(-.8deg)}
.mt-hl-note--hl2{border-left:3px solid var(--hl-2)}
.mt-hl-note--hl3{border-left:3px solid var(--hl-3)}
.mt-hl-note--hl4{border-left:3px solid var(--hl-4)}
```

- **禁忌**：高亮带每处只标 1–3 词（标整段等于没划）；圈注每页 ≤1 处；胶带只贴便签顶角；`.mt-hl-mark`/`.mt-hl-circle` 是文本载体类母题（加在真实文本上，文本保持可编辑），其余母题件一律 `data-editable-skip`

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：高亮带和便签是签名结构件——高亮带垫在关键词下（文本载体类，文本保持可编辑），便签由 CSS 承担（data-editable-skip），内部文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，便签浮层、高亮标注、行号列全部消失，正文退回通栏两段；元素数量/分组/位置**都变** → **PASS**。

```yaml
doctrine: 重点不是写出来的，是被划出来的；阅读的痕迹本身就是信息结构。

page_composition:
  skeleton: 单栏流式正文 + 嵌入式便签标注
  grid: {margin: 120, gutter: 40, text_width: 1280, note_width: 420}
  balance: {anchor: 正文流(主宽), counterweight: 便签标注(右侧浮动)}
  whitespace_ratio: "≥45%"
  flow: "上 → 下：正文自然流动 → 关键词高亮 → 便签标注浮在对应位置右侧"
signature_operator: 把页面组织成单栏流式正文（占主宽 ~75%）+ 嵌入式便签标注浮层——
  正文自然流动不拆行号，关键词底部垫荧光高亮带（四色封闭制，每页 ≤2 色）；
  标注（关键词解释/数字/补充说明）以微旋转便签（±0.8°）形式浮在正文右侧对应位置，
  便签用 paper-tint 面 + 细描边 + 荧光色左边线；
  三项数字作为便签贴在各自对应正文段右侧，不独立成格。
silhouette: 单栏主宽正文 + 右侧便签浮层；高亮带在词下；重心左；便签微旋转。
info_grammar:
  cover:    一行圆体巨标 + 关键词荧光带；右下角一枚便签写副标题
  toc:      3–6 项目录自然排列，关键词高亮，便签贴在右侧标注章节类型
  claim:    主张句独占正文首段（关键词高亮）；说明便签浮在右侧
  analysis: 3–6 段正文自然流动，关键词高亮 + 便签标注浮在对应段右侧
  data:     三项数字 → 三枚便签贴在对应正文段右侧，微旋转
  closing:  正文收束，高亮带回押，便签收为一条荧光带
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 128px  # 圆体亲切但有气势；与正文 4.6:1
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读；荧光色只进标注层，禁做容器面与正文文字色
  floor_note: body/heading/subhead/caption/meta 不覆盖，继承骨架 28/64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 正文占主宽（≥70%），便签浮在右侧不遮挡正文阅读区
  - 荧光标注 ≤4 处且同页 ≤2 色（G1 多色立场）
  - 便签微旋转 ±0.8°，paper-tint 面 + 细描边 + 荧光左边线
  - 同组便签同宽，KPI 便签内字号一致（heading 64px）
  - 便签 y 位置与对应正文段 y 偏差 ≤30px
  - 横排等权三格容器数 = 0
forbidden_defaults: [横向等权三格 KPI, 便签卡成阵, 居中内容带, solid hairline, 整段高亮, 荧光色做容器面, 投影, 机械双栏坐标]
dna_events: {cover: 中, claim: 强, analysis: 强, data: 中, toc: 弱, closing: 中}
```

---

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
