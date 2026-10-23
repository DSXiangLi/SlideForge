# 三形态翻转验收文档（tri-form）

> 对应模块：`skills/html-pptx/scripts/extract-manifest.py / compile-bake-prompts.py / export-pptx.py / subset-fonts.py`、`editor.html` v3.0（三态工作台） · 设计文档 `docs/design/tri-form-architecture.md` 系列 · 自动化 harness `tests/harness/run_e2e.py` T23–T26
> 最近全量执行：2026-09-22，51/51 PASS（Chromium headless）

## P0（核心路径，失败即功能不可用）

| # | 验收项 | 方式 | 状态 |
|---|---|---|---|
| P0-1 | manifest 提取幂等（两次提取除 extracted_at 外字节一致） | harness T23 / l_hash_check ① | ✅ |
| P0-2 | 编辑翻转：改一字 → 恰好该页 hash 翻转、他页不变 | harness T23 / l_hash_check ② | ✅ |
| P0-3 | hash 双端一致：编辑器保存产物的 data-content-hash == extractor 重算（14/14 页） | harness T23 / l_hash_check ③ | ✅ |
| P0-4 | 烙入契约三要素静态可验（render-mode / page-baked-16x9 三属性 / .baked-source 源层），check-images 页面级槽位零误报 | harness T24 / m_bake_check | ✅ |
| P0-5 | 源层保留与回退：烙入前后文本提取一致；摘除 img+render-mode 即完整回退 | harness T24 | ✅ |
| P0-6 | 生图指令 Text 段是 manifest 文本精确子串（防幻觉硬校验） | harness T24 | ✅ |
| P0-7 | 导出管线端到端：PDF 页数/尺寸恰为 13.333″×7.5″、svgBlip 双写、postflight 重开包一致 | harness T25 / n_fidelity_check | ✅ |
| P0-8 | 单向纪律：导出前后 index.html 字节一致（sha256 比对） | harness T25 | ✅ |
| P0-9 | 编辑器三态工作台：背面三态（就绪 SVG/过期水印/黑面诚实空态）、对比默认并排、stale 闭环（改字→水印→重导→消除） | harness T26 / o_tri_view_check | ✅ |
| P0-10 | 混合 deck 回归：烙入页 + HTML 页共存，滚动/章节跳转/保存幂等零回归 | harness T1-bake-mix / T24 | ✅ |

## P1（重要回归路径）

| # | 验收项 | 方式 | 状态 |
|---|---|---|---|
| P1-1 | 防线 C 门禁：伪造漂移基线 → 阻断并逐元素列出，不产半成品 | harness T25 ⑧ | ✅ |
| P1-2 | 降级链：屏蔽 pdftocairo → png-fallback 逐页列明；屏蔽截图 → 非零退出无半成品 | harness T25 ⑥ | ✅ |
| P1-3 | stale 检出：hash 翻转后 export/ 指纹过期被检出并指名页 | harness T25 ⑤ | ✅ |
| P1-4 | 保真阈值：全 deck 平均 diff <2%、单页 <5%、烙入页直通不参与 | harness T25 ③ | ✅ |
| P1-5 | 烙入页编辑器行为：正面文字锁（注册表无源层元素）、源层编辑入口、保存后烙入图 stale | harness T24/T26 | ✅ |
| P1-6 | 嵌入协议：export-intent 消息格式；exportManifest/exportBaseUrl 注入与缺省推导 | harness T26 ⑦ | ✅ |
| P1-7 | 降级引导：删 export/ 后对比/导出页为引导态不报错 | harness T26 ⑦ | ✅ |
| P1-8 | 翻面 reduced-motion 即时切换无动画残留；3D 上下文按需启用不污染 T4 渲染一致性 | harness T26 + T4 | ✅ |
| P1-9 | 真实 oai生图烙入（GPT-Image-2.5，i2i 锚图）：bake-mix ch-baked 页 2048×1152 真图，check-images 零警告 | 人工目检 + T24 | ✅ 2026-09-22 |
| P1-10 | 真实 Office 365 / WPS 打开 deck.pptx：版式零位移、文字矢量清晰、老载体走 PNG | 人工 | ⏳ 待人工 |
| P1-11 | 烙入页生图质量验收（文字准确/材质/构图，代表页审批闸门的真实走查） | 人工 | ⏳ 待人工 |
| P1-12 | OFL 字体迁移 20 主题 + 防线 A 子集化全量启用 | 独立批次 | ⏳ 未开工 |
| P1-13 | 可编辑 PPTX（子技能 C）：C1–C3 全落地——文本/形状/原生 chart（双源校验 5%）/grpSp 分组/烙图兜底/字体内嵌（fsType 闸）/双轨编排（deck.pptx 可编辑轨 + deck-vector.pptx + deck.pdf 保真轨 + manifest tracks）/编辑器导出面板双轨适配 | harness T27 + T25（双轨适配） | ✅（2026-09-22） |
| P1-14 | 可编辑轨版式一致性五层加固：字体随档默认化（自动子集化内嵌）/行高基线校准/松配合/几何自净零残留/LO 回验逐页降级；cmb-retail 54 页压测 degraded=0、文本覆盖率 1.0 | harness T27（H/ 组） | ✅ 2026-09-24 |
| P1-15 | 可编辑轨数学认证门禁（F1–F4′+混排边界项）：certify-pptx.py 四规则纯计算；旧产物新口径 921 违规（p35×55/p36×9/p38×16 点名页全中）、新产物 0 违规、LO 渲染层复核 p35/p36/p38 相交 0 对 | harness T27 | ✅ 2026-09-28 |
| P1-16 | 文本不烙图政策 + 净距规则：文本块修复阶梯终端=页级降级（cmb-retail 降级 16 页全列明），p18 文本截图消除；R4c 骑缝规则堵漏（p35 压卡片边缘修复）；LO 复核 p18/p20/p35 相交 0 对 | harness T27（禁令断言+骑缝合成页） | ✅ 2026-09-28 |
