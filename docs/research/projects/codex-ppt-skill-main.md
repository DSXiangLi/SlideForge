# codex-ppt-skill-main 深度调研

> 一行定位：整页 AI 生图（gpt-image-2）拼装的图片式 PPTX 生成技能，以门禁式工作流和脚本化状态机保证流程可控 · 来源：source/codex-ppt-skill-main/ · 调研日期 2026-09-17 · 索引：../source-survey.md

## 1. 定位与产物形态

产物是**整页图片式 PPTX**：每页幻灯片是一张由图像模型生成的完整 16:9 PNG，本地脚本 `assemble_ppt.py` 把图片全幅贴进空白版式组装成 `.pptx`（source/codex-ppt-skill-main/codex-ppt-skill-main/skills/codex-ppt/SKILL.md:30；组装逻辑见 scripts/assemble_ppt.py:272-289，空白版式 `slide_layouts[6]`、`add_picture(left=0, top=0, width=slide_width, height=slide_height)`）。幻灯片尺寸固定为 10×5.625 英寸（16:9）或 10×7.5（4:3）（assemble_ppt.py:242-247）。

它对自身边界说得非常直白："Do not use it when every textbox, chart, or shape must remain separately editable"（SKILL.md:32）。作者的设计文档解释了为什么主动放弃可编辑性：图片式 PPT 视觉统一性更好，而把"生成"与"转可编辑"耦合会让流程"更重、更慢、更贵、更难控"，因此拆成两个 skill（docs/design.md:16-27），可编辑化由姊妹项目 image-to-editable-ppt-skill 事后转换（README.md 温馨提示段）。

作者的核心主张是"AI 做 PPT 最重要的不是快，而是流程可控"（docs/design.md:5），整个技能围绕这个主张构建：六步门禁流程（读材料→大纲确认→风格确认→样张确认→批量生成→组装），宁可复杂也不做"点一下出 20 页"（docs/design.md:41）。README 还坦承这种通用性带来冗余，并建议用户"走通常用路线后让 AI 帮你改掉这个 skill、把偏好固定下来"（README.md"温馨提示"之后段落）。

## 2. 方案详解

### 2.1 质量保障与校验：门禁 + 状态机 + 溯源脚本

这是该项目投入最大的能力域，分三层。

**第一层：人工确认门禁。** 七个阶段、四道用户批准门（大纲→风格→后端→样张），批准前禁止创建任何下游产物（`deck_spec.json`、`prompts/`、最终图、pptx）；确需内部草稿必须用 `.draft.` 文件名并明示非正式（docs/workflow-gates-and-progress.md:7-24）。"完成"必须由真实文件或脚本记录的状态证明，聊天里说完成不算（workflow-gates-and-progress.md:46；SKILL.md:62）。

**第二层：样张即风格锚。** 大纲、风格、后端全部确认后，**只生成一页**代表性内容页（刻意避开封面，因为封面不能代表内容页节奏）作为样张，用户确认"视觉风格、字排、版式密度、中文质量"后才放行批量（docs/outline-style-and-sample.md:113-126）。样张直接以最终文件名 `origin_image/slide_XX.png` 保存，批准后就是正式页，不另存 `sample_slide.png`——因为组装脚本只认 `slide_XX` 命名（outline-style-and-sample.md:126；assemble_ppt.py:58-59 的正则过滤）。批准后把 `sample_generation_method`（后端/工具/模式/尺寸/输入图准备方式/handoff 规则）记入 `deck_spec.json`，作为所有子代理必须复现的契约（outline-style-and-sample.md:128-137）。

**第三层：脚本化状态机与强制溯源。** 批量阶段不用提示词规约，而是用一组 Python 脚本把流程钉死：

- `prepare_slide_prompts.py` 把 `deck_spec.json` 确定性地展开为每页一个自包含 JSON 任务（脚本 docstring 明示 "It does not call an image model"，scripts/prepare_slide_prompts.py:4-6），每个任务内嵌 `generation_contract`：`forbidden_final_image_methods` 列出 Pillow、SVG/HTML/CSS 截图、python-pptx 排版、手工合成覆盖层等"更便宜的路径"（prepare_slide_prompts.py:445-455）。
- 状态机五态：`pending / dispatched / recorded / accepted / blocked`（scripts/slide_run_state.py:18-20），所有状态读写走文件锁（`locked_json`，slide_run_state.py:113-114），"Slide dispatch and result state must be recorded with the bundled scripts. Chat messages alone do not make a slide dispatched or complete"（SKILL.md:46）。
- `record_slide_result.py` 在记录结果时做**后端黑名单校验**：`FORBIDDEN_BACKEND_TERMS = ("pillow", "html", "svg", "canvas", "python-pptx", "pptxgenjs", "manual", "script render")`（record_slide_result.py:21-30），backend 名不匹配样张生成方法直接报错 "Backend mismatch"（record_slide_result.py:119），并记录源图与最终图的 sha256 作为溯源证据（record_slide_result.py:164-169）。
- 阻塞是正式状态：子代理用不了指定后端就记 `blocker` 并停下报告，**禁止**降级为低质量替代（SKILL.md:47；prompts/slide-worker.md:37-38）。

**组装前 QA 靠人/AI 目检**：逐页检查文字可读不乱码、内容对得上大纲、标题要点不截断、风格一致、无意外页码、无重叠；严重问题收紧提示词重生，局部问题用后端 edit 能力修（docs/project-assembly-and-reporting.md:34-45）。没有任何像素级自动测量——因为产物是位图，唯一能"测"的就是看图。

**并行子代理是强制项**：样张批准后，只要运行时能起子代理就必须一页一个 worker 并行生成，不能为方便而串行；父代理独占编排、状态记录、QA 与组装，子代理只读自己的任务文件、只回传"图路径 + 后端 + 一句 QA 备注"，不得碰 `outline.md`/`deck_spec.json`/`origin_image/`（SKILL.md:124-130；docs/slide-generation-and-subagents.md:127-160）。跨页语义靠父代理在派发前把 `deck_context`（deck 级概念：核心论点、术语表、编年）和 `local_context`（页级事实）展开写进任务包，"The goal is not to make subagents validate missing context... hand each worker a complete enough task packet"（slide-generation-and-subagents.md:45-51）。

### 2.2 主题与视觉语言：自包含 JSON 风格简报

内置 12 套风格（references/ 下 12 个 .md，清单见 docs/outline-style-and-sample.md:84-97），每套是**同构的自包含 JSON 风格简报**，字段固定：`style_name / best_for / visual_direction / canvas / color_palette / typography / layout_patterns / layout_usage_rule / layout_blueprints / visual_elements(allowed/avoid) / image_treatment / rendering_constraints`（结构范本见 docs/style-library.md:80-140；实例见 references/麦肯锡风格.md:12-119）。

三个值得细看的机制：

1. **"风格是系统，不是模板"**——风格文件稳定的是配色、字体气质、纹理、图标语言、情绪，版式按页角色变化；`layout_blueprints` 只是"候选起点"（docs/outline-style-and-sample.md:82："Treat each reference as a style system... layout_blueprints are candidate starting points only. Do not apply the same blueprint to every slide"）。
2. **枚举项附量化验收标准**。以麦肯锡风为例，标题/章节/观点页的硬约束是"1 个巨型重构主标题、1 个完整小标题、2-4 个英文标签、1 个主导隐喻"，同时"禁止 5 个以上模块、3 个以上图表"；分析页"3-6 个主模块、1 个核心大结构"，"禁止 8 个以上模块"（references/麦肯锡风格.md:108-111）。这正是我们元原则"枚举必须附规则与验收标准"的现成范本。麦肯锡风还带一张**隐喻匹配表**：漏斗=转化筛选、飞轮=增长循环、断层线=结构变化……"choose exactly one most accurate dominant metaphor"（麦肯锡风格.md:51-52）。
3. **风格库可用户扩展**。用户风格存 `~/.codex-ppt-skill/references/`（skill 安装目录之外，升级不丢），目录扫描自动发现、同名覆盖内置；保存时禁止写入用户私有内容、禁止依赖外部文件——"the style file must be self-contained"（docs/style-library.md:7、49-54、144-146；outline-style-and-sample.md:76-78）。从参考材料抽取风格时禁止从 XML/元数据推断，必须先渲染成页面图像再"看"（outline-style-and-sample.md:58）。

风格选择环节给用户 2-3 个具体方向并标推荐（outline-style-and-sample.md:62-69、101-111），且官方文档站配了 12 张风格预览图（assets/style-previews/*.png，docs/styles.md 的对照表）。CHANGELOG 显示作者在持续把风格从"固定版式处方"改写为"内容驱动的视觉指导"（0.5.5：党政红、教学课件风去掉了固定模块数与卡片网格假设，CHANGELOG.md "0.5.5/Improvements"）。

### 2.3 密度与字排：密度绑在风格里，按页角色分档

没有 deck 级的密度双档决策。密度是每套风格内部、按页角色给出的定性描述：麦肯锡风"标题/章节/观点页低密度强留白，分析/框架/流程页中密度"（麦肯锡风格.md:23）；科研答辩风"medium-high to high"（references/科研答辩风.md:22）；电子墨水杂志风"moderate to low"（references/电子墨水杂志风.md:23）。字排完全没有像素/字号规格——标题层级、字体个性只以散文描述交给图像模型（如麦肯锡风 typography 字段，麦肯锡风格.md:32-37），质量兜底只有一句"render all Chinese text exactly, clearly, and without garbled characters"（docs/slide-generation-and-subagents.md:105、220）。溢出概念不存在：装不下就靠原则"split across more slides instead of crowding one slide"（docs/project-assembly-and-reporting.md:150）。

### 2.4 叙事方法论

大纲是门禁产物，每页字段固定：页号、标题、3-5 要点、可选视觉 idea、**布局角色**（封面/议程/章节/概念/流程/对比/时间线/数据证据/架构/案例/总结/Q&A 共 12 种）、必需源图及其角色（docs/outline-style-and-sample.md:9-16）。给了推荐叙事弧（封面→问题→3-7 页主体→收束，outline-style-and-sample.md:26-33）。`speech.md` 演讲稿被当作设计对象：先选**交付风格**（技术讲解/论文研读/产品路演/培训工作坊/高管汇报共 5 种），交付风格塑造措辞与节奏而不只是标签；中文 deck 每页 150-400 字；要求"先抛结论再讲细节""按观众看图顺序讲""禁止『本页主要介绍了』式 AI 腔"（docs/project-assembly-and-reporting.md:51-85）。组装脚本按 `## Slide N` 标题把讲稿写进 pptx 备注（assemble_ppt.py:80-120）。

### 2.5 图片策略：严格输入资产协议（无占位图概念）

用户提供的论文图/实验图/截图/logo 是"strict input asset，不是风格灵感"（docs/user-supplied-assets.md:5）。机制要点：

- 素材放 `{deck}/assets/figures|logos/`，与产物目录 `origin_image/` 严格分离（user-supplied-assets.md:7-18）。
- 大纲里用 **Markdown 图片语法**列出所需图，让用户在大纲评审时**可视化确认图-页映射**（outline-style-and-sample.md:35-50）；`prepare_slide_prompts.py` 用正则把同一语法解析成结构化 `input_images`（含 role 与 fidelity 字段）（prepare_slide_prompts.py:55-69、84-119）。
- 保真规则："Do not ask the model to 'redraw', 'recreate', 'imagine', or 'generate a similar chart'"，要求保留数据、坐标轴、标签、图例、颜色（user-supplied-assets.md:27-28）；生成的 prompt 里自动注入 "Input Image Handling Rules"（prepare_slide_prompts.py:250-257）。
- 批准的样张图会作为 "style-only reference" 注入每个非样张任务（"Match its palette... Do not copy its exact layout"，prepare_slide_prompts.py:242-248）。
- 透明背景用色键生成 + `scripts/remove_chroma_key.py` 本地抠除的迂回方案（docs/cli-api-fallback.md:68-73）。

**没有图片占位概念**：图要么是 AI 整页生成的一部分，要么是用户必须提供的严格输入。换图 = 重生或 edit 该页，不存在"替换同名文件即换图"。

### 2.6 图表与信息图

无独立图表系统。信息图/图表通过两个途径产生：风格文件的 `layout_blueprints` + 隐喻库指导图像模型"画"出来（如麦肯锡风的 2x2 矩阵、价值链、五力蓝图，麦肯锡风格.md:86-96）；或用户数据图以 strict input asset 保真嵌入。所有图中文字都是位图的一部分。

### 2.7 动效

完全不存在（对 references/、docs/、scripts/ 全文检索 animation/motion/动效 零命中）。整页位图的产物形态决定了这一点——它的目标是静态演示文稿，合理，但与我们标准②根本不兼容。

### 2.8 可编辑性与契约

明确放弃（见 §1）。产物内唯一的"契约"是文件命名约定（`slide_XX.png` 零填充两位序号，assemble_ppt.py:59；docs/slide-generation-and-subagents.md:212-218）与 `speech.md` 的 `## Slide N` 标题映射——服务的是组装脚本，不是编辑器。

### 2.9 工程化与防漂移

除 §2.1 的状态机外还有几处值得记录：

- **SKILL.md 是编排合同，细节全部外置**：158 行的 SKILL.md 每条工作流步骤都带"Before X, read `docs/Y.md`"的强制阅读协议（SKILL.md:38-39 及 13 步工作流），8 个 docs 文件每个开头都写清"Read this before..."的触发条件——按需加载有明确契约，比无差别预读克制。
- **共享运行时**：脚本统一跑在 `~/.codex-ppt-skill/.venv`，`codex_ppt_runtime.py bootstrap/doctor` 负责环境初始化与 API 自检，且明示"内部步骤，不要让用户跑"（docs/project-assembly-and-reporting.md:99-107）。
- **后端锁定**：后端确认后不可更换，子代理不得为方便切换（SKILL.md:44）；CLI fallback 默认 2560x1440 中质量（兼顾文字清晰度与 gpt-image-2 像素上限，docs/cli-api-fallback.md:51-53）。

## 3. 辩证评估（对照七条最优标准）

**① 密度双档 + 比 guizang 更有设计感。** 设计感上限极高：图像模型能做出 HTML/CSS 很难做的质感——纸纹、手绘笔触、重构字体、艺术化隐喻（麦肯锡风的"typographic architecture"），12 套策展风格 + 风格预览图 + 样张门禁构成完整的审美保障链。密度处理精细但是**定性的、绑死在风格里按页角色分档**（§2.3），没有给用户"高/低文字密度"的全局双档选择权；且中文字排质量完全押注 gpt-image-2 的能力与运气，乱码靠 QA 目检兜底，不可复现、不可测量。对我们而言：它的风格简报结构（§2.2）和隐喻匹配表可以直接学，但"图像模型自由发挥字排"这条路我们走不了也不需要走。

**② 动效丰富度可调。** 零覆盖（§2.7）。在它的目标场景（静态 pptx 交付）下这是自洽的，对我们的标准②完全无借鉴也无冲突。

**③ 复杂 fancy 信息图。** 它"支持"任意复杂信息图的方式是让图像模型画——上限高、一致性差、不可编辑。真正可迁移的是**组织知识的方式**而非产物：`layout_blueprints` 用语义化 position/count/labels 描述构图骨架（麦肯锡风格.md:55-96），隐喻匹配表把"内容关系→视觉隐喻"做成可查映射（麦肯锡风格.md:51-52）。这印证了我们 components.md"内容关系→构图骨架"选型的方向，且提供了比我们更细的枚举写法示范。

**④ 复杂标注、交互动效、图表覆盖。** 标注语言确实有深度：十字线、测量线、微标签、节点坐标等"精准标注系统"写进了风格枚举（麦肯锡风格.md:42-49、98）。交互为零。图表靠生图或用户供图保真，没有数据驱动的图表系统。覆盖广度的代价是所有这些都锁死在位图里。

**⑤ 图片占位。** 完全缺失，且是哲学层面的相反：它的图片要么是 AI 生成的整页，要么是"strict input asset，禁止重画"的用户供图（§2.5）。"占位图即换图指南"的概念在它的形态里没有存在理由——图就是页，页就是图。

**⑥ 双图片模式 + assets/ 落盘。** 只有半个模式 a：AI 自主绘图，但粒度是**整页**而非插画级配图。模式 b（纯 HTML/CSS 视觉）被明确列为 failure mode（SKILL.md:43）。assets/ 目录概念它有，但角色相反——是**输入**素材目录（`{deck}/assets/figures|logos/`），不是产物交付的可替换资产目录。用户在编辑器里换图这件事不存在；换图意味着带着 strict input asset 重新走生图流程。

**⑦ 文字就地可编辑、可批注。** 明确放弃且自洽（SKILL.md:32；design.md 的两 skill 拆分论证）。这是它与我们目标最根本的分歧：它用"事后另一个 skill 转可编辑"来兜底，我们则把可编辑性作为产物的第一公民。它为这个选择付出的隐性代价是：任何文字错误（哪怕一个字乱码）都要整页重生或图像级 edit（project-assembly-and-reporting.md:45），修正成本是我们的几十倍。

**元原则对照。** 该项目是"原则突出、枚举谨慎"的优等生：SKILL.md 只留编排合同与硬约束，枚举集中在自包含、可扩展、带验收标准的风格文件里；用户风格库的"目录扫描发现、同名覆盖、禁止外部依赖"（§2.2）是枚举可扩展性的工程范本。CHANGELOG 里"把固定版式处方改写为内容驱动指导"（0.5.5）说明作者自己也在从枚举向原则收敛。可挑剔处：13 步工作流每步都挂"先读某 doc"的强制协议，遵循成本不低；这是它兼容多 agent 环境、多后端路线的代价（README 自述"复杂也会带来不稳定性或者冗余性"）。

## 4. 结论：拿什么 / 不拿什么 / 与最优方案的差距

### 拿什么

1. **样张门禁 + 样张即风格锚**（§2.1 第二层）：先冻结一页视觉基准再批量，且把样张的生成方法固化为所有后续页面必须复现的契约。对我们 v1.4 的对应缺口：Step 1-3 冻结了主题 token 和密度，但没有"首页面试生成→用户确认→再批量"的门禁，第一页翻车成本要到 Step 5 渲染校验才暴露。这个机制可以低成本嫁接到我们的工作流。
2. **风格简报的字段结构与量化验收标准**（§2.2）：`layout_usage_rule` + `rendering_constraints` 里"允许 1 主视觉 2-4 标签 / 禁止 5+ 模块"式写法，是我们 themes.md / components.md 枚举项附验收标准的直接范本；隐喻匹配表可营养 components.md 的"内容关系→构图"选型。
3. **脚本强制的反降级契约**（§2.1 第三层）：把"不许偷换成更便宜的路径"从提示词规约升级为可执行校验（后端黑名单 + sha256 溯源）。我们的对应物应该是契约级的静态校验脚本（如检查 data-editable 覆盖率、assets/ 引用合法性），目前 v1.4 只有渲染测量，没有产物结构校验。
4. **演讲稿作为设计对象**（§2.4）：交付风格分档 + 长度指导 + 反 AI 腔禁令。我们若未来支持演讲者备注，这是现成配方。
5. **用户风格库的扩展工程**（§2.2 第 3 点）：目录扫描、同名覆盖、自包含禁令——对我们"预置主题库 + 用户自定义主题"的演进有直接参考价值。

### 不拿什么

- 整页生图的产物形态本身（与标准④⑤⑦根本冲突）；python-pptx 组装链路；多后端/多 agent 兼容的复杂度（README 自己都承认多数人只走一条路）；四道人工确认门的重量（我们已在 source-survey.md 结论中明确不拿门禁式多轮确认，只保留关键的样张级确认即可）；strict input asset 协议的全文（其"禁止重画用户图表"的保真规则可吸收进我们的图片纪律，但不需要整套 Markdown 图片解析管线）。

### 与最优方案的差距（对照 skills/html-pptx/ v1.4 现状）

| 维度 | codex-ppt 的做法 | 我们 v1.4 的现状 | 差距判断 |
|---|---|---|---|
| 视觉基准冻结 | 样张门禁 + 样张图作为每页 style-only 参考 | 主题 token 冻结（SKILL.md Step 2-3），无首页面试确认 | **我们缺一道门禁**，token 冻结挡不住执行层跑偏 |
| 产物校验 | 人/AI 目检位图 | Playwright 像素级测量溢出（SKILL.md Step 5） | **我们更强**：HTML 可测量，位图只能看；但我们缺产物结构（契约标记、assets 引用）的静态校验 |
| 风格枚举质量 | 每风格带量化验收标准与隐喻匹配表 | themes.md 13 套策展主题 + token 推导 | 我们的枚举偏 token 层，缺"规则与验收标准"层，需补齐以符合元原则 |
| 可编辑性 | 明确放弃 | data-editable 契约 + 编辑器（核心优势） | 赛道不同，我们完胜 |
| 状态与证据 | 脚本化五态状态机 + 文件锁 | 无（单 agent 单文件产物，不需要） | 不需要拿 |
| 密度双档 | 风格内按页角色定性分档 | 明确的高/低双档冻结决策（SKILL.md:75） | **我们更贴合标准①**，但我们的密度规则缺少它那种按页角色的细化描述 |

总体判断：codex-ppt 在"流程可控"这个它自己选的目标上做到了六家里最重的工程化，其风格简报的枚举质量是所有参考项目中最符合我们元原则的；但它的产物形态（不可编辑位图）与我们标准④⑤⑦正交，可迁移的是**流程机制与知识组织方式**，不是任何产物代码。
