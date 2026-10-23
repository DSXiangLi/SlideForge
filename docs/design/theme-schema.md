# 主题 Schema 设计（Theme Schema）

> 状态：已实施（迭代 B，2026-09-18） · 依据：2026-09-18 修订意见 1 · 关联：`../research/sota-visual-languages.md`（枚举规范）、`../../skills/html-pptx/references/themes/index.md`（现状）
> 后续演进：G 期七层表达力栈见 `theme-expression-stack.md`（G0–G9、两级主题架构、两两七层 diff 门槛）——本文档的 G0–G8 口径已被其取代，本文保留作迭代 B 历史记录。
> 实施对象：`references/themes/index.md` 重构 + `scripts/sync-themes.mjs` 升级 + editor.html 面板分组。

## 1. 问题

当前 themes/index.md 的 13 套主题只有"6 色 token + 3 字体栈 + 使用要点"的隐式惯例，没有显式 Schema。后果：

- 主题之间靠作者自觉对齐字段，新增主题没有结构约束，枚举不可扩展；
- **无法表达"重点在质感/手绘"这类非颜色主题**——比如"柔光质感"主题的差异化不在配色而在材质层，现有 token 结构无处安放；
- editor.html 的 design-system 面板只能按色系平铺展示，无法向用户传达"这个主题的灵魂是什么"。

用户裁定：主题仍**只选不改**，但主题的定义必须是显式 Schema；每个主题不必覆盖 Schema 全部字段，**必须有重点（focus）与辅助项**——重点是设计感的来源（奶油配色 / 柔光质感 / 手绘衬线 + 油画配色……），其余字段组是配套的视觉语言。

## 2. Schema 定义

主题 = 9 个字段组。G0/G1/G2 必填核心，G3–G8 可选。

| 组 | 字段 | 必填 | 内容 |
|---|---|---|---|
| G0 identity | id、名称、气质一句话、适用场景、**focus 声明** | ✅ | focus = 1–2 个字段组编号（见 §3） |
| G1 color | paper / paper-tint / ink / ink-tint / accent / accent-on、**accent 用量预算**（内容页面积上限 / 满屏特权页 / 首尾色彩闭环，F1 新增） | ✅ | 现状已有，语义不变 |
| G2 typography | font-display / font-body / font-mono、字重倾向、**字号对比档**、**字重映射**（F1 新增，照 typography.md §3/§5 口径）、标题修饰（可选：首字下沉、斜体强调等） | ✅ | 现状已有字体栈；字重倾向与标题修饰为新增 |
| G3 texture 质感 | 材质类型（柔光 glow / 颗粒 grain / 纸纹 paper / 手绘 hand-drawn / 平色 flat / 氛围光 aura〔J 期新增：多团光斑/渐变带/暗角等光学氛围层，见 `theme-optical-axes.md`〕）+ 实现 token（叠加层规格、强度、范围） | **立场必填**（F1 起：flat 也要显式写出，"flat 即质感立场"） | **新增维度**，见 §4 |
| G4 shape 形态 | 圆角策略、hairline/分割线风格、阴影策略 | 可选 | 现状散落在"使用要点"里，收编为字段 |
| G5 motion 动效亲和 | 气质六选 + 强度上限 + 禁用 recipe | 可选 | 与 `motion-system.md` 的词汇表对齐（如 editorial 系禁止 shatter） |
| G6 chart | 图表 token 覆盖 | 可选 | 缺省走 themes/index.md 已有的 color-mix 统一推导 |
| G7 illustration 插画风格 | 风格描述 + 提示词种子 + 禁忌 | 可选 | 为 `illustration-pipeline.md` 的 AI 生图打底 |
| G8 component 组件亲和 | 特别适合 / 禁止的信息图结构族与组件 | 可选 | 与 `infographic-system.md` 的结构族编号对齐 |

### 缺省推导规则（集中维护，只此一份）

可选字段组缺省时按下表推导，**不允许"留空且无规则"**：

| 缺省组 | 推导规则 |
|---|---|
| G3 texture | flat（平色，无叠加层） |
| G4 shape | 按系列默认：A/B 系 radius=0、无阴影；C 系 radius ≤8px |
| G5 motion | 全局默认气质（professional）+ 无禁用 |
| G6 chart | 统一 color-mix 推导（现状规则） |
| G7 illustration | 主题色抽象图形（即占位图风格，等价于"纯 HTML 模式"） |
| G8 component | 无特别亲和，全组件可用 |

## 3. focus 机制（重点与辅助项）

- 每个主题**必须声明 1–2 个字段组为 focus**（写在 G0）。focus 是该主题设计感的来源。
- **focus 组的字段必须全部显式给出**。机器可验到此为止（字段在场且 ≠ 缺省推导值可静态检查）；focus 的"显著性"（该组确实构成设计感来源）属主观判断，归入人工验收，不伪装成机器检查。
- 非 focus 组是配套视觉语言：要么显式给出、要么走缺省推导，两者都合法。
- 示例（用户给的三个方向，作为候选新主题的形态演示）：

| 候选主题 | focus | 配套 |
|---|---|---|
| 奶油物语 | G1 color（奶油色系：暖白/浅杏/焦糖 accent） | G3=平色，G2=圆润无衬线，G4=大圆角 |
| 柔光暗房 | G3 texture（柔光叠加：径向辉光 + 低透明度光斑层） | G1=深底暖光，G5=ambience 型动效亲和 |
| 手绘油彩 | G2 typography（手绘衬线）+ G1 color（油画氤氲配色：灰绿/赭石/雾蓝） | G3=纸纹颗粒，G7=手绘插画风格种子 |

- 入库可区分性：新主题的 **focus 组合 + 核心色**须与现有主题两两可区分（"它和 A1 的区别是什么"答不上来就不入库——沿用 sota-visual-languages.md 的可区分性声明）。

## 4. texture 字段组的技术形态

质感必须落在 token 上，不允许逐页自由发挥（否则换主题即破）：

```css
/* 主题 token 块内（示例：柔光暗房） */
--texture-type: glow;
--texture-layer: radial-gradient(120% 90% at 70% 10%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 60%);
--texture-scope: cover;   /* cover=仅封面/章节页；all=全页（谨慎） */
```

骨架在 `.slide` 背景层预留一个质感槽位（`SLOT` 之外的固定结构，消费 `--texture-layer`），主题不给质感时该层为空——**质感是主题维度，不是页面自由度**。此改动与 `motion-system.md` 的运行时拆字引擎同属骨架框架层升级，**合并为 skeleton v3 一次发布**（`<meta name="skeleton-version" content="3">`），存量 deck 不追溯。手绘类质感（rough 边框、不规则填充）作用于组件层，在 G8 中声明亲和的结构族，由生成侧按配方落码（参考 antv-infographic 的 stylize 声明式标记思想，见 `infographic-system.md` §5）。

**F1 修订（skeleton v4，2026-09-19）**：质感层改为**背景配给制**——默认只铺仪式页（`.cover-page`），正文页启用须生成侧逐页显式加 `.texture-on`（纯 CSS 配给，无运行时状态）；`--texture-scope` 从"自动开关"降级为主题级许可声明（`cover`/`all`）。同时 G3 从可选升级为立场必填（16 主题全部显式声明，flat 写出"flat 即立场"），校验器强制执行。

## 5. 现有 13 套主题的迁移映射

| 系 | focus 判定 | 说明 |
|---|---|---|
| A1–A5（电子杂志×电子墨水） | G1 + G2 | 双色墨水配色 + 衬线字排即灵魂；G4 走系列默认（无阴影无圆角） |
| B1–B4（瑞士国际主义） | G1 + G4 | 单一高亮色 + hairline 网格即灵魂；G4 需显式写出 hairline 规格 |
| C1 信号黑 / C3 终端绿 | G1 | 配色主导；C3 的 G2 全 mono 需显式 |
| C2 暗夜植物园 | G1 + G3 | 暗底暖金 + 柔光质感（现有"点缀"描述升级为 texture 字段） |
| C4 纸与墨 | G2 | 全衬线 + 标题修饰（首字下沉）主导 |

迁移不逐字重写存量主题描述，只做**字段归位**：把"使用要点"里的规则拆进 G4/G5/G8 字段，补齐 G0 的 focus 声明。

## 6. 验收标准

- **机器可验**（扩展 `scripts/sync-themes.mjs` 兼任 schema 校验）：每主题 G0/G1/G2 字段齐全；focus 声明的字段组全部显式且 ≠ 缺省值；无主题外 hex；可选组缺省时推导规则可查。
- **渲染可验**：每主题至少一个样板页过 Playwright 渲染（无溢出、accent 面积 ≤ 阈值、texture 层不遮挡文字——对比度达标）。
- **人工可验**：focus 声明与实际观感一致；三个候选新主题方向（奶油/柔光/手绘油彩）各出一页样张评审。
- **面板同步**：sync-themes.mjs 解析 Schema 后，editor.html 面板按 focus 分组展示（"配色主导 / 质感主导 / 字排主导"），让用户**看着重点选**，而不是在 13 个色板里盲选。

## 7. 明确不做

- 不给用户自定义 hex 的口子（只选不改原则不变）；
- 不为每个主题枚举页面版式（L4 版式层保持原则驱动，`sota-visual-languages.md` §2 分层不变）；
- texture 不引入图片纹理资产进骨架（纹理用 CSS 渐变/混合实现，保持零依赖；用户自加纹理图走 assets/ 由 AI 落码）。
