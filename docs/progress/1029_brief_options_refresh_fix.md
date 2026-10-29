# 1029 · 修复两处「存量红」根因：轨 B 脑暴选项不刷新 + 恢复动作寻址

> **状态**：**已实施并自测通过（2026-10-29）**；T34（theme-proving deck）按既定结论**不在本次范围**
> **日期**：2026-10-29
> **来源**：用户——"很好按你的思路修复，注意补充 progress 文档"
> **前置**：[`1029_stale_test_cleanup.md`](1029_stale_test_cleanup.md)（五条存量红的逐条定性，本文修其中两条的根因）

---

## 1. 修复一（P0）：轨 B 进入脑暴视图**必然清空** `brief_options`

### 1.1 现象与根因（定位到行）

服务端已存新的 `brief_options`，轨 B 页面重进脑暴视图却退回**静态问卷**。

- `bridgeStatusAndRecover()`（`editor.html:8871`）**内部**会赋 `bridge.briefOptions = st.brief_options || null`（`:8874`），
  但函数**末尾没有 `return`**（最后一句是 `updateHistoryBtn()`）⇒ 求值为 **`undefined`**。
- 而 `openBrief()`（`:6968-6986`）依赖它的**返回值**：
  ```js
  Promise.resolve(hostBridge.status())
    .then(function(st){ bridge.briefOptions = (st && st.brief_options) || null; ... }).then(show);
  ```
  `st === undefined` ⇒ **把刚拉到的 brief_options 覆盖成 null** ⇒ `show()` 用 null 渲染 ⇒ 静态问卷。

### 1.2 证据（探针实测四个数）

| 观测 | 结果 |
|---|---|
| 首屏 v1 正常渲染 | ✅（该路径**直接**调 `bridgeStatusAndRecover()`，不经过返回值） |
| 页面自己 `bridgeFetch('/api/bridge/status')` | **返回 v2** ⇒ daemon 无问题 |
| `hostBridge.status()` 的解析值 | 空对象 / `undefined` |
| **直接**调 `bridgeStatusAndRecover()` 之后 `bridge.briefOptions` | **v2**（内部赋值生效） |

⇒ 差异**只在"返回值"**，这就是根因。

### 1.3 影响面（用户可见）

**轨 B 里点「需求脑暴」回到的永远是静态问卷**，agent 注入的定制问题组被丢弃——`openBrief()` 注释里
承诺的"Bridge 态每次进入 brief 视图拉取最新 brief_options…重进视图生效"**从未成立**。
轨 A / 嵌入态不受影响（`mcpAppApplyStatus` 直接写字段，且轨 A 不进这个分支）——与 T35e-1 PASS 完全吻合。

### 1.4 改动与副作用核查

`editor.html`：`bridgeStatusAndRecover()` 末尾加 `return st;`（附注释说明为何必须是返回值）。
- `hostBridge.status()` 的**唯一**调用方是 `openBrief()`（`:6979`）；
- 另外三处（`:8905` resync-required、`:8931` SSE 重连、`:9012` 心跳后）是**直接调用、不读返回值** ⇒ 加 return 无副作用。

### 1.5 验收

**T35 现在 `RESULT: ALL PASS`**（此前 3 FAIL）：T35d-1「页面重进 brief 视图取到新值」、
T35d-3「不带参后页面仍为新值」、T35f 动态作答段全部转 PASS。1 行修 + 既有测试自动回归。

---

## 2. 修复二（P1）：恢复动作迁移后的**可寻址性**与测试重写

### 2.1 背景

v3.9.9 的按钮简化把简报区三个恢复按钮（`btnBriefStop/Resume/Retry`）删除，动作并入**任务面板**：
入口 `#btnBriefTasks`「查看请求记录」（`editor.html:7323-7329`：退出简报视图 + `$('bridgeTasks').classList.add('show')`），
动作按钮由 `bridgeRenderTasks()` 渲染（`:8805+`，文案 **取消 / 停止 / 确认重发 / 继续上次 / 重新生成**）。

问题：面板行**没有 intent id** ⇒ 无法稳定定位"某条 intent 的动作按钮"。

### 2.2 改动

1. **应用侧 1 行**：`bridgeRenderTasks()` 的行加 `row.dataset.intentId = x.id` ⇒ 面板可稳定寻址
   （测试/自动化按 intent 定位动作按钮；也让"哪一行对应哪条请求"在 DOM 里显式化）。
2. **测试侧**：`r_bridge_check.py --group ui` 该段按任务面板重写：
   - 新增 `brief_open()`（浮层已开就不再点 rail 按钮——它会被浮层盖住）与
     `panel_open()`（按入口展开面板；若浮层仍在则关掉它，否则面板不可点）；
   - `panel_btn(iid, label)` 用 `[data-intent-id="…"] button:has-text("…")` 定位；
   - 断言"恢复入口在 reload 后仍在"改为 `#btnBriefTasks` 存在 + 面板行含「重新生成」
     （等价于旧的"recovery action restored from query/IndexedDB"）；
   - **保留确认框步骤**——`askConfirm` 在**策略面**里（`bridgeStopIntent:8991`、`bridgeRetryIntent:8998`），
     面板按钮与旧简报区按钮**共用**同一套确认，故 `#confirmMask/#confirmOk` 仍需点
     （这条纠正了我先前"面板动作不带确认"的判断）。
3. **顺带两处断言健壮性修正**（都在同一段、都会误报）：
   - `#bridgeState` 的允许集只列了「Bridge 已同步/offline/waiting」，漏了合法的 **`Bridge working`**
     （agent 正忙时渲染 `'Bridge ' + agent_state`）→ 改为断言"以 `Bridge` 开头"；
   - 浮层残留会盖住面板/rail 按钮 → 由 `panel_open()` 统一处理。

### 2.3 验收

`r_bridge_check.py --group ui` **连续 8 次 PASS**（改动前该组必崩）。

**顺带排掉三类"潜伏的时序假设"**（都是 P0 修复后才暴露出来的**既有**问题——该组此前在 `#btnBriefGen` 就崩，
后面这些断言**从未被执行**过；`openBrief()` 的 `show()` 本来就在 `hostBridge.status()` 之后，所以不是本次引入的）：

| 位置 | 旧写法（同步读） | 新写法（等待式） |
|---|---|---|
| 首份 deck 后的状态条断言 | 一次性 `inner_text()` 与三个标签比对 | 等 `#bridgeState` **可见且非空**（`#bridgeBar` 在简报模式下被 CSS 隐藏，同步读会读到空串） |
| 未知 view 回落脑暴 | 只等 `data-launch==='brief'`（**同步标记**）就断言浮层已显示 | 追加等浮层**真的显示** |
| `brief_open()` | 点一次 `#btnBrief` | 有界重试（实测竞态：`view-hint` → `applyLaunch` **不受 `launch.applied` 保护**，会把刚点开的脑暴视图拽回工作台；探针实测超时那刻 `launch=null`/`overlay=false` 而 `bound/connected/briefRendered` 均正常） |

**遗留**：该组其余"同步假设"未逐一改造（本次只修实际打到的三处）；若后续再遇偶发，按同一口径改成等待式即可。

---

## 3. 明确不在本次范围

- **T34-theme-proving 仍红**：deck 实为 7 主题 × 8 页型 = 56 页（无 g3）、`data-ig` 只在 g1/g2/g4、
  e1/e4/g4/g5 存在真实重叠 —— 属**主题轨道的内容任务**（补 8 页 + 修几何 + 补 ig 根），
  按既定结论**不动测试期望**（改期望＝改尺子迎合测量）。见
  [`1029_stale_test_cleanup.md`](1029_stale_test_cleanup.md) §2 与
  [`test_acceptance/mcp-apps-upgrade.md`](../test_acceptance/mcp-apps-upgrade.md) §2.5.2。

## 4. 文件清单

- `editor.html`：`bridgeStatusAndRecover()` 补 `return st;`（P0）；`bridgeRenderTasks()` 行加 `data-intent-id`（P1）
- `tests/harness/r_bridge_check.py`：ui 组按任务面板重写（`brief_open`/`panel_open`/`panel_btn`）+ 两处断言健壮性修正
- 本文件 + `docs/progress/README.md` 索引
