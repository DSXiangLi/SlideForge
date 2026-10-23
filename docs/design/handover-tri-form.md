# HANDOVER：三形态翻转（整页生图 + HTML→PPTX + 编辑器 v3）——下个 session 的起点

> 日期：2026-09-21 · 交接对象：全新 session
> 本轮产出：**设计阶段闭环**——四份实施级设计文档 + 一轮 9 维审核（5 个问题已修）+ AGENTS.md/README 同步。**零代码改动**，实施未开始。
> 本文档 = 进度快照 + 阅读顺序 + 已定决策快照 + M1–M4 任务规划 + 遗留待澄清点。

---

## 一、阅读顺序（按此读，别跳）

1. **`AGENTS.md`**——项目基调与红线。重点读"已确认的技术决策"最后一条（**转换即技能**架构红线，2026-09-21 新增）与"项目组成"第 4 项（形态翻转子技能条目）。
2. **`docs/design/tri-form-architecture.md`**——总览。三形态角色、翻转统一动词、manifest + content-hash 公共地基（§4 全文精读，含 hash 计算环境统一条款、manifest 两个落点、role 推导规则）、防幻觉三硬规则、产物目录约定、M1–M4 路线。
3. **`docs/design/page-render-mode.md`**——子技能 A（向上兼容）。整页烙入唯一形态、`.baked-source` 源层结构、契约 v7 增量与骨架 v7.3 改动点、HTML 样张锚、指令编译模板、代表页闸门、失败回退。
4. **`docs/design/pptx-export-svg.md`**——子技能 B（向下兼容）。PDF→SVG→PPTX 管线五环节、**§4 字体/布局四道防线（本设计最重要的章节）**、M3 前置 spike 硬规则、降级链、保真分权威口径。
5. **`docs/design/editor-tri-view.md`**——编辑器 v3。三态工作台、翻面手势 + 背面三态（就绪/过期/黑面空态）、**并排为对比默认落定**、热区资产由管线产出（编辑器无栅格化能力）、stale 闭环。
6. 现状代码（需要动手时再读）：`skills/html-pptx/SKILL.md`（Step 5.5 插画 pass 是烙入模式的扩展基点）、`references/editing-contract.md`（v6.4，契约 v7 在此增量）、`tests/harness/j_render_check.py`（渲染校验设施，门禁与保真分复用）。

**不要重读** `source/codex-ppt-skill-main/` 与 `source/ppt-master/`——调研结论已压缩进设计文档（样张锚/指令分节法、编译器路线的否决理由），重读浪费上下文。`compat-roadmap.md` 已被取代，仅历史价值。

## 二、进度快照

- 技能现状：v1.7（skeleton v7.2 / themes 20 重主题 / editing-contract v6.4 / Step 5.5 插画 pass 已生产可用）；编辑器 v2.5；harness 全绿。
- 本轮新增：`docs/design/` 下 tri-form-architecture / page-render-mode / pptx-export-svg / editor-tri-view 四文档（状态：**待评审**——用户已逐条参与设计讨论并给出修订意见，方向级共识已达成，细节仍可推翻）；README 文档地图与决策速览已更新；compat-roadmap 标记被取代；AGENTS.md 新增"转换即技能"红线与项目组成第 4 项。
- **未实施**：extract-manifest、契约 v7、骨架 v7.3、烙入 pass、导出管线、编辑器 v3，均未动工。

## 三、已定决策快照（下轮不要重新讨论，除非用户明确推翻）

1. **三形态角色**：HTML = 唯一真相源 + 主战场；整页图片 = 视觉上限增强层；PPTX = 单向交付快照，**永不回读**。
2. **转换即技能【红线】**：两个转换能力是 `skills/html-pptx/` 子技能；`tools/edit.py` 永不承担转换；`editor.html` 无转换逻辑，只消费 `export/` 产物。
3. **生图只留整页烙入**：不做"背景生图+文字叠加"混合态（用户明确否决，理由是边界与插画模式不清）。插画 = 页内槽位，烙入 = 整页，无第三种。
4. **源层保留**：烙入页 = 整页 img + `.baked-source` hidden 源层；源层参与 content-hash，是 stale 检测与回退的真相锚。
5. **PPTX 走矢量转录管线**：printToPDF → pdf→svg → svgBlip+PNG 双写。**不走** ppt-master 式 SVG→DrawingML 编译器（4.7 万行 + 字体不内嵌 + 启发式量宽，已否决）；**不走**原生文本框映射主路（Slidev 保真天花板证据）；原生映射仅留作远期可选轨。
6. **字体四道防线**：A 字体随 deck 子集化内嵌（根治）/ B 度量兼容回退栈 / C 导出渲染门禁（行数+宽度漂移对比，不过门禁不产 PDF）/ D 容器余量纪律。
7. **防幻觉三硬规则**：单向流动、逐字引用（生图指令与导出文本 100% 来自 manifest）、hash 失效检测。
8. **编辑器交互**：翻转 = 逐页手势与过场；**并排 = 对比默认落定**；热区 = 管线产出 `page-NN.diff.png` 资产；背面三态含黑面诚实空态（不放假进度条）。
9. **保真分口径**：HTML 截图 vs 最终 SVG 光栅化件的像素 diff（测转录链损耗）；**不用 LibreOffice 当裁判**（它渲染 svgBlip 自身有缺陷）。

## 四、任务规划 M1–M4

### M1 · 公共地基：extract-manifest + content-hash

- **开工第一个决策点（技术栈）**：manifest 提取是**渲染后提取**（需要行数/宽度快照），必须有浏览器环境——现有 `scripts/*.mjs` 是纯 node stdlib 无依赖，而 `tests/harness/j_render_check.py` 已是 python+Playwright。**推荐落 python（`scripts/extract-manifest.py`）复用 harness 的 Playwright 设施**，不要为 node 侧引入 puppeteer 依赖。
- 改动清单：`scripts/extract-manifest.py`（freeze → 净化 → 逐页提取 texts/images/hash/role）；SKILL.md Step 5 后加"写入页级 hash"一句；editor.html 保存时 Web Crypto 重算 `data-content-hash`（与 extractor 同算法同净化语义——**两侧对同一内容必须算出同一 hash，这是 M1 的核心验收**）。
- 验收：同一 deck 两次提取幂等；编辑器改字保存后该页 hash 必翻转、他页不变；harness 新增 hash 一致性用例。

### M2 · 子技能 A：整页烙入

- 前置：M1 完成。
- 改动清单：editing-contract.md 升 **v7**（`data-render-mode` / `.baked-source` / 页面级槽位）；skeleton 升 **v7.3**（运行时排除 `.baked-source`、打印确认）；SKILL.md 新增 **Step 5.6 页面烙入 pass**（逐页选定闸门 → 指令编译 → HTML 样张锚截图 → 代表页审批 → oai生图 2560×1440 → 回归）；`check-images.mjs` 扩展页面级槽位。
- 验收：见 page-render-mode.md §6（源层回退、指令子串校验、混合 deck 回归、失败回退演练）。

### M3 · 子技能 B：PPTX 导出

- 前置：M1；M2 非必需（纯 HTML deck 也可导出）。
- **第一件事是 spike【硬规则】**：单页 deck → printToPDF → 逐家转换器实测 text-as-path 行为并固化参数 → svgBlip 双写 → 真实 Office 365 + WPS 目检。spike 不过则回填修订设计，不带未验证假设批量落码。
- 之后：导出脚本（freeze/打印/转 SVG/组装/降级链）、防线 C 门禁（复用 j_render_check + 漂移对比）、防线 A 字体子集化 pass（pyftsubset + 骨架 fonts SLOT + themes G2 补 `metric_fallback` 字段）、postflight + 保真分 + diff 热力图产出。
- 验收：见 pptx-export-svg.md §6（门禁演练、降级演练、保真阈值）。

### M4 · 编辑器 v3

- 前置：M1（stale 检测）、M3 产物约定（对比视图需要 export/ 实物）；M2 后补烙入页交互。
- 改动清单：顶栏三态分段；翻面组件（三态背面 + backface-visibility + 动画期禁 iframe 指针事件）；并排/滑动分割/热区三视图；导出面板 + stale 水印闭环；postMessage `export-intent`；harness `m_fidelity_check.py`。
- 验收：见 editor-tri-view.md §7。

**排序纪律**：M1 独立有价值（现有插画模式立即获得 staleness 检测），先落；M2/M3 可并行；M4 最后。每个 M 独立交付、独立验收，不做大爆炸。

## 五、遗留待澄清点（不阻断 M1，带着推荐默认值开工）

1. **OFL 字体重选工作量**：20 套主题 G2 字体栈收敛到可再分发开源字体是防线 A 的前提，工作量大——推荐随 M3 分批迁，M3 之前 deck 继续用系统栈（防线 C 门禁兜底）。
2. **烙入页批注粒度**：只到页级+坐标区域（excerpt 为空）——推荐接受，属全图化固有限制。

## 六、开工第一句话

"读 handover-tri-form.md 与总览文档，然后开工 M1：决策 extract-manifest 技术栈（推荐 python 复用 harness Playwright），实现提取器 + 编辑器 hash 重算，验收两侧 hash 一致。"
