# Cowart 调研：Codex 原生画布 widget 的 agent↔网页双向交互

> 调研对象：用户桌面 `/home/lixiang/Desktop/Cowart`（v0.1.28），GitHub `zhongerxin/Cowart`，MIT。
> 调研日期：2026-09-30。调研问题：它如何"在 agent 对话中无缝插入网页，网页结果与 AI 互动，且支持多 agent 框架"。

## 一句话定位

Codex 插件：通过 MCP 在对话中原生打开一个 tldraw 无限画布 widget（`text/html;profile=mcp-app`），画布内的生成请求（prompt/标注截图/AI HTML 框/AI Slides）**编译成结构化用户消息注入对话**，agent 侧由普通 skills 承接、经 MCP 工具写回磁盘，widget 轮询磁盘刷新。

## 核心架构：三段式解耦

**网页从不直接执行 AI 能力。** 画布只负责两件事：①把用户操作编译成一条带固定骨架的对话消息；②把画布状态静默写盘。agent 与网页之间没有私有事件通道，全部走「对话消息 + MCP 工具 + 文件存储」三段式。

```
widget ──A.静默写盘──→ MCP 工具(save_*) ──→ canvas/pages/<id>/*.json + assets/
widget ──B.注入用户消息──→ 对话流 ──→ skill 承接 ──→ MCP 工具(insert_*) 写盘
widget ←──1.6s 轮询读盘──────────────────────────────┘
```

## Widget 嵌入机制（MCP Apps + OpenAI 双写）

- widget 是 MCP 资源 `ui://widget/cowart/canvas.html`，MIME 为 `text/html;profile=mcp-app`（MCP 官方 Apps 扩展 `@modelcontextprotocol/ext-apps`，**不是** `text/html+skybridge`）。
- 资源与工具的 `_meta` **双写两套协议键**：MCP Apps 的 `ui/resourceUri` + OpenAI Apps SDK 的 `openai/outputTemplate` / `openai/widgetAccessible` 等（`mcp/lib/widget-resource.mjs:22-100`、`mcp/server.mjs:1078-1088`）。
- widget 是**全内联单文件 HTML**（6.4MB，CSP 禁外链/iframe/module script），由 `scripts/build-release-artifacts.mjs` 打包进 `mcp/generated/`；MCP server 也是零依赖单文件 bundle，`scripts/start-mcp.mjs` 只做版本闸门再 import。
- widget 内**自注入桥脚本**：底层 `new apps.App(...).connect()`（postMessage JSON-RPC 与宿主通信），上层把宿主上下文**映射伪装成 `window.openai`**（Apps SDK 形态）+ 自有命名空间 `window.cowartMcp`。

## 双向通道拆解

**通道 A（网页 → 宿主，静默数据）**：widget 直接 `callServerTool` 调 MCP 工具（保存画布/选中态/参考图）。这类工具标 `_meta.ui.visibility: ["app"]`——对模型隐藏、只许 widget 调。存储目标参数（projectDir/canvasDir）来自 render 工具返回的 `_meta.widgetData`，经 `ui/notifications/tool-result` 流入 widget。

**通道 B（网页 → agent，干活请求）**：MCP Apps `app.sendMessage({role:'user', content})`——宿主把它当作**新用户消息**进入对话流。消息是前端确定性编译的产物（`src/App.jsx:220-231`），固定骨架：

```
[@Cowart](plugin://cowart@cowart-github) 生成图片          ← ①插件 mention 强制路由
本请求来自已经打开的 Cowart 画布；不要调用 render_cowart_canvas_widget…  ← ②通道状态声明
请根据下面的 prompt 生成图片，并替换当前选中的 AI 图片框…
Cowart AI image holder shape: shape:xxxx                  ← ③UI 侧算好的上下文（几何/id）
Target canvas slot: 512 x 683 canvas units. Target aspect ratio: 3:4.
Required tool call after generating:                      ← ④回写指令逐条写死参数
- Call insert_cowart_image with anchorShapeId: "shape:xxxx", replaceAiImageHolder: true.
```

带图请求（标注截图）：先经通道 A 落盘拿路径，再把图片作为 image content 块随消息发出，prompt 里写本地路径兜底。

**agent → 网页：没有推送。** agent 调普通 MCP 工具（`insert_cowart_image` / `insert_cowart_html_draft`）直接改 store JSON + assets/，widget **每 1.6 秒轮询** `get_cowart_canvas_state` 重读快照，本地脏保护 merge。这是已知短板（浏览器 dev 模式才有 SSE 补）。

## 技能侧协作模式

- widget 消息与用户手打请求**完全同构**，skill 不区分来源；来源信息全部编码在消息文本里。
- 防重复开 widget 三层防御：消息第二行声明 + `cowart-open-canvas` skill description 排除条款 + `.mcp.json` server description。
- 不可逆禁令写进 description（image-edit："without replacing, moving, hiding, or deleting"），触发决策阶段即生效。
- 血缘元数据：产物 shape 的 meta 记录来源 holder id / 源 shape id / 截图文件名。
- `skills/*/agents/openai.yaml`：OpenAI 系宿主的技能 UI 元数据（展示名/默认 prompt/`allow_implicit_invocation`），与跨框架通用的 SKILL.md 分离。

## 插件协议与"多框架"真相

| 文件 | 服务对象 |
|---|---|
| 根目录 `plugin.json` + `mcp.json` | agent-plugins.org Agent Plugins v1.0.0 公开 schema，无框架专属字段 |
| `.codex-plugin/plugin.json`、`.mcp.json`、`.agents/plugins/marketplace.json` | Codex 专用清单与 marketplace 元数据 |
| `skills/*/agents/openai.yaml` | OpenAI 专用展示/策略层 |

通用层与框架层分离，同一份 skills/ + MCP server 被多套 manifest 复用；加新框架 = 加新 manifest 目录。**但 widget 机制实质只验证了 Codex/ChatGPT 系**——桥里伪造 `window.openai`、prompt 用 `plugin://` mention，无任何其他框架适配痕迹。不支持 MCP Apps 的宿主（如 Kimi Code CLI、Claude Code）跑不了这个画布。

## 对本项目的借鉴

1. **前端确定性编译 prompt**：几何/约束由 UI 侧算好后写死进消息文本，"Required tool call" 逐条写死回写参数——与我们 `compile-bake-prompts.py` 同构，只是挪到浏览器端。
2. **消息注入代替工具回调**：要 agent 干活的请求一律变成普通用户消息，skill 零特殊处理。
3. **磁盘单源 + 页面重读**：agent 写文件、页面靠 hash 检测刷新（我们已有 `data-content-hash` 可替轮询全量比对）。
4. **双轨客户端抽象**：`cowartClient.js` 同一 API 下按能力分流（MCP 桥 / HTTP fallback），对应我们"嵌入 postMessage / HTTP 伴随服务 / file:// 降级"三通道。
5. **警示**：1.6s 轮询的延迟感知、无推送，是"agent→页面"方向不做事件通道的代价。
