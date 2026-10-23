# 编辑器↔Agent 桥 v2：测试与验收计划

> 2026-10-04 · 状态：P0–P3 Linux 自动范围已执行；durable-processing 增量及最终竞态补丁已通过 core 34/34 与定向回归。既有 P4 的默认 r、真实 integration、PERF-03、CNS-08、54页双轨 convert、formal PERF-04/05/06 已有 PASS 报告；最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**。前一轮 856.417秒与更早 948.520秒仅作为历史保留；这些代码回归结果不改变 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN 或人工项 NOT_RUN。Kimi 2.1.1 最新正式重跑的核心功能与 cleanup 均通过，但 observation-07 宿主退出超时，整体 FAIL、formal=false；Codex 因未登录 BLOCKED；真实生图虽两次 provider exit 0，整体因当次 harness ledger 判断 bug 保持 UNKNOWN；Office/WPS、桌面真实开窗、图像观感和硬件掉电仍 NOT_RUN。顶部状态不替代 §16 逐项记录。
> 唯一协议依据：[editor-agent-bridge-protocol.md](../design/editor-agent-bridge-protocol.md)；恢复与安全细则：[editor-agent-bridge-consistency.md](../design/editor-agent-bridge-consistency.md)；执行顺序与结果：[P0–P4 计划](../progress/1002_editor_agent_bridge_plan.md)。不得用旧总览的 after_seq 隐式确认规则覆盖本计划。
> `test_bridge_core.py`、`r_bridge_check.py` 与 `T29-bridge` 已存在；实际命令、结果、性能分位数和阻断项见 §16。UNKNOWN/BLOCKED/NOT_RUN 不得由其他自动绿灯代替。

## 1. 验收边界与总判定

验收对象为五工具 → 代理 → 标准库 daemon → SQLite / 工作副本 / journal → 受管文件 → editor 的完整链路。核心问题不是“能收到一条消息”，而是：明确提交能恢复，认领不重不漏，完成有显式凭据，冲突不覆盖，浏览器草稿不丢，正式产物可独立打开，旧模式未被桥劫持。

### 1.1 四层证据

| 层 | 方法 | 能证明什么 | 不能冒充什么 |
|---|---|---|---|
| L0 核心 | Python 标准库 unittest，临时 SQLite/Git/文件系统、确定性故障注入 | 状态迁移、路径/权限、CAS、journal 恢复不变量 | 真实 MCP / UI 已连通 |
| L1 Linux 集成 | 官方 SDK stdio client、真实 HTTP、真实 daemon 进程 | MCP 协议、取消/有界等待、认证路由、并发与响应丢失 | Kimi/Codex 宿主一定兼容、模型零费用 |
| L2 页面与技能 | Playwright + 确定性 Agent driver + 真实技能脚本 | 从 UI 到正式文件及 UI 回读、真实导出、54 页密度、纯净保存 | 大模型创作质量、付费生图效果 |
| L3 人工环境 | 真实 Kimi/Codex、可用时 Office/WPS 与真实生图 | 宿主生命周期、费用、真实阅读/编辑与图像质量 | 未运行项目的通过结论 |

所有 Linux 自动必测用例须 100% PASS，零丢稿、零越权、零未声明重复发布、零源 fixture 改动。FAIL/BLOCKED/NOT_RUN 均不得折算 PASS。L3 不具备条件时标未测，整体交付写明未完成项；用户决定是否接受部分验收，不由执行者缩减范围。

### 1.2 已冻结的测试 oracle

协议的字段/状态/错误码/时限按原文断言；一致性文档提供源/导出 revision 算法、journal 提交点/恢复分支和 A 类 receipt 规则。retry_id+expected_attempt+`rebuild|resume`、attempt fence、resume 完整性/base/publication/无 writer 门禁、精确 validation、heartbeat/client 绑定、只读 Origin 例外及分路由容量均已在本轮定稿，无接口待决项。第 15 节给出独立 oracle；BLOCKED 仅用于实际执行中缺依赖或环境受限，不用于留下未定义接口，更不能用实现输出反过来定义正确性。

特别注意：`POST /api/save`、asset、rollback 没有 intent UUID，但一致性文档 §5.1 明确了 session+动作+base_revision+规范正文摘要的稳定 write key：目标仍等于原发布结果时重放原 receipt，目标已前进时返回带原 receipt_id 的 REVISION_CONFLICT；不是无条件恰好一次。下文涉及 A 类响应丢失的泛化场景须使用这一精确 oracle。

## 2. 测试组织与隔离

### 2.1 测试文件和执行入口

- `tests/harness/test_bridge_core.py`：已实现 **32 个 unittest**，覆盖状态机、持久化、安全、Git 隔离、发布恢复、严格内联栅格、processing 持久 owner、waiting 90秒回收、显式 stop/interrupted、retry `rebuild|resume`、resume 安全复用与旧 attempt fence、convert telemetry 及双轨 manifest 契约；仅标准库，不引入 pytest。
- `tests/harness/r_bridge_check.py`：已实现独立 CLI harness，包含 SDK/HTTP/UI/故障/安全/技能/性能分组，失败非零退出。
- `tests/harness/run_e2e.py`：标准全回归入口已加入 `T29-bridge`，以子进程调用 r_bridge_check 并保留既有测试；项目仍无 build 步骤。
- `tests/harness/t_imagegen_check.py`：无参数仍为随机 loopback mock；只有显式 `--real` 才执行 `culture-kraft` 插画与 `bake-mix` 封面烙入两次真实 GPT-Image-2.5 Bridge v2 流程，固定 flare/medium/n=1、零自动重试。`--self-check` 只校验真实命令契约，不联网。
- `tests/harness/results/bridge/` 与 `tests/harness/results/bridge-p4/`：忽略目录内保存 fault/performance、生图与人工验收结果；不得存浏览器 bearer、管理 token、完整发现文件或用户真实输入。真实生成图只复制到 `bridge-p4/manual-acceptance/`。
- 选择器已实现：`--group transport|sdk|http|ui|fault|security|integration|performance`。无参数实际默认 `transport,sdk,http,ui,fault,integration`，**不含 performance**；`security` 复用 HTTP 组入口。

### 2.2 运行纪律

1. 每例创建 `TemporaryDirectory`，复制而非链接到真实 deck；daemon workdir 必须是该例绝对路径。不同并发例使用不同隔离根与随机可用端口，禁止默认固定用户端口。
2. 新建临时 Git 仓库，仅在临时目录做初始化/保存/回滚/提交测试；不借用用户工作树的 Git 身份、暂存区或父仓库。
3. 标准 `run_e2e.py` 在隔离工程镜像根运行。镜像包含 editor/tools/skills/tests 及必要相对资源，符号链接不得指回原工作树；先检查测试 ROOT 和所有转换脚本输出落点。原因：现有检查器可能把报告写入 fixture 目录，仅给新 bridge 用例做副本不够。
4. 对真实 `tests/decks/bake-mix` 与 `tests/decks/cmb-retail` 测试前后枚举相对文件和 SHA-256，断言文件集合/字节/链接目标均未变化；额外确认用户 deck 不在任何测试写入集合。
5. fault hook 只能通过测试进程内依赖注入或隔离测试构造启用，不能新增网络“崩溃/任意执行”生产端点。
6. 注入 fake clock 验证 90/15/45 秒边界，提高单测确定性；另保留真实时间 lease、心跳、取消和 25/120 秒 long poll 例，不能全用 fake clock 代替真实等待。
7. finally 清理仅本次启动的进程/端口，先正常停止再在超时后终止本次进程组；不 `pkill` 全部 Python/Chromium/soffice，不删除真实导出目录。
8. 子进程 stdout/stderr、退出码、耗时均保存；日志在采集时脱敏，不到汇总时才过滤 token。报告不需要保存完整敏感草稿。

### 2.3 数据集

| 数据集 | 用途 |
|---|---|
| 空临时 workdir | 无 deck 脑暴、Git 初始化、首次生成与首次加载 |
| `bake-mix` 完整副本 | HTML/烙入混合、源层编辑、hash、缓存刷新和两轨导出 |
| 54 页 `cmb-retail` 完整副本 | 真实高密度文本、资产、章节、连续修改、容量/认证与性能 |
| 临时合成非法输入 | UTF-8/大小边界、未知字段、越权路径、symlink、错误产物、过期 revision |
| 临时兄弟目录 A/B 与父仓库 | 多 session 隔离、共享父仓库不受污染、目录单 deck 边界 |

禁止把超限载荷塞进真实 deck 作为反例；合成数据只在临时目录。确定性 Agent driver 通过真实五工具和文件路径工作，不直接改 SQL 来假装任务完成；只有 L0 / 特定恢复注入例允许构造数据库内部状态。

## 3. 通用断言与记录结构

每例至少记录：case_id、层级、fixture、前置版本、输入摘要、实际操作序列、预期/实际状态、退出码、开始/结束 UTC RFC3339、耗时、证据路径、结论 PASS/FAIL/BLOCKED/NOT_RUN。并发/故障例额外记 instance/session/intent/attempt/seq/event/receipt 关联（无凭证）、故障点、重启次数、前后 revision 与文件摘要。

通用 oracle：

- `protocol_version=2`；revision 为 `sha256:` + 64 小写十六进制；ID 不充当权限；client_id 不排序。
- seq/event_id 服务分配、各自单调但不要求连续，两者不能混用；intent_id UUID 在同一次明确提交重试中不变。
- 文件指针为绝对路径且在授权工作区；HTTP 资源为 URL 编码相对路径；拒绝错误信息泄露 token、堆栈及任意磁盘路径。
- 错误为 `{ok:false,error:{code,message,retryable,details}}`，HTTP/业务 code 与协议 §9 一致；SDK 工具错误无成功外观。
- 有完成 receipt 不代表页面应用；必须另看已发布文件、events、客户端 heartbeat/applied revision/游标。
- 每个声称幂等的动作至少覆盖“服务已执行成功，但响应被丢弃”的重试，不以连续两次正常调用代替。
- 受管文件修改前后验证无旁路覆盖；失败不得出现部分文件被当作成功产物呈现；产物 HTML 不含桥运行时状态。

## 4. transport 探针与五工具 conformance

### TRANSPORT-01：P0独立入口

`r_bridge_check.py --group transport` 启动测试专用官方 SDK 子进程，只注册 probe_wait/probe_status，不启动业务 daemon、不依赖 SQLite/发布器或五工具。真实 initialize/list/call 验证探针 schema/结构化返回/stdout 隔离，断言默认/最大 3600、最小 1，并验证 0/3601/非整数拒绝；只实等 1 秒，3600 秒用立即取消覆盖，不能把 schema/cancel 测试写成真实一小时宿主等待。wait 期间并行 status，执行真实取消100次及1秒 timeout 样本，记录连接/线程回收。断管道/对端/进程必须有界结束；可用受控 HTTP 探针验证 offload，但不得据此宣称业务 lease/claim 已通过。历史 1/25/120 秒 PERF 样本保留在 §12/§16，不重写。

此组独立通过即满足P0出口。生产工具列表、SDK缺失时`--mcp`懒加载、claim/cancel竞争和真实heartbeat仅在P1完成后执行下列SDK-01–07；它们组成 `--group sdk` conformance，不反向成为P0依赖。

所有生产工具先用官方 SDK tools/list 核对 schema，再经 tools/call 执行以下正反例；不能只直接调用 Python 函数。

### SDK-01：初始化与严格 schema

- 实际启动 `python3 tools/edit.py /abs/temp/workdir --mcp`，完成 initialize、list、call，检查 server 名 `pptx-html-bridge`、恰好五工具。
- 检查精确类型、Literal、缺省、整数上下界、null 与空字符串差异；inputSchema 由 SDK 1.28 生成。所有工具参数以及 `CheckEvidence` / `ValidationEvidence` 字段必须有非空 description。
- 检查 `mcp.types.ToolAnnotations`：`get_status` 精确为 readOnly/idempotent、non-destructive、closed-world；其余四工具按实际启动/认领/发布/中断副作用标注，不能把写操作伪装成只读。
- structuredContent 与兼容文本能被真实 SDK client 读取；业务失败与协议解析失败分别断言。stdout 只有协议内容，stderr 可有脱敏诊断。
- 非法消息、未知工具、未知参数以及 EOF 后进程清理；SDK 缺失只有 --mcp 非零且提供安装指引，普通服务不受影响。

### SDK-02：open_editor

技能契约静态检查同时断言 editor-first：普通 PPT/PPTX/slides/deck 的 Bridge 五工具齐备时，从零创建首交互含 `deck_path=null`、合理相对 `output_path`、`view=brief`、`open_browser=true`；已有 deck 先 open；文本明确禁止 AskUserQuestion/聊天脑暴替代 Step 0.5，只允许“用户明确拒绝”或“实测五工具不可用”的可观测降级。`brief.submitted` 必须冻结并以默认值补空项，Step 1/2 不二问；多页 bake 代表页须独立 intent 完成并释放 lease，页面查看后再收剩余页 intent。还必须逐字断言：Bridge 首次打开后的当前回合固定且只调用一次 `await_intent(timeout_sec=86400)`，提供完整一天；任何 `kind=timeout` 后立即说明页面仍可用并结束回合，严禁同回合再次 await，只有用户新聊天消息要求继续时才在新回合重等。协议 1–86400 秒范围继续由 SDK 边界测试覆盖，不因技能工作流约束而收窄。

1. `deck_path=null`，默认 output_path/index.html，返回 phase=briefing、deck_path/revision=null、target_path 为绝对目标；磁盘无伪造 HTML。
2. 已有 HTML 绝对路径→editing；已有 deck 时 output_path 被忽略。view 枚举 edit/brief/annotate/export 均可达，其他值拒绝。
3. open_browser=false 不调用 OS 浏览器；open_browser=true 才可尝试；page_online 在 heartbeat 前 false，不能因调用 webbrowser 成功置 true。
4. 重复同目标返回同 session；有 live tab 不反复开窗口，离线后可重开。跨目录任务独立，同目录第二受管 deck 拒绝且未登记文件不受影响。
5. Git 不可用/保护基线失败明确错误；父仓库配置、无关暂存文件不变；URL 不含管理凭证。
6. 成功响应丢失后重新open不创建第二session/daemon或重复Git基线。无人owner时consumer_state=registered，尚无owner lease、agent_state不能假waiting；他有效owner存在时open只登记本consumer，不抢占；同有效owner重复open刷新登记且保持waiting/working。
7. close后同consumer的await/heartbeat必须拒绝，重复open同目标后才回registered，再await可acquire；不允许以get_status或成功receipt重放代替重新open。自然lease过期但未close的已登记consumer，在无processing时可由await重新acquire。

### SDK-03：await_intent

1. 等待值默认 86400，schema/核心范围 1–86400；0/86401/小数/字符串拒绝；无 after_seq 参数。自动回归用 pending 立即返回或 1 秒 timeout，不真实 sleep 86400；历史 1/25/120 性能样本保留。
2. 先open登记registered，再await原子acquire→waiting，空队列kind=timeout且无新intent；未open/close后未重新open时RECOVERY_REQUIRED。并发两个registered只能一个取得owner；自然expired且无processing可重新acquire，paused须通过requires_open资格检查。有效owner才认领最早pending并返回payload/facts/attempt/文件指针。
3. 同 owner 再 await 必为同 intent+attempt，redelivered=true；未 complete 不越过该条取下一条。第二 owner SESSION_BUSY。
4. processing 认领响应丢失后同 owner 再 await 重放；90秒后 lease 可显示过期 telemetry，但不得改变 processing、owner 或 attempt。同 owner 迟到 heartbeat/progress/complete/fail 仍有效；第二 consumer 必须 `SESSION_BUSY`。processing 仅可由 complete/fail、原 consumer close、网页显式 stop、daemon restart 或真实发布/CAS错误转出，不自动重跑。
5. payload 16KiB 边界与大 payload 文件指针见 DATA-03；派生文件失败不返回不存在指针。
6. cancel 等待释放连接，不删除 pending；与认领竞争时 processing 保留。验证真实 SDK cancellation，不只关 HTTP socket。

### SDK-04：push_update

1. 必填 session/intent/attempt/action，attempt≥1、message≤2000 字符，progress/complete/fail 外枚举拒绝；代理 consumer 不由模型传入。
2. progress 只更新 telemetry 与 notice，不以“续租”决定 processing 存活；正式文件/revision/终态不变。fail 保留副本并记录失败，不伪 publish。
3. complete只消费分配的attempt副本，不接受任意源目录/shell/HTML。精确validation及每类必需names按CNS-11逐项测；缺HTML/产物/报告、非零、摘要错不发布，代理不得补假checks。progress/fail只允许省略validation或null。
4. 错owner/旧attempt的新写、越界/符号链接副本拒绝；revision冲突转conflict且目标不动。精确命中同session+intent+attempt+原consumer持久成功结果的complete是只读例外：即使lease已过期仍返回原receipt，不续租、不更新validation、不动当前任务。
5. 成功返回receipt/status/revision/export_revision/events/page_online，事件先持久；丢响应、daemon重启后原owner取同receipt/event集合，无第二次发布/提交。无成功记录的失效owner progress/fail/complete和heartbeat均拒绝；不能以查询成功记录抢回owner。
6. 页面 offline 时仍可成功发布，但返回 offline；页面脏或慢加载时 events 只表示已记录，不直接断言 UI 已应用。

### SDK-05：get_status

- 必填 session；未知 session SESSION_NOT_FOUND。字段与协议 §5.4 对照，processing/interrupted 只含摘要，不泄露完整 HTML/payload/历史。
- 空任务、等待、工作中、paused、recovering、冲突、export stale/fresh 全覆盖。
- 两个 tab 一脏一净，clients 分别正确、any_dirty 不被净 tab 清除；离线 tab dirty=null。daemon 活着但无 consumer lease 时不是 Agent online。
- 查询只读，不续造不存在的consumer，不改变pending/attempt/revision。capabilities精确包含local_convert/git_ready布尔值，与open同义；浏览器先heartbeat绑定，再通过现有鉴权status获取，公共health不泄露这两个字段。--convert关闭、Git保护不可用分别如实反映，capabilities不绕过执行门禁。

### SDK-06：close_session

- 仅本consumer_state返回paused并设requires_open，agent_state按会话实际owner计算；有他owner时不能错误改全局状态。close不关浏览器/daemon、不删请求/草稿/文件；直接await/heartbeat拒绝，重复open同session再await才恢复。
- 自己的 processing 转 interrupted，其他 consumer 不能结束不属于自己的任务；pending 留给后续新消费者。
- 同一关闭重复与成功后响应丢失重试幂等；迟到 close 不抢占新 owner。

### SDK-07：真实时限与资源

- await 阻塞期间 heartbeat/status/close 仍可执行；代理独立 heartbeat：waiting 时刷新90秒回收窗口，processing 时只更新 telemetry，不改变持久 owner。
- 真实取消 100 次和 100 次 1 秒 timeout 后线程/连接回到可解释基线；代理退出不遗留心跳；daemon 掉线工具有界失败。
- 一次 120 秒空等与真实90秒边界验证，和 fake clock 边界测试分开记录：waiting owner 到期回收；processing 仅更新 lease telemetry，不改变 owner/status/attempt。

## 5. HTTP API 全路由映射（HTTP-*）

下表每行须独立覆盖方法/鉴权/请求字段/响应字段/错误；实际路由实现不得以“已测 MCP”跳过浏览器权限。管理请求自动带 consumer，浏览器不能伪造管理身份。

| ID | 路由 | 必测正例及反例 |
|---|---|---|
| HTTP-01 | GET `/api/health` | 无认证仅 ok/protocol_version/bridge_available/instance_id；管理增强验证 workdir；不泄露 session/token/history |
| HTTP-02 | POST `/api/bridge/open` | 对应 SDK-02；浏览器 token 不可 open 管理任务；instance/workdir attach 校验 |
| HTTP-03 | POST `/api/bridge/await` | 对应 SDK-03；管理有效 consumer、bounded timeout；浏览器 401/403；断连接不删请求 |
| HTTP-04 | POST `/api/bridge/update` | 对应 SDK-04；浏览器 complete/publish 拒绝；伪 owner/attempt 拒绝 |
| HTTP-05 | POST `/api/bridge/status` | 管理和当前 session 浏览器均可读；他 session 拒绝；未知 session 明确错误 |
| HTTP-06 | POST `/api/bridge/close` | 对应 SDK-06；浏览器不可直接冒充 consumer；重复关闭安全 |
| HTTP-07 | POST `/api/bridge/heartbeat` | 协议§7.3两种严格role body/返回结构；消费身份有效时 waiting 刷新90秒回收窗口、processing 仅更新 telemetry；browser首次绑定client，混入另一分支字段/伪造role/错误类型拒绝；45秒离线dirty=null |
| HTTP-08 | POST `/api/intent` | 六种B类、UUID去重、服务seq、base_revision、首次attempt=1；同ID异内容409；未知顶层/type400；超限413 |
| HTTP-09 | POST `/api/intent/retry` | session/intent/retry_id UUID/expected_attempt/mode=`rebuild|resume`/base_revision/confirmed=true；两者 attempt+1；rebuild 新路径，resume 经完整性/base/publication/无 writer 门禁后复用旧 `work_path`；丢响应重放原attempt/status，竞争/异报文拒绝，旧 attempt 被 fence；详CNS-10 |
| HTTP-10 | POST `/api/intent/cancel` | pending→cancelled；processing→interrupted，返回 `external_work_may_continue:true`；cancel不是工具取消等待，也不承诺终止外部进程或撤销费用；未知记录404 |
| HTTP-11 | GET `/api/events?session_id=...&after=...` | 当前任务、Authorization fetch流、非负after；同源无Origin例外按协议；他session拒绝；过期resync |
| HTTP-12 | POST `/api/bridge/draft` | session_id/client_id/html/annotations/base_revision→ok/draft_id；只能署名token绑定client，当前session读取恢复另建新草稿；跨session拒绝；64MiB预算，失败保留DOM |
| HTTP-13 | GET `/api/bridge/drafts?session_id=...` | 最多最近 50 条元数据，不返完整 HTML；无草稿为空；跨任务不列出 |
| HTTP-14 | GET `/api/bridge/draft?id=...` | 当前 session 经鉴权读取完整备份；随机/他任务 ID 不能取内容；静态路径不可取 |
| HTTP-15 | POST `/api/save` | 既有 path/html/init 加 session/base_revision，保存 receipt 与事实事件；旧匿名 401；CAS 409；不进 B 队列 |
| HTTP-16 | GET `/api/versions?session_id=...&path=...` | browser bearer；仅受管版本；`snapshot_id` 为稳定回滚标识，`hash` 是可空 Git commit 展示值；历史 UI 支持 Bridge v2，并对旧 schema 缺 `snapshot_id` 时回退 `hash`；父仓库/他项目/未登记文件不得枚举 |
| HTTP-17 | POST `/api/rollback` | path/hash+session/base_revision，其中 `hash` 字段承载版本稳定 id（Bridge v2 为 `snapshot_id`）；新 revision/snapshot；回滚前保护；冲突不覆盖；不回滚无关文件 |
| HTTP-18 | POST `/api/bridge/asset` | assets 白名单格式+合法 base64，CAS 更新；路径穿越/伪格式/过大体拒绝；画布与缩略图刷新 |
| HTTP-19 | POST `/api/convert` | 仅显式 --convert 可用；本地转换与 Agent 任务互斥；无开关明确不可用，不后台偷转 |
| HTTP-20 | GET `/api/convert-status` | 仅当前受管转换状态；失败/完成如实、无转换不能伪running；未经鉴权不可读 |
| HTTP-22 | POST `/api/bridge/bootstrap` | 仅本机管理签发mode=deck/new+固定REL，返回单次URL/expiry；browser/boot/匿名拒绝，不创建consumer、不自动init |
| HTTP-23 | GET `/bootstrap` | 无cookie landing与有cookie一次兑换两阶段；fragment→限定cookie→302 editor片段，Host/来源/expiry/replay/重启/HEAD拒绝；详COMP-01 |
| HTTP-24 | POST `/api/intents/query` | 当前session绑定browser；严格过滤/分页/单条互斥，items/error/result_summary精确结构且无payload；详CNS-12 |

共享请求反例（HTTP-21）：错误方法、Content-Type、损坏 JSON、未知顶层字段、布尔值冒充整数、空 session、非法 UTF-8/超限 body、错误协议版本；断言非 2xx 成功外观且无状态副作用。无 Origin 管理请求允许；来自不可信 Origin/Host 的浏览器请求拒绝。路径和凭证矩阵另见 SEC 组。

## 6. 意图、持久化与并发（DATA-* / CON-*）

### DATA-01：六种 B 类 schema 和 UI 入口

| type | 硬断言 |
|---|---|
| brief.submitted | 无 deck 可提交；text/json 同次重建，json.kind=design-brief；预览/复制零请求，发送才生成 UUID；页面关闭仍执行 |
| design.submitted | version/kind/deck/answers；theme tokens/theme_css 同时保留；基于已保存 revision，不丢内容 |
| anno.submitted | version/kind/deck/annotations，项 id/targets/note/created_at 完整；changed/missing 目标不盲改 |
| convert.requested | formats为pptx/vector/pdf非空去重下载选择，scope=all；错值/空/重复拒绝。执行永远--track both，完整三文件/native/manifest两轨成功才可发布；formats不减执行范围，覆盖INT-06/07 |
| bake.requested | slide_ids 非空去重，明确用户选择；工作副本源层保留；不附送未请求导出，不越过代表页审批 |
| illustrate.requested | slots=[] 合法表示全部待生成；显式插画授权，生成失败不写 generated |

deck 路径由 session 决定，payload.deck 不得成为绕过权限的路径入口。base_revision 已过期时按规范冲突/前置校验，不把旧批注无声套到新目标。

### DATA-02：接收与规范摘要

1. 两个 JSON 字段顺序不同但语义相同的请求用相同 UUID，返回同 seq/status；同 UUID 修改内容触发 IDEMPOTENCY_CONFLICT，旧 payload 不变。
2. 接收前断网，本地队列完整；SQL 接收后丢 HTTP 响应，刷新浏览器再发同 UUID，仍是一条 intent。
3. 客户端传 seq/consumer/target_path 等未知顶层字段拒绝；seq 由 SQLite 生成，与客户端时钟/ID 排序无关。
4. 事务插入后重启仍可查询，intent JSON 删失可由 DB 重建，不改变 status/attempt/seq；文件写失败不返回假指针。
5. 事务失败/磁盘满返回 STORAGE_UNAVAILABLE，已确认请求不丢；新请求没有 accepted 假回执。模拟 WAL/busy_timeout/约束冲突，等待有界。

### DATA-03：字节边界与有界输出

- 分路由完整 JSON body 各测低一字节、恰等、超一字节：控制/intent 2MiB；save/draft 64MiB；asset 48MiB。用合法 JSON 空白补齐独立 body 边界，不让 payload/格式检查抢先遮蔽体积 oracle；HTTP Content-Length 与实际接收字节都受限。
- intent payload 1MiB 三点，按协议递归键排序、ensure_ascii=false、紧凑 JSON 的 UTF-8 字节计数；中文、emoji、转义分开测。payload≤16KiB 内联完整对象，超过改摘要/intent_file/payload_bytes；文件内容不截断。
- asset 原图 raw 32MiB 三点，body 48MiB 与解码后 raw 限制独立测试；构造有效 PNG/JPEG，不以随意字节冒充合法图片。raw 超限时即使 body 合法也返回413；原图32MiB正常 base64 编码约42.67MiB，须能在48MiB路由预算内上传。
- 正向兼容用例必须真实保存/读取大于2MiB的 HTML 和 HTML+批注草稿，并经浏览器上传/显示大于2MiB的有效图片（至少8MiB典型大图）；不能只测超限拒绝后宣称大文件兼容。64MiB 是整份 save/draft JSON 的预算，既有保存能力未缩为控制路由预算。
- message 2000/2001字符；草稿列表49/50/51条；深层非法结构不致崩溃。超路由预算保留原 DOM/Blob，不部分写入、不匿名或FSAA旁路、不假保存。
- 达到存储保护上限时拒绝新提交，保留所有未确认 intent/receipt/恢复快照及旧 attempt 副本，不靠清库释放空间。

### DATA-04：完整状态图

分别实测 pending→processing→succeeded/failed/conflict/interrupted、pending→cancelled、processing 经网页 stop/cancel→interrupted、failed/conflict/interrupted→明确 retry→pending；attempt 只在合法 `rebuild|resume` retry 增加。processing stop 返回 `external_work_may_continue:true`；非法跳转、succeeded retry、旧 attempt 确认均拒绝。生成成功前 deck_path=null，失败回 briefing 且保留请求，成功发布后 editing。

### CON-01：双 tab 排序和自动重试

同 session 两 tab 各明确发送 100 条、随机延迟并重复部分 HTTP 请求。断言 200 个唯一 UUID、200 个唯一 seq、payload 无覆盖；按服务 seq 而非 tab 时钟认领；不要求 seq 连续。double-click 同一个提交只产生一个 UUID；表单实质更新的新提交生成新 UUID。

### CON-02：双消费者和消费恢复

两个独立代理先分别open同目标登记registered，再barrier同时await同session：只能一个owner/processing，另一个 `SESSION_BUSY`；已有他 processing owner 时再次open也不抢占。赢家丢响应再await重放，complete前不领下一条。让90秒 telemetry lease 过期后状态仍为 processing，同 owner 迟到 heartbeat/progress/complete/fail 仍有效，新 consumer 仍 `SESSION_BUSY`。分别通过原 consumer close、网页显式 stop、daemon restart 和真实发布/CAS错误进入 interrupted，再由用户明确 retry 创建新 attempt；旧 attempt 写入被 fence。另测 waiting 自然 expired 可由合资格 consumer 重新 acquire，对比显式 close 后同 consumer 必须重新 open，heartbeat 不能复活。

### CON-03：双启动与发现身份

两个进程同时启动同 workdir，最终只有一个 daemon owner、同 instance；另一个 attach。陈旧 serve.json、无关占端口进程、错误 instance/protocol/workdir、锁持有者死亡均覆盖。错误发现不得连接到其他任务执行；恢复完成之前 health 不宣告 ready。重复 open 的丢响应场景不新建第二任务。

### CON-04：发布与保存/资产/回滚/本地转换竞争

在 Agent 工作副本验收后设置 barrier，页面先 save/asset/rollback 或外部文件写入，complete 必 CAS conflict，目标保持先行修改。反向时序 complete 先成功，旧 base 的页面操作 409 不覆盖。--convert 与 Agent 队列/发布互斥不同时写 export；两个不重叠目录任务不互相阻塞成全局长锁。

### CON-05：事实而非模型队列

连续保存、换图、回滚各 10 次后，B pending 不增加；revision/events 更新，下一次真正 B 请求 facts 摘要含最新事实。空 await 不因每次 A 类事件伪造 intent 唤醒模型。

## 7. 发布 journal、断电模拟与响应丢失（FAULT-*）

### FAULT-01：journal 分阶段崩溃矩阵

由一致性文档命名精确 journal 状态；测试在下列语义点分别注入异常和进程 SIGKILL。每点使用新临时仓库，至少重复 3 次，并做“恢复中再崩溃”一次。

| 故障点 | 重启后的不变量 |
|---|---|
| 校验完成、快照/journal 前 | 正式文件旧状态；没有虚假成功 receipt |
| 快照完成、journal 持久化前后 | 快照可核验；不丢已有作品；半条 journal 不能误判已提交 |
| 首个文件替换后、中间资产/fonts/export 替换后 | 启动恢复后是完整旧版或完整新版（按规范提交点决定），不是混合结果 |
| 文件替换完成、Git/SQL 终态前 | 恢复判定与文件摘要、Git、intent 一致；不重复外部操作 |
| SQL 结果/events 已持久、HTTP receipt 未发 | 原 receipt 可重放，events 不二次发号，不再次发布 |
| 清理或恢复流程中再次终止 | 再启动仍能幂等恢复，快照不可提前销毁 |

验收不是“杀进程后还能打开网页”：须比较所有受管文件存在性/删除集合/内容 hash、数据库 intent/receipt、Git 保护基线与 events，确认 ready 前恢复完成。故意破坏 journal/快照、模拟磁盘不可写时返回 RECOVERY_FAILED 或 STORAGE_UNAVAILABLE，保留证据并阻断发布，不能自动清空恢复目录后成功启动。

SIGKILL 是进程崩溃/断电路径模拟，不是真实机器断电。L0 检查关键落盘屏障调用顺序，L1 在文件替换窗口终止进程；真实硬件掉电和文件系统保证未测时明确注明，不把进程杀死宣称成全局原子或硬件耐久性认证。

### FAULT-02：完成响应丢失

通过本地测试代理在服务持久完成后丢弃响应。原客户端重试相同 intent+attempt complete；同 receipt/revision/events，Git 发布次数及文件写入次数不增加。再杀 daemon 重启后重试相同请求，仍不能重复发布。状态查询显示已经成功而非 pending；页面离线重连能取得事件。

### FAULT-03：接收、认领与其他幂等操作响应丢失

分别在intent accepted、await processing、open、close成功后丢响应，断言同seq、同processing重放、同session、无第二次关闭副作用。retry事务成功后丢响应，按原retry_id+完整确认报文重发，必须取得同一retry receipt、相同attempt，不多增；daemon重启后重复同例。异报文同ID与不同ID竞争同expected_attempt详CNS-10，不能用普通连续双调用代替丢响应测试。

### FAULT-04：A 类响应不确定与草稿备份失败

save/asset/rollback 写入后丢响应，客户端先 get_status/重新读取 revision 与必要文件，旧 base 的重复写不得覆盖新状态；不直接显示“失败，重新覆盖保存”。草稿 POST 超限/断网/500/磁盘满时，DOM、批注和持久待确认队列保留，reload 禁止自动替换。

### FAULT-05：外部副作用边界

确定性 driver 用外部调用计数器模拟已付费生图后代理死亡（不调用真实付费 API）。过期 interrupted 后不得自动再调用；明确 retry 显示可能重复外部费用。此例只证明桥没有自动重跑，不证明任意 shell/第三方 API 恰好一次。

## 8. SSE 逐事件与流式验收（SSE-*）

用真实 fetch Authorization 流运行，并从测试传输层按任意字节切块，不能用完整 JSON 调用 handler 冒充 SSE 集成。

| ID | event | 必需字段断言 | 可见效果与负例 |
|---|---|---|---|
| SSE-01 | deck-changed | session_id/revision/path/source/receipt_id | clean tab 重读正式文件；无 deck 首次加载；错 session 不应用、旧加载代次不覆盖 |
| SSE-02 | export-refreshed | session_id/revision/export_revision | 已缓存旧 manifest 时仍强制失效并重取；下载/对比/背面显示新产物 |
| SSE-03 | assets-changed | session_id/revision/files | 同名资产字节变更后主画布与缩略图都更新；导出 stale 正确；序列化 src 不留缓存参数 |
| SSE-04 | intent-status | session_id/intent_id/status/attempt | 显示真实队列/执行/冲突/失败/完成；旧 attempt 事件不覆盖新 attempt UI |
| SSE-05 | notice | session_id/intent_id/level/message | progress 状态可见，不伪百分比/不发布；文本按文本呈现，不执行脚本 |
| SSE-06 | resync-required | session_id/latest_event_id/revision | status记E→query从cursor0全分页恢复请求→after=E补流；必要文件另读，dirty继续保护；旧事件已清理也不丢恢复入口，详CNS-12 |
| SSE-07 | server-stop | instance_id | 当前服务显式停止提示、终止本次流；手动重连，不把其他 instance 停止当当前 session 删除 |

SSE-08 流解析：每业务事件 id，data 为单 JSON 对象；UTF-8 中文跨字节、CRLF、多个 data 行、一个 chunk 多事件、半事件断流、注释 ping 不误当业务。15 秒注释保活没有业务 id；断线按 1/2/4/8/16/30 秒退避，成功后重置。malformed 事件不能让客户端假推进应用游标或显示成功，需可见诊断和恢复。

SSE-09 重放/游标：相同 id 仅应用一次；处理抛错不能推进；脏页将通知持久记录为待处理后才可推进。成功 HTTP receipt 的 events 与数据库一致；客户端 offline 期间补收。事件保留使用“7 天内 或 每 session 最新 1000 条”，分别用 8 天历史不足/超过 1000 和 7 天内大量事件验证，不误写成二者交集。清理不删 intent/receipt/快照。

SSE-10 生命周期：双 tab 流分别维护游标；关闭一个 tab 不停止另一个流或消费者；取消 long poll 不关闭 SSE；SSE 重连不认领 intent。服务端30秒有界SSE响应的干净EOF必须由页面立即静默续接，不得短暂显示“Bridge 正在重连”；网络/协议异常才进入退避状态。401/403必须停止重试并提示前端不能自行签发新凭证，须经MCP `open_editor`或手动bootstrap重新打开。重复连接、断开 100 次后资源可回收，不持 SQLite 写锁阻塞保存。daemon 正常 stop 时活动 SSE/keep-alive socket 被唤醒并退出，请求线程全部结束后才关闭 SQLite；stderr 不得出现 closed database 或 BrokenPipe traceback，stop 在有活动流时仍须有界完成。

## 9. 页面端到端主场景（UI-*）

### UI-01：无 deck 脑暴→副本生成→complete→首次加载

1. 空 workdir、open_editor(null, open_browser=false)，Playwright 打开返回 URL；地址 fragment 被清除，sessionStorage 有受限凭证，管理 token 不在页面。
2. 没有真实 HTML 时进入脑暴；改变表单→预览→继续修改→复制，不产生 intent。明确发送才固化当前 text/json 与 UUID。结果区以该 UUID 绑定 loading/pending/processing/succeeded/error，HTTP receipt 显示 seq，SSE 更新处理中/完成，query + IndexedDB 在刷新后恢复；submitting/pending/processing 禁止重复发送，失败保留简报并提供恢复。嵌入 postMessage、无 Bridge 复制、Bridge 入队的文案必须互斥，网页明确不把 intent/发布 receipt 冒充只返回 Kimi 的 MCP JSON-RPC tool result。
3. driver 真实 await 获取意图与 work_path；原 target 仍不存在。driver 在工作副本生成最小合法 deck 并实际运行所需验收脚本，progress 不触碰目标。
4. complete 成功才在 target 出现文件；SQL phase=editing、deck_path/revision 有值、事件已持久；同 session 原页面收到 deck-changed 首次加载，文字可直接编辑。
5. 校验 DOM、正式文件、SQLite、Git 保护、receipt、client heartbeat revision 一致；再刷新浏览器保持同任务，不生第二 session。
6. 分支：发送后关 tab，driver 完成照常；open 后补收加载。生成失败回 briefing，无假 HTML，副本和失败请求保留。

### UI-02：已有 deck 批注与设计样式

bake-mix 副本打开→选文字批注→发送→driver 根据 targets 修改副本→真实校验→complete→clean 页刷新。再次设计面板选主题/配色→发送包含 tokens/theme_css→双 SLOT 修改→内容不丢。人为令 targets changed/missing 或 base_revision 过期，必须提示/冲突，不能猜位置盲改。文字四属性编辑与序列化仍保留合法 inline style。

### UI-03：资产→保存→回滚→导出

已有副本同名换图→uploaded及画布/缩略图更新、revision改变、导出stale；保存CAS成功后回滚保护快照，HTML/资产匹配。convert的formats选三件下载，driver固定--force --track both，完整三文件/native逐页图/manifest两轨成功再complete，UI强制重取；旧内容或任意完整集合成员缺失均拒绝。另由INT-06/07覆盖下载只选一件仍重建both。

### UI-04：双 tab 草稿保护

A/B 两 tab 同 revision，A 文字 dirty，B clean。Agent 发布后 B 可加载新版，A 必须保留原 DOM并显示待处理。分别单测 dirty=false 但 active_edit=true、dirty=false 但 draft_pending=true，仍不自动覆盖。备份包括 clean 序列化 HTML、annotations、base_revision；备份成功后的用户选择方可 reload。恢复旧草稿不绕过新 revision CAS。

加入断网、超限、页面崩溃恢复、离线>45 秒、同时一个 tab 保存，检查 any_dirty 不以 B 状态覆盖 A；离线 dirty=null，不能写 false 冒充 clean。

### UI-05：加载竞态与导出缓存

让 R1 文件 fetch 很慢，R2 发布先完成返回；最终只展示 R2。切换 session 后原事件不能加载旧 deck。先缓存 manifest/同名图片后发布，检查主画布、目录、对比页和翻面都更新；重复事件不多弹冲突框。UI 待处理记录和实际加载成功后 heartbeat 游标符合协议。

### UI-06：暂停、离线与恢复操作

consumer 等待/工作/paused/offline/recovering 状态有真实依据；close 后浏览器仍可读和手动保存。pending cancel 清晰；processing 显示“停止处理”，操作后转 interrupted，并明确 `external_work_may_continue:true`，不得暗示外部进程或费用已撤销。interrupted 同时提供 `resume`“续用原副本”和 `rebuild`“从当前版本重建”，不自动重新生图。刷新网页恢复本地未确认提交，同 UUID 去重。

### UI-07：纯净产物与既有编辑体验

以 `serializeClean` 实际保存结果重新独立加载，逐项断言：

- 无 token/桥脚本/consumer/client/intent 状态、contenteditable、草稿/运行时临时类及 blob/cache 临时 URL。
- canonical/content-hash 与 extractor 一致，主题 CSS/fonts SLOT 原样合法；烙入 `.baked-source` 源层保留但默认不参与编辑扫描。
- 文字就地编辑、图片替换、导航锚点、目录缩略图、翻面/对比/导出、批注定位和 hash stale 闭环未回归。
- 截图目检无新增遮挡/错位/空白；既有渲染/容量门禁零溢出零违规。截图不能替代文本与 DOM 断言。

## 10. 安全与旧模式兼容（SEC-* / COMP-*）

### SEC-01：凭证与 session 隔离

使用管理、A/B任务browser、单次boot、错误/空/过期凭证建立HTTP-01–24矩阵（HTTP-21为共享反例，实际23路由）。browser不可管理open/await/update/close或签发bootstrap；boot仅GET /bootstrap兑换，不能query/save/intent。A token猜到B的ID也不可读写。日志/错误/SSE/技能指令/产物/报告零token；唯一允许本机启动URL的boot片段和授权302的brt片段须单独断言不落请求query/Referer或日志。

### SEC-02：文件与静态隔离

对 `.pptx-html/serve.json`、SQLite/WAL、intents/jobs/snapshots/drafts/transactions、`.git` 和敏感文件发静态请求，均不可读；测试只用临时合成秘密，不读用户真实凭证。URL 编码/双编码/反斜线/绝对路径/`..`/NUL、目录列举、指向外部和内部秘密的 symlink、替换路径时的 symlink 竞态均拒绝。受管资源按一致性文档授权规则可正常加载，不以“安全”导致所有 deck 图片破图。

### SEC-03：浏览器 origin 与 token 引导

合法Host+同源Origin正常；恶意Host、跨源Origin、普通鉴权API仅带cookie无Bearer均拒绝；管理无Origin正常。协议§7.6的GET /bootstrap仅以单次boot cookie兑换是唯一启动例外，按COMP-01独立验收，不获得普通API权限。浏览器token仅fragment→sessionStorage，history.replaceState清除，除Authorization外请求URL/Referer/query不出现browser bearer；SSE用fetch Authorization，不用query。不能把管理token放localStorage或HTML。

### SEC-04：写入与输出最小权限

complete 不接受任意源目录/命令/HTML；副本/报告/资产路径都需受限。文件类型白名单、base64 格式、体积、路径检测先于写入；非法路径时旧资产不改变。错误 details 不泄露 token、堆栈、任意绝对路径；合法工具文件指针仍按协议提供绝对路径，不能把这两者混淆。

### COMP-01：无 MCP 手动服务

模拟无mcp包，分别运行tools/edit.py及start-webui.sh透传CLI：无参且index存在→已有deck；无参空目录→briefing target=index.html；--deck slides.html→非index；--new及--new reports/new.html→新目标；--deck/--new同时出现、缺失deck、越界和--new目标已存在拒绝且零覆盖。

真实浏览器打开/bootstrap#boot=<一次性token>：首次landing无session副作用，片段不发HTTP；清片段后以SHA-256(token)作为ticket、独立cookie pptx_bootstrap_<ticket>，GET /bootstrap?ticket=非秘密摘要完成一次兑换并302 editor片段。raw token不可进query；ticket与cookie不匹配/缺cookie/过期/重放/跨实例/错误Host/跨站拒绝并清本cookie，HEAD405不消耗。两个tab并发启动不同受管子目录，延迟cookie设置/导航，仍各自进入正确目标，不能互串或清掉另一cookie。再签发复用daemon/session，不依赖MCP；管理签发路由拒绝browser/boot/匿名，boot不能调用业务API。

手动非Git打开成功且git_ready=false，磁盘没有被自动init；首存不确认或init:false返回GIT_INIT_REQUIRED、HTML不动；确认init:true先init及保护基线，再保存receipt。模拟Git缺失/初始化失败/保护失败，打开仍可读和保草稿、保存明确失败，旧字节不动。现成父仓库按既有隔离规则保护。对照MCP open仍自动init并在失败时报错。

完成首存后验证保存/版本/回滚/换图；匿名旧写仍401，--convert需显式启用且执行both，未启用不偷转。bootstrap响应丢失不重复兑换，用户重新运行本机入口获取新token，不能重放旧302凭证。

### COMP-02：静态与 file://

普通 http.server 不存在 bridge API，能力探测降级；本地 file:// 无后端，沿用 FSAA（支持时）或下载。缺 bridge 不显示 Agent online，不伪保存到服务器；没有静默 fallback 到匿名写。现有相对资产/本地素材修复通道可用。

### COMP-03：iframe 宿主

原 harness 执行 `pptx-html:load`→文字/图像编辑→`save/dirty`，brainstorm/annotations/export-intent 消息结构不变。桥不拦截嵌入保存、不强求 FSAA 或本地 daemon；其他 origin 的宿主仍按原嵌入协议合法使用，不能将本地 HTTP Origin 规则误施加到整个 postMessage 契约。

### COMP-04：旧数据与无关文件

旧 deck 无 bridge 元数据仍可打开；skeleton/canonical 不升级。旧export manifest没tracks/native时，仅浏览旧件沿用现有回落并标stale/未核验；不能作为新桥convert complete的完整both集合或fresh证据。一个目录只登记一个 deck，其他未登记文件和父仓库无关已暂存项不进入 publish/rollback。不同互不重叠目录 session 互不误判资源归属。

## 11. 真实技能集成与 54 页回归（INT-*）

INT-01：确定性 driver 执行 open→await→文件读取/修改→真实校验→complete；通过 SDK 而非直接改 DB。对每个验证命令保存 argv/退出码/报告路径，complete 后从正式 target 再跑必要门禁并浏览器读取；校验摘要不能是预写的假“0”。

INT-02：bake-mix 副本覆盖 HTML、烙入图及源层、导出双轨和三文件下载。烙入/插画自动组可用确定性本地资产验证发布通道、失败与 state 纪律，但必须标为模拟生图，不替代付费服务质量/审批人工例。

INT-03：54 页 cmb-retail 副本做一次贯穿任务：章节定位批注→一处合理文本/样式修改→同名资产替换→保存/回滚→真实--force --track both重建完整导出集合→complete→页面首次/更新读取。验证页数/章节/文本预期/资产路径、工作副本及正式 target 的渲染与容量门禁、导出文件能重开、manifest stale/fresh；不以删页/缩内容逃避密度。原 fixture 文件摘要零变化。

INT-04：先制造失败产物（缺文件、错 manifest、旧 revision、技能非零），确认不发布、不假称全部完成；修正后经合法 retry 再跑真实命令。用户源内容不在失败过程中被部分替换。

INT-05：在隔离镜像跑标准run_e2e.py，既有组与T29通过。缺SDK/Playwright/转换依赖（含产生native页图的参考渲染依赖）明确BLOCKED/非零；桥不以旧技能的可选native降级声称完整both成功。Office/WPS人工另列。

INT-06（只选vector仍重建both）：已有旧双轨产物的副本改源后提交formats=['vector']，真实driver必须执行--force --track both；比较两轨/PDF/native/manifest均来自本次候选，验收完整集合后统一fresh。下载选择只vector，不影响实际执行；故意让editable失败或缺native时整次发布拒绝，不能保旧editable却标全局fresh。

INT-07（首次只选pptx也both）：无export的deck提交formats=['pptx']，同样真实生成deck.pptx、deck-vector.pptx、deck.pdf、export/native逐页图和export/manifest.json双轨成功记录；完整验收同源binding。拦截argv断言不是--track editable；缺任意成员不能成功。两例都从正式目标和editor重新核验，不能只看副本。

## 12. 性能、时限与资源阈值（PERF-*）

以下为待验证的 Linux 本机验收目标，不是已测数据，也不改变协议。记录 CPU/内存/磁盘、Python/SDK/Chromium 版本和后台负载；统一用单调时钟。每个样本保留原始值，P95 采用升序第 `ceil(0.95*n)` 个；不删除失败/超时样本，超时单列且判失败。

| ID/路径 | 采样 | 目标与口径 |
|---|---|---|
| PERF-01 status/heartbeat | 各预热20，测200次，双 tab+一个空 await 并发 | P95≤250ms；不含首次 daemon 启动，不因 await 长期持锁 |
| PERF-02 intent accepted | 预热20，测200次≤16KiB请求，含中文；另测20次接近1MiB载荷 | 小请求 P95≤500ms；近上限 P95≤2s；从发 HTTP 到持久 accepted，不含模型执行 |
| PERF-03 持久事件→clean tab 应用 | bake-mix 50次；cmb-retail 30次 | 接收事件 P95≤1s；实际 reload 并可编辑小 deck P95≤2s、54页 P95≤5s；dirty tab 应进入保护，不纳入自动加载成功样本 |
| PERF-04 await 时限/取消 | 1秒空等100次、25秒20次、120秒3次；取消100次 | timeout P95≤请求timeout+2s、max≤timeout+5s；取消至连接回收 P95≤1s；不允许无限挂起 |
| PERF-05 冷启动/首次空会话 | 独立空workdir 20次 | 到经身份验证 ready P95≤3s（不含OS浏览器启动）；有恢复journal的耗时单列，不掩盖或延迟恢复跳过 |
| PERF-06 长期空闲 | 双tab+consumer 30分钟；另100轮连接/断开 | 最后20轮线程/FD数量相对预热稳定基线增长≤5；30分钟末RSS相对稳定基线增长≤20MiB，若缓存需逐项解释且不得持续线性增长 |

lease/heartbeat 与事件留存为协议硬值，不拿性能目标替代：consumer heartbeat 15秒；waiting owner 90秒过期回收，processing 的同一字段只作 telemetry、不驱动状态迁移；浏览器15秒续、45秒离线；ping15秒。边界 fake clock 检查阈值前/等于/后，真实时钟允许调度误差但须记录观测值和实现轮询周期。

54 页 complete（复制/校验/CAS/发布）与导出管线总耗时单独至少测 5 次并报告全量，初轮建基线，不编造未经测量的整体秒数承诺。P95 的大样本指标和这类昂贵流程少样本不能混为统计可靠度相同。模型等待、付费生图和真实宿主调用成本不计入桥延迟“优化”数字，必须另记。

阈值未达标先检查锁、同步 I/O、全量扫描、资源泄漏和真实文件规模；不得通过关闭 fsync/绕过验证/减少内容/跳过慢样本让数字好看。确需调目标须说明实测依据并审核更新本节，不能在报告里临时放宽。

## 13. 真实宿主与人工清单（MAN-*）

所有项目当前均“未测”，SDK 1.28.0 已安装不改变此状态。

- MAN-01 Kimi：记录宿主版本/模型/绝对 workdir 配置；实际五工具列表、无 deck 脑暴、首次单次 86400 秒调用能否提交/取消、工作中断/恢复、明确结束 close。临时 MCP 配置的 `toolTimeoutMs` 设为 86500000；本轮自动测试不真实等待 86400 秒，未测不得记 PASS。
- MAN-02 Codex：独立重复相同流程，不引用 Kimi 结果；一天等待是否被宿主提前取消须实测记录。失败保留原错误，不能给无限等待补丁伪装成功。
- MAN-03 模型成本：每宿主空闲10分钟与一次完整任务，记录 tools/call 次数、实际模型请求次数、token及账单可见值；看不到记录“未知”，未做记录“未测”。不把工具超时次数直接换算成模型调用，也不把无收费回执当零费用。
- MAN-04 生图：用户明确许可后，验证插画模式和代表页审批、失败退款/费用未知说明、源层与state纪律；真实图像效果人工检查，不用本地占位图声称 AI 生图通过。
- MAN-05 Office/WPS：打开可编辑/矢量交付件及PDF，检查文本可编辑、字体/行距/无重叠、烙入页和导出页顺序。LO仅参考，Linux自动层不能替代此项。
- MAN-06 OS 浏览器：open_browser=true首次开窗、活tab不重复、离线重开、无浏览器环境诚实结果；自动层用拦截调用验证，真正桌面行为在本项人工核验。

## 14. 执行命令与证据模板

以下入口均已存在；2026-10-03 的实际执行状态见 §16。项目无 build 命令。

```bash
python3 -m unittest discover -s tests/harness -p 'test_bridge_core.py' -v
python3 tests/harness/r_bridge_check.py
python3 tests/harness/run_e2e.py
python3 tests/harness/v_bridge_host_check.py --self-check
```

真实宿主验收必须显式选择宿主；以下命令会真实调用模型并产生用量/可能费用，不能放入默认回归：

```bash
python3 tests/harness/v_bridge_host_check.py --host kimi
python3 tests/harness/v_bridge_host_check.py --host codex
python3 tests/harness/v_bridge_host_check.py --host all
```

`v_bridge_host_check.py` 无参数拒绝执行。Kimi Code 2.1.1 没有非交互 trust flag，临时 cwd 会跳过项目 MCP，因此 Kimi 正式调用固定以已受信任项目根 `ROOT` 为 cwd，并只在每次子进程期间原子替换 `ROOT/.kimi-code/mcp.json`；原文件按原字节/权限在 `finally` 原子恢复，原本不存在时删除临时文件并只删除空目录。配置中的 Python、`tools/edit.py`、临时 scenario workdir 和 `--mcp` 均为绝对参数，新进程/新 session 才读取。运行前后以不含正文的大小/权限/SHA-256 摘要核验 `ROOT/.kimi-code` 与用户 Kimi home 的 `mcp.json`、`config.toml`、`workspace-trust*` 不变；禁止修改 workspace trust。Codex 使用 `exec --ignore-user-config --ignore-rules --ephemeral` 与命令行 `mcp_servers.*` 覆盖，保留现有 `CODEX_HOME` 仅供认证读取，不调用 `codex mcp add/remove`。缺少安全隔离能力或登录态时报告 `BLOCKED`。每个宿主的脱敏 stream 原始记录和结构化报告分别覆盖写入 gitignored `tests/harness/results/bridge-p4/host-<host>.log`、`host-<host>.json`，带独立 `run_id` 且只统计当前运行；所有模型 prompt 明确禁止内建工具。只有五工具、无/有 deck、25/120秒 await、取消/reattach、close/reopen、fixture/配置零变化及约10分钟证据均齐全时，`formal_acceptance` 才能为 true。token/凭证不可落报告；usage/cost 不可见时必须写 `unknown`。

已实现分组调试：

```bash
python3 tests/harness/r_bridge_check.py --group transport
python3 tests/harness/r_bridge_check.py --group sdk
python3 tests/harness/r_bridge_check.py --group fault
python3 tests/harness/r_bridge_check.py --group performance
```

无参数的 `r_bridge_check.py` 运行 `transport,sdk,http,ui,fault,integration`，不自动包含 performance。运行报告最低结构仍为：环境/隔离根/开始结束时间/命令与退出码；逐case结论与证据；五工具23公开协议路由7事件覆盖索引（HTTP-21为共享反例，不另计路由；管理 CLI 的内部 stop 路由另列）；响应丢失与journal故障点矩阵；原fixture前后摘要；性能原始样本与分位数；Kimi/Codex人工与成本状态；失败/阻断/未测列表。

最终表述约束：

- 自动层通过：只可按实际分组说“Linux 自动化 X/Y 通过”，必须附真实结果并列人工未测项。
- 真实 fixture 缺失、完整样本数不足或人工环境未运行分别记 BLOCKED/NOT_RUN，不折算 PASS。
- 完整交付：只有全部要求已验证且用户接受剩余边界，才可汇报整体完成；不可将真实宿主、Office/WPS 或付费生图藏在日志末尾。
- SIGKILL 只模拟进程损失，不等于真实掉电；单页性能不等于54页/10倍素材认证。

## 15. 一致性文档细化与失败矩阵补充（CNS-*）

本节是已冻结协议与一致性文档的精确oracle及补充必测项，不另起协议，不留未定义的JSON字段。测试实现必须按这些独立期望验证，而不是照抄被测输出。

### CNS-01：源/导出/派生指纹与受管集合

- 按一致性 §3.1 用独立测试实现计算 golden hash：源文件原始字节、UTF-8字节序相对路径、`[path,byte_length,content_sha256]` 紧凑JSON、前缀 `pptx-html-source-v1\n`；export使用 `pptx-html-export-v1\n`。不能调用被测hash函数作为唯一期望值。
- 换行/BOM/CSS、同名图字节、字体、新增/删除/改名都改变源摘要；空目录不影响。单改导出/manifest/分析报告不改变源，导出摘要或派生binding分别变化；A→B→A可回原hash，不能把内容指纹当顺序号。
- 源字体变化但页级content-hash不变时整份导出stale；旧export未知binding即stale，继承旧产物不变fresh；纯export刷新同源请求不无故过期，相同hash的新事件仍刷新缓存。
- 新增/删除只作用受管清单；发布时未登记同名文件碰撞拒绝，未登记文件不删除。远程/未受管依赖列为未保证，不假称可回滚。

### CNS-02：Git隔离与历史范围

在临时仓库根与嵌套workdir各跑保存/回滚，预先暂存无关内容并创建未暂存文件。比较真实index原始字节hash、HEAD、分支、无关文件、Git配置前后完全一致；只允许专用refs/pptx-html和对象库新增。安装临时sentinel hook/filter确认未执行；对象路径必须是仓库根相对路径。

历史仅列session保护版本；任意其他commit即便可解析也不能回滚。旧HTML-only历史不得伪装完整资产/字体/导出恢复点。回滚是新publication/receipt而非Git reset，源hash可回历史值但事件序号前进。Git ref CAS遇第三方ref变化时拒绝，不强制覆盖。

### CNS-03：A类精确幂等与两次图片写入

对save/asset/rollback分别注入成功丢响应：同session+动作+base+规范正文key，目标未前进→原receipt、版本/事件/文件写次数不增加；目标已前进→REVISION_CONFLICT且含允许公开的原receipt_id和当前revision；未完成publication→RECOVERY_REQUIRED或短锁后复查，不能第二次发布。

图片先asset到R1，再HTML src/state保存到R2。第二步失败必须显示“资产已更新、页面尚未保存”，保留Blob/DOM；两步各自可重试/回滚。上传未收receipt前不得标uploaded；当前HTML保存不能恢复另tab早已换新的资产。asset完整base64 JSON≤48MiB且raw≤32MiB；后续HTML save独立使用64MiB预算。加入至少8MiB有效图片与大于2MiB HTML的正常成功链，不以超限反例替代大文件兼容。

### CNS-04：固定journal oracle、seal与第三方竞争

细化FAULT-01：仅孤立准备或PREPARED无DB→不发布保old；DB PREPARED/APPLYING未COMMITTED→全bundle回old、Git ref仅new→old条件CAS，Agent interrupted；DB COMMITTED→保new、补journal，原receipt/events。逐文件第N处SIGKILL均断言固定分支，不以“old/new随便一种”通过。

seal复制中改变副本，validation摘要与候选不一致必须拒绝；CAS后外部写入第三种字节时冻结RECOVERY_FAILED，不覆盖第三方sentinel；快照损坏、未知Git ref同样阻断。发布中 telemetry lease 超时不改变 processing；close 或其他显式终止也不能抢先开启第二 attempt，先恢复已持久 publication 再判终态。

静态读也测试：单个GET/HEAD不穿过正在替换的bundle；不同GET跨版本则加载后revision核对使整次装载重试，不把混合HTML/资产标已应用。外部程序读文件仍可能见窗口，测试不宣称全局文件系统原子。

### CNS-05：同tab保存中继续输入与批注世代

Playwright延迟save响应，在发起快照G1后继续输入G2；G1成功只能确认G1，G2仍dirty，live DOM不能写入G1 hash。重叠点击保存按同tab串行；后一请求基于前次成功revision。换session后旧save/manifest/image回调无UI副作用，但原session已保存事实仍成立。

dirty=false时，分别只有未发批注、脑暴/设计表单变化、待确认B intent、saveInFlight、pendingAssetWrites，也都不自动openHtml。已发批注快照成功不能清掉发送后新批注；重新定位changed/missing不贴错元素。本地IndexedDB持久失败要提示并保留输入，服务草稿成功前不重载。

### CNS-06：client绑定、重启换端口与可信deck边界

heartbeat精确断言管理body `{protocol_version:2,role:'consumer',session_id,consumer_id}` 与浏览器body `{protocol_version:2,role:'browser',session_id,client_id,dirty,active_edit,draft_pending,revision,last_event_id}`；逐项测缺失/未知字段、另一role字段混入、布尔/整数类型、revision非法、游标负值/超过session最新值。返回字段与协议§7.3逐项一致，时间由服务产生；browser不得改服务revision，paused/过期owner不得靠heartbeat复活。

未绑定browser token只能做首次合法heartbeat，其他业务API拒绝；首次绑定之后换client_id写heartbeat/draft拒绝。同tab刷新保留client身份，两个合法tab各自open取得独立token。session内新tab可读旧服务草稿，经明确选择恢复成自己的新草稿，不覆盖原草稿；不同session仍不可读。

daemon重启同端口旧token失效、新instance必须重新合法open；不同端口为新origin，旧IndexedDB不可能透明同步。分别测已上传服务draft在新页恢复，未上传草稿旧页下载→用户明确导入；连接失效期间停止自动写/重载，不能猜端口转发旧bearer。

确认入口“仅打开可信deck”的边界说明。受控合成同源脚本用于证明测试没有错误声称敌对HTML沙箱，而不是要求现有srcdoc隔离解决任意恶意脚本；不把管理token暴露给deck。所有API与内部秘密仍按权限矩阵保护。

### CNS-07：HTTP读例外与链接/格式细节

浏览器同源GET/HEAD无Origin时，鉴权API仍要求Bearer及same-origin Fetch Metadata；写请求要求同源Origin和Bearer。已登记静态交付资源可按一致性§9.4无Bearer读取，但必须Host/白名单/Fetch Metadata校验；§10所说无Bearer拒绝针对鉴权API/写入，不误封普通图片字体。

GET与HEAD共同拒绝内部/编码变体，不泄露内部文件长度；硬链接普通文件st_nlink>1拒绝，目录正常链接数不误判。读/写目录fd逐段no-follow，在检查与打开之间换symlink仍不能碰外部sentinel。上传PNG/JPEG/WebP/GIF双校验；浏览器SVG上传拒绝，已有/Agent SVG检查script/事件/foreignObject/外链，不靠删内容伪验收。

### CNS-08：容量与10倍负载

默认内部10GiB、保留空间512MiB、bundle2GiB/20,000文件、准备并发2；单测用注入预算验证低/等/超界且不真的耗尽用户磁盘。真实近满情况仅在隔离受控容量环境模拟或注入ENOSPC，禁止填满宿主盘。准备失败不碰目标，替换中失败走journal；未确认请求/receipt/草稿/快照不TTL清除。

在54页副本上以新增合法图片扩到原素材字节10倍做合成测量，超bundle上限就走拒绝例不擅升预算。测hash/复制/发布/等待/RSS，记录全量至少5次；检查流式读取，无每文件重新全目录扫描。与PERF分组同报，但不拿少样本或提前估算冒充可靠P95。

### CNS-09：与一致性失败矩阵的覆盖索引

| 一致性文档§13故障族 | 本计划用例 |
|---|---|
| 双tab保存、同tab继续输入、A类receipt丢失、图片变化/两阶段 | CON-04、UI-04、CNS-03、CNS-05 |
| intent接收/认领丢响应、排队base过期、waiting lease、processing迟到同owner/旧attempt fence、外部结果未知 | DATA-02/04、CON-02、FAULT-03/05、CNS-10 |
| complete丢响应、无deck失败、seal变化、第三方字节 | SDK-04、UI-01、FAULT-02、CNS-04 |
| validation缺检查/源不符/报告错、revision CLI、fresh binding | SDK-04、CNS-11 |
| 大HTML/草稿与典型多MiB图片正常链、各路由容量边界 | DATA-03、UI-03、CNS-03/08 |
| journal各阶段kill、Git先提交DB未提交、DB已提交 | FAULT-01、CNS-04 |
| 回滚未登记同名文件、父仓库index、空间/Git/快照失败 | CNS-01/02/08、FAULT-01 |
| export-only缓存、字体页hash不变、未发批注、旧回调、SSE恢复 | SSE-01–10、UI-05、CNS-01/05 |
| 新端口恢复、双启动/假daemon、匿名/跨域/越权 | CON-03、SEC-01/03、CNS-06/07 |
| GET/HEAD内部路径、链接竞态、超限、无mcp手动 | DATA-03、SEC-02、COMP-01、CNS-07/08 |
| open登记/不抢owner、await acquire、close后重新open | SDK-02/03/06、CON-02 |
| 手动非Git首存、bootstrap重放/双tab/来源限制 | COMP-01、HTTP-22/23、SEC-01/03 |
| 只选vector或首次只选pptx仍完整both、缺native拒绝 | INT-06/07、CNS-11 |
| 旧事件清理/新origin后query恢复、过滤分页和持久结果 | HTTP-24、SSE-06、CNS-12 |

### CNS-10：retry幂等、attempt fence 与 resume 安全复用

首次认领断言 `.pptx-html/jobs/<intent_id>/attempt-1/work/<relative-deck>`。processing 不因90秒 lease 过期；先通过原 consumer close、网页显式 stop、daemon restart 或真实发布/CAS错误令其进入 interrupted。用户明确发送 `{session_id,intent_id,retry_id,expected_attempt:1,mode:'rebuild',base_revision,confirmed:true}` 后 attempt 增至2并得到新隔离路径。保留仍持有 attempt-1 路径的旧 producer，继续写旧路径不能改变 attempt-2 字节；旧 attempt API 写入被 fence，旧副本仍存在。它只证明路径与 attempt fence，不证明任意 shell 是沙箱，也不保证外部付费不重复。

`mode:'resume'` 同样令 attempt+1，但只有 interrupted intent 且以下门禁全部通过才可复用原 `work_path`：旧副本清单/路径/摘要完整，正式 base_revision 未变化，无未完成 publication，确认没有 writer。新 claim 返回 `resumed:true`；旧 attempt 即使指向同一路径也不能 heartbeat/progress/complete/fail。分别破坏文件、改变 base、制造 publication、保留 writer，必须拒绝且不增 attempt。validation 后与 seal 后再次改变候选清单也必须拒绝发布。

在 retry 事务成功后丢响应，重发相同 retry_id/报文，即使已认领或有后续 attempt 也返回原 retry receipt 的 attempt/status，不多增；相同 retry_id 改 mode/base/expected_attempt/confirmed 触发 IDEMPOTENCY_CONFLICT。不同 retry_id 竞争同 expected_attempt 只能一个成功；过期 expected_attempt、非终态、succeeded/cancelled、mode 非 `rebuild|resume`、confirmed 缺失/false、错误 base、未完 publication 均拒绝且不建新 attempt。原 intent payload、各 attempt 基线/结果和旧副本永久保留。

### CNS-11：validation与revision辅助CLI

以真实命令结果提交候选，独立 oracle 对照 candidate_revision 与 `python3 tools/bridge_core.py revision <work_path>` 的单行输出；CLI 不修改字节/DB、不需要 token，缺 HTML/非法路径非零。检查 source 算法，不把完整 seal/导出摘要或页 hash 填作 candidate_revision。

六类请求逐一验证必需 names：brief/design/anno/bake/illustrate 的 render/capacity/images/manifest，convert 的 export。分别注入缺 validation、空 checks、漏 name、重复/未知 name、argv 非列表/空列表/空项、exit_code 非零/布尔、report_path 缺失/越界/不存在/软链接、候选源不匹配、convert 候选不等 base，断言协议错误且零发布。report_path=null 的真实无报告命令为正例；非空报告相对本 attempt work 根。driver 必须先真实执行再填 checks，代理不得自动补假 0。

非convert源修改可缺省export_source_revision而不新设fresh；convert缺binding或不是candidate_revision必须拒绝。同源成功export check还必须是--force --track both，完整三文件/native逐页图/manifest两轨成功才可全局fresh；单轨、新旧产物混合和缺native均反例。manifest最终写hash后重算候选，之后改源失败；导出/报告虽不计源摘要，seal中变化仍拒绝。

### CNS-12：持久请求query与旧事件清理恢复

1. 使用当前session已绑定browser调用POST /api/intents/query。检查精确items字段id/seq/type/status/attempt/base_revision/created_at/updated_at/error/result_summary，无payload/HTML/内部路径/checks。成功result_summary含receipt_id/revision/export_revision/message，未成功为null；失败/冲突/中断error有code/message/retryable，文本脱敏且长度受限。管理/boot/其他session凭证不能冒用browser权限。
2. 创建超过100条含所有状态的请求，seq有间隙。覆盖默认limit50、1/100、cursor0/页尾/超最大、statuses每枚举组合；按seq>cursor升序，无重复漏项；has_more与next_cursor最后页null准确。空/重复/未知statuses、负/小数/布尔cursor、limit0/101/布尔、未知字段拒绝。intent_id单条模式len1/has_more=false/next_cursor=null；不存在/他session统一404；同时给statuses/cursor/limit（包括默认值）拒绝。
3. query只读，不改变owner/lease/attempt；status.recoverable_count恰等于failed+conflict+interrupted数量，但UI必须另query获取列表。分页中状态变化，用全量cursor0和E之后SSE合并收敛，不能以旧页倒写更新attempt。
4. 构造8天前的failed/conflict/interrupted/succeeded记录，再产生足够事件使其旧intent-status落在最近1000条之外并按留存规则清理。浏览器收到resync后，status记E→query全分页→after=E补流，仍看到全部旧恢复项/成功结果，能明确retry而不自动执行；草稿不丢。
5. 重启到新端口、旧本地IndexedDB不可读，新页经本机bootstrap或MCP open获新browser token，首次heartbeat后query同session。从已清理SSE的记录恢复请求列表及服务草稿；未上传本地稿仍由旧页下载，不能混称自动恢复。两种恢复均不依赖旧origin缓存。

CNS 条目中已有自动覆盖的部分按 §16 登记；未被当前 32 个 unittest、定向 r_bridge、规模/稳定性报告或人工证据直接证明的条目继续保持 UNKNOWN/BLOCKED/NOT_RUN，不以文档检查或相邻绿灯替代。

<a id="16-2026-10-03-实际执行记录"></a>

## 16. 2026-10-04 P4 最终真实执行记录

### 16.1 自动与规模结果

证据均来自 gitignored `tests/harness/results/bridge-p4/*.json` 与 `tests/harness/results/report.json`；报告没有证明的事项不得推定通过。

| 项目 | 结果 | 关键证据 |
|---|---|---|
| core unittest | **PASS 34/34** | 在既有 durable-processing 覆盖上新增：stale telemetry 后 late fail/complete、确定性 stop/retry 与旧 progress/fail/complete 交错、重复 stop 风险提示幂等；既有 revision/receipt/Git/journal/安全/await 边界仍覆盖 |
| durable-processing 定向回归 | **PASS** | 本次 r transport/sdk/http/ui/integration/fault 与 k brief PASS；此前 v self-check（0模型调用）与 u quick PASS 保留为历史证据 |
| `r_bridge_check.py` 默认组 | **历史 PASS** | `fault,http,integration,sdk,transport,ui`；默认不含 performance |
| 最终竞态补丁后 `run_e2e.py` | **PASS 55/55，0 FAIL** | wall time 856.192秒；只代表代码回归，不改变 Kimi formal FAIL 等边界；前一轮856.417秒与更早948.520秒仅作历史 |
| `s_bridge_scale_check.py --group integration` | **PASS** | `bake-mix` 与54页 `cmb-retail` 的真实门禁、发布及可编辑刷新 |
| PERF-03 | **PASS** | `bake-mix` N=50，P95=297.388ms；`cmb-retail` N=30，P95=4691.988ms |
| CNS-08 | **PASS** | 54页×10倍素材，5轮；每轮 bundle 881文件/418460736B，render/capacity/images/manifest/revision、发布、save、rollback、recovery 均通过 |
| 54页 convert | **PASS** | 499867.728ms；54张 native 页图；`deck.pptx`、`deck-vector.pptx`、`deck.pdf` 三件完整双轨发布 |
| PERF-04 | **PASS（formal）** | await：1s N=100 P95=1012.252ms；25s N=20 P95=25014.319ms；120s N=3 P95=120007.629ms；cancel N=100 P95=13.578ms |
| PERF-05 | **PASS（formal）** | cold start N=20，P95=188.023ms |
| PERF-06 | **PASS（formal）** | connections N=100 P95=17.603ms；尾20轮 FD/线程/child 增长均0；idle=1800.015s、RSS +0.004MiB；活动连接 stop=266.414ms |
| Kimi Code 2.1.1 | **FAIL（宿主退出超时；功能与 cleanup PASS）** | 最新正式重跑15个模型进程、62次 MCP 工具调用、724.483s；核心功能 cases 均通过，cleanup `ok=true`、两个 scenario stop HTTP 200、端口关闭且无残留；`observation-07` 工具调用完成后宿主180s未退出，被 TERM，returncode 143，故 `formal_acceptance=false` |
| Codex CLI 0.150.1 | **BLOCKED** | `Not logged in`，真实模型调用0；未绕过认证，未借用 Kimi 结论 |
| imagegen mock | **PASS** | loopback mock 覆盖路由、尺寸/hash、失败、脱敏、路径和 ledger 契约 |
| imagegen real | **UNKNOWN** | 两次 provider 均 exit 0 并返回严格尺寸/hash，但 harness ledger 路径判断 bug 使临时目录退出前未复制人工验收图，也未继续 Bridge complete；bug 已修，未再次付费调用 |
| 历史回归 | **PASS** | `run_e2e.py` 55/55；direct `o_tri_view_check.py` ALL PASS |

### 16.2 真实生图的严格边界

- 插画调用：2048×1536、7077065B、SHA-256 `c78324f25178b4e278b8a0e3411b6ac1a7758c7f7fe550f22058d2d2d0aadfad`。
- 烙入调用：2560×1440、2353840B、SHA-256 `d4fec6f2ac533007fd7a1dcb0f8e9c2c89db9753bd7da28af68054b8c414553a`。
- 这两次只能证明 provider 进程成功返回并由 adapter 校验尺寸/hash；由于当次 harness 在错误位置检查 ledger，整体状态必须保持 **UNKNOWN**，费用也是 **unknown**。临时工作区退出后图像未保留，当前不能进行图像观感验收；若要验图，须由用户另行授权新的付费调用。禁止自动重试或把该结果写成 PASS。

### 16.3 宿主调用统计

Kimi 最新正式重跑记录15个模型进程、62次工具调用、724.483s。所有核心功能 cases 均通过；cleanup `ok=true`，两个 scenario 都以 `reason=cli-stop` 正常返回 HTTP 200，端口关闭且无 MCP/daemon 残留。但 `observation-07` 的 open/await/status/close 工具调用全部完成后，宿主进程未在180s内退出，harness 发送 TERM，returncode 143；因此该 case 为 FAIL，报告为 `status=FAIL`、`formal_acceptance=false`。本次 usage/cost 仍为 unknown。历史累计说明为：最初 trust 失败1次 + 首次功能 PASS 但 cleanup 缺陷8次 + 最新15次 = **24个 Kimi 模型进程**。首次运行的两个 cleanup HTTP 400 与残留 MCP/daemon 保留为历史发现，但当前 cleanup 已经正式重跑验证 PASS；重跑结束后的 `ps` 已确认无 `tools/edit.py`、`bridge_mcp`、Chromium 或 soffice 残留。Codex 因未登录 BLOCKED，0调用。

### 16.4 已验证根因修复

- SVG/导出根因：pdftocairo SVG 中已经内联的 PNG/JPEG `data:` URI 现在仅在严格 base64 解码且文件签名匹配时允许；SVG/text data URI、畸形 payload、HTTP/file/本地路径和 CSS 外链仍拒绝。
- 长 convert 每30秒 `progress` 更新 telemetry；processing 不因时钟或迟到 progress 自动失效。只有原 consumer close、网页显式 stop、daemon restart 或真实发布/CAS错误等显式终止事件才中断可控子进程；stop 仍返回 `external_work_may_continue:true`，不承诺终止外部进程。
- export manifest 以生产者真实布尔字段 `export.tracks.editable.ok` / `vector.ok` 为成功契约，必须精确为 `true`，不再误读不存在的 `status`。
- 宿主 cleanup 根因：stop body 已改为协议允许的 `reason=cli-stop`；harness 记录 host process group 与 daemon PID/start ticks/discovery，正常 stop 失败时仅对精确身份/argv 的进程组 TERM→KILL，并验证 PID 消失、端口关闭和临时 workdir 精确匹配进程为空。最新正式 Kimi 重跑的 cleanup `ok=true`，两个 scenario stop HTTP 200、端口关闭且无残留，故 cleanup 修复已验证。当前未通过项是 `observation-07` 的宿主退出生命周期。

### 16.5 fixture 与结论边界

PERF-03、CNS-08、integration、convert、Kimi host 和 imagegen 各专项报告中的 source fixture/config 前后摘要均相同。最终全量 fixture 比对 **PASS**：`fixtures-compare.json` 记录 baseline_entries=806、final_entries=806、baseline_bytes=final_bytes=789020265，added/removed/changed 均为空。历史 `run_e2e.py` 报告仍证明其自身55/55；fixture 与 cleanup 通过不能抵消 Kimi `observation-07` 的宿主退出超时。

P4 已完成 Linux 自动、真实规模、formal PERF-03/04/05/06 和54页双轨转换；Kimi 2.1.1 最新正式重跑的功能与 cleanup 均 PASS，但整体因 `observation-07` 宿主退出超时保持 FAIL、formal=false。剩余项：

- **FAIL / 待修复后显式验收**：Kimi 2.1.1 `observation-07` 宿主退出生命周期；不得误写正式 PASS。
- **BLOCKED**：Codex 0.150.1（`Not logged in`，0调用）。
- **UNKNOWN**：真实 GPT-Image 两次调用的整体流程与费用；图未保留，当前不可验图。
- **NOT_RUN**：PowerPoint 365/WPS 人工打开与编辑、完整桌面交互（仅安装后自然入口与浏览器 heartbeat 单例已 PASS）、图像观感、硬件掉电。
- 只有上述人工/阻断项补齐后，才可把 P4 写成全量完成。

### 16.6 editor-first 与 MCP schema 定向回归

本次仅调整技能入口契约、MCP schema 描述/annotations 与对应测试文档，不改变五工具、六 intent 或协议参数语义。已执行：

```bash
python3 -m py_compile tools/edit.py tools/bridge_core.py tools/bridge_mcp.py tests/harness/r_bridge_check.py tests/harness/test_bridge_core.py tests/harness/run_e2e.py
python3 tests/harness/r_bridge_check.py --group transport --group sdk --group integration
python3 tests/harness/run_e2e.py
git diff --check -- editor.html tools skills/html-pptx tests/harness docs AGENTS.md
```

结果均 PASS。SDK 组通过真实 stdio `tools/list` 核对五工具、所有顶层参数及 validation evidence 字段 description 和 `ToolAnnotations`；integration 组通过更新后的 `skill_contract_check` 与真实 MCP/HTTP 发布链路。本次一小时等待/UI 改动后，父代理完整执行 `run_e2e.py` 为 **55/55 PASS**、耗时948.520秒；这只代表本轮代码回归 PASS，不改变 §16.1 的 Kimi formal FAIL。

第一次自然触发测试确认 skill 正确命中并先调用 `open_editor(view=brief, open_browser=true)`，但同回合重复120秒 await 导致宿主外层超时；加入单次规则后的复测又因首次仍选择120秒而耗时约154秒。固定首次 `timeout_sec=25` 后，skill-creator iteration-3 的三条新版自然提示全部自动加载 `html-pptx`、均未调用 AskUserQuestion、均调用 `open_editor(open_browser=true)`，且随后首次 `await_intent` 均精确为25秒。eval2/3 exit0并正确结束；eval1 在 await 返回后宿主没有最终回复，外层90秒 exit124，所以自然触发整体仍不是全 PASS。报告记录 assertions 13/23=57.14%，旧 skill 3/23=12.5%；未通过项大多需要真实提交后续 intent，本轮只能标为未验证。人工 review：`skills/html-pptx-workspace/iteration-3/review.html`；其所在 `skills/*-workspace/` 已由 `.gitignore` 排除，仅供本地复核，不作为提交产物。

MCP schema 独立 smoke 使用 mcp 1.28.0：检查器 stdio connect/list 成功并发现恰好5个工具；新增 descriptions/annotations 后，`get_status` 被识别为 readOnly 并实际执行，返回预期 `SESSION_NOT_FOUND` 工具错误，其余4个因非只读按检查器策略跳过。现有 `r_bridge_check.py --group transport --group sdk --group integration` 仍 PASS。

首个安装后、不带 `--skills-dir` 的 smoke 自动发现 `html-pptx` 并调用 `open_editor(open_browser=true)`，但工具返回后宿主75秒内未继续到 await，最终 exit124，且 `page_online=false`；这只证明当次安装和工具发现成功。父代理随后确认系统 XDG 默认浏览器映射异常，并仅在用户级 `mcp.json` 的 `pptx-html-bridge` stdio server 环境增加 `BROWSER=/usr/bin/x-www-browser`。全新 Kimi smoke 对自然 prompt 自动加载 `html-pptx`，无 AskUserQuestion，调用 `open_editor(deck_path=null, output_path='product-weekly/index.html', view='brief', open_browser=true)`，首次 `await_intent` 精确25秒，返回 `page_online=true`，宿主 exit0，总耗时65.6秒。该 case 标记为“安装后的自然入口 + 桌面浏览器 heartbeat 单例 PASS”；它不覆盖 iteration-3 eval1 exit124，不证明完整桌面交互，也不改变 §16.1 的 Kimi formal FAIL。用户级注册细节不含凭证；howto 中仅把 `BROWSER` 写作 Linux XDG 映射异常时的可选修复，不是跨平台必需项。Codex BLOCKED、真实生图 UNKNOWN、Office/WPS/图像观感/硬件掉电及其他人工项状态均保持不变。

### 16.7 durable-processing 定向验收与真实恢复

- core unittest **34/34 PASS**；r transport/sdk/ui/integration、k brief、v self-check（0模型调用）与单独重跑 u quick 均 PASS。最终竞态补丁后的完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**；只代表代码回归，不改变 Kimi formal FAIL 等边界。前一轮856.417秒与更早948.520秒仅作为历史保留。
- session `s_6jXOxN_FpDIdxrTxqtIsu-6S` 中，原 intent `d53ad685-7502-4514-806a-782d00beb28a` attempt 1 因**旧实现的 consumer lease expiry**被置为 interrupted；该事件只作历史恢复前提，不是当前规范。
- 确认原 `work_path` 稳定并通过完整性/base/publication/无 writer 门禁后，`mode=resume` 创建 attempt 2，`reused_work_path=true`；attempt 1 被 fence。seq 2/3 的重复 brief 均 cancelled。
- attempt 2 重新执行 `extract-manifest --write-hashes`（53页）、`j_render_check`（53页 PASS）、`check-capacity`（0违规）、`check-images`（PASS），随后 complete receipt 为 `rcpt_qBdovYOwpczJ4r0uH7vAqipe`，revision 为 `sha256:579e17f41cf52be3522d44d4a1469426b5aed21f67cb8d04befd5c71eb00a8b0`。
- 正式 `test_case1/index.html` 再验 render/capacity/images 均 PASS；session 最终 editing，pending/recoverable=0，`page_online=true`。

该记录证明真实 resume、attempt fence 与正式目标复验，不是 Kimi formal PASS。历史 Kimi formal FAIL、Codex BLOCKED、真实生图 UNKNOWN、Office/WPS/完整桌面交互/图像观感/硬件掉电 NOT_RUN 均不变。

### 16.8 最终竞态审查补丁

- `push_update(progress|fail)` 在同一 session lock/SQLite 事务中执行 owner、attempt、processing 复核和带条件 UPDATE；complete 继续由 `_publish` 锁内复核，冲突终态写入也加同样的条件保护。stop/retry 先推进状态时，旧更新返回 `RECOVERY_REQUIRED`，不得覆盖新 attempt 或释放新 owner。
- processing 首次 stop 与 interrupted 状态下重复 stop 均返回 `external_work_may_continue:true`；重复调用不新增状态事件。
- `editor.html` 的 retry 请求失败后恢复原 status/error，并调用持久 query 校准服务端真相；failed/conflict 不再被伪装成 interrupted。
- 本次新增/扩充测试覆盖 stale telemetry 后 late fail/complete、确定性 stop→resume 与并发旧 progress/fail/complete、重复 stop，以及浏览器 retry API 失败状态保持。
- 实测：`python3 -m unittest tests.harness.test_bridge_core -v` 为 **34/34 PASS**；`r_bridge_check.py --group transport --group sdk --group http --group ui --group integration --group fault` 全部 PASS；`k_brief_check.py` ALL PASS；最终竞态补丁后完整 `python3 tests/harness/run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **856.192秒**。前一轮 856.417秒和更早 948.520秒结果仅作为历史记录保留。

### 16.9 SSE 计划轮换状态修复

- 根因：服务端SSE为有界线程每30秒正常结束响应，页面过去把干净EOF抛成异常，所以即使heartbeat与daemon正常，也会短暂显示“Bridge 正在重连”。
- 修复：干净EOF立即静默续接；真实网络/协议异常才显示1/2/4/8/16/30秒退避；401/403停止循环并明确提示前端不能自行签发token，必须经MCP `open_editor`或手动bootstrap重开。
- 浏览器定向覆盖正常EOF不显示假错误、立即安排0ms续接，以及失效凭证停止重试并显示合法恢复入口。`r_bridge_check.py --group ui` PASS；完整 `run_e2e.py` **55/55 PASS、0 FAIL**，wall time **893.116秒**。历史formal边界不变。
