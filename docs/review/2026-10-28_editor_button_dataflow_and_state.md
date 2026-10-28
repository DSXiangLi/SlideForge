# 2026-10-28 · 编辑器按钮数据流 & 状态变更全面分析

> **触发**：用户反馈"pptx 整体状态非常混乱"，并提三问：① 手动编辑保存后状态怎么更新、后续是否都基于新版本？② 重开编辑器前的请求是否应清空？为何 AI 看到排队请求而编辑器"请求记录"为空？③ 批注按钮是否真与 AI 打通，为什么像要复制指令？
> **取证方式**：读 `editor.html`（9007 行）四态实现 + `tools/bridge_core.py` 状态机 + **线上真实会话库**（`<workdir>/.pptx-html/bridge.sqlite3`）与 `clients` 表 + 复现 daemon 请求。
> **证据纪律**：区分「逐条读码/实测」与「需在页面上确认」。凡推断均标注。

---

## 0. 三问速答

| # | 问题 | 结论 |
|---|---|---|
| 1 | 手动编辑保存后状态如何更新？后续基于新的？ | **是**。保存走 `hostBridge.save()` → 各轨 CAS 发布 → **页面把 CAS 基线推进到新 revision**（轨 B `bridge.loadedRevision=res.revision`；轨 A `mcpApp.revision=res.revision`）。**新提交**的请求用新基线 ✅；但**此前已入队的"产物型"请求**（convert/bake/illustrate）基线仍是旧的 → 被认领时判 `conflict`，须用户 rebuild。**指令型**（brief/design/anno）不受影响（daemon 认领时自动 rebase，锚点另存）。 |
| 2 | 重开前的请求是否该清空？为何 AI 有、页面空？ | **不该清空**（设计如此：intent 是持久请求，跨 SSE/页面生命周期存活）。页面空是**通道缺口**：**轨 A 没有"列出意图"的通道** —— `get_status` 只给 `pending_count` 等计数与 `interrupted` 摘要，`query_intents` 工具已在 1027 删除，且 `mcpAppApplyStatus()` 不合并任何意图摘要。页面只显示**本页面会话内自己提交过**的条目（本地乐观条目）。⇒ AI 端 `pending_count=5`、页面列表空，是同一事实的两面。 |
| 3 | 批注按钮与 AI 打通了吗？ | **轨 A 是通的**（`发送给 AI` → `submit_intent` 工具）；**静态态必然降级为复制**（`staticHost.intent` = `copyText`）；**嵌入态发 postMessage + 顺带复制**。但**弹窗里的「提交批注」只写入本地清单、不发送** —— 必须再点清单底部的 `发送给 AI`。线上库里**从无 `anno.submitted` 记录** ⇒ 该按钮从未成功触发过（要么没点，要么页面不在轨 A）。 |

---

## 1. 通道模型（谁把 UI 事件送出去）

`editor.html` 有一个策略面 `hostBridge`（`:4655-4670`，`impl()` 按 `hostKindDetect()` 选实现），四态各自实现 11 个能力：

| 能力 | static | embedded | bridge（轨 B） | mcp-app（轨 A） |
|---|---|---|---|---|
| `save` | 伴随服务 → FSAA → 另存 → 下载 | `postMessage pptx-html:save` | `POST /api/save`（CAS + receipt） | `callTool save_deck` |
| `asset` | 返回 false（走 FSAA 直写） | 返回 false（FSAA） | `POST /api/bridge/asset` | `callTool write_asset` |
| `intent` | **`copyText(fallbackText)`** ⚠️ | `postMessage` + **顺带 copyText** ⚠️ | `bridgeSubmitIntent` → `POST /api/intent` | `callTool submit_intent` |
| `status` | `probeBackend()` | 同左 | `POST /api/bridge/status` | `callTool get_status` |
| `poll` | 无 | 无 | **SSE `/api/events`** | 2s 轮询 `get_status`（无 SSE） |
| `download` | 直链 | `postMessage export-intent` | 直链 | `read_bundle_file(export/…)`（设计的降级） |
| `versions`/`rollback` | 伴随服务 | 伴随服务 | `/api/versions`、`/api/rollback` | `list_versions`、`rollback` |

**判定顺序**（`hostKindDetect`，`:1行` 区间）：
```
window.pptxMcp 存在      → mcp-app
state.embedded（window.parent!==window）→ embedded
bridge.enabled（URL 带 #brt=）→ bridge
否则                     → static
```
> ⚠️ 关键坑：**轨 A 的 iframe 里 `window.parent !== window` 同样成立**。所以若 `window.pptxMcp` 没在编辑器脚本前注入成功，轨 A 会**误判成 embedded** → 一切"发送"类操作变成 `postMessage` 给一个**不监听该消息的宿主**（我们的 WebUI 不认 `pptx-html:annotations`），并且**静默顺带复制文本** —— 表现就是"点了没反应，只好复制"。这正是并发会话给 `convertDeck()` 打的那个补丁所修的问题（`:8254-8258` 注释原文）。

---

## 2. 逐按钮 / 控件 → 数据流（只列触达外部通道的）

### 2.1 保存与版本

| 控件 | 处理器 | 通道 | 状态副作用 |
|---|---|---|---|
| `btnSave`(5933) / ⌘S(5934) | `saveDeck()`(5912) | `hostBridge.save()` | 轨 B：`bridge.loadedRevision=res.revision`、`setDirty(false)`（若期间又有编辑则保持 dirty 并提示"上一份快照已保存"）；轨 A：`mcpApp.revision=res.revision`（`saveGeneration` 匹配时）。**CAS 失败** → 轨 B `REVISION_CONFLICT` 提示 + 下载副本出口；不静默覆盖 |
| `histDrawer` 版本列表 | `hostBridge.versions()` | 轨 B `/api/versions`；轨 A `list_versions` | 只读 |
| 回滚 | `hostBridge.rollback(id)` | 轨 B `/api/rollback`；轨 A `callTool rollback` | 成功后 `latestServerRevision=j.revision` 并**重载 deck**（轨 A 还 `mcpApp.revision=res.revision`） |
| 换图 | `replaceImage`(5718) | `hostBridge.asset()` | 轨 A/B：资产先发布（receipt.revision 推进基线）→ **紧接着自动 `saveDeck()`**（资产+引用是两步发布，见 `:4555` 注释） |
| 下载产物 | `hostBridge.download()` | 轨 A `read_bundle_file(export/…)` | — |

### 2.2 意图（发送给 AI）

| 控件 | 处理器 | 渠道 |
|---|---|---|
| 脑暴「确认并发送简报」`btnBriefSend`(1175) | `bridgeSend('brief.submitted',…)`(7131) | `hostBridge.intent` |
| 设计面板「发送给 AI」`btnSendDesign`(1089) | `bridgeSend('design.submitted',…)`(6141) | 同上 |
| 批注「发送给 AI」`btnSendAnno`(5661) | `bridgeSend('anno.submitted',…)`(5665) | 同上 |
| 「复制批注指令」`btnExportAnno`(5655) | `buildAnnoExport()` → `copyText` | **纯本地复制** |
| 「一键转换导出」`btnConvert` | `convertDeck()`(8251) | **手写 `hostKindDetect()` 分支**（`embedded`→postMessage；`mcp-app`→`mcpAppSubmitIntent`；`bridge`→`bridgeSubmitIntent`）——**绕过策略面** |
| 「重新翻转」`reFlip`(8228) | `bridgeSend('convert.requested',…)` | `hostBridge.intent`（与上一行**同一功能两条实现**，属并发会话未评审改动） |
| 生图/插画（重烙当前页 / 补齐插画） | `bridgeSend('bake.requested'/'illustrate.requested',…)` | `hostBridge.intent` |

### 2.3 任务 / 恢复

| 控件 | 处理器 | 渠道 | 备注 |
|---|---|---|---|
| 「请求记录」`btnBridgeTasks`(8728) | `bridgeRenderTasks()` | 渲染 `bridge.intents` | **轨 A 里这个 map 只会被"本页面自己提交的乐观条目"填充**（见 §3.2） |
| 任务面板 4 按钮（取消/停止/重发/重建） | `bridgeCancelIntent` 等 | `bridgeFetch('/api/intent/*')` | **1027 起轨 A 不再渲染**（`:8545` 的 `if(!trackA…)`） |
| 简报区 `btnBriefStop/Retry/Resume`(7140-7146) | 同上 | 同上 | 轨 A 已按轨隐藏（**:7084-7086**，全仓唯一的 3 行按轨门控） |
| 两处 `bridgeFetch('/api/bridge/status')`(6792) / `/api/convert-status`(8242) | — | 直连 HTTP | 共享代码里的残留直连（S1） |

---

## 3. 状态机（谁在什么条件下改什么）

### 3.1 意图状态机（daemon 是唯一真相）

```
pending ──await_intent──▶ processing ──push_update(complete)──▶ succeeded
                              │  └─push_update(fail)────▶ failed ─┐
                              │  └─认领时基线过期───────▶ conflict ┼─▶ retry(rebuild) ─▶ pending(attempt+1)
                              │  └─显式 stop / daemon 重启─▶ interrupted ┤  retry(resume) ─▶ pending(att+1, 复用 work_path)
pending ──cancel──▶ cancelled                                      ┘
interrupted ──cancel(再取消)──▶ cancelled          ← 2026-10-27 P4.1 新增（此前是 no-op）
interrupted/failed ──无 lease 且超 600s──▶ cancelled ← 2026-10-27 P4.2 新增（daemon 自愈）
```

**P4（本轮已实施，见 `docs/progress/1027_p4_state_machine_hemostasis.md`）改了三件事**：`cancel` 对 `interrupted` 不再 no-op；陈旧 `interrupted/failed` 自动作废；**会话级恢复门移除**（一条卡住不再锁死整会话）。⇒ 审计文档 §2.5/§5 里"全局门 + 无放弃出口"的描述**已过时**。

### 3.2 页面侧的意图视图（问题的核心）

| 轨 | 页面如何知道"有哪些请求" |
|---|---|
| 轨 B | `bridgeStatusAndRecover()`（`POST /api/intents/query` 分页重建）+ SSE `intent-status` 增量合并 + IndexedDB 里的未确认队列 |
| **轨 A** | **只有 `get_status`**：`mcpAppApplyStatus()` 只取 `phase / resource_path / revision / capabilities / deck_path / brief_options` —— **不合并任何意图**。`get_status` 返回的 `pending_count`/`interrupted` 只被用来做**轮询退避**（`:4449` 的 `busy`）和写"状态镜"便条（`:4452`），**不进任务面板**。|

⇒ **轨 A 的「请求记录」结构性为空**：重开页面后，`bridge.intents` 是空的；只有你**在本页面里刚提交**的请求会以乐观条目出现（`mcpAppSubmitIntent` 先塞本地条目再 merge）。**这就是"AI 说还有排队请求、页面列表却空"的确切原因。**

### 3.3 真实会话证据（`s_kQifUe4NJuZ9zESIuTTFCUXL`，2026-10-28 实测）

```
session.revision = sha256:fbc7fd09…（当前）
seq1 brief.submitted    cancelled            （daemon 重启自动作废）
seq2 bake.requested     cancelled            ← P4.2 自愈（原 interrupted，10-26 起卡死）
seq3 convert.requested  conflict   base=a65de62d…（旧）  ← 已认领，基线过期
seq4-7 convert.requested pending   base=a65de62d…（旧）  ← 一旦被认领同样会 conflict
seq8 convert.requested  pending    base=fbc7fd09…（当前）← 保存之后提交的，可用

events: deck-changed{source:save, revision:fbc7fd09} @00:33:20
        intent-status{pending, 4dde312f}             @00:34:06   ← seq8
        intent-status{conflict, 7e84a189}            @00:34:17   ← seq3
clients 表：**空**  ⇒ 页面从未以"浏览器客户端"注册 ⇒ **不是轨 B**
```

**这份数据同时回答了三问**：① 00:33:20 保存后 revision 变成 `fbc7fd09`，00:34:06 提交的 seq8 用的就是**新**基线 ✅（页面确实跟随了新版本）；而 10-27 提交的 seq3-7 用的是旧基线 → 逐个 `conflict`。② 页面空列表 + AI 有计数 = 轨 A 无列表通道。③ `clients` 空 + 无 `anno.submitted` 记录 → 批注从未走到 daemon。

---

## 4. 已核实的缺陷 / 设计缺口（按影响排序）

| # | 缺口 | 证据 | 影响 |
|---|---|---|---|
| **D1** | **轨 A 无意图列表通道** | `mcpAppApplyStatus()` 不合并意图；`query_intents` 已于 1027 删除 | 用户看不到队列 → "状态混乱"的主因之一 |
| **D2** | **轨 A 无恢复通道** | 审计 §2.3（恢复族在轨 A 为 0）；`:8545` 按轨移除按钮 | 轨 A 遇到 conflict/interrupted 无按钮可点（P4 只免除了"锁死"，没给"按钮"） |
| **D3** | **`convertDeck()` 绕过策略面** | `:8258` 手写 `hostKindDetect()` 分支，与 `reFlip` 的 `bridgeSend` 重复 | 同一功能两条实现；`static` 分支被漏掉 |
| **D4** | **轨 A 误判为 embedded 的风险** | `state.embedded` 在轨 A iframe 里也为真；若 `window.pptxMcp` 未注入 → 一切发送变 postMessage + 静默复制 | 表现"点了没用，只能复制"（`convertDeck` 的注释即为此打的补丁） |
| **D5** | **「提交批注」只入本地清单** | `annoSubmit`(5530) 只 push 到 `annotations`；发送在清单底部 `btnSendAnno` | 用户以为"提交=发送"，实际还要再点一次 |
| **D6** | **旧基线产物型请求排队即 conflict** | 实测 seq3 conflict / seq4-7 将同样 | 用户看到一串"冲突"，且只能 rebuild（可能重复计费） |
| **D7** | 共享代码里的残留直连 | `/api/bridge/status`(6792)、`/api/convert-status`(8242) | S1 的剩余面 |

**不是缺陷（但看起来像）**：
- **重开后请求不消失** —— 设计如此（持久请求）；`04` 文档也写明"已接收请求及 result 不随 SSE 事件清理"。真正缺的是**展示通道**（D1）。
- **保存后旧请求变 conflict** —— CAS 的设计结果，不是回归；它保证"不会在别人已改过的版本上盲目覆盖"。

---

## 5. 给你的诊断步骤（判断你这页在哪条轨）

在编辑器页面按 F12，Console 里执行：

```js
hostKindDetect()                 // 'mcp-app' / 'embedded' / 'bridge' / 'static'
!!window.pptxMcp                 // 轨 A 的必要条件
location.hash                    // 带 #brt= → 轨 B 条件
```
再看点「发送给 AI」后的 toast：
- `请求已记录 · seq N` → 轨 B，已入队 ✅
- `请求已记录 · seq N · 等待用户确认` → 轨 A，已入队（"敲门"需你在宿主对话面板确认）✅
- `已发送宿主` → **误判成 embedded**（D4）：宿主不认这条消息，等于没发
- `指令已复制，请交给 AI coding agent` → static：设计上就是复制

---

## 6. 建议（按性价比）

1. **补轨 A 的意图列表**（治 D1，最直接影响"混乱感"）：`get_status` 已能拿到计数，最小改法是在轨 A 增加一次 `query` 或让 `get_status` 带回摘要列表 + `mcpAppApplyStatus` 合并进 `bridge.intents`（只读展示，不含恢复按钮）。
2. **修 D4 的轨判定**：`hostKindDetect()` 在 iframe 里若 `!window.pptxMcp` 应显式告警并**不静默复制**（"静默降级必须有声音"），或把嵌入态判定收窄为"确实收到宿主的 load 消息"。
3. **修 D5 的语义**：`提交批注` 后就在清单底部高亮/直接提供发送；或让"提交"在非静态态直接发送。
4. **统一 D3**：`convertDeck()` 改回 `hostBridge.intent`（顺带修掉 static 分支缺失）。
5. **D6 的可用性**：队列里出现旧基线产物请求时，在任务面板直接给出「按当前版本重建」入口（轨 A 需先有 D2 的通道）。
6. D2（轨 A 恢复族）仍建议作为独立项决策（审计 §3 建议：优先看 D1/D4 是否已消解痛感，再决定是否加**一个** app-only 恢复工具）。
