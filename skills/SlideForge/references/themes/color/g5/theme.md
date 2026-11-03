# G5 三色旬刊

- **id**：g5
- **气质**：赭石 + 苔绿 + 暗夜蓝——大地色系 × 独立文学杂志，封闭三色的印刷物倔强
- **适用**：文化杂志、品牌特刊、餐饮与甜品、生活方式、限量与纪念叙事
- **focus**：G1 + G4
- **世界参考**：手编号限量版独立刊物——全册只有三支油墨，没有黑也没有白；纵深靠三色明度差，不靠阴影
- **unforgettable**：三色反转卡——相邻卡片赭石/苔绿/暗夜蓝底字配对反转（暗夜蓝底苔绿字 ↔ 苔绿底暗夜蓝字），全页无一处黑白灰
- **分化声明**：与 d1 分化于 L1/L4/L5/L6——d1 奶油底 + 焦糖 accent + 贴纸徽章/扇贝花边 + 大圆角弥散软影；g5 胭脂粉底 + 勃艮第彩色墨（零黑零灰零白）+ 三色反转配对面 + 三色带/刊号签母题 + 无阴影纯色面纵深

**本质规范**（从 unforgettable 推理出的骨架硬规则）

| # | 维度 | 规范 | 推理路径 |
|---|---|---|---|
| 1 | 氛围 | 只有三支油墨的印刷物——全册无黑白灰 | 三色封闭制，不是配色方案 |
| 2 | 容器 | 三色反转配对面——胭脂/黄油/酒红底字互反 | 反转即层级，不需要描边或阴影 |
| 3 | 分隔 | 色面跳跃——相邻异色面即边界 | 发丝线是杂志词汇，三色刊物靠色面跳跃分区 |
| 4 | 层次 | 明度阶梯——黄油前进/胭脂居中/酒红退后 | 纵深靠三色明度差，不靠阴影 |
| 5 | 版式 | 反转配对面——相邻卡片底字互反 | 不是居中内容带，是色面并置 |
| 6 | 入场 | mask-lines 逐行显影——刊物宣读感 | 旬刊的仪式感 |
| 7 | 底色 | 胭脂粉/黄油/酒红交替——不是固定一种底色 | 三色轮转做底，每页可以换底色 |
| 8 | 字色 | 三色互为底字——酒红底配黄油字、黄油底配酒红字 | 没有独立的"文字色"，文字色由底色决定 |

**骨架硬规则**：
- **禁 masthead / mastfoot**——刊物不需要编辑部家具
- **禁居中内容带布局**——用反转配对面，色面并置
- **禁 `.reveal`**——用 `data-anim="mask-lines"` 逐行显影
- **禁发丝线 hairline**——分隔靠色面跳跃或 `.mt-tri-rule`（双线装饰）
- **禁 box-shadow**——纵深靠三色明度阶梯
- **禁黑/白/灰**——全系统只有三支油墨（胭脂/黄油/酒红），"灰"用酒红透明度变体
- **容器用三色反转面**——相邻容器底字互反，不是同色卡片排列

**G1 color**

```css
--paper:#E4C9A8; --paper-tint:#8BAE6F;
--ink:#1A2B3D;   --ink-tint:#121E2D;
--accent:#8BAE6F; --accent-on:#1A2B3D;
```

- **accent 预算**：苔绿是点睛与底色双面手——赭石是默认页底，苔绿是亮面色域与焦点；暗夜蓝是唯一文字色与深色域；满屏暗夜蓝是封面/收束特权（暗夜蓝底 + 苔绿巨标）；首尾闭环：暗夜蓝封面（全亮）→ 收束页赭石底 + 三色带呼应。**面积-彩度落点**：赭石/苔绿走浅调低彩窗口、暗夜蓝走深调窗口，三色自构成明度阶梯（苔绿前进 / 赭石居中 / 暗夜蓝退后）。
- **多色立场**：封闭三色制——全系统只有三支油墨（赭石/苔绿/暗夜蓝），**禁第四色、禁黑禁白禁灰**；分配规则：三色互为底与字（暗夜蓝底配苔绿字、苔绿底配暗夜蓝字、赭石底配暗夜蓝字），配对反转即层级；中性色的职能由暗夜蓝全部承担（ink/结构线/正文）。

**G2 typography**

```css
--font-display:"Didot","Bodoni MT","Songti SC","Noto Serif SC",serif;
--font-body:"Songti SC","Noto Serif SC","STSong",serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 500–700（高对比衬线，拉丁落 Didot/Bodoni 档）、正文 400——旬刊的编辑部字排
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：衬线立场：≥77px→600–700；35–76px→500–600；正文 400；14–16px 小字 500–600
- **标题修饰**：刊号前缀（G9 `.mt-tri-tag`）+ 标题下三色带；**`<em>` 规则**：衬线标题中 `<em>` 触发切换到等宽字体（`--font-mono`），"衬线标题被等宽打断"的刊物编辑声调（禁用斜体——`em{font-style:normal;font-family:var(--font-mono)}`）
- **metric_fallback**：display→Songti SC/Noto Serif SC；body→Songti SC/Noto Serif SC；mono→SF Mono/Menlo

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——三色平涂就是全部材质，纸感交给胭脂底本身

**G4 shape**

- **圆角**：0（刊物的方正）
- **hairline**：1.5px solid var(--ink)——暗夜蓝细线，三色底上都成立
- **阴影**：无——纵深靠三色明度阶梯（苔绿前进/赭石居中/暗夜蓝退后），阴影在这个世界不存在
- **容器造型**：三色反转配对面——容器面在胭脂/黄油/酒红三色间轮转，底字配对固定（暗夜蓝底配苔绿字、苔绿/赭石底配暗夜蓝字）；**三色轮转纪律**：一排并列 tile 中赭石/苔绿/暗夜蓝三色轮转（非两色配对），第三色打破两色单调；同组并列容器相邻异色（深浅配对轮转）；单焦点 = 唯一的暗夜蓝底容器
- **高密度容器边界**：色面即分区（相邻异色面即边界，无需描边）；栏间暗夜蓝细线

**G5 motion**

- **气质**：editorial
- **强度上限**：默认
- **锚点偏好**：mask-lines 逐行显影（刊物宣读感）；数据页 draw-line；禁弹跳
- **节奏偏移**：时长档 +1
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / blur-in / flicker-in
- **fx 许可**：全禁

**G8 component**

- **亲和**：裂屏对开（三色对撞是它的原生形态）、网格矩阵（反转色面格子墙）、kv-rows（刊物的栏目页）
- **禁忌**：禁暗场词汇（辉光/暗角）；图表系列色在黄油/酒红/胭脂明度阶梯内派生，禁外色；不用幽灵巨字（杂志系词汇属于 a1，本刊的仪式感在三色）

**G9 motif**

- **词汇**：三色带（`.mt-tri-band`——赭石/苔绿/暗夜蓝三等分横带，页缘收束或标题下）/ 刊号签（`.mt-tri-tag`——mono 暗夜蓝小签「VOL.07 / NO.128」式期号，页眉位）/ 双线刊框（`.mt-tri-frame`——暗夜蓝 border + outline 双细线框，收编图版与引文） / 双线装饰（`.mt-tri-rule`——双侧 4px 暗夜蓝线夹中央字词，杂志封面仪式感；暗面版 `.mt-tri-rule-dark` 用 30% 透明苔绿色）/ 大刊号签（`.mt-tri-pill-lg`——44px mono 大签，封面专用）/ 小刊号签（`.mt-tri-pill-sm`——16px mono 小签，收束页用）/ 暗面刊框（`.mt-tri-frame-dark`——酒红底上的耳语式分隔线，30% 透明苔绿色替代实色线）

```css
/* G5 三色旬刊 · 装饰母题 */
.mt-tri-band{display:block;height:12px;background:linear-gradient(90deg,var(--paper) 0 33.3%,var(--accent) 33.3% 66.6%,var(--ink) 66.6%)}
.mt-tri-tag{font-family:var(--font-mono);font-size:14px;letter-spacing:.18em;color:var(--ink);border:1.5px solid var(--ink);padding:.25em .8em;display:inline-block}
.mt-tri-frame{border:1.5px solid var(--ink);outline:1px solid var(--ink);outline-offset:5px}
.mt-tri-frame-dark{border:1.5px solid rgba(139,174,111,0.30);outline:1px solid rgba(139,174,111,0.25);outline-offset:5px}
.mt-tri-rule{display:flex;align-items:center;gap:16px}
.mt-tri-rule::before,.mt-tri-rule::after{content:"";flex:1;height:4px;background:var(--ink)}
.mt-tri-rule-dark::before,.mt-tri-rule-dark::after{background:rgba(139,174,111,0.30)}
.mt-tri-pill-lg{font-family:var(--font-mono);font-size:44px;font-weight:600;letter-spacing:.12em;color:var(--accent);border:2px solid var(--ink);padding:.3em 1em;display:inline-block;background:var(--paper)}
.mt-tri-pill-sm{font-family:var(--font-mono);font-size:16px;letter-spacing:.14em;color:var(--ink);border:1.5px solid var(--ink);padding:.2em .6em;display:inline-block}
```

- **禁忌**：三色带每页至多一条（页缘或题下）；刊号签只许页眉一枚；反转配对不许错配（暗夜蓝底禁配赭石字——配对表即契约）；母题件一律 `data-editable-skip`（`.mt-tri-tag` 为文本载体类母题，文字可编辑）

**Variants 配色变体**

#### 抹茶三色

- **气质**：油墨换抹茶系——豆绿换雾灰、苔绿保留、暗夜蓝换深棕灰，和果子店感——茶文化、东方生活方式、手作

```css
--paper:#C9D6B8; --paper-tint:#8BAE6F;
--ink:#4A2E22;   --ink-tint:#382218;
--accent:#8BAE6F; --accent-on:#4A2E22;
```

#### 海盐三色

- **气质**：油墨换海盐系——雾蓝底 + 苔绿 + 藏青墨，海边小报感——旅行、户外、夏季专题

```css
--paper:#B9D2E0; --paper-tint:#8BAE6F;
--ink:#173A5E;   --ink-tint:#0F2C49;
--accent:#8BAE6F; --accent-on:#173A5E;
```
