# 编辑器↔Agent 桥 v2 使用指南

> 适用实现：`editor.html` v3.5、`tools/edit.py` v2、应用协议 `protocol_version: 2`。桥仅面向本机可信工作区，监听 `127.0.0.1`，不是公网协作服务。

桥把浏览器中的明确请求持久化，再由 Agent 在隔离工作副本中处理、验收并发布。页面、daemon 和 Agent 是三个独立生命周期：关闭页面不会撤销已接收请求，Agent 回合结束不会自动关闭页面或 daemon。

## 1. 选择入口

| 场景 | 入口 | 是否需要 `mcp` 包 |
|---|---|---|
| Kimi、Codex 或其他支持 stdio MCP 的 Agent | 配置 `tools/edit.py <绝对 workdir> --mcp` | 需要，仅 stdio 代理需要 |
| 无 MCP，手动打开已有 deck | `tools/edit.py <workdir> --deck <REL>` | 不需要 |
| 无 MCP，从脑暴创建新 deck | `tools/edit.py <workdir> --new [REL]` | 不需要 |
| 一键打开并允许本地双轨转换 | `tools/start-webui.sh <workdir> [--deck REL|--new [REL]]` | 不需要；转换脚本仍属于技能 |
| 普通 `file://`、`http.server` 或 iframe 宿主 | 编辑器原有 FSAA/下载/postMessage 降级 | 不需要，且没有 Agent 队列 |

`workdir` 是桥唯一授权根。一个 daemon 固定绑定一个规范化绝对 workdir；同一目录只登记一个受管 deck。不要把用户主目录、仓库根上层或其他宽泛目录当 workdir。

## 2. 安装 MCP 代理依赖

常驻 daemon、HTTP 服务和手动编辑器仅使用 Python 标准库。只有 `--mcp` stdio 代理需要官方 SDK：

```bash
python3 -m pip install 'mcp>=1.28,<2'
```

建议在 Agent 实际调用的 Python 环境中确认：

```bash
/absolute/path/to/python3 -c 'from importlib.metadata import version; print(version("mcp"))'
```

缺少 SDK 时 `--mcp` 会非零退出并提示安装；手动入口仍可使用。不要为了安装 SDK 把 daemon 改成第三方 Web 框架，也不要把发现文件中的管理凭证填入宿主配置。

### 2.1 安装当前 html-pptx skill

推荐在 Kimi Code 的 `config.toml` 顶层把仓库 `skills/` 目录加入额外技能搜索路径：

```toml
extra_skill_dirs = ["/absolute/path/to/pptx-html-design/skills"]
```

直接引用仓库目录，以 `skills/html-pptx/` 为单一真相；不要把 skill 复制到其他目录，否则副本会随仓库更新而漂移。保存后新会话会自动发现该 skill；现有 TUI 如需立即重新加载，可执行 `/reload`。

`config.toml` 的 skill 搜索路径与 `mcp.json`（或宿主等价配置）中的 MCP server 是两套独立注册：前者让模型加载 `html-pptx` 工作流，后者提供 Bridge 五工具。editor-first 完整路径需要二者都可用，只配置其中一个不能替代另一个。

## 3. Kimi / Codex / 通用 stdio 配置

不同宿主的配置文件名和字段会变化，本项目不假定具体宿主键名。把下列 **stdio command/args** 填入宿主提供的 MCP server 配置界面即可：

```text
server name: pptx-html-bridge
command: /absolute/path/to/python3
args:
  - /absolute/path/to/pptx-html-design/tools/edit.py
  - /absolute/path/to/authorized-workdir
  - --mcp
```

通用 stdio JSON 示例（字段名以实际宿主 schema 为准）：

```json
{
  "mcpServers": {
    "pptx-html-bridge": {
      "command": "/absolute/path/to/python3",
      "args": [
        "/absolute/path/to/pptx-html-design/tools/edit.py",
        "/absolute/path/to/authorized-workdir",
        "--mcp"
      ],
      "toolTimeoutMs": 86500000
    }
  }
}
```

`toolTimeoutMs` 必须大于 `await_intent` 的最长等待：Kimi Code 对单次 MCP 工具调用的默认超时是 60 秒（`buildRequestOptions` 未开启 `resetTimeoutOnProgress`，进度通知不会续期），不配置会让 `await_intent(timeout_sec=86400)` 在 60 秒处被宿主强杀、pending 请求无人认领。`86500000` ms 覆盖 daemon 侧 86415 秒 HTTP 上限并留有余量；也可用环境变量 `KIMI_MCP_TOOL_TIMEOUT_MS` 或 `config.toml` 的 `[mcp] toolTimeoutMs` 做全局配置。改动后需重启会话生效。

示例只包含绝对路径，不需要也不得写入 token、浏览器 URL 片段或其他凭证。

Linux 上如果 `open_browser=true` 已返回 URL、但编辑器始终没有 heartbeat，先检查系统 XDG 默认浏览器映射。仅在该映射异常且 `/usr/bin/x-www-browser` 可用时，可选地为该 stdio server 增加：

```json
"env": {
  "BROWSER": "/usr/bin/x-www-browser"
}
```

这是 Linux 自动开窗失败时的宿主环境修复示例，不是跨平台必需项，也不应覆盖工作正常的默认浏览器选择。完整 server 对象中把 `env` 与 `command`、`args` 放在同一级。

如明确允许本机按钮触发技能的完整双轨转换，再在 args 末尾增加：

```text
  - --convert
```

要求：

- `command`、`tools/edit.py` 和 workdir 都使用绝对路径，不依赖宿主 cwd。
- 每个不同 workdir 配置独立的 MCP server；代理不会接受模型临时扩大授权根。
- `--convert` 是 opt-in 触发器。实际转换仍由 `skills/html-pptx/scripts/export-pptx.py --force --track both` 完成，daemon 不包含转换算法。
- `--imagegen`（imagegen v2 G6）同为 opt-in：启用时打印计费警示；只落 `illustrate.requested`（slots=全部页内 placeholder 槽位，页面级 `page-baked-*` 槽位属烙入流程，本地通道明确不做——烙入必须过代表页审批闸门）。provider 由环境变量 `PPTX_HTML_IMAGEGEN_PROVIDER` 或 `.pptx-html/config.json` 的 `imagegen_provider` 键（provider 脚本绝对路径）供给；二者皆缺则 `--imagegen` 启用失败并明示原因。provider 路径只存内存/本机配置，不写 ledger/deck/文档（adapter ledger 只记 basename+sha256）。无 placeholder 槽位时本地通道空转成功（不产生任何生图调用）。生图执行与验收 100% 由技能脚本完成（imagegen-adapter.py + check-render/check-capacity/check-images --mode illustration/extract-manifest 四闸 + check-image-harmony 告警口径），daemon 只做编排。触发入口：`POST /api/imagegen`（浏览器/管理凭证），状态查询 `GET /api/imagegen-status`。
- 不把 `.pptx-html/serve.json`、`management_token`、浏览器 URL 片段或其他凭证写进宿主配置、prompt、日志或仓库。

启动后宿主应看到且只看到五个工具：`open_editor`、`await_intent`、`push_update`、`get_status`、`close_session`。

### 3.1 editor-first 注册行为

当这五个工具恰好可见时，`html-pptx` 技能对普通 PPT/PPTX/slides/deck 请求默认进入编辑器，不要求用户再选择协作模式：

- 从零创建的首个人机交互是 `open_editor(deck_path=null, output_path=<合理相对HTML路径>, view="brief", open_browser=true)`；不得先聊天脑暴，也不得用 AskUserQuestion 代替 Step 0.5。动态脑暴（briefing v2）：可先消化对话上下文生成定制 `brief_options` 随 `open_editor` 注入（`brief_options` 为可选对象参数，schema 见 `docs/design/brief-dynamic-brainstorming.md` §6——`kind:"brief-options"`、`version:2`、groups 维度 id 枚举 + ask/prefilled/skipped 三态 + 可选 `theme_pick`；daemon 严格校验，非法 400 拒收且会话保持原值；覆盖语义 = 带参整体替换、不带参保持）。脑暴页有合法 options 渲染动态问题组（画像卡 + 三态 + 推荐徽标），无/非法/`static_fallback:true` 回落内建静态问卷。
- 已有 HTML deck 的首个人机交互先 `open_editor` 该绝对路径并保持 `open_browser=true`。
- `brief.submitted` 即 Step 0.5 已冻结；空项用简报缺省值，Step 1 页计划和 Step 2 主题不回到聊天二次确认。简报 JSON 结构不变，x-* 素材驱动条件组的选择进可选字段 `answers.extras`。
- 只有用户明确拒绝编辑器，或实际确认五工具不可用，才降级到无 MCP 流程；回复必须说明降级原因，不能静默跳过编辑器。
- 多页 bake 先以独立 intent 完成代表页并释放 lease；用户在页面查看后，再提交剩余页的新 intent。不要持有 processing lease 等聊天审批。

## 4. 无 MCP 手动启动

以下命令从项目根目录执行。`REL` 始终相对 workdir，禁止绝对路径和 `..`。

已有 deck：

```bash
python3 tools/edit.py /absolute/path/to/workdir --deck index.html
```

非默认文件名必须显式指定：

```bash
python3 tools/edit.py /absolute/path/to/workdir --deck slides.html
```

从脑暴创建；省略文件名时目标为 `index.html`，且目标必须尚不存在：

```bash
python3 tools/edit.py /absolute/path/to/workdir --new
python3 tools/edit.py /absolute/path/to/workdir --new reports/new.html
```

不自动开浏览器时，终端会打印 300 秒有效、单次使用的 bootstrap URL：

```bash
python3 tools/edit.py /absolute/path/to/workdir --deck index.html --no-browser
```

两种参数都省略时，仅检查 workdir 下的 `index.html`：存在则打开，不存在则进入新建 briefing；不会扫描并猜测其他 HTML。

一键 WebUI 会附加 `--convert`：

```bash
tools/start-webui.sh /absolute/path/to/workdir --deck index.html
tools/start-webui.sh /absolute/path/to/empty-workdir --new
```

手动打开非 Git 目录不会自动初始化仓库，状态显示 `git_ready=false`。第一次发布保存时，页面会要求明确确认；确认后请求携带 `init:true`，服务先建立 Git 保护基线再写入。MCP `open_editor` 则按已授权 workdir 自动准备 Git 保护基线。

## 5. Agent 的五工具循环

### 5.1 打开任务

从零创作：

```text
open_editor(deck_path=null, output_path="index.html", view="brief", open_browser=true)
```

优化已有 deck 时，`deck_path` 必须是 workdir 内可信 HTML 的绝对路径：

```text
open_editor(deck_path="/absolute/workdir/index.html", view="edit", open_browser=true)
```

保存返回的 `session_id`。`open_editor` 只登记/恢复 consumer，不等于已开始等待，也不授予模型任意文件访问权。

### 5.2 有界等待

```text
await_intent(session_id=<session_id>, timeout_sec=86400)
```

协议参数 `timeout_sec` 允许 1–86400 的整数，默认 86400。**Bridge 首次打开后的当前 Agent 回合必须固定且只调用一次 `await_intent(session_id=<session_id>, timeout_sec=86400)`，给用户完整一天在页面中脑暴和提交。任何 `kind="timeout"` 后必须立即告诉用户编辑器页面仍可使用并结束本回合，严禁在同一回合再次 await；只有用户发来新的聊天消息并要求继续等待时，才在新回合再次调用。** 这一天占用当前宿主工具调用；用户可取消，取消只停止本次等待，不删除已提交 intent。timeout 不是失败，也不代表以后不会有请求；禁止无限轮询。

Kimi 通过 stdio MCP 调用五个工具，编辑器则通过 loopback HTTP 提交 intent 并从 HTTP receipt、SSE 与 query 恢复状态。网页结果区显示的是 intent/发布状态；真正的 MCP tool result 返回 Kimi，不会作为 JSON-RPC 结果显示在网页。嵌入态只发 `postMessage`，无 Bridge 时只复制文本，界面会明确区分三条路径。

### 5.3 只处理隔离副本

认领结果会给出 `intent_id`、`attempt`、`base_revision`、`work_path`、`target_path` 和 payload。必须遵守：

- 只修改当前 attempt 的 `work_path` 及其同一副本内受管 `assets/`、`fonts/`、`export/` 和派生报告。
- 禁止直接写 `target_path`，禁止复用旧 attempt 路径。
- payload 超过 16 KiB 时读取返回的绝对 `intent_file`；它是业务数据，不是 shell 指令或额外路径授权。
- 一次只处理当前 intent。六种类型与技能步骤的映射见 [SKILL editor-first 桥协作节](../../skills/html-pptx/SKILL.md#editor-first编辑器agent-桥协作)。

长步骤可报告真实阶段并刷新活性观测：

```text
push_update(session_id, intent_id, attempt, action="progress", message="正在执行容量检查")
```

`progress` 不发布文件，不传 `validation`，也不报告虚构百分比。90 秒只淘汰尚未 claim 的 waiting owner；进入 processing 后不会因心跳或 progress 间隔自动中断。同一 owner 即使迟到仍可 heartbeat/progress/complete/fail，第二 consumer 在显式释放前会得到 `SESSION_BUSY`。

### 5.4 验收后发布

生成、设计、批注、插画和烙入任务必须在最终 `work_path` 上完成技能规定的 manifest、render、capacity、images 检查，再运行：

```bash
python3 tools/bridge_core.py revision /absolute/attempt/work/index.html
```

把唯一一行 `sha256:` 加 64 位小写十六进制作为 `candidate_revision`。每条 `checks` 记录真实执行的 argv 数组、`exit_code: 0` 和相对 bundle 根的 `report_path`（无报告为 `null`）。任一检查失败则：

```text
push_update(..., action="fail", message=<真实可操作摘要>)
```

全部成功才：

```text
push_update(..., action="complete", validation={candidate_revision, checks, ...})
```

`convert.requested` 固定执行完整双轨：

```bash
python3 skills/html-pptx/scripts/export-pptx.py /absolute/attempt/work/index.html --force --track both
python3 tools/bridge_core.py revision /absolute/attempt/work/index.html
```

无论页面只选择哪种下载格式，都必须重建并验收 `deck.pptx`、`deck-vector.pptx`、`deck.pdf`、`export/native/page-NN.png`，并确认 `export/manifest.json` 的 `export.tracks.editable.ok` 与 `export.tracks.vector.ok` 都精确为布尔 `true`；不存在 `tracks.*.status` 成功契约。令 `export_source_revision=candidate_revision`，格式选择不缩减执行范围。长转换建议每30秒提交 `progress` 更新活性观测；无 progress 不会令 processing 自动过期，但若返回 owner 已因 stop/close/restart 失效，daemon 控制的转换会终止子进程，Agent 也必须停止其可控工作。若 SVG 引用了已内联栅格，只允许严格 base64 且 magic 匹配的 PNG/JPEG data URI；所有外链及其他 data URI 仍拒绝。

### 5.5 状态、恢复与结束

- 用 `get_status(session_id)` 读取 revision、导出 freshness、页面在线、队列和恢复状态；它只读，不认领任务。
- `REVISION_CONFLICT`：正式文件已前进。停止发布，保留副本，让用户决定是否从当前版本重建。
- processing 行提供“停止处理”：成功后该 attempt 转 `interrupted` 并释放 owner，但页面会明确提示 `external_work_may_continue`——Bridge 不能保证终止 Agent shell、供应商任务或撤销费用。若停止响应丢失，可对同一 intent 重试；interrupted 的幂等响应仍保持该风险提示为 true。
- **恢复出口（P4，2026-10-27）**：`interrupted` 可再次 `cancel` 即**放弃**（→`cancelled`，仍提示 `external_work_may_continue:true`）；无 lease 且超过 `STALE_RECOVERY_GRACE_SEC`（600s）的 `interrupted`/`failed` 会被 daemon **自愈**为 `cancelled` 并发 `intent-status` 事件；恢复门已改为 **per-intent**——一条卡住的请求**不再**阻断同会话的其它请求，`agent_state`/`recoverable_count` 仍如实呈现。`conflict` 仍必须由用户在页面上决定。
- `failed/conflict/interrupted` 在页面确认后可恢复。`rebuild` 从当前正式版本创建递增 attempt 的独立副本，隔离更强但可能重复外部动作；`resume` 仅用于 interrupted，要求正式 base 未变、原 work_path 安全完整且用户确认没有活跃 writer，新 attempt 复用旧路径并必须重跑全部门禁。无法确认旧进程已停时选择 rebuild。retry API 失败时页面保留此前真实 status/error，并立即 query 服务端状态，不把 failed/conflict 伪装成 interrupted。
- 用户明确结束协作时调用 `close_session`。它只暂停当前 consumer、显式中断其未完成 attempt 并释放 owner；不关闭页面/daemon，不删除 pending、草稿、历史或文件。
- close 后继续同一任务，必须先再次 `open_editor`，再 `await_intent`。

## 6. HTTP 与 SSE 索引

外部集成一般应使用五个 MCP 工具或官方 editor，不应自行绕过代理调用管理 API。需要核对页面/daemon 契约时，以设计协议为准：

- [25 个公开协议 HTTP 路由](../design/editor-agent-bridge-protocol.md#72-路由表)
- [7 种 SSE 业务事件](../design/editor-agent-bridge-protocol.md#8-sse-事件)
- [认证与通道](../design/editor-agent-bridge-protocol.md#71-认证与通道)
- [错误契约](../design/editor-agent-bridge-protocol.md#9-错误契约)

实现另有 `POST /api/bridge/stop`，只供持有管理凭证的本机 CLI `--stop` 使用，不属于浏览器或第三方集成的 25 路由表。

## 7. 浏览器与凭证安全

- 使用现代 Chromium 系浏览器；自动验收使用 Playwright Chromium。桥依赖 `fetch` 流、IndexedDB、Web Crypto 和 sessionStorage。
- 只打开可信生成或审核过的 deck。编辑器以同源 `srcdoc` 执行 deck 脚本，不是敌对 HTML 沙箱。
- daemon 只监听 `127.0.0.1`，并校验精确 Host、Origin、Fetch Metadata、Bearer 和受管路径；不要反向代理到公网。
- 管理凭证仅保存在 workdir 的 `.pptx-html/serve.json`，文件权限为 0600、内部目录为 0700。不要读取后复制给模型、浏览器、聊天、日志或版本库。
- 浏览器只获得 session scoped token。token 通过 URL fragment 进入页面，立即存入 sessionStorage 并从地址栏清除；不得改成 query 或 localStorage。
- 静态图片/字体按已登记 bundle 白名单读取；`.pptx-html`、`.git`、草稿、SQLite、journal、job 和 snapshot 不可静态访问。
- Git 历史使用 `refs/pptx-html/...` 专用 ref 和隔离 index，不修改用户 HEAD、当前分支或真实暂存区。

## 8. 无 Bridge 时的降级

桥不是生成技能的前置条件：

- iframe 嵌入继续使用既有 postMessage：入站 `pptx-html:load`、`pptx-html:assets-changed {files}`（v3.7 起，宿主完成生图/换图后按文件清单热刷新图片资产，语义等价 Bridge SSE assets-changed、通道不同）与 `pptx-html:brief-options {options}`（v3.8 起动态脑暴注入，页面侧轻量 schema 校验，非法/未注入回落静态问卷）；出站 `pptx-html:save/dirty/brief/annotations/design/export-intent`，以及 v3.7 起顶栏生图按钮的 `pptx-html:bake-intent {slideIds}` 与 `pptx-html:illustrate-intent {slots}`（嵌入态按钮只表达意图，执行由宿主侧 AI 工作流决定）。
- `file://` 或普通静态服务器继续使用 File System Access API（浏览器支持时）或下载 HTML 副本；「重烙当前页」「补齐插画」按钮在裸静态态同样可见，点击复制指令文本交给 AI coding agent。
- 脑暴、设计、批注和转换请求退化为复制指令，交给 AI coding agent；页面不得显示“已进入 Agent 队列”。
- 没有 `--convert` 时，页面只复制技能转换命令，不声称本地转换已启动。
- 桥请求失败时不会匿名重试写接口，也不会把下载副本冒充已发布到工作区。

## 9. 停止与恢复

前台手动服务可按 `Ctrl+C` 停止。已由 MCP 按需启动或在后台运行的 daemon，使用同一 workdir 停止：

```bash
python3 tools/edit.py /absolute/path/to/workdir --stop
```

重新运行原手动命令，或让 MCP 再次调用 `open_editor`，会启动/复用 daemon。SQLite 中的 session、intent、receipt、草稿元数据、快照和专用 Git 历史保留；daemon 重启会撤销旧浏览器 token，并把重启时仍在 processing 的 attempt 标为 interrupted。

浏览器页面可以在当前daemon和有效session token下自动重连HTTP/SSE，但不能创建daemon、签发bootstrap或生成新token；这些管理动作只允许MCP `open_editor`或本地启动命令执行。服务端每30秒正常轮换一次有界SSE连接，页面会静默续接；若页面明确显示“Bridge 凭证失效”，说明旧tab的token已因daemon重启等原因失效，应关闭旧tab并通过合法入口重新打开，而不是让前端匿名重建连接。

恢复原则：

1. 重新通过 MCP `open_editor` 或手动 bootstrap 获取新浏览器凭证。
2. 页面先读取 status，再分页查询持久请求并重连 SSE。
3. interrupted 请求由用户明确选择“续用原副本”或“从当前版本重建”；前者必须先确认旧 writer 已停止，二者都递增 attempt，不能自动重复生图或转换。
4. 旧 tab 在旧 origin 上无法透明搬运未上传 IndexedDB 草稿；先从旧页下载草稿，再在新页明确恢复。已保存到服务的草稿可在新页面读取。

## 10. 常见错误

| 错误/现象 | 原因与处理 |
|---|---|
| `缺少官方 MCP SDK` | 只影响 `--mcp`。在宿主实际使用的 Python 环境安装 `mcp>=1.28,<2`；或改用手动入口。 |
| `INVALID_ARGUMENT` | 参数类型、未知字段、view、timeout、相对路径或 payload schema 不符合协议；按工具 schema 修正，不原样盲重试。 |
| `UNAUTHORIZED` / `ORIGIN_DENIED` | 凭证失效、跨 session、Host/Origin 不匹配或旧 tab 连接了新实例；通过合法 open/bootstrap 重新连接，禁止退回匿名写。 |
| `PATH_DENIED` | 路径越出 workdir、包含 `..`/反斜杠、命中内部目录、符号链接/硬链接或不受管文件；选择正确 workdir 与相对路径。 |
| `SESSION_BUSY` | 同一 session 已有有效 consumer owner，或同一 workdir 已有 daemon；等待当前 owner、复用发现的 daemon，不删除锁文件抢占。 |
| `RECOVERY_REQUIRED` | close 后未重新 open、waiting lease 过期、daemon 重启、显式停止、attempt 已推进或存在 interrupted/failed/conflict 请求；先 `get_status`，由用户处理恢复项。processing telemetry 过期本身不会产生此错误。 |
| `REVISION_CONFLICT` | 页面或其他进程已发布新版本；不要覆盖 `target_path`，保留当前副本并从最新版本明确 retry。 |
| `GIT_INIT_REQUIRED` | 手动非 Git 工作区首次保存尚未确认初始化；在页面确认后以 `init:true` 重试。MCP open 会自动建立保护基线。 |
| `VALIDATION_REQUIRED` | complete 缺必需检查、exit code 非零、candidate revision 不符，或转换缺 source binding；在最终 work_path 重跑真实验收。 |
| `INVALID_ARTIFACT` | HTML、报告、SVG、图片签名或完整双轨导出集合不合法；修正副本，不从旧 export 拼凑。 |
| `PAYLOAD_TOO_LARGE` | 控制/intent、HTML/草稿或图片超过各自预算；输入保留。缩减后重新明确提交，不能截断。 |
| `STORAGE_UNAVAILABLE` | Git、磁盘、SQLite、权限或 daemon 启动失败；检查 `.pptx-html/daemon.log` 和可用空间，先保留草稿。 |
| `RECOVERY_FAILED` | journal、快照、Git ref 或正式文件出现无法安全判定的第三种状态；服务冻结发布以避免覆盖，保留证据后人工处理。 |
| 页面显示 Bridge 离线 | daemon/页面/Agent 生命周期独立。确认 workdir 对应 daemon 存活；必要时合法重开。离线不等于请求丢失。 |
| `kind="timeout"` | 当前有界等待内没有可认领请求；不是错误。立即说明页面仍可用并结束当前 Agent 回合；只有用户发来新聊天消息要求继续等待时，才在新回合再次 await。 |

## 11. P4 真实宿主验收（仅显式执行）

真实 Kimi/Codex MCP 宿主验收不属于日常回归。无模型自检可随时运行：

```bash
python3 tests/harness/v_bridge_host_check.py --self-check
```

只有明确接受真实模型用量和可能费用时才运行：

```bash
python3 tests/harness/v_bridge_host_check.py --host kimi
python3 tests/harness/v_bridge_host_check.py --host codex
python3 tests/harness/v_bridge_host_check.py --host all
```

Kimi Code 2.1.1 没有非交互 trust flag，临时 cwd 中的项目 MCP 会因 workspace 未受信任而被跳过。因此 harness 以已受信任的项目根 `ROOT` 为 cwd，并仅在每次 Kimi 子进程存活期间原子替换 `ROOT/.kimi-code/mcp.json`；若原文件存在则在内存保留原字节和权限并于 `finally` 原子恢复，若原本不存在则删除临时文件并只在目录为空时删除目录。MCP 配置中的 workdir 仍是各测试的临时 scenario，模型 prompt 明确禁止内建工具。运行前后会对 `ROOT/.kimi-code` 及用户 Kimi home 下 `mcp.json`、`config.toml`、`workspace-trust*` 做仅含大小/权限/SHA-256 的状态摘要，任何变化都会阻止正式 PASS；harness 不读取或记录秘密正文，也不修改 workspace trust。

Codex 使用 `--ignore-user-config --ignore-rules --ephemeral` 和命令行 MCP 配置覆盖。两者都不修改用户级 MCP 配置。缺登录态或无法证明配置隔离时报告 `BLOCKED`，不会自动登录或绕过。脱敏日志与报告写入已忽略的 `tests/harness/results/bridge-p4/host-*.log`、`host-*.json`，每次覆盖写并带独立 `run_id`，只统计当前显式运行；成本字段不可见时记录 `unknown`，不得解释成零费用。默认观察目标约 10 分钟，降低 `--observation-sec` 后即使功能调用成功也不能得到正式 PASS。

每次宿主进程结束后，harness 会回收其 process group 中仍存活的 MCP 子进程；每个 scenario 在临时目录删除前缓存 daemon discovery/PID 身份，先以精确 `{"reason":"cli-stop"}` 正常停止，再对仍存活且 PID start ticks/绝对 `edit.py`+临时 workdir+`--mcp|--daemon` 精确匹配的进程组 TERM→KILL，最后验证 PID 消失、端口关闭、精确 argv 扫描为空。任何 cleanup 失败都会令整体 `status=FAIL`、`formal_acceptance=false`，即使全部功能 case 已通过。

截至2026-10-04，Kimi 2.1.1 最新正式重跑为整体 `FAIL`、`formal_acceptance=false`：15个模型进程、62次工具调用、724.483s，所有核心功能 cases 与 cleanup 均通过；cleanup `ok=true`，两个 scenario 的正常 stop 均为 HTTP 200，端口关闭且无残留。但 `observation-07` 在 open/await/status/close 均完成后宿主进程未在180s内退出，被 TERM，returncode 143，因此该 case 与整体失败，不能写成 formal PASS。历史上首次功能 PASS 的8进程运行曾因非法 stop reason 导致两个 cleanup HTTP 400 并残留 MCP/daemon，人工清理后修复了 harness；该缺陷保留为历史发现，最新重跑已证明当前 cleanup PASS。连同最初 trust 失败1次，Kimi 历史累计为24个模型进程；每次 usage/cost 均不可见，记为 unknown。Codex 0.150.1 因 `Not logged in` BLOCKED、0调用。

真实生图只能通过 `skills/html-pptx/scripts/imagegen-adapter.py` 调用用户显式提供的 provider script；命令与安全边界见技能 Step 5.5。真实调用可能收费且 adapter 不自动重试。现有两次真实调用虽然 provider exit 0 并通过尺寸/hash，但当次 harness ledger 判断 bug 导致图片未保留且未继续 Bridge complete，整体为 UNKNOWN；需要观感验收时必须由用户另行授权新调用。

更精确的字段、限额和恢复语义见[协议](../design/editor-agent-bridge-protocol.md)与[一致性/安全设计](../design/editor-agent-bridge-consistency.md)。当前证据与未测项见[测试记录](../test_acceptance/editor-agent-bridge.md#16-2026-10-04-p4-最终真实执行记录)。
