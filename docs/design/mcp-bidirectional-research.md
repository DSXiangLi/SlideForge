# MCP 双向通信调研：UI↔Agent 交互范式对比与演进路线

> 调研日期：2026-10-14
> 触发：用户在 Kimi Code 中遇到 MCP 工具调用超时（`await_intent` 被 60 秒默认 `toolTimeoutMs` 掐断），引发对 MCP 单向协议限制的系统性调研。
> 方法：dsh（DeepSeek Harness）源码分析 + Cowart 源码分析 + MCP 官方规范 + 开源生态扫描。

## 1. 问题本质：MCP 协议的单向性

标准 MCP 协议是**严格单向请求-响应**的：agent 调用工具 → 工具返回结果。协议明确规定"servers do not initiate JSON-RPC requests and clients do not send JSON-RPC responses"。

这意味着：**MCP server 不能主动通知 agent**。当用户在 UI 上完成操作（编辑幻灯片、填写表单、选择主题）后，没有标准机制让这个信息"推送"给 agent。

当前项目用 `await_intent` 阻塞式工具调用绕行——agent 发起一次工具调用，阻塞等待用户在编辑器页面上提交 intent。这带来超时问题：MCP 客户端（如 Kimi Code）默认 60 秒超时会掐断调用。

### 超时问题的直接修复

根因是两端超时参数未配对：
- bridge 侧 `await_intent` 默认 `timeout_sec=86400`（一天）
- Kimi Code 侧 MCP 客户端默认 `toolTimeoutMs=60000`（60 秒）
- 项目 `.kimi-code/mcp.json` 已配 `toolTimeoutMs: 86500000`，但**配置在会话建立时定型**，旧会话仍按 60 秒跑

修复：新开会话让配置生效；可选在 `~/.kimi-code/config.toml` 加 `[mcp] tool_timeout_ms = 86500000` 做全局兜底。优先级：per-server 字段 > 环境变量 > config.toml > 默认值。

## 2. 三种架构范式对比

### 2.1 dsh 插件模式（DeepSeek Harness）

**架构**：一切皆插件（Cordis 框架），插件与 harness 同进程、同 event loop，无沙箱隔离。

**UI 交互链路**（三种形态）：

| 形态 | 场景 | agent 看到什么 | 是否阻塞 |
|---|---|---|---|
| A. 普通消息 | 用户在 UI 输入文字 | 一条 user 消息 | 不阻塞（入队等下一回合） |
| B. 工具结果 | `ask_user_question` 等交互式工具 | 一次 tool result | 不阻塞（工具挂起为 pending Promise，不占回合） |
| C. 宿主注入 | 任务完成通知、审批结果公告 | 一条 context 消息 | 不阻塞（注入不唤醒循环） |

**形态 B 是最精巧的设计**：agent 调用 `ask_user_question` 工具 → 宿主把工具调用挂起为 pending Promise → 通过 WebSocket 推 question/requested 给浏览器 → UI 渲染问题卡 → 用户作答后 POST /api/respond（带 rpcId）→ 宿主 resolve Promise → 工具返回结果。**agent 不知道有网页、有人在填表——它只看到一次普通的 tool_call → tool_result。**

关键特性：
- 上下行严格分工：下行 = 两条只读 WebSocket（mux + host），上行 = HTTP fetch RPC（POST + rpcId 回声）
- 插件可注册新工具、system prompt 片段、HTTP 路由、事件类型
- 通过 waterfall 事件可拦截改写 agent 循环本身（`agent/pre-step`、`tools/execute`）
- HMR 热替换、事务性回滚——Cordis fiber 提供完整生命周期管理
- 浏览器端也跑一套 Cordis，UI 组合靠 slots（声明式槽位认领 + 优先级遮蔽）
- 插件代码与 webui 同 JS 上下文（无 iframe/CSP/Shadow DOM）——"shell 级信任，非安全边界"

**局限**：绑定 dsh/Cordis 生态，不可移植到其他 agent 框架。

### 2.2 Cowart 模式（MCP ext-apps widget）

**架构**：标准 MCP stdio server + MCP Apps (ext-apps) widget 资源 + 文件系统状态桥梁。

**UI 交互链路**：

```
agent 调用 render_cowart_canvas_widget 工具
  → MCP server 返回 widget 资源 URI（ui://widget/cowart/canvas.html）
  → 宿主在界面内渲染原生 widget 面板（不弹浏览器）
  → 用户在 widget 上操作
  → widget 通过 window.cowartMcp.sendFollowUpMessage() 注入用户消息到对话流
  → widget 通过 window.cowartMcp.callServerTool() 读写文件系统状态
  → agent 在下一轮调用 MCP 工具读取文件系统状态
```

**两条通道**：
- `sendFollowUpMessage(message)` —— widget 主动向 agent 对话流注入消息（触发 agent 新一轮工作）
- `callServerTool({name, arguments})` —— widget 通过宿主中转调用 MCP server 工具（读写文件状态）

**状态同步走文件系统**——widget 写 `canvas/cowart-selection.json`，agent 调 `get_cowart_selection` 工具读文件。不需要 SQLite、SSE、daemon。

**关键特性**：
- 遵循 Agent Plugins v1.0.0 规范（`plugin.json` + `skills/` + `mcp.json` 可移植入口）
- MCP server 是标准 stdio，任何 MCP host 可连
- widget 渲染需要宿主支持 `io.modelcontextprotocol/ui` extension
- ext-apps 规范是开放的（非 OpenAI 专有），已合并 MCP-UI 社区项目 + OpenAI Apps SDK

**局限**：widget 原生渲染需宿主支持 ext-apps；`sendFollowUpMessage` 也依赖宿主桥接，非标准 MCP。

### 2.3 本项目 Bridge 模式（当前）

**架构**：MCP stdio server + 自建 daemon（loopback HTTP + SQLite/WAL + SSE 七类事件 + Git 隔离 ref）+ 独立浏览器窗口。

**UI 交互链路**：
```
agent 调用 await_intent 工具（阻塞等待）
  → bridge daemon 持有 waiting lease
  → 浏览器打开 editor.html，用户操作
  → 用户提交 intent → daemon 存入 SQLite
  → await_intent 工具调用返回（如果没超时的话）
  → agent 消费 intent
```

**关键特性**：
- 任何 MCP host 可用（纯标准 MCP，不依赖宿主扩展）
- 交付物即 HTML 文件（项目定位决定）
- 自建机械量大：lease/attempt fence、CAS、publication journal、SSE、Git 隔离 ref
- 超时问题：MCP 客户端默认 60 秒掐断 `await_intent` 阻塞调用

**局限**：MCP 协议单向性导致必须阻塞等待；自建 daemon 复杂度高；独立浏览器窗口断裂对话流。

### 2.4 三范式对照表

| 维度 | dsh 插件模式 | Cowart ext-apps | 本项目 Bridge |
|---|---|---|---|
| UI 位置 | 宿主界面内，同 JS 上下文 | 宿主界面内，widget 面板 | 独立浏览器窗口 |
| 通信通道 | Cordis 服务/事件（进程内直调） | ext-apps postMessage + 文件系统 | 自建 daemon + SSE + SQLite |
| "等人"建模 | 工具挂起为 pending Promise | 工具立即返回 + sendFollowUpMessage 触发新回合 | 阻塞工具调用 await_intent |
| 状态同步 | 进程内对象 / WebSocket | 文件系统 | SQLite + SSE |
| 自建机械量 | 几乎为零（Cordis 免费） | 很低（只管文件读写） | 极高（lease/attempt/journal/CAS） |
| 超时问题 | 不存在 | 不存在 | 存在（MCP 客户端超时） |
| 可移植性 | 绑死 dsh/Cordis | 需宿主支持 ext-apps | 任何 MCP host |
| 安全隔离 | 无（shell 级信任） | widget iframe 沙箱 | 浏览器沙箱 |

## 3. 开源生态方案扫描

### 3.1 MCP 官方进展

| 方案 | 机制 | 方向 | 解决双向？ | 需宿主支持？ |
|---|---|---|---|---|
| **MCP Elicitation** | Multi Round-Trip + InputRequiredResult | server→user | ❌ 阻塞式 | ✅ client 需声明 capability |
| **MCP Notifications** | JSON-RPC notification + subscriptions | server→client | ⚠️ 仅推送，无响应 | ✅ |
| **MCP Streamable HTTP (SSE)** | SSE 流推送 notifications | server→agent | ✅ server 中转可达成 | ✅ 需 Streamable HTTP transport |
| **MCP Tasks Extension** | durable handle + 轮询 | agent↔server | ❌ 但提供非阻塞替代 | ✅ |
| **MCP Apps (ext-apps)** | postMessage + JSON-RPC | UI↔host↔agent | ✅ **真正双向** | ✅ host 需支持 ui extension |

**关键约束**：MCP Modern 版本（2026-07-28）明确移除了 Legacy 版本中 server 发起 request 的能力。Notifications 是唯一的 server→client 推送通道，但无法要求响应。**协议层面短期内不会原生支持"server 主动发起请求"。**

### 3.2 MCP Apps (ext-apps) —— 唯一的真正双向方案

- 仓库：`github.com/modelcontextprotocol/ext-apps`（SEP-1865，2026-01-26 Stable）
- 统一了 MCP-UI（社区项目）和 OpenAI Apps SDK，是正式 MCP 扩展规范
- 机制：server 声明 `ui://` 资源 → 宿主沙箱 iframe 渲染 → `postMessage` + JSON-RPC 2.0 双向通信
- 已支持：Claude、ChatGPT、Postman、HuggingFace、Shopify、Goose、ElevenLabs 等
- **Cowart 用的就是这个**——`window.cowartMcp.sendFollowUpMessage()` 是 ext-apps 提供的 API

### 3.3 LangGraph interrupt/resume —— 暂停-恢复

- agent 执行到需要用户输入时"暂停"（interrupt），状态被 checkpoint 持久化
- agent 进程释放，不占资源，不会超时
- 人类在任意时刻提供输入，agent 从 checkpoint 恢复执行（resume）
- **关键区别**：不是"卡在工具调用里等"，而是"去休眠了，等被唤醒"
- 局限：需要 LangGraph runtime 和 persistence layer，不是 MCP 协议层面方案

### 3.4 其他 agent 框架

几乎所有框架的 HITL 都是**阻塞式询问**，没有框架原生支持"UI 主动通知 agent"：

| 框架 | 机制 | 双向？ |
|---|---|---|
| AutoGen User Proxy | 阻塞式询问 | ❌ |
| OpenAI Assistants API | requires_action 状态 | ❌ |
| CrewAI | human_input=True 阻塞 | ❌ |
| Dify | Human Input 节点阻塞 | ❌ |

### 3.5 开源 MCP HITL 项目

| 项目 | Stars | 机制 | 双向？ |
|---|---|---|---|
| ttommyth/interactive-mcp | 351 | OS 通知 + CLI 阻塞 | ❌ |
| GongRzhe/HITL-MCP-Server | 163 | tkinter GUI 阻塞 | ❌ |
| confirm-ai/confirm-mcp | 2 | 阻塞 + 轮询 fallback | ⚠️ 轮询可避免超时 |

**confirm-mcp 的轮询思路值得借鉴**：工具调用不阻塞等待，立即返回 pending 状态；agent 稍后再调 `check_approval` 轮询。超时不再是问题（因为不阻塞）。

## 4. 演进路线

### 路线 A：短期优化（今天能做，不依赖宿主改动）

保留 MCP 阻塞模型，降低自建机械复杂度：

1. **超时配对**：`timeout_sec` 与 `toolTimeoutMs` 两端必须同步（已修复）
2. **超时后优雅降级**：`await_intent` 超时返回"等待中"状态而非报错（AGENTS.md 红线已设计：timeout 后结束回合，用户新消息触发新回合重新 await）
3. **状态层简化**：SQLite → 文件系统。用户提交 intent 后，编辑结果直接写回 HTML 文件；agent 拿到 intent 后直接读文件。`get_status`、`snapshot`、`publication journal` 等 daemon 侧状态管理可大幅缩减——文件本身就是真相
4. **不能砍的部分**：`await_intent` 阻塞等待模型（MCP 约束）、daemon 进程管理（SSE 连接）、intent 队列

### 路线 B：中期根本解（需 Kimi Code 支持 MCP Apps ext-apps）

一旦 Kimi Code 支持 `io.modelcontextprotocol/ui` extension：

1. `render_editor_widget` 工具返回 widget URI，宿主在界面内渲染 editor.html（不弹浏览器）
2. editor.html 注入 host bridge 脚本，获得 `sendFollowUpMessage`（用户编辑意图 → agent 消息）和 `callServerTool`（读写 HTML 文件）
3. 状态同步走文件系统——agent 写 HTML 文件、editor 读 HTML 文件
4. **bridge_core 的 daemon/SSE/SQLite/intent 队列/lease/attempt/journal 全部删除**
5. editor.html 的 host bridge 做能力检测：有 ext-apps API 走原生通道，没有降级到当前 bridge 模式（双轨兼容，与 Cowart 的 HTTP fallback 思路一致）

### 路线 C：长期参考（LangGraph 模式）

如果 Kimi Code 未来走自己的 agent runtime 路线，interrupt/resume 模式值得参考：
- 把"等用户"从"阻塞一次工具调用"变成"暂停 agent + 持久化状态 + 等待恢复信号"
- 需要 agent runtime 层面支持，不是 MCP 工具层面能解决

### 路线 D：可移植插件打包（与上述路线正交）

按 Agent Plugins v1.0.0 规范把项目打包为 Kimi Code 插件：
- `plugin.json` + `skills/` + `mcp.json` 作为可移植入口
- `.kimi-code/` 目录放 Kimi Code 专用元数据
- MCP server 声明为 `mcpServers`，hooks 管理 daemon 生命周期（SessionEnd → `--stop`）
- sessionStart 加载技能，slash commands 提供快捷入口
- **当前 Kimi Code 插件不支持进程内工具注册**（manifest 的 `tools` 字段被 ignore），工具只能经 MCP server 子进程提供

## 5. Kimi Code 扩展能力现状

基于官方文档（2026-10-14 确认）：

| 能力 | 现状 |
|---|---|
| 进程内工具注册 | ❌ manifest `tools` 字段被 ignore |
| waterfall 中间件改写 agent 循环 | ❌ hooks 是弱化版：固定事件 + 外部脚本 + fail-open |
| UI 扩展（浏览器端 slots） | ❌ 无任何 UI 扩展面 |
| 配置式装配（skills/agents/systemPrompt/mcpServers/hooks/commands） | ✅ |
| MCP ext-apps widget | ❌ 未支持 |
| 插件安装执行代码 | ❌ 安装期不执行代码，路径限制在插件根内 |

**结论**：Kimi Code 只保留了"用户层装配"，把 dsh 那个全权内部层整个砍掉了。超时问题的根因是 MCP 协议单向性 + Kimi Code 不支持 ext-apps，不是 bridge 实现缺陷。

## 6. 关键结论

1. **MCP 协议的单向性是结构性约束**——标准 MCP 内无法让 server 主动通知 agent。生态中几乎所有 HITL 方案都用阻塞式工具调用绕行，超时是共性痛点。

2. **唯一真正解决双向通信的标准化方案是 MCP Apps (ext-apps)**——通过 `postMessage` + JSON-RPC 实现 UI↔宿主双向通信。Cowart 已验证可行，但需宿主支持 `io.modelcontextprotocol/ui` extension。

3. **本项目 bridge 的自建机械量（daemon/SQLite/SSE/lease/attempt/journal）是 MCP 单向性约束下的必要代价**——不是过度设计，而是"在不支持 ext-apps 的宿主上模拟双向通信"的代价。

4. **演进优先级**：路线 A（超时优化 + 状态简化）先做 → 路线 D（插件打包）正交推进 → 路线 B（ext-apps 根本解）作为给 Kimi Code 的需求输入。

## 参考

- MCP 官方规范：https://modelcontextprotocol.io/docs/concepts/architecture
- MCP ext-apps 规范：https://github.com/modelcontextprotocol/ext-apps
- Agent Plugins v1.0.0：https://agent-plugins.org/specification
- LangGraph HITL：https://docs.langchain.com/oss/python/langgraph
- dsh 源码：`~/Desktop/deepseek-harness/`（Cordis 插件架构 + waterfall 事件 + slots UI 组合）
- Cowart 源码：`~/Desktop/Cowart/`（MCP ext-apps widget + 文件系统状态桥梁）
- Kimi Code Plugins 文档：https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html
- Kimi Code MCP 文档：https://www.kimi.com/code/docs/en/kimi-code-cli/customization/mcp.html
- Kimi Code Hooks 文档：https://www.kimi.com/code/docs/en/kimi-code-cli/customization/hooks.html
- Kimi Code config-files 文档：https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/config-files.html
