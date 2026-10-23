# 1022 · MCP Apps 合规审计（官方 spec / SDK 对照）与最小修复

> **日期**：2026-10-22
> **触发**：用户调用 `create-mcp-app` 技能，要求"基于技能检查当前项目实现的 mcp-server 是否合法、是否按官方 mcp-app 来，是否存在问题"。
> **对照源**：官方 `@modelcontextprotocol/ext-apps` **v2.0.3**（npm latest，clone 到 `/tmp/mcp-ext-apps`）+ 稳定规范 `specification/2026-01-26/apps.mdx` + 仓库内 View bundle 的源（`~/Desktop/ext-apps` v2.0.3）。
> **判读纪律**：本文件里的"已核对"= 有命令/实测输出；"潜伏/未验证"一律写明。真实宿主端到端仍是 **NOT_RUN**（承接 `1021_mcp_apps_handover.md` §2 的口径）。

---

## 1. 结论

**server 侧（`tools/bridge_mcp.py`）没有发现违反规范的 MUST 项**：工具面、资源契约、文本兜底、CSP 前提、官方 View bundle 来源都经得起对照。问题集中在 **View 侧的三处功能/防护缺口**，以及一类 **MCP Python SDK 包裹错误载荷导致契约失真**（影响面在门面与模型两侧）。

本轮用户裁决：**只修 A1 / A2 / A4（最小改动）**；A3（传输层源过滤）与 B/C 组**留待后续讨论**（见 §7）。

---

## 2. 审计方法与证据（可复现）

| # | 验证 | 命令 / 方式 | 结果 |
|---|---|---|---|
| E1 | 工具面与资源面契约 | 对 `python3 tools/edit.py <tmp> --mcp` 手写 stdio JSON-RPC（两轮：不声明 / 声明 `io.modelcontextprotocol/ui`） | 5 个 / **18 个**工具；`_meta.ui.resourceUri` + 旧 `ui/resourceUri` 双写；资源 `mimeType=text/html;profile=mcp-app`，`text` 660,180 字节 |
| E2 | 错误载荷形状 | 同上，`tools/call get_status{session_id:"bogus"}` | `{"content":[{"type":"text","text":"Error executing tool get_status: {\"ok\":false,…}"}],"isError":true}`，**无 `structuredContent`** |
| E3 | 成功载荷 | 同上，`tools/call open_editor{open_browser:false}` | `content`（JSON 文本）**与** `structuredContent` 同时存在；`outputSchema` 宽松（`additionalProperties:true` / 字符串工具为 `{result:string}`） |
| E4 | View bundle 出处 | `python3 tools/build_ext_apps_bundle.py --check`；`sha256sum ~/Desktop/ext-apps/dist/src/app-with-deps.js` | `OK sha256=feea750b… bytes=255911`；源 sha256 `25b7c7ca…` = 官方 **2.0.3** |
| E5 | 门面 API 名是否对得上 2.0.3 | 逐个 grep 官方 `src/app.ts` / `src/message-transport.ts` | `callServerTool`/`getHostCapabilities`/`getHostContext`/`sendSizeChanged`/`sendLog`/`downloadFile`/`openLink`/`updateModelContext`/`sendMessage`/`onteardown`/`ontoolresult` **全部存在** |
| E6 | 嵌套 `iframe[srcdoc]` 是否被 `frame-src 'none'` 挡（轨 A 的 deck 就靠它渲染） | Chromium 145 + Playwright，四组 CSP 变体（规范默认 / 无 frame-src / `frame-src 'self'` / 无 CSP） | **四组都正常**（`srcdoc` 豁免帧源检查）→ 设计 §1.2 的 srcdoc 架构在轨 A 成立 |
| E7 | `resources/read` 的 `contents._meta` | E1 输出 | 同时携带 `{"ui":{"permissions":{"clipboardWrite":{}}}}`（FastMCP 把资源级 meta 带进 contents） |
| E8 | 门面 `reportSize` 有无调用点 | 全仓库 `grep reportSize` | 只有定义（引导脚本 no-op / 门面实现），`editor.html` **零调用** |

审计用的临时 daemon 已用 `tools/edit.py <dir> --stop` 全部回收，临时目录已删除（未触碰仓库内真实 deck）。

---

## 3. 合规项（已核对通过）

- **资源**：`ui://` 前缀、`mimeType` MUST 值、`text` 承载、HTML5 文档、< 2 MB 上限（`VIEW_SIZE_LIMIT`）。
- **`_meta`**：`ui.resourceUri` 新路径 + 旧 `ui/resourceUri` 双写，与官方 `registerAppTool` 的归一化**同类**；`visibility` 写在 `_meta.ui`（spec §332）；实测分档 5 / 18。
- **权限**：`_meta.ui.permissions.clipboardWrite` 落在**资源级** meta —— 官方 SDK 把资源级 `_meta.ui` 定义为 listing 层 fallback，而 FastMCP 会把它复制进 `contents`，两条读取路径都能拿到（E7）。
- **CSP**：`ui.csp` 省略 = 规范默认最严；View HTML 零外链由 `EXTERNAL_REF_RE`（`tools/bridge_mcp.py:105`）在构建期硬校验 → 无需 `resourceDomains`。
- **文本兜底**：UI 工具同时给 `content` 文本与 `structuredContent`（spec §1558-1559 的 SHOULD/MUST）。
- **View SDK 用法**：官方 2.0.3 bundle；handler 在 `connect` 前注册；`onteardown` 返回 `{}`；zod 走 jitless（`App` 构造器 `z.config({jitless:true})`）→ 规范默认 CSP 不含 `'unsafe-eval'` 也能跑；不用 localStorage/IndexedDB（草稿走 `save_draft`）。
- **偏离但已文档化且功能等价**：注册期早于 `initialize`，故用**列举期双模**替代 spec §1531 的"先读客户端能力再注册"（设计 §10.3）；UI 元数据对所有客户端都注册。

---

## 4. 发现清单

### A 组：影响轨 A 功能/防护（本轮处理）

**A1（中偏高）app-only 工具失败时，View 拿不到 `error.code` / `details`**
- 根因：mcp 1.28 的 `mcp/server/fastmcp/tools/base.py:117` 把**任何**异常（含项目自己抛的 `ToolError`）重新包成 `ToolError(f"Error executing tool {name}: {e}")`；实测该分支**不带 `structuredContent`**（E2）。
- 门面后果：`tools/ext_apps_facade.js:53-58` 的 `errorDetail()` 只对整段文本做 `JSON.parse` → 带前缀必抛 → `err.code` / `err.details` 恒为 `undefined`。设计 §234 声称"`isError` 时从 structured 与文本两处找 `error.{code,message,details}`"——**实际两处都拿不到**，那条设计描述不成立。
- 连带后果：`editor.html:3943`/`4159` 的错误码丢失、toast 带前缀；模型侧看到的也不是纯 JSON（与 `AGENTS.md` / SKILL 对错误契约的措辞不符——但两侧都能看到内嵌 JSON，属可用但不精确）。

**A2（中）`reportSize` 是死代码 → View 从不发 `ui/notifications/size-changed`**
- 事实：`tools/ext_apps_facade.js:133` 已实现 `app.sendSizeChanged`，`tools/bridge_mcp.py:131` 引导期是 no-op，但 `editor.html` **没有任何调用点**（E8）；`hostViewportMaxHeight()`（`editor.html:3699`）仍是返回 `null` 的钩子（交接 §T6 已记）。
- 规范/设计：spec §1217 View SHOULD 发 `size-changed`、§718 宿主 MUST 据此调整 iframe 尺寸；设计 §71 已把宿主 `size-changed`（**只跟随高度、宽度不动、钳制 `maxHeight=1200px`**）列为可用能力，§437 要求工作台按"聊天面板宽度 × ≤1200px 高"设计。
- 后果：工作台拿不到设计假定的高度；宿主模拟器把 `#view` 固定 `height:900px`，正好掩盖了它。

**A3（低—中，本轮不修）View 的传输层没有源过滤**
- `tools/ext_apps_facade.js:157` 写的是 `new PostMessageTransport()`；官方签名是 `(eventTarget = window.parent, eventSource)`，少传第二个参数使 `if (eventSource && …)` 短路 → 任何窗口都能向 View 发 JSON-RPC。官方 View 示例是 `(window.parent, window.parent)`，并注明"接收方应校验来源"。
- 本项目不是纯理论风险：View 自己创建了嵌套 deck iframe（`editor.html:870` / `4535`），该子文档可向 View 注入 `toolresult`/teardown 类消息（危害被 daemon 侧 session 归属校验兜住）。
- **裁决：留待后续讨论**（改动只有一行，但会给"官方示例逐字对齐"审计留一条记录，需与 A2/A4 一起回归）。

**A4（潜伏，中）轨 A 下 deck 的 `@font-face` / CSS `url()` 资产没有通道**
- `editor.html:4042-4072` 的水合只处理 `img[src]`（`/^(assets|fonts)\//`）；`@font-face{src:url("fonts/x.woff2")}` 与 CSS `url(assets/…)` 都不重写。轨 A 的 deck 是 `srcdoc`，相对 URL 按沙箱页基址解析 → 必 404。
- 数据通路本身是通的：`scan_bundle` 把 `fonts/*.{woff2,woff,ttf,otf}` 登记为 `source-font`（`tools/bridge_core.py:619`），`read_artifact` 放行 `assets/`+`fonts/`（`:995`）并回 `mime`（`:1009`）。
- 叠加因素（记录在案，不修）：规范默认 CSP（spec §275-285）**没有 `font-src`**，落到 `default-src 'none'` 会挡掉所有字体（含 `data:`）；参考宿主 `examples/basic-host/serve.ts:84` 是 `font-src 'self' data: blob:`。`_meta.ui.csp` 无法表达 `data:`，故只能"按宿主"。
- 现状：仓库内所有 `url(fonts/…)` 命中都在注释里（无真实 deck 使用），一旦 `subset-fonts.py --inject` 用过就会**静默丢字体**。

### B 组：非规范但（当前）无害 / 已文档化 —— 留待讨论

- **B1** 根级 `_meta.visibility` 双写（`tools/bridge_mcp.py:147`）：官方只对 `ui/resourceUri` 做前后兼容双写，`visibility` 只有 `_meta.ui.visibility` 一处。宿主 1022 已改为标准路径优先（交接 §3），这条现在是多余字段。
- **B2** UI 元数据对所有客户端都注册（spec §1531 是 SHOULD 先读能力）→ 已用列举期双模替代，等价。
- **B3** `resources/list` 对所有客户端都暴露 `ui://` 资源（规范不禁止）。
- **B4** 不订阅 `hostcontextchanged`、不采用宿主主题/字体变量（`applyDocumentTheme` 未用）：编辑器自有固定深色 chrome，属设计选择；代价是宿主切主题/改容器后 View 不重算（与 A2 同源，A2 修一半）。

### C 组：卫生级 —— 留待讨论

- **C1** `tools/bridge_mcp.py:140` 文案写死 `"8s 内未收到 ui/initialize 应答"`，实际 `setTimeout(…, 15000)`（`VIEW_WAIT_SEC_DEFAULT` 确实是 8，但两者不同源）。
- **C2** `serverInfo.version` 实测报 **`1.28.0`（SDK 版本）**：mcp 1.28 的 `FastMCP` 无 `version` 形参，`mcp/server/lowlevel/server.py:183` 默认取 `pkg_version("mcp")`；要报自己的版本需写 `self.mcp._mcp_server.version`。
- **C3** 18 个工具都没设 `title`（官方示例给 app 工具 title）。
- **C4** 引导期 `hostContext`/`hostCapabilities` 返回 Promise（`tools/bridge_mcp.py:128-129` 的 deferred），install 后变同步对象——同一 API 跨安装点形状不同（当前无调用点，但 A2 会去读 `hostContext()`，因此本轮必须容忍这一形状差异）。

---

## 5. 本轮决策（用户裁决 2026-10-22）

1. **只做最小改动，修 A1 / A2 / A4**；A3 与 B/C 组**留待后续讨论**，不扩范围。
2. 全部改动落在**产品代码 + 既有验收脚本的断言**，不改动真实 deck、不改动 daemon 状态机、不新增常驻服务。
3. A2 的高度口径（需用户后续确认是否满意）：工作台是满高布局，"想要的"高度取**宿主 `hostContext.containerDimensions.maxHeight`**（未知则退化为文档自身高度），并去重发送。理由：宿主只跟随高度、钳制 1200px，且设计 §437 已把工作台定义为"× ≤1200px 高"。

---

## 6. 实施计划（A1 / A2 / A4 ；**实施时的两处更正见 §9.2**）

### A1 · 门面剥掉 FastMCP 的错误前缀
- `tools/ext_apps_facade.js` 的 `errorDetail()`：先剥 `/^Error executing tool [^:]*:\s*/`，再取首个平衡的 JSON 对象解析；仍失败才回落整段文本。`parseToolResult()` 的错误分支同步复用。
- 重跑 `tools/build_ext_apps_bundle.py`（产物 `ext_apps_bundle.js` + `ext_apps_bundle.json` 的 sha256 随之更新）。
- 断言（`tests/harness/aa_mcp_apps_check.py` 受信臂）：从 View 内调一个必然失败的工具（如 `read_asset` 传 `path="etc/passwd"`），断言抛出的 `err.code === "INVALID_ARGUMENT"`（模拟器已按真实形状复刻前缀）。

### A2 · 打通 `size-changed` 并接上 `hostViewportMaxHeight`
- `tools/ext_apps_facade.js`：`reportSize(height?, width?)` 接受显式期望高度（缺省仍用文档自身高度，**旧语义不变**）。
- `editor.html`：
  - `hostViewportMaxHeight()` 改为实读 `hostContext().containerDimensions.maxHeight`（`height` 形态回退），读不到返回 null；对引导期 Promise 形状做保护（C4）。
  - 新增 `mcpAppReportSize()`（去重 + 仅在轨 A / 已握手后发送）与 `mcpAppSizeWatch()`（ResizeObserver，250ms 防抖），在 `mcpAppBoot()` 完成附着后启动。
- 断言：受信臂结束后 `window.hostSim.sizes` 非空且高度为有限正数。

### A4 · 轨 A 的 CSS 资产水合（`@font-face` + `url()`）
- `editor.html` 新增 `mcpAppHydrateCss()` / `mcpAppCssUrlEntries()`：遍历 deck 文档 `styleSheets`（递归 `@media` 等分组规则），凡声明值里含 `url(assets/…|fonts/…)` 的，一律经 `read_asset` 换成 `data:…;base64,…` 并写回该声明；按 rel 缓存、按 deck 载入重置。
- **必须配套的反向还原**：`serializeClean()` 里把 CSS 水合的 data URI 还原回原始相对路径（与既有 `[data-pptx-src]` 还原同一纪律），否则保存会把 data: 烤进磁盘 deck（既有断言 `"data:image" not in saved_text` 会挂）。
- fixture/断言：harness 的夹具 deck 加一条 `@font-face{src:url("fonts/test.woff2")}` + 一个 `fonts/test.woff2` 文件，断言（a）View 内该规则的 `src` 已变 `data:`；（b）保存产物里仍是 `fonts/test.woff2` 且无 `data:font`。

### 回归
- `python3 tools/build_ext_apps_bundle.py --check`
- `python3 tests/harness/aa_mcp_apps_check.py`（两臂）
- `python3 tests/harness/r_bridge_check.py --group apps --group ui`
- `python3 tests/harness/run_e2e.py`（既有失败 T34-theme-proving 除外）

---

## 7. 待办（留待后续讨论，本轮不做）

| 编号 | 待办 | 备注 |
|---|---|---|
| A3 | `new PostMessageTransport(window.parent, window.parent)` + 重建 bundle | 一行改动；给"逐字对齐官方示例"留记录 |
| B1 | 去掉根级 `_meta.visibility` 双写（宿主已修） | 需确认不再需要兼容旧宿主 |
| B2/B3 | UI 元数据按客户端能力注册 / 资源是否需要对非 Apps 宿主隐藏 | 与轨 B 五工具红线相关，需评审 |
| B4 | 订阅 `hostcontextchanged`（主题/容器变化后重算） | 与 A2 同源，A2 只修了高度上报 |
| C1 | 引导期超时文案与常量同源 | 一行 |
| C2 | `serverInfo.version` 报自己的版本 | 需用 SDK 私有字段，待确认风险 |
| C3 | 给 app-only 工具补 `title` | 体验项 |
| C4 | 引导期 `hostContext`/`hostCapabilities` 的 Promise/同步形状统一 | A2 已做容忍，未消除 |
| C5 | 模型侧错误文本仍带 SDK 前缀（`Error executing tool <name>: {json}`）；SKILL/AGENTS 对"错误返回 JSON"的措辞可精确化 | A1 只修了 View 侧；模型侧能读到内嵌 JSON，属可用但不精确 |
| — | A4 的剩余部分：规范严格宿主下 `font-src` 缺失导致的字体被挡 | `_meta.ui.csp` 无法表达 `data:`，只能按宿主 |
| — | A4 的剩余部分：**元素内联 style 属性**里的 `url(assets/…\|fonts/…)` 仍未水合（本轮只做样式表规则） | 现状无真实 deck 使用（仓内 68 处内联 `url()` 全是 `url(#…)` SVG 片段引用）；一旦支持，**必须**配套反向还原（内联 style 会进 DOM/序列化，与 `<style>` 文本不同） |
| — | 真实宿主端到端（P4） | 承接 1021 交接 §4 T3 |

---

## 8. 未验证项（NOT_RUN）

- **真实宿主端到端**（Claude Desktop / SproutHarness）：本轮审计只覆盖协议层、源码对照与 Chromium 行为探针（E1-E8）。
- A1/A4 的实际症状强度依赖宿主实现（错误投影方式、CSP 取值）；A2 的实际增益依赖宿主的默认容器高度与 `containerDimensions` 取值。

## 9. 实施结果（2026-10-22 落地）

### 9.1 改动清单

| 文件 | 改动 |
|---|---|
| `tools/ext_apps_facade.js` | 新增 `stripToolPrefix()`；`errorDetail()` 剥前缀 + 宽松 JSON 提取；`parseToolResult()` 的错误消息也去前缀（**A1**）。`reportSize(height?, width?)` 接受显式期望高度，缺省仍是文档自身尺寸（**A2**）。 |
| `tools/ext_apps_bundle.js` / `.json` | 重建（官方 ext-apps 2.0.3 源 + 门面），`view_version` 3.9.1，`bundle_sha256=9228ba76…`，257,252 字节（仍远低于 2 MB 上限）。 |
| `editor.html` | **A2**：`hostViewportMaxHeight()` 实读 `hostContext().containerDimensions`；新增 `mcpAppReportSize()` / `mcpAppSizeWatch()`（ResizeObserver + 250ms 防抖 + 去重），在 `mcpAppBoot()` 附着后启动。**A4**：新增 `mcpAppCssUrlEntries()` / `mcpAppHydrateCss()`，deck 载入时把 `@font-face` 与任意声明里的 `url(assets/…\|fonts/…)` 换成 data: URI。版本头 v3.9.1 + 变更记录。 |
| `tools/build_ext_apps_bundle.py`、`tools/bridge_mcp.py` | `VIEW_VERSION` 3.9.0 → 3.9.1（与 editor.html 头一致）。 |
| `tests/harness/aa_mcp_apps_check.py` | 夹具 deck 加 `@font-face{src:url("fonts/harness.woff2")}` + `fonts/harness.woff2`；受信臂新增三条断言（A2 高度档 / A1 错误码 / A4 水合），保存断言加"CSS 水合不落盘"。 |
| `AGENTS.md` | `editor.html` 版本号 v3.8 → v3.9.1（描述性事实同步，无架构变化）。 |

### 9.2 实施时对审计初判的两处更正（重要，勿沿用旧结论）

1. **A2 的初判不完整**：View **一直在发** `ui/notifications/size-changed` —— 官方 SDK 的 `App({autoResize:true})`（默认值）在 `connect()` 里用 ResizeObserver 自动上报（`src/app.ts` 的 `setUpAutoResize`）。实测证据：把本轮的 `mcpAppSizeWatch()` 注掉后，宿主模拟器仍收到 `{'width':1280,'height':4556}`。
   因此 A2 的真实缺口是：**编辑器侧没有"期望高度"的控制**（`api.reportSize` 是死代码、`hostViewportMaxHeight()` 是 null 钩子），而不是"完全不上报"。本轮补的是这一层：明确请求宿主 `containerDimensions.maxHeight`（避免把内容尺寸 4556 这种数值丢给宿主去钳）。
2. **A4 的反向还原是多余的**：初判假设"CSSOM 改动会回写 `<style>` 文本，所以保存必须反向还原"。Chromium 实测（`styleEl.textContent` / `outerHTML` 在 `rule.style.setProperty` 之后**不变**）证明**不改写**：文本是源码，CSSOM 只读回。因此 `serializeClean()` 里**不需要**任何 CSS 还原步骤，磁盘 deck 天然保持相对路径原文（与 `<img>` 的 `data-pptx-src` 情形不同——属性改动会进 DOM）。原本写下的 `mcpAppRestoreCssUrls()` 已作为死代码删除，并在 `serializeClean` 原位留了说明，避免后人重复踩。

### 9.3 断言真的会响（变异测试）

逐条把修复注掉后重跑 `aa_mcp_apps_check.py`，确认断言能抓到（不是"恰好通过"）：

| 变异 | 结果 |
|---|---|
| `errorDetail()` 还原成修复前的整段 `JSON.parse`（等价 A1 未修） | **FAIL** `带前缀的 ToolError 未还原出 error.code: {'code': None, 'message': 'Error executing tool read_asset: {...}'}` |
| 注掉 `mcpAppSizeWatch();` | **FAIL** `未按宿主 maxHeight 上报高度: [{'width':1280,'height':4556}]`（只剩 SDK autoResize 的重报） |
| 注掉 `mcpAppHydrateCss();` | **FAIL（等超时）** `deck 的 @font-face 被水合成 data: URI` |
| 只把 `stripToolPrefix()` 改成恒等（保留宽松 JSON 提取） | PASS —— 说明两层保险任一即可，属预期（非漏检） |

> 备注：`tests/harness/mcp_apps_host_sim.html` 与 `aa_mcp_apps_check.py` 的宿主代理本就按真实形状复刻了 `Error executing tool <name>: {json}` 前缀与 `isError:true`（`mcp_apps_host_sim.html:139`、`aa_mcp_apps_check.py:132-143`），所以这条链是可证的。

### 9.4 回归结果

| 命令 | 结果 |
|---|---|
| `python3 tools/build_ext_apps_bundle.py --check` | `OK sha256=9228ba76… bytes=257252`（EXIT=0） |
| `python3 tests/harness/aa_mcp_apps_check.py` | `RESULT: ALL PASS`（两臂；含新增三条断言） |
| `python3 tests/harness/r_bridge_check.py --group apps --group ui` | `PASS apps` + `PASS ui` + `PASS r_bridge_check selected automatic groups: apps,ui` |
| `node --check`（editor.html 内联脚本） | 通过（1 个 inline block，0 失败） |
| `python3 tests/harness/run_e2e.py` | **第一次尝试被后台 600s 上限掐断**（`_logs/1022_run_e2e_compliance_fix.log`：45 PASS / 0 FAIL 后进程被杀，**无 EXIT 行 → 不构成一次完整回归**）；无超时重跑 = `_logs/1022_run_e2e_compliance_fix_rerun.log`，末行 **`==== 汇总：62 项，61 PASS，1 FAIL ====`（EXIT=1）**，唯一 FAIL 是**既有失败 T34-theme-proving**（1014/1015 起同一签名，与本次改动零交集）；**T29-bridge（apps/fault/http 组）与 T36-mcp-apps 均 PASS** |
| `python3 -m pytest tests/harness/test_bridge_core.py -q` | `44 passed, 44 subtests passed`（18.5s，基线未被破坏） |

### 9.4.1 环境观察（**非本次改动**）：`tools/bridge_mcp.py` 在验证期间被外部修改

本轮重跑 e2e 期间（15:36:30），`tools/bridge_mcp.py` 出现**不属于本次改动**的修改：`import uuid` → `import hashlib`，`self.consumer_id = str(uuid.uuid4())` → `"mcp-" + hashlib.sha256(workdir)[:16]`（附 3 行英文注释，理由写的是 "langchain_mcp_adapters creates a new stdio subprocess per tool call"）。文件从 513 行变 516 行，`VIEW_BOOTSTRAP`/`APP_ONLY_META`/`class BridgeMCP` 行号未移动（说明改动局限在该处）。

- **不是本会话改的**（本会话对 `bridge_mcp.py` 只做过 `VIEW_VERSION` 3.9.0→3.9.1 的一行改动）；疑似并行会话/IDE 侧 AI 所为，**未回退**（不该由本轮代用户裁决）。
- 本轮做的一致性核查：`ast.parse` 通过；`import hashlib` 已补齐；全文件**无残留 `uuid.` 引用**（不会 NameError）；该改动**之后**启动的 T29-bridge 与 T36-mcp-apps 子进程**均 PASS**（它们会 import 本模块）。
- 结论：上述回归结论覆盖的是**改动后的工作树**（15:36 之后跑的项），这一点已在证据里如实标注。

### 9.5 本轮未做（承接 §7）

A3（传输层源过滤）与 B/C 组全部保持原样；A4 的"规范严格宿主下 `font-src` 缺失"一节仍无解（`_meta.ui.csp` 表达不了 `data:`）。真实宿主端到端仍是 **NOT_RUN**。
