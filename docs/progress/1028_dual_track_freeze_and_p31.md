# 1028 · 双轨收敛第一步：策略面收敛（P3.1）+ 轨 B 冻结

> **状态**：**已实施并自测通过（2026-10-28）**；未提交
> **日期**：2026-10-28
> **依据**：[2026-10-27 系统复盘](../review/2026-10-27_pptx_html_mcp_system_audit.md)（S1/§5 P0-3、P1-4）· [1027 标准化计划](1027_mcp_apps_standardization.md)（P3.1）· [1027 交接](1027_mcp_apps_standardization_handover.md)（决策账 D1–D4、Q1–Q3）
> **触发**：用户提出"**直接删除轨 B、只保留轨 A**，当前很多问题都是双轨带来的"。

---

## 1. 结论：不删轨 B，改为「收敛 + 冻结」

用户的动机成立（分叉与维护成本真实存在），但**删除轨 B 不能修掉这几天真正的痛点**，还会破坏"目标本身"。逐条如下。

### 1.1 哪些问题**真是**双轨造成的（删掉会消失）

| 问题 | 证据 |
|---|---|
| 某态下"点了没用"（`convertDeck` 误走 postMessage、批注路径分叉） | S1：`bridgeFetch(` 15 处 / `mcpAppCall(` 9 处在共享 UI，只有 8 处走策略面 |
| 恢复族按钮在轨 A 必然失败 | 那些按钮走 `bridgeFetch`，需 `bridge.token`，只有轨 B 设置过 |
| 保存/资产/版本/回滚/下载 各实现两遍 | 四态各自实现同一批能力 |
| 浏览器凭证失效 / 端口变化 / SSE 断连 | 只服务轨 B 的自建机械（tokens/SSE/heartbeat/bootstrap） |

### 1.2 哪些问题**不是**双轨造成的（删掉也修不了）

| 问题 | 真正原因 | 状态 |
|---|---|---|
| 一条卡死意图锁死整个会话 | 状态机缺"放弃"出口 + 全局门（S2），**daemon 侧** | ✅ 已由 P4（2026-10-27）修 |
| AI 有排队请求、页面"请求记录"为空 | **轨 A 自己**没有意图列表通道 | ✅ 已由 R3-a（2026-10-28）修 |
| 保存后旧请求变 `conflict` | CAS 的设计结果 | 非缺陷 |
| `conflict` 不自愈 | 用户判据（冲突必须用户决定） | 决策 |

### 1.3 删除轨 B 的三处硬代价

1. **编辑能力会大面积丢失（最关键）**：轨 A 能否编辑**取决于宿主沙箱策略**——官方规范默认 opaque origin，此时 `editor.html:4248` 明确报"处于不透明源…无法编辑"。我们自己的配置之所以能编辑，是因为 `config_work.yaml` 开了 `mcp.apps.allow_same_origin: true`（**仓库默认 false**）。轨 B 是**独立顶层窗口，永远可编辑**。⇒ 删轨 B ⇒ 在"所有支持 MCP Apps 的框架"里**多数只剩不可编辑的编辑器**，与用户目标相反。
2. **轨 A 今天还缺三项能力**（审计 §4 矩阵）：**恢复族**（取消/停止/重试）、**产物直链下载**（轨 A 只走 `read_bundle_file`）、**本地文件编辑**（轨 A 被"本地画布守卫"拒绝）。删之前必须先补齐。
3. **工作量与既有决策**：daemon **不会消失**（轨 A 也用它做状态机/CAS/Git/publication journal），要删的是 daemon 的浏览器面 + `edit.py` 独立模式 + `editor.html` 四态→两态 + `r_bridge_check`(1122 行)/`run_e2e`(62 项) 的重写；且项目自己的 **1027 不做清单**已写明「**不**删除 static/embedded/bridge 三态（它们是分发形态，不是历史包袱）」。

### 1.4 采纳的次序（用户已确认）

1. **收敛策略面（P3.1）** ← 本轮
2. **冻结轨 B**（maintenance-only）← 本轮
3. 给轨 A 补齐 §1.3-2 的三缺口 + 独立 sandbox origin（**后续**，其中 origin 属宿主能力，需框架侧配合）
4. 到那时再评估是否删除（那时删的是"没人用的机械"，风险完全不同）

> 另注：**宿主今天还没按规范声明 MCP Apps 扩展**（1027 的 P1.1 未开工，现靠非标 `PPTX_HTML_APPS_TOOLS=always`）。想让工具"在所有支持 mcp-app 的框架里可用"，**先把宿主声明做对**比删轨 B 更靠前提。

## 2. 本轮改动一：策略面收敛（P3.1）

**新增唯一入口**：`hostBridge.recover(op, x, mode?)`，`op ∈ cancel | stop | retry | resend | list`

| 形态 | 实现 |
|---|---|
| 轨 B（`bridgeHost.recover`） | 既有 HTTP：`bridgeCancelIntent` / `bridgeStopIntent` / `bridgeRetryIntent(x, mode)` / `bridgeResendIntent` / `bridgeRecoverIntents` |
| 轨 A（`mcpAppHost.recover`） | 只有 `list`（读 `get_status` 轻量摘要）与 `retry`（= **按当前版本重新提交**，结果等价于 rebuild、不扩工具面）；其余**明确拒绝**并给指引 |
| 嵌入 / 静态（门面默认分支） | **明确拒绝**（"当前形态不支持意图恢复：请在轨 B 或独立窗口处理"） |

**改走的三个共享 UI 调用者**（此前直接点名 `bridge*`，是"某态下点了没用"的成因）：

| 调用者 | 原 | 现 |
|---|---|---|
| `bridgeRenderTasks`（任务面板 4 按钮） | `bridgeCancelIntent/bridgeStopIntent/bridgeResendIntent/bridgeRetryIntent` | `hostBridge.recover(...)` |
| 简报区 `btnBriefRetry/Resume/Stop` | 同上 | `hostBridge.recover(...)` |
| `openBrief`（状态刷新） | `bridgeFetch('/api/bridge/status')` | `hostBridge.status()` |

**收敛前后核实**（脚本按"调用方是否为轨专属代码"分类）：
- 跨轨（任何形态都会跑到的）共享 UI 里直连轨专属函数：**3 处 → 0 处**；
- 残留 18 处"直连"**全部位于轨专属代码路径内**（`mcpApp*` 函数只在轨 A 跑；`bridge*` 的互相调用只在 `bridgeInitialise` / `bridgeApplyEvent` / `bridgeHandleDeckChanged` 等轨 B 路径）——合法，不再收敛。

> 保留的两处按轨门控（`:7084-7086`、`bridgeRenderTasks` 的 `if(!trackA…)`）**不撤**：那是 1027 的 UX 决策（轨 A 不展示在轨 A 必然失败的按钮）；策略面解决的是"通道正确性"，门解决的是"不要给出死按钮"。两者叠加。

## 3. 本轮改动二：轨 B 冻结（maintenance-only）

**冻结含义**：轨 B（独立浏览器窗口 / daemon 的浏览器面）只接受 **bug 修复与安全修复**，不再接受新能力。

| | 规则 |
|---|---|
| ✅ 允许 | 正确性/安全修复（如本轮 P4 的状态机止血、凭证与沙箱修复） |
| ❌ 不允许 | 新增按钮/能力/协议路由；把新能力只做在轨 B；为轨 B 新增只在轨 B 有效的 UI |
| 新增能力一律 | **只做轨 A**（并在 SKILL/设计文档里写清轨 A 的可用前提） |
| 例外通道 | 若确需在轨 B 加能力，需用户明确签字，并同步本文件与 `AGENTS.md` |

**落地位置**：`AGENTS.md`「Bridge 操作红线」段已加冻结条目；`editor.html` v3.9.7 变更记录 ⑦ 记了本次收敛。

## 4. 验证

```
python3 -m pytest tests/harness/test_bridge_core.py -q                                    → 48 passed
python3 tests/harness/r_bridge_check.py --group {transport,sdk,apps,http,fault,security,integration} → 7 组全 PASS
python3 tests/harness/aa_mcp_apps_check.py                                                → ALL PASS
python3 tools/build_ext_apps_bundle.py --check                                            → OK（bundle 未变：SDK+facade；本轮改的是 editor.html）
build_view_html()                                                                          → 769914 B（752 KB，< 2 MB）
```
**真宿主人工项仍 NOT_RUN**：任务面板按钮在轨 B 的实点、轨 A 的"按当前版本重新提交"实点。

## 5. 未做 / 后续（按 §1.4 次序）

| # | 项 | 归属 | 说明 |
|---|---|---|---|
| 1 | **P3.3 登记制静态断言** | 本仓库 | 把"共享 UI 直连轨专属函数"做成 harness 断言，防收敛回潮（审计 P1-4；"唯一能一次挡住一整类"的东西） |
| 2 | 轨 A 补**恢复族**（取消/停止） | 本仓库 | 需 app-only 工具或 daemon 路由；**需破红线签字**（本轮用"重新提交"绕开） |
| 3 | 轨 A 补**产物直链下载** | 本仓库 + 宿主 | 现在走 `read_bundle_file(export/…)` 的降级 |
| 4 | 轨 A 的**本地画布** | 本仓库 | 现被守卫拒绝（只能下载副本/独立窗口） |
| 5 | **独立 sandbox origin** | 宿主（框架侧） | 决定轨 A 能否在规范宿主里编辑；是"删轨 B"的真前提 |
| 6 | 宿主声明 MCP Apps 扩展（P1.1） | 框架侧 | 现依赖非标 `PPTX_HTML_APPS_TOOLS=always` |
