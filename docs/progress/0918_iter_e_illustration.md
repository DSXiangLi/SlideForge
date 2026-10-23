# 0918 · 迭代 E：AI 插画管线

依据：`docs/design/illustration-pipeline.md`（2026-09-18 修订意见 6 + optimal-solution 标准⑥）。目标：契约先行落地图片槽位契约（v5），SKILL.md 新增 Step 5.5 插画 pass（内容验收后、用户声明"AI 插画模式"才进入的独立 pass），编辑器上传置 `data-image-state="uploaded"`，新增静态校验器 check-images.mjs，并用环境中的 oai生图技能做真实端到端冒烟。

## 变更

| 文件 | 变更 |
|---|---|
| `skills/html-pptx/references/editing-contract.md` | 契约 v5（契约先行）：新增"图片槽位契约"节——`data-editable-image` 图位必携 `data-image-slot`（语义名-宽x高）/ `data-image-intent`（内容意图一句话）/ `data-image-state`（placeholder→generated→uploaded 状态机）三属性；三方绑定【硬规则】（槽位比例↔构图宽高比↔生图比例，静态可验容差 5%）；生成侧义务（新产物全图位写全三属性；pptx 转换原图补 slot/intent 且置 uploaded）；编辑器义务（上传只换 src 文件、置 uploaded、保留 slot/intent）；存量无槽位 deck 兼容（编辑器不强制、校验器警告不报错）；反降级【硬规则】（插画模式禁 placeholder 残留，失败诚实回退并列交付说明）。标记一览表补三属性行；生成侧规则 4、编辑器规则 6 同步指向新节 |
| `skills/html-pptx/SKILL.md` | 新增 Step 5.5 · 插画 pass（四步：盘点槽位 → 风格规划（主题 G7 字段，缺省走推导=主题色抽象图形精细化版本 + token 色系）→ 逐槽生图（提示词=统一风格段+槽位 intent+比例；oai生图 CLI 契约，`<oai生图技能目录>` 占位不硬编码机器路径；比例映射最近支持档；assets/ 同名覆盖、state 翻 generated）→ 回归校验（渲染重跑 + `check-images.mjs --mode illustration` 零错误 + 反降级））；Step 6 交付说明追加插画模式三件事（已生图槽位 / 回退槽位 / 如何替换）；图片纪律节同步（占位图必写全三属性；pptx 原图 state=uploaded；插画走 Step 5.5）；标记摘要补三属性；Step 0 转换入口补原图槽位义务 |
| `editor.html` | v1.9：图片上传成功后 `img.setAttribute('data-image-state','uploaded')`（同名覆盖与改名两个分支共用），保留 slot/intent；头部版本与变更记录同步。其余不变 |
| `skills/html-pptx/scripts/check-images.mjs` | 新增：图片槽位契约静态校验器（node，零依赖，风格对齐 sync-themes.mjs）。校验：src 必须 assets/ 相对路径且落盘存在；三属性完整性（有 slot 缺 intent/state = 错误；无 slot = 存量警告）；state 合法值；slot 格式 `<语义名>-<宽>x<高>`；比例三方绑定（判定源：img width/height 属性 → style aspect-ratio → style px 宽高对 → 素材固有尺寸，SVG viewBox/PNG IHDR/JPEG SOF/GIF/WebP VP8X/VP8/VP8L 零依赖解析，容差 5%，全部不可判定=警告）；`--mode illustration` 下 placeholder 残留与缺槽位均为错误。幂等纯读取，有错误非零退出 |
| `tests/decks/charts-a3/index.html` | 封面图位补 v5 三属性：`cover-hero-4x5`（SVG viewBox 800×1000=0.8 精确匹配）+ intent + `state="placeholder"` |
| `tests/decks/culture-kraft/index.html` | 田野图位补 v5 三属性：`village-fields-4x3`（img 840×630 与 SVG 1200×900 双源一致）+ intent + `state="placeholder"` |
| `tests/harness/run_e2e.py` | 新增 T16（check-images 三场景：合规 deck 零警告 rc=0 / 存量 tech-ikb 2 警告 rc=0 / 插画模式 placeholder 残留 rc=1 / 重跑幂等）与 T17（stub showOpenFilePicker/showDirectoryPicker 驱动真实 replaceImage 同名覆盖分支：state→uploaded、slot/intent 保留、置脏、保存产物持久化且 ?v= 剥离） |
| `docs/design/illustration-pipeline.md` | 状态：待评审 → 已实施（迭代 E） |
| `docs/skill-roadmap.md` | 未来规划表"AI 插画管线"行：待评审 → ✅ 已完成（迭代 E） |
| `docs/design/README.md` | 文档地图 illustration-pipeline 行标注（迭代 E 已实施） |
| `docs/progress/README.md` | 索引补本迭代 |
| `AGENTS.md` | 技能 v1.4→v1.5（Step 5.5 + check-images.mjs）、editor v1.8→v1.9、契约 v4→v5 描述同步 |

## 验收

- `python3 tests/harness/run_e2e.py`：**28/28 PASS**（原 26 项 + T16 + T17；10 个 deck 往返幂等与全部既有用例回归全绿）。Chromium 145 headless。
- check-images 手工三场景复核（见 T16 证据）：合规零警告、存量警告 rc=0、插画模式报错 rc=1。

## 真实冒烟（oai生图，GPT-Image-2.5）

在 `/tmp/iter-e-smoke/deck`（charts-a3 的临时副本，**未污染 tests/decks/ fixture**）执行 Step 5.5 单槽位生图：

1. **盘点**：全 deck 唯一槽位 `cover-hero-4x5`（封面，intent="城市骑行通勤的抽象意象：象牙底上的深绿骑行路线折线与点阵，竖幅构图"）；
2. **风格规划**：A3 主题未声明 G7，走缺省推导——主题色抽象图形的精细化版本，带入 token 色系（ink #1a2e1f 深林绿 / paper #f5f1e8 象牙）；
3. **生图**（1K/low/n=1 控成本，4x5 → `--aspect-ratio 4:5` 精确命中支持档）：

   ```bash
   python3 <oai生图技能目录>/script.py "Refined abstract geometric illustration, deep forest green (#1a2e1f) fine linework and subtle dot grid on ivory paper background (#f5f1e8), flat editorial style, generous negative space. Subject: abstract city cycling commute imagery — one elegant winding route line with waypoint dots across a faint dot grid, vertical composition. No text, no words, no letters." \
     --aspect-ratio 4:5 --resolution 1K --quality low --n 1 \
     --output-dir /tmp/iter-e-smoke/deck/assets --format png --name cover-ride
   ```

4. **结果**：`assets/cover-ride.png` 落盘成功，固有尺寸 1024×1280（0.8 = 4:5 精确）；img `src` 由 cover-ride.svg 改为 cover-ride.png（同名 basename），`data-image-state` 由 placeholder 翻 generated，被替换的占位 svg 已删除（避免孤儿文件）；
5. **回归**：`check-images.mjs --mode illustration` 通过（exit 0，无警告）；Playwright 渲染实测——生成图加载完成、渲染框 520×650 与占位期构图尺寸逐像素一致、封面 1920×1080 无溢出（图片替换未引起布局偏移）。

产物留在 `/tmp/iter-e-smoke/` 供查阅，不进仓库。

## 偏离记录（deviation）

1. **"两个测试 deck"的第二个改为 culture-kraft**：任务括号内候选 motion-d2 / infographic-d1 的 `data-editable-image` 只出现在 deck 注释中（两者均无真实图位），故第二个 v5 deck 选了 culture-kraft（真实图位、比例干净 4:3）。tech-ikb 有意保持存量无槽位状态，作为校验器"警告不报错"兼容路径的活样本。
2. **同名覆盖的扩展名处理**：规格 §2 要求"同名覆盖占位图"，但占位图是 SVG 而生图产物是 PNG——落码为 **basename 同名**（`cover-ride.svg`→`cover-ride.png`）并同步更新 img src 扩展名；冒烟中删除了被替换的占位 svg 避免孤儿文件（SKILL.md 未强制删除，留给执行者判断）。
3. **比例三方绑定的静态判定源**：容器宽高比在静态 HTML 上无法通用判定（grid/flex 计算值依赖布局引擎），校验器实现为依次收集可判定源（img 属性 → style aspect-ratio → style px 宽高对 → 素材固有尺寸），**全部可判定源各自**与 slot 声明比例比对（容差 5%），全部不可判定则警告而非放行。
4. **插画模式下缺槽位升级为错误**：规格 §4 只明确 placeholder 残留违规；插画模式产物理应是完整 v5 契约，故 `--mode illustration` 下缺 slot 的 img 同样报错（默认模式仍为警告）。
5. **T17 用 JS stub 驱动真实 replaceImage**：headless 无法交互 FSAA 系统弹窗（与既有"FSAA 直写路径不测"的约定一致），stub 只替身系统弹窗与磁盘写入，replaceImage 的 DOM 变更 / 置脏 / 序列化路径全真。（调试插曲：T17 初版"?v= 残留"断言漏写 `not` 导致假 FAIL，三轮定位为测试自身笔误，编辑器 ?v= 剥离行为始终正确。）

## 明确不做

- 不做逐页即时生图（规格 §8：与内容生成解耦是本设计的核心）；
- 不做页面内"重新生成此图"按钮（页面内无 AI，重新生图走 coding agent 流程）；
- 存量 deck（tech-ikb 等 8 个无槽位 deck）不追溯补标记——v5 是生成侧新产物义务，旧 deck 仍是合法契约产物（编辑器兼容、校验器警告）；
- 不做 git commit。
