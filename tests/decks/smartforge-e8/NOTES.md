# 高密度验收 · E8 号外报纸（基底号外红）——「SmartForge 内容流水线」交付说明

> **v2（2026-09-20）· 容器边界义务修正**：按 `tests/decks/isolation-ab/` 隔离三手段对照实验结论（高密度必须"面或框"，"只有线"不合格）与 components.md §13 新增硬规则「容器边界义务」，把五处高密度容器的"纯线分隔"统一升级为 **1px 墨线栏框**（`color-mix(in srgb,var(--ink) 50%,transparent)`——报纸栏框是实线不是发丝线，比栏间 hairline 22–25% 略实）。E8 是亮底世界，"面"弱（纸白上灰档对比低），报纸世界的正确答案是框（boxed sidebar/专栏框）。控制变量：文本/密度/动效/标注层一概不动，只改容器边界。

**v2 改动清单**（全部在产物样式块，框架层与主题 SLOT 不动）：

| 落点 | 前（纯线分隔） | 后（栏框） | 同构口径 |
|---|---|---|---|
| p2 ticker 三格 | 相邻栏间 1px hairline（border-left） | 每格 1px 墨线栏框 | gap 恒 24px · padding 恒 26/28px |
| p3 漏洞 metric-card ×4 | 仅顶 3px 粗规则 | 1px 栏框三边 + 顶 3px 粗规则保留（栏题） | gap 恒 36px · padding 恒 16/20px |
| p4 流水线三段 | 相邻栏间 1px hairline | 每段 1px 墨线栏框 | gap 恒 28px · padding 恒 20/26px；段间 draw-line 箭头随缝心重定位（≈555/≈1124） |
| p5 versus-cols 对照行 ×6 | 仅顶 1px hairline | 每行 1px 墨线栏框 | padding 恒 12/16px |
| p6 stack-rows ×3 | 仅顶 1px hairline | 每层 1px 墨线栏框（相邻行共享边防双线）；L01 墨档反白条以填充自身为界（border-color 转墨） | padding 恒 20/24px |

不动项：封面/收束的报头徽标条与红色通栏（仪式页特权）；mt-news-rule 粗细双线保留——它是装饰线（§14 词汇），不是容器边界，两回事；kv-band 通栏带本就有粗顶细底双线 + 栏间 hairline（通栏带形态，非栏框位）；p7 产出物条与 chips 不在本次修正范围（v1 即非裸排重灾区，且 §13 允许每页一个主力手段——p7 主力是字段块粗顶细底带）。同页边界手段单一（框），未与面混用（p6 L01 墨档条是层级强调不是并列容器组，§12 明度档照旧）。

**v2 自检**：`j_render_check.py` 8/8 PASS（零溢出零重叠，editable 25/57/44/81/54/61/59/6 与 v1 完全一致）；`k_nav_check.py` 三通道全过；`density_measure.py` 逐页指标与 v1 逐项相同（文本叶 61/56/82/55/62/60，标注层 29/24/45/28/31/29，字阶 9/9/8/9/8/9）——控制变量成立；`run_e2e.py` 全量回归 45/45 PASS（含 smartforge-e8 编辑器往返幂等）。

- 产物：`index.html`（8 页，1920×1080 竖向滚动，纯 HTML 模式——零图片、零 assets 依赖）。
- 内容源：`tests/decks/smartforge-content.md`（SmartForge · 自媒体全链路营销系统，高密度基准包）；与 `tests/decks/smartforge-c1/`（c1 信号黑版）构成**同内容双主题对照**——内容集与章节结构相同，呈现完全重写为报纸世界（报头徽标条、通栏粗细双线、多栏小字、号外半版红）。
- 主题：`E8 号外报纸`基底号外红（默认变体，无变体覆盖）；骨架 skeleton v7.2 逐字复制，双 SLOT 填充（theme tokens = E8 基底全套含 G3 paper 三 token；theme css = E8 G9 母题块逐字：mt-news-rule / mt-news-mast / mt-news-cols / mt-news-pull）。
- 密度：**高密度（阅读主导）**；动效档：**标准（L1–L4 各一，无 L5 交互层）**。
- 演示：浏览器打开 `index.html`，滚动 / 方向键翻页；**章节跳转三通道**：封面目录引线点击、数字键 1–5 直跳章节（0 回封面）、End 到末页。编辑：用 `editor.html` 打开，全部文字就地可改（编辑态编辑器拦截 nav-link 跳转，契约 v6.3）。

## Step 1 · 页计划表

| 页 | slide-id | 章节 | 叙事角色 | 这一页的一句话 | 谱系 | 容器分型（§13） | 内容清单 |
|---|---|---|---|---|---|---|---|
| 1 | cover | — | 号外仪式 | 内容流水线付印 | 裂屏对开（上红下纸半版 · E8 G8 唯一合法裂屏） | mt-news-cols 双栏专讯 + **rl-leader 引线目录** | 巨题 + 副题 + 专讯 2 段 + 目录 5 链 + 报尾 meta |
| 2 | impact | — | 数据英雄 | 三笔账，全部归零 | 数据英雄 | **ticker** 三格（栏间 hairline）+ **kv-rows** 通栏带 + **note-block** | 3 组 from→to（FROM/TO 标尺 + TYPE/DELTA/SRC 标注）+ 6 格图例带 + 口径注 |
| 3 | pain | 01 背景与痛点 | 问题 | 三重驱动，四处漏损 | 网格矩阵（多栏即网格） | **mt-news-cols 三栏驱动** + **metric-card** ×4（mend-bar）+ **note-block** | 3 驱动（各带来源注）+ 4 漏洞（94/86/100/78 → 0） |
| 4 | pipeline | 02 流水线 | 机制 | 需求进，物料出 | 轴与节点 | 三段栏（段顶粗规则 + mono 序号清单）+ **kv-rows** 状态带 + **note-block** | INPUT 4 / FORGE 7 / OUTPUT 4 + draw-line 连接 + 状态 5 字段 |
| 5 | deep-wide | 03 创新×复用 | 论证 | 创新做深，能力做宽 | 裂屏对开（数据级对照） | **versus-cols**（DEEP accent 单焦点 / WIDE 墨规则头）+ **kv-rows** 收口带 + **note-block** | 3+3 对照（每行 KEY 关键词 + NO 编号 + MAP 架构落点注） |
| 6 | arch | 04 架构 | 论证 | 三层架构，统一底座 | 网格矩阵（通栏横层变体） | **kv-rows** 层导图例带 + **stack-rows** ×3（右侧注记轨）+ **note-block** | L03 6 项 / L02 6 项 / L01 4 项（墨档反白基座）+ CNT/FOR/REUSE 注记 |
| 7 | online | 05 实践案例 | 证据 | 号外：系统已上线 | 数据英雄（巨数直排）+ 字段行 | **kv-rows** 字段块（五行 + 访问行）+ 指标区（巨数 100% + fill-bar）+ 产出物条 ×4 + **note-block** | 宣言 + chips ×4 + 元信息 5 行 + ACCESS 占位 + OUTPUT 4 类物料 |
| 8 | closing | — | 收束仪式 | 内容，从此流水线生产 | 宣言（报头 + 红色通栏粗细线首尾闭环） | —（mt-news-mast 终版报头） | 巨题 + 结论句 + 报尾 meta 三列 |

谱系节奏：裂屏（半版）→ 数据英雄 → 网格矩阵 → 轴与节点 → 裂屏（数据级变体）→ 网格矩阵（横层变体）→ 数据英雄（巨数变体）→ 宣言——无连续 3 页同谱系，同谱系复用均换构图变体，5 个不同谱系 ≥3 ✓。
明暗节奏：E8 为纸亮场主题，明度呼吸由色块明度档承担（纸 / 栏间 hairline / L01 墨档反白 / DEEP accent 单焦点）；封面号外红半版与收束页红色通栏规则是仅有的两处大面积 accent（首尾闭环，G1 口径）。
容器区密度：内容页 3–4 容器区/页，每容器 4–6 信息件；负空间留在容器之间，容器内部由标注层填满。

## 呈现发散（关键页 3 案 → 选定）

### 封面（p1）
- 案 A【尺度轴】号外半版：上半红底反白巨题「内容流水线」+ 下半纸白报头徽标条、双栏专讯、引线目录。E8 G1 的满屏 accent 唯一特权形态（"宜半版"即此），unforgettable 字段直译。
- 案 B【隐喻轴】印刷机滚筒：封面画滚筒/铅字盘图解"付印"。图解预支 p4 流水线信息，且滚筒是插画语义不是版式语义——号外的冲击来自满版巨题本身。
- 案 C【维度轴】三栏首页：全页纸白三栏 + 小报头。信息量够但仪式感不足——号外没有红就不是号外，G1 的 accent 特权浪费。
- **选定 A**：红带内 chars hero 巨题 + `.tt-shadow` 错版叠印（--tt-c 墨黑，白纸红底上黑影偏移=印刷套不准）；下半 mt-news-mast + mt-news-cols + rl-leader 目录三件套，一页集齐 E8 四个母题中的三个。

### 反差数据带（p2）
- 案 A【尺度轴】栏式巨数：三栏 hairline 分隔，from 值删除线小巨字 → to 值 124px 号外红巨字 + 墨影错版——"报纸头版大数字"（G8 数据英雄亲和 + G4 多栏即容器）。
- 案 B【隐喻轴】物价对比表（老报纸价目广告）：from/to 排成价目表。怀旧有趣但表格行高压缩巨数字级差，冲击力让位给秩序——数据英雄页要的是字级落差。
- 案 C【动静轴】三格全 count-up：motion.md 明示"多数字同屏全 count-up = 配额指纹病"，且 E8 G5 规定 count-up 只给数据简报英雄页的一个数字。
- **选定 A**：count-up 仅 ¥20,000（全 deck 唯一，从 0 滚起建立痛感再被 ¥0 斩杀）；from 值 `.tt-strike` ×3（被取代物画删除线）；底缘 `.rl-ticks` 刻度尺（度量语境原生）。

### 痛点页（p3）
- 案 A【维度轴】驱动三栏 + 漏洞四栏题卡：驱动装进 `mt-news-cols` 三栏正文（社论栏形态），漏洞用顶部 3px 粗规则的栏题卡 + mend-bar 双态修复条。
- 案 B【隐喻轴】漏桶：四漏洞画成桶身缺口。插画语义出戏（报纸无插画传统），且桶暗示"同一容器四缺口"，而四漏洞是四个独立环节。
- 案 C【动静轴】四漏洞全部 shake/闪烁告警：E8 禁用柔焦弹跳类，告警闪灯不属于报纸；mend-bar 的"警示渐变 → accent 纯态"两段态才是付印式利落。
- **选定 A**：mend-bar ×4（--from 94/86/100/78 → --val 0）；关键词 `.tt-mark` ×4（¥2K/条、≥5 款工具、0 组织级素材库、无全程留痕——荧光笔批注，每卡至多一处）。

### 流水线页（p4）
- 案 A【动静轴】三段栏 + draw-line 硬连接 + data-rotate 轮转：段顶粗规则即"栏题"，轮转 active = 段题与粗规则转号外红（付印色）——"各环节都在工作"的活态。
- 案 B【隐喻轴】传送带：皮带 + 滚筒图示。techy 亲和但插画化，与报纸的"栏"词汇冲突。
- 案 C【维度轴】纵向工序表：INPUT/FORGE/OUTPUT 三横行。纵向流程语义弱于横向（流程从左到右，motion.md 方向语义同构），且三段横向才装得下 FORGE 七工序清单。
- **选定 A**：draw-line ×2 描出段间箭头（EXTRACT/PRODUCE 语义落 note-block 说明，避免浮动标签与栏内标注重叠）；系统状态 RUNNING/100%/4 类/6 岗/合规全链路落 kv-rows 通栏带。

### 对照页（p5）
- 案 A【维度轴】versus-cols 数据级对照：DEEP 列头 accent 实底（全页唯一红色块 ≈2.4% 面积，守 G1 ≤5% 与 §12 单焦点）、WIDE 列头 6px 墨规则——异色异构列头即立场，行内容同构可比。
- 案 B【隐喻轴】裂屏红黑对撞：满屏对撞色场远超 3+3 均势对照的信息需求，且红色半屏直接击穿内容页 accent ≤5% 预算。
- 案 C【隐喻轴】天平：纵深 vs 横向不是轻重关系，天平的"权衡"暗示错误。
- **选定 A**：左列 data-anim="left"、右列 right 镜像异步入场（对照表首选）；每行 MAP 注记把能力映射到 p6 架构层，页间互文。

## 容器分型使用清单（§13，要求 ≥4，实际 5 型 + 母题容器）

| 分型 | 落点 | 四层字阶（① eyebrow mono 低明度 → ② 题 → ③ 体 → ④ 注 mono 低明度） |
|---|---|---|
| ticker 数据带 | p2 三格 | ① `01 · 资讯成本` + `T-01` → ② from 52px 删除线 / to 124px 900 红（FROM/TO 12px 标尺）→ ③ 描述 19px → ④ DELTA/SRC 注 |
| metric-card 指标卡 | p3 漏洞 ×4（顶 3px 粗规则即栏题，G4 无卡片立场的报纸解法） | ① LEAK·0N + L-0N → ② 27px 800 → ③ 18px（tt-mark 关键词）→ ④ LEAK RATE 行 + mend-bar + SRC 注 |
| kv-rows 字段行 | p2 图例带 ×6 / p4 状态带 ×5 / p5 收口带 ×5 / p6 层导带 ×4 / p7 元信息 5+1 行 | ① label mono 13px → ② value 20px 700；粗顶细底通栏带 + 栏间 hairline |
| versus-cols 对照列 | p5 DEEP/WIDE | 列头异色异构；行内 ① KEY + NO → ② 25px 800 → ③ 18px → ④ MAP 落点注 |
| stack-rows 堆栈层 | p6 L03/L02/L01 | ① LAYER 0N + EN 名 → ② 32px 900 → ③ 19px 清单 → ④ 右侧注记轨 CNT/FOR/REUSE |
| note-block 注记块 | p2–p7（¶ 符号标头，每页一族符号不混族） | mono 注文 + 口径注 |
| 母题容器 | mt-news-cols 三栏/双栏正文（p1 专讯、p3 驱动）；mt-news-mast 报头（p1/p8，skip 装饰件）；mt-news-rule 通栏粗细双线（每页 ≤1，p8 红规则首尾闭环） | 文本载体类母题（cols）文本保持可编辑 |

## 标注层落地（typography §5）

- 两款标注类：`.anno`（mono 13px · ink 38%）/ `.anno-sm`（12px · ink 36%），拉丁大写宽字距、中文标注归零字距（`.anno-cn`）；加 14px kv-label/chip、15px eyebrow/note-line 与刊头家具，覆盖 12–16px 全档。
- 标注位类型：容器 eyebrow、序号（T-01 / L-01 / PHASE 1/3 / li-ord 01–07 / OUT·01）、单位与口径（UNIT · CNY/条、SRC · 示例口径）、栏目标签（FROM/TO、LEAK RATE、GAUGE）、版次（SEC · A03 评论版）、来源（监管动态/渠道年报/团队调研）、架构映射（MAP · → L0N）、报尾编辑/审校/发行行。
- 纪律执行：全部 mono + 短文本 ≤20 字符 + 不承载关键结论（漏损率/100% 等关键数字永远在正文层，标注层只给口径与索引）；零编造数据——口径注一律"示例口径"。
- **harness 修正（本次顺带）**：`j_render_check.py` 与 `density_measure.py` 的亮度位置公式 `Link > Lbg ? … : 1` 对亮底主题（Link < Lbg）恒退化为 1，导致亮底 deck 的 12–13.9px 标注层永远违规/零计数——E8 是技能库里第一个亮底高密度 deck，问题首次暴露。公式 `(L−Lbg)/(Link−Lbg)` 本身极性无关，修正为 `Link !== Lbg ? … : 1`（仅亮暗等亮的非法主题退化为 1）。修正只放宽不收紧，暗底 deck 判定不变（c1 复测全过，见自检节）。

## E8 主题纪律执行

- **G1**：accent #C8102E 仅基底色；内容页 accent ≤5%（p2 三枚 to 巨数、p3 mend-bar 终态+tt-mark 小面、p4 轮转 active 段题、p5 DEEP 列头单块、p7 fill-bar 一条）；满屏 accent 仅 p1 半版红带；首尾闭环 = p1 红带 → p8 红色通栏粗细线（inline `border-color:var(--accent)`，主题明文允许的收束形态）。
- **G2**：display 极粗恒重立场（不走倒挂）：≥77px→900（封面 168 / 内容页题 96 / 巨数 124–136）、35–76px→800（段题/栏题）、正文 400 衬线（Georgia/Songti 报宋）、标注 mono 400–500；高密度对比档 ≥5:1（96:18 = 5.3）；中文 letter-spacing 归零（含刊头家具中文）。
- **G3**：paper 立场——`--texture-layer` 纸纹微沉一角仅 cover 配给（scope:cover，p1/p8 自动铺）；正文页不铺质感层。
- **G4**：圆角 0、无阴影、无卡片、无弥散渐变——全 deck 分区靠通栏粗细双线 + 栏间 1px hairline + 明度差；唯一色块容器是 p1 红带（号外特权）、p5 DEEP 列头（单焦点）、p6 L01 墨档反白条、p7 fill-bar 轨道（1px 墨框）。
- **G5**：professional 签名——锚点偏好 wipe-clip 用于通栏色块（p6 三层横带，正确对象）；禁用清单全守（无 scale-pop / blur-in / typewriter / scramble）；fx 许可全禁（零 canvas）；节奏偏移 −1 档由选型承担（利落款优先；骨架 stagger 步长为框架层烧死值，不修改框架）。
- **G8**：网格矩阵（多栏即网格）×2 变体、数据英雄 ×2、裂屏对开半版（仅封面，主题限定位）；无圆角卡/渐变卡/题花/首字下沉（c4 词汇零混入）。
- **G9 母题配额**：mt-news-rule 每页 ≤1（p2–p7 题下通栏 + p8 红规则）；mt-news-mast 仅 p1/p8（skip 装饰件）；mt-news-cols ×2（p1 双栏专讯、p3 三栏驱动——栏内只装真实正文，无卡片）；mt-news-pull 未用（无长引文内容，不硬塞）。

## 动效档（标准：L1–L4 各一）

**标题两档制**（motion.md §6）：

- 仪式页（p1/p8）：chars 逐字 **hero 档**（1s · 160ms 阶梯）——最强锚点款；
- 内容/章节页（p2–p7 共 6 页）：标题统一 **mask-lines 逐行遮罩**——E8 G5 明文亲和（"章节页 mask-lines 头条逐行显影"），editorial/professional 双亲和，生成侧显式分行 .ml-line>.ml-inner（契约 v6 产物结构）；与正文 reveal 阶梯拉开成本差；
- wipe-clip 不碰标题（职能混淆禁令），只给 p6 通栏横层色块——E8 锚点偏好的正确落位。

**每页动效清单（注意力预算复核）**：

| 页 | 锚点主动效（≤1） | L1 入场 | L2 文字 | L3 数据 | L4 环境 |
|---|---|---|---|---|---|
| p1 | chars hero 巨题 | hero 配方 | chars ×2 | — | paper-noise |
| p2 | count-up ¥20,000（唯一） | reveal 阶梯 | mask-lines | count-up | paper-noise |
| p3 | mend-bar ×4 | data-anim 阶梯 | mask-lines | mend-bar ×4 | paper-noise |
| p4 | data-rotate 轮转（语义循环） | reveal 阶梯 | mask-lines | draw-line ×2 | paper-noise + rotate |
| p5 | left/right 镜像入场 | data-anim left/right | mask-lines | — | paper-noise |
| p6 | wipe-clip 通栏 ×3（色块） | wipe-clip 阶梯 | mask-lines | — | paper-noise |
| p7 | fill-bar 100% | reveal 阶梯 | mask-lines | fill-bar | paper-noise |
| p8 | chars hero 巨题 | hero 配方 | chars | — | paper-noise |

- 每页主动效 ≤1 ✓；L4 全局一款 = **amb-noise 新闻纸噪点底纹**（data-URI turbulence 细颗粒，opacity .032，骨架烧死的 1.4s steps(2) 微 jitter，8 页全铺）——纸纹静场的"印刷颗粒活态"，选它而非 kenburns/marquee 因为报纸的底纹是纸不是镜头；fx 全禁无叠加冲突。对 G3 立场的说明：这是 L4 运动层全局选型（§6 标准档默认），质感槽位仍 cover 配给，噪点强度压到近乎不可察觉级。
- p4 的 data-rotate 是语义循环（不计入氛围配额，§6 三层叠加口径）；active 加强 = 段题与段顶粗规则转号外红（产物级 CSS，E8 付印色口径）。
- 相邻页锚点不重复 ✓（chars / count-up / mend-bar / rotate / mirror / wipe / fill-bar / chars）。

## 文字效果层（typography §7 · skeleton v7.2）

- **`.tt-shadow` 错版叠印**（e8 亲和，印刷套不准美学）：p1 号外巨题（白字 + --tt-c 墨影，红底上黑影偏移）、p8 宣言巨题（墨字 + accent 红影）、p2 三枚 to 巨数（红字 + 墨影）——全部 ≥52px（小字糊的禁忌以下不使用）；
- **`.tt-strike` ×3**：p2 from 值 ¥2,000 / ¥20,000 / 5+（只删被取代物）；
- **`.tt-mark` ×4**：p3 漏洞卡关键词（每段至多一处，45% accent 底纹计入预算）；
- **`.tt-uline` ×1**：p7 宣言"投入日常生产"（非链接语境，无样式混淆）；
- 全部为类标记，文字保持纯文本 data-editable，零运行时状态（契约 v6.4）。

## 装饰线（.rl-*，每页 ≤3 款）

rl-leader ×1 组（p1 目录——引线点线是报纸目录原生形态）/ rl-ticks ×2（p2、p4 底缘刻度，度量语境）/ rl-dashed ×2（p3 驱动与漏洞之间、p6 堆栈与注记之间，软分隔）/ rl-fade ×1（p7 收束软分隔）。全部 data-editable-skip，明度服从 G4 hairline 口径。

## 可编辑契约（v6.4）

- 8 页稳定语义 `data-slide-id`（cover/impact/pain/pipeline/deep-wide/arch/online/closing）；5 个章节页带 `data-chapter` + `id`（同值）；目录 `<a class="nav-link rl-leader">` ×5。
- 全部用户可见文字 `data-editable`（含刊头家具、目录链文字、标注层全文）；装饰（红带/噪点/箭头 SVG/刻度线/虚线/粗细分隔/mast 报头/¶ 符号/mend 轨道）一律 `data-editable-skip`。
- 零 `<img>`、零 assets 引用、零外链、产物样式块零字面 hex（仅 theme tokens SLOT 与框架层原文有 hex）。
- 提示：mend-bar/fill-bar 数值文字可就地改，几何不随数值变（改数走批注/AI 流程）。

## 自检结果（硬）

- `python3 tests/harness/j_render_check.py tests/decks/smartforge-e8/index.html`——**8/8 PASS**，零溢出零重叠零小字违规（editable 计数 25/57/44/81/54/61/59/6）。
- `python3 tests/harness/k_nav_check.py tests/decks/smartforge-e8/index.html`——**三通道全过**：① 数字键 3 → 第 3 章「创新×复用」slot 5；② 封面第一个 nav-link（#pain）→ slot 3；③ End → 末页 slot 8。
- `python3 tests/harness/density_measure.py tests/decks/smartforge-e8/index.html`——量化见下表，内容页全部达标（文本叶 ≥55 / 标注层 ≥15 / 字阶 ≥8）。
- 骨架完整性：框架层 CSS 与 JS 与 `assets/skeleton.html` 逐字节一致（脚本比对 identical）；双 SLOT 与 E8 主题块在位。
- 行为抽验（Playwright）：count-up 终值精确还原 `¥20,000`、`.sp-unit` 残留 0；mend-bar 四条终态 accent 纯态（--from 94/86/100/78 → --val 0）；data-rotate active 轮转在跑、`__pptxMotion.freeze()` 后 active 清空；mask-lines ×6 与 chars 标题入场后文本精确还原；tt-shadow ×5 / tt-strike ×3 / tt-mark ×4 / tt-uline ×1 在位。
- harness 修正回归：`python3 tests/harness/run_e2e.py` 全量复跑 **45/45 PASS**——修正只放宽亮底主题的标注层豁免，存量暗底 deck（含 c1）判定路径不变，全量回归无影响。

## 密度量化（density_measure.py 实测）

| 页 | 文本叶 | 标注层 | ≤13px 微字 | 字阶档（内容） | 字号档明细 |
|---|---|---|---|---|---|
| p1 cover | 28 | 9 | 10 | 8 | 13/15/16/18/20/26/56/168 |
| p2 impact | **61** | **29** | 29 | **9** | 12/13/14/15/19/20/52/96/124 |
| p3 pain | **56** | **24** | 24 | **9** | 12/13/14/15/18/20/24/27/96 |
| p4 pipeline | **82** | **45** | 45 | **8** | 12/13/14/15/18/20/32/96 |
| p5 deep-wide | **55** | **28** | 28 | **9** | 12/13/14/15/18/20/25/26/96 |
| p6 arch | **62** | **31** | 31 | **8** | 12/13/14/15/19/20/32/96 |
| p7 online | **60** | **29** | 29 | **9** | 12/13/14/15/18/20/24/96/136 |
| p8 closing | 8 | 3 | 5 | 4 | 13/15/24/110 |

达标线：内容页文本叶 ≥55 ✓（61/56/82/55/62/60）、标注层 ≥15 ✓（29/24/45/28/31/29）、字阶 ≥8 档连续 ✓（五区覆盖：巨数 124–136 / 标题 96 / 栏题 24–32 / 正文 18–20 / 标注 12–15，中间不断档）；与 c1 版（57–85 叶 / 22–55 标注）同量级。
