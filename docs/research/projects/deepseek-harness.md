# deepseek-harness（dsh）调研：插件化 agent harness 的 webui 互动架构

> 调研对象：用户桌面 `/home/lixiang/Desktop/deepseek-harness`（v0.1.0-rc.5，developer preview），GitHub `deepseek-ai/deepseek-harness`，MIT。
> 调研日期：2026-09-30。调研问题：它的插件功能能否解决"agent 进程中与 webui 互动"。

## 一句话定位

DeepSeek 官方 agent harness，"一切皆插件"（Cordis 框架）：**单进程**架构——`dsh web` 起一个 Node 进程同时跑 agent 运行时与 web server，浏览器是唯一外部进程；插件分 host 半（Node）与 client 半（浏览器），自定义 UI 以 **React 组件注册进 slot 树**（非 iframe），双向通信走 HTTP RPC + 只下行 WebSocket。

## 进程拓扑与通信面

- 上行：`POST /api/<namespace>/<method>`（unary RPC，Typert 代码生成的 strict descriptor + zod 校验）+ `POST /api/respond`（对可应答推送的回答）。
- 下行：两条**只下行 WebSocket**（`/api/events.mux` 会话事件流 + `/api/events.host` 宿主事件流），无 SSE fallback（SSE 仅 in-process carrier 用）。
- 浏览器端整个客户端也是一棵 Cordis 插件树（boot manifest 经 `window.__DSH_BOOT__` 注入 index.html）。
- 安全：`/api` 有 browser-trust 栅栏（Host 头归一化比较防 DNS-rebinding），刻意不支持 `--host 0.0.0.0`——"栅栏是可达性策略，不是认证"。对 iframe 嵌入场景的威胁模型分析值得一读（`packages/client/connection/README.md`）。

## 信封四象限 + rpcId 应答关联（协议精华）

`packages/host/apiproxy/src/api/rpc.ts:150-191`：

```ts
ClientRequest  { type:'client-request';  rpcId; method; payload }   // 浏览器发起
ServerResponse { type:'server-response'; rpcId; result }            // RPC 应答
ServerRequest  { type:'server-request';  rpcId; method; payload }   // agent 主动推送（可应答）
ClientResponse { type:'client-response'; rpcId; result }            // 网页回答，回同一 rpcId
```

agent 发起的提问/审批是带 rpcId 的 ServerRequest，经 mux 流推下；网页答复发回同 rpcId；断连重开时 pending 请求按原 rpcId 重放。这就是"网页弹面板、用户答完 agent 继续"的完整闭环。

## 插件系统

- 插件 = 导出 `apply(ctx)` 的 Cordis 模块，npm 包 + `package.json` 的 `dsh.bundle` 字段声明 patch 文件，`dsh plugin add` 安装；加载层序：bundle 补丁 → profile patch → `$DSH_HOME/cordis.patch.yml` → `--patch` overlay。（注：旧 `.dsh-plugin` manifest 格式已移除。）
- **host 半**：注册工具（`ctx.tools.register`）、系统提示词、钩子（`tools/pre-execute` 可返回 `ask` 触发审批）、技能、事件监听。注册即 effect，卸载即回滚。
- **client 半**：`exports["./client"]` + `dsh.client` manifest；往 **42 个 slot 席位**注册 React 组件——对话节点、工具卡、composer 接管、侧栏、设置页、全局浮层（`slot-catalog.ts`）。slot 分 single/list/keyed/chain 四种 cardinality。
- **对话内自定义 UI 三条路**：①`ConversationNodeDefinition` + keyed chat 渲染器（持久事件折叠成业务节点）；②`tool.call.toolview` 按工具名注册自定义工具卡；③`shell.overlay` 全局面板。
- **动态双半包**（`examples/web-cordis`）：`cordis_define`/`cordis_run` 让 **agent 现场写浏览器代码推送执行**（node:vm 沙箱 + 浏览器半；浏览器半不能 import/JSX，只 `React.createElement`），定位是"等同 bash 信任级别"的实验设施。
- **关键否定事实**：全仓无 iframe 嵌入机制；MCP client 只桥接 tools，**不支持 MCP Apps widget**（Resources/Prompts 无消费者）。

## agent → 用户的交互原语（对本项目最相关）

- `ctx.userQuestions.ask()`（`packages/interaction/user-questions`）= AskUserQuestion 等价物：阻塞工具调用直到人回答，答案 `{answers:[{id, selected, custom?}]}`。
- **intent 换肤机制**：`AskUserQuestionIntent = { kind: 'plan-review', ... }`——同一问题 schema，打 intent 标签让 UI 渲染成专用面板（plan-review 渲染成计划审批卡），**答案词汇不变**。先例证明"通用答案 schema + 专用呈现"是官方打法。
- Known Limitations 逐字承认：词汇只有 question-form（选项+自由文本），色板/文件选择等富交互无 seam——需自建 conversation node。

## 值得借鉴的协议设计（不搬实现）

1. **信封四象限 + rpcId 关联应答**：精确对应"网页展示→用户操作→回传 agent"闭环，天然支持断连重放。
2. **intent 换肤**：色板/字体面板可建模为 `intent:'theme-pick'` + 答案走 custom 字段，协议保持稳定。
3. **render intent 随事件下发**：host 算好 `{card:'diff'|...}` 视图随事件推（不落盘、每次现算），前端不做工具特判。
4. **allowlist 事件转发**：`API_REMOTE_FORWARDED_EVENTS` 显式数组收口自定义推送事件，类型与权限单一控制点。
5. **"Model-visible means logged"**：凡给模型看的内容必须进持久事件流再渲染，杜绝 UI 态与模型上下文漂移。

## 对本项目的结论

| 方案 | 判定 | 说明 |
|---|---|---|
| editor.html 搬进 dsh 当插件 | ✗ | 需 React 化 + bundle 体系，违背纯静态单文件红线 |
| dsh slot 组件内包 iframe + postMessage | △ | dsh 不拦但不在支持面内，且前提是宿主换成 dsh |
| 借鉴协议设计自建轻量桥 | ✓ | 信封四象限/rpcId/intent 换肤/allowlist 均可退化为 postMessage 协议条款 |

与 Cowart 对照：两者在"网页→agent"方向殊途同归（编译结构化消息注入对话流 / followup()），在"agent→网页"方向 dsh 有真推送（WS 事件流）而 Cowart 只有轮询——但 dsh 的推送能力来自它自己就是宿主，第三方项目无法借用。
