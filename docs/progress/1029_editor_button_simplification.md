# 1029 · 编辑页按钮简化（重复项盘点与合并方案）

> **状态**：**S1 + S2 已实施并自测通过（2026-10-29）**（用户勾选范围）；S3–S5 未做
> **结果**：markup 按钮 **58 → 54**（S1 删 2 + S2 删 3 增 1）
> **日期**：2026-10-29
> **来源**：用户——"简化编辑页面的按钮，当前看有很多重复"

---

## 1. 盘点

`editor.html` markup 区共 **58 个 `<button>`**（不含 `<select>`/`<input>`）：

| 容器 | 数量 | 内容 |
|---|---|---|
| `(root)` 页头 | 7 | 打开文件 / 保存(⌘S) / 替换图片 / 历史 / 重烙当前页(hidden) / 补齐插画(hidden) / 目录折叠 |
| `seg` 分段控件 | 12 | 视图三页签(编辑/批注/翻转) · 文字对齐四态 · 对比三模式 · 产物两页签(产物清单/对比质检) |
| `bridge-bar` 桥栏 | 3 | 重烙当前页(hidden) / 补齐插画(hidden) / **请求记录** |
| `brief-*` 简报 | 5 | 关闭 ✕ / 确认并发送简报 / 复制简报 / 停止处理(hidden) / 续用副本(hidden) / 重新构建(hidden) |
| 弹窗 `btns` | 7 | 取消/放弃修改/保存并继续（未保存弹窗）· 取消/提交批注（批注弹窗）· 取消/确定（确认框） |
| 其余 | 24 | 文字样式条(2) · 尺寸 −/＋(2) · 告警条(2) · 对比工具条(2) · 空状态(1) · 舞台(2) · 源层(1) · 批注底栏(2) · 导出栏(2) · 下载菜单(4) · 抽屉底栏(3) · 右缘条(2) |

## 2. 重复清单（含证据）

| # | 重复项 | 证据 | 说明 |
|---|---|---|---|
| **D1** | **重烙当前页 / 补齐插画 —— 两对完全一样的按钮** | 页头 `btnBake`/`btnIllustrate`（`:971-972`）**与**桥栏 `btnBridgeBake`/`btnBridgeIllustrate`（`:979-980`）；两者绑**同一个** handler（`:8926-8929` 都调 `requestBakeCurrent`/`requestIllustrate`）。`:969-970` 的注释自己写明："非 Bridge 形态的生图入口，Bridge 态由桥栏承担且 UI 不变" | 同一功能两个位置、按形态二选一 → **可以只留一份** |
| **D2** | **简报结果区的恢复三按钮 vs 任务面板五按钮** | `btnBriefStop/Resume/Retry`（`:brief-result`）与任务面板的 取消/停止处理/重发确认/续用原副本/从当前版本重建 —— **同一批动作（stop/retry/resume/cancel），两套 UI** | 简报区 3 个动作全部是任务面板的子集 |
| **D3** | **"重新读取产物" 两处同一 handler** | `btnTriRefresh`（对比工具条 `:1015`）与 `btnExpRefresh`（导出栏 `:1078`）**都绑 `triRefresh`**（`:7777-7778`） | 同一动作、同一视图的两个子页签各一份 |
| **D4** | **"打开文件" 两个入口** | 页头 `btnOpen` 与空状态 `btnOpen2` | 空状态是引导性的；未加载时两个同时可见 |
| **D5** | **"产物清单" 两个入口** | 对比工具条的 `btnCmpBack`（"← 产物清单"）与分段控件的 `data-view="artifacts"` | 同一导航两个按钮 |

**不是重复（保留）**：保存(⌘S) 与快捷键 · 三对齐/三对比模式（互斥选项）· 弹窗的取消（各自独立）· "复制指令/发送给 AI"出现两处（设计面板与批注面板，**对象不同**，但见 D6 建议）。

## 3. 建议方案

| # | 建议 | 影响面 | 风险 |
|---|---|---|---|
| **S1** | **删掉页头的 `btnBake`/`btnIllustrate`**，生图入口统一用桥栏那一对（桥栏在轨 A 现在也会显示：`mcpAppRenderState` 会 `show` 它）；同步删 `:8934` 的按形态显隐分支 | 少 2 个按钮 + 少一段形态分支 | 低。唯一前提：桥栏在**所有**形态可见——轨 A 已确认；嵌入/静态态也一直显示（`bridgeParseLaunch` 之外还有 `mcpAppRenderState`/`bridgeRenderState`）。实施前会再核一遍 |
| **S2** | **简报结果区只留一个「查看请求记录」**，删 `btnBriefStop/Resume/Retry`；动作统一在任务面板（含轨 A 的「按当前版本重新提交」）。**前提**：简报视图也要显示桥栏（去掉 `body[data-launch="brief"]>#bridgeBar{display:none}`） | 少 3 个按钮；简报视图多一条 34px 桥栏 | 中。要保证"简报页也有入口"（这正是 1028 修过的坑） |
| **S3** | **合并 D3**：删导出栏的 `btnExpRefresh`，翻转视图统一用工具条上的一个 | 少 1 个 | 低（同一个 handler） |
| **S4** | **合并 D4**：未加载时隐藏页头 `btnOpen`（只留空状态那个）；已加载后恢复 | 无净减，但消除"两个入口同时可见" | 低 |
| **S5** | **合并 D5**：删 `btnCmpBack`，返回统一用分段控件 | 少 1 个 | 低 |
| **S6（可选，属交互统一而非删按钮）** | "复制指令 / 发送给 AI"这一对出现两次（设计面板、批注面板）→ 抽成同一个小组件/同一套样式与文案（对象不同，**不删**） | 不改数量 | 低 |

**净效果**：58 → **51 个**（S1 2 + S2 3 + S3 1 + S5 1），并去掉 1 段按形态显隐的分支。

## 4. 不做

- **不删互为选项的按钮**（三个视图页签、四态对齐、三种对比模式、下载菜单三产物）——它们是**选项**不是重复。
- **不合并"取消"**（三个弹窗各自独立，合并会把模态语义搅在一起）。
- **不动快捷键 ⌘S**。
- 不新增任何按钮。

## 5. 验证方式（实施后）

```
python3 -m pytest tests/harness/test_bridge_core.py -q                 → 50 passed 不变
python3 tests/harness/r_bridge_check.py --group {transport,sdk,apps,http,fault,security,integration}
python3 tests/harness/aa_mcp_apps_check.py                            → ALL PASS（含 P3.1 登记制断言）
python3 tools/build_ext_apps_bundle.py --check                        → OK（版本随 editor.html 头）
```
真宿主人工项：各形态下"生图入口仍在"、"简报页仍有请求记录入口"、"翻转视图仍能重新读取产物"——如实标 NOT_RUN 或手工核。

---

## 6. 实施记录（2026-10-29，S1 + S2）

用户勾选 **S1 + S2**（S3–S5 未做）。

| 项 | 落点 |
|---|---|
| **S1 生图入口合并** | 删掉 markup 里桥栏的 `btnBridgeBake`/`btnBridgeIllustrate`、两处 `.hidden = !state.loaded`（`mcpAppRenderState` / `bridgeRenderState`）、两个 handler；`updateImagegenEntry()` 的显示条件由 `state.loaded && !bridge.enabled` 改为 **`state.loaded`**，并把 title hint 改为按 `hostKindDetect()` 三态给准（此前 Bridge/轨 A 下会错说"复制指令文本"，实际是发意图）。**统一到页头那一对**——页头在四种形态下都可见 |
| **S2 简报区按钮并入面板** | 删掉 markup 的 `btnBriefStop/Resume/Retry` + 对应 CSS 选择器 + 三个 handler + `briefRenderSubmission` 里的按轨显隐分支（含 v3.9.8 刚补的轨 A 分支）；新增 `btnBriefTasks`「**查看请求记录**」——点它 `closeBrief()` 回工作台并展开 `#bridgeTasks` 面板 |

### 6.1 两个实现取舍（值得记）

1. **S1 为什么统一到"页头"而不是"桥栏"**：桥栏只在 **轨 B**（`bridgeParseLaunch`）与 **轨 A**（`mcpAppRenderState`）被 `show`；**静态/嵌入态根本不显示桥栏**。若统一到桥栏，静态/嵌入态就会**失去生图入口**。页头是四种形态都在的地方，所以反过来删桥栏那一对更安全。
2. **S2 为什么不是"让简报视图显示桥栏"**：`#briefOverlay` 在 brief 模式下是 `position:fixed; inset:0; z-index:80` 的整屏层，会盖住桥栏；要露出桥栏得改它的 `inset`/`z-index`（脆弱——桥栏高度随内容变，且 `#bridgeTasks` 是下拉面板还需单独抬层级）。改为**一个按钮把用户送回工作台再展开面板**：效果等价、不碰整屏层布局、风险低。

### 6.2 验证

```
python3 -m pytest tests/harness/test_bridge_core.py -q          → 50 passed（不变）
python3 tests/harness/r_bridge_check.py --group apps            → PASS
python3 tests/harness/aa_mcp_apps_check.py                      → ALL PASS（含 P3.1 登记制断言）
python3 tools/build_ext_apps_bundle.py --check                  → OK（v3.9.9）
build_view_html()                                               → 773480 B（755 KB < 2MB）
```
`editor.html` v3.9.8 → **v3.9.9**；markup 按钮 **58 → 54**。
**真宿主人工项 NOT_RUN**：四种形态下页头生图按钮是否都可见可点；简报页「查看请求记录」跳转后面板是否正常展开、动作是否都能用。

## 7. 未做（S3–S5，用户未勾选）

- **S3**：删导出栏 `btnExpRefresh`（与工具条 `btnTriRefresh` 同一个 `triRefresh`）
- **S4**：未加载时隐藏页头 `btnOpen`（与空状态 `btnOpen2` 双入口）
- **S5**：删 `btnCmpBack`（与分段控件的"产物清单"重复）
