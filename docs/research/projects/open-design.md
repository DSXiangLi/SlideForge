# open-design 深度调研

> 一行定位：local-first 的 agent 设计工作台（"开源 Claude Design"），deck 只是其六种产物之一；真正与本项目同构的是它的**固定骨架提示词**与**宿主注入式编辑桥**两块。 · 来源：source/open-design/ · 调研日期 2026-09-17 · 索引：../source-survey.md

## 1. 定位与产物形态

OpenDesign 是一个本地优先的桌面应用（macOS/Windows，Electron 壳 + web 前端 + daemon 后端），定位为"the open-source Claude Design alternative"：把"发现需求 → 锁定方向 → 流式产出 → 批评 → 交付"的 agent 设计循环做成一个由技能、设计模板、设计系统、插件组成的文件系统（source/open-design/README.md:35-39）。它生成六类产物：prototype、live artifact、deck、image、video、HyperFrames 动效（CONTEXT.md:31-45 的术语表可见产物分 Normal/Live 两类）。

与本项目相关的不是整个产品，而是其中三层：

1. **提示词层（daemon）**：`apps/daemon/src/prompts/` 下的系统提示词是 TypeScript 代码——deck 骨架、设计方向库、媒体生成契约都是字符串常量，按项目类型条件装配（system.ts:1296, 1313）。这是"提示词即代码"的字面含义。
2. **模板/技能层**：`templates/deck-framework.html`（269 行固定骨架）、`skills/deck-*`（3 个 deck 技能）、`design-templates/`（115 个设计模板，其中 html-ppt-zhangzara-* 约 50 个幻灯片模板）、`design-templates/html-ppt/`（vendored 的 lewislulu/html-ppt-skill，36 主题 + 31 版式 + 27 CSS 动效 + 20 canvas FX）。
3. **编辑器层**：`apps/web/src/runtime/srcdoc.ts`（预览注入）+ `apps/web/src/edit-mode/`（bridge.ts 1368 行桥 + source-patches.ts 734 行源码补丁）。编辑器不是独立页面，而是宿主 React 应用的一部分，通过 postMessage 与注入产物 iframe 的桥脚本通信。

deck 产物形态：单 HTML 文件，1920×1080 固定画布，`transform` 整体缩放，**翻页式**（一次只显示 `.slide.active`），键盘 ←/→ + 半屏点击导航，`@media print` 把全部页面展开成多页竖排 PDF（deck-framework.ts:178-209）。产物在 OD 托管的 iframe（srcdoc）中预览，宿主在注入时修补产物（见 §2.1、§2.7）。

## 2. 方案详解

### 2.1 画布与适配

**固定骨架，逐字复制。** deck 模式的核心交付是 `DECK_SKELETON_HTML`（apps/daemon/src/prompts/deck-framework.ts:45-353）：一段嵌在系统提示词里的完整 HTML 骨架，agent 必须"copy the skeleton verbatim"，只允许编辑 `SLOT:` 注释标记的五个槽位（deck title / theme tokens / per-deck styles / slides / slide N content，deck-framework.ts:381-386）。骨架文件在仓库里另有一份 `templates/deck-framework.html`（269 行），两者同源但**缩放实现不同**（见下）。

**缩放方案（daemon 提示词版）**：1920×1080 stage 以 `transform-origin: top left` 锚定，JS `fit()` 计算 `s = min((sw-32)/1920, (sh-32)/1080)` 后写 `translate(tx,ty) scale(s)` 整体居中（deck-framework.ts:267-276）。设计理由写在文件头注释里（:13-43）：

- shell 是**纯 block flow，故意不用 grid/flex 居中**——任何额外居中层会与显式 translate 叠加，把缩放后的舞台推离屏幕（:14-19）；
- `translate + scale` 写法在 OD viewer 的嵌套 transform wrapper（宿主缩放控件）里稳定；
- 选这个形态而非 scroll-snap 的理由很务实："It matches what the model has the strongest prior on, so the framework gets adopted verbatim instead of being 'blended' with the model's own instincts"（:24-27）。

**缩放方案（templates/ 文件版）**：另一套实现——stage 用 `position:absolute; top:50%; left:50%; transform: translate(-50%,-50%) scale(var(--deck-scale))`，`transform-origin: center`，JS 只更新 CSS 变量（templates/deck-framework.html:41-52, 202-210）。注释自称这是"bulletproof pattern"（:13-19）。`templates/kami-deck.html:1-12` 声明自己是该文件的逐字副本。**两代缩放方案并存、互相矛盾**（一个 top-left + JS translate，一个 center + CSS 变量），说明"唯一骨架"在其自家仓库里也没有完全收敛。

**级联硬化**。可见性切换用 `.slide:not(.active) { display: none !important; }` 防变体类覆盖，active 默认布局用 `:where(.slide.active)` 包成**零优先级**，让 per-slide 变体类（如 `.s-cold{display:grid}`）天然获胜（deck-framework.ts:106-119，注释记录了"per-slide variant 把 .slide{display:none} 顶掉、所有页同时显示"的真实事故）。这是防 AI 改坏基础设施的 CSS 级手段，比纯口头禁令硬。

**chrome 外置**。页码计数器与前进/后退按钮放在缩放舞台**之外**（fixed 定位），"so they don't shrink with it"（deck-framework.ts:121-123）。

**键盘焦点三件套**：capture 阶段在 window 和 document **双目标**监听（iframe 里焦点可能在任一者，单监听会静默丢按键，:302-306）；`e.__odDeckKeyHandled` 标记去重（:293）；body 自动聚焦使方向键无需先点击（:333-338）；localStorage 恢复上次页码（:340-344）。

**宿主侧反向修补（deck-fix）**。这是索引未记录的机制：宿主在 srcdoc 注入时检测产物是否为框架 deck（`id="deck-stage"`），若是则注入修复样式 `.deck-shell{display:block!important} .deck-stage{flex-shrink:0!important}`（srcdoc.ts:2955-2974）。注释记录了 issue #47：生成物常违规把 shell 写成 flex 居中容器，stage 变成 flex item 后 `flex-shrink:1` 把 1920px 宽塌缩成预览面板宽，"a ~770px preview yields a 770x1080 stage — the 16:9 canvas silently turns portrait"。**产物偏离契约时，宿主在预览层兜底纠偏**——生成侧约束与消费侧防御双层并行。

### 2.2 主题与视觉语言

三层主题来源，优先级：用户品牌/设计系统 > 模板自带视觉签名 > 内置方向库。

**Direction 库（5 套）**。`DESIGN_DIRECTIONS`（apps/daemon/src/prompts/directions.ts:53-184）：editorial-monocle / modern-minimal / human-approachable / tech-utility / brutalist-experimental。每套携带：mood 一段、references（真实产品参照，如 Linear/Monocle）、CSS-ready 字体栈、**OKLch 六色调色板**（bg/surface/fg/muted/border/accent）、posture 具体行为线索（如 brutalist 的 "borders are full-strength fg (1.5–2px), not muted greys"，:178）。双用途设计写在文件头（:11-22）：运行时渲染成 `direction-cards` 问卡让用户点选（一次点击 → 确定性调色板，无模型即兴），构建时把选中方向的 spec 全文嵌进系统提示词，要求 **verbatim 绑定**到骨架 `:root`，"do not improvise"（:278）。

**问卡协议**。`<question-form>` 是 assistant 文本里的一段 XML，宿主解析成表单 UI；类型含 radio/checkbox/text/color/direction-cards 等（discovery.ts:76）；纪律严格：只在"答案会实质改变设计方向"时发问、一轮只发一个表单、发完立即停轮（discovery.ts:44, 87, 91）；有限选项由宿主自动加"其他"逃生口（discovery.ts:81）。

**按需拉取（pull-based 渐进披露）**。slim 模式只在常驻提示词里放方向 id+label 索引（约省 6.7KB），agent 选定后跑 `od tools directions --id <id>` 取全文（directions.ts:288-305；system.ts:1046-1056 记录了 text_artifact 运行时没有工具可用、只能全量内联的降级理由）。

**Design System 2.0（品牌级）**。`design-systems/` 下 154 个品牌目录，每目录固定文件名契约：manifest.json / DESIGN.md / tokens.css / design-tokens.json / tailwind-v4.css / components.html（design-systems/_schema/AGENTS.md:28-49）。token schema 分三层：**A1（身份+结构）每品牌必须显式声明，无跨品牌兜底；A2 有 fallback 默认值（defaults.css 是人类可读镜像，parity 由守卫强制）；B-slot 品牌可绑定**（scripts/check-tokens-fixture-sync.ts:23-43, 288-294）。每个品牌还带 `source/evidence.md` 溯源声明与 `token-contract.report.json`——把每个 token 映射回 tokens.css 的声明行，产出 score/grade（design-systems/apple/source/token-contract.report.json:15-20，score 100 / excellent）。这是"策展可审计"的工程化：**枚举（154 品牌）每个都带机器可验的契约与验收分数**。

**模板层策展（幻灯片专用）**。115 个 design-templates，其中 html-ppt-zhangzara-* 系列约 50 个，各自锁死一套视觉系统："Mixing layouts across templates breaks the system; stay inside this one"（design-templates/html-ppt-zhangzara-signal/SKILL.md:50-52）；palette/typography/mood/density 元数据在 template.json 里机器可读（design-templates/html-ppt-zhangzara-signal/template.json）。skills/deck-* 三个技能延续 guizang 式铁律："只能从下面 4 套二选一，不许混用、不许改 hex"（skills/deck-swiss-international/SKILL.md:42；deck-guizang-editorial 5 选 1 同款，SKILL.md:44）。

**装配条件逻辑**。system.ts 里 direction 库只在无 active design system 时注入（否则 6.7KB 是"dead weight"，system.ts:1034-1045）；deck framework 指令 pinned 在提示词最后且仅当 deck 项目**且**无自带骨架的 skill seed 时注入（skill seed 优先，system.ts:1296；无技能但 brief 像 deck 时加一行条件前缀注入，:1298-1313）。

### 2.3 密度与字排

密度纪律写在 deck framework 指令里（deck-framework.ts:412-427），自称"the #1 cause of ugly decks"：

1. 封面 display headline ≤140px、≤8 词、≤3 行——装不下就拆页，"don't shrink the font and pack more in"（:422）；
2. footer 安全区：absolute footer 存在时，flow 内容不得进入底部 200px；最简执法是给主内容区显式 `height:760px`（:423）；
3. 正文页 ≤3 段、lead 宽度 ≤56ch、每行 ≤12 词（:424）；
4. 一页一意（:425）。

字阶枚举在技能层：deck-open-slide-canvas 给 10 档 type scale（2xs:18 → 5xl:220 px）+ 三档 padding（96/128/160）（skills/deck-open-slide-canvas/SKILL.md:45-46）。

**校验的诚实边界**：交付前自检是"mentally render at 1920×1080"的七条清单（deck-framework.ts:515-527）——**纯心智渲染，没有像素级渲染测量**。唯一自动化 QA 是 `qa/deck-layout.ts`（186 行），但它只覆盖 brand-system 生成的 deck，且明确声明"there is no browser layout engine in the daemon, so the pass verifies that the no-clip *mechanism* is present and not the pixel result"（deck-layout.ts:14-19）：用 cheerio 静态断言 `container-type:size` 存在、shrink-to-fit runtime（`od-deck-fit`）存在、`.f-fit` 包裹层存在、headline 槽位不带 line-clamp 截断类（:77-119）。即**验证机制存在性，而非渲染结果**——overflow 防线依赖运行时 `.f-fit` 自动缩放到合身，这与"禁止缩字号"的流派正好相反。

### 2.4 图表

deck framework 内置三条图表纪律：

- **手写柱状图配方**（deck-framework.ts:429-454）：每根条带 inline `--v` 真实数值、容器声明一次 `--max`、`.bar{width:calc(var(--v)/var(--max)*100%)}`——"Bar lengths are computed, never eyeballed"；值标签必须在条外独立元素，不许放进定高 `overflow:hidden` 的条里被裁掉；`--v` 必须无单位（calc 除法要纯数字）。
- **嵌套/同心图纪律**（:456-473）：几何可共心，文字不可——中心最多放一个短 KPI，其余标签进外部 legend，给出 `rings(aria-hidden) + dl legend` 的骨架。
- **Mermaid 暗色主题纪律**（:475-513）：默认主题是为白页设计的（#333 标签 + 透明 SVG 底），暗色 deck 必须 initialize 时选 dark/base 主题；`themeVariables` 不接受 `var()` 必须传字面量；`darkMode:true` 单独不会加深节点填充色。

优先用 html-ppt 家族自带的 Chart.js 模板而非手写 div 图表（:429）。html-ppt 技能另有 20 个 canvas FX（粒子/力导图/神经网络脉冲等，design-templates/html-ppt/SKILL.md:64），属于动效化数据可视，非标准图表体系。

### 2.5 动效

deck framework 骨架本身**零动效**（无 transition/animation 指导）。动效来自两层模板：zhangzara 系列模板自带 `data-anim="fade-in" data-delay="3"` 这类属性驱动入场（design-templates/html-ppt-zhangzara-signal/example.html:1560）；html-ppt 技能提供 27 个 CSS 入场动效（`data-anim`）+ 20 个 canvas FX（`data-fx`，fx-runtime.js 在页进入时自动初始化、离开时清理）（design-templates/html-ppt/SKILL.md:63-66）。没有动效强度分档、没有 reduced-motion 纪律的显性规则。

### 2.6 图片策略

**反占位图是统一立场**：每个 deck 技能的 example_prompt 都带 "avoid lorem ipsum or placeholder images"（skills/deck-open-slide-canvas/SKILL.md:34）；deck-swiss 禁外部图片 URL、装饰几何必须纯 CSS/内联 SVG（skills/deck-swiss-international/SKILL.md:80）。zhangzara 模板用**纯 CSS 色块占位**（example.html:1558-1573 的 split-image 就是一个 flex 居中的空色块，注释 "image placeholder"），换图指南只有 SKILL.md 里一句 "Match existing dimensions when swapping image placeholders"（SKILL.md:74）——没有 assets/ 目录约定，没有"占位图即换图指南"的设计。真图走产品级媒体生成：agent 调 `od media generate` CLI，daemon 按 surface+model 分发、落盘进项目（media-contract.ts:1-24）；媒体契约 pinned 在提示词最后，连错误话术都逐字固定（:41-80）。**图片生成是宿主产品能力，不是 deck 技能的一部分**；产物 HTML 与图片资产之间没有契约。

### 2.7 可编辑性与契约

这是该项目最深的域，也是与本项目编辑器最直接对位的部分。架构是**宿主注入式**：产物 HTML 本身可以不带任何编辑标记，宿主在构建 srcdoc 时注入标注与桥脚本（srcdoc.ts:402-403）：

- `annotateMissingOdIds`：给无语义标记的外部 HTML 自动补位置性 `data-od-id`（srcdoc.ts:1275-1300，只标到语义容器的直接子级，"deeply nested layout divs create noise"）；
- `annotateManualEditSourcePaths`：给发现选择器内每个元素写 `data-od-source-path="path-N-N-N"`（DOM 位置路径）（srcdoc.ts:1236-1260）；
- 桥脚本由 `buildManualEditBridge()` 以**字符串模板**生成注入（bridge.ts:171-172），样式同理（:1297-1298）。

**身份三级**（bridge.ts:33-39）：授权语义 `data-od-id` > 构建期注入的 `data-od-source-path` > 运行时兜底 `data-od-runtime-id`/domPath。补丁侧按同序查找（source-patches.ts:278-286）。关键不变量："位置性身份必须跟随结构变更"——插入/删除/复制后桥的 `restampPositionalIdentity()` 全量重算 path id，但**授权语义 id 永不改写**，否则原地插入后点击后续兄弟会把补丁打到错误的源元素（specs/current/manual-edit-direct-manipulation.zh-CN.md:108）。

**元素分类**（bridge.ts:66-86）：text/link/image/container 四类；text leaf 的判定是"有可见文本且**无元素子节点**"，不是看标签名——裸 `<div>Title</div>`、`<li>`、`<td>` 与 `<p>` 同等可编辑。有内联子标记的（如 `<p><strong>Nested</strong> copy</p>`）故意不算 text leaf，因为扁平文本补丁无处安放（:50-65 的长注释记录了推理）。补丁侧有一条穿透规则：`findSoleMeaningfulTextNode` 允许"恰好一个后代文本节点承载全部可见文本"时（图标 span + 标签的常见情形）原地改那个文本节点，出现第二个有意义文本节点立即拒绝并指向 HTML tab（source-patches.ts:611-655）。

**编辑手势（实测驱动迭代）**。spec 文档（manual-edit-direct-manipulation.zh-CN.md）记录了 v2.1–v2.7 七轮用户实测修订，是最有价值的部分：

- **首击选中、二击入编辑**（v2.6，:176）：根因是单击文本立即 `makeEditable` 置 contenteditable 会**释放 line-clamp/定高截断**，元素瞬间变高（"选中变大"抖动）。修复：首击只发 `od-edit-select` 零回流，点击已选中元素或双击（`ev.detail>=2`）才入编辑。注意 bridge.ts:1071-1073 当前代码仍是单击即 `makeEditable`——spec 是更新的设计定稿，代码与文档存在时序差。
- **plaintext-only 默认、格式命令时升级**（v2 架构决策 2，:23）：会话默认 `contenteditable=plaintext-only`；首个格式命令（execCommand）才升级为 true，提交时若产生子元素走 `set-inner-html` 补丁（宿主侧消毒）。
- **键盘守卫**（bridge.ts:88-168）：monkey-patch window/document 的 addEventListener，编辑会话激活时拦截产物里 deck 骨架的 keydown 翻页监听，否则打字时按空格/方向键会翻页。
- **Home/End 滚底**（v2.4 验收轮，:136）：Chromium 在 contenteditable 里对 Home/End 双重生效（光标移动+文档平滑滚动），行内编辑按 End 会把画布拽到页面底部；修复 = 会话消费按键手动移光标。
- **粘贴/拖放传字节不传 File 句柄**（v2.3，:78）：postMessage 克隆的 File 句柄上传时报 `net::ERR_UPLOAD_FILE_CHANGED`（Chrome 在事件回合后失效句柄），桥必须在事件回合内 `file.arrayBuffer()` 读出字节再发。
- **undo/redo 原地化**（v2.1，:52；v2.4，:89-123）：所有内容补丁落盘后走 `od-edit-apply-dom` 原地 reconcile（"DOM ≡ 已落盘源码，元素粒度"，:106），iframe 重载降级为兜底且必带滚动位置快照；异步渲染页的滚动恢复用 260/600/1200/2400/4000ms 重试梯（:145）。
- **每次落盘都是一个文件版本**（versionSource:'manual' + 语义 label），undo/redo 也产生版本，"编辑不可能丢失"（:109）。

**补丁即源码手术**。`applyManualEditPatch` 对**源码字符串**（不是 live DOM）做 DOMParser 解析 → 修改 → 序列化（source-patches.ts:109-185, 235-250）：set-text/set-link/set-image/set-style/set-attributes/set-outer-html/remove-element/set-token/set-full-source 九种补丁；set-token 用正则在 `<style>` 里改 CSS 变量值（:703-713）；属性写入有白名单（拒绝 `on*`/`data-od-*` 伪造身份，:665-672）。宿主四模式分工：Edit（手动）/ Comment AI（AI 改）/ Tweaks（全局 token）/ Draw（批注）（manual-edit-mode-requirements.md:19-24），"the project source file as the only source of truth"（:14）。

### 2.8 质量保障与校验

- **提示词自检**：交付前七条心智渲染清单（deck-framework.ts:515-527），无自动化。
- **静态结构 QA**：`analyseDeckLayout`/`assertDeckLayoutSafe` 作为 brand-system 重建的硬门禁（deck-layout.ts:140-146），error 级直接 throw 阻断构建；但只覆盖 brand deck 一种产物。
- **deck 预览导航契约**：design-templates/AGENTS.md:36-62 给所有 `od.mode:deck` 模板规定了键盘/滚轮/触摸/圆点导航的最低行为集与 `.slide.active` 状态同步要求（宿主预览桥依赖它读页码）。
- **真浏览器 e2e**：编辑模式验收用 Playwright 驱动隔离实例跑 20/20 矩阵（sentinel 证明整个编辑会话 iframe 零重载等，spec:132-138）。
- **repo 级守卫**：`scripts/guard.ts` 汇总 design-system manifest/token parity/craft 引用等十余项检查（guard.ts:1-25）。

### 2.9 工程化与防漂移

- **提示词即代码**：骨架、方向库、媒体契约都是 TS 字符串常量，进 git、进 review、随版本演进；`DECK_FRAMEWORK_DIRECTIVE` 把骨架全文嵌进指令末尾（deck-framework.ts:533-537），"your output is this skeleton with theme tokens tuned … nothing more, nothing less"（:539）。
- **漂移负面清单**：指令里专设 "Common drift modes — DO NOT DO THESE"（:388-398），每条 ❌ 都附根因（"we just spent days debugging"）——不写自己 fit()、不用 transform-origin:center、不单目标监听键盘、不改 localStorage key/元素 ID、不把 chrome 放进 stage、不重定义 .slide、不删 @media print。再加一节 "Why this matters (so you can judge edge cases)"（:400-404）解释契约的服务对象（宿主 zoom wrapper、Share→PDF），让 agent 能自行判断边界情形——**禁令 + 根因 + 判断依据**的三层写法。
- **模板工业化流水线**：`scaffold-html-ppt-skills.mjs`（从上游模板批量生成技能壳）、`bake-html-ppt-examples.mjs`（把引用共享 CSS 的多文件模板烘焙成 srcdoc 可预览的单文件 example.html，:1-12）、`refresh-slide-template-commercialization.ts`（按 assignment.json 批量重写 50 个模板的商业元数据：品类、EN/ZH 标题、买家向描述，幂等可重跑，:1-16）。模板是**可批量运营的商品目录**，不是手工艺品。
- **design-systems 同步**：`sync-design-systems.ts` 从上游 npm 包（getdesign）同步 154 个品牌系统设计系统，手写系统（default/warm-editorial）豁免（sync-design-systems.ts:1-10）。

### 2.10 叙事方法论

几乎没有。deck framework 只要求工作流第 3 步 "Plan the slide arc and theme rhythm (state aloud before writing)"（deck-framework.ts:368），没有页计划表、叙事弧、章节结构的机制。html-ppt 技能的前置协议是 "infer first, ask only when blocked"（design-templates/html-ppt/SKILL.md:101-107）——能推断就不问，只有缺失答案会实质改变 deck 时才合并问一次。叙事深度让位给吞吐效率，这与其"模板商品目录"的定位一致。

## 3. 辩证评估（对照七条最优标准）

**① 高/低密度双档 + 比 guizang 更有设计感** —— **部分做到，路径不同。** 它的密度纪律只有一组硬数字（≤140px/≤8 词/≤3 段，deck-framework.ts:420-425），没有显式的高/低密度双档；高密度靠 zhangzara 系列模板承载（template.json 里 `density: "high"` 是策展元数据而非生成规则，design-templates/html-ppt-zhangzara-signal/template.json:27）。设计感的来源是**模板策展的规模**（50 个 zhangzara 模板各自是一套完整视觉系统，含衬线/纸张肌理/几何装饰）加 154 品牌设计系统——广度远超 guizang 的 2 风格。但代价是"锁模板"路线：换内容不换版式，"Adjust deck length by duplicating layouts"（zhangzara-signal/SKILL.md:79-84）。判断：它用枚举规模买设计感下限，我们用"原则 + token 系统"买上限；它的模板库里确实有比 guizang 更丰富的视觉语言可挖（尤其 zhangzara 系列的 editoral/brutalist 变体），但**抽取时应抽 token 与构图原则，不抄整页版式**。

**② 动效丰富度可调且各档吸睛** —— **未做到。** deck 骨架零动效；动效是模板自带属性（data-anim/data-delay）或 html-ppt 的 47 个动效资产（SKILL.md:63-66）。没有强度分档概念、没有 reduced-motion 纪律、没有动效语义（什么角色配什么动效）。FX 里有吸睛的（knowledge-graph 力导图、constellation），但那是 canvas 彩蛋，不是"丰富度可调"的系统。判断：这条上它没有可拿的机制，html-ppt 的 FX 清单可作动效枚举的素材参考。

**③ 复杂 fancy 信息图** —— **弱。** 信息图只有两条禁令式纪律（嵌套图文字分离 :456-473；图表标签防裁 :449），没有信息图组件库。zhangzara 模板里有现成的信息图版式（KPI Tower、Loop Diagram 等，deck-swiss-international/SKILL.md:48-70 的 22 版式池），但锁在各自模板里不可组合。判断：组件配方这条路它没走，我们的 components.md 是空白领域的自建。

**④ 复杂标注、交互动效、图表全覆盖** —— **图表纪律出色，覆盖不足。** --v/--max 计算比例、值标签防裁、Mermaid 暗色主题三条是真实踩坑沉淀（deck-framework.ts:429-513），值得逐条吸收。但图表类型只覆盖 bar + 嵌套图 + Mermaid 流程图，无折线/饼/散点/漏斗的配方；交互限于翻页。标注能力在编辑器侧（Draw 模式，manual-edit-mode-requirements.md:19-24），是产品功能而非产物能力。判断：图表的"数据诚实"纪律（computed never eyeballed）可直接并入我们的 charts.md；覆盖广度它没有答案。

**⑤ 图片占位（占位图即换图指南）** —— **明确反对。** 这是立场分歧：它的统一话术是 "avoid placeholder images"（deck-open-slide-canvas/SKILL.md:34），真图走宿主媒体生成（media-contract.ts:1-24）。合理之处在于它是**带图像生成模型的产品**，占位图在它的场景里是质量缺陷；我们没有运行时生图能力，占位图 + assets/ 换图契约是我们的必然选择。zhangzara 的纯 CSS 色块占位（example.html:1558-1573）证明即使反占位立场下，占位仍实际存在——只是没有成文化为契约。判断：不拿它的立场，但它提醒我们占位图的"交付感"需要设计（灰底叉线确实是廉价感来源），我们"主题色抽象图形占位"的决策因此更稳。

**⑥ 双图片模式 + assets/ 落盘** —— **机制有，契约无。** AI 生图（od media generate 落盘项目目录）+ 用户上传（编辑器图片替换，spec:9, 16-17）两条路都有，且支持裁剪（canvas 裁切后上传新 PNG、原资产不动，spec:17）。但产物侧没有 assets/ 目录约定——deck 技能普遍要求"不要外链图片"（deck-open-slide-canvas/SKILL.md:70），图片路径由项目文件系统托管，产物不是自包含的可移植单元。判断：它的"上传→项目→set-image 补丁"管线与我们编辑器的 FSAA 写 assets/ 同构，可参考其补丁语义；产物可移植性上我们的方案更干净。

**⑦ 全部文字就地可编辑、可批注** —— **做到且远超我们的现状，但架构不可直接搬。** 它把就地编辑做成了一个小型直接操纵编辑器：首击选中二击编辑、plaintext-only 默认、富文本会话升级、拖拽移动/拉伸/四角等比缩放、对齐参考线吸附、元素复制粘贴删除、undo/redo 文件版本化、补丁原地应用零重载（spec v2.1-v2.7 全文）。批注走 Comment AI（选元素 + 写指令 → agent 改源码）。**但它不设契约**——标记是宿主注入的（srcdoc.ts:1236-1300），产物离开 OD 运行时就是普通 HTML，可编辑性不随文件走。判断：手势与补丁语义（二段式、唯一文本节点穿透、键盘守卫、粘贴传字节、undo 原地化）全部可移植到我们的独立编辑器；它的"宿主注入标注"模式我们不采用（我们的 data-editable 契约随产物走，是第一期就定死的决策），但它的三级身份回退（授权 id > 注入 path > 运行时推导）对编辑器处理**无契约的历史产物**是现成的兜底方案。

**元原则对照（原则突出、枚举谨慎）**：它的枚举纪律两极分化——好的一面：direction 库只有 5 套且要求"visually distinct, two near-identical directions defeat the purpose"（directions.ts:20-22），每个枚举项带 mood/references/palette/posture 完整 spec，design-systems 每个品牌带 token 契约报告与评分（可验收）；差的一面：html-ppt 技能的 36 主题 + 31 版式 + 47 动效、zhangzara 50 模板，是无验收标准的大枚举，典型靠规模换覆盖。deck framework 指令本身是"枚举带规则"的好样本：每条 ❌ 都附根因与判断依据。

## 4. 结论：拿什么 / 不拿什么 / 与最优方案的差距

### 拿什么

1. **骨架防漂移的三层写法**：逐字复制契约 + ❌ 负面清单（每条带根因）+ "Why this matters" 判断依据（deck-framework.ts:388-404）。我们 skeleton.html 已有逐字复制，缺负面清单与判断依据层。
2. **级联硬化技巧**：`.slide:not(.active){display:none!important}` + `:where(.slide.active)` 零优先级（deck-framework.ts:106-119）——直接适用于我们骨架的页面可见性逻辑。
3. **缩放踩坑的具体结论**：shell 禁 grid/flex 居中、translate+scale 显式居中、双目标 capture 键盘监听、chrome 外置（deck-framework.ts:13-43, 121-123）；以及宿主侧 deck-fix 反向修补的兜底思路（srcdoc.ts:2955-2979）。
4. **图表数据诚实纪律**：--v/--max 计算比例、值标签不裁切、Mermaid 暗色主题（deck-framework.ts:429-513）——并入我们 charts.md。
5. **编辑桥的全部实测教训**（specs/current/manual-edit-direct-manipulation.zh-CN.md）：二段式手势、plaintext-only 默认 + 会话升级、键盘守卫 monkey-patch、粘贴传字节、undo 原地化 + 滚动恢复重试梯、Home/End 滚底——这是 v2.1-v2.7 七轮真用户实测换来的，是我们 editor.html 后续迭代最直接的避坑清单。
6. **唯一文本节点穿透规则**（source-patches.ts:611-655）与三级身份回退（bridge.ts:33-39）。
7. **方向卡片的枚举规格**：每套方向 = mood + references + OKLch palette + posture，且带 pull-based 按需加载（directions.ts:288-305）——我们 themes.md 的枚举规格可对齐这个完备度。
8. **question-form 协议纪律**：只在实质改变方向时发问、一轮一表、发完停轮（discovery.ts:44-91）——对我们 design-system 面板的意图收集交互有参考价值。
9. **token 契约可验收化**：每个枚举品牌带 token-contract 报告 + score（check-tokens-fixture-sync.ts）——"枚举必须附带规则与验收标准"的现成实现范式。

### 不拿什么

1. **翻页式 deck 形态**（一次一页、半屏点击翻页）——与我们 16:9 竖向滚动的形态决策不兼容，交互代码不可复用。
2. **宿主注入式可编辑**——标记不随产物走，产物离开 OD 运行时不可编辑；我们坚持 data-editable 契约内嵌产物。
3. **编辑器与宿主的重耦合**（React 宿主 + daemon + Electron + 文件版本存储）——我们是单文件静态页面 + FSAA，体量差两个数量级。
4. **锁模板路线**（50 个 zhangzara 模板复制填内容）——与我们"版式由内容驱动"的原则相悖；模板只作视觉语言素材库。
5. **运行时 shrink-to-fit 防溢出**（.f-fit 自动缩放，deck-layout.ts:1-19）——与"禁止缩字号、容量先于版式"的规划流派相反，它本质是把溢出从规划问题降级为渲染时压缩。
6. **演讲者模式**（html-ppt 的 S 键 magnetic cards 弹窗，html-ppt/SKILL.md:84-99）——本期范围外。
7. **媒体生成契约**（od CLI + 固定错误话术）——我们页面内无 AI 调用，不适用。

### 与最优方案的差距（对照 skills/html-pptx/ v1.4 现状）

我们已经拿到的：固定骨架逐字复制（SKILL.md:82-84）、主题只选不改（:80）、data-editable 契约（:121-130）、assets/ 占位图契约（:132-136）、Playwright 渲染测量（:103-111——**这一点我们强于它**，它只有心智自检 + brand deck 的结构 QA）。

差距清单：

1. **骨架缺级联硬化与漂移负面清单**。我们 skeleton.html 有 SLOT 和逐字复制硬规则，但没有 open-design 那种"每条禁令带真实事故根因"的写法，也没有 `:where()` 零优先级这类 CSS 级防覆盖手段。差距小，可直接补。
2. **编辑器的实测深度**。我们 editor.html 的两段手势 + plaintext-only 是 v1.5 刚落地的；open-design 的 spec 记录了七轮实测迭代出的十余个边界 bug 及修法（滚底、选词折叠、粘贴句柄失效、undo 闪屏、inline 元素拉伸无效、nowrap 收窄不换行……）。这些坑我们**大概率还没踩到但会踩到**——该 spec 是编辑器路线图上最有性价比的一份文档。
3. **主题枚举的规格完备度**。我们 themes.md 有 13 套主题 + token，但缺少 open-design direction 那样的 mood/references/posture 行为线索，也没有机器可验的契约报告（它的 token-contract.report.json + score）。元原则要求"枚举项必须附带规则与验收标准"——我们的主题枚举目前还没有验收标准这一层。
4. **图表纪律的细节密度**。我们 charts.md 有四类图表配方，但 open-design 的 --v/--max 计算比例、Mermaid 暗色主题字色等是更细的踩坑级规则，可并入。
5. **宿主侧防御层**。open-design 对"产物偏离骨架"有 deck-fix 预览层兜底（srcdoc.ts:2955-2979）；我们的编辑器对违规产物没有对应的修补机制——考虑到我们要求产物携带契约标记、编辑器按契约工作，这个差距可接受，但契约校验（产物是否合规）的静态检查工具是空白，它的 `analyseDeckLayout`（验证机制存在性而非像素，deck-layout.ts:14-19）是一个低成本起点。
