# G10 管线缺口审计报告

> 日期：2026-11-17
> 触发：用户发现 E3 新 sampler 与原 sampler 差异大，质疑 G10 是否真正落实到技能中
> 结论：**G10 是死文档——写在 13 套 theme.md 里但 SKILL.md 生成管线 0 引用**

---

## 一、问题定位

### 1.1 核心事实

对 SKILL.md 全文检索 8 个 G10 关键词，**全部 0 次出现**：

| 关键词 | SKILL.md 出现次数 |
|---|---|
| G10 | 0 |
| composition_program | 0 |
| signature_operator | 0 |
| info_grammar | 0 |
| invariants | 0 |
| forbidden_defaults | 0 |
| dna_events | 0 |
| page_composition | 0 |

### 1.2 生成管线中的缺口位置

SKILL.md 的生成流程是 Step 0 → Step 5.7，G10 应该接入但未接入的位置：

| 步骤 | 当前内容 | G10 缺口 |
|---|---|---|
| **Step 1 · 页计划表** | 列出页/角色/内容/明暗/呈现发散；密度决策冻结 | **不读 G10 `info_grammar`**——每页该用什么构图骨架（如 G5 的 claim = 裂屏对开、E2 的 analysis = 双线图框阵列）完全不在 agent 视野里 |
| **Step 2 · 冻结主题** | token 复制进 SLOT、G9 CSS 逐字复制、材料合成、多色立场 | **不读 G10 `composition_program`**——只复制 G1（色值）和 G9（母题 CSS），G10 的 `doctrine`/`page_composition`/`signature_operator`/`invariants`/`forbidden_defaults`/`dna_events` 完全不提 |
| **Step 4 · 逐页生成** | "重读一遍主题 token 和页计划表中本页那一行"；构图由内容决定；查 components.md/charts.md/motion.md | **不读 G10 `signature_operator`**——agent 不知道该主题的信息编译规则（如 G4 的"核心信息独占太阳黄出血面"、G5 的"核心信息独占暗夜蓝底苔绿字反转面"）；**不遵守 G10 `forbidden_defaults`**——agent 仍会使用横排等权三格 KPI（G10 明确禁止）；**不遵守 G10 `invariants`**——agent 不知道每页的硬约束（如 G5 的"三色反转面 ≥2 块/页"、"暗夜蓝面积 ≤40%"） |

### 1.3 唯一的部分接入

components.md 和 typography.md 有 4 处**被动引用** G10 `signature_operator`，但都是例外条件（"如果 G10 声明了 XX，则可以 YY"），不是主动驱动（"agent 必须读 G10 并按其契约执行"）：

| 文件 | 位置 | 引用方式 |
|---|---|---|
| components.md §13 规则 5 | "例外：主题 G10 `signature_operator` 显式声明了错落/阶梯作为签名手段时，基线可以不齐" | 被动例外 |
| components.md §13 规则 6 | "例外：主题 G10 `signature_operator` 显式声明了不同区域的列参数差异作为构图手段时" | 被动例外 |
| components.md §13 规则 7 | "例外：主题 G10 `signature_operator` 显式声明了垂直错落作为签名手段" | 被动例外 |
| typography.md §1 | "② 主题 G10 `signature_operator` 显式声明了换行作为构图手段" | 被动例外 |

### 1.4 主题覆盖状况

30 套主题中 **13 套有 G10，17 套没有**：

**有 G10（13 套）**：B1、C1、C3、E2、E3、E5、E6、E7、F1、G2、G4、G5、H1

**无 G10（17 套）**：A1、C2、C4、D1、D2、D3、D4、E1、E4、E8、E9、E10、E11、E12、F2、F3、G1

### 1.5 themes/index.md Schema 缺口

index.md 的 Schema 表（七层表达力栈 L1–L7 ↔ G0–G9）**没有 G10 行**——G10 不是 Schema 的正式字段。这意味着 `sync-themes.mjs` 校验器不会检查 G10 是否存在、是否完整。

---

## 二、分析

### 2.1 为什么 G10 成了死文档

G10 composition_program 是在 Phase 6（主题审美巅峰优化）中逐批补入 theme.md 的。设计意图是让主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。但补入时只改了 theme.md（数据层），没有同步改 SKILL.md（管线层）和 index.md（Schema 层）。

三层缺口：
1. **Schema 层**（index.md）：G10 不是正式 Schema 字段 → 校验器不检查 → 无 G10 的 17 套主题也不报错
2. **管线层**（SKILL.md）：Step 1/2/4 不引用 G10 → agent 生成 PPT 时不读 G10 → G10 契约不生效
3. **数据层**（theme.md）：13 套有 G10，17 套没有 → 即使管线接入，无 G10 的主题也无法被驱动

### 2.2 影响

- **所有 13 套"已升级 G10"的主题**：G10 契约（`info_grammar`/`signature_operator`/`invariants`/`forbidden_defaults`）不会影响实际生成的 PPT。agent 仍会使用 G10 禁止的默认模板（横排等权三格、卡片墙、居中 hero）。
- **theme-sampler / gallery**：原 sampler 是 G10 升级前构建的，全部用同一套布局模板，违反所有 G10 主题的 `forbidden_defaults`。手工构建的 G10 sampler 无法被 agent 复现——因为管线不驱动 G10。
- **之前所有批次的 G10 升级工作**：包括批次 1（E6/G2/E7/F1/C1）和批次 3（E2/E3/G4/G5）的 G10 composition_program 撰写——都是投入了大量精力但不会被消费的死文档。

### 2.3 E3 sampler 差异大的直接原因

原 sampler 的 E3 用居中对称布局 + 三等宽 flex KPI（`flex:1` × 3）。E3 的 G10 `forbidden_defaults` 明确禁止「横向等权三格 KPI」，`info_grammar.claim` 要求"中轴金框装主张句 + 两侧金线翼卫 + 底部菱形引出说明"，`signature_operator` 要求"三项数字重排为对称双栏的镜像模块（非横排等宽三格），主数字在中轴金框内"。

我手工构建的新 sampler 尝试遵循 G10，但因为没有管线支撑，结果既不是原 sampler 的样子，也不是 agent 实际会生成的样子——它是我临时手写的，不可复现、不可信任。

---

## 三、修复方案

### 3.1 优先级排序

| 优先级 | 修复项 | 影响范围 |
|---|---|---|
| **P0** | SKILL.md Step 2/4 接入 G10 | 让 agent 知道要读 G10 并按其契约生成 |
| **P1** | index.md Schema 补 G10 行 | 让 G10 成为正式字段，校验器可检查 |
| **P2** | 17 套无 G10 主题补写 G10 | 让全部 30 套主题都有 G10 驱动 |
| **P3** | gallery/index.html 按 G10 重建 | 让 sampler 展示 G10 驱动的布局 |

### 3.2 P0 修复细节：SKILL.md 接入 G10

#### Step 2 · 冻结主题（补入 G10 读取指令）

当前 Step 2 只说"token 复制进 SLOT、G9 CSS 逐字复制"。需要补入：

> **G10 composition_program 读取【硬规则】**：选定主题后，如果 theme.md 含 G10 `composition_program`，必须逐字段读取并作为本 deck 的构图契约写入页计划表头：
> - `doctrine`：主题的世界观——所有构图决策必须与此一致
> - `page_composition`：骨架构图（skeleton）、网格参数（grid）、平衡锚点（balance）、留白率（whitespace_ratio）、信息流（flow）
> - `signature_operator`：信息编译规则——每条信息如何变成视觉元素
> - `info_grammar`：每页类型的构图契约（cover/claim/analysis/data/closing 各一条）
> - `invariants`：每页必须满足的硬约束
> - `forbidden_defaults`：禁止使用的默认模板
> - `dna_events`：每页类型的 DNA 强度（强/中/弱）
> - `type_scale`：主题的 `--t-*` 令牌源（已在 G1/G2 层消费，此处确认一致性）
>
> 无 G10 的主题走骨架缺省（当前行为不变）。

#### Step 1 · 页计划表（补入 G10 info_grammar 驱动）

当前 Step 1 的页计划表只有 6 列。需要补入：

> **G10 `info_grammar` 驱动页型构图【硬规则】**：如果主题含 G10，页计划表的"呈现发散"列必须引用 G10 `info_grammar` 中对应页型的构图契约。例如主题 G5 的 claim 页，构图必须遵循 `info_grammar.claim`："裂屏对开（暗夜蓝/苔绿或暗夜蓝/赭石对撞），主张句在暗夜蓝底苔绿字上"。

#### Step 4 · 逐页生成（补入 G10 signature_operator + invariants + forbidden_defaults 驱动）

当前 Step 4 说"重读一遍主题 token 和页计划表中本页那一行"。需要补入：

> **G10 契约遵守【硬规则】**：每页动手前，如果主题含 G10，必须重读：
> 1. `signature_operator`——本页信息如何编译成视觉元素（如 G4 的"核心信息独占太阳黄出血面"、G5 的"核心信息独占暗夜蓝底苔绿字反转面"）
> 2. `invariants`——本页必须满足的硬约束（如 G5 的"三色反转面 ≥2 块/页"、"横排等权三格容器数 = 0"）
> 3. `forbidden_defaults`——本页禁止使用的默认模板（如 G4 的"横向等权三格 KPI"、E3 的"居中 hero（裸居中文字无金框）"）
> 4. `info_grammar[本页类型]`——本页的构图骨架
>
> 违反 G10 `forbidden_defaults` 或 `invariants` 的页面必须重构，不得以"内容需要"为由豁免（如果内容确实需要，说明该主题不适合此内容，应换主题）。

### 3.3 P1 修复细节：index.md Schema 补 G10 行

在 Schema 表（L1–L7 ↔ G0–G9）中补入：

```
| L8 构图程序 | 主题的构图 DNA——doctrine / page_composition / signature_operator / silhouette / info_grammar / type_scale / invariants / forbidden_defaults / dna_events | G10 composition_program | 有则必填完整 |
```

并补入 `sync-themes.mjs` 校验逻辑：如果 theme.md 含 G10，则所有子字段必须存在。

### 3.4 修复范围控制

本次只修 P0（SKILL.md）和 P1（index.md Schema），不修 P2（17 套主题补写 G10）和 P3（gallery 重建）——后者是后续批次的工作量。

---

## 四、验证方法

修复完成后，验证 SKILL.md 中 G10 关键词出现次数应 > 0：
- `G10` 或 `composition_program` 在 Step 2 和 Step 4 中各至少出现 1 次
- `signature_operator` 在 Step 4 中至少出现 1 次
- `forbidden_defaults` 在 Step 4 中至少出现 1 次
- `info_grammar` 在 Step 1 中至少出现 1 次
- `invariants` 在 Step 4 中至少出现 1 次
