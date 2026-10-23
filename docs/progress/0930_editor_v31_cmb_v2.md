# 0930：编辑器 v3.1（交互收敛 + organic 视觉）+ cmb-retail-v2 设计升级 deck

> 日期：2026-09-29/30 · 性质：用户驱动迭代（两条线：deck 设计升级 + 编辑器改版）

## 一、cmb-retail-v2：同内容设计升级版（tests/decks/cmb-retail-v2/）

- **诉求**：以 cmb-retail（B1 瑞士 IKB 蓝，54 页高密度 1:1 还原基准）为内容唯一来源，逐字不变做出设计感更强的版本。
- **路径**：v2.0 = A1 电子杂志基底（衬线 + Ghost 巨字 + 暗色仪式页明暗节奏，7 批并行分包施工）→ 用户反馈封面丑、要"色彩克制但更亮更多样" → v2.1 改冻结 **E4 包豪斯·原色红**（米白纸 + 墨黑 + 原色红 #D1342B，恰好贴合招行/天弘品牌红），排版几何不变：token/母题/字重倒挂全局机械换皮 + 封面重设计（满版原色红 + 基本形构成 + 照片纸托装裱）+ 封底闭环 + 章节页暗墨红圆焦点。
- **容量修复两轮**：分包施工 102 项 → 修复代理收敛到 4 → 手工收尾（徽记 chip 骑缝、净距·PPT 的 padding 而非 margin 修复、文本相碰加 <br> 控制断行）；换字体后 46 项垂直微超（无衬线自然行高更大）→ min-height 撑净高为主。
- **终态**：渲染校验 54 页 ALL PASS、容量门禁 0 违规、check-images 通过、k_nav 三通道 PASS、页级 hash + `.manifest-baseline.json` 已写。文本逐字一致性经程序化比对（唯一差异=mask-lines 分行叶拆分，拼接后逐字相同）。
- **方法论沉淀**：分包施工（7 批 × design-brief.md 最高法则）可行；masthead 内嵌图片因 align-items:baseline 会把刊头文字压到 y≈113（页首内容须 ≥120px 起排）；盒阴影/浮层染 iframe 会破坏 T4（编辑器侧同理）。

## 二、编辑器 v3.1（editor.html）

用户三诉求落地：

1. **目录侧栏常驻化**：顶栏"目录"按钮移除；侧栏收起态=34px 细条（把手吸附左缘常显，一键收/展），右缘拖拽调宽（--toc-w 180–420px），缩略图卡片 HTML5 拖拽排序（直接重排 iframe 内 .slide-slot DOM 序 + 置脏；页脚页码文本不随排序改写——内容层的已知边界）。
2. **主导航收敛**：双"编辑"语义消除——viewSeg（编辑/对比/导出）+ modeSeg（文字编辑/批注）合并为单条「编辑 | 批注 | 导出」（批注=伪视图：编辑视图+批注模式）；对比质检收进导出页 `#expSubSeg` 子页签（产物清单 | 对比质检），对比页有「← 产物清单」返回。设计面板/需求脑暴入口移入右侧浮动栏（.rail 主流内右缘条，胶囊竖排）；脑暴由全屏覆盖层改右侧 520px 浮动面板。
3. **一键转换**：导出页新增 #btnConvert「一键转换导出」，三通道分发——嵌入态 postMessage export-intent（带 formats 字段）/ edit.py 以 `--convert` 启动时 POST /api/convert 子进程触发技能 export-pptx.py（**转换实现 100% 在技能侧，edit.py 只是 opt-in 触发器，红线不变**，/api/health 增 convert 宣告）/ 都没有则复制技能命令。SVG/PNG 不单列按钮——它们是同一管线的中间产物（export/page-NN.svg/.png），转换完成后经产物清单/对比质检消费。
4. **organic 视觉**：暖纸底 #f4efe6 + 赤陶 #c0562f + 苔绿、弥散色斑底景、胶囊按钮/分段、24px 圆角浮动面板、空态有机 blob、柔和弥散阴影、衬线品牌字。

### 过程中修掉的两个真问题（方法论价值）

- **T4 渲染一致性**：任何贴/压舞台的元素的 box-shadow 都会染进 deck iframe 像素（二分定位：header 投影 → 顶条带 + 全局 AA 噪声）。规则：**贴舞台元素一律 border 分隔、禁投影**；浮动件不得覆盖 iframe（rail 从 fixed 改主流内右缘条、toc-collapse 收进侧栏内）。
- **curSlideIdx 漂移**：视图 display:none 期间 deck offsetTop 全塌为 0，scroll 监听把页码漂到末页。修复：applyView 恢复可见后补发合成 scroll 刷新；o_tri_view_check 的 scroll_deck_to 加合成 scroll + 两轮重试硬化。

### harness 兼容面更新

- run_e2e.py：批注/编辑选择器 `#modeSeg button[data-mode=…]` → `#viewSeg button[data-view="annotate|edit"]`（3 处）。
- o_tri_view_check.py：对比入口 `#viewSeg [data-view=compare]` → 「导出 → #expSubSeg [data-view=compare]」（3 处）+ scroll_deck_to 硬化。
- 终验：**run_e2e 54/54 PASS**（含 T23–T28 子进程套件）、k_brief_check PASS、o_tri_view_check 独立 PASS。

## 三、改动文件清单

- `editor.html`（v3.0→v3.1）、`tools/edit.py`（--convert + /api/convert + health.convert）
- `tests/harness/run_e2e.py`、`tests/harness/o_tri_view_check.py`（选择器/硬化）
- `tests/decks/cmb-retail-v2/`（新 deck：index.html + fragments/ + design-brief.md + assets 硬链接 + capacity-report.json + .manifest-baseline.json）
- `AGENTS.md`（v3.1 与 /api/convert 边界同步）

---

## 追记（2026-09-30 第二轮：用户反馈修正）

1. **素材路径修复通道**：用户发现"编辑器打开的 html 素材路径有问题"。根因：FSAA/拖拽打开本地文件时没有 assetsUrl 基址，deck 内 `assets/` 相对引用按 editor.html 所在目录解析 → 全破图。修复：initEditLayer 后 1.5s 扫描破图（`img.complete && naturalWidth===0` 且相对 src），警告条带「选择素材目录修复」动作按钮（showDirectoryPicker → 逐级 getDirectoryHandle 解析相对路径 → blob: URL 换源）；原 src 存 `data-editor-blob-orig`，serializeClean 还原——会话级修复不进保存产物；无 FSAA 类 API 时降级为文字引导（改用 tools/edit.py 打开）。HTTP(?deck=)/嵌入通道不受影响。
2. **文案修正**：保存按钮的无 FSAA 降级文案「导出下载」→「保存下载」；主导航「导出」→「翻转」（data-view 值不变，harness 无感），面板标题「翻转产物」。
3. **翻转页按钮收敛**：移除「重新翻转导出」（#btnExpReflip，与一键转换重复）；保留 一键转换导出 / 重新读取产物 / 三个下载件（下载件即交付物入口，不可省）。

4. **一键启动 WebUI + 启动即转**（方案 2 落地）：`tools/start-webui.sh [deck目录]`（= `edit.py <dir> --convert`）——伴随服务启动时若工作目录有 index.html 即后台线程自动跑 export-pptx.py（异步任务制：idle→running→done/failed，重复触发幂等，`GET /api/convert-status` 查态）；编辑器加载时探测到 running 会接续显示"转换中"并在完成后自动 refreshExport。端到端实测：bake-mix 从启动到 deck.pptx 产出全链路通过。**踩实修复**：deck 位于服务根目录时 `deckPath.slice(0, lastIndexOf('/')+1)` 得空串被 falsy 吞掉 → triDeckBase 失效、export/ 通道盲——改显式 null 判断（'' = 当前目录是合法基址）。

5. **原生 PPTX 预览 + 下载合并**（第三轮用户反馈）：用户指出"SVG 对比没有价值"——转曲件与 HTML 同源，对比信息量低。落地：可编辑轨的 LO 参考渲染页图从临时目录持久化到 `export/native/page-NN.png`（报告新增 native_preview 字段；无 soffice/--skip-verify 诚实缺省）；编辑器对比质检/翻面/叠层的产物载体改为 native 优先 + onerror 回落 SVG（烙入页直通不变），对比页头部加口径说明。下载三件套合并为「下载交付件 ▾」下拉（dlWrap/dlMenu，三按钮 id/dataset 不动，T26 兼容）。T26 更新：②d/③a/⑥c 产物断言改双口径（native 优先/SVG 回落），"产物缺失"模拟须同时删 svg 与 native 页图。**踩坑**：保真轨清场循环 os.remove 撞上 native/ 目录（Is a directory）→ keep 集加目录保护——新增 export/ 子目录时先想清场兼容性。
