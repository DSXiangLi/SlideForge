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
