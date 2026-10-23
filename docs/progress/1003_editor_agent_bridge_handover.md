# 编辑器↔Agent Bridge v2：完整交接文档

> 日期：2026-10-04
>
> 交接状态（2026-10-04）：P0–P3 已完成；durable-processing 增量及最终竞态补丁已落地并通过 core 34/34 与定向回归。既有 P4 的默认 r、integration、PERF-03、CNS-08、54页双轨 convert、formal PERF-04/05/06 与 direct `o_tri_view` 已 PASS；最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**。前一轮 856.417秒与更早 948.520秒仅作为历史保留；这些代码回归结果不改变 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN 或人工项 NOT_RUN。Kimi 2.1.1 最新正式重跑为15模型进程、62工具调用、724.483s；核心功能与 cleanup 均通过，两个 scenario stop HTTP 200、端口关闭且无残留，但 observation-07 在工具调用完成后宿主180s未退出，被 TERM（returncode 143），故整体 FAIL、formal=false。安装后自然入口与桌面浏览器 heartbeat 单例已 PASS，但不覆盖该 formal FAIL。Codex 因未登录 BLOCKED；真实生图整体 UNKNOWN；Office/WPS、完整桌面交互、图像观感及硬件掉电 NOT_RUN。
>
> 下一会话唯一入口：先阅读本文，再按“第 10 节：下一步执行计划”继续。
>
> Git 状态：本轮未执行 `git add`、`git commit` 或 `git push`；暂存区为空。

## 1. 本次工作的原始目标

本次工作的目标不是简单地给编辑器增加几个 MCP 按钮，而是将现有纯静态 `editor.html` 与开发侧 AI coding agent 连接成一个可恢复、可审计、不会静默覆盖用户内容的协作闭环：

```text
用户明确提交意图
→ Bridge 持久接收
→ Agent 可靠认领
→ Agent 只修改独立 attempt 工作副本
→ 执行真实技能验收
→ 带 revision CAS 和 validation 证据发布
→ 编辑器在保护用户草稿的前提下刷新
→ 用户继续修改或提交下一轮意图
```

必须同时支持两个入口：

1. **从零创作**：没有 HTML 文件时打开脑暴页，用户冻结需求简报并明确发送，Agent 生成首版 HTML，原会话首次加载作品。
2. **已有作品优化**：打开已有 HTML，用户保存文字/图片修改，或提交主题、批注、插画、整页烙入、导出等请求，Agent 完成后页面安全刷新。

本次还要求：

- 从第一性原理审核原 MCP 化设计，而不是直接照旧方案编码。
- 形成完整优化后的总体设计、公共协议、一致性/恢复设计、执行计划和测试验收计划。
- 文档审核通过后再进入开发。
- 转换能力继续属于 `skills/html-pptx/`，不得迁入 daemon。
- 保持编辑器纯静态、无框架、无构建步骤；无 Bridge 时继续支持 FSAA、下载和宿主 `postMessage`。
- 自动化测试只操作临时工作区，不改写真实 deck，不污染用户 Git HEAD 或暂存区。

## 2. 第一性原理结论与冻结边界

### 2.1 请求、事实和草稿必须分离

- 保存 HTML、替换资产和回滚是已经发生的 **A 类事实**，走 revision CAS 和持久 receipt，不唤醒模型。
- 需求简报、设计修改、批注、插画、烙入和导出是需要 Agent 执行的 **B 类请求**，走 UUID、服务 seq、attempt、lease、validation 和显式 complete/fail。
- 浏览器 DOM、未发送批注、脑暴表单和设计表单是用户草稿，不能因为远端发布成功就自动清空。

### 2.2 持久接收不等于执行完成

系统分别回答三个问题：

1. 请求是否已经可靠接收。
2. 哪个 consumer 正在处理哪个 attempt。
3. 候选结果是否仍基于当前正式 revision，能否安全发布。

不能再用一个页面游标或 `after_seq` 隐式表达三种确认。

### 2.3 Agent 不能直接改正式文件

Agent 只能修改：

```text
.pptx-html/jobs/<intent_id>/attempt-<N>/work/<relative-deck>
```

正式目标只允许由 Bridge 在验证通过后发布。retry 的 `rebuild|resume` 都创建新的 attempt 编号并 fence 旧 attempt；`rebuild` 使用新隔离路径，`resume` 仅在原副本完整、正式 base 未变化、无未完成 publication 且确认无 writer 后复用旧 `work_path`。旧副本保留，不自动删除。

### 2.4 SQLite 是状态真相

- session、consumer、client、intent、attempt、retry receipt、write receipt、event、draft、snapshot、publication 都以 SQLite/WAL 为状态真相。
- 文件系统 journal、snapshot、bundle manifest 和 Git 专用 ref 用于保护发布和恢复。
- 浏览器 IndexedDB 只保护本地草稿，不能替代服务端状态。

### 2.5 不承诺无法保证的 exactly-once

Bridge 可以保证自身持久状态、发布和 receipt 的幂等重放，但不能保证外部模型调用或付费生图 API 恰好执行一次。waiting owner 仍在90秒 lease 后回收；processing owner 不因 lease 时钟自动过期，lease 只作 telemetry。同 owner 的迟到 heartbeat/progress/complete/fail 仍有效，第二 consumer 得到 `SESSION_BUSY`。processing 仅由 complete/fail、原 consumer close、网页显式 stop、daemon restart 或真实发布/CAS错误结束；stop/cancel 转 `interrupted` 并返回 `external_work_may_continue:true`。只有用户明确 retry 才创建下一 attempt，并提示可能重复外部费用。

### 2.6 转换仍是技能

Bridge 的 `--convert` 和 `/api/convert` 只是在 attempt 工作副本内触发：

```bash
python3 skills/html-pptx/scripts/export-pptx.py <work_path> --force --track both
```

导出算法、字体处理、渲染门禁、PPTX 组装和交付规则仍全部位于 `skills/html-pptx/`。`formats` 只影响用户下载选择，不能减少完整双轨重建和验收范围。

## 3. 已完成的设计文档

以下文档已经完成并经过两轮独立交叉审核：

| 文档 | 作用 | 状态 |
|---|---|---|
| `docs/design/editor-agent-bridge.md` | 总体问题、第一性原理、用户流程、总体架构和取舍 | 已完成 |
| `docs/design/editor-agent-bridge-protocol.md` | 五个 MCP 工具、HTTP 路由、SSE、身份、状态机、错误和重试公共契约 | 已完成 |
| `docs/design/editor-agent-bridge-consistency.md` | revision、bundle、Git、CAS、journal、草稿、鉴权、路径与恢复算法 | 已完成 |
| `docs/progress/1002_editor_agent_bridge_plan.md` | P0–P4 实施计划、文件分工、出口条件和实际执行记录 | 已完成并记录当前结果 |
| `docs/test_acceptance/editor-agent-bridge.md` | 四层证据、测试矩阵、故障、性能、人工验收和实际结果 | 已完成并记录当前结果 |
| `docs/howto/editor-agent-bridge.md` | 安装、手动模式、MCP 模式、五工具循环、错误处理和安全说明 | 已完成 |
| `docs/design/README.md` | 设计文档索引 | 已同步 |
| `docs/progress/README.md` | 进度文档索引 | 已同步 |
| `AGENTS.md` | 当前专项状态、架构和测试边界 | 已同步 |

设计审核期间解决的关键问题：

1. 无 deck 脑暴到首次生成和首次加载的完整状态流。
2. consumer 首次注册、await acquire、close 后必须重新 open。
3. UUID、服务 seq、attempt 和 retry receipt，移除隐式确认。
4. attempt 独立副本路径和 retry 不复用旧副本。
5. validation 的精确 schema 和必需 checks。
6. bundle revision、CAS、journal、snapshot 和 Git 专用 ref。
7. 手动 `--deck` / `--new` bootstrap 和非 Git 首存确认。
8. Bridge 导出固定完整 `--track both`。
9. 持久 intent query，不依赖 SSE 永久保存。
10. 路由级 payload 限额。
11. `resource_path` 明确作为同源静态 URL 的相对路径。
12. MCP 可选 `export_source_revision` 缺省时不发送非法 `null`。
13. 正常 stop 先回收活动 HTTP/SSE 线程，再关闭 SQLite。

## 4. 已完成的生产实现

### 4.1 `tools/bridge_core.py`

已实现标准库 Bridge 核心，主要能力包括：

- SQLite schema、WAL、迁移和未来 schema 拒绝。
- 每个规范 workdir 单 daemon 和 `flock` 互斥。
- `serve.json` 发现文件、instance 身份、management/browser/bootstrap 凭证。
- session、consumer、client、intent、attempt、retry/write receipt、event、draft、snapshot、publication。
- source revision、export revision 和完整 bundle revision。
- intent 接收、认领、waiting lease、持久 processing owner、重投递、stop/interrupted、retry `rebuild|resume` 和持久 query。
- attempt 工作副本创建、rebuild 隔离、resume 安全复用与旧 attempt fence。
- A 类 save、asset、rollback 的 CAS 和 receipt。
- Git 专用 `refs/pptx-html/...` 与隔离 `GIT_INDEX_FILE`，不移动用户 HEAD，不修改真实暂存区。
- publication journal、故障注入、旧状态恢复、DB committed 后修复、第三种字节冻结。
- `dir_fd`、`O_NOFOLLOW`、路径规范化、符号链接和危险硬链接拒绝。
- SVG 主动内容检查和未知受管扩展拒绝。
- convert claim 时清除继承的旧 export，防止旧轨混入新结果。
- 23 个公开协议路由、内部 stop 路由和 7 类 SSE 事件。
- Host、Origin、Bearer、body 大小和静态资源隔离。
- `revision <work_path>` 内部只读 CLI。
- 正常 shutdown 的活动 socket 断开、请求线程回收和数据库关闭顺序。

### 4.2 `tools/bridge_mcp.py`

已使用官方 MCP SDK 1.28.x 实现 stdio 薄代理，恰好暴露五个工具：

1. `open_editor`
2. `await_intent`
3. `push_update`
4. `get_status`
5. `close_session`

代理负责：

- 启动或附着 daemon。
- 保存 management token，不向浏览器暴露。
- consumer heartbeat。
- 将协议错误映射为 MCP 工具错误。
- 大 payload 返回摘要和绝对 `intent_file`。
- validation 精确序列化。

官方依赖限定为：

```text
mcp>=1.28,<2
```

daemon 和手动编辑模式仍只依赖 Python 标准库。

### 4.3 `tools/edit.py` 与 `tools/start-webui.sh`

`tools/edit.py` 已重构为 Bridge v2 统一入口：

```text
--deck REL
--new [REL]
--mcp
--stop
--convert
--no-browser
--port
```

`tools/start-webui.sh` 已透传手动目标参数并显式附加 `--convert`。转换逻辑仍不在服务内。

### 4.4 `editor.html` v3.5

已完成：

- SSE生命周期反馈：服务端30秒计划内干净EOF静默续接；网络/协议异常才显示退避重连；401/403停止循环并提示经MCP `open_editor`或手动bootstrap获取新凭证。

- durable-processing 操作：processing 显示“停止处理”，停止后转 interrupted 并提示外部工作可能继续；interrupted 提供“续用原副本”与“从当前版本重建”，分别映射 retry `resume|rebuild`。
- brief 主结果按 processing → recoverable → pending → succeeded/cancelled 优先恢复，并显示其他 brief 数量。
- Bridge 状态条和任务 UI。
- URL fragment token 读取后立即清理。
- sessionStorage、client_id 和 browser heartbeat。
- 鉴权 fetch、fetch-SSE 解析、断线重连和 7 类事件消费。
- 持久 intent query、retry 和 cancel。
- 无 deck 脑暴、明确发送和首次生成加载；结果区绑定 brief intent id，持久显示 loading/pending/processing/succeeded/error，消费 HTTP receipt、SSE、query/IndexedDB，提交中禁重复、失败可恢复，三条提交路径文案互不混淆。
- 需求、设计、批注、插画、烙入、导出六类 intent。
- IndexedDB 本地草稿和服务 draft。
- load、manifest、save generation/epoch，防迟到响应覆盖新内容。
- dirty、active edit、表单和 pending 风险保护。
- save、asset、rollback receipt 和 revision CAS。
- export/assets 强制缓存刷新。
- 使用后端 `resource_path` 构造同源静态 URL，不从绝对路径猜 basename。
- 无 Bridge 时保留 FSAA、下载、复制和嵌入 `postMessage`。

### 4.5 `skills/html-pptx/SKILL.md`

已升级为 editor-first Bridge 工作流：普通 PPT/PPTX/slides/deck 请求在恰好五工具可见时，从零创建的首个人机交互直接 `open_editor(..., view='brief', open_browser=true)`，已有 deck 先 open；禁止 AskUserQuestion 或聊天脑暴替代 Step 0.5。只有用户明确拒绝编辑器或实际确认五工具不可用才可观测降级。当前 await 契约为 min/default/max=`1/86400/86400`；首次打开后的当前回合固定且只调用一次 `await_intent(timeout_sec=86400)`，给用户完整一天，允许宿主取消但禁止同回合重复或无限轮询。网页 brief 结果区绑定具体 intent id，持久呈现 loading/pending/processing/succeeded/error，并从 HTTP receipt、SSE、query/IndexedDB 恢复；网页只显示 intent/发布回执，MCP tool result 只返回 Kimi。历史上先后暴露同回合重复120秒、首次120秒约154秒；固定25秒后的 skill-creator iteration-3 三条首次均精确25秒，eval2/3 exit0、eval1 外层90秒 exit124，整体仍非 PASS（13/23 对旧3/23）。这些是历史证据，不被当前一小时契约改写；review 为 `skills/html-pptx-workspace/iteration-3/review.html`。

```text
open_editor
→ await_intent
→ brief.submitted 冻结 Step 0.5（缺项走默认，Step 1/2 不二问）
→ 读取 intent_file
→ 只修改 work_path
→ 执行原技能验收
→ push_update complete/fail
→ 首次打开后的当前回合固定且只 await_intent(timeout_sec=86400) 一次（一天占用可取消）；timeout 后说明页面仍可用并结束回合
→ 只有用户新消息要求继续时，才在新回合重新 await
→ 明确结束时 close_session
```

六类 intent、validation、完整双轨导出、冲突、恢复和 close 纪律保持不变。多页 bake 的代表页先作为独立 intent 完成并释放 lease，用户页面查看后再提交剩余页，不持 lease 等聊天。

MCP 1.28.0 检查器 stdio connect/list 成功并发现恰好5工具；schema descriptions/annotations smoke 仅执行 readOnly 的 `get_status`，返回预期 `SESSION_NOT_FOUND` 工具错误，其余4个非只读工具按策略跳过。安装后不带 `--skills-dir` 的 smoke 自动发现 skill 并调用 `open_editor(open_browser=true)`，但工具返回后75秒内未继续到 await、exit124，只证明安装/工具发现。所有 open 均返回 `page_online=false`：仅能确认自动开浏览器请求已发出并获得 URL，不能确认桌面窗口真实打开，桌面真实开窗保持 NOT_RUN。用户级 config/MCP 注册由父代理完成，文档不得记录凭证。

## 5. 已完成的测试实现

### 5.1 `tests/harness/test_bridge_core.py`

当前有 **34 个 unittest（34/34 PASS）**，除既有状态/安全/恢复覆盖外，还包括严格内联 PNG/JPEG data URI 与外链反例、waiting/processing 分离、迟到同 owner 更新、第二 consumer 排他、processing stop/interrupted、retry `rebuild|resume`、resume 门禁与旧 attempt fence、并发旧 attempt 更新隔离、重复 stop 风险提示、convert telemetry 和 `tracks.*.ok` 契约：

- schema/WAL 和迁移。
- source revision 黄金值。
- open/register/acquire/close/reopen。
- intent UUID 幂等、claim 重投递和 attempt 路径。
- retry receipt、`rebuild|resume` attempt+1、resume 复用门禁与旧 attempt fence。
- complete validation、发布和 receipt 重放。
- complete 响应丢失和重启恢复。
- intent/claim/open/close/retry 响应丢失。
- A 类 save/asset/rollback 响应丢失。
- save CAS、Git index 隔离。
- 外部副作用不自动重演。
- 双 consumer 和双 daemon 排他。
- publication 各故障点恢复。
- DB committed 后旧目标修复。
- 第三方字节冻结。
- 符号链接/硬链接拒绝。
- SVG 主动内容和未知扩展拒绝。
- convert 清除旧 export。
- processing 90秒后不自动过期、同 owner 迟到 heartbeat/progress/complete/fail、第二 consumer `SESSION_BUSY`。
- processing stop/cancel→interrupted 且 `external_work_may_continue:true`。
- `rebuild|resume` 均 attempt+1；resume 仅在完整性/base/publication/无 writer 门禁通过后复用旧 `work_path`。

### 5.2 `tests/harness/r_bridge_check.py`

`skill_contract_check` 已改为验证 editor-first、`open_browser=true`、AskUserQuestion 禁令、显式可观测降级、`brief.submitted` 冻结后 Step 1/2 不二问，以及多页 bake 代表页独立 intent/释放 lease。SDK 组同时核对所有工具参数与 validation evidence 字段 description，以及五工具 `ToolAnnotations` 的真实副作用声明；工具数量、名称和协议参数语义不变。

已实现组：

```text
transport
sdk
http
security
ui
integration
fault
performance
```

无参数默认运行：

```text
transport,sdk,http,ui,fault,integration
```

`security` 与 `http` 共用真实 daemon 入口；`performance` 必须显式选择。

### 5.3 `tests/harness/run_e2e.py`

已接入 `T29-bridge`。T12 已从旧 v1.6 companion 流程迁移为真实手动 daemon + bootstrap/browser bearer 流程，覆盖鉴权、CAS、receipt、draft、snapshot 历史与 Git 专用 ref 隔离；修复历史 UI 消费 `snapshot_id` 后，完整入口 T1–T29 共 55 项全部通过。

## 6. 已执行验证与真实结果

### 6.1 定向回归

| 命令 | 结果 | 耗时 |
|---|---|---:|
| `python3 -m unittest tests.harness.test_bridge_core -v` | 34/34 PASS | durable-processing 增量定向结果；旧26/26报告保留为历史 |
| `python3 tests/harness/r_bridge_check.py --group transport --group sdk --group ui --group integration` | PASS | durable-processing 定向结果 |
| `python3 tests/harness/r_bridge_check.py` | 历史默认六组 PASS，退出码0 | 既有报告保留 |
| `python3 tests/harness/s_bridge_scale_check.py --group integration` | 历史 PASS | 真实4页/54页副本 |
| `python3 tests/harness/s_bridge_scale_check.py --group perf03` | PERF-03 PASS | 50/30样本 |
| `python3 tests/harness/s_bridge_scale_check.py --group cns08` | CNS-08 PASS | 5轮10倍素材 |
| `python3 tests/harness/s_bridge_scale_check.py --group convert` | PASS | 499867.728ms |
| `python3 tests/harness/u_bridge_stability_check.py --formal` | formal PASS | PERF-04/05/06 |
| `python3 tests/harness/o_tri_view_check.py` | ALL PASS | direct回归 |
| `python3 tests/harness/run_e2e.py` | **最终竞态补丁后 55/55 PASS，0 FAIL** | wall time 856.192秒；只代表代码回归；前一轮856.417秒与更早948.520秒仅作历史 |

`r_bridge_check.py` 默认六组不包含 performance；真实宿主结论另由独立 host 报告给出。

静态检查：

```bash
python3 -m py_compile \
  tools/edit.py \
  tools/bridge_core.py \
  tools/bridge_mcp.py \
  tests/harness/r_bridge_check.py \
  tests/harness/test_bridge_core.py \
  tests/harness/run_e2e.py
bash -n tools/start-webui.sh
git diff --check -- editor.html tools skills/html-pptx tests/harness docs AGENTS.md
```

结果：全部通过。

### 6.2 单页协议性能基线

已有忽略目录内报告：

- `tests/harness/results/bridge/metrics.json`
- `tests/harness/results/bridge/report.json`

环境：Linux arm64、Python 3.13.11、MCP SDK 1.28.0、Git 2.20.1、8 CPU。fixture 只有 1 页、456B，因此只能作为协议基线。

| 指标 | 样本 | P50 | P95 | Max | 判定 |
|---|---:|---:|---:|---:|---|
| status | 100 | 1.115ms | 2.624ms | 3.860ms | PASS |
| browser heartbeat | 100 | 2.674ms | 4.396ms | 8.257ms | PASS |
| 小 intent | 200 | 3.811ms | 7.267ms | 11.794ms | PASS |
| 近 1MiB intent | 20 | 20.624ms | 45.130ms | 46.413ms | PASS |
| 25s await | 1 | 25002.970ms | 25002.970ms | 25002.970ms | 有界阈值 PASS，样本不足 |
| 120s await | 1 | 120009.915ms | 120009.915ms | 120009.915ms | 有界阈值 PASS，样本不足 |

资源快照：

```text
RSS 24.867 MiB → 32.949 MiB，增长 8.082 MiB
FD 9 → 9
```

这不是 54 页大 deck、30 分钟稳定性或完整冷启动分布认证。

### 6.3 fixture 恢复与零污染证据

- 完整枚举 25 个标准 deck；恢复前原有 7 个可用，其中 `cmb-retail` 实际存在但被 `.gitignore` 隐藏。
- 18 个缺失目录从可信 Git 删除前统一快照 `dd5d87940f9463a3b60972f0c9b288195a2264d5` 原字节恢复，共 47 个文件；Git blob 核验 missing=0、mismatch=0。
- `cmb-retail` 对删除前 `5fdd8c723e26594e7334080ba2c06cdf5e5733c1` 的 100 个历史受控文件核验 missing=0、mismatch=0。
- 恢复后的全 fixtures 基线为 806 entries / 789020265 bytes；该轮历史回归及后续各 P4 专项均证明前后相同。最终全量比对亦 PASS：baseline/final 均806 entries、789020265 bytes，added/removed/changed 均为空，证据为 `tests/harness/results/bridge-p4/fixtures-compare.json`。

### 6.4 完整历史回归与 T12 修复

首次运行完整 `python3 tests/harness/run_e2e.py`，真实失败于 T12：旧 v1.6 测试无鉴权 POST `/api/save`，与 Bridge v2 的 bootstrap/browser bearer、session/base_revision、专用 ref、snapshot 和 receipt 协议冲突。

T12 迁移后继续检出真实生产消费者 bug：`editor.html` 历史 UI 把可空 Git commit `v.hash` 当稳定身份并调用 `slice()`。现已改为 `snapshot_id || hash`，commit hash 仅作可选显示，rollback 传稳定版本 id，同时保留旧 versions schema 只有 `hash` 时的 fallback。生产鉴权与 revision CAS 未放松。

修复后结果：

```text
python3 tests/harness/run_e2e.py
==== 汇总：55 项，55 PASS，0 FAIL ====
```

耗时约 860 秒，T1–T29 全部通过。该结果证明完整历史 harness 与其现有子测试通过；不得把其中 `cmb-retail` 的 T1/导出子测试冒称 PERF-03 或 CNS-08。完整54页 Bridge convert 已由独立 `s_bridge_scale_check.py --group convert` 真实执行并通过。

## 7. 本轮最后修复的关闭竞态

最终回归曾暴露：活动 SSE 请求线程在 daemon shutdown 后仍可能访问已经关闭的 SQLite，随后尝试向已断连接写错误响应，产生：

```text
sqlite3.ProgrammingError: Cannot operate on a closed database
BrokenPipeError
```

最终修复：

1. `BridgeCore.begin_shutdown()` 先设置 `ready=false` 和 stop event，并唤醒 session conditions。
2. `BridgeHTTPServer` 跟踪活动 request sockets。
3. shutdown 主动断开活动 SSE/keep-alive sockets。
4. `server_close()` 等待所有 request threads 退出。
5. 之后才调用 `core.close()` 关闭 SQLite、workdir lock 和安全目录句柄。
6. SSE 循环显式检查 stop event。

修复后重新运行默认 `r_bridge_check.py`，六组全部 PASS，关闭阶段无 traceback。

## 8. 当前准确状态

| 阶段 | 状态 | 可以声称的结论 | 不能声称的结论 |
|---|---|---|---|
| P0–P3 | 完成 | durable-processing core 34/34、定向 r/sdk/ui/integration、真实 resume 恢复、既有默认 r/规模/受控发布与54页双轨 convert 通过 | 硬件断电、未执行人工项通过 |
| P4 自动/规模 | 部分结果已 PASS | PERF-03、CNS-08、formal PERF-04/05/06、direct `o_tri_view` 通过；最终竞态补丁后完整 `run_e2e` **55/55 PASS、0 FAIL，856.192秒**，前一轮856.417秒与更早948.520秒仅作历史 | 用代码回归替代 Kimi formal、Office/WPS 或其他人工验收 |
| Kimi 2.1.1 | FAIL（宿主退出超时；功能与 cleanup PASS） | 最新重跑15模型进程、62工具调用、724.483s；核心功能 cases 全过，cleanup `ok=true`，两个 scenario stop HTTP 200、端口关闭且无残留 | formal 宿主通过；`observation-07` 在工具完成后180s未退出，被 TERM，returncode 143 |
| Codex 0.150.1 | BLOCKED | 未登录，0调用 | Codex 宿主通过 |
| 真实 GPT-Image | UNKNOWN | 两次 provider exit 0 且尺寸/hash 合规 | Bridge complete 或图像观感通过；图未保留 |

本轮总体结论必须保持：

> P0–P3 与 durable-processing 增量及最终竞态补丁完成；core 34/34、定向回归和真实 resume 恢复已有 PASS，既有 P4 自动、规模和正式性能证据保持。最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**；前一轮856.417秒与更早948.520秒仅作为历史保留。代码回归不改变 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN 或人工项 NOT_RUN。Kimi 最新正式重跑的功能与 cleanup 均 PASS，但 `observation-07` 宿主退出超时令整体 FAIL、formal=false；Codex BLOCKED，真实生图 UNKNOWN，Office/WPS、桌面真实开窗、图像观感和硬件掉电 NOT_RUN，不得宣称 P4 全量完成。

## 9. 当前工作区与版本控制状态

### 9.1 本轮核心 modified/untracked 文件

```text
M  AGENTS.md
M  docs/design/README.md
M  docs/progress/README.md
M  editor.html
M  skills/html-pptx/SKILL.md
M  tests/harness/run_e2e.py
M  tools/edit.py
M  tools/start-webui.sh
?? docs/design/editor-agent-bridge.md
?? docs/design/editor-agent-bridge-protocol.md
?? docs/design/editor-agent-bridge-consistency.md
?? docs/howto/editor-agent-bridge.md
?? docs/progress/1002_editor_agent_bridge_plan.md
?? docs/progress/1003_editor_agent_bridge_handover.md
?? docs/test_acceptance/editor-agent-bridge.md
?? tests/harness/r_bridge_check.py
?? tests/harness/test_bridge_core.py
?? tools/bridge_core.py
?? tools/bridge_mcp.py
```

### 9.2 前期研究文件

以下文件来自本次前期调研或用户已有工作，必须保留，不要在下一会话擅自删除：

```text
M  docs/research/source-survey.md
?? docs/research/agent-webui-bridge.md
?? docs/research/projects/cowart.md
?? docs/research/projects/deepseek-harness.md
```

### 9.3 仓库边界注意事项

当前 Git 顶层可能位于项目目录之上，直接运行不带 pathspec 的 `git status --short` 会列出大量与本项目无关的用户目录变化。下一会话必须使用：

```bash
git status --short -- .
git diff --cached --name-only -- .
git diff --check -- editor.html tools skills/html-pptx tests/harness docs AGENTS.md
```

禁止清理、还原或提交项目目录外的变化。

### 9.4 当前运行态

- 历史首次功能 PASS 运行曾发现 `/tmp/bridge-host-kimi-ynnxbr3q/{no-deck,existing-deck}` 对应的 `edit.py --mcp/--daemon` 残留；验收 Agent 已按精确命令行匹配对 PIDs 14648/14654/5869 发 TERM 并确认清理。该人工动作只恢复当时现场，原 formal PASS 已作废。
- harness cleanup 已修为持有 host process group 与 daemon discovery/PID 身份，在临时目录删除前正常 stop→TERM→KILL 并验证 PID/端口/精确 argv。最新正式重跑已验证 cleanup `ok=true`、两个 scenario stop HTTP 200、端口关闭且无残留；当前失败点改为 `observation-07` 工具完成后宿主退出超时。
- 重跑结束后的 `ps` 已确认当前无 `tools/edit.py`、`bridge_mcp`、Chromium 或 soffice 残留。
- `tools/__pycache__` 和 `tests/harness/__pycache__` 为本地缓存，不作为验收证据。
- 测试性能报告位于 `.gitignore` 忽略目录，不进入提交。
- 暂存区为空。
- 未执行 commit/push。

## 10. 下一步执行计划

自动与规模主线及最终全量 fixture 比对已经执行完毕。下一会话只处理明确剩余项；不得重跑付费生图，除非用户另行授权。

### 10.1 已完成：fixtures、回归、规模与性能

- 25个标准 deck 已恢复；历史 `run_e2e.py` 55/55 与 direct `o_tri_view` 通过。
- integration、PERF-03、CNS-08、54页双轨 convert 与 formal PERF-04/05/06 全部 PASS。原始报告位于 gitignored `tests/harness/results/bridge-p4/`。
- PERF-03：bake50 P95 297.388ms，cmb30 P95 4691.988ms。CNS-08：5轮真实54页×10倍素材，每轮881文件/418460736B。convert：499867.728ms、54张 native 与三件交付物。
- formal 性能：cold N20 P95 188.023ms；await 1s N100 P95 1012.252ms、25s N20 P95 25014.319ms、120s N3 P95 120007.629ms；cancel N100 P95 13.578ms；connections N100 P95 17.603ms，尾20轮 FD/线程/child 增长0；idle 1800.015s RSS+0.004MiB；active stop 266.414ms。
- 最终全量 fixture 比对 PASS：baseline/final 均806 entries、789020265 bytes，added/removed/changed 均为空；证据为 `tests/harness/results/bridge-p4/fixtures-compare.json`。

### 10.2 功能通过/整体失败/阻断：真实宿主

- Kimi Code 2.1.1 最新正式重跑为15个模型进程、62次工具调用、724.483s；核心功能 cases 全过，cleanup `ok=true`，两个 scenario stop HTTP 200、端口关闭且无残留；但 `observation-07` 在 open/await/status/close 均完成后宿主180s未退出，被 TERM，returncode 143，故整体 FAIL、formal=false。usage/cost unknown。历史累计为 trust 失败1次 + 首次功能 PASS 但 cleanup 缺陷8次 + 最新15次 = 24次模型进程。
- cleanup 根因修复已由最新正式重跑验证：stop body 精确为 `cli-stop`；每个 invocation 回收宿主 process group；每个 scenario 缓存 daemon PID/start ticks/discovery，临时目录删除前正常 stop，失败时按精确身份/argv TERM→KILL；本次确认 PID 消失、端口关闭和进程扫描为空。当前待修复的是宿主工具完成后的退出生命周期，不是 cleanup。
- Codex CLI 0.150.1 因 `Not logged in` BLOCKED，0调用；不得自动登录、改用户配置或借用 Kimi 结果。
- harness 继续保持显式运行和隔离纪律：Kimi 临时原子替换并恢复项目 MCP 配置；Codex 使用 ephemeral CLI 覆盖；报告只存脱敏信息。

### 10.3 仍待人工/外部决定

1. PowerPoint 365/WPS 打开、播放、编辑、保存和版式目检。
2. 桌面真实开窗交互。
3. 图像观感。两次真实图因当次 harness bug 未复制出临时目录，当前无法验图；是否新付费调用由用户另行授权。
4. 硬件掉电耐久性。
5. Codex 登录后是否重跑正式宿主验收，由用户决定。

### 10.6 P4-F：Office/WPS 与真实付费生图人工验收

#### Office/WPS 目标

对真实双轨交付件进行人工目检：

- PowerPoint 365 打开、播放、编辑和保存。
- WPS 打开、播放、编辑和保存。
- 字体、行距、CJK/拉丁混排、图表、信息图、烙入页和图片无明显错位。
- 可编辑轨文本仍可编辑。
- 保真轨视觉稳定。
- 不以 LibreOffice 参考渲染替代 Office/WPS 结论。

#### 付费生图目标

只在用户明确授权费用后执行：

- illustration intent 必须已有插画模式授权。
- bake intent 必须明确页码和代表页审批。
- 记录外部调用次数、费用和失败。
- 失败不伪造 `generated`，不自动重复付费调用。
- retry 明确提示可能重复费用。

真实生图已显式执行两次且无自动重试：provider 均 exit 0，并返回插画2048×1536/7077065B/`c78324…fad` 与烙入2560×1440/2353840B/`d4fec6…53a`。但当次 harness ledger 路径判断 bug 使临时目录退出前未复制人工验收图，也未继续 Bridge complete，故整体必须为 **UNKNOWN**、费用 unknown。bug 已修但未再次付费调用；当前没有图可做观感验收，是否重新调用必须由用户另行授权。mock 报告为 PASS。

### 10.7 P4-G：最终文档回扫与交付判定

所有验证完成后：

1. 更新 `docs/progress/1002_editor_agent_bridge_plan.md` 的阶段状态和执行记录。
2. 更新 `docs/test_acceptance/editor-agent-bridge.md` §16，逐项从 BLOCKED/NOT_RUN 转为 PASS 或保留真实阻断。
3. 更新本文的当前状态和剩余任务。
4. 更新 `AGENTS.md` 当前专项。
5. 更新 `docs/howto/editor-agent-bridge.md` 中任何因真实宿主产生的配置差异。
6. 执行提交前文档回扫和修复代码验收。
7. 运行最终静态检查和标准测试。
8. 只有用户明确要求时才执行 `git add`、`git commit` 或 `git push`。

最终“全量完成”的必要条件：

- 定向 Bridge 测试通过。
- 标准 `run_e2e.py` 全通过。
- 真实 fixtures 完整且未被测试污染。
- 真实大 deck 与规模性能通过。
- Kimi/Codex 分别验收。
- Office/WPS 人工验收。
- 付费生图若属于本次交付范围，必须有用户授权和真实记录；若不执行，最终报告必须保留 NOT_RUN。

## 11. 下一会话开始时的必读顺序

下一会话不要从代码猜协议，按以下顺序阅读：

1. `AGENTS.md`
2. `docs/progress/1003_editor_agent_bridge_handover.md`
3. `docs/design/editor-agent-bridge.md`
4. `docs/design/editor-agent-bridge-protocol.md`
5. `docs/design/editor-agent-bridge-consistency.md`
6. `docs/progress/1002_editor_agent_bridge_plan.md`，重点 §11
7. `docs/test_acceptance/editor-agent-bridge.md`，重点 §16
8. `docs/howto/editor-agent-bridge.md`
9. `skills/html-pptx/SKILL.md` 中 Bridge 协作章节

如果开始恢复 fixtures，还应读取：

- `tests/harness/run_e2e.py`
- `tests/harness/o_tri_view_check.py`
- `tests/harness/m_bake_check.py`
- `tests/harness/n_fidelity_check.py`
- `tests/harness/p_editable_check.py`
- `tests/harness/q_capacity_check.py`

## 12. 关键代码入口

| 入口 | 位置 | 说明 |
|---|---|---|
| BridgeCore | `tools/bridge_core.py` | 状态、文件、发布、安全和 HTTP 核心 |
| shutdown 生命周期 | `tools/bridge_core.py` 的 `begin_shutdown`、`BridgeHTTPServer` | 活动请求先退出，SQLite 后关闭 |
| MCP 五工具 | `tools/bridge_mcp.py` | 官方 SDK stdio 薄代理 |
| CLI | `tools/edit.py` | 手动、MCP、daemon、stop、convert 分流 |
| 浏览器 Bridge 运行时 | `editor.html` 的 Bridge v2 区段 | token、heartbeat、SSE、draft、intent、刷新 |
| 技能协作 | `skills/html-pptx/SKILL.md` | Agent 对 intent/work_path/validation 的执行纪律 |
| 核心测试 | `tests/harness/test_bridge_core.py` | 32 个状态、安全、durable-processing 和恢复测试 |
| 综合测试 | `tests/harness/r_bridge_check.py` | transport 到 performance 的分组 harness |
| 规模/性能 | `tests/harness/s_bridge_scale_check.py`、`u_bridge_stability_check.py` | PERF-03、CNS-08、convert、formal PERF-04/05/06 |
| 宿主/生图 | `tests/harness/v_bridge_host_check.py`、`t_imagegen_check.py` | 显式真实调用，默认不产生费用 |
| 全量入口 | `tests/harness/run_e2e.py` | T1–T29 项目标准回归 |

## 13. 不得回退的协议与安全红线

下一会话修改代码时不得破坏以下约束：

1. MCP 工具保持恰好五个，不新增任意 shell 或文件发布工具。
2. Agent 只修改 `work_path`，不直接写正式 deck。
3. complete 必须带真实 validation，不允许仅凭“完成了”发布。
4. source/export revision 分离；旧 export 不得伪装 fresh。
5. Bridge convert 永远完整 `--track both`。
6. page、daemon、consumer 生命周期独立。
7. close 后同 consumer 必须重新 open，heartbeat 不能复活。
8. retry 必须显式确认并创建新 attempt。
9. 用户草稿不能因远端更新被静默清除。
10. management token 不进入浏览器、HTML、日志或示例配置。
11. browser token 只经 fragment 接收、转 sessionStorage、立即清 fragment。
12. SSE 使用 Authorization fetch，不把 token 放 query。
13. 不修改用户 HEAD、真实 Git index 或现有 Git 配置。
14. 路径安全必须继续拒绝穿越、符号链接和危险硬链接。
15. publication 遇第三种字节必须冻结，不覆盖外部修改。
16. stop 必须先回收活动请求线程，再关闭 SQLite。
17. 测试只操作临时工作区和 fixture 副本。
18. 缺 fixture 时诚实 BLOCKED，不伪造绿灯。
19. 转换算法只进技能，不进入 `tools/edit.py` 或 Bridge 核心。
20. 验收结论逐项写 PASS/BLOCKED/UNKNOWN/NOT_RUN；不得用其他绿灯覆盖阻断或未知。
21. 生图 adapter 只接受显式 provider script；provider 路径不硬编码、不写 ledger，外部调用不自动重试。
22. waiting owner 才按90秒 lease 回收；processing lease 只作 telemetry，不得按时钟自动中断。
23. processing 仅由 complete/fail、原 consumer close、网页显式 stop、daemon restart 或真实发布/CAS错误结束；同 owner 迟到更新有效，第二 consumer 必须 `SESSION_BUSY`。
24. processing stop/cancel 必须转 interrupted 并返回 `external_work_may_continue:true`，不得声称外部进程或费用已撤销。
25. retry `rebuild|resume` 均 attempt+1；resume 只有完整性/base/publication/无 writer 门禁全过才复用旧 `work_path`，旧 attempt 始终被 fence。

## 14. 建议的新会话启动提示

重启后可直接向新会话发送：

```text
请先阅读 AGENTS.md 和 docs/progress/1003_editor_agent_bridge_handover.md。Bridge v2 的 core、默认 r、integration、PERF-03、CNS-08、convert、formal PERF-04/05/06、历史回归和最终全量 fixture 比对已有 PASS。Kimi 2.1.1 最新正式重跑的核心功能与 cleanup 均 PASS，但 observation-07 在工具完成后宿主180s未退出，被 TERM（returncode 143），故整体 FAIL、formal=false；不得自动调用模型。另处理该宿主退出问题、Codex 登录阻断与 Office/WPS、桌面开窗、图像观感、硬件掉电。真实生图当前 UNKNOWN，图未保留；未经我另行授权不得重试付费调用。不要 commit/push。
```

## 15. 最终交接结论

当前 Linux Bridge durable-processing 增量及最终竞态补丁已通过 core 34/34、定向 r/sdk/ui/integration 与真实 resume 恢复；既有自动与规模主线报告仍包括默认 r、integration、PERF-03、CNS-08、54页完整双轨 convert、formal PERF-04/05/06、direct `o_tri_view` 和最终全量 fixture 比对 PASS。最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**；前一轮856.417秒与更早948.520秒仅作为历史保留。代码回归不改变 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN 或人工项 NOT_RUN。最终比对报告记录 baseline/final 均806 entries、789020265 bytes，added/removed/changed 均为空。Kimi 最新正式重跑为15个模型进程、62次工具调用、724.483s，核心功能 cases 与 cleanup 均通过；cleanup `ok=true`，两个 scenario stop HTTP 200、端口关闭且无残留。但 `observation-07` 在 open/await/status/close 完成后宿主180s未退出，被 TERM，returncode 143，因此报告为整体 FAIL、formal=false。usage/cost unknown。历史累计为 trust 失败1次 + 首次功能 PASS 但 cleanup 缺陷8次 + 最新15次 = 24次模型进程；首次 cleanup 缺陷保留为历史发现，当前 cleanup 已验证 PASS。Codex 0.150.1 因 `Not logged in` BLOCKED、0调用。

真实 GPT-Image 两次 provider 都 exit 0 并返回严格尺寸/hash，但当次 harness ledger 路径判断 bug 导致图未复制、Bridge complete 未执行，故整体 UNKNOWN、费用 unknown；bug 已修但没有再次付费调用。父代理确认本机 XDG 默认浏览器映射异常后，在用户级 MCP server 环境增加 `BROWSER=/usr/bin/x-www-browser`；随后无 `--skills-dir` 的全新 Kimi smoke 自动加载 `html-pptx`，无 AskUserQuestion，按 `open_editor(deck_path=null, output_path='product-weekly/index.html', view='brief', open_browser=true)` → 首次 `await_intent(timeout_sec=25)` 运行，返回 `page_online=true`，宿主 exit0，总耗时65.6秒。该单例只证明“安装后的自然入口 + 桌面浏览器 heartbeat PASS”，不覆盖 iteration-3 eval1 exit124，也不把 Kimi formal 整体改为 PASS。剩余人工仍包括 Office/WPS、完整桌面交互、图像观感（当前无图，须另行授权新调用）和硬件掉电；P4 总体仍是部分完成。

本次 editor-first / stdio schema 定向更新已运行 `py_compile`、`r_bridge_check.py --group transport --group sdk --group integration`（重复 `--group` 参数）及 `git diff --check`，均 PASS。父代理随后完整执行 `python3 tests/harness/run_e2e.py`，结果 **55/55 PASS**、耗时约878秒；这只代表本轮代码回归 PASS，不改变上述 Kimi formal FAIL、阻断、未知与人工项状态。iteration-3 review 所在 `skills/*-workspace/` 已由 `.gitignore` 排除，不作为提交产物。

其后批准的“brainstorming 一小时等待与提交反馈优化”只更新当时契约和自动测试：core/MCP schema 默认与上限为3600秒，MCP→loopback HTTP 留15秒收尾余量，Kimi 临时 host harness 配置 `toolTimeoutMs=3700000`；自动测试通过立即投递、1秒 timeout 和取消验证边界，不真实 sleep 3600。原 formal 1/25/120 性能样本继续有效但不代表一小时宿主 PASS。`editor.html` 的 brief 状态机与三路文案已按 intent id/receipt/SSE/query/IndexedDB 收敛。该历史轮次的定向验证为 `py_compile` PASS、core 27/27 PASS、r transport/sdk/ui/integration PASS、k_brief PASS、v self-check PASS、u quick PASS；随后完整 `run_e2e.py` **55/55 PASS**、耗时948.520秒。该历史结果不改变 Kimi formal **FAIL**、Codex **BLOCKED**、真实生图 **UNKNOWN** 与人工项 **NOT_RUN**。

## 16. durable-processing 当前实现与真实恢复

当前实现以 waiting 与 processing 分离为准：waiting owner 仍按90秒 lease 回收；processing owner 不因 `lease_until` 自动过期，lease 只作 telemetry。同 owner 迟到 heartbeat/progress/complete/fail 有效，第二 consumer 为 `SESSION_BUSY`。processing 只由 complete/fail、原 consumer close、网页显式 stop、daemon restart 或真实发布/CAS错误结束；网页 stop/cancel 转 interrupted 并返回 `external_work_may_continue:true`。

retry 支持 `rebuild|resume`，两者都令 attempt+1。rebuild 使用新隔离路径；resume 只有在旧副本完整、正式 base 未变化、无未完 publication 且确认无 writer 后才复用原 `work_path`，旧 attempt 始终被 fence。

当前真实恢复记录：session `s_6jXOxN_FpDIdxrTxqtIsu-6S` 的原 intent `d53ad685-7502-4514-806a-782d00beb28a` attempt 1 因**旧实现的 consumer lease expiry**被 interrupted；确认原 `work_path` 稳定后，resume 创建 attempt 2，`reused_work_path=true`，attempt 1 被 fence。seq 2/3 重复 brief 已 cancelled。attempt 2 重新运行 `extract-manifest --write-hashes`（53页）、`j_render_check`（53页 PASS）、`check-capacity`（0违规）、`check-images`（PASS），complete receipt 为 `rcpt_qBdovYOwpczJ4r0uH7vAqipe`，revision 为 `sha256:579e17f41cf52be3522d44d4a1469426b5aed21f67cb8d04befd5c71eb00a8b0`。正式 `test_case1/index.html` 再验 render/capacity/images 均 PASS；session 最终 editing，pending/recoverable=0，`page_online=true`。

最终竞态审查修复后，`push_update(progress|fail)` 的所有权复核与条件写入已收进同一 session lock/SQLite 事务；旧 attempt 与 stop/retry 并发时统一返回 `RECOVERY_REQUIRED`，不会覆盖或释放新 owner。重复 stop 对 interrupted 继续返回 `external_work_may_continue:true`。编辑器 retry API 失败会恢复原 status/error 并 query 校准，不再伪造 interrupted。当前定向结果为 core **34/34 PASS**；r transport/sdk/http/ui/integration/fault 全部 PASS；`k_brief_check.py` ALL PASS；最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**。前一轮 856.417秒及更早 948.520秒记录继续作为历史保留，也不改变 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN 或人工项 NOT_RUN。上述恢复不是 Kimi formal PASS；历史 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN、人工 NOT_RUN 均不变。
