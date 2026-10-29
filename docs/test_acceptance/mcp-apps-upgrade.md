# 验收证据 · MCP Apps 接入（P0.5 + P1 + P2 + P3）

> 日期：2026-10-21 · 交接与待办见 `docs/progress/1021_mcp_apps_handover.md` · 设计与偏差见 `docs/design/mcp-apps-upgrade.md`（§10 为落地事实）
> **判读纪律**：未跑项写 NOT_RUN；不做"跑绿即等价于宿主可用"的外推（真实宿主 P4 是 NOT_RUN）。

---

## 1. 结论摘要

| 项 | 结论 | 证据 |
|---|---|---|
| P0.5 协议修（D1–D4） | ✅ 实施并自证 | `test_bridge_core.py` 44 passed（含 P0.5 新增 6 例）；`SKILL.md` §3.1 契约断言在 `r_bridge_check --group integration` 中通过 |
| P1 宿主适配层（零行为变化） | ✅ 实施并回归 | `r_bridge_check` 六组（含 Playwright `ui` 组）**未改一行断言**全绿 |
| P2 server 双模 | ✅ 实施并自证 | 新增 `r_bridge_check --group apps`（默认跑）全 PASS；工具面/资源/自校验断言见下 |
| P3 View 第四态（轨 A） | ✅ **通过（按官方规范口径）**：规范沙箱下全功能；不合规宿主（只有 `allow-scripts`）**明确报错 + 处置指引**，不做降级模式 | `aa_mcp_apps_check.py` 两臂 ALL PASS（T36，连跑多次一致） |
| 完整 e2e 回归 | ✅ **62 项 61 PASS / 1 FAIL**（唯一 FAIL 是既有 T34） | `docs/progress/_logs/1021_run_e2e_final3.log` 末行 `==== 汇总：62 项，61 PASS，1 FAIL ====`（G7 裁决后重跑；T16 含新增双向断言 PASS、T29 七组 PASS、T36 PASS；此前 final2/final 同结论） |
| 遗留检查补跑（§2.6） | 见 §2.6：**`u_ --formal` PASS**、**`s_ integration/perf03/convert/cns08` 四组全 PASS**、`v_ --self-check` PASS、`z_` 已重跑；仅 `v_ --host` 仍是 **NOT_RUN**（需授权付费模型调用） | 各日志见 §2.6 |
| G7 适用范围裁决（§2.6.1） | ✅ 已裁决并实施（`uploaded` 豁免为告警；生成侧仍硬错误） | `docs/design/g7-resolution-floor-scope.md`；`cmb-retail` exit 1 → **exit 0**，`bake-mix` 零告警，`--mode illustration` 仍 rc=1；T16 双向断言 |
| **合规审计后的最小修复（A1/A2/A4，§2.7）** | ✅ 实施并自证（含**变异测试**：断言确实会响） | `aa_mcp_apps_check.py` 两臂 ALL PASS；`r_bridge_check --group apps --group ui` PASS；`build_ext_apps_bundle.py --check` OK；审计与更正见 `docs/progress/1022_mcp_apps_compliance_review.md` |
| P4 真实宿主端到端 | ⏳ **NOT_RUN** | SproutHarness 分支未合并；Claude Desktop 本机无法实测 |
| Office 365 / WPS 目检 | ⏳ **NOT_RUN** | 人工项 |
| `s_/u_/v_` 三个遗留检查 | ⏳ **NOT_RUN** | 本轮未跑 |

---

## 2. 实测记录

### 2.1 核心单测（未改动测试文件）

```
$ python3 -m pytest tests/harness/test_bridge_core.py -q
44 passed, 44 subtests passed in 15.95s
```

### 2.2 协议验收（六组未改动 + 新增 apps 组）

```
$ python3 tests/harness/r_bridge_check.py
PASS transport: official SDK initialize/list/call, bounded schema, concurrency, 100 cancellations
PASS sdk: official SDK production stdio initialize/list/call with exactly five tools
PASS apps: dual-mode tool face (5/18) with double-written visibility, self-contained view resource,
           track-A attach/arbitration/read/save/intent/draft chain and tool-layer self-validation
PASS http/security: real daemon auth, browser binding, intent idempotency/query, Host/Origin/static isolation
PASS ui: real daemon + Playwright no-deck first load, receipt generations, clean/dirty asset revision handling,
         dirty protection, forced export refresh, SSE parser, fragment hygiene
PASS integration: SKILL bridge contract + real MCP/HTTP no-deck claim, isolated work_path, revision CLI,
                  validation publish, receipt replay, bounded reattach
PASS fault: 9 captured unittest cases + real HTTP SSE expired-cursor resync
```

**对既有断言的最小改动（如实记）**：`--group integration` 里 SKILL 契约断言有一条字面量
`open_editor(..., open_browser=true)`，本轮 SKILL 桥流程改为显式 `open_browser="auto"`，该字面量同步
更新（1 行）。**其余断言零改动**——工具面"恰好五个"、`capabilities` 精确相等、JS/SSE/鉴权行为都原样通过。

`--group apps` 覆盖的断言（逐条）（**2026-10-27 按 1027 精简更新计数与链路**）：
- **工具面双模**：`PPTX_HTML_APPS_TOOLS=never`（等价于未声明扩展的客户端）→ 恰好五个工具；`=always` → **14** 个（1027 精简前为 18）；
- **app-only 的可见性标注**：**9** 个 app-only 工具（1027 精简前 13 个）**每个**都写 `_meta.ui.visibility:["app"]`，且**不带**根级 `_meta.visibility`（F4：规范只认 `ui.visibility`；本文档此前记的"根级 + `ui` 双写"是 F4 之前的状态）；
- **入口 `_meta` 三处写**：`open_editor` 的 `ui.resourceUri` 与 `ui/resourceUri` 都是 `ui://pptx-html-bridge/editor.html`；
- **资源契约**：mime `text/html;profile=mcp-app`、`_meta.ui.permissions={"clipboardWrite":{}}`、View HTML ≤ 2 MB（2026-10-28 实测 **746 KB** @ v3.9.7）、含引导门面与 SDK bundle、无外链 `script`；
- **轨 A 链路**：`attach_view` → `get_status.track == "mcp-app"` → `await_intent(kind="mcp_app")`（已决即采用，不阻塞）→ `read_deck` → `save_deck`（revision 前进）→ 陈旧 `base_revision` 被拒（`REVISION_CONFLICT`）→ `submit_intent`（含 `anchor`）→ `save_draft` → `read_bundle_file`（`assets`/`fonts` 前缀读资产、`export/` 前缀读产物）/`write_asset` → `list_versions`；`cancel_intent` / `retry_intent` / `query_intents` 三个**工具**已于 1027 删除（其 daemon 路由仍由 `test_bridge_core.py` 覆盖，轨 B 继续使用）；
- **工具层自校验**（不依赖宿主鉴权）：外部 session → `SESSION_NOT_OWNED`；`assets/../../.pptx-html/serve.json` → 拒；未登记资产 → `NOT_FOUND`。

### 2.3 View 端到端（T36，自带宿主模拟器）

```
$ python3 tests/harness/aa_mcp_apps_check.py
RESULT: ALL PASS (aa_mcp_apps_check)          # 连跑两次结果一致
```

被测对象是真货：`tools/bridge_mcp.build_view_html()` 产出的 View HTML（editor.html + 官方 ext-apps 2.0.3 bundle + `window.pptxMcp` 门面）+ 真 daemon（BridgeCore）；宿主侧由 `tests/harness/mcp_apps_host_sim.html` 复刻（sandbox、宿主默认 CSP、JSON-RPC 2.0、两阶段拆卸、工具经宿主代理）。

**规范沙箱臂（`sandbox="allow-scripts allow-same-origin"`）——全部通过**：
1. 握手：View 内 `window.pptxMcp` 由引导脚本同步可见 → `hostKindDetect` 判为 `mcp-app` → `ui/initialize` 应答 → 宿主收到 `ui/notifications/initialized`；
2. 会话下发：宿主发 `ui/notifications/tool-result`（open_editor 结果文本）→ View 自动 `attach_view` → `get_status` → `read_deck`（顺序被断言）→ deck 可读；daemon 侧 `track=mcp-app`、`view_attached=true`；
3. 保存：改文字 → `saveDeck()` → `save_deck` → revision 前进、目标文件写入新文案、**保存产物不含 `data:` URI**（水合被正确还原为 `assets/` 相对路径）；
4. 草稿：`setDirty` → 防抖 `save_draft` → `/api/bridge/drafts` 可查；
5. 便条：`setModelContext` 收到含"编辑器状态镜"的文本（2s 防抖）；
6. 两阶段拆卸：宿主发 `ui/resource-teardown` → View **先落草稿**再回执，宿主收到回执并进入 torn-down。

**非规范宿主负例臂（`sandbox="allow-scripts"`，不透明源）——明确报错 + 指引**（决策：按官方规范开发，不做降级）：
- 状态栏置错误态"宿主沙箱不符合规范"，提示与横幅都写明需要 `sandbox="allow-scripts allow-same-origin"`，并给出"暂用轨 B 独立窗口"的处置；
- 断言文案里**不得出现"只能查看"这类降级措辞**；`doc() === null` 是预期的拒绝理由，不是可编辑态。

### 2.3.1 v3.9.5 新增断言（⑨ 首份 deck 到达 / ⑩ 本地画布守卫 + 轨 A 换图）

```
$ python3 tests/harness/aa_mcp_apps_check.py
RESULT: ALL PASS (aa_mcp_apps_check)
```

- **⑨ 首份 deck 到达**（复现并封住"agent 生成完 deck 后页面既不关脑暴也不进编辑视图"）：无 deck 的 briefing 会话 → 页面点真按钮 `#btnBriefSend`（经 `submit_intent` 工具）→ agent 侧只走真 daemon 路径（`/api/bridge/await` 认领 → 工作副本写 deck → `/api/bridge/update complete` 发布）→ 断言 View 调 `read_deck`、渲染新 deck、`data-launch` 被摘除、header/footer 恢复可见、落 `view=edit`。
- **⑩ 本地画布守卫 + 轨 A 换图**：(a) 用 `openHtml(text, 'local.html', null, undefined, null)` 造出与 `<input type=file>` 回路完全同形的**本地画布** → `saveDeck()` 断言**没有** `save_deck` 调用、横幅说明原因、受管 deck 字节未变（否则 `mcpAppPath(null)` 会用本地文件覆盖 agent 的 deck）；(b) 回受管画布后驱动真 `replaceImage()`（Playwright `filechooser` 事件喂文件）→ 断言走宿主通道 `write_asset`、`data-image-state=uploaded`、保存成功后产物是 `assets/pixel.png` 且**无** `data:` URI。
- **⑩ 连跑 5 次 5/5 PASS**（该臂曾因 harness 侧技术问题（轮询谓词不驱动 Playwright 回调分发）表现为"保存卡 15s"，已改为浏览器侧谓词，见 `docs/progress/1026_open_file_track_and_first_deck.md` §3.1）。
- **变异探针**：把轮询条件改回旧式（`st.revision && mcpApp.revision && …`）后 ⑨ **必红**（`等待超时（25s）：首份 deck 到达后 View 调 read_deck`）——断言非恒真。
- **NOT_RUN**：真宿主内的实际点击（「打开文件」弹框、brief→edit 的视觉切换）；`<input type=file>` 在 sandbox 子框架里能否真正打开 = **UNKNOWN**。



```
$ python3 tools/build_ext_apps_bundle.py --check
OK bundle sha256=11c6afa706d0bbaaecbceff343cb43bcddbd97bc656d9c13bb92d907fda2e198 bytes=254632
exit=0
```

### 2.4.1 复现方式（给复审者）

```bash
# 只跑轨 A 端到端（~10s，自带宿主模拟器与临时工作区）
python3 tests/harness/aa_mcp_apps_check.py

# 只跑轨 A 的协议层断言（双模工具面 / 资源契约 / 工具层自校验）
python3 tests/harness/r_bridge_check.py --group apps

# 手工观察两条沙箱臂的差别（浏览器打开后看 View 状态栏与横幅）
python3 -m http.server -d <含 view.html 与 mcp_apps_host_sim.html 的目录> 8000
#   http://127.0.0.1:8000/mcp_apps_host_sim.html?view=view.html            # 默认=规范沙箱（可编辑）
#   http://127.0.0.1:8000/mcp_apps_host_sim.html?view=view.html&sandbox=host # 非规范沙箱负例（明确报错+指引）
```
（`view.html` 用 `python3 -c "import sys;sys.path.insert(0,'tools');from bridge_mcp import build_view_html;open('view.html','w').write(build_view_html())"` 生成。）

### 2.5 完整 e2e 回归

```
$ python3 -u tests/harness/run_e2e.py > docs/progress/_logs/1021_run_e2e_final2.log 2>&1   # 含沙箱决策落地后的重跑
==== 汇总：62 项，61 PASS，1 FAIL ====      # EXIT=1，唯一 FAIL 是既有失败 T34
PASS  T29-bridge 编辑器↔Agent bridge v2（P0–P2） — 7 组全 PASS（含新增 apps 组）
PASS  T36-mcp-apps MCP Apps 轨 A（View 第四态 + 宿主模拟器） — RESULT: ALL PASS (aa_mcp_apps_check)
FAIL  T34-theme-proving ...（既有失败，见下）
```

- **T34-theme-proving 是既有失败**：`1014_brief_dynamic_brainstorming.md` 与 `1015_theme_material_compositing_progress.md` 都记有同一签名（theme-proving deck 缺组 + 存量重叠，与编辑器/bridge 零交集），本轮之前（P1 前）实跑同样是它。**签字口径**：它是主题轨道待办，不是本次回归。
- 基线对照：本轮开始前实跑 **61 项 59 PASS / 2 FAIL**（T34 + 当时正在编辑 SKILL.md 造成的契约断言失败，随后修好复验 PASS）。本轮的 62 项 = 61 + 新增 T36。
- **`s_/u_/v_/z_` 四个检查本轮未跑 = NOT_RUN**，不要当已验。

#### 2.5.1 2026-10-26 v3.9.5 复跑（`docs/progress/_logs/1026_run_e2e_v395.log`）

```
==== 汇总：62 项，58 PASS，4 FAIL ====
PASS  T36-mcp-apps …（RESULT: ALL PASS，含新增 ⑨⑩ 两臂）
PASS  T17-upload-state / T24-bake / T26-tri-view …（与本条改动相邻的三条回归无回退）
FAIL  T29-bridge / T31-brief   ← waiting for locator("#btnBriefGen") 超时（下条解释）
FAIL  T35-dynamic-brief        ← 既有失败：等待 #btnBrief 可点超时（2023 起每次都在这一片）
FAIL  T34-theme-proving        ← 既有失败（主题轨道待办）
```

- **T29/T31 的成因不在本次改动（是前一轮未提交改名的迟发代价）**：`editor.html` 工作树里「预览需求简报」按钮已被改名/合并为 `#btnBriefSend`（`git show HEAD:editor.html` 仍是 `#btnBriefGen`），而 `k_brief_check.py:97/135/145/154`、`r_bridge_check.py:383`、`y_dynamic_brief_check.py:258/388` 仍在点旧 id →「locator 找不到」。本次改动只新增 `#imageInput` 与文件选择/轮询逻辑，**未触碰该按钮的 id 或标记**（`grep -c btnBriefGen editor.html` = 0 是直接证据；基线 `1024_run_e2e_baseline.log` 里 T31/T29 仍 PASS）。修复需一并复核语义——新按钮把"预览"与"发送"合并成一步，在轨 B 点击会**真的提交 intent**，不能只做字符串替换。
- **T35 是既有失败且成因不同**：`1023_run_e2e.log` 与 `1024_run_e2e_*.log` 的失败签名同族（`waiting for locator("#btnBrief")` 超时，只是行号随 SSE 时序落在 238 或 249）。机制：`bridgeApplyEvent` 的 `view-hint` 分支**无条件** `applyLaunch(data.view)`，于是一次 `open_editor(view="brief")` 会把用户刚关掉的脑暴视图重新盖上来，检查里随后的 Escape→点 `#btnBrief` 就被遮住。**是否算缺陷是设计判断**（§6 的意图是"每次 open_editor 的 view 都生效"，加 `launch.applied` 守卫会改变该语义），本次不动，仅记录。
- 上一份基线（改动前工作树）：`_logs/1024_run_e2e_baseline.log` = **62 项 60 PASS / 2 FAIL**（T34 + T35）。

#### 2.5.2 2026-10-29 存量红清理

起因是 v3.11.0 全页文案改名（[1029_ui_copy_plain_language](../progress/1029_ui_copy_plain_language.md)）后做的一次回归清扫，
顺手把长期红一并定性。逐条结论：

| 测试 | 现状 | 说明 |
|---|---|---|
| T31-brief | ✅ **已修（ALL PASS）** | `#btnBriefGen` 已删（生成并入「发送」）；断言改读 `buildBriefExport()`；4 条文案断言随 v3.11.0 同步 |
| T7-annotation | ✅ **已修** | 旧期望"提交后仍提示未导出"与 v3.9.7「批注提交即发送」冲突；改为"无提示 **且** 确实发出了 `pptx-html:annotations`" |
| T32-imagegen-entries | ✅ **已修** | 读取已删除的 `#btnBridgeBake` 抛异常会**截断整轮 E2E**（无汇总行）；删死字段 |
| T29-bridge(ui 组) | ❌ **仍红（已定位）** | 第二层：`#btnBriefRetry`/`#btnBriefStop`/`#btnBriefResume` 于 v3.9.9 随"简报区恢复按钮并入任务面板"删除，该段 5 处仍依赖 → 需按任务面板重写 |
| T35-dynamic-brief | ❌ **仍红（已定位）** | 第一层（Esc 关不掉浮层导致点被拦截）已修；第二层是**应用侧真问题**：服务端已存新 `brief_options`，轨 B 页面**重进 brief 拿不到**（嵌入态注入正常） |
| T34-theme-proving | ❌ **仍红（既有）** | deck 实为 7 主题 × 8 页型 = 56 页（无 g3）、`data-ig` 只在 g1/g2/g4、多处真实重叠 → 属**主题轨道待办**，非测试问题 |

完整分析、证据链与"未做/为何不做"见 [`docs/progress/1029_stale_test_cleanup.md`](../progress/1029_stale_test_cleanup.md)。

**清理后全量复核**：`==== 汇总：62 项，59 PASS，3 FAIL ====`（清理前 **57 PASS / 5 FAIL**）——T7 / T31 / T32 三条转 PASS ✅，剩下 3 条即上表的 T29-ui / T35 / T34。

---

### 2.6 遗留检查补跑（10-21 第二轮，"可以把 1 做了"）

| 检查 | 结果 | 证据 |
|---|---|---|
| `z_sandbox_matrix.py` | ✅ 已重跑（证据工具，无 pass/fail） | `results/z_sandbox_matrix.json`；**本轮新增探针** `nested srcdoc contentDocument`：`null` 源 → `FAIL: contentDocument 为 null（不透明源不可访问）`，真源 → `OK`。§10.10 的结论现在可由本项目自己的仪器复现 |
| `v_bridge_host_check.py --self-check` | ✅ **PASS**（离线，`real model invocations: 0`） | `results/bridge-p4/host-self-check.json`、`_logs/1021_v_selfcheck.log`（`RESULT: PASS`） |
| `u_bridge_stability_check.py --quick` | ✅ **PASS**（脚本自述 reduced development run；**不是** formal 验收） | `_logs/` 与 `results/bridge-p4/report.json`（重新生成） |
| `u_bridge_stability_check.py --formal` | ✅ **PASS（formal 验收级）** | `_logs/1021_u_formal.log` 末行 `EXIT=0`；`results/bridge-p4/report.json`：`mode=formal`、`formal_acceptance=true`、`status=PASS`，26 项检查全 True（PERF-04 await 1s/25s/120s/cancel 的 sample count·P95·max、PERF-05 冷启动 P95≤3s、PERF-06 FD/thread/child 增长与 idle RSS≤20MiB、stop 清理、端口全关、SQLite quick_check 始终 ok、formal profile 未改） |
| `s_bridge_scale_check.py --group integration` | ✅ **PASS**（G7 适用范围裁决后重跑；此前 FAIL 见 §2.6.1） | `_logs/1021_s_integration_after_g7.log`：`PASS integration: real bake-mix/cmb-retail Bridge orchestration, gates, CAS, asset, publication and editable UI`，`EXIT=0`（244s） |
| `s_bridge_scale_check.py --group perf03` | ✅ **PASS** | `_logs/1021_s_perf03.log` `EXIT=0`；`results/bridge-p4/perf03.json`：bake-mix N=50 p50=392ms/P95=645ms/max=721ms（阈值 2000ms）；cmb-retail N=30 p50=3780ms/P95=4802ms（阈值 5000ms） |
| `s_bridge_scale_check.py --group convert` | ✅ **PASS** | `_logs/1021_s_convert.log` `EXIT=0`；`results/bridge-p4/convert.json`：54 页完整双轨导出，耗时 588.7s，**夹具 sha256 前后一致**（未动真实 deck） |
| `s_bridge_scale_check.py --group cns08` | ✅ **PASS** | `_logs/1021_s_cns08.log` `EXIT=0`；`results/bridge-p4/cns08.json`：10× 素材（88 文件/41.8MB → 预计 881 文件/418.5MB bundle）、required=5 completed=5、preflight 5/5 accepted、无 blocker、**夹具 sha256 前后一致** |
| `v_bridge_host_check.py --host kimi\|codex` | ⏳ **NOT_RUN**（真实模型调用会产生费用，需用户显式授权） | — |

#### 2.6.0 宿主行为复读（2026-10-22，`SproutHarness/.claude/worktrees/feature+mcp-apps`）

> 交接纪律要求"改动宿主相关代码前重读宿主源码"。本轮复读结论（含当日未提交改动 `webui.html` 07:43 / `graph.py` 07:57 / `result_utils.py` / `gateway.py`）：

| 宿主事实 | 现状 | 对本项目的影响 |
|---|---|---|
| iframe 沙箱 | `webui.html:2138` `iframe.sandbox = MCP_APP_RUNTIME.iframeSandbox`（**已配置化**）；View 经**同源** `/mcp-sandbox/{id}` + CSP 头加载 | 默认形态下 View 仍是不透明源 → 取不到嵌套 deck 文档 → 轨 A 报错不可编辑（见下行的开关） |
| 沙箱开关（新） | `mcp.apps.allow_same_origin`（`server.py:555-605`）：`false`（**仓库默认**）→ `allow-scripts`；`true` → `allow-scripts allow-same-origin`（`defaults.py:129-130`，docstring 说明该模式"让 MCP Apps 加载工作区资源"）。仓库 `apps/*/config_*.yaml` 均未开启 | **条件已可满足**：部署侧开启后 View 有真实源 → 轨 A 可编辑（`?sandbox=trusted` 臂即此形态，全功能 PASS） |
| 工具结果载荷（二次复读：提交 `6e87ef5` 已落地） | `mcp_result_to_view_payload` 传完整 `CallToolResult`；`webui.html` 保留 string 兼容分支 | 门面两头兼容已就位（优先 `structuredContent`+拆 `{result:"<json>"}` 包装，回落文本） |
| 是否计划加 `allow-same-origin` | **否**（设计文档 805/835/910："不加 allow-same-origin，防止访问父页面 DOM"）；`isolation` 仍是其 §10.7 未做缺口，§12.1 排为后续"D 隔离与身份" | 出路改为：**官方独立 sandbox origin**（推荐）或为该 iframe 放开 `allow-same-origin`；编辑器提示已按两条改写 |
| 工具结果载荷 | **正在改**（1022 文档 P0-1）：新增 `mcp_result_to_view_payload`，View 将收到**完整 `CallToolResult`**（`structuredContent`/`isError`/`_meta.viewUUID`）；`webui.html` 保留 string 兼容分支 | 本项目门面已**两头兼容**：优先 `structuredContent`（拆 FastMCP 的 `{result:"<json>"}` 包装），回落 `content` 文本；`isError` 时两处找 `error.{code,message,details}` |
| `visibility` 读取（原 N15） | **已修**：`mcp/client.py` 现为"`_meta.ui.visibility`（标准路径）优先，根级 `_meta.visibility` 作为向后兼容回落" | 本项目"根级 + `ui` 双写"仍是最稳写法（两路径一致）；`apps` 组的双写断言继续有效 |
| 运行时常量 | `MCP_APP_RUNTIME` 固定：`maxIframeHeight=1200`、`teardownTimeoutMs=5000`、`downloadMaxBytes=20971520`(20MB)、`messageMaxChars=4000`、`contextMaxChars=8000`、`logMaxChars=2000`、`handshakeTimeoutMs=10000`、`allowedPermissions=[camera,microphone,geolocation,clipboardWrite]` | 与 10-20 记录一致，设计 §5.6/§5.7/§5.9 的约束继续成立 |
| View 自请求拆卸 | `onrequestteardown: unsupported-notification`（丢弃） | 我们只应答宿主发起的 `ui/resource-teardown`，不依赖该通知 |

**本轮据复读所做的改动**：① `tools/ext_apps_facade.js` 载荷双兼容（+ 重建 bundle）；② `editor.html` 沙箱提示改写为宿主的两条实际出路；③ **13:25 复读后**——轨 A 下不设产物基址（避免相对路径打到宿主源）、对比/导出视图失联文案去掉在轨 A 下不成立的"file:// 直开"归因；④ 宿主模拟器两臂与宿主配置对齐（`trusted` / `host`），T36 两臂相应改名。

**复验**：`aa_mcp_apps_check.py`（两臂）`RESULT: ALL PASS`、`r_bridge_check --group apps --group integration` PASS、`build_ext_apps_bundle.py --check` OK、**完整 e2e `62 项 61 PASS`（唯一 FAIL 仍是既有 T34）**——`_logs/1022_run_e2e_after_host_reread.log`，T16/T29/T36 均 PASS；13:25 调整后复跑 `aa_mcp_apps_check.py`（两臂）ALL PASS、`r_bridge_check --group apps --group ui` PASS。

#### 2.6.1 `s_ integration` FAIL 的分类与证据链（**既有失败，不是回归**）

失败点：脚本内 `check(run.returncode == 0, "real images gate failed")`，即 `node check-images.mjs <cmb-retail 的 attempt 副本>` 返回 1。

1. **直接复现**（不经 bridge、不经本次任何改动）：
   `node skills/html-pptx/scripts/check-images.mjs tests/decks/cmb-retail/index.html` → **exit 1**，
   12 处"页内槽位素材分辨率不足"（固有 58×58、64×64、66×66、136×127、523×148、542×1174、591×1281 …，下限 640px）。
   对照臂：同一门禁跑 `theme-proving` → exit 0。
2. **时间线**：夹具 `tests/decks/cmb-retail/index.html` mtime **09-29**（本轮未动）；G7 硬门禁所在
   `skills/html-pptx/scripts/check-images.mjs` mtime **10-06 19:11**；`s_bridge_scale_check.py` **10-06 20:18**；
   而该检查的历史 PASS 记录在 `docs/test_acceptance/editor-agent-bridge.md` §16.1，日期是 **2026-10-04**。
   → **门禁加严晚于那条 PASS**；此后该检查再未被跑过（1014/1015 只跑 r/core/e2e），所以失配一直没有暴露。
3. **性质判断：门禁适用范围问题，不是夹具"该修"的缺陷。** 这些图位都是 `data-image-state="uploaded"`
   （真实素材），而技能明确要求 pptx 转换时"图片原样落盘，不重画、不压缩"；G7 的理由（与烙入 Canvas 节 /
   adapter `--expected-size` 对齐）指向的是**生成侧**槽位。把用户真实素材放大到 640px 才算通过，等于伪造来源。
4. **裁决与修复（2026-10-21，用户批准）**：G7 对 `data-image-state="uploaded"` 的图位**降级为告警**，
   只对 placeholder/generated 保持硬错误。决策与影响面见 `docs/design/g7-resolution-floor-scope.md`；
   实施面：`check-images.mjs` 按 state 分流、`editing-contract.md` §2b 措辞 + 契约 v8.2、
   `T16` 新增双向断言（uploaded → 告警且 rc=0；generated → 仍报错）、`AGENTS.md` 同步。
   实测：`cmb-retail` 由 exit 1 → **exit 0（12 条 uploaded 告警可见）**、`bake-mix` 仍零告警、
   `--mode illustration` 仍 rc=1。**`s_ --group integration` 的重跑结论见 §2.6 表格更新。**

---

## 2.7 合规审计后的最小修复（2026-10-22，A1 / A2 / A4）

审计对象：官方 `@modelcontextprotocol/ext-apps` **2.0.3** + 稳定规范 `specification/2026-01-26/apps.mdx`。审计全文、方法（含对 `tools/edit.py --mcp` 的真实 stdio JSON-RPC 探测）与逐项结论见 `docs/progress/1022_mcp_apps_compliance_review.md`；设计侧同步见 `docs/design/mcp-apps-upgrade.md` §10.11。

| 修复 | 断言 | 结果 |
|---|---|---|
| **A1** 门面剥掉 SDK 的 `Error executing tool <name>: ` 前缀后再解析（否则 `err.code`/`details` 全丢） | 从 View 调 `read_asset{path:"etc/passwd"}` → `err.code == "INVALID_ARGUMENT"` 且消息不含前缀 | PASS |
| **A2** `hostViewportMaxHeight()` 实读 `hostContext.containerDimensions`；握手后去重上报期望高度 | 宿主 `sizes` 里出现 `height == 1200`（宿主 maxHeight） | PASS |
| **A4** `@font-face` 与 CSS `url(assets\|fonts/…)` 经 `read_asset` 水合成 data: URI | deck 的 `@font-face.src` 含 `data:`；保存产物仍为 `url("fonts/harness.woff2")` 且无 `data:font` | PASS |

**变异测试（防止"断言恰好通过"）**——把修复逐条注掉后重跑，确认断言会响：

| 变异 | 结果 |
|---|---|
| `errorDetail()` 还原为修复前的整段 `JSON.parse` | FAIL `带前缀的 ToolError 未还原出 error.code: {'code': None, ...}` |
| 注掉 `mcpAppSizeWatch();` | FAIL `未按宿主 maxHeight 上报高度: [{'width':1280,'height':4556}]` |
| 注掉 `mcpAppHydrateCss();` | FAIL（等超时）`deck 的 @font-face 被水合成 data: URI` |

**两条对旧结论的更正（勿沿用）**：
1. View 的 `ui/notifications/size-changed` **一直在发**——官方 `App({autoResize:true})`（默认）在 `connect()` 里按文档尺寸自动上报（变异实测：宿主收到 `height=4556`）。缺的是编辑器侧的**期望高度**控制。
2. CSS 水合**不需要**反向还原：CSSOM 的改动**不回写** `<style>` 文本（Chromium 实测 `textContent`/`outerHTML` 不变；文本是源码），故 `serializeClean` 无 CSS 还原步骤（与 `<img>` 的 `data-pptx-src` 情形不同）。原先写下的 `mcpAppRestoreCssUrls()` 已作为死代码删除。

**回归**（命令与产物）：

```bash
python3 tools/build_ext_apps_bundle.py --check         # OK sha256=9228ba76… bytes=257252 view_version=3.9.1
python3 tests/harness/aa_mcp_apps_check.py             # RESULT: ALL PASS（两臂，含新增三条断言）
python3 tests/harness/r_bridge_check.py --group apps --group ui   # PASS apps + PASS ui
python3 tests/harness/run_e2e.py                       # 亦可用 pytest 基线：44 passed
```

完整 e2e 结论（`docs/progress/_logs/1022_run_e2e_compliance_fix_rerun.log`）：末行 **`==== 汇总：62 项，61 PASS，1 FAIL ====`（EXIT=1）**，唯一 FAIL 是**既有失败 T34-theme-proving**（与本次改动零交集）；**T36-mcp-apps 与 T29-bridge 均 PASS**。首跑因后台 600s 上限被掐断（`…_fix.log`，45 PASS / 0 FAIL / 无 EXIT 行），**不算一次回归**，故重跑并以其末行为准。

---

## 3. 本轮发现的产品缺陷（已修，附现象）

| # | 现象 | 根因 | 处置 |
|---|---|---|---|
| 1 | 轨 A 保存/意图/换图全部 401 | app-only 工具带 management 凭证，但这些路由只认 browser 凭证 | 路由改为"management 或 browser"（与 `/api/save` 既有做法一致），session 归属由工具层自校验 |
| 2 | `save_draft` 400 | dispatch 层把 `annotations` 误当字符串校验 | 改为数组校验 |
| 3 | 轨 A 初始化总报失败 | `get_status` 不在 dispatcher 路由表里（它是面向模型的五工具之一） | harness 侧补模型工具路由映射；产品侧无需改（宿主会把 `tools/call` 原样转发） |
| 4 | 门面回调在"引导期注册"时丢失 | 引导占位脚本的 `onToolResult/onTeardown` 是空函数，未落存 | 改为落存 `api.__toolResult/__teardown`，由 connect 前装好的包装函数转发 |
| 5 | 握手后注册 teardown 处理器抛错 | SDK 不允许握手完成后注册一次性事件处理器 | 门面改为**恰好一次、connect 前**注册包装函数 |
| 6 | 轨 A 载入 deck 后卡住不渲染 | 嵌套文档不可访问时 `frame.onload` 内异常使 `onReady` 永不触发 | 装载后检测 `doc()` 为空 → 如实降级提示（不静默） |
| 7 | 轨 A 控制台报 `export/manifest.json` CORS 失败 | 轨 A 无不透明源可 fetch 的基址 | 已知：对比质检产物载入在轨 A 不可用（设计 §5.11 允许的降级），**未实现修复** |
| 8 | 轨 A 工具失败时 `err.code` / `details` 丢失、toast 带 SDK 前缀 | MCP Python SDK 把任何工具异常包成 `Error executing tool <name>: <消息>`，且该分支无 `structuredContent`；门面只做整段 `JSON.parse` | §2.7 的 A1：门面剥前缀（+ 宽松 JSON 提取）后解析 |
| 9 | 轨 A 下 deck 的 `@font-face` / CSS `url(assets\|fonts/…)` 全部 404（字体静默回落） | 水合只覆盖 `<img src>`；srcdoc 相对 URL 无可用基址 | §2.7 的 A4：`mcpAppHydrateCss()` 经 `read_asset` 换 data: URI（无需反向还原） |
| 10 | 工作台拿不到设计假定的容器高度（`hostViewportMaxHeight()` 恒 null，`reportSize` 无调用点） | 适配层留了钩子未接线；SDK autoResize 只按文档尺寸上报 | §2.7 的 A2：读 `hostContext.containerDimensions` 并去重上报期望高度 |

---

## 4. 未验证 / 未实现（如实清单）

**NOT_RUN**：P4 真实宿主端到端（SproutHarness 分支未合并、Claude Desktop 无法实测）；Office 365 / WPS 目检；`v_bridge_host_check.py --host kimi|codex`（真实模型调用需用户授权费用）。
**已补跑（§2.6）**：`z_sandbox_matrix.py`（含新增嵌套文档探针）、`v_ --self-check` PASS、`u_ --quick` 与 **`--formal`** PASS、`s_` 的 **integration / perf03 / convert / cns08 四组全 PASS**（integration 起初 FAIL，已定性为既有 G7 适用范围问题并经用户裁决修复）。

**未实现（设计 §10.9）**：批注批次分组 UI 与"新 revision 重解锚点"、对比质检按可见页懒加载（轨 A 暂视为轨 B 独有）、能力自动发现（官方 Python 客户端无法声明 `extensions`，现靠 `PPTX_HTML_APPS_TOOLS`）。（`hostViewport` 真实宿主取值原列于此，**已于 §2.7 / 设计 §10.11 落地**，A3 与 B/C 组按 `1022` §7 留待后续讨论。）

**已知限制**：轨 A 的完整编辑能力**依赖宿主提供规范沙箱**（`allow-scripts allow-same-origin`）——这是宿主的责任，本项目已决定不做降级模式（设计 §10.10 有决策与理由）；`ui/download-file` 20 MB 上限对真实导出产物的余量**仍未实测**；`notifyAgent` 敲门需用户确认的体验**未在真实宿主验证**。
