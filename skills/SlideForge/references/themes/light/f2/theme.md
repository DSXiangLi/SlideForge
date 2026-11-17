# F2 霓虹夜行

- **id**：f2
- **气质**：子夜蓝黑 + 紫电灯管——雨后夜街，光是唯一的主角，招牌在湿地面上拖着倒影
- **适用**：科技发布会、AI 与前沿主题、夜间活动与演出、潮流文化、娱乐与电竞
- **focus**：G4 + G9
- **世界参考**：雨后城市夜街的霓虹灯管招牌——玻璃管内气体放电的均匀线光，亮部光晕、暗部深渊、湿路面倒影
- **unforgettable**：rim-glow 灯管卡 + 雨后倒影——容器描边一圈"内发光 + 外晕"像灯管弯成的框，仪式页发光招牌正下方拖一段倒影
- **分化声明**：与 c3 分化于 L1/L2/L4/L5/L6——c3 是磷光绿点状信号 + 全栈等宽 + ASCII 框/光标/提示符母题 + 直角描边终端窗 + typewriter/scramble 签名；f2 是紫电面状发光 + 几何无衬线 + rim-glow 灯管卡/发光字/雨后倒影母题 + 圆角发光容器 + flicker-in 通电点亮签名

**G1 color**

```css
--paper:#05070D; --paper-tint:#0B101C;
--ink:#E9F0FA;   --ink-tint:#141B2A;
--accent:#9E8CFF; --accent-on:#1A1040;
```

- **accent 预算**：内容页发光体面积 ≤12% 且**严格单色系**——光会膨胀，发光体的视觉面积大于像素面积，预算从严；全页发光色只许 accent 一种（第二个发光色 = 另一条街，串街即事故）；满屏发光禁止；首尾闭环：封面发光巨字开场 → 收束页同位发光半亮呼应。

**G2 typography**

```css
--font-display:"DIN Alternate","Avenir Next","Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 500–600 恒重（灯管线宽均匀，粗细变化像电压不稳）、正文 400
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：恒重立场：标题全档 500–600；正文 400；14–16px 小字 500
- **标题修饰**：发光字 `.mt-neo-sign`——封面/章节标题与关键数字点光（同色双晕 text-shadow）；正文标题不发光
- **metric_fallback**：display→Avenir Next/Helvetica Neue；body→PingFang SC/Noto Sans SC；mono→SF Mono/Menlo

**G3 texture**

```css
--texture-type: glow;
--texture-layer: radial-gradient(85% 60% at 50% 0%, color-mix(in srgb, var(--accent) 7%, transparent), transparent 62%);
--texture-scope: cover;
```

- **立场**：夜空微光——仪式页顶部一团冷辉（整条街的环境光）；正文页纯暗，光只属于灯管（容器与字），背景永不光

**G4 shape**

- **圆角**：12–16px（灯管可以弯，但不能折出直角死弯）
- **hairline**：发光线代替墨线——1px color-mix(in srgb, var(--accent) 45%, transparent) + 同色低透明外晕
- **阴影**：无承托投影（深渊里没有影子）——纵深靠 rim-glow 三件套：inset 1px 亮边 + inset 内发光 + 外侧光晕
- **容器造型**：灯管卡（`.mt-neo-tube`）——深底 + accent 半透描边 + 内发光 + 外晕；禁实心亮底卡（亮面在夜里是灯箱广告，不是容器）
- **高密度容器边界**：灯管卡成阵；暗场"面"的等价物 = 亮度阶梯（color-mix(in srgb, var(--ink) 4–6%, transparent) 微亮面），靠空气不靠边界

**G5 motion**

- **气质**：techy
- **强度上限**：默认
- **锚点偏好**：flicker-in 通电点亮为签名（标题与灯管卡——霓虹通电瞬间的抖动点亮，v7.6 起入骨架）+ blur-in 备选（先晕后聚焦）；`.mt-neo-dot` 呼吸指示点（amb-pulse）；数字 count-up 只给 KPI 英雄
- **节奏偏移**：不偏移
- **缓动签名**：默认三 token，不覆盖
- **禁用**：typewriter / scramble（那是终端的签名，串味即事故）
- **fx 许可**：starfield（夜空粒子可破格；constellation 的连线感属星图，禁）

**G8 component**

- **亲和**：巨字宣言（发光巨字是霓虹的封面原生形态）、数据英雄（发光大数字）、裂屏对开（亮/暗对撞）
- **禁忌**：禁密集网格矩阵连页（夜街需要深渊留白）；不用墨色 hairline 分区（暗底灰线像没擦干净）；图表单系列 accent 发光描线，禁多色系列（单色系纪律延伸到图表）

**G9 motif**

- **词汇**：灯管卡（`.mt-neo-tube`——rim-glow 容器，本主题容器本体）/ 发光字（`.mt-neo-sign`——同色双晕 text-shadow，只给标题与关键数字）/ 光管分隔线（`.mt-neo-line`——一根发光的灯管横线）/ 呼吸指示点（`.mt-neo-dot`——在线状态/直播标记）/ 雨后倒影（`.mt-neo-refl`——发光招牌/标题的内容副本，scaleY(-1) 翻转 + 渐隐 mask，湿路面反射；只接在发光体正下方）

```css
/* F2 霓虹夜行 · 装饰母题 */
.mt-neo-tube{position:relative;border:1px solid color-mix(in srgb,var(--accent) 55%,transparent);border-radius:14px;background:color-mix(in srgb,var(--paper-tint) 55%,transparent);box-shadow:inset 0 0 18px color-mix(in srgb,var(--accent) 16%,transparent),0 0 24px -6px color-mix(in srgb,var(--accent) 45%,transparent)}
.mt-neo-sign{color:var(--accent);text-shadow:0 0 10px color-mix(in srgb,var(--accent) 65%,transparent),0 0 36px color-mix(in srgb,var(--accent) 32%,transparent)}
.mt-neo-line{height:2px;border:none;border-radius:2px;background:var(--accent);box-shadow:0 0 10px color-mix(in srgb,var(--accent) 70%,transparent),0 0 28px color-mix(in srgb,var(--accent) 28%,transparent)}
.mt-neo-dot{display:inline-block;width:.5em;height:.5em;border-radius:50%;background:var(--accent);box-shadow:0 0 12px color-mix(in srgb,var(--accent) 80%,transparent);animation:amb-pulse 2.4s ease-in-out infinite}
.mt-neo-refl{transform:scaleY(-1);opacity:.35;pointer-events:none;filter:blur(1px);-webkit-mask-image:linear-gradient(180deg,transparent 28%,color-mix(in srgb,var(--accent) 45%,transparent));mask-image:linear-gradient(180deg,transparent 28%,color-mix(in srgb,var(--accent) 45%,transparent))}
```

- **禁忌**：发光字只给标题/关键数字（正文发光即噪）；灯管卡每页 ≤4；发光严格单色；`.mt-neo-dot` 每页 ≤3 枚；倒影每页至多一段、只许接在发光招牌/标题正下方（不发光的东西没有倒影）；母题件一律 `data-editable-skip`

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：灯管卡（.mt-neo-tube）是容器本体——rim-glow 三件套（inset 1px 亮边 + inset 内发光 + 外侧光晕）像灯管弯成的框。发光字（.mt-neo-sign 同色双晕 text-shadow）只给标题与关键数字。雨后倒影（.mt-neo-refl）只接在发光体正下方。
- **DOM 结构测试签署**：删掉 signature_operator，页面回到「居中标题 + 两段正文 + 横排三格 KPI」，灯管卡、发光字、光管分隔线、呼吸指示点、雨后倒影全部消失，元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 雨后夜街——子夜蓝黑深渊里，霓虹灯管是唯一的主角，招牌在湿地面上拖着倒影，光是唯一的主角。

page_composition:
  skeleton: 灯管卡阵——rim-glow 容器成阵 + 发光字标题 + 光管分隔线 + 雨后倒影（仪式页）
  grid: {margin: 96px 120px, gutter: 32px}
  balance: {anchor: 发光标题区(上), counterweight: 灯管卡正文区(下) / 呼吸指示点}
  whitespace_ratio: ">=40%"
  flow: "顶部冷辉定锚 → 发光字标题（同色双晕）→ 灯管卡承载正文（rim-glow 容器）→ 光管分隔线 → 倒影收束（仪式页）"
signature_operator: 把每条信息编译成霓虹夜街——
  核心主张句用发光字（.mt-neo-sign 同色双晕 text-shadow，accent 紫电色），标题 500–600 恒重（灯管线宽均匀）；
  正文装进灯管卡（.mt-neo-tube rim-glow 容器——accent 半透描边 + 内发光 + 外晕），每页 ≤4 个；
  三项数字不做横排等权三格——主数字用发光字独占一段（.mt-neo-sign 大数字），辅数字在灯管卡中；
  光管分隔线（.mt-neo-line 发光灯管横线）替代墨线做功能分隔；
  呼吸指示点（.mt-neo-dot amb-pulse 2.4s）标记在线状态/重点，每页 ≤3 枚；
  雨后倒影（.mt-neo-refl scaleY(-1) + 渐隐 mask）只接在发光招牌/标题正下方，只给仪式页；
  发光严格单色系——全页发光色只许 accent 一种。
silhouette: 子夜蓝黑深渊 + 发光字标题 + 灯管卡正文阵 + 光管分隔线。重心偏上（光从上方投下）。
info_grammar:
  cover:    暗底 + 顶部冷辉 + 发光巨字标题 + 雨后倒影（标题正下方）+ 齿孔无（暗场留白）
  toc:      3–5 个灯管卡排列，当前章节用呼吸指示点标记
  claim:    发光字主张句标题（上方，同色双晕），灯管卡承载正文（下方，rim-glow 容器），主数字用发光字独占一段，光管分隔线
  analysis: 2–4 个灯管卡在暗底上，每个承载一段信息，至多一个用 accent 发光焦点
  data:     主数字用发光字独占（.mt-neo-sign 大数字），非横排等权三格
  closing:  暗底 + 发光半亮呼应封面 + 倒影最后一次出现
type_scale:            # px@1920x1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 96px  # 几何无衬线 500–600 恒重；与正文 3.4:1
  rule: 标题:正文 >=1.8:1；正文层 opacity = 1；发光体面积 <=12% 且严格单色系
  floor_note: body/heading/subhead/caption/meta 不覆盖，继承骨架 28/64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 灯管卡每页 ≤4（rim-glow 容器——inset 1px 亮边 + inset 内发光 + 外侧光晕）
  - 发光字只给标题/关键数字，正文禁发光
  - 发光严格单色——全页发光色只许 accent 一种
  - 雨后倒影每页至多一段、只接在发光体正下方
  - 呼吸指示点每页 ≤3 枚
  - 深渊留白——暗底需要大面积留白，禁密集网格矩阵连页
  - 横排等权三格容器数 = 0
forbidden_defaults: [横向等权三格 KPI, 居中 hero, 墨色 hairline, 弥散软影, 渐变色块, 玻璃拟态, 满版色块, 多色发光, 实心亮底卡]
dna_events: {cover: 强, claim: 中, analysis: 弱, data: 中, toc: 弱, closing: 强}
```

**Variants 配色变体**

#### 电青

- **气质**：电青光管——更冷更科幻，赛博海边城市，适合前沿科技、游戏、数字产品发布

```css
--paper:#05070D; --paper-tint:#0B101C;
--ink:#E9F0FA;   --ink-tint:#141B2A;
--accent:#3ADFFF; --accent-on:#03222C;
```

#### 品红

- **气质**：品红光管——更热烈更俱乐部，适合音乐、演出、夜生活与次文化主题

```css
--paper:#05070D; --paper-tint:#0B101C;
--ink:#E9F0FA;   --ink-tint:#141B2A;
--accent:#FF4DA6; --accent-on:#2A0A1C;
```
