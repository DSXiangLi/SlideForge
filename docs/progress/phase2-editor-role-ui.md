# Phase 2 · 编辑器侧：字号改为角色切换（与 Phase 1 同契约）

> 日期：2026-11-11
> 目标：把"设计层规避字号问题"从生成侧延伸到编辑侧——编辑器的字号控件不再允许裸写 `font-size`，改为切换骨架 `.t-*` 角色类。与 `typography.md` §8、`editing-contract.md` 白名单一致，无需后门禁。
> 风险等级：高（编辑器是 bridge 工作副本，改动面广）——故拆为 2a（契约）与 2b（代码）两步。

---

## Step 2a · editing-contract.md 白名单改写

文件：`skills/SlideForge/references/editing-contract.md` §样式覆盖（原 v2）

- 白名单由"四属性"改为"**三属性 + 角色切换**"：`font-family` / `color` / `text-align` 仍可写 inline style；**`font-size` 移出白名单**。
- 字号改由"切换 `.t-*` 角色类"实现：编辑器在元素上增删 `.t-display` / `.t-heading` / `.t-subhead` / `.t-body` / `.t-caption` / `.t-meta` / `.t-vertical`，同一元素至多一个字号角色。
- 生成侧义务（保留用户样式）与整体改版可重置义务同步更新：新增"保留/重置 `.t-*` 角色类"的措辞。
- 理由写明：字号下限（`max(令牌, 下限)`）由骨架结构性锁定，内联 `font-size` 既绕不过下限、又破坏主题令牌系统，故从白名单移除。

---

## Step 2b · editor.html 字号控件改为角色下拉

文件：`editor.html`（仓库根，bridge 编辑器工作副本）

### 改动清单
1. **Markup（顶栏 stylebar）**：原 `.st-size` 的 `− [number] ＋` 三段（px 数字框 + 步进按钮）替换为 `<select id="stRole">`，选项：默认 / 巨·封面(t-display) / 大·章节(t-heading) / 中·小节(t-subhead) / 正文(t-body) / 注·图注(t-caption) / 标·标签(t-meta) / 竖·竖排(t-vertical)。删除原 `stSizeWarn` 的"低于 18px"告警 span（下限已结构性保证，无需提示）。
2. **CSS**：`.st-size` 容器保留（圆角胶囊边框），内部 `.st-size button/input(.warn)` 规则改为 `.st-size select`（去边框、透明底、融入胶囊）。删除失效的 `.st-warn` 规则。
3. **JS · updateStyleBar**：不再读取 `computedStyle.fontSize` 写入数字框，改为扫描元素已挂的 `.t-*` 角色并令 `stRole.value = role`（无则"默认"）。
4. **JS · 字号写入**：删除 `applyFontSize` / `stepFontSize` 两个函数与 `stSize`/`stSizeDec`/`stSizeInc` 三个监听；新增 `applyRole(role)`——遍历 `ROLE_CLASSES` 用 `classList.toggle(c, c===role)` 切换，并 `el.style.removeProperty('font-size')` 把任何历史裸写 px 交回角色系统；新增 `$('stRole').change → applyRole`。保留 `stFont`/`stColor`/`stAlign` 监听不变。
5. **JS · 清理**：删除未再使用的 `var FONT_SIZE_MIN = 18` 常量。
6. **注释**：顶栏版本说明（v1.6 条 1）同步改写为"字号角色下拉切换 `.t-*`，其余三属性写白名单 inline style"。

### 验证
- grep 全文件已无 `stSize` / `stSizeDec` / `stSizeInc` / `stSizeWarn` / `applyFontSize` / `stepFontSize` / `FONT_SIZE_MIN` 残留引用。
- 余下 `font-size` 命中均为**编辑器自身 UI 样式**（顶栏/抽屉/弹窗等 chrome），与 deck 内容无关；deck 内容字号已完全由 `.t-*` 角色类承载。
- 角色切换与骨架 `.t-*` 定义（`skeleton.html` Step 1a）一一对应，编辑器只改 class 不改令牌，主题换肤时字号层级仍由 `theme.md` 的 G9 `:root` 令牌控制。

---

## 与 Phase 1 的闭环

| 侧 | Phase 1（生成侧） | Phase 2（编辑侧） |
|---|---|---|
| 字号来源 | 内容文字挂 `.t-*` 角色类，令牌 + `max()` 下限锁定 | 字号控件切换 `.t-*` 角色类，禁止内联 `font-size` |
| 主题分化 | `theme.md` G9 `:root` 覆盖 `--t-*` | 同左（编辑器不写 px，只切角色） |
| 下限保证 | 结构性（`max()`），不可破 | 结构性（编辑器根本写不进 px） |
| 门禁 | 不需要（`check-capacity.py` 仍只测"文本是否溢出容器"，与字号下限正交） | 不需要 |

**结论**：字号治理在生成侧与编辑侧都通过"角色令牌系统"结构性完成，未引入任何后拦截/门禁——符合用户"从设计上规避、不靠后端拦截"的拍板。
