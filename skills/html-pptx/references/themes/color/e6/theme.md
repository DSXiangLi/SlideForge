# E6 Memphis 孟菲斯

- **id**：e6
- **气质**：纯白底 + 墨黑粗描边 + 糖果色几何碎形，1980s Memphis 的戏谑与高能量
- **适用**：年轻消费品牌、活动发布、创意行业、教育科普、潮流零售、节庆营销
- **focus**：G9 + G5
- **世界参考**：1980s 孟菲斯设计小组（Ettore Sottsass 与米兰激进设计运动）——糖果色几何碎形、之字波浪线、彩纸屑撒布、黑白网格底的反叛平面语言
- **unforgettable**：彩纸屑撒布——圆点/三角/之字线几何碎形像庆祝彩纸撒在页面上，一眼 Memphis
- **分化声明**：与 d1 分化于 L2/L4/L5/L6——e6 是几何无衬线强字重对比（极粗标题对常规正文），d1 是圆体 500–600 的圆润轻盈（L2）；e6 母题是彩纸屑碎形/之字波浪线/粗描边，d1 是贴纸徽章/扇贝花边/奶油圆点（L4）；e6 容器是 2–3px 墨黑粗描边圆角卡 + accent 硬偏移投影，d1 是无描边大圆角 + 弥散软阴影（L5）；同为回弹缓动但参数错开（e6 cubic-bezier(.5,1.7,.4,1) 对 d1 (.34,1.56,.64,1)），且 e6 锚点是彩纸屑/卡片的 scale-pop 齐蹦 + magnetic 指针吸附，d1 是贴纸徽章单主角 Q 弹（L6）

**本质规范**（从 unforgettable 推理出的骨架硬规则——所有 G1–G9 规范须服从）

**视觉装置**：几何积木系统——3px ink 粗描边糖果色积木 + 硬偏移投影做物理重量感 + Futura 几何字即图形 + 之字线做过渡路标 + 彩纸屑做氛围层。布局传递信息，装置传递风格——两者叠加，不是用装置替代布局。

| # | 维度 | 规范 | 推理路径 |
|---|---|---|---|
| 1 | 氛围 | 派对桌面的彩色积木——有秩序地排列，不是散落 | 孟菲斯不是编辑部也不是垃圾桶，积木要有秩序 |
| 2 | 容器 | 粗描边色面块——3px ink 描边 + palette 色填充 + 硬偏移投影 | 糖果色编码信息类别，粗描边让块有实体感 |
| 3 | 分隔 | 不用发丝线——靠色面碰撞或之字线（`.mt-mem-zig`） | hairline 是瑞士系词汇，孟菲斯靠色面碰撞分区 |
| 4 | 层次 | 硬偏移投影做信息权重——焦点块 8px 投影，辅助块无投影 | 投影大小即信息权重，不是装饰 |
| 5 | 版式 | **有秩序的积木排列**——并列信息等大对齐，有主次信息大小不等 | 积木有秩序才有信息引导，散落只有混乱 |
| 6 | 入场 | scale-pop 蹦贴——彩纸屑与卡片的物理落位感 | 纸片是"蹦"上去的，不是"淡入"的 |
| 7 | 底色 | 纯白纸面（--paper）——糖果色的干净画布 | 纸纹与颗粒破坏糖果色的纯度 |
| 8 | 字色 | 墨黑印白纸 + 糖果色只进填充层——粗描边与结构线永远 ink | 墨色骨架托底，彩色只在填充层 |

**布局规则**（生成侧必须遵从——区分并列信息与有主次信息）：

- **并列信息**（目录章节、4 种店型、4 个流程步骤）→ **等大对齐**横排或 2×2，颜色轮转区分，全部统一投影（全有或全无）。大小不等在并列信息上只会造成认知混乱，不传递信息
- **有主次信息**（KPI 有焦点项、漏斗有断点、章节有重点）→ 焦点块**更大** + **8px 投影**，辅助块更小 + 无投影。大小差异和投影差异只在信息权重确实不同时使用
- **色面块必须占满可用宽度**——高对比色面块（3px 描边+糖果色填充+硬偏移投影）视觉重量极大，小色面在大画幅上显得小气。多块横排时等分全宽，2×2 时每块占满半宽半高区域，不漂浮在空白中的小方块
- **色面块尺寸由内容决定**——先确定文字需要多少空间，再确定色面块尺寸，不能为了大小不等而压缩文字空间导致溢出
- **色面块对齐**——横排时顶部或底部对齐（不是随意错位），2×2 时网格对齐（不是散落）

**骨架硬规则**（生成侧必须遵从）：
- **禁 masthead / mastfoot**——派对不需要编辑部刊头刊脚
- **禁 `.reveal` 通用入场**——用 `data-anim="scale-pop"` 替代（彩纸屑与卡片蹦贴上墙）
- **禁居中内容带布局**（`display:flex;flex-direction:column;justify-content:center`）——用有秩序的积木排列：内容在粗描边色面块上，块按信息关系排列
- **禁发丝线 hairline**——分隔靠色面碰撞或之字波浪线（`.mt-mem-zig`）
- **禁弥散 box-shadow**——唯一允许的"影"是硬偏移投影（`8px 8px 0` 或 `4px 4px 0`，零模糊）
- **禁倾斜/旋转容器**——信息要正可读，字歪七扭八无法传递信息
- **保留 3px 粗描边和硬偏移投影**——这是孟菲斯的材质语言，不是 guizang 的；粗描边 + 硬偏移影 = 签名容器，不可削弱
- **并列信息等大对齐**——不要在并列信息上用大小不等制造混乱

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
:root{--ease-out:cubic-bezier(.5,1.7,.4,1)}
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
```

- **禁忌**：彩纸屑每页 3–5 件为上限且按 palette 顺序轮转（同页至少两色，撒满即廉价）；之字线每页至多一条、禁进数据图表区（干扰读数）；硬偏移投影只许 accent 色，禁 ink 色投影（与描边糊成一团）、禁 palette 色投影（彩色影只有 accent 一支）；母题件一律 `data-editable-skip`

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
