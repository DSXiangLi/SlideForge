# E6 Memphis 孟菲斯

- **id**：e6
- **气质**：纯白底 + 墨黑粗描边 + 糖果色几何碎形，1980s Memphis 的戏谑与高能量
- **适用**：年轻消费品牌、活动发布、创意行业、教育科普、潮流零售、节庆营销
- **focus**：G9 + G5
- **世界参考**：1980s 孟菲斯设计小组（Ettore Sottsass 与米兰激进设计运动）——糖果色几何碎形、之字波浪线、彩纸屑撒布、黑白网格底的反叛平面语言
- **unforgettable**：彩纸屑撒布——圆点/三角/之字线几何碎形像庆祝彩纸撒在页面上，一眼 Memphis
- **分化声明**：与 g2 分化于 L2/L4/L5/L6——e6 是几何无衬线强字重对比（极粗标题对常规正文），g2 是圆体 700 的手账风（L2）；e6 母题是彩纸屑碎形/之字波浪线/粗描边，g2 是荧光高亮带/纸胶带便签（L4）；e6 容器是 2–3px 墨黑粗描边圆角卡 + accent 硬偏移投影，g2 是微旋转便签卡 + 荧光标注层（L5）；同为回弹缓动但参数错开（e6 cubic-bezier(.5,1.7,.4,1) 对 g2 无缓动签名），且 e6 锚点是彩纸屑/卡片的 scale-pop 齐蹦 + magnetic 指针吸附，g2 是荧光笔划过 + 便签贴入（L6）

**本质规范**（从 unforgettable 推理出的骨架硬规则——所有 G1–G9 规范须服从）

**视觉装置**：几何积木系统——3px ink 粗描边糖果色积木 + 硬偏移投影做物理重量感 + Futura 几何字即图形 + 之字线做过渡路标 + 彩纸屑做氛围层。布局传递信息，装置传递风格——两者叠加，不是用装置替代布局。

| # | 维度 | 规范 | 推理路径 |
|---|---|---|---|
| 1 | 氛围 | 派对桌面的彩色积木——有秩序地排列，不是散落 | 孟菲斯不是编辑部也不是垃圾桶，积木要有秩序 |
| 2 | 容器 | 粗描边色面块——3px ink 描边 + palette 色填充 + 硬偏移投影 | 糖果色编码信息类别，粗描边让块有实体感 |
| 3 | 分隔 | 不用发丝线——靠色面碰撞或之字线（`.mt-mem-zig`） | hairline 是瑞士系词汇，孟菲斯靠色面碰撞分区 |
| 4 | 层次 | 硬偏移投影做信息权重——焦点块 8px 投影，辅助块无投影 | 投影大小即信息权重，不是装饰 |
| 5 | 版式 | 之字路径积木——信息沿单向折线逐块吸附，不是居中带也不是横排格 | 积木有路径才有信息引导，散落只有混乱 |
| 6 | 入场 | scale-pop 蹦贴——彩纸屑与卡片的物理落位感 | 纸片是"蹦"上去的，不是"淡入"的 |
| 7 | 底色 | 纯白纸面（--paper）——糖果色的干净画布 | 纸纹与颗粒破坏糖果色的纯度 |
| 8 | 字色 | 墨黑印白纸 + 糖果色只进填充层——粗描边与结构线永远 ink | 墨色骨架托底，彩色只在填充层 |

**布局规则**（生成侧必须遵从——区分并列信息与有主次信息）：

- **并列信息**（目录章节、4 种店型、4 个流程步骤）→ 沿之字路径逐块吸附，等大等间距、颜色按 palette 固定顺序轮转，全部统一投影（全有或全无）；**禁横排等权三格**
- **有主次信息**（KPI 有焦点项、漏斗有断点）→ 焦点块**更大** + 8px 硬偏移投影且位于路径末段，辅助块更小 + 无投影；块宽沿路径单调不减
- **色面块必须占满可用宽度**——高对比色面块（3px 描边+糖果色填充+硬偏移投影）视觉重量极大，小色面在大画幅上显得小气。多块横排时等分全宽，2×2 时每块占满半宽半高区域，不漂浮在空白中的小方块
- **色面块尺寸由内容决定**——先确定文字需要多少空间，再确定色面块尺寸，不能为了大小不等而压缩文字空间导致溢出
- **色面块对齐**——块心落在之字路径的折点上，按 45°/135° 转折吸附；不是横排对齐，也不是散落

**骨架硬规则**（生成侧必须遵从）：
- **禁 masthead / mastfoot**——派对不需要编辑部刊头刊脚
- **禁 `.reveal` 通用入场**——用 `data-anim="scale-pop"` 替代（彩纸屑与卡片蹦贴上墙）
- **禁居中内容带布局**（`display:flex;flex-direction:column;justify-content:center`）——用有秩序的积木排列：内容在粗描边色面块上，块按信息关系排列
- **禁发丝线 hairline**——分隔靠色面碰撞或之字波浪线（`.mt-mem-zig`）
- **禁弥散 box-shadow**——唯一允许的"影"是硬偏移投影（`8px 8px 0` 或 `4px 4px 0`，零模糊）
- **禁倾斜/旋转容器**——信息要正可读；旋转只给之字路径本身与彩纸屑，不给积木内的文字
- **保留 3px 粗描边和硬偏移投影**——这是孟菲斯的材质语言，不是 guizang 的；粗描边 + 硬偏移影 = 签名容器，不可削弱
- **并列信息等大对齐**——信息必须沿之字路径编译为积木；**禁横排等权三格 KPI 与卡片墙成阵**（G10 composition_program 优先于本节其余条款）

**G1 color**

```css
--paper:#FFF8EE; --paper-tint:#FFE9C7;
--ink:#1A1A2E;   --ink-tint:#3A3A55;
--accent:#FF3DA5; --accent-on:#FFF8EE;
--palette-1:#FF3DA5; --palette-1-on:#FFF8EE;
--palette-2:#FFD93D; --palette-2-on:#1A1A2E;
--palette-3:#00B8D9; --palette-3-on:#1A1A2E;
--palette-4:#7BC950; --palette-4-on:#1A1A2E;
```

- **accent 预算**：内容页 accent 面积 ≤10%，且**彩纸屑碎形计入用量**（3–5 件/页即花掉大半预算，其余留给单强调）；满屏 accent 仅封面/收束的特权；首尾闭环：封面彩纸屑 + accent 色块开场 → 收束页同构图彩纸屑呼应。
- **多色立场**：糖果罐封闭四色（粉/黄/蓝/绿，`--palette-1..4`）——禁第五种高饱和色；分配规则：碎形/彩带/徽章按 palette **固定顺序轮转**（index→colour，禁随机），彩纸屑同页至少两色；墨色骨架托底——粗描边与结构线永远 ink，彩色只在填充层；注意力预算：accent 粉仍是唯一满版特权色与强调色，palette 是类目语言不是强调语言。

**G2 typography**

```css
--font-display:"Futura","Century Gothic","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：几何无衬线强对比——标题 700–900 极粗，正文 400–500，字重差本身是装饰
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：极粗标题立场：≥77px→800；35–76px→700；正文 400；14–16px 小字 500–600
- **标题修饰**：无（装饰交给彩纸屑与之字线）

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——孟菲斯是丝网印刷式的平涂世界，纸纹与颗粒都破坏糖果色的纯度

**G4 shape**

- **圆角**：8–16px 圆角，全套容器统一圆角语言
- **hairline**：不用细分割线——区隔靠 2–3px 墨黑粗描边或之字波浪线（G9），细线在粗描边世界里发虚
- **阴影**：禁弥散软阴影；唯一允许的"影"是 accent 硬偏移投影（`8px 8px 0` 平涂色块影，丝印套色错位的隐喻）
- **容器造型**：粗描边圆角卡——2–3px ink 描边 + 圆角 + 可选 accent 硬偏移投影；禁无描边色块卡、禁弥散阴影、禁玻璃拟态
- **高密度容器边界**：粗描边圆角卡（`.mt-mem-card`）成阵即边界——2–3px ink 描边 + accent 硬偏移投影是本主题签名容器，框即立场；卡阵同描边粗细、同圆角、同投影方向，彩纸屑不许进卡内

**G5 motion**

- **气质**：playful
- **强度上限**：默认
- **锚点偏好**：scale-pop 是本命（彩纸屑碎形与粗描边卡弹跳入场）；magnetic 指针吸附亲和（徽章/按钮被光标吸住，±16px 上限不动）；其余元素 rise-in
- **节奏偏移**：时长档 −1（快，节庆的急切感）；阶梯步长 ≤60ms
- **缓动签名**：覆盖 `--ease-out` 为 cubic-bezier(.5,1.7,.4,1)——比 d1 的回弹更弹更闹，参数错开防撞
- **禁用**：typewriter / scramble（打字机是 techy 限定款，不属于糖果世界）
- **fx 许可**：全禁（彩纸屑撒布已是仪式层，canvas 粒子与之打架）

**G8 component**

- **亲和**：网格矩阵（粗描边圆角卡片阵是它的货架）、巨字宣言（极粗巨字 + 彩纸屑撒布，节庆感拉满）
- **禁忌**：禁 hairline 密集分割与直角硬朗构图；不用加号角标/网格点阵（瑞士系词汇）、不用 Ghost 残影/竖排题字条（杂志系词汇）；图表页保持粗描边 + 圆角 + 硬偏移投影，柱条可用 ≤8px 圆角

**G9 motif**

- **词汇**：彩纸屑碎形（`.mt-mem-confetti` 一组小几何形 absolute 撒布——圆点 + 三角 + 空心环，颜色在 accent / accent 明度阶梯 / ink 间轮换，**3–5 件/页克制撒布**）/ 之字波浪线（`.mt-mem-zig`：linear-gradient 折出的锯齿横带，替代一切直线分隔）/ 粗描边圆角卡（`.mt-mem-card`：3px ink 描边 + accent 硬偏移投影的签名容器）

```css
/* E6 Memphis 孟菲斯 · 装饰母题 + 缓动签名 */
:root{--ease-out:cubic-bezier(.5,1.7,.4,1);--t-display:112px;--t-caption:20px;--t-meta:18px}
.mt-mem-confetti{position:absolute;inset:0;pointer-events:none;user-select:none;overflow:hidden}
.mt-mem-confetti i{position:absolute;display:block;--pc:var(--palette-1)}
.mt-mem-confetti .mt-mem-c2{--pc:var(--palette-2)}
.mt-mem-confetti .mt-mem-c3{--pc:var(--palette-3)}
.mt-mem-confetti .mt-mem-c4{--pc:var(--palette-4)}
.mt-mem-dot{width:14px;height:14px;border-radius:50%;background:var(--pc)}
.mt-mem-tri{width:0;height:0;border-left:9px solid transparent;border-right:9px solid transparent;border-bottom:15px solid var(--pc)}
.mt-mem-ring{width:16px;height:16px;border:3px solid var(--ink);border-radius:50%}
.mt-mem-zig{height:12px;pointer-events:none;background-image:linear-gradient(135deg,var(--ink) 25%,transparent 25%),linear-gradient(225deg,var(--ink) 25%,transparent 25%);background-size:16px 12px;background-repeat:repeat-x}
.mt-mem-card{border:3px solid var(--ink);border-radius:14px;background:var(--paper);box-shadow:8px 8px 0 color-mix(in srgb,var(--accent) 85%,var(--ink))}
.mt-mem-block{position:absolute;border:3px solid var(--ink);border-radius:14px;padding:20px 26px}
.mt-mem-block--ink{background:var(--ink);color:var(--paper)}
.mt-mem-block--focus{box-shadow:8px 8px 0 color-mix(in srgb,var(--accent) 85%,var(--ink))}
.mt-mem-circle{position:absolute;border:3px solid var(--ink);border-radius:50%}
.mt-mem-bar{position:absolute;height:12px;pointer-events:none;background-image:linear-gradient(135deg,var(--ink) 25%,transparent 25%),linear-gradient(225deg,var(--ink) 25%,transparent 25%);background-size:16px 12px;background-repeat:repeat-x}
.mt-mem-step{display:inline-block;width:1.6em;height:.32em;background:var(--ink);margin-right:.5em;vertical-align:middle}
```

- **禁忌**：彩纸屑每页 3–5 件为上限且按 palette 顺序轮转（同页至少两色，撒满即廉价）；之字线每页至多一条、禁进数据图表区（干扰读数）；硬偏移投影只许 accent 色，禁 ink 色投影（与描边糊成一团）、禁 palette 色投影（彩色影只有 accent 一支）；母题件一律 `data-editable-skip`

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：几何色面是签名结构件，形状由 CSS 承担（data-editable-skip），其内部承载的文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，页面回到「标题 + 两段正文 + 横排三格 KPI」，几何色面拼贴、色面形状差异、不对称平衡、palette 轮转全部消失，元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 反叛的秩序；信息不是被摆进格子，而是被几何色面碰撞出来的分区承载。

page_composition:
  skeleton: 几何拼贴（无固定主轴，不对称平衡）
  grid: {margin: 120, gutter: 40}
  balance: {anchor: 大色面(主信息区), counterweight: 小色面/圆形/之字带(对侧)}
  whitespace_ratio: "≥40%"
  flow: "不对称：大色面承载核心信息 → 碰撞色面承载辅助信息 → 彩纸屑散布做氛围"
signature_operator: 把每条信息编译成一块几何色面——矩形/圆形/之字带碰撞形成不对称分区，
  色面填充按 palette 固定顺序轮转（粉/黄/蓝/绿），3px 墨粗描边给色面以实体感；
  标题独占一块大色面（accent 焦点 + 8px 硬偏移影），正文在相邻色面上（反白或深色 on 糖果色）；
  三项数字重排为沿底部排列的三块色面（大小递减，非等宽），主数字带 accent 标签；
  之字线/彩纸屑是构图的一部分（色面的兄弟节点），不是背景装饰。
silhouette: 多色面碰撞构图；矩形+圆形+之字带混合形状；不对称平衡（大色面一侧，小色面+彩纸屑另一侧）；重心不在画布中心。
info_grammar:
  cover:    一块超大色面吞掉标题（palette-1 填充 + 硬偏移影），右侧散落小几何色面 + 彩纸屑
  toc:      3–5 块不等大色面碰撞排列，palette 轮转编号，之字带做过渡
  claim:    论点句独占大色面（唯一 accent + 硬偏移影），说明在相邻小色面上
  analysis: 3–5 块色面碰撞分区，palette 按固定顺序轮转，每块承载一段信息
  data:     三项数字 → 三块沿底部排列的等宽等高色面，主数字色面用 accent 填充区分焦点
  closing:  大色面回到起点方向，之字带收束，彩纸屑一次强形态
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 132px  # 极粗 800 承载色面压强；与正文 4.7:1
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读
  floor_note: body/heading/subhead/caption/meta 不覆盖，继承骨架 28/64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 色面形状 ≥2 种（矩形 + 圆形或之字带），不对称排布
  - 色面描边 3px ink，填充按 palette 顺序轮转；硬偏移影单页 ≤1、偏移 8px 零模糊
  - accent 焦点单页 ≤1（accent 面积 3–10%）
  - 同组并列色面 width/height 一致，焦点用 accent 填充区分不用尺寸区分
  - 横排等权三格容器数 = 0
  - 彩纸屑在 DOM 上是色面的兄弟节点，不进任一色面内部
forbidden_defaults: [横向等权三格 KPI, 卡片墙成阵, 居中 hero, hairline 分区, 白底细描边卡, 玻璃拟态, 弥散软影]
dna_events: {cover: 强, claim: 强, analysis: 中, data: 强, toc: 中, closing: 强}
```

---

**Variants 配色变体**

#### 电光蓝

- **气质**：糖果罐换成电光蓝——更冷更锐的孟菲斯，科技馆与极客活动感——科技产品、赛事、潮流数码

```css
--paper:#FFF8EE; --paper-tint:#FFE9C7;
--ink:#1A1A2E;   --ink-tint:#3A3A55;
--accent:#00B8D9; --accent-on:#1A1A2E;
--palette-1:#00B8D9; --palette-1-on:#1A1A2E;
--palette-2:#FF3DA5; --palette-2-on:#FFF8EE;
--palette-3:#FFD93D; --palette-3-on:#1A1A2E;
--palette-4:#7BC950; --palette-4-on:#1A1A2E;
```

- **accent 预算**：电光蓝明度高，accent-on 反深字（墨黑）才读得清；palette 随罐轮转（蓝打头）；其余同基底口径

#### 柠檬黄

- **气质**：柠檬黄糖果罐——最闹最节庆的一罐，黑白网格底的经典孟菲斯海报感——节庆营销、儿童教育、活动邀请

```css
--paper:#FFF8EE; --paper-tint:#FFE9C7;
--ink:#1A1A2E;   --ink-tint:#3A3A55;
--accent:#FFD93D; --accent-on:#1A1A2E;
--palette-1:#FFD93D; --palette-1-on:#1A1A2E;
--palette-2:#FF3DA5; --palette-2-on:#FFF8EE;
--palette-3:#00B8D9; --palette-3-on:#1A1A2E;
--palette-4:#7BC950; --palette-4-on:#1A1A2E;
```

- **accent 预算**：柠檬黄明度最高——accent-on 必须反深字；硬偏移投影由 `.mt-mem-card` 的 color-mix(accent 85%, ink) 自动压暗，无需另处理；palette 随罐轮转（黄打头）；其余同基底口径

#### 马卡龙

- **气质**：糖果罐换成马卡龙——粉樱/奶油黄/baby 蓝/薄荷绿全浅调低彩（浅调窗口），最温柔的一罐——母婴、甜品、春季上新、女性消费

```css
--paper:#FDF6F0; --paper-tint:#FBEADD;
--ink:#2B2B3A;   --ink-tint:#454558;
--accent:#F5A8C0; --accent-on:#2B2B3A;
--palette-1:#F5A8C0; --palette-1-on:#2B2B3A;
--palette-2:#FCE8A6; --palette-2-on:#2B2B3A;
--palette-3:#A8D8EA; --palette-3-on:#2B2B3A;
--palette-4:#B5E3C8; --palette-4-on:#2B2B3A;
```

- **accent 预算**：全浅调档——所有彩色面一律反深字（-on 全墨）；硬偏移投影由 color-mix 自动压成奶深色，柔而不脏；其余同基底口径
