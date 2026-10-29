# imagegen v2 —— AI 生图体验整体优化设计

> 状态：**待评审**。本文是设计方案，评审通过后才实施。
> 诉求来源：2026-10-06 用户意见——"整体优化 AI 生图效果；pptx 是向下兼容，图片是向上突破视觉天花板的核心"。
> 前置阅读：`illustration-pipeline.md`（Step 5.5）、`page-render-mode.md`（Step 5.6）、`tri-form-architecture.md`（三形态总论）、`editor-agent-bridge-protocol.md`（intent 契约）。

## 0. 一句话结论

用户设想的六条能力中**四条已完整存在**（脑暴声明插画→占位槽位+预写 intent、一键自动补图、单页一键烙入+当前页截图作风格锚、混合 deck 双轨导出），**MCP 侧无需新增工具**。真正的缺口是八处体验与质量短板（§3 G1–G8），本设计逐一给出方案。

## 1. 现状能力盘点（证据级）

### 1.1 用户诉求 ↔ 现有能力对照

| 用户诉求 | 现状 | 证据 |
|---|---|---|
| 脑暴选 AI 插画 → 生成 HTML 时预留插画位置 | ✅ 已有。脑暴第⑧组含插画模式单选；生成期写入图片槽位三属性占位 | `references/briefing.md:31`；`references/editing-contract.md:113–135` |
| 占位处写入"要呈现的内容/生图指令" | ✅ 已有。`data-image-intent` 即槽位级生图指令片段 | `editing-contract.md:127` |
| 页面提供一键生成插画按钮 / 免交互直接生成 | ✅ Bridge 模式已有「自动补图」按钮（扫 placeholder 槽位发 `illustrate.requested` intent）；agent 侧逐槽生成无需用户逐张确认 | `editor.html:752,6319–6322`；`SKILL.md:84` |
| 单页一键生图、以当前页为参考图 | ✅ 已有。Bridge 栏「整页重绘」→ `bake.requested`；风格锚 = 真实 HTML 页浏览器截图（非另一张生图） | `editor.html:751,6318`；`SKILL.md:282`；`page-render-mode.md:48` |
| 作为技能一部分 / 或提供 MCP 工具 | ✅ 两者都已成立。生图是技能子流程（Step 5.5/5.6 + `imagegen-adapter.py`）；Bridge 六种 intent 已含 `bake.requested`/`illustrate.requested`，恰好五工具完整承载，**不需要第六个 MCP 工具** | `tools/bridge_core.py:64`；`tools/bridge_mcp.py` |
| 部分页图片、部分页 HTML 混合 | ✅ 已有且是回归验收项（bake-mix fixture：4 页混合 deck） | `tests/decks/bake-mix/`；harness m/n/p/q 各 check |
| 生图色彩与原 HTML 一致 | ⚠️ 只有前置约束：指令注入主题 token 逐字色值 + 参考图锚定；**无后置机器校验** | `compile-bake-prompts.py:52–69`；`bake-prompts.md:52` |
| 导出 pptx 特殊处理 | ✅ 已有。保真轨 baked 页 PNG 直通；可编辑轨整页短路为满幅 p:pic；certify 位图豁免 | `export-pptx.py:586–663`；`export-pptx-editable.py:244–249,1523–1533`；`certify-pptx.py:20,72` |
| 尺寸与原 HTML 一致 | ✅ 已有。三方绑定（槽位比例↔画布 1920×1080↔生图 2560×1440，容差 5%）+ adapter 像素级验收 | `editing-contract.md:186`；`imagegen-adapter.py:327–342`；`check-images.mjs:213–243` |
| 图片的出现/消失动效 | ❌ 缺失。烙入页整图与插画槽位均无入场动效约定；PPTX 导出现状为静态化（FREEZE_JS / animation:none） | `export-pptx.py:248–261`；`export-pptx-editable.py:654–663` |

### 1.2 生图链路既有质量机制（不要重复造）

- 七节指令模板（Canvas / Deck Goal / Global Style / Style Anchor / Text / Layout / Constraints），Text 节 100% 逐字来自 manifest 防幻觉；脚本管确定性骨架，agent 管 Layout 与风格段（`compile-bake-prompts.py:36–104`）。
- 代表页审批闸门：先烙一页（封面优先）→ 用户确认 → 才批量（`SKILL.md:284`）。
- 失败对策表 + 重 roll 纪律（至多 2–3 次，不过即回退 HTML 页 / 保持 placeholder 诚实回退，禁冒充）（`bake-prompts.md:54–64`；`SKILL.md:255–261`）。
- 受控 adapter：staging→校验→原子发布、不自动重试（防重复计费）、ledger 证据账本、双档模型（flare / sunburst 重 roll）（`imagegen-adapter.py`）。
- stale 闭环：源层参与 content-hash → 编辑器过期水印 → 用户触发重烙，不自动重烙（`editing-contract.md:185`）。

## 2. 设计目标与非目标

**目标**：把"生图"从"流程上能跑通"提升到"效果上够到视觉天花板"——一致性可机器验证、质量有评审标尺、动效有表达力、各入口形态体验拉齐。

**实现后用户可见的结果**（成功标志）：

1. 脑暴环节可直接声明"混合烙入"及烙入页意向清单，生成的 HTML 对烙入页已按满幅构图预留设计，不再事后补救。
2. 每张 AI 生成图都经过色彩一致性机器校验，色偏有告警记录可追溯，不再是纯肉眼把关。
3. 代表页以双候选择优后呈现，审批页质量不再依赖单次运气。
4. 烙入页整图与插画在 HTML 演示态有入场动效；PPTX 导出为静态终态并在交付说明中明示。
5. 嵌入态与裸静态态也有显性生图入口与结果回流，不再只有 Bridge 模式可用。

**非目标**（明确不做）：
- 不在编辑器页面内做任何生图调用（"转换即技能"红线不变；编辑器永远只表达意图）。
- 不新增 MCP 工具；不改 intent 状态机与 lease/发布机制。
- 不在 PPTX 导出中写入动画 XML（PPTX 动效保真度不可控，静态化是既定诚实降级）。
- 不做"背景生图+文字叠加"混合态（既有硬规则不变）。

## 3. 缺口清单与方案

### G1 脑暴缺失"烙入策略"声明（混合形态无法前置规划）

**现状**：脑暴第⑧组只有"纯 HTML / AI 插画"二选一；烙入只能在 Step 5.6 逐页临时选定，导致生成期不为烙入页做构图预留（文字量控制、满幅构图），Step 5.6 的"选页把关"只能事后补救。

**方案**：第⑧组升级为三态 + 一个条件追问：

1. `纯 HTML`（缺省）/ `AI 插画` / `混合烙入`。
2. 选 `混合烙入` 时追问一句："哪些页适合做整页视觉（通常：封面、章节扉页、收束页）？"——缺省驱动：用户不答则按"封面+各章节扉页+收束页"缺省。
3. 简报输出增加 `烙入：<页清单|缺省>` 字段；Step 1/4 呈现发散时对清单内页面按"理想文字量 = 大标题+一行副题+一行标注"的烙入构图约束设计（`bake-prompts.md:9` 的选页把关从事后变为前置）；Step 5.6 直接按冻结清单执行，代表页闸门不变。
4. Bridge 模式映射：`brief.submitted` 冻结时携带 `bake_intent: string[]`（页 id 清单），Step 5.6 免再问。

**改动面**：`references/briefing.md`（第⑧组+简报格式）、`SKILL.md` Step 0.5/5.6 衔接句、编辑器脑暴浮板对应问题项（与 briefing.md 同一问题模型的既有约定）、harness brief 相关断言。

### G2 色彩一致性只有前置约束、无后置校验 ★质量核心

**现状**：Global Style 节注入 token 色值 + 参考图锚定，属于"叮嘱"；生成图是否真的没有色偏，全靠 agent 肉眼。

**方案**：新增 `scripts/check-image-harmony.py`，**复用 check-render 的无头浏览器通道提取色板**（页面内 canvas 缩采样 64×36 → 中位切分法取 5–8 主色），不在纯 Python 里解码 JPEG/PNG（stdlib 无法解 JPEG，自写解码器是深坑）——与"浏览器即编译器"的既有路线一致：

1. 对每张 `data-image-state="generated"` 的图（槽位图 + 页面级烙入图）经浏览器 canvas 提取主色板，输出 JSON；脚本主体只做色彩数学。
2. 与 manifest theme tokens（`--paper/--ink/--accent` 等）做双向最近色 **CIEDE2000** 校验，两项指标：
   - **指标 A 无锚率**：主色中"距全部 token 最近色 ΔE00 > 32"的占比 > 40% → 告警（发明新色过多）。
   - **指标 B 缺席**：`--accent` 在主色板中无 ΔE00 ≤ 24 的呼应色 → 告警；烙入满幅页豁免 `--paper/--ink`（背景色被画面覆盖是合法的）。
3. 处置：单图触发 A 或 B → **告警不阻断**（压暗/叠色等艺术化处理是合法偏离），进 ledger 与交付说明；deck 内 ≥50% 的图同时触发 A+B → 升级阻断，要求风格段重写后重 roll。阈值 32/24/40%/50% 为初值，真实生图验收（G8）后用实测分布校准一次。
4. 接入点：Step 5.5/5.6 回归校验第四项（渲染/check-images/hash 之后）；Bridge complete 的 `images` check 证据不变，harmony 作为 images check 的内部步骤，**不新增 check 枚举**（避免动 bridge_mcp 契约）。
5. **可确定性验收**：新增 `tests/decks/harmony-fixture/`——合成 PNG（一张纯 token 色构成、一张纯无关色构成、一张混合）+ 对应 deck，断言 A/B 指标命中/豁免，全程不依赖付费生图。

**改动面**：新脚本 + `SKILL.md` 两 pass 校验清单 + harness 对应子检查（复用 m/l 框架）。

### G3 生图质量评审无标尺，择优靠直觉 ★质量核心

**现状**：失败模式对策表覆盖"坏了怎么办"，但没有"多张里哪张好"的择优机制；adapter `--n` 支持多张却无人评审。

**方案**：

1. **生图评审 rubric 入库**（进 `bake-prompts.md` 新一节）：五维打分——①文字逐字渲染正确（一票否决）②构图符合 Layout 节谱系 ③色彩在场（与 G2 呼应）④风格段气质匹配 ⑤无不许可元素（页码/水印/画框/出血）。（v3 升维转向后增第六维"视觉升维"，见 §7。）
2. **代表页多候选**：代表页（审批闸门页）默认 `--n 2` 生成双候选，agent 按 rubric 选定后才进入用户审批；批量页 `--n 1` 降成本，rubric 任一一票否决项失败才按既有重 roll 纪律重试。
3. rubric 结论记入 ledger（每维 0/1 + 一句话理由），交付说明可追溯。

**改动面**：`bake-prompts.md`、`SKILL.md` Step 5.5/5.6、`imagegen-adapter.py` 调用参数约定（仅技能层，不改脚本逻辑）。**成本决策（用户已批准 2026-10-06）**：接受代表页 `--n 2` 双候选带来的成本翻倍，批量页保持 `--n 1`。

### G4 图片入场/退场动效缺失 ★用户点名

**现状**：烙入页整图与插画槽位都是"静默出现"；骨架动效词汇库 8 族的 enter 族未对图片元素做约定；导出现状静态化（正确，不动）。

**方案**（HTML 侧表达力，PPTX 侧诚实降级）：

1. **契约**：editing-contract 升级 v8——页面级烙入 img 与 `data-editable-image` 槽位图允许携带 enter 族动效标记（沿用 `data-anim`，白名单限定 enter 族子集：`fade / rise / zoom-in / curtain`，禁用 text 族与 ptr/scroll 族）；动效参数（时长/延迟/缓动）走既有 motion recipe，不发明新参数面。
2. **骨架**：确认 skeleton 运行时对 `<img>` 元素的 enter 族支持（拆字类天然不适用，遮罩/位移/缩放类应通用；不支持则补齐为纯 CSS class 方案，零 JS 依赖降级）。
3. **净化清单**：序列化净化与导出 FREEZE 已覆盖终态回滚，需回归确认 img 入场动效在 freeze 后呈终态（`export-pptx.py` FREEZE_JS / editable 轨 `animation:none` 均已有，预期零改动，但必须进 harness 断言）。
4. **纪律**：每页至多 1 个图片入场动效；烙入页整图动效时长 ≤0.8s（整页大图动久了晕）；插画槽位动效随所在页编排，不独立加延迟堆叠。
5. **PPTX 侧**：维持静态化，交付说明固定话术"图片动效为 HTML 演示态专属，PPTX 导出为静态终态"。

**改动面**：`editing-contract.md` v8、`motion.md` enter 族适用元素表、`skeleton.html`（如需）、harness 渲染/导出断言。

### G5 非 Bridge 形态的生图入口与回流不齐

**现状**：Bridge 模式按钮齐全；嵌入态只发 `pptx-html:illustrate-intent`/`export-intent` 出消息，结果回灌无协议（靠宿主重发 load）；裸静态态复制指令文本（可接受）；`editor.html:6501` 协议注释漏记 `:design` 与 `:illustrate-intent`（文档与实现不同步）。

**方案**：

1. **协议补全**：嵌入协议出站正式收录 `pptx-html:illustrate-intent {slots}` 与 `pptx-html:bake-intent {slideIds}`（bake 当前在嵌入态无独立出站消息，复用 export-intent 语义不清晰，应独立）；入站新增 `pptx-html:assets-changed {files}`——宿主完成生图/换图后通知编辑器热刷新指定资产，不必整页 reload。
2. **嵌入态按钮显性化**：「整页重绘」「自动补图」按钮从 Bridge bar 专属改为三态可见（Bridge 态发 intent / 嵌入态发 postMessage / 裸静态态复制指令文本），文案随形态自适应。
3. 修正 `editor.html:6501` 注释与实际出站消息清单同步。

**改动面**：`editor.html`、协议文档（AGENTS.md 宿主集成段、`editor-agent-bridge-protocol.md` 嵌入协议节）、harness 嵌入态用例。

### G6 本地无 agent 生图通道（与 convert 通道不对齐）

**现状**：daemon 有 `/api/convert` 本地通道（`--convert` 显式启用）；bake/illustrate 无对应通道——无 agent 在场时页面按钮死路。

**方案**：`edit.py` 增加 `--imagegen` 显式开关（与 `--convert` 同纪律：默认关、须显式启用、启用时打印计费警示）。**provider 解析是无 agent 场景的新问题**：adapter 的 `--provider-script` 原本由 agent 在运行环境解析，本地通道改由配置供给——环境变量 `PPTX_HTML_IMAGEGEN_PROVIDER` 或 `.pptx-html/config.json` 的 `imagegen_provider` 键，二者皆缺则 `--imagegen` 启用失败并明示原因（路径不落盘 ledger 的既有纪律不变，config 仅存本机路径且 `.pptx-html/` 本就在交付物之外）。daemon 侧 `start_local_imagegen` 复用 intent 队列直接落 `illustrate.requested`（slots=全部 placeholder）；执行体仍是技能脚本（adapter + compile-bake-prompts），daemon 只做编排——"转换即技能"红线不破，与 convert 通道同构。

**纪律**：本地通道**只做插画补齐**，不做烙入（烙入必须过代表页审批闸门，无人审批的整页生图风险与成本都不可接受）。**范围决策（用户已批准 2026-10-06）**：做，放 P2。

**改动面**：`tools/edit.py`、`tools/bridge_core.py`（局部）、howto 文档。

### G7 分辨率只有比例校验、无绝对下限

**现状**：check-images 三方绑定只校验比例（容差 5%），不查绝对分辨率；一张 640×360 的 16:9 图能过静态门。

**方案**：check-images.mjs 增加绝对像素下限——页面级槽位 ≥2560×1440（与 Canvas 节/adapter `--expected-size` 对齐，此项 adapter 已查，静态侧补齐双保险）；页内槽位下限按槽位声明尺寸 ×2（ retina 2x 基准）推算。超标即错误（此项无合法偏离）。

**改动面**：`check-images.mjs`、`editing-contract.md` 槽位节一句话。

### G8 真实生图端到端从未正式验收（UNKNOWN 不可带进 v2）

**现状**：AGENTS.md 与验收矩阵 MAN-04 均记录"真实生图 UNKNOWN——harness bug 已修但未再次付费调用，须用户另行授权"。

**方案**：v2 任何一项实施落地的验收前置 = 用户授权后完成一次真实付费生图端到端（插画模式 + 烙入模式各至少一页），证据补进 `docs/test_acceptance/editor-agent-bridge.md` §16 MAN-04。在次之前，v2 文档与汇报中涉及生图效果的表述一律保持 UNKNOWN 口径，**不得把新设计写成已验证**。

## 4. 与既有红线的对齐检查

| 红线 | 本设计是否触碰 |
|---|---|
| 转换即技能（编辑器/服务不含生图逻辑） | 不触碰。G5/G6 均为"表达意图/编排"，执行体永远是技能脚本 |
| 恰好五 MCP 工具 | 不触碰。全部新能力复用现有 intent 类型与 checks 枚举 |
| HTML 唯一真相源 | 不触碰。烙入源层保留、stale、回退机制不变 |
| 不存在"背景生图+文字叠加"混合态 | 不触碰。G4 动效只作用于既有两种形态各自的图片元素 |
| canonical hash 两端逐字一致 | G1 若 bake_intent 进 brief JSON 不碰 hash；G4 动效标记进 DOM 需同步 canonical 规则时两端同改（契约纪律已覆盖） |
| 凭证不入文档、provider 路径不落盘 | 不触碰。G2/G6 沿用 adapter 既有纪律 |

## 5. 实施分期建议

| 期 | 内容 | 理由 |
|---|---|---|
| P0 | G8 真实生图验收 + G2 色彩后置校验 + G3 评审 rubric | 用户核心诉求是"效果"，先把质量闭环钉死；G8 是全部验收前置 |
| P1 | G1 脑暴烙入策略 + G4 图片动效 | 体验表达力；G4 涉及契约 v8，需与编辑器同步发版 |
| P2 | G5 嵌入态协议补全 + G6 本地生图通道 + G7 分辨率下限 | 形态拉齐与加固；不阻塞质量主线 |

每期验收仍走 `python3 tests/harness/run_e2e.py` 全量 + 对应新子检查：

- P0 新增 `r_harmony_check`（harmony-fixture 确定性断言，不依赖付费生图）+ bake-mix fixture 扩充 rubric 账本断言；G8 真实生图证据进 `docs/test_acceptance/` 单独记录。
- P1 新增 brief 三态与烙入清单断言（复用 T1/brief 框架）、图片动效渲染断言与 freeze 终态断言（进 j/n/p 子检查）。
- P2 新增嵌入态 `assets-changed` 回流用例、`--imagegen` 本地通道用例（provider 打桩，不真实付费）、分辨率下限断言（进既有 images 子检查）。

真实生图相关证据按 G8 口径单独记录，不混入代码回归 PASS。**分期决策（用户已批准 2026-10-06）**：P0 质量闭环优先，P1 体验表达力，P2 形态拉齐。

## 6. 不做清单（本次明确排除）

- 编辑器内嵌生图 UI（参数调节、缩略图墙等）——编辑器只表达意图。
- PPTX 动画 XML 写入。
- 自动 stale 重烙（维持用户触发）。
- 背景生图+文字叠加混合态。
- 第六个 MCP 工具。

## 7. D1–D3 试点实施记录（2026-10-07，风格圣经）

来源：`docs/research/bake-sota-dissection.md`（codex 七手法解剖；结论：管线不弱于 SOTA，差在指令内容层）。切入点"试点 + A/B 重烙"已经用户批准。

### D1 风格圣经 Schema（themes.md 单源）

- 新字段组 `**bake_brief**`（json 围栏块，七层栈的生图翻译层，不进 HTML 产物、不进编辑器面板 JSON）：`visual_direction`（一句英文定调）/ `palette_rule`（色彩行为负向规则，禁字面 hex——色值主权在 G1）/ `typography_bake`（标题重构词汇，按主题气质定制）/ `allowed` / `avoid` / `layout_blueprints`（页角色 → 位置×数量×标签，cover/divider/key-message/analysis 四角色必填）/ `rendering_constraints`（≥8 条）。
- sync-themes.mjs 校验第 10 项：试点主题（e3/c3/a1，常量 `BAKE_BRIEF_REQUIRED`）必填、其余暂可选，铺量后一视同仁；形状校验到蓝图 section 粒度。面板输出不变（editor.html 同步幂等零改动验证过）。
- 试点三主题（气质反差最大跨度）：**e3 装饰艺术**（对称仪式奢华）、**c3 终端绿**（CRT 磷光等宽）、**a1 电子杂志**（双色墨水纸面）。

### D2 bake-prompts.md §6

六构图谱系保留为无简报主题的回退写法；新增 §6.1 页角色→蓝图选用规则（plan `role` > slide id 关键词 > 文本量推断；蓝图回落链 closing→key-message→首个蓝图）、§6.2 标题重构词汇表（细线结构笔划/半空心/断笔/延笔/隐喻融字，字面完整可读为底线）、§6.3 每页恰一个主导隐喻（motifs.md 八类进指令主链路的桥）、§6.4 词预算（回退散文 80–120 词 / Layout ≤150 词 / 禁 tag-soup）。

### D3 compile-bake-prompts.py v2

- Global Style：主题有简报时注入**单行紧凑 JSON**（去缩进 token 最省、ensure_ascii=False 防 \uXXXX 膨胀；分节 markdown 等价内容约多 30% token，弃）；无简报回退散文+token（向后兼容，bake-mix fixture 无 theme-id 元信息即回退路径，m_bake_check ③ 原断言全过）。
- Layout：首行页角色声明（含来源标注）；简报有该角色蓝图时注入蓝图块。
- Constraints：通用五条不变 + 六条通用反 AI-slop 清单（禁 mesh 渐变/aurora/浮球/玻璃拟态/自媒体海报感/无主张模板构图/chrome/图标排排坐/圆角卡片网格，"对称居中"条款为主题性对称留了母题承载的出口）+ 主题 avoid 一行。
- 幂等性不变；manifest theme 字段消费方式不变。

### A/B 真实生图验证（demos/imagegen-v2 封面，E3 墨绿金）

- 调用：1 次真实调用（`--n 2 --quality high --size 2560x1440`，参考图 = 真实 HTML 封面截图 anchor-cover.png），flare 模型，经 imagegen-adapter.py，产物落临时 deck 后复制进 `demos/imagegen-v2/ab/`（不改 demo deck 发布状态：A 组 = 现有 `assets/page-cover.png`）。
- 机器证据：check-image-harmony（临时 deck，不污染正式 ledger）——A 组指标 B 告警（accent 金无呼应，最近古铜 ΔE 24.34 出界）；B 组两候选 0 告警（无锚率 0%，金色呼应贴阈值 ΔE 20.9/23.6——金线偏象牙香槟，过线但勉强，已写入 rubric color 维理由）。
- OCR 证据（easyocr CPU，zh_sim+en）：**A 组一票否决维失败**——署名行『衡庐基金』渲染为『天弘基金』（conf 0.87，模型凭"基金"先验 hallucinate 知名公司名）；B 组两候选四行中文全部逐字正确（0.64–0.98）。kicker 因 ≥.3em 宽字距 OCR 拆散不可判，非渲染错误证据，目检终裁。
- rubric 结论：`demos/imagegen-v2/ab/rubric.json`——A 组 reject（文字+色彩双败），B 组两候选机器维全过 accept；layout/style 维无机器视觉工具，最终入选由用户目检终裁；本 A/B 不替换 demo deck 发布状态。

### 升维转向（2026-10-07 用户目检裁决后的语义重定义）

**用户裁决**：B 组与 A 组视觉几乎无差异，不达标。新定位（原话转述）：参考图只给出文字与基本视觉信息，生图的任务是**视觉升维**——插画化、布局重构、文字视觉化改造、全面超越原 HTML；"因为有参考图所以内容要参考，但效果要更好"。

**归因四条**：

1. 编译器 Style Anchor 节写"匹配其配色/字排/密度/质感"——把参考图设为临摹目标，i2i 场景下这是最高权重指令，压过风格圣经；
2. E3 简报 cover 蓝图与 HTML 页既有构图天然同构（同源主题语言），指令目标=参考图现状；
3. 全指令只奖励一致、无条款授权超越，蓝图成了复刻纪律；
4. i2i + flare 的保真倾向放大保守性。

**语义重定义（烙入 = 内容忠实 + 视觉升维）**：

- `bake_brief` 新增 **`uplift`** 必填字段（试点三主题）：该主题从扁平 HTML 到图像级画面的升维路径——漆面纵深/金属刻痕（e3）、CRT 余晖发光/玻璃曲率/扫描线纵深（c3）、纸纤维/油墨压痕/透印（a1）；禁泛词。
- 编译器 v3：Style Anchor 节改写为"内容锚"（只对齐文字/层级/色系，明示"不代表目标视觉效果……构图可重新设计"）；Layout 节蓝图后加构图授权行；Text 节补文字视觉化改造授权；`--anchor none` 支持纯文生图臂（Style Anchor 整节省略）。
- bake-prompts.md：开头语义段改写；§0 原则 3 改为"参考图是内容锚不是风格目标"；rubric 升六维——新增"视觉升维"维（与参考图趋同视为失败，无机器裁判，目检执行，此维 0 视同 reject）。
- 保真封存需求由保真导出轨（HTML→PPTX 的 PDF/SVG 轨）承担。

**C 组双臂实验**（demos/imagegen-v2 封面，E3 墨绿金）：C1 = 新内容锚指令 + 参考图；C2 = 纯风格圣经驱动、不传参考图。指令副本 `ab/c1-cover.md` / `ab/c2-cover.md`，产物 `ab/c1-cover.png` / `ab/c2-cover.png`，harmony + OCR + 六维 rubric 见 `ab/rubric-c.json`。

**C 组机器证据结论**：两臂各一次调用成功（尺寸/格式/比例全过）。harmony 双臂零告警且金色锚定大幅改善——C1 金 #d1bb8c 对 --accent ΔE 13.77、权重 7.9%（B 组最好成绩是象牙色贴阈值 20.9）；C2 无参考图臂色彩未脱锚（金 ΔE 17.5），"C2 色彩脱锚"风险未出现。OCR 两臂四行中文全部逐字正确（C2 置信度显著更低：标题 0.02——无参考图锚定字排后重构风格化更强，可读性风险记录在案）。升维代理指标：文件熵从 A/B 的 ~1.2MB 跃升到 C1 4.16MB / C2 3.85MB；主色板暗色 top2 权重从 ~90%（扁平）摊平到 38%（漆面明暗纵深出现）。升维终裁（rubric 第六维）无机器裁判，由用户目检。

**C 组用户裁决（2026-10-08）**：双臂都有提升，**通过**；默认策略定为 **C1 臂**（带内容锚的升维指令）。

### 高密度页压力测试（2026-10-08，D 组）

动机：封面只验证了低文字量仪式页；高密度中文文字页的升维与逐字渲染是烙入真正的风险敞口。测试副本 `demos/imagegen-v2-dense/`（cmb-retail 54 页 deck 的副本，fixture 本体未动；该副本因含真实公司内容已于 10-08 脱敏重构为 3 页中性题材 deck——虚构"珩云科技×恪远控股"云服务方案， dense 页结构与文本量保持，D 组结论仍然有效）。

- **选页**：按 manifest 文本量统计取全文最密页 `allocation-solution`（38 条非家具文本、922 字符——7 个编号能力块 + 3 个服务段落 + 脚注）。注：任务前提"cmb-retail 用 E12"与事实不符——该 deck 实为 **B1 瑞士国际主义**（token 与头部注释为证，E12 只是蒸馏时参考了其高密度边界纪律）；故本次简报写 B1（测试用）+ E12（任务点名，入库备用）两份。
- **编译器配套修正**：Text 节排除 furniture 角色（页眉/页码是 chrome，Constraints 明禁渲染，进文字契约自相矛盾）；副本补 `theme-id` meta（fixture 无此 meta）。
- **调用**：flare `--n 2 --quality high`（内容锚 = 该页 2560×1440 截图）；文字问题超阈后按纪律重 roll 一次升级 **sunburst** `--n 2`——本组共 2 次调用。
- **证据与结论**：flare/sunburst 各两候选的 harmony + OCR 38 行全行比对 + 六维 rubric（原 rubric-dense.json 与候选图因含真实公司名，已在 10-08 脱敏重构中随旧副本一并退役——结论以本节文字为准）。
- **结果**：四候选全部 reject（text_exact 一票否决）——模块名/编号/短标签全部正确、harmony 零告警（IKB 锚定 ΔE≈9–10、权重 ~10%）、升维信息熵在场（2.4–4.1MB），但 >30 字长句系统性截断/掉段且两模型同症。结论一：§0 文字量纪律被实证——922 字符/38 行超出可靠逐字渲染，此类页诚实回退 HTML；结论二：升维机制在高密度页同样生效，瓶颈纯粹在文字量。不建议发布为正式烙入页。

### v4 收紧与 E 组双臂（2026-10-08）

**用户目检 D 组裁决**（原话要点）：升维不明显，候选图受参考图影响还是太大——指令中应更明确"对参考图的参考只在内容和配色"，升维要显式增加光线、质感、插画、优化布局、容器、字体等维度。

**编译器 v4 变更**：① Style Anchor 节重写为"只提供①文字内容与信息层级②配色基调，其余一律不参照……与参考图在构图或质感上趋同，视为失败"；② 新增「Uplift 升维手段」节（六维工具箱：光线/质感/插画/布局/容器/字体），回退路径同样携带；③ Layout 构图授权行保留。bake-prompts.md（参考图六字诀"只内容与配色"）、SKILL.md、page-render-mode.md §4 同步。

**E 组双臂**（各 1 次调用，flare/high/n=1/带内容锚）：

- **E1 封面臂**（E3）：`demos/imagegen-v2/ab/e1-cover.png`（+指令 `e1-cover.md`、rubric `rubric-e1.json`）。harmony 零告警（金呼应 ΔE 19.0，暗绿 5+ 档色阶无垄断档）；OCR 四行内容文字全对；文件熵 3.90MB。rubric accept，v4 vs v3 升维差异待目检。
- **E2 高密度臂**（B1）：`demos/imagegen-v2-dense/e2-allocation.png`（+指令 `prompts/e2-allocation.md`、rubric `rubric-e2.json` 含 38 行全行比对）。harmony 零告警（IKB ΔE 10.33）；OCR exact 18/38——与 D 组同 band，长句截断同症未消（QDII 行已修复为全对）；text_exact 一票否决维持 reject。结论：**v4 措辞影响的是视觉升维幅度，不改变高密度文字渲染的结构性瓶颈**。
- 三联对比图：`ab/compare-cover-v4.png`（HTML anchor / v3 C1 / v4 E1）、`demos/imagegen-v2-dense/compare-dense-v4.png`（HTML anchor / D 组胜者 sb-1 / v4 E2；D 组胜者面板因含真实公司名已在脱敏重构中退役，该拼图同步重制）。

## 8. 场景矩阵实验与布局重构（2026-10-08，已实施）

- **三场景烙入实验**（B1 × gallery 中性页）：信息图页、对比页 accept（结构/数值对位保持）；定量图表页 reject（数字错、减号丢失、柱高误差 10–26%）→ bake-prompts §0 新增「定量图表页禁整页烙入」纪律；文字量上限实测固化（905 字符长句系统性截断）。
- **布局重构（编译器 v5）**：plan.json 页级 `restructure: true` 触发重构授权段——授权把平铺直叙文本重组为结构化信息图（文字逐字保留/层级/配色不变为硬约束）。中密度实验页（395 字符平铺散文）双候选均真重构为编号节点信息图，字符覆盖 99–100%。bake-prompts §6.5 适用三条件 + 伪重构失败模式入库。
- 烙入适用地图：封面/扉页 ✅、中低密度平铺文本 ✅（重构）、信息图/对比 ✅、定量图表 ❌、高密度文本 ❌（留 HTML）。
- 证据与全量数据：`../progress/1008_imagegen_scenes_test.md`。

### §8 追记：H 组装饰升维 + G 组数据强锚定（2026-10-08 晚，用户修正后）

- **H 组（高密度页装饰升维，编译器 v5 `decorate: true`）**：高密度页从"禁烙"修正为"内容不动 + 氛围升维"——授权段四项范围（布局节奏微调/底部边缘插画背景带/母题角饰/光与质感作用于背景容器）+ 文字区对比度硬约束。实测（905 字符页）：装饰克制（边缘密度 13–15% vs 中部 13%）、文字可读性不劣化、harmony 零告警 → accept。
- **G 组（图表页数据强锚定）**：逐点数值+百分比比例写进 Layout 后，**文字层收敛**（数值/副题/减号全对）但**几何层不收敛**（柱高误差最大 −31%）——§0 定量图表页禁烙纪律维持，§6.7 记录强锚定写法与"文字可锚定、几何不可锚定"的证据边界。
- 烙入适用地图更新：封面/扉页 ✅、中低密度平铺文本 ✅（restructure 重构）、信息图/对比 ✅、高密度文本 ✅（decorate 装饰升维，仅氛围）、定量图表 ❌（维持）。
- 证据：`../progress/1008_imagegen_scenes_test.md` H/G 组节；产物 `demos/imagegen-v2-dense/e3-allocation-decorate.png` + `demos/imagegen-v2-scenes/baked-profit-waterfall-v2.png`。
