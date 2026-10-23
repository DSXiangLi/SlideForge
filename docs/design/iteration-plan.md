# 开工计划（v2 迭代排期）

> 日期：2026-09-18 · 范围：`docs/design/` 全部待评审设计 + 编辑器 v2
> 原则沿用 roadmap §三：契约先行、每期有可执行验收、先低风险后高风险。

## 迭代序列

| 迭代 | 内容 | 设计依据 | 风险 | 验收方式 |
|---|---|---|---|---|
| **A（本轮）** | 编辑器 v2：文字样式编辑（字体/字号/字色/对齐）+ PPT 式目录侧栏 + 本地 git 版本回滚 | `editor-v2.md` | 中（editor.html 单文件改三处 + 新增 tools/edit.py） | harness 扩展用例全绿 + 用户验收 |
| B | 主题 Schema 化：themes.md 重构为 G0–G8 + focus 声明；sync-themes.mjs 升级兼任 schema 校验；面板按 focus 分组 | `theme-schema.md` | 低（文档 + 脚本） | schema 校验脚本 + 面板分组截图评审 |
| C | 动效 v2：skeleton v3（运行时拆字 + 质感槽位，同版发布）+ motion.md v2 重写 + 契约拆字条款修订 | `motion-system.md` | **高**（骨架框架层） | reduced-motion 可读、新旧骨架幂等、编辑往返 |
| D | 信息图 v2：components.md 重构为结构族 × 皮肤模型 + 数据形态硬约定 + 适配矩阵 | `infographic-system.md` | 中（纯 references） | 新结构族测试 deck + harness 组件用例 |
| E | 插画管线：SKILL.md Step 5.5 + 图片槽位契约（data-image-slot/intent/state）+ 反降级校验 | `illustration-pipeline.md` | 中（契约变更先行） | 槽位静态校验 + 插画 pass 端到端 |
| F | 向上兼容（全图化）：评估后启动 | `compat-roadmap.md` | 高 | 另行规划 |
| G | 向下兼容（html2pptx）：评估后启动 | `compat-roadmap.md` | 高 | 另行规划 |

## 依赖关系

- B（主题 Schema）是 C 的 G5 动效亲和、E 的 G7 插画风格的前置——Schema 字段不定稿，动效/插画无处声明亲和；
- C 与 D 无互相依赖，可并行；E 依赖 B；
- F/G 依赖 E 的生图能力与渲染截图工具链（C 的骨架升级顺带完善降级链）。

## 本轮（迭代 A）交付物清单

1. `editor.html` v1.6：样式控件组（选中文字时出现）、目录侧栏（懒渲染缩略图 + 点击导航 + 当前页高亮）、后端探测与历史面板；
2. `tools/edit.py`：零依赖伴随服务（静态托管 + /api/save、/api/versions、/api/rollback，git 集成含 pre-rollback 保护）；
3. `skills/html-pptx/references/editing-contract.md`：新增"样式覆盖"条款（白名单四属性）；
4. `tests/harness/`：样式持久化、侧栏导航、git 保存/回滚的端到端用例；
5. `docs/progress/` 迭代记录 + `AGENTS.md` 版本号同步（editor v1.6）。
