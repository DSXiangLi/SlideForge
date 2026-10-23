# dashi-ppt-skill 深度调研

> 一行定位：基于"预置主题页面组件库 + JSON 契约"的本地 PPT 生成技能（React SSR 出静态 HTML，产物内置播放器/编辑器/导出器） · 来源：`source/dashi-ppt-skill/` · 调研日期 2026-09-17 · 索引：[../source-survey.md](../source-survey.md)

## 1. 定位与产物形态

dashi-ppt（当前 0.4.11，`source/dashi-ppt-skill/skills/dashi-ppt/SKILL.md:13`）是一个**重运行时**的生成技能：AI 不写 HTML，而是把用户需求整理成一份 `goal.json` 计划，调用内置的 Node 项目生成器（`<skill-root>/project`，SKILL.md:29）做 React SSR，输出 `index.html` + `assets/`（SKILL.md:8）。产物是横向翻页的单 HTML，内置三大件：

- 播放器（翻页、GSAP 页面转场、演讲模式）；
- 编辑器（就地改文字、换图/视频、右侧面板调 props、切换 4 个候选方案、增删复制页）；
- 导出器（HTML / PDF / **可编辑 PPTX**，经本地预览服务的 HTTP 接口完成，SKILL.md:102-104）。

代价是这些全部打进每个产物：`project/assets/template-swiss.html` 单文件 10277 行（播放器 + 编辑器 + 9 种转场 + 导出逻辑 + i18n）。主题也不是 token 级换肤，而是**12 套各 71–111 页的整页组件库**（README.md:38-49，`project/src/components/themes/generated-metadata.js` 各 theme 的 `pageCount`），合计 1020 个具名页面模板（`project/layout-manifest.json` 中 `themeXX_pageNNN` key 去重计数）。主题源码以"导入外部成品 deck"的方式进入（`src/components/themes/themeXX/source/` 保留原始实现，`dist/theme-runtime/imported-theme-runtime.themeXX.js` 是编译产物）。

与本项目的根本差异：dashi 是"组件库 + 契约填空"，AI 的自由度被压缩到文案和第四个定制方案；我们是"骨架 + 原则"，AI 自己写全部页面 HTML。

## 2. 方案详解

### 2.1 画布与适配

每页固定 1920×1080，`.imported-theme-root{width:1920px;height:1080px;transform:scale(var(--deck-scale));transform-origin:top left}`（template-swiss.html:1829），缩放系数按视口宽度计算 `deckScale=deckW/1920`（template-swiss.html:4394-4399）——只按宽度缩放，不取宽高最小值，配合横滑翻页（一屏一页）。打印媒体查询里强制 `--deck-scale:1`、每页 `break-after:page`（template-swiss.html:1838-1844）。导出时在屏外起 1920×1080 隐藏 iframe 跑，保证视口与服务端无头浏览器一致（template-swiss.html:7970、8028 注释）。这是"固定画布 + 整体缩放"路线的又一个独立印证，但翻页交互是横滑，与我们竖向滚动不兼容。

### 2.2 主题与视觉语言

12 套主题各有风格名、适配场景、适配人群（`references/options.md:5-18`，同数据由脚本同步进 SKILL.md:58-73 的 `theme-choice-hints` 区块）。选择纪律是"问用户、不代选"：开工前必须确认主题风格和是否需要图片/视频，用户未表态先提问；风格选择回复**必须嵌入** `assets/skill/theme-style-grid.png` 风格对比图（SKILL.md:51-54）——即"看着选"的可视化选择，与"只选不改"互补。

两个有意思的守门规则：

- `theme10 金色指数风` 默认不进自动选择池，只有用户明确指定或金融内容强相关且 inspect 确认可填才用（SKILL.md:59）——对高风险主题做显式门禁。
- 面向用户交付的 deck 默认隐藏主题切换器，只在内部调试 demo 保留（SKILL.md:84）。

主题没有跨主题 token 系统；一致性靠"一份 deck 只用一套主题"（goal 顶层 `themePack` 枚举锁死，`references/goal-spec.schema.json:36-51`）。

### 2.3 密度与字排（文案容量预算系统）

没有显式的高/低密度双档，密度控制全部下沉为**逐槽字数预算**（`copyBudgets`），机制在 `project/scripts/workflow/copy-contract.mjs`：

- 每个文案槽按字段名推断角色密度（`inferCopyDensity`，copy-contract.mjs:273-286）：`serial`（大序号）/`tagline`（刊头标语）/`metric`（数字）/`display`（标题）/`compact`/`brief`/`body`。
- 预算从模板默认文案长度推导：`maxChars = clamp(floor, ceil(base × 系数), cap)`，系数按角色从 1.1（tagline）到 2.2（body）不等（copy-contract.mjs:254-271）。即"默认文案多长，槽位物理上就只容得下约这个量级"。
- 字数按**视觉宽度**折算：全角记 1、半角记 0.5（`charLength`，copy-contract.mjs:288-308）。注释记录了 issue #15 的教训：此前按码点计数，"GPT · Gemini · Claude" 这类混排文案被误拦——预算常数是按中文字符标定的，必须统一口径。

这套系统比"渲染后量溢出"更前置一层：预算在写文案阶段就约束，渲染校验只做兜底。`validate:goal-spec` 对 `display`/`metric` 超长直接拦截（SKILL.md:250）。

### 2.4 容量驱动选版与全稿分配

选页不是 AI 拍脑袋，是一个**硬条件过滤 + 打分 + 组合优化**的管道：

1. **内容形状冻结**：每页先写唯一文案包 `slide.content.presentation`（title/summary/takeaway/items，item 带 `id/label/value/displayValue/detail/unit/required/priority`，SKILL.md:89），再由 `contentShapeFromPresentation` 抽成形状向量（标题字数、item 数、带值 item 数、嵌套深度等，`workflow/layout-query.mjs:86-156`）。
2. **硬条件过滤**：标题、items、`value/displayValue`、媒体需求是硬条件（通不过 `projectionPlan.requiredFits` 直接出局，layout-query.mjs:245）；摘要、detail、role 只是排序软偏好（SKILL.md:75）。
3. **整稿 beam search 分配**：每页选 3 个结构家族不同的模板时，不是逐页贪心，而是 `selectDiverseLayouts` 对候选组合做 beam width 72 的搜索（`workflow/layout-allocation.mjs:62-86`），打分函数显式编码多样性目标（layout-allocation.mjs:204-217）：不同构图 +520、不同家族 +150、新 layout +260、layout 复用 -260、整份 deck 复用同一组三布局（triplet）-480、相邻页家族重叠 -18……之后 `rebalanceDuplicateLayouts` 再做一轮全局消重（layout-allocation.mjs:88-134）。
4. **种子化随机打散**：同分候选用 `randomSeed:slide-N` 打散（layout-query.mjs:250-），注释记录了动机——"历史上并列项按页码稳定排序，所有调用方都贪婪取列表最前，导致不同用户生成的 deck 大量选中同一批'前面的页'，成片雷同"（layout-query.mjs:247-249）。这是用工程手段对抗 AI 选择收敛的直接案例。

页面语义分 21 个 `role`（cover/statement/metrics/trend/comparison/…，`references/layout-roles.md:5-26`），但 role 只做轻量排序加分，候选资格由容量决定（layout-roles.md:3）——"语义软、容量硬"。

### 2.5 四方案策略：3 模板 + 1 bespoke

每个逻辑页产出 4 个方案（SKILL.md:44-45）：

- **v1–v3 锁模板填文案**：保留页面组件的原始视觉/结构/配色/图表类型/图片槽位，只替换可见文字。三方案共享同一事实源（同一 presentation 文案包），只在文案长短、排序、视觉层级上分化，"不分别创作三套故事"（SKILL.md:89）。
- **v4 bespoke（Agent 定制）**：不写 layout/props，写一份受约束的 `composition`：12×8 网格（`BespokeSlide.jsx:10-11`）、元素类型闭集 `text/metric/list/quote/media/shape/chart`、最多 32 个元素（BespokeSlide.jsx:63）、必须用当前主题 runtime 的字体层级/recipe、禁止 raw CSS（SKILL.md:90-93）。构图家族枚举 `hero/split/metric-spotlight/chart-led/timeline/matrix/editorial/comparison/process`，且硬性反模式："不能把不同家族都画成标题加卡片墙""整稿同一家族不连续出现，卡片网格最多占正文 v4 的三分之一""不把标签换色当成设计"（SKILL.md:92-93）。
- **字号自动适配**：`fitTextToGrid` 按网格像素边界 + 角色 recipe（行高/字重/minSize，`TEXT_ROLE_RECIPES` BespokeSlide.jsx:19-26）做字号回缩，触底 minSize 后打 `data-bespoke-capacity="minimum"` 标记（BespokeSlide.jsx:1465-1482、461）——注意这是"缩字号保底"，与我们"缩字号是禁区"的原则相反。
- Codex 环境存在 `baoyu-design` 技能时，v4 先读它做艺术指导再落 composition（SKILL.md:91）——技能间协作的一个实例。

交付时默认每页 `selectedVariant: "v1"`，右侧面板可切换；只有 `variantOutputMode:"comparison"` 的导出才派生 4N 页（SKILL.md:243）。

### 2.6 动效

两层：

- **元素入场动画**：用页面组件自带效果，不允许自定义（SKILL.md:82）——模板锁定的一部分。
- **页面切换转场**：9 种 GSAP 转场（liquidMorph、pixelReveal/pixelZoom/pixelBarsY 像素网格、slice 切片、containerClip/containerSlide），注册表见 template-swiss.html:2226、player 表 :9861-9871；转场在预览控制面板里由用户选、可改色（SKILL.md:83，template-swiss.html:6720-6736）。转场尊重 `prefers-reduced-motion`（template-swiss.html:9882-9884）。
- **动态背景**：内置 4 个 Unicorn Studio WebGL shader 场景（科技/自动化/流动/黏球，`src/components/themes/unicorn-background.jsx:3-8`，场景 JSON 在 `project/assets/unicorn/`），作为 `ambient` 氛围页背景，且"背景可换成上传媒体"是一个正式 control（unicorn-background.jsx:12-22）。

动效没有档位概念：要么开要么关，丰富度不可调。

### 2.7 图片策略

媒体走严格的槽位契约（SKILL.md:245-257 的 `mediaSlots`）：

- 只有 `canPresetMedia: true` 且 `initialSrcSupported` 的槽可预填（`workflow/media-slots.mjs:373-377` 的 `isWritableMediaSlot`）；goal.json 只引用 deck 内相对路径，禁止临时目录/绝对路径/远程 URL（SKILL.md:109）。
- 用户本地素材先 `media:stage` 落盘到 `assets/user-media/`：AVIF 转浏览器可用格式，位图长边压到 2048，视频生成 poster（`scripts/stage-media.mjs:12-19,44`）。文件名用内容 sha256 去重。
- 素材复用纪律：**每个图片/视频全稿最多用一次**；同一逻辑页的 4 个方案共用算 1 次（SKILL.md:112）。
- 生图走外部 image-gen，2 张以上用多个 subagent 并行、禁止串行、禁止拼图后拆分（SKILL.md:113）；未明确生图意图先问用户（SKILL.md:110）。
- 空槽策略：不留"占位提示文字"，改选无媒体页（SKILL.md:110）——与我们"占位图即换图指南"的思路相反，他们选择不出现占位。

编辑器内换图：图片槽内嵌隐藏 `input[type=file]`，点击即换（`isDeckFileSlotTarget` 判定，template-swiss.html:4574-4576），上传的 dataURL 在保存时由服务端解码落盘（见 2.8）。

### 2.8 可编辑性与持久化

这是 dashi 对本项目价值最大的部分，机制分三层：

**标记契约**：可编辑元素打 `data-editable-id`；主题组件可显式提供 `data-editable-path`（`explicitTextId`，template-swiss.html:9796-9802），纯装饰打 `data-editable-skip`（isTextCandidate 第一关就排除，template-swiss.html:9818）。无显式标记时走启发式兜底：排除结构化/表单/媒体标签后，要求"所有子元素都是 BR/SPAN/B/I/EM/STRONG/SMALL"的叶子（template-swiss.html:9816-9825）。

**稳定 ID（JAD-173 教训）**：不用 `querySelectorAll` 遍历序号，而用"slide key + 从 slide 根到元素的 child-index 路径"，形如 `text:<slideKey>:p2-0-1`（`nextTextId`，template-swiss.html:9783-9794）。注释写明原因：计数器在 prop 变更 reflow（候选元素集合变化）时整体漂移，已存文案会套到错误元素；结构路径只随元素自身祖先结构变化（template-swiss.html:9780-9782）。

**持久化模型是 state-overlay，不是 DOM 序列化**：所有编辑（文字覆盖、props、媒体、方案选择、页序增删）存进一个 JSON state，写回 `index.html` 里既有的 `<script id="deck-view-model" type="application/json">` 块的 `.state` 字段，其余字段不动（`scripts/persist-deck-state.mjs:122-136`）；页面加载时 state 覆盖到渲染结果上（template-swiss.html:9560-9567）。具体实现细节：

- 编辑器在编辑模式下给元素挂 `contenteditable="true"`（不是 plaintext-only），focus 时快照 `editBefore`、blur 时 diff 决定脏位并推入撤销栈（template-swiss.html:9610-9628, 9679-9719）。
- 自动保存防抖 2s 后 POST `/api/save-deck-state`，服务端**原子写回**（同目录临时文件 + rename，persist-deck-state.mjs:145-152）。
- state 里的 dataURL 媒体解码落盘到 `assets/user-media/<sha256前24位>.<ext>`，内容哈希天然去重；且因为保存往返期间用户可能继续编辑，客户端只用返回的 `mediaMap` 做"精确字符串替换"，不整份覆盖 state（persist-deck-state.mjs:82-120，注释明确写出这个竞态）。
- 服务端不可达（file:// 直开）时降级到 localStorage（超限转 IndexedDB，localStorage 只留签名指针，template-swiss.html:2782-2814），并亮常驻提醒"更改仅保存在本浏览器，分发前请导出"（template-swiss.html:1855）。
- 一个真实的 React 共存坑：媒体槽内嵌在可编辑文本块里时，blur 用陈旧 innerHTML 快照覆写会摧毁 React 管理的槽 DOM，因此文本编辑路径与媒体槽路径用同一个 `isDeckFileSlotTarget` 判定互相隔离（template-swiss.html:9679-9684 注释）。

### 2.9 质量保障与校验

渲染脚本把校验固化进管道（`scripts/render_goal_deck.sh:44-48`）：`props:safe --write` → 渲染 → `validate:swiss` → `validate:goal-copy` → `validate:four-variant-quality`。四个校验各司其职：

- `validate:goal-spec`（1975 行）：JSON 结构、layout 存在性、props 形状、文案长度预算、自由 HTML 拦截（Html 字段只允许 `<br>/<b>/<em>`，SKILL.md:80）、媒体槽合规、重复 id 等几十个检查点。
- `validate:swiss`（654 行）：输出 HTML 的资产引用完整性——收集 src/href/poster/srcset、CSS url()、字符串字面量里的本地资产引用，逐一验证落盘存在（`validate-swiss-deck.mjs:30-120`）。
- `validate:goal-copy`（757 行）：**残留默认文案检测**——内置主题默认文案指纹词表（"AI Capital/投融资""SoundWave/声浪"等组，带"内容与主题相关时放行"的 allowWhen 正则，`validate-goal-copy.mjs:69-100`），正文中出现与主题无关的默认文案必须重写重渲染（SKILL.md:105）。这是"模板填空"路线的特有风险，他们用了对的解法。
- `validate:four-variant-quality`（519 行）：Playwright 起 1920×1080 无头浏览器，**只对 bespoke v4 页**做水合检查、裁切（scroll-clipping）测量和逐页截图，模板页只做运行时检查、明确不做截图审美复查（`visualQaScope: 'bespoke-only'`，validate-four-variant-quality.mjs:179-183、SKILL.md:128,144）；同时做**资产溯源审计**——产物里每个资产必须能追溯到"主题源码/共享运行时/用户素材"三者之一，内容不一致即报错（`workflow/four-variant-quality.mjs:33-114`）。

验收哲学：机器校验只是技术基线，最终验收以用户原始需求为准；状态只有"通过/待修正/阻塞"（SKILL.md:135-146）。

### 2.10 工程化与防漂移

- **可复现随机**：每任务生成 `randomSeed` + `workflowRunId`，选页种子 = `<seed>:slide-<n>`；同一任务重试复用 run ID，新任务新 ID（SKILL.md:118）。
- **工作流遥测**：`workflow-telemetry.mjs` 记录每个阶段（scaffold/validate/…）的起止与结果，供复盘。
- **脚手架代替手写**：长 deck 用 `goal:scaffold` 从逐页 brief 一次完成候选查询、三布局分配、v4 初稿生成（SKILL.md:78,121），明确"不要让 Agent 手写 30 份 contentMap"（SKILL.md:76）。
- **版本自更新提醒**：每次任务结束静默跑 `check_latest_version.mjs`，有新版本才在回复末尾提醒（SKILL.md:15-21）。
- 规则过载问题真实存在：SKILL.md 263 行塞了数十条硬规则（含"不要使用旧 token、旧主题、旧媒体槽、旧风格分支或旧入场动画控制"这类历史包袱清理条款，SKILL.md:74、`options.md:62`）。

### 2.11 叙事方法论

叙事结构很轻：goal 顶层只收 `title/goal/audience/owner`（SKILL.md:117），页级靠 `role` + `priority`（layout-roles.md），没有显式的叙事弧/页计划表确认环节。它的"叙事"更多体现在**单页内部**：presentation 文案包强制 title/titleShort、summary/summaryShort 双档 + takeaway（结论）+ items（带 priority/required），即每页必须有明确结论句。图表页改数据后，页内 insight/读图文案必须一并改写，不保留默认结论（SKILL.md:123）。

### 2.12 导出（可编辑 PPTX）

内置自研包 `packages/html-deck-to-pptx`：HTML→**可编辑** PPTX，核心不是截图拍平，而是"逐节点保真回退链"——映射不了的区域截图，但从实时 DOM 把文字重新抽回来保持可编辑（无 OCR），加 alpha-matte 透明背景捕获，自报基线 editableFidelity 0.851（`packages/html-deck-to-pptx/README.md:5-7`）。经预览服务 `/api/export-editable-pptx` 调用（`serve-preview-https.mjs:126`），导出跑在屏外 1920×1080 iframe 里保证视口一致（template-swiss.html:8028 注释）。我们已决策不做反向导出，但其 DOM 契约假设（`#deck > .slide`、active 页标记，README.md:29-31）与我们的骨架结构同构，是兼容性的旁证。

## 3. 辩证评估（对照七条最优标准）

**① 高/低文字密度双档下的设计感。**
做到的部分：1020 个整页模板覆盖了从封面到高密度图表页的频谱，单页设计感下限由成品 deck 原作者保证，远高于 AI 即兴；v4 bespoke 的反卡片墙约束（SKILL.md:92-93）直接对抗 AI 默认审美。缺的：没有显式密度双档概念，密度只有逐槽 `copyBudgets` 这层隐式控制（copy-contract.mjs:254-271）；低密度"演讲主导"场景的呼吸感依赖主题库里恰好有的大字页，而非系统性的密度决策。更重要的是它的设计感是**买来的**（导入成品 deck 编译），无法迁移到我们"AI 从零生成"的路线——我们能拿的是 copyBudgets 的"按槽角色推导字数预算"机制和全稿分配的组合优化思路，拿不到那 1020 页本身。

**② 动效丰富度可调。**
不够。动效是"模板自带入场 + 用户面板选 1 种全局转场 + Unicorn 动态背景"（SKILL.md:82-83），没有丰富度档位，也没有滚动叙事（横滑形态天然没有）。它在自己场景下合理（商务汇报，转场克制是对的），但"各档都足够吸引眼球"这个目标它没有对应机制。Unicorn Studio 场景 JSON 的接入方式（unicorn-background.jsx:3-8，本地 JSON + UMD SDK）对我们"高级氛围页"有参考价值。

**③ 复杂 fancy 信息图。**
模板库内含大量信息图页面（漏斗/矩阵/径向/时间线等 role 分布，layout-roles.md:11-24），但这些是**固化在组件里的**，AI 不能创造新信息图，只能在 `fillPlan` 允许的字段里填数据；v4 的元素类型闭集（text/metric/list/quote/media/shape/chart，SKILL.md:93）也不支持自由绘制复杂信息图。对我们的启示是反向的：锁定换稳定的路我们不走，但它的"信息图页 = 内容形状（items 数/带值数/嵌套深度）的函数"这一选型机制（layout-query.mjs:86-156）值得拿。

**④ 复杂标注、复杂交互动效、图表全覆盖。**
图表由主题组件承载（theme05 色谱图表风 94 页、theme10 金色指数风 95 页等，README.md:42,47），种类覆盖广但同样是封闭集合；`numericBounds`/`fixedLength` 等数值契约（SKILL.md:255）保证数据填不错位置。交互只有转场和控制面板，无页内交互动效；标注能力没有专门机制。不构成对④的满足。

**⑤ 图片占位。**
明确走了反面：素材不可访问时"不在页面内留占位提示文字"，改选无媒体页（SKILL.md:110）；`isDeckFileSlotTarget` 的占位只存在于编辑器的空槽 UI。"占位图即换图指南"这条它完全没有，我们的占位图方案（主题色抽象图形、尺寸即构图尺寸）在它这里没有先验。

**⑥ 双图片模式 + 落盘 assets/。**
做到的部分：用户素材一律 `media:stage` 落盘 `assets/user-media/`，goal 只写相对路径、禁外链禁绝对路径（SKILL.md:109-111）；编辑器换图上传 → dataURL → 服务端解码落盘 + 哈希去重（persist-deck-state.mjs:91-120）——这条链路（含 mediaMap 竞态处理）是我们可以直接借鉴的成熟实现。缺的：AI 自主绘图走外部 image-gen（SKILL.md:113），不是"AI 用 HTML/CSS 画插画"；也不存在"纯 HTML/CSS 视觉"这一档的显式决策。

**⑦ 文字全部就地可编辑、可批注。**
文字就地编辑做到了，且比我们目前更深：稳定 ID 的结构路径方案（JAD-173，template-swiss.html:9780-9802）、React 共存的快照隔离坑（template-swiss.html:9679-9684）、撤销栈、多档位持久化降级。**但持久化模型与我们不兼容**：它是 state-overlay（编辑存进 `#deck-view-model` JSON 块、加载时覆盖渲染），原 DOM 里的模板文案原样保留，所以 file:// 下"更改仅保存在本浏览器"，分发前必须导出（template-swiss.html:1855）——我们要求"保存回 HTML 文件本身、DOM 即真相"，它的模型在 React 重渲染场景下是对的，在我们的静态产物场景下是不必要的间接层。批注功能没有。

**元原则对照**：dashi 恰恰是"枚举谨慎"的反面样本——1020 个枚举页面 + 263 行 SKILL.md 硬规则。但要公允地说：它的枚举是**机器可执行的**（每个页面带 fillPlan/copyBudgets/mediaSlots 契约，可被脚本查询、校验、组合优化），不是写在文档里让 AI 背的清单；规则过载的负担部分被脚本卸载了（"不要让 Agent 手写 30 份 contentMap"，SKILL.md:76）。这提示我们：当枚举不可避免时，把枚举做成**带契约、可被程序消费的数据**（而非散文），枚举项自带规则与验收——这与元原则中"每个枚举项必须附带规则与验收标准"是同一个方向，dashi 是这条路的重度实现。

## 4. 结论：拿什么 / 不拿什么 / 与最优方案的差距

### 拿什么

1. **稳定 ID 的结构路径方案**（child-index 路径，非遍历序号）——已被我们 `editing-contract.md` 吸收，此处确认其工程理由（reflow 漂移）成立。
2. **字数预算双层制**：写文案前的槽位预算（按角色推导 maxChars + 视觉宽度折算）+ 渲染后的溢出测量，比单纯事后测量多一道前置闸。我们 v1.4 的槽位预算（typography.md）方向一致，可借鉴其"预算 = 默认容量 × 角色系数，clamp 上下限"的定量形式，以及全角 1 / 半角 0.5 的口径（我们已采用同口径）。
3. **全稿版式分配的组合优化**（beam search + 复用惩罚 + 相邻页家族去重 + 种子化打散防"人人选中同一批页"）——我们目前是原则性条款（"卡片墙最多一次"），dashi 证明了这个问题的严重性和可工程化程度；`layout-query.mjs:247-249` 的雷同事故注释尤其值得引用。
4. **媒体落盘链路**：编辑器上传 → dataURL → 哈希命名落盘 `assets/` → mediaMap 精确替换（防保存竞态）→ 原子写回（临时文件 + rename）。我们 editor.html 的图片替换（FSAA 写 assets/）可对标本链路的去重与原子性。
5. **残留默认文案校验**（主题指纹词表 + allowWhen 放行）——凡"模板/示例文案可能泄漏进产物"的系统都需要这一道。
6. **验收分级**：模板页机器检查、bespoke 页才做截图级视觉 QA（visualQaScope bespoke-only）——校验成本花在 AI 自由度最高的地方，这个配比思路可直接用。

### 不拿什么

- 编辑器/播放器/导出器打进产物（10277 行 template-swiss.html）——我们独立编辑器页面的决策正是为了避开这个。
- state-overlay 持久化模型——我们 DOM 即真相、序列化回写。
- 1020 页锁模板路线与 React SSR 工具链——与"AI 从零生成、无构建"冲突。
- 横滑翻页交互、PPTX 导出、运行时主题切换。
- "缩字号保底"（fitTextToGrid 触底 minSize）——与我们的修正阶梯原则相反。

### 与最优方案的差距（对照 skills/html-pptx v1.4 现状）

我们 v1.4 已有：1920×1080 固定画布 + 竖向滚动骨架（skeleton.html 逐字复制）、13 套策展主题 token、密度双档、容量先于版式原则、渲染测量校验、data-editable 契约、占位图纪律（SKILL.md:122-136）。相对七条标准的差距，从 dashi 视角看：

- **②动效档位**：dashi 也没有，双方都不满足；但 dashi 的 Unicorn 场景接入方式提示了"高档位 = 预编译 WebGL 场景 JSON + 本地 SDK"这条重资产路径，与我们 data-anim 语义动效的轻路径形成光谱两端。
- **④图表/标注覆盖**：dashi 靠 1020 页枚举达到广度，我们靠 4 类图表配方 + 原则；我们的风险正是 dashi 用枚举对冲掉的那个风险（AI 自由发挥的质量方差）。dashi 的"枚举做成机器可消费的契约数据"是中间道路。
- **⑦可编辑性**：我们契约一致但工程深度不足——dashi 的撤销栈、媒体槽/文本编辑隔离、保存竞态处理、降级链提醒都是 editor.html 可对照检查的清单。
- **质量保障**：我们只有"渲染校验一条硬规则 + 人工目测"，dashi 有四级脚本校验固化进渲染管道；其中"残留默认文案检测"和"资产溯源审计"是我们工具链里目前完全没有的两类。
