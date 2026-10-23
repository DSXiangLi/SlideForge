# 编辑器 v2 设计（样式编辑 / 目录侧栏 / git 版本）

> 状态：待评审 · 依据：2026-09-18 用户意见（样式编辑、PPT 式目录、git 版本回滚）
> 实施对象：`editor.html`（v1.5 → v1.6）、新增 `tools/edit.py`（本地伴随服务）、`skills/html-pptx/references/editing-contract.md`（样式覆盖条款）、`tests/harness/`（回归扩展）。
> 既有编辑器设计文档：`../design-editor.md`（v0.3），本文档是其增量，冲突处以本文档为准。

## 1. 文字样式编辑（字体 / 字号 / 字色 / 对齐）

### 粒度决定（重要边界）

样式作用于**整个 `data-editable` 元素**，不做选区级（range 级）富文本。理由：

- 编辑是 `contenteditable="plaintext-only"`，选区级样式需要拆 span、破坏纯文本约束，与"文件即真相 + 序列化干净"直接冲突；
- 幻灯片文字样式的一致性是主题级的，逐词改样式是 AI slop 的入口；
- 局部强调需求走批注 → AI 落码流程（已有通路）。

### UI 形态

选中文字类可编辑元素后，顶栏右侧出现**样式控件组**（未选中时隐藏）：

- **字体**：下拉。选项来源 = 当前 deck 的三个主题字体栈（从 `:root` computed style 读 `--font-display` / `--font-body` / `--font-mono`，显示为"标题字体/正文字体/等宽字体"）+ 常用系统字体小清单；
- **字号**：数字输入 + 步进按钮，单位 px（画布坐标系，与 SKILL.md 字号分档一致），下限 18px 与生成侧红线对齐（低于下限时警告不禁止——编辑是用户主权）；
- **字色**：主题色板（读 `--paper/--ink/--accent` 等 token 的 computed 值，显示色块）+ 自定义 `<input type="color">`；
- **对齐**：左/中/右/两端 四按钮切换。

### 存储与序列化

样式写为该元素的 inline `style`（白名单四属性：`font-family` / `font-size` / `color` / `text-align`）。序列化净化清单**保留**这四个属性，其余 style 属性不新增。样式修改置脏、随保存写回、重载后还原——与文字编辑同一通路，无新保存机制。

### 契约条款（editing-contract.md 新增"样式覆盖"节）

- 编辑器只允许对 `data-editable` 元素写白名单四属性的 inline style；
- 生成侧（AI 落码）修改该元素内容时**不得无故清除**已有 inline style——用户的样式选择与内容修改正交；
- AI 整体改版（换主题/换构图）时可以重置样式，但必须在交付说明中声明。

## 2. PPT 式目录侧栏

### 布局

```
┌────────┬──────────────────────┬──────────┐
│ 目录侧栏 │   编辑画布（iframe）   │ 设计面板抽屉 │
│ 240px  │   弹性（现状不变）      │ （现状右抽屉）│
└────────┴──────────────────────┴──────────┘
```

顶栏加"目录"切换按钮（默认开，可收起）。嵌入态默认收起（宽度敏感），独立打开默认展开。

### 缩略图实现

- 每个 slide 一条缩略卡片：**克隆 section DOM**，去掉所有 `id`（避免重复 id）、`pointer-events:none`、aria-hidden，外层容器 `overflow:hidden` + 克隆体 `transform: scale(缩略宽度/1920)`；
- **懒渲染**：IntersectionObserver，滚入视口才克隆（deck 页数大时控制 DOM 成本）；动画元素在克隆中强制终态（注入 `.slide *{animation:none!important}` 到克隆容器作用域，避免抓到动画中间态）；
- 当前页高亮与 iframe 滚动同步（复用现有 sbPage 的页码跟踪逻辑）；点击缩略图 → iframe 滚动到对应页；
- 编辑内容后缩略图**按需失效重克隆**（保存或翻页后刷新对应卡片，不做实时同步——缩略图是导航件不是监视器）。

## 3. git 版本记录与回滚

### 架构决定：伴随服务，不污染编辑器单文件形态

纯静态页面无法执行 git。引入 `tools/edit.py`（python3 标准库，零依赖）：本地 HTTP 服务，托管 editor.html 并暴露最小 API。编辑器保持单文件纯静态，**检测到后端才启用版本能力**：

```
python3 tools/edit.py          # 启动后浏览器自动打开编辑器
python3 tools/edit.py deck/    # 指定工作目录
```

API（全部只操作工作目录内文件，拒绝路径穿越）：

- `GET  /api/health` → 存活探测（编辑器加载时探一次，失败则走 FSAA/下载现状路径）；
- `POST /api/save` `{path, html}` → 原子写文件 + `git add <deck> assets/ && git commit`（message 自动生成：`edit: <timestamp>`）。目录非 git 仓库时**先询问再 init**（health 响应里带 `gitReady` 标志，UI 弹一次确认；确认后 `git init`）；
- `GET  /api/versions?path=` → 该文件的提交列表（hash/时间/message）；
- `POST /api/rollback` `{path, hash}` → **先对当前状态做一次 `pre-rollback` 提交**（永不丢数据），再把目标版本内容写入文件；
- `POST /api/convert` `{path}` →（v3.1 增，**opt-in**：仅 `--convert` 启动时可用；health 以 `convert` 字段宣告）以子进程触发技能脚本 `skills/html-pptx/scripts/export-pptx.py --force`，30 分钟超时，返回尾部日志。**边界**：本端点只是触发器，不含任何转换实现——转换即技能的红线不变；未启用时编辑器回退"复制技能命令"。

### 编辑器侧

- 有后端时：保存 = POST /api/save（每次保存一个版本）；顶栏加"历史"按钮 → 版本列表面板（时间倒序）→ 选中版本可"回滚到此版本"，回滚后重新加载文件；
- 无后端时：维持现状（FSAA/下载），"历史"按钮置灰，tooltip 提示 `python3 tools/edit.py` 启动以获得版本记录；
- 嵌入态：保存仍走 postMessage（现状不变），版本能力由宿主决定，与本伴随服务无关。

### 回滚红线

- 任何回滚前先自动提交当前状态（可反悔的回滚）；
- git 操作只 add deck 文件与 `assets/`，不 `git add -A`（避免把用户目录里无关文件卷入提交）；
- 工作目录限制：API 拒绝处理启动目录之外的路径。

## 4. 验收标准

- 样式编辑：选中文字 → 改四属性 → iframe 即时生效、置脏；保存 → 重开文件样式仍在；harness 用例覆盖（设置样式 → 保存 → 重新加载断言 inline style 存在）；
- 目录侧栏：N 页 deck 渲染 N 张缩略卡；点击第 k 张 → iframe 滚动到第 k 页且该卡高亮；收起/展开状态正确；harness 用例覆盖；
- git 版本：伴随服务启动下保存两次 → `git log` 两条提交；回滚到第一版 → 文件内容还原且有 `pre-rollback` 保护提交；无后端时保存路径退化为 FSAA/下载且历史置灰；harness 起 `tools/edit.py` 做端到端；
- 回归：现有 harness 全绿（文字编辑、图片替换、批注、嵌入 postMessage、净化保存五条不受新功能影响）。

## 5. 明确不做

- 不做选区级富文本（见 §1 粒度决定）；
- 不做样式编辑的撤销栈增强（沿用浏览器 contenteditable 撤销 + git 版本即后悔药）；
- 缩略图不做实时渲染同步、不做拖拽排序（页面结构调整走 AI 落码）；
- git 不做分支/标签 UI（面板只有线性历史 + 回滚）。
