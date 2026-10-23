# 1014 动态脑暴（Briefing v2 P1）实施实录

> 2026-10-14 · 设计文档：`docs/design/brief-dynamic-brainstorming.md`（用户当日批准）。解决"无论用户输入什么，脑暴选项完全相同"——根因为脑暴页选项 100% 静态硬编码（`BRIEF_GROUPS` 等字面量），用户输入（topic/custom）从不参与选项生成。

## 方案要点（单段注入式）

- 输入来源在对话上下文（指令/素材/附件 agent 自读），页面内不新增素材通道；两轮交互式回环方案在评审中否决。
- agent 按 briefing.md v2（维度池 + 实例化规则 + 缺口表）生成 `brief.options` JSON → `open_editor(view="brief", brief_options=...)` 注入 → 页面动态渲染 → `brief.submitted` 冻结语义不变。
- 曾考虑 `push_update` complete 携带 options 回推，审核发现该工具无结果载荷字段，不可实施，改为 open_editor 可选参数（五工具契约不变、零新增 intent/SSE）。

## 落地清单

- **Bridge**：`tools/bridge_core.py` 新增 `validate_brief_options`（维度 id 枚举 scene/audience/source/pages/style/font/motion/cover + 条件组 x-data/x-brand/x-fidelity；三态 ask/prefilled/skipped；prefilled 必带 prefill_reason；label ≤30/desc ≤120 字等，fail-fast 400 且会话原值不变）；sessions 表 `brief_options_json` 列（幂等 ALTER 迁移，SCHEMA_VERSION 保持 3）；open/status 返回携带；覆盖语义=带参整体替换、不带参保持。`bridge_mcp.py` open_editor 加同名可选参数。
- **编辑器 v3.8**：`editor.html` 脑暴页数据源切换为会话状态 `brief_options`——画像卡（context_summary + signals 胶囊 + 定制徽标）、问题组三态（ask ★推荐+理由 / prefilled 折叠一行可展开 / skipped 页尾折叠区）、theme_pick 推荐置顶+理由（P1 文字形态）、「由 AI 决定」与「全部按推荐」快捷路径；嵌入态入站 `pptx-html:brief-options`（页面侧轻量校验，非法回落静态）；无注入/`static_fallback:true` 回落内建静态问卷（静态 DOM 序列逐节点不变，k_brief 28 项断言实证）。提交输出格式零变化，x-* 条件组选择进可选 `answers.extras`。
- **技能**：`references/briefing.md` 升级 v2（八维度池骨架与缺省体系、简报格式不变；新增实例化规则/优先级缺口表/schema 摘要/三态语义）；`SKILL.md` Step 0.5 更新为"消化上下文 → 缺口盘点 → 生成 brief.options → open_editor 注入 → await brief.submitted → 冻结"，五工具红线与首轮一次 await 纪律未动。

## 验收证据

- core 回归：`pytest tests/harness/test_bridge_core.py` → **38 passed, 44 subtests passed**（新增 BriefOptionsCase 4 测试：合法注入回显、覆盖语义、16 个非法子用例拒收且原值不变、旧表幂等迁移）。
- 新增 `tests/harness/y_dynamic_brief_check.py`（T35，28 项断言）：T35a 注入全链路+动态渲染 / T35b 非法 400 原值不变 / T35c 无参回落静态 / T35d 覆盖语义 / T35e 嵌入态三态 / T35f design-brief JSON 与静态提交键结构 diff 为空（仅多 extras）。28/28 ALL PASS。
- 全量 `run_e2e.py`：**61 项 60 PASS 1 FAIL**——T34-theme-proving 为先于本任务的既有失败（直开 deck 测量，与本次 diff 零交集；`tests/decks/` 与主题库均无未提交改动；失败内容缺 g3 组/e1/e4/g5 重叠，与 1013 在途主题本质重建一致）。
- agent 侧选项生成质量属人工目检项，未自动断言（见 `docs/test_acceptance/brief-dynamic-brainstorming.md`）。

## 遗留

- P2：主题封面预览卡（纯 CSS 16:9 缩略，用用户真实标题渲染）、画像卡打磨、prefilled/skipped 折叠交互细节。
- P3：options 质量 exemplar 沉淀进 briefing.md；0 问确认单触发阈值；驻留页 options 更新推送（如需再加 SSE）。
- 页面内改主题/补充文本只进简报不触发选项重生成（无回环），画像卡提示文案已写明。
