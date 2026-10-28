# 1027 · MCP 工具面精简：18 → 14（删三个孤儿意图工具 + 合并两个读工具）

> **日期**：2026-10-27
> **触发**：用户提问「请全面审视当前 pptx-html 的工具，为何需要这么多的工具？」——一次对 tool surface 的全面体检，结论是 18 个里**有 3 个从未被任何调用方使用**，另有 2 个打的是同一个 daemon handler。
> **改动**：`tools/bridge_dispatch.py`、`tools/bridge_mcp.py`、`editor.html`（轨 A 撤恢复按钮 + 读工具改名）、`tests/harness/r_bridge_check.py`、`tests/harness/aa_mcp_apps_check.py`；app-only 工具 **13 → 9**，工具面 **18 → 14**。
> **证据纪律**：本轮结论全部来自静态代码与 daemon 契约核对 + 本机 harness 实测（工具列表计数）。真宿主内的人工点击（撤按钮后的观感、轨 A 下载）仍是 **NOT_RUN**，见 §5。

---

## 1. 先澄清「18 个」是什么

工具面由两部分构成，**模型能看到的仍然是 5 个**：

| 层 | 数量 | 工具 | 可见性 |
|---|---|---|---|
| 面向模型 | 5 | `open_editor` `await_intent` `push_update` `get_status` `close_session` | `visibility:["model","app"]` |
| app-only | 13 | 其余全部 | `_meta.ui.visibility:["app"]` |

「18」是**注册数**，不是模型可见数。链路（本机 harness 实测）：

1. 服务端注册 18 个（`tools/bridge_mcp.py:448-580`）；
2. `tools/list` 按客户端能力分流——未声明 `io.modelcontextprotocol/ui` 时**只列 5 个**（`bridge_mcp.py:318-335`）；
3. SproutHarness **不声明**该扩展，所以用 `PPTX_HTML_APPS_TOOLS=always` 打开工具面（`bridge_mcp.py:269` 点名就是给它用的；harness 侧 `config_work.yaml:60`）→ 列 18 个，**但这是给 View 的代理通道用的**；
4. harness 再按 `_meta.ui.visibility` 过滤：不含 `"model"` 的工具 `bind_to_llm=False`，**不进 LLM 工具表**（`…/src/sprout_harness/agent/tools.py:120-124,138-143`）。

⚠️ 因此 `[assemble_tools] MCP tools registered: [...18...]` 这条日志是**注册数**，读它容易误判模型被塞了 18 个工具。

### 1.1 那 13 个为什么会有 13 个

不是 13 个功能，是**一条传输通道的补齐**。轨 A 的 View 在 iframe 沙箱里丢了三条标准浏览器通道，每个原本免费的能力都必须显式变成一个工具：

| 沙箱缺什么 | 逼出来的工具 | 依据 |
|---|---|---|
| 无同源 fetch（CORS `Origin: null`） | `read_deck` `read_asset` `read_export` `save_deck` `write_asset` | `editor.html:4056-4057`、设计 §2.4 |
| 无 localStorage/IndexedDB/cookie | `save_draft`（唯一草稿通道） | `editor.html:4429` |
| 无 SSE（7 类事件） | 轮询替代（复用面向模型的 `get_status`） | 设计 §2.4 |

设计文档对这一层的表述是**路线对齐**而非裁剪：这 13 个「等价于轨 B 的浏览器 HTTP 端点」（`docs/design/mcp-apps-upgrade.md:356`），实现就是「把 `BridgeHandler._api()` 的路由表映射成 MCP 工具函数」（同文 `:322`）。daemon 28 条路由 → 18 个工具，**故意**漏掉的 9 条恰好是最危险/结构上不可能的（`/api/convert`、`/api/imagegen`、`/api/bridge/stop`、`/api/bridge/bootstrap`、`/api/events` 等）。所以它也不是「全量 1:1」。

---

## 2. 体检发现

### 2.1 三个工具全仓没有任何调用方（孤儿）

`cancel_intent` / `retry_intent` / `query_intents` 在 `editor.html`、`tools/ext_apps_facade.js`、`tools/ext_apps_bundle.js` 里**零调用点**；唯一的使用者是服务端测试直接调 daemon 路由（`tests/harness/r_bridge_check.py:902-907`、`test_bridge_core.py` 走 `self.core.*`，不经工具层）。

而它们本该服务的 UI 确实存在——任务面板的「取消 / 停止处理 / 续用原副本 / 从当前版本重建」（`editor.html:8536-8540`），但那些按钮调的是 `bridgeCancelIntent` / `bridgeStopIntent` / `bridgeRetryIntent` → `bridgeFetch('/api/intent/cancel'|'/api/intent/retry')`（`editor.html:8663,8667,8672`），走的是**轨 B 的 HTTP 通道**：需要 `bridge.token`，而该凭证只由 `bridgeParseLaunch()` 在轨 B 设置（`editor.html:8289,8298`，轨 A 不经过它）。

⇒ 轨 A 里那几个按钮**必然失败**（`Authorization: Bearer undefined` 或沙箱内 fetch 不可达），而同一能力的 app-only 工具从没接上线。**现状是两头都不占**：工具是死的，按钮是坏的。

### 2.2 `read_asset` 与 `read_export` 是同一个 handler 的两个 kind

`read_asset` → `POST /api/bridge/asset-read` → `read_artifact(kind="asset")`（`bridge_core.py:1039`）；
`read_export` → `POST /api/bridge/export-read` → `read_export_file`（`:1065`，5 行 shim：拼上 deck 目录 +`export/`）→ `read_artifact(kind="export")`。

两者上限（`ARTIFACT_READ_MAX`）、回包形状（base64 + mime + sha256）、登记表白名单机制（`bundle_files`）完全一致，差别**只有**路径前缀与接受的 class 集合（`:1047-1057`）。这是工具面里唯一一组合并后**不改变语义**的。

### 2.3 薄厚分层：8 个是零逻辑转发

| 层 | 工具 |
|---|---|
| 零逻辑转发（仅附 `consumer_id` + JSON 字符串化） | `get_status` `attach_view` `read_export` `cancel_intent` `list_versions` `rollback` `save_deck` `write_asset` |
| 薄校验 | `read_asset` `query_intents` `retry_intent` `save_draft` |
| 有真逻辑 | `open_editor`（`auto` 解析 + 结果富化）、`await_intent`（轨道仲裁）、`submit_intent`（`client_ts` + 前置校验）、`push_update`（证据 dump）、`close_session`（归属簿记） |

其中 `get_status` 被模型与 View 的 2 秒轮询**共用**（`editor.html:4394`）——说明设计做过复用，不是无脑加。

### 2.4 不该合并的（评估后否决）

- `save_deck` / `write_asset` / `rollback` 同属 CAS 发布族（`_write_key` + `_write_replay` + `_publish`，`bridge_core.py:1419-1460`），但校验（HTML 文本 vs 图片签名 vs snapshot 回灌）、事件（`assets-changed`）、`allow_git_init` 各不相同——合并会把共享校验的爆炸半径放大到三条写入路径上，**为一个工具数优势承担发布路径风险，不对称**。
- `read_deck` 与资产族只是外表像：它是文本 + revision + 仅限 target 的硬守卫（`:1030-1031`），不是 base64 产物。
- 通用 `bridge_request(method, path, body)` passthrough：能把 9 个压成 1-2 个，但 (a) 等于把 daemon **全部**路由（含 convert/imagegen/stop）的写权限交给沙箱；(b) 丢掉逐工具的 `readOnlyHint`/`destructiveHint`——宿主据此决定要不要弹确认，折叠成一个不透明调用等于放弃同意语义；(c) `visibility` 无法只对「一部分路由」声明 app-only。**不做**。

### 2.5 文档缺口

全 `docs/` 树检索确认：**从未讨论过通用 passthrough 这条路**，也**没有把这 13 个做过分级或给过合并计划**。最接近的一条是设计文档自己的风险 #11：「轨 A 工具数从 5 增至 18，**需用户明确签字**」（`mcp-apps-upgrade.md:618`）——也就是说这个数字本来就被记成「需要一个用户决策」。本轮的体检与精简正是补上这一步。

---

## 3. 决策（2026-10-27 用户签字）

1. **删除** `cancel_intent` / `retry_intent` / `query_intents` 三个工具，并**撤掉轨 A 的任务恢复按钮**（轨 B 按钮保留——那里通道是通的，功能正常）。
   - daemon 侧 `/api/intent/cancel`、`/api/intent/retry`、`/api/intents/query` **三条路由原样保留**，轨 B 的浏览器与 `bridgeRecoverIntents` 继续使用；本次只收工具面。
   - 轨 A 里「停止处理」的替代路径仍在：模型侧 `close_session`（会中断未完成 attempt 并释放 lease）。
2. **合并** `read_asset` + `read_export` → **`read_bundle_file`**：入参统一为**bundle 相对路径**（`assets/…`、`fonts/…`、`export/…`），分发层按前缀路由到原有两条 daemon 路由（`export/` 前缀剥掉后走 `export-read`）。daemon 契约与安全白名单一字未动。
3. **不做**：上节 §2.4 的三项。
4. 结果：**app-only 13 → 9，工具面 18 → 14**。

---

## 4. 改动清单

| 文件 | 改动 |
|---|---|
| `tools/bridge_dispatch.py` | `OPERATIONS` 删 3 条、`read_asset`+`read_export` 合为 `read_bundle_file`（新增 `export_path` 键 + 前缀路由 + 三条前缀校验）；删 `query_intents`/`retry_intent` 的字段校验分支 |
| `tools/bridge_mcp.py` | `_register_app_only_tools` 删 3 个工具、读工具合并为 `read_bundle_file`；`TOOL_TITLES` 同步；docstring/注释计数 13→9 |
| `editor.html` | ① 轨 A 撤任务恢复按钮——`bridgeRenderTasks()` 与 `briefRenderSubmission()` **两处**按轨判定（后者是复核时抓到的**活缺陷**：轨 A 提交失败后 `status='failed'` 会让「重新构建」真的露出来）；② 3 处调用点 `read_asset`/`read_export` → `read_bundle_file`；③ 10 处注释同步；④ 版本 v3.9.5 → **v3.9.6** + 变更记录 |
| `tools/ext_apps_bundle.js` / `tools/ext_apps_bundle.json` | 版本号内嵌在 bundle 里，改版本必须重建（`--check` OK） |
| `tests/harness/r_bridge_check.py` | 删 `query_intents`/`cancel_intent` 工具层用例；`read_asset` → `read_bundle_file`（3 处）；**新增** `export/nope.json` → `NOT_FOUND`、`etc/passwd` → `INVALID_ARGUMENT` 两条前缀路由断言；3 处陈旧计数 18 → 14 |
| `tests/harness/aa_mcp_apps_check.py` | 越权用例工具名同步（2 处） |
| `AGENTS.md` | 红线第 1 条计数 18/13 → 14/9 + 指向本文 |
| `docs/design/mcp-apps-upgrade.md` | §4.3 工具清单（13 → 9 + 改名说明）、§8 风险 #11、§9 #1、§10.3 计数、**新增 §10.13** 本轮记录 |
| `docs/test_acceptance/mcp-apps-upgrade.md` | `--group apps` 断言计数 18→14 / 13→9、轨 A 链路工具名、View HTML 尺寸实测更新 |
| `skills/html-pptx/SKILL.md` | ① 工具面计数 18/13 → 14/9；② **删掉 D4「工具面提供 `cancel_intent` 时」那条分支**（该工具是 app-only、对模型从来不可见，这条指令从来没有可执行过——见 §6） |
| `docs/progress/README.md` | 本文入索引 |

---

## 5. 验证（2026-10-27，全部在改动后重跑）

| 检查 | 命令 | 结果 |
|---|---|---|
| daemon 核心回归（证明**保留**的三条路由未受影响） | `python3 -m pytest tests/harness/test_bridge_core.py -q` | **44 passed / 44 subtests passed** |
| 工具面双模（独立探针，真 stdio 起 server） | 临时脚本：`PPTX_HTML_APPS_TOOLS=always`｜`auto` 各起一次 `<repo>/tools/edit.py <tmp> --mcp` 后 `tools/list` | `always` → **14 个**（其中 `_meta.ui.visibility:["app"]` **9 个**、每个都有 title）；`auto` → **恰好 5 个**；被删的 5 个名字（`cancel_intent`/`retry_intent`/`query_intents`/`read_asset`/`read_export`）均不再出现 → **PASS** |
| dispatch 路由与守卫（直调 `build_request`） | `read_bundle_file` × `export/`、`assets/`、`fonts/`；负例 `etc/passwd`、裸 `export/`、`assets/../x` | `export/…` → `POST /api/bridge/export-read {"file":…}`；`assets`/`fonts` → `asset-read` 原样；`etc/passwd` → `INVALID_ARGUMENT`；裸 `export/` → `INVALID_ARGUMENT`；`assets/../x` 交由 daemon 的 `normalize_rel`/`_bundle_rel` 拒（与改动前同一行为，未放宽） |
| bridge 回归（除 `ui` 组） | `r_bridge_check.py --group transport sdk apps http fault security integration` | **全 PASS**（apps 组含新增的两条前缀断言） |
| View 端到端（真宿主模拟器 + 真 daemon + `build_view_html()` 真产物） | `python3 tests/harness/aa_mcp_apps_check.py` | **ALL PASS**——覆盖改名后的 `read_bundle_file` 资产水合与越权探测 |
| bundle 一致性 | `python3 tools/build_ext_apps_bundle.py --check` | **OK**（sha256 与 manifest 一致，`view_version` = 3.9.6） |
| View 资源尺寸 | `build_view_html()` | **739 KB**（上限 2 MB） |

**未通过 / 未跑（如实记）**

- `r_bridge_check` **全量**（不带 `--group`）在 **`ui` 组失败**：`Page.click: Timeout 30000ms … waiting for locator("#btnBriefGen")`。这是**既有红、与本轮无关**：`btnBriefGen` 在 `editor.html`（HEAD 与工作树）里出现 **0** 次、在 harness 里出现 1 次（`r_bridge_check.py:383` 仍点旧 id），且 `docs/progress/1026_open_file_track_and_first_deck.md:96` 已把它记为「前一轮改名未同步 harness 定位器」；本轮未触碰该按钮。
- **真宿主人工项仍 NOT_RUN**：轨 A 内撤按钮后的观感、轨 A 的产物下载（`read_bundle_file` 的 `export/` 分支）。本机可覆盖的是工具列表、daemon 契约与 View 端到端（模拟宿主）。
- **本机运行中的 8100 服务仍用旧技能副本**：`/storage/skills/html-pptx` 是启动时复制的快照，本轮 `SKILL.md` 的改动要重启（`run_local.py` 默认会重拷技能）后才生效。

⚠️ **并发现象（非本轮改动，需用户确认）**：工作树里 `editor.html` 的 `convertDeck()` 在本次会话期间被**另一个并发会话**（`~/.kimi-code/sessions/wd_pptx-html-design_af53b0b73151/…`，cwd 即本 repo）改写成按 `hostKindDetect()` 分流（轨 A 走 `mcpAppSubmitIntent`）。该改写**不是本轮授权范围、不是本轮子 Agent 所为、也不是我改的**（子 Agent 的汇报与其记录里都没有它；我只改了 `bridgeRenderSubmission()` 那处按轨判定）。本轮全部验证是在该改写**已在树上**的状态下跑的。其归属与去留见 §6。

---

## 6. 遗留

- **`convertDeck()` 的并发改写（见 §5 ⚠️）**：需用户确认是本方另一个会话的意图改动（保留）还是需要回退。它看起来像一处**真实修复**（轨 A 里 `state.embedded` 为真 → 旧代码把转换请求 `postMessage` 给不监听它的宿主 → 按钮"无反应"），但未经本轮评审，也**未验证**。
- **D4 批次合并指令已失效（本轮新发现）**：`SKILL.md` 原有一条「工具面提供 `cancel_intent` 时…」的合并流程，但 `cancel_intent` 是 app-only、**对模型从来不可见**（harness 按 `_meta.ui.visibility` 过滤 → `bind_to_llm=False`），所以这条对模型**从来没有可执行过**。本轮把该分支改写为「批次合并当前不可用 + 一律串行」。若要真正恢复合并能力，需要一条**对模型可见**的取消通道（新增工具或改 `visibility`），属工具面扩张，须另行签字。
- **真宿主人工项 NOT_RUN**：见 §5。
- **`read_export` 的轨 A 归宿**：它的下载入口在轨 A 本就落在设计声明「无产物通道」的降级路径上（`editor.html:4878`、`:7600`，设计 §5.11）——若确认该路径在轨 A 不再提供，`read_bundle_file` 的 `export/` 分支（连同 `/api/bridge/export-read`）可再收一层，工具面可到 13。
- **线协议（sandbox-proxy / 独立 origin）**：轨 A 至今要求 `allow-same-origin`（`mcp.apps.allow_same_origin`），这是设计 §10.10/§11.13 的既有缺口，与本轮无关。
