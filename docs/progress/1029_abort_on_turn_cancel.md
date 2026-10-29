# 1029 · 用户终止回合 → 在途 MCP 意图转 interrupted（方案 B：不做 hook）

> **状态**：**已实施并自测通过（2026-10-29）**；宿主侧 `tool-cancelled` 通知为独立欠账，未做
> **日期**：2026-10-29
> **来源**：用户——"如果用户点击 ui 按钮触发请求后，AI 执行请求时手动终止对话并发送下一个请求，但是在历史面板里还会存在排队请求，这个终止状态能否反馈给 mcp 就是取消前一次请求呢？…哪个比较合理"；随后选定 **B（不做 hook）** 并要求"去桌面上 mcp-apps 的官方仓库确认下哪种是标准操作"
> **规范依据**：`ext-apps/specification/draft/apps.mdx` §Tool cancelled（原文见 §3）

---

## 1. 问题（现场）

用户在编辑器 UI 上提交一个意图（`convert.requested` / `bake.requested`），模型在回合内 `await_intent` 认领并开始处理。此时用户**手动终止本轮对话**（点停止），然后在同一会话继续提问。

现象：

- daemon 里那条意图**永远停在 `processing`**——任务面板显示"仍在执行/排队"，而实际已经没有人在做。下一轮 AI 调 `get_status` 看到的仍是"有请求在跑"。
- 用户随后收到的那句"已收到你提交的 convert.requested，但被之前中断的 bake.requested 阻塞"就是这条幽灵 `processing` 的直接后果——**状态撒谎**。
- 更隐蔽的副作用：`await_intent` 认领时会挑 **`status='processing' AND consumer_id=?`** 的行重投（redelivery 语义，保护"同一 owner 重挂"）。于是一条**已被用户取消**的意图可能被**下一轮重跑一遍**——转换/烙入有外部副作用（付费生图、文件发布），这是实打实的重复执行风险。

根因：**框架的取消路径完全不碰 MCP 意图**。用户点停止时框架做了 `run_mgr.set_status(interrupted)`、把部分回复写回 checkpoint，但对 MCP 侧那条"我认领了、正在做"的意图**一句话都没说**。全仓 `close_session` **零调用**——连"结束协作"这条路都没走。

## 2. 为什么是设计缺口而非普通 bug

`processing` 的所有权模型（协议 §4）本来就规定"processing 只由 owner 显式动作 / 发布结果 / daemon 重启结束，**绝不因时间经过或心跳丢失自动过期**"。这是为了防"长任务被误判成死了"。代价是：**owner 主动放手时必须显式说**。框架取消路径恰恰是这个"必须说"的位置，而它没说——于是 `processing` 按设计**正确地不死**，只是它守护的那个生产者早没了。

## 3. 规范核实（去官方仓库确认"标准操作"）

用户要求先核实标准做法。读 `~/Desktop/ext-apps/specification/draft/apps.mdx`（Apps SDK 规范草案）：

- **`ui/notifications/tool-cancelled {reason}`**（原文 §Tool cancelled，:1381–1394）：
  > "Host **MUST** send this notification if the tool execution was cancelled, for any reason — including when the user cancels …"
  时序图给出 `alt Tool complete → tool-result / else Tool cancelled → tool-cancelled` 两条互斥分支。
- 结论：**"取消"确实有标准，但它只规范"宿主 → View"这一半**（告诉已渲染的 UI："这次工具调用被取消了"）。规范**不建模** agent 的工作队列 / 意图状态——那是我们 bridge 自己的东西。因此：
  - "把在途意图如实转 `interrupted`"**不与规范冲突**，属于我们用既有协议词汇表达的业务状态；
  - 但**宿主那一半我们没实现**（`mcp_apps_design.md` §10 表 B 里标 🚫，理由写的是"View 只存在于工具完成后"——这条理由**已过时**，本任务之后仍欠账，见 §8）。

## 4. 方案取舍

| 方案 | 做法 | 评价 |
|---|---|---|
| **A** | 加 hook：框架在会话建立时把 bridge `session_id` 记下来，取消时用它 `close_session` | **重**：要新增 hook、要跨模块传递 bridge session id（框架本不掌握它），且 `close_session` 语义是"结束协作"（置 `requires_open`），比"终止这一轮"重得多 |
| **B（选定）** | daemon 侧给 `push_update` 增加 **`abort`** 动作；框架取消路径以 **`consumer_id`**（MCP server 已注入、框架天然持有）调用它，**只需 action** | 复用既有工具面、不新增 hook、语义精确（副本保留、可 resume/rebuild）；代价是 daemon 要支持"无 intent_id/session_id 的宽形态" |
| **C** | 允许用户在面板里手动删掉历史请求 | 该做，但只是兜底——用户不会为每条幽灵请求手动点删；治标。留作后续可选 |

**为何 B 优于 A**：`consumer_id` 是框架在工具调用链里本来就有的稳定标识（MCP server 把它附在每次请求上），而 bridge `session_id`（形如 `s_xxx`）**既不是 harness 的 thread_id，框架也没有任何地方记录它**。走 A 等于为一个附带动作引入一条新的跨模块状态传递链。

## 5. 实现

### 5.1 daemon 侧（`tools/bridge_core.py`）

`push_update` 新增 **`abort`** 动作，语义 **`processing → interrupted`**：

- 工作副本**保留**、`consumer_id`/`lease_until` 清空、`attempt` 同步置 `interrupted`、写 `intent-status` 事件、`_release_owner`；
- 错误码 `AGENT_ABORTED`（`retryable:true`）；
- **不置 `requires_open`**——这正是它与 `close_session` 的关键区别（那是"结束协作"，本方案刻意不用）。

三级宽松形态（从紧到松，逐级复用同一条已校验路径）：

1. `abort` + 完整 `(session_id, intent_id, attempt)`：等价于其它动作的严格形态；
2. `abort` **省略 `intent_id`**（`idless_abort`）：= "释放本 consumer 当前在途意图"；该形态**豁免 attempt 校验**，也无在途时如实抛 `RECOVERY_REQUIRED`；
3. `abort` **连 `session_id` 也省略**（最终形态，框架走这条）：按 `consumer_id` 反查 `consumers` 表得到会话，逐会话递归；某会话无在途（`RECOVERY_REQUIRED`）跳过，全无则报错；未登记 consumer → `SESSION_NOT_FOUND`。

校验放宽（`bridge_core.py`）：`idless_abort = action=="abort" and intent_id is None`；`{"progress","fail","abort"}` **不接受** `validation`。

路由 `/api/bridge/update`：required 从 `{session_id,intent_id,attempt,consumer_id,action}` 改为 **`{consumer_id, action}`**，其余转 optional（向后兼容：老调用照带全字段仍然工作）。

工具签名（`tools/bridge_mcp.py`）**重排**为：

```python
push_update(action, session_id=None, intent_id=None, attempt=None, message="", validation=None)
```

（可选参数必须排在 `action` 之后，否则 `SyntaxError`——这条踩过一次，记此。）`Literal` 加上 `"abort"`，`Field(description=...)` 说明何时用、以及"可省 session_id/intent_id"的宽形态。

### 5.2 框架侧（`src/sprout_harness/agent/handlers.py`）

新增模块级 `async def _abort_inflight_intents(configurable, rid)`：

- 从 `configurable["registry"]` 取 `push_update` 条目（与 `tool_node` 里 `registry.get("present_files")` 同一路径；MCP 工具按**裸名**注册，`registry.get("push_update")` 命中）；
- `await entry.instance.invoke_coroutine(action="abort", message="用户终止了本轮对话")`；
- **best-effort**：任何失败只 `_diag.warning`，绝不阻塞取消路径。

两处调用（取消路径的两个真实分支）：

- `elif record.abort_event.is_set():` 分支（`set_status(interrupted)` 之后）——`agent_node` 可能吞掉 `CancelledError`（3.11+ `uncancel`），此时靠 `abort_event` 判定；
- `except asyncio.CancelledError:` 分支（同样在 `set_status(interrupted)` 之后）。

成功时 `_diag.info("[run_agent] aborted in-flight MCP intents: run_id=%s")`，便于线上取证。

## 6. 与队列语义的关系（1028）

本方案与 [1028 队列语义](1028_queue_discard_and_dedupe.md) 是**互补**的两件事，不要混淆：

| | 触发 | 作用 |
|---|---|---|
| **`abort`**（本文件） | 用户**终止本轮对话** | 把**在途的** `processing` 如实转 `interrupted`（副本保留、可 resume/rebuild） |
| **重开丢弃**（1028） | `attach_view` 的 **client 变了**（页面重开） | 丢弃该会话的 `pending`/`failed`/`conflict`，**保留 `interrupted` 与 `processing`** |

注意 1028 的"重开丢弃"**刻意保留 `interrupted`**（那是唯一能 resume 的入口）——所以 `abort` 产生的 `interrupted` 在用户重开页面后**仍在**，用户可显式 resume 或 rebuild，这正是想要的（用户没放弃，只是这一轮停了）。二者叠加后，"幽灵 `processing`"的两个来源（用户停回合 / 页面其实关了）都被如实收敛，而**用户真正想保留的恢复线索不丢**。

## 7. 验证

- `python3 -m pytest tests/harness/test_bridge_core.py -q` → **53 passed**（原 50，新增 3：`test_push_update_abort_interrupts_and_releases_owner`、`test_abort_without_intent_id_releases_current_inflight`、`test_abort_without_session_or_intent_resolves_from_consumer`）。
- `r_bridge_check --group sdk / apps / integration` 全 PASS（路由 required 变更未破坏既有调用方）。
- `aa_mcp_apps_check.py` **ALL PASS**（工具面/UI 面纪律未被破坏）。
- `build_ext_apps_bundle.py --check` **OK**（View bundle 与版本单源一致）。
- 框架侧：`PYTHONPATH=src pytest tests/test_cancel_checkpoint_persistence.py tests/test_run_manager.py tests/test_reconnect_new_request.py -q` → **23 passed**。

**人工项 NOT_RUN（如实标注）**：真宿主端到端"用户点停止 → daemon 意图真的变 `interrupted`"未在本机自动跑通；若需确认：页面上提交一个请求 → AI 执行时点停止 → 查 `<workdir>/.pptx-html/bridge.sqlite3` 的 `intents.status`，或看 agent 日志 `[run_agent] aborted in-flight MCP intents: run_id=…`。

**已知薄弱点**：`_abort_inflight_intents` 的 `registry.get("push_update")` 取不到时**静默 return**（无日志）。对"没装 pptx bridge 的 agent"这是正确 no-op，但若"装了却因键名变化取不到"则会无声失效——若后续出现，给该分支补一条 `debug/warning`。

## 8. 未做 / 后续

- **宿主侧 `ui/notifications/tool-cancelled`**（规范 **MUST**，独立欠账）：取消时宿主应告知 View "这次工具调用被取消了"。`mcp_apps_design.md` §10 表 B 现标 🚫 且理由（"View 只存在于工具完成后"）**已过时**，需重评后实施。**独立于本任务**，待用户确认再动。
- **手动删除历史请求（方案 C）**：仍是想做的兜底项，可作后续小迭代。
- **不做**："用户发下一条消息就自动清 `processing`"——会误杀正常长任务（模型可能正等着在下一回合继续），明确不采纳。

## 9. 文件清单

**pptx 仓库**：

- `tools/bridge_core.py`（`abort` 动作 + 三级宽形态 + 路由 required 放宽）
- `tools/bridge_mcp.py`（`push_update` 签名重排 + `abort` + 描述）
- `tests/harness/test_bridge_core.py`（+3 用例）
- `docs/design/editor-agent-bridge-protocol.md`（§4 动作绑定、§5.3 输入表 `action`/`validation` 行与语义段）
- 本文件 + `docs/progress/README.md` 索引
- `AGENTS.md`（Bridge 操作红线补 abort 语义；该文件被 gitignore，不入提交）

**框架仓库**（worktree `feature+mcp-apps`）：

- `src/sprout_harness/agent/handlers.py`（`_abort_inflight_intents` + 两处调用）
