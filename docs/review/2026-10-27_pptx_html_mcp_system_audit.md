# pptx-html 四态编辑器 · MCP 面系统复盘（2026-10-27）

> **触发**：用户提问「为什么琐碎问题一个接一个地蹦出来，请对 html-pptx 的所有 MCP 功能、所有用户操作路径、所有操作按钮做一次系统复盘」。
> **结论一句话**：不是"bug 多"，而是**架构里有三层都在干同一件事，而抽象层被绕过**；叠加**意图状态机没有"放弃"出口 + 一道全局门**，于是任何一次 daemon 重启都会把会话钉死，表现出来就像互不相关的小毛病。
> **取证方式**：静态扫描 `editor.html`（54 个事件绑定 / 34 处直连通道 / 四态实现区间）+ 读 daemon 状态机源码 + 读线上库里的一条真实卡死意图。方法可复现，见 §6。
> **证据纪律**：本报告区分「逐条读过源码的已验证实例」与「静态扫描的候选」；后者一律标注，不当作结论。

---

## 1. 为什么是"打地鼠"：三个结构性原因

| # | 结构 | 后果 |
|---|---|---|
| **S1** | **三层并存、策略层被绕过**：`hostBridge` 策略面（11 能力 × 4 态）本该是唯一入口，但 `bridge*`（轨 B）与 `mcpApp*`（轨 A）两族函数**住在共享 UI 代码里**，被按钮直接调用 | 加一个能力/按钮要改三层；改漏一层就是"某个态下点了没用"，而且**看起来与上一个 bug 无关** |
| **S2** | **意图状态机没有"放弃"出口，却有一道全局门**：`await_intent` 只要会话里存在 `failed/conflict/interrupted` 就拒绝一切新认领（`bridge_core.py:1105`）；而 `cancel_intent` 对 `interrupted` 是 **no-op** | 一条陈旧意图 → 整个会话发不出请求，且**没有任何受支持的出路**（本次实测：一条 10-27 07:59 的 bake 把会话堵了 9 小时） |
| **S3** | **daemon 重启是常态，而它每次都制造 S2 的燃料**：启动时把 `processing` 全部改写成 `interrupted`（`bridge_core.py:585`，只有 `brief.submitted` 例外 → `cancelled`） | `run_local.py` 每次起服务都会杀 daemon；开发环境里"重启即制造卡死"几乎是必然 |

---

## 2. 事实盘点（全部有据可查）

### 2.1 MCP 工具面 × daemon 路由 × 鉴权

| 层 | 数量 | 说明 |
|---|---|---|
| 面向模型的工具 | 5 | `open_editor` `await_intent` `push_update` `get_status` `close_session` |
| app-only 工具（`ui.visibility:["app"]`） | 9 | `attach_view` `read_deck` `read_bundle_file` `save_deck` `write_asset` `submit_intent` `save_draft` `list_versions` `rollback`（1027 精简后） |
| daemon 路由（`_api`） | 28 + `/api/health` + `/bootstrap` | 18 条经工具暴露、1 条内部（`/api/bridge/heartbeat`）、**9 条不暴露给任何工具** |
| 未暴露的 9 条 | — | `/api/convert`、`/api/imagegen`、`/api/bridge/bootstrap`、`/api/bridge/stop`、`/api/events`(SSE)、`/api/convert-status`、`/api/imagegen-status`、`/api/bridge/drafts`(GET)、`/api/bridge/draft`(GET) |
| 鉴权 | — | 多数 `_management()`；`status`/`intent`/`retry`/`cancel`/`query`/`save`/`rollback`/`asset`/`convert`/`imagegen` = management 或 browser；`drafts` 列 = browser |

**缺口（S2 的工具面投影）**：`retry_intent` / `cancel_intent` / `query_intents` 在 1027 被删（当时证据：全仓无 View 调用方）。它们的 daemon 路由仍在，但**轨 A（沙箱）没有凭证走 HTTP**，于是**轨 A 彻底没有任何恢复意图的通道**。

### 2.2 四态 × 11 能力 × 实现分布

四个 host 对象的行区间（静态测出）：`staticHost 3862-3946`、`embeddedHost 3949-3983`、`bridgeHost 3986-4059`、`mcpAppHost 4502-4603`。

能力面覆盖是**完整**的（11/11 × 4 态都在），所以问题不是"某态缺能力"，而是**共享 UI 绕过它们**：

| 直连通道 | 总调用点 | 在四态实现内部（合法） | **在共享 UI 代码里** |
|---|---|---|---|
| `bridgeFetch(` | 19 | 4 | **15**（`bridgeSubmitIntent` `bridgeResendIntent` `bridgeCancelIntent` `bridgeStopIntent` `bridgeRetryIntent` `bridgeRecoverIntents` `bridgeLoadDeck` `bridgePersistDraft` `bridgeConnectSSE` `bridgeStatusAndRecover` `bridgeForceExport` `bridgeHeartbeat` `openBrief` `pollConvertStatus` `normCssVal`） |
| `mcpAppCall(` | 15 | 6 | **9**（`mcpAppBoot` `mcpAppLoadDeck` `mcpAppHydrateImage` `mcpAppHydrateCss` `mcpAppPollOnce` `mcpAppPersistDraft` `mcpAppSubmitIntent` …） |
| `hostBridge.<能力>()` 分派 | **8** | — | 其余全部按钮不经过策略面 |
| `window.parent.postMessage` | 5 | — | 嵌入态专用 |

⇒ **34 处直连通道里只有 4+6 处在"该在的地方"**；`hostBridge` 这个抽象层实际只被 8 处使用。这就是 S1 的量化证据。

### 2.3 能力在轨间的对称性（缺陷的滋生地）

| 能力 | 轨 B 侧函数 | 轨 A 侧函数 | 是否对称 |
|---|---|---|---|
| 提交意图 | `bridgeSubmitIntent(8678)` / `bridgeSend` | `mcpAppSubmitIntent(4485)` | ✅ |
| 草稿 | `bridgePersistDraft(8433)` | `mcpAppPersistDraft(4442)` | ✅ |
| 载入 deck | `bridgeLoadDeck(8501)` | `mcpAppLoadDeck(4229)` | ✅ |
| 状态/轮询 | `bridgeConnectSSE(8634)` + `bridgeStatusAndRecover(8584)` | `mcpAppPollOnce(4402)` | ✅（通道不同） |
| 保存 / 资产 / 版本 / 回滚 / 下载 | `hostBridge.save/asset/versions/rollback/download` | 同（策略面） | ✅ **（这四项做对了：走分派）** |
| **取消 / 停止 / 重试 / 查询意图** | `bridgeCancelIntent(8692)` `bridgeStopIntent(8697)` `bridgeRetryIntent(8706)` `bridgeRecoverIntents(8577)` | **无** | ❌ **不对称** |

⇒ 唯一不对称的能力族，正是**恢复**族。这解释了为什么"取消/停止/重建"按钮在轨 A 必然失败，也解释了 1027 之后轨 A 为什么无路可走：**这不是按钮写错，是这一族在轨 A 从来就没有实现过**。

### 2.4 按钮 / 控件清单（54 个绑定）

- **28 个纯视图或本地状态**（视图切换、分段、对比滑块、目录、翻转…）——无外部通道，风险低。
- **26 个触达外部通道**（含传递可达，候选需逐个复核）。逐条读过的**已验证缺陷实例**：

| 控件 | 行 | 处理器 → 通道 | 判定 |
|---|---|---|---|
| `btnBriefStop` | 7146 | `bridgeStopIntent` → `bridgeFetch('/api/intent/cancel')` | 轨 A 必失败（已按轨隐藏，但通道侧无自愈） |
| `btnBriefRetry` / `btnBriefResume` | 7140 / 7145 | `bridgeResendIntent` / `bridgeRetryIntent` → `bridgeFetch('/api/intent/retry')` | 同上 |
| 任务面板 4 按钮 | 8545-8549 | `bridgeCancelIntent` / `bridgeStopIntent` / `bridgeRetryIntent` / `bridgeResendIntent` | 同上（1027 起轨 A 不再渲染） |
| `btnConvert` | 8279 | 现按 `hostKindDetect()` 分派 | ✅ 已修（并发会话所为，非本轮） |
| `btnBrief`(6812) / `annoSubmit`(5530) | — | 静态扫描报"B"，实读为**纯视图/本地态** | ✅ 扫描假阳性，已排除 |

**状态门控的写法**：全仓只有 **3 行**按轨隐藏控件（`editor.html:7084-7086`，1027 加）+ 1 处 `if(!trackA&&…)`（`:8545`）。⇒ 新控件默认"到处都显示"，门控靠人记。

### 2.5 意图状态机（daemon 真相 vs UI 呈现）

| 侧 | 状态集合 |
|---|---|
| daemon（`INTENT_STATUSES`） | `pending` `processing` `succeeded` `failed` `conflict` `interrupted` `cancelled`（7） |
| 前端另有 | `submitting` `unconfirmed` `retrying`（3，纯 UI 反馈态） |

迁移与出口（源码行）：

| 从 | 到 | 触发 |
|---|---|---|
| pending | processing | `await_intent` 认领 |
| pending | cancelled | `cancel_intent`（`:1319`） |
| processing | succeeded | `push_update(complete)`（`:1578`） |
| processing | failed / conflict | `push_update(fail)`（`:1390`）/ 认领时基线冲突（`:1178`、`:1408`） |
| processing | interrupted | 网页显式 stop（`:1311`）、daemon 重启（`:585`） |
| **failed / conflict / interrupted** | **下一 attempt** | `retry_intent(rebuild\|resume)`（`:1269` 起）——**唯一出口** |
| interrupted | **（无）** | `cancel_intent` 对该状态**直接 return**（`:1322` 尾部分支） |

**两道结构性墙**：

1. **全局门** `bridge_core.py:1105`：`SELECT 1 FROM intents WHERE session_id=? AND status IN ('failed','conflict','interrupted')` 命中 → `RECOVERY_REQUIRED`，**拒绝一切新认领**。一条陈旧意图即可让整个会话失去工作能力。
2. **无"放弃"出口**：`cancel_intent` 只处理 `pending`/`processing`；`interrupted` 要出去只能 `retry`。而 `mode=resume` 还要求**上一 attempt 的 `base_revision` == 当前 revision**（`:1280` 起），基线一漂移就只剩 `rebuild`（重跑、可能计费）。

**本次实测的卡死实例**（该 workspace 的真实库）：

```
intents 35fbd594-29c0-41ee-b064-55cbbbde3985  bake.requested  interrupted  attempt=1
  error = {"code":"RECOVERY_REQUIRED","message":"daemon-restarted"}   created 10-26T23:56:52Z  updated 23:59:40Z
会话 s_kQifUe4N…  pending=4  recoverable=1   → await_intent 一律 RECOVERY_REQUIRED
```
attempt-1 基线 `sha256:c187b808…` 与会话当前 `sha256:a65de62d…` **不同** ⇒ `resume` 被拒 ⇒ 只剩 `rebuild`；而"放弃"做不到。**4 条后续提交的 `convert.requested` 全部卡在 pending**——用户看到的正是"发不出去"。

### 2.6 静默与漂移

| 项 | 实测 | 备注 |
|---|---|---|
| 空 `catch` | `catch(e){}` **17 处** | 与项目自己的规则「静默降级必须有声音」相悖 |
| SKILL.md 引用不可见工具 | 1 处（D4 让模型用 `cancel_intent`；该工具历来对模型不可见） | 1027 已改写 |
| acceptance 记法过期 | 1 处（记 F4 之前的"根级 + ui 双写"） | 1027 已修 |
| harness 定位器漂移 | 1 处（点 `#btnBriefGen`，该 id 已不存在）→ `ui` 组既有红 | 1027 未触碰，仍红 |

---

## 3. 简化门报告（对我自己给的修复路线做减法）

| 候选 | 分解 | 简化门裁决 |
|---|---|---|
| ① 为轨 A 加回 `retry_intent`/`cancel_intent` 工具并接线 | 这是"加能力"（+2 工具、改红线、改编辑器、再评测） | **砍掉/推迟**。先看有没有不加面就能解卡的路（见 ③ 的最小形态）。只有证明"用户确实需要在页面里重试烙入"时才回来加**一个**工具 |
| ② 静态不变量：共享 UI 直连通道需登记 | 复用已有 harness 检查机制（不新建框架、不引新工具链） | **纳入，最小形态**：在既有 harness 里加一条"登记制"断言（新增未登记的直连调用点即失败）。这是唯一能**一次挡住一整类**的东西 |
| ③ `cancel` 对 `interrupted` 不再 no-op | 一个分支、一个文件 | **纳入（P0）**；但**单靠它不够**——轨 A 无通道调用它。配套最小解：**daemon 侧自愈**（把"永久堵门"改成"可自愈"），见下 |
| ④ 统一状态枚举 | 无已知缺陷可归因 | **推迟**（不为整洁性动刀；等真的有 bug 指向它） |
| ⑤ 新增 JS lint 禁空 catch | 编辑器红线是"纯静态、零构建"，引入 lint 工具链 = 破红线 | **降级**：并入 ② 的同一条登记检查；17 处暂不批量改，只修"用户可见静默失败"的（`replaceImage` 已修） |

**最简解卡方案（不需要新增任何工具/按钮/红线变更）**：让 daemon 自己收拾陈旧中断——在启动 bookkeeping 或新意图入队时，把"基线已漂移且无人持有 lease 的 `interrupted`"自动推进为 `cancelled`（带原因 + 发 `intent-status` 事件，满足"事事有回响"）。一处改动 ≈ 10 行，**门即不再永久堵**。是否允许"自动放弃"属状态机语义变更，**需用户签字**。

---

## 4. 用户操作路径 × 四态（哪些是结构性不可用，哪些是"假可用"）

| 路径 | static（裸静态） | embedded（嵌入） | bridge（轨 B） | mcpApp（轨 A） |
|---|---|---|---|---|
| 打开文件 / 换图 | FSAA 或下载 | 内置文件框 | FSAA / 内置框 | 内置框（**保存/换图被告知拒绝**：本地画布守卫） |
| 保存 | 另存/下载 | postMessage 给宿主 | CAS 保存 | `save_deck` ✅ |
| 脑暴 / 设计 / 批注提交 | 复制文本给 agent | postMessage | intent 队列 | `submit_intent` ✅ |
| 转换 / 烙入 / 插画 | 复制指令 | postMessage intent | intent 队列 | `submit_intent` ✅ |
| 状态回执 | 无 | 无 | SSE + 轮询 | `get_status` 2s 轮询（**无 SSE**） |
| 版本 / 回滚 | 无 | 无 | ✅ | ✅（`list_versions`/`rollback`） |
| 产物下载 | 直链 | 宿主交付 | 直链 | `read_bundle_file(export/…)`（**设计声明的降级**，`editor.html:4881`/`:7600`） |
| **意图恢复（取消/停止/重试）** | 不适用 | 不适用 | ✅ 按钮 + HTTP | ❌ **结构性缺失**（§2.3）→ 被 S2 堵死时无出路 |

"**假可用**"这一类（控件可见但通道不可用）就是本次与 1027 反复撞到的东西；它的成因不是回归，而是 **S1**：这一族能力从来没在轨 A 实现过。

---

## 5. 路线（P0/P1/P2）与明确不做

**P0（止血，小改）**
1. daemon 侧自愈：陈旧 `interrupted`（基线漂移 + 无 lease）→ `cancelled` + 事件（§3 最简解卡）。**需签字**（状态机语义）。
2. `cancel_intent` 支持 `interrupted`（显式放弃），使轨 B/CLI 有正当放弃路径。
3. 三个 `bridge*` 恢复按钮的通道判定收敛到策略面（或明确登记为"仅轨 B"），消除"点了没用"。

**P1（防复发，一次挡一类）**
4. ② 的登记制静态断言进 harness：`bridge*`/`mcpApp*` 在共享 UI 里的直连调用点必须登记；未登记即失败。顺带把 ⑤ 的空 catch 允许清单并进来。
5. 把"门"改成 **per-intent**：`await_intent` 只阻塞"存在 processing 且未终结"的情形，而不是"存在任何 failed/conflict/interrupted"。这是一处改动、直接影响 S2 的破坏半径。**需签字**。

**P2（清理）**
6. 文档/harness 定位器漂移（`#btnBriefGen`）、17 处空 catch 的白名单化、④ 状态枚举（**推迟**）。

**明确不做（本次及可预见期内）**
- **不**为轨 A 新增恢复工具/按钮（先看 P0-1/P1-5 是否已消灭卡死；真需要再回来加**一个**）。
- **不**引入 JS lint 工具链（破"零构建"红线）。
- **不**为了统一而统一状态枚举（④）。
- **不**把轨 A 改回"浏览器直连 HTTP + 凭证下发"——那会与 §10.10 的方向相反（且依赖仓库默认关闭的 `allow-same-origin`）。

---

## 6. 取证方法（可复现）

```bash
# ① 控件 → 通道/守卫 矩阵（大括号配平 + 深度 2 可达）
python3 /tmp/inv2.py            # 表：id / 事件 / 处理器 / 行 / 通道与状态守卫
# ② 直连通道归属：在四态实现内部 vs 共享 UI（本次报告的核心证据）
python3 /tmp/inv4.py            # 输出 19/15 与 15/9 的拆分
# ③ daemon 路由 × 鉴权
grep -nE 'if path=="/api' -A2 tools/bridge_core.py
# ④ 意图状态机与全局门
sed -n '1096,1108p;1269,1300p;1302,1325p;565,590p' tools/bridge_core.py
# ⑤ 线上实例（只读）
#    /api/bridge/status + /api/intents/query（management 凭证取自 <workdir>/.pptx-html/serve.json）
```

> 脚本目前只是审计仪器（`/tmp`，未入库）。若 P1-4 获批，把它按"登记制"改写成 harness 里的一条断言再入库（一个文件、一条检查，不建框架）。

---

## 7. 未决 / 待签字

1. **P0-1 自动放弃**：允许 daemon 把陈旧 `interrupted` 自动转 `cancelled`？（改状态机语义）
2. **P1-5 门改为 per-intent**：是否接受"只有存在未终结 processing 时才阻塞"？（同样改语义，但直接缩小 S2 的破坏半径）
3. 本次仍挂在树上的**并发会话改动**（`convertDeck()` 按 `hostKindDetect()` 分流）：保留还是回退——与本报告无关，但同属"未决"。
4. 线上那条卡死意图（`35fbd594…`）是否现在处理：`rebuild`（重跑烙入，可能计费）／等 P0-1 落地后自动放弃／手改 DB（不推荐）。
