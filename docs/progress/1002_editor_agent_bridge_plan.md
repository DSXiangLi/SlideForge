# 编辑器↔Agent 桥 v2：分阶段执行计划

> 2026-10-04 · 状态：P0–P3 Linux 自动实现已落地；durable-processing 增量及最终竞态补丁已实现。本次 core 34/34、r transport/sdk/http/ui/integration/fault 与 k brief 定向验收均 PASS；最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**。前一轮 856.417秒及更早 948.520秒证据保留为历史，也不改变 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN 或人工项 NOT_RUN。既有 P4 的 PERF-03、CNS-08、54页双轨 convert、formal PERF-04/05/06 证据保持不变。Kimi 2.1.1 最新正式重跑仍因 observation-07 宿主退出超时整体 FAIL、formal=false；Codex BLOCKED；真实生图 UNKNOWN；人工项 NOT_RUN。FAIL/UNKNOWN/BLOCKED 不得推定为 PASS。未提交 Git。
> 规范：[协议与状态机](../design/editor-agent-bridge-protocol.md)（下文简称“协议”）；配套：[一致性与安全](../design/editor-agent-bridge-consistency.md)、[测试验收计划](../test_acceptance/editor-agent-bridge.md)、[外部使用指南](../howto/editor-agent-bridge.md)。协议优先；旧总览的页面 seq / after_seq 隐式确认语义不得沿用。

## 1. 目标、现状与不做什么

`editor.html` v3.5、`tools/edit.py` v2、`tools/bridge_core.py` 与 `tools/bridge_mcp.py` 已形成“页面明确提交 → Agent 可靠认领 → attempt 工作副本验收 → 显式确认发布 → 页面保稿刷新”的 Linux 自动闭环。技能仍负责生成、插画、烙入和转换；bridge 只负责接收、状态、隔离、验收证据核验和发布。

已落地目标：

1. 无 deck 时先脑暴；同一 session 在首次生成发布后加载真实 HTML，不创建伪空文件。
2. 已有 deck 的请求使用 UUID 去重、服务 seq 排序和 attempt 防迟到确认；A 类保存/资产/回滚使用 receipt/CAS。
3. SQLite 是状态真相；副本、journal、快照、Git 专用 ref 与 revision CAS 保护磁盘；浏览器 IndexedDB/服务草稿独立保护输入。
4. 官方 SDK stdio 代理暴露五个 MCP 工具；daemon 保持标准库，手动模式不依赖 `mcp` 包。
5. 自动结果与真实宿主/模型/Office/WPS/付费生图结果分开登记。

不做：页面内模型调用；自写 JSON-RPC/MCP 传输；无限 long poll；任意 shell / 任意发布源工具；daemon 实现转换；多 deck 共用同一受管目录；全局文件系统事务或外部生图恰好一次保证；自动修改用户宿主配置。测试仍只操作临时工作区，不在真实 deck 上做破坏性写入。

## 2. 事实、前置闸门与文件分工

### 2.1 2026-10-04 当前事实与未测项

- 生产实现已存在：`tools/bridge_core.py`、`tools/bridge_mcp.py`、`tools/edit.py` v2、`editor.html` v3.5；`skills/html-pptx/SKILL.md` 已升级为普通 PPT/PPTX/slides/deck 的 editor-first 入口：五工具恰好可见时从零先开 brief、已有 deck 先 open，禁用 AskUserQuestion 替代 Step 0.5，`brief.submitted` 冻结后 Step 1/2 不二问；validation 与受控生图 adapter 纪律不变。2026-10-04 后续批准将 await 常量集中为 min/default/max=`1/3600/3600`，首次打开后的当前回合固定且只调用一次 `await_intent(timeout_sec=3600)`，提供完整一小时且允许用户取消；不得同回合重复或无限轮询。网页结果区现以具体 brief intent id 持久显示 loading/pending/processing/succeeded/error，消费 HTTP receipt、SSE、query 与 IndexedDB，且明确网页 receipt/status 不等于只返回 Kimi 的 MCP tool result。此前先后出现同回合重复120秒、首次120秒约154秒，以及改为25秒后的 iteration-3 结果（3条首次均精确25秒；eval2/3 exit0，eval1 外层90秒 exit124；13/23 对 3/23）均保留为历史证据，不因本次配置更新改写为 PASS；review 仍位于 `skills/html-pptx-workspace/iteration-3/review.html`。
- MCP 1.28.0 检查器已通过 stdio connect/list 并发现恰好5工具；schema descriptions/annotations smoke 中仅执行被识别为 readOnly 的 `get_status`，得到预期 `SESSION_NOT_FOUND` 工具错误，其余4个非只读工具按检查器策略跳过。首个安装后、无 `--skills-dir` smoke 自动发现 skill 并调用 `open_editor(open_browser=true)`，但工具返回后75秒内没有继续到 await，进程 exit124，且 `page_online=false`。父代理确认本机 XDG 默认浏览器映射异常后，仅在用户级 MCP server 环境增加 `BROWSER=/usr/bin/x-www-browser`；随后全新 Kimi smoke 对自然 prompt 自动加载 `html-pptx`，无 AskUserQuestion，调用 `open_editor(deck_path=null, output_path='product-weekly/index.html', view='brief', open_browser=true)`，首次 `await_intent(timeout_sec=25)`，返回 `page_online=true`，宿主 exit0，总耗时65.6秒。该单例可记为“安装后的自然入口 + 桌面浏览器 heartbeat PASS”，但不覆盖 iteration-3 eval1 exit124，也不改变 Kimi formal 整体 FAIL；完整桌面交互仍 NOT_RUN。用户级 config/MCP 由父代理注册，文档不记录凭证。
- 核心 unittest 当前 **34/34 PASS**：除既有 durable-processing 覆盖外，新增 stale telemetry 后 late fail/complete、确定性 stop→resume 与旧 progress/fail/complete 并发交错、重复 stop 风险提示幂等。`push_update(progress|fail)` 的检查与条件写入现位于同一 session lock/事务；UI retry 失败恢复原 status/error 并 query 校准。`r_bridge_check.py --group transport --group sdk --group http --group ui --group integration --group fault` 与 `k_brief_check.py` 本次均 PASS；最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**。此前 `v_bridge_host_check.py --self-check`、`u_bridge_stability_check.py --quick` 以及前一轮 856.417秒和更早 948.520秒的完整回归仅保留为历史证据。
- PERF-03 PASS：`bake-mix` N=50/P95=297.388ms，`cmb-retail` N=30/P95=4691.988ms。CNS-08 PASS：真实54页×10倍素材5轮，每轮881文件/418460736B，门禁、发布、save、rollback、recovery 全部通过。
- 54页完整双轨 convert PASS：499867.728ms、54张 native 页图和三件交付物。formal PERF-04/05/06 PASS，详细分位数见 §11。
- Kimi Code 2.1.1 最新正式重跑整体 **FAIL**、`formal_acceptance=false`：15个模型进程、62次工具调用、724.483s；所有核心功能 cases 与 cleanup 均通过，cleanup `ok=true`，两个 scenario stop HTTP 200、端口关闭且无残留；但 `observation-07` 在 open/await/status/close 均完成后宿主180s未退出，被 TERM，returncode 143。usage/cost 不可见为 unknown。历史累计为 trust 失败1次 + 首次功能 PASS 但 cleanup 缺陷8次 + 最新15次 = 24次模型进程；首次 cleanup 缺陷仅作历史记录，当前 cleanup 已验证 PASS。
- Codex CLI 0.150.1 因 `Not logged in` **BLOCKED**，0调用。真实 GPT-Image 两次 provider exit 0 且尺寸/hash 合规，但当次 harness ledger 路径判断 bug 导致未复制人工验收图、未继续 Bridge complete，整体保持 **UNKNOWN**、费用 unknown；bug 已修但未再次付费调用。
- 各专项报告中的 fixture 前后摘要相同；最终全量 fixture 比对亦 **PASS**：baseline/final 均806 entries、789020265 bytes，added/removed/changed 均为空（`tests/harness/results/bridge-p4/fixtures-compare.json`）。
- 已修正实现回归点包括：只允许严格签名的内联 PNG/JPEG data URI、仍拒绝外链；长 convert progress 仅报告 telemetry，不决定 processing 存活；双轨按 `tracks.*.ok is true` 验收；以及既有 `resource_path`、SSE、stop、revision 与历史 UI 修复。
- 仍未完成：Office/WPS、桌面真实开窗交互、图像观感（图未保留，需用户另行授权新调用）及硬件掉电。

### 2.2 本轮定稿的公共约束

实现者先完整读取[总览](../design/editor-agent-bridge.md)、协议及一致性文档，不在代码/测试里自创字段。本轮已消除接口前置待决项：

1. 工作副本为 `.pptx-html/jobs/<intent_id>/attempt-<N>/work/<relative-deck>`，首次 attempt=1；旧副本永久保留。retry 必须带 retry_id UUID、expected_attempt、`mode='rebuild'|'resume'`、当前 base_revision、confirmed:true；两种模式都令 attempt+1，同 retry_id 同报文重放原 attempt，异报文拒绝。rebuild 使用新隔离路径；resume 仅在旧副本清单完整、正式 base 未变化、无未完 publication 且确认无 writer 时复用原 `work_path`。旧 attempt 始终被 fence，用户须确认外部工作可能继续及重复付费风险。
2. validation=`{candidate_revision,checks,export_source_revision?}`；checks 为非空 `{name,argv:string[],exit_code:int,report_path:string|null}` 列表，仅允许真实 exit_code=0。brief/design/anno/bake/illustrate 必有 render/capacity/images/manifest；convert 必有 export。候选源 revision 使用 `python3 tools/bridge_core.py revision <work_path>` 取得；这是内部只读辅助，不新增 MCP 工具。只有显式 export check 且 export_source_revision 与候选源一致才新设 fresh。
3. heartbeat 的 role 分支、client 首次绑定、A 类 receipt、GET/HEAD 无 Origin 只读例外全部按协议 §7。waiting owner 90秒过期可回收；processing owner 的 lease 仅为 telemetry，不按时钟失效。同 owner 即使 heartbeat/progress 迟到仍可 progress/complete/fail，第二 consumer 始终 `SESSION_BUSY`；旧 attempt 或已由显式终止事件中断的 owner 只能重放持久成功 receipt，不能新写。
4. 控制/intent JSON body 2MiB、intent payload 1MiB；save/draft JSON body 64MiB；asset JSON body 48MiB 且原始图片≤32MiB；保留既有大 HTML 保存能力，限额统一定义且逐路由边界测试。
5. P0只验证SDK transport，不依赖P1；P1完成后跑五工具conformance，真实宿主另测。
6. consumer由管理open登记/刷新且不抢owner，返回consumer_state；await原子acquire registered/paused/expired中仍具登记资格者→waiting，已有他有效owner则SESSION_BUSY。close设置requires_open，同consumer必须重复open同session，不可heartbeat复活。
7. 无MCP手动入口固定为CLI `--deck REL` / `--new [REL]`互斥，默认已有index则打开，否则briefing target=index.html；一次性本机bootstrap兑换browser session。手动非Git打开不失败、git_ready=false；首存用户确认init:true，先init及保护后写。MCP open仍自动init。
8. 桥转换永远`--track both`，formats仅选下载件，不减少重建/验收范围；完整三文件、native页图与manifest双轨成功后才全局fresh，禁单轨发布。
9. 浏览器通过POST /api/intents/query按seq分页或指定intent_id查询持久摘要；status新增recoverable_count但不替代query。SSE resync与新origin恢复必须重查，不能只依赖被清理的旧事件。

### 2.3 实际落点

| 文件/目录 | 已实现责任与边界 |
|---|---|
| `tools/edit.py` | v2 CLI 分流：`--mcp`、`--deck/--new`、`--daemon`、`--stop`、`--convert`；复用 bridge core，不承载转换算法 |
| `tools/bridge_core.py` | SQLite 状态机、目录单 deck、waiting lease/持久 processing owner、revision、attempt fence、`rebuild|resume`、publication journal、恢复、Git 专用 ref、23 个公开协议路由及内部 stop 路由 |
| `tools/bridge_mcp.py` | 官方 MCP SDK stdio 薄代理，恰好五工具；代理持有 management token 并独立心跳 |
| `tools/start-webui.sh` | 透传手动目标参数并附加 `--convert`，仍只触发技能转换 |
| `editor.html` | v3.2 bridge token 绑定、鉴权 fetch、SSE、请求列表/retry/cancel、IndexedDB/服务草稿、CAS 保存/资产/回滚、加载代次和强制产物刷新；历史 UI 以 `snapshot_id` 为稳定回滚标识，旧 schema 回退 `hash` |
| `skills/html-pptx/SKILL.md` | 五工具协作循环、六 intent 映射、work_path 单向写入、真实 validation、恢复与结束纪律 |
| `tests/harness/test_bridge_core.py` | 21 个标准库 unittest，覆盖状态机、安全、幂等、Git 隔离与 publication 恢复 |
| `tests/harness/r_bridge_check.py` | transport/sdk/http/ui/fault/security/integration/performance 选择器；默认组不含 performance |
| `tests/harness/run_e2e.py` | `T29-bridge` 子进程与 T1–T28 全部保留；T12 已迁移为真实手动 daemon + bootstrap/browser bearer/CAS/receipt/snapshot 历史回滚；完整入口 55/55 PASS |
| `docs/howto/editor-agent-bridge.md` | 外部安装、配置、手动启动、五工具循环、安全、恢复和错误指南 |

实现保持单 daemon、单 SQLite 真相、无 Web 框架、无第二套状态存储。转换所有权仍在技能。

## 3. 统一执行纪律

- **先安全基座，后UI开通**：本轮审查通过→P0独立transport→P1核心及五工具conformance→P2；P3文案按已定稿协议准备，端到端验收等P2；P4汇总全链路与人工结果。
- **先失败证据，再通过证据**：每个子阶段先写能抓出相应错误的测试；不能只证明 import、compile 或 schema 输出存在。
- **只改工作副本**：Agent 读取返回的绝对 `intent_file` / `work_path`，生成和导出均指向副本；目标路径只供识别，不作直接写入。
- **不把刷新当确认**：SQL commit 和持久 events 先于 completion receipt；客户端成功应用或记录待处理后才推进游标。
- **不可用要可见**：Git 失败、缺依赖、草稿备份失败、过大载荷、磁盘满、恢复失败均不返回成功外观；用户输入保持可恢复。
- **不自动重演外部副作用**：processing 不因90秒 lease 自动过期；lease 只作 telemetry。只有 complete/fail、原 consumer close、网页显式 stop、daemon restart 或真实发布/CAS错误才能结束 processing；用户明确 retry 才增加 attempt，不以新消费者出现为自动重试依据。
- **保守重试**：只有已定义幂等键的写操作才自动重发；save/asset/rollback 遇响应丢失先查状态/revision，不虚构其拥有 intent UUID 的幂等保证。
- **集中常量**：lease、heartbeat、payload、SSE 留存/退避采用协议值，在核心集中定义并由测试对照；性能阈值另列为验收目标，不能偷改协议以让测试通过。
- **不污染源仓库**：测试在临时工作区和隔离工程副本中运行；真实 fixture 前后做字节摘要对比。测试内 Git 操作仅限自建临时仓库。

## 4. P0：独立 transport 探针，不依赖 P1

P0 只证明官方 SDK 的真实 stdio、取消、并发和有界等待可用；不要求已经存在 daemon、SQLite、认领、发布或五工具实现。探针仅放测试侧，使用独立名称，不让生产 `--mcp` 以临时工具冒充完成。

### P0.1 最小 SDK 探针

1. 在 `r_bridge_check.py --group transport` 的隔离子进程内使用官方 `mcp>=1.28,<2`，注册 `probe_wait(timeout_sec)` 与 `probe_status()`；两者只维护测试内存计数，不读写 deck、不启动业务 daemon。
2. 官方 ClientSession 经真实 stdio initialize → list → call，断言探针这两个工具的 schema、结构化内容、兼容文本和错误封装；**此阶段不要求恰好五个业务工具**。
3. stdout 无协议外日志；非法类型、未知探针工具、EOF、坏输入分别记录，diagnostic 只写 stderr。当前 probe_wait 断言 min/default/max=1/3600/3600，验证0/3601/非整数拒绝；只实等1秒并立即取消3600秒调用，不真实 sleep 一小时。历史1/25/120秒性能样本另行保留。

### P0.2 取消、并发和资源

1. wait 阻塞时并行 status，验证 SDK 调度不串行冻结；可加受控标准库 HTTP 测试服务模拟阻塞 I/O，仅用于测 offload/取消，不依赖真实业务接口。
2. 发送真实 MCP cancellation，确认等待被取消且连接/任务回收；100 次取消、100 次 1 秒 timeout 后测资源基线。只取消线程 future 而底层连接泄漏不算通过。
3. 断 stdin/stdout、关闭 client、SIGTERM/SIGKILL、测试 HTTP 对端断开，必须有界退出。独立周期计数可验证 await 不阻塞定时任务，但不把它叫真实 consumer 续租或 interrupted 验收。
4. claim/cancel 竞争、lease/heartbeat、重复 receipt、无 SDK 的生产 `--mcp` 懒加载等业务验证明确移到 P1.5，不让 P0 依赖未建成的 P1。

### P0.3 宿主与证据边界

探针的 Linux SDK 结果单独记录版本与日志。真实宿主的一小时调用、取消和重挂留给 P4 人工组；SDK schema/取消通过不替代宿主通过，未测成本仍为未知。本轮只把 Kimi 临时测试配置的 `toolTimeoutMs` 调整为3700000，不真实等待3600秒；若宿主实际更短超时须按证据报告，不能增加无限后台模型轮询。历史25/120秒宿主与性能结果不改写。

**P0 出口**：transport 自动组通过，有真实取消/并发/等待及资源证据；即可进入 P1。没有五工具和业务状态不算 P0 缺项，也不能因此宣称业务 conformance 已通过。

## 5. P1：标准库持久、安全与发布核心

### P1.1 daemon 身份与权限

1. 规范化 workdir；竞争每 workdir 启动锁，取锁者负责初始化/恢复并终生持锁。已有锁持有者时走有界等待与 attach，验证 serve.json、instance_id、协议、管理 health workdir；attach 不要求再次取得 daemon 独占锁，也不得删锁抢占。陈旧端口、其他服务占端口、双启动均不能误 attach。
2. `.pptx-html` 私有目录与 0600 发现文件；management token 只进入代理内存和管理 Authorization。浏览器仅 session scoped token，经 fragment 引导到 sessionStorage 并清除地址片段。
3. 静态请求路径在统一入口拒绝 `.pptx-html`、`.git`、凭证和越界/符号链接穿透；受管资产读取按一致性文档实现，不能因 iframe 无 Authorization 而整体开放管理文件。
4. 校验 Host、同源 Origin、权限矩阵和所有路径；公开 health 只返协议规定四字段。跨 session 的 token、ID、draft_id、version path、资产路径不得互通。
5. 无MCP实现`--deck REL`与`--new [REL]`互斥；无参时index存在则打开，否则briefing target=index.html；非index显式--deck slides.html。CLI/脚本首次及再次打开都签发新的单次bootstrap，已存活daemon通过仅管理权限的POST /api/bridge/bootstrap签发，不创建consumer。
6. 按§7.6实现landing→fragment清除→按token摘要ticket独立命名的短期Path=/bootstrap cookie→GET /bootstrap?ticket=非秘密摘要→302 editor片段。raw boot不进query/日志/普通API；校验Host/同源/一次使用/300秒expiry/重启，两个启动tab不得互串。手动非Gitgit_ready=false仍可开，首存init:true先保护后写；MCP open自动init；匿名旧写401。

### P1.2 SQLite 状态机与有界接收

1. 实现 sessions/intents/events/clients 最少实体、外键/WAL/busy_timeout、必要唯一约束及 session+status+seq 查询索引；数据库版本升级失败拒绝写入，不重建丢历史。
2. 按 session/intent UUID/规范 payload digest 去重；单调 seq/event_id 由服务分配。JSON 字段顺序不改变 digest，未知 type/顶层字段拒绝。
3. 接收事务落盘后返回 accepted；派生 intent JSON 失败时认领返回明确错误，不给不存在指针，也不能删除已接收 SQL 记录。
4. 新增consumers登记状态：open事务注册/刷新本consumer，无人owner时registered，不抢他有效owner；await原子acquire有资格的registered/paused/expired→waiting，同owner重入，他有效owner `SESSION_BUSY`。close设requires_open，再次open同session才解除；heartbeat不能登记/acquire。仅 waiting owner 在90秒 lease 后回收；processing owner 不按 `lease_until` 自动过期，同 owner 迟到 heartbeat/progress/complete/fail 继续有效，第二 consumer 仍 `SESSION_BUSY`。
5. 实现 cancel/retry/close/lease 迁移；每条迁移和通知在同一状态真相下记录，拒绝 succeeded retry、过期 attempt 和越权 complete。
6. 按路由先选预算再读体：控制/intent 2MiB、save/draft 64MiB、asset 48MiB JSON且raw≤32MiB；intent规范UTF-8 payload≤1MiB，MCP >16KiB返回摘要+绝对intent_file+payload_bytes。集中常量按协议§7.5实现；真实多MiB HTML/草稿/典型大图必须成功回归，不能把控制限额套到文档。磁盘满拒绝新增，不删除未确认请求或旧attempt副本。
7. A 类 save/asset/rollback 只发 facts/events 更新 revision；不能塞进 B 类队列。await 附最新 facts 摘要而非完整历史。

### P1.3 工作副本、CAS 与日志化发布

1. open 登记受管目标：无 deck 的 target_path 已知而 deck_path/revision=null；同目录重复目标复用，第二个受管 deck 拒绝；不重叠目录允许独立任务。
2. Git基线只覆盖受管集合，不改父仓库配置/index。MCP open自动init及保护，失败停止；手动bootstrap非Git打开成功但git_ready=false，首次save确认init:true后先init/保护再写，失败仅阻断发布。atomic_write只有单文件原子性，不能描述为跨文件事务。
3. 认领时创建对应工作副本与基线，保留相对 assets/fonts/export 关系；检查副本及目标符号链接，生成/转换实际写到 `work_path`。
4. complete先鉴权并查同intent+attempt+原consumer的持久成功结果，命中只读重放；未命中才按新写顺序校验 processing owner/attempt fence（lease 时间只作 telemetry）→ 路径/产物/精确validation → seal及目标revision CAS → 快照/journal → 受控发布 → 文件/Git/SQLite终态与events → receipt。同一 processing owner 的迟到 complete 有效；旧 attempt 或已被显式终止的 owner 无成功结果不得进入写流程。阶段细节按一致性journal表。
5. 外部编辑或页面保存抢先改变 revision 时 conflict，不覆盖；保留副本。export-only 发布也检查基线，不把旧内容产物伪标 fresh。
6. publish 失败或 daemon 重启，先恢复未完 journal 再 ready；恢复后只能是可验证的旧状态、新状态或明确阻断，不能放行混合状态。无法恢复返回 RECOVERY_FAILED 并保留证据。
7. complete 重试只返原 receipt；崩溃发生在文件替换后、SQL 终态前或响应前均需覆盖。不能声称外部 Agent shell 和生图费用也恰好一次。
8. save/rollback/asset/显式本地 convert 共用互斥和 revision 通路；转换实现仍调用技能。冲突返回明确错误而不是队列外悄悄写文件。

### P1.4 SSE 与客户端状态

1. events 持久化、鉴权 fetch 流、每业务事件 id、15 秒注释 ping；心跳分消费者与浏览器，不能以 HTTP/SSE 连接存在证明页面 online。
2. 浏览器 15 秒 heartbeat，45 秒未见 offline，离线 dirty=null；聚合 any_dirty 和 clients，不把一个 clean tab 代替所有 tab。
3. after 游标重放、去重、保留最近 7 天与每 session 最近 1000 条的并集；过期返回 resync-required；intent/receipt/快照不随事件清理删除。
4. SSE/await不长期占写锁，连接有界并可回收。新增浏览器POST /api/intents/query：严格session/statuses/cursor/limit/intent_id，seq升序分页、limit默认50最大100、单条模式禁止混入过滤字段，结果无payload；status返回recoverable_count但不代替详情。索引支持session+seq/status，单页limit+1判断has_more。
5. 首载/新origin/SSE resync先status记事件E，再query从cursor=0分页恢复，最后订阅after=E补齐变化；失败保留本地草稿，不通过跳最新游标丢恢复入口。

### P1.5 五工具 conformance（P1核心完成后）

1. 生产 `tools/edit.py /abs/workdir --mcp` 经官方SDK真实initialize/list/call，恰好五工具、精确schema、结构化结果、错误封装和stdout隔离；执行验收SDK-01–07，与P0的两个探针工具严格分开。
2. 真实daemon/SQLite覆盖open登记registered/不抢owner→await acquire→同owner重入；close后直接await/heartbeat拒绝，重新open同session才可acquire。分别测试 waiting 90秒 expired 回收与 processing 90秒仅 telemetry；processing 同 owner 迟到 heartbeat/progress/complete/fail 有效，第二 consumer `SESSION_BUSY`。再测claim/stop竞争、redelivered、retry_id丢响应、`rebuild|resume` attempt+1、resume完整性/base/publication/无 writer门禁、旧attempt新写拒绝/成功receipt只读，以及浏览器15/45秒心跳。
3. 测long poll期间status/heartbeat/close并行，真实HTTP关闭/取消能回收；生产无SDK时--mcp非零且提示安装，手动模式不导入SDK。
4. 实现并验收内部只读CLI `python3 tools/bridge_core.py revision <work_path>`；候选源与seal内部完整摘要分离，checks结构、必需names、报告路径和fresh绑定全部负例通过。

**P1 出口**：核心unittest、真实HTTP/安全/恢复组和P1.5五工具conformance通过；CAS、丢响应、独立attempt、双启动/消费者及每个journal断点均有证据。尚未有UI不可宣称用户场景闭环。

## 6. P2：editor 全链路接入

### P2.1 能力探测与显式发送

1. 梳理现有 `saveDeck`、`serializeClean`、`buildBriefExport`、`briefLast`、`refreshExport`、`loadVersions`、转换按钮三通道和嵌入 postMessage 分支。
2. 连接态集中认证fetch与错误展示；先按协议精确heartbeat绑定client，再从POST /api/bridge/status读取capabilities.local_convert/git_ready初始化按钮。公共health仍不含旧gitReady/convert详情；401不等于无后端，不匿名重试或请求管理open。
3. 无 deck 的 open 直接呈现脑暴；预览/复制不发送。发送时重新 `buildBriefExport()` 固化同源 text/json，不复用过期 briefLast。
4. 主题/批注/convert/bake/illustrate 六类请求共用提交包装器：先处理 dirty，再本地保存 UUID+payload+base_revision 快照，POST accepted 后记 seq。双击/响应丢失重发同 ID；修改后新发送才新建 ID。
5. 浏览器持久队列不存管理 token；持久化失败阻止“已可靠提交”假提示，保留界面输入并给导出恢复入口。body/payload 超限保持草稿并提供 JSON 下载。
6. 增加pending/working/succeeded/failed/conflict/interrupted和retry/cancel控件；v1明确只有rebuild，用户确认当前base及可能重复费用后持久化retry_id/expected_attempt/mode/base_revision/confirmed，再发送。网络重发使用原retry_id，不把确认解释成继续写旧副本或自动rebase。

### P2.2 草稿保护与安全加载

1. heartbeat 上报独立 client_id、dirty、active_edit、draft_pending、当前 revision/已应用游标；页面开关与 consumer 生命周期互不绑定。
2. 刷新前检查当前 tab 三种编辑风险，不只看 dirty。先备份 `serializeClean()` 结果与 annotations/base_revision，经鉴权草稿 API 成功后再允许用户选择重载；失败不丢原 DOM。
3. 草稿恢复不得把旧 HTML 直接覆盖新 revision：展示备份/当前版本，用户明确处理，恢复后按正常 CAS 保存；session 草稿不经静态 URL 暴露。
4. `deck-changed` 先验 session，再判断加载代次和草稿。首个发布使同一 session 首次加载；旧 fetch 延迟完成不能覆盖更新版本或切换后的任务。
5. `export-refreshed` 强制清除缓存 manifest 并重取；`assets-changed` 同时更新画布与目录缩略图并标 stale。资源缓存键不污染序列化后的真实 src。
6. SSE UTF-8 分块、CRLF、多行 data、重复/断线/过期游标均有统一处理；只有成功处理或记录待处理后更新游标。receipt.events 不是已应用证明。
7. 关闭tab已接收任务继续；首载、重新认证或resync后调用query恢复列表，不仅依赖status计数/SSE旧记录。close_session只暂停本consumer并设requires_open，浏览器仍可用；同consumer再协作必须重复open同session后await，不以heartbeat复活。

### P2.3 旧链路边界

- 桥会话：保存、版本、回滚、资产经受限凭证和 CAS；图片替换沿用外部 assets 文件及 data-image-state 语义。
- 无 MCP 手动服务：相同安全 API 可编辑，不要求安装 mcp；显式 `--convert` 才能本地转换，与 Agent 发布互斥。
- 普通 http.server / file://：FSAA 或下载降级，不伪造服务器保存、协作在线或 conversion 成功。
- 嵌入：原 `pptx-html:load/save/dirty/brief/annotations/export-intent` 协议保持；桥不夺取宿主保存。不得因新 auth 拦截嵌入正常消息。
- HTML 交付：canonical/hash、编辑契约和源层约定不变；token、SSE 脚本、任务 ID、草稿标记、cache-busting 临时 URL 不写入产物。

**P2 出口**：Linux Playwright 完成无 deck 与已有 deck 闭环；双 tab 草稿保护、首次加载、缓存失效、静态/嵌入/手动模式回归通过。单独 HTTP 200 不算 UI 验收。

## 7. P3：技能整合与真实产物

1. 在 `skills/html-pptx/SKILL.md` 接入已冻结五工具并设为 editor-first：恰好五工具可见时，从零请求首交互 `open_editor(null, 合理相对 output_path, brief, open_browser=true)`，已有 deck 先 open；禁止 AskUserQuestion/聊天脑暴替代 Step 0.5。`brief.submitted` 冻结后空项走默认，Step 1/2 不在聊天二问；只有用户明确拒绝或实测五工具不可用才说明原因后降级。之后 open → await → Read intent_file（必要时）→ 只改 work_path → 原技能验收 → push_update complete/fail → 用户继续才重挂，明确结束 close。
2. 六类请求分流到既有脑暴、主题双 SLOT、批注、Step 5.5 插画、Step 5.6 烙入、Step 5.7 导出；不抄第二套转换代码，不越过用户插画授权。多页 bake 的代表页作为独立 intent 完成，释放 lease 供用户在页面查看，剩余页由后续新 intent 提交，不持 lease 等聊天。
3. validation记录真实argv/退出码/报告；桥所有转换固定调用export-pptx.py <work_path> --force --track both，formats仅控制用户下载选择。必须重建并验收export/deck.pptx、deck-vector.pptx、deck.pdf、native逐页图及manifest的editable/vector两轨成功；任一缺失/失败不发布，不拿继承旧轨凑齐。fresh为完整集合全局binding，convert必须填同候选源export_source_revision。单轨能力仅留技能非桥手工调用。
4. Linux 自动化用确定性 Agent driver 执行真实五工具、磁盘编辑与技能脚本；明确它不是大模型创作能力或生图质量证明。付费生图仅在后续获准人工测试中执行，费用与不可回滚边界单列。
5. 小 fixture 验证烙入源层及导出：复制 `bake-mix`；真实密度验收复制 54 页 `cmb-retail`。所有脚本指向副本，真实 fixture 前后字节一致。
6. 从已有 deck 批注修改、样式修改、资产替换、回滚到导出逐步跑通；工作副本中抽取 hash/渲染/容量/导出报告，complete 后从正式目标及 editor 重新验证，不只检查副本。
7. 交付配置示例只用绝对 workdir，不含发现文件 token，不改用户现有 Kimi/Codex 配置；真实宿主加载由用户明确操作并记录版本。

**P3 出口**：确定性自动 driver + 真实技能产物 + editor 可见结果全部通过；原始 deck 不变。未执行付费生图及真实模型时，相关能力标“未测”，不伪写 generated 或已完成宿主验收。

## 8. P4：全回归、测量与交付判定

1. durable-processing core **34/34** 与定向 r/sdk/ui/integration 已通过；默认 r 六组、真实 integration 和 direct `o_tri_view` 的既有证据保持。最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**；前一轮 856.417秒与更早 948.520秒仅作为历史保留。代码回归不改变 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN 或人工项 NOT_RUN。
2. PERF-03 固定50/30样本、CNS-08 54页×10倍素材5轮、54页完整双轨 convert 与 formal PERF-04/05/06 已通过。
3. Kimi 2.1.1 最新正式宿主重跑整体 FAIL、formal=false；核心功能与 cleanup 均通过，失败点是 `observation-07` 工具完成后的宿主退出超时。Codex 0.150.1 因 `Not logged in` BLOCKED。
4. 两次真实 GPT-Image provider 调用均 exit 0，但整体因当次 ledger 判断 bug 保持 UNKNOWN；不自动重试。
5. Office/WPS、桌面真实开窗、图像观感和硬件掉电仍未执行，因此 P4 总体保持“部分完成”。任何 git commit/push 仍需用户另行授权。

### 8.1 命令与本次结果

```bash
python3 -m unittest tests.harness.test_bridge_core -v              # 本次 PASS 34/34
python3 tests/harness/r_bridge_check.py --group transport --group sdk --group http --group ui --group integration --group fault  # 本次 PASS
python3 tests/harness/k_brief_check.py                              # 本次 ALL PASS
python3 tests/harness/v_bridge_host_check.py --self-check          # PASS，0模型调用
python3 tests/harness/u_bridge_stability_check.py --quick           # 单独重跑 PASS
python3 tests/harness/s_bridge_scale_check.py --group integration  # 历史 PASS
python3 tests/harness/s_bridge_scale_check.py --group perf03      # 历史 PERF-03 PASS
python3 tests/harness/s_bridge_scale_check.py --group cns08        # 历史 CNS-08 PASS, 5 rounds
python3 tests/harness/s_bridge_scale_check.py --group convert      # 历史 PASS, 499867.728ms
python3 tests/harness/u_bridge_stability_check.py --formal         # 历史 formal PERF-04/05/06 PASS
python3 tests/harness/v_bridge_host_check.py --host kimi           # 历史 FAIL, formal=false（observation-07 宿主退出超时）
python3 tests/harness/v_bridge_host_check.py --host codex          # 历史 BLOCKED, Not logged in
python3 tests/harness/run_e2e.py                                   # 最终竞态补丁后 PASS 55/55，0 FAIL，856.192秒；前一轮856.417秒、更早948.520秒另记
python3 tests/harness/o_tri_view_check.py                          # 历史 ALL PASS
```

真实生图报告来自显式 `t_imagegen_check.py --real`：恰有2次 provider 调用、零自动重试；报告整体为 UNKNOWN。mock 报告为 PASS。

### 8.2 阶段状态登记

| 阶段 | 2026-10-04 状态 | 已有证据与边界 |
|---|---|---|
| P0 | **完成（Linux 自动）** | 官方 SDK initialize/list/call、schema、有界等待、并发和取消通过 |
| P1 | **完成（Linux 自动）** | durable-processing core 34/34；五工具 stdio、HTTP/安全、CAS/receipt、journal/fault、resume/rebuild、revision CLI 通过 |
| P2 | **完成（Linux 自动）** | editor v3.5；Playwright 无 deck、processing stop、resume/rebuild、保存世代、dirty 保护、SSE、fragment 与历史 UI/CAS 回滚通过 |
| P3 | **完成（确定性自动范围）** | 真实 MCP/HTTP work_path、validation、发布闭环及54页完整双轨 convert 通过 |
| P4 | **部分完成** | PERF-03、CNS-08、formal PERF-04/05/06 PASS；最终竞态补丁后 run_e2e 为 **55/55 PASS、0 FAIL，856.192秒**，前一轮856.417秒与更早948.520秒仅作历史；代码回归不改变 Kimi FAIL/formal=false、Codex BLOCKED、真实生图 UNKNOWN、人工项 NOT_RUN |
| Kimi | **FAIL（formal=false）** | 2.1.1；最新15模型进程/62工具调用/724.483s；功能与 cleanup PASS，但 observation-07 宿主180s退出超时、TERM/143；usage/cost unknown；历史累计24模型进程 |
| Codex | **BLOCKED** | 0.150.1，`Not logged in`，0调用 |

## 9. 方案风险提示（自审）

| 维度 | 风险 | 控制措施 |
|---|---|---|
| 外溢影响 | 高 | health/API 鉴权改变 editor、脚本和旧测试；P2/P4 联动，嵌入及静态路径独立回归 |
| 性能影响 | 中 | SQLite 写锁不可跨 long poll；有界请求/事件留存、资源回收与 P95 实测，54 页真实规模覆盖 |
| 维护成本 | 中 | SDK transport、标准库核心、静态 UI 各一处职责；契约映射与集中常量阻止多套语义 |
| 根因解决度 | 中 | SQL 确认与 journal 解决隐式确认和覆盖，但外部付费副作用仍只能显式恢复，不承诺全局 exactly-once |
| 向后兼容性 | 高 | 匿名写主动不兼容且明确 401；公开 health 不再给旧详情，所有自带消费者一起升级 |
| 简洁性 | 低 | 五工具、单目录单 deck、SQLite 标准库；不增常驻任务系统/框架/通用 shell 工具 |
| 边界覆盖 | 高 | retry 重建意图、validation、revision/journal 细节先冻结；响应丢失、断电模拟、双消费者、草稿失败均为硬闸 |

自审改进已纳入：将“进程在 = Agent 在线”改为持久 owner/status 证据；waiting lease 用于回收等待 owner，processing lease 仅作 telemetry；将“完成通知 = 页面刷新”改为 applied cursor；将“保存后整目录原子替换”改为分阶段恢复；将仅小 deck 冒烟提升为 54 页与真实产物回归；将标准 harness 对 fixture 的潜在写入隔离到镜像。本轮四项独立审核修订已同步至P1/P2/P3：open登记与await acquire、手动单次bootstrap和首存Git确认、固定完整both导出、持久请求query及跨事件清理恢复。设计审核结论须由整套设计交叉审核给出，本文不自行批准开发。

## 10. 一致性文档交叉复读后的执行细化

本节是 P1/P2/P4 的必做子步骤，不是未来可选加固；与验收计划 §15 一一对应，不增加 MCP 工具或私改主协议。

### 10.1 P1 补充：bundle、Git 与提交点

1. 按一致性文档 §2–3 落 `bundle_files` 分类清单；source/export/derived 分别绑定，摘要前缀和紧凑 JSON 编码逐字遵循算法。CSS/同名图/字体字节变化使 source revision 变化；纯导出不改 source，旧产物未知 binding 则 stale。页级 canonical 不参与替代 CAS。
2. Git 采用 `refs/pptx-html/<workspace-key>/<session-id>` 专用 ref 与 `GIT_INDEX_FILE` 隔离 index；API/workdir/bundle/Git树四种路径显式转换。只新增保护对象和专用 ref，不移动用户 HEAD、不写真实 index、不跑用户 hooks/filter，不把旧“每次保存提交当前分支”当兼容要求。
3. A 类保存/资产/回滚调用同一 publication；稳定 write key 与 receipt 按一致性 §5.1 实现。客户端可重发同一不可变快照：目标未前进则原 receipt，已前进则明确 conflict，不自动重写旧内容。
4. complete按协议validation校验candidate_revision（候选源），服务内部另算完整seal清单摘要；复制期间任一受管文件变化即失败。PREPARED/APPLYING且DB未COMMITTED统一回old；DB COMMITTED保new补journal；Git ref已是old不动、等于new才CAS回old，第三值冻结。第三种文件字节/损坏快照同样不ready，不猜“看起来完成”。
5. 静态GET/HEAD遵守bundle读锁；多次GET跨发布后重核revision，不接受HTML/资产混合装载。关键写入复算真实字节，后台观察只作便利。
6. attempt 编号永久递增，旧 attempt 永久 fence 且旧副本不自动删除。retry 事务按 retry_id 去重、expected_attempt CAS、`mode=rebuild|resume` 与 confirmed=true 校验，当前 base 正确才新建 attempt：rebuild 使用新隔离路径；resume 仅在旧 `work_path` 完整、base 未变、无未完 publication 且确认无 writer 后复用路径。未知外部费用须显式确认。
7. 空间默认值按一致性文档集中：内部10GiB、文件系统至少512MiB保留、bundle≤2GiB/20,000文件、同workdir最多2个准备并发。峰值预检包含 old/new/seal/temp/job/Git/SQLite；任何阶段仍处理 ENOSPC，绝不清掉未确认记录换空间。

### 10.2 P2 补充：保存中继续输入与多维草稿

1. 保存快照绑定 session/epoch/editGeneration/hash map；异步 serializeClean 结果不借共享 lastSaveHashes。receipt 后 generation 已变化时仍 dirty，不把旧 hash 写到新 DOM；同tab保存串行，后次基于前次真实 revision。
2. 防自动重载不仅三项 heartbeat 状态，还包括未提交批注/设计或脑暴表单、待确认 intent、saveInFlight、pendingAssetWrites。IndexedDB 保存这些状态和未上传 Blob；服务 draft 正文仅用已有 html/annotations/base_revision，表单留本地，不扩 body。
3. 图片是两次明确写入：资产成功到R1后才标上传已确认，HTML的src/state以R1另存到R2；第二步失败保留草稿，不能显示整个换图保存成功。浏览器大图超过body限额不走匿名或FSAA旁路。
4. 缓存刷新覆盖 CSS/font 与图片，保留用户原有 URL query，只清桥注入参数；export-only刷新不重载HTML/清批注。恢复原slide_id/章节/view/侧栏状态，目标页消失有明确落点。
5. token绑定client后，复制tab不能沿用旧凭证伪装新client，重新合法open领独立凭证。同session新tab可以读服务草稿，但恢复为自己的新草稿，不覆盖他tab原记录。
6. daemon重启旧实例token失效；手动重开CLI/脚本取得新单次bootstrap，同端口/新端口均重新认证。新origin不能读旧IndexedDB；新页首绑后status记E→query完整恢复请求→after=E补流，即使旧事件已清理也能恢复旧失败项。服务草稿可重取，未上传稿仍从旧页下载，不混称透明跨端口恢复。

### 10.3 P4 补充：威胁与极端负载

1. GET/HEAD路径隔离、硬链接、目录fd/O_NOFOLLOW竞态、匿名已登记交付资源的准确边界均测试。作品公开静态读取不等于匿名API可写；恶意同源deck、同UID进程不在沙箱保证内，入口声明仅可信deck。
2. 在基础性能组之外增加10倍素材体积的合成副本测量：不减少54页数据，仍受2GiB/20,000文件上限；超上限必须先拒绝而不是改预算让测试进入。记录峰值RSS、hash/复制/锁等待和保存/发布耗时，不提前声称毫秒级大bundle保存。
3. 针对一致性文档 §13 失败矩阵逐行挂接测试ID；已自动覆盖的故障点见下节，保存中继续输入由 UI 组覆盖。图片R1/HTML失败、字体变更页hash不变、新端口草稿恢复、真实大 bundle 等未在现有自动报告中完整证明，继续保留为待验项。

## 11. 2026-10-04 P4 最终真实执行记录

### 11.1 自动、规模与性能

- core **26/26 PASS**；默认 r 六组 PASS；integration PASS；`run_e2e.py` **55/55**；direct `o_tri_view_check.py` ALL PASS。
- PERF-03 **PASS**：`bake-mix` N=50/P95=297.388ms；`cmb-retail` N=30/P95=4691.988ms。
- CNS-08 **PASS**：54页×10倍素材5轮，每轮881文件/418460736B；各门禁、发布、save、rollback、recovery 全过。
- convert **PASS**：499867.728ms、54张 native 页图、`deck.pptx`/`deck-vector.pptx`/`deck.pdf` 三件双轨。
- formal PERF-04/05/06 **PASS**：cold N=20/P95=188.023ms；await 1s N=100/P95=1012.252ms、25s N=20/P95=25014.319ms、120s N=3/P95=120007.629ms；cancel N=100/P95=13.578ms；connections N=100/P95=17.603ms，尾20轮 FD/线程/child 增长0；idle 1800.015s、RSS +0.004MiB；active stop 266.414ms。

### 11.2 真实宿主与生图

- Kimi Code 2.1.1 最新正式重跑 **FAIL**、`formal_acceptance=false`：15个模型进程、62次工具调用、724.483s；所有核心功能 cases 与 cleanup 均通过，cleanup `ok=true`，两个 scenario stop HTTP 200、端口关闭且无残留；但 `observation-07` 在 open/await/status/close 均完成后宿主180s未退出，被 TERM，returncode 143。usage/cost 不可见，均为 unknown。历史累计为最初 trust 失败1次 + 首次功能 PASS 但 cleanup 缺陷8次 + 最新15次 = 24次模型进程；当前 cleanup 已验证 PASS。
- Codex CLI 0.150.1 **BLOCKED**：`Not logged in`，0调用。
- imagegen mock **PASS**。
- 真实 GPT-Image 整体 **UNKNOWN**：两次 provider 均 exit 0；插画2048×1536、7077065B、SHA-256 `c78324f25178b4e278b8a0e3411b6ac1a7758c7f7fe550f22058d2d2d0aadfad`，烙入2560×1440、2353840B、SHA-256 `d4fec6f2ac533007fd7a1dcb0f8e9c2c89db9753bd7da28af68054b8c414553a`。但 harness ledger 路径判断 bug 使临时目录退出前未复制人工验收图、未继续 Bridge complete；费用 unknown。bug 已修但未再次付费调用，禁止自动重试或判 PASS。

### 11.3 根因与契约修复

1. pdftocairo SVG 的内联 PNG/JPEG data URI 只在严格 base64 与文件签名匹配时放行；SVG/text data URI、畸形 payload 与所有外链仍拒绝。
2. 本地长 convert 每30秒 progress 更新活性观测；processing 不按时钟过期，若 owner 因 stop/close/restart 明确失效则终止可控子进程。
3. export 双轨成功读取生产者布尔契约 `tracks.editable.ok` / `tracks.vector.ok`，必须精确为 true。

### 11.4 fixture 与剩余项

各专项报告中的 fixture/config 前后摘要相同；最终全量 fixture 比对 **PASS**。`tests/harness/results/bridge-p4/fixtures-compare.json` 记录 baseline_entries=806、final_entries=806、baseline_bytes=final_bytes=789020265，added/removed/changed 均为空。

P4 保持“部分完成”，剩余为：Codex BLOCKED；真实生图 UNKNOWN；Office/WPS、桌面真实开窗交互、图像观感和硬件掉电 NOT_RUN。由于真实图未保留，当前无法验图；是否重新产生付费调用须由用户另行授权。

## 12. 2026-10-04 durable-processing 增量实施记录

本轮按已批准设计完成以下变更：

1. `BridgeCore` 只回收过期 waiting owner；processing owner 不再按 `lease_until` 自动中断。同 owner 的迟到 heartbeat/progress/complete/fail 继续受 `(consumer_id, attempt)` 栅栏保护，第二 owner 始终 `SESSION_BUSY`。
2. processing 仅由 complete/fail、原 consumer close、浏览器显式 stop、daemon restart 或真实发布错误结束。stop 返回 `external_work_may_continue:true`，明确 Bridge 不保证终止外部进程或撤销费用。
3. retry 支持 `mode=rebuild|resume`。两者都递增 attempt；rebuild 使用新隔离路径，resume 仅在 interrupted、正式 base 未变化、无未完 publication、原 work_path 安全完整时登记复用原路径。新 attempt 的 claim 返回 `resumed:true`，旧 attempt API 写入被拒绝。
4. validation 后与 seal 后均复核候选清单，避免 resume 路径在门禁后变化仍被发布。所有 intent 状态迁移同步写 `intent-status` 并在提交后 notify session condition/SSE。
5. `editor.html` 升为 v3.5：processing 提供“停止处理”；interrupted 同时提供“续用原副本/从当前版本重建”；brief 主结果按 processing → recoverable → pending → succeeded/cancelled 优先级恢复，并显示“其他 brief ×N”。
6. `SKILL.md`、`evals/evals.json`、MCP 字段说明与使用文档同步 processing 持久所有权和 resume/rebuild 纪律。

定向验证结果：`py_compile` PASS；core unittest **34/34 PASS**；`r_bridge_check.py --group transport --group sdk --group ui --group integration` PASS；`k_brief_check.py` PASS；`v_bridge_host_check.py --self-check` PASS（0 模型调用）；`u_bridge_stability_check.py --quick` 首次与其他浏览器测试并行时因 browser heartbeat 失败，单独重跑 PASS，正式性能结论未改变。最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**；前一轮856.417秒与更早948.520秒仅作为历史保留。代码回归不改变 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN 或人工项 NOT_RUN。

### 12.1 当前真实 resume 恢复记录

- session：`s_6jXOxN_FpDIdxrTxqtIsu-6S`。
- 原 intent `d53ad685-7502-4514-806a-782d00beb28a` attempt 1 因**旧实现的 consumer lease expiry**转为 interrupted；这是升级前遗留的历史状态，不是当前“processing 90秒自动过期”规范。
- 确认原 `work_path` 稳定且通过完整性/base/publication/无 writer 检查后，以 `mode=resume` 创建 attempt 2，`reused_work_path=true`；attempt 1 随即被 fence。
- seq 2/3 的重复 brief 已取消。attempt 2 在复用副本上重新运行 `extract-manifest --write-hashes`（53页）、`j_render_check`（53页 PASS）、`check-capacity`（0违规）和 `check-images`（PASS）。
- complete receipt：`rcpt_qBdovYOwpczJ4r0uH7vAqipe`；发布 revision：`sha256:579e17f41cf52be3522d44d4a1469426b5aed21f67cb8d04befd5c71eb00a8b0`。
- 正式 `test_case1/index.html` 发布后再次执行 render/capacity/images，均 PASS；最终 session 为 editing，pending/recoverable=0，`page_online=true`。

该恢复记录证明一次真实 resume 与正式目标复验，不是 Kimi formal PASS；Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN、Office/WPS/完整桌面交互/图像观感/硬件掉电 NOT_RUN 均不变。

## 13. 2026-10-05 SSE 连接状态修复

页面显示“Bridge 正在重连”的根因不是daemon或MCP断线：服务端为限制请求线程，主动在30秒结束SSE响应；旧前端把这个计划内干净EOF当成异常，因而每次轮换都会短暂显示错误。`editor.html` v3.5 现将干净EOF静默立即续接，只对真实网络/协议错误显示退避重连；401/403则停止循环并明确提示前端不能自行签发凭证，须经MCP `open_editor`或手动bootstrap重新打开。`r_bridge_check.py --group ui` 新增干净EOF与失效凭证两条浏览器回归并PASS；修复后完整 `run_e2e.py` **55/55 PASS、0 FAIL**，wall time **893.116秒**。该代码回归不改变Kimi formal FAIL、Codex BLOCKED、真实生图UNKNOWN或人工项NOT_RUN。
