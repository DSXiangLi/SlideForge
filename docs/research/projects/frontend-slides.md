# frontend-slides 深度调研

> 一行定位：面向非设计师的"零依赖单 HTML 幻灯片"生成技能（Claude Code 插件形态），核心武器是"Show, Don't Tell"的视觉预览选型 + 三级渐进披露的 34 套大胆模板库。 · 来源：source/frontend-slides/（GitHub: zarazhangrui/frontend-slides，插件版本 2.1.0，见 source/frontend-slides/plugins/frontend-slides/.claude-plugin/plugin.json:2）· 调研日期 2026-09-17 · 索引：../source-survey.md

## 1. 定位与产物形态

**它是什么**：一个 coding-agent 技能，SKILL.md 是工作流地图（380 行），配套按需加载的支持文件（README 架构表：source/frontend-slides/README.md:517-539）。以 Claude Code 插件分发，但明确支持其他 agent（Codex、Kimi Code 等）直接读 SKILL.md 使用（source/frontend-slides/README.md:74-93）。

**产物形态**：单 HTML 文件，全部 CSS/JS 内联，无 npm 无构建（source/frontend-slides/SKILL.md:12 "Zero Dependencies"）。图片是唯一外部资产，放 `assets/` 目录（source/frontend-slides/html-template.md:340-344）。固定 1920×1080 舞台整体缩放是"NON-NEGOTIABLE"原则（source/frontend-slides/SKILL.md:16）。

**三种模式**（source/frontend-slides/SKILL.md:67-73）：Mode A 从零生成、Mode B pptx 转换（python-pptx 提取，source/frontend-slides/SKILL.md:250-258）、Mode C 增强已有 HTML（专门的修改规则，source/frontend-slides/SKILL.md:75-86——这是六家参考里少见地认真对待"改已有产物"场景的项目）。

**工作流六阶段**：Phase 0 模式检测 → Phase 1 内容发现（4 个问题一次问完）→ Phase 2 风格发现（生成 3 个可视预览）→ Phase 3 生成 → Phase 5 交付 → Phase 6 分享（Vercel 部署 / PDF 导出，source/frontend-slides/SKILL.md:261-364）。

**模板库来源**：`bold-template-pack/` 的 34 套模板并非本项目原创，而是从同一作者的另一个仓库 `zarazhangrui/beautiful-html-templates` 移植（source/frontend-slides/bold-template-pack/selection-index.json:4），每套只有 `design.md` + `preview.md` 两个文件（不含 template.html 实体代码——README 里提到它但作为"最后手段参考"，source/frontend-slides/bold-template-pack/README.md:22-23）。

## 2. 方案详解

### 2.1 画布与适配

**固定舞台方案**由 `viewport-base.css`（133 行，逐字复制进每个产物，source/frontend-slides/SKILL.md:52）+ 一段 JS 缩放代码组成。核心结构三层：`.deck-viewport`（fixed 全窗）→ `.deck-stage`（1920×1080，`transform-origin: 0 0`）→ `.slide`（absolute inset:0 堆叠）（source/frontend-slides/viewport-base.css:17-51）。缩放公式：

```js
const factor = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
const x = (window.innerWidth - 1920 * factor) / 2;   // letterbox 居中
this.stage.style.transform = `translate(${x}px, ${y}px) scale(${factor})`;
```
（source/frontend-slides/html-template.md:114-123）

两个值得记录的硬规则细节：

- **幻灯片切换禁止用 `display:none`**，必须用 `visibility`+`opacity`+`pointer-events`，因为后续的 `.slide-content { display:flex }` 会覆盖 display 让所有幻灯片同时可见（source/frontend-slides/SKILL.md:47；实现在 source/frontend-slides/viewport-base.css:40-59）——这是典型的"被坑过才写下的规则"。
- **CSS 函数前不能直接加负号**：`-clamp()` 被浏览器静默忽略、无报错，必须写 `calc(-1 * clamp(...))`（source/frontend-slides/SKILL.md:50；source/frontend-slides/STYLE_PRESETS.md:330-346 给出正误对照）。

**打印适配**：`@media print` 里把舞台拆回文档流、每页一张幻灯片、`break-after: page`（source/frontend-slides/viewport-base.css:80-123）。

**第二套舞台实现——deck-stage.js**（619 行 Web Component，source/frontend-slides/bold-template-pack/deck-stage.js）：shadow DOM 封装、幻灯片**隐藏不卸载**以保留 video/iframe 状态（source/frontend-slides/bold-template-pack/deck-stage.js:18-21）、自动给每页注入 `data-screen-label` 和 `data-om-validate="no_overflowing_text,no_overlapping_text,slide_sized_text"` 校验属性（source/frontend-slides/bold-template-pack/deck-stage.js:49-56, 439-447）、派发 `slidechange` CustomEvent 供宿主编排（source/frontend-slides/bold-template-pack/deck-stage.js:24-34）、`noscale` 属性专供 PPTX 导出器读取原始几何（source/frontend-slides/bold-template-pack/deck-stage.js:12-14, 528-534）、`@page` 规则在 shadow DOM 内无效所以动态注入 `<head>`（source/frontend-slides/bold-template-pack/deck-stage.js:389-405）。注意：这是模板源仓库的实现，frontend-slides 的最终产物**不强制使用它**——source/frontend-slides/SKILL.md:220 要求无论源模板用什么都转写为固定舞台。

### 2.2 主题与视觉语言（双层体系）

**第一层：12 套安全预设**（source/frontend-slides/STYLE_PRESETS.md）。每套给出 Vibe / Layout / Typography（具体字体+字重）/ Colors（可直接复制的 `:root` 变量块）/ Signature Elements。例如 Bold Signal 的签名元素是"大号色卡 + 大序号 01/02 + 面包屑导航透明度态"（source/frontend-slides/STYLE_PRESETS.md:32-36）。末尾有明确的 **DO NOT USE 负面清单**：Inter/Roboto、generic indigo #6366f1、紫渐变白底、无目的的 drop shadow（source/frontend-slides/STYLE_PRESETS.md:318-326）。预设层还有一条总纪律："Abstract shapes only — no illustrations"（source/frontend-slides/STYLE_PRESETS.md:3）。

**第二层：34 套 bold 模板**（bold-template-pack/）。这是该项目最值得解剖的部分——**枚举项如何写得可执行**。每套模板的 design.md 约 400-680 行（34 套共 20405 行，wc 实测），结构高度一致，以 monochrome 为例（source/frontend-slides/bold-template-pack/templates/monochrome/design.md）：

1. **YAML frontmatter 即 token 表**：colors / color-aliases / typography（每个角色带 fontFamily/fontSize/fontWeight/lineHeight/letterSpacing）/ spacing / components（每个组件带属性 + 一句 design rationale 的 description）（source/frontend-slides/bold-template-pack/templates/monochrome/design.md:6-175）。
2. **Overview 叙事段**：讲清这套系统的"材质约束"（"black ink on cream paper, and nothing else"）和三声部字体分工（source/frontend-slides/bold-template-pack/templates/monochrome/design.md:190-196）。
3. **Density philosophy 专段**：每套模板写明自己的密度哲学——"A slide that fills 80% of its area with type reads as cramped"（source/frontend-slides/bold-template-pack/templates/monochrome/design.md:198）；对比 studio 的"one massive thing, said once, in 900 weight uppercase"（source/frontend-slides/bold-template-pack/templates/studio/design.md:172）、pin-and-paper 的"中密度 populated，大半空白页反而是坏的"（source/frontend-slides/bold-template-pack/templates/pin-and-paper/design.md:319）。**密度不是全局档位，而是每套视觉系统的内生属性**。
4. **Do's and Don'ts**：成对的正误规则（source/frontend-slides/bold-template-pack/templates/monochrome/design.md:385-407）。
5. **Iteration Guide**：10 条编号的"新增元素时必须……"不变量（source/frontend-slides/bold-template-pack/templates/monochrome/design.md:471-483）——直接对应"防漂移"需求。
6. **Known Gaps**：诚实记录系统自身的坑（donut 图表的 ::after 裁切依赖背景色一致、bar chart 无数据绑定层靠手写 inline height、color-mix 的浏览器兼容）（source/frontend-slides/bold-template-pack/templates/monochrome/design.md:484-493）。
7. **CJK 专节**（34/34 套全有，grep 实测）：中文配对表 + 反直觉结论——Noto Sans SC 最细 300 仍显重，所以中文大标题要用 700 去匹配 Jost 200 的视觉分量；Noto Serif SC 无 italic，禁止伪造斜体；盘古之白（source/frontend-slides/bold-template-pack/templates/monochrome/design.md:424-469）。

**反 AI slop 的行为诊断**：不只列负面清单，还直接对模型喊话——"You tend to converge toward generic, 'on distribution' outputs"（source/frontend-slides/SKILL.md:20），并点名跨生成会话的收敛现象："You still tend to converge on common choices (Space Grotesk, for example) across generations"（source/frontend-slides/SKILL.md:36）。

**Preview authenticity 规则**（NON-NEGOTIABLE，source/frontend-slides/SKILL.md:180-187）：预览幻灯片**不得渲染任何内部流程文字**——不能出现 "Option A/B/C"、模板名、slug、文件路径、"generated from"、用户需求备注（如 "safe option"）；chrome 只能用真实 deck 信息（标题、日期、作者、页码）。这解决的是"AI 生成的预览页长得像诊断卡片"这一真实污染问题。

### 2.3 密度与字排

**密度双档**在 Phase 1 就向用户冻结（source/frontend-slides/SKILL.md:56-63）：低密度=演讲主导（一页一意、大字、1-3 条 bullet），高密度=阅读主导（结构化网格、4-8 bullet 或 4-6 卡片）。兜底原则："If content exceeds the selected density mode, split it into more slides instead of shrinking"（source/frontend-slides/SKILL.md:63）。混合需求时向更近一档靠拢、不发明中间档（source/frontend-slides/SKILL.md:213）。

模板选择时密度再次起作用：selection-index.json 每个模板带 `density` 元数据（实测分布：21 medium、6 high、5 low、2 medium-high），选型规则要求匹配 mood/tone/best_for/avoid_for/formality/density/scheme 七个字段（source/frontend-slides/SKILL.md:171-174）。

字排本身完全交给各 design.md 的 typography token 表（vw 单位标注为"设计比例"，生成时换算为 1920×1080 固定坐标，source/frontend-slides/SKILL.md:221）。技能层没有跨主题的字阶规范。

### 2.4 动效

`animation-patterns.md`（110 行）的组织轴是**情绪而非强度**：Effect-to-Feeling 表把 6 种感受映射到动画组合（Dramatic→慢淡入+大缩放；Techy→霓虹+glitch+粒子；Playful→弹性 easing……source/frontend-slides/animation-patterns.md:7-14），然后给四类入场动画 CSS（fade-up/scale/left/blur）、三类背景效果（渐变网格/噪点/网格线）、一个 3D tilt JS 类，以及 troubleshooting 表。

触发机制：`.reveal` 元素在父幻灯片获得 `.visible` 类时播入，`nth-child` 阶梯延迟（source/frontend-slides/html-template.md:59-76）。6/34 套 design.md 另外定义了 `data-anim` + `data-delay` 离散延迟步进（0/0.08/0.18/0.3/0.44/0.6/0.78/0.96s，source/frontend-slides/bold-template-pack/templates/monochrome/design.md:418）。

**关键判断：这个项目没有"动效档位"概念。** 动效多少由所选模板的情绪决定，不是用户可调的旋钮；唯一的降级通道是 prefers-reduced-motion（source/frontend-slides/viewport-base.css:126-133）。source/frontend-slides/html-template.md:163-169 倒是把 custom cursor、粒子背景、视差、磁吸按钮列为"可选增强"，但无系统化分档。

### 2.5 图片策略

有图时的完整管线（source/frontend-slides/SKILL.md:114-126 + source/frontend-slides/html-template.md:258-324）：

1. **评估先于排版**：扫描用户图片文件夹 → 逐张用视觉能力判读（USABLE/NOT USABLE + 理由 + 主色）→ **图片与大纲协同设计**（"This is NOT 'plan slides then add images'"，source/frontend-slides/SKILL.md:123）。3 张截图→3 个功能页，1 个 logo→封面/封底。
2. **logo 进预览**：把可用 logo base64 嵌进 3 个风格预览，让用户看到"自己品牌在三种风格下的样子"（source/frontend-slides/SKILL.md:126）。
3. **Pillow 处理**：圆形裁切（圆角美学下的 logo）、>1MB 缩到 1200px、`_processed` 后缀永不覆盖原图（source/frontend-slides/html-template.md:266-294）。
4. **引用方式**：直接文件路径而非 base64（"presentations are viewed locally"，source/frontend-slides/html-template.md:298），`assets/` 目录。

**占位图**：10/34 套 design.md 定义了 img-placeholder 组件（grep 实测；如 monochrome 的"hairline 边框奶油色空块 + 居中 mono 标签"，source/frontend-slides/bold-template-pack/templates/monochrome/design.md:170-174；studio 的整页封面占位，source/frontend-slides/bold-template-pack/templates/studio/design.md:145-148）。但这只是视觉样式定义，**没有"占位图即换图指南"的协议设计**，也没有运行时替换机制。

**无 AI 生图路径**：预设层明令"no illustrations"（source/frontend-slides/STYLE_PRESETS.md:3），无图时 CSS 渐变/形状/图案是"fully supported first-class path"（source/frontend-slides/SKILL.md:206）。

### 2.6 可编辑性与契约

就地编辑被明确定位为 **post-draft affordance**：Phase 1 故意不问编辑行为（"Users should not have to choose editing behavior before seeing a draft"），默认包含，除非用户要求锁定版（source/frontend-slides/SKILL.md:108；source/frontend-slides/html-template.md:177-179）。

交互细节是血泪经验：**不要用 CSS `~` 兄弟选择器做 hover 显示编辑按钮**——按钮初始 `pointer-events:none`，鼠标从热区移向按钮时离开热区、按钮在点击前消失（hover 链断裂）。必须用 JS + 400ms 延迟宽限（source/frontend-slides/html-template.md:181-256，含完整代码）。进入方式三通道：左上角热区 hover / 热区点击 / E 键（编辑文本时跳过）。

**但必须诚实指出：该项目的编辑能力止步于此。** 全仓库没有 contenteditable 的序列化规范、没有可编辑标记契约（无 data-editable 类属性）、没有图片替换编辑；"Auto-save to localStorage"（source/frontend-slides/html-template.md:173）只是一行清单，"Ctrl+S to save"（source/frontend-slides/SKILL.md:269）只出现在交付话术里，保存到文件的实现完全留白。deck-stage.js 里的 `data-om-validate` / `data-noncommentable` 属性（source/frontend-slides/bold-template-pack/deck-stage.js:56, 347）暗示源仓库有过批注/校验流程的配套工具，但该工具不在此仓库内。

### 2.7 质量保障与校验

- **截图验证而非数值验证**：明确要求"verify rendered output for both text overflow and panel overlap. `scrollHeight` checks alone are not enough because grid panels can visually cover each other"（source/frontend-slides/SKILL.md:225；同样表述在 source/frontend-slides/bold-template-pack/README.md:76-77）——认识到 DOM 数值检查查不出视觉遮挡。
- **Mode C 修改后验证**：任何修改后检查 16:9 保持、文字不溢出卡片、面板不重叠、1280×720 加一个手机视口截图（source/frontend-slides/SKILL.md:82）。
- **export-pdf.sh 的鲁棒性设计**（418 行）：起本地 HTTP 服务（字体与相对路径图片需要 HTTP）→ 等 `document.fonts.ready` → 首屏等 1.5s 让动效落定 → **三策略兜底切页**（直接操作 .slide 显隐 / 调 `window.presentation.goToSlide` / scrollIntoView，source/frontend-slides/scripts/export-pdf.sh:229-256）→ **强制所有 .reveal 元素置为终态**（否则入场动效在截图里是透明的，source/frontend-slides/scripts/export-pdf.sh:264-276）→ 截图拼 PDF。`--compact` 降 1280×720 省 50-70% 体积。
- 约束：依赖 `.slide` 类名约定，外部 HTML 不适用（source/frontend-slides/SKILL.md:356）。

没有 guizang 那样的"输出溢出 px 数"的量化校验闭环；它的 QA 更偏"流程纪律 + 浏览器截图复核"。（判断）

### 2.8 工程化与防漂移

**渐进披露是最体系化的一家**，三级加载纪律：

1. 先读 selection-index.json（858 行紧凑元数据）做短名单；
2. 只读入选候选的 preview.md（约 55 行的"风格卡"：metadata + Visual Snapshot + Preview Ingredients + Preview Rules）；
3. 用户拍板后**只读那一套** design.md。

并且明文禁止："Do not bulk-read source/frontend-slides/bold-template-pack/templates/*/design.md"（source/frontend-slides/bold-template-pack/selection-index.json:10）、"Do not read every design.md in the pack"（source/frontend-slides/bold-template-pack/README.md:21）。这与 SKILL.md 末尾的 Supporting Files 表（每个文件标注"When to Read"，source/frontend-slides/SKILL.md:367-380）共同构成上下文预算控制。

**防漂移的具体机制**：
- viewport-base.css "include its full contents in every presentation"（source/frontend-slides/SKILL.md:52）——基础设施逐字复制，与 open-design 的 SLOT 骨架同思路。
- design.md 是 "style recipe, not content to copy"（source/frontend-slides/bold-template-pack/README.md:55-56）：保字体/色板/装饰词汇/间距节奏/组件语法，但不许照抄 demo 内容（source/frontend-slides/SKILL.md:223）。
- 源模板的 vw/vh/clamp 值是"设计比例"，必须换算为 1920×1080 固定坐标，不得保留为流体规则（source/frontend-slides/SKILL.md:220-221；每个 design.md 开头还有一段"Fixed-Stage Policy"声明此优先级高于文件后文的响应式描述，source/frontend-slides/bold-template-pack/templates/monochrome/design.md:177-185）。
- 每套模板的 Iteration Guide 把"新增元素时的一致性"写成编号不变量（见 §2.2）。

### 2.9 叙事方法论

- Phase 1 四问一次问完（目的/长度/内容就绪度/密度），有结构化提问 UI 就用（source/frontend-slides/SKILL.md:91-107）。
- 内容侧没有叙事弧方法论（无 codex 那样的冲突/英雄结构），叙事指导止于密度表的"one idea per slide"（source/frontend-slides/SKILL.md:60）。（判断）
- pptx 转换保留演讲者备注为 HTML 注释（source/frontend-slides/SKILL.md:257）；deck-stage.js 另支持 `<script type="application/json" id="speaker-notes">` 并在翻页时 postMessage 给宿主（source/frontend-slides/bold-template-pack/deck-stage.js:5-6, 453-463, 491-492）。

## 3. 辩证评估（对照七条最优标准）

**① 高/低密度双档 × 设计感超过 guizang**

做到了什么：密度双档是显式产品决策（Phase 1 第四问，source/frontend-slides/SKILL.md:102-107），且密度深入模板选型元数据与每套模板的 density philosophy 专段——比"全局两档规则"更细腻：它承认密度是视觉系统的内生气质（sparse 的 Ivory Ledger 与 populated 的 Pin & Paper 不可互换）。设计感供给是六家里最厚的：12 预设 + 34 套策展 design.md，每套带 token 表 + Do/Don't + Iteration Guide + Known Gaps，枚举项全部带规则与理由，直接命中元原则"枚举必须附带规则与验收标准"。

缺什么（判断）：高低密度只影响"选哪套模板 + 拆页策略"，同一模板内部的密度弹性没有规则（typography 槽位预算、单页容量表都没有——那些是本项目 typography.md 已建的）。34 套模板的美学几乎全部根植拉丁排版传统，CJK 节是事后补丁而非原生设计；对中文项目的"更有设计感"只能移植其**写法**（design.md 结构），不能移植其**审美内容**。

**② 动效丰富度可调**

没有做到"可调"。它的动效组织轴是情绪（Effect-to-Feeling，source/frontend-slides/animation-patterns.md:7-14），动效量由模板气质决定，用户没有"丰富/克制"旋钮；唯一降级是 prefers-reduced-motion。入场动效只有 fade-up/scale/left/blur 四类 + 阶梯延迟，拆字、滚动驱动、编排式时间线都没有。合理之处在于：它的目标场景是"快速出一份能看的演讲 deck"，动效是氛围不是主角；对本项目"各档都足够吸引眼球"的目标，这套供给明显不够。（后半为判断）

**③ 复杂 fancy 信息图**

部分做到。design.md 的 components 区有信息图组件配方：stat-cell、timeline-dot、vtimeline-spine、pyramid-bar（color-mix 渐层）、insight-card、无箭头流程图（whitespace 表顺序，source/frontend-slides/bold-template-pack/templates/monochrome/design.md:383）等，且每个组件带"为什么长这样"的 description。但它们是**组件词汇表，不是信息图语法**——没有组合规则、没有数据到视觉的映射规范、没有"何时用哪种图"的内容类型匹配。fancy 程度上限就是"策展过的编辑风组件"，不到"复杂 fancy 信息图"。（判断）

**④ 复杂标注、交互动效、图表全覆盖**

不够。图表是手绘 CSS：bar（inline `style="height:XX%"` 手写高度，无数据绑定层，source/frontend-slides/bold-template-pack/templates/monochrome/design.md:492）、donut（conic-gradient + ::after 裁切，且依赖背景色一致——Known Gaps 自己承认的坑，source/frontend-slides/bold-template-pack/templates/monochrome/design.md:488）、pie/pyramid/timeline。30/34 套 design.md 提到 chart（grep 实测），但类型集中在 stat/table/timeline/flow/pie/bar/donut/pyramid，无折线、无散点、无雷达、无交互图表、无图表库。复杂标注（引线、注释层）不存在。交互动效止于 3D tilt 与 hover（source/frontend-slides/animation-patterns.md:80-100）。

**⑤ 图片占位（占位图即换图指南）**

有一半：10/34 套模板定义了 img-placeholder 的视觉样式（含标签文案），占位块本身是设计系统的一部分而非丑补丁——这个理念对路。但没有把占位做成**换图协议**：占位里没有"该放什么图、什么比例、去哪换"的指引规范，更没有编辑器联动。它的占位是"等摄影图到位"的静态提示，不是"占位即指南"。（后半为判断）

**⑥ 双图片模式**

明确只有一半：b) 纯 CSS 视觉 + 用户上传图 是一等路径（source/frontend-slides/SKILL.md:206），assets/ 目录与图片处理管线完整；a) AI 自主绘图插画 被**明确排除**——"Abstract shapes only — no illustrations"（source/frontend-slides/STYLE_PRESETS.md:3），creative-mode 模板甚至写明"Icons and illustrations are CSS-only geometric shapes. No external images or SVGs needed"（source/frontend-slides/bold-template-pack/templates/creative-mode/design.md:556）。编辑器内换图落盘 assets/ 不存在（无编辑器）。对本项目，它的图片管线（评估→协同大纲→Pillow→assets/ 引用）可移植，双模式要自己建。

**⑦ 全部就地可编辑、可批注**

最弱的一条。有 contenteditable 编辑模式的产品判断（默认开启、事后提供、E 键+热区三通道、400ms hover 宽限的血泪方案），但没有标记契约、没有序列化保存实现、没有批注（见 §2.6）。它证明了"零依赖单文件 + 就地编辑"的产品形态成立，工程深度则远不及 dashi 的 data-editable-path 契约或本项目 editor.html。（判断）

**元原则对照**（判断）：这个项目是"枚举要谨慎、枚举项必须带规则与验收"的最佳正面教材——34 套 design.md 每套都把枚举写成了可执行规范（token + rationale + Do/Don't + Iteration Guide + Known Gaps），且用三级渐进披露控制枚举对上下文的膨胀。原则层（反 slop、Show Don't Tell、固定舞台）极突出，枚举层被纪律约束。这正是本项目元原则想要的形态。

## 4. 结论：拿什么 / 不拿什么 / 差距

**拿什么**

1. **design.md 的写法**（最高价值）：token frontmatter + Overview 叙事 + Density philosophy + Do/Don't + Iteration Guide + Known Gaps + CJK 专节的七段结构，作为本项目 themes.md 每套主题枚举项的升级模板。
2. **三级渐进披露**：紧凑索引（带 mood/tone/density/formality 七字段元数据）→ 轻量 preview 卡 → 只读选中一套全文 + 明文禁止 bulk-read。本项目 editor.html 主题面板与技能的 themes.md 都可套用。
3. **Preview authenticity 禁令**：预览/产物里不得出现 "Option A/B/C"、模板名、流程标签（source/frontend-slides/SKILL.md:180-187）——本项目生成侧同样需要这条防污染规则。
4. **图片协同大纲**：图片评估先于排版、"3 截图→3 功能页"的映射思路、logo 进预览（source/frontend-slides/SKILL.md:114-126）。
5. 血泪规则三条：幻灯片切换禁用 display:none（用 visibility，source/frontend-slides/SKILL.md:47）、`-clamp()` 静默失败写 `calc(-1*clamp())`（source/frontend-slides/SKILL.md:50）、编辑按钮 hover 用 JS+400ms 而非 CSS `~`（source/frontend-slides/html-template.md:181-256）。
6. export-pdf.sh 的"强制 .reveal 终态再截图"（source/frontend-slides/scripts/export-pdf.sh:264-276）——一切基于入场动效的 deck 做无头截图/导出的通用对策。

**不拿什么**

1. **横向切页交互**（键盘/触摸/滑轮翻页、deck chrome）——与本项目 16:9 竖向滚动形态不兼容，交互代码整体不可复用；缩放与 chrome 外置的思路已吸收。
2. **34 套模板的审美内容**——拉丁排版传统，CJK 是补丁；只移植写法不移植主题。
3. **情绪轴动效组织**——本项目需要"强度档位"轴，它的 Effect-to-Feeling 只能作为各档内部的选型参考。
4. **Vercel 部署/PDF 导出链路**——本项目交付物即 HTML 文件 + 编辑器保存，不需要部署脚本；PDF 导出若有需求可直接借 export-pdf.sh 的思路。
5. **localStorage 自动保存 + 无契约编辑**——本项目已有更完整的 FSAA 写回 + data-editable 契约。

**与最优方案的差距**（对照本项目 skills/html-pptx/ v1.4 现状）

- 本项目 v1.4 已有它不有的：data-editable 可编辑契约、编辑器就地编辑/批注/FSAA 保存、竖向滚动形态、容量先于版式的槽位预算（skills/html-pptx/references/typography.md）。
- 它领先本项目 v1.4 的，集中在**主题枚举的深度与写法**：本项目 themes.md 的 13 套主题是 token 级策展，而它的 design.md 是"token + 组件词汇 + 密度哲学 + 迭代不变量 + 已知坑"的系统级策展，直接支撑最优标准①（双档都有设计感）和③（信息图组件配方）；本项目主题若升级到 design.md 写法，③④的组件/图表配方也有了落点。（判断）
- 动效分档（②）、AI 生图模式（⑥a）、占位图协议化（⑤）两边都没有完整答案，是本项目的自研空间；它的实践表明：动效不做档位也能交付，但满足不了"各档都吸引眼球"。（判断）
- 防漂移上，它的"preview 卡 + 单套 design.md + 禁止 bulk-read"与本项目骨架逐字复制（skills/html-pptx/assets/skeleton.html）互补：一个防**上下文膨胀**，一个防**基础设施重写漂移**。（判断）
