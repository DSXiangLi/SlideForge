# tencent-pptx 深度调研

> 一句话定位：受限 JSX（SlideDSL）→ `slidep` CLI 编译直出原生 OOXML 的 PPT 生成技能，强项在质量保障的工程化门禁 · 来源：source/tencent-pptx/（用户提供 zip，v20260904，2026-09-24 入库）· 调研日期 2026-09-24 · 索引：../source-survey.md

## 1. 定位与产物形态

腾讯的 PPT 生成技能：每页一个 `.slide` 文件（**受限 JSX 子集**，明确"不是 React"——禁 import/export/hooks/函数组件，最后一个表达式必须是 `<Slide>`，`component-slide.md:30-31`），由 Node 侧 `slidep` CLI（create / upsert-dsl / lint）编译直出原生 PPTX。目录规范：每个 PPT 一个 project_dir，内含 `DESIGN.md`（视觉契约）+ `STORY.md`（叙事契约）+ `assets/` + `slides/NN.slide` + 产物 pptx（SKILL.md:35-48）。

组成：SKILL.md（63 行路由器）+ references/ 15 个组件文档 + 两条工作流（create-from-scratch 10.6KB / create-from-material）+ design-principle.md（16KB）+ story-principle.md（13KB）+ human-alignment.md（9.8KB）+ designs/ 三套领域风格（academic/consulting/redgold）+ scripts/（pptx2image.py 目检宫格图、doc_image_extractor.py 材料图片提取）。

**单向纪律**（SKILL.md:21）："PPTX 完全生成后，所有后续修改通过 `tencent-local-office-edit` SKILL 完成，**禁止回退到 SlideDSL 源文件修改**"——与我们烙入/导出的单向纪律同构。**术语隔离**：对用户只许说「页/封面/目录/这一页」，禁暴露 DSL/lint/OOXML（SKILL.md:28、create-from-scratch.md:5）。

## 2. 方案详解

### 2.1 SlideDSL 组件模型

- **画布**：1280×720 固定 px；Slide 的 padding 即安全区，"不能用绝对定位绕过"（component-slide.md:21,44）。
- **样式通道**：一律 `style={{...}}` 内联对象（camelCase CSS）；Table/Chart/Image 继承 Box 获得统一 style 通道。**允许 JS 表达式**（`.map()` 渲列表，富文本条目用 Fragment 包裹，component-text.md:64-79）——"无模块系统的 JSX 表达式"。
- **Box 限制**：仅 flex（默认 column）+ border-box + 绝对定位；**禁 grid、禁 calc()**（component-box.md:39-40）。
- **Text**：`<span style>` 富文本 + `<br/>` 换行 + 渐变文字/textShadow；**禁 `<strong>/<em>` 语义标签、禁 `\n`**（component-text.md:31-34）。无自动字号自适应。
- **Chart**：6 类型（bar/bar3d/line/area/pie/doughnut）、grouping 4 值、系列色支持 CSS 渐变；数值必须 number、饼/环仅单系列；场景选型表含"精确数值清单 → Table，不建议用图表"（component-chart.md:142-150）。
- **Table**：宽高必填，**推荐百分比尺寸"避免溢出父容器——推荐用于 LLM 生成"**（component-table.md:14-17）。
- **Diagram 三级路由硬规则**：首选内联 SVG → 次选 Box+Text 绝对定位 → Kroki 远程兜底（"Kroki 超时不要重试，直接改 SVG"，component-diagram.md:7-29）。
- **Image**：**严禁 URL/占位符**；先图后写强制流程；P0 材料图/P1 ImageGen/P2 SVG 三级配图策略（component-image.md:27-61）。
- **Animation**：直写 OOXML `<p:timing>`，animType 白名单（~40 入场+exit+emphasis），**单页 ≤4、密集列表禁逐条 fadeIn**（component-animation.md:57-65）。
- **Hyperlink**：`href` 是跨组件 prop；支持 `ppaction://hlinkshowjump?jump=nextslide` 跳页字面量；段内 span 链接不支持。
- **FAIcon**：`fill` 必填（不设完全不可见）；**严禁编造图标名**（编造校验失败）。

**高度预算纪律（强制）**：写码前必须做加法预算"上padding + 标题区 + 内容区 + 间距 + 下padding ≤ 720px"；"禁止主内容区用 flex:1 且不计算实际高度"；内容占比建议 30%–85%（component-slide.md:32-40）。默认母版三区：A 标题 0–120 / B 内容 120–660 / C 页脚 660–720（design-principle.md:25-31）。

### 2.2 slidep 工具链与质量保障

- **lint**：语法（禁模块语句、最后表达式必须 `<Slide>`、组件白名单）+ 溢出检测（固定 720px + flex 使编译器可做真实排版计算）；错误回路"按 error 字段修复后重新校验直到通过"（create-from-scratch.md:111）。
- **upsert-dsl 页级原子提交**：追加省略 page-index、替换用 `--page-index N`（0-based）；硬约束"写完立即 lint → 通过立即 upsert → ok:true 才继续下一页"（create-from-scratch.md:107-119）。改一页不动全稿。
- **pptx2image.py**：LibreOffice → pdftoppm → Pillow 拼 6/9 宫格 contact sheet（缩略图带页码）+ STYLE_PREVIEW.md，指导语"先读宫格图推断全局视觉语言，细节不清再看单页"。用途是**学习用户上传 PPTX 的风格**（create-from-material 前置步）。
- **doc_image_extractor.py**：pptx/docx/xlsx 图片提取，**双阈值过滤**（短边 <64px 一律丢弃；体积 ≥10KB 且长边 ≥480 保留；体积小但像素有效也保留）；尺寸从二进制头直读不做完整解码；命名带溯源 `pptx_s{页码}_img{n}.png`。配套纪律：高置信场景（财务/学术/法律）**严禁 AI 生图替代材料真实配图**（create-from-material.md:15-16）。

### 2.3 工作流：先内容后设计，双文档契约

六步（create-from-scratch.md:7-14）：信息收集 → 需求对齐（≤3 问）→ **STORY.md** → **DESIGN.md** → `slidep create` + **立即 present_files 打开预览（硬约束，"不得推迟到最终交付"** :88）→ 逐页循环（本页生图→写页→lint→upsert）。**配图限当前页**——"禁止一次性生成全部图片后再写页面"（:105）。**设计依据封闭**："动笔前禁读本目录之外的任何 PPT 项目源码…严禁仅靠记忆动笔"（:99-101）。

- **STORY.md** = 叙事契约：意图 5 问 → 骨架 5 件事 → 逐页大纲 10 字段（title/type/role/rhythm/layout/visual/visual_role/density/**anti_pattern**/description）。
- **DESIGN.md** = 视觉契约：母版三区具体 px、≤4 hex 色彩池、色彩面积分配、字号层级表、配图清单（生成方式/prompt/真实内容/是否核对）、**页面映射表**（序号/文件/类型/role/版式/字数估算/留白%/色彩分配/关键约束）——"是 STORY 与 slides 之间的契约，逐页生成严格对照"（design-principle.md:169-180）。
- 每页提交前 **10 条自检清单**（:120-129）：母版三区齐全 / ≤4 hex ≤2 字体 / 与上页版式不重复 / 留白 ≤35% / ≥1 视觉锚点 ≥44px / **与上页视觉重量差 >1.5:1** / 强调色只在焦点 / role 与 STORY 一致。

### 2.4 设计原则：两层分离 + 三态路由 + 量化密度门禁

**文件层级**（design-principle.md:1-11）：通用法则 vs designs/ 领域分支；每个分支分**结构层**（版式分类/字号阶梯比例/色彩面积比/装饰白名单结构/自检条件——"工程化骨架"）与**常量值层**（默认 hex/字体族——"可被 query 改写的填空答案"）。**三态路由**：完全命中 → 两层全执行；**软降级命中**（关键词中但命中禁用词）→ 结构层继续生效、常量层失效由 query 改写（"比 universal-only 更优"）；无命中 → 纯通用法则。**冲突优先级链**：用户显式指令 ≻ 分支结构层 ≻ 通用法则；细则：显式值只覆盖被指定的常量 / 同向冲突取更严者 / 正交冲突以分支为准。

**密度门禁（通用层，:115-139）**：按页型字数下限（内容页 ≥180 字；卡片组每卡 ≥100；数据页 ≥80 字 + 主图占 B 区 ≥50%）；留白 ≤35%；**容器填充率 ≥85%**（卡高 ≥380px → 正文 ≥100 字）；**底栏锚定**（尾元素必须 `marginTop:auto` 钉底）；**兄弟卡尾部 y 坐标差 >16px → 返工**。

**三套风格的差异轴**：

| 轴 | academic | consulting | redgold |
|---|---|---|---|
| 色彩 | 宝蓝主导，金=0 | Navy 20-35%，禁金/正红 | 美术层红 ≥50%+金 15-30%；内页白 ≥60% |
| 字体 | ≤2 套禁楷体 | **禁衬线** | 主标宋体 Heavy + 正文无衬线 |
| 密度哲学 | 撑满优先（C 区 ≥96%） | **大字优先**（"精简文案合并页面，而非缩小字号硬塞" :81） | 分层：内页留白 ≤35%、美术层 ≤15% |
| 独有纪律 | 数据真实可溯源；卡内五段骨架 | **Action Title 必须完整结论句**；信息结构图 12 子版式 ≥20%；**文图分离**（结构图文字必须独立可编辑，禁烤进 SVG :175） | **零旋转**；中文优先；封面金字三叠加 |
| 硬闸门 | 15 条返工条件 | 17 条（含"5 卡排 3 列留 1 空位"末行残缺禁令） | 18 条 |

### 2.5 叙事与人机对齐

**story-principle.md** 三步带闸门（意图未完成→禁入骨架；骨架未确认→禁入逐页）：
- 意图 5 问含总页数**决定 Hero 配额**（10 页中 2-3、15 页中 3-4）。
- 骨架含**目录↔章节扉页逐字一致契约**（"目录声明 N 章 → 有且仅有 N 个扉页，编号/标题/页码区间逐字一致" :22）、rhythm 曲线（连续 ≥3 页 valley 必须插 peak/transition）、**非对称版式 ≥40%、对称 ≤2 页**。
- 逐页大纲两个特色字段：**`anti_pattern`**（"每页必须显式写出具体禁止项，空泛=不合格" :128-136）；**`description` 数据两段式**（"含关键数据的页必须写成'数据+判断'…只摆数字收尾是信息板不是汇报稿，此为 STORY 职责禁止推给 DESIGN" :49-57）。
- 版式纪律：相邻页版式不重复；`左大图+右文字` 与 `非对称双栏` 合计 ≤40%（防"换着花样的单调"）。

**human-alignment.md**：
- **≤3 文字提问一轮问完**（缺失 >3 按 P0–P4 优先级取前 3，其余走默认）；风格预览卡不占提问名额；先文字后预览卡；**禁止暴露推理过程**。
- **风格预览卡**：跳过条件四选一（用户上传模板/已明确风格/要求快速出稿/命中预设分支，:54-61）；卡片四区固定（编号+风格名 / 色板条带 HEX / **封面缩略图占 74% 用用户真实主题文字渲染，禁色块占位** / 气质标签）；执行硬约束——禁通用色板库、**4 卡版式结构性不同**（"不允许只换颜色"）、顺序锁定"先定 4 套色板+4 种版式 → 再渲染 → 再弹卡"（:121-125）。
- **生成后追问路由**：只在模糊反馈时触发，按类型路由改动范围（风格→重弹卡排除已选；太长→回 STORY；太空→补内容）；"局部改页优先；风格改动落 DESIGN 后改页；页数改动回 STORY 重排"（:129-141）。

## 3. 对本项目的可提炼范式（8 条）

1. **设计文档两层分离 + 三态命中路由 + 冲突优先级链**：我们 themes.md 缺"用户 query 显式值覆盖哪些层"的元规则与命中/软降级路由——可在 themes.md 头部加"命中与覆盖规则"一节。
2. **页面映射表作为叙事↔产物的机器可对账契约**：与我们 M1 manifest 的 content_hash 正交互补（意图 vs 产物），harness 可按表核验 role/留白/色彩分配。
3. **per-page anti_pattern + "数据+判断"两段式**：我们呈现发散是正向选优，这是负向封禁，互补；内容验收可加"关键数字必须带'所以呢'判断"。
4. **目录↔章节扉页逐字一致契约**：k_nav_check 可加"目录条目文字 ↔ data-chapter 标题逐字一致 + 数量相等"静态校验。
5. **页级原子提交粒度**：我们导出整 deck 重跑；M4 已有 stale 检出，可加"只重导 stale 页"的增量路径。
6. **风格预览卡的真实内容渲染 + 结构差异硬约束 + 跳过条件表**：编辑器主题卡缺"用真实首页内容渲染预览"与"候选间必须结构性差异"口径；跳过条件表可优化 Step 0.5 脑暴触发逻辑。
7. **密度门禁机器化口径**：容器填充率、兄弟卡尾部 y 差 >16px、末行留坑——与 j_render_check 的零溢出/零重叠正好互补（它查"太满"，这些查"太空/松散"），可用 Playwright 量测落进 density_measure.py。
8. **用户面向术语隔离 + 预览即时化**：SKILL.md 可加"对用户汇报禁用内部术语表"；"先建空文件立即打开预览"对应嵌入态 load→逐页 patch 心智。

附两个可直接搬走的脚本级做法：pptx2image.py 的 contact sheet + "先全局后单页"风格学习法（可用于我们 pptx→HTML 转换的风格提取前置步）；doc_image_extractor.py 的双阈值图片过滤（可用于材料转换的图片筛选）。

## 4. 总体判断

腾讯这套的强项不在 DSL 表达力（受限 JSX、无 grid、无自适应字号），而在**质量保障的工程化**——所有设计规则都写成可返工的量化门禁（px/百分比/字数/数量上限），配"lint 单页原子提交 + 10 条页级自检 + 15-18 条风格硬闸门"三层防线，以及 DESIGN/STORY 双文档契约与人机对齐的"≤3 问 + 预览卡按需触发"纪律。slide-paipai 与它是同一问题的两端答案：一个用"统一 API + 双后端"保证形态一致，一个用"DSL + 编译期 lint"保证单形态质量；我们的"渲染真相 + 双轨导出"在架构上兼取两者，可吸收的是它们各自的**数值纪律与门禁口径**。
