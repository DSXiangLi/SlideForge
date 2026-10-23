# ppt-master 深度调研

> 一句话定位：把素材变成**原生可编辑 PPTX** 的路由式工作流技能（SVG 作为 AI 书写层，脚本编译为 DrawingML）· 来源：source/ppt-master/ · 调研日期 2026-09-17 · 索引：../source-survey.md

## 1. 定位与产物形态

ppt-master（v4.8.0，`source/ppt-master/skills/ppt-master/SKILL.md:12`）的自我定位是"chat 驱动的开源工作流，先理顺论证，再设计并产出**真正的、可编辑的 PowerPoint**——不是幻灯片图片，也不是一层薄薄的可编辑皮"（`source/ppt-master/docs/project-positioning.md:15`）。它的核心差异化轴是 **native depth**：产物里包含真实的 `p:sldMaster`/`p:sldLayout`、187 种 DrawingML 预设形状、原生图表/表格（可选）、OMML 公式、切换/动画/旁白配音等 PowerPoint 原生对象模型（`source/ppt-master/docs/why-ppt-master.md` 第 1 节）。

产物形态与运行方式：

- **交付物是 `.pptx` 文件**（`exports/<project>_<timestamp>.pptx`），外加项目工作区：`sources/`、`analysis/`、`images/`、`svg_output/`（手写源）、`svg_final/`（派生预览）、`design_spec.md`、`spec_lock.md`、`validation/` 等（`source/ppt-master/skills/ppt-master/references/artifact-ownership.md:23-67`）。
- **技术路线**：AI 手写受约束的 SVG（每页一个文件），脚本 `svg_to_pptx.py` 把 SVG 编译成 DrawingML。选择 SVG 的理由是"SVG 和 DrawingML 是同一种东西——绝对坐标 2D 矢量格式，转换是方言翻译而非格式搭桥"（`docs/why-ppt-master.md` 第 1 节末引用块）。
- **四条互斥顶层路由**：Generate PPTX（含 Image-to-PPTX / Beautify 两个 profile、Default / Quick 两种运行时）、Create Template、Fill Native PPTX、Enhance Native PPTX，由 `workflows/routing.md:29-36` 的路由矩阵确定性裁决，且明令"禁止给用户呈现路由选择菜单"（`workflows/routing.md:25`）。
- 它运行在通用 coding agent 内（Claude Code / Codex / Cursor 等），不是独立应用（`source/ppt-master/AGENTS.md:50-52`）。

**与本项目的本质差异**：它交付二进制 PPTX，我们交付单文件 HTML；它的"可编辑"指 PowerPoint 里的对象级可编辑，我们的"可编辑"指浏览器里就地改字换图。这决定了两者大部分机制不可直接迁移，但**元设计方法**（规则分级、权威归属、条件加载、门禁校验）高度可迁移。

## 2. 方案详解

### 2.1 工程化与防漂移：权威文件制 + 条件加载 + 上下文纪律

这是 ppt-master 对本项目价值最大的域，也是索引已收录方向的细节展开。

**SKILL.md 已瘦身成 92 行纯路由器**（`SKILL.md:21-23`："owns global execution discipline and route selection only"）。值得注意：source-survey.md 称"ppt-master 单文件 700+ 行防御性散文"，但当前 v4.8.0 的 SKILL.md 只有 92 行；体量转移到了 references（`shared-standards-core.md` 703 行、`svg-effects.md` 980 行、`image-generator.md` 813 行），靠条件加载控制上下文成本。该批评在"总规范体量"层面仍成立（workflows+references 的 Markdown 合计超 1.2 万行），但"单文件过载"已不成立。

**权威归属（authority）机制**：几乎每个文件开头声明自己拥有什么、不拥有什么，冲突时谁赢写死在文件里。例：`routing.md:9-11`（"If this file conflicts with a route summary elsewhere… this file wins"）；`canvas-formats.md:56-58` 声明自己是字号锚点的"normative owner"，其他文件"must not infer alternate values"。`artifact-ownership.md:6` 是总纲："Read each fact from its owning artifact. Do not merge multiple channels into a second source of truth."——每个事实只有一个归属渠道（如 `analysis/image_analysis.csv` 是 `images/` 的"再生视图而非持久存储"，`generate-pptx.md:491`），派生产物只允许从 owning 命令重新生成、禁止手工修补（`artifact-ownership.md:101-118` 的 Regeneration Rules 表）。

**规则效力分级**：实际比索引记录的 Hard/Default/Reference 三档更细。词汇层面是 `Hard rule`（全库约 168 处）/ `Default — …（may override when …）` / `Reference — not a constraint` / `Forbidden —`；`shared-standards-core.md:40-45` 明确三者的遵守语义。更细的一层是**确认值五级语义**（`strategist.md:51-59`）：Literal requirement（精确值不可动）/ Semantic requirement（保事实关系，表达可变）/ Identity anchor（保持复现身份稳定，非穷举白名单）/ Reference（可采用、改写、拒绝）/ Permission（允许的边界，无配额）。并配类型提升规则：用户说 *must/only/exactly* 只能把**具名属性**强化为 Literal，"接受 AI 推荐不会把 Reference 提升为 Literal"（`strategist.md:63`）。

**spec/lock 双文件**：`design_spec.md`（人类可读完整设计叙事，结构见 `templates/design_spec_reference.md:21-207`，§I–§X，其中 §IX 是逐页完整简报含 Audience move）与 `spec_lock.md`（机器可读的稳定执行锚点/路由子集）。两者之间有两道保真门禁：Gate 1"活跃决策保真"（spec 必须逐字段匹配最终确认，schema 合法不算过，`strategist.md:594`）、Gate 2"lock 上下文保真"（lock 不得改变身份/丢弃修订/引入新方向，`strategist.md:596`）。实例见 `examples/ppt169_cangzhuo/spec_lock.md`（70 行）：canvas、六色角色、字体角色锚点（body 24 / title 40 / cover_title 80…）、图标库与笔宽、图片清单、`page_rhythm` 逐页节奏标签、禁用清单。

**条件加载（防上下文膨胀）**：所有非核心文件都由"确定性触发器"按需加载，触发表写在 workflow 里（`generate-pptx.md:629-641`，如"有值驱动几何 → 才读 `executor-chart.md`"）。目录分两级：先读 `_index.md` 冻结选用的 id，再只读被选中的详情文件，"Never glob the directory or read an unselected sibling"（`visual-styles/_index.md:20`）。Executor 侧还有上下文有效性策略（`executor-base.md:57-71`：未压缩的活跃上下文直接复用、不轮询文件）与**每 5 页重读一次 spec_lock** 的轻量再锚定（`executor-base.md:128-137`——P05/P10/P15 后重读，纯上下文再锚定，不跑校验不暂停）。

**执行纪律**：串行执行、`⛔ BLOCKING` 门禁必须等用户显式确认、禁止跨阶段打包（`SKILL.md:63-69`）；失败时"修复 owning source 并从路由声明的指针恢复，不得静默降级"（`SKILL.md:69`）。

### 2.2 叙事方法论：Strategist 角色与双阶段确认

Strategist（`references/strategist.md`，625 行）是规划角色，核心机制：

- **双阶段阻塞确认**（`strategist.md:31-39`）：Stage 1 确认"沟通契约"（受众/意图/期望结果/核心信息/交付场景/产物身后事，全是开放散文字段，`strategist.md:81-90`）+ 模板/自由设计选择，且**沟通推荐必须先于任何模板内容产出**（`routing.md:162-167` 的"延迟读模板"硬规则）；Stage 2 才确认完整方案（阅读模式、mode、视觉风格、页数、配色、字体、图标、图片来源、生产机制）。
- **三方向制**：Stage 2 必须先产出三个"完整且明显不同"的整体方案方向，再逐方向投影出 mode/style/配色/字体等字段；每个方向都序列化为 `custom` + 可执行行为散文，固定目录只作保守的底层备选（`strategist.md:39`、`modes/_index.md:61-71`）。禁止为了凑差异而制造"安全/中庸/激进"假三选（`strategist.md:39`）。
- **沟通意图是开放散文，不是枚举**：inform/explain/persuade… 只作提示词，"Never render them as a checkbox list"（`strategist.md:92`）；每个被命名的意图有一张"大纲义务"对照表（`strategist.md:108-120`），且**每一页（含封面/结尾）必须有 Audience move**（受众状态前→后），推不动全局结果的页应该被合并或删除（`strategist.md:602`）。
- **内容发散度**：`content_divergence` 是用户自由填的散文（贴近源文 ↔ 自由重构的谱系），但"再自由也不许编造源外事实"（`strategist.md:100-104`）。
- **事实溯源**：外部事实挂 `sources/*.facts.json` 的稳定 `fact_id`，页面上引用；编造的演示数据必须标 `Data class: scenario` 并在页面上可见标注"情景数据"（`strategist.md:106`、`executor-base.md:167`）。
- **叙事骨架 mode 目录**：5 个 mode（pyramid/narrative/instructional/showcase/briefing），明确定义"mode = 怎么论证，不是沟通目的的分类法"，且给了相邻概念辨析表（`modes/_index.md:36-44`，如 pyramid vs briefing："要落结论"vs"完整铺陈不站队"）。

### 2.3 画布与适配

- 8 种注册画布，`ppt169` = **1280×720**（注意：不是 1920×1080；`canvas-formats.md:26` 明确"同比例的 1920×1080 banner 必须视为不同坐标系"），导出按 `1 SVG px = 9,525 EMU` 量化（`shared-standards-core.md:589-598`）。全部页面共享同一 viewBox，Quick 模式以第一页 SVG 定画布（`shared-standards-core.md:566-568`）。
- 无"响应式适配"概念——画布是固定的，适配发生在 PowerPoint 的显示层。对本项目（固定画布 + transform 缩放）是同构前提。
- **字号起点由画布规格拥有**：`canvas-formats.md:61-67` 按阅读模式给 ppt169 三档正文带（text 18–21 / balanced 22–25 / presentation 28–32，初始值 20/24/32），且声明"这是起点不是下限，低于带外不是校验失败"（`canvas-formats.md:91-98`）。

### 2.4 主题与视觉语言

- **视觉风格目录 18 套**（`visual-styles/_index.md:30-71`）：swiss-minimal、editorial、dark-tech、glassmorphism、zine、ink-wash 等，按 corporate/editorial/expressive/hand-drawn/specialty 分组。**风格文件不含任何 HEX**——"Styles carry NO fixed HEX"，颜色全部来自确认环节 e 的六角色色板；风格只规定"颜色怎么用"（`visual-styles/_index.md:12`）。每个风格详情文件结构统一：形状与装饰 / 字体性格 / 色彩使用纪律 / 质感与海拔 / 配对插画渲染 / 插画倾向（见 `visual-styles/swiss-minimal.md` 全文结构）。
- **配色**：六角色硬约束（background/secondary_bg/primary/accent/secondary_accent/body_text），正文对比度 ≥4.5:1（`strategist.md:168`）；复发的中性角色（surface/grid/scrim 等）按需提升为命名锁行，但"不预测每个页面级 tint"（`strategist.md:172-178`）。
- **模板工作区四类**：Brand（身份）/ Style（可复用的沟通方法+设计方向，无版式）/ Layout（品牌中立的结构）/ Deck（含身份的结构），互斥且选择规则写死（`routing.md:109-126`、`templates/styles/README.md:3-18`）。内置库：17 个品牌（mckinsey/anthropic/huawei…）、12 个 style、7 个 layout、3 个 deck 工作区，发现一律走 `*_index.json`，"Never scan the corresponding directories"（`routing.md:152-160`）。
- **图标**：5 套内置库共约 1.2 万个 SVG（tabler-outline 5138、simple-icons 3675、phosphor-duotone 1518、tabler-filled 1055、chunk-filled 641；实测 `templates/icons/` 各目录计数）。规则：一份 deck 只选一个主风格库，stroke 库锁一种笔宽（1.5/2/3），simple-icons 只在内容真需要品牌标识时使用（`strategist.md:215-223`）；`icon_sync.py` 把选中的图标复制进项目并校验，缺失即重选（`strategist.md:233`）。

### 2.5 密度与字排

- **阅读模式（信息承载轴）**：text（read-close）/ balanced / presentation 三档，决定"意义在页面、视觉、演讲者、备注之间怎么分配"，进而驱动页面语法、粒度、密度、页数推荐（`strategist.md:98`、`strategist.md:541-552` 的对照表）。关键论证："同一份素材做出的 presentation deck 和 text deck 必须在页面语法、页数、单页文字量、视觉负担、节奏上都不同，不只是字号不同"（`strategist.md:558`）。
- **page_rhythm 逐页节奏锁**：每页打 anchor（结构页）/ dense（信息页，基线）/ breathing（低密冲击页，**禁用多卡片网格**）之一，写进 spec_lock，是强制段落（`strategist.md:604`、`executor-base.md:139-153`）；配"全 roster 节奏检查"（章节是否可见重置、同密度长跑是否有意、结尾是否真正降低信息负荷，`strategist.md:606`）。封面必须有具体 hook、结尾不许是空洞的"Thank you"（`strategist.md:607-609`）。
- **字排**：字号全部 px（"PowerPoint 的 pt 是导出结果，不是输入"，`strategist.md:252`）；角色比例表（封面标题 2.5–5×正文 … 脚注 0.5–0.65×，`strategist.md:262-272`）；每个复发角色一个全 deck 锚点、取偶数 px、Executor 单次允许 ±2px 浮动；第三个复现的未声明展示字号会强制回到上游命名角色（`strategist.md:273`、`executor-base.md:117-122`）。行高按角色/密度给起始区间（标题 1.2–1.3×、正文 1.5–1.6×、疏朗页 1.6–2.0×），用 `tspan dy` 书写——`line-height` 无 DrawingML 映射所以禁用（`shared-standards-core.md:625`）。

### 2.6 信息图与图形构造：结构语法 + 原生形状优先

这是它"复杂图形也可编辑"的核心机制。

- **结构语法（executor-structure.md，101 行）**：把定性关系归纳为 6 个原子（order/link/parent/membership/contrast/overlap，`:17-28`）、5 种形状角色（field/node/spine/edge/label/garnish，`:32-41`）、6 个操作（repeat/arrange/transform/connect/region/attach，`:43-50`），构造顺序强制 spine→nodes→connectors→labels→garnish（`:62-76`），并有 8 条验证 rubric（如"Removal：去掉颜色/效果/图标后位置本身仍能传达"，`:88-99`）。**明确禁止结构目录**："never recall or resolve `structure/<key>`"（`:11`）——结构层用语法不用枚举，这是"原则突出、枚举谨慎"的教科书样本。
- **Shape-first 门禁**（`native-shape-authoring.md:41-95`）：先选轮廓再选写法；"矩形/圆不是更初级的视觉层级，仅仅因为 SVG 写法更短"（`:43-46`）；阶梯为 原生预设 → 独立组合 → Boolean 运算 → 自由路径兜底。187 个 DrawingML 预设形状由 `preset_shape_svg.py` 生成紧凑原子片段，元数据禁止手写（`shared-standards-core.md:388-427`："helper-only metadata"）。
- **效果词汇按"视觉任务"组织**：`svg-effects.md` §6.1 的 Visual Job Router 是"诊断出的视觉问题 → 候选技术 → 停止条件"的路由表（`:49-70`），而非效果陈列；明确"无配额，纯构造合法"（`:51-58`）。海拔系统只有 Floor/Resting/Raised/Glow 四级，"一页一个光源方向"（`:332-345`）。构造配方（faux glass、paper cut、Riso 套印偏移、等距切面、halftone…）全部给出"受支持图层的显式构造法"并标注保真度（`:881-934`）。
- **保真度词汇表**（`shared-standards-core.md:31-38`）：`Native-stable` / `Native-normalized` / `Approximate` / `Bake-required` 四级，每种效果的 SVG→PPTX 映射保真度都标注。封闭语法是 fail-closed 的：内联属性白名单（`:108-116`）、结构黑名单（mask/style/class/foreignObject/textPath/@font-face/animate/script/iframe，`:88-103`），未列属性直接被 checker 拒绝。模糊、混合模式、逐像素合成全部 Bake-required（`svg-effects.md:942-954`）。

### 2.7 图表

- **33 种图表表达词汇表**（`templates/charts/chart-vocabulary.md`，每图一个 SVG 构造模板 + `charts_index.json`），按信息关系分 6 组（时间变化/类别比较/目标进度/分布/部分整体…）。文件自我声明"Reference — not a constraint……Zero Chart selections remains valid"（`:1-10`）。表格另有 6 种词汇（`templates/tables/`）。
- **选型与实现分离**：Strategist 只做"信息模型 → 图表族/key"的选型并用 `visualization_recall.py validate` 校验引用合法（`strategist.md:424-441`）；几何、坐标、标签放置全归 Executor（`executor-chart.md`）。
- **Native-ready 双轨**：图表默认导出为 SVG 派生的可编辑形状（跨 PowerPoint/Keynote/WPS 像素一致）；可选 `--native-charts-and-tables` 换成带数据工作簿的原生图表对象——"跨端保真 vs 活数据工作簿，由这份 deck 的用途决定，不被工具锁死"（`docs/why-ppt-master.md` 第 1 节末）。

### 2.8 动效

动效是 PPTX 原生能力（OOXML timing），不是网页动效，但其**动效纪律**高度可迁移：

- **默认关闭**：页面切换默认 fade 0.4s，元素动画默认 none，音效默认 none（`animations.md:44-46`）。理由直给："Auto-firing element builds on every page are an unsolicited 'AI deck' tell"（`animations.md:34-36`）。
- **能力菜单制**：动效不是"一个旋钮"，而是按"这份 deck 需要什么"分发到不同机制：通用入场 `-a auto` / 对象生命周期 sidecar `animations.json` / 旁白同步 / Morph / 环境慢动 / 轮播与数字滚动配方 / kiosk 自动播放 / 音效（`animations.md:8-24`）。
- **Morph 哲学**："没有关键帧时间线；两个普通可编辑静态页之间的差**就是**动画"（`animations.md:19`）——连续动作（推镜、翻转、渐显）必须在写 SVG 页面时就写成相邻两页，导出走 PowerPoint Morph，且可用 `!!key` 强制对象配对（`animations.md:189-245`）。
- **对象动画锚点即分组**：每个逻辑单元一个顶层 `<g id>` 既是语义分组也是动画目标（`shared-standards-core.md:620`）；因此有强制分组纪律（禁止整页一个大 g、禁止一堆散原子、禁止匿名顶层组，`:663-670`）。sidecar 支持 enter/emphasize/move/exit 生命周期、排序、触发器（含 PowerPoint 的"点击某对象触发" `trigger_shape`）、音效（`animations.md:115-177`）。
- **切换选型剧本**：按"页间关系"选切换（同段延续 fade / 方向推进 push / 同对象跨页 morph / 章节开启 reveal…），"never vary transitions for catalog coverage"（`animations.md:293-320`）。

### 2.9 图片策略

- **四种来源 + 占位**：`none` / `provided`（用户提供）/ `ai` / `web` / `placeholder`（延后提供），由 Strategist 在 Stage 2 推荐、用户确认（`strategist.md:297-304`）。"凭证缺失不构成不需要图片的理由"（`strategist.md:308`）。
- **AI 图片管线**（`image-generator.md`，813 行）：20 种渲染风格（vector-illustration/ink-notes/paper-cut…）× 11 种信息图内部骨架类型 × 2 个页面角色（local/hero_page）× 2 种文字政策（none/embedded）。核心硬规则是**文字双层归属**："图内文字只给永远不需要改的词——改一个图内字要重新生图，改一个 SVG 字只要一次击键"（`image-generator.md:29-35`）。提示词必须是"一段连贯散文，禁止 tag soup"（`:163-169`）；科学/医学等领域准确性要求时词数上限解除（`:235-249`）；还有插画 sheet 一次生图切多元素（`slice_images.py`，`:252-258`）。
- **占位与就绪门禁**：`placeholder` 行在 SVG 里是虚线占位框；Step 7 的 Image readiness GATE 要求所有 Needs-Manual 文件到位，"never ship the dashed placeholder"（`generate-pptx.md:792`）。即占位是**流程机制**而非交付物的一部分。
- **网络搜图有完整降级链**：元数据排序 → 候选缩略图视觉评审（`--save-candidates` + 隔离 reviewer）→ 采用页回退 → Needs-Manual（`generate-pptx.md:551-553`）。
- 图片版式有独立模式库（`image-layout-patterns.md`：P1 单图/P2 图作画布+原生叠加/P3 多图 × M1/M2 修饰层）与几何规范（`image-layout-spec.md`：contain/fill/邻接/叠加/网格/加权轨道）。

### 2.10 可编辑性与契约：双层可编辑 + 内置浏览器编辑器

- **第一层：产物在 PowerPoint 里原生可编辑**——这是整个项目的存在理由（见 §1）。"诚实可编辑"是产品承诺：保真度取舍全部显式标注，"output is a draft the user keeps editing, not a sealed final deck"（`docs/project-positioning.md` §2 表）。
- **第二层：内置浏览器 SVG 编辑器**（`scripts/svg_editor/server.py` + `workflows/stages/live-preview.md`）——这是 source-survey.md 完全未收录的重大事实。编辑器双通道（`live-preview.md:40-41`）：
  - **Direct edit**（确定性修改：措辞、颜色、坐标、SVG 属性）：选中元素 → 右侧面板改 → 预览即时更新，点 Apply changes 才写回 `svg_output/`；支持拖拽移动（经 CTM 换算，任意缩放下跟手）、方向键微调（1px/Shift+10px）、右键重叠元素拾取、Ctrl+Z 撤销（连续同学段修改合并为一步），应用历史写 `edits.jsonl`（`live-preview.md:74-78`）。
  - **Annotate**（需要 AI 判断的修改：换图/重排等）：选中元素 → 写自然语言指令 → 以 `data-edit-target` / `data-edit-annotation` 属性标记写回 SVG → 用户回 chat 说"应用注解" → agent 逐条改 SVG、清标记、重新导出 PPTX（`live-preview.md:48-66`）。
  - 重新导出始终是 chat 驱动的——编辑器自己不直接产出最终 PPTX。
- **语义标记契约**：SVG 里的 `data-pptx-*` 族（layer/placeholder/role/bounds/carrier…）是"渲染中立的编译器提示"，克制使用——"不给普通标题、正文、卡片、KPI 加通用内容角色"（`generate-pptx.md:703`、`references/semantic-svg.md`）。

### 2.11 质量保障与校验

- **校验器是重型工程**：`svg_quality_checker.py` 入口背后 `svg_quality/checker.py` 达 7958 行，覆盖 viewBox、图片契约、字体、文本几何、模块边界、预设形状元数据、动画锚点、spec_lock 对齐、图片溯源等 30+ 检查族（`scripts/svg_quality/checker.py:1182-1450` 起的 `check_*` 方法清单）。文本溢出用**逐 run 宽度估算函数**（`estimate_single_line_text_frame_width`，要求 text/font_size/font_family/font_weight/letter_spacing 齐全，`generate-pptx.md:715`）而非渲染测量；模块边界溢出 1px 内忽略、5% 内警告、超 5% 失败（`shared-standards-core.md:631`）。
- **首页门禁（方法样本诊断）**：P01 完成后强制跑 `--stage first-page`，把 P01 当"方法样本"——同类同向问题 ≥2 个 = 方法级偏差，必须在 P02 前归因到权威规则；并输出 `gate-signal: method=… | page-local=… | not-exercised=…` 一行分类（`generate-pptx.md:705-725`）。通过后才不间断生成其余页，禁止中途跑 checker（`:19-22`）。
- **终检 + 修复纪律**：全页完成后一次 `--stage final`；要求"一次性审完整 issue 集 → 一轮合并修改 → 一次复验"，禁止"边修边跑 checker 一次只发现一个问题"（`:727-738`）。warning 全部是建议性的，"如果一个条件真的必须在发布前修复，它就应该被分类为 error"（`:734`）。
- **Token 节约纪律**：checker 成功时只看退出码和摘要，"Do not open or cat the complete JSON report into model context"（`:738`）。
- **导出后校验（postflight）**：`svg_to_pptx.py` 独立要求当前匹配的 final 报告存在且通过，否则退出非零；产物附 `validation/*.report.json`（`generate-pptx.md:860-866`）。
- **视觉自检（opt-in）**：用户显式要求时，`visual_review.py` 把每页渲染成 PNG，派视觉子 agent 按 rubric（H1–H9 硬规则 + 软规则 + don't-touch 清单）逐页检查修复；默认只迭代 1 轮（`references/visual-review.md:10`、`:35-46`、`:111`）。
- **载体回执对照**：终检打印 `[CARRIERS]` 事实摘要，Executor 必须拿它与页面计划对照——"数量和多样性从来不是配额也不是质量证明"，但事实与决策矛盾（如计划采用的主图沦为次要小框）时必须修复（`executor-base.md:179-188`）。

## 3. 辩证评估（对照七条最优标准）

**① 高/低文字密度双档 + 比 guizang 更有设计感。**
它做到的部分：密度机制比我们目前更精细——阅读模式三档（`strategist.md:541-552`）× page_rhythm 三标签（`executor-base.md:139-153`）× 画布字号带（`canvas-formats.md:63-67`）三层正交，且明确"密度差异必须体现在页面语法/页数/节奏上，不只是字号"（`strategist.md:558`）。设计感上，18 风格目录 + job-first 效果词汇 + 结构语法，理论上能产出远超 guizang 两风格的变化面。
它缺/不适配的部分：它的视觉上限被 DrawingML 映射**主动压低**——混合模式、背景模糊、逐像素合成、复杂滤镜全部 Bake-required 或禁止（`svg-effects.md:942-954`、黑名单 `shared-standards-core.md:88-103`）。这对它的目标（PPTX 原生可编辑）是完全合理的取舍，但我们的画布是浏览器，CSS 全量能力可用；照搬它的效果词汇等于自缚手脚。另外它没有"比 guizang 更有设计感"的直接证据：风格目录覆盖广度足够，但每页的实际出品质量依赖模型在封闭语法内的构图判断，其示例工程（`examples/ppt169_cangzhuo/`）走的是水墨文人路线，无法证明高密度商务页的设计上限。

**② 动效丰富度可调、各档都吸引眼球。**
它做到的部分：丰富度确实可调且分档清晰（默认全关 → fade → `-a auto` → sidecar 编舞 → Morph 跨页连续动作，`animations.md:8-24`）；"默认全关 + 自动元素动画是 AI deck 的破绽"（`animations.md:34-36`）这条论证可以直接引用进我们的动效原则。
不适配的部分：它的动效天花板是 PowerPoint 效果集（实测 `scripts/pptx_animation_presets.json` 注册 203 个对象动画效果、`scripts/pptx_transitions.py` 注册 48 种页面切换），且**默认态刻意不吸引眼球**——它的目标是"演讲时不露怯"，而标准②要求"各档都足够吸引眼球"。它没有滚动驱动、悬停、视差等网页动效概念（也无需有）。我们可拿的是它的"动效按沟通任务分发、拒绝目录式覆盖"的纪律（`animations.md:303-305`），不是它的效果清单。

**③ 复杂 fancy 信息图。**
它做到的部分：结构语法（6 原子 × 5 角色 × 6 操作 + 验证 rubric，`executor-structure.md`）+ 187 原生预设 + Boolean 运算，覆盖了"复杂且可编辑"的信息图构造；另有 AI 生图路线覆盖"fancy 但不可编辑"的部分（11 种内部骨架类型）。
缺的部分：在它那里"fancy"（材质、光效、混合）和"可编辑"是互斥的——fancy 到超出封闭语法的部分只能 Bake 成位图（`svg-effects.md:944-950`）。标准③要求我们 HTML 语境下"复杂 fancy 信息图"不需要这个妥协；但它的"关系先于样式""去掉颜色效果后位置本身仍能传达"的验证 rubric（`executor-structure.md:88-99`）是我们 components.md 可以引入的验收标准形态。

**④ 复杂标注、复杂交互动效、全面图表。**
图表覆盖强：33 图表 + 6 表格词汇、Native-ready 双轨（原生图表 vs 形状）。标注方面，结构语法把 label/leader/tether 作为一等角色（`executor-structure.md:38-40`）。交互方面出乎意料地有 PowerPoint `trigger_shape`（点击某对象触发某行动画，`animations.md:135-138`）。
缺的部分：没有网页级交互（悬停、点击展开、滚动联动）——PPTX 介质决定。它的图表是"选型目录 + Executor 自由实现"，图表内文字的可编辑性在 PPTX 里天然成立，对我们无迁移成本问题但也没有可直接抄的实现。

**⑤ 图片占位（占位图即换图指南）。**
它做到的部分：`placeholder` 来源 + 虚线占位框 + Step 7 就绪门禁（`generate-pptx.md:792`）。
关键差异：**它禁止占位图出现在交付物里**（"never ship the dashed placeholder"），而我们的标准⑤恰恰要求"占位图作为交付物的一部分、构图即换图指南"。这不是它做得不够，是目标不同：它的交付物必须立即可演示，我们的交付物明确允许用户后续换图。它的就绪门禁思路可借鉴为"导出前清点 placeholder 行"的校验项，但语义要反过来：我们的占位图是合法交付状态。

**⑥ 双图片模式 + 落盘 assets/。**
它做到的部分：四种来源 + slice 派生的光谱比我们的双模式更宽；`image-generator.md:29-35` 的"文字双层归属"硬规则（图内只放永不改的词）与我们的 assets/ 纪律 + 可编辑文字契约在精神上是同一条原则，且它把代价讲得最清楚（改图内一字 = 重新生图）。图片统一放项目 `images/` 目录、`<image href>` 必须指向锁内登记文件（`executor-base.md:123`），与我们的 assets/ 固定目录同构。
缺的部分：它没有"用户上传图"作为编辑器内运行时能力（图片由生成期的 acquisition 阶段落定）；也没有"占位图构图即换图指南"的概念。⑥b（纯 HTML/CSS 视觉 + 用户上传图）近似它的 `none` 来源档。

**⑦ 图表、文字、信息图中的文字全部就地可编辑、可批注修改。**
这是它与标准⑦最意外的重合点：它的双层可编辑（PowerPoint 原生 + 内置浏览器 SVG 编辑器）中，**编辑器双通道（Direct edit / Annotate）与我们 editor.html 的"就地编辑 + 批注"架构同构**，连"批注以 data 属性写回源文件、AI 回落后逐条应用"的机制都一致（`live-preview.md:48-66`）。这反过来验证了我们批注设计的合理性。
缺/不适配的部分：它的"就地编辑"发生在源 SVG 上、最终交付仍需重新导出（chat 驱动），不是"保存即交付"；它的图表文字可编辑靠 PPTX 原生对象，我们是靠 HTML 文本节点 + data-editable 契约。另外它的 AI 生图内嵌文字明确**放弃**可编辑（`image-generator.md:34`），标准⑦"信息图中的文字全部可编辑"要求我们对 AI 插画采取更保守的用法（插画不带字，文字全部 HTML 覆盖层）。

**元原则（原则突出、枚举谨慎；枚举项必附规则与验收）。**
ppt-master 是六个参考项目里对这一原则实践最系统的：几乎每个目录文件都自带"Reference — not a constraint / 无配额 / zero selection is valid"声明（如 `chart-vocabulary.md:9`、`modes/_index.md:27-34`）；枚举项确实附带规则（每个风格文件有统一的六节结构 + 插画倾向级；每个图表附"编码关系"定义）；`custom` 逃逸舱无处不在且要求"行为散文非空"（`modes/_index.md:75`）。它甚至把"enumerable 的边界"本身写成了规则："结构层禁止目录"（`executor-structure.md:11`）。
但它也展示了这一路线的代价：**规范体量与 agent 遵循成本的矛盾没有被条件加载完全消解**——1.2 万行规范散文中大量是防御性的"禁止做 X 的 12 种变体"，每一条都在防一个真实发生过的模型行为，但边际遵循成本递增。它用 checker（7958 行）把最有效的规则从"散文"转成"可执行门禁"，这个分工——**散文承载理由、代码承载强制**——是它给元原则最重要的示范。

## 4. 结论：拿什么 / 不拿什么 / 与最优方案的差距

### 拿什么

1. **权威归属与事实单源**："每个事实只有一个 owning artifact，派生物只重新生成不手修"（`artifact-ownership.md:6`、`:97-118`）。我们的 themes.md → editor.html 主题数据的单源同步（sync-themes.mjs）已是这个思想，可扩展为整个技能的产物归属表。
2. **确认值五级语义 + 类型提升规则**（`strategist.md:51-63`）：比我们现在的【硬规则/默认/参考】三档更能表达"用户确认的字段各有各的约束力"。尤其"接受 AI 推荐不提升约束级别"这条，直接适用于我们的 design-system 面板意图清单。
3. **条件加载的确定性触发表 + 索引→详情两级读**：我们 SKILL.md 已有"按需加载"纪律（`skills/html-pptx/SKILL.md:149-159`），它示范了更严格的形式——触发条件写成表格、"never glob"。
4. **首页门禁 + gate-signal 方法级诊断**（`generate-pptx.md:705-725`）：我们的渲染校验在全部页面完成后才跑；它把 P01 当方法样本、同类同向问题归因到规则再批量生成，可显著降低我们逐页返工率。
5. **page_rhythm 逐页节奏锁 + 全 roster 节奏检查**（`strategist.md:604-606`）：我们只有明暗节奏；anchor/dense/breathing 三标签（breathing 禁多卡片网格）可直接进 typography.md 的密度规则。
6. **动效纪律的论证措辞**："自动元素动画是 AI deck 的破绽"（`animations.md:36`）、"切换按页间关系选、不为目录覆盖而变"（`animations.md:303-305`）、"无关键帧时间线，相邻两页的差就是动画"（`animations.md:19`，对应我们的滚动语义动效）。
7. **文字双层归属原则**（`image-generator.md:29-35`）：图内只放永不改的文字——这是我们 AI 插画用法的现成硬规则。
8. **编辑器双通道证据**（Direct edit / Annotate，`live-preview.md:40-41`）：验证我们 editor.html 批注模式是已被实践的形态；其拖拽经 CTM 换算、连续修改合并撤销等细节是编辑器演进的参考。
9. **事实溯源二分**：外部事实挂 ID + 编造数据标"情景数据"（`strategist.md:106`）——我们的"数据真实性"红线目前只有禁止编造，没有溯源/标注机制。

### 不拿什么

- **SVG→DrawingML 工具链与封闭语法**：属性白名单/黑名单的存在理由是 PPTX 映射，我们的 HTML 画布无此约束；照搬等于放弃 CSS 全量能力。
- **双阶段阻塞式确认 + Confirm UI 服务器**（`strategist.md:31-39`、`scripts/docs/confirm_ui.md`）：索引已决定不拿门禁式多轮人工确认；但其"确认产物写结构化 JSON、agent 一次性消费不 reopen"的协议形态可作 design-system 面板输出 schema 的参考。
- **1280×720 画布与 EMU 量化**、原生形状 helper、模板工作区四类体系、旁白配音/视频导出——全部服务于 PPTX 交付，与 HTML 产物无关。
- **防御性散文体量**：1.2 万行规范的遵循成本正是我们"原则突出、枚举谨慎"要避开的形态；拿它的机制，不拿它的体积。

### 与最优方案的差距（对照本项目 skills/html-pptx/ v1.4 现状）

| 维度 | 我们 v1.4 现状 | ppt-master 参照下暴露的差距 |
|---|---|---|
| 规则分级 | 三级（SKILL.md:45-51） | 缺"确认值语义类型"（Literal/Semantic/Identity/Reference/Permission）与提升规则；design-system 面板的用户意图清单落地时约束力粒度不够 |
| 上下文防漂移 | 按需加载纪律（SKILL.md:149-159）+ 骨架锁定 | 缺确定性触发表；缺"每 N 页重读锚点"机制（我们只有 Step 4 的"每页动手前重读"，未制度化长 deck 的再锚定） |
| 密度机制 | 高/低双档（SKILL.md:75） | 缺页面级节奏锁（anchor/dense/breathing）与全 roster 节奏检查；双档只控总量，不控页间起伏 |
| 质量门禁 | Step 5 全部生成后渲染测量（SKILL.md:103-111） | 缺首页方法门禁：P01 问题的方法级归因发生在 N 页之后，返工面大 |
| 图表/信息图验收 | components.md / charts.md 配方 + 内容门槛 | 缺"去掉颜色/效果后位置仍传达关系"式的验收 rubric；配方法验收、语法化构造（executor-structure 模式）值得引入 |
| 图片 | assets/ 固定目录 + 占位图即换图指南（SKILL.md:132-136） | 机制已超 ppt-master（它有占位但禁止随交付）；可补"占位行清点"校验与"图内文字只放不改的词"硬规则 |
| 动效 | 语义动效引擎 + 拆字禁令 | 纪律相当；可引用其"AI deck tell"论证强化 motion.md 的原则表述 |
| 可编辑/批注 | editor.html 就地编辑 + 批注（三层引用 + 导出指令） | 同构已被其 live-preview 双通道验证；差距不在设计在演进细节（拖拽/撤销合并/重叠拾取） |
| 数据真实性 | 红线禁止编造（SKILL.md:143） | 缺溯源机制：真实数据的来源标注与演示数据的可见"情景数据"标签 |

总体判断：ppt-master 是六个参考项目里**工程纪律的天花板**（权威归属、条件加载、门禁校验、防漂移），也是**枚举可扩展性的最佳示范**（每个枚举项附规则与验收、custom 逃逸舱、"结构层禁止目录"）。对它的借鉴应集中在元机制层；它的视觉与动效清单受 PPTX 介质压缩，对我们全量 CSS 的浏览器画布不构成上限，反而提醒我们：本项目的 SOTA 视觉语言枚举（标准①③④所要求的 fancy 信息图与复杂交互）在它那里找不到现成答案，需要本项目自己策展。
