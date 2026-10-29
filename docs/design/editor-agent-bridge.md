# 编辑器↔Agent 桥 v2：总体设计与决策

> 2026-10-04 · 状态：设计边界保持有效；“waiting lease 与持久 processing owner 分离、显式 stop、rebuild/resume、全状态 SSE notify、brief 全量状态优先恢复”已完成代码与定向自动验收。既有 P0–P3 Linux 自动实现和 P4 已执行证据保持原口径：Kimi 2.1.1 最新正式重跑整体 `FAIL`、`formal_acceptance=false`；Codex BLOCKED，真实生图 UNKNOWN，Office/WPS 等人工项未完成。实现状态与证据以[执行计划](../progress/1002_editor_agent_bridge_plan.md#11-2026-10-04-p4-最终真实执行记录)和[验收记录](../test_acceptance/editor-agent-bridge.md#16-2026-10-04-p4-最终真实执行记录)为准。
> 本文取代旧《阻塞式 MCP 会话设计》：保留独立编辑器与 daemon/代理拓扑，规定请求确认、文件发布、无 deck 创建、草稿保护和安全边界。

## 1. 文档地图与实施入口

| 文档 | 规范范围 |
|---|---|
| 本文 | 问题、产品流程、第一性原理、总体架构、取舍、兼容和范围 |
| [协议与状态机](editor-agent-bridge-protocol.md) | 五 MCP 工具、HTTP/SSE、身份、请求确认、错误和重试的公共契约 |
| [文件一致性、恢复与安全](editor-agent-bridge-consistency.md) | revision、受管 bundle、Git、工作副本、CAS、journal、草稿、鉴权和路径边界 |
| [具体执行计划](../progress/1002_editor_agent_bridge_plan.md) | P0–P4 文件分工、依赖、出口、实际进度和未测项目 |
| [测试验收计划](../test_acceptance/editor-agent-bridge.md) | 需求到工具/API/事件/故障/真实规模的测试追踪与结果口径 |

公共字段以协议为准；revision 与恢复算法以一致性文档为准。发现矛盾先修文档，不让实现者自行择一。执行计划只记录实施状态，不能改变协议；测试使用独立 oracle，不以实现返回值反向定义“正确”。

## 2. 背景与问题定义

现有编辑器是纯静态单文件网页：能直接改文字、样式、图片，保存回 HTML，收集脑暴/设计/批注意图，读取技能导出产物。Agent 在开发侧执行生成、插画、页面烙入和 PPTX 导出，页面本身不含模型调用。

当前断点有两个：用户在编辑器提交的内容要复制回 Agent；Agent 更新文件后，用户要重新打开或手动刷新。新增通信通道可以消除来回搬运，但同时引入并发写、请求重放和浏览器草稿风险。仅把按钮包成 MCP 工具不能解决这些问题。

本设计要实现可验证闭环：

`用户明确提交 → 持久接收 → Agent 认领 → 修改工作副本 → 实际验收 → 带版本校验发布 → 页面保稿更新 → 用户继续优化`

两个第一等入口：

1. **从零创作**：没有 HTML → 打开脑暴页面 → 冻结简报 → Agent 生成 → 原页面首次加载作品。
2. **已有作品优化**：打开已有 HTML → 保存/批注/选主题/请求导出 → Agent 执行 → 页面看到新版本。

成功不以“HTTP 200”或“工具返回”为准，而以正式文件、任务记录、恢复证据及页面实际显示一致为准。

## 3. 第一性原理与不可破坏的不变量

### 3.1 作品与草稿

磁盘受管 bundle 是**已发布作品**的权威来源，不是所有用户状态的唯一来源。浏览器 DOM、未发批注、脑暴表单是用户草稿，不能因为磁盘更新就清空。发布和采用新版本是两件事：服务可以成功发布，但一个有草稿的 tab 应保持旧版并提示。

### 3.2 请求与事实

“用户保存了文件”是事实，通常不需要模型执行；“请按这条批注修改”是请求。事实可合并到下次请求上下文，不能让连续 Ctrl+S 强迫模型反复醒来。预览/复制不是提交，只有明确发送才创建请求 ID。

### 3.3 投递与执行

持久化解决“请求还在不在”；认领与确认解决“谁在处理、是否完成”；工作副本/CAS解决“结果能否覆盖当前版本”。三个问题不能用一个 after_seq 游标代替。网络断开不证明执行没有发生，不自动重做付费生图。

### 3.4 版本与保护

已有 Git 仓库不证明未保存 DOM 或未提交 Agent 改动可恢复。发布前保护磁盘，丢弃前保护草稿；保护失败则不执行破坏性动作。源 hash 覆盖真实 HTML/CSS/资产/字体字节；旧页级文本 hash 继续服务既有契约，但不作为 CAS。

### 3.5 生命周期

页面、daemon、Agent 消费者各自独立。页面长开不证明模型在等；模型结束不应该关闭用户页面；daemon 崩溃不应该丢掉已接收请求。状态显示必须由 heartbeat/owner/receipt 证明，而不是由是否配置了 MCP 推断。

lease 只约束“尚未认领工作时谁正在等待”：waiting owner 仍使用 90 秒 lease 和 15 秒 heartbeat，过期后可回收。请求一旦进入 processing，owner 是持久执行所有权，lease 只作为 liveness telemetry；即使 53 页生成等真实工作超过 90 秒，也不得按时钟自动改为 interrupted。同一 owner 的迟到 heartbeat、progress、complete/fail 仍可恢复通信，第二 consumer 在该 owner 被明确释放前仍得到 `SESSION_BUSY`。processing 只由 complete/fail、原 consumer close、用户显式停止、daemon restart 的保守恢复，或真实 CAS/发布错误结束，不能由“多久没有进度”结束。

## 4. 用户流程与页面行为

### 4.1 无 deck 脑暴与 editor-first 入口

当宿主恰好暴露 `pptx-html-bridge` 五工具时，普通 PPT/PPTX/slides/deck 创作采用 editor-first：Agent 的首个人机交互直接调用 `open_editor(deck_path=null, output_path=<合理相对HTML路径>, view='brief', open_browser=true)`。不得先在聊天中脑暴，也不得以 AskUserQuestion 替代 Step 0.5。已有 deck 同样先 `open_editor` 再收页面意图。只有用户明确拒绝编辑器或实际确认五工具不可用才可观测降级，并向用户说明原因。

返回创作 session 和浏览器 URL，不创建伪 HTML。用户可预览/复制简报而不提交；点“发送给 AI”后才把当前同源 text/json 快照持久化。`brief.submitted` 是 Step 0.5 的冻结边界：未填字段走既定缺省，Agent 在 attempt 内完成 Step 1 页计划与 Step 2 主题收敛，不回到聊天二次确认。

页面结果区以具体 `brief.submitted` intent id 为锚，持久显示 loading/pending/processing/succeeded/error；提交中禁重复点击，失败保留简报并提供恢复。状态由 HTTP 接收回执、SSE `intent-status`、query 与 IndexedDB 共同恢复，而不是显示无依据百分比。恢复时必须读取并保留全部 brief 记录，主结果按状态优先级 processing → recoverable（failed/conflict/interrupted）→ pending → succeeded/cancelled 选择，同级才比较更新时间/seq；因此较新的 pending 不得遮住较旧的 interrupted/error。结果区同时显示“其他 brief ×N”并可进入既有任务面板查看每条 intent，不在通用服务中猜测、合并或删除“语义相同”请求。当前已核实的 seq1 interrupted、seq2/3 pending 三条 brief，由实施阶段在明确核对其 `json.answers` 相同后一次性取消 seq2/3；这是针对已知存量的人工/迁移动作，不新增通用去重协议。用户提交后可以关闭 tab；请求已接收则继续。Agent 在服务分配的工作副本生成，按现有技能完成布局、容量、图片与 manifest 验收，然后 complete。正式文件发布后，session 从 briefing/generating 进入 editing；原 tab 在线且无草稿时首次加载，否则下次 open 恢复同一任务。

生成失败不制造空白作品，也不清简报。页面是 Bridge 模式的澄清与审批界面；等待用户查看或再次提交时先完成当前 intent 并释放 owner，不持有 processing owner 进行聊天等待。Bridge 首次打开后的当前 Agent 回合固定且只调用一次 `await_intent(timeout_sec=3600)`，给用户完整一小时脑暴与提交；返回 `kind=timeout` 后立即告知用户页面仍可用并结束回合，只有用户发来新的聊天消息要求继续等待时才在新回合再次调用。等待可由宿主取消，但不得在同回合重复 await 或实现无限轮询。

### 4.2 已有作品优化

打开可信 deck，建立受管清单和保护基线。文字/图片保存走服务的鉴权、版本比较、恢复快照及 receipt；批注和设计面板共用一次性提交路径。提交前如果当前 DOM 未保存，用户选择先保存或取消；针对已保存版本执行时必须明确提示，不能把新 DOM 的批注绑定到旧文件。

Agent 认领后只修改 work_path。用户同时继续编辑是允许的：若用户先保存，Agent 的旧 base complete 返回 conflict，保留双方结果；不自动覆盖也不自动三向合并。

完成后 clean tab 自动更新并恢复当前位置；dirty、活动编辑、未发批注或表单草稿存在时，先保护输入并展示待处理更新。导出刷新只刷新产物，不替换活 HTML。

### 4.3 转换、烙入与插画

- “导出交付件”对应 convert.requested，v1作用范围为整份 deck；文件名/三格式与既有技能一致。
- “重新生成本页整页图”对应 bake.requested，必须显式选择，不能因为该页是 baked 就把导出请求自动升级成付费生图。
- “自动补图”对应 illustrate.requested，只有用户声明插画模式才能提交。
- 代表页审批、失败不伪造 generated、导出门禁和单向纪律不因桥接而取消。
- L1 本地 opt-in 转换与 L2 Agent 转换是互斥执行路径，同一次点击只走一个。复制按钮不是另一次入队。

### 4.4 恢复与结束

页面显示等待中、执行中、暂停、离线、恢复待决。pending 请求可取消；processing 可由浏览器显式“停止”转为 interrupted 并释放 owner，但这只是 Bridge 所有权与发布授权的停止，不承诺终止 Agent shell、浏览器外部进程、模型/生图供应商任务，也不承诺撤销已发生费用。停止与 complete/publication 竞争时由服务端事务和 publication journal 决定唯一结果，页面不能先行假定已停止。

interrupted请求提供两种明确恢复：`rebuild`从当前正式版本创建新attempt和独立work_path；`resume`仅在原attempt工作副本完整、正式base未变化、无未完publication、已确认无活跃writer且用户确认风险时复用原work_path。两种模式都递增attempt：例如attempt1 interrupted后resume得到attempt2 pending，但attempt2的attempts行指向attempt1原work_path；resume不复制、不清空、不重命名目录。后续await以attempt2重新认领该路径，旧producer携带attempt1的progress/complete/fail均被现有attempt栅栏拒绝；complete前必须重跑该intent的全部现行门禁。daemon重启仍保守地把processing转interrupted，既避免死进程永久占锁，也允许历史`lease-expired` interrupted在满足条件时resume。

resume比rebuild风险更高：attempt递增可以拒绝旧producer的迟到API写入，但不能阻止同UID旧进程继续写复用的物理路径。resume前必须由用户确认没有活跃writer；恢复后由全门禁重跑、candidate revision和seal前后稳定性检查拦截文件竞争，检测到变化必须失败而不是发布。无法确认writer已停、外部副作用未知或需要路径隔离时必须选择rebuild，并明确可能重复费用。

用户结束协作时 Agent 调 close_session，页面/daemon仍可用于手动编辑。用户显式停止 daemon 才停止本地服务。新端口重启后旧 tab 不可能透明读取新 origin 的本地草稿，旧页保留下载入口；服务端已确认的草稿可在新页面鉴权后恢复。

## 5. 总体架构

```text
Agent 宿主
  │ MCP stdio（官方 SDK，协议协商/取消）
  ▼
薄代理 tools/bridge_mcp.py
  │ HTTP Bearer（管理凭证不交给模型）
  ▼
本地 daemon tools/edit.py
  ├─ 标准库 HTTP / fetch-SSE / 路径与认证
  ├─ bridge_core：SQLite 状态、认领、lease、受管清单
  ├─ 文件发布器：工作副本、seal、CAS、journal、快照、Git专用ref
  └─ 固定技能入口触发器（仅 --convert，无转换实现）
  ▲
  │ session scoped Bearer，POST意图 / SSE状态
浏览器 editor.html
  ├─ 单一提交分发与真实回执
  ├─ 文字/图片/批注/脑暴现有界面
  └─ IndexedDB草稿、加载代次、冲突保护、产物刷新
```

### 5.1 一种 daemon，不按宿主复制后端

每 workdir 一个 daemon，生命周期进程锁保证单例。手动启动和代理按需启动使用同一服务实现；“是否有 Agent 消费者”是运行状态，不是两套业务模式。代理固定绑定配置里的绝对 workdir；不根据模型任意路径偷偷扩大授权根。

手动服务仍只需标准库。`--mcp` 入口懒加载已确认可用的官方 `mcp` SDK（1.28系列兼容范围），避免手写初始化、取消和 stdio 分帧。stdio MCP 只连接 Agent 宿主与薄代理；浏览器不讲 JSON-RPC，而是经 loopback HTTP 提交 intent、接收 receipt，并经 SSE/query 观察状态。MCP `tools/call` 的真正 tool result 返回 Kimi 宿主；网页只展示 intent 状态和发布回执，二者不得混称。缺依赖只阻断代理，明确给安装指引，不影响无 MCP 编辑。

### 5.2 一个任务数据库

SQLite 是 session/intent/receipt/event 的唯一真相，标准库可用，无外部服务。相比独立 JSON 文件加自制 seq/多文件状态迁移，事务和唯一约束更简单可靠。intent JSON 只是给 Agent 读取的可重建投影，绝不靠移动 JSON 到 done 目录充当另一套确认。

### 5.3 一个受控发布器

浏览器保存、换图、回滚、Agent complete、本地转换完成共用受控发布。工作副本完成时检查 base_revision，对旧/新 bundle 建不可变快照，逐文件日志化替换，最后提交数据库结果和事件。失败按固定状态表恢复，不以“文件好像已经写好”判成功。

Git 版本使用专用 `refs/pptx-html/` 和隔离 index，不修改用户 HEAD、分支或真实暂存区。保存仍可从编辑器历史找回，但不再等于代用户向当前开发分支 commit。无仓库时桥 open 按用户决策初始化；手动编辑非仓库仍先询问。

### 5.4 权限层次

管理 token 只在发现文件和代理内存；浏览器获得当前 session 的受限 token，不能 complete/publish 或跨任务操作。内部目录不可静态读取，旧写接口不能成为绕过认证的后门。已有 srcdoc 编辑运行可信 deck，不宣称是恶意 HTML 沙箱；该边界在入口说明。

## 6. 关键技术决策与替代方案

| 决策 | 选择理由 | 未选方案与原因 |
|---|---|---|
| 浏览器独立编辑器 | 大画布、用户已有流程、可独立交付、不依赖宿主UI | 不以 MCP Apps 作为唯一入口，目标 CLI 支持不统一 |
| MCP工具返回交互结果 | 编程 Agent 通用扩展接口，明确当前请求因果 | 不注入宿主私有用户消息、不移植 React 插件体系 |
| 有界 await + 持久队列 | waiting 仍可回收，工具等待超时不丢请求 | 不把 MCP long poll 无限化，也不把 waiting timeout 套到已认领 processing |
| processing 持久 owner | 长生成只等明确完成/失败/停止；lease仅作活性观测 | 不按90秒时钟猜测进程已死；daemon重启仍保守中断以解除死锁 |
| SQLite | 标准库、事务、唯一约束、可恢复确认 | 不自制多个 JSON 间的原子状态机、不部署外部队列 |
| attempt隔离工作副本+CAS | rebuild保护用户保存、隔离旧生产者；resume仅显式复用完整原副本 | 不允许 Agent 直接覆盖正式文件，也不把resume冒充进程隔离 |
| 受管清单+快照+journal | 兼容外部 HTML/assets 交付，失败可恢复 | 不把整个用户目录rmtree/rename，不假称跨文件全局原子 |
| Git专用ref | 避免用户父仓库与暂存区被编辑器污染 | 不再每次保存自动提交当前分支 |
| POST+fetch SSE | 标准库可实现、单向事件足够、Authorization明确 | 无需 WebSocket，也不使用URL query bearer |
| 保留现有页hash | 避免扩大生成器/编辑器契约变更 | 不把文本hash冒充样式/图片字节摘要 |

MCP Apps 本身不是仅 Codex/ChatGPT 支持，也不强制禁止所有外链；官方扩展支持 CSP 声明及多个宿主。旧文档将 Cowart 个例等同协议限制的说法已撤销。独立浏览器路线仍然是本项目的产品选择，而非基于错误排除法。

官方依据：[MCP生命周期与超时](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)、[工具规范](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)、[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview)。项目调研是选型背景，不高于协议和实测。

## 7. 全部动作与路由

| 动作 | 分类 | 桥行为 |
|---|---|---|
| 文字/四属性样式保存、排序保存、烙入源层保存 | A事实 | CAS保存 receipt，revision变化，必要时导出stale |
| 图片替换 | A事实 | 受管资产API保护旧字节，更新revision，HTML标记另存回执 |
| 版本回滚 | A事实 | 整个受管快照新发布，草稿先保护 |
| 脑暴发送 | B请求 | brief.submitted；无deck合法 |
| 设计意图发送 | B请求 | design.submitted；保留双SLOT结构 |
| 批注发送 | B请求 | anno.submitted；保留一意见多目标及changed/missing |
| 整份导出 | B请求或显式本地执行 | convert.requested 与本地 --convert 互斥 |
| 重新整页生图 | B请求 | bake.requested，显式选择页 |
| 插画补齐 | B请求 | illustrate.requested，显式模式许可 |
| 预览/复制/选择字体/翻面/目录导航 | C界面 | 不入Agent执行队列；实际样式修改保存归A |
| 换文件 | C会话路由 | 未登记/工作区外文件退出桥资格，不能保留旧session继续收写 |
| 素材blob修复 | C本地辅助 | 保留已有静态降级，不假称桥资产已更新 |

分发优先级：嵌入态由宿主处理；受管本地桥按真实消费者/用户选择入队；手动本地转换只在 opt-in 下执行；无服务使用FSAA/下载/复制。L1中“已记录，下次继续”必须真的持久接收；不能只写localStorage就宣称daemon已记录。

## 8. 兼容、范围与明确不做

保留：单HTML编辑器、纯净deck、现有编辑标记、主题CSS/fonts槽、烙入源层、postMessage协议、无MCP手动页面、file/普通HTTP静态降级、转换脚本所有权。

有意改变：

- 旧匿名写API返回401，官方editor/启动器/测试同步升级，不为旧客户端保留安全后门。
- 用户当前分支不再被每次保存自动提交；历史由专用保护ref提供。
- 源/导出stale补充bundle级检测，旧manifest未知来源保守显示未核验。
- 页面与服务驻留默认可持续，模型是否等待另有真实状态。

第一版不做：多用户远程协作、Web公网部署、三向自动合并、通用命令执行工具、任意文件管理器、MCP Apps内嵌、敌对HTML沙箱、外部AI副作用恰好一次、自动替用户配置宿主、未授权付费生图。

多tab允许但写入受CAS限制；每目录一受管deck是明确范围，不把共享assets归属难题藏到实现。外部非协作写者只能检测冲突，不能被本服务神奇锁住。

## 9. 性能与复杂度预算

等待中的 daemon 通过阻塞 HTTP 与 heartbeat 维护连接，不持续调用模型；但 MCP tool call 会占用当前宿主回合。生产默认/最大等待均为 3600 秒，目的是给页面脑暴一个完整小时，不承诺“永远等待且零成本”。用户可取消宿主工具调用，取消只终止本次等待、不删除已提交 intent；历史 1/25/120 秒性能样本继续作为既有证据，本次不把未实跑的 3600 秒宿主等待写成 PASS。

磁盘hash与复制按字节线性成本，使用流式I/O、短SQLite事务、限制准备并发。不能用禁用fsync/跳过hash达到延迟目标。小deck通知/刷新目标和54页真实deck指标分开，详见验收计划。性能样本包括错误和超时，不通过删慢样本证明达标。

本设计不再用“后端+450行、前端+350行”排期。拆分存储、发布、安全、代理与界面职责是为了隔离测试和维护，不为了按文件数追求表面简洁。页面仍保持单文件，不引入构建栈。

## 10. 实施门禁与交付判据

实施顺序仍为：文档冻结与交叉审核 → P0官方SDK/取消/有界等待 → P1持久安全发布 → P2无deck及优化页面闭环 → P3技能/确定性 Agent 集成 → P4全回归/性能/真实宿主。截至2026-10-04，既有P0–P3 Linux自动范围已完成，P4的真实fixtures、规模、双轨转换与formal性能已有PASS证据；processing持久owner、stop、resume、状态事件唤醒和重复请求UI也已实现，并通过本轮定向 core/UI/协议回归。该定向绿灯不替代未重跑的完整 `run_e2e.py`，也不改变真实宿主与人工项结论。

SDK通过不能冒称Kimi/Codex实测通过。真正模型回合、付费生图、Office/WPS属于独立人工记录，不藏在自动测试绿灯后面。Kimi 2.1.1 最新正式重跑虽通过核心功能与 cleanup，但 `observation-07` 工具完成后的宿主退出超时，整体仍为 FAIL、formal=false；Codex 因未登录 BLOCKED，总体验收仍未完成。

最小可交付判据不变：不能只证明工具可列出。当前自动环境已证明无 deck、已有 deck 核心页面状态、冲突/丢响应/恢复/草稿保护/静态安全，以及 `bake-mix`、54页 `cmb-retail`、真实双轨导出链路；真实生图整体仍 UNKNOWN，Office/WPS 与桌面交互仍待人工。标准全回归命令仍为 `python3 tests/harness/run_e2e.py`，没有额外build步骤。

## 11. 审核问题的闭环追踪

| 旧设计问题 | 新规范落点 |
|---|---|
| 无deck入口缺失 | 本文§4.1，协议open/phase |
| 页面常驻等同模型在线 | 本文§3.5，协议consumer/client lease |
| 页面seq碰撞、after_seq隐式确认 | 协议§4 UUID/服务seq/认领/receipt |
| git存在即两端可恢复 | 一致性§4/§8 磁盘快照与浏览器草稿分离 |
| 先看dirty再直接写文件 | 一致性§6–7 工作副本+CAS+发布日志 |
| 内部token静态公开 | 一致性§9 GET/HEAD白名单与两级凭证 |
| hash漏样式/图片 | 一致性§3 原始字节source revision |
| 热加载清批注/迟到保存清dirty | 一致性§8 epoch/generation/草稿 |
| refreshExport仍使用旧manifest | 一致性§8.5 强制重读 |
| 转换双写、烙入自动升级 | 本文§4.3/§7 唯一分发与显式语义 |
| 双启动、新端口重连矛盾 | 一致性§10 进程锁/身份/诚实恢复 |
| payload截断和伪分页 | 协议明确大小限额/完整文件指针/拒绝保稿 |
| 手写MCP低估协议工作 | 官方SDK，P0验证取消与真实I/O |
| 只小fixture正常路径验收 | 验收L0–L3、54页、故障/并发/安全/性能矩阵 |
| 90秒lease误杀53页processing | 本文§3.5/§4.4，协议§3–4，一致性§6.4/§7.3 |
| lease-expiry未唤醒SSE | 协议§4/§8，一致性§6.4/§8.4 |
| 最新pending遮住旧recoverable brief | 本文§4.1，协议§7.7/§8，一致性§8.4 |

既有公共接口与实现证据在执行计划中登记；本轮修订已同步代码、技能、eval 与定向验收。本文仍是设计边界，不以设计文字或定向自动测试替代真实宿主、完整回归或人工测试；当前仅可声称记录中明确执行的范围通过。
