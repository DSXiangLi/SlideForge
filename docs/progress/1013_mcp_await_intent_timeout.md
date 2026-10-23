# 1013 · await_intent MCP 60 秒硬超时导致请求排队无人认领

## 解决结论（2026-10-13 已修复）

**原文"60 秒硬超时不可配置"的判断有误。** 对 Kimi Code 运行时二进制（`~/.kimi-code/bin/kimi`）的静态分析证实，`toolTimeoutMs` 是正式支持的配置项，有三条通道：

1. **per-server**：`mcp.json` 的 server 条目内 `"toolTimeoutMs": <ms>`（`McpServerStdioConfigSchema`，上限 2147483647 ms）
2. **全局**：`config.toml` 的 `[mcp]` 节 `toolTimeoutMs`（`McpSectionSchema`）
3. **环境变量**：`KIMI_MCP_TOOL_TIMEOUT_MS`

同时证实 `buildRequestOptions(timeoutMs, signal)` **不开启** `resetTimeoutOnProgress`，因此 MCP 进度通知无法续期，"bridge_mcp 内部分片 + progress 保活"路线在 Kimi 侧无效；`toolTimeoutMs` 是唯一根治路径。

**已实施的修复**：项目 `.kimi-code/mcp.json` 的 `pptx-html-bridge` 条目增加 `"toolTimeoutMs": 86500000`（覆盖 daemon 侧 86415 秒 HTTP 上限 + 余量）。`docs/howto/editor-agent-bridge.md` 注册示例同步更新。**改动需重启 Kimi 会话生效。**

**同日应用户要求，await 契约上限由 1 小时提升为 1 天**：`bridge_core.py` 的 `AWAIT_TIMEOUT_DEFAULT_SEC`/`AWAIT_TIMEOUT_MAX_SEC` 由 3600 改为 86400，`bridge_mcp.py` 工具描述、SKILL.md（双份）、evals、AGENTS.md、howto、handover、test_acceptance 与 harness（test_bridge_core / r / u / v 四组断言）全部同步。

修复后方向 1（短轮询）与方向 3（工作流降级）均不需要；SKILL.md 的"每回合一次 `await_intent(3600)`"语义恢复成立。daemon 侧代码无需任何改动。

## 问题现象

1. Agent 通过 `open_editor(view="brief")` 打开编辑器，用户在浏览器中完成需求简报并提交（`brief.submitted`）
2. Agent 调用 `await_intent(timeout_sec=3600)` 等待用户后续请求
3. **60 秒后**，MCP 工具调用被 Kimi Code 运行时强制超时，返回 `MCP error -32001: Request timed out`
4. Agent 退出等待状态，此时用户尚未提交任何请求
5. 用户在编辑器中提交了 3 个请求（`illustrate.requested`、`bake.requested`、`convert.requested`）
6. 这 3 个请求成功进入 daemon 的 pending 队列（`pending_count: 3`）
7. **但 Agent 没有在 `await_intent` 等待，无人认领这些请求**
8. 请求一直堆积在队列中，用户在编辑器页面看到请求状态停留在"请求队列"中，没有被发送给 AI

## 问题根因

### 直接原因：Kimi Code 运行时的 MCP 工具调用 60 秒硬超时

`await_intent` MCP 工具的工作方式是长轮询——向 bridge daemon 的 `/api/bridge/await` 端点发起 HTTP 请求，daemon 最长等待 `timeout_sec` 秒（默认 3600 秒）后返回。

但 **Kimi Code 运行时对 MCP 工具调用有一个 60 秒的硬超时限制**，这个限制：

- 不在用户的 `config.toml` 中可配置（检查了 `~/.kimi/config.toml` 和 `~/.kimi-code/config.toml`，无 MCP 超时配置项）
- 不在 `bridge_mcp.py` 代码中（`bridge_mcp.py` 正确地传入了 `timeout_sec=3600`）
- 是 Kimi Code 运行时在 MCP stdio 通信层面强制施加的

### 调用链路

```
Agent 调用 await_intent(timeout_sec=3600)
  → bridge_mcp.py 向 daemon 发起 HTTP POST /api/bridge/await (timeout=3615s)
    → daemon 持有 consumer lease，等待 pending intent（最长 3600s）
      → 60s 后 Kimi Code 运行时强制中断 MCP 工具调用
        → Agent 收到 "MCP error -32001: Request timed out"
          → Agent 退出等待，不再 await_intent
            → 用户后续提交的请求堆积在 pending 队列无人认领
```

### 为什么之前没有暴露这个问题

- 之前的会话中，用户在 `await_intent` 的 60 秒内就提交了 `brief.submitted`（第一次使用时用户已经准备好内容，提交很快）
- 本次的场景是：Agent 在排查 bridge 初始化失败问题期间花费了较长时间，`await_intent` 的 60 秒窗口内用户没有提交请求，timeout 后用户才提交

### 与 SKILL.md 工作流的冲突

SKILL.md 规定：
- "首次打开后的当前 Agent 回合，必须且只能调用一次 `await_intent`"
- "同回合最多调用一次 `await_intent`"
- "timeout 后必须立即向用户说明页面仍可用并结束回合"
- "只有用户发来新的聊天消息要求继续等待时，才在新回合再次 `await_intent`"

这些规则假设 `await_intent` 能够真正等待 3600 秒。在 60 秒硬超时下，Agent 每次只能等 60 秒，timeout 后必须结束回合等用户发消息——这严重破坏了用户体验：用户在编辑器中操作时，Agent 处于不等待状态，提交的请求无人认领。

## 影响范围

- **所有 Bridge 模式下的后续请求**：`brief.submitted` 之后的所有 intent 类型（`design.submitted`、`anno.submitted`、`illustrate.requested`、`bake.requested`、`convert.requested`）都受影响
- **首次 `brief.submitted` 不受影响**：因为 `open_editor(view="brief")` 后用户通常在 60 秒内提交简报
- **多页 bake 的代表页审批流程也受影响**：完成代表页后释放 lease，用户在页面查看后提交剩余页的新 `bake.requested`，此时 Agent 不在等待

## 相关文件

- `tools/bridge_mcp.py`：MCP 薄代理，`await_intent` 工具定义（第 122-127 行），`_request` 方法（第 101 行，`timeout` 参数传给 HTTP 请求）
- `tools/bridge_core.py`：daemon 端 `await_intent` 实现，正确支持长轮询
- `~/.kimi/config.toml`、`~/.kimi-code/config.toml`：用户配置，无 MCP 超时配置项
- `editor.html`：`bridgeSubmitIntent()` 提交 intent 到 daemon，`bridgeRenderTasks()` 显示请求状态——浏览器端行为正常

## 可能的修复方向

### 方向 1：bridge_mcp.py 内部短超时轮询（推荐）

将 `await_intent` 的单次 HTTP 长轮询改为内部自动重试的短轮询循环：

- 每次向 daemon 请求 `timeout_sec=50`（< 60 秒安全线）
- daemon 50 秒内无 intent 则返回 timeout，`bridge_mcp.py` 内部自动重新发起请求
- 对 Agent 透明：Agent 仍调用 `await_intent(timeout_sec=3600)`，`bridge_mcp.py` 内部拆分为多次 50 秒短轮询
- 需要注意：每次短轮询之间 daemon 的 consumer lease 不能断开（heartbeat 机制需验证）

**优点**：不改 Agent 侧代码，不改 SKILL.md 工作流，对 Agent 完全透明
**风险**：50 秒安全线需要实测验证；consumer lease 在短轮询间隔的续期需验证

### 方向 2：Kimi Code 运行时增加 MCP 工具超时配置

在 `config.toml` 中增加 `[mcp] timeout = 3600` 之类的配置项，允许按工具或全局设置 MCP 工具调用的超时时间。

**优点**：根治问题，所有长等待 MCP 工具受益
**缺点**：需要 Kimi Code 运行时侧修改，不在本项目控制范围内

### 方向 3：SKILL.md 工作流适配

调整工作流，接受 60 秒超时为正常行为：

- timeout 后在回复中提示"请发送任意消息让 Agent 继续等待"
- 用户每次在编辑器操作后需要手动发消息触发 Agent 重新 `await_intent`
- 可结合 `pending_count` 检查：Agent 被唤醒后先 `get_status` 检查是否有 pending 请求

**优点**：不需要代码修改
**缺点**：严重破坏用户体验，用户每次操作后都要手动发消息

## 本会话中还修复的两个 bridge_core.py bug

在排查此问题的过程中，还发现并修复了 `bridge_core.py` 中的两个独立 bug（已提交 `dc75288`）：

1. **`_check_host_origin` Firefox POST 请求间歇性 403**：Firefox 的 `setInterval` 定时 `fetch()` POST 不总是携带 `Origin` header，导致写请求被拒。修复：当 Origin 缺失时回退到 Host 检查。

2. **`_static` .pptx-html 路径下资源无法加载**：bundle 工作副本位于 `.pptx-html/jobs/` 下，`normalize_rel` 拒绝含 `.pptx-html` 路径段的请求，导致 HTML 和图片资源全部 403。修复：增加 fallback 路径解析。
