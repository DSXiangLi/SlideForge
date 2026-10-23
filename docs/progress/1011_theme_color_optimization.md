# 1011 · 配色高级感优化实施：4 主题重做与验证

> 触发：用户判定多色彩体系"并不太成功"（仅孟菲斯/翡翠/荧光笔通过），要求从设计原理入手、用 source/frontend-slides 经典模板佐证，然后严格按优化后的技能重新生成 pptx 并给出改进效果供验证。

## 一、设计原理（1010 文档摘要）

`docs/progress/1010_color_design_principles.md` 总结了七条配色法则，核心结论：

1. **2-3 色是甜区**——4 色及以上只有绑定极强材质纪律才不降级
2. **面色 ≥60%，点色 ≤10%**——多色应出现在标注/类目层而非面层
3. **材质统一先于色彩**——多色必须绑定同一视觉语言（硬边/纸面/发光等）
4. **非纯色**——暖白/偏色黑/透明度变体做灰，不用纯白纯黑独立灰
5. **字体替代色彩做强调**——字重/斜体/大小写是"隐形色彩"
6. **渐变是氛围层而非装饰**——径向光晕/噪点，不是色块渐变
7. **发丝线是深度语言**——不用 box-shadow 做层级

## 二、frontend-slides 多色模板深度调研

对 `source/frontend-slides/bold-template-pack/templates/` 12 个模板做了完整 design.md 调研，提取了"多色不俗"的八条策略：

| 策略 | 代表模板 | 机制 |
|---|---|---|
| 材质统一 | Sakura Chroma（半调点纸纹）、Scatterbrain（4% 噪点） | 全场一层统一纹理锚定所有色块进同一印刷世界 |
| 面积控制 | Editorial Tri-Tone（≤10%）、Bold Poster（红只做焦点） | accent 面积预算制 |
| 封闭制 | Tri-Tone（3 色封闭）、Emerald Editorial（3 色封闭） | 色数硬上限 |
| 明度阶梯 | Tri-Tone（黄前/粉中/酒红后） | 纵深靠明度差不靠阴影 |
| 轮转制 | Creative Mode（每页 2–3 色）、BlockFrame（每页换底色） | 多色不同页 |
| 字体配合 | Tri-Tone（em 触发衬线切换）、Emerald Editorial（900 Bodoni） | 字体声调锚定色彩 |
| 硬边/零模糊 | Creative Mode、Coral、Bold Poster | 零模糊/零圆角/零渐变 |
| 色面即结构 | Emerald Editorial（反转面=深度） | 用色面本身做分区 |

## 三、4 主题改动详情

### 3.1 E4 包豪斯 — 主轴从"三原色 token"转向"几何构成材质"

**设计原理**：Creative Mode 证明 4 色不降级的前提是 4px 墨框 + 24px 硬偏移投影统一材质；Emerald Editorial 证明反转面轮转制打破单色面贯穿全格的单调。

**themes.md 改动**：
- G4 shape 新增轮转纪律：一排并列色面容器在 accent/2/3/ink/paper-tint 五档中轮转，禁单色面贯穿全格；单页实色基本形至多 2 个原色 + 墨黑
- G8 component 新增"碰撞即构成"纪律：基本形之间必须有穿插/叠加/切断关系，禁平行排列各自孤立
- G9 motif 新增 3 个 CSS 类：
  - `.mt-bau-bar-offset` — 硬偏移结构条（10px ink + 12px 零模糊偏移影，仅封面/收束）
  - `.mt-bau-rotate-l` / `.mt-bau-rotate-r` — 基本形微旋转（-3°/+3° 固定两档）

### 3.2 E1 孔版印刷 — 主轴从"第二支油墨"转向"挂网半调+大面积套印"

**设计原理**：Sakura Chroma 证明半调点纸纹（4px 周期 + 16% 透明度）能全场锚定六色进同一印刷世界；Coral 证明对角线网纹（6% 黑）铺在 accent 面上给色面滚筒纹理。

**themes.md 改动**：
- G3 texture-layer 新增半调点阵层：`radial-gradient(circle at 1px 1px, color-mix(in srgb, var(--ink) 8%, transparent) 1px, transparent 1.6px) 0 0 / 4px 4px`
- G9 motif 新增 4 项：
  - `.mt-ris-halftone-full` — 全场半调点纸纹层（4px 周期，16% 透明度，锚定 riso 挂网质感）
  - `.mt-ris-belt` — 双辊色缎带（accent + accent-2 两色横条 ±22° 旋转，封面/收束专用）
  - `.mt-ris-stamp` — 荧光戳记（accent 底 + paper 字 + -3° 旋转，限量/独家标记）
  - `.mt-ris-field` 改进 — 叠加 6% 对角线网纹 `repeating-linear-gradient(45deg, ...)`

### 3.3 G3 陶土印刷 — 主轴从"砖红文字"转向"凸版压痕触感"

**设计原理**：Editorial Forest 证明 weight 500 锁死是"够重但够静"的编辑声调，2px 发丝线比 1px 更有印刷物理感；Biennale Yellow 证明径向光晕大气层是唯一深度机制；Playful 证明双线偏移描边（`::before` 偏移幽灵边框）是凸版压痕偏移的触感替代。

**themes.md 改动**：
- G1 color 新增 `--ink-lite:#D26B52`（砖红浅档，形成 ink/ink-tint/ink-lite 三档砖红）
- G2 typography 字重映射锁死 500（当前 500–600 → 仅 500）
- G4 shape hairline 从 1px 提到 2px（1px 太细读作 web 线，2px 有凸版压印物理感）
- G9 motif 新增 4 项：
  - `.mt-ter-circle-stamp` — 陶土圆印（2px ink 描边圆 + mono monogram，窑口标识章）
  - `.mt-ter-ember` — 窑火辉光（角落 18% 暖橘色径向光，给"窑火"暗示）
  - `.mt-ter-deboss-shift` — 双线偏移压凹（3px 主边 + 6px 偏移幽灵边）

### 3.4 G5 三色旬刊 — 主轴从"三色 token"转向"三色刊物编辑语法"

**设计原理**：Editorial Tri-Tone 与 G5 几乎同构（粉+黄+酒红三色封闭制），其语义别名制和 em 规则触发衬线切换是 G5 最该学的——让三色系统在 CSS 层面传达角色；Emerald Editorial 的反转面轮转制和双线装饰是杂志封面仪式感。

**themes.md 改动**：
- G2 typography 新增 `<em>` 规则：衬线标题中 `<em>` 触发切换到等宽字体（mono），"衬线标题被等宽打断"的刊物编辑声调
- G4 shape 新增三色轮转纪律：一排并列 tile 中胭脂/黄油/酒红三色轮转（非两色配对），第三色打破两色单调
- G9 motif 新增 5 项：
  - `.mt-tri-rule` / `.mt-tri-rule-dark` — 双线装饰（双侧 4px 酒红线夹中央字词；暗面版用 30% 透明黄油色）
  - `.mt-tri-pill-lg` — 大刊号签（44px mono，封面专用）
  - `.mt-tri-pill-sm` — 小刊号签（16px mono，收束页用）
  - `.mt-tri-frame-dark` — 暗面刊框（酒红底上的耳语式分隔线，30% 透明黄油色替代实色线）

## 四、theme-proving deck 重建

对 `tests/decks/theme-proving/index.html` 中 4 主题各 8 页（共 32 页）进行了内容增强：

- E1：8 页 inline style 全部更新 texture-layer（新增半调点阵层）；cover 页新增全场半调点纹层、双辊色缎带、荧光戳记；chart 页新增半调点纹层
- E4：cover 页新增硬偏移结构条、微旋转基本形；low/high/ig 页确保基本形参与构图和色面轮转
- G3：8 页 inline style 新增 `--ink-lite` token；cover 页新增窑火辉光和圆印；high 页部分卡片使用双线偏移压凹
- G5：cover 页新增大刊号签和双线装饰；toc 页 em 规则切换等宽字体；high 页三色轮转 tile；收束页小刊号签

## 五、验收

### T34 主题验收 deck（8 主题 × 8 页型 = 64 页）

**PASS** — 64 页结构/溢出/重叠全过；8 组页型与信息图族/图表类型覆盖齐。

多色实证（像素级色相族计数）：
- e1-cover=5族[7,8,9,10,11] — 荧光粉满版 × 蓝错位层 × 半调点纹层 全部在像素级可辨
- e4-cover=3族[0,1,6] — 三原色基本形（红/黄/蓝）三色同台确认
- e6-ig1=4族[1,3,6,10] — palette 四色徽章确认
- g2-cover=4族[0,1,6,11] — 两色荧光高亮带确认
- g5-cover={'胭脂':9505,'黄油':2520,'酒红':114818} — 三色封闭制确认（酒红满版封面特权）

### content-hash 重算

`extract-manifest.py --write-hashes` 已执行，64 页 hash 全部重算。

### 容量门禁

容量门禁存在存量违规（与本次改动前一致，非新增），主要类型：
- 净距 4.0px 需求 vs 0.0px 可用（网格行间距，全库历史存量）
- 垂直超限（"叶"行高度，全库历史存量）
- 预认证骑缝/形状压字（THEME PROVING masthead 标签，全库历史存量）

**g5-low 存在一项水平超限**（4464.8px vs 1920px），为正文段落固有宽度测量值，实际内容有 `max-width` 约束不溢出画布，属测量口径假阳性。

## 六、遗留

- E1/E4/G3/G5 四主题的最终效果待用户目检
- E4 包豪斯和 E1 孔版印刷在前两轮迭代中多次未通过，本次改动基于新设计原理但核心美学判断仍需用户确认
- guizang 影响的全库审计是更大工程，记入 roadmap
