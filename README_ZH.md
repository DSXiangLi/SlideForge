# pptx-html-design

**[English](README.md) | [中文](README_ZH.md)**

**AI 做的 PPT，终于可以直接改了。**

用过 AI PPT 工具的人都有过这种经历：生成结果有 90% 满意，但想改一个字、换一张图，就得重新描述、重新生成、重新碰运气——改一处，动全身。

这个项目的答案很直接：**让 AI 生成的不是 PPT 文件，而是一个网页**。网页打开就能改——改字像改文档一样点进去就改文字，换图像换头像一样上传就换，改完点保存，结束。不需要再跟 AI 说一句话。

而当你真的需要 PPT 文件时，一键导出。需要更强视觉效果，也可以针对特定页面直接AI绘图并替换原有HTML。

HTML、PPTX、Image，这不是三个独立的形态，而是不同条件下可以无缝切换，并且编辑层上移到HTML层。

编辑器不依赖任何框架，不绑定任何Harness，通过mcp直接启动本地网页，编辑、批注、生图、对比、更换设计面板、导出一键完成。

<img src="assets/motion/cover-enter.gif" width="100%">

---

## 三个关键设计

### 1️⃣ HTML 是中间媒介：向上够得着惊艳，向下兼容得了现实

```
        AI 整页绘画（烙入页）        ← 向上升级：封面、主视觉页可以美到极限
                  ↑
     【HTML 幻灯片】← 中间媒介：AI灵活生成、可人工手动编辑、浏览器即播放器
                  ↓
        标准 PPTX 文件             ← 向下兼容：发给用 Office / WPS 的人
                  ↓
              PDF                  ← 顺带直出，用于归档与分发
```

一份内容，三种形态。日常编辑在 HTML 上进行；需要极致视觉的页面让 AI 整页绘画（原网页保留在隐藏层，随时回退）；需要交付时导出标准 PPTX。三种形态用内容指纹联动——HTML 改了，生图页和导出件会自动标记"已过期"，不会悄悄交付旧版本。

### 2️⃣ 原地可编辑，不依赖 AI 交互

编辑器是一个**零依赖的单个网页文件**，打开任何一份生成的幻灯片：

- **改字**：点进去直接改，不用切换"编辑模式"
- **换图**：上传即替换，图片自动存到幻灯片的素材目录
- **批注**：框选不满意的元素写一句话，生成指令交给 AI 精准修改
- **排序**：目录侧栏拖拽缩略图调整页面顺序

全程不需要 AI 在线，不需要网络，保存就是写回文件本身。快速、直接、可预期。

### 3️⃣ MCP 标准接入，适配任意 agent 框架

编辑器通过 **MCP（Model Context Protocol）** 标准协议与 AI 协作，只暴露五个标准工具，**不绑定任何特定 AI 产品或框架**——Kimi Code、Claude Code、Codex，或任何支持 MCP 的 agent，接入即用。

没有 agent 时编辑器独立可用；接入 agent 后，你在网页上提交的每个需求（脑暴、生成、修改、导出）都会作为任务交给 AI 在隔离副本上完成，校验通过后才发布回来——**AI 改坏你文件的可能性被架构性消除**。

---

## 它能做什么

| 场景 | 怎么做 |
|---|---|
| **从零做一套幻灯片** | 告诉 AI 主题和资料，先在可视化面板上选定风格（29 套主题 × 配色变体，色板/字体/动效所见即所得），AI 在冻结的风格内生成 |
| **改造已有 PPTX** | 把 .pptx 交给 AI 转换成网页幻灯片，进入同一套编辑流程 |
| **导出 PPTX 交付** | 一键导出**双轨产物**：可编辑版（文字、图表在 PowerPoint 里原生可改）+ 保真版（视觉逐像素封存），附 PDF |
| **嵌入自己的系统** | 幻灯片和编辑器都可 iframe 嵌入，通过 postMessage 协议与宿主通信 |

## 编辑器实拍

你不需要手动打开编辑器：接入 MCP 后，agent 在需要人工介入的节点（需求脑暴、修改确认、导出质检）会**自动唤起这个本地网页**，你在页面上操作、提交，agent 在隔离副本上完成任务并发布回来。以下为这条自动化链路中人工节点的真实录屏：

| <img src="assets/editor/editor-edit-annotate.gif" width="280"> | <img src="assets/editor/editor-brief.gif" width="280"> | <img src="assets/editor/editor-export-compare.gif" width="280"> |
|---|---|---|
| 就地编辑 + 框选批注（点进去就改，框一下就写意见） | 需求脑暴浮板：逐项选择风格与内容，生成结构化简报 | 导出 PPTX + 对比质检：并排 / 滑动分割 / 差异热区 |

> 备注：编辑器本身是单文件、零依赖的 `editor.html`，脱离 agent 也可独立使用——直接打开任意生成的 deck 即可编辑，保存即写回文件本身。这是降级路径，不是主流程。

## 主题样张：同一份内容 × 12 套主题

以下截图来自 `tests/decks/theme-sampler/`（演示主体为虚构茶饮品牌「山禾集」，数据均为虚构）：同一份业务内容在不同主题下的真实渲染——主题之间是排版、材质与图形语言的系统差异，不只是换配色。此处精选区分度最高的 12 套（含 F 系光学两主题与 G 系色彩结构三主题），完整 28 套见 `assets/theme-sampler/`。

| <img src="assets/theme-sampler/p05-c3.png" width="280"> | <img src="assets/theme-sampler/p11-e2.png" width="280"> | <img src="assets/theme-sampler/p12-e3.png" width="280"> |
|---|---|---|
| C3 · 终端绿 · 磷光绿 | E2 · 蓝图 | E3 · 装饰艺术 |
| <img src="assets/theme-sampler/p03-c1.png" width="280"> | <img src="assets/theme-sampler/p16-e7.png" width="280"> | <img src="assets/theme-sampler/p15-e6.png" width="280"> |
| C1 · 信号黑 · 信号橙 | E7 · 浮世绘 | E6 · 孟菲斯 · 糖果粉 |
| <img src="assets/theme-sampler/p19-e10.png" width="280"> | <img src="assets/theme-sampler/p22-f1.png" width="280"> | <img src="assets/theme-sampler/p23-f2.png" width="280"> |
| E10 · 星图 · 深夜蓝金 | F1 · 浮光玻璃 · 晨雾蓝 | F2 · 霓虹夜行 · 霓紫 |
| <img src="assets/theme-sampler/p25-g1.png" width="280"> | <img src="assets/theme-sampler/p26-g2.png" width="280"> | <img src="assets/theme-sampler/p28-g4.png" width="280"> |
| G1 · 翡翠年鉴 · 深翡翠 | G2 · 腮红荧光笔 | G4 · 靛墨黄页 · 黄页 |

## 页面类型实拍

同一套生成管线产出的不同页面形态：封面即目录（可点击跳转）、高密度数据页、图表页、信息图页。

| <img src="assets/page-types/smartforge-cover.png" width="280"> | <img src="assets/page-types/smartforge-impact.png" width="280"> | <img src="assets/page-types/smartforge-pipeline.png" width="280"> |
|---|---|---|
| 封面 · 章节导航（smartforge-c1） | 三格反差数据带（smartforge-c1） | 流水线（smartforge-c1） |
| <img src="assets/page-types/smartforge-arch.png" width="280"> | <img src="assets/page-types/charts-annual.png" width="280"> | <img src="assets/page-types/infographic-loop.png" width="280"> |
| 架构堆栈（smartforge-c1） | 图表页 · 年度总览（charts-a3） | 信息图页 · 闭环图（infographic-b2） |

## 动效实拍

动效是骨架内建词汇库（8 族 41 式），不是后期视频——以下是网页的真实录屏。

| <img src="assets/motion/lamp-kenburns.gif" width="280"> | <img src="assets/motion/closing-typewriter.gif" width="280"> | <img src="assets/motion/text-engine.gif" width="280"> |
|---|---|---|
| AI 插画氛围推拉（launch-mono-v3） | 打字机 + 乱码解码（smartforge-c1） | 拆字文字引擎（motion-v5） |

## AI 插画与整页烙入

上排：页面内 AI 插画——图片以槽位引用 `assets/` 外部文件，替换同名文件即可换图。下排：整页烙入与布局重构——平铺直叙的段落文本由 AI 重组为结构化信息图（文字逐字保留），原 HTML 保留在隐藏源层，可随时回退或重新烙入。

| <img src="assets/ai-illustration/lumen-p09-device-halo.png" width="416"> | <img src="assets/ai-illustration/lumen-p11-interface-panel.png" width="416"> |
|---|---|
| 页面内 AI 插画：产品氛围图（launch-mono-v3 · p09） | 页面内 AI 插画：App 界面图（launch-mono-v3 · p11） |
| <img src="assets/ai-bake/imagegen-v2-restructure-html.png" width="416"> | <img src="assets/ai-bake/imagegen-v2-restructure-baked.png" width="416"> |
| 烙入前：平铺直叙的 HTML 文本页，纯文字段落无视觉层级（B1 瑞士国际主义 · imagegen-v2） | 烙入后：布局重构的整页生图——段落重组为编号四阶段信息图，视觉全面升维（源层保留可回退） |

## 深入了解：质量是怎么保证的

<details open><summary><b>设计不由 AI 自由发挥</b></summary>

AI 生成的幻灯片之所以平庸，是因为它的默认审美会收敛到"居中标题 + 紫蓝渐变 + 卡片墙"。本项目的对策是**决策前置**：风格身份来自人工策展的主题库（你只选不改），版式由内容驱动（先数字数再选构图），AI 在约束内发挥——约束不是限制质量，是质量的来源。

</details>

<details><summary><b>文字溢出靠数学门禁，不靠目测</b></summary>

- **搭建期**：容量规划先于版式选择，用 PPT 字体度量口径预认证每一个容器
- **生成后**：Playwright 真实渲染测量——零溢出、零重叠、字号合规，脚本说了算
- **导出时**：数学认证器重开 PPTX 逐行计算——墨水宽度、墨水盒相碰、行高下限，认证全过才落盘，不过则自动修复，**绝不交付带溢出的 PPTX**
- 字体子集内嵌进文件，根治"换台电脑版式就乱"

</details>

<details><summary><b>55 项端到端自动化验收</b></summary>

覆盖渲染校验、章节跳转、密度量化、内容指纹、页面烙入、双轨导出、编辑器三态、容量门禁等全链路，真实内容基准是一套 54 页真实商业材料的 1:1 还原。验收体系面向开发者，证据见 `docs/test_acceptance/`。

</details>

<details><summary><b>编辑器 ↔ Agent 桥的技术要点</b></summary>

- 恰好五个 MCP 工具：`open_editor` / `await_intent` / `push_update` / `get_status` / `close_session`
- 所有任务为异步 intent：agent 在隔离工作副本上操作，CAS 校验后原子发布
- durable processing：任务可停止、可续作（resume / rebuild），状态真相在 SQLite，网页 / agent / 服务三方经 SSE 实时同步
- git 保护基线：独立 ref 与隔离 index，不触碰用户的 HEAD 与暂存区

</details>

## 与常见方案的功能差异

| 维度 | 常见做法 | 本项目 |
|---|---|---|
| 产物形态 | PPTX 文件 / 图片拼装 / 依赖框架的播放器 | 单个零依赖 HTML 文件，浏览器即播放器 |
| 生成后修改 | 重新生成，碰运气 | 原文件就地改，无需 AI 参与 |
| 设计决策 | AI 单方面拍板，风格随缘 | 策展主题库 + 可视化面板，人选型 AI 落码 |
| 防文字溢出 | 运行时缩字号 / 目测 | 容量规划 + 渲染测量 + 数学认证 |
| 导出 PPTX | 截图贴入（不可编辑）/ 朴素转换（版式漂移） | 原生可编辑 + 矢量保真双轨，认证不过不落盘 |
| 整页 AI 生图 | 生成即终态，改无可改 | 烙入页保留隐藏源层，随时回退重烙 |
| AI 框架绑定 | 绑定特定产品 | MCP 标准协议，任意 agent 框架可接入 |
| 质量证据 | "看起来没问题" | 55 项自动化验收 + 保真评分 + 差异热区图 |

## 快速开始

产品组成只有两个：**一个技能 + 一个 MCP 桥**。生成、编辑、导出所需的全部脚本都在技能内部，用户无需运行任何测试脚本。

生成侧由 AI coding agent 驱动：
- 加载 `skills/html-pptx/` 技能后，从需求脑暴到双轨导出的完整工作流（含渲染校验、容量门禁、双轨导出所需的全部脚本）由技能自带。
- 接入MCP服务，Agent会在需要人工介入时弹出网页让你操作

### 安装技能

**方式一（推荐）—— [`npx skills`](https://github.com/vercel-labs/skills) 安装器**，自动识别你的 agent 并装进对应目录（检测到多个技能时选择 `html-pptx`）：

```bash
# 装进当前项目
npx skills add DSXiangLi/pptx_fuse_design
# 或全局安装，所有项目可用
npx skills add DSXiangLi/pptx_fuse_design -g
```

**方式二——手动**：把 `skills/html-pptx/` 复制（或软链）到你 agent 的技能目录，入口为 `SKILL.md`：

```bash
# Claude Code
cp -r skills/html-pptx ~/.claude/skills/
# Kimi Code
cp -r skills/html-pptx ~/.agents/skills/
```

### 接入 MCP 桥（编辑器自动唤起的关键）

桥是一个 stdio MCP server，入口为 `tools/edit.py --mcp`。先装它唯一的依赖：

```bash
pip install "mcp>=1.28,<2"
```

然后注册到你的 agent——Claude Code 一行搞定：

```bash
claude mcp add pptx-html-bridge -- python3 /绝对路径/tools/edit.py --mcp
```

其他 agent（Codex / Kimi Code / Cursor …）在各自的 MCP 配置中加入等价条目：

```json
{
  "mcpServers": {
    "pptx-html-bridge": {
      "command": "python3",
      "args": ["/绝对路径/tools/edit.py", "--mcp"]
    }
  }
}
```

> **Kimi Code 注意：调大工具超时。** Kimi Code 默认在 60 秒处强制中断任何单次 MCP 工具调用（进度通知不会续期），这会杀掉桥的长等待 `await_intent`（最长一天），导致页面提交的请求无人认领。请在上方 server 条目中加入 `"toolTimeoutMs": 86500000`（或在 `config.toml` 设置 `[mcp] toolTimeoutMs`，或用环境变量 `KIMI_MCP_TOOL_TIMEOUT_MS`），然后重启会话。没有 60 秒限制的宿主不需要此项。

接入成功的标志：agent 恰好看到五个工具——`open_editor` / `await_intent` / `push_update` / `get_status` / `close_session`。

### 可选依赖

技能内置的验收与导出脚本按需安装：渲染校验 / 容量门禁需要 Playwright（`pip install playwright && playwright install chromium`）；HTML→PPTX 保真轨导出另需 poppler（`pdftocairo`）。


## 项目结构

```
skills/html-pptx/     【产品】生成技能：工作流 + 骨架 + 规范库 + 全部生成/导出脚本
editor.html           【产品】单文件编辑器：编辑 / 批注 / 翻转三态工作台
tools/                【产品】MCP 桥：edit.py 入口 + 核心 + MCP 代理
tests/                【开发验收】回归 harness 与测试基准，非产品组成，用户使用无需运行
docs/                 设计文档 / 调研 / 迭代实录 / 验收证据 / 踩坑台账
```

## 文档导航

- 协作约定与架构总览：根目录 `AGENTS.md`
- 设计与架构：`docs/design/`（索引见 `docs/design/README.md`）
- 桥接使用手册：`docs/howto/editor-agent-bridge.md`
- 迭代实录 `docs/progress/` · 验收证据 `docs/test_acceptance/` · 调研 `docs/research/`

## 当前状态

核心链路（生成 → 编辑 → 桥接 → 双轨导出）自动化验收全绿；真实 Office 365 / WPS 目检、真实付费生图观感为待办人工项，详见 `docs/progress/1003_editor_agent_bridge_handover.md`。
