# SlideForge 主题「审美巅峰」优化 · Handover v3

> 建立日期：2026-11-17（batch-3 验收后）
> 用途：**新 session 的唯一入口文档**。读完本文即可继续优化剩余主题，无需重放历史对话。
> 前版：`docs/progress/HANDOVER-v2.md`（v2，2026-11-17）—— 仍保留作参考，但本文件取代其作为入口。
> 基线：本地 `main` 已包含 Phase 1–6 + 批次 1 v2 + 批次 3 的全部提交（未 push）。

---

## 0. 新 session 快速启动

| 项 | 值 |
|---|---|
| 主题库总数 | **23 套**（六类设计轴：色法 6 / 线法 4 / 空间 4 / 质感 6 / 光线 2 / 字法 1） |
| 已升级到「审美巅峰」+ G10 | **23 套**：B1 / C3 / E5 / H1 / E6 / G2 / E7 / F1 / C1 / G4 / G5 / E2 / E3 / C2 / D3 / D4 / E9 / E8 / E11 / **A1 / D2 / E12 / G1**（batch-5；E6 从 batch-1 v2 恢复；E4/F2/E10 已删除） |
| 待优化 | **0 套**——全部 23 套主题均已写入 G10 composition_program |
| 下一批应做 | 无待优化批次；后续可做 D4/E9/E8/E11 的 sampler 验收 + 7 套无 G10 主题复核 |
| 铁律 | **每批只做 4 套 → 多类数据实测 → 出 A/B 与验收包 → 停下来等用户验收 → 通过后才进下一批** |
| 不允许 | 未经用户验收就批量铺量；把「更新 README 示例」做成新增章节；为字号加后拦截门禁 |
| 已删除 | **D1 奶油物语 / C4 纸与墨 / F3 暮色长镜 / E1 孔版印刷 / E4 包豪斯 / F2 霓虹夜行 / E10 星图**——HTML 媒材表达能力有限或与最近邻主题差异化不足，已从技能中完整删除。D3 手绘油彩、E6 孟菲斯已恢复并通过验收。 |

**开工前必读（按顺序）**
1. 本文 §5（分批 SOP 与验收门槛）——决定怎么做。
2. 本文 §4（batch-3 经验教训 + 100% 防范清单）——避免重蹈覆辙。
3. `analysis/G10-主题DNA规范草案.md` —— G10 字段组的原始规范与「审美巅峰」验收口径。
4. `skills/SlideForge/references/themes/<分类>/<id>/theme.md` —— 每套主题的 G0–G9/G10。
5. `assets/theme-sampler/content.md` —— theme-sampler 的内容规范（山禾集业务汇报）。

---

## 1. 任务关键描述

### 1.1 优化目标

30 套主题从「可替换参数集」升级为「决定信息如何进入空间的程序」——每套主题获得构图主权，使同一段内容在不同主题下呈现结构级差异（非换配色），灰度去色后仍可辨识。

> **2026-11-18 更新（batch-5 完成后 + 主题纠正）**：D1/C4/F3/E1/E4/F2/E10 七套主题已删除，主题库从 30 套缩减为 23 套。全部 23 套主题均已写入 G10 composition_program。D3 手绘油彩、E6 孟菲斯已恢复并通过验收。用户于 2026-11-18 纠正删除对象：E6 孟菲斯恢复、E4 包豪斯删除（theme/gallery/editor/index/README 全部同步）。本文件中历史段落仍可能提及 30/29/26/27/24 等旧数字，以本节计数为准。

### 1.2 G10 composition_program 管线

G10 是让主题获得构图主权的字段组，含 9 个子字段：
- `doctrine`（世界观一句话）
- `page_composition`（骨架 skeleton + 网格 grid + 平衡 balance + 留白 whitespace_ratio + 信息流 flow）
- `signature_operator`（信息编译规则——每条信息如何变成视觉元素）
- `silhouette`（剪影特征）
- `info_grammar`（每页类型构图契约：cover/toc/claim/analysis/data/closing 各一条）
- `type_scale`（`--t-*` 令牌源，px@1920 画布基准）
- `invariants`（每页硬约束列表）
- `forbidden_defaults`（禁止的默认模板列表）
- `dna_events`（每页型 DNA 强度）

**管线接入**（batch-3 修复）：
- `SKILL.md` Step 1 页计划表：标注 G10 `info_grammar` 页型（硬规则）
- `SKILL.md` Step 2 冻结主题：逐字段读取 G10 作为构图契约（硬规则）
- `SKILL.md` Step 4 逐页生成：重读 `signature_operator`/`info_grammar`/`invariants`/`forbidden_defaults`/`dna_events`（硬规则）
- `index.md` Schema 表：L8 构图程序行（G10 composition_program）

### 1.3 文档引用

| 文档 | 用途 |
|------|------|
| `analysis/G10-主题DNA规范草案.md` | G10 字段组原始规范 + 「审美巅峰」验收口径 |
| `skills/SlideForge/SKILL.md` | 生成管线（Step 1/2/4 含 G10 硬规则） |
| `skills/SlideForge/references/themes/index.md` | 主题 Schema 表（L1–L8） |
| `skills/SlideForge/references/themes/<分类>/<id>/theme.md` | 各主题 G0–G9 + G10 |
| `skills/SlideForge/assets/skeleton.html` | 骨架 v7.7（1920×1080 px 基准，`.t-*` 角色类 + `max()` 地板） |
| `skills/SlideForge/gallery/index.html` | README 画廊（23 主题 cover 样张） |
| `assets/theme-sampler/content.md` | theme-sampler 内容规范（山禾集） |
| `docs/progress/G10-pipeline-audit.md` | G10 管线缺口审计报告（batch-3） |
| `docs/progress/HANDOVER-v2.md` | v2 handover（批次 1 经验教训） |
| `docs/progress/HANDOVER-v3.md` | ← 本文件 |

---

## 2. 已完成主题明细

### 2.1 批次 1 v2（9 套）

| 主题 | `--t-display` | signature_operator 一句话 |
|------|--------------|------------------------|
| B1 瑞士国际主义 | 176 | 12 栏网格 + 标题跨栏语义断行 + KPI 重排为右侧纵向数据脊 |
| C3 终端绿 | 104 | 内容编译成命令行 stdout + 描边终端窗口 + key:value 输出行 |
| E5 构成主义 | 128 | −12° 力带劈开版面 + 标题反白装进带内 + 正文沿力线阶梯错排 |
| H1 氤氲手卷 | 92 | 自右向左手卷展开 + 标题竖排居右 + 汉数题跋 + 朱印句读 |
| E6 孟菲斯 | 112 | 几何色面碰撞拼贴 + palette 轮转 + 3px 墨粗描边 + 不对称平衡 |
| G2 腮红荧光笔 | 128 | 单栏流式正文 + 荧光高亮带 + 便签浮在右侧标注 |
| E7 浮世绘 | — | 浮世绘前景深墨块 + 天空留白 + 印章句读（需复核） |
| F1 浮光玻璃 | 108 | 居中悬浮主玻璃 + 四角柔光斑 + 深底亮玻璃明度签名 |
| C1 信号黑 | 120 | 黑场单焦点 + 信号橙色块（唯一焦点）+ 巨号页码背景层 + 明度档分区 |

### 2.2 批次 3（4 套，本次新增）

| 主题 | `--t-display` | signature_operator 一句话 | G10 claim 契约 |
|------|--------------|------------------------|---------------|
| G4 靛墨黄页 | 128 | 出血色面 + 靛蓝线框分区 + 太阳黄焦点面 + 余烬橙单点 | 裂屏对开（黄/靛对撞），主张句在黄面上反白，说明在靛面上 |
| G5 三色旬刊 | 112 | 三色反转色面 + 明度阶梯 + 暗夜蓝底苔绿字焦点面 + 刊号签/三色带 | 裂屏对开（暗夜蓝/苔绿对撞），主张句在暗夜蓝底苔绿字上 |
| E2 蓝图 | 104 | 双线图框 + 标注线 + 图框标题栏 + 制图网格全页铺 + mono key:value | 主张句在主图框内，标注线指向关键数据点，标题栏钉右下 |
| E3 装饰艺术 | 120 | 中轴对称金线框阵列 + 双线金框 + 扇形放射 + 菱形分隔 + 金线翼卫 | 中轴金框装主张句 + 两侧金线翼卫 + 底部菱形引出说明 |

### 2.3 批次 4（2 套保留，2 套删除）

| 主题 | `--t-display` | signature_operator 一句话 | G10 claim 契约 |
|------|--------------|------------------------|---------------|
| C2 暗夜植物园 | 96 | 图鉴卡阵 + 编号签条 + 标本引线 + 叶脉侧缘 + 暖金辉光 | 图鉴卡阵承载主张句（卡内衬线大字 + 拉丁学名注），标本引线从卡引出连接辅助说明，编号签条钉卡角 |
| D3 手绘油彩 | 96 | 笔触块标题 + 虚线圈注 + 不规则圆角切片 + 画框装裱 | 笔触块垫主张句标题（左上），不规则圆角切片承载正文说明 + 虚线圈注关键词（右侧），画框装裱 KPI 横贯底部 |

> **已删除**：D1 奶油物语 / C4 纸与墨——HTML 媒材表达能力有限或与最近邻主题差异化不足，已从技能中完整删除（theme.md / gallery / editor / index.md 均已清理）。D1/C4 的 G10 和 sampler 产物一并删除。

### 2.4 批次 4b-5（5 套 G10 已写）

| 主题 | `--t-display` | signature_operator 一句话 |
|------|--------------|------------------------|
| D4 黄铜年代 | — | 刻线框阵 + 铆钉四角 + 红色标注章 + 疏格钢板网 |
| E9 地质地层 | — | 剖面切片阵 + 层理色带页底 + 岩芯样本条 + 年代标注签 |
| E8 号外报纸 | — | 通栏粗细双线 + 多栏正文 + 号外头条 + 报头徽标 |
| E11 票据 | — | 齿孔撕线 + 票根字段行 + 条码 + 副券区 |

> 这 4 套 G10 已写入 theme.md，sampler 已制作待验收。E10 星图已删除（与 D2/F1 暗色光学轴差异化不足）。

### 2.5 批次 5（4 套保留，E4 删除，E6 恢复）

| 主题 | `--t-display` | signature_operator 一句话 | G10 claim 契约 |
|------|--------------|------------------------|---------------|
| A1 电子杂志 | 96 | Ghost 残影巨字 + 竖排题字条 + hairline 分栏 + 墨点角标 | Ghost 残影巨字背景标题（左上），hairline 分栏正文（右侧），主数字 `.t-display` 竖排题字条收束（底部） |
| D2 柔光暗房 | 96 | 显影晕无框容器 + 胶片齿孔条 + 光束角标 + 银盐颗粒层 | 显影晕托底主张句标题（左上），显影晕分组正文（右侧），主数字独占显影晕（底部），齿孔条压缘 |
| E12 商务粗野 | 96 | 描边平面卡阵 + 纯墨硬偏移投影 + 贴纸 chip + 3px 墨结构线 | 极粗标题 + 荧光标记主张句（左上），描边平面卡阵承载正文（右侧），主数字独占焦点卡（底部 8px 硬影），3px 墨结构线横贯 |
| G1 翡翠年鉴 | 96 | 深翡翠绒面 + 奶油墨档卡 + 金箔奖章 + 年鉴栏框线 | 衬线巨字主张句左对齐（左上奶油墨），奶油墨档卡承载正文（右侧绿字反白），主数字独占奶油墨档卡 + 金箔奖章（底部），栏框线分隔 |
| E6 孟菲斯（恢复） | 112 | 几何色面碰撞拼贴 + palette 轮转 + 3px 墨粗描边 + 不对称平衡 | batch-1 v2 样张恢复，G10 保留原始版本（几何拼贴 + palette 轮转），从 batch-5 的误删中撤销 |

> **主题纠正（2026-11-18）**：用户纠正删除对象——**E6 孟菲斯恢复**（从 `13ca24e` 取回 theme.md + demo PNG + gallery CSS/slide + editor 面板，README 样张回到 `v2-e6.png`，E12 分化声明改回对 e6），**E4 包豪斯完整删除**（theme 目录 + gallery + editor + index.md + compositing.md + README 双语 + batch5/p13 e4 样张 + 验收目录）。E4 原删除理由：与 E6/E12 差异化不足。F2 霓虹夜行（与 D2/F1 光学轴差异化不足）、E10 星图（与 D2/F1 暗色光学轴差异化不足）同样已删除。主题库保持 23 套。

> **batch-5 修复要点**：四套 sampler 均经历「KPI 字号从 `.t-heading`(64px)/`.t-subhead`(40px) 升级到 `.t-display`(96px) → 垂直三区分布（标题 110-380 / 正文 460-740 / KPI 790-990）→ 重心校正（金箔奖章移到右上空象限等）→ 容器重叠归零」的系统性修复。G10 的 `info_grammar.claim` 契约已同步反映这些布局决策。

### 2.5 G10 管线接入状态

| 组件 | 状态 | 验证方法 |
|------|------|---------|
| SKILL.md Step 1（页计划标注 info_grammar） | ✅ 已接入 | `grep -c "info_grammar" SKILL.md` = 8 |
| SKILL.md Step 2（读取 G10 作构图契约） | ✅ 已接入 | `grep -c "composition_program" SKILL.md` = 4 |
| SKILL.md Step 4（逐页遵守 5 字段） | ✅ 已接入 | `grep -c "signature_operator\|invariants\|forbidden_defaults" SKILL.md` = 4+2+2 |
| index.md L8 Schema 行 | ✅ 已接入 | `grep "L8" index.md` 有结果 |
| 4 主题 G10 完整性 | ✅ 全有 | 4 主题各 `grep -c "composition_program" theme.md` = 1 |

---

## 3. batch-3/4 关键修复

### 3.1 G5 色值修正

| Token | 旧色值（错误） | 正确色值 | 色名 |
|-------|--------------|---------|------|
| --paper | #F2B6C6 | #E4C9A8 | 赭石 |
| --paper-tint | #F2D86A | #8BAE6F | 苔绿 |
| --ink | #7A1F35 | #1A2B3D | 暗夜蓝 |
| --ink-tint | #5E1828 | #121E2D | 深暗夜蓝 |
| --accent | #F2D86A | #8BAE6F | 苔绿 |
| --accent-on | #7A1F35 | #1A2B3D | 暗夜蓝 |

修复范围：theme.md 9 处旧色名 + gallery/index.html inline style + sampler HTML。

### 3.2 G10 管线缺口修复

**问题**：G10 写进 13 套 theme.md 但 SKILL.md 0 引用——agent 生成 PPT 时不读 G10，所有 `info_grammar`/`signature_operator`/`invariants`/`forbidden_defaults` 不生效。

**修复**：SKILL.md Step 1/2/4 补入 G10 硬规则 + index.md Schema 补 L8 行。详见 `docs/progress/G10-pipeline-audit.md`。

### 3.3 E3 中轴对称 invariant 补强

**问题**：E3 invariant 说"中轴对称"但未明确"对称双栏左右两栏必须 flex:1 等宽"，导致 sampler 中 KPI 区左右栏用 padding-only 定位、中轴金框视觉偏移。

**修复**：invariant 第一条补入"对称双栏的左右两栏必须 flex:1 等宽，确保中轴元素严格居中（禁用 padding-only 定位替代 flex 等分）"。

### 3.4 batch-4 字号回归与容器重叠修复

**问题 1（字号回归）**：4 套 sampler 的正文和 KPI 字号普遍偏小——Playwright `getComputedStyle()` 审计显示正文 20px（应为 28px `.t-body`）、KPI 标签 15px（应为 18px `.t-caption`）、裸写 inline `font-size:13px` 绕过骨架 `.t-*` 令牌。

**根因**：sampler HTML 中大量使用 inline `font-size:20px/22px` 覆盖了骨架角色类，等于绕过了 `max()` 地板保护。

**修复**：全部替换为 `.t-body`/`.t-caption`/`.t-display` 角色类，删除所有 inline `font-size` 声明。这是防范清单第 10 条的再次违反。

**问题 2（D3 容器重叠）**：字号修复后 D3 右栏切片因字号增大而向下膨胀，与底部 KPI 画框栏产生 82px 重叠。

**修复**：压缩右栏 padding（36→28px）、line-height（1.75→1.65）、第三行降至 `.t-caption`；压缩 KPI padding（28→24px）、数字字号（56/52→52/48）、KPI `bottom` 从 96→84px。留出 94px 间隙。

**问题 3（C2 布局重叠）**：C2 主张句图鉴卡（width:780, top:120）与右栏正文（top:380, left:960）在 380px 处重叠。

**修复**：缩减卡宽至 680px、右栏左移至 left:860、重新分配垂直位置、KPI 从横排三格改为纵向编号卡阵。

---

## 4. batch-3/4 经验教训 + 100% 防范清单

### 4.1 batch-3 踩过的 5 个坑

| # | 坑 | 根因 | 修复 | 代价 |
|---|---|---|---|---|
| 1 | **G10 成了死文档** | G10 写进 theme.md 但 SKILL.md 0 引用——agent 不读 G10 | SKILL.md Step 1/2/4 补入硬规则 + index.md L8 行 | 5 轮迭代才发现 |
| 2 | **从零重写布局丢掉骨架框架层** | 构建 sampler 时用 `padding:0` + 绝对定位面板，丢了 `--slide-pad`/`.mastfoot`/`.reveal` | 保留 gallery 骨架框架 CSS，只追加截图修复 CSS | 3 轮迭代 |
| 3 | **用错内容源** | 用了 gallery 的 cover 内容（"想象的形状"）而非 sampler 的 claim 内容（"山禾集"） | 确认内容源：`assets/theme-sampler/` 截图 = 原版 sampler = 山禾集业务汇报 | 2 轮迭代 |
| 4 | **保留老布局丢掉 G10 优化** | 从原版 sampler 原样提取 HTML，但原版是 G10 之前的布局（横排等权三格 KPI） | 布局必须按 G10 `info_grammar.claim` 契约重构，只保留骨架框架层 + 内容 | 1 轮迭代 |
| 5 | **E3 中轴金框未严格居中** | invariant 说"中轴对称"但未明确 flex:1 等宽约束，左右栏用 padding-only | invariant 补入 flex:1 等宽约束 + sampler 修复 | 用户目视发现 |

### 4.2 batch-4 踩过的 3 个坑

| # | 坑 | 根因 | 修复 | 代价 |
|---|---|---|---|---|
| 6 | **字号回归——inline font-size 绕过 .t-\* 令牌** | sampler HTML 大量使用 inline `font-size:20px/22px`，覆盖了骨架角色类，绕过 `max()` 地板 | 全部替换为 `.t-body`/`.t-caption`/`.t-display` 角色类，删除所有 inline `font-size` | 3 轮迭代 |
| 7 | **字号修复后容器膨胀导致重叠** | 字号从 20px→28px 后右栏向下膨胀 82px，与底部 KPI 重叠 | 压缩 padding/line-height/数字字号，留出 94px 间隙 | 1 轮迭代 |
| 8 | **C2 绝对定位面板宽度过大导致重叠** | 主张句卡 width:780 + 右栏 left:960，在 380px 处重叠 | 缩减卡宽至 680、右栏左移至 860、KPI 改纵向编号卡阵 | 1 轮迭代 |

### 4.3 100% 防范清单（v2 的 12 条 + batch-3 的 5 条 + batch-4 的 2 条 = 19 条）

| # | 坑 | 正确做法 | 来源 |
|---|---|---|---|
| 1 | 并行 dispatch 子 agent 超过 2 个 | 最多并行 2 个，或串行 | v2 |
| 2 | 标题让换行 | 调 `--t-display` 而非折行 | v2 |
| 3 | 只查画布越界不查容器内溢出 | 补最近显式 `top`+`height` 绝对定位祖先检测 | v2 |
| 4 | 重叠检测不排除旋转元素 | 排除带 `transform` 的元素 | v2 |
| 5 | 同组 KPI 用等宽检测 | 改检测 x 间距规则性 | v2 |
| 6 | titleFlush 用 bounding box 宽度 | 用 Range API 测实际文本渲染宽度 | v2 |
| 7 | 留白只查下限不查上限 | 低密度 ≥40% ≤65%；高密度 ≥20% ≤50% | v2 |
| 8 | 只查留白率不查 9 宫格 | 3×3 网格无空格 | v2 |
| 9 | 布局改动不回写 theme.md | G10 invariants 必须与实际产物一致 | v2 |
| 10 | 审计把 `var(--t-*)` 计作裸写字号 | 只查裸写 inline px | v2 |
| 11 | `git add -A` | 用 `git add -u` + 显式路径 | v2 |
| 12 | 提交默认 push | 只到本地，不 push（除非用户显式要求） | v2 |
| **13** | **G10 写了不接入管线** | **SKILL.md Step 1/2/4 必须引用 G10；新主题写 G10 后验证 SKILL.md grep > 0** | **batch-3** |
| **14** | **从零重写丢掉骨架框架层** | **构建 sampler 时保留 gallery 骨架 CSS（padding/mastfoot/reveal/G9母题），只追加截图修复 CSS** | **batch-3** |
| **15** | **用错内容源** | **sampler 内容 = `assets/theme-sampler/` 截图 = 原版 sampler = 山禾集业务汇报；gallery cover 内容 = "想象的形状"——两者不同** | **batch-3** |
| **16** | **保留老布局丢掉 G10 优化** | **原版 sampler 是 G10 之前的布局（横排等权三格 KPI 违规）；必须按 G10 `info_grammar.claim` 契约重构布局，只保留骨架框架层 + 内容** | **batch-3** |
| **17** | **对称主题中轴元素未严格居中** | **invariant 必须写明"对称双栏 flex:1 等宽"；sampler 中左右栏用 flex:1 而非 padding-only** | **batch-3** |
| **18** | **inline font-size 绕过 .t-\* 令牌** | **sampler HTML 禁用 inline `font-size`；内容文字只用 `.t-body`/`.t-caption`/`.t-display` 角色类；用 Playwright `getComputedStyle()` 审计实际渲染值，不只看源码** | **batch-4** |
| **19** | **字号修复后容器膨胀重叠** | **字号增大后必须重新检测所有绝对定位容器的 `getBoundingClientRect()` 交集面积；压缩 padding/line-height 留出安全间距** | **batch-4** |

### 4.4 theme-sampler 制作 SOP（batch-3 确立，batch-4 补充）

**第一步就包含最终交付的 theme-sampler 完整 PPTX 页面**：

1. **内容源**：`assets/theme-sampler/content.md`（山禾集业务汇报）
2. **页型**：claim（主张页）——最能集中展示主题 DNA
3. **骨架框架 CSS**：从 `gallery/index.html` 提取完整 `<style>` 块（含 padding/mastfoot/reveal/G9 母题）
4. **布局**：按各主题 `theme.md` 的 G10 `info_grammar.claim` 契约手写 slide HTML
5. **色值**：从 `theme.md` G1 color 逐字复制，不猜测
6. **KPI**：按 G10 `info_grammar.data` 契约排列（禁止横排等权三格——`forbidden_defaults`）
7. **G9 母题**：从 `theme.md` G9 逐字复制 CSS + 原版 sampler 中的位置/尺寸
8. **截图修复 CSS**：追加 `--slide-scale:1` + `content-visibility:visible` + `transform:none` + 动效终态
9. **Playwright 截图**：逐 slide 元素截图，1920×1080 PNG
9.5. **字号审计（batch-4 新增）**：用 Playwright `getComputedStyle()` 逐元素检查实际渲染字号，确保正文 ≥28px（`.t-body`）、标签 ≥18px（`.t-caption`）；发现 inline `font-size` 立即替换为角色类
9.6. **容器重叠检测（batch-4 新增）**：用 `getBoundingClientRect()` 逐对检测所有绝对定位容器的交集面积，重叠 = 0 才通过
10. **验收**：4 张截图展示给用户，通过后才进下一批
11. **PPTX 导出**：sampler HTML 通过骨架导出管线生成完整 PPTX 文件（含全部页面），作为最终交付物

**关键**：theme-sampler 不是临时验收物——它是最终交付的 PPTX 页面，在第一步制作时就要包含完整的导出就绪结构。

---

## 5. 分批 SOP 与验收门槛

### 5.1 分批表

| 批次 | 主题 | 状态 | 备注 |
|------|------|------|------|
| 批次 1 v2 | E6 / G2 / E7 / F1 | ✅ 已验收 | v2 重启后通过 |
| 批次 2 | C1 / B1 / C3 / E5 / H1 | ✅ 已验收 | 含 v2 验收 + C1 G10 补全 |
| **批次 3** | **G4 / G5 / E2 / E3** | **✅ 已验收** | **G10 管线接入 + 色值修正 + 布局重构** |
| **批次 4** | **C2 暗夜植物园 / D3 手绘油彩 / ~~D1 奶油物语~~ / ~~C4 纸与墨~~** | **✅ 已验收** | **C2/D3 G10 + sampler 完成；D1/C4 删除（差异化不足）** |
| **批次 4b** | **E8 号外报纸 / E11 票据** | **✅ G10 已写** | **E8/E11 G10 完成（E1 已删除）** |
| **批次 5** | **A1 电子杂志 / D2 柔光暗房 / E12 商务粗野 / G1 翡翠年鉴 / ~~E4 包豪斯~~ / ~~F2 霓虹夜行~~** | **✅ 已验收** | **A1/D2/E12/G1 G10 + sampler 完成；E4（差异化不足）、F2（与 D2/F1 撞光学轴）删除；E6 孟菲斯从误删中恢复** |
| 批次 6 | D4/E9/E10/E8/E11 sampler 验收 | ⬜ 待做 | G10 已写，sampler 待制作验收 |
| 批次 7 | 7 套无 G10 主题补写 G10 | ⬜ 待做 | 尾批：补全 + 复核 |

### 5.2 每批 SOP

```
1. 读 theme.md G0–G9 + G10（4 套）
2. 确认 G10 info_grammar.claim 契约
3. 构建 theme-sampler HTML（保留骨架框架层 + 山禾集内容 + G10 契约布局）
4. Playwright 截图 4 张 1920×1080 PNG
5. 导出完整 PPTX（含全部页面）
6. 展示给用户验收
7. 通过后：
   a. 更新 README（中英）追加 batch-N 样张
   b. 提交（只到本地，不 push）
   c. 更新 handover 文档
8. 进入下一批
```

### 5.3 验收门槛

- **G10 契约一致性**：sampler 布局必须与 theme.md 的 G10 `info_grammar.claim` 契约一致
- **forbidden_defaults 零违反**：`横向等权三格 KPI` 等禁止项全部为零
- **骨架框架层保留**：padding/mastfoot/reveal/G9 母题原样保留
- **色值正确**：从 theme.md G1 color 逐字复制
- **内容一致**：与 `assets/theme-sampler/content.md` 一致
- **PPTX 可导出**：sampler HTML 通过骨架导出管线生成完整 PPTX

---

## 6. 下一批（批次 6）主题预览

| 主题 | 分类 | 气质 | 预期 G10 方向 |
|------|------|------|-------------|
| D4 黄铜年代 | texture | 刻线框阵 + 铆钉四角 + 红色标注章 | G10 已写，sampler 待制作 |
| E9 地质地层 | texture | 剖面切片阵 + 层理色带页底 + 岩芯样本条 | G10 已写，sampler 待制作 |
| E10 星图 | type | 星座连线阵 + 黄道坐标网格 + 星等注记 | G10 已写，sampler 待制作 |
| E8 号外报纸 | line | 通栏粗细双线 + 多栏正文 + 号外头条 | G10 已写，sampler 待制作 |
| E11 票据 | line | 齿孔撕线 + 票根字段行 + 条码 + 副券区 | G10 已写，sampler 待制作 |

> 5 套 G10 已写入 theme.md，sampler 尚未制作。需按 batch-3/4/5 的 SOP 制作 sampler、Playwright 审计、用户验收后更新 README。

---

## 7. 本机环境备忘

- shell shim 缺 `dirname/head/tail/ls/mkdir/cat/sed`，命令不接管道；用托管 Node `fs` / `child_process.execFileSync` 代替
- Playwright：托管 Node + `playwright-core@1.65.0`（装在 `~/.workbuddy/binaries/node/workspace/node_modules`）+ 系统 Chrome `C:/Program Files/Google/Chrome/Application/chrome.exe`
- `.gitignore` 用 `/docs/*` + `!/docs/progress/` 白名单；**绝不用 `git add -A`**
- 提交默认**只到本地、不 push**
