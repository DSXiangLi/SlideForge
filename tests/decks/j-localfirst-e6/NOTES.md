# j-localfirst-e6 · 交付说明（不进产物）

J 期终验 3/3：同一内容（本地优先软件「数据回家」）× 主题 **E6 Memphis 孟菲斯（基底糖果粉配色）**。
密度 = 低密度（演讲主导）；动效档 = 标准（L1–L4 各一）；纯 HTML 模式（零图片、零 assets）。

## 主题冻结（Step 2）

- 重主题：E6 Memphis 孟菲斯；变体：基底（糖果粉 `--accent:#FF3DA5`），无变体覆盖。
- SLOT: theme tokens = G1 六色 + G2 字体栈 + G3 质感三 token（flat / none / cover，flat 即质感立场）。
- SLOT: theme css = G9 母题块**逐字**复制（已脚本比对 themes.md 原文，一致），含缓动签名 `:root{--ease-out:cubic-bezier(.5,1.7,.4,1)}`。

## 页计划表（Step 1）

| 页 | 叙事角色 | 一句话 | 内容清单 | 明/暗 | 呈现发散（关键页） |
|---|---|---|---|---|---|
| 1 cover | 开场仪式 | 数据回家 | 标题 4 字 + 副题 13 字 + kicker | 明（cover-page） | 普通页豁免（巨字宣言 + 彩纸屑撒布 + accent 错位色块，满屏 accent 特权） |
| 2 problem | 问题 | 数据被锁在云端 | 主标题 7 字 + 2 条论点（各 ~40 字） | 明 | 普通页豁免（巨字宣言谱系 + 之字线 + 3px 粗描边顶线分区） |
| 3 numbers | 数据英雄 | 代价可以量化 | 3 个关键数字 + 各 1 句注 | 明 | **关键页，见下** |
| 4 compare | 对比论证 | 本地优先 vs 云优先 | 4 个维度 × 2 侧 | 明（右半 paper-tint 色场） | **关键页，见下** |
| 5 pipeline | 机制解释 | 同步引擎工作流 | 6 个环节 + 1 句收束 | 明 | **关键页，见下** |
| 6 manifesto | 收束宣言 | 你的数据，你的设备，你的规则 | 宣言 3 行 + 3 条行动 | 明（cover-page） | 普通页豁免（mask-lines 逐行宣言 + 彩纸屑同构图呼应封面 = 首尾闭环） |

明暗节奏的【默认】（避免连续 3 页同亮色）被主题立场推翻：E6 是"纯白底丝网平涂"世界，主题词汇中没有暗色页；亮度的呼吸改由 paper / paper-tint 色场与 accent 特权页承担。理由记录于此。

## 呈现发散三案与选定理由

### P3 数据英雄页（73% / 7 天 / 0）

- 案 A（尺度轴）**巨字直排**：三个数字 ≥180px 直排，字号即冲击，无动效。最克制，亲和 editorial/dramatic。
- 案 B（动静轴）**印戳 + count-up**：数字像盖章一样 scale-pop 落位，数值滚动计数后精确还原文本。亲和 playful/dramatic。
- 案 C（维度轴）**刻度盘/仪表**：ring 环形进度承载 73%，另两个数字另排。亲和 professional/techy。

**选定 B**。理由：①主题 G5 锚点偏好钦定 scale-pop 为本命、气质 playful，印戳隐喻与"结果已定"的论断语义同构；②案 C 被 motifs.md 禁忌否决——「7 天」「0」不是百分比语义，硬套仪表是视觉谎言；③案 A 最强硬但放弃了本主题的动效签名，且三连巨字与 P6 宣言页的巨字构图雷同。执行：count-up 只用于 73% 与 7 天（L3），「0」静态（0 滚动无意义）；三块数字衬 accent 明度阶梯色块（accent / 30% / 55% 派生，多彩纪律），单焦点 = 73%。

### P4 对比页（本地优先 vs 云优先，4 维度）

- 案 A（维度轴）**裂屏对开**：两半色场对撞，中间一道缝。裂屏对开谱系。
- 案 B（隐喻轴）**拔河**：一根绳双向拉力，中点偏移示优势。亲和 playful。
- 案 C（材质轴）**前后对照**：before/after，左灰阶右全彩。

**选定 A**。理由：①二元对比恰好两项、两侧信息量均衡（各 4 条），正合裂屏对开的合法区间；②案 B 只装得下一个总结论，4 个维度清单无处安放，且"谁赢"的偏移量在每条维度上方向相同，绳子表达不出逐维对照；③案 C 是"改造前后"叙事，内容不是时间性改造而是平行对立。执行：右半 paper-tint 色场 vs 左半 paper，中缝 = 主题签名**之字波浪线旋转 90°**（每页至多一条的配额用在缝上），维度标签做成跨缝的墨黑描边药丸章（压住之字线，避免线穿文字），本地侧每行 accent 圆点 marker 单焦点强调。

### P5 流程页（本地写入 → … → 全设备一致，6 环节）

- 案 A（隐喻轴）**管道**：一条粗管贯穿，环节是管上的节点/阀门。亲和 techy/professional。
- 案 B（隐喻轴）**行程单/车票**：一段旅程一张票，站名 = 环节。亲和 playful/editorial。
- 案 C（结构轴）**轴与节点默认链**：横向节点 + 箭头连接。默认解。

**选定 A**。理由：①同步引擎是严格串行的数据通路，"数据在管中流动"与内容关系忠实同构，flow-dot 沿线粒子（link 族）把"同步"做成了可见的流动；②案 B 的票根槽位（时刻/检票口）对应不到真实环节，隐喻会漏气；③案 C 箭头链是反例纪律点名的默认解，且 6 站箭头在 Memphis 粗描边世界里发碎。执行：管道 = SVG 双线（ink 粗描边外管 + paper-tint 内芯），入场 draw-line 描出（L3），6 张签名容器 `.mt-mem-card`（3px 墨描边 + accent 硬偏移投影）骑在管上 scale-pop 齐蹦（G5 锚点），两枚 flow-dot 沿管循环（`--flow-path` 与可见管同路径）。

## 主题表达力落位

- **G9 母题**：每页 ≥1 件——彩纸屑碎形 6 页全铺（封面/收束各 5 件同构图首尾闭环，内容页各 3 件，配额 3–5 遵守；颜色在 accent / accent 55% 明度阶梯 / ink 间轮换）；之字线 4 页各 1 条（封面装饰、问题页分隔、对比页竖缝、收束页分隔，未进数据图表区）；`.mt-mem-card` 仅流程页 6 张（全 deck 卡片阵只此一处，网格矩阵亲和）。母题件全部 `data-editable-skip`。
- **G5 动效签名**：scale-pop 用于彩纸屑与卡片（本命锚点）；rise-in 用于其余元素；chars 拆字（封面标题，L2）、mask-lines 逐行遮罩（收束宣言，L2）、count-up ×2 与 draw-line ×1（L3）、amb-drift 彩纸屑漂浮（L4）；缓动签名经主题 CSS 槽位覆盖 `--ease-out:cubic-bezier(.5,1.7,.4,1)` 全 deck 生效。禁用遵守：无 typewriter/scramble；fx 许可全禁 → 无 canvas。偏差记录：G5 节奏偏移要求阶梯步长 ≤60ms，骨架 `[data-anim]` 阶梯烧死 75ms，框架层不可改，以缓动签名 + 快时长档（未使用 hero/quote 慢配方）落实"快而弹"的节奏意图。
- **G4 容器**：粗描边圆角卡 + accent 硬偏移投影（仅 `.mt-mem-card` 与封面/收束 accent 色块）；无弥散阴影、无 hairline（分隔一律 3px 墨线或之字线）。
- **G1 预算**：内容页 accent 仅数字衬块（单焦点 73% 满色，余为 30%/55% 派生）+ 彩纸屑 ≤3 件 + 圆点 marker，估算 <5%；满屏特权用于封面与收束的 accent 色块。
- **G2 字排**：极粗标题立场（≥77px→800，35–76px→700，正文 400，小字 500–600）；低密度对比档 = 主标题 144px : 正文 18px = 8:1；中文无 letter-spacing（家具中文 `letter-spacing:0` 归零）。

## 可编辑契约

- 每页 `data-slide-id`：cover / problem / numbers / compare / pipeline / manifesto。
- 用户可见文字全部 `data-editable`（79 处）；装饰全部 `data-editable-skip`（23 处，含彩纸屑/之字线/色块/管道 SVG/flow-dot）；零图片（纯 HTML 模式，无 assets）。
- 拆字类动效文件中为纯文本（chars/mask-lines 均运行时化，无 .sp-unit 静态残留）；mask-lines 的 .ml-line>.ml-inner 结构为产物内容，.ml-inner 是可编辑叶子。

## 自检结果（Playwright，1920×1080 视口，逐页滚入等动效完成后测量）

脚本：`tests/harness/j_e6_check.py`（复跑：`python3 tests/harness/j_e6_check.py`；截图在 `tests/harness/results/j-e6-p1..6.png`）。

- **零溢出**：6/6 页 `scrollWidth/scrollHeight` = 1920×1080，不越画布。
- **零重叠**：同页全部 `[data-editable]` 两两求交，>16px² 的重叠 0 处。
- **正文 ≥18px**：非 meta 可编辑文字最小 18px；<18px 的仅 masthead/mastfoot 家具（15/14px，框架层烧死的 meta 档）与对比页维度标签、流程页 STEP 标签（16px，typography §2 小字档下限内）。
- 附带回放核验：骨架框架层 CSS/JS 与 skeleton v6 逐字一致；G9 主题 CSS 块与 themes.md 逐字一致。

## 演示与编辑

1. 演示：浏览器直接打开 `index.html`，滚动或方向键翻页（1 / 6）。
2. 编辑：用项目根 `editor.html` 打开本文件，文字点击就地改，保存走 FSAA 或伴随服务。
3. 本 deck 无图片槽位；如后续加图，放 `assets/` 并补齐槽位三属性（契约 v5）。
