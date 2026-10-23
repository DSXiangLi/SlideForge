# 1015 · 主题材料合成优化计划

> **前置阅读**：`docs/learnings/visual-material-compositing.md`（设计原理）→ `docs/progress/1012_theme_essence_thinking.md`（guizang 骨架污染诊断）→ 本文档（执行计划）。
>
> 来源：2026-10-15 外部视觉风格参考项目深度对比分析（33+25 封面/海报风格的材料语言、构图策略、反惰性纪律），结论：当前系统 35 种 CSS 合成技术只用了约 5 种，G3/G9 层的材料表达深度是视觉出挑度的最大瓶颈。

---

## 一、总体路线

```
Phase 0  材料合成词汇表（前置依赖）
    ↓
Phase 1  主题 Schema 扩展（material_world / G3 升级 / title_role / reveal_sequence / anti_lazy）
    ↓
Phase 2  主题材料规格填充（三批次）
    ↓
Phase 3  bake 层 brief 补全 + 融合强化
    ↓
Phase 4  验证（渲染门禁 + 导出轨道 + 截图对比）
```

---

## 二、Phase 0：材料合成词汇表

**新建 `references/compositing.md`**——HTML 层材料合成配方库。结构仿照 motion.md 的 recipe 模式，收录 15–20 个配方。

每个配方的字段：

```
## 配方 X：配方名（模拟材料）

- **材料**：什么物理材料
- **CSS 实现**：完整代码块（可直接复制使用）
- **适用层**：背景 / 容器 / 装饰 / 文字
- **密度兼容**：全密度 / 仅低密度仪式页 / 仅装饰层
- **导出**：保真轨保留 / 可编辑轨丢失 / 待实测
- **主题亲和**：哪些主题世界参考天然匹配
```

### 首批配方清单（15 个）

| # | 配方名 | 模拟材料 | 核心技术 |
|---|---|---|---|
| 1 | overprint-flat | 珐琅/丝网印刷平面 | 纯色 + `mix-blend-mode: multiply` |
| 2 | riso-misreg | 孔版套色错位 | multiply + offset transform + isolation（E1 已有，泛化入库） |
| 3 | halftone-dots | 半调网点 | `radial-gradient` 点阵 + `background-size` |
| 4 | paper-fiber | 纸张纤维 | `feTurbulence` + `feColorMatrix` data-URI |
| 5 | emboss-deboss | 击凸/压凹 | 双侧 `drop-shadow`（暖影+高光） |
| 6 | watercolor-bleed | 水彩晕染 | `radial-gradient` + `blur(8-20px)` + `multiply` |
| 7 | film-grain | 胶片颗粒 | `feTurbulence` 高频 + 低透明度 |
| 8 | light-leak | 漏光/光斑 | `radial-gradient` 大光斑 + `blur(40-60px)` + `screen` |
| 9 | spotlight-mask | 聚光灯 | `mask-image: radial-gradient` |
| 10 | aged-fade | 做旧褪色 | `sepia() contrast()` + 颗粒 + `soft-light` |
| 11 | engraved-line | 金属刻痕 | `repeating-linear-gradient` 细线 + `box-shadow: inset` |
| 12 | ink-bleed | 墨迹洇开 | `feMorphology` dilate + `feGaussianBlur` |
| 13 | torn-edge | 撕裂边缘 | `clip-path: polygon()` 不规则轮廓 |
| 14 | reflection-fade | 倒影渐隐 | `scaleY(-1)` + `mask-image: linear-gradient`（F2 已有，泛化入库） |
| 15 | organic-stroke | 手绘笔触 | `feTurbulence` + `feDisplacementMap` 作用于描边 |

**验收**：sync-themes.mjs schema 同步；harness 新增检查项。

---

## 三、Phase 1：主题 Schema 扩展

在 theme.md 字段组中新增四个字段：

### 3.1 G0 新增 `material_world`

```yaml
material_world: "1960s Swiss railway enamel signage under fluorescent station light — painted steel, glossy enamel, crisp screen-print ink"
```

一句话物理世界描述。G3 的 CSS 配方选型和 bake_brief 的 uplift 都从这个锚点推导。

### 3.2 G3 升级：从类型标签到材料规格

当前：
```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

升级后（增加三个字段，原有字段保留向后兼容）：
```yaml
texture:
  # 原有三字段不变
  material: "painted steel with screen-print ink"   # 新增：物理材料描述
  light: "overhead fluorescent, even, no direction"  # 新增：光线条件
  css_recipes: ["overprint-flat", "halftone-dots"]   # 新增：compositing.md 配方选型
  stance: "flat with physical substrate — the flatness of enamel, not the flatness of pixels"
```

### 3.3 G2 新增 `title_role`

```yaml
title_role:
  cover: "architecture"       # 标题即建筑——透视/遮挡/材质化（仅低密度）
  key_message: "hero"         # 巨字主角——标准渲染，极端字级
  analysis: "editorial"       # 编辑排版——正常字号
  analysis_ghost: true        # 允许背景层 Ghost 核心词（低透明巨字）
```

按页面角色分级标题策略，不是一刀切。`analysis_ghost` 泛化 A1 Ghost 字模式为系统级合法技法。

### 3.4 G5 新增 `reveal_sequence`

```yaml
reveal_sequence:
  - "ambient: 背景光晕/质感层先出现（fade-in, 300ms）"
  - "title: 标题/焦点元素第二位（主题签名入场）"
  - "content: 正文/数据最后（rise-in / wipe-clip）"
```

### 3.5 G0 新增 `anti_lazy`

```yaml
anti_lazy:
  - "不要把十字标当装饰花边撒满页面——只许四角和内容区角点"
  - "不要用 IKB 蓝以外的高饱和色做焦点"
```

每个主题 2–3 条，格式"不要因为___就___"。

---

## 四、Phase 2：主题材料规格填充（三批次）

### 第一批：材料映射最清晰（5 主题）

| 主题 | 世界参考 | 材料配方选型 | 预期提升 |
|---|---|---|---|
| **D1 奶油物语** | 甜品店/生活方式杂志 | emboss-deboss + paper-fiber | "圆角卡片+软阴影" → "纸面击凸触感" |
| **D2 暗房** | 胶片暗房 | film-grain + light-leak + aged-fade | "暗色底" → "胶片质感+漏光" |
| **C2 植物园** | 植物标本/水彩 | watercolor-bleed + organic-stroke | "绿色主题" → "水彩纸面" |
| **C1 信号黑** | 黑色舞台+聚光灯 | spotlight-mask + hard-light blend | "黑底橙字" → "聚光灯下的舞台" |
| **B1 瑞士国际** | 珐琅牌面/丝网印刷 | overprint-flat + registration-mark | "白底蓝块" → "珐琅牌面物质感" |

### 第二批：中等映射难度（5–8 主题）

E4、E5、E7、E8、E9、E10、E11、G2、G4——每个主题根据世界参考推导材料配方。

### 第三批：已完成或低优先级

E1/E6/F1/F2/F3/G5（已有深度）、E12、C3、A1、E3（已有 bake_brief，HTML 层材料可再深化）。

---

## 五、Phase 3：bake 层 brief 补全 + 融合强化

### 3a. 回退路径结构化

修改 `compile-bake-prompts.py` 回退路径（无 bake_brief 的主题），从"散文 + token 色值"升级为最小结构模板：

```
material_anchor: {{theme.material_world}}
uplift_hints: [至少 2 个升维方向]
anti_lazy: [theme.anti_lazy 直接引用]
viewing_sequence: [第一眼/近看/理解 三层]
```

### 3b. bake_brief 增加 `viewing_sequence` 字段

```json
"viewing_sequence": [
  "第一眼：整体剪影与视觉中心——远看效果",
  "第二眼：材质细节与纹理——近看发现",
  "第三眼：文字与信息——理解内容"
]
```

### 3c. 第一批 5 主题补齐完整 bake_brief

D1/D2/C2/C1/B1 补齐 visual_direction / palette_rule / typography_bake / uplift / allowed / avoid / layout_blueprints / viewing_sequence / material_anchor。

---

## 六、Phase 4：验证

| 验证项 | 内容 | 工具 |
|---|---|---|
| 渲染门禁 | 新合成技术不破坏渲染（backdrop-filter 在 print 下的表现需实测） | `check-render` |
| 容量门禁 | 材料层不影响容量计算 | `check-capacity` |
| 主题验收 | 第一批 5 主题各出 8 页 theme-proving deck | theme-proving 结构/几何/多色三闸 |
| 截图对比 | 非 reduced-motion 模式（JS null 检查红线不变） | Playwright |
| 保真轨导出 | mix-blend-mode / filter / mask 在 PDF→SVG 管线中的表现 | `export-pptx.py --track vector` |
| 可编辑轨导出 | 可编辑身份（色+字+形）独立于保真身份 | `export-pptx.py --track editable` |
| harness 回归 | 全量 61 项 | `python3 tests/harness/run_e2e.py` |

---

## 七、与既有计划的关系

- **1012/1013 主题本质重建**：本计划是同一方向的第二阶段。1012 解决"骨架污染"（结构层），本计划解决"材料贫乏"（表现层）。两者叠加 = 完整的主题深度。
- **F 系光学轴**：F1/F2/F3 已证明合成技术可以支撑主题身份。本计划把这个能力从 3 个主题扩展到全库。
- **G 系多色**：多色是色彩结构的扩展，本计划是材料结构的扩展——两者正交，不冲突。
- **bake 风格圣经 D1–D3**：本计划的 Phase 3 是 D1–D3 的延续，把 bake_brief 从 5 主题扩展到更多主题。
