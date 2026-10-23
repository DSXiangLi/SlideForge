# 0918 · 迭代 C：动效系统 v2

依据：`docs/design/motion-system.md`（2026-09-18 修订意见 2 + `docs/research/motion_gudie.md`）。目标：拆字类动效从"一律禁止"升级为"运行时化"（产物文件中文字永远是纯文本节点，拆字由骨架 JS 入场执行、完成还原）；骨架合并发布 v3（运行时拆字引擎 + G3 质感槽位）；motion.md 重写为 v2（三原理/六原则/recipe 词汇表/丰富度三档）。

## 变更

| 文件 | 变更 |
|---|---|
| `skills/html-pptx/references/editing-contract.md` | 契约 v3（契约先行）："动效与编辑的互斥"节改写为"动效与编辑"——【硬规则】文本破坏性动效必须运行时化，产物中禁止拆字 span；净化清单新增拆字 span 还原 textContent、count-up 终值还原、draw-line 描边 style 归位、`<html>` 运行时 class（js + texture-cover）整体移除；编辑器侧进入编辑前经 `window.__pptxMotion.restore(el)` 强制还原 |
| `skills/html-pptx/assets/skeleton.html` | skeleton v3（`<meta name="skeleton-version" content="3">`）：运行时拆字引擎（chars/words/shatter——文件纯文本，入场拆成 `.sp-unit` 序列，完成后还原为纯文本节点；滚动回滚不重复触发）；新 recipe：count-up（读元素文本终值、支持 `data-from` 起值/千分位/小数/前后缀，结束精确还原文本）、draw-line（加载量长藏线、入场 stroke-dashoffset 归零描出）、fill-bar（scaleX 填充）；背景 ambience 类 `amb-pulse/amb-drift/amb-glow`（强度上限烧死在骨架参数）；缓动三 token `--ease-out/--ease-shift/--ease-loop`；G3 质感槽位（`.slide::before` 消费 `--texture-layer`，`--texture-scope:cover` 时 JS 给 `<html>` 加 `texture-cover`、仅 `.cover-page` 铺层）；reduced-motion/打印降级覆盖全部新 recipe；v2 既有行为（缩放/滚动/键盘/打印/IO/.js 门槛）不变 |
| `skills/html-pptx/references/motion.md` | 重写为 v2：开篇保留"内容自己想动，我们只是把它显影出来"；三条物理原理（注意力预算 1 主+2-3 背景 / 五信息职能 / 时长公式 300ms+bit×200ms、循环 ≥3s）；六条组合原则（stagger 步长公式、Reveal-Hold-Interact、锚点动效、缓动 ≤3 种进骨架 token、方向语义同构、感知性能）；recipe 词汇表（信息职能/适用内容/时长档/实现要点 + 硬规则汇总 + 新项入库走七件规范）；丰富度三档（克制/标准/华丽，共享注意力预算）；主题 G5 接口与气质对照表；配方决策树保留 |
| `skills/html-pptx/SKILL.md` | Step 4 动效条目："拆字类动效一律禁止"→"拆字类只写纯文本+标记，拆字由骨架 JS 运行时执行；【硬规则】产物禁止出现拆字 span"，指向 motion.md v2 |
| `skills/html-pptx/references/themes.md` | "G3 texture 的落地状态"节更新：skeleton v3 已落地质感槽位，写明 `cover-page` 类约定与 scope 语义 |
| `editor.html` | v1.8：`enterEdit` 前调用骨架 `__pptxMotion.restore(el)` 强制还原；`serializeClean` 保存前 `restoreAll()`，克隆体兜底还原 `.sp-unit` 容器、移除 draw-line 的 stroke-dasharray/offset 运行时 style，`<html>` 净化从"移除 js class"升级为"移除整个 class 属性"；EDIT_CLASSES 增加 `split-anim`；品牌行版本号修正（v1.6→v1.8，v1.7 时漏改） |
| `tests/decks/motion-d2/` | 新增 skeleton v3 验收 deck（5 页，D2 柔光暗房主题）：cover=chars+amb-glow、章节页=words、metrics=count-up×2（含 `data-from="12"` 分支）、flow=draw-line（SVG path）、bars=fill-bar×3；框架层由脚本从 skeleton.html 逐字复制并自检一致 |
| `tests/harness/run_e2e.py` | DECKS 增加 motion-d2（T1 往返幂等回归）；新增 T13（骨架 v3 运行时动效：拆字出现→还原纯文本节点、count-up 中间态/终值精确、draw-line 归零、fill-bar 终态、质感层仅封面页、reduced-motion 全文可读零拆字）与 T14（动画进行中点击编辑→强制还原纯文本→保存产物零 span/style/class 污染→重载逐字节幂等） |
| `docs/design/motion-system.md` | 状态：待评审 → 已实施（迭代 C） |
| `docs/design/theme-schema.md` | 状态：待评审 → 已实施（迭代 B） |
| `docs/design/README.md` | 文档地图补 theme-schema/motion-system 的实施标记 |
| `AGENTS.md` | skeleton v3、motion.md v2、契约 v3、editor v1.8 描述同步 |

## 验收

- `node skills/html-pptx/scripts/sync-themes.mjs`：16 套主题校验通过，editor.html 幂等无改动（themes.md 仅散文改动）；
- `python3 tests/harness/run_e2e.py`：**24/24 PASS**（原 21 项 + T1-motion-d2 + T13 + T14；8 个存量 v2 骨架 deck 回归全绿，T4 渲染一致性像素差在抗锯齿容差内）。Chromium 145 headless。

## 偏离记录（deviation）

1. **缓动 token 替换既有 `ease`**：v2 骨架的 reveal/基础 data-anim 过渡 timing function 从 `ease` 改为 `--ease-out`（cubic-bezier(.22,1,.36,1)）——规格 §3.4 要求缓动写进骨架 token；时长/延迟/触发逻辑不变。存量 v2 deck 内嵌旧骨架不受影响。
2. **`--texture-scope: cover` 的实现机制**：theme-schema.md §4 只定义语义未定义机制，CSS 无法按字符串 token 分支，采用"骨架 JS 读 token → `<html>` 加 `texture-cover` class + 生成侧给封面/章节页标 `cover-page` 类"；`texture-cover` 列入契约运行时净化清单。
3. **shatter 散布用确定性伪随机**（seed=序号×137.5°）：同一文本每次入场形态一致，不用 `Math.random`（避免逐次形态漂移、便于评审复现）。
4. **count-up 缓动在 JS 内插值**（easeOutCubic，时长固定 1400ms 取档位中值）：数值滚动不是 CSS 过渡，未占用第四种缓动 token，词汇表纪律（≤3 种）仍成立。
5. **ambience 强度上限由骨架常量承载**（位移 ≤10px、不透明度摆幅 ≤.4、周期 ≥3s），生成侧只能选类不能调参——"上限"因此不可被生成侧违反。
6. **编辑器 `<html>` 净化升级**：从"移除 js class"改为"移除整个 class 属性"（骨架产物的 html 本就无 class，js/texture-cover 均为运行时产物）。
7. **motion-d2 夹具有意违反"每页主动效 ≤1"**：metrics 页放两个 count-up 以覆盖有无 `data-from` 两分支，已在 deck 注释声明夹具用途；生产 deck 仍须遵守 motion.md §5。
8. **editor.html 品牌行版本号**：v1.7 时漏改可见标签（一直显示 v1.6），本次直接修正为 v1.8。

## 明确不做

- 存量 v2 骨架 deck 不追溯（骨架内嵌于产物文件，升级只影响新产物）；
- 编辑器面板 motion 选项未改文案（丰富度三档语义写在 motion.md，面板映射属后续面板迭代）；
- 竖向柱体 scaleY 生长配方未入骨架（motion.md §6 记为已知限制，入库走七件规范）；
- 不做 git commit。
