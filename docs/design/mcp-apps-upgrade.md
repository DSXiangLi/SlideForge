# MCP Apps 升级设计（真实宿主实证版）

> 日期：2026-10-19 初稿 → 2026-10-20 两轮修订。状态：**待评审**。
> 本文取代 `ext-apps-dual-track.md`（2026-10-15，未实施）——该版写于"宿主支持性未知"阶段，
> 其 §1 动机、§2.4 沙箱假设、§5.2 工具面扩张、§7 能力检测决策树均被实测修正。
>
> **修订记录**
> - **10-20 一轮**：重读 SproutHarness `feature/mcp-apps` 分支，宿主能力面已由 **render-only 升到 interactive**（`ui/message`、`ui/update-model-context`、`ui/open-link`、`ui/download-file`、`notifications/message`、`size-changed`、`ui/resource-teardown`、`hostContext`、`_meta.ui.permissions` 全部落地）。初稿"`ui/message` 很可能 reject""下载全废""剪贴板只能兜底"三条结论被推翻。
> - **10-20 二轮（本轮）**：一致性自查后修五处 ——
>   ① **§5.5 推翻重写**：初稿把便条（`updateModelContext`）放在"提交路径"上是错的（用户指出）；改为**三通道模型**（状态机=待办 / 敲门=触发 / 便条=背景）。
>   ② **新增 §5.10 异步批注与版本并发**：识别出**指令型意图被错误施加写入前置**这一协议硬伤，含死锁时间线、五条设计、以及 `await_intent` 的 `conflict` 毒化行为。
>   ③ **§3.1 能力读取从"推断"升级为"实测可用"**（`ClientCapabilities` 未声明 `extensions` 字段，但 `extra="allow"` 保留且可读；`ServerSession.client_params` 可取），并补一条**注册期早于 `initialize`、只能在调用期分流**的硬约束。
>   ④ **§4.2 轨道判定补三条硬化**：仲裁自解除（仅当本会话从未出现 UI 信号时启用一次，避免轨 B 白付时延）、`mode_hint` 可能恒为 `unknown`（设计必须在此前提下正确）、已决则不再等待。
>   ⑤ **§4.2/§6.2 新增轨 A 实现约束**：`BridgeCore.await_intent` 是同步轮询，轨 A 内嵌时不得直接同步调用（会堵住服务 View 的事件循环）。
> - **10-20 三轮（P0.5 实施）**：按用户授权"按推荐决策来"落五项裁决（§9），并实施 §5.10 **D1 + D2** ——
>   `tools/bridge_core.py`（`INSTRUCTION_INTENT_TYPES` + `accept_intent` 归一化 + `await_intent` 认领归一化不毒化 + `anchor` payload 校验）、
>   `editor.html`（`bridgeSubmitIntent` 指令型解耦"先存后交"、上报 `anchor={revision,dirty}`）、
>   `tests/harness/test_bridge_core.py`（+6 个正负例，38 → 44）。**D3/D4 属 agent/SKILL 侧，未实施。**
>   实施中发现并纠正了本设计自己的一处错误：`intents.base_revision` **是发布 CAS 基线**（`_publish` 直接用它），
>   不是信息字段——所以"指令型跳过校验"必须实现为**归一化**而非"忽略"，否则发布阶段会 CAS 失败（§5.10.1）。
> - **10-21 一轮（P1 + P2 + P3 实施）**：D3/D4 落进 `skills/html-pptx/SKILL.md`（§3.1 新增小节）；
>   `editor.html` 抽出宿主适配层 `hostBridge`（四态策略面 + `mcpApp*` 轨 A 实现）；
>   新增 `tools/bridge_dispatch.py`、`tools/build_ext_apps_bundle.py` + `tools/ext_apps_facade.js` + 产物 `tools/ext_apps_bundle.js`（带 sha256 manifest）；
>   `tools/bridge_mcp.py` 落 13 个 app-only 工具 + View 资源 + 列举期双模 + 仲裁相位；`tools/bridge_core.py` 落 `attach_view`/view 信号/三条只读路由/open_browser `auto`。
>   **实施偏差九条见 §10**（含"轨 A 传输层并没有整层不启动"与"仲裁落在 MCP 层而非 core"两处对本文架构描述与 §6.2 的修正）。
>
> **证据来源**（均为直接读取，非转述）：
> 1. `~/Desktop/ext-apps` — 官方 `@modelcontextprotocol/ext-apps` **2.0.3**，稳定规范 `specification/2026-01-26/apps.mdx`（SEP-1865）、四项迁移技能 `plugins/mcp-apps/skills/*`；
> 2. `~/Desktop/SproutHarness/.claude/worktrees/feature+mcp-apps` — `docs/howto/mcp_apps_development_guide.md`（576 行）、`docs/design/agent/mcp_apps_design.md` §十 能力矩阵（1436 行）、`agent/webui.html`（能力处置表 `:924-985`、`_buildHostContext :5040-5072`、`_takeAppContextFor :5274-5287`、App 消息确认卡 `:5288-5360`、handler 实现 `:5360-5510`）、`mcp/sandbox.py`、`mcp/client.py:145-186`、`agent/graph.py:40-140,746-778`、`defaults.py:85-123`、`tests/test_mcp_apps_host_matrix.py`；
> 3. `~/Desktop/Cowart` — 已上线 widget 的宿主接入手法；
> 4. **本机 Kimi Code 2.2.0 二进制实测**（SEA 内嵌源码字符串检索）；
> 5. **Playwright 沙箱能力矩阵实测**（已固化为 `tests/harness/z_sandbox_matrix.py`）；
> 6. **本项目 bridge 代码核对**：`tools/bridge_core.py`（`accept_intent :1026-1052`、`await_intent :964-1013`、`retry_intent :1064-1108`、线程模型 `:439-447`）、`tools/bridge_mcp.py`（187 行全文）、`editor.html`（`bridgeSubmitIntent :7599-7615`、`bridgeHandleDeckChanged :7458-7469`、`bridgeSubmitIntent` 的前置保存 `:7600`）、回归覆盖（`grep REVISION_CONFLICT` 全仓）。
>
> **标注纪律**：`【实测】` = 本轮有可复现证据；`【源码】` = 读到的实现代码；`【设计】` = 本文提出的决策，尚未实现；`【未验证】` = 明确未测。

---

## 0. 一句话决策

**传输层可替换，状态机不动；轨道判定必须靠实证，不能靠能力声明。**

`BridgeCore`（intent 队列 / attempt 隔离副本 / 验证证据 / CAS 发布 / Git 隔离 ref / publication journal）作为宿主无关的整体**原样保留**；其外的"远程不受信前端"传输机械（loopback HTTP、SSE、两级凭证、心跳、lease、bootstrap 票据）在 MCP Apps 轨道上**整层不启动**，改为宿主中转的 `postMessage` JSON-RPC + `visibility:["app"]` 工具组。`editor.html` 新增第四运行态，单文件零构建红线不破。

**升级不是替换，是并行加轨**：Kimi Code 2.2.0 实测不支持 MCP Apps，今天仍是唯一宿主，轨 B 必须逐字节保留。

**但有一个双轨共用的协议硬伤必须先修**（§5.10）：指令型意图（`brief`/`design`/`anno`）被错误地施加了写入前置（`base_revision` 强校验），导致"用户在 agent 工作期间继续批注"这一正常用法会走到需要用户介入的死锁。这与轨 A/B 无关，**建议先于本体升级单独修**。

---

## 1. 本轮新增的实证事实

### 1.1 宿主侧：两个方向相反的确凿事实

| 宿主 | MCP Apps 支持 | 证据 |
|---|---|---|
| **Kimi Code 2.2.0**（当前唯一宿主） | **不支持，且是三层不支持** | 【实测】① 客户端 `new Client({name,version})` **不传 capabilities**，SDK 回填 `{}` → 既不声明 `io.modelcontextprotocol/ui`，也不声明 roots/sampling/elicitation/experimental；② 自研 MCP 客户端只实现 `listTools()`/`callTool()`/`ping()`，**`listResources` / `readResource` 零命中** → 即使注册了 `ui://` 资源也拉不到；③ 二进制内 `io.modelcontextprotocol/ui`、`ui://`、`resourceUri`、`ext-apps`、`outputTemplate` 字符串**命中数全为 0** → 无 widget 渲染路径 |
| **SproutHarness**（自研框架，分支 `feature/mcp-apps`） | **已实现，能力面已到 interactive；仍与官方规范有已知偏差** | 【源码】`webui.html` 建 iframe + 完整 AppBridge 能力处置表；`mcp/sandbox.py` 服务不可信 HTML + CSP 头；`graph.py:746` 检测工具 `ui_meta.resource_uri` 自动拉资源；宿主侧自评仍缺 `structural` / `app-tools` / `isolation` 三类（`mcp_apps_design.md` §10.7） |
| **Cowart**（已有产品） | 依赖 Codex 宿主，无自带宿主 | 【源码】`mcp/lib/widget-resource.mjs` 注入门面 + `src/cowartClient.js` 双通道抽象 |
| **Claude Desktop** 等 | 声称支持 | 【未验证】本机无法实测 |

**宿主侧能力面（10-20 快照）**——即"host 现在真的能做什么"：

| 能力 | 状态 | 语义要点【源码】 |
|---|---|---|
| `ui/message`（View 敲门） | ✅ | 文本块 only；≤4000 字符；**必须用户在聊天面板点「确认发送」才成为一条 user 消息并触发新回合**；≤3 条待确认，超出丢最旧；正在流式输出时进 pendingQueue |
| `ui/update-model-context`（便条） | ✅ | 文本块 only；≤8000 字符；**覆盖式**；`structuredContent` 本轮忽略；**不触发回合，在 `startStream` 内随下一条用户消息附带后清空**（`_takeAppContextFor :5274`） |
| `ui/open-link` | ✅ | http/https 白名单；新标签打开；弹窗被拦 → 返回错误 |
| `ui/download-file` | ✅ | **仅 embedded**（`resource.text` / `resource.blob`）；`resource_link` 明确拒绝；≤20 MB；多条只取第一条 |
| `notifications/message`（`sendLog`） | ✅ | 落宿主日志面板，≤2000 字符 |
| `size-changed` | ✅ | 只跟随高度（宽度不动），钳制到 `maxHeight=1200px` |
| `ui/resource-teardown` | ✅ | 两阶段：iframe 仍挂载时发请求 → 隐藏容器但**不移除** → 等 View 回执（≤5s）→ 才真正拆卸 |
| `hostContext` | ✅ | `theme` 固定 `dark`；`styles.variables` 映射宿主 CSS 变量；`displayMode=inline`、`availableDisplayModes=['inline']`；`containerDimensions.maxHeight=1200`；`locale`/`timeZone`/`userAgent=SproutHarness-WebUI`/`platform=web`/`deviceCapabilities` |
| `hostCapabilities` | ✅ 声明 7 项 | `serverTools{}`、`serverResources{}`、`logging{}`、`openLinks{}`、`downloadFile{}`、`message{text:{}}`、`updateModelContext{text:{}}` |
| `_meta.ui.permissions` | ✅ | 白名单 `camera`/`microphone`/`geolocation`/`clipboardWrite` → iframe `allow` 属性 |
| `resources/list` | ✅ | — |
| `sampling` / `prompts` / `resources/templates` | 🚫 显式拒绝 | 注册说明性拒绝，不静默 |
| `tool-input-partial` / `tool-cancelled` | 🚫 结构性不可能 | **View 只在工具执行完成后才创建**（宿主自认 `structural` 缺口） |
| `host-context-changed` | 🚫 | 无动态上下文；theme 固定 dark |
| View 自请求拆卸 | 🚫 | 通知被丢弃 |
| 异源 sandbox-proxy / owner 隔离 / 身份 | 🚫 | 宿主自认 `isolation` 缺口 |

**推论（本文最重要的判断，两轮修订后依然成立）**：【设计】`capabilities.extensions["io.modelcontextprotocol/ui"]` **既非充分也非必要**——SproutHarness 能渲染 widget 却**不声明**该扩展（重读确认：全仓 `grep io.modelcontextprotocol/ui` **零命中**，即 1018 N17 / R08 仍未落地）。因此**任何以能力声明为唯一门控的轨道选择都会在 SproutHarness 上判错**。轨道判定必须引入实证信号，见 §4.2。

### 1.2 沙箱侧：比 1015 版假设的**更宽松**，但对"状态"**更严苛**

1015 版 §2.4 的假设与实测对照（复刻 SproutHarness 确切配置：`iframe.sandbox='allow-scripts'`、`build_csp_header({})` 的 CSP 头）：

| 能力 | 1015 版假设 | **实测结果** | 影响 |
|---|---|---|---|
| 嵌套 `iframe srcdoc` | 未讨论 | ✅ **可用**（`frame-src 'none'` 不拦 `srcdoc`/`about:blank`） | **重大利好**：editor.html 现有"deck 装进 srcdoc iframe"的渲染架构可原样保留 |
| 相对路径 `<img src="assets/x.png">` | 假设不可用 | ✅ **可用**（no-cors 请求，`img-src 'self'` 命中） | 资产路径比我方假设更宽 |
| `img` 用 `data:` / `blob:` URI | `data:` 保底、`blob:` 存疑 | ✅ **两者都可用** | 三条资产管道全部可行 |
| `URL.createObjectURL` / `new Worker(blobURL)` | 未讨论 | ✅ 可用（`script-src` 含 `blob:`） | 可分片解析大图 |
| `crypto.randomUUID` / `getRandomValues` / `subtle` | 未讨论 | ✅ **全部可用** | **content-hash 计算、SHA-256 净化工序不受影响** |
| `eval` / `new Function` | 未讨论 | ✅ 可用（CSP 含 `unsafe-eval`） | deck 运行时文本引擎可原样工作 |
| `navigator.clipboard` | 未讨论 | ⚠️ 对象存在（不透明源下仍是 secure context）；**宿主已支持声明 `clipboardWrite` → iframe `allow`** | 声明权限 + 试调用 + 纯文本兜底，三层齐全 |
| `fetch()` 相对/同源 | 假设不可用 | ❌ **失败——但不因 CSP，因 CORS**（不透明源 → `Origin: null`，无 ACAO 头） | 若对端补 `Access-Control-Allow-Origin` 且 CSP `connect-src` 放行，**仍可直读**；见 §5.2 方案 b |
| `localStorage` / `sessionStorage` / `indexedDB` / `cookie` | 假设"通常允许，但不保证" | ❌ **全部 SecurityError**（无 `allow-same-origin` → 不透明源） | **必须按"完全无本地存储"设计**，这是 1015 版最大的判断偏差 |
| `window.open` | 未讨论 | ❌ 被禁（无 `allow-popups`）——但 **`ui/open-link` 已补回** | 链接类需求走门面 |
| 文件下载（`<a download>`） | 假设不可用 | ❌ iframe 内被禁（无 `allow-downloads`）——但 **`ui/download-file` 已补回** | 见 §5.9 |
| 文件选择（`showSaveFilePicker`/`showOpenFilePicker`） | 假设不可用 | ⚠️ API **存在但不代表可调用**（`typeof` 仍返回 `'function'`） | **存在性检测是伪检测**，必须试调用 |
| 对照：`sandbox="allow-scripts allow-same-origin"`（官方规范要求，SproutHarness 未采用） | — | ✅ 上表所有 ❌ 项**全部恢复**（含 `fetch` 同源、localStorage、indexedDB） | 规范合规宿主上约束大幅放宽，**故适配层必须按能力检测写，不能硬编码假设** |

**两条硬结论**：
1. **状态不能放本地**。草稿、编辑游标、脑暴暂存全部必须服务端化（`callTool("save_draft")`），`onteardown` 是重要防线（见 §5.3）。
2. **"存在性检测"在本环境是伪检测**。所有宿主能力一律**试调用 + 捕获**，不查 `typeof`、不查 `window.parent !== window`。

---

## 2. editor.html 交互能力全清单

> 行号约定：`E` = `editor.html`（v3.8，7947 行 / 428,149 B / gzip 115 KB）；`B` = `tools/bridge_core.py`（2156 行）；`M` = `tools/bridge_mcp.py`（187 行）。
> 本清单是**升级的输入**：迁移方案必须逐条回答"这一项在 MCP Apps 沙箱下走哪条路"。

### 2.1 五类用户交互能力（A–E，具名 21 项 + 键盘/手势全集）

**A 类 · 内容编辑（本地写入，无 agent 参与）**

| # | 能力 | 入口 → 结果 | 依赖 API | 沙箱判定 |
|---|---|---|---|---|
| A1 | 打开文件 | 顶栏 E:773 / 拖拽 E:3777 / `showOpenFilePicker` E:3755 → 写入 iframe `srcdoc` E:3877 | FSAA + File.text | ❌ 不可用；轨 A 改由 `read_deck` 取 |
| A2 | 就地文字编辑（两段手势） | 首击选中 / 二击编辑 E:4153,4162；`Enter` E:4208 → `contenteditable=plaintext-only` E:4078 → commit + 换行归一 E:4120 | Selection/Range E:4091、`execCommand` 降级 E:4085 | ✅ 纯 DOM，可用 |
| A3 | 文字样式白名单四属性 | `styleBar` E:782 → `applyStyleProp` E:6211 / `applyFontSize` E:6219 | `getComputedStyle`、`input[type=color]` | ✅ 可用 |
| A4 | 图片替换 | 双击 E:4169 / `btnReplaceImg` E:4273 → `replaceImage` E:4626 → 写 `assets/` 同名覆盖 | FSAA 双 picker E:4633,4674、`createWritable` E:4621、FileReader E:4654 | ❌ 落盘路径不可用；改 `write_asset` |
| A5 | 章节目录导航 | 侧栏点击 E:6285,6334、滚动高亮 E:4227、deck 内 `a.nav-link` 拦截 E:4146 | IntersectionObserver E:6262 | ✅ 可用 |
| A6 | 目录侧栏缩略图 + 拖拽排序 | Shadow DOM E:6302,6305、HTML5 拖拽 E:6394 → **改 deck DOM 顺序** E:6421 → `setDirty` E:6432 | `attachShadow`、pointer capture | ✅ 可用 |
| A7 | 三态工作台 | 编辑/批注/翻转 `viewSeg` E:775-778 → `setView` E:6710 / `applyView` E:6719 | — | ✅ 可用 |
| A8 | 双面卡翻面 | `flipBadge` E:867 + `F` 键 E:4203 → `setFlip` 3D E:6631 | `transitionend` E:6658 | ✅ 可用 |
| A9 | 对比质检 | 并排/滑动/差异 E:838-840 → `applyCmpView` E:6763；分割线拖拽 E:7017；热区 E:7032 | — | ⚠️ 可用但**产物载体待设计**（见 §5.11） |
| A10 | 播放动效 | **编辑器无播放功能**：加载即 `__pptxMotion.freeze()` E:4002，序列化 `restoreAll` E:4732 | — | ✅ 可用 |

**B 类 · 设计决策输入（产出"给 AI 的指令"，由 agent 落码）**

| # | 能力 | 入口 → 结果 | intent | 依赖 API |
|---|---|---|---|---|
| B1 | 设计面板四组（主题/节奏/动效/密度） | `btnPanel` E:976,5190；主题卡 + 变体 E:5029；其余三组 E:5087；补充 E:5000 → 复制 E:5180 / 发送 E:5184 | ✅ `design.submitted` E:5186 | clipboard |
| B2 | 需求脑暴浮板（静态/动态两态） | `btnBrief` E:979,5832；静态问卷 E:5219 / 动态校验 E:5295 + 渲染 E:5761；画像卡 E:5541；ask/prefilled/skipped E:5649,5660,5695；"由 AI 决定" E:5640,5726；主题推荐 E:5409；预览 E:6064 → 复制 E:6072 / 发送 E:6077 | ✅ `brief.submitted` E:6083 | clipboard、`fetch` status E:5826 |
| B3 | 批注（框选 → 三层引用） | `批注` E:777 → `setMode` E:4291；框选 E:4339 → 弹窗 E:4438 → 清单 E:4536,4544；复制 E:4605 / 发送 E:4611 | ✅ `anno.submitted` E:4615 | 向 iframe 注入节点、clipboard E:5169 |

**C 类 · 协作意图与产物（必须触达 agent）**

| # | 能力 | 入口 → 结果 | intent / 通道 |
|---|---|---|---|
| C1 | 生图入口三态 | `btnBake`/`btnIllustrate` E:800-801,7674；桥栏 E:808-809 → `requestBake` E:7664 / `requestIllustrate` E:7668 | ✅ Bridge=intent / 嵌入=postMessage / 静态=复制 |
| C2 | 导出（一键转换 + 下载） | `btnConvert` E:7238；下载 deck.pptx / vector.pdf E:7177-7185；重新翻转 E:7139,7198 | ✅ `export-intent` E:7156,7201,7223 |
| C3 | 产物清单 | 导出内页签 E:903-904 | — |
| C4 | 版本历史与回滚 | `btnHistory` E:7773 → 列表 E:7781 → 回滚 E:7836 | ❌ 本地 → 服务端 `list_versions`/`rollback` |

**D 类 · 状态与持久化**

| # | 能力 | 实现 | 沙箱判定 |
|---|---|---|---|
| D1 | 保存（五通道优先级） | Bridge `POST /api/save` E:4879 → 嵌入 postMessage E:4904 → 伴随 `api/save` E:7763 → FSAA 句柄直写 E:4936 / `showSaveFilePicker` E:4949 → Blob 下载 E:4967 | ❌ 后三条全废；轨 A 收敛为 `save_deck` 单通道 |
| D2 | 脏标记 | `setDirty` E:3721 → postMessage E:3731；`beforeunload` E:3745 | ✅ `setDirty` 可用；`beforeunload` 在 iframe 内不可靠 → 靠 `onteardown` |
| D3 | 草稿持久化 | sessionStorage 凭证 E:7269-7282 + **indexedDB 草稿** E:7343-7360,7382 | ❌ **两者全废** → 必须服务端草稿 |
| D4 | 凭证续传 | `location.hash` 读凭证 E:7266 + `history.replaceState` E:7271 | ✅ 机制可用但无意义（iframe 无地址栏） |

**E 类 · 键盘与手势全集**（全部纯 DOM，沙箱无影响）

`Ctrl/⌘+S` 保存 E:4979,4193 · `Ctrl/⌘+Enter` 提交 E:4199 · `Esc` = 取消编辑/框选/翻回/清选/关弹窗/关脑暴 E:4196,4198,4364,4501,5835,6677 · `F` 翻面 E:4203,6671 · `Enter` 编辑选中 E:4208。

### 2.2 出站协议（现状全量）

**HTTP（Bridge，统一 `Authorization: Bearer` E:7291）**

| 端点 | 载荷 | 时机 |
|---|---|---|
| `POST /api/bridge/heartbeat` | `{protocol_version:2,role:'browser',session_id,client_id,dirty,active_edit,draft_pending,revision,last_event_id}` | 首连 + 每 15s（E:7328,7337,7650） |
| `POST /api/bridge/status` | `{session_id}` | 初始化 / 进脑暴（E:7531,5826） |
| `GET /api/events?session_id&after` | —（SSE） | 持续（E:7573） |
| `POST /api/intent` | `{protocol_version:2,intent_id,session_id,type,base_revision,payload,client_ts}` | 提交意图（E:7602,7610） |
| `POST /api/intent/cancel` \| `/retry` \| `/intents/query` | 取消 / 恢复（**重试用 `latestServerRevision`**，E:7638）/ 列表（E:7524） |
| `POST /api/save` | `{session_id,path,html,base_revision,init?}` | 保存（E:4873,4879） |
| `POST /api/bridge/asset` | `{session_id,path,data_base64,base_revision}` | 换图（E:4657） |
| `POST /api/bridge/draft` | `{session_id,client_id,html,annotations,base_revision}` | 草稿（E:7384） |
| `GET/POST /api/versions`、`/api/rollback` | 历史 / 回滚（E:7790,7842） |
| `GET /api/health`、`POST /api/convert`、`/api/convert-status` | 探测 / 单机转换（E:7695,7231,7212） |

**postMessage 出站（`window.parent`，target `'*'`）**：`pptx-html:dirty` E:3731 · `:save` E:4904 · `:annotations` E:4615 · `:brief` E:6083 · `:design` E:5186 · `:export-intent` E:7156,7201,7223 · `:bake-intent` E:7666 · `:illustrate-intent` E:7670。

### 2.3 入站协议（现状全量）

| 通道 | 消息 | 效果 |
|---|---|---|
| SSE（分发 E:7541-7551） | `deck-changed` → 重载 deck（**有脏护栏**，E:7458-7469）· `export-refreshed` → 重取 manifest E:7545,7473 · `assets-changed` → `img ?v=` 热刷 E:7546,7484 · `intent-status` → 合并状态 E:7547,7496 · `notice` E:7548 · `resync-required` → status + query 全量恢复 E:7549,7530 · `server-stop` E:7550 | 断网退避重连 E:7591；401/403 停循环 E:7586 |
| postMessage 入站 E:7903 | `pptx-html:load{html,name?,assetsUrl?,exportManifest?,exportBaseUrl?}` → `openHtml` E:7906 · `assets-changed{files}` → `applyAssetsChanged` E:7911,7891 · `brief-options{options}` → 轻量校验 E:7914 | 嵌入态 |
| 运行时接口 | iframe 内 `__pptxMotion.freeze()` E:4002 / `restore(el)` E:4074 / `restoreAll()` E:4732；本页 `window.BridgeSSEParser` E:7567 | — |

### 2.4 MCP Apps 态的通道缺口（按 10-20 宿主能力面重算）

1. **无 SSE** → 7 类事件全部需要替代（`deck-changed`/`assets-changed`/`intent-status` 是刚需）；
2. **无 postMessage 出站** → 8 类 `pptx-html:*` 需要 `ui/message` / `updateModelContext` / `callTool` 等价物；
3. **无本地存储/草稿** → D3 整条重做（不透明源的硬约束）；
4. **无 FSAA** → D1 收敛为 `save_deck` 单通道；**下载产物已由 `ui/download-file` 补回**（§5.9）；
5. **无服务端 origin** → 图片、export 产物、manifest 全部需要中转管道（§5.2、§5.11）。

**已由宿主新版补回的能力**（初稿曾判为不可用）：剪贴板（`clipboardWrite` 权限）、打开链接（`ui/open-link`）、下载文件（`ui/download-file`）、日志诊断（`sendLog`）、容器高度自适应（`size-changed`）、状态清理（`ui/resource-teardown`）。

---

## 3. MCP Apps 契约（本项目需精确实现的部分）

### 3.1 server 侧（Python，不引入 TS SDK）

ext-apps **没有 Python SDK**，但 server 侧只需协议字段，官方 TS 封装是薄层【源码 `src/server/index.ts:247-310,437-512`】。本项目用现有 `mcp>=1.28` FastMCP 手写等价物：

```python
# 工具：UI 入口（三处必写：ui.resourceUri / ui/resourceUri / 根级 visibility）
@mcp.tool(meta={
    "ui": {"resourceUri": VIEW_URI},
    "ui/resourceUri": VIEW_URI,
    "visibility": ["model", "app"],
})
def open_editor(...) -> str: ...

# 工具：app-only（对模型隐藏，仅 widget 可经宿主代理调用）
@mcp.tool(meta={"ui": {"visibility": ["app"]}, "visibility": ["app"]})
def read_deck(session_id: str) -> str: ...

# 资源：完整 HTML5 文档
@mcp.resource(VIEW_URI, mime_type="text/html;profile=mcp-app",
              meta={"ui": {"csp": {...}, "permissions": {"clipboardWrite": {}}}})
def editor_view() -> str: ...
```

四条硬约束【源码/实测】：

1. `mime_type` 必须含 `text/html`（宿主 `graph.py:128` 强校验），标准标识是 `text/html;profile=mcp-app`；`resourceUri` 三方一致（工具 meta、`@mcp.resource` URI、常量）。
2. **`_meta` 必须双写**：`"ui"` 嵌套与 `"ui/resourceUri"` 扁平**都要写**（宿主 `mcp/client.py:161` 是 `raw_meta.get("ui") or raw_meta.get("ui/resourceUri")`）。
3. ⭐ **`visibility` 必须根级 + `ui` 内双写**（安全相关）。宿主 `_extract_ui_meta` 两条分支不一致【源码 `mcp/client.py:161-186`】：**有 `resourceUri` 时只读根级** `raw_meta.get("visibility", ["model","app"])`，`ui.visibility` 被忽略；无 `resourceUri` 时才读 `ui.visibility`。即带 UI 的工具若只在 `ui.visibility` 写 `["app"]`，会被当成 `["model","app"]` **泄露给模型**（宿主自查 1018 的 N15，重读仍未修）。本项目 13 个 app-only 工具**一律双写**，并在 P2 加断言测试。
4. 工具**无论如何必须返回有意义的 `content` 文本**（规范 Progressive Enhancement 硬条款）——**这正是回退轨的免费实现**。
   **宿主载荷在变，两头都要兼容**：旧行为下宿主 `mcp_result_to_ui_text` 只把 `content` 纯文本投影给 View（剥掉 `structuredContent`），所以给 View 的数据必须 `return json.dumps(...)` 字符串；**2026-10-22 复读宿主源码发现 SproutHarness 正在改成传完整 `CallToolResult`**（新增 `mcp_result_to_view_payload`，`webui.html` 侧 `sendToolResult(resultPayload)` 保留 string 兼容分支），届时 View 还会拿到 `structuredContent` / `isError` / `_meta.viewUUID`。
   本项目的落地：app-only 工具**仍然返回 JSON 文本**（不是靠文本而是因为这是 Progressive Enhancement 的正解），而 `window.pptxMcp` 门面**两条路都认**——优先 `structuredContent`（并拆掉 FastMCP 对字符串返回值的 `{result:"<json>"}` 包装），解析失败再回落 `content` 文本；`isError` 时从 structured 与文本两处找 `error.{code,message,details}`。见 `tools/ext_apps_facade.js`。

**能力协商**（本轮从"推断"升级为可实施）【实测】：
- `mcp` 1.28 的 `ClientCapabilities` **未声明 `extensions` 字段**，但 `model_config extra="allow"` → 传入的 `extensions` 被保留在 `model_extra` 中且 `model_validate` 可原样往返；`mcp.types` 侧已实测通过。兜底路径需要读时用 `caps.model_extra.get("extensions", {})` 而不是 `getattr`。
- FastMCP 侧可取：`Context.request_context.session.client_params.capabilities`（`ServerSession.client_params` 已确认存在）。
- ⚠️ **注册期早于 `initialize`**：工具注册发生在服务器启动时，`initialize` 之后才到。因此**不能按能力注册不同的工具集**（1015 版 §5.1 的双模注册不可行），**只能在调用期分流**——这正是 §4.2 用 `mode_hint` + 实证信号而非"注册两套工具"的原因。
- 由于 §1.1 的结论（声明非充分非必要），**能力协商只作为乐观提示，不作为门控**。

**CSP 与权限声明**（本项目实际需要）【设计】：

```json
{"ui": {
  "csp": {"resourceDomains": ["<loopback 资产服务，方案 b，可选>"]},
  "permissions": {"clipboardWrite": {}}
}}
```
- View HTML 自身**不含任何外链**（现状全文零外链脚本/字体/CDN），**默认 CSP 即够用**——不需要 `unpkg.com`（SproutHarness 两个示例 server 之所以要它，是因为从 CDN `import` SDK；本项目走**内联 bundle**，见 §6.3）；
- `frame-src 'none'` 对本项目无害（实测 `srcdoc` 不被拦）；
- `permissions` 经宿主白名单过滤后转成 iframe `allow` 属性。

### 3.2 View 侧

editor.html **不引入 npm 依赖、不改构建**：SDK 以预构建 bundle 形式由 server 在投递资源时注入（Cowart 手法【源码 `build-release-artifacts.mjs:113-149`】），暴露 `window.pptxMcp` 门面，editor.html 只依赖门面。

门面 API【设计】：

```js
window.pptxMcp = {
  ready,                          // Promise<hostContext>
  callTool(name, args),           // → app.callServerTool
  notifyAgent(text),              // → app.sendMessage（敲门；需用户确认）
  setModelContext(text),          // → app.updateModelContext（便条；背景状态镜）
  downloadFile(uri, mime, bytes), // → app.downloadFile（embedded resource 形态包装）
  openLink(url),                  // → app.openLink（http/https）
  log(level, msg),                // → app.sendLog（落宿主日志面板）
  onToolResult(cb), onTeardown(cb),
  hostCapabilities(),
}
```

**写法纪律**：
- 宿主当前声明 **7 项**能力（`serverTools`/`serverResources`/`logging`/`openLinks`/`downloadFile`/`message{text}`/`updateModelContext{text}`）。`message` 与 `updateModelContext` **只声明 `text`**——**不要发 image 块**（Cowart 那套靠 `message.image` 回传图片的做法在本宿主会抛错）。
- 每个门面方法仍**先探测 `hostCapabilities()` 再调用，并 try/catch**。理由不是"宿主没实现"，而是：① 不同宿主能力面不同；② 能力声明**不是访问控制**（宿主自查明确写："View SDK 只对 `sampling` 做 capability 预检，其余方法一律发到线上"）。
- `unsupported` 的三项（`sampling`/`prompts`/`resources/templates`）**不要调用**。

### 3.3 宿主差异矩阵（决定适配层写法的关键表）

| 维度 | 官方规范 | SproutHarness（10-20） | Kimi Code 2.2.0 |
|---|---|---|---|
| 能力声明 | client MUST 声明 `extensions[io.modelcontextprotocol/ui]` | ❌ 不声明（全仓零命中） | ❌ `capabilities={}` |
| `resources/read` / `list` | 必须 | ✅ 支持（http / stdio 两条路径） | ❌ **不支持** |
| 渲染 iframe | 必须（双 iframe 异源沙箱） | ✅ 单 iframe 同源路由（`isolation` 缺口） | ❌ 无 |
| sandbox 属性 | `allow-scripts allow-same-origin` | `allow-scripts`（不透明源）+ 按 `permissions` 设 `allow` | — |
| CSP 下发 | HTTP 头，默认最严 | HTTP 头，默认 `default-src 'self' 'unsafe-inline'` + `script-src … 'unsafe-eval' blob: data:` + `img/font-src 'self' data: blob:` + `connect-src 'self'` + `frame-src 'none'` + `object-src 'none'` + `base-uri 'none'` | — |
| 工具结果给 View | `CallToolResult` | **只给纯文本 `content`，剥掉 `structuredContent`** | — |
| View→server 调用 | host 代理 `tools/call` | ✅ `/api/mcp/{sid}/proxy`（双 header 鉴权）+ `read`/`list` 同路 | — |
| `ui/message` | 标准 | ✅ **需用户点「确认发送」**；文本 only；≤4000 字符；≤3 条待确认 | — |
| `ui/update-model-context` | 标准 | ✅ 文本 only；≤8000 字符；覆盖式；**在 `startStream` 内随下一条用户消息（含确认后的敲门）附带** | — |
| `ui/open-link` / `ui/download-file` | 标准 | ✅（链接 http/https；下载**仅 embedded**、≤20 MB、只取第一条） | — |
| `size-changed` / `logging` | 标准 | ✅（高度钳制 1200px；日志 ≤2000 字符） | — |
| `ui/resource-teardown` | Host MUST | ✅（发请求 → 隐藏容器**不移除** → 等回执 ≤5s → 才拆；**View 必须应答**） | — |
| `hostContext` | 标准 | ✅（**theme 固定 `dark`**；`displayMode` 固定 `inline`；`maxHeight=1200`） | — |
| 结构时序 | — | 🚫 **View 只在工具执行完成后创建** → `tool-input-partial`/`tool-cancelled` 结构性不可能 | — |
| 动态上下文 | — | 🚫 `host-context-changed` 不支持 | — |
| 容器限制 | — | UI HTML ≤ **2 MB**；资源拉取超时 15s；握手超时 10s；iframe 加载超时 15s；**每会话最多 4 个 App 实例**；UI HTML 每会话 LRU 缓存 600s；buffer 队列 8 条 / 空闲 TTL 300s；`mcp_app` SSE 事件**不重放** | — |

**运维约束**：widget HTML 有 300s 空闲寿命、跨进程不可见、SSE 重连不重放 → **页面刷新后 widget 消失是正常态**；适配层必须在 `get_status` 轮询失败时优雅提示"重新打开编辑器"。**缓解**：宿主 `oninitialized` 可重复触发并重发 `tool-input`/`tool-result`，**iframe 自身重载（会话切回）能自动恢复**——只有进程级驱逐/页面刷新才需要重新调 `open_editor`。

---

## 4. 目标架构

### 4.1 一个核心、两条传输、一个 View

```
轨 B（现状，逐字节不动）
Agent ←MCP stdio→ bridge_mcp.py ←loopback HTTP(mgmt bearer)→ daemon(BridgeCore + HTTP + SSE + SQLite)
                                                                    ↑ loopback HTTP(browser bearer) + SSE
                                                             独立浏览器 editor.html

轨 A（新增）
Agent ←MCP stdio→ bridge_mcp.py（同进程直接持有 BridgeCore，**不起 HTTP 端口、不发凭证**）
                        ↑ MCP tools/call（标准）
Host（SproutHarness / Claude / …）— AppBridge ←postMessage JSON-RPC→ iframe沙箱 editor.html
                        ↓ /api/mcp/{sid}/proxy（宿主侧，透明）
                   visibility:["app"] 工具组 → BridgeCore
```

`BridgeCore`（`tools/bridge_core.py:409-1783`）与 `BridgeHTTPServer`（`:1784-2076`）本就是分离的两层，**轨 A 只需新增一个"直连 dispatch"层**：把 `BridgeHandler._api()` 的路由表映射为 MCP 工具函数，其余零改动。

### 4.2 轨道判定：声明 + 实证双信号【设计】

**判定不能发生在 `open_editor` 之内**——SproutHarness 的工具结果是**先返回、后拉资源、再渲染 iframe**（`graph.py:746`：`adapter.invoke_coroutine` 完成 → 才 `_fetch_ui_resource` → 才 `store_app_html` → 才发 `mcp_app` SSE）。宿主自认这是 `structural` 缺口。若 `open_editor` 阻塞等 widget 握手 → 死锁（宿主等我们的结果，我们等宿主的 iframe）。

- **`open_editor` 立即返回**，附 `mode_hint`：`"mcp-app"`（客户端声明了 UI 扩展 → 乐观）/ `"unknown"`（未声明）。**`mode_hint` 在 SproutHarness 与 Kimi Code 上都会是 `"unknown"`（两家都不声明），设计必须在"恒为 unknown"的前提下正确。**
- **`open_browser` 扩展为 `"auto"`（新默认）**：
  - `mode_hint == "mcp-app"` → 不启动浏览器；
  - `unknown` → daemon 起**存在性窗口**（默认 8s，`PPTX_HTML_VIEW_WAIT_SEC` 可配）：窗口内收到 `attach_view` → 取消浏览器启动；到期无信号 → 启动浏览器（轨 B）。
- **`await_intent` 增加仲裁相位**，三条硬化：
  1. **先查已决状态**：若本会话已出现 `view_attached` 或 `page_online`，**直接采用，不等待**（agent 调用 `await_intent` 通常晚于 daemon 的窗口判定）；
  2. **自解除**：仲裁相位**仅在本会话从未出现过任何 UI 信号时启用一次**。轨 B（Kimi Code）在 `open_editor` 后浏览器已心跳 → 此后每次 `await_intent` 都跳过仲裁 → **轨 B 行为与今日一致，零时延回退**；
  3. **窗口 ≥ 存在性窗口 + 4s**（默认 12s），避免两者判定互相矛盾。
- 返回：`attach_view` 先到 → `{status:"mcp_app", note:"UI 已嵌入宿主，勿阻塞；请结束本回合，编辑器会主动发消息"}`；心跳先到 → 落入现有阻塞逻辑（逐字节不变）；直接等到 intent → 返回 intent。

**失败模式是良性的**（重要）：若仲裁窗口判成轨 B 而 widget 其实活着，agent 会阻塞在 `await_intent`——但 widget 提交的 intent 会**正常解锁它**。代价只是"回合被占住"（即 1015 想解决的那个问题），**不会挂死**。

这样**五个工具不变**，`await_intent` 仍是唯一"等待 UI"动词，且 `await_intent(timeout_sec=1)` 自然成为非阻塞轮询——无需新增 `take_intent`（修正 1015 版 §5.2 的工具面扩张）。

| 轨 | 存在性探针 | 存续判定 |
|---|---|---|
| B | 浏览器心跳（已有，`POST /api/bridge/heartbeat` → `page_online`，B:885） | 15s 一次 |
| A | 新增 app-only 工具 `attach_view`（View 连接后**立即**调用）+ 每次轮询捎带 | 超 30s 未见 → 视为离线 |

### 4.3 工具面

| 轨 B（现状五工具） | 轨 A | 说明 |
|---|---|---|
| `open_editor` | `open_editor` | **唯一带 UI 的工具**；轨 A 加 `_meta.ui.resourceUri`，轨 B 不加（或加也无害） |
| `await_intent` | `await_intent`（先仲裁再阻塞） | 轨 A 下通常返回 `status:"mcp_app"` |
| `push_update` | `push_update` | 验证证据模型、CAS 发布**原样** |
| `get_status` | `get_status` | View 轮询也走它 |
| `close_session` | `close_session` | 原样 |
| （`/api/*` 非工具端点） | `attach_view` / `read_deck` / `read_bundle_file` / `save_deck` / `write_asset` / `submit_intent` / `save_draft` / `list_versions` / `rollback` —— **全部 `visibility:["app"]`（根级 + `ui` 双写）** | 等价于轨 B 的浏览器 HTTP 端点 |

> ⚠️ **2026-10-27（1027 精简，见 §10.13）**：本行原列 **13** 个 app-only 工具，现为 **9** 个——`cancel_intent` / `retry_intent` / `query_intents` 删除（全仓无 View 调用方；daemon 三条路由保留给轨 B），`read_asset` + `read_export` 合并为 `read_bundle_file`。本文 §5/§6 等处的 `read_asset` / `read_export` 一律按 `read_bundle_file` 读（`assets|fonts` 前缀走资产路由，`export/` 前缀走产物路由）。

**红线变更需签字**：AGENTS.md 现写"恰好五个 `pptx-html-bridge` MCP 工具可见时必须 editor-first"。轨 A 下工具数**不减反增**（+9 个 app-only）。建议改写为：
> **"轨 B 恰好五个工具；轨 A 工具面扩展，但 `open_editor` 仍是唯一带 UI 的入口、唯一面向模型的创作入口；全部 app-only 工具 `visibility:["app"]`（根级 + `ui` 双写，对模型不可见）。"**
> editor-first 原则两轨一致。工具总数变化必须经用户确认后再实施。
> **（2026-10-27 履行）**：第二次工具数变化（13 → 9，工具面 18 → 14）即按本行要求先取用户签字后实施，见 §10.13。

### 4.4 通道映射总表

| 轨 B 机制 | 轨 A 等价物 | 备注 |
|---|---|---|
| `await_intent` 阻塞 | 仲裁相位 + 敲门触发新回合 | **超时/租约问题消失**；敲门需用户确认（§5.5） |
| SSE 七类事件 | `get_status` 轮询（默认 2s，空闲退避 10s）+ `onteardown` | 高频事件退化；`assets-changed` 由 revision 比对推导 |
| `POST /api/save` | `callTool("save_deck")` | CAS/receipt 语义**不变** |
| `POST /api/bridge/asset` | `callTool("write_asset")` | 同名覆盖 + `data-image-state="uploaded"` 语义不变 |
| `POST /api/bridge/draft` | `callTool("save_draft")` | **从"本地优先"升为唯一通道** |
| `POST /api/intent` | `callTool("submit_intent")` | 同一 `accept_intent` 校验与 SQLite 入队 |
| 编辑器"复制指令"（写剪贴板） | `setModelContext`/`notifyAgent` 承担"发送"语义；复制仍是本地剪贴板（声明 `clipboardWrite`） | 两者不同动作，不互相替代 |
| 下载产物（Blob + `<a download>`） | `read_export` 取字节 → `downloadFile` | 仅 embedded、≤20 MB（§5.9） |
| browser/management 两级凭证 | **删除**（宿主沙箱 + `visibility:["app"]` 担保） | |
| 浏览器心跳 / `page_online` | 保留（轨 B）；轨 A 用 `attach_view` | |
| waiting lease 90s | **删除**；processing owner / attempt fence **保留** | |
| bootstrap 票据 | **删除** | |
| `pptx-html:assets-changed` | revision 比对 → 重读资产 | |

---

## 5. 关键决策与难点

**5.1 deck HTML 传输**：widget 不能读文件 → `callTool("read_deck")` 经宿主中转。实测规模：`tests/decks/cmb-retail/index.html` = 518 KB（54 页）。**替代通道**：宿主已实现 `onreadresource` 与 `onlistresources` 代理【源码】，大载荷可走 `ui://` 资源分片（`ui://…/deck/{session}/part/{n}`）。一期实现前者，预留后者。

**5.2 资产（图片）三条管道**：
- **方案 a（默认，跨宿主保真）**：`read_asset` → base64 → `data:` / `blob:` 替换 `src`。实测两者均可用。内存缓存按 revision 失效；序列化保存时**还原为 `assets/` 相对路径**（磁盘 deck 纯净性不破）；IntersectionObserver 按可见页懒加载。
- **方案 b（loopback 只读静态服务 + `resourceDomains` 声明）**：**可行性上调**（实测相对路径 `img` 可直载；`fetch` 失败是 CORS 不是 CSP）。⚠️ **但与本设计 §0 的"轨 A 传输层整层不启动"自相矛盾**——它要保留一个只读端口。**定位为可选优化，不是架构的一部分**；若要启用，须在评审中明确承认这条例外，并接受"需对端补 ACAO + 宿主不收紧 loopback 条目"的双重依赖。
- **烙入大图专项**：契约下限 2560×1440，单张 PNG 常 2–5 MB，几十张经 base64（+33%）不可行 → 落盘即存展示档（WebP/JPEG）+ 源档（PNG）双份；可见页懒加载。
- **三层兜底**：图标级 <100 KB → `data:` 直出 → 默认 `blob:` 中转 → 方案 b 白名单宿主 URL 直读。

**5.3 无本地存储 → 草稿全面服务端化**：实测三类存储 + cookie 在 SproutHarness 沙箱**全部 SecurityError**。因此：
- 草稿写 `callTool("save_draft")`，**防抖 800ms + 失焦立即**；
- **`onteardown` 是可靠的最后防线**：宿主拆卸走两阶段——发 `ui/resource-teardown` 请求、隐藏容器但**不移除 iframe**、等 View 回执（≤5s）才拆。所以 **View 必须实现 `onteardown` 并在回执前完成草稿落盘**（异步 flush 后 resolve）；
- 残留风险：`clearChat` / 强杀 / 进程驱逐时回执超时 → 未落盘编辑丢失。用"防抖窗口 ≤ 1s"压到最小；
- 凭证续传（sessionStorage）整层删除；session 上下文改由 `onToolResult` 下发。

**5.4 轮询替代 SSE**：`get_status` 默认 2s、空闲退避 10s、`document.hidden` 时暂停。桥栏"任务进行中"必须**如实表达时延**。**便条不适合做状态推送**（覆盖式 + 只在 `startStream` 消费）；revision 变化用 `sendLog` 写宿主日志面板更合适。

**5.5 三个通道，各司其职**（本轮按用户指正重写）

初稿写的是"提交时：`submit_intent` + `setModelContext(简报)` + `notifyAgent(短句)`"的三段式——**这是错的**：脑暴/设计/批注的"发送"，用户那一下点击本身就是敲门，而意图载荷本就落在状态机里，agent 一个 `await_intent` 就拿到。便条在提交路径上纯属冗余。

正确模型是**三个通道，三种职责**：

| 通道 | 职责 | 判据 | 可靠性 |
|---|---|---|---|
| **状态机**（`submit_intent`）+ `await_intent` | **待办**：agent 必须处理的工作项 | 有提交事件、要 agent 动手 | ✅ 持久化、不丢、可重试（唯一可信的一环） |
| **敲门**（`notifyAgent` → `ui/message`） | **触发**：把 agent 叫醒 | 需要降低时延 | ⚠️ 文本 only、≤4000 字符、**需用户点「确认发送」、可被忽略** |
| **便条**（`setModelContext` → `ui/update-model-context`） | **背景**：agent 下一回合该知道的静默状态 | 没有提交事件、不该打断 | ⚠️ ≤8000 字符、覆盖式、**一次性**（`startStream` 内消费后即清） |

一句话概括：**意图队列是"待办"，便条是"背景"。** 有工作项就进队列；只是背景就进便条。

**便条的真正主场（都是"未提交的静默状态"）**：

| 场景 | 携带什么 | 为什么不能走状态机 |
|---|---|---|
| 用户手改了没保存 | "未落盘编辑 3 处：标题字号 40→32、两处正文改 KPI 样式" | 没有提交事件；不说 agent 会覆盖掉 |
| 当前在看哪一页 | "当前编辑 slide-07" | 用户打字说"这页再改改"，agent 否则只能猜 |
| 设计面板的探索状态 | 四组当前选择 | 面板是探索性的——挑了半小时**没点发送**，然后打字说"按刚才面板里的选" |
| 批注未发送 | 框选内容 + 三层引用 | 用户选了批注直接去聊天说"这些错别字改掉" |
| 待处理批注批次 | "2 批 / 共 5 条待处理" | 见 §5.10 |

**便条的传输语义（两条关键细节）**：
1. **它搭 `startStream` 的顺风车**——`_takeAppContextFor` 在 `startStream` 内（`webui.html:2628,2654`），而确认敲门的 `_submitAppMessage` 也走 `startStream`。所以**便条不是"只能等用户下次打字"，用户点确认敲门时它一并送达**。二者是互补而非互斥。
2. **它是覆盖式 + 一次性**：只保留最后一份，随下一条用户消息送出后即清空。所以它是**"当前状态镜"，不是事件流**——要发的是"编辑器当前的完整相关状态"合成的一条，不是"又发生了一件事"。

**设计纪律**：
1. agent 需要知道的任何事，**必须先落状态机**；敲门与便条都是优化；
2. **大内容走状态机（agent 自己取），背景走便条，敲门只发短句**；
3. **UI 文案必须如实**：提交按钮旁标注"提交后请在对话面板点『确认发送』"；
4. 门面 `notifyAgent` **静默吞掉 reject**（用户忽略不算错误），结果作为诊断字段回传；
5. **`await_intent(timeout_sec=1)` 是"用户不点确认"时的唯一到达路径**——便条让 agent 看到"有 2 批批注待处理"，轮询把它取走。SKILL 增加条款：用户表达"等编辑器反馈"后若长时间无下文，主动查一次。

**5.6 主题/容器/尺寸**（宿主 10-20 已填充 hostContext，据此定稿）：
- `theme` **固定 `dark`**、`displayMode` **固定 `inline`**、`availableDisplayModes=['inline']`——**不要调 `requestDisplayMode("fullscreen")`**。全屏诉求只能靠宿主容器尺寸，或降级 `openLink`。
- **`containerDimensions.maxHeight = 1200px`、宽度不跟随 `size-changed`** → 工作台必须为"聊天面板宽度 × ≤1200px 高"设计。**这是轨 A 最实的 UI 约束**，P1 的适配层必须带 `hostViewport` 抽象（轨 A 取 `containerDimensions`，轨 B/嵌入态取 `window.innerHeight`）。
- 宿主提供 `styles.variables` 与 `locale`/`timeZone` —— 工作台外层 chrome 应用宿主色板与暗色基调；**deck 渲染区不受影响**。
- 🚫 `host-context-changed` 不支持 → **不要指望运行时主题切换**。

**5.7 2 MB HTML 上限**：editor.html 428 KB + 内联 SDK bundle ≈ 700 KB < 2 MB ✅。**必须设构建期门禁**（注入后 > 1.5 MB 告警），因为它是宿主侧的**静默失败点**（超限直接回退纯文本，日志只有一行 warning）。

**5.8 宿主缺陷依赖风险**：10-20 重读显示宿主已修多项，但**仍影响本项目的项**：
- **N15（visibility 读取路径）未修** → 见 §3.1 第 3 条，本项目**双写**规避 + 断言测试；
- **`isolation` 整类未做**：单 iframe 同源路由返回不可信 HTML（顶层打开即失去隔离）、无 owner 隔离、`resolve_principal` 只校验目录存在、proxy 不校验 server/tool 绑定。
- **本项目对策**：不假设宿主已修；轨 A 的 app-only 工具**全部自校验**（session 存在性、CAS、意图归属），不依赖宿主鉴权。

**5.9 产物交付：下载通道**：宿主 `ui/download-file` 可用，但**只接受 embedded 内容**，`resource_link` 明确拒绝，≤20 MB，多条只取第一条。
→ 轨 A 路径：View 先 `read_export(file)` 取字节（base64）→ 包装成 embedded resource → `downloadFile`。
→ **风险**：导出档常接近 20 MB（含字体内嵌与双位图双写），且 base64 经 postMessage 有内存放大（≈27 MB 字符串）。**P3 必须实测单档字节数**；超限降级为"导出到工作目录 + 告知路径"。

### 5.10 异步批注与版本并发【本轮新增】

**场景**：用户在当前页批注 → 点发送 → 页面**驻留不跳转** → agent 开始干活 → 用户**继续对后面的页面批注**，可能再发多批。

**这不是轨 A 的问题，是双轨共用的协议硬伤。**

#### 5.10.1 根因：指令型意图被错误施加了写入前置

**先纠正一个易错点（读码后修正，我上一版的 D1 说错了）**：`intents.base_revision` **不是信息字段，它是发布时的 CAS 基线**——`push_update` 把它原样交给 `_publish`：`self._publish(session_id, work_path.parent, manifest, row["base_revision"], …)`（`B:1210`），而 `_publish` 第一件事就是 `if current != base_revision: raise 409 REVISION_CONFLICT`（`B:1300`）。因此"指令型不做校验"**不能实现成"跳过检查"**——必须把**写入基线**与**锚点版本**拆成两个概念：

| 概念 | 现状载体 | 应有语义 |
|---|---|---|
| **写入基线**（publish CAS base） | `intents.base_revision` → 认领时写入 `attempts.base_revision` | 必须等于**认领时刻**的 `session.revision` |
| **锚点版本**（批注引用所在版本） | 无独立字段 | 记录**捕获时刻**的版本，仅作信息，供 agent 重解锚点 |

| 类别 | intent | 写入基线处理 |
|---|---|---|
| **指令型** | `brief.submitted` / `design.submitted` / **`anno.submitted`** | **不因提交者版本陈旧而拒绝**，归一化到当前 |
| **写耦合型** | `convert.requested` / `bake.requested` / `illustrate.requested` | 保持硬校验（"你要转换的那个版本已经没了"是有意义的拒绝） |

批注是一条条**指向文字/元素的引用 + 指令**，不是要提交的文档字节。对二者一视同仁会走到：

- `bridge_core.py:1045` —— `accept_intent`：`base != session["revision"]` → **409 REVISION_CONFLICT**。
- `bridge_core.py:988` —— `await_intent` **认领时**再次校验，陈旧则**把意图毒化为 `status='conflict'`** 并抛 **409 `RECOVERY_REQUIRED`（"请求基线冲突，需要用户决定重试"）**。⚠️ 这比单纯 409 更硬：该意图被终结，必须用户介入。
- `editor.html:7600` —— 提交任何非 brief intent 前**强制先存盘**（`state.dirty → saveDeck()`），而 `saveDeck` 同样带 `base_revision` → 存盘也会失败。
- `editor.html:7602` —— 首次提交用 `bridge.loadedRevision`；而**重试路径已在用 `bridge.latestServerRevision`**（`E:7638`）。**这个不对称就是缺口所在**，也说明修法有现成先例。

**补充核对（说明现状内部是自洽的，不是 bug）**：`_copy_attempt` 的工作副本永远从**当前** bundle 复制，并断言 `revisions(check)[0] == session["revision"]`（`B:950`）——即"副本来自当前版本"，而发布 CAS 用的是**意图基线**。两者只在"接受之后、认领之前没有任何发布"时才一致——**这正是 `accept_intent:1045` 在维护的不变量，也正是它在异步场景下不可用的原因**。

#### 5.10.2 死锁时间线（按现有代码推演）

```
t0  编辑器在 R1，用户开始批注 slide-05
t1  agent 完成上一批，发布 R2                       ← 服务端已是 R2
t2  编辑器收 deck-changed；bridgeAutoReloadRisk() 为真（有未落盘编辑）
    → 护栏正确：不自动覆盖，存草稿，挂「载入远端」横幅
      latestServerRevision = R2，loadedRevision 仍是 R1
t3  用户继续批注 slide-07，点「发送」
    ├─ state.dirty → saveDeck(base=R1) → CAS 失败 → 抛「请先成功保存当前修改」   ← 卡死 A
    └─ 无 dirty → POST /api/intent(base=R1) → 409                                ← 卡死 B
t4  用户唯一出路：点「载入远端」→ 画布被替换
    → 与"页面驻留、继续批注"的诉求直接矛盾
（另有一种：若 409 未拦在提交、而在认领时才暴露 → 该批注被毒化为 conflict，
   agent 抛 RECOVERY_REQUIRED，同样要用户介入）
```

护栏（`bridgeAutoReloadRisk` + 草稿 + 载入远端横幅，`E:7458-7469`）**设计是对的**；错的是**把"提交"绑在了"画布必须是当前版本"上**。

#### 5.10.3 设计（五条）

**D1 · 写入基线与锚点版本拆开；仅写耦合型保留硬校验** —— ✅ **已实施**（`tools/bridge_core.py`）
- 新增 `INSTRUCTION_INTENT_TYPES = {"brief.submitted","design.submitted","anno.submitted"}`（`B:66`）；
- `accept_intent`（`B:1050`）：指令型**跳过相等校验**，并把存库的 `base_revision` **归一化为 `session["revision"]`**——该字段是**写入基线**，不是锚点，不能存捕获时的版本。`request_digest` 仍用客户端提交的原值（幂等语义不变）；
- `await_intent` 认领（`B:987`）：指令型若发现 `row["base_revision"] != s["revision"]`，**重新归一化后继续**（`UPDATE intents SET base_revision=?` 并重取该行），**不毒化**；写耦合型保持原有毒化行为逐字节不变；
- **锚点版本**：`anno.submitted` / `design.submitted` 的 payload 新增**可选键 `anchor = {revision, dirty}`**（`revision` = 捕获时的 `loadedRevision`，可为 `null`；`dirty` = 捕获时是否有未落盘编辑）。`_validate_payload`（`B:1062`）对这两个类型做形状校验并对键集放行 `-{"anchor"}`；`brief.submitted` 与三个写耦合型键集不动。（原设计说复用 `deck` 字段，但 `deck` 实际是**文件名**字符串，不是版本，故改用新键。）
- 副作用（正确性关键）：归一化后 `attempts.base_revision` 与发布 CAS 都取"**认领时刻**"的版本 → **agent 工作期间若有他人发布，CAS 仍会如实失败**，写入保护一点没丢。
- **回归影响（已核对）**：`REVISION_CONFLICT` 全仓只被断言 3 处——`test_bridge_core.py:809`（`core.save` 路径）、`r_bridge_check.py:610`（描述串）、`s_bridge_scale_check.py:552`（stale save）。**没有一处覆盖 `accept_intent` 的陈旧基线**，所以 D1 是"改了没人拦"而非"会打破回归" → 已补 6 个针对性用例（见 §7 P0.5）。

**D2 · 编辑器提交不再要求"画布是当前版本"** —— ✅ **已实施**（`editor.html:7599-7608`，已裁决：**允许**锚点指向未落盘内容）
- 指令型提交直接送 `loadedRevision` 作 `base_revision`（**服务端会归一化，不参与校验**），锚点版本另经 `payload.anchor` 上报；
- 放宽 `E:7600` 的"必须先存盘"耦合：`saveDeck()` 失败（它以返回 `false` 表示失败，不抛异常）时，**指令型**改为 `toast` 一句诚实提示后继续提交；非指令型保持"保存失败即抛错"；
- payload 用 `Object.assign({}, payload, {anchor})` 克隆，**不污染调用方对象**；`bridgeResendIntent` 原样重发 `item.request`，无需改动；
- 理由：阻断会让用户在异步场景下无路可走（§5.10.2 卡死 A/B）；**诚实标注优于阻断**，未命中的锚点由 D3 按条报"已失效/已重定位"。

**D3 · 锚点"处理时解析"，不是"捕获时冻结"**
批注的三层引用（slide / DOM path / 文字摘录）在 agent **处理那一刻**对当前 revision 解析；解析不到的**按条**报"已失效"或"已按文字重定位到 slide-12"，**不盲目套用**。否则用户在 R1 锚的文字，agent 在 R3 上照改会改错地方。

**D4 · 批次合并：`anno` 可合并，写耦合型不可**
用户 3 分钟提交 5 批，串行 = 5 次发布 → 每次发布让后面的批注更旧 → 冲突越滚越大。做法：agent 取到最早的 pending 批注 intent 时，**一次抽干所有 pending 批注 intent** 合成一个工作项，其余用已存在的 `cancel_intent` 标记"已合并处理"（留审计痕迹，不改状态机结构）。
判据干净：**纯指令、幂等、无副作用 → 可合并**（`anno`、`design`）；**作用于具体产物 → 不可合并**（`convert`/`bake`/`illustrate`）。

**D5 · 编辑中页保护 —— 便条的落点**
`active_edit` **在心跳里已经存在**（`E:7331`）。轨 A 把它放进便条：

```
setModelContext("用户当前编辑 slide-07；待处理批注 2 批 / 共 5 条；未落盘编辑 3 处")
notifyAgent("批注已提交（batch#2）")
```

因为**便条搭 `startStream` 的顺风车**（§5.5），用户点确认敲门时它一并送达——**这就是便条在本场景最实的用途**。配套 SKILL 条款：**不改用户 `active_edit` 指向的页**，除非该页本来就有批注。

#### 5.10.4 编辑器侧要改的

- 批注清单从"平铺"改成**按批次分组**，每条带状态：待处理 / 处理中 / 已应用 / 已重定位 / 已失效；
- 新 revision 载入后**重解锚点**，解不出的就地标黄，不静默丢；
- **「提交」与「载入远端」解耦**：提交不再要求画布是当前版本（D2）；横幅只在真的会覆盖用户画布时拦人。

### 5.11 对比质检的产物载入（轨 A 缺口）【本轮补】

A9 的并排/滑动/差异视图需要 export 产物（`deck-vector` 的逐页 SVG/PNG、`manifest.json`）。轨 A 无服务端 origin → 全部要经 `read_export` base64 中转，64 页 × 多档体积可观。
**一期决策**：轨 A 的对比质检**按可见页懒加载单文件**，不做全量预取；若实测不可接受，**降级为"对比质检仅在轨 B 提供"**（诚实降级优于卡顿）。**待 P3 实测决定。**

---

## 6. 改造清单

### 6.1 editor.html（第四运行态，最小侵入）

| 位置 | 改动 |
|---|---|
| `bridgeParseLaunch()`（E:7260）旁 | 新增 `pptxMcpParseLaunch()`：`window.pptxMcp` 存在 → MCP Apps 态；**检测顺序必须先于嵌入态**（轨 A 下 `window.parent !== window` 也成立，两态互斥） |
| 状态宿主层（新增） | 抽出**统一宿主适配层**：`hostBridge.{load,save,asset,intent,status,poll,viewport,background}` 策略接口，轨 A/B/嵌入/静态四实现；`viewport` 在轨 A 取 `hostContext.containerDimensions.maxHeight`（1200）。**P1 的独立重构，行为零变化** |
| `bridgeSend()`（E:7637 三态分流） | 加第四臂：`callTool("submit_intent", …)` + `notifyAgent(短句)`（**提交路径不发便条**，见 §5.5） |
| 便条维护（新增） | 独立于提交：页切换 / 脏状态反转 / 待处理批注数变化时，**防抖 2s** 合成一条状态镜 → `setModelContext(...)`；覆盖式，无需去重 |
| `saveDeck()`（E:4898） | 加 arm：`callTool("save_deck",{html,base_revision})`，复用 CAS receipt；**删除 FSAA/下载臂的调用点，不删代码路径**（轨 B 仍用） |
| `bridgeSubmitIntent`（E:7599-7615） | 按 §5.10 D2 改：指令型用 `loadedRevision` 作锚点版本、去掉强制存盘耦合、payload 增 `dirty` 标记 |
| 批注清单（E:4536,4544） | 按 §5.10.4 改：批次分组 + 每条状态 + 失效标记 |
| 图片加载/替换（E:4626） | 加 arm：`read_asset` / `write_asset`；序列化时还原 `assets/` 相对路径 |
| `bridgeApplyEvent()`（E:7537） | 轨 A 无 SSE → 换 2s 轮询 `get_status`，diff 后**走同一状态合并函数** |
| 草稿（E:7343-7382） | `indexedDB` 臂改为 `callTool("save_draft")` |
| 连接时新增 | `ready` 后**立即** `callTool("attach_view",{session_id,client})`；轮询时捎带续期 |
| `onteardown` 新增 | **异步 flush 草稿 + 提交未提交 intent，完成后才 resolve**（宿主等这个回执 ≤5s） |
| 导出下载（E:7177-7185） | 加 arm：`read_export` → `downloadFile`；超 20 MB 回落"告知路径" |
| 复制指令（E:5169,6072,4605） | 加 arm：声明 `clipboardWrite` 后试调用；失败回落 `execCommand`/纯文本 |
| 存储/剪贴板/文件选择探测 | 全部改为**试调用 + try/catch**，删除 `typeof` 判断 |
| 桥栏（E:750-812） | 复用；数据源 SSE → 轮询；如实标注时延 |
| 顶栏显隐（E:7675 起） | 轨 A 隐藏"打开浏览器"类入口（链接走 `openLink`） |
| 外层 chrome 配色 | 轨 A 用 `hostContext.theme=dark` 与 `styles.variables`（仅外层；按初始值定死） |
| 快捷键 / 章节 / 侧栏 / 三态 / 翻面 | **零改动**（实测沙箱可用） |

### 6.2 server

1. `bridge_mcp.py`：新增 `ui://pptx-html-bridge/editor.html` 资源注册（注入门面）+ `open_editor` 的 `_meta` **三处写** + `mode_hint`；
2. 新增 **`tools/bridge_dispatch.py`**：把 `BridgeHandler._api()` 的路由映射为可调用 `BridgeCore` 方法表，**轨 B 与轨 A 共用**；
3. 新增 **app-only 工具组**（13 个，§4.3），全部根级 + `ui` 双写 `visibility:["app"]` + 工具层二次校验（§5.8）；
4. ⚠️ **轨 A 的 `await_intent` 实现约束**：`BridgeCore.await_intent`（`B:964`）是**同步轮询**（`cond.wait(min(remain, 0.5))`），而 `bridge_mcp.py` 是 async 且现用 `await asyncio.to_thread(...)`（`M:97`）——**不得在轨 A 直接同步调用**，否则会堵住同时服务 View 的事件循环（`callServerTool` 永远进不来 → 死锁）。两条可行路线：① 继续用 `asyncio.to_thread`（**安全性已具备**：`BridgeCore` 是 `check_same_thread=False` + `_db_lock` RLock + 每会话 RLock/Condition，`B:439-447`，本就是为 ThreadingHTTPServer 与转换 worker 线程设计的）；② 把 `await_intent` 加一个 async 变体，用 `await asyncio.sleep` 替代 `cond.wait`。**倾向 ②**（单线程、无池占用），但 ① 风险更低。
5. `open_editor` 的 `open_browser` 支持 `"auto"`；新增 `PPTX_HTML_VIEW_WAIT_SEC`（默认 8s）；
6. `await_intent` 增加仲裁相位（三条硬化见 §4.2）；
7. `get_status.capabilities` 增加 `track: "mcp-app"|"bridge"|"pending"` 与 `view_attached`；
8. 资源 `_meta.ui` 增补 `permissions: {"clipboardWrite": {}}`；
9. **断言测试**：每个 app-only 工具的 meta 同时含根级与 `ui` 内 `visibility`。

### 6.3 构建产物（一次性，提交 Git + sha256 manifest）

`tools/ext_apps_bundle.js`：从 `@modelcontextprotocol/ext-apps` 提取 View 侧 `App` 浏览器 bundle（官方 `dist/src/app-with-deps.js`，248 KB，经核验**产物内无 `import` 语句**，可直接 `<script type="module">` 引入【源码 `build.bun.ts:35-36`】）+ `window.pptxMcp` 门面 + `</script` 转义。**构建期依赖，运行时零 npm 依赖**（与"daemon 不依赖 MCP 包"同精神）。附带 CSP 静态断言：注入后 HTML 无外链 `script`/`link`/`iframe`/`object`。

---

## 7. 分期与验收

| 期 | 内容 | 验收 | 风险 |
|---|---|---|---|
| **P0 事实冻结**（已完成） | §1/§2 的实测矩阵入库；宿主差异矩阵带版本戳 | ✅ `tests/harness/z_sandbox_matrix.py` + `results/z_sandbox_matrix.json`；宿主能力面按 10-20 实现逐项对齐 | 宿主高频变动 |
| **P0.5 协议修（双轨共用，已裁决先做）** | **D1**（写入基线与锚点版本拆开：`INSTRUCTION_INTENT_TYPES` + accept 归一化 + claim 归一化不毒化）✅ 已实施 ／ **D2**（编辑器提交解耦、`anchor` 标注 `revision`+`dirty`）✅ 已实施 ／ **D3**（锚点处理时解析）⏳ agent/SKILL 侧待做 ／ **D4**（批注批次合并）⏳ agent/SKILL 侧待做 ／ **6 个正负例测试** ✅ 已补 | ✅ `test_bridge_core.py` **44 passed**（原 38，+6）；✅ `r_bridge_check.py` 六组全 PASS；⏳ `run_e2e.py` 61 项回归在跑（**未出结果前不得记 PASS**） | ⚠️ **D1 落在无测试覆盖区**（变更前无任何断言覆盖 `accept_intent` 陈旧基线），已补测；`await_intent` 是双轨共用单点 |
| **P1 适配层抽取** | editor.html 抽出统一宿主适配层（四态检测 + 策略接口 + `hostViewport` + 便条维护），**行为零变化** | 现有 e2e 61 项全绿 | 纯重构，可回滚 |
| **P2 server 双模** | `bridge_dispatch.py` + 资源注册 + `attach_view` + app-only 工具组 + `_meta` 双写断言 + `await_intent` 异步化（§6.2 第 4 条） | 双模注册单测 + `r_bridge_check` 全绿 | 不改轨 B 行为 |
| **P3 View 第四态** | editor.html 轨 A 态（读 deck / 保存 / 图片 / 轮询 / 草稿 / teardown / 下载 / 便条 / 批注批次 UI） | **harness 第三组宿主模拟器**：可参照宿主自身做法——`mcp_apps_tester.html`（264 行宿主模拟页）+ `tests/test_mcp_apps_host_matrix.py`（能力处置表与 SDK handler 全集双向 diff）+ L1/L2/L3 三层（pytest / node 探针驱动真实 bundle / playwright 真实页面）；另需实测 §5.11 对比质检与 §5.9 下载体积 | widget 生命周期不受控 |
| **P4 真实宿主** | SproutHarness 端到端（脑暴 → 生成 → 发布 → 编辑 → **异步批注** → 再生成）；Claude Desktop 可选 | 证据入 `docs/test_acceptance/`；**未跑项一律记 NOT_RUN** | 宿主分支未合并 |
| **P5 插件打包**（正交） | 按 Agent Plugins 打包，widget 三件套入产物 | 冷启动探针 | — |

**回归红线的准确表述**（本轮修正）：`r_bridge_check.py`、`test_bridge_core.py`、`run_e2e.py` 现有 61 项在 **P1–P5 必须零改动全绿**（这是"BridgeCore 原样复用"的证明）；**P0.5 例外**——它有意变更协议语义，但变更点经核**不在现有覆盖内**，因此**必须新增测试**，而不是靠"现有测试仍绿"来证明正确。

---

## 8. 风险与未决

1. **轨 A 仍无真实端到端验证对象**：Kimi Code 不支持；SproutHarness 分支**未合并**（`git status` 显示 61 项改动已暂存/未提交）。P4 之前轨 A 的价值是"给 SproutHarness / Claude 的能力面"与"给 Kimi Code 的需求输入"——**轨 B 的维护负担不因轨 A 消失**。
2. **宿主高频变动**：10-19→10-20 一天内能力面从 render-only 变 interactive（本文初稿因此作废三条结论）。适配层必须**全部按能力位 + 试调用**写，§3.3 矩阵**必须带版本戳**。
3. **§5.10 的 D1 改动落在无测试覆盖区**：这是本轮识别出的最大工程风险——不是"会打破回归"，而是"改了没人拦"。必须先补测再改。
4. **容器寿命与容量**：LRU 缓存 600s、buffer 空闲 TTL 300s、队列 8 条、**每会话最多 4 个 App 实例**、事件不重放、跨进程不可见。必须设计"优雅失联"；**不能**把 widget 存活当默认前提。缓解：`oninitialized` 可重复触发 → iframe 重载可恢复。
5. **`notifyAgent` 的用户确认闸门是 UX 问题**：能触发回合，但用户必须点一下；不点则永不到达。**P4 第一个要看的体验点**。兜底是"便条 + `await_intent(1)` 轮询"（§5.5 第 5 条）。
6. **`ui/download-file` 的 20 MB 上限对导出产物偏紧**（字体内嵌 + 双位图双写）→ P3 实测单档；超限回落"告知路径"。
7. **布局约束是轨 A 最实的代价**：仅 `inline`、高度上限 1200px、宽度不跟随。工作台在此尺寸下的可用性需 P3 真机评估，可能需要"紧凑模式"。
8. **§5.11 对比质检的产物载入未定**：轨 A 可能不得不降级为"仅在轨 B 提供对比"。
9. **图片管道性能**：54 页 deck 数十张图经 base64 的首屏性能待 P3 实测；方案 b 依赖对端 ACAO 与宿主 CSP 放行，且与"传输层整层删除"矛盾（§5.2）。
10. **大载荷宿主限制**：单个工具结果的尺寸上限未知【未验证】；必要时切 `ui://` 资源分片。
11. **红线变更分两次履行**：轨 A 工具数 5 → 18 于 2026-10-20 经用户签字（§4.3、§9 #1）；**1027 再精简 18 → 14**（删 `cancel_intent`/`retry_intent`/`query_intents`、并 `read_asset`+`read_export` → `read_bundle_file`）于 2026-10-27 经用户签字，见 §10.13。
12. **`await_intent` 是双轨共用单点**：仲裁相位（§4.2）与 D1 的认领校验（§5.10）都改它。缓解：仲裁**自解除**（仅本会话从未有 UI 信号时启用一次），轨 B 零时延回退。

---

## 9. 裁决记录（2026-10-20，用户授权"按推荐决策来"）

| # | 事项 | 裁决 | 落地位置 |
|---|---|---|---|
| 1 | 轨 A 工具数 5 → 18 的红线措辞 | ✅ **按 §4.3 改写 AGENTS.md** | 已改：红线第 1 条拆为「轨 B 恰好五工具」+「轨 A 扩展但 `open_editor` 仍是唯一带 UI / 唯一面向模型的入口」，并写明 `visibility` 根级 + `ui` 双写；**（2026-10-27）第二次工具数变更 18 → 14 同规矩先取签字后实施，见 §10.13** |
| 2 | §5.10 D2：是否允许"锚点指向未落盘内容"提交 | ✅ **允许**（诚实标注 `dirty`，由 D3 按条报"已失效/已重定位"） | §5.10.3 D2 |
| 3 | P0.5 是否先于 P1 实施 | ✅ **先做**（双轨共用、与 MCP Apps 升级解耦、可独立验收） | §7 P0.5 行 |
| 4 | §5.2 方案 b（loopback 静态服务） | ✅ **保留为可选优化、不默认启用**；须在评审中明确承认它是对 §0"传输层整层不启动"的例外 | §5.2 方案 b |
| 5 | §5.11 对比质检在轨 A 的取舍 | ✅ **按可见页懒加载单文件**；P3 实测不可接受时才降级为轨 B 独有 | §5.11 |

**遗留待验证（非裁决项，P3/P4 实测）**：下载 20 MB 上限对导出产物的实际余量；1200px 高度下的工作台可用性；对比质检产物载入的真实代价。

---

## 附：参考

- 官方规范：`~/Desktop/ext-apps/specification/2026-01-26/apps.mdx`（SEP-1865，SDK 2.0.3，HEAD `82221c0`）
- 官方迁移指南：`~/Desktop/ext-apps/plugins/mcp-apps/skills/convert-web-app/SKILL.md`（544 行）
- **宿主接入文档**：`~/Desktop/SproutHarness/.claude/worktrees/feature+mcp-apps/docs/howto/mcp_apps_development_guide.md`（576 行）
- **宿主能力矩阵（权威）**：`…/docs/design/agent/mcp_apps_design.md` §十（表 A/B/B2/C/D/E + §10.7 宿主形态自评）
- 宿主实现：`…/src/sprout_harness/agent/webui.html`（`:924-985` 能力处置表、`:5040-5072` `_buildHostContext`、`:5274-5287` `_takeAppContextFor`、`:5288-5360` App 消息确认卡、`:5360-5510` handler 实现）；`…/mcp/sandbox.py`；`…/mcp/client.py:145-186`（⭐ visibility 读取路径）；`…/agent/graph.py:40-140,746-778`；`…/defaults.py:85-123`
- 宿主自身的宿主模拟器与测试范式：`…/src/sprout_harness/agent/mcp_apps_tester.html`、`…/tests/test_mcp_apps_host_matrix.py`
- 宿主自查：`…/docs/progress/1016_mcp_apps_development.md`、`1017`、`1018_mcp_apps_followup_audit_and_fix_plan.md`（N01–N27；N15 与 `isolation` 整类仍未修）
- 本项目 bridge：`tools/bridge_core.py`（`accept_intent :1026-1052`、`await_intent :964-1013`、`retry_intent :1064-1108`、线程模型 `:439-447`）、`tools/bridge_mcp.py`、`editor.html`（`bridgeSubmitIntent :7599-7615`、`bridgeHandleDeckChanged :7458-7469`）
- Cowart：`~/Desktop/Cowart/mcp/lib/widget-resource.mjs`、`src/cowartClient.js`、`scripts/build-release-artifacts.mjs`
- 前置调研：`mcp-bidirectional-research.md`；被取代：`ext-apps-dual-track.md`
- 本机实测（已固化）：`tests/harness/z_sandbox_matrix.py` → `tests/harness/results/z_sandbox_matrix.json`

---

## 10. 实施偏差记录（2026-10-21，P1 + P2 + P3 实施）

> 本节记录**实际落地与本文原设计不一致的地方**，以及不一致的理由。冲突时以本节 + 代码为准。

### 10.1 轨 A 的传输层并没有"整层不启动"（修正 §0 / §4.1 / §8.2）

原设计把轨 A 描述为"loopback HTTP / SSE / 凭证 / 心跳 / lease / bootstrap 整层不启动，`bridge_mcp.py` 同进程直接持有 `BridgeCore`"。实施时这条**做不到**，原因有两条硬事实：

1. `BridgeMCP.__init__` 在 MCP server 启动时就调用 `ensure_daemon()` 拉起 daemon —— 而宿主是否支持 MCP Apps 要到 `initialize` 之后才知道（§3.1 已证明注册期早于 `initialize`）；
2. 同一个 workdir 上不允许两个 writer（`WorkdirLock`），因此"MCP 进程内再持一个 `BridgeCore`"会与 daemon 抢锁，或在无锁模式下破坏单写者不变量。

**落地**：app-only 工具复用同一条 loopback HTTP 通道（management 凭证，与五个模型工具完全一致）。
**代价**：轨 A 仍有一个本机 loopback 端口（原设计想省掉的那一层）。
**收益**：① 单写者/状态机不变量零破坏，`BridgeCore` 真正"原样复用"；② 设计 §6.2 第 4 条的异步约束**自动满足**——`BridgeCore.await_intent` 的同步轮询运行在 daemon 自己的线程里，不会堵住 MCP 进程服务 View 的事件循环，因此**不需要 async 变体**（该项视为已由架构消解）。
**若要回到"整层不启动"**：需要先有"宿主能力可提前获知"的信号（例如由宿主在启动参数里声明），否则只能靠本次这种实证路线。

### 10.2 仲裁相位落在 MCP 层，不落 `BridgeCore.await_intent`（修正 §4.2 / §6.2 第 6 条）

原设计把仲裁相位放进 `await_intent`（隐含指 `BridgeCore.await_intent`）。实施改为 `tools/bridge_mcp.py:_arbitrate_view()`：

- `BridgeCore.await_intent` 的阻塞语义是**双轨共用单点**，改它会牵动 44 个 core 单测与 HTTP 层回归（`u_bridge_stability_check` / `s_bridge_scale_check` 亦依赖其时延特征）；
- 只有 MCP 层知道客户端能力（`apps_declared()`），仲裁与 `mode_hint` 应共用同一个判据。

三条硬化照旧实现：① **已决即采用**（`view_attached` → 直接返回 `kind="mcp_app"` 不阻塞；`page_online` → 落既有阻塞逻辑）；② **自解除**（只在"本会话从未出现过任何 UI 信号"时付一次窗口，判据 `get_status.ui_signal_ever`）；③ **窗口 = 存在性窗口 + 4s**。另加一条硬化：**窗口从 `timeout_sec` 里扣**（`min(window, max(0, timeout_sec-1))`），使 `await_intent(timeout_sec=1)` 这条"用户不点确认"的兜底轮询路径保持零时延。

### 10.3 工具面双模改为"**列举期**分流"（部分修正 §3.1 第 2 条）

原设计断言"不能按能力注册两套工具集，只能在调用期分流"。前半句仍然成立（注册期早于 `initialize`），但**`tools/list` 发生在 `initialize` 之后**，因此可以在**列举期**按客户端能力过滤：

- 声明了 `io.modelcontextprotocol/ui`（或环境变量 `PPTX_HTML_APPS_TOOLS=always`）→ 列出 14 个工具（1027 精简前为 18）；
- 否则（`auto` 默认）→ 只列出面向模型的 5 个。

这条改动的价值：轨 B（当前唯一真实宿主）看到的仍是**恰好五个工具**，`AGENTS.md` 红线与既有 `r_bridge_check` 断言**零改动**通过；轨 A 宿主才看到 9 个 app-only 工具（1027 精简前为 13）。
**已知限制**：【实测】官方 Python `ClientSession` **无法声明 `extensions`**（构造参数里没有该入口），所以"能力声明"这条路只有自带宿主才有；**能渲染 widget 却不声明扩展**的宿主（SproutHarness）需要 `PPTX_HTML_APPS_TOOLS=always`（另有 `never` 用于强制关闭）。

### 10.4 `get_status` 的轨道信息放顶层，不动 `capabilities`

原设计写"`get_status.capabilities` 增 `track` 与 `view_attached`"。实施改为**顶层字段** `track` / `view_attached` / `ui_signal_ever`，`capabilities` 保持原三键不变——既有回归里 `capabilities == {...}` 是**精确相等**断言，扩键会打破它，而"轨道"本身也不是"能力"。

### 10.5 management 凭证可走浏览器路由（安全边界说明）

轨 A 的 View 没有 browser 凭证，其工具调用经 MCP server 以 **management** 凭证到达 daemon。因此以下路由从"browser only"改为"management 或 browser 二选一"：`/api/intent`、`/api/intent/retry`、`/api/intent/cancel`、`/api/intents/query`、`/api/save`、`/api/rollback`、`/api/bridge/asset`、`/api/bridge/draft`（其中 draft 的 `client_id` 绑定校验仅对 browser 调用生效）。`/api/save` 与 `/api/rollback` 本来就已是这个形状，本次只是把其余几个对齐。
**信任边界不变**：management 凭证是 MCP server 自己的、本就可经 `/api/bridge/*` 管理全部状态；**session 归属改由工具层 `tools/bridge_dispatch.py` 自校验**（`SESSION_NOT_OWNED`），不依赖宿主鉴权——这正是 §5.8 对策的落地。

### 10.6 新增三条只读路由（design §4.3 的 read_* 落地方式）

`/api/bridge/attach`、`/api/bridge/read`、`/api/bridge/asset-read`、`/api/bridge/export-read` 均为 **management only**。read 类只放行**已登记**文件（`bundle_files` 白名单 + `SecureRoot` 的 O_NOFOLLOW 逐级打开 + `normalize_rel` 拒绝 `..`/`.pptx-html`），未登记即 404；单次读取上限 8 MiB（文档）/ 24 MiB（产物），超限回 `PAYLOAD_TOO_LARGE` 并提示在宿主工作目录取件。

### 10.7 `open_browser="auto"` 成为 schema 默认（轨 B 的可观测代价）

`open_editor` 的 `open_browser` 类型扩为 `bool | "auto"`，**默认 `"auto"`**：起一个存在性窗口（默认 8s，`PPTX_HTML_VIEW_WAIT_SEC` 可配、上限 120s、设 0 即等价旧行为），窗口内收到 `attach_view` 则不开浏览器，否则照旧打开。

**`"auto"` 由 MCP 层按客户端能力解析**（实施时加的硬化，为避免"不支持 MCP Apps 的宿主白等 8s"）：
- 工具面已打开 app-only 工具（客户端声明了 UI 扩展，或运维设了 `PPTX_HTML_APPS_TOOLS=always`）→ 真按 `"auto"` 起存在性窗口；
- 否则（默认 `auto` 且未声明）→ **解析为 `true`，立即开浏览器**，与升级前逐字节同体验。
返回值里带 `open_browser_resolved` 便于诊断。显式传 `true`/`false` 时该解析不生效。
**代价（必须如实记）**：在不支持 MCP Apps 的宿主上，独立浏览器最多晚 8s 打开。按上面的解析规则，该代价只落在"声明了扩展/开了工具面、却没有渲染视图"的宿主上；默认路径（未声明）不付这个代价。
**缓解**：`skills/html-pptx/SKILL.md` 的桥流程显式传 `open_browser="auto"`（语义显式），运维可设 `PPTX_HTML_VIEW_WAIT_SEC=0` 回到旧行为。

### 10.8 View bundle 与门面（§6.3 落地）

`tools/ext_apps_bundle.js` = 官方 `@modelcontextprotocol/ext-apps` 的 View 侧 bundle（源 sha256 记于产物首行与 manifest）经"末尾 ESM `export{...}` → `const __ext = {...}`"改写后，拼上本项目的 `tools/ext_apps_facade.js`（`window.pptxMcp` 门面）。构建脚本 `tools/build_ext_apps_bundle.py`（`--check` 可校验产物是否最新），manifest `tools/ext_apps_bundle.json`。
注入方式与设计略不同：**引导脚本（classic，定义 `window.pptxMcp` 占位与 `ready`）+ bundle（classic，包在 `(function(){"use strict"; …})()` 里）**，而非 `<script type="module">`。理由：module 脚本天然 defer，会在 `editor.html` 自身启动脚本**之后**执行，`hostKindDetect()` 就看不到门面而错误回落到轨 B/静态态。引导脚本保证**同步可见**，实现随后覆盖（`__install`），`ready` 在握手完成后 resolve。
产物尺寸【实测】约 **626 KB**（`editor.html` 428 KB + bundle 254 KB − 注入开销），低于宿主 2 MB 静默失败线，构建期在 >1.5 MB 时告警。

### 10.9 P3 实际交付范围（诚实清单）

**已实现**（`editor.html` 的 `mcpApp*`）：`ready`/`attach_view`/`get_status`/`read_deck` 载入渲染、`save_deck`（CAS + receipt + Git 初始化确认）、`write_asset`（换图后随即保存引用）、`submit_intent`（指令型不因陈旧基线阻断 + `anchor` 上报 + 敲门短句）、`save_draft` 草稿（防抖）+ `setModelContext` 便条（2s 防抖，含 D5 的 `active_edit`/待处理数/批注数）、2s 轮询 `get_status`（空闲退避 10s、`document.hidden` 暂停、远端 revision 变化走"有脏则先保草稿 + 横幅"）、`read_export` + `downloadFile`（>20 MB 回落"告知路径"）、`list_versions`/`rollback`、`onteardown` 异步 flush 草稿后才回执、图片按可见页懒加载 `read_asset` → `data:` URI（保存序列化时还原 `assets/` 相对路径）。**10.11 起补充**：资产水合并含 deck 文档的 `@font-face` 与 CSS `url(assets/…|fonts/…)`（无需反向还原）；高度上报落地（`hostViewportMaxHeight()` 实读 `hostContext.containerDimensions`，`mcpAppReportSize()`/`mcpAppSizeWatch()` 去重上报期望高度）。
**未实现（明确记录，勿当已做）**：
- §5.10.4 的**批注批次分组 UI**（每条状态：待处理/处理中/已应用/已重定位/已失效）与"新 revision 载入后重解锚点标黄"；
- §5.11 的**对比质检产物按可见页懒加载**（轨 A 下对比视图目前仍依赖 `exportBaseUrl`，轨 A 不可用 → 视为**轨 B 独有**，与设计允许的降级一致）；
- `PPTX_HTML_APPS_TOOLS` 之外的**能力自动发现**（官方 Python 客户端无法声明扩展，见 10.3）。

### 10.10 ⚠️ 重大发现：宿主沙箱只有 `allow-scripts` 时，嵌套渲染文档**不可访问**（修正 §1.2）

§1.2 把"嵌套 `iframe srcdoc` 可用"记为**重大利好**，并推断"editor.html 现有『deck 装进 srcdoc iframe』的渲染架构可原样保留"。**10-21 实测表明这条推断只在规范沙箱下成立**：

| 宿主沙箱 | 嵌套 srcdoc 能**显示** | View 能**访问**嵌套文档（`contentDocument`） |
|---|---|---|
| `allow-scripts`（SproutHarness 当前做法，不透明源） | ✅ | ❌ **`contentDocument === null`** |
| `allow-scripts allow-same-origin`（MCP Apps 规范要求） | ✅ | ✅ 可读写 |

【实测】`tests/harness/mcp_apps_host_sim.html` 两臂 + 最小复现：外层 `sandbox="allow-scripts"`（`location.origin === "null"`）时，无论内层 iframe 是否加 `allow-same-origin`，父文档都拿不到它的 `contentDocument`（内层拿到的仍是**另一个**不透明源）。

**可复现证据（本项目自己的仪器）**：`tests/harness/z_sandbox_matrix.py` → `tests/harness/results/z_sandbox_matrix.json` 的 `nested srcdoc contentDocument` 探针：
- `sandbox=allow-scripts`（origin `null`）→ **FAIL: contentDocument 为 null（不透明源不可访问）**
- `sandbox=allow-scripts allow-same-origin`（origin `http://…`）→ **OK**
（该探针 10-21 补入；此前矩阵只测了"嵌套 srcdoc 能加载"，漏掉了"父文档能否访问它"。）

**后果**：轨 A 的编辑器在"只有 allow-scripts"的宿主里**只能显示、不能编辑**——而编辑能力（就地文字编辑、批注、序列化保存）全部依赖 `frame.contentDocument`。sandbox 属性由宿主决定，本项目无法在协议内覆盖（`_meta.ui.permissions` 白名单只管 camera/mic/geolocation/clipboardWrite）。

**决策（2026-10-21，用户）：走官方规范路径，不做降级。** 本项目**不为不合规宿主实现只读降级模式**，也不为此重构 `doc()` 体系（原候选 ② Shadow DOM 内联、③ 注入编辑代理：**均不实施**）。

**2026-10-22 复读宿主源码后的更正（替换上一版"后续会支持 allow-same-origin"的表述）**：
- 宿主当前仍是 `webui.html:2138` `iframe.sandbox = 'allow-scripts'`（**硬编码，无配置项**），View 走**同源**路由 `/mcp-sandbox/{appInstanceId}`（HTTP 头下发 CSP，非 srcdoc）；
- 这是**有意为之的安全姿态**，不是遗漏：`docs/design/agent/mcp_apps_design.md:805 / 835 / 910` 明确写"不加 `allow-same-origin`，防止访问父页面 DOM"，并作为安全项列出；
- 宿主自评 `§10.7` 仍把 **`isolation`（独立 origin sandbox-proxy / owner 隔离 / 身份）列为未做缺口**，`§12.1` 把它排为后续"D 隔离与身份"项（与 1018 门禁合并）；
- 因此**宿主的计划不是"给同源沙箱放开 allow-same-origin"**（那会让不可信 HTML 触达宿主源与存储，他们明确拒绝），而是**官方独立 sandbox origin 结构**：View 跑在**另一个源**上，天然有真实源且仍与宿主隔离。
- **对蓝图的准确表述**：轨 A 的完整编辑能力要求"**View 运行在有真实源的容器里**"；满足方式有两条——① 官方**独立 sandbox origin**；② 为该 iframe 放开 `allow-same-origin`。编辑器状态栏/横幅与宿主日志文案按这两条写。

**2026-10-22 13:25 再次复读（当日新提交 `6e87ef5`）——条件已可满足**：
- 宿主已把沙箱做成**配置项**：`iframe.sandbox = MCP_APP_RUNTIME.iframeSandbox`（`webui.html:2138`），取值由 `mcp.apps.allow_same_origin` 决定（`server.py:555-605`）：`false`（**仓库默认**）→ `allow-scripts`；`true` → `allow-scripts allow-same-origin`（`defaults.py:129-130`；其 docstring 明说该模式"让 MCP Apps 加载工作区资源"）。
- 仓库内 `apps/*/config_*.yaml` **尚未开启**该键，故默认形态下"两条都不满足"仍成立——但**开关已在**：部署侧置 `mcp.apps.allow_same_origin: true` 即可让轨 A 拿到真实源。
- **本项目据本次复读做的两处调整**（只与"有真实源"模式相关，轨 B 零影响）：
  1. 轨 A 下**不设产物基址**（`triDeckBase`/`triBaseUrl` 置 null）：有真实源后相对路径会打到**宿主源**（404 噪音，甚至误读宿主资源）；产物读取只走 `read_export`，对比/导出视图明确报"无产物通道"。
  2. 对比/导出视图的失联原因文案去掉"file:// 直开"这一在轨 A 下**不成立**的归因（四处），改为"无产物通道"并写明两种成因。
- 验收矩阵同步：`mcp_apps_host_sim.html` 两臂与宿主配置一一对应（`?sandbox=trusted` = `allow_same_origin:true`；`?sandbox=host` = 默认 false），`aa_mcp_apps_check.py` 的受信臂/负例臂据此改名并各自断言。

**落地**：`mcpAppLoadDeck` 装载后检查 `doc()`，失败即**明确报错 + 处置指引**（状态栏"宿主沙箱不符合规范"、横幅与宿主日志写明需要 `sandbox="allow-scripts allow-same-origin"`、并提示可暂用轨 B 独立窗口），随后**不进入编辑态**——这是错误路径而不是"只读模式"。`tests/harness/aa_mcp_apps_check.py` 的负例臂（`?sandbox=host`）把这条预期固化成断言，并断言文案里**不得出现"只能查看"这类降级措辞**。

**分工提示**：模拟器默认走规范沙箱；宿主侧改造（SproutHarness 的 iframe sandbox 加 `allow-same-origin`）在宿主仓库，不在本项目。

### 10.11 MCP Apps 合规审计后的最小修复（2026-10-22，A1 / A2 / A4）

审计全文与方法见 `docs/progress/1022_mcp_apps_compliance_review.md`（官方 ext-apps 2.0.3 + 稳定规范 `2026-01-26/apps.mdx` 对照；A3 与 B/C 组留待后续讨论）。本节只记**与本文档既有描述相关的落地事实与更正**：

1. **错误载荷的机器可读性（A1）**：MCP Python SDK 会把任何工具异常重新包成 `Error executing tool <name>: <消息>`（`mcp/server/fastmcp/tools/base.py:117`），且该分支**不带 `structuredContent`**。因此 §233-234 承诺的"`isError` 时从 structured 与文本两处找 `error.{code,message,details}`"在修复前**并不成立**；现在由门面 `stripToolPrefix()` 先剥前缀（再宽松取首个 JSON 对象），该承诺才真正成立。视图侧与模型侧看到的错误文本仍带 SDK 前缀，属 SDK 既定行为。
2. **`size-changed`（A2）**：View 的 `ui/notifications/size-changed` **一直存在**——官方 `App({autoResize:true})`（默认）在 `connect()` 里自动上报文档尺寸。本文档 §5.6 的 `hostViewport` 抽象此前只剩 `hostViewportMaxHeight()` 返回 null 的钩子；**现已落地**：读 `hostContext.containerDimensions.maxHeight`（无则退化为文档自身高度），握手后与容器变化时去重上报一次。宿主仍只跟随高度、宽度不动、钳制 `maxHeight`。
3. **轨 A 的 CSS 资产（A4）**：§5.2 方案 a 的"资产经 `read_asset` → data: URI"此前只覆盖 `<img src>`；现扩到 deck 文档的 `@font-face` 与任意声明里的 `url(assets/…|fonts/…)`（`mcpAppHydrateCss`）。**不需要反向还原**：CSSOM 的改动不回写 `<style>` 文本（文本是源码），序列化出来的 deck 天然是相对路径原文——与 `<img>` 的属性改动会进 DOM 的情形不同（那条仍需 `data-pptx-src` 还原）。§5.2 若按"CSS 也要还原"理解，以此为准。
4. **残留（记录在案，未修）**：规范默认 CSP（spec §275-285）未列 `font-src`，落到 `default-src 'none'` 会挡掉含 `data:` 在内的全部字体；参考宿主 `examples/basic-host/serve.ts:84` 则允许 `font-src 'self' data: blob:`。`_meta.ui.csp` 无法表达 `data:`，故水合后的字体能否显示取决于宿主实现。

### 10.12 MCP server 全面审计后的修复（2026-10-23）

审计全文（方法、逐条证据、变异测试）见 `docs/progress/1024_mcp_server_audit.md`。它对本文档的影响有三处，**以本节为准**：

1. **错误信封（F9）——推翻 §10.11 第 1 条的后半句**。原文说"视图侧与模型侧看到的错误文本仍带 SDK 前缀，属 SDK 既定行为"；现在**服务端不再让前缀出现**：`BridgeFastMCP.call_tool` 兜住失败（含 pydantic 参数校验错），直接构造 `isError=true` + **纯 JSON 文本**的 `CallToolResult`（低层 `lowlevel/server.py:546` 对 `CallToolResult` 原样透传，故不会拿错误载荷去撞成功路径的 `outputSchema`）。§233-234 的承诺因此**无条件成立**，门面里的 `stripToolPrefix()` 降级为针对其它宿主/SDK 版本的防御。副作用：错误结果**不带 `structuredContent`**（有意为之）。
2. **传输层源校验（F6，即 §10.11 里"留待讨论"的 A3）**：View 的 `app.connect()` 必须显式传 `eventSource`（`new PostMessageTransport(window.parent, window.parent)`，与官方 `App.connect` 默认一致）。此前少了第二个参数，任何窗口都能向 View 注入 JSON-RPC；View 自身会创建嵌套 deck iframe，风险不是纯理论。
3. **`_meta` 的规范面收敛（F4 / F5 / F11）**：`visibility` **只**写 `_meta.ui.visibility`（去掉根级双写——规范明确否决扁平键）；客户端能力门在扩展键之外**必须**校验 `mimeTypes` 含 `text/html;profile=mcp-app`（缺省按宽松处理）；资源补显式 `prefersBorder: false`；18 个工具统一补 `title`（集中在 `tools/bridge_mcp.py:TOOL_TITLES`）。

另有两处**属于服务可用性与归属语义**的修复，也请以审计文档为准：daemon 启动失败不再拖垮 MCP server（注册期与 daemon 解耦）、会话归属判定从 MCP 进程内存**下沉到 daemon**（`consumers` 表），因此 §4.2 里"内存 `owned_sessions`"的描述与 §3.1 的"工具层自校验"实现均已改口径。版本号亦改为**单源**：`editor.html` 头部 → 构建脚本 → bundle manifest → server 上报（§3.1 曾有两处字面量，会产生"编辑器 v3.9.3 / 上报 3.9.2"的漂移）。

### 10.13 1027 工具面精简（2026-10-27，用户签字；修正 §4.3 的清单与 §10.3 的计数）

**触发**：用户提问"为何需要这么多工具"。体检结论：18 个里 **3 个全仓无调用方**、**2 个打同一个 daemon handler**；而 13 个 app-only 的由来是**路线对齐**（每个 ≈ 一条浏览器 HTTP 端点 + 一条沙箱缺口），不是 13 个功能。逐条证据（含 file:line）见 `docs/progress/1027_tool_surface_slimming.md`。

**改动**（app-only **13 → 9**，工具面 **18 → 14**）：

1. **删 `cancel_intent` / `retry_intent` / `query_intents`**：三者只在服务端测试里被调用，View 侧零调用点；而它们的 UI 对应物（`editor.html` 任务面板的「取消 / 停止处理 / 续用原副本 / 从当前版本重建」）走的是**轨 B 的 `bridgeFetch` + `bridge.token`**——沙箱里拿不到该凭证，轨 A 点必失败（现状是"工具是死的、按钮是坏的"）。**daemon 侧 `/api/intent/cancel`、`/api/intent/retry`、`/api/intents/query` 三条路由保留**（轨 B 浏览器与 `bridgeRecoverIntents` 继续使用）；轨 A 同步撤掉那组按钮。轨 A「停止处理」的替代路径为模型侧 `close_session`（中断未完成 attempt 并释放 lease）。
2. **`read_asset` + `read_export` → `read_bundle_file(session_id, path)`**：入参统一为 **bundle 相对路径**，由 `tools/bridge_dispatch.py` 按前缀路由（`assets/`｜`fonts/` → `/api/bridge/asset-read` 原样；`export/` 剥前缀 → `/api/bridge/export-read`）。两者本就是同一个 `read_artifact(kind=...)`（`bridge_core.py:1039`，`read_export_file` 只是 5 行 shim），**daemon 契约与 `bundle_files` 白名单一字未动**。

**明确不做**（评估后否决，理由见 progress §2.4）：合并 `save_deck` / `write_asset` / `rollback`（同一 CAS 发布族，但校验、事件、`allow_git_init` 各异，合并会把共享校验的爆炸半径放大到三条写入路径）；通用 `bridge_request(method, path, body)` passthrough（等于把 daemon **全部**路由的写权限交给沙箱，并丢掉逐工具 `readOnlyHint`/`destructiveHint` 所承载的宿主同意语义）。

**遗留**：`read_bundle_file` 的 `export/` 分支在轨 A 本就落在本文 §5.11 声明的"无产物通道"降级路径上；若后续确认轨 A 不再提供产物下载，该分支连同 `/api/bridge/export-read` 可再收一层（工具面到 13）。
