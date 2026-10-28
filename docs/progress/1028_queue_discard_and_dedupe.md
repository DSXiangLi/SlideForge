# 1028 · 队列语义：重开页面丢弃排队请求 + 请求语义去重

> **状态**：**已实施并自测通过（2026-10-28）**；未提交
> **来源**：用户 2026-10-28 反馈——"重新打开编辑器之前的 req 应该都丢弃""重复 request 应该消重，不应该出现多个 convert 的请求"
> **依据**：[1028 状态流修复](1028_editor_state_flow_fixes.md)（可见+可处置）、[1027 P4 状态机止血](1027_p4_state_machine_hemostasis.md)、[1026 一致性规范](../design/editor-agent-bridge-consistency.md)

---

## 1. 现场证据（为什么用户会这么提）

`2026-10-28` 实测该会话队列：

```
seq3 convert.requested conflict  base=a65de62…（旧）   ← agent 认领时判 conflict
seq4 convert.requested conflict  base=a65de62…（旧）
seq5/6/7 convert.requested pending base=a65de62…（旧） ← 迟早同样 conflict
seq8/9 convert.requested pending base=fbc7fd0…（当前） ← 用户点"重新提交"产生的新请求
```

三条事实：
1. **队列里堆着 5 条注定失败的旧请求**（基线已过期），agent 逐条认领 → 逐条变 `conflict`，`recoverable` 长期 ≥1 → `agent_state` 一直 `recovering`；
2. 用户新提交的请求（seq9）**排在 4 条旧的后面**，看起来"点了没用"；
3. 旧请求与新请求**内容完全相同**（都是 `{formats:[pptx,vector,pdf],scope:all}` 的转换）——重复且无意义。

⇒ 用户的两个要求（重开即丢弃、同类去重）都直接对症。

## 2. 决策一：语义去重（daemon `accept_intent`）

**规则**：同一 session 内，**(type, payload 内容, 归一化后的 base_revision) 完全相同**且**尚未终结**（`pending`/`processing`）的请求**不再新建**——直接返回既有那条，响应带 `deduplicated:true` 与既有 `intent_id`/`seq`/`status`。

**为什么 base 也进 key**：`base` 是"针对哪一版内容提的请求"。把 base 纳入 → **"改版后重发"仍是新请求**（这是必须保留的语义）；只有"同一版、同一内容、还没做完"的重复才被吸收。

**与旧口径的差异（刻意变更）**：协议原文写的是「**不同 intent_id 始终是独立持久请求**；服务不根据 payload_digest 或其他启发式自动判断语义重复、合并或取消」。本轮把它改成"同 base 同内容的非终态请求去重"——属**用户签字的语义变更**，已同步协议 §4 与 `AGENTS.md`。
**保留的旧语义**：同 `intent_id` 不同内容仍返回 `IDEMPOTENCY_CONFLICT`（不变）。

**页面侧配合**：`mcpAppSubmitIntent` 收到 `deduplicated:true` 时撤掉本地乐观条目、合并到既有那条，并明说
「队列中已有相同的请求（seq N），未重复提交」——不静默（否则用户以为"点了没反应"）。

## 3. 决策二：**新 View client attach** = 用户重开了页面 → 丢弃先前排队的请求

**范围（刻意排除两类）**：
| 状态 | 处置 | 理由 |
|---|---|---|
| `pending` | **丢弃**（→`cancelled`） | 还没轮到，丢掉零损失 |
| `failed` / `conflict` | **丢弃** | 唯一出路是 `rebuild`（从**当前**版本重跑），而"按当前版本重新提交"与它等价 ⇒ 丢弃不减少可选项 |
| `interrupted` | **保留** | 唯一能 `resume`（复用原工作副本）的状态；协议里"close → 再次 open_editor → resume"是既有且**有测试保护**的路径 |
| `processing` | **保留** | agent 正在处理，取消会半途丢工作 |

**每条都发 `intent-status`（"事事有回响"）+ 一条汇总 `notice{kind:'reopen-discard'}`**，并在 `attach_view` 的返回里给出 `discarded` 列表，便于 agent 如实告知用户（"本次重开作废了 N 条旧请求，请重新提交"）。

### 3.1 为什么触发点是 **attach 的新 client**，而不是 `open_editor`

第一版实现挂在 `open_editor` 上，**被 harness 当场证伪**：

```
r_bridge_check --group integration
  → 该组流程：MCP open_editor → **提交 brief.submitted** → 再 open（换 driver consumer）→ await 认领
  → 报错：claimed.kind == 'timeout'（pending_count=0）——刚提交的请求被"open 即丢弃"吃掉了
```

结论：`open_editor` 在正常流程里会被**多次**调用（换 consumer、恢复会话、驱动脚本接管），拿它当"用户重新打开页面"的信号是错的。

**正确信号**：`attach_view(session_id, client)` 的 `client` **变了**。
- View 在轮询期会用**同一个** `client` 反复上报（工具描述原文："Call immediately after the view is ready, and again while polling"）→ 同 client 不触发；
- 只有**真正的新页面**（重新打开编辑器 / 刷新页面）才会换 `client` → 触发丢弃 ✅。

> 副作用（已知、如实记录）：用户在页面上**刷新**也会被当作"重开"→ 排队请求被丢弃。这与用户口径一致（"重开之前的 req 都丢弃"），且是**可见的**（toast/事件/`discarded`）。

## 4. 改动清单

| 文件 | 改动 |
|---|---|
| `tools/bridge_core.py` | `accept_intent`：新增语义去重分支；新增 `discard_prior_requests()`；`attach_view()`：新 client 时调用它并在返回里带 `discarded` |
| `editor.html`（v3.9.8 ④） | `deduplicated` 响应 → 撤本地条目 + 合并既有 + 明说 |
| `tests/harness/test_bridge_core.py` | +2 用例：`test_duplicate_request_is_deduplicated`、`test_new_view_client_discards_previous_unfinished_requests`（含"同 client 重复上报不丢弃"的负例） |
| 协议 | §4 去重口径变更；`attach_view` 的新语义 |

## 5. 验证

```
python3 -m pytest tests/harness/test_bridge_core.py -q                                    → 50 passed（48 → +2）
python3 tests/harness/r_bridge_check.py --group {transport,sdk,apps,http,fault,security,integration} → 7 组全 PASS
python3 tests/harness/aa_mcp_apps_check.py                                                → ALL PASS
python3 tools/build_ext_apps_bundle.py --check                                            → OK（v3.9.8）
```
**关键回归**：`integration` 组首版挂、改 hook 后 PASS（上面 §3.1 的过程已留下证据）。

## 6. 残余 / 后续

- **`interrupted` 仍会累积**（本轮刻意保留）：它的出口是 resume/rebuild/「按当前版本重新提交」，见 `1028_dual_track_freeze_and_p31.md` §5 的后续项。
- 真宿主人工项 NOT_RUN：真页面上"重开 → 队列清空 → 新提交 → 去重提示"的观感。
- SKILL/agent 侧建议（未改，待确认）：`await_intent`/`get_status` 之后如遇 `discarded`，**如实告知用户**而不是继续让用户去点不存在的按钮。
