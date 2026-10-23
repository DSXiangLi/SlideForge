# 信息图系统设计（结构 × 皮肤 × 主题）

> 状态：已实施（迭代 D，2026-09-18） · 依据：2026-09-18 修订意见 3 + antv-infographic 架构调研（`../research/source-survey.md` 体系外补充，调研摘要见本文 §2）
> 实施对象：`references/components.md` 重构为 v2（分层模型）+ SKILL.md Step 4 选型规则修订。

## 1. 问题

当前 `components.md` 是 12 个平铺组件（Stat/Callout/Rowline/Pillar/……）。问题：

- **组合空间被枚举数量锁死**：12 个组件就是 12 种样子，"复杂 fancy 信息图"的上限取决于 AI 临时发挥，质量方差大；
- 组件之间没有共享的底层结构——"三列行"和"步骤链"其实是同一结构族的不同皮肤，现在写成两个配方，新增一个要全文重写；
- 没有数据形态约束：AI 把层级数据填进并列结构、把两项对比填成三列，是常见翻车。

## 2. 借鉴：antv-infographic 的正交组合模型

antv-infographic（AntV 开源的声明式信息图引擎，github.com/antvis/Infographic）的核心架构：

- **模板 = 结构（Structure）× 数据项皮肤（Item）× 主题配置**。约 200 个内置模板全部来自"结构族 × 皮肤"的笛卡尔积——如 `list-zigzag-up-compact-card` = 结构 `list-zigzag-up` + 皮肤 `compact-card`。**命名即组合**，模板数量低成本扩张；
- **结构分七大族**：`list-*`（并列）/ `sequence-*`（顺序流）/ `compare-*`（对比）/ `hierarchy-*`（层级）/ `relation-*`（关系连接）/ `geo-*`（地理）/ `chart-*`（定量图表）；
- **数据字段与结构族硬约定**：`list→lists`、`sequence→sequences`、`compare→compares`（二元对比恰好两个根节点）、`hierarchy→root` 递归、`relation→nodes+relations`、`chart→values`——这是防止 AI 乱填数据的关键护栏；
- **风格化（stylize）是声明式标记 + 统一后处理**：组件只声明哪些图形参与风格化（手绘 rough / 图案 / 渐变），渲染器统一施加，主题层因此保持很薄；
- 扩展机制是注册表（`registerStructure` / `registerItem`），官方还配了"让 AI agent 按规范文档生成新构件"的 skills——与我们"AI coding agent 落码"模式同构。

**红线声明：借鉴架构，不引入库。** antv-infographic 是运行时 JS 库（自研 JSX→SVG 渲染器），引入即违反产物"单 HTML + assets/ 零依赖"的离线红线。我们的对应物：**生成侧 AI 就是渲染器**——结构与皮肤是写在 references 里的配方，AI 按配方落码静态 HTML/CSS。

## 3. 三层正交模型

信息图 = **结构族 × Item 皮肤 × 参数变体**，主题 token 贯穿染色。

### 3.1 结构族（枚举，有限集）

布局与数据组织方式。首版六族（geo 缓建，等真实需求）：

| 族 | 内容关系 | 骨架示例 | 数据字段约定 |
|---|---|---|---|
| `list` | 并列排布 | row / grid / zigzag / waterfall / pyramid | `items[]`（label/desc/value/icon?） |
| `sequence` | 方向性顺序 | steps / timeline / stairs / funnel / snake | `sequences[]`（+可选 order） |
| `compare` | 二元/多元对比 | binary-cols / quadrant / swot / vs-overlay | `compares[]`（binary 恰好两项） |
| `hierarchy` | 层级包含 | tree / mindmap / concentric | `root` 递归（label/children） |
| `relation` | 关系连接 | flow / network / circle-loop | `nodes[]` + `edges[]`（A -标注-> B） |
| `chart` | 定量图表 | 引用 charts.md 四配方 | `values[]`（数据真实性硬规则不变） |

### 3.2 Item 皮肤（枚举，有限集）

单个数据单元的视觉形态，与结构族正交：`bare`（无框纯文字）/ `card`（卡片）/ `badge`（徽章）/ `ribbon`（丝带/标签）/ `stat`（大数字三段式）/ `icon-line`（图标行）等。皮肤只负责"单元长什么样"，不负责布局。

### 3.3 参数变体（不枚举，规则化）

密度档（low/high 影响间距与 desc 有无）、方向（横/纵）、项数（结构族声明合法项数区间，如 zigzag 3–6 项）。变体由规则推导，不产生新枚举项。

**衍生能力 = 6 族 × ~6 皮肤 × 参数变体**，组合空间数百种，而枚举对象只有十几个——这就是"基础样式 + 无限衍生"的落地形态。组合合法性由"族 × 皮肤适配矩阵"约束（如 `stat` 皮肤不适配 `hierarchy` 族），矩阵本身是一张小表，不是逐组合配方。

### 3.4 现有 12 组件的归类映射

| 现组件 | 新模型位置 |
|---|---|
| Stat 数字矩阵 | `list/grid` × `stat` |
| Rowline 三列行 | `list/row` × `bare` |
| Pillar 支柱卡 | `list/row` × `card` |
| Process 步骤链 | `sequence/steps` × `badge` |
| Timeline 时间线 | `sequence/timeline` × `bare` |
| Before/After 对比 | `compare/binary-cols` × `card` |
| Loop 闭环 | `relation/circle-loop` × `bare` |
| H-Bar / KPI Tower | `chart` 族（移交 charts.md） |
| Callout / Ghost / Highlight | 非信息图，归入"页面修饰件"小类保留 |

## 4. 生成侧护栏：数据形态匹配（硬规则）

沿用并强化 antv 的"数据字段↔结构族"硬约定，与现有"内容类型匹配"硬规则合并为一条。执行层面的诚实说明：我们的生成侧直接写 HTML，没有 DSL 解析器——因此这条护栏的落点是 **Step 4 的检查清单 + 页计划表的容量核对**（AI 动笔前自证"本页内容能填入所选族的数据形态"），可机器验证的部分（如 binary 对比恰好两项、项数区间）写进静态校验脚本，其余靠清单约束，不假装有解析器兜底。

- 选定结构族前，内容必须先能填入该族的数据字段形态（并列数据不进 `sequence`，二元关系不进 `list`）；
- 没有真实量化数据不进 `chart` 族（现状硬规则不变）；
- 项数超出结构族合法区间 → 换族或拆页，不硬塞。

## 5. 风格化（stylize）：与主题 Schema 的接口

信息图的"fancy"很大程度来自质感而非结构。借鉴 antv 的声明式风格化思想：

- 主题 Schema 的 G3 texture 字段声明风格化类型（手绘 rough / 柔光 / 图案 / 平色）与作用范围；
- 生成侧落码时，参与风格化的图形元素统一标 `data-stylize`（纯装饰语义，同时标 `data-editable-skip`），按主题配方施加对应 CSS（rough 手绘边 = 不规则 border-radius + 双层错位描边；柔光 = 径向叠加层）；
- **风格化由主题决定，不由单页决定**——换主题即换质感，信息图结构不变。

## 6. 组合与嵌套规则

- 一页一个信息图主体（一页一意原则在信息图层的投影）；信息图旁允许配 Callout/Highlight 修饰件；
- **嵌套允许一层**：信息图 Item 内可嵌 chart 族小图（如卡片内嵌迷你柱图），禁止信息图套信息图；
- 嵌套时容量预算分摊：内层占用外层的槽位预算（typography.md §4 的折算不变），预算超限换结构或拆页；
- 复杂标注（引线、角标、数值旗标）作为独立修饰件配方入库——**标注 = 文字元素，不进几何**，全部 `data-editable`（沿用 optimal-solution.md 标准④判断）。

## 7. 可编辑契约

- Item 的 label/desc/value 文字：`data-editable`（就地可改）；
- 结构装饰（连线/箭头/背景形）：`data-editable-skip`；
- 结构变更（增删项、换族、改数据字段）：走 AI 流程（与图表数值分层同理）——静态 HTML 不做"改文字重排布局"的承诺，边界声明保持诚实；
- 批注：信息图任意元素可框选批注（editor 现有能力，无新增契约）。

## 8. 扩展与验收

- 新结构族 / 新 Item 皮肤入库走 `../research/sota-visual-languages.md` 七件规范：身份卡（与现有族/皮肤的可区分性）、骨架、量化规则（合法项数区间/适配矩阵行）、密度适配、可编辑分层声明、反模式、三级验收；
- 验收专项：每个结构族至少一个测试页过渲染校验（溢出/重叠）；适配矩阵静态可验（族 × 皮肤组合白名单）；数据字段形态在 SKILL.md Step 4 以检查清单形式落地。

## 9. 明确不做

- 不引入任何运行时信息图库（antv-infographic 本体、D3、ECharts 一律不引）；
- 不做信息图的页面内可视化编辑器（编辑器只改文字，结构修改走 AI 落码）；
- `geo` 族缓建；3D 透视类结构缓建（与 16:9 竖滚阅读流的相性未验证）。
