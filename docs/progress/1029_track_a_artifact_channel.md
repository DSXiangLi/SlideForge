# 1029 · 轨 A 产物通道（export/ 自动加载）

> **状态**：**已实施并自测通过（2026-10-29）**，`editor.html` **v3.10.0**
> **日期**：2026-10-29
> **来源**：用户——"一键转换导出按钮可以让 agent 正常导出 pptx，但是似乎遗漏了自动加载 export 导出的文件到 html 中？"
> **设计落点**：[`docs/design/mcp-apps-upgrade.md`](../design/mcp-apps-upgrade.md) §10.14（并更正 §5.11 / §10.10 / §10.13）

---

## 1. 现场与排查

用户点「一键转换导出」→ agent 正常导出 pptx → **页面上什么都不加载**（产物清单空、对比质检黑面、下载不可用）。

**先证伪"daemon 有问题"**。查该会话的 daemon 落盘证据（`<workdir>/.pptx-html/bridge.sqlite3`，会话 `s_kQifUe4NJuZ9zESIuTTFCUXL`，一次成功的 `convert.requested`）：

| event id | type | 时刻 |
|---|---|---|
| 39 | `deck-changed` | 00:34:49 |
| 40 | **`export-refreshed`** | 00:34:49 |
| 41 | `intent-status: succeeded` | 00:34:49 |

`export/` 产物齐全（`deck.pptx` / `deck-vector.pptx` / `deck.pdf` / `page-01..03.svg|png` / `native/page-01..03.png` / `manifest.json`），且**全部在 `bundle_files` 白名单里**（`export` 16 条 + `export-manifest` 1 条），即 `read_bundle_file` 本来就能读到。⇒ **daemon 与登记表都没问题，病在 View 侧。**

**轨 A 的病根**（三处叠加，全在 `editor.html` 的 mcp-app 分支）：

1. `openHtml` 对 mcp-app 显式 `triBaseUrl = triDeckBase = null`（"View 没有自己的产物源，相对路径会打到宿主源"，设计 §10.10 第 1 条的做法）；
2. `refreshExport` 因此只能落 `triStatus = 'unavailable'`；
3. `bridgeForceExport`（`export-refreshed` 的落点）第一行 `if(!triBaseUrl) return` **直接返回**；`buildTriPages` / `nativeUrlOf` 的产物地址也全部依赖该基址。

净效果：**产物清单恒空、对比质检恒黑面、下载按钮恒不可用**；`export-refreshed` 到了也什么都不发生——用户看到的是那句"无产物通道"的降级文案。

**这不是漏调用，是当初写进设计的降级**：`1028_dual_track_freeze_and_p31.md` 把"产物直链"列为轨 A 尚缺的三项之一，代码注释也写着"设计 §5.11 允许的降级"。当初轨 B 还在，这条降级可接受；现在决定"只保留轨 A"，它就成了必修项。

## 2. 方案

通道**现成**：app-only 工具 `read_bundle_file` 已支持 `export/` 前缀，`mcpAppHost.download` 就在用它读单个产物。差的是把 manifest 与逐页产物图也接上去。**不动 daemon、不新增工具**（不破"轨 A 不扩工具面"的红线）。

1. **`triArtifactUri(rel)` 成为产物地址解析的唯一入口**
   - 轨 A：`read_bundle_file` → `data:` URI（rel → URI 缓存；在途/失败各记一份；同一 rel 只取一次）；
   - 其余形态：基址直链——`export/…` 走 `triBaseUrl`（**须摘掉 rel 的 `export/` 前缀**，因为 `triBaseUrl` 自带该前缀），`assets/`、`fonts/` 走 `triDeckBase`。
   - `buildTriPages` / `nativeUrlOf` 改为产 **deck 根相对 rel**（`export/page-01.svg`、`export/native/page-01.png`、烙入页的 `assets/page-x.png`），交给它统一解析 ⇒ **下游渲染代码一字未改**（它们仍把返回值当 URL 用）。
2. **`mcpAppLoadExport()`**：轨 A 读 `export/manifest.json`（base64 → `TextDecoder`），取代 `triStatus='unavailable'`；取不到落 `'none'`（引导态）。`refreshExport` / 「重新读取 export/」在轨 A 都改走它（后者顺带丢弃 data: 缓存）。
3. **触发点**：① `get_status.export_revision` 变化——**轨 A 没有 SSE，这是它唯一的"产物已更新"信号**（`mcpAppApplyStatus`，同时丢缓存重读）；② 装载 deck（`openHtml` 的 `frame.onload` → `refreshExport`）；③ `export-refreshed`（轨 B 的既有路径）；④ 「重新读取 export/」按钮。
4. **按可见页懒加载**：产物图只在构建视图时经 `triArtifactUri` 触发，而视图只请求**当前页**的产物 ⇒ 不遍历整个 deck（对齐 §5.11"一期决策"的体积纪律，实测可接受）。到位后回填并重渲染。
5. **下载判据由"必须有 HTTP 基址"改为"有 manifest"**：轨 A 的下载按**文件名**走 `read_bundle_file`（`mcpAppHost.download` 自动补 `export/` 前缀），**不预取**整个 pptx 成 data URI；`triCacheBust()` 在轨 A 返回空串（data URI 不能挂查询串）。

**为什么不在渲染层逐个分支判轨**：`triArtifactUri` 是单点，轨 A/轨 B/静态的差异只活在它一处；渲染层（背面 / 对比 / 叠层 / 导出清单）继续当"URL 就是 URL"用。P3.1 的策略面纪律照旧——新增的两个轨 A 传输包装按**注册制**登记进 `aa_mcp_apps_check._TRANSPORT_CALLERS`（`mcpAppLoadExport`、`mcpAppFetchArtifact`），检查器当场拦过一次。

## 3. 验收

新增 `aa_mcp_apps_check.py` 第九臂 **⑪ `run_track_a_artifacts_arm`**（受信沙箱）：预置 deck + 完整 `export/`，发布一次让产物进白名单，然后断言——装载即读到 manifest、产物清单两行且表可见、正文**不出现**"无产物通道"、主产物下载可用、当前页产物水合成 `data:image/svg`、`export_revision` 变化触发重读 manifest。

**负向对照（已做）**：把 `editor.html` 换回修复前的 `HEAD` 版本，该臂在"等 `triStatus==='ready'`"处 **15s 超时失败**；换回修复版即 ALL PASS。⇒ 该臂确实在守这个功能，不是恒真断言。

**回归**：

| 项 | 结果 |
|---|---|
| `aa_mcp_apps_check.py` | **ALL PASS**（含新臂 ⑪） |
| `o_tri_view_check.py`（三态工作台，轨 B 侧） | **ALL PASS** |
| `tests/harness/test_bridge_core.py` | **53 passed** |
| `r_bridge_check --group sdk / apps / integration` | **PASS** |
| `build_ext_apps_bundle.py --check` | **OK**（版本单源同步） |
| 真宿主端到端（人在宿主里点一次） | **NOT_RUN**（如实标注） |

**过程中被既有测试抓到一处真回归**：`o_tri_view_check` 的 ①d 报出 `deck/export/export/page-01.svg`——rel 改成 deck 根相对后与 `triBaseUrl`（自带 `export/`）叠加，**双前缀**。修法是 `triArtifactUri` 在走 `triBaseUrl` 时摘掉 rel 的 `export/` 前缀。这正是"改动的边界外必须有回归"的价值。

## 4. 连带更正

- `docs/design/mcp-apps-upgrade.md`：§5.11 加落地注、新增 §10.14（口径以 §10.14 为准）；§10.10 第 1、2 条与 §10.13 末尾"遗留"里"轨 A 无产物通道 / 可再收一层到 13 工具"的表述**作废**——`read_bundle_file` 的 `export/` 分支现在是轨 A 的**唯一**产物通道，必须保留。
- `AGENTS.md`：轨 A 能力清单里"产物直链"由缺项改为已具备；编辑器版本升 v3.10.0。

## 5. 文件清单

- `editor.html`（v3.10.0：`triArtifactUri` + `mcpAppLoadExport` + `mcpAppFetchArtifact` + 触发点 + 下载判据 + 文案）
- `tools/ext_apps_bundle.{js,json}`（版本单源 → v3.10.0 重建）
- `tests/harness/aa_mcp_apps_check.py`（新臂 ⑪ + 传输包装登记）
- `docs/design/mcp-apps-upgrade.md`（§5.11 注 + §10.14）
- 本文件 + `docs/progress/README.md` 索引
