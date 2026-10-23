# 子技能 C：可编辑 PPTX 导出（原生元素轨）

> 状态：**已实现（2026-09-22，C1–C3 全落地）**——C1 文本+简单形状 / C2 图表原生+信息图+烙图兜底 / C3 字体内嵌+双轨编排+编辑器面板；验收 p_editable_check（T27）+ n_fidelity_check（T25）全绿 · 总览见 `tri-form-architecture.md`；保真轨（SVG 转曲）见 `pptx-export-svg.md`
> 依据：2026-09-22 用户意见——整页转曲 SVG 的 pptx 不可编辑、与 PDF 交付无差异；需要**可编辑 PPTX** 导出（文本框/信息图/图表全方位原生可编辑），并全方位参考 `source/ppt-master/`（v6.6.0，MIT）站在巨人肩膀上。调研结论见本文件 §2。

## 1. 定位：双轨导出

| 轨道 | 产物 | 编辑性 | 适用 |
|---|---|---|---|
| **可编辑轨（本文档，新）** | `export/deck.pptx` | 文本框/形状/图表全部原生可编辑 | 主交付：对方要接着改 |
| 保真轨（既有，M3） | `export/deck-vector.pptx` + `export/deck.pdf` | 不可编辑（转曲/整页图） | 视觉封存、打印、跨机零漂移 |

- 用户的判断成立：不可编辑的 pptx 与 PDF 等价——保真轨因此**顺带直出 PDF**（printToPDF 已有产物，落盘即可），其 pptx 形态降级为次要产物；
- 三形态架构不变：HTML 仍是唯一真相源，两条轨都是单向快照，重导即作废旧件；
- 烙入页（Step 5.6）在两轨中同为满幅图片，不变。

**诚实声明（可编辑轨的固有边界）**：可编辑 = 放弃像素级特效的保真承诺。glow/混合模式/canvas FX/复杂渐变等 CSS 视觉在 PowerPoint 原生模型里不存在等价物，这些层以整组烙图兜底（见 §3 L5）。可编辑轨的目标是**内容 100% 原生可改 + 版式几何一致**，不是特效等价。

## 2. 路线选择：渲染真相 × 契约标记

调研对比（证据见调研记录，ppt-master v6.6.0 / commit fb478a93）：

| 路线 | 代表 | 版式真相来源 | 致命伤 / 局限 |
|---|---|---|---|
| 手写 SVG → DrawingML 编译器 | ppt-master（编译器 ~5.1 万行 + 807 行封闭子集契约） | AI 手写坐标 + 字符宽估算表（CJK=1em 启发式） | 文本框多为 `wrap=none`：用户改长文本即溢出；图表要 AI 双写 SVG+JSON 防 hash 腐化；换机字体靠白名单祈祷 |
| DOM 快照 → pptxgenjs | dashi html-deck-to-pptx（闭源 minified） | getBoundingClientRect + computed style | 方向正确但逐个文本框绝对定位、无段落流；代码不可借 |
| **渲染真相 × 契约标记（本文档）** | 本项目 | **Playwright 渲染后 DOM**：真实几何 + 真实分行 + 真实计算样式 | 编译面比 ppt-master 小一个数量级（见下） |

我们独有的两张牌：

1. **渲染真相**：`extract-manifest.py` 已在渲染后 DOM 上工作——可编辑轨直接从浏览器拿每个文本叶的真实包围盒、真实逐行分行、真实计算样式（color-mix/渐变都由浏览器算成具体值），**零估算**。ppt-master 的 `font_advances.json` 只配做我们的兜底。
2. **契约标记**：`data-editable`（文本叶）/ `data-editable-skip`（装饰）/ `data-ig`（信息图族）/ 图表配方（charts.md 14 款）把"这是什么"直接写在 DOM 里——ppt-master 要 AI 手写语义标记再编译，我们的标记本来就是产物的一部分。

**从 ppt-master 借用的资产**（MIT 许可，可复制/仿写）：

- `drawingml/utils.py` 四张字体表（`EA_FONTS` / `FONT_FALLBACK_WIN` / `PPT_SAFE_FONTS` / `GENERIC_FONT_MAP`）与 `parse_font_family` 的 latin/ea 双 typeface 策略；
- `elements.py` `convert_text` 的 bodyPr 工程（lnSpc spcPts 行距、run 级样式保留、bullet 抽取）——**但其默认 `wrap=none+noAutofit` 要超越**：我们用真实框宽 + `wrap=square`，用户改字后 PowerPoint 按原宽重排而不是溢出；
- `native_objects/chart_xml.py` / `table.py` / `workbook.py` 的原生 chart/表格发射器作参照（python-pptx 自带 add_chart 覆盖基础款，复杂款参照重写）；
- `pptx_embedded_fonts.py` 的 `embeddedFontLst`+`fntdata` 嵌入机制（它只用于导入侧 roundtrip，我们用于导出侧主动嵌入）。

## 3. 元素映射规格（核心）

逐元素决策树（渲染后 DOM，画布坐标系 1920×1080，深度优先）：

| 层 | 对象 | 映射 | 可编辑性 |
|---|---|---|---|
| L1 文本叶 | `[data-editable]`（不含 .baked-source） | `p:sp txBox`：位置=渲染包围盒；**逐行真实分行**（Range 逐行 rect → `<a:br>` 或分段）；字体 latin/ea 双 typeface；字重/字号/颜色/对齐/行距/letter-spacing 从 computed style 映射；行内 `<b>/<i>/<em>` 拆 run | 全文可改，按原框重重排 |
| L2 简单几何 | 色块/圆角矩形/线条（`.rl-*`、hairline、容器底） | prstGeom（rect/roundRect/line）：fill/border/圆角从 computed style 映射（浏览器已算出具体 rgb/px） | 原生形状 |
| L3 图表 | 图表根（charts.md 配方标记） | **原生 chart XML**（内嵌 workbook，数据可改）：数据从 DOM/配方参数单源派生——柱/条/折线/面积/饼环/雷达/散点用 python-pptx `add_chart`；瀑布/斜率/热力表格等定制度高的 → L5 烙图 + 标注文字原生 | 数据与系列可编辑 |
| L4 信息图 | `data-ig` 组件 | Item 文字（label/desc/value）→ L1 文本框；结构骨架（连线/节点/容器）→ 简单者 L2 原生形状、复杂者整组烙图；分组落 `p:grpSp` 保持整体可移动 | 文字全可改，结构件尽量原生 |
| L5 复杂视觉 | canvas FX、gradient-flow 文字底、滤镜、纹理、复杂 SVG 场景 | **整组烙图**（elementScreenshot 思路：该子树单独截图为 PNG 嵌入），叠于其上的文字仍走 L1 原生 | 背景不可改、文字可改 |
| L6 烙入页/图片 | baked 页、`data-editable-image` 图片 | 满幅/定位 `p:pic` | 图片可替换 |

配套规则：

- **背景层**：页底色/暗色变体 → slide 背景或满幅 rect；质感层（grain/glow 等）→ 满幅烙图置底；
- **覆盖率指标**：每页报告 `native_text_ratio`（原生文本叶数 / 总文本叶数）与 `native_area_ratio`（原生元素面积占比）——"全方位可编辑"从口号变成数字；
- **动效**：全部静态化（与保真轨同），无动画映射；
- **分组语义**：L4 信息图与 L5 混合组用 `p:grpSp` 分组，命名带 slide_id 与角色（PowerPoint 选择窗格可读）。

## 4. 字体内嵌（可编辑轨的漂移根治）

保真轨靠转曲消灭字体依赖；可编辑轨文字是活的，必须把字体随档：

1. `subset-fonts.py`（M3 已落地）按全 deck 用字产出子集字体；导出侧扩展：子集需输出 **TTF**（pptx fntdata 不支持 woff2；fontTools 直接存 .ttf）；
2. zip 手术嵌入：`ppt/fonts/fontN.fntdata` + `presentation.xml` 的 `p:embeddedFontLst` + content-type 注册（机制参照 ppt-master `pptx_embedded_fonts.py`，我们主动写入而非 roundtrip 保留）；
3. 许可闸：嵌入前检查字体 fsType（installable/editable 才嵌；OFL 字体满足）——许可审查仍是选字责任；
4. 无 fonts/ 的存量 deck：回退 `FONT_FALLBACK_WIN` 映射表 + 导出报告声明"字体未随档，跨机版式可能漂移"（防线 B 语义延续）。

## 5. 与既有轨道的整合

- `export/` 目录约定扩展：`deck.pptx`（可编辑轨，主交付）/ `deck-vector.pptx`（保真轨）/ `deck.pdf`（保真轨直出）/ `page-NN.svg|png|diff.png`（既有，编辑器对比资产）/ `manifest.json` 增 `tracks` 字段与每轨覆盖率/保真分；
- 默认行为：`export-pptx.py` 默认两轨全出（可编辑轨失败不阻断保真轨，反之亦然，报告逐轨声明）；
- 编辑器导出面板：按轨分列载体与指标（可编辑轨显示 native 覆盖率，保真轨显示保真分）；对比视图仍以保真轨 SVG 为参照件（可编辑轨的视觉校验走 LibreOffice 参考渲染 diff，**标注非裁判**）；
- stale 闭环不变：同一 content-hash 指纹管辖两条轨。

## 6. 实现拆分

- **C1 文本与形状**：渲染快照扩展（extract 输出全样式快照）+ L1 文本框引擎 + L2 简单形状 + 字体映射四表 → 纯文本/形状页全可编辑；harness：python-pptx 重开、全部 data-editable 文本在 pptx XML 中逐字存在、几何偏移抽验；
- **C2 图表与信息图**：L3 基础五配方原生 chart + L4 文字层与 grpSp 分组 + L5 烙图兜底；harness：原生 chart 存在性与数据逐字、覆盖率阈值；
- **C3 字体内嵌与整合**：fntdata 嵌入 + 双轨编排 + 编辑器面板/协议 + 全量回归。

## 7. 验收标准

- 文本逐字：fixture deck 导出的 pptx 中，全部 `[data-editable]` 文本逐字出现于 slide XML（harness 硬校验，防幻觉三硬规则之"逐字引用"在可编辑轨的落点）；
- 可编辑性：文本框 wrap=square 且框宽=渲染宽度（±2%）；图表为原生 chart 对象且 workbook 数据与 DOM 一致；
- 几何一致：LibreOffice 参考渲染 vs HTML 截图逐页 diff（参考口径、报告展示，不作硬门禁——可编辑轨的硬门禁是文本逐字 + 覆盖率阈值）；
- 覆盖率：fixture（含图表页/信息图页/动效页/烙入页）native_text_ratio = 100%（L5 烙图页内无文字的例外逐页声明）；
- 字体内嵌：fonts/ 存在时产物含 embeddedFontLst 且 fsType 合规；缺失时报告声明；
- 单向纪律与 postflight 与保真轨同口径（只读 deck、临时文件原子落盘、重开包校验）；
- 真实 Office 365 / WPS 目检：人工验收项（本环境不可自动化，诚实标注）。

## 8. 版式一致性加固（2026-09-28 二次修订：F1–F4′ 数学认证口径）

> 第一版五层（0924，L1–L5 视觉回验）在真实 PowerPoint/WPS 复测仍见容器重叠——
> 二次诊断（/tmp/diag/REPORT.md）定位四个根因，用户拍板：重叠/边距问题用
> **数学计算认证**（写入后读结构化文件纯计算），视觉 QA 降级为参考通道。
> 修订方案见 `docs/progress/0924_editable_overlap_fix.md` §六。

| 层 | 机制 | 关键参数 |
|---|---|---|
| F1 墨水盒判定（修 R3） | 相交判定对象=墨水盒非框：墨水高 = Σ 行 lnSpc_eff（**末行只占墨迹 em 高**——OS/2 typo 口径，hhea 是行距储备不是墨迹）× 最坏行墨水宽+内边距；余量区允许伸入空白，墨水相碰才算冲突；位图豁免不变 | typo/hhea 口径分离 |
| F2 行距模型重做（修 R2） | 单行/标题：wrap=none 永不重排 + 框宽=候选集最坏实测宽 ×1.08（全角标点占比 >20% → ×1.15）；多行：lnSpc 一律 **spcPct** = max(作者行高/最坏自然行高, 1.03)——行距随字体缩放，机制免疫行内叠字；块高 = Σ 各行 spcPct×最坏自然行高重新预算；超隙修复环先 normAutofit 缩字（2% 步进，下限 90% 报 warning）再烙图 | ×1.08/×1.15、103% |
| F3 字体交付分级（修 R1） | run typeface 写**目标机必有字体**（雅黑/宋体/Consolas 系映射）；内嵌字体保留并以**映射后族名**注册（365 吃内嵌增强、WPS 可预测回退）；同一字体文件多族名共享同一 fntdata part（修孤儿件）；交付话术：WPS 用户走 deck-vector.pptx/deck.pdf | 族名=映射名 |
| F4′ 数学认证门禁（修 R4） | `certify-pptx.py`：写入后重开产物 XML 纯计算——R1 逐行墨水宽≤净宽（硬）、R2 逐块墨水高≤框高（硬）、R3 lnSpc≥候选最坏自然行高、R4 墨水盒两两不相交（文字-文字严格/背景形状 z 序在下豁免/位图豁免）+ 容器净距 ≥4px；导出器集成"组装→认证→修复环→重认证→页级降级→终认证全过才落盘"，**认证全过是出厂条件【硬规则】**；LO 回验降级为参考通道 | 秒级（54 页 <1s） |

**候选字体集度量**（`pptx_text_metrics.py`）：声明族名**分轨**（run 只以其声明的
typeface 或匹配内嵌件渲染——全局最坏会把 Noto Mono 1.17 的高墨迹误摊给正文轨，
cmb 实测假碰撞）+ 逐字按 CJK/拉丁分流（CJK 走 ea 轨）；度量源优先级：内嵌文件 >
fc-match 本机文件（标注替换近似）> ppt-master font_advances.json（MIT，仅拉丁族）>
保守上界（CJK/全角 1.0em、拉丁 0.65em）。

**净距规则与文本不烙图政策（0928 四次诊断）**：certify R4 族补 R4c——文字墨水盒
与下层形状**部分相交（骑缝/压边线）即违规**（此前只查完全包含的四边净距，修复环
shift-down 把文本挪到卡片缝上形成系统性盲区，p35 实锤）；修复环对骑缝直接计算
收进卡内/挪出卡外的最小合法位移。**政策硬规则：纯文本块永不烙图**——修复阶梯终端
是页级降级矢量件（文本烙图曾 19 处越界）；烙图仅限装饰/复杂视觉层。

**混排间距项（0928 三次诊断提出，0929 受控实验校正）**：OOXML 排版引擎在
CJK↔拉丁/数字边界自动加间距——宽度模型必须计入，否则高密度混排 deck 换行点
系统性早于模型，行数低估 → 块底下溢（p35/p36 实锤）。**0929 校正**：0928 的
≈1.04em/边界系单行反推（未分解多边界），受控实验（构造已知宽度 pptx 经 LO 出
PDF、pdftotext -bbox 逐词坐标，证据 `tests/harness/results/diag-c5/spacing/`）实测
**0.237em/边界**（取 `MIXED_BOUNDARY_EM=0.25`，与 Word/PPT 文献 1/4em 吻合；
单/双 typeface 无差异、空格相邻对不计）；同批实验证明真实引擎按 advance 精确换行
（压实密度 99.4%+），0928 的 R2 容量折扣 0.97 是边界项缺失时代的补偿，模型校正后
退役——est 行数统一走 `greedy_wrap_lines`（贪心换行：CJK 逐字可断/拉丁词界/长词
硬断/边界 0.25em，certify 与 apply_layout 与 check-capacity 三处同函数）。

**逻辑段 a:p（0929 五处诊断）**：逐渲染行 a:p 会把 Chromium 的紧凑断行（无混排
间距）锁死为 PPT 段落边界——每段独立重断行、短尾行堆叠，行数系统性虚增
（cmb-retail 预认证幻行主因之一）。改为**逻辑段**（`<br>` 硬换行分段，快照
leafLines 逐字聚类时记 hard 标记），段内软换行交还 PPT wrap=square 贪心重排——
与 PPT 段落语义一致、与用户编辑后的重排行为一致。同批落地两闸同数学：
certify 抽取 `certify_elements`（XML 路径与快照路径同一实现），export 新增
`slide_elements_from_snap`（与 build_pptx 发射同构），check-capacity 层 B 直跑
同一认证函数——生成侧过闸 ⇒ 导出第一轮认证净（cmb-retail 实证：
预认证 144 项与 certify 第一轮 143/143 逐元素一致；修正后导出
certify rounds=1 fixes=0、degraded_pages=0、native_text_ratio=1.0）。

**连带修复（快照正确性）**：行聚类从"按 top"改为"纵向区间相交"——同行混排小字
（<em> 0.4em）共享基线但 top/bottom 皆异，top 聚类撕成伪行、bottom 聚类错序
（'km1128' 倒序事故）；区间相交 + 行内按 left 视觉序重排，两全。
