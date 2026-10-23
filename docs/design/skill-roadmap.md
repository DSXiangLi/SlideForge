# html-pptx 技能迭代方案

> 版本：v1.0 · 2026-09-16
> 对象：`skills/html-pptx/`（当前 v1）
> 依据：`docs/research/source-survey.md`（宏观调研）+ 四能力域深挖报告（2026-09-16 第二轮，带文件路径的资产提取）
> 约束：迭代必须守住技能的三条命根子——原则优先枚举谨慎、产物纯净（单 HTML + assets/ 零依赖）、可编辑契约不被破坏。

## 一、优化空间全景

### 1. 内容密度策略（低/高双档）

**现状缺口**：SKILL.md 只有"容量先于版式"原则，没有密度的操作化定义；页计划表没有密度维度。

**借鉴**：
- frontend-slides 的 Content Density Modes（`SKILL.md:54-63`）：**只分两档不发明中间档**——低档 speaker-led（一页一意、大字、1-3 条 bullet、宁可加页），高档 reading-first（自包含页、结构化 grid/表格、4-8 bullets、间距收紧但有意）；混合需求"向更近一档靠拢"。两档共享底线：不溢出、不缩字号，超出就拆页。
- dashi 的槽位字数预算（`copy-contract.mjs`）：7 档语义槽（serial/tagline/metric/display/compact/brief/body）各带 maxChars，**全角记 1、半角记 0.5** 折算视觉宽度——这是"容量先于版式"的最可操作形态，浓缩为 4 档（display ≤36 字 / brief ≤80 / body ≤120 / metric ≤16）。
- guizang 中文标题分档表与字重阶梯（`SKILL.md:400-438`）：1 行 ≤8 字 → `min(6.4vw,11.2vh)`；≥3 行优先改写标题；字号×字重反比（≥8vw→200，13-15px→500-600）——中文场景的血泪资产，直接抄。

**方案**：密度成为开工前的冻结决策（Step 1 页计划表加"密度档"列）；新增 `references/typography.md` 承载分档表/字重阶梯/槽位预算；design-system 面板意图 Schema 增加 `density` 单选题（low/high），与 theme/rhythm/motion 并列。

### 2. 高质感信息图

**现状缺口**：版式层只有原则，没有"组件"这一中间层——AI 每页从零发明结构，质量方差大。

**借鉴**：
- guizang 组件手册（`references/components.md`）：Stat 数字三段式（mono 标签/巨数/注释）、Callout、Rowline 三列行、Ghost 巨型背景字、Highlight 荧光标记——纯 HTML/CSS 资产，可直接改写。
- guizang 的**内容类型匹配 P0**（`layouts-swiss.md:860-882`）：有真实量化数据才能用图表类版式，纯定性论断严禁用 KPI/柱图（编造数据会被识破）；项数必须匹配——这是反 AI-slop 的核心规则，升为我们的【硬规则】。
- ppt-master 图示类型库（`image-type-templates/`）：11 种几何构图骨架（并列/流程/中心辐射/象限/闭环/漏斗/金字塔/对比/时间线/地图/场景），"类型是图块内部骨架、按图块决定"的视角 + `text_policy`（图内嵌字 vs 外部标注）。

**方案**：新增 `references/components.md`——每个组件只给"结构骨架 + 适用场景 + 内容类型门槛"三件套（**不给登记版式锁**，守住原则 2）。text_policy 理念接契约：图内嵌字 = 不可编辑走 `data-editable-image`，文字外置 = 可编辑。

### 3. 图表

**现状缺口**：完全没有。主题 token 也只有色/字，没有图表系列色。

**借鉴**：
- dashi 的 `chartTreatment` 五件套主题槽位（grid/label/series[]/barRadius/strokeWidth，`theme-profile-core.mjs:94-98`）——补上主题系统的图表维度。
- guizang 的 CSS 变量驱动条图（`--w`/`--h` + scaleX/scaleY 入场，`template-swiss.html:536-542` 的 bar-row 三列 grid）——零 JS 零依赖，最贴我们的红线。
- dashi 四种图表几何参数（bar 的 slot/barWidth/zeroY、donut 的 dasharray 分段、progress 纯 HTML）——bar/line/donut/progress 即最小充分集。
- 不抄：open-design 的 Chart.js CDN 路径（违反离线红线）。

**方案**：新增 `references/charts.md`（四图表配方 + 数据→几何安全原则：先 clamp、防除零、防空数组）；themes.md 每主题补 chart token 块；**数据真实性 + 填数后 insight 必须改写**升为硬规则。

**契约断层（必须先写清楚）**：静态文件里用户就地改图表数值文字，几何不会跟着变。dashi 式分层——**图例/标签文字 `data-editable` 可改，数值列与几何绑定（改数走 AI 流程），SVG 几何整体 `data-editable-skip`**——写进 editing-contract.md 的图表章节。

### 4. 动态视觉效果

**现状缺口**：骨架只有单一 `.reveal` 淡入，没有动效语义层；面板"动效强度"选项没有对应的生成侧词汇。

**借鉴**：
- guizang 的 `data-animate` 双层语义模型（section 级 recipe × 元素级角色，5 种 recipe + 决策树）——recipe 是语义、参数是实现，最贴"原则优先"。
- frontend-slides 的 Effect-to-Feeling 表（Dramatic/Techy/Playful/Professional/Calm/Editorial 六感）——中文化后就是面板"动效气质"选项的语义词汇。
- guizang 降级链 + B 键低功耗 + reduced-motion 默认降级；open-design fx-runtime 的"进入启动/离开停止"生命周期（我们把它的 MutationObserver 换成 IntersectionObserver，已在骨架）。

**方案**：骨架框架层升级（这属于"逐字复制区"的框架升级，不是逐页自由）：`data-animate` recipe 引擎，IO 触发、文本安全动画集（fade/slide/blur/scale/逐行）与**文本破坏性动画（拆字类）禁用清单**——拆字与就地编辑互斥，写进契约；面板 `motion` 选项从三档强度改为"气质六选 + 强度"。

### 5. 此前已定位的优化空间

| 空间 | 方案 |
|---|---|
| 构图缺乏中间层 | 由方向 2 的 components.md 覆盖 |
| themes.md ↔ editor 面板数据双源手工同步 | 写 `scripts/sync-themes.mjs`：从 themes.md 解析生成面板 JSON，CI/手动跑，消灭双源漂移 |
| pptx 转换入口只有一句话 | SKILL.md Step 0 展开为转换子流程：提取文字/图片 → 图片落 assets/ → 按密度档重新组织叙事（**不是逐页复刻 pptx**，是内容重组） |
| 占位图指导薄 | SKILL.md 图片纪律补占位图规格（主题色抽象图形、尺寸即构图尺寸、语义化文件名——4 个测试 deck 已验证可行） |

## 二、分期迭代方案

### v1.1 · 密度与字排（纯文档层，零视觉资产风险）

- SKILL.md：Step 1 页计划表加密度档列；Step 0 展开 pptx 转换子流程；图片纪律补占位图规格
- 新增 `references/typography.md`：中文标题分档表、字重阶梯、槽位字数预算（4 档浓缩版）
- editor.html：面板内置 JSON 增加 `density` 单选题（low/high）——手工同步一次，v1.3 起由脚本接管
- 契约：无变化
- 验收（量化）：同一内容源按低/高两档各生成一个 deck——低档页数 > 高档；每页 `data-editable` 文本总字数 ≤ 槽位预算表上限（脚本可验）；两档均过渲染溢出校验

### v1.2 · 信息图组件层

- 新增 `references/components.md`（三件套格式）+ SKILL.md 挂"内容类型匹配"硬规则
- 新增 1-2 个信息图密集的测试 deck（真实数据场景）
- 验收：新 deck 过 harness 回归 + 组件标记合规（文字 editable / 装饰 skip）；harness 为组件新增的元素类型补充对应用例

### v1.3 · 图表

- 新增 `references/charts.md`；themes.md 每主题补 chart token 五件套；editing-contract.md 加图表可编辑分层章节
- **`scripts/sync-themes.mjs` 提前到本期**：themes.md 结构变更（加 chart token）时，面板数据双源同步机制必须先行——脚本从 themes.md 解析生成 editor.html 面板 JSON，消灭手工漂移
- 验收：含四类图表的测试 deck，图表数值/标签的编辑行为符合契约分层

### v1.4 · 动效语义层

- **骨架框架层升级**（data-animate 引擎 + IO 触发 + 降级链）。配套两个防漂移措施：
  - 骨架加版本标记（`<meta name="skeleton-version" content="2">`），SKILL.md 注明"以仓库当前骨架版本为准"；存量 deck 不追溯（旧版本骨架的产物编辑器继续兼容）；
  - **编辑器侧同步交付**：净化清单（设计文档 §5.4）新增动效运行时状态项，harness 回归覆盖新骨架 deck。
- 新增 `references/motion.md`（Effect-to-Feeling 中文表 + recipe 决策树 + 文本破坏性动画禁用清单）
- 契约加拆字互斥条款；面板 motion 选项接六感词汇（sync 脚本同步）
- 验收：动效 deck 在 reduced-motion 下静态可读；编辑态不受动画影响；新旧骨架 deck 的往返幂等都通过

### v1.5 · 工程化收尾（评估结论）

- ~~`scripts/sync-themes.mjs` 双源同步~~ → **已提前至 v1.3 完成**（editor.html 面板数据改为脚本生成，幂等写回 + 自检）；
- **WebGL/氛围背景：结论——不进入骨架，推迟**。理由：① 我们的形态是竖向滚动阅读流，氛围背景的价值低于发布会式翻页 deck；② guizang 的 WebGL 三件套（hero 透出/getContext 兜底/低功耗停 RAF）会显著加重"逐字复制"的框架层，违背克制原则；③ 当前 `.js` 门槛 + reduced-motion 降级链已经完整。若未来有真实需求（如发布会场景），以"单页级背景层"形式单独评估，不进默认骨架；
- **宿主嵌入深化：结论——推迟到宿主确定**。最小闭环（load/save/dirty/annotations）已实现并通过验收；鉴权、双向协议扩展依赖真实宿主环境，凭空设计必然返工。

## 三、排序逻辑

1. **先文字后视觉再动效**：密度/字排（v1.1）是内容层的根，信息图和图表（v1.2/1.3）都建立在容量与字阶规则之上；动效（v1.4）改骨架框架层，风险最高放最后；
2. **契约先行**：图表分层（v1.3）和拆字互斥（v1.4）都先改 editing-contract.md 再改 SKILL.md——契约是编辑器与生成器之间唯一的协议，不能后补；
3. **每期都有可执行的验收**：测试 deck 驱动，harness 回归兜底，不做没有验证手段的迭代。

## 四、未来规划（2026-09-18 补充，设计文档见 `design/`）

以下方向已完成设计；主题 Schema / 动效 v2 / 信息图 v2 已按迭代 B/C/D 实施完毕，其余排期不变：

| 方向 | 设计文档 | 要点 | 状态 |
|---|---|---|---|
| 主题 Schema 化 | `design/theme-schema.md` | 主题定义升级为显式 Schema（G0–G8 字段组）+ focus 重点/辅助项机制 + 缺省推导规则 | ✅ 已完成（迭代 B） |
| 主题差异化与想象层 | `design/theme-expression-stack.md` | G 期：七层表达力栈（L1–L7 ↔ G0–G9）+ skeleton v6 主题 CSS 槽位 + 两级架构（重主题 × ≥3 配色变体）+ 两两七层 diff ≥3 机器门槛；H 期：motifs.md 隐喻库 + SKILL.md 呈现发散步；I 期：世界采样建库 20 重主题 + 撞脸矩阵；J 期：同题三主题终验 | ✅ 全部完成（2026-09-19/20）；肉眼验收待用户 |
| 动效系统 v2 | `design/motion-system.md` | 拆字禁令改为"运行时拆字"（产物文字永远是纯文本节点）；motion_gudie 三原理六原则入库；recipe 词汇扩展（shatter/count-up/draw-line 等） | ✅ 已完成（迭代 C） |
| 信息图组合衍生 | `design/infographic-system.md` | 结构族 × Item 皮肤 × 参数变体正交模型（借鉴 antv-infographic 架构，不引入库）；数据字段与结构族硬约定 | ✅ 已完成（迭代 D） |
| AI 插画管线 | `design/illustration-pipeline.md` | 内容验收后统一补齐插画；`data-image-slot` 槽位契约；反降级静态校验 | ✅ 已完成（迭代 E） |
| 向上兼容（全图化） | `design/compat-roadmap.md` | 页面级转全图（HTML 截图 / AI 重绘），混合 deck，原页 HTML 注释保留可回退 | 待评审 |
| 向下兼容（html2pptx） | `design/compat-roadmap.md` | 三层映射（原生元素 / 结构降级 / 整页截图），独立工具不进产物 | 待评审 |
| 编辑器图片 reframe 裁剪 | `research/demo1-framework-comparison.md` §三 | 换图后的裁剪调整（平移/缩放/角点拖拽，omelette 系 image-slot 先例）；工程量大，排期在 compat 评估后 | 待评估 |

依赖顺序：插画管线 → 全图化 → html2pptx；主题 Schema 是动效亲和（G5）与插画风格（G7）的前置。
