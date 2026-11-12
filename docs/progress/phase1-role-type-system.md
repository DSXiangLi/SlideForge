# Phase 1 · 角色化字号系统（设计层规避，不靠后门禁）

> 日期：2026-11-11
> 目标：解决"字号设置/布局/换行在部分主题下不合理"的根因——内容文字既可被生成侧（skeleton 示例页）裸写 `font-size`，又可由编辑侧（editing-contract 白名单）内联 `font-size`，而 `typography.md` §2 的下限只是软指引。
> 决策（用户拍板）：**从主题设计上直接规避问题，不加入后拦截/门禁**。改用"角色令牌系统"——文字只选角色（`.t-*`），字号由令牌 + `max()` 下限结构性锁定，主题令牌无法突破下限。

---

## Step 1a · skeleton.html 注入 `.t-*` 角色类 + 不可破下限

文件：`skills/SlideForge/assets/skeleton.html`（v7.6，1920×1080 画布基准）

在 `:root` 与 `SLOT: fonts` 之间新增：

```css
:root{
  --t-display:96px; --t-heading:64px; --t-subhead:40px; --t-body:28px;
  --t-caption:18px; --t-meta:15px; --t-vertical:96px;
}
.t-display{font-size:max(var(--t-display),64px);line-height:1.15}
.t-heading{font-size:max(var(--t-heading),32px);line-height:1.25}
.t-subhead{font-size:max(var(--t-subhead),24px);line-height:1.3}
.t-body{font-size:max(var(--t-body),18px);line-height:1.6}
.t-caption{font-size:max(var(--t-caption),16px);line-height:1.5}
.t-meta{font-size:max(var(--t-meta),14px);line-height:1.4}
.t-vertical{font-size:max(var(--t-vertical),64px);line-height:1.12;writing-mode:vertical-rl}
```

要点：
- 每个 `.t-*` 用 `max(var(--t-*), <下限>)` 双保险。下限（display≥64 / heading≥32 / subhead≥24 / body≥18 / caption≥16 / meta≥14 / vertical≥64 px@1920）由 `max()` 锁定，**主题令牌再小也突破不了**——这就是"设计层规避"。
- 三张示例页（封面 `<h1>`、内容 `<h2>`/`<p>`）已从裸 `font-size` 改为 `.t-display` / `.t-heading` / `.t-body`，仅保留 `font-family` / `line-height` / `margin` 等非字号内联样式。
- 与 `check-capacity.py`（文本是否溢出容器）正交：容量是生成后测量，字号下限是生成前锁定，两者都不靠"后拦截改字号"。

---

## Step 1b · 4 个主题 theme.md 的 `type_scale` 改写为 px@1920 令牌源 + G9 `:root` 注入

文件（4 个）：
- `references/themes/line/b1/theme.md`
- `references/themes/type/c3/theme.md`
- `references/themes/space/e5/theme.md`
- `references/themes/texture/h1/theme.md`

### 改写规则
1. `type_scale` 从「cqw@480 三级层级」改写为「px@1920 角色令牌源」，注释注明每档来源与下限关系。
2. 在 G9 `:root` 注入该主题差异化的 `--t-*`（B1/H1 追加到已有 `:root`；C3 新增 `:root`；E5 追加到已有 `:root`）。
3. 未覆盖的角色（heading / subhead / caption / meta）继承骨架默认（64 / 40 / 18 / 15px），文档中显式注明。

### 终值表（px@1920，画布坐标系）

| 主题 | `--t-display` | `--t-heading` | `--t-body` | `--t-vertical` | 说明 |
|---|---|---|---|---|---|
| B1 瑞士 | 176 | 继承 64 | 35 | — | 倒挂巨字封面；display 略超 §1 上限契合海报传统 |
| C3 终端 | 104 | 继承 64 | 35 | — | 终端"巨字"封面（$ 提示符+等宽标题）；扁平层级靠明暗 |
| E5 构成 | 128 | 继承 64 | 35 | — | 极粗 800–900 承载"巨字宣言"压强 |
| H1 手卷 | 92 | 继承 64 | 35 | 118 | 横向题跋数字 92；竖排主标题 118 为签名形态（>横向 display） |

> 全部覆盖值均 ≥ 各自下限（display≥64 / body≥18 / vertical≥64），`max()` 无需兜底。

### 换算口径（重要，防误读）
- **body 35px** = 主题原 `body:1.8cqw@480` 按 `1cqw@1920 = 19.2px` 换算（1.8 × 19.2 ≈ 35）。这是唯一忠实换算的档。
- **display 不按 cqw 盲换算**：主题原 `display:2.6–3.0cqw` 若按 ×19.2 仅得 50–58px，落在 64px 下限以下、且远低于 `typography.md` §1 封面标题 120–160px 的硬指引——说明原 cqw `display` 是"次级展示层"而非封面英雄。故 display 改以 §1 封面指引为锚、按主题性格定档（B1 最大、C3 最克制的扁平、E5 极粗、H1 让位给竖排）。
- **heading 不覆盖**：保留骨架 64px，使"标题:正文"对比 ≥1.8:1，优于原 cqw 换算的 1.2:1 扁平层级。

---

## Step 1c · 生成/编辑侧"禁止裸 font-size"硬规则

- `references/typography.md`：新增 **§8 角色令牌系统（.t-*）**，明确"内容文字只选角色不选像素"、`.t-*` 的 `max()` 双保险、主题只在 G9 `:root` 覆盖 `--t-*`、生成侧模板/脚本与编辑侧白名单都**禁止内联 `font-size`**、文字效果走 `.tt-*` 与字号角色正交。
- `skills/SlideForge/SKILL.md`：Step 4「逐页生成」在"中文排版"bullet 后新增【硬规则】bullet，把上述约束写进生成流程；并指向 `typography.md` §8。

---

## 验证与遗留

- 已用 grep 核对 4 主题 `:root` 与 `type_scale` 数值一致、均 ≥ 下限。
- 仍未触碰：`check-capacity.py`（保留，正交于字号下限）；其余 20+ 主题未改（本次仅 B1/C3/E5/H1 四个试点主题，与其历史字号问题一致）。
- **Phase 2（编辑器侧）待做**：`editing-contract.md` 白名单把 `font-size` 换成"切换 `.t-*` 角色类"；`editor.html` 字号输入从 px 数字框改为"巨/大/中/小/注 → `.t-*`"下拉。详见 `phase2-editor-role-ui.md`。
