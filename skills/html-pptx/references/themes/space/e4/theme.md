# E4 包豪斯 Bauhaus

- **id**：e4
- **气质**：米白纸 + 墨黑 + 原色，圆/三角/方基本形的构成游戏，理性而有玩心
- **适用**：设计、教育、文化、产品方法论、品牌故事，任何"形式追随功能"立场的场合
- **focus**：G9 + G4
- **世界参考**：包豪斯 1919–1933（魏玛/德绍）——Kandinsky 与 Klee 的基本形练习、三原色构成、不对称平衡、形式追随功能
- **unforgettable**：三原色基本几何形的构成游戏——一个正圆、一个三角、一个方块在页面上达成不对称平衡，一眼包豪斯
- **分化声明**：与 b1 分化于 L1/L4/L6/L7——e4 米白暖纸底 + 三原色同台（accent/2/3 三色封闭组 + Kandinsky 形色对应）、b1 灰白冷纸底 + 单一高亮蓝；e4 母题是基本形三件套（正圆/三角/方块）大尺度构成、b1 是加号角标/网格点阵/色块编号；e4 动效默认缓动且不禁 mask-lines（逐行揭示服务构成节奏）、b1 锐利快出急停缓动且禁 mask-lines；e4 构图是不对称平衡（网格必须被基本形打破）、b1 是网格矩阵纪律亲和

**本质规范**（从 unforgettable 推理出的骨架硬规则——所有 G1–G9 规范须服从）

| # | 维度 | 规范 | 推理路径 |
|---|---|---|---|
| 1 | 氛围 | Kandinsky 画室——画布上只有几何形、原色、墨线、留白 | 包豪斯不是编辑部，是画室 |
| 2 | 容器 | 几何形色面——容器即放大的基本形，内容直接坐在色面上 | 基本形是构成游戏的棋子，不是装饰贴纸 |
| 3 | 分隔 | 2px 粗结构线——横贯版面的功能分隔 | 发丝线是杂志词汇，包豪斯的线是承重墙 |
| 4 | 层次 | 色面对比——深度来自明度差与色相对比 | 包豪斯不用阴影，深度靠形与色的重量博弈 |
| 5 | 版式 | 不对称构成——网格被基本形打破，内容不居中 | 对称是静态，不对称才是包豪斯的平衡 |
| 6 | 入场 | wipe-clip 精确揭示 + mask-lines 逐行 | 基本形沿网格方向滑入，不是通用淡入 |
| 7 | 底色 | 米白画布（--paper）——画布就是画布 | 画布不是编辑部页面，不需要刊头刊脚框定 |
| 8 | 字色 | 墨黑印浅底 + 原色反白印深色面 | 油墨与纸的关系，不是前景与背景的关系 |

**骨架硬规则**（生成侧必须遵从）：
- **禁 masthead / mastfoot**——包豪斯不需要编辑部刊头刊脚，画布上的内容不需要家具框定
- **禁 `.reveal` 通用入场**——用 `data-anim="wipe-clip"` 或 `data-anim="mask-lines"` 替代
- **禁居中内容带布局**（`display:flex;flex-direction:column;justify-content:center`）——用不对称构成：基本形色面承载内容，形与形的不对称排布构成版式
- **禁发丝线 hairline**——分隔用 2px 粗结构线（`.mt-bau-line`）或色面边缘
- **禁 box-shadow**——深度靠色面对比
- **色面即容器**——数据/短句直接坐在放大的基本形色面上（反白字），不是在白底上加色块装饰

**G1 color**

```css
--paper:#f4f0e4; --paper-tint:#e9e3d3;
--ink:#141412;   --ink-tint:#26241f;
--accent:#D1342B; --accent-on:#f4f0e4;
--accent-2:#F2A600; --accent-2-on:#141412;
--accent-3:#0057A8; --accent-3-on:#f4f0e4;
```

- **accent 预算**：内容页 accent 面积 ≤10%——原色是构成的焦点件，单页至多一个 accent 实色基本形；满屏原色是封面/收束特权（满版原色 + 反白几何构成）；首尾闭环：满版原色封面（全亮）开场 → 收束页原色基本形（缩小或半亮）呼应。
- **多色立场**：三原色同台封闭制——红（accent）/黄（accent-2）/蓝（accent-3）禁第四彩色；分配规则 = **Kandinsky 形色对应**（1923 点线面问卷：方=红、三角=黄、圆=蓝），基本形的颜色由形决定不由排版决定；注意力预算：单页实色基本形 1–3 件成组（三形同页即三色同台），accent 红仍是唯一满版特权色。

**G2 typography**

```css
--font-display:"Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"Helvetica Neue","PingFang SC","Noto Sans SC",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：几何无衬线，字重倒挂立场（大标题 200–300 细而稳，小字 500–700）——包豪斯的粗细是功能不是装饰
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：归藏倒挂阶梯：≥154px→200；77–153px→200–300；35–76px→300–400；17–34px→400–500；14–16px→500–600；同页小字字重 ≥ 大字
- **标题修饰**：无（大写拉丁小标题可配基本形标记，修饰归母题不归字体）

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——包豪斯不要纹理，纸面、原色、几何三样就够

**G4 shape**

- **圆角**：0——圆只属于基本形正圆，不作为容器圆角策略
- **hairline**：2px solid var(--ink)——网格线是粗结构线、横贯版面的功能分隔，不是装饰细线
- **阴影**：无
- **容器造型**：直角纯色基本形块——容器即放大的基本形（正方块、正圆块、四分之一圆面承载内容，accent/accent-2/accent-3/ink/paper-tint 纯色档）；轮转纪律：一排并列的色面容器在 accent/accent-2/accent-3/ink/paper-tint 五档中轮转，禁单色面贯穿全格；单页实色基本形至多 2 个原色 + 墨黑（三原色不同页全部出现）；**色面即容器**：数据或短句直接坐在放大的基本形色面上（反白字），基本形块是不对称构图的平衡件与承重件，不是背后贴纸；禁圆角卡、禁渐变、禁阴影
- **高密度容器边界**：直角纯色块面 + 2px ink 粗结构线——包豪斯的边界是色面与结构线（hairline 口径即 2px 结构线），面阵之间以粗结构线横贯分区；细描边框不存在于本世界，容器边界义务由面承担

**G5 motion**

- **气质**：professional
- **强度上限**：默认
- **锚点偏好**：wipe-clip 精确揭示（基本形块与标题沿网格方向滑入）+ mask-lines（标题逐行揭示，服务构成节奏）；count-up 给数据英雄页
- **节奏偏移**：时长档 −1（短促）；阶梯步长 ≤60ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / persp-in / blur-in（过冲弹跳与柔焦不是包豪斯的理性）
- **fx 许可**：全禁

**G8 component**

- **亲和**：裂屏对开（原色对撞）、巨字宣言（配基本形平衡件）、图文证据（图与文的不对称并置）
- **禁忌**：碰撞即构成纪律：基本形之间必须有穿插/叠加/切断关系——一个形压住另一个形的边缘、或切断结构线、或与文字层叠穿插，禁平行排列各自孤立；禁严格对称的静态网格矩阵连页——包豪斯的平衡是不对称的，网格可用但必须被基本形打破；轴与节点可用但轴线必须粗结构线化；不用加号角标/网格点阵（那是瑞士系词汇）

**G9 motif**

- **词汇**：基本形三件套（`.mt-bau-circle` 正圆 / `.mt-bau-tri` 三角 / `.mt-bau-square` 方块——颜色由形决定：方=accent 红、三角=accent-2 黄、圆=accent-3 蓝）/ 粗结构条（`.mt-bau-bar`——10px 墨黑横贯条，版面的承重墙）/ 四分之一圆（`.mt-bau-quarter`——圆的一个象限，顶角用，可 transform rotate 转向）/ 粗网格线（2px ink 结构线） / 硬偏移结构条（`.mt-bau-bar-offset`——10px ink 结构条 + 12px 零模糊偏移影，仅封面/收束页使用，几何构成的硬边冲击）/ 基本形微旋转（`.mt-bau-rotate-l` / `.mt-bau-rotate-r`——-3°/+3° 固定两档，方向交替打破对称网格）

**尺度纪律（J3 期，"小气"教训）**：基本形是建筑不是贴纸——参与构图的基本形**短边 ≥ 画幅短边的 1/5**（1920×1080 下 ≥216px），小于此尺度的基本形禁止出现；色面容器的合法面积是 **1/4–1/2 页**（裂屏尺度的色面）；基本形出血合法且推荐（被页缘裁切是构成的一部分，完整小形才是贴纸）；竖向空间必须被至少一件形/条贯穿或切断——形只在角落扎堆即"小气"。

```css
/* E4 包豪斯 · 装饰母题 */
.mt-bau-circle,.mt-bau-tri,.mt-bau-square,.mt-bau-quarter{position:absolute;pointer-events:none;user-select:none}
.mt-bau-circle{border-radius:50%;background:var(--accent-3)}
.mt-bau-tri{clip-path:polygon(50% 0,100% 100%,0 100%);background:var(--accent-2)}
.mt-bau-square{background:var(--accent)}
.mt-bau-quarter{border-radius:0 0 0 100%;background:var(--accent-3)}
.mt-bau-bar{display:block;height:10px;background:var(--ink)}
.mt-bau-fill-ink{background:var(--ink)}
.mt-bau-tint{background:color-mix(in srgb,var(--ink) 10%,transparent)}
.mt-bau-line{display:block;height:2px;background:var(--ink)}
.mt-bau-bar-offset{display:block;height:10px;background:var(--ink);box-shadow:12px 12px 0 color-mix(in srgb,var(--ink) 15%,transparent);margin-bottom:12px}
.mt-bau-rotate-l{transform:rotate(-3deg)}
.mt-bau-rotate-r{transform:rotate(3deg)}
```

- **禁忌**：基本形必须正圆/正三角/正方——禁椭圆、禁圆角矩形、禁任意多边形，形不真即背叛；形色对应是法则（禁红圆蓝方）；**构成纪律：基本形必须参与构图——穿压文字下层（z-index 垫大标题）、自身作色面容器承载内容、或切断网格结构线——禁孤立漂浮的装饰贴纸**；每页 1–3 件成组构成不对称平衡，禁对称撒布当墙纸；实色基本形组单页至多一组（单焦点纪律在多色下的形态）；母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 原色黄

- **气质**：原色黄 + 墨黑，乐观明亮，教室里的构成练习——教育、儿童、科普、生活方式品牌

```css
--paper:#f4f0e4; --paper-tint:#e9e3d3;
--ink:#141412;   --ink-tint:#26241f;
--accent:#F2A600; --accent-on:#141412;
--accent-2:#D1342B; --accent-2-on:#f4f0e4;
--accent-3:#0057A8; --accent-3-on:#f4f0e4;
```

- **accent 预算**：黄底配深字（accent-on 用 ink）；满版黄封面投影场景注意亮度，正文页黄面积仍 ≤10%；三原色角色轮转（方=accent 黄/三角=accent-2 红/圆=accent-3 蓝）；其余同基底口径

#### 原色蓝

- **气质**：原色蓝 + 墨黑，冷静理性，最贴近瑞士邻居的一种光——科技、建筑、机构发布

```css
--paper:#f4f0e4; --paper-tint:#e9e3d3;
--ink:#141412;   --ink-tint:#26241f;
--accent:#0057A8; --accent-on:#f4f0e4;
--accent-2:#F2A600; --accent-2-on:#141412;
--accent-3:#D1342B; --accent-3-on:#f4f0e4;
```
