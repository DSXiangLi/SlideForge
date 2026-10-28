# 1027 · MCP Apps 标准化 + 四态收敛（计划与进度）

> **日期**：2026-10-27
> **触发**：用户提问「为什么琐碎问题一个接一个」→ 系统复盘（`docs/review/2026-10-27_pptx_html_mcp_system_audit.md`）→ 用户批准「按你的来」，并明确「在使用标准 MCP Apps 标准协议的基础上，全局优化编辑器的完整功能」。
> **本文定位**：计划与进度记录（为什么做/做成什么样/分几阶段/验收口径）。
> **动手前请先读**：[`1027_mcp_apps_standardization_handover.md`](1027_mcp_apps_standardization_handover.md)（实施交接：仓库安全须知、任务清单、第一件事）。
> **证据纪律**：本文引用的现状全部来自本机实测（文件:行、命令输出）；**未跑就是 NOT_RUN**，不得记 PASS。

---

## 1. 为什么做：三条结构原因

完整证据见审计文，摘要：

| # | 结构 | 量化证据 |
|---|---|---|
| **S1** | 三层并存、策略面被绕过：`hostBridge`（11 能力 × 4 态）本该唯一入口，但 `bridge*`（轨 B）与 `mcpApp*`（轨 A）两族函数住在**共享 UI 代码**里被按钮直接调用 | `bridgeFetch(` 19 处 → 仅 4 处在 `bridgeHost` 内；`mcpAppCall(` 15 处 → 仅 6 处在 `mcpAppHost` 内；`hostBridge.<能力>()` 分派仅 **8** 处 |
| **S2** | 意图状态机没有"放弃"出口，却有一道全局门 | `await_intent` 遇任一 `failed/conflict/interrupted` 即拒（`tools/bridge_core.py:1105`）；`cancel_intent` 对 `interrupted` 是 **no-op**（`:1322` 尾部分支）；`resume` 要求旧基线未漂移（`:1280` 起） |
| **S3** | daemon 重启是常态，且每次都制造 S2 的燃料 | 启动时把 `processing` 全改 `interrupted`（`:585`，仅 `brief.submitted` 例外 → `cancelled` `:581`）；`run_local.py` 起服务即杀 daemon |

**一个反直觉的结论**：客户端**本来就是标准 SDK**——`tools/ext_apps_facade.js:11` 是 `new App({...})`，用的是官方 `callServerTool` / `sendMessage` / `updateModelContext` / `downloadFile` / `sendSizeChanged` / `getHostContext` / `sendHostCapabilities`，握手走标准 `PostMessageTransport(window.parent, window.parent)`（`:192`）。
所以**不需要重写客户端、不需要框架、不需要给 View 引入构建步骤**。不标准的地方只有三处（§3）。

---

## 2. 用户批准的范围（2026-10-27）

用户原话：「我认为都可以按你的来」——据此，以下三处**破红线**项获授权：

1. **宿主侧声明 MCP Apps 扩展**（改 SproutHarness 框架：MCP 客户端能力声明）。
2. **删掉 `PPTX_HTML_APPS_TOOLS=always` 与"列举期双模"**（改写 `AGENTS.md` 里对应红线措辞）。
3. **允许 View 在 CSP 声明下直接 HTTP 取资产/文档**（推翻"资产一律经工具 base64"的既有决策）。

**同时授权**审计中的止血项：`cancel` 支持 `interrupted`、陈旧中断自愈、门改 per-intent。

> 授权范围**不包含** §8「不做清单」中的任何一项。实施时若发现必须越界，**停下来问用户**。

---

## 3. 目标形态：标准协议对齐清单

| 能力 | 标准做法 | 现状 | 目标 | 阶段 |
|---|---|---|---|---|
| 客户端 SDK | `App` + 标准 handlers + `PostMessageTransport` | ✅ 已符合 | 保持 | — |
| 宿主能力握手 | `initialize.capabilities.extensions["io.modelcontextprotocol/ui"]` + `mimeTypes` | ❌ 宿主零声明 → 用 `PPTX_HTML_APPS_TOOLS=always` 绕 | 宿主声明；删掉 always 与双模 | P1 |
| app-only 工具 | `_meta.ui.visibility:["app"]` | ✅ 服务端已写；宿主已按 `bind_to_llm=False` 过滤 | 保持 | — |
| 资源与 UI | 资源 `ui://…` + 工具 `_meta.ui.resourceUri` | ✅ | 保持 | — |
| **CSP** | `_meta.ui.csp.resourceDomains`（写在 **contents** 的 meta 里） | ❌ 全仓零命中 → 资产 base64 穿工具结果（View 740KB / deck 518KB） | 声明 CSP，资产转 HTTP；保留回退开关 | P2 |
| **稳定源** | `_meta.ui.domain` | ❌ 依赖 `allow-same-origin`（设计 §10.10 自认偏离） | 用 `ui.domain`，沙箱回隔离态 | P2 |
| 宿主主题/字体 | `applyHostStyleVariables` / `applyDocumentTheme` | ⚠️ 编辑器自带 chrome（`prefersBorder:false`），未接宿主变量 | 可选：接入宿主变量做视觉融合 | P2（可砍） |
| 尺寸与两阶段拆卸 | `sendSizeChanged` / `onteardown` | ✅ 已实现（`hostViewportMaxHeight`、teardown flush 草稿） | 保持 | — |
| 模型交互 | `updateModelContext`（便条）/ `sendMessage`（敲门） | ✅ 已实现 | 保持 | — |
| 视图状态 | `viewUUID` / 状态恢复 | ⚠️ 未用；改用服务端 `save_draft`（沙箱无 localStorage） | **不迁移**（save_draft 已工作，迁了无收益） | 不做 |

---

## 4. 阶段与任务（每阶段可独立验收、可随时停）

### P1 · 宿主合规（改框架，不改编辑器）
- **目标**：宿主声明扩展，`always` 与"列举期双模"退场。
- **改动面**：`SproutHarness/.claude/worktrees/feature+mcp-apps` 的 `src/sprout_harness/mcp/client.py:78 get_mcp_tools()`（客户端经 `langchain_mcp_adapters` 建会话，需在会话初始化处注入 `extensions`）；`apps/sale_pptx_agent/config_work.yaml:60` 去掉 `PPTX_HTML_APPS_TOOLS`；`tools/bridge_mcp.py:318-335`（`apps_tools_listed`）与 `:448-473`（`mode_hint`）随之简化。
- **关键前提（已实测）**：本地 `mcp` 包 `ClientCapabilities.model_config.extra == "allow"` ⇒ **不需要改 SDK 源码**，只需让 `initialize` 发出的 capabilities 带上 `extensions`。
- **验收**：`bridge_mcp.BridgeFastMCP.apps_declared()` 为真（不依赖环境变量）；`r_bridge_check --group apps` 的"未声明扩展 → 恰好五个"断言改写为"声明即全量"；`aa_mcp_apps_check` 全绿。
- **回退**：`always` 是行为开关，保留代码分支一段时间即可即时回退。

### P2 · CSP 与稳定源
- **目标**：资产/文档不再穿工具结果；沙箱回到隔离态。
- **改动面**：`tools/bridge_mcp.py:581-594`（资源装饰器的 `meta` 加 `ui.csp.resourceDomains`——**已实测** `FastMCP.read_resource` 会把 `resource.meta` 透传到 contents，无需改 SDK）；`editor.html:4288`/`:4378`（`mcpAppHydrateImage`/`mcpAppHydrateCss` 转 HTTP + 保留 base64 回退）；宿主侧 `webui.html` 的 CSP 注入点；`tools/bridge_mcp.py` 的 `read_bundle_file` 资产分支下线（保留 `export/`）。
- **验收**：在不给 `allow-same-origin` 的沙箱下资产仍渲染（`aa_mcp_apps_check` 新增一臂）；`build_view_html()` 的外链断言不破（CSP 是宿主注入，不是 HTML 外链）。
- **风险**：全计划最容易翻车的一步（CSP / `ui.domain` / allow-same-origin 三者关系）。**必须留开关**。

### P3 · 三层收敛（治 S1）
- **目标**：共享 UI 不再直连通道；新增控件不再"到处都显示"。
- **改动面**：把共享 UI 里的 15 处 `bridgeFetch` / 9 处 `mcpAppCall` 收敛到 `hostBridge` 策略面（先做 intent/status/draft/load/export 五能力）；入库**登记制静态断言**（未登记的直连调用点即失败，空 catch 允许表并入同一检查）。
- **验收**：断言先对**改动前的树失败**（变异测试证明非恒真），修复后通过；`editor.html` 的 54 个绑定逐个过一遍通道归属表。
- **注意**：这是"不再一个个蹦"的正解，但也是改动面最大的一步；建议在 P1/P2 完成后做。

### P4 · 状态机止血（治 S2/S3）—— ✅ 已实施 2026-10-27
- **P4.1** ✅ `cancel_intent` 支持 `interrupted`（**再取消 = 放弃** → `cancelled`，`external_work_may_continue:true`）。
- **P4.2** ✅ 陈旧自愈：**无 lease 且超过 `STALE_RECOVERY_GRACE_SEC`（600s）** 的 `interrupted`/`failed` → `cancelled` + 发 `intent-status` 事件。实现在新增 `BridgeCore._heal_stale_recoverables()`，由 `_invalidate_previous_instance()`（daemon 启动）与 `_acquire_owner()`（每次认领前）调用；**`conflict` 不自愈**。
- **P4.3** ✅ 门改 per-intent：**移除**会话级门——认领循环只挑 `pending` 行，一条 recoverable 自身不是 `pending`、天然不可认领。
- **验收**：✅ `python3 -m pytest tests/harness/test_bridge_core.py -q` → **47 passed**（基线 44 + 3 新用例）；变异测试证明 4 条相关用例在改动前**全部失败**；`r_bridge_check` 7 组 + `aa_mcp_apps_check` ALL PASS。
- **语义变更**：具体判据已由用户 2026-10-27 确认（"按建议默认"：无 lease 且 >10 分钟；`conflict` 仍须用户决定）。详见 [1027 P4 状态机止血](1027_p4_state_machine_hemostasis.md)。

---

## 5. 验收标准：「完整功能」的定义

把审计的「操作路径 × 四态」矩阵做到 **全 ✅ 或显式声明降级**，不允许"控件可见但通道不可用"：

| 路径 | static | embedded | bridge | mcpApp |
|---|---|---|---|---|
| 打开/换图 | ✅ | ✅ | ✅ | ✅ |
| 保存 | ✅ | ✅ | ✅ | ✅ |
| 脑暴/设计/批注 | ✅(复制) | ✅(PM) | ✅ | ✅ |
| 转换/烙入/插画 | ✅(复制) | ✅(PM) | ✅ | ✅ |
| 状态回执 | n/a | n/a | ✅(SSE) | ✅(轮询) |
| 版本/回滚 | n/a | n/a | ✅ | ✅ |
| 产物下载 | ✅ | ✅ | ✅ | ✅（P2 后从"降级"升级为可用） |
| **意图恢复（取消/停止/重试）** | n/a | n/a | ✅ | **P3/P4 补齐** |

---

## 6. 风险登记

| # | 风险 | 缓解 |
|---|---|---|
| R1 | P2 的 CSP/domain 与 `allow-same-origin` 相互纠缠，改坏后轨 A 完全不可编辑 | 分两步、留开关、每步跑 `aa_mcp_apps_check` |
| R2 | P1 依赖 langchain_mcp_adapters 的内部会话创建，SDK 升级可能失效 | 注入点集中在 `mcp/client.py` 一处 + 加断言测试 |
| R3 | P3 触碰 8979 行的 `editor.html`，回归面大 | 只做"通道归属"替换，不动 DOM/交互；每步跑 r/aa/e2e |
| R4 | P4 改状态机语义，可能影响 durable-processing 既有不变量 | 先补测试再改；与 `test_bridge_core.py` 44 项基线逐项对齐 |
| R5 | 本机唯一真实宿主是 SproutHarness（自研）；Kimi Code 不声明任何扩展 | 标准路径只在 SproutHarness + 官方 basic-host 上验证；**basic-host 只代表协议，不代表真实宿主行为** |

---

## 7. 当前状态

| 阶段 | 状态 |
|---|---|
| 先行动作：系统复盘（审计文） | ✅ 已完成 |
| 先行动作：工具面精简 18 → 14（`1027_tool_surface_slimming.md`） | ✅ 已完成并验收 |
| P1 宿主合规 | ⬜ 未开始 |
| P2 CSP / 稳定源 | ⬜ 未开始 |
| P3 三层收敛 | ⬜ 未开始 |
| P4 状态机止血 | ✅ 已完成 2026-10-27（[1027 P4 状态机止血](1027_p4_state_machine_hemostasis.md)；线上卡死意图 `35fbd594…` 由 P4.2 自愈解除，无需改 DB） |

---

## 8. 不做清单（简化门裁决）

- **不**重写编辑器的 DOM/交互层；**不**引入 React/Vue 等框架。
- **不**为 View 引入前端构建步骤（继续用 `tools/build_ext_apps_bundle.py` 的 Python 构建器）。
- **不**删除 static / embedded / bridge 三态（它们是分发形态，不是历史包袱）。
- **不**做 `viewUUID` 迁移（`save_draft` 已工作）。
- **不**做 deck 资源分片（CSP 到位后直连 HTTP 更简单）。
- **不**统一状态枚举（无缺陷可归因）。
- **不**引入 JS lint 工具链（破"零构建"红线）；空 catch 用登记表约束，并入 P3 的同一条检查。
- **不**为轨 A 新增恢复工具**除非** P3/P4 证明仍不够（届时只加**一个**）。
