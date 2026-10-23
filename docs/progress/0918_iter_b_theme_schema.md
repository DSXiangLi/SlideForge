# 0918 · 迭代 B：主题 Schema 化

依据：`docs/design/theme-schema.md`（2026-09-18 修订意见 1）。目标：themes.md 从"6 色 token + 3 字体栈 + 使用要点"的隐式惯例升级为显式 Schema（G0–G8 九字段组 + focus 声明），sync-themes.mjs 兼任 Schema 校验器，editor 面板按 focus 分组展示。

## 变更

| 文件 | 变更 |
|---|---|
| `skills/html-pptx/references/themes.md` | 全文重构为 G0–G8 Schema 结构；开头集中维护字段组表 + 缺省推导规则表（只此一份）；存量 13 套按 §5 映射归位（A 系 G1+G2、B 系 G1+G4、C1/C3 G1、C2 G1+G3、C4 G2），"使用要点"拆入 G1 高亮纪律 / G2 字重倾向·标题修饰 / G4 hairline 规格 / G5 动效气质；新增 D 系三套候选：D1 奶油物语（focus=G1，暖白/浅杏/焦糖 + Yuanti 圆体 + 大圆角）、D2 柔光暗房（focus=G3，径向辉光 token + 深底暖光）、D3 手绘油彩（focus=G2+G1，Kaiti 手绘衬线栈 + 灰绿/赭石油画配色 + 纸纹氤氲 + G7 插画种子）；选择建议表补三行；注明 G3 token 现在定义、渲染待迭代 C（skeleton v3）落地，本次不改骨架 |
| `skills/html-pptx/scripts/sync-themes.mjs` | 解析新 Schema（`### Xn` 主题段 / `**Gx**` 字段组 / `- **字段**：值` bullets / ```css token 块）；校验项：主题数 16、id 唯一、G0/G1/G2 齐全、focus 组全部显式（G3 须非 flat 三 token、G4 须圆角/hairline/阴影三项）、无主题外 hex（剔除代码块后散文查 hex）、focus 组合内 accent 不撞车 + 全库 6 色三元组不重复；失败打印清单并非零退出；生成 JSON 带 `focus` / `focus_label` / `group` / `group_label` / `vibe` 字段 |
| `editor.html` | v1.7：主题卡按 focus 分组（`.theme-group` + 组标题，顺序 配色→质感→字排→形态），卡片显示 focus 标签 + 气质一句话（`vibe`）；选中切换改为 `querySelectorAll('.theme-card')`（组标题节点不再混入）；问题 header "配色"→"主题"；rhythm/motion/density 组与导出逻辑不变 |
| `skills/html-pptx/SKILL.md` | Step 2：主题 = Schema 定义 + focus（说明气质时带 focus），只选不改原则不变 |
| `AGENTS.md` | themes.md 条目（16 套 + Schema 化）、sync-themes.mjs 条目（兼任校验器）、editor.html v1.7（面板分组） |
| `tests/harness/run_e2e.py` | T9：主题卡断言 13→16，新增 focus 分组数 ≥3 断言（适配而非删除） |

## 验收

- `node skills/html-pptx/scripts/sync-themes.mjs`：16 套解析 + 校验通过，幂等写回 editor.html；负向冒烟（focus 指向未显式给出的组、散文塞 hex）均正确报错 exit=1；
- `python3 tests/harness/run_e2e.py`：21/21 PASS（含适配后的 T9：16 张主题卡 + focus 分组断言通过）。

## 偏离记录（deviation）

1. **面板分组归属规则**：theme-schema.md 未规定 focus 两字段时归入哪一组。实现采用"最差异化优先"（G3 质感 > G2 字排 > G4 形态 > G1 配色），定义在 sync-themes.mjs 注释中——颜色是每套主题的必有维度，非颜色维度优先才能体现"重点"。效果：A 系→字排主导，B 系→形态主导，C2/D2→质感主导，C1/C3/D1→配色主导，C4/D3→字排主导。
2. **D2 柔光暗房的动效气质**：规格示例称 "ambience 型动效亲和"，但 `references/motion.md` §2 气质六选中无 ambience，归入 calm（沉静：慢速、低强度、只动主角），并在 themes.md 该字段处注明。
3. **修复既有解析 quirk**：旧解析器会把文末"图表 token"节的 css 块并入最后一个主题（c4）的 tokens；新解析器以 `##`/`---` 为段界，c4 的 tokens 不再夹带 `--chart-*`（图表 token 本就统一推导，不影响导出指令的正确性）。
4. **主题 label 归一化**：旧 JSON 的 label 保留括号注记（如"克莱因蓝（IKB）"），新生成统一去掉尾括号（id 前的编号与标题行仍保留）；harness T9 断言的"克莱因蓝"子串不受影响。
5. **编辑器版本**：面板分组属呈现层数据驱动调整，仍记为 v1.7 并同步 AGENTS.md。
6. theme-schema.md 状态行仍为"待评审"，本次按任务指令直接实施，未回写该文件状态。

## 明确不做（沿用规格 §7）

- 不改骨架（G3 质感槽位待迭代 C / skeleton v3）；不改 editing-contract.md；不做 git commit；
- 不给用户自定义 hex 的口子；texture 不引入图片纹理资产。
