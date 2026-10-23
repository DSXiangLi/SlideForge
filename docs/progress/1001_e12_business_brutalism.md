# 1001 · E12 商务粗野入库 + cmb-retail-v3 + theme-sampler

## 概要

- **cmb-retail-v3**（tests/decks/cmb-retail-v3/）：cmb-retail 的第三个设计版——商务粗野（Business Neo-Brutalism，完整粗野的商务驯化版）。内容诚信红线：与 v2 逐字 1:1、同 54 页同页序同图片素材（manifest 双端提取比对 0 差异）。两轮施工：
  - 轮一（主题改造）：token 换奶油纸+策展五色、五色章节色相系统（每页 data-hue=c0..c5，页内 var(--accent) 派生随章换色：朱红/钴蓝/松绿/明黄/青碧）、字重立场反转（标题/大数字 200/300→800）、7 仪式页重构（封面封底奶油底+五色方块列+描边照片卡+爆炸星；五章节页满版各色相）、母题换 .mt-nb-* 七件。
  - 轮二（正文页丰富化，用户反馈"过度克制"）：列表墨点→章节色描边方块（195 处）、hairline→2px 实墨结构线（327 处）、标题加章节色块引子（42 页）、正文图片描边卡化（21 张）、paper-tint 容器全描边（194 处）。
- **E12 商务粗野入库**：themes.md 第 21 套主题（focus G1+G4，与 E6 孟菲斯 4 层分化：L1 策展五色板/L4 母题/L5 直角+墨影/L6 去弹跳；4 变体=钴蓝/松绿/明黄/青碧），sync-themes EXPECTED_COUNT 20→21 校验全过并同步 editor.html 面板；画廊第 21 张样张 theme-e12（p45，样张组文案同步"二十一个世界"，页码顺延至 53 页）；设计文档 docs/design/theme-e12-neobrutalism.md（经设计文档审核技能评审后修订：补验收标准/v3 不回迁声明/变体数理由/G7 注记）。
- **theme-sampler**（tests/decks/theme-sampler/）：21 主题差异样张——cmb-retail 中等密度业务页（万亿规模 值得托付）同一逐字内容 × 21 主题，逐主题重排布局（明暗交替、构图无一重复），用于主题库差异度目检。骨架=v3 框架层 + 画廊母题 CSS 合入区（sampler 豁免），:root 主主题 B1。
- **可编辑轨导出**：cmb-retail-v3 两轮融资导出 deck.pptx——native_text_ratio=1.0、页级降级 0、certify 出厂认证全过、字体内嵌无跳过；烙图仅 7 处（4 图表双源校验失败兜底 + 3 非图表 SVG），uncovered 15 处全部为刻意出血装饰件。

## 门禁记录

- cmb-retail-v3：j_render 54/54 PASS、check-capacity 0 违规、check-images 零警告、k_nav PASS、内容 0 diff、页级 hash 全量写回。
- 画廊：T18 PASS（53 页）；k_brief_check ALL PASS（主题卡计数断言 20→21/40→42 同步）。
- theme-sampler：j_render 21/21 ALL PASS。
- 修复的坑：① .mt-nb-block-ink 初版漏 position:absolute 掉文档流压刊头（容量门禁抓获）；② section 级 --font-body 不继承（C3 等宽/C4 衬线/D3 楷体不落地，sampler 21 页统一补 font-family:var(--font-body)）；③ 容器描边化把 paper-tint 卡注册为形状后暴露 3 处真实几何紧度（coop-overview 脚注入卡/service-philosophy 墨黑列净距/mixed-asset-team 表格卡压页脚）；④ 柱图卡"散高数字被行簇模型叠算"型垂直超限（PPT 度量口径 vs CSS 渲染差异，padding 收敛解决）。
- 环境注记：工作区多个 fixture deck（tech-ikb 等）与 components-gallery 符号链接在本 session 期间被并行工作删除/重构（commit d60a48d"测试 deck 重构中"收录）；components-gallery 符号链接已按 git 登记恢复以跑通 T18。run_e2e 全量在本机因此不可跑，受影响面已单独回归。

## 交接

- cmb-retail-v3 保留 deck 级 data-hue 五色轮转扩展不回迁（设计文档 §4）；E12 是单 accent + 变体的库内蒸馏。
- theme-sampler 是主题差异度评估资产：若哪对主题目检太像（重点 E6↔E12、A1↔C4、E4↔E5），即为下一轮主题分化迭代点。
- export/ 产物按 .gitignore 不入库（export-pptx.py 重跑可得）。
