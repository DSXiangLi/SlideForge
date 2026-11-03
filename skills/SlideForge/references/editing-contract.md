# 可编辑标记契约（Editing Contract）

本文件是**生成技能**（生产者）与**编辑器页面**（消费者）之间的唯一协议。双方各自实现，以 HTML 文件中的标记为通信介质。文件是唯一事实源。

## 标记一览

| 标记 | 位置 | 含义 |
|---|---|---|
| `data-slide-id` | 每个 `<section class="slide">` | 页面的稳定语义 ID |
| `data-editable` | 叶子文本元素 | 用户可在编辑器中就地修改的文字 |
| `data-editable-image` | `<img>` | 用户可替换的图片 |
| `data-image-slot` | `<img data-editable-image>` | 图片槽位：语义名 + 宽高比（如 `cover-hero-21x9`），见"图片槽位契约"节 |
| `data-image-intent` | `<img data-editable-image>` | 图片内容意图一句话（占位图依据 / 生图提示词槽位部分 / 换图指南） |
| `data-image-state` | `<img data-editable-image>` | 图像供给状态机：`placeholder` / `generated` / `uploaded` |
| `data-editable-skip` | 任意元素 | 纯装饰，编辑器必须忽略 |
| `data-render-mode` | `<section class="slide">` | 页面渲染形态：`html`（缺省）/ `baked`（整页生图烙入），见"页面烙入模式"节 |

## 规则（生成侧义务）

1. **稳定语义 ID**：`data-slide-id` 用描述性 kebab-case slug（如 `cover`、`q3-growth`、`closing`）。【禁止】用页码或遍历序号（`slide-1`、`slide-2`）——增删页面后序号漂移，编辑器的定位会套到错误元素上。
2. **标记在最小语义容器上**：`data-editable` 标在直接承载文字的元素（`h1`/`p`/`li`/`blockquote`/`td` 等），【禁止】标在 `section`、`div` 容器上——那会让编辑器把整个版式变成一个大文本框。
3. **内容保持简单**：`data-editable` 元素内部只含纯文本或简单行内标签（`<b>` `<i>` `<em>` `<strong>` `<br>`）。不含块级嵌套、不含 `<img>`、不含 SVG。
4. **图片**：`data-editable-image` 的 `src` 必须是指向 `assets/` 的相对路径。`alt` 写有意义的描述（编辑器会展示它）。图片槽位三属性（`data-image-slot` / `data-image-intent` / `data-image-state`）见"图片槽位契约"节——新产物必须写全。
5. **装饰标记**：色块、分割线、背景图形、页眉页脚装饰文字，标 `data-editable-skip`。
6. **框架层不可编辑**：骨架中标注"框架层 · 禁止修改"的 CSS/JS/chrome 不在标记范围内，编辑器不得触碰。

## 规则（编辑器侧约定）

1. **两段手势**：首次点击只选中（显示选中框），再次点击（或双击）才进入编辑——否则给截断文本框加 contenteditable 会释放截断、元素突然撑高。
2. **纯文本优先**：进入编辑时设 `contenteditable="plaintext-only"`（不支持的浏览器降级 `"true"` 并拦截粘贴格式）。不提供富文本工具栏。
3. **就地补丁**：编辑结果直接写回 DOM，序列化整个文档保存。**永不重载页面**。
4. **序列化净化**：保存前移除一切编辑态残留（`contenteditable` 属性、选中态 class、编辑器注入的节点），并把骨架运行时动效残留归位（拆字 span 还原为 textContent、`draw-line` 的描边 style、`<html>` 的运行时 class 等，清单见"动效与编辑"节），保证存回的文件与"纯净产物"同构。
5. **保存**：File System Access API 直写原文件；不可用（非 Chrome/Edge、跨域 iframe 受限）时降级为下载导出。
6. **图片替换**：用户选择本地图片后，写入 `assets/` 目录并更新 `src`；同名覆盖优先（保持"替换 assets/ 同名文件即可换图"的心智模型）。上传成功后把该 img 的 `data-image-state` 置为 `"uploaded"`，**保留** `data-image-slot` 与 `data-image-intent` 属性——契约不随换图丢失。
7. **兜底定位**：编辑器内部记录修改位置时，用 `data-slide-id` + 祖先 child-index 路径——页与路径之间用 `:`，路径层级之间用 `>`，如 `cover:h1.0`、`metrics:div.2>span.1`。不用全局遍历序号。

## 生成侧自检

交付前执行：

```bash
# 每页都有稳定 ID
grep -c 'data-slide-id="' index.html   # 应等于页数
# 没有可编辑元素里嵌套块级结构（人工抽查）
# 图片全部指向 assets/
grep -o 'src="[^"]*"' index.html | grep -v 'src="assets/'   # 应为空
```

## 动效与编辑（契约级，v3 修订，v6 扩展）

【硬规则】**文本破坏性动效必须运行时化**——产物文件中的文字永远是完整纯文本节点，拆字（split-text / 逐字 / 碎聚等把文字拆成 `<span>` 的实现）与逐字变换（typewriter / scramble）只允许由骨架 JS 在运行时进行：

1. 生成侧只写纯文本 + 语义标记（如 `<h1 data-editable data-anim="chars">标题</h1>`），【禁止】在产物文件中写入拆字 span；
2. 骨架 JS（skeleton v3 起）在元素入场时把 `textContent` 拆成 span 序列执行动画，**动画完成后还原为纯文本节点**；typewriter / scramble（v5）同语义——运行时改写 textContent，完成后精确还原原文本；滚动回滚默认不重复触发；
3. 编辑该元素就是编辑一个纯文本 `data-editable` 元素，与既有契约完全一致；编辑后动画不失效，下次入场按新文本重拆/重打；
4. 用户在拆字动画进行中点击进入编辑时，编辑器先调用骨架暴露的 `window.__pptxMotion.restore(el)` 强制还原为纯文本，再进入编辑态；
5. 序列化净化新增一条：若遇未还原的拆字 span 容器（动画进行中被打断、或骨架缺失的旧产物），还原为 `textContent` 再保存；`count-up` / `typewriter` / `scramble` 元素保存前必须还原为终值文本（`__pptxMotion.restoreAll()` 统一覆盖）。

**mask-lines 的结构归属**（v5 新增 recipe）：`.ml-line`（外遮罩）+ `.ml-inner`（内层位移）的**分行结构是产物的一部分**，由生成侧显式写出、保存时原样保留——它不是运行时残留，编辑器不得塌缩。`.ml-inner` 是 `data-editable` 叶子文本元素（逐行就地编辑）；`.ml-inner` 上由骨架 JS 分配的 `--i` 序号是运行时状态，净化时移除。改行数（增删 `.ml-line`）属于结构变更，编辑器不支持，走 AI 流程。

**透明填充类效果的编辑态还原**（v5 新增）：`gradient-flow` 等 `background-clip:text` + 透明填充的效果，编辑态下用户看不到自己正在编辑的文字。规则：生成侧必须把"透明"写为 `-webkit-text-fill-color:transparent` 并保留 `color` 本色兜底（骨架 recipe 已如此）；编辑器在元素进入编辑态（`.ed-editing`）时强制 `-webkit-text-fill-color:currentColor` + 去背景渐变 + 停动画（编辑器注入样式，保存时随净化剔除）。

**pointer / scroll 族的运行时状态**（v5 新增）：pointer tracker 只写 CSS 变量、不碰 DOM 结构；scroll 族的 parallax/scrub/scrub-draw 由骨架 JS 滚动驱动、只往 `.slide` 写 `--sp` 进度变量（read-progress 是纯 CSS scroll-timeline，无运行时状态）。骨架 v5 暴露 `__pptxMotion.freeze()`——编辑器加载 deck 后调用以冻结交互动效层（摘除 tracker 与滚动监听、清空变量），read-progress 由编辑器注入样式冻结；冻结只影响编辑器内的 iframe，不进保存产物。

**canvas FX 仪式层的净化**（v6.1 新增，skeleton v5.1）：`canvas[data-fx]` 在产物文件中是**空元素**——无 width/height 属性、无内容、一律 `data-editable-skip`，编辑器忽略。骨架运行时的唯一 DOM 写入是 DPR 修正的 `width`/`height` 属性（像素绘制不是 DOM 状态，序列化天然不含）；且 canvas 首次入视口才初始化——从未入视口的 canvas 零残留。净化口径与 pointer 变量相同：`__pptxMotion.freeze()` 主责（停帧 + 清屏 + 摘除 width/height，freeze 后 in-view 回调不再重启），编辑器序列化净化再兜底移除一次。

骨架 v3–v5 的运行时状态（供编辑器净化参考，全部必须归位）：

| 运行时产物 | 净化方式 |
|---|---|
| `<html>` 的 `js` class、`texture-cover` class（质感范围，v3 骨架；v4 起背景配给为纯 CSS、无此运行时 class） | 移除 `<html>` 的整个 class 属性 |
| `[data-anim]` 元素内联 style 的 `--i` 序号（含 mask-lines 的 `.ml-inner`） | 移除 `--i` 属性值 |
| pointer tracker 写入的 CSS 变量（v5）：`.slide` 上的 `--mx`/`--my`/`--mxr`/`--myr`，tilt/magnetic 元素上的 `--rx`/`--ry`/`--mgx`/`--mgy` | 移除这些自定义属性（`--pdepth`/`--depth`/`--val`/`--flow-path`/`--pin-i` 等是生成侧产物内容，【禁止】移除） |
| scroll 族 JS 驱动写入的 `--sp` 进度变量（v5，在含 scroll 族元素的 `.slide` 上） | 移除该自定义属性 |
| `.in-view` class、`<html>` 的 `--slide-scale` | 移除（既有规则） |
| 拆字 span（`.sp-unit`，含 `split-anim` class） | 还原为 `textContent` 纯文本节点 |
| `data-anim="count-up"` / `typewriter` / `scramble` 元素的进行中文本、`tw-live` 光标 class | 还原为终值文本（调用 `__pptxMotion.restoreAll()`），移除 `tw-live` |
| `data-anim="draw-line"` 元素内联 style 的 `stroke-dasharray` / `stroke-dashoffset` | 移除这两个 style 属性 |
| `canvas[data-fx]` 的 `width` / `height` 属性（v6.1，fx 运行时 DPR 修正） | 移除这两个属性（freeze 主责，序列化兜底；canvas 像素不属 DOM 状态） |
| `[data-rotate-item]` 的 `.active` class（v6.3，轮转运行时） | 移除（freeze 主责，序列化兜底） |

无 JS / `prefers-reduced-motion` 环境下产物天然完整可读（文件里本来就是纯文本与完整图形），不需要任何降级代码。

## 图表元素的分层（契约级）
静态文件里"改数字、图形跟着变"做不到（无运行时）。因此图表按层划分编辑权：

| 层 | 元素 | 编辑权 |
|---|---|---|
| 几何层 | SVG 图形、柱/条/扇区、装饰网格线 | `data-editable-skip`，编辑器忽略 |
| 标签层 | 图例标签、轴标签、类目名 | `data-editable`，可就地改 |
| 数值层 | 与几何绑定的数值（柱高对应的数字、百分比） | 标注为可编辑但**改数值不改几何**——生成侧在交付说明中提示"改数走批注/AI 流程"；编辑器侧不特殊处理 |

生成侧义务：SVG/画布几何必须整体 `data-editable-skip`；图表的可读文字尽量放在 SVG 外的 HTML（text_policy: none 原则）。

## 信息图组件的分层（契约级，v4 新增）

信息图 = 结构族 × Item 皮肤（生成侧配方见 components.md v2）。与图表同理——静态 HTML 不做"改文字重排布局"的承诺，按层划分编辑权：

| 层 | 元素 | 编辑权 |
|---|---|---|
| Item 文字层 | 数据单元的 label / desc / value | `data-editable`，就地可改 |
| 结构装饰层 | 连线、箭头、节点圆点、骨架几何、背景形 | `data-editable-skip`，编辑器忽略 |
| 风格化层 | 参与主题 stylize 的图形（`data-stylize`） | 纯装饰语义，必须同时标 `data-editable-skip` |
| 结构层 | 增删 Item、换结构族/骨架、改数据字段形态 | 编辑器不支持，走 AI 流程（生成侧在交付说明中提示，与图表数值分层同理） |

补充条款：

1. **标注修饰件**（引线标注、角标、数值旗标）是文字元素、不进几何：标注文字 `data-editable`，引线/箭杆 `data-editable-skip`；
2. **嵌套**（Item 内嵌 chart 族小图）按各层自己的规则标记——外层按本节、内层按"图表元素的分层"，嵌套不改变分层语义；
3. Item 容器与结构骨架容器（grid/flex 包装）不标 `data-editable`，沿用"标记在最小语义容器上"规则；
4. **辅助标记（生成侧自检用，编辑器原样保留）**：信息图根元素标 `data-ig="<族>-<骨架>"`（如 `list-zigzag`、`compare-binary-cols`）与 `data-ig-skin="<皮肤>"`，每个数据单元标 `data-ig-item`——用于静态校验项数区间与族×皮肤白名单（components.md §0.3）。编辑器不消费这些标记，序列化保存时不得增删。

## 图片槽位契约（契约级，v5 新增）

图片从"只有 `data-editable-image` 标记"升级为槽位契约——占位图规格从文字纪律变成机器可验的绑定关系：

```html
<img data-editable-image
     data-image-slot="cover-hero-21x9"
     data-image-intent="团队协作的抽象场景，暖色调，俯视"
     data-image-state="placeholder"
     src="assets/cover-hero.svg" alt="…">
```

1. **三属性语义**：
   - `data-image-slot`：语义名 + 宽高比，格式 `<kebab-case 语义名>-<宽>x<高>`（如 `cover-hero-21x9`）；
   - `data-image-intent`：内容意图一句话。占位图阶段是生成占位图形的依据，插画 pass 阶段是生图提示词的槽位部分，用户换图时是换图指南；
   - `data-image-state`：图像供给状态机 `placeholder` → `generated` → `uploaded`，是反降级校验的依据（规格 §4）。
2. **三方绑定【硬规则】**：槽位声明比例 ↔ 容器/img 构图宽高比 ↔ 生图比例，三者必须一致，静态可验（容差 5%）。槽位决定构图尺寸，构图尺寸决定生图比例——不为插画改构图。
2b. **分辨率下限【生成侧硬规则；`uploaded` 素材豁免】**（imagegen v2 G7，校验器静态执行）：页面级槽位（`page-baked-*`）栅格素材 ≥ 2560×1440（与烙入 Canvas 节 / adapter `--expected-size` 对齐）；页内槽位栅格素材短边 ≥ 640px（槽位声明是比例语义，容器像素尺寸无法可靠静态推算，取保守下限）；SVG 矢量豁免。**适用范围**：`placeholder`（待生成）与 `generated`（已生成/烙入）不达标 = **错误**（生成侧无合法偏离）；`uploaded`（用户真实素材）不达标 = **告警**——本契约第 3 条要求真实素材"原样落盘、不重画不压缩"，把它放大到下限才算通过等于伪造来源。
3. **生成侧义务**：
   - 新产物的全部图位必须带完整三属性（占位图阶段 `state="placeholder"`）；
   - pptx 转换入口提取的原图原样落盘 `assets/`，按画面角色补 `data-image-slot` 与 `data-image-intent`，并置 `data-image-state="uploaded"`（用户提供的真图，视同上传）。
4. **编辑器义务**：上传替换只换 `src` 指向的文件并置 `data-image-state="uploaded"`，保留 slot / intent 属性（契约不随换图丢失）。用户上传永远是终态——上传的图不会被后续 AI 操作覆盖。
5. **存量兼容**：无槽位三属性的老 deck，编辑器不强制要求（缺失时上传仍可用，置 `state="uploaded"` 即可）；静态校验器（`scripts/check-images.mjs`）对无槽位 img 给出**警告**而非报错。
6. **反降级【硬规则】**：声明 AI 插画模式的 deck，产物中不允许残留 `placeholder` 状态的槽位（校验器 `--mode illustration` 下报错）；生成失败的槽位诚实回退——保持 `placeholder` 状态与占位图，并在交付说明中逐条列出。回退不是失败，冒充才是：禁止用 CSS 渐变或占位图冒充插画。

## 样式覆盖（契约级，v2 新增）

编辑器（v1.6 起）允许用户对 `data-editable` **文字元素**做元素级样式微调，样式写为该元素的 inline `style`：

1. **白名单四属性**：编辑器只允许写 `font-family` / `font-size` / `color` / `text-align` 四个 inline 属性，不新增其它 style 属性；样式粒度是整个 `data-editable` 元素，不做选区级富文本。
2. **生成侧不得无故清除**：AI 落码修改该元素内容（改文字、调结构）时，必须**保留**用户已有的白名单 inline 样式——样式选择与内容修改正交。
3. **整体改版可重置**：AI 整体改版（换主题 / 换构图）时可以重置这些 inline 样式，但必须在交付说明中显式声明"已重置用户自定义样式"。

编辑器写主题相关值时优先写 token 引用（如 `color:var(--accent)`、`font-family:var(--font-display)`），使后续换主题时用户样式仍跟随主题。

## 章节跳转与 v7 动效（契约级，v6.3 新增，skeleton v7）

1. **章节跳转标记是产物内容**：章节页 `.slide` 上的 `data-chapter="章节名"` 与 `id`（与 `data-slide-id` 同值）、目录链接 `<a class="nav-link" href="#id">` 全部原样保留，编辑器不消费。链接文字照常 `data-editable`。
2. **编辑器义务**：编辑态拦截 `.nav-link` 的点击跳转（preventDefault）——用户点击目录文字是为了编辑，不是为了跳转；预览态滚动跳转无害。
3. **mend-bar（双态修复条）**：`--from`/`--val` 是产物内容（同 fill-bar `--val` 口径，净化【禁止】移除）；动画由 `.in-view` 纯 CSS 触发，无运行时残留。
4. **data-rotate（轮转高亮）**：`.active` class 是运行时状态——`__pptxMotion.freeze()` 摘除轮转并清空 `.active`；序列化净化兜底移除（与 `.in-view` 同口径）。

## 主题 CSS 块与母题件（契约级，v6.2 新增，skeleton v6）

1. **主题 CSS 块**：骨架 `SLOT: theme css`（框架层之后的 `<style>` 区段，承载主题 G9 装饰母题与缓动签名）是产物的一部分——编辑器不消费、不修改；序列化只动 body DOM，`<style>` 区天然原样保留。
2. **母题件**：主题母题类（`.mt-*`）的纯装饰件一律 `data-editable-skip`。**文本载体类母题**（如 `.mt-pub-dropcap` 首字下沉、`.mt-pub-pull` 引文拉页）加在真实文本上——样式由类承担，文本保持 `data-editable` 就地可编辑，编辑/保存不改变类归属。
3. **缓动签名**：主题块内 `:root{}` 的 token 重定义（如 `--ease-out`）是主题产物内容，与 `--val`/`--pdepth` 同口径——序列化净化【禁止】移除。

## 页面烙入模式（契约级，v7 新增，skeleton v7.3）

烙入页 = 一张整页生图 + **完整保留的 HTML 源层**：

```html
<section class="slide" data-slide-id="cover" data-render-mode="baked" data-content-hash="…">
  <img data-editable-image
       data-image-slot="page-baked-16x9"
       data-image-intent="（人可读的换图指南一句话）"
       data-image-state="generated"
       src="assets/page-cover.png" alt="…"
       style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">
  <div class="baked-source" hidden>
    <!-- 原 HTML 页面内容完整保留：标题、正文、组件、契约标记原样不动 -->
  </div>
</section>
```

1. **`data-render-mode`**：`"html"`（缺省，可不写）/ `"baked"`。标在 `<section class="slide">` 上，是产物内容，参与 content-hash（canonical string 第 2 行）。
2. **`.baked-source` 源层规约**：
   - 源层是烙入页的真相锚——原页面 HTML（含全部 `data-editable` 文字与组件标记）原样收进 `<div class="baked-source" hidden>`，作为 section 的直接子元素放在整页 img 之后；
   - 骨架运行时（拆字/打字机/count-up 等文本引擎、动效初始化、in-view 驱动）**跳过 `.baked-source` 内部**（skeleton v7.3 起）；
   - 编辑器可编辑扫描（注册表、两段手势、样式编辑、批注框选候选）同样**跳过 `.baked-source` 内部**——烙入页的文字不可就地编辑；源层编辑走编辑器专用"源层编辑"入口）；
   - 源层【禁止】标 `data-editable-skip`——它不是装饰件，skip 语义会让它从 manifest/hash 的语义树中消失；
   - 序列化保存时源层**原样保留**（净化规则与页面其他部分同口径，无新增条目）；
   - 源层**参与 content-hash**：canonical string 的 `querySelectorAll` 天然包含 hidden 子树，编辑源层即翻转 hash——stale 检测对烙入页与 HTML 页同一机制。
3. **页面级槽位 `page-baked-16x9`**：烙入页的整页 img 沿用"图片槽位契约"三属性与三方绑定——槽位声明比例 16:9 ↔ 画布 1920×1080（页面级槽位的构图框即整个画布）↔ 生图 2560×1440，容差 5%；img 必须是 `section.slide` 的直接子元素并满幅铺放（inline style 见上）。`data-image-intent` 写**人可读的换图指南**（同插画槽位语义），生图指令全文不入属性（指令是编译产物，存 `prompts/` 工作区）。换图走编辑器既有图片替换流（上传置 `uploaded`，用户真图永不被 AI 覆盖）。
4. **批注粒度**：烙入页批注 = **页级 + 坐标区域**——整页 img 在注册表内可框选，批注目标的 `excerpt` 为空（图里没有可引用的文本元素）。
5. **回退规约**：摘除整页 img 与 `data-render-mode`、解除 `.baked-source` 的 `hidden`，即完整回退为普通 HTML 页——回退必须是生成失败时的诚实出路（`data-render-mode` 保持 `html`，源层即页面本体），禁止交付残页。

## 图片入场动效（契约级，v8 新增，skeleton v7.5）

图片元素（页面级烙入整图 img 与页内 `data-editable-image` 槽位图）允许携带 enter 族入场动效，沿用既有 `data-anim` 标记体系，不发明新属性、新参数面：

1. **白名单四款**（名称以 skeleton enter 族现有 recipe 为准）：裸 `data-anim`（fade 语义：上浮 24px + 淡入）/ `rise-in`（rise：位移 64px 郑重入场）/ `scale-pop`（zoom-in：scale .86→1）/ `wipe-clip`（curtain：clip-path 左→右揭示）。其余 enter recipe（left/right/line/blur-in/persp-in）与一切 text / data / link / ptr / scroll 族 recipe【禁止】作用于 img——拆字类天然不适用，ptr/scroll 族的位移会与 enter 位移打架（transform 互斥规则不变）。
2. **每页至多 1 个图片入场动效**——图片入场是锚点级编排，计入 §1 注意力预算的主动效配额；插画槽位动效随所在页编排，不独立叠加延迟。
3. **烙入页整图时长 ≤0.8s**：整页大图动久了晕。页面级槽位（`page-baked-*`）img 的动效时长与延迟由骨架 v7.5 统一压到 ≤0.8s、零阶梯延迟（烧死在骨架，生成侧不可调）；选 wipe-clip（原 .9s）同样被压到 .8s。
4. **产物形态**：`data-anim` 是标记属性，序列化保存时原样保留；运行时状态只有骨架分配的 `--i` 阶梯序号，净化口径与既有 `[data-anim]` 条目完全相同（freeze/序列化移除 `--i`，标记属性保留），无新增净化条目。
5. **不参与 content-hash**：canonical string 的图片行只含 slot|intent|state|src——`data-anim` 不进 canonical（图片动效是纯演示态编排，改它不翻转 hash、不触发烙入 stale），`extract-manifest.py` 与 editor.html 两端 canonical 规则均不变。
6. **降级与导出**：`.js` 门槛保证无 JS / reduced-motion / 打印下图片直接完整可见（零降级代码）；PPTX 导出为静态终态（FREEZE_JS 滚动触发 + 打印 CSS / 可编辑轨注入样式强制 `[data-anim]` 终态），交付说明固定话术"图片动效为 HTML 演示态专属，PPTX 导出为静态终态"。

## 版本

契约 v8.2（2026-10-21，G7 适用范围裁决）：2b 的分辨率下限细化为**生成侧硬规则**——`placeholder` / `generated` 不达标仍是错误，`uploaded`（用户真实素材，契约要求原样落盘）降级为**告警**；`check-images.mjs` 按 `data-image-state` 分流，告警文案标注"uploaded 真实素材，按 G7 适用范围豁免"。动机：54 页真实材料基准 deck `cmb-retail` 的 12 张真图（含 58×58 图标）被旧口径一票否决，而放大真图等于伪造来源。
契约 v8.1（2026-10-06，imagegen v2 P2 G7）：图片槽位契约新增"分辨率下限"硬规则（2b）——页面级槽位栅格素材 ≥2560×1440、页内槽位栅格素材短边 ≥640px、SVG 豁免；`check-images.mjs` 两种模式同口径报错。bake-mix fixture 的 `page-ch-baked.png` 同步升级为 2560×1440。
契约 v8（2026-10-06，imagegen v2 P1 G4 / skeleton v7.5）：新增"图片入场动效"节——烙入整图与插画槽位 img 允许携带 enter 族动效标记（白名单：裸 data-anim / rise-in / scale-pop / wipe-clip），禁 text/ptr/scroll 族作用于 img；每页至多 1 个图片入场动效；烙入整图时长 ≤0.8s（骨架 v7.5 烧死）；data-anim 为标记属性原样保留、--i 净化口径不变；data-anim 不进 canonical string（两端 hash 规则不变）。
契约 v7（2026-09-21，三形态 M2 / skeleton v7.3）：新增"页面烙入模式"节——`data-render-mode="html|baked"`（缺省 html，进 canonical string 第 2 行）、`.baked-source` 源层规约（骨架运行时与编辑器扫描跳过其内部、禁标 data-editable-skip、序列化原样保留、源层参与 content-hash）、页面级槽位 `page-baked-16x9`（三属性 + 三方绑定：16:9 ↔ 画布 1920×1080 ↔ 生图 2560×1440）、烙入页批注粒度=页级+坐标区域（excerpt 为空）、回退规约。
契约 v6.4（2026-09-20，K 期深化 / skeleton v7.1）：文字效果词汇 `.tt-*`（outline/strike/mark/uline）是静态 CSS 类——文字保持纯文本可编辑；`.tt-outline` 描边字（color:transparent）编辑态还原本色（编辑器注入样式强制还原本色 + 去描边，随净化剔除，同 gradient-flow 条款口径）；无运行时状态，净化无新增。
契约 v6.3（2026-09-20，K 期 / skeleton v7）：新增"章节跳转与 v7 动效"节——data-chapter/nav-link/id 为产物内容、编辑态拦截 nav-link 点击、mend-bar 的 --from/--val 为产物内容、data-rotate 的 .active 为运行时状态净化移除。
契约 v6.2（2026-09-19，G 期 / skeleton v6）：新增"主题 CSS 块与母题件"节——`SLOT: theme css` 原样保留、`.mt-*` 母题件 skip、文本载体类母题的文本保持可编辑、主题块 `:root{}` token 重定义不得净化。
契约 v6.1（2026-09-19，迭代 F5 / skeleton v5.1）：canvas FX 仪式层净化条款——`canvas[data-fx]` 产物中为空元素（无 width/height、无内容、一律 data-editable-skip）；运行时 width/height（DPR 修正）由 `__pptxMotion.freeze()` 摘除、序列化净化兜底；首次入视口才初始化，从未入视口零残留。契约 v6（2026-09-19，迭代 F4 / visual-depth.md §三）："动效与编辑"节扩展 skeleton v5 新族——typewriter/scramble 纳入运行时化条款；mask-lines 分行结构归属产物（.ml-inner 是 data-editable 叶子，其 --i 为运行时）；gradient-flow 透明填充类效果的编辑态强制还原本色规则；pointer tracker CSS 变量（--mx/--my/--mxr/--myr/--rx/--ry/--mgx/--mgy）与 scroll 族 --sp 进度变量列入净化清单；新增 __pptxMotion.freeze() 编辑态冻结交互层约定。
契约 v5（2026-09-18，迭代 E / illustration-pipeline.md）：新增"图片槽位契约"节——`data-editable-image` 图位必携 `data-image-slot`（语义名+宽高比）/ `data-image-intent`（内容意图）/ `data-image-state`（placeholder→generated→uploaded 状态机）三属性；槽位比例 ↔ 构图尺寸 ↔ 生图比例三方绑定（容差 5%）；编辑器上传置换置 `uploaded` 并保留 slot/intent；pptx 转换原图补 slot/intent 且置 `uploaded`；存量无槽位 deck 兼容（校验器警告不报错）；插画模式反降级（禁 placeholder 残留，失败诚实回退）。
契约 v4（2026-09-18，迭代 D / infographic-system.md）：新增"信息图组件的分层"节——Item 文字 `data-editable`、结构装饰 skip、`data-stylize` 图形必伴 skip、结构变更走 AI 流程、标注修饰件文字 editable；引入生成侧辅助标记 `data-ig` / `data-ig-skin` / `data-ig-item`（编辑器原样保留）。
契约 v3（2026-09-18，迭代 C / motion-system.md）："拆字禁令"修订为"文本破坏性动效必须运行时化"；净化清单新增拆字 span 还原、count-up 终值还原、draw-line 描边 style 归位、`<html>` 运行时 class 整体移除（含 `texture-cover`）。
契约 v2（2026-09-18）：新增"样式覆盖"节（编辑器 v1.6 样式编辑）。
契约 v1（2026-09）。任何一侧修改标记语义前，必须同步修改本文件并告知另一侧。
