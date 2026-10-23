# HANDOVER：主题材料合成优化——试点验证

> 日期：2026-10-15 · 交接对象：全新 session
>
> **目标**：验证材料合成优化方向——优化 1 个既有主题 + 新增 1 个主题，用户验收确认后再推进全量。
>
> **前置阅读**（按序）：
> 1. `AGENTS.md` — 项目全貌与红线
> 2. `docs/learnings/visual-material-compositing.md` — 7 条设计原理（材料语言/合成技术目录/标题角色分级/观看序列/反惰性/边缘裁切/双层身份）
> 3. `docs/progress/1015_theme_material_compositing_plan.md` — 五阶段完整计划
> 4. `docs/progress/1012_theme_essence_thinking.md` — 主题本质问题诊断（guizang 骨架污染）
> 5. `docs/progress/1013_theme_essence_progress.md` — 已有主题重建进度
>
> 本文档 = 试点任务定义 + 执行步骤 + 验收标准。

---

## 一、试点任务

### 任务 A：优化既有主题——D2 柔光暗房

**选它的理由**：

| 维度 | 评估 |
|---|---|
| 材料映射清晰度 | **极高**——世界参考就是"摄影暗房与胶片工艺"，材料语言（胶片颗粒/漏光/显影/做旧）有明确的 CSS 配方对应 |
| 当前差距 | **大**——G9 母题只有 3 个简单件（齿孔条/光束角标/显影晕），没有胶片颗粒（feTurbulence）、没有漏光（screen blend）、没有做旧（sepia+contrast）——"暗房"目前只是"暗色底" |
| 视觉提升预期 | **戏剧性**——从"黑底琥珀光"升级为"胶片物质感：颗粒纹理 + 漏光光斑 + 做旧色调 + 显影纵深" |
| 重建状态 | 未重建（不在 E1/E4/E6/G5 已完成的 4 主题中）——验证材料合成对未重建主题的提升路径 |
| bake_brief | 无——同时验证回退路径结构化改造 |

**不改什么**：配色（G1）、字体栈（G2）、页角色蓝图、分化声明、动效签名（G5 已有 blur-in 显影，方向正确只需保留）。

**改什么**：G3 质感层升级为材料规格 + G9 母题增加合成技术配方 + 补全 bake_brief。

### 任务 B：新增主题——D4 黄铜年代（Brass Age）

**选这个方向的理由**：

| 维度 | 评估 |
|---|---|
| 谱系空缺 | 28 个主题中没有"中世纪工业乐观主义"世界——E3 是 1920s Art Deco、E5 是 1920s 苏联构成主义、E2 是工程蓝图（但是现代冷调），1950s–60s 太空时代/世博会/工业乐观完全空白 |
| 材料独特性 | 涂漆钢 + 黄铜配件 + 蓝图纸 + 丝网印刷——使用 engraved-line、halftone-dots、aged-fade、paper-fiber 四种配方，全部未被现有主题使用 |
| 视觉辨识度 | 极高——黄铜金属色 + 深蓝图纸底 + 红色标注线，三色系统与所有现有主题零撞脸 |
| 受众适用面 | 科技发布/工程/制造/基础设施/航天——当前库缺少"工业乐观"气质的主题 |
| 合成技术展示 | 最多——可以同时展示 engraved-line（刻痕）、halftone-dots（网点）、aged-fade（做旧）、paper-fiber（纸纤维）四种配方 |

**分类归属**：`texture/`（质感类）

---

## 二、执行步骤

### Phase 0：材料合成词汇表（前置依赖，两个任务共用）

新建 `skills/html-pptx/references/compositing.md`，收录首批 15 个配方。结构仿照 `motion.md` recipe 模式。

**文件结构模板**：

```markdown
# 材料合成词汇表（Compositing Recipes）

> 读者：执行主题重建/新建主题的 AI coding agent。
> 用途：G3 质感层升级与 G9 母题块的材料配方选型——每个配方是"用 CSS 合成技术模拟一种物理材料"的完整实现。

## 配方 1：overprint-flat（珐琅/丝网印刷平面）
- **材料**：涂漆钢板上的丝网印刷油墨——平整但有物理厚度
- **CSS 实现**：（完整代码块）
- **适用层**：背景 / 容器 / 装饰
- **密度兼容**：全密度
- **导出**：保真轨保留（PDF transparency group）/ 可编辑轨丢失
- **主题亲和**：B1 瑞士、E2 蓝图

## 配方 2：riso-misreg（孔版套色错位）
...
```

**15 个配方清单**（详见 `docs/progress/1015_theme_material_compositing_plan.md` §二）：

overprint-flat / riso-misreg / halftone-dots / paper-fiber / emboss-deboss / watercolor-bleed / film-grain / light-leak / spotlight-mask / aged-fade / engraved-line / ink-bleed / torn-edge / reflection-fade / organic-stroke

**验收**：每个配方有可直接使用的 CSS 代码块 + 材料描述 + 导出轨道标注。sync-themes.mjs schema 同步（新增 `css_recipes` 字段的校验）。

### 任务 A 执行步骤：D2 柔光暗房材料升级

**Step A1：读取当前 D2 theme.md**

路径：`skills/html-pptx/references/themes/light/d2/theme.md`

**Step A2：G3 质感层升级**

当前：
```css
--texture-type: glow;
--texture-layer: radial-gradient(120% 90% at 70% 10%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 60%);
--texture-scope: cover;
```

升级为材料规格（保留原有三字段向后兼容，新增材料描述字段）：

```yaml
# 原有三字段不变

# 新增：材料规格
material: "胶片相纸——银盐乳剂面的微颗粒，安全灯琥珀光下的显影液反光"
light: "安全灯单点光源——琥珀色、低亮度、有方向性，从上方 70° 投射"
css_recipes: ["film-grain", "light-leak", "aged-fade"]
```

**Step A3：G9 母题增加材料配方**

在现有 3 个母题件（`.mt-drk-film` / `.mt-drk-beam` / `.mt-drk-halo`）基础上，新增材料配方件：

1. **`.mt-drk-grain`**——胶片颗粒层：`feTurbulence` data-URI 作为背景图，覆盖整个页面或指定区域，opacity 0.03–0.06，模拟银盐颗粒。仪式页用较大颗粒（`baseFrequency="0.9"`），正文页用细颗粒（`baseFrequency="0.6"`）。

2. **`.mt-drk-leak`**——漏光光斑：`radial-gradient` 不规则光斑 + `filter: blur(30–50px)` + `mix-blend-mode: screen`。琥珀/暖橙色，只许页面上缘或侧缘，opacity ≤0.15。每页至多 1 个，只许仪式页。

3. **`.mt-drk-aged`**——做旧色调：微量 `filter: sepia(0.08) contrast(0.97)` 作用于页面背景层（不影响文字可读性），模拟胶片相纸的微微泛黄。只许仪式页。

**Step A4：G0 新增字段**

```yaml
material_world: "摄影暗房——安全灯琥珀光下，银盐相纸在显影液中浮现，胶片齿孔记录时间，空气中有药液微粒"
anti_lazy:
  - "不要因为是暗色主题就加星空/宇宙元素——暗房不是夜空"
  - "不要因为是胶片就加电影院银幕边框——齿孔条只许一条，不许变成画框"
  - "不要用高亮度白光——暗房唯一的光源是安全灯，白光会毁了这个主题"
```

**Step A5：补全 bake_brief**

D2 当前无 bake_brief。按 D1 风格圣经格式补全，包含：

```json
{
  "visual_direction": "摄影暗房的物质感——银盐相纸颗粒、安全灯琥珀光晕、显影液反光、胶片齿孔，暗底上一切从柔光中浮现",
  "palette_rule": "深棕黑底 + 暖米白文字 + 琥珀金 accent 三色系统；琥珀是安全灯的光不是颜料，面积 ≤5%",
  "typography_bake": "衬线标题如相纸显影——从模糊到清晰的显影过程定格在最清晰的一帧；断行在语义边界",
  "uplift": "银盐颗粒的物理肌理——不是数字噪点，是乳剂层的微晶体在光下的反光；显影液的光学折射——光斑边缘有色散；相纸的白边与齿孔的物理厚度",
  "material_anchor": "银盐相纸 + 安全灯琥珀光 + 显影液光学",
  "viewing_sequence": [
    "第一眼：暗场中一团琥珀辉光和标题剪影",
    "第二眼：发现胶片颗粒纹理和齿孔边带",
    "第三眼：阅读文字，感受暗房的安静时间感"
  ],
  "anti_lazy": ["不要加星空/宇宙元素", "不要加电影银幕边框", "不要用高亮度白光"],
  ...
}
```

**Step A6：更新 theme-proving deck**

在 `tests/decks/theme-proving/` 中为 D2 出 8 页验收 deck，验证新材料规格在各页型上的表现。

### 任务 B 执行步骤：D4 黄铜年代新建

**Step B1：主题定义**

新建 `skills/html-pptx/references/themes/texture/d4/theme.md`：

```yaml
id: d4
气质: "深蓝图纸 + 黄铜刻线 + 红色标注——1950s 世博会工业乐观主义，钢铁的时代相信未来"
适用: 科技发布 / 工程 / 制造 / 基础设施 / 航天 / 工业品牌
focus: G9 + G3
世界参考: "1950s 世界博览会展馆海报与太空时代工业设计——涂漆钢板、黄铜铆钉、蓝图晒图纸、丝网印刷宣传画"
unforgettable: "黄铜刻线框——双线黄铜色刻痕边框，内凹刻槽感，每个容器像从钢板上刻出来的"
分化声明: 与 e2 蓝图分化于 L1/L2/L3/L4/L5/L6——d4 暖调黄铜 + 深蓝图纸，e2 冷调青蓝 + 白线；d4 有金属刻痕与做旧颗粒，e2 纯净白线；d4 母题是铆钉/刻线/锈斑，e2 是尺寸标注线/图框标题栏
```

**G1 color**：
```css
--paper:#1a2332; --paper-tint:#243044;  /* 深蓝图纸底 */
--ink:#e8dcc8;   --ink-tint:#3a4a5e;    /* 图纸暖白 */
--accent:#b8860b; --accent-on:#1a2332;   /* 黄铜 */
```

**G2 typography**：Condensed grotesk 风格标题 + 无衬线正文 + mono 标注。标题 600–700 恒重（工业重量感）。

**G3 texture**：材料规格——
```yaml
material: "涂漆钢板 + 黄铜铆钉 + 蓝图晒图纸"
light: "展馆顶灯——均匀但有微弱方向性，金属面有高光"
css_recipes: ["engraved-line", "halftone-dots", "aged-fade", "paper-fiber"]
```

**G4 shape**：直角 + 黄铜刻线边框（`border: 2px solid` + `outline: 1px solid; outline-offset: 3px`，黄铜色）。

**G9 motif**：
1. `.mt-brs-rivet`——黄铜铆钉：小圆点（6px），金属渐变（`radial-gradient` 模拟球面），钉在容器角上
2. `.mt-brs-engrave`——刻线边框：`repeating-linear-gradient` 细线模拟刻刀痕 + `box-shadow: inset` 内凹感
3. `.mt-brs-stamp`——红色标注印章：`border: 2px solid` 红色 + `transform: rotate(-3deg)` 微倾斜 + mono 大写文字
4. `.mt-brs-grid`——蓝图网格：`linear-gradient` 双向 1px 线，低透明度，只许仪式页背景

**G5 motion**：professional——wipe-clip 精确揭示（像蓝图展开）+ count-up（工程数据）。

**Step B2：配色变体（≥3 套）**

1. **黄铜蓝**（基底）：深蓝图纸底 + 黄铜 accent
2. **锈红**：深棕底 + 锈红 accent——更旧的工业感
3. **橄榄绿**：深橄榄底 + 黄铜 accent——军事/野外工程感

**Step B3：bake_brief 完整编写**

包含全部字段：visual_direction / palette_rule / typography_bake / uplift / material_anchor / viewing_sequence / anti_lazy / allowed / avoid / layout_blueprints / rendering_constraints。

**Step B4：入库校验**

sync-themes.mjs 校验：Schema 合规 + 两两七层 diff ≥3 + 差异化声明真实性。

**Step B5：theme-proving deck**

8 页验收 deck（封面/目录/关键信息/分析/数据/对比/流程/收束）。

---

## 三、验收标准

### D2 优化验收

| 项 | 标准 | 验证方式 |
|---|---|---|
| 材料感 | 页面截图中可见胶片颗粒纹理（不是纯色暗底） | 截图对比（非 reduced-motion） |
| 漏光 | 仪式页有琥珀色光斑，blend-mode: screen 生效 | 截图对比 |
| 做旧 | 仪式页背景有微泛黄做旧感 | 截图对比 |
| 不劣化 | 正文可读性不降、信息层级不变 | check-render + 目检 |
| 导出 | 保真轨 PDF→SVG 中颗粒/漏光可见 | export-pptx.py --track vector |
| 可编辑轨 | 可编辑轨正常导出（颗粒/漏光丢失为预期行为） | export-pptx.py --track editable |
| harness | 全量回归 PASS | run_e2e.py |
| content-hash | 更新 | extract-manifest.py --write-hashes |

### D4 新建验收

| 项 | 标准 | 验证方式 |
|---|---|---|
| Schema | G0–G9 + variants + bake_brief 全字段完整 | sync-themes.mjs |
| 差异化 | 与全部 28 个现有主题两两七层 diff ≥3 | sync-themes.mjs |
| 材料感 | 刻线/铆钉/做旧在页面截图中可见 | 截图（非 reduced-motion） |
| 一眼辨识 | 与所有现有主题零撞脸——一眼能认出"这是黄铜年代" | 目检 |
| theme-proving | 8 页 deck 通过结构/几何/多色三闸 | T34 |
| harness | 全量回归 PASS | run_e2e.py |

---

## 四、关键文件路径

| 用途 | 路径 |
|---|---|
| 设计原理 | `docs/learnings/visual-material-compositing.md` |
| 完整计划 | `docs/progress/1015_theme_material_compositing_plan.md` |
| D2 主题 | `skills/html-pptx/references/themes/light/d2/theme.md` |
| 主题索引 | `skills/html-pptx/references/themes/index.md` |
| Schema 校验器 | `skills/html-pptx/scripts/sync-themes.mjs` |
| 骨架 | `skills/html-pptx/assets/skeleton.html` |
| 组件参考 | `skills/html-pptx/references/components.md` |
| 动效参考 | `skills/html-pptx/references/motion.md` |
| 排版参考 | `skills/html-pptx/references/typography.md` |
| bake 指令参考 | `skills/html-pptx/references/bake-prompts.md` |
| theme-proving 验收 | `tests/decks/theme-proving/` |
| 主题样张 gallery | `skills/html-pptx/gallery/index.html` |
| E2E 回归 | `tests/harness/run_e2e.py` |

---

## 五、用户验收后推进

用户确认 D2 优化 + D4 新建方向可行后，按 `1015_theme_material_compositing_plan.md` Phase 2–4 继续：

1. **第二批**（5–8 主题）：E4/E5/E7/E8/E9/E10/E11/G2/G4 材料规格填充
2. **Phase 3**：bake 层 brief 补全（回退路径结构化 + viewing_sequence 字段）
3. **Phase 4**：全量验证
