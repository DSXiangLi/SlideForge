# 1027 — P4 状态机止血（"放弃"出口 + 陈旧自愈 + per-intent 门）

> 状态：**已实施并自测通过**；**未提交**（等用户确认文件清单与 commit message）
> 日期：2026-10-27
> 依据：`docs/review/2026-10-27_pptx_html_mcp_system_audit.md`（S2、§4）、`docs/progress/1027_mcp_apps_standardization.md`（P4）、`docs/progress/1027_mcp_apps_standardization_handover.md`（P4 任务 + 决策账 D4 / Q1 / Q3）
> 单源契约：[`docs/design/editor-agent-bridge-protocol.md`](../design/editor-agent-bridge-protocol.md) §3.2 / §4 / §6.2 / §7.5（本轮已同步）

---

## 一、问题（审计 S2 根因）

审计原话：**"意图状态机没有『放弃』出口，却有一道全局门。"** 三条代码事实：

1. **全局门**：`_acquire_owner` 在会话内存在任一 `failed/conflict/interrupted` 时对**整个会话**抛 `RECOVERY_REQUIRED`——一条卡住的请求锁死同会话的**所有**请求。实测：一条 10-27 的 `bake.requested` 把会话堵了 9 小时，其后 5 条 `convert.requested` 永远停在 `pending`。
2. **没有放弃出口**：`cancel_intent` 对 `interrupted` 是 **no-op** → 既不能取消、也无法让状态机前进（"关闭重开也清不掉"不是错觉）。
3. **`resume` 常被基线漂移挡掉**（handover 坑 #3）→ 只剩 `rebuild`（重跑，可能计费）。

## 二、改了什么（用户 2026-10-27 批准 D4，判据按"建议默认"）

| 项 | 位置 | 改动 |
|----|------|------|
| **P4.1 放弃出口** | `tools/bridge_core.py::cancel_intent` | `interrupted` 再取消 → `cancelled`（清 owner/lease、attempt 同步置 `cancelled`、写 `intent-status` 事件），返回 `external_work_may_continue:true`（放弃**不终止**可能仍在跑的外部进程，风险提示与 interrupted 一致） |
| **P4.2 陈旧自愈** | 新增 `BridgeCore._heal_stale_recoverables()`，在 `_invalidate_previous_instance()`（daemon 启动）与 `_acquire_owner()`（每次认领前）调用 | 判据 = **无 lease 且 `updated_at` 早于宽限期** 的 `interrupted`/`failed` → `cancelled` + `intent-status` 事件（"事事有回响"）。`conflict` **不自愈**；同时刷新 `sessions.agent_state` 持久投影（作废后若无 recoverable 则不再是 `recovering`） |
| **P4.3 per-intent 门** | `tools/bridge_core.py::_acquire_owner` | 移除会话级 `RECOVERY_REQUIRED` 门。认领循环只挑 `pending` 行，一条 recoverable 请求自身不是 `pending`、天然不可认领；其它 `pending` 正常走 |
| **常量** | `tools/bridge_core.py` | 新增 `STALE_RECOVERY_GRACE_SEC = 600`（10 分钟，用户确认"按建议默认"） |

**有意保留（未改）**：`conflict` 仍必须由用户在页面上决定 rebuild/resume；`SESSION_BUSY`、consumer `open` 登记闸门、`pending` 的 90 秒 waiting lease、processing 的持久 owner 语义、publication/journal 恢复路径。

## 三、验证（改动前失败 / 改动后通过）

- `python3 -m pytest tests/harness/test_bridge_core.py -q` → **47 passed**（基线 44 + 3 新用例；另有 1 条既有用例按新语义更新）。
- **RED 自证（变异测试）**：把 `tools/bridge_core.py` 换回 `HEAD` 版本后，4 条相关用例**全部失败**——`test_per_intent_gate_*` 被全局门拒、`test_stale_*` 因无 `_heal_stale_recoverables` 报 AttributeError、`test_processing_cancel_*` 因旧"再取消=no-op"语义不符；恢复实现后全绿。
- `python3 tests/harness/r_bridge_check.py --group {transport,sdk,apps,http,fault,security,integration}` → **7 组全 PASS**（`ui` 组为既有红，未跑）。
- `python3 tests/harness/aa_mcp_apps_check.py` → **ALL PASS**。

## 四、对线上卡死会话的效果（Q3：等自愈）

那条 `bake.requested`（`interrupted`，基线已漂移）在新代码下会在以下任一时刻被 **P4.2 自愈**为 `cancelled`：下一次 daemon 启动，或下一次 `await_intent` 认领前。此后排队的 5 条 `convert.requested` 可按 **P4.3** 正常认领——**无需改 DB、无需用户操作**。

## 五、残余（本轮不做）

- **轨 A 仍无恢复通道（P3.2 未做）**：P4 之后轨 A 不再"因一条 recoverable 而整个会话不可工作"，但轨 A 内仍没有 rebuild/resume 的按钮与通道；陈旧项由 P4.2 自愈，其余需在轨 B / 独立窗口处理。
- **`ext_apps_bundle`**：本轮未改 `editor.html`，无需重建 bundle。
- 真宿主人工项仍 **NOT_RUN**；未跑 `r_bridge_check --group ui`（既有红）。
