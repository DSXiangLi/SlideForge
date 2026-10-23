# 子技能 B：HTML→PPTX 导出（SVG 矢量管线）

> **角色修订（2026-09-22，C3 起）**：本管线为**保真轨**——产物定名 `export/deck-vector.pptx`（原 deck.pptx 改名）并顺带直出 `export/deck.pdf`（printToPDF 落盘）；`export/deck.pptx` 改指可编辑轨（主交付，见 `pptx-export-editable.md`）。管线逻辑零行为变更，由 export-pptx.py 双轨编排（--track both|editable|vector）。

> 状态：待评审 · 2026-09-21 · 总览与公共地基见 `tri-form-architecture.md`
> 依据：2026-09-21 用户意见——以 SVG 为中间层、尽可能保留视觉效果；调研 `source/ppt-master/`（AI 手写 SVG + 自研 SVG→DrawingML 编译器路线）后确认不走编译器路线。

## 1. 路线选择：浏览器即编译器

三条候选路线的证据对比：

| 路线 | 代表 | 致命伤 |
|---|---|---|
| 整页截图贴入 | 各类 html2pptx 工具 | 位图、不可缩放、无矢量逃生舱 |
| AI 手写 SVG → DrawingML 编译器 | ppt-master（编译器约 4.7 万行） | 手写字符宽度启发表（CJK=1em…）永远不准；字体不内嵌，换机跑字；校验门体系臃肿 |
| 原生形状重排（文本框映射） | Slidev pptx-editable | 保真天花板低，已有实证 |

**我们的路线：排版由浏览器完成，SVG 只是渲染结果的矢量转录。**

```
index.html
  │ ① __pptxMotion.freeze()（契约 v6 既有接口，动效压回静态终态）
  │ ② headless Chromium printToPDF：页尺寸锁定 13.333″×7.5″，每页恰好一页
  ▼
矢量 PDF（字体子集已内嵌于 PDF）
  │ ③ mutool draw -F svg / pdftocairo -svg：逐页转出，文字转曲为矢量路径
  ▼
export/page-NN.svg（+ page-NN.png 位图副本）
  │ ④ python-pptx 组装：每页满幅图片，a:blip 双写 svgBlip 扩展 + PNG fallback
  ▼
export/deck.pptx
```

三个关键性质：

1. **布局零重算**：不存在"重新实现排版"的环节，Chromium 的渲染结果就是版式真相；skeleton 固定 1920×1080 画布 + 禁响应式重排的既有约束，使"打印成单页 PDF"成为完全确定的操作；
2. **消费端字体零依赖**：文字在 ③ 转曲为路径，目标机器不装主题字体也 100% 保真（ppt-master 做不到这一点，它只能警告"字体需自行安装"）；
3. **可编辑性逃生舱**：Office 2016+/365 原生支持 SVG 图片，且提供"转换为形状"——用户在 PowerPoint 里可打散为原生矢量形状手动微调。PNG fallback 写进同一 `a:blip` 扩展结构，老版本 Office 自动降级。

**诚实声明**：这不是"前无古人"的方案——printToPDF、pdf2svg、svgBlip 每一步都是成熟技术。差异化在于组合后的工程闭环：字体随档（§4 防线 A）消灭生产端环境变量、渲染门禁（防线 C）保证烙入的版式必是合格版式、SVG 中间产物同时充当编辑器对比视图与保真回归的资产（`editor-tri-view.md`）。

## 2. 管线细则

- **① freeze**：导出前调用骨架 `__pptxMotion.freeze()`；canvas FX 页在 PDF 中天然落成位图，无需特判；
- **② printToPDF**：分页依托骨架既有红线"打印时每页输出为独立一页"（`@page` + 分页规则已在框架层），导出只做 `preferCSSPageSize`、关闭页眉页脚、开启背景图形；验证每页 PDF 恰为 13.333″×7.5″ 单页；
- **M3 前置 spike【硬规则】**：正式落码前先跑通最小链路验证——单页 deck → printToPDF → 逐家转换器出 SVG → **确认文字以路径而非 `<text>` 元素输出**（mutool / pdftocairo / Inkscape 的 text-as-path 行为不一，必须在 spike 中实测选定并固化参数）→ svgBlip 双写 → 真实 Office 365 与 WPS 打开目检。spike 不过则管线设计回填修订，不允许带着未验证假设进入批量实现；
- **烙入页直通**：`data-render-mode="baked"` 页跳过 ②③，`assets/` 中 PNG 直接满幅嵌入 pptx——两个子技能在管线尾部汇合；
- **③ pdf→svg**：转换器探测顺序 mutool → pdftocairo → Inkscape CLI；产出 SVG 后做 sanity check（viewBox 比例 16:9、非空、无外部引用）；
- **④ 组装**：python-pptx 建 13.333″×7.5″ 演示文稿；每页插入 PNG（python-pptx 原生路径），再补丁 XML 追加 `svgBlip` 扩展（`{96DAC541-7B7A-43D3-8B79-37D633B846F1}`）指向 SVG；烙入页 PNG 即是终态无需补丁；
- **降级链【硬规则】**：SVG 转换器全部不可用 → 高分辨率 PNG（3840×2160 截图）单独成页；截图设施也不可用 → 诚实报错，不产出半成品。降级页逐页列入导出报告；
- **产物**：`export/page-NN.svg` / `page-NN.png` / `deck.pptx` / `manifest.json`（含每页导出方式 svg/png/baked、保真分、导出时 hash）。

## 3. 单向边界与 Office 兼容矩阵

- PPTX 是**交付快照，永不回读**：用户在 PowerPoint 中的修改不回流 HTML；再导出 = 重新翻转，旧 pptx 作废；
- 动效全部静态化（freeze 终态）；视频/交互不在范围内；
- 兼容矩阵：Office 2016+/365 显示 SVG（清晰、可"转换为形状"）；更老版本及 WPS 走 PNG fallback；导出报告声明每页实际生效的载体。

## 4. 字体与布局稳定性（核心章节）

### 4.1 问题陈述

转曲消灭了**消费端**字体依赖，但**生产端**布局仍发生在转换机的浏览器里：本机缺主题字体 → 回退字体度量不同 → 换行位置改变 → 容器内文字溢出/重叠 → **PDF 忠实地把坏布局烙成矢量**。管线保真度越高，烙入坏版式越忠实。这是截图/转录类路线的共命门，必须把"布局正确性"从环境运气变成工程闭环。

### 4.2 防线 A：字体随 deck 走【根治，默认开启】

消灭环境变量的唯一办法是不留环境变量：

- 产物形态修订为 `index.html` + `assets/` + **`fonts/`**；主题库 G2 字体栈收敛到 OFL 等可再分发许可的开源字体（Noto/思源系等），许可审查入主题入库门槛；
- **字面子集化**：`pyftsubset` 按 manifest 提取的全 deck 实际用字裁剪字体 → woff2（中文裁到实际用字通常几百 KB）；翻字（编辑新增字符）后子集可能缺新字形——**字形覆盖检测**随 manifest 输出 `uncovered_glyphs`（deck 用字集 vs fonts/ 子集覆盖集的差集），非空即标记 fonts stale，编辑器导出面板展示，重跑子集化 pass 闭合（技能侧动作）；
- skeleton 增加 fonts SLOT（`@font-face` 块，框架层约定位置），产物仍零网络依赖（woff2 是本地文件）；
- 收益不限于导出：所有用户浏览器、编辑器 iframe、转换机渲染同一份字体文件——**布局从"环境相关"变成"文件的纯函数"**，HTML 形态自身的跨机一致性也一并解决。

### 4.3 防线 B：度量兼容回退栈【缓释】

themes.md G2 扩展必填字段 `metric_fallback`：每个主题字体声明度量兼容回退（如 Arial↔Liberation Sans、苹方→Noto Sans SC 近似）。fonts/ 缺失的存量 deck 渲染时退到此栈，度量漂移有界（缓释，非消灭）。

### 4.4 防线 C：导出渲染门禁【硬规则】

导出管线**在转换机上、用即将烙入的那次渲染**做门禁，不过门禁不产出 PDF：

1. 重跑 Step 5 渲染校验（零溢出/零重叠/字号档）——与生成时同一套 `check-render.py` 口径；
2. **排版漂移对比**：manifest 记录生成时逐文本叶的 `line_count` 与 `advance_width` 快照；导出时同机重测，任一叶行数变化或宽度漂移 >3% 即判定字体替换已改变排版；
3. 失败 = blocker：逐页逐元素列出（哪页哪段文字、快照值 vs 实测值），修复路径明确（装字体 / 跑防线 A 子集化 / 调容器），**绝不烙入坏布局**。

### 4.5 防线 D：容器余量纪律【韧性】

文本容器设计预留排版余量（内容高度 ≤ 容器 85%、行高 slack），微小度量差不破版——生成侧纪律，写进 typography.md 修订。

### 4.6 小结

A 消灭变量、B 有界缓释、C 测量兜底、D 结构韧性。任何"不绑字体却声称跨机版式一致"的方案都在隐瞒问题（ppt-master 的 CJK=1em 估算器正是这个失败模式）；我们的答案：**不估算——绑字体、量真实渲染、不过门禁不导出**。

## 5. postflight 与保真回归

- 重开包校验：ZIP/OPC 完整性、页数 = deck 页数、每页载体与导出报告一致；先写临时文件，全过才覆盖主产物；
- **保真分的权威口径**：`HTML 页截图（freeze 后） vs export/page-NN.png 的像素 diff`——page-NN.png 由最终 SVG 光栅化产出，与 PPTX 内嵌件同一份矢量源，测量的是"转录链损耗"，链路内无第三方渲染器。**不用 LibreOffice 当保真裁判**：它对 svgBlip 的渲染缺陷会测出 LibreOffice 的错而非本管线的错；LibreOffice/真实 Office 打开仅作人工抽检渠道；
- 差异热区资产：diff 的同时产出 `export/page-NN.diff.png`（差异热力图），编辑器 v3 热区视图直接消费（编辑器自身无栅格化能力，见 `editor-tri-view.md` §4）；
- 导出报告：每页导出方式（svg/png-fallback/baked）、保真分、降级原因；不给"100% 可编辑 pptx"的承诺。

## 6. 验收标准

- 端到端：fixture deck（含图表页/信息图页/烙入页/动效页）导出 pptx，Office 365 与 WPS 打开验证：版式零位移、文字清晰（矢量）、老载体走 PNG；
- 门禁演练：卸载主题字体的转换机上导出，防线 C 必须阻断并给出逐元素报告；跑了防线 A 子集化后同机导出必须通过；
- 降级演练：屏蔽 svg 转换器 → PNG fallback 生效且报告列明；屏蔽截图设施 → 非零退出、无半成品；
- 保真回归：harness `m_fidelity_check.py` 阈值卡死（如全 deck 平均 diff < 2%，单页 < 5%），指纹过期（hash 翻转后未重导）的 export/ 被检出；
- 单向纪律：导出过程对 index.html 只读（前后字节一致）。
