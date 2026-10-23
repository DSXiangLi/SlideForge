# 动态脑暴（Briefing v2）：上下文驱动 + Agent 实例化的需求对齐

> 状态：**已批准，P1 实施完成**。解决"无论用户输入什么，脑暴选项完全相同"的问题。
> 调研依据：`source/` 六项目脑暴机制横评（见 §2）；现状根因见 §1。
> 影响面：`skills/html-pptx/references/briefing.md`（v2）、`skills/html-pptx/SKILL.md` Step 0.5、`editor.html` 脑暴页、`tools/bridge_core.py`（open_editor 可选参数 + 会话状态字段）、嵌入态 postMessage 协议、`tests/harness/`。

## 1. 问题与根因

**现象**：无论用户给什么主题/素材，脑暴页呈现的选项完全相同。

**输入来源澄清**：用户向 agent 下达 PPT 任务时，指令与素材（文字、大纲、附件文件）都在**对话上下文**里给出；agent 是 coding agent，可自行读取附件。脑暴定制应以这部分已有信息为输入，**页面内不新增素材上传/粘贴通道**。

**根因（代码证据）**：

- 问题模型是静态文档 `briefing.md`（八组问题，选项全部枚举写死）；`editor.html` 脑暴页是它的纯 UI 形态——`BRIEF_GROUPS`（`editor.html:5173–5213`）、`BRIEF_NARRATIVES`、`BRIEF_COVER` 为硬编码 JS 字面量；主题卡来自 `sync-themes.mjs` 构建期静态快照。
- 用户输入只进不出：`briefAnswers.topic` 全文件仅 3 处引用（存值 5276 / 拼简报 5468 / 进 JSON 5496），**从不参与任何选项生成、过滤、排序逻辑**。
- 这是"AI 在开发侧、页面内不含 AI 调用"红线的直接后果：动态性被整体推给了"提交简报之后的 Step 1/2"，脑暴阶段本身没有任何动态机制（连半成品都没有）。

**结论**：让选项随输入变化 = 新增一条"**agent 生成选项 → 注入页面渲染**"的通道。动态性全部在开发侧 agent（Bridge 态）或宿主系统（嵌入态）供给，页面只做渲染与采集，"页面内无 AI"红线不变。

## 2. 调研结论（source/ 横评）

| 机制 | 代表项目 | 做法 | 本方案取舍 |
|---|---|---|---|
| A. 固定骨架 + 选项实时生成 | tencent-pptx `human-alignment.md`（明令"禁止固定模板，必须结合用户具体主题生成问题和选项"） | 问题维度/优先级/缺省/跳过条件固定，问题文案与 2–4 个选项由 LLM 结合主题现场写 | **采用，作为主范式** |
| B. 静态目录 + 元数据筛选 | html-ppt（36 主题×受众映射）、dashi（12 主题×场景） | 选项预先策展，LLM 只做推荐 2–3 个 | 保留给主题/字体等"质量必须先验"的维度，与 A 混用 |
| C. 素材分析 → 内容画像 → 出题 | frontend-slides（逐图评估后出题）、tencent P4（有素材才问忠实度）、guizang（截图信号触发子问卷） | 问题从素材事实里长出来 | **采用**：agent 消化对话中的素材产出画像，素材驱动条件组 |
| D. 生成式视觉预览代替文字选项 | frontend-slides（真实单页预览）、tencent（用用户真实标题渲染封面缩略卡） | 不让用户用语言表达品味，直接看候选 | **采用纯 CSS 版**：主题卡用用户真实标题 + 主题 token 本地渲染封面缩略，不引入生图延迟 |
| E. 缺口驱动 + 缺省收敛 | open-design（已知信息汇总，目标问题数 0/1/2–3；skip 率 42% 的教训）、tencent（≤3 问 + 优先级表） | 已明确的一律不问，只问无法推断的 | **采用**：对话已明确的维度 prefilled，页面显示推断值可改而非重问 |
| F. 结构化 JSON 契约 + UI 渲染 | ppt-master（agent 写推荐 JSON → 确认页渲染 → 回执落盘） | agent 写 JSON，UI 渲染，提交即冻结契约 | **采用**：`brief.options` JSON 即契约，`brief.submitted` 冻结语义不变 |

## 3. 设计目标与不变量

**目标**：

1. 同一脑暴页，不同任务输入（主题/素材/受众/约束）呈现不同的问题文案、选项内容与推荐项。
2. 已能从对话推断的维度不再打扰用户（缺口驱动），用户成本下降而非上升。
3. 视觉类选项（主题）用用户真实标题做可视化预览，所见即所得。

**不变量（红线不动）**：

- 页面内无 AI 调用；纯静态、无框架、无构建、无外部依赖。
- Bridge 恰好五个 MCP 工具的公共契约不变（不新增工具；`open_editor` 增加一个可选参数不算新增工具）。
- `brief.submitted` 即冻结、Step 1/2 不二问的纪律不变；简报输出格式不变。
- 裸静态态（无 Bridge、无宿主）必须完全可用——静态问卷作为兜底永远存在。
- 嵌入协议只增不改：新增消息类型，既有消息语义不变。
- 首轮 `await_intent(86400)` 一次等待的纪律不变（本方案不新增脑暴阶段的 await 次数）。

## 4. 总体架构：单段注入式

```
对话上下文（指令 + 素材 + 附件，agent 自读）
        │ agent 消化 → 素材画像 + 缺口盘点 → 按 briefing.md v2 生成 brief.options JSON
        ▼
open_editor(view="brief", brief_options={...})     ← 现有五工具之一加可选参数
        │ daemon：schema 校验 → 落库（会话级存储）
        ▼
脑暴页打开 → 随会话状态拉取 brief_options
        │ 有 → 渲染动态问题组（定制）      无/非法 → 渲染静态问卷（兜底）
        ▼
用户作答 → brief.submitted（既有通道，格式不变）→ 冻结 → Step 1 页计划表
```

**关键决策**：

- **选项先于页面存在**。agent 在打开编辑器之前已完成定制，页面打开即是动态脑暴，无等待态、无新增往返、无新 intent 类型、无新 SSE 事件。这是对两段式回环方案的简化——输入本就在对话里，页面内再造素材入口是冗余。
- **覆盖语义**：对已打开会话再次调用 `open_editor(brief_options=...)` 可更新已存 options（agent 在对话中补充素材后重新定制）；页面每次进入 brief 视图时拉取最新值。P1 不做驻留页实时推送（见 §13 限制）。
- **上下文不足时**：agent 先在聊天里缺口补问（briefing.md 纪律本就允许），信息够了再开编辑器——不在页面里补救。

**已否决方案**：

- 两段式回环（页面内素材屏 → `brief.context` intent → agent 生成 → SSE 回推）：输入来源在对话而非页面，回环是冗余往返，且需新增 intent/SSE 并修订 await 纪律。
- `push_update` complete 携带 options 回推：该工具 schema 无结果载荷字段（仅 message/validation），不可实施。
- 页面内启发式/本地 LLM 生成：违反"页面内无 AI"红线。

## 5. briefing.md v2：问题模型改造

从"八组固定问卷"升级为"**维度池 + 实例化规则**"：

1. **维度池固定**：八个维度（场景/受众/来源与切分/页数预算/视觉风格/字体/动效明暗/封面交付）作为骨架保留——它们定义"问什么"；缺省值体系与派生规则（场景→密度/动效映射）不变。
2. **选项内容实例化**：每维度由 agent 按主题/素材现场生成 2–4 个选项，必须含：一个推荐项（`recommended:true` + 一句话理由）、一个缺省锚（`default:true`，回落到 briefing.md 原缺省语义）；禁止兜底凑数项、禁止向用户暴露推理过程（tencent 纪律）。
3. **优先级与缺口表**（新增，替代"一律全问"）：
   - P0 主题与核心目标——来自对话，不问；
   - P1 场景、受众、来源——对话/素材可推断则 prefilled，否则生成选项问；
   - P2 风格、字体、动效明暗——主题维度走"推荐 2–3 + 全库自选"（机制 B 混用）；
   - P3 封面元素、插画三态、页数预算——缺省质量高，一律可 prefilled；
   - **素材驱动条件组**：素材含大量数据 → 追加"数据呈现偏好"组；素材含品牌 VI → 追加品牌色映射声明确认；来源=pptx 转换 → 追加保真度组（tencent P4 模式）。条件组由 agent 判定触发，写进 options JSON。
4. **缺省驱动不变**：每组仍有缺省；未答项简报标（缺省）；追问上限两轮不变。
5. **风格回谏纪律不变**，前移到 options 生成时执行（推荐项即回谏结果）；品牌色不自定义 hex、映射最近变体的纪律不变。

## 6. `brief.options` JSON Schema（v2）

```jsonc
{
  "version": 2,
  "kind": "brief-options",
  "context_summary": "季度经营汇报，面向管理层，数据密集，含品牌红 VI",  // agent 对输入的一句话消化
  "profile": {                  // 素材画像（机制 C），页面展示用
    "signals": ["data-heavy", "brand-color", "audience:management"]
  },
  "groups": [
    {
      "id": "scene",                  // 维度池 id 固定枚举（八维度 + 条件组 id 白名单）
      "title": "使用场景",             // agent 可结合主题改写文案
      "impact": "决定密度与动效锚点",
      "state": "ask",                 // ask | prefilled | skipped
      "prefill_reason": "...",        // prefilled/skipped 时必填：推断依据一句话
      "multi": false,
      "options": [
        { "id": "report", "label": "汇报答辩", "desc": "限时讲完...", "recommended": true, "reason": "素材为季度经营数据", "default": false },
        { "id": "read",   "label": "阅读分发", "desc": "...", "default": true }
      ]
    }
  ],
  "theme_pick": {                     // 视觉风格维度的特殊载荷（机制 B+D）
    "recommended": ["e3/red", "c3/ink"],   // 2–3 个 主题/变体 id，编辑器渲染封面预览卡
    "reason": "经营汇报 + 品牌红 → 号外红变体",
    "library_open": true
  },
  "static_fallback": false            // true 时编辑器忽略动态内容按静态问卷渲染
}
```

- daemon 在 `open_editor` 携带该参数时做 schema 校验（version/kind/groups 结构、维度 id 在固定枚举内、每组 ≤6 选项、每选项 label/desc ≤120 字、prefilled/skipped 必带 prefill_reason），校验失败拒绝本次参数并返回错误（会话维持原 options 或回落静态）；不过拒内容质量。
- 简报输出格式（文本模板 + `kind:'design-brief'` JSON）**不变**——`bake_intent` 等既有字段口径不动，下游 Step 1/2 零感知。

## 7. Bridge 协议改动（bridge_core.py）

1. `open_editor` 增加可选参数 `brief_options`（对象，§6 schema）：daemon 校验后存入会话级存储（sessions 扩展列或独立 kv 表），会话状态路由返回值中携带 `brief_options`。
2. **覆盖语义**：同一会话重复调用带 `brief_options` 的 `open_editor` 时整体替换；不带该参数时保持原值。
3. 会话 phase 机不变（`briefing` → 冻结路径不动）；状态恢复时浏览器照常自动打开 brief 视图，打开时拉取最新 options。
4. 无新 intent 类型、无新 SSE 事件、无新 MCP 工具。协议文档（`editor-agent-bridge-protocol.md`）同步：open_editor 参数 +1、会话状态字段 +1。

## 8. 嵌入态与裸静态态

- **嵌入态**（宿主含 AI）：新增入站 `pptx-html:brief-options {options}`（§6 schema），宿主在加载编辑器后、用户打开脑暴页前注入；未注入则脑暴页按静态问卷渲染。既有 `pptx-html:brief` 出站不变。
- **裸静态态**：无注入源，直接渲染静态问卷（现有 `BRIEF_*` 数据保留为内建静态模型，即 schema 的 `static_fallback` 实例），页面形态与今天完全一致。

## 9. 编辑器呈现设计（editor.html 脑暴页改造）

### 9.1 页面结构（自上而下）

1. **画像卡**（有 options 时显示）：`context_summary` 一句话 + `profile.signals` 胶囊标签 + 「根据你的需求定制」徽标。让用户第一眼确认"agent 读懂了我的素材"。
2. **动态问题组**：数据源从 `BRIEF_*` 字面量改为"会话状态 `brief_options` → 渲染"；`renderBrief()`（5268–5387）与 `briefOptRow()`（5237–5258）参数化，静态字面量仅作 fallback 实例。
3. **主题卡组**：`theme_pick.recommended` 的 2–3 个主题渲染**16:9 封面预览卡**（纯 CSS：取主题 tokens 画迷你封面，标题用 `context_summary` 提炼的真实主题文字，装饰元素按主题 G9 母题 css 简化呈现）；「浏览全部主题」展开现有全库列表。
4. **提交区**：沿用既有提交三通道与 `briefObserveIntent` 状态机 UI，不变。

### 9.2 动态组三态

- **ask**：常规卡片组。推荐项带 ★ 徽标 + 一行理由（`reason`）；缺省项带「缺省」小标（复用现有视觉语言）。
- **prefilled**：折叠态一行——「受众：管理层（根据素材推断）· 修改」，点击展开为完整选项卡；顶部计数「已按你的需求预填 N 项」。
- **skipped**：收进页尾「未提及的维度」折叠区（展开可见缺省值），保证缺省披露透明（open-design 要求）。

### 9.3 回落与异常

- 无 `brief_options` 或 schema 非法 → 静态问卷渲染，无等待态（options 先于页面存在，不存在"生成中"）。
- agent 显式声明 `static_fallback:true` → 静态渲染但保留画像卡。
- 条件组渲染与普通组一致，组标多一个「因你的素材而问」徽标。

### 9.4 低成本路径与提交

- 每组保留「由 AI 决定」快捷项（= 接受 recommended/default）；顶栏一键「全部按推荐」。
- 提交后原位折叠为**简报摘要卡**（既有 `buildBriefExport()` 输出的人类可读版，含缺省披露），可「展开修改」重提交，走既有 `brief.submitted` 覆盖语义。

## 10. SKILL.md Step 0.5 更新要点

- 流程更新为：消化对话上下文（指令/素材/附件自读）→ 缺口盘点（不足先在聊天补问）→ 按 briefing.md v2 生成 `brief.options` → `open_editor(view="brief", brief_options=...)` → await `brief.submitted` → 冻结进 Step 1。
- 生成纪律写入 SKILL：每题 2–4 选项、必含推荐+理由、缺省锚定原语义、不暴露推理、素材条件组判定规则、品牌色映射纪律不变。
- 五工具 editor-first 红线、brief.submitted 冻结语义、首轮一次 await 纪律均不变。

## 11. 验收方案（tests/harness 新增）

- **T35a 注入全链路**：`open_editor(brief_options=...)` → 会话状态携带 options → 页面渲染断言（DOM 选项文本 = options 内容，非静态字面量）。
- **T35b schema 拒收**：非法 options（维度 id 越枚举/选项超字数/prefilled 缺 reason）→ open_editor 返回错误且会话原值不变。
- **T35c 无 options 回落**：不带参数打开 → 静态问卷渲染断言。
- **T35d 覆盖语义**：二次 open_editor 带新 options → 会话状态返回新值；不带参数 → 原值保持。
- **T35e 嵌入态**：入站 `pptx-html:brief-options` 注入 → 动态渲染断言；未注入 → 静态。
- **T35f 下游零回归**：动态简报提交后 `design-brief` JSON 与既有格式 diff 为空；k_brief 脑暴三态既有用例全绿。
- agent 侧生成质量（选项是否贴合素材）属人工目检项，记入 test_acceptance，不进自动断言。

## 12. 分期实施

- **P1（机制打通）**：briefing.md v2 + §6 schema + bridge `open_editor` 参数与落库 + 编辑器动态渲染三态 + 嵌入态入站消息 + SKILL Step 0.5 更新 + T35a–f。
- **P2（呈现升级）**：§9.1 主题封面预览卡 + 画像卡/胶囊标签打磨 + prefilled/skipped 折叠交互细节。
- **P3（质量迭代）**：按真实使用回收 options 质量样本，沉淀选项生成 exemplar 进 briefing.md；评估"内容明显指向时全 prefilled 的 0 问确认单"触发阈值；评估驻留页 options 更新推送（如需再加 SSE）。

## 13. 风险与限制

- **agent 生成质量参差**：选项贴合度依赖模型。缓解：schema 硬约束兜底、推荐项强制给理由（质量可审计）、静态问卷永远可回落；P3 用 exemplar 迭代。
- **页面内补充信息不重生成选项**：用户在脑暴页改主题/补充自由文本只进简报，不触发选项重生成（无回环）。如需定制更新须回对话告知 agent 后由其再次 `open_editor` 覆盖。此限制写入页内画像卡提示文案。
- **驻留页不实时更新**：options 在页面已停留 brief 视图时被覆盖，P1 不推送，刷新或重进视图生效；P3 评估是否加 SSE。
- **协议膨胀极小**：1 个可选工具参数 + 1 个会话状态字段 + 1 个入站 postMessage 类型；五工具、冻结语义、await 纪律全部不动。
