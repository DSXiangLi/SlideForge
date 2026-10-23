# 0918 · 编辑器 v2（样式编辑 / 目录侧栏 / git 版本）

> 依据：`docs/design/editor-v2.md`（唯一权威需求源）+ `docs/design/iteration-plan.md`（迭代 A）。
> 契约先行：`skills/html-pptx/references/editing-contract.md` 升 v2，新增"样式覆盖"节。

## 做了什么

### 1. 文字样式编辑（editor.html v1.6）

- 选中 `data-editable` 文字元素（或进入编辑）后，顶栏出现样式控件组：字体下拉（deck `:root` computed style 读 `--font-display/--font-body/--font-mono` 三个主题栈 + serif/sans-serif/monospace 系统项）、字号（数字输入 + ±2 步进，画布坐标 px，低于 18px 警告不禁止）、字色（`--paper/--ink/--accent` 等 6 个 token 色板 + 自定义 color input）、对齐（左/中/右/两端）。
- 粒度是整个元素（plaintext-only 下不做选区级富文本）；只写白名单四属性 inline style（`font-family/font-size/color/text-align`），置脏并随 §5.4 序列化保留。
- 主题相关值写 `var()` 引用（如 `color:var(--accent)`），换主题时用户样式跟随主题——已写入契约。
- 图片元素选中时控件组隐藏，"替换图片"按钮逻辑不变。

### 2. PPT 式目录侧栏（editor.html v1.6）

- 主区左侧 240px 侧栏，顶栏"目录"按钮切换；独立打开默认展开，嵌入态默认收起。
- 缩略卡 = 克隆 section 进 Shadow DOM：deck CSS 注入影子树（`:root`→`:host` 使 token 生效），注入 `animation:none !important` 并补 `.in-view` 强制动效终态（骨架 v2 的隐藏门槛 `html.js` 在影子树里天然不命中）；去全部 `id`、`pointer-events:none`、`aria-hidden`；`--slide-scale = 缩略宽度/1920` 写到 host，左边距补偿 `top center` 缩放原点。
- IntersectionObserver 懒渲染；点击卡片 → iframe 内 `.deck` 滚动到对应 slot；当前页高亮与 sbPage 页码跟踪共用 `curSlideIdx`。
- 编辑（文字提交 / 样式 / 换图）后按需失效重克隆对应卡片——导航件不是监视器，不做实时同步。

### 3. 本地 git 版本（新增 tools/edit.py）

- `tools/edit.py`：python3 标准库零依赖伴随服务。静态托管工作目录（目录内无 editor.html 时回落项目根副本，故 `python3 tools/edit.py some/deck/` 直接可用）+ 四个 API：
  - `GET /api/health` → `{ok, git, gitReady}`；
  - `POST /api/save {path, html, init?}` → 原子写（同目录临时文件 + os.replace）+ `git add` 仅该 deck 与同级 `assets/` + commit（message `edit: <时间戳>`）；非 git 仓库时不擅自 init，需调用方显式 `init:true`（编辑器 UI 弹一次确认）；
  - `GET /api/versions?path=` → 该文件提交列表（hash/时间/message，时间倒序）；
  - `POST /api/rollback {path, hash}` → 工作区有未提交改动时先自动 `pre-rollback` 提交（永不丢数据），再 `git show` 还原目标版本。
- 所有 API 用 realpath 校验路径必须在工作目录内，拒绝路径穿越；git 身份逐命令 `-c user.name/email` 注入，不依赖用户全局配置。
- 编辑器侧：加载时探测同源 `/api/health`；有后端且经 `?deck=` 打开时保存走 `/api/save`（每次保存一版本），顶栏"历史"按钮可用（版本列表面板 + 确认后回滚 + 回滚后重新加载文件）；无后端维持 FSAA/下载现状，历史置灰并 tooltip 提示 `python3 tools/edit.py`；嵌入态保存仍走 postMessage 不变。

## 怎么用

```bash
# 带版本记录的编辑（推荐）
cd 某deck目录 && python3 /path/to/tools/edit.py        # 浏览器自动打开 ?deck=index.html
python3 tools/edit.py tests/decks/tech-ikb             # 指定工作目录
python3 tools/edit.py --port 8930 --no-browser         # 换端口 / 不开浏览器

# 不带版本记录（维持现状）
直接用 Chrome/Edge 打开 editor.html，或任意静态服务托管
```

编辑器 URL 支持 `?deck=<工作目录内相对路径>` 直接载入；不带参数时仍走"打开文件"（FSAA），此时无路径信息，保存维持 FSAA/下载路径。

## 验收（tests/harness/run_e2e.py）

新增三条用例，全量回归：

- **T10 文字样式编辑持久化**：控件组随选中显隐（图片选中隐藏）；四属性即时生效 + 置脏；<18px 警告不禁止；保存 → 重载后 inline style 完整回显（字体下拉回显 `var(--font-body)`）；白名单外属性不混入。
- **T11 目录侧栏导航**：嵌入态默认收起；N 页 N 卡；懒渲染滚到底全部出图；克隆体无 id、动效终态（opacity=1）；点击第 3 卡 → iframe 滚动位置/卡片高亮/页码三者同步；编辑后对应卡片失效重克隆。
- **T12 伴随服务 git 版本**：harness 自 spawn `tools/edit.py`（临时目录隔离，结束清理）；无后端时历史置灰且 tooltip 含启动方式；路径穿越三种形态全部 400；非仓库保存不提交、`init:true` 后提交；UI 保存两次 → 两条 `edit:` 提交；磁盘制造未提交改动后 UI 回滚到第一版 → 文件还原 + `pre-rollback` 保护提交。

结果：**21/21 PASS**（2026-09-18，`python3 tests/harness/run_e2e.py`，Chromium 145 headless）——T1 往返幂等 ×8、T2 编辑 ×2、T3 Esc 取消、T4 渲染一致性 ×2、T5 assetsUrl、T6 独立模式、T7/T8 批注、T9 面板导出（以上既有用例全部保持绿）、T10/T11/T12 新增用例全过。

## 偏离设计文档的决定（均已在实现中注释）

1. **缩略图用 Shadow DOM 而非直接克隆进父页面**：设计文档只规定"克隆 section + 去 id + animation:none"。直接挂进父页面会让 deck 的 `.slide`/`.reveal` 等类与编辑器 chrome 共享样式表层级（污染风险双向）；Shadow DOM 顺带解决"骨架 v2 的 `html.js` 门槛在克隆里不命中、动效天然终态"。代价是要把 deck CSS 文本注入影子树并把 `:root` 改写为 `:host`。
2. **`git add` 的 assets/ 取 deck 同级目录**：设计文档写"仅该 deck 文件与 assets/"，按项目资产约定（每个 deck 目录自带 assets/，见 tests/decks 布局）解释为"deck 所在目录的 assets/"，而非工作目录根部。
3. **后端模式下非 `?deck=` 打开的文件不走 /api/save**：FSAA 文件句柄不暴露磁盘路径，无法定位 `path`；此类文件保存维持 FSAA/下载，历史按钮 tooltip 说明原因。这是 FSAA 的固有限制，不是偷懒。

## 遗留

- 字号步进固定 ±2px；大标题想从 128 调到 96 要点很多次（可直接输入数字）。
- 历史面板不支持版本 diff 预览（只有 message/时间/hash）；回滚只还原 deck 文件，assets/ 图片变更靠直接替换文件。
- `tools/edit.py` 单线程语义足够本地使用；多客户端并发保存未做串行化（ThreadingHTTPServer 下理论存在，本地单用户场景忽略）。
