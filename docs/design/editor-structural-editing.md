# 编辑器结构编辑（M1'–M2'）设计：Undo 地基 + 删除优先

> 日期：2026-10-13。依据：`../research/editor-structural-editing.md`（技术调研 + §7 需求反思）。
> 状态：待评审。实施前须先落 `editing-contract.md` v8.2（项目纪律：契约不后补）。

## 1. 定位与哲学

编辑器的用户哲学一句话：**AI 负责构图，人负责删减、纠错和替换**。

本期不做"自由排版"（拖动/resize/新增文本框/z-index），那是 PowerPoint 的手工画布心智，与本产品"系统性栅格生成物 + 批注→AI 落码"的结构修改通道冲突。本期只做反思后确认的真需求：

| 优先级 | 需求 | 理由 |
|---|---|---|
| P0（M1'' 先行） | 页级删除 / 复制 / 隐藏 + 页范围 undo | 做 deck 最高频的结构操作是页级的；成本趋零、价值占大头 |
| P1（M2'' 按需） | 块级删除（内容块整体，含守卫）+ 通用 undo | AI 生成物必然冗余，"减"天然安全；但是成本大头，以 M1'' 真实反馈决定是否启动 |
| P1（M2'' 附属） | 图片重置为占位 | 换图的逆操作，槽位状态机语义自洽 |
| 后续 | 微调 nudge + 吸附 + 几何 lint（M3'） | 触发点明确但频率低于删除，本文档只定方向 |

## 2. 非目标（明确不做）

- 色块作为独立操作对象（操作对象一律是"内容块 = 容器+内容整体"）
- 流式元素自由拖动 / 脱流转换（塌缩风险 + 与 AI 通道竞争）
- resize 手柄、z-index 调整、复制块、新增文本框（构图工具，导流到批注/脑暴）
- 信息图 Item 增删、mask-lines 行增删（维持契约红线，走 AI 流程）
- Bridge / 嵌入协议 / `tools/` 任何改动（§8 论证为零改动）

## 3. 概念模型：块（block）与可删除单元

### 3.1 块解析规则 `blockUnit(el)`

从用户点中的叶子（`[data-editable]` / `[data-editable-image]`）向上爬，停在最近满足条件的祖先：

1. `[data-block]`（契约 v8.2 新增的可选标记，生成侧逐步回刷）——最优先
2. 启发式容器：computed style 有非透明背景色 / 非 0 边框 / 非 0 圆角，且不是 `section.slide` / `.slide-slot` / `.deck` / `body` / `.masthead` / `.mastfoot`（与 `check-capacity.py` 的 isContainer 同一套判定，编辑器侧 JS 重写）
3. 都不是 → 叶子本身即为块

### 3.2 删除守卫清单（命中即禁删，toast 说明原因）

- `section.slide`、`.slide-slot`、`.deck`、`body`、`.masthead`、`.mastfoot`、`.baked-source` 及其内部一切（烙入页只能在源层编辑态内删，且删的是源叶子）
- `canvas[data-fx]`、`a.nav-link`（删了断章节跳转）、带 `id` 的章节锚元素
- `[data-render-mode="baked"]` 页的整页图（`page-baked-16x9` 槽位）
- `[data-ig]` 信息图根；`[data-ig-item]` 删除后将违反族项数断言（compare 必须 2/4 等，沿用 components.md 各族断言表）——提示"信息图项数受结构族约束，请用批注让 AI 调整"
- 删除后页内 `[data-editable]` 归零：不禁止，但二次确认"该页将变为纯装饰页"
- 块内同时含可删与禁删内容（如卡片里包了 nav-link）：禁删，提示用户改删子块

### 3.3 删除交互：预览 → 执行 → 撤销，不弹确认框

1. 选中元素后（现有两段手势的第一段已提供选中态），顶栏出现「删除块」按钮 + `Delete`/`Backspace` 快捷键可用
2. **预览只走一条路径：悬停顶栏「删除块」按钮**时，目标块（`blockUnit` 解析结果）显示红色虚线轮廓（注入 class `ed-block-target`，`data-editor-injected` 体系）——用户在删除前看到"将要删掉的是哪一块"，启发式误判的成本降为"看得见就不点"
3. 执行：点击按钮或按 `Delete`/`Backspace` 立即删除，右下角 toast"已删除 ××，Ctrl+Z 撤销"（5 秒，父页 DOM）
4. **快捷键路由红线**：`Delete`/`Backspace` 仅在 `selEl` 非空、`editEl` 为空、且焦点不在任何 input/textarea/contenteditable 内时才触发块删除——编辑进行中按 Delete 是删字符，绝不升级为删块（现有键盘路由 `:4165` 附近扩展，统一做焦点守卫）
5. 仅两种情况弹确认：页级删除（影响整页）、§3.2 的"归零"警告

## 4. F1：Undo/Redo 命令栈

### 4.1 命令模型

```js
{type, pageId, before, after, note}
```

**载荷策略分两类（审核修正：放弃路径恢复，结构操作用页级快照）**：

- **结构类命令**（`block-delete` / `page-delete` / `page-duplicate` / `page-hide`）：`before`/`after` = 受影响 `.slide-slot` 的**完整 outerHTML 快照**，undo/redo = 整体替换该 slot（page-delete 的 undo = 按记录的相邻 slot-id 插回；仅剩一页时退化为 append）。选快照而非"父路径 + 前驱路径"的理由：child-index 路径在兄弟增删后漂移，路径恢复必须依赖隐式 LIFO 不变式才不踩空；快照恢复与 DOM 其余部分的状态完全解耦，实现更短、无漂移面。代价是内存——单页 outerHTML 约 50–200KB，栈容量据此定为 **50 条**（上限约 10MB，可接受）
- **值类命令**（`text` / `style` / `image-reset` / `image-replace`）：`before`/`after` = 元素级前后值（innerHTML / 四属性 inline / src+state），目标用 slide-id + child-index 路径寻址（复用批注体系 `:3968`/`:4272`）——值类操作不改结构，路径在 LIFO 纪律下稳定

| type | before / after | 说明 |
|---|---|---|
| `text` | 元素 innerHTML 前后值 | 接入现有 `commitEdit()`（`:4077`），统一 Ctrl+Z 体验 |
| `style` | 四属性 inline 前后值 | 接入 `applyStyleProp()`（`:5730`） |
| `block-delete` | 页 slot outerHTML 快照 | 结构类 |
| `page-delete` / `page-duplicate` | 页 slot 快照 + 相邻 slot-id / 副本 slot-id | 结构类 |
| `page-hide` | 页 slot 快照 | 结构类（属性开关也走快照，省一条特判路径） |
| `image-reset` | `src` + `data-image-state` 前后值 | 不回滚资产文件字节（见 §12.5 边界声明） |
| `image-replace` | `src` + state 前后值 | 同上，仅回滚引用 |

- **严格 LIFO**：只允许从栈顶撤销/重做，不提供乱序撤销；任何新操作清空 redo 分支
- `saveDeck()` 成功后记 `savedCmdIndex`，undo/redo 越过该点时对 `dirty` 做精确往返（undo 回到保存点 = 置干净）
- 恢复快照后统一清洗 `EDIT_CLASSES`（`:3643`）+ 重建 `registry`/`buildToc()`，防止 `ed-selected` 等陈旧 class 被 outerHTML 带回、选中状态指向已不存在的节点

### 4.2 与 contenteditable 原生撤销的边界

- 编辑进行中（`editEl` 非空）：Ctrl+Z 归浏览器原生栈，编辑器不拦截
- 失焦/提交后：该次文本变更已固化为一条 `text` 命令，Ctrl+Z 走编辑器命令栈
- 焦点在任何 input/textarea/contenteditable 内时，编辑器全局快捷键一律不生效（现有键盘路由已有类似判断，扩展即可）

## 5. F2：页级三操作（目录侧栏扩展）

侧栏卡片悬停操作条（⋮ 菜单，纯父页 DOM）+ 快捷键：

1. **删除页**：仅剩 1 页时禁删；弹确认（列出页标题）；undo 可恢复。删除已烙入页不额外警告（整页移除语义清晰）
2. **复制页**：深拷贝 `.slide-slot` insertAfter 原页；`data-slide-id` 去重（`-copy`、`-copy-2` 递增）；副本内章节锚 `id` 同步加后缀防撞；`data-chapter` 保留（目录多一章，语义诚实）；`data-content-hash` 交由保存时既有逐页重算逻辑（`:4783-4792`）处理。复制含烙入页 = 连烙入图一起复制（引用同一 assets 文件，不复制资产）
3. **隐藏页**：`.slide-slot` 置 `data-slide-hidden="true"`；骨架 v7.7 新增一行 CSS：`.slide-slot[data-slide-hidden]{display:none}`；TOC 卡片半透明 + 眼睛图标再点恢复；隐藏 `[data-chapter]` 页时 toast 警告"目录跳转将跳过该章"。页码总数不变（与 PPT 隐藏页保留页码一致）。**隐藏页从 `requestIllustrate()` 的 placeholder 扫描（`:7187`）中排除**——隐藏 = 不交付，不为它花生图额度

三个操作全部置脏、全部入 undo 栈、全部复用现有 `buildToc()` 重建。

## 6. F4：图片重置为占位

- 契约 v8.2 新增 `data-image-prev-src`：`replaceImage()`（`:4583-4649`）两条路径上传成功时写入原 src，声明为"编辑器写入的溯源属性，生成侧原样保留"
- 「重置为占位」操作（图片选中态顶栏按钮）：
  - `data-image-state` → `placeholder`（生图入口 `:7187` 的扫描逻辑自动重新纳入，下轮插画 pass 会重新生图——这正是重置的意图）
  - `prev-src` 存在且 ≠ 当前 src → `src` 恢复并 `?v=` 热刷新；不存在（存量 deck / 同名覆盖）→ 仅翻 state，toast 说明"原占位图不可恢复，将在下次插画补齐时重新生成"
- 契约 v8.2 同步修订："uploaded 是终态永不被 AI 覆盖"条款补充豁免——**用户显式重置**不受此限（AI 仍不得主动覆盖）

## 7. 契约 v8.2 修订点（完整清单，先改契约再实施）

1. 新增可选块标记 `data-block`（§3.1）：生成侧对新 deck 的容器型元素标注；存量 deck 无标记时编辑器走启发式回落，不强制回刷（回刷作为独立 backlog 项）
2. 新增删除守卫清单（§3.2 全文入契约）
3. 新增 `data-slide-hidden` 页属性：语义、骨架 CSS 配合、导出侧行为（§8.3）
4. 新增 `data-image-prev-src` 溯源属性 + uploaded 终态的显式重置豁免
5. **canonical 规则零改动**——`data-slide-hidden`、`data-image-prev-src`、块删除前后的几何变化均不进 canonical；删除/复制页通过现有 T:/I: 行自然反映。`extract-manifest.py` 的 CANONICAL_JS **不需要动**，双端同步红线本轮不触发（评审时重点确认本条）

## 8. 系统影响面论证

### 8.1 保存/序列化：零改动

全部新操作都是产物 DOM 改动，走现有 `serializeClean()` → 五通道路径。新增 UI（toast、确认框、TOC 操作条、块轮廓）全部父页 DOM 或 `data-editor-injected` 注入，净化清单天然剔除。T1 往返幂等基线不受影响（无操作打开→保存仍零 diff）。undo 栈只在父页内存，不进序列化。

### 8.2 Bridge / 嵌入协议：零改动

payload 仍是完整 HTML；无新消息类型（M3' 的几何 lint 警告透出是可选项，届时单评）。

### 8.3 生成侧/导出侧：两处小改动，随 M2' 同批

- 骨架 v7.7：`.slide-slot[data-slide-hidden]{display:none}` 一行（存量 deck 无此属性，向后兼容；`--i` 阶梯分配与入场观察器天然跳过 display:none 子树，需实测确认）
- `export-pptx.py` / `extract-manifest.py`：`data-slide-hidden` 页默认跳过导出、manifest 标记 `hidden: true`（用户意图是"不交付此页"）；`check-render` / `check-capacity` 仍校验隐藏页（内容完整即合法，防止"藏一页烂的"）

## 9. 验收与测试

**成功标准（用户视角，可对照验证）**：① 任意非守卫块 3 次操作内（选中→预览→删除）可删且可 Ctrl+Z 恢复；② 删除/撤销/保存/再打开后内容与所见一致；③ 页级三操作在目录侧栏全部可发现、可撤销；④ 无操作打开→保存仍零 diff（现有 T1 基线不破）。

新增 harness 测试组（沿用 T2 真实手势 + T1 往返范式）：

- **T35 undo/redo**：删块→undo→redo→保存→重载断言内容一致；`savedCmdIndex` 的 dirty 精确往返；EDIT_CLASSES 不随快照泄漏；连续删 A、B 后乱序不变式（LIFO 恢复正确性）
- **T36 页级三操作**：删页（含最后一页禁删）、复制页（slide-id/id 唯一性、保存后 manifest 含新页）、隐藏页（序列化含属性 + 渲染断言不可见 + manifest `hidden:true` + 导出过滤的单元级断言）
- **T37 删除守卫**：禁删清单逐项命中（nav-link、page-baked、data-ig-item 计数、归零确认）；快捷键路由（编辑中 Delete 不触发块删除）
- **测试夹具必须覆盖真实密度**：`tests/decks/cmb-retail/`（54 页高密度真实内容）、`tests/decks/bake-mix/`（烙入页守卫）、gallery（信息图 `data-ig-item` 族断言）——不允许只用 4 页玩具夹具
- 回归红线：**完整 `run_e2e.py` 全量 PASS**（当前基线 60 项）+ T1 / T2 / T10 / o_tri_view 单独点名；删除翻 hash → stale 链路顺带覆盖
- 版本：editor.html → v3.8，契约 v8.2，骨架 v7.7；AGENTS.md 与 docs/design/README.md 同步

## 10. 分期与工作量（2026-10-13 再分期：页级包先行）

评审反馈确认：本方案核心价值是"删除"，而页级删除/复制/隐藏占了价值的大头、成本趋近于零——拆为独立先行期，块级删除按需启动。

| 里程碑 | 内容 | 预估 |
|---|---|---|
| **M1''（最小闭环，先做）** | 页级删除/复制/隐藏 + **页范围 undo**（每操作存一个 slot outerHTML 快照即可，不上通用命令栈）+ 骨架 v7.7 一行 CSS + 导出侧 hidden 支持 + T36 | 3–4 天 |
| **M2''（按需启动）** | 块级删除（块解析 + 守卫清单 + 悬停预览 + 归零确认）+ 通用 undo 命令栈扩展（接 text/style/结构操作 + savedCmdIndex）+ 契约 v8.2 + 图片重置占位 + T35/T37 | ~1.5 周 |
| M3' | 微调 nudge（absolute only）+ 吸附参考线 + 编辑器侧几何 lint | 另行评审，本文档不承诺 |

再分期依据：M1'' 的 undo 无需通用命令栈——页级操作只有四种，快照恢复与 DOM 状态解耦，几十行代码；契约 v8.2 中仅 `data-slide-hidden` 一项是 M1'' 的前置（可与骨架 v7.7 同批评审落地），`data-block`/守卫清单/`data-image-prev-src` 均随 M2''。M2'' 是否启动以 M1'' 上线后的真实使用反馈为准——若"页内删块"诉求没有实际出现，M2'' 可整体取消，方案收敛为纯页级。

## 11. M3' 方向预留（不展开）

- 方向键 nudge：选中块后 ←→↑↓ ±1px、Shift ±10px，仅作用于 absolute 定位块，写 inline `left/top`（白名单届时扩两属性）
- 吸附参考线：候选块边缘/中心 + 画布中线两两对齐，注入 SVG 线
- 几何 lint：check-render 核心数学（包围盒、重叠 16px²、越界 ±2px）JS 重写，移动结束跑当前页，警告不阻断
- 契约预留：白名单扩展条款草稿随 M3' 设计文档一并评审

## 12. 风险与开放问题

1. **启发式块解析误判**：靠悬停预览把成本降为"可见即可避"；`data-block` 回刷存量 deck（29 主题模板 + gallery 61 页 + cmb-retail 54 页 + theme-proving 64 页）列为独立 backlog，可用 check-capacity 启发式半自动标注
2. **删除后留空洞**：不自动重排（流式回流交给 CSS 自己处理，absolute 页留空洞是诚实的）；删除 toast 附带「让 AI 重排本页」快捷动作，复用批注通道预填指令——把善后导流到正确的通道
3. **复制页的 `--i` 动效阶梯**：副本页内文档序与原页一致，阶梯不变；删除页/块后同页阶梯次序变化，属已知行为（调研 §6.3），文档明示即可
4. **隐藏页与章节跳转**：nav-link 跳到 display:none 页时浏览器滚动行为需实测（预期：无可见位移），骨架 v7.7 落地时一并验证，必要时 nav 逻辑跳过隐藏页
5. **undo 与图片资产字节**：同名覆盖上传后 undo 只能回滚引用、回滚不了 assets 里的文件内容——Bridge 态可靠 git ref 历史找回，FSAA 态不可找回；toast 文案如实声明，不做隐式备份
6. **结构操作使既有批注失配**：批注用 child-index 路径寻址（`:4267`），删块/删页后兄弟索引漂移，已录制批注重载时退化为 changed/missing——三态兜底保证不崩，但用户应知情：删除 toast 在检测到本页存在批注时追加"本页已有批注，可能失配"；不做人肉重映射（成本高于收益，批注重录即可）
