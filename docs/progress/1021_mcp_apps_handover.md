# 1021 · MCP Apps 接入交接（session handover）

> **日期**：2026-10-21（第二轮，P1/P2/P3 实施后）
> **状态**：**P0.5 + P1 + P2 + P3 已实施并有实测证据**；P4（真实宿主端到端）**NOT_RUN**；P5（插件打包）未开始。
> **重启会话阅读顺序**：本文 §0 → §2（当前验证状态）→ §3（必读发现）→ §4（下一步）→ §5（验收标准与判读纪律）；
> 设计细节与**九条实施偏差**见 `docs/design/mcp-apps-upgrade.md`（**唯一权威**，§10 是落地事实）。
> **前一份交接**：`1003_editor_agent_bridge_handover.md`（Bridge v2）。

---

## 0. 30 秒速览

**在做什么**：把「编辑器 ↔ Agent 桥 v2」升级为 **MCP Apps 双轨**——宿主支持 MCP Apps 时编辑器在宿主内 iframe 渲染（轨 A），否则回落到现有独立浏览器页（轨 B）。`BridgeCore` 状态机两轨复用。

**本轮做完的**：
1. **P0.5 D3/D4**（agent/SKILL 侧）：`SKILL.md` §3.1 新增"锚点处理时解析 + 批次合并"。
2. **P1 宿主适配层**：`editor.html` 抽出 `hostBridge.{load,save,asset,intent,status,poll,viewport,background,download,versions,rollback}` 四态策略面，调用点已全部迁移（零行为变化，六组协议验收全绿）。
3. **P2 server 双模**：新增 `tools/bridge_dispatch.py`（app-only 工具 → 路由唯一真相）、`tools/build_ext_apps_bundle.py` + `tools/ext_apps_facade.js` → 产物 `tools/ext_apps_bundle.js`；`tools/bridge_mcp.py` 落 13 个 app-only 工具 + View 资源 + **列举期双模** + **仲裁相位**；`tools/bridge_core.py` 落 `attach_view`/view 信号/三条只读路由/`open_browser="auto"`。
4. **P3 View 第四态**：`editor.html` 的 `mcpApp*` 全部落地（附着/载入/保存/换图/意图/草稿/便条/轮询/下载/版本回滚/teardown/图片懒加载）。
5. **新验收**：`r_bridge_check.py --group apps`（协议层）+ `tests/harness/aa_mcp_apps_check.py`（View 端到端，自带宿主模拟器 `mcp_apps_host_sim.html`，已注册为 **T36**）。

**下一步最重要的一件事**：§3 的沙箱发现需要**用户决策**（轨 A 的完整编辑能力依赖宿主用规范沙箱）。

---

## 1. 本轮产出物清单

| 文件 | 状态 | 说明 |
|---|---|---|
| `docs/design/mcp-apps-upgrade.md` | 已更新（718+ 行） | 新增文首修订记录（10-21 轮）与 **§10 实施偏差记录（10.1–10.10）**——**冲突时以 §10 为准** |
| `tools/bridge_dispatch.py` | **新增** | app-only 工具的唯一路由/校验表（不依赖 MCP 包，可单测） |
| `tools/bridge_mcp.py` | 大改 | 13 个 app-only 工具 + `ui://pptx-html-bridge/editor.html` 资源 + 列举期双模 + `_arbitrate_view` + `mode_hint` |
| `tools/bridge_core.py` | 改 | `attach_view`/`view_attached`/`ui_signal_ever`/`track_of`/`read_document`/`read_artifact`/`read_export_file`、`open_browser="auto"` + 存在性窗口、4 条新路由、浏览器路由接受 management 凭证 |
| `tools/build_ext_apps_bundle.py` + `tools/ext_apps_facade.js` + `tools/ext_apps_bundle.js` + `tools/ext_apps_bundle.json` | **新增** | View bundle 构建（官方 SDK + 本项目门面，254 KB，带 sha256 manifest；`--check` 校验产物是否最新） |
| `editor.html` | 大改 | 宿主适配层 `hostBridge` + 轨 A `mcpApp*` 实现 + 序列化还原 `data-pptx-src` |
| `skills/html-pptx/SKILL.md` | 改 | §3.1（D3/D4）+ `open_browser="auto"` + `kind="mcp_app"` 处置 + app-only 对模型不可见的说明 |
| `tests/harness/mcp_apps_host_sim.html` | **新增** | 宿主模拟器（两臂沙箱：`?sandbox=spec|host`，默认注入宿主默认 CSP） |
| `tests/harness/aa_mcp_apps_check.py` | **新增** | T36 端到端验收（真 editor.html + 真 daemon + 模拟宿主） |
| `tests/harness/r_bridge_check.py` | 改（仅加法） | 新增 `--group apps`（默认跑）：双模工具面/资源契约/轨 A 全链路/工具层自校验；另把 SKILL 契约里 `open_browser=true` 的字面量同步为 `"auto"` |
| `tests/harness/run_e2e.py` | 改（仅加法） | 新增 **T36-mcp-apps** |

---

## 2. 当前验证状态（严格区分已证/未证）

| 项 | 状态 | 证据 |
|---|---|---|
| 核心单测 `test_bridge_core.py` | ✅ **44 passed, 44 subtests** | 本轮实跑（**零改动**通过 = BridgeCore 语义未被 P1/P2 破坏） |
| 协议验收 `r_bridge_check.py` | ✅ **7 组全 PASS**（transport / sdk / **apps** / http·security / ui / integration / fault） | 本轮实跑；除既有 6 组外新增 apps 组；对既有组**只改了 1 行 SKILL 契约字面量** |
| View 端到端 `aa_mcp_apps_check.py`（T36） | ✅ **两臂 ALL PASS**（规范沙箱臂全功能；`allow-scripts` 臂如实降级） | 本轮连跑两次一致 |
| 完整 `run_e2e.py` | ✅ **62 项 61 PASS / 1 FAIL**（`EXIT=1`，唯一 FAIL = 既有失败 T34） | 最新一次：`docs/progress/_logs/1022_run_e2e_after_host_reread.log`（宿主复读适配后；G7 裁决后为 `1021_run_e2e_final3.log`；更早两次同结论）——`1021_run_e2e_final2.log` 末行 `==== 汇总：62 项，61 PASS，1 FAIL ====`（沙箱决策落地后重跑；`1021_run_e2e_final.log` 为同功能等价版本的首跑，结论一致）；新增的 **T36-mcp-apps PASS**，T29-bridge（含新增 apps 组）PASS |
| `editor.html` Bridge 提交路径（轨 B，真浏览器） | ✅ 覆盖到了 | `r_bridge_check --group ui` 用真 daemon + Playwright 跑通 |
| P4 真实宿主（SproutHarness / Claude Desktop） | ⏳ **NOT_RUN** | 分支未合并 / 本机无法实测 |
| Office 365 / WPS 目检 | ⏳ **NOT_RUN** | 人工项 |
| 遗留检查补跑（10-21 第二轮） | 见 §2.1 | `z_` 重跑（+新增嵌套文档探针）／`v_ --self-check` **PASS**／`u_ --quick` **PASS**／**`u_ --formal` PASS（formal_acceptance=true，26 项全 True）**；`s_` 四组：integration 先 FAIL（G7 适用范围）→ **用户裁决修复后 PASS**，perf03 / convert / cns08 **均 PASS**；仅 `v_ --host` **NOT_RUN**（需授权付费调用） |

**基线对照**：本轮开始前（P1 之前）实跑 `run_e2e.py` = **61 项 59 PASS / 2 FAIL**，其中 T29 是当时**正在编辑 SKILL.md** 造成的契约断言失败（随后修好并单独复验 PASS），T34-theme-proving 是 **1014/1015 就记录的既有失败**（主题 deck 与 T34 断言漂移，与本工作零交集）。**T34 仍是既有失败，不要当回归。**

---

## 3. 轨 A 的宿主前提（**已决策：按官方规范开发，不做降级**）

【实测】宿主 iframe 若只有 `sandbox="allow-scripts"`（不透明源），View **拿不到嵌套 deck 文档的 `contentDocument`**——deck 能显示但不能编辑；换成规范要求的 `allow-scripts allow-same-origin` 则一切正常。设计 §1.2 原来"既有 srcdoc 架构可原样保留"的推断只在规范沙箱下成立（已更正，见设计 §10.10）。

**决策（2026-10-21，用户）**：**按官方版本开发，不为不合规宿主做只读降级**。

**2026-10-22 复读宿主源码（worktree 有当日未提交改动）后的更正**：
- 宿主仍是 `webui.html:2138` 硬编码 `sandbox='allow-scripts'` + 同源 `/mcp-sandbox/` 路由，且**明确不加 `allow-same-origin`**（见其设计文档 805/835/910）；其自评 §10.7 仍把 `isolation` 列为未做缺口、§12.1 排为后续"D 隔离与身份"。
- 所以**宿主的计划是官方独立 sandbox origin**（另一个源，天然有真实源且仍隔离），而非给同源沙箱放开 `allow-same-origin`。
- **准确条件**：轨 A 编辑能力要求"View 跑在有真实源的容器"——① 独立 sandbox origin（宿主计划）或 ② 为该 iframe 放开 `allow-same-origin`；**当前两条都不满足**。
- **13:25 再次复读（新提交 `6e87ef5`）：宿主已把沙箱配置化**——`mcp.apps.allow_same_origin`（默认 false）→ `allow-scripts`；true → `allow-scripts allow-same-origin`（`defaults.py:129-130` / `server.py:555-605`）。仓库配置尚未开启，但**开关已在**；部署侧开启后轨 A 即可编辑。本项目据此做了两处小调整（轨 A 不设产物基址以免打到宿主源；对比视图失联文案去掉在轨 A 下不成立的 file:// 归因）并把验收矩阵两臂与宿主配置对齐。
- 同时发现：**N15 已被宿主修复**（`ui.visibility` 标准路径优先、根级回落）；宿主正在把工具结果改为传**完整 `CallToolResult`**（1022 文档 P0-1）——本项目门面已做**两头兼容**（优先 `structuredContent`、回落文本；拆 FastMCP 的 `{result:"<json>"}` 包装）。

因此：

- 编辑器在不合规宿主上**明确报错 + 给处置指引**（状态栏"宿主沙箱不符合规范"、横幅与宿主日志写明需要 `allow-scripts allow-same-origin`、提示可暂用轨 B 独立窗口），**不提供"只能查看"这种降级模式**；
- 原候选的"Shadow DOM 内联""注入编辑代理"两条重构**不实施**；
- **宿主侧改造在宿主仓库**（SproutHarness 的 iframe sandbox 加 `allow-same-origin`），不是本项目的待办；
- 负例臂（模拟器 `?sandbox=host`）已把"必须报错并给指引、不得出现降级措辞"固化成断言。

---

## 4. 下一步 TODO（按优先级）

### T1：推动/等待宿主提供规范沙箱（**宿主侧工作，不在本项目**）
决策已定（§3）：按官方规范开发、不做降级。本项目侧无待办；在小结/交付说明里**如实写明**："轨 A 的完整编辑能力依赖宿主 iframe 使用 `sandbox=\"allow-scripts allow-same-origin\"`；不合规宿主上编辑器会明确报错并给指引。"SproutHarness 支持后再做 P4。

### T2（决策后）：若选 ①，则把"规范沙箱"写进宿主接入要求与文档；若选 ②/③，走设计评审
`docs/design/` 下新增设计文档 → 评审 → 实施。涉及 `doc()` 的调用点清单可用 `grep -n "doc()" editor.html` 起手。

### T3：P4 真实宿主端到端（当前阻塞在宿主侧）
- SproutHarness 分支合并后在真宿主里跑：脑暴 → 生成 → 发布 → 编辑 → 异步批注 → 再生成；
- 必须实测的两条：`ui/message` 敲门是否需要用户点确认、`ui/download-file` 对导出产物的 20 MB 余量（设计 §5.9 未验证项）；
- 证据入 `docs/test_acceptance/`；**未跑项一律记 NOT_RUN**。

### T4：遗留检查补跑的收尾（10-21 第二轮；integration/formal 已补，余 4 项）
✅ 已完成：`z_sandbox_matrix`（重跑 + 新增探针）、`v_ --self-check`（PASS）、`u_ --quick`（PASS）、
**`u_ --formal`（PASS，formal_acceptance=true，26 项检查全 True）**、**`s_` 四组 integration/perf03/convert/cns08 全 PASS**
（integration 起初因 G7 适用范围 FAIL，用户裁决后修复并重跑通过；perf03 P95 645ms/4802ms 达标、convert 54 页 588.7s、cns08 10× 5/5 轮）。
已完成：`z_sandbox_matrix.py`（重跑 + 新增 `nested srcdoc contentDocument` 探针）、`v_bridge_host_check.py --self-check`（PASS）、`u_bridge_stability_check.py --quick`（PASS）。
待做：
```bash
python3 tests/harness/u_bridge_stability_check.py --formal    # 运行中，结果见 _logs/1021_u_formal.log
python3 tests/harness/s_bridge_scale_check.py --group perf03  # perf03 历史 PASS（P95 有数）
python3 tests/harness/s_bridge_scale_check.py --group cns08   # 预计同因被 images 门禁挡（同 cmb-retail）
python3 tests/harness/s_bridge_scale_check.py --group convert # 历史 PASS（~500s）
python3 tests/harness/v_bridge_host_check.py --host kimi      # ⚠️ 真实模型调用，需用户授权费用
```
⚠️ **`s_ --group integration` 的失败要先裁决**：它 100% 可复现于"夹具 cmb-retail 的 12 张 `uploaded` 小图 vs G7 硬下限 640px"，与 bridge/编辑器无关（详见 `docs/test_acceptance/mcp-apps-upgrade.md` §2.6.1）。建议先做那条**门禁适用范围**裁决（uploaded 素材豁免/降级），否则 cns08 也会被同一处挡住。

### T5：P5 插件打包（正交，可延后）

### T6：P3 未实现清单（设计 §10.9 逐条记着，勿当已做）
批注批次分组 UI（§5.10.4）、对比质检产物按可见页懒加载（§5.11，轨 A 暂视为轨 B 独有）、`hostViewport` 真实宿主取值（仍是钩子）、能力自动发现（官方 Python 客户端无法声明 `extensions`，目前靠 `PPTX_HTML_APPS_TOOLS`）。

---

## 5. 如何验收 / 判读纪律

### 5.1 命令

```bash
python3 -m pytest tests/harness/test_bridge_core.py -q          # ~16s，基线 44 passed
python3 tests/harness/r_bridge_check.py                          # ~30s，7 组全 PASS
python3 tests/harness/aa_mcp_apps_check.py                       # ~10s，RESULT: ALL PASS
python3 tools/build_ext_apps_bundle.py --check                   # bundle 是否与源+门面一致
python3 tests/harness/run_e2e.py > docs/progress/_logs/$(date +%m%d)_run_e2e.log 2>&1; echo "EXIT=$?" >> $_
```

### 5.2 判读纪律（项目红线，不得违反）

- **不得把 BLOCKED / UNKNOWN / NOT_RUN 写成 PASS**。当前 P4 与 Office/WPS 目检是 **NOT_RUN**；`s_`/`v_`/`u_` 三个检查本轮 **NOT_RUN**。
- e2e 的 T34-theme-proving 是**既有失败**（1014/1015 起），除它之外任何 FAIL 都要当回归处理。
- 跑分与验收证据**只写 `docs/progress/` 与 `docs/test_acceptance/`**，不进 `AGENTS.md`。
- **测试只操作临时工作区**；不要为验证改写仓库里的真实 deck。
- 长回归必须**落盘**（后台进程随应用退出会失联，本文件上一版就踩过）。
- 任何"上轮读到的宿主行为"都可能过期——**改宿主相关代码前重读宿主源码**。

### 5.3 本轮新增/变更的对外契约（agent 侧要知道）

- `open_editor(..., open_browser="auto")`：`"auto"` 在**声明了 MCP Apps 扩展（或 `PPTX_HTML_APPS_TOOLS=always`）**的客户端上起存在性窗口（默认 8s），否则解析为 `true` 立即开浏览器（返回值带 `open_browser_resolved`）。
- `await_intent` 可能返回 `kind="mcp_app"`（视图已嵌入宿主）：**不要阻塞**，结束本回合；兜底用 `await_intent(timeout_sec=1)`。
- 工具面双模：默认客户端仍看到**恰好五个**工具；`PPTX_HTML_APPS_TOOLS=auto|always|never` 控制 13 个 app-only 工具是否列举。
- `get_status` 顶层新增 `track` / `view_attached` / `ui_signal_ever`；`capabilities` 结构**未变**。
