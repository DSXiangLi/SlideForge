# 高密度表达：文本容器层 + 章节跳转 + 动效编排纪律（K 期设计）

> 状态：已审核修订（自审修复 5 项：锚点 id 规格/编辑态 nav-link 拦截/rotate 默认样式/mend-bar 语义/层次纪律硬规则表述） · 日期：2026-09-20
> 触发：用户验收意见——① 低密度测试充分、高密度缺乏测试（基准内容包 `tests/decks/smartforge-content.md`，抽象自 `source/demo1/`）；② 产物不支持章节跳转（demo 的 topnav 章节锚点是证据）；③ 没有鲜明的文本容器层，高密度页面层次感弱；④ 外部顶尖动效实践（demo1 Motion Layer 13 组）的可吸收点。

## 一、文本容器层（components.md 新增 §13）

### 问题

现有组件体系是"结构族 × Item 皮肤"——族描述**内容关系**，皮肤描述**单元样式**，但中间缺一层：**文本容器的结构分型**。demo1 的高密度屏证明真实内容大量落在"容器"而非"信息图"上：key/value 字段行（hero-meta、demo-status）、三格数据带（ticker）、痛点清单卡（pain-card）、对照列（mtx-col）、架构层行（arch-layer）。这些在 demo 里层次井然（tag/编号 → 大数字/标题 → 描述 → 清单/字段行，四层字阶清晰），而我们的 deck 里同类内容退化为"带边框文本块"——这就是用户说的"层次感弱"。

### 设计：六型文本容器（与结构族正交——族管关系，容器管包装）

| 型 | 结构 | 适用 | 密度容量 |
|---|---|---|---|
| **字段行 kv-rows** | label/value 两端对齐行 + hairline 行间分隔（demo 的 hero-meta/demo-status） | 元信息、规格、状态 | 每容器 4–8 行 |
| **数据带 ticker** | 等宽多格，格内 序号+变化标签 → 大数字 flow（from→to）→ 描述（demo 的三格带） | 反差数据、KPI 对比 | 2–4 格 |
| **指标卡 metric-card** | 编号/图标 + 标题 + 描述 + 可选指标条（demo 的 pain-card + leak-bar） | 问题/特性枚举 | 3–5 卡一排 |
| **对照列 versus-cols** | 两列头（可异色）+ 逐行对照项 | 二元对比（与裂屏对开互补：裂屏是叙事级，对照列是数据级） | 每列 3–6 项 |
| **堆栈层 stack-rows** | 全宽横层，层内 层号/名称 → 内容清单 → 右侧注记（demo 的 arch-layer） | 架构分层、流程分带 | 3–5 层 |
| **注记块 note-block** | 小字注 + 引线/左边线（与图表标注层同源） | 脚注、来源、例外说明 | 1–3 行 |

**容器内层次纪律（四层字阶，typography.md 联动）【硬规则】**：容器内层级固定为 ① eyebrow/tag（mono 小字、低明度）→ ② 题（标题档）→ ③ 体（正文）→ ④ 注（mono 小字注记、低明度）；**相邻两层至少在字号/字重/明度中分化一项，①④两层强制低明度 mono**——容器内全部同字重同明度即违规（层次感的机器可查底线）。

**与主题七层的接口**：容器造型（圆角/描边/双线图框/撕线…）一律委托主题 G4/G9（§12 硬规则 2 同口径）；§13 只管结构分型与层次纪律，不管造型。母题件可作为容器的 eyebrow/tag 呈现（如 c4 题花作注记块标头、e2 图签作 kv-rows 标题栏）。

**入库形态**：§13 配方进 components.md；gallery 每型一页高密度实例（六页，p45–50）进 T18 回归。

## 二、章节跳转导航（skeleton v7）

### 问题

骨架只有方向键逐页翻页。高密度 deck 页数多（8–10+ 页），demo 证明章节锚点导航（5 章可点 + 滚动高亮）是刚需。用户提"首页按 Tab 跳转"——Tab 是焦点导航，劫持它破坏无障碍；正确做法是**真实锚点 + 键盘直跳**双通道。

### 设计（最小机制，编辑/嵌入零冲突）

1. **章节声明**：页 `<section class="slide">` 可加 `data-chapter="背景与痛点"`（产物内容，语义标注）。
2. **锚点跳转**：章节页或封面放 `<a href="#slide-id" class="nav-link">` 目录链接——原生 `<a>` 天然 Tab 可达、可点击；骨架 JS 把点击转为 `.deck` 容器内平滑滚动（scrollIntoView，scroll-snap proximity 兼容）。**锚点规格**：被跳转的章节页 `<section class="slide">` 带 `id`（与 `data-slide-id` 同值）；`href` 指向该 id；骨架 JS 向上 `closest('.slide-slot')` 定位滚动目标（滚动容器子项是 slot 而非 slide）。封面目录从高密度档起为【默认】要求（SKILL.md 页计划表体现）。
3. **键盘直跳**：数字键 `1–9` 跳第 N 章（按 data-chapter 出现序），`0`/`Home` 回封面，`End` 到末页。监听挂在 `.deck`、仅未聚焦可编辑元素时生效（输入框内数字键不受影响）、嵌入态 passive 不劫持宿主；老 deck 无 `data-chapter` 时数字键不动作（无章节可跳），不产生任何副作用。
4. **编辑器兼容**：跳转无运行时状态（无净化新增项）；**编辑态必须拦截 nav-link 点击**（click preventDefault——否则用户点目录文字想编辑时会触发跳转），编辑器对 `.nav-link` 只做选中/编辑不跳转；这是 editor.html 的新增改动点。
5. reduced-motion 下平滑滚动降级为瞬时跳转。

## 三、动效编排纪律吸收（motion.md 增补，不动既有词汇语义）

从 demo1 Motion Layer 提炼的五条**编排纪律**（我们没有的）：

1. **职能五分法**（动效合法性总纲）：每个动效必须归属五职能之一——① 揭示存在（enter 族）② 数据/状态变化（data 族）③ 因果/空间关系（link 族、draw-line）④ 可交互指示（hover、ptr 族）⑤ 活着的存在感（amb/light/fx 族）。答不上职能 = 删。归属两职以上 = 过重。recipe 词汇表每条的"职能"字段对齐此五分法。
2. **静止期纪律**：Reveal → Hold（≥1.5s）→ Interact。入场完成后内容必须静止足够久；背景动效（amb/fx）不许在静止期抢注意力（强度上限已有，补"为什么"）。
3. **时长≈信息量**：入场 ≈300ms+每比特 200ms（标签 300ms / 卡片 500ms / 数字 1200–1800ms / 拆字 ~1800ms）；循环动效 ≥3s 且越慢越高级。时长档的选择从感觉变成推导。
4. **语义同构**：动效方向匹配内容语义——增长向上、流失向下、修复由警示色到主题色、连接有方向性。与 motifs.md 是同一想象层的两半：motifs 管"静态呈现隐喻"，本节管"动态过程隐喻"。
5. **内容→动效对照表**：查询手册（Hero 标题→shatter/mask-lines；反差数字→count-up 落差；流程→flow-dot/draw-line；对照→左右异步入场；卡片列→stagger；状态指标→mend-bar……），进 motion.md。

### 两个新 recipe（骨架 v7 一并落码，证明吸收不是抄写）

- **`data-anim="mend-bar"`（data 族，双态修复条）**：fill-bar 的语义扩展——入视口后条从 0 填充到 `data-from`（起始值，警示色红→黄渐变，建立张力）→ 再收窄到 `--val`（目标值）并切换为 accent 纯态（修复完成）。条宽 = 指标数值（漏损率 94% → 修复后目标），颜色迁移 = 状态迁移。`data-from`/`--val` 都是产物内容（同 fill-bar/count-up 既有口径）；reduced-motion 直接终态；净化无新增（终态由 CSS class 表达，运行时 class 按既有 .in-view 口径移除）。
- **`data-rotate`（link/amb 之间的 loop 型，轮转高亮）**：容器内 N 个 `[data-rotate-item]` 轮转 `.active` class（间隔 ≥2.2s，in-view 启动、离屏停、reduced-motion 不启动、`__pptxMotion.freeze()` 摘除并清空 active）——承载"流水线各阶段都在工作"的活态隐喻（demo 的 pipeline 轮转）。骨架提供最小默认 active 样式（`color:var(--accent)`），产物/主题可覆盖加强（描边/底色等造型属主题主权）。

## 四、联动改动清单

| 文件 | 改动 |
|---|---|
| `references/components.md` | 新增 §13 文本容器六型 + 四层字阶纪律 |
| `references/typography.md` | 高密度档补"容器内层次"条款（与 §13 互引） |
| `references/motion.md` | 增补职能五分法/静止期/时长公式/语义同构/对照表 + mend-bar 与 data-rotate 两个 recipe 入词汇表 |
| `assets/skeleton.html` | v7：章节跳转（data-chapter + 锚点平滑滚动 + 数字键/Home/End）+ mend-bar + data-rotate 两个运行时/样式 + freeze 覆盖 data-rotate |
| `references/editing-contract.md` | v6.3：data-chapter/nav-link 是产物内容原样保留；data-rotate 的 active class 是运行时状态净化移除；mend-bar 净化口径 |
| `editor.html` | 编辑态拦截 `.nav-link` 点击（preventDefault，只选中/编辑不跳转） |
| `SKILL.md` | 高密度档封面目录【默认】；Step 4 文本容器选型指引（查 §13）；动效对照表引用 |
| `gallery/` | §13 六型高密度实例页（p45–50）进 T18 |
| `tests/harness/run_e2e.py` | T22：章节跳转（数字键直跳/锚点点击/编辑器态无冲突） |
| `tests/decks/smartforge-c1/` | 高密度验收 deck（SmartForge 内容 × c1 信号黑，8–10 页，走全流程） |

## 五、验收标准

- smartforge-c1 deck：高密度档 8–10 页、封面目录可 Tab/点击/数字键三通道跳转、≥3 种文本容器分型、mend-bar 用于痛点页、data-rotate 用于流水线页，渲染自检零溢出零重叠。
- harness：T22 跳转三通道断言 + T1 注册 + T18 六型实例页，全量绿。
- 动效纪律成文后，motifs.md 与 motion.md 对照表互引闭环。
