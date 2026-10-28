# 交接：MCP Apps 标准化 + 四态收敛（先读本文，再动手）

> **给下一位 AI**：本文是实施入口。读完本文 → 再读文末「必读顺序」里的三份文档 → 跑一遍「基线命令」确认环境 → 从 §7「第一件事」开始。
> **计划与进度记录**：[`1027_mcp_apps_standardization.md`](1027_mcp_apps_standardization.md)；**证据与缺陷矩阵**：[`../review/2026-10-27_pptx_html_mcp_system_audit.md`](../review/2026-10-27_pptx_html_mcp_system_audit.md)。

---

## 0. 30 秒速览

| 项 | 内容 |
|---|---|
| 目标 | 在**标准 MCP Apps 协议**基础上，把编辑器的完整功能在四种运行态下都做成真可用（治"一个接一个蹦"的三条结构原因：三层并存/状态机无放弃出口/daemon 重启常态） |
| 关键前提 | 客户端**已经是官方 SDK**（`tools/ext_apps_facade.js:11` 是 `new App(...)`）→ **不重写客户端、不引框架、不引构建步骤** |
| 四阶段 | **P1 宿主合规 → P2 CSP/稳定源 → P3 三层收敛 → P4 状态机止血**（每阶段可独立验收、可停） |
| 当前状态 | P1–P4 **均未开始**；先行动作（系统复盘、工具面 18→14）已完成 |
| 第一件事 | 跑基线命令确认环境 → 做 **P1.1**（宿主侧声明扩展，风险最低、删代码最多） |

---

## 1. 安全须知（必读，先看这一节）

### 1.1 两个仓库，别搞混

| 仓库 | 路径 | 角色 |
|---|---|---|
| **编辑器/桥/MCP server** | `/home/lixiang/Desktop/pptx-html-design` | `editor.html`（View，8979 行）、`tools/bridge_core.py`（daemon）、`tools/bridge_mcp.py`（stdio MCP server，Python）、`tools/bridge_dispatch.py`（工具→路由映射） |
| **框架/宿主** | `/home/lixiang/Desktop/SproutHarness/.claude/worktrees/feature+mcp-apps` | 宿主侧（MCP 客户端能力、WebUI 宿主实现、sandbox 路由）。分支 `feature/mcp-apps`，HEAD `6f4bdb4` |

⚠️ **项目红线**：禁止删除或修改 `.claude/worktrees/` 下的任何 git worktree（除非用户明确要求）。
⚠️ **凭证**：daemon 的 `management_token` 在 `<session workspace>/.pptx-html/serve.json`，**不得写入文档**。

### 1.2 工作树里有未提交改动（务必先看）

`/home/lixiang/Desktop/pptx-html-design` 的 HEAD 是 `0f3cfcf`，但工作树**领先**，包含：

1. **本轮的 1027 工具面精简**（已验收）：`tools/bridge_dispatch.py`、`tools/bridge_mcp.py`、`editor.html`、`tests/harness/r_bridge_check.py`、`tests/harness/aa_mcp_apps_check.py`、`tools/ext_apps_bundle.{js,json}`、`AGENTS.md`、`docs/design/mcp-apps-upgrade.md`（含新增 §10.13）、`docs/test_acceptance/mcp-apps-upgrade.md`、`skills/html-pptx/SKILL.md`、`docs/progress/README.md`。
2. **一处不属于本轮、来源为并发会话的改动**：`editor.html` 的 `convertDeck()` 被改成按 `hostKindDetect()` 分流（轨 A 走 `mcpAppSubmitIntent`）。它**未经本轮评审、未验证**，也**没有**被本轮的子 Agent 汇报。归属证据：另一个会话 `~/.kimi-code/sessions/wd_pptx-html-design_af53b0b73151/session_652e4d1b…` 在 08:17/08:18 写过 `editor.html`。
   → **动手前先问用户**：保留还是回退（这是交接账上的一笔未决）。
3. 新增未跟踪文档：`docs/progress/1027_tool_surface_slimming.md`、`docs/progress/1027_mcp_apps_standardization.md`、`docs/review/2026-10-27_pptx_html_mcp_system_audit.md`、本文，以及若干 `docs/progress/_logs/*.log`（历史产物）。

### 1.3 运行中的服务（自己复核，不要相信本文的快照）

```bash
cd /home/lixiang/Desktop/SproutHarness/.claude/worktrees/feature+mcp-apps
python3 apps/sale_pptx_agent/run_local.py --port 8100      # 起服务（会重拷技能 + 杀旧 daemon）
ss -tlnp | grep :8100 ; curl -s localhost:8100/health
# 测试入口： http://127.0.0.1:8100/mcp-apps-tester   （MCP Apps 测试台）
#           http://127.0.0.1:8100/webui              （通用 WebUI）
# 日志：/tmp/mcp_apps_sale_pptx.log
```

**必须知道的运行语义**（本轮踩过）：

- MCP stdio server 是**每次工具调用新起进程**（宿主经 `langchain_mcp_adapters`）→ "重启服务"**不等于**重启 MCP；`PPTX_HTML_APPS_TOOLS` 是它的环境变量。
- bridge daemon（`tools/edit.py <workdir> --daemon`）**懒起**：第一次 MCP 工具调用才拉。杀 daemon = 中断在跑的意图（并在重启时把 `processing` 改成 `interrupted`）。
- `run_local.py` 启动时会**杀掉所有** `edit.py … --daemon`，并在存在时删除 `<physical_root>/workspace/.pptx-html/`（桥状态目录）。
- `/storage/skills/html-pptx` 是**启动时复制的技能快照** → 改 `skills/html-pptx/SKILL.md` 必须重启服务才生效。
- bridge 的 `session_id` 形如 `s_xxxx`（由 `open_editor` 生成），**不是** harness 的 thread_id（形如 `dcc2ad3a…`）。查状态时用错 id 会得到 404「任务不存在」（本轮的乌龙）。

---

## 2. 必读顺序

1. **本文**（安全须知 + 任务清单）。
2. `docs/review/2026-10-27_pptx_html_mcp_system_audit.md`（缺陷矩阵：三层归属统计、按钮×状态、状态机出口、静默吞错、取证命令）。
3. `docs/progress/1027_mcp_apps_standardization.md`（阶段计划、标准对齐清单、风险、不做清单）。
4. `docs/design/mcp-apps-upgrade.md` §4.3（工具面）、§10.3（列举期双模）、**§10.13（1027 工具面精简）**、§10.10（沙箱偏离）。
5. `AGENTS.md` →「Bridge 操作红线」段（轨 A/轨 B、`open_editor` 唯一入口、app-only 不可见）。
6. `docs/progress/1027_tool_surface_slimming.md`（刚发生的工具面变化，避免重蹈"删了发现没出口"）。

---

## 3. 决策账

**已获用户批准（2026-10-27，"都可以按你的来"）**

| # | 决策 | 影响 |
|---|---|---|
| D1 | 宿主声明 MCP Apps 扩展（`io.modelcontextprotocol/ui` + `mimeTypes`） | 改 SproutHarness；**删** `always` 依赖 |
| D2 | 删掉 `PPTX_HTML_APPS_TOOLS=always` 与"列举期双模" | 改写 `AGENTS.md` 红线措辞、`bridge_mcp.py:318-335` 简化 |
| D3 | 允许 View 在 CSP 下直接 HTTP 取资产/文档 | 推翻"资产一律经工具 base64"；`read_bundle_file` 资产分支退场 |
| D4 | 状态机止血：`cancel` 支持 `interrupted`、陈旧中断自愈、门改 per-intent | 改 `bridge_core.py` 语义 |

**仍需逐条确认（实施到该点时必须停下来问）**

| # | 事项 | 说明 |
|---|---|---|
| Q1 | P4.2 / P4.3 的**具体判据** | "陈旧"多久？"无 lease"怎么判？门改成 per-intent 后，`conflict` 是否仍需用户介入？ |
| Q2 | 并发会话的 `convertDeck()` 改动 | 保留 or 回退（见 §1.2 第 2 条） |
| Q3 | 线上卡死意图 `35fbd594-29c0-41ee-b064-55cbbbde3985`（`bake.requested`，`interrupted`，基线已漂移） | 等 P4.2 自愈 / 立刻 `rebuild`（重跑烙入可能计费）/ 手改 DB（**不推荐**） |
| Q4 | 任何越出 D1–D4 的改动 | 先问，不要自行扩大范围 |

---

## 4. 任务清单（可勾选；每项含文件:行 + 改法 + 验收）

### P1 · 宿主合规

- [ ] **P1.1** 宿主 MCP 客户端声明扩展
  - 位置：`SproutHarness/.claude/worktrees/feature+mcp-apps/src/sprout_harness/mcp/client.py:78 get_mcp_tools()`（经 `langchain_mcp_adapters.client.MultiServerMCPClient`，见同文件 `:164`）。
  - 改法：让 `initialize` 发出的 `ClientCapabilities` 带上 `extensions={"io.modelcontextprotocol/ui": {"mimeTypes": ["text/html;profile=mcp-app"]}}`。**已实测**本地 `mcp` 包 `ClientCapabilities.model_config.extra == "allow"` ⇒ 不必改 SDK 源码，注入点集中一处即可（若 adapters 不开放入口，用最窄的 monkey-patch，并在文件头写清"为什么"）。
  - 验收：`tools/bridge_mcp.py` 的 `apps_declared()` 返回真（可在宿主启动日志加一条断言）；**不再需要** `PPTX_HTML_APPS_TOOLS`。
- [ ] **P1.2** 退场 `always` 与列举期双模
  - 位置：`apps/sale_pptx_agent/config_work.yaml:60`（去掉环境变量）；`tools/bridge_mcp.py:318-335`（`apps_tools_listed`）、`:448-473`（`mode_hint`/`mode_source`/`open_browser_resolved`）、`tools/bridge_dispatch.py` 顶部注释；`AGENTS.md` 红线措辞；`docs/design/mcp-apps-upgrade.md` §4.3/§10.3。
  - 验收：`r_bridge_check --group apps` 的双模断言改写为"声明扩展即全量 14"；`aa_mcp_apps_check` 全绿。
- [ ] **P1.3** 复核宿主 UI 侧既有实现（不是新建）
  - 位置：`SproutHarness/.../src/sprout_harness/agent/webui.html`（`_buildHostContext:5057`、`containerDimensions:5084`、握手门 `:5045`、两阶段拆卸与 App 消息确认卡）。
  - 验收：只做"确认已符合"，**不重构宿主 UI**。

### P2 · CSP 与稳定源

- [ ] **P2.1** 资源 contents 加 CSP
  - 位置：`tools/bridge_mcp.py:581-594` 的资源装饰器 `meta`（加 `ui.csp.resourceDomains`）。
  - **已实测**：`FastMCP.read_resource` 会把 `resource.meta` 透传到 `contents[]._meta` ⇒ 无需改 SDK。（规范要求 CSP 在 contents 上，不在 `registerAppResource` 配置上——Python 侧即上述 meta。）
- [ ] **P2.2** View 侧资产转 HTTP
  - 位置：`editor.html:4288`（`mcpAppHydrateImage`）、`:4378`（`mcpAppHydrateCss`）。保留 base64 回退分支与开关。
  - 连带：`read_bundle_file` 的资产分支下线（保留 `export/`）。
  - 验收：**在不给 `allow-same-origin` 的沙箱下**资产仍渲染（`aa_mcp_apps_check` 新增一臂）。
- [ ] **P2.3** `ui.domain` 替代 `allow-same-origin`
  - 现状：`mcp.apps.allow_same_origin`（仓库默认 false；`config_work.yaml:70` 为 true）。
  - 验收：默认形态（false）下编辑器仍可编辑；宿主侧注入 CSP 的路径有测试。
- **风险**：全计划最易翻车处（CSP / `ui.domain` / `allow-same-origin` 三者纠缠）。**每步留开关 + 跑 aa 检查**。

### P3 · 三层收敛（治 S1）

- [ ] **P3.1** 共享 UI 的直连通道收敛到策略面
  - 现状（审计 §2.2）：`bridgeFetch(` 19 处中 **15 处在共享 UI**；`mcpAppCall(` 15 处中 **9 处在共享 UI**；`hostBridge.<能力>()` 分派仅 8 处。
  - 顺序建议：intent / status / draft / load / export 五个能力先收敛。
- [ ] **P3.2** 补轨 A 的"恢复族"
  - 现状（审计 §2.3）：恢复族（取消/停止/重试/查询）在轨 B 有 4 个函数，轨 A **为 0** → 这是"按钮点了没用"的根因。
  - 优先走 **P4.2 自愈**（不加工具面）；只有证明不够时才加**一个** app-only 工具（需重新签字，见计划 §8）。
- [ ] **P3.3** 入库"登记制"静态断言
  - 内容：共享 UI 里的直连通道调用点必须在**登记表**内；空 `catch` 必须在允许表内（现状 17 处，见审计 §2.6）；未登记 → 检查失败。
  - 位置：`tests/harness/`（复用现有检查机制，**不建框架、不引 JS lint 工具链**）。
  - 验收：**先对改动前的树失败**（变异测试证明非恒真），修复后通过。

### P4 · 状态机止血（治 S2/S3）

- [x] **P4.1** `cancel_intent` 支持 `interrupted`（即"放弃"）——**已实施 2026-10-27**。
- [x] **P4.2** 陈旧中断自愈（新增 `_heal_stale_recoverables`，启动 + 每次认领前调用）→ `cancelled` + 发 `intent-status` 事件。判据（用户确认"按建议默认"）：无 lease 且超过 `STALE_RECOVERY_GRACE_SEC`（600s）；`conflict` 不自愈。
- [x] **P4.3** 门改 per-intent（移除会话级 `RECOVERY_REQUIRED`）。
- 验收：**✅ 47 passed**（基线 44 + 3 新用例）；变异测试证明 4 条相关用例在改动前**全部失败**；`r_bridge_check` 7 组全 PASS + `aa_mcp_apps_check` ALL PASS。线上 `35fbd594…` 由 P4.2 自愈解除。详见 [1027 P4 状态机止血](1027_p4_state_machine_hemostasis.md)。

---

## 5. 基线命令（动手前跑一遍；每阶段结束再跑）

```bash
cd /home/lixiang/Desktop/pptx-html-design
python3 -m pytest tests/harness/test_bridge_core.py -q                     # 基线：44 passed
python3 tests/harness/r_bridge_check.py --group transport sdk apps http fault security integration   # 基线：全 PASS
python3 tests/harness/aa_mcp_apps_check.py                                 # 基线：ALL PASS
python3 tools/build_ext_apps_bundle.py --check                             # 基线：OK（改 editor.html 版本号必须重建）
python3 tests/harness/run_e2e.py                                           # 基线：62 项 58 PASS / 4 FAIL（见下）
python3 -c "import sys;sys.path.insert(0,'tools');from bridge_mcp import build_view_html;print(len(build_view_html().encode()))"   # 基线 757102 字节（<2MB）
```

**已知红（不得当成本轮引入）**

| 项 | 现象 | 性质 |
|---|---|---|
| `r_bridge_check` **全量** | `ui` 组 `Page.click: Timeout … waiting for locator("#btnBriefGen")` | 既有：`editor.html` 里该 id 出现 **0** 次、harness `:383` 仍点旧 id（见 `1026_open_file_track_and_first_deck.md:96`） |
| `run_e2e.py` | 4 FAIL：T29-bridge / T31-brief / T35-dynamic-brief（同一定位器漂移）+ T34-theme-proving | 既有 |

**工具面探针**（本轮用过的独立验证：真起 stdio server 列工具）

```bash
# PPTX_HTML_APPS_TOOLS=always → 14 个（其中 ui.visibility:["app"] 9 个）；auto → 恰好 5 个
# 脚本见审计 §6（/tmp，未入库）；P1.2 落地后这条断言要改成"宿主声明即全量"
```

---

## 6. 坑（本轮踩过的，逐条一句）

1. ~~**一条 `interrupted` 意图锁死整个会话**~~ —— **已修（P4.3，2026-10-27）**：会话级恢复门已移除——一条 recoverable 不再阻断整会话的认领（此前 `bridge_core.py:1105` 拒绝一切新认领 → 页面能提交、agent 永远不领；**S2 的核心**）。
2. ~~**`cancel` 救不了 `interrupted`**~~ —— **已修（P4.1，2026-10-27）**：对 `interrupted` 再取消即**放弃**（→`cancelled`）。此前它只处理 `pending`（→cancelled）与 `processing`（→interrupted），对 `interrupted` 是 no-op——这就是"关闭重开也清不掉"的原因。另：陈旧的 `interrupted`/`failed` 由 **P4.2** 在宽限期后自愈为 `cancelled`。
3. **`retry` 的 `resume` 会被基线漂移挡掉**：只有 `rebuild` 可用（重跑，可能计费）。线上那条就是这个组合。
4. **daemon 重启即制造坑 1**：`processing` → `interrupted`（`:585`），而 `run_local.py` 起服务就杀 daemon。
5. **`bridge session_id` ≠ harness `thread_id`**：查状态用错 id 会 404。
6. **技能是启动时复制的快照**：改 `SKILL.md` 要重启服务才生效。
7. **MCP server 每次调用新起**：改它立即可见，不需要重启服务；改 `editor.html`/`config.yaml` 则需要（`editor.html` 由 daemon 资源读取时组装，`config` 在启动时读）。
8. **空 `catch` 会伪装成"没反应"**：全仓 17 处（`:5571` 那类已修，其余待 P3.3 覆盖）。
9. **并发会话**：本 repo 可能同时被另一个会话编辑（§1.2 第 2 条）。动手前 `git status` + 看 mtime。
10. **杀 daemon 会打断用户正在跑的活**（本轮即因此中断过一次烙入）——除非用户要求，不要随手清理。

---

## 7. 第一件事

```bash
# ① 确认环境（别相信交接里的快照）
cd /home/lixiang/Desktop/pptx-html-design && git status --short && git log --oneline -1
ss -tlnp | grep :8100 || echo "服务未起"
# ② 跑一遍 §5 基线命令，记下与本文件数字的差异
# ③ 问用户三件事：Q2（convertDeck 去留）、Q3（卡死意图处理）、Q1（P4 判据）——若用户希望先做不依赖 Q1 的部分，从 P1.1 开始
# ④ 开始 P1.1（宿主侧声明扩展）；改完立刻跑 §5 的 apps 组 + 工具面探针
```

---

## 8. 完成判据（DoD）

- [ ] P1–P4 全部落地，且每阶段都有"改动前失败、改动后通过"的证据（变异测试或等价断言）。
- [ ] 审计 §4 的「操作路径 × 四态」矩阵达到**全 ✅ 或显式声明降级**，无"控件可见但通道不可用"。
- [ ] §5 全部命令回到（或优于）基线：`test_bridge_core` 不退化、`r_bridge_check` 除已知 `ui` 红外全绿、`aa_mcp_apps_check` ALL PASS、`bundle --check` OK。
- [ ] P3.3 的登记制断言入库且**非恒真**。
- [ ] 文档同步：`AGENTS.md` 红线、`docs/design/mcp-apps-upgrade.md`（§4.3/§10.3/§10.13）、`docs/test_acceptance/mcp-apps-upgrade.md`、`skills/html-pptx/SKILL.md` 与该轮进度文档。
- [ ] **不把 NOT_RUN / UNKNOWN 写成 PASS**；真宿主人工项（真实点击、宿主内文件选择）如实标注。
- [ ] `git commit` / `push` / `cherry-pick` **必须先向用户确认文件清单与 commit message**（项目规矩）。
