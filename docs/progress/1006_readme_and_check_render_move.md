# 2026-10-06 · README 成稿 + 渲染校验脚本归入技能 + AGENTS.md 精简

## 1. AGENTS.md 精简（60KB → 16KB，约 -73%）

- 版本编年史、验收跑分、评测过程全部移出（证据原本就在 `docs/test_acceptance/editor-agent-bridge.md` §16 与 `docs/progress/1002/1003`）；editor.html 逐版本 changelog 删除，只留 v3.5 当前能力清单。
- 保留全部操作性红线：editor-first 五工具、await 3600 单回合一次、brief 冻结、durable processing 语义、SVG base64 / 双轨契约、SSE 生命周期、测试不碰真实 deck。
- 顺手修正三处过时表述：导出决策（HTML→PPTX 已是可选子技能）、编辑范围（现状已含样式/图片/批注）、保存三通道优先级。
- 协作约定新增：版本编年史与验收跑分写入 docs/progress 与 docs/test_acceptance，不写入 AGENTS.md。

## 2. 渲染校验脚本归入技能（j_render_check → check-render）

- 动机：产品形态 = 1 技能 + 1 MCP；技能工作流（SKILL.md Step 5、export-pptx 防线 C1）却跨目录依赖 `tests/harness/j_render_check.py`，tests/ 应只面向开发者。
- 迁移：`tests/harness/j_render_check.py` → `skills/html-pptx/scripts/check-render.py`（git mv 保留历史；命名对齐 check-capacity/check-images 家族）。export-pptx.py 的门禁路径改为 `__file__` 同目录相对，技能自包含、不再假设仓库根。
- 同步更新 10 处引用：SKILL.md ×2（命令 + validation argv）、export-pptx.py ×4、harness 四处调用点（m_bake / s_bridge_scale / t_imagegen / r_bridge 的 SKILL.md 断言字符串）、密度脚本注释、AGENTS.md、docs/design/pptx-export-svg.md。
- 验收：check-render 直跑 bake-mix 4/4 PASS；T24 m_bake_check 41/41 PASS；T25 n_fidelity_check 29/29 PASS（含完整双轨导出与门禁阻断演练）；r_bridge_check 六组 PASS（含 SKILL.md 契约断言）；全部触及文件 py_compile 通过；活代码旧路径零残留（历史文档与 html-pptx-workspace 快照不动）。

## 3. README.md 成稿

- 根目录新增 README：先讲人话（"AI 做的 PPT 终于可以直接改了"）→ 三个关键设计（HTML 中间媒介向上 AI 烙入向下 PPTX / 原地可编辑不依赖 AI / MCP 标准接入任意 agent 框架）→ 场景表 → 技术细节折叠深入 → 功能差异对比表（不点名其他项目）→ 快速开始（只含技能与 MCP 两个产品入口，测试脚本不出现在用户面）。

## 4. test_case1/ 不入库

根目录 `test_case1/`（41MB，54 页真实 deck + 素材，CNS-08 恢复演练工作区）与 cmb-retail 系列同性质，登记入 .gitignore 本地保留、不入版本库。
