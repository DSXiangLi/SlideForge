# J 期终验 · A1 电子杂志（基底墨黑）——「数据回家」交付说明

- 产物：`index.html`（6 页，1920×1080 竖向滚动，纯 HTML 模式——零图片、零 assets 依赖）。
- 主题：`a1 电子杂志`基底墨黑配色（默认变体，无变体覆盖）；骨架 skeleton v6 逐字复制，双 SLOT 填充（theme tokens = A1 基底全套含 G3 墨韵三 token；theme css = A1 G9 母题块逐字）。
- 密度：低密度（演讲主导）；动效档：标准（L1–L4 各一，无 L5 交互层）。
- 演示：浏览器打开 `index.html`，滚动或方向键翻页。编辑：用 `editor.html` 打开，全部文字可就地改。

## Step 1 · 页计划表

| 页 | slide-id | 叙事角色 | 这一页的一句话 | 内容清单 | 明/暗 | 呈现发散（关键页 3 案 → 选定） |
|---|---|---|---|---|---|---|
| 1 | cover | 开场仪式 | 数据回家 | 标题 4 字 + 副题 12 字 + kicker | 暗（cover-page，首尾闭环起点） | 普通页豁免（巨字宣言直落：160px 衬线 + chars 锚点 + ascii-field 仪式层） |
| 2 | problem | 问题 | 今天的软件把数据锁在云端 | 2 要点 ×（标题 ≤6 字 + 正文 ≤45 字）+ 一句收束 | 亮 | 普通页豁免 |
| 3 | metrics | 数据英雄 | 三个数字说明云端的风险与本地的安心 | 3 数字（73% / 7 天 / 0）+ 各 1 句注 + 一句收束 | 亮（paper-tint 灰档呼吸页） | 见下「呈现发散 · 数据英雄页」 |
| 4 | compare | 对比 | 同构的两种软件，命运相反 | 2 列 × 4 行对照 | 亮 | 见下「呈现发散 · 对比页」 |
| 5 | sync-flow | 流程 | 同步引擎如何把数据送回家 | 6 节点 ×（标签 ≤6 字 + 注 ≤14 字） | 亮 | 见下「呈现发散 · 流程页」 |
| 6 | closing | 收束宣言 | 你的数据，你的设备，你的规则 | 宣言 3 行 ×5 字 + 3 行动建议 | 暗（cover-page，首尾闭环） | 普通页豁免（quote 配方 + mask-lines 锚点） |

明暗节奏说明【默认推翻，留档】：明暗序列为 暗/亮/亮(灰)/亮/亮/暗，正文四页连续偏亮。A1 的 G1 纪律规定暗色反白页（满屏 accent）是封面/收束特权，内容页不可用暗页做呼吸；因此呼吸改由 G4 允许的 paper-tint 灰档承担（p3 数据英雄页整页灰底），主题纪律优先于明暗节奏默认。

## 呈现发散 · 数据英雄页（p3）

- 案 A【尺度轴】巨字直排：三个数字 160px 衬线直排分栏，hairline 分隔，无图表。亲和 editorial；A1 G5 锚点偏好明示"数字以字号对比直排为主"。
- 案 B【隐喻轴】刻度盘/仪表：73% 用 ring 环形进度 + 仪表读数。亲和 professional/techy；7 天与 0 非百分比语义，硬套仪表犯 motifs.md 禁忌，且仪表气质偏离杂志系。
- 案 C【动静轴】翻牌 split-flap：数字卡上下半、中线缝合的时刻表意象。亲和 playful/techy，戏谑感与"数据蒸发"的严肃议题冲突。
- **选定 A**：编辑气质亲和 + G5 锚点偏好直接点名；count-up 只给 73% 一个数字（G5：count-up 只给真正的 KPI 英雄页锚点），7 天 / 0 静态直排（0 从 0 起滚无意义）。

## 呈现发散 · 对比页（p4）

- 案 A【隐喻轴】裂屏对开：左右色场对撞中间一道缝。亲和 dramatic；但暗半屏擦边 A1 G1"暗色反白是封面/收束特权"的纪律，且四对条目信息量均势，裂屏的大色场是浪费。
- 案 B【维度轴】镜像：同一列表结构左右镜像——左列灰阶 + 虚线下划（云优先），右列实墨 + 字重（本地优先），"同构不同命"。亲和 editorial/calm，motifs.md 明示适合 editorial。
- 案 C【隐喻轴】天平：中央支点两侧砝码、梁倾角即结论。四项对比非数值，天平无法承载 4 对条目，弃。
- **选定 B**：镜像即本页标题「同构不同命」的视觉转译——同构（完全对称的双栏四行）承载"不同命"（灰虚 vs 墨实）；零卡片、零色块，全靠 G4 hairline 与字重对比，最杂志。镜像入场（data-anim left/right）放弃：其阶梯 75ms 低于 A1 节奏偏移 ≥90ms 的要求，统一改用 reveal --d ≥120ms 阶梯，镜像感由静态造型承担。

## 呈现发散 · 流程页（p5）

- 案 A【隐喻轴】管道：粗管贯穿、阀门仪表为环节状态。亲和 techy/professional，工业感与纸面杂志世界不符。
- 案 B【动静轴】轴与节点 + draw-line：水平墨线贯底、6 个方墨点节点、逐环节 reveal 阶梯 + 轴线 draw-line 描绘入场。轴与节点是 A1 G8 亲和谐系，draw-line 是 G5 数据页锚点偏好，描绘的方向性（左→右）承担流程因果。
- 案 C【隐喻轴】接力：跑者剪影交接棒，强调交接风险。亲和 dramatic，剪影插画气质出戏，且 6 环节无"交接风险"语义可对应。
- **选定 B**：严格串行流程 × 杂志系 = 一条被"画出来"的墨线轴；每环节信息控在标签 ≤6 字 + 注 ≤14 字，守住低密度。

## 母题使用（G9，每页 ≥1 件）

| 页 | 母题件 |
|---|---|
| 1 cover | `.mt-vquote` 右缘竖排「DATA COMES HOME · MMXXVI」+ `.mt-dot`（kicker 前） |
| 2 problem | `.mt-ghost`「锁」（右下背景层，远离左上标题区，不抢焦）+ `.mt-dot` |
| 3 metrics | `.mt-dot`（kicker 前） |
| 4 compare | `.mt-ghost`「VS」（底部居中背景层）+ `.mt-dot` |
| 5 sync-flow | `.mt-dot`（kicker 前） |
| 6 closing | `.mt-vquote` 左缘竖排「YOUR DATA · YOUR DEVICE · YOUR RULES」+ `.mt-dot`（kicker + 3 行动建议前，暗页反白覆写 background:var(--paper)） |

禁忌遵守：Ghost 字不与标题同区（p2 标题左上/字右下，p4 标题左上/字底中）；内容页 Ghost 不连用（p2、p4 之间隔 p3）；母题件一律 `data-editable-skip`；未跨主题借用（无加号/点阵/ASCII 框）。

## 动效签名执行（G5 editorial · 标准档 L1–L4 各一）

- L1 入场：全页 reveal 阶梯，`--d` 步长 ≥120ms（执行节奏偏移"阶梯步长 ≥90ms"；骨架默认 [data-anim] 阶梯 75ms 故内容页不混用多元素 data-anim）。
- L2 文字：p1 封面标题 `chars`（hero 配方，阶梯 160ms）+ p6 收束宣言 `mask-lines` 逐行遮罩（quote 配方，行阶梯 110ms）——均为 G5 锚点偏好点名项。
- L3 数据：p3 `count-up` 仅 73%（真 KPI 英雄页锚点）；p5 同步轴 `draw-line`（SVG line，量长藏线描绘）。
- L4 环境：p1 `<canvas data-fx="ascii-field">`——A1 fx 许可白名单唯一项；仪式页 1 个/页，该页不再叠 amb/light 件；fx 参数全部烧死在骨架。
- L5：不启用（标准档）。
- 禁用清单遵守：无 scale-pop / persp-in / shatter / typewriter / scramble / gradient-flow。
- 节奏偏移 +1：封面 hero（1s 档）、收束 quote、全 deck reveal 慢阶梯——一切比默认慢半拍的显影感。
- 文本破坏性动效运行时化：chars/mask-lines 文件内均为纯文本 / .ml-line 产物结构，零拆字 span 落盘。

## 可编辑契约

- 6 页均带语义 `data-slide-id`（cover / problem / metrics / compare / sync-flow / closing）；
- 全部用户可见文字 `data-editable`（含刊头家具与 mask-lines 的 `.ml-inner` 叶子）；装饰（Ghost/vquote/墨点/hairline 容器/SVG 轴/canvas fx）一律 `data-editable-skip`；
- 零 `<img>`、零 assets 引用；grep 自检：6 个 slide-id，无外链/内嵌图。

## Step 5 · 渲染自检（硬）

工具：`tests/harness/j_render_check.py`（Playwright Chromium，视口 1920×1080 ⇒ --slide-scale=1，逐页 scrollIntoView 后等 2.6s 动效还原终态再测量，画布坐标系）。

```
PASS  p1 cover        editable=4
PASS  p2 problem      editable=11
PASS  p3 metrics      editable=15
PASS  p4 compare      editable=16
PASS  p5 sync-flow    editable=24
PASS  p6 closing      editable=8
RESULT: ALL PASS
```

- 零溢出：全部 78 个 data-editable 元素包围盒均在 1920×1080 内（容差 2px）；
- 零重叠：同页可编辑元素两两交集面积 ≤16px²；
- 字号：正文全部 ≥18px（masthead/mastfoot 15/14px 与 mono meta 15–16px 属 typography §2 meta 槽位下限 14px 的合法例外）。

骨架逐字性：`diff assets/skeleton.html 产物` 仅四处 SLOT 差异（标题 / theme tokens / theme css / slides / chrome 页码），框架层 CSS 与 JS 零改动。
