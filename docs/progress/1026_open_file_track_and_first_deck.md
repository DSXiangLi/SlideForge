# 1026 · 宿主内「打开文件 / 换图」回正 + 首份 deck 到达切编辑页（editor v3.9.5）

> **日期**：2026-10-26
> **触发**：宿主侧把 View iframe 的 sandbox 改为 `allow-scripts allow-same-origin`（编辑器终于能访问渲染文档、能进编辑态）之后，**文件选择类 API 在子框架里依旧被拒**——用户报告宿主内「打开文件」不可用；同批排查发现「脑暴页 → agent 生成 deck → 自动进编辑页」这条链**从未发生**。
> **改动**：`editor.html` v3.9.4 → **v3.9.5**（+ `tools/ext_apps_bundle.json` 的 `view_version`，版本号单源在 editor 头部，**改版本必须重建 bundle**）；`tests/harness/aa_mcp_apps_check.py` 新增两条臂（⑨⑩）。
> **证据纪律**：本机没有真宿主，宿主内的人工实际操作仍是 **NOT_RUN**；每条结论下面都标注"已验证 / 未验证"。跑分与日志见 §3。

---

## 1. 三处根因

### 1.1 「打开文件」：能力探测为真、调用必被拒（轨优先 vs 能力）

`openViaPicker()` 原先只按 `state.fsaa`（`typeof window.showOpenFilePicker === 'function'`）分支：宿主 iframe 里该函数**存在**，但调用被宿主权限策略拒绝 → 抛错被 catch 成一句 `toast('打开失败：…')`，而内置的 `<input id="fileInput">` 回路**永远走不到**。

同一课在 v1.1 已经上过一次（保存路径：`embedded && !fsaa` 在 FSAA 存在的宿主里失效、保存被静默吞掉 → 改为"嵌入态一律 postMessage"）。所以本次按同一口径修：**轨优先、能力其次**。顺带把"探测为真但调用被拒"的出口改成"说明原因 + 回落文件选择框"，不再只弹提示。

### 1.2 首份 deck 到达：轮询条件对 briefing 会话恒假

`mcpAppPollOnce()` 的远端变化条件是

```js
if (st.revision && mcpApp.revision && st.revision !== mcpApp.revision)   /* 旧 */
```

而 `open_editor(view="brief")` 建的是 **briefing 会话**（`deck_path=NULL`、`revision=NULL`），`mcpApp.revision` 因此是 `null` → 条件恒假 → `mcpAppLoadDeck()` 永不调用 → **不 read_deck、不关脑暴、不进编辑视图**。agent 生成完 deck 后页面停在脑暴页（用户看到的症状）。

下游其实全通：`mcpAppLoadDeck → read_deck → openHtml（复位 view='edit'）→ launchOnDeckReady() → closeBrief()`。修法就是把"首份 deck"也算成一次变化：`st.deck_path && st.revision && st.revision !== mcpApp.revision`（`st.deck_path` 是"这轮终于有 deck 可读"的判据）。

### 1.3 换图：同一类缺陷 + 空 catch（静默 no-op）

`replaceImage()` 同样是 `state.fsaa`-only 判定，且 `catch(e){ return; }` 是**空 catch**——宿主内点「替换图片」是彻底的静默 no-op（与项目"静默降级必须有声音"的约定冲突）。轨 A 里本该走 `hostBridge.asset() → mcpAppHost.asset → write_asset`，这条路径从未跑到。

### 1.4 顺带发现的两个"修好入口也仍然不工作"的洞（本次一并修，否则 §1.3 等于只修一半）

1. **CAS 基线不前进**：`mcpAppHost.asset` 原先不更新 `mcpApp.revision`，而资产写入是一次**独立发布**（revision 前进）→ 紧随其后的 `saveDeck()` 用旧基线发 `save_deck`，**必然** `REVISION_CONFLICT`（实测：资产落盘了，HTML 引用没保存，`state.dirty` 一直是 true）。轨 B 的 `bridgeHost.asset` 是同一处理（`bridge.loadedRevision=receipt.revision`），轨 A 漏了。
2. **取文件名取错源**：`replaceImage` 从 `img.src` 推当前文件名/目录，而轨 A 的图片是经 `read_asset` 水合成的 **data: URI**（相对路径留在 `data-pptx-src` 里）→ 算出 `assets/iVBORw0…==.png` 这种垃圾名，写进受管 bundle 并把引用指向不存在的文件。改为 `data-pptx-src` 优先。

---

## 2. 改动清单（`editor.html` v3.9.5，行号为改后）

| 位置 | 改动 |
|---|---|
| `:4756` | 新增 `localPickerUsable()`：`state.fsaa && hostKindDetect() ∉ {embedded, mcp-app}`（轨优先、能力其次） |
| `:4763` | 新增 `pickFileOnce(inputId)`：一次性 `<input type=file>` 选择，窗口重新获得焦点兜底"用户取消"（避免 Promise 永久挂起） |
| `:1189` | 新增 `<input type="file" id="imageInput" accept="image/*…" hidden>`（换图回路） |
| `:4784` | `openViaPicker()`：`localPickerUsable()` 才走 FSAA；嵌入/轨 A 直接 `fileInput`；FSAA 真失败时**说明原因后回落**文件选择框 |
| `:5671` | 新增 `replaceImageUsable()`：轨 A 看 `mcpAppCanvasManaged()`，其余轨看 `state.fsaa`（按钮禁用态用） |
| `:5677` | 新增 `pickImageFile()`：轨 A 不走 FSAA，直接用 `imageInput`；其余轨沿用 FSAA，失败有声音 |
| `:5692` | `replaceImage()`：开头只做"取文件"，空 catch 删除；`:5699` 目录/文件名改从 `data-pptx-cache-orig → data-pptx-src → src` 取 |
| `:5200` `:5305` | `btnReplaceImg.disabled` 由 `!state.fsaa` 改为 `!replaceImageUsable()` |
| `:4090` `:4091` | 新增 `mcpAppCanvasManaged()` / `mcpAppRefuseLocalCanvas()`：**本地画布守卫**（见 §2.1） |
| `:4502` | `mcpAppHost.save`：`!mcpAppCanvasManaged()` → 拒绝（toast + 横幅 + 「下载副本」出路），**不调 save_deck** |
| `:4531` | `mcpAppHost.asset`：同一守卫（本地画布的图不许写进受管 bundle） |
| `:4549` | `mcpAppHost.asset`：`mcpApp.revision = receipt.revision`（CAS 基线前进，§1.4-1） |
| `:4553` | `mcpAppHost.asset`：渲染用 `data:`、**引用**留在 `data-pptx-src`（序列化还原 `assets/` 相对路径，"磁盘 deck 必须纯净"红线） |
| `:4402` | `mcpAppPollOnce`：变化条件加 `st.deck_path`（§1.2） |
| `:4415`-`:4421` | `mcpAppPollOnce`：`idlePolls` 只增不减的旧行为改为——检测到变化或有**在途工作**（`pending_count`/`processing`）就复位并回到 2s，否则才累积退避到 10s |

### 2.1 本地画布守卫（配套、必须）

`openHtml()` 对"无句柄"的文件（`fileInput` / 拖拽 / 嵌入加载）会把 `state.deckPath` 置 **null**，而轨 A 的保存路径是 `mcpAppPath(state.deckPath)`——传 null 时它回落到 `mcpApp.resourcePath`，也就是**把用户本地打开的文件写进 agent 管理的 deck**。§1.1 的修法让宿主内"打开本地文件"成为可能，这个洞就成了真陷阱。

**选择：拒绝**（而不是"证明安全"，因为无法证明）。轨 A 里画布不是本会话受管 deck 时，保存与换图一律中止、给可读原因与两条出路（下载副本 / 独立窗口）。代价是轨 A 不能编辑本地文件；收益是**不可能**覆盖 agent 的 deck。

---

## 3. 验证

| 项 | 命令 | 结果 |
|---|---|---|
| JS 语法 | 抽 `<script>` → `node --check` | OK |
| bundle 一致性 | `python3 tools/build_ext_apps_bundle.py --check` | `OK`（改版本后已重建，`view_version: 3.9.5`） |
| T36 全量（含新臂 ⑨⑩） | `python3 tests/harness/aa_mcp_apps_check.py` | `RESULT: ALL PASS` |
| 新臂稳定性 | ⑩ 连跑 5 次 | 5/5 PASS |
| 变异测试（断言非恒真） | 把 `:4402` 条件改回旧式（`st.revision && mcpApp.revision && …`）后跑 ⑨ | **必红**：`等待超时（25s）：首份 deck 到达后 View 调 read_deck` —— 复现的正是用户报告的症状 |
| 全量 e2e | `python3 tests/harness/run_e2e.py` | **62 项 58 PASS / 4 FAIL**（`_logs/1026_run_e2e_v395.log`）。FAIL = **T29-bridge / T31-brief / T35-dynamic-brief**（前一轮未提交的 `#btnBriefGen → #btnBriefSend` 改名未同步 harness 定位器，属**改动前既有**，见 `docs/test_acceptance/mcp-apps-upgrade.md` §2.5.1）+ **T34-theme-proving**（既有）。与本次改动相邻的 **T36（轨 A）与 T17（图片上传）均 PASS** |

### 3.1 T36 新增的两条臂（`aa_mcp_apps_check.py`）

- **⑨ 首份 deck 到达**：无 deck 的 briefing 会话 → 页面点真按钮 `#btnBriefSend`（走 `submit_intent` 工具）→ agent 侧只经真 daemon 路径认领 intent、在工作副本写 deck、`push_update complete` 发布 → 断言 View `read_deck`、渲染、`data-launch` 被摘除、chrome 恢复、落编辑页签。
- **⑩ 本地画布守卫 + 轨 A 换图**：(a) 用 `openHtml(text, 'local.html', null, undefined, null)` 造出与 `fileInput` 回路完全同形的本地画布 → `saveDeck()` 断言**没有** `save_deck` 调用、横幅说明原因、受管 deck 字节未变；(b) 回受管画布后驱动真 `replaceImage()`（用 Playwright 的 `filechooser` 事件喂文件）→ 断言走 `write_asset`、`data-image-state=uploaded`、保存成功后产物里是 `assets/pixel.png` 且**无** `data:` URI。

**harness 踩坑（写进用例注释）**：轮询谓词必须落在**浏览器侧**（`frame.evaluate`）。纯 Python 的 `sleep` / 读文件不驱动 Playwright 同步 API 的回调分发，宿主的 `mcpCall` 绑定会一直挂着——实测表现为"保存卡 ~15s 才落地"，一度被误判成产品缺陷。

### 3.2 未验证（如实标注）

- **真宿主内的实际点击**（「打开文件」弹出文件选择框、换图弹框、brief→edit 的视觉切换）：本机无宿主，**NOT_RUN**。
- 文件选择框在宿主 iframe 里能否真正打开（`<input type=file>` 在 sandbox 子框架里的行为）：**未验证**——只验证了"代码走这条回路且不再静默"。若宿主侧连 `<input type=file>` 也拦，需换宿主侧提供文件通道（届时是本设计的下一个缺口）。
- 轨 A 换图后 `saveGeneration` 守卫导致的"canvas revision 偶发滞后 → 轮询随后自动重载一次"：观察到的**既有**行为（`mcpAppHost.save` 与 `bridgeHost.save` 共用同一守卫），不阻断交付，未改。

### 3.3 全量 e2e 里的既有红（与本次改动的关系）

`==== 汇总：62 项，58 PASS，4 FAIL ====`（`_logs/1026_run_e2e_v395.log`）
- **T29-bridge / T31-brief**：`waiting for locator("#btnBriefGen")` 超时——`editor.html` 工作树里该按钮已被前一轮未提交的工作改名/合并为 `#btnBriefSend`，而 `k_brief_check.py`、`r_bridge_check.py`、`y_dynamic_brief_check.py` 仍点旧 id（`git show HEAD:editor.html` 仍是旧 id；基线 `1024_run_e2e_baseline.log` 里 T31/T29 仍 PASS）。本次改动只新增 `#imageInput` 与文件选择/轮询逻辑，未触碰该按钮。**修复需复核语义**：新按钮把"预览"与"发送"合并成一步，轨 B 下点击会真的提交 intent。
- **T35-dynamic-brief**：`1023` 起每次都红的**既有**失败，签名同族（`waiting for locator("#btnBrief")` 超时，行号随时序漂移）。机制：`bridgeApplyEvent` 的 `view-hint` 分支**无条件** `applyLaunch(data.view)` → 一次 `open_editor(view="brief")` 会把用户刚关掉（或正要操作）的脑暴视图重新盖上来。**是否算缺陷属设计判断**（§6 的语义是"每次 open_editor 的 view 都生效"），本次只记录不动。
- **T34-theme-proving**：既有失败（主题轨道待办，AGENTS.md 已记）。

---

## 4. 与既有文档的关系

- `docs/design/brief-page-split.md`：补 §18（首份 deck 到达的实现缺口与修法）。
- `docs/design/design-editor.md` §3.1/§3.2/§9：文件打开矩阵补"宿主轨用内置文件选择框"。
- `docs/test_acceptance/mcp-apps-upgrade.md` §2.3：T36 断言面更新。
