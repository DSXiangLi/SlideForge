# Phase 5 · README Theme Gallery 替换为 4 套构图程序样张

> 日期：2026-11-12 ｜ 前置：`phase4-sampler-v2-ab.md` ｜ 用户指令：「很好确实差异化非常显著了，请替换README 中模版」

## 0. 需求溯源与纠偏链路

| 阶段 | 用户意图 | 我的动作 | 结论 |
|---|---|---|---|
| `5dc73a8` | 「更新 README 中示例」 | 另起一套自造内容、**新增** Theme DNA 章节 | ❌ 理解错：应是更新已有示例，不是加章节 |
| Phase 4 | 「用 `tests/decks/theme-sampler/` 相同内容做 sampler，与现有展示图对比，看有无更好的可替换」 | 从 git 历史 `41a3147` 取回源 deck，用同一内容对象 × 4 套 G10 构图程序重编译；出具 A/B 报告；按选择「只移除不替换」撤销 Theme DNA 章节 | ✅ 差异化成立，Gallery 暂不动 |
| **Phase 5（本轮）** | 「差异化非常显著了，请替换 README 中模版」 | **4 张整体替换** Gallery | ✅ 本文件记录 |

关键事实：新版只覆盖 **B1 / C3 / E5 / H1** 四套已升级 G10 的主题，而原 Gallery 现役 12 张里**仅 C3 属于这四套**（B1/E5/H1 原本不在 Gallery 中）。因此「替换」必然改变 Gallery 阵容。开工前用选择题向用户确认范围，用户选定 **「4 张整体替换（推荐）」**。

## 1. 范围决策

- ✅ **选定**：Gallery 只展示新版 4 张，标题「12 套主题」→「4 套构图程序」，文案改为陈述结构级差异。
- ❌ 未选：新版置顶 + 旧 12 张保留（章节翻倍、新旧并置放大落差）；只换 C3 + 增补 H1（只有 2 张体现差异化）。
- **代价（已向用户明示）**：不再展示 F 系光学 / G 系多色主题广度。旧 `p01`–`p29` 共 28 张仍保留在 `assets/theme-sampler/`，未删除、未改名，README 以 footnote 指明其存在。

## 2. 变更清单

### 2.1 新增样张文件（4 个，均为 untracked 新文件）

从 `docs/progress/theme-sampler-v2/new-*.png` 复制到 `assets/theme-sampler/v2-*.png`，命名用 `v2-` 前缀以与旧 `pNN-xx` 序列区分。全部为 **1920×1081 px**（渲染截图含 1px 边界），与旧样张 1920×1080 规格基本一致。

| 目标文件 | 源文件 | 字节 | 主题 |
|---|---|---|---|
| `assets/theme-sampler/v2-b1.png` | `new-b1.png` | 152,636 | B1 · 瑞士国际主义 · 12 栏网格 + 数据脊 |
| `assets/theme-sampler/v2-c3.png` | `new-c3.png` | 200,217 | C3 · 终端绿 · 终端窗口 + key:value |
| `assets/theme-sampler/v2-e5.png` | `new-e5.png` | 233,160 | E5 · 构成主义 · −12° 对角力带 |
| `assets/theme-sampler/v2-h1.png` | `new-h1.png` | 333,879 | H1 · 氤氲手卷 · 竖排题字 + 朱砂印 |

### 2.2 `README.md`

- 标题：`## Theme Gallery: One Deck × 12 Themes` → `## Theme Gallery: One Deck × 4 Composition Programs`
- 正文：删除「12 most distinctive」「含 F 系两主题 / G 系三主题」「all 28 live」等与旧阵容绑定的表述；改为写明四套主题各带 G10 `composition_program` 契约、差异是结构级而非调色板，逐一列出四种空间组织方式，并点明字号由 `.t-*` 角色类决定、可读性下限由设计层锁定而非事后门禁。
- 表格：3 列 × 4 行（12 张 `width=280`）→ **2 列 × 2 行（4 张 `width=416`）**，图放大以便看清结构差异；列宽与 README 其他 2 列表格（AI 插画节）一致。
- Footnote：新增一行说明旧 `p01`–`p29` 仍在 `assets/theme-sampler/`、源 deck 为 `tests/decks/theme-sampler/`。

### 2.3 `README_ZH.md`

与英文版逐项对应：标题「同一份内容 × 12 套主题」→「同一份内容 × 4 套构图程序」；文案改为「每套主题对『信息如何进入空间』有不同主权」「差异是结构级的，不是换配色」；同一 2×2 表格与 footnote。

## 3. 文案依据（为何这样写）

旧文案有一处**图文不符**：声称 themes differ systematically in **layout**... not just color，但抽查现役 6 张（B1/C3/E5/E7/G1/F1）发现 12 张全是同一版式骨架——大标题 → 两段正文 → 横向等权三格 KPI → 三条列表，元素位置几乎逐像素一致，仅换配色/字体/背景；且「等权三格 KPI」正是 B1 的 G10 `forbidden_defaults` 明令禁止的。新版 4 张是**同一内容对象按各主题 `signature_operator` 重新编译 DOM**，结构真正不同，这句宣称才第一次成立。文案因此从「笼统声称差异」改为「具体列出四套如何组织空间」。

## 4. 校验结果

| 项 | 结果 |
|---|---|
| 两版 README 全部 `src="assets/..."` 引用 | 各 23 条，**缺失 0** |
| 新版 4 张引用 | 各 4 条，路径全部存在 |
| 残留「12 Themes / 12 套主题 / 12 most」 | **0** |
| diff hunk 范围 | 仅 `L1`（既有 WIP）、`L87`（标题）、`L89`（文案）、`L91–109`（表格 + Theme DNA 撤销） |
| 预览页 `gallery-preview.html` 真实浏览器渲染 | 4 图 `ok=true`，各 1920×1081，**page errors 0** |

- 首轮预览页相对路径少算一级（`../../` 应为 `../../../`：从 `docs/progress/theme-sampler-v2/` 到仓库根），4 图全 `ok=false`；已修正重跑通过。
- 预览页经 `present_files` 的静态服务（`http://127.0.0.1:*/static-html/<hash>/gallery-preview.html`）打开时，`../../../assets/...` 会 404（服务根即 HTML 所在目录，跨不出去）。故为每张图加 `onerror` 回退到同目录 `new-*.png`（内容字节相同）。实测：服务返回最新 HTML（4815 bytes、含 onerror），`new-b1.png` 200 / 152636 bytes，模拟阻断 assets 路径后 4 图全部回退成功、page errors 0。**两种打开方式（file:// 直开 / 静态服务）均已验证可显示**。
- `git diff --stat`：`README.md` / `README_ZH.md` 各 32 行变更（合计 +18 / −46）。累积 diff 含三项：本轮 Gallery 替换、上一轮 Theme DNA 章节撤销、既有 WIP 首行标题 `# pptx-html-design` → `# SlideForge`（HEAD 仍是旧标题，非本轮改动，未触碰）。
- 新版样张自身的渲染审计数据见 `theme-sampler-v2/report.json`：4 页零画布越界、零容器溢出、零灰化弱读、零重叠、零页面错误；字号层级比 6.93:1（C3）～11.73:1（B1）。

## 5. 产物

| 文件 | 用途 |
|---|---|
| `docs/progress/theme-sampler-v2/gallery-preview.html` | 模拟 README Gallery 表格的替换后预览（2×2 + 中英文案 + footnote + 替换说明） |
| `docs/progress/theme-sampler-v2/gallery-preview.png` | 该预览页整页截图（1100px 宽，真实 Chrome 渲染） |
| `docs/progress/phase5-readme-gallery-replace.md` | 本文件 |
| `docs/progress/phase4-sampler-v2-ab.md` | 前置 A/B 对比结论与替换建议 |
| `docs/progress/theme-sampler-v2/compare.html` | 新旧 8 图并排对照 |

## 6. 遗留与边界

- **本轮改动未提交**（用户本次只要求替换，未要求提交）。工作区另有 `SKILL.md` / `bridge_mcp.py` 修改及 `.workbuddy/`、`analysis/`、`SlideForge.zip`、h1 两张 demo 图等未跟踪项，均与本轮无关。
- `assets/theme-dna/` 的 8 张图保留未删，只是自 Phase 4 起不再被任何 README 引用。
- 旧 `p01`–`p29` 全部保留；若日后需要恢复主题广度展示，可直接从 `assets/theme-sampler/` 引用，无需重新渲染。
- 诚实边界：新版 4 张均为**单页高密度页**（同一「山禾集 · 1.1 整体特色及优势」内容），与旧 Gallery 单页 A/B 公平；README 文案亦未宣称覆盖多页型。若要下「整 deck 替换」结论，需再补一轮「同一份内容 × 6 页型 × 4 主题」。
