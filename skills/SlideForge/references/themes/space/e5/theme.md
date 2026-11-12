# E5 构成主义 Constructivism

- **id**：e5
- **气质**：米纸 + 墨黑 + 革命红，对角线劈开版面的宣传画压强
- **适用**：宣言式发布、动员/号召、变革叙事、观点鲜明的演讲、需要鼓动性的场合
- **focus**：G9 + G5
- **世界参考**：苏联构成主义海报 1920s（Rodchenko、Lissitzky）——红黑石印两色、激进对角线、宣传口号式排版
- **unforgettable**：对角线切割——页面被一条粗对角色带劈开，文字沿对角排布，一眼宣传画
- **分化声明**：与 c1 分化于 L1/L4/L6/L7——e5 米纸底 + 革命红石印两色、c1 纯黑舞台 + 信号橙；e5 母题是对角切割带/粗黑横杠/阶梯错排、c1 是信号条/巨号页码/信号方块；e5 动效是 wipe-clip 硬切直进直出零过冲、c1 是 scale-pop 过冲回弹爆发曲线；e5 构图对角线亲和且禁水平垂直网格矩阵、c1 巨字宣言居中压场

**G1 color**

```css
--paper:#eadfc4; --paper-tint:#ddd0b0;
--ink:#171310;   --ink-tint:#2b241a;
--accent:#9E1B1E; --accent-on:#eadfc4;
```

- **accent 预算**：内容页 accent 面积 ≤15%（对角色带本身即面积——预算是给结构件的，比瑞士系宽，但单页至多一条红带/一个红色焦点）；满屏红仅封面宣言页特权（满版红 + 反白口号）；首尾闭环：封面满版红（全亮）开场 → 收束页红色对角带（半亮）呼应。

**G2 typography**

```css
--font-display:"Arial Black","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题极粗 800–900、正文 400；口号即压强
- **字号对比**：主标题:正文 ≥8:1（低密度）；巨字特档 10:1（宣言页）；高密度 ≥5:1
- **字重映射**：反向立场（不走倒挂——极粗大写即宣传画）：标题恒重 800–900（≥35px 全档）；正文 400；14–16px 小字 500–600
- **标题修饰**：拉丁标题全大写；中文标题配粗黑横杠（`.mt-con-bar`）引导——口号式排版的原生语言

**G3 texture**

```css
--texture-type: grain;
--texture-layer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E");
--texture-scope: all;
```

- **立场**：石印颗粒全页轻铺——油墨世界的纸都有肌理（scope all，仍需生成侧逐页 `texture-on` 落码）；强度烧死 0.05 不得加深（颗粒是纸性不是图案）

**G4 shape**

- **圆角**：0
- **hairline**：不用——分区靠色带与对角切割，细线太文气
- **阴影**：无承托投影；唯一允许的"影"是对角色带的双印错位（`.mt-con-diag--print`，油墨第二遍没对准的套印，不是光影）
- **容器造型**：无容器立场——色带与对角线即结构；内容直接落纸面或 ink/accent 纯色带内（反白字）；禁圆角、禁承托投影、禁玻璃
- **高密度容器边界**：ink / accent 纯色带面承载反白字——色带即容器即边界（宣传画的色块压强）；带间分区靠对角切割与粗黑横杠（G9），细线描边在本世界不存在，容器边界义务由色带面承担

**G5 motion**

- **气质**：dramatic
- **强度上限**：默认
- **锚点偏好**：wipe-clip 硬切（标题与色带沿对角方向切出）+ chars 逐字砸落（封面口号）；rise-in 硬位移（阶梯错排块逐级入场）；count-up 只给真正的 KPI 英雄数字
- **节奏偏移**：时长档 −1（急促）；阶梯步长 ≤50ms
- **缓动签名**：覆盖 `--ease-out` 为 cubic-bezier(.8,0,.2,1)——硬切急停，零过冲零回弹
- **禁用**：scale-pop / blur-in / mask-lines / gradient-flow（过冲回弹与一切柔化手段都与硬切立场冲突）
- **fx 许可**：全禁

**G8 component**

- **亲和**：裂屏对开（对角变体——裂屏线必须是斜的）、巨字宣言（口号式）、数据英雄（数字配粗横杠）
- **禁忌**：禁水平垂直网格矩阵连页——构成主义就是反网格的；轴与节点的时间轴/流程必须走对角或阶梯错排，禁水平直线轴；不用加号角标/网格点阵（瑞士系词汇）与 Ghost 残影字（杂志系词汇）

**G9 motif**

- **词汇**：对角切割带（`.mt-con-diag`——transform rotate 的宽色带横贯页面，accent 或 ink 实色，页面结构件而非点缀，每页至多一条；`--print` 变体带 ink 低透明双印错位，油墨第二遍没对准的套印感）/ 楔形块（`.mt-con-wedge`——clip-path 三角实色楔块楔入版面边缘，Lissitzky"红楔"词汇，结构件每页至多一枚）/ 粗黑横杠（`.mt-con-bar`——极粗短杠，标题强调与列表编号标记）/ 阶梯错排（文字块沿对角逐级错位——生成侧用 margin 阶梯落码，无类）

```css
/* E5 构成主义 · 装饰母题 + 缓动签名 */
:root{--ease-out:cubic-bezier(.8,0,.2,1)}
.mt-con-diag{position:absolute;left:-15%;width:130%;height:14vh;pointer-events:none;transform:rotate(-12deg);background:var(--accent)}
.mt-con-diag--ink{background:var(--ink)}
.mt-con-diag--print{box-shadow:0 10px 0 color-mix(in srgb,var(--ink) 25%,transparent)}
.mt-con-wedge{position:absolute;pointer-events:none;width:38vmin;height:38vmin;background:var(--accent);clip-path:polygon(0 0,100% 0,0 100%)}
.mt-con-wedge--ink{background:var(--ink)}
.mt-con-bar{display:inline-block;width:1.6em;height:.28em;background:var(--ink)}
.mt-con-bar--accent{background:var(--accent)}
```

- **禁忌**：对角带每页至多一条、角度全场统一（−12° 签名角）；对角带是结构件，禁缩小当装饰撒布；楔块每页至多一枚、只许 accent/ink 实色、只许从页缘楔入（浮在版面中央即杂耍）；双印错位只给对角带（处处套印即脏）；横杠只在标题/列表位；母题件一律 `data-editable-skip`

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约；`signature_operator` 必须通过 DOM 结构测试——删掉它，页面的元素数量 / 分组 / 顺序 / 位置会变，否则退回重写。
- **灵魂承载**：签名形状升级为信息容器（对角带装标题与口号、楔形块装结论数字）；形状由 CSS 承担（`data-editable-skip`），其内部承载文字仍是 `data-editable` 叶子节点——文字始终留在 DOM，不牺牲可编辑性，也不需整页生图。

```yaml
doctrine: 动员与变革；版面是被力量劈开的现场，不是承载信息的容器。
signature_operator: 用一条 −12° 力线把版面劈成两个互相推挤的三角，标题与口号装进力线带内反白，
  其余文字沿力线阶梯错排或与之对抗；楔形块从页缘楔入承载结论数字。
silhouette: −12° 主对角；三角/楔形块面；重心沿对角分布；无水平垂直网格矩阵。
info_grammar:
  claim:    主标题必须在对角带内（信息容器，不是角标），右上放与之对抗的论点句
  data:     三项数字 → 沿力线阶梯错排（margin 逐级递增），末项用 accent 且带结论短句
  analysis: 说明文压到页缘注脚，不设独立正文块
  cover:    满版红 + 反白口号，楔形块从页缘楔入
type_scale:            # 三级层级（480px 预览基准，单位 cqw）；任何文本不得低于 floor
  floor:   1.5         # ≈7.2px，唯一硬下限（真实 deck ~2.7x 后 ≈19px）
  display: 3.0         # 序号 / 结论数字（对角带内或楔形块承载，与标题拉开 ≥1.3 倍）
  heading: 2.2         # 条目标题 / 对抗论点句
  body:    1.8         # 页缘注脚 / 说明（opacity ≥ .8，禁灰化弱读）
  rule: 序号:标题 ≥ 1.3:1 且 标题:正文 ≈ 1.2–1.5:1（禁层级倒挂：数字压过标题、说明又小又灰）
invariants:
  - 存在 ≥1 条 −12°±3° 的大面积色带，面积 ≥ 12%
  - 带内至少 1 个可编辑文本节点（承载主标题）
  - 对角方向梯度能量 ≥ 25%
  - 禁水平等权三栏（三栏容器数量 = 0）
  - 楔形块每页 ≤1 且必须贴页缘
forbidden_defaults: [水平垂直网格矩阵, 三格等权 KPI, 卡片墙, 居中对称, hairline 分区]
dna_events: {cover: 强, claim: 强, divider: 中, analysis: 弱, data: 强, closing: 强}
```

**Variants 配色变体**

#### 工业蓝

- **气质**：米纸 + 墨黑 + 工业蓝，五年计划与建设题材——工业、基建、工程、组织变革叙事

```css
--paper:#eadfc4; --paper-tint:#ddd0b0;
--ink:#171310;   --ink-tint:#2b241a;
--accent:#1E4E8C; --accent-on:#eadfc4;
```

#### 全墨

- **气质**：单色石印——米纸 + 墨黑两色印刷，最朴素也最锋利——档案、历史、极简宣言

```css
--paper:#eadfc4; --paper-tint:#ddd0b0;
--ink:#171310;   --ink-tint:#2b241a;
--accent:#171310; --accent-on:#eadfc4;
```

- **accent 预算**：accent 与 ink 同色——强调靠字重与对角结构，"满屏 accent"体现为满版墨底反白宣言页（封面/收束特权）；其余同基底口径
