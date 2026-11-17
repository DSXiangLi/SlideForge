# C1 信号黑

- **id**：c1
- **气质**：纯黑舞台 + 一束信号橙，keynote 发布的压强美学
- **适用**：产品发布、主题演讲、数据宣言、需要冲击力与记忆点的场合
- **focus**：G1 + G5
- **世界参考**：keynote 发布舞台与信号弹美学——黑场、追光、单束高饱和信号色
- **unforgettable**：信号橙色块 + 极粗巨字——黑场上唯一的橙色块就是全场焦点
- **分化声明**：与 c3 分化于 L2/L3/L4/L5/L6——c1 是极粗无衬线 + flat 平色 + 信号条/巨号页码母题 + 直角色块容器 + scale-pop 硬切签名；c3 是全栈等宽 + CRT 扫描线 + ASCII 框/光标母题 + 描边终端窗口 + typewriter/scramble 签名

**G1 color**

```css
--paper:#1a1a1a; --paper-tint:#242424;
--ink:#ffffff;   --ink-tint:#0f0f0f;
--accent:#FF5722; --accent-on:#1a1a1a;
```

- **accent 预算**：内容页 accent 面积 ≤10%（信号橙色块单焦点——单页至多一个橙色块）；满屏 accent 仅封面/收束特权；首尾闭环：封面信号橙色块 + 巨字开场 → 收束页橙色块（半亮或缩小）呼应。

**G2 typography**

```css
--font-display:"Arial Black","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题极粗 800–900、正文 400；层级靠色块与字重压强
- **字号对比**：主标题:正文 ≥8:1（低密度）；巨字特档 10:1（封面宣言页）；高密度 ≥5:1
- **字重映射**：反向立场（不走倒挂——极粗无衬线大字即压强）：标题恒重 800–900（≥35px 全档）；正文 400；14–16px 小字 500–600
- **标题修饰**：填充 + 描边混排（`.tt-outline`）亲和——信号黑标题里描边词充当背景层、填充词（或 accent 词）做焦点；删除线对照（`.tt-strike`）亲和反差数据带的 from 值；禁用 gradient-flow（柔化渐变削弱信号，G5 同口径）
- **metric_fallback**：display→Arial Black/Helvetica Neue（极粗立场无量度兼容替代，漂移时防线 C 兜底）；body→PingFang SC/Noto Sans SC；mono→SF Mono/Menlo
- **display 联网备选**：Bebas Neue 类窄体大写（fallback：'Arial Narrow','Helvetica Neue Condensed',sans-serif）——仅用户接受联网时加载，离线回落系统极粗无衬线无感

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——高冲击靠色块与字重压强，纹理只会削弱信号

**G4 shape**

- **圆角**：0
- **hairline**：不用——分区靠色块明度差与留白，不靠线
- **阴影**：无
- **容器造型**：大色块直角立场——accent / paper-tint / ink-tint 明度档纯色块承载内容，压强靠色块明度差不靠装饰；禁渐变、禁阴影；accent 色块单页至多一个（与单焦点纪律同口径）
- **高密度容器边界**：灰档面 + 1px 细框——paper-tint 平涂叠 1px color-mix(in srgb, var(--ink) 18%, transparent) 描边（暗底上面与底明度差小，框补边界，§12 例外条款）；框是刻度不是装饰，粗细永不超过 hairline

**G5 motion**

- **气质**：dramatic
- **强度上限**：默认
- **锚点偏好**：scale-pop（巨字与色块压入，配缓动签名的过冲回弹）+ wipe-clip 硬切揭示；封面 chars 逐字砸落；count-up 只给真正的 KPI 英雄数字
- **节奏偏移**：时长档 −1（短促有力）；阶梯步长 ≤60ms
- **缓动签名**：覆盖 `--ease-out` 为 cubic-bezier(.2,1.25,.3,1)——带过冲的爆发曲线，色块砸落有回弹
- **禁用**：blur-in / mask-lines / gradient-flow（柔化手段削弱信号冲击）
- **fx 许可**：constellation / starfield / particle-drift（ascii-field 禁——终端字符感与信号黑不搭）

**G8 component**

- **亲和**：巨字宣言、数据英雄（大数字直压）、裂屏对开（黑橙对撞）
- **禁忌**：禁连续两页网格矩阵——碎格子稀释压强；不用加号角标/网格点阵（瑞士系词汇）与 ASCII 字符装饰（终端系词汇）

**G9 motif**

- **词汇**：信号条（accent 粗短条，标题区/页眉的"信号"标记，每页至多一个）/ 巨号页码（超大极粗低透明数字，页面底缘背景层，只作背景不抢焦）/ 信号方块（小实心 accent 方块，替代圆点的列表/编号标记）

```css
/* C1 信号黑 · 装饰母题 + 缓动签名 */
:root{--ease-out:cubic-bezier(.2,1.25,.3,1);--t-display:120px;--t-caption:20px;--t-meta:18px}
.mt-sig-bar{display:block;width:64px;height:10px;background:var(--accent)}
.mt-sig-folio{position:absolute;right:2%;bottom:-.16em;z-index:0;pointer-events:none;user-select:none;font-family:var(--font-display);font-weight:900;font-size:30vh;line-height:.8;color:color-mix(in srgb,var(--ink) 7%,transparent)}
.mt-sig-mark{display:inline-block;width:.55em;height:.55em;background:var(--accent)}
```

- **禁忌**：信号条每页至多一个、只许标题区/页眉；巨号页码只作背景层、禁与标题同区抢焦；信号方块只在列表/编号位，禁当装饰撒布；母题件一律 `data-editable-skip`

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：信号橙色块和巨号页码是签名结构件，形状由 CSS 承担（data-editable-skip），其内部承载的文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，页面回到「标题 + 两段正文 + 横排三格 KPI」，信号橙色块、巨号页码背景层、色块明度分区、单焦点压强全部消失，元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 压强即信息——黑场上唯一的橙色块就是全场焦点，留白不是空虚而是蓄力。

page_composition:
  skeleton: 黑场单焦点（不对称居中偏移）
  grid: {margin: 120, gutter: 40}
  balance: {anchor: 信号橙色块(唯一焦点), counterweight: 巨号页码背景层(对侧底缘)}
  whitespace_ratio: "≥45%"
  flow: "焦点：信号橙色块承载核心信息 → 周围纯黑留白蓄力 → 巨号页码做背景层兜底"
signature_operator: 把每条信息编译成黑场上的明度分区——
  核心信息独占一块信号橙色块（accent 填充 + accent-on 文字，单页至多一块，绝对的视觉焦点）；
  辅助信息在 paper-tint / ink-tint 明度档色块上（明度差分区，不用线不用框）；
  标题极粗巨字（800–900）压在黑场上，信号条标记标题区（每页至多一条）；
  三项数字以纵向堆叠或错落排列的明度档色块承载（主数字独占 accent 色块），非横排等宽三格；
  巨号页码以 30vh 极粗低透明数字沉在页面底缘背景层，只做背景不抢焦。
silhouette: 黑场单焦点构图；纯黑底 + 一块信号橙色块（唯一高饱和面）+ 明度档灰块辅助；不对称平衡（焦点偏一侧，巨号页码在对侧底缘配重）；重心不在画布中心。
info_grammar:
  cover:    信号橙色块吞掉标题（满版 accent，封面特权），巨号页码沉在底缘
  toc:      3–5 块明度档色块纵向错落排列，当前章节用 accent 色块标记，信号条做章节分隔
  claim:    主张句独占信号橙色块（唯一 accent 焦点），说明在相邻 paper-tint 色块上
  analysis: 3–5 块明度档色块错落分区（paper-tint / ink-tint 明度差），每块承载一段信息
  data:     三项数字 → 纵向堆叠或错落排列的明度档色块，主数字独占 accent 色块
  closing:  信号橙色塔回到封面方向（半亮或缩小呼应），巨号页码最后一次出现
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 120px  # 极粗 800–900 承载黑场压强；与正文 4.3:1
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读；accent 面积 ≤10%（单焦点纪律）
  floor_note: body/heading/subhead 不覆盖，继承骨架 28/64/40；caption/meta 覆盖为 20/18（黑场小字需加粗可读）；地板由 max() 保证，无需后拦截门禁
invariants:
  - 信号橙色块单页 ≤1 块（accent 面积 ≤10%），是绝对的视觉焦点
  - 色块明度分区 ≥2 档（paper-tint / ink-tint 明度差），不用线不用框
  - 信号条单页 ≤1 条，只许标题区/页眉；巨号页码只作背景层（opacity ≤7%），禁与标题同区抢焦
  - 同组并列色块 width/height 一致，焦点用 accent 填充区分不用尺寸区分
  - 高密度容器边界用 1px color-mix(in srgb, var(--ink) 18%, transparent) 描边（暗底明度差小补边界），框是刻度不是装饰
  - 横排等权三格容器数 = 0
forbidden_defaults: [横向等权三格 KPI, 卡片墙成阵, 居中 hero, hairline 分区, 弥散软影, 渐变色块, 玻璃拟态, 多 accent 色块并置]
dna_events: {cover: 强, claim: 强, analysis: 中, data: 强, toc: 中, closing: 强}
```

---

**Variants 配色变体**

#### 赛博青

- **气质**：冷调电子信号，赛博感——开发者产品、数据平台、AI 基础设施发布

```css
--paper:#1a1a1a; --paper-tint:#242424;
--ink:#ffffff;   --ink-tint:#0f0f0f;
--accent:#00E5FF; --accent-on:#1a1a1a;
```

#### 警报红

- **气质**：警报/故障/转折，紧迫感——风险披露、安全主题、发布会的"问题"章节

```css
--paper:#1a1a1a; --paper-tint:#242424;
--ink:#ffffff;   --ink-tint:#0f0f0f;
--accent:#FF2D40; --accent-on:#ffffff;
```

- **accent 预算**：满版红仅封面（冲击力极强，连用两页即疲劳）；收束页用半亮红色块呼应；其余同基底口径
