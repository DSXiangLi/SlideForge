# 编辑器页面设计文档

> 版本：v0.3（评审修订稿）· 2026-09-16
> 范围：第一期——HTML 幻灯片的页面化编辑（文字就地编辑 + 图片替换 + 批注回传 + 保存回文件）。
> 关联契约：`skills/html-pptx/references/editing-contract.md`（编辑器是它的消费侧实现）。

## 0. 背景

`skills/html-pptx/` 已就绪：AI 可以生成带可编辑标记的纯净 HTML 幻灯片。但用户拿到文件后**改一个字都要动代码**——这违背了项目"页面直接可编辑、直接保存"的第一优先级诉求。当前缺失的正是消费标记契约的那一端：编辑器页面。本设计补齐这一环，使"生成 → 编辑 → 保存"闭环可用。

## 1. 目标与非目标

### 目标

1. 打开任意符合标记契约的幻灯片 HTML，完整渲染（缩放、滚动、动效与直接双击打开文件一致）；
2. 所有带 `data-editable` 的文字就地编辑：点击选中、再点进入编辑、失焦生效；
3. 带 `data-editable-image` 的图片可替换，图片写入 `assets/` 目录；
4. 保存将修改序列化写回原 HTML 文件（FSAA），不支持的浏览器降级下载；
5. design-system 面板：可视化选择主题等设计选项，产出**意图清单**（结构化 JSON + 自然语言指令），交给 AI coding agent 落码；
6. **批注**：批注模式下框选一个或多个元素（文本框、图片等），弹窗填写批注，产出**批注清单**（结构化 JSON + 自然语言指令），回传给 AI coding agent 落码。

### 非目标（第一期不做）

- 撤销/重做、增删/排序页面、富文本格式、布局拖拽；
- 页面内直接改样式（视觉修改走"意图清单 → AI 落码"）；
- 宿主 postMessage 集成（只预留接口形状）；
- 服务端、账号体系、多人协作。

## 2. 总体架构

单文件 `editor.html`（纯静态、无框架、无构建），双击或本地静态服务即可运行。

```
┌──────────────────────────────────────────────┐
│ 顶栏：打开 · 保存(⌘S) · [文字编辑|批注] · 设计面板│
├───────────────┬──────────────────────────────┤
│               │                              │
│   舞台 iframe │   design-system 面板（抽屉）  │
│  (幻灯片渲染   │   可视化选项 + 意图清单导出   │
│   + 编辑层)    │                              │
├───────────────┴──────────────────────────────┤
│ 状态栏：当前页 / 选中元素类型 / 脏标记          │
└──────────────────────────────────────────────┘
```

### 关键决策：幻灯片在 iframe 中渲染

编辑器 UI 与幻灯片**样式与脚本完全隔离**：幻灯片的 CSS（`--paper` 等 token、`.slide` 布局）不会污染编辑器，编辑器注入的编辑态样式也不会漏进保存产物。

- 加载方式：`iframe.srcdoc = 文件全文`。srcdoc 与父页面同源，编辑器可直接读写 iframe DOM，**无需 postMessage**；未来接入宿主时，通信点天然落在 iframe 边界上。
- 幻灯片内的框架 JS（fit/键盘/动效）在 iframe 内自然运行，不做任何改写。
- 编辑层（选中框、hover 高亮）由编辑器注入到 iframe 内的一段 `<style>` + 事件监听实现；**保存前从序列化结果中剔除**（见 §5.4）。

备选方案（不采纳）：把幻灯片 DOM 直接内联进编辑器页面——省一层 iframe，但样式隔离要靠 Shadow DOM 或前缀改写，序列化回文件的保真度差，且幻灯片 JS 的选择器上下文被破坏。

## 3. 文件打开与保存

### 3.1 打开

- 主路径：`showOpenFilePicker()`（accept `.html`），拿到 `FileSystemFileHandle` 读全文；
- 辅助路径：拖拽文件到页面 / `<input type="file">`（无句柄，只能降级保存）；
- 关于 `assets/` 目录句柄：FSAA **无法**从文件句柄推导父目录句柄。首次执行图片替换且尚无目录句柄时，弹 `showDirectoryPicker({mode:'readwrite'})` 请用户选一次 assets 目录，句柄在会话内缓存（见 §6）。
- 解析校验：用 `DOMParser` 预检文件是否符合契约（至少有 `.slide` 和 `data-slide-id`）；不符合时提示"该文件不是 html-pptx 技能产物"，仍允许打开（就地编辑退化为仅对带标记元素生效）。

### 3.2 保存

- `Ctrl/Cmd+S` 或顶栏按钮触发；
- 序列化 iframe 文档 → 净化（§5.4）→ 字符串；
- 有句柄：`handle.createWritable()` 直写原文件；无句柄：`showSaveFilePicker()` 让用户指一次；都不支持：Blob 下载；
- 保存成功后清脏状态。
- 脏状态：`beforeunload` 拦截 + 顶栏脏标记（●）。（FSAA 句柄在 `file://` 下可用；跨域 iframe 嵌入时 FSAA 会被权限策略拦截，届时自动落下载路径。）

### 3.3 防串味

同时只打开一个文件。切换文件且有未保存修改时，弹确认（保存/放弃/取消）。

## 4. 渲染

iframe 加载后：

1. 等待 iframe `load`（幻灯片自身 fit() 已完成首次缩放）；
2. 注入编辑层样式与脚本钩子（§5）；
3. 枚举契约元素，构建**编辑注册表**：`data-slide-id` → 页，`data-editable` / `data-editable-image` → 可编辑元素；注册表条目记录 `slide-id + child-index 路径` 作为稳定定位（契约 §编辑器侧-7）。

iframe 尺寸变化（面板抽屉开合、窗口缩放）时不需要通知幻灯片——骨架的 `resize` 监听在 iframe 内自己工作。

## 5. 编辑模式与文字就地编辑

### 5.0 模式切换

顶栏分段控件切换两个互斥模式，全局生效：

- **文字编辑**（默认）：§5.1–5.3 的两段手势文字编辑 + §6 图片替换；
- **批注**：文字编辑手势禁用，舞台进入框选批注交互（§10）。

切换模式时：退出进行中的编辑/框选——进行中的文字编辑按失焦语义**直接提交**（与全文"失焦即确认"一致），进行中的框选取消；清空选中态。批注弹窗为模态，打开期间无法切换模式。模式是纯粹的交互层概念，**不进保存产物**。

### 5.1 两段手势

- **第一击**：选中——元素显示选中框（outline），状态栏显示所在页与元素类型；
- **第二击（或双击/Enter）**：进入编辑——`contenteditable="plaintext-only"`（不支持则 `"true"` 并拦截粘贴，剥成纯文本），全选原文；
- **退出**：`Esc` 取消还原；失焦 / `Ctrl+Enter` 确认。确认后更新注册表与脏状态。

两段手势的原因（契约 §编辑器侧-1）：截断文本框一加 contenteditable 会释放截断、突然撑高，先选中让用户有预期。

### 5.2 编辑中约束

- 纯文本语义：换行以 `<br>` 持久化（注意：Chromium 的 plaintext-only 原生 Enter 产生的是文本 `\n` 而非 `<br>`，直接序列化会在重新解析时丢换行，因此提交时由编辑器把文本节点中的 `\n` 归一化为 `<br>`；编辑期间元素以 `white-space:pre-wrap` 渲染，使 `\n` 即时可见）；不允许粘贴富文本；
- 不改动元素上的任何 `data-*` 与 class；
- 编辑期间禁用骨架的键盘翻页——骨架已实现：`isContentEditable` 时忽略方向键，天然兼容。

### 5.3 hover 高亮

鼠标悬停在可编辑元素上时显示虚线框。实现走 **JS mouseover + 延迟隐藏**，不用 CSS `~` 兄弟选择器悬浮按钮（pointer-events 断链坑，frontend-slides 实测）。

### 5.4 序列化净化

保存前对 iframe `document.documentElement.cloneNode(true)` 做：

1. 移除编辑器注入的 `<style data-editor-injected>` 与选中框等节点（全部带 `data-editor-injected` 属性，一处登记）；
2. 移除所有 `contenteditable` 属性、选中态 class；
3. **框架运行时状态归位**：移除 `<html>` 上的 inline `style`（`--slide-scale`）、移除骨架 v2 动效门槛在 `<html>` 上添加的 `js` class、移除所有 `.in-view` class、移除框架 JS 为 `[data-anim]` 分配的 `--i` 内联自定义属性（style 因 CSSOM 重序列化产生的格式差异属一次性规范化差异）、chrome 页码文本重置为 `1 / N`——这些是骨架 JS 的运行时产物，不属于文件；
4. 剥离图片 `src` 上的 `?v=` 查询串（§6 的会话内缓存刷新）；
5. 输出 `"<!DOCTYPE html>\n" + clone.outerHTML`。

净化后的字符串必须与"技能生成的纯净产物"**语义同构**。注意：`outerHTML` 序列化会做属性规范化（引号、自闭合），因此**开发期需把 skeleton.html 做到"序列化往返幂等"**——即对未修改的 deck 执行一次"打开→保存"，产物与原文的 diff 应为空或仅含白名单差异；达不到就调整骨架写法，直到幂等。

## 6. 图片替换

- 点击（选中态下再点）`data-editable-image` 图片 → `showOpenFilePicker()` 选图；
- 写入策略：**同名覆盖优先**。新文件与现 `src` 同扩展名 → 覆盖 assets/ 原文件，`src` 不变（会话内用 `?v=` 破缓存，见下）；不同扩展名 → 以原文件主体名 + 新扩展名写入 assets/，更新 `src`；
- 无 assets 目录句柄时先引导授权（§3.1）；拒绝授权则提示并中止替换（绝不退化为 base64 内嵌——契约硬规则）；
- 会话内预览：写入磁盘后，用 `?v=<timestamp>` 或 blob URL 刷新显示，但**该查询串只存在于编辑会话的显示层，不进序列化产物**（§5.4 净化项）；
- 换扩展名的边界：新文件已写入 assets/ 而 HTML 未保存时关闭，会留下孤儿文件——可接受，状态栏提示"有未保存的图片引用变更"；
- 替换即脏，随正文一起保存 HTML。

## 7. Design-System 面板与意图清单

### 7.1 面板形态

右侧抽屉，分组展示设计选项。第一期分组：

1. **主题配色**（核心，`theme`）：13 套预置主题（`skills/html-pptx/references/themes.md` 为数据源），每套渲染为可视化卡片——paper/ink/accent 三色块 + 字体样张（"Aa 标题字 / 正文字"）；
2. **明暗节奏偏好**（`rhythm`）：`low` 少 / `moderate` 适中 / `high` 多（hero 暗页频率）；
3. **动效强度**（`motion`）：`none` 无 / `subtle` 克制（默认 reveal）/ `strong` 强；
4. **自由补充**（`custom`）：多行文本（对应 AskUserQuestion 的 "Other" 自由输入）。

面板**只收集意图，不改幻灯片样式**（已确认决策：AI 在开发侧落码）。

### 7.2 意图清单 Schema（参考 AskUserQuestion 形态）

面板数据源与产出共用一份 Schema：

```jsonc
{
  "version": 1,
  "kind": "design-intent",
  "deck": "index.html",
  "questions": [                       // 面板渲染依据（内置在 editor.html）
    {
      "id": "theme",
      "header": "配色",
      "question": "选择整体主题配色",
      "multi_select": false,
      "options": [
        { "id": "a1", "label": "墨水经典",
          "visual": { "paper": "#f1efea", "ink": "#0a0a0b", "accent": "#0a0a0b",
                      "font_display": "serif", "font_body": "sans" },
          "description": "通用安全，杂志感最强" }
      ]
    }
  ],
  "answers": {                         // 用户选择结果
    "theme":   { "choice": "b1" },
    "rhythm":  { "choice": "moderate" },
    "motion":  { "choice": "subtle" },
    "custom":  { "text": "封面希望更克制一点" }
  }
}
```

### 7.3 导出

"生成修改指令"按钮把 answers 编译为**给 AI coding agent 的自然语言指令 + 附 JSON**，复制到剪贴板，例如：

> 请按以下意图修改 index.html（技能：skills/html-pptx）：主题切换为 B1 克莱因蓝（整套 token 替换 skeleton 的 SLOT: theme tokens，规则见 references/themes.md）；明暗节奏适中；动效保持克制。用户补充：封面希望更克制一点。结构化意图如下：```json …```

### 7.4 主题数据源

`themes.md` 是契约级数据源，但 editor.html 不运行时 fetch 它（`file://` 下不可靠）——**面板内置一份由脚本从 themes.md 生成的 JSON**：`skills/html-pptx/scripts/sync-themes.mjs`（Node ≥20、零依赖）解析 themes.md 的 13 套主题条目（名称 / 适合+调性 / ```css token 块），生成面板卡片 JSON（id、label、description、visual、tokens），幂等写回 editor.html 的 `/*__THEMES_JSON_BEGIN__*/ … /*__THEMES_JSON_END__*/` 标记区间。改主题必须先改 themes.md，再跑 `node skills/html-pptx/scripts/sync-themes.mjs`；标记区间内禁止手工编辑，脚本自检失败（主题数 ≠ 13、必填字段缺失、标记异常）会以非零退出。

## 8. 嵌入预留（不实现，只定形状）

iframe 嵌入宿主时的协议草案，写在这里防止架构堵死：

- 入：`postMessage({type:"pptx-html:load", html, assetsUrl?})` → 编辑器以 srcdoc 渲染；
- 出：`postMessage({type:"pptx-html:save", html})`（宿主落盘）、`{type:"pptx-html:dirty", dirty}`、`{type:"pptx-html:annotations", payload}`（批注导出，§10.4）；
- 嵌入态检测：`window.parent !== window` → 保存一律走 postMessage（嵌入加载没有文件句柄，FSAA 在此语境只能另存/下载，且权限策略拦截时 FSAA 调用会被静默吞掉，宿主永远收不到保存结果）。

## 9. 错误与边界

| 场景 | 行为 |
|---|---|
| 文件不符合契约 | 警告条提示，仍可打开（仅标记元素可编辑） |
| FSAA 不可用 | 保存按钮变为"导出下载"，tooltip 说明 |
| 用户拒绝 assets 目录授权 | 图片替换中止并提示，文字编辑不受影响 |
| 幻灯片 JS 抛错 | 编辑层不依赖幻灯片 JS，编辑功能仍可用；控制台透出 |
| 超大文件（>5MB） | 正常打开；保存前不特殊处理（单文件文本量级可控） |

## 10. 批注（框选 → 批注 → 回传 AI）

批注是**沟通层**功能：用户在幻灯片上框出"有问题的区域"，写下意见，产出结构化批注清单交给 AI coding agent 落码。批注**不修改文档、不置脏、不进保存产物**——这与意图清单（§7）同一哲学：编辑器收集意图，AI 落码。

### 10.1 框选交互（批注模式）

- mousedown 拖拽绘制选框（marquee）。选框层注入 iframe 文档内（带 `data-editor-injected`），**坐标在 iframe 坐标系内计算**——命中检测用各元素 `getBoundingClientRect()`，与选框同坐标系，天然不受幻灯片 transform 缩放影响。
- 拖拽期间抑制文字选中与图片原生拖拽（`user-select:none` + `dragstart` preventDefault）；滚轮滚动保留（只有拖拽手势被占用）；`Esc` 取消本次框选。
- **命中规则（宽松相交）**：选框与候选元素矩形**相交即命中**，不要求完全包含（大标题、通栏图很难完整框住）。
- **候选元素**：`[data-editable]` 与 `[data-editable-image]`，排除 `data-editable-skip` 子树。框选范围比文字编辑大——一次可以框住多个文本框、图片混选。

### 10.2 批注弹窗

mouseup 且有命中时：

1. 命中元素加高亮描边 + **编号角标**（注入节点，净化剔除）。**注入的视觉元素必须按当前 `--slide-scale` 反缩放补偿**（角标字号、描边宽度除以 scale），否则缩放画布里角标小到不可读。角标编号 = 批注序号；同一元素属于多条批注时角标堆叠显示；
2. 弹出批注窗口（**父页面 DOM，不在 iframe 内**，避免污染与焦点问题）：
   - 命中元素清单：命中序号（#1…#n，供剔除引用，与角标的批注序号不同义）+ 所在页 slug + 标签名 + 文本摘要（前 40 字）/ 图片 src；每条带勾选框，可剔除误选；
   - 批注输入：多行 textarea；
   - 提交 / 取消（取消则清除高亮角标，不留痕）。
3. 提交后批注进入**批注清单**（批注模式下舞台右下浮动列表）：每条可点击定位（滚动到所在页并闪烁高亮对应元素）、可删除；角标保留在元素上直到删除该条批注。

### 10.3 元素关联（回传 AI 的关键）

每条批注的 target 用**三层冗余引用**，AI 落码时可定位、可校验、可纠错：

| 字段 | 来源 | 作用 |
|---|---|---|
| `slide` | 所在页 `data-slide-id` | 稳定语义定位到页（契约硬规则保证存在） |
| `path` | 页内 child-index 路径（`tag.index` 链，如 `h1.0`、`div.2>span.1`） | 精确 DOM 定位，与编辑注册表同一算法（契约 §编辑器侧-7） |
| `excerpt` | 元素当前文本前 40 字 / 图片 `src` | 内容校验：AI 按 path 找到的元素应对得上 excerpt；对不上说明路径漂移，按 excerpt 全文检索找回 |

path 的脆弱性（AI 改稿后 child-index 可能变）由 excerpt 兜底；excerpt 被用户刚编辑过也不怕——保存后的文件里就是新文本。

### 10.4 批注 Schema 与导出

与意图清单（§7.2）同构：

```jsonc
{
  "version": 1,
  "kind": "annotation",
  "deck": "index.html",
  "annotations": [
    {
      "id": "anno-1",
      "targets": [
        { "slide": "metrics", "path": "h1.0", "tag": "h1", "excerpt": "拆完之后，数字说话" },
        { "slide": "metrics", "path": "div.2>span.1", "tag": "span", "excerpt": "2 小时" }
      ],
      "note": "这两个数字换成 Q3 最新口径，单位统一成中文",
      "created_at": "2026-09-16T10:30:00+08:00"
    }
  ]
}
```

批注清单底部"**导出批注指令**"按钮：编译为自然语言指令 + 附 JSON，复制到剪贴板。**嵌入模式下同时向宿主发 `postMessage({type:"pptx-html:annotations", payload})`**（嵌入协议出向消息随之扩展）——宿主场景的"回传 AI"靠这条消息，剪贴板只是人工通道。示例：

> 请按以下批注修改 index.html（技能：skills/html-pptx）。共 2 条批注，每条按 slide + path 定位元素，用 excerpt 校验；对不上时按 excerpt 检索。
> 批注 1（页 metrics，2 个元素）：这两个数字换成 Q3 最新口径，单位统一成中文。目标：h1.0「拆完之后，数字说话」、div.2>span.1「2 小时」。
> 结构化批注：```json …```

### 10.5 生命周期与边界

- 批注**仅存会话**：不写文件、不置脏、不触发 beforeunload；未导出的批注在清单头部常显"未导出"徽标（导出后消失）——不拦截的关闭提示在 Web 平台无法有效送达，徽标替代之；
- 文字编辑修改了某元素文本后，已有批注的 `excerpt` **不自动更新**（快照语义），导出时以导出时刻重新抓取 excerpt 为准并标注可能已变更。
- 框选零命中：静默结束，不弹窗。
- 空批注文本：禁止提交（按钮置灰）。

## 11. 验收标准

示例 deck 要求：≥8 页，覆盖边界情况——暗色页、含截断风险的窄文本框、多行 `<br>` 文本、至少两张 `data-editable-image` 图片（其中一张换图时换扩展名）。

1. 在 Chrome 中经编辑器打开示例 deck：渲染与直接打开文件**截图对比无视觉差异**（无文字重叠、无错位、无异常空白）；
2. 修改三处文字（含一处多行编辑、一处截断文本框）、替换两张图片（其一换扩展名）、保存；重新直接打开原文件：修改生效、无编辑态残留、文件可通过 `editing-contract.md` 生成侧自检（grep 检查）；
3. **往返幂等**：对未做任何修改的 deck 执行"打开 → 保存"，产物与原文 diff 为空或仅含 §5.4 白名单差异；
4. Firefox 中打开同一文件：编辑可用，保存降级为下载；
5. 面板选择主题 B1 + 动效 `subtle` + 自由补充，导出的指令文本粘贴给 coding agent 后可直接执行（人工走查）；
6. 骨架框架层（标注"禁止修改"的 CSS/JS 块）在保存产物中语义不变（归一化后 diff 为空）；
7. **批注端到端**：批注模式下框选命中多个元素（跨两个文本框 + 一张图）→ 弹窗清单正确（页 slug/标签/摘要）→ 剔除一个误选项 → 提交 → 导出指令中 JSON 的 `slide`/`path`/`excerpt` 能在原文件中真实定位到对应元素（harness 自动回验）；保存产物不含任何批注痕迹（角标、高亮、弹窗节点均为注入节点，随净化剔除）；
8. **批注边界**：零命中不弹窗；空批注不可提交；Esc 取消框选无残留；批注全程不置脏。
