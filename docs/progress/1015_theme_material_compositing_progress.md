# 1015 · 主题材料合成优化试点进度（D2 升级 + D4 新建）

> 前置：`docs/design/handover-theme-material-compositing.md`（试点任务定义）← `1015_theme_material_compositing_plan.md`（五阶段计划）← `docs/learnings/visual-material-compositing.md`（7 条原理）。
> 本文档 = 试点执行实录。验收跑分证据见 `docs/test_acceptance/`（如补）。

## 状态

- **Phase 0 材料合成词汇表：DONE**
- **任务 A（D2 柔光暗房材料升级）：DONE，用户已验收（2026-10-15）**
- **任务 B（D4 黄铜年代新建）：DONE，待用户验收**

## Phase 0 落地

- 新建 `skills/html-pptx/references/compositing.md`：15 个材料合成配方（overprint-flat / riso-misreg / halftone-dots / paper-fiber / emboss-deboss / watercolor-bleed / film-grain / light-leak / spotlight-mask / aged-fade / engraved-line / ink-bleed / torn-edge / reflection-fade / organic-stroke），每个含材料描述 + 可直接复制的 CSS 代码块 + 适用层 / 密度兼容 / 导出轨道 / 主题亲和。文件头载明使用纪律（色值只许 token、背景配给制、每页材料层 ≤2 配方叠加）。
- `sync-themes.mjs`：新增 G3 `css_recipes` 字段校验——配方名必须存在于 compositing.md（`## 配方 N：name` 标题解析），非法引用报错并列出合法配方；负向测试通过。

### 顺手修复的存量问题（HEAD 上 sync-themes 本来就不绿）

1. **主题数 28 vs 期望 29**：G3 陶土印刷在 587621b（主题本质重建）中被删除但 EXPECTED_COUNT 未同步 → 改为 28，注释载明由来。D4 入库时再 +1。
2. **主题外 hex ×3**：e1/e6/e4 theme.md 骨架硬规则表格把色值写进了散文（`#f7f2e6` / `#FFF8EE` / `#f4f0e4`）→ 改为 token 引用（`--paper`）。
3. **editor.html 残留 G3 主题卡**：G3 删除后未跑同步，THEMES_JSON 里一直有死卡片 → 本次同步清除（这是 editor.html diff 的主要来源）。

## 任务 A：D2 柔光暗房材料升级

**改动**（`references/themes/light/d2/theme.md`，配色/字体栈/页角色蓝图/分化声明/动效签名均未动）：

- G0 新增 `material_world`（摄影暗房一句话物理世界描述）+ `anti_lazy`（3 条主题级反惰性：禁星空宇宙/禁电影银幕边框/禁高亮度白光）。
- G3 升级材料规格：原三 token 不动，新增 `material`（胶片相纸——银盐乳剂面的微颗粒）/ `light`（安全灯单点光源，上方 70°）/ `css_recipes: ["film-grain","light-leak","aged-fade"]`。
- G9 新增 4 个母题类（CSS 经 sync 校验：无 hex、data-URI 内联、.mt-* 唯一）：`.mt-drk-grain`（细颗粒 feTurbulence 0.6，全页可铺）/ `.mt-drk-grain-lg`（粗颗粒 0.9，仪式页）/ `.mt-drk-leak`（琥珀漏光 blur40+screen，页缘裁切，仪式页每页至多 1 个）/ `.mt-drk-aged`（暖调 soft-light 罩 + ink-tint 暗角，仪式页）。词汇与禁忌条款同步扩写（颗粒 opacity ≤0.06、leak 与 beam 一页只许一个光源叙事等）。
- 补全 bake_brief 全字段（含 viewing_sequence / material_anchor / anti_lazy 三个新字段），过 checkBakeBrief 全项；d2 已加入 `BAKE_BRIEF_REQUIRED`。
- 回灌子 agent 发现：G1 新增「暗底 token 语义」条款——`--ink-tint` 比 `--paper` 更深，是暗角色不是次级文字色；次级文字走 ink 明度阶梯。

**验收 deck**：`tests/decks/theme-proving/d2-darkroom-slides.html`（8 页型 cover/toc/low/high/ig1/ig2/chart1/chart2，skeleton v7.6 框架层逐字，`<meta name="theme-id" content="d2">` 已声明）。母题分配：grain 全 8 页；grain-lg/leak/aged 只上 cover+toc；film 齿孔 3 页；beam 只 toc（与 leak 互斥）；halo 承担无框容器边界。

**机器验收结果**：

| 项 | 结果 |
|---|---|
| sync-themes Schema（含 css_recipes + bake_brief） | PASS |
| check-render | ALL PASS 8/8 |
| check-capacity | PASS，违规 0 |
| extract-manifest --write-hashes | 8 页 hash 写回，幂等 |
| compile-bake-prompts 烟测（d2-cover） | bake_brief 整段注入生效（此前 deck 缺 theme-id meta 走回退路径，已修） |
| Playwright 1920×1080 非 reduced-motion 截图 | `tests/harness/results/A-d2-*.png` 8 张，零白屏零 pageerror |
| 溢出/重叠（T34 同口径） | 零 |
| 像素实证 | 齿孔条 159 段恰在 cover 上缘/toc 下缘/low 下缘；cover 右上亮度 45.2 vs 左上 30.5（漏光成立）；正文页无漏光 |
| 双轨导出 export-pptx --track both | 双轨 ok：保真轨 fidelity_avg 98.958、8/8 SVG 载体；可编辑轨 native_text/infographic 1.0，材料层 4 件走 raster（预期行为），uncovered 仅出血裁剪 1 项 |
| harness 全量回归 | 61 项 60 PASS / 1 FAIL——FAIL 即 T34，与 1014 记录的既有失败完全同源（theme-proving/index.html 缺 g3 组 + 存量重叠，与本次改动零交集；本次未触碰 index.html） |

## 子 agent 发现（待决策，未动）

1. **chart token 暗底镜像条款撞档**：index.md「5–8 档 ink 阶梯换成 accent→ink 阶梯」逐字执行会得到 s4≈s6、s5≈s2 明度相邻撞车。d2 deck 折中：1–4 档镜像、s5/s7/s8 保留 ink→paper 阶梯。建议修订 index.md 镜像条款（影响面：所有暗色主题，需另行评审）。
2. **模板 fragment 非合规基准**：e1-risograph 等老 proving deck 是无骨架纯片段、无 data-ig；`theme-proving/capacity-report.json` 显示 64 页 index.html 有上百项容量违规存量。d2 deck 按契约 + 双门禁直接落码，未照抄模板几何。
3. **容量认证对材料层天然免疫**：check-capacity 层 B 中 filter/blend 元素走 raster、background-image+透明底不进 items——grain/leak/aged/beam/film 满版叠不影响容量认证。
4. **T34 硬编码 8 主题组**：d2/d4 验收 deck 若并入 theme-proving/index.html 会破坏 T34 分组断言；当前走独立单主题 deck 模式（同 e1-risograph 等）。是否扩展 T34 覆盖新主题验收待决策。

## 任务 B：D4 黄铜年代新建（Brass Age）

**用户已验收任务 A**（2026-10-15，"通过"）后推进。

**新建** `references/themes/texture/d4/theme.md`：

- G0：世界参考 = 1950s 世博会展馆海报与太空时代工业设计；unforgettable = 黄铜刻线框；分化声明 vs e2 蓝图六层（L1/L2/L3/L4/L5/L6，校验器逐层核真）；material_world + 3 条 anti_lazy（禁 steampunk 齿轮堆/禁金色渐变金属字/禁赛博科幻蓝）。
- G1：深蓝图纸底 + 黄铜 accent + **多色扩展 `--accent-2` 标注红**（封闭双色墨：黄铜=结构 ≤6%，红=批注 ≤3% 单页 ≤2 处，「多色立场」字段齐备）；`--ink-tint` 明确定为蓝图弱墨线色（暗底语义条款与 d2 同源）。
- G2：condensed grotesk 恒重 600–700 + 拉丁大写宽字距 kicker（EXPO-58 式编号前缀）。
- G3：grain/cover（纸纤维 data-URI 仪式页铺底）+ 材料规格四字段（涂漆钢板+黄铜铆钉+蓝图晒图纸 / 展馆顶灯 / css_recipes=["engraved-line","halftone-dots","aged-fade","paper-fiber"]）。
- G4：直角 + 黄铜刻线框容器（2px border + 1px outline-offset 双刻线 + inset 刻槽影），禁弥散影。
- G5：professional，wipe-clip 签名 + count-up 工程数据；禁 scale-pop/persp-in/blur-in（模糊显影是 d2 的签名）。
- G9 四母题（.mt-brs-* 前缀全库唯一）：rivet 球面高光铆钉 / engrave 刻线框 / stamp 红色标注章（文本载体类例外，文字保持可编辑）/ grid 疏格蓝图网（仪式页）。
- bake_brief 全字段（含 viewing_sequence/material_anchor/anti_lazy），d4 入 BAKE_BRIEF_REQUIRED。
- 变体 2 套：锈红（深棕底+锈红主色，与黄铜角色互换）/ 橄榄绿（装备漆+黄铜铭牌）。

**入库校验**：sync-themes 全过——29 套主题（EXPECTED_COUNT 28→29）、两两七层 diff ≥3、focus+accent 唯一、变体合规；`themes/index.md` 质感类 6→7、选择建议 +D4 行、顺手删除指向已删除主题的「G3 陶土印刷」死行；editor.html 面板新增 d4 卡片（含 demo-1/2.png）。

**配套修复**：`extract-manifest.py` THEME_TOKENS 从 6 个旧谱名扩到 12 个（补 -tint/-on/--accent-2/3 现代扩展位）——此前多色主题的 --accent-2 从未进 manifest，D4 的红色标注章无法到达生图指令；修复后 d4 manifest 八 token 齐、编译指令引用 accent-2 生效。

**验收 deck**：`tests/decks/theme-proving/d4-brass-slides.html`（8 页型，skeleton v7.6 逐字，theme-id meta 齐）。母题分配：刻线框全 deck 主容器、铆钉钉框角（每容器 ≤4）、红章全 deck 恰 3 枚（EXPO-58/REV.B/MERGED Q3）、疏格网只 cover/toc。

**机器验收结果**：

| 项 | 结果 |
|---|---|
| sync-themes Schema（29 套全量两两 diff） | PASS |
| check-render / check-capacity | ALL PASS 8/8 / 违规 0（首轮 chart2 铭牌超限，改文案后过） |
| extract-manifest --write-hashes | 8 页 hash 写回，幂等 |
| compile-bake-prompts 烟测（d4-cover） | bake_brief 注入 + accent-2 色值到达 |
| Playwright 截图 | `tests/harness/results/A-d4-*.png` 8 张（非 reduced-motion） |
| 像素实证 | 黄铜刻线 8 页全检出；铆钉球面高光 4/4；红章像素 3 页命中、无章页 ≤13 杂点；疏格网仅 cover/toc |
| demo 图 | demo-1.png（cover）/ demo-2.png（high 页）入主题目录，已注册进面板 |
| 双轨导出 export-pptx --track both | 双轨 ok：保真轨 fidelity_avg 99.288、8/8 SVG 载体；可编辑轨 native_text/infographic 1.0，仅 1 件 rasterized，uncovered 0 |
| harness 全量回归 | 61 项 60 PASS / 1 FAIL——FAIL 即 T34 既有失败（签名与任务 A 后运行逐字一致，与本次改动零交集）；extract-manifest token 扩展未影响 l_hash/n_fidelity/p_editable/q_capacity 等子进程 |

**子 agent 落地备忘**（回灌主题实践要点）：刻线框是 border 容器、框内文字参与容量核算（框高要比内容高大一档）；`.mt-brs-stamp` 净距余量小（5.84px 过 4px 闸），改字号/padding 需当心；mono 宽字距 kicker 在窄刻线容器里容易被容量水平闸拦（估算器对 mono+letter-spacing 偏保守 ≈20px/字符）。

## 下一步

用户验收 D4 → 按 `1015_theme_material_compositing_plan.md` Phase 2–4 全量推进（第二批 E4/E5/E7/E8/E9/E10/E11/G2/G4 材料规格填充 → bake 回退路径结构化 → 全量验证）。

### 补记：D4 图表透明 bug 根因与修复（铺量必读）

**现象**：D4 chart1/chart2 页柱子和折线完全不可见（用户反馈"看不见就没有柱子或者线"）。

**根因**：D4 的 `--texture-layer:url("data:image/svg+xml,...")` 用了双引号 `"` 包裹 url() 内联 SVG，但它嵌在 HTML `style="..."` 属性里——双引号提前截断了 style 属性，`--texture-layer` 之后的所有 token（`--chart-series-*`、`--chart-grid`、`--chart-stroke` 等）全部丢失，柱子和折线用了 `var(--chart-series-*)` 解析为空 = 透明。

**D2 为什么没这个问题**：D2 的 texture-layer 是 `radial-gradient()`，不涉及 `url()`，不产生引号冲突。

**修复**：`url('data:...')` 单引号包 + SVG 内部属性用 `%22` 转义双引号（与 E1 risograph 模板的 texture-layer 写法同模式）。

**铺量纪律**：任何主题的 `--texture-layer` 含 `url(data:...)` 内联 SVG 时，在 HTML inline style 中必须用单引号包 url() + SVG 属性用 `%22` 转义。sync-themes.mjs 校验器已校验 `url()` 只允许 `data:` 内联，但未校验引号转义——这是一个已知缺口，建议后续补静态校验。
