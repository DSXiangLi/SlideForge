# 1023 · 脑暴页剥离 P1 实施实录（首屏分流 / view 下发）

> **日期**：2026-10-23
> **触发**：用户"按计划执行"——落地 `docs/design/brief-page-split.md` §12 的 P1。
> **设计依据**：`docs/design/brief-page-split.md`（含 §15 四路评审修订、§16 实施记录）；设计轮实录见 `1022_brief_page_split.md`。
> **判读纪律**：本文件的"已实测"= 有命令输出；未跑项一律写明，**不得把 NOT_RUN 写成 PASS**。

---

## 1. 改了什么

版本：`editor.html` **v3.9.1 → v3.9.2**；`VIEW_VERSION` **3.9.1 → 3.9.2**（`tools/bridge_mcp.py` + `tools/build_ext_apps_bundle.py` 同步，bundle 已重建）。

| 文件 | 改动 |
|---|---|
| `tools/bridge_core.py` | ① `open_editor()` 的浏览器 URL 追加 `&view=<v>`；② **新增一次性 SSE 事件 `view-hint`**（仅当 `page_online` 为真时发射）——会话已有在线页面时既不开新窗、fragment 也到不了它，这是唯一的投递通道（设计 C9）；③ `_open_result()` 新增 `view` 字段；④ `bootstrap_redeem()` 按 `mode` 推断 view（`new`→`brief`、`deck`→`edit`）并写进 302 Location |
| `tools/ext_apps_facade.js` + `tools/ext_apps_bundle.js` | 新增 `app.ontoolinput`；`tool-input` / `tool-result` **注册时重放缓冲**（`api.__lastToolInput` / `__lastToolResult`）。顺带修掉设计里记过的既有缺口："门面 connect 早于 editor.html 注册回调 → 通知被丢 → 编辑器一直停在等待宿主下发会话" |
| `tools/bridge_mcp.py` | `VIEW_BOOTSTRAP` 增 `api.onToolInput`（同样带重放），保证引导期注册也不丢载荷 |
| `editor.html` | 首屏分流段（`launchHint` / `launchTargetFor` / `applyLaunch` / `launchEnterBrief` / `launchEnterWorkbench` / `launchResetSize` / `launchOnDeckReady` / `briefWasSubmitted` / `briefSyncRender`）；`body[data-launch="brief"]` 整屏视图层；`closeBrief()` 清标记 + 补偿；`bridgeParseLaunch` 在清 hash **之前**取 view 并持久化到 sessionStorage；`bridgeStatusAndRecover` / `mcpAppBoot` / `mcpAppOnToolResult` 接分流；`bridgeApplyEvent` 处理 `view-hint`；`mcpAppApplyStatus` 写 `briefOptions` / `deckKnown`；`mcpAppOnToolInput` 取 `arguments.view`；**`briefActiveOptions()` 改三态取数**（修复轨 A 动态脑暴失效） |
| `skills/html-pptx/SKILL.md` | §1「首次交互」补一条：`view` 现在真的落位；`view="brief"` 对已有 deck 同样合法（改版脑暴）；一次性意图不落库。**未改被 `r_bridge_check.py:566` 断言的那句调用字面量** |

**分流规则（实现）**：`view==="brief"` 或 无 deck → 落脑暴；否则按 `view` 落工作台；嵌入态/裸静态态不参与（恒工作台，绝不隐藏）。

---

## 2. 实施期对设计的修正（已就地回写设计文档 §7.2/§10/§16）

1. **`<main>` 由"隐藏"改成"被覆盖"**。deck 是 `<main>` 内的嵌套 iframe；祖先一旦 `display:none`，该 iframe 视口变 0×0、内部排版会塌，而恢复可见只有一次 scroll 重发可补偿，不够可靠。改为让 `#briefOverlay` 变成 `inset:0` 的**不透明整屏层**去遮挡：iframe 视口全程正常。`header`/`footer`/`#bridgeBar`/`#bridgeTasks`/`#warnBanner` 不是 iframe 的祖先，直接 `display:none`。**验收口径随之改为**：上述 chrome 不可见 + `document.elementFromPoint(视口中心)` 命中 overlay 内。
2. **`launchOnDeckReady()` 多一条守卫**：只在用户**已经提交过简报**时才自动切回工作台，否则会在用户正填表时把表单抢走。
3. **bootstrap 比设计更简单**：view 由服务端按 `mode` 推断，无需改 LANDING 页（C8 只要求它走 fragment）。

---

## 3. 验证证据

### 3.1 已实测（本轮）

| # | 检查 | 命令 | 结果 |
|---|---|---|---|
| V1 | 服务端 view 下发（四种组合：有无 deck × 是否显式 view） | 临时 daemon + `/api/bridge/open`（一次性脚本，未入库） | 返回值均含 `view` 且与入参一致；URL 均含 `view=`。**注意"无 deck + 缺省"回的是 `view="edit"`**——正因如此 §7.1 才必须"无 deck 恒 brief"来吸收 MCP 的默认值，否则新建 deck 首开会退化成空工作台 |
| V2 | 核心状态机未回归 | `python3 -m pytest tests/harness/test_bridge_core.py -q` | **44 passed, 44 subtests passed**（与基线一致） |
| V3 | `editor.html` 内联脚本语法 | 抽出 script 块 `node --check` | OK（过程中抓到并修掉一处：插入分流段时吞掉了 `briefOptLabel` 的函数头） |
| V4 | View bundle 与源一致 | `python3 tools/build_ext_apps_bundle.py --check` | `OK bundle sha256=f4934f98… bytes=258294` |
| V5 | **首屏分流端到端复验**（轨 A 宿主模拟器，脚本由我独立写、未入库） | `python3 /tmp/verify_launch.py` | **5 场景全 PASS**：S1 无 deck+brief / S2 有 deck+brief（症状回归，含关闭清标记）/ S3 有 deck+edit / S4 有 deck+缺省 view / S5 tool-input 说 brief 覆盖 tool-result 的 edit。每场景断言：`data-launch` 置位、overlay 已显示、**几何 ≈ 视口（1280×900）**、header/footer 已隐藏、**视口中心命中 overlay**（工作台够不着）、有 deck 时 `read_deck` 仍发生、宿主模拟器零自身错误 |
| V6 | **注册期缓冲重放**（真实 bundle 内） | `python3 /tmp/verify_buffer.py` | tool-input 与 tool-result 均在"载荷先到、后注册"时立刻重放（`{"got":{"arguments":{"view":"brief"}},"buffered":true}` / `{"got":true,"buffered":true}`） |

证据日志：`docs/progress/_logs/1023_verify_launch.log`（V5/V6/V2 的原始输出）。

### 3.2 验收用例与回归（已完成 / 待补）

- **T36（`aa_mcp_apps_check.py`）扩到 §10 的 14 条 —— `RESULT: ALL PASS`**（连跑 3 次无 flake）。新增断言覆盖：两臂下的无 deck/有 deck + `view=brief`、缺省路径、`view=edit/annotate/export`、注入 `brief_options`（轨 A 动态脑暴）、Esc/✕ 关闭、`tool-input` 优先与缓冲重放、高度上报自愈、`read_deck` 仍发生、2s 轮询不翻视图、静态/嵌入态不参与分流、全程无 `pageerror`。
  - **防"恒真断言"**：仓库无 VCS，无法真跑"修复前代码"对比 → 改用**突变探针**：把已建立的脑暴视图当场还原成修复前形态（520px 抽屉 + 去 `data-launch` + chrome 恢复），6 条关键断言**全部由绿转红**。
- **`r_bridge_check.py` 7 组全 PASS**（新增：`open_editor` 返回体/URL 的 `view` 契约、bootstrap 两种 mode 的推断、未知 `view` 值回落、`view-hint` 事件驱动的在线页面切换）；既有 `:157`（恰好五工具精确列表）/`:231`/`:357` 未改仍通过。
- **`pytest tests/harness/test_bridge_core.py` → 44 passed**（基线不变）。
- **`build_ext_apps_bundle.py --check` → OK**（sha256 `f4934f98…`，258294 字节）。
- 完整 `run_e2e.py`（62 项基线）——**本节结果以 `docs/progress/_logs/1023_run_e2e.log` 为准**。
- 真宿主 SproutHarness 端到端目检——**NOT_RUN**（本机不可实测，P4 仍阻塞在宿主侧）。

---

## 4. 未做 / 遗留

- **P2（源码级拆分 + 轨 B 真拆 `brief.html`）**：按用户决议留下一轮（设计文档 §8/§11/§12）。
- **高度上报在视图切换后是否自愈**：实现里已重置 `mcpApp.reportedHeight` 并补发，但**属推测性修复**，须由 T36 对应断言实测确认（设计文档 §10 #9）。
- 轨 A 的 `brief_options` 动态脑暴修复已并入本次；其端到端断言同属 T36 待补项。

---

## 5. 用户实测反馈修复（同日第二轮，v3.9.3）

### 5.1 现象与根因

用户实测报告：脑暴页"直接展示在原始首页上"、"底部打开文件等都溢出了"、"尺寸有压缩、展示非常奇怪"。

**根因是我的一个 CSS token bug**：整屏视图层的底色写作 `background:var(--paper)` —— 而 **`--paper` 是 deck/主题侧的 token，`editor.html` 自己并没有定义它**（本页的 token 是 `--bg/--bar/--border/--text/--muted/--accent/...`）。CSS 中 `var()` 引用未定义变量会让**该声明在计算值阶段失效**，`background` 回落到初始值 `transparent` —— 于是整屏层是**透明的**：脑暴内容直接画在工作台之上，底下顶栏、目录、画布、状态栏全部透出来。这正是"贴在原始首页上""底部都溢出"的来源。

**我的复验盲区（已补）**：V5 只断言了 `data-launch` / 几何 / `display:none` / `elementFromPoint` 命中 —— 全部与"透明度"无关，所以一条都没红。已在复验脚本里补上 `getComputedStyle(#briefOverlay).backgroundColor` 必须不透明这一断言（新增后当场复现旧 bug 会红）。

### 5.2 尺寸自适应：改动与实测

| 改动 | 说明 |
|---|---|
| 底色修正 | `background:var(--bg,#f4efe6)`（本页 token + 字面量 fallback，双保险） |
| 内容限宽居中 | `.brief-wrap{max-width:1180px;margin:0 auto}` + 内边距 `clamp()`——原先 `max-width:none`，容器多宽就拉多宽（1280px 容器 → 1280px 长行） |
| 宽容器两列 | `#briefBody` 在 ≥1024px 走两列网格（维度组本是彼此独立的卡片）；主题卡组 / 素材叙事 / 自由补充 / 画像卡 / 快捷条整行（`:has()` 命中） |
| 主题库自适应列数 | `.theme-grid` / `.theme-group-cards` 由硬编码 `1fr 1fr` 改为 `auto-fill` + `min(232px, calc(50% - 5px))`——**静态问卷路径会把全部主题内联展开**，原先在宽容器里仍是 2 列、独占约 2600px，是页面高度的主因；下限取 `50%-5px` 保证窄容器保底仍 2 列（第一版写成 232px 下限，420px 容器掉成 1 列反而更高，已改） |
| 高度上报 | 脑暴视图请求**内容自然高度（钳到宿主上限）**而非恒定满高：宿主只声明 `maxHeight`、不知道可见区多高，请求满高会让 iframe 比可见区还高、把宿主自己的底栏顶出视野；并单独 `observe` `.brief-wrap`（overlay 是固定定位，内容变高不改文档高度，否则不会重报） |

实测（`docs/progress/_logs/1023_brief_size_adaptive.log`；内容为**静态问卷**，即未注入 `brief_options` 的最长形态）：

| 容器 | 脑暴内容高 修前 → 修后 | `.brief-wrap` 宽 | `#briefBody` 列 | 横向溢出 | overlay 背景 |
|---|---|---|---|---|---|
| 420×720（宿主侧栏） | 5868 → 5675 | 420 → 420 | 1 → 1 | 无 | 透明 → `rgb(244,239,230)` |
| 700×500（矮容器） | 4922 → 4800 | 700 → 700 | 1 → 1 | 无 | 同上 |
| 900×1200（宿主 maxHeight 档） | 4629 → **3721**（−20%） | 900 → 900 | 1 → 1 | 无 | 同上 |
| 1280×900（宽容器） | 4430 → **3369**（−24%） | 1280 → **1180** | 1 → **2** | 无 | 同上 |

其中主题库那一个分组：1280 容器下 2628 → **1695**（−35%）。四种容器**横向溢出全为 0**（窄容器不再挤压出界）。

### 5.3 入口统一（子 agent 报的缺口，已修）

`$('btnBrief').addEventListener('click', openBrief)` 走的仍是老 `openBrief()`——**不设 `data-launch`**，于是"从工作台点进去"依旧是 520px 浮层 + 工作台可见，与决议"脑暴形态统一为视图切换、不留两种形态"直接冲突。已改为 `launchEnterBrief`（与 agent 入口同一套），并在其内记录 `launch.applied`，避免后续 status 重放与用户当前视图打架。

### 5.4 判读

- 以上均为**当前实现**的实测数字；真宿主 SproutHarness 内的目检仍是 **NOT_RUN**（本机无法运行宿主），"宿主里不再顶出底栏"这一点只有机制层证据（改请求内容高度 + 不再要满高），**未经真机确认**。
- 静态问卷形态在 ≤1200px 的宿主上限里**依然需要内部滚动**（内容 3400–5700px）。进一步压缩要动产品形态（例如把维度组做成默认折叠的手风琴——与"脑暴是对齐不是问卷、答几组算几组"的理念一致），**不在本轮**，待用户决定。
