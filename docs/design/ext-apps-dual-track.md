
# MCP Apps (ext-apps) 双轨迁移设计

> ⚠️ **已被 `mcp-apps-upgrade.md` 取代（2026-10-19）**。本文保留作演进记录：其 §1 动机、§2.4 沙箱假设、§5.2 工具面扩张、
> §5.7.3 本地持久化、§7 能力检测决策树均被后续实测修正（详见新文档 §1.2 / §4.2 / §4.3 / §5.3）。
> 实施一律以 `mcp-apps-upgrade.md` 为准。

> 日期：2026-10-15。状态：**已被取代**。
> 前置：`mcp-bidirectional-research.md`（三范式对比 + 演进路线，路线 B 的实施化设计）。
> 依据：用户本地下载的官方 ext-apps（`~/Desktop/ext-apps`，已核对与 GitHub main @ 82221c0 同一提交，`@modelcontextprotocol/ext-apps` **2.0.3**，规范稳定版 `specification/2026-01-26/apps.mdx`，SEP-1865）源码精读 + `~/Desktop/Cowart/`（v0.1.28）用法解剖 + 本项目 bridge 对接面盘点。

## 0. 一句话决策

**传输层可替换，状态机不动**：`BridgeCore`（intent 队列 / attempt 隔离副本 / 验证证据 / CAS 发布 / Git 隔离 ref）作为宿主无关的核心整体保留；其外的"远程不受信前端"传输机械（loopback HTTP、SSE、两级凭证、心跳、lease）按宿主能力换成 ext-apps 的 `postMessage` JSON-RPC 通道。宿主支持 ext-apps 走**轨 A（宿主内 widget）**，不支持走**轨 B（现有 daemon + 独立浏览器）**，`editor.html` 增加第四运行态，单文件零构建红线不破。

## 1. 背景：为什么是现在

`mcp-bidirectional-research.md` 的三个结论：

1. MCP 协议单向性是结构性约束，`await_intent` 阻塞等待 + 超时配对是绕行不是解；
2. 唯一标准化的真正双向方案是 MCP Apps (ext-apps)，Cowart 已验证可行；
3. 本项目 bridge 的自建机械是"在不支持 ext-apps 的宿主上模拟双向"的必要代价——不是过度设计，**因此轨 B 必须完整保留作为降级轨**。

本文档把路线 B（根本解）落为可实施设计。核心收益：

- **超时问题消失**：轨 A 没有任何阻塞式工具调用，UI→agent 方向走 `ui/message` 直接注入对话流触发新回合，`toolTimeoutMs` 配对问题不复存在；
- **对话流不断裂**：编辑器在宿主界面内 iframe 渲染，不再弹独立浏览器窗口；
- **自建机械减半**：凭证、SSE、心跳、page_online 探测、bootstrap 票据在轨 A 整层删除。

## 2. ext-apps 机制精要（源码事实）

### 2.1 身份三角与通道

```
View（iframe 内，App 类）<--PostMessageTransport--> Host（AppBridge）<--外层 MCP Client--> Server
```

- iframe 通道上唯一握手是 `ui/initialize`：View 宣告 `appInfo/appCapabilities/protocolVersion`，Host 回 `hostCapabilities/hostInfo/hostContext`；View 随后发 `ui/notifications/initialized`，**Host 在此之前不得向 View 发任何消息**。
- Host 在 `oninitialized` 后 MUST 发 `ui/notifications/tool-input`（恰一次、先于 result），工具执行完发 `ui/notifications/tool-result`；卸载前 MUST `ui/resource-teardown`（View 可 async 清理存状态）。

### 2.2 Server 侧声明（协议层只是元数据，不绑语言）

- 工具挂 UI：`_meta.ui.resourceUri = "ui://..."`（另可 `visibility:["model"|"app"]`——`["app"]` = 对模型隐藏、仅 View 可经 `tools/call` 调用）；
- 资源：`resources/read` 返回完整 HTML5 文档（text 或 base64 blob），mimeType `text/html;profile=mcp-app`；**事实标准是单 HTML 内联一切**（官方示例全部 vite-plugin-singlefile）；
- CSP 只能挂资源 `_meta.ui.csp`（`connectDomains/resourceDomains/frameDomains/baseUriDomains` 四个白名单），**默认即 `connect-src 'none'` + 内联脚本样式 + `img-src 'self' data:`**——恰好是本项目 deck/editor 的形态；
- **能力检测**：MCP 主 `initialize` 的 client capabilities `extensions["io.modelcontextprotocol/ui"].mimeTypes` 含 `text/html;profile=mcp-app`；官方指引（Graceful Degradation）：带 UI 的工具 MUST 同时返回有意义的纯文本 `content`，不支持的宿主自动按普通工具执行。

### 2.3 View 侧关键 API（`App` 类）

| 方法 | 线路 | 语义 |
|---|---|---|
| `callServerTool({name,arguments})` | `tools/call`（host 代理） | View 读写 server 状态，**不经过模型** |
| `sendMessage({role:"user",content})` | `ui/message` | **注入会话、触发 agent 新回合**（host MAY 求用户同意） |
| `updateModelContext({content})` | `ui/update-model-context` | 只写模型未来上下文、**不触发回合**，覆盖式只发最后一份 |
| `ontoolinput / ontoolresult / onhostcontextchanged / onteardown` | host→view 通知 | 拿工具参数/结果、主题容器变化、卸载钩子 |
| `getHostCapabilities()` | 握手结果 | 能力位：`message{text,image…}`、`updateModelContext`、`openLinks`、`downloadFile`、`serverTools`、`sandbox`、`sampling` 等 |

`sendMessage` 与 `updateModelContext` 的语义区分是轨 A 设计的关键：前者 = "敲门唤醒 agent"，后者 = "留便条给下一回合"。

### 2.4 沙箱约束（直接影响 editor.html 适配）

- View 在**异源双 iframe 沙箱**里，不能访问父页面、默认不能 fetch 任何网络、不能读本地文件、不能直接下载（须 `ui/download-file` 由 host 中介）；
- 推论：widget 里 `src="assets/xxx.png"` 相对路径无法解析，assets 必须经 `callServerTool` 中转（默认）或显式 CSP 声明的 loopback 静态服务直读（宿主验证后启用）——这是轨 A 最大的适配点（见 §5.7.2 双方案）。

## 3. Cowart 范式提炼

可借鉴（七条）：

1. **服务端注入桥脚本**：构建时把 ext-apps App bundle 内联 + 注入 `window.cowartMcp` 门面（`sendFollowUpMessage/callServerTool/getHostCapabilities/…`，各带超时），View 源码不依赖 SDK 包——editor.html 零构建红线可保；
2. **存储目标经 tool result 下发**（`structuredContent`/`_meta.widgetData` → `ontoolresult`），不用 URL 传参——iframe 无地址栏；
3. **双轨客户端抽象**：每个函数 `hasBridge() ? callServerTool : fetch(localhost)`，同一套 UI 两种宿主跑；
4. **状态同步 = 文件 + 轮询**（widget 250ms/500ms 防抖写，1600ms 轮询拉），无推送通道也能工作；
5. **SKILL 即 widget 协议说明书**：把选区文件语义、工具调用顺序写进技能，widget 与 agent 零直接通信；
6. **发布纪律**：CSP 静态断言（禁外链 script/iframe/fetch 未 guard）、产物 sha256 manifest 提交 Git、冷启动探针；
7. **写冲突用"拒绝破坏性丢失"**而非锁（图片未确认删除拒写）。

不适用（六条，不得照抄）：

1. Cowart 无推送、接受轮询，因为它的状态变更低频；我们的 intent 状态机事件更高频，轮询只做兜底（§5.6）；
2. Cowart 无会话/凭证/多 consumer 概念；我们的 attempt fence、CAS、journal 必须保留在核心层；
3. Cowart 降级策略是"无桥即报错"；我们是三通道保存哲学，降级 = 换通道不是砍功能；
4. Cowart 是"widget 主写 + agent 偶插"；我们双向高频改同一 HTML，冲突模型不能简化；
5. `sendMessage`（其 `sendFollowUpMessage`）在不同宿主上不稳（Cowart 自己加 8s 超时 + 能力探测）——**唤醒语义不能作为唯一通道**，intent 必须持久化入队；
6. 6.4MB 单文件 widget 是 React+tldraw 全内联的代价；我们 editor.html 416KB + 注入 bundle（约 350KB）仍在合理范围，但要设体积门禁。

## 4. 总体架构

### 4.1 四态宿主模型（editor.html）

检测顺序（前者优先）：

1. **ext-apps 态**：`window.pptxMcp` 存在（server 投递 HTML 时注入的门面脚本）——宿主内 iframe；
2. **Bridge 态**：URL fragment `brt+session` 或 sessionStorage 凭证——独立浏览器窗口 + daemon；
3. **嵌入态**：`window.parent !== window`——宿主 postMessage 协议（现有 harness 通道）；
4. **裸静态态**：探测伴随服务 `/api/health`，否则下载导出。

> 注意 ext-apps 态下 `window.parent !== window` 也成立，检测顺序必须先于嵌入态；且 ext-apps 沙箱异源，postMessage 嵌入协议在沙箱里**不可用**（宿主不会转发 `pptx-html:*` 消息进沙箱），两态互斥无歧义。

### 4.2 进程架构对比

**轨 B（现状，不动）**：

```
Agent ←MCP stdio→ bridge_mcp.py ←loopback HTTP(mgmt bearer)→ daemon(BridgeCore+HTTP+SSE+SQLite)
                                                            ↑ loopback HTTP(browser bearer)+SSE
                                                     独立浏览器 editor.html
```

**轨 A（新增）**：

```
Agent ←MCP stdio→ bridge_mcp.py（检测宿主能力后进程内嵌 BridgeCore，不起 HTTP 端口）
                        ↑ MCP tools/call（标准）
Host（Claude/未来 Kimi Code）— AppBridge ←postMessage JSON-RPC→ iframe 沙箱 editor.html
```

要点：

- **server 侧继续用 Python 标准库 + 官方 `mcp` 包实现，不引入 TS SDK**。ext-apps 的 server 侧只是 `_meta.ui` 元数据 + `ui://` 资源 + capabilities 读取，全是协议字段；官方 SDK 是 TS 生态便利层。
- 轨 A 下 `bridge_mcp.py` 从"daemon 薄代理"变为"直接持有 BridgeCore 实例"（BridgeCore 与 HTTP 层本就分离，dispatch 在 `BridgeHTTPServer`）；loopback HTTP / SSE / 凭证 / 心跳 / lease / bootstrap 票据**整层不启动**。
- SQLite 状态库仍用（intent 队列、attempts、草稿的真相源），只是不再经 HTTP 暴露。

### 4.3 分层职责（迁移后）

| 层 | 内容 | 轨 A | 轨 B |
|---|---|---|---|
| agent 面 | MCP 工具声明 | 扩展工具面（§5.2） | 现有五工具 |
| 核心面 | BridgeCore 状态机/验证/CAS/Git ref | **进程内嵌，原样复用** | daemon 内，原样 |
| 传输面 | 凭证/HTTP/SSE/心跳/lease | **删除** | 保留 |
| 宿主面 | editor.html 宿主适配 | 第四态（pptxMcp 门面） | Bridge 态（现有） |

## 5. 轨 A 详细设计

### 5.1 能力检测与双模注册

`bridge_mcp.py` 在 MCP `initialize` 后读 client capabilities：

```python
ext_apps = (client_caps.get("extensions", {})
            .get("io.modelcontextprotocol/ui", {})
            .get("mimeTypes", []))
ui_ok = "text/html;profile=mcp-app" in ext_apps
```

- `ui_ok=True`：注册轨 A 工具面（`open_editor` 挂 `_meta.ui.resourceUri` + 一组内部工具），进程内嵌 BridgeCore；
- `ui_ok=False`：现有五工具 + daemon 模式，行为逐字节不变；
- 两种模式同一进程不二态共存（一次会话一种轨），`get_status.capabilities` 增加 `track: "ext-apps"|"bridge"` 字段供观测。

### 5.2 工具面映射

| 轨 B（五工具） | 轨 A | 说明 |
|---|---|---|
| `open_editor` | `open_editor`（挂 `_meta.ui`，唯一带 UI 的工具） | 立即返回，不阻塞；`structuredContent` 带 session/deck/brief_options 给 widget；`content` 给 agent 文本摘要 |
| `await_intent`（阻塞） | **消除**；新增 `take_intent`（非阻塞，立即返回 pending intent 或空） | UI→agent 方向改由 widget `sendMessage` 敲门（§5.6 时序） |
| `push_update` | `push_update`（不变） | 验证证据模型、CAS 发布原样 |
| `get_status` | `get_status`（不变）+ widget 侧轮询用 | |
| `close_session` | `close_session`（不变） | |
| （daemon HTTP 端点，非 MCP 工具） | `read_deck` / `save_deck` / `read_asset` / `write_asset` / `submit_intent` / `cancel_intent` / `retry_intent` / `query_intents` / `list_drafts` / `save_draft` / `list_versions` / `rollback` | 均 `visibility:["app"]`（对模型隐藏，仅 widget 经 `callServerTool` 可达）——等价于轨 B 的 `/api/*` 浏览器端点 |

红线更新（AGENTS.md）：「恰好五个工具」改为「**轨 B 恰好五个工具；轨 A 工具面扩展但 `open_editor` 仍是唯一带 UI 的入口、唯一面向模型的创作入口**」。editor-first 原则两轨一致。

### 5.3 widget 注入：`window.pptxMcp` 门面

- 预构建产物 `tools/ext_apps_bundle.js`：从 `@modelcontextprotocol/ext-apps` npm 包提取 `App` 浏览器 bundle + 门面脚本（Cowart `build-release-artifacts.mjs` 手法），**构建产物提交 Git + sha256 manifest**，运行时零 npm 依赖（与 bridge "daemon 不依赖 MCP 包"的红线精神一致——依赖在构建期）；
- server 在 `resources/read` 投递时在 editor.html 的 `</head>` 前注入（`</script` 转义 `<\/script`），**editor.html 源文件本身不含 SDK**；
- 门面 API（对齐 Cowart 门面，超时默认 30s）：

```js
window.pptxMcp = {
  ready,                      // Promise<hostContext>，ui/initialize 完成后 resolve
  callTool(name, args),       // → app.callServerTool
  notifyAgent(text|content),  // → app.sendMessage（敲门，不保证到达）
  setModelContext(text),      // → app.updateModelContext（便条）
  onToolResult(cb),           // open_editor 的 structuredContent 入口
  onTeardown(cb),             // 存草稿/状态
  hostCapabilities(),         // 能力探测（message.image 等）
}
```

### 5.4 editor.html 第四态改造点（最小侵入清单）

| 位置（现状） | 改动 |
|---|---|
| `bridgeParseLaunch()`（editor.html:7260）旁 | 加 `pptxMcpParseLaunch()`：`window.pptxMcp` 存在 → ext-apps 态，等 `ready` 拿 `onToolResult` 的 session 上下文 |
| `bridgeSend()`（:7637 三态分流） | 加第四臂：ext-apps → `callTool("submit_intent",…)` + `notifyAgent(...)` |
| `saveDeck()`（:4898 embedded 分支旁） | 加 ext-apps 臂：`callTool("save_deck",{html,base_revision})`，复用 CAS receipt 语义 |
| `bridgeApplyEvent()`（SSE 消费，:7537） | ext-apps 态无 SSE → 等价物为 `setInterval` 轮询 `callTool("get_status")`（默认 2s，空闲退避 10s），diff revision/intent 状态后走同一状态合并函数 |
| 图片加载 | ext-apps 态下 assets 引用经 `callTool("read_asset")` 换 data URI / blob URL（§5.7.2） |
| 桥栏（:750-812） | 复用，数据源从 SSE 换轮询； Bridge 态专属元素（revision 点等）保持 |
| 顶栏显隐（:7675 起） | ext-apps 态隐藏"打开浏览器"类入口 |

### 5.5 通道映射总表

| 轨 B 机制 | 轨 A 等价物 | 备注 |
|---|---|---|
| `await_intent` 阻塞调用 | widget `notifyAgent()` → agent 新回合 → `take_intent` 非阻塞取 | **超时问题消失** |
| `POST /api/intent` | `callTool("submit_intent")` | 同一 `accept_intent` 校验与 SQLite 入队 |
| SSE 七类事件 | 轮询 `get_status` + `onToolResult`/`onhostcontextchanged` | 高频事件退化为 2s 轮询（Cowart 1.6s 先例） |
| `POST /api/save` | `callTool("save_deck")` | CAS/receipt 语义不变 |
| browser/management 两级凭证 | **删除**（宿主沙箱 + visibility:["app"] 担保） | |
| 浏览器心跳 / page_online | **删除**（`onteardown` 即离线信号） | |
| waiting lease 90s | **删除**（无等待租约语义） | processing owner/fence 保留 |
| bootstrap 票据 | **删除** | |
| `pptx-html:assets-changed` 热刷新 | 轮询发现 revision 变化 → 重读 deck/asset | |

### 5.6 关键时序：脑暴 intent（轨 A）

```
1. agent 调 open_editor(view="brief", brief_options=…)          [MCP 标准调用，立即返回]
2. host 读 ui://editor 资源 → 沙箱渲染 editor.html（含注入门面）
3. widget: ui/initialize → initialized → host 发 tool-input/tool-result
4. widget: onToolResult 拿 {session_id, deck 上下文, brief_options} → 渲染脑暴页
5. 用户提交脑暴 → widget: callTool("submit_intent",{type:"brief",…})   [状态机入队，持久化]
                 → widget: notifyAgent("脑暴已提交，intent <id>，请调 take_intent 处理")
6. agent 新回合 → take_intent → attempt 副本（_copy_attempt 不变）→ 生成 → push_update(complete+验证证据) → CAS 发布
7. widget 轮询 get_status 发现 intent succeeded / revision 变化 → 加载新 deck 渲染
```

要点：**第 5 步双通道**——`submit_intent` 保证持久化不丢（`notifyAgent` 被宿主拦截/用户拒绝也不丢 intent），`notifyAgent` 只负责唤醒时延。agent 被任何方式唤醒后 `take_intent` 都能发现 pending——语义等价于轨 B "timeout 后结束回合、新消息触发重新 await"，但无阻塞。

### 5.7 难点与设计决策

**5.7.1 deck HTML 加载**：widget 不能读文件 → `callTool("read_deck")` 经宿主中转。54 页 deck 约数百 KB–数 MB，JSON-RPC 传输可接受；`save_deck` 同路反向。大 payload 经 postMessage 结构化克隆，无序列化瓶颈担忧，但设门禁：deck > 20MB 时 `read_deck` 返回分段游标（预留，不一期实现）。

**5.7.2 assets 图片（最大适配点）**：先澄清概念——"插件在本地"指的是 **MCP server 进程**在本地（它能自由读写 `assets/`）；但 widget（View）不在 server 进程里，它被**宿主**渲染在异源沙箱 iframe 中（web 宿主的沙箱 origin 是宿主的远程 https 域名），浏览器不允许该页面触碰本地文件系统；规范默认 CSP `img-src 'self' data:` + `connect-src 'none'`（`apps.mdx:275-284`），全文无 `file://`/本地文件通道（已全文检索确认）。widget 与本地之间唯一的管道是宿主中转的 MCP JSON-RPC。由此有两条路线：

- **方案 a（默认，官方范式，跨宿主保证可用）**：`callServerTool("read_asset",{path})` 返回 base64 → `URL.createObjectURL(Blob)` 替换 src——官方二进制资产同款范式（`examples/video-resource-server/src/mcp-app.ts:102-113`、`pdf-server/src/mcp-app.ts:3258`）。内存缓存 + 按 revision 失效；序列化保存时**还原为 `assets/` 相对路径**（编辑契约不变，磁盘上 deck 纯净性不破）；首屏用 IntersectionObserver 按需解析可见页图片。图片上传走 `callTool("write_asset")`（等价现有 `/api/bridge/asset`，同名覆盖 + `data-image-state="uploaded"` 语义不变）。代价：base64 +33% 体积、多图首屏延迟。
- **方案 b（loopback 资产服务，P4 宿主实测后按宿主启用）**：server 侧保留一个极简**只读**静态服务（固定端口如 8642，占用冲突则整会话回落方案 a），资源 `_meta.ui.csp.resourceDomains` 声明 `http://127.0.0.1:8642`（规范只要求 host 不放行未声明域名、允许加严，不禁止 loopback 源，`apps.mdx:286`），widget 里 `<img src>` 直读。优点：图片语义零改写（编辑器序列化/契约完全不动）、浏览器原生缓存、无 base64 膨胀。风险：① CSP 无端口通配符，必须固定端口；② 宿主 "MAY further restrict"，loopback 条目可能被剥离；③ https 沙箱 origin 加载 http loopback 的混合内容行为——Chromium 系视 127.0.0.1 为可信源可加载，WebKit 系未验证；④ 传输层"整层删除"退让为一个只读静态端口。
- **一期决策**：方案 a 保底实现（可用性优先）；方案 b 做能力探测（会话开始发探针图，`onerror` 即整会话回落方案 a），P4 真实宿主矩阵验证后按宿主白名单启用。
- **CSP 粒度事实**（决定兜底顺序）：规范最低线只有 `img-src 'self' data:`——**data: URI 是唯一规范级保证**；`blob:` 不在最低线，但官方参考宿主放行（`examples/basic-host/serve.ts:82`）且 video/pdf 示例都依赖 `createObjectURL` → 事实标准，仍属宿主可加严项，门面层留 data: URI 终极兜底。
- **烙入大图专项**：烙入页是整页位图（契约下限 2560×1440，单张 PNG 常 2–5MB），混合展示 deck 可能几十张——全部经 base64 中转（+33%）不可行。策略：按可见页懒加载；烙入图落盘即存展示档（WebP/JPEG）与源档（PNG）双份；方案 b（URL 直读）对烙入页价值最大，白名单宿主上烙入图优先走 URL。
- **三层兜底**：小图（图标级 <100KB）data: 内联直出 → 默认 blob: 中转（read_asset）→ 白名单宿主方案 b URL 直读；任一层失效向下一层回落。**图片在轨 A 任何宿主都能显示——约束不在"能否显示"，在"字节走哪条管道"**；生成/烙入/导出全部发生在 agent 侧本地文件系统，不受沙箱影响。

**5.7.3 状态持久化跨 widget 生命周期**：宿主可随时 teardown widget（`onteardown`）。未提交编辑 → 现有 IndexedDB 本地持久化逻辑原样可用（沙箱 iframe 通常允许 localStorage/IndexedDB，但**不保证**——门面对存储失败降级为 `callTool("save_draft")` 服务端草稿，复用现有 draft 机制）。重新打开时 draft 恢复逻辑不变。

**5.7.4 widget 实例纪律**：同一 deck 只允许一个 editor widget 实例。借鉴 Cowart SKILL 条款：`open_editor` 已在会话内打开过则返回现有状态 + `updateModelContext` 提示，不重复渲染（宿主对同 URI 多实例行为不一，不依赖）。

**5.7.5 `notifyAgent` 不可信**：host MAY 求用户同意、Cowart 实测该能力跨宿主不稳。设计纪律：**任何 agent 需要知道的事都必须先落状态机（submit_intent/save_deck），`notifyAgent` 只是时延优化**。agent 侧 SKILL 增加条款：用户表达"等编辑器反馈"意图后若长时间无下文，主动 `take_intent` 查一次。

**5.7.6 主题/容器适配**：`onhostcontextchanged` 携带宿主 theme(light/dark) 与 `containerDimensions`——editor.html 工作台外层 chrome 跟随宿主主题（deck 渲染区不受影响，deck 是产物）；`requestDisplayMode("fullscreen")` 在编辑场景主动申请（能力探测后）。

## 6. 轨 B 保留面（明确不改清单）

- 五工具 MCP 面、`/api/*` 端点、SSE 协议、两级凭证、心跳、lease、bootstrap——**逐字节不动**；
- `tests/harness/r_bridge_check.py`（1122 行全协议验收）、`test_bridge_core.py`、`run_e2e.py` T12/T29——**零改动必须全绿**（回归红线：轨 A 实现不得触碰这些测试的断言面）；
- 嵌入态 postMessage 协议与裸静态态——不动。

## 7. 能力检测决策树（agent 视角，写进 SKILL）

```
调 open_editor → 观察返回与环境：
├─ MCP initialize 时宿主声明 io.modelcontextprotocol/ui → 轨 A
│   （open_editor 返回 content + widget 由宿主渲染；agent 后续用 take_intent/push_update）
├─ 未声明但五工具可见 → 轨 B（现状：open_editor 返回 URL，await_intent 阻塞等待）
└─ 工具不可用/用户拒绝编辑器 → 说明原因后降级纯 coding（现有红线）
```

agent 不需要自己"选择"轨道——server 按宿主能力注册不同工具面，agent 看到的工具集本身就是轨道信号。

## 8. 测试与验收

1. **harness 第三组宿主模拟器**：`tests/harness/` 新增 ext-apps host 模拟器（复用 harness.html iframe 骨架 + 实现 AppBridge 侧最小协议：`ui/initialize` 应答、tool-input/result 转发、`ui/message` 捕获、CSP 头注入），驱动 editor.html ext-apps 态全操作面（brief 提交/保存/图片替换/intent 生命周期）；
2. **核心回归零改动**：`test_bridge_core.py` + `r_bridge_check.py` + `run_e2e.py` 现有 61 项全绿（BridgeCore 复用的证明）；
3. **双模注册单测**：模拟两种 client capabilities，断言注册的工具集差异；
4. **CSP 静态断言**：构建期校验 editor.html + 注入 bundle 无外链 script/iframe、fetch 均经门面（Cowart `assertCspCompatibleStaticHtml` 同款）；
5. **真实宿主验收矩阵**：Claude Desktop（已支持 ext-apps）作为首个真实宿主；Kimi Code 支持后补验； Goose 可选。未实测前文档一律记 NOT_RUN（AGENTS.md 证据纪律）。

## 9. 分期路线

| 期 | 内容 | 验收 |
|---|---|---|
| P1 适配层抽取 | editor.html 抽出统一宿主适配层（四态检测 + `bridgeSend`/`saveDeck`/资产解析重构为策略接口），**行为零变化** | 现有 e2e 全绿 |
| P2 server 双模 | bridge_mcp.py 能力检测 + BridgeCore 进程内嵌模式 + `ui://` 资源与注入门面 + visibility:["app"] 工具组 | 双模注册单测 + r_bridge_check 全绿 |
| P3 widget 通道 | editor.html ext-apps 态实现（读 deck/保存/图片/轮询/notifyAgent） | harness 第三组全绿 |
| P4 真实宿主 | Claude Desktop 端到端（脑暴→生成→发布→编辑→再生成） | 验收证据入 docs/test_acceptance/ |
| P5 插件打包（正交） | 按 Agent Plugins v1.0.0 打包（research 路线 D），widget 三件套入插件产物 | 冷启动探针 |

## 10. 风险与未决

1. **Kimi Code 尚无 ext-apps 支持**（2026-10-14 调研结论）——轨 A 首期价值在 Claude 等已支持宿主 + 给 Kimi Code 的需求输入；轨 B 在 Kimi Code 上仍是唯一路径，**bridge 维护负担不因轨 A 消失**；
2. **各宿主 ext-apps 实现完成度参差**（`sendMessage` 同意策略、displayMode、CSP 严格度）——P4 需逐宿主出兼容矩阵，门面层留能力探测降级；
3. **轮询替代 SSE 的时延回归**：intent 状态反馈从推送变 2s 轮询，可接受（Cowart 先例）但桥栏"任务进行中"反馈要在 UI 上如实表达时延；
4. **大 deck 经 JSON-RPC 的宿主限制**：个别宿主对 postMessage 载荷/工具结果大小有限制，P4 实测后决定是否启用 `read_deck` 分段；
5. **assets 图片传输路径**：方案 a（桥内 base64 中转）在 54 页 deck 数十张图下的首屏性能待 P3 实测调优；方案 b（loopback 静态服务 + CSP `resourceDomains`）依赖宿主不收紧 loopback CSP 条目与 https→loopback 混合内容行为，P4 宿主矩阵验证前不作为默认；
6. **Widget 内直接编辑 + agent 并发的冲突模型**：轨 B 依赖"独立浏览器窗口里人是唯一写者、agent 走 attempt 副本"；轨 A 同语义（widget 保存走同一 CAS），但 widget 生命周期不受我们控制（宿主可 teardown），`onteardown` 存草稿是唯一防线——宿主若不调 teardown 强杀 iframe，未存编辑丢失。接受该风险（与 web 应用同级），IndexedDB 持久化兜底。

## 参考

- 官方规范：`~/Desktop/ext-apps/specification/2026-01-26/apps.mdx`（github.com/modelcontextprotocol/ext-apps @ 82221c0，SDK 2.0.3）
- Cowart 实现：`~/Desktop/Cowart/`（注入门面 `mcp/lib/widget-resource.mjs`、双轨客户端 `src/cowartClient.js`、构建 `scripts/build-release-artifacts.mjs`）
- 前置调研：`mcp-bidirectional-research.md`
- 对接面事实：bridge_core/bridge_mcp/editor.html 行号引用见本文 §4–§5（2026-10-15 盘点）
