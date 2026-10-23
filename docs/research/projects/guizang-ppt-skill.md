# guizang-ppt-skill 深度调研

> 一行定位：单文件 HTML 横向翻页网页 PPT，双风格锁定（电子杂志 × 电子墨水 / 瑞士国际主义），以"种子模板 + 策展主题只选不改 + 登记版式锁 + 校验脚本闭环"为核心策略 · 来源：source/guizang-ppt-skill/ · 调研日期 2026-09-17 · 索引：../source-survey.md

## 1. 定位与产物形态

- 产物是**单个 `index.html`**（CSS、WebGL shader、翻页 JS、演讲者模式全部内嵌在模板里）+ 同级 `images/` 图片目录，直接双击浏览器打开即可演示，无需本地服务器（source/guizang-ppt-skill/SKILL.md:528-536）。
- 两种互斥风格（source/guizang-ppt-skill/SKILL.md:14-29）：
  - **风格 A · 电子杂志 × 电子墨水**（默认）：WebGL 流体/色散背景 + 衬线标题（Noto Serif SC + Playfair Display）+ 等宽元数据，美学锚点是 *Monocle* 杂志。
  - **风格 B · 瑞士国际主义**：WebGL 网格/点阵背景 + 全程无衬线（Inter/Helvetica/Noto Sans SC）+ 单一高饱和 accent 色（IKB 蓝/柠檬黄/柠檬绿/安全橙四选一），锚点是 Massimo Vignelli。
- 两风格**类名互不通用、不可混用**——同名 class（如 `h-hero`）在两个模板里视觉完全不同（source/guizang-ppt-skill/SKILL.md:193, 250-253）。
- 共享一套重型演示运行时：横向翻页（键盘/滚轮/触屏/ESC 总览）、`P` 演讲者模式、观众屏 postMessage 同步、SPEAKER_NOTES 讲稿、分组计时、排练记录、激光笔/圈选、黑白屏/冻结、断线恢复、演前检查（source/guizang-ppt-skill/SKILL.md:31；references/presenter-mode.md:90-165）。
- 自己声明的边界：**"大段表格数据、图表叠加（用常规 PPT）；培训课件（信息密度不够）；需要多人协作编辑（这是静态 HTML）"**都不适合（source/guizang-ppt-skill/SKILL.md:43-46）。它本质是低密度演讲型工具。

## 2. 方案详解

### 2.1 画布与适配：100vw×100vh 流体，vw/vh 排版

- 每页 `.slide{width:100vw;height:100vh}`，`#deck` 是一个 `10000vw` 宽的 flex 横排容器，用 `transform` 平移翻页；JS 启动时把宽度矫正为 `total*100vw`（source/guizang-ppt-skill/assets/template.html:43-44, 693-694）。
- **没有固定设计画布**：字号全部用 vw 表达（如 `.display{font-size:11vw}`、`.h1-zh{font-size:4.6vw}`），小字用 `max(14px,.82vw)` 这类下限钳制防小屏不可读（source/guizang-ppt-skill/assets/template.html:78-86；template-swiss.html:236-257）。
- 风格 B 的大字号用 **`min(Xvw, Yvh)` 双约束**防 16:9 屏高度溢出，且经验规则 `Y ≥ X × 1.6`（source/guizang-ppt-skill/references/checklist.md:187；layouts-swiss.md:131-140）。这是"vw 主导、vh 兜底"的修正，不是固定坐标系。
- 风格 B 的页面容器是 `.canvas-card`：`100vw × 100vh`、直角、padding `5.6vh 5vw 4.4vh`，页眉/主体/页脚共用同一条 5vw 边线（source/guizang-ppt-skill/references/layouts-swiss.md:84-87, 93-110）。
- 设计理由：流体适配任何屏，但代价是**溢出风险转移到生成侧**——内容多少会直接撑破页面，所以必须配套渲染测量校验（见 §2.9）。

### 2.2 主题与视觉语言：策展预设"只选不改"，token 整体替换

- 主题只有预设、**禁止自定义 hex、禁止混搭**，理由是"颜色搭配错了画面瞬间变丑，保护美学比给自由更重要"（source/guizang-ppt-skill/SKILL.md:206-207, 223-226；references/themes.md:3, 116-120）。
- 换肤机制：主题文件给出 `:root` 变量块，**整体替换**模板里标"主题色"注释的几行，其余 CSS 全部走 `var(--...)`，零额外改动（source/guizang-ppt-skill/references/themes.md:8-13；themes-swiss.md:8-13）。风格 A 5 套暖纸色系（themes.md:17-93），风格 B 4 套共享同一组"高级灰"灰阶、只换 accent（themes-swiss.md:147-157）。
- 风格 A 的字体分工是硬规则：标题衬线、正文非衬线、元数据等宽（source/guizang-ppt-skill/SKILL.md:499；template.html:25-27 定义三套字体变量）。
- **主题节奏是硬规则而非建议**：每页 section 必须带 `light`/`dark`/`hero light`/`hero dark` 之一；连续 3 页同主题不允许；8 页以上必须 hero dark 和 hero light 各 ≥1；每 3-4 页插一个 hero 页；生成后 `grep 'class="slide'` 自检（source/guizang-ppt-skill/SKILL.md:283-291；layouts.md:119-140）。hero 页通过降低遮罩透明度让 WebGL 背景透出，形成明暗呼吸（template.html:49-58）。
- WebGL 背景：风格 A 暗页用"全息色散"shader（彩虹微扰+鼠标径向涟漪）、亮页用 domain-warp 涡流 shader，两张 fixed canvas 按页面主题切换前景（source/guizang-ppt-skill/assets/template.html:559-685）；风格 B 的网格背景会读取 `--accent` 变量做鼠标附近高亮（references/themes-swiss.md:132）。

### 2.3 密度与字排：单档低密度 + 字重阶梯 + 中文分档

- **没有密度双档概念**。它的密度策略是"装不下就拆页、换版式，绝不缩字号"：演示最小字号下限为正文 18px / 卡片与 caption 16px / meta 与图表标签 14px（source/guizang-ppt-skill/SKILL.md:415-423）。
- 中文大标题字号分档表：按"1 行 ≤8 字 / 2 行 / 3 行"给出 `min(6.4vw,11.2vh)` 等四档，规则是"先改短标题、再降字号"（source/guizang-ppt-skill/SKILL.md:400-411；layouts-swiss.md:42-52）。
- **字重阶梯**（"越大越细，越小越粗"的具体映射）：≥8vw→200，4-7.9vw→200-300，1.8-3.9vw→300-400，16-20px→400-500，13-15px→500-600；同页内小字元素字重必须 ≥ 大字元素（source/guizang-ppt-skill/SKILL.md:425-438）。这是把感性原则量化成可检查规则的典型样本。
- 溢出修正按 px 分级阶梯：1-40px 只微调间距、40-90px 局部压缩、90-160px 压标题或正文、160px+ 才换版式/删内容；修过头（底部空白变大）要回滚（source/guizang-ppt-skill/SKILL.md:471-478；checklist.md:252-273）。

### 2.4 版式系统：风格 A 十骨架自由粘贴，风格 B 二十二版式锁死

- 风格 A：`layouts.md` 提供 10 种可直接粘贴的 `<section>` 骨架（封面、幕封、数据大字报、左文右图、图片网格、Pipeline、悬念页、大引用、对比、图文混排），"不要从零写 slide"（source/guizang-ppt-skill/SKILL.md:293-311）。
- 风格 B 进入 **Swiss locked mode**：正文页只能用登记的 S01-S22（外加封面/封尾 ASCII 两个特例），每个 `<section>` 必须写 `data-layout="Sxx"`，禁止发明 P23/P24 等未登记结构（source/guizang-ppt-skill/references/swiss-layout-lock.md:9-18；SKILL.md:314-321）。登记表的每一项带"必须保留的骨架 + 图片规则"两列（swiss-layout-lock.md:21-44）。
- **内容类型 → 版式的匹配表带禁区**：有真实量化数据必须用 P6/P7/P20/P21，纯定性论断严禁用图表版式（"编造 96/88/78 会被识破"），Before/After 必须正好 2 项……（source/guizang-ppt-skill/references/layouts-swiss.md:860-882）。这是本项目 components.md "内容门槛"规则的直接先声。
- **版式多样性配额**：7-8 页 deck 至少 6 个不同 S 版式，10 页以上至少 8 个；禁止连续 3 页同主体结构；写代码前先列 `页码 → data-layout → 选用理由 → 图片槽位` 草稿（source/guizang-ppt-skill/SKILL.md:354-359）。
- 唯一登记的交互扩展：S08 右槽位可换 MapLibre 地图组件（点位/连线/HTML 卡片/右上角 +-DRAG 控件，默认禁滚轮缩放避免抢翻页），仍算 S08 不算新版式（swiss-layout-lock.md:46-55；references/swiss-map-component.md:11-19）。

### 2.5 图表：三种内置图形，明确不覆盖复杂图表

- 风格 B 模板内置图表只有三类：KPI Tower（不等高柱）、H-Bar Chart（横条排名）、spec-bars（竖向规格条），全部是 HTML/CSS 结构（source/guizang-ppt-skill/SKILL.md:273）。
- **SVG 只许画几何、禁止 `<text>`**——所有标签必须放 HTML 网格/卡片/caption 里（swiss-layout-lock.md:16；validator 强制，validate-swiss-deck.mjs:86-88）。这保证文字可选中、样式统一，但也封死了复杂标注型图表。
- 没有饼图/折线/散点/面积等任何通用图表系统；SKILL.md 自己说图表叠加场景"用常规 PPT"（SKILL.md:44）。

### 2.6 动效：语义 recipe 字典，动效绑内容语义而非统一 fade

- 引擎是 Motion One（约 4KB），加载策略**本地 `assets/motion.min.js` 优先、jsdelivr CDN 兜底、双失败则强制 `opacity:1` 全量 reveal**——"内容永远可读，演示不依赖网络"（source/guizang-ppt-skill/references/components.md:374-392）。
- 风格 A 有 5 种 recipe（cascade/hero/quote/directional/pipeline）+ 选择决策树；pipeline recipe 会把翻页键劫持成分步点亮（components.md:409-425, 437-438）。
- 风格 B 内置 **21 个语义化 recipe**（`hero`/`progression`/`measure-up`/`bar-grow`/`loop-form`/`matrix-fill`……），每个与版式图形耦合：KPI 塔从底 scaleY 生长、bar 宽 0→target、矩阵按对角线波 `(i+j)*.055` 扫入、SVG 节点按时钟序点亮（source/guizang-ppt-skill/assets/template-swiss.html:2263-2318, 2490-2520, 2761-2783）。硬规则"每页一个语义化 recipe，禁止所有页用同一个 generic fade-up"（SKILL.md:515）。
- 缓动从 `:root` 的 IBM Carbon motion token 经 `getComputedStyle` 读取，"CSS 是唯一事实源"（template-swiss.html:2136-2144）。
- 关键工程细节：`playSlide` 入口先把本页所有 `[data-anim]` 容器强制 `opacity:1`，recipe 内再用 `{opacity:[0,1]}` 覆盖——防止"容器是占位标记、几何动画在子元素上"时整页不可见（template-swiss.html:2807-2812）；ESC 总览的克隆缩略图必须强制 reveal（template-swiss.html:605-606；SKILL.md:517）。
- 降级链完整：`B` 键低功耗模式停 RAF + 取消 Web Animations + 静态最终态（template.html:666-685；SKILL.md:520）；`prefers-reduced-motion` 同理（template-swiss.html:1194）。
- **没有"丰富度档位"概念**——动效只有开/低功耗关两态，档位差异靠 recipe 本身的语义差异体现。

### 2.7 图片策略：槽位-比例绑定 + 同名覆盖 + GPT-M 配图 + 截图程序化适配

- 资产落盘纪律：图片放 `images/` 目录，命名 `{页号}-{语义}.{ext}`（页号补零便于排序），规格建议 ≥1600px 宽、总量 ≤10MB；**替换方式=同名覆盖**（HTML 不用改路径）（source/guizang-ppt-skill/SKILL.md:125-138）。
- **图片槽位契约 `data-image-slot`**：风格 B 每张本地图必须标槽位（如 `s22-hero-21x9`），槽位决定生成比例与容器类；validator 静态强制（SKILL.md:379；validate-swiss-deck.mjs:90-124）。"先确定版式和槽位，再生成图片"是硬规则（swiss-layout-lock.md:17）。
- 占位机制：风格 A 有 `.img-slot` 虚线框占位符（`+` 号 + 语义标签），但这是"图片未就位"的临时态，不是交付物的一部分（components.md:299-307）；SKILL.md 也承认"没图的图文页没法验证视觉效果"（SKILL.md:138）。
- 比例纪律：禁止用原图奇葩比例，各场景有标准比例表（21:9 顶图 / 16:10 左文右图 / 网格固定 `height:Nvh` 不用 aspect-ratio）；照片 `object-fit:cover` 只裁底部，S22 用 `object-position:center 35%` 防截人脸，文字密集图用 `.fit-contain`（SKILL.md:361-386；layouts.md:15-29）。还有一个完整的图文混排决策树（证据截图保真 / 重生成铺满 / 照片标准比例 / 文字压图需 30% quiet-zone）（SKILL.md:388-398）。
- **AI 配图管线**（Codex 环境 GPT-M 2.0）：7 种图片类型各有基础提示词；提示词后缀统一约束比例/留白/"不要生成页眉页脚页码署名"（避免和 deck chrome 重复）；同组多图追加一致性后缀（references/image-prompts.md:1-15, 53-65；SKILL.md:397）。
- **截图美化管线**：优先程序化适配（目标比例画布 + 内置主题背景 WebP + 等比缩放 + 语义化 padding/alignment），GPT-M 重画只用于原图不可用；7 个语义参数（ratio/background/padding/inset/shadow/corners/alignment）按风格 A/B 分别有默认值映射；内置 9 张 crop-safe 背景资产（references/screenshot-framing.md:5-9, 23-47, 85-110）。

### 2.8 可编辑性与契约：只有"演讲备注契约"，没有页面内容编辑

- 唯一的 data 契约是 `data-slide-id`：小写语义 slug、重排不换、禁止页码——但它服务的是**演讲者备注按 ID 存 localStorage 防串页**，不是内容编辑（source/guizang-ppt-skill/references/presenter-mode.md:32-42；SKILL.md:232）。
- `SPEAKER_NOTES` 是结构化讲稿 schema：`id/title/purpose/talk/transition` 必填，`cue/interaction/delivery/advance/fallback/pronunciation/autoAdvanceSeconds` 可选，缺失信息省略字段而非编造（presenter-mode.md:44-88）。
- 页面文字**完全不可就地编辑**；修改方式是回到 AI coding 迭代，"90% 的调整都是改 inline style"（SKILL.md:540-542）。

### 2.9 质量保障与校验：预检 → 静态校验 + 渲染测量 → 案底式清单

- **Pre-flight 类名预检**："这是所有生成问题的源头"——写 slide 前先读模板 `<style>` 块，确认用到的每个类都有定义；模板是类名唯一来源，缺类在模板里补、不发明新类（SKILL.md:246-262；checklist.md:308-318）。
- `validate-swiss-deck.mjs`（311 行）双阶段：静态检查（data-layout 白名单、实验版式拦截、标题对齐、SVG text、图片槽位绑定）+ **Playwright 真实渲染测量**（可解析到 playwright 才跑）——量出每页 DOM/visual overflow 的具体 px 与肇事元素、底部空白与 active ratio、nav 安全线（93vh）、标题-内容间距 M2，且 overflow 错误信息**内嵌修正阶梯建议**（validate-swiss-deck.mjs:20-26, 45-124, 127-296）。
- `validate-presenter-mode.mjs`：校验 data-slide-id slug 合法性/唯一性、用 `node:vm` 沙箱解析 `SPEAKER_NOTES` 数组、检查必填字段、总时长 ≤90% 预算、演讲者运行时控件齐全（validate-presenter-mode.mjs:40-58；SKILL.md:446-454）。
- `checklist.md`（634 行）是 **P0-P3 分级的"案底"**——每条都是"现象→根因→做法"结构，标注"吸取 P15/P20/P22 教训"这类出处（checklist.md:9-306）。SKILL.md 强制"生成完逐项对照"（SKILL.md:442-444）。
- 要求"不只看代码"：开网页逐页视觉核对、等动效稳定再截图、以实际页面用法而非 raw CSS helper 为准（SKILL.md:480-489；checklist.md:294-305）。

### 2.10 工程化与防漂移：golden source 守卫 + 运行时同步 CI

- `template-swiss.html` 被明确定义为 **golden source**（由作者原始参考 PPT 派生，原文件不随仓库分发，S01-S22 即其版式快照）；修改模板前必须做原始对比，可接受差异有明确白名单（checklist.md:277-292；swiss-layout-lock.md:5-7）。
- 两份模板的演讲者模式 CSS/JS 用**注释边界标记圈出**，`check-presenter-runtime-sync.mjs` 逐字节比对两块必须 identical，且有 GitHub Actions workflow 在模板变更时自动跑（scripts/check-presenter-runtime-sync.mjs:8-38；.github/workflows/presenter-runtime-sync.yml:1-24）。
- Step 0 每次启动先 `git fetch` 检查上游更新（询问后 `--ff-only`，不自动更新）（SKILL.md:50-65）。
- 防漂移的主手段仍是"文案纪律"：模板是唯一类名来源、不要发明类名、自定义一律 inline style（SKILL.md:262；layouts.md:13）。

### 2.11 叙事方法论：7 问澄清 + 叙事弧 + 双轨页计划表

- 动手前 7 问（风格/受众/时长/素材/图片/主题色/硬约束），每问附"为什么要问"；时长直接映射页数（15 分钟 ≈ 10 页）（SKILL.md:78-88）。
- 无大纲时用五段叙事弧（钩子→定调→主体→转折→收束）搭骨架，"叙事弧 + 页数规划 + 主题节奏表三张表对齐后再进 Step 2"（SKILL.md:104-114）。
- 正式演讲的页计划表是**双轨**：除"这页放什么"外还规划"台上说什么"（页面目的/观众可见/演讲者补充/建议时长/转场），默认提词卡而非逐字稿，总时长 ≤90% 预算留缓冲（SKILL.md:116-121）。

## 3. 辩证评估（对照七条最优标准）

**① 高/低文字密度双档下的设计感。**
它只有低密度一档，且是自觉选择：SKILL.md 明说培训课件"信息密度不够"不适用（SKILL.md:43-46），最小字号 18/16/14px 的下限（SKILL.md:415-423）在物理上封死了高密度排版。在其目标场景（发布会式演讲）这是合理的——低密度正是"杂志感"的前提；而且它的低密度设计感确实是六家里打磨最深的：字重量化阶梯（SKILL.md:425-438）、中文分档、`min(vw,vh)` 双约束、明暗节奏硬规则，都是可检查的规则而非口号。但对本项目"高密度阅读型 deck 也要有设计感"的目标，它**没有提供任何机制**——没有高密度字阶、没有紧凑组件、没有密度决策入口。

**② 动效丰富度可调且各档吸睛。**
动效质量高但**不可调档**：只有"语义 recipe 开 / B 键低功耗全关"两态（template.html:666-685）。风格 B 的 21 个语义 recipe 确实是"动效绑内容语义"的最佳实践样本（对角线波、scaleY 生长、stroke 描线），比统一 fade-up 高一档；但 recipe 字典是**枚举死在模板 JS 里**的——用户无法选"再热闹一点"或"再克制一点"，新增 recipe 必须改模板源码，违反本项目"骨架不改一字"的纪律方向。它的降级链（本地→CDN→静态 reveal→reduced-motion→B 键）值得整条搬走。

**③ 复杂 fancy 信息图。**
S14 Loop、S17 System Diagram、S15 Matrix 这类结构化信息图是有的，且 SVG 几何 + HTML 标签的分层（swiss-layout-lock.md:16）是对的工程选择。但上限被 locked mode 钉死：22 个版式之外即违规（swiss-layout-lock.md:14），"禁止 SVG 写文字"同时封死了标注密集型 fancy 图（如带引线标注的架构图）。它的答案是"不需要的不支持"，不是"支持不了"。

**④ 复杂标注、复杂交互动效、图表全覆盖。**
明确不支持。图表只有 KPI 塔/横条/规格条三类（SKILL.md:273），交互动效只有翻页与演讲控制，复杂标注被 SVG 禁文字规则排除。唯一的页面内交互组件是 MapLibre 地图（swiss-map-component.md），且被刻意做成"默认禁缩放拖动"的半静态件——在它的场景里对（防抢翻页），对"复杂交互"标准则是反例。

**⑤ 图片占位（占位图即换图指南）。**
做到一半。`.img-slot` 虚线占位框（components.md:299-307）只是"图还没来"的临时态，作者自己承认没图就无法验证图文页（SKILL.md:138）；`data-image-slot` 槽位契约 + "先定槽位再生图"（swiss-layout-lock.md:17）是**方向正确的占位思想**，但落点是约束 AI 生图，不是给用户交付"占位图即换图指南"。没有"占位图是交付物"的概念。

**⑥ 双图片模式 + assets/ 落盘 + 编辑器可换图。**
落盘纪律完全达标且是本项目的直接来源：`images/` 目录、`{页号}-{语义}` 命名、同名覆盖即换图（SKILL.md:129-138）。AI 配图（GPT-M 2.0 七类型 + 提示词后缀规范）+ 用户图/截图（程序化适配优先、重画兜底）两条路都有，且比"双模式"更细。但：没有"纯 HTML/CSS 视觉"这一档——风格 A 的 hero 背景是写死的 WebGL shader，不可替换；没有编辑器，换图靠用户手动覆盖文件，"编辑器内上传替换并落盘 assets/"不在它的世界里。

**⑦ 全部文字就地可编辑、可批注。**
完全没有。它唯一的契约（`data-slide-id` + `SPEAKER_NOTES`）服务的是演讲者备注防串页（presenter-mode.md:32-42），页面正文没有任何可编辑标记，修改一律回到 AI coding 改 inline style（SKILL.md:540-542）。这是目标差异而非缺陷：它的交付物是"演示成品"，我们的是"可继续加工的中间态"。

**元原则（原则突出、枚举谨慎；枚举项须带规则与验收标准）。**
它是"原则与枚举并重但枚举超重"的样本：SKILL.md 632 行 + references 约 4900 行，22 版式、5+4 主题、两页类名清单全是枚举。可贵的是**大部分枚举项确实带了规则与验收**：版式表带骨架与图片规则、字重阶梯带数值、checklist 每条带案底。但枚举的**可扩展性靠 validator 白名单硬编码兜底**（validate-swiss-deck.mjs:45-49），新增一个版式要同步改 layout-lock 文档 + 模板 CSS + validator 三处——枚举不可独立扩展。source-survey.md 的批评成立：遵循成本与规则数量成正比。

## 4. 结论：拿什么 / 不拿什么 / 与最优方案的差距

### 拿什么（部分已被 v1.4 吸收）

1. **主题 token 整体替换机制**——`:root` 块整体换、其余全走 `var()`，换肤零风险（themes.md:8-13）。已被 themes.md 13 套主题继承。
2. **渲染测量校验闭环**——Playwright 量出溢出 px 数 + 肇事元素 + 内嵌修正阶梯（validate-swiss-deck.mjs:127-296），比"规则要求去量"高一级。
3. **案底式 checklist 写法**——"现象→根因→做法+出处"的结构，规则随真实踩坑生长（checklist.md）。
4. **动效降级链**——本地→CDN→静态 reveal→reduced-motion→低功耗键，以及"容器先 reveal、recipe 再覆盖"的防消失模式（template-swiss.html:2807-2812）。
5. **图片槽位-比例绑定**与截图程序化适配的语义参数表。
6. **双轨页计划表**与叙事弧前置确认（已被 v1.4 Step 1 吸收）。
7. **golden source 守卫 + 运行时块级同步 CI**——双模板/多副本项目的防漂移工程手段。

### 不拿什么

- 100vw/vh 流体画布与横滑翻页（我们用 1920×1080 固定画布 + transform + 竖滚）；
- 22 版式 locked mode 的版式层枚举（我们把枚举收敛到 token/主题层，版式交给原则）；
- WebGL 背景（依赖 GPU、不可替换、与"纯 HTML/CSS 视觉档"冲突）；
- 整套演讲者运行时（观众屏、激光笔、计时排练）；
- validator 白名单硬编码的枚举维护方式。

### 与最优方案（skills/html-pptx/ v1.4）的差距

v1.4 已在多处反超：占位图是**交付物级**的（主题色抽象 SVG、构图即换图指南，SKILL.md:135-136），优于 guizang 的临时虚线框；可编辑契约（`data-editable` 族）覆盖了 guizang 完全空白的第⑦条；密度双档、骨架逐字复制防漂移分别回应了①与元原则。剩余的明确差距：

1. **校验闭环**：guizang 有可执行的 validator（静态 + Playwright 测量 + 内嵌修复建议）；v1.4 的 Step 5 渲染校验是规则条文（SKILL.md:105-111），`scripts/` 下只有 `sync-themes.mjs`，没有测量脚本。
2. **案底积累**：guizang 的 checklist 是 5 轮以上真实迭代的踩坑沉淀；v1.4 的规则多为前置设计，缺"案底"层。
3. **动效与图形语义的耦合深度**：guizang swiss 是 per-layout 定制编排（对角线波、塔生长）；v1.4 的 `data-anim` 是通用语义角色引擎，吸睛上限低于定制 recipe，但换来了骨架不改与可组合性——这是有意的取舍，差距在"高档位丰富度"尚未兑现。
4. **图片槽位契约**：v1.4 有 assets/ 纪律与占位图，但没有 guizang `data-image-slot` 式的"槽位↔比例↔生成提示词"三方绑定。
