# 动效参考（Motion）v3

> **好的动效不是"这里能不能加点动画"，而是"内容自己想动，我们只是把它显影出来"。**
> 动效是叙事节奏的一部分，不是装饰。一次精心编排的入场，胜过散落的微交互。

v3 相对 v2 的核心变化：词汇库从单层枚举升级为 **8 族 × 触发器自文档化**（skeleton v5 承载），丰富度从"三档强度"升级为 **五层启用矩阵**（L1–L5，档间差异是机制类别不同而非参数不同）。运行时化裁定不变：文本破坏性动效永远运行时化，产物文件中的文字永远是完整纯文本节点（契约条款见 `editing-contract.md`）。

v3.1 patch（F5 / skeleton v5.1）：§4 新增 **fx 仪式层**（canvas 2D，8 族之外的第 9 类）——默认关、主题 G5「fx 许可」白名单启用、只许仪式页、参数烧死在骨架。

v3.2 patch（imagegen v2 P1 G4 / 契约 v8 / skeleton v7.5）：**图片入场动效**——enter 族白名单子集（裸 `data-anim` / `rise-in` / `scale-pop` / `wipe-clip`）允许作用于 img 元素（页面级烙入整图 + 页内插画槽位）；纪律烧死：每页至多 1 个图片入场动效（计入主动效配额）、烙入整图时长 ≤0.8s 且零阶梯延迟（骨架压死）、禁 text/ptr/scroll 族作用于 img、插画槽位动效随所在页编排不独立叠加延迟；PPTX 导出为静态终态（HTML 演示态专属）。

## 1. 三条物理原理（能不能动的硬约束）

1. **动效是注意力预算**【硬规则】：一屏最多 **1 个主动效**（叙事驱动、大幅变化、>600ms）+ **2–3 个背景动效**（呼吸/漂移/辉光，不承载信息）。超过即"哪儿都在动等于哪儿都没动"。
2. **动效必须承担信息职能**：合法职能只有五种——**揭示存在**（entry）/ **传达数据变化**（transform）/ **建立空间因果**（causality）/ **指示可交互**（affordance）/ **维持存在感**（ambience）。一个动效归属两种以上职能 = 过重，删掉。这是"该不该加动效"的判定标准，也是动效版的"一页一意"。
3. **时长匹配信息密度**：`时长 ≈ 300ms + 信息比特 × 200ms`。fade 一个标签 300ms，slide-in 一张卡 500ms，count-up 一个数字 1200–1800ms，shatter 一个标题 ~1800ms，循环动效 ≥3s（越缓越高级）。fade 慢到 1s、count-up 快到 500ms 是最常见的翻车点。

## 2. 六条组合原则（默认区）

1. **编舞（stagger）**：同类元素永不同时动；步长 ≈ 单元素时长 / 元素数 × 1.2。骨架按 DOM 序自动分配 `--i` 阶梯，生成时不手写延迟数值；stagger 阶梯不超过 6 个元素，再多的列表项按组入场。
2. **三段式**：Reveal → Hold（≥1500ms 静止期，不可省略）→ Interact；背景动效不得占用静止期的注意力（密度与幅度压到极低——骨架 ambience/light 类的强度上限已按此烧死）。
3. **锚点动效**：每页主角配一个**独有**的动效变体（其他元素用常规款），让用户记得住这一页——与"一页一个视觉重心"同构。
4. **词汇表纪律**【硬规则】：一份 deck 只用骨架 token 里的三种缓动——出 `cubic-bezier(.22,1,.36,1)` / 变 `cubic-bezier(.7,0,.2,1)` / 环 `ease-in-out`（骨架 `--ease-out` / `--ease-shift` / `--ease-loop`），禁止逐页自定义缓动。
5. **方向语义同构**：增长向上向右、流失向下降饱和、流程从左到右、稳定几乎不动。动效方向与内容语义冲突即失败。
6. **感知性能**：入场动效本身占用注意力、让加载感变短；但骨架/首屏 200ms 内必须可见（骨架 `.js` 门槛与一次性 `.in-view` 语义已保证）。

### 反目录覆盖纪律【硬规则】（v3 新增）

词汇库 8 族是**词汇表不是清单**——存在的意义是让"内容自己想动"时手头有词，不是让每份 deck 把 39 个 recipe 都秀一遍。【禁止】为了展示词汇量而加动效：每个动效必须能回答"它承担 §1.2 的哪一种职能"。一份 deck 实际使用的 recipe 族数通常 ≤4（克制 1 族、标准 2–3 族、华丽 ≤5 族），超出即失控信号。

## 3. 触发器三维模型（骨架接口，v3 重写）

v3 把"动效怎么被触发"提升为一等维度。**族前缀即触发器自文档化**——看到标记就知道它何时动、由谁驱动：

| 触发器 | 承载标记 | 驱动方 | 族 |
|---|---|---|---|
| **inview**（入视口一次性） | `data-anim="..."` | CSS 过渡 + 框架 JS 引擎 | enter / text / data / link（draw-line） |
| **loop**（持续循环） | `amb-*` / `light-*` / `dash-flow` / `flow-dot` class；`data-rotate` 容器（v7，JS 轮转 .active，in-view 生命周期） | 纯 CSS 动画 / 框架 JS 轮转 | amb / light / link（循环款） |
| **scroll**（滚动驱动） | `data-scroll="..."` | 框架 JS 滚动驱动（--sp 进度变量，rAF 节流）+ 纯 CSS scroll-timeline（read-progress）+ sticky 纯 CSS（页间效果） | scroll |
| **pointer**（指针驱动） | `data-ptr="..."` / `.spotlight` | 框架 JS pointer tracker（rAF 节流，只写 CSS 变量） | ptr / light（spotlight） |
| **canvas**（in-view 生命周期，v5.1） | `<canvas data-fx="...">` | 框架 JS canvas FX runtime（rAF，离屏停帧，参数烧死） | fx 仪式层（§4 fx 小节，8 族之外，默认关） |

既有双层语义不变：**页面级配方** `<section class="slide" data-animate="...">` 选节奏（`hero` / `quote`，不写 = 默认 cascade），**元素级角色** 按上表标记。【硬规则】每页至多一个 `data-animate` 配方；完全不想动的页不写任何标记，也是合法选择。

**transform 互斥**【硬规则】：同一元素只能有一个 transform 来源——`data-ptr` / `data-scroll="parallax"` 元素【不得】再标 enter 族的位移类 recipe（默认/left/right/rise-in/persp-in）；可叠加 opacity/filter/clip 类（blur-in / wipe-clip）或不加入场。

### 配方决策树

```
本页是封面/收束/大情绪页？ → hero（慢节奏、长延迟；主角可配 chars/shatter/typewriter）
本页主体是金句/引文？     → quote（逐句节奏；标题可配 mask-lines 逐行遮罩）
本页是左右对比/双栏？     → 默认配方 + 元素标 left/right（镜像入场）
本页主角是大数字/图表？   → 默认配方 + 锚点 count-up / fill-bar / fill-bar-y / ring / draw-line
需要阅读中的持续推进感？ → scroll 族：parallax 分层 / scrub / scrub-draw（华丽档才启用）
需要指针响应的沉浸感？   → ptr 族：spotlight / tilt / magnetic / parallax（华丽档才启用）
其他内容页             → 不写 data-animate（默认 cascade 阶梯）
完全不想动             → 不写任何标记（该页静止，也是合法选择）
```

### 内容→动效对照表（K 期新增，查询手册）

| 你在写什么 | 首选 | 备选 | 不要 |
|---|---|---|---|
| Hero 标题（品牌名/宣言） | chars / mask-lines / shatter | typewriter（techy 限定） | 简单 fade（浪费首屏） |
| 反差数字（¥2000→¥0） | count-up（落差即叙事） | 巨字直排（不用动效） | 多数字同屏全 count-up（配额指纹病） |
| "问题→解决"指标 | mend-bar 双态修复条 | fill-bar + 注释 | 静态百分比 |
| 进度/占比 | fill-bar / fill-bar-y / ring | count-up | 静态数字 |
| 流程/管道 | draw-line 描绘 + flow-dot 沿线粒子 | data-rotate 轮转各阶段 | 静态箭头链 |
| 对照（A vs B） | 左右镜像异步入场 | 裂屏色场对撞 | 两方同时出现 |
| 卡片/清单列 | stagger 阶梯（≤6 个/组） | scale-pop（playful 主题） | 同步出现 |
| 金句/引文 | quote 配方 + mask-lines | blur-in | count-up 等数据款 |
| 章节切换/封面 | hero 配方 +（主题 fx 许可内）canvas 仪式层 | 页间 cover/stack（sticky） | 硬切之外的过度编排 |

与 `references/motifs.md` 互引：motifs 管"静态呈现隐喻"（选什么图形关系），本表管"动态过程隐喻"（图形怎么动）；选定隐喻后从本表配动效，而不是反过来。

## 4. 词汇表：8 族 46 recipe（枚举，带规则）

每个 recipe 是枚举项；**新 recipe 入库必须过「入库七件规范」**（身份卡、骨架、量化规则、密度适配、可编辑分层声明、反模式、三级验收——逐条见 `references/components.md` §10）。表中"触发器"列即 §3 三维；"亲和/禁用"列是主题 G5 选型的默认口径（主题显式声明优先）。

### enter 族（入场揭示 · inview 一次性）

| recipe | 职能 | 适用内容 | 时长档 | 亲和/禁用 | 实现要点 |
|---|---|---|---|---|---|
| `enter`（裸 `data-anim`） | entry | 一切元素的默认上浮 | 300–600ms | 全主题 | 上浮 24px + 淡入，`--i` 阶梯 |
| `enter-left` / `enter-right`（`left`/`right`） | entry | 对比/双栏的镜像入场 | 600ms | 全主题 | 横向滑入 ±40px |
| `enter-line`（`line`） | entry+causality | hairline 分隔线生长 | 600ms | 全主题 | scaleX 0→1，原点左 |
| `blur-in` | entry（柔和） | 大标题、氛围文字（图片不走此款——v8 图片白名单四款见下） | ~800ms | calm/editorial 亲和；techy 慎用 | blur(14px)→0 + 淡入 |
| `scale-pop` | entry（强调） | 徽章、数字、图标、卡片 | ~550ms | playful/dramatic 亲和；editorial 慎用 | scale(.86)→1 + 快淡入 |
| `wipe-clip` | entry（揭示） | 通栏色块、图片、大容器 | ~900ms | dramatic/professional 亲和 | clip-path 从左向右揭示，方向固定 |
| `rise-in` | entry（郑重） | 章节标题、大数字组 | ~800ms | dramatic 亲和 | 位移 64px（比默认大三倍） |
| `persp-in` | entry（空间感） | 卡片组、产品图、封面主视觉 | ~900ms | dramatic/techy 亲和；editorial 禁 | perspective 1200px rotateX(12°) 俯仰入场 |
| `flicker-in` 通电点亮（v7.6） | entry（点亮） | 霓虹/灯管世界的标题与发光容器 | ~1100ms | techy 亲和；**主题限定**：发光体系主题（如 F2 霓虹夜行）；editorial/calm 禁 | steps 明暗抖动数次后常亮（气体放电稳定过程），一次性，终态常亮 |

**图片元素入场（契约 v8，白名单子集）**：页面级烙入整图（`page-baked-*` 槽位 img）与页内插画槽位 img 只允许用四款——裸 `data-anim`（fade）/ `rise-in`（rise）/ `scale-pop`（zoom-in）/ `wipe-clip`（curtain）；烙入整图时长 ≤0.8s、零阶梯延迟（骨架 v7.5 烧死，选 wipe-clip 也被压到 .8s）；每页至多 1 个图片入场动效（即该页主动效）；整图是页面唯一主角，入场即仪式，不再配第二个锚点。

### text 族（文字引擎 · inview，运行时化）

| recipe | 职能 | 适用内容 | 时长档 | 亲和/禁用 | 实现要点 |
|---|---|---|---|---|---|
| `chars` 逐字飞入 | entry（强调） | 封面/章节标题 | ~1800ms | 全主题 | 运行时拆字：文件里只写纯文本，骨架入场拆字、完成还原 |
| `words` 逐词飞入 | entry（强调） | 英文/西文标题 | ~1800ms | 全主题 | 同上，按词拆分（中文无词边界，勿用） |
| `shatter` 碎聚 | entry（最强） | 全 deck 仅首页主角 | ~1800ms | dramatic 亲和；editorial 系（C4/A1 等）禁 | 运行时拆字 + 确定性散布聚合；**一份 deck 限 1 次** |
| `mask-lines` 逐行遮罩 | entry（编辑感） | 多行标题/导语（2–4 行） | 行 ~850ms，阶梯 110ms | editorial/professional 亲和 | 生成侧显式分行：`.ml-line` 外遮罩 + `.ml-inner` 内层位移；`.ml-inner` 是 data-editable 叶子，文本节点完整不拆 |
| `typewriter` 打字机 | entry（叙事） | 终端感短句、命令行、金句 | 字 28–70ms 自适应 | **主题限定**：techy（如 C3 终端绿）；其余主题禁 | 运行时逐字显影 + 光标闪烁，完成还原纯文本 |
| `scramble` 乱码归位 | entry（解码感） | 短词、标签、数字串 | ~1100ms | **主题限定**：techy；其余主题禁 | 运行时乱码逐字 settle，完成还原纯文本 |
| `gradient-flow` 流光字 | ambience（文字） | 封面/收束页大标题 | 循环 7s | dramatic 亲和；editorial 慎用 | background-clip:text 透明填充 + 渐变流动；`color` 保留本色兜底（契约 v6：编辑态强制还原本色） |

### data 族（数据显影 · inview）

| recipe | 职能 | 适用内容 | 时长档 | 亲和/禁用 | 实现要点 |
|---|---|---|---|---|---|
| `count-up` 数字滚动 | transform | 大数字/KPI | 1200–1800ms | techy/professional 亲和 | 元素文本即终值（支持千分位/小数/前后缀），从 0 或 `data-from` 起滚，结束精确还原原文本 |
| `fill-bar` 横向填充 | transform | 进度/占比/横条图 | 800–1200ms | 全主题 | scaleX 0→目标；条内数值另用 count-up 或静态文本 |
| `fill-bar-y` 竖柱生长 | transform | 柱状图、竖向进度 | 800–1200ms | 全主题 | scaleY 0→1，原点底部（v5 补全 v2 的已知限制） |
| `ring` 环形进度 | transform | 占比环、完成度 | ~1200ms | 全主题 | 纯 CSS：SVG circle 写 `pathLength="100"` + `style="--val:N"`，dashoffset 100→100−N |
| `mend-bar` 双态修复条（v7） | transform（状态迁移） | "问题→解决"指标（漏损率/错误率/风险敞口） | 两段：1.5s 填充 + 1.2s 收窄 | dramatic/professional 亲和；calm 慎用 | 填充条标 `data-anim="mend-bar"` + `style="--from:N;--val:M"`——先填充到 --from（警示渐变建立张力），再收窄到 --val 并切 accent 纯态；纯 CSS .in-view 触发；--from/--val 是产物内容 |

### link 族（连接件 · inview / loop）

| recipe | 职能 | 适用内容 | 时长档 | 亲和/禁用 | 实现要点 |
|---|---|---|---|---|---|
| `draw-line` 描绘 | causality | 流程连线/箭头/图表折线 | 800–1500ms | techy 亲和 | stroke-dasharray 描绘，框架 JS 量长藏线；元素同时标 `data-editable-skip` |
| `dash-flow` 流动虚线 | causality（持续） | 循环流程、数据流、进行中状态 | 循环 1.6s | techy 亲和；calm 禁（持续运动扰静） | class `dash-flow`，dasharray 默认 6 10 可覆盖；装饰件标 skip |
| `flow-dot` 沿线粒子 | causality（持续） |  Pipeline、传输、能量流 | 循环 ≥4.5s | techy/dramatic 亲和；calm 禁 | class `flow-dot` 的 HTML 圆点 + `style="--flow-path:path('…')"`（与可见线同份路径数据）；offset-path 不支持时藏点留线 |
| `data-rotate` 轮转高亮（v7，loop） | ambience + causality | 流水线各阶段、轮值状态、"各环节都在工作"的活态 | 轮转 2.4s/格 | techy/professional 亲和；calm 禁（持续运动扰静） | 容器标 `data-rotate`，子项标 `data-rotate-item`；骨架 JS 轮转 .active（in-view 启动/离屏停帧/freeze 摘除清空）；active 加强造型由产物/主题定义；active class 是运行时状态 |

### amb 族（环境氛围 · loop，只许背景层）

| recipe | 职能 | 适用内容 | 时长档 | 亲和/禁用 | 实现要点 |
|---|---|---|---|---|---|
| `amb-pulse` 呼吸 | ambience | 呼吸点、状态灯 | 循环 4s | 全主题 | 不透明度摆幅 ≤.4 |
| `amb-drift` 漂移 | ambience | 水印、背景图形 | 循环 9s | 全主题 | 位移 ≤10px |
| `amb-glow` 辉光呼吸 | ambience | 氛围光斑 | 循环 6s | dramatic/calm 亲和 | 透明度 + 1.05 缩放 |
| `amb-noise` 噪点 | ambience | 纸纹/胶片感背景 | 步进 1.4s | 纸感/手绘主题（A4/D3）亲和；flat 系（B/C1）禁 | steps(2) 抖动背景位，作用于自带纹理背景的元素 |
| `amb-gradient-blob` 渐变球 | ambience | 封面/收束的氛围主体 | 循环 16s | dramatic/calm 亲和 | 位移 ≤24px、缩放 ≤1.06（上限烧死） |
| `amb-kenburns` 缓推镜 | ambience | 封面大图、背景照片 | 循环 26s 往返 | editorial/dramatic 亲和 | scale 1→1.08 + 微位移，作用于 img/背景容器 |
| `amb-marquee` 走马灯 | ambience | 装饰条带（logo 墙/关键词带） | 循环 ≥12s | playful/techy 亲和；editorial 禁 | 生成侧把内容写两遍，translateX −50% 无缝循环 |

### light 族（光效 · loop / pointer，装饰件一律 skip）

| recipe | 职能 | 适用内容 | 时长档 | 亲和/禁用 | 实现要点 |
|---|---|---|---|---|---|
| `light-sweep` 扫光 | ambience（强调） | 封面标题容器、主打卡片 | 循环 5.5s | dramatic 亲和；editorial 禁 | class `light-sweep`，伪元素掠过（宿主自动 overflow:hidden） |
| `border-beam` 边框流光 | affordance+ambience | 焦点卡片、CTA 容器 | 循环 4.5s | techy/dramatic 亲和 | class `border-beam`，conic-gradient 旋转光弧贴边（@property 不支持时静态弧，优雅降级） |
| `god-rays` 神光 | ambience | 暗色封面/收束页顶部 | 循环 15s | dramatic 亲和；仅限 dark 页 | class `god-rays` 装饰 div，repeating-conic 光柱 + 径向渐隐，摆角 ±2° |
| `light-leak` 漏光 | ambience | 暗色页角落、胶片感页 | 循环 12s | dramatic/calm 亲和 | class `light-leak` 装饰 div，accent 15% 软光斑漂移 |
| `spotlight` 聚光 | ambience（跟随） | 暗色封面/展示页 | 实时 | dramatic 亲和；仅限 dark 页 | class `spotlight` 装饰 div，消费 pointer tracker 的 `--mx/--my`；tracker 不启动时停在默认位 |

### ptr 族（指针交互 · pointer tracker）

> **hover 微交互**（K 期补，demo1 复盘）：内容卡片的纯 CSS hover 反馈是合法的 L5 轻量款——推荐**整卡反色**（hover 时背景↔文字色按 token 互换，如 accent 底 + accent-on 字）或 border-color 转 accent；只给"可交互暗示"的容器（链接卡/可点击区/对照列），纯展示容器不加；过渡 ≤.3s；accent 反色计入单焦点预算。`@media(hover:none)` 下天然无效果、零降级成本。

| recipe | 职能 | 适用内容 | 时长档 | 亲和/禁用 | 实现要点 |
|---|---|---|---|---|---|
| `ptr-parallax`（`data-ptr="parallax"`） | affordance | 封面分层元素（前/后景） | 实时 + .5s 回弹 | dramatic 亲和 | 消费 slide 级 `--mxr/--myr`，力度 `style="--pdepth:Npx"`，位移上限 ±28px 烧死 |
| `tilt`（`data-ptr="tilt"`） | affordance | 单张主打卡片/产品图 | 实时 + .45s 回弹 | playful/dramatic 亲和 | per-element 监听，倾角 ±6° 烧死，离开回弹 |
| `magnetic`（`data-ptr="magnetic"`） | affordance | 小徽章、编号角标、装饰芯片 | 实时 + .4s 回弹 | playful 亲和 | 向指针吸附，位移 ±16px 烧死 |

### scroll 族（滚动驱动 · scroll-timeline / sticky）

| recipe | 职能 | 适用内容 | 时长档 | 亲和/禁用 | 实现要点 |
|---|---|---|---|---|---|
| `scroll-parallax`（`data-scroll="parallax"`） | ambience（纵深） | 页内背景/前景分层 | 滚动链接 | dramatic 亲和；低密度页用 | `style="--depth:0.3–1"` 分层，位移上限 ±64px 烧死；骨架 JS 滚动驱动 `--sp` 进度变量（CSS `view()` 在 `overflow:hidden` 画布下绑错滚动容器，见 §7） |
| `scrub`（`data-scroll="scrub"`） | entry（渐进） | 长内容页的分段显影 | 滚动链接 | professional 亲和 | 透明度+位移与页穿越进度链接（`--sp` 0.12→0.45 区间完成显影） |
| `scrub-draw`（`data-scroll="scrub-draw"`） | causality（渐进） | 跨页叙事线、时间轴主线 | 滚动链接 | techy 亲和 | draw-line 的滚动变体：path 写 `pathLength="100"`，dashoffset 随 `--sp`（0.15→0.85）从 100→0 |
| `pin-stack`（`.slide-slot[data-scroll="stack"]`） | causality（页间） | 连续 2–4 页的递进论证 | 滚动链接 | dramatic 亲和 | sticky 叠放：同组 slot 递推写 `style="--pin-i:0,1,2…"` 错位叠顶；组内 ≤4 页 |
| `cover-uncover`（`.slide-slot[data-scroll="cover"]`） | causality（页间） | 章节页的揭开仪式 | 滚动链接 | dramatic/editorial 亲和 | sticky 钉住本页，下页滑过覆盖；被钉页应是完整构图的仪式页 |
| `read-progress`（`.read-progress` div） | affordance | 长 deck（≥10 页）的阅读进度 | 滚动链接 | professional 亲和 | body 级 `<div class="read-progress" data-editable-skip>`；不支持 scroll-timeline 时自动隐藏 |

### fx 仪式层（canvas 2D · skeleton v5.1 / F5 新增，8 族之外）

canvas FX 是**页面级仪式效果**，不是元素级 recipe——8 族词汇表之外的第 9 类，**默认关**、主题 G5「fx 许可」白名单启用。效果集收敛为 4 款，密度/数量/速度全部烧死在骨架常量，**生成侧只能选类、无任何参数通道**：

| fx | 职能 | 适用内容 | 亲和/禁用 | 实现要点（参数已烧死，仅供理解） |
|---|---|---|---|---|
| `constellation` 星座连线 | ambience（仪式） | 暗色封面/收束页 | dramatic/techy 亲和；editorial/calm 禁 | 44 点漂移 + 近距连线（阈值 ≈7.8% 页宽），accent 着色，线 alpha ≤.16、点 ≤.5 |
| `starfield` 星空 | ambience（仪式） | 暗色封面/收束页 | dramatic/techy/暗场 calm 亲和 | 150 星 sin 相位闪烁，无位移，文字色低透明 |
| `particle-drift` 漂浮微粒 | ambience（仪式） | 封面/收束的尘埃感 | calm/dramatic 亲和 | 26 粒缓浮上行（≤0.6% 页高/秒），呼吸透明 |
| `ascii-field` 字符呼吸场 | ambience（仪式） | techy/editorial 仪式页 | techy/editorial 亲和；calm/playful 禁 | sin 噪声场驱动 mono 字符显隐（致敬 guizang ascii-bg），单元格 ≈26px@1920 |

【硬规则】fx 启用纪律（违反即失控信号）：

1. **默认关**：只有主题 G5「fx 许可」白名单内的效果可用（themes/index.md 逐主题声明；未声明 = 全禁）；
2. **页面配给**：只许 `.cover-page` 仪式页（封面/章节/收束），每页至多 1 个 fx，全 deck 建议 ≤3 页——这是背景配给制（F1）的动效版；
3. **写法唯一**：`<canvas data-fx="<效果名>" data-editable-skip aria-hidden="true"></canvas>` 作为 `.slide` 的子元素（骨架 CSS 已把 canvas 以 `z-index:-1` 垫在页背景之上、全部内容之下，内容侧无需补定位）；
4. **注意力预算**：标了 fx 的页面，fx 即该页唯一的 L4 环境层——不再叠加 amb/light 循环装饰件（L1 入场不受限）；
5. 无 JS / reduced-motion / 打印下 canvas 恒为空白透明层，零痕迹；离屏自动停帧，回屏续播。

## 5. 五层启用矩阵（design-system 面板 motion 选项的语义，v3 替换三档）

丰富度 = **启用哪些机制层**，不是"同层动效调强"。五个机制层：

| 层 | 内容 | 对应族 |
|---|---|---|
| **L1 入场编排** | reveal / enter 族 / 页面配方 / stagger 阶梯 | enter |
| **L2 文字动效** | 拆字、逐行遮罩、打字机、流光字 | text |
| **L3 数据动效** | count-up / fill-bar(-y) / ring / draw-line | data / link（描绘款） |
| **L4 环境层** | amb 族 + light 族 + link 族循环款；fx 仪式层（canvas，默认关、主题白名单、只许仪式页） | amb / light / link（循环款） / fx |
| **L5 交互层** | ptr 族 + scroll 族 | ptr / scroll |

| 档 | 启用层 | 构成描述（面板选项语义） |
|---|---|---|
| **克制** | 仅 L1 | 只有入场编排：默认 cascade 阶梯 + 页面配方，无文字特效、无背景、无交互 |
| **标准** | L1–L4 各一 | 每层至多一个代表：如 chars（L2）+ count-up（L3）+ 1 个 amb（L4），无交互层 |
| **华丽** | L1–L5 全开 | 五层齐全：锚点 shatter/typewriter 级（L2）+ 数据显影（L3）+ 环境光效（L4）+ ptr/scroll（L5） |

【硬规则】三档共享注意力预算——华丽档加的是**层**不是同层数量：每页主动效仍 ≤1，背景动效仍 ≤2–3，机器可验口径不变（按族计数）。

【硬规则】**华丽档相邻页锚点 recipe 不重复**：相邻两页的锚点动效（每页那个"独有的主角动效"）不得是同一个 recipe——连续两页都 count-up 等于没有锚点。选型时先排锚点序列再填常规款。

## 6. 与主题/图表/编辑的接口

**高密度档的动效配额**（K 期注记，demo1 复盘）：密度升高时注意力预算不变——每屏主动效仍只有 1 个；变化的是**容器级微动效**：随容器数增加，每容器至多 1 个、语义型优先（mend-bar 修复 / data-rotate 轮转 / count-up 落差），循环类氛围微动效全屏 ≤2。密度越高，动效越往语义型集中、越远离氛围型——高密度页的"丰富"由标注层和容器结构承担，动效只点关键节点。

**标题动效两档制**（K 期深化，demo1 代码级复盘）【默认】：

- **仪式页标题**（封面/章节/收束）：用最强锚点款——chars / shatter / mask-lines / typewriter（techy 限定），每页不重样；
- **章节/内容页标题**：同 deck 内**统一用一款质感化文字动效**（系统感来自一致）——但必须是文字款（chars 小步错峰 / mask-lines / rise-in），**禁止用 wipe-clip 这类色块揭示款充当标题动效**（职能混淆：wipe 的对象是色块不是文字）；与正文的 reveal 阶梯区分（标题动效必须比正文入场"贵"）；
- **错误模式**：全 deck 所有标题同一款通用入场（如清一色 wipe-clip 或清一色默认 reveal）——标题是每页的仪式起点，与正文同待遇即无仪式。

**背景与装饰层的隐性运动**（K 期深化）【默认】：标准档以上，L4 环境层的那个代表**优先选全局隐性运动**——amb/light 族循环款（drift/noise/gradient-blob/light-leak，周期 ≥8s、幅度极小）或主题质感层的缓慢漂移（gridDrift 教训：background-position 60s 漂移是底纹最便宜的活态），一次选型全 deck 生效，比"只在封面放氛围"更值。装饰家具层（Ghost 字/巨号页码/刊头/水印）可挂低频呼吸（amb-pulse/amb-glow，opacity 摆幅 ≤.08），计入每屏背景动效 ≤2–3 的既有注意力预算，不与 fx 仪式层叠加。"活着的密度"= 标注层（静态）+ 装饰呼吸（低频）+ 语义微动效（容器级）三层叠加。

**气质对照表（Effect → Feeling）**：选配方前先对齐"这页想要什么感觉"（也是主题 G5 字段与编辑器面板的语义基础）：

| 气质 | 感觉 | 做法 |
|---|---|---|
| 戏剧 Dramatic | 重磅揭晓 | hero 配方，大元素慢速入场，锚点 shatter/persp-in/count-up，可配 god-rays/light-leak/spotlight |
| 编辑 Editorial | 杂志翻阅 | quote 配方，mask-lines 逐行遮罩；禁 shatter/persp-in，慎 gradient-flow |
| 专业 Professional | 干净高效 | 默认 cascade，300–500ms 级，锚点 draw-line/fill-bar 系 |
| 沉静 Calm | 呼吸感 | 减少动画元素数量，只动主角；背景可配 amb-pulse/amb-gradient-blob；禁 dash-flow/flow-dot |
| 科技 Techy | 精确、系统 | count-up/draw-line/dash-flow/flow-dot，数字与图表生长；主题限定款 typewriter/scramble 只在这里合法 |
| 活泼 Playful | 轻松 | scale-pop/magnetic/amb-marquee 点到为止；本技能形态下建议主要用配色表达 |

- **主题 G5**：主题声明动效气质、强度上限与禁用 recipe（如 editorial 系禁 shatter/persp-in、calm 系禁 dash-flow/flow-dot、typewriter/scramble 仅 techy 主题可用），生成侧选型必须遵守；G5 缺省时走全局默认（professional，无禁用，主题限定款仍按 §4 表执行）。G5 另携「fx 许可」白名单（canvas 仪式层，§4 fx 小节），缺省全禁。**G 期起 G5 扩为动效签名**：气质/上限/禁用/fx 许可之外可声明——「锚点偏好」（本主题锚点 recipe 首选序列，如 c1=scale-pop/wipe-clip、d2=blur-in、a1=mask-lines）、「节奏偏移」（时长档 ±1 与阶梯步长上下限，生成侧落码时执行）、「缓动签名」（主题 CSS 块内 `:root{}` 重定义 `--ease-out/--ease-shift/--ease-loop`，骨架 var() 消费即生效，如 b1 锐利 .2,.9,.25,1、d1 回弹 .34,1.56,.64,1）。优先级硬规则：注意力预算（§1/§5）与禁用清单仍是上限，签名只在预算内定倾向，不得借签名突破。
- **图表**：`draw-line` / `fill-bar` / `fill-bar-y` / `ring` / `count-up` 即图表入场动效的标准款，charts.md 引用本词汇表，不再单独定义动画。同一页里图表生长是主角时，其他元素减少或不做入场（沉静原则）。
- **编辑**：所有文本类动效运行时化（`data-anim` 属性本身不参与编辑，编辑器忽略）；编辑后下次入场按新文本重拆/重打。mask-lines 的分行结构（`.ml-line`/`.ml-inner`）是**产物结构**，编辑对象是 `.ml-inner` 叶子文字；改行数属于结构变更，走 AI 流程。ptr/scroll 族在编辑器内被冻结（编辑态静态终态），不影响演示态。
- **隐喻交叉**：内容关系 → 视觉隐喻的发散见 `references/motifs.md`（H 期，SKILL.md 呈现发散步的查询库）——动效承载内容隐喻时（如 draw-line=生长/描绘、blur-in=显影），锚点选择先服从主题 G5 签名，再服从隐喻亲和。
- **iframe 嵌入**：pointer tracker 只监听 deck 容器的 passive 事件、只写 CSS 变量，不劫持宿主的任何事件；scroll 族不触 scroll-jacking（竖滚主权始终在用户手上）。

## 7. 降级链（骨架已内置，生成侧无需处理）

1. `.js` 门槛：无 JS 环境（打印预览、抓取器）下动效样式不生效，内容直接完整可见；
2. `IntersectionObserver` 不可用 → 全部直接可见（含运行时引擎效果，一次性入场）；
3. `prefers-reduced-motion: reduce` → 所有动效（含 ambience/light 循环、scroll/pointer 族）消失，运行时引擎与 pointer tracker 不启动，文件里本来就是纯文本与完整图形，零成本成立（含打印）；
4. CSS scroll-timeline 不支持 → `read-progress` 自动隐藏（`@supports` 外 `display:none`）；parallax/scrub/scrub-draw 不依赖 scroll-timeline（骨架 JS 滚动驱动 `--sp`），有 JS 即可用；
   > 设计注记：parallax/scrub/scrub-draw 曾按"CSS `view()` 时间线优先"设计，实测 `view()` 的滚动容器解析会把 `overflow:hidden` 的 `.slide` 画布当作最近滚动容器（规范如此——overflow:hidden 也是滚动容器），进度冻结在初值（Chromium 145 实测）。因此这三个 recipe 降级为骨架 JS 滚动监听写 `--sp` 变量、CSS `calc` 消费的形态——声明式强度上限不变，零 DOM 结构写入；
5. `pointer:fine` 不满足（触屏）→ pointer tracker 不启动，ptr 族停在设计位、spotlight 停在默认位；
6. `offset-path` 不支持 → flow-dot 藏点留线；`@property` 不支持 → border-beam 退化为静态光弧。
7. canvas FX（fx 仪式层，v5.1）：无 JS / reduced-motion 下整组不初始化、canvas 恒为空白透明层（打印额外 `display:none`）；离屏自动停帧；无 `IntersectionObserver` → 全部常开（同入场引擎降级语义）；编辑器 `__pptxMotion.freeze()` 停帧 + 清屏 + 摘除运行时 width/height。
