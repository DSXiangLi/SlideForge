# 1022 · 脑暴页剥离（Brief page split）：设计先行 + 四路独立评审实录

> **日期**：2026-10-22（与 `1022_mcp_apps_compliance_review.md` 同日，主题不同）
> **触发**：用户反馈"调用工具后脑暴的页面无法直接打开，还需要用户去点击按钮"，要求把脑暴页从 `editor.html` 里整体剥离。
> **本轮性质**：**纯设计轮，零代码改动**。产出 = 设计文档 `docs/design/brief-page-split.md`（评审后 31930 字节 / 286 行）+ 一支一次性实测探针的结论 + 三条用户决议 + 四路独立评审及其折入。
> **判读纪律**：本文件的"已实测"= 有探针/命令输出；"读源码所得"= 静态阅读（**不等于运行验证**）；"未跑"一律写明。**本轮没有任何代码回归跑分**——`run_e2e.py` / pytest / `r_bridge_check` / `aa_mcp_apps_check` **均未跑**，不得把探针结论或子 agent 的静态阅读写成 PASS 进验收表。

---

## 1. 结论

1. **"必须点按钮"的根因不是页面结构，而是 `view` 参数从未下发到 UI**：`BridgeCore.open_editor()` 校验后即丢弃 `view`（`tools/bridge_core.py:863-865`），`_open_result()`（:898-906）不回传，轨 B 的 URL 硬编码（:883 / bootstrap :1912），轨 A 的门面（`tools/ext_apps_facade.js:17,23`）只订阅 `teardown`/`toolresult`。UI 只能按"有没有 deck"猜。
2. **结构性事实**：脑暴在 `editor.html` 内是一层 `position:fixed` 的**右侧 520px 抽屉**（CSS 559-635 / markup 1053-1080 / JS 5850-6753，合计约 1010 行，占全文 11.8%），与工作台共享 49 个外部符号。即使它自动打开，"打开的那个页面"仍是编辑器。
3. **一个硬约束决定了方案形状**：宿主 SproutHarness 按**工具的静态** `_meta.ui.resourceUri` 取页面（`feature+mcp-apps` 分支 `src/sprout_harness/agent/graph.py:833-841`），工具结果的 `_meta` 不做资源覆盖，官方规范（`apps.mdx:319-347`）也只把 `resourceUri` 定义在 Tool 上 → "让宿主渲染另一个页面"**只能靠另一个工具**，代价是模型可见工具 5→6（破 `AGENTS.md` 红线 + `tests/harness/r_bridge_check.py:157` 的**精确列表**断言 + SKILL 契约）。
4. **选定方案**：**单工具·首屏分流**（用户确认）——五工具不动，`view` 真正下发，`view=brief` 时工作台隐藏、脑暴成为整屏视图。
5. **四路独立评审结论**：方案成立、无"根因判错"，但原稿有 **7 条硬错误**（隐藏集漏 `<header>`、`#briefOverlay` 是抽屉非整屏、关闭不解除标记会白屏、缺省分流公式自相矛盾、deck 到达不会自动退出、bootstrap 无处携带 view、已在线页面收不到 view），**全部已折入设计文档 §15**。按旧稿实施会翻车。

---

## 2. 实测证据（可复现）

### 2.1 方法与一次性探针

把 `tests/harness/aa_mcp_apps_check.py` 的驱动抽成一次性脚本（**真** `tools.bridge_mcp.build_view_html()` + **真** daemon（`BridgeCore` 全套状态机）+ 宿主模拟器 `tests/harness/mcp_apps_host_sim.html?sandbox=trusted`），每个场景独立 workdir + daemon，`open_browser=False`，随后 `hostSim.sendToolResult(<open_editor 的返回体>)` 并观察 View frame 内 `#briefOverlay` 的 `.show`。

探针脚本用完即删（未入库；重建配方见 §6.3）。

### 2.2 结果

| 场景 | `view` | 会话状态 | 脑暴自动打开 | 说明 |
|---|---|---|---|---|
| S1 | `brief` | `phase=briefing`，无 deck | ✅ | **不是因为 `view`**，而是因为"没有 deck" |
| S2 | `edit` | `phase=briefing`，无 deck | ✅ | 同样打开 → 反证 S1 的机制（`view` 被忽略） |
| S3 | `brief` | `phase=editing`，有 deck | ❌ | **复现用户报告**：必须点顶栏「需求脑暴」 |

三条的附加观测（同一批输出）：

- 浏览器 URL 一律 `editor.html#brt=…&session=…`，**不含 view**；
- `open_editor` 返回体键集：`ok/protocol_version/session_id/deck_path/target_path/resource_path/revision/phase/url/page_online/view_attached/track/agent_state/consumer_state/git_initialized/brief_options/capabilities`（**无 `view`**；`protocol_version` 见 `bridge_core.py:899`）；
- 探针没有调用宿主模拟器的 `sim.sendToolInput`（该函数**存在**，`mcp_apps_host_sim.html:147`），而 View 侧也没有 `window.pptxMcp.onToolInput`。⚠️ **不能说成"宿主不发 tool-input"**——真宿主在 `initialized` 时同时发 input 与 result（`src/sprout_harness/agent/webui.html:5508` 与 `:5515`），真正的风险是"**通知早于回调注册**"（门面 connect 在 `ext_apps_facade.js:178` 立即执行，`editor.html:4363` 才注册回调）。

### 2.3 宿主侧核对（读源码，非实测运行）

| 事项 | 位置 | 结论 |
|---|---|---|
| 按哪个资源渲染 | `SproutHarness/.claude/worktrees/feature+mcp-apps/src/sprout_harness/agent/graph.py:833-841` | 用 `entry.ui_meta["resource_uri"]`（来自 `tools/list`），**工具结果不参与** |
| 是否每次新建 iframe | 同分支 `src/sprout_harness/mcp/sandbox.py:41`（`def store_app_html`，`uuid4()` 在 `:59`） | 每个 UI 工具调用一个新 app instance |
| 是否会漏发工具结果 | 同分支 `src/sprout_harness/agent/webui.html:5508,:5515` | 宿主**显式等待** View 的 `initialized` 才发 `tool-input`/`tool-result`（注释在 `:5586-5591`）→ 无"View 还没起来就发"的竞态 |
| 资源是否被预取/缓存 | 全仓 grep | **未发现**预取/缓存代码（每次调用才 `_fetch_ui_resource`；唯一缓存是 per-instance buffer `sandbox.py:60`，属预期） |
| 规范口径 | `~/Desktop/ext-apps/specification/2026-01-26/apps.mdx:319-347` | `resourceUri` 只定义在 Tool 上 |

### 2.4 仓库内既有断言（决定改动代价）

| 断言 | 位置 | 影响 |
|---|---|---|
| 工具面**精确列表** `names == [五个]` | `tests/harness/r_bridge_check.py:157` | 任何第 6 个工具必破——"不新增工具"的直接验证点 |
| SKILL 调用字面量被断言 | `tests/harness/r_bridge_check.py:566`（含 `open_editor(deck_path=null, output_path="index.html", view="brief", open_browser="auto")`） | 本次**不改**这句话，故无需动断言 |
| `open_editor` 结果体断言 | `tests/harness/r_bridge_check.py:188,200`（`:185`/`:199` 是 `call_tool` 调用行） | 逐字段取值断言，**新增 `view` 字段不会破**（全仓无对返回体的精确键集断言） |
| 轨 B 启动 URL 断言 | `tests/harness/r_bridge_check.py:231`（`startswith("/editor.html#brt=")`）、`:357`（`launch["hash"] == ""`） | 对"fragment 尾部追加 `&view=`"的改法仍成立 |
| T36 已注册为 e2e 子进程 | `tests/harness/run_e2e.py:2965` | 验收落点 |
| e2e 基线 | `docs/progress/_logs/1022_run_e2e_after_host_reread.log` 末行 | **62 项 / 61 PASS / 1 FAIL**，唯一 FAIL = T34（theme-proving，既有失败） |

---

## 3. 设计决议（2026-10-22 用户）

| # | 议题 | 决议 |
|---|---|---|
| 1 | 脑暴页形态 | **统一为视图切换**：编辑态点「需求脑暴」也隐藏工作台，不留"浮层 / 视图"两种形态；Esc / 关闭回工作台 |
| 2 | 有 deck 时 `view="brief"` | **允许**（修复 S3 的必要条件；语义 = 改版脑暴） |
| 3 | 源码级拆分（P2） | **本轮不做**：只做 P1；`views/` 源目录 + 组装脚本 + 轨 B 真拆 `brief.html` 留下一轮 |

选型与否决理由（含被评审修正过的 D/E/A 三条）见设计文档 §4。

---

## 4. 四路独立评审（2026-10-22，子 agent，只读）

四个只读子 agent 分别从**事实核对 / 外溢风险 / 验收充分性 / 替代方案**独立审核设计文档与本文，要求"必须给 `file:line`、允许推翻"。结论：**方案成立、无根因判错，无阻断性方向问题**；但发现 7 条硬错误 + 若干事实口径修正，已全部折入设计文档 §15。

### 4.1 硬错误（按旧稿实施会翻车）

| # | 问题 | 证据 | 后果 |
|---|---|---|---|
| 1 | **隐藏集漏 `<header>`** | 顶栏在 `editor.html:793-824`，是 `<main>`（`:845`）的**兄弟**；`#bridgeBar:826`/`#bridgeTasks:833`/`#warnBanner:835` 同样在 main 外 | 脑暴顶上仍是一条工作台工具栏，而原验收只断言 main/footer → **假 PASS** |
| 2 | **`#briefOverlay` 是 520px 右侧抽屉** | `editor.html:559-565`（`position:fixed; top/right/bottom:12px; width:min(520px,94vw)`） | "可见性切换"达不成"占据整屏" |
| 3 | **关闭不解除标记 → 白屏** | `closeBrief()`（`:6485`）只 `remove('show')`；Esc（`:6489`）与 ✕ 共用 | 关闭后 `<main>` 仍隐藏 |
| 4 | **缺省分流公式自相矛盾** | 原式在"无 deck + `view="edit"`"（S2）下落工作台，与"与今天一致"冲突；且 MCP 默认 `view="edit"` **无条件透传**（`tools/bridge_mcp.py:300,310`） | 新建 deck 首开退化成空工作台 |
| 5 | **"轮询发现 deck → 切工作台"不是既有行为** | `closeBrief` 全仓无自动调用点（`grep briefOverlay` 仅 8 处命中） | S3 下用户提交后停在脑暴，以为没动静 |
| 6 | **bootstrap 无处携带 view** | `/bootstrap` query 被精确校验（`bridge_core.py:2185`）、LANDING 只透传 `#boot`（`:1920`）、`bootstrap_tokens` 无该列 | "`edit.py --new` 也落脑暴首屏"无法实现 |
| 7 | **已在线页面收不到 view** | `bridge_core.py:886-890`：`page_online` 时不 `webbrowser.open`；`_schedule_view_window.fire()` 同样早退 | 会话已有驻留页面时，S3 症状**仍然残留** |

### 4.2 事实与口径修正（已折入）

- **C7 新增**：真宿主**确实**发 `tool-input`；风险是"注册晚于 connect"→ 接它必须带**缓冲重放**，且它是**并行冗余**而非"优先级更高的兜底"。
- **"非法 view 不 400"收窄**：MCP 参数的非法值由 SDK 的 `Literal` 直接拒（到不了 daemon）；daemon 的 400 **保持不变**；"忽略未知值"只适用 URL fragment / `tool-input`。
- **§7.3 映射表改为"一入两出"**：内部 `view` 域只有 `edit|compare|export`（`:7105`），`annotate` 实为 `setView('edit')+setMode('annotate')`（`:7394-7396`）；launch 应用点必须在 `openHtml`（内部会重置 `view='edit'`，`:4598-4600`）**之后**。
- **引用修正**：`sandbox.py:41` 是 `def`、`uuid4()` 在 `:59`；返回体键集补 `protocol_version`；r_bridge_check 断言在 `:188/:200`；嵌入态 `brief_options` 覆盖是 **T35e**（`y_dynamic_brief_check.py`，原稿误写"REQ-T36b"，全仓不存在）；markup 为 `1053-1080`；`mcpAppBoot` 定义在 `:4034`。
- **选型理由修正**：D 去掉无实据的"宿主预取/缓存"（改用契约 + 并发立论）；E 的首要理由是 `EXTERNAL_REF_RE` 硬拒含 `<iframe src=` 的 View（`tools/bridge_mcp.py:105-107,170-171`），CSP 只作次要理由（它可被资源 `_meta.ui.csp.frameDomains` 覆盖）；A 补记 C2 带来的"脑暴与编辑变成两个 iframe"真实代价。
- **新增两条验收**：有 deck + `brief` 时 `read_deck` 仍必须发生（否则与既有 `aa_mcp_apps_check.py:250-252` 的 `wait_for("read_deck")` 对撞）；嵌入态/裸静态态不得隐藏工作台。
- **两条隐藏态副作用**：隐藏 `<main>` 会复现 `editor.html:7379-7382` 自述的 offsetTop 塌陷 / `curSlideIdx` 漂移；高度上报去重（`mcpAppReportSize`，`:4022`）可能在内容骤降后不自愈 → 切换时重置 `reportedHeight`（**高置信推测，须 T36 实测**）。

### 4.3 评审未能验证的部分（纪律）

- 真宿主 SproutHarness 端到端、`tool-input` 的实际下发时机——**读源码所得，非运行实测**。
- 任何回归（`run_e2e.py`/pytest/r/aa）——**未跑**。
- 工作区**不是 git 仓库**（`git rev-parse` 失败）→ "本轮零代码改动"只能用文件 mtime 弱佐证，无法用 diff 证伪。
- "共享 49 个外部符号"未逐符号复核（行数与占比已复算）。

---

## 5. 顺带发现的既有缺陷（与本次同源，一并修）

**轨 A 下 `brief_options` 完全不生效**：`briefActiveOptions()`（`editor.html:5966`）在非 Bridge 态只读 `embedBriefOptions`；轨 A 的 `mcpAppApplyStatus()`（`editor.html:3984-3992`）拿到 `st.brief_options` 却不存；轨 A 下 `bridge.enabled` 恒为 false（唯一赋值点 `:7913` 在 `bridgeParseLaunch` 内，而它因 `state.embedded` 于 `:7901` 早退）。后果：`AGENTS.md` / `SKILL.md` 承诺的"可携 `brief_options` 注入动态脑暴"在宿主内失效（轨 B 正常）。这是 `docs/design/brief-dynamic-brainstorming.md` P1 验收范围没覆盖到的轨 A 缺口。

---

## 6. 产出物与下一步

### 6.1 产出物

| 文件 | 状态 | 说明 |
|---|---|---|
| `docs/design/brief-page-split.md` | **新增**（31930 字节 / 286 行，待评审） | 含 §15 评审修订记录（7 条硬错误 + 7 条事实修正） |
| `docs/design/README.md` | 改（+1 行） | 文档地图登记 |
| `docs/progress/1022_brief_page_split.md` | **新增**（本文件） | 本轮实录 |
| `docs/progress/README.md` | 改（+2 处） | 最近更新 + 按日期索引 |

**本轮零代码改动**：`editor.html` / `tools/*` / `tests/harness/*` 均未动。

### 6.2 P1 改动清单（评审后版，逐条对标）

1. `tools/bridge_core.py`：`url`（`:883`）fragment 尾部追加 `&view=`；`bootstrap_redeem()`（`:1912`）+ LANDING（`:1920`）+ 票据按 C8 处理（`view` 只能走 fragment，或按 mode 推断：`new`→brief、`deck`→edit）；`_open_result()`（`:898-906`）增 `view` 字段；`notice` 事件增一次性 `view`（解"已在线页面"）。
2. `tools/ext_apps_facade.js` + `tools/bridge_mcp.py` 的 `VIEW_BOOTSTRAP`：新增 `onToolInput`，带**缓冲重放**。
3. `editor.html`：`bridgeParseLaunch`（`:7900`）在清 hash 之前取值 → `launchView` 判定（无 deck 恒 brief；嵌入/静态态恒 edit）→ `data-launch` 视图切换（隐藏集 **header+main+footer**（+桥栏/warn 区待定）；`#briefOverlay` **几何改写为整屏**）→ `closeBrief()` 解除标记 → deck 到达自动退出脑暴 → 隐藏态副作用处理（offsetTop/curSlideIdx 恢复、`reportedHeight` 重置）→ `mcpAppApplyStatus()`/`briefActiveOptions()` 三态取数。
4. `skills/html-pptx/SKILL.md`：补一句"有 deck 时 `view=brief` 的语义"；**不动 `r_bridge_check.py:566` 断言的那句字面量**。
5. `tests/harness/`：T36 十四条（含臂标注）+ `r_bridge_check` 两条；S1/S3 症状回归用例（S2 期望按新公式改写）。

### 6.3 门禁与探针重建

- **门禁**：T36 全 PASS + `run_e2e.py` 除既有失败 T34 外无新增 FAIL（基线 62 项 / 61 PASS / 1 FAIL）。跑分证据落 `docs/progress/` 与 `docs/test_acceptance/`，不进 `AGENTS.md`。
- **探针重建配方**：复用 `tests/harness/aa_mcp_apps_check.py` 的 `static_server()`（:72）、`find_view_frame()`（:84）、`make_tool_proxy()`（:126），外加从 `s_bridge_scale_check` 导入 `Daemon`/`managed_post`/`bind_browser_token`（该文件 `:47-49` 已示范）；另需 `build_view_html()` 落成 `view.html` 交给 static_server、`page.expose_function("mcpCall", proxy)`。差别只有三点：① `view` 入参；② 有 deck 场景要先把 `index.html` 落盘再 open；③ 断言 `#briefOverlay` 的 `.show`。注意该配方复现的是**修复前**行为，转正式用例时 S2 的期望要重写。

### 6.4 未跑项（不得写成 PASS）

- 真宿主（SproutHarness 分支合并后的端到端目检）——**NOT_RUN**，P4 仍阻塞在宿主侧（承接 `1021_mcp_apps_handover.md` §2）。
- 本轮任何代码回归（`run_e2e.py` / pytest / r / aa）——**未跑**（无代码改动）。
- 宿主 `tool-input` 的实际下发与时机——**读源码所得**（`webui.html:5508`），**未运行实测**。
- 设计文档里的"共享 49 个外部符号""隐藏态高度上报不自愈"——**未逐项复核 / 属推测**，后者须 T36 实测。

---

## 7. 后续

P1 已按本文收敛的设计实施完毕，实施实录（含实现期对设计的三处修正、验证证据与遗留）见 **`1023_brief_page_split_impl.md`**。
