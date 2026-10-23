# 动态脑暴（Briefing v2）：验收证据

> 2026-10-14 · 设计依据：[brief-dynamic-brainstorming.md](../design/brief-dynamic-brainstorming.md)（已批准，P1 实施完成）；实施实录：[1014_brief_dynamic_brainstorming.md](../progress/1014_brief_dynamic_brainstorming.md)。

## 验收边界

验收对象：agent 生成 `brief.options` → `open_editor(brief_options=...)` 注入 → daemon 校验落库 → 编辑器动态渲染三态 → `brief.submitted` 提交格式不变的完整链路，含嵌入态入站 `pptx-html:brief-options` 与裸静态回落。**不含**：agent 选项生成内容质量（依赖模型，人工目检）、P2 主题封面预览卡（未实施）。

## P0（失败即功能不成立）

| 项 | 方法 | 结果 |
|---|---|---|
| 合法 options 注入 → 会话状态携带 → 页面动态渲染（选项文本来自 options 而非静态字面量，画像卡存在） | T35a（`y_dynamic_brief_check.py`，真 daemon + Playwright） | PASS |
| 非法 options 拒收（维度越枚举/缺 prefill_reason/超字数/ask 空组等 16 子用例）→ 400 且会话原值不变 | core `BriefOptionsCase` + T35b 端到端 | PASS |
| 无注入 / `static_fallback:true` → 静态问卷渲染，DOM 与改造前逐节点一致 | T35c + k_brief 28 项既有断言全绿 | PASS |
| 提交输出零回归：动态作答 design-brief JSON 键结构与静态提交 diff 为空（仅多可选 extras） | T35f | PASS |

## P1（重要回归路径）

| 项 | 方法 | 结果 |
|---|---|---|
| 覆盖语义：二次带参整体替换、不带参保持；页面重进 brief 视图取到新值 | T35d + core | PASS |
| 嵌入态入站注入/未注入/非法注入三态 | T35e（harness.html iframe 真实嵌入） | PASS |
| 旧版 sessions 表幂等迁移补列 | core `test_legacy_sessions_table_migrates` | PASS |
| 五工具契约不变（MCP 工具清单实测） | r_bridge_check sdk 组 | PASS |

## 汇总

- core：**38 passed, 44 subtests passed**；T35：**28/28 ALL PASS**；全量 `run_e2e.py`：**61 项 60 PASS 1 FAIL**（T34 为既有失败，与本改动零交集，证据见实录）。
- agent 生成质量：NOT_RUN（人工目检，待真实使用回收样本后进 P3 exemplar 沉淀）。
