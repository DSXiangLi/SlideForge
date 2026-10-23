# 设计文档（docs/design/）

> 本目录同时承载待评审设计与已实施模块的持续规格。调研依据在 `../research/`（索引：`../research/source-survey.md`），技能演进分期在 `skill-roadmap.md`，评审驱动的优化分期在 `optimization-roadmap.md`。
> 编辑器↔Agent 桥 v2 截至 2026-10-05 已完成 P0–P3 Linux 自动实现；durable-processing、最终竞态补丁及SSE生命周期反馈修复已落地，`editor.html` v3.5、core 34/34 与定向回归已有 PASS 证据。SSE修复后完整 `run_e2e.py` 为 **55/55 PASS、0 FAIL**，wall time **893.116秒**；此前856.192/856.417/948.520秒记录仅作为历史保留。这些代码回归结果不改变 Kimi formal FAIL 等边界。既有规模/正式性能与54页双轨 convert 证据不变。Kimi 2.1.1 最新正式重跑的核心功能与 cleanup 均通过，但 observation-07 宿主退出超时，故整体 FAIL、formal=false；Codex BLOCKED，真实生图 UNKNOWN，Office/WPS 等人工项未完成。其他文档状态以各行说明及对应 progress 为准。

## 文档地图

| 文档 | 解决的问题 | 对应修订意见 |
|---|---|---|
| `editor-v2.md` | 编辑器 v2 迭代：文字样式编辑（白名单四属性 inline style）、PPT 式目录侧栏、本地 git 版本回滚（tools/edit.py 伴随服务） | 2026-09-18 用户意见（本轮已实施） |
| `iteration-plan.md` | v2 迭代排期：A 编辑器 v2 → B 主题 Schema → C 动效 v2 → D 信息图 v2 → E 插画管线 → F/G 上下兼容 | 2026-09-18 开工计划 |
| `theme-schema.md` | 主题库从无 schema 的惯例对齐，升级为显式 Schema：必填核心 + 可选字段组 + focus 机制（重点/辅助项）+ 缺省推导规则 | 意见 1（迭代 B 已实施） |
| `motion-system.md` | 拆字类动效与就地编辑的共存方案（运行时拆分）；motion_gudie 三原理六原则入库为动效规范 v2 | 意见 2 + `../research/motion_gudie.md`（迭代 C 已实施） |
| `infographic-system.md` | 信息图从 12 个平铺组件升级为"结构族 × Item 皮肤 × 主题"的正交组合衍生模型（借鉴 antv-infographic 架构，不引入库） | 意见 3（迭代 D 已实施） |
| `illustration-pipeline.md` | AI 生图插画模式：内容验收后的统一插画补齐 pass + 图片槽位契约 + 反降级校验 | 意见 6（迭代 E 已实施） |
| `compat-roadmap.md` | 未来规划：向上兼容（页面级全图化：HTML 截图 / AI 重绘）与向下兼容（html2pptx）的形态、契约与排序 | 意见 7 |
| `visual-depth.md` | 视觉纵深：归藏高级感 8 要素落位、信息图/图表组件库（画廊+配方双形态）、动效词汇库 8 族与五层启用矩阵 | 2026-09-19 v2 效果诊断 + 两轮深潜调研（F1–F6 已实施完毕） |
| `handover-theme-differentiation.md` | **session 交接文档**：进度快照 + 用户验收 comment + baoyu-design 补充调研 + 主题差异化/想象层的独立思考（七层表达力栈、隐喻库、世界采样构思法、G–J 期路线） | 2026-09-19 用户验收 comment |
| `theme-expression-stack.md` | G+H 期设计：主题 = 七层表达力栈（L1–L7 ↔ G0–G9）；骨架 v6 主题 CSS 槽位；两级主题架构（9 重主题 + 配色变体，16 纯调色板主题诚实合并）；两两七层 diff ≥3 的机器门槛；隐喻库 + 呈现发散步 | handover §5 路线（G/H/I/J 全部实施完毕） |
| `theme-e12-neobrutalism.md` | E12 商务粗野入库：cmb-retail-v3 deck 级定制主题的回灌蒸馏——策展五色（变体即五色）+ 粗墨描边 + 硬偏移投影 + 直角平面卡；与 E6 孟菲斯的 ≥4 层分化；章节级 data-hue 色相轮转记为 deck 级玩法（不进 G9 css 白名单） | 2026-09-30 用户验收 v3 后批准入库（已实施，sync-themes 校验 + T18 全绿） |
| `high-density-containers.md` | K 期：高密度表达三件套——文本容器层（components.md §13 六型 + 四层字阶纪律）、章节跳转导航（skeleton v7：data-chapter/nav-link/数字键）、动效编排纪律吸收（mend-bar 双态修复条 + data-rotate 轮转高亮 + 内容→动效对照表） | 2026-09-20 用户验收意见（高密度测试缺口 + demo1 动效复盘） |
| `tri-form-architecture.md` | 三形态架构总览：HTML（唯一真相）/ 整页生图（视觉上限）/ PPTX（单向交付快照）；翻转统一动词；**转换即技能**红线；manifest + content-hash 公共地基；防幻觉三硬规则 | 2026-09-21 上下兼容两轮设计讨论（M1 已实现，T23） |
| `page-render-mode.md` | 子技能 A：整页生图烙入模式——与插画模式的边界（页内槽位 vs 整页）、源层保留结构（契约 v7）、HTML 样张锚 + 确定性指令编译、代表页审批闸门、stale 重烙 | 同上（M2 已实现，T24） |
| `pptx-export-svg.md` | 子技能 B：HTML→PDF→SVG→PPTX 矢量管线（浏览器即编译器、文字转曲、svgBlip+PNG 双写）；字体/布局稳定性四道防线（字体随档子集化/度量兼容回退/导出渲染门禁/容器余量） | 同上（M3 已实现 T25；C3 起为保真轨 deck-vector.pptx + deck.pdf 直出） |
| `editor-tri-view.md` | 编辑器 v3：三态工作台（编辑/对比/导出）、翻面交互（手势/过场 + 背面三态含黑面空态）+ 并排（默认落定）/滑动分割/差异热区（质检层）、stale 闭环、保真分排序 | 同上（M4 已实现，editor.html v3.0 + T26） |
| `handover-tri-form.md` | **session 交接文档**：三形态翻转设计的进度快照 + 阅读顺序 + 已定决策快照 + M1–M4 任务规划 + 遗留待澄清点——下个 session 从这里读起 | 2026-09-21 设计闭环交接 |
| `pptx-export-editable.md` | 子技能 C：可编辑 PPTX 导出（原生元素轨）——渲染真相 × 契约标记路线（真实分行文本框 wrap=square / 原生 chart XML / 信息图 grpSp 分组 / 复杂视觉烙图兜底 / 字体内嵌 embeddedFontLst）；双轨导出（deck.pptx 可编辑轨主交付 + deck-vector.pptx/deck.pdf 保真轨）；ppt-master 资产借用清单 | 2026-09-22 用户意见（SVG 轨不可编辑≈PDF）+ ppt-master v6.6.0 调研（**C1–C3 已实现**，T25/T27 全绿） |
| `editor-agent-bridge-communication.md` | Agent、MCP stdio代理、Bridge daemon与HTML编辑器的通信导览：MCP直发browser URL与手动CLI bootstrap两条启动链、brainstorming→claim→副本→发布、三种结果、SSE轮换、长任务、冲突与恢复 | 已实施导览；精确协议与一致性单一真相分别见 protocol/consistency 文档 |
| `editor-agent-bridge.md` | 编辑器↔Agent 桥 v2 总览：无 deck 脑暴与已有作品优化；waiting lease 与持久 processing owner 分离；rebuild/resume 恢复；工作副本 CAS 发布 | **P0–P3 与 durable-processing 增量已落地**；processing 不按时钟过期，waiting 仍90秒回收；历史 P4 状态见 `../progress/1002_editor_agent_bridge_plan.md` §11–13 |
| `editor-agent-bridge-protocol.md` | 桥 v2 公共契约：五 MCP 工具、23个公开HTTP路由/7事件、processing 显式终止、retry `rebuild|resume`、全状态 SSE notify、brief 状态优先恢复、await 1/3600/3600 秒 | 协议修订与最终竞态补丁已实现并通过 core 34/34、定向回归及完整 `run_e2e.py` 55/55 PASS（0 FAIL，856.192秒）；前一轮856.417秒与更早948.520秒仅作历史；只代表代码回归，一小时宿主等待未实跑，Kimi formal 仍 FAIL、Codex BLOCKED |
| `editor-agent-bridge-consistency.md` | 受管 bundle、源/导出 revision、Git 专用 ref、seal/CAS/journal 恢复、resume 风险、草稿/请求恢复排序、路径安全与容量 | resume 真实恢复已验证完整性/base/publication/无 writer 门禁与旧 attempt fence；完整失败矩阵及人工项边界见 `../test_acceptance/editor-agent-bridge.md` §16 |
| `imagegen-v2.md` | AI 生图体验整体优化：现状盘点（六诉求四已存在）+ 八缺口 P0–P2 分期 + D1–D3 风格圣经试点 + v4 升维转向（内容锚"只内容与配色" + 六维升维手段） | 2026-10-06 用户意见（**已实施**，E 组用户目检通过；验收证据 `../test_acceptance/imagegen-v2-g8-real-imagegen.md`，实录 `../progress/1007_imagegen_v2.md`） |
| `g7-resolution-floor-scope.md` | G7 绝对分辨率下限的**适用范围**：它是生成侧纪律（placeholder/generated 硬错误），`uploaded` 真实素材豁免为告警——真实素材要求"原样落盘"，放大它等于伪造来源 | 2026-10-21 用户裁决（**已实施**：check-images 分流 + 契约 v8.2 + T16 双断言；触发见 `../test_acceptance/mcp-apps-upgrade.md` §2.6.1） |
| `theme-optical-axes.md` | 主题光学轴扩展（J 期）：全库手法量化盘点（阴影/玻璃/发光/平滑渐变整格空缺）→ 六轴第一性原理框架 → F 系「光与纵深」三主题（F1 浮光玻璃/F2 霓虹夜行/F3 暮色长镜）+ C3/E5 名实不符升级 + 手法纪律条款 | 2026-10-07 用户观察与方向批准（已实施，sync-themes 24 主题全绿 + sampler/gallery 截图证据） |
| `theme-multi-hue.md` | 多色彩主题体系（J2 期）：G1 多色扩展 schema（accent-2/3、palette-N、hl-N + on-color 配对强制）→ E1/E4/E6 名实不符升级（双墨辊套印/三原色形色对应/糖果四色轮转）→ G 系「色彩结构」四主题（翡翠年鉴/腮红荧光笔/陶土印刷/靛墨黄页）→ theme-proving 验收 deck（每主题 8 页型 + T34） | 2026-10-08 用户三轮方向确认（多色非开关、落层地图、配色即风格）后批准实施 |
| `editor-structural-editing.md` | 编辑器结构编辑（M1'–M2'）：undo/redo 命令栈地基 + 页级删除/复制/隐藏 + 块级删除（块解析规则 + 守卫清单 + 悬停预览）+ 图片重置占位；哲学 = AI 构图、人删减纠错替换；自由拖动/resize/新增文本框明确不做 | 2026-10-13 基于 `../research/editor-structural-editing.md` 调研与需求反思（**待评审**） |
| `handover-theme-material-compositing.md` | **session 交接文档**：主题材料合成优化试点——D2 柔光暗房材料升级（film-grain/light-leak/aged-fade）+ D4 黄铜年代新建（engraved-line/halftone-dots/aged-fade/paper-fiber），用户验收后推进全量 | 2026-10-15 外部视觉风格参考深度对比 → 材料合成优化方向 |
| `brief-dynamic-brainstorming.md` | 动态脑暴（Briefing v2）：选项随输入动态生成——单段注入式（agent 消化对话上下文生成 brief.options JSON → open_editor 可选参数注入 → 页面动态渲染，brief.submitted 冻结不变）、维度池+缺口驱动+prefilled 折叠、主题封面预览卡、静态问卷兜底；五工具与页面无 AI 红线不动 | 2026-10-14 用户反馈"脑暴选项与输入无关"（**待评审**） |
| `mcp-bidirectional-research.md` | MCP 双向通信调研：MCP 协议单向性约束分析、dsh 插件模式（Cordis waterfall + slots）/ Cowart ext-apps widget / 本项目 Bridge 三范式对比、开源生态方案扫描（MCP Elicitation/Notifications/Tasks/ext-apps、LangGraph interrupt/resume、confirm-mcp 轮询）、Kimi Code 扩展能力现状、四条演进路线（短期超时优化 → 状态简化 → ext-apps 根本解 → 插件打包） | 2026-10-14 MCP `await_intent` 超时问题触发的系统性调研（**待评审**） |
| `ext-apps-dual-track.md` | ext-apps 双轨迁移：传输层可替换、状态机不动——宿主支持 ext-apps 走轨 A（宿主内 widget：`ui/message` 敲门 + 非阻塞 take_intent 消除超时、凭证/SSE/心跳/lease 整层删除），不支持走轨 B（现有 daemon 不动）；BridgeCore 进程内嵌复用、editor.html 第四态、window.pptxMcp 注入门面、assets 经 callServerTool 换 data URI、P1–P5 分期 | 2026-10-15 基于 mcp-bidirectional-research 路线 B + 官方 ext-apps 2.0.3 源码精读 + Cowart 解剖（**已取代**，见 `mcp-apps-upgrade.md`） |
| `mcp-apps-upgrade.md` | **MCP Apps 升级设计（真实宿主实证版，10-20 三轮）**：① editor.html 交互能力全清单（五类 A–E 具名 21 项 + 键盘手势全集 + 出站/入站协议 + 沙箱存活判定）；② 轨道判定改为"能力声明（乐观提示）+ `attach_view`/心跳实证"双信号——实测 Kimi Code 2.2.0 三层不支持、SproutHarness 能渲染却不声明扩展，故声明既非充分也非必要；③ 沙箱能力矩阵 Playwright 实测（`srcdoc`/相对图/`crypto.subtle` 可用；localStorage/IndexedDB/`fetch` 同源全废；"存在性检测"是伪检测）；④ 五工具不变、`await_intent` 增仲裁相位（**自解除**，轨 B 零时延回退）、13 个 `visibility:["app"]` 工具组（⭐根级+`ui` 双写，宿主 N15 未修）、`bridge_dispatch.py` 直连层；⑤ 宿主能力面按 10-20 逐项对齐（`ui/message` 有用户确认闸门 / `update-model-context` 在 `startStream` 内随下条用户消息附带 / `download-file` 仅 embedded ≤20MB / `displayMode` 仅 inline、高度上限 1200px）；⑥ **三通道模型**（状态机=待办 / 敲门=触发 / 便条=背景，便条不在提交路径上）；⑦ **§5.10 异步批注与版本并发**——识别出"指令型意图被错误施加写入前置"的双轨共用协议硬伤，**且纠正了设计自身的一处错误**：`intents.base_revision` 是**发布 CAS 基线**不是信息字段，故"指令型跳过校验"必须实现为**归一化**；含死锁时间线、D1–D5 设计、可合并性判据、`active_edit` 便条；⑧ 轨 A `await_intent` 异步化约束、§5.11 对比质检产物载入缺口；⑨ P0–P5 分期、12 条风险、**§9 五项裁决已落**（红线改写 AGENTS.md / 允许锚点指向未落盘内容 / P0.5 先做 / 方案 b 保留为可选优化 / 对比质检懒加载）；⑩ **P0.5 D1+D2 已实施**（`bridge_core.py` + `editor.html` + 6 个测试，core 38→44） | 2026-10-19 初稿 → 2026-10-20 三轮（宿主能力面 / 一致性自查 + 异步批注 / 裁决落地 + P0.5 实施）（**待评审**） |
| `brief-page-split.md` | 脑暴页剥离：从「编辑器浮层」到「可直达的首屏」——实测根因三条（`view` 是装饰性参数 / 脑暴是浮层 / 轨 A 的 `brief_options` 失效）→ 宿主按工具静态 `resourceUri` 取页（C1）+ 每次调用新建 iframe（C2）推出"单工具·首屏分流"→ `view` 三处下发 + `tool-input` 兜底（不落库）、`launchView` 分流、轨 B 可选真拆 `brief.html`、五工具与冻结语义不动 | 2026-10-22 用户反馈"调用工具后脑暴页无法直接打开、要点按钮"；**四路独立评审折入 §15**（7 条硬错误 + 7 条事实修正）（**待评审**） |
| `optimization-roadmap.md` | **评审驱动优化路线图（第 0–6 期）**：把 `../review/2026-10-15_project_review.md` 的 22 个问题条目 + 8 条架构风险全部落到分期——0 止血（回归转绿 + 文档诚实）→ 1 真实验证三连（Office/WPS、付费生图、宿主矩阵）→ 2 上手可达（一键安装 + 英文化）→ 3 编辑诚意（undo + 结构编辑 + 演示模式）→ 4 交付公民 + 品牌适配 → 5 视觉产品化（背景升维三态、感知评审闸、benchmark）→ 6 工程可持续与生态；含现状校准（评审陈述 vs 仓库事实）、追溯矩阵、需用户拍板的四个岔口 | 2026-10-15 外部深度评审 → 2026-10-19 结合仓库现状拆分（**待评审**） |

## 决策速览

1. **主题 Schema**：色与字是必填核心，质感/形态/动效亲和/插画风格等是可选字段组；每个主题声明 1–2 个 focus 字段组作为设计感来源，其余走集中维护的缺省推导——"不覆盖全字段也完整"。
2. **拆字不禁令**：产物文件中的文字永远是纯文本节点，拆字由骨架 JS 在运行时执行；编辑器看到的永远是纯文本，编辑契约零改动，无 JS/reduced-motion 天然降级。
3. **信息图组合衍生**：结构族（有限枚举）× Item 皮肤（有限枚举）× 参数变体（密度/方向/项数）= 大组合空间；数据字段与结构族硬约定防止 AI 乱填；新族/新皮肤入库走 `../research/sota-visual-languages.md` 七件规范。
4. **插画管线**：占位图 →（内容验收）→ AI 统一补齐插画 →（用户随时）上传替换，三级供给链共享同一条 `assets/` 资产契约；声明插画模式必须真实落盘（可静态校验的反降级）。
5. **上下兼容**：HTML 永远是唯一事实源与起点；全图化和 pptx 导出都是**导出态分支**，以独立工具承载，不污染产物纯净性。（2026-09-21 起升级为实施级设计：见 `tri-form-architecture.md` 系列四文档；原 `compat-roadmap.md` 保留为历史记录。）
6. **三形态与翻转**：HTML = 唯一真相源，整页生图与 PPTX 导出是两种"翻转"（单向、逐字引用、hash 失效检测）；**转换是技能不是后端**——编辑器只消费 `export/` 产物；PPTX 保真走浏览器渲染→PDF→SVG 转录路线，字体随 deck 子集化内嵌根治跨机版式漂移。

## 共同纪律

- 所有枚举型资产（主题、信息图结构族、Item 皮肤、动效 recipe）入库必须满足 `../research/sota-visual-languages.md` 的七件结构与三级验收。
- 凡涉及编辑器与生成器之间的约定，先改 `skills/html-pptx/references/editing-contract.md` 再改生成侧，契约不后补。
