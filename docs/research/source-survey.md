# 参考项目调研（索引）

> 本文是调研体系的**索引层**：六个参考项目的一句话定位、第一性原理分析、结论表。
> 每个项目的方案详解与逐条辩证评估在 `projects/` 下的细节文档；跨项目的最优方案综合判断见 `optimal-solution.md`；枚举层的规范见 `sota-visual-languages.md`。
> 调研日期：2026-09-16（第一轮）/ 2026-09-17（拆分细化）。

## 〇、文档地图

| 文档 | 内容 |
|---|---|
| `projects/guizang-ppt-skill.md` | 归藏 PPT 技能：种子模板 + 锁死主题/版式 + 脚本校验闭环 |
| `projects/frontend-slides.md` | 前端幻灯片技能：1920×1080 固定舞台 + 三槽主题策略（12 预设 / 34 bold 模板 / 自定义）+ 反 AI slop |
| `projects/codex-ppt-skill-main.md` | 整页 AI 生图拼 pptx：门禁式工作流 + 脚本强制的反降级契约 + 带量化验收的风格库 |
| `projects/dashi-ppt-skill.md` | React SSR + 内置编辑器：JSON 契约 + 槽位字数预算 + beam search 全稿版式分配 + state-overlay 持久化 |
| `projects/ppt-master.md` | SVG → 原生可编辑 PPTX：规则效力分级 + spec/lock 双文件 + 内置 SVG 编辑器（双通道编辑/批注先行实现） |
| `projects/open-design.md` | 单 HTML deck + 桌面编辑器：骨架 SLOT 逐字复制 + 编辑桥七轮实测迭代全记录 |
| `projects/slide-paipai.md` | 一套内容双后端渲染（PIL 页图 + python-pptx 原生对象）：统一绘制 API + 后端替换、wrap=square 单段策略、表格边框 XML 顺序坑 |
| `projects/tencent-pptx.md` | SlideDSL（受限 JSX）→ slidep 编译原生 OOXML：量化密度门禁 + DESIGN/STORY 双文档契约 + 风格两层分离与三态路由 |
| `projects/cowart.md` | Codex 原生画布 widget：MCP Apps 嵌入对话 + 消息注入 + 磁盘单源轮询回写 |
| `projects/deepseek-harness.md` | dsh 插件体系：单进程 Cordis + React slot 自定义对话 UI + rpcId 可应答推送 |
| `agent-webui-bridge.md` | **agent↔webui 综合**：两个核心操作（呈现/回收）+ 框架无关的"原生最小协议"构想 + **阻塞式 MCP 工具方案**（2026-10-02 用户提议，当前推荐方向；待评审） |
| `optimal-solution.md` | **综合判断**：以七条最优标准为标尺的逐条辩证结论 + 现状差距表 |
| `sota-visual-languages.md` | **枚举规范**：SOTA 视觉的可衍生性判定 + 枚举项法定结构 + 三级验收标准 |
| `bake-sota-dissection.md` | **整页生图 SOTA 解剖**（2026-10-07）：codex 风格圣经 JSON/标题重构/样张三段式七手法 + 七源横向普查 + 我们烙入指令的结构性差距表 + D1–D6 优化方向 |

## 一、各项目一句话定位

| 项目 | 产物形态 | 核心策略 | 对本项目的价值 |
|---|---|---|---|
| guizang-ppt-skill | 单 HTML，横滑翻页，vw/vh 流体 | 种子模板 + 锁死主题/版式 + 脚本校验 | 主题策展、校验闭环、"案底式"规则写法、字重量化阶梯、图片槽位契约 |
| frontend-slides | 单 HTML，1920×1080 固定舞台 + transform 缩放 | 三槽主题策略（安全预设 / 34 套 bold 模板 / wildcard 自定义）+ 渐进披露 + 反 AI slop 原则 | 画布缩放方案、密度双档、枚举项七段式写法范本、CJK 专节 |
| codex-ppt-skill | 整页 AI 生图拼 pptx | 门禁式工作流（大纲→风格→样张→批量），状态机与反降级由脚本强制 | 叙事方法论、样张门禁、风格枚举带量化验收的范本 |
| dashi-ppt-skill | React SSR 静态 HTML + 内置编辑器 | JSON 契约 + 锁模板填文案 + 受约束 bespoke | 可编辑标记约定、槽位容量预算、beam search 版式分配、四级校验 |
| ppt-master | SVG → 原生可编辑 PPTX | 规则效力分级 + spec/lock 双文件 + 条件加载（SKILL.md 已瘦身为 92 行路由器，规范体量在 references） | 元设计（Hard/Default/Reference 分级）、防上下文漂移、SVG 编辑器双通道（编辑/批注）先例 |
| open-design | 单 HTML deck + 桌面编辑器 | 固定骨架 SLOT 逐字复制 + 提示词即代码 | 骨架防漂移模式、编辑桥架构、编辑模式七轮实测坑清单 |
| baoyu-design（2026-09-19 补） | Claude Design 系统提示词的 Skill 化 | 设计系统文件夹约定 + 编译绑定 + 发散质量标尺 | 主题完备性问卷、差异轴纪律、unforgettable 一问——见 `../design/handover-theme-differentiation.md` §四 |
| html-ppt-skill（2026-09-19 补） | 多文件 HTML deck 播放器 | 36 轻主题 + 15 重主题双层架构 + 主题热插拔 | 主题双层分级、撞脸检测 showcase、语义化 FX——见 `../design/handover-theme-differentiation.md` §四 |
| demo1（2026-09-20 补，用户提供） | omelette 系设计-交付框架的长滚动落地页 | 一方向一文件手工定制 + image-slot Web Component + sidecar 持久化 + 13 组 bespoke 动效 | 密度解剖（`demo1-density-analysis.md`）、框架对比（`demo1-framework-comparison.md`：reframe 裁剪/sidecar 模式/hover 反色可学；运行时拆字等五项收敛同构） |
| slide-paipai（2026-09-24 补，用户提供） | 同一内容 → 1920×1080 页图 + 原生可编辑 PPTX 双产物 | 统一绘制 API + monkey-patch 后端替换；PIL 确定性排版（原子 token 断行/last_y 流式定位）；python-pptx 手写 XML 兜底 | 数字原子化断行基线、wrap=square 单段策略的外部印证、表格边框 XML 顺序、柱图 1.28× 头部余量等数值纪律 |
| tencent-pptx（2026-09-24 补，用户提供） | SlideDSL（受限 JSX）→ slidep CLI 编译原生 PPTX | DESIGN/STORY 双文档契约 + 页级 lint/upsert 原子提交 + 风格结构层/常量层分离与三态路由 | 量化密度门禁（填充率/留白/兄弟卡对齐）、anti_pattern 负向封禁、目录↔扉页逐字一致契约、风格预览卡纪律 |
| Cowart（2026-09-30 补，用户桌面） | Codex 原生 tldraw 画布 widget（MCP Apps 单文件 HTML 嵌入对话） | 网页操作编译成结构化用户消息注入对话 + agent 经 MCP 工具写盘 + widget 轮询刷新；插件打包层跨框架、widget 层仅 Codex 系 | 前端确定性编译 prompt 骨架（mention/来源声明/几何约束/Required tool call）、磁盘单源 + hash 刷新、双轨客户端抽象 |
| deepseek-harness（2026-09-30 补，用户桌面） | 单进程 agent harness（Cordis 插件树 + React slot webui） | 插件双半（host/client）+ 42 slot 席位自定义对话 UI + 信封四象限 rpcId 可应答推送；无 iframe、不支持 MCP Apps | rpcId 应答关联、intent 换肤（通用答案 schema + 专用呈现）、allowlist 事件转发、"Model-visible means logged" |

## 二、关键发现（按主题归并）

### 画布与适配
- frontend-slides / dashi / open-design 三家独立收敛到同一方案：**固定 1920×1080 设计画布 + 单个 transform 整体缩放**，禁止响应式重排。open-design 还记录了缩放实现的踩坑（transform-origin 必须 top left、shell 不能是 grid/flex 包装——注意其仓库内部两代骨架并存且不一致，见 `projects/open-design.md`）。
- 六家的翻页交互（横滑/切页）与我们确定的"16:9 竖向滚动"形态都不兼容，**交互代码不可复用，缩放与 chrome 外置的思路可迁移**。

### 质量保障
- guizang 的闭环最完整：Pre-flight 类名预检 → 生成 → 静态校验 + Playwright 渲染测量（输出溢出 px 数）→ 按"修正阶梯"修复（微调间距→压文案→换版式，不许缩字号）。
- dashi 的校验成本按 AI 自由度配比（bespoke 页才做像素测量）+ 残留默认文案检测 + 资产溯源审计；codex 用脚本状态机强制"聊天里说完成不算完成"。
- open-design 的"固定骨架 + SLOT 注释逐字复制"直接回应了"AI 每轮重写基础设施必然引入微妙 bug"的漂移问题；其宿主侧还有 deck-fix 反向修补兜底（生成侧约束 + 消费侧防御双层并行）。
- ppt-master 的 spec/lock 双文件 + "每页生成前重读 lock"回应长上下文漂移；首页门禁（P01 当方法样本，同类问题 ≥2 即归因方法级偏差）是对"全部生成完再校验"流程的具体改进。

### 一致性与审美
- codex："风格是系统，不是重复构图"——一份 deck 一个视觉身份，但版式必须由内容驱动。
- dashi v4 的反模式清单精准打击 AI 默认审美："不要把所有页面都画成标题+卡片墙""卡片网格最多占三分之一""给标签换色不是设计"；其 beam search 版式分配用工程手段（构图多样性加分、种子化随机打散同分候选）对抗 AI 选择收敛。
- guizang / open-design 的主题纪律："只选不改"——策展预设替代自由度，禁止混搭、禁止自定义 hex。
- frontend-slides 直接对 AI 行为诊断（"你会收敛到 Space Grotesk 和紫渐变白底"），并记录 CSS 静默失败类坑（`-clamp()` 必须写成 `calc(-1 * clamp())`）。

### 可编辑性（我们核心诉求的先行者们）
- dashi：`data-editable-path` 显式标记 + `data-editable-skip` 排除装饰 + 无标记时的启发式兜底（叶子元素 + 行内元素白名单）。**稳定 ID 教训**：不用遍历序号（reflow 会漂移），用"slide key + child-index 路径"。其持久化走 state-overlay（内嵌 JSON 视图模型 + 原子写回），与我们"DOM 即真相"路线不同，但原子写回与媒体哈希落盘可对照。
- open-design 的实测经验：`contenteditable=plaintext-only` 为默认、首击选中二击才编辑（避免截断文本框突然撑高）、源码文件是唯一事实源、补丁原地应用永不重载页面；完整七轮坑清单见 `projects/open-design.md`。
- ppt-master 的内置 SVG 编辑器证明了 **Annotate 双通道**（标记写回 → 用户回 chat → agent 应用注解）是已实践的形态，与我们 editor.html 批注模式同构。
- frontend-slides 的血泪规则：不要用 CSS `~` 兄弟选择器做编辑按钮 hover（pointer-events 断链），用 JS + 延迟。

### 共同的反面教材
- 规范体量过载：guizang 632 行 SKILL.md + 8000 行 references、dashi 263 行塞数十条硬规则、ppt-master 总规范超 1.2 万行（入口虽已瘦身为路由器，上下文成本转移到了条件加载纪律上）。**agent 遵循成本与规则数量成正比**——这印证了"原则突出、枚举谨慎"的设计要求。
- 编辑器与产物耦合（dashi 把 10277 行播放器+编辑器塞进每个产物）、产物是图片完全不可编辑（codex）、防溢出靠运行时缩字号（open-design 的 shrink-to-fit，与"禁缩字号"原则相反），都是我们要避开的。

## 三、第一性原理分析

### 问题 1：AI 生成的幻灯片为什么平庸？
AI 的默认输出收敛到训练分布的均值：居中 hero、紫蓝渐变、卡片墙、Inter 字体。**靠"写提示词让它更努力"无效**，因为收敛发生在决策层而非执行层。
→ 推论：**决策必须前置且外置**。主题、密度、叙事弧在写代码前冻结，且候选项来自人工策展的库（用户可视化选择），AI 只在冻结的约束内发挥。约束不是限制质量，是质量的来源。

### 问题 2：一致性从哪来？
两种路线：锁死版式（guizang 22 版式、dashi 锁模板）换稳定，但压抑内容表达；完全自由则必然漂移。
→ 推论：**一致性应该由 token 系统承载（色/字/间距/动效的少量变量），不由版式复制承载**。版式交给"构图原则 + 内容容量"动态决定。这就是"原则突出、枚举谨慎"的技术含义：枚举只保留在 token/主题/骨架层（这里枚举是保护），版式层用原则（这里枚举是枷锁）。分层判定见 `sota-visual-languages.md`。

### 问题 3：文字溢出为什么根除不了？
因为 AI 在"写完再发现溢出"。人眼检查不可靠，AI 目测更不可靠。
→ 推论：**容量规划先于版式选择**（先数字数/条目数再选构图），**渲染测量代替目测**（脚本量出溢出 px 数），**修复有阶梯**（间距→文案→拆页，缩字号是最后的禁区）。溢出是规划问题，不是排版问题。

### 问题 4：编辑器怎么认识生成的文件？
编辑器与生成器是两个不相识的进程，唯一的通信介质是 HTML 文件本身。
→ 推论：**data 属性即契约**。生成侧必须给每个可编辑元素打稳定语义标记（`data-editable` / `data-slide-id`），这不是可选的修饰，是产物的组成部分。文件是唯一事实源，编辑器的一切操作最终序列化回文件。

## 四、结论：新技能站在谁的肩膀上拿什么

| 设计决策 | 来源 | 理由 |
|---|---|---|
| 1920×1080 固定画布 + transform 缩放 + 竖向滚动 | frontend-slides / open-design（缩放部分） | 三家收敛验证过的保真方案；竖滚是我们自己的形态决策 |
| 固定骨架 skeleton.html 逐字复制 + SLOT 填充 | open-design deck-framework | 消灭基础设施漂移 |
| 主题库"只选不改"，token 即换肤契约 | guizang / open-design directions | 策展保护审美；`var()` 全覆盖使换主题零风险 |
| 规则效力分级（Hard / Default / Reference） | ppt-master | 让原则与清单各就其位 |
| 叙事弧 + 页计划表前置确认 | codex / guizang | 防止边写边想 |
| 容量驱动选版 + 渲染测量校验 + 修正阶梯 | dashi / guizang | 根治溢出 |
| 可编辑标记契约（data-editable 族 + 稳定语义 ID） | dashi / open-design | 我们与编辑器的通信协议 |
| 反模式清单（AI slop 负面清单） | frontend-slides / dashi v4 | 原则性对抗审美收敛 |

**明确不拿的**：横滑翻页交互、演讲者模式（激光笔/观众屏）、编辑器内置进产物、SVG/PPTX 工具链、门禁式多轮人工确认、锁死页面版式的枚举教法（guizang 22 版式 / dashi 1020 模板）、运行时 shrink-to-fit 防溢出。

---

## 五、主流框架补充调研（2026-09-16 第二轮）

对象：reveal.js / Slidev / impress.js / Spectacle / Shower / WebSlides / scrollytelling 模式（scrollama、Pudding 方法论）/ contenteditable 与 FSAA 浏览器现状。

### 结论摘要

1. **我们的形态决策被主流验证**：reveal.js 5.0 Scroll View 的 `compact` 布局（宽=视口宽、高按长宽比推出）与我们 `.slide-slot` 模型完全同构；Shower 的"文档/放映双模"是同一路线的老前辈。WebSlides 证明滚动形态可以不缩放，但代价是放弃版式确定性——我们不走那条路。
2. **缩放方案是行业共识**：reveal（`clamp(min(w/W,h/H))` + min/max 护栏）、Slidev（CSS `scale` 属性 + `transform-origin: top left`）、impress.js（默认画布同为 1920×1080）全部收敛到"固定画布 + 整体缩放"。
3. **骨架采纳的改进**（已实施）：`transform-origin: top center`（修复窄窗口裁剪 bug）、`ResizeObserver` 观察 deck（iframe/侧栏场景）、打印 `print-color-adjust: exact`、reduced-motion 时键盘瞬时翻页、`.slide-slot` 加 `content-visibility: auto`、fit() 阈值去抖。
4. **滚动动效纪律**：scroll-to-trigger，绝不 scrolljack；IntersectionObserver 原生够用，不引库；连续滚动动画可用纯 CSS `animation-timeline: view()` 做渐进增强。
5. **编辑器关键事实**：Firefox 136+ 才支持 `plaintext-only`（降级 + 粘贴拦截是必需品）；transform 缩放容器内的 contenteditable 光标偏移是高危组合，必须多缩放档实测；FSAA 在跨域 iframe 直接 SecurityError（降级路径是必需品）；FSAA 需安全上下文 + 瞬时用户激活；`::before/::after` 内容不进 outerHTML（chrome 类装饰天然"保存即消失"）。
6. **不反向导出 pptx 的决策被佐证**：Slidev 的 `pptx-editable` 实践证明 HTML→可编辑 PPTX 保真天花板很低。

来源明细见调研原始记录（revealjs.com、slidev 仓库文档、caniuse、MDN 等）。
