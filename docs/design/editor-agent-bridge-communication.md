# Agent、MCP、Bridge 与 HTML 编辑器通信架构

> 状态：已实施通信导览，适用于 `editor.html` v3.5、`tools/edit.py` v2、`tools/bridge_core.py`、`tools/bridge_mcp.py` 与 `protocol_version: 2`。
>
> 本文解释四个运行主体如何建立连接、传递用户意图、执行长任务、发布作品并在断线后恢复，帮助读者形成端到端通信视图；它不是精确协议的单一真相。字段、路由、状态和错误码的单一真相是 [`editor-agent-bridge-protocol.md`](editor-agent-bridge-protocol.md)，CAS、publication journal、路径、凭证和安全边界的单一真相是 [`editor-agent-bridge-consistency.md`](editor-agent-bridge-consistency.md)。两者与本文冲突时，以前两者为准。

## 1. 目标与边界

本架构要同时满足四个目标：

1. brainstorming 和后续设计决策必须发生在可视化 HTML 编辑器中，不能退化为 Agent 在聊天里自行问答。
2. Agent 可以长时间生成、修复和验收；按协作工作流只修改 Bridge 为当前 attempt 登记的 `work_path`，正式作品只由 Bridge 发布该登记 attempt。
3. 浏览器刷新、SSE 轮换、Agent 回合结束或普通网络中断不得丢失已确认请求。
4. 浏览器不获得 MCP 管理接口；owner、attempt、validation、revision 和 publication 门禁限制误操作与跨 session 影响范围。

上述“只写 `work_path`”是 Agent 与 Bridge 的工作流契约，不是同 UID shell 沙箱。Bridge complete 校验并发布当前登记 attempt，但不阻止 Agent shell、其他编辑器或同 UID 进程主动读写可访问文件。

明确不做：

- HTML 页面不直接调用模型 API。
- HTML 页面不连接 MCP stdio，也不实现 MCP JSON-RPC。
- MCP 代理不承载生成、插画、烙入或 PPTX 转换算法。
- Bridge 不把 HTTP receipt 冒充 MCP tool result。
- 前端不能自行启动 daemon、调用管理签发接口或生成 browser token。
- 外部模型调用、shell 和付费生图不承诺 exactly-once；Bridge 只保证持久请求、attempt fence、受控发布和 receipt 幂等。
- 当前同源 `srcdoc` 编辑方式不是敌对 HTML 沙箱；只允许打开可信生成或已审核的 deck。恶意 deck 可使用当前 tab 已有的 browser 权限，session scope 只能限制影响范围，不能把该 deck 变成可信内容。

## 2. 四个运行主体

### 2.1 Agent

Agent 是 Kimi Code 中真正执行工作的 coding agent，负责：

- 读取用户提交的 brief、设计、批注、插画、烙入和导出意图；
- 按工作流只在 `work_path` 内生成或修改 HTML、assets 和 export 产物；
- 按 intent 类型执行生成类的 render/capacity/images/manifest 门禁，或 convert 的 export 门禁；
- 通过 `push_update(progress|complete|fail)` 报告状态；
- 在需要新请求时通过 `await_intent` 等待，而不是轮询网页 DOM。

正常 MCP 工具输入输出不包含 management token，Agent 也不需要 browser token。management token 在运行时存在于 daemon 与 MCP 代理内存，明文只持久化在本机 0600 发现文件；这不承诺阻止同 UID 进程读取其有权限访问的发现文件。

### 2.2 MCP stdio 代理

`tools/bridge_mcp.py` 是官方 MCP SDK 的 stdio 薄代理。Kimi Code 通过 stdin/stdout 与它交换 MCP JSON-RPC；stdout 只允许协议帧，诊断信息只能写 stderr。

代理恰好暴露五个工具：

| 工具 | 责任 |
|---|---|
| `open_editor` | 启动或复用 daemon，登记 consumer，创建/恢复 session，直接取得 browser URL，并按需打开浏览器 |
| `await_intent` | 等待并认领最早可执行的持久请求；按16KiB阈值返回内联 payload，或摘要、字节数和绝对 `intent_file`，并返回 attempt、facts 与 `work_path` |
| `push_update` | 提交 progress、complete 或 fail；complete 请求 Bridge 验证并发布 |
| `get_status` | 只读查询 session、页面、队列、revision 和导出状态 |
| `close_session` | 结束当前 consumer 的协作资格；不关闭页面、daemon 或删除作品 |

MCP 代理把工具调用转换为 `127.0.0.1` 上的管理 HTTP 请求。它不是第二套状态机，业务真相仍在 Bridge SQLite 中。

### 2.3 Bridge daemon

`tools/edit.py` 启动统一 daemon，`tools/bridge_core.py` 提供状态、认证、隔离和发布核心。每个规范 workdir 最多一个 daemon。

Bridge 负责：

- SQLite/WAL 持久化 session、consumer、client、intent、attempt、event、receipt、draft、snapshot 和 publication；
- 管理 waiting/processing owner 与 attempt fence；
- 创建并登记 attempt 工作副本；
- 校验 validation、bundle、revision 和受管路径；
- 只从当前登记 attempt 通过 CAS、snapshot、journal 和 Git 专用 ref 发布正式文件；
- 向浏览器提供 HTTP API、静态受管资源和 fetch-SSE；
- 为浏览器签发 session scoped token，但不把 management token 交给浏览器。

这些机制是协作式完整性和影响范围控制，不是针对同 UID 任意进程的操作系统沙箱。

### 2.4 HTML 编辑器

`editor.html` 是纯静态 HTML/JS/CSS 客户端，负责：

- brainstorming、设计选择、批注、插画、烙入和导出请求的可视化交互；
- 显示和就地编辑正式 HTML deck；
- 通过 HTTP 提交明确意图和 A 类保存事实；
- 通过 status、query、SSE 和 IndexedDB 恢复状态；
- 展示 pending、processing、succeeded、failed、conflict、interrupted 和 cancelled；
- 在有 dirty、活动编辑或草稿风险时阻止远端更新覆盖本地输入。

HTML 页面不生成内容，不直接调用 Agent，也不能把一个请求“发送成 MCP tool result”。deck 在同源 `srcdoc` 中运行，因此必须是可信内容；敌对脚本可能使用当前 tab 的 DOM、sessionStorage 和 session scoped browser 权限。

## 3. 两条通信链路

```text
Kimi Code / Agent
      │
      │ MCP stdio：initialize、tools/list、tools/call、cancel
      ▼
bridge_mcp.py
      │
      │ loopback HTTP + management Bearer
      ▼
Bridge daemon / SQLite / publication
      ▲
      │ loopback HTTP + fetch-SSE + browser session Bearer
      │
editor.html
```

### 3.1 Agent ↔ MCP：stdio

- 通道：stdin/stdout。
- 协议：官方 MCP SDK。
- 身份：代理内部的 consumer ID 与 management credential。
- 结果接收者：Kimi Code 宿主。
- 典型数据：`open_editor` 结果、`await_intent` 认领结果、`push_update` 发布 receipt。

### 3.2 HTML ↔ Bridge：HTTP + SSE

- 通道：本机 `127.0.0.1:<port>`。
- 身份：只作用于一个 session 的 browser token。
- 写入：HTTP POST。
- 状态：HTTP status/query + fetch-SSE。
- 结果接收者：当前浏览器 tab。
- 典型数据：intent accepted receipt、`intent-status`、`deck-changed`、保存 receipt。

### 3.3 不存在 HTML ↔ MCP 直连

浏览器既不能访问 MCP stdio，也没有 management credential。这个通道边界意味着：

- 网页脚本不能通过浏览器 API 直接调用 `open_editor`、`await_intent` 或 `push_update`；
- MCP 宿主退出不会强制关闭编辑页面；
- 浏览器刷新不会改变 Agent consumer owner；
- browser token 只能调用当前 session 的浏览器路由。

它不意味着同源 deck 是敌对代码沙箱。恶意 deck 仍可使用当前 tab 的 browser 权限；必须只打开可信 deck，session scope 只缩小潜在影响范围。

## 4. 两条不同的启动链与浏览器绑定

### 4.1 MCP `open_editor` 入口：直接 browser URL

从零创作时，Agent 首先调用：

```text
open_editor(
  deck_path=null,
  output_path=<相对 HTML 路径>,
  view="brief",
  open_browser=true
)
```

已有作品则传入 `deck_path` 并先打开编辑器。`open_editor` 经 MCP 代理执行以下动作：

1. 验证配置的绝对 workdir。
2. 启动或复用该 workdir 的 daemon。
3. 通过管理 `POST /api/bridge/open` 创建或恢复 session。
4. 登记当前 Agent consumer，但不把“已登记”伪装成正在 waiting。
5. 直接签发 browser token，返回 `editor.html#brt=<browser-token>&session=<id>`，并按 `open_browser` 决定是否交给操作系统打开。
6. editor 将 token 写入 sessionStorage、立即清除 fragment，首次 heartbeat 再把 token 摘要绑定到本 tab 的 `client_id`。

MCP `open_editor` **不经过** `/api/bridge/bootstrap`、`/bootstrap` landing、ticket 或 cookie 兑换。

### 4.2 手动 CLI 入口：一次性 bootstrap

无 MCP 时，本地 CLI 使用另一条启动链：

```bash
python3 tools/edit.py /absolute/workdir --deck index.html
python3 tools/edit.py /absolute/workdir --new reports/index.html
```

CLI 启动或附着 daemon 后调用 `POST /api/bridge/bootstrap`，取得一次性启动 URL；这一步不登记 Agent consumer。手动入口和 MCP 入口复用同一 daemon、SQLite、最终 browser token 与后续浏览器 API，但启动授权链不同，不能把 bootstrap 描述成 `open_editor` 的内部步骤。

### 4.3 仅手动 CLI 使用的 bootstrap 兑换

手动启动链接形态为：

```text
http://127.0.0.1:<port>/bootstrap#boot=<一次性随机值>
```

固定流程：

1. landing 页读取 fragment 中的 boot 值并立即从地址栏清除。
2. 通过限定 cookie 和非秘密摘要 ticket 请求 `/bootstrap` 兑换。
3. Bridge 校验实例、来源、有效期、单次使用状态和固定目标。
4. Bridge 创建或复用 session，签发 browser token。
5. 浏览器跳转到 `editor.html#brt=<browser-token>&session=<id>`。
6. editor 将 token 写入 sessionStorage，再次清除 fragment。
7. 首次 browser heartbeat 把 token 摘要绑定到本 tab 的 `client_id`。

management token 不进入 browser URL、HTML、intent 或 SSE；正常 MCP 工具输出也不返回它。其运行时副本存在于 daemon 与 MCP 代理内存，明文持久副本仅位于 0600 发现文件；同 UID 读取不在安全保证内。

### 4.4 前端可以和不可以重建什么

前端在同一 daemon、同一 origin 且 browser token 有效时，可以自动：

- 重连 HTTP 和 SSE；
- 读取 status；
- 分页查询持久 intent；
- 从最后应用的 event ID 补收事件；
- 恢复 IndexedDB 或服务端草稿。

前端不能：

- 启动 daemon；
- 连接 MCP stdio；
- 调用管理级 `open_editor`；
- 调用 `/api/bridge/bootstrap`；
- 生成新 browser token；
- token 失效后匿名恢复写权限。

因此 daemon 重启后必须重新走对应入口：MCP 调用 `open_editor` 直接取得新 browser URL；手动 CLI 重新签发并兑换 bootstrap。旧 tab 的 token 不允许透明迁移到新实例。

## 5. brainstorming 到正式发布的完整时序

```text
用户          editor.html       Bridge/SQLite       MCP代理        Agent
 │                │                  │                 │             │
 │ 完成选择       │                  │                 │             │
 │ 点击发送 ─────►│                  │                 │             │
 │                │ POST /api/intent►│                 │             │
 │                │◄─ accepted/seq ──│                 │             │
 │                │◄─ SSE pending ───│                 │             │
 │                │                  │◄─ await HTTP ───│◄─await_intent│
 │                │                  │ claim + 副本     │             │
 │                │◄─SSE processing─│─认领结果────────►│────────────►│
 │                │                  │                 │             │写 work_path
 │                │◄─SSE notice ─────│◄─progress───────│◄────────────│
 │                │                  │                 │             │跑该intent要求的全部门禁
 │                │                  │◄─complete────────│◄────────────│
 │                │                  │ validation/CAS/journal/publish │
 │                │◄─succeeded───────│─receipt─────────►│────────────►│
 │                │◄─deck-changed────│                 │             │
 │ 看见正式作品 ◄─│ 重新加载或保护草稿│                 │             │
```

### 5.1 页面提交

用户只有点击“发送给 AI”才创建 B 类请求。预览和复制不入队。`brief.submitted` 的完整 intent envelope 为：

```json
{
  "protocol_version": 2,
  "intent_id": "<客户端生成的 UUID>",
  "session_id": "<当前 session>",
  "type": "brief.submitted",
  "base_revision": null,
  "payload": {
    "text": "<人类可读简报>",
    "json": {
      "kind": "design-brief"
    }
  },
  "client_ts": "<UTC RFC3339 时间>"
}
```

已有 deck 时 `base_revision` 是页面当前加载的 source revision；无 deck 时为 `null`。`payload.text` 与 `payload.json` 由同一份表单状态生成，`payload.json.kind` 对 brief 固定为 `design-brief`。页面先把待确认快照写入 IndexedDB，再 POST `/api/intent`。Bridge 事务落盘后返回：

```json
{
  "ok": true,
  "accepted": true,
  "intent_id": "...",
  "seq": 1,
  "status": "pending"
}
```

这个响应是 HTTP accepted receipt，不是 MCP tool result。

### 5.2 Agent 认领

Agent 调用 `await_intent`，MCP 代理调用管理 `/api/bridge/await`。认领过程由 session lock 串行化，并使用若干短 SQLite 事务，而不是把 bundle 复制和扫描包在一个长事务里：

1. 在 session lock 内用短事务校验 consumer 已通过 `open_editor` 登记且未 close，原子取得 waiting owner；其他有效 owner 得到 `SESSION_BUSY`；**认领前先作废陈旧 recoverable（P4.2），且 session 级恢复门已移除（P4.3，2026-10-27）**——存在待恢复项不再阻断整会话的认领（`agent_state`/`recoverable_count` 仍如实呈现）。
2. 锁内选择最早可执行的 pending intent，读取 facts 并复核 base revision；若 base 已变化，在短事务中记录 conflict 与事件，不创建可交付副本。
3. 仍在 session lock/认领准备门闩保护下、但不持有 SQLite 写事务，创建或复用候选 `work_path`，复制完整 bundle，扫描复制前后清单和字节摘要，并落盘 intent/job 元数据。复制或扫描失败时 intent 保持 pending。
4. 复制完成后再用短事务复核 owner、base 和当前状态，登记 attempt/`work_path`，把 pending 原子改为 processing，并在同一事务写 `intent-status` 事件。
5. 返回 attempt、facts、base revision、绝对 `intent_file`、`work_path` 和 `target_path`；同 owner 重投递复用同一 attempt/路径，不重新复制。

典型工作副本路径：

```text
.pptx-html/jobs/<intent_id>/attempt-1/work/<relative-deck>
```

payload 以协议规定的规范 JSON UTF-8 字节数计量：`payload_bytes <= 16 KiB` 时，`await_intent` 内联完整 `payload`；超过 16 KiB 时不内联 payload，而是返回 `payload_bytes`、`payload_digest` 和绝对 `intent_file`，由 Agent 从该文件读取完整持久请求内容。两种情况都仍返回当前 `attempt`、`facts` 和绝对 `work_path`。

浏览器 HTTP/SSE/query 输出不暴露任意内部路径；`await_intent` 是明确的 MCP 例外，向受信 Agent 返回绝对 `intent_file` 与 `work_path` 供读取输入和修改候选。按工作流，正式 `target_path` 只用于识别和最终发布，Agent 不直接写入；这项纪律不是 shell 沙箱。

### 5.3 长时间处理

claim 后 processing owner 是持久所有权：

- 90秒 lease 只用于 waiting owner 回收；
- processing 的 lease 字段仅为活性 telemetry；
- 无 heartbeat 或 progress 不会按时钟中断 processing；
- 同一 owner 的迟到 heartbeat/progress/complete/fail 仍有效；
- 第二 consumer 在明确终止前始终得到 `SESSION_BUSY`。

processing 只由 complete、fail、原 consumer close、网页显式 stop、daemon restart 或真实发布/CAS结果结束。

### 5.4 Agent complete 与发布

Agent 在工作副本完成后运行该 intent 类型要求的真实门禁：brief/design/anno/bake/illustrate 要求 render、capacity、images、manifest，convert 要求 export。随后调用 `push_update(action="complete")`，提交：

- `intent_id`；
- 当前 `attempt`；
- candidate revision；
- 每项 check 的名称、argv、exit code 和报告路径；
- 需要时的 export source binding。

Bridge 随后：

1. 在锁内复核 session、owner、attempt 和 processing 状态。
2. 只接受并扫描该 attempt 登记的 `work_path`，不接受 Agent 另传任意目录。
3. 校验 validation 与该 intent 类型的必需门禁集合。
4. 扫描 bundle 并核对 candidate revision。
5. 比较正式目标的 base revision。
6. 创建 snapshot 和 publication journal。
7. 执行受控替换。
8. 再次确认候选文件没有在 seal 后变化。
9. 写成功状态、receipt、revision 和持久事件。

因此 complete 的保证是“只发布 Bridge 登记的当前 attempt 且门禁通过”，不是阻止同 UID shell 访问文件。页面收到 `succeeded` 和 `deck-changed` 后，clean tab 自动加载；dirty、活动编辑或草稿存在时只提示待处理更新，不覆盖本地输入。

## 6. 三种“结果”不能混淆

| 结果 | 回答的问题 | 接收者 |
|---|---|---|
| HTTP accepted receipt | 页面请求是否已被 Bridge 可靠接收并落盘 | HTML 页面 |
| SSE/query 状态 | 请求后来是 pending、processing、succeeded 还是错误 | HTML 页面 |
| MCP tool result | Agent 的工具调用返回了什么认领、状态或发布结果 | Kimi Code 宿主 |

网页可以显示 intent ID、seq、状态和发布 receipt，但不能声称“已收到 MCP tool result”。MCP tool result 只通过 stdio 返回宿主。

## 7. SSE 生命周期与页面状态

### 7.1 事件和游标

Bridge 的 SSE 通道支持七类事件或控制通知：

- `deck-changed`
- `export-refreshed`
- `assets-changed`
- `intent-status`
- `notice`
- `resync-required`
- `server-stop`

普通业务事件持久化并带单调 event ID，包括 `deck-changed`、`export-refreshed`、`assets-changed`、`intent-status` 和 `notice`。`resync-required` 可在客户端游标早于保留窗口时由服务即时合成，用于要求 status/query 全量校准，不冒充一条已持久业务事件；`server-stop` 是 daemon 关闭期发送的特殊控制通知，不作为普通业务历史重放。

页面只有在成功应用持久事件或把待处理状态可靠保存后才推进游标；断线后使用 `after=<last_event_id>` 补收。收到 `resync-required` 时按其 `latest_event_id` 执行协议规定的 status/query 恢复，收到 `server-stop` 时停止当前流并显示关闭状态。

### 7.2 30秒计划轮换

服务端为限制请求线程，让单次 SSE 响应最多持续约30秒，并每15秒发送注释 ping。干净 EOF 是计划内轮换：

```text
正常EOF → 0ms静默续接 → 不显示“Bridge 正在重连”
```

只有真实网络或协议错误才显示重连，并按1、2、4、8、16、30秒退避。重连成功后重新读取 status 和持久 intent，清除错误外观。

401/403表示 browser token 失效：

```text
停止重试 → 显示“Bridge 凭证失效” → 要求合法入口重新打开
```

前端不能在这个分支自行签发 token。

### 7.3 页面在线不等于 Agent 在线

- `page_online=true`：至少一个 browser client 在45秒窗口内有有效 heartbeat。
- `agent_state=waiting`：当前 owner consumer 已取得 waiting lease，正在等待请求。
- `agent_state=working`：当前 owner consumer 持有 processing attempt。
- `agent_state=recovering`：当前无 working/waiting owner，且存在 failed、conflict 或 interrupted 请求等待用户处理。
- `agent_state=paused`：当前无 owner、无 recoverable 请求，但存在经 `close_session` 暂停的 consumer；重新协作必须再次 `open_editor`。
- `agent_state=offline`：以上情况均不成立；daemon 仍可能正常，页面也可能在线。

聚合优先级是当前 owner 的 `working/waiting`，其次 `recovering`，再其次 `paused`，最后 `offline`。因此“Bridge 已连接”“页面在线”“Agent 已登记”“Agent 正在等待”“Agent 正在处理”和“等待恢复”必须分别显示，不能互相推断。

## 8. 保存、生成与并发冲突

页面保存和 Agent complete 共用 revision CAS。示例：

```text
Agent claim base = R1
用户先保存，正式版本变为 R2
Agent 以 R1 complete
→ REVISION_CONFLICT
→ 不覆盖 R2
→ 保留 Agent 工作副本
```

浏览器保存、图片替换和回滚是 A 类事实，直接更新 revision 和 events，不进入模型队列。设计、批注、插画、烙入和导出是 B 类请求，需要 Agent 认领。

## 9. stop、close、restart 与恢复

### 9.1 浏览器 stop

网页对 processing intent 显式停止时：

- 当前 attempt 转为 interrupted；
- Bridge owner 和发布资格释放；
- 返回 `external_work_may_continue:true`；
- 不承诺终止 Agent shell、供应商任务或撤销费用。

重复 stop 必须保持相同风险提示，不能因为状态已是 interrupted 就声称外部工作不会继续。

### 9.2 Agent close

`close_session` 关闭当前 consumer：

- waiting owner 被释放；
- 自己的 processing 转 interrupted；
- 页面和 daemon 保持；
- 同 consumer 必须再次 `open_editor` 才能继续 await。

### 9.3 daemon restart

重启会撤销旧实例的 browser token 和 consumer 身份。SQLite、intent、attempt、receipt、draft、snapshot 与工作副本保留；遗留 processing 保守转为 interrupted，避免死 owner 永久占锁。

旧 tab 不能透明迁移到新 origin/token。必须重新走对应启动链：MCP `open_editor` 直接返回新 `editor.html#brt=...` URL；本地 CLI 则重新签发 `/api/bridge/bootstrap` URL 并完成 landing/ticket/cookie 兑换。

### 9.4 resume 与 rebuild

`rebuild`：

- failed、conflict、interrupted 可用；
- attempt + 1；
- 从当前正式版本创建独立新副本；
- 隔离更强，但可能重复外部动作和费用。

`resume`：

- 仅 interrupted 可用；
- attempt + 1；
- 正式 base 未变化、无未完 publication、原 work path 安全完整且用户确认无活跃 writer时，复用原物理路径；
- 必须重跑该 intent 类型要求的全部门禁：生成类为 render/capacity/images/manifest，convert 为 export。

attempt 增加后，旧 producer 携旧 attempt 的 progress、fail 和 complete 均被 fence。attempt fence 只能阻止旧 API 写入，不能阻止同 UID 旧进程继续写复用路径，因此无法确认 writer 已停止时必须选择 rebuild。

## 10. 浏览器本地状态与 Bridge 持久状态

### 10.1 浏览器本地提交/重试状态

以下状态只描述当前 tab 的网络动作与 IndexedDB 待确认记录，不是 Bridge intent 状态：

| 浏览器本地状态 | 含义 | 恢复动作 |
|---|---|---|
| `submitting` | 首次 intent POST 正在进行，尚未获得 accepted receipt | 禁止重复点击；保留同一 intent ID |
| `unconfirmed` | 请求可能已落盘，但 HTTP 结果丢失或未知 | 以同一 intent ID 和同一 envelope 幂等重发，再用 query 校准 |
| `retrying` | 用户已确认 rebuild/resume，retry POST 正在进行或结果未知 | 以同一 retry ID 和同一请求幂等重发，不预先伪造新的 Bridge 状态 |

### 10.2 Bridge 七种持久 intent 状态

| Bridge 持久状态 | 页面语义 | 允许操作 |
|---|---|---|
| `pending` | 已落盘，等待 Agent | 取消 |
| `processing` | Agent 已认领，可能长时间执行 | 查看进度、显式停止 |
| `succeeded` | 已完成并有发布结果 | 查看 receipt/加载作品 |
| `failed` | Agent 明确失败，副本保留 | rebuild |
| `conflict` | 正式版本已变化或发布冲突 | 从最新版本 rebuild |
| `interrupted` | owner 因 stop/close/restart 失效，副本保留 | 条件满足时 resume，或 rebuild |
| `cancelled` | 尚未执行即取消 | 只读历史 |

brainstorming 主结果按以下优先级恢复：

```text
processing
→ recoverable（failed/conflict/interrupted）
→ pending
→ succeeded/cancelled
```

同级才比较更新时间和 seq；页面还应显示“其他 brief ×N”，避免较新的 pending 遮住较旧的恢复项。

## 11. 安全不变量与信任边界

1. management token 在运行时存在于 daemon 与 MCP 代理内存；明文只持久化于 0600 发现文件。正常 MCP 工具输出、浏览器 URL、HTML、intent 和 SSE 都不包含它，但不承诺阻止同 UID 进程读取有权限访问的发现文件或进程资源。
2. browser token 只授权一个 session，首次 heartbeat 绑定一个 client ID；session scope 限制影响范围，不是敌对脚本隔离。
3. browser 不能调用 open、await、complete、close 等管理动作。
4. Agent“只写 Bridge 登记的 attempt `work_path`”是工作流契约；Bridge complete 只发布当前登记 attempt，不构成同 UID shell 沙箱。
5. complete 必须同时通过 owner、attempt、validation、bundle、revision 和 publication 检查。
6. URL fragment 中的启动凭证读取后立即清除，不写入作品。
7. `.pptx-html`、`.git`、凭证和越界路径不得由浏览器静态服务读取。
8. 浏览器 intent、SSE、query 和 status 输出不得包含 token、完整 HTML、`.pptx-html` 内部路径或堆栈。MCP `await_intent` 是受信 Agent 通道的明确例外，会返回绝对 `intent_file` 与 `work_path`。
9. 当前同源 `srcdoc` 不安全运行敌对 HTML。首次受管打开必须只使用可信生成或已审核的 deck；恶意 deck 可使用当前 tab 的 browser 权限，不能把 session scope 误写成沙箱保证。
10. daemon 存活、页面在线、consumer 登记、Agent waiting、working、paused 与 recovering 是不同事实，必须分别证明。
11. 页面无法自行重建授权链接是安全特性，不是待绕过的限制。

## 12. 关键调用链、自动验收与正式验收边界

MCP 与手动 CLI 的启动链必须分别映射，不能用一个“open → bootstrap”用例覆盖两者：

| 调用链 | 自动验收 |
|---|---|
| MCP stdio initialize/list/call/cancel | `r_bridge_check.py --group transport --group sdk` |
| MCP `open_editor` → `POST /api/bridge/open` → 直接 `editor.html#brt=...` → heartbeat/status | `r_bridge_check.py --group sdk --group integration` |
| 手动 CLI → `POST /api/bridge/bootstrap` → landing/ticket/cookie → `GET /bootstrap` 兑换 → heartbeat/status | `r_bridge_check.py --group http --group ui --group integration`；标准回归 T12 |
| brief POST → await claim → work path → complete → deck reload | `r_bridge_check.py --group ui --group integration` |
| waiting lease 与持久 processing owner | `test_bridge_core.py`、r sdk/fault |
| stop → interrupted → resume/rebuild →旧 attempt fence | `test_bridge_core.py`、r ui/integration |
| 30秒 SSE 计划轮换与401/403失效凭证 | r ui |
| publication、CAS、响应丢失与重启恢复 | r fault/integration |
| 编辑器与技能的标准自动 harness 覆盖回归 | `python3 tests/harness/run_e2e.py` |

自动验收通过不等于 Bridge 整体 formal 通过，也不得覆盖独立宿主、付费外部服务或人工验收边界。当前结论必须逐项保留：

- 自动代码回归：`run_e2e.py` 55/55 PASS；只证明其覆盖的代码路径。
- Kimi formal：**FAIL**，`observation-07` 在工具完成后宿主进程未退出。
- Codex formal：**BLOCKED**，未登录。
- 真实生图：**UNKNOWN**，既有调用未形成可验收的完整 Bridge 结果，未经授权不重试付费调用。
- Office 365/WPS、完整桌面交互、图像观感与硬件掉电：**NOT_RUN**。

任何新的自动回归绿灯都不能把上述 FAIL、BLOCKED、UNKNOWN 或 NOT_RUN 改写为 PASS；实际证据与最新状态以 [`../test_acceptance/editor-agent-bridge.md`](../test_acceptance/editor-agent-bridge.md) 为准。

## 13. 阅读顺序

1. 本文：理解四个主体和端到端通信。
2. [`editor-agent-bridge.md`](editor-agent-bridge.md)：理解产品目标、第一性原理和总体取舍。
3. [`editor-agent-bridge-protocol.md`](editor-agent-bridge-protocol.md)：查询精确工具、HTTP、SSE、状态和错误契约。
4. [`editor-agent-bridge-consistency.md`](editor-agent-bridge-consistency.md)：查询revision、bundle、Git、journal、认证和恢复算法。
5. [`../howto/editor-agent-bridge.md`](../howto/editor-agent-bridge.md)：安装、注册和日常操作。
6. [`../test_acceptance/editor-agent-bridge.md`](../test_acceptance/editor-agent-bridge.md)：验收矩阵和实际结果边界。
