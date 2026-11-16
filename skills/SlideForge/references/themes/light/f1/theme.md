# F1 浮光玻璃

- **id**：f1
- **气质**：晨雾冷白 + 蓝紫环境光斑 + 悬浮玻璃卡——光是背景，玻璃是容器，层级靠透明
- **适用**：产品发布、SaaS 与消费科技、设计驱动的品牌叙事、年轻化商务汇报
- **focus**：G3 + G4
- **世界参考**：macOS / iOS 的毛玻璃材质体系（壁纸光斑 + 控制中心半透明叠层）——界面悬浮在彩色环境光之上，层级由透明度而非线条表达
- **unforgettable**：玻璃卡浮在光斑上——内容承载在半透明容器里，背后的环境光透过玻璃漫上来
- **分化声明**：与 d1 分化于 L1/L3/L4/L5——d1 是暖奶纸底 + flat 平色 + 贴纸/扇贝花边母题 + 不透明奶油圆角色块卡（单层软影）；f1 是冷雾底 + aura 光斑全页质感 + 玻璃卡/光斑/玻璃 chip 母题 + 毛玻璃半透明叠层容器（backdrop-filter 六件套）（L6 两者同为轻上浮系，不计入分化）

**G1 color**

```css
--paper:#EEF1F7; --paper-tint:#E0E5F0;
--ink:#15181F;   --ink-tint:#2A2F3C;
--accent:#4E63E7; --accent-on:#FFFFFF;
```

- **accent 预算**：内容页 accent 焦点一处（关键数据/主按钮级元素）——环境光斑是低透明底色不是焦点，不计入面积；满屏 accent 渐变仅封面特权（全屏光斑）；首尾闭环：封面全屏光斑开场 → 收束页同构光斑半亮呼应。

**G2 typography**

```css
--font-display:"SF Pro Display","Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 300–500（大字偏细——玻璃世界是轻的）、正文 400
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：轻倒挂立场：≥77px→300–400；35–76px→500；正文 400；14–16px 小字 500–600（玻璃上的字要稳）
- **标题修饰**：无（材质本身即修饰）
- **metric_fallback**：display→Helvetica Neue/PingFang SC；body→PingFang SC/Noto Sans SC；mono→SF Mono/Menlo

**G3 texture**

```css
--texture-type: aura;
--texture-layer: radial-gradient(42% 52% at 18% 22%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 70%), radial-gradient(38% 46% at 84% 14%, color-mix(in srgb, var(--ink-tint) 20%, transparent), transparent 70%), radial-gradient(50% 60% at 70% 88%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 72%);
--texture-scope: all;
```

- **立场**：环境光斑 = 玻璃的光源——没有光斑玻璃就失去意义，本主题正文页默认铺（scope all + 生成侧逐页 `texture-on` 落码）；强度烧死不得加深（光斑是环境不是图案）

**G4 shape**

- **圆角**：20–28px 大圆角（玻璃是连续曲面）；chip 用胶囊形
- **hairline**：半透亮边——玻璃卡的 1px 受光边 color-mix(in srgb, var(--accent-on) 65%, transparent)；不用墨色实线
- **阴影**：多层柔和投影体系（全库首发）——浮卡三件套：inset 0 1px 0 顶高光 + 0 1px 2px 近影 + 0 16px 40px −12px 远影（负 spread 收敛，影色取 ink 冷色相 ≤20% 透明）；禁硬偏移影、禁中性纯灰重影
- **容器造型**：玻璃卡（`.mt-gls-card`）六件齐上——半透明渐变底 + backdrop-filter blur(18px) saturate(150%) + 1px 半透亮边 + inset 顶高光 + 柔和外影，缺一不可（缺了像蒙灰）；禁不透明实心色块卡（挡住光斑即破坏世界）
- **高密度容器边界**：玻璃深度栈 3–4 层，沿 ≈12° 深度轴逐级错位叠压，各层 z 与不透明度档互不相同；**禁并列成阵、禁玻璃叠玻璃（无祖先-后代 backdrop-filter 嵌套）**；文字层 opacity = 1，禁对文字降透明度

**G5 motion**

- **气质**：calm
- **强度上限**：默认
- **锚点偏好**：rise-in 轻上浮（玻璃浮起）/ blur-in（雾气散开显形）；count-up 只给真正的 KPI 英雄
- **节奏偏移**：不偏移
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / wipe-clip（弹跳与硬切破坏悬浮感）
- **fx 许可**：全禁（光斑是静态材质，粒子会把玻璃世界弄脏）

**G8 component**

- **亲和**：深度栈分层（近/中/远景玻璃沿斜向轴错位，非网格矩阵）、数据英雄（沿深度轴逐级后退的三枚玻璃 chip）、图文证据（图片垫在远景层，边缘透出光斑）
- **禁忌**：禁裂屏实心色块对撞（实心色块挡光）；不用粗描边/硬偏移影/爆炸星（粗野系词汇）；图表以 accent 单系列为主，网格线用 ink 10% 极淡

**G9 motif**

- **词汇**：玻璃卡（`.mt-gls-card`——容器即材质，六件套见 G4）/ 光斑（`.mt-gls-blob`——页面级 blur 光团垫在玻璃卡后增加纵深，每页 ≤2 团）/ 玻璃 chip（`.mt-gls-chip`——胶囊形小玻璃标，标签/序号用）

```css
:root{--t-display:108px;--t-body:24px}
/* F1 浮光玻璃 · 装饰母题 */
.mt-gls-card{position:relative;border:1px solid color-mix(in srgb,var(--accent-on) 65%,transparent);border-radius:24px;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 62%,transparent),color-mix(in srgb,var(--paper) 34%,transparent));backdrop-filter:blur(18px) saturate(150%);-webkit-backdrop-filter:blur(18px) saturate(150%);box-shadow:inset 0 1px 0 color-mix(in srgb,var(--accent-on) 70%,transparent),0 1px 2px color-mix(in srgb,var(--ink) 5%,transparent),0 16px 40px -12px color-mix(in srgb,var(--ink) 20%,transparent)}
.mt-gls-blob{position:absolute;pointer-events:none;border-radius:50%;background:radial-gradient(circle,color-mix(in srgb,var(--accent) 38%,transparent),transparent 70%);filter:blur(48px)}
.mt-gls-chip{display:inline-flex;align-items:center;gap:.5em;padding:.35em 1em;border-radius:999px;border:1px solid color-mix(in srgb,var(--accent-on) 60%,transparent);background:color-mix(in srgb,var(--paper) 40%,transparent);backdrop-filter:blur(10px) saturate(140%);-webkit-backdrop-filter:blur(10px) saturate(140%);box-shadow:0 4px 14px -6px color-mix(in srgb,var(--ink) 16%,transparent)}
.mt-gls-depth{position:absolute;border:1px solid color-mix(in srgb,var(--accent-on) 65%,transparent);border-radius:24px;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 82%,transparent),color-mix(in srgb,var(--paper) 62%,transparent));backdrop-filter:blur(14px) saturate(130%);-webkit-backdrop-filter:blur(14px) saturate(130%);box-shadow:inset 0 1px 0 color-mix(in srgb,var(--accent-on) 70%,transparent),0 16px 40px -12px color-mix(in srgb,var(--ink) 20%,transparent)}
.mt-gls-axis{position:absolute;height:1px;background:color-mix(in srgb,var(--accent) 35%,transparent);transform-origin:left center;pointer-events:none}
.mt-gls-chip-n{display:inline-flex;align-items:center;gap:.5em;padding:.35em 1em;border-radius:999px;border:1px solid color-mix(in srgb,var(--accent-on) 60%,transparent);background:color-mix(in srgb,var(--paper) 70%,transparent)}
```

- **禁忌**：玻璃禁叠玻璃（两层 blur 即糊）；光斑层是文本层的兄弟节点，禁进入任何文本节点的祖先链、禁压正文阅读主列；**禁玻璃卡成阵与横排等权三格**；每页玻璃层 3–4、文字层 opacity = 1；其余母题件一律 data-editable-skip

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：深度轴与 3–4 层玻璃是签名结构件，形状由 CSS 承担（data-editable-skip），层内文字仍是 data-editable 叶子节点。
- **设计层规避弱读**：文字层 opacity 恒为 1；光斑层是文本层的兄弟节点，永不进入文本节点的祖先链；玻璃不叠玻璃（无祖先-后代 backdrop-filter 嵌套）。
- **DOM 结构测试签署**：删掉 signature_operator，深度轴、3–4 层 z 档差异、逐级错位与三枚后退 chip 全部消失，页面退回同 gap 同 padding 的玻璃卡阵；元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 层级不是靠线划出来的，是靠「离光源多远」量出来的。

page_composition:
  skeleton: 对角深度栈（默认）/ 中心聚焦（备选 full-b）
  grid: {margin: 120, gutter: 40}
  balance: {anchor: 前景玻璃(右下,实), counterweight: 柔光斑(左上/右上)}
  whitespace_ratio: "≥60%"
  flow: "对角：远景(左上,透) → 中景 → 前景(右下,实)；重心回光学中心"
signature_operator: 把内容编译成左对齐的玻璃深度栈——三层玻璃左缘对齐、宽度单调递减
  （近景最宽在底、远景最窄在顶），每层有固定 z 深度与模糊/透明度档；
  近景承载标题（accent 蓝，唯一焦点）与结论数字，中景承载说明，远景承载正文与理念；
  三项数字为沿深度档后退的玻璃 chip，非横排三格。
silhouette: 左对齐 + 宽度递减的垂直堆叠（1560→1240→920）；深度靠模糊档体现；重心左下；左上长留白。
info_grammar:
  cover:    单块近景玻璃吞掉标题 + 满幅光斑（封面特权）
  toc:      3–4 层按章节优先级，宽度递减，层号即深度档
  claim:    近景主张句 + 中景一行说明，沿深度档错位
  analysis: 3 层按信息优先级，左对齐宽度递减，不同 z 档
  data:     三项数字 → 三枚沿深度档后退的 chip，末枚为焦点
  closing:  深度栈收束回近景单层，光斑半亮呼应
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 108px  # 轻倒挂细字，靠深度而非字高压层级；与正文 4.5:1
  --t-body:    24px  # 正文段落（长段落可读）；图注/说明走 caption 18、注脚走 meta 15
  rule: 标题:正文 ≥1.8:1；文字层 opacity = 1，禁灰化弱读；环境光斑不计入 accent 面积但禁压正文主列
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 玻璃层数 3–4，各层 z / 不透明度档互不相同
  - 三层左缘 x 相同，宽度单调递减
  - 无祖先-后代 backdrop-filter 嵌套（玻璃不叠玻璃）
  - 光斑层为文本层的兄弟节点，不进入任何文本节点的祖先链
  - 横排等权三格容器数 = 0
forbidden_defaults: [玻璃卡成阵同gap同padding, 横向等权三格 KPI, 卡片墙, 居中 hero, 实心色块卡, 硬偏移影, 光斑压正文主列]
dna_events: {cover: 强, claim: 中, analysis: 中, data: 强, toc: 弱, closing: 中}
```

---

**Variants 配色变体**

#### 蜜桃光

- **气质**：暖桃纸底 + 珊瑚光斑——晨光透过磨砂玻璃的温度，适合生活方式、消费品牌、女性健康与母婴

```css
--paper:#FBF3EC; --paper-tint:#F4E7DA;
--ink:#241C17;   --ink-tint:#3E3026;
--accent:#E26D4F; --accent-on:#FFF8F2;
```

#### 薄荷雾

- **气质**：冷绿雾底 + 青碧光斑——雨后植物园玻璃房，适合环保、健康、金融科技与清新商务

```css
--paper:#EDF5F0; --paper-tint:#DFEAE3;
--ink:#15201B;   --ink-tint:#29382F;
--accent:#2FA98C; --accent-on:#F4FBF8;
```
