# 1028 · 编辑器状态流问题分析与修复方案

> **状态**：**已实施并自测通过（2026-10-28）**；**未提交**（等用户确认文件清单与 commit message）。用户已拍板：Q1 提交即发送 / Q2 可见+可处置不丢 / Q3 改 `get_status` 带轻量摘要 / Q4 顺带统一 convert 通道。实施记录见 §9。
> **日期**：2026-10-28
> **依据**：[2026-10-27 系统复盘](../review/2026-10-27_pptx_html_mcp_system_audit.md) · [2026-10-28 按钮数据流分析](../review/2026-10-28_editor_button_dataflow_and_state.md) · [1027 P4 状态机止血](1027_p4_state_machine_hemostasis.md)
> **用户诉求（本条目的来源）**：① 「提交批注」应像「一键转换」那样支持发送给 AI；② 用户手动编辑并保存后，**之前的请求是否应直接丢弃**；③ 要一份完整的问题分析 + 修复方案。

---

## 1. 结论速览

| # | 诉求 | 我的结论 |
|---|---|---|
| ① | 提交批注 = 发送给 AI | **通道本来就是对的**（`hostBridge.impl()` 与 `convertDeck()` 同用 `hostKindDetect()`）。真正缺的是 **「提交批注」只写入本地清单、不发**（`annoSubmit` `:5530-5549`），必须再点清单底部 `发送给 AI`。⇒ **改「提交批注」的语义**，不是改通道。 |
| ② | 保存后丢弃之前的请求 | **不建议无条件丢弃**。理由见 §5.2：请求不是"一定失效"，且把"保存"变成有副作用的高危动作会反噬。**建议改为"可见 + 一键处置"**；若你坚持，正确形态是 **保存时只作废"基线已过期的产物型 pending 请求"，并发事件告知**（不是静默丢弃）。 |
| ③ | 完整分析 + 方案 | §3 问题清单、§4 实测证据、§5 分项方案、§6 待你拍板的决策、§7 验收计划。 |

**一句话概括"为什么感觉乱"**：**状态机是诚实的（DB 里一切都有据），但页面的可见性与可操作性只覆盖了轨 B**——轨 A 既看不到队列（无列表通道），也不能处置（无恢复按钮），而"发送/保存"类动作在轨判定失误时会**静默降级成复制**。于是"AI 说还有 5 条 / 页面什么都不显示 / 点了像没反应"三者同时成立。

---

## 2. 现状模型（修复的对象）

### 2.1 四态 × 策略面

`hostBridge`（`:4654-4672`）是策略面，`impl()` 每次按 `hostKindDetect()` 取实现：

```
window.pptxMcp        → mcp-app（轨 A）
state.embedded        → embedded            ← ⚠️ 轨 A 的 iframe 里也为真
bridge.enabled(#brt=) → bridge（轨 B）
否则                   → static
```

四态各实现 11 个能力（`load/save/asset/intent/status/poll/viewport/background/download/versions/rollback`）。**`intent` 是"把用户意图交给 AI"的唯一入口**：

| 轨 | `intent()` 行为 | 是否真的到 AI |
|---|---|---|
| mcp-app | `callTool submit_intent` | ✅ 入状态机 + 敲门 |
| bridge | `POST /api/intent` | ✅ 入状态机 |
| embedded | `postMessage` + **顺带 copyText** | ❌ 我们的 WebUI 不监听这些消息 → 只剩复制 |
| static | **`copyText`** | ❌ 设计上就是复制 |

### 2.2 意图状态机（daemon 是唯一真相；P4 已实施）

```
pending ──认领──▶ processing ──complete──▶ succeeded
                    │ ├──fail──▶ failed ─┐
                    │ ├──基线过期──▶ conflict ─┼─▶ retry(rebuild) ─▶ pending(attempt+1)
                    │ └──stop/重启──▶ interrupted ┤  retry(resume) ─▶ pending(att+1, 复用 work_path)
pending ──cancel──▶ cancelled                    ┘
interrupted ──再 cancel──▶ cancelled        （P4.1，2026-10-27）
interrupted/failed ──无 lease 且超 600s──▶ cancelled（P4.2 自愈，2026-10-27）
```

**谁能动谁**：只有 **轨 B 页面 / CLI**、以及 **daemon 自愈** 能推进 recoverable 状态；**轨 A 没有任何恢复通道**（审计 §2.3，`query_intents`/`retry_intent`/`cancel_intent` 工具在 1027 被删）。

---

## 3. 问题清单

| # | 问题 | 位置 | 性质 |
|---|---|---|---|
| **P1** | **「提交批注」只入本地清单、不发送** —— 用户以为提交=发送，实际还要再点清单底部的 `发送给 AI` | `editor.html:5530-5549`（`annoSubmit`）vs `:5661`（`btnSendAnno`） | UX 缺陷（用户诉求 ①） |
| **P2** | **轨 A 无意图列表通道** —— `mcpAppApplyStatus()` 不合并任何意图；`query_intents` 已删 | `editor.html:4118-4132`；审计 §2.3 | 结构性缺口（"AI 有 5 条 / 页面空"的直接原因） |
| **P3** | **轨 A 无恢复通道** —— 遇到 conflict/interrupted 无按钮可点 | `editor.html:8545`（`if(!trackA…)`） | 结构性缺口 |
| **P4** | **轨判定失误会静默降级** —— `state.embedded` 在轨 A iframe 里也为真；若 `window.pptxMcp` 未注入成功 → `intent` 发 postMessage（无人听）+ **静默复制** | `hostKindDetect()`；`embeddedHost.intent` | 静默降级（违反"静默降级必须有声音"） |
| **P5** | **保存后旧基线产物请求排队即 conflict** —— 实测 seq3 已 conflict、seq4-7 将同样 | daemon `await_intent` 认领时判 | 设计结果（但缺可见/处置）→ 用户诉求 ② 的来源 |
| **P6** | **`convertDeck()` 绕过策略面** —— 手写 `hostKindDetect()` 分支，与 `reFlip` 的 `bridgeSend` 重复（并发会话未评审改动，handover Q2 未决） | `editor.html:8251-8268` | 一致性/维护性 |
| **P7** | 共享代码残留直连（`/api/bridge/status`、`/api/convert-status`） | `:6792`、`:8242` | S1 剩余面 |

---

## 4. 实测证据（真实会话 `s_kQifUe4NJuZ9zESIuTTFCUXL`，2026-10-28）

```
session.revision = sha256:fbc7fd09…（当前）   deck=outputs/compound-interest/index.html
seq1 brief.submitted     cancelled                            （daemon 重启自动作废）
seq2 bake.requested      cancelled  STALE_RECOVERY            ← P4.2 自愈（原 interrupted 卡死 21h）
seq3 convert.requested   conflict   base=a65de62d…（旧）       ← 已认领，基线过期
seq4-7 convert.requested pending    base=a65de62d…（旧）       ← 会被逐条判 conflict
seq8 convert.requested   pending    base=fbc7fd09…（当前）     ← 保存之后提交的，可用

events: deck-changed{source:save, revision:fbc7fd09} @00:33:20
        intent-status{pending, seq8}                  @00:34:06
        intent-status{conflict, seq3}                 @00:34:17
clients 表：空           → 页面从未以浏览器客户端注册 → 不是轨 B（⇒ 轨 A）
anno.submitted：从未出现  → 批注从未真正发出
```

**由此确证**：① 保存会推进 revision，之后提交的用新基线（`seq8` 是对的）；② 页面空列表 + AI 有计数 = P2；③ 批注从未发出 = P1（或 P4）。

---

## 5. 修复方案

### 5.1 R1 · 批注：让「提交批注」与一键转换同体验（解决 P1）

**现状**：`annoSubmit`（弹窗）→ push 到 `annotations` → 只 `renderAnnoList()`；发送在 `btnSendAnno`（`bridgeSend('anno.submitted', buildAnnoExport().payload, …)`）。

**两种改法（需你选，见 §6）**：

- **R1-a（推荐）「提交即发送整份清单」**：`annoSubmit` 在入清单后，若当前形态支持发送（`mcp-app`/`bridge`），**立即调用与 `btnSendAnno` 完全相同的路径**（`bridgeSend`，载荷=`buildAnnoExport()` 全量清单），并保留 `发送给 AI` 作为"补充后再发"、`复制批注指令` 作为 static 降级。
  - 连续加多条批注 = 多次发送（每次都带全量清单）。**消解**：发送后置 `annoUnexported=false`；再提交时若清单内容未变则跳过，或提示"已发送，是否重发全部"。
- **R1-b「只让发送按钮显眼」**：`提交批注` 语义不变，但把 `发送给 AI` 提为主按钮 + 提交后高亮/滚动到它，`复制批注指令` 仅在 static 轨显示。

**无论选哪个，都一并做**（低风险、治 P4）：`embeddedHost.intent` 的"顺带 copyText"改为**显式提示**（toast/告警条"当前形态不支持直接发送，已复制指令"），并把 `hostKindDetect()` 落到 embedded 分支时在控制台打一条 warn（轨道判定可观测）。

### 5.2 R2 · 保存与旧请求（你的诉求 ②）

**先给事实**：保存后，旧基线请求的结局由 daemon 决定，**分两类**：

| 类型 | 保存后行为 |
|---|---|
| **指令型**（`brief.submitted`/`design.submitted`/`anno.submitted`） | 认领时**自动 rebase** 到当前 revision（锚点另存 `payload.anchor`）→ **不受影响，照常执行** |
| **产物型**（`convert.requested`/`bake.requested`/`illustrate.requested`） | 基线过期 → 认领时判 **`conflict`** → 必须用户 rebuild（重跑，可能计费） |

**为什么不建议"保存即丢弃全部请求"**：

1. **并非全部失效**——指令型请求（批注/设计/简报）本来就该随版本前进，丢掉会丢掉用户的真实意图。
2. **"保存"会变成高危动作**——用户随手 Ctrl+S 就静默删掉队列，之后要重排；且保存是高频动作。
3. **与"持久请求"的设计前提冲突**——协议明确"已接收请求及 result 不随事件清理"，且 `retry` 是既有的正式出口。
4. **真正让用户烦的不是"请求还在"，而是"看不见、动不了"**（P2/P3）。请求消失并不会让"乱"变好——下次仍会在别处撞上同样的不可见。

**建议的三档（需你选，见 §6）**：

- **R2-a（推荐）"可见 + 一键处置"，不丢**：
  - 补 P2：轨 A 也能列出队列（只读）；
  - 补 P3 的**最小形态**：面板里对 `conflict`/`interrupted` 给一个「按当前版本重建」入口（**不新增模型可见工具**，走已有的 app-only `submit_intent` 语义或 daemon 路由，需你签字形态）；
  - 队列里对"基线已过期"的产物请求**预标注**（"基线已过期，需重建"），不让用户自己猜。
- **R2-b "保存时只作废基线已过期的产物型 pending 请求"**：`save` 成功后，把该会话内 `status='pending'` 且 `base_revision != 新 revision` 的**产物型**请求 → `cancelled` + `intent-status` 事件 + 面板提示"因本次保存作废 N 条（可重新提交）"。**不碰**指令型、不碰 processing。→ 满足你的直觉，但不静默、不误伤。
- **R2-c "保存时清空该会话全部 pending"**：最简单、最激进；会连带丢掉刚提交的有效请求（如 seq8）。**不推荐**。

### 5.3 R3 · 轨 A 的意图列表（解决 P2）

`get_status` 已能返回 `pending_count`/`interrupted` 摘要。两条路：
- **R3-a（不改工具面）**：让 `get_status` 的返回带上**轻量摘要列表**（id/type/status/attempt/seq，无 payload），`mcpAppApplyStatus()` 合并进 `bridge.intents` 只读渲染。需改 daemon 的 status 返回（协议文档 §7.5 同步）。
- **R3-b（新增一个 app-only 工具）**：恢复一个"查询意图"的 app-only 工具。审计 §3 明确建议**先走 R3-a**，真不够再加**一个**工具（需签字）。

### 5.4 R4 · 统一 convert 通道（解决 P6）

`convertDeck()` 改回 `hostBridge.intent('convert.requested', …)`（与 `reFlip` 同一实现），删掉手写的 `hostKindDetect()` 分支——顺带修掉它漏掉的 `static` 分支。

---

## 6. 待你拍板的决策

| # | 决策 | 选项 |
|---|---|---|
| **Q1** | 批注发送形态 | R1-a 提交即发送（推荐） / R1-b 只把发送按钮做强 |
| **Q2** | 保存后旧请求 | R2-a 可见+一键处置不丢（推荐） / R2-b 保存时作废"基线过期的产物型 pending" / R2-c 清空全部 pending |
| **Q3** | 轨 A 列表实现 | R3-a 改 `get_status` 返回摘要（推荐） / R3-b 新增一个 app-only 查询工具（需破红线签字） |
| **Q4** | 是否顺带做 R4（统一 convert 通道） | 是（推荐，一次消除一处不一致） / 否 |

> 说明：Q2-b / Q3-b 都触及"状态机语义"或"工具面红线"，按项目规矩需你明确签字后我才动手。

---

## 7. 验收与验证计划（实施后执行）

```bash
cd /home/lixiang/Desktop/pptx-html-design
python3 -m pytest tests/harness/test_bridge_core.py -q                    # 基线 47 passed，不得退化
python3 tests/harness/r_bridge_check.py --group transport sdk apps http fault security integration   # 期望 7 组 PASS（ui 组为既有红）
python3 tests/harness/aa_mcp_apps_check.py                                # 期望 ALL PASS
python3 tools/build_ext_apps_bundle.py --check                            # 改 editor.html 必须重建并 OK
```
- 每项改动**先写失败断言再修**（如 R1：断言"提交批注后产生一条 anno intent"）。
- 真宿主人工项（轨 A 内点击、宿主确认"敲门"）仍会如实标 **NOT_RUN**，不写成 PASS。
- 文档同步：`docs/design/editor-agent-bridge-protocol.md`（若 Q3 动 status 返回）、`AGENTS.md` 红线、`docs/howto/editor-agent-bridge.md`、`skills/html-pptx/SKILL.md`（若批注流程语义变化）、本目录 README 索引。
- `git commit` 前报文件清单 + commit message 等你确认。

---

## 8. 明确不做（本轮）

- **不为轨 A 全面补齐能力面**（审计 §5 明确不做）；P3 只做"最小可处置"那一条（若你选 R2-a）。
- **不引入 JS lint / 构建步骤**（破"纯静态零构建"红线）；空 catch 的白名单化留在既有 harness 检查里。
- **不改 `retry/resume` 的既有语义**（basline 校验、attempt fence、publication 恢复都不动）。
- **不动并发会话的未决项**（`convertDeck()` 的归属待你确认；R4 若获批即顺带收口）。

---

## 9. 实施记录（2026-10-28）

### 9.1 改动清单

| 文件 | 改动 |
|---|---|
| `tools/bridge_core.py` | `get_status()` 返回新增 **`intents` 轻量摘要**：只列非终态 + recoverable，按 seq 升序、上限 50 条；`payload` 仅在 `payload_bytes ≤ INTENT_INLINE_MAX`(16 KiB) 时附带（供"按当前版本重新提交"） |
| `editor.html` | **v3.9.6 → v3.9.7**：① `bridgeMergeStatusIntents()` 把摘要并进 `bridge.intents`（本地的纯 UI 在途态 `submitting/unconfirmed/retrying` 不被覆盖）；② `currentRevision()` + 面板"基线已过期（认领时会冲突）"标注；③ 轨 A 新增**「按当前版本重新提交」**（`bridgeResubmitIntent` → `bridgeSend`，不扩工具面/不破红线）；④ `annoSubmit` **提交即发送**（`sendAnnotations({skipUnchanged:true})`），`btnSendAnno` 复用同一入口（显式发送不跳过）；⑤ `embeddedHost.intent` 不再静默复制（`console.warn` + 明确 toast，保留剪贴板兜底）；⑥ `convertDeck()` 统一走 `hostBridge.intent`（与 `reFlip` 同一实现，补回原先漏掉的 static 臂） |
| `tools/ext_apps_bundle.{js,json}` | 由 `tools/build_ext_apps_bundle.py` 重建（版本随 `editor.html` 头 → v3.9.7） |
| `tests/harness/test_bridge_core.py` | 新增 `test_get_status_exposes_intent_summary_for_track_a` |

### 9.2 验证（改动后实测）

```
python3 -m pytest tests/harness/test_bridge_core.py -q                   → 48 passed（基线 47 + 1 新用例）
python3 tests/harness/r_bridge_check.py --group apps|fault|integration   → 均 PASS
python3 tests/harness/aa_mcp_apps_check.py                               → ALL PASS
python3 tools/build_ext_apps_bundle.py --check                           → OK（sha256 b2991cad…）
build_view_html() 字节数                                                  → 764088（746 KB，< 2 MB）
```

> 注：`aa_mcp_apps_check` 偶发在**收尾阶段**抛一次 `playwright TargetClosedError`（teardown 竞态），但结果仍 `ALL PASS`；重跑即消失，与本次改动无关。

### 9.3 未做 / 残余

- **真宿主人工项仍 NOT_RUN**：轨 A 内实际点击「按当前版本重新提交」、批注提交后的"敲门"确认链路、面板在真宿主的观感。
- **`conflict` 仍不自愈**（沿用 2026-10-27 判据：冲突必须用户决定）。轨 A 用"重新提交"绕开，**原 conflict 行保留可见**——这正是"不丢请求"的应有之义。
- **未恢复 `query_intents` 工具**：轨 A 的列表改由 status 摘要提供（≤50 条、无分页、无详情）。够用即不加工具；若日后需要分页/详情，再按审计 §3 的建议**只加一个** app-only 工具（需签字）。
- **未采用 R2-b / R2-c**（保存时作废或清空旧请求）——按用户选择"可见+可处置，不丢"。
