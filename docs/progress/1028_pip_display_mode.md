# 1028 · pptx 接入宿主 pip 呈现形态（脑暴 inline、其余三视图 pip）

> **状态**：**pptx 侧已实施并自测通过（2026-10-28）**；**框架侧需配合一处改动**（见 §4，属 SproutHarness 仓库）
> **日期**：2026-10-28
> **依据**：宿主设计 [`docs/design/agent/mcp_apps_pip_panel_design.md`](../../../../SproutHarness/.claude/worktrees/feature+mcp-apps/docs/design/agent/mcp_apps_pip_panel_design.md)（§一 形态归属、§二 布局）· [`mcp_apps_design.md` §十五](../../../../SproutHarness/.claude/worktrees/feature+mcp-apps/docs/design/agent/mcp_apps_design.md)（§15.2 D1–D9 决策、§15.3 交叉校验、**§15.10 给 pptx 的清单**）
> **背景**：宿主新增 pip（停靠式宽侧栏）形态，并按「工具的 `_meta.ui.mode`」分流 inline/pip。宿主设计 §一 明确：**脑暴/图表/表单 = 一次性 widget → inline；编辑器/画布 = 常驻工作台 → pip**。

---

## 1. 结论

| 项 | 结论 |
|---|---|
| 脑暴 inline、其余三视图 pip | **正确**，且与宿主设计 §一 的分类一致；**§15.10 现在给 pptx 的清单写的是"整工具 pip"**，与 §一 自相矛盾，本轮一并厘清 |
| 为什么不能只写 `mode='pip'` | pptx 是 **"一工具四视图"**：`open_editor` 一个工具承载 `brief/edit/annotate/export`，而 `mode` 是**工具级静态**声明（§15.2 D2：形态必须在挂载前确定）→ 表达不了"按视图区分" |
| 解法 | 新增**可选**宿主扩展 `_meta.ui.mode_inline_when = {"arg":"view","in":["brief"]}`：宿主在**发射 mcp_app 时用本次 tool_args 求值**——命中则 inline，否则用 `mode`（=pip）。仍是"挂载前确定、运行时不切换"，不违反 D2 |
| 兼容性 | 框架**今天**忽略未知字段 → 一切 pptx 视图按 `mode='pip'` 挂载（等于方案 B），**不会降级**；框架补上求值后，脑暴自动回落 inline。**前后都安全** |

## 2. pptx 侧改了什么

| 文件 | 改动 |
|---|---|
| `tools/bridge_mcp.py` · `_tool_meta()` | `open_editor` 的 `_meta.ui` 补 **`mode="pip"`** + **`mode_inline_when={"arg":"view","in":["brief"]}`**（app-only 工具**不带**形态声明——它们不渲染 View） |
| `tools/bridge_mcp.py` · `VIEW_BOOTSTRAP` | 引导期补 `api.onHostContextChanged`（与 onToolInput/onToolResult 同构：注册期可能早于 bundle 安装） |
| `tools/ext_apps_facade.js` | ① `new App(appInfo, { availableDisplayModes: ["inline","pip"] })`——**此前只传了第一个参数，View 从未声明过任何能力**（§15.3 校验读 `appCapabilities.availableDisplayModes`，读不到只在日志提示）；② 接 `app.onhostcontextchanged`（connect 前注册）+ 门面 `onHostContextChanged(cb)`（注册即回放当前上下文） |
| `editor.html`（v3.9.7 的 ⑥） | `mcpAppBoot()` 里 `mcpAppHostCtxWatch()`；新增 `mcpAppOnHostCtxChanged()`——**pip 面板可拖宽**（§15.2 D7：形态不可变但容器尺寸会变），宽度变化时重排与宽度相关的部分（注入 deck 内的批注角标按 `--slide-scale` 反缩放、对比叠层绝对定位）并重报尺寸；其余交给 CSS 弹性布局 |
| `tools/ext_apps_bundle.{js,json}` | 重建（视图版本仍 v3.9.7；View HTML **767608 B** < 2 MB） |
| `tests/harness/r_bridge_check.py` | `apps` 组新增断言：`open_editor` 的 `ui.mode=='pip'` 且 `ui.mode_inline_when=={'arg':'view','in':['brief']}`（防静默漂移） |

**关于"布局假设"**：宿主对 **pip 忽略 `size-changed`**（面板高度固定、滚动由 View 内部处理，`webui.html:6123-6129`），并在面板拖拽时发 `host-context-changed`（`webui.html:6203` 的 ResizeObserver）。View 侧因此**不需要**按内容高度自增——`mcpAppDesiredHeight()` 在非脑暴态返回 `hostViewportMaxHeight()`（= 宿主的 `containerDimensions.maxHeight`，pip 下即面板高），脑暴态才请求"内容自然高度"（inline 语义，正好对应脑暴=inline）。

## 3. 验证（pptx 侧）

```
python3 -m pytest tests/harness/test_bridge_core.py -q                      → 48 passed
python3 tests/harness/r_bridge_check.py --group {transport,sdk,apps,http,fault,security,integration} → 7 组全 PASS（apps 含新增断言）
python3 tests/harness/aa_mcp_apps_check.py                                  → ALL PASS
python3 tools/build_ext_apps_bundle.py --check                              → OK（sha256 ecbb4579…）
工具 meta 探针：open_editor.ui = {visibility, resourceUri, mode:'pip', mode_inline_when:{arg:'view',in:['brief']}}
```
**真宿主人工项仍 NOT_RUN**：pip 面板内的实际观感、拖宽后的重排、脑暴在 inline 工具卡内的表现。

## 4. 需要 **框架侧（SproutHarness）** 配合的改动 — 交接清单

### 4.1 字段契约（宿主扩展，spec 无此字段）

```
tool._meta.ui.mode             = "inline" | "pip"                    ← 已有：mcp/client.py::_extract_display_mode
tool._meta.ui.mode_inline_when = {"arg": <参数名>, "in": [<值>, ...]}  ← 新增，可选
```

### 4.2 求值规则（在**发射 mcp_app 事件**时，用**本次 `tool_args`** 求值）

1. `mode` 缺省 / 非法 → `inline`（沿用现状，保留"非法值打 warning"的纪律）
2. `mode == "pip"` **且**声明了 `mode_inline_when`：`tool_args[arg] ∈ in` → `inline`；否则 `pip`
   （`arg` 缺省 / 类型不符 / `in` 为空 / `tool_args` 缺该键 → 一律按 `mode`，即 `pip`）
3. 其余 → `mode` 本身

> 语义仍是"**挂载前确定、运行时不切换**"——只是把"每工具一个形态"放宽为"每工具一个默认形态 + 可选的按参数例外"，不违反 §15.2 D2/D7。

### 4.3 具体改动点（框架仓库）

| # | 位置 | 改动 |
|---|---|---|
| a | `src/sprout_harness/mcp/client.py` | `_extract_ui_meta()` / `_extract_display_mode()`：把 `mode_inline_when` 一并取出放进 `ui_meta`（保持非法值 → warning + 不生效） |
| b | `src/sprout_harness/agent/graph.py:966` | 由 `"pip" if entry.ui_meta.get("mode")=="pip" else "inline"` 改为按 §4.2 求值（**同一处已有 `tc_args`，零额外成本**） |
| c | `docs/design/agent/mcp_apps_design.md` | §15.2 D3 补"可选按参数条件化"；**§15.10 给 pptx 的清单从"工具补 `mode='pip'`"更正为"`mode='pip'` + `mode_inline_when={arg:'view',in:['brief']}`，View 补 `availableDisplayModes:['inline','pip']`"** |
| d | 验收 | `tests/test_mcp_apps_host_matrix.py` 或 L3 e2e 增两臂：`view=brief` → hostContext/挂载容器为 inline；`view=edit` → pip |

### 4.4 注意

- **§15.3 交叉校验**：pptx 现在声明 `availableDisplayModes=['inline','pip']`，两种形态都通过；若未来某工具只声明 `pip` 而 View 声明里也含 pip，同样通过。
- **不要**改成"由 View 运行时申请形态"（`request-display-mode`）——§15.2 D1/D2 明确形态不可运行时切换，pptx 侧也不依赖它。
- 框架侧改完前，pptx 的 pip 会**整工具生效**（脑暴也进 pip 面板）；这不是回归，是 §4.2 未落地的中间态。

## 5. 不做 / 残余

- **不拆工具**（不新增 `open_brief` 之类的第二个 UI 工具）：`open_editor` 是"唯一带 UI 的入口、唯一面向模型的创作入口"（AGENTS.md 红线），不为此破线。
- **不改 `request-display-mode` 语义**（沿用宿主的"诚实拒绝式接受"）。
- 真宿主人工项 NOT_RUN；`editor.html` 未做"面板宽度断点"级别的专门排版（依赖 CSS 弹性布局）。
