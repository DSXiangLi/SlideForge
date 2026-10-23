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
:root{--ease-out:cubic-bezier(.2,1.25,.3,1)}
.mt-sig-bar{display:block;width:64px;height:10px;background:var(--accent)}
.mt-sig-folio{position:absolute;right:2%;bottom:-.16em;z-index:0;pointer-events:none;user-select:none;font-family:var(--font-display);font-weight:900;font-size:30vh;line-height:.8;color:color-mix(in srgb,var(--ink) 7%,transparent)}
.mt-sig-mark{display:inline-block;width:.55em;height:.55em;background:var(--accent)}
```

- **禁忌**：信号条每页至多一个、只许标题区/页眉；巨号页码只作背景层、禁与标题同区抢焦；信号方块只在列表/编号位，禁当装饰撒布；母题件一律 `data-editable-skip`

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
