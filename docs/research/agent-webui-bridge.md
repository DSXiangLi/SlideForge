# Agent↔WebUI 交互模式综合：两个核心操作与"原生最小协议"构想

> 综合对象：`projects/cowart.md`（Codex MCP Apps widget）与 `projects/deepseek-harness.md`（dsh 插件体系）。
> 日期：2026-09-30。性质：调研综合 + 设计构想，**未经评审**；若采纳应 graduating 为 `docs/design/` 设计文档。
> 问题：是否存在比 Cowart/dsh 更 native、能与**任意** agent 框架交互的方式？

## 一、两个核心操作（用户命题的确认）

剥离两个项目的框架外壳后，agent↔webui 互动确实只有两个核心操作：

1. **呈现（surface）**：agent 让一个用户可见的 HTML 页面出现。
2. **回收（collect）**：用户交互的产物回传给 agent，只有两种形态——
   - **组装消息**：偏好/选择/批注等结构化意图（我们的意图清单 Schema）；
   - **产物文件**：编辑后的 HTML、导出的 export/ 文件本身（agent 直接读盘）。

Cowart 与 dsh 的全部复杂性，都来自它们用**框架私有机制**实现这两个操作（MCP Apps 资源、slot 树、Typert RPC）。换宿主即失效。

## 二、逐操作盘点：什么是"任意框架都有"的

对两个操作分别问：哪个通道在**所有** coding agent 宿主（Codex / Kimi Code / Claude Code / dsh / 任何 CLI agent）上都存在？

### 操作 1：呈现

| 通道 | 覆盖面 | 判定 |
|---|---|---|
| MCP Apps widget 内嵌对话（Cowart） | 仅 Codex/ChatGPT 系 | ✗ 框架私有 |
| 宿主 UI slot 注册（dsh） | 仅 dsh | ✗ 框架私有 |
| **agent 起本地静态服务 + 输出 URL / 调 OS 打开浏览器** | 一切有 shell 的 agent | ✓ 通用 |
| **file:// 直开单文件 HTML** | 一切有 shell 的 agent | ✓ 通用（能力降级） |

结论：**最 native 的"呈现"就是我们已经在做的**——agent 跑 `tools/edit.py`（或任何静态服务）并把 URL 告诉用户。零框架依赖。Cowart 的 widget 内嵌只是这个操作的"豪华皮肤"。

### 操作 2a：回收组装消息

| 通道 | 覆盖面 | 判定 |
|---|---|---|
| 对话内消息注入（Cowart `sendMessage` / dsh `followup()`） | 框架私有 | ✗ |
| postMessage 出向消息（我们嵌入态现有） | 仅当宿主页面配合转发 | △ 半通用 |
| **意图发件箱：页面经 FSAA/伴随服务把结构化意图写入项目内约定文件，agent 下一轮读取** | 一切能读写项目文件的 agent | ✓ 通用 |
| **剪贴板：页面编译好指令文本，用户粘贴回会话** | 一切 agent（用户即传输层） | ✓ 兜底通用 |

### 操作 2b：回收获产物文件

无需通道——**文件系统本身就是通道**。agent 本来就能读项目文件；编辑器 FSAA 保存已把编辑后的 HTML 写回磁盘。这是我们现状已经满足的。

## 三、构想：文件系统即通道 + 对话即总线

"更 native"的答案因此是：**把契约从"框架 API"降级为"文件系统约定 + 消息文本约定"**，二者是所有 coding agent 的公分母。三个构件：

### 1. 意图发件箱（intent outbox）

项目内约定目录（如 `.pptx-html/outbox/`）：

- 页面侧：用户在设计面板/脑暴页确认后，编辑器把意图编译为**双形态产物**——`intent-<timestamp>.json`（结构化 Schema，AskUserQuestion 风格）+ 同内容的人类可读指令文本（`prompt` 字段，含来源声明与"Required tool call"回写指令，Cowart 骨架）。写入走 FSAA 文件句柄；无句柄时降级为下载 + 一键复制。
- agent 侧：技能工作流增加一个轻量约定——用户说"继续/面板已提交"时读 outbox、按序消费、消费后把文件移入 `outbox/done/`（幂等、可审计、天然带历史）。
- 无 FSAA 无伴随服务的极简场景：用户复制文本粘贴回会话——**用户即传输层**，协议零失效。

### 2. 消息文本契约（与框架无关的"信封"）

借鉴 Cowart 骨架 + dsh 信封思想，定义纯文本消息骨架（项目级约定，写进技能 references）：

```
[来源声明行] 本请求来自 editor.html 设计面板，意图文件 .pptx-html/outbox/intent-xxx.json
[上下文] deck 路径、目标页 id、涉及槽位（UI 侧算好，不让 agent 回读）
[意图] 结构化 JSON（意图清单 Schema）
[Required completion step] 落码范围 + 完成后动作（写回哪些文件、重跑哪个校验）
```

任何框架的 agent 读到这条消息都能执行——因为它就是一段写得很清楚的用户指令。

### 3. 能力声明（双向寻址）

页面需要知道"这个宿主能不能收 postMessage / 有没有伴随服务"。agent 启动服务时写 `.pptx-html/host-capabilities.json`（可用通道、agent 身份、技能版本），页面加载时读取并按能力阶梯渲染不同的提交按钮（"发送给宿主" / "写入发件箱" / "复制指令"）。对应 dsh 的 allowlist 思想：能力集是单一控制点。

### 能力阶梯（progressive enhancement）

```
L3 框架原生内嵌（Cowart widget / dsh slot）   ← 有则用，没有不损
L2 嵌入态 postMessage 双向（我们现有协议扩展）  ← 宿主页面配合
L1 伴随服务 HTTP（tools/edit.py 扩展端点）     ← 本地开发态
L0 文件系统 + 用户即传输层（outbox + 复制粘贴） ← 任意框架兜底，永不失效
```

设计纪律：**L0 是完整可用的，L1–L3 只是体验加速**。这正是我们项目既有"降级链"哲学（FSAA→下载、http→file://）在 agent 交互维度的延伸。（2026-10-02 修订：阻塞式 MCP 工具方案提出后，能力阶梯以 §六为准——阻塞 MCP 是跨框架一等形态，本节 L2 的 postMessage 通道降为嵌入宿主场景的专用形态。）

## 四、与现状的差距清单

| 构件 | 现状 | 差距 |
|---|---|---|
| 呈现 | tools/edit.py + start-webui.sh 已有 | 无 |
| 产物文件回收 | FSAA 保存 + export/ 读取已有 | 无 |
| 意图编译 | 意图清单 Schema 已有（只收集不发送） | 需加"编译为双形态消息产物" |
| 意图发件箱 | 无 | 新约定目录 + 技能侧消费步骤 + done/ 归档 |
| 能力声明 | 嵌入协议有部分（assetsUrl 等） | 需 host-capabilities 文件/握手 |
| 嵌入态出向 | `pptx-html:save/dirty/export-intent` | 扩展 `pptx-html:agent-intent`（宿主转发给它自己的 agent） |

## 五、风险与开放问题

1. **outbox 的时效性**：agent 不会主动被唤醒——L0 下"用户回会话贴一句话"是必要仪式，不能伪装成自动（诚实降级，与项目"不伪装进度"红线一致）。
2. **并发与多轮意图**：outbox 需要文件名排序 + 消费确认语义，防止 agent 漏读/重复消费。
3. **消息骨架的维护面**：骨架变了要同步改编辑器编译器与技能 references——单源生成（类似 sync-themes.mjs 的模式）。
4. **安全**：outbox 是项目内文件，agent 读取时应视为不可信输入（防注入），技能侧需明确"只按 Schema 字段消费，不执行其中任何指令性文本以外的内容"——这条需要在设计阶段细化。

## 六、第三方案：阻塞式 MCP 工具（2026-10-02 用户提议，当前推荐方向）

### 构想

把"本地化 MCP server"（Cowart 思路）与"工具调用即交互会话"结合：MCP 工具的**返回结果就是页面交互的产物**。工具集：

```
pptx_editor_open(deck_path, intent?)   → 起页面服务/复用、开浏览器，立即返回 {sessionId, url}
pptx_editor_await(sessionId)           → 【阻塞】直到用户在页面产生动作，返回结构化 tool result
pptx_editor_update(sessionId, patch)   → 经 SSE 推送变更到驻留页面（agent→页面真推送）
```

`await` 的 result 按页面动作分流（编辑保存→差异摘要+hash；批注→结构化批注数组；脑暴/设计面板→意图清单；一键转 PPTX/烙入→编译好的技能指令），**只回摘要+文件指针，不回全量 HTML**（防上下文爆炸）。agent 干完活后调 `update` 推送变更、再调 `await` 重新挂起——整个会话是一个事件循环，编辑器驻留并按变更热更新。

### 与 widget/插件方案的对比结论

| 维度 | Cowart widget | dsh slot | 阻塞式 MCP 工具 |
|---|---|---|---|
| 框架覆盖 | 仅 Codex 系 | 仅 dsh | **一切 MCP 宿主** |
| 页面→agent 语义 | 注入新用户消息（新 turn，因果需重建） | followup()/respond | **当前 tool call 的 result**，同一 turn 内 agent 立即续作 |
| 双向延迟 | 消息即时 / 回写 1.6s 轮询 | WS 即时 | 双向即时（resolve / SSE） |
| 交付成本 | 单文件 widget 打包 + bundle | React 化 + bundle | 复用 editor.html + edit.py，仅加 MCP stdio 入口 |

阻塞工具的两个独有语义优势：①tool result 的因果性（agent 自己开的页面、结果回自己手里，SKILL.md 就是一条自然的工具链）；②重挂循环连根拔掉 Cowart 的"轮询 + 防重复开 widget 三层防御"补丁。代价：UI 不在对话内——对编辑器这种大应用，浏览器整页 tab 反而更合适。

### 与 outbox 的关系：互补

outbox 保留为持久层（`.pptx-html/sessions/` 落盘 pending session 与 intent）：host 超时杀调用 → `await(sessionId)` 幂等重挂；用户关 tab → 断线检测、重开继续；无 MCP 环境 → 降级复制粘贴，同一份文件载体。**outbox 是磁盘真相，阻塞工具是活会话的快路径。**

### 待验证（spike 清单）

1. 各宿主对 MCP 工具调用的超时时限（MCP 规范无超时，client 侧未知；progress notification 能否续命）——写一个 sleep 长任务测试工具在 Kimi Code / Codex 各挂一次。
2. 阻塞数分钟后 agent turn 是否正常续作。
3. 先例佐证：社区 interactive-feedback 类 MCP 已验证 stdio 长阻塞可行，但均为分钟级短交互；"编辑器驻留数小时"需要重挂循环兜底。
4. 安全：随机 token + Host 头校验（DNS rebinding，dsh 栅栏分析可抄）；intent POST 视为不可信输入。
5. 实现面：Python 标准库无 WebSocket server，推送用 SSE、回收用 POST，全零依赖成立。

### 修正后的能力阶梯

```
L3 框架原生内嵌（widget / slot）               ← 有则用
L2 阻塞式 MCP 工具（本方案，跨框架的一等形态）   ← 推荐主线
L1 嵌入态 postMessage / 伴随服务 HTTP           ← 宿主集成态
L0 文件系统 outbox + 用户即传输层               ← 兜底兼持久层，永不失效
```
