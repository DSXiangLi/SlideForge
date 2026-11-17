# SlideForge 主题「审美巅峰」优化 · Handover v3

> 建立日期：2026-11-17（batch-3 验收后）
> 用途：**新 session 的唯一入口文档**。读完本文即可继续优化剩余主题，无需重放历史对话。
> 前版：`docs/progress/HANDOVER-v2.md`（v2，2026-11-17）—— 仍保留作参考，但本文件取代其作为入口。
> 基线：本地 `main` 已包含 Phase 1–6 + 批次 1 v2 + 批次 3 的全部提交（未 push）。

---

## 0. 新 session 快速启动

| 项 | 值 |
|---|---|
| 主题库总数 | **30 套**（六类设计轴：色法 7 / 线法 4 / 空间 5 / 质感 8 / 光线 4 / 字法 2） |
| 已升级到「审美巅峰」+ G10 | **13 套**：B1 / C3 / E5 / H1 / E6 / G2 / E7 / F1 / C1 / **G4 / G5 / E2 / E3**（batch-3 新增） |
| 待优化 | **17 套**，分 **5 批**（4 批 × 4 + 尾批 1） |
| 下一批应做 | **批次 4：C2 暗夜植物园 / C4 纸与墨 / D1 奶油物语 / D3 手绘油彩** |
| 铁律 | **每批只做 4 套 → 多类数据实测 → 出 A/B 与验收包 → 停下来等用户验收 → 通过后才进下一批** |
| 不允许 | 未经用户验收就批量铺量；把「更新 README 示例」做成新增章节；为字号加后拦截门禁 |

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
| `skills/SlideForge/assets/skeleton.html` | 骨架 v7.6（1920×1080 px 基准） |
| `skills/SlideForge/gallery/index.html` | README 画廊（29 主题 cover 样张） |
| `assets/theme-sampler/content.md` | theme-sampler 内容规范（山禾集） |
| `docs/progress/G10-pipeline-audit.md` | G10 管线缺口审计报告（batch-3） |
| `docs/progress/HANDOVER-v2.md` | v2 handover（批次 1 经验教训） |
| `docs/progress/HANDOVER-v3.md` | ← 本文件 |

---

## 2. 已完成 13 套主题明细

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

### 2.3 G10 管线接入状态

| 组件 | 状态 | 验证方法 |
|------|------|---------|
| SKILL.md Step 1（页计划标注 info_grammar） | ✅ 已接入 | `grep -c "info_grammar" SKILL.md` = 8 |
| SKILL.md Step 2（读取 G10 作构图契约） | ✅ 已接入 | `grep -c "composition_program" SKILL.md` = 4 |
| SKILL.md Step 4（逐页遵守 5 字段） | ✅ 已接入 | `grep -c "signature_operator\|invariants\|forbidden_defaults" SKILL.md` = 4+2+2 |
| index.md L8 Schema 行 | ✅ 已接入 | `grep "L8" index.md` 有结果 |
| 4 主题 G10 完整性 | ✅ 全有 | 4 主题各 `grep -c "composition_program" theme.md` = 1 |

---

## 3. batch-3 关键修复

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

---

## 4. batch-3 经验教训 + 100% 防范清单

### 4.1 batch-3 踩过的 5 个坑

| # | 坑 | 根因 | 修复 | 代价 |
|---|---|---|---|---|
| 1 | **G10 成了死文档** | G10 写进 theme.md 但 SKILL.md 0 引用——agent 不读 G10 | SKILL.md Step 1/2/4 补入硬规则 + index.md L8 行 | 5 轮迭代才发现 |
| 2 | **从零重写布局丢掉骨架框架层** | 构建 sampler 时用 `padding:0` + 绝对定位面板，丢了 `--slide-pad`/`.mastfoot`/`.reveal` | 保留 gallery 骨架框架 CSS，只追加截图修复 CSS | 3 轮迭代 |
| 3 | **用错内容源** | 用了 gallery 的 cover 内容（"想象的形状"）而非 sampler 的 claim 内容（"山禾集"） | 确认内容源：`assets/theme-sampler/` 截图 = 原版 sampler = 山禾集业务汇报 | 2 轮迭代 |
| 4 | **保留老布局丢掉 G10 优化** | 从原版 sampler 原样提取 HTML，但原版是 G10 之前的布局（横排等权三格 KPI） | 布局必须按 G10 `info_grammar.claim` 契约重构，只保留骨架框架层 + 内容 | 1 轮迭代 |
| 5 | **E3 中轴金框未严格居中** | invariant 说"中轴对称"但未明确 flex:1 等宽约束，左右栏用 padding-only | invariant 补入 flex:1 等宽约束 + sampler 修复 | 用户目视发现 |

### 4.2 100% 防范清单（v2 的 12 条 + batch-3 的 5 条 = 17 条）

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

### 4.3 theme-sampler 制作 SOP（batch-3 确立）

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
| **批次 4** | **C2 暗夜植物园 / C4 纸与墨 / D1 奶油物语 / D3 手绘油彩** | **⬜ 待做** | **下一批** |
| 批次 5 | E1 孔版印刷 / E8 号外报纸 / E9 地质地层 / E10 星图 | ⬜ 待做 | |
| 批次 6 | E11 票据 / E12 商务粗野 / F2 霓虹夜行 / F3 暮色长镜 | ⬜ 待做 | |
| 批次 7 | A1 电子杂志 / D2 柔光暗房 / D4 (待定) / G1 翡翠年鉴 | ⬜ 待做 | |
| 批次 8 | E7 复核 / 17 套无 G10 主题补写 G10 | ⬜ 待做 | 尾批：补全 + 复核 |

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

## 6. 下一批（批次 4）主题预览

| 主题 | 分类 | 气质 | 预期 G10 方向 |
|------|------|------|-------------|
| C2 暗夜植物园 | texture | 暗底 + 暖金 + 植物图鉴 | 图鉴卡阵 + 编号签 + 标本引线脚注 + 叶脉侧缘 |
| C4 纸与墨 | texture | 居中书籍版式 + 首字下沉 + 引文拉页 | 题花 + 首字下沉首段 + 引文拉页理念行 |
| D1 奶油物语 | texture | 圆角弥散 + 贴纸徽章 + 扇贝花边 | 圆角弥散卡片阵 + 贴纸徽章 + 奶油圆点 |
| D3 手绘油彩 | texture | 楷体 + 纸面晕染 + 笔触块 + 不规则圆角切片 | 笔触块标题 + 虚线圈注 + 不规则圆角切片右栏 |

> 4 套均为 texture 分类——需要在质感（grain/paper/glow）维度上与已有 13 套同时分化。

---

## 7. 本机环境备忘

- shell shim 缺 `dirname/head/tail/ls/mkdir/cat/sed`，命令不接管道；用托管 Node `fs` / `child_process.execFileSync` 代替
- Playwright：托管 Node + `playwright-core@1.65.0`（装在 `~/.workbuddy/binaries/node/workspace/node_modules`）+ 系统 Chrome `C:/Program Files/Google/Chrome/Application/chrome.exe`
- `.gitignore` 用 `/docs/*` + `!/docs/progress/` 白名单；**绝不用 `git add -A`**
- 提交默认**只到本地、不 push**
