# 1029 · 存量红测试清理 + harness 软链硬化

> **状态**：部分完成（2 修好 / 1 精确定位（应用侧真问题）/ 1 属主题轨道 / 1 需按新 UI 重写一段）
>
> **后续更新（2026-10-29 同日晚）**：本文 §2 表里 **T29-ui 与 T35 两条已修复**，根因（`bridgeStatusAndRecover()` 缺 `return` / 恢复动作迁移后的寻址）与改动见
> [`1029_brief_options_refresh_fix.md`](1029_brief_options_refresh_fix.md)——阅读 §2/§3/§4 时请以该文为准，**只剩 T34 仍红**。
> **日期**：2026-10-29
> **来源**：用户批准"清 5 个存量红 + 硬化 `setup_serve`"
> **前置**：[`1029_ui_copy_plain_language.md`](1029_ui_copy_plain_language.md)（v3.11.0 文案改名，连带打到若干硬编码旧标签）

---

## 1. `setup_serve` 软链硬化（事故根因）

`run_e2e.setup_serve()` 原本把 `SERVE/editor.html` 建成**指向仓库真文件的软链**，于是"测试脚本往
serve 目录写一份对照版本"会**穿透软链改坏仓库源码**——2026-10-29 实际踩过：一次 T7 对照实验把
`editor.html` 覆盖成了 HEAD 版，v3.11.0 全部改动当场丢失（已用事故前的 JS 快照 + markup 重做复原）。

**改动**：`editor.html` 改为 `shutil.copy`（副本与源解耦）；`decks/` 体积大且从不被写，保留软链。

## 2. 五条存量红的逐条定性与动作

| 测试 | 定性 | 动作 | 结果 |
|---|---|---|---|
| **T31-brief**（`k_brief_check.py`） | ① `#btnBriefGen` 已不存在（v3.9.x「生成简报」并入「发送」，`buildBriefExport()` 才是产出点）；② 本次改名连带打到 4 条断言：`插画：混合烙入`→`配图方式：部分页整页重绘`、`烙入：…`→`整页重绘：…` | 断言改读 `page.evaluate("() => buildBriefExport()")`（不再为了断言真的提交）；同步新文案；`#briefResult` 可见性断言移到 Send 之后 | ✅ **ALL PASS** |
| **T35-dynamic-brief**（`y_dynamic_brief_check.py`） | ① **第一层**：用 `Escape` 关浮层不可靠（焦点可能在 deck iframe 内，顶层 keydown 收不到）→ 浮层仍显示 → 点被它盖住的 `#btnBrief` 必被拦截；② **第二层（应用侧真问题）**：`open_editor(brief_options=…)` 后服务端已存新值（T35d-2 PASS），但页面**重进 brief 拿不到它**（T35d-1 FAIL），后续动态组消失 | 用浮层自己的 ✕ 关闭 + 等"内容真的渲染出来"；把 helper 改成**失败返回 False 而非抛异常**（原先一次超时会把整支脚本吞掉）；T35f 加前置守卫 | ⚠️ **3 FAIL（同一根因）+ 其余全 PASS**：T35a-\* / T35c-\* / T35e-\* / T35f-6 全过 |
| **T29-bridge（ui 组）**（`r_bridge_check.py`） | ① `#btnBriefGen`（已删）；② **第二层未解决**：`#btnBriefRetry` / `#btnBriefStop` / `#btnBriefResume` **三个 id 已在 v3.9.9 随"简报区恢复按钮并入任务面板"一起删除**，而该组仍整段依赖它们（5 处） | 修掉 `#btnBriefGen` 那一处（顺带把"发送前队列为空"的实质断言留下） | ❌ **仍红**：该段需按任务面板重写（`hostBridge.recover` 的四个动作现在渲染在 `#bridgeTasks` 里）——**未做**，不做半改凑绿 |
| **T7-annotation**（`run_e2e.py`） | 断言与 v3.9.7「**批注提交即发送**」直接冲突：旧期望"提交后仍提示未导出"，而提交即整份发出 ⇒ 提示本就该空 | 改为"提交后无未导出提示 **且** 确实发出了 `pptx-html:annotations`"（正向断言，避免把"什么都没发生"当通过） | ✅ 已修（全量确认中） |
| **T34-theme-proving**（`run_e2e.py`） | **不是测试陈旧，是 deck 不满足验收契约**：`tests/decks/theme-proving/index.html` 实为 **7 主题 × 8 页型 = 56 页（无 g3）**，契约要求 8×8；`data-ig` 只出现在 g1/g2/g4（e1/e4/e6/g5 一个都没有）；e1/e4/g4/g5 存在真实重叠（如 `e1-high "NET GROWTH" × "门店净增"`）；g5-cover 三色近邻像素全部 <150 | **不动**（改测试期望＝改尺子迎合测量） | ❌ 仍红；项目已在 `docs/test_acceptance/mcp-apps-upgrade.md` §2.5.1 登记为**主题轨道待办** |
| （附）**T32** 对已删除 `#btnBridgeBake` 的读取 | v3.9.9 删桥栏按钮的迟发代价；它抛异常会**截断整轮 E2E** | 已在上一笔提交修掉（删死字段） | ✅ PASS |

## 3. 本次暴露的**新**应用侧问题（需另定）

**轨 B 下"重进 brief 视图生效"没有生效。** 证据链：

1. 服务端：`open_editor(brief_options=<v2>)` 的响应回显 v2；随后 `open_editor()`（不带参）后
   `get_status`/open 响应仍为 v2（T35d-2 **PASS**）——**存储没问题**；
2. 页面：重进 brief 后 `#briefBody` 仍是静态问卷（T35d-1 FAIL），且实测 `bridge.briefOptions` 为 `null`；
3. 对照：**嵌入态**的入站注入是好的（T35e-1 "入站 pptx-html:brief-options → 动态渲染" **PASS**）。

⇒ 问题只落在 **`openBrief()` 的 Bridge 分支**（`hostBridge.status()` → `bridge.briefOptions` → `renderBrief()`）
这一条路径上。`openBrief()` 的设计意图明确（"Bridge 态每次进入 brief 视图拉取最新 brief_options…
重进视图生效"），实测未兑现。**未修改**——需要带日志单独查（改测试去绕开它等于掩盖）。

## 4. 结论与边界

**全量 E2E 复核（2026-10-29）**：`==== 汇总：62 项，59 PASS，3 FAIL ====`（清理前同口径 **57 PASS / 5 FAIL**）。
**T7-annotation / T31-brief / T32-imagegen-entries 三条转为 PASS** ✅，且整轮**有汇总行**（T32 的异常截断已消除）；
剩下的 3 条正是 §2 表里标注的三条（T29-ui 待重写段 / T35 应用侧问题 / T34 主题轨道）。

- 5 条里 **2 条按"测试陈旧"修好**（T31、T7），**1 条精确定位为应用侧问题**（T35，附带发现 §3），
  **1 条属 deck/主题轨道**（T34，项目已登记），**1 条需按新 UI 重写一段**（T29-ui，未做）。
- **没有一条是靠放宽/改写期望值变成绿的**：T7 的期望按产品决策（提交即发送）更正并补了正向断言；
  T31 改成读构造器输出而非"点一次发送"；T34/T35/T29-ui 保持红并给出可执行的原因。
- `editor.html` 本次只多了一处一致性改动：脑暴文本行的前缀 `插画：` → `配图方式：`（与 v3.11.0 的组标题统一）。

## 5. 文件清单

- `tests/harness/run_e2e.py`（`setup_serve` 副本化；T7 断言按"提交即发送"更正）
- `tests/harness/k_brief_check.py`（6 处断言改读 `buildBriefExport()` + 文案同步）
- `tests/harness/y_dynamic_brief_check.py`（新增 `reenter_brief`；4 处调用；T35f 前置守卫）
- `tests/harness/r_bridge_check.py`（去掉已删 `#btnBriefGen`，保留"发送前队列为空"断言）
- `editor.html`（脑暴文本前缀统一为 `配图方式：`）
- 本文件 + `docs/progress/README.md` 索引（另：`docs/test_acceptance/mcp-apps-upgrade.md` §2.5 状态表更新）
