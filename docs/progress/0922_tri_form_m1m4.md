# 0922 · 三形态翻转 M1–M4 实施 + 真实烙入生图 + 可编辑 PPTX 设计

> 2026-09-22 · 承接 `docs/design/handover-tri-form.md`（M1–M4 规划）→ 全部落地；同日新增 `docs/design/pptx-export-editable.md`（子技能 C，评审通过进入实施）。

## M1 公共地基：extract-manifest + content-hash

- `scripts/extract-manifest.py`（python+Playwright，渲染后提取：role 推导 furniture→annotation→title/body、逐字 content、line_count/advance_width 快照、canonical string = slide_id+render_mode+T:/I: 行，SHA-256 前 12 hex；`--write-hashes` 属性级精准写回，23 个 fixture deck 已写入）；
- editor.html v2.6：保存时 Web Crypto 重算页级 hash，canonical JS 与 extractor 逐字一致（脚本 diff 证实 byte-identical）；
- harness `l_hash_check.py`（T23，7 项）：幂等 / 编辑翻转（恰好该页翻）/ 双端一致（编辑器保存产物 == extractor 重算，14/14 页）。

## M2 整页烙入（契约 v7 / skeleton v7.3）

- 契约 v7：data-render-mode / .baked-source 源层五条规约 / 页面级槽位 page-baked-16x9 / 批注粒度页级+坐标；
- skeleton v7.3：`liveEls()` 过滤器 7 处排除源层（拆字/动效/in-view/scroll 驱动/fx/ptr），存量 deck 零影响；
- SKILL.md Step 5.6 + `compile-bake-prompts.py` 七节模板（Text 段逐字，harness 校验精确子串）；check-images 页面级槽位扩展；editor v2.7 扫描跳过源层；
- fixture `tests/decks/bake-mix/` + harness `m_bake_check.py`（T24，41 项断言）。

## M3 HTML→PPTX 导出（保真轨）

- spike 先行（`tests/harness/results/spike-m3/REPORT.md`，gitignored 可复跑）：pdftocairo 逐页 `-f N -l N` 实测零 `<text>` 全转曲；三个坑固化——@page+scale=2/3 换算、gradient-flow 还原本色注入（p14 diff 17.1%→1.16%）、python-pptx 漏 svg content-type 需 zip 手术；
- `scripts/export-pptx.py`：防线 C 双门禁（j_render_check + 漂移对比 >3% 阻断）→ printToPDF → 转曲 SVG → svgBlip+PNG 双写 → postflight 原子落盘 → 保真分 + diff 热区 → export/manifest.json；烙入页直通；降级链；单向纪律 sha256 比对；
- 防线 A 最小落地：`subset-fonts.py` + skeleton v7.4 SLOT: fonts + uncovered_glyphs 检测；防线 B metric_fallback 试点 b1/a1/c1；防线 D 进 typography §6.5；
- 实测 bake-mix 44s、保真 avg diff 0.27%；harness `n_fidelity_check.py`（T25，23 项：postflight/阈值/stale/降级/门禁演练）。

## M4 编辑器 v3.0 三态工作台

- 顶栏三态分段（编辑/对比/导出）+ 翻面手势（F 键双面卡，背面三态：就绪 SVG/过期水印/黑面诚实空态）+ 对比三视图（并排默认/滑动分割/差异热区）+ stale 闭环 + 烙入页源层编辑 + export/ 三通道读取（HTTP/?deck=、嵌入 exportManifest·exportBaseUrl、file:// 降级）+ postMessage `export-intent`；
- 计划外修复：常驻 preserve-3d 改变 iframe 栅格化路径致 T4 回归 → 3D 上下文按需启用；
- harness `o_tri_view_check.py`（T26，35 项）。

## 同日：真实烙入生图 + bake-prompts 参考

- oai生图（ThinkSkillHub，GPT-Image-2.5）真实执行 Step 5.6：封面截图为风格锚 i2i，bake-mix ch-baked 页换成真图（2048×1152），回归全过；
- 用户意见"生图优化是手艺不是脚本"→ `references/bake-prompts.md`：六构图谱系 Layout 指令策略 + 文字量纪律 + 失败模式对策；SKILL.md 分工口径硬规则（脚本管防幻觉骨架、agent 管 Layout/风格段写法）；
- harness 修复：n_fidelity/o_tri_view 拷贝 fixture 排除 export//prompts/（残留产物导致预备导出被拒绝）；
- **全量回归 51 项 51 PASS 0 FAIL**（T23–T26 子进程全绿）。

## 可编辑 PPTX（子技能 C）设计与评审

- 用户意见：SVG 轨不可编辑≈PDF → 双轨导出（deck.pptx 可编辑轨主交付 / deck-vector.pptx + deck.pdf 保真轨）；
- ppt-master v6.6.0 深研：编译器 ~5.1 万行、文本框 wrap=none 改字即溢出、图表双写 hash 腐化、字体靠白名单；可借资产=字体映射四表/bodyPr 工程/chart_xml 参照/embeddedFontLst 机制（MIT）；
- 我们的路线=**渲染真相 × 契约标记**：真实分行文本框 wrap=square、原生 chart XML（DOM 单源派生数据）、信息图 grpSp、复杂视觉烙图兜底、字体内嵌根治漂移；
- 设计文档 `docs/design/pptx-export-editable.md` 评审通过，C1（文本+形状）→C2（图表+信息图）→C3（字体内嵌+双轨整合）**当日全部落地**：
  - C1：export-pptx-editable.py——渲染快照（真实逐行分行零估算）→ 原生文本框（wrap=square + 真实框宽，超越 ppt-master 的 wrap=none 改字即溢出）+ 简单形状 prstGeom + latin/ea 双 typeface（pptx_font_maps.py，MIT 抽取 ppt-master 四表）；T27 挂回归；
  - C2：图表双源校验（文本×几何比值不变量容差 5%，不过即烙图——宁烙图不错映射）→ 基础五配方原生 chart XML（workbook 数据逐字、轴/图例删除防双写）；data-ig → grpSp 分组；复杂视觉 elementScreenshot 烙图、文字仍原生叠加；
  - C3：字体内嵌（fsType 许可闸 + embeddedFontLst zip 手术，不伪造）、双轨编排（deck.pptx=可编辑主交付 / deck-vector.pptx / deck.pdf；基础设施失败单轨隔离、防线 C 门禁双轨同撤；manifest export.tracks）、编辑器导出面板双轨适配（旧 schema 向后兼容）；
  - 验收：p_editable_check 73 项（5 fixture deck：文本逐字缺失 0、几何 ≤2%、原生 chart workbook 逐字、字体内嵌、双轨三件套）+ n_fidelity 26 项 + **全量回归 52 项 52 PASS**。

## 遗留

- 真实 Office 365 / WPS 目检：人工验收项（两轨共用）；
- OFL 字体迁移 20 主题：独立批次（防线 A 能力已就位）；
- 既有问题未修：tech-ikb-v3 的 22 处 16px 小字（老 deck 口径）、f1_texture_check.py 游离脚本过时。

## 09-24：cmb-retail 真实还原基准 deck 建成

- `tests/decks/cmb-retail/`：54 页招商银行×天弘基金高拜材料从 source-content.md（pptx 解析包）1:1 高密度还原——主题 B1 瑞士国际主义基底 IKB 蓝（金融机构商务风，只选不改），脚手架（封面/目录/章节页范例 + 页计划表 page-plan.md）→ 7 片段分包施工 → 整合终验；
- 终验：j_render_check 54 页全 PASS（合并后修掉 p33/p35 masthead 与标题 1px 级叠压——页眉 68px logo 推高家具底线至 113px，标题 margin-top 16→26px）；check-images 零错误（~80 槽位三方绑定全过）；k_nav_check 五章三通道全过；extract-manifest --write-hashes 写入 54 页 content-hash；
- 文本逐字总审计（一次性脚本 /tmp/text_audit.py，源侧逐页 × HTML data-editable 叶子，去空白子串口径）：修复真缺失——p21 十个 kv 标签丢全角冒号、p20 两个板块标注、p25 图题、p27 漏配履历（贺雨轩卡重复沙川履历，换入漏配的嘉实基金履历——z-order 归属不可考，记偏差）、p42 体系口号、p45 章节题「计划/规划」逐字分保；残余"缺失"全部为图表源数据表工件（类别/系列1/列2 等提取残留列头与原始小数列），非幻灯片可见文本；
- 图表数值直标补全：p5 折线中间 6 点、p34 柱图中间 6 柱（原仅首尾直标）；
- 接入回归：run_e2e DECKS 加入 cmb-retail（T1 往返幂等覆盖 54 页真实 deck）；可编辑轨首次实战冒烟 `export-pptx.py --track editable`（读数见当次汇报）。
