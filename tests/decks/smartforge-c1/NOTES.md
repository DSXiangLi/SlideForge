# K 期高密度验收 · C1 信号黑（基底信号橙）——「SmartForge 内容流水线」交付说明

- 产物：`index.html`（8 页，1920×1080 竖向滚动，纯 HTML 模式——零图片、零 assets 依赖）。
- 内容源：`tests/decks/smartforge-content.md`（SmartForge · 自媒体全链路营销系统，高密度基准包）。
- 主题：`c1 信号黑`基底信号橙（默认变体，无变体覆盖）；骨架 skeleton v7.1 逐字复制，双 SLOT 填充（theme tokens = C1 基底全套含 G3 flat 三 token；theme css = C1 G9 母题块逐字，含 `--ease-out` 过冲缓动签名）。
- 密度：**高密度（阅读主导）**；动效档：**标准（L1–L4 各一，无 L5 交互层）**。
- 演示：浏览器打开 `index.html`，滚动 / 方向键翻页；**章节跳转三通道**：封面目录点击、数字键 1–5 直跳章节（0 回封面）、End 到末页。编辑：用 `editor.html` 打开，全部文字就地可改（编辑态编辑器拦截 nav-link 跳转，契约 v6.3）。
- **v2 密度重做（2026-09-20）**：按 `docs/research/demo1-density-analysis.md` 五条范式就地重做——8 页结构 / 章节跳转 / mend-bar / data-rotate / 呈现发散结论全部不变，只加密度：标注层全量落地（每内容页 ≥15 处 mono 12–16px 低明度标注）、容器区 3–5 个/页、文本叶 ≥55/内容页、字阶 ≥8 档连续。量化对比见文末「v2 密度量化」。
- **v3 动效层返工（2026-09-20）**：按 motion.md §6 两档制 + 隐性运动——内容页标题统一 chars 默认档（wipe-clip 撤下归还色块）、amb-noise 信号噪点底纹全 deck（封面让位 fx）、巨号页码 folio-breath 呼吸（8s · 摆幅 .08）。清单见「动效档」节。
- **v4 文字效果层（2026-09-20，K 期第三轮 / skeleton v7.1）**：应用 typography.md §7 `.tt-*` 文字效果词汇（c1 G2 已声明亲和 `.tt-outline` 混排与 `.tt-strike` 对照）。框架层随 skeleton 同步至 v7.1（新增 `.tt-*` 四规则，meta skeleton-version 7.1），主题 SLOT 不动。落点见「文字效果层」节。
- **v5 容器边界返工（2026-09-20）**：隔离实验 `tests/decks/isolation-ab/` C 版「面+框」裁决落地——高密度容器区统一 灰档面 + 1px hairline 细框（ink 18%），依据 components.md §12 暗底例外 + §13 容器边界义务。落点见「容器边界」节。

## Step 1 · 页计划表

| 页 | slide-id | 章节 | 叙事角色 | 这一页的一句话 | 谱系 | 容器分型（§13） | 内容清单 |
|---|---|---|---|---|---|---|---|
| 1 | cover | — | 开场仪式 | SMART FORGE = 内容流水线 | 宣言（巨字+橙色块） | —（目录 nav ×5，带英文小注） | 标题 + 副题 26 字 + kicker + meta 标注行 + 目录 5 章 |
| 2 | impact | — | 数据英雄 | 三笔账，全归零 | 数据英雄 | **ticker** 三格 + **kv-rows** 图例带 + **note-block** | 3 组 from→to（格内 FROM/TO 标尺 + TYPE/DELTA/SRC 标注）+ 6 格图例带 + 口径注 |
| 3 | pain | 01 背景与痛点 | 问题 | 三重驱动，四处漏损 | 网格矩阵 | **metric-card** ×3（驱动）+ ×4（漏洞，配 mend-bar + LEAK RATE 标注行）+ **note-block** | 3 驱动（含 → 影响行 + TYPE 标注）+ 4 漏洞（94/86/100/78） |
| 4 | pipeline | 02 流水线 | 机制 | 需求进，物料出 | 轴与节点 | 三段卡（清单带 mono 序号 + 类型标签）+ **kv-rows** 状态带 + **note-block** | INPUT 4 / FORGE 7 / OUTPUT 4 + 箭头标注 EXTRACT/PRODUCE + 状态 5 字段 |
| 5 | deep-wide | 03 创新×复用 | 论证 | 创新做深，能力做宽 | 裂屏对开（数据级对照） | **versus-cols**（DEEP accent 档头 / WIDE 纸档头；v5 起列体灰档面+细框）+ **kv-rows** 收口带 + **note-block** | 3 + 3 对照项（每行 KEY 关键词 + MAP 架构落点标注） |
| 6 | arch | 04 架构 | 论证 | 三层架构，统一底座 | 网格矩阵（通栏横层变体） | **kv-rows** 层导图例带 + **stack-rows** ×3（右侧注记轨）+ **note-block** | L03 6 项 / L02 6 个 / L01 4 层 + 每层 EN 名 + CNT/FOR/REUSE 注记 |
| 7 | online | 05 实践案例 | 证据 | 系统已上线 | 宣言 + 字段行 | **kv-rows** 字段块（纵向 8 行）+ kv 访问块 + 产出物条 ×4 | 宣言 + 状态 chips + ring 100% + 元信息 8 行 + OUTPUT 4 类物料 |
| 8 | closing | — | 收束仪式 | 首尾闭环 | 宣言（橙色块呼应封面） | — | 巨字 + 同尺寸橙色块 + 元信息 + STACK 标注 |

谱系节奏：宣言 → 数据英雄 → 网格矩阵 → 轴与节点 → 裂屏对开 → 网格矩阵（变体）→ 宣言 → 宣言——无连续 3 页同谱系（仅 p3/p6 同谱系且不相邻、构图变体不同：4 卡网格 vs 通栏横层），5 个不同谱系 ≥3 ✓。
明暗节奏：C1 全暗场主题（--paper #1a1a1a），明暗呼吸由色块明度档承担（纸/灰/墨/accent 四档轮转），封面与收束的大橙色块是仅有的两处满屏级 accent（首尾闭环，G1 纪律允许）。
容器区密度（v2）：内容页 3–4 容器区/页（p2 ticker+图例带+注记 / p3 驱动卡排+漏洞卡排+注记 / p4 流水线卡+状态带+注记 / p5 对照列+收口带+注记 / p6 图例带+堆栈+注记 / p7 元信息块+访问块+产出物条），每容器 4–6 信息件；负空间留在容器之间，容器内部由标注层填满。

## 呈现发散（关键页 3 案 → 选定，v2 不变）

### 封面（p1）
- 案 A【尺度轴】巨字宣言：188px 极粗 SMART FORGE + 信号橙色块压「内容流水线」。dramatic 亲和，C1 G8 第一亲和谱系。
- 案 B【隐喻轴】管道剖面：封面画一条横贯的管道图示预演流水线。信息前置透支 p4，封面仪式感应靠尺度不靠图解。
- 案 C【动静轴】particle-drift 微粒 + 巨字静态：微粒上行=内容涌出。C1 fx 白名单内，但 constellation 的"信号连线"语义更贴"信号黑"世界（信号弹彼此呼应成网）。
- **选定 A + constellation**：巨字尺度是 C1 的 unforgettable（黑场唯一橙色块=全场焦点）；fx 选 constellation（该页唯一 L4）。

### 反差数据带（p2）
- 案 A【尺度轴】巨字直排：三格 from 巨字删除线 → to 巨字 accent，纯字重压强，零图形。最 C1。
- 案 B【隐喻轴】天平/赛道：三笔账语义不同构（成本/成本/工具数），天平只装两项、赛道暗示同单位竞赛，均不忠实（motifs.md 禁忌）。
- 案 C【动静轴】三格全部 count-up：motion.md 对照表明示"多数字同屏全 count-up = 配额指纹病"，且 C1 G5 规定 count-up 只给真 KPI 英雄数字。
- **选定 A**：ticker 三格；count-up 仅给 ¥20,000（全 deck 唯一，从 0 滚起建立痛感再被 ¥0 巨字斩杀）；三枚 to 值 scale-pop 砸落（C1 锚点偏好）。

### 痛点页（p3）
- 案 A【动静轴】mend-bar 双态修复条：漏损率先充满（警示渐变建立张力）再收窄归零并切信号橙纯态——"修复由警示色到主题色"的语义同构（motion.md 编排纪律 4）。
- 案 B【隐喻轴】多米诺：四漏洞依次倾倒。dramatic 亲和，但"倾倒"暗示崩溃加剧，与"可修复"语义相反。
- 案 C【维度轴】漏斗：四漏洞画成漏斗四级。漏洞是并列枚举不是逐级转化，数据形态不符。
- **选定 A**：3 驱动 metric-card（无条）+ 4 漏洞 metric-card（各配 mend-bar，--from 94/86/100/78 → --val 0）；漏损率数字静态直标（改数不改几何，交付说明提示）。

### 流水线页（p4）
- 案 A【隐喻轴】管道：粗管贯穿 + 段间阀门。techy/professional 亲和，但管道图示与 C1 flat 直角色块词汇冲突（管=圆角渐变暗示）。
- 案 B【动静轴】三段卡 + draw-line 硬连接 + data-rotate 轮转：三段 INPUT/FORGE/OUTPUT 直角色块卡，连接件由 draw-line 描绘（因果方向性），data-rotate 轮转 active 承担"各环节都在工作"的活态隐喻（K 期新 recipe 的设计场景）。
- 案 C【隐喻轴】接力：跑者剪影交接。剪影插画气质出戏，且三段无交接风险语义。
- **选定 B**：draw-line（L3 描绘款）+ data-rotate（L4 loop）分层清晰不撞车；active 加强 = accent 描边 + 微光（C1 气质，产物内联定义）；系统状态 RUNNING/100%/4 类模态/6 岗位/合规全链路 落 kv-rows 横向状态带。

### 对照页（p5）
- 案 A【隐喻轴】裂屏对开：黑橙两半对撞。C1 G8 亲和，但 DEEP/WIDE 是 3+3 均势对照，满屏对撞色场面积远超信息需求，且橙色半屏破内容页 accent ≤10% 预算。
- 案 B【维度轴】对照列 versus-cols（数据级）：两列头异色（DEEP accent 档 / WIDE 灰档，守 §12 单焦点——墨+accent 不同组共存），逐行对照项四层字阶；列头色即立场，行内容同构可比。
- 案 C【隐喻轴】镜像：同构图形左右镜像填异值。DEEP/WIDE 条目语义不同构（纵深创新 vs 横向复用），镜像的"同构不同命"暗示不成立。
- **选定 B**：左列 data-anim="left"、右列 right 镜像异步入场（对照表首选）；accent 仅 DEEP 列头一块（全页唯一橙色块，≈3% 面积）。

## 容器分型使用清单（§13，6 型全用，要求 ≥4）

| 分型 | 落点 | 四层字阶（① eyebrow mono 低明度 → ② 题 → ③ 体 → ④ 注 mono 低明度） |
|---|---|---|
| ticker 数据带 | p2 三格 | ① `01 · 资讯成本` + `T-01` 标注 → ② from 54px 删除线 / to 132px 900 accent（带 FROM/TO 12px 标尺）→ ③ 描述 19px → ④ 口径注 15px + `SRC · 示例口径` 12px |
| metric-card 指标卡 | p3 驱动 ×3 + 漏洞 ×4 | ① DRIVER/LEAK · 0N mono → ② 28px 800 → ③ 18px（驱动卡含 → 影响行）→ ④ mono 注（漏洞卡含 LEAK RATE 标注行 + mend-bar，`--from/--val` 为产物内容） |
| kv-rows 字段行 | p2 图例带（6 格）+ p4 状态带（5 格）+ p5 收口带（5 格）+ p6 层导图例带（3 格）+ p7 元信息块（8 行）+ 访问块 | ① label mono 15px 低明度 → ② value 21px 600；分隔用墨档色块 + 明度差（C1 G4 不用 hairline） |
| versus-cols 对照列 | p5 DEEP/WIDE | 列头异色（accent 档 ×1 单焦点 / 纸档透明头，v5 起列体灰档面+细框）；行内 ① DEEP·01 + KEY 标注 → ② 26px 800 → ③ 18px → ④ MAP 架构落点标注 12px |
| stack-rows 堆栈层 | p6 L03/L02/L01 | ① LAYER 0N mono → ② 层名 34px 800 → ③ 清单 19px（信号方块分隔）→ ④ 右侧注记轨（CNT/FOR/REUSE 等 kv 行）+ EN 名标注 |
| note-block 注记块 | p2/p3/p4/p5/p6 口径注 | 信号方块作注记标头（母题作 eyebrow 位，§13 接口条款）+ mono 注文 |

## 标注层落地（v2 核心 · typography §5）

- 两款标注类：`.anno`（mono 13px · ink 46%）/ `.anno-sm`（12px · ink 42%），拉丁大写宽字距、中文标注归零字距（`.anno-cn`）；加上既有 15px eyebrow/note-line 与 14–15px 刊头家具，标注层覆盖 12–16px 全档。
- 标注位类型：容器 eyebrow、序号（T-01 / PHASE 1/3 / li-ord 01–07 / OUT · 01）、单位与口径（UNIT · CNY/条、BASIS/SRC · 示例口径）、状态（TYPE · EXT/INT、LIVE · 实时）、栏目标签（FROM/TO、LEAK RATE）、来源与阅读注（READ · FROM → TO、MAP · → L0N）、箭头语义（EXTRACT/PRODUCE）。
- 纪律执行：全部 mono + 低明度 42–65% + 短文本 ≤20 字符 + 不承载关键结论（漏损率等关键数字同时在 14px bar-val 与 mend-bar 几何上表达，标注层只给口径与索引）；零编造数据——所有新增标注为单位/序号/类型/口径/架构映射等真实元信息，口径注一律写"示例口径"。
- 密而不乱：页面焦点仍 1–2 个（巨字 + 单 accent），标注层整体退为印刷肌理；j_render_check 的小字豁免同步升级为"mono + ≥12px + 合成色线性亮度 ≤65% 区间"（全亮小字仍判违规）。

## C1 主题纪律执行

- **G1**：accent #FF5722 仅基底色无变体；内容页 accent 面积 ≤10%（p2 三枚 to 数字、p3 信号条+信号方块、p4 RUNNING 值、 p5 DEEP 列头单块 ≈3%、p6 信号方块、p7 ring 描边——逐页单焦点）；满屏级橙色块仅 p1/p8（首尾闭环）。
- **G2**：标题恒重 900（Arial Black 立场，不走倒挂）；高密度对比档 ≥5:1（内容页主标题 96–108px vs 正文 18px = 5.3–6:1；封面巨字 188px 特档）；中文 letter-spacing 归零（含刊头家具与中文标注）。
- **G3**：flat——无质感层、无纹理。
- **G4**：全部直角纯色块（accent/paper-tint/ink-tint 明度档），零渐变、零阴影；分区靠明度差与留白；**v5 起**高密度容器区按隔离实验 C 版裁决叠加 1px hairline 细框（ink 18%，§12 暗底例外——themes.md C1 G4 文本同步由另一任务进行，见「容器边界」节）。
- **G5**：dramatic 签名——锚点序列 chars（p1/p8 巨字）→ count-up 唯一 KPI（p2）→ mend-bar ×4（p3）→ draw-line+rotate（p4）→ 左右镜像（p5）→ wipe-clip 通栏（p6）→ ring 100%（p7）；过冲缓动 `cubic-bezier(.2,1.25,.3,1)` 由主题 css 块注入；禁用清单遵守（无 blur-in/mask-lines/gradient-flow）。**v2 密度增加不动动效配额**：每屏主动效仍 1 个，循环氛围 ≤2（p1 constellation + p4 data-rotate 各归本页），新增信息全部是静态标注层。
- **G8**：无连续两页网格矩阵（p3 网格 → p4 轴与节点隔开）；无瑞士系/终端系词汇混入。
- **G9 母题配额**：信号条每页 ≤1 且只在标题区/页眉位（p1–p7）；巨号页码 02–07 只在内容页底缘背景层（7% 明度不抢焦）；信号方块只在列表/编号/注记标头位；母题件全部 `data-editable-skip`。
- **fx 许可**：全 deck 仅 p1 封面 1 个 `constellation`（白名单内），该页不再叠 amb/light 件。

## 动效档（标准：L1–L4 各一）——v3 动效层返工（2026-09-20）

v2 遗留问题：全 deck 标题清一色 wipe-clip（职能混淆——wipe 是色块揭示款不是文字款）、背景与装饰层零运动。v3 按 motion.md §6「标题动效两档制」+「背景与装饰层的隐性运动」返工：

**标题两档制**：

- 仪式页（p1/p8）：chars 逐字砸落 **hero 档**（1s 时长 · 160ms 阶梯）——最强锚点款，不变；
- 内容/章节页（p2–p7 共 6 页）：标题统一 **chars 默认档**（.5s · 45ms 小步错峰）——同一 recipe 两档节奏：封面慢速砸落是仪式，内容页快速逐字是"信号解码"的系统感。**选型理由**：C1 G5 禁用清单明列 blur-in / **mask-lines** / gradient-flow（柔化手段削弱信号冲击）——mask-lines 对 c1 非法；typewriter/scramble 是 techy 主题限定款；可用文字款只剩 chars，而 rise-in 是整块位移（enter 族）、与正文 reveal 拉不开成本差。chars 默认档 × hero 档的节奏差即两档制的落地形态；
- wipe-clip 从标题全部撤下，回归正确对象——色块：p1/p8 信号橙色块、p6 stack-row 通栏横层（本来就是色块，保留）。

**背景与装饰层隐性运动**：

- L4 全局款：**amb-noise 信号噪点底纹**（data-URI turbulence 细颗粒、opacity .04、骨架烧死的 1.4s steps(2) 微 jitter）——噪点即"信号"世界的底纹，贴题且零资产依赖；p2–p8 全铺，**封面让位 constellation fx**（fx 优先不叠加，§6/§4 fx 纪律）。对 C1 G3 flat 立场的说明：这是 L4 运动层的全局选型（§6 标准档默认），不是 G3 质感槽位——质感槽位仍 none，噪点强度压到近乎不可察觉的印刷颗粒级；
- 装饰呼吸：巨号页码 mt-sig-folio（p2–p7）挂自定义 `folio-breath`——周期 8s、opacity 摆幅 .08（骨架 amb 上限内取最小；骨架成品 amb-pulse 摆幅 .4 对家具层太强，故按 §6「≤.08」口径落产物级 keyframes），reduced-motion 停用；
- 刊头家具不动。

**注意力预算复核（每页动效清单，前 → 后）**：

| 页 | 锚点主动效（≤1） | L1 入场 | L2 文字 | L3 数据 | L4 环境 | 循环款计数（氛围 ≤2） |
|---|---|---|---|---|---|---|
| p1 | chars hero 巨字 | hero 配方 + 橙块 wipe-clip | chars（hero 档） | — | constellation fx | 1（fx） |
| p2 | count-up ¥20,000 | reveal 阶梯 | ~~wipe-clip~~ → chars（默认档） | count-up + scale-pop ×3 | **+噪点** +folio 呼吸 | 2（noise+folio） |
| p3 | mend-bar ×4 | reveal 阶梯 | ~~wipe-clip~~ → chars | mend-bar ×4 | **+噪点** +folio 呼吸 | 2 |
| p4 | data-rotate 轮转 | reveal 阶梯 | ~~wipe-clip~~ → chars | draw-line ×2 | **+噪点** +folio 呼吸 +rotate（语义循环） | 氛围 2 + 语义 1 |
| p5 | left/right 镜像入场 | data-anim left/right | ~~wipe-clip~~ → chars | — | **+噪点** +folio 呼吸 | 2 |
| p6 | wipe-clip 通栏 ×3（色块，正确对象） | wipe-clip 阶梯 | ~~wipe-clip~~ → chars | — | **+噪点** +folio 呼吸 | 2 |
| p7 | ring 100% | reveal 阶梯 | ~~rise-in~~ → chars | ring --val:100 | **+噪点** +folio 呼吸 | 2 |
| p8 | chars hero 巨字 | hero 配方 + 橙块 wipe-clip | chars（hero 档） | — | **+噪点**（无 fx 冲突） | 1 |

- 每页主动效 ≤1 ✓；氛围循环每屏 ≤2 ✓（p4 另有语义循环 data-rotate——§6「装饰呼吸 + 语义微动效 + 标注层」三层叠加口径，不计入氛围配额）；
- L5 不启用（标准档）；密度增加与动效返工不增任何同层数量（§5 硬规则：加层不加同层数量）。

## 文字效果层（v4 · typography.md §7 · skeleton v7.1）

- **p1 封面标题混排**：「SMART FORGE」拆为两个 chars 词元——SMART 保持 ink 填充巨字、FORGE 加 `.tt-outline`（--tt-c 默认 ink，188px ≥ 64px 下限），描边词充当背景层、填充词是焦点；酸橙色块「内容流水线」不动，accent 焦点仍唯一。技术注：chars 拆字引擎按元素 textContent 重建文本，混排必须按词拆成两个 `data-anim="chars"` 元素（各带 data-editable），动画完成各自还原、类标记不受运行时影响。
- **p2 ticker from 值 `.tt-strike` ×3**：¥2,000 / ¥20,000 / 5+ 三枚 from 值——被取代物画删除线（demo 签名手法）；原 `.tick-from` 产物样式里的内联删除线（4px）移交词汇类（.07em ≈ 3.8px，色随 currentColor 不变），to 值 accent 巨字不动。
- **p3 关键数字词 `.tt-mark` ×4**（每卡至多一处）：¥2K / 条（成本不可控）、≥5 款工具（链路碎片化）、0 组织级素材库（资产无法沉淀）、无全程留痕（合规难闭环）；45% accent 底纹小面，计入 G1 accent 预算。
- **p8 收束页宣言 `.tt-uline` ×3**：新增宣言行「你的数据，你的设备，你的规则。」三个并列短语各挂粗下划条（reveal 入场，32px/700）。
- 纪律：全部是类标记，文字保持纯文本 data-editable，零运行时状态、零净化新增（契约 v6.4）；`.tt-outline` 全 deck 仅封面一处（每页至多一处）。

## 容器边界（v5 · 隔离实验 C 版「面+框」裁决 · components.md §12 暗底例外 + §13 容器边界义务）

- **统一边界手段**：`.tick-cell / .mcard / .pipe-card / .vcol / .stack-row / .kv-band / .kv-block / .out-cell` 全部 = 面（灰档 `--paper-tint` 或墨档 `--ink-tint`）+ **1px hairline 细框** `color-mix(in srgb, var(--ink) 18%, transparent)`（c1 母题 color-mix 口径，零字面 hex）。一条产物样式规则覆盖，同页同构：各容器区 gap/padding 维持 v2 起的恒等值（ticker 24/32、mcard 20/30×28、pipe 36/30、stack 18/26×36、kv-band 36/22×36）。
- **p5 对照列结构补齐**：`.vcol` 补灰档面 + 底 padding（原 vcol 裸排只有 head 有面，不满足边界义务）；WIDE 列头降纸档（透明底——避免与列体同色面叠面），DEEP accent 列头保持全页唯一焦点块（§12 单焦点不破）；垂直空间随列体增厚回收（vcol gap 18→12、列头 padding 22→16、vcols/band/note 上边距收紧），渲染检查通过。
- **不动项**：封面/收束满版 accent 色块保持无框（仪式页特权）；卡内 accent 小件不动（mend-bar 修复条、p4 rotate active 的 accent outline+微光）——细框是容器边界、accent 是焦点，两层各司其职；文本/密度/动效/标注层一概未动（控制变量）。
- **themes.md 同步状态**：C1 G4 正由另一任务改写为允许暗底灰档面+细框；本 deck 依据用户裁决 + §12 暗底例外条款先行落地，G4 文本落地后即合规闭环（当前 G4 文本"hairline：不用"为旧口径）。
- 密度复测：文本叶/标注层/字阶与 v2 持平（density_measure 口径不变；p3 editable 叶 56→52 是 v4 `.tt-mark` 子 span 使父级不再是文本叶的计数口径差，j_render 口径 56 不变，信息量为零变化）。

## 可编辑契约（v6.4）

- 8 页稳定语义 `data-slide-id`（cover/impact/pain/pipeline/deep-wide/arch/online/closing）；5 个章节页同时带 `data-chapter` 与 `id`（与 slide-id 同值）；目录 `<a class="nav-link" href="#id">` ×5。
- 全部用户可见文字 `data-editable`（含刊头家具、目录链接文字与英文小注、kv label/value、全部标注层文本）；装饰（信号条/巨号页码/信号方块/mend-track+fill/连接 SVG/canvas fx/ring 几何）一律 `data-editable-skip`——Playwright 逐页核验：非 editable 文本叶只有 folio 页码与 tick 箭头两类 skip 件。
- 零 `<img>`、零 assets 引用；grep 自检：8 个 slide-id、产物样式块无字面 hex（字面 hex 仅存在于 theme tokens SLOT 与框架层 mend-bar 警示渐变等骨架原文）。
- 提示：mend-bar/ring 的数值文字可就地改，几何不随数值变（改数走批注/AI 流程，图表分层惯例）。

## 自检结果（硬）

- `python3 tests/harness/j_render_check.py tests/decks/smartforge-c1/index.html`——8/8 PASS，零溢出零重叠零小字违规（v5 后 editable 计数 22/57/56/84/58/59/55/7；v4 起封面 h1 拆双词元 +1、收束页 +1）。检查器小字规则已升级：mono + ≥12px + 低明度（合成色线性亮度退到底色→墨色区间 ≤65%）的标注层放行，全亮小字仍判违规。
- v5 边界核验（Playwright 计算样式抽验）：tick-cell/mcard/vcol/stack-row/kv-band 全部 `border 1px color(srgb 1 1 1 / 0.18)` 生效；`.vcol` 面 = rgb(36,36,36)（--paper-tint）；chars 拆字（含封面双词元）完成后 `.sp-unit` 残留 0；count-up 终值 `¥20,000` 精确还原。
- `python3 tests/harness/k_nav_check.py tests/decks/smartforge-c1/index.html`——三通道全过：① 数字键 3 → 第 3 章「创新×复用」slot 5；② 点击封面第一个 nav-link（#pain）→ slot 3；③ End → 末页 slot 8。
- 骨架完整性：`assets/skeleton.html` 框架层 CSS 与 JS 与 deck 内对应区块逐字节一致（脚本比对 identical）；双 SLOT 与 C1 主题块在位。
- 行为抽验（Playwright）：fx constellation 入视口初始化（1920×1080 位图）；count-up 终值精确还原 `¥20,000`；mend-bar 四条终态 scaleX(0) + accent 纯态；data-rotate active 轮转 0→1 且 accent 描边+微光生效；`__pptxMotion.freeze()` 后 active 清空、fx 摘除 width/height；拆字动画完成后 `.sp-unit` 残留为 0。
- v3 动效抽验（Playwright）：8 个标题全部 chars（封面/收束 hero 档、内容页默认档）且入场后文本精确还原、`.sp-unit` 残留 0；噪点层 7 处（p2–p8，封面无——fx 优先）、`amb-noise` 1.4s 循环在跑；folio-breath 8s 在跑；**reduced-motion 下 noise/folio 循环全静态、标题 opacity 1 纯文本可读**；freeze 后 rotate active 清空、fx 无尺寸属性残留。
- v4 文字效果自检（Playwright，编辑器 harness 加载态）：`.tt-outline` ×1 且为 FORGE；演示态描边 1.5px + 透明填充；**编辑态模拟（加 `ed-editing` class）描边归零、还原本色 ink**（契约 v6.4）；`.tt-strike` ×3 line-through 生效；`.tt-mark` ×4；`.tt-uline` ×3；封面双词元 chars 完成后 h1 文本精确还原 `SMART FORGE`、`.sp-unit` 残留 0。j_render_check 8/8 PASS（editable 22/57/56/84/58/59/55/7）；k_nav_check 三通道 PASS；框架层与 skeleton v7.1 逐字节一致。
- 全量回归 `python3 tests/harness/run_e2e.py`：45/45 PASS（含 T1-smartforge-c1 编辑器往返幂等、T22 章节跳转三通道、T13/T19 动效兼容）。

## v2 密度量化（`python3 tests/harness/density_measure.py`，对比 demo1 解剖基线）

| 页 | 文本叶 前→后 | 标注层 前→后 | ≤13px 微字 前→后 | 字阶档（内容） 前→后 |
|---|---|---|---|---|
| p1 cover | 15 → 21 | 7 → 13 | 0 → 6 | 6 → 8 |
| p2 impact | 25 → **61** | 7 → **36** | 0 → **23** | 6 → **10** |
| p3 pain | 35 → **57** | 15 → **33** | 0 → **16** | 5 → **8** |
| p4 pipeline | 40 → **85** | 11 → **55** | 0 → **42** | 6 → **9** |
| p5 deep-wide | 34 → **59** | 14 → **33** | 0 → **25** | 6 → **10** |
| p6 arch | 31 → **60** | 6 → **22** | 0 → **15** | 5 → **8** |
| p7 online | 22 → **56** | 8 → **35** | 0 → **23** | 6 → **9** |
| p8 closing | 5 → 6 | 3 → 4 | 0 → 1 | 4 → 5 |

达标线（demo1-density-analysis §四）：内容页文本叶 ≥55 ✓（61/57/85/59/60/56）、标注层 ≥15 ✓（36/33/55/33/22/35）、字阶 ≥8 档连续 ✓（五区覆盖：巨字 folio/to 数字 → 标题 96–108 → 小标 26–34 → 正文 18–20 → 标注 12–15，中间不断档）。demo1 基线（61–94 叶 / 21–54 微字 / 8–14 档）已整体进入同一量级；≤13px 微字从 0 断层补齐到 15–42 个/内容页。
