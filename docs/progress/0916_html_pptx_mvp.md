# 0916 · 项目从零到 MVP

## 背景

项目目标：HTML PPTX 设计系统——AI 生成网页版 PPT（单 HTML + assets/），配套独立编辑器页面就地编辑。本日完成从零到可用的完整闭环。

## 决策记录（按时间）

1. **形态**：16:9 竖向滚动；纯静态无框架；FSAA 直写保存；不反向导出 pptx（Slidev 的 pptx-editable 实践证明保真天花板低）。
2. **架构**：独立编辑器页面 + 纯净产物；AI 在开发侧，页面不含 AI；pptx→HTML 由 AI agent 转换。
3. **两轮调研**：6 个 `source/` 参考项目 + 主流框架（reveal/Slidev/impress/scrollytelling），结论沉淀 `docs/research/source-survey.md`。
4. **技能设计**：原则优先、枚举谨慎；固定骨架 SLOT 制；主题库 13 套策展（guizang + frontend-slides 血统）；可编辑标记契约。
5. **编辑器**：iframe srcdoc 隔离渲染；两段手势文字编辑；批注模式（框选 → 弹窗 → 三层引用回传 AI）。
6. **验收驱动**：4 个子 agent 生成不同主题测试 deck → harness 自动化验收。

## 产出

| 产出 | 位置 | 状态 |
|---|---|---|
| 生成技能 | `skills/html-pptx/` | v1，骨架经框架调研修订（transform-origin bug 等 6 项） |
| 编辑器 | `editor.html` | v1.2（文字编辑 + 图片替换 + 批注） |
| 设计文档 | `docs/design-editor.md` | v0.3，两轮审核修订 |
| 测试 deck ×4 | `tests/decks/` | 全部通过渲染校验 |
| E2E harness | `tests/harness/` | 13/13 PASS |

## 关键踩坑（供后来者）

- Chromium `plaintext-only` 的 Enter 产生 `\n` 而非 `<br>`——提交时必须归一化，否则序列化丢换行；
- iframe 内 FSAA 函数存在但调用被静默吞掉——嵌入态保存必须一律走 postMessage；
- srcdoc 的 base URL 继承编辑器目录——嵌入加载必须注入 `<base>`（assetsUrl）否则图片全 404；
- `transform-origin: top left` 在窄窗口裁切内容——画布缩放必须 `top center`；
- mousedown preventDefault 会抑制焦点转移，Esc 监听要挂双层。

## 遗留

- 图片替换（FSAA 交互）与 Firefox 降级路径未经真实浏览器人工验收；
- 独立模式跨目录打开时编辑器内图片预览坏（产物正确，预览层待 blob URL 方案）；
- 意图清单导出指令未经人工走查。

## 同日追加：技能 v1.1（密度与字排）

- 新增 `skills/html-pptx/references/typography.md`：中文标题分档（vw/vh→px 换算，含封面特档 144-160px）、字重阶梯、槽位字数预算（全角 1/半角 0.5）、密度双档规则；
- SKILL.md：Step 0 展开 pptx 转换子流程（内容重组非逐页复刻）、Step 1 密度冻结、Step 4 容量核对硬规则、占位图规格；
- editor.html 面板加 `density` 选项（low/high），导出的意图指令含密度条目并提示 AI 按工作流重组而非只改字号；
- 验证：同一内容源（远程办公报告）生成 density-low（10 页）/ density-high（9 页）双 deck；harness 回归 15/15 PASS（含新 deck 往返幂等）；独立脚本复核无元素超预算；
- 校准记录：low deck 封面标题 160px 超出原分档表 120px 档 → 修订 typography.md 增加 hero 特档（文档向已验证的实践对齐）。

## 同日追加：技能 v1.2–v1.4（按 skill-roadmap 实施）

**v1.2 信息图组件层**：新增 references/components.md（12 个组件配方，三件套格式，内容类型匹配硬规则：无真实数据禁用量化组件）；验证 deck tests/decks/infographic-b2（11 页，11 类组件全覆盖，Playwright 零溢出）。

**v1.3 图表**：新增 references/charts.md（H-Bar/Column/Line/Donut/Progress 五配方，calc 几何，零 JS）；themes.md 加图表 token 统一推导（color-mix 派生，解决 A 系 accent==ink 撞色）；契约加图表可编辑分层（几何 skip/标签 editable/数值走 AI）；sync-themes.mjs 单源化提前到本期（editor.html 面板数据改为脚本生成 + 幂等写回 + 13 主题自检）；验证 deck tests/decks/charts-a3（10 页，五图表全覆盖，数值-几何比例抽查精确吻合，数据跨页自洽）。

**v1.4 动效语义层**：骨架升 v2（skeleton-version meta、data-animate 页面配方 × data-anim 元素角色、--i 自动阶梯、.js 无脚本门槛、reduced-motion/打印降级）；references/motion.md（决策树 + 六感气质表 + 拆字禁令）；契约加"动效与编辑互斥"条款；编辑器净化扩展（js class、--i 剥离）；已知限制：scaleY 柱体生长不在 v2，记录待评估。

**v1.5 评估结论**：sync 脚本已完成；WebGL 背景推迟（形态不匹配+克制原则）；宿主嵌入深化推迟（等真实宿主）。

**累计验证**：8 个测试 deck；harness 18/18 PASS（T1 往返幂等 ×8、编辑、渲染一致性、批注、面板导出）。
