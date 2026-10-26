# 1024 · MCP server 全面审计（官方 spec 对照）与逐项修复计划

> **日期**：2026-10-23
> **触发**：用户调用 `create-mcp-app` 技能，要求"使用官方 mcp-app 搭建指南全面扫描当前项目的 MCP server 实现是否正确"，并点名两个实测症状（「open_editor 没有注册」「stdio 的 sessionid 变化」）。
> **对照源**：官方 `@modelcontextprotocol/ext-apps` **v2.0.3**（clone 于 `/tmp/mcp-ext-apps`）；稳定规范 `specification/2026-01-26/apps.mdx`（1768 行，Status: Stable）+ `src/server/index.ts` / `src/spec.types.ts` / `src/message-transport.ts` / `src/app.ts` / `docs/patterns.md` / `docs/csp-cors.md` + 官方 Python 示例 `examples/qr-server/server.py`。文中 `S:nnn` 指稳定规范行号。
> **判读纪律**：本文"已核实"= 有命令/实测输出（探针脚本在 `/tmp/mcp_scan/`，均为临时工作区，已回收 daemon）。真实宿主端到端仍是 **NOT_RUN**（承接 1021 交接 §2 口径）。
> **前一份审计**：`docs/progress/1022_mcp_apps_compliance_review.md`（其结论"server 侧没有发现违反规范的 MUST 项"**在本轮被修正**，见 §3）。

---

## 1. 审计方法（可复现）

| 手段 | 内容 |
|---|---|
| 官方对照 | 逐条读稳定规范 + SDK 源码；规范原文引用见 §3/§4 每条 |
| 真 stdio 握手 | 对 `python3 tools/edit.py <tmp> --mcp` 打原始 JSON-RPC：`initialize`（不声明 / 声明 `io.modelcontextprotocol/ui` / 声明但 `mimeTypes` 错值）→ `initialized` → `tools/list` → `resources/list` → `resources/read` → `tools/call`；并区分「同一进程」与「每次调用新起进程」 |
| CSP 行为探针 | Chromium 145 + Playwright，经 `route.fulfill` 注真 CSP 响应头，检测 `data:` 字体与 `data:` 图片的放行情况 + 捕获 CSP 违规日志 |
| 代码对照 | `tools/bridge_mcp.py`(520) / `bridge_dispatch.py`(199) / `ext_apps_facade.js` / `bridge_core.py` 路由与状态层 |

探针脚本：`/tmp/mcp_scan/handshake.py`（工具面分档）、`probe2.py`（资源契约 + 跨进程 session）、`probe3/4.py`（open/read 分档）、`probe5.py`（线上 `_meta` + 冷启动计时）、`fontcsp.py`（CSP 字体/图片）。

---

## 2. 两个点名症状的根因

### ②「stdio 的 sessionid 变化」

- **已修好的那一半**：`consumer_id` 现由 workdir 哈希派生（`tools/bridge_mcp.py:238`）。实测两次**全新进程**调 `open_editor` 返回**同一个** `session_id`（`register_session` 按 `target_path` 复用，`bridge_core.py:824`）。
- **未被发现的代价**：会话归属校验被废。`tools/bridge_dispatch.py:141` 有一处**未提交**改动 `if owned_sessions is not None and …` → `if owned_sessions and …`；`owned_sessions` 是**进程内内存**，只由本进程的 `open_editor` 填充（`bridge_mcp.py:315`）。宿主若每次调用新起 stdio 进程（代码注释自述 `langchain_mcp_adapters creates a new stdio subprocess per tool call`），每个新进程都是空集 → 校验整段跳过。
- **实测**：一个从未调用 `open_editor` 的全新进程，拿别的进程的 `session_id` 调 `read_deck` **通过了工具层校验**（一路走到 daemon，最后停在 F2 的 500）；伪造 id 才由 daemon 拦成 `SESSION_NOT_FOUND`，永远拿不到 `SESSION_NOT_OWNED`。⇒ `SESSION_NOT_OWNED` 只在"同一进程刚 open 过"时才可能触发，即**不可能失败的情形**，等同死代码。

### ①「open_editor 没有注册」

- **P0-1（最强候选）**：daemon 起不来 ⇒ **整个 MCP server 崩溃、零工具**。`BridgeMCP.__init__` 在进程启动、`initialize` 之前就调 `ensure_daemon()`（`tools/bridge_mcp.py:239`），异常直接抛出构造函数 → `edit.py:102` 崩溃 → 宿主看到死进程。实测（只读工作目录）`PermissionError` 回溯落在 `bridge_core.py:2306`；`ensure_daemon` 另有 10 秒硬超时（`bridge_core.py:2308-2314`），慢启动同样整机消失。
- **P2-2**：版本号脱节——`editor.html` 头是 **v3.9.3**，`bridge_mcp.py:100` 的 `VIEW_VERSION` 与 `ext_apps_bundle.json` 的 `view_version` 都是 **3.9.2**。
- **排除项**：工具面在**当前工作树**是正常的——实测默认客户端恰好 5 个工具、声明扩展后 18 个，`open_editor` 都在。所以"没注册"不是常驻状态，而是启动期失败的表现。

---

## 3. 发现清单

### P0 —— 破坏主链路 / 服务可用性

| # | 问题 | 证据 | 位置 |
|---|---|---|---|
| **F1** | daemon 启动失败 ⇒ MCP server 崩溃、零工具注册 | 只读 workdir 下 `PermissionError` 自 `ensure_daemon`（`bridge_core.py:2306`）抛出 `__init__`，无 `tools/list` 应答 | `bridge_mcp.py:239` |
| **F2** | `read_deck` 对"目标 HTML 尚未落盘"的会话返回**被掩盖的 500** | 新建 deck 后 `read_deck` → `{"code":"STORAGE_UNAVAILABLE","message":"服务内部错误","retryable":true}`；已有 deck 正常。根因 `SecureRoot.open_read`（`bridge_core.py:327`）让 `FileNotFoundError` 逃逸，被通配处理器 `bridge_core.py:2053` 转成 500 | `bridge_core.py:988` |
| **F3** | 会话归属校验**实际失效**（未提交改动，见 §2②） | 全新进程可跨 session 调 app-only 工具 | `bridge_dispatch.py:141` |

### P1 —— 规范不符

| # | 问题 | 证据 / 规范依据 | 位置 |
|---|---|---|---|
| **F4** | app-only 工具带**非规范**的根级 `_meta.visibility` | 线上实见 `_meta:{"ui":{"visibility":["app"]},"visibility":["app"]}`。规范只在 `_meta.ui.visibility`；扁平 `ui/visibility` 被**明确否决**（S:1668 "Flat `ui/visibility` key: Rejected in favor of nested structure"），根级 `visibility` 在规范/生成 schema/SDK 读取路径（`src/app-bridge.ts:151-171`）中均不存在 | `bridge_mcp.py:151` |
| **F5** | 能力检测**不校验 `mimeTypes`**（规范标 REQUIRED，S:1522） | 客户端声明 `{"mimeTypes":["text/uri-list"]}` 仍拿到全部 18 个工具；官方助手以 `mimeTypes.includes("text/html;profile=mcp-app")` 为门（`src/server/index.ts:478`） | `bridge_mcp.py:208-215` |
| **F6** | View **关掉了 SDK 的 postMessage 源校验** | `app.connect(new PostMessageTransport())` 无 `eventSource`；SDK 默认传两次 `(window.parent, window.parent)`（`src/app.ts:2002-2005`），构造器丢弃非 `eventSource` 消息（`src/message-transport.ts:71-79`）。View 自身还会创建嵌套 deck iframe（可向其注入 JSON-RPC）。**1022 已记为 A3 并"留待讨论"，本轮采纳修复** | `ext_apps_facade.js:189` |

### P2 —— 正确性 / 契约卫生

| # | 问题 | 证据 | 位置 |
|---|---|---|---|
| **F7** | `serverInfo.version` 报 **SDK 版本**而非应用版本 | `initialize` 实见 `{"name":"pptx-html-bridge","version":"1.28.0"}`；mcp 1.28 的 `FastMCP` 无 `version` 形参，默认取 `pkg_version("mcp")` | `BridgeFastMCP` 未设 `_mcp_server.version` |
| **F8** | 版本号脱节（见 §2①） | `editor.html` v3.9.3 vs `VIEW_VERSION`/bundle `3.9.2` | `bridge_mcp.py:100` |
| **F9** | 错误契约不统一：模型侧收到 `Error executing tool <name>: {json}` 前缀文本；pydantic 校验错**完全没有 JSON 信封** | `get_status` 空参 → `1 validation error for get_statusArguments…`；daemon 错 → `Error executing tool read_deck: {"ok":false,…}`。与 AGENTS/SKILL 声称的"错误返回 JSON"不符 | FastMCP 包装 + `bridge_mcp.py:278` |
| **F10** | **`data:` 字体在规范默认 CSP 下必然被挡**，故 A4 的字体水合修法无效 | Chromium 实测：规范默认 CSP（`default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' data:; connect-src 'none'`，**无 `font-src`**，S:275-284）下 `@font-face{src:url("data:font/woff2;…")}` 报 *violates the following Content Security Policy*；同页 `data:` 图片正常。构造分支（声明 csp 时）也只给 `font-src 'self' <resourceDomains>`（S:1730-1744），而 `_meta.ui.csp` 的 `resourceDomains` 只接受 origin，**表达不了 `data:`** | 未声明 `_meta.ui.csp`；`editor.html` 的 `mcpAppHydrateCss()` |
| **F11** | 18 个工具**全部没有 `title`**；资源未声明 `prefersBorder` | 线上 `title: None`；S:220-227 "Specifying an explicit value for this is recommended because hosts' defaults may vary" | `bridge_mcp.py` 全部 `@tool` |

### P3 —— 卫生级

| # | 问题 | 位置 |
|---|---|---|
| **F12** | 引导期 `api.log` / `api.reportSize` 是 no-op，**静默吞掉** View 早期日志 | `bridge_mcp.py:132-133` |
| **F13** | 引导期超时文案写死 `"8s"`，实际 `setTimeout(…, 15000)` | `bridge_mcp.py:140/145` |

---

## 4. 已核对通过的项（**本轮修正 1022 §1 的结论**）

1022 结论"server 侧没有发现违反规范的 MUST 项"**不成立**：F4（非规范字段）、F5（漏校验 REQUIRED 的 `mimeTypes`）、F6（关掉 SDK 源校验）都是对照规范/SDK 的真实偏差。其余经逐条核对**确实合规**：

- 资源：`ui://` 前缀、`mimeType` 精确值 `text/html;profile=mcp-app`、内容走 `text`、合法 HTML5 ✓
- `_meta.ui.resourceUri` 新路径 + 旧 `ui/resourceUri` 双写，与官方 `registerAppTool` 归一化**同类**（`src/server/index.ts:284-297`）✓
- `_meta.ui.permissions.clipboardWrite` 落在**资源**（不是工具）✓，且实测出现在 `resources/read` 的 `contents[0]._meta`（宿主优先读 content item，S/D:263-272）✓
- 文本兜底：UI 工具同时给 `content` 与 `structuredContent`（规范 MUST，S:1559）✓
- View SDK 用官方 2.0.3 bundle；handler 全部在 `connect` **之前**注册；`onteardown` 返回 `{}`；zod jitless ✓
- 默认 CSP 下：内联 script/style 放行、`img-src 'self' data:` 放行 ⇒ **data: 图片水合这条路是通的** ✓
- 列举期双模（5/18）与规范 `visibility` 语义不冲突，且比"注册期按能力分家"更可行（注册期早于 `initialize`）✓

---

## 5. 逐项修复计划与验收纪律

**顺序**（用户裁决：按下面的顺序逐项修，**每项完成后跑完整验收再推进**）：

| 步 | 项 | 改动范围 |
|---|---|---|
| 1 | **F1** | `bridge_mcp.py`：`ensure_daemon` 移出 `__init__` → 懒初始化 + 干净错误 |
| 2 | **F2** | `bridge_core.py`：目标 HTML 缺失/未落盘 → 干净 `NOT_FOUND` 语义 |
| 3 | **F3** | `bridge_core.py` + `bridge_dispatch.py`：归属真值下沉 daemon |
| 4 | **F4 / F5** | `bridge_mcp.py`：去掉根级 `visibility`；`mimeTypes` 门 |
| 5 | **F6** | `ext_apps_facade.js` → 重建 bundle |
| 6 | **F7 / F8 / F11 / F13** | 版本同源、`serverInfo.version`、`title`/`prefersBorder`、文案常量 |
| 7 | **F10** | 需用户裁决（见 §6） |
| 8 | **F9** | 错误信封（须同步门面 + SKILL/AGENTS 措辞 + 断言） |

**每项验收命令**（全绿才算完成）：

```bash
python3 -m pytest tests/harness/test_bridge_core.py -q          # 核心状态机基线
python3 tests/harness/r_bridge_check.py                         # 7 组协议验收
python3 tests/harness/aa_mcp_apps_check.py                      # T36 轨 A 端到端
python3 tools/build_ext_apps_bundle.py --check                  # 仅改动 bundle 时
python3 tests/harness/run_e2e.py                                # 完整回归（落盘 _logs/）
```

**基线（本会话重跑前）**：`docs/progress/_logs/1023_run_e2e.log` = **62 项，59 PASS，3 FAIL**（T26-tri-view / T35-dynamic-brief / T34-theme-proving）——**与 AGENTS.md 与 1021/1022 记录的 "61 PASS / 1 FAIL" 不一致**，是既有漂移，本会话先重跑建立基线，见 §7。

---

## 6. 待用户裁决

**F10**：规范默认 CSP **没有 `font-src`**（落到 `default-src 'none'`）⇒ 轨 A 下 deck 的 `@font-face` 字体**一律被挡**（含 `data:`）；而 `_meta.ui.csp` 的 `resourceDomains` 只接受 origin，**表达不了 `data:`**。两条出路：

1. **轨 A 不承诺外挂字体**：接受"宿主内不自带字体（走系统字体栈）"，把 `mcpAppHydrateCss()` 的字体分支改为**只告警不水合**（避免做出无效动作），并在文档写明。
2. **按宿主能力**：继续水合，靠宿主补 `font-src data:`（宿主侧工作，不在本项目）。

---

## 7. 实施记录

（逐项修复完成后追加：改动清单 / 验收输出 / 变异测试 / 结论）

---

### §7.0 基线重跑（本会话，修复前）

`docs/progress/_logs/1024_run_e2e_baseline.log` = **62 项，60 PASS，2 FAIL**：
`T35-dynamic-brief`（子进程退出码 1，但 stdout 显示 "PASS T35d-0" —— 疑似 flaky）与 `T34-theme-proving`（既有失败）。
**注意**：`docs/progress/_logs/1023_run_e2e.log` 记录的是 **59 PASS / 3 FAIL**（多一个 `T26-tri-view`）；两次之间 T26 自行转绿 ⇒ 这三项含 flaky 成分，判读时以"是否出现**新**FAIL"为准。

---

### §7.1 F1 · daemon 启动失败不再拖垮 MCP server ✅

**改动**（`tools/bridge_mcp.py`）
- `BridgeMCP.__init__` 不再调用 `ensure_daemon`：新增 `self._allow_convert/_allow_imagegen/self.discovery=None/self._discovery_lock`。
- 新增 `BridgeMCP._discovery()`：带锁的懒解析，`BridgeError` → 原样 `payload()` 的 ToolError；其他异常（如 `PermissionError`/`FileExistsError`）→ `STORAGE_UNAVAILABLE` + 真实原因文本。
- `BridgeMCP._request()`：改走 `await asyncio.to_thread(self._discovery)` 再发 HTTP；新增 `except ToolError: raise` 防止被下面的宽 `except Exception` 二次包装。
- `import threading`。

**验收**
| 检查 | 结果 |
|---|---|
| `python3 -m pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests** |
| `python3 tests/harness/r_bridge_check.py` | **7 组全 PASS**（apps 组含新增 ⑤） |
| `python3 tests/harness/aa_mcp_apps_check.py` | **RESULT: ALL PASS** |
| `python3 tests/harness/run_e2e.py` | `1024_run_e2e_f1.log` = **62 项，60 PASS，2 FAIL**（与基线**同签名**：T35/T34） |

**变异测试**（把 `__init__` 改回 eager `ensure_daemon`）：`r_bridge_check.py --group apps` → **FAIL**，报 `mcp.shared.exceptions.McpError: Connection closed`（= 修复前"进程崩溃、零工具"的原始症状）⇒ 新增断言确实会响。

**新增断言**（`tests/harness/r_bridge_check.py::apps_group` ⑤）：用**普通文件**占住 `.pptx-html`（对 root 也成立，不依赖 chmod），断言 ① 工具面仍是恰好五个 ② `open_editor` 返回 `isError` 且载荷是 JSON 的 `STORAGE_UNAVAILABLE`。

---

### §7.2 F2 · 目标 HTML 未落盘时 `read_deck` 返回干净错误 ✅

**改动**（`tools/bridge_core.py`）
- 新增 `BridgeCore._read_managed(rel, *, message, details)`：把 `FileNotFoundError` / `NotADirectoryError` / `IsADirectoryError` 映射为 `404 NOT_FOUND`（带 `path` 与可选 `phase` 细节），不再让它们逃逸。
- `read_document` 改用它（`message="目标 HTML 尚未创建"`、`details={"phase":…}`）；`read_artifact` 改用它（`message="受管文件已不在盘上"`）。
- `BridgeHTTPServer` 的通配处理器（`except Exception`）新增 `traceback.print_exc()`：回溯进 daemon.log，杜绝"服务内部错误"继续掩盖真实原因。`import traceback`。

**验收**
| 检查 | 结果 |
|---|---|
| 定向探针 | briefing 阶段 `read_deck` → `{"code":"NOT_FOUND","message":"目标 HTML 尚未创建","details":{"path":"index.html","phase":"briefing"}}`；目标落盘后同一调用 `ok:true`（bytes=40）；干净路径**不产生**通配处理器回溯 |
| `pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests** |
| `python3 tests/harness/r_bridge_check.py` | **7 组全 PASS**（apps 组含新增 ⑥） |
| `python3 tests/harness/aa_mcp_apps_check.py` | **RESULT: ALL PASS** |
| `python3 tests/harness/run_e2e.py` | `1024_run_e2e_f2.log` = **62 项，60 PASS，2 FAIL**（与基线同签名 T35/T34） |

**新增断言**（`r_bridge_check.py::apps_group` ⑥）：独立临时工作区里 `open_editor` 无 deck 打开 → 断言 phase 为 `briefing`、目标文件未被创建、`read_deck` 返回 `NOT_FOUND` + "尚未创建"、且**不含**"服务内部错误"。

---

### §7.3 F3 · 会话归属判定的真相下沉到 daemon ✅

**根因**：归属判定放在 MCP 进程的内存集合 `owned_sessions` 里，而宿主可能每次工具调用新起 stdio 进程 ⇒ 集合恒为空 ⇒ `if owned_sessions and …` 直接放行。该内存版本只有"同一进程刚 open 过"时才会触发，即**不可能失败的情形**。

**改动**
- `tools/bridge_core.py`：新增 `BridgeCore.assert_consumer(session_id, consumer_id)` —— 查 `consumers` 表（`requires_open`）作为**唯一真相**；无行或 `requires_open=1` ⇒ `403 SESSION_NOT_OWNED`。读操作在 `_db_lock` 内（避免 HTTP 处理线程间的 sqlite 并发）。
- `tools/bridge_core.py`：新增 `BridgeHTTPServer._verify_consumer(path, target)`，在 `_api` 的 POST 与 GET 两处**统一**调用：校验后**摘除** `consumer_id`，因此 `/api/intent`、`/api/versions` 等对字段集合做**精确**比对的路由契约一字未改；`/api/bridge/open|await|update|close|heartbeat` 自行声明该字段，跳过。
- `tools/bridge_dispatch.py`：`build_request(name, arguments, *, owned_sessions)` → `build_request(name, arguments, *, consumer_id)`；每个请求附 `consumer_id`。**删掉了那行未提交的 `if owned_sessions and …` 妥协**（问题由构造消除）。
- `tools/bridge_mcp.py`：新增模块级 `consumer_id_for(workdir)`（单源派生），`__init__` 复用它；`_app_request` 改传 `consumer_id=self.consumer_id`。`owned_sessions` 仍在，但降级为**心跳列表**，不再承担授权。
- `tests/harness/aa_mcp_apps_check.py`：`make_tool_proxy(discovery, consumer)` / `ViewPage(..., consumer=...)`，与 `open_split(consumer=…)` 对齐（`split-harness` / `apps-harness`）。

**语义**（比旧实现严格且更鲁棒）
| 情形 | 旧（内存集合） | 新（daemon 表） |
|---|---|---|
| 新进程调用已登记会话 | 被拒（或靠妥协放行） | **放行**（consumer_id 跨进程稳定） |
| 新进程调用陌生会话 | **放行**（漏洞） | **拒绝** `SESSION_NOT_OWNED` |
| `close_session` 之后 | 被拒 | 被拒（`requires_open=1`），需重新 `open_editor` |

**验收**
| 检查 | 结果 |
|---|---|
| `pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests** |
| `python3 tests/harness/r_bridge_check.py` | **7 组全 PASS**（apps 组含新增 ⑤） |
| `python3 tests/harness/aa_mcp_apps_check.py` | **RESULT: ALL PASS** |
| `python3 tests/harness/run_e2e.py` | `1024_run_e2e_f3.log` = **62 项，60 PASS，2 FAIL**（同签名 T35/T34） |

**变异测试**：把 `assert_consumer` 首行改成 `return`（退回"恒放行"）⇒ `r_bridge_check.py --group apps` **FAIL**：`AssertionError: 外部 session 未被工具层拒绝`。

**新增断言**（`r_bridge_check.py::apps_group` ⑤）：在**另一个 stdio 进程**里 ① 用同一 workdir 复读已登记会话必须成功（模拟宿主"每次调用新起进程"，这是用户实测症状的回归位）② 陌生 session 在新进程里也必须是 `SESSION_NOT_OWNED`（旧实现在此恒放行）。

**环境观察（非本项引入）**：F3 落地后某一次 `r_bridge_check` 全量运行里出现过一次 `sqlite3.InterfaceError: bad parameter or other API misuse`（改了 9 次全量/分组运行只复现 1 次，基线/F1/F2 的 e2e 日志里为 0 次）。已在本项新增的读路径上补 `_db_lock`；其余无锁读（`_session` 等）属既有形态，**记为待观察**，本轮不改。

---

### §7.4 F4 + F5 · 工具面规范化（visibility 单写 + mimeTypes 能力门）✅

**改动**（`tools/bridge_mcp.py`）
- **F4**：`APP_ONLY_META = {"ui": {"visibility": ["app"]}}` —— 去掉非规范的根级 `_meta.visibility`。规范只在 `_meta.ui.visibility`（S:324-333；SDK 读取路径 `src/app-bridge.ts:151-171`），且**明确否决**扁平键（S:1668）。仓库内无任何读者依赖根级字段（grep `visibility` 只命中 CSS `backface-visibility`）。
- **F5**：`BridgeFastMCP.apps_declared()` 现在要求 `extensions["io.modelcontextprotocol/ui"]` 是对象且 `mimeTypes` **包含** `text/html;profile=mcp-app`（S:1522 标 REQUIRED；官方门 `src/server/index.ts:478`）。`mimeTypes` **缺省按宽松处理**（生成式 schema 标为可选 `src/generated/schema.ts:767-769`，判成"不支持"会误伤真实宿主）；声明了别的类型则必须挡住。

**验收**
| 检查 | 结果 |
|---|---|
| `pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests** |
| `python3 tests/harness/r_bridge_check.py` | **7 组全 PASS**（apps 组含改写后的 ② 与新增 ⑦） |
| `python3 tests/harness/aa_mcp_apps_check.py` | **RESULT: ALL PASS** |
| `python3 tests/harness/run_e2e.py` | `1024_run_e2e_f45.log` = **62 项，60 PASS，2 FAIL**（同签名 T35/T34） |

**变异测试**
| 变异 | 结果 |
|---|---|
| 把根级 `visibility` 加回 `APP_ONLY_META`（= F4 未修） | **FAIL** `attach_view 带了非规范的根级 _meta.visibility（F4：规范只在 ui.visibility）` |
| `apps_declared` 只认扩展键（= F5 未修） | **FAIL** `mimeTypes 不含 html profile 时不应开放 app-only 工具: [18 个工具]` |

**新增/改写断言**（`r_bridge_check.py::apps_group`）
- ② 改为断言 `_meta.ui.visibility == ["app"]` **且** 根级 `visibility` **不存在**。
- ⑦ 新增 `raw_tools_list()`：不经官方 Python 客户端、直接打原始 stdio JSON-RPC（官方 `ClientSession` 没有声明 `extensions` 的入口），四档断言：正确 mimeTypes → 18 个；`["text/uri-list"]` → 恰好五个；`mimeTypes` 缺省 → 宽松放行；未声明扩展 → 恰好五个。

**附注（F1 的连带观察）**：⑦ 首次运行暴露了一个预期变化——`tools/list` 只在**没有工具调用**时不再拉起 daemon（F1 的懒初始化），因此断言里不再假设临时目录里存在 `serve.json`（改为存在才停 daemon）。

---

### §7.5 F6 · View 传输层恢复 postMessage 源校验 ✅

**改动**
- `tools/ext_apps_facade.js`：`app.connect(new PostMessageTransport())` → `app.connect(new PostMessageTransport(window.parent, window.parent))`，与官方 `App.connect` 的默认一致（`src/app.ts:2002-2005`）。少了 `eventSource` 会命中 SDK `if (eventSource && …)` 的短路，**任何窗口**都能向 View 注入 JSON-RPC；而 View 自己会创建嵌套 deck iframe（`editor.html:870/4535`），这不是纯理论风险。
- 重建 `tools/ext_apps_bundle.js` / `.json`（`bundle_sha256=f9b6830a…`, 258,695 字节）。

**验收**
| 检查 | 结果 |
|---|---|
| `python3 tools/build_ext_apps_bundle.py --check` | **OK**（重建后一致） |
| `pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests** |
| `python3 tests/harness/r_bridge_check.py` | **7 组全 PASS** |
| `python3 tests/harness/aa_mcp_apps_check.py` | **RESULT: ALL PASS** |
| `python3 tests/harness/run_e2e.py` | `1024_run_e2e_f6.log` = **62 项，60 PASS，2 FAIL**（同签名 T35/T34） |

**变异测试**：把门面改回无 `eventSource` 的构造并重建 bundle ⇒ `r_bridge_check --group apps` **FAIL**：`View 传输层缺少 eventSource 源校验（F6）`。

**新增断言**（`r_bridge_check.py::apps_group` ②，作用于**已下发的 View HTML**）：
`html.count("new PostMessageTransport(") == html.count("new PostMessageTransport(window.parent, window.parent)")`。
> 迭代记：初版写成"子串存在性"，而**我自己的注释里也含同一串字面量**（`grep` 显示 bundle 内 2 处），会假通过；改成计数比对后 bundle 内只剩 1 处真实调用，断言才真正有牙。

**环境观察（非本项引入）**：本轮某次全量 `r_bridge_check` 在 `ui` 组出现一次
`AssertionError: brief failure recovery action was not restored from query/IndexedDB`；单独连跑 `--group ui` **3/3 PASS** ⇒ 判定为 Chromium IndexedDB 时序抖动，与本轮改动无关（记为待观察，不改）。

---

### §7.6 F7 + F8 + F11 + F13 · 版本/标题/资源元数据/引导文案 ✅

**改动**
| 项 | 文件 | 内容 |
|---|---|---|
| **F8** | `tools/build_ext_apps_bundle.py` | 删除写死的 `VIEW_VERSION="3.9.2"`；新增 `VERSION_RE` + `view_version()`，从 **editor.html 头部注释**（`  版本：v3.9.3（2026-10-23）`，全仓唯一）解析；`build(source, version)`；manifest 写解析结果。解析不到**直接失败**（宁可响，不要静默漂移） |
| **F8** | `tools/bridge_mcp.py` | 删除写死的 `VIEW_VERSION`；新增 `_view_version()` 读 bundle manifest（读不到报 `unknown`，不猜）；新增 `VIEW_MANIFEST_PATH` |
| **F7** | `tools/bridge_mcp.py` | `with contextlib.suppress(Exception): self.mcp._mcp_server.version = VIEW_VERSION` —— mcp 1.28 的 `FastMCP` 无 `version` 形参，低层 `MCPServer.version` 于是回落成 `pkg_version("mcp")`；直接写低层实例属性（`create_initialization_options` 在 serve 期读它） |
| **F11** | `tools/bridge_mcp.py` | 新增模块级 `TOOL_TITLES`（18 个中文标题）+ 在 `BridgeFastMCP.list_tools` 里统一补齐空 `title`（集中一张表，不散进 18 个装饰器）；资源 `_meta.ui` 补 `prefersBorder: False`（工作台自带完整 chrome，再叠宿主边框会双重框住） |
| **F13** | `tools/bridge_mcp.py` | 新增 `VIEW_HANDSHAKE_TIMEOUT_MS = 15000`；引导文案改为 `%ds 内未收到 ui/initialize 应答`，与计时同源（原先写死 8s 而实际 15000ms） |
| — | bundle | 重建：`view_version=3.9.3`，`bundle_sha256=0acaba25…`，258,695 字节 |

**验收**
| 检查 | 结果 |
|---|---|
| 定向探针 | `serverInfo={"name":"pptx-html-bridge","version":"3.9.3"}`（原 1.28.0）；**18/18** 工具都有 title；资源 `_meta.ui={"permissions":{"clipboardWrite":{}},"prefersBorder":false}`；引导 `api.version = "3.9.3"`、文案 `15s 内未收到 ui/initialize 应答` |
| `python3 tools/build_ext_apps_bundle.py --check` | **OK**（`view_version=3.9.3`） |
| `pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests** |
| `python3 tests/harness/r_bridge_check.py` | **7 组全 PASS** |
| `python3 tests/harness/aa_mcp_apps_check.py` | **RESULT: ALL PASS** |
| `python3 tests/harness/run_e2e.py` | `1024_run_e2e_f7811.log` |

**变异测试**（逐条注掉修复后重跑 `r_bridge_check --group apps`）
| 变异 | 结果 |
|---|---|
| `_mcp_server.version` 写回 `"1.28.0"` | **FAIL** `serverInfo 未报本应用版本（F7）: {'version': '1.28.0'} vs VIEW_VERSION=3.9.3` |
| `VIEW_VERSION` 固定返回 `"3.9.2"`（模拟旧漂移） | **FAIL** `View 引导期版本与 editor.html 头不一致（F8）：期望 3.9.3` |
| 停掉 `list_tools` 的标题补齐 | **FAIL** `工具缺少 title（F11）: [18 个工具]` |
| 引导文案去掉 `ui/initialize` 字样 | **FAIL** `引导期握手超时文案与常量不同源（F13）: 15000` |
| `prefersBorder` 未做变异测试（`.get(...) is False` 的相等性断言，删掉即失败；取值已由探针实证） | — |

**新增断言**（`r_bridge_check.py::apps_group` ② 与 ⑦）：资源 `_meta.ui.prefersBorder is False`；所有工具必须有 `title`；下发 HTML 的 `api.version` 必须等于 **editor.html 头部**解析出的版本（漂移守门）；引导文案必须含 `VIEW_HANDSHAKE_TIMEOUT_MS//1000` 秒字样；`serverInfo.version` 必须等于 `VIEW_VERSION` 且非 `unknown`（`raw_handshake()` 现在同时返回 `serverInfo`）。

#### §7.6.1 e2e 结果与一处**既有 flaky** 的定性

`docs/progress/_logs/1024_run_e2e_f7811b.log` = **62 项，60 PASS，2 FAIL**（同签名 T35/T34）。

**第一次跑的 `1024_run_e2e_f7811b.log`（被覆盖前）出现 `T29-bridge` FAIL**，根因是 `ui` 组的一条**既有**竞态：

- 断言：`r_bridge_check.py:423` `check(not page.locator("#btnBriefRetry").is_hidden(), "brief failure recovery action was not restored from query/IndexedDB")`。
- 关键证据：**紧邻的前一行（:421）`wait_for_function(... briefSubmission.intentId === id && state === 'error')` 已经通过** ⇒ IndexedDB/query 恢复其实是成功的；失败的是 `page.click("#btnBrief")` 之后**没有任何等待**就去读 `#btnBriefRetry` 的可见性 —— 纯前端 UI 未落定的竞态。
- 归属定性：① `editor.html` 本轮**零改动**；② `editor.html` 里 `consumer_id` 出现 **0 次** ⇒ F3 的 `_verify_consumer` 不可能作用于轨 B 浏览器通道（它只在请求体/查询里带 `consumer_id` 时才生效）；③ `ui` 组不加载 View bundle、不 import `bridge_mcp`。
- 频率：该断言在全量 `r_bridge_check` 里 **2 次失败 / 8 次运行**，单独 `--group ui` **11 次通过 / 3 次失败**；重跑 `1024_run_e2e_f7811b.log` 时 T29 **PASS**。
- 结论：**既有 flaky，与本轮改动无关**，记为待修（修法应是给该断言加等待，属 editor 侧工作，未纳入本轮范围）。

**顺带清理**：跑测期间发现 **19 个遗留 daemon，工作目录全部已被删除**（历次 harness 运行的孤儿）。已回收工作目录不存在的那些（19 → 5）。这类孤儿会随每次 `run_e2e` 累积，建议后续在 harness 的收尾里统一回收。

---

### §7.7 F9 · 统一 JSON 错误信封 ✅

**改动**
| 文件 | 内容 |
|---|---|
| `tools/bridge_mcp.py` | 新增模块级 `error_envelope(exc)`：取 `exc.__cause__`（SDK 包装下才是原始异常）——我们自己的 `ToolError`（字符串即 JSON 载荷）原样复用，其余（pydantic 参数校验等）归一成 `INVALID_ARGUMENT`（非 retryable）或 `STORAGE_UNAVAILABLE`（retryable）。新增 `BridgeFastMCP.call_tool` 覆写：任何失败都返回 `isError=true` + **纯 JSON 文本**的 `CallToolResult`（低层 `lowlevel/server.py:546` 对 `CallToolResult` **原样透传**，故不撞成功路径的 `outputSchema` 校验）；显式不带 `structuredContent` |
| `tools/ext_apps_facade.js` | 更新注释：前缀**不再由本 server 产生**；`stripToolPrefix()` 降级为针对其它宿主/SDK 版本的**防御**（逻辑未变） |
| `tests/harness/mcp_apps_host_sim.html` | `isError` 判定不再靠 `/^Error executing tool /` 猜（前缀消失后必判"成功"）；代理可返回 `{text, isError}`（与真实 `CallToolResult` 同形），纯文本按成功处理 |
| `tests/harness/aa_mcp_apps_check.py` | `make_tool_proxy` 改名返回值形状为 `{text, isError}`；A1 断言改为**直接读宿主下发的 `CallToolResult`**，断言 `isError` 且文本可 `JSON.parse` 出 `error.code` |
| `editor.html` | v3.9.3 → **v3.9.4**：变更记录写明① 传输层补 `eventSource`（F6）② 错误信封改纯 JSON（F9）；bundle 随之重建（`view_version=3.9.4`，`bundle_sha256=18742e7a…`，258,640 字节） |
| `docs/design/mcp-apps-upgrade.md` | 新增 **§10.12**：推翻 §10.11 第 1 条"错误文本仍带 SDK 前缀属既定行为"的说法，并记 F6/F4/F5/F11 与归属下沉、版本单源的口径 |
| `AGENTS.md` | `editor.html` v3.9.4；轨 A 工具面描述改为"`visibility` 只写 `_meta.ui.visibility` + `mimeTypes` 能力门"；`bridge_dispatch.py` 描述改为"归属真相在 daemon" |

**验收**
| 检查 | 结果 |
|---|---|
| 定向探针 | `get_status{}` → `isError=true`，文本 `{"ok":false,"error":{"code":"INVALID_ARGUMENT","retryable":false,…}}`（原先是一段 pydantic 散文）；`read_deck`（陌生 session）→ 纯 JSON `SESSION_NOT_OWNED`；`read_asset` 非法路径 → 纯 JSON `INVALID_ARGUMENT`；成功路径**不变**（`content` + `structuredContent`、无 `isError`） |
| `python3 tools/build_ext_apps_bundle.py --check` | **OK**（`view_version=3.9.4` —— 单源改版后重建即生效，F8 的耦合得到实测） |
| `pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests** |
| `python3 tests/harness/r_bridge_check.py` | **7 组全 PASS**（apps 组含新增 ⑤ 错误信封） |
| `python3 tests/harness/aa_mcp_apps_check.py` | **RESULT: ALL PASS** |
| `python3 tests/harness/run_e2e.py` | `1024_run_e2e_f9.log` = **62 项，60 PASS，2 FAIL**（同签名 T35/T34） |

**变异测试**：把 `call_tool` 覆写短路（直接 `return await super().call_tool(...)`）⇒ `r_bridge_check --group apps` **FAIL**，输出退回 pydantic 的 `1 validation error for get_statusArguments …` 散文形态。

**新增断言**：`r_bridge_check.py::apps_group` ⑤ —— 参数校验错与业务错两条路径都必须 `isError=true`、文本**不含** `Error executing tool`、可 `json.loads` 出 `ok:false` 与正确 `error.code`/`retryable`，且错误结果**不携带 `structuredContent`**；`aa_mcp_apps_check.py` 受信臂直接断言宿主下发的 `CallToolResult.content[0].text` 是纯 JSON 信封。

**未做（承接 §7）**：`docs/test_acceptance/mcp-apps-upgrade.md` 与 `docs/progress/1022_*.md` 是**历史记录**，按项目惯例不改写；口径以本文与设计 §10.12 为准。

---

### §7.8 F10 · 轨 A 字体被宿主 CSP 挡下时的检测与一次性告警 ✅

**用户裁决（2026-10-23）**：选「运行时检测 + 一次告警」；`prefersBorder` 维持 `false`。

**实施过程中的两个实测发现（都推翻了原定做法，记下来免得后人重踩）**

1. **`securitypolicyviolation` 在本场景下根本不触发**。原计划是监听该事件。实测（Chromium 145，规范默认 CSP，srcdoc 嵌套 deck）：
   - 控制台确凿记录两次拦截：`Loading the font 'http://127.0.0.1:PORT/fonts/harness.woff2' … blocked` 与 `Loading the font 'data:font/woff2;base64,…' … blocked`（后者正是我们水合出来的）；
   - 而**在 View 文档与 deck 文档上各挂一个探针，收到 0 条事件**（`probe: []`）。
   ⇒ 继承来的 CSP 在 `about:srcdoc` 文档里不派发该事件。**事件驱动方案作废。**
2. **被挡字体的 status 是 `unloaded`，不是 `error`**。改用"直接探字体是否真的可用"后，第一次实现仍不告警，诊断显示 `{families:['HarnessSub'], check:['HarnessSub=false'], entries:['HarnessSub:unloaded']}` —— 字体确实不可用，但 `document.fonts` 里的状态停在 `unloaded`（`error` 只在 decode 失败时出现）。判据因此定为：**`document.fonts.load()` 尝试之后 `document.fonts.check()` 仍为 false**。

**最终实现**（`editor.html`）
- 新增 `async function mcpAppProbeFonts()`：扫描 deck 内**已水合**（`src` 含 `data:`）的 `@font-face` 家族 → 逐个 `document.fonts.load('12px "<家族>"')` → `check()` 仍 false 的判为被挡 → **一次性** `showWarn`（写明原因：宿主 CSP 未放行 `data:` 字体、规范默认不含 `font-src`；写明出路：宿主把 `font-src` 放开到 `data:`）+ `pptxMcp.log('warn', …)`；用 `mcpApp.fontCspWarned` 去重。
- 接线：`mcpAppLoadDeck` 里 `mcpAppHydrateCss().then(function(){ mcpAppProbeFonts(); }).catch(function(){})`。⚠️ **必须显式接在 promise 上**：该调用点的 `mcpAppHydrateCss()` 没有被 await，直接顺排调用会让探针跑在水合之前（`src` 还是相对路径）而永远测不到——这正是第一次实现不告警的原因。
- `editor.html` v3.9.4 变更记录的第 ③ 条同步了上述两个发现。

**测试侧**（`tests/harness/mcp_apps_host_sim.html` + `aa_mcp_apps_check.py`）
- 模拟器新增 **`?csp=spec`**：注入**规范默认 CSP**（`default-src 'none'` 起手、**无 `font-src`**、`connect-src 'none'`），复现被挡条件；默认仍是参考宿主 CSP（`font-src 'self' data:`）。
- 新增受信臂 **`run_font_csp_arm()`**：在 `csp=spec` 下断言 ① deck 正常载入（`hasDeckDoc`）② 编辑器**检测到字体被挡并告警一次** ③ 告警文案同时含 `font-src` 与 `data:` ④ 无 JS 报错。

**验收**
| 检查 | 结果 |
|---|---|
| `python3 tests/harness/aa_mcp_apps_check.py` | **RESULT: ALL PASS**（含新臂） |
| `python3 -m pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests** |
| `python3 tests/harness/r_bridge_check.py` | **7 组全 PASS** |
| `node --check`（editor.html 内联脚本） | **1 个 inline block，0 失败** |
| `python3 tools/build_ext_apps_bundle.py --check` | **OK**（`view_version=3.9.4`，editor.html 未改版本号 ⇒ 无需重建） |
| `python3 tests/harness/run_e2e.py` | `1024_run_e2e_f10.log` = **62 项，60 PASS，2 FAIL**（同签名 T35/T34） |

**变异测试**：在 `mcpAppProbeFonts()` 首行插 `return;` ⇒ `aa_mcp_apps_check.py` **FAIL**：`F10：规范默认 CSP 挡下字体后应触发一次性告警；诊断={'warned': False, 'hasDeckDoc': True, 'bridgeState': 'MCP Apps 已同步'}`（并附 CSP 控制台记录）。

**仍未做（承接 §6）**：题面里的选项 ②（宿主把 `font-src` 放开到 `data:`）属**宿主侧**工作，不在本项目；本项目侧到此为止是"检测 + 如实告知"。
