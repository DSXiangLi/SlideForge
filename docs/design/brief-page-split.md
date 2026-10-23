# 脑暴页剥离：从「编辑器浮层」到「可直达的首屏」

> 状态：**待评审**（本文只定方案与契约，不含代码改动；评审通过后按 §12 分期实施）
> 前序设计：`brief-dynamic-brainstorming.md`（briefing v2，已实施）、`mcp-apps-upgrade.md`（MCP Apps 双轨，§10 为落地事实）
> 触发：用户反馈"调用工具后脑暴的页面无法直接打开，还需要用户去点击按钮"——要求把脑暴从编辑器页里整体剥离
> 影响面：`editor.html`、`tools/bridge_core.py`、`tools/bridge_mcp.py`、`tools/ext_apps_facade.js`、`tools/edit.py`（bootstrap 一致性）、`skills/html-pptx/SKILL.md`（措辞；**工具面不变**）、`tests/harness/`
> **本文已按四路独立评审（事实核对 / 外溢风险 / 验收充分性 / 替代方案）修订**，改动清单见 §15——其中 **7 条**是会直接导致实现翻车的硬错误，勿按旧稿实施。

## 1. 问题与实测根因

### 1.1 现象

`open_editor(view="brief")` 调用之后，用户看到的是**编辑器工作台**，脑暴只是它上面的一层浮层；要进脑暴还得点顶栏「需求脑暴」。也就是说：脑暴没有"自己的页面"。

### 1.2 实测（本文写作时新跑；方法可复现）

把 `tests/harness/aa_mcp_apps_check.py` 的驱动抽成一次性探针（真 `build_view_html()` + 真 daemon + 宿主模拟器 `mcp_apps_host_sim.html?sandbox=trusted`），三个场景：

| 场景 | `open_editor` 的 `view` | 会话 | 脑暴是否自动打开 |
|---|---|---|---|
| S1 | `brief` | 无 deck（从零创作） | ✅ 开了——但**不是因为有 `view`**，而是因为"没有 deck" |
| S2 | `edit` | 无 deck | ✅ 同样开了（`view` 被完全忽略，反证 S1 的机制） |
| S3 | `brief` | **已有 deck** | ❌ 不打开，**必须点顶栏按钮**（复现用户报告） |

三条的浏览器 URL 全是 `editor.html#brt=…&session=…`（**不含 `view`**）；`open_editor` 的返回体键里也**没有 `view`**（实测键：`ok/protocol_version/session_id/deck_path/target_path/resource_path/revision/phase/url/page_online/view_attached/track/agent_state/consumer_state/git_initialized/brief_options/capabilities`，见 `tools/bridge_core.py:899`）。

### 1.3 根因（三条，互相独立）

1. **`view` 是装饰性参数**。`BridgeCore.open_editor()` 只做 `view not in {"edit","brief","annotate","export"} → 400` 的校验，随后丢弃（`tools/bridge_core.py:863-865`）；`_open_result()`（:898-906）不回传；轨 B 的 URL 硬编码 `editor.html#brt=…&session=…`（:883；`bootstrap_redeem()` 同形 :1912）。轨 A 的门面只订阅 `onteardown`/`ontoolresult`（`tools/ext_apps_facade.js:17,23`），**没订阅 `ui/notifications/tool-input`**，`arguments.view` 收不到（注：`editor.html:4002` 已有 `mcpApp.view = payload.view || mcpApp.view` 的消费点，只是从没拿到过值）。于是页面只能按 `deck_path` 猜——S2/S3 的错位由此而来。
2. **脑暴在物理上是编辑器的浮层**：`#briefOverlay` 的 CSS（`editor.html:559-635`）、markup（:1053-1080）、JS（:5850-6753）合计约 1010 行（11.8%），与工作台共用同一份运行时。即使它打开，页面上仍是顶栏、目录侧栏、画布、状态栏——**"打开的页面"是编辑器，不是脑暴页**；且它本身是右侧 **520px 抽屉**（`:559-565`：`position:fixed; top/right/bottom:12px; width:min(520px,94vw)`），不是整屏。
3. **轨 A 的 `brief_options` 根本没生效**：`briefActiveOptions()`（`editor.html:5966`）在非 Bridge 态只读 `embedBriefOptions`，而轨 A 的 `mcpAppApplyStatus()`（:3984-3992）**不写 `brief_options`**；轨 A 下 `bridge.enabled` 恒为 false（唯一赋值点 `:7913` 在 `bridgeParseLaunch` 内，而它因 `state.embedded` 于 `:7901` 早退……注意轨 A 的 `state.embedded` 由 `window.parent !== window` 判定，`:3671`）。AGENTS.md / SKILL 承诺的"可携 `brief_options` 注入动态脑暴"在宿主内失效（轨 B 正常）。

## 2. 关键约束（决定方案形状；均为源码/规范核对结果）

| # | 约束 | 证据 |
|---|---|---|
| C1 | 宿主按**工具的静态** `_meta.ui.resourceUri` 取页面；**工具结果的 `_meta` 不做资源覆盖** | SproutHarness `feature+mcp-apps` 分支 `src/sprout_harness/agent/graph.py:833-841`（用 `entry.ui_meta["resource_uri"]`，来自 `tools/list`）；官方规范 `specification/2026-01-26/apps.mdx:319-347`「Resource Discovery」只把 `resourceUri` 定义在 Tool 上 |
| C2 | 每次 UI 工具调用都新建一个 app instance（新 iframe） | 同分支 `mcp/sandbox.py:41` 定义 `store_app_html()`、其内 `:59` 每次 `uuid4()` |
| C3 | 轨 A 的 View 资源必须**单文件自包含**：无外链、≤2MB（当前 0.69MB） | `tools/bridge_mcp.py:105-107` `EXTERNAL_REF_RE`（`<script src>`/`<link href=http>`/`<iframe src>` 命中即报错）；`VIEW_SIZE_LIMIT` 2MB |
| C4 | 轨 B 的静态路由是白名单，只有 `/` 与 `/editor.html` | `tools/bridge_core.py:2197` |
| C5 | 「轨 B 恰好五个模型可见工具」是 AGENTS.md 红线，且已被测试固化 | `tests/harness/r_bridge_check.py:157` 是**精确列表**断言——任何第 6 个工具都会破它 |
| C6 | SKILL 里的调用字面量也被断言 | `tests/harness/r_bridge_check.py:566` 断言 SKILL 文本含 `open_editor(deck_path=null, output_path="index.html", view="brief", open_browser="auto")` |
| C7 | 真宿主在 `initialized` 时**同时**发 `tool-input` 与 `tool-result`；真正的丢消息窗口是"通知早于回调注册" | `src/sprout_harness/agent/webui.html:5508`（`sendToolInput`）紧接 `:5515`（`sendToolResult`）；而门面 `connect` 在 `tools/ext_apps_facade.js:178` 立即执行，`editor.html:4363` 才注册回调 → 早到的通知会丢 |
| C8 | `/bootstrap` 的 query 被精确校验，`view` 只能走 fragment | `tools/bridge_core.py:2185`（`set(q)!={"ticket"}`）、LANDING 页只透传 `#boot`（`:1920`）、`bootstrap_tokens` 无 view 列（`:1904-1909`） |
| C9 | 会话已有在线页面时，`open_editor` 既不开新窗也无投递通道 | `tools/bridge_core.py:886-890`（`page_online` 时不 `webbrowser.open`）、`_schedule_view_window.fire()` 亦早退 → 仅靠 URL fragment 无法触达已在线页面 |

**由 C1+C2 推出的核心结论**：轨 A 里"让宿主渲染**另一个页面**"**只能**靠"另一个工具"（C1）；而"另一个工具"要付 C5 的代价，并牵动 SKILL 契约与 `r_bridge_check` 的计数断言。因此**本次不新增工具**，走"同一资源内**首屏分流**"。

## 3. 设计目标与不变量

**目标**

1. agent 调用 `open_editor(view="brief")` 后，两条轨上都**直接**看到脑暴页面，零点击。
2. `view` 这个已经写在工具签名里的意图被真正尊重；并覆盖"已有 deck 时进脑暴"（S3）与"页面已在线时也要切换"（C9）。
3. `view=brief` 时**工作台 chrome 不可见**，脑暴占据视口——而不是浮在工作台上。
4. 顺带修复轨 A 的 `brief_options` 失效。

**不变量（红线不动）**

- 五工具不变，`open_editor` 仍是唯一带 UI / 唯一面向模型的创作入口。
- 页面内无 AI；纯静态、无框架、无外部依赖。
- `brief.submitted` 即冻结、Step 1/2 不二问的纪律不变；简报输出格式（文本 + `design-brief` JSON）不变。
- 裸静态态（file:// 直开）可用；嵌入态 postMessage 协议只增不改。
- 首轮 `await_intent(86400)` 一次等待的纪律不变。
- `BridgeCore.open_editor()` 对非法 `view` 的 400 **保持不变**（不放宽既有护栏）。

## 4. 方案选型

| 候选 | 做法 | 结论 |
|---|---|---|
| **A 双工具·双资源** | 新增 model 可见工具 `open_brief`，`_meta.ui.resourceUri` 指向独立的 `ui://pptx-html-bridge/brief.html` | **未选**。代价：破 C5 红线（`r_bridge_check.py:157` 必破）+ 要改 AGENTS.md + SKILL §3.1 + `:690-697` 的工具计数/visibility 断言；且按 C2，脑暴与编辑会变成**两个 iframe**，丢掉"同一实例内无缝切换"。收益（脑暴页不再驮整份编辑器）可由 §11 源码拆分为将来"一次资源指向"预留 |
| **B 单工具·首屏分流** | `open_editor` 不变；`view` 真正下发；`view=brief` 时同一资源只渲染脑暴视图 | **选定**（用户已确认） |
| C 只拆轨 B | 轨 B 真开 `brief.html`，轨 A 保持浮层 | 未选：宿主内（主场景）仍是浮层，没解决报告的问题 |
| D 有状态的资源 | `resources/read` 按"最近一次 `open_editor` 的 view"返回不同 HTML | **明确否决**：违反"资源即静态资产"契约，`resources/read` 失去纯函数性；URI 里没有会话维度，多会话并发下必然把 A 的视图喂给 B。（注：调查中**未发现**宿主预取/缓存资源的证据，否决理由不依赖这一条） |
| E View 内嵌 `brief.html` | 单资源里放 `<iframe src="brief.html">` | 否决：**首要理由是硬约束**——`EXTERNAL_REF_RE`（`tools/bridge_mcp.py:105-107`，:170-171 抛错）直接拒绝含 `<iframe src=` 的 View；其次宿主默认 CSP `frame-src 'none'`（可被资源 `_meta.ui.csp.frameDomains` 覆盖，故不作为首要理由） |

## 5. 总体架构

```
                       agent: open_editor(view="brief", brief_options=…) 
                                        │
        ┌───────────────────────────────┴────────────────────────────────┐
        │ daemon / MCP：view 原样透出（不落库；已在线页面经 notice 一次性投递）│
        └───────────────────────────────┬────────────────────────────────┘
     ┌──────────────────────────────────┴───────────────────────────────────┐
     │ 轨 B（浏览器）                        │ 轨 A（MCP Apps 宿主）           │
     │ 新窗: /editor.html#brt=…&session=…&view=brief │ tool-result.view（主通道）│
     │ bootstrap 302 Location 带 view        │ tool-input.arguments.view（并行）│
     │ 已在线页面: SSE notice 一次性提示      │                                 │
     ▼                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ 同一个 View 资源（单文件自包含，C3）                                     │
   │   launch=brief → 隐藏 header/main/footer，脑暴改写为整屏视图             │
   │   launch=edit/annotate/export → 工作台 + 对应 mode/页签                  │
   │   无 deck 恒落 brief（吸收 MCP 默认 view="edit"，防行为倒退）             │
   └────────────────────────────────────────────────────────────────────────┘
```

## 6. 契约改动一：`view` 真正下发

| 通道 | 位置 | 形态 | 说明 |
|---|---|---|---|
| 轨 A 主通道 | `_open_result()` 增 `view` 字段（`:898-906`）→ MCP 层原样透出 | 工具结果里的 `view` | 宿主必发（C7 实测源码）；`editor.html:4002` 已预埋消费点 |
| 轨 A 并行通道 | 门面增 `api.onToolInput`，订阅 `ui/notifications/tool-input`（facade 与 `VIEW_BOOTSTRAP` 都要） | `arguments.view` | **不是"优先级更高"，而是并行冗余**；必须在 `VIEW_BOOTSTRAP` 里**缓冲最后一次载荷并重放**，否则会被 C7 的"注册晚于 connect"丢掉 |
| 轨 B 新窗 | `open_editor()` 的 `url`（`:883`） | `/editor.html#brt=…&session=…&view=brief` | 追加在 fragment 尾部；`bridgeParseLaunch`（`:7900`）必须在 `history.replaceState` 清 hash **之前**取值 |
| 轨 B 手动启动 | `bootstrap_redeem()`（`:1912`） | 同上 | 受 C8 限制：`view` 只能走 fragment；需同时改 LANDING 页（`:1920`）、票据（`:1904-1909`，或改为按 mode 推断而不落库）；推断规则：`mode=new` → `brief`、`mode=deck` → `edit` |
| 已在线页面 | 复用既有 SSE `notice` 事件，加一个一次性的 `view` 字段 | 不落库、不进 `get_status` | 解 C9。协议只增字段（`editor.html` 的 `bridgeApplyEvent` 已处理 `notice`） |

**取值优先级**：显式 `view`（工具结果 > `tool-input`）> URL fragment `view` > 无 → 交给 §7.1 的缺省规则。三处不冲突（每条轨只可能命中其中一条）。

**容错口径（按评审修正）**：

- MCP 工具签名的 `view: Literal["edit","brief","annotate","export"] = "edit"`（`tools/bridge_mcp.py:300`）在 SDK 层就会拒非法值，**到不了 daemon**；daemon 的 400（`bridge_core.py:864-865`）**保持不变**，不放宽。
- "忽略未知值并回落缺省"只适用于 **URL fragment / `tool-input` 里出现的未知值**（这两条不经过 schema）。

**唯一新增的"不做"决定：`view` 不落库、不进会话状态。** 理由：它是一次性启动提示，不是会话真值。若落库，驻留页每 2s 轮询 `get_status()` 会被后到的 `open_editor(view=…)` 翻转当前视图。URL fragment、工具结果与 `notice` 事件都天然是"一次性/每页面"作用域，正好匹配。（`notice` 是会话级广播——同会话多页面同时在线的极端情形下所有页面都会切换，属可接受异常态。）

**命名**：编辑器内部已有 `view` 表示三态页签（`edit`/`compare`/`export`，声明于 `:7105`）。启动提示在代码里命名 **`launchView`**，避免与内部值域混用（映射见 §7.3）。

## 7. 契约改动二：首屏分流

### 7.1 判定

```
launch = (view === "brief" || 会话无 deck) ? "brief" : (view || "edit")
```

- **无 deck 恒 brief**：这一条吸收了"MCP 默认 `view="edit"` 且无条件透传"（`bridge_mcp.py:300,310`）的事实——否则新建 deck 的首次打开会退化成**空工作台**（行为倒退）。S1 不变。
- **有 deck + `view="brief"`** → brief（修复 S3）。
- **有 deck + edit/annotate/export** → 工作台对应 mode/页签。
- **无 deck + `view="edit"`**（S2）→ **仍是 brief**（与今天一致）。也就是说：无 deck 时 `view` 只能表达"是否直达脑暴"，区分不了其他页签——这是可接受的，因为此时没有可编辑的内容。

**时序（避免首屏白屏）**：`view === "brief"` 时页面 boot 即可定，不依赖会话状态；缺省路径要知道 `deck_path`，此时**先渲染脑暴壳**（无 deck 时唯一有意义的空态），`get_status` 回来若发现 deck 再切工作台——今天就是这个顺序（`editor.html:8173` 与 `mcpAppBoot` 内 `:4046` 的分支），不新增等待。

**轨的界限（防误隐藏）**：缺省规则只在 **bridge / mcp-app** 两轨生效；**嵌入态与裸静态态没有 session，`launchView` 恒为 `edit`**，绝不能据此隐藏工作台（否则嵌入态 `pptx-html:load` 到达前首屏就是空白，且没有解除路径）。

### 7.2 渲染：脑暴是"视图"，不是"浮层"

**隐藏/覆盖的集合**（按评审修正——顶栏不在 `<main>` 内）：

| 元素 | 位置 | 处置（**已按实施结果更新**） |
|---|---|---|
| `<header>` | `editor.html:793-824`（打开/保存/编辑·批注·翻转页签/字体条/图片/历史） | **隐藏**（是 `<main>` 的兄弟节点，原稿漏了） |
| `<main>` | `:845-1006`（目录侧栏 + 画布 `#workarea`） | **只被覆盖，不做 `display:none`**（见下） |
| `<footer>` | `:1008-1014`（状态栏） | 隐藏 |
| `#bridgeBar` / `#bridgeTasks` / `#warnBanner` | `:826` / `:833` / `:835` | 隐藏（否则脑暴顶上仍有一条桥栏） |

**为什么 `<main>` 用"覆盖"而不是"隐藏"**（实施期修正，实测驱动）：deck 是 `<main>` 内的嵌套 iframe。一旦祖先 `display:none`，该 iframe 的视口变成 0×0，内部排版/动效会塌；而恢复可见只有 `applyView()` 的既有补偿（重发一次 scroll），不足以可靠复原。让 `#briefOverlay` 变成 `inset:0` 的**不透明整屏层**去遮挡，则 iframe 视口全程正常——`<main>` 只被"看不见"，没有被"拆除"。`<header>`/`<footer>`/桥栏不是 iframe 的祖先，隐藏它们没有这个副作用。

**几何改写**：`#briefOverlay` 原为右侧 520px 抽屉（`:559-565`），实施为 `body[data-launch="brief"] #briefOverlay{inset:0;width:auto;height:auto;border:0;border-radius:0;box-shadow:none;background:var(--paper)}`（保留内部滚动）。

**关闭必须解除标记**：`closeBrief()` 原只 `classList.remove('show')`，Esc 与 ✕ 共用它。只在 `openBrief()` 侧加标记会让关闭后工作台不可见 → **白屏**。实施：`closeBrief()` 同步清除 `data-launch`、重置高度上报并调 `applyView()` 补偿。

**deck 到达自动退出脑暴视图（新增行为）**：实施为 `launchOnDeckReady()`，挂在 `bridgeLoadDeck()` / `mcpAppLoadDeck()` 的成功路径。比原设计**多一条守卫**：只在用户**已经提交过简报**（`bridge.briefSubmission.intentId` 或 `bridge.intents` 里有 `brief.submitted`）时才自动切走——否则会在用户正填表时把表单抢走。

**两个已知的隐藏态副作用（已处理）**：

- 视图切换后的 `offsetTop` 塌陷 / `curSlideIdx` 漂移 → 由 `closeBrief()` 里的 `applyView()` 复用既有补偿；
- 高度上报按值去重（`mcpAppReportSize`）在内容高度骤变后不自愈 → `launchResetSize()` 重置 `mcpApp.reportedHeight` 并补发一次。**该条仍待 T36 实测确认**（§10 #9）。

**保留"不显示而非不初始化"的表述**：工作台的 JS（缩略图 Shadow DOM、SSE 轮询、图片懒加载）仍在后台运行——回到工作台必须无缝；无 deck 时它们本就空转。实现与验收口径都按**可见性断言**，不按"不渲染"。

**有 deck + brief 时 deck 仍要照常读取**：既有的 T36 断言链里有 `wait_for("read_deck" in chain())`（`aa_mcp_apps_check.py:250-252`）。首屏分流**不得短路 deck 加载**，否则既有断言会超时——这条本身就是一条验收项（§10 #10）。

### 7.3 与编辑器内部状态映射（一入两出）

内部有**两个**维度：`view`（`edit|compare|export`，`:7105`）与 `mode`（`annotate` 等，`:7394-7396`）。工具 `view` 到它们的映射：

| 工具 `view` | 内部动作 | 落点 |
|---|---|---|
| `brief` | 标记 `data-launch="brief"` | 脑暴视图 |
| `edit` | `setView('edit')` | 编辑页签 |
| `annotate` | `setView('edit')` + `setMode('annotate')` | 批注伪视图 |
| `export` | `setView('export')` | 导出/对比页签 |

注：**不要**把 `annotate` 当成内部 `view` 的取值——它不存在于 `view` 域。应用时机也要对：`openHtml` 内部会 `view='edit'; applyView()`（`:4598-4600`），launch 的应用点必须在它**之后**，否则 `annotate`/`export` 会被覆盖。

### 7.4 入口关系

| 入口 | 行为 |
|---|---|
| agent `open_editor(view="brief")` | 直接落脑暴视图（工作台隐藏） |
| 编辑态顶栏「需求脑暴」按钮 | 走**同一套视图切换**进脑暴（工作台整块隐藏）；Esc / 关闭 → 回工作台 |
| 嵌入态 postMessage / 裸静态态 | 入口与出站协议**不变**；缺省恒 `edit`，**不隐藏工作台** |

## 8. 轨 B 的独立页面

- **本轮（P1）**：URL 带 `view`，页面内分流——浏览器里打开的仍是同一个单文件页面，但直接落在脑暴视图。**不新增页面文件、不改 C4 白名单。**
- **下一轮（P2，已决议本轮不做）**：真正拆成 `/brief.html`，`open_editor(view="brief")` 的 URL 直指它（需加 C4 白名单 + §11 的组装产物）。属于结构收益，不是症状修复。

## 9. 顺带修复：轨 A 的 `brief_options` 失效

**证据**：`briefActiveOptions()`（`editor.html:5966`）为 `bridge.enabled ? bridge.briefOptions : embedBriefOptions`；轨 A 下 `bridge.enabled` 恒 false（唯一赋值点 `:7913` 需 `bridgeParseLaunch` 走到，而它在 `state.embedded` 时 `:7901` 早退——轨 A 的 `state.embedded` 由 `window.parent !== window` 判定，`:3671`），而 `mcpAppApplyStatus()`（`:3984-3992`）拿到 `st.brief_options` 却不存。**修法**：轨 A 把 `st.brief_options` 落到 `mcpApp.briefOptions`，`briefActiveOptions()` 三态取数（bridge / mcp-app / embedded）。验收见 §10 #6。

## 10. 验收方案

**T36（`tests/harness/aa_mcp_apps_check.py`，已注册为 `run_e2e.py` 的 T36-mcp-apps 子进程）扩。每条都标注**执行臂**（`trusted` / `host`）——仓库默认配置是未开 `allow_same_origin` 的**受限臂**，症状类断言必须两臂都跑，否则等于在非发货配置上验证。

| # | 场景 | 断言 | 臂 |
|---|---|---|---|
| 1 | `view="brief"` + 无 deck | 脑暴视图成立；`body[data-launch="brief"]` 已置位；`header`/`footer`/`#bridgeBar` **不可见**（高度 0 或 `display:none`）；`#briefOverlay` 几何 ≈ 视口；**`getComputedStyle(#briefOverlay).backgroundColor 不透明**（透明层照样能通过命中测试——v3.9.3 的透明 bug 就是栽在这条上）；**`document.elementFromPoint(视口中心)` 落在 overlay 内**（`<main>` 按实施为"被覆盖"，用命中测试证明工作台确实够不着） | 两臂 |
| 2 | `view="brief"` + **有 deck** | 脑暴视图成立（S3 回归） | 两臂 |
| 3 | `view="edit"` + 有 deck | 工作台可见、脑暴不可见（不误入） | trusted |
| 4 | `view="annotate"` / `view="export"` + 有 deck | 落对应 **mode/页签**（按 §7.3 的"一入两出"分别断言，而不是只数一个变量） | trusted |
| 5 | 不传 `view`（缺省路径） | 无 deck → brief；有 deck → 工作台。**这是 §7.1 缺省规则唯一的直接覆盖**（S1/S2 都带显式 view，覆盖不了它） | 两臂 |
| 6 | 注入 `brief_options` | 轨 A 渲染动态问题组（修复 §9）；嵌入态的对应覆盖是 **T35e**（`tests/harness/y_dynamic_brief_check.py`），不是"REQ-T36b" | trusted |
| 7 | 关闭脑暴（Esc 与 ✕ 各一次） | `data-launch` 被清除、`<main>`/`<header>` 恢复可见、已加载的 deck 仍在 | trusted |
| 8 | `tool-input.view` 与 `tool-result.view` 冲突 | 门面缓冲重放生效、两者不打架（C7） | trusted |
| 9 | 隐藏 → 恢复后的高度上报 | `sim.sizes` 末值 ≥ 1000（模拟器已记录，`mcp_apps_host_sim.html:117`）——**验证 §7.2 的 reportedHeight 重置** | trusted |
| 10 | 有 deck + `brief` 时 | `read_deck` 仍被调用（防与 `aa_mcp_apps_check.py:250-252` 的既有 `wait_for("read_deck")` 对撞） | trusted |
| 11 | 嵌入态 / 裸静态态 | `launchView` 恒 `edit`，工作台**不**被隐藏（防 §7.1 的轨界限写错） | 需新臂或既有 o_ 用例 |
| 12 | 隐藏态运行期间 | 全程无 `pageerror`（复用 `r_bridge_check.py:352` 的 pageerror 收集手法；对应 AGENTS.md 的"框架 JS null 检查"红线） | 两臂 |
| 13 | 2s 轮询 | `get_status` 轮询**不把视图翻回**（验证"`view` 不落库"这一关键决定） | trusted |
| 14 | URL fragment 里的未知 `view` 值 | 不报错、按 §7.1 回落缺省（注意：MCP 参数的非法值由 SDK 的 `Literal` 直接拒，不经 daemon——不要拿它当这条的测试） | 轨 B 用例 |

- **`r_bridge_check.py`**：`open_editor` 返回体含 `view` 且与入参一致（**已核对**：`:188`/`:200` 是逐字段取值断言，全仓无对返回体的精确键集断言 → 新增字段不破）；轨 B URL 含 `view`（注意既有 `:231` 的 `location.startswith("/editor.html#brt=")` 与 `:357` 的 `launch["hash"] == ""` 两条断言对本次改法仍成立）；**工具面仍恰好五个**（`:157` 不动——本次不新增工具的直接验证点）。
- 三条探针场景（S1/S2/S3）转正式用例：S1/S3 是症状回归；**S2 的期望要按 §7.1 改写**（无 deck + `edit` 仍落 brief），不能再表述为"防回归缺省"。
- **门禁**：T36 全 PASS + `run_e2e.py` 除既有失败 **T34**（theme-proving）外无新增 FAIL——既有基线 **62 项 / 61 PASS / 1 FAIL**（证据 `docs/progress/_logs/1022_run_e2e_after_host_reread.log` 末行）。
- **NOT_RUN（人工项）**：真宿主 SproutHarness 内目检"调用 `open_editor(view="brief")` 是否零点击直达脑暴"——本机无法实测，P4 仍阻塞在宿主侧，**不得写成 PASS**。

## 11. 源码拆分与组装（P2，本轮不做；保留设计）

**现状代价**：脑暴约 1010 行挤在 `editor.html` 内，与工作台共享 49 个外部符号（未逐符号复核），其中真实共享的是 `hostBridge` / Bridge 客户端（`bridge`/`bridgeFetch`/`bridgeSend`/`bridgeRetryIntent`/…）/ 主题卡渲染（`buildThemeCard`/`refreshThemeSelection`/`PANEL_DATA`）/ `toast`·`copyText`·`localIso` / 设计 tokens。

**目标布局**（源单点、产物自包含）：

```
views/shared/    宿主适配层、Bridge 客户端、UI 小件、tokens（两页共用）
views/brief/     脑暴页的 CSS / markup / 渲染与提交核心（单源）
editor.html      工作台源页面（保留原位，含一份由标记区间注入的脑暴首屏）
tools/build_views.py  视图源文件 → editor.html 标记区间 + brief.html 产物的组装：
                      规格对齐 tools/build_ext_apps_bundle.py（产物提交 + sha256 manifest
                      + --check 门禁）与 sync-themes.mjs（幂等标记区间）
```

**对既有约束的影响**：轨 A 组装产物仍是**单文件自包含**（C3 不受影响）；裸静态态 `editor.html` 仍是可直接双击打开的完整单文件；"无框架、无外部依赖"不变；"无构建"变为"构建只用于开发期生成产物"（已有 `ext_apps_bundle.js`、`sync-themes.mjs` 两个先例）。

**与方案 A 的关系**：拆完之后若要求"脑暴必须是独立资源"，只需加一个工具 + 一次资源指向，源码零改动。

## 12. 分期实施（P1）

1. `tools/bridge_core.py`：`url`（`:883`）带 `&view=`；`bootstrap_redeem()`（`:1912`）+ LANDING（`:1920`）+ 票据按 C8 处理；`_open_result()` 增 `view`；`notice` 事件增一次性 `view`（解 C9）。
2. `tools/ext_apps_facade.js` + `tools/bridge_mcp.py:VIEW_BOOTSTRAP`：`onToolInput`（含缓冲重放）。
3. `editor.html`：`bridgeParseLaunch` 取值（清 hash 之前）→ `launchView` 判定（§7.1，含轨界限）→ `data-launch` 视图切换（§7.2 隐藏集 + 几何改写）→ `closeBrief` 解除标记 → deck 到达自动退出 → 隐藏态副作用处理（offsetTop/curSlideIdx、`reportedHeight` 重置）→ `mcpAppApplyStatus`/`briefActiveOptions` 三态取数。
4. `skills/html-pptx/SKILL.md`：补一句"有 deck 时 `view=brief` 的语义"；**不动 `r_bridge_check.py:566` 断言的那句调用字面量**。
5. `tests/harness/`：T36 十四条（§10）+ `r_bridge_check` 两条；S1/S3 症状回归用例。

**P2（下一轮，用户已决议本轮不做）**：§8 轨 B 拆 `brief.html` + §11 源码拆分与组装。
**P3（可选演进）**：若要求脑暴为独立资源，切方案 A。

## 13. 风险与限制

- **有 deck 时 `view=brief` 是语义扩张**：SKILL 目前只在"从零创作"用它；改动后含义为改版脑暴（briefing v2 的维度组仍适用）。SKILL §3.1 只**补一句**说明——注意 `r_bridge_check.py:566` 断言了那句调用字面量，本次不改它。
- **首屏分流引入第二个渲染分支**：harness 必须两臂 + 两态都测（本项目有过"只在 reduced-motion 下截图形似正常"的教训）。
- **C7 的丢消息窗口**：接 `tool-input` 必须带缓冲重放，否则早到的通知会被丢；但主通道是 `tool-result`，即使不接 `tool-input` 功能也成立（并行冗余而非依赖）。
- **C9 已在线页面**：靠 `notice` 一次性投递解决；`notice` 是会话级广播，多页面同时在线的极端情形会一起切换（可接受）。
- **"不显示"与"不初始化"的差别**：脑暴视图下工作台仍在后台跑（无 deck 时空转），可接受；换回工作台因此无缝。
- **两个隐藏态副作用**（offsetTop/curSlideIdx、高度上报去重）已列入 §7.2/§12，但**高度上报那条是推测**，必须以 T36 #9 实测为准。
- **P2 的构建步骤**引入"产物与源不一致"风险 → `--check` 门禁（与 `ext_apps_bundle` 同规格）。
- 本设计**不改变** `brief.submitted` 的冻结语义与简报格式，下游 Step 1/2 零感知。

## 14. 已确认决议（2026-10-22，用户）

1. **脑暴页形态统一为视图切换**：编辑态点「需求脑暴」也隐藏工作台，不留"浮层 / 视图"两种形态（§7.2/§7.4）。
2. **有 deck 时允许 `open_editor(view="brief")`** 直接进脑暴（修复实测 S3 的必要条件，§7.1）。
3. **本轮只做 P1**；源码级拆分（P2）留下一轮（§8/§12）。

## 15. 评审修订记录（2026-10-22，四路独立评审后折入）

**硬错误（原稿按此实施会翻车）**

1. **隐藏集漏 `<header>`**：顶栏（`:793-824`）是 `<main>`（`:845`）的兄弟，原稿只隐 `main`+`footer`，且把"工具条"错置进 `main` → 脑暴顶上仍是一条工作台工具栏，而 §10 #1 只断言 main/footer，会给出**假 PASS**。已改 §7.2 隐藏集与断言。
2. **`#briefOverlay` 是 520px 右侧抽屉**（`:559-565`），不是整屏 → "可见性切换"不足以达成目标 3；已补几何改写要求与"宽度 ≥ 视口 − ε"断言。
3. **关闭不解除标记会白屏**：`closeBrief()`（`:6485`）只摘 `.show` → 已补"同步清除 `data-launch`"与 #7 断言。
4. **缺省分流公式自相矛盾**：原式在"无 deck + `view="edit"`"（S2）下落工作台，与"与今天一致"冲突；且 MCP 默认 `view="edit"` 且无条件透传（`bridge_mcp.py:300,310`）→ 新建 deck 首开退化为空工作台。已改为"无 deck 恒 brief"并补缺省路径断言（#5）。
5. **"轮询发现 deck → 切工作台（既有行为）"不成立**：`closeBrief` 无任何自动调用点 → 已列为**新增行为**并要求实现。
6. **bootstrap 无处携带 view**：query 被精确校验（`:2185`）、LANDING 只透传 `#boot`（`:1920`）、票据无该列 → 已补 C8 与三处改动。
7. **已在线页面收不到 `view`**（`page_online` 时不新开窗口，`:886-890`）→ 已补 C9 与 `notice` 投递通道。

**事实/口径修正**

8. C7 新增：真宿主**确实**发 `tool-input`（`webui.html:5508`），真正的风险是"注册晚于 connect"；原稿"宿主是否下发未验证"的措辞与"兜底优先级"表述已改（`tool-input` 是并行冗余，且必须缓冲重放）。
9. "非法 view 不 400"改为只适用 URL/`tool-input` 的未知值——MCP 参数的非法值被 SDK 的 `Literal` 直接拒；daemon 的 400 保持不变。
10. §7.3 映射表改为"一入两出"（内部 `view` 域只有 edit/compare/export，`annotate` 是 `mode`），并补"应用点必须在 `openHtml` 之后"。
11. 引用修正：`sandbox.py:41` 是 `def`、`uuid4()` 在 `:59`；返回体键集补 `protocol_version`（`:899`）；r_bridge_check 的断言在 `:188`/`:200`（`:185`/`:199` 是调用行）；嵌入态 `brief_options` 覆盖是 **T35e**（原稿写"REQ-T36b"，全仓不存在）；markup 为 `1053-1080`；`mcpAppBoot` 定义在 `:4034`（原稿写 `4046` 指其内部分支）；§6 的 `:7378` 应为 `:7105`（声明）。
12. §4 选型理由修正：D 去掉无实据的"宿主预取/缓存"，改以契约与并发立论；E 的首要理由改为 `EXTERNAL_REF_RE` 硬拒（CSP 可被 `_meta.ui.csp.frameDomains` 覆盖）；A 补记 C2 带来的"两个 iframe"真实代价。
13. §1.2 补注：宿主模拟器**有** `sim.sendToolInput`（`mcp_apps_host_sim.html:147`），只是探针没调用——原稿"模拟器从未发出 tool-input"的措辞有误导。
14. 新增两条验收：#10（有 deck + brief 时 `read_deck` 仍要发生，否则与既有 `aa_mcp_apps_check.py:250-252` 对撞）、#11（嵌入/静态态不得隐藏工作台）。

## 16. 实施记录（2026-10-23，P1 已落地）

**代码改动**（`editor.html` v3.9.1 → **v3.9.2**，`VIEW_VERSION` 3.9.1 → 3.9.2）：

| 文件 | 改动 |
|---|---|
| `tools/bridge_core.py` | `open_editor()` 的 URL 追加 `&view=`；`page_online` 时发一次性 SSE 事件 **`view-hint`**（解 C9）；`_open_result()` 增 `view` 字段；`bootstrap_redeem()` 按 `mode` 推断 view（`new`→brief / `deck`→edit）并写进 Location |
| `tools/ext_apps_facade.js` + `tools/ext_apps_bundle.js`（重建） | 新增 `app.ontoolinput`；`tool-input` / `tool-result` **注册时重放缓冲**（`api.__lastToolInput` / `__lastToolResult`）——同时修掉文档记过的"注册晚于 connect 导致编辑器停在等待宿主下发会话" |
| `tools/bridge_mcp.py` | `VIEW_BOOTSTRAP` 增 `api.onToolInput`（含重放）；`VIEW_VERSION` 升版 |
| `editor.html` | 新增首屏分流段（`launchHint` / `launchTargetFor` / `applyLaunch` / `launchEnterBrief` / `launchEnterWorkbench` / `launchResetSize` / `launchOnDeckReady` / `briefWasSubmitted` / `briefSyncRender`）；`body[data-launch="brief"]` 整屏视图层 + chrome 隐藏；`closeBrief()` 清标记并补偿；`bridgeParseLaunch` 取 view（清 hash 前）并持久化到 sessionStorage；`bridgeStatusAndRecover` / `mcpAppBoot` / `mcpAppOnToolResult` 接分流；`bridgeApplyEvent` 处理 `view-hint`；`mcpAppApplyStatus` 写 `briefOptions` / `deckKnown`；`briefActiveOptions()` 改三态取数（**修复轨 A 动态脑暴失效**） |
| `skills/html-pptx/SKILL.md` | §1「首次交互」补一条：`view` 现在真的落位、`view="brief"` 对已有 deck 也合法（改版脑暴）、一次性意图不落库。**未改被 `r_bridge_check.py:566` 断言的那句调用字面量** |

**实施期对设计的修正**（已在 §7.2 / §10 就地更新）：

1. **`<main>` 由"隐藏"改为"被覆盖"**：deck 是 `<main>` 内的嵌套 iframe，祖先 `display:none` 会让它的视口变 0×0、内部排版塌掉且恢复不可靠。改为 `#briefOverlay` 整屏不透明遮挡后 iframe 视口全程正常；验收相应改用 `elementFromPoint` 命中测试（§10 #1）。
2. **`launchOnDeckReady()` 多一条守卫**：只在用户已提交过简报时才自动切回工作台，否则会在用户正填表时抢走表单。
3. **bootstrap 比设计更简单**：view 由服务端按 `mode` 推断（`new`→brief），无需改 LANDING 页——C8 的约束只要求它走 fragment。

**未在本次覆盖**：P2（源码级拆分 / 轨 B 真拆 `brief.html`）按决议留下一轮；真宿主端到端仍是 **NOT_RUN**。

## 17. 第二轮实施记录（2026-10-23，用户实测反馈，`editor.html` v3.9.3）

用户在真机看到脑暴页后反馈三件事，都已修（详录见 `docs/progress/1023_brief_page_split_impl.md` §5）：

1. **整屏层透明（我的 bug，也是"展示非常奇怪"的根因）**：底色写成 `var(--paper)`，而 `--paper` 是 **deck/主题侧** token、本页未定义 → `var()` 失效使 `background` 回落到 `transparent`，工作台整个透出来。已改为 `var(--bg,#f4efe6)`（本页 token + 字面量 fallback）。
   **§10 #1 的断言因此扩了一条**：不仅要求几何与命中测试，还要求 `#overlay` 的 `backgroundColor` **不透明**——原断言只看"盖住"，透明层同样能通过命中测试，所以漏了。
2. **尺寸自适应**：`.brief-wrap` 限宽 1180px 居中 + `clamp()` 内边距（原先随容器拉到 1280px 长行）；`#briefBody` 在 ≥1024px 两列网格（主题卡组/素材叙事/自由补充/画像卡/快捷条整行）；主题卡网格由 `1fr 1fr` 改为 `auto-fill + min(232px,50%-5px)`——**静态问卷路径会把全部主题内联展开**，原先在宽容器里仍是 2 列、独占约 2600px，是页面高度主因。实测 900/1280 容器下总高 −20%/−24%，四种容器横向溢出全 0。
3. **高度上报**：脑暴视图改请求"内容自然高度（钳到宿主上限）"，并单独观察 `.brief-wrap`（overlay 固定定位，内容变高不改文档高度）。宿主只声明 `maxHeight`、不知道可见区多高，请求满高会把宿主自己的底栏顶出视野——这是"底部溢出"的机制面原因。
4. **入口统一（子 agent 复核时发现的设计—实现缺口）**：顶栏「需求脑暴」按钮原先直接 `openBrief()`、不设 `data-launch`，仍是浮层形态，与 §14 决议 1 冲突。已改走 `launchEnterBrief`（与 agent 入口同一套）。

**仍未解决的（待用户决定）**：静态问卷形态（未注入 `brief_options`）内容 3400–5700px，在宿主 ≤1200px 的上限里必然内部滚动。进一步压缩需改产品形态（如维度组默认折叠的手风琴，与"脑暴是对齐不是问卷"的定位其实相符），本轮不动。
